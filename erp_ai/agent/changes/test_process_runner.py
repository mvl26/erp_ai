import subprocess
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import process_runner
from erp_ai.agent.changes.process_runner import (
	ENV_ALLOWLIST,
	OUTPUT_MAX_LINES,
	CommandResult,
	run_bench,
)

RUN_PATH = "erp_ai.agent.changes.process_runner.subprocess.run"
CLOCK_PATH = "erp_ai.agent.changes.process_runner.time.monotonic"
BENCH_PATH = "erp_ai.agent.changes.process_runner.frappe.utils.get_bench_path"
FAKE_BENCH = "/srv/fake-bench"
ARGS = ["--site", "miyano", "migrate"]


def completed(returncode=0, stdout=""):
	return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestProcessRunner(FrappeTestCase):
	def setUp(self):
		patcher = patch(BENCH_PATH, return_value=FAKE_BENCH)
		patcher.start()
		self.addCleanup(patcher.stop)

	def _run(self, result, limit_s=120, elapsed_s=1.0, args=ARGS):
		effect = result if isinstance(result, BaseException) else None
		value = None if effect else result
		with (
			patch(RUN_PATH, return_value=value, side_effect=effect) as run,
			patch(CLOCK_PATH, side_effect=[1000.0, 1000.0 + elapsed_s]),
		):
			outcome = run_bench(args, limit_s)
		return outcome, run

	def test_constants(self):
		self.assertEqual(ENV_ALLOWLIST, ("PATH", "HOME", "LANG", "LC_ALL", "USER"))
		self.assertEqual(OUTPUT_MAX_LINES, 400)

	def test_output_cut_to_400_lines(self):
		lines = [f"line {n}" for n in range(1, 1001)]
		outcome, _run = self._run(completed(0, "\n".join(lines) + "\n"))
		kept = outcome.output.split("\n")
		self.assertEqual(len(kept), 400)
		self.assertEqual(kept[0], "… đã cắt 601 dòng đầu")
		self.assertEqual(kept[1], "line 602")
		self.assertEqual(kept[-1], "line 1000")

		exact = "\n".join(f"line {n}" for n in range(1, 401))
		outcome, _run = self._run(completed(0, exact))
		self.assertEqual(outcome.output, exact)

		one_over = "\n".join(f"line {n}" for n in range(1, 402))
		outcome, _run = self._run(completed(0, one_over))
		kept = outcome.output.split("\n")
		self.assertEqual(len(kept), 400)
		self.assertEqual(kept[0], "… đã cắt 2 dòng đầu")
		self.assertEqual(kept[1], "line 3")

		outcome, _run = self._run(completed(0, "a" * 5000 + "\nshort"))
		self.assertEqual(outcome.output, "a" * 1000 + "\nshort")
		outcome, _run = self._run(completed(0, "b" * 1000))
		self.assertEqual(outcome.output, "b" * 1000)

		outcome, _run = self._run(completed(0, None))
		self.assertEqual(outcome.output, "")

	def test_output_cut_after_backstop_timeout(self):
		raw = "\n".join(f"line {n}" for n in range(1, 1001)).encode("utf-8") + b"\xff"
		expired = subprocess.TimeoutExpired(cmd=["timeout"], timeout=150, output=raw)
		outcome, _run = self._run(expired)
		kept = outcome.output.split("\n")
		self.assertEqual(len(kept), 400)
		self.assertEqual(kept[0], "… đã cắt 601 dòng đầu")
		self.assertEqual(kept[-1], "line 1000�")

	def test_limit_comes_from_deadline_and_kills_group(self):
		outcome, run = self._run(completed(0, "ok"), limit_s=123, elapsed_s=2.5)
		run.assert_called_once()
		self.assertEqual(
			run.call_args.args[0],
			["timeout", "-s", "KILL", "123", "bench", "--site", "miyano", "migrate"],
		)
		kwargs = run.call_args.kwargs
		self.assertEqual(
			set(kwargs),
			{
				"cwd",
				"env",
				"stdin",
				"stdout",
				"stderr",
				"text",
				"encoding",
				"errors",
				"timeout",
				"start_new_session",
			},
		)
		self.assertEqual(kwargs["cwd"], FAKE_BENCH)
		self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
		self.assertIs(kwargs["stdout"], subprocess.PIPE)
		self.assertIs(kwargs["stderr"], subprocess.STDOUT)
		self.assertIs(kwargs["text"], True)
		self.assertEqual(kwargs["encoding"], "utf-8")
		self.assertEqual(kwargs["errors"], "replace")
		self.assertEqual(kwargs["timeout"], 153)
		self.assertIs(kwargs["start_new_session"], True)
		self.assertEqual(
			outcome,
			CommandResult(exit_code=0, output="ok", duration_ms=2500, timed_out=False, not_found=False),
		)

		_outcome, run = self._run(completed(0), limit_s=540)
		self.assertEqual(run.call_args.args[0][3], "540")
		self.assertEqual(run.call_args.kwargs["timeout"], 570)
		_outcome, run = self._run(completed(0), limit_s=1)
		self.assertEqual(run.call_args.args[0][3], "1")
		self.assertEqual(run.call_args.kwargs["timeout"], 31)

	def test_killed_after_limit_is_timed_out(self):
		for returncode in (-9, 124, 137):
			for elapsed_s in (120.0, 121.5):
				with self.subTest(returncode=returncode, elapsed_s=elapsed_s):
					outcome, _run = self._run(completed(returncode, "x"), limit_s=120, elapsed_s=elapsed_s)
					self.assertIs(outcome.timed_out, True)
					self.assertEqual(outcome.exit_code, returncode)
					self.assertIs(outcome.not_found, False)

	def test_killed_before_limit_is_not_timed_out(self):
		for returncode in (-9, 124, 137):
			with self.subTest(returncode=returncode):
				outcome, _run = self._run(completed(returncode, "x"), limit_s=120, elapsed_s=119.9)
				self.assertIs(outcome.timed_out, False)
				self.assertEqual(outcome.exit_code, returncode)

	def test_other_exit_after_limit_is_not_timed_out(self):
		for returncode in (0, 1, 2, -15, 125, 127):
			with self.subTest(returncode=returncode):
				outcome, _run = self._run(completed(returncode), limit_s=120, elapsed_s=300.0)
				self.assertIs(outcome.timed_out, False)

	def test_backstop_timeout_expired_is_timed_out(self):
		expired = subprocess.TimeoutExpired(cmd=["timeout"], timeout=150, output=None)
		outcome, _run = self._run(expired, limit_s=120, elapsed_s=150.0)
		self.assertEqual(
			outcome,
			CommandResult(exit_code=None, output="", duration_ms=150000, timed_out=True, not_found=False),
		)

	def test_env_is_allowlist_only(self):
		full = {
			"PATH": "/usr/bin:/bin",
			"HOME": "/home/frappe",
			"LANG": "C.UTF-8",
			"LC_ALL": "C.UTF-8",
			"USER": "frappe",
			"OPENAI_API_KEY": "sk-fake-never-leak",
			"PYTHONPATH": "/tmp/evil",
			"GIT_DIR": "/tmp/repo",
			"FRAPPE_SITE": "miyano",
		}
		with patch.dict(process_runner.os.environ, full, clear=True):
			_outcome, run = self._run(completed(0))
		self.assertEqual(
			run.call_args.kwargs["env"],
			{
				"PATH": "/usr/bin:/bin",
				"HOME": "/home/frappe",
				"LANG": "C.UTF-8",
				"LC_ALL": "C.UTF-8",
				"USER": "frappe",
			},
		)
		with patch.dict(process_runner.os.environ, {"PATH": "/bin", "SECRET": "x"}, clear=True):
			_outcome, run = self._run(completed(0))
		self.assertEqual(run.call_args.kwargs["env"], {"PATH": "/bin"})

	def test_exit_127_is_not_found(self):
		outcome, _run = self._run(completed(127, "bench: command not found"))
		self.assertEqual(
			outcome,
			CommandResult(
				exit_code=127,
				output="bench: command not found",
				duration_ms=1000,
				timed_out=False,
				not_found=True,
			),
		)
		for returncode in (0, 1, 126, 128):
			with self.subTest(returncode=returncode):
				outcome, _run = self._run(completed(returncode))
				self.assertIs(outcome.not_found, False)

	def test_missing_timeout_executable_is_not_found(self):
		outcome, _run = self._run(FileNotFoundError(2, "No such file", "timeout"))
		self.assertEqual(
			outcome,
			CommandResult(exit_code=None, output="", duration_ms=1000, timed_out=False, not_found=True),
		)

	def test_bad_input_never_reaches_argv(self):
		cases = (
			("args not a list", ("migrate",), 120),
			("args empty", [], 120),
			("arg not a string", ["migrate", 1], 120),
			("arg with NUL", ["mig\0rate"], 120),
			("limit zero", ARGS, 0),
			("limit negative", ARGS, -1),
			("limit above COMMAND_TIMEOUT_S", ARGS, 541),
			("limit not int", ARGS, 120.0),
			("limit bool", ARGS, True),
		)
		for label, args, limit_s in cases:
			with self.subTest(label), patch(RUN_PATH) as run:
				with self.assertRaises(ValueError):
					run_bench(args, limit_s)
				run.assert_not_called()
