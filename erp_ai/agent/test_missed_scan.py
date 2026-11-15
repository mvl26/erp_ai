from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import missed_scan, policy
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT
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
