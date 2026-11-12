from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from helpdesk.test_utils import make_ticket

from erp_ai.agent import policy
from erp_ai.constants import LOG_DOCTYPE, SETTING_DOCTYPE
from erp_ai.test_utils import set_agent_settings

TEAM = "Nhân sự & Hành chính"


def _ensure_team(name):
	"""Create the HD Team inside the current transaction if missing."""
	if frappe.db.exists("HD Team", name):
		return
	frappe.get_doc({"doctype": "HD Team", "team_name": name, "users": [{"user": "Administrator"}]}).insert(
		ignore_permissions=True
	)


TEAMS = (TEAM, "IT")


class TestPolicy(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert makes an Assignment Rule that Frappe caches in Redis; the DB
		# rollback leaves that entry stale. Registered first so it runs AFTER the rollback.
		# (Never delete_doc HD Team: HDTeam.on_trash commits the transaction.)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		# Teams are created inside each test transaction and rolled back; any commit during a
		# test would leak them (FrappeTestCase's own class-level commits happen outside setUp).
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(
			enabled=0,
			trigger_keyword="@ai",
			excluded_teams=f"{TEAM}\nTài chính Kế toán",
			permission_level="L2",
			monthly_budget_usd=10,
			spent_this_month_usd=0,
		)
		for name in TEAMS:
			_ensure_team(name)

	def _ticket(self, **values):
		ticket = make_ticket(subject="T20 policy ticket")
		for key, value in values.items():
			frappe.db.set_value("HD Ticket", ticket.name, key, value)
		return ticket.name

	def _settings(self, **fields):
		set_agent_settings(**fields)
		return frappe.get_doc(SETTING_DOCTYPE)

	def test_is_enabled_follows_setting(self):
		self.assertFalse(policy.is_enabled())
		set_agent_settings(enabled=1)
		self.assertTrue(policy.is_enabled())

	def test_field_names_are_exported(self):
		self.assertEqual(policy.OPT_OUT_FIELD, "ai_opt_out")
		self.assertEqual(policy.EXCLUDED_TEAMS_FIELD, "excluded_teams")
		self.assertIn(policy.OPT_OUT_FIELD, policy.SEND_POLICY_FIELDS)
		self.assertIn("agent_group", policy.SEND_POLICY_FIELDS)

	def test_ticket_without_team_can_send(self):
		self.assertTrue(policy.can_send_ticket(self._ticket()))

	def test_opt_out_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(self._ticket(**{policy.OPT_OUT_FIELD: 1})))

	def test_excluded_team_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_other_team_can_send(self):
		self.assertTrue(policy.can_send_ticket(self._ticket(agent_group="IT")))

	def test_excluded_team_matches_ignoring_case_and_spaces(self):
		set_agent_settings(excluded_teams="  nhân  sự &   HÀNH chính \n")
		self.assertFalse(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_blank_excluded_teams_excludes_nobody(self):
		set_agent_settings(excluded_teams="\n  \n")
		self.assertTrue(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_is_excluded_team_same_normalization(self):
		set_agent_settings(excluded_teams="  nhân  sự &   HÀNH chính \n\nIT  Support")
		self.assertTrue(policy.is_excluded_team(TEAM))
		self.assertTrue(policy.is_excluded_team("  NHÂN sự & hành   CHÍNH "))
		self.assertTrue(policy.is_excluded_team("it support"))
		self.assertFalse(policy.is_excluded_team("IT"))
		self.assertFalse(policy.is_excluded_team(""))
		self.assertFalse(policy.is_excluded_team(None))
		set_agent_settings(excluded_teams="\n  \n")
		self.assertFalse(policy.is_excluded_team(TEAM))

	def test_auto_assign_enabled_reads_switch(self):
		self.assertTrue(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=1)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=0)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=None)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict()))
		self.assertFalse(policy.auto_assign_enabled(object()))

	def test_missing_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket("T20-NOT-A-TICKET"))

	def test_empty_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(None))

	def test_accepts_dict_and_document(self):
		name = self._ticket(agent_group=TEAM)
		self.assertFalse(policy.can_send_ticket({"agent_group": TEAM}))
		self.assertFalse(policy.can_send_ticket(frappe.get_doc("HD Ticket", name)))
		self.assertTrue(policy.can_send_ticket({"agent_group": "IT", policy.OPT_OUT_FIELD: 0}))
		self.assertFalse(policy.can_send_ticket({"agent_group": "IT", policy.OPT_OUT_FIELD: 1}))

	def test_contains_keyword_ignores_case(self):
		self.assertTrue(policy.contains_keyword("xin chào @AI giúp tôi"))
		self.assertFalse(policy.contains_keyword("không nhắc ai"))
		self.assertFalse(policy.contains_keyword(None))

	def test_contains_keyword_ignores_case_of_configured_keyword(self):
		set_agent_settings(trigger_keyword="@AI")
		self.assertTrue(policy.contains_keyword("xin chào @ai giúp tôi"))

	def test_empty_keyword_never_matches(self):
		set_agent_settings(trigger_keyword="")
		self.assertFalse(policy.contains_keyword("anything @ai"))

	def test_get_trigger_keyword_matches_contains_keyword(self):
		for configured in ("@AI", " @ai ", "", None):
			with self.subTest(configured=configured):
				set_agent_settings(trigger_keyword=configured)
				keyword = policy.get_trigger_keyword()
				self.assertEqual(keyword, configured or "")
				if keyword:
					self.assertTrue(policy.contains_keyword(f"hi {keyword.upper()} there"))
				else:
					self.assertFalse(policy.contains_keyword("anything @ai"))

	def test_effective_level_over_budget_never_raises(self):
		cases = [("L3", "L1"), ("L2", "L1"), ("L1", "L1"), ("L0", "L0")]
		for level, expected in cases:
			with self.subTest(level=level):
				settings = self._settings(
					permission_level=level, monthly_budget_usd=10, spent_this_month_usd=10.5
				)
				self.assertEqual(policy.effective_level(settings), expected)

	def test_effective_level_at_budget_does_not_lower(self):
		settings = self._settings(permission_level="L3", monthly_budget_usd=10, spent_this_month_usd=10)
		self.assertEqual(policy.effective_level(settings), "L3")

	def test_effective_level_under_budget_unchanged(self):
		settings = self._settings(permission_level="L2", spent_this_month_usd=1)
		self.assertEqual(policy.effective_level(settings), "L2")

	def _log(self, ticket, run_id, entry_type="classify", created=None):
		log = frappe.get_doc(
			{"doctype": LOG_DOCTYPE, "ticket": ticket, "run_id": run_id, "entry_type": entry_type, "turn": 0}
		).insert(ignore_permissions=True)
		if created:
			frappe.db.set_value(LOG_DOCTYPE, log.name, "creation", created, update_modified=False)

	def test_runs_today_counts_distinct_runs_of_classify_and_reason(self):
		ticket = self._ticket()
		self._log(ticket, "r1", "classify")
		self._log(ticket, "r1", "reason")
		self._log(ticket, "r2", "reason")
		self._log(ticket, "r3", "skip")
		self._log(self._ticket(), "other", "classify")
		self.assertEqual(policy.runs_today(ticket), 2)

	def test_runs_today_ignores_yesterday(self):
		ticket = self._ticket()
		self._log(ticket, "old", "classify", created=now_datetime() - timedelta(days=1, minutes=1))
		self._log(ticket, "new", "classify")
		self.assertEqual(policy.runs_today(ticket), 1)

	def test_runs_today_uses_given_now(self):
		ticket = self._ticket()
		self._log(ticket, "r1", "classify")
		tomorrow = datetime.combine(now_datetime().date() + timedelta(days=1), datetime.min.time())
		self.assertEqual(policy.runs_today(ticket, now=tomorrow + timedelta(hours=1)), 0)
		self.assertEqual(policy.runs_today(ticket, now=now_datetime()), 1)

	def test_runs_today_counts_creation_exactly_at_midnight(self):
		ticket = self._ticket()
		midnight = datetime.combine(now_datetime().date(), datetime.min.time())
		self._log(ticket, "edge", "classify", created=midnight)
		self._log(ticket, "before", "classify", created=midnight - timedelta(seconds=1))
		self.assertEqual(policy.runs_today(ticket, now=midnight + timedelta(hours=12)), 1)
