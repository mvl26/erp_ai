import copy
import importlib
from collections.abc import Callable
from dataclasses import dataclass
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

	def grant_inputs(self) -> GrantInputs:
		switches = PermissionSwitches(
			unrestricted=self.unrestricted,
			# temporary bridge, removed in T82, source design-w1-fixes-3.md Điểm 1
			record_tools=self.record_tools or self.change_enabled,
			act_now=self.act_now,
			code_change=self.change_enabled,
			one_click_approval=self.one_click_approval,
		)
		return GrantInputs(
			effective_level=self.effective_level,
			main_path_level=self.effective_level if self.main_path_level is None else self.main_path_level,
			has_instructor=bool(self.instructor),
			switches=switches,
			over_budget=self.over_budget,
			below_threshold=self.below_threshold,
		)


@dataclass(frozen=True)
class ToolSpec:
	name: str
	group: Literal["read", "ticket_write", "task_write", "change_propose", "site_admin", "site_unrestricted"]
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
)
SAVEPOINT = "erp_ai_tool"
KEY_REASON_MAX = 100  # model-supplied argument names are cut so reason stays short
CHANGE_GROUP = "change_propose"
SITE_ADMIN_GROUP = "site_admin"
UNRESTRICTED_GROUP = "site_unrestricted"


def unrestricted_granted(inputs: GrantInputs) -> bool:
	# The full-power switch: any level above L0 (so also L1 after a budget cut), with an instructor.
	return inputs.switches.unrestricted and inputs.effective_level in LEVELS[1:] and inputs.has_instructor


# ADR-011 QĐ 2, 6, ADR-023 QĐ 4 and ADR-030 QĐ 3: the only grant table, one row per group, checked
# above L0: (group, Callable[[GrantInputs], bool]). The below-threshold and over-budget terms come in T77.
GRANT_TABLE = (
	("read", lambda inputs: True),
	("ticket_write", lambda inputs: True),
	("task_write", lambda inputs: inputs.has_instructor and inputs.main_path_level in LEVELS[1:]),
	(
		CHANGE_GROUP,
		lambda inputs: inputs.switches.code_change
		and inputs.effective_level == "L3"
		and inputs.has_instructor,
	),
	# Generic record tools (site_api.py): the record-tools switch, level and authority, or full power.
	(
		SITE_ADMIN_GROUP,
		lambda inputs: (
			(inputs.switches.record_tools and inputs.effective_level == "L3" and inputs.has_instructor)
			or unrestricted_granted(inputs)
		),
	),
	(UNRESTRICTED_GROUP, unrestricted_granted),
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
	specs = tuple(spec for spec in _all_specs() if spec.group in groups)
	granted_groups = {spec.group for spec in specs}
	# act_now_block and ask_only_block stay False until T77 (design-w1-fixes-3.md Điểm 2).
	return Grant(
		specs=specs,
		change_block=CHANGE_GROUP in granted_groups,
		record_block=SITE_ADMIN_GROUP in granted_groups,
		unrestricted_block=UNRESTRICTED_GROUP in granted_groups,
	)


def _legacy_inputs(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> GrantInputs:
	# The old four-argument callers until T82: (2) and (4) both follow change_enabled; (3), (5) off.
	return GrantInputs(
		effective_level=effective_level,
		main_path_level=effective_level,
		has_instructor=has_instructor,
		switches=PermissionSwitches(
			unrestricted=unrestricted, record_tools=change_enabled, code_change=change_enabled
		),
	)


def get_tool_schemas(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> list[dict]:
	return grant(_legacy_inputs(effective_level, has_instructor, change_enabled, unrestricted)).schemas()


def _grants_group(
	group: str, effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool
) -> bool:
	granted = grant(_legacy_inputs(effective_level, has_instructor, change_enabled, unrestricted)).specs
	return any(spec.group == group for spec in granted)


def grants_change_tools(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> bool:
	return _grants_group(CHANGE_GROUP, effective_level, has_instructor, change_enabled, unrestricted)


def grants_site_admin_tools(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> bool:
	return _grants_group(SITE_ADMIN_GROUP, effective_level, has_instructor, change_enabled, unrestricted)


def grants_unrestricted_tools(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> bool:
	return _grants_group(UNRESTRICTED_GROUP, effective_level, has_instructor, change_enabled, unrestricted)


def _invalid(key) -> dict:
	return {"ok": False, "reason": f"tham số không hợp lệ: {str(key)[:KEY_REASON_MAX]}"}


def _is_number(value) -> bool:
	return isinstance(value, int | float) and not isinstance(value, bool)


JSON_TYPES = {
	"string": lambda v: isinstance(v, str),
	"integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
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
		frappe.db.rollback(save_point=SAVEPOINT)
		raise
	frappe.db.release_savepoint(SAVEPOINT)
	return result
