import dataclasses
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
from erp_ai.agent.tools import source
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


class TestApplyCodeSteps(ApplyJobTestCase):
	"""Design 4.3 step 4.3 items 1 to 5 and 7 (ADR-022 decision 1, D-19, design-addendum-3 QĐ-B2 and QĐ-B5)."""

	def log_row(self, name, step):
		row = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name, "change_step": step},
			fields=["value_before", "value_after"],
		)[0]
		return json.loads(row.value_before or "null"), json.loads(row.value_after or "null")

	def author_email(self):
		return self.sandbox.git(APP, "log", "-1", "--format=%ae").strip()

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
