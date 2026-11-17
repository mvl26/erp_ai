"""Ticket labels (ADR-049 with CHG-014): the one Helpdesk Tag the bot gives a ticket at classification, chosen from
the tag table of ERP AI Setting by each tag's description; when none fits, a new tag the model names and describes
(CHG-018), which the route adds to the table.

The labels live where Helpdesk keeps tags (`_user_tags` and `Tag Link`); the list of tags lives in the tag table
(`routing.tag_rules`); nothing is stored here.
"""

import frappe

from erp_ai.constants import AGENT_USER

TICKET_DOCTYPE = "HD Ticket"
# Helpdesk tags a requester's first ticket itself: no label of the ticket's content.
IGNORED_LABELS = frozenset({"First Ticket"})


def parse_tags(value) -> list[str]:
	"""The labels of a `_user_tags` column (",a,b"), in order, without blanks and Helpdesk's own tags."""
	return [
		tag
		for tag in (part.strip() for part in (value or "").split(","))
		if tag and tag not in IGNORED_LABELS
	]


def tag_choices(rules) -> tuple[tuple[str, str], ...]:
	"""(tag, description) of the tag table in its order, each tag once without case, the description of its first
	row (CHG-014): the list the classify step chooses the ticket's one tag from."""
	seen, choices = set(), []
	for rule in rules:
		if rule.tag.casefold() not in seen:
			seen.add(rule.tag.casefold())
			choices.append((rule.tag, rule.description))
	return tuple(choices)


def chosen_tag(labels: tuple[str, ...], choices) -> tuple[str, ...]:
	"""(the table's tag,) when the model's first label is a tag of `choices` without case, else () (CHG-014)."""
	from erp_ai.agent.routing import tag_key

	spelling = {tag_key(tag): tag for tag, _description in choices}
	first = tag_key(labels[0]) if labels else ""
	return (spelling[first],) if first in spelling else ()


# CHG-018: a noise ticket (test, unclear title) makes no new tag; it may still get a tag of the table.
NO_NEW_TAG_CATEGORY = "F"


def new_tag(labels: tuple[str, ...], description: str, category: str, choices) -> tuple[str, str] | None:
	"""(tag, description) when the model's first label is no tag of `choices` and comes with a description, on a
	ticket that is not noise and for a tag Helpdesk does not give itself; else None (CHG-018)."""
	from erp_ai.agent.routing import tag_key

	if not labels or not description or category == NO_NEW_TAG_CATEGORY:
		return None
	first = tag_key(labels[0])
	if first in {tag_key(tag) for tag, _description in choices}:
		return None
	if first in {tag_key(tag) for tag in IGNORED_LABELS}:
		return None
	return labels[0], description


def agent_tags(ticket_name: str, is_active_agent) -> tuple[str, ...]:
	"""The ticket's tags an active HD Agent other than the bot put on, in the order they were put on (CHG-011).

	Frappe's whitelisted add_tag lets the requester tag their own ticket; only the tag of someone who could assign
	the ticket themselves may pick its person. The Tag Link's owner is who put the tag on.
	"""
	rows = frappe.get_all(
		"Tag Link",
		filters={"document_type": TICKET_DOCTYPE, "document_name": ticket_name},
		fields=["tag", "owner"],
		order_by="creation, name",
	)
	return tuple(
		dict.fromkeys(
			row.tag
			for row in rows
			if row.tag
			and row.tag not in IGNORED_LABELS
			and (row.owner or "").casefold() != AGENT_USER.casefold()
			and is_active_agent(row.owner)
		)
	)
