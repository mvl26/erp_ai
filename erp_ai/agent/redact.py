"""Secret masking shared by logs, tool results, Error Log reads and emails (NFR-6, ADR-034 QĐ 2).

Rules N-1..N-7, K-1..K-8, R-1..R-5 of `design-w0-fixes-3.md` section 3, with K-4, K-4a and K-8 as
amended by `design-w0-fixes-4.md` point 3, K-4b added and K-7 as amended by `design-w1-fixes-5.md`. One word
list (`SECRET_WORDS`) drives both `is_secret_key` and the key-value scan of `redact_secrets`. Output is
always NFC (3a).
"""

import re
import unicodedata

MASK = "[đã che]"
SECRET_WORDS = ("api_key", "api_secret", "token", "secret", "password", "passwd", "pwd", "mật khẩu")

_SEGMENT_SEPARATOR = re.compile(r"[\s_\-.]+")

# The five value patterns, in this order (3b); each match except the `prefix` group is the secret.
SECRET_PATTERNS = (
	re.compile(r"(?<![\w-])sk-ant-[\w-]+"),
	re.compile(r"(?<![\w-])sk-[\w-]{16,}"),
	re.compile(r"(?P<prefix>\bBearer\s+)[\w.~+/=-]{8,}", re.IGNORECASE),
	re.compile(r"(?P<prefix>\btoken\s+)[A-Za-z0-9]+:[A-Za-z0-9]+", re.IGNORECASE),
	re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+"),
)

# Key-name candidate (K-1..K-3): up to three `[\w-]+` runs one space apart, starting where no run
# continues, then an optional quote, `:` or `=` and surrounding whitespace. Each run and each `\s*` is
# taken whole and never given back (`(?=(?P<x>...))(?P=x)`, the Python 3.10 form of a possessive
# quantifier), so the scan stays linear in the text (K-8).
_KEY_NAME_RUNS = (
	r"(?=(?P<run1>[\w-]+))(?P=run1)(?: (?=(?P<run2>[\w-]+))(?P=run2)(?: (?=(?P<run3>[\w-]+))(?P=run3))?)?"
)
_KEY_NAME_END = r"[\"']?(?=(?P<space1>\s*))(?P=space1)[:=]"
_KEY_CANDIDATE = re.compile(
	rf"(?<![\w-])(?P<name>{_KEY_NAME_RUNS}){_KEY_NAME_END}(?=(?P<space2>\s*))(?P=space2)"
)
# Key value (K-4): double-quoted, single-quoted or bare. A bare value runs over `,` `;` `&` too, unless
# the separator is followed by the end of the text, whitespace or the start of a key candidate (K-1..K-3);
# the look-ahead reads that candidate with the same taken-whole runs (K-8). `_BARE_VALUE_STEP` is the
# repeated part of a bare value, shared with `_BARE_VALUE_TAIL` so the two cannot drift apart.
_BARE_VALUE_STEP = (
	rf"(?:(?=(?P<chunk>[^\s,;&\"'}}\]]+))(?P=chunk)|[,;&](?!\Z|\s|{_KEY_NAME_RUNS}{_KEY_NAME_END}))"
)
_KEY_VALUE = re.compile(
	rf"\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'|(?P<bare>[^\s,;&\"'}}\]]{_BARE_VALUE_STEP}*)"
)
# K-7: the tail of a bare value after a `MASK` that a value pattern (R-3) already put in.
_BARE_VALUE_TAIL = re.compile(rf"{_BARE_VALUE_STEP}*")


def _name_segments(name: str) -> tuple[str, ...]:
	"""N-1..N-4: NFC, camelCase and acronym boundaries, casefold, split on `_SEGMENT_SEPARATOR`."""
	name = unicodedata.normalize("NFC", name)
	marked = "".join(
		f" {char}"
		if index
		and char.isupper()
		and (
			name[index - 1].islower()
			or name[index - 1].isdigit()
			or (name[index - 1].isupper() and index + 1 < len(name) and name[index + 1].islower())
		)
		else char
		for index, char in enumerate(name)
	)
	return tuple(segment for segment in _SEGMENT_SEPARATOR.split(marked.casefold()) if segment)


_SECRET_WORD_SEGMENTS = tuple(_name_segments(word) for word in SECRET_WORDS)

_WORD_START = re.compile(r"(?<![\w-])[\w-]")
_NOT_WORD_CHAR = re.compile(r"[^\w-]")


def _secret_value_end(text: str, start: int, end: int) -> int:
	"""K-4b: end of the secret bare value or K-7 tail read over `text[start:end]`.

	Stops at the first `MASK` or key candidate with a secret name inside it, less the non-word
	characters just before that point; otherwise `end`.
	"""
	stop = text.find(MASK, start, end + len(MASK) - 1)
	stop = end if stop == -1 else stop
	for word in _WORD_START.finditer(text, start, stop):
		candidate = _KEY_CANDIDATE.match(text, word.start())
		if candidate and is_secret_key(candidate.group("name")):
			stop = word.start()
			break
	if stop == end:
		return end
	while stop > start and _NOT_WORD_CHAR.match(text, stop - 1):
		stop -= 1
	return stop


def _mask_key_values(text: str) -> str:
	"""K-1..K-8: mask the value after each key-name candidate that `is_secret_key` accepts; one pass."""
	parts = []
	position = 0
	while candidate := _KEY_CANDIDATE.search(text, position):
		parts.append(text[position : candidate.end()])
		position = candidate.end()
		if text.startswith(MASK, position):
			parts.append(MASK)
			position += len(MASK)
			if is_secret_key(candidate.group("name")):
				position = _secret_value_end(text, position, _BARE_VALUE_TAIL.match(text, position).end())
			continue
		value = _KEY_VALUE.match(text, position)
		if value is None or not is_secret_key(candidate.group("name")):
			continue
		if value.group("double") is not None:
			parts.append(f'"{MASK}"')
			position = value.end()
		elif value.group("single") is not None:
			parts.append(f"'{MASK}'")
			position = value.end()
		elif (end := _secret_value_end(text, position, value.end())) > position:
			parts.append(MASK)
			position = end
	parts.append(text[position:])
	return "".join(parts)


def _mask_keep_prefix(match: re.Match) -> str:
	return (match.groupdict().get("prefix") or "") + MASK


def redact_secrets(text: str | None) -> str:
	"""Return `text` in NFC with each secret value replaced by `MASK`, keeping key names and prefixes.

	`None` or empty gives "". The five `SECRET_PATTERNS` run first, then the key-value scan (R-1..R-5).
	"""
	if not text:
		return ""
	text = unicodedata.normalize("NFC", text)
	for pattern in SECRET_PATTERNS:
		text = pattern.sub(_mask_keep_prefix, text)
	return _mask_key_values(text)


def is_secret_key(name: str) -> bool:
	"""N-6: True when the segments of a word of `SECRET_WORDS` appear next to each other in the segments of `name`."""
	segments = _name_segments(name)
	return any(
		segments[start : start + len(word)] == word
		for word in _SECRET_WORD_SEGMENTS
		for start in range(len(segments) - len(word) + 1)
	)
