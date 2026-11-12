from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import site_facts
from erp_ai.constants import AGENT_USER
from erp_ai.test_utils import make_active_agent, make_sla, make_team, pin_agent_roles


class TestSiteFacts(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert makes an Assignment Rule that Frappe caches in Redis; the DB
		# rollback leaves that entry stale. Registered first so it runs AFTER the rollback.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.ticket = make_ticket(subject="T13 site facts").name

	def _todo(self, allocated_to, status="Open", assignment_rule=None, ticket=None):
		return frappe.get_doc(
			{
				"doctype": "ToDo",
				"reference_type": "HD Ticket",
				"reference_name": ticket or self.ticket,
				"allocated_to": allocated_to,
				"status": status,
				"assignment_rule": assignment_rule,
				"description": "T13",
			}
		).insert(ignore_permissions=True)

	def test_assignments_include_closed_exclude_cancelled(self):
		open_user, closed_user, cancelled_user = (make_active_agent(self) for _ in range(3))
		rule = frappe.db.get_value("HD Team", make_team(self, with_rule=True), "assignment_rule")
		other_ticket = make_ticket(subject="T13 other").name
		self._todo(open_user, "Open", rule)
		self._todo(closed_user, "Closed")
		self._todo(cancelled_user, "Cancelled")
		self._todo(open_user, "Open", ticket=other_ticket)

		rows = site_facts.ticket_assignments(self.ticket)

		self.assertCountEqual(
			[(row["allocated_to"], row["assignment_rule"]) for row in rows],
			[(open_user, rule), (closed_user, None)],
		)
		self.assertEqual(site_facts.ticket_assignments("HD-TICKET-NOPE"), [])

	def test_has_linked_task_sees_other_owners_task(self):
		self.assertFalse(site_facts.has_linked_task(self.ticket))
		task = frappe.get_doc(
			{"doctype": "Task", "subject": "T13 task", "description": "T13", "ai_ticket": self.ticket}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Task", task.name, "owner", make_active_agent(self), update_modified=False)

		self.assertTrue(site_facts.has_linked_task(self.ticket))
		self.assertFalse(site_facts.has_linked_task(make_ticket(subject="T13 untouched").name))

	def test_is_active_agent_flags(self):
		user = make_active_agent(self)
		self.assertTrue(site_facts.is_active_agent(user))

		frappe.db.set_value("HD Agent", {"user": user}, "is_active", 0)
		self.assertFalse(site_facts.is_active_agent(user))
		self.assertFalse(site_facts.is_active_agent("nobody-t13@example.com"))
		self.assertFalse(site_facts.is_active_agent(""))

	def test_team_exists(self):
		self.assertTrue(site_facts.team_exists(make_team(self)))
		self.assertFalse(site_facts.team_exists("ERPAI-TEST-no-such-team"))
		self.assertFalse(site_facts.team_exists(""))

	def test_applied_sla_none_without_sla(self):
		frappe.db.set_value("HD Ticket", self.ticket, "sla", None)
		self.assertIsNone(site_facts.applied_sla(self.ticket))

	def test_applied_sla_reads_priority_row(self):
		sla = make_sla(self)
		frappe.db.set_value("HD Ticket", self.ticket, {"sla": sla, "priority": "High"})

		# High: response 2h, resolution 4 * 2h (make_sla)
		self.assertEqual(
			site_facts.applied_sla(self.ticket), {"sla": sla, "priority": "High", "resolution_s": 8 * 3600}
		)

	def test_facts_work_under_pinned_agent_roles(self):
		user = make_active_agent(self)
		team = make_team(self)
		sla = make_sla(self)
		frappe.db.set_value("HD Ticket", self.ticket, {"sla": sla, "priority": "Urgent"})
		self._todo(user)
		frappe.get_doc(
			{"doctype": "Task", "subject": "T13 pinned", "description": "T13", "ai_ticket": self.ticket}
		).insert(ignore_permissions=True)
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)

		self.assertEqual([row["allocated_to"] for row in site_facts.ticket_assignments(self.ticket)], [user])
		self.assertTrue(site_facts.has_linked_task(self.ticket))
		self.assertTrue(site_facts.is_active_agent(user))
		self.assertTrue(site_facts.team_exists(team))
		self.assertEqual(
			site_facts.applied_sla(self.ticket), {"sla": sla, "priority": "Urgent", "resolution_s": 4 * 3600}
		)
