import hashlib
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import authority, queue
from erp_ai.agent.changes import apply_job
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_PENDING,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
from erp_ai.test_utils import GitSandbox, pin_agent_roles, set_agent_settings

APP = "custom_app"
REL = "pkg/mod.py"
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
