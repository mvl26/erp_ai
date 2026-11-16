import datetime
import json
import unicodedata
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import frappe
from frappe.core.utils import html_to_plain_text
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai import handlers, hooks
from erp_ai.agent import answer_delay, messages, queue, runner
from erp_ai.agent.tools import site_api
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.constants import (
	AGENT_USER,
	LOG_DOCTYPE,
	LOGGER_NAME,
	MESSAGE_DOCTYPE,
	TRIGGER_KB_DRAFT,
	TRIGGER_REQUESTER_REPLY,
)
from erp_ai.test_utils import (
	FakeGateway,
	clear_lesson_store,
	keep_agent_settings,
	make_log_entry,
	make_model_result,
	record_status_signals,
	set_agent_settings,
)

PREFIX = "ERPAI-TEST-"
RUN_FOR_TICKET_PATH = "erp_ai.agent.runner.run_for_ticket"
KEYWORD = "@ai"
EXCLUDED_TEAM = f"{PREFIX}Excluded"
OPEN_TEAM = f"{PREFIX}Open"
TICKET_TYPE = f"{PREFIX}Type"


def _agent_calls(enqueue_mock):
	return [call for call in enqueue_mock.call_args_list if call.args and call.args[0] == RUN_FOR_TICKET_PATH]


def _ensure_team(name):
	if frappe.db.exists("HD Team", name):
		return
	frappe.get_doc({"doctype": "HD Team", "team_name": name, "users": [{"user": "Administrator"}]}).insert(
		ignore_permissions=True
	)


def _ensure_ticket_type(name):
	if frappe.db.exists("HD Ticket Type", name):
		return
	frappe.get_doc({"doctype": "HD Ticket Type", "name": name}).insert(ignore_permissions=True)


class HandlerTestCase(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert makes an Assignment Rule cached in Redis; the DB rollback leaves
		# that entry stale. Registered first so it runs AFTER the rollback.
		# (Never delete_doc HD Team: HDTeam.on_trash commits the transaction.)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")

		# Nothing a handler or a failing run reports may leave an Error Log row behind.
		log_error = patch.object(frappe, "log_error")
		log_error.start()
		self.addCleanup(log_error.stop)

		# A run started by a handler test must neither publish to Redis nor sleep for real.
		record_status_signals(self)
		sleep_patch = patch.object(answer_delay, "_sleep")
		sleep_patch.start()
		self.addCleanup(sleep_patch.stop)

		self.gateway = FakeGateway()
		gateway_patch = patch("erp_ai.gateway.call_model", self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)

		enqueue_patch = patch.object(frappe, "enqueue")
		self.enqueue = enqueue_patch.start()
		self.addCleanup(enqueue_patch.stop)

		set_agent_settings(
			enabled=1,
			trigger_keyword=KEYWORD,
			excluded_teams=EXCLUDED_TEAM,
			answer_delay_min_s=0,
			answer_delay_max_s=0,
		)
		for team in (EXCLUDED_TEAM, OPEN_TEAM):
			_ensure_team(team)
		_ensure_ticket_type(TICKET_TYPE)

	def _jobs(self):
		return _agent_calls(self.enqueue)

	def _ticket_without_job(self, **values):
		"""Create a ticket while the agent is off, then restore the previous state."""
		was_enabled = frappe.db.get_single_value("ERP AI Setting", "enabled")
		set_agent_settings(enabled=0)
		ticket = make_ticket(subject=f"{PREFIX}ticket", **values)
		set_agent_settings(enabled=was_enabled)
		self.enqueue.reset_mock()
		return ticket

	def _messages(self, ticket_name):
		return frappe.get_all(
			MESSAGE_DOCTYPE,
			filters={"ticket": ticket_name},
			fields=["name", "content", "owner", "source_comment"],
		)

	def _comment(self, ticket_name, content, comment_type="Comment", reference_doctype="HD Ticket"):
		comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": comment_type,
				"reference_doctype": reference_doctype,
				"reference_name": ticket_name,
				"content": content,
			}
		)
		comment.insert(ignore_permissions=True)
		return comment


class TestTicketHandlers(HandlerTestCase):
	def test_new_unclassified_ticket_enqueues_one_job(self):
		ticket = make_ticket(subject=f"{PREFIX}unclassified")

		# Helpdesk filled defaults before after_insert; the job must still be queued.
		self.assertTrue(ticket.priority)
		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		kwargs = jobs[0].kwargs
		self.assertEqual(kwargs["queue"], "long")
		self.assertEqual(kwargs["timeout"], 600)
		self.assertIs(kwargs["enqueue_after_commit"], True)
		self.assertIs(kwargs["deduplicate"], True)
		self.assertEqual(kwargs["ticket_name"], ticket.name)
		self.assertEqual(kwargs["trigger"], "ticket_insert")
		self.assertEqual(kwargs["job_id"], f"erp_ai::{ticket.name}::ticket_insert")
		self.assertEqual(self.gateway.call_count, 0)

	def test_before_insert_sets_prefilled_flag_only_when_all_fields_given(self):
		full = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": f"{PREFIX}flag",
				"ticket_type": TICKET_TYPE,
				"agent_group": OPEN_TEAM,
				"priority": "Medium",
			}
		)
		handlers.ticket_before_insert(full)
		self.assertIs(full.flags.erp_ai_prefilled, True)

		partial = frappe.get_doc({"doctype": "HD Ticket", "subject": f"{PREFIX}flag", "priority": "Medium"})
		handlers.ticket_before_insert(partial)
		self.assertIs(partial.flags.erp_ai_prefilled, False)

	def test_disabled_agent_new_ticket_no_job_no_model_call(self):
		set_agent_settings(enabled=0)

		make_ticket(subject=f"{PREFIX}disabled")

		self.assertEqual(self._jobs(), [])
		self.assertEqual(self.enqueue.call_count, 0)
		self.assertEqual(self.gateway.call_count, 0)

	def test_prefilled_ticket_no_job(self):
		make_ticket(
			subject=f"{PREFIX}prefilled",
			ticket_type=TICKET_TYPE,
			agent_group=OPEN_TEAM,
			priority="Medium",
		)

		self.assertEqual(self._jobs(), [])

	def test_partially_prefilled_ticket_enqueues_job(self):
		make_ticket(subject=f"{PREFIX}partial", ticket_type=TICKET_TYPE, priority="Medium")

		self.assertEqual(len(self._jobs()), 1)

	def test_agent_created_ticket_and_comment_no_job(self):
		frappe.set_user(AGENT_USER)
		ticket = make_ticket(subject=f"{PREFIX}by agent")
		self.assertEqual(ticket.owner, AGENT_USER)
		self.assertEqual(self._jobs(), [])

		comment = self._comment(ticket.name, f"{KEYWORD} please look")
		self.assertEqual(comment.owner, AGENT_USER)
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])

	def test_opt_out_or_excluded_team_no_job_no_model_call(self):
		make_ticket(subject=f"{PREFIX}opt out", ai_opt_out=1)
		self.assertEqual(self._jobs(), [])

		make_ticket(subject=f"{PREFIX}excluded", agent_group=EXCLUDED_TEAM)
		self.assertEqual(self._jobs(), [])

		ticket = self._ticket_without_job(ai_opt_out=1)
		self._comment(ticket.name, f"{KEYWORD} hello")
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])

		other = self._ticket_without_job(agent_group=EXCLUDED_TEAM)
		self._comment(other.name, f"{KEYWORD} hello")
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(other.name), [])

		self.assertEqual(self.gateway.call_count, 0)

	def test_open_team_ticket_enqueues_job(self):
		make_ticket(subject=f"{PREFIX}open team", agent_group=OPEN_TEAM)

		self.assertEqual(len(self._jobs()), 1)

	def test_decisions_are_logged_without_ticket_content(self):
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger) as get_logger:
			make_ticket(subject=f"{PREFIX}SECRET subject", description="SECRET description")
			set_agent_settings(enabled=0)
			make_ticket(subject=f"{PREFIX}SECRET subject 2", description="SECRET description")

		get_logger.assert_called_with(LOGGER_NAME)
		self.assertGreaterEqual(logger.info.call_count, 2)
		logged = " ".join(str(arg) for call in logger.info.call_args_list for arg in call.args)
		self.assertNotIn("SECRET", logged)
		self.assertIn("ticket_insert", logged)

	def test_save_ticket_and_comment_make_no_model_call(self):
		ticket = make_ticket(subject=f"{PREFIX}no model call")
		ticket.reload()
		ticket.subject = f"{PREFIX}no model call (edited)"
		ticket.save(ignore_permissions=True)
		self._comment(ticket.name, f"{KEYWORD} help")

		self.assertEqual(self.gateway.call_count, 0)
		for call in self.enqueue.call_args_list:
			self.assertEqual(call.args[0], RUN_FOR_TICKET_PATH)

	def test_run_for_ticket_calls_classify_once(self):
		ticket = self._ticket_without_job()
		self.gateway.results.append(make_model_result(text="{}"))
		set_agent_settings(enabled=1, permission_level="L0")

		runner.run_for_ticket(ticket.name, "ticket_insert")

		self.assertEqual(self.gateway.call_count, 1)
		call = self.gateway.calls[0]
		self.assertEqual(call["task"], "classify")
		self.assertEqual(call["max_tokens"], 600)
		self.assertTrue(call["system"])
		self.assertTrue(call["messages"])


class TestCommentHandler(HandlerTestCase):
	def test_comment_keyword_case_insensitive(self):
		ticket = self._ticket_without_job()

		comment = self._comment(ticket.name, "Xin chào, nhờ @AI xem giúp")

		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0].kwargs["ticket_name"], ticket.name)
		self.assertEqual(jobs[0].kwargs["trigger"], "comment_mention")
		self.assertEqual(jobs[0].kwargs["job_id"], f"erp_ai::{ticket.name}::comment_mention")
		self.assertEqual(comment.comment_type, "Comment")

	def test_mention_copies_comment_into_one_chat_message_and_one_job(self):
		ticket = self._ticket_without_job()

		comment = self._comment(ticket.name, f"{KEYWORD} xem <b>giúp</b><script>x()</script>")

		rows = self._messages(ticket.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].source_comment, comment.name)
		self.assertEqual(rows[0].owner, comment.owner)
		# stored verbatim (Code field): the markup stripping is html_to_plain_text's job
		self.assertEqual(rows[0].content, html_to_plain_text(comment.content))
		self.assertNotIn("<b>", rows[0].content)
		self.assertIn("giúp", rows[0].content)
		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0].kwargs["message_name"], rows[0].name)
		self.assertEqual(jobs[0].kwargs["job_id"], f"erp_ai::{ticket.name}::comment_mention")

	def test_panel_style_chat_message_enqueues_once(self):
		ticket = self._ticket_without_job()
		frappe.set_user("Administrator")

		name = messages.add_message(ticket.name, "xem giúp", trusted=True)

		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0].kwargs["message_name"], name)
		self.assertEqual(jobs[0].kwargs["trigger"], "comment_mention")

	def test_two_chat_messages_same_transaction_one_job(self):
		ticket = self._ticket_without_job()

		messages.add_message(ticket.name, "một", trusted=True)
		messages.add_message(ticket.name, "hai", trusted=True)

		self.assertEqual(len(self._jobs()), 1)

	def test_bot_message_never_enqueues(self):
		ticket = self._ticket_without_job()

		frappe.set_user(AGENT_USER)
		messages.add_message(ticket.name, "bot nói", trusted=True)
		self.assertEqual(self._jobs(), [])

		def no_db(*args, **kwargs):
			raise AssertionError("the bot's own message must return before any database read")

		doc = frappe.get_doc({"doctype": MESSAGE_DOCTYPE, "ticket": ticket.name, "content": "x"})
		doc.owner = AGENT_USER
		with (
			patch.object(frappe.db, "get_value", side_effect=no_db),
			patch.object(frappe.db, "get_single_value", side_effect=no_db),
		):
			handlers.message_after_insert(doc)
		self.assertEqual(self._jobs(), [])

	def test_message_with_agent_disabled_or_not_sendable_no_job(self):
		ticket = self._ticket_without_job()
		set_agent_settings(enabled=0)
		messages.add_message(ticket.name, "xem giúp", trusted=True)
		self.assertEqual(self._jobs(), [])

		set_agent_settings(enabled=1)
		opted_out = self._ticket_without_job(ai_opt_out=1)
		messages.add_message(opted_out.name, "xem giúp", trusted=True)
		excluded = self._ticket_without_job(agent_group=EXCLUDED_TEAM)
		messages.add_message(excluded.name, "xem giúp", trusted=True)
		self.assertEqual(self._jobs(), [])

	def test_mention_with_no_text_left_is_skipped_and_the_comment_is_saved(self):
		ticket = self._ticket_without_job()

		# the keyword sat only inside markup: nothing is left to say once the markup is gone
		with patch.object(handlers, "html_to_plain_text", return_value=" \n"):
			comment = self._comment(ticket.name, f"{KEYWORD} xem giúp")

		self.assertTrue(frappe.db.exists("Comment", comment.name))
		self.assertEqual(self._messages(ticket.name), [])
		self.assertEqual(self._jobs(), [])

	def test_comment_without_keyword_no_job(self):
		ticket = self._ticket_without_job()

		self._comment(ticket.name, "Không nhắc ai cả")

		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])

	def test_comment_with_agent_disabled_no_job(self):
		ticket = self._ticket_without_job()
		set_agent_settings(enabled=0)

		self._comment(ticket.name, f"{KEYWORD} xem giúp")

		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])
		self.assertEqual(self.gateway.call_count, 0)

	def test_comment_with_empty_keyword_setting_no_job(self):
		ticket = self._ticket_without_job()
		set_agent_settings(trigger_keyword="")

		self._comment(ticket.name, "any content")

		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])

	def test_comment_author_is_owner_not_spoofable_fields(self):
		ticket = self._ticket_without_job()
		doc = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "HD Ticket",
				"reference_name": ticket.name,
				"content": f"{KEYWORD} help",
				"comment_email": AGENT_USER,
				"comment_by": AGENT_USER,
			}
		)
		doc.owner = "Administrator"
		doc.name = f"{PREFIX}comment"

		handlers.comment_after_insert(doc)

		rows = self._messages(ticket.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].owner, "Administrator")
		self.assertEqual(rows[0].source_comment, doc.name)
		self.assertEqual(len(self._jobs()), 1)

	def test_comment_on_other_doctype_or_type_no_job(self):
		ticket = self._ticket_without_job()
		other_doctype = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": "HD Team",
				"reference_name": OPEN_TEAM,
				"content": f"{KEYWORD} help",
			}
		)
		info_comment = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "HD Ticket",
				"reference_name": ticket.name,
				"content": f"{KEYWORD} help",
			}
		)

		def no_db(*args, **kwargs):
			raise AssertionError("the early return must not touch the database")

		with (
			patch.object(frappe.db, "sql", side_effect=no_db),
			patch.object(frappe.db, "get_value", side_effect=no_db),
			patch.object(frappe.db, "get_single_value", side_effect=no_db),
			patch.object(frappe.db, "exists", side_effect=no_db),
			patch.object(frappe, "get_all", side_effect=no_db),
			patch.object(frappe, "logger", side_effect=no_db),
		):
			handlers.comment_after_insert(other_doctype)
			handlers.comment_after_insert(info_comment)

		self.assertEqual(self._jobs(), [])

		# End to end: real inserts on the same hook path.
		self._comment(OPEN_TEAM, f"{KEYWORD} help", reference_doctype="HD Team")
		self._comment(ticket.name, f"{KEYWORD} help", comment_type="Info")
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._messages(ticket.name), [])

	def test_comment_decisions_are_logged_without_content(self):
		ticket = self._ticket_without_job()
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._comment(ticket.name, f"{KEYWORD} SECRET body")
			self._comment(ticket.name, "SECRET body without keyword")

		self.assertGreaterEqual(logger.info.call_count, 2)
		logged = " ".join(str(arg) for call in logger.info.call_args_list for arg in call.args)
		self.assertNotIn("SECRET", logged)
		self.assertIn("comment_mention", logged)
		self.assertIn("copied", logged)


class TestExcludedTitle(HandlerTestCase):
	"""A ticket the send predicate refuses is not queued; the logger line carries the refusal code only (AC-9 a)."""

	PREFIX_LINE = "[HR]"

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)
		set_agent_settings(excluded_title_prefixes=self.PREFIX_LINE)
		enqueue_patch = patch.object(handlers, "enqueue_agent_run")
		self.enqueue_agent_run = enqueue_patch.start()
		self.addCleanup(enqueue_patch.stop)

	@staticmethod
	def _lines(logger):
		return [str(arg) for call in logger.info.call_args_list for arg in call.args]

	def test_prefixed_ticket_not_enqueued_and_logged_once(self):
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			ticket = make_ticket(subject=f"{self.PREFIX_LINE} SECRET salary", description="SECRET body")

		self.assertEqual(self.enqueue_agent_run.call_count, 0)
		lines = self._lines(logger)
		refused = [line for line in lines if "not_sendable:excluded_title" in line]
		self.assertEqual(len(refused), 1, lines)
		self.assertIn(f"ticket={ticket.name}", refused[0])
		self.assertIn("trigger=ticket_insert", refused[0])
		self.assertNotIn("SECRET", " ".join(lines))

	def test_keyword_comment_on_prefixed_ticket_logs_the_code(self):
		ticket = make_ticket(subject=f"{self.PREFIX_LINE} SECRET salary")
		self.enqueue_agent_run.reset_mock()
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			self._comment(ticket.name, f"{KEYWORD} SECRET question")

		self.assertEqual(self.enqueue_agent_run.call_count, 0)
		lines = self._lines(logger)
		refused = [line for line in lines if "not_sendable:excluded_title" in line]
		self.assertEqual(len(refused), 1, lines)
		self.assertIn("trigger=comment_mention", refused[0])
		self.assertNotIn("SECRET", " ".join(lines))


class TestHumanCorrection(HandlerTestCase):
	"""AC-11: a person's change to the classification is recorded on the ticket's reference `classify` row, its
	first row with a result (ADR-037 QĐ 5, T114): the row the ERP AI Accuracy report reads."""

	FIRST_CORRECTION_AT = "2026-01-01 08:00:00"
	PAST = "2020-01-01 00:00:00"

	def _classified_ticket(self, **log_fields):
		ticket = self._ticket_without_job(priority="Low")
		fields = {"ticket": ticket.name, "entry_type": "classify", "predicted_category": "A"}
		fields.update(log_fields)
		return ticket, make_log_entry(**fields)

	def _log(self, name):
		return frappe.db.get_value(
			LOG_DOCTYPE,
			name,
			["human_corrected_to", "human_corrected_by", "human_corrected_at"],
			as_dict=True,
		)

	def _classified_by(self, ticket):
		return frappe.db.get_value("HD Ticket", ticket.name, "ai_classified_by")

	def _save_priority(self, ticket, priority):
		ticket.reload()
		ticket.priority = priority
		ticket.save(ignore_permissions=True)

	def test_two_result_rows_correction_lands_on_first(self):
		# ADR-037 QĐ 5 (T114): a ticket classified again has two rows with a result; the correction goes on the first
		# (it replaces "updates the latest row": the handler moved from the latest row to the reference row)
		ticket, first_log = self._classified_ticket(run_id=f"{PREFIX}old")
		later_log = make_log_entry(
			ticket=ticket.name,
			entry_type="classify",
			predicted_category="B",
			run_id=f"{PREFIX}new",
		)
		frappe.db.set_value(LOG_DOCTYPE, first_log, "creation", self.PAST, update_modified=False)
		self.assertEqual(handlers.reference_classify_row(ticket.name), first_log)

		self._save_priority(ticket, "High")

		first = self._log(first_log)
		self.assertEqual(
			json.loads(first.human_corrected_to),
			{"ticket_type": ticket.ticket_type, "agent_group": ticket.agent_group, "priority": "High"},
		)
		self.assertEqual(first.human_corrected_by, "Administrator")
		self.assertTrue(first.human_corrected_at)
		self.assertEqual(self._classified_by(ticket), "Người")
		self.assertIsNone(self._log(later_log).human_corrected_to)

		# Second correction: the value is the last one, the time stays the first one.
		frappe.db.set_value(
			LOG_DOCTYPE, first_log, "human_corrected_at", self.FIRST_CORRECTION_AT, update_modified=False
		)
		self._save_priority(ticket, "Urgent")

		second = self._log(first_log)
		self.assertEqual(json.loads(second.human_corrected_to)["priority"], "Urgent")
		self.assertEqual(str(second.human_corrected_at), self.FIRST_CORRECTION_AT)
		self.assertIsNone(self._log(later_log).human_corrected_to)

	def test_reference_row_is_the_first_with_a_result(self):
		# a failed run's row (no category) and a row of another entry type are never the reference
		ticket = self._ticket_without_job(priority="Low")
		self.assertIsNone(handlers.reference_classify_row(ticket.name))
		failed = make_log_entry(ticket=ticket.name, entry_type="classify", run_id=f"{PREFIX}failed")
		reason = make_log_entry(ticket=ticket.name, entry_type="reason", turn=1, run_id=f"{PREFIX}failed")
		for name in (failed, reason):
			frappe.db.set_value(LOG_DOCTYPE, name, "creation", self.PAST, update_modified=False)
		self.assertIsNone(handlers.reference_classify_row(ticket.name))
		result = make_log_entry(
			ticket=ticket.name, entry_type="classify", predicted_category="C", run_id=f"{PREFIX}ok"
		)
		make_log_entry(
			ticket=ticket.name, entry_type="classify", predicted_category="A", run_id=f"{PREFIX}again"
		)
		frappe.db.set_value(LOG_DOCTYPE, result, "creation", self.FIRST_CORRECTION_AT, update_modified=False)
		self.assertEqual(handlers.reference_classify_row(ticket.name), result)

	def test_correction_does_not_touch_modified_of_the_log(self):
		ticket, log = self._classified_ticket()
		frappe.db.set_value(LOG_DOCTYPE, log, "modified", "2026-01-01 00:00:00", update_modified=False)

		self._save_priority(ticket, "High")

		self.assertEqual(str(frappe.db.get_value(LOG_DOCTYPE, log, "modified")), "2026-01-01 00:00:00")

	def test_agent_correction_not_recorded(self):
		ticket, log = self._classified_ticket()
		frappe.set_user(AGENT_USER)

		self._save_priority(ticket, "High")

		frappe.set_user("Administrator")
		self.assertIsNone(self._log(log).human_corrected_to)
		self.assertNotEqual(self._classified_by(ticket), "Người")

	def test_latest_classify_row_wins_over_newer_reason_row(self):
		ticket, classify_log = self._classified_ticket(run_id=f"{PREFIX}classify")
		reason_log = make_log_entry(
			ticket=ticket.name, entry_type="reason", turn=1, run_id=f"{PREFIX}classify"
		)
		frappe.db.set_value(LOG_DOCTYPE, classify_log, "creation", self.PAST, update_modified=False)

		self._save_priority(ticket, "High")

		self.assertEqual(json.loads(self._log(classify_log).human_corrected_to)["priority"], "High")
		self.assertIsNone(self._log(reason_log).human_corrected_to)
		self.assertEqual(self._classified_by(ticket), "Người")

	def _save_as_helpdesk_agent(self, **changes):
		"""A real form save by a user holding only the `Agent` role, no ignore_permissions."""
		email = f"{PREFIX}agent@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": f"{PREFIX}agent",
				"send_welcome_email": 0,
				"roles": [{"role": "Agent"}],
			}
		).insert(ignore_permissions=True)
		ticket, log = self._classified_ticket()
		frappe.set_user(email)
		doc = frappe.get_doc("HD Ticket", ticket.name)
		doc.update(changes)
		doc.save()
		frappe.set_user("Administrator")
		return email, ticket, log

	def test_helpdesk_agent_save_is_recorded(self):
		email, ticket, log = self._save_as_helpdesk_agent(priority="High")

		self.assertEqual(self._classified_by(ticket), "Người")
		recorded = self._log(log)
		self.assertEqual(json.loads(recorded.human_corrected_to)["priority"], "High")
		self.assertEqual(recorded.human_corrected_by, email)

	def test_save_by_user_without_permlevel_8_access_still_records_correction(self):
		# Frappe resets permlevel 8 fields (ai_*) before the validate hook runs, so the hook's
		# value must survive. Control: a permlevel 8 field this user typed is reset in the same save.
		real = frappe.model.document.Document.get_permlevel_access

		def without_level_8(doc, permission_type="write"):
			return [level for level in real(doc, permission_type) if level != 8]

		with patch("frappe.model.document.Document.get_permlevel_access", without_level_8):
			email, ticket, log = self._save_as_helpdesk_agent(priority="High", ai_confidence="Cao")

		self.assertFalse(frappe.db.get_value("HD Ticket", ticket.name, "ai_confidence"))
		self.assertEqual(self._classified_by(ticket), "Người")
		self.assertEqual(self._log(log).human_corrected_by, email)

	def test_ticket_without_classify_log_saves_without_error(self):
		# AC-21 changed the FEAT-001 rule "no prediction yet → skip": the person is marked (NFR-8).
		ticket = self._ticket_without_job(priority="Low")
		skip_log = make_log_entry(ticket=ticket.name, entry_type="skip", run_id=f"{PREFIX}skip")

		self._save_priority(ticket, "High")

		self.assertEqual(frappe.db.get_value("HD Ticket", ticket.name, "priority"), "High")
		self.assertEqual(self._classified_by(ticket), "Người")
		self.assertIsNone(self._log(skip_log).human_corrected_to)

	def test_log_without_predicted_category_not_recorded(self):
		# The row has nothing to correct, so it stays as it is; the person is still marked (AC-21, NFR-8).
		ticket, log = self._classified_ticket(predicted_category="")

		self._save_priority(ticket, "High")

		self.assertIsNone(self._log(log).human_corrected_to)
		self.assertEqual(self._classified_by(ticket), "Người")

	def test_edit_before_first_log_marks_human(self):
		ticket = self._ticket_without_job(priority="Low")
		self.assertEqual(frappe.db.count(LOG_DOCTYPE, {"ticket": ticket.name}), 0)
		logger = MagicMock()

		with patch.object(frappe, "logger", return_value=logger):
			self._save_priority(ticket, "High")

		self.assertEqual(frappe.db.get_value("HD Ticket", ticket.name, "priority"), "High")
		self.assertEqual(self._classified_by(ticket), "Người")
		self.assertEqual(frappe.db.count(LOG_DOCTYPE, {"ticket": ticket.name}), 0)
		self.assertFalse(ticket.flags.erp_ai_human_corrected)
		logged = [str(arg) for call in logger.info.call_args_list for arg in call.args]
		self.assertIn(
			f"erp_ai handler ticket={ticket.name} trigger=human_correction recorded: human_changed_before_prediction",
			logged,
		)

	def test_record_tool_write_is_not_human(self):
		# Only the session tells the bot's write from a person's: a record tool runs as AGENT_USER.
		for with_log in (True, False):
			with self.subTest(with_log=with_log):
				if with_log:
					ticket, log = self._classified_ticket(run_id=f"{PREFIX}record")
				else:
					ticket, log = self._ticket_without_job(priority="Low"), None
				context = ToolContext(
					ticket_name=ticket.name,
					effective_level="L3",
					instructor=None,
					run_id=f"{PREFIX}record",
					category_mapping={},
					agent_user=AGENT_USER,
					record_tools=True,
				)
				frappe.set_user(AGENT_USER)
				result = site_api.update_record(
					{"doctype": "HD Ticket", "name": ticket.name, "values": {"priority": "High"}}, context
				)
				frappe.set_user("Administrator")

				self.assertTrue(result["ok"], result)
				self.assertEqual(frappe.db.get_value("HD Ticket", ticket.name, "priority"), "High")
				self.assertNotEqual(self._classified_by(ticket), "Người")
				if log:
					self.assertIsNone(self._log(log).human_corrected_to)

	def test_change_outside_classification_fields_not_recorded(self):
		ticket, log = self._classified_ticket()

		ticket.reload()
		ticket.subject = f"{PREFIX}renamed"
		ticket.save(ignore_permissions=True)

		self.assertIsNone(self._log(log).human_corrected_to)
		self.assertNotEqual(self._classified_by(ticket), "Người")

	def test_on_update_skips_insert(self):
		ticket, log = self._classified_ticket()
		ticket.reload()
		ticket.flags.erp_ai_human_corrected = log
		ticket.flags.in_insert = True

		handlers.ticket_on_update(ticket)

		self.assertIsNone(self._log(log).human_corrected_to)

	def test_validate_clears_a_stale_flag_on_an_early_return(self):
		ticket, log = self._classified_ticket()
		ticket.reload()
		ticket.load_doc_before_save()
		ticket.flags.erp_ai_human_corrected = log

		handlers.ticket_validate(ticket)

		self.assertFalse(ticket.flags.erp_ai_human_corrected)

	def test_flag_is_consumed_so_a_plain_resave_changes_nothing(self):
		ticket, log = self._classified_ticket()
		self._save_priority(ticket, "High")
		frappe.db.set_value(LOG_DOCTYPE, log, "human_corrected_to", "", update_modified=False)

		ticket.reload()
		ticket.subject = f"{PREFIX}resaved"
		ticket.save(ignore_permissions=True)

		self.assertFalse(self._log(log).human_corrected_to)

	def test_correction_decisions_are_logged_without_content(self):
		ticket, _log = self._classified_ticket()
		ticket.reload()
		ticket.subject = f"{PREFIX}SECRET subject"
		ticket.priority = "High"
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			ticket.save(ignore_permissions=True)

		self.assertGreaterEqual(logger.info.call_count, 1)
		logged = " ".join(str(arg) for call in logger.info.call_args_list for arg in call.args)
		self.assertNotIn("SECRET", logged)
		self.assertIn("human_correction", logged)


CREATED_LABELS_FIELD = "ai_created_labels"
CREATED_LABELS_FLAG = "erp_ai_created_labels"


def _labels(values):
	return json.dumps(values, ensure_ascii=False, sort_keys=True) if values else ""


def _ensure_user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(role)
	return email


class TestCreatedLabels(HandlerTestCase):
	"""AC-21, AC-19: the classification fields the person typed at creation, fixed for the ticket's life."""

	CUSTOMER = f"{PREFIX}labels-customer@example.com"
	AGENT = f"{PREFIX}labels-agent@example.com"

	def _new_ticket(self, **values):
		return frappe.get_doc(
			{"doctype": "HD Ticket", "subject": f"{PREFIX}labels", "description": "labels", **values}
		)

	def _stored(self, ticket_name):
		return frappe.db.get_value("HD Ticket", ticket_name, CREATED_LABELS_FIELD) or ""

	def _insert_as(self, user, permlevels=None, **values):
		"""Insert as `user` through the permission checks; `permlevels` fixes the write levels it holds."""
		frappe.set_user(user)
		doc = self._new_ticket(**values)
		if permlevels is None:
			doc.insert()
		else:
			with patch("frappe.model.document.Document.get_permlevel_access", return_value=permlevels):
				self.assertEqual(doc.get_permlevel_access("write"), permlevels)
				doc.insert()
		frappe.set_user("Administrator")
		return doc

	def test_insert_records_typed_fields_only(self):
		self.assertEqual(getattr(handlers, "CREATED_LABELS_FIELD", None), CREATED_LABELS_FIELD)
		self.assertEqual(getattr(handlers, "CREATED_LABELS_FLAG", None), CREATED_LABELS_FLAG)
		every = {"ticket_type": TICKET_TYPE, "agent_group": OPEN_TEAM, "priority": "High"}
		keys = list(every)
		subsets = [()] + [(k,) for k in keys] + [tuple(k for k in keys if k != skip) for skip in keys]
		subsets.append(tuple(keys))
		self.assertEqual(len(subsets), 8)
		for subset in subsets:
			typed = {key: every[key] for key in subset}
			with self.subTest(typed=typed):
				# before_insert only keeps the typed set in the flag; the field is written at validate.
				doc = self._new_ticket(**typed)
				with (
					patch.object(frappe.db, "set_value") as set_value,
					patch.object(type(doc), "save") as save,
				):
					handlers.ticket_before_insert(doc)
					self.assertEqual(doc.flags.get(CREATED_LABELS_FLAG), typed)
					self.assertFalse(doc.get(CREATED_LABELS_FIELD))
					doc.set("__islocal", 1)
					handlers.ticket_validate(doc)
				self.assertEqual(doc.get(CREATED_LABELS_FIELD) or "", _labels(typed))
				set_value.assert_not_called()
				save.assert_not_called()

				ticket = make_ticket(subject=f"{PREFIX}labels", **typed)
				self.assertEqual(self._stored(ticket.name), _labels(typed))

	def test_customer_portal_insert_records_typed_fields(self):
		customer = _ensure_user(self.CUSTOMER, "HD Customer")
		frappe.set_user(customer)
		self.assertNotIn(8, self._new_ticket().get_permlevel_access("write"))
		# Seed the template instead of reading the site's: it lets a customer fill `priority`.
		template = patch(
			"helpdesk.helpdesk.doctype.hd_ticket.hd_ticket.HDTicket.customer_writable_rows",
			return_value=[frappe._dict(fieldname="priority")],
		)

		with template:
			doc = self._insert_as(customer, priority="High")

		self.assertEqual(frappe.db.get_value("HD Ticket", doc.name, "via_customer_portal"), 1)
		self.assertEqual(self._stored(doc.name), _labels({"priority": "High"}))

	def test_user_without_level8_insert_records_typed_fields(self):
		# The classification fields are permlevel 7 on HD Ticket; level 8 is the one withheld.
		agent = _ensure_user(self.AGENT, "Agent")
		typed = {"ticket_type": TICKET_TYPE, "priority": "High"}

		doc = self._insert_as(agent, permlevels=[0, 7], **typed)

		self.assertEqual(self._stored(doc.name), _labels(typed))

	def test_level8_user_client_value_overwritten(self):
		agent = _ensure_user(self.AGENT, "Agent")
		forged = json.dumps({"ticket_type": TICKET_TYPE, "agent_group": OPEN_TEAM, "priority": "Low"})

		typed = self._insert_as(
			agent, permlevels=[0, 7, 8], priority="High", **{CREATED_LABELS_FIELD: forged}
		)
		untyped = self._insert_as(agent, permlevels=[0, 7, 8], **{CREATED_LABELS_FIELD: forged})

		self.assertEqual(self._stored(typed.name), _labels({"priority": "High"}))
		self.assertEqual(self._stored(untyped.name), "")

	def test_only_values_still_on_ticket_recorded(self):
		for typed, on_ticket, expected in (
			({"priority": "High"}, {"priority": "Medium"}, ""),
			(
				{"priority": "High", "ticket_type": TICKET_TYPE},
				{"priority": "Medium", "ticket_type": TICKET_TYPE},
				_labels({"ticket_type": TICKET_TYPE}),
			),
		):
			with self.subTest(typed=typed):
				doc = frappe.new_doc("HD Ticket")
				doc.update(on_ticket)
				doc.flags[CREATED_LABELS_FLAG] = typed

				handlers.ticket_validate(doc)

				self.assertEqual(doc.get(CREATED_LABELS_FIELD) or "", expected)

	def test_created_labels_frozen_after_insert(self):
		ticket = make_ticket(subject=f"{PREFIX}labels", priority="High")
		recorded = _labels({"priority": "High"})
		self.assertEqual(self._stored(ticket.name), recorded)
		forged = json.dumps({"priority": "Low"})

		for user in ("Administrator", AGENT_USER):
			with self.subTest(user=user):
				frappe.set_user(user)
				doc = frappe.get_doc("HD Ticket", ticket.name)
				doc.set(CREATED_LABELS_FIELD, forged)
				doc.save(ignore_permissions=True)
				frappe.set_user("Administrator")
				self.assertEqual(self._stored(ticket.name), recorded)

		# A later save that changes a typed field does not recompute the record either.
		doc = frappe.get_doc("HD Ticket", ticket.name)
		doc.priority = "Low"
		doc.save(ignore_permissions=True)
		self.assertEqual(self._stored(ticket.name), recorded)

		# The freeze works on the doc being saved: no extra save, no db.set_value on HD Ticket.
		doc = frappe.get_doc("HD Ticket", ticket.name)
		doc.load_doc_before_save()
		doc.set(CREATED_LABELS_FIELD, forged)
		with patch.object(frappe.db, "set_value") as set_value, patch.object(type(doc), "save") as save:
			handlers.ticket_validate(doc)
		self.assertEqual(doc.get(CREATED_LABELS_FIELD), recorded)
		set_value.assert_not_called()
		save.assert_not_called()


class TestTicketNameNotReused(HandlerTestCase):
	"""Deleting the newest ticket must not hand its name, nor its kept ERP AI Log rows (D7), to the next ticket.

	Frappe's `delete_doc` moves the `.####` counter back when the newest ticket is deleted (C0F R6b).
	"""

	def _delete_ticket(self, name):
		frappe.delete_doc("HD Ticket", name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("HD Ticket", name))

	def test_next_ticket_after_deleting_the_newest_gets_a_new_name(self):
		deleted = self._ticket_without_job().name
		self._delete_ticket(deleted)
		self.assertNotEqual(self._ticket_without_job().name, deleted)

	def test_next_ticket_does_not_see_the_deleted_tickets_log_rows(self):
		deleted = self._ticket_without_job().name
		row = make_log_entry(ticket=deleted, entry_type="classify")
		self._delete_ticket(deleted)
		# D7: the audit row stays, under the deleted ticket's name.
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, row, "ticket"), deleted)

		following = self._ticket_without_job().name
		self.assertNotIn(row, frappe.get_all(LOG_DOCTYPE, filters={"ticket": following}, pluck="name"))


REPLY_DAY = datetime.datetime(2026, 11, 2, 9, 0)
HOUR = datetime.timedelta(hours=1)


class RequesterReplyTestCase(HandlerTestCase):
	"""Communications stored as is (no Helpdesk hook runs); `communication_on_update` is called the way the
	Communication `on_update` hook calls it."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)

	def _requester_ticket(self, **values):
		requester = f"{PREFIX.lower()}requester-{frappe.generate_hash(length=8).lower()}@example.com"
		return self._ticket_without_job(raised_by=requester, **values)

	def _message(self, ticket, sent_or_received, creation, sender, owner="Administrator", **values):
		doc = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": sent_or_received,
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"sender": sender,
				"subject": f"{PREFIX}reply",
				"content": "SECRET reply body",
				"owner": owner,
				"modified_by": owner,
				"creation": creation,
				"modified": creation,
				**values,
			}
		)
		doc.db_insert()
		return doc

	def _bot_message(self, ticket, creation=REPLY_DAY):
		return self._message(ticket, "Sent", creation, sender=AGENT_USER, owner=AGENT_USER)

	def _reply(self, ticket, creation=REPLY_DAY + HOUR, **values):
		raised_by = frappe.db.get_value("HD Ticket", ticket, "raised_by")
		return self._message(
			ticket, "Received", creation, sender=f"Người tạo <{raised_by.upper()}>", **values
		)

	def _reply_jobs(self):
		return [call.kwargs for call in self._jobs() if call.kwargs["trigger"] == TRIGGER_REQUESTER_REPLY]

	def _on_update(self, doc):
		"""Run the handler; return the logger lines it wrote."""
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			handlers.communication_on_update(doc)
		return [str(arg) for call in logger.info.call_args_list for arg in call.args]

	def assertSkipped(self, lines, ticket, reason):
		self.assertEqual(
			lines, [f"erp_ai handler ticket={ticket} trigger={TRIGGER_REQUESTER_REPLY} skipped: {reason}"]
		)


class TestRequesterReply(RequesterReplyTestCase):
	"""AC-41 (U6b-fixes.md:58-66; ADR-033 QĐ 2): a requester's reply after the bot's message queues exactly one job;
	the handler only reads and queues (traps B-1, B-2, B-3, X-1)."""

	def test_requester_reply_enqueues_one_job(self):
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		reply = self._reply(ticket)

		lines = self._on_update(reply)

		jobs = self._reply_jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0]["ticket_name"], ticket)
		self.assertEqual(jobs[0]["communication_name"], reply.name)
		self.assertEqual(jobs[0]["job_id"], f"erp_ai::{ticket}::{TRIGGER_REQUESTER_REPLY}::{reply.name}")
		self.assertEqual(
			lines,
			[f"erp_ai handler ticket={ticket} trigger={TRIGGER_REQUESTER_REPLY} enqueued: conditions_met"],
		)
		self.assertNotIn("SECRET", " ".join(lines))
		self.assertEqual(self.gateway.call_count, 0)

	def test_bot_own_message_no_job(self):
		ticket = self._requester_ticket().name
		bot = self._bot_message(ticket)
		raised_by = frappe.db.get_value("HD Ticket", ticket, "raised_by")
		cheap = [
			bot,
			self._message(
				ticket, "Received", REPLY_DAY + HOUR, raised_by, communication_type="Automated Message"
			),
			self._message(ticket, "Received", REPLY_DAY + HOUR, raised_by, reference_doctype="HD Team"),
		]

		def no_db(*args, **kwargs):
			raise AssertionError("the early return must not touch the database")

		with (
			patch.object(frappe.db, "sql", side_effect=no_db),
			patch.object(frappe.db, "get_value", side_effect=no_db),
			patch.object(frappe.db, "get_single_value", side_effect=no_db),
			patch.object(frappe.db, "exists", side_effect=no_db),
			patch.object(frappe, "get_all", side_effect=no_db),
			patch.object(frappe, "logger", side_effect=no_db),
		):
			for doc in cheap:
				handlers.communication_on_update(doc)
		# a Received message written under the agent account is the bot's own as well
		by_agent = self._message(ticket, "Received", REPLY_DAY + HOUR, raised_by, owner=AGENT_USER)
		self.assertSkipped(self._on_update(by_agent), ticket, "written_by_agent")

		self.assertEqual(self._reply_jobs(), [])

	def test_other_person_no_job(self):
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		other = self._message(ticket, "Received", REPLY_DAY + HOUR, f"{PREFIX.lower()}other@example.com")

		self.assertSkipped(self._on_update(other), ticket, "not_requester")
		self.assertEqual(self._reply_jobs(), [])

	def test_opening_message_no_job(self):
		# B-1, portal: the customer's ticket opens with its own Received Communication (new_ticket=True).
		customer = _ensure_user(f"{PREFIX.lower()}reply-customer@example.com", "HD Customer")
		set_agent_settings(enabled=0)
		frappe.set_user(customer)
		portal = make_ticket(subject=f"{PREFIX}portal", raised_by=customer).name
		frappe.set_user("Administrator")
		set_agent_settings(enabled=1)
		opening = frappe.get_all(
			"Communication",
			filters={"reference_doctype": "HD Ticket", "reference_name": portal},
			pluck="name",
		)
		self.assertEqual(len(opening), 1)
		opening = frappe.get_doc("Communication", opening[0])
		self.assertEqual((opening.sent_or_received, opening.sender), ("Received", customer))
		self.assertSkipped(self._on_update(opening), portal, "no_bot_message_before")

		# B-1, email: the mail that opened the ticket; a bot message written after it does not count.
		emailed = self._requester_ticket().name
		first = self._reply(emailed, creation=REPLY_DAY)
		self.assertSkipped(self._on_update(first), emailed, "no_bot_message_before")
		self._bot_message(emailed, creation=REPLY_DAY + HOUR)
		self.assertSkipped(self._on_update(first), emailed, "no_bot_message_before")

		self.assertEqual(self._reply_jobs(), [])

	def test_on_update_twice_one_job(self):
		# B-2: insert then save of one message in one transaction run the hook twice.
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		reply = self._reply(ticket)

		self._on_update(reply)
		self._on_update(reply)

		self.assertEqual(len(self._reply_jobs()), 1)

	def test_on_update_after_run_no_job(self):
		# B-2 after the job ran: its rows carry the event key as run_id.
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		handled = self._reply(ticket)
		make_log_entry(
			ticket=ticket,
			run_id=queue.requester_reply_key(ticket, handled.name),
			trigger=TRIGGER_REQUESTER_REPLY,
			entry_type="skip",
		)

		self.assertSkipped(self._on_update(handled), ticket, "already_handled")
		self.assertEqual(self._reply_jobs(), [])

		# the key is the message's own: a later message of the same ticket still gets its job
		later = self._reply(ticket, creation=REPLY_DAY + 2 * HOUR)
		self._on_update(later)
		self.assertEqual([job["communication_name"] for job in self._reply_jobs()], [later.name])

	def test_merged_ticket_uses_final_reference(self):
		# B-3: Helpdesk moves a reply to a merged ticket onto the merge target before the hook runs.
		target = self._requester_ticket().name
		raised_by = frappe.db.get_value("HD Ticket", target, "raised_by")
		source = self._ticket_without_job(raised_by=raised_by).name
		frappe.db.set_value(
			"HD Ticket", source, {"is_merged": 1, "merged_with": target}, update_modified=False
		)
		self._bot_message(target)
		reply = self._reply(source)

		frappe.get_doc("HD Ticket", source).on_communication_update(reply)
		self.assertEqual(reply.reference_name, target)
		self.enqueue.reset_mock()
		self._on_update(reply)

		jobs = self._reply_jobs()
		self.assertEqual([job["ticket_name"] for job in jobs], [target])
		self.assertEqual(jobs[0]["job_id"], f"erp_ai::{target}::{TRIGGER_REQUESTER_REPLY}::{reply.name}")

	def test_reply_while_previous_job_started_gets_own_job(self):
		# X-1: Frappe drops a deduplicated job whose id is QUEUED or STARTED (background_jobs.py:577-578).
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		statuses, received = {}, []

		def fake_enqueue(method, **kwargs):
			if kwargs.get("deduplicate") and statuses.get(kwargs["job_id"]) in ("queued", "started"):
				return None
			received.append(kwargs)
			statuses[kwargs["job_id"]] = "queued"

		self.enqueue.side_effect = fake_enqueue
		first = self._reply(ticket)
		self._on_update(first)
		self.assertEqual([job["communication_name"] for job in received], [first.name])
		statuses[received[0]["job_id"]] = "started"
		# M1 again in a later transaction while its job runs: Frappe drops it
		queue._clear_pending_job_ids()
		self._on_update(first)
		self.assertEqual(len(received), 1)

		second = self._reply(ticket, creation=REPLY_DAY + 2 * HOUR)
		self._on_update(second)

		self.assertEqual([job["communication_name"] for job in received], [first.name, second.name])
		self.assertEqual(received[1]["job_id"], f"erp_ai::{ticket}::{TRIGGER_REQUESTER_REPLY}::{second.name}")

	def test_handlers_write_nothing(self):
		# ADR-033 QĐ 2: the three new handlers only read and queue, on the path that queues as well.
		set_agent_settings(kb_draft_enabled=1)
		ticket = self._requester_ticket().name
		self._bot_message(ticket)
		reply = self._reply(ticket)
		task = frappe.get_doc(
			{
				"doctype": "Task",
				"subject": f"{PREFIX}write nothing",
				"description": f"{PREFIX}write nothing",
				"status": "Open",
				"ai_ticket": ticket,
			}
		).insert(ignore_permissions=True)
		task.status = "Working"
		task.save(ignore_permissions=True)
		resolved = frappe.get_doc("HD Ticket", ticket)
		resolved.status = "Resolved"
		resolved.save(ignore_permissions=True)
		# what the hooks queued while saving is dropped: the handlers run again below as a new transaction
		queue._clear_pending_job_ids()
		self.enqueue.reset_mock()

		with ExitStack() as stack:
			writes = {
				name: stack.enter_context(patch.object(owner, name))
				for owner, name in (
					(Document, "save"),
					(Document, "insert"),
					(Document, "db_set"),
					(Document, "delete"),
					(frappe.db, "set_value"),
					(frappe.db, "set_single_value"),
					(frappe.db, "delete"),
				)
			}
			handlers.communication_on_update(reply)
			handlers.task_on_update(task)
			handlers.ticket_on_update(resolved)

		self.assertEqual({name: mock.call_count for name, mock in writes.items()}, dict.fromkeys(writes, 0))
		self.assertEqual(
			sorted(call.kwargs.get("trigger", call.args[0]) for call in self.enqueue.call_args_list),
			sorted([TRIGGER_REQUESTER_REPLY, LIFECYCLE_JOB_PATH, TRIGGER_KB_DRAFT]),
		)


LIFECYCLE_JOB_PATH = "erp_ai.agent.lifecycle.run_task_lifecycle"


class TestTaskLifecycle(HandlerTestCase):
	"""AC-43 (U6b.md:277, A-11): a status change of a Task linked to a ticket queues the ticket's lifecycle job."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)

	def _task(self, ticket=None):
		values = {
			"doctype": "Task",
			"subject": f"{PREFIX}lifecycle task",
			"description": f"{PREFIX}lifecycle",
			"status": "Open",
		}
		if ticket:
			values["ai_ticket"] = ticket
		return frappe.get_doc(values).insert(ignore_permissions=True).name

	def _saved(self, task, **values):
		"""The Task saved with `values`, as the `on_update` hook receives it."""
		doc = frappe.get_doc("Task", task)
		doc.update(values)
		doc.save(ignore_permissions=True)
		return doc

	def _lifecycle_jobs(self):
		return [
			call.kwargs
			for call in self.enqueue.call_args_list
			if call.args and call.args[0] == LIFECYCLE_JOB_PATH
		]

	def test_status_change_enqueues_once(self):
		ticket = self._ticket_without_job().name
		task = self._task(ticket)
		# the Task hook (hooks.py, T161) queued the job of the linked insert: dropped, the saves below are a new
		# transaction
		queue._clear_pending_job_ids()
		self.enqueue.reset_mock()

		same_status = self._saved(task, subject=f"{PREFIX}lifecycle task, renamed")
		handlers.task_on_update(same_status)
		self.assertEqual(self._lifecycle_jobs(), [])

		changed = self._saved(task, status="Working")
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			handlers.task_on_update(changed)
			handlers.task_on_update(changed)

		jobs = self._lifecycle_jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0]["ticket_name"], ticket)
		self.assertEqual(jobs[0]["job_id"], f"erp_ai_lifecycle::{ticket}")
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self.gateway.call_count, 0)

		set_agent_settings(enabled=0)
		self.enqueue.reset_mock()
		off = self._saved(task, status="Pending Review")
		with patch.object(frappe, "logger", return_value=logger):
			handlers.task_on_update(off)
		self.assertEqual(self._lifecycle_jobs(), [])
		lines = [str(arg) for call in logger.info.call_args_list for arg in call.args]
		self.assertEqual(
			lines[-1], f"erp_ai handler ticket={ticket} trigger=task_status skipped: agent_disabled"
		)

	def test_task_without_ai_ticket_no_job(self):
		task = self._task()
		changed = self._saved(task, status="Working")
		self.enqueue.reset_mock()

		def no_db(*args, **kwargs):
			raise AssertionError("the early return must not touch the database")

		with (
			patch.object(frappe.db, "sql", side_effect=no_db),
			patch.object(frappe.db, "get_value", side_effect=no_db),
			patch.object(frappe.db, "get_single_value", side_effect=no_db),
			patch.object(frappe.db, "exists", side_effect=no_db),
			patch.object(frappe, "get_all", side_effect=no_db),
			patch.object(frappe, "logger", side_effect=no_db),
		):
			handlers.task_on_update(changed)

		self.assertEqual(self._lifecycle_jobs(), [])


class TestKbDraftTrigger(HandlerTestCase):
	"""AC-45 (U6b.md:268, :275; ADR-033 QĐ 2): a ticket moving into the Resolved group queues the knowledge-draft
	run; the ticket's `on_update` hook runs on a real save."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)
		set_agent_settings(kb_draft_enabled=1)

	def _kb_jobs(self):
		return [call.kwargs for call in self._jobs() if call.kwargs["trigger"] == TRIGGER_KB_DRAFT]

	def _set_status(self, ticket, status, **flags):
		"""Save the ticket with `status` and `flags`; return the kb_draft lines its handler logged."""
		doc = frappe.get_doc("HD Ticket", ticket)
		doc.status = status
		doc.flags.update(flags)
		logger = MagicMock()
		with patch.object(frappe, "logger", return_value=logger):
			doc.save(ignore_permissions=True)
		lines = [str(arg) for call in logger.info.call_args_list for arg in call.args]
		return [line for line in lines if f"trigger={TRIGGER_KB_DRAFT} " in line]

	@staticmethod
	def _skipped(ticket, reason):
		return [f"erp_ai handler ticket={ticket} trigger={TRIGGER_KB_DRAFT} skipped: {reason}"]

	def test_resolved_enqueues_kb_draft(self):
		ticket = self._ticket_without_job().name
		# a status change outside the Resolved group, and a save without a status change: nothing
		self.assertEqual(self._set_status(ticket, "Replied"), [])
		self.assertEqual(self._set_status(ticket, "Replied"), [])
		self.assertEqual(self._kb_jobs(), [])

		lines = self._set_status(ticket, "Resolved")

		jobs = self._kb_jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0]["ticket_name"], ticket)
		self.assertEqual(jobs[0]["job_id"], f"erp_ai::{ticket}::{TRIGGER_KB_DRAFT}")
		self.assertNotIn("communication_name", jobs[0])
		self.assertEqual(
			lines, [f"erp_ai handler ticket={ticket} trigger={TRIGGER_KB_DRAFT} enqueued: conditions_met"]
		)
		self.assertEqual(self.gateway.call_count, 0)

	def test_excluded_team_no_job(self):
		ticket = self._ticket_without_job(agent_group=EXCLUDED_TEAM).name

		self.assertEqual(
			self._set_status(ticket, "Resolved"), self._skipped(ticket, "not_sendable:excluded_team")
		)
		self.assertEqual(self._kb_jobs(), [])

	def test_ai_opt_out_no_job(self):
		ticket = self._ticket_without_job(ai_opt_out=1).name

		self.assertEqual(self._set_status(ticket, "Closed"), self._skipped(ticket, "not_sendable:opted_out"))
		self.assertEqual(self._kb_jobs(), [])

	def test_silent_close_no_job(self):
		# the lifecycle job's own close of a silent F ticket (U6b.md:260 step 7)
		ticket = self._ticket_without_job().name

		lines = self._set_status(ticket, "Closed", erp_ai_silent_close=True)

		self.assertEqual(lines, self._skipped(ticket, "silent_close"))
		self.assertEqual(self._kb_jobs(), [])

	def test_switch_off_no_job(self):
		switch_off = self._ticket_without_job().name
		agent_off = self._ticket_without_job().name

		set_agent_settings(kb_draft_enabled=0)
		self.assertEqual(self._set_status(switch_off, "Resolved"), self._skipped(switch_off, "kb_draft_off"))
		set_agent_settings(kb_draft_enabled=1, enabled=0)
		self.assertEqual(self._set_status(agent_off, "Resolved"), self._skipped(agent_off, "agent_disabled"))

		self.assertEqual(self._kb_jobs(), [])

	def test_second_close_no_second_job(self):
		ticket = self._ticket_without_job().name
		self._set_status(ticket, "Resolved")
		# Resolved then Closed in one transaction: the job is already claimed
		self._set_status(ticket, "Closed")
		self.assertEqual(len(self._kb_jobs()), 1)

		# a later transaction, after the first run wrote its draft: reopened, then closed again
		frappe.get_doc(
			{
				"doctype": "HD Article",
				"title": f"{PREFIX}kb draft",
				"content": "<p>ERPAI-TEST</p>",
				"status": "Draft",
				"ai_source_ticket": ticket,
			}
		).insert(ignore_permissions=True)
		queue._clear_pending_job_ids()
		self._set_status(ticket, "Open")
		lines = self._set_status(ticket, "Closed")

		self.assertEqual(lines, self._skipped(ticket, "kb_exists"))
		self.assertEqual(len(self._kb_jobs()), 1)


# T161 (U6b.md:305-310, U6b-fixes Sửa 14): the hooks of the U6b handlers and the hourly silent-F scan.
U6B_ON_UPDATE = {
	"Communication": "erp_ai.handlers.communication_on_update",
	"Task": "erp_ai.handlers.task_on_update",
	"HD Ticket": "erp_ai.handlers.ticket_on_update",
}
SILENT_F_SCAN = "erp_ai.agent.lifecycle.scan_silent_f_tickets"
HOURLY_CRON = "0 * * * *"


class TestHooksWiring(FrappeTestCase):
	"""AC-41, AC-43, AC-44: the requester-reply and Task handlers run on `on_update`, the ticket's hook keeps its path,
	and the hourly cron points straight at the silent-F scan, which migrate made a Scheduled Job Type."""

	def test_u6b_hooks_registered(self):
		for doctype, path in U6B_ON_UPDATE.items():
			with self.subTest(doctype):
				self.assertEqual(hooks.doc_events.get(doctype, {}).get("on_update"), path)
				self.assertTrue(callable(frappe.get_attr(path)))
		self.assertIn(SILENT_F_SCAN, hooks.scheduler_events["cron"].get(HOURLY_CRON, []))
		self.assertTrue(callable(frappe.get_attr(SILENT_F_SCAN)))
		self.assertEqual(
			frappe.db.get_value(
				"Scheduled Job Type", {"method": SILENT_F_SCAN}, ["frequency", "cron_format"]
			),
			("Cron", HOURLY_CRON),
		)


INSTRUCTOR = "erp-ai-src-instructor@example.com"
PLAIN_USER = "erp-ai-src-plain@example.com"
OTHER_TYPE = f"{PREFIX}OtherType"
OTHER_TEAM = f"{PREFIX}OtherTeam"


def _make_user(email, *roles):
	"""A user holding exactly `roles`, created inside the test transaction."""
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


class TestLessonSources(HandlerTestCase):
	"""AC-5, AC-9: a person's classification fix and a "ghi nhớ:" message each make a lesson."""

	def setUp(self):
		frappe.db.rollback()
		keep_agent_settings(self)
		super().setUp()
		# Only the lessons this test makes: the shared site holds real ones (NFR-7, rolled back, never committed).
		clear_lesson_store()
		set_agent_settings(lessons_enabled=1, lesson_teach_marker="ghi nhớ:")
		_ensure_ticket_type(OTHER_TYPE)
		_ensure_team(OTHER_TEAM)
		_make_user(INSTRUCTOR, "ERP AI Instructor", "Agent")
		_make_user(PLAIN_USER, "Agent")

	def _lessons(self, **filters):
		return frappe.get_all(
			"ERP AI Lesson",
			filters=filters,
			fields=["name", "lesson_status", "lesson_source", "lesson_text", "ticket", "author"],
		)

	def _steps(self, name):
		return [row.step for row in frappe.get_doc("ERP AI Lesson", name).history]

	def _classified(self, **values):
		ticket = self._ticket_without_job(
			priority="Low", ticket_type=TICKET_TYPE, agent_group=OPEN_TEAM, **values
		)
		ticket.reload()
		log = make_log_entry(
			ticket=ticket.name,
			entry_type="classify",
			predicted_category="A",
			predicted_ticket_type=TICKET_TYPE,
			predicted_agent_group=OPEN_TEAM,
			predicted_priority="Low",
		)
		return ticket, log

	def _change(self, ticket, user="Administrator", **values):
		frappe.set_user(user)
		try:
			ticket.reload()
			ticket.update(values)
			ticket.save(ignore_permissions=True)
		finally:
			frappe.set_user("Administrator")

	def test_correction_of_each_field_makes_one_lesson(self):
		cases = (
			({"ticket_type": OTHER_TYPE}, f"Loại {TICKET_TYPE}", f"Loại {OTHER_TYPE}"),
			({"agent_group": OTHER_TEAM}, f"Nhóm {OPEN_TEAM}", f"Nhóm {OTHER_TEAM}"),
			({"priority": "High"}, "Ưu tiên Low", "Ưu tiên High"),
		)
		for changes, before, after in cases:
			with self.subTest(changes):
				ticket, _log = self._classified()
				self._change(ticket, **changes)
				rows = self._lessons(ticket=ticket.name)
				self.assertEqual(len(rows), 1)
				self.assertEqual(rows[0].lesson_source, "Người sửa")
				self.assertIn(before, rows[0].lesson_text)
				self.assertIn(after, rows[0].lesson_text)

	def test_change_before_prediction_makes_none(self):
		ticket = self._ticket_without_job(priority="Low")
		self._change(ticket, priority="High")
		self.assertEqual(self._lessons(), [])

	def test_change_to_bot_value_makes_none(self):
		ticket, _log = self._classified()
		self._change(ticket, priority="Low", agent_group=OPEN_TEAM)
		self.assertEqual(self._lessons(ticket=ticket.name), [])

	def test_correction_on_excluded_ticket_makes_none(self):
		ticket = self._ticket_without_job(priority="Low", ticket_type=TICKET_TYPE, agent_group=EXCLUDED_TEAM)
		make_log_entry(
			ticket=ticket.name,
			entry_type="classify",
			predicted_category="A",
			predicted_ticket_type=TICKET_TYPE,
			predicted_agent_group=EXCLUDED_TEAM,
			predicted_priority="Low",
		)
		self._change(ticket, priority="High")
		self.assertEqual(self._lessons(), [])

	def test_second_correction_updates_same_lesson(self):
		ticket, _log = self._classified()
		self._change(ticket, priority="High")
		self._change(ticket, priority="Urgent")
		rows = self._lessons(ticket=ticket.name)
		self.assertEqual(len(rows), 1)
		self.assertIn("Ưu tiên Urgent", rows[0].lesson_text)
		self.assertEqual(self._steps(rows[0].name), ["Tạo", "Cập nhật"])

	def test_correction_by_plain_user_is_pending(self):
		ticket, _log = self._classified()
		self._change(ticket, user=PLAIN_USER, priority="High")
		rows = self._lessons(ticket=ticket.name)
		self.assertEqual([row.lesson_status for row in rows], ["Chờ duyệt"])
		self.assertEqual(rows[0].author, PLAIN_USER)

	def test_correction_by_instructor_is_active(self):
		ticket, _log = self._classified()
		self._change(ticket, user=INSTRUCTOR, priority="High")
		self.assertEqual([row.lesson_status for row in self._lessons(ticket=ticket.name)], ["Đang dùng"])

	def test_revert_to_prediction_retires_lesson(self):
		for user, status, step in ((INSTRUCTOR, "Đã tắt", "Tắt"), (PLAIN_USER, "Bị từ chối", "Từ chối")):
			with self.subTest(user):
				ticket, _log = self._classified()
				self._change(ticket, user=user, priority="High")
				self._change(ticket, user=user, priority="Low")
				rows = self._lessons(ticket=ticket.name)
				self.assertEqual(len(rows), 1)
				self.assertEqual(rows[0].lesson_status, status)
				self.assertEqual(self._steps(rows[0].name), ["Tạo", step])
				doc = frappe.get_doc("ERP AI Lesson", rows[0].name)
				self.assertEqual(doc.reviewed_by, user)
				self.assertTrue(doc.reviewed_at)

	def test_store_failure_keeps_ticket_save(self):
		ticket, log = self._classified()
		with patch("erp_ai.agent.lessons._store", side_effect=RuntimeError("boom")):
			self._change(ticket, priority="High")
		self.assertEqual(frappe.db.get_value("HD Ticket", ticket.name, "priority"), "High")
		corrected = frappe.db.get_value(LOG_DOCTYPE, log, "human_corrected_to")
		self.assertEqual(json.loads(corrected)["priority"], "High")
		self.assertEqual(self._lessons(), [])
		self.assertEqual(frappe.log_error.call_count, 1)

	def test_teaching_comment_by_instructor_makes_active_lesson(self):
		ticket = self._ticket_without_job()
		frappe.set_user(INSTRUCTOR)
		with patch("erp_ai.handlers.enqueue_agent_run") as enqueue:
			self._comment(ticket.name, f"{KEYWORD} ghi nhớ: phiếu máy in chuyển nhóm IT")
		frappe.set_user("Administrator")
		rows = self._lessons()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].lesson_source, "Người dạy")
		self.assertEqual(rows[0].lesson_status, "Đang dùng")
		self.assertEqual(rows[0].ticket, ticket.name)
		self.assertEqual(rows[0].lesson_text, "phiếu máy in chuyển nhóm IT")
		self.assertEqual(enqueue.call_count, 1)

	def test_comment_without_marker_makes_none(self):
		ticket = self._ticket_without_job()
		frappe.set_user(INSTRUCTOR)
		self._comment(ticket.name, f"{KEYWORD} phiếu máy in nên chuyển nhóm IT")
		frappe.set_user("Administrator")
		self.assertEqual(self._lessons(), [])

	def test_teaching_by_plain_user_makes_none(self):
		ticket = self._ticket_without_job()
		frappe.set_user(PLAIN_USER)
		messages.add_message(ticket.name, "ghi nhớ: phiếu máy in chuyển nhóm IT", trusted=True)
		frappe.set_user("Administrator")
		self.assertEqual(self._lessons(), [])

	def test_teaching_on_excluded_ticket_makes_none(self):
		ticket = self._ticket_without_job(agent_group=EXCLUDED_TEAM)
		frappe.set_user(INSTRUCTOR)
		messages.add_message(ticket.name, "ghi nhớ: phiếu máy in chuyển nhóm IT", trusted=True)
		frappe.set_user("Administrator")
		self.assertEqual(self._lessons(), [])

	def test_same_message_twice_makes_one(self):
		ticket = self._ticket_without_job()
		frappe.set_user(INSTRUCTOR)
		name = messages.add_message(ticket.name, "xin chào", trusted=True)
		from erp_ai.agent import lessons

		first = lessons.record_teaching_message(ticket.name, name, "quy tắc một")
		second = lessons.record_teaching_message(ticket.name, name, "quy tắc một")
		frappe.set_user("Administrator")
		self.assertTrue(first)
		self.assertEqual(first, second)
		self.assertEqual(len(self._lessons()), 1)

	def test_marker_without_rule_makes_no_lesson(self):
		ticket = self._ticket_without_job()
		frappe.set_user(INSTRUCTOR)
		self._comment(ticket.name, f"{KEYWORD} ghi nhớ:   ")
		messages.add_message(ticket.name, "ghi nhớ:", trusted=True)
		frappe.set_user("Administrator")
		self.assertEqual(self._lessons(), [])

	def test_marker_case_and_unicode_variants(self):
		from erp_ai.agent import lessons

		for text in (
			"Ghi nhớ: quy tắc",
			"GHI NHỚ : quy tắc",
			f"{KEYWORD} ghi nhớ   : quy tắc",
			unicodedata.normalize("NFD", "ghi nhớ: quy tắc"),
			unicodedata.normalize("NFD", "GHI NHỚ: quy tắc"),
		):
			with self.subTest(text):
				self.assertEqual(unicodedata.normalize("NFC", lessons.teaching_rule(text) or ""), "quy tắc")
		for text in ("quy tắc ghi nhớ: x", "ghi chú: quy tắc", ""):
			with self.subTest(text):
				self.assertIsNone(lessons.teaching_rule(text))

	def test_blank_marker_turns_teaching_off(self):
		from erp_ai.agent import lessons

		set_agent_settings(lesson_teach_marker="")
		self.assertIsNone(lessons.teaching_rule("ghi nhớ: quy tắc"))

	def test_panel_message_teaches(self):
		ticket = self._ticket_without_job()
		frappe.set_user(INSTRUCTOR)
		messages.add_message(ticket.name, "ghi nhớ: phiếu máy in chuyển nhóm IT", trusted=True)
		frappe.set_user("Administrator")
		rows = self._lessons()
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].lesson_status, "Đang dùng")


BOT_PICK = "bot-pick@example.com"
HUMAN_PICK = "human-pick@example.com"


class TestAssigneeChangeSource(HandlerTestCase):
	"""AC-6: a person changing the assignee the bot chose makes a lesson."""

	def setUp(self):
		frappe.db.rollback()
		keep_agent_settings(self)
		super().setUp()
		# Only the lessons this test makes: the shared site holds real ones (NFR-7, rolled back, never committed).
		clear_lesson_store()
		set_agent_settings(lessons_enabled=1, lesson_teach_marker="ghi nhớ:")
		_make_user(INSTRUCTOR, "ERP AI Instructor", "Agent")
		_make_user(PLAIN_USER, "Agent")
		_make_user(BOT_PICK, "Agent")
		_make_user(HUMAN_PICK, "Agent")

	def _lessons(self, **filters):
		return frappe.get_all(
			"ERP AI Lesson",
			filters=filters,
			fields=["name", "lesson_status", "lesson_source", "lesson_text", "ticket", "author"],
		)

	def _bot_assigns(self, ticket, user=BOT_PICK):
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": user,
				"reference_type": "HD Ticket",
				"reference_name": ticket,
				"assigned_by": AGENT_USER,
				"status": "Open",
			}
		)
		todo.set_new_name()
		todo.db_insert()

	def _person_assigns(self, ticket, session_user, user=HUMAN_PICK):
		from frappe.desk.form.assign_to import add

		frappe.set_user(session_user)
		try:
			add({"doctype": "HD Ticket", "name": ticket, "assign_to": [user]})
		finally:
			frappe.set_user("Administrator")

	def test_reassign_after_bot_makes_lesson(self):
		ticket = self._ticket_without_job()
		self._bot_assigns(ticket.name)
		self._person_assigns(ticket.name, INSTRUCTOR)
		rows = self._lessons(ticket=ticket.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].lesson_source, "Người sửa")
		self.assertEqual(rows[0].lesson_status, "Đang dùng")
		self.assertIn(BOT_PICK, rows[0].lesson_text)
		self.assertIn(HUMAN_PICK, rows[0].lesson_text)

	def test_reassign_without_bot_assignment_makes_none(self):
		ticket = self._ticket_without_job()
		self._person_assigns(ticket.name, INSTRUCTOR)
		self.assertEqual(self._lessons(), [])

	def test_bot_own_assignment_makes_none(self):
		ticket = self._ticket_without_job()
		self._bot_assigns(ticket.name)
		self._person_assigns(ticket.name, AGENT_USER)
		self.assertEqual(self._lessons(), [])

	def test_reassign_by_plain_user_is_pending(self):
		ticket = self._ticket_without_job()
		self._bot_assigns(ticket.name)
		self._person_assigns(ticket.name, PLAIN_USER)
		rows = self._lessons(ticket=ticket.name)
		self.assertEqual([row.lesson_status for row in rows], ["Chờ duyệt"])
		self.assertEqual(rows[0].author, PLAIN_USER)

	def test_second_reassign_updates_same_lesson(self):
		ticket = self._ticket_without_job()
		self._bot_assigns(ticket.name)
		self._person_assigns(ticket.name, INSTRUCTOR)
		self._person_assigns(ticket.name, INSTRUCTOR, user=PLAIN_USER)
		rows = self._lessons(ticket=ticket.name)
		self.assertEqual(len(rows), 1)
		self.assertIn(PLAIN_USER, rows[0].lesson_text)

	def test_non_ticket_todo_returns_before_db_read(self):
		note = frappe.get_doc({"doctype": "Note", "title": "ghi chú thử", "public": 1}).insert(
			ignore_permissions=True
		)
		real_get_value = frappe.db.get_value

		def guarded(doctype, *args, **kwargs):
			# Frappe itself reads DocType metadata while inserting; the handler must not read ToDo rows.
			if doctype == "ToDo":
				raise AssertionError("handler read ToDo before step 0")
			return real_get_value(doctype, *args, **kwargs)

		with patch("frappe.db.get_value", side_effect=guarded):
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"allocated_to": HUMAN_PICK,
					"reference_type": "Note",
					"reference_name": note.name,
					"description": "x",
				}
			).insert(ignore_permissions=True)
		self.assertEqual(self._lessons(), [])
