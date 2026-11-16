"""Line helpers for multi-line setting values; standard library only, so any layer may import it."""


def filled_lines(value: str | None) -> list[str]:
	"""The non-blank lines of `value`, each stripped, in order; duplicates are kept. None or "" gives []."""
	return [line.strip() for line in (value or "").splitlines() if line.strip()]
