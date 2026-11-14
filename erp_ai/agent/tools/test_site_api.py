import datetime
import json
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import change_link
from erp_ai.agent.tools import registry, site_api
from erp_ai.agent.tools.registry import ToolContext, execute_tool, get_tool_schemas
from erp_ai.constants import ROLE_AGENT, ROLE_INSTRUCTOR

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
	"""The tool result as the model sees it: the runner takes `_snapshot` out (AC-13, asserted on its own)."""
	return {key: value for key, value in result.items() if key != "_snapshot"}


def _make_user(email, *roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "SITEAPI", "send_welcome_email": 0}
		).insert()
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)


def _context(level="L3", instructor=BOSS, change_enabled=True, agent_user=AGENT, unrestricted=False):
	return ToolContext(
		ticket_name="TKT-SITEAPI",
		effective_level=level,
		instructor=instructor,
		run_id="run-siteapi",
		category_mapping={},
		agent_user=agent_user,
		change_enabled=change_enabled,
		unrestricted=unrestricted,
	)


class TestSiteApiGrant(FrappeTestCase):
	def names(self, level, has_instructor, change_enabled):
		granted = get_tool_schemas(level, has_instructor, change_enabled)
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
		self.assertIs(registry.grants_site_admin_tools("L3", True, True), True)
		self.assertIs(registry.grants_site_admin_tools("L3", True, False), False)
		self.assertIs(registry.grants_site_admin_tools("L3", False, True), False)
		self.assertIs(registry.grants_site_admin_tools("L2", True, True), False)

	def test_execute_refuses_when_not_granted(self):
		arguments = {"doctype": "Note", "values": {"title": NOTE_TITLE}}
		for context in (
			_context(change_enabled=False),
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


class TestUnrestrictedGrant(FrappeTestCase):
	def names(self, level, has_instructor, unrestricted):
		# Only the site_admin + site_unrestricted tools (site_api.TOOLS), change switch off.
		record_tools = {spec.name for spec in site_api.TOOLS}
		return [
			spec["name"]
			for spec in get_tool_schemas(level, has_instructor, False, unrestricted)
			if spec["name"] in record_tools
		]

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
			names = [spec["name"] for spec in get_tool_schemas(level, True, True)]
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
