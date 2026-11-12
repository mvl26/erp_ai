import json
from dataclasses import dataclass

import frappe

from erp_ai.agent.classification import (
	PRIORITY_URGENT,
	URGENT_TAGS,
	Classification,
	resolve_ticket_values,
)
from erp_ai.constants import AGENT_USER, CATEGORIES

PRIORITIES = ("Low", "Medium", "High", "Urgent")

# Default routing_rules (design 3.3, D-11). People lists stay empty: System Manager fills them in.
DEFAULT_ROUTING_RULES = json.dumps(
	{
		"assignees": {
			"A": {"default": "", "prefixes": {"[tracecore]": ""}},
			"B": {"default": "", "prefixes": {}},
			"C": {"default": "", "prefixes": {}},
			"F": {"default": "", "prefixes": {}},
		},
		"departments": {},
		"importance_priority": {"1": "", "2": "High", "3": "High"},
		"expected_sla": {
			"A": {"response_min": 15, "resolution_min": 480},
			"B": {"response_min": 15, "resolution_min": 240},
			"C": {"response_min": 60, "resolution_min": 1440},
			"D": {"response_min": 60, "resolution_min": None},
			"E": {"response_min": 60, "resolution_min": None},
			"F": {"response_min": 5, "resolution_min": 60},
		},
	},
	ensure_ascii=False,
	indent=2,
)
ROOT_KEYS = ("assignees", "departments", "importance_priority", "expected_sla")
ASSIGNEE_CATEGORIES = ("A", "B", "C", "F")
SLA_KEYS = ("response_min", "resolution_min")


@dataclass(frozen=True)
class RouteDecision:
	ticket_type: str | None
	agent_group: str | None
	priority: str | None
	assignee: str | None
	needs_task: bool
	notes: tuple


def decide_route(
	classification: Classification,
	subject,
	mapping: dict,
	config: dict,
	*,
	team_exists,
	is_excluded_team,
	is_active_agent,
) -> RouteDecision:
	"""Priority per R1-R5; team per mapping or department; assignee by category/prefix; needs_task for C/D."""
	values = resolve_ticket_values(classification, subject, mapping)
	notes = []
	if classification.category in ("D", "E"):
		agent_group = _department_team(classification, config, team_exists, is_excluded_team, notes)
	else:
		agent_group = values["agent_group"] or None
	assignee = _assignee(classification, subject, config, is_active_agent, notes)
	return RouteDecision(
		ticket_type=values["ticket_type"],
		agent_group=agent_group,
		priority=_priority(classification, subject, mapping, config),
		assignee=assignee,
		needs_task=classification.category in ("C", "D") and assignee is not None,
		notes=tuple(notes),
	)


# Same normalization as policy.py (kept local so routing does not import policy).
def _normalize(name) -> str:
	return " ".join((name or "").split()).casefold()


def _department_team(classification, config, team_exists, is_excluded_team, notes) -> str | None:
	department = classification.department
	key = _normalize(department)
	if not key:
		return _skip_team(notes, "không có bộ phận")
	entry = _department_entry(config, key)
	if entry is None:
		return _skip_team(notes, f"bộ phận '{department}' không có trong bảng bộ phận")
	team = (entry or {}).get("team") or ""
	if not team or not team_exists(team):
		return _skip_team(notes, f"nhóm '{team}' không tồn tại")
	if is_excluded_team(team):
		return _skip_team(notes, f"nhóm '{team}' bị loại trừ")
	return team


def _department_entry(config, key):
	departments = (config or {}).get("departments") or {}
	return next((value for name, value in departments.items() if _normalize(name) == key), None)


def _skip_team(notes, reason) -> None:
	notes.append({"field": "agent_group", "reason": reason})


def _assignee(classification, subject, config, is_active_agent, notes) -> str | None:
	category = classification.category
	if category in ("D", "E"):
		entry = _department_entry(config, _normalize(classification.department))
		candidate = (entry or {}).get("head") or ""
	else:
		candidate = _category_assignee(category, subject, config)
	if not candidate:
		notes.append({"field": "assignee", "reason": f"cấu hình không có người cho đầu mục {category}"})
		return None
	if candidate.strip().casefold() == AGENT_USER.casefold():
		notes.append({"field": "assignee", "reason": "không gán tài khoản agent"})
		return None
	if not is_active_agent(candidate):
		notes.append({"field": "assignee", "reason": f"{candidate} không phải HD Agent đang hoạt động"})
		return None
	return candidate


def _category_assignee(category, subject, config) -> str:
	entry = ((config or {}).get("assignees") or {}).get(category) or {}
	title = subject.casefold() if isinstance(subject, str) else ""
	for prefix, user in (entry.get("prefixes") or {}).items():
		if user and prefix and prefix.casefold() in title:
			return user
	return entry.get("default") or ""


def _priority(classification: Classification, subject, mapping: dict, config: dict) -> str | None:
	category = classification.category
	if isinstance(subject, str) and any(tag in subject.upper() for tag in URGENT_TAGS):
		return PRIORITY_URGENT
	if category == "F":
		return "Low"
	if category == "E":
		return None
	importance = classification.importance
	if category == "A" and importance == 3:
		return PRIORITY_URGENT
	candidates = [(mapping.get(category) or {}).get("priority")]
	if importance:
		candidates.append(((config or {}).get("importance_priority") or {}).get(str(importance)))
	candidates = [value for value in candidates if value]
	return max(candidates, key=_rank) if candidates else None


def _rank(priority: str) -> int:
	return PRIORITIES.index(priority) if priority in PRIORITIES else -1


def sla_lag(category: str, resolution_s: int | None, config: dict) -> tuple[int, int] | None:
	"""(actual_min, expected_min) when the applied SLA resolves slower than expected, else None.

	actual_min is resolution_s rounded UP to whole minutes, so it is always above expected_min.
	D/E, a null resolution_min, a missing category/config and resolution_s None are not checked.
	"""
	if resolution_s is None or category in ("D", "E"):
		return None
	expected_min = (((config or {}).get("expected_sla") or {}).get(category) or {}).get("resolution_min")
	if expected_min is None or resolution_s <= expected_min * 60:
		return None
	return (-(-resolution_s // 60), expected_min)


def departments(config: dict) -> tuple[str, ...]:
	"""Department names in declared order (for the classify prompt)."""
	return tuple((config or {}).get("departments") or {})


def _is_minutes(value) -> bool:
	return value is None or (type(value) is int and value > 0)


def _user_error(path, user, check_users):
	if not isinstance(user, str):
		return f"{path}: người phải là chuỗi"
	if check_users and user and not frappe.db.exists("User", user):
		return f"{path}: người '{user}' không tồn tại"
	return None


def _assignees_error(assignees, check_users):
	if not isinstance(assignees, dict):
		return "assignees phải là object"
	for category, entry in assignees.items():
		if category not in ASSIGNEE_CATEGORIES:
			return f"assignees: đầu mục '{category}' không hợp lệ (D, E lấy người theo departments)"
		path = f"assignees.{category}"
		if not (
			isinstance(entry, dict)
			and isinstance(entry.get("default"), str)
			and isinstance(entry.get("prefixes"), dict)
		):
			return f"{path} phải là object có default (chuỗi) và prefixes (object)"
		error = _user_error(f"{path}.default", entry["default"], check_users)
		for prefix, user in entry["prefixes"].items():
			error = error or _user_error(f"{path}.prefixes.{prefix}", user, check_users)
		if error:
			return error
	return None


def _departments_error(departments, check_users):
	if not isinstance(departments, dict):
		return "departments phải là object"
	for name, entry in departments.items():
		if not (
			_normalize(name)
			and isinstance(entry, dict)
			and isinstance(entry.get("team"), str)
			and isinstance(entry.get("head"), str)
		):
			return f"departments.{name} phải là object có team và head (chuỗi)"
		error = _user_error(f"departments.{name}.head", entry["head"], check_users)
		if error:
			return error
	return None


def _importance_error(table):
	if not isinstance(table, dict) or sorted(table) != ["1", "2", "3"]:
		return "importance_priority phải có đúng các khóa 1, 2, 3"
	for level, value in table.items():
		if value != "" and value not in PRIORITIES:
			return (
				f"importance_priority.{level}: mức '{value}' không hợp lệ, "
				"chỉ nhận Low, Medium, High, Urgent hoặc rỗng"
			)
	return None


def _sla_error(table):
	if not isinstance(table, dict):
		return "expected_sla phải là object"
	for category, entry in table.items():
		if category not in CATEGORIES or not isinstance(entry, dict):
			return f"expected_sla.{category} phải là object theo đầu mục {', '.join(CATEGORIES)}"
		for key, value in entry.items():
			if key not in SLA_KEYS or not _is_minutes(value):
				return f"expected_sla.{category}.{key} phải là số nguyên dương (phút) hoặc null"
	return None


def _config_error(raw, check_users):
	"""Message naming the bad key path, or None when raw is a valid routing_rules."""
	try:
		data = json.loads(raw) if isinstance(raw, str) else None
	except ValueError:
		data = None
	if not isinstance(data, dict):
		return "Cấu hình định tuyến không phải JSON object hợp lệ"
	for key in data:
		if key not in ROOT_KEYS:
			return f"Cấu hình định tuyến có khóa lạ '{key}', chỉ nhận {', '.join(ROOT_KEYS)}"
	checks = (
		("assignees", lambda value: _assignees_error(value, check_users)),
		("departments", lambda value: _departments_error(value, check_users)),
		("importance_priority", _importance_error),
		("expected_sla", _sla_error),
	)
	for key, check in checks:
		error = key in data and check(data[key])
		if error:
			return error
	return None


def validate_routing_config(raw) -> None:
	"""Raise frappe.ValidationError naming the bad key path. Does not check teams or block the agent account."""
	error = _config_error(raw, check_users=True)
	if error:
		frappe.throw(error)


def load_routing_config(raw) -> dict:
	"""Parse routing_rules with every root key present; a bad schema gives {} and never raises."""
	if _config_error(raw, check_users=False):
		return {}
	data = json.loads(raw)
	return {key: data.get(key, {}) for key in ROOT_KEYS}
