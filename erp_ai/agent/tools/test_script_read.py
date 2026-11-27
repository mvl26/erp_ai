"""2026-11-27: the read-only Server Script tools (group `script_read`), opened by `server_script_read_enabled`.

Every Server Script made here is disabled and rolled back with its test: an enabled one would land in the shared
`server_script_map` cache of the site.
"""

import dataclasses
import inspect
import itertools
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import server_script_read
from erp_ai.agent.policy import PermissionSwitches
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import registry, script_read
from erp_ai.agent.tools.read import TOOL_RESULT_MAX_CHARS
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import AGENT_USER, HELPDESK_AGENT_ROLE, ROLE_AGENT

SCRIPT_TOOL_NAMES = ["list_server_scripts", "get_server_script"]
NOT_GRANTED = {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}
PREFIX = "ERPAI-TEST-SSR"
# The roles the agent account is meant to hold (tasks._agent_role_drift): neither reads Server Script.
PLAIN_AGENT = "erpai-test-ssr.agent@example.com"
OTHER_SWITCHES = ("unrestricted", "record_tools", "act_now", "code_change", "one_click_approval", "console")
SECRET_KEY = "sk-" + "a1B2c3D4e5F6g7H8i9J0k1L2"
BEARER_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOi" + "Jsecret0123456789"
PASSWORD = "Mat-khau-2026!"
SECRET_SCRIPT = (
	f'api_key = "{SECRET_KEY}"\n'
	f'headers = {{"Authorization": "Bearer {BEARER_TOKEN}"}}\n'
	f'password = "{PASSWORD}"\n'
	'frappe.sendmail(recipients=["ke.toan@example.com"], subject="Hóa đơn đến hạn thanh toán")\n'
)
LIST_KEYS = {
	"name",
	"script_type",
	"reference_doctype",
	"doctype_event",
	"api_method",
	"event_frequency",
	"disabled",
	"modified",
}


def _inputs(level="L1", has_instructor=False, server_script_read=True, **fields):
	switches = PermissionSwitches(server_script_read=server_script_read)
	return dataclasses.replace(registry.GrantInputs(level, level, has_instructor, switches), **fields)


def _names(inputs) -> list[str]:
	return [spec.name for spec in registry.grant(inputs).specs]


def _context(level="L1", server_script_read=True, agent_user=AGENT_USER):
	return ToolContext(
		ticket_name="TKT-SSR",
		effective_level=level,
		instructor=None,
		run_id="run-ssr",
		category_mapping={},
		agent_user=agent_user,
		server_script_read=server_script_read,
	)


class TestScriptReadGrant(FrappeTestCase):
	"""The group follows its switch above L0: no instructor needed and granted over budget, like the `read` group; not
	below the confidence threshold (that run only asks one question and keeps the read group and the ask tools), never
	in a KB-draft run."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_switch_off_gives_no_script_tool(self):
		every_other = dict.fromkeys(OTHER_SWITCHES, True)
		for level, has_instructor, below in itertools.product(
			("L0", "L1", "L2", "L3"), (False, True), (False, True)
		):
			with self.subTest((level, has_instructor, below)):
				inputs = registry.GrantInputs(
					level, level, has_instructor, PermissionSwitches(**every_other), below_threshold=below
				)
				self.assertFalse(set(SCRIPT_TOOL_NAMES) & set(_names(inputs)))

	def test_switch_on_above_l0_grants_both_tools_without_an_instructor(self):
		for level, has_instructor, over_budget in itertools.product(
			("L1", "L2", "L3"), (False, True), (False, True)
		):
			with self.subTest((level, has_instructor, over_budget)):
				names = _names(_inputs(level, has_instructor, over_budget=over_budget))
				self.assertEqual(names[-2:], SCRIPT_TOOL_NAMES)
				# the main-path level (category cap) does not close a read group
				self.assertIn("get_server_script", _names(_inputs(level, main_path_level="L0")))

	def test_switch_on_adds_only_the_two_tools_and_no_block(self):
		for level in ("L1", "L3"):
			with self.subTest(level):
				off = registry.grant(_inputs(level, True, server_script_read=False, below_threshold=False))
				on = registry.grant(_inputs(level, True, below_threshold=False))
				self.assertEqual(
					[s.name for s in on.specs], [*(s.name for s in off.specs), *SCRIPT_TOOL_NAMES]
				)
				self.assertEqual(dataclasses.replace(on, specs=()), dataclasses.replace(off, specs=()))
				self.assertEqual({s.group for s in on.specs} - {s.group for s in off.specs}, {"script_read"})

	def test_below_threshold_gives_no_script_tool(self):
		every_switch = dict.fromkeys(OTHER_SWITCHES, True)
		for level, has_instructor in itertools.product(("L1", "L2", "L3"), (False, True)):
			with self.subTest((level, has_instructor)):
				switches = PermissionSwitches(server_script_read=True, **every_switch)
				inputs = registry.GrantInputs(level, level, has_instructor, switches, below_threshold=True)
				granted = registry.grant(inputs)
				self.assertFalse(set(SCRIPT_TOOL_NAMES) & granted.names())
				self.assertIs(granted.ask_only_block, True)
				self.assertIn("get_record", granted.names())

	def test_l0_and_unknown_level_grant_nothing(self):
		for level in ("L0", "LX"):
			for has_instructor in (False, True):
				with self.subTest((level, has_instructor)):
					self.assertEqual(registry.grant(_inputs(level, has_instructor)), registry.Grant(specs=()))

	def test_kb_draft_run_never_gets_script_tools(self):
		for level, below in itertools.product(("L1", "L2", "L3"), (False, True)):
			with self.subTest((level, below)):
				kb = _names(_inputs(level, True, kb_draft_run=True, below_threshold=below))
				self.assertFalse(set(SCRIPT_TOOL_NAMES) & set(kb))
				self.assertEqual(kb[-1], "create_kb_draft")

	def test_tool_context_carries_the_switch(self):
		self.assertIs(_context().grant_inputs().switches.server_script_read, True)
		self.assertIs(_context(server_script_read=False).grant_inputs().switches.server_script_read, False)
		self.assertIs(ToolContext.__dataclass_fields__["server_script_read"].default, False)

	def test_execute_refuses_when_not_granted(self):
		for context in (_context(server_script_read=False), _context(level="L0")):
			with self.subTest(context):
				for name, arguments in (("get_server_script", {"name": "x"}), ("list_server_scripts", {})):
					self.assertEqual(execute_tool(name, arguments, context), NOT_GRANTED, name)

	def test_specs_are_read_only_and_in_their_own_group(self):
		self.assertEqual([spec.name for spec in script_read.TOOLS], SCRIPT_TOOL_NAMES)
		self.assertEqual({spec.group for spec in script_read.TOOLS}, {registry.SCRIPT_READ_GROUP})
		self.assertEqual(registry.SCRIPT_READ_GROUP, "script_read")
		# never edits, enables or disables a script: no write call in either module
		for module in (script_read, server_script_read):
			source = inspect.getsource(module)
			for word in (".save(", ".insert(", "set_value", "db_set", "delete", ".submit(", "frappe.db.sql"):
				self.assertNotIn(word, source, f"{module.__name__}: {word}")


class TestScriptReadTools(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("User", AGENT_USER))
		if not frappe.db.exists("User", PLAIN_AGENT):
			frappe.get_doc(
				{"doctype": "User", "email": PLAIN_AGENT, "first_name": "SSR", "send_welcome_email": 0}
			).insert()
		frappe.get_doc("User", PLAIN_AGENT).add_roles(ROLE_AGENT, HELPDESK_AGENT_ROLE)
		self.due = self._script(
			f"{PREFIX} nhắc hạn hóa đơn",
			script_type="Scheduler Event",
			event_frequency="Daily",
			script=SECRET_SCRIPT,
			modified="2030-01-03 00:00:00",
		)
		self.todo = self._script(
			f"{PREFIX} ToDo trước khi lưu",
			script_type="DocType Event",
			reference_doctype="ToDo",
			doctype_event="Before Save",
			modified="2030-01-02 00:00:00",
		)
		self.api = self._script(
			f"{PREFIX} API",
			script_type="API",
			api_method="erpai_test_ssr_probe",
			modified="2030-01-01 00:00:00",
		)

	def _script(self, name, *, modified, script="frappe.response['message'] = 1", **values):
		frappe.get_doc(
			{"doctype": "Server Script", "name": name, "script": script, "disabled": 1, **values}
		).insert()
		frappe.db.set_value("Server Script", name, "modified", modified, update_modified=False)
		return name

	def _run(self, name, arguments, context=None):
		return execute_tool(name, arguments, context or _context())

	def test_get_returns_the_fields_with_secrets_masked(self):
		result = self._run("get_server_script", {"name": self.due})
		self.assertTrue(result["ok"], result)
		record = result["server_script"]
		stored = frappe.db.get_value("Server Script", self.due, [*LIST_KEYS, "cron_format"], as_dict=True)
		self.assertEqual({key: record[key] for key in stored}, dict(stored))
		self.assertEqual(set(record), {*LIST_KEYS, "cron_format", "script", "script_cut"})
		self.assertIs(record["script_cut"], False)
		self.assertEqual((record["script_type"], record["disabled"]), ("Scheduler Event", 1))
		script = record["script"]
		# the key names, the Bearer prefix and the code around them stay; the values are masked
		for kept in ('api_key = "', "Bearer ", 'password = "', "Hóa đơn đến hạn thanh toán"):
			self.assertIn(kept, script)
		self.assertEqual(script.count(MASK), 3)
		dumped = json.dumps(result, ensure_ascii=False, default=str)
		for secret in (SECRET_KEY, BEARER_TOKEN, PASSWORD, "a1B2c3D4", "Mat-khau"):
			self.assertNotIn(secret, dumped)

	def test_long_script_is_cut_so_the_result_fits_the_tool_result_cap(self):
		lines = "".join(
			f'if doc.get("f{index}"):\n\tfrappe.msgprint("dòng {index}")\n' for index in range(2000)
		)
		name = self._script(f"{PREFIX} dài", script_type="API", api_method="erpai_test_ssr_long", script=lines,
			modified="2030-01-04 00:00:00")  # fmt: skip
		result = self._run("get_server_script", {"name": name})
		self.assertTrue(result["ok"], result)
		record = result["server_script"]
		self.assertIs(record["script_cut"], True)
		self.assertTrue(lines.startswith(record["script"]))
		self.assertGreater(len(record["script"]), TOOL_RESULT_MAX_CHARS // 4)
		# the runner cuts the JSON of a result at TOOL_RESULT_MAX_CHARS: this one is never cut there
		self.assertLessEqual(len(json.dumps(result, ensure_ascii=False, default=str)), TOOL_RESULT_MAX_CHARS)

	def test_unknown_or_missing_name_is_refused(self):
		self.assertEqual(
			self._run("get_server_script", {"name": f"{PREFIX} không có"}),
			{"ok": False, "reason": "không tìm thấy Server Script"},
		)
		self.assertEqual(self._run("get_server_script", {})["reason"], "tham số không hợp lệ: name")
		self.assertEqual(
			script_read.get_server_script({"name": ""}, _context()),
			{"ok": False, "reason": "thiếu name"},
		)

	def test_list_includes_disabled_scripts_newest_first_without_body(self):
		result = self._run("list_server_scripts", {"name_contains": PREFIX})
		self.assertTrue(result["ok"], result)
		rows = result["server_scripts"]
		self.assertEqual([row["name"] for row in rows], [self.due, self.todo, self.api])
		self.assertIs(result["more"], False)
		for row in rows:
			self.assertEqual(set(row), LIST_KEYS)
			self.assertEqual(row["disabled"], 1)
		self.assertNotIn(SECRET_KEY, json.dumps(result, ensure_ascii=False, default=str))

	def test_list_filters(self):
		cases = {
			"reference_doctype": ({"reference_doctype": "ToDo", "name_contains": PREFIX}, [self.todo]),
			"script_type": ({"script_type": "API", "name_contains": PREFIX}, [self.api]),
			"name_contains": ({"name_contains": f"{PREFIX} nhắc hạn"}, [self.due]),
			"name, any case": ({"name_contains": "erpai-test-ssr todo"}, [self.todo]),
			"nothing": ({"name_contains": f"{PREFIX} không có"}, []),
		}
		for case, (arguments, expected) in cases.items():
			with self.subTest(case):
				result = self._run("list_server_scripts", arguments)
				self.assertTrue(result["ok"], result)
				self.assertEqual([row["name"] for row in result["server_scripts"]], expected)

	def test_list_limit(self):
		result = self._run("list_server_scripts", {"name_contains": PREFIX, "limit": 2})
		self.assertEqual([row["name"] for row in result["server_scripts"]], [self.due, self.todo])
		self.assertIs(result["more"], True)
		properties = script_read.TOOLS[0].schema["input_schema"]["properties"]
		self.assertEqual((properties["limit"]["minimum"], properties["limit"]["maximum"]), (1, 50))
		self.assertEqual(script_read.DEFAULT_LIST_LIMIT, 20)
		for limit in (0, 51, True):
			with self.subTest(limit=limit):
				self.assertEqual(
					self._run("list_server_scripts", {"limit": limit}),
					{"ok": False, "reason": "tham số không hợp lệ: limit"},
				)
		# the script types offered are the DocType's own options
		options = frappe.get_meta("Server Script").get_field("script_type").options.split("\n")
		self.assertEqual(properties["script_type"]["enum"], [option for option in options if option])

	def test_reads_skip_role_permissions_for_the_agent_account(self):
		# The switch is the grant: an account without any Server Script permission still reads (AGENT_USER as it is
		# on this site, and an account with exactly the agent's intended roles), and nothing is written.
		self.assertFalse(frappe.has_permission("Server Script", "read", user=PLAIN_AGENT))
		before = frappe.db.get_value("Server Script", self.due, ["modified", "disabled"], as_dict=True)
		for user in (AGENT_USER, PLAIN_AGENT):
			with self.subTest(user=user):
				frappe.set_user(user)
				listed = self._run(
					"list_server_scripts", {"name_contains": PREFIX}, _context(agent_user=user)
				)
				got = self._run("get_server_script", {"name": self.due}, _context(agent_user=user))
				frappe.set_user("Administrator")
				self.assertEqual(len(listed["server_scripts"]), 3, listed)
				self.assertTrue(got["ok"], got)
				self.assertIn(MASK, got["server_script"]["script"])
		self.assertEqual(
			frappe.db.get_value("Server Script", self.due, ["modified", "disabled"], as_dict=True), before
		)

	def test_handler_refuses_without_the_switch_in_its_context(self):
		# a second lock behind the grant: the handler itself reads the switch of its context
		closed = _context(server_script_read=False)
		for handler, arguments in (
			(script_read.list_server_scripts, {}),
			(script_read.get_server_script, {"name": self.due}),
		):
			with self.subTest(handler.__name__):
				self.assertEqual(
					handler(arguments, closed), {"ok": False, "reason": script_read.SWITCH_OFF_REASON}
				)
