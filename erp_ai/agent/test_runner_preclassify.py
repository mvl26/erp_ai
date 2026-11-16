import itertools
import json
from unittest.mock import patch

import frappe
from helpdesk.test_utils import make_ticket

from erp_ai.agent import policy, runner
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.test_agent_runner import PREFIX, requester_message
from erp_ai.agent.test_runner_routing import CLASSIFY_SCORED, ROUTE_TYPE, AssignTestBase
from erp_ai.agent.tools import write_ticket
from erp_ai.agent.tools.write_ticket import CREATED_LABELS_FIELD, REASON_HUMAN_FILLED
from erp_ai.constants import CLASSIFICATION_FIELDS, CLASSIFIED_BY_AI, LOG_DOCTYPE
from erp_ai.gateway import GatewayError
from erp_ai.test_utils import (
	keep_agent_settings,
	make_model_result,
	make_routing_rules,
	make_team,
	set_agent_settings,
)

MENTION = "comment_mention"
REPLY = "requester_reply"
# not the DocType default (5): the run reads the Setting
RUN_LIMIT = 7
BELOW_PCT = 40
HUMAN_TYPE = f"{PREFIX}preclassify-human-type"
HUMAN_PRIORITY = "Low"


def classify_below():
	return make_model_result(
		text=json.dumps({"dau_muc": "A", "do_tin_cay": "Thấp", "do_tin_cay_pct": BELOW_PCT, "ly_do": "x"})
	)


class PreclassifyTestBase(AssignTestBase):
	"""CHG-005 (Amendment 1 of ADR-037 QĐ 1, ADR-019 QĐ 2): a later run at L1+ on a ticket with no classify row with a
	result classifies and routes first, then reasons. Every switch a run depends on is set by the test."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)
		set_agent_settings(
			permission_level="L1",
			level_cap_a="L1",
			act_now_enabled=0,
			code_change_enabled=0,
			record_tools_enabled=0,
			unrestricted_enabled=0,
			reply_enabled=0,
			kb_draft_enabled=0,
			monthly_budget_usd=1000,
			max_runs_per_ticket_per_day=RUN_LIMIT,
			confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD,
			excluded_teams="",
		)
		# the classify rows are read for real: "unclassified" is decided on this ticket's own rows
		self.latest_classification.side_effect = self.real_latest_classification

	def _model_says(self, *results):
		self.gateway.calls.clear()
		self.gateway.results = list(results) or [
			make_model_result(text=CLASSIFY_SCORED),
			make_model_result(stop_reason="end_turn"),
		]

	def _tasks(self):
		return [call["task"] for call in self.gateway.calls]

	def _result_rows(self, ticket=None):
		return frappe.get_all(
			LOG_DOCTYPE,
			filters={
				"ticket": ticket or self.ticket.name,
				"entry_type": "classify",
				"predicted_category": ("is", "set"),
			},
			fields=["*"],
			order_by="creation asc",
		)

	def _reply_run(self, ticket=None):
		ticket = ticket or self.ticket.name
		requester = f"{PREFIX.lower()}requester-{frappe.generate_hash(length=8).lower()}@example.com"
		frappe.db.set_value("HD Ticket", ticket, "raised_by", requester, update_modified=False)
		message = requester_message(
			ticket, frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-30)
		)
		runner.run_for_ticket(ticket, REPLY, communication_name=message)


class TestPreclassify(PreclassifyTestBase):
	"""AC-1, NFR-1: the run classifies first, routes as on insert at the threshold, then reasons, in the same run."""

	def test_ticket_43209_case_mention_classifies_routes_then_reasons(self):
		# ticket 43209: its insert run was lost; "@ai chạy đi" must leave a classify row and fill Team/Ticket type
		row = frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True)
		self.assertFalse(row.ticket_type)
		self.assertNotEqual(row.agent_group, self.team)
		self._model_says()
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "reason"])
		(entry,) = self._result_rows()
		self.assertEqual((entry.trigger, entry.applied), (MENTION, 1))
		ticket = frappe.db.get_value(
			"HD Ticket", self.ticket.name, ["ticket_type", "agent_group", "ai_classified_by"], as_dict=True
		)
		self.assertEqual((ticket.ticket_type, ticket.agent_group), (ROUTE_TYPE, self.team))
		self.assertEqual(ticket.ai_classified_by, CLASSIFIED_BY_AI)
		self.assertEqual(self._assigned_to(), [self.person])
		(reason,) = self._entries(entry_type="reason")
		self.assertEqual(reason.run_id, entry.run_id)
		self.assertEqual(write_ticket.count_guidance(self.ticket.name), 1)

	def test_each_trigger_classifies_once_and_counts_one_run(self):
		for trigger in (MENTION, REPLY):
			with self.subTest(trigger):
				ticket = make_ticket(subject=f"{PREFIX}preclassify {trigger}").name
				self._model_says()
				if trigger == REPLY:
					self._reply_run(ticket)
				else:
					runner.run_for_ticket(ticket, trigger)

				self.assertEqual(self._tasks(), ["classify", "reason"])
				(entry,) = self._result_rows(ticket)
				self.assertEqual((entry.trigger, entry.applied), (trigger, 1))
				self.assertEqual(frappe.db.get_value("HD Ticket", ticket, "agent_group"), self.team)
				self.assertEqual(policy.runs_today(ticket), 1)

	def test_error_row_alone_is_unclassified(self):
		# an earlier classify row without a result (a gateway error) does not count as classified
		write_entry(
			ticket=self.ticket.name,
			run_id=f"{PREFIX}failed-insert",
			entry_type="classify",
			trigger="ticket_insert",
			turn=0,
			error="all_keys_failed status=401",
			stop_reason="gateway_error",
		)
		self._model_says()
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "reason"])
		self.assertEqual(len(self._result_rows()), 1)


class TestNoPreclassify(PreclassifyTestBase):
	"""AC-2, NFR-2: no classification first for a knowledge draft, at L0, on a ticket the person typed in full, or when
	the ticket already has a classify row with a result at the threshold."""

	def test_kb_draft_run_makes_no_classify_call(self):
		set_agent_settings(kb_draft_enabled=1)
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{"status": "Closed", "resolution_details": f"{PREFIX}đã sửa máy in"},
			update_modified=False,
		)
		self._model_says(make_model_result(stop_reason="end_turn"))
		with patch.object(runner, "_kb_draft_skip", return_value=None):
			self._run("kb_draft")

		self.assertNotIn("classify", self._tasks())
		self.assertEqual(self._result_rows(), [])

	def test_level_l0_skips_without_a_model_call(self):
		set_agent_settings(permission_level="L0")
		self._model_says()
		self._run(MENTION)

		self.assertEqual(self._tasks(), [])
		self.assertEqual([(e.entry_type, e.stop_reason) for e in self._entries()], [("skip", "level_L0")])

	def test_person_typed_all_three_makes_no_classify_call(self):
		if not frappe.db.exists("HD Ticket Type", HUMAN_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": HUMAN_TYPE}).insert()
		values = {"ticket_type": HUMAN_TYPE, "agent_group": self.team, "priority": HUMAN_PRIORITY}
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{**values, CREATED_LABELS_FIELD: json.dumps(values, sort_keys=True)},
		)
		self._model_says(make_model_result(stop_reason="end_turn"))
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["reason"])
		self.assertEqual(self._result_rows(), [])
		self.assertEqual(
			dict(frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True)),
			values,
		)

	def test_ticket_with_a_result_at_threshold_is_not_classified_again(self):
		self._model_says()
		self._run(MENTION)
		self._model_says(make_model_result(stop_reason="end_turn"))
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["reason"])
		self.assertEqual(len(self._result_rows()), 1)

	def test_below_threshold_result_classifies_once_per_run(self):
		# ADR-037 QĐ 1 unchanged: the second run sees a result below the threshold and classifies again, once
		self._model_says(classify_below(), make_model_result(stop_reason="end_turn"))
		self._run(MENTION)
		self._model_says(classify_below(), make_model_result(stop_reason="end_turn"))
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "reason"])
		self.assertEqual(len(self._result_rows()), 2)


class TestPreclassifyTypedFields(PreclassifyTestBase):
	"""AC-3: a person typed some of the three fields: those keep the person's value, the empty ones are routed, the
	classify row names the typed set."""

	def setUp(self):
		super().setUp()
		if not frappe.db.exists("HD Ticket Type", HUMAN_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": HUMAN_TYPE}).insert()
		self.typed_values = {"ticket_type": HUMAN_TYPE, "agent_group": self.team, "priority": HUMAN_PRIORITY}
		# the route's values differ from every typed value
		self.routed = {"ticket_type": ROUTE_TYPE, "agent_group": self._other_team(), "priority": "Urgent"}

	def _other_team(self):
		team = make_team(self)
		mapping = {"A": {"ticket_type": ROUTE_TYPE, "agent_group": team, "priority": "High"}}
		assignees = {cat: {"default": self.person, "prefixes": {}} for cat in "ABCF"}
		set_agent_settings(
			category_mapping=json.dumps(mapping), routing_rules=make_routing_rules(assignees=assignees)
		)
		return team

	def test_six_partial_subsets(self):
		subsets = [
			subset for size in (1, 2) for subset in itertools.combinations(CLASSIFICATION_FIELDS, size)
		]
		self.assertEqual(len(subsets), 6)
		for typed in subsets:
			with self.subTest(typed=typed):
				values = {field: self.typed_values[field] for field in typed}
				ticket = make_ticket(subject=f"{PREFIX}preclassify typed {' '.join(typed)}").name
				frappe.db.set_value(
					"HD Ticket",
					ticket,
					{**values, CREATED_LABELS_FIELD: json.dumps(values, ensure_ascii=False, sort_keys=True)},
				)
				self._model_says()
				runner.run_for_ticket(ticket, MENTION)

				self.assertEqual(self._tasks(), ["classify", "reason"])
				row = frappe.db.get_value("HD Ticket", ticket, CLASSIFICATION_FIELDS, as_dict=True)
				expected = {f: values[f] if f in typed else self.routed[f] for f in CLASSIFICATION_FIELDS}
				self.assertEqual(dict(row), expected)
				(entry,) = self._result_rows(ticket)
				self.assertEqual(entry.applied, 1)
				self.assertEqual(json.loads(entry.created_labels), values)
				kept = [
					i["field"] for i in json.loads(entry.skipped_fields) if i["reason"] == REASON_HUMAN_FILLED
				]
				self.assertEqual(kept, list(typed))


class TestPreclassifyOnce(PreclassifyTestBase):
	"""AC-4: two runs, one after the other or interleaved, route the ticket once and post one guidance comment; below the
	threshold the run only asks; an excluded team stops the run as on insert."""

	def _assert_routed_once(self):
		self.assertEqual([row.applied for row in self._result_rows()].count(1), 1)
		self.assertLessEqual(len(self._assigned_to()), 1)
		self.assertLessEqual(self._task_count(), 1)
		self.assertEqual(write_ticket.count_guidance(self.ticket.name), 1)

	def test_two_sequential_runs(self):
		self._model_says()
		self._run(MENTION)
		self._model_says(make_model_result(stop_reason="end_turn"))
		self._run(MENTION)

		self.assertEqual(len(self._result_rows()), 1)
		self._assert_routed_once()

	def test_second_run_during_the_first_ones_classification(self):
		# both runs start with no classify row with a result; the second one runs whole while the first waits on its
		# classification call, so the first one's route finds the ticket routed
		nested = []

		def second_run(task, kwargs):
			if task == "classify" and not nested:
				nested.append(True)
				results = self.gateway.results
				self.gateway.results = [
					make_model_result(text=CLASSIFY_SCORED),
					make_model_result(stop_reason="end_turn"),
				]
				runner.run_for_ticket(self.ticket.name, MENTION)
				self.gateway.results = results

		self._model_says()
		self.gateway.on_call = second_run
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "classify", "reason", "reason"])
		self.assertEqual(len(self._result_rows()), 2)
		self._assert_routed_once()
		self.log_error.assert_not_called()

	def test_below_threshold_asks_only_no_route(self):
		before = frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True)
		self._model_says(classify_below(), make_model_result(stop_reason="end_turn"))
		with patch.object(runner, "_route", wraps=runner._route) as route:
			self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "reason"])
		route.assert_not_called()
		(entry,) = self._result_rows()
		self.assertEqual((entry.predicted_confidence_pct, entry.applied), (BELOW_PCT, 0))
		self.assertEqual(
			frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True), before
		)
		self.assertEqual(write_ticket.count_guidance(self.ticket.name), 0)

	def test_excluded_team_stops_before_reasoning(self):
		# the classification names a department called like an excluded team (AC-9 (b)): the run stops after its row
		set_agent_settings(excluded_teams=self.team)
		before = frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True)
		answer = {
			"dau_muc": "A",
			"do_tin_cay": "Cao",
			"do_tin_cay_pct": 90,
			"ly_do": "x",
			"bo_phan": self.team,
		}
		self._model_says(
			make_model_result(text=json.dumps(answer)), make_model_result(stop_reason="end_turn")
		)
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify"])
		(entry,) = self._result_rows()
		self.assertEqual((entry.applied, entry.stop_reason), (0, policy.EXCLUDED_BY_CLASSIFICATION))
		self.assertEqual(
			frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFICATION_FIELDS, as_dict=True), before
		)
		self.assertEqual(self._assigned_to(), [])


class TestPreclassifyFailure(PreclassifyTestBase):
	"""AC-5, NFR-1: a gateway error stops the run as on insert; an unparseable answer lets it go on without a result;
	neither counts as classified, so the next run classifies; nothing is raised out of the job."""

	def _run_failed_notices(self):
		return frappe.get_all(
			"Comment",
			filters={
				**runner.authority.ticket_comment_filters(self.ticket.name),
				"content": ["like", f"{write_ticket.NOTICE_PREFIXES['run_failed']}%"],
			},
			pluck="name",
		)

	def test_gateway_error_stops_then_next_run_classifies(self):
		self._model_says(GatewayError("all_keys_failed", status=401, credential_label=f"{PREFIX}key"))
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify"])
		self.log_error.assert_not_called()
		(failed,) = self._entries(entry_type="classify")
		self.assertEqual((failed.stop_reason, failed.trigger), ("gateway_error", MENTION))
		self.assertEqual(self._entries(entry_type="reason"), [])
		self.assertEqual(len(self._run_failed_notices()), 1)

		self._model_says()
		self._run(MENTION)
		self.assertEqual(self._tasks(), ["classify", "reason"])
		(entry,) = self._result_rows()
		self.assertEqual(entry.applied, 1)

	def test_unparseable_goes_on_then_next_run_classifies(self):
		self._model_says(make_model_result(text="không phải JSON"), make_model_result(stop_reason="end_turn"))
		self._run(MENTION)

		self.assertEqual(self._tasks(), ["classify", "reason"])
		self.log_error.assert_not_called()
		(row,) = self._entries(entry_type="classify")
		self.assertEqual(row.stop_reason, "unparseable")
		self.assertEqual(self._result_rows(), [])

		self._model_says()
		self._run(MENTION)
		self.assertEqual(self._tasks(), ["classify", "reason"])
		self.assertEqual(len(self._result_rows()), 1)
		self.assertEqual(policy.runs_today(self.ticket.name), 2)
