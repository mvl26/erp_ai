import json
import sys
from unittest.mock import MagicMock, patch

import frappe
from frappe.desk.form import assign_to
from helpdesk.test_utils import make_ticket

from erp_ai.agent import runner
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.routing import departments, load_routing_config
from erp_ai.agent.runner import BAD_ROUTING_ERROR, NO_SLA_REASON
from erp_ai.agent.test_agent_runner import CLASSIFY_A, CLASSIFY_FIELDS, PREFIX, RunnerTestBase
from erp_ai.agent.tools.route_ticket import (
	ASSIGN_REQUEST,
	NO_SLA,
	REASON_ASSIGN_FAILED,
	REASON_NO_VALID_ASSIGNEE,
	REASON_TASK_NOT_ASSIGNED,
	create_routed_task,
)
from erp_ai.constants import AGENT_USER, CLASSIFIED_BY_HUMAN, LOG_DOCTYPE, LOGGER_NAME
from erp_ai.test_utils import (
	make_active_agent,
	make_model_result,
	make_routing_rules,
	make_sla,
	make_team,
	pin_agent_roles,
	set_agent_settings,
)

ROUTE_TYPE = f"{PREFIX}route-type"
ROUTE_TEAM = f"{PREFIX}route-team"

SCORE_FIELDS = ("ai_complexity", "ai_importance", "ai_score_reason")
SCORE_REASON = f"{PREFIX}lý do chấm điểm"
CLASSIFY_B2 = json.dumps(
	{"dau_muc": "B", "do_tin_cay": "Cao", "ly_do": "x", "do_phuc_tap": 1, "do_quan_trong": 2}
)
CLASSIFY_E_NO_DEPARTMENT = json.dumps({"dau_muc": "E", "do_tin_cay": "Cao", "ly_do": "x"})
SLA_DOCTYPE = "HD Service Level Agreement"
CLASSIFY_SCORED = json.dumps(
	{
		"dau_muc": "A",
		"do_tin_cay": "Cao",
		"ly_do": "x",
		"do_phuc_tap": 2,
		"do_quan_trong": 3,
		"ly_do_diem": SCORE_REASON,
	}
)
CLASSIFY_C = json.dumps(
	{
		"dau_muc": "C",
		"do_tin_cay": "Cao",
		"ly_do": "x",
		"do_phuc_tap": 2,
		"do_quan_trong": 3,
		"ly_do_diem": SCORE_REASON,
	}
)


def _caller_file():
	"""File of the first frame above the mock machinery that called a patched function."""
	frame = sys._getframe(2)
	while frame.f_code.co_filename.endswith("unittest/mock.py"):
		frame = frame.f_back
	return frame.f_code.co_filename


class RoutingTestBase(RunnerTestBase):
	def setUp(self):
		super().setUp()
		# Cleanups run LIFO: set_user, rollback, then the stale Redis rule map (HD Team.after_insert).
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		frappe.set_user("Administrator")
		if not frappe.db.exists("HD Ticket Type", ROUTE_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": ROUTE_TYPE}).insert()
		if not frappe.db.exists("HD Team", ROUTE_TEAM):
			frappe.get_doc(
				{"doctype": "HD Team", "team_name": ROUTE_TEAM, "users": [{"user": AGENT_USER}]}
			).insert()
		mapping = {"A": {"ticket_type": ROUTE_TYPE, "agent_group": ROUTE_TEAM, "priority": "High"}}
		set_agent_settings(permission_level="L1", category_mapping=json.dumps(mapping))
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)

	def _ticket_row(self):
		return frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFY_FIELDS, as_dict=True)

	def _single_entry(self):
		(entry,) = self._entries(entry_type="classify")
		return entry

	def _scores(self):
		return frappe.db.get_value("HD Ticket", self.ticket.name, SCORE_FIELDS, as_dict=True)


class TestRoutingEndToEnd(RoutingTestBase):
	"""Walking skeleton (FEAT-006 T1): classification call -> decision -> fields on the ticket."""

	def test_l1_scores_written_to_ticket(self):
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()

		self.log_error.assert_not_called()
		scores = self._scores()
		self.assertEqual((scores.ai_complexity, scores.ai_importance), (2, 3))
		self.assertEqual(scores.ai_score_reason, SCORE_REASON)
		row = self._ticket_row()
		# R4/AC-3: category A with importance 3 routes to Urgent (not the mapping's High).
		self.assertEqual((row.ticket_type, row.agent_group, row.priority), (ROUTE_TYPE, ROUTE_TEAM, "Urgent"))
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual(
			json.loads(entry.actions),
			[{"tool": "apply_route", "doctype": "HD Ticket", "name": self.ticket.name, "ok": True}],
		)
		after = json.loads(entry.value_after)["ticket"]
		self.assertEqual((after["ai_complexity"], after["ai_importance"]), (2, 3))

	def test_l0_ticket_unchanged_scores_zero_not_null(self):
		set_agent_settings(permission_level="L0")
		before = self._ticket_row()
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()

		self.assertEqual(self._ticket_row(), before)
		scores = self._scores()
		self.assertEqual((scores.ai_complexity, scores.ai_importance), (0, 0))
		self.assertFalse(scores.ai_score_reason)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertFalse(entry.actions)

	def test_model_call_count_unchanged(self):
		set_agent_settings(permission_level="L0")
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()
		self.assertEqual(self.gateway.call_count, 1)

		set_agent_settings(permission_level="L1")
		self.gateway.calls.clear()
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()
		self.assertEqual([call["task"] for call in self.gateway.calls], ["classify", "reason"])

	def test_classify_request_lists_departments_and_has_600_tokens(self):
		rules = make_routing_rules(departments={"Kế toán": {"team": ROUTE_TEAM, "head": ""}})
		set_agent_settings(routing_rules=rules)
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()

		call = self.gateway.calls[0]
		self.assertEqual(call["max_tokens"], 600)
		expected = build_classify_request(
			self.ticket.subject, self.ticket.description, departments(load_routing_config(rules))
		)
		self.assertEqual(call["system"], expected["system"])
		self.assertIn("Kế toán", call["system"][0]["text"])

	def test_route_gets_switch_and_config_once_loaded(self):
		rules = make_routing_rules()
		set_agent_settings(routing_rules=rules, auto_assign_enabled=1)
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		with patch.object(runner, "_route") as route:
			self._run()

		route.assert_called_once()
		context, auto_assign = route.call_args.args[3], route.call_args.args[4]
		self.assertEqual(context.routing_config, load_routing_config(rules))
		self.assertIs(auto_assign, True)

	def test_switch_off_passed_as_false(self):
		set_agent_settings(auto_assign_enabled=0)
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		with patch.object(runner, "_route") as route:
			self._run()

		self.assertIs(route.call_args.args[4], False)

	def _run_b2(self, ticket_name):
		self.gateway.results = [
			make_model_result(text=CLASSIFY_B2),
			make_model_result(stop_reason="end_turn"),
		]
		runner.run_for_ticket(ticket_name, "ticket_insert")
		return frappe.db.get_value("HD Ticket", ticket_name, "priority")

	def _set_b_mapping(self, **rules):
		mapping = {"B": {"ticket_type": ROUTE_TYPE, "agent_group": ROUTE_TEAM, "priority": "Low"}}
		set_agent_settings(category_mapping=json.dumps(mapping), **rules)

	def test_priority_from_scores_through_runner(self):
		self._set_b_mapping()
		self.assertEqual(self._run_b2(self.ticket.name), "High")

		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual(json.loads(entry.value_after)["ticket"]["priority"], "High")
		self.assertEqual(json.loads(entry.value_before)["ticket"]["priority"], self.ticket.priority)
		self.assertEqual(json.loads(entry.actions)[0]["tool"], "apply_route")

	def test_changed_importance_table_used_next_run(self):
		self._set_b_mapping()
		self.assertEqual(self._run_b2(self.ticket.name), "High")

		rules = json.loads(make_routing_rules())
		rules["importance_priority"]["2"] = "Medium"
		set_agent_settings(routing_rules=json.dumps(rules))
		second = make_ticket(subject=f"{PREFIX}runner second ticket")
		self.assertEqual(self._run_b2(second.name), "Medium")

	def test_no_helpdesk_config_records_created(self):
		doctypes = (SLA_DOCTYPE, "HD Team", "Assignment Rule")
		before = {doctype: frappe.db.count(doctype) for doctype in doctypes}
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()

		self.assertEqual({doctype: frappe.db.count(doctype) for doctype in doctypes}, before)


class TestRoutingUnit(RoutingTestBase):
	"""(u1) outcome on the entry: applied from `ok`, actions, one reason per skipped field, no exception out (D-16)."""

	def _two_calls(self):
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]

	def test_applied_follows_ok_even_when_nothing_changed(self):
		self._two_calls()
		with patch.object(
			runner, "apply_route", return_value={"ok": True, "before": {}, "after": {}, "skipped": []}
		):
			self._run()

		self.assertEqual(self._single_entry().applied, 1)

	def test_exception_in_unit_rolls_back_records_class_and_run_continues(self):
		before = self._ticket_row()
		self._two_calls()

		def save_then_fail(decision, classification, context):
			frappe.db.set_value("HD Ticket", context.ticket_name, "priority", "Urgent")
			raise ValueError(f"{PREFIX}nội dung phiếu bí mật")

		with patch.object(runner, "apply_route", side_effect=save_then_fail):
			self._run()

		self.log_error.assert_not_called()
		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertIn("route apply_route: ValueError", entry.error)
		self.assertNotIn("bí mật", entry.error)
		(action,) = json.loads(entry.actions)
		self.assertEqual(
			(action["tool"], action["ok"], action["reason"]), ("apply_route", False, "ValueError")
		)
		self.assertNotIn("bí mật", entry.actions)
		self.assertEqual([call["task"] for call in self.gateway.calls], ["classify", "reason"])

	def test_refusal_records_reason_and_skips_sla_check(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		self._two_calls()
		self._run()

		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		(action,) = json.loads(entry.actions)
		self.assertEqual((action["tool"], action["ok"]), ("apply_route", False))
		self.assertTrue(action["reason"])

	def test_skipped_field_has_one_reason_when_route_note_explains_it(self):
		mapping = {"E": {"ticket_type": ROUTE_TYPE, "agent_group": "", "priority": ""}}
		set_agent_settings(category_mapping=json.dumps(mapping))
		self.gateway.results = [
			make_model_result(text=CLASSIFY_E_NO_DEPARTMENT),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()

		skipped = json.loads(self._single_entry().skipped_fields)
		team = [item for item in skipped if item["field"] == "agent_group"]
		self.assertEqual(team, [{"field": "agent_group", "reason": "không có bộ phận"}])
		self.assertIn("assignee", [item["field"] for item in skipped])

	def test_route_info_line_has_codes_only(self):
		self._two_calls()
		logger = MagicMock()
		fact = {"sla": f"{PREFIX}SLA", "priority": "High", "resolution_s": 60}
		with (
			patch.object(frappe, "logger", return_value=logger) as factory,
			patch.object(runner.site_facts, "applied_sla", return_value=fact),
		):
			self._run()

		factory.assert_called_with(LOGGER_NAME)
		lines = [call.args for call in logger.info.call_args_list if call.args[0].startswith("erp_ai route")]
		self.assertEqual(len(lines), 1)
		template, ticket, run_id, applied, assigned, task, comment, sla = lines[0]
		self.assertNotIn("lines=", template)
		self.assertEqual((ticket, applied, sla), (self.ticket.name, 1, "ok"))
		self.assertEqual((assigned, task, comment), (0, 0, 0))
		self.assertTrue(run_id)

	def test_broken_routing_rules_skip_sla_check_and_log_skipped(self):
		set_agent_settings(routing_rules="{không phải json")
		self._two_calls()
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertIn(BAD_ROUTING_ERROR, entry.error)
		self.assertEqual(
			[a["tool"] for a in json.loads(entry.actions)],
			["apply_route"],
		)
		logger.warning.assert_not_called()
		(info,) = [c.args for c in logger.info.call_args_list if c.args[0].startswith("erp_ai route")]
		self.assertEqual((info[3], info[7]), (1, "skipped"))

	def test_apply_exception_keeps_earlier_error_and_adds_its_own(self):
		set_agent_settings(routing_rules="{không phải json")
		self._two_calls()
		with patch.object(runner, "apply_route", side_effect=ValueError("x")):
			self._run()

		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertIn(BAD_ROUTING_ERROR, entry.error)
		self.assertIn("route apply_route: ValueError", entry.error)


class TestRoutingSla(RoutingTestBase):
	"""SLA check (D-9): read only, at L1+ with the switch on or off, a warning and a `sla_check` action."""

	def _only_sla(self, *, condition=""):
		for name in frappe.get_all(SLA_DOCTYPE, filters={"enabled": 1}, pluck="name"):
			frappe.db.set_value(SLA_DOCTYPE, name, "enabled", 0)
		frappe.db.set_value("HD Ticket", self.ticket.name, "sla", None)
		if condition is None:
			return
		sla = make_sla(self, default=not condition)
		# the condition is validated on insert, so a broken one can only get in sideways
		frappe.db.set_value(SLA_DOCTYPE, sla, "condition", condition)

	def _two_calls(self):
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]

	def _sla_actions(self):
		return [a for a in json.loads(self._single_entry().actions) if a["tool"] == "sla_check"]

	def test_slow_sla_warning_in_log(self):
		self._only_sla()
		# make_sla gives Urgent 4h = 240 min; expect 60.
		rules = json.loads(make_routing_rules())
		rules["expected_sla"]["A"]["resolution_min"] = 60
		set_agent_settings(routing_rules=json.dumps(rules), auto_assign_enabled=0)
		self._two_calls()
		logger = MagicMock()
		before_comments = self._comment_count()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		(action,) = self._sla_actions()
		self.assertFalse(action["ok"])
		self.assertIn("240 phút > mong đợi 60 phút (A)", action["reason"])
		logger.warning.assert_called_once()
		self.assertEqual(self._comment_count(), before_comments)

	def test_matching_sla_no_action_no_warning(self):
		self._only_sla()
		self._two_calls()
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		self.assertEqual(self._sla_actions(), [])
		logger.warning.assert_not_called()

	def test_no_sla_one_action_one_warning_and_one_line_gathered(self):
		self._only_sla(condition=None)
		set_agent_settings(auto_assign_enabled=1)
		self._two_calls()
		logger = MagicMock()
		captured = []
		real_route = runner._route

		def spy(*args):
			captured.append(real_route(*args))
			return captured[-1]

		with (
			patch.object(frappe, "logger", return_value=logger) as factory,
			patch.object(runner, "_route", spy),
		):
			self._run()

		(action,) = self._sla_actions()
		self.assertEqual((action["ok"], action["name"]), (False, self.ticket.name))
		self.assertEqual(action["reason"], NO_SLA_REASON)
		logger.warning.assert_called_once()
		self.assertEqual(factory.call_args_list[-1].args, (LOGGER_NAME,))
		self.assertIn(NO_SLA_REASON, logger.warning.call_args.args)
		self.assertEqual(captured, [[NO_SLA]])

	def _configure_person(self, person):
		mapping = {"A": {"ticket_type": ROUTE_TYPE, "agent_group": make_team(self), "priority": "High"}}
		assignees = {cat: {"default": person, "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(
			auto_assign_enabled=1,
			category_mapping=json.dumps(mapping),
			routing_rules=make_routing_rules(assignees=assignees),
		)

	def _comments_posted(self):
		(posted,) = [
			a for a in json.loads(self._single_entry().actions) if a["tool"] == "post_routing_comment"
		]
		self.assertEqual((posted["doctype"], posted["ok"]), ("Comment", True))
		return frappe.db.get_value("Comment", posted["name"], "content")

	def test_no_sla_one_warning_one_comment(self):
		self._only_sla(condition=None)
		person = make_active_agent(self)
		self._configure_person(person)
		self._two_calls()
		logger = MagicMock()
		before_comments = self._comment_count()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		logger.warning.assert_called_once()
		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(NO_SLA, self._comments_posted())
		self.assertNotIn(ASSIGN_REQUEST.split("{")[0], self._comments_posted())

	def test_no_sla_and_assign_request_share_one_comment(self):
		self._only_sla(condition=None)
		self._configure_person(AGENT_USER)
		self._two_calls()
		before_comments = self._comment_count()
		self._run()

		self.assertEqual(self._comment_count(), before_comments + 1)
		text = self._comments_posted()
		self.assertIn(NO_SLA, text)
		self.assertIn(ASSIGN_REQUEST.format(reason=REASON_NO_VALID_ASSIGNEE), text)

	def test_switch_off_no_sla_still_one_comment(self):
		self._only_sla(condition=None)
		set_agent_settings(auto_assign_enabled=0)
		self._two_calls()
		before_comments = self._comment_count()
		self._run()

		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(NO_SLA, self._comments_posted())

	def test_sla_without_priority_or_resolution_is_not_a_lag(self):
		self._two_calls()
		fact = {"sla": "x", "priority": None, "resolution_s": None}
		with patch.object(runner.site_facts, "applied_sla", return_value=fact):
			self._run()

		self.assertEqual(self._sla_actions(), [])
		self.assertEqual(self._single_entry().applied, 1)

	def test_broken_sla_condition_stops_route_cleanly(self):
		self._only_sla(condition="1/0")
		before = self._ticket_row()
		set_agent_settings(auto_assign_enabled=1)
		self._two_calls()
		set_value = frappe.db.set_value
		ticket_writes = []

		def spy(doctype, *args, **kwargs):
			# only the runner's own writes count: Frappe's `save` writes to the ticket itself and is rolled back
			if _caller_file() == runner.__file__:
				ticket_writes.append(doctype)
			return set_value(doctype, *args, **kwargs)

		before_comments = self._comment_count()
		logger = MagicMock()
		routed = []
		real_route = runner._route

		def route_spy(*args):
			routed.append(real_route(*args))
			return routed[-1]

		with (
			patch.object(frappe.db, "set_value", side_effect=spy),
			patch.object(frappe, "logger", return_value=logger),
			patch.object(runner, "_route", route_spy),
		):
			self._run()

		self.log_error.assert_not_called()
		# the SLA check stops after (u1) fails: no sla_check action, no warning, no sentence
		self.assertEqual([a["tool"] for a in json.loads(self._single_entry().actions)], ["apply_route"])
		logger.warning.assert_not_called()
		self.assertEqual(routed, [[]])
		self.assertNotIn("HD Ticket", ticket_writes)
		self.assertEqual(ticket_writes, ["ERP AI Log"])
		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertIn("route apply_route:", entry.error)
		self.assertNotIn(self.ticket.subject, entry.error)
		self.assertNotIn(self.ticket.subject, entry.actions)
		self.assertEqual(frappe.db.count("ToDo", {"reference_name": self.ticket.name}), 0)
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual([call["task"] for call in self.gateway.calls], ["classify", "reason"])


class AssignTestBase(RoutingTestBase):
	"""(u2)/(u4): a configured person, a team with no Assignment Rule, a fixed SLA fact, the switch on."""

	def setUp(self):
		super().setUp()
		self.person = make_active_agent(self)
		self.team = make_team(self)
		self._configure(self.team, self.person)
		set_agent_settings(auto_assign_enabled=1)
		# a fact with no resolution time never lags and never lacks: no SLA sentence joins the comment
		sla = patch.object(
			runner.site_facts,
			"applied_sla",
			return_value={"sla": f"{PREFIX}SLA", "priority": "High", "resolution_s": None},
		)
		sla.start()
		self.addCleanup(sla.stop)
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]

	def _configure(self, team, person):
		mapping = {"A": {"ticket_type": ROUTE_TYPE, "agent_group": team, "priority": "High"}}
		assignees = {cat: {"default": person, "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(
			category_mapping=json.dumps(mapping), routing_rules=make_routing_rules(assignees=assignees)
		)

	def _assigned_to(self, ticket=None):
		return frappe.get_all(
			"ToDo",
			filters={"reference_type": "HD Ticket", "reference_name": (ticket or self.ticket).name},
			pluck="allocated_to",
			order_by="creation, name",
		)

	def _notifications(self, user):
		return frappe.db.count(
			"Notification Log",
			{"for_user": user, "document_type": "HD Ticket", "document_name": self.ticket.name},
		)

	def _action(self, tool):
		return [a for a in json.loads(self._single_entry().actions) if a["tool"] == tool]

	def _comment_text(self):
		(posted,) = self._action("post_routing_comment")
		self.assertEqual((posted["doctype"], posted["ok"]), ("Comment", True))
		return frappe.db.get_value("Comment", posted["name"], "content")

	def _task_count(self):
		return frappe.db.count("Task", {"ai_ticket": self.ticket.name})


class TestRoutingAssign(AssignTestBase):
	def test_assigns_configured_person_one_notification(self):
		before_comments = self._comment_count()
		self._run()

		self.assertEqual(self._assigned_to(), [self.person])
		self.assertEqual(self._notifications(self.person), 1)
		(action,) = self._action("assign_owner")
		self.assertEqual((action["doctype"], action["name"], action["ok"]), ("HD Ticket", self.person, True))
		entry = self._single_entry()
		self.assertEqual(json.loads(entry.value_after)["assign"], [self.person])
		self.assertEqual(entry.predicted_assignee, self.person)
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual(self._task_count(), 0)
		self.assertEqual([a["tool"] for a in json.loads(entry.actions)], ["apply_route", "assign_owner"])

	def test_info_line_has_assigned_and_comment_flags(self):
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		(info,) = [c.args for c in logger.info.call_args_list if c.args[0].startswith("erp_ai route")]
		self.assertIn("assigned=%d task=%d comment=%d", info[0])
		self.assertEqual(info[3:], (1, 1, 0, 0, "ok"))

	def test_info_line_counts_the_posted_comment(self):
		self._configure(self.team, AGENT_USER)
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		(info,) = [c.args for c in logger.info.call_args_list if c.args[0].startswith("erp_ai route")]
		self.assertEqual(info[3:], (1, 0, 0, 1, "ok"))

	def test_team_rule_assigns_bot_does_not(self):
		member = make_active_agent(self)
		team = make_team(self, with_rule=True, rule_users=(member,))
		self._configure(team, self.person)
		with patch.object(runner, "assign_owner") as assign:
			self._run()

		assign.assert_not_called()
		self.assertEqual(self._assigned_to(), [member])
		self.assertEqual(self._notifications(self.person), 0)
		(action,) = self._action("assign_owner")
		self.assertFalse(action["ok"])
		self.assertEqual(action["reason"], f"phiếu đã có người được gán: {member}")
		self.assertEqual(action["rule"], frappe.db.get_value("HD Team", team, "assignment_rule"))

	def test_agent_account_never_assigned_one_comment(self):
		self._configure(self.team, AGENT_USER)
		before_comments = self._comment_count()
		with patch.object(runner, "assign_owner") as assign:
			self._run()

		assign.assert_not_called()
		self.assertEqual(self._assigned_to(), [])
		(action,) = self._action("assign_owner")
		self.assertEqual((action["ok"], action["reason"]), (False, "không gán tài khoản agent"))
		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(ASSIGN_REQUEST.format(reason=REASON_NO_VALID_ASSIGNEE), self._comment_text())
		self.assertFalse(self._single_entry().predicted_assignee)
		self.assertEqual(self._task_count(), 0)

	def test_failed_assign_one_comment_and_no_second_try(self):
		before_comments = self._comment_count()
		with patch.object(runner, "assign_owner", side_effect=ValueError("x")) as assign:
			self._run()

		assign.assert_called_once()
		(action,) = self._action("assign_owner")
		self.assertEqual((action["ok"], action["reason"]), (False, "ValueError"))
		self.assertIn("route assign_owner: ValueError", self._single_entry().error)
		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(ASSIGN_REQUEST.format(reason=REASON_ASSIGN_FAILED), self._comment_text())
		self.assertEqual(self._assigned_to(), [])

	def test_assign_that_wrote_then_raised_is_undone_but_route_kept(self):
		def write_then_raise(user, context):
			assign_to.add({"assign_to": [user], "doctype": "HD Ticket", "name": context.ticket_name})
			raise ValueError("x")

		with patch.object(runner, "assign_owner", side_effect=write_then_raise) as assign:
			self._run()

		assign.assert_called_once()
		self.assertEqual(self._assigned_to(), [])
		row = self._ticket_row()
		self.assertEqual((row.agent_group, row.priority), (self.team, "Urgent"))
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual([a["ok"] for a in json.loads(entry.actions)][:2], [True, False])
		self.assertIn("route assign_owner: ValueError", entry.error)

	def test_comment_that_wrote_then_raised_is_undone_but_route_kept(self):
		self._configure(self.team, AGENT_USER)
		real_post = runner.post_routing_comment

		def write_then_raise(lines, context):
			real_post(lines, context)
			raise ValueError("x")

		before_comments = self._comment_count()
		with patch.object(runner, "post_routing_comment", side_effect=write_then_raise):
			self._run()

		self.assertEqual(self._comment_count(), before_comments)
		row = self._ticket_row()
		self.assertEqual((row.agent_group, row.priority), (self.team, "Urgent"))
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertIn("route post_routing_comment: ValueError", entry.error)

	def test_refused_assign_one_comment(self):
		before_comments = self._comment_count()
		refusal = {"ok": False, "reason": "thiếu quyền đọc phiếu"}
		with patch.object(runner, "assign_owner", return_value=refusal):
			self._run()

		(action,) = self._action("assign_owner")
		self.assertEqual((action["ok"], action["reason"]), (False, "thiếu quyền đọc phiếu"))
		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(ASSIGN_REQUEST.format(reason=REASON_ASSIGN_FAILED), self._comment_text())

	def test_comment_exception_recorded_not_raised_not_retried(self):
		self._configure(self.team, AGENT_USER)
		with patch.object(runner, "post_routing_comment", side_effect=ValueError("x")) as post:
			self._run()

		post.assert_called_once()
		self.log_error.assert_not_called()
		(action,) = self._action("post_routing_comment")
		self.assertEqual((action["ok"], action["reason"]), (False, "ValueError"))
		self.assertIn("route post_routing_comment: ValueError", self._single_entry().error)
		self.assertEqual([call["task"] for call in self.gateway.calls], ["classify", "reason"])

	def test_changed_default_person_assigned_next_run(self):
		self._run()
		self.assertEqual(self._assigned_to(), [self.person])

		other = make_active_agent(self)
		self._configure(self.team, other)
		second = make_ticket(subject=f"{PREFIX}runner second ticket")
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		runner.run_for_ticket(second.name, "ticket_insert")

		self.assertEqual(self._assigned_to(second), [other])
		self.assertEqual(self._assigned_to(), [self.person])


class TestRoutingNoOverride(AssignTestBase):
	def test_existing_assignment_kept(self):
		earlier = make_active_agent(self)
		assign_to.add({"assign_to": [earlier], "doctype": "HD Ticket", "name": self.ticket.name})
		before_comments = self._comment_count()
		with patch.object(runner, "assign_owner") as assign:
			self._run()

		assign.assert_not_called()
		self.assertEqual(self._assigned_to(), [earlier])
		(action,) = self._action("assign_owner")
		self.assertEqual((action["ok"], action["reason"]), (False, f"phiếu đã có người được gán: {earlier}"))
		self.assertNotIn("rule", action)
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual(self._task_count(), 0)

	def test_rule_assignment_in_route_save_kept(self):
		member = make_active_agent(self)
		team = make_team(self, with_rule=True, rule_users=(member,))
		self._configure(team, self.person)
		before_comments = self._comment_count()
		self._run()

		# one ToDo in total, the rule's; the configured person got nothing and no request was posted
		self.assertEqual(self._assigned_to(), [member])
		self.assertEqual(self._notifications(self.person), 0)
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual(self._task_count(), 0)
		self.assertNotIn("assign", json.loads(self._single_entry().value_after))

	def test_human_classified_no_route_writes(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		before_comments = self._comment_count()
		with (
			patch.object(runner, "assign_owner") as assign,
			patch.object(runner, "post_routing_comment") as post,
		):
			self._run()

		assign.assert_not_called()
		post.assert_not_called()
		self.assertEqual(self._assigned_to(), [])
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual([a["tool"] for a in json.loads(self._single_entry().actions)], ["apply_route"])

	def test_switch_off_no_todo_no_task(self):
		set_agent_settings(auto_assign_enabled=0)
		before_comments = self._comment_count()
		with patch.object(runner, "assign_owner") as assign:
			self._run()

		assign.assert_not_called()
		self.assertEqual(self._assigned_to(), [])
		self.assertEqual(self._task_count(), 0)
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual([a["tool"] for a in json.loads(self._single_entry().actions)], ["apply_route"])

	def test_l0_no_todo_no_task(self):
		set_agent_settings(permission_level="L0")
		before_comments = self._comment_count()
		with patch.object(runner, "assign_owner") as assign:
			self._run()

		assign.assert_not_called()
		self.assertEqual(self._assigned_to(), [])
		self.assertEqual(self._task_count(), 0)
		self.assertEqual(self._comment_count(), before_comments)
		entry = self._single_entry()
		self.assertFalse(entry.actions)
		self.assertEqual(entry.predicted_assignee, self.person)


class TestRoutingTask(AssignTestBase):
	"""(u3): a C/D ticket the bot just gave to a person also gets one linked Task for that person (AC-13)."""

	def setUp(self):
		super().setUp()
		pin_agent_roles(self)
		self._configure_c(self.team, self.person)
		self._model_says_c()

	def _model_says_c(self):
		self.gateway.results = [make_model_result(text=CLASSIFY_C), make_model_result(stop_reason="end_turn")]

	def _configure_c(self, team, person):
		mapping = {"C": {"ticket_type": ROUTE_TYPE, "agent_group": team, "priority": "High"}}
		assignees = {cat: {"default": person, "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(
			category_mapping=json.dumps(mapping), routing_rules=make_routing_rules(assignees=assignees)
		)

	def _tasks(self):
		return frappe.get_all("Task", filters={"ai_ticket": self.ticket.name}, pluck="name")

	def _task_todos(self, user=None):
		filters = {"reference_type": "Task"}
		if user:
			filters["allocated_to"] = user
		return frappe.db.count("ToDo", filters)

	def test_c_ticket_one_linked_task_assigned(self):
		before_comments = self._comment_count()
		before_todos = self._task_todos()
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._run()

		(task,) = self._tasks()
		self.assertEqual(frappe.db.get_value("Task", task, "subject"), self.ticket.subject)
		self.assertEqual(
			frappe.get_all("ToDo", {"reference_type": "Task", "reference_name": task}, pluck="allocated_to"),
			[self.person],
		)
		self.assertEqual(self._task_todos(), before_todos + 1)
		self.assertEqual(self._assigned_to(), [self.person])
		(action,) = self._action("create_routed_task")
		self.assertEqual((action["doctype"], action["name"], action["ok"]), ("Task", task, True))
		entry = self._single_entry()
		self.assertEqual(json.loads(entry.value_after)["task"], task)
		self.assertEqual(json.loads(entry.value_after)["assign"], [self.person])
		self.assertEqual(
			[a["tool"] for a in json.loads(entry.actions)],
			["apply_route", "assign_owner", "create_routed_task"],
		)
		self.assertEqual(self._comment_count(), before_comments)
		(info,) = [c.args for c in logger.info.call_args_list if c.args[0].startswith("erp_ai route")]
		self.assertIn("assigned=%d task=%d comment=%d", info[0])
		self.assertEqual(info[3:], (1, 1, 1, 0, "ok"))

	def test_rerun_keeps_one_task(self):
		self._run()
		(task,) = self._tasks()
		(first,) = self._entries(entry_type="classify")
		self._model_says_c()
		self._run()

		self.assertEqual(self._tasks(), [task])
		self.assertEqual(self._task_todos(self.person), 1)
		(second,) = [e for e in self._entries(entry_type="classify") if e.name != first.name]
		self.assertEqual([a["tool"] for a in json.loads(second.actions)], ["apply_route", "assign_owner"])

	def test_existing_linked_task_no_new_task(self):
		earlier = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"{PREFIX}việc có sẵn",
				"ai_ticket": self.ticket.name,
				"description": "có sẵn",
			}
		).insert()
		before_todos = self._task_todos(self.person)
		with patch.object(runner, "create_routed_task") as create:
			self._run()

		create.assert_not_called()
		self.assertEqual(self._tasks(), [earlier.name])
		self.assertEqual(self._task_todos(self.person), before_todos)
		self.assertEqual(self._assigned_to(), [self.person])
		(action,) = self._action("create_routed_task")
		self.assertEqual(
			(action["doctype"], action["ok"], action["reason"]),
			("Task", False, "phiếu đã có Task liên kết"),
		)
		self.assertNotIn("task", json.loads(self._single_entry().value_after))

	def test_other_category_or_no_person_no_task(self):
		# category A: the decision does not ask for a Task
		self.gateway.results = [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]
		with patch.object(runner, "create_routed_task") as create:
			self._run()
		create.assert_not_called()
		self.assertEqual(self._assigned_to(), [self.person])
		self.assertEqual(self._tasks(), [])
		self.assertEqual(self._action("create_routed_task"), [])

		# category C but no valid person: nothing is assigned, so no Task
		self._configure_c(self.team, "")
		second = make_ticket(subject=f"{PREFIX}runner no person")
		self._model_says_c()
		with patch.object(runner, "create_routed_task") as create:
			runner.run_for_ticket(second.name, "ticket_insert")
		create.assert_not_called()
		self.assertEqual(frappe.db.count("Task", {"ai_ticket": second.name}), 0)
		(entry,) = frappe.get_all(LOG_DOCTYPE, {"ticket": second.name, "entry_type": "classify"}, ["actions"])
		self.assertEqual(
			[(a["tool"], a["ok"]) for a in json.loads(entry.actions)],
			[("apply_route", True), ("assign_owner", False), ("post_routing_comment", True)],
		)

	def test_sharing_disabled_no_task_one_comment(self):
		def write_then_raise(user, subject, classification, context):
			create_routed_task(user, subject, classification, context)
			raise PermissionError("chia sẻ tắt")

		before_comments = self._comment_count()
		before_todos = self._task_todos()
		with patch.object(runner, "create_routed_task", side_effect=write_then_raise) as create:
			self._run()

		create.assert_called_once()
		self.assertEqual(self._tasks(), [])
		self.assertEqual(self._task_todos(), before_todos)
		self.assertEqual(self._assigned_to(), [self.person])
		(action,) = self._action("create_routed_task")
		self.assertEqual((action["ok"], action["reason"]), (False, "PermissionError"))
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertIn("route create_routed_task: PermissionError", entry.error)
		self.assertNotIn(self.ticket.subject, entry.error)
		self.assertNotIn(self.ticket.subject, entry.actions)
		self.assertNotIn("task", json.loads(entry.value_after))
		self.assertEqual(self._comment_count(), before_comments + 1)
		self.assertIn(ASSIGN_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED), self._comment_text())

	def test_refused_task_without_exception_no_task_no_comment(self):
		refusal = {"ok": False, "reason": "thiếu quyền tạo Task"}
		before_comments = self._comment_count()
		before_todos = self._task_todos(self.person)
		with patch.object(runner, "create_routed_task", return_value=refusal) as create:
			self._run()

		create.assert_called_once()
		self.assertEqual(self._tasks(), [])
		self.assertEqual(self._task_todos(self.person), before_todos)
		self.assertEqual(self._assigned_to(), [self.person])
		(action,) = self._action("create_routed_task")
		self.assertEqual((action["ok"], action["reason"]), (False, "thiếu quyền tạo Task"))
		self.assertEqual(self._comment_count(), before_comments)
		self.assertNotIn("task", json.loads(self._single_entry().value_after))

	def test_preassigned_by_human_no_task_no_comment(self):
		earlier = make_active_agent(self)
		assign_to.add({"assign_to": [earlier], "doctype": "HD Ticket", "name": self.ticket.name})
		before_comments = self._comment_count()
		with patch.object(runner, "create_routed_task") as create:
			self._run()

		create.assert_not_called()
		self.assertEqual(self._tasks(), [])
		self.assertEqual(self._assigned_to(), [earlier])
		self.assertEqual(self._comment_count(), before_comments)
		self.assertEqual(
			[a["tool"] for a in json.loads(self._single_entry().actions)], ["apply_route", "assign_owner"]
		)

	def test_preassigned_by_rule_no_task_no_comment(self):
		member = make_active_agent(self)
		team = make_team(self, with_rule=True, rule_users=(member,))
		self._configure_c(team, self.person)
		before_comments = self._comment_count()
		with patch.object(runner, "create_routed_task") as create:
			self._run()

		create.assert_not_called()
		self.assertEqual(self._tasks(), [])
		self.assertEqual(self._assigned_to(), [member])
		self.assertEqual(self._comment_count(), before_comments)
		(action,) = self._action("assign_owner")
		self.assertEqual(action["reason"], f"phiếu đã có người được gán: {member}")


class TestRoutingLog(RoutingTestBase):
	"""AC-1/AC-2: the log entry carries the scores and the predicted assignee, at L0 and L1."""

	def test_l0_entry_has_scores_ticket_unchanged(self):
		agent = make_active_agent(self)
		assignees = {cat: {"default": agent if cat == "A" else "", "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(permission_level="L0", routing_rules=make_routing_rules(assignees=assignees))
		before = self._ticket_row()
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()

		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual((entry.predicted_complexity, entry.predicted_importance), (2, 3))
		self.assertEqual(entry.predicted_score_reason, SCORE_REASON)
		self.assertEqual(entry.predicted_assignee, agent)
		self.assertEqual(entry.applied, 0)
		scores = self._scores()
		self.assertEqual(scores.ai_complexity, 0)
		self.assertFalse(scores.ai_importance)
		self.assertFalse(scores.ai_score_reason)

	def test_l1_no_score_writes_zero_logs_no_score(self):
		self.gateway.results = [make_model_result(text=CLASSIFY_A), make_model_result(stop_reason="end_turn")]
		self._run()

		entry = self._single_entry()
		self.assertEqual((entry.predicted_complexity, entry.predicted_importance), (0, 0))
		self.assertEqual(entry.predicted_score_reason, "không có điểm")
		self.assertFalse(entry.predicted_assignee)

	def test_unusable_assignee_leaves_column_empty(self):
		assignees = {cat: {"default": "nobody@example.com", "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(permission_level="L0", routing_rules=make_routing_rules(assignees=assignees))
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()

		self.assertFalse(self._single_entry().predicted_assignee)

	def test_broken_routing_rules_error_in_log_run_continues(self):
		set_agent_settings(permission_level="L0", routing_rules="{không phải json")
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()

		entry = self._single_entry()
		self.assertIn("routing_rules không hợp lệ", entry.error)
		self.assertEqual(entry.predicted_category, "A")

	def test_valid_routing_rules_no_error(self):
		set_agent_settings(permission_level="L0", routing_rules=make_routing_rules())
		self.gateway.results = [make_model_result(text=CLASSIFY_SCORED)]
		self._run()

		self.assertFalse(self._single_entry().error)
