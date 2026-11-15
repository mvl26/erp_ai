"""Knowledge-base search over published HD Articles (AC-46, D-12, ADR-034 QĐ 4).

App query under the running session's permissions; never Helpdesk's own article search (it drops Vietnamese
accents and needs RediSearch, R-4). MariaDB LIKE ignores accents, so it only pre-filters; the ranking matches
whole words with accents kept. The same ranking searches the sections of the manuals directory (AC-47).
"""

import os
import re
import time
import unicodedata

import frappe
from frappe.utils import strip_html

from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import source

KB_SCAN_MAX = 200
EXCERPT_MAX_CHARS = 300
QUERY_MAX_WORDS = 8
WORD_MIN_CHARS = 2
EMPTY_QUERY = "Câu tìm cần ít nhất một từ dài 2 ký tự"
MANUALS_MAX_FILES = 500
MANUALS_FILE_MAX_BYTES = 1024 * 1024
MANUALS_BUDGET_S = 10

_WORD = re.compile(r"\w+")
# Tags that end a line or a block of text: a space goes before each of them (opening, closing or self-closing,
# any case) so words of adjacent blocks stay apart. Any other tag is inline and must not split a word.
BLOCK_TAGS = (
	"address|article|aside|blockquote|br|dd|div|dl|dt|figcaption|figure|footer|h[1-6]|header|hr|li|"
	"main|nav|ol|p|pre|section|table|tbody|td|tfoot|th|thead|tr|ul"
)
_BLOCK_TAG = re.compile(rf"<(?=/?(?:{BLOCK_TAGS})\b)", re.IGNORECASE)


def tokenize(text) -> list[str]:
	"""D-12: NFC + casefold, Unicode `\\w+` words of at least 2 characters, the first 8 of them."""
	return _words(text)[:QUERY_MAX_WORDS]


def text_words(text) -> set[str]:
	"""The words of a document text by the rules of `tokenize`, all of them: D-12 caps only the query."""
	return set(_words(text))


def plain_text(html) -> str:
	"""HTML without its tags; a space before each block tag keeps the words of adjacent blocks apart."""
	return strip_html(_BLOCK_TAG.sub(" <", html or ""))


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
		text = f"{row.title or ''} {plain_text(row.content)}"
		matched = set(words) & text_words(text)
		if matched:
			in_title = len(matched & text_words(row.title))
			ranked.append((len(matched), in_title, row.modified, row, text, matched))
	ranked.sort(key=lambda item: item[:3], reverse=True)
	return [
		{"name": row.name, "title": row.title, "excerpt": _excerpt(text, matched)}
		for _score, _in_title, _modified, row, text, matched in ranked[:limit]
	]


def search_manuals(
	query: str, limit: int, manuals_dir: str | None, *, clock=time.monotonic
) -> list[dict] | None:
	"""Sections of the `.md` manuals ranked like `search_kb_articles` (AC-47); None when `manuals_dir` is blank.

	Only the configured manuals directory is scanned, each file through `source.resolve_manual_path`: at most
	`MANUALS_MAX_FILES` files, files over `MANUALS_FILE_MAX_BYTES` skipped, stop after `MANUALS_BUDGET_S` of
	`clock`. A file that raises `OSError` on reading is skipped with one warning log line. A section starts at
	each line beginning with `#`; the text before the first one is a section with an empty heading. Order: matched words desc, matched words in the heading desc, document, line. Returns `limit`
	rows `{document (path relative to the manuals directory), heading, line (1-based), excerpt}`.
	"""
	manuals_dir = (manuals_dir or "").strip()
	if not manuals_dir:
		return None
	words = list(dict.fromkeys(tokenize(query)))
	if not words:
		frappe.throw(EMPTY_QUERY)
	source_root = source.get_source_root()
	top = os.path.realpath(os.path.join(source_root, manuals_dir))
	if top != source.manuals_root():
		return []
	ranked = []
	for document, path in _manual_files(top, clock):
		try:
			sections = list(_sections(path))
		except OSError as error:
			# Skip only this file; no absolute path and no `str(error)` in the log (it carries one).
			frappe.logger(source.LOGGER_NAME).warning(
				"search_manuals skipped %s: %s", document, type(error).__name__
			)
			continue
		for line, heading, text in sections:
			matched = set(words) & set(_words(text))
			if matched:
				in_heading = len(matched & set(_words(heading)))
				ranked.append((-len(matched), -in_heading, document, line, heading, text, matched))
	ranked.sort(key=lambda item: item[:4])
	return [
		{"document": document, "heading": heading, "line": line, "excerpt": _excerpt(text, matched)}
		for _score, _in_heading, document, line, heading, text, matched in ranked[:limit]
	]


def _manual_files(top: str, clock):
	"""`(path relative to top, real path)` of the scanned `.md` files, in name order, within the three bounds."""
	source_root = source.get_source_root()
	started = clock()
	seen = 0
	for directory, subdirs, files in os.walk(top):
		subdirs.sort()
		for name in sorted(files):
			if not name.lower().endswith(".md"):
				continue
			if seen >= MANUALS_MAX_FILES or clock() - started >= MANUALS_BUDGET_S:
				return
			seen += 1
			walked = os.path.join(directory, name)
			full = source.resolve_manual_path(os.path.relpath(walked, source_root))
			if full and os.path.isfile(full) and os.path.getsize(full) <= MANUALS_FILE_MAX_BYTES:
				yield os.path.relpath(walked, top), full


def _sections(path: str):
	"""`(1-based line, heading, text)` per section; a line starting with `#` opens a new section."""
	with open(path, encoding="utf-8", errors="replace") as handle:
		lines = unicodedata.normalize("NFC", handle.read()).splitlines()
	start, heading = 0, ""
	for index, text in enumerate(lines):
		if text.startswith("#"):
			if index:
				yield start + 1, heading, "\n".join(lines[start:index])
			start, heading = index, text.lstrip("#").strip()
	if lines:
		yield start + 1, heading, "\n".join(lines[start:])


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
