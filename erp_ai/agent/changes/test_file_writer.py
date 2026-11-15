import os
import stat
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import file_writer
from erp_ai.agent.changes.file_writer import (
	sha256_of,
	write_atomic,
)
from erp_ai.test_utils import TempAppsRoot

OLD_BYTES = b"old\n"
OLD_SHA256 = "01d09d19c2139a46aebfb577780d123d7396e97201bc7ead210a2ebff8239dee"
NEW_TEXT = "new\n"
NEW_SHA256 = "7aa7a5359173d05b63cfd682e3c38487f3cb4f7f1d60659fe59fab1505977d4c"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
VIETNAMESE_CRLF_TEXT = "dòng một\r\nTiếng Việt có dấu\r\nkhông newline cuối"
VIETNAMESE_CRLF_BYTES = (
	b"d\xc3\xb2ng m\xe1\xbb\x99t\r\nTi\xe1\xba\xbfng Vi\xe1\xbb\x87t c\xc3\xb3 d\xe1\xba\xa5u\r\n"
	b"kh\xc3\xb4ng newline cu\xe1\xbb\x91i"
)
APP_DIR_BEFORE = sorted([".env", "dir_out", "link_out.py", "ok.py", "site_config.json", "x.pem"])
VIETNAMESE_CRLF_SHA256 = "9b6d99b985f50f7227a1325a9f46c400a8b8a6e94830254b973a2fe640f6039a"


class TestFileWriter(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self)
		self.root = os.path.join(self.apps.root, "myapp", "pkg")
		os.mkdir(self.root)

	def _existing(self, name="target.py", mode=0o755):
		full = os.path.join(self.root, name)
		with open(full, "wb") as handle:
			handle.write(OLD_BYTES)
		os.chmod(full, mode)
		return full

	def _read(self, full):
		with open(full, "rb") as handle:
			return handle.read()

	def _mode(self, full):
		return stat.S_IMODE(os.stat(full).st_mode)

	def test_write_atomic_keeps_mode_and_leaves_no_temp(self):
		full = self._existing(mode=0o755)
		self.assertEqual(write_atomic(full, NEW_TEXT, new_file=False), NEW_SHA256)
		self.assertEqual(self._read(full), b"new\n")
		self.assertEqual(self._mode(full), 0o755)
		self.assertEqual(os.listdir(self.root), ["target.py"])

		other = self._existing(name="private.py", mode=0o600)
		write_atomic(other, NEW_TEXT, new_file=False)
		self.assertEqual(self._mode(other), 0o600)

		created = os.path.join(self.root, "created.py")
		old_umask = os.umask(0o077)
		try:
			self.assertEqual(write_atomic(created, NEW_TEXT, new_file=True), NEW_SHA256)
		finally:
			os.umask(old_umask)
		self.assertEqual(self._mode(created), 0o644)
		self.assertEqual(sorted(os.listdir(self.root)), ["created.py", "private.py", "target.py"])

	def test_write_atomic_temp_file_is_in_target_dir_with_prefix(self):
		full = self._existing()
		seen = []
		real_replace = os.replace

		def spy(src, dst):
			seen.append((src, dst))
			return real_replace(src, dst)

		with patch.object(file_writer.os, "replace", side_effect=spy):
			write_atomic(full, NEW_TEXT, new_file=False)
		self.assertEqual(len(seen), 1)
		src, dst = seen[0]
		self.assertEqual(dst, full)
		self.assertEqual(os.path.dirname(src), self.root)
		self.assertTrue(os.path.basename(src).startswith(".erp_ai_"))
		self.assertTrue(os.path.basename(src).endswith(".tmp"))

	def test_write_atomic_failure_removes_temp_and_keeps_old_file(self):
		for step in ("fsync", "chmod", "replace"):
			with self.subTest(step=step):
				full = self._existing(mode=0o755)
				with patch.object(file_writer.os, step, side_effect=OSError(f"{step} failed")):
					with self.assertRaisesRegex(OSError, f"{step} failed"):
						write_atomic(full, NEW_TEXT, new_file=False)
				self.assertEqual(os.listdir(self.root), ["target.py"])
				self.assertEqual(self._read(full), OLD_BYTES)
				self.assertEqual(self._mode(full), 0o755)

	def test_write_atomic_failure_on_new_file_leaves_nothing(self):
		created = os.path.join(self.root, "created.py")
		with patch.object(file_writer.os, "replace", side_effect=OSError("replace failed")):
			with self.assertRaises(OSError):
				write_atomic(created, NEW_TEXT, new_file=True)
		self.assertEqual(os.listdir(self.root), [])

	def test_write_atomic_exact_bytes(self):
		full = self._existing()
		self.assertEqual(write_atomic(full, VIETNAMESE_CRLF_TEXT, new_file=False), VIETNAMESE_CRLF_SHA256)
		self.assertEqual(self._read(full), VIETNAMESE_CRLF_BYTES)

		empty = os.path.join(self.root, "empty.txt")
		self.assertEqual(write_atomic(empty, "", new_file=True), EMPTY_SHA256)
		self.assertEqual(self._read(empty), b"")

	def test_write_atomic_returns_hash_of_bytes_read_back(self):
		full = self._existing()
		with patch.object(file_writer, "sha256_of", return_value="read-back") as read_back:
			self.assertEqual(write_atomic(full, NEW_TEXT, new_file=False), "read-back")
		read_back.assert_called_once_with(full)

	def test_sha256_of_missing_is_none(self):
		self.assertIsNone(sha256_of(os.path.join(self.root, "missing.py")))
		self.assertEqual(sha256_of(self._existing()), OLD_SHA256)

	def test_remove_file_created(self):
		created = os.path.join(self.root, "created.py")
		write_atomic(created, NEW_TEXT, new_file=True)
		self.assertIsNone(file_writer.remove_file(created))
		self.assertFalse(os.path.exists(created))
		self.assertIsNone(sha256_of(created))
		with self.assertRaises(ValueError):
			file_writer.remove_file(created)

	def test_refuses_paths_inside_dot_git(self):
		git_dir = os.path.join(self.root, ".git")
		os.mkdir(git_dir)
		inside = os.path.join(git_dir, "config")
		with open(inside, "wb") as handle:
			handle.write(OLD_BYTES)
		with self.assertRaises(ValueError):
			write_atomic(inside, NEW_TEXT, new_file=False)
		with self.assertRaises(ValueError):
			file_writer.remove_file(inside)
		self.assertEqual(self._read(inside), OLD_BYTES)
		self.assertEqual(os.listdir(git_dir), ["config"])


class TestMakeParents(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self)
		self.app_dir = os.path.join(self.apps.root, "myapp")

	def test_three_levels_created_top_down(self):
		full = os.path.join(self.app_dir, "a", "b", "c", "new.py")
		made = []
		real_mkdir = os.mkdir

		def spy(path, mode=0o777):
			made.append((path, mode))
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=spy):
			created = file_writer.make_parents(full, self.app_dir)
		expected = [
			os.path.join(self.app_dir, "a"),
			os.path.join(self.app_dir, "a", "b"),
			os.path.join(self.app_dir, "a", "b", "c"),
		]
		self.assertEqual(created, expected)
		self.assertEqual(made, [(d, 0o755) for d in expected])
		for d in expected:
			self.assertTrue(os.path.isdir(d))
		self.assertFalse(os.path.exists(full))
		self.assertEqual(file_writer.make_parents(full, self.app_dir), [])

		existing = os.path.join(self.app_dir, "a", "x", "y.py")
		self.assertEqual(
			file_writer.make_parents(existing, self.app_dir), [os.path.join(self.app_dir, "a", "x")]
		)

	def test_app_dir_missing_raises(self):
		missing_app = os.path.join(self.apps.root, "noapp")
		full = os.path.join(missing_app, "pkg", "new.py")
		with self.assertRaises(ValueError):
			file_writer.make_parents(full, missing_app)
		self.assertFalse(os.path.exists(missing_app))

	def test_git_component_rolls_back(self):
		for parts in (("pkg", ".github", "workflows"), ("pkg", ".git", "hooks")):
			with self.subTest(parts=parts):
				full = os.path.join(self.app_dir, *parts, "x.yml")
				with self.assertRaises(ValueError):
					file_writer.make_parents(full, self.app_dir)
				self.assertFalse(os.path.exists(os.path.join(self.app_dir, "pkg")))
				self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)

	def test_symlinked_parent_rolls_back(self):
		full = os.path.join(self.app_dir, "dir_out", "pkg", "new.py")
		with self.assertRaises(ValueError):
			file_writer.make_parents(full, self.app_dir)
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])

	def test_symlinked_ancestor_refused_before_mkdir(self):
		full = os.path.join(self.app_dir, "dir_out", "pkg", "new.py")
		made = []
		real_mkdir = os.mkdir

		def spy(path, mode=0o777):
			made.append(path)
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=spy):
			with self.assertRaises(ValueError):
				file_writer.make_parents(full, self.app_dir)
		self.assertEqual(made, [])
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)

	def test_file_outside_app_dir_raises(self):
		for parts in (("other", "x"), ("loose",)):
			with self.subTest(parts=parts):
				full = os.path.join(self.apps.root, *parts, "new.py")
				with self.assertRaises(ValueError):
					file_writer.make_parents(full, self.app_dir)
				self.assertEqual(os.listdir(self.apps.root), ["myapp"])
				self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)

	def test_level_turned_symlink_after_mkdir_rolls_back(self):
		full = os.path.join(self.app_dir, "a", "b", "new.py")
		second = os.path.join(self.app_dir, "a", "b")
		real_mkdir = os.mkdir

		def swap(path, mode=0o777):
			if path == second:
				return os.symlink(self.apps.outside, path)
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=swap):
			with self.assertRaises(ValueError):
				file_writer.make_parents(full, self.app_dir)
		self.assertFalse(os.path.lexists(os.path.join(self.app_dir, "a")))
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])

	def test_level_turned_self_loop_symlink_after_mkdir_rolls_back(self):
		full = os.path.join(self.app_dir, "a", "b", "new.py")
		second = os.path.join(self.app_dir, "a", "b")
		real_mkdir = os.mkdir

		def loop(path, mode=0o777):
			if path == second:
				return os.symlink(path, path)
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=loop):
			with self.assertRaisesRegex(ValueError, "through a symlink"):
				file_writer.make_parents(full, self.app_dir)
		self.assertFalse(os.path.lexists(os.path.join(self.app_dir, "a")))
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])

	def test_created_level_swapped_for_symlink_before_next_mkdir_rolls_back(self):
		full = os.path.join(self.app_dir, "a", "b", "new.py")
		first = os.path.join(self.app_dir, "a")
		second = os.path.join(self.app_dir, "a", "b")
		real_mkdir = os.mkdir

		def swap_parent(path, mode=0o777):
			if path == second:
				os.rmdir(first)
				os.symlink(self.apps.outside, first)
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=swap_parent):
			with self.assertRaisesRegex(ValueError, "does not touch this path"):
				file_writer.make_parents(full, self.app_dir)
		self.assertFalse(os.path.lexists(first))
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])

	def test_symlink_inside_root_refused_before_mkdir(self):
		os.symlink(self.app_dir, os.path.join(self.app_dir, "inner_link"))
		full = os.path.join(self.app_dir, "inner_link", "pkg", "new.py")
		made = []
		real_mkdir = os.mkdir

		def spy(path, mode=0o777):
			made.append(path)
			return real_mkdir(path, mode)

		with patch.object(file_writer.os, "mkdir", side_effect=spy):
			with self.assertRaises(ValueError):
				file_writer.make_parents(full, self.app_dir)
		self.assertEqual(made, [])
		self.assertFalse(os.path.lexists(os.path.join(self.app_dir, "pkg")))
		self.assertEqual(sorted(os.listdir(self.app_dir)), sorted([*APP_DIR_BEFORE, "inner_link"]))


class TestRefuseUnlessCanonical(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self)
		self.app_dir = os.path.join(self.apps.root, "myapp")

	def test_symlink_inside_root_refused(self):
		os.symlink(self.app_dir, os.path.join(self.app_dir, "inner_link"))
		for parts in (("inner_link", "x.py"), ("inner_link", "pkg", "new.py"), ("inner_link",)):
			with self.subTest(parts=parts):
				with self.assertRaises(ValueError):
					file_writer._refuse_unless_canonical(os.path.join(self.app_dir, *parts))
		self.assertEqual(sorted(os.listdir(self.app_dir)), sorted([*APP_DIR_BEFORE, "inner_link"]))

	def test_plain_path_accepted(self):
		for parts in (("ok.py",), ("pkg", "new.py"), ("pkg",)):
			with self.subTest(parts=parts):
				self.assertIsNone(file_writer._refuse_unless_canonical(os.path.join(self.app_dir, *parts)))
		self.assertIsNone(file_writer._refuse_unless_canonical(self.app_dir))

	def test_outside_git_secret_and_symlinked_target_refused(self):
		cases = {
			"outside the apps root": os.path.join(self.apps.outside, "plain.py"),
			"the apps root itself": self.apps.root,
			"a .git* component": os.path.join(self.app_dir, ".github", "workflows", "x.yml"),
			"a .git directory": os.path.join(self.app_dir, ".git", "config"),
			"a secret name": os.path.join(self.app_dir, "site_config.json"),
			"a symlinked parent": os.path.join(self.app_dir, "dir_out", "plain.py"),
			"a symlinked ancestor": os.path.join(self.app_dir, "dir_out", "pkg", "new.py"),
			"a symlinked target file": os.path.join(self.app_dir, "link_out.py"),
			"a symlinked target directory": os.path.join(self.app_dir, "dir_out"),
		}
		for name, full in cases.items():
			with self.subTest(case=name):
				with self.assertRaises(ValueError):
					file_writer._refuse_unless_canonical(full)
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)


class TestRemoveEmptyDirs(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self)
		self.app_dir = os.path.join(self.apps.root, "myapp")

	def _dir(self, *parts):
		path = os.path.join(self.app_dir, *parts)
		os.makedirs(path, exist_ok=True)
		return path

	def test_keeps_nonempty_and_preexisting(self):
		preexisting = self._dir("pre")
		empty = self._dir("pre", "empty")
		full = self._dir("pre", "full")
		self.apps.write(os.path.join("myapp", "pre", "full", "keep.py"), "x = 1\n")
		removed = file_writer.remove_empty_dirs([empty, full])
		self.assertEqual(removed, [empty])
		self.assertFalse(os.path.exists(empty))
		self.assertTrue(os.path.isdir(full))
		self.assertTrue(os.path.isdir(preexisting))

	def test_symlink_dir_skipped_target_untouched(self):
		target = os.path.join(self.apps.base, "outside_empty")
		os.mkdir(target)
		link = os.path.join(self.app_dir, "link_empty")
		os.symlink(target, link)
		self.assertEqual(file_writer.remove_empty_dirs([link]), [])
		self.assertTrue(os.path.islink(link))
		self.assertTrue(os.path.isdir(target))

	def test_git_component_dir_skipped(self):
		empty = self._dir(".github", "empty")
		git_empty = self._dir(".git", "refs")
		self.assertEqual(file_writer.remove_empty_dirs([empty, git_empty]), [])
		self.assertTrue(os.path.isdir(empty))
		self.assertTrue(os.path.isdir(git_empty))

	def test_deepest_first_nonempty_kept(self):
		top = self._dir("a")
		middle = self._dir("a", "b")
		deepest = self._dir("a", "b", "c")
		cached = self._dir("a", "cached")
		self.apps.write(os.path.join("myapp", "a", "cached", "__pycache__", "m.pyc"), "")
		removed = file_writer.remove_empty_dirs([top, cached, middle, deepest])
		self.assertEqual(removed, [deepest, middle])
		self.assertTrue(os.path.isdir(top))
		self.assertTrue(os.path.isdir(os.path.join(cached, "__pycache__")))

	def test_dir_under_symlinked_parent_or_outside_root_skipped(self):
		outside_empty = os.path.join(self.apps.outside, "empty")
		os.mkdir(outside_empty)
		through_link = os.path.join(self.app_dir, "dir_out", "empty")
		self.assertEqual(file_writer.remove_empty_dirs([through_link, outside_empty]), [])
		self.assertTrue(os.path.isdir(outside_empty))

	def test_dir_under_symlink_inside_root_skipped(self):
		empty = self._dir("empty")
		os.symlink(self.app_dir, os.path.join(self.app_dir, "inner_link"))
		through_link = os.path.join(self.app_dir, "inner_link", "empty")
		self.assertEqual(file_writer.remove_empty_dirs([through_link]), [])
		self.assertTrue(os.path.isdir(empty))


class _GuardedTargets:
	"""Shared fixture of `TestRemoveFile` and `TestWriteAtomic`: the temp apps root plus spies on the writes."""

	def setUp(self):
		self.apps = TempAppsRoot(self)
		self.app_dir = os.path.join(self.apps.root, "myapp")
		self.removed = []
		self.temps = []
		real_remove = os.remove
		real_mkstemp = file_writer.tempfile.mkstemp

		def remove_spy(path, *args, **kwargs):
			self.removed.append(path)
			return real_remove(path, *args, **kwargs)

		def mkstemp_spy(*args, **kwargs):
			self.temps.append(kwargs.get("dir"))
			return real_mkstemp(*args, **kwargs)

		for target, name, spy in (
			(file_writer.os, "remove", remove_spy),
			(file_writer.tempfile, "mkstemp", mkstemp_spy),
		):
			patcher = patch.object(target, name, side_effect=spy)
			patcher.start()
			self.addCleanup(patcher.stop)

	def _file(self, *parts):
		return self.apps.write(os.path.join("myapp", *parts), "x = 1\n")

	def _read(self, full):
		with open(full, encoding="utf-8") as handle:
			return handle.read()


class TestRemoveFile(_GuardedTargets, FrappeTestCase):
	def test_regular_file_removed(self):
		full = self._file("pkg", "x.py")
		self.assertIsNone(file_writer.remove_file(full))
		self.assertFalse(os.path.lexists(full))
		self.assertEqual(self.removed, [full])
		self.assertEqual(os.listdir(os.path.join(self.app_dir, "pkg")), [])

	def test_symlink_or_directory_refused(self):
		self._file("pkg", "x.py")
		loop = os.path.join(self.app_dir, "loop.py")
		os.symlink(loop, loop)
		inner = os.path.join(self.app_dir, "inner.py")
		os.symlink(os.path.join(self.app_dir, "ok.py"), inner)
		cases = {
			"a self-loop symlink": loop,
			"a symlink to a file inside the root": inner,
			"a symlink to a file outside the root": os.path.join(self.app_dir, "link_out.py"),
			"a symlink to a directory": os.path.join(self.app_dir, "dir_out"),
			"a directory": os.path.join(self.app_dir, "pkg"),
			"a missing file": os.path.join(self.app_dir, "missing.py"),
		}
		for name, full in cases.items():
			with self.subTest(case=name):
				with self.assertRaises(ValueError):
					file_writer.remove_file(full)
		self.assertEqual(self.removed, [])
		self.assertTrue(os.path.islink(loop))
		self.assertTrue(os.path.islink(inner))
		self.assertEqual(self._read(os.path.join(self.app_dir, "ok.py")), "x = 1\n")
		self.assertEqual(os.listdir(os.path.join(self.app_dir, "pkg")), ["x.py"])
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])

	def test_symlink_refused_by_islink_alone(self):
		"""With the canonical re-check out of the way, `islink` still refuses a symlink to a regular file."""
		inner = os.path.join(self.app_dir, "inner.py")
		os.symlink(os.path.join(self.app_dir, "ok.py"), inner)
		with patch.object(file_writer, "_refuse_unless_canonical") as recheck:
			with self.assertRaises(ValueError):
				file_writer.remove_file(inner)
		recheck.assert_called_once_with(inner)
		self.assertEqual(self.removed, [])
		self.assertTrue(os.path.islink(inner))

	def test_parent_dir_symlink_refused_zero_removed(self):
		inner_target = self._file("pkg", "x.py")
		os.symlink(self.app_dir, os.path.join(self.app_dir, "inner_link"))
		for full in (
			os.path.join(self.app_dir, "dir_out", "plain.py"),
			os.path.join(self.app_dir, "inner_link", "pkg", "x.py"),
		):
			with self.subTest(full=full):
				with self.assertRaises(ValueError):
					file_writer.remove_file(full)
		self.assertEqual(self.removed, [])
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])
		self.assertEqual(self._read(inner_target), "x = 1\n")

	def test_git_component_refused_file_kept(self):
		kept = [self._file(".git", "config"), self._file(".github", "workflows", "x.yml")]
		for full in kept:
			with self.subTest(full=full):
				with self.assertRaises(ValueError):
					file_writer.remove_file(full)
		self.assertEqual(self.removed, [])
		for full in kept:
			self.assertEqual(self._read(full), "x = 1\n")

	def test_secret_name_refused_file_kept(self):
		for name in ("site_config.json", ".env", "x.pem"):
			with self.subTest(name=name):
				with self.assertRaises(ValueError):
					file_writer.remove_file(os.path.join(self.app_dir, name))
		self.assertEqual(self.removed, [])
		self.assertEqual(sorted(os.listdir(self.app_dir)), APP_DIR_BEFORE)

	def test_outside_source_root_refused(self):
		kept = [
			os.path.join(self.apps.outside, "plain.py"),
			self.apps.write("loose.py", "x = 1\n", root=self.apps.base),
		]
		for full in kept:
			with self.subTest(full=full):
				with self.assertRaises(ValueError):
					file_writer.remove_file(full)
		self.assertEqual(self.removed, [])
		for full in kept:
			self.assertEqual(self._read(full), "x = 1\n")


class TestWriteAtomic(_GuardedTargets, FrappeTestCase):
	def test_parent_symlink_and_git_component_refused(self):
		os.symlink(self.app_dir, os.path.join(self.app_dir, "inner_link"))
		loop = os.path.join(self.app_dir, "loop.py")
		os.symlink(loop, loop)
		git_config = self._file(".git", "config")
		workflow = self._file(".github", "workflows", "x.yml")
		cases = {
			"a symlinked parent outside the root": (os.path.join(self.app_dir, "dir_out", "new.py"), True),
			"a symlinked parent inside the root": (os.path.join(self.app_dir, "inner_link", "new.py"), True),
			"an existing file through an inner symlink": (
				os.path.join(self.app_dir, "inner_link", "ok.py"),
				False,
			),
			"a .git directory": (git_config, False),
			"a .git* directory": (workflow, False),
			"a new file in a .git* directory": (os.path.join(self.app_dir, ".github", "new.yml"), True),
			"a secret name": (os.path.join(self.app_dir, "site_config.json"), False),
			"outside the root": (os.path.join(self.apps.outside, "plain.py"), False),
			"a symlinked target": (os.path.join(self.app_dir, "link_out.py"), False),
			"a new file over a self-loop symlink": (loop, True),
			"an existing self-loop symlink": (loop, False),
		}
		for name, (full, new_file) in cases.items():
			with self.subTest(case=name):
				with self.assertRaises(ValueError):
					write_atomic(full, NEW_TEXT, new_file=new_file)
		self.assertEqual(self.temps, [])
		self.assertTrue(os.path.islink(loop))
		self.assertEqual(self._read(git_config), "x = 1\n")
		self.assertEqual(self._read(workflow), "x = 1\n")
		self.assertEqual(os.listdir(os.path.join(self.app_dir, ".github")), ["workflows"])
		self.assertEqual(self._read(os.path.join(self.app_dir, "ok.py")), "x = 1\n")
		self.assertEqual(self._read(os.path.join(self.app_dir, "site_config.json")), "x = 1\n")
		self.assertEqual(self._read(os.path.join(self.apps.outside, "plain.py")), "x = 1\n")
		self.assertEqual(os.listdir(self.apps.outside), ["plain.py"])
		self.assertEqual(
			sorted(os.listdir(self.app_dir)),
			sorted([*APP_DIR_BEFORE, ".git", ".github", "inner_link", "loop.py"]),
		)

	def test_plain_target_still_written(self):
		full = os.path.join(self.app_dir, "ok.py")
		self.assertEqual(write_atomic(full, NEW_TEXT, new_file=False), NEW_SHA256)
		self.assertEqual(self.temps, [self.app_dir])
		self.assertEqual(self.removed, [])
