"""The child side of an approved console script (CHG-010).

The change job runs `bench --site <site> execute erp_ai.console_entry.run` with the script on stdin
(`process_runner.run_console`). `bench execute` connects as Administrator, calls `run` and commits only when
it returns normally; this module never commits. Any error rolls the whole script back and ends the process
with exit code 1, so the script is one transaction that is kept whole or not at all.
"""

import sys
import traceback

import frappe

from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import change_guard

TRACEBACK_MAX_LINES = 20
SCRIPT_FILENAME = "<console>"
SCRIPT_MODULE_NAME = "__console__"


def execute_script(script: str) -> None:
	"""Run `script` once with `frappe` in its globals, as `bench console` would.

	The script rules run again first: the child trusts no stored text.

	Raises:
		ValueError: the script rules refuse `script`; the message is the refusal reason.
		Whatever the script itself raises.
	"""
	reason = change_guard.check_console_script(script)
	if reason:
		raise ValueError(reason)
	exec(compile(script, SCRIPT_FILENAME, "exec"), {"frappe": frappe, "__name__": SCRIPT_MODULE_NAME})


def run() -> None:
	"""Entry of `bench execute`: read the script from stdin and run it once.

	Returns normally only when the script ran to its end, so `bench execute` commits. Anything else the
	script raises, `SystemExit` included (an early exit must not read as success), rolls everything back,
	prints the last `TRACEBACK_MAX_LINES` lines of the traceback with secrets masked and exits with code 1.
	`SystemExit` is not an `Exception`, so `bench execute` neither commits nor calls the method again.
	"""
	try:
		execute_script(sys.stdin.read())
	except BaseException:
		frappe.db.rollback()
		lines = traceback.format_exc().splitlines()[-TRACEBACK_MAX_LINES:]
		print(redact_secrets("\n".join(lines)))
		raise SystemExit(1) from None
