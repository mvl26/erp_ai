import os
import shutil
import stat
import tempfile
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import file_writer
from erp_ai.agent.changes.file_writer import (
	PROPOSAL_FILE_MAX_BYTES,
	remove_created,
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
		self.root = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.root, True)

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

	def test_remove_created(self):
		created = os.path.join(self.root, "created.py")
		write_atomic(created, NEW_TEXT, new_file=True)
		self.assertIsNone(remove_created(created))
		self.assertFalse(os.path.exists(created))
		self.assertIsNone(sha256_of(created))
		with self.assertRaises(FileNotFoundError):
			remove_created(created)

	def test_refuses_paths_inside_dot_git(self):
		git_dir = os.path.join(self.root, ".git")
		os.mkdir(git_dir)
		inside = os.path.join(git_dir, "config")
		with open(inside, "wb") as handle:
			handle.write(OLD_BYTES)
		with self.assertRaises(ValueError):
			write_atomic(inside, NEW_TEXT, new_file=False)
		with self.assertRaises(ValueError):
			remove_created(inside)
		self.assertEqual(self._read(inside), OLD_BYTES)
		self.assertEqual(os.listdir(git_dir), ["config"])

	def test_proposal_file_max_bytes_is_one_mib(self):
		self.assertEqual(PROPOSAL_FILE_MAX_BYTES, 1048576)


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
