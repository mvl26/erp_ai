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
	PROPOSAL_DOCTYPE,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
	RESTART_STATUS_SENT,
	RESTART_STATUS_UNCONFIRMED,
	RESTART_TIMEOUT_S,
	ROLE_INSTRUCTOR,
	TRIGGER_COMMENT_MENTION,
)
from erp_ai.test_utils import make_block_proposal, make_change_proposal, set_agent_settings

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


class TestLegacyResult(ResultCommentTestCase):
	"""CHG-002 addendum-3 RQ-3: a stored proposal of the old shape keeps the CHG-001 (`f5cfed2`) text."""

	def test_legacy_text_byte_identical_per_status(self):
		# Pinned from `result_lines` at f5cfed2, one row per final status and per shape it accepts.
		cases = {
			"applied code": (
				CHANGE_KIND_CODE,
				{"file_path": FILE_PATH},
				f"kết quả đề xuất {{name}} (sửa {FILE_PATH}): Đã áp dụng; commit 0123456789ab",
			),
			"applied command": (
				CHANGE_KIND_COMMAND,
				{"command_args": json.dumps(ARGS), "apply_commit_sha": "", "exit_code": 3},
				"kết quả đề xuất {name} (lệnh bench build --app custom_app): Đã áp dụng; mã thoát 3",
			),
			"failed command": (
				CHANGE_KIND_COMMAND,
				{
					"command_args": json.dumps(ARGS),
					"change_status": CHANGE_STATUS_FAILED,
					"failure_reason": "lệnh trả mã 2",
					"apply_commit_sha": "",
					"exit_code": 2,
				},
				"kết quả đề xuất {name} (lệnh bench build --app custom_app): Lỗi; lý do: lệnh trả mã 2, mã thoát 2",
			),
			"failed while undoing": (
				CHANGE_KIND_CODE,
				{
					"file_path": FILE_PATH,
					"is_new_file": 1,
					"change_status": CHANGE_STATUS_FAILED,
					"failure_reason": REASON,
					"undo_by": INSTRUCTOR,
				},
				f"kết quả đề xuất {{name}} (tạo {FILE_PATH}): Lỗi; khi hoàn tác, lý do: {REASON}",
			),
			"stale": (
				CHANGE_KIND_CODE,
				{
					"file_path": FILE_PATH,
					"change_status": CHANGE_STATUS_STALE,
					"failure_reason": REASON,
					"apply_commit_sha": "",
				},
				f"kết quả đề xuất {{name}} (sửa {FILE_PATH}): Hết hiệu lực; lý do: {REASON}",
			),
			"undone": (
				CHANGE_KIND_CODE,
				{
					"file_path": FILE_PATH,
					"change_status": CHANGE_STATUS_UNDONE,
					"undo_commit_sha": UNDO_SHA,
					"undo_by": INSTRUCTOR,
				},
				f"kết quả đề xuất {{name}} (sửa {FILE_PATH}): Đã hoàn tác; commit hoàn tác fedcba987654",
			),
		}
		for label, (kind, fields, pinned) in cases.items():
			with self.subTest(label):
				name = self.proposal(kind, **fields)
				self.assertFalse(frappe.get_doc(PROPOSAL_DOCTYPE, name).get("operations"))
				self.assertFalse(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "command_list"))
				content = frappe.db.get_value("Comment", result_comment.post_result(name), "content")
				self.assertEqual(content, frappe.utils.escape_html(pinned.format(name=name)))


JS_PATH = "custom_app/public/js/form.js"
JSON_PATH = "custom_app/fixtures/role.json"
OLD_PATH = "custom_app/pkg/old.py"
NEW_PATH = "custom_app/pkg/new.py"
RESTART = ["restart"]
CLEAR_CACHE = ["clear-cache"]
SENT_HINT = (
	f"nếu sau {RESTART_TIMEOUT_S // 60} phút form đề xuất chưa ghi "
	'"Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)'
)
BUILD_HINT = "chạy bench build --app custom_app"
TODO = "việc người còn phải làm: "


def _edit(path):
	return {"kind": CHANGE_OP_EDIT, "path": path, "before": "a\n", "after": "b\n"}


def _create(path):
	return {"kind": CHANGE_OP_CREATE, "path": path, "after": "b\n"}


def _delete(path):
	return {"kind": CHANGE_OP_DELETE, "path": path, "before": "a\n"}


def _rename(path, new_path):
	return {"kind": CHANGE_OP_RENAME, "path": path, "new_path": new_path, "before": "a\n", "after": "a\n"}


def _ran(args, exit_code=0, timed_out=False, output=""):
	return {"args": args, "exit_code": exit_code, "duration_ms": 5, "timed_out": timed_out, "output": output}


def _migrate_hint():
	# A7-5: the site the job runs in, read from the test's own context (not written as "miyano").
	return f"chạy bench --site {frappe.local.site} migrate"


APPLIED = {"change_status": CHANGE_STATUS_APPLIED, "apply_commit_sha": APPLY_SHA}
FAILED_BEFORE_COMMIT = {"change_status": CHANGE_STATUS_FAILED, "failure_reason": "kiểm lại: không còn quyền"}
FAILED_AFTER_COMMIT = {
	"change_status": CHANGE_STATUS_FAILED,
	"apply_commit_sha": APPLY_SHA,
	"failure_reason": "lệnh 1 (bench build --app custom_app): lệnh trả mã 1",
}
STALE = {"change_status": CHANGE_STATUS_STALE, "failure_reason": REASON}
UNDO_REFUSED = {
	"change_status": CHANGE_STATUS_FAILED,
	"apply_commit_sha": APPLY_SHA,
	"undo_by": INSTRUCTOR,
	"failure_reason": "kiểm lại: không còn quyền",
}
FAILED_AFTER_UNDO_COMMIT = {
	"change_status": CHANGE_STATUS_FAILED,
	"apply_commit_sha": APPLY_SHA,
	"undo_commit_sha": UNDO_SHA,
	"undo_by": INSTRUCTOR,
	"failure_reason": "lệnh 1 (bench build --app custom_app): lệnh trả mã 1",
}
UNDONE = {
	"change_status": CHANGE_STATUS_UNDONE,
	"apply_commit_sha": APPLY_SHA,
	"undo_commit_sha": UNDO_SHA,
	"undo_by": INSTRUCTOR,
}


class TestBlockResult(ResultCommentTestCase):
	"""The result comment of a block proposal (CHG-002 AC-45, AC-49, design 3.7, addendum-7 P7-1..P7-9)."""

	def block(self, operations, commands, results=None, **state):
		"""A block proposal on `self.ticket`, moved to `state` the way the job leaves it.

		`results` is stored as `command_results`: a list is written as JSON, a string as it is.
		"""
		doc = make_block_proposal(operations, commands, ticket=self.ticket)
		values = dict(state)
		if results is not None:
			values["command_results"] = results if isinstance(results, str) else json.dumps(results)
		if values:
			frappe.db.set_value(PROPOSAL_DOCTYPE, doc.name, values, update_modified=False)
		return doc.name

	def text(self, name):
		"""`result_lines` joined, read the way `post_result` reads (fields from the DB, the stored doc)."""
		return result_comment.LINE_SEPARATOR.join(self.lines(name))

	@staticmethod
	def lines(name):
		fields = frappe.db.get_value(PROPOSAL_DOCTYPE, name, list(result_comment.RESULT_FIELDS), as_dict=True)
		return result_comment.result_lines(fields, doc=frappe.get_doc(PROPOSAL_DOCTYPE, name))

	def posted(self, name):
		"""The content of the one new comment `post_result` writes."""
		before = {row.name for row in self.ticket_comments()}
		comment = result_comment.post_result(name)
		new = [row for row in self.ticket_comments() if row.name not in before]
		self.assertEqual([row.name for row in new], [comment])
		self.assertEqual(new[0].comment_type, "Info")
		return new[0].content

	def test_one_result_comment_per_outcome_with_items_commit_exit_codes_restart_todo(self):
		cases = {
			"applied, one item: the label is its path": (
				[_create(FILE_PATH)],
				[ARGS],
				[_ran(ARGS)],
				APPLIED,
				f"kết quả đề xuất {{name}} ({FILE_PATH}): Đã áp dụng; tạo {FILE_PATH}: đã áp dụng; "
				"commit 0123456789ab; bench build --app custom_app: mã thoát 0; restart: không cần; "
				f"{TODO}không",
			),
			"failed after commit, every command that ran": (
				[_edit(FILE_PATH), _edit(JS_PATH)],
				[CLEAR_CACHE, ARGS],
				[_ran(CLEAR_CACHE), _ran(ARGS, exit_code=2)],
				{
					"change_status": CHANGE_STATUS_FAILED,
					"apply_commit_sha": APPLY_SHA,
					"exit_code": 2,
					"failure_reason": "lệnh 2 (bench build --app custom_app): lệnh trả mã 2",
				},
				"kết quả đề xuất {name} (2 file): Lỗi; "
				"lý do: lệnh 2 (bench build --app custom_app): lệnh trả mã 2; "
				f"sửa {FILE_PATH}: đã áp dụng; sửa {JS_PATH}: đã áp dụng; commit 0123456789ab; "
				"bench clear-cache: mã thoát 0; bench build --app custom_app: mã thoát 2; restart: không cần; "
				f"{TODO}{BUILD_HINT}",
			),
			"stale: no commit group": (
				[_edit(FILE_PATH)],
				[],
				None,
				STALE,
				f"kết quả đề xuất {{name}} ({FILE_PATH}): Hết hiệu lực; lý do: {REASON}; "
				f"sửa {FILE_PATH}: chưa áp dụng; restart: không cần; {TODO}không",
			),
			"undone: both commits, apply first": (
				[_delete(OLD_PATH), _edit(FILE_PATH)],
				[],
				[],
				UNDONE,
				f"kết quả đề xuất {{name}} (2 file): Đã hoàn tác; xóa {OLD_PATH}: đã hoàn tác; "
				f"sửa {FILE_PATH}: đã hoàn tác; commit 0123456789ab; commit hoàn tác fedcba987654; "
				f"restart: không cần; {TODO}không",
			),
			"commands only: the label counts restart, never 0 file": (
				[],
				[ARGS, RESTART],
				[_ran(ARGS)],
				{"change_status": CHANGE_STATUS_APPLIED, "restart_status": RESTART_STATUS_SENT},
				"kết quả đề xuất {name} (2 lệnh bench): Đã áp dụng; bench build --app custom_app: mã thoát 0; "
				f"restart: đã gửi; {TODO}{SENT_HINT}",
			),
			"items and commands: the label is the items'": (
				[_edit(FILE_PATH)],
				[CLEAR_CACHE],
				[_ran(CLEAR_CACHE)],
				APPLIED,
				f"kết quả đề xuất {{name}} ({FILE_PATH}): Đã áp dụng; sửa {FILE_PATH}: đã áp dụng; "
				f"commit 0123456789ab; bench clear-cache: mã thoát 0; restart: không cần; {TODO}không",
			),
			"undo refused: the apply's commands are not shown": (
				[_edit(FILE_PATH)],
				[ARGS],
				[_ran(ARGS)],
				UNDO_REFUSED,
				f"kết quả đề xuất {{name}} ({FILE_PATH}): Lỗi; khi hoàn tác, lý do: kiểm lại: không còn quyền; "
				f"sửa {FILE_PATH}: đã áp dụng; commit 0123456789ab; restart: không cần; {TODO}không",
			),
			"undo failed after its commit: its commands are shown": (
				[_edit(FILE_PATH)],
				[ARGS],
				[_ran(ARGS, exit_code=1)],
				FAILED_AFTER_UNDO_COMMIT,
				f"kết quả đề xuất {{name}} ({FILE_PATH}): Lỗi; "
				"khi hoàn tác, lý do: lệnh 1 (bench build --app custom_app): lệnh trả mã 1; "
				f"sửa {FILE_PATH}: đã hoàn tác; commit 0123456789ab; commit hoàn tác fedcba987654; "
				f"bench build --app custom_app: mã thoát 1; restart: không cần; {TODO}không",
			),
		}
		for label, (operations, commands, results, state, expected) in cases.items():
			with self.subTest(label):
				name = self.block(operations, commands, results, **state)
				self.assertEqual(self.posted(name), frappe.utils.escape_html(expected.format(name=name)))

	def test_command_timeout_names_command_keeps_files_no_restart(self):
		name = self.block(
			[_edit(FILE_PATH), _edit(JS_PATH)],
			[ARGS, RESTART],
			[_ran(ARGS, exit_code=None, timed_out=True)],
			change_status=CHANGE_STATUS_FAILED,
			apply_commit_sha=APPLY_SHA,
			failure_reason="lệnh 1 (bench build --app custom_app): quá thời gian",
		)
		text = self.text(name)
		self.assertEqual(
			text,
			f"kết quả đề xuất {name} (2 file): Lỗi; lý do: lệnh 1 (bench build --app custom_app): quá thời gian; "
			f"sửa {FILE_PATH}: đã áp dụng; sửa {JS_PATH}: đã áp dụng; commit 0123456789ab; "
			"bench build --app custom_app: quá thời gian; restart: không chạy; "
			f"{TODO}restart bench, {BUILD_HINT}",
		)
		self.assertNotIn("mã thoát", text)

	def todo(self, operations, commands, results, state):
		text = self.text(self.block(operations, commands, results, **state))
		self.assertIn(TODO, text)
		return text.split(TODO, 1)[1]

	def test_build_and_migrate_todo_hints(self):
		migrate = ["--site", frappe.local.site, "migrate"]
		js = [_edit(JS_PATH)]
		json_items = [_create(JSON_PATH)]
		cases = {
			"js, no build": (js, [], [], APPLIED, BUILD_HINT),
			"js, build of the app done": (js, [ARGS], [_ran(ARGS)], APPLIED, "không"),
			"js, build of every app done": (js, [["build"]], [_ran(["build"])], APPLIED, "không"),
			"js, build of another app": (
				js,
				[["build", "--app", "hrms"]],
				[_ran(["build", "--app", "hrms"])],
				APPLIED,
				BUILD_HINT,
			),
			"js, --app without a name": (
				js,
				[["build", "--app"]],
				[_ran(["build", "--app"])],
				APPLIED,
				BUILD_HINT,
			),
			"js, build failed": (js, [ARGS], [_ran(ARGS, exit_code=1)], APPLIED, BUILD_HINT),
			"js, build timed out": (
				js,
				[ARGS],
				[_ran(ARGS, exit_code=None, timed_out=True)],
				APPLIED,
				BUILD_HINT,
			),
			"js, another command done": (js, [CLEAR_CACHE], [_ran(CLEAR_CACHE)], APPLIED, BUILD_HINT),
			"renamed to js": (
				[_rename(OLD_PATH, "custom_app/public/js/new.js")],
				[],
				[],
				APPLIED,
				BUILD_HINT,
			),
			"py only": ([_edit(FILE_PATH)], [], [], APPLIED, "không"),
			"json, no migrate": (json_items, [], [], APPLIED, _migrate_hint()),
			"json, migrate done": (json_items, [migrate], [_ran(migrate)], APPLIED, "không"),
			"json, migrate failed": (
				json_items,
				[migrate],
				[_ran(migrate, exit_code=1)],
				APPLIED,
				_migrate_hint(),
			),
			"json, migrate timed out": (
				json_items,
				[migrate],
				[_ran(migrate, exit_code=None, timed_out=True)],
				APPLIED,
				_migrate_hint(),
			),
			"json, build done is not a migrate": (json_items, [ARGS], [_ran(ARGS)], APPLIED, _migrate_hint()),
			"js and json, in order": (js + json_items, [], [], APPLIED, f"{BUILD_HINT}, {_migrate_hint()}"),
			"undone js and json": (js + json_items, [], [], UNDONE, f"{BUILD_HINT}, {_migrate_hint()}"),
			"the app is the proposal's": (
				js,
				[],
				[],
				{**APPLIED, "app": "hrms"},
				"chạy bench build --app hrms",
			),
			"stale: files not applied": (js + json_items, [], [], STALE, "không"),
			"failed before commit": (js + json_items, [], [], FAILED_BEFORE_COMMIT, "không"),
			"undo refused": (js + json_items, [], [], UNDO_REFUSED, "không"),
		}
		for suffix in (".ts", ".vue", ".css", ".scss", ".less", ".JS"):
			cases[f"suffix {suffix}"] = ([_edit(f"custom_app/public/x{suffix}")], [], [], APPLIED, BUILD_HINT)
		cases["suffix .JSON"] = ([_edit("custom_app/fixtures/x.JSON")], [], [], APPLIED, _migrate_hint())
		for label, (operations, commands, results, state, expected) in cases.items():
			with self.subTest(label):
				self.assertEqual(self.todo(operations, commands, results, state), expected)

	def test_seeded_token_zero(self):
		seed = "SEEDTOKEN-ghp_FAKE42"
		name = self.block(
			[{**_edit(FILE_PATH), "after": f"API_KEY = '{seed}'\n"}],
			[ARGS],
			[_ran(ARGS, exit_code=1, output=f"{seed} {TOKEN_URL} https://host.example/out")],
			change_status=CHANGE_STATUS_FAILED,
			apply_commit_sha=APPLY_SHA,
			failure_reason=f"lệnh 1 (bench build --app custom_app): push {TOKEN_URL} tới {EMAIL} lỗi",
			upstream_ref=f"https://{seed}@host.example/custom_app.git",
		)
		content = self.posted(name)
		for part in (seed, "x-token-FAKE", "host", "real.person", "example.com", "://", "@", "API_KEY"):
			self.assertNotIn(part, content)
		self.assertIn(f"lý do: lệnh 1 (bench build --app custom_app): push {MASK} tới {MASK} lỗi", content)
		self.assertIn("bench build --app custom_app: mã thoát 1", content)

	def test_block_only_lines_absent_when_not_block(self):
		legacy = {
			"applied": {},
			"failed": {
				"change_status": CHANGE_STATUS_FAILED,
				"failure_reason": REASON,
				"apply_commit_sha": "",
			},
			"stale": {"change_status": CHANGE_STATUS_STALE, "failure_reason": REASON, "apply_commit_sha": ""},
			"undone": {
				"change_status": CHANGE_STATUS_UNDONE,
				"undo_commit_sha": UNDO_SHA,
				"undo_by": INSTRUCTOR,
			},
		}
		for label, fields in legacy.items():
			with self.subTest(label):
				name = self.proposal(file_path=FILE_PATH, **fields)
				content = self.posted(name)
				for part in (
					"restart:",
					"việc người còn phải làm",
					"mã thoát",
					"đã áp dụng;",
					"chưa áp dụng",
				):
					self.assertNotIn(part, content)
				stored = frappe.db.get_value(
					PROPOSAL_DOCTYPE, name, list(result_comment.RESULT_FIELDS), as_dict=True
				)
				self.assertEqual(
					result_comment.result_lines(stored, doc=frappe.get_doc(PROPOSAL_DOCTYPE, name)),
					result_comment.result_lines(stored),
				)
		with self.subTest("command of the old shape"):
			content = self.posted(
				self.proposal(CHANGE_KIND_COMMAND, command_args=json.dumps(ARGS), apply_commit_sha="")
			)
			self.assertNotIn("restart:", content)
			self.assertNotIn("việc người còn phải làm", content)
		with self.subTest("no doc: the old shape even for block fields"):
			name = self.block(
				[_edit(FILE_PATH)], [RESTART], [], **APPLIED, restart_status=RESTART_STATUS_SENT
			)
			stored = frappe.db.get_value(
				PROPOSAL_DOCTYPE, name, list(result_comment.RESULT_FIELDS), as_dict=True
			)
			text = result_comment.LINE_SEPARATOR.join(result_comment.result_lines(stored))
			self.assertNotIn("restart:", text)
			self.assertNotIn("việc người còn phải làm", text)

	def test_sent_todo_says_permission_may_be_missing_unconfirmed_todo_restart(self):
		cases = {
			RESTART_STATUS_SENT: f"restart: đã gửi; {TODO}{SENT_HINT}",
			RESTART_STATUS_UNCONFIRMED: f"restart: chưa xác nhận; {TODO}restart bench",
			RESTART_STATUS_LAUNCH_FAILED: f"restart: lỗi khởi chạy; {TODO}restart bench",
			RESTART_STATUS_CONFIRMED: f"restart: đã xác nhận; {TODO}không",
		}
		self.assertIn("có thể chưa được cấp quyền restart", SENT_HINT)
		self.assertIn(f"sau {RESTART_TIMEOUT_S // 60} phút", SENT_HINT)
		for restart_status, tail in cases.items():
			with self.subTest(restart_status):
				name = self.block([_edit(FILE_PATH)], [RESTART], [], **APPLIED, restart_status=restart_status)
				self.assertEqual(
					self.text(name),
					f"kết quả đề xuất {name} ({FILE_PATH}): Đã áp dụng; sửa {FILE_PATH}: đã áp dụng; "
					f"commit 0123456789ab; {tail}",
				)

	def test_addendum7_samples_exact_text(self):
		samples = {
			"M1": (
				[_edit(JS_PATH), _create(JSON_PATH)],
				[ARGS],
				[_ran(ARGS)],
				APPLIED,
				"kết quả đề xuất {name} (2 file): Đã áp dụng; sửa custom_app/public/js/form.js: đã áp dụng; "
				"tạo custom_app/fixtures/role.json: đã áp dụng; commit 0123456789ab; "
				"bench build --app custom_app: mã thoát 0; restart: không cần; "
				"việc người còn phải làm: chạy bench --site {site} migrate",
			),
			"M2": (
				[],
				[ARGS],
				[_ran(ARGS)],
				{"change_status": CHANGE_STATUS_APPLIED},
				"kết quả đề xuất {name} (1 lệnh bench): Đã áp dụng; bench build --app custom_app: mã thoát 0; "
				"restart: không cần; việc người còn phải làm: không",
			),
			"M3": (
				[_edit(FILE_PATH), _edit(JS_PATH)],
				[ARGS, RESTART],
				[_ran(ARGS, exit_code=1)],
				FAILED_AFTER_COMMIT,
				"kết quả đề xuất {name} (2 file): Lỗi; lý do: lệnh 1 (bench build --app custom_app): lệnh trả mã 1; "
				"sửa custom_app/pkg/mod.py: đã áp dụng; sửa custom_app/public/js/form.js: đã áp dụng; "
				"commit 0123456789ab; bench build --app custom_app: mã thoát 1; restart: không chạy; "
				"việc người còn phải làm: restart bench, chạy bench build --app custom_app",
			),
			"M3, build timed out": (
				[_edit(FILE_PATH), _edit(JS_PATH)],
				[ARGS, RESTART],
				[_ran(ARGS, exit_code=None, timed_out=True)],
				{
					**FAILED_AFTER_COMMIT,
					"failure_reason": "lệnh 1 (bench build --app custom_app): quá thời gian",
				},
				"kết quả đề xuất {name} (2 file): Lỗi; lý do: lệnh 1 (bench build --app custom_app): quá thời gian; "
				"sửa custom_app/pkg/mod.py: đã áp dụng; sửa custom_app/public/js/form.js: đã áp dụng; "
				"commit 0123456789ab; bench build --app custom_app: quá thời gian; restart: không chạy; "
				"việc người còn phải làm: restart bench, chạy bench build --app custom_app",
			),
			"M4": (
				[_edit(FILE_PATH), _rename(OLD_PATH, NEW_PATH)],
				[RESTART],
				[],
				{**UNDONE, "restart_status": RESTART_STATUS_SENT},
				"kết quả đề xuất {name} (2 file): Đã hoàn tác; sửa custom_app/pkg/mod.py: đã hoàn tác; "
				"đổi tên custom_app/pkg/old.py → custom_app/pkg/new.py: đã hoàn tác; commit 0123456789ab; "
				"commit hoàn tác fedcba987654; restart: đã gửi; việc người còn phải làm: nếu sau 11 phút "
				'form đề xuất chưa ghi "Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)',
			),
			"M5": (
				[_edit(FILE_PATH)],
				[RESTART],
				[],
				{**APPLIED, "restart_status": RESTART_STATUS_SENT},
				"kết quả đề xuất {name} (custom_app/pkg/mod.py): Đã áp dụng; sửa custom_app/pkg/mod.py: đã áp dụng; "
				"commit 0123456789ab; restart: đã gửi; việc người còn phải làm: nếu sau 11 phút form đề xuất "
				'chưa ghi "Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)',
			),
			"M5, launch failed": (
				[_edit(FILE_PATH)],
				[RESTART],
				[],
				{**APPLIED, "restart_status": RESTART_STATUS_LAUNCH_FAILED},
				"kết quả đề xuất {name} (custom_app/pkg/mod.py): Đã áp dụng; sửa custom_app/pkg/mod.py: đã áp dụng; "
				"commit 0123456789ab; restart: lỗi khởi chạy; việc người còn phải làm: restart bench",
			),
			"M6": (
				[_edit(FILE_PATH), _delete(OLD_PATH)],
				[RESTART],
				None,
				{
					"change_status": CHANGE_STATUS_STALE,
					"failure_reason": "mục 2 (custom_app/pkg/old.py): file đích đã đổi kể từ lúc đề xuất",
				},
				"kết quả đề xuất {name} (2 file): Hết hiệu lực; sửa custom_app/pkg/mod.py: chưa áp dụng; "
				"xóa custom_app/pkg/old.py: chưa áp dụng, lý do: mục 2 (custom_app/pkg/old.py): file đích đã đổi "
				"kể từ lúc đề xuất; restart: không chạy; việc người còn phải làm: không",
			),
		}
		self.assertEqual(RESTART_TIMEOUT_S // 60, 11)
		for label, (operations, commands, results, state, sample) in samples.items():
			with self.subTest(label):
				name = self.block(operations, commands, results, **state)
				expected = sample.format(name=name, site=frappe.local.site)
				self.assertEqual(self.posted(name), frappe.utils.escape_html(expected))

	def test_item_state_follows_commits(self):
		item = f"sửa {FILE_PATH}: "
		cases = {
			"applied": (APPLIED, "đã áp dụng", ["commit 0123456789ab"]),
			"failed before commit": (FAILED_BEFORE_COMMIT, "chưa áp dụng", []),
			"failed after commit": (FAILED_AFTER_COMMIT, "đã áp dụng", ["commit 0123456789ab"]),
			"undo refused": (UNDO_REFUSED, "đã áp dụng", ["commit 0123456789ab"]),
			"failed after the undo commit": (
				FAILED_AFTER_UNDO_COMMIT,
				"đã hoàn tác",
				["commit 0123456789ab", "commit hoàn tác fedcba987654"],
			),
			"stale": (STALE, "chưa áp dụng", []),
			"undone": (UNDONE, "đã hoàn tác", ["commit 0123456789ab", "commit hoàn tác fedcba987654"]),
			# The undo sha alone decides, whatever the apply sha holds.
			"undo commit without apply commit": (
				{**UNDONE, "apply_commit_sha": ""},
				"đã hoàn tác",
				["commit hoàn tác fedcba987654"],
			),
		}
		for label, (state, expected, commits) in cases.items():
			with self.subTest(label):
				parts = self.lines(self.block([_edit(FILE_PATH)], [], [], **state))
				self.assertIn(f"{item}{expected}", [part.split(", lý do")[0] for part in parts])
				self.assertEqual([part for part in parts if part.startswith("commit")], commits)
		with self.subTest("verbs are the commit body's, lower case; rename shows both paths"):
			name = self.block(
				[_edit(FILE_PATH), _create(JS_PATH), _delete(OLD_PATH), _rename(OLD_PATH + "x", NEW_PATH)],
				[],
				[],
				**APPLIED,
			)
			self.assertEqual(
				self.lines(name)[1:5],
				[
					f"sửa {FILE_PATH}: đã áp dụng",
					f"tạo {JS_PATH}: đã áp dụng",
					f"xóa {OLD_PATH}: đã áp dụng",
					f"đổi tên {OLD_PATH}x → {NEW_PATH}: đã áp dụng",
				],
			)

	def test_item_reason_attached_once_other_reason_own_line(self):
		operations = [_edit(FILE_PATH), _delete(OLD_PATH)]
		first = f"sửa {FILE_PATH}: chưa áp dụng"
		second = f"xóa {OLD_PATH}: chưa áp dụng"

		def failed(reason, **state):
			values = {
				"change_status": CHANGE_STATUS_FAILED,
				"failure_reason": reason,
				"exit_code": 3,
				**state,
			}
			return self.lines(self.block(operations, [], [], **values))

		cases = {
			"mục n (path): attached to item n": (
				f"mục 2 ({OLD_PATH}): {REASON}",
				[first, f"{second}, lý do: mục 2 ({OLD_PATH}): {REASON}"],
			),
			"ghi mục k (path) lỗi: attached to item k": (
				f"ghi mục 1 ({FILE_PATH}) lỗi, đĩa đầy",
				[f"{first}, lý do: ghi mục 1 ({FILE_PATH}) lỗi, đĩa đầy", second],
			),
			"leading blanks are not a different reason": (
				f"  mục 1 ({FILE_PATH}): {REASON}",
				[f"{first}, lý do: mục 1 ({FILE_PATH}): {REASON}", second],
			),
			"item number past the block: own line": (
				f"mục 3 (x): {REASON}",
				[f"lý do: mục 3 (x): {REASON}", first, second],
			),
			"item number 0: own line": (
				f"mục 0 (x): {REASON}",
				[f"lý do: mục 0 (x): {REASON}", first, second],
			),
			"command reason: own line": (
				"lệnh 1: không cho phép",
				["lý do: lệnh 1: không cho phép", first, second],
			),
			"git reason: own line": ("GIT_COMMIT_FAILED", ["lý do: GIT_COMMIT_FAILED", first, second]),
			"mục without its bracket: own line": (
				f"mục 1 {REASON}",
				[f"lý do: mục 1 {REASON}", first, second],
			),
			"masked when attached": (
				f"mục 1 ({FILE_PATH}): push {TOKEN_URL} lỗi",
				[f"{first}, lý do: mục 1 ({FILE_PATH}): push {MASK} lỗi", second],
			),
			"blank reason: none": ("  \n ", [first, second]),
		}
		for label, (reason, expected) in cases.items():
			with self.subTest(label):
				lines = failed(reason)
				self.assertEqual(lines[1 : 1 + len(expected)], expected)
				self.assertLessEqual(" ".join(lines).count("lý do"), 1)
				self.assertNotIn("mã thoát 3", " ".join(lines))
		with self.subTest("undo: khi hoàn tác"):
			lines = failed(f"mục 2 ({OLD_PATH}): {REASON}", undo_by=INSTRUCTOR, apply_commit_sha=APPLY_SHA)
			self.assertEqual(
				lines[2], f"xóa {OLD_PATH}: đã áp dụng, khi hoàn tác, lý do: mục 2 ({OLD_PATH}): {REASON}"
			)
		with self.subTest("stale: attached too"):
			lines = self.lines(
				self.block(
					operations,
					[],
					[],
					change_status=CHANGE_STATUS_STALE,
					failure_reason=f"mục 1 ({FILE_PATH}): x",
				)
			)
			self.assertEqual(lines[1], f"{first}, lý do: mục 1 ({FILE_PATH}): x")
		with self.subTest("an old reason left on Đã hoàn tác is not shown"):
			lines = self.lines(
				self.block(operations, [], [], **UNDONE, failure_reason=f"mục 1 ({FILE_PATH}): x")
			)
			self.assertNotIn("lý do", " ".join(lines))

	def test_restart_line_per_status_and_not_run(self):
		def restart_part(commands, state):
			parts = self.lines(self.block([_edit(FILE_PATH)], commands, [], **state))
			return [part for part in parts if part.startswith("restart")]

		cases = {
			"applied, sent": (
				[RESTART],
				{**APPLIED, "restart_status": RESTART_STATUS_SENT},
				"restart: đã gửi",
			),
			"applied, launch failed": (
				[RESTART],
				{**APPLIED, "restart_status": RESTART_STATUS_LAUNCH_FAILED},
				"restart: lỗi khởi chạy",
			),
			"applied, confirmed": (
				[RESTART],
				{**APPLIED, "restart_status": RESTART_STATUS_CONFIRMED},
				"restart: đã xác nhận",
			),
			"applied, unconfirmed": (
				[RESTART],
				{**APPLIED, "restart_status": RESTART_STATUS_UNCONFIRMED},
				"restart: chưa xác nhận",
			),
			"undone, sent": ([RESTART], {**UNDONE, "restart_status": RESTART_STATUS_SENT}, "restart: đã gửi"),
			"applied, restart listed, no status": ([RESTART], APPLIED, "restart: không chạy"),
			"applied, no restart listed": ([], APPLIED, "restart: không cần"),
			# On Lỗi and Hết hiệu lực the stored status may be the apply's own: it is not read (A7-3).
			"failed, restart listed, old status left": (
				[RESTART],
				{**UNDO_REFUSED, "restart_status": RESTART_STATUS_SENT},
				"restart: không chạy",
			),
			"failed, no restart listed, old status left": (
				[],
				{**FAILED_AFTER_COMMIT, "restart_status": RESTART_STATUS_SENT},
				"restart: không cần",
			),
			"stale, unknown status not read": (
				[RESTART],
				{**STALE, "restart_status": "Lạ"},
				"restart: không chạy",
			),
		}
		for label, (commands, state, expected) in cases.items():
			with self.subTest(label):
				self.assertEqual(restart_part(commands, state), [expected])
		with self.subTest("not run and files changed: restart bench"):
			self.assertEqual(
				self.todo([_edit(FILE_PATH)], [RESTART], [], FAILED_AFTER_COMMIT), "restart bench"
			)
		with self.subTest("not run and no file changed: nothing to restart"):
			self.assertEqual(self.todo([_edit(FILE_PATH)], [RESTART], [], FAILED_BEFORE_COMMIT), "không")
		with self.subTest("not run, undo refused: this run changed no file"):
			self.assertEqual(self.todo([_edit(FILE_PATH)], [RESTART], [], UNDO_REFUSED), "không")

	def test_bad_command_results_or_restart_status_raises_value_error(self):
		bad_results = {
			"not JSON": "[{",
			"not a list": json.dumps({"args": ARGS, "exit_code": 0}),
			"an item that is not an object": json.dumps([ARGS]),
			"args not a list": json.dumps([{"args": "build", "exit_code": 0, "timed_out": False}]),
			"args holding a number": json.dumps([{"args": ["build", 1], "exit_code": 0, "timed_out": False}]),
			"no exit code, not timed out": json.dumps(
				[{"args": ARGS, "exit_code": None, "timed_out": False}]
			),
			"exit code as text": json.dumps([{"args": ARGS, "exit_code": "0", "timed_out": False}]),
			"exit code missing": json.dumps([{"args": ARGS, "timed_out": False}]),
			"exit code a boolean": json.dumps([{"args": ARGS, "exit_code": True, "timed_out": False}]),
		}
		for label, stored in bad_results.items():
			with self.subTest(label):
				name = self.block([_edit(FILE_PATH)], [ARGS], stored, **APPLIED)
				with self.assertRaisesRegex(ValueError, "^command_results không đọc được: "):
					self.lines(name)
		with self.subTest("a timed-out command needs no exit code"):
			name = self.block(
				[_edit(FILE_PATH)], [ARGS], json.dumps([{"args": ARGS, "timed_out": True}]), **APPLIED
			)
			self.assertIn("bench build --app custom_app: quá thời gian", self.lines(name))
		for state in (APPLIED, UNDONE):
			with self.subTest("unknown restart status", status=state["change_status"]):
				name = self.block([_edit(FILE_PATH)], [RESTART], [], **state, restart_status="Lạ")
				with self.assertRaisesRegex(ValueError, "^restart_status không hỗ trợ: 'Lạ'$"):
					self.lines(name)
		with self.subTest("a block in a status that is not final"):
			name = self.block([_edit(FILE_PATH)], [], [], change_status=CHANGE_STATUS_APPLYING)
			with self.assertRaises(ValueError):
				self.lines(name)


NOTICE_APP = "custom_app"
NOTICE_BRANCH = "develop"
NOTICE_REMOTE = "https://x-token-FAKE@host.example/custom_app.git"


class TestRestartNotice(ResultCommentTestCase):
	"""The comment written before a restart (CHG-002 AC-46 b, design 3.7, addendum-3 RQ-4)."""

	def notice_proposal(self, **fields):
		values = {
			"app": NOTICE_APP,
			"target_branch": NOTICE_BRANCH,
			"applied_branch": NOTICE_BRANCH,
			"upstream_ref": NOTICE_REMOTE,
			"undo_commit_sha": UNDO_SHA,
			**fields,
		}
		return self.proposal(**values)

	def new_comments(self, action, name):
		before = {row.name for row in self.ticket_comments()}
		comment = result_comment.post_restart_notice(name, action)
		new = [row for row in self.ticket_comments() if row.name not in before]
		self.assertEqual(len(new), 1)
		self.assertEqual(new[0].name, comment)
		return new[0]

	@staticmethod
	def expected(name, verb, sha):
		return frappe.utils.escape_html(
			f"Đề xuất {name} đã {verb}: commit {sha[:12]} trên nhánh {NOTICE_BRANCH} của app {NOTICE_APP}. "
			"Hệ thống sắp restart bench. Nếu site không lên sau vài phút: trên máy chủ chạy "
			f"`git -C apps/{NOTICE_APP} revert --no-edit {sha}` rồi `bench restart`."
		)

	def test_apply_notice_text_commit_branch_recovery(self):
		name = self.notice_proposal()
		row = self.new_comments("apply", name)
		self.assertEqual(row.content, self.expected(name, "áp dụng", APPLY_SHA))
		self.assertIn(f"commit {APPLY_SHA[:12]} trên nhánh", row.content)
		self.assertIn(f"revert --no-edit {APPLY_SHA}`", row.content)
		self.assertNotIn(UNDO_SHA, row.content)

	def test_undo_notice_uses_undo_commit(self):
		name = self.notice_proposal()
		row = self.new_comments("undo", name)
		self.assertEqual(row.content, self.expected(name, "hoàn tác", UNDO_SHA))
		self.assertIn("hoàn tác", row.content)
		self.assertNotIn(APPLY_SHA[:12], row.content)

	@staticmethod
	def expected_without_commit(name, verb):
		"""The no-commit template of addendum-5 P-2."""
		return (
			f"Đề xuất {name} đã {verb}. Hệ thống sắp restart bench. "
			"Nếu site không lên sau vài phút: trên máy chủ chạy `bench restart`."
		)

	def assert_names_no_commit(self, text):
		for part in ("None", "commit", "git -C", "apps/", "nhánh", NOTICE_APP, NOTICE_BRANCH):
			self.assertNotIn(part, text)

	def test_command_only_apply_notice_has_no_commit_branch_app(self):
		for sha in (None, ""):
			with self.subTest(sha=sha):
				fields = frappe._dict(
					name="P-9",
					ticket="T-1",
					app=None,
					target_branch=None,
					applied_branch=None,
					apply_commit_sha=sha,
					undo_commit_sha=None,
				)
				text = result_comment.restart_notice_text(fields, "apply")
				self.assertEqual(text, self.expected_without_commit("P-9", "áp dụng"))
				self.assert_names_no_commit(text)

	def test_undo_without_commit_notice_text(self):
		for sha in (None, ""):
			with self.subTest(sha=sha):
				fields = frappe._dict(
					name="P-9",
					ticket="T-1",
					app=None,
					target_branch=None,
					applied_branch=None,
					apply_commit_sha=APPLY_SHA,
					undo_commit_sha=sha,
				)
				text = result_comment.restart_notice_text(fields, "undo")
				self.assertEqual(text, self.expected_without_commit("P-9", "hoàn tác"))
				self.assert_names_no_commit(text)
		name = self.notice_proposal(undo_commit_sha="")
		row = self.new_comments("undo", name)
		self.assertEqual(
			row.content, frappe.utils.escape_html(self.expected_without_commit(name, "hoàn tác"))
		)
		self.assert_names_no_commit(row.content)

	def test_apply_without_commit_comment_on_ticket(self):
		name = self.notice_proposal(apply_commit_sha="")
		row = self.new_comments("apply", name)
		self.assertEqual(row.content, frappe.utils.escape_html(self.expected_without_commit(name, "áp dụng")))
		self.assert_names_no_commit(row.content)

	def test_no_remote_url_or_token(self):
		name = self.notice_proposal()
		for action in ("apply", "undo"):
			with self.subTest(action):
				content = self.new_comments(action, name).content
				for part in ("x-token-FAKE", "host.example", "://", "@", ".git"):
					self.assertNotIn(part, content)

	def test_info_comment_session_user_not_result_prefix(self):
		"""Addendum-5 P-2 (RQ-4): 0 calls of its own to `frappe.set_user`, `frappe.publish_realtime` and
		`new_comment`; the only realtime events are the `doc_update` and `list_update` Frappe sends when the
		new Comment is inserted (`Document.notify_update`), as for `post_result`."""
		name = self.notice_proposal()
		frappe.set_user(APPROVER)
		with (
			patch.object(frappe, "set_user") as set_user,
			patch.object(frappe, "publish_realtime") as publish,
			patch("frappe.realtime.publish_realtime", publish),
		):
			row = self.new_comments("apply", name)
			set_user.assert_not_called()
			# 0 calls of its own; the only events are `doc_update` and `list_update` that Frappe sends
			# on `insert` of the new Comment (`Document.notify_update`), the same as `post_result`.
			self.assertEqual(
				[
					(call.args[0], call.kwargs.get("doctype"), call.kwargs.get("docname"))
					for call in publish.call_args_list
				],
				[("doc_update", "Comment", row.name), ("list_update", None, None)],
			)
		self.assertEqual(row.comment_type, "Info")
		self.assertEqual(row.owner, frappe.session.user)
		self.assertEqual(row.owner, APPROVER)
		self.assertFalse(row.content.startswith(TRIGGER_KEYWORD))

	def test_write_failure_logged_not_raised(self):
		name = self.notice_proposal()
		with (
			patch.object(Document, "add_comment", side_effect=RuntimeError("boom")),
			patch.object(frappe, "log_error") as log_error,
		):
			self.assertIsNone(result_comment.post_restart_notice(name, "apply"))
		log_error.assert_called_once_with(
			result_comment.TITLE_RESULT_COMMENT_FAILED,
			f"proposal={name} action=apply error=RuntimeError",
		)

	def test_no_ticket_returns_none(self):
		name = self.notice_proposal()
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "ticket", "", update_modified=False)
		before = frappe.db.count("Comment")
		self.assertIsNone(result_comment.post_restart_notice(name, "apply"))
		self.assertEqual(frappe.db.count("Comment"), before)


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
