import json
from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import daily_report
from erp_ai.agent.ops_data import BA_NOTE_MARKER
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE
from erp_ai.test_utils import keep_agent_settings, make_routing_rules, set_agent_settings

# Anchors long before any real ticket on the shared site, one per test, so "open" and "created in the
# window" see only the tickets a test makes.
ANCHOR_TWELVE = datetime(2002, 3, 11, 8, 0)
ANCHOR_DE = datetime(2002, 4, 8, 8, 0)
ANCHOR_HOURS = datetime(2002, 5, 6, 8, 0)
REPORT_KEYS = {
	"new_by_category_priority",
	"new_list",
	"due_soon",
	"overdue",
	"response_overdue",
	"c_missing_ba_note",
	"cd_missing_task",
	"de_progress",
}
HUMAN_AGENT = "erpai-test-daily-human@example.com"
TYPE_PREFIX = "ERPAI-TEST daily "
TYPE_UNMAPPED = "ERPAI-TEST daily unmapped"
CATEGORY_MAPPING = {category: {"ticket_type": f"{TYPE_PREFIX}{category}"} for category in "ABCDEF"}
# A real Datetime Custom Field erp_ai installs on HD Ticket (test_install pins it): no test creates a field.
DUE_FIELD = "ai_updated_at"


def _ticket(label: str, creation: datetime, category: str | None, **values) -> str:
	"""A ticket whose dates and fields are set straight in the database; side records of the insert removed."""
	name = make_ticket(subject=f"ERPAI-TEST daily {label}").name
	for doctype in ("Comment", "Communication"):
		frappe.db.delete(doctype, {"reference_doctype": "HD Ticket", "reference_name": name})
	frappe.db.delete("ToDo", {"reference_type": "HD Ticket", "reference_name": name})
	frappe.db.delete(LOG_DOCTYPE, {"ticket": name})
	frappe.db.delete("Task", {"ai_ticket": name})
	row = {
		"ticket_type": f"{TYPE_PREFIX}{category}" if category else TYPE_UNMAPPED,
		"priority": "Medium",
		"status": "Open",
		"status_category": "Open",
		"agent_group": None,
		"first_responded_on": creation + timedelta(minutes=1),
		"resolution_by": None,
		"resolution_date": None,
		DUE_FIELD: None,
		**values,
	}
	row["creation"] = creation
	frappe.db.set_value("HD Ticket", name, row, update_modified=False)
	return name


def _resolved(on: datetime) -> dict:
	return {"status": "Resolved", "status_category": "Resolved", "resolution_date": on}


def _comment(ticket: str, owner: str, content: str) -> None:
	doc = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"content": content,
		}
	)
	doc.db_insert()
	frappe.db.set_value("Comment", doc.name, "owner", owner, update_modified=False)


def _task(ticket: str) -> None:
	frappe.get_doc({"doctype": "Task", "subject": "ERPAI-TEST daily", "ai_ticket": ticket}).db_insert()


def _names(rows: list[dict], mine: set[str]) -> list[str]:
	"""Names of the report rows that belong to this test, in report order."""
	return [row["name"] for row in rows if row["name"] in mine]


def _item(name: str, category: str, priority: str = "Medium") -> dict:
	return {
		"name": name,
		"subject": frappe.db.get_value("HD Ticket", name, "subject"),
		"category": category,
		"priority": priority,
		"excluded": False,
	}


class TestBuild(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)
		set_agent_settings(
			category_mapping=json.dumps(CATEGORY_MAPPING),
			routing_rules=make_routing_rules(),
			field_due_date=DUE_FIELD,
			due_reminder_hours=24,
			ba_note_due_hours=24,
			task_due_days=3,
		)

	def test_twelve_tickets_sections(self):
		anchor = ANCHOR_TWELVE
		start = anchor - timedelta(hours=24)
		t = {}
		# 1. C created exactly at the window start: new (inclusive), BA note missing (exactly 24 h counts)
		t["c_new_start"] = _ticket("c_new_start", start, "C", priority="High")
		# 2. F created one second before the anchor: new; 5' response mark not reached yet
		t["f_new_last"] = _ticket(
			"f_new_last", anchor - timedelta(seconds=1), "F", priority="Low", first_responded_on=None
		)
		# 3. B new and opted out: listed by number only, still counted
		t["b_new_excluded"] = _ticket("b_new_excluded", start + timedelta(hours=1), "B", ai_opt_out=1)
		# 4. unmapped type, new, never answered: category "?", no response mark known -> not response overdue
		t["unmapped_new"] = _ticket(
			"unmapped_new", start + timedelta(hours=2), None, priority="Urgent", first_responded_on=None
		)
		# 5. A created one second before the window: not new; deadline exactly anchor + 24 h -> due soon
		t["a_before"] = _ticket(
			"a_before", start - timedelta(seconds=1), "A", resolution_by=anchor + timedelta(hours=24)
		)
		# 6. A created exactly at the anchor: not new
		t["a_at_anchor"] = _ticket("a_at_anchor", anchor, "A")
		# 7. B with a deadline one second past the due-soon range: neither due soon nor overdue
		t["b_due_beyond"] = _ticket(
			"b_due_beyond",
			start - timedelta(days=2),
			"B",
			resolution_by=anchor + timedelta(hours=24, seconds=1),
		)
		# 8. B never answered, deadline exactly the anchor: response overdue and overdue
		t["b_overdue_exact"] = _ticket(
			"b_overdue_exact", start - timedelta(days=2), "B", first_responded_on=None, resolution_by=anchor
		)
		# 9. C created exactly task_due_days ago, no Task, no real BA note (wrong author / wrong start);
		#    deadline one second after the anchor -> due soon
		t["c_old_no_task"] = _ticket(
			"c_old_no_task", anchor - timedelta(days=3), "C", resolution_by=anchor + timedelta(seconds=1)
		)
		_comment(t["c_old_no_task"], AGENT_USER, f"Ghi chú: {BA_NOTE_MARKER} chưa có")
		_comment(t["c_old_no_task"], HUMAN_AGENT, f"{BA_NOTE_MARKER} của người")
		# 10. C one second younger than task_due_days, with the bot's BA note: in neither missing list
		t["c_ba_note_young"] = _ticket(
			"c_ba_note_young", anchor - timedelta(days=3) + timedelta(seconds=1), "C"
		)
		_comment(t["c_ba_note_young"], AGENT_USER, f"{BA_NOTE_MARKER}\nPhân tích nghiệp vụ")
		# 11. D with a Task; its due field (D-18) wins over a past resolution_by -> due soon, not overdue
		t["d_task_due_field"] = _ticket(
			"d_task_due_field",
			anchor - timedelta(days=4),
			"D",
			resolution_by=anchor - timedelta(days=1),
			**{DUE_FIELD: anchor + timedelta(hours=2)},
		)
		_task(t["d_task_due_field"])
		# 12. E resolved exactly at the window start with a past deadline: done, not overdue (not open)
		t["e_resolved"] = _ticket(
			"e_resolved",
			anchor - timedelta(days=5),
			"E",
			resolution_by=anchor - timedelta(days=1),
			first_responded_on=None,
			**_resolved(start),
		)
		mine = set(t.values())

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(set(result), REPORT_KEYS)
		self.assertEqual(
			result["new_by_category_priority"],
			{"C": {"High": 1}, "B": {"Medium": 1}, "?": {"Urgent": 1}, "F": {"Low": 1}},
		)
		self.assertEqual(
			[row for row in result["new_list"] if row["name"] in mine],
			[
				_item(t["c_new_start"], "C", "High"),
				{"name": t["b_new_excluded"], "category": "B", "priority": "Medium", "excluded": True},
				_item(t["unmapped_new"], "?", "Urgent"),
				_item(t["f_new_last"], "F", "Low"),
			],
		)
		self.assertEqual(
			_names(result["due_soon"], mine), [t["d_task_due_field"], t["c_old_no_task"], t["a_before"]]
		)
		self.assertEqual(_names(result["overdue"], mine), [t["b_overdue_exact"]])
		self.assertEqual(_names(result["response_overdue"], mine), [t["b_overdue_exact"]])
		self.assertEqual(_names(result["c_missing_ba_note"], mine), [t["c_old_no_task"], t["c_new_start"]])
		self.assertEqual(_names(result["cd_missing_task"], mine), [t["c_old_no_task"]])
		self.assertEqual(
			result["de_progress"],
			{
				"D": {"done": 0, "in_progress": 1, "overdue": 0},
				"E": {"done": 1, "in_progress": 0, "overdue": 0},
			},
		)
		for key in ("due_soon", "overdue", "response_overdue", "c_missing_ba_note", "cd_missing_task"):
			for row in result[key]:
				if row["name"] in mine:
					self.assertIn("subject", row, key)

	def test_excluded_ticket_number_only_in_every_list(self):
		anchor = ANCHOR_TWELVE
		name = _ticket(
			"excluded_overdue",
			anchor - timedelta(days=5),
			"C",
			first_responded_on=None,
			resolution_by=anchor - timedelta(hours=1),
			ai_opt_out=1,
		)

		result = daily_report.build_daily_report(anchor)

		expected = {"name": name, "category": "C", "priority": "Medium", "excluded": True}
		for key in ("overdue", "response_overdue", "c_missing_ba_note", "cd_missing_task"):
			self.assertEqual([row for row in result[key] if row["name"] == name], [expected], key)

	def test_de_progress_window_edges(self):
		anchor = ANCHOR_DE
		start = anchor - timedelta(hours=24)
		# done: resolved at the window start; not done: one second before it, and exactly at the anchor
		_ticket("d_done", start - timedelta(days=1), "D", **_resolved(start))
		_ticket("d_done_before", start - timedelta(days=2), "D", **_resolved(start - timedelta(seconds=1)))
		_ticket("e_done_at_anchor", start - timedelta(days=2), "E", **_resolved(anchor))
		# open E past its due field (D-18) while resolution_by is unset: in progress and overdue
		_ticket("e_overdue", start - timedelta(days=3), "E", **{DUE_FIELD: anchor - timedelta(days=1)})
		# open D due later: in progress only; open C overdue: not a D/E ticket
		_ticket("d_open", start - timedelta(days=1), "D", **{DUE_FIELD: anchor + timedelta(days=5)})
		_ticket("c_overdue", start - timedelta(days=3), "C", resolution_by=anchor - timedelta(hours=1))

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(
			result["de_progress"],
			{
				"D": {"done": 1, "in_progress": 1, "overdue": 0},
				"E": {"done": 0, "in_progress": 1, "overdue": 1},
			},
		)

	def test_hours_and_days_come_from_settings(self):
		anchor = ANCHOR_HOURS
		set_agent_settings(due_reminder_hours=2, ba_note_due_hours=48, task_due_days=1)
		due_in_2h = _ticket(
			"due_in_2h", anchor - timedelta(days=1), "A", resolution_by=anchor + timedelta(hours=2)
		)
		due_in_3h = _ticket(
			"due_in_3h", anchor - timedelta(days=1), "A", resolution_by=anchor + timedelta(hours=3)
		)
		c_47h = _ticket("c_47h", anchor - timedelta(hours=47), "C")
		c_48h = _ticket("c_48h", anchor - timedelta(hours=48), "C")
		d_1_day = _ticket("d_1_day", anchor - timedelta(days=1), "D")
		mine = {due_in_2h, due_in_3h, c_47h, c_48h, d_1_day}

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(_names(result["due_soon"], mine), [due_in_2h])
		self.assertEqual(_names(result["c_missing_ba_note"], mine), [c_48h])
		self.assertEqual(_names(result["cd_missing_task"], mine), [c_48h, c_47h, d_1_day])

	def test_no_due_field_uses_resolution_by(self):
		anchor = ANCHOR_HOURS
		set_agent_settings(field_due_date="")
		name = _ticket(
			"d_no_due_field",
			anchor - timedelta(days=2),
			"D",
			resolution_by=anchor - timedelta(hours=1),
			**{DUE_FIELD: anchor + timedelta(hours=2)},
		)

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(_names(result["overdue"], {name}), [name])
		self.assertEqual(_names(result["due_soon"], {name}), [])
