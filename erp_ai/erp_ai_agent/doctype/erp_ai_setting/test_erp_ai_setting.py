import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	SETTING_DOCTYPE,
)
from erp_ai.test_utils import set_agent_settings

PRICES = {
	"price_input_per_mtok": 1,
	"price_cache_write_per_mtok": 1.25,
	"price_cache_read_per_mtok": 0.1,
	"price_output_per_mtok": 5,
}


def _settings_with_keys(*labels):
	"""Save the setting with the given key labels and return the reloaded document."""
	doc = frappe.get_doc(SETTING_DOCTYPE)
	doc.set("credentials", [])
	for label in labels:
		doc.append("credentials", {"label": label, "api_key": f"sk-{label}"})
	doc.save()
	return frappe.get_doc(SETTING_DOCTYPE)


class TestERPAISetting(FrappeTestCase):
	def setUp(self):
		self.assertTrue(
			frappe.db.exists("DocType", SETTING_DOCTYPE),
			"DocType ERP AI Setting is missing",
		)

	def test_default_mapping_and_default_disabled_l0(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		self.assertTrue(meta.issingle)
		self.assertEqual(meta.module, "ERP AI agent")
		self.assertEqual(json.loads(meta.get_field("category_mapping").default), DEFAULT_CATEGORY_MAPPING)
		self.assertEqual(int(meta.get_field("enabled").default), 0)
		self.assertEqual(meta.get_field("permission_level").default, "L0")
		self.assertEqual(meta.get_field("credentials").options, CREDENTIAL_DOCTYPE)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		self.assertFalse(doc.enabled)
		self.assertEqual(doc.permission_level, "L0")
		self.assertEqual(json.loads(doc.category_mapping), DEFAULT_CATEGORY_MAPPING)

	def test_hd_agent_cannot_read_or_write_settings(self):
		email = "erp-ai-hd-agent@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.new_doc("User")
			user.update({"email": email, "first_name": "HD Agent", "send_welcome_email": 0})
			user.append("roles", {"role": "Agent"})
			user.insert(ignore_permissions=True)
		for ptype in ("read", "write"):
			self.assertFalse(frappe.has_permission(SETTING_DOCTYPE, ptype, user=email), ptype)
		self.assertTrue(frappe.has_permission(SETTING_DOCTYPE, "read", user="Administrator"))
		roles = {p.role for p in frappe.get_meta(SETTING_DOCTYPE).permissions}
		self.assertEqual(roles, {"System Manager"})

	def test_self_managed_fields_restored_on_human_save(self):
		set_agent_settings(spent_this_month_usd=3.5)
		doc = _settings_with_keys("k1")
		row = doc.credentials[0]
		frappe.db.set_value(
			CREDENTIAL_DOCTYPE,
			row.name,
			{"status": KEY_STATUS_PAUSED, "error_count": 4, "last_error": "rate_limit 429 req_1"},
		)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].status = KEY_STATUS_ACTIVE
		doc.credentials[0].error_count = 0
		doc.credentials[0].last_error = ""
		doc.spent_this_month_usd = 0
		doc.save()
		stored = frappe.db.get_value(
			CREDENTIAL_DOCTYPE, row.name, ["status", "error_count", "last_error"], as_dict=True
		)
		self.assertEqual(stored.status, KEY_STATUS_PAUSED)
		self.assertEqual(stored.error_count, 4)
		self.assertEqual(stored.last_error, "rate_limit 429 req_1")
		self.assertEqual(float(frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")), 3.5)

	def test_new_key_row_gets_default_self_managed_fields(self):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("credentials", [])
		doc.append(
			"credentials",
			{"label": "fresh", "api_key": "sk-x", "status": KEY_STATUS_BAD_KEY, "error_count": 9},
		)
		doc.save()
		row = frappe.get_doc(SETTING_DOCTYPE).credentials[0]
		self.assertEqual(row.status, KEY_STATUS_ACTIVE)
		self.assertEqual(row.error_count, 0)

	def test_human_can_move_key_error_to_active_only(self):
		doc = _settings_with_keys("k1", "k2")
		bad, paused = doc.credentials[0], doc.credentials[1]
		frappe.db.set_value(
			CREDENTIAL_DOCTYPE,
			bad.name,
			{"status": KEY_STATUS_BAD_KEY, "error_count": 5, "last_error": "auth 401 req_2"},
		)
		frappe.db.set_value(CREDENTIAL_DOCTYPE, paused.name, "status", KEY_STATUS_PAUSED)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].status = KEY_STATUS_ACTIVE
		doc.credentials[1].status = KEY_STATUS_ACTIVE
		doc.save()
		moved = frappe.db.get_value(
			CREDENTIAL_DOCTYPE, bad.name, ["status", "error_count", "last_error"], as_dict=True
		)
		self.assertEqual(moved.status, KEY_STATUS_ACTIVE)
		self.assertEqual(moved.error_count, 0)
		self.assertFalse(moved.last_error)
		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, paused.name, "status"), KEY_STATUS_PAUSED)
		# A human cannot move an active key back to the error state.
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].status = KEY_STATUS_BAD_KEY
		doc.save()
		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, bad.name, "status"), KEY_STATUS_ACTIVE)

	def test_validation_rejects_bad_mapping_limits_and_missing_prices(self):
		def saved_with(**fields):
			doc = frappe.get_doc(SETTING_DOCTYPE)
			doc.update(fields)
			doc.save()

		bad_values = [
			{"category_mapping": "not json"},
			{"category_mapping": json.dumps({"Z": {}})},
			{"max_turns_per_run": 0},
			{"max_turns_per_run": 21},
			{"max_runs_per_ticket_per_day": 51},
			{"max_keys_per_call": 11},
			{"request_timeout_s": 4},
			{"request_timeout_s": 301},
			{"monthly_budget_usd": -1},
			{"price_output_per_mtok": -1},
			{"enabled": 1, **PRICES, "price_output_per_mtok": 0},
			{"enabled": 1, **PRICES, "trigger_keyword": " "},
		]
		for fields in bad_values:
			with self.subTest(fields=fields), self.assertRaises(frappe.ValidationError):
				saved_with(**fields)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("credentials", [])
		doc.append("credentials", {"label": "Dup", "api_key": "a"})
		doc.append("credentials", {"label": "dup", "api_key": "b"})
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		saved_with(enabled=1, credentials=[], **PRICES)
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"), 1)

	def test_set_agent_settings_writes_values(self):
		set_agent_settings(enabled=1, permission_level="L1")
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L1")
