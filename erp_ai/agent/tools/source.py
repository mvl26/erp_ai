import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass

import frappe

from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolSpec
from erp_ai.constants import BOT_GIT_EMAIL, BOT_GIT_NAME, CHANGE_FILE_MAX_BYTES, SETTING_DOCTYPE

LOGGER_NAME = "erp_ai.source"


def _logger() -> logging.Logger:
	"""The "erp_ai.source" logger, got at each use: importing this module makes no logger (F-3)."""
	try:
		return frappe.logger(LOGGER_NAME)
	except Exception:
		# Kept on purpose (STD-ERR-1): the callers log from inside their own error handling, so a log file
		# that cannot be opened must not replace their error; the stdlib logger of the same name takes it.
		return logging.getLogger(LOGGER_NAME)


DUOI_CHO_PHEP = {".py", ".js", ".vue", ".json", ".md", ".html", ".css", ".txt"}
TEN_CAM = re.compile(
	r"(site_config\.json|common_site_config\.json|\.env|\.pem|\.key|" r"id_rsa|credential|secret|password)",
	re.I,
)

# ADR-040 QĐ 5, design §3.1, §3.2 and addendum A-1.2 to A-1.4: the one definition of "allowed text".
TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES
TEXT_SECRET_NAME = "tên file thuộc loại bí mật hoặc được bảo vệ"
GIT_DIR = "không được chạm .git hoặc tên bắt đầu bằng .git"
TEXT_TOO_LARGE = f"file lớn hơn {TEXT_MAX_BYTES // (1024 * 1024)} MiB"
TEXT_HAS_NUL = "file có byte NUL, không phải văn bản"
TEXT_NOT_UTF8 = "file không phải văn bản UTF-8"
GIT_NAME_PREFIX = ".git"

READ_MAX_LINES = 400
READ_DEFAULT_LINES = 200
SEARCH_MAX_HITS = 40
SEARCH_TIME_BUDGET_S = 30
SEARCH_FILE_MAX_BYTES = 1024 * 1024
SEARCH_TEXT_MAX_CHARS = 300
PATTERN_MIN_CHARS = 2
PATTERN_MAX_CHARS = 200
# Design §3.2 "Nơi dùng hàm": the shape of the `extension` argument; which files are text is `text_refusal`'s call.
SEARCH_EXTENSION = re.compile(r"^\.[A-Za-z0-9]{1,10}$")
SKIPPED_DIRS = {"node_modules"}

GIT_SUBCOMMANDS = {"log", "blame"}
GIT_NO_EXT_SUBCOMMANDS = {"log"}
GIT_ALLOWED_FLAGS = {
	"--oneline",
	"--stat",
	"--shortstat",
	"--numstat",
	"--name-only",
	"--name-status",
	"--no-merges",
	"--merges",
	"--graph",
	"--decorate",
	"--abbrev-commit",
	"--follow",
	"-w",
	"-n",
	"--max-count",
	"--since",
	"--until",
	"--author",
	"--date",
}
GIT_BLAME_FLAGS = {"--porcelain", "--line-porcelain", "-w"}
GIT_COUNT_FLAG = re.compile(r"-n\d+")
GIT_GLOB_CHARS = re.compile(r"[*?\[\]]")
GIT_TIMEOUT_S = 30
GIT_MAX_ARGS = 10
GIT_OUTPUT_MAX_CHARS = 8000

# ADR-022 QĐ 2, 4: the git read set and the one definition of git options and environment.
GIT_READ_SUBCOMMANDS = frozenset(
	{"rev-parse", "rev-list", "status", "check-ignore", "ls-files", "merge-base", "diff-tree", "cat-file"}
)
TIMEOUT_EXECUTABLE = "timeout"
BENCH_EXECUTABLE = "bench"
SETSID_EXECUTABLE = "setsid"
GIT_HOOKS_DIR = os.path.realpath(
	os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "git_no_hooks")
)
GIT_BACKSTOP_EXTRA_S = 5
GIT_DEFAULT_PATH = "/usr/bin:/bin"
KILLED_EXIT_CODES = (-9, 124, 137)
# ADR-022 QĐ 2: the diff option that makes diff-tree/rev-list write a file; git accepts unambiguous abbreviations.
GIT_WRITE_OPTION = "--output"
# arch-ruling-clean-filter.md (b): options that run a program declared in the repo config; never a read argument.
GIT_PROGRAM_OPTIONS = ("--filters", "--textconv", "--ext-diff")
# Design table 3.2: the git refusal sentences of read_git_state are a contract with the tests.
GIT_NOT_REPO = "thư mục app không phải gốc một kho git"
GIT_NO_COMMIT = "kho git của app chưa có commit nào"
GIT_DETACHED = "HEAD của kho git không nằm trên nhánh nào (detached)"
GIT_LOCKED = "kho git đang bị khóa (index.lock): có thao tác git khác đang chạy hoặc bị dừng giữa chừng"
GIT_IN_PROGRESS = "kho git đang dở merge, rebase, cherry-pick hoặc revert"
GIT_IGNORED = "file đích bị git bỏ qua (.gitignore)"
GIT_DIRTY = "file đích có thay đổi chưa commit"
GIT_ERROR = "không đọc được trạng thái git"
# Design 3.2 step 7: shown instead of an upstream name that looks like a URL (NFR-8).
GIT_MASKED_UPSTREAM = "(remote không tên)"
# index.lock first (GIT_LOCKED), then the files git leaves while an operation is in progress (GIT_IN_PROGRESS).
GIT_STATE_FILES = (
	"index.lock",
	"MERGE_HEAD",
	"CHERRY_PICK_HEAD",
	"REVERT_HEAD",
	"rebase-merge",
	"rebase-apply",
)
GIT_OBJECT_NAME = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


def get_source_root():
	return os.path.realpath(os.path.dirname(os.path.dirname(frappe.get_app_path("frappe"))))


def _inside(root, full):
	return os.path.commonpath([root, full]) == root and full != root


def _base_resolve(rel):
	"""Return the real path of an allowed path under the root (no secret name, allowed extension), else None."""
	if not isinstance(rel, str) or not rel.strip() or "\0" in rel:
		return None
	root = os.path.realpath(get_source_root())
	full = os.path.realpath(os.path.join(root, rel))
	if not _inside(root, full):
		return None
	if text_refusal(os.path.relpath(full, root)) is not None:
		return None
	return full


def manuals_root():
	"""Real path of the manuals directory set in `manuals_dir`; None when blank or not a safe directory (AC-47)."""
	value = (frappe.db.get_single_value(SETTING_DOCTYPE, "manuals_dir") or "").strip()
	full = _base_resolve(value)
	return full if full and os.path.isdir(full) else None


def resolve_manual_path(rel):
	"""Return the real path of an allowed path strictly inside the manuals directory, else None."""
	full = _base_resolve(rel)
	root = manuals_root() if full else None
	return full if root and _inside(root, full) else None


def resolve_safe_path(rel):
	"""Return the real path of an allowed source path under the root, else None.

	Anything strictly inside the manuals directory that is not an existing directory is not source: an existing
	file or a path not on disk yet (ADR-034 QĐ 5); the directory itself and its subdirectories still resolve (E-7).
	"""
	full = _base_resolve(rel)
	if full and not os.path.isdir(full):
		root = manuals_root()
		if root and _inside(root, full):
			return None
	return full


def text_refusal(rel_path: str, data: bytes | None = None) -> str | None:
	"""The refusal reason when rel_path (and data, when given) is not allowed text, else None.

	Checked in this order (design §3.2): secret name, a component starting with ".git", size, NUL, strict UTF-8.
	"""
	if TEN_CAM.search(rel_path):
		return TEXT_SECRET_NAME
	if any(part.startswith(GIT_NAME_PREFIX) for part in rel_path.split(os.sep)):
		return GIT_DIR
	if data is None:
		return None
	if len(data) > TEXT_MAX_BYTES:
		return TEXT_TOO_LARGE
	if b"\0" in data:
		return TEXT_HAS_NUL
	try:
		data.decode("utf-8", errors="strict")
	except UnicodeDecodeError:
		return TEXT_NOT_UTF8
	return None


def _refuse(reason):
	return {"ok": False, "reason": reason}


def _to_int(value, default):
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def read_source(args, ctx):
	try:
		args = args or {}
		full = resolve_safe_path(args.get("path"))
		if full is None or not os.path.isfile(full):
			return _refuse("Đường dẫn không hợp lệ hoặc không được phép đọc")
		offset = max(_to_int(args.get("offset"), 1), 1)
		limit = min(max(_to_int(args.get("limit"), READ_DEFAULT_LINES), 1), READ_MAX_LINES)
		with open(full, "rb") as handle:
			data = handle.read(TEXT_MAX_BYTES + 1)
		reason = text_refusal(os.path.relpath(full, os.path.realpath(get_source_root())), data)
		if reason is not None:
			return _refuse(reason)
		lines = data.decode("utf-8", errors="strict").splitlines()
		chunk = lines[offset - 1 : offset - 1 + limit]
		return {
			"ok": True,
			"path": os.path.relpath(full, os.path.realpath(get_source_root())),
			"from_line": offset,
			"total_lines": len(lines),
			"content": "\n".join(chunk),
		}
	except Exception:
		_logger().exception("read_source failed")
		return _refuse("Không đọc được file")


def _search_base(root, app):
	if not app:
		return root
	if not isinstance(app, str):
		return None
	base = os.path.realpath(os.path.join(root, app))
	if base == root or (_inside(root, base) and os.path.isdir(base)):
		return base
	return None


def _scan_text(text, rel, needle, hits):
	for number, line in enumerate(text.splitlines(), 1):
		if needle in line.lower():
			hits.append({"path": rel, "line": number, "text": line.strip()[:SEARCH_TEXT_MAX_CHARS]})
			if len(hits) >= SEARCH_MAX_HITS:
				return


def _read_text(full, rel):
	"""The decoded text of a file allowed by `text_refusal`, else None (unreadable files included)."""
	try:
		with open(full, "rb") as handle:
			data = handle.read(TEXT_MAX_BYTES + 1)
	except OSError:
		return None
	if text_refusal(rel, data) is not None:
		return None
	return data.decode("utf-8", errors="strict")


def search_source(args, ctx):
	try:
		args = args or {}
		pattern = args.get("pattern")
		if not isinstance(pattern, str) or not PATTERN_MIN_CHARS <= len(pattern) <= PATTERN_MAX_CHARS:
			return _refuse("Mẫu tìm phải dài từ 2 đến 200 ký tự")
		extension = args.get("extension")
		if extension is not None and not (
			isinstance(extension, str) and SEARCH_EXTENSION.fullmatch(extension)
		):
			return _refuse("Đuôi file không được phép tìm")
		root = os.path.realpath(get_source_root())
		base = _search_base(root, args.get("app"))
		if base is None:
			return _refuse("Thư mục nằm ngoài mã nguồn cho phép")

		needle = pattern.lower()
		started = time.monotonic()
		hits = []
		for folder, dirnames, filenames in os.walk(base, followlinks=False):
			dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIPPED_DIRS]
			for name in sorted(filenames):
				if time.monotonic() - started > SEARCH_TIME_BUDGET_S or len(hits) >= SEARCH_MAX_HITS:
					return {"ok": True, "hits": hits}
				if extension and os.path.splitext(name)[1].lower() != extension.lower():
					continue
				full = resolve_safe_path(os.path.relpath(os.path.join(folder, name), root))
				if full is None or not os.path.isfile(full):
					continue
				rel = os.path.relpath(full, root)
				text = _read_text(full, rel)
				if text is not None:
					_scan_text(text, rel, needle, hits)
		return {"ok": True, "hits": hits}
	except Exception:
		_logger().exception("search_source failed")
		return _refuse("Không tìm được trong mã nguồn")


def _git_repo(root, app):
	if not isinstance(app, str) or not app or os.sep in app or app in {".", ".."}:
		return None
	repo = os.path.join(root, app)
	if os.path.realpath(repo) != repo or not os.path.isdir(os.path.join(repo, ".git")):
		return None
	return repo


def _git_path_ok(root, repo, path):
	"""A pathspec is safe when it has no glob/magic and passes resolve_safe_path like read_source."""
	if not path or GIT_GLOB_CHARS.search(path):
		return False
	return resolve_safe_path(os.path.relpath(os.path.join(repo, path), root)) is not None


def _git_log_args_ok(root, repo, git_args):
	"""True when every option is on the exact-name allowlist and every other arg passes the path check."""
	only_paths = False
	for arg in git_args:
		if only_paths:
			if not _git_path_ok(root, repo, arg):
				return False
		elif arg == "--":
			only_paths = True
		elif arg.startswith("-"):
			if arg.split("=", 1)[0] not in GIT_ALLOWED_FLAGS and not GIT_COUNT_FLAG.fullmatch(arg):
				return False
		elif arg.startswith(":") or GIT_GLOB_CHARS.search(arg):
			return False
		elif not _git_path_ok(root, repo, arg.split(":", 1)[1] if ":" in arg else arg):
			return False
	return True


def _git_blame_args_ok(root, repo, git_args):
	"""True for blame flags on the allowlist followed by exactly one readable file."""
	files = []
	only_paths = False
	for arg in git_args:
		if only_paths:
			files.append(arg)
		elif arg == "--":
			only_paths = True
		elif arg.startswith("-"):
			if arg not in GIT_BLAME_FLAGS:
				return False
		else:
			files.append(arg)
	if len(files) != 1 or not _git_path_ok(root, repo, files[0]):
		return False
	full = resolve_safe_path(os.path.relpath(os.path.join(repo, files[0]), root))
	return full is not None and os.path.isfile(full)


GIT_ARGS_CHECKERS = {"log": _git_log_args_ok, "blame": _git_blame_args_ok}


def git_source(args, ctx):
	try:
		args = args or {}
		sub = args.get("subcommand")
		if not isinstance(sub, str) or sub not in GIT_SUBCOMMANDS:
			return _refuse("Chỉ cho phép git log và blame")
		git_args = args.get("args")
		if git_args is None:
			git_args = ["--oneline", "-n", "15"] if sub == "log" else []
		if (
			not isinstance(git_args, list)
			or len(git_args) > GIT_MAX_ARGS
			or not all(isinstance(a, str) and "\0" not in a for a in git_args)
		):
			return _refuse("Tham số git không hợp lệ (tối đa 10 chuỗi)")
		root = os.path.realpath(get_source_root())
		repo = _git_repo(root, args.get("app"))
		if repo is None:
			return _refuse("Không tìm thấy kho git của app")
		args_ok = GIT_ARGS_CHECKERS.get(sub)
		if args_ok is None or not args_ok(root, repo, git_args):
			return _refuse("Tham số git bị cấm hoặc đường dẫn không được phép")

		extra = ["--no-ext-diff", "--no-textconv"] if sub in GIT_NO_EXT_SUBCOMMANDS else []
		command = ["git", "--no-pager", "-C", repo, sub, *extra, *git_args]
		done = subprocess.run(
			command,
			capture_output=True,
			stdin=subprocess.DEVNULL,
			text=True,
			timeout=GIT_TIMEOUT_S,
			env={**os.environ, "GIT_PAGER": "cat"},
		)
		if done.returncode != 0:
			_logger().warning("git_source %s exit %s", sub, done.returncode)
			return _refuse(f"git báo lỗi (mã {done.returncode})")
		return {"ok": True, "output": (done.stdout or "")[:GIT_OUTPUT_MAX_CHARS]}
	except FileNotFoundError:
		return _refuse("chưa cài git trên máy chủ")
	except subprocess.TimeoutExpired:
		_logger().warning("git_source timed out")
		return _refuse("git chạy quá thời gian cho phép")
	except Exception:
		_logger().exception("git_source failed")
		return _refuse("Không chạy được git")


@dataclass(frozen=True)
class GitRun:
	exit_code: int | None
	stdout: bytes
	timed_out: bool


def git_global_options(*, read: bool) -> list[str]:
	"""Options in front of every git subcommand of FEAT-004: no repo hooks, no fsmonitor, no auto gc (ADR-022 QĐ 4)."""
	options = [
		"--no-pager",
		"-c",
		f"core.hooksPath={GIT_HOOKS_DIR}",
		"-c",
		"core.fsmonitor=false",
		"-c",
		"maintenance.auto=false",
		"-c",
		"gc.auto=0",
	]
	return [*options, "--no-optional-locks"] if read else options


def git_env(*, identity: bool) -> dict[str, str]:
	"""An explicit git environment: no HOME, no global/system config, nothing from os.environ but PATH (NFR-8)."""
	env = {
		"PATH": os.environ.get("PATH") or GIT_DEFAULT_PATH,
		"LC_ALL": "C",
		"GIT_CONFIG_GLOBAL": "/dev/null",
		"GIT_CONFIG_NOSYSTEM": "1",
		"GIT_TERMINAL_PROMPT": "0",
	}
	if identity:
		env.update(
			{
				"GIT_AUTHOR_NAME": BOT_GIT_NAME,
				"GIT_COMMITTER_NAME": BOT_GIT_NAME,
				"GIT_AUTHOR_EMAIL": BOT_GIT_EMAIL,
				"GIT_COMMITTER_EMAIL": BOT_GIT_EMAIL,
			}
		)
	return env


def _is_option(name: str, option: str) -> bool:
	"""True when `name` is `option` or an abbreviation of it that git accepts (longer than `--`)."""
	return name.startswith(option) or (len(name) > 2 and option.startswith(name))


def _check_git_read_call(repo_root, subcommand, args, limit_s) -> None:
	if not isinstance(subcommand, str) or subcommand not in GIT_READ_SUBCOMMANDS:
		raise ValueError(f"git read subcommand not allowed: {subcommand!r}")
	if (
		not isinstance(repo_root, str)
		or "\0" in repo_root
		or not os.path.isabs(repo_root)
		or not os.path.isdir(repo_root)
	):
		raise ValueError(f"repo_root must be an existing absolute directory: {repo_root!r}")
	if not all(isinstance(arg, str) and "\0" not in arg for arg in args):
		raise ValueError("every git argument must be a string without NUL")
	for arg in args:
		name = arg.split("=", 1)[0]
		if _is_option(name, GIT_WRITE_OPTION):
			raise ValueError(f"git argument not allowed, it writes a file: {name!r}")
		if any(_is_option(name, option) for option in GIT_PROGRAM_OPTIONS):
			raise ValueError(f"git argument not allowed, it runs a configured program: {name!r}")
	if not isinstance(limit_s, int) or isinstance(limit_s, bool) or not 1 <= limit_s <= GIT_TIMEOUT_S:
		raise ValueError(f"limit_s must be an integer from 1 to {GIT_TIMEOUT_S}: {limit_s!r}")


def run_git_read(repo_root: str, subcommand: str, *args: str, limit_s: int = GIT_TIMEOUT_S) -> GitRun:
	"""Run one read-only git subcommand in repo_root, killed with its process group after limit_s (ADR-022 QĐ 2, 4)."""
	_check_git_read_call(repo_root, subcommand, args, limit_s)
	started = time.monotonic()
	try:
		done = subprocess.run(
			[
				TIMEOUT_EXECUTABLE,
				"-s",
				"KILL",
				str(limit_s),
				"git",
				*git_global_options(read=True),
				subcommand,
				*args,
			],
			cwd=repo_root,
			env=git_env(identity=False),
			stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE,
			stderr=subprocess.DEVNULL,
			timeout=limit_s + GIT_BACKSTOP_EXTRA_S,
			start_new_session=True,
		)
	except subprocess.TimeoutExpired:
		_logger().warning("git %s timed out after the backstop", subcommand)
		return GitRun(exit_code=None, stdout=b"", timed_out=True)
	except OSError as error:
		_logger().warning("git %s could not start: %s", subcommand, type(error).__name__)
		return GitRun(exit_code=None, stdout=b"", timed_out=False)
	timed_out = done.returncode in KILLED_EXIT_CODES and time.monotonic() - started >= limit_s
	return GitRun(exit_code=done.returncode, stdout=done.stdout or b"", timed_out=timed_out)


@dataclass(frozen=True)
class GitState:
	refusal: str | None  # a sentence of design table 3.2; None = the target can be committed
	repo_root: str | None  # real path of the repo root, which is the app directory (D-20)
	rel_in_repo: str | None
	branch: str | None
	head: str | None
	upstream_ref: str = ""
	ahead_count: int = 0


def _git_refused(reason: str) -> GitState:
	return GitState(refusal=reason, repo_root=None, rel_in_repo=None, branch=None, head=None)


def _git_finished(run: GitRun) -> GitRun | None:
	"""The run when git exited on its own; None when it timed out or could not start (GIT_ERROR)."""
	return None if run.timed_out or run.exit_code is None else run


def _git_lines(run: GitRun) -> list[str]:
	text = os.fsdecode(run.stdout)
	return text[:-1].split("\n") if text.endswith("\n") else [text]


def _check_git_state_call(full_path, new_file, limit_s) -> tuple[str, str]:
	"""Return (app directory, path in the repo) of a canonical file path under the root, else ValueError."""
	if not isinstance(new_file, bool):
		raise ValueError(f"new_file must be a bool: {new_file!r}")
	if not isinstance(limit_s, int) or isinstance(limit_s, bool) or not 1 <= limit_s <= GIT_TIMEOUT_S:
		raise ValueError(f"limit_s must be an integer from 1 to {GIT_TIMEOUT_S}: {limit_s!r}")
	root = os.path.realpath(get_source_root())
	if (
		not isinstance(full_path, str)
		or "\0" in full_path
		or not os.path.isabs(full_path)
		or os.path.realpath(full_path) != full_path
		or not _inside(root, full_path)
	):
		raise ValueError(f"full_path must be a real path under the source root: {full_path!r}")
	app, _, rel_in_repo = os.path.relpath(full_path, root).partition(os.sep)
	if not rel_in_repo:
		raise ValueError(f"full_path must be a file inside an app directory: {full_path!r}")
	return os.path.join(root, app), rel_in_repo


def read_git_state(full_path: str, *, new_file: bool, limit_s: int = GIT_TIMEOUT_S) -> GitState:
	"""Read whether the target file can get one `commit --only` in its app repo; stop at the first refusal.

	Order (design 3.2): app dir is a repo root, a first commit, HEAD on a branch, no `index.lock`, no
	merge/rebase/cherry-pick/revert in progress, target not ignored, target clean. Other dirty files do
	not block. Every command is a read subcommand through `run_git_read`; a timeout, an unknown exit code
	or unparsable output is GIT_ERROR. `new_file` is part of the contract: the same status check covers a
	tracked file deleted from disk.
	"""
	repo_root, rel_in_repo = _check_git_state_call(full_path, new_file, limit_s)
	if not os.path.isdir(repo_root):
		return _git_refused(GIT_NOT_REPO)

	top = _git_finished(
		run_git_read(repo_root, "rev-parse", "--show-toplevel", "--git-common-dir", limit_s=limit_s)
	)
	if top is None:
		return _git_refused(GIT_ERROR)
	if top.exit_code != 0:
		return _git_refused(GIT_NOT_REPO)
	lines = _git_lines(top)
	if len(lines) != 2 or not all(lines):
		return _git_refused(GIT_ERROR)
	if os.path.realpath(lines[0]) != repo_root:
		return _git_refused(GIT_NOT_REPO)

	verify = _git_finished(run_git_read(repo_root, "rev-parse", "--verify", "-q", "HEAD", limit_s=limit_s))
	if verify is None or verify.exit_code not in (0, 1):
		return _git_refused(GIT_ERROR)
	if verify.exit_code == 1:
		return _git_refused(GIT_NO_COMMIT)
	head = _git_lines(verify)
	if len(head) != 1 or not GIT_OBJECT_NAME.fullmatch(head[0]):
		return _git_refused(GIT_ERROR)

	abbrev = _git_finished(run_git_read(repo_root, "rev-parse", "--abbrev-ref", "HEAD", limit_s=limit_s))
	if abbrev is None or abbrev.exit_code != 0:
		return _git_refused(GIT_ERROR)
	branch = _git_lines(abbrev)
	if len(branch) != 1 or not branch[0]:
		return _git_refused(GIT_ERROR)
	if branch[0] == "HEAD":
		return _git_refused(GIT_DETACHED)

	git_path_args = [arg for name in GIT_STATE_FILES for arg in ("--git-path", name)]
	paths = _git_finished(run_git_read(repo_root, "rev-parse", *git_path_args, limit_s=limit_s))
	if paths is None or paths.exit_code != 0:
		return _git_refused(GIT_ERROR)
	state_files = _git_lines(paths)
	if len(state_files) != len(GIT_STATE_FILES) or not all(state_files):
		return _git_refused(GIT_ERROR)
	existing = [os.path.exists(os.path.join(repo_root, path)) for path in state_files]
	if existing[0]:
		return _git_refused(GIT_LOCKED)
	if any(existing[1:]):
		return _git_refused(GIT_IN_PROGRESS)

	# `./` keeps a leading `:` from being read as pathspec magic, which check-ignore refuses.
	ignored = _git_finished(
		run_git_read(repo_root, "check-ignore", "-q", "--", f"./{rel_in_repo}", limit_s=limit_s)
	)
	if ignored is None or ignored.exit_code not in (0, 1):
		return _git_refused(GIT_ERROR)
	if ignored.exit_code == 0:
		return _git_refused(GIT_IGNORED)

	status = _git_finished(
		run_git_read(
			repo_root,
			"status",
			"--porcelain=v1",
			"-z",
			"--untracked-files=all",
			"--",
			f":(literal){rel_in_repo}",
			limit_s=limit_s,
		)
	)
	if status is None or status.exit_code != 0:
		return _git_refused(GIT_ERROR)
	if status.stdout:
		return _git_refused(GIT_DIRTY)

	# Step 7: the upstream from local remote refs only (no fetch); a URL-like name is masked (NFR-8).
	upstream = _git_finished(
		run_git_read(
			repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", limit_s=limit_s
		)
	)
	if upstream is None:
		return _git_refused(GIT_ERROR)
	upstream_ref, ahead_count = "", 0
	if upstream.exit_code == 0:
		ref = _git_lines(upstream)
		if len(ref) != 1 or not ref[0]:
			return _git_refused(GIT_ERROR)
		upstream_ref = GIT_MASKED_UPSTREAM if "://" in ref[0] or "@" in ref[0] else ref[0]
		ahead = _git_finished(
			run_git_read(repo_root, "rev-list", "--count", "@{upstream}..HEAD", limit_s=limit_s)
		)
		if ahead is None or ahead.exit_code != 0:
			return _git_refused(GIT_ERROR)
		count = _git_lines(ahead)
		if len(count) != 1 or not count[0].isascii() or not count[0].isdigit():
			return _git_refused(GIT_ERROR)
		ahead_count = int(count[0])
	return GitState(
		refusal=None,
		repo_root=repo_root,
		rel_in_repo=rel_in_repo,
		branch=branch[0],
		head=head[0],
		upstream_ref=upstream_ref,
		ahead_count=ahead_count,
	)


@dataclass(frozen=True)
class CommitSummary:
	commit: str
	parents: tuple[str, ...]
	paths: tuple[str, ...]  # paths HEAD changed against its own parent (diff-tree), sorted by git
	branch: str | None  # None when HEAD is detached
	author_email: str  # author email of the HEAD commit


def _check_rev(rev) -> None:
	if not isinstance(rev, str) or not (rev == "HEAD" or GIT_OBJECT_NAME.fullmatch(rev)):
		raise ValueError(f"rev must be HEAD or a full object name: {rev!r}")


def _check_rel_in_repo(rel_in_repo) -> None:
	if (
		not isinstance(rel_in_repo, str)
		or not rel_in_repo
		or "\0" in rel_in_repo
		or any(part in ("", ".", "..") for part in rel_in_repo.split("/"))
	):
		raise ValueError(f"rel_in_repo must be a normalized relative path: {rel_in_repo!r}")


def _git_failed(what: str) -> RuntimeError:
	_logger().warning("git %s could not be read", what)
	return RuntimeError(f"{GIT_ERROR}: {what}")


def git_head(repo_root: str) -> str | None:
	"""The HEAD commit of repo_root; None when there is none or git could not tell (timeout, error)."""
	run = _git_finished(run_git_read(repo_root, "rev-parse", "--verify", "-q", "HEAD"))
	if run is None or run.exit_code != 0:
		return None
	head = _git_lines(run)
	return head[0] if len(head) == 1 and GIT_OBJECT_NAME.fullmatch(head[0]) else None


def git_commit_summary(repo_root: str) -> CommitSummary:
	"""HEAD compared with its own parent (design 3.2, [Sửa vòng 2]); RuntimeError when git cannot be read.

	Commit, parents and author email come from `rev-list` (diff-tree prints nothing for a merge); the
	paths come from `diff-tree` of that commit, which lists none for a merge (two parents).
	"""
	meta = _git_finished(
		run_git_read(repo_root, "rev-list", "-1", "--no-commit-header", "--format=%H%x00%P%x00%ae", "HEAD")
	)
	if meta is None or meta.exit_code != 0:
		raise _git_failed("HEAD commit")
	lines = _git_lines(meta)
	fields = lines[0].split("\0") if len(lines) == 1 else []
	if len(fields) != 3:
		raise _git_failed("HEAD commit")
	commit, parent_text, author_email = fields
	parents = tuple(parent_text.split(" ")) if parent_text else ()
	if not all(GIT_OBJECT_NAME.fullmatch(name) for name in (commit, *parents)):
		raise _git_failed("HEAD commit")

	changed = _git_finished(
		run_git_read(
			repo_root,
			"diff-tree",
			"-r",
			"-z",
			"--root",
			"--no-commit-id",
			"--no-renames",
			"--name-only",
			commit,
		)
	)
	if changed is None or changed.exit_code != 0:
		raise _git_failed("HEAD paths")
	text = os.fsdecode(changed.stdout)
	paths = tuple(text[:-1].split("\0")) if text else ()
	if text and (not text.endswith("\0") or not all(paths)):
		raise _git_failed("HEAD paths")

	abbrev = _git_finished(run_git_read(repo_root, "rev-parse", "--abbrev-ref", "HEAD"))
	if abbrev is None or abbrev.exit_code != 0:
		raise _git_failed("HEAD branch")
	branch = _git_lines(abbrev)
	if len(branch) != 1 or not branch[0]:
		raise _git_failed("HEAD branch")
	return CommitSummary(
		commit=commit,
		parents=parents,
		paths=paths,
		branch=None if branch[0] == "HEAD" else branch[0],
		author_email=author_email,
	)


def git_blob(repo_root: str, commit: str, rel_in_repo: str) -> bytes | None:
	"""The bytes of rel_in_repo in the tree of commit; None when the path is not in that tree.

	`<commit>:<rel>` is a tree path, not a pathspec (design-addendum-2 QĐ-A1). The commit is checked
	first because git exits 128 both for a missing commit and for a missing path. A path that is not a
	file (directory, submodule), a timeout or any other git error is a RuntimeError, never None.
	"""
	_check_rev(commit)
	_check_rel_in_repo(rel_in_repo)
	kind = _git_finished(run_git_read(repo_root, "cat-file", "-t", commit))
	if kind is None or kind.exit_code != 0 or _git_lines(kind) != ["commit"]:
		raise _git_failed("commit of blob")
	spec = f"{commit}:{rel_in_repo}"
	kind = _git_finished(run_git_read(repo_root, "cat-file", "-t", spec))
	if kind is None or kind.exit_code not in (0, 128):
		raise _git_failed("blob type")
	if kind.exit_code == 128:
		return None
	if _git_lines(kind) != ["blob"]:
		raise _git_failed("blob type")
	blob = _git_finished(run_git_read(repo_root, "cat-file", "blob", spec))
	if blob is None or blob.exit_code != 0:
		raise _git_failed("blob")
	return blob.stdout


def git_is_ancestor(repo_root: str, older: str, newer: str) -> bool | None:
	"""True when older is an ancestor of (or equal to) newer, False when not, None on any git error."""
	_check_rev(older)
	_check_rev(newer)
	run = _git_finished(run_git_read(repo_root, "merge-base", "--is-ancestor", older, newer))
	if run is None or run.exit_code not in (0, 1):
		return None
	return run.exit_code == 0


TOOLS: list[ToolSpec] = [
	ToolSpec(
		"search_source",
		"read",
		_schema(
			"search_source",
			"Tìm chuỗi cố định (không phân biệt hoa thường) trong mã nguồn các app.",
			{
				"pattern": {"type": "string", "minLength": PATTERN_MIN_CHARS, "maxLength": PATTERN_MAX_CHARS},
				"app": {"type": "string", "minLength": 1},
				"extension": {"type": "string", "pattern": SEARCH_EXTENSION.pattern},
			},
			["pattern"],
		),
		search_source,
	),
	ToolSpec(
		"read_source",
		"read",
		_schema(
			"read_source",
			"Đọc một đoạn file mã nguồn theo dòng.",
			{
				"path": {"type": "string", "minLength": 1},
				"offset": {"type": "integer", "minimum": 1},
				"limit": {"type": "integer", "minimum": 1, "maximum": READ_MAX_LINES},
			},
			["path"],
		),
		read_source,
	),
	ToolSpec(
		"git_source",
		"read",
		_schema(
			"git_source",
			"Chạy git log hoặc git blame (chỉ đọc) trên kho git của một app.",
			{
				"app": {"type": "string", "minLength": 1},
				"subcommand": {"type": "string", "enum": sorted(GIT_SUBCOMMANDS)},
				"args": {"type": "array", "maxItems": GIT_MAX_ARGS, "items": {"type": "string"}},
			},
			["app", "subcommand"],
		),
		git_source,
	),
]
