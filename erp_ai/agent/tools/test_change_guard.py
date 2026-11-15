import os
import threading
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

import erp_ai
from erp_ai.agent.changes import process_runner
from erp_ai.agent.tools import change_guard, source
from erp_ai.constants import (
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
	CORE_APPS,
)
from erp_ai.test_utils import GitSandbox, TempAppsRoot, keep_agent_settings, set_agent_settings

ALLOWED = ("myapp",)
SITE = "site1.test"

# Refusal sentences of design 3.1 / 3.2, typed here so the tests do not compare a constant with itself.
SHELL_REFUSAL = "đối số chứa ký tự điều khiển shell"
FORCE_REFUSAL = "cờ --force bị cấm"
OTHER_SITE_REFUSAL = "chỉ chạy cho site đang chạy"
NOT_LISTED_REFUSAL = "lệnh không có trong danh sách cho phép"
NEEDS_APP_REFUSAL = "lệnh build cần app"
TAKES_NO_APP_REFUSAL = "lệnh này không nhận app"
PATH_INVALID_REFUSAL = "đường dẫn không hợp lệ hoặc nằm ngoài apps/"
APP_NOT_ALLOWED_REFUSAL = "app không có trong danh sách được sửa"
APP_FORBIDDEN_REFUSAL = "không được sửa app erp_ai hoặc kho git của nó"
GIT_PATTERN_REFUSAL = 'tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được'
PATH_INVALID_REFUSAL = "đường dẫn không hợp lệ hoặc nằm ngoài apps/"
NAME_FORBIDDEN_REFUSAL = "tên file thuộc loại bí mật hoặc được bảo vệ"
GIT_DIR_REFUSAL = "không được chạm .git hoặc tên bắt đầu bằng .git"
PATH_SYMLINK_REFUSAL = "đường dẫn đi qua symlink"
NESTED_REPO_REFUSAL = "đường dẫn nằm trong một kho git lồng trong app"
BLOCK_EMPTY_REFUSAL = "khối không có mục file hay lệnh nào"
BLOCK_TOO_MANY_OPS_REFUSAL = "khối có hơn 50 mục file"
BLOCK_TOO_MANY_COMMANDS_REFUSAL = "khối có hơn 6 lệnh"
BLOCK_PATH_TWICE_REFUSAL = "đường dẫn trùng hoặc nằm trong đường dẫn khác của cùng khối"
OP_UNKNOWN_REFUSAL = "loại mục phải là edit, create, delete hoặc rename"
BLOCK_TOO_LARGE_REFUSAL = "tổng nội dung của khối (kể cả diff) lớn hơn 8 MiB"
TEXT_TOO_LARGE_REFUSAL = "file lớn hơn 2 MiB"
TEXT_HAS_NUL_REFUSAL = "file có byte NUL, không phải văn bản"
TEXT_NOT_UTF8_REFUSAL = "file không phải văn bản UTF-8"
RESTART_PLACE_REFUSAL = "restart chỉ được một lần và phải là lệnh cuối"
RESTART_NEEDS_MIGRATE_REFUSAL = "khối có file và restart phải có migrate đứng trước restart"
PY_NEEDS_RESTART_REFUSAL = "khối có file .py phải kết thúc bằng migrate rồi restart"
RESTART_WITHOUT_PY_REFUSAL = "khối có file nhưng không có file .py thì không restart"
MIB = 1024 * 1024

HAND_WRITTEN_CORE_APPS = ("frappe", "erpnext", "helpdesk", "hrms")
# design-addendum-2 QĐ-A2: refused and allowed names, under one app.
GIT_PATTERN_REFUSED = (
	"custom_app/[id].vue",
	"custom_app/src/a*.py",
	"custom_app/a?.py",
	"custom_app/a].py",
	"custom_app/:x.py",
	"custom_app/-x.py",
)
GIT_PATTERN_ALLOWED = ("custom_app/sub/-x.py", "custom_app/a:b.py")

# Denied list of spec A-6 plus ADR-022 QĐ 2 (design 8.1), without `restart` (FEAT-004 Amd-4 Q-2,
# AC-47): 22 names.
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
		# The temp root holds no git repos: these T7-T9 checks run without the git read (T42).
		return change_guard.check_write_path(rel, allowed, new_file=new_file, read_git=False).reason

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
				change_guard.GIT_DIR,
				change_guard.PATH_GIT_PATTERN,
			),
			(
				"đường dẫn không hợp lệ hoặc nằm ngoài apps/",
				"app không có trong danh sách được sửa",
				"không được sửa app erp_ai hoặc kho git của nó",
				"tên file thuộc loại bí mật hoặc được bảo vệ",
				"không được chạm .git hoặc tên bắt đầu bằng .git",
				'tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được',
			),
		)

	def test_double_refusal_returns_earlier_reason_of_table_order(self):
		for rel, expected in (
			("otherapp/.env", change_guard.APP_NOT_ALLOWED),
			("otherapp/run.sh", change_guard.APP_NOT_ALLOWED),
			("otherapp/.git/x.py", change_guard.APP_NOT_ALLOWED),
			("myapp/.git/run.sh", change_guard.GIT_DIR),
			("myapp/.git/config", change_guard.GIT_DIR),
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

	def test_refuses_git_dir_component(self):
		self.apps.write("myapp/.git/info.txt", "x\n")
		self.assertEqual(self.reason("myapp/.git/info.txt"), change_guard.GIT_DIR)
		self.assertEqual(self.reason("myapp/.git/hooks/pre_commit.py", new_file=True), change_guard.GIT_DIR)
		self.assertEqual(self.reason("myapp/sub/.git/x.json", new_file=True), change_guard.GIT_DIR)
		os.symlink(os.path.join(self.root, "myapp", ".git"), os.path.join(self.root, "myapp", "gitlink"))
		self.assertEqual(self.reason("myapp/gitlink/info.txt"), change_guard.GIT_DIR)

	def test_any_text_extension_allowed(self):
		# AC-44, design 3.2: the extension step is gone; which bytes are text is `text_refusal`'s call later.
		self.apps.write("myapp/run.sh", "echo\n")
		self.assertFalse(hasattr(change_guard, "EXT_FORBIDDEN"))
		for rel, new_file in (
			("myapp/run.sh", False),
			("myapp/new.sh", True),
			("myapp/lib.so", True),
			("myapp/tool.exe", True),
			("myapp/Makefile", True),
			("myapp/conf/settings", True),
			("myapp/pkg/Dockerfile.prod", True),
			("myapp/pyproject.toml", True),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ALLOWED, new_file=new_file, read_git=False)
				self.assertEqual(
					result,
					change_guard.GuardResult(
						full_path=os.path.join(self.root, rel), rel_path=rel, app="myapp", reason=None
					),
				)
		os.symlink(os.path.join(self.root, "myapp", "run.sh"), os.path.join(self.root, "myapp", "sh_link.py"))
		self.assertEqual(self.reason("myapp/sh_link.py"), change_guard.PATH_SYMLINK)

	def test_gitignore_gitattributes_github_refused_git_dir(self):
		# AC-50, design 3.2 step 4: any component starting with ".git", with the new wording of table 3.1.
		self.assertIs(change_guard.GIT_DIR, source.GIT_DIR)
		self.apps.write("myapp/.gitignore", "build/\n")
		for rel, new_file in (
			("myapp/.gitignore", False),
			("myapp/.gitattributes", True),
			("myapp/.github/workflows/ci.yml", True),
			("myapp/sub/.gitmodules", True),
			("myapp/.git/config", True),
			("myapp/.gitkeep", True),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ALLOWED, new_file=new_file, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, GIT_DIR_REFUSAL))
		# A component only containing ".git", not starting with it, is not the git rule.
		for rel in ("myapp/my.gitignore", "myapp/docs/notes.git", "myapp/.gi/x.py", "myapp/git/x.py"):
			with self.subTest(rel=rel):
				self.assertIsNone(self.reason(rel, new_file=True))
		# Order: app checks come before the git rule, the git rule before the git pattern rule.
		self.fake_erp_ai_repo()
		for rel, allowed, expected in (
			("otherapp/.github/ci.yml", ALLOWED, APP_NOT_ALLOWED_REFUSAL),
			("erp_ai/.github/ci.yml", ("myapp", "erp_ai"), APP_FORBIDDEN_REFUSAL),
			("myapp/.github/a*.yml", ALLOWED, GIT_DIR_REFUSAL),
			("myapp/-x/.gitignore", ALLOWED, GIT_DIR_REFUSAL),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, allowed, new_file=True), expected)

	def test_secret_name_refused_before_git_rule(self):
		# AC-51, design 3.2 step 4: the name rule is `text_refusal`'s, checked before the ".git*" one.
		self.assertIs(change_guard.NAME_FORBIDDEN, source.TEXT_SECRET_NAME)
		for rel in (
			"myapp/.github/.env",
			"myapp/.git/secret.py",
			"myapp/.gitignore/password.txt",
			"myapp/.github/license.txt",
			"myapp/.git/LICENSE.txt",
			"myapp/.github/deploy.pem",
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ALLOWED, new_file=True, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, NAME_FORBIDDEN_REFUSAL))
		# Order: app checks come before the name rule, the name rule before the git pattern rule.
		for rel, expected in (
			("otherapp/.github/.env", APP_NOT_ALLOWED_REFUSAL),
			("myapp/a*secret.py", NAME_FORBIDDEN_REFUSAL),
			("myapp/-x/license.txt", NAME_FORBIDDEN_REFUSAL),
			("myapp/:x.key", NAME_FORBIDDEN_REFUSAL),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=True), expected)

	def test_missing_app_dir_path_invalid(self):
		# AC-52, design 3.2: the app folder must exist; a listed name with no folder is PATH_INVALID.
		self.apps.write("flat.py", "x = 1\n")
		listed = ("myapp", "ghost", "flat.py")
		for rel in (
			"ghost/x.py",
			"ghost/pkg/new.py",
			"ghost/.env",
			"ghost/.github/ci.yml",
			"ghost/a*.py",
			"flat.py",
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, listed, new_file=True, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, PATH_INVALID_REFUSAL))
		# Order: a name not on the list stays APP_NOT_ALLOWED, folder or not.
		self.assertEqual(self.reason("ghost/x.py", ALLOWED, new_file=True), APP_NOT_ALLOWED_REFUSAL)
		self.assertIsNone(self.reason("myapp/x.py", listed, new_file=True))

	def test_app_dir_itself_path_invalid(self):
		# Design 3.2 step 2 (addendum-4 P-1.2 note 2): the app folder itself is no file to write.
		for rel in ("myapp", "myapp/", "myapp/."):
			for new_file in (True, False):
				with self.subTest(rel=rel, new_file=new_file):
					self.assertEqual(self.reason(rel, new_file=new_file), change_guard.PATH_INVALID)
		# Order (addendum-4 P-1.2 note 3): a name not on the list stays APP_NOT_ALLOWED.
		self.assertEqual(self.reason("helpdesk", new_file=True), change_guard.APP_NOT_ALLOWED)

	def test_erp_ai_in_allowed_list_still_refused(self):
		# AC-16 kept by design 3.2 step 3: `erp_ai` and its worktrees are refused before the name and git rules.
		self.fake_erp_ai_repo()
		listed = ("myapp", "erp_ai", "erp_ai-wt")
		for rel in (
			"erp_ai/run.sh",
			"erp_ai/Makefile",
			"erp_ai/.github/workflows/ci.yml",
			"erp_ai/.gitignore",
			"erp_ai/.env",
			"erp_ai/a*.py",
			"erp_ai-wt/tool.exe",
			"erp_ai-wt/.gitattributes",
			"erp_ai-wt/secret.py",
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, listed, new_file=True, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, APP_FORBIDDEN_REFUSAL))
		self.assertIsNone(self.reason("myapp/run.sh", listed, new_file=True))

	def test_allows_file_in_allowed_app(self):
		full = os.path.join(self.root, "myapp", "ok.py")
		self.assertEqual(
			change_guard.check_write_path("myapp/ok.py", ALLOWED, new_file=False, read_git=False),
			change_guard.GuardResult(full_path=full, rel_path="myapp/ok.py", app="myapp", reason=None),
		)
		new = change_guard.check_write_path(
			"myapp/pkg/new_module.py", ("myapp", "otherapp"), new_file=True, read_git=False
		)
		self.assertIsNone(new.reason)
		self.assertEqual(new.full_path, os.path.join(self.root, "myapp", "pkg", "new_module.py"))
		self.assertEqual((new.rel_path, new.app), ("myapp/pkg/new_module.py", "myapp"))
		normalized = change_guard.check_write_path(
			"myapp/sub/../ok.py", ALLOWED, new_file=False, read_git=False
		)
		self.assertEqual((normalized.rel_path, normalized.reason), ("myapp/ok.py", None))

	def test_new_file_in_manuals_refused(self):
		# design-w0-fixes-4 điểm 5: the bot may not write into the manuals store, neither a new nor an existing file.
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.apps.write("myapp/docs/hdsd.md", "# HDSD\n")
		set_agent_settings(manuals_dir="myapp/docs")
		for rel, new_file in (
			("myapp/docs/new.md", True),
			("myapp/docs/new_dir/new.md", True),
			("myapp/docs/hdsd.md", False),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=new_file), PATH_INVALID_REFUSAL)
		# A new file of the same app outside the store is not refused because of its path.
		for rel in ("myapp/new.md", "myapp/docs-other/new.md", "myapp/pkg/new_module.py"):
			with self.subTest(rel=rel):
				self.assertIsNone(self.reason(rel, new_file=True))

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

	def fake_repo(self, rel):
		"""A plain repo at `apps/<rel>` (a `.git` dir), written with file writes only."""
		self.apps.write(os.path.join(rel, ".git", "HEAD"), "ref: refs/heads/main\n")

	def link(self, target_rel, link_rel):
		"""Symlink `apps/<link_rel>` to `apps/<target_rel>`: a target inside the apps root."""
		os.symlink(os.path.join(self.root, target_rel), os.path.join(self.root, link_rel))

	def test_path_through_symlink_refused(self):
		# AC-50, design 3.2 step 6: any symlink on the existing part, even one pointing inside the apps root.
		self.assertEqual(change_guard.PATH_SYMLINK, PATH_SYMLINK_REFUSAL)
		self.apps.write("myapp/real/ok.py", "x = 1\n")
		self.apps.write("myapp/real.py", "x = 1\n")
		os.makedirs(os.path.join(self.root, "myapp", "sub"))
		self.link("myapp/real", "myapp/pkg_link")
		self.link("myapp/real", "myapp/sub/deep_link")
		os.makedirs(os.path.join(self.root, "myapp", "real", "inner"))
		self.link("myapp/real/inner", "myapp/deeper_link")
		self.link("myapp/real.py", "myapp/file_link.py")
		self.link("myapp/missing.py", "myapp/dangling.py")
		self.link("otherapp", "myapp/other_dir")
		self.link("otherapp/ok.py", "myapp/other_file.py")
		listed = ("myapp", "otherapp")
		for rel, new_file in (
			("myapp/pkg_link/ok.py", False),
			("myapp/pkg_link/new.py", True),
			("myapp/sub/deep_link/ok.py", False),
			# ".." after a symlink is applied to its target, not dropped as text.
			("myapp/deeper_link/../x.py", True),
			("myapp/sub/deep_link/../x.py", True),
			("myapp/file_link.py", False),
			("myapp/dangling.py", True),
			("myapp/other_dir/ok.py", False),
			("myapp/other_dir/new.py", True),
			("myapp/other_file.py", False),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, listed, new_file=new_file, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, PATH_SYMLINK_REFUSAL))
		# The same files by their real path pass: only the symlink on the way is refused.
		for rel in ("myapp/real/ok.py", "myapp/real.py", "otherapp/ok.py"):
			with self.subTest(rel=rel):
				self.assertIsNone(self.reason(rel, listed))
		# Order: earlier rules of design 3.2 classify the resolved path before the symlink step.
		for rel, allowed, expected in (
			("myapp/other_file.py", ALLOWED, APP_NOT_ALLOWED_REFUSAL),
			("myapp/link_out.py", listed, PATH_INVALID_REFUSAL),
			("myapp/pkg_link/a*.py", listed, GIT_PATTERN_REFUSAL),
		):
			with self.subTest(rel=rel, allowed=allowed):
				self.assertEqual(self.reason(rel, allowed, new_file=True), expected)

	def test_symlink_to_erp_ai_refused(self):
		# AC-50: a symlink into `erp_ai` or its worktree, at a middle or the last component, stays
		# APP_FORBIDDEN (design 3.2 step 3 comes before step 6); the symlink step does not hide it.
		self.fake_erp_ai_repo()
		os.makedirs(os.path.join(self.root, "myapp", "sub"))
		self.link("erp_ai", "myapp/sub/link_to_erp_ai")
		self.link("erp_ai/ok.py", "myapp/ai_file.py")
		self.link("erp_ai-wt", "myapp/link_to_wt")
		listed = ("myapp", "erp_ai", "erp_ai-wt")
		for rel, new_file in (
			("myapp/sub/link_to_erp_ai/ok.py", False),
			("myapp/sub/link_to_erp_ai/pkg/new.py", True),
			("myapp/ai_file.py", False),
			("myapp/link_to_wt/ok.py", False),
			("myapp/link_to_wt/new.py", True),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, listed, new_file=new_file, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, APP_FORBIDDEN_REFUSAL))
		# A symlink to a plain listed app next to it is the symlink step's.
		self.link("myapp/ok.py", "myapp/plain_link.py")
		self.assertEqual(self.reason("myapp/plain_link.py", listed), PATH_SYMLINK_REFUSAL)

	def test_nested_repo_refused(self):
		# Design 3.2 step 7: the nearest `.git` from the deepest existing folder must be the app's repo.
		self.assertEqual(change_guard.NESTED_REPO, NESTED_REPO_REFUSAL)
		self.fake_repo("myapp")
		self.fake_repo("myapp/vendor/lib")
		self.apps.write("myapp/vendor/lib/x.py", "x = 1\n")
		self.apps.write("myapp/vendor/lib/deep/y.py", "x = 1\n")
		self.apps.write("myapp/vendor/plain.py", "x = 1\n")
		# A submodule-like `gitdir:` file leading to another repo.
		self.apps.write("myapp/.git/modules/sub2/HEAD", "ref: refs/heads/main\n")
		self.apps.write("myapp/sub2/.git", f"gitdir: {self.root}/myapp/.git/modules/sub2\n")
		# A worktree of the app's own repo inside the app: same common dir, so not a nested repo.
		self.apps.write("myapp/.git/worktrees/wt/commondir", "../..\n")
		self.apps.write("myapp/wt/.git", f"gitdir: {self.root}/myapp/.git/worktrees/wt\n")
		self.apps.write("myapp/wt/ok.py", "x = 1\n")
		# An app with no repo of its own still refuses a repo inside it.
		self.fake_repo("otherapp/inner")
		listed = ("myapp", "otherapp")
		for rel, new_file in (
			("myapp/vendor/lib/x.py", False),
			("myapp/vendor/lib/new.py", True),
			("myapp/vendor/lib/deep/y.py", False),
			("myapp/sub2/new.py", True),
			("otherapp/inner/new.py", True),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, listed, new_file=new_file, read_git=False)
				self.assertEqual(result, change_guard.GuardResult(None, None, None, NESTED_REPO_REFUSAL))
		for rel, new_file in (
			("myapp/vendor/plain.py", False),
			("myapp/vendor/new.py", True),
			("myapp/wt/ok.py", False),
			("myapp/wt/pkg/new.py", True),
			("myapp/ok.py", False),
			("otherapp/ok.py", False),
		):
			with self.subTest(rel=rel):
				self.assertIsNone(self.reason(rel, listed, new_file=new_file))
		# Order: the git pattern step and the symlink step come before the nested repo step.
		self.link("myapp/vendor/lib", "myapp/lib_link")
		self.link("myapp/vendor/lib/deep", "myapp/deep_link")
		for rel, expected in (
			("myapp/vendor/lib/a*.py", GIT_PATTERN_REFUSAL),
			("myapp/lib_link/new.py", PATH_SYMLINK_REFUSAL),
			# "link/.." reaches a file of the nested repo (myapp/vendor/lib/x.py), not myapp/x.py.
			("myapp/deep_link/../x.py", PATH_SYMLINK_REFUSAL),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, listed, new_file=True), expected)

	def test_new_dirs_not_yet_existing_use_deepest_existing(self):
		# Design 3.2 steps 6-7 look at the existing part only; a missing tail is judged by its deepest
		# existing folder (a dangling symlink counts as existing).
		self.fake_repo("myapp")
		self.fake_repo("myapp/vendor/lib")
		self.apps.write("myapp/real/ok.py", "x = 1\n")
		self.link("myapp/real", "myapp/pkg_link")
		self.link("myapp/missing_dir", "myapp/dangling_dir")
		for rel in ("myapp/a", "myapp/a/b", "myapp/a/b/c/new.py", "myapp/real/x/y/new.py"):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ALLOWED, new_file=True, read_git=False)
				self.assertEqual(
					result,
					change_guard.GuardResult(
						full_path=os.path.join(self.root, rel), rel_path=rel, app="myapp", reason=None
					),
				)
		for rel, expected in (
			("myapp/pkg_link/x/y/new.py", PATH_SYMLINK_REFUSAL),
			("myapp/pkg_link/x", PATH_SYMLINK_REFUSAL),
			("myapp/dangling_dir/new.py", PATH_SYMLINK_REFUSAL),
			("myapp/vendor/lib/x/y/new.py", NESTED_REPO_REFUSAL),
			("myapp/vendor/lib/x", NESTED_REPO_REFUSAL),
		):
			with self.subTest(rel=rel):
				self.assertEqual(self.reason(rel, new_file=True), expected)


class TestCheckWritePathGit(FrappeTestCase):
	"""T42: core apps, the git state read at proposal time and git pattern names, on `GitSandbox` repos only."""

	def setUp(self):
		self.sandbox = GitSandbox(self)
		self.root = self.sandbox.root

	def head(self, app):
		return self.sandbox.git(app, "rev-parse", "HEAD").strip()

	def make_dirty(self, app, rel="README.md"):
		with open(os.path.join(self.sandbox.repo(app), rel), "a", encoding="utf-8") as handle:
			handle.write("changed\n")

	def git_reads(self):
		reads = patch.object(source, "run_git_read", wraps=source.run_git_read)
		mock = reads.start()
		self.addCleanup(reads.stop)
		return mock

	def test_core_apps_allowed_only_when_listed(self):
		self.assertEqual(CORE_APPS, ("frappe", "erpnext", "helpdesk", "hrms"))
		listed = (*HAND_WRITTEN_CORE_APPS, "custom_app")
		for app in HAND_WRITTEN_CORE_APPS:
			with self.subTest(app=app, listed=True):
				result = change_guard.check_write_path(f"{app}/README.md", listed, new_file=False)
				self.assertIsNone(result.reason)
				self.assertTrue(result.is_core_app)
				self.assertEqual(
					(result.app, result.git.branch, result.git.head), (app, "main", self.head(app))
				)
				no_git = change_guard.check_write_path(
					f"{app}/README.md", listed, new_file=False, read_git=False
				)
				self.assertEqual((no_git.reason, no_git.is_core_app, no_git.git), (None, True, None))
			with self.subTest(app=app, listed=False):
				result = change_guard.check_write_path(f"{app}/README.md", ("custom_app",), new_file=False)
				self.assertEqual(result.reason, APP_NOT_ALLOWED_REFUSAL)
				self.assertFalse(result.is_core_app)
				self.assertIsNone(result.git)
		# `erp_ai` is not a core app and stays refused even when listed (AC-16).
		for rel in ("erp_ai/README.md", "erp_ai-wt/README.md"):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, (*listed, "erp_ai", "erp_ai-wt"), new_file=False)
				self.assertEqual(result.reason, APP_FORBIDDEN_REFUSAL)
				self.assertFalse(result.is_core_app)
				self.assertIsNone(result.git)

	def test_non_core_app_has_no_core_flag(self):
		self.assertNotIn("custom_app", HAND_WRITTEN_CORE_APPS)
		for read_git in (True, False):
			with self.subTest(read_git=read_git):
				result = change_guard.check_write_path(
					"custom_app/README.md", ("custom_app",), new_file=False, read_git=read_git
				)
				self.assertIsNone(result.reason)
				self.assertFalse(result.is_core_app)

	def test_guard_returns_git_state_when_allowed(self):
		repo = self.sandbox.repo("custom_app")
		for rel, new_file, rel_in_repo in (
			("custom_app/README.md", False, "README.md"),
			("custom_app/pkg/new_module.py", True, "pkg/new_module.py"),
		):
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ("custom_app",), new_file=new_file)
				self.assertIsNone(result.reason)
				self.assertEqual(result.full_path, os.path.join(repo, rel_in_repo))
				self.assertEqual(
					result.git,
					source.GitState(
						refusal=None,
						repo_root=repo,
						rel_in_repo=rel_in_repo,
						branch="main",
						head=self.head("custom_app"),
						upstream_ref="",
						ahead_count=0,
					),
				)

	def test_guard_refuses_with_git_reason_and_read_git_false_skips_git(self):
		self.make_dirty("custom_app")
		reads = self.git_reads()
		refused = change_guard.check_write_path("custom_app/README.md", ("custom_app",), new_file=False)
		self.assertEqual(refused.reason, "file đích có thay đổi chưa commit")
		self.assertEqual((refused.full_path, refused.git, refused.is_core_app), (None, None, False))
		self.assertGreater(reads.call_count, 0)
		reads.reset_mock()
		skipped = change_guard.check_write_path(
			"custom_app/README.md", ("custom_app",), new_file=False, read_git=False
		)
		self.assertEqual((skipped.reason, skipped.git), (None, None))
		self.assertEqual(skipped.full_path, os.path.join(self.sandbox.repo("custom_app"), "README.md"))
		self.assertEqual(reads.call_count, 0)
		# An ignored new file is refused with the git sentence too, and only when git is read.
		self.sandbox.commit_file("custom_app", ".gitignore", "build/\n")
		self.assertEqual(
			change_guard.check_write_path("custom_app/build/out.js", ("custom_app",), new_file=True).reason,
			"file đích bị git bỏ qua (.gitignore)",
		)
		self.assertIsNone(
			change_guard.check_write_path(
				"custom_app/build/out.js", ("custom_app",), new_file=True, read_git=False
			).reason
		)

	def test_refuses_git_pattern_names(self):
		for rel in GIT_PATTERN_REFUSED:
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ("custom_app",), new_file=True)
				self.assertEqual(result.reason, GIT_PATTERN_REFUSAL)
				self.assertEqual((result.full_path, result.git), (None, None))
		for rel in GIT_PATTERN_ALLOWED:
			with self.subTest(rel=rel):
				result = change_guard.check_write_path(rel, ("custom_app",), new_file=True)
				self.assertIsNone(result.reason)
				self.assertEqual(result.git.rel_in_repo, rel.partition("/")[2])
		# Order of table 3.1: earlier refusals win over the git pattern one; it comes before the git read.
		for rel, expected in (
			("other/a*.py", APP_NOT_ALLOWED_REFUSAL),
			("custom_app/-secret.py", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			("custom_app/a*.sh", GIT_PATTERN_REFUSAL),
			("custom_app/.git/a*.py", change_guard.GIT_DIR),
			("custom_app/:x/.git/a.py", change_guard.GIT_DIR),
		):
			with self.subTest(rel=rel):
				self.assertEqual(
					change_guard.check_write_path(rel, ("custom_app",), new_file=True).reason, expected
				)
		# A tracked, dirty pattern name: git would say GIT_DIRTY, the pattern refusal comes first.
		self.sandbox.commit_file("custom_app", "a*.py", "x = 1\n")
		self.make_dirty("custom_app", "a*.py")
		self.assertEqual(
			change_guard.check_write_path("custom_app/a*.py", ("custom_app",), new_file=False).reason,
			GIT_PATTERN_REFUSAL,
		)

	def test_git_pattern_refusal_also_with_read_git_false(self):
		reads = self.git_reads()
		for rel in GIT_PATTERN_REFUSED:
			with self.subTest(rel=rel):
				for read_git in (True, False):
					result = change_guard.check_write_path(
						rel, ("custom_app",), new_file=True, read_git=read_git
					)
					self.assertEqual(result.reason, GIT_PATTERN_REFUSAL)
		self.assertEqual(reads.call_count, 0)

	def test_guard_and_process_runner_agree_on_git_pattern_names(self):
		repo = self.sandbox.repo("custom_app")
		for rel in GIT_PATTERN_REFUSED:
			with self.subTest(rel=rel, refused=True):
				self.assertEqual(
					change_guard.check_write_path(rel, ("custom_app",), new_file=True, read_git=False).reason,
					GIT_PATTERN_REFUSAL,
				)
				with self.assertRaises(ValueError):
					process_runner._check_git_write_call(repo, rel.partition("/")[2], 1)
		for rel in GIT_PATTERN_ALLOWED:
			with self.subTest(rel=rel, refused=False):
				self.assertIsNone(
					change_guard.check_write_path(rel, ("custom_app",), new_file=True, read_git=False).reason
				)
				self.assertIsNone(process_runner._check_git_write_call(repo, rel.partition("/")[2], 1))


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
		self.assertEqual(len(A6_DENIED_COMMANDS), 22)
		self.assertEqual(len(set(A6_DENIED_COMMANDS)), 22)
		for name in A6_DENIED_COMMANDS:
			with self.subTest(command=name):
				self.assertEqual(self.build(name), NOT_LISTED_REFUSAL)
				self.assertEqual(self.build(name, "myapp"), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name, "--app", "myapp"]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name, "myapp"]), NOT_LISTED_REFUSAL)

	def test_bench_allow_list_is_exactly_the_seven_design_commands(self):
		# Design 3.2 / spec A-6: the allow-list is the mechanism; every other command is refused.
		self.assertEqual(
			set(change_guard.BENCH_COMMANDS),
			{"migrate", "build", "clear-cache", "clear-website-cache", "list-apps", "version", "restart"},
		)
		self.assertEqual(len(change_guard.BENCH_COMMANDS), 7)
		for name in ("trim-database", "doctor", "show-config", "destroy-all-sessions"):
			with self.subTest(command=name):
				self.assertNotIn(name, A6_DENIED_COMMANDS)
				self.assertEqual(self.build(name), NOT_LISTED_REFUSAL)
				self.assertEqual(self.build(name, "myapp"), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check(["--site", "site1.test", name]), NOT_LISTED_REFUSAL)
				self.assertEqual(self.check([name]), NOT_LISTED_REFUSAL)

	def test_restart_plain_accepted(self):
		# Design 3.2 / AC-47: the one new shape is `["restart"]`, no site, no app, no flag.
		self.assertEqual(self.build("restart"), ["restart"])
		self.assertIsNone(self.check(["restart"]))
		self.assertEqual(change_guard.RESTART_COMMAND, "restart")
		self.assertIn(change_guard.RESTART_COMMAND, change_guard.BENCH_COMMANDS)
		# Like `version`, the shape names no site, so it needs no running site.
		self.assertEqual(self.build("restart", None, ALLOWED, None), ["restart"])
		self.assertIsNone(self.check(["restart"], ALLOWED, None))
		self.assertIsNone(self.check(["restart"], ()))

	def test_restart_with_any_arg_refused(self):
		# Proposal time: an app given with `restart`.
		for app in ("myapp", "otherapp", ""):
			with self.subTest(build_app=app):
				self.assertEqual(self.build("restart", app), change_guard.CMD_TAKES_NO_APP)
		# Apply time: the whole stored argv must be exactly `["restart"]`.
		for args in (
			# an app
			["restart", "myapp"],
			["restart", "--app", "myapp"],
			["build", "--app", "myapp", "restart"],
			["--site", "site1.test", "restart", "myapp"],
			# a flag
			["restart", "--web"],
			["restart", "--supervisor"],
			["restart", "--systemd"],
			["--web", "restart"],
			# a site option, even the running site
			["--site", "site1.test", "restart"],
			["restart", "--site", "site1.test"],
			["--site=site1.test", "restart"],
			# a second word
			["restart", "restart"],
			["restart", "migrate"],
			["restart", ""],
			["bench", "restart"],
			# not the plain word
			["Restart"],
			[" restart"],
			["restart "],
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), change_guard.CMD_NOT_LISTED)
		for command in ("Restart", "restart ", "restart --web"):
			with self.subTest(build_command=command):
				self.assertEqual(self.build(command), change_guard.CMD_NOT_LISTED)

	def test_every_denied_command_refused(self):
		# AC-47: 21 items (`mariadb`/`db-console` is one), refused at proposal and at apply time.
		denied = (
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
			"run-tests",
			"new-app",
			"switch-to-branch",
			"init",
		)
		self.assertEqual(len(set(denied)), 22)
		for name in denied:
			with self.subTest(command=name):
				self.assertNotIn(name, change_guard.BENCH_COMMANDS)
				self.assertEqual(self.build(name), change_guard.CMD_NOT_LISTED)
				self.assertEqual(self.build(name, "myapp"), change_guard.CMD_NOT_LISTED)
				self.assertEqual(self.check([name]), change_guard.CMD_NOT_LISTED)
				self.assertEqual(self.check(["--site", "site1.test", name]), change_guard.CMD_NOT_LISTED)
				self.assertEqual(self.check(["restart", name]), change_guard.CMD_NOT_LISTED)

	def test_force_shell_other_site_refused(self):
		# AC-47: the earlier steps of `check_bench_args` still win over the new `restart` shape.
		for char in (";", "|", "&", "`", "$(", ">", "<", "\n"):
			with self.subTest(char=char):
				self.assertEqual(self.check([f"restart{char}"]), change_guard.CMD_SHELL)
				self.assertEqual(self.check(["restart", f"x{char}y"]), change_guard.CMD_SHELL)
				self.assertEqual(self.build(f"restart{char}"), change_guard.CMD_NOT_LISTED)
		for args in (["restart", "--force"], ["--force", "restart"], ["restart", "--force=1"]):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), change_guard.CMD_FORCE)
		for args in (
			["--site", "other", "restart"],
			["restart", "--site", "other"],
			["restart", "--site=other"],
			["restart", "--site"],
		):
			with self.subTest(args=args):
				self.assertEqual(self.check(args), change_guard.CMD_OTHER_SITE)

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


def edit(path, before="x = 1\n", after="x = 2\n"):
	return change_guard.FileOp(CHANGE_OP_EDIT, path, None, before, after, None, None)


def create(path, after="x = 1\n"):
	return change_guard.FileOp(CHANGE_OP_CREATE, path, None, None, after, None, None)


def delete(path, before="x = 1\n"):
	return change_guard.FileOp(CHANGE_OP_DELETE, path, None, before, None, None, None)


def rename(path, new_path, text="x = 1\n"):
	return change_guard.FileOp(CHANGE_OP_RENAME, path, new_path, text, text, None, None)


MOMENTS = (False, True)  # `at_apply`: proposal time (git read) and apply time (CHG-002 design 3.2)
README = "myapp/README.md"
MIGRATE = ["--site", SITE, "migrate"]
RESTART = ["restart"]
# A block with a `.py` file must end with migrate then restart (CHG-002 design 3.2 step 4, D-3).
MIGRATE_RESTART = (MIGRATE, RESTART)


class TestCheckBlock(FrappeTestCase):
	"""CHG-002 design 3.2 `check_block`, on `GitSandbox` repos `myapp` and `otherapp` (both moments)."""

	def setUp(self):
		self.sandbox = GitSandbox(self, apps=("myapp", "otherapp"))
		self.root = self.sandbox.root

	def check(self, ops, commands=(), allowed=ALLOWED, *, at_apply, diff_text="", legacy=False):
		return change_guard.check_block(
			list(ops),
			[list(args) for args in commands],
			allowed,
			SITE,
			at_apply=at_apply,
			diff_text=diff_text,
			legacy=legacy,
		)

	def reason(self, ops, commands=(), allowed=ALLOWED, *, at_apply):
		return self.check(ops, commands, allowed, at_apply=at_apply).reason

	def test_refusal_wording_matches_design_table(self):
		self.assertEqual(
			(
				change_guard.BLOCK_EMPTY,
				change_guard.BLOCK_TOO_MANY_OPS,
				change_guard.BLOCK_TOO_MANY_COMMANDS,
				change_guard.BLOCK_TWO_APPS.format(a="a", b="b"),
				change_guard.BLOCK_PATH_TWICE,
				change_guard.OP_UNKNOWN,
				change_guard.OP_FIELDS.format(action="edit"),
				change_guard.NOT_REGULAR_FILE,
				change_guard.EXECUTABLE_FILE,
			),
			(
				BLOCK_EMPTY_REFUSAL,
				BLOCK_TOO_MANY_OPS_REFUSAL,
				BLOCK_TOO_MANY_COMMANDS_REFUSAL,
				"các mục file thuộc hai app a và b; mỗi app một đề xuất",
				BLOCK_PATH_TWICE_REFUSAL,
				OP_UNKNOWN_REFUSAL,
				"mục edit thiếu hoặc thừa trường",
				"đường dẫn không phải file thường",
				"file có quyền thực thi, bot không xóa hay đổi tên được",
			),
		)

	def test_valid_block_returns_app_and_targets_in_item_order(self):
		self.sandbox.commit_file("myapp", "old.py", "x = 1\n")
		ops = (
			edit(README),
			create("myapp/pkg/sub/new.py"),
			delete("myapp/old.py"),
			rename("myapp/README2.md", "myapp/moved/README2.md"),
		)
		self.sandbox.commit_file("myapp", "README2.md", "x = 1\n")
		repo = self.sandbox.repo("myapp")
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				result = self.check(ops, MIGRATE_RESTART, at_apply=at_apply)
				self.assertIsNone(result.reason)
				self.assertEqual(result.app, "myapp")
				self.assertEqual(
					[
						(target.op, target.full_path, target.full_new_path, target.new_dirs)
						for target in result.targets
					],
					[
						(ops[0], os.path.join(repo, "README.md"), None, ()),
						(
							ops[1],
							os.path.join(repo, "pkg", "sub", "new.py"),
							None,
							(os.path.join(repo, "pkg"), os.path.join(repo, "pkg", "sub")),
						),
						(ops[2], os.path.join(repo, "old.py"), None, ()),
						(
							ops[3],
							os.path.join(repo, "README2.md"),
							os.path.join(repo, "moved", "README2.md"),
							(os.path.join(repo, "moved"),),
						),
					],
				)
				# `read_git = not at_apply`: the git state is read only at proposal time.
				self.assertEqual(
					[target.guard.git is None for target in result.targets], [at_apply] * len(ops)
				)
				self.assertEqual([target.guard.app for target in result.targets], ["myapp"] * len(ops))

	def test_command_only_block_has_no_app(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				result = self.check((), (["version"],), at_apply=at_apply)
				self.assertEqual((result.reason, result.app, tuple(result.targets)), (None, None, ()))

	def test_empty_block_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				result = self.check((), (), at_apply=at_apply)
				self.assertEqual(
					(result.reason, result.app, tuple(result.targets)), (BLOCK_EMPTY_REFUSAL, None, ())
				)

	def test_ops_50_ok_51_refused(self):
		fifty = [create(f"myapp/f{index}.txt") for index in range(50)]
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertIsNone(self.reason(fifty, at_apply=at_apply))
				self.assertEqual(
					self.reason([*fifty, create("myapp/f50.txt")], at_apply=at_apply),
					BLOCK_TOO_MANY_OPS_REFUSAL,
				)
				# The count comes before any item check: 51 items whose first is refused still name the count.
				self.assertEqual(
					self.reason([create("otherapp/x.txt"), *fifty], at_apply=at_apply),
					BLOCK_TOO_MANY_OPS_REFUSAL,
				)

	def test_commands_6_ok_7_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertIsNone(self.reason((), [["version"]] * 6, at_apply=at_apply))
				self.assertIsNone(self.reason([edit(README)], [["version"]] * 6, at_apply=at_apply))
				self.assertEqual(
					self.reason((), [["version"]] * 7, at_apply=at_apply), BLOCK_TOO_MANY_COMMANDS_REFUSAL
				)
				self.assertEqual(
					self.reason([create("otherapp/x.txt")], [["version"]] * 7, at_apply=at_apply),
					BLOCK_TOO_MANY_COMMANDS_REFUSAL,
				)

	def test_two_apps_refused_names_both(self):
		both = ("myapp", "otherapp")
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertEqual(
					self.reason([edit(README), edit("otherapp/README.md")], allowed=both, at_apply=at_apply),
					"mục 2 (otherapp/README.md): các mục file thuộc hai app myapp và otherapp; mỗi app một đề xuất",
				)
				self.assertEqual(
					self.reason([rename(README, "otherapp/moved.md")], allowed=both, at_apply=at_apply),
					"mục 1 (myapp/README.md): các mục file thuộc hai app myapp và otherapp; mỗi app một đề xuất",
				)
				self.assertIsNone(
					self.reason([edit(README), create("myapp/x.txt")], allowed=both, at_apply=at_apply)
				)

	def test_path_twice_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				for ops, number, path in (
					([edit(README), edit(README)], 2, README),
					([edit(README), delete("myapp/./README.md")], 2, "myapp/./README.md"),
					([edit(README), rename("myapp/a.md", README)], 2, "myapp/a.md"),
					([rename(README, README)], 1, README),
				):
					with self.subTest(ops=ops):
						self.assertEqual(
							self.reason(ops, at_apply=at_apply),
							f"mục {number} ({path}): {BLOCK_PATH_TWICE_REFUSAL}",
						)

	def test_path_inside_another_path_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				for ops, number, path in (
					([create("myapp/pkg"), create("myapp/pkg/a.py")], 2, "myapp/pkg/a.py"),
					([create("myapp/pkg/a.py"), create("myapp/pkg")], 2, "myapp/pkg"),
					([rename(README, "myapp/README.md/x.md")], 1, README),
				):
					with self.subTest(ops=ops):
						self.assertEqual(
							self.reason(ops, at_apply=at_apply),
							f"mục {number} ({path}): {BLOCK_PATH_TWICE_REFUSAL}",
						)
				# A shared name prefix is not nesting.
				self.assertIsNone(
					self.reason(
						[create("myapp/pkg/a.py"), create("myapp/pkg2/a.py")],
						MIGRATE_RESTART,
						at_apply=at_apply,
					)
				)

	def test_new_dir_directly_under_apps_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertEqual(
					self.reason([create("newapp/x.py")], allowed=("myapp", "newapp"), at_apply=at_apply),
					f"mục 1 (newapp/x.py): {PATH_INVALID_REFUSAL}",
				)
				self.assertEqual(
					self.reason(
						[rename(README, "newapp/x.md")], allowed=("myapp", "newapp"), at_apply=at_apply
					),
					f"mục 1 (myapp/README.md): {PATH_INVALID_REFUSAL}",
				)

	def test_new_dir_under_sites_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				for path in ("../sites/new/x.txt", "myapp/../../sites/new/x.txt"):
					with self.subTest(path=path):
						self.assertEqual(
							self.reason([create(path)], at_apply=at_apply),
							f"mục 1 ({path}): {PATH_INVALID_REFUSAL}",
						)

	def test_new_dir_in_unlisted_app_refused(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertEqual(
					self.reason([create("otherapp/newdir/x.py")], at_apply=at_apply),
					f"mục 1 (otherapp/newdir/x.py): {APP_NOT_ALLOWED_REFUSAL}",
				)
				self.assertEqual(
					self.reason([rename(README, "otherapp/newdir/x.md")], at_apply=at_apply),
					f"mục 1 ({README}): {APP_NOT_ALLOWED_REFUSAL}",
				)

	def test_each_new_dir_checked_on_its_own(self):
		# The file path passes `check_write_path`; only the new folder `license.txt` is a protected name.
		for path in ("myapp/license.txt/x.py", "myapp/a/LICENSE.TXT/b/x.py"):
			self.assertIsNone(
				change_guard.check_write_path(path, ALLOWED, new_file=True, read_git=False).reason
			)
			for at_apply in MOMENTS:
				with self.subTest(path=path, at_apply=at_apply):
					self.assertEqual(
						self.reason([create(path)], at_apply=at_apply),
						f"mục 1 ({path}): {NAME_FORBIDDEN_REFUSAL}",
					)
					self.assertEqual(
						self.reason([rename(README, path)], at_apply=at_apply),
						f"mục 1 ({README}): {NAME_FORBIDDEN_REFUSAL}",
					)

	def test_unknown_kind_refused(self):
		for at_apply in MOMENTS:
			for kind in ("edit", "Sua", None, ""):
				with self.subTest(kind=kind, at_apply=at_apply):
					op = change_guard.FileOp(kind, README, None, "x = 1\n", "x = 2\n", None, None)
					self.assertEqual(
						self.reason([edit("myapp/a.md"), op], at_apply=at_apply),
						f"mục 2 ({README}): {OP_UNKNOWN_REFUSAL}",
					)

	def test_fields_missing_or_extra_for_kind_refused(self):
		text = "x = 1\n"
		cases = (
			("edit", change_guard.FileOp(CHANGE_OP_EDIT, README, "myapp/b.md", text, text, None, None)),
			("edit", change_guard.FileOp(CHANGE_OP_EDIT, README, None, None, text, None, None)),
			("edit", change_guard.FileOp(CHANGE_OP_EDIT, README, None, text, None, None, None)),
			("create", change_guard.FileOp(CHANGE_OP_CREATE, "myapp/n.md", None, text, text, None, None)),
			("create", change_guard.FileOp(CHANGE_OP_CREATE, "myapp/n.md", None, None, None, None, None)),
			(
				"create",
				change_guard.FileOp(CHANGE_OP_CREATE, "myapp/n.md", "myapp/b.md", None, text, None, None),
			),
			("delete", change_guard.FileOp(CHANGE_OP_DELETE, README, None, text, text, None, None)),
			("delete", change_guard.FileOp(CHANGE_OP_DELETE, README, None, None, None, None, None)),
			("delete", change_guard.FileOp(CHANGE_OP_DELETE, README, "myapp/b.md", text, None, None, None)),
			("rename", change_guard.FileOp(CHANGE_OP_RENAME, README, None, text, text, None, None)),
			("rename", change_guard.FileOp(CHANGE_OP_RENAME, README, "myapp/b.md", None, text, None, None)),
			("rename", change_guard.FileOp(CHANGE_OP_RENAME, README, "myapp/b.md", text, None, None, None)),
			("rename", change_guard.FileOp(CHANGE_OP_RENAME, README, 5, text, text, None, None)),
			("edit", change_guard.FileOp(CHANGE_OP_EDIT, README, None, b"x", text, None, None)),
		)
		for at_apply in MOMENTS:
			for action, op in cases:
				with self.subTest(op=op, at_apply=at_apply):
					self.assertEqual(
						self.reason([op], at_apply=at_apply),
						f"mục 1 ({op.path}): mục {action} thiếu hoặc thừa trường",
					)
			# A path that is not a string is a missing field too (the shown path is T14's concern).
			for path in (None, 5, b"myapp/a.md"):
				with self.subTest(path=path, at_apply=at_apply):
					op = change_guard.FileOp(CHANGE_OP_EDIT, path, None, text, text, None, None)
					self.assertTrue(
						self.reason([op], at_apply=at_apply).endswith("): mục edit thiếu hoặc thừa trường")
					)

	def test_reason_names_item_number_and_path(self):
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				ops = [edit(README), create("myapp/x.txt"), create("myapp/.env.txt")]
				self.assertEqual(
					self.reason(ops, at_apply=at_apply), f"mục 3 (myapp/.env.txt): {NAME_FORBIDDEN_REFUSAL}"
				)
				# The first refused item is the one named, even when a later item is refused too.
				ops = [edit(README), create("otherapp/x.txt"), create("myapp/.env.txt")]
				self.assertEqual(
					self.reason(ops, at_apply=at_apply), f"mục 2 (otherapp/x.txt): {APP_NOT_ALLOWED_REFUSAL}"
				)

	def test_proposal_time_reads_git_state_of_every_path(self):
		self.sandbox.commit_file("myapp", "old.py", "x = 1\n")
		with open(os.path.join(self.sandbox.repo("myapp"), "old.py"), "a", encoding="utf-8") as handle:
			handle.write("changed\n")
		for ops, path in (
			([edit("myapp/old.py")], "myapp/old.py"),
			([edit(README), edit("myapp/old.py")], "myapp/old.py"),
		):
			with self.subTest(ops=ops):
				reason = self.reason(ops, at_apply=False)
				self.assertTrue(reason.startswith(f"mục {len(ops)} ({path}): "), reason)
				self.assertIsNone(self.reason(ops, MIGRATE_RESTART, at_apply=True))
		# A dirty rename target is refused at proposal time, not at apply time.
		self.sandbox.commit_file("myapp", "target.md", "x = 1\n")
		os.remove(os.path.join(self.sandbox.repo("myapp"), "target.md"))
		ops = [rename(README, "myapp/target.md")]
		self.assertTrue(self.reason(ops, at_apply=False).startswith(f"mục 1 ({README}): "))
		self.assertIsNone(self.reason(ops, at_apply=True))

	def test_content_refusal_wording_matches_design_table(self):
		self.assertEqual(
			(
				change_guard.BLOCK_TOO_LARGE,
				change_guard.PY_SYNTAX.format(n=3),
				change_guard.JSON_SYNTAX.format(n=4),
			),
			(
				BLOCK_TOO_LARGE_REFUSAL,
				"file .py không biên dịch được: dòng 3",
				"file .json không phải JSON hợp lệ: dòng 4",
			),
		)

	def assert_refused_in_both_moments(self, ops, expected, diff_text="", commands=(), legacy=False):
		for at_apply in MOMENTS:
			with self.subTest(
				ops=[(op.kind, op.path, op.new_path) for op in ops],
				commands=commands,
				legacy=legacy,
				at_apply=at_apply,
			):
				result = self.check(ops, commands, at_apply=at_apply, diff_text=diff_text, legacy=legacy)
				self.assertEqual(result.reason, expected)

	def assert_accepted_in_both_moments(self, ops, diff_text="", commands=(), legacy=False):
		self.assert_refused_in_both_moments(ops, None, diff_text, commands, legacy)

	def test_py_syntax_error_refused_with_line(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		self.sandbox.commit_file("myapp", "broken.py", "def f(:\n")
		self.assert_refused_in_both_moments(
			[create("myapp/bad.py", "x = 1\ndef f(:\n")],
			"mục 1 (myapp/bad.py): file .py không biên dịch được: dòng 2",
		)
		self.assert_refused_in_both_moments(
			[edit(README), edit("myapp/a.py", "x = 1\n", "x = 1\n\n\nif x\n")],
			"mục 2 (myapp/a.py): file .py không biên dịch được: dòng 4",
		)
		# Parser stack overflow is a MemoryError: line 0.
		self.assert_refused_in_both_moments(
			[create("myapp/deep.py", "-" * 100000 + "1\n")],
			"mục 1 (myapp/deep.py): file .py không biên dịch được: dòng 0",
		)
		with patch.object(change_guard, "compile", side_effect=RecursionError, create=True) as compiled:
			self.assert_refused_in_both_moments(
				[create("myapp/rec.py", "x = 1\n")],
				"mục 1 (myapp/rec.py): file .py không biên dịch được: dòng 0",
			)
		self.assertEqual(compiled.call_args.args, ("x = 1\n", "myapp/rec.py", "exec"))
		self.assertEqual(compiled.call_args.kwargs, {"dont_inherit": True})
		# `compile` does not run the code; only the content after the change of a `.py` target is compiled.
		self.assert_accepted_in_both_moments(
			[
				create("myapp/exits.py", "raise SystemExit(1)\n"),
				create("myapp/empty.py", ""),
				edit("myapp/a.py", "def f(:\n", "x = 2\n"),
				delete("myapp/broken.py", "def f(:\n"),
				create("myapp/bad.txt", "def f(:\n"),
			],
			commands=MIGRATE_RESTART,
		)

	def test_json_invalid_refused_with_line(self):
		self.assert_refused_in_both_moments(
			[create("myapp/a.json", '{\n"a": 1,\n}\n')],
			"mục 1 (myapp/a.json): file .json không phải JSON hợp lệ: dòng 3",
		)
		self.assert_refused_in_both_moments(
			[create("myapp/x.txt"), create("myapp/empty.json", "")],
			"mục 2 (myapp/empty.json): file .json không phải JSON hợp lệ: dòng 1",
		)
		self.assert_refused_in_both_moments(
			[create("myapp/deep.json", "[" * 100000 + "]" * 100000)],
			"mục 1 (myapp/deep.json): file .json không phải JSON hợp lệ: dòng 0",
		)
		self.assert_accepted_in_both_moments(
			[create("myapp/ok.json", '{"a": [1, 2]}\n'), create("myapp/bad.txt", '{"a": 1,}')]
		)

	def test_rename_dest_py_checked(self):
		self.sandbox.commit_file("myapp", "notes.txt", "def f(:\n")
		self.sandbox.commit_file("myapp", "old.py", "def f(:\n")
		self.sandbox.commit_file("myapp", "data.txt", "{,}\n")
		self.assert_refused_in_both_moments(
			[rename("myapp/notes.txt", "myapp/notes.py", "def f(:\n")],
			"mục 1 (myapp/notes.txt): file .py không biên dịch được: dòng 1",
		)
		self.assert_refused_in_both_moments(
			[rename("myapp/data.txt", "myapp/data.json", "{,}\n")],
			"mục 1 (myapp/data.txt): file .json không phải JSON hợp lệ: dòng 1",
		)
		# The source name of a rename is not compiled.
		self.assert_accepted_in_both_moments(
			[rename("myapp/old.py", "myapp/old.txt", "def f(:\n")], commands=MIGRATE_RESTART
		)

	def test_total_bytes_at_limit_ok_plus_one_refused(self):
		two_mib = "é" * MIB  # 2 MiB of UTF-8 in 1 Mi characters: bytes are counted, not characters.
		self.sandbox.commit_file("myapp", "big.txt", two_mib)
		self.sandbox.commit_file("myapp", "a.txt", "x = 1\n")
		self.sandbox.commit_file("myapp", "d.txt", "x = 1\n")
		# A rename stores its content twice and counts twice: 4 + 2 + (2 MiB - 10) = 8 MiB - 10.
		renamed = [
			rename("myapp/big.txt", "myapp/big2.txt", two_mib),
			create("myapp/c1.txt", two_mib),
			create("myapp/c2.txt", "x" * (2 * MIB - 10)),
		]
		self.assert_accepted_in_both_moments(renamed, "d" * 10)
		self.assert_accepted_in_both_moments(renamed, "é" * 5)
		self.assert_refused_in_both_moments(renamed, BLOCK_TOO_LARGE_REFUSAL, "d" * 11)
		self.assert_refused_in_both_moments(renamed, BLOCK_TOO_LARGE_REFUSAL, "é" * 5 + "d")
		# An edit counts before and after, a deletion its before: 2 + 2 + 2 + 2 = 8 MiB.
		edited = [
			edit("myapp/a.txt", "a" * (2 * MIB), "b" * (2 * MIB)),
			delete("myapp/d.txt", "d" * (2 * MIB)),
			create("myapp/c.txt", "c" * (2 * MIB)),
		]
		self.assert_accepted_in_both_moments(edited, "")
		self.assert_refused_in_both_moments(edited, BLOCK_TOO_LARGE_REFUSAL, "d")

	def test_total_counts_diff_bytes(self):
		small = [create("myapp/a.txt", "x")]
		self.assert_accepted_in_both_moments(small, "d" * (8 * MIB - 1))
		self.assert_refused_in_both_moments(small, BLOCK_TOO_LARGE_REFUSAL, "d" * (8 * MIB))
		self.assert_refused_in_both_moments(small, BLOCK_TOO_LARGE_REFUSAL, "é" * (4 * MIB))
		# A block with only commands has its diff counted too.
		for at_apply in MOMENTS:
			with self.subTest(at_apply=at_apply):
				self.assertIsNone(
					self.check([], [["version"]], at_apply=at_apply, diff_text="d" * 8 * MIB).reason
				)
				self.assertEqual(
					self.check([], [["version"]], at_apply=at_apply, diff_text="d" * (8 * MIB + 1)).reason,
					BLOCK_TOO_LARGE_REFUSAL,
				)

	def test_file_at_text_max_ok_plus_one_refused(self):
		self.sandbox.commit_file("myapp", "a.txt", "x = 1\n")
		self.sandbox.commit_file("myapp", "r.txt", "x = 1\n")
		at_max, over = "x" * (2 * MIB), "x" * (2 * MIB + 1)
		wide_over = "é" * MIB + "x"  # 1 Mi + 1 characters, 2 MiB + 1 bytes
		self.assert_accepted_in_both_moments(
			[create("myapp/f.txt", at_max), edit("myapp/a.txt", at_max, at_max)]
		)
		for ops, path in (
			([create("myapp/f.txt", over)], "myapp/f.txt"),
			([create("myapp/f.txt", wide_over)], "myapp/f.txt"),
			([edit("myapp/a.txt", over, "x")], "myapp/a.txt"),
			([edit("myapp/a.txt", "x", over)], "myapp/a.txt"),
			([delete("myapp/a.txt", over)], "myapp/a.txt"),
			([rename("myapp/r.txt", "myapp/r2.txt", over)], "myapp/r.txt"),
		):
			self.assert_refused_in_both_moments(ops, f"mục 1 ({path}): {TEXT_TOO_LARGE_REFUSAL}")
		self.assertIn("2 MiB", TEXT_TOO_LARGE_REFUSAL)
		# The item's own limit is checked in step 2, before the block total of step 3.
		self.assert_refused_in_both_moments(
			[create("myapp/x.txt"), create("myapp/f.txt", over)],
			f"mục 2 (myapp/f.txt): {TEXT_TOO_LARGE_REFUSAL}",
			"d" * (8 * MIB),
		)

	def test_content_with_nul_refused(self):
		self.sandbox.commit_file("myapp", "a.txt", "x = 1\n")
		for ops, path in (
			([create("myapp/n.txt", "a\0b")], "myapp/n.txt"),
			([create("myapp/n.py", "x = 1\0\n")], "myapp/n.py"),
			([edit("myapp/a.txt", "a\0", "b")], "myapp/a.txt"),
			([edit("myapp/a.txt", "a", "b\0")], "myapp/a.txt"),
			([delete("myapp/a.txt", "\0")], "myapp/a.txt"),
			([rename("myapp/a.txt", "myapp/b.txt", "\0")], "myapp/a.txt"),
		):
			self.assert_refused_in_both_moments(ops, f"mục 1 ({path}): {TEXT_HAS_NUL_REFUSAL}")

	def test_content_not_utf8_refused(self):
		self.sandbox.commit_file("myapp", "a.txt", "x = 1\n")
		for ops in (
			[create("myapp/n.txt", "a\ud800")],
			[edit("myapp/a.txt", "\udcff", "b")],
			[edit("myapp/a.txt", "a", "\ud800")],
		):
			self.assert_refused_in_both_moments(ops, f"mục 1 ({ops[0].path}): {TEXT_NOT_UTF8_REFUSAL}")

	def test_command_refusal_wording_matches_design_table(self):
		self.assertEqual(
			(
				change_guard.RESTART_PLACE,
				change_guard.RESTART_NEEDS_MIGRATE,
				change_guard.PY_NEEDS_RESTART,
				change_guard.RESTART_WITHOUT_PY,
			),
			(
				RESTART_PLACE_REFUSAL,
				RESTART_NEEDS_MIGRATE_REFUSAL,
				PY_NEEDS_RESTART_REFUSAL,
				RESTART_WITHOUT_PY_REFUSAL,
			),
		)

	def assert_commands_in_both_moments(self, commands, expected, legacy=False):
		for at_apply in MOMENTS:
			with self.subTest(commands=commands, legacy=legacy, at_apply=at_apply):
				result = self.check((), commands, at_apply=at_apply, legacy=legacy)
				self.assertEqual((result.reason, result.app, tuple(result.targets)), (expected, None, ()))

	def test_command_only_restart_block_valid(self):
		# R-5, AC-47: with no file item, a lone restart needs no migrate and no `.py`.
		for legacy in (False, True):
			self.assert_commands_in_both_moments([RESTART], None, legacy)
			self.assert_commands_in_both_moments([["version"], RESTART], None, legacy)
			self.assert_commands_in_both_moments([MIGRATE, RESTART], None, legacy)

	def test_restart_twice_or_not_last_refused(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		for legacy in (False, True):
			self.assert_commands_in_both_moments([RESTART, RESTART], RESTART_PLACE_REFUSAL, legacy)
			self.assert_commands_in_both_moments([RESTART, ["version"]], RESTART_PLACE_REFUSAL, legacy)
			self.assert_commands_in_both_moments([MIGRATE, RESTART, MIGRATE], RESTART_PLACE_REFUSAL, legacy)
			for commands in (
				[MIGRATE, RESTART, RESTART],
				[RESTART, MIGRATE, RESTART],
				[RESTART, MIGRATE],
			):
				self.assert_refused_in_both_moments(
					[edit("myapp/a.py")], RESTART_PLACE_REFUSAL, commands=commands, legacy=legacy
				)
		# Design 3.2 step 4: the place of restart is checked before `.py <=> restart`, so a block
		# with no `.py` and a misplaced restart gets RESTART_PLACE, not RESTART_WITHOUT_PY.
		for commands in ([MIGRATE, RESTART, RESTART], [RESTART, MIGRATE]):
			self.assert_refused_in_both_moments(
				[edit(README)], RESTART_PLACE_REFUSAL, commands=commands, legacy=False
			)

	def test_py_without_restart_refused(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		self.sandbox.commit_file("myapp", "old.py", "x = 1\n")
		self.sandbox.commit_file("myapp", "notes.txt", "x = 1\n")
		# A `.py` on any path of the block counts: edit, create, delete, rename source, rename target.
		for ops in (
			[edit("myapp/a.py")],
			[edit(README), create("myapp/pkg/new.py")],
			[delete("myapp/a.py")],
			[rename("myapp/old.py", "myapp/old.txt")],
			[rename("myapp/notes.txt", "myapp/notes.py")],
		):
			for commands in ((), [MIGRATE], [MIGRATE, ["--site", SITE, "clear-cache"]]):
				self.assert_refused_in_both_moments(ops, PY_NEEDS_RESTART_REFUSAL, commands=commands)
			self.assert_accepted_in_both_moments(ops, commands=MIGRATE_RESTART)

	def test_restart_without_py_refused(self):
		self.sandbox.commit_file("myapp", "a.py.txt", "x = 1\n")
		for ops in (
			[edit(README)],
			[create("myapp/x.json", "{}"), edit("myapp/a.py.txt")],
			[rename(README, "myapp/py/README.md")],
		):
			for commands in (MIGRATE_RESTART, [RESTART]):
				self.assert_refused_in_both_moments(ops, RESTART_WITHOUT_PY_REFUSAL, commands=commands)
			self.assert_accepted_in_both_moments(ops, commands=[MIGRATE])
			self.assert_accepted_in_both_moments(ops)

	def test_file_block_restart_without_migrate_refused(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		for commands in (
			[RESTART],
			[["version"], RESTART],
			[["--site", SITE, "clear-cache"], RESTART],
		):
			self.assert_refused_in_both_moments(
				[edit("myapp/a.py")], RESTART_NEEDS_MIGRATE_REFUSAL, commands=commands
			)
		# Migrate anywhere before restart passes.
		self.assert_accepted_in_both_moments(
			[edit("myapp/a.py")], commands=[MIGRATE, ["--site", SITE, "clear-cache"], RESTART]
		)
		# The migrate rule still applies to a legacy block that has a file and restart.
		self.assert_refused_in_both_moments(
			[edit(README)], RESTART_NEEDS_MIGRATE_REFUSAL, commands=[RESTART], legacy=True
		)
		self.assert_accepted_in_both_moments([edit(README)], commands=MIGRATE_RESTART, legacy=True)

	def test_legacy_py_without_restart_allowed(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		self.sandbox.commit_file("myapp", "old.py", "x = 1\n")
		for ops in ([edit("myapp/a.py")], [rename("myapp/old.py", "myapp/new.txt")]):
			self.assert_accepted_in_both_moments(ops, legacy=True)
			self.assert_accepted_in_both_moments(ops, commands=[MIGRATE], legacy=True)
		# Legacy also lets a file block without `.py` restart.
		self.assert_accepted_in_both_moments([edit(README)], commands=MIGRATE_RESTART, legacy=True)

	def test_denied_command_in_block_names_command_number(self):
		self.sandbox.commit_file("myapp", "a.py", "x = 1\n")
		for commands, expected in (
			([["--site", SITE, "migrate", "--force"]], f"lệnh 1: {FORCE_REFUSAL}"),
			([["version"], ["restart", "--now"]], f"lệnh 2: {NOT_LISTED_REFUSAL}"),
			([["version"], MIGRATE, ["--site", "other.test", "migrate"]], f"lệnh 3: {OTHER_SITE_REFUSAL}"),
			([["version"], ["version;", "x"], ["console"]], f"lệnh 2: {SHELL_REFUSAL}"),
			([["build", "--app", "otherapp"]], f"lệnh 1: {NOT_LISTED_REFUSAL}"),
			([["console"], RESTART, RESTART], f"lệnh 1: {NOT_LISTED_REFUSAL}"),
		):
			self.assert_commands_in_both_moments(commands, expected)
			self.assert_refused_in_both_moments([edit("myapp/a.py")], expected, commands=commands)
		# Item reasons (step 2) and the total (step 3) come before the commands (step 4).
		self.assert_refused_in_both_moments(
			[create("otherapp/x.txt")],
			f"mục 1 (otherapp/x.txt): {APP_NOT_ALLOWED_REFUSAL}",
			commands=[["console"]],
		)
		self.assert_refused_in_both_moments(
			[create("myapp/x.txt")], BLOCK_TOO_LARGE_REFUSAL, "d" * (8 * MIB), commands=[["console"]]
		)

	def test_empty_path_item_refused(self):
		# Design-addendum-5 P-6: an empty path (or rename target) is a shape refusal, in both moments.
		self.sandbox.commit_file("myapp", "notes.txt", "x = 1\n")
		text = "x = 1\n"
		for blank in ("", "   ", "\t\n"):
			for action, op in (
				("edit", change_guard.FileOp(CHANGE_OP_EDIT, blank, None, text, text, None, None)),
				("create", change_guard.FileOp(CHANGE_OP_CREATE, blank, None, None, text, None, None)),
				("delete", change_guard.FileOp(CHANGE_OP_DELETE, blank, None, text, None, None, None)),
				(
					"rename",
					change_guard.FileOp(CHANGE_OP_RENAME, blank, "myapp/b.txt", text, text, None, None),
				),
				(
					"rename",
					change_guard.FileOp(CHANGE_OP_RENAME, "myapp/notes.txt", blank, text, text, None, None),
				),
			):
				self.assert_refused_in_both_moments(
					[edit(README), op], f"mục 2 ({op.path}): mục {action} thiếu hoặc thừa trường"
				)
