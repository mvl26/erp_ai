import os
from dataclasses import dataclass

import erp_ai
from erp_ai.agent.tools import source
from erp_ai.constants import CORE_APPS

PROTECTED_FILE_NAME = "license.txt"
GIT_DIR_NAME = ".git"
ERP_AI_APP = "erp_ai"
GITDIR_PREFIX = "gitdir:"
COMMONDIR_FILE = "commondir"
# Larger pointer files are not read: git itself rejects them (READ_GITFILE_ERR_TOO_LARGE).
MAX_POINTER_BYTES = 4096

# Refusal wording of design 3.1 (contract with the model and the tests).
PATH_INVALID = "đường dẫn không hợp lệ hoặc nằm ngoài apps/"
APP_NOT_ALLOWED = "app không có trong danh sách được sửa"
APP_FORBIDDEN = "không được sửa app erp_ai hoặc kho git của nó"
# CHG-002 design table 3.1: the name and ".git*" sentences are those of `source.text_refusal`.
NAME_FORBIDDEN = source.TEXT_SECRET_NAME
GIT_DIR = source.GIT_DIR
PATH_GIT_PATTERN = 'tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được'
PATH_SYMLINK = "đường dẫn đi qua symlink"
NESTED_REPO = "đường dẫn nằm trong một kho git lồng trong app"
CMD_SHELL = "đối số chứa ký tự điều khiển shell"
CMD_FORCE = "cờ --force bị cấm"
CMD_OTHER_SITE = "chỉ chạy cho site đang chạy"
CMD_NOT_LISTED = "lệnh không có trong danh sách cho phép"
CMD_NEEDS_APP = "lệnh build cần app"
CMD_TAKES_NO_APP = "lệnh này không nhận app"
# CHG-002 design table 3.1.
BLOCK_SHAPE = "đưa changes hoặc path, không cả hai và không thiếu cả hai"
BLOCK_EMPTY = "khối không có mục file hay lệnh nào"
OP_UNKNOWN = "loại mục phải là edit, create, delete hoặc rename"
OP_FIELDS = "mục {action} thiếu hoặc thừa trường"

# Command table of design 3.1: the only bench argument shapes an agent may propose (ADR-011 QĐ 4).
# No subcommand here runs git in an app repo (ADR-022 QĐ 2).
SITE_COMMANDS = ("migrate", "clear-cache", "clear-website-cache", "list-apps")
BUILD_COMMAND = "build"
VERSION_COMMAND = "version"
# CHG-002 design 3.2 (ADR-040 QĐ 6): the plain form only, shape `["restart"]`.
RESTART_COMMAND = "restart"
BENCH_COMMANDS = (*SITE_COMMANDS, BUILD_COMMAND, VERSION_COMMAND, RESTART_COMMAND)
SITE_FLAG = "--site"
APP_FLAG = "--app"
FORCE_FLAG = "--force"
SHELL_METACHARACTERS = (";", "|", "&", "`", "$(", ">", "<", "\n")


@dataclass(frozen=True)
class GuardResult:
	full_path: str | None
	rel_path: str | None
	app: str | None
	reason: str | None
	is_core_app: bool = False
	git: source.GitState | None = None


@dataclass(frozen=True)
class FileOp:
	"""One file item of a block proposal (CHG-002 design 3.2); `kind` is a value of `CHANGE_OPS`.

	`path` is relative to `apps/` (the source of a rename); `new_path` is the rename target, else `None`.
	`before` is `None` for a created file, `after` is `None` for a deleted one.
	"""

	kind: str
	path: str
	new_path: str | None
	before: str | None
	after: str | None
	base_hash: str | None
	after_hash: str | None


def _refused(reason: str) -> GuardResult:
	return GuardResult(full_path=None, rel_path=None, app=None, reason=reason)


def _first_line(path: str) -> str | None:
	"""First line of a regular file of at most `MAX_POINTER_BYTES`, stripped.

	Anything git would not read as a pointer (not a regular file, e.g. a FIFO or a directory; too
	large; unreadable; not UTF-8) yields `None`, which the caller treats as "no repo".
	"""
	if not os.path.isfile(path) or os.path.getsize(path) > MAX_POINTER_BYTES:
		return None
	try:
		with open(path, encoding="utf-8") as handle:
			return handle.readline(MAX_POINTER_BYTES).strip()
	except (OSError, UnicodeDecodeError):
		return None  # Unreadable pointer: git cannot follow it either, so it leads to no repo.


def _git_common_dir(entry: str) -> str | None:
	"""Return the real git common dir that a `.git` entry leads to, reading files only (no `git`).

	A `.git` directory is its own common dir; a `gitdir: X` file (worktree, submodule) leads to
	`X/<commondir>` when `X/commondir` exists, else to `X`. A relative `X` is resolved, as git does,
	from the folder holding the `.git` entry, not from where a symlinked `.git` points. A file git
	itself could not read as a `gitdir:` pointer, or a `commondir` that exists but cannot be read,
	leads to no repo, so it yields `None`.
	"""
	real = os.path.realpath(entry)
	if os.path.isdir(real):
		return real
	line = _first_line(real)
	if line is None or not line.startswith(GITDIR_PREFIX):
		return None
	gitdir = os.path.join(os.path.dirname(entry), line[len(GITDIR_PREFIX) :].strip())
	commondir_file = os.path.join(gitdir, COMMONDIR_FILE)
	if not os.path.lexists(commondir_file):
		return os.path.realpath(gitdir)
	commondir = _first_line(commondir_file)
	if commondir is None:
		return None
	return os.path.realpath(os.path.join(gitdir, commondir))


def _common_dirs_upward(start: str, stop: str | None = None, *, nearest_only: bool = False) -> set[str]:
	"""Common dirs of every `.git` entry from `start` up to `stop` (inclusive), or to `/` without `stop`.

	With `nearest_only`, the walk ends at the first `.git` entry found, the repo git itself would use.
	"""
	found = set()
	current = start
	while True:
		entry = os.path.join(current, GIT_DIR_NAME)
		if os.path.lexists(entry):
			common = _git_common_dir(entry)
			if common:
				found.add(common)
			if nearest_only:
				return found
		parent = os.path.dirname(current)
		if current == stop or parent == current:
			return found
		current = parent


def _erp_ai_common_dirs(root: str) -> set[str]:
	"""Union of the two `erp_ai` identities: the repo holding the running package and `<root>/erp_ai`."""
	running = _common_dirs_upward(os.path.dirname(os.path.realpath(erp_ai.__file__)), nearest_only=True)
	temp_app = os.path.join(root, ERP_AI_APP)
	return running | _common_dirs_upward(temp_app, temp_app)


def _is_erp_ai(target: str, root: str, app: str) -> bool:
	if app == ERP_AI_APP:
		return True
	repos = _common_dirs_upward(target, os.path.join(root, app))
	return bool(repos & _erp_ai_common_dirs(root))


def _existing_part(path: str) -> str:
	"""The longest prefix of `path` that exists on disk; a dangling symlink counts as existing."""
	while not os.path.lexists(path):
		path = os.path.dirname(path)
	return path


def _is_nested_repo(existing: str, app_dir: str) -> bool:
	"""Design 3.2 step 7: the repo git would use from the deepest existing folder is not the app folder's."""
	start = existing if os.path.isdir(existing) else os.path.dirname(existing)
	return _common_dirs_upward(start, nearest_only=True) != _common_dirs_upward(app_dir, nearest_only=True)


def _is_git_pattern(rel_in_repo: str) -> bool:
	"""Same condition as `process_runner._check_git_write_call` (design-addendum-2 QĐ-A2): a bare path
	git would read as a glob, a magic pathspec or an option cannot be committed safely."""
	return rel_in_repo.startswith((":", "-")) or bool(source.GIT_GLOB_CHARS.search(rel_in_repo))


def check_write_path(
	rel_path: str, allowed_apps: tuple[str, ...], *, new_file: bool, read_git: bool = True
) -> GuardResult:
	"""Check a write target relative to `apps/`; refusals follow steps 1-7 of CHG-002 design 3.2.

	1. invalid or outside `apps/` → `PATH_INVALID`; 2. app not listed → `APP_NOT_ALLOWED`; a listed app
	with no folder, or the app folder itself → `PATH_INVALID`; 3. `erp_ai` by repo identity →
	`APP_FORBIDDEN`; 4. `license.txt`, then `source.text_refusal` (secret name, then a ".git*"
	component) → `NAME_FORBIDDEN` / `GIT_DIR`; 5. git pattern → `PATH_GIT_PATTERN`; 6. a symlink on
	the existing part of the path (the normalized path differs from the real one) → `PATH_SYMLINK`;
	7. the nearest `.git` from the deepest existing folder of the real path is not the app folder's
	repo → `NESTED_REPO`. Any file extension passes.

	`source.resolve_safe_path` is the only path resolver; when it refuses, the same real path is only
	classified to pick the reason, and an unclassified refusal stays `PATH_INVALID`. With `read_git`
	(proposal time), a target passing every path check then needs `source.read_git_state` to pass and
	its state is returned in `git`; the apply/undo job passes `read_git=False` and reads git itself.
	"""
	if not isinstance(rel_path, str) or not rel_path.strip() or "\0" in rel_path or os.path.isabs(rel_path):
		return _refused(PATH_INVALID)
	root = os.path.realpath(source.get_source_root())
	full = source.resolve_safe_path(rel_path)
	target = full or os.path.realpath(os.path.join(root, rel_path))
	if os.path.commonpath([root, target]) != root or target == root:
		return _refused(PATH_INVALID)
	rel = os.path.relpath(target, root)
	parts = rel.split(os.sep)
	if parts[0] not in allowed_apps:
		return _refused(APP_NOT_ALLOWED)
	if len(parts) == 1 or not os.path.isdir(os.path.join(root, parts[0])):
		return _refused(PATH_INVALID)
	if _is_erp_ai(target, root, parts[0]):
		return _refused(APP_FORBIDDEN)
	if parts[-1].lower() == PROTECTED_FILE_NAME:
		return _refused(NAME_FORBIDDEN)
	name_reason = source.text_refusal(rel)
	if name_reason is not None:
		return _refused(name_reason)
	if _is_git_pattern(os.sep.join(parts[1:])):
		return _refused(PATH_GIT_PATTERN)
	if full is None:
		return _refused(PATH_INVALID)
	# Compared with the real path, so a symlink followed by ".." is caught too: normpath drops
	# "link/.." as text while realpath applies ".." to the link's target.
	if os.path.normpath(os.path.join(root, rel_path)) != full:
		return _refused(PATH_SYMLINK)
	if _is_nested_repo(_existing_part(full), os.path.join(root, parts[0])):
		return _refused(NESTED_REPO)
	state = None
	if read_git:
		state = source.read_git_state(full, new_file=new_file)
		if state.refusal is not None:
			return _refused(state.refusal)
	return GuardResult(
		full_path=full,
		rel_path=rel,
		app=parts[0],
		reason=None,
		is_core_app=parts[0] in CORE_APPS,
		git=state,
	)


def _app_names(allowed_apps) -> tuple[str, ...]:
	"""`allowed_apps` as a tuple of names; anything but a collection of strings allows no app.

	A plain string is refused on purpose: `in` on it would match any substring of the name.
	"""
	if not isinstance(allowed_apps, tuple | list | set | frozenset):
		return ()
	if not all(isinstance(name, str) for name in allowed_apps):
		return ()
	return tuple(allowed_apps)


def _is_site(site) -> bool:
	return isinstance(site, str) and bool(site.strip())


def _build_app_reason(app, allowed_apps: tuple[str, ...]) -> str | None:
	"""Reason of design table 3.1 why `app` cannot be built, or `None` when it passes the app guard.

	The name must be one plain folder directly under `apps/`, listed, resolving (symlinks followed) to
	itself, and not `erp_ai` or a repo sharing its git common dir.
	"""
	if not isinstance(app, str) or app not in allowed_apps or "\0" in app:
		return APP_NOT_ALLOWED
	root = os.path.realpath(source.get_source_root())
	target = os.path.realpath(os.path.join(root, app))
	if os.path.dirname(target) != root or os.path.basename(target) != app:
		return APP_NOT_ALLOWED
	if _is_erp_ai(target, root, app):
		return APP_FORBIDDEN
	return None


def _bench_shape(command, app, allowed_apps: tuple[str, ...], site) -> list[str] | str:
	"""The argument list of design table 3.1 for one command, or the refusal reason."""
	if not isinstance(command, str) or command not in BENCH_COMMANDS:
		return CMD_NOT_LISTED
	if command == BUILD_COMMAND:
		if app is None or (isinstance(app, str) and not app.strip()):
			return CMD_NEEDS_APP
		return _build_app_reason(app, allowed_apps) or [BUILD_COMMAND, APP_FLAG, app]
	if app is not None:
		return CMD_TAKES_NO_APP
	if command in (VERSION_COMMAND, RESTART_COMMAND):
		return [command]
	if not _is_site(site):
		return CMD_OTHER_SITE
	return [SITE_FLAG, site, command]


def build_bench_args(
	command: str, app: str | None, allowed_apps: tuple[str, ...], site: str
) -> list[str] | str:
	"""Build the stored `command_args` of design table 3.1; a `str` result is the refusal reason.

	The built list then goes through `check_bench_args`, so a name or site carrying a shell
	metacharacter is refused with the same sentence as at apply time.
	"""
	args = _bench_shape(command, app, _app_names(allowed_apps), site)
	if isinstance(args, str):
		return args
	return check_bench_args(args, allowed_apps, site) or args


def _site_values(args: list[str]) -> list[str | None]:
	"""Every value given to `--site` (`--site X` or `--site=X`); a trailing `--site` gives `None`."""
	values = []
	for index, arg in enumerate(args):
		if arg == SITE_FLAG:
			values.append(args[index + 1] if index + 1 < len(args) else None)
		elif arg.startswith(SITE_FLAG + "="):
			values.append(arg[len(SITE_FLAG) + 1 :])
	return values


def check_bench_args(args: list[str], allowed_apps: tuple[str, ...], site: str) -> str | None:
	"""Check stored bench arguments in the order of design 3.2; `None` lets them run.

	1. shell metacharacter, 2. `--force`, 3. `--site` other than the running site, 4. not exactly
	one shape of table 3.1 for the current `allowed_apps`. Anything but a non-empty list of strings
	matches no shape.
	"""
	if not isinstance(args, list) or not args or not all(isinstance(arg, str) for arg in args):
		return CMD_NOT_LISTED
	if any(char in arg for arg in args for char in SHELL_METACHARACTERS):
		return CMD_SHELL
	if any(arg == FORCE_FLAG or arg.startswith(FORCE_FLAG + "=") for arg in args):
		return CMD_FORCE
	if any(not _is_site(site) or value != site for value in _site_values(args)):
		return CMD_OTHER_SITE
	apps = _app_names(allowed_apps)
	if len(args) == 3 and args[:2] == [BUILD_COMMAND, APP_FLAG]:
		expected = _bench_shape(BUILD_COMMAND, args[2], apps, site)
	elif len(args) == 3 and args[0] == SITE_FLAG:
		expected = _bench_shape(args[2], None, apps, site)
	else:
		expected = _bench_shape(args[0], None, apps, site)
	return None if expected == args else CMD_NOT_LISTED
