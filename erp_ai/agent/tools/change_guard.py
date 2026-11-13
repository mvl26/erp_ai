import os
from dataclasses import dataclass

from erp_ai.agent.tools import source

PROTECTED_FILE_NAME = "license.txt"
GIT_DIR_NAME = ".git"

# Refusal wording of design 3.1 (contract with the model and the tests).
PATH_INVALID = "đường dẫn không hợp lệ hoặc nằm ngoài apps/"
APP_NOT_ALLOWED = "app không có trong danh sách được sửa"
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
	if source.TEN_CAM.search(rel) or parts[-1].lower() == PROTECTED_FILE_NAME:
		return _refused(NAME_FORBIDDEN)
	if os.path.splitext(target)[1].lower() not in source.DUOI_CHO_PHEP:
		return _refused(EXT_FORBIDDEN)
	if GIT_DIR_NAME in parts:
		return _refused(GIT_DIR)
	if full is None:
		return _refused(PATH_INVALID)
	return GuardResult(full_path=full, rel_path=rel, app=parts[0], reason=None)
