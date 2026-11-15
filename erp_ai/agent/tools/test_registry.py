import dataclasses
import importlib
import inspect
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.policy import PermissionSwitches
from erp_ai.agent.tools import registry, route_ticket
from erp_ai.agent.tools.registry import (
	ASK_TOOL_NAMES,
	ToolContext,
	ToolSpec,
	execute_tool,
	get_tool_schemas,
)
from erp_ai.agent.tools.source import GIT_SUBCOMMANDS
from erp_ai.constants import PROPOSAL_DOCTYPE, ROLE_AGENT
from erp_ai.test_utils import GitSandbox

REAL_ALL_SPECS = registry._all_specs
AGENT_EMAIL = "erpai-test-t27.agent@example.com"
SEED_TYPE = "ERPAI-TEST-T27 Loại"
FORBIDDEN_ROUTE_PARAMETER_WORDS = (
	"assign",
	"allocat",
	"owner",
	"person",
	"user",
	"agent",
	"sla",
	"priority",
	"response",
	"resolution_by",
	"score",
	"complexity",
	"importance",
)
ROUTE_FUNCTION_NAMES = (
	"apply_route",
	"assign_owner",
	"create_routed_task",
	"post_routing_comment",
	"route_ticket",
)
NOTE_TITLE = "erp_ai registry savepoint probe"
OTHER_NOTE_TITLE = "erp_ai registry earlier note"


def _schema(name, properties=None, required=None):
	return {
		"name": name,
		"description": name,
		"input_schema": {
			"type": "object",
			"properties": properties or {},
			"required": required or [],
		},
	}


def _echo(arguments, context):
	return {"ok": True, "echo": arguments, "ticket": context.ticket_name}


def _spec(name, group, properties=None, required=None, handler=_echo):
	return ToolSpec(name, group, _schema(name, properties, required), handler)


def _specs():
	return [
		_spec(
			"do_read",
			"read",
			{
				"limit": {"type": "integer", "minimum": 1, "maximum": 50},
				"query": {"type": "string", "minLength": 2, "maxLength": 5},
				"mode": {"type": "string", "enum": ["a", "b"]},
				"flag": {"type": "boolean"},
				"tags": {"type": "array", "maxItems": 2, "items": {"type": "string"}},
			},
			["query"],
		),
		_spec("do_ticket", "ticket_write"),
		_spec("do_task", "task_write"),
	]


def _specs_with_change():
	return [*_specs(), _spec("do_change", "change_propose")]


def _context(level="L1", instructor=None, change_enabled=False, unrestricted=False):
	return ToolContext(
		ticket_name="TKT-1",
		effective_level=level,
		instructor=instructor,
		run_id="run-1",
		category_mapping={},
		agent_user="ai.agent@miyano.com.vn",
		change_enabled=change_enabled,
		unrestricted=unrestricted,
	)


def _schema_keys(rule):
	"""Every property name in a JSON-schema fragment, nested ones included."""
	keys = []
	for key, sub in (rule.get("properties") or {}).items():
		keys.append(key)
		keys.extend(_schema_keys(sub))
	if "items" in rule:
		keys.extend(_schema_keys(rule["items"]))
	return keys


def _insert_note():
	frappe.get_doc({"doctype": "Note", "title": NOTE_TITLE, "public": 1}).insert()


class TestRegistry(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		specs_patcher = patch.object(registry, "_all_specs", _specs)
		specs_patcher.start()
		self.addCleanup(specs_patcher.stop)

	def names(self, level, has_instructor):
		return [s["name"] for s in get_tool_schemas(level, has_instructor, False)]

	def test_l0_has_no_tools(self):
		self.assertEqual(self.names("L0", True), [])

	def test_unknown_level_has_no_tools(self):
		self.assertEqual(self.names("L9", True), [])

	def test_l1_to_l3_get_read_and_ticket_write_only(self):
		for level in ("L1", "L2", "L3"):
			self.assertEqual(self.names(level, False), ["do_read", "do_ticket"], level)

	def test_instructor_adds_task_write(self):
		self.assertEqual(self.names("L1", True), ["do_read", "do_ticket", "do_task"])

	def test_returned_schemas_are_copies(self):
		first = get_tool_schemas("L1", False, False)
		first[0]["cache_control"] = {"type": "ephemeral"}
		first[0]["input_schema"]["properties"].clear()
		second = get_tool_schemas("L1", False, False)
		self.assertNotIn("cache_control", second[0])
		self.assertIn("query", second[0]["input_schema"]["properties"])

	def test_execute_runs_granted_tool(self):
		result = execute_tool("do_read", {"query": "abc"}, _context())
		self.assertEqual(result, {"ok": True, "echo": {"query": "abc"}, "ticket": "TKT-1"})

	def test_execute_rejects_tool_not_granted_and_bad_arguments(self):
		denied = execute_tool("do_task", {}, _context("L1", None))
		self.assertFalse(denied["ok"])
		self.assertIn("không được cấp", denied["reason"])
		invalid = execute_tool("do_read", {"query": "abc", "extra": 1}, _context())
		self.assertEqual(invalid, {"ok": False, "reason": "tham số không hợp lệ: extra"})

	def test_execute_rejects_tool_not_granted(self):
		for name, context in (
			("nope", _context()),
			("do_task", _context("L1", None)),
			("do_read", _context("L0", "boss@x.com")),
		):
			result = execute_tool(name, {"query": "abc"}, context)
			self.assertFalse(result["ok"], name)
			self.assertIn("không được cấp", result["reason"])

	def test_instructor_context_may_run_task_write(self):
		result = execute_tool("do_task", {}, _context("L1", "boss@x.com"))
		self.assertTrue(result["ok"])

	def test_execute_rejects_bad_arguments(self):
		cases = {
			"query": {},
			"mode": {"query": "abc", "mode": "z"},
			"limit": {"query": "abc", "limit": 51},
			"flag": {"query": "abc", "flag": "yes"},
			"tags": {"query": "abc", "tags": ["a", "b", "c"]},
			"extra": {"query": "abc", "extra": 1},
		}
		for key, arguments in cases.items():
			result = execute_tool("do_read", arguments, _context())
			self.assertFalse(result["ok"], key)
			self.assertEqual(result["reason"], f"tham số không hợp lệ: {key}")

	def test_execute_rejects_length_and_type_edges(self):
		for key, arguments in (
			("query", {"query": "toolong"}),
			("query", {"query": "a"}),
			("query", {"query": 5}),
			("limit", {"query": "abc", "limit": 0}),
			("limit", {"query": "abc", "limit": True}),
			("limit", {"query": "abc", "limit": 1.5}),
			("tags", {"query": "abc", "tags": "a"}),
			("tags", {"query": "abc", "tags": [1]}),
		):
			result = execute_tool("do_read", arguments, _context())
			self.assertEqual(result["reason"], f"tham số không hợp lệ: {key}", arguments)

	def test_execute_rejects_non_object_for_object_rule(self):
		specs = [_spec("do_read", "read", {"values": {"type": "object"}})]
		with patch.object(registry, "_all_specs", lambda: specs):
			for given in (["a"], "a", 1, None):
				result = execute_tool("do_read", {"values": given}, _context())
				self.assertEqual(result, {"ok": False, "reason": "tham số không hợp lệ: values"}, given)
			accepted = execute_tool("do_read", {"values": {"a": 1}}, _context())
		self.assertTrue(accepted["ok"])

	def test_invalid_reason_cuts_model_supplied_key(self):
		result = execute_tool("do_read", {"query": "abc", "x" * 5000: 1}, _context())
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)

	def test_execute_rejects_non_dict_arguments(self):
		result = execute_tool("do_read", ["query"], _context())
		self.assertFalse(result["ok"])
		self.assertIn("tham số không hợp lệ", result["reason"])

	def test_execute_accepts_boundary_values(self):
		arguments = {"query": "ab", "limit": 50, "mode": "b", "flag": False, "tags": ["x", "y"]}
		self.assertTrue(execute_tool("do_read", arguments, _context())["ok"])
		self.assertTrue(execute_tool("do_read", {"query": "abcde", "limit": 1}, _context())["ok"])

	def test_unexpected_exception_rolls_back_to_savepoint_and_raises(self):
		frappe.get_doc({"doctype": "Note", "title": OTHER_NOTE_TITLE, "public": 1}).insert()

		def boom(arguments, context):
			_insert_note()
			raise RuntimeError("boom")

		specs = [_spec("do_read", "read", handler=boom)]
		with patch.object(registry, "_all_specs", lambda: specs):
			with self.assertRaises(RuntimeError):
				execute_tool("do_read", {}, _context())
		self.assertFalse(frappe.db.exists("Note", {"title": NOTE_TITLE}))
		self.assertTrue(frappe.db.exists("Note", {"title": OTHER_NOTE_TITLE}))

	def test_successful_write_is_kept(self):
		def write(arguments, context):
			_insert_note()
			return {"ok": True}

		specs = [_spec("do_read", "read", handler=write)]
		with patch.object(registry, "_all_specs", lambda: specs):
			execute_tool("do_read", {}, _context())
		self.assertTrue(frappe.db.exists("Note", {"title": NOTE_TITLE}))

	def test_all_specs_collects_tools_of_each_module(self):
		fakes = {name: SimpleNamespace(TOOLS=[_spec(name, "read")]) for name in registry.TOOL_MODULES}
		with (
			patch.object(registry, "_all_specs", REAL_ALL_SPECS),
			patch.object(registry.importlib, "import_module", fakes.__getitem__),
		):
			self.assertEqual([s.name for s in registry._all_specs()], list(registry.TOOL_MODULES))

	def test_no_tool_schema_takes_person_sla_priority_or_score(self):
		# AC-9: the model cannot choose a person, an SLA, a priority or a score through any tool.
		specs = REAL_ALL_SPECS()
		self.assertTrue(specs)
		for spec in specs:
			for key in _schema_keys(spec.schema["input_schema"]):
				for word in FORBIDDEN_ROUTE_PARAMETER_WORDS:
					self.assertNotIn(word, key.lower(), f"{spec.name} accepts {key}")
		classification = next(s for s in specs if s.name == "set_classification")
		self.assertEqual(
			classification.schema["input_schema"]["properties"].keys(), {"category", "confidence"}
		)
		self.assertEqual(classification.schema["input_schema"]["required"], ["category", "confidence"])

	def test_route_functions_not_executable_as_tools(self):
		# AC-9: a tool call naming a route function is "not granted" and no route function runs.
		context = _context("L3", "boss@x.com")
		arguments = ({}, {"user": "Administrator"}, {"assignee": "Administrator", "priority": "Urgent"})
		with (
			patch.object(registry, "_all_specs", REAL_ALL_SPECS),
			patch.object(route_ticket, "apply_route") as apply_route,
			patch.object(route_ticket, "assign_owner") as assign_owner,
			patch.object(route_ticket, "create_routed_task") as create_routed_task,
			patch.object(route_ticket, "post_routing_comment") as post_routing_comment,
		):
			granted = [spec["name"] for spec in get_tool_schemas("L3", True, False)]
			for name in ROUTE_FUNCTION_NAMES:
				self.assertNotIn(name, granted)
				for given in arguments:
					result = execute_tool(name, given, context)
					self.assertFalse(result["ok"], name)
					self.assertIn("không được cấp", result["reason"], name)
		for function in (apply_route, assign_owner, create_routed_task, post_routing_comment):
			function.assert_not_called()

	def test_tool_context_appends_change_fields_after_routing_config(self):
		fields = [(f.name, f.default) for f in dataclasses.fields(ToolContext)]
		self.assertEqual(
			fields[6:10],
			[
				("routing_config", None),
				("change_enabled", False),
				("allowed_apps", ()),
				("unrestricted", False),
			],
		)
		# FEAT-007 T76: the grant fields come after `unrestricted`, each with a default.
		self.assertEqual(
			fields[10:],
			[
				("record_tools", False),
				("act_now", False),
				("one_click_approval", False),
				("over_budget", False),
				("main_path_level", None),
				("below_threshold", False),
			],
		)
		self.assertEqual(len(fields), 16)

	def test_grant_functions_take_change_enabled_without_default(self):
		for function in (registry._legacy_inputs, get_tool_schemas, registry.grants_change_tools):
			parameters = inspect.signature(function).parameters
			self.assertEqual(
				list(parameters),
				["effective_level", "has_instructor", "change_enabled", "unrestricted"],
				function.__name__,
			)
			self.assertIs(parameters["change_enabled"].default, inspect.Parameter.empty, function.__name__)

	def test_change_group_only_when_switch_l3_and_instructor(self):
		# AC-2 full matrix: 4 levels (+ unknown) x authority x switch; change_propose only at
		# switch on, L3 and an instructor. Each dropped condition flips one row below.
		base = ["do_read", "do_ticket"]
		with_task = ["do_read", "do_ticket", "do_task"]
		expected = {
			("L0", False, False): [],
			("L0", False, True): [],
			("L0", True, False): [],
			("L0", True, True): [],
			("L9", True, True): [],
			("L1", False, False): base,
			("L1", False, True): base,
			("L1", True, False): with_task,
			("L1", True, True): with_task,
			("L2", False, False): base,
			("L2", False, True): base,
			("L2", True, False): with_task,
			("L2", True, True): with_task,
			("L3", False, False): base,
			("L3", False, True): base,
			("L3", True, False): with_task,
			("L3", True, True): ["do_read", "do_ticket", "do_task", "do_change"],
		}
		with patch.object(registry, "_all_specs", _specs_with_change):
			for (level, has_instructor, change_enabled), names in expected.items():
				key = (level, has_instructor, change_enabled)
				schemas = get_tool_schemas(level, has_instructor, change_enabled)
				self.assertEqual([s["name"] for s in schemas], names, key)
				self.assertIs(
					registry.grants_change_tools(level, has_instructor, change_enabled),
					key == ("L3", True, True),
					key,
				)

	def test_grants_change_tools_follows_granted_specs_not_conditions(self):
		# Design 3.6, ADR-011 QĐ 3/6: with every condition met but no change_propose spec
		# registered, nothing is granted, so the prompt flag must say False too.
		schemas = get_tool_schemas("L3", True, True)
		self.assertEqual([s["name"] for s in schemas], ["do_read", "do_ticket", "do_task"])
		self.assertIs(registry.grants_change_tools("L3", True, True), False)

	def test_execute_rejects_change_tool_when_not_granted(self):
		denied = (
			_context("L3", "boss@x.com", change_enabled=False),
			_context("L3", None, change_enabled=True),
			_context("L2", "boss@x.com", change_enabled=True),
			_context("L1", "boss@x.com", change_enabled=True),
			_context("L0", "boss@x.com", change_enabled=True),
		)
		with patch.object(registry, "_all_specs", _specs_with_change):
			for context in denied:
				result = execute_tool("do_change", {}, context)
				self.assertEqual(
					result,
					{"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"},
					context,
				)
			granted = execute_tool("do_change", {}, _context("L3", "boss@x.com", change_enabled=True))
		self.assertEqual(granted, {"ok": True, "echo": {}, "ticket": "TKT-1"})


READ_TOOL_NAMES = ["get_ticket", "list_comments", "search_resolved_tickets", "get_record"]
SOURCE_TOOL_NAMES = ["search_source", "read_source", "git_source"]
TICKET_WRITE_TOOL_NAMES = ["set_classification", "set_resolution_hint", "post_comment"]
TASK_WRITE_TOOL_NAMES = ["create_task"]
CREATED_NOTE = "<note made by api_create_record>"
CHANGE_TOOL_NAMES = ["propose_file_change", "propose_new_file", "propose_bench_command"]
SANDBOX_APP = "custom_app"
SITE_ADMIN_TOOL_NAMES = ["api_list_records", "api_get_record", "api_create_record", "api_update_record"]
FORBIDDEN_WRITE_PARAMETER_WORDS = ("doctype", "field")
SCHEMA_TYPES = {"string", "integer", "boolean", "array", "object"}
# Written out by hand, not read from registry.TOOL_MODULES: module -> its tool names, in order.
TOOLS_BY_MODULE = {
	"erp_ai.agent.tools.read": ["get_ticket", "list_comments", "search_resolved_tickets", "get_record"],
	"erp_ai.agent.tools.source": ["search_source", "read_source", "git_source"],
	"erp_ai.agent.tools.write_ticket": [
		"set_classification",
		"set_resolution_hint",
		"post_comment",
		"create_task",
	],
	"erp_ai.agent.tools.propose_change": ["propose_file_change", "propose_new_file", "propose_bench_command"],
	"erp_ai.agent.tools.site_api": [
		"api_list_records",
		"api_get_record",
		"api_create_record",
		"api_update_record",
		"api_delete_record",
		"api_submit_record",
		"api_call_method",
	],
}


class TestRealToolSet(FrappeTestCase):
	"""AC-8 / NFR-6 against the real specs of read.py, source.py and write_ticket.py."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def names(self, level, has_instructor):
		return [s["name"] for s in get_tool_schemas(level, has_instructor, False)]

	def test_tool_names_per_level_and_authority(self):
		granted = READ_TOOL_NAMES + SOURCE_TOOL_NAMES + TICKET_WRITE_TOOL_NAMES
		for has_instructor in (False, True):
			self.assertEqual(self.names("L0", has_instructor), [])
		for level in ("L1", "L2", "L3"):
			self.assertEqual(self.names(level, False), granted)
			self.assertEqual(self.names(level, True), granted + TASK_WRITE_TOOL_NAMES)
		self.assertEqual(len(registry._all_specs()), 21)

	def test_tool_modules_register_exactly_the_21_tools(self):
		# Spec Amendment 2, N-3 items 18-19: 11 base + 3 propose + 4 record + 3 full-power tools.
		self.assertEqual(registry.TOOL_MODULES, tuple(TOOLS_BY_MODULE))
		self.assertNotIn("erp_ai.agent.tools.route_ticket", registry.TOOL_MODULES)
		for module_name, names in TOOLS_BY_MODULE.items():
			module = importlib.import_module(module_name)
			self.assertEqual([spec.name for spec in module.TOOLS], names, module_name)
		expected = [name for names in TOOLS_BY_MODULE.values() for name in names]
		self.assertEqual(len(expected), 21)
		self.assertEqual([spec.name for spec in registry._all_specs()], expected)

	def test_switch_on_adds_site_admin_tools_only_at_l3_with_instructor(self):
		base = READ_TOOL_NAMES + SOURCE_TOOL_NAMES + TICKET_WRITE_TOOL_NAMES
		with_task = base + TASK_WRITE_TOOL_NAMES
		expected = {
			("L1", True): with_task,
			("L2", True): with_task,
			("L3", False): base,
			("L3", True): with_task + CHANGE_TOOL_NAMES + SITE_ADMIN_TOOL_NAMES,
		}
		for (level, has_instructor), names in expected.items():
			schemas = get_tool_schemas(level, has_instructor, True)
			self.assertEqual([s["name"] for s in schemas], names, (level, has_instructor))

	def test_switch_off_tool_names_match_base_for_all_levels_and_authority(self):
		# AC-1: switch off = the exact tool names of the FEAT-006 base, written out as literals.
		base = [
			"get_ticket",
			"list_comments",
			"search_resolved_tickets",
			"get_record",
			"search_source",
			"read_source",
			"git_source",
			"set_classification",
			"set_resolution_hint",
			"post_comment",
		]
		expected = {
			("L0", False): [],
			("L0", True): [],
			("L1", False): base,
			("L1", True): [*base, "create_task"],
			("L2", False): base,
			("L2", True): [*base, "create_task"],
			("L3", False): base,
			("L3", True): [*base, "create_task"],
		}
		for (level, has_instructor), names in expected.items():
			schemas = get_tool_schemas(level, has_instructor, False)
			self.assertEqual([s["name"] for s in schemas], names, (level, has_instructor))
			self.assertFalse(
				registry.grants_change_tools(level, has_instructor, False), (level, has_instructor)
			)

	def test_no_write_tool_accepts_doctype_or_field(self):
		write_specs = [s for s in registry._all_specs() if s.group in ("ticket_write", "task_write")]
		self.assertEqual([s.name for s in write_specs], TICKET_WRITE_TOOL_NAMES + TASK_WRITE_TOOL_NAMES)
		for spec in write_specs:
			for key in spec.schema["input_schema"]["properties"]:
				for word in FORBIDDEN_WRITE_PARAMETER_WORDS:
					self.assertNotIn(word, key.lower(), f"{spec.name} accepts {key}")

	def spec(self, name):
		return next(s for s in registry._all_specs() if s.name == name)

	def test_git_source_schema_only_log_and_blame(self):
		properties = self.spec("git_source").schema["input_schema"]["properties"]
		self.assertEqual(set(properties["subcommand"]["enum"]), {"log", "blame"})
		self.assertEqual(self.spec("git_source").schema["input_schema"]["required"], ["app", "subcommand"])
		self.assertEqual(properties["args"]["maxItems"], 10)

	def test_schemas_use_only_types_the_validator_knows(self):
		def types_of(rule):
			found = {rule["type"]} if "type" in rule else set()
			if "items" in rule:
				found |= types_of(rule["items"])
			return found

		for spec in registry._all_specs():
			self.assertEqual(spec.schema["name"], spec.name)
			for key, rule in spec.schema["input_schema"]["properties"].items():
				self.assertLessEqual(types_of(rule), SCHEMA_TYPES, f"{spec.name}.{key}")

	def test_no_tool_module_commits(self):
		# Handlers run inside execute_tool's savepoint; a commit would release it.
		for module_name in registry.TOOL_MODULES:
			module = importlib.import_module(module_name)
			self.assertNotIn(".commit(", inspect.getsource(module), module_name)

	def test_git_source_enum_comes_from_git_subcommands(self):
		self.assertEqual(
			self.spec("git_source").schema["input_schema"]["properties"]["subcommand"]["enum"],
			sorted(GIT_SUBCOMMANDS),
		)


class TestRealToolsRunWithoutCommit(FrappeTestCase):
	"""Every real handler really runs inside execute_tool on a seeded ticket while commit is forbidden."""

	def setUp(self):
		# Registered first so it is undone last: the rollback cleanup runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in tool test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		self.assertTrue(frappe.db.exists("User", AGENT_EMAIL))
		frappe.get_doc("User", AGENT_EMAIL).add_roles(ROLE_AGENT)
		self.assertFalse(frappe.db.exists("HD Ticket Type", SEED_TYPE))
		frappe.get_doc({"doctype": "HD Ticket Type", "name": SEED_TYPE}).insert()
		self.ticket = make_ticket(subject="ERPAI-TEST-T27 phiếu", raised_by=AGENT_EMAIL).name
		# Every source and file tool reads the temp repos only; the file tools may edit SANDBOX_APP.
		sandbox = GitSandbox(self, apps=("erp_ai", SANDBOX_APP), erp_ai_worktree=None)
		sandbox.commit_file("erp_ai", "erp_ai/agent/tools/registry.py", "class ToolSpec:\n\tpass\n")

	def arguments(self):
		return {
			"get_ticket": {"name": self.ticket},
			"list_comments": {"ticket": self.ticket},
			"search_resolved_tickets": {"query": "ERPAI-TEST"},
			"get_record": {"doctype": "HD Ticket", "name": self.ticket},
			"search_source": {"pattern": "ToolSpec", "app": "erp_ai"},
			"read_source": {"path": "erp_ai/erp_ai/agent/tools/registry.py", "limit": 5},
			"git_source": {"app": "erp_ai", "subcommand": "log", "args": ["--oneline", "-n", "1"]},
			"set_classification": {"category": "A", "confidence": "Cao"},
			"set_resolution_hint": {"text": "ERPAI-TEST-T27 gợi ý"},
			"post_comment": {"content": "ERPAI-TEST-T27 bình luận"},
			"create_task": {"subject": "ERPAI-TEST-T27 việc", "description": "ERPAI-TEST-T27 mô tả"},
			"propose_file_change": {
				"path": f"{SANDBOX_APP}/README.md",
				"find": ["# "],
				"replace": ["## "],
				"reason": "ERPAI-TEST-T27",
			},
			"propose_new_file": {"path": f"{SANDBOX_APP}/t27.md", "content": "x", "reason": "ERPAI-TEST-T27"},
			"propose_bench_command": {"command": "version", "reason": "ERPAI-TEST-T27"},
			"api_list_records": {"doctype": "HD Ticket", "filters": [["name", "=", str(self.ticket)]]},
			"api_get_record": {"doctype": "HD Ticket", "name": str(self.ticket)},
			"api_create_record": {"doctype": "Note", "values": {"title": "ERPAI-TEST-T27 ghi chú"}},
			"api_update_record": {
				"doctype": "HD Ticket",
				"name": str(self.ticket),
				"values": {"subject": "ERPAI-TEST-T27 phiếu đã sửa"},
			},
			"api_delete_record": {"doctype": "Note", "name": CREATED_NOTE},
			"api_submit_record": {"doctype": "Note", "name": CREATED_NOTE, "action": "submit"},
			"api_call_method": {"method": "frappe.client.get_count", "arguments": {"doctype": "HD Ticket"}},
		}

	def test_every_real_handler_runs_without_committing(self):
		context = ToolContext(
			ticket_name=self.ticket,
			effective_level="L3",
			instructor=AGENT_EMAIL,
			run_id="run-t27",
			category_mapping={"A": {"ticket_type": SEED_TYPE}},
			agent_user=AGENT_EMAIL,
			change_enabled=True,
			allowed_apps=(SANDBOX_APP,),
			unrestricted=True,
		)
		arguments = self.arguments()
		specs = REAL_ALL_SPECS()
		self.assertEqual(sorted(arguments), sorted(spec.name for spec in specs))
		frappe.set_user(AGENT_EMAIL)
		results = {}
		for spec in specs:
			call_arguments = dict(arguments[spec.name])
			if call_arguments.get("name") == CREATED_NOTE:
				call_arguments["name"] = results["api_create_record"]["name"]
			results[spec.name] = execute_tool(spec.name, call_arguments, context)
		# The note is deleted before the submit call, so that handler ends at its own "missing record" refusal.
		self.assertEqual(results.pop("api_submit_record")["reason"], "không tìm thấy bản ghi")
		for name, result in results.items():
			# ok means the handler ran to its end: not a schema refusal, not "not granted", not a handler refusal.
			self.assertTrue(result["ok"], f"{name}: {result}")
		frappe.set_user("Administrator")
		ticket = frappe.get_doc("HD Ticket", self.ticket)
		self.assertEqual(ticket.ticket_type, SEED_TYPE)
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_name": self.ticket, "content": ["like", "%ERPAI-TEST-T27%"]}
			)
		)
		self.assertTrue(frappe.db.exists("Task", {"subject": "ERPAI-TEST-T27 việc"}))
		self.assertFalse(frappe.db.exists("Note", {"title": "ERPAI-TEST-T27 ghi chú"}))
		self.assertEqual(ticket.subject, "ERPAI-TEST-T27 phiếu đã sửa")
		for name in ("propose_file_change", "propose_new_file"):
			self.assertTrue(frappe.db.exists(PROPOSAL_DOCTYPE, results[name]["proposal"]), name)


# Snapshot of the grant at 6d90e79, written by hand from the old two-function code
# (get_tool_schemas + get_unrestricted_tool_schemas, as the runner merged them) before M4.
SNAPSHOT_BASE = [
	"get_ticket",
	"list_comments",
	"search_resolved_tickets",
	"get_record",
	"search_source",
	"read_source",
	"git_source",
	"set_classification",
	"set_resolution_hint",
	"post_comment",
]
SNAPSHOT_WITH_TASK = [*SNAPSHOT_BASE, "create_task"]
SNAPSHOT_RECORD = ["api_list_records", "api_get_record", "api_create_record", "api_update_record"]
SNAPSHOT_FULL_POWER = ["api_delete_record", "api_submit_record", "api_call_method"]
SNAPSHOT_PROPOSE = ["propose_file_change", "propose_new_file", "propose_bench_command"]
# (change_enabled, unrestricted, level, has_instructor) -> granted tool names, in order.
GRANT_SNAPSHOT = {
	(False, False, "L0", False): [],
	(False, False, "L0", True): [],
	(False, False, "L1", False): SNAPSHOT_BASE,
	(False, False, "L1", True): SNAPSHOT_WITH_TASK,
	(False, False, "L2", False): SNAPSHOT_BASE,
	(False, False, "L2", True): SNAPSHOT_WITH_TASK,
	(False, False, "L3", False): SNAPSHOT_BASE,
	(False, False, "L3", True): SNAPSHOT_WITH_TASK,
	(False, True, "L0", False): [],
	(False, True, "L0", True): [],
	(False, True, "L1", False): SNAPSHOT_BASE,
	(False, True, "L1", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
	(False, True, "L2", False): SNAPSHOT_BASE,
	(False, True, "L2", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
	(False, True, "L3", False): SNAPSHOT_BASE,
	(False, True, "L3", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
	(True, False, "L0", False): [],
	(True, False, "L0", True): [],
	(True, False, "L1", False): SNAPSHOT_BASE,
	(True, False, "L1", True): SNAPSHOT_WITH_TASK,
	(True, False, "L2", False): SNAPSHOT_BASE,
	(True, False, "L2", True): SNAPSHOT_WITH_TASK,
	(True, False, "L3", False): SNAPSHOT_BASE,
	(True, False, "L3", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_PROPOSE, *SNAPSHOT_RECORD],
	(True, True, "L0", False): [],
	(True, True, "L0", True): [],
	(True, True, "L1", False): SNAPSHOT_BASE,
	(True, True, "L1", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
	(True, True, "L2", False): SNAPSHOT_BASE,
	(True, True, "L2", True): [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
	(True, True, "L3", False): SNAPSHOT_BASE,
	(True, True, "L3", True): [
		*SNAPSHOT_WITH_TASK,
		*SNAPSHOT_PROPOSE,
		*SNAPSHOT_RECORD,
		*SNAPSHOT_FULL_POWER,
	],
}
NOT_GRANTED = {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}


class TestGrantTable(FrappeTestCase):
	"""M4 (ADR-023 QĐ 4): one grant function, one GRANT_TABLE, `unrestricted` is its fourth input."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_grant_matrix_matches_snapshot(self):
		# AC-1, AC-2 (a/b/c): 2 switches x 2 x 4 levels x instructor = 32 rows, all written out above.
		# FEAT-007 T76 (U1.md:396): the same 32 rows through grant(GrantInputs) with (2) := (4), (3) = 1,
		# (5) = 1, not over budget, not below threshold, main-path level = permission level.
		self.assertEqual(len(GRANT_SNAPSHOT), 32)
		for key, names in GRANT_SNAPSHOT.items():
			change_enabled, unrestricted, level, has_instructor = key
			legacy = (level, has_instructor, change_enabled, unrestricted)
			switches = PermissionSwitches(
				unrestricted=unrestricted,
				record_tools=change_enabled,
				act_now=True,
				code_change=change_enabled,
				one_click_approval=True,
			)
			with self.subTest(key):
				granted = registry.grant(registry.GrantInputs(level, level, has_instructor, switches))
				self.assertEqual([s.name for s in granted.specs], names)
				self.assertEqual([s["name"] for s in granted.schemas()], names)
				self.assertEqual(granted.names(), frozenset(names))
				self.assertIs(granted.change_block, "propose_file_change" in names)
				# FEAT-007 T77 (U1.md:396): the four block flags; the full-power block replaces the record one.
				self.assertIs(
					granted.record_block, "api_list_records" in names and "api_delete_record" not in names
				)
				self.assertIs(granted.unrestricted_block, "api_delete_record" in names)
				self.assertIs(
					granted.act_now_block,
					any(
						name in names
						for name in ("propose_file_change", "api_list_records", "api_delete_record")
					),
				)
				self.assertIs(granted.ask_only_block, False)
				self.assertEqual([s["name"] for s in get_tool_schemas(*legacy)], names)
				self.assertIs(registry.grants_change_tools(*legacy), "propose_file_change" in names)
				self.assertIs(registry.grants_site_admin_tools(*legacy), "api_list_records" in names)
				self.assertIs(registry.grants_unrestricted_tools(*legacy), "api_delete_record" in names)

	def test_unknown_level_grants_like_l0(self):
		for change_enabled in (False, True):
			for unrestricted in (False, True):
				for has_instructor in (False, True):
					grant = ("LX", has_instructor, change_enabled, unrestricted)
					with self.subTest(grant):
						self.assertEqual(get_tool_schemas(*grant), [])
						self.assertIs(registry.grants_site_admin_tools(*grant), False)
						self.assertIs(registry.grants_unrestricted_tools(*grant), False)

	def test_registry_has_one_grant_function_and_one_table(self):
		for name in (
			"_unrestricted_specs",
			"get_unrestricted_tool_schemas",
			"UNRESTRICTED_GROUPS",
			"_granted_specs",
		):
			self.assertFalse(hasattr(registry, name), name)
		self.assertEqual(
			[group for group, _condition in registry.GRANT_TABLE],
			["read", "ticket_write", "task_write", "change_propose", "site_admin", "site_unrestricted"],
		)

	def test_execute_asks_the_one_grant_function(self):
		# The context is chosen so context.grant_inputs() differs from the four-argument builder.
		context = dataclasses.replace(
			_context("L2", "boss@x.com", unrestricted=True),
			record_tools=True,
			act_now=True,
			main_path_level="L1",
		)
		self.assertNotEqual(context.grant_inputs(), registry._legacy_inputs("L2", True, False, True))
		with patch.object(registry, "grant", wraps=registry.grant) as granted:
			execute_tool("get_ticket", {"name": "x"}, context)
		granted.assert_called_once_with(context.grant_inputs())

	def test_execute_grants_by_the_context_fields_not_the_legacy_switches(self):
		# (2) on with (4) off still runs the record tools; the main-path level alone closes task tools.
		records_only = dataclasses.replace(_context("L3", "boss@x.com"), record_tools=True)
		self.assertNotEqual(execute_tool("api_list_records", {"doctype": "Note"}, records_only), NOT_GRANTED)
		main_path_l0 = dataclasses.replace(_context("L3", "boss@x.com"), main_path_level="L0")
		self.assertEqual(execute_tool("create_task", {}, main_path_l0), NOT_GRANTED)

	def test_execute_denies_with_the_same_reason_when_grant_is_empty(self):
		# The refusal text is unchanged: a tool missing from grant(...).specs is "not granted", the
		# handler never runs, even for a read tool at a granted level.
		context = _context("L3", "boss@x.com", change_enabled=True, unrestricted=True)
		with patch.object(registry, "grant", return_value=registry.Grant(specs=())):
			self.assertEqual(execute_tool("get_ticket", {"name": "x"}, context), NOT_GRANTED)

	def test_execute_rejects_delete_record_when_not_granted(self):
		arguments = {"doctype": "Note", "name": "ERPAI-TEST-T63 không có"}
		denied = {
			"switch on, L3, instructor, no full power": _context("L3", "boss@x.com", change_enabled=True),
			"full power without instructor": _context("L3", None, unrestricted=True),
			"full power at L0": _context("L0", "boss@x.com", unrestricted=True),
			"full power at an unknown level": _context("LX", "boss@x.com", unrestricted=True),
			"everything off": _context("L1", "boss@x.com"),
		}
		for case, context in denied.items():
			with self.subTest(case):
				self.assertEqual(execute_tool("api_delete_record", arguments, context), NOT_GRANTED)
		granted = execute_tool(
			"api_delete_record", arguments, _context("L1", "boss@x.com", unrestricted=True)
		)
		self.assertNotEqual(granted, NOT_GRANTED)

	def test_unrestricted_enabled_defaults_to_zero_and_only_system_manager_can_set(self):
		# AC-32: the switch is a Check that starts off; only System Manager may write the Setting.
		meta = frappe.get_meta("ERP AI Setting")
		field = meta.get_field("unrestricted_enabled")
		self.assertEqual((field.fieldtype, field.default, field.permlevel), ("Check", "0", 0))
		writers = {perm.role for perm in meta.permissions if perm.write}
		self.assertEqual(writers, {"System Manager"})


def _inputs(level="L3", has_instructor=True, main_path_level=None, **switches):
	main_path = level if main_path_level is None else main_path_level
	return registry.GrantInputs(level, main_path, has_instructor, PermissionSwitches(**switches))


def _granted_names(inputs):
	return [spec.name for spec in registry.grant(inputs).specs]


class TestGrantInputs(FrappeTestCase):
	"""FEAT-007 T76 (U1.md:166): ToolContext builds the one GrantInputs that execute_tool hands to grant."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_grant_inputs_maps_context_fields(self):
		base = _context("L3", "boss@x.com")
		self.assertEqual(
			base.grant_inputs(), registry.GrantInputs("L3", "L3", True, PermissionSwitches(), False, False)
		)
		for main_path_level, expected in ((None, "L3"), ("L1", "L1"), ("L0", "L0")):
			context = dataclasses.replace(base, main_path_level=main_path_level)
			self.assertEqual(context.grant_inputs().main_path_level, expected, main_path_level)
			self.assertEqual(context.grant_inputs().effective_level, "L3", main_path_level)
		for instructor, expected in ((None, False), ("", False), ("boss@x.com", True)):
			context = dataclasses.replace(base, instructor=instructor)
			self.assertIs(context.grant_inputs().has_instructor, expected, instructor)
		# One context field on at a time -> exactly the switch it feeds ((4) also feeds (2), the bridge).
		switch_of_field = {
			"unrestricted": {"unrestricted": True},
			"record_tools": {"record_tools": True},
			"act_now": {"act_now": True},
			"change_enabled": {"code_change": True, "record_tools": True},
			"one_click_approval": {"one_click_approval": True},
		}
		for field, switches in switch_of_field.items():
			context = dataclasses.replace(base, **{field: True})
			self.assertEqual(context.grant_inputs().switches, PermissionSwitches(**switches), field)
		for over_budget in (False, True):
			for below_threshold in (False, True):
				context = dataclasses.replace(base, over_budget=over_budget, below_threshold=below_threshold)
				inputs = context.grant_inputs()
				self.assertEqual(
					(inputs.over_budget, inputs.below_threshold),
					(over_budget, below_threshold),
					(over_budget, below_threshold),
				)

	def test_bridge_change_switch_still_brings_record_tools(self):
		# Design w1-fixes-3 Điểm 1: (2) = record_tools or change_enabled until T82.
		cases = {(True, False): True, (False, True): True, (True, True): True, (False, False): False}
		for (change_enabled, record_tools), expected in cases.items():
			context = dataclasses.replace(
				_context("L3", "boss@x.com"), change_enabled=change_enabled, record_tools=record_tools
			)
			switches = context.grant_inputs().switches
			self.assertIs(switches.record_tools, expected, (change_enabled, record_tools))
			self.assertIs(switches.code_change, change_enabled, (change_enabled, record_tools))
		# The bridge keeps the record tools runnable where only change_enabled is set (runner, test_site_api).
		bridged = _context("L3", "boss@x.com", change_enabled=True)
		self.assertNotEqual(execute_tool("api_list_records", {"doctype": "Note"}, bridged), NOT_GRANTED)
		closed = _context("L3", "boss@x.com")
		self.assertEqual(execute_tool("api_list_records", {"doctype": "Note"}, closed), NOT_GRANTED)


class TestGrantFeat007(FrappeTestCase):
	"""FEAT-007 T76, T77: the grant table and flags of grant(GrantInputs), called directly, real specs."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def test_each_switch_alone_adds_only_its_declared_set(self):
		# AC-3: (1) -> record + full-power tools above L0; (2) -> record tools at L3; (3) -> none;
		# (4) -> the three propose tools at L3; (5) -> none; all off = the base.
		rows = {
			"all off": ({}, SNAPSHOT_WITH_TASK),
			"(1) unrestricted": (
				{"unrestricted": True},
				[*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
			),
			"(2) record_tools": ({"record_tools": True}, [*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD]),
			"(3) act_now": ({"act_now": True}, SNAPSHOT_WITH_TASK),
			"(4) code_change": ({"code_change": True}, [*SNAPSHOT_WITH_TASK, *SNAPSHOT_PROPOSE]),
			"(5) one_click_approval": ({"one_click_approval": True}, SNAPSHOT_WITH_TASK),
		}
		for case, (switches, names) in rows.items():
			with self.subTest(case):
				self.assertEqual(_granted_names(_inputs("L3", True, **switches)), names)
		for level in ("L1", "L2"):
			with self.subTest(f"(1) at {level}"):
				self.assertEqual(
					_granted_names(_inputs(level, True, unrestricted=True)),
					[*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
				)

	def test_declared_sets_need_level_and_instructor(self):
		# AC-3 edges: (2), (4) below L3 -> nothing extra; no instructor -> nothing extra and no task tool;
		# L0 or an unknown level -> empty with every flag off; main-path L0 -> no task tool.
		for level in ("L1", "L2"):
			for switch in ("record_tools", "code_change"):
				with self.subTest((level, switch)):
					self.assertEqual(
						_granted_names(_inputs(level, True, **{switch: True})), SNAPSHOT_WITH_TASK
					)
		for switch in ("unrestricted", "record_tools", "code_change"):
			with self.subTest(("no instructor", switch)):
				self.assertEqual(_granted_names(_inputs("L3", False, **{switch: True})), SNAPSHOT_BASE)
		every_switch = dict.fromkeys(
			("unrestricted", "record_tools", "act_now", "code_change", "one_click_approval"), True
		)
		for level in ("L0", "LX"):
			for has_instructor in (False, True):
				with self.subTest((level, has_instructor)):
					granted = registry.grant(_inputs(level, has_instructor, **every_switch))
					self.assertEqual(granted, registry.Grant(specs=()))
		with self.subTest("main-path L0"):
			self.assertEqual(_granted_names(_inputs("L3", True, main_path_level="L0")), SNAPSHOT_BASE)

	def test_act_now_block_needs_a_power_group(self):
		# AC-6 (U1.md:186): (3) shows the act-now block only next to a granted change, record or
		# full-power group; no other group and no other switch turns it on.
		cases = {
			"(3) alone at L3": (_inputs("L3", True, act_now=True), False),
			"(3)+(5) at L3": (_inputs("L3", True, act_now=True, one_click_approval=True), False),
			"(3)+(2) at L3": (_inputs("L3", True, act_now=True, record_tools=True), True),
			"(3)+(4) at L3": (_inputs("L3", True, act_now=True, code_change=True), True),
			"(3)+(1) at L1": (_inputs("L1", True, act_now=True, unrestricted=True), True),
			"(3)+(2)+(4) at L2, groups closed": (
				_inputs("L2", True, act_now=True, record_tools=True, code_change=True),
				False,
			),
			"(3)+(1) without instructor": (_inputs("L3", False, act_now=True, unrestricted=True), False),
			"(1)+(2)+(4) with (3) off": (
				_inputs("L3", True, unrestricted=True, record_tools=True, code_change=True),
				False,
			),
		}
		for case, (inputs, expected) in cases.items():
			with self.subTest(case):
				self.assertIs(registry.grant(inputs).act_now_block, expected)

	def test_record_on_act_now_off_grants_record_tools_without_act_now_block(self):
		# AC-6 extra case: (2) on, (3) off -> the record tools and their block, no act-now block.
		granted = registry.grant(_inputs("L3", True, record_tools=True))
		self.assertEqual(granted.names(), frozenset([*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD]))
		self.assertEqual(
			(
				granted.record_block,
				granted.act_now_block,
				granted.change_block,
				granted.unrestricted_block,
				granted.ask_only_block,
			),
			(True, False, False, False, False),
		)

	def test_record_block_hidden_when_unrestricted_granted(self):
		# U1.md:185: the full-power block replaces the record block while site_admin stays granted.
		both = registry.grant(_inputs("L3", True, unrestricted=True, record_tools=True))
		self.assertTrue(set(SNAPSHOT_RECORD) <= both.names())
		self.assertEqual((both.unrestricted_block, both.record_block), (True, False))
		# Over budget closes full power only: the record tools of (2) stay, and so does their block.
		over_budget = registry.grant(
			dataclasses.replace(_inputs("L3", True, unrestricted=True, record_tools=True), over_budget=True)
		)
		self.assertEqual(over_budget.names(), frozenset([*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD]))
		self.assertEqual((over_budget.unrestricted_block, over_budget.record_block), (False, True))

	def test_over_budget_with_all_switches_equals_l1_all_off(self):
		# AC-7: the level is already cut to L1; with all five on and over budget, the tool set is the
		# L1 set with all five off, with no full-power group and every flag off.
		every_switch = dict.fromkeys(
			("unrestricted", "record_tools", "act_now", "code_change", "one_click_approval"), True
		)
		for has_instructor in (False, True):
			with self.subTest(has_instructor=has_instructor):
				all_off = registry.grant(_inputs("L1", has_instructor))
				granted = registry.grant(
					dataclasses.replace(_inputs("L1", has_instructor, **every_switch), over_budget=True)
				)
				self.assertEqual(granted, all_off)
				self.assertNotIn("api_delete_record", granted.names())
		self.assertEqual(
			_granted_names(dataclasses.replace(_inputs("L1", True, **every_switch), over_budget=True)),
			SNAPSHOT_WITH_TASK,
		)

	def test_below_threshold_grants_read_and_ask_tool_only(self):
		# AC-22: below the threshold, all five on, L3, an instructor -> read + post_comment only, in the
		# _all_specs() order; only the ask-only block.
		every_switch = dict.fromkeys(
			("unrestricted", "record_tools", "act_now", "code_change", "one_click_approval"), True
		)
		self.assertEqual(ASK_TOOL_NAMES, frozenset({"post_comment"}))
		read_names = [*READ_TOOL_NAMES, *SOURCE_TOOL_NAMES]
		below = dataclasses.replace(_inputs("L3", True, **every_switch), below_threshold=True)
		granted = registry.grant(below)
		self.assertEqual([spec.name for spec in granted.specs], [*read_names, "post_comment"])
		self.assertEqual(
			(
				granted.ask_only_block,
				granted.change_block,
				granted.record_block,
				granted.unrestricted_block,
				granted.act_now_block,
			),
			(True, False, False, False, False),
		)
		with self.subTest("all switches off, no instructor"):
			plain = registry.grant(dataclasses.replace(_inputs("L1", False), below_threshold=True))
			self.assertEqual([spec.name for spec in plain.specs], [*read_names, "post_comment"])
			self.assertIs(plain.ask_only_block, True)
		with self.subTest("not below the threshold"):
			self.assertIs(registry.grant(_inputs("L3", True, **every_switch)).ask_only_block, False)
		with self.subTest("L0 stays empty"):
			at_l0 = registry.grant(dataclasses.replace(_inputs("L0", True), below_threshold=True))
			self.assertEqual(at_l0, registry.Grant(specs=()))
		with self.subTest("the added ticket_write specs follow ASK_TOOL_NAMES"):
			with patch.object(registry, "ASK_TOOL_NAMES", frozenset({"set_resolution_hint"})):
				self.assertEqual(_granted_names(below), [*read_names, "set_resolution_hint"])

	def test_category_c_cap_keeps_code_tools_at_l3(self):
		# AC-31: the category cap lowers only the main path; the permission level keeps (4) at L3.
		names = _granted_names(_inputs("L3", True, main_path_level="L1", code_change=True))
		self.assertEqual(names, [*SNAPSHOT_WITH_TASK, *SNAPSHOT_PROPOSE])
		self.assertEqual(
			_granted_names(_inputs("L1", True, main_path_level="L1", code_change=True)), SNAPSHOT_WITH_TASK
		)

	def test_l1_main_path_has_no_erp_write_tools(self):
		# AC-32: at L1 with full power off, no record, full-power or propose tool even with (2)-(5) on;
		# create_task only with an instructor.
		switches = dict.fromkeys(("record_tools", "act_now", "code_change", "one_click_approval"), True)
		for has_instructor, expected in ((True, SNAPSHOT_WITH_TASK), (False, SNAPSHOT_BASE)):
			with self.subTest(has_instructor=has_instructor):
				granted = registry.grant(_inputs("L1", has_instructor, **switches))
				self.assertEqual([spec.name for spec in granted.specs], expected)
				self.assertEqual(
					(granted.change_block, granted.record_block, granted.unrestricted_block), (False,) * 3
				)

	def test_unrestricted_at_l1_not_over_budget_is_granted(self):
		# AC-32: full power stays above L0, so at L1 too, unless over budget.
		inputs = _inputs("L1", True, unrestricted=True)
		granted = registry.grant(inputs)
		self.assertEqual(
			[spec.name for spec in granted.specs],
			[*SNAPSHOT_WITH_TASK, *SNAPSHOT_RECORD, *SNAPSHOT_FULL_POWER],
		)
		self.assertIs(granted.unrestricted_block, True)
		over_budget = registry.grant(dataclasses.replace(inputs, over_budget=True))
		self.assertEqual([spec.name for spec in over_budget.specs], SNAPSHOT_WITH_TASK)
		self.assertIs(over_budget.unrestricted_block, False)
