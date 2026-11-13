import os
import threading
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

import erp_ai
from erp_ai.agent.tools import change_guard, source
from erp_ai.test_utils import TempAppsRoot

ALLOWED = ("myapp",)
SITE = "site1.test"

# Refusal sentences of design 3.1 / 3.2, typed here so the tests do not compare a constant with itself.
SHELL_REFUSAL = "đối số chứa ký tự điều khiển shell"
FORCE_REFUSAL = "cờ --force bị cấm"
OTHER_SITE_REFUSAL = "chỉ chạy cho site đang chạy"
NOT_LISTED_REFUSAL = "lệnh không có trong danh sách cho phép"
NEEDS_APP_REFUSAL = "lệnh build cần app"
TAKES_NO_APP_REFUSAL = "lệnh này không nhận app"
APP_NOT_ALLOWED_REFUSAL = "app không có trong danh sách được sửa"
APP_FORBIDDEN_REFUSAL = "không được sửa app erp_ai hoặc kho git của nó"

# Denied list of spec A-6 plus ADR-022 QĐ 2 (design 8.1): 23 names.
A6_DENIED_COMMANDS = (
	"execute",
	"console",
	"mariadb",
	"db-console",
	"backup",
	"restore",
	"drop-site",
	"reinstall",
	"set-config",
	"set-admin-password",
	"add-system-manager",
	"add-user",
	"install-app",
	"uninstall-app",
	"remove-app",
	"get-app",
	"update",
	"setup",
	"restart",
	"run-tests",
	"switch-to-branch",
	"new-app",
	"init",
)


def release_fifo_reader(fifo):
	"""Open the FIFO for writing and close it so a reader blocked on it gets EOF; no reader is fine."""
	try:
		os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
	except OSError:
		pass  # ENXIO: nobody is reading, nothing to release.


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

	def test_unreadable_git_pointer_leads_to_no_repo_without_raising(self):
		self.fake_erp_ai_repo()
		self.apps.write("junk/.git", "not a pointer\ngitdir: ../erp_ai/.git\n")
		with open(self.apps.write("binary/.git", ""), "wb") as handle:
			handle.write(b"gitdir: \xff\xfe../erp_ai/.git\n")
		admin = os.path.join(self.root, "erp_ai", ".git", "worktrees", "dircommon")
		os.makedirs(os.path.join(admin, "commondir"))
		self.apps.write("dircommon/.git", f"gitdir: {admin}\n")
		padding = " " * change_guard.MAX_POINTER_BYTES
		self.fake_worktree("huge", "huge", gitdir=padding + os.path.join(self.root, "erp_ai", ".git"))
		allowed = ("junk", "binary", "dircommon", "huge")
		for app in allowed:
			with self.subTest(app=app):
				self.assertIsNone(change_guard._git_common_dir(os.path.join(self.root, app, ".git")))
				self.assertIsNone(self.reason(f"{app}/new.py", allowed, new_file=True))

	def test_git_pointer_that_is_not_a_regular_file_does_not_block(self):
		fifo = os.path.join(self.root, "piped", ".git")
		os.makedirs(os.path.dirname(fifo))
		os.mkfifo(fifo)
		self.addCleanup(release_fifo_reader, fifo)
		results = []
		worker = threading.Thread(
			target=lambda: results.append(change_guard._git_common_dir(fifo)), daemon=True
		)
		worker.start()
		worker.join(5)
		self.assertFalse(worker.is_alive(), "reading a FIFO .git blocked")
		self.assertEqual(results, [None])

	def test_relative_gitdir_resolves_from_the_git_entry_not_its_symlink_target(self):
		self.fake_erp_ai_repo()
		admin = os.path.join(self.root, "erp_ai", ".git", "worktrees", "linked")
		self.apps.write(os.path.join(admin, "commondir"), "../..\n")
		pointer = self.apps.write("holder/sub/pointer", "gitdir: ../erp_ai/.git/worktrees/linked\n")
		self.apps.write("linked/ok.py", "x = 1\n")
		os.symlink(pointer, os.path.join(self.root, "linked", ".git"))
		allowed = ("linked", "holder")
		self.assertEqual(self.reason("linked/ok.py", allowed), change_guard.APP_FORBIDDEN)
		self.assertEqual(self.reason("linked/new.py", allowed, new_file=True), change_guard.APP_FORBIDDEN)

	def test_running_package_identity_is_the_nearest_repo_only(self):
		outer = os.path.join(self.apps.base, "outer")
		self.apps.write(".git/HEAD", "ref: refs/heads/main\n", root=outer)
		self.apps.write("inner/.git/HEAD", "ref: refs/heads/main\n", root=outer)
		package_file = self.apps.write("inner/erp_ai/__init__.py", "", root=outer)
		os.symlink(os.path.join(outer, ".git"), os.path.join(self.root, "myapp", ".git"))
		os.symlink(os.path.join(outer, "inner", ".git"), os.path.join(self.root, "otherapp", ".git"))
		allowed = ("myapp", "otherapp")
		with patch.object(erp_ai, "__file__", package_file):
			self.assertEqual(self.reason("otherapp/ok.py", allowed), change_guard.APP_FORBIDDEN)
			self.assertIsNone(self.reason("myapp/ok.py", allowed))

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


class TestBenchArgs(FrappeTestCase):
	def setUp(self):
		self.apps = TempAppsRoot(self, apps=("myapp", "otherapp"))
		self.root = self.apps.root

	def build(self, command, app=None, allowed=ALLOWED, site=SITE):
		return change_guard.build_bench_args(command, app, allowed, site)

	def check(self, args, allowed=ALLOWED, site=SITE):
		return change_guard.check_bench_args(args, allowed, site)

	def fake_erp_ai_repo(self):
		"""A temp `erp_ai` repo (`.git` dir) and a worktree of it named `erp_ai-wt`, plain file writes only."""
		self.apps.write("erp_ai/.git/HEAD", "ref: refs/heads/main\n")
		admin = os.path.join(self.root, "erp_ai", ".git", "worktrees", "wt")
		self.apps.write(os.path.join(admin, "commondir"), "../..\n")
		self.apps.write("erp_ai-wt/.git", f"gitdir: {admin}\n")

	def test_build_args_for_each_allowed_command(self):
		for command, app, expected in (
			("migrate", None, ["--site", "site1.test", "migrate"]),
			("build", "myapp", ["build", "--app", "myapp"]),
			("clear-cache", None, ["--site", "site1.test", "clear-cache"]),
			("clear-website-cache", None, ["--site", "site1.test", "clear-website-cache"]),
			("list-apps", None, ["--site", "site1.test", "list-apps"]),
			("version", None, ["version"]),
		):
			with self.subTest(command=command):
				self.assertEqual(self.build(command, app), expected)
				self.assertIsNone(self.check(expected))
		self.assertEqual(
			self.build("build", "otherapp", ("myapp", "otherapp")), ["build", "--app", "otherapp"]
		)
		self.assertIsNone(self.check(["build", "--app", "otherapp"], ("myapp", "otherapp")))
		self.assertEqual(self.build("version", None, ALLOWED, None), ["version"])
		self.assertIsNone(self.check(["version"], ALLOWED, None))

	def test_bench_refusal_wording_matches_design(self):
		self.assertEqual(
			(
				change_guard.CMD_SHELL,
				change_guard.CMD_FORCE,
				change_guard.CMD_OTHER_SITE,
				change_guard.CMD_NOT_LISTED,
				change_guard.CMD_NEEDS_APP,
				change_guard.CMD_TAKES_NO_APP,
			),
			(
				"đối số chứa ký tự điều khiển shell",
				"cờ --force bị cấm",
				"chỉ chạy cho site đang chạy",
				"lệnh không có trong danh sách cho phép",
				"lệnh build cần app",
				"lệnh này không nhận app",
			),
		)

	def test_bench_args_refuse_every_a6_denied_command(self):
		self.assertEqual(len(A6_DENIED_COMMANDS), 23)
		self.assertEqual(len(set(A6_DENIED_COMMANDS)), 23)
		for name in A6_DENIED_COMMANDS:
			with self.subTest(command=name):
				self.assertEqual(self.build(name), NOT_LISTED_REFUSAL)
				self.assertEqual(self.build(name, "myapp"), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name, "--app", "myapp"]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name, "myapp"]), NOT_LISTED_REFUSAL)

	def test_bench_allow_list_is_exactly_the_six_design_commands(self):
		# Design 3.2 / spec A-6: the allow-list is the mechanism; every other command is refused.
		self.assertEqual(
			set(change_guard.BENCH_COMMANDS),
			{"migrate", "build", "clear-cache", "clear-website-cache", "list-apps", "version"},
		)
		self.assertEqual(len(change_guard.BENCH_COMMANDS), 6)
		for name in ("trim-database", "doctor", "show-config", "destroy-all-sessions"):
			with self.subTest(command=name):
				self.assertNotIn(name, A6_DENIED_COMMANDS)
				self.assertEqual(self.build(name), NOT_LISTED_REFUSAL)
				self.assertEqual(self.build(name, "myapp"), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name]), NOT_LISTED_REFUSAL)

	def test_bench_args_refuse_shell_metacharacters(self):
		for char in (";", "|", "&", "`", "$(", ">", "<", "\n"):
			with self.subTest(char=char):
				self.assertEqual(self.check(["--site", "site1.test", f"migrate{char}ls"]), SHELL_REFUSAL)
				self.assertEqual(self.check([f"version{char}"]), SHELL_REFUSAL)
				self.assertEqual(self.check(["build", "--app", f"myapp{char}x"]), SHELL_REFUSAL)
				# Step 1 comes before every other check: force, other site, unlisted command.
				self.assertEqual(
					self.check(["--site", "other", "execute", "--force", f"x{char}y"]), SHELL_REFUSAL
				)
				self.assertEqual(self.check(["--site", f"site1.test{char}", "migrate"]), SHELL_REFUSAL)
				app = f"my{char}app"
				self.assertEqual(self.build("build", app, (app,)), SHELL_REFUSAL)
				self.assertEqual(self.build("migrate", None, ALLOWED, f"site1.test{char}"), SHELL_REFUSAL)
		self.assertEqual(self.check(["--site", "site1.test", "migrate$x"]), NOT_LISTED_REFUSAL)

	def test_bench_args_refuse_other_site_and_force(self):
		for args in (
			["--site", "site1.test", "migrate", "--force"],
			["--force", "--site", "site1.test", "migrate"],
			["build", "--app", "myapp", "--force"],
			["--site", "site1.test", "migrate", "--force=1"],
			# Step 2 comes before steps 3 and 4.
			["--site", "other", "migrate", "--force"],
			["--force", "--site", "other", "execute"],
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), FORCE_REFUSAL)
		for args in (
			["--site", "other", "migrate"],
			["--site", "SITE1.TEST", "migrate"],
			["--site=other", "migrate"],
			["--site", "site1.test", "--site", "other", "migrate"],
			["migrate", "--site"],
			["site1.test", "--site", "migrate"],
			# Step 3 comes before step 4.
			["--site", "other", "execute"],
			["--site", "other", "build", "--app", "myapp"],
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), OTHER_SITE_REFUSAL)
		for site in (None, "", "  ", 5):
			with self.subTest(site=site):
				self.assertEqual(
					self.check(["--site", "site1.test", "migrate"], ALLOWED, site), OTHER_SITE_REFUSAL
				)
				self.assertEqual(self.build("migrate", None, ALLOWED, site), OTHER_SITE_REFUSAL)
				self.assertEqual(self.build("list-apps", None, ALLOWED, site), OTHER_SITE_REFUSAL)
		# Step 3 refuses a blank running site even when `--site` repeats it exactly.
		for site in ("", "  "):
			with self.subTest(site=site):
				self.assertEqual(self.check(["--site", site, "migrate"], ALLOWED, site), OTHER_SITE_REFUSAL)

	def test_bench_args_refuse_unlisted_and_build_of_disallowed_app(self):
		self.fake_erp_ai_repo()
		listed = ("myapp", "erp_ai", "erp_ai-wt")
		self.assertEqual(self.build("build", "otherapp"), APP_NOT_ALLOWED_REFUSAL)
		self.assertEqual(self.build("build", "MyApp"), APP_NOT_ALLOWED_REFUSAL)
		self.assertEqual(self.build("build", "myapp", ()), APP_NOT_ALLOWED_REFUSAL)
		self.assertEqual(self.build("build", "erp_ai", listed), APP_FORBIDDEN_REFUSAL)
		self.assertEqual(self.build("build", "erp_ai-wt", listed), APP_FORBIDDEN_REFUSAL)
		self.assertEqual(self.build("build", "erp_ai"), APP_NOT_ALLOWED_REFUSAL)
		os.symlink(os.path.join(self.root, "erp_ai"), os.path.join(self.root, "aliased"))
		self.assertEqual(self.build("build", "aliased", ("aliased", "erp_ai")), APP_NOT_ALLOWED_REFUSAL)
		for app in ("../myapp", "myapp/", "myapp/sub", ".", "..", "/myapp", "my\0app"):
			with self.subTest(app=app):
				self.assertEqual(self.build("build", app, (app, "myapp")), APP_NOT_ALLOWED_REFUSAL)
		for args, allowed in (
			(["build", "--app", "otherapp"], ALLOWED),
			(["build", "--app", "erp_ai"], listed),
			(["build", "--app", "erp_ai-wt"], listed),
			(["build", "--app", "aliased"], ("aliased",)),
			(["build", "--app", "../myapp"], ("../myapp",)),
			(["build"], ALLOWED),
			(["build", "--app"], ALLOWED),
			(["build", "--app", "myapp", "--production"], ALLOWED),
			(["build", "--apps", "myapp"], ALLOWED),
			(["--site", "site1.test", "build", "--app", "myapp"], ALLOWED),
			(["--site", "site1.test", "migrate", "--skip-failing"], ALLOWED),
			(["--site", "site1.test", "version"], ALLOWED),
			(["version", "--site", "site1.test"], ALLOWED),
			(["migrate"], ALLOWED),
			(["--site", "site1.test"], ALLOWED),
			(["bench", "version"], ALLOWED),
			([" version"], ALLOWED),
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args, allowed), NOT_LISTED_REFUSAL)
		self.assertEqual(self.build("build"), NEEDS_APP_REFUSAL)
		self.assertEqual(self.build("build", ""), NEEDS_APP_REFUSAL)
		self.assertEqual(self.build("build", "   "), NEEDS_APP_REFUSAL)
		for command in ("migrate", "clear-cache", "clear-website-cache", "list-apps", "version"):
			with self.subTest(command=command):
				self.assertEqual(self.build(command, "myapp"), TAKES_NO_APP_REFUSAL)
				self.assertEqual(self.build(command, ""), TAKES_NO_APP_REFUSAL)
		for command in ("Migrate", " migrate", "migrate ", "", "bench"):
			with self.subTest(command=command):
				self.assertEqual(self.build(command), NOT_LISTED_REFUSAL)

	def test_bench_args_refuse_wrong_types(self):
		for args in (
			None,
			"version",
			("version",),
			[],
			[None],
			["version", 1],
			[["version"]],
			{"version": 1},
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), NOT_LISTED_REFUSAL)
		for command in (None, 5, ["migrate"]):
			with self.subTest(command=command):
				self.assertEqual(self.build(command), NOT_LISTED_REFUSAL)
		for app in (5, ["myapp"], b"myapp"):
			with self.subTest(app=app):
				self.assertEqual(self.build("build", app), APP_NOT_ALLOWED_REFUSAL)
				self.assertEqual(self.build("migrate", app), TAKES_NO_APP_REFUSAL)
		# `allowed_apps` must be a collection of names: a plain string would match by substring.
		for allowed in ("myapp", "xmyappx", None, ("myapp", 1), {"myapp": 1}):
			with self.subTest(allowed=allowed):
				self.assertEqual(self.build("build", "myapp", allowed), APP_NOT_ALLOWED_REFUSAL)
				self.assertEqual(self.check(["build", "--app", "myapp"], allowed), NOT_LISTED_REFUSAL)
				self.assertEqual(self.build("migrate", None, allowed), ["--site", "site1.test", "migrate"])
		self.assertEqual(self.build("build", "app", "myapp"), APP_NOT_ALLOWED_REFUSAL)
		self.assertEqual(self.build("build", "myapp", ["myapp"]), ["build", "--app", "myapp"])
		self.assertEqual(self.build("build", "myapp", frozenset({"myapp"})), ["build", "--app", "myapp"])
