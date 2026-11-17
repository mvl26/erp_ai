"""Reads a proposal as a block (CHG-002 design 2.3): its file items in `idx` order and its bench commands.

A block proposal has child rows or a `command_list`; a proposal of the old shape (scalar fields only) is
read in memory as a block of at most one file item or one command, never migrated.
"""

import json

from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CONSOLE_COMMAND,
)


def is_block(doc) -> bool:
	return bool(doc.get("operations")) or bool(doc.get("command_list"))


def require_code_kind(doc) -> None:
	"""Raises ValueError unless `change_kind` is one of the two kinds of the code path (A3 RQ-5)."""
	if doc.get("change_kind") not in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
		raise ValueError(f"change_kind không hỗ trợ ở đường code: {doc.get('change_kind')!r}")


def operations_of(doc) -> tuple[FileOp, ...]:
	"""The file items as `FileOp`; a created file has no `before`, a deleted one no `after`.

	A block gives its child rows in `idx` order. The old shape gives one `Sửa` (or `Tạo` when
	`is_new_file`) from its scalar fields for a file change, and `()` for a bench command.

	Raises:
		ValueError: `change_kind` is neither a file change nor a bench command.
	"""
	require_code_kind(doc)
	if not is_block(doc):
		return _legacy_operations(doc)
	rows = sorted(doc.get("operations") or [], key=lambda row: row.idx)
	return tuple(
		FileOp(
			kind=row.operation,
			path=row.file_path,
			new_path=row.new_path or None,
			before=None if row.operation == CHANGE_OP_CREATE else row.content_before or "",
			after=None if row.operation == CHANGE_OP_DELETE else row.content_after or "",
			base_hash=row.base_hash or None,
			after_hash=row.after_hash or None,
		)
		for row in rows
	)


def _legacy_operations(doc) -> tuple[FileOp, ...]:
	if doc.get("change_kind") != CHANGE_KIND_CODE:
		return ()
	new_file = bool(doc.get("is_new_file"))
	return (
		FileOp(
			kind=CHANGE_OP_CREATE if new_file else CHANGE_OP_EDIT,
			path=doc.get("file_path") or "",
			new_path=None,
			before=None if new_file else doc.get("content_before") or "",
			after=doc.get("content_after") or "",
			base_hash=doc.get("base_hash") or None,
			after_hash=doc.get("after_hash") or None,
		),
	)


def commands_of(doc) -> list[list[str]]:
	"""The approved argv list, in order; `[]` when there is no command.

	A block reads its `command_list`; the old shape gives `[command_args]` for a bench command with
	stored arguments, else `[]`.

	Raises:
		ValueError: `change_kind` is neither a file change nor a bench command.
	"""
	require_code_kind(doc)
	if is_block(doc):
		return json.loads(doc.get("command_list") or "[]")
	if doc.get("change_kind") != CHANGE_KIND_COMMAND or not doc.get("command_args"):
		return []
	return [json.loads(doc.get("command_args"))]


def is_console(doc) -> bool:
	"""True for a console proposal (CHG-010): a bench command whose only command is `--site <site> console`."""
	if doc.get("change_kind") != CHANGE_KIND_COMMAND or operations_of(doc):
		return False
	commands = commands_of(doc)
	return (
		len(commands) == 1
		and len(commands[0]) == 3
		and commands[0][0] == "--site"
		and commands[0][2] == CONSOLE_COMMAND
	)
