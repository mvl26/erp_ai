import contextlib
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.error import log_error as real_log_error
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import authority, change_text, policy
from erp_ai.agent.changes import apply_job, file_writer, process_runner, result_comment, transitions
from erp_ai.agent.changes.process_runner import CommandResult
from erp_ai.agent.tools import change_guard, source
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import (
	AGENT_USER,
	BOT_GIT_EMAIL,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	COMMAND_TIMEOUT_S,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_AGENT,
	ROLE_INSTRUCTOR,
)
from erp_ai.test_utils import (
	GIT_SANDBOX_EMAIL,
	GitSandbox,
	RealCoreReposUntouchedMixin,
	add_credential,
	make_change_proposal,
	pin_agent_roles,
	set_agent_settings,
)

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
GIT_NOT_ANCESTOR_TEXT = "commit áp dụng không còn nằm trong lịch sử nhánh đang checkout"
# AC-13, NFR-5: a fake key planted in the process environment and in the stored credential.
FAKE_KEY = "sk-ant-ERPAI-T22-LEAK-5d0c71"
PROPOSER = "propose.t22@example.com"


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

	def add_proposer(self):
		"""Create `PROPOSER`, an agent who may call the propose tools; the session goes back to `ACTOR`."""
		frappe.set_user("Administrator")
		create_agent(PROPOSER)
		frappe.get_doc("User", PROPOSER).add_roles(ROLE_AGENT)
		frappe.set_user(ACTOR)

	def tool_context(self, ticket, run_id):
		"""The context the runner hands the propose tools for `PROPOSER` on `ticket`, with `ACTOR` instructing."""
		return ToolContext(
			ticket_name=ticket,
			effective_level="L3",
			instructor=ACTOR,
			run_id=run_id,
			category_mapping={},
			agent_user=PROPOSER,
			change_enabled=True,
			allowed_apps=(APP,),
		)


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
			({"code_change_apps": "helpdesk"}, f"mục 1 ({FILE_PATH}): app không có trong danh sách được sửa"),
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
		self.assertEqual(before, {"head": old_head, "files": {REL: _sha(BEFORE)}})
		self.assertEqual(after, {"commit": state.apply_commit_sha, "branch": "main", "files": {REL: _sha(AFTER)}})

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
		self.assertEqual(before, {"head": start, "files": {REL: _sha(BEFORE)}})
		self.assertEqual(after["commit"], state.apply_commit_sha)
		self.assertEqual(after["files"][REL], _sha(AFTER))

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
		# Ordinary words: a 300-letter run would be masked as key-like (design addendum 4 QĐ-D1).
		output = "dòng đầu\n" + "lỗi " * 80 + "\n"

		with patch.object(process_runner, "git_commit_only", return_value=self.failed(output=output)):
			apply_job.run_change(name, "apply")

		expected = " ".join(["lỗi"] * 80)[:120]
		self.assertEqual(self.stored(name).failure_reason, f"{GIT_COMMIT_FAILED_TEXT}: {expected}")

	def test_git_short_line_masks_paths_urls_emails_and_key_like_words(self):
		# NFR-8, AC-13, design addendum 4 QĐ-D1: no path, URL, email, key=value, `~` path or key reaches the store.
		key = "Ab3dEf6hIj9lMn2pQr5tUv8xYz1bCd4fGh7jKl0n"
		self.assertEqual(len(key), 40)
		cases = (
			(
				"fatal: Unable to create '/home/u/bench/apps/x/.git/index.lock': File exists.",
				("/home/u/bench/apps/x/.git/index.lock", "/home", "index.lock"),
				("fatal:", "File exists."),
			),
			(
				"https://x-token-FAKE@host/r.git",
				("https://x-token-FAKE@host/r.git", "x-token-FAKE", "host"),
				(),
			),
			("real.person@example.com", ("real.person@example.com", "example.com"), ()),
			("token=abc", ("token=abc", "abc"), ()),
			("~/x", ("~/x",), ()),
			("C:\\x", ("C:\\x",), ()),
			(key, (key,), ()),
		)
		for line, secrets, kept in cases:
			with self.subTest(line):
				short = apply_job._git_short_line(line)
				for secret in secrets:
					self.assertNotIn(secret, short)
				self.assertIn("…", short)
				for word in kept:
					self.assertIn(word, short)

	def test_git_short_line_masks_each_rule_member_alone(self):
		# Review round 1 (design addendum 4 QĐ-D1): each word holds exactly one rule member, so dropping
		# that member, or moving the key-like threshold off 20, changes the result.
		alnum_20 = "Ab3dEf6hIj9lMn2pQr5t"
		self.assertEqual(len(alnum_20), 20)
		cases = (
			("HEAD~1", "…"),
			("~miyano", "…"),
			(alnum_20, "…"),
			(alnum_20[:19], alnum_20[:19]),
			(("ab_" * 7)[:20], "…"),
			(("ab-" * 7)[:20], "…"),
			(("ab+" * 7)[:20], "…"),
			("C:\\x", "…"),
			("token=abc", "…"),
		)
		for word, expected in cases:
			with self.subTest(word):
				self.assertEqual(apply_job._git_short_line(f"lỗi {word} cuối"), f"lỗi {expected} cuối")

	def test_git_short_line_masks_before_cut_and_drops_control_chars(self):
		# Design addendum 4 QĐ-D1 steps (1) and (4): mask first, cut to 120 after.
		prefix = ("lỗi " * 30)[:109] + " "
		self.assertEqual(len(prefix), 110)
		token = "Z9" * 20
		short = apply_job._git_short_line(prefix + token + " lỗi" * 10)
		self.assertNotIn("Z", short)
		self.assertNotIn("9", short)
		self.assertIn("…", short)
		self.assertLessEqual(len(short), 120)
		self.assertLessEqual(len(apply_job._git_short_line("lỗi " * 80)), 120)

		self.assertEqual(apply_job._git_short_line("fatal:\x1b[31mlỗi\rđỏ\t\tcuối"), "fatal: [31mlỗi đỏ cuối")
		self.assertEqual(apply_job._git_short_line("/a/b token=x ~/y"), "… … …")
		for empty in ("", " \t ", "\x1b\x07\r"):
			with self.subTest(repr(empty)):
				self.assertEqual(apply_job._git_short_line(empty), "")

		# An output whose last line is empty after cleaning gives only the sentence, without `: `.
		name = self.proposal_for("changed file")
		with patch.object(
			process_runner, "git_commit_only", return_value=self.failed(output="fatal\n\x1b\x07\n")
		):
			apply_job.run_change(name, "apply")
		self.assertEqual(self.stored(name).failure_reason, GIT_COMMIT_FAILED_TEXT)

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
					patch.object(file_writer, "remove_file", wraps=file_writer.remove_file) as removes,
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

		def overwrite_then_commit(repo, rels, *args):
			# A person overwrites the target between the job's write and its commit.
			(rel,) = rels
			self.sandbox.write_unstaged(APP, rel, "x = 7\n")
			return real_commit(repo, rels, *args)

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

	def assert_no_human_email_stored(self, name, row_count=2):
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name},
			fields=["change_step", "error", "value_before", "value_after"],
		)
		proposal = frappe.get_doc(PROPOSAL_DOCTYPE, name).as_dict()
		# The stores are not empty: the check below reads real rows and a real proposal.
		self.assertEqual(len(rows), row_count)
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
		# Undo side (design 4.4 step 6, same rule as 4.3 step 3.4): the applied bytes come back.
		for kind in ("changed file", "new file"):
			with self.subTest("undo", kind=kind):
				self.fresh_repo()
				name = self.proposal_for(kind)
				apply_job.run_change(name, "apply")
				self.assertEqual(self.stored(name).change_status, CHANGE_STATUS_APPLIED)
				transitions.request_undo(name, ACTOR)
				human = []

				def human_commits_then_failure(*args):
					human.append(self.human_commit())
					return self.failed()

				with patch.object(process_runner, "git_commit_only", side_effect=human_commits_then_failure):
					apply_job.run_change(name, "undo")

				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, f"{GIT_COMMIT_FAILED_TEXT}: fatal: lỗi giả"),
				)
				self.assertEqual(self.read(self.target(kind)), AFTER)
				self.assertEqual(self.head(), human[0])
				self.assertEqual(self.author_email(), GIT_SANDBOX_EMAIL)
				self.assertEqual(self.worktree_changes(), "")
				self.assertFalse(state.undo_commit_sha)
				self.assertFalse(self.stored(name).command_output)
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])
				self.assert_no_human_email_stored(name, row_count=3)

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
					patch.object(file_writer, "remove_file", wraps=file_writer.remove_file) as removes,
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
					patch.object(file_writer, "remove_file", wraps=file_writer.remove_file) as removes,
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
				self.assertEqual(before, {"head": start, "files": {REL: _sha(BEFORE)}})
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
					after, {"commit": state.apply_commit_sha, "branch": "main", "files": {REL: _sha(AFTER)}}
				)
				self.assertEqual(before, {"head": start, "files": {REL: _sha(BEFORE)}})


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
			("app removed", None, app_removed, f"mục 1 ({FILE_PATH}): app không có trong danh sách được sửa"),
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
		# CHG-001 design 4 step 4: the line gains `comment=`.
		self.assertEqual(
			template,
			"erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s comment=%s",
		)
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

		with patch.object(file_writer, "remove_file") as remove:
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
				self.assertEqual(before, {"head": apply_commit, "files": {REL: _sha(AFTER)}})
				restored = None if kind == "new file" else _sha(BEFORE)
				self.assertEqual(
					after, {"commit": state.undo_commit_sha, "branch": "main", "files": {REL: restored}}
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
			# The guard of design 3.2 with a patched secret-name list: `mod.py` is now a secret name.
			patcher = patch.object(source, "TEN_CAM", re.compile(re.escape(os.path.basename(REL))))
			patcher.start()
			return patcher

		# Design 4.4 step 2, one case per row; the switch is not a row (G-1).
		cases = (
			("wrong session user", approver_session, "sai người chạy job"),
			("role lost", role_lost, "người duyệt không còn quyền"),
			("digest edited", digest_edited, "nội dung đề xuất đã bị sửa sau khi duyệt"),
			("guard refusal", guard_refusal, change_guard.NAME_FORBIDDEN),
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
		self.assertEqual(before, {"head": apply_commit, "files": {REL: _sha(AFTER)}})
		restored = None if kind == "new file" else _sha(BEFORE)
		self.assertEqual(after, {"commit": state.undo_commit_sha, "branch": branch, "files": {REL: restored}})

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

	# Design 4.4 steps 4 and 6 (AC-19 for undo, AC-20 refusals, D-2, D-17, design-addendum-3 QĐ-B2, QĐ-B5).

	def fresh_undo(self, kind="changed file"):
		"""A new sandbox, a proposal of `kind` applied, its undo asked; returns (name, apply commit)."""
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		return self.undo_requested(kind)

	def failed(self, *, timed_out=False, output="fatal: lỗi giả"):
		return CommandResult(
			exit_code=None if timed_out else 1,
			output=output,
			duration_ms=3,
			timed_out=timed_out,
			not_found=False,
		)

	def stored(self, name):
		return frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			["change_status", "failure_reason", "undo_commit_sha", "command_output"],
			as_dict=True,
		)

	def file_calls(self):
		"""Spies on every file write and removal and on the undo commit."""
		return (
			patch.object(file_writer, "write_atomic", wraps=file_writer.write_atomic),
			patch.object(file_writer, "remove_file", wraps=file_writer.remove_file),
			patch.object(process_runner, "git_commit_only", wraps=process_runner.git_commit_only),
		)

	def assert_refused_before_writing(self, name, kind, reason, count, calls):
		state = self.stored(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
		self.assertEqual(self.read(self.target(kind)), AFTER)
		self.assertEqual(self.commit_count(), count)
		for call in calls:
			call.assert_not_called()
		self.assertFalse(state.undo_commit_sha)
		self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_refused_when_apply_commit_not_ancestor(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				self.sandbox = GitSandbox(self)
				base = self.sandbox.commit_file(APP, REL, BEFORE)
				name, _ = self.undo_requested(kind)
				# Another branch without the apply commit, whose target has the same bytes (step 3 passes).
				self.sandbox.switch_branch(APP, "other")
				self.sandbox.git(APP, "reset", "--hard", "--quiet", base)
				other_head = self.sandbox.commit_file(APP, self.target(kind), AFTER, message="việc tay")
				count = self.commit_count()

				write, remove, commit = self.file_calls()
				with write as writes, remove as removes, commit as commits:
					apply_job.run_change(name, "undo")

				self.assert_refused_before_writing(
					name, kind, GIT_NOT_ANCESTOR_TEXT, count, (writes, removes, commits)
				)
				self.assertEqual(self.head(), other_head)

	def test_undo_accepted_after_a_human_commit_on_the_same_branch(self):
		# AC-20, ADR-022 decision 6: the apply commit is an ancestor of HEAD, not HEAD itself.
		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)
				human_head = self.sandbox.commit_file(APP, "pkg/manual.py", "y = 1\n", message="việc tay")

				apply_job.run_change(name, "undo")

				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
				self.assert_target_undone(kind)
				self.assertEqual(state.undo_commit_sha, self.head())
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), human_head)
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~2").strip(), apply_commit)

	def test_undo_ancestor_unreadable_fails_with_git_error(self):
		name, apply_commit = self.fresh_undo()
		# HEAD differs from the apply commit, so the order of the two arguments is visible.
		human_head = self.sandbox.commit_file(APP, "pkg/manual.py", "y = 1\n", message="việc tay")
		count = self.commit_count()

		write, remove, commit = self.file_calls()
		with (
			patch.object(source, "git_is_ancestor", return_value=None) as ancestor,
			write as writes,
			remove as removes,
			commit as commits,
		):
			apply_job.run_change(name, "undo")

		ancestor.assert_called_once()
		self.assertEqual(ancestor.call_args.args[1:], (apply_commit, human_head))
		self.assert_refused_before_writing(
			name, "changed file", GIT_ERROR_TEXT, count, (writes, removes, commits)
		)

	def test_undo_refused_on_git_precheck(self):
		cases = (
			("index.lock", lambda: self.sandbox.hold_index_lock(APP), GIT_LOCKED_TEXT),
			("detached", lambda: self.sandbox.detach(APP), GIT_DETACHED_TEXT),
		)
		for kind in self.KINDS:
			for label, break_git, reason in cases:
				with self.subTest(kind=kind, case=label):
					name, apply_commit = self.fresh_undo(kind)
					break_git()
					count = self.commit_count()

					write, remove, commit = self.file_calls()
					with write as writes, remove as removes, commit as commits:
						apply_job.run_change(name, "undo")

					self.assert_refused_before_writing(name, kind, reason, count, (writes, removes, commits))
					self.assertEqual(self.head(), apply_commit)

	def test_undo_commit_failure_restores_applied_bytes(self):
		cases = (
			("commit fails", self.failed(), f"{GIT_COMMIT_FAILED_TEXT}: fatal: lỗi giả"),
			(
				"commit times out",
				self.failed(timed_out=True, output=""),
				f"{GIT_COMMIT_FAILED_TEXT} (quá thời gian)",
			),
		)
		for kind in self.KINDS:
			for label, result, reason in cases:
				with self.subTest(kind=kind, case=label):
					name, apply_commit = self.fresh_undo(kind)
					# HEAD is the bot's apply commit: only "HEAD == old HEAD" may give the file back here.
					self.assertEqual(self.author_email(), BOT_GIT_EMAIL)

					with patch.object(process_runner, "git_commit_only", return_value=result):
						apply_job.run_change(name, "undo")

					state = self.stored(name)
					self.assertEqual(
						(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason)
					)
					with open(self.path(self.target(kind)), "rb") as handle:
						self.assertEqual(handle.read(), AFTER.encode("utf-8"))
					self.assertEqual(self.head(), apply_commit)
					self.assertEqual(self.worktree_changes(), "")
					self.assertFalse(state.undo_commit_sha)
					# The git output is never stored on the proposal (design 3.5).
					self.assertFalse(state.command_output)
					self.assertEqual(self.steps(name), ["approve", "apply", "fail"])
					self.assertNotIn("commit", self.log_row(name, "fail")[1] or {})

	def test_commit_failed_reason_stores_no_path_or_secret(self):
		# NFR-8, AC-13, design addendum 4 QĐ-D1 and QĐ-D2: the apply and the undo commit both store a clean line.
		for action in ("apply", "undo"):
			with self.subTest(action):
				if action == "apply":
					self.sandbox = GitSandbox(self)
					self.sandbox.commit_file(APP, REL, BEFORE)
					frappe.set_user(ACTOR)
					name = self.approved(self.code_proposal())
				else:
					name, _ = self.fresh_undo()
				repo = self.sandbox.repo(APP)
				url = "https://x-token-FAKE@host/r.git"
				email = "real.person@example.com"
				line = f"fatal: {url} {email} {repo}/.git/index.lock"
				output = f"dòng đầu\n{line}\n"
				secrets = (repo, url, "x-token-FAKE", email)
				# The leak check reads a store that would hold them: the stub output carries every one,
				# inside the 120 characters an uncleaned reason keeps.
				self.assertLessEqual(len(line), 120)
				for secret in secrets:
					self.assertIn(secret, output)

				with patch.object(process_runner, "git_commit_only", return_value=self.failed(output=output)):
					apply_job.run_change(name, action)

				state = self.stored(name)
				self.assertEqual(state.change_status, CHANGE_STATUS_FAILED)
				self.assertTrue(state.failure_reason.startswith(f"{GIT_COMMIT_FAILED_TEXT}: fatal: "))
				self.assertFalse(state.command_output)
				errors = frappe.get_all(LOG_DOCTYPE, filters={"change_proposal": name}, pluck="error")
				self.assertIn(state.failure_reason, errors)
				for secret in secrets:
					self.assertNotIn(secret, state.failure_reason)
					for error in errors:
						self.assertNotIn(secret, error or "")

	def test_undo_restore_check_failing_reports_restore_failed(self):
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
		for kind in self.KINDS:
			for label, function, stub in cases:
				with self.subTest(kind=kind, case=label):
					name, _ = self.fresh_undo(kind)

					with (
						patch.object(process_runner, "git_commit_only", return_value=self.failed()),
						patch.object(source, function, side_effect=stub()),
					):
						apply_job.run_change(name, "undo")

					state = self.stored(name)
					self.assertEqual(
						(state.change_status, state.failure_reason),
						(CHANGE_STATUS_FAILED, GIT_RESTORE_FAILED_TEXT),
					)
					self.assertEqual(self.read(self.target(kind)), AFTER)
					self.assertFalse(state.undo_commit_sha)
					self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_commit_failed_and_head_unreadable_fails_without_restore(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)

				write, remove, _ = self.file_calls()
				with (
					patch.object(process_runner, "git_commit_only", return_value=self.failed()),
					patch.object(source, "git_head", return_value=None),
					write as writes,
					remove as removes,
				):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_ERROR_TEXT)
				)
				# QĐ-B2 item 2: the undo commit may exist, so the undone side stays on disk.
				self.assert_target_undone(kind)
				self.assertEqual(writes.call_count, 0 if kind == "new file" else 1)
				self.assertEqual(removes.call_count, 1 if kind == "new file" else 0)
				self.assertEqual(self.head(), apply_commit)
				self.assertFalse(state.undo_commit_sha)
				self.assertNotIn("commit", self.log_row(name, "fail")[1] or {})
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_head_moved_and_summary_unreadable_fails_without_restore(self):
		real_commit = process_runner.git_commit_only

		def commit_then_report_failure(*args):
			real_commit(*args)
			return self.failed()

		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)

				write, remove, _ = self.file_calls()
				with (
					patch.object(process_runner, "git_commit_only", side_effect=commit_then_report_failure),
					patch.object(source, "git_commit_summary", side_effect=RuntimeError("không đọc được")),
					write as writes,
					remove as removes,
				):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, GIT_ERROR_TEXT)
				)
				self.assert_target_undone(kind)
				self.assertEqual(writes.call_count, 0 if kind == "new file" else 1)
				self.assertEqual(removes.call_count, 1 if kind == "new file" else 0)
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), apply_commit)
				self.assertFalse(state.undo_commit_sha)
				self.log_error.assert_not_called()
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_commit_reported_failed_but_head_moved_goes_to_postcheck(self):
		real_commit = process_runner.git_commit_only

		def commit_then_report_failure(*args):
			real_commit(*args)
			return self.failed()

		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)

				write, remove, _ = self.file_calls()
				with (
					patch.object(process_runner, "git_commit_only", side_effect=commit_then_report_failure),
					write as writes,
					remove as removes,
				):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
				self.assert_target_undone(kind)
				self.assertEqual(writes.call_count, 0 if kind == "new file" else 1)
				self.assertEqual(removes.call_count, 1 if kind == "new file" else 0)
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), apply_commit)
				self.assertEqual(state.undo_commit_sha, self.head())
				self.assertEqual(self.author_email(), BOT_GIT_EMAIL)
				self.assertEqual(self.steps(name), ["approve", "apply", "undo"])

	def test_undo_accepted_when_bot_commit_lands_after_human_commit(self):
		real_commit = process_runner.git_commit_only
		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)
				human = []

				def human_commits_first(*args, human=human):
					human.append(
						self.sandbox.commit_file(APP, "pkg/human.py", "h = 1\n", message="việc tay của người")
					)
					return real_commit(*args)

				with patch.object(process_runner, "git_commit_only", side_effect=human_commits_first):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), human[0])
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~2").strip(), apply_commit)
				self.assertEqual(state.undo_commit_sha, self.head())
				self.assert_target_undone(kind)

	def test_fail_row_with_commit_sha_carries_value_after_commit(self):
		cases = (
			("mismatch", {"return_value": b"x = 7\n"}),
			("RuntimeError at post-check", {"side_effect": RuntimeError("không đọc được")}),
		)
		for label, behavior in cases:
			with self.subTest(label):
				name, apply_commit = self.fresh_undo()

				with patch.object(source, "git_blob", **behavior):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual(state.failure_reason, GIT_COMMIT_MISMATCH_TEXT)
				self.assertTrue(state.undo_commit_sha)
				before, after = self.log_row(name, "fail")
				self.assertEqual(
					after, {"commit": state.undo_commit_sha, "branch": "main", "files": {REL: _sha(BEFORE)}}
				)
				self.assertEqual(before, {"head": apply_commit, "files": {REL: _sha(AFTER)}})

	def test_undo_exception_after_commit_landed_does_not_restore(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)

				write, remove, _ = self.file_calls()
				with (
					patch.object(source, "git_blob", side_effect=KeyError("k")),
					write as writes,
					remove as removes,
					patch.object(frappe.db, "rollback"),
				):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "KeyError")
				)
				self.assert_target_undone(kind)
				self.assertEqual(writes.call_count, 0 if kind == "new file" else 1)
				self.assertEqual(removes.call_count, 1 if kind == "new file" else 0)
				self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), apply_commit)
				self.assertEqual(state.undo_commit_sha, self.head())
				before, after = self.log_row(name, "fail")
				self.assertEqual(before, {"head": apply_commit, "files": {REL: _sha(AFTER)}})
				self.assertEqual(after["commit"], state.undo_commit_sha)

	def test_undo_unexpected_exception_after_write_restores_file(self):
		for kind in self.KINDS:
			with self.subTest(kind):
				name, apply_commit = self.fresh_undo(kind)
				self.log_error.reset_mock()

				with (
					patch.object(apply_job, "_person", side_effect=KeyError("k")),
					patch.object(frappe.db, "rollback"),
				):
					apply_job.run_change(name, "undo")

				state = self.stored(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "KeyError")
				)
				self.assertEqual(self.read(self.target(kind)), AFTER)
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(self.head(), apply_commit)
				self.assertFalse(state.undo_commit_sha)
				self.log_error.assert_called_once()
				self.assertEqual(self.steps(name), ["approve", "apply", "fail"])

	def test_undo_read_back_mismatch_gives_the_applied_bytes_back(self):
		name, apply_commit = self.fresh_undo()
		count = self.commit_count()
		real_write = file_writer.write_atomic

		def write_reads_back_other_bytes(path, content, new_file):
			written = real_write(path, content, new_file=new_file)
			return _sha("khác\n") if content == BEFORE else written

		with (
			patch.object(file_writer, "write_atomic", side_effect=write_reads_back_other_bytes) as writes,
			patch.object(process_runner, "git_commit_only") as commit,
		):
			apply_job.run_change(name, "undo")

		state = self.stored(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, "đọc lại sau khi ghi không khớp"),
		)
		commit.assert_not_called()
		self.assertEqual([call.args[1] for call in writes.call_args_list], [BEFORE, AFTER])
		self.assertEqual(self.read(), AFTER)
		self.assertEqual((self.head(), self.commit_count()), (apply_commit, count))
		self.assertEqual(self.worktree_changes(), "")

	def test_undo_postcheck_branch_is_the_checked_out_branch(self):
		# Design 4.4 steps 4 and 6: the undo commits on the branch checked out at undo time when the apply
		# commit is in its history; the post-check compares with that branch, not `target_branch`.
		name, apply_commit = self.fresh_undo()
		self.sandbox.switch_branch(APP, "feature")

		apply_job.run_change(name, "undo")

		state = self.stored(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_UNDONE, None))
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "feature").strip(), state.undo_commit_sha)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "main").strip(), apply_commit)
		self.assertEqual(self.log_row(name, "undo")[1]["branch"], "feature")

	def test_request_undo_refuses_a_command_proposal(self):
		# The undo job has no command branch (`_recheck` reads the guard of a code change only for undo):
		# `request_undo` is what keeps a bench command out of it.
		name = self.approved(
			make_change_proposal(
				CHANGE_KIND_COMMAND, app=APP, command_args=json.dumps(["build", "--app", APP])
			).name
		)

		with self.assertRaises(transitions.InvalidTransition):
			transitions.request_undo(name, UNDOER)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPROVED)
		self.assertFalse(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "undo_by"))


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

	def test_approved_command_runs_once_with_exact_args(self):
		# AC-8, NFR-2: one process for the whole job, the approved arguments after `timeout -s KILL <n> bench`,
		# no shell, in the bench directory, with a timeout; a bench command makes no git call (ADR-022 QĐ 1).
		args = ["--site", frappe.local.site, "migrate"]
		name = self.command_proposal(args)
		done = subprocess.CompletedProcess(args=[], returncode=0, stdout="xong\n")
		with patch("subprocess.run", return_value=done) as run:
			apply_job.run_change(name, "apply")

		self.assertEqual(run.call_count, 1)
		(argv,), kwargs = run.call_args
		self.assertEqual(argv[:3], ["timeout", "-s", "KILL"])
		self.assertTrue(argv[3].isdigit() and 1 <= int(argv[3]) <= COMMAND_TIMEOUT_S, argv[3])
		self.assertEqual(argv[4:], ["bench", *args])
		self.assertFalse(kwargs.get("shell", False))
		self.assertEqual(kwargs["cwd"], frappe.utils.get_bench_path())
		self.assertGreater(kwargs["timeout"], int(argv[3]))
		self.assertIs(kwargs["start_new_session"], True)
		self.assertEqual([call for call in run.call_args_list if "git" in call.args[0]], [])
		state = self.state(name)
		self.assertEqual((state.change_status, state.exit_code), (CHANGE_STATUS_APPLIED, 0))
		self.assertFalse(state.apply_commit_sha)
		self.assertEqual(self.steps(name), ["approve", "apply"])

	def test_nonzero_exit_and_missing_bench_fail(self):
		# Design 4.3 step 4, word for word; every branch stores the exit code, duration and output on the
		# proposal and in the `fail` row's `value_after`.
		for fields, reason, stored_exit_code in (
			({"exit_code": 2, "output": "lỗi"}, "lệnh trả mã 2", 2),
			({"exit_code": 127, "not_found": True, "output": ""}, "không tìm thấy bench trên máy chủ", 127),
			({"exit_code": None, "not_found": True, "output": ""}, "không tìm thấy bench trên máy chủ", 0),
		):
			with self.subTest(reason=reason, exit_code=fields["exit_code"]):
				name = self.command_proposal(["--site", frappe.local.site, "migrate"])
				result = self.result(duration_ms=34, **fields)
				with patch.object(process_runner, "run_bench", return_value=result) as run_bench:
					apply_job.run_change(name, "apply")

				run_bench.assert_called_once()
				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
				stored = frappe.db.get_value(
					PROPOSAL_DOCTYPE, name, ["exit_code", "duration_ms", "command_output"], as_dict=True
				)
				self.assertEqual(
					(stored.exit_code, stored.duration_ms, stored.command_output),
					(stored_exit_code, 34, fields["output"]),
				)
				self.assertEqual(self.steps(name), ["approve", "fail"])
				self.assertEqual(
					self.log_row(name, "fail")[1],
					{"exit_code": fields["exit_code"], "duration_ms": 34, "output": fields["output"]},
				)

	def test_approved_command_tampered_to_denied_is_blocked_at_apply(self):
		# AC-9: an approved command edited into a denied one never runs. Editing only the arguments trips the
		# digest row; editing the digest too still meets the guard (design 4.3 step 4.2).
		denied = ["--site", frappe.local.site, "execute", "frappe.db.truncate"]
		for refresh_digest, reason in (
			(False, "nội dung đề xuất đã bị sửa sau khi duyệt"),
			(True, "lệnh 1: lệnh không có trong danh sách cho phép"),
		):
			with self.subTest(refresh_digest=refresh_digest):
				name = self.command_proposal(["--site", frappe.local.site, "migrate"])
				frappe.db.set_value(PROPOSAL_DOCTYPE, name, "command_args", json.dumps(denied))
				if refresh_digest:
					digest = transitions.content_digest(frappe.get_doc(PROPOSAL_DOCTYPE, name))
					frappe.db.set_value(PROPOSAL_DOCTYPE, name, "approved_digest", digest)
				with patch("subprocess.run") as run:
					apply_job.run_change(name, "apply")

				run.assert_not_called()
				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
				self.assertEqual(self.steps(name), ["approve", "fail"])

	def test_command_without_budget_fails_as_timeout_without_subprocess(self):
		# Design addendum 2 QĐ-A3 and addendum 3 QĐ-B4: under 1 s left → `Lỗi` "quá thời gian", no process,
		# exit code 0 on the proposal (no code) and null in the one `fail` row.
		for left_s in (0.999, -5.0):
			with self.subTest(left_s=left_s):
				name = self.command_proposal(["version"])
				clock = iter([1000.0])
				with (
					patch(
						"time.monotonic", side_effect=lambda: next(clock, 1000.0 + COMMAND_TIMEOUT_S - left_s)
					),
					patch("subprocess.run") as run,
				):
					apply_job.run_change(name, "apply")

				run.assert_not_called()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "quá thời gian")
				)
				stored = frappe.db.get_value(
					PROPOSAL_DOCTYPE, name, ["exit_code", "duration_ms", "command_output"], as_dict=True
				)
				self.assertEqual(
					(stored.exit_code, stored.duration_ms, stored.command_output or ""), (0, 0, "")
				)
				self.assertEqual(self.steps(name), ["approve", "fail"])
				after = self.log_row(name, "fail")[1]
				self.assertIsNone(after["exit_code"])
				self.assertEqual((after["duration_ms"], after["output"]), (0, ""))
				self.log_error.assert_not_called()

	def test_command_budget_of_one_second_runs_with_limit_1(self):
		name = self.command_proposal(["version"])
		clock = iter([1000.0])
		with (
			patch("time.monotonic", side_effect=lambda: next(clock, 1000.0 + COMMAND_TIMEOUT_S - 1.0)),
			patch.object(process_runner, "run_bench", return_value=self.result()) as run_bench,
		):
			apply_job.run_change(name, "apply")

		run_bench.assert_called_once_with(["version"], 1)
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

	def test_command_timeout_fails_with_reason(self):
		# AC-10, design 4.3 step 4 (design.md:627): `timed_out` → `Lỗi` "quá thời gian", checked first, so a
		# result that is also `not_found` or carries a kill exit code still says "quá thời gian". Every branch
		# stores the exit code, duration and output (design.md:632).
		for fields, stored_exit_code in (
			({"exit_code": None}, 0),
			({"exit_code": 137, "output": "đang chạy\n"}, 137),
			({"exit_code": None, "not_found": True}, 0),
		):
			with self.subTest(**fields):
				name = self.command_proposal(["--site", frappe.local.site, "migrate"])
				result = self.result(timed_out=True, duration_ms=540000, **fields)
				with patch.object(process_runner, "run_bench", return_value=result) as run_bench:
					apply_job.run_change(name, "apply")

				run_bench.assert_called_once()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "quá thời gian")
				)
				stored = frappe.db.get_value(
					PROPOSAL_DOCTYPE, name, ["exit_code", "duration_ms", "command_output"], as_dict=True
				)
				self.assertEqual(
					(stored.exit_code, stored.duration_ms, stored.command_output),
					(stored_exit_code, 540000, result.output),
				)
				self.assertEqual(self.steps(name), ["approve", "fail"])
				self.assertEqual(
					self.log_row(name, "fail")[1],
					{"exit_code": result.exit_code, "duration_ms": 540000, "output": result.output},
				)

	def test_limit_passed_is_remaining_budget(self):
		# NFR-3, design 4.3 step 4: `limit = int(deadline - now)`, `deadline` taken when the job starts; the
		# limit reaches `timeout -s KILL <limit> bench` unchanged.
		for elapsed_s, limit in (
			(0.0, COMMAND_TIMEOUT_S),
			(0.5, COMMAND_TIMEOUT_S - 1),
			(123.4, 416),
			(539.0, 1),
		):
			with self.subTest(elapsed_s=elapsed_s):
				name = self.command_proposal(["version"])
				clock = iter([1000.0])
				done = subprocess.CompletedProcess(args=[], returncode=0, stdout="xong\n")
				with (
					patch("time.monotonic", side_effect=lambda: next(clock, 1000.0 + elapsed_s)),
					patch("subprocess.run", return_value=done) as run,
				):
					apply_job.run_change(name, "apply")

				(argv,), _ = run.call_args
				self.assertEqual(argv[1:5], ["-s", "KILL", str(limit), "bench"])
				self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

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

	def test_applying_state_committed_before_subprocess(self):
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


# Design 8.1 (AC-19 c): the six repo hooks the sandbox installs; each one would leave a marker file.
HOOKS_THAT_MUST_NOT_RUN = (
	"pre-commit",
	"prepare-commit-msg",
	"commit-msg",
	"post-commit",
	"post-index-change",
	"reference-transaction",
)
# Design 8.3 (NFR-8): the bot identity as written in the design, not read from the constants.
BOT_AUTHOR = "ERP AI Agent <erp-ai-agent@bot.invalid>"
HOME_EMAIL = "real.person@example.com"
HOME_NAME = "Real Person From Home"
REMOTE_URL = "https://x-token-FAKE@host/r.git"
APPROVER_NAME_EMAIL = "duyet.that@corp.example"
# Review-45: what each planted repo hook prints when it runs.
HOOK_OUTPUT = f"hook-output-T48 {HOME_EMAIL}"


class TestCommitCrossChecks(RealCoreReposUntouchedMixin, ApplyJobTestCase):
	"""Cross checks of the bot commit for apply and undo: hooks, refs, metadata (AC-19 c, AC-23, NFR-7..9, AC-13)."""

	def apply_then_undo(self, name, actor=ACTOR):
		# The job runs as the deciding instructor (ADR-023 decision 2); the session goes back to `ACTOR`.
		frappe.set_user(actor)
		transitions.approve(name, actor)
		apply_job.run_change(name, "apply")
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		transitions.request_undo(name, actor)
		apply_job.run_change(name, "undo")
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		frappe.set_user(ACTOR)
		return name

	def hook_dir(self):
		return os.path.join(self.sandbox.repo(APP), ".git", "hooks")

	def test_repo_hooks_never_run(self):
		markers = self.sandbox.install_marker_hooks(APP)
		for hook in HOOKS_THAT_MUST_NOT_RUN:
			self.assertTrue(os.access(os.path.join(self.hook_dir(), hook), os.X_OK), hook)

		for label, proposal in (("file sửa", self.code_proposal), ("file mới", self.new_file_proposal)):
			with self.subTest(label):
				name = self.apply_then_undo(proposal())
				self.assertEqual(self.steps(name), ["approve", "apply", "undo"])
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(sorted(os.listdir(markers)), [])

		# Control: the same hooks do run for a plain git commit in this repo, so an empty marker dir
		# above means the job switched them off, not that they were broken.
		with self.assertRaises(AssertionError):
			self.sandbox.commit_file(APP, "pkg/control.py", "c = 1\n", run_hooks=True)
		fired = set(os.listdir(markers))
		self.assertIn("pre-commit", fired)
		self.assertLessEqual(fired, set(HOOKS_THAT_MUST_NOT_RUN))

	def test_failure_reason_has_no_hook_output(self):
		# Review-45: a failed commit stores the last line of the git output; a repo hook that ran would print it.
		markers = self.sandbox.install_marker_hooks(APP)
		for hook in HOOKS_THAT_MUST_NOT_RUN:
			path = os.path.join(self.hook_dir(), hook)
			with open(path, encoding="utf-8") as handle:
				script = handle.read()
			with open(path, "w", encoding="utf-8") as handle:
				handle.write(script.replace("#!/bin/sh\n", f'#!/bin/sh\necho "{HOOK_OUTPUT} {hook}"\n', 1))
		# A held branch lock makes git fail the commit at the ref update, after the point where hooks run.
		ref_lock = self.sandbox.git(
			APP, "rev-parse", "--path-format=absolute", "--git-path", "refs/heads/main.lock"
		).strip()

		for action in ("apply", "undo"):
			with self.subTest(action):
				name = self.approved(self.code_proposal())
				if action == "undo":
					apply_job.run_change(name, "apply")
					self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
					transitions.request_undo(name, ACTOR)
				content, head = self.read(), self.head()
				with open(ref_lock, "w", encoding="utf-8"):
					pass
				try:
					apply_job.run_change(name, action)
				finally:
					os.remove(ref_lock)

				state = self.state(name)
				self.assertEqual(state.change_status, CHANGE_STATUS_FAILED)
				self.assertTrue(
					state.failure_reason.startswith(f"{GIT_COMMIT_FAILED_TEXT}: "), state.failure_reason
				)
				self.assertNotIn(HOOK_OUTPUT, state.failure_reason)
				self.assertNotIn("hook-output-T48", state.failure_reason)
				self.assertNotIn(HOME_EMAIL, state.failure_reason)
				self.assertEqual((self.read(), self.head(), self.worktree_changes()), (content, head, ""))
				self.assertEqual(sorted(os.listdir(markers)), [])

		# Control: the job made to run the repo hooks puts their output in `failure_reason` (a new file:
		# the failed undo above left `REL` applied).
		name = self.approved(self.new_file_proposal())
		with patch.object(source, "GIT_HOOKS_DIR", self.hook_dir()):
			apply_job.run_change(name, "apply")
		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_FAILED)
		self.assertIn(f"hook-output-T48 {apply_job.GIT_MASKED_WORD} pre-commit", state.failure_reason)
		self.assertIn("pre-commit", os.listdir(markers))

	def test_remote_refs_and_other_branches_unchanged_after_apply_and_undo(self):
		self.sandbox.add_remote(APP, url=REMOTE_URL)
		# A push to `origin` would land in the temp bare repo; fetch keeps the fake URL of the leak checks.
		bare = self.sandbox.remote_dir(APP)
		self.sandbox.git(APP, "remote", "set-url", "--push", "origin", bare)
		self.assertEqual(self.sandbox.git(APP, "remote", "get-url", "--push", "origin").strip(), bare)
		self.assertEqual(self.sandbox.git(APP, "remote", "get-url", "origin").strip(), REMOTE_URL)
		self.sandbox.switch_branch(APP, "other")
		self.sandbox.commit_file(APP, "pkg/other_branch.py", "o = 1\n")
		self.sandbox.switch_branch(APP, "main", create=False)
		self.sandbox.git(APP, "tag", "v1")

		def other_refs():
			refs = self.sandbox.refs(APP)
			main = refs.pop("refs/heads/main")
			return main, refs

		def remote_refs():
			return self.sandbox.git(APP, "ls-remote", bare)

		main_before, refs_before = other_refs()
		remote_before = remote_refs()
		self.assertEqual(set(refs_before), {"refs/heads/other", "refs/remotes/origin/main", "refs/tags/v1"})
		self.assertIn("refs/heads/main", remote_before)
		name = self.approved(self.code_proposal(upstream_ref="origin/main"))

		apply_job.run_change(name, "apply")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		main_applied, refs_applied = other_refs()
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "main~1").strip(), main_before)
		self.assertEqual(refs_applied, refs_before)
		self.assertEqual(remote_refs(), remote_before)

		transitions.request_undo(name, ACTOR)
		apply_job.run_change(name, "undo")

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		_, refs_undone = other_refs()
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "main~1").strip(), main_applied)
		self.assertEqual(refs_undone, refs_before)
		self.assertEqual(remote_refs(), remote_before)

	def test_commit_metadata_has_no_email_url_or_token(self):
		home = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, home, True)
		with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as handle:
			handle.write(f"[user]\n\temail = {HOME_EMAIL}\n\tname = {HOME_NAME}\n")
		environ = patch.dict(os.environ, {"HOME": home, "XDG_CONFIG_HOME": home, "EMAIL": HOME_EMAIL})
		environ.start()
		self.addCleanup(environ.stop)
		self.sandbox.add_remote(APP, url=REMOTE_URL)
		self.add_proposer()
		frappe.set_user("Administrator")
		approver = f"erp-ai-t48-{frappe.generate_hash(length=8)}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": approver,
				"first_name": f"Duyệt {APPROVER_NAME_EMAIL}",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True).add_roles(ROLE_INSTRUCTOR)
		ticket = str(make_ticket(subject="ERPAI-TEST T48 metadata", raised_by=PROPOSER).name)
		# A `.py` file needs a restart command the tool does not take yet (design 3.2 step 4): a text file.
		text_rel = "pkg/mod.txt"
		self.sandbox.commit_file(APP, text_rel, BEFORE)
		# The proposal comes from the propose tool, which writes its own ticket comment (design 3.8, 3.9).
		frappe.set_user(PROPOSER)
		result = execute_tool(
			"propose_file_change",
			{
				"path": f"{APP}/{text_rel}",
				"find": ["x = 1"],
				"replace": ["x = 2"],
				"reason": "sửa theo yêu cầu",
			},
			self.tool_context(ticket, "run-t48"),
		)
		frappe.set_user(ACTOR)
		self.assertTrue(result["ok"], result)
		name = result["proposal"]
		self.assertEqual(frappe.db.get_value(PROPOSAL_DOCTYPE, name, "upstream_ref"), "origin/main")
		# The tool makes a block proposal; undoing a block is T39, so the apply and undo run on a file
		# proposal of the old form for the same file and content, on the same ticket.
		legacy = self.code_proposal(
			file_path=f"{APP}/{text_rel}",
			ticket=ticket,
			upstream_ref="origin/main",
			reason="sửa theo yêu cầu",
		)

		self.apply_then_undo(legacy, actor=approver)

		state = self.state(legacy)
		commits = {"apply": state.apply_commit_sha, "undo": state.undo_commit_sha}
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD~1").strip(), commits["apply"])
		self.assertEqual(self.head(), commits["undo"])
		people = {"apply": "Người duyệt: (không hiện tên)", "undo": "Người hoàn tác: (không hiện tên)"}
		for action, commit in commits.items():
			with self.subTest(action):
				meta = self.sandbox.log_meta(APP, commit)
				author_name, author_email, committer_name, committer_email, message = meta.split("\n", 4)
				self.assertEqual(f"{author_name} <{author_email}>", BOT_AUTHOR)
				self.assertEqual(f"{committer_name} <{committer_email}>", BOT_AUTHOR)
				self.assertIn(people[action], message)
				for leak in ("@", "://", "x-token-FAKE", "host/r.git", HOME_NAME):
					self.assertNotIn(leak, message)
				for leak in (HOME_EMAIL, HOME_NAME, approver, APPROVER_NAME_EMAIL, "x-token-FAKE"):
					self.assertNotIn(leak, meta)

		doc = frappe.get_doc(PROPOSAL_DOCTYPE, legacy)
		doc.run_method("onload")
		notes = json.dumps(doc.get("__onload"), ensure_ascii=False, default=str)
		self.assertIn("origin/main", notes)
		fields = json.dumps(doc.as_dict(), ensure_ascii=False, default=str)
		self.assertIn(commits["apply"], fields)
		# The store is not empty: the proposal comment with its notes is read below.
		ticket_comments = frappe.get_all(
			"Comment", filters=authority.ticket_comment_filters(ticket), pluck="content"
		)
		self.assertEqual(len(ticket_comments), 1, ticket_comments)
		self.assertIn(name, ticket_comments[0])
		self.assertIn("Nhánh này theo origin/main", ticket_comments[0])
		comments = json.dumps(
			frappe.get_all(
				"Comment",
				filters={"reference_name": ("in", [name, legacy, doc.ticket])},
				fields=["content", "subject"],
			)
			+ frappe.get_all(
				"HD Ticket Comment", filters={"reference_ticket": doc.ticket}, fields=["content"]
			)
			+ frappe.get_all(
				LOG_DOCTYPE,
				filters={"change_proposal": ("in", [name, legacy])},
				fields=["value_before", "value_after", "error"],
			),
			ensure_ascii=False,
			default=str,
		)
		for where, text in (("__onload", notes), ("trường đề xuất", fields), ("comment và log", comments)):
			for leak in (HOME_EMAIL, HOME_NAME, APPROVER_NAME_EMAIL, "x-token-FAKE", "host/r.git", "://"):
				with self.subTest(where=where, leak=leak):
					self.assertNotIn(leak, text)


class TestNoKeyLeak(ApplyJobTestCase):
	"""AC-13, NFR-5: a fake key in `os.environ` and in the stored credential never reaches a store of the flow."""

	def setUp(self):
		super().setUp()
		environ = patch.dict(os.environ, {"ANTHROPIC_API_KEY": FAKE_KEY, "ERP_AI_FAKE_SECRET": FAKE_KEY})
		environ.start()
		self.addCleanup(environ.stop)
		self.add_proposer()
		frappe.set_user("Administrator")
		add_credential("t22-leak", api_key=FAKE_KEY)
		frappe.set_user(ACTOR)

	def run_flow(self) -> dict:
		"""Propose a file change and a bench command with the tools, approve and apply both, undo the file
		change; returns each store as text, after proving that each one holds what the flow wrote.

		`subprocess.run` is spied on: git runs for real in the sandbox, bench is a stub that prints the `env`
		it was given as its output, so a key in that `env` lands in the proposal and its log rows.
		"""
		frappe.set_user("Administrator")
		ticket = str(make_ticket(subject="ERPAI-TEST T22 leak", raised_by=PROPOSER).name)
		context = self.tool_context(ticket, "run-t22")
		# A `.py` file needs a restart command the tool does not take yet (design 3.2 step 4): a text file.
		text_rel = "pkg/mod.txt"
		if not os.path.lexists(self.path(text_rel)):
			self.sandbox.commit_file(APP, text_rel, BEFORE)
		base = self.head()
		calls = []
		real_run = subprocess.run

		def spy(argv, *args, **kwargs):
			env = kwargs.get("env") or {}
			calls.append(("bench" if "bench" in argv else "git", list(argv), env))
			if "bench" in argv:
				printed = "".join(f"{key}={value}\n" for key, value in sorted(env.items()))
				return subprocess.CompletedProcess(args=argv, returncode=0, stdout=printed)
			return real_run(argv, *args, **kwargs)

		with patch("subprocess.run", side_effect=spy):
			frappe.set_user(PROPOSER)
			results = [
				execute_tool(
					"propose_file_change",
					{
						"path": f"{APP}/{text_rel}",
						"find": ["x = 1"],
						"replace": ["x = 2"],
						"reason": "sửa theo yêu cầu",
					},
					context,
				),
				execute_tool(
					"propose_bench_command", {"command": "version", "reason": "xem phiên bản"}, context
				),
			]
			frappe.set_user(ACTOR)
			self.assertEqual([result["ok"] for result in results], [True, True], results)
			code, command = (result["proposal"] for result in results)
			# The tool makes a block proposal; undoing a block is T39, so the apply and undo run on a file
			# proposal of the old form for the same file, content and branch (read by the tool), on the same ticket.
			legacy = self.code_proposal(
				file_path=f"{APP}/{text_rel}",
				ticket=ticket,
				reason="sửa theo yêu cầu",
				target_branch=frappe.db.get_value(PROPOSAL_DOCTYPE, code, "target_branch"),
			)
			for name in (legacy, command):
				transitions.approve(name, ACTOR)
				apply_job.run_change(name, "apply")
			transitions.request_undo(legacy, ACTOR)
			apply_job.run_change(legacy, "undo")

		names = [legacy, command]
		self.assertEqual(
			[self.state(name).change_status for name in names], [CHANGE_STATUS_UNDONE, CHANGE_STATUS_APPLIED]
		)
		proposals = [frappe.get_doc(PROPOSAL_DOCTYPE, name).as_dict() for name in [*names, code]]
		logs = frappe.get_all(LOG_DOCTYPE, filters={"change_proposal": ["in", names]}, fields=["*"])
		comments = frappe.get_all(
			"Comment", filters=authority.ticket_comment_filters(ticket), pluck="content"
		)
		commits = self.sandbox.git(APP, "log", "--format=%an%ae%cn%ce%B", f"{base}..HEAD")
		bench_envs = [env for kind, _argv, env in calls if kind == "bench"]
		git_envs = [env for kind, _argv, env in calls if kind == "git"]
		git_writes = [argv for kind, argv, _env in calls if kind == "git" and "commit" in argv]
		# Each store is not empty: a "0 occurrences" below reads real content.
		self.assertIn("PATH=", proposals[1]["command_output"])
		self.assertEqual(len(logs), 5, logs)
		self.assertEqual(len(comments), 2, comments)
		self.assertEqual(int(self.sandbox.git(APP, "rev-list", "--count", f"{base}..HEAD")), 2)
		self.assertEqual(commits.count(BOT_GIT_EMAIL), 4, commits)
		self.assertEqual(len(bench_envs), 1)
		self.assertEqual(len(git_writes), 2, git_writes)
		self.assertTrue(all(env.get("GIT_CONFIG_GLOBAL") == "/dev/null" for env in git_envs), git_envs)

		def text(value):
			return json.dumps(value, ensure_ascii=False, default=str)

		return {
			"tool_result": text(results),
			"proposal": text(proposals),
			"log": text(logs),
			"comment": text(comments),
			"commit": commits,
			"bench_env": text(bench_envs),
			"git_env": text(git_envs),
		}

	def leaks(self, stores) -> set:
		return {store for store, content in stores.items() if FAKE_KEY in content}

	def test_fake_key_never_in_proposal_result_log_comment(self):
		self.assertEqual(self.leaks(self.run_flow()), set())

		# The same check goes red when the key is leaked on purpose into each store.
		real_git_env = source.git_env

		def git_env_with_key(**kwargs):
			identity = {"GIT_COMMITTER_NAME": FAKE_KEY} if kwargs["identity"] else {}
			return {**real_git_env(**kwargs), "ERP_AI_FAKE_SECRET": FAKE_KEY, **identity}

		planted = (
			(
				"bench env",
				patch.object(process_runner, "_minimal_env", return_value=dict(os.environ)),
				{"bench_env", "proposal", "log"},
			),
			("git env", patch.object(source, "git_env", side_effect=git_env_with_key), {"git_env", "commit"}),
			(
				"comment",
				patch.object(change_text, "proposal_notes", return_value=[f"ghi chú {FAKE_KEY}"]),
				{"comment"},
			),
		)
		for label, leak, stores in planted:
			with self.subTest(leak=label), leak:
				leaked = self.leaks(self.run_flow())
				self.assertTrue(stores <= leaked, (stores, leaked))
		# Last: the branch name stays checked out and ends in the tool result, the proposal and the log.
		with self.subTest(leak="branch"):
			self.sandbox.switch_branch(APP, f"leak/{FAKE_KEY}")
			leaked = self.leaks(self.run_flow())
			self.assertTrue({"tool_result", "proposal", "log"} <= leaked, leaked)


class TestActorRecheckAndLock(ApplyJobTestCase):
	"""ADR-023 decision 2 (M2), ADR-012 decision 7, NFR-6: the job itself refuses the actor and a busy lock.

	The role-lost and other-session-user rows are pinned by `test_rechecks_fail_without_writing` (apply) and
	`test_undo_rechecks_fail_without_writing` (undo).
	"""

	ACTOR_REFUSED_TEXT = "người duyệt không còn quyền"
	LOCK_BUSY_TEXT = "đang có thay đổi khác chạy, không lấy được khóa"

	def read_bytes(self, rel=REL):
		with open(self.path(rel), "rb") as handle:
			return handle.read()

	def agent_holds_instructor_role(self):
		"""Give the agent account `ERP AI Instructor` for this test only, as it holds it on the site today."""
		frappe.set_user("Administrator")
		pin_agent_roles(self)
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": AGENT_USER,
				"parenttype": "User",
				"parentfield": "roles",
				"role": ROLE_INSTRUCTOR,
			}
		).db_insert()
		frappe.clear_cache(user=AGENT_USER)
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles(AGENT_USER))

	def test_apply_refused_when_decider_is_agent_account_even_with_role(self):
		# The agent account holds the role and is the job's session user: only `NEVER_AUTHORITY` can refuse.
		self.agent_holds_instructor_role()
		for action in ("apply", "undo"):
			with self.subTest(action):
				self.sandbox = GitSandbox(self)
				self.sandbox.commit_file(APP, REL, BEFORE)
				frappe.set_user(ACTOR)
				name = self.code_proposal()
				if action == "apply":
					transitions.approve(name, AGENT_USER)
					steps = ["approve", "fail"]
				else:
					apply_job.run_change(self.approved(name), "apply")
					self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
					transitions.request_undo(name, AGENT_USER)
					steps = ["approve", "apply", "fail"]
				content, head = self.read_bytes(), self.head()
				frappe.set_user(AGENT_USER)

				apply_job.run_change(name, action)

				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, self.ACTOR_REFUSED_TEXT),
				)
				self.assertEqual(self.read_bytes(), content)
				self.assertEqual(self.head(), head)
				self.assertEqual(self.worktree_changes(), "")
				self.assertEqual(self.steps(name), steps)

	def test_lock_timeout_fails_with_reason_one_log_row_zero_subprocess(self):
		# A file change and a bench command waiting in `Đã duyệt`, then a file change waiting in `Đang hoàn tác`.
		for label in ("code apply", "command apply", "undo"):
			with self.subTest(label):
				frappe.set_user(ACTOR)
				if label == "command apply":
					command = make_change_proposal(
						CHANGE_KIND_COMMAND, app=APP, command_args=json.dumps(["build", "--app", APP])
					)
					name = self.approved(command.name)
				else:
					name = self.approved(self.code_proposal())
				action, waiting, steps = "apply", CHANGE_STATUS_APPROVED, ["approve", "fail"]
				if label == "undo":
					apply_job.run_change(name, "apply")
					transitions.request_undo(name, ACTOR)
					action, waiting, steps = "undo", CHANGE_STATUS_UNDOING, ["approve", "apply", "fail"]
				self.assertEqual(self.state(name).change_status, waiting)
				content, head = self.read_bytes(), self.head()

				with (
					patch.object(
						apply_job, "filelock", side_effect=LockTimeoutError(apply_job.LOCK_NAME)
					) as lock,
					patch("subprocess.Popen", wraps=subprocess.Popen) as popen,
				):
					apply_job.run_change(name, action)

				lock.assert_called_once()
				popen.assert_not_called()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, self.LOCK_BUSY_TEXT)
				)
				self.assertEqual(self.steps(name), steps)
				self.assertEqual(self.read_bytes(), content)
				self.assertEqual(self.head(), head)


class TestResultComment(ApplyJobTestCase):
	"""AC-28, CHG-001 design 4 and 8: after every outcome the job writes one `Info` result line on the ticket."""

	def info_rows(self, name):
		ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "HD Ticket", "reference_name": ticket, "comment_type": "Info"},
			fields=["name", "content", "owner"],
			order_by="creation asc",
		)

	def fresh_repo(self):
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)

	def run_job(self, name, action, post_result=None):
		"""Run the job with its log line, rollback and `post_result` watched; returns what the checks read.

		`post_result` replaces the real writer when given; `commits_at_post` is the commit count when it is called,
		`last_commit_at_post` the `(count, change_status)` the job's last commit saw before that call (None: no commit).
		"""
		real_post_result = result_comment.post_result
		commits = []
		seen = {"commits_at_post": None, "last_commit_at_post": None}

		def commit():
			# The commit is mocked, so what it would make durable is the status the job holds when it is called.
			commits.append(
				(frappe.db.commit.call_count, frappe.db.get_value(PROPOSAL_DOCTYPE, name, "change_status"))
			)

		def post(proposal_name):
			seen["commits_at_post"] = frappe.db.commit.call_count
			seen["last_commit_at_post"] = commits[-1] if commits else None
			return (post_result or real_post_result)(proposal_name)

		frappe.db.commit.side_effect = commit
		try:
			with (
				patch.object(frappe, "logger") as logger,
				patch.object(frappe.db, "rollback") as rollback,
				patch.object(result_comment, "post_result", side_effect=post) as posted,
			):
				apply_job.run_change(name, action)
		finally:
			frappe.db.commit.side_effect = None

		lines = [
			call.args
			for call in logger.return_value.info.call_args_list
			if call.args and call.args[0].startswith("erp_ai change ")
		]
		self.assertEqual(len(lines), 1, lines)
		self.assertTrue(lines[0][0].endswith(" comment=%s"), lines[0][0])
		return {
			"comment": lines[0][-1],
			"posted": posted,
			"rollback": rollback,
			"commits_at_post": seen["commits_at_post"],
			"last_commit_at_post": seen["last_commit_at_post"],
			"commits_after": frappe.db.commit.call_count,
		}

	def test_one_result_comment_per_outcome(self):
		def apply_code():
			return self.approved(self.code_proposal()), "apply", contextlib.nullcontext()

		def command_exit_2():
			name = make_change_proposal(
				CHANGE_KIND_COMMAND, app=APP, command_args=json.dumps(["build", "--app", APP])
			).name
			failed = CommandResult(exit_code=2, output="lỗi", duration_ms=5, timed_out=False, not_found=False)
			return (
				self.approved(name),
				"apply",
				patch.object(process_runner, "run_bench", return_value=failed),
			)

		def branch_changed():
			name = self.approved(self.code_proposal())
			self.sandbox.switch_branch(APP, "other")
			return name, "apply", contextlib.nullcontext()

		def undo():
			name = self.approved(self.code_proposal())
			apply_job.run_change(name, "apply")
			transitions.request_undo(name, ACTOR)
			return name, "undo", contextlib.nullcontext()

		def lock_timeout():
			busy = patch.object(apply_job, "filelock", side_effect=LockTimeoutError(apply_job.LOCK_NAME))
			return self.approved(self.code_proposal()), "apply", busy

		def wrong_runner():
			name = self.approved(self.code_proposal())
			frappe.set_user("Administrator")
			return name, "apply", contextlib.nullcontext()

		# Final status and reason of each outcome; the reasons are written out as in design 4.3 (not read from the
		# constants), the statuses are the `CHANGE_STATUS_*` values.
		cases = (
			("apply code", apply_code, CHANGE_STATUS_APPLIED, None),
			("command exit 2", command_exit_2, CHANGE_STATUS_FAILED, "lệnh trả mã 2"),
			(
				"branch changed",
				branch_changed,
				CHANGE_STATUS_STALE,
				"nhánh đang checkout đã đổi kể từ lúc đề xuất",
			),
			("undo", undo, CHANGE_STATUS_UNDONE, None),
			(
				"lock timeout",
				lock_timeout,
				CHANGE_STATUS_FAILED,
				"đang có thay đổi khác chạy, không lấy được khóa",
			),
			("wrong runner", wrong_runner, CHANGE_STATUS_FAILED, "sai người chạy job"),
		)
		for label, prepare, status, reason in cases:
			with self.subTest(label):
				# Each case starts from a fresh repo on `main` and the approver's session.
				self.fresh_repo()
				frappe.set_user(ACTOR)
				name, action, context = prepare()
				runner = frappe.session.user
				before = {row.name for row in self.info_rows(name)}

				with context:
					run = self.run_job(name, action)
				frappe.set_user(ACTOR)

				state = self.state(name)
				self.assertEqual((state.change_status, state.failure_reason), (status, reason))
				new_rows = [row for row in self.info_rows(name) if row.name not in before]
				self.assertEqual(len(new_rows), 1, new_rows)
				row = new_rows[0]
				self.assertEqual(row.owner, runner)
				self.assertIn(f"kết quả đề xuất {name} ", row.content)
				self.assertIn(f": {status}", row.content)
				run["posted"].assert_called_once_with(name)
				self.assertEqual(run["comment"], row.name)
				# The final status is committed before the line is written (design 4 step 3): the job's last commit
				# before `post_result` saw it.
				self.assertEqual(run["last_commit_at_post"], (run["commits_at_post"], status))
				# The line is committed on its own, after the final status (design 4 step 2), never rolled back.
				self.assertEqual(run["commits_after"], run["commits_at_post"] + 1)
				run["rollback"].assert_not_called()

	def test_skipped_job_posts_nothing(self):
		applied = self.approved(self.code_proposal())
		apply_job.run_change(applied, "apply")
		self.assertEqual(self.state(applied).change_status, CHANGE_STATUS_APPLIED)
		pending = self.code_proposal()
		for label, name, action in (
			("repeated apply", applied, "apply"),
			("never approved", pending, "apply"),
			("undo never requested", applied, "undo"),
		):
			with self.subTest(label):
				status, before = self.state(name).change_status, self.info_rows(name)

				run = self.run_job(name, action)

				self.assertEqual(self.state(name).change_status, status)
				self.assertEqual(self.info_rows(name), before)
				run["posted"].assert_not_called()
				self.assertEqual(run["comment"], "-")

		# The other `comment=-` branch: the writer found nothing to write on and returned None.
		with self.subTest("nothing written"):
			self.fresh_repo()
			name = self.approved(self.code_proposal())

			run = self.run_job(name, "apply", post_result=lambda proposal_name: None)

			self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
			run["posted"].assert_called_once_with(name)
			self.assertEqual(run["comment"], "-")

	def test_comment_failure_keeps_final_status_and_logs(self):
		def failing_post(proposal_name):
			raise RuntimeError("bí mật https://x-token-FAKE@host/r.git")

		title = result_comment.TITLE_RESULT_COMMENT_FAILED
		for label, action, status in (
			("apply", "apply", CHANGE_STATUS_APPLIED),
			("undo", "undo", CHANGE_STATUS_UNDONE),
			("lock timeout", "apply", CHANGE_STATUS_FAILED),
		):
			with self.subTest(label):
				self.fresh_repo()
				name = self.approved(self.code_proposal())
				if label == "undo":
					apply_job.run_change(name, "apply")
					transitions.request_undo(name, ACTOR)
				busy = contextlib.nullcontext()
				if label == "lock timeout":
					busy = patch.object(
						apply_job, "filelock", side_effect=LockTimeoutError(apply_job.LOCK_NAME)
					)
				before = {row.name for row in self.info_rows(name)}
				logged_before = frappe.get_all("Error Log", filters={"method": title}, pluck="name")

				# The real `Error Log` is written here; the job's rollback is mocked, as its commits are.
				with busy, patch.object(frappe, "log_error", side_effect=real_log_error):
					run = self.run_job(name, action, post_result=failing_post)

				self.assertEqual(self.state(name).change_status, status)
				self.assertEqual(run["comment"], "error")
				run["rollback"].assert_called_once_with()
				# The rollback only loses the line: the final status was committed before `post_result` ran.
				self.assertEqual(run["last_commit_at_post"], (run["commits_at_post"], status))
				self.assertEqual(run["commits_after"], run["commits_at_post"])
				logged = frappe.get_all(
					"Error Log",
					filters={"method": title, "name": ("not in", logged_before or [""])},
					pluck="error",
				)
				self.assertEqual(logged, [f"proposal={name} action={action} error=RuntimeError"])
				self.assertEqual([row for row in self.info_rows(name) if row.name not in before], [])

	def test_result_comment_has_no_remote_url_or_fake_token(self):
		self.sandbox.add_remote(APP, url=REMOTE_URL)
		name = self.approved(self.code_proposal(upstream_ref="origin/main"))
		apply_job.run_change(name, "apply")
		transitions.request_undo(name, ACTOR)
		apply_job.run_change(name, "undo")
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_UNDONE)
		# A failure reason that carries the remote URL with its fake token reaches the proposal as is.
		busy = self.approved(self.code_proposal(upstream_ref="origin/main"))
		with (
			patch.object(apply_job, "LOCK_BUSY", f"không fetch được {REMOTE_URL}"),
			patch.object(apply_job, "filelock", side_effect=LockTimeoutError(apply_job.LOCK_NAME)),
		):
			apply_job.run_change(busy, "apply")
		self.assertIn(REMOTE_URL, self.state(busy).failure_reason)

		stored = [row.content for proposal in (name, busy) for row in self.info_rows(proposal)]
		self.assertEqual(len(stored), 3, stored)
		for leak in ("://", "x-token-FAKE", "host/r.git", "@"):
			with self.subTest(leak=leak):
				self.assertNotIn(leak, " ".join(stored))
