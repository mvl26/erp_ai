from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import queue
from erp_ai.constants import TRIGGER_COMMENT_MENTION, TRIGGER_TICKET_INSERT

RUN_FOR_TICKET_PATH = "erp_ai.agent.runner.run_for_ticket"


class TestEnqueueAgentRun(FrappeTestCase):
	def setUp(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)

	def tearDown(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)

	def test_duplicate_trigger_same_transaction_one_job(self):
		with patch("frappe.enqueue") as enqueue:
			first = queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT)
			second = queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT)
			other_trigger = queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION)
			other_ticket = queue.enqueue_agent_run("TKT-2", TRIGGER_TICKET_INSERT)

		self.assertTrue(first)
		self.assertFalse(second)
		self.assertTrue(other_trigger)
		self.assertTrue(other_ticket)
		self.assertEqual(enqueue.call_count, 3)

	def test_enqueue_parameters(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION))

		enqueue.assert_called_once_with(
			RUN_FOR_TICKET_PATH,
			queue="long",
			timeout=600,
			enqueue_after_commit=True,
			job_id="erp_ai::TKT-1::comment_mention",
			deduplicate=True,
			ticket_name="TKT-1",
			trigger=TRIGGER_COMMENT_MENTION,
		)

	def test_requeue_after_rollback(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT))
			frappe.db.rollback()
			self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT))

		self.assertEqual(enqueue.call_count, 2)

	def test_pending_ids_cleared_after_commit_callbacks(self):
		with patch("frappe.enqueue"):
			queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT)
		self.assertIn("erp_ai::TKT-1::ticket_insert", frappe.flags.erp_ai_pending_job_ids)
		frappe.db.after_commit.run()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))

	def test_unknown_trigger_raises_value_error(self):
		with patch("frappe.enqueue") as enqueue:
			with self.assertRaises(ValueError):
				queue.enqueue_agent_run("TKT-1", "bogus")
		enqueue.assert_not_called()

	def test_runner_enqueue_unchanged(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-7", TRIGGER_TICKET_INSERT))

		enqueue.assert_called_once_with(
			"erp_ai.agent.runner.run_for_ticket",
			queue="long",
			timeout=600,
			enqueue_after_commit=True,
			job_id="erp_ai::TKT-7::ticket_insert",
			deduplicate=True,
			ticket_name="TKT-7",
			trigger="ticket_insert",
		)


class TestEnqueueChangeJob(FrappeTestCase):
	def test_enqueue_change_job_shape(self):
		for action in ("apply", "undo"):
			with self.subTest(action=action), patch("frappe.enqueue") as enqueue:
				self.assertIsNone(queue.enqueue_change_job("PROP-0001", action))

				enqueue.assert_called_once_with(
					"erp_ai.agent.changes.apply_job.run_change",
					queue="long",
					timeout=600,
					enqueue_after_commit=True,
					job_id=f"erp_ai_change::PROP-0001::{action}",
					deduplicate=True,
					proposal_name="PROP-0001",
					action=action,
				)

	def test_enqueue_change_job_rejects_unknown_action(self):
		for action in ("bogus", "Apply", "UNDO", "", None, "approve"):
			with self.subTest(action=action), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "Unknown action"):
					queue.enqueue_change_job("PROP-0001", action)
				enqueue.assert_not_called()

	def test_enqueue_change_job_rejects_bad_proposal_name(self):
		for proposal_name in ("", None, 17, b"PROP-0001"):
			with self.subTest(proposal_name=proposal_name), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "proposal_name"):
					queue.enqueue_change_job(proposal_name, "apply")
				enqueue.assert_not_called()
