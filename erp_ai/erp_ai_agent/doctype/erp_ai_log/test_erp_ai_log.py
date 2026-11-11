import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import HELPDESK_AGENT_ROLE, LOG_DOCTYPE, ROLE_AGENT

AI_USER = "erp-ai-log-agent@example.com"
HD_AGENT_USER = "erp-ai-log-hd-agent@example.com"
USD_FIELDS = ("cost_usd",)
LOG_FIELDS = (
	"ticket",
	"run_id",
	"entry_type",
	"turn",
	"trigger",
	"instructor",
	"model",
	"input_tokens",
	"output_tokens",
	"cache_creation_input_tokens",
	"cache_read_input_tokens",
	"cost_usd",
	"credential_label",
	"keys_tried",
	"latency_ms",
	"stop_reason",
	"tools_called",
	"actions",
	"value_before",
	"value_after",
	"predicted_category",
	"predicted_confidence",
	"predicted_ticket_type",
	"predicted_agent_group",
	"predicted_priority",
	"applied",
	"human_corrected_to",
	"human_corrected_by",
	"human_corrected_at",
	"error",
)


def _make_user(email, role):
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)


def _new_log(**fields):
	values = {"doctype": LOG_DOCTYPE, "run_id": "abc123", "entry_type": "classify", "turn": 0}
	values.update(fields)
	return frappe.get_doc(values)


class TestERPAILog(FrappeTestCase):
	def setUp(self):
		self.assertTrue(frappe.db.exists("DocType", LOG_DOCTYPE), "DocType ERP AI Log is missing")
		# FrappeTestCase rolls back only after the whole class: undo each test, then start from a known baseline.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		_make_user(AI_USER, ROLE_AGENT)
		_make_user(HD_AGENT_USER, HELPDESK_AGENT_ROLE)

	def test_meta_has_all_log_fields_and_hash_naming(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		self.assertEqual(meta.module, "ERP AI agent")
		self.assertEqual(meta.autoname, "hash")
		for fieldname in LOG_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertIsNotNone(meta.get_field(fieldname))
		self.assertTrue(meta.get_field("ticket").search_index)
		self.assertTrue(meta.get_field("run_id").search_index)
		self.assertEqual(meta.get_field("ticket").options, "HD Ticket")

	def test_usd_fields_are_float_precision_6(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		for fieldname in USD_FIELDS:
			field = meta.get_field(fieldname)
			with self.subTest(fieldname=fieldname):
				self.assertEqual(field.fieldtype, "Float")
				self.assertEqual(str(field.precision), "6")
				self.assertIn("(USD)", field.label)

	def test_erp_ai_agent_account_can_create_and_read(self):
		frappe.set_user(AI_USER)
		doc = _new_log(model="m", cost_usd=0.000123, input_tokens=5).insert()
		self.assertTrue(frappe.has_permission(LOG_DOCTYPE, "read", doc=doc))
		self.assertEqual(frappe.get_doc(LOG_DOCTYPE, doc.name).cost_usd, 0.000123)

	def test_plain_hd_agent_gets_permission_error(self):
		frappe.set_user(HD_AGENT_USER)
		for ptype in ("read", "create"):
			self.assertFalse(frappe.has_permission(LOG_DOCTYPE, ptype), ptype)
		with self.assertRaises(frappe.PermissionError):
			_new_log().insert()

	def test_no_role_can_write_or_delete(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		roles = {p.role: p for p in meta.permissions}
		self.assertEqual(set(roles), {"System Manager", ROLE_AGENT})
		for role, perm in roles.items():
			for ptype in ("write", "delete", "submit", "cancel", "amend"):
				with self.subTest(role=role, ptype=ptype):
					self.assertFalse(perm.get(ptype))
		self.assertTrue(roles["System Manager"].read and roles["System Manager"].report)
		self.assertTrue(roles["System Manager"].export)
		self.assertFalse(roles["System Manager"].create)
		self.assertTrue(roles[ROLE_AGENT].read and roles[ROLE_AGENT].create)

	def test_agent_account_cannot_update_or_delete_existing_log(self):
		doc = _new_log().insert(ignore_permissions=True)
		frappe.set_user(AI_USER)
		for ptype in ("write", "delete"):
			self.assertFalse(frappe.has_permission(LOG_DOCTYPE, ptype, doc=doc), ptype)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc(LOG_DOCTYPE, doc.name)
