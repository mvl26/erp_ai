import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai import handlers
from erp_ai.agent import runner
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, LOGGER_NAME
from erp_ai.test_utils import FakeGateway, make_log_entry, make_model_result, set_agent_settings

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

		self.gateway = FakeGateway()
		gateway_patch = patch("erp_ai.gateway.call_model", self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)

		enqueue_patch = patch.object(frappe, "enqueue")
		self.enqueue = enqueue_patch.start()
		self.addCleanup(enqueue_patch.stop)

		set_agent_settings(enabled=1, trigger_keyword=KEYWORD, excluded_teams=EXCLUDED_TEAM)
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

	def test_opt_out_or_excluded_team_no_job_no_model_call(self):
		make_ticket(subject=f"{PREFIX}opt out", ai_opt_out=1)
		self.assertEqual(self._jobs(), [])

		make_ticket(subject=f"{PREFIX}excluded", agent_group=EXCLUDED_TEAM)
		self.assertEqual(self._jobs(), [])

		ticket = self._ticket_without_job(ai_opt_out=1)
		self._comment(ticket.name, f"{KEYWORD} hello")
		self.assertEqual(self._jobs(), [])

		other = self._ticket_without_job(agent_group=EXCLUDED_TEAM)
		self._comment(other.name, f"{KEYWORD} hello")
		self.assertEqual(self._jobs(), [])

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
		self.assertEqual(call["max_tokens"], 400)
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

	def test_comment_without_keyword_no_job(self):
		ticket = self._ticket_without_job()

		self._comment(ticket.name, "Không nhắc ai cả")

		self.assertEqual(self._jobs(), [])

	def test_comment_with_agent_disabled_no_job(self):
		ticket = self._ticket_without_job()
		set_agent_settings(enabled=0)

		self._comment(ticket.name, f"{KEYWORD} xem giúp")

		self.assertEqual(self._jobs(), [])
		self.assertEqual(self.gateway.call_count, 0)

	def test_comment_with_empty_keyword_setting_no_job(self):
		ticket = self._ticket_without_job()
		set_agent_settings(trigger_keyword="")

		self._comment(ticket.name, "any content")

		self.assertEqual(self._jobs(), [])

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

		handlers.comment_after_insert(doc)

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


class TestHumanCorrection(HandlerTestCase):
	"""AC-11: a person's change to the classification is recorded on the latest `classify` log row."""

	FIRST_CORRECTION_AT = "2026-01-01 08:00:00"

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

	def test_human_correction_updates_latest_log(self):
		ticket, older_log = self._classified_ticket(run_id=f"{PREFIX}old")
		latest_log = make_log_entry(
			ticket=ticket.name,
			entry_type="classify",
			predicted_category="B",
			run_id=f"{PREFIX}new",
			creation="2099-01-01 00:00:00",
		)

		self._save_priority(ticket, "High")

		first = self._log(latest_log)
		self.assertEqual(
			json.loads(first.human_corrected_to),
			{"ticket_type": ticket.ticket_type, "agent_group": ticket.agent_group, "priority": "High"},
		)
		self.assertEqual(first.human_corrected_by, "Administrator")
		self.assertTrue(first.human_corrected_at)
		self.assertEqual(self._classified_by(ticket), "Người")
		self.assertIsNone(self._log(older_log).human_corrected_to)

		# Second correction: the value is the last one, the time stays the first one.
		frappe.db.set_value(
			LOG_DOCTYPE, latest_log, "human_corrected_at", self.FIRST_CORRECTION_AT, update_modified=False
		)
		self._save_priority(ticket, "Urgent")

		second = self._log(latest_log)
		self.assertEqual(json.loads(second.human_corrected_to)["priority"], "Urgent")
		self.assertEqual(str(second.human_corrected_at), self.FIRST_CORRECTION_AT)

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

	def test_ticket_without_classify_log_saves_without_error(self):
		ticket = self._ticket_without_job(priority="Low")
		make_log_entry(ticket=ticket.name, entry_type="skip", run_id=f"{PREFIX}skip")

		self._save_priority(ticket, "High")

		self.assertEqual(frappe.db.get_value("HD Ticket", ticket.name, "priority"), "High")
		self.assertNotEqual(self._classified_by(ticket), "Người")

	def test_log_without_predicted_category_not_recorded(self):
		ticket, log = self._classified_ticket(predicted_category="")

		self._save_priority(ticket, "High")

		self.assertIsNone(self._log(log).human_corrected_to)
		self.assertNotEqual(self._classified_by(ticket), "Người")

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
		ticket.flags.erp_ai_human_corrected = True
		ticket.flags.in_insert = True

		handlers.ticket_on_update(ticket)

		self.assertIsNone(self._log(log).human_corrected_to)

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
