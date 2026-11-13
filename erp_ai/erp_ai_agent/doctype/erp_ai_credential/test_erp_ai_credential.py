import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	KEY_STATUS_QUOTA_EXHAUSTED,
)


class TestERPAICredential(FrappeTestCase):
	def setUp(self):
		self.assertTrue(
			frappe.db.exists("DocType", CREDENTIAL_DOCTYPE),
			"DocType ERP AI Credential is missing",
		)
		self.meta = frappe.get_meta(CREDENTIAL_DOCTYPE)

	def test_is_child_table(self):
		self.assertTrue(self.meta.istable)

	def test_api_key_is_password_field(self):
		self.assertEqual(self.meta.get_field("api_key").fieldtype, "Password")

	def test_defaults(self):
		self.assertEqual(self.meta.get_field("status").default, KEY_STATUS_ACTIVE)
		self.assertEqual(int(self.meta.get_field("try_order").default), 10)
		self.assertEqual(int(self.meta.get_field("enabled").default), 1)

	def test_budget_month_is_float_precision_6_usd(self):
		field = self.meta.get_field("budget_month_usd")
		self.assertEqual(field.fieldtype, "Float")
		self.assertEqual(str(field.precision), "6")
		self.assertIn("(USD)", field.label)

	def test_status_options_and_read_only_rule(self):
		status = self.meta.get_field("status")
		self.assertEqual(
			status.options.split("\n"),
			[KEY_STATUS_ACTIVE, KEY_STATUS_PAUSED, KEY_STATUS_QUOTA_EXHAUSTED, KEY_STATUS_BAD_KEY],
		)
		self.assertEqual(status.read_only_depends_on, f"eval:doc.status!='{KEY_STATUS_BAD_KEY}'")

	def test_gateway_managed_fields_are_read_only(self):
		for fieldname in (
			"spent_month_usd",
			"paused_until",
			"tokens_remaining",
			"limit_reset_at",
			"error_count",
			"last_error",
			"last_success_at",
		):
			self.assertTrue(self.meta.get_field(fieldname).read_only, fieldname)
