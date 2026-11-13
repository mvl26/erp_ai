import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import run_log
from erp_ai.constants import HELPDESK_AGENT_ROLE, LOG_DOCTYPE, ROLE_AGENT
from erp_ai.test_utils import make_change_proposal, make_log_entry

AI_USER = "erpai-test-run-log-agent@example.com"
HD_AGENT_USER = "erpai-test-run-log-hd-agent@example.com"
KEYS_TRIED = [
	{"label": "ERPAI-TEST-k1", "outcome": "rate_limit"},
	{"label": "ERPAI-TEST-k2", "outcome": "ok"},
]
TOOLS_CALLED = ["get_ticket", "set_classification"]
ACTIONS = [{"tool": "set_classification", "doctype": "HD Ticket", "name": "1", "ok": True}]
# FEAT-004 design 2.5 / ADR-012 QĐ 6: the closed set of proposal steps and the single change trigger.
CHANGE_STEP_VALUES = ("propose", "approve", "reject", "apply", "fail", "stale", "undo")
CHANGE_TRIGGER = "change_action"
OLD_ENTRY_TYPES = ("classify", "reason", "skip")
MISSING = object()


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

	def _change_fields(self, proposal, **overrides):
		fields = {
			"ticket": proposal.ticket,
			"run_id": proposal.run_id,
			"entry_type": "change",
			"trigger": CHANGE_TRIGGER,
			"change_step": "approve",
			"actor": HD_AGENT_USER,
			"change_proposal": proposal.name,
		}
		fields.update(overrides)
		return {key: value for key, value in fields.items() if value is not MISSING}

	def test_change_entry_requires_step_actor_proposal_and_trigger(self):
		proposal = make_change_proposal()
		frappe.set_user(HD_AGENT_USER)
		log_count = frappe.db.count(LOG_DOCTYPE)
		bad_cases = {
			"trigger missing": {"trigger": MISSING},
			"trigger ticket_insert": {"trigger": "ticket_insert"},
			"trigger comment_mention": {"trigger": "comment_mention"},
			"trigger unknown": {"trigger": "bogus"},
			"change_step missing": {"change_step": MISSING},
			"change_step empty": {"change_step": ""},
			"change_step unknown": {"change_step": "commit"},
			"change_step wrong case": {"change_step": "Apply"},
			"actor missing": {"actor": MISSING},
			"actor empty": {"actor": ""},
			"actor blank": {"actor": "   "},
			"actor not a string": {"actor": ["Administrator"]},
			"change_proposal missing": {"change_proposal": MISSING},
			"change_proposal empty": {"change_proposal": ""},
			"change_proposal not a string": {"change_proposal": 7},
		}
		for case, overrides in bad_cases.items():
			with self.subTest(case=case), self.assertRaises(ValueError):
				run_log.write_entry(**self._change_fields(proposal, **overrides))
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), log_count)

		for entry_type in OLD_ENTRY_TYPES:
			with self.subTest(entry_type=entry_type), self.assertRaises(ValueError):
				run_log.write_entry(
					run_id="ERPAI-TEST-run", entry_type=entry_type, trigger=CHANGE_TRIGGER, turn=0
				)

		for step in CHANGE_STEP_VALUES:
			with self.subTest(step=step):
				name = run_log.write_entry(**self._change_fields(proposal, change_step=step))
				row = frappe.db.get_value(
					LOG_DOCTYPE,
					name,
					["entry_type", "trigger", "change_step", "actor", "change_proposal", "ticket"],
					as_dict=True,
				)
				self.assertEqual(
					row,
					{
						"entry_type": "change",
						"trigger": "change_action",
						"change_step": step,
						"actor": HD_AGENT_USER,
						"change_proposal": proposal.name,
						"ticket": proposal.ticket,
					},
				)

	def test_change_entry_keeps_git_keys_of_apply_and_undo_rows(self):
		proposal = make_change_proposal()
		before = {"sha256": "a" * 64, "head": "1" * 40}
		after = {"sha256": None, "commit": "2" * 40, "branch": "develop"}
		for step in ("apply", "undo"):
			with self.subTest(step=step):
				name = run_log.write_entry(
					**self._change_fields(proposal, change_step=step, value_before=before, value_after=after)
				)
				doc = frappe.get_doc(LOG_DOCTYPE, name)
				self.assertEqual(json.loads(doc.value_before), before)
				self.assertEqual(json.loads(doc.value_after), after)

	def test_change_entry_bypasses_permission_but_other_types_do_not(self):
		proposal = make_change_proposal()
		frappe.set_user(HD_AGENT_USER)
		self.assertFalse(frappe.has_permission(LOG_DOCTYPE, "create"))

		name = run_log.write_entry(**self._change_fields(proposal, change_step="reject"))

		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "owner"), HD_AGENT_USER)
		for entry_type in OLD_ENTRY_TYPES:
			with self.subTest(entry_type=entry_type), self.assertRaises(frappe.PermissionError):
				run_log.write_entry(
					run_id="ERPAI-TEST-run", entry_type=entry_type, trigger="ticket_insert", turn=0
				)

	def test_log_change_fields_match_design(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		self.assertEqual(
			meta.get_field("entry_type").options.split("\n"), ["classify", "reason", "skip", "change"]
		)
		self.assertEqual(
			meta.get_field("trigger").options.split("\n"),
			["ticket_insert", "comment_mention", "change_action"],
		)
		expected = {
			"change_proposal": ("Link", "ERP AI Change Proposal"),
			"change_step": ("Select", "propose\napprove\nreject\napply\nfail\nstale\nundo"),
			"actor": ("Link", "User"),
		}
		for fieldname, (fieldtype, options) in expected.items():
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field)
				self.assertEqual((field.fieldtype, field.options, field.read_only), (fieldtype, options, 1))

	def test_make_log_entry_returns_name_of_saved_log(self):
		name = make_log_entry(model="fake-model")

		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "trigger"), "ticket_insert")
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "model"), "fake-model")
		self.assertTrue(frappe.db.get_value(LOG_DOCTYPE, name, "run_id"))
