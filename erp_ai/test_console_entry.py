"""CHG-010 Task 5: the child side of an approved console script (`bench execute erp_ai.console_entry.run`)."""

import io
import os
from contextlib import redirect_stdout
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import console_entry
from erp_ai.agent.changes import process_runner
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import change_guard

REFUSED_SCRIPT = "frappe.db.commit()\n"
SECRET_SCRIPT = "raise ValueError('password=hunter2 sk-ant-abc123def456ghi789')\n"
PROBE_KEY = "erp_ai_console_rollback_probe"


class TestExecuteScript(FrappeTestCase):
	def test_runs_the_script_and_prints(self):
		printed = io.StringIO()
		with redirect_stdout(printed):
			console_entry.execute_script("print(1+1)")
		self.assertEqual(printed.getvalue(), "2\n")

	def test_script_sees_frappe_and_its_own_name(self):
		printed = io.StringIO()
		with redirect_stdout(printed):
			console_entry.execute_script("print(__name__)\nprint(frappe.local.site)\n")
		self.assertEqual(printed.getvalue(), f"__console__\n{frappe.local.site}\n")

	def test_refused_script_raises_the_guard_reason_and_never_runs(self):
		reason = change_guard.check_console_script(REFUSED_SCRIPT)
		self.assertEqual(reason, change_guard.CONSOLE_ATTR.format(name="commit"))
		with patch.object(frappe.db, "commit") as commit, self.assertRaises(ValueError) as caught:
			console_entry.execute_script(REFUSED_SCRIPT)
		self.assertEqual(str(caught.exception), reason)
		commit.assert_not_called()


class TestRun(FrappeTestCase):
	def run_entry(self, script: str):
		"""`run()` with `script` on stdin: (the SystemExit raised or None, printed text, rollback, commit)."""
		printed = io.StringIO()
		raised = None
		with (
			patch("sys.stdin", io.StringIO(script)),
			redirect_stdout(printed),
			patch.object(frappe.db, "rollback") as rollback,
			patch.object(frappe.db, "commit") as commit,
		):
			try:
				console_entry.run()
			except SystemExit as error:
				raised = error
		return raised, printed.getvalue(), rollback, commit

	def assert_failed(self, raised, rollback, commit):
		self.assertIsNotNone(raised)
		self.assertEqual(raised.code, 1)
		rollback.assert_called_once_with()
		commit.assert_not_called()

	def test_error_rolls_back_prints_and_exits_1(self):
		raised, printed, rollback, commit = self.run_entry("raise ValueError('boom')")
		self.assert_failed(raised, rollback, commit)
		self.assertIn("ValueError", printed)
		self.assertIn("boom", printed)

	def test_success_returns_and_never_commits(self):
		raised, printed, rollback, commit = self.run_entry("print('xong')\n")
		self.assertIsNone(raised)
		self.assertEqual(printed, "xong\n")
		# `bench execute` commits after a normal return; the child never does it itself.
		commit.assert_not_called()
		rollback.assert_not_called()

	def test_refused_script_exits_1_with_its_reason(self):
		raised, printed, rollback, commit = self.run_entry(REFUSED_SCRIPT)
		self.assert_failed(raised, rollback, commit)
		self.assertIn(change_guard.CONSOLE_ATTR.format(name="commit"), printed)

	def test_script_exit_is_an_error_too(self):
		# A script that leaves through SystemExit did not finish: nothing is kept and the job must see an error.
		for script in ("raise SystemExit(0)\n", "raise SystemExit\n"):
			with self.subTest(script=script):
				raised, printed, rollback, commit = self.run_entry(script)
				self.assert_failed(raised, rollback, commit)
				self.assertIn("SystemExit", printed)

	def test_printed_traceback_is_masked(self):
		raised, printed, rollback, commit = self.run_entry(SECRET_SCRIPT)
		self.assert_failed(raised, rollback, commit)
		self.assertIn(MASK, printed)
		self.assertNotIn("hunter2", printed)
		self.assertNotIn("sk-ant-abc123def456ghi789", printed)

	def test_printed_traceback_keeps_its_last_20_lines(self):
		raised, printed, rollback, commit = self.run_entry(
			"raise ValueError('\\n'.join(str(n) for n in range(50)))\n"
		)
		self.assert_failed(raised, rollback, commit)
		self.assertEqual(printed.splitlines(), [str(n) for n in range(30, 50)])


class TestRunConsoleChild(FrappeTestCase):
	"""The real child process through `process_runner.run_console`."""

	def setUp(self):
		minimal_env = process_runner._minimal_env

		def with_this_checkout():
			# The child imports erp_ai through the bench environment; wt-test.sh points PYTHONPATH at the
			# checkout under test, which the env allowlist drops. ENV_ALLOWLIST itself stays as it is.
			return {**minimal_env(), "PYTHONPATH": os.environ.get("PYTHONPATH", "")}

		patcher = patch.object(process_runner, "_minimal_env", side_effect=with_this_checkout)
		patcher.start()
		self.addCleanup(patcher.stop)

	def run_child(self, script: str):
		return process_runner.run_console(script, frappe.local.site, 120)

	def test_child_runs_the_script_and_exits_0(self):
		result = self.run_child("print(6*7)")
		self.assertEqual(result.exit_code, 0, result.output)
		self.assertIn("42", result.output)

	def test_child_error_exits_1_with_the_traceback(self):
		result = self.run_child("raise ValueError('x')")
		self.assertEqual(result.exit_code, 1, result.output)
		self.assertIn("ValueError", result.output)

	def test_child_error_after_a_write_saves_nothing(self):
		result = self.run_child(
			f"frappe.db.set_default({PROBE_KEY!r}, 'x')\nraise ValueError('sau khi ghi')\n"
		)
		self.assertEqual(result.exit_code, 1, result.output)
		self.assertIn("ValueError", result.output)
		# A new connection reads the committed rows only.
		check = self.run_child(
			f"print('probe=' + repr(frappe.db.sql('select defvalue from `tabDefaultValue` where defkey=%s', {PROBE_KEY!r})))\n"
		)
		self.assertEqual(check.exit_code, 0, check.output)
		if "probe=()" not in check.output:
			self.addCleanup(
				self.run_child,
				f"frappe.db.sql('delete from `tabDefaultValue` where defkey=%s', {PROBE_KEY!r})\n",
			)
		self.assertIn("probe=()", check.output)
