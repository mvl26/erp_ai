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
NEW_DIR_MODE = 0o755


def _refuse_git_dir(full_path):
	if GIT_DIR_NAME in PurePath(os.path.abspath(full_path)).parts:
		raise ValueError("file_writer does not write inside .git")


def _refuse_unsafe_path(full_path) -> None:
	"""Raise ValueError when the path is outside the apps root, has a `.git*` component, or a symlinked parent."""
	full = os.path.abspath(full_path)
	rel = os.path.relpath(full, os.path.realpath(source.get_source_root()))
	parts = PurePath(rel).parts
	if os.path.isabs(rel) or not parts or parts[0] == os.pardir:
		raise ValueError("file_writer does not touch paths outside the apps root")
	if any(part.startswith(GIT_DIR_NAME) for part in parts):
		raise ValueError("file_writer does not touch .git* paths")
	parent = os.path.dirname(full)
	if os.path.realpath(parent) != parent:
		raise ValueError("file_writer does not touch paths under a symlinked directory")


def make_parents(full_path, app_dir) -> list[str]:
	"""Create the missing directories between `app_dir` (must exist) and the file, top down; return those created."""
	app = os.path.abspath(app_dir)
	parent = os.path.dirname(os.path.abspath(full_path))
	if not os.path.isdir(app) or os.path.islink(app):
		raise ValueError("app directory does not exist")
	parts = PurePath(os.path.relpath(parent, app)).parts
	if parts[:1] == (os.pardir,):
		raise ValueError("file is outside the app directory")
	created = []
	current = app
	try:
		for part in parts:
			current = os.path.join(current, part)
			if os.path.lexists(current):
				continue
			os.mkdir(current, NEW_DIR_MODE)
			created.append(current)
			_refuse_unsafe_path(current)
			if os.path.islink(current):
				raise ValueError("file_writer does not create directories through a symlink")
	except BaseException:
		for made in reversed(created):
			if os.path.islink(made):
				os.unlink(made)
			else:
				os.rmdir(made)
		raise
	return created


def remove_empty_dirs(dirs) -> list[str]:
	"""Remove the listed directories that are safe and empty, deepest first; skip the rest; return those removed."""
	removed = []
	for directory in sorted(dirs, key=lambda d: len(PurePath(os.path.abspath(d)).parts), reverse=True):
		if os.path.islink(directory) or os.path.realpath(directory) != os.path.abspath(directory):
			continue
		try:
			_refuse_unsafe_path(directory)
		except ValueError:
			continue
		if not os.path.isdir(directory) or os.listdir(directory):
			continue
		os.rmdir(directory)
		removed.append(directory)
	return removed


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
