"""Ticket labels (ADR-049 with CHG-014): the one Helpdesk Tag the bot gives a ticket at classification, chosen from
the tag table of ERP AI Setting by each tag's description; when none fits, a new tag the model names and describes
(CHG-018), which the route adds to the table.

The labels live where Helpdesk keeps tags (`_user_tags` and `Tag Link`); the list of tags lives in the tag table
(`routing.tag_rules`), where `add_tag_row` puts a new tag (CHG-018).
"""

import hashlib

import frappe

from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE, TAG_ASSIGNEE_DOCTYPE

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


TAG_TABLE = {"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE, "parentfield": "tag_assignees"}
# CHG-018 review fix I1: rows the bot added that no System Manager has reviewed yet; past this many it adds none.
BOT_TAGS_UNREVIEWED_MAX = 20
TOO_MANY_UNREVIEWED_TAGS = f"bảng đã có {BOT_TAGS_UNREVIEWED_MAX} tag bot tạo chưa duyệt"


def _table_rows() -> list:
	return frappe.get_all(TAG_ASSIGNEE_DOCTYPE, filters=TAG_TABLE, fields=["tag", "idx", "bot_added"])


def _known_tag(tag: str, rows) -> bool:
	"""The table has `tag`: by `tag_key`, or by the database's own comparison, which also ignores accents (the one
	`check_tag_assignees` and Tag names use)."""
	from erp_ai.agent.routing import tag_key

	key = tag_key(tag)
	return any(tag_key(row.tag) == key for row in rows) or bool(
		frappe.db.exists(TAG_ASSIGNEE_DOCTYPE, {**TAG_TABLE, "tag": tag})
	)


def add_tag_row(tag: str, description: str) -> dict:
	"""CHG-018: put a tag the bot made at the end of the tag table of ERP AI Setting, with the model's description
	(secrets masked), no person and `bot_added` set, so later tickets choose it by name and a System Manager reviews
	it. A system write of the route (ADR-023 Amendment 1), not a model tool: outside agent/tools (ADR-005, ADR-034).

	A tag the table has is not added again. Past BOT_TAGS_UNREVIEWED_MAX unreviewed bot rows it adds none and says
	why. The row alone is written, not the Setting: no check of the Setting's other fields runs and nobody's open
	Setting form goes stale. Its name comes from the tag, so a run whose read of the table came before another run's
	row of that tag adds no second one; a row of that name holding another tag (a bot row renamed since) gives way
	to a row of a random name. Returns `{"ok": True, "added": False}`, `{"ok": True, "added": True, "description":
	<as stored>}` or `{"ok": False, "reason": ...}`."""
	from erp_ai.agent.redact import redact_secrets
	from erp_ai.agent.routing import tag_key

	rows = _table_rows()
	if _known_tag(tag, rows):
		return {"ok": True, "added": False}
	if sum(1 for row in rows if row.bot_added) >= BOT_TAGS_UNREVIEWED_MAX:
		return {"ok": False, "reason": TOO_MANY_UNREVIEWED_TAGS}
	key = tag_key(tag)
	values = {
		"doctype": TAG_ASSIGNEE_DOCTYPE,
		**TAG_TABLE,
		"idx": max((row.idx or 0 for row in rows), default=0) + 1,
		"tag": tag,
		"description": redact_secrets(description),
		"bot_added": 1,
	}
	name = f"erp-ai-tag-{hashlib.sha1(key.encode()).hexdigest()[:12]}"
	try:
		frappe.get_doc({**values, "name": name}).db_insert()
	except frappe.DuplicateEntryError:
		# a locking read sees the other run's committed row, which the run's own snapshot may not
		held = frappe.db.get_value(TAG_ASSIGNEE_DOCTYPE, name, "tag", for_update=True)
		if tag_key(held) == key:
			return {"ok": True, "added": False}
		frappe.get_doc(values).db_insert()
	frappe.clear_document_cache(SETTING_DOCTYPE, SETTING_DOCTYPE)
	return {"ok": True, "added": True, "description": values["description"]}
