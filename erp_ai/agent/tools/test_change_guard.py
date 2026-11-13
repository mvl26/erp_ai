import os

from frappe.tests.utils import FrappeTestCase

import erp_ai
from erp_ai.agent.tools import change_guard, source
from erp_ai.test_utils import TempAppsRoot

ALLOWED = ("myapp",)


class TestCheckWritePath(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self, apps=("myapp", "otherapp"))
		self.root = self.apps.root

	def reason(self, rel, allowed=ALLOWED, *, new_file=False):
		return change_guard.check_write_path(rel, allowed, new_file=new_file).reason

	def fake_erp_ai_repo(self):
		"""Build, with plain file writes, a temp `erp_ai` repo (`.git` dir) and its worktree `erp_ai-wt`.

		The worktree's `.git` is a `gitdir:` file whose `commondir` leads back to `erp_ai/.git`, the
		layout `git worktree add` writes; no `git` command runs.
		"""
		self.apps.write("erp_ai/.git/HEAD", "ref: refs/heads/main\n")
		self.apps.write("erp_ai/ok.py", "x = 1\n")
		self.fake_worktree("erp_ai-wt", "wt")
		self.apps.write("erp_ai-wt/ok.py", "x = 1\n")

	def fake_worktree(self, app, name, *, gitdir=None):
		"""Point `apps/<app>/.git` at `erp_ai/.git/worktrees/<name>`, which holds `commondir` = `../..`."""
		admin = os.path.join(self.root, "erp_ai", ".git", "worktrees", name)
		self.apps.write(os.path.join(admin, "commondir"), "../..\n")
		self.apps.write(os.path.join(app, ".git"), f"gitdir: {gitdir or admin}\n")

	def test_temp_root_replaces_real_apps(self):
		self.assertEqual(source.get_source_root(), self.root)
		self.assertTrue(self.root.startswith(self.apps.base + os.sep))

	def test_refusal_wording_matches_design_table(self):
		self.assertEqual(
			(
				change_guard.PATH_INVALID,
				change_guard.APP_NOT_ALLOWED,
				change_guard.APP_FORBIDDEN,
				change_guard.NAME_FORBIDDEN,
				change_guard.EXT_FORBIDDEN,
				change_guard.GIT_DIR,
			),
			(
				"đường dẫn không hợp lệ hoặc nằm ngoài apps/",
				"app không có trong danh sách được sửa",
				"không được sửa app erp_ai hoặc kho git của nó",
				"tên file thuộc loại bí mật hoặc được bảo vệ",
				"đuôi file không được phép",
				"không được chạm thư mục .git",
			),
		)

	def test_double_refusal_returns_earlier_reason_of_table_order(self):
		for rel, expected in (
			("otherapp/.env", change_guard.APP_NOT_ALLOWED),
			("otherapp/run.sh", change_guard.APP_NOT_ALLOWED),
			("otherapp/.git/x.py", change_guard.APP_NOT_ALLOWED),
			("myapp/.git/run.sh", change_guard.EXT_FORBIDDEN),
			("myapp/.git/config", change_guard.EXT_FORBIDDEN),
			("myapp/.git/secret.py", change_guard.NAME_FORBIDDEN),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=True), expected)

	def test_double_refusal_places_app_forbidden_after_app_not_allowed(self):
		self.fake_erp_ai_repo()
		os.symlink(self.apps.outside, os.path.join(self.root, "erp_ai", "dir_out"))
		listed = ("myapp", "erp_ai", "erp_ai-wt")
		for rel, allowed, expected in (
			("erp_ai/../../outside/plain.py", listed, change_guard.PATH_INVALID),
			("erp_ai/dir_out/plain.py", listed, change_guard.PATH_INVALID),
			("erp_ai/ok.py", ALLOWED, change_guard.APP_NOT_ALLOWED),
			("erp_ai-wt/.env", ALLOWED, change_guard.APP_NOT_ALLOWED),
			("erp_ai/.env", listed, change_guard.APP_FORBIDDEN),
			("erp_ai/secret.py", listed, change_guard.APP_FORBIDDEN),
			("erp_ai/run.sh", listed, change_guard.APP_FORBIDDEN),
			("erp_ai/.git/x.py", listed, change_guard.APP_FORBIDDEN),
			("erp_ai-wt/x.pem", listed, change_guard.APP_FORBIDDEN),
			("erp_ai-wt/Makefile", listed, change_guard.APP_FORBIDDEN),
			("erp_ai-wt/.git/x.py", listed, change_guard.APP_FORBIDDEN),
		):
			with self.subTest(rel=rel, allowed=allowed):
				self.assertEqual(self.reason(rel, allowed, new_file=True), expected)

	def test_refuses_absolute_path_even_inside_root(self):
		self.apps.write("myapp/ok.py", "x = 1\n")
		self.assertEqual(self.reason(os.path.join(self.root, "myapp", "ok.py")), change_guard.PATH_INVALID)

	def test_refuses_app_not_in_allowed_list(self):
		self.assertEqual(self.reason("otherapp/ok.py"), change_guard.APP_NOT_ALLOWED)
		self.assertEqual(self.reason("myapp/ok.py", allowed=()), change_guard.APP_NOT_ALLOWED)
		self.assertEqual(self.reason("MyApp/ok.py"), change_guard.APP_NOT_ALLOWED)
		self.assertEqual(self.reason("myapp/ok.py", allowed=("MYAPP",)), change_guard.APP_NOT_ALLOWED)
		self.assertEqual(self.reason("otherapp/new.py", new_file=True), change_guard.APP_NOT_ALLOWED)

	def test_refuses_escape_with_dotdot_and_symlink(self):
		for rel in (
			"../sites/site_config.json",
			"../sites/x.py",
			"../outside/plain.py",
			"myapp/../../outside/plain.py",
			os.path.join(self.apps.outside, "plain.py"),
			"myapp/link_out.py",
			"myapp/dir_out/plain.py",
			"myapp/dir_out/new.py",
			"",
			".",
			"myapp/a\0.py",
			None,
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=True), change_guard.PATH_INVALID)

	def test_refuses_secret_and_protected_names(self):
		for rel in (
			"myapp/.env",
			"myapp/x.pem",
			"myapp/x.key",
			"myapp/license.txt",
			"myapp/LICENSE.txt",
			"myapp/site_config.json",
			"myapp/secret.py",
			"myapp/conf/.env.local",
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=True), change_guard.NAME_FORBIDDEN)
		os.symlink(os.path.join(self.root, "myapp", ".env"), os.path.join(self.root, "myapp", "env_link.py"))
		self.assertEqual(self.reason("myapp/env_link.py"), change_guard.NAME_FORBIDDEN)

	def test_refuses_extension_outside_read_list_even_for_new_file(self):
		self.apps.write("myapp/run.sh", "echo\n")
		for rel, new_file in (
			("myapp/run.sh", False),
			("myapp/new.sh", True),
			("myapp/lib.so", True),
			("myapp/Makefile", True),
			("myapp/conf/settings", True),
			("myapp", True),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=new_file), change_guard.EXT_FORBIDDEN)
		os.symlink(os.path.join(self.root, "myapp", "run.sh"), os.path.join(self.root, "myapp", "sh_link.py"))
		self.assertEqual(self.reason("myapp/sh_link.py"), change_guard.EXT_FORBIDDEN)

	def test_refuses_git_dir_component(self):
		self.apps.write("myapp/.git/info.txt", "x\n")
		self.assertEqual(self.reason("myapp/.git/info.txt"), change_guard.GIT_DIR)
		self.assertEqual(self.reason("myapp/.git/hooks/pre_commit.py", new_file=True), change_guard.GIT_DIR)
		self.assertEqual(self.reason("myapp/sub/.git/x.json", new_file=True), change_guard.GIT_DIR)
		os.symlink(os.path.join(self.root, "myapp", ".git"), os.path.join(self.root, "myapp", "gitlink"))
		self.assertEqual(self.reason("myapp/gitlink/info.txt"), change_guard.GIT_DIR)

	def test_allows_file_in_allowed_app(self):
		full = os.path.join(self.root, "myapp", "ok.py")
		self.assertEqual(
			change_guard.check_write_path("myapp/ok.py", ALLOWED, new_file=False),
			change_guard.GuardResult(full_path=full, rel_path="myapp/ok.py", app="myapp", reason=None),
		)
		new = change_guard.check_write_path("myapp/pkg/new_module.py", ("myapp", "otherapp"), new_file=True)
		self.assertIsNone(new.reason)
		self.assertEqual(new.full_path, os.path.join(self.root, "myapp", "pkg", "new_module.py"))
		self.assertEqual((new.rel_path, new.app), ("myapp/pkg/new_module.py", "myapp"))
		normalized = change_guard.check_write_path("myapp/sub/../ok.py", ALLOWED, new_file=False)
		self.assertEqual((normalized.rel_path, normalized.reason), ("myapp/ok.py", None))

	def test_refuses_erp_ai_app(self):
		self.apps.write("erp_ai/ok.py", "x = 1\n")
		allowed = ("myapp", "erp_ai")
		self.assertEqual(self.reason("erp_ai/ok.py", allowed), change_guard.APP_FORBIDDEN)
		self.assertEqual(self.reason("erp_ai/pkg/new.py", allowed, new_file=True), change_guard.APP_FORBIDDEN)
		self.assertEqual(self.reason("myapp/../erp_ai/ok.py", allowed), change_guard.APP_FORBIDDEN)
		self.assertEqual(self.reason("myapp/ok.py", allowed), None)

	def test_refuses_erp_ai_worktree_under_other_name_even_if_allowed(self):
		self.fake_erp_ai_repo()
		self.fake_worktree("other", "other")
		self.apps.write("other/pkg/ok.py", "x = 1\n")
		self.fake_worktree("relative", "relative", gitdir="../erp_ai/.git/worktrees/relative")
		self.apps.write("direct/.git", "gitdir: ../erp_ai/.git\n")
		self.apps.write("unrelated/.git", f"gitdir: {self.root}/repo/.git/worktrees/unrelated\n")
		self.apps.write("repo/.git/worktrees/unrelated/commondir", "../..\n")
		allowed = ("other", "relative", "direct", "unrelated")
		for rel, new_file in (
			("other/pkg/ok.py", False),
			("other/pkg/new.py", True),
			("other/deep/missing/new.py", True),
			("relative/new.py", True),
			("direct/new.py", True),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, allowed, new_file=new_file), change_guard.APP_FORBIDDEN)
		self.assertIsNone(self.reason("unrelated/new.py", allowed, new_file=True))

	def test_refuses_symlink_into_erp_ai_repo(self):
		self.fake_erp_ai_repo()
		os.symlink(os.path.join(self.root, "erp_ai", "ok.py"), os.path.join(self.root, "myapp", "ai_link.py"))
		os.symlink(os.path.join(self.root, "erp_ai"), os.path.join(self.root, "myapp", "ai_dir"))
		os.symlink(os.path.join(self.root, "erp_ai-wt"), os.path.join(self.root, "myapp", "wt_dir"))
		os.symlink(os.path.join(self.root, "erp_ai", ".git"), os.path.join(self.root, "otherapp", ".git"))
		listed = ("myapp", "otherapp", "erp_ai", "erp_ai-wt")
		for rel, new_file in (
			("myapp/ai_link.py", False),
			("myapp/ai_dir/ok.py", False),
			("myapp/ai_dir/new.py", True),
			("myapp/wt_dir/ok.py", False),
			("otherapp/ok.py", False),
			("otherapp/new.py", True),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, listed, new_file=new_file), change_guard.APP_FORBIDDEN)
		# Resolved into an app that is not listed: the earlier refusal of table 3.1 wins.
		self.assertEqual(self.reason("myapp/ai_link.py"), change_guard.APP_NOT_ALLOWED)

	def test_running_erp_ai_package_repo_refused(self):
		# The repo top of the running package: a plain clone (`.git` dir) or a worktree (`.git` file).
		running_top = os.path.dirname(os.path.dirname(os.path.realpath(erp_ai.__file__)))
		running_git = os.path.join(running_top, ".git")
		self.assertTrue(os.path.lexists(running_git), running_git)
		self.assertFalse(running_top.startswith(self.apps.base + os.sep))
		before = os.lstat(running_git)
		allowed = ("myapp", "otherapp")
		self.assertIsNone(self.reason("otherapp/ok.py", allowed))
		os.symlink(running_git, os.path.join(self.root, "otherapp", ".git"))
		self.assertEqual(self.reason("otherapp/ok.py", allowed), change_guard.APP_FORBIDDEN)
		self.assertEqual(
			self.reason("otherapp/pkg/new.py", allowed, new_file=True), change_guard.APP_FORBIDDEN
		)
		os.symlink(running_top, os.path.join(self.root, "myapp", "running"))
		self.assertEqual(self.reason("myapp/running/erp_ai/hooks.py", allowed), change_guard.PATH_INVALID)
		after = os.lstat(running_git)
		self.assertEqual((before.st_mtime_ns, before.st_size), (after.st_mtime_ns, after.st_size))

	def test_erp_ai_refused_even_when_listed_in_temp_root(self):
		self.fake_erp_ai_repo()
		allowed = ("myapp", "erp_ai", "erp_ai-wt")
		for rel, new_file in (
			("erp_ai/ok.py", False),
			("erp_ai/new.py", True),
			("erp_ai-wt/ok.py", False),
			("erp_ai-wt/pkg/new.py", True),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, allowed, new_file=new_file), change_guard.APP_FORBIDDEN)
		self.assertIsNone(self.reason("myapp/ok.py", allowed))
