import hashlib
import json
import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.synchronization import filelock
from helpdesk.test_utils import create_agent

from erp_ai.agent import policy
from erp_ai.agent.changes import apply_job, file_writer, process_runner, transitions
from erp_ai.agent.changes.process_runner import CommandResult
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
from erp_ai.test_utils import GitSandbox, make_change_proposal, set_agent_settings

APP = "custom_app"
REL = "pkg/mod.py"
FILE_PATH = f"{APP}/{REL}"
NEW_REL = "pkg/new_mod.py"
BEFORE = "x = 1\n# Tiếng Việt\n"
AFTER = "x = 2\n# Tiếng Việt\n"
ACTOR = "apply.instructor@example.com"


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

	def test_apply_leaves_other_dirty_files_out_of_the_commit(self):
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
		self.assertEqual(state.failure_reason, "file đã đổi từ lúc đề xuất")
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

	def test_branch_changed_since_proposal_is_stale(self):
		name = self.approved(self.code_proposal())
		self.sandbox.git(APP, "checkout", "--quiet", "-b", "other")

		apply_job.run_change(name, "apply")

		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_STALE, "nhánh đang checkout đã đổi từ lúc đề xuất"),
		)
		self.assertEqual(self.read(), BEFORE)

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
		self.assertEqual(state.failure_reason, "git commit lỗi, file đã được trả lại như cũ")
		self.assertEqual(self.read(), BEFORE)
		self.assertEqual(self.worktree_changes(), "")
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
		self.assertEqual(state.failure_reason, "file đã đổi sau khi áp dụng, không hoàn tác tự động được")
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
