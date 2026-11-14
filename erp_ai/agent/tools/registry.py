import copy
import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import frappe

from erp_ai.constants import LEVELS


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


@dataclass(frozen=True)
class ToolSpec:
	name: str
	group: Literal["read", "ticket_write", "task_write", "change_propose", "site_admin", "site_unrestricted"]
	schema: dict
	handler: Callable[[dict, ToolContext], dict]


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


def _unrestricted_grant(level: str, has_instructor: bool, unrestricted: bool) -> bool:
	# The full-power switch: any level above L0 (so also L1 after a budget cut), with an instructor.
	return unrestricted and level != LEVELS[0] and has_instructor


# ADR-011 QĐ 2, 6 and ADR-023 QĐ 4: the only grant table, one row per group, checked above L0:
# group -> condition on (effective_level, has_instructor, change_enabled, unrestricted).
GRANT_TABLE = (
	("read", lambda level, has_instructor, change_enabled, unrestricted: True),
	("ticket_write", lambda level, has_instructor, change_enabled, unrestricted: True),
	("task_write", lambda level, has_instructor, change_enabled, unrestricted: has_instructor),
	(
		CHANGE_GROUP,
		lambda level, has_instructor, change_enabled, unrestricted: (
			change_enabled and level == "L3" and has_instructor
		),
	),
	# Generic record tools (site_api.py): the change tools' switch, level and authority, or full power.
	(
		SITE_ADMIN_GROUP,
		lambda level, has_instructor, change_enabled, unrestricted: (
			(change_enabled and level == "L3" and has_instructor)
			or _unrestricted_grant(level, has_instructor, unrestricted)
		),
	),
	(
		UNRESTRICTED_GROUP,
		lambda level, has_instructor, change_enabled, unrestricted: _unrestricted_grant(
			level, has_instructor, unrestricted
		),
	),
)


def _all_specs() -> list[ToolSpec]:
	# Imported lazily: tool modules import ToolContext from this file.
	specs = []
	for module_name in TOOL_MODULES:
		specs.extend(importlib.import_module(module_name).TOOLS)
	return specs


def _granted_specs(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> list[ToolSpec]:
	if effective_level not in LEVELS or effective_level == LEVELS[0]:
		return []
	groups = {
		group
		for group, condition in GRANT_TABLE
		if condition(effective_level, has_instructor, change_enabled, unrestricted)
	}
	return [spec for spec in _all_specs() if spec.group in groups]


def get_tool_schemas(
	effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool = False
) -> list[dict]:
	granted = _granted_specs(effective_level, has_instructor, change_enabled, unrestricted)
	return [copy.deepcopy(spec.schema) for spec in granted]


def _grants_group(
	group: str, effective_level: str, has_instructor: bool, change_enabled: bool, unrestricted: bool
) -> bool:
	granted = _granted_specs(effective_level, has_instructor, change_enabled, unrestricted)
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
	granted = _granted_specs(
		context.effective_level, bool(context.instructor), context.change_enabled, context.unrestricted
	)
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
