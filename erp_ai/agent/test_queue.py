from unittest.mock import ANY, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket
from rq.job import JobStatus

from erp_ai.agent import queue, runner
from erp_ai.constants import (
	LOG_DOCTYPE,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_KB_DRAFT,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import stub_job_states

RUN_FOR_TICKET_PATH = "erp_ai.agent.runner.run_for_ticket"


class TestEnqueueAgentRun(FrappeTestCase):
	def setUp(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)
		# ADR-048 QĐ 2: the queue reads the RQ job state; no job exists here, and the test never reaches Redis
		stub_job_states(self, {})

	def tearDown(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)

	def test_duplicate_trigger_same_transaction_one_job(self):
		with patch("frappe.enqueue") as enqueue:
			first = queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT)
			second = queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT)
			other_trigger = queue.enqueue_agent_run(
				"TKT-1", TRIGGER_COMMENT_MENTION, message_name="MESSAGE-1"
			)
			other_ticket = queue.enqueue_agent_run("TKT-2", TRIGGER_TICKET_INSERT)

		self.assertTrue(first)
		self.assertFalse(second)
		self.assertTrue(other_trigger)
		self.assertTrue(other_ticket)
		self.assertEqual(enqueue.call_count, 3)

	def test_enqueue_parameters(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(
				queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, message_name="MESSAGE-1")
			)

		enqueue.assert_called_once_with(
			RUN_FOR_TICKET_PATH,
			queue="long",
			timeout=600,
			enqueue_after_commit=True,
			job_id="erp_ai::TKT-1::comment_mention",
			deduplicate=True,
			ticket_name="TKT-1",
			trigger=TRIGGER_COMMENT_MENTION,
			message_name="MESSAGE-1",
			# ADR-048 QĐ 2 (CHG-009): the job gets the run id its call_received row carries
			run_id=ANY,
		)

	def test_comment_mention_job_carries_message_name(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(
				queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, message_name="MESSAGE-9")
			)
			# A-U1-3: the job id stays per ticket, so a second @ai in the same transaction is merged.
			self.assertFalse(
				queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, message_name="MESSAGE-10")
			)

		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["message_name"], "MESSAGE-9")
		self.assertEqual(enqueue.call_args.kwargs["job_id"], "erp_ai::TKT-1::comment_mention")

	def test_comment_mention_without_message_name_raises(self):
		for kwargs in ({}, {"message_name": None}, {"message_name": ""}):
			with self.subTest(kwargs=kwargs), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "message_name"):
					queue.enqueue_agent_run("TKT-1", TRIGGER_COMMENT_MENTION, **kwargs)
				enqueue.assert_not_called()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))

	def test_ticket_insert_without_message_name_enqueues(self):
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(queue.enqueue_agent_run("TKT-3", TRIGGER_TICKET_INSERT))

		enqueue.assert_called_once()
		self.assertIsNone(enqueue.call_args.kwargs["message_name"])

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

	def test_requester_reply_requires_communication_name(self):
		# U6b-fixes Sửa 1: the requester-reply job is keyed by its Communication, so the name is required.
		for kwargs in (
			{},
			{"communication_name": None},
			{"communication_name": ""},
			{"communication_name": 17},
		):
			with self.subTest(kwargs=kwargs), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "communication_name"):
					queue.enqueue_agent_run("TKT-1", TRIGGER_REQUESTER_REPLY, **kwargs)
				enqueue.assert_not_called()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))

	def test_communication_name_rejected_for_other_triggers(self):
		for trigger, kwargs in (
			(TRIGGER_TICKET_INSERT, {}),
			(TRIGGER_COMMENT_MENTION, {"message_name": "MESSAGE-1"}),
			(TRIGGER_KB_DRAFT, {}),
		):
			with self.subTest(trigger=trigger), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "communication_name"):
					queue.enqueue_agent_run("TKT-1", trigger, communication_name="COMM-1", **kwargs)
				enqueue.assert_not_called()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))

	def test_requester_reply_job_id_per_communication(self):
		# U6b-fixes Sửa 1 (X-1): M2 arriving while M1's job waits or runs gets its own job, not merged away.
		self.assertEqual(queue.requester_reply_key("TKT-1", "COMM-1"), "requester_reply:TKT-1:COMM-1")
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(
				queue.enqueue_agent_run("TKT-1", TRIGGER_REQUESTER_REPLY, communication_name="COMM-1")
			)
			self.assertTrue(
				queue.enqueue_agent_run("TKT-1", TRIGGER_REQUESTER_REPLY, communication_name="COMM-2")
			)
			# The same message twice in one transaction stays one job.
			self.assertFalse(
				queue.enqueue_agent_run("TKT-1", TRIGGER_REQUESTER_REPLY, communication_name="COMM-1")
			)
			self.assertTrue(queue.enqueue_agent_run("TKT-1", TRIGGER_TICKET_INSERT))

		job_ids = [call.kwargs["job_id"] for call in enqueue.call_args_list]
		self.assertEqual(
			job_ids,
			[
				"erp_ai::TKT-1::requester_reply::COMM-1",
				"erp_ai::TKT-1::requester_reply::COMM-2",
				"erp_ai::TKT-1::ticket_insert",
			],
		)
		self.assertEqual(
			[call.kwargs.get("communication_name") for call in enqueue.call_args_list],
			["COMM-1", "COMM-2", None],
		)
		self.assertEqual({call.args[0] for call in enqueue.call_args_list}, {RUN_FOR_TICKET_PATH})
		self.assertTrue(all(call.kwargs["deduplicate"] for call in enqueue.call_args_list))

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
			message_name=None,
			# ADR-048 QĐ 2 (CHG-009): the job gets the run id its call_received row carries
			run_id=ANY,
		)


class TestEnqueueRunEvents(FrappeTestCase):
	"""CHG-009 AC-6 (design 3.5, D-3, D-9; ADR-048 QĐ 2): one read of the job state decides the row the call leaves
	and the value returned; `frappe.enqueue` is still called on every branch."""

	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(queue._clear_pending_job_ids)
		with patch("frappe.enqueue"):
			self.ticket = make_ticket(subject="ERPAI-TEST-queue events").name
		self.states = stub_job_states(self, {})

	def _new_request(self):
		"""Each call below is its own request: no pending claim, no row of an earlier call."""
		queue._clear_pending_job_ids()
		frappe.db.delete(LOG_DOCTYPE, {"ticket": self.ticket})

	def _rows(self):
		return [
			(row.entry_type, row.trigger, row.stop_reason, row.run_id)
			for row in frappe.get_all(
				LOG_DOCTYPE,
				filters={"ticket": self.ticket},
				fields=["entry_type", "trigger", "stop_reason", "run_id"],
				order_by="creation asc",
			)
		]

	def test_rows_by_job_state(self):
		calls = (
			(TRIGGER_TICKET_INSERT, {}, ""),
			(TRIGGER_COMMENT_MENTION, {"message_name": "MESSAGE-7"}, ""),
			(TRIGGER_REQUESTER_REPLY, {"communication_name": "COMM-7"}, "::COMM-7"),
			(TRIGGER_KB_DRAFT, {}, ""),
		)
		# no job, an ended job and a failed read are all a new job; only a waiting or running one is not
		new_states = (None, JobStatus.FINISHED, JobStatus.FAILED, ConnectionError("redis down"))
		fresh_run_ids = []
		for trigger, kwargs, job_suffix in calls:
			job_id = f"erp_ai::{self.ticket}::{trigger}{job_suffix}"
			for state in (*new_states, JobStatus.QUEUED, JobStatus.STARTED):
				with self.subTest(trigger=trigger, state=state):
					self._new_request()
					self.states[job_id] = state
					with patch("frappe.enqueue") as enqueue:
						queued = queue.enqueue_agent_run(self.ticket, trigger, **kwargs)

					enqueue.assert_called_once()
					self.assertEqual(enqueue.call_args.kwargs["job_id"], job_id)
					run_id = enqueue.call_args.kwargs.get("run_id")
					if state in (JobStatus.QUEUED, JobStatus.STARTED):
						code = "call_merged" if state == JobStatus.QUEUED else "call_busy"
						# AC-6: only a message (comment_mention) is told it was merged or must wait
						expected = (
							[("run_event", trigger, code, None)] if trigger == TRIGGER_COMMENT_MENTION else []
						)
						self.assertEqual(self._rows(), expected)
						self.assertFalse(queued)
						self.assertIsNone(run_id)
					else:
						self.assertEqual(self._rows(), [("run_event", trigger, "call_received", run_id)])
						self.assertTrue(queued)
						if trigger == TRIGGER_REQUESTER_REPLY:
							# ADR-033 QĐ 2: the requester-reply run keeps its event key
							self.assertEqual(run_id, queue.requester_reply_key(self.ticket, "COMM-7"))
						else:
							self.assertRegex(run_id, r"^[0-9a-f]{32}$")
							fresh_run_ids.append(run_id)
					self.assertIn("run_id", enqueue.call_args.kwargs)
		self.assertEqual(len(fresh_run_ids), 3 * len(new_states))
		self.assertEqual(len(set(fresh_run_ids)), len(fresh_run_ids))

	def test_same_job_twice_in_one_request_one_row(self):
		# D-9: the second call of one job in one transaction is the first one's: no row, False
		for trigger, kwargs in (
			(TRIGGER_COMMENT_MENTION, {"message_name": "MESSAGE-8"}),
			(TRIGGER_TICKET_INSERT, {}),
		):
			with self.subTest(trigger=trigger):
				self._new_request()
				with patch("frappe.enqueue") as enqueue:
					self.assertTrue(queue.enqueue_agent_run(self.ticket, trigger, **kwargs))
					self.assertFalse(queue.enqueue_agent_run(self.ticket, trigger, **kwargs))

				enqueue.assert_called_once()
				self.assertEqual([row[2] for row in self._rows()], ["call_received"])


class TestRunForTicketCommentName(FrappeTestCase):
	def test_message_name_passed_down_to_run(self):
		with patch.object(runner, "_run") as run:
			runner.run_for_ticket("TKT-1", TRIGGER_COMMENT_MENTION, message_name="MESSAGE-9")
			runner.run_for_ticket("TKT-2", TRIGGER_TICKET_INSERT)

		self.assertEqual(
			run.call_args_list[0].args,
			("TKT-1", TRIGGER_COMMENT_MENTION, "MESSAGE-9", None),
			run.call_args_list,
		)
		self.assertEqual(run.call_args_list[1].args, ("TKT-2", TRIGGER_TICKET_INSERT, None, None))

	def test_communication_name_passed_down_to_run(self):
		with patch.object(runner, "_run") as run:
			runner.run_for_ticket("TKT-3", TRIGGER_REQUESTER_REPLY, communication_name="COMM-4")

		self.assertEqual(run.call_args_list[0].args, ("TKT-3", TRIGGER_REQUESTER_REPLY, None, "COMM-4"))


class TestEnqueueLifecycleJob(FrappeTestCase):
	# U6b.md:135, U6b-fixes Sửa 5 (AC-43): the sixth enqueue target, one job per ticket, the shared pending claim.
	def setUp(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)

	def tearDown(self):
		frappe.flags.pop("erp_ai_pending_job_ids", None)

	def test_job_id_dedupe_and_target(self):
		self.assertEqual(getattr(queue, "LIFECYCLE_JOB_TIMEOUT_S", None), 300)
		enqueue_job = getattr(queue, "enqueue_lifecycle_job", None)
		self.assertTrue(callable(enqueue_job), "queue.enqueue_lifecycle_job is missing")
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(enqueue_job("TKT-1"))
			# Two events of one ticket in one transaction are one job; another ticket has its own.
			self.assertFalse(enqueue_job("TKT-1"))
			self.assertTrue(enqueue_job("TKT-2"))

		self.assertEqual(enqueue.call_count, 2)
		enqueue.assert_any_call(
			"erp_ai.agent.lifecycle.run_task_lifecycle",
			queue="default",
			timeout=300,
			enqueue_after_commit=True,
			job_id="erp_ai_lifecycle::TKT-1",
			deduplicate=True,
			ticket_name="TKT-1",
		)
		self.assertEqual(enqueue.call_args.kwargs["job_id"], "erp_ai_lifecycle::TKT-2")
		self.assertTrue(callable(frappe.get_attr("erp_ai.agent.lifecycle.run_task_lifecycle")))
		# The claim is released with the transaction, so the next transaction queues again.
		frappe.db.after_commit.run()
		with patch("frappe.enqueue") as enqueue:
			self.assertTrue(enqueue_job("TKT-1"))
		enqueue.assert_called_once()

	def test_rejects_bad_ticket_name(self):
		enqueue_job = getattr(queue, "enqueue_lifecycle_job", None)
		self.assertTrue(callable(enqueue_job), "queue.enqueue_lifecycle_job is missing")
		for ticket_name in ("", None, 17, b"TKT-1"):
			with self.subTest(ticket_name=ticket_name), patch("frappe.enqueue") as enqueue:
				with self.assertRaisesRegex(ValueError, "ticket_name"):
					enqueue_job(ticket_name)
				enqueue.assert_not_called()
		self.assertFalse(frappe.flags.get("erp_ai_pending_job_ids"))


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
