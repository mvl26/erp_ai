from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import queue, runner
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
			other_trigger = queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, comment_name="COMMENT-1")
			other_ticket = queue.enqueue_agent_run("TKT-2", TRIGGER_TICKET_INSERT)

		self.assertTrue(first)
		self.assertFalse(second)
		self.assertTrue(other_trigger)
		self.assertTrue(other_ticket)
		self.assertEqual(enqueue.call_count, 3)

	def test_enqueue_parameters(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, comment_name="COMMENT-1"))

		enqueue.assert_called_once_with(
			RUN_FOR_TICKET_PATH,
			queue="long",
			timeout=600,
			enqueue_after_commit=True,
			job_id="erp_ai::TKT-1::comment_mention",
			deduplicate=True,
			ticket_name="TKT-1",
			trigger=TRIGGER_COMMENT_MENTION,
			comment_name="COMMENT-1",
		)

	def test_comment_mention_job_carries_comment_name(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, comment_name="COMMENT-9"))
			# A-U1-3: the job id stays per ticket, so a second @ai in the same transaction is merged.
			self.assertFalse(
				queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, comment_name="COMMENT-10")
			)

		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["comment_name"], "COMMENT-9")
		self.assertEqual(enqueue.call_args.kwargs["job_id"], "erp_ai::TKT-1::comment_mention")

	def test_comment_mention_without_comment_name_raises(self):
		for kwargs in ({}, {"comment_name": None}, {"comment_name": ""}):
			with self.subTest(kwargs=kwargs), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "comment_name"):
					queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, **kwargs)
				enqueue.assert_not_called()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))

	def test_ticket_insert_without_comment_name_enqueues(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-3", TRIGGER_TICKET_INSERT))

		enqueue.assert_called_once()
		self.assertIsNone(enqueue.call_args.kwargs["comment_name"])

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
			comment_name=None,
		)


class TestRunForTicketCommentName(FrappeTestCase):
	def test_comment_name_passed_down_to_run(self):
		with patch.object(runner, "_run") as run:
			runner.run_for_ticket("TKT-1", TRIGGER_COMMENT_MENTION, comment_name="COMMENT-9")
			runner.run_for_ticket("TKT-2", TRIGGER_TICKET_INSERT)

		self.assertEqual(
			run.call_args_list[0].args, ("TKT-1", TRIGGER_COMMENT_MENTION, "COMMENT-9"), run.call_args_list
		)
		self.assertEqual(run.call_args_list[1].args, ("TKT-2", TRIGGER_TICKET_INSERT, None))


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


class TestEnqueueScheduledJobs(FrappeTestCase):
	def test_each_job_shape(self):
		cases = (
			(
				"enqueue_daily_report_job",
				"erp_ai.agent.daily_report.run_daily_report",
				"erp_ai::daily_report",
			),
			("enqueue_weekly_kpi_job", "erp_ai.agent.kpi.run_weekly_kpi", "erp_ai::weekly_kpi"),
			(
				"enqueue_monthly_review_job",
				"erp_ai.agent.monthly_review.run_monthly_review",
				"erp_ai::monthly_review",
			),
		)
		self.assertEqual(getattr(queue, "SCHEDULED_JOB_TIMEOUT_S", None), 1200)
		for function_name, target, job_id in cases:
			with self.subTest(function=function_name), patch("frappe.enqueue") as enqueue:
				enqueue_job = getattr(queue, function_name, None)
				self.assertTrue(callable(enqueue_job), f"queue.{function_name} is missing")
				self.assertIsNone(enqueue_job())

				enqueue.assert_called_once_with(
					target,
					queue="long",
					timeout=1200,
					enqueue_after_commit=True,
					job_id=job_id,
					deduplicate=True,
				)
