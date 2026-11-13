import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	PROPOSAL_DOCTYPE,
)
from erp_ai.test_utils import PREFIX, make_change_proposal

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
	"section_content",
	"content_before",
	"content_after",
	"base_hash",
	"after_hash",
	"section_command",
	"command_args",
	"exit_code",
	"duration_ms",
	"command_output",
	"section_decision",
	"decided_by",
	"decided_at",
	"undo_by",
	"undo_at",
	"finished_at",
	"failure_reason",
	"approved_digest",
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
		self.assertEqual(select_fields, {"change_status", "change_kind"})

	def test_content_fields_are_code_and_read_only(self):
		fields = _fields_by_name()
		code_fields = {name for name, field in fields.items() if field["fieldtype"] == "Code"}
		self.assertEqual(code_fields, CODE_FIELDS)
		data_fields = [
			name
			for name, field in fields.items()
			if field["fieldtype"] not in ("Section Break", "Column Break", "Tab Break")
		]
		self.assertEqual(len(data_fields), 35)
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
		self.assertTrue(stored.commit_message.startswith("erp_ai: áp dụng đề xuất mẫu"))
		self.assertEqual(stored.reason, "Đề xuất mẫu cho test")

	def test_unchanged_content_resave_is_allowed(self):
		for kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
			with self.subTest(kind=kind):
				proposal = make_change_proposal(kind=kind)
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				doc.save(ignore_permissions=True)
				self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, proposal.name, "change_kind"), kind)

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
