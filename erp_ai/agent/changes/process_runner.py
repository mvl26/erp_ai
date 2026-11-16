"""The one module in `erp_ai/agent/changes/` that starts processes: bench, the console child and git add/commit/rm (ADR-013 decisions 3, 7; ADR-022; design 3.5/4.3, D-3, D-5, D-12; CHG-010)."""

import os
import subprocess
import time
from dataclasses import dataclass

import frappe

from erp_ai.agent.tools import source
from erp_ai.constants import (
	COMMAND_TIMEOUT_S,
	JOB_SAFETY_MARGIN_S,
	RESTART_LAUNCH_TIMEOUT_S,
	RESTART_TIMEOUT_S,
)

ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "USER")
OUTPUT_MAX_LINES = source.READ_MAX_LINES
OUTPUT_LINE_MAX_CHARS = 1000
GIT_OUTPUT_MAX_LINES = 20
NOT_FOUND_EXIT_CODE = 127
# CHG-010: the console child is `bench --site <site> execute CONSOLE_ENTRY`, the script on its stdin.
CONSOLE_ENTRY = "erp_ai.console_entry.run"
RESTART_ARGV = (
	source.SETSID_EXECUTABLE,
	"-f",
	source.TIMEOUT_EXECUTABLE,
	"-s",
	"KILL",
	str(RESTART_TIMEOUT_S),
	source.BENCH_EXECUTABLE,
	"restart",
)


@dataclass(frozen=True)
class CommandResult:
	exit_code: int | None
	output: str
	duration_ms: int
	timed_out: bool
	not_found: bool


def _minimal_env() -> dict:
	return {name: os.environ[name] for name in ENV_ALLOWLIST if name in os.environ}


def _cut_output(output, max_lines: int) -> str:
	"""Keep the last max_lines - 1 lines under a `… đã cắt <n> dòng đầu` line; each line ≤ 1000 chars."""
	if isinstance(output, bytes):
		output = output.decode("utf-8", errors="replace")
	lines = [line[:OUTPUT_LINE_MAX_CHARS] for line in (output or "").splitlines()]
	if len(lines) > max_lines:
		dropped = len(lines) - (max_lines - 1)
		lines = [f"… đã cắt {dropped} dòng đầu", *lines[dropped:]]
	return "\n".join(lines)


def _check_bench_call(args, limit_s) -> None:
	if not isinstance(args, list) or not args:
		raise ValueError("args must be a non-empty list")
	if not all(isinstance(arg, str) and "\0" not in arg for arg in args):
		raise ValueError("every bench argument must be a string without NUL")
	if not isinstance(limit_s, int) or isinstance(limit_s, bool) or not 1 <= limit_s <= COMMAND_TIMEOUT_S:
		raise ValueError(f"limit_s must be an integer from 1 to {COMMAND_TIMEOUT_S}: {limit_s!r}")


def run_bench(args: list[str], limit_s: int) -> CommandResult:
	"""Run `bench *args` in the bench directory, killed with its process group after limit_s."""
	_check_bench_call(args, limit_s)
	return _run_wrapped(
		[source.BENCH_EXECUTABLE, *args],
		cwd=frappe.utils.get_bench_path(),
		env=_minimal_env(),
		limit_s=limit_s,
		backstop_s=JOB_SAFETY_MARGIN_S // 2,
		max_lines=OUTPUT_MAX_LINES,
	)


def run_console(script: str, site: str, limit_s: int) -> CommandResult:
	"""Run an approved console script once (CHG-010): `bench --site <site> execute erp_ai.console_entry.run`
	in the bench directory with `script` on stdin (never written to a file), killed with its process group
	after limit_s. The child commits only when the script returns; its output is cut like `run_bench`."""
	if not isinstance(script, str) or not script.strip():
		raise ValueError("script must be non-empty text")
	args = ["--site", site, "execute", CONSOLE_ENTRY]
	_check_bench_call(args, limit_s)
	return _run_wrapped(
		[source.BENCH_EXECUTABLE, *args],
		cwd=frappe.utils.get_bench_path(),
		env=_minimal_env(),
		limit_s=limit_s,
		backstop_s=JOB_SAFETY_MARGIN_S // 2,
		max_lines=OUTPUT_MAX_LINES,
		input_text=script,
	)


def _check_git_write_call(repo_root, rel, limit_s) -> None:
	if not isinstance(repo_root, str) or not os.path.isabs(repo_root) or not os.path.isdir(repo_root):
		raise ValueError(f"repo_root must be an existing absolute directory: {repo_root!r}")
	_check_git_rel(rel)
	if not isinstance(limit_s, int) or isinstance(limit_s, bool) or not 1 <= limit_s <= source.GIT_TIMEOUT_S:
		raise ValueError(f"limit_s must be an integer from 1 to {source.GIT_TIMEOUT_S}: {limit_s!r}")


def _check_git_rel(rel) -> None:
	if (
		not isinstance(rel, str)
		or not rel
		or "\0" in rel
		or rel.startswith(("-", "/", ":"))
		or os.path.normpath(rel) != rel
		or rel == ".."
		or rel.startswith("../")
		or rel == "."
		or source.GIT_GLOB_CHARS.search(rel)
	):
		raise ValueError(f"rel must be a plain relative file path inside the repo: {rel!r}")


def _check_commit_rels(rels) -> None:
	if not isinstance(rels, tuple) or not rels:
		raise ValueError(f"rels must be a non-empty tuple of paths: {rels!r}")
	for rel in rels:
		_check_git_rel(rel)
	if len(set(rels)) != len(rels):
		raise ValueError(f"rels must not repeat a path: {rels!r}")


def _check_commit_message(subject, body) -> None:
	if not isinstance(subject, str) or not subject.strip() or any(char in subject for char in "\0\r\n"):
		raise ValueError("subject must be one non-empty line without NUL")
	if not isinstance(body, str) or not body.strip() or "\0" in body:
		raise ValueError("body must be non-empty text without NUL")


def _run_git_write(repo_root: str, rels, limit_s: int, subcommand_args: list[str]) -> CommandResult:
	"""Run one git write subcommand on the paths rels in repo_root with the bot identity (ADR-022 QĐ 2, 4, 5)."""
	return _run_wrapped(
		["git", *source.git_global_options(read=False), *subcommand_args, "--", *rels],
		cwd=repo_root,
		env=source.git_env(identity=True),
		limit_s=limit_s,
		backstop_s=source.GIT_BACKSTOP_EXTRA_S,
		max_lines=GIT_OUTPUT_MAX_LINES,
	)


def git_add_new(repo_root: str, rel_in_repo: str, limit_s: int) -> CommandResult:
	"""`git add -- rel_in_repo`: stage a file the proposal created."""
	_check_git_write_call(repo_root, rel_in_repo, limit_s)
	return _run_git_write(repo_root, (rel_in_repo,), limit_s, ["add"])


def git_commit_only(
	repo_root: str, rels: tuple[str, ...], subject: str, body: str, limit_s: int
) -> CommandResult:
	"""`git commit --only -- *sorted(rels)`: one local commit holding just those paths, never `-a`/`--amend`."""
	_check_commit_rels(rels)
	_check_git_write_call(repo_root, rels[0], limit_s)
	_check_commit_message(subject, body)
	return _run_git_write(
		repo_root,
		sorted(rels),
		limit_s,
		["commit", "--only", "--no-gpg-sign", "--quiet", "-m", subject, "-m", body],
	)


def git_unstage_new(repo_root: str, rel_in_repo: str, limit_s: int) -> CommandResult:
	"""`git rm --cached -q -- rel_in_repo`: take a new file back out of the index after a failed commit."""
	_check_git_write_call(repo_root, rel_in_repo, limit_s)
	return _run_git_write(repo_root, (rel_in_repo,), limit_s, ["rm", "--cached", "-q"])


def launch_restart() -> tuple[bool, str | None]:
	"""Start `bench restart` detached in its own session and return at once (design 3.4, 4.4; ADR-040 QĐ 7).

	Never raises: any error returns (False, <error class name>) and the caller logs it (STD-ERR-1).
	"""
	try:
		done = subprocess.run(
			RESTART_ARGV,
			cwd=frappe.utils.get_bench_path(),
			env=_minimal_env(),
			stdin=subprocess.DEVNULL,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
			timeout=RESTART_LAUNCH_TIMEOUT_S,
			start_new_session=True,
		)
	except Exception as error:
		return False, type(error).__name__
	if done.returncode != 0:
		return False, subprocess.CalledProcessError.__name__
	return True, None


def _run_wrapped(
	command, *, cwd, env, limit_s, backstop_s, max_lines, input_text: str | None = None
) -> CommandResult:
	"""Run `timeout -s KILL limit_s *command` in its own process group; timed out like ADR-013 QĐ 7.

	`input_text` is written to the child's stdin (CHG-010: the console script); without it stdin is DEVNULL.
	"""
	# `subprocess.run` refuses `stdin=` next to `input=`, so exactly one of the two is passed.
	feed = {"stdin": subprocess.DEVNULL} if input_text is None else {"input": input_text}
	started = time.monotonic()
	try:
		done = subprocess.run(
			[source.TIMEOUT_EXECUTABLE, "-s", "KILL", str(limit_s), *command],
			cwd=cwd,
			env=env,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			encoding="utf-8",
			errors="replace",
			timeout=limit_s + backstop_s,
			start_new_session=True,
			**feed,
		)
	except subprocess.TimeoutExpired as expired:
		return CommandResult(
			exit_code=None,
			output=_cut_output(expired.output, max_lines),
			duration_ms=_elapsed_ms(started),
			timed_out=True,
			not_found=False,
		)
	except FileNotFoundError:
		return CommandResult(
			exit_code=None, output="", duration_ms=_elapsed_ms(started), timed_out=False, not_found=True
		)
	elapsed_s = time.monotonic() - started
	return CommandResult(
		exit_code=done.returncode,
		output=_cut_output(done.stdout, max_lines),
		duration_ms=int(elapsed_s * 1000),
		timed_out=done.returncode in source.KILLED_EXIT_CODES and elapsed_s >= limit_s,
		not_found=done.returncode == NOT_FOUND_EXIT_CODE,
	)


def _elapsed_ms(started: float) -> int:
	return int((time.monotonic() - started) * 1000)
