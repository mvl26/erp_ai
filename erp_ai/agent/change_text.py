"""Text of code-change commits (design 3.9, ADR-022 decision 5).

Pure module: standard library and erp_ai.constants only, no I/O. Shared by the tool,
the controller and the apply job.
"""

import json
import unicodedata

from erp_ai.constants import (
	BOT_GIT_NAME,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_UNDONE,
)

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


# Verb of each item line of a block commit body (CHG-002 design 3.7).
_ITEM_VERBS = {
	CHANGE_OP_EDIT: "sửa",
	CHANGE_OP_CREATE: "tạo",
	CHANGE_OP_DELETE: "xóa",
	CHANGE_OP_RENAME: "đổi tên",
}


def block_label(operations) -> str:
	"""Label of a block commit: the item's path for one item, `{n} file` for more (CHG-002 3.7)."""
	if len(operations) == 1:
		return operations[0].path
	return f"{len(operations)} file"


def _item_lines(operations) -> str:
	"""One line per block item (`sửa …`, `tạo …`, `xóa …`, `đổi tên … → …`); "" for `None`."""
	lines = []
	for operation in operations or ():
		line = f"{_ITEM_VERBS[operation.kind]} {operation.path}"
		if operation.kind == CHANGE_OP_RENAME:
			line += f" → {operation.new_path}"
		lines.append(f"{line}\n")
	return "".join(lines)


def apply_message(proposal: str, ticket: str, label: str, approver: str, operations=None) -> tuple[str, str]:
	"""(subject, body) of the apply commit; `approver` = APPROVER_PLACEHOLDER gives the preview.

	`operations` (block items) adds one line per item after the "Phiếu" line; `None` keeps the old text.
	"""
	subject = f"erp_ai: áp dụng {proposal} ({label})"
	body = (
		f"Đề xuất: {proposal}\n"
		f"Phiếu: {ticket}\n"
		f"{_item_lines(operations)}"
		f"Người duyệt: {approver}\n"
		f"Commit do {BOT_GIT_NAME} tạo sau khi người duyệt bấm Duyệt."
	)
	return subject, body


def undo_message(
	proposal: str, ticket: str, label: str, apply_commit: str, actor: str, operations=None
) -> tuple[str, str]:
	"""(subject, body) of the undo commit; names the apply commit and the person who undid it.

	`operations` (block items) adds one line per item after the "Phiếu" line; `None` keeps the old text.
	"""
	subject = f"erp_ai: hoàn tác {proposal} ({label})"
	body = (
		f"Đề xuất: {proposal}\n"
		f"Phiếu: {ticket}\n"
		f"{_item_lines(operations)}"
		f"Commit áp dụng: {apply_commit}\n"
		f"Người hoàn tác: {actor}\n"
		f"Commit do {BOT_GIT_NAME} tạo sau khi người hoàn tác bấm Hoàn tác."
	)
	return subject, body


def message_text(subject: str, body: str) -> str:
	"""Full message as stored in `commit_message`: subject, blank line, body."""
	return f"{subject}\n\n{body}"


def _shown(value) -> str:
	"""Field value fit for a note: stripped text; "" when empty or carrying a URL (NFR-8)."""
	text = str(value or "").strip()
	return "" if "://" in text else text


# Verb of each item line of a block's notes; delete and rename in capitals (CHG-002 design 3.7).
_NOTE_VERBS = {**_ITEM_VERBS, CHANGE_OP_DELETE: "XÓA", CHANGE_OP_RENAME: "ĐỔI TÊN"}
_RESTART_ARGV = ["restart"]


def _stored_commands(command_list) -> list[list[str]]:
	"""The argv list stored in `command_list`, read strictly like `block.commands_of` (design 2.3).

	Raises ValueError when the stored value is not a JSON list of argv lists, so the notes never
	show the approver fewer commands than the apply job would read.
	"""
	commands = json.loads(command_list or "[]")
	if not isinstance(commands, list) or not all(isinstance(argv, list) for argv in commands):
		raise ValueError(f"command_list is not a list of argv lists: {command_list!r}")
	return commands


def _block_notes(rows, commands) -> list[str]:
	"""Lines 1-5 of a block's notes (CHG-002 design 3.7): counts, items, commands, restart, undo."""
	rows = sorted(rows or (), key=lambda row: row.get("idx") or 0)
	kinds = [row.get("operation") for row in rows]
	notes = [
		f"Gồm {kinds.count(CHANGE_OP_EDIT)} sửa, {kinds.count(CHANGE_OP_CREATE)} tạo,"
		f" {kinds.count(CHANGE_OP_DELETE)} xóa, {kinds.count(CHANGE_OP_RENAME)} đổi tên;"
		f" {len(commands)} lệnh."
	]
	for row in rows:
		line = f"{_NOTE_VERBS[row.get('operation')]} {row.get('file_path')}"
		if row.get("operation") == CHANGE_OP_RENAME:
			line += f" → {row.get('new_path')}"
		notes.append(line)
	notes.extend(f"lệnh: bench {' '.join(argv)}" for argv in commands)
	if _RESTART_ARGV in commands:
		notes.append("Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).")
	if commands:
		notes.append("Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file.")
	return notes


def proposal_notes(proposal_fields) -> list[str]:
	"""Sentences for the bot comment and the review form (design 3.9; block shape CHG-002 3.7).

	`proposal_fields` is the proposal document or a dict of its fields; only those stored
	fields are read, never git. A sentence whose value is missing or carries a URL is left out.
	A block (child rows or a `command_list`) starts with its counts, items and commands.
	"""
	rows = proposal_fields.get("operations")
	command_list = proposal_fields.get("command_list")
	# same test as `block.is_block` (design 2.3), on a dict or a document
	is_block = bool(rows) or bool(command_list)
	notes = _block_notes(rows, _stored_commands(command_list)) if is_block else []
	is_code = proposal_fields.get("change_kind") == CHANGE_KIND_CODE
	app = _shown(proposal_fields.get("app"))
	branch = _shown(proposal_fields.get("target_branch"))
	upstream_raw = str(proposal_fields.get("upstream_ref") or "").strip()
	upstream = _shown(upstream_raw)
	status = proposal_fields.get("change_status")
	if is_code and branch:
		if app:
			notes.append(f"Commit sẽ vào nhánh {branch} của app {app}.")
		if upstream:
			ahead = int(proposal_fields.get("ahead_count") or 0)
			notes.append(
				f"Nhánh này theo {upstream} và đang đi trước {ahead} commit"
				" (tính theo lần fetch cuối trên máy chủ)."
			)
		elif not upstream_raw:
			notes.append("Nhánh này không theo nhánh remote nào.")
	if proposal_fields.get("is_core_app") and app:
		notes.append(
			f"Cảnh báo app lõi: {app} dùng chung cho mọi site trên bench này, nên thay đổi ảnh hưởng"
			" tất cả các site. bench update không giữ commit local: nó dừng nếu kho có thay đổi chưa"
			" commit; khi kho sạch, nó kéo bằng git pull (merge) từ remote upstream hoặc remote đầu"
			" tiên, có thể tạo merge commit hoặc xung đột; bench update --reset xóa vĩnh viễn commit"
			" chưa đẩy. Đẩy commit lên fork là việc của người, làm trước khi chạy bench update."
		)
	if is_code:
		apply_commit = _shown(proposal_fields.get("apply_commit_sha"))
		undo_commit = _shown(proposal_fields.get("undo_commit_sha"))
		if status == CHANGE_STATUS_APPLIED and apply_commit:
			notes.append(f"Commit áp dụng: {apply_commit}.")
		elif status == CHANGE_STATUS_UNDONE and undo_commit:
			notes.append(f"Commit hoàn tác: {undo_commit}.")
		if not is_block and str(proposal_fields.get("file_path") or "").endswith(".py"):
			notes.append("Sau khi áp dụng cần người chạy bench restart.")
	elif not is_block and proposal_fields.get("change_kind") == CHANGE_KIND_COMMAND:
		notes.append("Lệnh bench không hoàn tác được.")
	return notes
