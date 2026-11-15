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
from erp_ai.agent.changes import transitions
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
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
from erp_ai.test_utils import PREFIX, make_block_proposal, make_change_proposal

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
		self.assertEqual(own, set(METHOD_NAMES))
		for method in METHOD_NAMES:
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


FORM_SCRIPT_PATH = Path(__file__).resolve().parent / "erp_ai_change_proposal.js"
# The three whitelisted methods (design 3.3), written out by hand.
APPROVE_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.approve"
REJECT_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.reject"
UNDO_PATH = "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.undo"
ROLE_CHECK = 'frappe.user.has_role("ERP AI Instructor")'


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

		with self.subTest(rule="Hoàn tác only when Đã áp dụng and Thay đổi code"):
			applied = _block_after(
				source,
				r'frm\.doc\.change_status === "Đã áp dụng" &&\s*frm\.doc\.change_kind === "Thay đổi code"',
			)
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
			self.assertEqual(outside.count("frappe.call("), 1)
			call_at = outside.index("frappe.call(")
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
			applied = _block_after(
				source,
				r'frm\.doc\.change_status === "Đã áp dụng" &&\s*frm\.doc\.change_kind === "Thay đổi code"',
			)
			self.assertNotIn("File được ghi lại như cũ", source)
			self.assertIn("file mới thì bị xóa", applied)

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
