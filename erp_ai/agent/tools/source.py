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
# Design table 3.2: the git refusal sentences of read_git_state are a contract with the tests.
GIT_NOT_REPO = "thư mục app không phải gốc một kho git"
GIT_NO_COMMIT = "kho git của app chưa có commit nào"
GIT_DETACHED = "HEAD của kho git không nằm trên nhánh nào (detached)"
GIT_LOCKED = "kho git đang bị khóa (index.lock): có thao tác git khác đang chạy hoặc bị dừng giữa chừng"
GIT_IN_PROGRESS = "kho git đang dở merge, rebase, cherry-pick hoặc revert"
GIT_IGNORED = "file đích bị git bỏ qua (.gitignore)"
GIT_DIRTY = "file đích có thay đổi chưa commit"
GIT_ERROR = "không đọc được trạng thái git"
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


@dataclass(frozen=True)
class GitState:
	refusal: str | None  # a sentence of design table 3.2; None = the target can be committed
	repo_root: str | None  # real path of the repo root, which is the app directory (D-20)
	rel_in_repo: str | None
	branch: str | None
	head: str | None
	upstream_ref: str = ""
	ahead_count: int = 0


def _git_refused(reason) -> GitState:
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
	return GitState(
		refusal=None, repo_root=repo_root, rel_in_repo=rel_in_repo, branch=branch[0], head=head[0]
	)


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
