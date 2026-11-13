import dataclasses
import hashlib
import json
import os
import shutil
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.synchronization import filelock
from helpdesk.test_utils import create_agent

from erp_ai.agent import change_text, policy
from erp_ai.agent.changes import apply_job, file_writer, process_runner, transitions
from erp_ai.agent.changes.process_runner import CommandResult
from erp_ai.agent.tools import change_guard, source
from erp_ai.constants import (
	BOT_GIT_EMAIL,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDONE,
	COMMAND_TIMEOUT_S,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.test_utils import GIT_SANDBOX_EMAIL, GitSandbox, make_change_proposal, set_agent_settings

APP = "custom_app"
REL = "pkg/mod.py"
FILE_PATH = f"{APP}/{REL}"
NEW_REL = "pkg/new_mod.py"
BEFORE = "x = 1\n# Tiếng Việt\n"
AFTER = "x = 2\n# Tiếng Việt\n"
ACTOR = "apply.instructor@example.com"
UNDOER = "undo.instructor@example.com"
# Design table 3.2, written out by hand so a changed constant cannot hide a changed text.
GIT_LOCKED_TEXT = "kho git đang bị khóa (index.lock): có thao tác git khác đang chạy hoặc bị dừng giữa chừng"
GIT_DETACHED_TEXT = "HEAD của kho git không nằm trên nhánh nào (detached)"
GIT_IN_PROGRESS_TEXT = "kho git đang dở merge, rebase, cherry-pick hoặc revert"
GIT_IGNORED_TEXT = "file đích bị git bỏ qua (.gitignore)"
GIT_NOT_REPO_TEXT = "thư mục app không phải gốc một kho git"
GIT_ERROR_TEXT = "không đọc được trạng thái git"
GIT_COMMIT_FAILED_TEXT = "commit git lỗi, đã trả file về như trước"
GIT_RESTORE_FAILED_TEXT = "commit git lỗi và không trả lại được trạng thái kho, cần người kiểm"
GIT_COMMIT_MISMATCH_TEXT = "commit không đúng nội dung đã duyệt, cần người kiểm"


def _sha(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ApplyJobTestCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		# The job commits its state; inside a test nothing may reach the real database for good.
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		# The job runs as the approver, who must still hold the instructor role (design 4.3 step 4.2).
		self.addCleanup(frappe.set_user, "Administrator")
		create_agent(ACTOR)
		frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)
		frappe.set_user(ACTOR)
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		set_agent_settings(code_change_enabled=1, code_change_apps=APP)

	def path(self, rel=REL):
		return os.path.join(self.sandbox.repo(APP), rel)

	def read(self, rel=REL):
		with open(self.path(rel), encoding="utf-8", newline="") as handle:
			return handle.read()

	def head(self):
		return self.sandbox.git(APP, "rev-parse", "HEAD").strip()

	def commit_count(self):
		return int(self.sandbox.git(APP, "rev-list", "--count", "HEAD").strip())

	def worktree_changes(self):
		return self.sandbox.git(APP, "status", "--porcelain").strip()

	def code_proposal(self, **fields):
		values = {
			"app": APP,
			"file_path": FILE_PATH,
			"content_before": BEFORE,
			"content_after": AFTER,
			"base_hash": _sha(BEFORE),
			"after_hash": _sha(AFTER),
			"target_branch": "main",
			"upstream_ref": "",
			**fields,
		}
		return make_change_proposal(CHANGE_KIND_CODE, **values).name

	def new_file_proposal(self):
		return self.code_proposal(
			file_path=f"{APP}/{NEW_REL}",
			is_new_file=1,
			content_before="",
			base_hash="",
			after_hash=_sha(AFTER),
		)

	def approved(self, name):
		transitions.approve(name, ACTOR)
		return name

	def state(self, name):
		return frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			[
				"change_status",
				"failure_reason",
				"apply_commit_sha",
				"undo_commit_sha",
				"applied_branch",
				"exit_code",
			],
			as_dict=True,
		)

	def steps(self, name):
		rows = frappe.get_all(
			LOG_DOCTYPE, filters={"change_proposal": name}, fields=["change_step"], order_by="creation asc"
		)
		return [row.change_step for row in rows]

	def log_row(self, name, step):
		row = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name, "change_step": step},
			fields=["value_before", "value_after"],
		)[0]
		return json.loads(row.value_before or "null"), json.loads(row.value_after or "null")

	def author_email(self):
		return self.sandbox.git(APP, "log", "-1", "--format=%ae").strip()


class TestApplyCode(ApplyJobTestCase):
	def test_apply_writes_the_file_and_makes_one_bot_commit(self):
		name = self.approved(self.code_proposal())
		before_head, before_count = self.head(), self.commit_count()

		apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
		self.assertEqual(self.read(), AFTER)
		self.assertEqual(self.commit_count(), before_count + 1)
		self.assertEqual(state.apply_commit_sha, self.head())
		self.assertEqual(state.applied_branch, "main")
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), before_head)
		self.assertEqual(self.sandbox.git(APP, "log", "-1", "--format=%ae").strip(), BOT_GIT_EMAIL)
		self.assertIn(name, self.sandbox.git(APP, "log", "-1", "--format=%s"))
		self.assertEqual(self.sandbox.git(APP, "show", "--name-only", "--format=", "HEAD").split(), [REL])
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "apply"])

	def test_other_dirty_files_do_not_block_apply(self):
		self.sandbox.commit_file(APP, "pkg/other.py", "a = 1\n")
		with open(self.path("pkg/other.py"), "w", encoding="utf-8") as handle:
			handle.write("a = 2\n")
		name = self.approved(self.code_proposal())

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(self.sandbox.git(APP, "show", "--name-only", "--format=", "HEAD").split(), [REL])
		self.assertEqual(self.worktree_changes(), "M pkg/other.py")

	def test_repeated_job_does_nothing(self):
		name = self.approved(self.code_proposal())
		apply_job.run_change(name, "apply")
		count = self.commit_count()

		apply_job.run_change(name, "apply")

		self.assertEqual(self.commit_count(), count)
		self.assertEqual(self.steps(name), ["approve", "apply"])

	def test_unapproved_proposal_is_not_applied(self):
		name = self.code_proposal()
		apply_job.run_change(name, "apply")
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.steps(name), [])

	def test_file_changed_since_proposal_is_stale(self):
		name = self.approved(self.code_proposal())
		self.sandbox.commit_file(APP, REL, "x = 99\n")
		count = self.commit_count()

		apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_STALE)
		# Design 4.3 step 3.1 gives the reason word for word.
		self.assertEqual(state.failure_reason, "file đích đã đổi kể từ lúc đề xuất")
		self.assertEqual(self.read(), "x = 99\n")
		self.assertEqual(self.commit_count(), count)
		self.assertEqual(self.steps(name), ["approve", "stale"])

	def test_uncommitted_edit_of_the_target_is_stale(self):
		name = self.approved(self.code_proposal())
		with open(self.path(), "w", encoding="utf-8") as handle:
			handle.write("x = 5\n")

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_STALE)
		self.assertEqual(self.read(), "x = 5\n")

	def test_branch_changed_after_approval_becomes_stale(self):
		name = self.approved(self.code_proposal())
		main_head = self.head()
		self.sandbox.switch_branch(APP, "other")

		apply_job.run_change(name, "apply")

		state = self.state(name)
		# Design table 3.2 `GIT_BRANCH_CHANGED`, word for word (spec D-1, ADR-022 decision 6).
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_STALE, "nhánh đang checkout đã đổi kể từ lúc đề xuất"),
		)
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "main").strip(), main_head)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "other").strip(), main_head)
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "stale"])

	def test_switch_off_or_app_removed_fails_without_writing(self):
		for settings, reason in (
			({"code_change_enabled": 0}, "công tắc đang tắt"),
			({"code_change_apps": "helpdesk"}, "app không có trong danh sách được sửa"),
		):
			set_agent_settings(code_change_enabled=1, code_change_apps=APP)
			name = self.approved(self.code_proposal())
			set_agent_settings(**settings)

			apply_job.run_change(name, "apply")

			state = self.state(name)
			self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
			self.assertEqual(self.read(), BEFORE)

	def test_content_edited_after_approval_fails(self):
		name = self.approved(self.code_proposal())
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "content_after", "import os\n", update_modified=False)

		apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, "nội dung đề xuất đã bị sửa sau khi duyệt"),
		)
		self.assertEqual(self.read(), BEFORE)

	def test_failed_commit_gives_the_file_back(self):
		name = self.approved(self.code_proposal())
		failed = CommandResult(exit_code=1, output="fatal", duration_ms=3, timed_out=False, not_found=False)
		with patch.object(process_runner, "git_commit_only", return_value=failed):
			apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_FAILED)
		# Design table 3.2 `GIT_COMMIT_FAILED` (design.md:366) plus the short reason from the git output.
		self.assertEqual(state.failure_reason, f"{GIT_COMMIT_FAILED_TEXT}: fatal")
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_read_back_hash_mismatch_fails_without_a_commit(self):
		name = self.approved(self.code_proposal())
		count = self.commit_count()
		real_write = file_writer.write_atomic

		def write_reads_back_other_bytes(path, content, new_file):
			written = real_write(path, content, new_file=new_file)
			return _sha("khác\n") if content == AFTER else written

		with patch.object(file_writer, "write_atomic", side_effect=write_reads_back_other_bytes):
			apply_job.run_change(name, "apply")

		state = self.state(name)
		# Design 4.3 step 4.3 gives the reason word for word.
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, "đọc lại sau khi ghi không khớp"),
		)
		self.assertEqual(self.commit_count(), count)
		self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_crash_ends_as_failed_with_the_exception_class_only(self):
		name = self.approved(self.code_proposal())
		# The job rolls back before it records the failure; here its own commits are mocked, so a real
		# rollback would also drop the proposal the test made.
		with (
			patch.object(file_writer, "write_atomic", side_effect=RuntimeError("bí mật /srv/x")),
			patch.object(frappe.db, "rollback") as rollback,
		):
			apply_job.run_change(name, "apply")

		rollback.assert_called_once_with()

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "RuntimeError"))
		self.log_error.assert_called_once()
		self.assertNotIn("bí mật", str(self.log_error.call_args))

	def test_unknown_action_is_refused(self):
		with self.assertRaises(ValueError):
			apply_job.run_change("x", "delete")


class TestGitPrecheck(ApplyJobTestCase):
	"""Design 4.3 step 4.3 item 2 (AC-18 at apply time, NFR-3, ADR-022 decisions 3, 6 and 7)."""

	def remove_git_dir(self):
		shutil.rmtree(os.path.join(self.sandbox.repo(APP), ".git"))

	def ignore_new_target(self):
		self.sandbox.commit_file(APP, ".gitignore", f"{NEW_REL}\n")

	def test_git_precheck_fails_at_apply_without_write_or_commit(self):
		# Each git refusal of design table 3.2 ends the job as `Lỗi` with its text, word for word.
		cases = (
			("index.lock", lambda: self.sandbox.hold_index_lock(APP), False, GIT_LOCKED_TEXT),
			("detached", lambda: self.sandbox.detach(APP), False, GIT_DETACHED_TEXT),
			(
				"MERGE_HEAD",
				lambda: self.sandbox.mark_in_progress(APP, "MERGE_HEAD"),
				False,
				GIT_IN_PROGRESS_TEXT,
			),
			("ignored after", self.ignore_new_target, True, GIT_IGNORED_TEXT),
			(".git removed", self.remove_git_dir, False, GIT_NOT_REPO_TEXT),
		)
		for label, break_git, new_file, reason in cases:
			with self.subTest(label):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				name = self.approved(self.new_file_proposal() if new_file else self.code_proposal())
				break_git()
				count = None if label == ".git removed" else self.commit_count()

				with (
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as write,
					patch.object(process_runner, "git_add_new", wraps=process_runner.git_add_new) as add,
					patch.object(
						process_runner, "git_commit_only", wraps=process_runner.git_commit_only
					) as commit,
				):
					apply_job.run_change(name, "apply")

				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
				write.assert_not_called()
				add.assert_not_called()
				commit.assert_not_called()
				if new_file:
					self.assertFalse(os.path.lexists(self.path(NEW_REL)))
				else:
					self.assertEqual(self.read(), BEFORE)
				if count is not None:
					self.assertEqual(self.commit_count(), count)
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_index_lock_fails_fast(self):
		name = self.approved(self.code_proposal())
		self.sandbox.hold_index_lock(APP)
		lock = os.path.join(self.sandbox.repo(APP), ".git", "index.lock")
		count = self.commit_count()

		started = time.monotonic()
		apply_job.run_change(name, "apply")
		elapsed = time.monotonic() - started

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_LOCKED_TEXT))
		self.assertLess(elapsed, source.GIT_TIMEOUT_S)
		# The job never removes a lock it did not take (design 4.3 error table).
		self.assertTrue(os.path.exists(lock))
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.commit_count(), count)
		self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_git_precheck_limit_comes_from_the_job_deadline(self):
		start = self.head()
		# Seconds gone from the job budget when git is read → the `limit_s` of `read_git_state` (NFR-3).
		for spent, limit in (
			(100, source.GIT_TIMEOUT_S),
			(COMMAND_TIMEOUT_S - 5, 5),
			(COMMAND_TIMEOUT_S + 50, 1),
		):
			with self.subTest(spent=spent):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				name = self.approved(self.code_proposal())
				clock = iter([1000.0])
				with (
					patch("time.monotonic", side_effect=lambda spent=spent: next(clock, 1000.0 + spent)),
					patch.object(source, "read_git_state", wraps=source.read_git_state) as read_git,
				):
					apply_job.run_change(name, "apply")

				self.assertEqual(read_git.call_args.kwargs.get("limit_s"), limit)
				self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)


class TestApplyCodeSteps(ApplyJobTestCase):
	"""Design 4.3 step 4.3 items 1 to 5 and 7 (ADR-022 decision 1, D-19, design-addendum-3 QĐ-B2 and QĐ-B5)."""

	def test_apply_writes_exact_approved_bytes(self):
		content = "a = '<script>alert(1)</script>'\r\n# Tiếng Việt có dấu\r\nb = 2"
		name = self.approved(self.code_proposal(content_after=content, after_hash=_sha(content)))

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		with open(self.path(), "rb") as handle:
			self.assertEqual(handle.read(), content.encode("utf-8"))

	def test_apply_creates_one_commit_with_only_target_path(self):
		self.sandbox.commit_file(APP, "pkg/staged.py", "s = 1\n")
		self.sandbox.commit_file(APP, "pkg/unstaged.py", "u = 1\n")
		self.sandbox.stage(APP, "pkg/staged.py", "s = 2\n")
		self.sandbox.write_unstaged(APP, "pkg/unstaged.py", "u = 2\n")
		name = self.approved(self.code_proposal())
		count = self.commit_count()

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(self.commit_count(), count + 1)
		changed = self.sandbox.git(APP, "diff-tree", "-r", "--no-commit-id", "--name-only", "HEAD").split()
		self.assertEqual(changed, [REL])
		self.assertRegex(name, r"^AICHG-\d{5}$")
		self.assertIn(name, self.sandbox.git(APP, "log", "-1", "--format=%B"))
		self.assertEqual(self.sandbox.git(APP, "diff", "--cached", "--name-only").split(), ["pkg/staged.py"])
		self.assertEqual(self.sandbox.git(APP, "diff", "--name-only").split(), ["pkg/unstaged.py"])
		self.assertEqual(self.read("pkg/staged.py"), "s = 2\n")
		self.assertEqual(self.read("pkg/unstaged.py"), "u = 2\n")

	def test_target_changed_after_proposal_becomes_stale(self):
		def committed_by_a_person():
			self.sandbox.commit_file(APP, REL, "x = 99\n")

		def left_uncommitted():
			self.sandbox.write_unstaged(APP, REL, "x = 99\n")

		start = self.head()
		for label, change in (("committed", committed_by_a_person), ("uncommitted", left_uncommitted)):
			with self.subTest(label):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				name = self.approved(self.code_proposal())
				change()
				count = self.commit_count()

				# D-19: the file hash is checked first, so git is not even read for a stale target.
				with patch.object(source, "read_git_state", wraps=source.read_git_state) as read_git:
					apply_job.run_change(name, "apply")

				read_git.assert_not_called()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_STALE, "file đích đã đổi kể từ lúc đề xuất"),
				)
				self.assertEqual(self.read(), "x = 99\n")
				self.assertEqual(self.commit_count(), count)
				self.assertEqual(self.steps(name), ["approve", "stale"])

	def test_new_file_appeared_meanwhile_becomes_stale(self):
		def committed_by_a_person():
			self.sandbox.commit_file(APP, NEW_REL, "taken = 1\n")

		def left_untracked():
			self.sandbox.write_unstaged(APP, NEW_REL, "taken = 1\n")

		start = self.head()
		for label, create in (("committed", committed_by_a_person), ("untracked", left_untracked)):
			with self.subTest(label):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				if os.path.lexists(self.path(NEW_REL)):
					os.remove(self.path(NEW_REL))
				name = self.approved(self.new_file_proposal())
				create()
				count = self.commit_count()

				with patch.object(source, "read_git_state", wraps=source.read_git_state) as read_git:
					apply_job.run_change(name, "apply")

				read_git.assert_not_called()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_STALE, "file đích đã đổi kể từ lúc đề xuất"),
				)
				self.assertEqual(self.read(NEW_REL), "taken = 1\n")
				self.assertEqual(self.commit_count(), count)
				self.assertEqual(self.steps(name), ["approve", "stale"])

	def test_two_proposals_same_file_second_is_stale(self):
		first = self.approved(self.code_proposal())
		second = self.approved(self.code_proposal(content_after="x = 3\n", after_hash=_sha("x = 3\n")))
		count = self.commit_count()

		apply_job.run_change(first, "apply")
		apply_job.run_change(second, "apply")

		self.assertEqual(self.state(first).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(self.state(second).change_status, CHANGE_STATUS_STALE)
		self.assertEqual(self.read(), AFTER)
		self.assertEqual(self.commit_count(), count + 1)
		self.assertEqual(self.state(first).apply_commit_sha, self.head())

	def test_apply_and_undo_rows_carry_commit_sha(self):
		name = self.approved(self.code_proposal())
		old_head = self.head()

		apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual(state.apply_commit_sha, self.head())
		before, after = self.log_row(name, "apply")
		self.assertEqual(before, {"sha256": _sha(BEFORE), "head": old_head})
		self.assertEqual(after, {"sha256": _sha(AFTER), "commit": state.apply_commit_sha, "branch": "main"})

	def test_git_commit_limit_comes_from_the_job_deadline(self):
		start = self.head()
		# Seconds gone from the job budget when the commit starts → the commit's `limit_s` (design 3.5).
		for spent, limit in (
			(100, source.GIT_TIMEOUT_S),
			(COMMAND_TIMEOUT_S - 5, 5),
			(COMMAND_TIMEOUT_S + 50, 1),
		):
			with self.subTest(spent=spent):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				name = self.approved(self.code_proposal())
				clock = iter([1000.0])
				with (
					patch("time.monotonic", side_effect=lambda spent=spent: next(clock, 1000.0 + spent)),
					patch.object(
						process_runner, "git_commit_only", wraps=process_runner.git_commit_only
					) as commit,
				):
					apply_job.run_change(name, "apply")

				self.assertEqual(commit.call_args.args[4], limit)
				self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

	def assert_commit_kept_and_failed(self, name, start, writes):
		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, "commit không đúng nội dung đã duyệt, cần người kiểm"),
		)
		self.assertEqual(self.read(), AFTER)
		self.assertNotEqual(self.head(), start)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), start)
		self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
		self.assertEqual(state.apply_commit_sha, self.head())
		# The only write is the apply itself: the file is never given back once the commit exists.
		self.assertEqual(writes.call_count, 1)
		self.assertEqual(self.steps(name), ["approve", "fail"])
		before, after = self.log_row(name, "fail")
		self.assertEqual(before, {"sha256": _sha(BEFORE), "head": start})
		self.assertEqual(after["commit"], state.apply_commit_sha)
		self.assertEqual(after["sha256"], _sha(AFTER))

	def test_postcheck_unreadable_keeps_commit_and_fails(self):
		start = self.head()
		unreadable = RuntimeError("không đọc được trạng thái git: HEAD commit")
		cases = (
			("git_commit_summary raises", "git_commit_summary", {"side_effect": unreadable}),
			("git_blob raises", "git_blob", {"side_effect": unreadable}),
			("git_is_ancestor None", "git_is_ancestor", {"return_value": None}),
		)
		for label, function, behavior in cases:
			with self.subTest(label):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				name = self.approved(self.code_proposal())
				with (
					patch.object(source, function, **behavior),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
				):
					apply_job.run_change(name, "apply")

				self.log_error.assert_not_called()
				self.assert_commit_kept_and_failed(name, start, writes)

	def test_postcheck_wrong_commit_keeps_commit_and_fails(self):
		start = self.head()
		real_summary = source.git_commit_summary

		def summary_with(**changes):
			return lambda repo: dataclasses.replace(real_summary(repo), **changes)

		# ADR-022 decision 1 step 5, one case per condition of design 4.3 step 3.5.
		cases = (
			("two parents", "git_commit_summary", {"side_effect": summary_with(parents=(start, start))}),
			("old head not an ancestor", "git_is_ancestor", {"return_value": False}),
			("other paths", "git_commit_summary", {"side_effect": summary_with(paths=(REL, "pkg/x.py"))}),
			("other branch", "git_commit_summary", {"side_effect": summary_with(branch="other")}),
			("other blob", "git_blob", {"return_value": b"x = 7\n"}),
		)
		for label, function, behavior in cases:
			with self.subTest(label):
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				name = self.approved(self.code_proposal())
				with (
					patch.object(source, function, **behavior),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
				):
					apply_job.run_change(name, "apply")

				self.assert_commit_kept_and_failed(name, start, writes)
				branch = "other" if label == "other branch" else "main"
				self.assertEqual(self.log_row(name, "fail")[1]["branch"], branch)


class TestCommitFailure(ApplyJobTestCase):
	"""Design 4.3 steps 3.3, 3.4, 3.5, 3.6 and 5 (D-17, ADR-022 decision 1, design-addendum-3 QĐ-B2, QĐ-B5)."""

	def fresh_repo(self):
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		return self.head()

	def proposal_for(self, kind):
		return self.approved(self.new_file_proposal() if kind == "new file" else self.code_proposal())

	def failed(self, *, timed_out=False, output="fatal: lỗi giả"):
		return CommandResult(
			exit_code=None if timed_out else 1,
			output=output,
			duration_ms=3,
			timed_out=timed_out,
			not_found=False,
		)

	def target(self, kind):
		return NEW_REL if kind == "new file" else REL

	def assert_target_given_back(self, kind):
		if kind == "new file":
			self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		else:
			self.assertEqual(self.read(), BEFORE)

	def index_snapshot(self):
		return self.sandbox.git(APP, "diff", "--cached"), self.sandbox.git(APP, "status", "--porcelain")

	def stored(self, name):
		return frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			["change_status", "failure_reason", "apply_commit_sha", "command_output"],
			as_dict=True,
		)

	def test_commit_failure_restores_file_and_index(self):
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				self.fresh_repo()
				self.sandbox.commit_file(APP, "pkg/staged.py", "s = 1\n")
				self.sandbox.stage(APP, "pkg/staged.py", "s = 2\n")
				start = self.head()
				name = self.proposal_for(kind)
				index_before = self.index_snapshot()

				with patch.object(process_runner, "git_commit_only", return_value=self.failed()):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				# Design table 3.2 `GIT_COMMIT_FAILED`, then the short reason from the git output (design 3.5).
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, f"{GIT_COMMIT_FAILED_TEXT}: fatal: lỗi giả"),
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.index_snapshot(), index_before)
				self.assertEqual(self.head(), start)
				self.assertFalse(state.apply_commit_sha)
				# The git output is never stored on the proposal (design 3.5).
				self.assertFalse(state.command_output)
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_commit_timeout_restores_file(self):
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				timed_out = self.failed(timed_out=True, output="")
				with patch.object(process_runner, "git_commit_only", return_value=timed_out):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, f"{GIT_COMMIT_FAILED_TEXT} (quá thời gian)"),
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(self.head(), start)
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_long_git_output_gives_a_short_reason(self):
		self.fresh_repo()
		name = self.proposal_for("changed file")
		output = "dòng đầu\n" + "e" * 300 + "\n"

		with patch.object(process_runner, "git_commit_only", return_value=self.failed(output=output)):
			apply_job.run_change(name, "apply")

		self.assertEqual(self.stored(name).failure_reason, f"{GIT_COMMIT_FAILED_TEXT}: {'e' * 120}")

	def test_new_file_add_failure_removes_the_file(self):
		start = self.fresh_repo()
		name = self.proposal_for("new file")

		with (
			patch.object(process_runner, "git_add_new", return_value=self.failed()),
			patch.object(process_runner, "git_unstage_new", wraps=process_runner.git_unstage_new) as unstage,
			patch.object(process_runner, "git_commit_only") as commit,
		):
			apply_job.run_change(name, "apply")

		state = self.stored(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, f"{GIT_COMMIT_FAILED_TEXT}: fatal: lỗi giả"),
		)
		commit.assert_not_called()
		# Design 4.3 step 3.6: unstage only when `git add` went through.
		unstage.assert_not_called()
		self.assert_target_given_back("new file")
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.head(), start)

	def test_read_back_mismatch_gives_the_file_back(self):
		real_write = file_writer.write_atomic

		def write_reads_back_other_bytes(path, content, new_file):
			written = real_write(path, content, new_file=new_file)
			return _sha("khác\n") if content == AFTER else written

		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				with patch.object(file_writer, "write_atomic", side_effect=write_reads_back_other_bytes):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, "đọc lại sau khi ghi không khớp"),
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(self.head(), start)

	def test_restore_check_failing_reports_restore_failed(self):
		real_head, real_state = source.git_head, source.read_git_state

		def head_unreadable_after_restore():
			calls = iter([real_head])
			return lambda repo: next(calls, lambda repo: None)(repo)

		def refusal_after_restore():
			calls = iter([real_state])
			refused = source.GitState(GIT_LOCKED_TEXT, None, None, None, None)
			return lambda full, **kw: next(calls, lambda full, **kw: refused)(full, **kw)

		cases = (
			("HEAD unreadable", "git_head", head_unreadable_after_restore),
			("git refuses", "read_git_state", refusal_after_restore),
		)
		for label, function, stub in cases:
			for kind in ("changed file", "new file"):
				with self.subTest(label, kind=kind):
					self.fresh_repo()
					name = self.proposal_for(kind)

					with (
						patch.object(process_runner, "git_commit_only", return_value=self.failed()),
						patch.object(source, function, side_effect=stub()),
					):
						apply_job.run_change(name, "apply")

					state = self.stored(name)
					self.assertEqual(
						(state.change_status, state.failure_reason),
						(CHANGE_STATUS_FAILED, GIT_RESTORE_FAILED_TEXT),
					)
					self.assert_target_given_back(kind)
					self.assertFalse(state.apply_commit_sha)
					self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_commit_reported_failed_but_head_moved_goes_to_postcheck(self):
		real_commit = process_runner.git_commit_only

		def commit_then_report_failure(*args):
			real_commit(*args)
			return self.failed()

		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				with (
					patch.object(process_runner, "git_commit_only", side_effect=commit_then_report_failure),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					patch.object(file_writer, "remove_created", wraps=file_writer.remove_created) as removes,
				):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
				self.assertEqual(self.read(self.target(kind)), AFTER)
				self.assertEqual(writes.call_count, 1)
				removes.assert_not_called()
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), start)
				self.assertEqual(state.apply_commit_sha, self.head())
				self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
				self.assertEqual(self.steps(name), ["approve", "apply"])

	def test_postcheck_mismatch_keeps_commit_and_fails(self):
		real_commit = process_runner.git_commit_only

		def overwrite_then_commit(repo, rel, *args):
			# A person overwrites the target between the job's write and its commit.
			self.sandbox.write_unstaged(APP, rel, "x = 7\n")
			return real_commit(repo, rel, *args)

		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				with (
					patch.object(process_runner, "git_commit_only", side_effect=overwrite_then_commit),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
				):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, GIT_COMMIT_MISMATCH_TEXT),
				)
				self.assertEqual(state.apply_commit_sha, self.head())
				# History is not rewritten and the file is not given back.
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), start)
				self.assertEqual(self.read(self.target(kind)), "x = 7\n")
				self.assertEqual(writes.call_count, 1)
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_unexpected_exception_after_write_restores_file(self):
		# The job rolls back before it records the failure; its own commits are mocked here, so a real
		# rollback would also drop the proposal the test made.
		cases = (
			(
				"changed file",
				"person name raises",
				patch.object(apply_job, "_person", side_effect=KeyError("k")),
			),
			(
				"new file",
				"git add raises",
				patch.object(process_runner, "git_add_new", side_effect=KeyError("k")),
			),
		)
		for kind, label, failing in cases:
			with self.subTest(label, kind=kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)
				self.log_error.reset_mock()

				with failing, patch.object(frappe.db, "rollback"):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "KeyError")
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(self.head(), start)
				self.assertFalse(state.apply_commit_sha)
				self.log_error.assert_called_once()
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_unexpected_exception_after_write_with_head_moved_does_not_restore(self):
		# Design 4.3 step 3.4 (D-17): the file is given back only once `git_head == old_head` is proven.
		self.fresh_repo()
		name = self.proposal_for("changed file")
		real_commit = process_runner.git_commit_only

		def commit_then_raise(*args):
			real_commit(*args)
			raise OSError("x")

		with (
			patch.object(process_runner, "git_commit_only", side_effect=commit_then_raise),
			patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
			patch.object(frappe.db, "rollback"),
		):
			apply_job.run_change(name, "apply")

		state = self.stored(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "OSError"))
		self.assertEqual(self.read(), AFTER)
		self.assertEqual(writes.call_count, 1)

	def human_commit(self):
		return self.sandbox.commit_file(APP, "pkg/human.py", "h = 1\n", message="việc tay của người")

	def assert_no_human_email_stored(self, name):
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name},
			fields=["change_step", "error", "value_before", "value_after"],
		)
		proposal = frappe.get_doc(PROPOSAL_DOCTYPE, name).as_dict()
		# The stores are not empty: the check below reads real rows and a real proposal.
		self.assertEqual(len(rows), 2)
		self.assertTrue(proposal.failure_reason)
		self.assertTrue(any(row.error for row in rows))
		for store in (rows, proposal):
			self.assertNotIn(GIT_SANDBOX_EMAIL, json.dumps(store, default=str))

	def test_commit_failed_while_human_commit_moved_head_restores(self):
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				self.fresh_repo()
				name = self.proposal_for(kind)
				human = []

				def human_commits_then_failure(*args):
					human.append(self.human_commit())
					return self.failed()

				with patch.object(process_runner, "git_commit_only", side_effect=human_commits_then_failure):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, f"{GIT_COMMIT_FAILED_TEXT}: fatal: lỗi giả"),
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.head(), human[0])
				self.assertEqual(self.author_email(), GIT_SANDBOX_EMAIL)
				self.assertEqual(self.worktree_changes(), "")
				self.assertFalse(state.apply_commit_sha)
				self.assertEqual(self.steps(name), ["approve", "fail"])
				# NFR-8: the person's author e-mail never reaches the log rows or the proposal.
				self.assert_no_human_email_stored(name)

	def test_commit_failed_on_top_of_an_earlier_bot_commit_restores(self):
		# D-17: HEAD unchanged gives the file back even when HEAD is the bot's own commit of an earlier apply.
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				self.fresh_repo()
				earlier = self.approved(
					self.code_proposal(
						file_path=f"{APP}/pkg/earlier_mod.py",
						is_new_file=1,
						content_before="",
						base_hash="",
						after_hash=_sha(AFTER),
					)
				)
				apply_job.run_change(earlier, "apply")
				start = self.head()
				self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
				self.assertEqual(self.stored(earlier).apply_commit_sha, start)
				name = self.proposal_for(kind)

				with patch.object(process_runner, "git_commit_only", return_value=self.failed()):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, "commit git lỗi, đã trả file về như trước: fatal: lỗi giả"),
				)
				self.assert_target_given_back(kind)
				self.assertEqual(self.head(), start)
				self.assertEqual(self.worktree_changes(), "")
				self.assertFalse(state.apply_commit_sha)
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_apply_accepted_when_bot_commit_lands_after_human_commit(self):
		real_commit = process_runner.git_commit_only
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)
				human = []

				def human_commits_first(*args):
					human.append(self.human_commit())
					return real_commit(*args)

				with patch.object(process_runner, "git_commit_only", side_effect=human_commits_first):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), human[0])
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~2").strip(), start)
				self.assertEqual(state.apply_commit_sha, self.head())
				self.assertEqual(self.read(self.target(kind)), AFTER)

	def test_commit_failed_and_head_unreadable_fails_without_restore(self):
		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				with (
					patch.object(process_runner, "git_commit_only", return_value=self.failed()),
					patch.object(source, "git_head", return_value=None),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					patch.object(file_writer, "remove_created", wraps=file_writer.remove_created) as removes,
					patch.object(
						process_runner, "git_unstage_new", wraps=process_runner.git_unstage_new
					) as unstage,
				):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_ERROR_TEXT)
				)
				self.assertEqual(self.read(self.target(kind)), AFTER)
				self.assertEqual(writes.call_count, 1)
				removes.assert_not_called()
				unstage.assert_not_called()
				self.assertEqual(self.head(), start)
				self.assertFalse(state.apply_commit_sha)
				self.assertNotIn("commit", self.log_row(name, "fail")[1] or {})
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_head_moved_and_summary_unreadable_fails_without_restore(self):
		real_commit = process_runner.git_commit_only

		def commit_then_report_failure(*args):
			real_commit(*args)
			return self.failed()

		for kind in ("changed file", "new file"):
			with self.subTest(kind):
				start = self.fresh_repo()
				name = self.proposal_for(kind)

				with (
					patch.object(process_runner, "git_commit_only", side_effect=commit_then_report_failure),
					patch.object(source, "git_commit_summary", side_effect=RuntimeError("không đọc được")),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					patch.object(file_writer, "remove_created", wraps=file_writer.remove_created) as removes,
				):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_ERROR_TEXT)
				)
				self.assertEqual(self.read(self.target(kind)), AFTER)
				self.assertEqual(writes.call_count, 1)
				removes.assert_not_called()
				self.assertNotEqual(self.head(), start)
				self.assertFalse(state.apply_commit_sha)
				self.log_error.assert_not_called()
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_exception_after_commit_landed_does_not_restore(self):
		cases = (
			("git_blob raises KeyError", "git_blob"),
			("git_commit_summary raises KeyError", "git_commit_summary"),
		)
		for label, function in cases:
			with self.subTest(label):
				start = self.fresh_repo()
				name = self.proposal_for("changed file")

				with (
					patch.object(source, function, side_effect=KeyError("k")),
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					patch.object(frappe.db, "rollback"),
				):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "KeyError")
				)
				self.assertEqual(self.read(), AFTER)
				self.assertEqual(writes.call_count, 1)
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), start)
				self.assertEqual(state.apply_commit_sha, self.head())
				before, after = self.log_row(name, "fail")
				self.assertEqual(before, {"sha256": _sha(BEFORE), "head": start})
				self.assertEqual(after["commit"], state.apply_commit_sha)

	def test_fail_row_with_commit_sha_carries_value_after_commit(self):
		cases = (
			("mismatch", {"return_value": b"x = 7\n"}),
			("RuntimeError at post-check", {"side_effect": RuntimeError("không đọc được")}),
		)
		for label, behavior in cases:
			with self.subTest(label):
				start = self.fresh_repo()
				name = self.proposal_for("changed file")

				with patch.object(source, "git_blob", **behavior):
					apply_job.run_change(name, "apply")

				state = self.stored(name)
				self.assertEqual(state.failure_reason, GIT_COMMIT_MISMATCH_TEXT)
				self.assertTrue(state.apply_commit_sha)
				before, after = self.log_row(name, "fail")
				self.assertEqual(
					after, {"sha256": _sha(AFTER), "commit": state.apply_commit_sha, "branch": "main"}
				)
				self.assertEqual(before, {"sha256": _sha(BEFORE), "head": start})


class TestRunChangeSkeleton(ApplyJobTestCase):
	def assert_failed_without_writing(self, name, reason, count):
		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.commit_count(), count)
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_rechecks_fail_without_writing(self):
		def switch_off(name):
			set_agent_settings(code_change_enabled=0)

		def role_lost(name):
			# A user cannot change their own roles: an administrator takes the role away.
			frappe.set_user("Administrator")
			frappe.get_doc("User", ACTOR).remove_roles(ROLE_INSTRUCTOR)
			frappe.set_user(ACTOR)

		def digest_edited(name):
			frappe.db.set_value(PROPOSAL_DOCTYPE, name, "content_after", "import os\n", update_modified=False)

		def app_removed(name):
			set_agent_settings(code_change_apps="helpdesk")

		def other_session_user(name):
			frappe.set_user("Administrator")

		# Design table 4.3 step 4.2, one case per row (the role row has two sides).
		cases = (
			("switch off", None, switch_off, "công tắc đang tắt"),
			("role lost", None, role_lost, "người duyệt không còn quyền"),
			("digest edited", None, digest_edited, "nội dung đề xuất đã bị sửa sau khi duyệt"),
			("app removed", None, app_removed, "app không có trong danh sách được sửa"),
			("wrong session user", None, other_session_user, "sai người chạy job"),
			(
				"commit_message edited",
				{"commit_message": "erp_ai: thông điệp khác"},
				None,
				"nội dung đề xuất đã bị sửa sau khi duyệt",
			),
			("after_hash mismatch", {"after_hash": _sha("y = 3\n")}, None, "nội dung lưu không khớp dấu"),
		)
		start = self.head()
		for label, edit_before_approval, change_after_approval, reason in cases:
			with self.subTest(label):
				# Each case starts from the same repo, whatever an earlier case did.
				self.sandbox.git(APP, "reset", "--hard", "--quiet", start)
				frappe.set_user("Administrator")
				frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)
				frappe.set_user(ACTOR)
				set_agent_settings(code_change_enabled=1, code_change_apps=APP)
				name = self.code_proposal()
				if edit_before_approval:
					# Edited before approval, so the approved digest covers it and only this row can catch it.
					frappe.db.set_value(PROPOSAL_DOCTYPE, name, edit_before_approval, update_modified=False)
				self.approved(name)
				if change_after_approval:
					change_after_approval(name)
				count = self.commit_count()

				apply_job.run_change(name, "apply")

				self.assert_failed_without_writing(name, reason, count)

	def test_approver_who_never_carries_authority_fails(self):
		frappe.set_user("Administrator")
		name = self.code_proposal()
		transitions.approve(name, "Administrator")
		count = self.commit_count()

		apply_job.run_change(name, "apply")

		self.assert_failed_without_writing(name, "người duyệt không còn quyền", count)

	def test_lock_timeout_fails_without_writing(self):
		name = self.approved(self.code_proposal())
		count = self.commit_count()

		with patch.object(apply_job, "LOCK_TIMEOUT_S", 0.2), filelock(apply_job.LOCK_NAME, is_global=True):
			apply_job.run_change(name, "apply")

		self.assert_failed_without_writing(name, "đang có thay đổi khác chạy, không lấy được khóa", count)

	def test_repeat_job_does_nothing_when_not_approved(self):
		pending = self.code_proposal()
		applied = self.approved(self.code_proposal())
		apply_job.run_change(applied, "apply")
		count = self.commit_count()

		for name, steps in ((pending, []), (applied, ["approve", "apply"])):
			with self.subTest(steps=steps), patch.object(apply_job, "filelock") as lock:
				status = self.state(name).change_status

				apply_job.run_change(name, "apply")

				lock.assert_not_called()
				self.assertEqual(self.state(name).change_status, status)
				self.assertEqual(self.steps(name), steps)
				self.assertEqual(self.commit_count(), count)

	def test_applying_state_committed_before_rechecks_run(self):
		name = self.approved(self.code_proposal())
		seen = []
		real_settings = policy.current_change_settings

		def settings():
			seen.append(
				(frappe.db.commit.call_count, frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status"))
			)
			return real_settings()

		with patch.object(policy, "current_change_settings", side_effect=settings):
			apply_job.run_change(name, "apply")

		self.assertEqual(seen, [(1, "Đang áp dụng")])
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

	def info_lines(self, logger):
		return [
			call.args
			for call in logger.return_value.info.call_args_list
			if call.args and call.args[0].startswith("erp_ai change ")
		]

	def test_one_log_line_with_the_commit_and_no_content(self):
		name = self.approved(self.code_proposal())
		with patch.object(frappe, "logger") as logger:
			apply_job.run_change(name, "apply")

		lines = self.info_lines(logger)
		self.assertEqual(len(lines), 1)
		template, *values = lines[0]
		self.assertEqual(template, "erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s")
		self.assertEqual(values[:3], [name, "apply", CHANGE_STATUS_APPLIED])
		self.assertIsInstance(values[3], int)
		self.assertEqual(values[4], self.head())
		logger.assert_any_call("erp_ai")
		self.assertNotIn("x = 2", str(logger.mock_calls))

	def test_log_line_without_commit_shows_a_dash(self):
		name = self.approved(self.code_proposal())
		set_agent_settings(code_change_enabled=0)
		with patch.object(frappe, "logger") as logger:
			apply_job.run_change(name, "apply")

		lines = self.info_lines(logger)
		self.assertEqual(len(lines), 1)
		self.assertEqual((lines[0][3], lines[0][5]), (CHANGE_STATUS_FAILED, "-"))


class TestNewFileAndUndo(ApplyJobTestCase):
	def applied(self, name):
		apply_job.run_change(self.approved(name), "apply")
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		return name

	def test_new_file_is_created_and_committed(self):
		name = self.applied(self.new_file_proposal())

		self.assertEqual(self.read(NEW_REL), AFTER)
		self.assertEqual(self.sandbox.git(APP, "show", "--name-only", "--format=", "HEAD").split(), [NEW_REL])
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.state(name).apply_commit_sha, self.head())

	def test_new_file_that_now_exists_is_stale(self):
		name = self.approved(self.new_file_proposal())
		self.sandbox.commit_file(APP, NEW_REL, "taken = 1\n")

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_STALE)
		self.assertEqual(self.read(NEW_REL), "taken = 1\n")

	def test_new_file_failed_commit_removes_the_file_and_unstages_it(self):
		name = self.approved(self.new_file_proposal())
		failed = CommandResult(exit_code=1, output="fatal", duration_ms=3, timed_out=False, not_found=False)
		with patch.object(process_runner, "git_commit_only", return_value=failed):
			apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_FAILED)
		self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		self.assertEqual(self.worktree_changes(), "")

	def test_undo_restores_the_old_bytes_in_one_commit(self):
		name = self.applied(self.code_proposal())
		apply_commit, count = self.head(), self.commit_count()
		transitions.request_undo(name, ACTOR)

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.commit_count(), count + 1)
		self.assertEqual(state.undo_commit_sha, self.head())
		self.assertEqual(state.apply_commit_sha, apply_commit)
		self.assertIn(apply_commit, self.sandbox.git(APP, "log", "-1", "--format=%b"))
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "apply", "undo"])

	def test_undo_of_a_new_file_removes_it_in_one_commit(self):
		name = self.applied(self.new_file_proposal())
		transitions.request_undo(name, ACTOR)

		apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.sandbox.git(APP, "show", "--name-only", "--format=", "HEAD").split(), [NEW_REL])

	def test_undo_still_works_after_the_app_left_the_list(self):
		name = self.applied(self.code_proposal())
		set_agent_settings(code_change_enabled=0, code_change_apps="")
		transitions.request_undo(name, ACTOR)

		apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		self.assertEqual(self.read(), BEFORE)

	def test_undo_refuses_a_file_changed_after_apply(self):
		name = self.applied(self.code_proposal())
		self.sandbox.commit_file(APP, REL, "x = 3\n")
		transitions.request_undo(name, ACTOR)

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_FAILED)
		# Design 4.4 step 3 (design.md:667), word for word.
		self.assertEqual(state.failure_reason, "file đã đổi sau khi áp dụng, không hoàn tác")
		self.assertEqual(self.read(), "x = 3\n")

	def test_undo_failed_commit_puts_the_applied_content_back(self):
		name = self.applied(self.code_proposal())
		transitions.request_undo(name, ACTOR)
		failed = CommandResult(exit_code=1, output="fatal", duration_ms=3, timed_out=False, not_found=False)
		with patch.object(process_runner, "git_commit_only", return_value=failed):
			apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_FAILED)
		self.assertEqual(self.read(), AFTER)
		self.assertEqual(self.worktree_changes(), "")

	def test_undo_job_without_a_request_does_nothing(self):
		name = self.applied(self.code_proposal())
		count = self.commit_count()

		apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(self.commit_count(), count)


class TestUndoCode(ApplyJobTestCase):
	"""Design 4.4 steps 2, 3, 5, 6 (post-check) and 7 (AC-7, AC-20, D-18, ADR-022 decisions 1 and 6, QĐ-B2, QĐ-B5)."""

	KINDS = ("changed file", "new file")

	def setUp(self):
		super().setUp()
		# Undo is asked by a second instructor, so a check that reads `decided_by` instead of `undo_by` fails.
		create_agent(UNDOER)
		frappe.set_user("Administrator")
		frappe.get_doc("User", UNDOER).add_roles(ROLE_INSTRUCTOR)
		frappe.set_user(ACTOR)

	def undo_requested(self, kind="changed file"):
		"""Apply a proposal of `kind`, then ask for its undo as `UNDOER`; returns (name, apply commit)."""
		frappe.set_user(ACTOR)
		name = self.approved(self.new_file_proposal() if kind == "new file" else self.code_proposal())
		apply_job.run_change(name, "apply")
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		transitions.request_undo(name, UNDOER)
		frappe.set_user(UNDOER)
		return name, self.head()

	def target(self, kind):
		return NEW_REL if kind == "new file" else REL

	def assert_target_undone(self, kind):
		if kind == "new file":
			self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		else:
			self.assertEqual(self.read(), BEFORE)

	def tree_paths(self, rev="HEAD"):
		return self.sandbox.git(APP, "ls-tree", "-r", "--name-only", rev).split()

	def test_undo_restores_previous_bytes(self):
		name, _ = self.undo_requested()

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		with open(self.path(), "rb") as handle:
			self.assertEqual(handle.read(), BEFORE.encode("utf-8"))
		self.assertEqual(file_writer.sha256_of(self.path()), _sha(BEFORE))

	def test_undo_removes_created_file(self):
		name, _ = self.undo_requested("new file")

		apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		self.assertEqual(self.worktree_changes(), "")

	def test_undo_refused_when_file_changed_after_apply(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				name, _ = self.undo_requested(kind)
				self.sandbox.write_unstaged(APP, self.target(kind), "x = 3\n")
				count = self.commit_count()

				apply_job.run_change(name, "undo")

				state = self.state(name)
				# Design 4.4 step 3, word for word.
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, "file đã đổi sau khi áp dụng, không hoàn tác"),
				)
				self.assertEqual(self.read(self.target(kind)), "x = 3\n")
				self.assertEqual(self.commit_count(), count)
				self.assertIsNone(state.undo_commit_sha)
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_allowed_with_switch_off(self):
		name, _ = self.undo_requested()
		set_agent_settings(code_change_enabled=0)

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		self.assertEqual(self.read(), BEFORE)

	def test_undo_creates_one_commit_restoring_previous_bytes(self):
		name, apply_commit = self.undo_requested()
		count = self.commit_count()

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual(self.commit_count(), count + 1)
		self.assertEqual(state.undo_commit_sha, self.head())
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), apply_commit)
		self.assertEqual(self.sandbox.git(APP, "show", "--name-only", "--format=", "HEAD").split(), [REL])
		self.assertEqual(self.sandbox.git(APP, "show", f"HEAD:{REL}"), BEFORE)
		self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
		self.assertIn(apply_commit, self.sandbox.git(APP, "log", "-1", "--format=%b"))
		self.assertEqual(self.worktree_changes(), "")
		self.assertEqual(self.steps(name), ["approve", "apply", "undo"])

	def test_undo_new_file_removes_from_disk_and_tree(self):
		name, apply_commit = self.undo_requested("new file")
		self.assertIn(NEW_REL, self.tree_paths())
		count = self.commit_count()

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_UNDONE)
		self.assertFalse(os.path.lexists(self.path(NEW_REL)))
		self.assertEqual(self.commit_count(), count + 1)
		self.assertEqual(state.undo_commit_sha, self.head())
		self.assertEqual(
			self.sandbox.git(APP, "show", "--name-status", "--format=", "HEAD").split(), ["D", NEW_REL]
		)
		self.assertNotIn(NEW_REL, self.tree_paths())
		self.assertEqual(self.sandbox.git(APP, "ls-files", "--", NEW_REL), "")
		# The apply commit stays in history (AC-20, A-14).
		self.assertIn(NEW_REL, self.tree_paths(apply_commit))
		self.assertEqual(self.worktree_changes(), "")

	def test_undo_new_file_still_on_disk_after_remove_fails_without_commit(self):
		name, apply_commit = self.undo_requested("new file")
		count = self.commit_count()

		with patch.object(file_writer, "remove_created") as remove:
			apply_job.run_change(name, "undo")

		remove.assert_called_once_with(self.path(NEW_REL))
		state = self.state(name)
		# Design 4.4 step 5: the file must be gone before the undo commit.
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, "đọc lại sau khi ghi không khớp"),
		)
		self.assertEqual(self.read(NEW_REL), AFTER)
		self.assertEqual((self.head(), self.commit_count()), (apply_commit, count))

	def test_undo_row_carries_sha256_head_commit_branch(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				name, apply_commit = self.undo_requested(kind)

				apply_job.run_change(name, "undo")

				state = self.state(name)
				self.assertEqual(state.change_status, CHANGE_STATUS_UNDONE)
				before, after = self.log_row(name, "undo")
				# Design 4.4 step 7 and design-addendum-3 QĐ-B5.
				self.assertEqual(before, {"sha256": _sha(AFTER), "head": apply_commit})
				restored = None if kind == "new file" else _sha(BEFORE)
				self.assertEqual(
					after, {"sha256": restored, "commit": state.undo_commit_sha, "branch": "main"}
				)

	def test_undo_rechecks_fail_without_writing(self):
		def role_lost():
			frappe.set_user("Administrator")
			frappe.get_doc("User", UNDOER).remove_roles(ROLE_INSTRUCTOR)
			frappe.set_user(UNDOER)

		def digest_edited():
			frappe.db.set_value(
				PROPOSAL_DOCTYPE, name, "content_before", "import os\n", update_modified=False
			)

		def approver_session():
			# The approver is a valid instructor, but the undo job must run as the person who asked for it.
			frappe.set_user(ACTOR)

		def guard_refusal():
			# The guard of design 3.2 with the extension list of today: `.py` is no longer writable.
			patcher = patch.object(source, "DUOI_CHO_PHEP", {".txt"})
			patcher.start()
			return patcher

		# Design 4.4 step 2, one case per row; the switch is not a row (G-1).
		cases = (
			("wrong session user", approver_session, "sai người chạy job"),
			("role lost", role_lost, "người duyệt không còn quyền"),
			("digest edited", digest_edited, "nội dung đề xuất đã bị sửa sau khi duyệt"),
			("guard refusal", guard_refusal, "đuôi file không được phép"),
		)
		for label, change, reason in cases:
			with self.subTest(label):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				frappe.set_user("Administrator")
				frappe.get_doc("User", UNDOER).add_roles(ROLE_INSTRUCTOR)
				name, apply_commit = self.undo_requested()
				count = self.commit_count()
				patcher = change()

				with (
					patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					patch.object(apply_job, "_undo_code", wraps=apply_job._undo_code) as undo_steps,
				):
					apply_job.run_change(name, "undo")

				if patcher:
					patcher.stop()
				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
				self.assertEqual(self.read(), AFTER)
				self.assertEqual((self.head(), self.commit_count()), (apply_commit, count))
				writes.assert_not_called()
				# The step 2 recheck refuses, not the guard of steps 3 to 7 that repeats it.
				undo_steps.assert_not_called()
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_checks_the_undoer_not_the_approver(self):
		name, _ = self.undo_requested()
		# The approver lost the role after apply; the undoer still holds it and runs the job.
		frappe.set_user("Administrator")
		frappe.get_doc("User", ACTOR).remove_roles(ROLE_INSTRUCTOR)
		frappe.set_user(UNDOER)

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))

	def test_undo_does_not_rebuild_the_commit_message_preview(self):
		# Design 4.4 step 2 has no preview row: the undo commit uses `undo_message`, so a later change of
		# `apply_message` must not block it. The stored `commit_message` (a digest field) stays as approved.
		name, _ = self.undo_requested()

		with patch.object(change_text, "apply_message", return_value=("tiêu đề khác", "nội dung khác")):
			apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		self.assert_target_undone("changed file")

	def test_undo_does_not_recheck_the_stored_content_after_hash(self):
		# Design 4.4 step 2 has no `sha256(content_after) == after_hash` row; step 3 checks the file on disk.
		# The digest is rebuilt so only that apply-only row would refuse.
		name, _ = self.undo_requested()
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, name)
		doc.content_after = "y = 0\n"
		frappe.db.set_value(
			PROPOSAL_DOCTYPE,
			name,
			{"content_after": doc.content_after, "approved_digest": transitions.content_digest(doc)},
			update_modified=False,
		)

		apply_job.run_change(name, "undo")

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		self.assert_target_undone("changed file")

	def test_undo_guard_allows_only_the_proposal_app(self):
		name, _ = self.undo_requested()
		set_agent_settings(code_change_enabled=0, code_change_apps="")

		with patch.object(change_guard, "check_write_path", wraps=change_guard.check_write_path) as guard:
			apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		self.assertTrue(guard.call_args_list)
		for call in guard.call_args_list:
			self.assertEqual(call.args[1], (APP,))

	def assert_undo_commit_kept_and_failed(self, name, kind, apply_commit, branch="main"):
		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_COMMIT_MISMATCH_TEXT)
		)
		# The undo commit exists: the file is never given back and history is never rewritten (QĐ-B2 item 1).
		self.assert_target_undone(kind)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), apply_commit)
		self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
		self.assertEqual(state.undo_commit_sha, self.head())
		self.assertEqual(self.steps(name), ["approve", "apply", "fail"])
		before, after = self.log_row(name, "fail")
		self.assertEqual(before, {"sha256": _sha(AFTER), "head": apply_commit})
		restored = None if kind == "new file" else _sha(BEFORE)
		self.assertEqual(after, {"sha256": restored, "commit": state.undo_commit_sha, "branch": branch})

	def test_undo_postcheck_wrong_commit_keeps_commit_and_fails(self):
		real_summary = source.git_commit_summary

		def summary_with(**changes):
			return lambda repo: dataclasses.replace(real_summary(repo), **changes)

		# Design 4.4 step 6 "Kiểm sau", one case per condition; each builds its patch from
		# (target, commit before apply, apply commit = old HEAD).
		cases = (
			(
				"two parents",
				"git_commit_summary",
				lambda rel, base, old: {"side_effect": summary_with(parents=(old, old))},
			),
			(
				# The old HEAD (the apply commit) is not an ancestor of the commit before it.
				"old head not an ancestor",
				"git_commit_summary",
				lambda rel, base, old: {"side_effect": summary_with(parents=(base,))},
			),
			(
				"other paths",
				"git_commit_summary",
				lambda rel, base, old: {"side_effect": summary_with(paths=(rel, "pkg/x.py"))},
			),
			(
				"other branch",
				"git_commit_summary",
				lambda rel, base, old: {"side_effect": summary_with(branch="other")},
			),
			("other blob", "git_blob", lambda rel, base, old: {"return_value": b"x = 7\n"}),
		)
		for kind in self.KINDS:
			for label, function, behavior in cases:
				with self.subTest(kind=kind, case=label):
					self.sandbox = GitSandbox(self)
					base = self.sandbox.commit_file(APP, REL, BEFORE)
					name, apply_commit = self.undo_requested(kind)
					with (
						patch.object(source, function, **behavior(self.target(kind), base, apply_commit)),
						patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic) as writes,
					):
						apply_job.run_change(name, "undo")

					self.assert_undo_commit_kept_and_failed(
						name, kind, apply_commit, branch="other" if label == "other branch" else "main"
					)
					self.assertEqual(writes.call_count, 0 if kind == "new file" else 1)

	def test_undo_postcheck_blob_must_match_the_restored_side(self):
		# Changed file: the blob of the undo commit must be `content_before`; new file: the path must be gone.
		for kind, wrong_blob in (("changed file", None), ("new file", AFTER.encode("utf-8"))):
			with self.subTest(kind):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				name, apply_commit = self.undo_requested(kind)

				with patch.object(source, "git_blob", return_value=wrong_blob):
					apply_job.run_change(name, "undo")

				self.assert_undo_commit_kept_and_failed(name, kind, apply_commit)

	def test_undo_postcheck_unreadable_keeps_commit_and_fails(self):
		unreadable = RuntimeError("không đọc được trạng thái git: HEAD commit")
		for kind in self.KINDS:
			for label, function in (
				("git_commit_summary raises", "git_commit_summary"),
				("git_blob raises", "git_blob"),
				("git_is_ancestor None", "git_is_ancestor"),
			):
				with self.subTest(kind=kind, case=label):
					self.sandbox = GitSandbox(self)
					self.sandbox.commit_file(APP, REL, BEFORE)
					name, apply_commit = self.undo_requested(kind)
					real = getattr(source, function)
					committed = []

					def after_commit(*args, real=real, function=function, committed=committed):
						# Only the post-check read fails; reads before the undo commit stay real.
						if not committed:
							return real(*args)
						if function == "git_is_ancestor":
							return None
						raise unreadable

					real_commit = process_runner.git_commit_only

					def commit_then_mark(*args, committed=committed, real_commit=real_commit):
						result = real_commit(*args)
						committed.append(True)
						return result

					with (
						patch.object(process_runner, "git_commit_only", side_effect=commit_then_mark),
						patch.object(source, function, side_effect=after_commit),
					):
						apply_job.run_change(name, "undo")

					self.log_error.assert_not_called()
					branch = None if function == "git_commit_summary" else "main"
					self.assert_undo_commit_kept_and_failed(name, kind, apply_commit, branch=branch)

	def test_undo_git_commit_limit_comes_from_the_job_deadline(self):
		name, _ = self.undo_requested()
		clock = iter([1000.0])
		with (
			patch("time.monotonic", side_effect=lambda: next(clock, 1000.0 + COMMAND_TIMEOUT_S - 5)),
			patch.object(process_runner, "git_commit_only", wraps=process_runner.git_commit_only) as commit,
		):
			apply_job.run_change(name, "undo")

		self.assertEqual(commit.call_args.args[4], 5)
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)


class TestApplyCommand(ApplyJobTestCase):
	def command_proposal(self, args):
		name = make_change_proposal(CHANGE_KIND_COMMAND, app=APP, command_args=json.dumps(args)).name
		return self.approved(name)

	def result(self, **fields):
		values = {"exit_code": 0, "output": "xong", "duration_ms": 12, "timed_out": False, "not_found": False}
		return CommandResult(**{**values, **fields})

	def test_command_runs_with_the_stored_arguments(self):
		name = self.command_proposal(["build", "--app", APP])
		with patch.object(process_runner, "run_bench", return_value=self.result()) as run_bench:
			apply_job.run_change(name, "apply")

		(args, limit), _ = run_bench.call_args
		self.assertEqual(args, ["build", "--app", APP])
		self.assertGreater(limit, 0)
		state = self.state(name)
		self.assertEqual((state.change_status, state.exit_code), (CHANGE_STATUS_APPLIED, 0))
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "command_output"), "xong")
		self.assertEqual(self.steps(name), ["approve", "apply"])

	def test_failed_timed_out_and_missing_command_end_as_failed(self):
		for fields, reason in (
			({"exit_code": 2}, "lệnh thoát với mã 2"),
			({"exit_code": None, "timed_out": True}, "lệnh chạy quá giờ và đã bị dừng"),
			({"exit_code": 127, "not_found": True}, "không tìm thấy lệnh bench"),
		):
			name = self.command_proposal(["--site", frappe.local.site, "migrate"])
			with patch.object(process_runner, "run_bench", return_value=self.result(**fields)):
				apply_job.run_change(name, "apply")

			state = self.state(name)
			self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))

	def test_arguments_no_longer_allowed_never_run(self):
		name = self.command_proposal(["build", "--app", APP])
		set_agent_settings(code_change_apps="helpdesk")
		with patch.object(process_runner, "run_bench") as run_bench:
			apply_job.run_change(name, "apply")

		run_bench.assert_not_called()
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_FAILED)

	def test_command_limit_comes_from_the_job_deadline(self):
		name = self.command_proposal(["version"])
		clock = iter([1000.0])
		with (
			patch("time.monotonic", side_effect=lambda: next(clock, 1100.0)),
			patch.object(process_runner, "run_bench", return_value=self.result()) as run_bench,
		):
			apply_job.run_change(name, "apply")

		(_, limit), _ = run_bench.call_args
		self.assertEqual(limit, COMMAND_TIMEOUT_S - 100)

	def test_state_is_committed_before_the_command_runs(self):
		name = self.command_proposal(["version"])
		seen = []

		def run(args, limit):
			seen.append(
				(frappe.db.commit.call_count, frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status"))
			)
			return self.result()

		with patch.object(process_runner, "run_bench", side_effect=run):
			apply_job.run_change(name, "apply")

		self.assertEqual(seen, [(1, "Đang áp dụng")])
		self.assertNotEqual(self.state(name).change_status, CHANGE_STATUS_APPROVED)
