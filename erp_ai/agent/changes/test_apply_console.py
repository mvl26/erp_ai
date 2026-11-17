"""CHG-010 Task 5: the change job runs an approved console script once, through `process_runner.run_console`."""

import json
import subprocess
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent

from erp_ai.agent import policy
from erp_ai.agent.changes import apply_job, process_runner, transitions
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import change_guard
from erp_ai.constants import (
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_FAILED,
	COMMAND_TIMEOUT_S,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.test_utils import (
	keep_agent_settings,
	make_block_proposal,
	make_change_proposal,
	pin_agent_roles,
	set_agent_settings,
)

ACTOR = "console.instructor@example.com"
SCRIPT = "for name in frappe.get_all('ToDo', pluck='name', limit=1):\n\tprint(name)\n"
REFUSED_SCRIPT = "frappe.db.commit()\n"
# Written by hand so a changed constant cannot hide a changed sentence.
CONSOLE_SWITCH_OFF_TEXT = "công tắc chạy bench console đã tắt"
CONSOLE_PREFIX_TEXT = "script console: "
SECRET_OUTPUT = "password=hunter2 sk-ant-abc123def456ghi789"
SECRETS = ("hunter2", "sk-ant-abc123def456ghi789")


def _result(exit_code=0, output="xong", duration_ms=1234, timed_out=False, not_found=False):
	return process_runner.CommandResult(
		exit_code=exit_code, output=output, duration_ms=duration_ms, timed_out=timed_out, not_found=not_found
	)


class _LateClock:
	"""A `time` stand-in for `apply_job`: 1000 at the job's start, then half a second before its deadline."""

	def __init__(self):
		self.calls = 0

	def monotonic(self):
		self.calls += 1
		return 1000.0 if self.calls == 1 else 1000.0 + COMMAND_TIMEOUT_S - 0.5


class ConsoleApplyTestCase(FrappeTestCase):
	"""An approver, the console switch on and the code switch off."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		pin_agent_roles(self)
		keep_agent_settings(self)
		# The job commits its state; inside a test nothing may reach the real database for good.
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		log_error = patch.object(frappe, "log_error")
		log_error.start()
		self.addCleanup(log_error.stop)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(ACTOR)
		frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)
		self.site = frappe.local.site
		set_agent_settings(code_change_enabled=0, console_enabled=1)

	def console(self, script=SCRIPT):
		"""An approved console proposal (approved by ACTOR) holding `script`."""
		doc = make_change_proposal(
			CHANGE_KIND_COMMAND,
			command_args=None,
			app=None,
			command_list=json.dumps([change_guard.console_args(self.site)]),
			content_after=script,
		)
		transitions.approve(doc.name, ACTOR)
		return doc.name

	def refresh_digest(self, name):
		digest = transitions.content_digest(frappe.get_doc(PROPOSAL_DOCTYPE, name))
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, "approved_digest", digest, update_modified=False)

	def run_apply(self, name, result=None, user=ACTOR):
		"""Run the apply job as `user` with `run_console` stubbed; returns (run_console mock, subprocess.run spy)."""
		frappe.set_user(user)
		try:
			with (
				patch.object(
					apply_job.process_runner, "run_console", return_value=result or _result()
				) as run_console,
				patch("subprocess.run", wraps=subprocess.run) as run,
			):
				apply_job.run_change(name, "apply")
		finally:
			frappe.set_user("Administrator")
		return run_console, run

	def state(self, name):
		row = frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			[
				"change_status",
				"failure_reason",
				"exit_code",
				"duration_ms",
				"command_output",
				"command_results",
			],
			as_dict=True,
		)
		row.command_results = json.loads(row.command_results or "null")
		return row

	def last_log_after(self, name):
		"""`(change_step, value_after)` of the one log row the job's end wrote."""
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name, "change_step": ("in", ["apply", "fail"])},
			fields=["change_step", "value_after"],
		)
		self.assertEqual(len(rows), 1, rows)
		return rows[0].change_step, json.loads(rows[0].value_after or "null")

	def entry(self, exit_code=0, duration_ms=1234, output="xong", timed_out=False):
		return {
			"args": ["--site", self.site, "console"],
			"exit_code": exit_code,
			"duration_ms": duration_ms,
			"timed_out": timed_out,
			"output": output,
		}

	def assert_refused(self, name, reason, run_console, run):
		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, reason))
		# The child process never starts.
		run_console.assert_not_called()
		run.assert_not_called()


class TestApplyConsole(ConsoleApplyTestCase):
	def test_constants(self):
		self.assertEqual(apply_job.CONSOLE_SWITCH_OFF, CONSOLE_SWITCH_OFF_TEXT)

	def test_approved_script_runs_once_with_code_change_off(self):
		name = self.console()
		with patch.object(
			apply_job.policy, "current_change_settings", wraps=policy.current_change_settings
		) as code_switch:
			run_console, _run = self.run_apply(name, _result(output="xong", duration_ms=4321))

		# The code switch is never read on the console path.
		code_switch.assert_not_called()
		run_console.assert_called_once()
		script, site, limit_s = run_console.call_args.args
		self.assertEqual((script, site), (SCRIPT, self.site))
		self.assertIsInstance(limit_s, int)
		self.assertTrue(1 <= limit_s <= COMMAND_TIMEOUT_S, limit_s)
		state = self.state(name)
		self.assertEqual((state.change_status, state.failure_reason), (CHANGE_STATUS_APPLIED, None))
		self.assertEqual((state.exit_code, state.duration_ms, state.command_output), (0, 4321, "xong"))
		self.assertEqual(state.command_results, [self.entry(duration_ms=4321)])
		self.assertEqual(
			self.last_log_after(name), ("apply", {"exit_code": 0, "duration_ms": 4321, "output": "xong"})
		)

	def test_console_switch_off_after_approval_stops_before_the_child(self):
		name = self.console()
		set_agent_settings(console_enabled=0)

		run_console, run = self.run_apply(name)

		self.assert_refused(name, CONSOLE_SWITCH_OFF_TEXT, run_console, run)

	def test_script_edited_after_approval_refused(self):
		name = self.console()
		frappe.db.sql(
			"update `tabERP AI Change Proposal` set content_after=%s where name=%s", ("print(2)\n", name)
		)

		run_console, run = self.run_apply(name)

		self.assert_refused(name, apply_job.DIGEST_CHANGED, run_console, run)

	def test_runner_role_script_and_site_rechecked(self):
		def wrong_runner(name):
			return "Administrator"

		def lost_role(name):
			frappe.get_doc("User", ACTOR).remove_roles(ROLE_INSTRUCTOR)
			return ACTOR

		def refused_script(name):
			frappe.db.set_value(
				PROPOSAL_DOCTYPE, name, "content_after", REFUSED_SCRIPT, update_modified=False
			)
			self.refresh_digest(name)
			return ACTOR

		def other_site(name):
			commands = json.dumps([change_guard.console_args("other.example.com")])
			frappe.db.set_value(PROPOSAL_DOCTYPE, name, "command_list", commands, update_modified=False)
			self.refresh_digest(name)
			return ACTOR

		cases = (
			("wrong runner", wrong_runner, apply_job.WRONG_RUNNER),
			("approver lost the role", lost_role, apply_job.APPROVER_LOST_ROLE),
			("refused script", refused_script, change_guard.CONSOLE_ATTR.format(name="commit")),
			("other site", other_site, change_guard.CMD_OTHER_SITE),
		)
		for label, prepare, reason in cases:
			with self.subTest(label):
				name = self.console()
				user = prepare(name)

				run_console, run = self.run_apply(name, user=user)

				self.assert_refused(name, reason, run_console, run)
				frappe.get_doc("User", ACTOR).add_roles(ROLE_INSTRUCTOR)

	def test_nonzero_exit_failed_with_the_console_prefix(self):
		name = self.console()

		self.run_apply(name, _result(exit_code=1, output="ValueError: x", duration_ms=77))

		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason),
			(CHANGE_STATUS_FAILED, CONSOLE_PREFIX_TEXT + apply_job.COMMAND_FAILED.format(1)),
		)
		self.assertTrue(state.failure_reason.startswith(CONSOLE_PREFIX_TEXT))
		self.assertEqual((state.exit_code, state.duration_ms, state.command_output), (1, 77, "ValueError: x"))
		self.assertEqual(
			state.command_results, [self.entry(exit_code=1, duration_ms=77, output="ValueError: x")]
		)

	def test_timeout_and_missing_bench_failed_with_the_console_prefix(self):
		cases = (
			("timed out", _result(exit_code=None, timed_out=True), apply_job.COMMAND_OUT_OF_TIME),
			("bench missing", _result(exit_code=None, not_found=True), apply_job.COMMAND_NOT_FOUND),
		)
		for label, result, reason in cases:
			with self.subTest(label):
				name = self.console()

				# The result line refuses a result with no exit code that did not time out (block rule P7-6)
				# and rolls back; with commit stubbed that rollback would drop this test's proposal.
				with patch.object(apply_job, "_post_result", return_value="-"):
					run_console, _run = self.run_apply(name, result)

				run_console.assert_called_once()
				state = self.state(name)
				self.assertEqual(
					(state.change_status, state.failure_reason),
					(CHANGE_STATUS_FAILED, CONSOLE_PREFIX_TEXT + reason),
				)

	def test_under_one_second_left_the_child_never_starts(self):
		name = self.console()

		with patch.object(apply_job, "time", _LateClock()):
			run_console, run = self.run_apply(name)

		self.assert_refused(name, CONSOLE_PREFIX_TEXT + apply_job.COMMAND_OUT_OF_TIME, run_console, run)
		state = self.state(name)
		self.assertEqual(
			state.command_results, [self.entry(exit_code=None, duration_ms=0, output="", timed_out=True)]
		)

	def test_secrets_in_the_output_are_masked_wherever_stored(self):
		for label, exit_code in (("applied", 0), ("failed", 1)):
			with self.subTest(label):
				name = self.console()

				self.run_apply(name, _result(exit_code=exit_code, output=SECRET_OUTPUT))

				state = self.state(name)
				_step, logged = self.last_log_after(name)
				stored = (state.command_output, state.command_results[0]["output"], logged["output"])
				for text in stored:
					self.assertIn(MASK, text)
					for secret in SECRETS:
						self.assertNotIn(secret, text)

	def test_undo_of_an_applied_console_proposal_refused(self):
		name = self.console()
		self.run_apply(name)
		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

		with self.assertRaises(transitions.InvalidTransition):
			transitions.request_undo(name, ACTOR)

		self.assertEqual(self.state(name).change_status, CHANGE_STATUS_APPLIED)

	def test_other_bench_commands_still_need_the_code_switch(self):
		name = make_block_proposal([], [["--site", self.site, "migrate"]]).name
		transitions.approve(name, ACTOR)

		with patch.object(apply_job.process_runner, "run_bench") as run_bench:
			run_console, _run = self.run_apply(name)

		state = self.state(name)
		self.assertEqual(
			(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, apply_job.SWITCH_OFF)
		)
		run_bench.assert_not_called()
		run_console.assert_not_called()
