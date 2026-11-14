"""Secret masking shared by logs, tool results, Error Log reads and emails (NFR-6, ADR-034 QĐ 2).

One word list (`SECRET_WORDS`) drives both the key-value pattern of `redact_secrets` and `is_secret_key`.
"""

import re

MASK = "[đã che]"
SECRET_WORDS = ("api_key", "api_secret", "token", "secret", "password", "passwd", "pwd", "mật khẩu")

_KEY_VALUE = re.compile(
	r"(?P<key>(?<![\w-])[\w-]*(?:" + "|".join(re.escape(word) for word in SECRET_WORDS) + r")[\w-]*"
	r"[\"']?\s*[:=]\s*)"
	r"(?:\"(?P<double>[^\"]*)\"|'(?P<single>[^']*)'|(?P<bare>[^\s,;&\"'}\]]+))",
	re.IGNORECASE,
)

SECRET_PATTERNS = (
	_KEY_VALUE,
	re.compile(r"(?<![\w-])sk-ant-[\w-]+"),
	re.compile(r"(?<![\w-])sk-[\w-]{16,}"),
	re.compile(r"(?P<prefix>\bBearer\s+)[\w.~+/=-]{8,}", re.IGNORECASE),
	re.compile(r"(?P<prefix>\btoken\s+)[A-Za-z0-9]+:[A-Za-z0-9]+", re.IGNORECASE),
	re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+"),
)


def _mask_key_value(match: re.Match) -> str:
	if match.group("double") is not None:
		return f'{match.group("key")}"{MASK}"'
	if match.group("single") is not None:
		return f"{match.group('key')}'{MASK}'"
	return match.group("key") + MASK


def _mask_keep_prefix(match: re.Match) -> str:
	return (match.groupdict().get("prefix") or "") + MASK


def redact_secrets(text: str | None) -> str:
	"""Replace each secret value matched by `SECRET_PATTERNS` with "[đã che]", keeping key names and prefixes."""
	if not text:
		return ""
	for pattern in SECRET_PATTERNS:
		text = pattern.sub(_mask_key_value if pattern is _KEY_VALUE else _mask_keep_prefix, text)
	return text


def is_secret_key(name: str) -> bool:
	"""True when the casefolded field or key name contains a word of `SECRET_WORDS`."""
	folded = name.casefold()
	return any(word in folded for word in SECRET_WORDS)
