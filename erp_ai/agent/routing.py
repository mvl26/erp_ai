from dataclasses import dataclass

from erp_ai.agent.classification import (
	PRIORITY_URGENT,
	URGENT_TAGS,
	Classification,
	resolve_ticket_values,
)

PRIORITIES = ("Low", "Medium", "High", "Urgent")


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
	"""Priority per R1-R5; team per mapping or department; no assignee, no task (T8..T10 do the rest)."""
	values = resolve_ticket_values(classification, subject, mapping)
	notes = []
	if classification.category in ("D", "E"):
		agent_group = _department_team(classification, config, team_exists, is_excluded_team, notes)
	else:
		agent_group = values["agent_group"] or None
	return RouteDecision(
		ticket_type=values["ticket_type"],
		agent_group=agent_group,
		priority=_priority(classification, subject, mapping, config),
		assignee=None,
		needs_task=False,
		notes=tuple(notes),
	)


# Same normalization as policy.py (copied: routing does not import frappe yet).
def _normalize(name) -> str:
	return " ".join((name or "").split()).casefold()


def _department_team(classification, config, team_exists, is_excluded_team, notes) -> str | None:
	department = classification.department
	key = _normalize(department)
	if not key:
		return _skip_team(notes, "không có bộ phận")
	departments = (config or {}).get("departments") or {}
	entry = next((value for name, value in departments.items() if _normalize(name) == key), None)
	if entry is None:
		return _skip_team(notes, f"bộ phận '{department}' không có trong bảng bộ phận")
	team = (entry or {}).get("team") or ""
	if not team or not team_exists(team):
		return _skip_team(notes, f"nhóm '{team}' không tồn tại")
	if is_excluded_team(team):
		return _skip_team(notes, f"nhóm '{team}' bị loại trừ")
	return team


def _skip_team(notes, reason) -> None:
	notes.append({"field": "agent_group", "reason": reason})


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
