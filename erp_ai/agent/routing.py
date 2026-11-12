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
	notes: list


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
	"""Priority per R1-R5; team from the mapping; no assignee, no task (T7..T10 do the rest)."""
	values = resolve_ticket_values(classification, subject, mapping)
	return RouteDecision(
		ticket_type=values["ticket_type"],
		agent_group=values["agent_group"],
		priority=_priority(classification, subject, mapping, config),
		assignee=None,
		needs_task=False,
		notes=[],
	)


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
