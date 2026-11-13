import os
from dataclasses import dataclass

import erp_ai
from erp_ai.agent.tools import source

PROTECTED_FILE_NAME = "license.txt"
GIT_DIR_NAME = ".git"
ERP_AI_APP = "erp_ai"
GITDIR_PREFIX = "gitdir:"
COMMONDIR_FILE = "commondir"

# Refusal wording of design 3.1 (contract with the model and the tests).
PATH_INVALID = "đường dẫn không hợp lệ hoặc nằm ngoài apps/"
APP_NOT_ALLOWED = "app không có trong danh sách được sửa"
APP_FORBIDDEN = "không được sửa app erp_ai hoặc kho git của nó"
NAME_FORBIDDEN = "tên file thuộc loại bí mật hoặc được bảo vệ"
EXT_FORBIDDEN = "đuôi file không được phép"
GIT_DIR = "không được chạm thư mục .git"


@dataclass(frozen=True)
class GuardResult:
	full_path: str | None
	rel_path: str | None
	app: str | None
	reason: str | None


def _refused(reason: str) -> GuardResult:
	return GuardResult(full_path=None, rel_path=None, app=None, reason=reason)


def _git_common_dir(entry: str) -> str | None:
	"""Return the real git common dir that a `.git` entry leads to, reading files only (no `git`).

	A `.git` directory is its own common dir; a `gitdir: X` file (worktree, submodule) leads to
	`X/<commondir>` when `X/commondir` exists, else to `X`. A file git itself could not read as a
	`gitdir:` pointer leads to no repo, so it yields `None`.
	"""
	real = os.path.realpath(entry)
	if os.path.isdir(real):
		return real
	try:
		with open(real, encoding="utf-8") as handle:
			line = handle.readline().strip()
	except (OSError, UnicodeDecodeError):
		return None
	if not line.startswith(GITDIR_PREFIX):
		return None
	gitdir = os.path.join(os.path.dirname(real), line[len(GITDIR_PREFIX) :].strip())
	try:
		with open(os.path.join(gitdir, COMMONDIR_FILE), encoding="utf-8") as handle:
			commondir = handle.readline().strip()
	except FileNotFoundError:
		return os.path.realpath(gitdir)
	except (OSError, UnicodeDecodeError):
		return None
	return os.path.realpath(os.path.join(gitdir, commondir))


def _common_dirs_upward(start: str, stop: str | None = None) -> set[str]:
	"""Common dirs of every `.git` entry from `start` up to `stop` (inclusive), or to `/` without `stop`."""
	found = set()
	current = start
	while True:
		entry = os.path.join(current, GIT_DIR_NAME)
		if os.path.lexists(entry):
			common = _git_common_dir(entry)
			if common:
				found.add(common)
		parent = os.path.dirname(current)
		if current == stop or parent == current:
			return found
		current = parent


def _erp_ai_common_dirs(root: str) -> set[str]:
	"""Union of the two `erp_ai` identities: the repo holding the running package and `<root>/erp_ai`."""
	running = _common_dirs_upward(os.path.dirname(os.path.realpath(erp_ai.__file__)))
	temp_app = os.path.join(root, ERP_AI_APP)
	return running | _common_dirs_upward(temp_app, temp_app)


def _is_erp_ai(target: str, root: str, app: str) -> bool:
	if app == ERP_AI_APP:
		return True
	repos = _common_dirs_upward(target, os.path.join(root, app))
	return bool(repos & _erp_ai_common_dirs(root))


def check_write_path(rel_path: str, allowed_apps: tuple[str, ...], *, new_file: bool) -> GuardResult:
	"""Check a write target relative to `apps/`; refusals follow the order of design table 3.1.

	`source.resolve_safe_path` is the only path resolver; when it refuses, the same real path is only
	classified to pick the reason, and an unclassified refusal stays `PATH_INVALID`.
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
	if _is_erp_ai(target, root, parts[0]):
		return _refused(APP_FORBIDDEN)
	if source.TEN_CAM.search(rel) or parts[-1].lower() == PROTECTED_FILE_NAME:
		return _refused(NAME_FORBIDDEN)
	if os.path.splitext(target)[1].lower() not in source.DUOI_CHO_PHEP:
		return _refused(EXT_FORBIDDEN)
	if GIT_DIR_NAME in parts:
		return _refused(GIT_DIR)
	if full is None:
		return _refused(PATH_INVALID)
	return GuardResult(full_path=full, rel_path=rel, app=parts[0], reason=None)
