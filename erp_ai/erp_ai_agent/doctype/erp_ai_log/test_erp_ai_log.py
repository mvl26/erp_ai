import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import run_log
from erp_ai.constants import HELPDESK_AGENT_ROLE, LOG_DOCTYPE, ROLE_AGENT, ROLE_INSTRUCTOR
from erp_ai.test_utils import keep_agent_settings

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
	"skipped_fields",
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


SMALL_TEXT_MAX_BYTES = 65535


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

	def test_skipped_fields_is_read_only_small_text(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		field = meta.get_field("skipped_fields")
		self.assertIsNotNone(field, "skipped_fields is missing")
		self.assertEqual(field.fieldtype, "Small Text")
		self.assertEqual(field.read_only, 1)
		self.assertEqual(field.permlevel or 0, 0)
		order = [f.fieldname for f in meta.fields]
		self.assertEqual(order.index("skipped_fields"), order.index("value_after") + 1)
		# Read-only does not open a write path: the agent role still cannot update an existing row.
		doc = _new_log(skipped_fields='[{"field": "ticket_type", "reason": "x"}]').insert(
			ignore_permissions=True
		)
		frappe.set_user(AI_USER)
		self.assertFalse(frappe.has_permission(LOG_DOCTYPE, "write", doc=doc))

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
		self.assertEqual(set(roles), {"System Manager", ROLE_AGENT, ROLE_INSTRUCTOR})
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


def _actions_just_over_small_text(byte_size):
	"""One `actions` entry whose JSON is exactly `byte_size` UTF-8 bytes, mostly 3-byte Vietnamese letters."""
	entry = run_log.action_entry("post_comment", "Comment", None, True)
	entry["note"] = ""
	base = len(json.dumps([entry], ensure_ascii=False).encode("utf-8"))
	letters, ascii_tail = divmod(byte_size - base, len("ệ".encode()))
	entry["note"] = "ệ" * letters + "a" * ascii_tail
	return [entry]


class TestActionsLongText(FrappeTestCase):
	"""FEAT-007 D-6 / F-6: `actions` is Long Text, so a JSON list over the old 64 KB Small Text limit fits."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)

	def test_write_entry_actions_over_65535_bytes_round_trips(self):
		actions = _actions_just_over_small_text(SMALL_TEXT_MAX_BYTES + 1)
		written = json.dumps(actions, ensure_ascii=False)
		# Over the limit in bytes only: the character count stays far below it.
		self.assertEqual(len(written.encode("utf-8")), SMALL_TEXT_MAX_BYTES + 1)
		self.assertLess(len(written), SMALL_TEXT_MAX_BYTES)
		name = run_log.write_entry(entry_type="reason", trigger="ticket_insert", actions=actions)
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "actions"), written)

	def test_actions_fieldtype_long_text(self):
		self.assertEqual(frappe.get_meta(LOG_DOCTYPE).get_field("actions").fieldtype, "Long Text")

	def test_actions_column_is_longtext(self):
		data_type = frappe.db.sql(
			"""select DATA_TYPE from information_schema.columns
			where table_schema = database() and table_name = %s and column_name = %s""",
			(f"tab{LOG_DOCTYPE}", "actions"),
		)
		self.assertEqual(data_type[0][0].lower(), "longtext")


class TestOptions(FrappeTestCase):
	def test_entry_type_and_trigger_options(self):
		# FEAT-007 U3 2, U6b-fixes Sửa 3: five entry types, seven triggers, in this order; run_log holds the same constants.
		meta = frappe.get_meta(LOG_DOCTYPE)
		self.assertEqual(
			meta.get_field("entry_type").options.split("\n"),
			["classify", "reason", "skip", "change", "bot_action"],
		)
		self.assertEqual(
			meta.get_field("trigger").options.split("\n"),
			[
				"ticket_insert",
				"comment_mention",
				"requester_reply",
				"kb_draft",
				"change_action",
				"setting_save",
				"scheduled_job",
			],
		)
		self.assertEqual(tuple(meta.get_field("entry_type").options.split("\n")), run_log.ENTRY_TYPES)
		self.assertEqual(
			meta.get_field("trigger").options.split("\n"),
			[*run_log.TRIGGERS, *run_log.CHANGE_TRIGGERS, *run_log.BOT_ACTION_TRIGGERS],
		)
