import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import authority, queue
from erp_ai.agent.changes import apply_job, process_runner, transitions
from erp_ai.agent.tools import change_guard, source
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_STALE,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
from erp_ai.test_utils import (
	GitSandbox,
	make_block_proposal,
	make_change_proposal,
	pin_agent_roles,
	set_agent_settings,
)

APP = "custom_app"
REL = "pkg/mod.txt"
FILE_PATH = f"{APP}/{REL}"
BEFORE = "x = 1\n# Tiếng Việt\ny = 1\n"
AFTER = "x = 2\n# Tiếng Việt\ny = 1\n"
ACTOR = "block.instructor@example.com"
# Design 2.1, written by hand so a changed constant cannot hide a changed name.
OPERATION_DOCTYPE_NAME = "ERP AI Change Operation"
OPERATION_EDIT = "Sửa"


def _sha(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestWalkingSkeleton(FrappeTestCase):
	"""CHG-002 T1 (AC-36 frame): one block with one `edit` item goes from the tool to one commit."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		pin_agent_roles(self)
		# The job commits its state; inside a test nothing may reach the real database for good.
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(ACTOR)
		frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		set_agent_settings(code_change_enabled=1, code_change_apps=APP)
		self.ticket = str(make_ticket(subject="ERPAI-TEST CHG-002 T1", raised_by=ACTOR).name)

	def context(self):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L3",
			instructor=ACTOR,
			run_id="run-chg002-t1",
			category_mapping={},
			agent_user=AGENT_USER,
			change_enabled=True,
			allowed_apps=(APP,),
		)

	def git(self, *args):
		return self.sandbox.git(APP, *args).strip()

	def test_one_edit_block_proposed_approved_applied_one_commit(self):
		head_before = self.git("rev-parse", "HEAD")
		frappe.set_user(AGENT_USER)
		result = execute_tool(
			"propose_file_change",
			{
				"changes": [{"action": "edit", "path": FILE_PATH, "find": ["x = 1"], "replace": ["x = 2"]}],
				"reason": "sửa theo yêu cầu",
			},
			self.context(),
		)
		frappe.set_user("Administrator")

		self.assertTrue(result.get("ok"), result)
		self.assertEqual(result["status"], CHANGE_STATUS_PENDING)
		self.assertEqual(result["branch"], "main")
		name = result["proposal"]
		self.assertEqual(frappe.db.count(PROPOSAL_DOCTYPE, {"ticket": self.ticket}), 1)
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, name)
		self.assertEqual(
			(doc.change_status, doc.change_kind, doc.app), (CHANGE_STATUS_PENDING, CHANGE_KIND_CODE, APP)
		)
		for fieldname in ("file_path", "content_before", "content_after", "base_hash", "after_hash"):
			self.assertFalse(doc.get(fieldname), fieldname)
		self.assertEqual(len(doc.operations), 1)
		row = doc.operations[0]
		self.assertEqual(row.doctype, OPERATION_DOCTYPE_NAME)
		self.assertEqual(
			(row.operation, row.file_path, row.new_path or "", row.content_before, row.content_after),
			(OPERATION_EDIT, FILE_PATH, "", BEFORE, AFTER),
		)
		self.assertEqual((row.base_hash, row.after_hash), (_sha(BEFORE), _sha(AFTER)))
		self.assertIn(f"({FILE_PATH})", doc.commit_message)
		comments = frappe.get_all(
			"Comment", filters=authority.ticket_comment_filters(self.ticket), pluck="content"
		)
		self.assertEqual(len(comments), 1, comments)
		self.assertIn(name, comments[0])
		self.assertIn(FILE_PATH, comments[0])
		# Nothing is written before the approval.
		self.assertEqual(self.git("rev-parse", "HEAD"), head_before)

		frappe.set_user(ACTOR)
		with patch.object(queue, "enqueue_change_job") as enqueue:
			self.assertEqual(controller.approve(name), {"name": name, "status": CHANGE_STATUS_APPROVED})
		enqueue.assert_called_once_with(name, "apply")
		apply_job.run_change(name, "apply")

		state = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason", "apply_commit_sha"], as_dict=True
		)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
		with open(f"{self.sandbox.repo(APP)}/{REL}", "rb") as handle:
			self.assertEqual(handle.read(), AFTER.encode("utf-8"))
		self.assertEqual(self.git("rev-parse", "HEAD"), state.apply_commit_sha)
		self.assertEqual(self.git("rev-parse", "HEAD~1"), head_before)
		self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), REL)
		self.assertEqual(self.git("status", "--porcelain"), "")


# Text files that need no restart (design 3.2 step 4), so a block of them passes the guard without commands.
TEXT_RELS = ("docs/a.txt", "docs/b.txt", "docs/c.txt")
TEXT_BEFORE = "dòng một\n"
TEXT_AFTER = "dòng hai\n"
LEGACY_REL = "pkg/legacy.py"


class BlockApplyTestCase(FrappeTestCase):
	"""A sandbox app with three committed text files and one `.py`, an approver, and the change switch on."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		pin_agent_roles(self)
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		log_error = patch.object(frappe, "log_error")
		log_error.start()
		self.addCleanup(log_error.stop)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(ACTOR)
		frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)
		self.sandbox = GitSandbox(self)
		for rel in TEXT_RELS:
			self.sandbox.commit_file(APP, rel, TEXT_BEFORE)
		self.sandbox.commit_file(APP, LEGACY_REL, BEFORE)
		set_agent_settings(code_change_enabled=1, code_change_apps=APP)
		frappe.set_user(ACTOR)

	def git(self, *args):
		return self.sandbox.git(APP, *args).strip()

	def snapshot(self):
		"""Every file's bytes, HEAD, the commit count and the porcelain status: what "0 written" compares."""
		files = {}
		for rel in (*TEXT_RELS, LEGACY_REL):
			with open(os.path.join(self.sandbox.repo(APP), rel), "rb") as handle:
				files[rel] = handle.read()
		return (
			files,
			self.git("rev-parse", "HEAD"),
			self.git("rev-list", "--count", "HEAD"),
			self.git("status", "--porcelain"),
		)

	def edits(self, count=3, overrides=None):
		"""`count` `edit` items over `TEXT_RELS`; `overrides` maps an item index to the fields it replaces."""
		items = []
		for index, rel in enumerate(TEXT_RELS[:count]):
			item = {
				"kind": CHANGE_OP_EDIT,
				"path": f"{APP}/{rel}",
				"before": TEXT_BEFORE,
				"after": TEXT_AFTER,
			}
			item.update((overrides or {}).get(index, {}))
			items.append(item)
		return items

	def block(self, operations, commands=(), **fields):
		return make_block_proposal(operations, list(commands), **fields).name

	def approve(self, name):
		transitions.approve(name, ACTOR)
		return name

	def refresh_digest(self, name):
		digest = transitions.content_digest(frappe.get_doc(PROPOSAL_DOCTYPE, name))
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "approved_digest", digest, update_modified=False)

	def run_apply(self, name):
		with patch("subprocess.run", wraps=subprocess.run) as run:
			apply_job.run_change(name, "apply")
		return run

	def assert_failed_untouched(self, name, reason, before, status=CHANGE_STATUS_FAILED):
		state = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason", "apply_commit_sha"], as_dict=True
		)
		self.assertEqual(
			(state.change_status, state.failure_reason, state.apply_commit_sha), (status, reason, None)
		)
		self.assertEqual(self.snapshot(), before)

	def full(self, rel):
		return os.path.join(self.sandbox.repo(APP), rel)

	def tree(self):
		"""Every directory and file's bytes under the repo but `.git`, HEAD, commit count, index and status."""
		repo = self.sandbox.repo(APP)
		dirs, files = [], {}
		for top, subdirs, names in os.walk(repo):
			subdirs[:] = sorted(d for d in subdirs if d != ".git")
			dirs.append(os.path.relpath(top, repo))
			for entry in sorted(names):
				path = os.path.join(top, entry)
				with open(path, "rb") as handle:
					files[os.path.relpath(path, repo)] = handle.read()
		return (
			dirs,
			files,
			self.git("rev-parse", "HEAD"),
			self.git("rev-list", "--count", "HEAD"),
			self.git("ls-files", "--stage"),
			self.git("status", "--porcelain"),
		)

	def assert_given_back(self, name, reason, before):
		"""`Lỗi` with `reason`, no commit sha, and the tree, HEAD and index as `before`."""
		state = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason", "apply_commit_sha"], as_dict=True
		)
		self.assertEqual(
			(state.change_status, state.failure_reason, state.apply_commit_sha),
			(CHANGE_STATUS_FAILED, reason, None),
		)
		self.assertEqual(self.tree(), before)

	def mixed_block(self, commands=()):
		"""Five items, one of each kind and a second edit: edit a, create in two new folders, delete b,
		rename c into two new folders, edit e; `commands` as stored."""
		if not os.path.exists(self.full(EXTRA_REL)):
			self.sandbox.commit_file(APP, EXTRA_REL, TEXT_BEFORE)
		return self.approve(
			self.block(
				[
					*self.edits(count=1),
					{"kind": CHANGE_OP_CREATE, "path": f"{APP}/{CREATED_REL}", "after": CREATED_TEXT},
					{"kind": CHANGE_OP_DELETE, "path": f"{APP}/{TEXT_RELS[1]}", "before": TEXT_BEFORE},
					{
						"kind": CHANGE_OP_RENAME,
						"path": f"{APP}/{TEXT_RELS[2]}",
						"new_path": f"{APP}/{MOVED_REL}",
						"before": TEXT_BEFORE,
						"after": TEXT_BEFORE,
					},
					{
						"kind": CHANGE_OP_EDIT,
						"path": f"{APP}/{EXTRA_REL}",
						"before": TEXT_BEFORE,
						"after": TEXT_AFTER,
					},
				],
				commands,
			)
		)

	def write_reason(self, number, path):
		# Design 4.2 step 6, written by hand so a changed constant cannot hide a changed sentence.
		return f"ghi mục {number} ({APP}/{path}) lỗi, đã trả mọi file về như trước"

	def record(self):
		"""Wrap the four `file_writer` functions and the two staging calls; return the list each call is
		appended to as `(name, args, kwargs)`. `self.failing(name, args, kwargs)`, when set, may return an
		exception to raise instead, or a value to return instead."""
		calls = []
		self.failing = None
		for module, names in (
			(apply_job.file_writer, ("make_parents", "write_atomic", "remove_file", "remove_empty_dirs")),
			(apply_job.process_runner, ("git_add_new", "git_unstage_new")),
		):
			for name in names:
				real = getattr(module, name)

				def wrapper(*args, _real=real, _name=name, **kwargs):
					calls.append((_name, args, kwargs))
					instead = self.failing(_name, args, kwargs) if self.failing else None
					if isinstance(instead, BaseException):
						raise instead
					if instead is not None:
						return instead
					return _real(*args, **kwargs)

				patcher = patch.object(module, name, side_effect=wrapper)
				patcher.start()
				self.addCleanup(patcher.stop)
		return calls

	def commit_result(self, **values):
		"""A failed `git_commit_only` result (exit 128) with `values` replaced."""
		fields = {"exit_code": 128, "output": "", "duration_ms": 1, "timed_out": False, "not_found": False}
		fields.update(values)
		return process_runner.CommandResult(**fields)

	def state(self, name):
		return frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			[
				"change_status",
				"failure_reason",
				"apply_commit_sha",
				"applied_branch",
				"applied_ahead_count",
				"created_dirs",
			],
			as_dict=True,
		)

	def name_status(self, rev="HEAD"):
		"""`(status, path)` of each path `rev` changed against its parent, a rename as delete + add."""
		out = self.git("show", "--no-renames", "--name-status", "--format=", rev)
		return sorted(tuple(line.split("\t")) for line in out.splitlines() if line)

	def log_rows(self, name):
		"""`(change_step, value_before, value_after)` of every log row of the proposal, oldest first."""
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name},
			fields=["change_step", "value_before", "value_after"],
			order_by="creation asc",
		)
		return [
			(row.change_step, json.loads(row.value_before or "null"), json.loads(row.value_after or "null"))
			for row in rows
		]

	def restart_from(self, start):
		"""Put the sandbox repo back at `start` with nothing untracked, between sub-cases that committed."""
		self.sandbox.git(APP, "reset", "--quiet", "--hard", start)
		self.sandbox.git(APP, "clean", "-fdq")

	def assert_mixed_files_applied(self):
		"""The five items of `mixed_block` are on disk: both edits, the created file, b and c gone, c moved."""
		files = self.tree()[1]
		for _status, rel in MIXED_COMMIT:
			with self.subTest(rel=rel):
				self.assertEqual(files.get(rel), MIXED_FILES_AFTER.get(rel))
		self.assertEqual(files[LEGACY_REL], BEFORE.encode())


def _once(test):
	"""A `fail` for `record` that answers `test(name, args, kwargs)` only the first time it is not None."""
	done = []

	def fail(name, args, kwargs):
		if done:
			return None
		instead = test(name, args, kwargs)
		if instead is not None:
			done.append(True)
		return instead

	return fail


EXTRA_REL = "notes/e.txt"
CREATED_REL = "fresh/deep/n.txt"
CREATED_TEXT = "file mới\n"
MOVED_REL = "moved/deep/c.txt"
# What `mixed_block` commits (design 4.2 step 7): every path of the block, both ends of the rename.
MIXED_COMMIT = sorted(
	[
		("M", TEXT_RELS[0]),
		("A", CREATED_REL),
		("D", TEXT_RELS[1]),
		("D", TEXT_RELS[2]),
		("A", MOVED_REL),
		("M", EXTRA_REL),
	]
)
MIXED_FILES_AFTER = {
	TEXT_RELS[0]: TEXT_AFTER.encode(),
	CREATED_REL: CREATED_TEXT.encode(),
	MOVED_REL: TEXT_BEFORE.encode(),
	EXTRA_REL: TEXT_AFTER.encode(),
}
MISMATCH = "commit không đúng nội dung đã duyệt, cần người kiểm"
ADD_FAILED = process_runner.CommandResult(
	exit_code=128, output="fatal: add lỗi", duration_ms=1, timed_out=False, not_found=False
)
UNSTAGE_FAILED = process_runner.CommandResult(
	exit_code=128, output="fatal: rm lỗi", duration_ms=1, timed_out=False, not_found=False
)


class TestBlockAllOrNothing(BlockApplyTestCase):
	"""Design 4.2 steps 1 to 3: the guard runs again at apply time; a refusal writes 0 bytes and makes 0 commits."""

	def test_guard_fails_at_apply_error_names_item(self):
		# A refusal at item 1, 2 or 3 names that item: the target became a symlink after approval.
		for index in range(3):
			with self.subTest(item=index + 1):
				name = self.approve(self.block(self.edits()))
				full = os.path.join(self.sandbox.repo(APP), TEXT_RELS[index])
				os.rename(full, f"{full}.real")
				os.symlink(f"{full}.real", full)
				# Put back before the next subtest even when this one fails, so only item `index` is a symlink.
				try:
					before = self.snapshot()

					self.run_apply(name)

					self.assert_failed_untouched(
						name,
						f"mục {index + 1} ({APP}/{TEXT_RELS[index]}): {change_guard.PATH_SYMLINK}",
						before,
					)
				finally:
					os.remove(full)
					os.replace(f"{full}.real", full)

	def test_app_removed_from_list_error(self):
		name = self.approve(self.block(self.edits()))
		set_agent_settings(code_change_apps="helpdesk")
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(
			name, f"mục 1 ({APP}/{TEXT_RELS[0]}): {change_guard.APP_NOT_ALLOWED}", before
		)

	def test_syntax_broken_at_apply_error(self):
		# Stored straight into the database (the tool would refuse it), hashes matching, approved.
		operations = [
			*self.edits(count=1),
			{"kind": CHANGE_OP_CREATE, "path": f"{APP}/docs/new.json", "after": '{"a": }\n'},
		]
		name = self.approve(self.block(operations))
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(
			name, f"mục 2 ({APP}/docs/new.json): {change_guard.JSON_SYNTAX.format(n=1)}", before
		)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "docs/new.json")))

	def write(self, rel, text):
		with open(os.path.join(self.sandbox.repo(APP), rel), "w", encoding="utf-8") as handle:
			handle.write(text)

	def stale_reason(self, number, rel):
		return f"mục {number} ({APP}/{rel}): {apply_job.TARGET_CHANGED}"

	def test_stale_target_first_middle_last_zero_written(self):
		# Design 4.2 step 4: every row is compared before any byte is written, wherever the stale one is.
		for index in range(3):
			with self.subTest(item=index + 1):
				self.sandbox.git(APP, "checkout", "--quiet", "--", ".")
				name = self.approve(self.block(self.edits()))
				self.write(TEXT_RELS[index], "người khác sửa\n")
				before = self.snapshot()

				self.run_apply(name)

				self.assert_failed_untouched(
					name, self.stale_reason(index + 1, TEXT_RELS[index]), before, CHANGE_STATUS_STALE
				)

	def test_branch_changed_stale(self):
		name = self.approve(self.block(self.edits()))
		self.git("checkout", "--quiet", "-b", "other")
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(name, apply_job.GIT_BRANCH_CHANGED, before, CHANGE_STATUS_STALE)

	def test_git_refusal_error_names_item(self):
		# Design 4.2 step 5: `read_git_state` for every path; a refusal is `Lỗi` naming its item (here item 2).
		real = source.read_git_state
		refused = os.path.join(self.sandbox.repo(APP), TEXT_RELS[1])

		def read_git_state(full, **kwargs):
			state = real(full, **kwargs)
			return dataclasses.replace(state, refusal="git bị khóa") if full == refused else state

		name = self.approve(self.block(self.edits()))
		before = self.snapshot()

		with patch.object(source, "read_git_state", side_effect=read_git_state):
			self.run_apply(name)

		self.assert_failed_untouched(name, f"mục 2 ({APP}/{TEXT_RELS[1]}): git bị khóa", before)

	def test_create_target_appeared_stale(self):
		operations = [
			*self.edits(count=1),
			{"kind": CHANGE_OP_CREATE, "path": f"{APP}/docs/new.txt", "after": "mới\n"},
		]
		name = self.approve(self.block(operations))
		self.write("docs/new.txt", "người khác tạo\n")
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(name, self.stale_reason(2, "docs/new.txt"), before, CHANGE_STATUS_STALE)
		with open(os.path.join(self.sandbox.repo(APP), "docs/new.txt"), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), "người khác tạo\n")

	def rename_item(self):
		"""Renames `TEXT_RELS[1]` to `docs/moved.txt`, its content kept."""
		return {
			"kind": CHANGE_OP_RENAME,
			"path": f"{APP}/{TEXT_RELS[1]}",
			"new_path": f"{APP}/docs/moved.txt",
			"before": TEXT_BEFORE,
			"after": TEXT_BEFORE,
		}

	def precheck(self, name):
		"""Steps 2 to 5 of design 4.2 called on their own, so the value step 5 returns can be read."""
		proposal = frappe.get_doc(PROPOSAL_DOCTYPE, name)
		check = apply_job._recheck_block(proposal, (APP,))
		return apply_job._precheck_block(proposal, check, time.monotonic() + 60)

	def test_rename_source_changed_or_target_exists_stale(self):
		cases = (
			("source changed", TEXT_RELS[1], "người khác sửa\n"),
			("target exists", "docs/moved.txt", "người khác tạo\n"),
		)
		moved = os.path.join(self.sandbox.repo(APP), "docs/moved.txt")
		for label, rel, text in cases:
			with self.subTest(label):
				self.sandbox.git(APP, "checkout", "--quiet", "--", ".")
				name = self.approve(self.block([*self.edits(count=1), self.rename_item()]))
				self.write(rel, text)
				try:
					before = self.snapshot()

					self.run_apply(name)

					self.assert_failed_untouched(
						name, self.stale_reason(2, TEXT_RELS[1]), before, CHANGE_STATUS_STALE
					)
				finally:
					if os.path.lexists(moved):
						os.remove(moved)

	def test_git_read_new_file_by_kind_returns_shared_head(self):
		# Step 5: git is read for every path, `new_file` only for a created file and a rename target; the HEAD
		# they all share is what step 5 remembers as `old_head`.
		created = {"kind": CHANGE_OP_CREATE, "path": f"{APP}/docs/new.txt", "after": "mới\n"}
		name = self.approve(self.block([*self.edits(count=1), created, self.rename_item()]))
		repo = self.sandbox.repo(APP)

		with patch.object(source, "read_git_state", wraps=source.read_git_state) as spy:
			old_head = self.precheck(name)

		self.assertEqual(old_head, self.git("rev-parse", "HEAD"))
		self.assertEqual(
			[(call.args[0], call.kwargs["new_file"]) for call in spy.call_args_list],
			[
				(os.path.join(repo, TEXT_RELS[0]), False),
				(os.path.join(repo, "docs/new.txt"), True),
				(os.path.join(repo, TEXT_RELS[1]), False),
				(os.path.join(repo, "docs/moved.txt"), True),
			],
		)

	def test_head_differs_between_paths_error_names_item(self):
		# Design 4.2 step 5 has no sentence for it: every path must show the one HEAD that becomes `old_head`.
		real = source.read_git_state
		seen = []

		def read_git_state(full, **kwargs):
			seen.append(full)
			state = real(full, **kwargs)
			return dataclasses.replace(state, head="0" * 40) if len(seen) == 2 else state

		name = self.approve(self.block(self.edits()))
		before = self.snapshot()

		with patch.object(source, "read_git_state", side_effect=read_git_state):
			self.run_apply(name)

		self.assert_failed_untouched(name, f"mục 2 ({APP}/{TEXT_RELS[1]}): {source.GIT_ERROR}", before)

	def test_every_row_compared_before_any_git_read(self):
		# Item 3 is stale and git would refuse item 1: step 4 finishes before step 5 starts.
		real = source.read_git_state
		refused = os.path.join(self.sandbox.repo(APP), TEXT_RELS[0])

		def read_git_state(full, **kwargs):
			state = real(full, **kwargs)
			return dataclasses.replace(state, refusal="git bị khóa") if full == refused else state

		name = self.approve(self.block(self.edits()))
		self.write(TEXT_RELS[2], "người khác sửa\n")
		before = self.snapshot()

		with patch.object(source, "read_git_state", side_effect=read_git_state) as spy:
			self.run_apply(name)

		self.assert_failed_untouched(name, self.stale_reason(3, TEXT_RELS[2]), before, CHANGE_STATUS_STALE)
		spy.assert_not_called()

	def reset_sandbox(self):
		"""Put the sandbox repo back at HEAD with nothing untracked, between sub-cases that leave it broken."""
		self.sandbox.git(APP, "reset", "--quiet", "--hard", "HEAD")
		self.sandbox.git(APP, "clean", "-fdq")

	def raises_on(self, name, full, content=None):
		"""A `failing` hook raising `OSError` at the first `name(full, …)` call (with `content`, if given)."""
		return _once(
			lambda called, args, kwargs: OSError("đĩa đầy")
			if called == name and args[0] == full and (content is None or args[1] == content)
			else None
		)

	def test_writer_fails_at_item_3_of_5_restores_bytes_dirs_zero_commit(self):
		# Design 4.2 step 6, NFR-13: the delete of item 3 fails after items 1 and 2 were written.
		name = self.mixed_block()
		before = self.tree()
		calls = self.record()
		self.failing = self.raises_on("remove_file", self.full(TEXT_RELS[1]))

		self.run_apply(name)

		self.assert_given_back(name, self.write_reason(3, TEXT_RELS[1]), before)
		self.assertNotIn("git_add_new", [call[0] for call in calls])

	def test_writer_fails_at_first_and_last_item(self):
		# NFR-13: a failure at the first item writes nothing else; at the last item all four kinds go back.
		calls = self.record()
		for number, rel in ((1, TEXT_RELS[0]), (5, EXTRA_REL)):
			with self.subTest(item=number):
				name = self.mixed_block()
				before = self.tree()
				calls.clear()
				self.failing = self.raises_on("write_atomic", self.full(rel), TEXT_AFTER)

				self.run_apply(name)

				self.assert_given_back(name, self.write_reason(number, rel), before)
				if number == 1:
					self.assertEqual(len(calls), 2, calls)

	def test_give_back_reverse_order_with_kind_arguments(self):
		# Design 4.2 step 6 table and give-back list: each kind's calls and arguments, then the reverse order.
		name = self.mixed_block()
		repo = self.sandbox.repo(APP)
		a, b, c, e = (self.full(rel) for rel in (*TEXT_RELS, EXTRA_REL))
		created, moved = self.full(CREATED_REL), self.full(MOVED_REL)
		calls = self.record()
		self.failing = self.raises_on("write_atomic", e)

		self.run_apply(name)

		self.assertEqual(
			calls,
			[
				("write_atomic", (a, TEXT_AFTER), {"new_file": False}),
				("make_parents", (created, repo), {}),
				("write_atomic", (created, CREATED_TEXT), {"new_file": True}),
				("remove_file", (b,), {}),
				("make_parents", (moved, repo), {}),
				("write_atomic", (moved, TEXT_BEFORE), {"new_file": True}),
				("remove_file", (c,), {}),
				("write_atomic", (e, TEXT_AFTER), {"new_file": False}),
				("write_atomic", (c, TEXT_BEFORE), {"new_file": True}),
				("remove_file", (moved,), {}),
				("write_atomic", (b, TEXT_BEFORE), {"new_file": True}),
				("remove_file", (created,), {}),
				("write_atomic", (a, TEXT_BEFORE), {"new_file": False}),
				(
					"remove_empty_dirs",
					(
						[
							self.full("fresh"),
							self.full("fresh/deep"),
							self.full("moved"),
							self.full("moved/deep"),
						],
					),
					{},
				),
			],
		)

	def test_read_back_hash_mismatch_restores_all(self):
		# Design 4.2 step 6: a read-back hash other than `after_hash` gives everything back like an error,
		# for an edit, a created file and a rename target alike. The bytes are written; only the hash is wrong.
		real_write = apply_job.file_writer.write_atomic
		self.record()
		for number, written, rel in (
			(5, EXTRA_REL, EXTRA_REL),
			(2, CREATED_REL, CREATED_REL),
			(4, MOVED_REL, TEXT_RELS[2]),
		):
			with self.subTest(item=number):
				self.reset_sandbox()
				name = self.mixed_block()
				before = self.tree()
				full = self.full(written)
				self.failing = _once(
					lambda called, args, kwargs, full=full: real_write(*args, **kwargs) and "0" * 64
					if called == "write_atomic" and args[0] == full
					else None
				)

				self.run_apply(name)

				self.assert_given_back(name, self.write_reason(number, rel), before)

	def test_rename_into_new_dir_fails_after_add_restores_index_and_dirs(self):
		# `git add` of the rename target fails after the created file was staged: unstaged, dirs gone.
		name = self.mixed_block()
		repo = self.sandbox.repo(APP)
		before = self.tree()
		calls = self.record()
		self.failing = _once(
			lambda called, args, kwargs: ADD_FAILED
			if called == "git_add_new" and args[1] == MOVED_REL
			else None
		)

		self.run_apply(name)

		self.assert_given_back(name, self.write_reason(4, TEXT_RELS[2]), before)
		staging = [(call[0], call[1][:2]) for call in calls if call[0].startswith("git_")]
		self.assertEqual(
			staging,
			[
				("git_add_new", (repo, CREATED_REL)),
				("git_add_new", (repo, MOVED_REL)),
				("git_unstage_new", (repo, CREATED_REL)),
			],
		)
		self.assertEqual(calls[-1][0], "remove_empty_dirs")

	def test_restore_incomplete_reports_restore_failed(self):
		# Design 4.2 step 6: a give-back that does not hold is `GIT_RESTORE_FAILED`; the other steps still run.
		calls = self.record()
		a, e, moved = self.full(TEXT_RELS[0]), self.full(EXTRA_REL), self.full(MOVED_REL)

		def add_fails(called, args, kwargs):
			return ADD_FAILED if called == "git_add_new" and args[1] == MOVED_REL else None

		cases = {
			# case: (failing hooks, bytes of item 1 after the give-back)
			"remove of a created file raises": (
				(self.raises_on("write_atomic", e), self.raises_on("remove_file", moved)),
				TEXT_BEFORE,
			),
			"read-back of a rewritten file wrong": (
				(
					self.raises_on("write_atomic", e),
					_once(
						lambda called, args, kwargs: "0" * 64
						if called == "write_atomic" and args == (a, TEXT_BEFORE)
						else None
					),
				),
				TEXT_AFTER,
			),
			"unstage fails": (
				(
					_once(add_fails),
					_once(
						lambda called, args, kwargs: UNSTAGE_FAILED if called == "git_unstage_new" else None
					),
				),
				TEXT_BEFORE,
			),
		}
		for case, (hooks, item_1) in cases.items():
			with self.subTest(case=case):
				self.reset_sandbox()
				name = self.mixed_block()
				head = self.git("rev-parse", "HEAD")
				calls.clear()
				self.failing = lambda *call, hooks=hooks: next(
					(instead for instead in (hook(*call) for hook in hooks) if instead is not None), None
				)

				self.run_apply(name)

				state = frappe.db.get_value(
					PROPOSAL_DOCTYPE,
					name,
					["change_status", "failure_reason", "apply_commit_sha"],
					as_dict=True,
				)
				self.assertEqual(
					(state.change_status, state.failure_reason, state.apply_commit_sha),
					(CHANGE_STATUS_FAILED, apply_job.GIT_RESTORE_FAILED, None),
				)
				# The steps after the one that did not hold still ran, down to the folders.
				self.assertEqual(self.tree()[1][TEXT_RELS[0]], item_1.encode())
				self.assertEqual(calls[-1][0], "remove_empty_dirs")
				self.assertEqual(self.git("rev-parse", "HEAD"), head)

	def test_each_give_back_check_alone_reports_restore_failed(self):
		# Design 4.2 step 6: each condition of "the give-back held" is caught on its own; the write of
		# item 5 fails, so items 1 to 4 (with two staged files and four new folders) go back.
		real_write = apply_job.file_writer.write_atomic
		real_head = source.git_head
		calls = self.record()
		a, e, moved = self.full(TEXT_RELS[0]), self.full(EXTRA_REL), self.full(MOVED_REL)
		head_moved = []

		def git_head(app_dir):
			return "f" * 40 if head_moved else real_head(app_dir)

		def give_back_of_a(answer):
			return _once(
				lambda called, args, kwargs: answer(*args, **kwargs)
				if called == "write_atomic" and args == (a, TEXT_BEFORE)
				else None
			)

		def at_dirs(answer):
			return lambda called, args, kwargs: answer(args[0]) if called == "remove_empty_dirs" else None

		def flip_head(created):
			head_moved.append(True)

		cases = {
			# case: (failing hook after item 5 fails, the tree is as before)
			"a: read-back hash wrong after real bytes": (
				give_back_of_a(lambda *args, **kwargs: real_write(*args, **kwargs) and "0" * 64),
				True,
			),
			"b: base_hash returned, bytes not written": (
				give_back_of_a(lambda *args, **kwargs: _sha(TEXT_BEFORE)),
				False,
			),
			"c: created folders not removed": (at_dirs(lambda created: []), False),
			"d: HEAD moved": (at_dirs(flip_head), True),
			"e: created file not removed": (
				lambda called, args, kwargs: True
				if called == "remove_file" and args == (moved,)
				else (list(args[0]) if called == "remove_empty_dirs" else None),
				False,
			),
		}
		with patch.object(source, "git_head", side_effect=git_head):
			for case, (hook, same_tree) in cases.items():
				with self.subTest(case=case):
					self.reset_sandbox()
					head_moved.clear()
					name = self.mixed_block()
					before = self.tree()
					calls.clear()
					fail_e = self.raises_on("write_atomic", e, TEXT_AFTER)
					self.failing = lambda *call, hook=hook, fail_e=fail_e: fail_e(*call) or hook(*call)

					self.run_apply(name)

					head_moved.clear()
					state = frappe.db.get_value(
						PROPOSAL_DOCTYPE,
						name,
						["change_status", "failure_reason", "apply_commit_sha"],
						as_dict=True,
					)
					self.assertEqual(
						(state.change_status, state.failure_reason, state.apply_commit_sha),
						(CHANGE_STATUS_FAILED, apply_job.GIT_RESTORE_FAILED, None),
					)
					self.assertEqual(calls[-1][0], "remove_empty_dirs")
					now = self.tree()
					self.assertEqual(now[2:5], before[2:5])
					if same_tree:
						self.assertEqual(now, before)

	def test_whole_block_written_then_given_back_until_one_commit_exists(self):
		# T36 boundary: the commands of a block come later (T37); a block with a command still has every
		# write given back, 0 commits, 0 commands.
		name = self.mixed_block(commands=[["--site", frappe.local.site, "migrate"]])
		before = self.tree()
		calls = self.record()

		self.run_apply(name)

		self.assert_given_back(name, change_guard.OP_UNKNOWN, before)
		self.assertEqual(
			[(call[0], call[1][1]) for call in calls if call[0].startswith("git_")],
			[
				("git_add_new", CREATED_REL),
				("git_add_new", MOVED_REL),
				("git_unstage_new", MOVED_REL),
				("git_unstage_new", CREATED_REL),
			],
		)

	def test_commit_fails_restores_all_head_and_index_unchanged(self):
		# Design 4.2 step 7: the one commit fails with HEAD unchanged → every item back as step 6, 0 commits.
		name = self.mixed_block()
		before = self.tree()
		failed = self.commit_result(output="fatal: không commit được")
		with patch.object(apply_job.process_runner, "git_commit_only", return_value=failed) as commit:
			self.run_apply(name)

		self.assertEqual(commit.call_count, 1)
		self.assert_given_back(
			name, "commit git lỗi, đã trả file về như trước: fatal: không commit được", before
		)

	def test_commit_timeout_restores_all(self):
		name = self.mixed_block()
		before = self.tree()
		timed_out = self.commit_result(exit_code=None, timed_out=True)
		with patch.object(apply_job.process_runner, "git_commit_only", return_value=timed_out):
			self.run_apply(name)

		self.assert_given_back(name, "commit git lỗi, đã trả file về như trước (quá thời gian)", before)

	def test_one_log_row_per_outcome(self):
		# Design 6 "Quan sát": one `apply` or `fail` row per run, with the block's head, branch and files.
		real_summary = source.git_commit_summary
		self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		cases = (
			("applied", {}, "apply"),
			(
				"commit failed",
				{"git_commit_only": lambda *args: self.commit_result(output="fatal: lỗi")},
				"fail",
			),
			(
				"post-check mismatch",
				{"git_commit_summary": lambda repo: dataclasses.replace(real_summary(repo), branch="khac")},
				"fail",
			),
			("crash after commit", {"record_commit": RuntimeError("hỏng")}, "fail"),
		)
		owners = {"git_commit_only": apply_job.process_runner, "git_commit_summary": source}
		for label, stubs, step in cases:
			with self.subTest(label):
				self.restart_from(start)
				name = self.mixed_block()
				known = len(self.log_rows(name))
				patchers = [
					patch.object(owners.get(stub, apply_job.transitions), stub, side_effect=effect)
					for stub, effect in stubs.items()
				]
				# The crash case rolls back before it records `Lỗi`; inside a test that would drop the proposal.
				patchers.append(patch.object(frappe.db, "rollback"))
				for patcher in patchers:
					patcher.start()
				try:
					self.run_apply(name)
				finally:
					for patcher in patchers:
						patcher.stop()

				rows = self.log_rows(name)[known:]
				self.assertEqual([row[0] for row in rows], [step])
				files_before = {rel: _sha(TEXT_BEFORE) for rel in (*TEXT_RELS, EXTRA_REL)}
				self.assertEqual(rows[0][1], {"head": start, "files": files_before})
				if label == "commit failed":
					continue
				self.assertEqual(
					rows[0][2],
					{
						"commit": self.git("rev-parse", "HEAD"),
						"branch": "khac" if label == "post-check mismatch" else "main",
						"files": {
							TEXT_RELS[0]: _sha(TEXT_AFTER),
							CREATED_REL: _sha(CREATED_TEXT),
							TEXT_RELS[1]: None,
							TEXT_RELS[2]: None,
							MOVED_REL: _sha(TEXT_BEFORE),
							EXTRA_REL: _sha(TEXT_AFTER),
						},
					},
				)

	def test_parent_became_file_after_proposal_error_zero_written(self):
		# The parent folder of a created item is a file by apply time: `Lỗi`, 0 bytes left, 0 commits.
		name = self.approve(
			self.block(
				[
					*self.edits(count=1),
					{"kind": CHANGE_OP_CREATE, "path": f"{APP}/{CREATED_REL}", "after": CREATED_TEXT},
				]
			)
		)
		with open(self.full("fresh"), "w", encoding="utf-8") as handle:
			handle.write("tệp chắn đường\n")
		before = self.tree()
		with patch.object(
			apply_job.process_runner, "git_commit_only", wraps=process_runner.git_commit_only
		) as commit:
			self.run_apply(name)

		self.assert_given_back(name, self.write_reason(2, CREATED_REL), before)
		self.assertEqual(commit.call_count, 0)


class TestDelete(BlockApplyTestCase):
	"""Design 4.2 step 4 for a `delete` item: its file must still hash to `base_hash`."""

	def test_changed_since_proposal_stale_zero_deleted(self):
		operations = [
			*self.edits(count=1),
			{"kind": CHANGE_OP_DELETE, "path": f"{APP}/{TEXT_RELS[1]}", "before": TEXT_BEFORE},
		]
		name = self.approve(self.block(operations))
		with open(os.path.join(self.sandbox.repo(APP), TEXT_RELS[1]), "w", encoding="utf-8") as handle:
			handle.write("người khác sửa\n")
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(
			name, f"mục 2 ({APP}/{TEXT_RELS[1]}): {apply_job.TARGET_CHANGED}", before, CHANGE_STATUS_STALE
		)

	def test_parent_swapped_to_symlink_after_check_zero_deleted_outside(self):
		# Design-addendum-1 A-3.3: once `check_block` passed, the delete's folder becomes a symlink out of
		# the app; the delete is refused, the file outside stays, item 1 goes back byte for byte.
		self.sandbox.commit_file(APP, "sub/x.txt", TEXT_BEFORE)
		outside = os.path.join(self.sandbox.base, "outside")
		os.makedirs(outside)
		with open(os.path.join(outside, "x.txt"), "w", encoding="utf-8") as handle:
			handle.write(TEXT_BEFORE)
		name = self.approve(
			self.block(
				[
					*self.edits(count=1),
					{"kind": CHANGE_OP_DELETE, "path": f"{APP}/sub/x.txt", "before": TEXT_BEFORE},
				]
			)
		)
		real_check, real_write = change_guard.check_block, apply_job.file_writer.write_atomic
		swapped = {}

		def check_block(*args, **kwargs):
			swapped["checked"] = True
			return real_check(*args, **kwargs)

		def write_atomic(*args, **kwargs):
			# Any moment after `check_block` returned; here right before the first byte is written, so the
			# git reads of step 5 have passed and the delete itself meets the symlink.
			if swapped.pop("checked", False):
				os.rename(self.full("sub"), os.path.join(self.sandbox.base, "sub_kept"))
				os.symlink(outside, self.full("sub"))
				swapped["tree"] = self.tree()
			return real_write(*args, **kwargs)

		with (
			patch.object(change_guard, "check_block", side_effect=check_block),
			patch.object(apply_job.file_writer, "write_atomic", side_effect=write_atomic),
		):
			self.run_apply(name)

		self.assert_given_back(name, self.write_reason(2, "sub/x.txt"), swapped.get("tree"))
		with open(os.path.join(outside, "x.txt"), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), TEXT_BEFORE)
		self.assertEqual(self.tree()[1][TEXT_RELS[0]], TEXT_BEFORE.encode())

	def test_delete_removes_file_commit_records_deletion(self):
		# Design 4.2 steps 6 to 7 (R-9, T-0): the file is removed and the one commit records it as deleted.
		rel = TEXT_RELS[1]
		name = self.approve(
			self.block([{"kind": CHANGE_OP_DELETE, "path": f"{APP}/{rel}", "before": TEXT_BEFORE}])
		)
		start = self.git("rev-parse", "HEAD")

		self.run_apply(name)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPLIED, state.failure_reason)
		self.assertFalse(os.path.lexists(self.full(rel)))
		self.assertEqual(self.name_status(), [("D", rel)])
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assertEqual(self.git("status", "--porcelain"), "")
		self.assertEqual(
			self.log_rows(name)[-1],
			(
				"apply",
				{"head": start, "files": {rel: _sha(TEXT_BEFORE)}},
				{"commit": state.apply_commit_sha, "branch": "main", "files": {rel: None}},
			),
		)


class TestApplyBlock(BlockApplyTestCase):
	"""Design 4.2 steps 2 to 3 on the stored commands and rows of an approved block."""

	def test_stored_command_edited_to_denied_blocked_at_apply(self):
		site = frappe.local.site
		denied = ["--site", site, "execute", "frappe.db.truncate"]
		migrate = ["--site", site, "migrate"]
		py_edit = [{"kind": CHANGE_OP_EDIT, "path": f"{APP}/{LEGACY_REL}", "before": BEFORE, "after": AFTER}]
		cases = (
			("denied command", self.edits(count=1), [denied], f"lệnh 1: {change_guard.CMD_NOT_LISTED}"),
			(
				"denied second command",
				self.edits(count=1),
				[migrate, denied],
				f"lệnh 2: {change_guard.CMD_NOT_LISTED}",
			),
			("empty argv", self.edits(count=1), [[]], f"lệnh 1: {change_guard.CMD_NOT_LISTED}"),
			# Block-wide rules with no command prefix, refused only because a block is not the old shape.
			("block .py without restart", py_edit, [migrate], change_guard.PY_NEEDS_RESTART),
			(
				"block restart without .py",
				self.edits(count=1),
				[migrate, ["restart"]],
				change_guard.RESTART_WITHOUT_PY,
			),
		)
		for label, operations, commands, reason in cases:
			with self.subTest(label):
				name = self.approve(self.block(operations, [migrate]))
				frappe.db.set_value(
					PROPOSAL_DOCTYPE, name, "command_list", json.dumps(commands), update_modified=False
				)
				self.refresh_digest(name)
				before = self.snapshot()

				run = self.run_apply(name)

				run.assert_not_called()
				self.assert_failed_untouched(name, reason, before)

	def test_stored_hash_mismatch_refused(self):
		# Edited before approval, so the approved digest covers it and only the stored-hash row catches it.
		cases = (
			("after_hash item 1", 0, {"after_hash": _sha("autre\n")}),
			("base_hash item 2", 1, {"base_hash": _sha("autre\n")}),
			("after_hash item 3", 2, {"after_hash": _sha("autre\n")}),
		)
		for label, index, override in cases:
			with self.subTest(label):
				name = self.approve(self.block(self.edits(overrides={index: override})))
				before = self.snapshot()

				self.run_apply(name)

				self.assert_failed_untouched(name, apply_job.STORED_HASH_MISMATCH, before)

	def test_commit_message_preview_edited_refused(self):
		name = self.block(self.edits())
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "commit_message", "erp_ai: khác", update_modified=False)
		self.approve(name)
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(name, apply_job.DIGEST_CHANGED, before)

	def test_one_approval_applies_whole_block_decision_calls_1(self):
		# One approval, one run: the five items of every kind land in one commit, no second decision.
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		with (
			patch.object(
				apply_job.process_runner, "git_commit_only", wraps=process_runner.git_commit_only
			) as commit,
			patch.object(apply_job.transitions, "approve", wraps=transitions.approve) as approve,
		):
			self.run_apply(name)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPLIED, state.failure_reason)
		self.assertFalse(state.failure_reason)
		self.assertEqual((commit.call_count, approve.call_count), (1, 0))
		self.assertEqual(state.apply_commit_sha, self.git("rev-parse", "HEAD"))
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assertEqual((state.applied_branch, state.applied_ahead_count), ("main", 0))
		self.assertEqual(
			json.loads(state.created_dirs),
			[f"{APP}/fresh", f"{APP}/fresh/deep", f"{APP}/moved", f"{APP}/moved/deep"],
		)
		self.assertEqual(self.name_status(), MIXED_COMMIT)
		self.assert_mixed_files_applied()
		self.assertEqual(self.git("status", "--porcelain"), "")


# The bot identity as written in design 8.3 (NFR-8), and what must never leak into a commit.
BOT_AUTHOR = "ERP AI Agent <erp-ai-agent@bot.invalid>"
HOME_EMAIL = "real.person@example.com"
HOME_NAME = "Real Person From Home"
REMOTE_URL = "https://x-token-FAKE@host/r.git"
APPROVER_NAME_EMAIL = "duyet.that@corp.example"


class TestBlockCommit(BlockApplyTestCase):
	"""Design 4.2 steps 7 to 8: one commit holding every path of the block, its post-check, its record."""

	def test_commit_holds_exactly_block_paths_with_rename_both_ends(self):
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		with patch.object(
			apply_job.process_runner, "git_commit_only", wraps=process_runner.git_commit_only
		) as commit:
			self.run_apply(name)

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(commit.call_count, 1)
		repo, rels = commit.call_args.args[:2]
		self.assertEqual(os.path.realpath(repo), os.path.realpath(self.sandbox.repo(APP)))
		self.assertEqual(rels, tuple(sorted(rel for _status, rel in MIXED_COMMIT)))
		self.assertEqual(self.name_status(), MIXED_COMMIT)
		self.assertEqual(self.git("rev-list", "--parents", "-n", "1", "HEAD").split()[1:], [start])

	def test_other_staged_and_unstaged_files_untouched_refs_unchanged(self):
		name = self.mixed_block()
		self.git("tag", "kept-tag")
		self.git("branch", "kept-branch")
		with open(self.full(LEGACY_REL), "w", encoding="utf-8") as handle:
			handle.write(AFTER)
		with open(self.full("staged.txt"), "w", encoding="utf-8") as handle:
			handle.write("đã stage\n")
		self.git("add", "--", "staged.txt")
		refs = ("for-each-ref", "--format=%(refname) %(objectname)", "refs/tags", "refs/heads/kept-branch")
		refs_before = self.git(*refs)

		self.run_apply(name)

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(self.name_status(), MIXED_COMMIT)
		self.assertEqual(self.git("diff", "--cached", "--name-status"), "A\tstaged.txt")
		self.assertEqual(self.git("diff", "--name-only"), LEGACY_REL)
		with open(self.full(LEGACY_REL), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), AFTER)
		self.assertEqual(self.git(*refs), refs_before)

	def assert_mismatch_kept(self, name, start):
		"""`Lỗi` `GIT_COMMIT_MISMATCH` with the commit sha kept and every file left as applied."""
		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, MISMATCH))
		self.assertEqual(state.apply_commit_sha, self.git("rev-parse", "HEAD"))
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assert_mixed_files_applied()

	def test_postcheck_extra_path_is_mismatch(self):
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		real = source.git_commit_summary

		def summary(repo):
			found = real(repo)
			return dataclasses.replace(found, paths=(*found.paths, "docs/khac.txt"))

		with patch.object(source, "git_commit_summary", side_effect=summary):
			self.run_apply(name)

		self.assert_mismatch_kept(name, start)

	def test_postcheck_each_condition_alone_is_mismatch(self):
		# Each condition of design 4.2 step 7 broken alone, every other one true.
		real_summary, real_blob = source.git_commit_summary, source.git_blob
		self.mixed_block()
		start = self.git("rev-parse", "HEAD")

		def with_summary(**changes):
			return {"git_commit_summary": lambda repo: dataclasses.replace(real_summary(repo), **changes)}

		def with_blob(rel, blob):
			return {
				"git_blob": lambda repo, commit, path: blob if path == rel else real_blob(repo, commit, path)
			}

		cases = (
			("two parents", lambda: with_summary(parents=(start, start))),
			("old head not an ancestor", lambda: {"git_is_ancestor": lambda *args: False}),
			(
				"a path missing",
				lambda: with_summary(paths=tuple(r for _s, r in MIXED_COMMIT if r != MOVED_REL)),
			),
			("other branch", lambda: with_summary(branch="khac")),
			("edit bytes", lambda: with_blob(TEXT_RELS[0], TEXT_BEFORE.encode())),
			("created bytes", lambda: with_blob(CREATED_REL, b"")),
			("rename target bytes", lambda: with_blob(MOVED_REL, None)),
			("deleted file still in tree", lambda: with_blob(TEXT_RELS[1], TEXT_BEFORE.encode())),
			("rename source still in tree", lambda: with_blob(TEXT_RELS[2], TEXT_BEFORE.encode())),
		)
		for label, stubs in cases:
			with self.subTest(label):
				self.restart_from(start)
				name = self.mixed_block()
				patchers = [
					patch.object(source, stub, side_effect=effect) for stub, effect in stubs().items()
				]
				for patcher in patchers:
					patcher.start()
				try:
					self.run_apply(name)
				finally:
					for patcher in patchers:
						patcher.stop()

				self.assert_mismatch_kept(name, start)

	def test_postcheck_asks_old_head_ancestor_of_parent(self):
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		with patch.object(source, "git_is_ancestor", wraps=source.git_is_ancestor) as ancestor:
			self.run_apply(name)

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		repo, older, newer = ancestor.call_args.args
		self.assertEqual((older, newer), (start, self.git("rev-parse", "HEAD~1")))

	def test_blob_bytes_equal_approved(self):
		name = self.mixed_block()
		with patch.object(source, "git_blob", wraps=source.git_blob) as blob:
			self.run_apply(name)

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)
		self.assertEqual(
			sorted(call.args[2] for call in blob.call_args_list), sorted(r for _s, r in MIXED_COMMIT)
		)
		for rel, data in MIXED_FILES_AFTER.items():
			with self.subTest(rel):
				shown = subprocess.run(
					["git", "-C", self.sandbox.repo(APP), "show", f"HEAD:{rel}"],
					capture_output=True,
					check=True,
				)
				self.assertEqual(shown.stdout, data)
		self.assertEqual(self.git("ls-tree", "--name-only", "HEAD", "--", TEXT_RELS[1], TEXT_RELS[2]), "")

	def test_crash_after_commit_keeps_sha_and_files(self):
		# Design-addendum-3 QĐ-B2 items 1 and 4: once the bot commit exists nothing is given back.
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		# The job rolls back before it records `Lỗi`; inside a test that would drop the proposal itself.
		with (
			patch.object(apply_job.transitions, "record_commit", side_effect=RuntimeError("hỏng")),
			patch.object(frappe.db, "rollback"),
		):
			self.run_apply(name)

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "RuntimeError"))
		self.assertEqual(state.apply_commit_sha, self.git("rev-parse", "HEAD"))
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assert_mixed_files_applied()
		self.assertEqual(self.log_rows(name)[-1][2]["commit"], state.apply_commit_sha)

	def test_commit_reported_failed_but_bot_commit_landed_goes_to_postcheck(self):
		# Design 4.2 step 7 → `_commit_landed`: HEAD moved to the bot's commit, so nothing is given back.
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		real_commit = process_runner.git_commit_only

		def commit_then_report_failure(*args):
			real_commit(*args)
			return self.commit_result(output="fatal: báo lỗi sau khi commit")

		with patch.object(
			apply_job.process_runner, "git_commit_only", side_effect=commit_then_report_failure
		):
			self.run_apply(name)

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
		self.assertEqual(state.apply_commit_sha, self.git("rev-parse", "HEAD"))
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assertEqual(self.name_status(), MIXED_COMMIT)
		self.assert_mixed_files_applied()

	def test_commit_limit_comes_from_the_job_deadline(self):
		# Design 3.5: the one commit's `limit_s` is what is left of the job budget, capped by `GIT_TIMEOUT_S`.
		self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		for spent, limit in ((100, source.GIT_TIMEOUT_S), (apply_job.COMMAND_TIMEOUT_S - 5, 5)):
			with self.subTest(spent=spent):
				self.restart_from(start)
				name = self.mixed_block()
				clock = iter([1000.0])
				with (
					patch("time.monotonic", side_effect=lambda spent=spent: next(clock, 1000.0 + spent)),
					patch.object(
						apply_job.process_runner, "git_commit_only", wraps=process_runner.git_commit_only
					) as commit,
				):
					self.run_apply(name)

				self.assertEqual(commit.call_args.args[4], limit)
				self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

	def test_git_refusal_after_commit_keeps_sha_and_files(self):
		# Step 8 reads the upstream again after the commit: a refusal then ends `Lỗi` with that sentence and
		# keeps the commit and every file as applied (design-addendum-3 QĐ-B2 item 1).
		name = self.mixed_block()
		start = self.git("rev-parse", "HEAD")
		real_commit, real_state = process_runner.git_commit_only, source.read_git_state
		committed = []

		def commit(*args):
			committed.append(True)
			return real_commit(*args)

		def read_git_state(full, **kwargs):
			state = real_state(full, **kwargs)
			return dataclasses.replace(state, refusal="git bị khóa") if committed else state

		with (
			patch.object(apply_job.process_runner, "git_commit_only", side_effect=commit),
			patch.object(source, "read_git_state", side_effect=read_git_state),
		):
			self.run_apply(name)

		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, "git bị khóa"))
		self.assertEqual(state.apply_commit_sha, self.git("rev-parse", "HEAD"))
		self.assertEqual(self.git("rev-parse", "HEAD~1"), start)
		self.assert_mixed_files_applied()
		self.assertEqual(self.log_rows(name)[-1][2]["commit"], state.apply_commit_sha)

	def test_block_commit_metadata_has_no_email_url_or_token(self):
		home = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, home, True)
		with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as handle:
			handle.write(f"[user]\n\temail = {HOME_EMAIL}\n\tname = {HOME_NAME}\n")
		environ = patch.dict(os.environ, {"HOME": home, "XDG_CONFIG_HOME": home, "EMAIL": HOME_EMAIL})
		environ.start()
		self.addCleanup(environ.stop)
		self.sandbox.add_remote(APP, url=REMOTE_URL)
		name = self.mixed_block()

		with patch.object(apply_job, "get_fullname", return_value=f"Duyệt {APPROVER_NAME_EMAIL}"):
			self.run_apply(name)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPLIED, state.failure_reason)
		meta = self.sandbox.log_meta(APP, state.apply_commit_sha)
		author_name, author_email, committer_name, committer_email, message = meta.split("\n", 4)
		self.assertEqual(f"{author_name} <{author_email}>", BOT_AUTHOR)
		self.assertEqual(f"{committer_name} <{committer_email}>", BOT_AUTHOR)
		self.assertIn("Người duyệt: (không hiện tên)", message)
		for leak in ("@", "://", "x-token-FAKE", "host/r.git", HOME_NAME):
			self.assertNotIn(leak, message)
		for leak in (HOME_EMAIL, HOME_NAME, ACTOR, APPROVER_NAME_EMAIL, "x-token-FAKE"):
			self.assertNotIn(leak, meta)
		self.assertEqual(state.applied_ahead_count, int(self.git("rev-list", "--count", "origin/main..HEAD")))


class TestNewDirs(BlockApplyTestCase):
	def test_create_three_level_tree_matches_proposal(self):
		rel = "lop1/lop2/lop3/moi.txt"
		name = self.approve(
			self.block([{"kind": CHANGE_OP_CREATE, "path": f"{APP}/{rel}", "after": CREATED_TEXT}])
		)

		self.run_apply(name)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPLIED, state.failure_reason)
		self.assertEqual(
			json.loads(state.created_dirs), [f"{APP}/lop1", f"{APP}/lop1/lop2", f"{APP}/lop1/lop2/lop3"]
		)
		with open(self.full(rel), "rb") as handle:
			self.assertEqual(handle.read(), CREATED_TEXT.encode())
		self.assertEqual(self.name_status(), [("A", rel)])
		self.assertEqual(self.git("status", "--porcelain"), "")


class TestRename(BlockApplyTestCase):
	def test_rename_keeps_bytes(self):
		src = TEXT_RELS[2]
		name = self.approve(
			self.block(
				[
					{
						"kind": CHANGE_OP_RENAME,
						"path": f"{APP}/{src}",
						"new_path": f"{APP}/{MOVED_REL}",
						"before": TEXT_BEFORE,
						"after": TEXT_BEFORE,
					}
				]
			)
		)

		self.run_apply(name)

		state = self.state(name)
		self.assertEqual(state.change_status, CHANGE_STATUS_APPLIED, state.failure_reason)
		self.assertFalse(os.path.lexists(self.full(src)))
		with open(self.full(MOVED_REL), "rb") as handle:
			self.assertEqual(handle.read(), TEXT_BEFORE.encode())
		self.assertEqual(self.name_status(), sorted([("A", MOVED_REL), ("D", src)]))
		self.assertEqual(self.git("status", "--porcelain"), "")


class TestLegacyThroughAdapter(BlockApplyTestCase):
	"""Design 2.3 and 4.2 step 2: a proposal of the old shape goes through the adapter and `legacy=True`."""

	def legacy(self, **fields):
		values = {
			"app": APP,
			"file_path": f"{APP}/{LEGACY_REL}",
			"content_before": BEFORE,
			"content_after": AFTER,
			"base_hash": _sha(BEFORE),
			"after_hash": _sha(AFTER),
			"target_branch": "main",
			"upstream_ref": "",
			**fields,
		}
		return make_change_proposal(CHANGE_KIND_CODE, **values).name

	def test_legacy_approved_proposal_applies(self):
		diff = f"--- a/{LEGACY_REL}\n+++ b/{LEGACY_REL}\n-x = 1\n+x = 2\n"
		name = self.approve(self.legacy(diff=diff))
		head = self.git("rev-parse", "HEAD")

		with (
			patch.object(apply_job.block, "operations_of", wraps=apply_job.block.operations_of) as adapter,
			patch.object(change_guard, "check_block", wraps=change_guard.check_block) as guard,
		):
			self.run_apply(name)

		state = frappe.db.get_value(
			PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason", "apply_commit_sha"], as_dict=True
		)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
		self.assertTrue(adapter.called)
		guard.assert_called_once()
		self.assertEqual(guard.call_args.kwargs["legacy"], True)
		self.assertEqual(guard.call_args.kwargs["at_apply"], True)
		self.assertEqual(guard.call_args.kwargs["diff_text"], diff)
		with open(os.path.join(self.sandbox.repo(APP), LEGACY_REL), "rb") as handle:
			self.assertEqual(handle.read(), AFTER.encode("utf-8"))
		self.assertEqual(self.git("rev-parse", "HEAD"), state.apply_commit_sha)
		self.assertEqual(self.git("rev-parse", "HEAD~1"), head)
		self.assertEqual(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"), LEGACY_REL)
		self.assertEqual(self.git("status", "--porcelain"), "")

	def test_legacy_edit_empty_path_refused_at_apply_zero_writes(self):
		name = self.legacy()
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "file_path", "", update_modified=False)
		self.approve(name)
		before = self.snapshot()

		self.run_apply(name)

		self.assert_failed_untouched(
			name,
			"mục 1 (): " + change_guard.OP_FIELDS.format(action=change_guard.OP_ACTIONS[CHANGE_OP_EDIT]),
			before,
		)
