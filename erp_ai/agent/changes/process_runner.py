"""The one module in `erp_ai/agent/changes/` that starts processes (ADR-013 decisions 3, 7; design 3.5/4.3, D-3, D-5, D-12)."""

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


def _cut_output(output) -> str:
	"""Keep the last OUTPUT_MAX_LINES - 1 lines under a `… đã cắt <n> dòng đầu` line; each line ≤ 1000 chars."""
	if isinstance(output, bytes):
		output = output.decode("utf-8", errors="replace")
	lines = [line[:OUTPUT_LINE_MAX_CHARS] for line in (output or "").splitlines()]
	if len(lines) > OUTPUT_MAX_LINES:
		dropped = len(lines) - (OUTPUT_MAX_LINES - 1)
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
	started = time.monotonic()
	try:
		done = subprocess.run(
			[source.TIMEOUT_EXECUTABLE, "-s", "KILL", str(limit_s), source.BENCH_EXECUTABLE, *args],
			cwd=frappe.utils.get_bench_path(),
			env=_minimal_env(),
			stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			encoding="utf-8",
			errors="replace",
			timeout=limit_s + JOB_SAFETY_MARGIN_S // 2,
			start_new_session=True,
		)
	except subprocess.TimeoutExpired as expired:
		return CommandResult(
			exit_code=None,
			output=_cut_output(expired.output),
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
		output=_cut_output(done.stdout),
		duration_ms=int(elapsed_s * 1000),
		timed_out=done.returncode in source.KILLED_EXIT_CODES and elapsed_s >= limit_s,
		not_found=done.returncode == NOT_FOUND_EXIT_CODE,
	)


def _elapsed_ms(started: float) -> int:
	return int((time.monotonic() - started) * 1000)
