import datetime
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

import frappe
import frappe.desk.form.load
import frappe.handler
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket, make_todo

from erp_ai.agent import authority, change_text
from erp_ai.agent.changes import restart_check, transitions
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	LOG_DOCTYPE,
	OPERATION_DOCTYPE,
	PROPOSAL_DOCTYPE,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
	RESTART_STATUS_SENT,
	RESTART_STATUS_UNCONFIRMED,
	RESTART_TIMEOUT_S,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
from erp_ai.test_utils import (
	PREFIX,
	keep_agent_settings,
	make_block_proposal,
	make_change_proposal,
	set_agent_settings,
)

JSON_PATH = Path(__file__).resolve().parent / "erp_ai_change_proposal.json"

# Design 3.3 form layout, in JSON order (column breaks split "cột 2").
FIELD_ORDER = [
	"section_proposal",
	"change_status",
	"change_kind",
	"app",
	"file_path",
	"is_new_file",
	"reversible",
	"column_proposal",
	"ticket",
	"run_id",
	"instructor",
	"reason",
	"section_git",
	"target_branch",
	"upstream_ref",
	"ahead_count",
	"is_core_app",
	"column_git",
	"commit_message",
	"section_git_result",
	"apply_commit_sha",
	"applied_branch",
	"applied_ahead_count",
	"column_git_result",
	"undo_commit_sha",
	"section_diff",
	"diff",
	"operations",
	"section_content",
	"content_before",
	"content_after",
	"base_hash",
	"after_hash",
	"section_command",
	"command_args",
	"command_list",
	"exit_code",
	"duration_ms",
	"command_output",
	"command_results",
	"section_decision",
	"decided_by",
	"decided_at",
	"undo_by",
	"undo_at",
	"finished_at",
	"failure_reason",
	"approved_digest",
	"created_dirs",
	"restart_status",
	"restart_sent_at",
]
GIT_FIELDS = (
	"target_branch",
	"upstream_ref",
	"ahead_count",
	"is_core_app",
	"commit_message",
	"applied_branch",
	"applied_ahead_count",
	"apply_commit_sha",
	"undo_commit_sha",
)
CODE_FIELDS = {
	"command_args",
	"content_before",
	"content_after",
	"diff",
	"commit_message",
	"command_output",
}
# Design 2.2 block fields stored as JSON text.
BLOCK_CODE_FIELDS = {"command_list", "command_results", "created_dirs"}
# Design 2.1 content group, each with a valid replacement value so only the immutability rule can refuse it.
CONTENT_FIELD_NEW_VALUES = {
	"run_id": "ERPAI-TEST-other-run",
	"instructor": "Guest",
	"change_kind": CHANGE_KIND_COMMAND,
	"app": "otherapp",
	"file_path": "otherapp/otherapp/ok.py",
	"is_new_file": 1,
	"command_args": '["migrate"]',
	"base_hash": "0" * 64,
	"content_before": "y = 1\n",
	"content_after": "y = 2\n",
	"after_hash": "1" * 64,
	"diff": "--- a/x\n+++ b/x\n",
	"reason": "Lý do khác",
	"reversible": 0,
	"target_branch": "develop",
	"upstream_ref": "upstream/develop",
	"ahead_count": 7,
	"is_core_app": 1,
	"commit_message": "erp_ai: thông điệp khác",
}
STATE_FIELD_NEW_VALUES = {
	"change_status": CHANGE_STATUS_FAILED,
	"decided_by": "Administrator",
	"decided_at": "2026-11-13 10:00:00",
	"approved_digest": "2" * 64,
	"undo_by": "Administrator",
	"undo_at": "2026-11-13 11:00:00",
	"finished_at": "2026-11-13 12:00:00",
	"exit_code": 1,
	"duration_ms": 250,
	"command_output": "lỗi\n",
	"failure_reason": "nội dung đề xuất đã bị sửa sau khi duyệt",
	"applied_branch": "main",
	"applied_ahead_count": 1,
	"apply_commit_sha": "a" * 40,
	"undo_commit_sha": "b" * 40,
}


# CHG-002 design 2.1: the 7 fields of a child row, all content.
OPERATION_ROW_FIELDS = (
	"operation",
	"file_path",
	"new_path",
	"content_before",
	"content_after",
	"base_hash",
	"after_hash",
)
# Two items of a block: an edit, then a rename (so `new_path` has a value to compare).
BLOCK_OPERATIONS = [
	{"kind": CHANGE_OP_EDIT, "path": "myapp/myapp/a.py", "before": "x = 1\n", "after": "x = 2\n"},
	{
		"kind": CHANGE_OP_RENAME,
		"path": "myapp/myapp/b.py",
		"new_path": "myapp/myapp/c.py",
		"before": "y = 1\n",
		"after": "y = 1\n",
	},
]
CONTENT_REFUSAL = "Nội dung đề xuất không sửa được sau khi tạo"
UNREADABLE_NOTES = (
	"Không đọc được nội dung đã lưu của đề xuất này (dữ liệu hỏng); báo quản trị trước khi duyệt."
)


def _load_json():
	with open(JSON_PATH, encoding="utf-8") as handle:
		return json.load(handle)


def _fields_by_name():
	return {field["fieldname"]: field for field in _load_json()["fields"]}


class TestERPAIChangeProposal(FrappeTestCase):
	def setUp(self):
		self.assertTrue(JSON_PATH.exists(), "erp_ai_change_proposal.json is missing")
		self.assertTrue(
			frappe.db.exists("DocType", PROPOSAL_DOCTYPE), "DocType ERP AI Change Proposal is missing"
		)
		# FrappeTestCase rolls back only after the whole class: undo each test's proposals and tickets.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")

	def test_proposal_json_permissions_have_no_write_delete_submit_cancel_amend(self):
		doctype = _load_json()
		self.assertEqual(doctype["name"], "ERP AI Change Proposal")
		self.assertEqual(doctype["module"], "ERP AI agent")
		self.assertEqual(doctype["autoname"], "AICHG-.#####")
		self.assertFalse(doctype.get("is_submittable"))
		granted = {
			row["role"]: {
				right for right, value in row.items() if right not in ("role", "permlevel") and value
			}
			for row in doctype["permissions"]
		}
		self.assertEqual(
			granted,
			{
				"ERP AI Agent": {"create", "read"},
				"ERP AI Instructor": {"read"},
				"System Manager": {"read"},
			},
		)
		self.assertEqual(len(doctype["permissions"]), 3)
		stored = frappe.get_all(
			"DocPerm",
			filters={"parent": PROPOSAL_DOCTYPE},
			fields=["role", "read", "write", "create", "delete", "submit", "cancel", "amend"],
		)
		self.assertEqual(
			{
				(row.role, row.read, row.write, row.create, row.delete, row.submit, row.cancel, row.amend)
				for row in stored
			},
			{
				("ERP AI Agent", 1, 0, 1, 0, 0, 0, 0),
				("ERP AI Instructor", 1, 0, 0, 0, 0, 0, 0),
				("System Manager", 1, 0, 0, 0, 0, 0, 0),
			},
		)

	def test_select_options_match_constants(self):
		fields = _fields_by_name()
		status_options = [
			"Chờ duyệt",
			"Đã từ chối",
			"Đã duyệt",
			"Đang áp dụng",
			"Đã áp dụng",
			"Lỗi",
			"Hết hiệu lực",
			"Đang hoàn tác",
			"Đã hoàn tác",
		]
		kind_options = ["Thay đổi code", "Lệnh bench"]
		self.assertEqual(fields["change_status"]["options"].split("\n"), status_options)
		self.assertEqual(fields["change_status"]["default"], "Chờ duyệt")
		self.assertEqual(fields["change_kind"]["options"].split("\n"), kind_options)
		self.assertEqual(
			[
				CHANGE_STATUS_PENDING,
				CHANGE_STATUS_REJECTED,
				CHANGE_STATUS_APPROVED,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				CHANGE_STATUS_FAILED,
				CHANGE_STATUS_STALE,
				CHANGE_STATUS_UNDOING,
				CHANGE_STATUS_UNDONE,
			],
			status_options,
		)
		self.assertEqual([CHANGE_KIND_CODE, CHANGE_KIND_COMMAND], kind_options)
		select_fields = {name for name, field in fields.items() if field["fieldtype"] == "Select"}
		self.assertEqual(select_fields, {"change_status", "change_kind", "restart_status"})
		restart_options = ["", "Đã gửi", "Đã xác nhận", "Chưa xác nhận", "Lỗi khởi chạy"]
		self.assertEqual(fields["restart_status"]["options"].split("\n"), restart_options)
		self.assertEqual(
			[
				"",
				RESTART_STATUS_SENT,
				RESTART_STATUS_CONFIRMED,
				RESTART_STATUS_UNCONFIRMED,
				RESTART_STATUS_LAUNCH_FAILED,
			],
			restart_options,
		)
		# Empty restart status means "no restart needed" (ADR-040 decision 7).
		self.assertFalse(fields["restart_status"].get("default"))

	def test_content_fields_are_code_and_read_only(self):
		fields = _fields_by_name()
		code_fields = {name for name, field in fields.items() if field["fieldtype"] == "Code"}
		self.assertEqual(code_fields, CODE_FIELDS | BLOCK_CODE_FIELDS)
		for name in BLOCK_CODE_FIELDS:
			with self.subTest(fieldname=name):
				self.assertEqual(fields[name]["options"], "JSON")
		self.assertEqual(fields["operations"]["fieldtype"], "Table")
		self.assertEqual(fields["operations"]["options"], OPERATION_DOCTYPE)
		self.assertEqual(fields["restart_sent_at"]["fieldtype"], "Datetime")
		data_fields = [
			name
			for name, field in fields.items()
			if field["fieldtype"] not in ("Section Break", "Column Break", "Tab Break")
		]
		self.assertEqual(len(data_fields), 41)
		for name in data_fields:
			with self.subTest(fieldname=name):
				self.assertEqual(fields[name].get("read_only"), 1)
		unsafe = {"HTML", "Text Editor", "Markdown Editor", "HTML Editor"}
		self.assertEqual({field["fieldtype"] for field in fields.values()} & unsafe, set())
		self.assertEqual(fields["ticket"]["options"], "HD Ticket")
		self.assertEqual(fields["ticket"].get("reqd"), 1)
		self.assertEqual(fields["ticket"].get("search_index"), 1)
		self.assertEqual(fields["change_status"].get("search_index"), 1)
		self.assertEqual(fields["run_id"].get("reqd"), 1)

	def test_content_field_change_on_save_is_refused(self):
		other_ticket = make_ticket(subject=f"{PREFIX}change proposal other ticket").name
		new_values = dict(CONTENT_FIELD_NEW_VALUES, ticket=other_ticket)
		self.assertEqual(len(new_values), 20)
		for fieldname, new_value in new_values.items():
			with self.subTest(fieldname=fieldname):
				proposal = make_change_proposal()
				before = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal.name, fieldname)
				self.assertNotEqual(str(before), str(new_value))
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				doc.set(fieldname, new_value)
				with self.assertRaises(frappe.ValidationError) as caught:
					doc.save(ignore_permissions=True)
				self.assertIn(fieldname, str(caught.exception))
				self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, proposal.name, fieldname), before)

	def test_state_field_change_on_save_is_allowed(self):
		proposal = make_change_proposal()
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
		doc.update(STATE_FIELD_NEW_VALUES)
		doc.save(ignore_permissions=True)
		stored = frappe.db.get_value(
			PROPOSAL_DOCTYPE, proposal.name, list(STATE_FIELD_NEW_VALUES), as_dict=True
		)
		for fieldname, value in STATE_FIELD_NEW_VALUES.items():
			with self.subTest(fieldname=fieldname):
				self.assertEqual(str(stored[fieldname]), str(value))

	def test_insert_with_non_pending_status_is_forced_pending(self):
		statuses = (
			CHANGE_STATUS_REJECTED,
			CHANGE_STATUS_APPROVED,
			CHANGE_STATUS_APPLYING,
			CHANGE_STATUS_APPLIED,
			CHANGE_STATUS_FAILED,
			CHANGE_STATUS_STALE,
			CHANGE_STATUS_UNDOING,
			CHANGE_STATUS_UNDONE,
		)
		self.assertEqual(len(statuses), 8)
		cleared = {
			"change_status": "Chờ duyệt",
			"decided_by": None,
			"decided_at": None,
			"approved_digest": None,
			"undo_by": None,
			"undo_at": None,
			"finished_at": None,
			"exit_code": 0,
			"duration_ms": 0,
			"command_output": None,
			"failure_reason": None,
			"applied_branch": None,
			"applied_ahead_count": 0,
			"apply_commit_sha": None,
			"undo_commit_sha": None,
		}
		self.assertEqual(set(cleared), set(STATE_FIELD_NEW_VALUES))
		for kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
			for status in statuses:
				with self.subTest(kind=kind, status=status):
					proposal = make_change_proposal(
						kind=kind, **dict(STATE_FIELD_NEW_VALUES, change_status=status)
					)
					self.assertEqual(proposal.change_status, CHANGE_STATUS_PENDING)
					stored = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal.name, list(cleared), as_dict=True)
					self.assertEqual(stored, cleared)

	def test_insert_keeps_content_fields(self):
		proposal = make_change_proposal(**dict(STATE_FIELD_NEW_VALUES))
		stored = frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			proposal.name,
			["change_kind", "target_branch", "upstream_ref", "commit_message", "reason"],
			as_dict=True,
		)
		self.assertEqual(stored.change_kind, CHANGE_KIND_CODE)
		self.assertEqual((stored.target_branch, stored.upstream_ref), ("main", "origin/main"))
		# D-14: the controller replaces the sample message by the design 3.9 preview.
		self.assertTrue(
			stored.commit_message.startswith(f"erp_ai: áp dụng {proposal.name} (myapp/myapp/ok.py)")
		)
		self.assertEqual(stored.reason, "Đề xuất mẫu cho test")

	def test_commit_message_set_by_controller_not_by_tool(self):
		tool_text = "erp_ai: chữ do model tự viết\n\nNgười duyệt: ai cũng được"
		code = make_change_proposal(commit_message=tool_text)
		expected = (
			f"erp_ai: áp dụng {code.name} (myapp/myapp/ok.py)\n"
			"\n"
			f"Đề xuất: {code.name}\n"
			f"Phiếu: {code.ticket}\n"
			"Người duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt."
		)
		self.assertEqual(code.commit_message, expected)
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, code.name, "commit_message"), expected)
		command = make_change_proposal(kind=CHANGE_KIND_COMMAND, commit_message=tool_text)
		self.assertFalse(frappe.db.get_value(PROPOSAL_DOCTYPE, command.name, "commit_message"))
		# After insert the message is a content field: an unchanged re-save keeps it.
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, code.name)
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, code.name, "commit_message"), expected)

	def test_unchanged_content_resave_is_allowed(self):
		for kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
			with self.subTest(kind=kind):
				proposal = make_change_proposal(kind=kind)
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				doc.save(ignore_permissions=True)
				self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, proposal.name, "change_kind"), kind)

	def _stored_rows(self, name) -> list:
		return frappe.get_all(
			OPERATION_DOCTYPE,
			filters={"parent": name, "parenttype": PROPOSAL_DOCTYPE},
			fields=["idx", *OPERATION_ROW_FIELDS],
			order_by="idx asc",
		)

	def assertContentRefused(self, doc, fieldname):
		"""Saving `doc` raises the immutability sentence naming `fieldname`; the stored rows are unchanged."""
		before = (
			self._stored_rows(doc.name),
			frappe.db.get_value(PROPOSAL_DOCTYPE, doc.name, "command_list"),
		)
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.save(ignore_permissions=True)
		self.assertEqual(str(caught.exception), f"{CONTENT_REFUSAL}: {fieldname}")
		self.assertEqual(
			(self._stored_rows(doc.name), frappe.db.get_value(PROPOSAL_DOCTYPE, doc.name, "command_list")),
			before,
		)

	def test_child_rows_immutable_after_insert(self):
		# One replacement per row field, each a valid value so only the immutability rule can refuse it.
		new_values = {
			"operation": CHANGE_OP_CREATE,
			"file_path": "myapp/myapp/other.py",
			"new_path": "myapp/myapp/z.py",
			"content_before": "x = 9\n",
			"content_after": "x = 8\n",
			"base_hash": "0" * 64,
			"after_hash": "1" * 64,
		}
		self.assertEqual(tuple(new_values), OPERATION_ROW_FIELDS)
		for fieldname, new_value in new_values.items():
			with self.subTest(fieldname=fieldname):
				proposal = make_block_proposal(BLOCK_OPERATIONS, [])
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				self.assertNotEqual(doc.operations[0].get(fieldname), new_value)
				doc.operations[0].set(fieldname, new_value)
				self.assertContentRefused(doc, "operations")

	def test_row_added_or_removed_refused(self):
		def add_row(doc):
			doc.append(
				"operations",
				{"operation": CHANGE_OP_DELETE, "file_path": "myapp/myapp/d.py", "content_before": "z = 1\n"},
			)

		def remove_row(doc):
			doc.remove(doc.operations[-1])

		def reorder_rows(doc):
			doc.operations.reverse()
			for index, row in enumerate(doc.operations, start=1):
				row.idx = index

		def renumber_rows(doc):
			# Same list, swapped `idx`: the stored order changes all the same.
			first, second = doc.operations
			first.idx, second.idx = second.idx, first.idx

		for change in (add_row, remove_row, reorder_rows, renumber_rows):
			with self.subTest(change=change.__name__):
				proposal = make_block_proposal(BLOCK_OPERATIONS, [])
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				change(doc)
				self.assertContentRefused(doc, "operations")

	def test_block_unchanged_resave_is_allowed(self):
		proposal = make_block_proposal(BLOCK_OPERATIONS, [["--site", "miyano", "migrate"]])
		before = self._stored_rows(proposal.name)
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
		doc.save(ignore_permissions=True)
		self.assertEqual(self._stored_rows(proposal.name), before)

	def test_command_list_immutable(self):
		for operations in (BLOCK_OPERATIONS, []):
			with self.subTest(file_items=len(operations)):
				proposal = make_block_proposal(operations, [["--site", "miyano", "migrate"]])
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				doc.command_list = json.dumps([["build", "--app", "myapp"]])
				self.assertContentRefused(doc, "command_list")

	def test_block_commit_preview_lists_items(self):
		many = make_block_proposal(BLOCK_OPERATIONS, [])
		self.assertEqual(
			many.commit_message,
			f"erp_ai: áp dụng {many.name} (2 file)\n"
			"\n"
			f"Đề xuất: {many.name}\n"
			f"Phiếu: {many.ticket}\n"
			"sửa myapp/myapp/a.py\n"
			"đổi tên myapp/myapp/b.py → myapp/myapp/c.py\n"
			"Người duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		self.assertEqual(
			frappe.db.get_value(PROPOSAL_DOCTYPE, many.name, "commit_message"), many.commit_message
		)
		one = make_block_proposal(BLOCK_OPERATIONS[:1], [])
		self.assertEqual(
			one.commit_message,
			f"erp_ai: áp dụng {one.name} (myapp/myapp/a.py)\n"
			"\n"
			f"Đề xuất: {one.name}\n"
			f"Phiếu: {one.ticket}\n"
			"sửa myapp/myapp/a.py\n"
			"Người duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		commands_only = make_block_proposal([], [["build", "--app", "myapp"]])
		self.assertFalse(frappe.db.get_value(PROPOSAL_DOCTYPE, commands_only.name, "commit_message"))

	def test_onload_unreadable_notes_opens_with_one_warning_line(self):
		corruptions = {
			"command_list not a list of argv lists": {"command_list": '["migrate"]'},
			"unknown restart_status": {"restart_status": "Không rõ"},
		}
		for case, values in corruptions.items():
			with self.subTest(case=case):
				proposal = make_block_proposal(BLOCK_OPERATIONS, [["--site", "miyano", "migrate"]])
				frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, values, update_modified=False)
				error_logs = frappe.db.count("Error Log")
				with patch.object(controller.frappe, "logger") as logger:
					frappe.response.docs = []
					try:
						frappe.desk.form.load.getdoc(PROPOSAL_DOCTYPE, proposal.name)
						form = frappe.response.docs[0]
					finally:
						frappe.response.docs = []
				self.assertEqual(form.name, proposal.name)
				self.assertEqual(form.get("__onload").change_notes, [UNREADABLE_NOTES])
				self.assertEqual(
					logger.return_value.warning.call_args_list,
					[call("erp_ai notes proposal=%s error=%s", proposal.name, "ValueError")],
				)
				self.assertIn(call("erp_ai"), logger.call_args_list)
				self.assertEqual(frappe.db.count("Error Log"), error_logs)
		with self.subTest(case="other exception classes are not caught"):
			proposal = make_block_proposal(BLOCK_OPERATIONS, [])
			doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
			with patch.object(controller.change_text, "proposal_notes", side_effect=TypeError("x")):
				with self.assertRaises(TypeError):
					doc.run_method("onload")

	def test_sample_proposals_are_pending_with_git_fields(self):
		code = make_change_proposal()
		self.assertRegex(code.name, r"^AICHG-\d{5}$")
		self.assertEqual(code.change_status, "Chờ duyệt")
		self.assertEqual(code.change_kind, "Thay đổi code")
		self.assertEqual(code.reversible, 1)
		for fieldname in ("target_branch", "upstream_ref", "commit_message", "file_path", "diff"):
			with self.subTest(fieldname=fieldname):
				self.assertTrue(code.get(fieldname))
		command = make_change_proposal(kind=CHANGE_KIND_COMMAND)
		self.assertEqual(command.change_status, "Chờ duyệt")
		self.assertEqual(command.change_kind, "Lệnh bench")
		self.assertEqual(command.reversible, 0)
		self.assertIsInstance(json.loads(command.command_args), list)
		for fieldname in ("target_branch", "upstream_ref", "commit_message", "file_path"):
			with self.subTest(fieldname=fieldname):
				self.assertFalse(command.get(fieldname))
		self.assertEqual((command.ahead_count, command.is_core_app), (0, 0))

	def test_form_layout_git_sections(self):
		doctype = _load_json()
		self.assertEqual(doctype["field_order"], FIELD_ORDER)
		self.assertEqual([field["fieldname"] for field in doctype["fields"]], FIELD_ORDER)
		fields = _fields_by_name()
		sections = [
			(name, fields[name]["label"], fields[name].get("depends_on"))
			for name in FIELD_ORDER
			if fields[name]["fieldtype"] == "Section Break"
		]
		self.assertEqual(
			sections,
			[
				("section_proposal", "Đề xuất", None),
				("section_git", "Commit git sẽ tạo", "eval:doc.change_kind=='Thay đổi code'"),
				("section_git_result", "Commit đã tạo", "eval:doc.apply_commit_sha"),
				("section_diff", "Diff", "eval:doc.change_kind=='Thay đổi code'"),
				("section_content", "Nội dung đầy đủ", "eval:doc.change_kind=='Thay đổi code'"),
				("section_command", "Lệnh bench", "eval:doc.change_kind=='Lệnh bench'"),
				("section_decision", "Duyệt và kết quả", None),
			],
		)
		self.assertEqual(fields["section_content"].get("collapsible"), 1)
		self.assertEqual(fields["upstream_ref"].get("depends_on"), "eval:doc.upstream_ref")
		self.assertEqual(fields["ahead_count"].get("depends_on"), "eval:doc.upstream_ref")
		self.assertEqual(fields["undo_commit_sha"].get("depends_on"), "eval:doc.undo_commit_sha")
		columns = [name for name in FIELD_ORDER if fields[name]["fieldtype"] == "Column Break"]
		self.assertEqual(columns, ["column_proposal", "column_git", "column_git_result"])
		for fieldname in GIT_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(fields[fieldname].get("read_only"), 1)
		self.assertEqual(
			{name: fields[name]["fieldtype"] for name in GIT_FIELDS},
			{
				"target_branch": "Data",
				"upstream_ref": "Data",
				"ahead_count": "Int",
				"is_core_app": "Check",
				"commit_message": "Code",
				"applied_branch": "Data",
				"applied_ahead_count": "Int",
				"apply_commit_sha": "Data",
				"undo_commit_sha": "Data",
			},
		)

	def test_exit_code_hidden_when_unknown(self):
		# Design addendum 3 QĐ-B4: the Int column stores 0 when there is no exit code (out of budget,
		# `TimeoutExpired`, never ran); the form shows it only once applied or when the code is not 0.
		self.assertEqual(
			_fields_by_name()["exit_code"].get("depends_on"),
			'eval:doc.change_status=="Đã áp dụng" || doc.exit_code',
		)


METHOD_MODULE = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal"
METHOD_NAMES = ("approve", "reject", "undo")
# Every whitelisted method of the controller (CHG-002 T24 adds `confirm_restart`).
WHITELISTED_NAMES = (*METHOD_NAMES, "confirm_restart")
RUN_CHANGE = "erp_ai.agent.changes.apply_job.run_change"
# Design 3.3 error sentences, copied by hand.
ROLE_REFUSAL = "Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được"
COMMAND_UNDO_REFUSAL = "Lệnh bench không hoàn tác được"
METHOD_INSTRUCTOR = "change.method.instructor@example.com"
METHOD_PLAIN = "change.method.plain@example.com"
METHOD_ASSIGNEE = "change.method.assignee@example.com"
METHOD_ASSIGNER = "change.method.assigner@example.com"
DECISION_FIELDS = (
	"change_status",
	"decided_by",
	"decided_at",
	"approved_digest",
	"undo_by",
	"undo_at",
	"finished_at",
	"modified",
)
# The state each method starts from when the caller is allowed (only the refusal under test can stop it).
START_STATUS = {
	"approve": CHANGE_STATUS_PENDING,
	"reject": CHANGE_STATUS_PENDING,
	"undo": CHANGE_STATUS_APPLIED,
}
ALL_STATUSES = (
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
)


def _proposal_in(status, kind=CHANGE_KIND_CODE):
	proposal = make_change_proposal(kind=kind)
	frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, "change_status", status, update_modified=False)
	return proposal.name


def _change_rows(name) -> list:
	return frappe.get_all(
		LOG_DOCTYPE,
		filters={"change_proposal": name},
		fields=["change_step", "actor", "ticket"],
		order_by="creation asc",
	)


class TestChangeProposalMethods(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		for email in (METHOD_INSTRUCTOR, METHOD_PLAIN, METHOD_ASSIGNEE, METHOD_ASSIGNER):
			create_agent(email)
		if not frappe.db.exists("User", AGENT_USER):
			create_agent(AGENT_USER)
		frappe.get_doc("User", METHOD_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		enqueue = patch("frappe.enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)

	def _change_jobs(self) -> list:
		return [call for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_CHANGE]

	def _call_as(self, user, method, name):
		frappe.set_user(user)
		try:
			return getattr(controller, method)(name)
		finally:
			frappe.set_user("Administrator")

	def _snapshot(self, name):
		return (
			frappe.db.get_value(PROPOSAL_DOCTYPE, name, list(DECISION_FIELDS), as_dict=True),
			_change_rows(name),
			frappe.db.count(LOG_DOCTYPE),
		)

	def assertRefused(self, user, method, name, error, message, proposal=None):
		"""`method(name)` as `user` raises exactly `error`/`message`; DB, log rows and change jobs unchanged."""
		proposal = name if proposal is None else proposal
		before = self._snapshot(proposal)
		with self.assertRaises(error) as caught:
			self._call_as(user, method, name)
		self.assertIs(type(caught.exception), error)
		self.assertEqual(str(caught.exception), message)
		self.assertEqual(self._snapshot(proposal), before)
		self.assertEqual(self._change_jobs(), [])

	def test_methods_refuse_agent_admin_guest_and_user_without_role(self):
		self.assertEqual(authority.NEVER_AUTHORITY, frozenset({"Administrator", "Guest", AGENT_USER}))
		self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles(METHOD_PLAIN))
		cases = [(user, False) for user in (AGENT_USER, "Administrator", "Guest", METHOD_PLAIN)]
		# The other side of the condition: an account that never carries authority, even holding the role.
		cases += [(user, True) for user in (AGENT_USER, "Administrator", "Guest")]
		for method in METHOD_NAMES:
			for user, holds_role in cases:
				with self.subTest(method=method, user=user, holds_role=holds_role):
					name = _proposal_in(START_STATUS[method])
					roles = patch("frappe.get_roles", return_value=[ROLE_INSTRUCTOR]) if holds_role else None
					if roles:
						roles.start()
					try:
						self.assertRefused(user, method, name, frappe.PermissionError, ROLE_REFUSAL)
					finally:
						if roles:
							roles.stop()
			with self.subTest(method=method, check="role before existence"):
				name = _proposal_in(START_STATUS[method])
				self.assertRefused(
					METHOD_PLAIN, method, "AICHG-99999", frappe.PermissionError, ROLE_REFUSAL, proposal=name
				)

	def test_assigned_user_without_role_cannot_approve(self):
		for method in METHOD_NAMES:
			with self.subTest(method=method):
				name = _proposal_in(START_STATUS[method])
				ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
				todo = make_todo(ticket, METHOD_ASSIGNEE)
				frappe.db.set_value("ToDo", todo, "assigned_by", METHOD_ASSIGNER)
				# The boundary: the assignee's comments ARE instructions, yet the role is still missing.
				self.assertTrue(authority.is_instruction(METHOD_ASSIGNEE, ticket))
				self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles(METHOD_ASSIGNEE))
				self.assertRefused(METHOD_ASSIGNEE, method, name, frappe.PermissionError, ROLE_REFUSAL)

	def test_ok_comment_by_instructor_keeps_pending(self):
		name = _proposal_in(CHANGE_STATUS_PENDING)
		ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
		before = self._snapshot(name)[:2]
		frappe.set_user(METHOD_INSTRUCTOR)
		try:
			for content in ("ok", "duyệt", f"ok duyệt {name}"):
				frappe.get_doc("HD Ticket", ticket).new_comment(content)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.count(
				"Comment", {"reference_name": ticket, "comment_type": "Comment", "owner": METHOD_INSTRUCTOR}
			),
			3,
		)
		self.assertEqual(self._snapshot(name)[:2], before)
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status"), "Chờ duyệt")
		self.assertEqual(self._change_jobs(), [])

	def test_rejected_never_applies(self):
		name = _proposal_in(CHANGE_STATUS_PENDING)
		ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
		self.assertEqual(
			self._call_as(METHOD_INSTRUCTOR, "reject", name), {"name": name, "status": "Đã từ chối"}
		)
		stored = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "decided_by", "approved_digest"], as_dict=True
		)
		self.assertEqual(
			stored, {"change_status": "Đã từ chối", "decided_by": METHOD_INSTRUCTOR, "approved_digest": None}
		)
		self.assertEqual(
			_change_rows(name), [{"change_step": "reject", "actor": METHOD_INSTRUCTOR, "ticket": ticket}]
		)
		self.assertEqual(self._change_jobs(), [])
		self.assertRefused(
			METHOD_INSTRUCTOR,
			"approve",
			name,
			transitions.InvalidTransition,
			"Đề xuất đang ở trạng thái Đã từ chối, không duyệt được",
		)

	def test_approve_and_reject_refused_outside_pending(self):
		verbs = {"approve": "duyệt", "reject": "từ chối"}
		for method, verb in verbs.items():
			for status in ALL_STATUSES[1:]:
				with self.subTest(method=method, status=status):
					name = _proposal_in(status)
					self.assertRefused(
						METHOD_INSTRUCTOR,
						method,
						name,
						transitions.InvalidTransition,
						f"Đề xuất đang ở trạng thái {status}, không {verb} được",
					)

	def test_methods_are_post_only_and_not_guest(self):
		own = {fn.__name__ for fn in frappe.whitelisted if getattr(fn, "__module__", None) == METHOD_MODULE}
		self.assertEqual(own, set(WHITELISTED_NAMES))
		for method in WHITELISTED_NAMES:
			with self.subTest(method=method):
				fn = getattr(controller, method)
				self.assertIn(fn, frappe.whitelisted)
				self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
				self.assertNotIn(fn, frappe.guest_methods)
				self.assertEqual(frappe.get_attr(f"{METHOD_MODULE}.{method}"), fn)
				# The request check Frappe's handler runs before the method: GET is refused, POST passes.
				with patch.object(frappe.local, "request", SimpleNamespace(method="GET"), create=True):
					with self.assertRaises(frappe.PermissionError):
						frappe.handler.is_valid_http_method(fn)
				with patch.object(frappe.local, "request", SimpleNamespace(method="POST"), create=True):
					frappe.handler.is_valid_http_method(fn)

	def test_undo_refused_for_command_and_non_applied(self):
		for status in ALL_STATUSES:
			with self.subTest(kind=CHANGE_KIND_COMMAND, status=status):
				name = _proposal_in(status, kind=CHANGE_KIND_COMMAND)
				self.assertRefused(
					METHOD_INSTRUCTOR, "undo", name, transitions.InvalidTransition, COMMAND_UNDO_REFUSAL
				)
		for status in ALL_STATUSES:
			if status == CHANGE_STATUS_APPLIED:
				continue
			with self.subTest(kind=CHANGE_KIND_CODE, status=status):
				name = _proposal_in(status)
				self.assertRefused(
					METHOD_INSTRUCTOR,
					"undo",
					name,
					transitions.InvalidTransition,
					f"Đề xuất đang ở trạng thái {status}, không hoàn tác được",
				)

	def test_approve_success_enqueues_one_job_and_logs_one_row(self):
		name = _proposal_in(CHANGE_STATUS_PENDING)
		ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
		status_at_enqueue = []
		self.enqueue.side_effect = lambda *args, **kwargs: status_at_enqueue.append(
			frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status")
		)
		self.assertEqual(
			self._call_as(METHOD_INSTRUCTOR, "approve", name), {"name": name, "status": "Đã duyệt"}
		)
		stored = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "decided_by", "approved_digest"], as_dict=True
		)
		self.assertEqual((stored.change_status, stored.decided_by), ("Đã duyệt", METHOD_INSTRUCTOR))
		self.assertEqual(
			stored.approved_digest, transitions.content_digest(frappe.get_doc(PROPOSAL_DOCTYPE, name))
		)
		self.assertEqual(
			_change_rows(name), [{"change_step": "approve", "actor": METHOD_INSTRUCTOR, "ticket": ticket}]
		)
		jobs = self._change_jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0].kwargs["proposal_name"], name)
		self.assertEqual(jobs[0].kwargs["action"], "apply")
		self.assertEqual(jobs[0].kwargs["job_id"], f"erp_ai_change::{name}::apply")
		# The job is queued after the transition, never before it.
		self.assertEqual(status_at_enqueue, ["Đã duyệt"])

	def test_undo_success_enqueues_one_undo_job_without_row(self):
		name = _proposal_in(CHANGE_STATUS_APPLIED)
		status_at_enqueue = []
		self.enqueue.side_effect = lambda *args, **kwargs: status_at_enqueue.append(
			frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status")
		)
		self.assertEqual(
			self._call_as(METHOD_INSTRUCTOR, "undo", name), {"name": name, "status": "Đang hoàn tác"}
		)
		stored = frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["change_status", "undo_by"], as_dict=True)
		self.assertEqual((stored.change_status, stored.undo_by), ("Đang hoàn tác", METHOD_INSTRUCTOR))
		self.assertEqual(_change_rows(name), [])
		jobs = self._change_jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual((jobs[0].kwargs["proposal_name"], jobs[0].kwargs["action"]), (name, "undo"))
		self.assertEqual(status_at_enqueue, ["Đang hoàn tác"])

	def test_bad_or_unknown_name_is_does_not_exist(self):
		# Hand-written escaped sentences (design 3.3): `name` is not a string, blank, or no such proposal.
		cases = (
			(None, "Không có đề xuất "),
			(123, "Không có đề xuất 123"),
			(["<x>"], "Không có đề xuất [&apos;&lt;x&gt;&apos;]"),
			("", "Không có đề xuất "),
			("   ", "Không có đề xuất    "),
			("AICHG-99999", "Không có đề xuất AICHG-99999"),
			('<img src=x onerror="a">', "Không có đề xuất &lt;img src=x onerror=&quot;a&quot;&gt;"),
		)
		witness = _proposal_in(CHANGE_STATUS_PENDING)
		for method in METHOD_NAMES:
			for name, message in cases:
				with self.subTest(method=method, name=name):
					self.assertRefused(
						METHOD_INSTRUCTOR, method, name, frappe.DoesNotExistError, message, proposal=witness
					)

	def test_methods_missing_name_is_not_found(self):
		"""Design 3.3 error table after addendum 3 QĐ-B6: `name` missing, not a string or unknown → 404.

		Called the way Frappe's handler does (`frappe.call` with the form dict) on the whitelisted function,
		so the wrapper's type validation runs (`in_test`) and a missing `name` reaches the method.
		"""
		cases = (
			({}, "Không có đề xuất "),
			({"name": None}, "Không có đề xuất "),
			({"name": 123}, "Không có đề xuất 123"),
			({"name": ["<x>"]}, "Không có đề xuất [&apos;&lt;x&gt;&apos;]"),
		)
		witness = _proposal_in(CHANGE_STATUS_PENDING)
		self.assertTrue(frappe.flags.in_test)
		for method in METHOD_NAMES:
			for form_dict, message in cases:
				with self.subTest(method=method, form_dict=form_dict):
					before = self._snapshot(witness)
					frappe.set_user(METHOD_INSTRUCTOR)
					try:
						with self.assertRaises(frappe.DoesNotExistError) as caught:
							frappe.call(f"{METHOD_MODULE}.{method}", **form_dict)
					finally:
						frappe.set_user("Administrator")
					self.assertIs(type(caught.exception), frappe.DoesNotExistError)
					self.assertEqual(str(caught.exception), message)
					self.assertEqual(self._snapshot(witness), before)
					self.assertEqual(self._change_jobs(), [])

	def _form_as(self, user, name):
		"""The document Desk receives from `getdoc` for `user` (design 3.3 form data)."""
		frappe.set_user(user)
		frappe.response.docs = []
		try:
			frappe.desk.form.load.getdoc(PROPOSAL_DOCTYPE, name)
			return frappe.response.docs[0]
		finally:
			frappe.response.docs = []
			frappe.set_user("Administrator")

	def test_form_data_per_state(self):
		# Design 3.9 sentences, copied by hand.
		branch = "Commit sẽ vào nhánh main của app myapp."
		upstream = (
			"Nhánh này theo origin/main và đang đi trước 2 commit (tính theo lần fetch cuối trên máy chủ)."
		)
		no_upstream = "Nhánh này không theo nhánh remote nào."
		core_warning = (
			"Cảnh báo app lõi: myapp dùng chung cho mọi site trên bench này, nên thay đổi ảnh hưởng tất cả"
			" các site. bench update không giữ commit local: nó dừng nếu kho có thay đổi chưa commit; khi"
			" kho sạch, nó kéo bằng git pull (merge) từ remote upstream hoặc remote đầu tiên, có thể tạo"
			" merge commit hoặc xung đột; bench update --reset xóa vĩnh viễn commit chưa đẩy. Đẩy commit"
			" lên fork là việc của người, làm trước khi chạy bench update."
		)
		restart = "Sau khi áp dụng cần người chạy bench restart."
		apply_sha = "a" * 40
		undo_sha = "b" * 40

		core = make_change_proposal(is_core_app=1, ahead_count=2)
		preview = (
			f"erp_ai: áp dụng {core.name} (myapp/myapp/ok.py)\n\nĐề xuất: {core.name}\nPhiếu: {core.ticket}\n"
			"Người duyệt: <người duyệt>\nCommit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt."
		)

		with self.subTest(status="Chờ duyệt", app="core", upstream=True):
			form = self._form_as(METHOD_INSTRUCTOR, core.name)
			self.assertEqual(form.change_status, "Chờ duyệt")
			self.assertEqual(
				(form.app, form.file_path, form.target_branch, form.commit_message, form.reversible),
				("myapp", "myapp/myapp/ok.py", "main", preview, 1),
			)
			self.assertIn("+++ b/myapp/myapp/ok.py", form.diff)
			self.assertEqual(form.get("__onload").change_notes, [branch, upstream, core_warning, restart])

		plain = make_change_proposal(upstream_ref="")
		with self.subTest(status="Chờ duyệt", app="not core", upstream=False):
			form = self._form_as(METHOD_INSTRUCTOR, plain.name)
			self.assertEqual(form.get("__onload").change_notes, [branch, no_upstream, restart])

		frappe.db.set_value(
			PROPOSAL_DOCTYPE,
			core.name,
			{"change_status": CHANGE_STATUS_APPLIED, "apply_commit_sha": apply_sha},
			update_modified=False,
		)
		with self.subTest(status="Đã áp dụng"):
			form = self._form_as(METHOD_INSTRUCTOR, core.name)
			self.assertEqual((form.change_status, form.apply_commit_sha), ("Đã áp dụng", apply_sha))
			self.assertFalse(form.undo_commit_sha)
			self.assertEqual(
				form.get("__onload").change_notes,
				[branch, upstream, core_warning, f"Commit áp dụng: {apply_sha}.", restart],
			)

		frappe.db.set_value(
			PROPOSAL_DOCTYPE,
			core.name,
			{"change_status": CHANGE_STATUS_UNDONE, "undo_commit_sha": undo_sha},
			update_modified=False,
		)
		with self.subTest(status="Đã hoàn tác"):
			form = self._form_as(METHOD_INSTRUCTOR, core.name)
			self.assertEqual(
				(form.change_status, form.apply_commit_sha, form.undo_commit_sha),
				("Đã hoàn tác", apply_sha, undo_sha),
			)
			self.assertEqual(
				form.get("__onload").change_notes,
				[branch, upstream, core_warning, f"Commit hoàn tác: {undo_sha}.", restart],
			)

		command = make_change_proposal(kind=CHANGE_KIND_COMMAND)
		with self.subTest(kind="Lệnh bench"):
			form = self._form_as(METHOD_INSTRUCTOR, command.name)
			self.assertFalse(form.commit_message)
			self.assertEqual(form.get("__onload").change_notes, ["Lệnh bench không hoàn tác được."])


RESTART_SYSTEM_MANAGER = "change.restart.sysmanager@example.com"
RESTART_LOG_FORMAT = "erp_ai restart proposal=%s status=%s"
# A fixed send moment in the site's timezone (naive, as Frappe stores Datetime fields); never the wall clock.
RESTART_SENT_AT = datetime.datetime(2026, 1, 5, 10, 0, 0)
NOT_SENT_STATUSES = (
	None,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_UNCONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
)


def _sent_epoch(sent_at=RESTART_SENT_AT) -> float:
	return restart_check.epoch_of_system_time(sent_at, frappe.utils.get_system_timezone())


def _restart_row(name) -> frappe._dict:
	return frappe.db.get_value(
		PROPOSAL_DOCTYPE, name, ["restart_status", "restart_sent_at", "modified"], as_dict=True
	)


class TestConfirmRestart(FrappeTestCase):
	"""CHG-002 T24: `confirm_restart` (design 3.3, 4.4 step 5; addendum-1 A-2.1; addendum-5 P-4)."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		for email in (METHOD_INSTRUCTOR, METHOD_PLAIN, RESTART_SYSTEM_MANAGER):
			create_agent(email)
		if not frappe.db.exists("User", AGENT_USER):
			create_agent(AGENT_USER)
		frappe.get_doc("User", METHOD_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		frappe.get_doc("User", RESTART_SYSTEM_MANAGER).add_roles("System Manager")
		# Evidence and "now" are stubbed: no real process, no Redis, no wall clock.
		self.web = self._start(patch.object(restart_check, "web_started", return_value=None))
		self.workers = self._start(patch.object(restart_check, "workers_started", return_value=None))
		self.now = self._start(
			patch.object(
				controller, "now_datetime", return_value=RESTART_SENT_AT + datetime.timedelta(seconds=5)
			)
		)
		self.logger = self._start(patch.object(controller.frappe, "logger"))

	def _start(self, patcher):
		mock = patcher.start()
		self.addCleanup(patcher.stop)
		return mock

	def _proposal(self, restart_status=RESTART_STATUS_SENT, sent_at=RESTART_SENT_AT) -> str:
		name = _proposal_in(CHANGE_STATUS_APPLIED)
		frappe.db.set_value(
			PROPOSAL_DOCTYPE,
			name,
			{"restart_status": restart_status, "restart_sent_at": sent_at},
			update_modified=False,
		)
		return name

	def _evidence_confirms(self):
		"""Both processes started after the send: `outcome` would conclude `Đã xác nhận`."""
		self.web.return_value = _sent_epoch() + 3
		self.workers.return_value = _sent_epoch() + 4

	def _call_as(self, user, name):
		frappe.set_user(user)
		try:
			return controller.confirm_restart(name)
		finally:
			frappe.set_user("Administrator")

	def _conclusion_lines(self) -> list:
		return [
			c for c in self.logger.return_value.info.call_args_list if c.args[:1] == (RESTART_LOG_FORMAT,)
		]

	def assertRefused(self, user, name, error, message, proposal=None):
		"""`confirm_restart(name)` as `user` raises exactly `error`/`message`; no evidence read, nothing written."""
		proposal = name if proposal is None else proposal
		before = _restart_row(proposal)
		self._evidence_confirms()
		with patch.object(transitions, "confirm_restart") as write:
			with self.assertRaises(error) as caught:
				self._call_as(user, name)
		self.assertIs(type(caught.exception), error)
		self.assertEqual(str(caught.exception), message)
		self.assertEqual(write.call_count, 0)
		self.assertEqual((self.web.call_count, self.workers.call_count), (0, 0))
		self.assertEqual(_restart_row(proposal), before)
		self.assertEqual(self._conclusion_lines(), [])

	def test_only_from_sent(self):
		for status in NOT_SENT_STATUSES:
			with self.subTest(restart_status=status):
				name = self._proposal(restart_status=status)
				self._evidence_confirms()
				before = _restart_row(name)
				with patch.object(transitions, "confirm_restart", wraps=transitions.confirm_restart) as write:
					result = self._call_as(METHOD_INSTRUCTOR, name)
				self.assertEqual(result, {"name": name, "status": status})
				self.assertEqual(write.call_count, 0)
				self.assertEqual(_restart_row(name), before)
				self.assertEqual(self._conclusion_lines(), [])

	def test_no_conclusion_writes_nothing(self):
		cases = {
			"no evidence, before the deadline": (None, None, 5),
			"web only, before the deadline": (_sent_epoch() + 3, None, 5),
			"started before the send, at the deadline": (
				_sent_epoch() - 1,
				_sent_epoch() - 1,
				RESTART_TIMEOUT_S,
			),
		}
		for label, (web, workers, elapsed) in cases.items():
			with self.subTest(case=label):
				name = self._proposal()
				self.web.return_value, self.workers.return_value = web, workers
				self.now.return_value = RESTART_SENT_AT + datetime.timedelta(seconds=elapsed)
				before = _restart_row(name)
				with patch.object(transitions, "confirm_restart") as write:
					result = self._call_as(METHOD_INSTRUCTOR, name)
				self.assertEqual(result, {"name": name, "status": RESTART_STATUS_SENT})
				self.assertEqual(write.call_count, 0)
				self.assertEqual(_restart_row(name), before)
				self.assertEqual(self._conclusion_lines(), [])
		with self.subTest(case="sent without a send time"):
			# Both processes "start" ~300 years after the fixed send: later than any moment a missing send
			# time could be read as (`get_datetime(None)` is the real now), so only the guard stops a write.
			name = self._proposal(sent_at=None)
			self.web.return_value = self.workers.return_value = _sent_epoch() + 10**10
			before = _restart_row(name)
			with patch.object(transitions, "confirm_restart") as write:
				result = self._call_as(METHOD_INSTRUCTOR, name)
			self.assertEqual(result, {"name": name, "status": RESTART_STATUS_SENT})
			self.assertEqual(write.call_count, 0)
			self.assertEqual(_restart_row(name), before)
			self.assertEqual(self._conclusion_lines(), [])

	def test_agent_account_refused(self):
		for holds_role in (False, True):
			with self.subTest(holds_role=holds_role):
				name = self._proposal()
				with patch("frappe.get_roles", return_value=[ROLE_INSTRUCTOR] if holds_role else []):
					self.assertRefused(AGENT_USER, name, frappe.PermissionError, ROLE_REFUSAL)

	def test_administrator_guest_no_role_refused(self):
		self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles(METHOD_PLAIN))
		for user in ("Administrator", "Guest", METHOD_PLAIN):
			with self.subTest(user=user):
				self.assertRefused(user, self._proposal(), frappe.PermissionError, ROLE_REFUSAL)
		for user in ("Administrator", "Guest"):
			with self.subTest(user=user, holds_role=True):
				with patch("frappe.get_roles", return_value=[ROLE_INSTRUCTOR]):
					self.assertRefused(user, self._proposal(), frappe.PermissionError, ROLE_REFUSAL)
		with self.subTest(check="role before existence"):
			self.assertRefused(
				METHOD_PLAIN, "AICHG-99999", frappe.PermissionError, ROLE_REFUSAL, proposal=self._proposal()
			)

	def test_system_manager_without_instructor_refused_status_unchanged(self):
		roles = frappe.get_roles(RESTART_SYSTEM_MANAGER)
		self.assertIn("System Manager", roles)
		self.assertNotIn(ROLE_INSTRUCTOR, roles)
		name = self._proposal()
		self.assertRefused(RESTART_SYSTEM_MANAGER, name, frappe.PermissionError, ROLE_REFUSAL)
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "restart_status"), RESTART_STATUS_SENT)

	def test_instructor_records_conclusion(self):
		cases = {
			RESTART_STATUS_CONFIRMED: (_sent_epoch() + 3, _sent_epoch() + 4, 5),
			RESTART_STATUS_UNCONFIRMED: (_sent_epoch() + 3, None, RESTART_TIMEOUT_S + 1),
		}
		for expected, (web, workers, elapsed) in cases.items():
			with self.subTest(conclusion=expected):
				self.logger.reset_mock()
				name = self._proposal()
				self.web.return_value, self.workers.return_value = web, workers
				self.now.return_value = RESTART_SENT_AT + datetime.timedelta(seconds=elapsed)
				result = self._call_as(METHOD_INSTRUCTOR, name)
				self.assertEqual(result, {"name": name, "status": expected})
				stored = _restart_row(name)
				self.assertEqual((stored.restart_status, stored.restart_sent_at), (expected, RESTART_SENT_AT))
				self.assertEqual(self._conclusion_lines(), [call(RESTART_LOG_FORMAT, name, expected)])
				self.assertIn(call("erp_ai"), self.logger.call_args_list)

	def test_uses_decider(self):
		name = self._proposal()
		self._evidence_confirms()
		order = []
		real_get_value = frappe.db.get_value

		def reading(doctype, *args, **kwargs):
			if doctype == PROPOSAL_DOCTYPE:
				order.append("read")
			return real_get_value(doctype, *args, **kwargs)

		def deciding(_name):
			order.append("decider")
			return METHOD_INSTRUCTOR

		self.web.side_effect = lambda: order.append("evidence") or _sent_epoch() + 3
		with patch.object(controller, "_decider", side_effect=deciding) as decider:
			with patch.object(frappe.db, "get_value", side_effect=reading):
				result = self._call_as(METHOD_INSTRUCTOR, name)
		self.assertEqual(decider.call_args_list, [call(name)])
		self.assertEqual(order[0], "decider")
		self.assertEqual(order.count("decider"), 1)
		self.assertIn("read", order)
		self.assertIn("evidence", order)
		self.assertEqual(result, {"name": name, "status": RESTART_STATUS_CONFIRMED})
		with self.subTest(check="the decider's refusal stops everything"):
			other = self._proposal()
			refusal = frappe.PermissionError("refused by the decider")
			with patch.object(controller, "_decider", side_effect=refusal) as decider:
				with self.assertRaises(frappe.PermissionError):
					self._call_as(METHOD_INSTRUCTOR, other)
			self.assertEqual(decider.call_args_list, [call(other)])
			self.assertEqual(
				frappe.db.get_value(PROPOSAL_DOCTYPE, other, "restart_status"), RESTART_STATUS_SENT
			)

	def test_missing_proposal_does_not_exist(self):
		witness = self._proposal()
		cases = (
			(None, "Không có đề xuất "),
			("", "Không có đề xuất "),
			("AICHG-99999", "Không có đề xuất AICHG-99999"),
		)
		for name, message in cases:
			with self.subTest(name=name):
				self.assertRefused(
					METHOD_INSTRUCTOR, name, frappe.DoesNotExistError, message, proposal=witness
				)

	def test_passes_sent_at_it_read(self):
		name = self._proposal()
		self._evidence_confirms()
		with patch.object(transitions, "confirm_restart", return_value=True) as write:
			result = self._call_as(METHOD_INSTRUCTOR, name)
		self.assertEqual(
			write.call_args_list, [call(name, RESTART_STATUS_CONFIRMED, sent_at=RESTART_SENT_AT)]
		)
		self.assertIsInstance(write.call_args.kwargs["sent_at"], datetime.datetime)
		self.assertEqual(result, {"name": name, "status": RESTART_STATUS_CONFIRMED})

	def test_resent_between_read_and_write_keeps_new_status(self):
		resent_at = RESTART_SENT_AT + datetime.timedelta(seconds=30)
		cases = {
			"sent again": (RESTART_STATUS_SENT, resent_at),
			"launch failed": (RESTART_STATUS_LAUNCH_FAILED, resent_at),
		}
		for label, (new_status, new_sent_at) in cases.items():
			with self.subTest(case=label):
				self.logger.reset_mock()
				name = self._proposal()
				self.workers.return_value = _sent_epoch() + 4

				def resend_while_reading(name=name, new_status=new_status, new_sent_at=new_sent_at):
					# The undo job's `record_restart` lands between the evidence read and the write.
					frappe.db.set_value(
						PROPOSAL_DOCTYPE,
						name,
						{"restart_status": new_status, "restart_sent_at": new_sent_at},
						update_modified=False,
					)
					return _sent_epoch() + 3

				self.web.side_effect = resend_while_reading
				with patch.object(transitions, "confirm_restart", wraps=transitions.confirm_restart) as write:
					result = self._call_as(METHOD_INSTRUCTOR, name)
				self.web.side_effect = None
				self.assertEqual(
					write.call_args_list, [call(name, RESTART_STATUS_CONFIRMED, sent_at=RESTART_SENT_AT)]
				)
				self.assertEqual(result, {"name": name, "status": new_status})
				stored = _restart_row(name)
				self.assertEqual((stored.restart_status, stored.restart_sent_at), (new_status, new_sent_at))
				self.assertEqual(self._conclusion_lines(), [])


FORM_SCRIPT_PATH = Path(__file__).resolve().parent / "erp_ai_change_proposal.js"
# The three whitelisted methods (design 3.3), written out by hand.
APPROVE_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.approve"
REJECT_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.reject"
UNDO_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.undo"
CONFIRM_RESTART_PATH = (
	"erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.confirm_restart"
)
ROLE_CHECK = 'frappe.user.has_role("ERP AI Instructor")'
# Design 3.7 line 5 of the block notes, which the undo confirmation repeats.
COMMAND_UNDO_NOTE = "Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file."
# The only pieces a form condition is written with; anything else makes `_condition_holds` fail.
_CONDITION_TOKEN = re.compile(
	r"\s+|frm\.doc\.(?P<field>\w+)|frappe\.user\.has_role\(\"(?P<role>[^\"]+)\"\)"
	r'|"(?P<text>[^"\\]*)"|(?P<op>===|!==|&&|\|\||!|\(|\))'
)
_CONDITION_OPERATORS = {"===": " == ", "!==": " != ", "&&": " and ", "||": " or ", "(": "(", ")": ")"}


def _without_comments(source: str) -> str:
	"""The script text with `//` and `/* */` comments removed; string literals are kept as they are."""
	return re.sub(
		r'("(?:\\.|[^"\\\n])*")|/\*.*?\*/|//[^\n]*',
		lambda match: match.group(1) or "",
		source,
		flags=re.DOTALL,
	)


def _statement(code: str) -> str:
	"""Regex for `code` written in full, allowing any line breaks and indent the formatter adds."""
	parts = []
	for token in re.split(r"(\s+|[\(\)\[\]])", code):
		if not token:
			continue
		if token.isspace():
			parts.append(r"\s+")
		elif token in "([":
			parts.append(re.escape(token) + r"\s*")
		elif token in ")]":
			parts.append(r"\s*,?\s*" + re.escape(token))
		else:
			parts.append(re.escape(token))
	return "".join(parts)


def _button_pattern(label: str, method_path: str) -> str:
	"""One `add_action_button(frm, __("<label>"), <confirm>, "<method>")` call site."""
	return (
		r'add_action_button\(\s*frm,\s*__\("'
		+ re.escape(label)
		+ r'"\),[^;]*?"'
		+ re.escape(method_path)
		+ r'"\s*\)'
	)


def _block_after(source: str, condition_pattern: str) -> str:
	"""Body of the first `if (<condition>) { ... }` block, up to its closing brace at the same indent."""
	match = re.search(r"\n(\t+)if \(\s*" + condition_pattern + r"\s*\) \{\n(.*?)\n\1\}", source, re.DOTALL)
	return match.group(2) if match else ""


def _function_return(source: str, name: str) -> str:
	"""The expression of `function <name>(frm) { return <expression>; }`, the whole body of that function."""
	match = re.search(r"\nfunction " + name + r"\(frm\) \{\s*return (.*?);\s*\n\}", source, re.DOTALL)
	return match.group(1) if match else ""


def _condition_holds(expression: str, doc: dict, roles: set) -> bool:
	"""Value of a form condition for one document and one user's roles, read token by token.

	Only `frm.doc.<field>`, `frappe.user.has_role("<role>")`, string literals, `===`, `!==`, `&&`, `||`,
	`!` and parentheses are understood, with JavaScript truthiness for an empty or missing field.
	`!` must stand right before a field or a role check, so it binds as tightly as in JavaScript.
	"""
	if not expression:
		raise AssertionError("condition not found in the form script")
	parts, at, negate = [], 0, False
	while at < len(expression):
		token = _CONDITION_TOKEN.match(expression, at)
		if not token:
			raise AssertionError(f"condition piece not understood: {expression[at:at + 30]!r}")
		at = token.end()
		if token.group("field"):
			atom = f"doc.get({token.group('field')!r})"
		elif token.group("role"):
			atom = f"({token.group('role')!r} in roles)"
		elif token.group("text") is not None:
			atom = repr(token.group("text"))
		elif token.group("op") == "!":
			negate = True
			continue
		elif token.group("op"):
			atom = _CONDITION_OPERATORS[token.group("op")]
		else:
			continue
		if negate and not (token.group("field") or token.group("role")):
			raise AssertionError(f"`!` before something other than a field or a role check: {expression!r}")
		parts.append(f"(not {atom})" if negate else atom)
		negate = False
	return bool(eval("".join(parts), {"__builtins__": {}}, {"doc": doc, "roles": roles}))


class TestChangeProposalFormScript(FrappeTestCase):
	"""Design 3.3 "Form Desk", AC-5, AC-22, ADR-022 QĐ 9: static rules on the form script text.

	The buttons are only a convenience (AC-5): the server checks role and state again.
	The real rendering is checked by hand after G4 (profile `ui: false`, dev-notes.md).
	"""

	def setUp(self):
		if not FORM_SCRIPT_PATH.exists():
			self.fail(f"form script missing: {FORM_SCRIPT_PATH.name}")
		# Every static check reads code only: a call written inside a comment does not count.
		self.source = _without_comments(FORM_SCRIPT_PATH.read_text(encoding="utf-8"))

	def test_form_script_static_rules(self):
		source = self.source
		self.assertIn('frappe.ui.form.on("ERP AI Change Proposal", {', source)
		self.assertIn("refresh(frm) {", source)

		with self.subTest(rule="each method path once, wired to its own button"):
			for label, method_path in (
				("Duyệt", APPROVE_PATH),
				("Từ chối", REJECT_PATH),
				("Hoàn tác", UNDO_PATH),
			):
				self.assertEqual(source.count(f'"{method_path}"'), 1, method_path)
				self.assertRegex(source, _button_pattern(label, method_path))

		with self.subTest(rule="role check returns before any button"):
			self.assertRegex(source, r"if \(!" + re.escape(ROLE_CHECK) + r"\) \{\s*return;\s*\}")
			self.assertLess(source.index(ROLE_CHECK), source.index("add_action_button(frm,"))

		with self.subTest(rule="Duyệt and Từ chối only when Chờ duyệt"):
			pending = _block_after(source, r'frm\.doc\.change_status === "Chờ duyệt"')
			self.assertRegex(pending, _button_pattern("Duyệt", APPROVE_PATH))
			self.assertRegex(pending, _button_pattern("Từ chối", REJECT_PATH))
			self.assertNotIn(UNDO_PATH, pending)

		with self.subTest(rule="Hoàn tác only when undo_allowed"):
			applied = _block_after(source, r"undo_allowed\(frm\)")
			self.assertRegex(applied, _button_pattern("Hoàn tác", UNDO_PATH))
			self.assertNotIn(APPROVE_PATH, applied)
			self.assertNotIn(REJECT_PATH, applied)

		with self.subTest(rule="confirm, then POST call with name, then reload_doc"):
			helper = re.search(
				r"function add_action_button\(frm, label, message, method\) \{\n(.*?)\n\}", source, re.DOTALL
			)
			self.assertIsNotNone(helper, "add_action_button helper missing")
			body = helper.group(1)
			self.assertIn("frm.add_custom_button(label,", body)
			for step in ("frappe.confirm(message,", "frappe.call({", "frm.reload_doc()"):
				self.assertIn(step, body)
			confirm_at = body.index("frappe.confirm(message,")
			call_at = body.index("frappe.call({")
			reload_at = body.index("frm.reload_doc()")
			self.assertLess(confirm_at, call_at)
			self.assertLess(call_at, reload_at)
			call = body[call_at:reload_at]
			self.assertIn("method,", call)
			self.assertIn("args: { name: frm.doc.name },", call)
			self.assertIn('type: "POST",', call)
			self.assertRegex(body[call_at:], _statement("callback: () => frm.reload_doc(),"))
			# The three buttons share this one confirmed POST call (design 3.3/T17).
			self.assertEqual(body.count("frm.reload_doc()"), 1)
			self.assertEqual(body.count("frappe.call("), 1)
			self.assertEqual(body.count('type: "POST"'), 1)
			self.assertEqual(source.count("frappe.confirm("), 1)
			self.assertEqual(source.count("frm.add_custom_button("), 1)

		with self.subTest(rule="signed link: one extra POST call to decide, no confirm (ADR-023 QĐ 1)"):
			outside = source.replace(helper.group(0), "")
			# The other call outside the helper is the one to confirm_restart (T25); its shape is pinned in test_calls_confirm_restart_only_when_sent.
			self.assertEqual(outside.count("frappe.call("), 2)
			call_at = outside.index("frappe.call(", outside.index("\nfunction decide_from_link(frm) {"))
			function_at = outside.rindex("\nfunction ", 0, call_at)
			function_end = outside.index("\n}", call_at)
			auto_block = outside[function_at:function_end]
			call = auto_block[auto_block.index("frappe.call(") :]
			self.assertIn('method: "erp_ai.change_decision.decide",', call)
			self.assertIn('type: "POST",', call)
			self.assertNotIn("frappe.confirm", auto_block)

		with self.subTest(rule="intro from __onload.change_notes, each line escaped"):
			self.assertIn("frm.doc.__onload", source)
			self.assertIn(".change_notes", source)
			self.assertRegex(
				source,
				r'frm\.set_intro\(\s*notes\.map\(frappe\.utils\.escape_html\)\.join\("<br>"\),\s*'
				r'frm\.doc\.is_core_app \? "orange" : "blue"\s*\)',
			)
			self.assertEqual(source.count("frm.set_intro("), 1)

		with self.subTest(rule="approve confirmation repeats branch line and core warning, escaped"):
			builder = re.search(
				r"function approve_confirm_message\(frm, notes\) \{\n(.*?)\n\}", source, re.DOTALL
			)
			self.assertIsNotNone(builder, "approve_confirm_message missing")
			body = builder.group(1)
			self.assertIn("frm.doc.is_core_app", body)
			self.assertIn(".map(frappe.utils.escape_html)", body)
			self.assertRegex(
				source,
				r'__\("Duyệt"\),\s*approve_confirm_message\(frm, notes\),\s*"'
				+ re.escape(APPROVE_PATH)
				+ '"',
			)
			notes = change_text.proposal_notes(
				{
					"change_kind": CHANGE_KIND_CODE,
					"app": "myapp",
					"target_branch": "main",
					"is_core_app": 1,
					"file_path": "myapp/x.js",
				}
			)
			for prefix_name, note_name in (
				("BRANCH_NOTE_PREFIX", "Commit sẽ vào nhánh "),
				("CORE_WARNING_PREFIX", "Cảnh báo app lõi: "),
			):
				literal = re.search(r"const " + prefix_name + r' = "([^"]+)";', source)
				self.assertIsNotNone(literal, prefix_name)
				self.assertEqual(literal.group(1), note_name)
				self.assertTrue(any(note.startswith(literal.group(1)) for note in notes), literal.group(1))
			self.assertRegex(
				body,
				_statement(
					"const branch_note = notes.find((note) => note.startsWith(BRANCH_NOTE_PREFIX));"
					" if (branch_note) { lines.push(branch_note); }"
				),
			)
			self.assertRegex(
				body,
				_statement(
					"const core_warning = notes.find((note) => note.startsWith(CORE_WARNING_PREFIX));"
					' if (frm.doc.is_core_app && core_warning) { lines.push(core_warning.split(". ")[0] + "."); }'
				),
			)
			self.assertRegex(body, _statement('return lines.map(frappe.utils.escape_html).join("<br>");'))
			self.assertEqual(body.count("lines.push("), 2)

		with self.subTest(rule="approve confirmation sentence follows change_kind"):
			builder = re.search(
				r"function approve_confirm_message\(frm, notes\) \{\n(.*?)\n\}", source, re.DOTALL
			)
			self.assertIsNotNone(builder, "approve_confirm_message missing")
			body = builder.group(1)
			command_note = "Lệnh bench không hoàn tác được."
			self.assertIn(command_note, change_text.proposal_notes({"change_kind": CHANGE_KIND_COMMAND}))
			# A bench command runs and cannot be undone; only a code change writes a file and commits.
			self.assertRegex(
				body,
				_statement(
					"const lines = frm.doc.change_kind === "
					+ json.dumps(CHANGE_KIND_COMMAND, ensure_ascii=False)
					+ ' ? [__("Duyệt đề xuất này? Lệnh bench sẽ chạy."), __('
					+ json.dumps(command_note, ensure_ascii=False)
					+ ')] : [__("Duyệt đề xuất này? File sẽ được ghi và có một commit.")];'
				),
			)
			self.assertEqual(source.count("File sẽ được ghi"), 1)

		with self.subTest(rule="Từ chối and Hoàn tác confirmations state what is written"):
			pending = _block_after(source, r'frm\.doc\.change_status === "Chờ duyệt"')
			self.assertNotIn("Không có gì được ghi", source)
			self.assertIn("Không có file nào được ghi, không có lệnh nào chạy.", pending)
			undo_message = re.search(
				r"function undo_confirm_message\(frm, notes\) \{\n(.*?)\n\}", source, re.DOTALL
			)
			self.assertIsNotNone(undo_message, "undo_confirm_message missing")
			self.assertNotIn("File được ghi lại như cũ", source)
			self.assertIn("file mới thì bị xóa", undo_message.group(1))
			# New value (design 3.3): both wordings of the confirmation, block and single change, say it.
			self.assertEqual(undo_message.group(1).count("file mới thì bị xóa"), 2)

		with self.subTest(rule="no HTML built by concatenation"):
			self.assertNotIn("`", source)
			self.assertEqual(source.count('"<br>"'), source.count('.join("<br>")'))
			# The only markup literal is the "<br>" separator between escaped lines.
			self.assertNotRegex(source, r'"<(?!br>")')

		for forbidden in (
			"innerHTML",
			"eval(",
			"document.write",
			".html(",
			"outerHTML",
			"insertAdjacentHTML",
		):
			with self.subTest(forbidden=forbidden):
				self.assertNotIn(forbidden, source)

	def _undo_shown(self, **fields) -> bool:
		doc = {"change_kind": CHANGE_KIND_CODE, "apply_commit_sha": "", "undo_commit_sha": "", **fields}
		return _condition_holds(_function_return(self.source, "undo_allowed"), doc, {ROLE_INSTRUCTOR})

	def test_undo_button_shown_for_failed_with_commit(self):
		# Design 3.3 `undo`: Đã áp dụng, or Lỗi with an apply commit and no undo commit, for Thay đổi code.
		applied = _block_after(self.source, r"undo_allowed\(frm\)")
		self.assertRegex(
			applied,
			r'add_action_button\(\s*frm,\s*__\("Hoàn tác"\),\s*undo_confirm_message\(frm, notes\),\s*"'
			+ re.escape(UNDO_PATH)
			+ r'"\s*\)',
		)
		self.assertEqual(self.source.count("undo_allowed(frm)"), 2)
		sha = "a" * 40
		for name, fields, shown in (
			("applied", {"change_status": CHANGE_STATUS_APPLIED}, True),
			("applied with commit", {"change_status": CHANGE_STATUS_APPLIED, "apply_commit_sha": sha}, True),
			("failed with commit", {"change_status": CHANGE_STATUS_FAILED, "apply_commit_sha": sha}, True),
			("failed without commit", {"change_status": CHANGE_STATUS_FAILED}, False),
			("failed commit None", {"change_status": CHANGE_STATUS_FAILED, "apply_commit_sha": None}, False),
			(
				"failed already undone",
				{"change_status": CHANGE_STATUS_FAILED, "apply_commit_sha": sha, "undo_commit_sha": "b" * 40},
				False,
			),
			(
				"failed command kind",
				{
					"change_status": CHANGE_STATUS_FAILED,
					"apply_commit_sha": sha,
					"change_kind": CHANGE_KIND_COMMAND,
				},
				False,
			),
			(
				"applied command kind",
				{"change_status": CHANGE_STATUS_APPLIED, "change_kind": CHANGE_KIND_COMMAND},
				False,
			),
			("undone", {"change_status": CHANGE_STATUS_UNDONE, "apply_commit_sha": sha}, False),
			("undoing", {"change_status": CHANGE_STATUS_UNDOING, "apply_commit_sha": sha}, False),
			("pending", {"change_status": CHANGE_STATUS_PENDING}, False),
			("stale with commit", {"change_status": CHANGE_STATUS_STALE, "apply_commit_sha": sha}, False),
		):
			with self.subTest(case=name):
				self.assertIs(self._undo_shown(**fields), shown)

	def test_undo_confirmation_counts_items_and_names_commands(self):
		# AC-42: the block's item count, and the command line of the notes, are said before the click.
		body = re.search(r"function undo_confirm_message\(frm, notes\) \{\n(.*?)\n\}", self.source, re.DOTALL)
		self.assertIsNotNone(body, "undo_confirm_message missing")
		literal = re.search(r'const COMMAND_UNDO_NOTE_PREFIX = "([^"]+)";', self.source)
		self.assertIsNotNone(literal, "COMMAND_UNDO_NOTE_PREFIX")
		self.assertTrue(literal.group(1).startswith("Lệnh trong khối không hoàn tác được"))
		rows = [{"operation": CHANGE_OP_EDIT, "file_path": "myapp/myapp/a.py", "idx": 1}]
		for commands, has_note in (([["migrate"]], True), ([], False)):
			with self.subTest(commands=commands):
				notes = change_text.proposal_notes(
					{
						"change_kind": CHANGE_KIND_CODE,
						"operations": rows,
						"command_list": json.dumps(commands),
					}
				)
				self.assertIs(any(note.startswith(literal.group(1)) for note in notes), has_note)
				self.assertIs(COMMAND_UNDO_NOTE in notes, has_note)
		self.assertRegex(
			body.group(1),
			_statement(
				"const items = (frm.doc.operations || []).length; const lines = items ? [__("
				+ json.dumps(
					"Hoàn tác khối {0} mục? File trở lại như trước khi áp dụng (file mới thì bị xóa)"
					" và có một commit hoàn tác.",
					ensure_ascii=False,
				)
				+ ", [items])] : [__("
				+ json.dumps(
					"Hoàn tác thay đổi này? File trở lại như trước khi áp dụng (file mới thì bị xóa)"
					" và có một commit hoàn tác.",
					ensure_ascii=False,
				)
				+ ")];"
				" const command_note = notes.find((note) => note.startsWith(COMMAND_UNDO_NOTE_PREFIX));"
				" if (command_note) { lines.push(command_note); }"
				' return lines.map(frappe.utils.escape_html).join("<br>");'
			),
		)

	def _confirm_called(self, restart_status, roles) -> bool:
		doc = {"restart_status": restart_status, "change_status": CHANGE_STATUS_APPLIED}
		return _condition_holds(_function_return(self.source, "restart_check_due"), doc, roles)

	def test_calls_confirm_restart_only_when_sent(self):
		# Design 4.4 step 5 and arch-ruling-3 (ADR-040 C-4): once on open, only from Đã gửi; the answer's
		# `status` is compared with the field and the form reloads only when it changed.
		source = self.source
		self.assertEqual(source.count(f'"{CONFIRM_RESTART_PATH}"'), 1)
		onload = re.search(r"\n\tonload\(frm\) \{\n(.*?)\n\t\},", source, re.DOTALL)
		self.assertIsNotNone(onload, "onload handler missing")
		self.assertRegex(onload.group(1), _statement("confirm_restart_on_open(frm);"))
		self.assertEqual(source.count("confirm_restart_on_open(frm)"), 2)
		function = re.search(r"\nfunction confirm_restart_on_open\(frm\) \{\n(.*?)\n\}", source, re.DOTALL)
		self.assertIsNotNone(function, "confirm_restart_on_open missing")
		self.assertRegex(
			function.group(1),
			_statement(
				"if (!restart_check_due(frm)) { return; } frappe.call({ method: "
				+ json.dumps(CONFIRM_RESTART_PATH)
				+ ', args: { name: frm.doc.name }, type: "POST", callback: (r) => {'
				" if (r.message.status !== frm.doc.restart_status) { frm.reload_doc(); } }, });"
			),
		)
		self.assertEqual(source.count("restart_check_due(frm)"), 2)
		self.assertNotIn("message.restart_status", source)
		self.assertNotIn("frappe.realtime", source)
		self.assertNotIn("open_doc:", source)
		for status, called in (
			(RESTART_STATUS_SENT, True),
			(RESTART_STATUS_CONFIRMED, False),
			(RESTART_STATUS_UNCONFIRMED, False),
			(RESTART_STATUS_LAUNCH_FAILED, False),
			("", False),
			(None, False),
		):
			with self.subTest(restart_status=status):
				self.assertIs(self._confirm_called(status, {ROLE_INSTRUCTOR}), called)

	def test_confirm_restart_called_only_for_instructor(self):
		# Design addendum 1 A-2.1, D-17: a System Manager without the Instructor role gets no call, so no error box.
		for roles, called in (
			({ROLE_INSTRUCTOR}, True),
			({ROLE_INSTRUCTOR, "System Manager"}, True),
			({"System Manager"}, False),
			(set(), False),
		):
			with self.subTest(roles=sorted(roles)):
				self.assertIs(self._confirm_called(RESTART_STATUS_SENT, roles), called)

	def test_form_diff_covers_every_item(self):
		# AC-48 (form): the one `diff` field Desk receives holds the hunk of every item of the block.
		operations = [
			{"kind": CHANGE_OP_EDIT, "path": "myapp/myapp/a.py", "before": "x = 1\n", "after": "x = 2\n"},
			{"kind": CHANGE_OP_CREATE, "path": "myapp/myapp/new/b.py", "after": "y = 1\n"},
			{"kind": CHANGE_OP_DELETE, "path": "myapp/myapp/c.py", "before": "z = 1\n"},
			{
				"kind": CHANGE_OP_RENAME,
				"path": "myapp/myapp/d.py",
				"new_path": "myapp/myapp/e.py",
				"before": "w = 1\n",
				"after": "w = 1\n",
			},
		]
		proposal = make_block_proposal(operations, [["migrate"], ["restart"]])
		frappe.response.docs = []
		try:
			frappe.desk.form.load.getdoc(PROPOSAL_DOCTYPE, proposal.name)
			diff = frappe.response.docs[0].diff
		finally:
			frappe.response.docs = []
		for name, segment in (
			("edit", "--- a/myapp/myapp/a.py\n+++ b/myapp/myapp/a.py\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"),
			("create", "--- /dev/null\n+++ b/myapp/myapp/new/b.py\n@@ -0,0 +1 @@\n+y = 1\n"),
			("delete", "--- a/myapp/myapp/c.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-z = 1\n"),
			("rename", "rename from myapp/myapp/d.py\nrename to myapp/myapp/e.py\n"),
		):
			with self.subTest(item=name):
				self.assertIn(segment, diff)
		fields = _fields_by_name()
		self.assertEqual(fields["diff"]["fieldtype"], "Code")
		self.assertFalse(fields["diff"].get("hidden"))
		self.assertFalse(fields["diff"].get("depends_on"))
		self.assertLess(FIELD_ORDER.index("section_diff"), FIELD_ORDER.index("diff"))
		self.assertLess(FIELD_ORDER.index("diff"), FIELD_ORDER.index("section_content"))
		# The form script never hides or trims the field.
		self.assertNotIn('"diff"', self.source)
		self.assertNotIn(".diff", self.source)


PANEL_INSTRUCTOR = "change.panel.instructor@example.com"
PANEL_PLAIN = "change.panel.plain@example.com"


class TestPanelDecisionRefusal(FrappeTestCase):
	"""CHG-008 design 3.3 (AC-4, AC-6): the predicate behind the panel's Duyệt / Từ chối buttons."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		for email in (PANEL_INSTRUCTOR, PANEL_PLAIN):
			create_agent(email)
		if not frappe.db.exists("User", AGENT_USER):
			create_agent(AGENT_USER)
		frappe.get_doc("User", PANEL_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		frappe.get_doc("User", AGENT_USER).add_roles(ROLE_INSTRUCTOR)
		set_agent_settings(one_click_approval_enabled=1)

	def _refusal(self, user, status=CHANGE_STATUS_PENDING):
		frappe.set_user(user)
		try:
			return controller.panel_decision_refusal(status)
		finally:
			frappe.set_user("Administrator")

	def test_refusal_texts_are_the_three_panel_sentences(self):
		self.assertEqual(
			controller.PANEL_REFUSALS,
			{
				"role": "Chỉ người có vai trò ERP AI Instructor mới duyệt hoặc từ chối được.",
				"not_pending": "Đề xuất không còn chờ duyệt.",
				"switch_off": "Duyệt một lần bấm đang tắt; hãy duyệt ở form đề xuất.",
				# CHG-010: the fourth refusal, for a console proposal whose own switch is off
				"console_off": "Chạy bench console đang tắt.",
			},
		)

	def test_has_decider_role(self):
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles(AGENT_USER))
		cases = {
			PANEL_INSTRUCTOR: True,
			PANEL_PLAIN: False,
			AGENT_USER: False,
			"Administrator": False,
			"Guest": False,
		}
		for user, expected in cases.items():
			with self.subTest(user=user):
				self.assertIs(controller.has_decider_role(user), expected)

	def test_matrix_role_status_switch(self):
		for user, role in ((PANEL_INSTRUCTOR, True), (PANEL_PLAIN, False)):
			for status, pending in ((CHANGE_STATUS_PENDING, True), (CHANGE_STATUS_APPROVED, False)):
				for switch in (1, 0):
					with self.subTest(role=role, pending=pending, switch=switch):
						set_agent_settings(one_click_approval_enabled=switch)
						expected = None
						if not role:
							expected = "role"
						elif not pending:
							expected = "not_pending"
						elif not switch:
							expected = "switch_off"
						got = self._refusal(user, status)
						# design 3.3 contract: the predicate returns the key of PANEL_REFUSALS, not its sentence
						self.assertEqual(got, expected)

	def test_never_authority_is_role_refusal_even_with_role_and_pending_and_switch_on(self):
		for user in (AGENT_USER, "Administrator", "Guest"):
			with self.subTest(user=user):
				# design 3.3 contract: the predicate returns the key of PANEL_REFUSALS, not its sentence
				self.assertEqual(self._refusal(user), "role")

	def test_order_role_before_not_pending_before_switch_off(self):
		set_agent_settings(one_click_approval_enabled=0)
		# design 3.3 contract: the predicate returns the key of PANEL_REFUSALS, not its sentence
		self.assertEqual(self._refusal(PANEL_PLAIN, CHANGE_STATUS_APPROVED), "role")
		self.assertEqual(self._refusal(PANEL_INSTRUCTOR, CHANGE_STATUS_APPROVED), "not_pending")

	def test_switch_read_again_on_every_call(self):
		self.assertIsNone(self._refusal(PANEL_INSTRUCTOR))
		set_agent_settings(one_click_approval_enabled=0)
		# design 3.3 contract: the predicate returns the key of PANEL_REFUSALS, not its sentence
		self.assertEqual(self._refusal(PANEL_INSTRUCTOR), "switch_off")
		set_agent_settings(one_click_approval_enabled=1)
		self.assertIsNone(self._refusal(PANEL_INSTRUCTOR))

	def test_switch_not_read_when_role_or_status_already_refuse(self):
		for user, status in (
			(PANEL_PLAIN, CHANGE_STATUS_PENDING),
			(PANEL_INSTRUCTOR, CHANGE_STATUS_APPROVED),
		):
			with self.subTest(user=user, status=status):
				with patch("erp_ai.agent.policy.permission_switches") as switches:
					self._refusal(user, status)
				switches.assert_not_called()

	def test_proposal_head(self):
		proposal = make_change_proposal()
		head = controller.proposal_head(proposal.name)
		# CHG-010: the head also says whether the proposal is a console one
		self.assertEqual(
			head, frappe._dict(ticket=proposal.ticket, change_status=CHANGE_STATUS_PENDING, is_console=False)
		)
		self.assertEqual(set(head), {"ticket", "change_status", "is_console"})

	def test_proposal_head_unknown_names_do_not_exist(self):
		for name in (None, "", "   ", 5, ["x"], "ERP-AI-NO-SUCH-PROPOSAL"):
			with self.subTest(name=name):
				with self.assertRaises(frappe.DoesNotExistError):
					controller.proposal_head(name)

	def test_new_functions_are_not_whitelisted(self):
		# CHG-010: panel_approve is the panel's approval, reachable only through the panel gate
		for fn in (
			controller.has_decider_role,
			controller.panel_decision_refusal,
			controller.proposal_head,
			controller.panel_approve,
		):
			with self.subTest(fn=fn.__name__):
				self.assertNotIn(fn, frappe.whitelisted)

	def test_decider_uses_has_decider_role(self):
		proposal = make_change_proposal()
		frappe.set_user(PANEL_INSTRUCTOR)
		with patch.object(controller, "has_decider_role", return_value=False) as role:
			with self.assertRaises(frappe.PermissionError):
				controller._decider(proposal.name)
		role.assert_called_once_with(PANEL_INSTRUCTOR)


CONSOLE_PANEL_ONLY_TEXT = "Script console chỉ duyệt được bằng nút Duyệt trong khung Trao đổi với bot."
CONSOLE_OFF_TEXT = "Chạy bench console đang tắt."


def _console_proposal(**fields):
	return make_change_proposal(
		CHANGE_KIND_COMMAND,
		command_args=None,
		app=None,
		command_list=json.dumps([["--site", frappe.local.site, "console"]]),
		content_after="print(1)\n",
		**fields,
	)


class TestConsoleProposalDecision(FrappeTestCase):
	"""CHG-010: a console proposal is approved only from the chat panel; rejecting stays possible everywhere."""

	def setUp(self):
		self.addCleanup(frappe.clear_cache, user=PANEL_INSTRUCTOR)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		enqueue = patch("frappe.enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		create_agent(PANEL_INSTRUCTOR)
		if not frappe.db.exists("User", AGENT_USER):
			create_agent(AGENT_USER)
		frappe.get_doc("User", PANEL_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		frappe.get_doc("User", AGENT_USER).add_roles(ROLE_INSTRUCTOR)
		set_agent_settings(one_click_approval_enabled=1, console_enabled=1)

	def _jobs(self):
		return [call for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_CHANGE]

	def _as(self, user, method, name):
		frappe.set_user(user)
		try:
			return getattr(controller, method)(name)
		finally:
			frappe.set_user("Administrator")

	def _status(self, name):
		return frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["change_status", "decided_by"], as_dict=True)

	def test_form_approve_refused_for_a_console_proposal(self):
		name = _console_proposal().name
		with self.assertRaises(frappe.PermissionError) as caught:
			self._as(PANEL_INSTRUCTOR, "approve", name)
		self.assertEqual(str(caught.exception), controller.CONSOLE_PANEL_ONLY)
		self.assertEqual(controller.CONSOLE_PANEL_ONLY, CONSOLE_PANEL_ONLY_TEXT)
		self.assertEqual(self._status(name).change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(self._jobs(), [])

	def test_form_approve_other_kinds_unchanged(self):
		name = make_change_proposal(CHANGE_KIND_COMMAND).name
		self.assertEqual(self._as(PANEL_INSTRUCTOR, "approve", name)["status"], CHANGE_STATUS_APPROVED)
		self.assertEqual(len(self._jobs()), 1)

	def test_form_reject_still_works_for_a_console_proposal(self):
		name = _console_proposal().name
		self.assertEqual(self._as(PANEL_INSTRUCTOR, "reject", name)["status"], CHANGE_STATUS_REJECTED)
		self.assertEqual(self._jobs(), [])

	def test_role_is_checked_before_the_console_refusal(self):
		name = _console_proposal().name
		with self.assertRaises(frappe.PermissionError) as caught:
			self._as(AGENT_USER, "approve", name)
		self.assertNotEqual(str(caught.exception), controller.CONSOLE_PANEL_ONLY)

	def test_panel_approve_approves_and_queues_one_job(self):
		name = _console_proposal().name
		self.assertEqual(
			self._as(PANEL_INSTRUCTOR, "panel_approve", name),
			{"name": name, "status": CHANGE_STATUS_APPROVED},
		)
		stored = self._status(name)
		self.assertEqual(
			(stored.change_status, stored.decided_by), (CHANGE_STATUS_APPROVED, PANEL_INSTRUCTOR)
		)
		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual((jobs[0].kwargs["proposal_name"], jobs[0].kwargs["action"]), (name, "apply"))

	def test_panel_approve_refuses_the_agent_account(self):
		name = _console_proposal().name
		with self.assertRaises(frappe.PermissionError):
			self._as(AGENT_USER, "panel_approve", name)
		self.assertEqual(self._status(name).change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(self._jobs(), [])

	def test_panel_approve_is_not_whitelisted(self):
		self.assertNotIn(controller.panel_approve, frappe.whitelisted)

	def test_refusal_console_off_even_with_one_click_on(self):
		set_agent_settings(one_click_approval_enabled=1, console_enabled=0)
		frappe.set_user(PANEL_INSTRUCTOR)
		self.assertEqual(
			controller.panel_decision_refusal(CHANGE_STATUS_PENDING, console=True), "console_off"
		)
		self.assertIsNone(controller.panel_decision_refusal(CHANGE_STATUS_PENDING))

	def test_refusal_none_with_console_on_even_with_one_click_off(self):
		set_agent_settings(one_click_approval_enabled=0, console_enabled=1)
		frappe.set_user(PANEL_INSTRUCTOR)
		self.assertIsNone(controller.panel_decision_refusal(CHANGE_STATUS_PENDING, console=True))
		self.assertEqual(controller.panel_decision_refusal(CHANGE_STATUS_PENDING), "switch_off")

	def test_refusal_order_role_then_pending_then_switch_for_console(self):
		set_agent_settings(console_enabled=0)
		frappe.set_user(AGENT_USER)
		self.assertEqual(controller.panel_decision_refusal(CHANGE_STATUS_PENDING, console=True), "role")
		frappe.set_user(PANEL_INSTRUCTOR)
		self.assertEqual(
			controller.panel_decision_refusal(CHANGE_STATUS_APPROVED, console=True), "not_pending"
		)

	def test_proposal_head_flags_a_console_proposal(self):
		self.assertIs(controller.proposal_head(_console_proposal().name).is_console, True)
		self.assertIs(
			controller.proposal_head(make_change_proposal(CHANGE_KIND_COMMAND).name).is_console, False
		)
