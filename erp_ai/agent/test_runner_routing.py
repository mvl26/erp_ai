import json
from unittest.mock import patch

import frappe

from erp_ai.agent import runner
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.routing import departments, load_routing_config
from erp_ai.agent.test_agent_runner import CLASSIFY_A, CLASSIFY_FIELDS, PREFIX, RunnerTestBase
from erp_ai.constants import AGENT_USER
from erp_ai.test_utils import make_active_agent, make_model_result, make_routing_rules, set_agent_settings

ROUTE_TYPE = f"{PREFIX}route-type"
ROUTE_TEAM = f"{PREFIX}route-team"

SCORE_FIELDS = ("ai_complexity", "ai_importance", "ai_score_reason")
SCORE_REASON = f"{PREFIX}lý do chấm điểm"
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
		after = json.loads(entry.value_after)
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
