"""Secret masking shared by logs, tool results, Error Log reads and emails (NFR-6, ADR-034 QĐ 2).

One word list (`SECRET_WORDS`) drives both the key-value pattern of `redact_secrets` and `is_secret_key`.
"""

import re
import unicodedata

MASK = "[đã che]"
SECRET_WORDS = ("api_key", "api_secret", "token", "secret", "password", "passwd", "pwd", "mật khẩu")

_SEGMENT_SEPARATOR = re.compile(r"[\s_\-.]+")

# A key-name candidate: one or two `[\w-]+` runs one space apart, starting where no run continues, then
# the separator. Possessive runs never backtrack inside a run, so each search is linear in the text.
_KEY_CANDIDATE = re.compile(r"(?<![\w-])(?P<first>[\w-]++)(?: (?P<second>[\w-]++))?[\"']?\s*+[:=]\s*+")
_KEY_VALUE = re.compile(r"\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'|(?P<bare>[^\s,;&\"'}\]]+)")


def _name_segments(name: str) -> tuple[str, ...]:
	"""NFC, a boundary where a lowercase letter or digit meets an uppercase one, casefold, split on `_SEGMENT_SEPARATOR`."""
	name = unicodedata.normalize("NFC", name)
	marked = "".join(
		f" {char}"
		if index and char.isupper() and (name[index - 1].islower() or name[index - 1].isdigit())
		else char
		for index, char in enumerate(name)
	)
	return tuple(segment for segment in _SEGMENT_SEPARATOR.split(marked.casefold()) if segment)


_SECRET_WORD_SEGMENTS = tuple(_name_segments(word) for word in SECRET_WORDS)


SECRET_PATTERNS = (
	_KEY_CANDIDATE,
	re.compile(r"(?<![\w-])sk-ant-[\w-]+"),
	re.compile(r"(?<![\w-])sk-[\w-]{16,}"),
	re.compile(r"(?P<prefix>\bBearer\s+)[\w.~+/=-]{8,}", re.IGNORECASE),
	re.compile(r"(?P<prefix>\btoken\s+)[A-Za-z0-9]+:[A-Za-z0-9]+", re.IGNORECASE),
	re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+"),
)


def _mask_key_values(text: str) -> str:
	"""Mask the value after each key-name candidate that `is_secret_key` accepts; one pass over the text."""
	parts = []
	position = 0
	while candidate := _KEY_CANDIDATE.search(text, position):
		first, second = candidate.group("first", "second")
		if second is not None and is_secret_key(first):
			# The secret word sits before another run ("token <key>:<secret>", "pwd password=…"):
			# that run, not the pair, is the next candidate.
			parts.append(text[position : candidate.start("second")])
			position = candidate.start("second")
			continue
		value = _KEY_VALUE.match(text, candidate.end())
		if value is None or not is_secret_key(first if second is None else f"{first} {second}"):
			parts.append(text[position : candidate.end()])
			position = candidate.end()
			continue
		parts.append(text[position : candidate.end()])
		if value.group("double") is not None:
			parts.append(f'"{MASK}"')
		elif value.group("single") is not None:
			parts.append(f"'{MASK}'")
		else:
			parts.append(MASK)
		position = value.end()
	parts.append(text[position:])
	return "".join(parts)


def _mask_keep_prefix(match: re.Match) -> str:
	return (match.groupdict().get("prefix") or "") + MASK


def redact_secrets(text: str | None) -> str:
	"""Replace each secret value matched by `SECRET_PATTERNS` with "[đã che]", keeping key names and prefixes."""
	if not text:
		return ""
	text = _mask_key_values(unicodedata.normalize("NFC", text))
	for pattern in SECRET_PATTERNS[1:]:
		text = pattern.sub(_mask_keep_prefix, text)
	return text


def is_secret_key(name: str) -> bool:
	"""True when the segments of a word of `SECRET_WORDS` appear next to each other in the segments of `name`."""
	segments = _name_segments(name)
	return any(
		segments[start : start + len(word)] == word
		for word in _SECRET_WORD_SEGMENTS
		for start in range(len(segments) - len(word) + 1)
	)
