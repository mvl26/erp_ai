"""Reads a proposal as a block (CHG-002 design 2.3): its file items in `idx` order and its bench commands.

A block proposal has child rows or a `command_list`; the reading of a single-file proposal of the old
shape comes with task T18.
"""

import json

from erp_ai.agent.tools.change_guard import FileOp
from erp_ai.constants import CHANGE_OP_CREATE, CHANGE_OP_DELETE


def is_block(doc) -> bool:
	return bool(doc.get("operations")) or bool(doc.get("command_list"))


def operations_of(doc) -> tuple[FileOp, ...]:
	"""The child rows as `FileOp`, in `idx` order; a created file has no `before`, a deleted one no `after`."""
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


def commands_of(doc) -> list[list[str]]:
	"""The approved argv list of `command_list`, in order; `[]` when the block has no command."""
	return json.loads(doc.get("command_list") or "[]")
