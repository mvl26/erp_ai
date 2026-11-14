import json
from datetime import date, datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import kpi
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE
from erp_ai.test_utils import keep_agent_settings

# Weeks long before any real ticket on the shared site, one per test, so "open at the week end" (A-D2)
# sees only the tickets a test makes.
WEEK_KPI1 = date(2001, 1, 1)
WEEK_KPI2 = date(2001, 2, 5)
WEEK_KPI3 = date(2001, 3, 5)
WEEK_EMPTY = date(2001, 4, 2)
WEEK_NO_RESPONSE = date(2001, 5, 7)
KPI_1_TO_3_KEYS = {
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
}
CUSTOMER = "erpai-test-kpi-customer@example.com"
HUMAN_AGENT = "erpai-test-kpi-human@example.com"
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
		self.settings = frappe.get_cached_doc("ERP AI Setting")

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

		self.assertEqual(set(result), KPI_1_TO_3_KEYS)
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
		# decoys: resolved before `we`; created at `we`
		_ticket(ws, resolution_date=we - timedelta(seconds=1), ticket_type=None)
		_ticket(we, ticket_type=None)

		result = kpi.compute_week(WEEK_KPI2, self.settings)

		self.assertEqual(result["complete_fields_sample"], 4)
		self.assertEqual(result["complete_fields_pct"], 50.0)

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
		# decoys outside [ws, we): bot-only closures resolved at `we` and just before `ws`
		for resolution in (we, ws - timedelta(seconds=1)):
			decoy = _ticket(ws - timedelta(days=1), resolution_date=resolution, raised_by=CUSTOMER)
			_log(decoy, [_close_action(decoy)])

		result = kpi.compute_week(WEEK_KPI3, self.settings)

		self.assertEqual(result["closed_sample"], 8)
		self.assertEqual(result["closed_without_human_pct"], 25.0)

	def test_zero_sample_none(self):
		result = kpi.compute_week(WEEK_EMPTY, self.settings)

		self.assertEqual(set(result), KPI_1_TO_3_KEYS)
		for field in (
			"first_response_median_min",
			"first_response_within_15_pct",
			"first_response_within_5_pct",
			"complete_fields_pct",
			"closed_without_human_pct",
		):
			self.assertIsNone(result[field], field)
		for field in ("first_response_sample", "complete_fields_sample", "closed_sample"):
			self.assertEqual(result[field], 0, field)

		# one ticket in the week, never answered: no median, rates are 0 (not answered = missed)
		_ticket(_start(WEEK_NO_RESPONSE) + timedelta(hours=1))
		result = kpi.compute_week(WEEK_NO_RESPONSE, self.settings)
		self.assertIsNone(result["first_response_median_min"])
		self.assertEqual(result["first_response_within_15_pct"], 0.0)
		self.assertEqual(result["first_response_within_5_pct"], 0.0)
		self.assertEqual(result["first_response_sample"], 1)
