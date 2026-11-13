"""Text of code-change commits (design 3.9, ADR-022 decision 5).

Pure module: standard library and erp_ai.constants only, no I/O. Shared by the tool,
the controller and the apply job.
"""

import unicodedata

from erp_ai.constants import BOT_GIT_NAME

APPROVER_PLACEHOLDER = "<người duyệt>"
ANONYMOUS_PERSON = "(không hiện tên)"
PERSON_NAME_MAX_CHARS = 80


def safe_person_name(full_name: str | None) -> str:
	"""One-line person name for a commit message (NFR-8).

	Control characters and line breaks become spaces, whitespace is collapsed and trimmed,
	the result is cut to 80 characters. Empty, or containing `@` or `://` → ANONYMOUS_PERSON.
	"""
	text = "".join(" " if unicodedata.category(char) == "Cc" else char for char in full_name or "")
	text = " ".join(text.split())
	if not text or "@" in text or "://" in text:
		return ANONYMOUS_PERSON
	return text[:PERSON_NAME_MAX_CHARS].rstrip()


def apply_message(proposal: str, ticket: str, file_path: str, approver: str) -> tuple[str, str]:
	"""(subject, body) of the apply commit; `approver` = APPROVER_PLACEHOLDER gives the preview."""
	subject = f"erp_ai: áp dụng {proposal} ({file_path})"
	body = (
		f"Đề xuất: {proposal}\n"
		f"Phiếu: {ticket}\n"
		f"Người duyệt: {approver}\n"
		f"Commit do {BOT_GIT_NAME} tạo sau khi người duyệt bấm Duyệt."
	)
	return subject, body


def undo_message(
	proposal: str, ticket: str, file_path: str, apply_commit: str, actor: str
) -> tuple[str, str]:
	"""(subject, body) of the undo commit; names the apply commit and the person who undid it."""
	subject = f"erp_ai: hoàn tác {proposal} ({file_path})"
	body = (
		f"Đề xuất: {proposal}\n"
		f"Phiếu: {ticket}\n"
		f"Commit áp dụng: {apply_commit}\n"
		f"Người hoàn tác: {actor}\n"
		f"Commit do {BOT_GIT_NAME} tạo sau khi người hoàn tác bấm Hoàn tác."
	)
	return subject, body


def message_text(subject: str, body: str) -> str:
	"""Full message as stored in `commit_message`: subject, blank line, body."""
	return f"{subject}\n\n{body}"
