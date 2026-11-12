import importlib
import inspect
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.tools import registry, route_ticket
from erp_ai.agent.tools.registry import ToolContext, ToolSpec, execute_tool, get_tool_schemas
from erp_ai.agent.tools.source import GIT_SUBCOMMANDS
from erp_ai.constants import ROLE_AGENT

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


def _context(level="L1", instructor=None):
	return ToolContext(
		ticket_name="TKT-1",
		effective_level=level,
		instructor=instructor,
		run_id="run-1",
		category_mapping={},
		agent_user="ai.agent@miyano.com.vn",
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
		return [s["name"] for s in get_tool_schemas(level, has_instructor)]

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
		first = get_tool_schemas("L1", False)
		first[0]["cache_control"] = {"type": "ephemeral"}
		first[0]["input_schema"]["properties"].clear()
		second = get_tool_schemas("L1", False)
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
			granted = [spec["name"] for spec in get_tool_schemas("L3", True)]
			for name in ROUTE_FUNCTION_NAMES:
				self.assertNotIn(name, granted)
				for given in arguments:
					result = execute_tool(name, given, context)
					self.assertFalse(result["ok"], name)
					self.assertIn("không được cấp", result["reason"], name)
		for function in (apply_route, assign_owner, create_routed_task, post_routing_comment):
			function.assert_not_called()


READ_TOOL_NAMES = ["get_ticket", "list_comments", "search_resolved_tickets", "get_record"]
SOURCE_TOOL_NAMES = ["search_source", "read_source", "git_source"]
TICKET_WRITE_TOOL_NAMES = ["set_classification", "set_resolution_hint", "post_comment"]
TASK_WRITE_TOOL_NAMES = ["create_task"]
FORBIDDEN_WRITE_PARAMETER_WORDS = ("doctype", "field")
SCHEMA_TYPES = {"string", "integer", "boolean", "array"}


class TestRealToolSet(FrappeTestCase):
	"""AC-8 / NFR-6 against the real specs of read.py, source.py and write_ticket.py."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)

	def names(self, level, has_instructor):
		return [s["name"] for s in get_tool_schemas(level, has_instructor)]

	def test_tool_names_per_level_and_authority(self):
		granted = READ_TOOL_NAMES + SOURCE_TOOL_NAMES + TICKET_WRITE_TOOL_NAMES
		for has_instructor in (False, True):
			self.assertEqual(self.names("L0", has_instructor), [])
		for level in ("L1", "L2", "L3"):
			self.assertEqual(self.names(level, False), granted)
			self.assertEqual(self.names(level, True), granted + TASK_WRITE_TOOL_NAMES)
		self.assertEqual(len(registry._all_specs()), 11)

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
		}

	def test_every_real_handler_runs_without_committing(self):
		context = ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=AGENT_EMAIL,
			run_id="run-t27",
			category_mapping={"A": {"ticket_type": SEED_TYPE}},
			agent_user=AGENT_EMAIL,
		)
		arguments = self.arguments()
		specs = REAL_ALL_SPECS()
		self.assertEqual(sorted(arguments), sorted(spec.name for spec in specs))
		frappe.set_user(AGENT_EMAIL)
		for spec in specs:
			result = execute_tool(spec.name, arguments[spec.name], context)
			# ok means the handler ran to its end: not a schema refusal, not "not granted", not a handler refusal.
			self.assertTrue(result["ok"], f"{spec.name}: {result}")
		frappe.set_user("Administrator")
		ticket = frappe.get_doc("HD Ticket", self.ticket)
		self.assertEqual(ticket.ticket_type, SEED_TYPE)
		self.assertTrue(
			frappe.db.exists(
				"Comment", {"reference_name": self.ticket, "content": ["like", "%ERPAI-TEST-T27%"]}
			)
		)
		self.assertTrue(frappe.db.exists("Task", {"subject": "ERPAI-TEST-T27 việc"}))
