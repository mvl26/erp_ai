import ast
import json
import os
from dataclasses import dataclass

import erp_ai
from erp_ai.agent.tools import source
from erp_ai.constants import (
	CHANGE_MAX_COMMANDS,
	CHANGE_MAX_FILE_OPS,
	CHANGE_MAX_TOTAL_BYTES,
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CONSOLE_COMMAND,
	CONSOLE_SCRIPT_MAX_CHARS,
	CORE_APPS,
)

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
BLOCK_TOO_MANY_OPS = f"khối có hơn {CHANGE_MAX_FILE_OPS} mục file"
BLOCK_TOO_MANY_COMMANDS = f"khối có hơn {CHANGE_MAX_COMMANDS} lệnh"
BLOCK_TWO_APPS = "các mục file thuộc hai app {a} và {b}; mỗi app một đề xuất"
BLOCK_PATH_TWICE = "đường dẫn trùng hoặc nằm trong đường dẫn khác của cùng khối"
OP_UNKNOWN = "loại mục phải là edit, create, delete hoặc rename"
OP_FIELDS = "mục {action} thiếu hoặc thừa trường"
NOT_REGULAR_FILE = "đường dẫn không phải file thường"
EXECUTABLE_FILE = "file có quyền thực thi, bot không xóa hay đổi tên được"
# design-addendum-1 A-1.3: the total counts the stored `diff` too.
BLOCK_TOO_LARGE = f"tổng nội dung của khối (kể cả diff) lớn hơn {CHANGE_MAX_TOTAL_BYTES // (1024 * 1024)} MiB"
PY_SYNTAX = "file .py không biên dịch được: dòng {n}"
JSON_SYNTAX = "file .json không phải JSON hợp lệ: dòng {n}"
PY_SUFFIX = ".py"
JSON_SUFFIX = ".json"
RESTART_PLACE = "restart chỉ được một lần và phải là lệnh cuối"
RESTART_NEEDS_MIGRATE = "khối có file và restart phải có migrate đứng trước restart"
PY_NEEDS_RESTART = "khối có file .py phải kết thúc bằng migrate rồi restart"
RESTART_WITHOUT_PY = "khối có file nhưng không có file .py thì không restart"
# Prefix of a reason tied to one file item, n counted from 1 (design 3.1).
OP_PREFIX = "mục {number} ({path}): "
# Prefix of a reason tied to one command, n counted from 1 (design 3.1).
COMMAND_PREFIX = "lệnh {number}: "

# Fields of `FileOp` each kind needs as `str` (True) or leaves `None` (False): new_path, before, after.
OP_SHAPES = {
	CHANGE_OP_EDIT: (False, True, True),
	CHANGE_OP_CREATE: (False, False, True),
	CHANGE_OP_DELETE: (False, True, False),
	CHANGE_OP_RENAME: (True, True, True),
}
# The model's `action` name of each kind, as the sentence `OP_FIELDS` shows it.
OP_ACTIONS = {
	CHANGE_OP_EDIT: "edit",
	CHANGE_OP_CREATE: "create",
	CHANGE_OP_DELETE: "delete",
	CHANGE_OP_RENAME: "rename",
}

# Command table of design 3.1: the only bench argument shapes an agent may propose (ADR-011 QĐ 4).
# No subcommand here runs git in an app repo (ADR-022 QĐ 2).
SITE_COMMANDS = ("migrate", "clear-cache", "clear-website-cache", "list-apps")
MIGRATE_COMMAND = SITE_COMMANDS[0]  # must come before `restart` in a block with files (design 3.2)
BUILD_COMMAND = "build"
VERSION_COMMAND = "version"
# CHG-002 design 3.2 (ADR-040 QĐ 6): the plain form only, shape `["restart"]`.
RESTART_COMMAND = "restart"
BENCH_COMMANDS = (*SITE_COMMANDS, BUILD_COMMAND, VERSION_COMMAND, RESTART_COMMAND)
SITE_FLAG = "--site"
APP_FLAG = "--app"
FORCE_FLAG = "--force"
CONSOLE_EMPTY = "script trống"
CONSOLE_TOO_LONG = "script dài quá {max} ký tự"
CONSOLE_SYNTAX = "script không phải Python hợp lệ (dòng {line})"
CONSOLE_IMPORT = (
	"script chỉ được import frappe, erpnext, hrms, helpdesk, json, datetime, decimal, re, math (gặp {name})"
)
CONSOLE_CALL = "script không được gọi {name}"
CONSOLE_ATTR = "script không được dùng .{name}"
CONSOLE_TEXT = "script không được nhắc tới {text}"
CONSOLE_IMPORT_ROOTS = ("frappe", "erpnext", "hrms", "helpdesk", "json", "datetime", "decimal", "re", "math")
CONSOLE_FORBIDDEN_CALLS = (
	"eval", "exec", "compile", "open", "__import__", "getattr", "setattr", "delattr",
	"globals", "locals", "vars", "breakpoint", "input", "exit", "quit",
)  # fmt: skip
CONSOLE_FORBIDDEN_ATTRS = (
	"commit", "rollback", "set_user", "get_password", "get_decrypted_password", "conf",
	"get_site_config", "environ", "system", "popen", "connect", "destroy",
)  # fmt: skip
CONSOLE_FORBIDDEN_TEXT = ("erp ai", "__auth", "site_config", ".git")
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


@dataclass(frozen=True)
class OpTarget:
	"""One file item that passed `check_block` (CHG-002 design 3.2).

	`full_path` and `full_new_path` are the real paths of `path` and of a rename's `new_path` (else
	`None`); `new_dirs` are the real paths of the folders to create, top down; `guard` is the
	`check_write_path` result of `path`.
	"""

	op: FileOp
	full_path: str
	full_new_path: str | None
	new_dirs: tuple[str, ...]
	guard: GuardResult


@dataclass(frozen=True)
class BlockCheck:
	"""Result of `check_block`: the first refusal `reason` (`None` passes), the app of the file items
	(`None` for a block with only commands or a refused one) and one `OpTarget` per item, in order."""

	reason: str | None
	app: str | None
	targets: tuple[OpTarget, ...]


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


def _shape_reason(op: FileOp) -> str | None:
	"""`OP_UNKNOWN` for a kind outside `CHANGE_OPS`; `OP_FIELDS` when a field the kind needs is not a
	string or one it leaves out is set (`OP_SHAPES`), or when `path` (or a rename's `new_path`) is
	empty after `strip()` (design-addendum-5 P-6)."""
	if not isinstance(op.kind, str) or op.kind not in OP_SHAPES:
		return OP_UNKNOWN
	fields = (op.new_path, op.before, op.after)
	if (
		not _is_named(op.path)
		or any(
			not isinstance(value, str) if needed else value is not None
			for value, needed in zip(fields, OP_SHAPES[op.kind], strict=True)
		)
		or (op.kind == CHANGE_OP_RENAME and not _is_named(op.new_path))
	):
		return OP_FIELDS.format(action=OP_ACTIONS[op.kind])
	return None


def _is_named(path) -> bool:
	return isinstance(path, str) and bool(path.strip())


def _paths_of(op: FileOp) -> tuple[str, ...]:
	return (op.path,) if op.new_path is None else (op.path, op.new_path)


def _overlaps(path: str, other: str) -> bool:
	return path == other or path.startswith(other + os.sep) or other.startswith(path + os.sep)


def _new_dirs(guard: GuardResult) -> tuple[tuple[str, str], ...]:
	"""`(rel, real path)` of every missing folder above a checked target, top down; the app folder exists."""
	missing = []
	rel, full = os.path.dirname(guard.rel_path), os.path.dirname(guard.full_path)
	while os.sep in rel and not os.path.lexists(full):
		missing.append((rel, full))
		rel, full = os.path.dirname(rel), os.path.dirname(full)
	return tuple(reversed(missing))


def _utf8(text: str) -> bytes:
	"""UTF-8 bytes of `text`; a lone surrogate is kept as bytes so `text_refusal` refuses it as not UTF-8."""
	return text.encode("utf-8", errors="surrogatepass")


def _syntax_reason(text: str, rel: str) -> str | None:
	"""Design 3.2 step 2: a `.py` target must compile (never run), a `.json` target must parse."""
	if rel.endswith(PY_SUFFIX):
		try:
			compile(text, rel, "exec", dont_inherit=True)
		except SyntaxError as error:
			return PY_SYNTAX.format(n=error.lineno or 0)
		except (RecursionError, MemoryError):
			return PY_SYNTAX.format(n=0)  # Too deep for the parser: refused, with no line to name.
	elif rel.endswith(JSON_SUFFIX):
		try:
			json.loads(text)
		except ValueError as error:
			return JSON_SYNTAX.format(n=getattr(error, "lineno", 0))
		except RecursionError:
			return JSON_SYNTAX.format(n=0)  # Nested deeper than the decoder can go: refused, no line.
	return None


def _content_reason(op: FileOp, source_rel: str, target_rel: str) -> str | None:
	"""`source.text_refusal` for the content before (under the source name) and after (under the target
	name), then the syntax of the content after for an edit, a created file and a rename target."""
	if op.before is not None:
		reason = source.text_refusal(source_rel, _utf8(op.before))
		if reason is not None:
			return reason
	if op.after is None:
		return None
	return source.text_refusal(target_rel, _utf8(op.after)) or _syntax_reason(op.after, target_rel)


def _check_op(op: FileOp, seen: list[str], allowed_apps, block_app: str | None, at_apply: bool):
	"""Design 3.2 step 2 for one item: an `OpTarget`, or the refusal reason as a `str`.

	`seen` holds the normalized paths of the earlier items and gets this item's; `block_app` is the app
	of item 1 (`None` while checking item 1 itself).
	"""
	reason = _shape_reason(op)
	if reason is not None:
		return reason
	paths = _paths_of(op)
	for path in paths:
		normal = os.path.normpath(path)
		if any(_overlaps(normal, other) for other in seen):
			return BLOCK_PATH_TWICE
		seen.append(normal)
	# Only a created file and a rename target are new; an edit, a deletion and a rename source exist.
	new_files = (op.kind == CHANGE_OP_CREATE, True)
	guards = []
	for path, new_file in zip(paths, new_files, strict=False):
		guard = check_write_path(path, allowed_apps, new_file=new_file, read_git=not at_apply)
		if guard.reason is not None:
			return guard.reason
		guards.append(guard)
	new_dirs = _new_dirs(guards[-1]) if op.kind in (CHANGE_OP_CREATE, CHANGE_OP_RENAME) else ()
	for rel, _full in new_dirs:
		reason = check_write_path(rel, allowed_apps, new_file=True, read_git=False).reason
		if reason is not None:
			return reason
	block_app = block_app or guards[0].app
	other_app = next((guard.app for guard in guards if guard.app != block_app), None)
	if other_app is not None:
		return BLOCK_TWO_APPS.format(a=block_app, b=other_app)
	reason = _content_reason(op, guards[0].rel_path, guards[-1].rel_path)
	if reason is not None:
		return reason
	return OpTarget(
		op=op,
		full_path=guards[0].full_path,
		full_new_path=guards[1].full_path if len(guards) > 1 else None,
		new_dirs=tuple(full for _rel, full in new_dirs),
		guard=guards[0],
	)


def check_block(
	ops,
	commands,
	allowed_apps,
	site,
	*,
	at_apply: bool,
	diff_text: str,
	legacy: bool = False,
) -> BlockCheck:
	"""Check a whole block at proposal time (`at_apply=False`) and again at apply time; first reason wins.

	CHG-002 design 3.2: 1. no item and no command → `BLOCK_EMPTY`; more than `CHANGE_MAX_FILE_OPS`
	items → `BLOCK_TOO_MANY_OPS`; more than `CHANGE_MAX_COMMANDS` commands → `BLOCK_TOO_MANY_COMMANDS`.
	2. each item in order, its reason prefixed by `OP_PREFIX`: shape (`OP_UNKNOWN`, `OP_FIELDS`); a path
	equal to or inside another path of the block → `BLOCK_PATH_TWICE`; `check_write_path` for every
	path of the item, with the git state read only at proposal time; `check_write_path` for each folder
	to create; an app other than item 1's → `BLOCK_TWO_APPS`; `source.text_refusal` of the content
	before and after (the only per-file size limit); `PY_SYNTAX` / `JSON_SYNTAX` for the content after
	of a `.py` / `.json` target. 3. the UTF-8 bytes of every before and after plus `diff_text` (the
	stored `diff`, no default so no caller forgets it) over `CHANGE_MAX_TOTAL_BYTES` → `BLOCK_TOO_LARGE`;
	exactly the limit passes. 4. each command through `check_bench_args`, its reason prefixed by
	`COMMAND_PREFIX`; `["restart"]` more than once or not last → `RESTART_PLACE`; only for a block with
	file items: unless `legacy`, a `.py` on any path of the block (a rename source and target too)
	without `restart` → `PY_NEEDS_RESTART`, `restart` without one → `RESTART_WITHOUT_PY`; `restart`
	with no `[--site, site, migrate]` before it → `RESTART_NEEDS_MIGRATE`. A block with only commands
	may hold a lone `["restart"]` (R-5).
	"""
	ops, commands = tuple(ops), tuple(commands)
	if not ops and not commands:
		return BlockCheck(reason=BLOCK_EMPTY, app=None, targets=())
	if len(ops) > CHANGE_MAX_FILE_OPS:
		return BlockCheck(reason=BLOCK_TOO_MANY_OPS, app=None, targets=())
	if len(commands) > CHANGE_MAX_COMMANDS:
		return BlockCheck(reason=BLOCK_TOO_MANY_COMMANDS, app=None, targets=())
	app, targets, seen = None, [], []
	for number, op in enumerate(ops, start=1):
		target = _check_op(op, seen, allowed_apps, app, at_apply)
		if isinstance(target, str):
			return BlockCheck(
				reason=OP_PREFIX.format(number=number, path=op.path) + target, app=None, targets=()
			)
		app = app or target.guard.app
		targets.append(target)
	# A rename stores its content as before and after, so it counts twice (design-addendum-1 A-1.2).
	total = sum(len(_utf8(text)) for op in ops for text in (op.before, op.after) if text is not None)
	if total + len(_utf8(diff_text)) > CHANGE_MAX_TOTAL_BYTES:
		return BlockCheck(reason=BLOCK_TOO_LARGE, app=None, targets=())
	reason = _commands_reason(ops, commands, allowed_apps, site, legacy)
	if reason is not None:
		return BlockCheck(reason=reason, app=None, targets=())
	return BlockCheck(reason=None, app=app, targets=tuple(targets))


def _commands_reason(ops: tuple, commands: tuple, allowed_apps, site, legacy: bool) -> str | None:
	"""Design 3.2 step 4, on items that already passed step 2 (so every path is a string)."""
	for number, args in enumerate(commands, start=1):
		reason = check_bench_args(args, allowed_apps, site)
		if reason is not None:
			return COMMAND_PREFIX.format(number=number) + reason
	restarts = [index for index, args in enumerate(commands) if args == [RESTART_COMMAND]]
	if restarts and restarts[0] != len(commands) - 1:  # a second restart leaves the first not last
		return RESTART_PLACE
	if not ops:
		return None
	if not legacy:
		has_py = any(path.endswith(PY_SUFFIX) for op in ops for path in _paths_of(op))
		if has_py and not restarts:
			return PY_NEEDS_RESTART
		if restarts and not has_py:
			return RESTART_WITHOUT_PY
	if restarts and [SITE_FLAG, site, MIGRATE_COMMAND] not in commands[: restarts[0]]:
		return RESTART_NEEDS_MIGRATE
	return None


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


def console_args(site: str) -> list[str]:
	"""The stored argv of a console proposal (CHG-010); kept out of BENCH_COMMANDS so the generic bench tool
	cannot make a console without a script."""
	return [SITE_FLAG, site, CONSOLE_COMMAND]


def _import_root(node) -> list[str]:
	if isinstance(node, ast.Import):
		return [alias.name.split(".")[0] for alias in node.names]
	if node.level:
		return ["." * node.level + (node.module or "")]
	return [(node.module or "").split(".")[0]]


def _tree_reason(tree) -> str | None:
	for node in ast.walk(tree):
		if isinstance(node, ast.Import | ast.ImportFrom):
			for root in _import_root(node):
				if root not in CONSOLE_IMPORT_ROOTS:
					return CONSOLE_IMPORT.format(name=root)
		elif isinstance(node, ast.Call):
			if isinstance(node.func, ast.Name) and node.func.id in CONSOLE_FORBIDDEN_CALLS:
				return CONSOLE_CALL.format(name=node.func.id)
		elif isinstance(node, ast.Attribute):
			if node.attr in CONSOLE_FORBIDDEN_ATTRS:
				return CONSOLE_ATTR.format(name=node.attr)
		elif isinstance(node, ast.Name) and node.id in CONSOLE_FORBIDDEN_CALLS:
			return CONSOLE_CALL.format(name=node.id)
	return None


def check_console_script(script) -> str | None:
	"""Static rules of a bot-drafted console script (CHG-010); the refusal reason, or None when allowed.

	Order: blank, length, forbidden text, syntax, then the first import, call or attribute violation.
	"""
	if not isinstance(script, str) or not script.strip():
		return CONSOLE_EMPTY
	if len(script) > CONSOLE_SCRIPT_MAX_CHARS:
		return CONSOLE_TOO_LONG.format(max=CONSOLE_SCRIPT_MAX_CHARS)
	lowered = script.lower()
	for text in CONSOLE_FORBIDDEN_TEXT:
		if text in lowered:
			return CONSOLE_TEXT.format(text=text)
	try:
		tree = ast.parse(script)
	except SyntaxError as error:
		return CONSOLE_SYNTAX.format(line=error.lineno or 1)
	except (ValueError, RecursionError, MemoryError):
		return CONSOLE_SYNTAX.format(line=1)
	return _tree_reason(tree)


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
