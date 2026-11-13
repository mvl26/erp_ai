import os

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.tools import change_guard, source
from erp_ai.test_utils import TempAppsRoot

ALLOWED = ("myapp",)


class TestCheckWritePath(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self, apps=("myapp", "otherapp"))
		self.root = self.apps.root

	def reason(self, rel, allowed=ALLOWED, *, new_file=False):
		return change_guard.check_write_path(rel, allowed, new_file=new_file).reason

	def test_temp_root_replaces_real_apps(self):
		self.assertEqual(source.get_source_root(), self.root)
		self.assertTrue(self.root.startswith(self.apps.base + os.sep))

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
		# No extension: refused earlier by the table order (EXT_FORBIDDEN before GIT_DIR), never allowed.
		self.assertIsNotNone(self.reason("myapp/.git/config", new_file=True))
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
