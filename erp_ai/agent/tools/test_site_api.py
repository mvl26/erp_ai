import datetime
import json
import os
import uuid
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import change_link, policy
from erp_ai.agent.policy import PermissionSwitches
from erp_ai.agent.tools import registry, site_api
from erp_ai.agent.tools.registry import ToolContext, execute_tool, get_tool_schemas
from erp_ai.constants import ROLE_AGENT, ROLE_INSTRUCTOR, TICKET_CONTENT_DOCTYPES
from erp_ai.test_utils import keep_agent_settings, make_log_entry, set_agent_settings

AGENT = "siteapi.agent@example.com"
PLAIN_AGENT = "siteapi.plain@example.com"
BOSS = "siteapi.boss@example.com"
NEW_USER = "siteapi.new@example.com"
ALLOWED_ROLE = "Stock User"
PROFILE = "SITEAPI Hồ sơ quản trị"
NOTE_TITLE = "SITEAPI-TEST ghi chú"
TOOL_NAMES = ["api_list_records", "api_get_record", "api_create_record", "api_update_record"]
UNRESTRICTED_TOOL_NAMES = ["api_delete_record", "api_submit_record", "api_call_method"]
NOT_GRANTED = {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}
APP_NAME = "erp_ai"
STUB_APP_DOCTYPE = "Note"
OTHER_PROFILE = "SITEAPI hồ sơ thường"
WEBHOOK_NAME = "SITEAPI-TEST webhook"
RENAMED_NOTE = "SITEAPI-TEST tên mới"
DUPLICATE_TAG = "SITEAPI-TEST nhãn trùng"
FAKE_SECRET = "SITEAPI-FAKE-SECRET-7f3a"
FAKE_PASSWORD = "SITEAPI-FAKE-PASSWORD-91c2"
FAKE_API_SECRET = "SITEAPI-FAKE-API-SECRET-4d8e"
HIDDEN = "[đã ẩn]"
SECRET_METHOD_REFUSED = "hàm này trả khóa API hoặc mật khẩu, không gọi qua công cụ"
SECRET_ARGUMENT_REFUSED = "tham số nhắc tới trường khóa API hoặc mật khẩu, không gọi qua công cụ"
COLUMN_SELECTOR_REFUSED = "tham số chọn mọi cột bằng *, hãy liệt kê tên trường cần lấy"
SPELLING_USER = "siteapi.spelling@example.com"
BANNED_PROFILE = "SITEAPI Ho so cam"
FORBIDDEN_REFUSAL = "vai trò không được gán qua công cụ: System Manager"
_real_get_all = frappe.get_all


def _app_doctypes():
	"""Every DocType of the app's modules, read independently of site_api."""
	modules = frappe.get_all("Module Def", {"app_name": APP_NAME}, pluck="name")
	return sorted(frappe.get_all("DocType", {"module": ["in", modules]}, pluck="name"))


def _get_all_with_stub_app_doctype(doctype, *args, **kwargs):
	"""`frappe.get_all` as if the stub DocType belonged to the app's module."""
	rows = _real_get_all(doctype, *args, **kwargs)
	filters = args[0] if args else kwargs.get("filters")
	if doctype == "DocType" and isinstance(filters, dict) and "module" in filters:
		rows = [*rows, STUB_APP_DOCTYPE]
	return rows


def _snapshot(doctype):
	if frappe.get_meta(doctype).issingle:
		return frappe.db.get_singles_dict(doctype)
	return frappe.db.count(doctype)


def _calls_naming(doctype):
	"""One call of every site_api tool on the DocType, keyed by tool name."""
	return {
		"api_list_records": {"doctype": doctype},
		"api_get_record": {"doctype": doctype, "name": doctype},
		"api_create_record": {"doctype": doctype, "values": {}},
		"api_update_record": {"doctype": doctype, "name": doctype, "values": {}},
		"api_delete_record": {"doctype": doctype, "name": doctype},
		"api_submit_record": {"doctype": doctype, "name": doctype, "action": "submit"},
		"api_call_method": {"method": "frappe.client.get_list", "arguments": {"doctype": doctype}},
	}


def _without_snapshot(result):
	"""The tool result less `_snapshot`, which is asserted on its own (AC-13)."""
	return {key: value for key, value in result.items() if key != "_snapshot"}


def _make_user(email, *roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "SITEAPI", "send_welcome_email": 0}
		).insert()
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)


def _context(
	level="L3", instructor=BOSS, change_enabled=True, agent_user=AGENT, unrestricted=False, record_tools=True
):
	return ToolContext(
		ticket_name="TKT-SITEAPI",
		effective_level=level,
		instructor=instructor,
		run_id="run-siteapi",
		category_mapping={},
		agent_user=agent_user,
		change_enabled=change_enabled,
		unrestricted=unrestricted,
		record_tools=record_tools,
	)


class TestSiteApiGrant(FrappeTestCase):
	def names(self, level, has_instructor, record_tools):
		inputs = registry.GrantInputs(
			level, level, has_instructor, PermissionSwitches(record_tools=record_tools)
		)
		granted = get_tool_schemas(inputs)
		return [spec["name"] for spec in granted if spec["name"] in TOOL_NAMES]

	def test_granted_only_with_switch_l3_and_instructor(self):
		self.assertEqual(self.names("L3", True, True), TOOL_NAMES)
		for level, has_instructor, change_enabled in (
			("L3", True, False),
			("L3", False, True),
			("L2", True, True),
			("L1", True, True),
			("L0", True, True),
		):
			self.assertEqual(
				self.names(level, has_instructor, change_enabled), [], (level, has_instructor, change_enabled)
			)

	def test_grants_site_admin_tools_matches_the_grant(self):
		def record_block(level, has_instructor, record_tools):
			switches = PermissionSwitches(record_tools=record_tools)
			return registry.grant(registry.GrantInputs(level, level, has_instructor, switches)).record_block

		self.assertIs(record_block("L3", True, True), True)
		self.assertIs(record_block("L3", True, False), False)
		self.assertIs(record_block("L3", False, True), False)
		self.assertIs(record_block("L2", True, True), False)

	def test_execute_refuses_when_not_granted(self):
		arguments = {"doctype": "Note", "values": {"title": NOTE_TITLE}}
		for context in (
			_context(record_tools=False),
			_context(instructor=None),
			_context(level="L2"),
		):
			result = execute_tool("api_create_record", arguments, context)
			self.assertEqual(result, {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"})
		self.assertFalse(frappe.db.exists("Note", {"title": NOTE_TITLE}))


class TestSiteApi(FrappeTestCase):
	def setUp(self):
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		# The tool goes through Frappe permissions: this agent account may manage users, the plain one may not.
		_make_user(AGENT, ROLE_AGENT, "System Manager")
		_make_user(PLAIN_AGENT, ROLE_AGENT)
		_make_user(BOSS, ROLE_INSTRUCTOR)
		frappe.set_user(AGENT)

	def run_tool(self, name, arguments, context=None):
		return execute_tool(name, arguments, context or _context())

	def create(self, doctype, values, context=None):
		return self.run_tool("api_create_record", {"doctype": doctype, "values": values}, context)

	def update(self, doctype, name, values):
		return self.run_tool("api_update_record", {"doctype": doctype, "name": name, "values": values})

	def user_values(self, **extra):
		return {"email": NEW_USER, "first_name": "Người mới", "send_welcome_email": 0, **extra}

	def roles_of(self, user):
		frappe.set_user("Administrator")
		roles = {row.role for row in frappe.get_doc("User", user).roles}
		frappe.set_user(AGENT)
		return roles

	def test_creates_user_with_an_allowed_role(self):
		result = self.create("User", self.user_values(roles=[{"role": ALLOWED_ROLE}]))
		self.assertEqual(
			{key: result[key] for key in ("ok", "doctype", "name", "value_before")},
			{"ok": True, "doctype": "User", "name": NEW_USER, "value_before": None},
		)
		self.assertEqual(set(result["value_after"]), {"email", "first_name", "send_welcome_email", "roles"})
		self.assertEqual(frappe.db.get_value("User", NEW_USER, "enabled"), 1)
		self.assertEqual(self.roles_of(NEW_USER), {ALLOWED_ROLE})

	def test_refuses_each_forbidden_role(self):
		for role in ("System Manager", "Administrator", ROLE_INSTRUCTOR, ROLE_AGENT, "Guest", "All"):
			result = self.create("User", self.user_values(roles=[{"role": ALLOWED_ROLE}, {"role": role}]))
			self.assertFalse(result["ok"], role)
			self.assertIn(role, result["reason"])
			self.assertFalse(frappe.db.exists("User", NEW_USER), role)

	def test_forbidden_roles_are_exactly_the_six_admin_roles_of_ac14(self):
		# Written out by hand so a role dropped from or added to the constant fails here.
		self.assertEqual(
			site_api.FORBIDDEN_ROLES,
			{"System Manager", "Administrator", "ERP AI Instructor", "ERP AI Agent", "Guest", "All"},
		)

	def test_refuses_adding_a_forbidden_role_to_an_existing_user(self):
		self.create("User", self.user_values())
		result = self.update("User", NEW_USER, {"roles": [{"role": "System Manager"}]})
		self.assertFalse(result["ok"])
		self.assertEqual(self.roles_of(NEW_USER), set())

	def test_refuses_role_profile_holding_a_forbidden_role(self):
		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": PROFILE, "roles": [{"role": "System Manager"}]}
		).insert()
		frappe.set_user(AGENT)
		result = self.create("User", self.user_values(role_profile_name=PROFILE))
		self.assertFalse(result["ok"])
		self.assertIn("System Manager", result["reason"])
		self.assertFalse(frappe.db.exists("User", NEW_USER))
		# `role_profiles` exists only on newer Frappe: refused either as a forbidden role or as an unknown field.
		result = self.create("User", self.user_values(role_profiles=[{"role_profile": PROFILE}]))
		self.assertFalse(result["ok"])
		self.assertFalse(frappe.db.exists("User", NEW_USER))

	def test_refuses_role_profile_edit_that_adds_a_forbidden_role(self):
		result = self.create("Role Profile", {"role_profile": PROFILE, "roles": [{"role": "System Manager"}]})
		self.assertFalse(result["ok"])
		self.assertFalse(frappe.db.exists("Role Profile", PROFILE))

	def test_refuses_denied_doctypes_on_every_tool(self):
		for doctype in ("ERP AI Setting", "ERP AI Credential", "ERP AI Log", "ERP AI Change Proposal"):
			calls = (
				("api_list_records", {"doctype": doctype}),
				("api_get_record", {"doctype": doctype, "name": doctype}),
				("api_create_record", {"doctype": doctype, "values": {"enabled": 0}}),
				("api_update_record", {"doctype": doctype, "name": doctype, "values": {"enabled": 0}}),
			)
			for name, arguments in calls:
				result = self.run_tool(name, arguments)
				self.assertFalse(result["ok"], (name, doctype))
				self.assertIn("không được phép", result["reason"])
		for doctype in ("Custom DocPerm", "Custom Role", "Salary Slip", "Employee", "GL Entry"):
			self.assertTrue(frappe.db.exists("DocType", doctype), doctype)
			result = self.create(doctype, {"role": ALLOWED_ROLE})
			self.assertFalse(result["ok"], doctype)
			self.assertIn("không được phép", result["reason"], doctype)

	def test_every_app_doctype_denied_for_every_tool_in_both_modes(self):
		doctypes = _app_doctypes()
		self.assertIn("ERP AI Change Proposal", doctypes)
		before = {doctype: _snapshot(doctype) for doctype in doctypes}
		for context in (_context(), _context(level="L1", change_enabled=False, unrestricted=True)):
			for doctype in doctypes:
				self.assert_closed_on_every_tool(doctype, context)
		self.assertEqual({doctype: _snapshot(doctype) for doctype in doctypes}, before)

	def test_doctype_added_to_the_app_module_is_denied(self):
		# A fifth DocType of the app is closed without editing site_api: Note stands in for it through a stub.
		before = _snapshot(STUB_APP_DOCTYPE)
		with patch.object(frappe, "get_all", side_effect=_get_all_with_stub_app_doctype):
			for context in (_context(), _context(level="L1", change_enabled=False, unrestricted=True)):
				self.assert_closed_on_every_tool(STUB_APP_DOCTYPE, context)
		self.assertEqual(_snapshot(STUB_APP_DOCTYPE), before)

	def assert_closed_on_every_tool(self, doctype, context):
		calls = _calls_naming(doctype)
		self.assertEqual(sorted(calls), sorted(spec.name for spec in site_api.TOOLS))
		for spec in site_api.TOOLS:
			with self.subTest(doctype=doctype, tool=spec.name, unrestricted=context.unrestricted):
				result = spec.handler(calls[spec.name], context)
				self.assertFalse(result["ok"])
				self.assertIn("không được phép", result["reason"])

	def test_normal_mode_denies_doctype_and_role_records(self):
		# developer_mode is on: a DocType save would export JSON into the frappe app, so the write is stubbed.
		for doctype, name, values in (
			("DocType", "Note", {"permissions": [{"role": ALLOWED_ROLE, "read": 1, "write": 1}]}),
			("Role", ALLOWED_ROLE, {"desk_access": 0}),
			("Custom DocPerm", "x", {"read": 1}),
			("Custom Role", "x", {"report": "x"}),
		):
			with self.subTest(doctype), patch.object(site_api, "_write") as write:
				result = self.update(doctype, name, values)
				self.assertFalse(result["ok"])
				self.assertIn("không được phép", result["reason"])
				write.assert_not_called()

	def test_lowercase_names_are_refused(self):
		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": PROFILE, "roles": [{"role": "System Manager"}]}
		).insert()
		frappe.set_user(AGENT)
		unrestricted = _context(level="L1", change_enabled=False, unrestricted=True)
		cases = (
			(
				"role",
				"api_create_record",
				{"doctype": "User", "values": self.user_values(roles=[{"role": "system manager"}])},
				"vai trò không được gán",
				None,
			),
			(
				"user doctype",
				"api_create_record",
				{"doctype": "user", "values": self.user_values(roles=[{"role": "System Manager"}])},
				"vai trò không được gán",
				None,
			),
			(
				"role profile of a user",
				"api_create_record",
				{"doctype": "User", "values": self.user_values(role_profile_name=PROFILE.lower())},
				"vai trò không được gán",
				None,
			),
			(
				"role in a role profile",
				"api_create_record",
				{
					"doctype": "role profile",
					"values": {"role_profile": OTHER_PROFILE, "roles": [{"role": "system manager"}]},
				},
				"vai trò không được gán",
				None,
			),
			(
				"administrator",
				"api_update_record",
				{"doctype": "User", "name": "administrator", "values": {"first_name": "Đổi"}},
				"không được sửa",
				None,
			),
			(
				"agent account",
				"api_update_record",
				{"doctype": "user", "name": AGENT.upper(), "values": {"first_name": "Đổi"}},
				"không được sửa",
				None,
			),
			(
				"app doctype",
				"api_get_record",
				{"doctype": "erp ai setting", "name": "erp ai setting"},
				"không được phép",
				None,
			),
			(
				"app doctype",
				"api_update_record",
				{"doctype": "erp ai setting", "name": "erp ai setting", "values": {"enabled": 0}},
				"không được phép",
				None,
			),
			(
				"app doctype unrestricted",
				"api_get_record",
				{"doctype": "erp ai setting", "name": "erp ai setting"},
				"không được phép",
				unrestricted,
			),
			(
				"app doctype unrestricted",
				"api_list_records",
				{"doctype": "erp ai change proposal"},
				"không được phép",
				unrestricted,
			),
			(
				"permission doctype",
				"api_list_records",
				{"doctype": "custom docperm"},
				"không được phép",
				None,
			),
		)
		for label, tool, arguments, reason, context in cases:
			with self.subTest(label, tool=tool):
				result = self.run_tool(tool, arguments, context)
				self.assertFalse(result["ok"])
				self.assertIn(reason, result["reason"])
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("User", NEW_USER))
		self.assertFalse(frappe.db.exists("Role Profile", OTHER_PROFILE))
		self.assertNotEqual(frappe.db.get_value("User", "Administrator", "first_name"), "Đổi")
		self.assertNotEqual(frappe.db.get_value("User", AGENT, "first_name"), "Đổi")

	def test_names_only_the_database_matches_are_refused(self):
		"""MariaDB ignores trailing spaces and accents where casefold does not: the stored name decides."""
		role_values = lambda role: self.user_values(roles=[{"role": role}])  # noqa: E731
		user_update = lambda user: {"doctype": "User", "name": user, "values": {"first_name": "Đổi"}}  # noqa: E731
		cases = (
			(
				"Role",
				"System Manager ",
				"api_create_record",
				{"doctype": "User", "values": role_values("System Manager ")},
				"vai trò không được gán",
			),
			(
				"Role",
				"Systém Manager",
				"api_create_record",
				{"doctype": "User", "values": role_values("Systém Manager")},
				"vai trò không được gán",
			),
			("User", "Administrator ", "api_update_record", user_update("Administrator "), "không được sửa"),
			("User", "Ädministrator", "api_update_record", user_update("Ädministrator"), "không được sửa"),
		)
		for doctype, name, tool, arguments, reason in cases:
			with self.subTest(doctype, name=name), patch.object(site_api, "_write") as write:
				# Precondition: the database finds the record while casefold alone would not.
				stored = frappe.db.get_value(doctype, name, "name")
				self.assertTrue(stored)
				self.assertNotEqual(stored.casefold(), name.casefold())
				result = self.run_tool(tool, arguments)
				self.assertFalse(result["ok"])
				self.assertIn(reason, result["reason"])
				write.assert_not_called()

	def test_refuses_child_table_doctype(self):
		result = self.create(
			"Has Role",
			{"parent": AGENT, "parenttype": "User", "parentfield": "roles", "role": "System Manager"},
		)
		self.assertFalse(result["ok"])
		self.assertIn("bảng con", result["reason"])

	def test_refuses_unknown_doctype(self):
		result = self.create("SITEAPI Không Có", {"title": "x"})
		self.assertFalse(result["ok"])
		self.assertIn("không tìm thấy DocType", result["reason"])

	def test_refuses_protected_users(self):
		for user in ("Administrator", "Guest", AGENT):
			result = self.update("User", user, {"first_name": "Đổi"})
			self.assertFalse(result["ok"], user)
			self.assertIn("không được sửa", result["reason"])
		self.assertNotEqual(frappe.db.get_value("User", AGENT, "first_name"), "Đổi")

	def test_refuses_secret_and_system_fields(self):
		for key in ("new_password", "api_key", "api_secret", "reset_password_key", "docstatus", "owner"):
			result = self.create("User", self.user_values(**{key: "1"}))
			self.assertFalse(result["ok"], key)
			self.assertIn(key, result["reason"])
			self.assertFalse(frappe.db.exists("User", NEW_USER), key)

	def test_refuses_field_the_doctype_does_not_have(self):
		result = self.create("Note", {"title": NOTE_TITLE, "khong_co_truong_nay": 1})
		self.assertFalse(result["ok"])
		self.assertIn("khong_co_truong_nay", result["reason"])
		self.assertFalse(frappe.db.exists("Note", {"title": NOTE_TITLE}))

	def test_account_without_permission_is_refused_and_nothing_is_written(self):
		frappe.set_user(PLAIN_AGENT)
		result = self.create("User", self.user_values(), _context(agent_user=PLAIN_AGENT))
		self.assertFalse(result["ok"])
		self.assertIn("thiếu quyền", result["reason"])
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("User", NEW_USER))

	def test_validation_error_is_reported_and_rolled_back(self):
		result = self.create("User", {"email": "không phải email", "first_name": "Sai"})
		self.assertFalse(result["ok"])
		self.assertTrue(result["reason"])
		self.assertFalse(frappe.db.exists("User", {"first_name": "Sai"}))

	def test_server_script_is_always_created_disabled(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", AGENT).add_roles("Script Manager")
		frappe.set_user(AGENT)
		result = self.create(
			"Server Script",
			{
				"name": "SITEAPI-TEST script",
				"script_type": "API",
				"api_method": "siteapi_test_method",
				"script": "frappe.response['message'] = 1",
				"disabled": 0,
			},
		)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Server Script", result["name"], "disabled"), 1)
		# The forced value shows as saved, not as the model sent it.
		self.assertEqual(result["value_before"], None)
		self.assertEqual(
			result["value_after"],
			{
				"name": "SITEAPI-TEST script",
				"script_type": "API",
				"api_method": "siteapi_test_method",
				"script": "frappe.response['message'] = 1",
				"disabled": 1,
			},
		)
		enabled = self.update("Server Script", result["name"], {"disabled": 0})
		self.assertTrue(enabled["ok"], enabled)
		self.assertEqual(frappe.db.get_value("Server Script", result["name"], "disabled"), 1)
		self.assertEqual(
			(enabled["value_before"], enabled["value_after"]), ({"disabled": 1}, {"disabled": 1})
		)

	def test_webhook_always_saved_disabled_in_normal_mode(self):
		before = frappe.db.count("Webhook")
		result = self.create(
			"Webhook",
			{
				"name": WEBHOOK_NAME,
				"webhook_doctype": "Note",
				"webhook_docevent": "after_insert",
				"request_url": "https://example.com/siteapi",
				"request_method": "POST",
				"enabled": 1,
			},
		)
		self.assertEqual(
			_without_snapshot(result),
			{
				"ok": True,
				"doctype": "Webhook",
				"name": WEBHOOK_NAME,
				"value_before": None,
				"value_after": {
					"name": WEBHOOK_NAME,
					"webhook_doctype": "Note",
					"webhook_docevent": "after_insert",
					"request_url": "https://example.com/siteapi",
					"request_method": "POST",
					"enabled": 0,
				},
			},
		)
		self.assertEqual(frappe.db.count("Webhook"), before + 1)
		self.assertEqual(frappe.db.get_value("Webhook", WEBHOOK_NAME, "enabled"), 0)
		enabled = self.update("Webhook", WEBHOOK_NAME, {"enabled": 1})
		self.assertEqual(
			_without_snapshot(enabled),
			{
				"ok": True,
				"doctype": "Webhook",
				"name": WEBHOOK_NAME,
				"value_before": {"enabled": 0},
				"value_after": {"enabled": 0},
			},
		)
		self.assertEqual(frappe.db.get_value("Webhook", WEBHOOK_NAME, "enabled"), 0)

	def test_snapshot_keys_are_the_given_values_not_the_forced_ones(self):
		values = {
			"name": WEBHOOK_NAME,
			"webhook_doctype": "Note",
			"webhook_docevent": "after_insert",
			"request_url": "https://example.com/siteapi",
			"request_method": "POST",
		}
		created = self.create("Webhook", values)
		self.assertTrue(created["ok"], created)
		self.assertEqual(frappe.db.get_value("Webhook", WEBHOOK_NAME, "enabled"), 0)
		self.assertIsNone(created["_snapshot"]["before"])
		self.assertEqual(set(created["_snapshot"]["after"]), {"name", *values})
		updated = self.update("Webhook", WEBHOOK_NAME, {"request_method": "PUT"})
		self.assertTrue(updated["ok"], updated)
		self.assertEqual(
			updated["_snapshot"],
			{
				"before": {"name": WEBHOOK_NAME, "request_method": "POST"},
				"after": {"name": WEBHOOK_NAME, "request_method": "PUT"},
			},
		)

	def test_update_snapshot_holds_the_doctype_tables_and_the_saved_values(self):
		from frappe.desk.doctype.note.note import Note

		created = self.create("Note", {"title": NOTE_TITLE, "public": 1, "seen_by": [{"user": BOSS}]})
		self.assertTrue(created["ok"], created)
		content = frappe.db.get_value("Note", created["name"], "content")

		def rewrite(note):
			note.content = "SITEAPI-TEST đã chuẩn hóa"

		with (
			patch.dict(site_api.SNAPSHOT_TABLES, {"Note": ("seen_by",)}),
			patch.object(Note, "validate", side_effect=rewrite, autospec=True, create=True),
		):
			result = self.update("Note", created["name"], {"content": "SITEAPI-TEST model gửi"})
		seen_by = [{"docstatus": 0, "user": BOSS}]
		self.assertEqual(
			result["_snapshot"],
			{
				"before": {"name": created["name"], "content": content, "seen_by": seen_by},
				"after": {
					"name": created["name"],
					"content": "SITEAPI-TEST đã chuẩn hóa",
					"seen_by": seen_by,
				},
			},
		)

	def test_rename_is_refused(self):
		created = self.create("Note", {"title": NOTE_TITLE, "public": 1})
		self.assertTrue(created["ok"], created)
		before = frappe.db.count("Note")
		content = frappe.db.get_value("Note", created["name"], "content")
		result = self.update("Note", created["name"], {"name": RENAMED_NOTE, "content": "mới"})
		self.assertEqual(
			result, {"ok": False, "reason": "không đổi tên bản ghi qua công cụ: name", "doctype": "Note"}
		)
		self.assertEqual(frappe.db.count("Note"), before)
		self.assertFalse(frappe.db.exists("Note", RENAMED_NOTE))
		self.assertEqual(frappe.db.get_value("Note", created["name"], "content"), content)

	def test_duplicate_name_rolls_back_to_savepoint(self):
		created = self.create("Tag", {"name": DUPLICATE_TAG})
		self.assertEqual(
			_without_snapshot(created),
			{
				"ok": True,
				"doctype": "Tag",
				"name": DUPLICATE_TAG,
				"value_before": None,
				"value_after": {"name": DUPLICATE_TAG},
			},
		)
		before = frappe.db.count("Tag")
		with (
			patch.object(frappe.db, "rollback", wraps=frappe.db.rollback) as rollback,
			patch.object(frappe, "log_error") as log_error,
		):
			result = self.create("Tag", {"name": DUPLICATE_TAG})
		self.assertEqual(result, {"ok": False, "reason": "đã có bản ghi cùng tên", "doctype": "Tag"})
		rollback.assert_any_call(save_point=site_api.SAVEPOINT)
		log_error.assert_called_once()
		self.assertEqual(frappe.db.count("Tag"), before)

	def test_hook_error_leaves_no_partial_write(self):
		from frappe.desk.doctype.note.note import Note

		before = frappe.db.count("Note")
		with (
			patch.object(Note, "on_update", side_effect=TypeError("hook boom"), create=True) as hook,
			patch.object(frappe, "log_error") as log_error,
		):
			result = self.create("Note", {"title": NOTE_TITLE, "public": 1})
		hook.assert_called_once()
		self.assertEqual(
			result, {"ok": False, "reason": "lỗi hệ thống khi lưu, không có gì thay đổi", "doctype": "Note"}
		)
		self.assertNotIn("hook boom", result["reason"])
		log_error.assert_called_once()
		self.assertEqual(frappe.db.count("Note"), before)
		self.assertFalse(frappe.db.exists("Note", {"title": NOTE_TITLE}))

	def test_update_changes_only_the_given_fields(self):
		created = self.create("Note", {"title": NOTE_TITLE, "public": 1, "content": "cũ"})
		self.assertTrue(created["ok"], created)
		result = self.update("Note", created["name"], {"content": "mới"})
		self.assertEqual(
			_without_snapshot(result),
			{
				"ok": True,
				"doctype": "Note",
				"name": created["name"],
				"value_before": {"content": "cũ"},
				"value_after": {"content": "mới"},
			},
		)
		note = frappe.get_doc("Note", created["name"])
		self.assertEqual((note.title, note.public, note.content), (NOTE_TITLE, 1, "mới"))

	def test_create_returns_the_saved_values_and_no_before(self):
		long_content = "n" * 300
		result = self.create("Note", {"title": NOTE_TITLE, "public": 1, "content": long_content})
		self.assertEqual(
			_without_snapshot(result),
			{
				"ok": True,
				"doctype": "Note",
				"name": result["name"],
				"value_before": None,
				"value_after": {"title": NOTE_TITLE, "public": 1, "content": "n" * 200},
			},
		)
		row = frappe.db.get_value("Note", result["name"], ["title", "public", "content"], as_dict=True)
		self.assertEqual(row, {"title": NOTE_TITLE, "public": 1, "content": long_content})

	def test_update_reads_the_saved_value_back_from_the_document(self):
		from frappe.desk.doctype.note.note import Note

		created = self.create("Note", {"title": NOTE_TITLE, "public": 1})

		def rewrite(note):
			note.title = "SITEAPI-TEST đã chuẩn hóa"

		with patch.object(Note, "validate", side_effect=rewrite, autospec=True, create=True):
			result = self.update("Note", created["name"], {"title": "SITEAPI-TEST model gửi"})
		self.assertEqual(
			(result["value_before"], result["value_after"]),
			({"title": NOTE_TITLE}, {"title": "SITEAPI-TEST đã chuẩn hóa"}),
		)
		self.assertEqual(frappe.db.get_value("Note", created["name"], "title"), "SITEAPI-TEST đã chuẩn hóa")

	def test_refused_and_failed_calls_carry_no_before_after(self):
		created = self.create("Tag", {"name": DUPLICATE_TAG})
		self.assertIn("value_after", created)
		with patch.object(frappe, "log_error"):
			failed = self.create("Tag", {"name": DUPLICATE_TAG})
		refused = self.create("User", self.user_values(roles=[{"role": "System Manager"}]))
		missing = self.update("Note", "SITEAPI-không-có", {"content": "x"})
		for result in (failed, refused, missing):
			self.assertFalse(result["ok"], result)
			self.assertNotIn("value_before", result)
			self.assertNotIn("value_after", result)

	def test_update_refuses_missing_record(self):
		result = self.update("Note", "SITEAPI-không-có", {"content": "x"})
		self.assertFalse(result["ok"])
		self.assertIn("không tìm thấy bản ghi", result["reason"])

	def test_update_refuses_submitted_document(self):
		created = self.create("Note", {"title": NOTE_TITLE, "public": 1})
		with patch.object(site_api, "_is_draft", return_value=False):
			result = self.update("Note", created["name"], {"content": "x"})
		self.assertFalse(result["ok"])
		self.assertIn("đã submit", result["reason"])

	def test_get_returns_the_record_without_secret_fields(self):
		result = self.run_tool("api_get_record", {"doctype": "User", "name": BOSS})
		self.assertTrue(result["ok"], result)
		record = result["record"]
		self.assertEqual(record["email"], BOSS)
		self.assertIn(ROLE_INSTRUCTOR, [row["role"] for row in record["roles"]])
		for key in ("new_password", "api_key", "api_secret", "reset_password_key"):
			self.assertNotIn(key, record)

	def test_get_refuses_missing_record(self):
		result = self.run_tool("api_get_record", {"doctype": "User", "name": "siteapi.none@example.com"})
		self.assertFalse(result["ok"])

	def test_list_returns_requested_fields_with_filters_and_limit(self):
		result = self.run_tool(
			"api_list_records",
			{
				"doctype": "User",
				"filters": [["email", "like", "siteapi.%"]],
				"fields": ["name", "enabled"],
				"limit": 2,
			},
		)
		self.assertTrue(result["ok"], result)
		self.assertEqual(len(result["records"]), 2)
		for row in result["records"]:
			self.assertEqual(set(row), {"name", "enabled"})
			self.assertTrue(row["name"].startswith("siteapi."))

	def test_list_refuses_bad_fields_filters_and_secrets(self):
		for arguments in (
			{"doctype": "User", "fields": ["api_secret"]},
			{"doctype": "User", "fields": ["count(*)"]},
			{"doctype": "User", "filters": [["api_key", "like", "a%"]]},
			{"doctype": "User", "filters": [["email", "regexp", ".*"]]},
			{"doctype": "User", "filters": [["email", "="]]},
			{"doctype": "User", "filters": ["email"]},
		):
			result = self.run_tool("api_list_records", arguments)
			self.assertFalse(result["ok"], arguments)

	def test_list_respects_frappe_permissions(self):
		frappe.set_user(PLAIN_AGENT)
		# Server Script is readable by Script Manager only; User would still list the caller's own row.
		result = self.run_tool(
			"api_list_records", {"doctype": "Server Script"}, _context(agent_user=PLAIN_AGENT)
		)
		self.assertFalse(result["ok"])
		self.assertIn("thiếu quyền", result["reason"])


class TestForbiddenRoleSpelling(FrappeTestCase):
	"""A forbidden role (or a Role Profile holding one) written as a variant spelling is refused by the tool's own
	check with the stored name, not left to Frappe's link check (STD-SEC-4)."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		_make_user(AGENT, ROLE_AGENT, "System Manager")
		_make_user(BOSS, ROLE_INSTRUCTOR)
		_make_user(SPELLING_USER)
		frappe.get_doc(
			{"doctype": "Role Profile", "role_profile": BANNED_PROFILE, "roles": [{"role": "System Manager"}]}
		).insert()
		frappe.set_user(AGENT)

	def stored(self, user):
		frappe.set_user("Administrator")
		doc = frappe.get_doc("User", user) if frappe.db.exists("User", user) else None
		frappe.set_user(AGENT)
		if not doc:
			return None
		return {"roles": {row.role for row in doc.roles}, "role_profile_name": doc.role_profile_name}

	def assert_refused_on_both_tools(self, values, reason, **labels):
		with self.subTest(tool="create_record", **labels):
			new_values = {"email": NEW_USER, "first_name": "Người mới", "send_welcome_email": 0, **values}
			result = execute_tool("api_create_record", {"doctype": "User", "values": new_values}, _context())
			self.assertEqual(result, {"ok": False, "reason": reason, "doctype": "User"})
			self.assertIsNone(self.stored(NEW_USER))
		with self.subTest(tool="update_record", **labels):
			before = self.stored(SPELLING_USER)
			arguments = {"doctype": "User", "name": SPELLING_USER, "values": values}
			result = execute_tool("api_update_record", arguments, _context())
			self.assertEqual(result, {"ok": False, "reason": reason, "doctype": "User"})
			self.assertEqual(self.stored(SPELLING_USER), before)

	def test_variant_spellings_refused(self):
		spellings = (
			("accented", "Sýstem Manager", "SITEAPI Hó sơ cám"),
			("case", "SYSTEM MANAGER", BANNED_PROFILE.upper()),
			("leading whitespace", "  System Manager", f"  {BANNED_PROFILE}"),
			("trailing whitespace", "System Manager  ", f"{BANNED_PROFILE}  "),
		)
		for spelling, role, profile in spellings:
			self.assert_refused_on_both_tools(
				{"roles": [{"role": role}]}, FORBIDDEN_REFUSAL, spelling=spelling, path="roles"
			)
			self.assert_refused_on_both_tools(
				{"role_profile_name": profile}, FORBIDDEN_REFUSAL, spelling=spelling, path="role_profile_name"
			)
		# This Frappe version has no `role_profiles` on User: the unknown-field check refuses it first.
		self.assert_refused_on_both_tools(
			{"role_profiles": [{"role_profile": BANNED_PROFILE}]},
			"DocType không có trường: role_profiles",
			path="role_profiles",
		)

	def test_whitespace_around_an_allowed_role_still_rejected_by_frappe(self):
		# The tool's check strips names only to look them up; the values written keep the spaces, as before.
		before = self.stored(SPELLING_USER)
		arguments = {
			"doctype": "User",
			"name": SPELLING_USER,
			"values": {"roles": [{"role": f"  {ALLOWED_ROLE}  "}]},
		}
		result = execute_tool("api_update_record", arguments, _context())
		self.assertFalse(result["ok"])
		self.assertTrue(result["reason"].startswith("hệ thống từ chối: Could not find Row #1: Role:"), result)
		self.assertNotIn("vai trò không được gán", result["reason"])
		self.assertEqual(self.stored(SPELLING_USER), before)

	def test_unrestricted_still_assigns_a_variant_spelling(self):
		arguments = {
			"doctype": "User",
			"name": SPELLING_USER,
			"values": {"roles": [{"role": "Sýstem Manager"}]},
		}
		unrestricted = _context(level="L1", change_enabled=False, unrestricted=True)
		result = execute_tool("api_update_record", arguments, unrestricted)
		self.assertTrue(result["ok"], result)
		self.assertEqual(self.stored(SPELLING_USER)["roles"], {"System Manager"})


class TestUnrestrictedGrant(FrappeTestCase):
	def names(self, level, has_instructor, unrestricted):
		# Only the site_admin + site_unrestricted tools (site_api.TOOLS), change switch off.
		record_tools = {spec.name for spec in site_api.TOOLS}
		inputs = registry.GrantInputs(
			level, level, has_instructor, PermissionSwitches(unrestricted=unrestricted)
		)
		return [spec["name"] for spec in get_tool_schemas(inputs) if spec["name"] in record_tools]

	def test_switch_grants_every_record_tool_at_any_level_above_l0_with_instructor(self):
		for level in ("L1", "L2", "L3"):
			self.assertEqual(self.names(level, True, True), TOOL_NAMES + UNRESTRICTED_TOOL_NAMES, level)
		for level, has_instructor, unrestricted in (
			("L3", True, False),
			("L3", False, True),
			("L0", True, True),
			("LX", True, True),
		):
			self.assertEqual(self.names(level, has_instructor, unrestricted), [], (level, has_instructor))

	def test_normal_grant_never_holds_the_unrestricted_tools(self):
		for level in ("L1", "L2", "L3"):
			inputs = registry.GrantInputs(
				level, level, True, PermissionSwitches(record_tools=True, code_change=True)
			)
			names = [spec["name"] for spec in get_tool_schemas(inputs)]
			for name in UNRESTRICTED_TOOL_NAMES:
				self.assertNotIn(name, names)

	def test_execute_refuses_unrestricted_tools_without_the_switch_or_instructor(self):
		arguments = {"doctype": "Note", "name": "x"}
		self.assertEqual(execute_tool("api_delete_record", arguments, _context()), NOT_GRANTED)
		self.assertEqual(
			execute_tool("api_delete_record", arguments, _context(instructor=None, unrestricted=True)),
			NOT_GRANTED,
		)
		self.assertEqual(
			execute_tool("api_delete_record", arguments, _context(level="L0", unrestricted=True)), NOT_GRANTED
		)


class TestSiteApiUnrestricted(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		_make_user(AGENT, ROLE_AGENT, "System Manager")
		_make_user(PLAIN_AGENT, ROLE_AGENT)
		_make_user(BOSS, ROLE_INSTRUCTOR)
		frappe.set_user(AGENT)
		# Level L1 on purpose: the switch does not depend on L3 or on the code-change switch.
		self.context = _context(level="L1", change_enabled=False, unrestricted=True)

	def run_tool(self, name, arguments, context=None):
		return execute_tool(name, arguments, context or self.context)

	def roles_of(self, user):
		frappe.set_user("Administrator")
		roles = {row.role for row in frappe.get_doc("User", user).roles}
		frappe.set_user(AGENT)
		return roles

	def test_assigns_any_role_and_edits_protected_accounts(self):
		created = self.run_tool(
			"api_create_record",
			{
				"doctype": "User",
				"values": {
					"email": NEW_USER,
					"first_name": "Quản trị",
					"send_welcome_email": 0,
					"roles": [{"role": "System Manager"}, {"role": ROLE_INSTRUCTOR}],
				},
			},
		)
		self.assertEqual(
			{key: created[key] for key in ("ok", "doctype", "name", "value_before")},
			{"ok": True, "doctype": "User", "name": NEW_USER, "value_before": None},
		)
		self.assertEqual(self.roles_of(NEW_USER), {"System Manager", ROLE_INSTRUCTOR})
		own = self.run_tool(
			"api_update_record", {"doctype": "User", "name": AGENT, "values": {"first_name": "Đổi"}}
		)
		self.assertTrue(own["ok"], own)
		self.assertEqual(frappe.db.get_value("User", AGENT, "first_name"), "Đổi")
		self.assertEqual(
			(own["value_before"], own["value_after"]), ({"first_name": "SITEAPI"}, {"first_name": "Đổi"})
		)

	def test_permission_doctypes_are_open(self):
		for doctype in ("Custom DocPerm", "Custom Role"):
			result = self.run_tool("api_list_records", {"doctype": doctype})
			self.assertTrue(result["ok"], (doctype, result))

	def test_own_configuration_log_and_secrets_stay_closed(self):
		for doctype in ("ERP AI Setting", "ERP AI Credential", "ERP AI Log", "ERP AI Change Proposal"):
			for name, arguments in (
				("api_list_records", {"doctype": doctype}),
				("api_get_record", {"doctype": doctype, "name": doctype}),
				("api_create_record", {"doctype": doctype, "values": {"enabled": 0}}),
				("api_update_record", {"doctype": doctype, "name": doctype, "values": {"enabled": 0}}),
				("api_delete_record", {"doctype": doctype, "name": doctype}),
				("api_submit_record", {"doctype": doctype, "name": doctype, "action": "submit"}),
			):
				result = self.run_tool(name, arguments)
				self.assertFalse(result["ok"], (name, doctype))
				self.assertIn("không được phép", result["reason"])
		result = self.run_tool(
			"api_update_record", {"doctype": "User", "name": BOSS, "values": {"new_password": "x"}}
		)
		self.assertFalse(result["ok"])
		self.assertIn("new_password", result["reason"])

	def test_server_script_keeps_the_requested_state(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", AGENT).add_roles("Script Manager")
		frappe.set_user(AGENT)
		result = self.run_tool(
			"api_create_record",
			{
				"doctype": "Server Script",
				"values": {
					"name": "SITEAPI-TEST script bật",
					"script_type": "API",
					"api_method": "siteapi_test_method_on",
					"script": "frappe.response['message'] = 1",
					"disabled": 0,
				},
			},
		)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Server Script", result["name"], "disabled"), 0)

	def test_delete_removes_the_record_through_permissions(self):
		created = self.run_tool(
			"api_create_record",
			{"doctype": "Note", "values": {"title": NOTE_TITLE, "public": 1, "content": "nội dung"}},
		)
		row = frappe.db.get_value(
			"Note", created["name"], ["name", "title", "public", "notify_on_login", "content"], as_dict=True
		)
		result = self.run_tool("api_delete_record", {"doctype": "Note", "name": created["name"]})
		self.assertEqual(
			_without_snapshot(result),
			{
				"ok": True,
				"doctype": "Note",
				"name": created["name"],
				"value_before": {
					"name": created["name"],
					"title": NOTE_TITLE,
					"public": 1,
					"notify_on_login": 0,
					"notify_on_every_login": 0,
					"content": "nội dung",
				},
				"value_after": None,
			},
		)
		self.assertLessEqual(row.items(), result["value_before"].items())
		self.assertFalse(frappe.db.exists("Note", created["name"]))
		missing = self.run_tool("api_delete_record", {"doctype": "Note", "name": created["name"]})
		self.assertFalse(missing["ok"])
		self.assertIn("không tìm thấy bản ghi", missing["reason"])

	def create_new_user(self):
		created = self.run_tool(
			"api_create_record",
			{
				"doctype": "User",
				"values": {"email": NEW_USER, "first_name": "Bí mật", "send_welcome_email": 0},
			},
		)
		self.assertTrue(created["ok"], created)

	def test_delete_before_holds_at_most_twenty_fields(self):
		self.create_new_user()
		result = self.run_tool("api_delete_record", {"doctype": "User", "name": NEW_USER})
		self.assertTrue(result["ok"], result)
		self.assertEqual(len(result["value_before"]), 20)
		self.assertEqual(
			{key: result["value_before"][key] for key in ("name", "email", "first_name")},
			{"name": NEW_USER, "email": NEW_USER, "first_name": "Bí mật"},
		)
		self.assertIsNone(result["value_after"])
		self.assertFalse(frappe.db.exists("User", NEW_USER))

	def test_before_after_never_carry_secret_fields(self):
		self.create_new_user()
		real_get_doc = frappe.get_doc
		planted = []

		def get_doc_with_planted_secrets(*args, **kwargs):
			doc = real_get_doc(*args, **kwargs)
			if getattr(doc, "doctype", None) == "User" and doc.name == NEW_USER:
				doc.new_password, doc.api_secret = FAKE_PASSWORD, FAKE_API_SECRET
				planted.append(doc)
			return doc

		# The cap is lifted so only the secret filter, not the 20-field limit, keeps the planted values out.
		with (
			patch.object(frappe, "get_doc", side_effect=get_doc_with_planted_secrets),
			patch.object(site_api, "DELETED_FIELDS_MAX", 1000),
		):
			result = self.run_tool("api_delete_record", {"doctype": "User", "name": NEW_USER})
		self.assertTrue(planted)
		self.assertEqual(
			(planted[0].as_dict()["new_password"], planted[0].as_dict()["api_secret"]),
			(FAKE_PASSWORD, FAKE_API_SECRET),
		)
		self.assertTrue(result["ok"], result)
		self.assertIn("value_before", result)
		self.assertIn("value_after", result)
		self.assertGreater(len(result["value_before"]), 20)
		self.assertEqual(result["value_before"]["first_name"], "Bí mật")
		text = json.dumps(result, ensure_ascii=False, default=str)
		self.assertEqual((text.count(FAKE_PASSWORD), text.count(FAKE_API_SECRET)), (0, 0))
		for key in ("new_password", "api_secret", "api_key", "reset_password_key"):
			self.assertNotIn(key, result["value_before"])

	def test_delete_without_permission_is_refused(self):
		frappe.set_user(PLAIN_AGENT)
		context = _context(level="L1", agent_user=PLAIN_AGENT, unrestricted=True)
		result = self.run_tool("api_delete_record", {"doctype": "User", "name": BOSS}, context)
		self.assertFalse(result["ok"])
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("User", BOSS))

	def test_submit_and_cancel_call_the_document(self):
		created = self.run_tool(
			"api_create_record", {"doctype": "Note", "values": {"title": NOTE_TITLE, "public": 1}}
		)
		refused = self.run_tool(
			"api_submit_record", {"doctype": "Note", "name": created["name"], "action": "submit"}
		)
		self.assertFalse(refused["ok"])
		self.assertIn("không submit được", refused["reason"])
		for action, before, after in (("submit", 0, 1), ("cancel", 1, 2)):
			# The stub moves docstatus in the database the way the real action would.
			with (
				patch.object(site_api, "_is_submittable", return_value=True),
				patch.object(
					frappe.model.document.Document,
					action,
					autospec=True,
					side_effect=lambda doc, status=after: doc.db_set("docstatus", status),
				) as called,
			):
				result = self.run_tool(
					"api_submit_record", {"doctype": "Note", "name": created["name"], "action": action}
				)
			self.assertEqual(
				_without_snapshot(result),
				{
					"ok": True,
					"doctype": "Note",
					"name": created["name"],
					"value_before": {"docstatus": before},
					"value_after": {"docstatus": after},
				},
				action,
			)
			self.assertEqual(frappe.db.get_value("Note", created["name"], "docstatus"), after, action)
			called.assert_called_once()

	def test_delete_and_submit_snapshot_shapes(self):
		long_content = "c" * 300
		created = self.run_tool(
			"api_create_record",
			{"doctype": "Note", "values": {"title": NOTE_TITLE, "public": 1, "content": long_content}},
		)
		name = created["name"]
		self.assertEqual(
			created["_snapshot"],
			{
				"before": None,
				"after": {"name": name, "title": NOTE_TITLE, "public": 1, "content": long_content},
			},
		)

		updated = self.run_tool(
			"api_update_record",
			{
				"doctype": "Note",
				"name": name,
				"values": {"expire_notification_on": "2026-12-01", "seen_by": [{"user": BOSS}]},
			},
		)
		self.assertEqual(
			updated["_snapshot"],
			{
				"before": {"name": name, "expire_notification_on": None, "seen_by": []},
				"after": {
					"name": name,
					"expire_notification_on": "2026-12-01",
					"seen_by": [{"docstatus": 0, "user": BOSS}],
				},
			},
		)

		for action, before, after in (("submit", 0, 1), ("cancel", 1, 2)):
			with (
				patch.object(site_api, "_is_submittable", return_value=True),
				patch.object(
					frappe.model.document.Document,
					action,
					autospec=True,
					side_effect=lambda doc, status=after: doc.db_set("docstatus", status),
				),
			):
				result = self.run_tool(
					"api_submit_record", {"doctype": "Note", "name": name, "action": action}
				)
			self.assertEqual(
				result["_snapshot"],
				{"before": {"name": name, "docstatus": before}, "after": {"name": name, "docstatus": after}},
				action,
			)
		frappe.db.set_value("Note", name, "docstatus", 0, update_modified=False)

		creation = frappe.db.get_value("Note", name, "creation")
		self.assertIsInstance(creation, datetime.datetime)
		deleted = self.run_tool("api_delete_record", {"doctype": "Note", "name": name})
		self.assertTrue(deleted["ok"], deleted)
		before = deleted["_snapshot"]["before"]
		self.assertIsNone(deleted["_snapshot"]["after"])
		self.assertEqual(set(deleted["_snapshot"]), {"before", "after"})
		self.assertEqual(
			{
				key: before[key]
				for key in ("name", "title", "public", "content", "expire_notification_on", "seen_by")
			},
			{
				"name": name,
				"title": NOTE_TITLE,
				"public": 1,
				"content": long_content,
				"expire_notification_on": "2026-12-01",
				"seen_by": [{"docstatus": 0, "user": BOSS}],
			},
		)
		self.assertEqual(before["creation"], str(creation))
		self.assertEqual([key for key, value in before.items() if value in (None, "", [])], [])
		self.assertEqual(deleted["value_before"]["content"], "c" * 200)
		json.dumps(deleted["_snapshot"])

	def test_refused_or_failed_write_has_no_snapshot(self):
		from frappe.desk.doctype.note.note import Note

		control = self.run_tool("api_create_record", {"doctype": "Note", "values": {"title": NOTE_TITLE}})
		self.assertTrue(control["ok"], control)
		self.assertIn("_snapshot", control)
		name = control["name"]

		def refuse(note):
			frappe.throw("SITEAPI từ chối")

		with patch.object(Note, "validate", side_effect=refuse, autospec=True, create=True):
			failed_update = self.run_tool(
				"api_update_record", {"doctype": "Note", "name": name, "values": {"content": "x"}}
			)
		with (
			patch.object(frappe, "log_error"),
			patch.object(frappe, "delete_doc", side_effect=TypeError("boom")),
		):
			crashed_delete = self.run_tool("api_delete_record", {"doctype": "Note", "name": name})
		results = {
			"create": self.run_tool("api_create_record", {"doctype": "ERP AI Log", "values": {"enabled": 0}}),
			"update": self.run_tool(
				"api_update_record",
				{"doctype": "Note", "name": "SITEAPI-không-có", "values": {"content": "x"}},
			),
			"delete": self.run_tool("api_delete_record", {"doctype": "Note", "name": "SITEAPI-không-có"}),
			"submit": self.run_tool(
				"api_submit_record", {"doctype": "Note", "name": name, "action": "submit"}
			),
			"failed update": failed_update,
			"crashed delete": crashed_delete,
		}
		for case, result in results.items():
			self.assertFalse(result["ok"], (case, result))
			self.assertNotIn("_snapshot", result, case)

		method = self.run_tool(
			"api_call_method",
			{
				"method": "frappe.client.get_value",
				"arguments": {"doctype": "User", "filters": BOSS, "fieldname": "email"},
			},
		)
		self.assertTrue(method["ok"], method)
		self.assertNotIn("_snapshot", method)

	def test_call_method_runs_whitelisted_methods_only(self):
		result = self.run_tool(
			"api_call_method",
			{
				"method": "frappe.client.get_value",
				"arguments": {"doctype": "User", "filters": BOSS, "fieldname": "email"},
			},
		)
		self.assertEqual(
			result,
			{
				"ok": True,
				"method": "frappe.client.get_value",
				"result": {"email": BOSS},
				"value_before": None,
				"value_after": {
					"method": "frappe.client.get_value",
					"argument_keys": ["doctype", "fieldname", "filters"],
				},
			},
		)
		for method in ("frappe.get_doc", "frappe.db.sql", "os.system", "frappe.khong.co", "khongco"):
			refused = self.run_tool("api_call_method", {"method": method, "arguments": {}})
			self.assertFalse(refused["ok"], method)

	def test_call_method_refuses_own_app_and_own_doctypes(self):
		own = self.run_tool(
			"api_call_method", {"method": "erp_ai.ticket_panel.get_panel_data", "arguments": {"ticket": "1"}}
		)
		self.assertFalse(own["ok"])
		self.assertIn("erp_ai", own["reason"])
		for arguments in (
			{"doctype": "ERP AI Setting", "fieldname": "enabled"},
			{"doc": '{"doctype": "ERP AI Credential", "label": "x"}'},
			{"doctype": "User", "filters": {"name": ["in", ["ERP AI Log"]]}},
		):
			refused = self.run_tool(
				"api_call_method", {"method": "frappe.client.get_value", "arguments": arguments}
			)
			self.assertFalse(refused["ok"], arguments)
			self.assertIn("không được phép", refused["reason"])

	def test_call_method_reports_validation_and_permission_errors(self):
		frappe.set_user(PLAIN_AGENT)
		context = _context(level="L1", agent_user=PLAIN_AGENT, unrestricted=True)
		result = self.run_tool(
			"api_call_method",
			{"method": "frappe.client.delete", "arguments": {"doctype": "User", "name": BOSS}},
			context,
		)
		self.assertFalse(result["ok"])
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("User", BOSS))

	def test_secret_returning_methods_are_refused_before_call(self):
		for method in (
			"frappe.core.doctype.user.user.generate_keys",
			"frappe.client.get_password",
			"frappe.utils.password.get_decrypted_password",
			"frappe.utils.backups.get_backup_encryption_key",
			"frappe.integrations.oauth2.get_token",
			"frappe.core.doctype.user.user.update_password",
			"frappe.twofactor.reset_otp_secret",
			"other_app.api.Generate_Keys_For",
		):
			with patch.object(frappe, "call") as called:
				result = self.run_tool("api_call_method", {"method": method, "arguments": {"user": BOSS}})
			self.assertEqual(result, {"ok": False, "reason": SECRET_METHOD_REFUSED}, method)
			self.assertEqual(called.call_count, 0, method)

	def test_result_secrets_are_scrubbed(self):
		returned = {
			"api_secret": FAKE_SECRET,
			"API_KEY": FAKE_SECRET,
			"title": "giữ nguyên",
			"rows": [{"name": "r1", "password": FAKE_SECRET}, ("t1", {"Access_Token": FAKE_SECRET})],
		}
		with patch.object(frappe, "call", return_value=returned) as called:
			result = self.run_tool(
				"api_call_method", {"method": "frappe.client.get_value", "arguments": {"doctype": "Note"}}
			)
		called.assert_called_once()
		self.assertTrue(result["ok"], result)
		scrubbed = result["result"]
		self.assertEqual(scrubbed["title"], "giữ nguyên")
		self.assertEqual(scrubbed["rows"][0], {"name": "r1", "password": HIDDEN})
		self.assertEqual(scrubbed["rows"][1], ["t1", {"Access_Token": HIDDEN}])
		self.assertEqual((scrubbed["api_secret"], scrubbed["API_KEY"]), (HIDDEN, HIDDEN))
		self.assertEqual(json.dumps(result, ensure_ascii=False).count(FAKE_SECRET), 0)

	def test_arguments_naming_a_secret_field_are_refused_before_call(self):
		for method, arguments in (
			(
				"frappe.client.get_value",
				{"doctype": "User", "filters": BOSS, "fieldname": "api_key", "as_dict": 0},
			),
			(
				"frappe.client.get_value",
				{"doctype": "OAuth Bearer Token", "filters": {}, "fieldname": ["Access_Token"], "as_dict": 0},
			),
			("frappe.client.get_list", {"doctype": "User", "fields": ["name", "api_key as k"], "as_dict": 0}),
			("frappe.client.get_list", {"doctype": "User", "fields": '["`tabUser`.`API_KEY`"]'}),
			("frappe.client.get_list", {"doctype": "User", "fields": ["tabUser.reset_password_key"]}),
			(
				"frappe.client.get_value",
				{"doctype": "User", "filters": {"name": BOSS}, "fieldname": "password"},
			),
		):
			with self.subTest(arguments=arguments), patch.object(frappe, "call") as called:
				result = self.run_tool("api_call_method", {"method": method, "arguments": arguments})
				self.assertEqual(result, {"ok": False, "reason": SECRET_ARGUMENT_REFUSED})
				self.assertEqual(called.call_count, 0)

	def test_get_value_on_an_ordinary_field_still_goes_through(self):
		arguments = {"doctype": "User", "filters": BOSS, "fieldname": "full_name", "as_dict": 0}
		with patch.object(frappe, "call", return_value="Sếp") as called:
			result = self.run_tool(
				"api_call_method", {"method": "frappe.client.get_value", "arguments": arguments}
			)
		called.assert_called_once()
		# T62 contract: every ok api_call_method result also carries value_before/value_after.
		self.assertEqual(
			result,
			{
				"ok": True,
				"method": "frappe.client.get_value",
				"result": "Sếp",
				"value_before": None,
				"value_after": {
					"method": "frappe.client.get_value",
					"argument_keys": ["as_dict", "doctype", "fieldname", "filters"],
				},
			},
		)

	def test_column_selector_star_is_refused_before_call(self):
		for method, arguments in (
			("frappe.client.get_list", {"doctype": "User", "fields": ["*"], "as_dict": 0}),
			("frappe.desk.reportview.get", {"doctype": "User", "fields": ["*"]}),
			("frappe.client.get_list", {"doctype": "User", "fields": ["name", "tabUser.*"]}),
			("frappe.client.get_list", {"doctype": "User", "fields": ["`tabUser` . *"]}),
			("frappe.client.get_list", {"doctype": "User", "fields": '["name", "*"]'}),
			("frappe.client.get_list", {"doctype": "User", "fields": "name, *"}),
			("frappe.client.get_value", {"doctype": "User", "filters": BOSS, "fieldname": "*", "as_dict": 0}),
			("frappe.client.get_list", {"doctype": "User", "fields": '"*"', "as_dict": 0}),
			(
				"frappe.client.get_value",
				{"doctype": "User", "filters": BOSS, "fieldname": '"*"', "as_dict": 0},
			),
			("frappe.client.get_list", {"doctype": "User", "args": [{"fields": ["*"]}]}),
		):
			with self.subTest(method=method, arguments=arguments), patch.object(frappe, "call") as called:
				result = self.run_tool("api_call_method", {"method": method, "arguments": arguments})
				self.assertEqual(result, {"ok": False, "reason": COLUMN_SELECTOR_REFUSED})
				self.assertEqual(called.call_count, 0)

	def test_star_outside_a_column_selector_still_goes_through(self):
		for arguments, argument_keys in (
			({"doctype": "User", "fields": ["name"], "as_dict": 0}, ["as_dict", "doctype", "fields"]),
			({"doctype": "User", "fields": ["count(*) as total"]}, ["doctype", "fields"]),
			(
				{"doctype": "User", "fields": ["name"], "filters": {"full_name": "*"}},
				["doctype", "fields", "filters"],
			),
		):
			with (
				self.subTest(arguments=arguments),
				patch.object(frappe, "call", return_value=[["r1"]]) as called,
			):
				result = self.run_tool(
					"api_call_method", {"method": "frappe.client.get_list", "arguments": arguments}
				)
				called.assert_called_once()
				# T62 contract: every ok api_call_method result also carries value_before/value_after.
				self.assertEqual(
					result,
					{
						"ok": True,
						"method": "frappe.client.get_list",
						"result": [["r1"]],
						"value_before": None,
						"value_after": {"method": "frappe.client.get_list", "argument_keys": argument_keys},
					},
				)

	def test_nested_json_doc_naming_app_doctype_is_refused(self):
		for method, arguments in (
			# `S` is "S": the name only appears once the `doc` string is parsed as JSON.
			("frappe.client.insert", {"doc": '{"doctype": "erp ai \\u0053etting", "enabled": 1}'}),
			("frappe.client.save", {"doc": json.dumps({"doc": '{"doctype": "erp ai credential"}'})}),
			("frappe.client.get_list", {"doctype": "erp ai log"}),
		):
			with patch.object(frappe, "call") as called:
				result = self.run_tool("api_call_method", {"method": method, "arguments": arguments})
			self.assertFalse(result["ok"], arguments)
			self.assertIn("không được phép", result["reason"], arguments)
			self.assertEqual(called.call_count, 0, arguments)

	def test_decision_method_refused_even_with_valid_signed_link(self):
		name, action = "AICHG-00001", change_link.ACTION_APPROVE
		signature = change_link.decision_path(name, action).rsplit(change_link.SIGNATURE_MARK, 1)[1]
		self.assertTrue(change_link.signature_ok(name, action, signature))
		arguments = {"name": name, "action": action, "_signature": signature}
		with patch.object(frappe, "call") as called:
			result = self.run_tool(
				"api_call_method", {"method": change_link.DECIDE_METHOD, "arguments": arguments}
			)
		self.assertFalse(result["ok"])
		self.assertIn("erp_ai", result["reason"])
		self.assertEqual(called.call_count, 0)


class TestSnapshot(FrappeTestCase):
	"""`site_api._snapshot` on records held in memory: nothing is saved."""

	def test_snapshot_drops_secret_and_system_fields(self):
		long_note = "x" * 30000
		setting = frappe.get_doc(
			{
				"doctype": "ERP AI Setting",
				"name": "ERP AI Setting",
				"monthly_budget_usd": Decimal("12.50"),
				"credentials": [
					{"label": "SITEAPI thứ hai", "api_key": FAKE_SECRET, "idx": 2, "note": long_note},
					{
						"label": "SITEAPI thứ nhất",
						"api_key": FAKE_SECRET,
						"idx": 1,
						"paused_until": datetime.datetime(2026, 11, 14, 8, 30),
					},
				],
			}
		)
		# A private property is never part of the snapshot.
		setattr(setting.credentials[0], "__unsaved", 1)
		snapshot = site_api._snapshot(setting, ("name", "credentials", "monthly_budget_usd"))
		self.assertEqual(set(snapshot), {"name", "credentials", "monthly_budget_usd"})
		self.assertEqual(snapshot["name"], "ERP AI Setting")
		self.assertEqual(snapshot["monthly_budget_usd"], 12.5)
		rows = snapshot["credentials"]
		self.assertEqual([row["label"] for row in rows], ["SITEAPI thứ nhất", "SITEAPI thứ hai"])
		dropped = {
			"name",
			"idx",
			"parent",
			"parentfield",
			"parenttype",
			"owner",
			"creation",
			"modified",
			"modified_by",
			"doctype",
		}
		for row in rows:
			self.assertEqual(set(row) & (dropped | {"api_key"}), set(), row)
			self.assertEqual([key for key in row if key.startswith("_")], [], row)
		self.assertEqual(rows[1]["note"], long_note)
		self.assertEqual(rows[0]["paused_until"], "2026-11-14 08:30:00")
		json.dumps(snapshot)

		account = frappe.get_doc(
			{
				"doctype": "Email Account",
				"name": "SITEAPI hộp thư",
				"email_id": BOSS,
				"password": FAKE_PASSWORD,
			}
		)
		snapshot = site_api._snapshot(account, ("email_id", "password", "docstatus"))
		self.assertEqual(snapshot, {"name": "SITEAPI hộp thư", "email_id": BOSS, "docstatus": 0})

		text = json.dumps([site_api._snapshot(setting, ("credentials",)), snapshot], ensure_ascii=False)
		self.assertEqual(text.count(FAKE_SECRET), 0)
		self.assertEqual(text.count(FAKE_PASSWORD), 0)

	def test_user_snapshot_only_name_and_roles(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"name": NEW_USER,
				"email": NEW_USER,
				"first_name": "Người mới",
				"api_key": FAKE_SECRET,
				"new_password": FAKE_PASSWORD,
				"roles": [{"role": "Accounts User", "idx": 2}, {"role": ALLOWED_ROLE, "idx": 1}],
			}
		)
		self.assertEqual(site_api.SNAPSHOT_TABLES, {"User": ("roles",)})
		for fields in ((), ("first_name", "email", "api_key", "new_password"), ("roles",)):
			snapshot = site_api._snapshot(user, fields)
			self.assertEqual(set(snapshot), {"name", "roles"}, fields)
			self.assertEqual(snapshot["name"], NEW_USER)
			self.assertEqual([row["role"] for row in snapshot["roles"]], [ALLOWED_ROLE, "Accounts User"])
			self.assertNotIn(FAKE_SECRET, json.dumps(snapshot))
			self.assertNotIn(FAKE_PASSWORD, json.dumps(snapshot))


# F-2: planted fake values in child rows; none may reach `value_before`/`value_after`.
FAKE_CHILD_KEY = "SITEAPI-FAKEKEY123"
FAKE_CHILD_SECRET = "SITEAPI-FAKESECRET456"
FAKE_CHILD_PIN = "SITEAPI-FAKEPIN789"
FAKE_DEEP_KEY = "SITEAPI-FAKEDEEP000"
FAKE_JSON_TOKEN = "SITEAPI-FAKETOKEN321"
FAKE_CREDENTIAL_KEY = "SITEAPI-FAKECREDKEY654"
CHILD_FAKES = (FAKE_CHILD_KEY, FAKE_CHILD_SECRET, FAKE_CHILD_PIN, FAKE_DEEP_KEY, FAKE_JSON_TOKEN)
CHILD_SHOWN = "SITEAPI nhãn dòng con"
DEEP_SHOWN = "SITEAPI ghi chú sâu"
STUB_CHILD = "SITEAPI Stub Child"
# `pin_code` is not secret-named: only the child meta's Password type hides it.
STUB_CHILD_META = frappe._dict(
	fields=[
		frappe._dict(fieldname="pin_code", fieldtype="Password"),
		frappe._dict(fieldname="label", fieldtype="Data"),
	]
)


class _StubMeta:
	"""A parent meta whose `rows` field is a table of STUB_CHILD."""

	def get_field(self, fieldname):
		return frappe._dict(fieldtype="Table", options=STUB_CHILD) if fieldname == "rows" else None


class _StubDoc:
	def __init__(self, record, meta=None):
		self.record, self.meta = record, meta or _StubMeta()

	def as_dict(self):
		return self.record


def _child_rows():
	return [
		{
			"name": "r1",
			"api_key": FAKE_CHILD_KEY,
			"api_secret": FAKE_CHILD_SECRET,
			"pin_code": FAKE_CHILD_PIN,
			"label": CHILD_SHOWN,
			"inner": [{"api_key": FAKE_DEEP_KEY, "note": DEEP_SHOWN}],
		},
		# a row that arrives as JSON text, compared after decoding the way Frappe decodes it
		json.dumps({"token": FAKE_JSON_TOKEN, "label": CHILD_SHOWN}),
	]


def _stub_child_meta(test):
	"""Make `frappe.get_meta` return STUB_CHILD_META for STUB_CHILD for the duration of `test`."""
	real_get_meta = frappe.get_meta

	def get_meta(doctype, *args, **kwargs):
		return STUB_CHILD_META if doctype == STUB_CHILD else real_get_meta(doctype, *args, **kwargs)

	patcher = patch.object(frappe, "get_meta", get_meta)
	patcher.start()
	test.addCleanup(patcher.stop)


class TestSiteApiChildSecrets(FrappeTestCase):
	"""F-2: secret-named keys and child Password fields are scrubbed in child rows at every depth."""

	def setUp(self):
		_stub_child_meta(self)
		# The cut is lifted so only the secret filter, not the 200-character cut, keeps the fake values out.
		patcher = patch.object(site_api, "VALUE_MAX", 10000)
		patcher.start()
		self.addCleanup(patcher.stop)

	def assert_scrubbed(self, values, fakes=CHILD_FAKES, shown=(CHILD_SHOWN, DEEP_SHOWN)):
		text = json.dumps(values, ensure_ascii=False, default=str)
		self.assertEqual([text.count(fake) for fake in fakes], [0] * len(fakes), text)
		for value in shown:
			self.assertGreaterEqual(text.count(value), 1, text)

	def test_deleted_values_scrub_child_rows(self):
		doc = _StubDoc({"name": "p1", "title": "tiêu đề", "rows": _child_rows()})
		values = site_api._deleted_values(doc)
		self.assertEqual(values["title"], "tiêu đề")
		self.assert_scrubbed(values)

	def test_created_or_updated_values_scrub_child_rows(self):
		doc = _StubDoc({"name": "p1", "title": "tiêu đề", "rows": _child_rows()})
		self.assert_scrubbed(site_api._shown(doc, ["title", "rows"]))

	def test_table_held_as_json_text_is_scrubbed(self):
		doc = _StubDoc({"rows": json.dumps(_child_rows())})
		self.assert_scrubbed(site_api._shown(doc, ["rows"]))

	def test_child_row_held_as_document_is_scrubbed(self):
		credential = frappe.get_doc(
			{"doctype": "ERP AI Credential", "label": CHILD_SHOWN, "api_key": FAKE_CREDENTIAL_KEY}
		)
		doc = _StubDoc({"credentials": [credential]}, frappe.get_meta("ERP AI Setting"))
		self.assert_scrubbed(
			site_api._shown(doc, ["credentials"]), fakes=(FAKE_CREDENTIAL_KEY,), shown=(CHILD_SHOWN,)
		)

	def test_child_rows_without_secrets_are_shown_as_before(self):
		doc = _StubDoc({"rows": [{"label": "a"}]})
		self.assertEqual(site_api._shown(doc, ["rows"]), {"rows": '[{"label": "a"}]'})

	def test_compact_json_text_without_secrets_is_shown_unchanged(self):
		doc = _StubDoc({"rows": '[{"label":"a"}]'})
		self.assertEqual(site_api._shown(doc, ["rows"]), {"rows": '[{"label":"a"}]'})


class TestSiteApiChildSecretsAtRealCut(FrappeTestCase):
	"""F-2 at the real VALUE_MAX (200, not patched): secrets are scrubbed first, the text is cut after."""

	def setUp(self):
		_stub_child_meta(self)

	def test_secret_within_the_first_200_characters_is_scrubbed_before_the_cut(self):
		# Unscrubbed, the fake key sits at characters 28-45, inside the cut; scrubbed, the text is 48 + 300 + 3 long.
		doc = _StubDoc({"rows": [{"name": "r1", "api_key": FAKE_CHILD_KEY, "label": "x" * 300}]})
		shown = site_api._shown(doc, ["rows"])["rows"]
		self.assertEqual(shown, '[{"name": "r1", "api_key": "[đã ẩn]", "label": "' + "x" * 152)
		self.assertEqual(len(shown), 200)
		self.assertEqual(shown.count(FAKE_CHILD_KEY), 0)


U2_TEAM = "U2 Nhân sự loại trừ"
U2_PREFIX = "[HR]"
EXCLUDED_KINDS = ("team", "opt_out", "title", "classified")
# The 4 DocTypes of TICKET_CONTENT_DOCTYPES plus Helpdesk's legacy ticket note DocType.
LEGACY_NOTE_DOCTYPE = "HD Ticket Comment"
CONTENT_DOCTYPES = (*TICKET_CONTENT_DOCTYPES, LEGACY_NOTE_DOCTYPE)
# Listed columns that hold the ticket's text, so a leaked row would carry the seed.
LIST_FIELDS = {
	"HD Ticket": ["name", "subject", "description"],
	"Comment": ["name", "content"],
	"Communication": ["name", "subject", "content"],
	"File": ["name", "file_name"],
	LEGACY_NOTE_DOCTYPE: ["name", "content"],
	"Task": ["name", "subject", "ai_ticket"],
}


def _db_insert(values):
	"""Insert the row without hooks or notifications and return its name."""
	doc = frappe.get_doc(values)
	doc.db_insert()
	return doc.name


class _ExcludedTicketCase(FrappeTestCase):
	"""A ticket of every exclusion rule plus a normal one, each with a record of every ticket content DocType.

	The session user is Administrator, who reads every row: only the exclusion can hide or refuse one."""

	def setUp(self):
		# Runs after the rollback: HD Team.after_insert caches an Assignment Rule in Redis.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		set_agent_settings(enabled=0, excluded_teams=U2_TEAM, excluded_title_prefixes=U2_PREFIX)
		if not frappe.db.exists("HD Team", U2_TEAM):
			frappe.get_doc(
				{"doctype": "HD Team", "team_name": U2_TEAM, "users": [{"user": "Administrator"}]}
			).insert(ignore_permissions=True)
		self.seed = f"U2-SEED-{uuid.uuid4().hex}"
		self.plain = f"U2-THUONG-{uuid.uuid4().hex}"

	def ticket(self, kind, text):
		"""A ticket refused by the rule `kind` (or a normal one) holding `text` in its subject and description."""
		subject = f"{U2_PREFIX} {text}" if kind == "title" else f"{text} {kind}"
		name = make_ticket(subject=subject, description=f"<p>{text}</p>").name
		if kind == "team":
			frappe.db.set_value("HD Ticket", name, "agent_group", U2_TEAM)
		elif kind == "opt_out":
			frappe.db.set_value("HD Ticket", name, "ai_opt_out", 1)
		elif kind == "classified":
			make_log_entry(
				ticket=name, entry_type="classify", stop_reason=policy.EXCLUDED_BY_CLASSIFICATION, applied=0
			)
		self.assertEqual(policy.send_refusal(name) is None, kind == "normal", kind)
		return name

	def comment(self, ticket, text, reference_doctype="HD Ticket", **values):
		return _db_insert(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": reference_doctype,
				"reference_name": ticket,
				"content": text,
				**values,
			}
		)

	def file(self, ticket, text):
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{text}.txt",
				"attached_to_doctype": "HD Ticket",
				"attached_to_name": ticket,
				"is_private": 1,
				"content": f"{text} {uuid.uuid4().hex}",
			}
		).insert(ignore_permissions=True)
		physical = doc.get_full_path()
		self.addCleanup(lambda: os.path.exists(physical) and os.remove(physical))
		return doc.name

	def records(self, ticket, text):
		"""`{doctype: name}`: the ticket and one record of every other DocType of CONTENT_DOCTYPES on it."""
		communication = {
			"doctype": "Communication",
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Sent",
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"subject": text,
			"content": text,
		}
		return {
			"HD Ticket": ticket,
			"Comment": self.comment(ticket, text),
			"Communication": _db_insert(communication),
			"File": self.file(ticket, text),
			LEGACY_NOTE_DOCTYPE: _db_insert(
				{"doctype": LEGACY_NOTE_DOCTYPE, "reference_ticket": ticket, "content": text}
			),
		}

	def make_tickets(self):
		"""`{kind: {doctype: name}}` for every exclusion rule and the normal ticket; only the normal one is
		free of the seed."""
		made = {}
		for kind in (*EXCLUDED_KINDS, "normal"):
			text = self.plain if kind == "normal" else self.seed
			made[kind] = self.records(self.ticket(kind, text), text)
		self.assertEqual(sorted(made["normal"]), sorted(CONTENT_DOCTYPES))
		return made

	def assert_no_seed(self, result):
		self.assertEqual(json.dumps(result, ensure_ascii=False, default=str).count(self.seed), 0, result)

	def list_rows(self, doctype, filters, unrestricted=False, limit=site_api.MAX_LIMIT):
		arguments = {
			"doctype": doctype,
			"filters": filters,
			"fields": LIST_FIELDS.get(doctype, ["name"]),
			"limit": limit,
		}
		result = site_api.list_records(arguments, _context(unrestricted=unrestricted))
		self.assertTrue(result["ok"], result)
		return result

	def listed(self, doctype, filters, unrestricted=False):
		"""Names of the listed rows, as text; the seed never appears in the result."""
		result = self.list_rows(doctype, filters, unrestricted)
		self.assert_no_seed(result)
		return [str(row["name"]) for row in result["records"]]


class TestExcludedTicketReads(_ExcludedTicketCase):
	def test_get_refuses_excluded_record_in_both_modes(self):
		made = self.make_tickets()
		for unrestricted in (False, True):
			context = _context(unrestricted=unrestricted)
			for kind, records in made.items():
				for doctype, name in records.items():
					with self.subTest(unrestricted=unrestricted, kind=kind, doctype=doctype):
						result = site_api.get_record({"doctype": doctype, "name": name}, context)
						self.assert_no_seed(result)
						if kind == "normal":
							self.assertTrue(result["ok"], result)
							self.assertEqual(str(result["record"]["name"]), str(name))
						else:
							self.assertEqual(
								result,
								{"ok": False, "reason": policy.EXCLUDED_TICKET_REASON, "doctype": doctype},
							)

	def test_list_hides_excluded_rows_in_both_modes(self):
		made = self.make_tickets()
		for unrestricted in (False, True):
			for doctype in CONTENT_DOCTYPES:
				with self.subTest(unrestricted=unrestricted, doctype=doctype):
					names = [records[doctype] for records in made.values()]
					result = self.list_rows(doctype, [["name", "in", names]], unrestricted)
					self.assert_no_seed(result)
					self.assertEqual(
						[str(row["name"]) for row in result["records"]], [str(made["normal"][doctype])]
					)
					self.assertEqual(result["excluded_note"], site_api.EXCLUDED_LIST_NOTE)

	def test_list_result_identical_when_excluded_ticket_added(self):
		# ADR-034 Ràng buộc 2: the condition is in the query, so `limit` and the order never reveal the excluded.
		marker = f"U2-LIST-{uuid.uuid4().hex}"
		for index in range(3):
			old = f"2001-01-0{index + 1} 00:00:00"
			normal = self.ticket("normal", f"{marker} {self.plain} {index}")
			frappe.db.set_value("HD Ticket", normal, "modified", old, update_modified=False)
			self.comment(normal, f"{marker} {self.plain} {index}", creation=old, modified=old)
		filters = {
			"HD Ticket": [["subject", "like", f"{marker}%"]],
			"Comment": [["content", "like", f"{marker}%"]],
		}

		def results():
			return {doctype: self.list_rows(doctype, rows, limit=2) for doctype, rows in filters.items()}

		before = results()
		# The newest ticket of all, excluded, with three comments newer than every other row.
		excluded = self.ticket("team", f"{marker} {self.seed}")
		for index in range(3):
			self.comment(excluded, f"{marker} {self.seed} {index}")
		after = results()
		self.assertEqual(after, before)
		self.assertEqual([len(result["records"]) for result in after.values()], [2, 2])
		self.assert_no_seed(after)

	def test_name_filter_on_excluded_ticket_returns_zero_rows_with_note(self):
		excluded = self.ticket("team", self.seed)
		self.comment(excluded, self.seed)
		for unrestricted in (False, True):
			for doctype, filters in (
				("Comment", [["reference_name", "=", excluded]]),
				("HD Ticket", [["name", "=", excluded]]),
			):
				with self.subTest(unrestricted=unrestricted, doctype=doctype):
					result = self.list_rows(doctype, filters, unrestricted)
					self.assertEqual(result["records"], [])
					self.assertEqual(result["excluded_note"], site_api.EXCLUDED_LIST_NOTE)

	def test_excluded_note_present_even_with_nothing_excluded(self):
		self.assertEqual(
			site_api.EXCLUDED_LIST_NOTE,
			"Phiếu nhóm loại trừ, phiếu không dùng AI và mọi bản ghi của chúng không bao giờ có trong danh sách.",
		)
		comment = self.comment(self.ticket("normal", self.plain), self.plain)
		with patch.object(policy, "excluded_ticket_names", return_value=[]):
			result = self.list_rows("Comment", [["name", "=", comment]])
		self.assertEqual([row["name"] for row in result["records"]], [comment])
		self.assertEqual(result["excluded_note"], site_api.EXCLUDED_LIST_NOTE)
		# A DocType that carries no ticket content gets no note.
		todo = _db_insert({"doctype": "ToDo", "description": self.plain})
		result = self.list_rows("ToDo", [["name", "=", todo]])
		self.assertEqual([row["name"] for row in result["records"]], [todo])
		self.assertNotIn("excluded_note", result)

	def test_comment_without_reference_still_listed(self):
		marker = f"U2-LIST-{uuid.uuid4().hex}"
		excluded = self.ticket("team", self.seed)
		no_reference = self.comment(None, f"{marker} a", reference_doctype=None)
		# Another DocType's comment whose reference_name is the excluded ticket's number.
		other_doctype = self.comment(str(excluded), f"{marker} b", reference_doctype="ToDo")
		self.comment(excluded, f"{marker} {self.seed}")
		for unrestricted in (False, True):
			with self.subTest(unrestricted=unrestricted):
				listed = self.listed("Comment", [["content", "like", f"{marker}%"]], unrestricted)
				self.assertEqual(sorted(listed), sorted([no_reference, other_doctype]))

	def test_empty_ticket_link_row_still_listed(self):
		excluded = self.ticket("team", self.seed)
		empty_note = _db_insert(
			{"doctype": LEGACY_NOTE_DOCTYPE, "reference_ticket": None, "content": self.plain}
		)
		excluded_note = _db_insert(
			{"doctype": LEGACY_NOTE_DOCTYPE, "reference_ticket": excluded, "content": self.seed}
		)
		# A Task a person made has no ai_ticket (A-11).
		empty_task = _db_insert({"doctype": "Task", "subject": self.plain})
		excluded_task = _db_insert({"doctype": "Task", "subject": self.seed, "ai_ticket": excluded})
		for unrestricted in (False, True):
			with self.subTest(unrestricted=unrestricted):
				notes = self.listed(
					LEGACY_NOTE_DOCTYPE, [["name", "in", [empty_note, excluded_note]]], unrestricted
				)
				self.assertEqual(notes, [empty_note])
				tasks = self.listed("Task", [["name", "in", [empty_task, excluded_task]]], unrestricted)
				self.assertEqual(tasks, [empty_task])

	def test_task_of_excluded_ticket_hidden(self):
		normal_task = _db_insert(
			{"doctype": "Task", "subject": self.plain, "ai_ticket": self.ticket("normal", self.plain)}
		)
		excluded_task = _db_insert(
			{"doctype": "Task", "subject": self.seed, "ai_ticket": self.ticket("team", self.seed)}
		)
		for unrestricted in (False, True):
			with self.subTest(unrestricted=unrestricted):
				listed = self.listed("Task", [["name", "in", [normal_task, excluded_task]]], unrestricted)
				self.assertEqual(listed, [normal_task])
				result = site_api.get_record(
					{"doctype": "Task", "name": excluded_task}, _context(unrestricted=unrestricted)
				)
				self.assertEqual(
					result, {"ok": False, "reason": policy.EXCLUDED_TICKET_REASON, "doctype": "Task"}
				)

	def test_static_link_on_dynamic_doctype_also_filtered(self):
		excluded = self.ticket("team", self.seed)
		normal = self.ticket("normal", self.plain)
		todo = _db_insert({"doctype": "ToDo", "description": self.plain})
		# The dynamic pair names a ToDo; only the static Link points at a ticket.
		via_static = self.comment(todo, self.seed, "ToDo", link_doctype="HD Ticket", link_name=excluded)
		via_static_normal = self.comment(todo, self.plain, "ToDo", link_doctype="HD Ticket", link_name=normal)
		real_fieldnames = policy.ticket_link_fieldnames

		def fieldnames(doctype):
			# Comment as if a Custom Field made `link_name` a Link to HD Ticket. Stubbed in this process only: a
			# real Custom Field runs ALTER TABLE (frappe.db.updatedb commits) and would put the changed meta of
			# Comment into the Redis cache other sessions of the shared site read.
			return ("link_name",) if doctype == "Comment" else real_fieldnames(doctype)

		with patch.object(policy, "ticket_link_fieldnames", side_effect=fieldnames):
			self.assertEqual(
				policy.ticket_link_columns("Comment"),
				(("reference_doctype", "reference_name"), (None, "link_name")),
			)
			for unrestricted in (False, True):
				with self.subTest(unrestricted=unrestricted):
					listed = self.listed(
						"Comment", [["name", "in", [via_static, via_static_normal]]], unrestricted
					)
					self.assertEqual(listed, [via_static_normal])

	def test_record_tools_granted_when_switch_on(self):
		inputs = registry.GrantInputs("L3", "L3", True, PermissionSwitches(record_tools=True))
		self.assertLessEqual({"api_list_records", "api_get_record"}, registry.grant(inputs).names())


# One harmless change per DocType, for the update tool.
WRITE_VALUES = {
	"HD Ticket": {"subject": "U2 đổi"},
	"Comment": {"content": "U2 đổi"},
	"Communication": {"content": "U2 đổi"},
	"File": {"file_name": "U2-doi.txt"},
	LEGACY_NOTE_DOCTYPE: {"content": "U2 đổi"},
	"Task": {"subject": "U2 đổi"},
}


class TestExcludedTicketWrites(_ExcludedTicketCase):
	def assert_refused(self, result, doctype):
		self.assertEqual(result, {"ok": False, "reason": policy.EXCLUDED_TICKET_REASON, "doctype": doctype})
		self.assert_no_seed(result)

	def stored(self, doctype, name):
		return frappe.db.get_value(doctype, name, "*", as_dict=True)

	def test_update_delete_submit_refused_on_excluded_records(self):
		made = self.make_tickets()
		for kind in EXCLUDED_KINDS:
			ticket = made[kind]["HD Ticket"]
			made[kind]["Task"] = _db_insert({"doctype": "Task", "subject": self.seed, "ai_ticket": ticket})
		for unrestricted in (False, True):
			context = _context(unrestricted=unrestricted)
			for kind in EXCLUDED_KINDS:
				for doctype, name in made[kind].items():
					calls = {
						"update": (
							site_api.update_record,
							{"doctype": doctype, "name": name, "values": WRITE_VALUES[doctype]},
						),
						"delete": (site_api.delete_record, {"doctype": doctype, "name": name}),
						"submit": (
							site_api.submit_record,
							{"doctype": doctype, "name": name, "action": "submit"},
						),
					}
					for tool, (handler, arguments) in calls.items():
						with self.subTest(unrestricted=unrestricted, kind=kind, doctype=doctype, tool=tool):
							before = self.stored(doctype, name)
							self.assertTrue(before)
							self.assert_refused(handler(arguments, context), doctype)
							self.assertEqual(self.stored(doctype, name), before)

	def test_create_linked_to_excluded_ticket_refused(self):
		excluded = self.ticket("team", self.seed)
		normal = self.ticket("normal", self.plain)
		comment = {"comment_type": "Comment", "reference_doctype": "HD Ticket", "content": self.seed}
		communication = {
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Sent",
			"reference_doctype": "HD Ticket",
			"subject": self.seed,
			"content": self.seed,
		}
		# `(doctype, values, column holding the seed)`; the name as a number and as text, the type in any case.
		cases = (
			("Comment", {**comment, "reference_name": excluded}, "content"),
			(
				"Comment",
				{**comment, "reference_doctype": "hd ticket", "reference_name": str(excluded)},
				"content",
			),
			("Communication", {**communication, "reference_name": excluded}, "content"),
			(LEGACY_NOTE_DOCTYPE, {"reference_ticket": excluded, "content": self.seed}, "content"),
			("Task", {"subject": self.seed, "ai_ticket": excluded}, "subject"),
		)
		for unrestricted in (False, True):
			context = _context(unrestricted=unrestricted)
			for doctype, values, column in cases:
				with self.subTest(unrestricted=unrestricted, doctype=doctype, values=values):
					result = site_api.create_record({"doctype": doctype, "values": values}, context)
					self.assert_refused(result, doctype)
					self.assertEqual(frappe.db.count(doctype, {column: ["like", f"%{self.seed}%"]}), 0)
		# The same link to a normal ticket is created.
		values = {**comment, "reference_name": normal, "content": self.plain}
		result = site_api.create_record({"doctype": "Comment", "values": values}, _context())
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Comment", result["name"], "reference_name"), str(normal))

	def test_update_moving_record_into_excluded_ticket_refused(self):
		excluded = self.ticket("team", self.seed)
		normal = self.ticket("normal", self.plain)
		comment = self.comment(normal, self.plain)
		task = _db_insert({"doctype": "Task", "subject": self.plain, "ai_ticket": normal})
		note = _db_insert({"doctype": LEGACY_NOTE_DOCTYPE, "reference_ticket": normal, "content": self.plain})
		# A ToDo's comment whose reference_name is the excluded ticket's number: only the type column moves it.
		todo_comment = self.comment(str(excluded), self.plain, "ToDo")
		cases = (
			("Comment", comment, {"reference_name": excluded}),
			("Task", task, {"ai_ticket": excluded}),
			(LEGACY_NOTE_DOCTYPE, note, {"reference_ticket": excluded}),
			("Comment", todo_comment, {"reference_doctype": "HD Ticket"}),
		)
		for unrestricted in (False, True):
			context = _context(unrestricted=unrestricted)
			for doctype, name, values in cases:
				with self.subTest(unrestricted=unrestricted, doctype=doctype, values=values):
					before = self.stored(doctype, name)
					arguments = {"doctype": doctype, "name": name, "values": values}
					self.assert_refused(site_api.update_record(arguments, context), doctype)
					self.assertEqual(self.stored(doctype, name), before)
