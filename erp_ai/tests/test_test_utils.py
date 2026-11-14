import hashlib
import json
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import remove_encrypted_password, set_encrypted_password

from erp_ai.constants import AGENT_USER, CREDENTIAL_DOCTYPE, HELPDESK_AGENT_ROLE, ROLE_AGENT, SETTING_DOCTYPE
from erp_ai.test_utils import (
	PREFIX,
	add_credential,
	keep_agent_settings,
	make_active_agent,
	make_routing_rules,
	make_sla,
	make_team,
	pin_agent_roles,
	set_agent_settings,
)

AUTOMATIC_ROLES = {"Guest", "All", "Administrator", "Desk User"}
STRAY_ROLE = "Blogger"
PINNED = (ROLE_AGENT, HELPDESK_AGENT_ROLE)


def _roles() -> set[str]:
	return set(frappe.get_all("Has Role", filters={"parent": AGENT_USER, "parenttype": "User"}, pluck="role"))


def _rows() -> list[tuple]:
	rows = frappe.get_all(
		"Has Role",
		filters={"parent": AGENT_USER, "parenttype": "User"},
		fields=["name", "role", "parentfield"],
		order_by="name",
	)
	return [(row.name, row.role, row.parentfield) for row in rows]


class TestPinAgentRoles(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def test_pin_agent_roles_sets_exact_set_and_restores(self):
		if STRAY_ROLE not in _roles():
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": STRAY_ROLE,
				}
			).insert(ignore_permissions=True)
		before_rows = _rows()
		inner = unittest.TestCase()

		pin_agent_roles(inner)

		self.assertEqual(_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})
		self.assertIn(ROLE_AGENT, frappe.get_roles(AGENT_USER))
		self.assertNotIn(STRAY_ROLE, frappe.get_roles(AGENT_USER))

		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)
		self.assertIn(STRAY_ROLE, _roles())

	def test_pin_agent_roles_restores_state_changed_after_pinning(self):
		before_rows = _rows()
		inner = unittest.TestCase()
		pin_agent_roles(inner)
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ROLE_AGENT})

		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)

	def _add_role(self, role):
		if role not in _roles():
			frappe.get_doc(
				{
					"doctype": "Has Role",
					"parent": AGENT_USER,
					"parenttype": "User",
					"parentfield": "roles",
					"role": role,
				}
			).insert(ignore_permissions=True)

	def test_pin_agent_roles_adds_missing_pinned_roles(self):
		cases = {
			"agent role missing": (ROLE_AGENT,),
			"helpdesk role missing": (HELPDESK_AGENT_ROLE,),
			"both missing": (ROLE_AGENT, HELPDESK_AGENT_ROLE),
		}
		for label, missing in cases.items():
			with self.subTest(label):
				for role in PINNED:
					self._add_role(role)
				frappe.db.delete(
					"Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ("in", list(missing))}
				)
				before_rows = _rows()
				self.assertFalse(set(missing) & _roles())
				inner = unittest.TestCase()

				pin_agent_roles(inner)

				self.assertEqual(_roles() - AUTOMATIC_ROLES, set(PINNED))
				self.assertLessEqual(set(PINNED), set(frappe.get_roles(AGENT_USER)))

				inner.doCleanups()

				self.assertEqual(_rows(), before_rows)
				self.assertFalse(set(missing) & _roles())

	def test_pin_agent_roles_keeps_automatic_roles(self):
		self._add_role("Desk User")
		before_rows = _rows()
		inner = unittest.TestCase()

		pin_agent_roles(inner)

		self.assertIn("Desk User", _roles())
		inner.doCleanups()

		self.assertEqual(_rows(), before_rows)
		self.assertIn("Desk User", _roles())

	def test_pin_agent_roles_clears_cache_even_when_restore_fails(self):
		inner = unittest.TestCase()
		with patch.object(frappe, "clear_cache") as clear_cache:
			pin_agent_roles(inner)
			clear_cache.reset_mock()
			with patch.object(frappe.db, "delete", side_effect=RuntimeError("restore failed")):
				self.assertFalse(inner.doCleanups())

		clear_cache.assert_called_once_with(user=AGENT_USER)


class TestMakeHelpers(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def test_make_routing_rules_is_valid_shape_without_users(self):
		rules = json.loads(make_routing_rules())
		self.assertEqual(set(rules), {"assignees", "departments", "importance_priority", "expected_sla"})
		self.assertEqual(set(rules["assignees"]), {"A", "B", "C", "F"})
		self.assertEqual(rules["assignees"]["A"], {"default": "", "prefixes": {}})
		self.assertEqual(rules["importance_priority"], {"1": "", "2": "High", "3": "High"})
		self.assertEqual(set(rules["expected_sla"]), set("ABCDEF"))

	def test_make_routing_rules_overrides_replace_top_level_keys(self):
		departments = {"Kế toán": {"team": "T", "head": "u@example.com"}}
		rules = json.loads(make_routing_rules(departments=departments))
		self.assertEqual(rules["departments"], departments)
		self.assertEqual(set(rules["assignees"]), {"A", "B", "C", "F"})

	def test_make_active_agent_returns_active_hd_agent(self):
		user = make_active_agent(self)
		self.assertTrue(user)
		self.assertNotEqual(user, AGENT_USER)
		self.assertEqual(frappe.db.get_value("HD Agent", {"user": user}, "is_active"), 1)
		self.assertNotEqual(make_active_agent(self), user)

	def test_make_team_with_rule_has_enabled_rule(self):
		member = make_active_agent(self)
		team = make_team(self, with_rule=True, rule_users=(member,))
		self.assertTrue(frappe.db.exists("HD Team", team))
		self.assertTrue(team.startswith(PREFIX))
		rule = frappe.db.get_value("HD Team", team, "assignment_rule")
		self.assertTrue(rule)
		self.assertEqual(frappe.db.get_value("Assignment Rule", rule, "disabled"), 0)
		users = frappe.get_all("Assignment Rule User", filters={"parent": rule}, pluck="user")
		self.assertEqual(users, [member])

	def test_make_team_without_rule_has_no_assignment_rule(self):
		team = make_team(self)
		self.assertTrue(frappe.db.exists("HD Team", team))
		self.assertFalse(frappe.db.get_value("HD Team", team, "assignment_rule"))
		self.assertFalse(frappe.db.exists("Assignment Rule", {"name": ("like", f"{team}%")}))
		self.assertFalse(frappe.db.exists("Assignment Rule User", {"parent": ("like", f"{team}%")}))

	def test_make_sla_sets_condition_default_enabled(self):
		sla = make_sla(self, condition="doc.priority == 'High'", default=True, enabled=False)
		self.assertTrue(sla.startswith(PREFIX))
		values = frappe.db.get_value(
			"HD Service Level Agreement", sla, ["condition", "default_sla", "enabled"], as_dict=True
		)
		self.assertEqual(values.condition, "doc.priority == 'High'")
		self.assertEqual(values.default_sla, 1)
		self.assertEqual(values.enabled, 0)
		plain = make_sla(self)
		self.assertEqual(
			frappe.db.get_value(
				"HD Service Level Agreement", plain, ["default_sla", "enabled"], as_dict=True
			),
			{"default_sla": 0, "enabled": 1},
		)
		priorities = frappe.get_all("HD Service Level Priority", filters={"parent": plain}, pluck="priority")
		self.assertEqual(set(priorities), {"Low", "Medium", "High", "Urgent"})


def _setting_singles() -> list[tuple]:
	return [
		tuple(row)
		for row in frappe.db.sql(
			"select field, value from `tabSingles` where doctype=%s order by field", SETTING_DOCTYPE
		)
	]


def _credential_rows() -> list[dict]:
	return frappe.get_all(
		CREDENTIAL_DOCTYPE,
		filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE},
		fields=["*"],
		order_by="name",
	)


def _credential_auth_rows() -> list[tuple]:
	"""`__Auth` rows of ERP AI Credential; the stored (encrypted) value appears only as its sha256, never printed."""
	rows = frappe.db.sql(
		"select doctype, name, fieldname, password, encrypted from `__Auth` where doctype=%s",
		CREDENTIAL_DOCTYPE,
		as_dict=True,
	)
	return sorted(
		(
			row.doctype,
			row.name,
			row.fieldname,
			hashlib.sha256(row.password.encode("utf-8")).hexdigest(),
			row.encrypted,
		)
		for row in rows
	)


class TestKeepAgentSettings(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# The rollback empties `value_cache` but not the document cache the test fills.
		self.addCleanup(frappe.clear_document_cache, SETTING_DOCTYPE, SETTING_DOCTYPE)
		self.addCleanup(frappe.db.rollback)

	def test_restores_singles_and_child_rows(self):
		set_agent_settings(trigger_keyword=f"{PREFIX}keyword", thinking_text=f"{PREFIX}thinking")
		add_credential(f"{PREFIX}keep-A")
		add_credential(f"{PREFIX}keep-B")
		singles_before = _setting_singles()
		rows_before = _credential_rows()
		inner = unittest.TestCase()

		keep_agent_settings(inner)
		set_agent_settings(trigger_keyword=f"{PREFIX}changed")
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "thinking_text"})
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE, "label": f"{PREFIX}keep-A"})
		add_credential(f"{PREFIX}keep-new")
		self.assertNotEqual(_setting_singles(), singles_before)
		self.assertNotEqual(_credential_rows(), rows_before)
		# Fill both caches with the changed values; the raw-SQL restore does not touch them.
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword"), f"{PREFIX}changed")
		self.assertIsNone(frappe.get_cached_doc(SETTING_DOCTYPE).thinking_text)

		inner.doCleanups()

		self.assertEqual(_setting_singles(), singles_before)
		self.assertEqual(_credential_rows(), rows_before)
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword"), f"{PREFIX}keyword")
		self.assertEqual(frappe.get_cached_doc(SETTING_DOCTYPE).thinking_text, f"{PREFIX}thinking")

	def test_restores_auth_rows_of_credentials(self):
		# Own rows, so the test never depends on the site's credentials.
		changed = add_credential(f"{PREFIX}auth-changed")
		deleted = add_credential(f"{PREFIX}auth-deleted")
		auth_before = _credential_auth_rows()
		inner = unittest.TestCase()

		keep_agent_settings(inner)
		set_encrypted_password(CREDENTIAL_DOCTYPE, changed, f"sk-{PREFIX}FAKE-changed", "api_key")
		remove_encrypted_password(CREDENTIAL_DOCTYPE, deleted, "api_key")
		added = add_credential(f"{PREFIX}auth-added")
		auth_changed = _credential_auth_rows()
		self.assertNotEqual(auth_changed, auth_before)
		self.assertEqual(len(auth_changed), len(auth_before))
		self.assertIn(added, {row[1] for row in auth_changed})

		inner.doCleanups()

		self.assertEqual(_credential_auth_rows(), auth_before)
		self.assertEqual(len(_credential_auth_rows()), len(auth_before))
