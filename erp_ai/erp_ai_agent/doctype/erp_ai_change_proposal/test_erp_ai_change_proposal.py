import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import frappe
import frappe.handler
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket, make_todo

from erp_ai.agent import authority
from erp_ai.agent.changes import transitions
from erp_ai.constants import (
	AGENT_USER,
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
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
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
