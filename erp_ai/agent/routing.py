from dataclasses import dataclass

from erp_ai.agent.classification import Classification, resolve_ticket_values


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
	"""Skeleton: values from the category mapping plus the urgent tag; no assignee, no task (T6..T10 do the rest)."""
	values = resolve_ticket_values(classification, subject, mapping)
	return RouteDecision(
		ticket_type=values["ticket_type"],
		agent_group=values["agent_group"],
		priority=values["priority"],
		assignee=None,
		needs_task=False,
		notes=[],
	)
