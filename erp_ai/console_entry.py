"""The child side of an approved console script (CHG-010).

The change job runs `bench --site <site> execute erp_ai.console_entry.run` with the script on stdin
(`process_runner.run_console`). `bench execute` connects as Administrator, calls `run` and commits only when
it returns normally; this module never commits, and while the script runs no statement sent through
`frappe.db.sql` may open or end a transaction. Any error rolls the whole script back and ends the process
with exit code 1, so the script is one transaction that is kept whole or not at all.
"""

import re
import sys
import traceback
from contextlib import contextmanager

import frappe

from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import change_guard

TRACEBACK_MAX_LINES = 20
SCRIPT_FILENAME = "<console>"
SCRIPT_MODULE_NAME = "__console__"
STDIN_ENCODING = "utf-8"  # `process_runner.run_console` always writes the script as UTF-8
TRANSACTION_REFUSED = "script không được tự mở hoặc kết thúc giao dịch"
# MySQL/MariaDB run the text of an executable comment (`/*!50000 …*/`, `/*M!100000 …*/`): only its opener is
# dropped before the first keyword is read.
EXECUTABLE_COMMENT_OPENER = re.compile(r"/\*M?!\d*", re.IGNORECASE)
# The first keyword of a statement that opens or ends a transaction. `ROLLBACK [WORK] TO …` goes back to a
# savepoint and is allowed; a SET that names autocommit anywhere is refused.
TRANSACTION_KEYWORD = re.compile(
	r"(?:commit|rollback(?!\s+(?:work\s+)?to\b)|start\s+transaction|begin|set\b.*\bautocommit)\b",
	re.IGNORECASE | re.DOTALL,
)


def _statement_start(query: str) -> str:
	"""`query` from its first keyword on: leading whitespace and comments are dropped as the server skips
	them ("" when nothing but comments is left)."""
	text = query
	while True:
		text = text.lstrip()
		opener = EXECUTABLE_COMMENT_OPENER.match(text)
		if opener:
			text = text[opener.end() :]
		elif text.startswith("/*"):
			end = text.find("*/", 2)
			if end == -1:
				return ""
			text = text[end + 2 :]
		elif text.startswith(("--", "#")):
			newline = text.find("\n")
			if newline == -1:
				return ""
			text = text[newline + 1 :]
		else:
			return text


def is_transaction_statement(query) -> bool:
	"""True when `query` (as `frappe.db.sql` turns it into text) starts a transaction, ends one or sets
	autocommit."""
	return bool(TRANSACTION_KEYWORD.match(_statement_start(str(query))))


@contextmanager
def _no_transaction_statements():
	"""While the block runs, `frappe.db.sql` refuses a transaction statement with `TRANSACTION_REFUSED`
	(`frappe.db.commit`, `rollback` and `begin` send theirs through it too); the connection's own `sql` is
	back when the block ends, before `run` rolls back or `bench execute` commits."""
	db = frappe.local.db
	own = vars(db).get("sql")
	original = db.sql

	def guarded_sql(query, *args, **kwargs):
		if is_transaction_statement(query):
			raise frappe.PermissionError(TRANSACTION_REFUSED)
		return original(query, *args, **kwargs)

	db.sql = guarded_sql
	try:
		yield
	finally:
		if own is None:
			del db.sql
		else:
			db.sql = own


def execute_script(script: str) -> None:
	"""Run `script` once with `frappe` in its globals, as `bench console` would, with no transaction statement
	allowed while it runs.

	The script rules run again first: the child trusts no stored text.

	Raises:
		ValueError: the script rules refuse `script`; the message is the refusal reason.
		frappe.PermissionError: the script sent a transaction statement (`TRANSACTION_REFUSED`).
		Whatever the script itself raises.
	"""
	reason = change_guard.check_console_script(script)
	if reason:
		raise ValueError(reason)
	code = compile(script, SCRIPT_FILENAME, "exec")
	with _no_transaction_statements():
		exec(code, {"frappe": frappe, "__name__": SCRIPT_MODULE_NAME})


def run() -> None:
	"""Entry of `bench execute`: read the script from stdin as UTF-8 bytes and run it once.

	Returns normally only when the script ran to its end, so `bench execute` commits. Anything else the
	script raises, `SystemExit` included (an early exit must not read as success), rolls everything back,
	prints the last `TRACEBACK_MAX_LINES` lines of the traceback with secrets masked and exits with code 1.
	`SystemExit` is not an `Exception`, so `bench execute` neither commits nor calls the method again.
	"""
	try:
		execute_script(sys.stdin.buffer.read().decode(STDIN_ENCODING))
	except BaseException:
		frappe.db.rollback()
		lines = traceback.format_exc().splitlines()[-TRACEBACK_MAX_LINES:]
		print(redact_secrets("\n".join(lines)))
		raise SystemExit(1) from None
