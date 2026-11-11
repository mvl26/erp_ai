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


@dataclass(frozen=True)
class ToolSpec:
	name: str
	group: Literal["read", "ticket_write", "task_write"]
	schema: dict
	handler: Callable[[dict, ToolContext], dict]


TOOL_MODULES = (
	"erp_ai.agent.tools.read",
	"erp_ai.agent.tools.source",
	"erp_ai.agent.tools.write_ticket",
)
SAVEPOINT = "erp_ai_tool"
GROUPS_BY_LEVEL = ("read", "ticket_write")


def _all_specs() -> list[ToolSpec]:
	# Imported lazily: tool modules import ToolContext from this file.
	specs = []
	for module_name in TOOL_MODULES:
		try:
			module = importlib.import_module(module_name)
		except ModuleNotFoundError as error:
			if error.name != module_name:
				raise
			continue  # tool module of a later task, not written yet
		specs.extend(module.TOOLS)
	return specs


def _granted_specs(effective_level: str, has_instructor: bool) -> list[ToolSpec]:
	if effective_level not in LEVELS or effective_level == LEVELS[0]:
		return []
	groups = GROUPS_BY_LEVEL + (("task_write",) if has_instructor else ())
	return [spec for spec in _all_specs() if spec.group in groups]


def get_tool_schemas(effective_level: str, has_instructor: bool) -> list[dict]:
	return [copy.deepcopy(spec.schema) for spec in _granted_specs(effective_level, has_instructor)]


def _invalid(key) -> dict:
	return {"ok": False, "reason": f"tham số không hợp lệ: {key}"}


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


def execute_tool(name: str, arguments: dict, context: ToolContext) -> dict:
	granted = _granted_specs(context.effective_level, bool(context.instructor))
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
