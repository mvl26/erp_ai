"""The one module in `erp_ai/agent/**` that writes or removes files (ADR-013 decision 6, design 3.9/4.3)."""

import hashlib
import os
import stat
import tempfile
from pathlib import PurePath

from erp_ai.agent.tools import source

NEW_FILE_MODE = 0o644
TEMP_PREFIX = ".erp_ai_"
TEMP_SUFFIX = ".tmp"
NEW_DIR_MODE = 0o755


def _refuse_unless_canonical(full_path) -> None:
	"""Raise ValueError unless the one resolver accepts the path and leaves it unchanged (ADR-040 C-2)."""
	full = os.path.abspath(full_path)
	if source.resolve_safe_path(os.path.relpath(full, source.get_source_root())) != full:
		raise ValueError(
			"file_writer does not touch this path (outside the apps root, .git*, secret name or symlink)"
		)


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
			_refuse_unless_canonical(current)
			os.mkdir(current, NEW_DIR_MODE)
			created.append(current)
			_refuse_unless_canonical(current)
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
		if os.path.islink(directory):
			continue
		try:
			_refuse_unless_canonical(directory)
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
	_refuse_unless_canonical(full_path)
	if os.path.islink(full_path):
		raise ValueError("file_writer does not write through a symlink")
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


def remove_file(full_path) -> None:
	"""Remove one regular file (Delete, undo, or giving back a created file); never a symlink or a directory."""
	_refuse_unless_canonical(full_path)
	if os.path.islink(full_path) or not os.path.isfile(full_path):
		raise ValueError("file_writer removes only a regular file")
	os.remove(full_path)
