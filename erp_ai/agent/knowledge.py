"""Knowledge-base search over published HD Articles (AC-46, D-12, ADR-034 QĐ 4).

App query under the running session's permissions; never Helpdesk's own article search (it drops Vietnamese
accents and needs RediSearch, R-4). MariaDB LIKE ignores accents, so it only pre-filters; the ranking matches
whole words with accents kept.
"""

import re
import unicodedata

import frappe
from frappe.utils import strip_html

from erp_ai.agent.redact import redact_secrets

KB_SCAN_MAX = 200
EXCERPT_MAX_CHARS = 300
QUERY_MAX_WORDS = 8
WORD_MIN_CHARS = 2
EMPTY_QUERY = "Câu tìm cần ít nhất một từ dài 2 ký tự"

_WORD = re.compile(r"\w+")


def tokenize(text) -> list[str]:
	"""D-12: NFC + casefold, Unicode `\\w+` words of at least 2 characters, the first 8 of them."""
	return _words(text)[:QUERY_MAX_WORDS]


def search_kb_articles(query: str, limit: int) -> list[dict]:
	"""Published articles the session user may read, ranked by the number of query words they contain.

	Order: matched words desc, matched words in the title desc, `modified` desc. Returns `limit` rows
	`{name, title, excerpt}`.
	"""
	words = list(dict.fromkeys(tokenize(query)))
	if not words:
		frappe.throw(EMPTY_QUERY)
	or_filters = []
	for word in words:
		pattern = _like_pattern(word)
		or_filters += [["title", "like", pattern], ["content", "like", pattern]]
	rows = frappe.get_list(
		"HD Article",
		filters={"status": "Published"},
		or_filters=or_filters,
		fields=["name", "title", "content", "modified"],
		order_by="modified desc",
		limit_page_length=KB_SCAN_MAX,
	)
	ranked = []
	for row in rows:
		# One space keeps the last title word and the first content word apart.
		text = f"{row.title or ''} {strip_html(row.content or '')}"
		matched = set(words) & set(_words(text))
		if matched:
			in_title = len(matched & set(_words(row.title)))
			ranked.append((len(matched), in_title, row.modified, row, text, matched))
	ranked.sort(key=lambda item: item[:3], reverse=True)
	return [
		{"name": row.name, "title": row.title, "excerpt": _excerpt(text, matched)}
		for _score, _in_title, _modified, row, text, matched in ranked[:limit]
	]


def _words(text) -> list[str]:
	normalized = unicodedata.normalize("NFC", text or "").casefold()
	return [word for word in _WORD.findall(normalized) if len(word) >= WORD_MIN_CHARS]


def _like_pattern(word: str) -> str:
	escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{escaped}%"


def _excerpt(text: str, matched: set[str]) -> str:
	"""`EXCERPT_MAX_CHARS` characters around the first matched word, masked first and cut after (3a)."""
	masked = redact_secrets(text)
	first = next(
		(found.start() for found in _WORD.finditer(masked) if found.group().casefold() in matched),
		0,
	)
	start = max(0, min(first - EXCERPT_MAX_CHARS // 2, len(masked) - EXCERPT_MAX_CHARS))
	return masked[start : start + EXCERPT_MAX_CHARS]
