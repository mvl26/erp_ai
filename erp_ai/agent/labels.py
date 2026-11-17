"""Ticket labels (ADR-049): the Helpdesk Tags the bot gives a ticket at classification, and what the next
classification is shown of them.

The labels live where Helpdesk keeps tags (`_user_tags` and `Tag Link`); nothing is stored here. Each classification
reads the labelled tickets again, so a label a person fixes on a ticket is what the next alike ticket sees.
"""

from collections import Counter
from typing import NamedTuple

import frappe

from erp_ai.agent import policy
from erp_ai.constants import AGENT_USER

TICKET_DOCTYPE = "HD Ticket"
# The app's own module is no area of the business (read.AI_MODULE, install.AI_MODULE).
AI_MODULE = "ERP AI agent"
# Helpdesk tags a requester's first ticket itself: no label of the ticket's content.
IGNORED_LABELS = frozenset({"First Ticket"})
LABEL_SCAN_MAX = 500
CATALOG_MAX = 40
SIMILAR_MAX = 5
SIMILAR_MIN_WORDS = 2
# The new ticket's subject and the start of its description are matched against the subjects of labelled tickets.
SIMILAR_TEXT_CHARS = 1000
# Function words of Vietnamese tickets: shared, they say nothing about what a ticket is about.
COMMON_WORDS = frozenset(
	{
		"ai",
		"anh",
		"bạn",
		"bị",
		"các",
		"cần",
		"cho",
		"chị",
		"có",
		"của",
		"đã",
		"đang",
		"để",
		"em",
		"được",
		"giúp",
		"hỗ",
		"khi",
		"không",
		"là",
		"lại",
		"mà",
		"một",
		"này",
		"nhờ",
		"những",
		"phiếu",
		"rồi",
		"sẽ",
		"thì",
		"tôi",
		"trên",
		"trợ",
		"và",
		"vẫn",
		"với",
		"vui",
		"lòng",
	}
)


class LabelInputs(NamedTuple):
	"""What the classify request is shown of the labels (prompts.build_classify_request takes `_asdict()`)."""

	modules: tuple[str, ...] = ()
	# (label, tickets carrying it, the Tag's description)
	label_catalog: tuple[tuple[str, int, str], ...] = ()
	# (subject, labels) of alike tickets, most alike first
	similar_labels: tuple[tuple[str, tuple[str, ...]], ...] = ()


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
	spelling = {tag.casefold(): tag for tag, _description in choices}
	first = labels[0].casefold() if labels else ""
	return (spelling[first],) if first in spelling else ()


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


def module_labels() -> tuple[str, ...]:
	"""The modules of the installed apps, the bot's own left out, sorted without case: the names a first label takes."""
	names = frappe.get_all("Module Def", filters={"name": ["!=", AI_MODULE]}, pluck="name")
	return tuple(sorted(names, key=str.casefold))


def canonical(labels: tuple[str, ...], modules: tuple[str, ...]) -> tuple[str, ...]:
	"""`labels` with a module's own spelling where one matches it without case, Helpdesk's own tags left out."""
	spelling = {module.casefold(): module for module in modules}
	ignored = {tag.casefold() for tag in IGNORED_LABELS}
	return tuple(spelling.get(label.casefold(), label) for label in labels if label.casefold() not in ignored)


def _words(text) -> set[str]:
	# Imported on call: knowledge imports tools.source, which imports tools.read as it loads.
	from erp_ai.agent import knowledge

	return knowledge.text_words(text) - COMMON_WORDS


def classify_inputs(
	ticket_name: str, subject: str, description: str, pinned: tuple[str, ...] = ()
) -> LabelInputs:
	"""The module list, the labels in use and the labels of alike tickets for classifying `ticket_name`.

	`pinned` (CHG-011): the tags of the assignee table; each one not already among the most used follows them in the
	catalog, never cut by CATALOG_MAX, so the model knows it even before any ticket carries it.

	One scan of the LABEL_SCAN_MAX newest labelled tickets, the ticket itself and excluded tickets left out
	(ADR-034 QĐ 1): the catalog counts them, the alike ones share SIMILAR_MIN_WORDS words or more with the ticket.
	"""
	from erp_ai.agent import knowledge

	excluded, _or = policy.ticket_content_filters(TICKET_DOCTYPE)
	rows = frappe.get_all(
		TICKET_DOCTYPE,
		filters=[["_user_tags", "is", "set"], ["name", "!=", ticket_name], *excluded],
		fields=["subject", "_user_tags"],
		order_by="modified desc",
		limit_page_length=LABEL_SCAN_MAX,
	)
	counts = Counter()
	words = _words(f"{subject or ''} {knowledge.plain_text(description)[:SIMILAR_TEXT_CHARS]}")
	ranked = []
	for order, row in enumerate(rows):
		names = parse_tags(row._user_tags)
		if not names:
			continue
		counts.update(dict.fromkeys(names, 1))
		shared = len(words & _words(row.subject))
		if shared >= SIMILAR_MIN_WORDS:
			ranked.append((-shared, order, row.subject or "", tuple(names)))
	ranked.sort()
	top = counts.most_common(CATALOG_MAX)
	listed = {name.casefold() for name, _count in top}
	for name in pinned:
		if name and name.casefold() not in listed:
			listed.add(name.casefold())
			top.append((name, counts[name]))
	descriptions = dict(
		frappe.get_all(
			"Tag",
			filters={"name": ["in", [name for name, _count in top] or [""]]},
			fields=["name", "description"],
			as_list=True,
		)
	)
	return LabelInputs(
		modules=module_labels(),
		label_catalog=tuple((name, count, descriptions.get(name) or "") for name, count in top),
		similar_labels=tuple((subject, names) for _shared, _order, subject, names in ranked[:SIMILAR_MAX]),
	)
