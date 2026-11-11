import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import run_log
from erp_ai.constants import HELPDESK_AGENT_ROLE, LOG_DOCTYPE, ROLE_AGENT
from erp_ai.test_utils import make_log_entry

AI_USER = "erpai-test-run-log-agent@example.com"
HD_AGENT_USER = "erpai-test-run-log-hd-agent@example.com"
KEYS_TRIED = [
	{"label": "ERPAI-TEST-k1", "outcome": "rate_limit"},
	{"label": "ERPAI-TEST-k2", "outcome": "ok"},
]
TOOLS_CALLED = ["get_ticket", "set_classification"]
ACTIONS = [{"tool": "set_classification", "doctype": "HD Ticket", "name": "1", "ok": True}]


def _make_user(email, role):
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)


class TestRunLog(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		_make_user(AI_USER, ROLE_AGENT)
		_make_user(HD_AGENT_USER, HELPDESK_AGENT_ROLE)

	def test_write_entry_serializes_json_and_requires_agent_role(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			run_id="ERPAI-TEST-run",
			entry_type="reason",
			trigger="comment_mention",
			turn=1,
			model="fake-model",
			input_tokens=7,
			cost_usd=0.000123,
			keys_tried=KEYS_TRIED,
			tools_called=TOOLS_CALLED,
			actions=ACTIONS,
			value_before={"priority": "Low"},
			value_after={"priority": "High"},
			error="Không phân loại được",
		)

		doc = frappe.get_doc(LOG_DOCTYPE, name)
		self.assertRegex(name, r"^[0-9a-z]{10}$")
		self.assertEqual(doc.owner, AI_USER)
		self.assertEqual(json.loads(doc.keys_tried), KEYS_TRIED)
		self.assertEqual(json.loads(doc.tools_called), TOOLS_CALLED)
		self.assertEqual(json.loads(doc.actions), ACTIONS)
		self.assertEqual(json.loads(doc.value_before), {"priority": "Low"})
		self.assertEqual(json.loads(doc.value_after), {"priority": "High"})
		self.assertEqual((doc.turn, doc.input_tokens, doc.cost_usd), (1, 7, 0.000123))
		self.assertEqual(doc.error, "Không phân loại được")

		frappe.set_user(HD_AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			run_log.write_entry(
				run_id="ERPAI-TEST-run", entry_type="classify", trigger="ticket_insert", turn=0
			)

	def test_write_entry_keeps_string_values_and_non_ascii_json(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			run_id="ERPAI-TEST-run",
			entry_type="skip",
			trigger="ticket_insert",
			turn=0,
			keys_tried='[{"a": 1}]',
			actions=[{"note": "Không phân loại"}],
		)

		doc = frappe.get_doc(LOG_DOCTYPE, name)
		self.assertEqual(doc.keys_tried, '[{"a": 1}]')
		self.assertIn("Không phân loại", doc.actions)

	def test_write_entry_rejects_missing_or_unknown_entry_type(self):
		frappe.set_user(AI_USER)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", trigger="ticket_insert", turn=0)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="bogus", trigger="ticket_insert", turn=0)

	def test_write_entry_rejects_missing_or_unknown_trigger(self):
		frappe.set_user(AI_USER)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", turn=0)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="bogus", turn=0)

	def test_write_entry_ignores_doctype_override(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			doctype="User", run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0
		)

		self.assertTrue(frappe.db.exists(LOG_DOCTYPE, name))

	def test_write_entry_commits_outside_tests(self):
		frappe.set_user(AI_USER)
		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		with patch.object(frappe.db, "commit") as commit:
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0)
		commit.assert_called_once_with()

	def test_write_entry_does_not_commit_in_tests(self):
		frappe.set_user(AI_USER)
		with patch.object(frappe.db, "commit") as commit:
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0)
		commit.assert_not_called()

	def test_make_log_entry_returns_name_of_saved_log(self):
		name = make_log_entry(model="fake-model")

		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "trigger"), "ticket_insert")
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "model"), "fake-model")
		self.assertTrue(frappe.db.get_value(LOG_DOCTYPE, name, "run_id"))
