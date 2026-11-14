import json
from datetime import date, datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import kpi
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

# Weeks long before any real ticket on the shared site, one per test, so "open at the week end" (A-D2)
# sees only the tickets a test makes.
WEEK_KPI1 = date(2001, 1, 1)
WEEK_KPI2 = date(2001, 2, 5)
WEEK_KPI3 = date(2001, 3, 5)
WEEK_EMPTY = date(2001, 4, 2)
WEEK_NO_RESPONSE = date(2001, 5, 7)
WEEK_KPI4 = date(2001, 6, 4)
WEEK_KPI5 = date(2001, 7, 2)
WEEK_KPI6 = date(2001, 8, 6)
KPI_KEYS = {
	"week_start",
	"week_end",
	"first_response_median_min",
	"first_response_within_15_pct",
	"first_response_within_5_pct",
	"first_response_sample",
	"complete_fields_pct",
	"complete_fields_sample",
	"closed_without_human_pct",
	"closed_sample",
	"b_resolution_avg_hours",
	"b_resolution_sample",
	"c_task_in_3_days_pct",
	"c_task_sample",
	"stale_over_5_days",
	"stale_over_7_days",
}
CUSTOMER = "erpai-test-kpi-customer@example.com"
HUMAN_AGENT = "erpai-test-kpi-human@example.com"
TYPE_A = "ERPAI-TEST kpi A"
TYPE_B = "ERPAI-TEST kpi B"
TYPE_C = "ERPAI-TEST kpi C"
TYPE_UNMAPPED = "ERPAI-TEST kpi unmapped"
# D shares B's ticket type and comes first in the JSON: B still wins (earlier in CATEGORIES).
CATEGORY_MAPPING = {
	"D": {"ticket_type": TYPE_B},
	"A": {"ticket_type": TYPE_A},
	"B": {"ticket_type": TYPE_B},
	"C": {"ticket_type": TYPE_C},
}
FULL_FIELDS = {"ticket_type": "ERPAI-TEST type", "agent_group": "ERPAI-TEST team", "priority": "Medium"}


def _start(week: date) -> datetime:
	return datetime.combine(week, datetime.min.time())


def _ticket(creation: datetime, **values) -> str:
	"""A ticket whose dates and fields are set straight in the database; side records of the insert removed."""
	name = make_ticket(subject="ERPAI-TEST kpi").name
	for doctype, field in (("Comment", "reference_name"), ("Communication", "reference_name")):
		frappe.db.delete(doctype, {"reference_doctype": "HD Ticket", field: name})
	frappe.db.delete("ToDo", {"reference_type": "HD Ticket", "reference_name": name})
	frappe.db.delete(LOG_DOCTYPE, {"ticket": name})
	row = {"first_responded_on": None, "resolution_date": None, **FULL_FIELDS, **values}
	row["creation"] = creation
	frappe.db.set_value("HD Ticket", name, row, update_modified=False)
	return name


def _insert_as(doc, owner: str) -> None:
	"""Insert without hooks, then set `owner` (the insert writes the session user there)."""
	doc.db_insert()
	frappe.db.set_value(doc.doctype, doc.name, "owner", owner, update_modified=False)


def _comment(ticket: str, owner: str, comment_type: str = "Comment") -> None:
	doc = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": comment_type,
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"content": "ERPAI-TEST",
		}
	)
	_insert_as(doc, owner)


def _communication(ticket: str, owner: str, sent_or_received: str = "Sent") -> None:
	doc = frappe.get_doc(
		{
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": sent_or_received,
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"subject": "ERPAI-TEST",
			"content": "ERPAI-TEST",
		}
	)
	_insert_as(doc, owner)


def _todo(ticket: str, assigned_by: str) -> None:
	doc = frappe.get_doc(
		{
			"doctype": "ToDo",
			"status": "Open",
			"allocated_to": HUMAN_AGENT,
			"reference_type": "HD Ticket",
			"reference_name": ticket,
			"description": "ERPAI-TEST",
			"assigned_by": assigned_by,
		}
	)
	_insert_as(doc, assigned_by)


def _task(ticket: str, creation: datetime) -> None:
	doc = frappe.get_doc({"doctype": "Task", "subject": "ERPAI-TEST kpi", "ai_ticket": ticket})
	doc.db_insert()
	frappe.db.set_value("Task", doc.name, "creation", creation, update_modified=False)


def _log(ticket: str, actions: list[dict]) -> None:
	frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"ticket": ticket,
			"run_id": "ERPAI-TEST-run",
			"entry_type": "reason",
			"trigger": "ticket_insert",
			"turn": 1,
			"actions": json.dumps(actions),
		}
	).db_insert()


def _close_action(ticket: str, status: str = "Resolved", ok: bool = True) -> dict:
	return {
		"tool": "resolve_on_tasks_done",
		"doctype": "HD Ticket",
		"name": ticket,
		"ok": ok,
		"value_before": {"status": "Open"},
		"value_after": {"status": status},
	}


def _bot_only_trail(ticket: str) -> None:
	"""Every agent-side action by the bot; the requester's own comment and email do not count."""
	_comment(ticket, AGENT_USER)
	_comment(ticket, CUSTOMER)
	_comment(ticket, HUMAN_AGENT, comment_type="Info")
	_communication(ticket, AGENT_USER)
	_communication(ticket, CUSTOMER, sent_or_received="Received")
	_todo(ticket, AGENT_USER)


class TestKpi(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)
		set_agent_settings(category_mapping=json.dumps(CATEGORY_MAPPING))
		self.settings = frappe.get_single("ERP AI Setting")

	def test_kpi1_median_and_rates(self):
		ws = _start(WEEK_KPI1)
		we = ws + timedelta(days=7)
		# in the week: 3, 5, 15, 40 minutes and one never answered
		for created, minutes in (
			(ws, 3),
			(ws + timedelta(days=2), 5),
			(ws + timedelta(days=3, hours=4), 15),
			(we - timedelta(minutes=50), 40),
		):
			_ticket(created, first_responded_on=created + timedelta(minutes=minutes))
		_ticket(ws + timedelta(days=4))
		# decoys: created just before the week and exactly at its end
		for created in (ws - timedelta(seconds=1), we):
			_ticket(created, first_responded_on=created + timedelta(minutes=1))

		result = kpi.compute_week(WEEK_KPI1, self.settings)

		self.assertEqual(set(result), KPI_KEYS)
		self.assertEqual(result["week_start"], WEEK_KPI1)
		self.assertEqual(result["week_end"], WEEK_KPI1 + timedelta(days=6))
		self.assertEqual(result["first_response_median_min"], 10.0)
		self.assertEqual(result["first_response_within_15_pct"], 60.0)
		self.assertEqual(result["first_response_within_5_pct"], 40.0)
		self.assertEqual(result["first_response_sample"], 5)

	def test_kpi2_open_at_week_end(self):
		ws = _start(WEEK_KPI2)
		we = ws + timedelta(days=7)
		# open at `we` and complete: created the week before, never resolved
		_ticket(ws - timedelta(days=3))
		# open at `we` and complete: resolved after the week end
		_ticket(ws + timedelta(days=1), resolution_date=we + timedelta(days=1))
		# open at `we` (resolved exactly at `we`), no team
		_ticket(ws + timedelta(days=2), resolution_date=we, agent_group=None)
		# open at `we`, no priority
		_ticket(ws + timedelta(days=5), priority=None)
		# open at `we`, no ticket type
		_ticket(ws + timedelta(days=6), ticket_type=None)
		# decoys: resolved before `we`; created at `we`
		_ticket(ws, resolution_date=we - timedelta(seconds=1), ticket_type=None)
		_ticket(we, ticket_type=None)

		result = kpi.compute_week(WEEK_KPI2, self.settings)

		self.assertEqual(result["complete_fields_sample"], 5)
		self.assertEqual(result["complete_fields_pct"], 40.0)

	def test_kpi3_bot_only_closures(self):
		ws = _start(WEEK_KPI3)
		we = ws + timedelta(days=7)
		resolved = ws + timedelta(days=2)

		def closed(**values):
			return _ticket(ws - timedelta(days=1), resolution_date=resolved, raised_by=CUSTOMER, **values)

		# counts: bot-only trail, closed by the bot (Resolved)
		bot_resolved = closed()
		_bot_only_trail(bot_resolved)
		_log(bot_resolved, [_close_action(bot_resolved)])
		# counts: nothing but the bot's close (Closed)
		bot_closed = closed()
		_log(bot_closed, [_close_action(bot_closed, status="Closed")])
		# does not count: a human agent comment
		human_comment = closed()
		_bot_only_trail(human_comment)
		_comment(human_comment, HUMAN_AGENT)
		_log(human_comment, [_close_action(human_comment)])
		# does not count: a human reply sent out
		human_reply = closed()
		_bot_only_trail(human_reply)
		_communication(human_reply, HUMAN_AGENT)
		_log(human_reply, [_close_action(human_reply)])
		# does not count: a human assignment
		human_assign = closed()
		_bot_only_trail(human_assign)
		_todo(human_assign, HUMAN_AGENT)
		_log(human_assign, [_close_action(human_assign)])
		# does not count: bot-only trail but no bot close in the log
		no_bot_close = closed()
		_bot_only_trail(no_bot_close)
		_log(no_bot_close, [{"tool": "post_comment", "doctype": "Comment", "name": "x", "ok": True}])
		# does not count: the bot close failed
		failed_close = closed()
		_bot_only_trail(failed_close)
		_log(failed_close, [_close_action(failed_close, ok=False)])
		# does not count: the bot's ok action set another status
		other_status = closed()
		_bot_only_trail(other_status)
		_log(other_status, [_close_action(other_status, status="Replied")])
		# does not count: the bot's ok close action is on another doctype
		other_doctype = closed()
		_bot_only_trail(other_doctype)
		_log(other_doctype, [{**_close_action(other_doctype, status="Closed"), "doctype": "ToDo"}])
		# does not count: the bot's ok close action is on another ticket
		other_ticket = closed()
		_bot_only_trail(other_ticket)
		_log(other_ticket, [_close_action(bot_closed)])
		# decoys outside [ws, we): bot-only closures resolved at `we` and just before `ws`
		for resolution in (we, ws - timedelta(seconds=1)):
			decoy = _ticket(ws - timedelta(days=1), resolution_date=resolution, raised_by=CUSTOMER)
			_log(decoy, [_close_action(decoy)])

		result = kpi.compute_week(WEEK_KPI3, self.settings)

		self.assertEqual(result["closed_sample"], 10)
		self.assertEqual(result["closed_without_human_pct"], 20.0)

	def test_zero_sample_none(self):
		result = kpi.compute_week(WEEK_EMPTY, self.settings)

		self.assertEqual(set(result), KPI_KEYS)
		for field in (
			"first_response_median_min",
			"first_response_within_15_pct",
			"first_response_within_5_pct",
			"complete_fields_pct",
			"closed_without_human_pct",
			"b_resolution_avg_hours",
			"c_task_in_3_days_pct",
		):
			self.assertIsNone(result[field], field)
		for field in (
			"first_response_sample",
			"complete_fields_sample",
			"closed_sample",
			"b_resolution_sample",
			"c_task_sample",
			"stale_over_5_days",
			"stale_over_7_days",
		):
			self.assertEqual(result[field], 0, field)

		# one ticket in the week, never answered: no median, rates are 0 (not answered = missed)
		_ticket(_start(WEEK_NO_RESPONSE) + timedelta(hours=1))
		result = kpi.compute_week(WEEK_NO_RESPONSE, self.settings)
		self.assertIsNone(result["first_response_median_min"])
		self.assertEqual(result["first_response_within_15_pct"], 0.0)
		self.assertEqual(result["first_response_within_5_pct"], 0.0)
		self.assertEqual(result["first_response_sample"], 1)

	def test_kpi4_b_resolution_hours(self):
		ws = _start(WEEK_KPI4)
		we = ws + timedelta(days=7)
		# category B resolved in [ws, we): 2 h, 30 h, 10 h -> mean 14 h
		for resolved, hours in ((ws, 2), (ws + timedelta(days=3), 30), (we - timedelta(seconds=1), 10)):
			_ticket(resolved - timedelta(hours=hours), resolution_date=resolved, ticket_type=TYPE_B)
		# decoys: B resolved at `we` and just before `ws`; B never resolved
		for resolved in (we, ws - timedelta(seconds=1)):
			_ticket(resolved - timedelta(hours=100), resolution_date=resolved, ticket_type=TYPE_B)
		_ticket(ws + timedelta(days=1), ticket_type=TYPE_B)
		# decoys: resolved in the week but category A, C, an unmapped type, no type
		for ticket_type in (TYPE_A, TYPE_C, TYPE_UNMAPPED, None):
			_ticket(
				ws - timedelta(hours=100), resolution_date=ws + timedelta(days=1), ticket_type=ticket_type
			)

		result = kpi.compute_week(WEEK_KPI4, self.settings)

		self.assertEqual(result["b_resolution_sample"], 3)
		self.assertEqual(result["b_resolution_avg_hours"], 14.0)

	def test_kpi5_task_within_72h_edge(self):
		ws = _start(WEEK_KPI5)
		we = ws + timedelta(days=7)
		window_start, window_end = ws - timedelta(days=3), we - timedelta(days=3)
		hours_72 = timedelta(hours=72)
		# counts: first moment of the window, its Task at exactly 72 h
		_task(_ticket(window_start, ticket_type=TYPE_C), window_start + hours_72)
		# counts: created the day before the week, inside the shifted window (A-D4), a fast Task
		created = ws - timedelta(days=1)
		_task(_ticket(created, ticket_type=TYPE_C), created + timedelta(hours=1))
		# counts: one late Task, one early Task
		created = ws + timedelta(days=1)
		both = _ticket(created, ticket_type=TYPE_C)
		_task(both, created + timedelta(hours=80))
		_task(both, created + timedelta(hours=1))
		# does not count: its only Task at 72 h + 1 s
		_task(_ticket(ws, ticket_type=TYPE_C), ws + hours_72 + timedelta(seconds=1))
		# does not count: no Task of its own (a fast Task is linked to another ticket, outside the sample)
		created = ws + timedelta(days=2)
		_ticket(created, ticket_type=TYPE_C)
		_task(_ticket(created, ticket_type=TYPE_A), created + timedelta(hours=1))
		# decoys: C just before the window and at its end, a fast Task each
		for created in (window_start - timedelta(seconds=1), window_end):
			_task(_ticket(created, ticket_type=TYPE_C), created + timedelta(hours=1))
		# decoys: in the window with a fast Task but category B, an unmapped type, no type
		created = ws + timedelta(days=1)
		for ticket_type in (TYPE_B, TYPE_UNMAPPED, None):
			_task(_ticket(created, ticket_type=ticket_type), created + timedelta(hours=1))

		result = kpi.compute_week(WEEK_KPI5, self.settings)

		self.assertEqual(result["c_task_sample"], 5)
		self.assertEqual(result["c_task_in_3_days_pct"], 60.0)

	def test_kpi6_stale_edges(self):
		we = _start(WEEK_KPI6) + timedelta(days=7)
		five, seven = timedelta(days=5), timedelta(days=7)
		# age exactly 5 days: not counted
		_ticket(we - five)
		# over 5 days only
		_ticket(we - five - timedelta(seconds=1))
		# age exactly 7 days: over 5, not over 7
		_ticket(we - seven, ticket_type=TYPE_B)
		# over 7 days, any category
		_ticket(we - seven - timedelta(seconds=1), ticket_type=None)
		# still open at `we` (resolved exactly at `we`), over 7 days
		_ticket(we - timedelta(days=10), resolution_date=we)
		# decoys: resolved just before `we`; created at `we`
		_ticket(we - timedelta(days=10), resolution_date=we - timedelta(seconds=1))
		_ticket(we)

		result = kpi.compute_week(WEEK_KPI6, self.settings)

		self.assertEqual(result["stale_over_5_days"], 4)
		self.assertEqual(result["stale_over_7_days"], 2)
