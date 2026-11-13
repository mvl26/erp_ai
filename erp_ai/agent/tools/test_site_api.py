from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

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
		self.assertEqual(result, {"ok": True, "doctype": "User", "name": NEW_USER})
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
		for doctype in ("Custom DocPerm", "Role Permission", "Salary Slip", "Custom Role"):
			result = self.create(doctype, {"role": ALLOWED_ROLE})
			self.assertFalse(result["ok"], doctype)

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
		enabled = self.update("Server Script", result["name"], {"disabled": 0})
		self.assertTrue(enabled["ok"], enabled)
		self.assertEqual(frappe.db.get_value("Server Script", result["name"], "disabled"), 1)

	def test_update_changes_only_the_given_fields(self):
		created = self.create("Note", {"title": NOTE_TITLE, "public": 1, "content": "cũ"})
		self.assertTrue(created["ok"], created)
		result = self.update("Note", created["name"], {"content": "mới"})
		self.assertEqual(result, {"ok": True, "doctype": "Note", "name": created["name"]})
		note = frappe.get_doc("Note", created["name"])
		self.assertEqual((note.title, note.public, note.content), (NOTE_TITLE, 1, "mới"))

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
		return [
			spec["name"]
			for spec in registry.get_unrestricted_tool_schemas(level, has_instructor, unrestricted)
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
		self.assertEqual(created, {"ok": True, "doctype": "User", "name": NEW_USER})
		self.assertEqual(self.roles_of(NEW_USER), {"System Manager", ROLE_INSTRUCTOR})
		own = self.run_tool(
			"api_update_record", {"doctype": "User", "name": AGENT, "values": {"first_name": "Đổi"}}
		)
		self.assertTrue(own["ok"], own)
		self.assertEqual(frappe.db.get_value("User", AGENT, "first_name"), "Đổi")

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
			"api_create_record", {"doctype": "Note", "values": {"title": NOTE_TITLE, "public": 1}}
		)
		result = self.run_tool("api_delete_record", {"doctype": "Note", "name": created["name"]})
		self.assertEqual(result, {"ok": True, "doctype": "Note", "name": created["name"]})
		self.assertFalse(frappe.db.exists("Note", created["name"]))
		missing = self.run_tool("api_delete_record", {"doctype": "Note", "name": created["name"]})
		self.assertFalse(missing["ok"])
		self.assertIn("không tìm thấy bản ghi", missing["reason"])

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
		for action in ("submit", "cancel"):
			with (
				patch.object(site_api, "_is_submittable", return_value=True),
				patch.object(frappe.model.document.Document, action, autospec=True) as called,
			):
				result = self.run_tool(
					"api_submit_record", {"doctype": "Note", "name": created["name"], "action": action}
				)
			self.assertEqual(result, {"ok": True, "doctype": "Note", "name": created["name"]}, action)
			called.assert_called_once()

	def test_call_method_runs_whitelisted_methods_only(self):
		result = self.run_tool(
			"api_call_method",
			{
				"method": "frappe.client.get_value",
				"arguments": {"doctype": "User", "filters": BOSS, "fieldname": "email"},
			},
		)
		self.assertEqual(result, {"ok": True, "method": "frappe.client.get_value", "result": {"email": BOSS}})
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
