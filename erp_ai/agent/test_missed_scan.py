from datetime import datetime, timedelta
from unittest.mock import call as unittest_call
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import missed_scan, policy, queue
from erp_ai.constants import (
	AGENT_USER,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import keep_agent_settings, make_log_entry, set_agent_settings

# A window no live ticket can fall into: every ticket a test needs gets its `creation` set inside it.
ENABLED_AT = datetime(2099, 1, 1, 0, 0, 0)
NOW = datetime(2099, 1, 2, 12, 0, 0)
OLD_ENOUGH = NOW - timedelta(hours=1)
MAX_RUNS = 2
EXCLUDED_TEAM = "ERPAI-TEST-missed-scan excluded"
OTHER_TEAM = "ERPAI-TEST-missed-scan other"
# Standard Helpdesk records (created by its install).
TICKET_TYPE = "Unspecified"
PRIORITY = "Medium"
# Text an exception may carry (ticket content); it must never reach the Error Log message.
SECRET_TEXT = "ERPAI-TEST nội dung phiếu bí mật"


class TestMissedScan(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert makes an Assignment Rule that Frappe caches in Redis; registered first so it runs
		# AFTER the rollback. (Never delete_doc HD Team: HDTeam.on_trash commits the transaction.)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(
			enabled=0,
			agent_enabled_at=ENABLED_AT,
			excluded_teams=EXCLUDED_TEAM,
			max_runs_per_ticket_per_day=MAX_RUNS,
		)
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)
		for team in (EXCLUDED_TEAM, OTHER_TEAM):
			if not frappe.db.exists("HD Team", team):
				frappe.get_doc(
					{"doctype": "HD Team", "team_name": team, "users": [{"user": "Administrator"}]}
				).insert(ignore_permissions=True)

	def _ticket(self, creation=OLD_ENOUGH, **values) -> str:
		"""A ticket missing only `agent_group` (ticket_type and priority filled), created at `creation`."""
		ticket = make_ticket(subject="T33 missed scan ticket")
		fields = {"ticket_type": TICKET_TYPE, "priority": PRIORITY, "agent_group": None, "creation": creation}
		fields.update(values)
		frappe.db.set_value("HD Ticket", ticket.name, fields, update_modified=False)
		return str(ticket.name)

	def _log(self, ticket, entry_type, run_id, predicted_category=None, creation=NOW):
		name = make_log_entry(
			ticket=ticket,
			entry_type=entry_type,
			run_id=run_id,
			trigger=TRIGGER_TICKET_INSERT,
			predicted_category=predicted_category,
		)
		frappe.db.set_value(LOG_DOCTYPE, name, "creation", creation, update_modified=False)

	def _found(self, tickets, now=NOW) -> list[str]:
		"""The scan result restricted to the tickets this test made, in the returned order."""
		mine = set(tickets)
		return [name for name in missed_scan.find_missed_tickets(now) if name in mine]

	def test_constants(self):
		self.assertEqual(missed_scan.SCAN_BATCH, 50)
		self.assertEqual(missed_scan.SCAN_GRACE_MIN, 5)

	def test_seven_ticket_kinds(self):
		"""AC-16: each refused ticket fails exactly one of the 8 conditions and meets the other 7."""
		wanted = [
			self._ticket(),  # only agent_group missing
			self._ticket(ticket_type=None, agent_group=OTHER_TEAM),  # only ticket_type missing
			self._ticket(priority=None, agent_group=OTHER_TEAM),  # only priority missing
		]
		refused = {
			"created before enabling": self._ticket(creation=ENABLED_AT - timedelta(minutes=1)),
			"created exactly at enabling": self._ticket(creation=ENABLED_AT),
			"created under 5 minutes ago": self._ticket(creation=NOW - timedelta(minutes=4)),
			"resolved": self._ticket(status_category="Resolved"),
			"created by the agent": self._ticket(owner=AGENT_USER),
			"classified": self._ticket(),
			"all 3 fields filled": self._ticket(agent_group=OTHER_TEAM),
			"excluded team": self._ticket(ticket_type=None, agent_group=EXCLUDED_TEAM),
			"opted out of AI": self._ticket(**{policy.OPT_OUT_FIELD: 1}),
			"daily runs used up": self._ticket(),
		}
		self._log(refused["classified"], "classify", "ERPAI-TEST-run-ok", predicted_category="B")
		for run in range(MAX_RUNS):
			self._log(refused["daily runs used up"], "reason", f"ERPAI-TEST-run-{run}")

		found = self._found([*wanted, *refused.values()])

		self.assertEqual(found, wanted)
		for kind, name in refused.items():
			with self.subTest(kind=kind):
				self.assertNotIn(name, found)

	def test_runs_below_daily_limit_still_found(self):
		ticket = self._ticket()
		self._log(ticket, "reason", "ERPAI-TEST-run-0")
		# a run of yesterday does not count for today's limit
		self._log(ticket, "reason", "ERPAI-TEST-run-1", creation=NOW.replace(hour=0) - timedelta(seconds=1))
		self.assertEqual(self._found([ticket]), [ticket])

	def test_failed_run_requeued(self):
		"""A classify row without predicted_category (gateway error, bad format) leaves the ticket in the scan."""
		ticket = self._ticket()
		self._log(ticket, "classify", "ERPAI-TEST-run-failed")
		self.assertEqual(self._found([ticket]), [ticket])

		self._log(ticket, "classify", "ERPAI-TEST-run-ok", predicted_category="A")
		self.assertEqual(self._found([ticket]), [])

	def test_predicted_category_on_other_entry_type_does_not_count(self):
		ticket = self._ticket()
		self._log(ticket, "reason", "ERPAI-TEST-run-reason", predicted_category="A")
		self.assertEqual(self._found([ticket]), [ticket])

	def test_grace_edge_exactly_five_minutes(self):
		at_edge = self._ticket(creation=NOW - timedelta(minutes=5))
		one_second_late = self._ticket(creation=NOW - timedelta(minutes=5) + timedelta(seconds=1))
		self.assertEqual(self._found([at_edge, one_second_late]), [at_edge])

	def test_no_enabled_at_noop(self):
		ticket = self._ticket()
		self.assertEqual(self._found([ticket]), [ticket])
		for stored in (None, ""):
			with self.subTest(stored=stored):
				frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "agent_enabled_at"})
				frappe.db.sql(
					"insert into `tabSingles` (doctype, field, value) values (%s, 'agent_enabled_at', %s)",
					(SETTING_DOCTYPE, stored),
				)
				frappe.db.value_cache.pop(SETTING_DOCTYPE, None)
				self.assertEqual(missed_scan.find_missed_tickets(NOW), [])
		with self.subTest(stored="<missing>"):
			frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "agent_enabled_at"})
			frappe.db.value_cache.pop(SETTING_DOCTYPE, None)
			self.assertEqual(missed_scan.find_missed_tickets(NOW), [])

	def test_batch_limit_oldest_first(self):
		"""At most SCAN_BATCH names, by creation ascending; a refused older ticket takes no slot."""
		refused = self._ticket(creation=OLD_ENOUGH - timedelta(minutes=1), **{policy.OPT_OUT_FIELD: 1})
		newest_first = [
			self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second))
			for second in reversed(range(missed_scan.SCAN_BATCH + 1))
		]
		oldest_first = list(reversed(newest_first))

		found = missed_scan.find_missed_tickets(NOW)

		self.assertEqual(found, oldest_first[: missed_scan.SCAN_BATCH])
		self.assertNotIn(refused, found)

	def _enable_agent(self):
		set_agent_settings(enabled=1)
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)

	def _cap(self, limit):
		"""Patch the candidate cap (design-w1-fixes-6 Điểm 2); `create` so the test also runs on code without it."""
		return patch.object(missed_scan, "SCAN_CANDIDATE_LIMIT", limit, create=True)

	@staticmethod
	def _queued_tickets(enqueue) -> list[str]:
		return [queued.kwargs["ticket_name"] for queued in enqueue.call_args_list]

	def test_two_scans_one_job_per_ticket(self):
		"""AC-16, NFR-3: a second scan in the same transaction queues nothing new; one logger line per scan (D-17)."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(2)]
		self._enable_agent()

		with patch("frappe.enqueue") as enqueue, patch.object(missed_scan.frappe, "logger") as logger:
			missed_scan.scan_missed_tickets(NOW)
			self.assertEqual(self._queued_tickets(enqueue), tickets)
			self.assertEqual(
				logger.return_value.info.call_args_list, [unittest_call("missed_scan: xếp 2 phiếu")]
			)

			logger.reset_mock()
			missed_scan.scan_missed_tickets(NOW)
			self.assertEqual(self._queued_tickets(enqueue), tickets)
			self.assertEqual(
				logger.return_value.info.call_args_list, [unittest_call("missed_scan: xếp 0 phiếu")]
			)

		for queued in enqueue.call_args_list:
			with self.subTest(ticket=queued.kwargs["ticket_name"]):
				self.assertEqual(queued.kwargs["trigger"], TRIGGER_TICKET_INSERT)
				self.assertEqual(
					queued.kwargs["job_id"],
					f"erp_ai::{queued.kwargs['ticket_name']}::{TRIGGER_TICKET_INSERT}",
				)
		logger.return_value.warning.assert_not_called()

	def test_agent_disabled_noop(self):
		"""Agent off: no candidate query, no job, exactly one logger line."""
		self._ticket()
		with (
			patch("frappe.enqueue") as enqueue,
			patch.object(missed_scan.frappe, "logger") as logger,
			patch.object(missed_scan, "find_missed_tickets", wraps=missed_scan.find_missed_tickets) as find,
		):
			missed_scan.scan_missed_tickets(NOW)

		enqueue.assert_not_called()
		find.assert_not_called()
		self.assertEqual(
			logger.return_value.info.call_args_list, [unittest_call("missed_scan: agent tắt, bỏ qua")]
		)
		logger.return_value.warning.assert_not_called()

	def test_cron_declared_every_15_minutes(self):
		"""ADR-033 QĐ 2, AC-16: hooks.py declares the cron and migrate turned it into a Scheduled Job Type."""
		method = "erp_ai.agent.missed_scan.scan_missed_tickets"
		self.assertEqual(frappe.get_hooks("scheduler_events").get("cron", {}).get("*/15 * * * *"), [method])
		self.assertEqual(
			frappe.db.get_value("Scheduled Job Type", {"method": method}, ["frequency", "cron_format"]),
			("Cron", "*/15 * * * *"),
		)

	def test_candidate_window_keeps_the_newest(self):
		"""D-16 cap: only the SCAN_CANDIDATE_LIMIT newest candidates are considered, still returned oldest first."""
		a, b, c, d = (self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(4))
		with self._cap(3):
			self.assertEqual(self._found([a, b, c, d]), [b, c, d])

	def test_old_refused_tickets_do_not_starve_a_new_one(self):
		"""Old opted-out tickets never leave the candidate set; the cap keeps them from crowding out a new one."""
		refused = [
			self._ticket(creation=OLD_ENOUGH - timedelta(minutes=10 - minute), **{policy.OPT_OUT_FIELD: 1})
			for minute in range(5)
		]
		new = self._ticket(creation=OLD_ENOUGH)
		with (
			self._cap(3),
			patch.object(policy, "can_send_ticket", wraps=policy.can_send_ticket) as can_send,
		):
			self.assertEqual(self._found([*refused, new]), [new])
		self.assertEqual(can_send.call_count, 3)

	def test_warns_once_when_candidate_limit_reached(self):
		"""One warning when the candidate query returns exactly the cap; none one below it."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(2)]
		with self._cap(3), patch.object(missed_scan.frappe, "logger") as logger:
			self.assertEqual(self._found(tickets), tickets)
			logger.return_value.warning.assert_not_called()

			tickets.append(self._ticket(creation=OLD_ENOUGH + timedelta(seconds=2)))
			self.assertEqual(self._found(tickets), tickets)
		self.assertEqual(
			logger.return_value.warning.call_args_list,
			[unittest_call("missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét", 3)],
		)
		self.assertEqual(getattr(missed_scan, "SCAN_CANDIDATE_LIMIT", None), 1000)

	def _scan_with_error(self, target, attribute, side_effect):
		"""Run the scan with `target.attribute` raising; returns (log_error mock, logger mock). No exception may escape."""
		self._enable_agent()
		with (
			patch.object(target, attribute, side_effect=side_effect),
			patch("frappe.enqueue"),
			patch.object(missed_scan.frappe, "log_error") as log_error,
			patch.object(missed_scan.frappe, "logger") as logger,
		):
			missed_scan.scan_missed_tickets(NOW)
		return log_error, logger

	def _assert_one_constant_title_error(self, log_error, tickets, message="missed_scan error=RuntimeError"):
		"""D-17: exactly one log_error, constant title, message names only the exception type (no ticket data)."""
		self.assertEqual(log_error.call_args_list, [unittest_call(TITLE_RUN_FAILED, message)])
		logged = " ".join(str(arg) for arg in log_error.call_args.args)
		self.assertNotIn(SECRET_TEXT, logged)
		for ticket in tickets:
			self.assertNotIn(ticket, logged)

	def test_ticket_that_always_raises_does_not_starve_newer_ones(self):
		"""AC-16 (design-w1-fixes-17 Điểm 2): a predicate error on the oldest ticket skips only that ticket."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(3)]
		real_can_send = policy.can_send_ticket

		def can_send_ticket(name):
			if name == tickets[0]:
				raise RuntimeError(SECRET_TEXT)
			return real_can_send(name)

		self._enable_agent()
		with (
			patch.object(policy, "can_send_ticket", side_effect=can_send_ticket),
			patch.object(queue, "enqueue_agent_run", wraps=queue.enqueue_agent_run) as enqueue_agent_run,
			patch("frappe.enqueue"),
			patch.object(missed_scan.frappe, "log_error") as log_error,
			patch.object(missed_scan.frappe, "logger") as logger,
		):
			missed_scan.scan_missed_tickets(NOW)

		self.assertEqual([queued.args[0] for queued in enqueue_agent_run.call_args_list], tickets[1:])
		self._assert_one_constant_title_error(
			log_error, tickets, message="missed_scan failed=1 error=RuntimeError"
		)
		self.assertEqual(
			logger.return_value.method_calls,
			[unittest_call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 1, 2)],
		)

	def test_enqueue_error_on_one_ticket_still_queues_the_rest(self):
		"""An enqueue error on the second ticket does not stop the run: the third is still queued (D-17 one line)."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(3)]
		log_error, logger = self._scan_with_error(
			queue, "enqueue_agent_run", [True, RuntimeError(SECRET_TEXT), True]
		)
		self._assert_one_constant_title_error(
			log_error, tickets, message="missed_scan failed=1 error=RuntimeError"
		)
		self.assertEqual(
			logger.return_value.method_calls,
			[unittest_call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 1, 2)],
		)

	def test_per_ticket_failures_stop_at_the_cap(self):
		"""D-16: per-ticket errors stop the run once SCAN_MAX_FAILURES is reached."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(3)]
		self._enable_agent()
		with (
			patch.object(missed_scan, "SCAN_MAX_FAILURES", 2, create=True),
			patch.object(policy, "can_send_ticket", side_effect=RuntimeError(SECRET_TEXT)) as can_send,
			patch("frappe.enqueue"),
			patch.object(missed_scan.frappe, "log_error") as log_error,
			patch.object(missed_scan.frappe, "logger") as logger,
		):
			missed_scan.scan_missed_tickets(NOW)

		self.assertEqual(can_send.call_count, 2)
		self._assert_one_constant_title_error(
			log_error, tickets, message="missed_scan failed=2 error=RuntimeError"
		)
		self.assertEqual(
			logger.return_value.method_calls,
			[unittest_call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 2, 0)],
		)
		self.assertEqual(getattr(missed_scan, "SCAN_MAX_FAILURES", None), missed_scan.SCAN_BATCH)

	def test_run_level_error_logged_once_and_swallowed(self):
		"""D-17 run-level error path (unchanged from T34): one log_error, one logger line, no exception escapes."""
		tickets = [self._ticket(creation=OLD_ENOUGH + timedelta(seconds=second)) for second in range(2)]
		log_error, logger = self._scan_with_error(policy, "is_enabled", RuntimeError(SECRET_TEXT))
		self._assert_one_constant_title_error(log_error, tickets)
		self.assertEqual(
			logger.return_value.method_calls,
			[unittest_call.error("missed_scan: lỗi %s, đã xếp %s phiếu", "RuntimeError", 0)],
		)

	def test_find_without_failures_list_still_raises(self):
		"""Called without `failures`, find_missed_tickets lets a predicate error escape as before (T33)."""
		self._ticket()
		with patch.object(policy, "can_send_ticket", side_effect=RuntimeError(SECRET_TEXT)):
			with self.assertRaises(RuntimeError):
				missed_scan.find_missed_tickets(NOW)
