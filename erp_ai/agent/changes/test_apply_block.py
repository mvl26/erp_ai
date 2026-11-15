import dataclasses
import hashlib
import json
import os
import subprocess
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import authority, queue
from erp_ai.agent.changes import apply_job, transitions
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

	def test_legacy_steps_4_5_reasons_have_no_item_prefix(self):
		# Design addendum-8 A8-1: the old shape does steps 4 to 5 in `_apply_code`, its reasons without `mục n`.
		# The sentences are written by hand (apply_job.TARGET_CHANGED, source.GIT_LOCKED, GIT_BRANCH_CHANGED).
		repo = self.sandbox.repo(APP)
		branch = self.git("rev-parse", "--abbrev-ref", "HEAD")
		lock = self.git("rev-parse", "--path-format=absolute", "--git-path", "index.lock")

		def overwrite():
			with open(os.path.join(repo, LEGACY_REL), "w", encoding="utf-8") as handle:
				handle.write("người khác sửa\n")

		def undo_overwrite():
			self.git("checkout", "--quiet", "--", ".")

		def release_lock():
			if os.path.exists(lock):
				os.remove(lock)

		cases = (
			(
				"stale",
				overwrite,
				undo_overwrite,
				CHANGE_STATUS_STALE,
				"file đích đã đổi kể từ lúc đề xuất",
			),
			(
				"git refusal",
				lambda: self.sandbox.hold_index_lock(APP),
				release_lock,
				CHANGE_STATUS_FAILED,
				"kho git đang bị khóa (index.lock): có thao tác git khác đang chạy hoặc bị dừng giữa chừng",
			),
			(
				"branch",
				lambda: self.git("checkout", "--quiet", "-b", "other"),
				lambda: self.git("checkout", "--quiet", branch),
				CHANGE_STATUS_STALE,
				"nhánh đang checkout đã đổi kể từ lúc đề xuất",
			),
		)
		for label, arrange, restore, status, reason in cases:
			with self.subTest(label):
				name = self.approve(self.legacy())
				arrange()
				try:
					before = self.snapshot()

					with patch.object(apply_job, "_precheck_block", wraps=apply_job._precheck_block) as spy:
						self.run_apply(name)

					self.assert_failed_untouched(name, reason, before, status)
					spy.assert_not_called()
				finally:
					restore()

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
