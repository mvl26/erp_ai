import json
from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket
from helpdesk.utils import is_agent

from erp_ai.agent import authority
from erp_ai.agent.changes import result_comment
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
	ROLE_INSTRUCTOR,
	TRIGGER_COMMENT_MENTION,
)
from erp_ai.test_utils import make_change_proposal, set_agent_settings

FILE_PATH = "custom_app/pkg/mod.py"
APPLY_SHA = "0123456789abcdef0123456789abcdef01234567"
UNDO_SHA = "fedcba9876543210fedcba9876543210fedcba98"
ARGS = ["build", "--app", "custom_app"]
REASON = "file đích đã đổi kể từ lúc đề xuất"
MASK = "[đã ẩn]"
# Design 3: the reason is cut to 300 characters.
REASON_MAX = 300
REASON_PREFIX = "lý do: "
TOKEN_URL = "https://x-token-FAKE@host/repo"
PLAIN_URL = "https://host.example/repo"
EMAIL = "real.person@example.com"
# A plain user (not a Helpdesk agent) who approved: the Info line needs no agent role (design Quyết định d).
APPROVER = "result.approver@example.com"
# A Helpdesk agent who also holds the instructor role, so a real Comment from them is an instruction.
INSTRUCTOR = "result.instructor@example.com"
RUN_FOR_TICKET_PATH = "erp_ai.agent.runner.run_for_ticket"
TRIGGER_KEYWORD = "kết quả đề xuất"


def _fields(**override):
	values = {
		"name": "P-1",
		"change_kind": CHANGE_KIND_CODE,
		"is_new_file": 0,
		"file_path": FILE_PATH,
		"command_args": "",
		"change_status": CHANGE_STATUS_APPLIED,
		"failure_reason": "",
		"apply_commit_sha": APPLY_SHA,
		"undo_commit_sha": "",
		"exit_code": 0,
		"undo_by": None,
	}
	values.update(override)
	return values


def _command(**override):
	return _fields(change_kind=CHANGE_KIND_COMMAND, file_path="", command_args=json.dumps(ARGS), **override)


def _reason_of(lines):
	"""The masked reason inside line 2 of a `Hết hiệu lực` result."""
	line = lines[1]
	if not line.startswith(REASON_PREFIX):
		raise AssertionError(f"line 2 does not start with {REASON_PREFIX!r}: {line!r}")
	return line[len(REASON_PREFIX) :]


class TestResultLines(FrappeTestCase):
	def test_lines_for_each_final_status(self):
		cases = {
			"applied code, edit": (
				_fields(),
				[f"kết quả đề xuất P-1 (sửa {FILE_PATH}): Đã áp dụng", "commit 0123456789ab"],
			),
			"applied code, new file": (
				_fields(is_new_file=1),
				[f"kết quả đề xuất P-1 (tạo {FILE_PATH}): Đã áp dụng", "commit 0123456789ab"],
			),
			"applied command": (
				_command(apply_commit_sha=""),
				["kết quả đề xuất P-1 (lệnh bench build --app custom_app): Đã áp dụng", "mã thoát 0"],
			),
			"failed code": (
				_fields(change_status=CHANGE_STATUS_FAILED, failure_reason=REASON, apply_commit_sha=""),
				[f"kết quả đề xuất P-1 (sửa {FILE_PATH}): Lỗi", f"lý do: {REASON}"],
			),
			"failed command with exit code": (
				_command(change_status=CHANGE_STATUS_FAILED, failure_reason="lệnh trả mã 2", exit_code=2),
				[
					"kết quả đề xuất P-1 (lệnh bench build --app custom_app): Lỗi",
					"lý do: lệnh trả mã 2, mã thoát 2",
				],
			),
			"failed while undoing": (
				_fields(change_status=CHANGE_STATUS_FAILED, failure_reason=REASON, undo_by=INSTRUCTOR),
				[f"kết quả đề xuất P-1 (sửa {FILE_PATH}): Lỗi", f"khi hoàn tác, lý do: {REASON}"],
			),
			"stale": (
				_fields(change_status=CHANGE_STATUS_STALE, failure_reason=REASON, apply_commit_sha=""),
				[f"kết quả đề xuất P-1 (sửa {FILE_PATH}): Hết hiệu lực", f"lý do: {REASON}"],
			),
			"undone": (
				_fields(change_status=CHANGE_STATUS_UNDONE, undo_commit_sha=UNDO_SHA, undo_by=INSTRUCTOR),
				[f"kết quả đề xuất P-1 (sửa {FILE_PATH}): Đã hoàn tác", "commit hoàn tác fedcba987654"],
			),
		}
		for label, (fields, expected) in cases.items():
			with self.subTest(label):
				self.assertEqual(result_comment.result_lines(fields), expected)

		for status in (
			CHANGE_STATUS_PENDING,
			CHANGE_STATUS_REJECTED,
			CHANGE_STATUS_APPROVED,
			CHANGE_STATUS_APPLYING,
			CHANGE_STATUS_UNDOING,
			"",
			None,
		):
			with self.subTest(status=status), self.assertRaises(ValueError):
				result_comment.result_lines(_fields(change_status=status))


class ResultCommentTestCase(FrappeTestCase):
	def setUp(self):
		# post_result never commits: the caller (the job) does.
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("post_result must not commit")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		if not frappe.db.exists("User", APPROVER):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": APPROVER,
					"first_name": "Result Approver",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		frappe.get_doc("User", APPROVER).add_roles(ROLE_INSTRUCTOR)
		create_agent(INSTRUCTOR)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		self.ticket = make_ticket(subject="erp_ai result comment").name

	def proposal(self, kind=CHANGE_KIND_CODE, **fields):
		"""A proposal on `self.ticket`, then moved to its final state the way the job leaves it."""
		name = make_change_proposal(kind, ticket=self.ticket).name
		values = {"change_status": CHANGE_STATUS_APPLIED, "apply_commit_sha": APPLY_SHA, **fields}
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, values, update_modified=False)
		return name

	def ticket_comments(self, ticket=None):
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "HD Ticket", "reference_name": ticket or self.ticket},
			fields=["name", "comment_type", "owner", "comment_email", "content"],
		)


class TestPostResult(ResultCommentTestCase):
	def test_post_result_writes_one_info_activity_as_session_user(self):
		path = "custom_app/pkg/<b>x</b>.py"
		name = self.proposal(file_path=path, diff=f"--- DIFF-MARKER {TOKEN_URL}")
		before = {row.name for row in self.ticket_comments()}
		frappe.set_user(APPROVER)
		self.assertFalse(is_agent(APPROVER))

		comment = result_comment.post_result(name)

		frappe.set_user("Administrator")
		new = [row for row in self.ticket_comments() if row.name not in before]
		self.assertEqual(len(new), 1)
		row = new[0]
		self.assertEqual(row.name, comment)
		self.assertEqual(row.comment_type, result_comment.COMMENT_TYPE_INFO)
		self.assertEqual(result_comment.COMMENT_TYPE_INFO, "Info")
		self.assertEqual(row.owner, APPROVER)
		self.assertEqual(row.comment_email, APPROVER)
		expected = frappe.utils.escape_html(
			f"kết quả đề xuất {name} (sửa {path}): Đã áp dụng; commit 0123456789ab"
		)
		self.assertEqual(row.content, expected)
		self.assertNotIn("<b>", row.content)
		self.assertIn("&lt;b&gt;", row.content)
		self.assertNotIn("DIFF-MARKER", row.content)

		# Errors reach the caller (the job logs them, design 4 step 3).
		with (
			patch.object(Document, "add_comment", side_effect=RuntimeError("boom")),
			self.assertRaises(RuntimeError),
		):
			result_comment.post_result(name)

	def test_reason_with_url_email_or_token_is_masked(self):
		def stale(reason):
			return result_comment.result_lines(
				_fields(change_status=CHANGE_STATUS_STALE, failure_reason=reason, apply_commit_sha="")
			)

		cases = {
			# Each form of the rule alone: a word with `://`, a word with `@`, and both.
			"url without @": (f"git lỗi {PLAIN_URL} xong", f"git lỗi {MASK} xong", ("host.example", "://")),
			"email": (f"gửi {EMAIL} lỗi", f"gửi {MASK} lỗi", ("real.person", "example.com", "@")),
			"remote url with token": (
				f"push {TOKEN_URL} bị từ chối",
				f"push {MASK} bị từ chối",
				("x-token-FAKE", "host/repo", "://", "@"),
			),
			# Whitespace folding: tabs and line breaks become one space.
			"whitespace folded": ("  a\n\tb   c \r\n", "a b c", ("\n", "\t", "  ")),
		}
		for label, (reason, expected, absent) in cases.items():
			with self.subTest(label):
				lines = stale(reason)
				self.assertEqual(_reason_of(lines), expected)
				for part in absent:
					self.assertNotIn(part, " ".join(lines))

		with self.subTest("1000 characters are cut to 300"):
			self.assertEqual(_reason_of(stale("x" * 1000)), "x" * REASON_MAX)
		with self.subTest("exactly 300 characters are kept"):
			self.assertEqual(_reason_of(stale("y" * REASON_MAX)), "y" * REASON_MAX)
		with self.subTest("folding happens before the cut"):
			# Unfolded, the 500 spaces would push "b" past the cut.
			self.assertEqual(_reason_of(stale("a" + " " * 500 + "b")), "a b")
		with self.subTest("a secret on the cut boundary is masked, not half kept"):
			reason = "z" * (REASON_MAX - 10) + " " + EMAIL
			text = _reason_of(stale(reason))
			self.assertLessEqual(len(text), REASON_MAX)
			self.assertNotIn("real.pe", text)
		with self.subTest("the failed line masks too"):
			lines = result_comment.result_lines(
				_command(change_status=CHANGE_STATUS_FAILED, failure_reason=f"lỗi {TOKEN_URL}", exit_code=1)
			)
			self.assertEqual(lines[1], f"lý do: lỗi {MASK}, mã thoát 1")
		with self.subTest("the stored text is masked"):
			name = self.proposal(
				change_status=CHANGE_STATUS_FAILED,
				apply_commit_sha="",
				failure_reason=f"push {TOKEN_URL} tới {EMAIL} lỗi " + "w" * 1000,
			)
			content = frappe.db.get_value("Comment", result_comment.post_result(name), "content")
			for part in ("x-token-FAKE", "host/repo", "real.person", "example.com", "://", "@"):
				self.assertNotIn(part, content)
			self.assertEqual(content.count(MASK), 2)
			self.assertNotIn("w" * (REASON_MAX + 1), content)

	def test_post_result_publishes_no_realtime(self):
		name = self.proposal()
		with (
			patch.object(frappe, "publish_realtime") as publish,
			patch("frappe.realtime.publish_realtime", publish),
		):
			comment = result_comment.post_result(name)
			# Nothing but Frappe's own after-commit refresh of the new Comment row (`Document.notify_update`,
			# sent for every inserted document): no timeline push, no agent status signal, nothing to the ticket.
			self.assertEqual(
				[
					(call.args[0], call.kwargs.get("doctype"), call.kwargs.get("docname"))
					for call in publish.call_args_list
				],
				[("doc_update", "Comment", comment), ("list_update", None, None)],
			)
			self.assertEqual(publish.call_args_list[1].args[1]["name"], comment)
			self.assertTrue(all(call.kwargs.get("after_commit") for call in publish.call_args_list))
			# The stub sees the timeline push of a comment type that sends it, so its absence above is real.
			publish.reset_mock()
			frappe.get_doc("HD Ticket", self.ticket).add_comment("Like", "x")
			self.assertIn("docinfo_update", [call.args[0] for call in publish.call_args_list])

	def test_post_result_without_ticket_or_deleted_ticket_returns_none(self):
		def count():
			return frappe.db.count("Comment")

		with self.subTest("no proposal"):
			before = count()
			self.assertIsNone(result_comment.post_result("ERP AI Change Proposal that does not exist"))
			self.assertEqual(count(), before)

		with self.subTest("proposal without ticket"):
			name = self.proposal()
			frappe.db.set_value(PROPOSAL_DOCTYPE, name, "ticket", "", update_modified=False)
			before = count()
			self.assertIsNone(result_comment.post_result(name))
			self.assertEqual(count(), before)

		with self.subTest("ticket deleted"):
			name = self.proposal()
			frappe.db.delete("HD Ticket", {"name": self.ticket})
			before = count()
			self.assertIsNone(result_comment.post_result(name))
			self.assertEqual(count(), before)


class TestResultIsNotAnInstruction(ResultCommentTestCase):
	def setUp(self):
		super().setUp()
		set_agent_settings(enabled=1, trigger_keyword=TRIGGER_KEYWORD, excluded_teams="")
		enqueue = patch.object(frappe, "enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)
		log_error = patch.object(frappe, "log_error")
		log_error.start()
		self.addCleanup(log_error.stop)

	def agent_runs(self):
		return [
			call for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_FOR_TICKET_PATH
		]

	def test_result_activity_enqueues_no_agent_run_and_is_not_an_instruction(self):
		name = self.proposal()
		self.enqueue.reset_mock()
		frappe.set_user(INSTRUCTOR)

		comment = result_comment.post_result(name)

		content = frappe.db.get_value("Comment", comment, "content")
		self.assertIn(TRIGGER_KEYWORD, content)
		self.assertEqual(self.agent_runs(), [])
		frappe.set_user("Administrator")
		fetched = {row["name"] for row in authority.fetch_ticket_comments(self.ticket)}
		self.assertNotIn(comment, fetched)
		self.assertIsNone(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, comment))

		# The same text as a human Comment from the same person does start a run and is an instruction,
		# so the zeros above come from the Info type, not from the setup.
		frappe.set_user(INSTRUCTOR)
		human = frappe.get_doc("HD Ticket", self.ticket).add_comment("Comment", content).name
		self.assertEqual(len(self.agent_runs()), 1)
		frappe.set_user("Administrator")
		self.assertIn(human, {row["name"] for row in authority.fetch_ticket_comments(self.ticket)})
		self.assertEqual(authority.run_instructor(self.ticket, TRIGGER_COMMENT_MENTION, human), INSTRUCTOR)
