import os
import subprocess
import tempfile
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import file_writer, process_runner
from erp_ai.agent.changes.process_runner import (
	ENV_ALLOWLIST,
	OUTPUT_MAX_LINES,
	CommandResult,
	run_bench,
)
from erp_ai.agent.tools import source
from erp_ai.test_utils import GitSandbox

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


REL = "helpdesk/api/ticket.py"
SUBJECT = "fix(helpdesk): sửa lỗi phiếu (AICHG-00001)"
BODY = "Đề xuất: AICHG-00001\nNgười duyệt: Nguyễn Văn A"
GLOBAL_OPTIONS = [
	"--no-pager",
	"-c",
	f"core.hooksPath={source.GIT_HOOKS_DIR}",
	"-c",
	"core.fsmonitor=false",
	"-c",
	"maintenance.auto=false",
	"-c",
	"gc.auto=0",
]
GIT_WRITES = ("git_add_new", "git_commit_only", "git_unstage_new")


class TestGitWrites(FrappeTestCase):
	def setUp(self):
		folder = tempfile.TemporaryDirectory()
		self.addCleanup(folder.cleanup)
		self.repo = folder.name

	def _call(self, function, repo=None, rel=REL, limit_s=20, subject=SUBJECT, body=BODY):
		repo = self.repo if repo is None else repo
		if function == "git_commit_only":
			return process_runner.git_commit_only(repo, rel, subject, body, limit_s)
		return getattr(process_runner, function)(repo, rel, limit_s)

	def _run(self, function, result, limit_s=20, elapsed_s=1.0):
		effect = result if isinstance(result, BaseException) else None
		value = None if effect else result
		with (
			patch(RUN_PATH, return_value=value, side_effect=effect) as run,
			patch(CLOCK_PATH, side_effect=[1000.0, 1000.0 + elapsed_s]),
		):
			outcome = self._call(function, limit_s=limit_s)
		return outcome, run

	def test_git_write_argv_shapes(self):
		tails = {
			"git_add_new": ["add", "--", REL],
			"git_commit_only": [
				"commit",
				"--only",
				"--no-gpg-sign",
				"--quiet",
				"-m",
				SUBJECT,
				"-m",
				BODY,
				"--",
				REL,
			],
			"git_unstage_new": ["rm", "--cached", "-q", "--", REL],
		}
		for function in GIT_WRITES:
			with self.subTest(function=function):
				outcome, run = self._run(function, completed(0, "ok"), limit_s=17, elapsed_s=2.5)
				run.assert_called_once()
				argv = run.call_args.args[0]
				self.assertEqual(
					argv, ["timeout", "-s", "KILL", "17", "git", *GLOBAL_OPTIONS, *tails[function]]
				)
				for forbidden in (
					"-a",
					"--all",
					"--amend",
					"--allow-empty",
					"--no-verify",
					"--no-optional-locks",
				):
					self.assertNotIn(forbidden, argv)
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
				self.assertEqual(kwargs["cwd"], self.repo)
				self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
				self.assertIs(kwargs["stdout"], subprocess.PIPE)
				self.assertIs(kwargs["stderr"], subprocess.STDOUT)
				self.assertIs(kwargs["text"], True)
				self.assertEqual(kwargs["encoding"], "utf-8")
				self.assertEqual(kwargs["errors"], "replace")
				self.assertEqual(kwargs["timeout"], 22)
				self.assertIs(kwargs["start_new_session"], True)
				self.assertEqual(
					outcome,
					CommandResult(
						exit_code=0, output="ok", duration_ms=2500, timed_out=False, not_found=False
					),
				)
				for limit_s, backstop in ((1, 6), (30, 35)):
					_outcome, run = self._run(function, completed(0), limit_s=limit_s)
					self.assertEqual(run.call_args.args[0][3], str(limit_s))
					self.assertEqual(run.call_args.kwargs["timeout"], backstop)

	def test_git_commands_use_git_env_without_os_environ_or_keys(self):
		polluted = {
			"PATH": "/usr/local/bin:/usr/bin",
			"HOME": "/home/frappe",
			"USER": "frappe",
			"OPENAI_API_KEY": "sk-fake-never-leak",
			"GIT_DIR": "/tmp/other-repo",
			"GIT_AUTHOR_EMAIL": "real.person@example.com",
			"GIT_CONFIG_GLOBAL": "/home/frappe/.gitconfig",
		}
		expected = {
			"PATH": "/usr/local/bin:/usr/bin",
			"LC_ALL": "C",
			"GIT_CONFIG_GLOBAL": "/dev/null",
			"GIT_CONFIG_NOSYSTEM": "1",
			"GIT_TERMINAL_PROMPT": "0",
			"GIT_AUTHOR_NAME": "ERP AI Agent",
			"GIT_COMMITTER_NAME": "ERP AI Agent",
			"GIT_AUTHOR_EMAIL": "erp-ai-agent@bot.invalid",
			"GIT_COMMITTER_EMAIL": "erp-ai-agent@bot.invalid",
		}
		for function in GIT_WRITES:
			with self.subTest(function=function):
				with patch.dict(process_runner.os.environ, polluted, clear=True):
					_outcome, run = self._run(function, completed(0))
				env = run.call_args.kwargs["env"]
				self.assertEqual(env, expected)
				self.assertNotIn("sk-fake-never-leak", repr(run.call_args))
				self.assertNotIn("real.person@example.com", repr(run.call_args))
		with open(process_runner.__file__, encoding="utf-8") as handle:
			text = handle.read()
		for word in ("user.name", "user.email", "AGENT_USER", "GIT_CONFIG_GLOBAL", "hooksPath"):
			self.assertNotIn(word, text)

	def test_git_timeout_detected_like_bench(self):
		for function in GIT_WRITES:
			for returncode in (-9, 124, 137):
				for elapsed_s, timed_out in ((19.9, False), (20.0, True), (21.5, True)):
					with self.subTest(function=function, returncode=returncode, elapsed_s=elapsed_s):
						outcome, _run = self._run(function, completed(returncode, "x"), elapsed_s=elapsed_s)
						self.assertIs(outcome.timed_out, timed_out)
						self.assertEqual(outcome.exit_code, returncode)
						self.assertIs(outcome.not_found, False)
			for returncode in (0, 1, 128, -15, 125):
				with self.subTest(function=function, returncode=returncode):
					outcome, _run = self._run(function, completed(returncode), elapsed_s=300.0)
					self.assertIs(outcome.timed_out, False)
					self.assertIs(outcome.not_found, False)
			with self.subTest(function=function, case="TimeoutExpired"):
				expired = subprocess.TimeoutExpired(cmd=["timeout"], timeout=25, output=b"partial\n")
				outcome, _run = self._run(function, expired, elapsed_s=25.0)
				self.assertEqual(
					outcome,
					CommandResult(
						exit_code=None, output="partial", duration_ms=25000, timed_out=True, not_found=False
					),
				)
			with self.subTest(function=function, case="127"):
				outcome, _run = self._run(function, completed(127, "git: not found"))
				self.assertEqual(
					outcome,
					CommandResult(
						exit_code=127,
						output="git: not found",
						duration_ms=1000,
						timed_out=False,
						not_found=True,
					),
				)
			with self.subTest(function=function, case="FileNotFoundError"):
				outcome, _run = self._run(function, FileNotFoundError(2, "No such file", "timeout"))
				self.assertEqual(
					outcome,
					CommandResult(
						exit_code=None, output="", duration_ms=1000, timed_out=False, not_found=True
					),
				)

	def test_git_output_cut_to_20_lines(self):
		self.assertEqual(process_runner.GIT_OUTPUT_MAX_LINES, 20)
		many = "\n".join(f"line {n}" for n in range(1, 101))
		outcome, _run = self._run("git_commit_only", completed(1, many))
		self.assertEqual(
			outcome.output.split("\n"), ["… đã cắt 81 dòng đầu", *[f"line {n}" for n in range(82, 101)]]
		)
		exact = "\n".join(f"line {n}" for n in range(1, 21))
		outcome, _run = self._run("git_add_new", completed(1, exact))
		self.assertEqual(outcome.output, exact)
		one_over = "\n".join(f"line {n}" for n in range(1, 22))
		outcome, _run = self._run("git_unstage_new", completed(1, one_over))
		self.assertEqual(
			outcome.output.split("\n"), ["… đã cắt 2 dòng đầu", *[f"line {n}" for n in range(3, 22)]]
		)
		outcome, _run = self._run("git_add_new", completed(1, "c" * 3000))
		self.assertEqual(outcome.output, "c" * 1000)

	def test_git_bad_input_never_reaches_argv(self):
		missing = os.path.join(self.repo, "missing")
		cases = [
			("rel empty", {"rel": ""}),
			("rel not a string", {"rel": 1}),
			("rel with NUL", {"rel": "a\0b.py"}),
			("rel starts with -", {"rel": "-a"}),
			("rel is --amend", {"rel": "--amend"}),
			("rel absolute", {"rel": "/etc/passwd"}),
			("rel parent", {"rel": "../other/x.py"}),
			("rel is ..", {"rel": ".."}),
			("rel is .", {"rel": "."}),
			("rel inner ..", {"rel": "a/../b.py"}),
			("rel double slash", {"rel": "a//b.py"}),
			("rel trailing slash", {"rel": "api/"}),
			("rel pathspec magic", {"rel": ":(glob)*.py"}),
			("rel pathspec magic without glob", {"rel": ":(top)x.py"}),
			("rel pathspec short magic", {"rel": ":x.py"}),
			("rel glob *", {"rel": "api/*.py"}),
			("rel glob ?", {"rel": "api/t?.py"}),
			("rel glob [", {"rel": "api/[ab].py"}),
			("repo relative", {"repo": "apps/helpdesk"}),
			("repo empty", {"repo": ""}),
			("repo not a string", {"repo": 5}),
			("repo with NUL", {"repo": "/tmp/a\0b"}),
			("repo missing", {"repo": missing}),
			("limit zero", {"limit_s": 0}),
			("limit negative", {"limit_s": -1}),
			("limit above GIT_TIMEOUT_S", {"limit_s": 31}),
			("limit not int", {"limit_s": 5.0}),
			("limit bool", {"limit_s": True}),
		]
		message_cases = [
			("subject empty", {"subject": ""}),
			("subject blank", {"subject": "   "}),
			("subject not a string", {"subject": None}),
			("subject with newline", {"subject": "a\nb"}),
			("subject with carriage return", {"subject": "a\rb"}),
			("subject with NUL", {"subject": "a\0b"}),
			("body empty", {"body": ""}),
			("body blank", {"body": " \n "}),
			("body not a string", {"body": b"x"}),
			("body with NUL", {"body": "a\0b"}),
		]
		calls = [(function, label, kwargs) for function in GIT_WRITES for label, kwargs in cases]
		calls += [("git_commit_only", label, kwargs) for label, kwargs in message_cases]
		for function, label, kwargs in calls:
			with self.subTest(function=function, case=label), patch(RUN_PATH) as run:
				with self.assertRaises(ValueError):
					self._call(function, **kwargs)
				run.assert_not_called()
		for function in GIT_WRITES:
			for rel in ("x.py", "a/b/c.py", "a-b/-c.py", ".github/x.yml"):
				with self.subTest(function=function, good_rel=rel):
					with patch(RUN_PATH, return_value=completed(0)) as run:
						self._call(function, rel=rel)
					self.assertEqual(run.call_args.args[0][-1], rel)
					self.assertEqual(run.call_args.args[0][-2], "--")


SANDBOX_APP = "custom_app"
DELETED_REL = "myapp/a.py"
OTHER_STAGED_REL = "myapp/staged.py"


class TestCommitOnlyRecordsDeletion(FrappeTestCase):
	"""T-0 (design 8.0, AC-38, AC-52): a real `git commit --only -- <deleted path>` on a `GitSandbox` repo."""

	def setUp(self):
		self.sandbox = GitSandbox(self, apps=(SANDBOX_APP,), erp_ai_worktree=None)
		self.sandbox.commit_file(SANDBOX_APP, DELETED_REL, "a = 1\n")
		self.repo_root = self.sandbox.repo(SANDBOX_APP)

	def _git(self, *args) -> str:
		return self.sandbox.git(SANDBOX_APP, *args)

	def test_single_deleted_path_recorded(self):
		print(f"T-0 {self._git('--version').strip()}")
		self.sandbox.stage(SANDBOX_APP, OTHER_STAGED_REL, "s = 1\n")
		before_head = self._git("rev-parse", "HEAD").strip()

		file_writer.remove_file(os.path.join(self.repo_root, DELETED_REL))
		outcome = process_runner.git_commit_only(self.repo_root, DELETED_REL, SUBJECT, BODY, 20)

		self.assertEqual(outcome.exit_code, 0, outcome.output)
		self.assertEqual(self._git("rev-parse", "HEAD~1").strip(), before_head)
		self.assertEqual(
			self._git("diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"), f"D\t{DELETED_REL}\n"
		)
		self.assertEqual(self._git("ls-files", "--", DELETED_REL), "")
		self.assertEqual(self._git("status", "--porcelain", "--", DELETED_REL), "")
		self.assertEqual(self._git("status", "--porcelain"), f"A  {OTHER_STAGED_REL}\n")
		self.assertEqual(self._git("diff", "--cached", "--name-only"), f"{OTHER_STAGED_REL}\n")
