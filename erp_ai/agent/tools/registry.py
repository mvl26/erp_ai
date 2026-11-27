import copy
import importlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal

import frappe

from erp_ai.agent.policy import PermissionSwitches
from erp_ai.constants import LEVELS


@dataclass(frozen=True)
class GrantInputs:
	effective_level: str
	main_path_level: str
	has_instructor: bool
	switches: PermissionSwitches
	over_budget: bool = False
	below_threshold: bool = False
	reply_enabled: bool = False
	kb_draft_run: bool = False


@dataclass(frozen=True)
class ToolContext:
	ticket_name: str
	effective_level: str
	instructor: str | None
	run_id: str
	category_mapping: dict
	agent_user: str
	routing_config: dict | None = None
	change_enabled: bool = False
	allowed_apps: tuple[str, ...] = ()
	unrestricted: bool = False
	record_tools: bool = False
	act_now: bool = False
	one_click_approval: bool = False
	over_budget: bool = False
	main_path_level: str | None = None
	below_threshold: bool = False
	reply_enabled: bool = False
	kb_draft_run: bool = False
	console: bool = False
	# True when a message of the ticket's conversation started the run: when the guidance comment takes the run's
	# answer, the run still answers there (CHG-003 Amendment 3).
	in_conversation: bool = False
	server_script_read: bool = False  # 2026-11-27: the read-only Server Script tools

	def grant_inputs(self) -> GrantInputs:
		switches = PermissionSwitches(
			unrestricted=self.unrestricted,
			record_tools=self.record_tools,
			act_now=self.act_now,
			code_change=self.change_enabled,
			one_click_approval=self.one_click_approval,
			console=self.console,
			server_script_read=self.server_script_read,
		)
		return GrantInputs(
			effective_level=self.effective_level,
			main_path_level=self.effective_level if self.main_path_level is None else self.main_path_level,
			has_instructor=bool(self.instructor),
			switches=switches,
			over_budget=self.over_budget,
			below_threshold=self.below_threshold,
			reply_enabled=self.reply_enabled,
			kb_draft_run=self.kb_draft_run,
		)


@dataclass(frozen=True)
class ToolSpec:
	name: str
	group: Literal[
		"read",
		"ticket_write",
		"task_write",
		"change_propose",
		"site_admin",
		"site_unrestricted",
		"requester_reply",
		"kb_draft",
		"console_propose",
		"script_read",
	]
	schema: dict
	handler: Callable[[dict, ToolContext], dict]


@dataclass(frozen=True)
class Grant:
	specs: tuple[ToolSpec, ...]
	change_block: bool = False
	record_block: bool = False
	unrestricted_block: bool = False
	act_now_block: bool = False
	ask_only_block: bool = False
	reply_block: bool = False
	console_block: bool = False

	def schemas(self) -> list[dict]:
		return [copy.deepcopy(spec.schema) for spec in self.specs]

	def names(self) -> frozenset[str]:
		return frozenset(spec.name for spec in self.specs)


TOOL_MODULES = (
	"erp_ai.agent.tools.read",
	"erp_ai.agent.tools.source",
	"erp_ai.agent.tools.write_ticket",
	"erp_ai.agent.tools.propose_change",
	"erp_ai.agent.tools.site_api",
	"erp_ai.agent.tools.knowledge_read",
	"erp_ai.agent.tools.reply",
	"erp_ai.agent.tools.kb_draft",
	"erp_ai.agent.tools.script_read",
)
SAVEPOINT = "erp_ai_tool"
# MariaDB ER_SP_DOES_NOT_EXIST: a COMMIT inside a tool (Frappe's own in `updatedb` when a Custom Field is saved, a
# controller's commit) dropped every savepoint and kept every write before it (ADR-024 QĐ 5).
SAVEPOINT_GONE = 1305
KEY_REASON_MAX = 100  # model-supplied argument names are cut so reason stays short
CHANGE_GROUP = "change_propose"
SITE_ADMIN_GROUP = "site_admin"
UNRESTRICTED_GROUP = "site_unrestricted"
REPLY_GROUP = "requester_reply"
KB_DRAFT_GROUP = "kb_draft"
CONSOLE_GROUP = "console_propose"
SCRIPT_READ_GROUP = "script_read"
# The only tools left below the confidence threshold, each while its group is granted above it (U1.md:158,
# U6b-fixes Sửa 12).
ASK_TOOL_NAMES = frozenset({"post_comment", "reply_to_requester"})


def unrestricted_granted(inputs: GrantInputs) -> bool:
	# The full-power switch: any level above L0, with an instructor, never over budget, below threshold or in a
	# KB-draft run.
	return (
		inputs.switches.unrestricted
		and inputs.effective_level in LEVELS[1:]
		and inputs.has_instructor
		and not inputs.over_budget
		and not inputs.below_threshold
		and not inputs.kb_draft_run
	)


# ADR-011 QĐ 2, 6, ADR-023 QĐ 4, ADR-030 QĐ 3 and ADR-033 QĐ 3: the only grant table, one row per group, checked
# above L0: (group, Callable[[GrantInputs], bool]). A KB-draft run is a fixed row: `read` and `kb_draft` only.
GRANT_TABLE = (
	("read", lambda inputs: True),
	("ticket_write", lambda inputs: not inputs.below_threshold and not inputs.kb_draft_run),
	(
		"task_write",
		lambda inputs: inputs.has_instructor
		and inputs.main_path_level in LEVELS[1:]
		and not inputs.below_threshold
		and not inputs.kb_draft_run,
	),
	(
		CHANGE_GROUP,
		lambda inputs: inputs.switches.code_change
		and inputs.effective_level == "L3"
		and inputs.has_instructor
		and not inputs.below_threshold
		and not inputs.kb_draft_run,
	),
	# CHG-010: the console switch alone (not code_change): L3, an instructor, above the threshold, no KB-draft run.
	(
		CONSOLE_GROUP,
		lambda inputs: inputs.switches.console
		and inputs.effective_level == "L3"
		and inputs.has_instructor
		and not inputs.below_threshold
		and not inputs.kb_draft_run,
	),
	# Generic record tools (site_api.py): the record-tools switch, level and authority, or full power.
	(
		SITE_ADMIN_GROUP,
		lambda inputs: (
			(inputs.switches.record_tools and inputs.effective_level == "L3" and inputs.has_instructor)
			or unrestricted_granted(inputs)
		)
		and not inputs.below_threshold
		and not inputs.kb_draft_run,
	),
	(UNRESTRICTED_GROUP, unrestricted_granted),
	(
		REPLY_GROUP,
		lambda inputs: inputs.reply_enabled and not inputs.kb_draft_run and not inputs.below_threshold,
	),
	(KB_DRAFT_GROUP, lambda inputs: inputs.kb_draft_run),
	# 2026-11-27: read only, so like `read` it needs no instructor and stays over budget; its own switch. Not below the
	# threshold: that run only asks one question (ASK_ONLY_BLOCK) and keeps the read group and the ask tools; never in
	# a KB-draft run (that row is fixed).
	(
		SCRIPT_READ_GROUP,
		lambda inputs: inputs.switches.server_script_read
		and not inputs.below_threshold
		and not inputs.kb_draft_run,
	),
)


def _all_specs() -> list[ToolSpec]:
	# Imported lazily: tool modules import ToolContext from this file.
	specs = []
	for module_name in TOOL_MODULES:
		specs.extend(importlib.import_module(module_name).TOOLS)
	return specs


def grant(inputs: GrantInputs) -> Grant:
	"""The one grant function: the granted specs, in _all_specs() order, and the prompt block flags."""
	if inputs.effective_level not in LEVELS or inputs.effective_level == LEVELS[0]:
		return Grant(specs=())
	groups = {group for group, condition in GRANT_TABLE if condition(inputs)}
	# Below the threshold the ask tools come back, each whose group the table grants above the threshold
	# (U1.md:179 step 3, U6b-fixes Sửa 12).
	ask_groups = set()
	if inputs.below_threshold:
		above = replace(inputs, below_threshold=False)
		ask_groups = {group for group, condition in GRANT_TABLE if condition(above)}
	specs = tuple(
		spec
		for spec in _all_specs()
		if spec.group in groups or (spec.name in ASK_TOOL_NAMES and spec.group in ask_groups)
	)
	unrestricted_block = UNRESTRICTED_GROUP in groups
	# U1.md:181-187: the full-power block replaces the record block; act-now needs a power group. The reply block
	# goes with a granted tool of the reply group (U6b.md:159).
	return Grant(
		specs=specs,
		change_block=CHANGE_GROUP in groups,
		record_block=SITE_ADMIN_GROUP in groups and not unrestricted_block,
		unrestricted_block=unrestricted_block,
		act_now_block=inputs.switches.act_now
		and bool(groups & {CHANGE_GROUP, SITE_ADMIN_GROUP, UNRESTRICTED_GROUP, CONSOLE_GROUP}),
		ask_only_block=inputs.below_threshold and not inputs.kb_draft_run,
		reply_block=any(spec.group == REPLY_GROUP for spec in specs),
		console_block=CONSOLE_GROUP in groups,
	)


def get_tool_schemas(inputs: GrantInputs) -> list[dict]:
	return grant(inputs).schemas()


def _invalid(key) -> dict:
	return {"ok": False, "reason": f"tham số không hợp lệ: {str(key)[:KEY_REASON_MAX]}"}


def _is_number(value) -> bool:
	return isinstance(value, int | float) and not isinstance(value, bool)


JSON_TYPES = {
	"string": lambda v: isinstance(v, str),
	"integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
	"number": _is_number,
	"boolean": lambda v: isinstance(v, bool),
	"array": lambda v: isinstance(v, list),
	"object": lambda v: isinstance(v, dict),
}


def _value_ok(value, rule: dict) -> bool:
	type_name = rule.get("type")
	if type_name and not JSON_TYPES[type_name](value):
		return False
	if "enum" in rule and value not in rule["enum"]:
		return False
	if isinstance(value, str):
		if len(value) < rule.get("minLength", 0) or len(value) > rule.get("maxLength", len(value)):
			return False
	if _is_number(value):
		if value < rule.get("minimum", value) or value > rule.get("maximum", value):
			return False
	if isinstance(value, list):
		if len(value) > rule.get("maxItems", len(value)):
			return False
		item_rule = rule.get("items")
		if item_rule and not all(_value_ok(item, item_rule) for item in value):
			return False
	return True


def _first_invalid_key(arguments, input_schema: dict) -> str | None:
	if not isinstance(arguments, dict):
		return "arguments"
	properties = input_schema.get("properties", {})
	for key in input_schema.get("required", []):
		if key not in arguments:
			return key
	for key, value in arguments.items():
		if key not in properties or not _value_ok(value, properties[key]):
			return key
	return None


def _savepoint_gone(exc: Exception) -> bool:
	return bool(getattr(exc, "args", None)) and exc.args[0] == SAVEPOINT_GONE


def release_savepoint(name: str) -> bool:
	"""Release savepoint `name`; False when a commit inside the tool already dropped it."""
	try:
		frappe.db.release_savepoint(name)
	except Exception as exc:
		if not _savepoint_gone(exc):
			raise
		return False
	return True


def rollback_to_savepoint(name: str) -> bool:
	"""Undo back to savepoint `name`; False when a commit inside the tool already dropped it: nothing was undone."""
	try:
		frappe.db.rollback(save_point=name)
	except Exception as exc:
		if not _savepoint_gone(exc):
			raise
		return False
	return True


def execute_tool(name: str, arguments: dict, context: ToolContext) -> dict:
	granted = grant(context.grant_inputs()).specs
	spec = next((s for s in granted if s.name == name), None)
	if spec is None:
		return {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}
	bad_key = _first_invalid_key(arguments, spec.schema.get("input_schema", {}))
	if bad_key is not None:
		return _invalid(bad_key)
	frappe.db.savepoint(SAVEPOINT)
	try:
		result = spec.handler(arguments, context)
	except Exception:
		# a commit inside the handler leaves nothing to undo; the handler's own error goes on either way
		rollback_to_savepoint(SAVEPOINT)
		raise
	release_savepoint(SAVEPOINT)
	return result
