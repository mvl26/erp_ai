import json
from datetime import datetime, timedelta
from unittest.mock import call, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import daily_report, runner
from erp_ai.agent.ops_data import BA_NOTE_MARKER
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, LOGGER_NAME, SETTING_DOCTYPE
from erp_ai.test_utils import keep_agent_settings, make_routing_rules, set_agent_settings

# Anchors long before any real ticket on the shared site, one per test, so "open" and "created in the
# window" see only the tickets a test makes.
ANCHOR_TWELVE = datetime(2002, 3, 11, 8, 0)
ANCHOR_DE = datetime(2002, 4, 8, 8, 0)
ANCHOR_HOURS = datetime(2002, 5, 6, 8, 0)
ANCHOR_BOT = datetime(2002, 6, 4, 8, 0)
ANCHOR_BOT_KINDS = datetime(2002, 7, 2, 8, 0)
REPORT_KEYS = {
	"new_by_category_priority",
	"new_list",
	"due_soon",
	"overdue",
	"response_overdue",
	"c_missing_ba_note",
	"cd_missing_task",
	"de_progress",
	"bot_actions",
	"cost_yesterday",
}
HUMAN_AGENT = "erpai-test-daily-human@example.com"
TYPE_PREFIX = "ERPAI-TEST daily "
TYPE_UNMAPPED = "ERPAI-TEST daily unmapped"
CATEGORY_MAPPING = {category: {"ticket_type": f"{TYPE_PREFIX}{category}"} for category in "ABCDEF"}
# A real Datetime Custom Field erp_ai installs on HD Ticket (test_install pins it): no test creates a field.
DUE_FIELD = "ai_updated_at"
# A Date field of HD Ticket itself (Helpdesk core), for a due field of type Date.
DATE_DUE_FIELD = "opening_date"


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


def _comment(ticket: str, owner: str, content: str, comment_type: str = "Comment") -> None:
	doc = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": comment_type,
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"content": content,
		}
	)
	doc.db_insert()
	frappe.db.set_value("Comment", doc.name, "owner", owner, update_modified=False)


def _task(ticket: str) -> None:
	frappe.get_doc({"doctype": "Task", "subject": "ERPAI-TEST daily", "ai_ticket": ticket}).db_insert()


def _log(creation: datetime, **values) -> None:
	"""An ERP AI Log row inserted straight into the database with its `creation` set."""
	doc = frappe.get_doc(
		{"doctype": LOG_DOCTYPE, "run_id": "ERPAI-TEST-daily", "entry_type": "skip", **values}
	)
	doc.db_insert()
	frappe.db.set_value(LOG_DOCTYPE, doc.name, "creation", creation, update_modified=False)


def _action(tool: str, ok: bool = True) -> dict:
	return {"tool": tool, "doctype": "HD Ticket", "name": None, "ok": ok}


def _names(rows: list[dict], mine: set[str]) -> list[str]:
	"""Names of the report rows that belong to this test, in report order."""
	return [row["name"] for row in rows if row["name"] in mine]


def _deadlines(rows: list[dict], mine: set[str]) -> dict[str, datetime]:
	"""The `deadline` of each report row that belongs to this test."""
	return {row["name"]: row["deadline"] for row in rows if row["name"] in mine}


def _item(name: str, category: str, priority: str = "Medium") -> dict:
	return {
		"name": name,
		"subject": frappe.db.get_value("HD Ticket", name, "subject"),
		"category": category,
		"priority": priority,
		"excluded": False,
	}


def _report_settings(test: FrappeTestCase) -> None:
	"""Seed the settings the report reads; restore them and roll the test's rows back after the test."""
	keep_agent_settings(test)
	test.addCleanup(frappe.db.rollback)
	set_agent_settings(
		category_mapping=json.dumps(CATEGORY_MAPPING),
		routing_rules=make_routing_rules(),
		field_due_date=DUE_FIELD,
		due_reminder_hours=24,
		ba_note_due_hours=24,
		task_due_days=3,
	)


def _bot_actions(**counts: int) -> dict[str, int]:
	"""Every kind of `bot_actions` at 0, except the given ones; keys with a space are passed as `**{...}`."""
	return {kind: counts.get(kind, 0) for kind in daily_report.BOT_ACTION_KINDS}


class TestBuild(FrappeTestCase):
	def setUp(self):
		_report_settings(self)

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
		self.assertEqual(
			_deadlines(result["due_soon"], mine),
			{
				t["d_task_due_field"]: anchor + timedelta(hours=2),
				t["c_old_no_task"]: anchor + timedelta(seconds=1),
				t["a_before"]: anchor + timedelta(hours=24),
			},
		)
		self.assertEqual(_deadlines(result["overdue"], mine), {t["b_overdue_exact"]: anchor})
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
		overdue = _ticket(
			"excluded_overdue",
			anchor - timedelta(days=5),
			"C",
			first_responded_on=None,
			resolution_by=anchor - timedelta(hours=1),
			ai_opt_out=1,
		)
		due_soon = _ticket(
			"excluded_due_soon",
			anchor - timedelta(days=4),
			"C",
			first_responded_on=None,
			resolution_by=anchor + timedelta(hours=1),
			ai_opt_out=1,
		)
		in_list = {
			"due_soon": [due_soon],
			"overdue": [overdue],
			"response_overdue": [overdue, due_soon],
			"c_missing_ba_note": [overdue, due_soon],
			"cd_missing_task": [overdue, due_soon],
		}

		result = daily_report.build_daily_report(anchor)

		for key, names in in_list.items():
			expected = [
				{"name": name, "category": "C", "priority": "Medium", "excluded": True} for name in names
			]
			self.assertEqual(
				[row for row in result[key] if row["name"] in (overdue, due_soon)], expected, key
			)

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
		self.assertEqual(_deadlines(result["overdue"], {name}), {name: anchor - timedelta(hours=1)})
		self.assertEqual(_names(result["due_soon"], {name}), [])

	def test_due_lists_carry_deadline(self):
		anchor = ANCHOR_HOURS
		set_agent_settings(field_due_date=DATE_DUE_FIELD)
		a_due_soon = _ticket(
			"a_due_soon", anchor - timedelta(days=2), "A", resolution_by=anchor + timedelta(hours=3)
		)
		# E past its due field of type Date: the deadline is the end of that day; resolution_by is later
		e_overdue = _ticket(
			"e_overdue_date",
			anchor - timedelta(days=3),
			"E",
			resolution_by=anchor + timedelta(days=2),
			**{DATE_DUE_FIELD: (anchor - timedelta(days=1)).date()},
		)
		excluded_overdue = _ticket(
			"b_excluded_overdue",
			anchor - timedelta(days=4),
			"B",
			resolution_by=anchor - timedelta(hours=1),
			ai_opt_out=1,
		)
		mine = {a_due_soon, e_overdue, excluded_overdue}

		result = daily_report.build_daily_report(anchor)

		due_soon = [row for row in result["due_soon"] if row["name"] in mine]
		self.assertEqual(due_soon, [{**_item(a_due_soon, "A"), "deadline": anchor + timedelta(hours=3)}])
		overdue = [row for row in result["overdue"] if row["name"] in mine]
		self.assertEqual(
			overdue,
			[
				{"name": excluded_overdue, "category": "B", "priority": "Medium", "excluded": True},
				{**_item(e_overdue, "E"), "deadline": datetime(2002, 5, 5, 23, 59, 59)},
			],
		)

	def test_empty_priority_counted_as_unknown(self):
		anchor = ANCHOR_HOURS
		name = _ticket("a_no_priority", anchor - timedelta(hours=1), "A", priority=None)

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(result["new_by_category_priority"]["A"]["?"], 1)
		self.assertEqual([row for row in result["new_list"] if row["name"] == name], [_item(name, "A", "?")])

	def test_reopened_ticket_not_done(self):
		anchor = ANCHOR_DE
		start = anchor - timedelta(hours=24)
		# written straight to the database: open again, yet resolution_date still in the window
		_ticket(
			"d_reopened",
			start - timedelta(days=1),
			"D",
			status="Open",
			status_category="Open",
			resolution_date=start + timedelta(hours=1),
		)

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(result["de_progress"]["D"], {"done": 0, "in_progress": 1, "overdue": 0})

	def test_due_field_not_on_ticket_uses_resolution_by(self):
		anchor = ANCHOR_HOURS
		# "subject" exists on HD Ticket but is not a Date/Datetime field
		for due_field in ("erpai_test_no_such_field", "subject"):
			with self.subTest(due_field=due_field):
				frappe.db.set_single_value(SETTING_DOCTYPE, "field_due_date", due_field)
				name = _ticket(
					f"d_lost_due_field {due_field}",
					anchor - timedelta(days=2),
					"D",
					resolution_by=anchor - timedelta(hours=1),
				)

				with patch("frappe.logger") as get_logger:
					result = daily_report.build_daily_report(anchor)

				self.assertEqual(_deadlines(result["overdue"], {name}), {name: anchor - timedelta(hours=1)})
				get_logger.assert_called_with(LOGGER_NAME)
				self.assertEqual(
					get_logger.return_value.warning.call_args_list,
					[
						call(
							"erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, "
							"using resolution_by",
							due_field,
						)
					],
				)

	def test_ba_note_other_comment_type_not_counted(self):
		anchor = ANCHOR_HOURS
		name = _ticket("c_info_note", anchor - timedelta(days=2), "C")
		_comment(name, AGENT_USER, f"{BA_NOTE_MARKER}\nPhân tích nghiệp vụ", comment_type="Info")

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(_names(result["c_missing_ba_note"], {name}), [name])

	def test_empty_due_field_logs_no_warning(self):
		anchor = ANCHOR_HOURS
		set_agent_settings(field_due_date="")
		name = _ticket(
			"d_empty_due_field", anchor - timedelta(days=2), "D", resolution_by=anchor - timedelta(hours=1)
		)

		with patch("frappe.logger") as get_logger:
			result = daily_report.build_daily_report(anchor)

		self.assertEqual(_deadlines(result["overdue"], {name}), {name: anchor - timedelta(hours=1)})
		self.assertEqual(get_logger.return_value.warning.call_args_list, [])

	def test_bot_actions_and_cost_yesterday(self):
		anchor = ANCHOR_BOT
		day = datetime(2002, 6, 3)
		frappe.db.delete(
			LOG_DOCTYPE, {"creation": ["between", [day - timedelta(days=1), anchor + timedelta(days=1)]]}
		)
		# yesterday, first second: classified and applied with a predicted assignee but no ok assign_owner
		# entry -> classify only
		_log(day, entry_type="classify", applied=1, predicted_assignee=HUMAN_AGENT, cost_usd=0.1)
		# classified, applied, no assignee: classify only
		_log(day + timedelta(hours=9), entry_type="classify", applied=1, cost_usd=0.2)
		# classified, not applied: neither; its error counts
		_log(
			day + timedelta(hours=10),
			entry_type="classify",
			applied=0,
			predicted_assignee=HUMAN_AGENT,
			error="model timeout",
			cost_usd=0.000001,
		)
		# actions: ok ones by kind (an unknown tool -> other), a failed one not counted
		_log(
			day + timedelta(hours=11),
			entry_type="reason",
			actions=json.dumps(
				[
					_action("create_task"),
					_action("create_task"),
					_action("post_comment"),
					_action("set_priority"),
					_action("post_comment", ok=False),
				]
			),
		)
		# unreadable actions count as none; a blank error is no error; cost_usd is a decimal(21,6) column
		# (precision 6), so 0.0000004 is stored as 0 and the sum stays 0.300001
		_log(
			day + timedelta(hours=12), entry_type="reason", actions="not json", error="  ", cost_usd=0.0000004
		)
		# change steps: propose x2, approve, reject; other steps not counted
		for step in ("propose", "propose", "approve", "reject", "apply", "undo"):
			_log(day + timedelta(hours=13), entry_type="change", trigger="change_action", change_step=step)
		# last second of yesterday
		_log(day + timedelta(hours=23, minutes=59, seconds=59), entry_type="classify", applied=1)
		# outside yesterday: the day before, and today before the anchor
		for creation in (day - timedelta(seconds=1), day + timedelta(days=1)):
			_log(
				creation,
				entry_type="classify",
				applied=1,
				predicted_assignee=HUMAN_AGENT,
				error="outside",
				cost_usd=5.0,
				actions=json.dumps([_action("create_task")]),
			)
			_log(creation, entry_type="change", trigger="change_action", change_step="propose")

		result = daily_report.build_daily_report(anchor)

		self.assertEqual(
			daily_report.ACTION_KIND_BY_TOOL,
			{
				"set_classification": "phân loại",
				"assign_owner": "gán",
				"create_task": "Task",
				"create_routed_task": "Task",
				"post_comment": "comment",
				"post_routing_comment": "comment",
			},
		)
		self.assertEqual(
			daily_report.TOOLS_COUNTED_ELSEWHERE,
			frozenset({"apply_route", "propose_file_change", "propose_new_file", "propose_bench_command"}),
		)
		self.assertEqual(
			result["bot_actions"],
			{
				"phân loại": 3,
				"gán": 0,
				"Task": 2,
				"comment": 1,
				"trả lời": 0,
				"đóng": 0,
				"đề xuất chờ duyệt": 2,
				"đã duyệt": 1,
				"bị từ chối": 1,
				"lỗi": 1,
				"khác": 1,
			},
		)
		self.assertEqual(result["cost_yesterday"], 0.300001)


class TestBotActions(FrappeTestCase):
	"""How each ok action entry of yesterday's ERP AI Log rows is counted (design-w1-fixes-18 Điểm 1-3)."""

	def setUp(self):
		_report_settings(self)
		self.day = ANCHOR_BOT_KINDS.date() - timedelta(days=1)
		self.yesterday = datetime.combine(self.day, datetime.min.time()) + timedelta(hours=10)
		frappe.db.delete(
			LOG_DOCTYPE,
			{
				"creation": [
					"between",
					[ANCHOR_BOT_KINDS - timedelta(days=3), ANCHOR_BOT_KINDS + timedelta(days=1)],
				]
			},
		)

	def _report(self) -> dict:
		return daily_report.build_daily_report(ANCHOR_BOT_KINDS)

	def test_assign_counted_from_ok_assign_owner_only(self):
		already_assigned = {**_action("assign_owner", ok=False), "reason": "phiếu đã có người được gán"}
		for assign in (_action("assign_owner"), already_assigned, _action("assign_owner", ok=False)):
			_log(
				self.yesterday,
				entry_type="classify",
				applied=1,
				predicted_assignee=HUMAN_AGENT,
				actions=json.dumps([_action("apply_route"), assign]),
			)

		result = self._report()

		self.assertEqual(result["bot_actions"], _bot_actions(**{"phân loại": 3, "gán": 1}))

	def test_routing_task_and_comment_kinds(self):
		_log(
			self.yesterday,
			entry_type="classify",
			applied=1,
			actions=json.dumps(
				[
					_action("apply_route"),
					_action("sla_check", ok=False),
					_action("assign_owner"),
					_action("create_routed_task"),
					_action("post_routing_comment"),
				]
			),
		)

		result = self._report()

		self.assertEqual(
			result["bot_actions"], _bot_actions(**{"phân loại": 1, "gán": 1, "Task": 1, "comment": 1})
		)

	def test_propose_counted_once(self):
		self.assertEqual(
			daily_report.TOOLS_COUNTED_ELSEWHERE, frozenset({"apply_route", *runner.PROPOSE_TOOLS})
		)
		_log(
			self.yesterday,
			entry_type="reason",
			actions=json.dumps([_action("propose_file_change"), _action("propose_new_file", ok=False)]),
		)
		_log(self.yesterday, entry_type="change", trigger="change_action", change_step="propose")

		result = self._report()

		self.assertEqual(result["bot_actions"], _bot_actions(**{"đề xuất chờ duyệt": 1}))

	def test_close_reply_and_classification_kinds(self):
		ticket = _ticket("bot_close", self.yesterday, "A")
		other = _ticket("bot_close_other", self.yesterday, "A")

		def update(name: str, status: str, ok: bool = True) -> dict:
			return {
				"tool": "api_update_record",
				"doctype": "HD Ticket",
				"name": name,
				"ok": ok,
				"value_before": {"status": "Open"},
				"value_after": {"status": status},
			}

		_log(
			self.yesterday,
			entry_type="reason",
			ticket=ticket,
			actions=json.dumps(
				[
					update(ticket, "Closed"),
					update(ticket, "Resolved"),
					update(other, "Closed"),
					update(ticket, "Open"),
					update(ticket, "Closed", ok=False),
					{**_action("set_classification"), "name": ticket},
					{**_action("post_comment"), "name": ticket},
				]
			),
		)

		result = self._report()

		self.assertEqual(
			result["bot_actions"],
			_bot_actions(**{"đóng": 2, "khác": 2, "phân loại": 1, "comment": 1, "trả lời": 0}),
		)

	def test_empty_day_zero_float(self):
		result = self._report()

		self.assertEqual(list(result["bot_actions"]), list(daily_report.BOT_ACTION_KINDS))
		self.assertEqual(result["bot_actions"], _bot_actions())
		self.assertEqual(result["cost_yesterday"], 0.0)
		self.assertIsInstance(result["cost_yesterday"], float)

	def test_unreadable_actions_and_non_classify_applied(self):
		# an applied reason row is no classification
		_log(self.yesterday, entry_type="reason", applied=1, actions="{}")
		_log(self.yesterday, entry_type="reason", actions="null")
		# entries that are not dicts, and an `ok` that is truthy but not True
		_log(
			self.yesterday,
			entry_type="reason",
			actions=json.dumps([1, "x", {"tool": "create_task", "ok": "yes"}]),
		)

		result = self._report()

		self.assertEqual(result["bot_actions"], _bot_actions())
