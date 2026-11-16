"""Pick the active lessons that fit a ticket (FEAT-008, AC-12, AC-13, AC-16).

Read only: no model call, no write. The runner (Task 10) is the only caller and the prompts render the rows.
"""

import frappe

from erp_ai.agent import knowledge, policy
from erp_ai.agent.prompts import LESSON_ROLE_DATA, LESSON_ROLE_RULE
from erp_ai.constants import LESSON_DOCTYPE, LESSON_SOURCE_TEACHING, LESSON_STATUS_ACTIVE


def lesson_role(source: str) -> str:
	"""How the prompt presents a lesson: a teaching is the instructor's rule, every other source is data."""
	return LESSON_ROLE_RULE if source == LESSON_SOURCE_TEACHING else LESSON_ROLE_DATA


def relevant_lessons(
	subject: str, description: str, *, max_lessons: int, max_chars: int, scan_max: int
) -> list[dict]:
	"""Active lessons sharing words with the ticket, most relevant first, within the count and size caps.

	Scans the `scan_max` newest active lessons, drops those whose source ticket the bot must not take
	(a deleted source ticket is not excluded), ranks by matched words, matched words in the situation and
	`modified`, and stops at the first lesson that would take the total past `max_chars`.
	Returns `[{name, role, situation, text}]`; `[]` when the ticket has no word to match.
	"""
	words = list(dict.fromkeys(knowledge.tokenize(f"{subject or ''} {knowledge.plain_text(description)}")))
	if not words:
		return []
	# get_all on purpose: the runner is the bot account, which has no read permission on lessons.
	rows = frappe.get_all(
		LESSON_DOCTYPE,
		filters={"lesson_status": LESSON_STATUS_ACTIVE},
		fields=["name", "lesson_source", "situation", "lesson_text", "ticket", "modified"],
		order_by="modified desc, name desc",
		limit=scan_max,
	)
	if any(row.ticket for row in rows):
		excluded = set(policy.excluded_ticket_names())
		rows = [row for row in rows if not (row.ticket and row.ticket in excluded)]
	ranked = []
	for row in rows:
		situation = row.situation or ""
		text = row.lesson_text or ""
		score = knowledge.match_score(words, situation, f"{situation} {text}")
		if score:
			ranked.append((score[0], score[1], row.modified, row))
	ranked.sort(key=lambda item: item[2], reverse=True)
	ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
	picked, total = [], 0
	for _matched, _in_heading, _modified, row in ranked:
		size = len(row.situation or "") + len(row.lesson_text or "")
		if len(picked) >= max_lessons or total + size > max_chars:
			break
		total += size
		picked.append(
			{
				"name": row.name,
				"role": lesson_role(row.lesson_source),
				"situation": row.situation or "",
				"text": row.lesson_text or "",
			}
		)
	return picked
