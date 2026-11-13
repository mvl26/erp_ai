import os
import re
import subprocess
import time
from dataclasses import dataclass

import frappe

from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolSpec
from erp_ai.constants import BOT_GIT_EMAIL, BOT_GIT_NAME

logger = frappe.logger("erp_ai.source")

DUOI_CHO_PHEP = {".py", ".js", ".vue", ".json", ".md", ".html", ".css", ".txt"}
TEN_CAM = re.compile(
	r"(site_config\.json|common_site_config\.json|\.env|\.pem|\.key|" r"id_rsa|credential|secret|password)",
	re.I,
)

READ_MAX_LINES = 400
READ_DEFAULT_LINES = 200
SEARCH_MAX_HITS = 40
SEARCH_TIME_BUDGET_S = 30
SEARCH_FILE_MAX_BYTES = 1024 * 1024
SEARCH_TEXT_MAX_CHARS = 300
PATTERN_MIN_CHARS = 2
PATTERN_MAX_CHARS = 200
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
GIT_HOOKS_DIR = os.path.realpath(
	os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "git_no_hooks")
)
GIT_BACKSTOP_EXTRA_S = 5
GIT_DEFAULT_PATH = "/usr/bin:/bin"
KILLED_EXIT_CODES = (-9, 124, 137)
# ADR-022 QĐ 2: the diff option that makes diff-tree/rev-list write a file; git accepts unambiguous abbreviations.
GIT_WRITE_OPTION = "--output"


def get_source_root():
	return os.path.realpath(os.path.dirname(os.path.dirname(frappe.get_app_path("frappe"))))


def _inside(root, full):
	return os.path.commonpath([root, full]) == root and full != root


def resolve_safe_path(rel):
	"""Return the real path of an allowed source file under the root, else None."""
	if not isinstance(rel, str) or not rel.strip() or "\0" in rel:
		return None
	root = os.path.realpath(get_source_root())
	full = os.path.realpath(os.path.join(root, rel))
	if not _inside(root, full):
		return None
	if TEN_CAM.search(os.path.relpath(full, root)):
		return None
	if os.path.isfile(full) and os.path.splitext(full)[1].lower() not in DUOI_CHO_PHEP:
		return None
	return full


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
		with open(full, encoding="utf-8", errors="replace") as handle:
			lines = handle.read().splitlines()
		chunk = lines[offset - 1 : offset - 1 + limit]
		return {
			"ok": True,
			"path": os.path.relpath(full, os.path.realpath(get_source_root())),
			"from_line": offset,
			"total_lines": len(lines),
			"content": "\n".join(chunk),
		}
	except Exception:
		logger.exception("read_source failed")
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


def _scan_file(full, rel, needle, hits):
	try:
		with open(full, encoding="utf-8", errors="replace") as handle:
			for number, line in enumerate(handle, 1):
				if needle in line.lower():
					text = line.strip()[:SEARCH_TEXT_MAX_CHARS]
					hits.append({"path": rel, "line": number, "text": text})
					if len(hits) >= SEARCH_MAX_HITS:
						return
	except OSError:
		return


def search_source(args, ctx):
	try:
		args = args or {}
		pattern = args.get("pattern")
		if not isinstance(pattern, str) or not PATTERN_MIN_CHARS <= len(pattern) <= PATTERN_MAX_CHARS:
			return _refuse("Mẫu tìm phải dài từ 2 đến 200 ký tự")
		extension = args.get("extension")
		if extension is not None and extension not in DUOI_CHO_PHEP:
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
				if extension and os.path.splitext(name)[1].lower() != extension:
					continue
				full = resolve_safe_path(os.path.relpath(os.path.join(folder, name), root))
				if full is None or not os.path.isfile(full):
					continue
				if os.path.getsize(full) > SEARCH_FILE_MAX_BYTES:
					continue
				_scan_file(full, os.path.relpath(full, root), needle, hits)
		return {"ok": True, "hits": hits}
	except Exception:
		logger.exception("search_source failed")
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
			logger.warning("git_source %s exit %s", sub, done.returncode)
			return _refuse(f"git báo lỗi (mã {done.returncode})")
		return {"ok": True, "output": (done.stdout or "")[:GIT_OUTPUT_MAX_CHARS]}
	except FileNotFoundError:
		return _refuse("chưa cài git trên máy chủ")
	except subprocess.TimeoutExpired:
		logger.warning("git_source timed out")
		return _refuse("git chạy quá thời gian cho phép")
	except Exception:
		logger.exception("git_source failed")
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
		if name.startswith(GIT_WRITE_OPTION) or (len(name) > 2 and GIT_WRITE_OPTION.startswith(name)):
			raise ValueError(f"git argument not allowed, it writes a file: {name!r}")
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
		logger.warning("git %s timed out after the backstop", subcommand)
		return GitRun(exit_code=None, stdout=b"", timed_out=True)
	except OSError as error:
		logger.warning("git %s could not start: %s", subcommand, type(error).__name__)
		return GitRun(exit_code=None, stdout=b"", timed_out=False)
	timed_out = done.returncode in KILLED_EXIT_CODES and time.monotonic() - started >= limit_s
	return GitRun(exit_code=done.returncode, stdout=done.stdout or b"", timed_out=timed_out)


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
				"extension": {"type": "string", "enum": sorted(DUOI_CHO_PHEP)},
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
