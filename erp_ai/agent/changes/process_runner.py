"""The one module in `erp_ai/agent/changes/` that starts processes: bench and git add/commit/rm (ADR-013 decisions 3, 7; ADR-022; design 3.5/4.3, D-3, D-5, D-12)."""

import os
import subprocess
import time
from dataclasses import dataclass

import frappe

from erp_ai.agent.tools import source
from erp_ai.constants import COMMAND_TIMEOUT_S, JOB_SAFETY_MARGIN_S

ENV_ALLOWLIST = ("PATH", "HOME", "LANG", "LC_ALL", "USER")
OUTPUT_MAX_LINES = source.READ_MAX_LINES
OUTPUT_LINE_MAX_CHARS = 1000
GIT_OUTPUT_MAX_LINES = 20
NOT_FOUND_EXIT_CODE = 127


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


def _check_git_write_call(repo_root, rel, limit_s) -> None:
	if not isinstance(repo_root, str) or not os.path.isabs(repo_root) or not os.path.isdir(repo_root):
		raise ValueError(f"repo_root must be an existing absolute directory: {repo_root!r}")
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
	if not isinstance(limit_s, int) or isinstance(limit_s, bool) or not 1 <= limit_s <= source.GIT_TIMEOUT_S:
		raise ValueError(f"limit_s must be an integer from 1 to {source.GIT_TIMEOUT_S}: {limit_s!r}")


def _check_commit_message(subject, body) -> None:
	if not isinstance(subject, str) or not subject.strip() or any(char in subject for char in "\0\r\n"):
		raise ValueError("subject must be one non-empty line without NUL")
	if not isinstance(body, str) or not body.strip() or "\0" in body:
		raise ValueError("body must be non-empty text without NUL")


def _run_git_write(repo_root: str, rel: str, limit_s: int, subcommand_args: list[str]) -> CommandResult:
	"""Run one git write subcommand on rel in repo_root with the bot identity (ADR-022 QĐ 2, 4, 5)."""
	return _run_wrapped(
		["git", *source.git_global_options(read=False), *subcommand_args, "--", rel],
		cwd=repo_root,
		env=source.git_env(identity=True),
		limit_s=limit_s,
		backstop_s=source.GIT_BACKSTOP_EXTRA_S,
		max_lines=GIT_OUTPUT_MAX_LINES,
	)


def git_add_new(repo_root: str, rel_in_repo: str, limit_s: int) -> CommandResult:
	"""`git add -- rel_in_repo`: stage a file the proposal created."""
	_check_git_write_call(repo_root, rel_in_repo, limit_s)
	return _run_git_write(repo_root, rel_in_repo, limit_s, ["add"])


def git_commit_only(repo_root: str, rel_in_repo: str, subject: str, body: str, limit_s: int) -> CommandResult:
	"""`git commit --only -- rel_in_repo`: one local commit holding just that path, never `-a`/`--amend`."""
	_check_git_write_call(repo_root, rel_in_repo, limit_s)
	_check_commit_message(subject, body)
	return _run_git_write(
		repo_root,
		rel_in_repo,
		limit_s,
		["commit", "--only", "--no-gpg-sign", "--quiet", "-m", subject, "-m", body],
	)


def git_unstage_new(repo_root: str, rel_in_repo: str, limit_s: int) -> CommandResult:
	"""`git rm --cached -q -- rel_in_repo`: take a new file back out of the index after a failed commit."""
	_check_git_write_call(repo_root, rel_in_repo, limit_s)
	return _run_git_write(repo_root, rel_in_repo, limit_s, ["rm", "--cached", "-q"])


def _run_wrapped(command, *, cwd, env, limit_s, backstop_s, max_lines) -> CommandResult:
	"""Run `timeout -s KILL limit_s *command` in its own process group; timed out like ADR-013 QĐ 7."""
	started = time.monotonic()
	try:
		done = subprocess.run(
			[source.TIMEOUT_EXECUTABLE, "-s", "KILL", str(limit_s), *command],
			cwd=cwd,
			env=env,
			stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			encoding="utf-8",
			errors="replace",
			timeout=limit_s + backstop_s,
			start_new_session=True,
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
