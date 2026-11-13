"""The one module in `erp_ai/agent/**` that writes or removes files (ADR-013 decision 6, design 3.9/4.3)."""

import hashlib
import os
import stat
import tempfile
from pathlib import PurePath

from erp_ai.agent.tools import source

PROPOSAL_FILE_MAX_BYTES = source.SEARCH_FILE_MAX_BYTES
NEW_FILE_MODE = 0o644
TEMP_PREFIX = ".erp_ai_"
TEMP_SUFFIX = ".tmp"
GIT_DIR_NAME = ".git"


def _refuse_git_dir(full_path):
	if GIT_DIR_NAME in PurePath(os.path.abspath(full_path)).parts:
		raise ValueError("file_writer does not write inside .git")


def sha256_of(full_path) -> str | None:
	try:
		with open(full_path, "rb") as handle:
			return hashlib.sha256(handle.read()).hexdigest()
	except FileNotFoundError:
		return None


def write_atomic(full_path, content: str, *, new_file: bool) -> str:
	"""Write `content` as UTF-8 bytes via a temp file in the same directory; return the sha256 read back."""
	_refuse_git_dir(full_path)
	data = content.encode("utf-8")
	mode = NEW_FILE_MODE if new_file else stat.S_IMODE(os.stat(full_path).st_mode)
	fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(full_path), prefix=TEMP_PREFIX, suffix=TEMP_SUFFIX)
	try:
		with os.fdopen(fd, "wb") as handle:
			handle.write(data)
			handle.flush()
			os.fsync(handle.fileno())
		os.chmod(temp_path, mode)
		os.replace(temp_path, full_path)
	except BaseException:
		os.remove(temp_path)
		raise
	return sha256_of(full_path)


def remove_created(full_path) -> None:
	"""Remove a file the proposal created (undo, or giving back a new file after a failed commit)."""
	_refuse_git_dir(full_path)
	os.remove(full_path)
