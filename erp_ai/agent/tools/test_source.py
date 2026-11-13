import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import test_utils
from erp_ai.agent.tools import source
from erp_ai.test_utils import GitSandbox, RealCoreReposUntouchedMixin

ROOT_PATH = "erp_ai.agent.tools.source.get_source_root"


class TestSourceTools(FrappeTestCase):
	def setUp(self):
		base = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, base, True)
		self.root = os.path.join(base, "apps")
		self.outside = os.path.join(base, "outside")
		os.makedirs(os.path.join(self.root, "myapp"))
		os.makedirs(self.outside)
		patcher = patch(ROOT_PATH, return_value=self.root)
		patcher.start()
		self.addCleanup(patcher.stop)

	def write(self, rel, text, root=None):
		path = os.path.join(root or self.root, rel)
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "w", encoding="utf-8") as handle:
			handle.write(text)
		return path

	def test_path_escape_refused(self):
		self.write("plain.py", "x = 1\n", root=self.outside)
		self.write("myapp/ok.py", "x = 1\n")
		os.symlink(os.path.join(self.outside, "plain.py"), os.path.join(self.root, "myapp", "link.py"))
		os.symlink(self.outside, os.path.join(self.root, "dirlink"))

		self.assertIsNotNone(source.resolve_safe_path("myapp/ok.py"))
		self.assertIsNone(source.resolve_safe_path("../outside/plain.py"))
		self.assertIsNone(source.resolve_safe_path("myapp/../../outside/plain.py"))
		self.assertIsNone(source.resolve_safe_path(os.path.join(self.outside, "plain.py")))
		self.assertIsNone(source.resolve_safe_path("myapp/link.py"))
		self.assertIsNone(source.resolve_safe_path("dirlink/plain.py"))
		self.assertIsNone(source.resolve_safe_path(""))
		self.assertIsNone(source.resolve_safe_path("."))
		self.assertFalse(source.read_source({"path": "../outside/plain.py"}, None)["ok"])

	def test_secret_names_and_extensions_refused(self):
		for rel in (
			"myapp/site_config.json",
			"myapp/.env",
			"myapp/server.pem",
			"myapp/id_rsa",
			"myapp/my_credential.py",
			"myapp/Password.py",
			"myapp/secrets.txt",
			"myapp/tool.exe",
			"myapp/noext",
		):
			self.write(rel, "data\n")
			self.assertIsNone(source.resolve_safe_path(rel), rel)
			result = source.read_source({"path": rel}, None)
			self.assertFalse(result["ok"], rel)
			self.assertTrue(result["reason"])

		self.write("myapp/Notes.MD", "hello\n")
		self.assertIsNotNone(source.resolve_safe_path("myapp/Notes.MD"))
		self.assertEqual(
			source.DUOI_CHO_PHEP, {".py", ".js", ".vue", ".json", ".md", ".html", ".css", ".txt"}
		)

	def test_each_forbidden_name_pattern_blocked_with_allowed_extension(self):
		for rel in (
			"myapp/site_config.json",
			"myapp/common_site_config.json",
			"myapp/prod.env.json",
			"myapp/server.pem.txt",
			"myapp/deploy.key.md",
			"myapp/id_rsa.txt",
			"myapp/my_credential.py",
			"myapp/client_secret.json",
			"myapp/Password.py",
		):
			self.write(rel, "data\n")
			with self.subTest(rel=rel):
				self.assertIsNone(source.resolve_safe_path(rel))
				self.assertFalse(source.read_source({"path": rel}, None)["ok"])

	def test_forbidden_name_regex_matches_guide(self):
		self.assertEqual(
			source.TEN_CAM.pattern,
			r"(site_config\.json|common_site_config\.json|\.env|\.pem|\.key|id_rsa|credential|secret|password)",
		)
		self.assertTrue(source.TEN_CAM.flags & re.I)

	def test_sibling_prefix_directory_refused(self):
		self.write("ok.py", "x = 1\n", root=self.root + "_evil")
		self.addCleanup(shutil.rmtree, self.root + "_evil", True)
		self.assertIsNone(source.resolve_safe_path("../apps_evil/ok.py"))

	def test_unexpected_error_is_refused_and_logged(self):
		self.write("myapp/a.py", "a\n")
		with patch("erp_ai.agent.tools.source.open", side_effect=RuntimeError("boom"), create=True):
			with patch("erp_ai.agent.tools.source.logger") as logger:
				result = source.read_source({"path": "myapp/a.py"}, None)
		self.assertFalse(result["ok"])
		logger.exception.assert_called_once()

	def test_directory_and_missing_file_refused(self):
		self.assertFalse(source.read_source({"path": "myapp"}, None)["ok"])
		self.assertFalse(source.read_source({"path": "myapp/none.py"}, None)["ok"])
		self.assertFalse(source.read_source({}, None)["ok"])

	def test_read_capped_at_400_lines(self):
		self.write("myapp/big.py", "".join(f"line {i}\n" for i in range(1, 1001)))

		result = source.read_source({"path": "myapp/big.py", "limit": 5000}, None)
		self.assertTrue(result["ok"])
		self.assertEqual(result["from_line"], 1)
		self.assertEqual(result["total_lines"], 1000)
		self.assertEqual(len(result["content"].splitlines()), 400)

		default = source.read_source({"path": "myapp/big.py"}, None)
		self.assertEqual(len(default["content"].splitlines()), 200)

		paged = source.read_source({"path": "myapp/big.py", "offset": 991, "limit": 50}, None)
		self.assertEqual(paged["from_line"], 991)
		self.assertEqual(len(paged["content"].splitlines()), 10)
		self.assertTrue(paged["content"].startswith("line 991"))

	def test_read_bad_numbers_do_not_raise(self):
		self.write("myapp/a.py", "a\nb\n")
		result = source.read_source({"path": "myapp/a.py", "offset": "x", "limit": None}, None)
		self.assertTrue(result["ok"])
		self.assertEqual(result["from_line"], 1)
		result = source.read_source({"path": "myapp/a.py", "offset": -4, "limit": 0}, None)
		self.assertTrue(result["ok"])
		self.assertEqual(result["from_line"], 1)
		self.assertEqual(len(result["content"].splitlines()), 1)

	def test_search_capped_at_40_hits(self):
		self.write("myapp/many.py", "".join(f"needle {i}\n" for i in range(100)))
		self.write("myapp/more.py", "NEEDLE again\n" * 30)

		result = source.search_source({"pattern": "needle"}, None)
		self.assertTrue(result["ok"])
		self.assertEqual(len(result["hits"]), 40)
		hit = result["hits"][0]
		self.assertEqual(set(hit), {"path", "line", "text"})
		self.assertFalse(os.path.isabs(hit["path"]))

	def test_search_is_fixed_string_case_insensitive_and_filtered(self):
		self.write("myapp/a.py", "x = Foo(1)\n" + "y" * 500 + "foo(\n")
		self.write("myapp/b.js", "foo(\n")
		self.write("myapp/skip.png", "foo(\n")
		self.write("myapp/node_modules/x.js", "foo(\n")
		self.write("myapp/.hidden/x.py", "foo(\n")
		self.write("myapp/site_config.json", "foo(\n")
		with open(os.path.join(self.root, "myapp", "bad.py"), "wb") as handle:
			handle.write(b"foo(\xff\xfe\n")
		self.write("myapp/huge.py", "foo(\n" + "z" * (1024 * 1024 + 1))
		os.symlink(self.outside, os.path.join(self.root, "myapp", "outlink"))
		self.write("leak.py", "foo(\n", root=self.outside)

		result = source.search_source({"pattern": "foo("}, None)
		paths = sorted({hit["path"] for hit in result["hits"]})
		self.assertEqual(paths, ["myapp/a.py", "myapp/b.js", "myapp/bad.py"])
		self.assertTrue(all(len(hit["text"]) <= 300 for hit in result["hits"]))

		only_js = source.search_source({"pattern": "FOO(", "extension": ".js"}, None)
		self.assertEqual([hit["path"] for hit in only_js["hits"]], ["myapp/b.js"])

		scoped = source.search_source({"pattern": "foo(", "app": "myapp"}, None)
		self.assertTrue(scoped["ok"])
		self.assertEqual(len(scoped["hits"]), len(result["hits"]))

	def test_search_refuses_bad_input(self):
		for args in (
			{},
			{"pattern": "a"},
			{"pattern": "x" * 201},
			{"pattern": "foo", "app": "../outside"},
			{"pattern": "foo", "app": "/etc"},
			{"pattern": "foo", "extension": ".exe"},
		):
			result = source.search_source(args, None)
			self.assertFalse(result["ok"], args)
			self.assertTrue(result["reason"])

	def test_search_stops_after_time_budget(self):
		self.write("myapp/a.py", "needle\n")
		with patch("erp_ai.agent.tools.source.time.monotonic", side_effect=[0, 100, 100, 100]):
			result = source.search_source({"pattern": "needle"}, None)
		self.assertTrue(result["ok"])
		self.assertEqual(result["hits"], [])


RUN_PATH = "erp_ai.agent.tools.source.subprocess.run"


def completed(stdout="", stderr="", returncode=0):
	return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestGitSource(FrappeTestCase):
	def setUp(self):
		base = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, base, True)
		self.root = os.path.join(base, "apps")
		self.outside = os.path.join(base, "outside")
		os.makedirs(os.path.join(self.root, "myapp", ".git"))
		os.makedirs(os.path.join(self.root, "nogit"))
		os.makedirs(os.path.join(self.outside, ".git"))
		os.makedirs(os.path.join(self.root, "myapp", "src"))
		with open(os.path.join(self.root, "myapp", "src", "a.py"), "w", encoding="utf-8") as handle:
			handle.write("x = 1\n")
		with open(os.path.join(self.root, "myapp", "site_config.json"), "w", encoding="utf-8") as handle:
			handle.write("{}\n")
		self.repo = os.path.join(self.root, "myapp")
		patcher = patch(ROOT_PATH, return_value=self.root)
		patcher.start()
		self.addCleanup(patcher.stop)

	def git(self, subcommand, args=None, app="myapp"):
		payload = {"app": app, "subcommand": subcommand}
		if args is not None:
			payload["args"] = args
		return source.git_source(payload, None)

	def test_git_only_read_subcommands_and_safe_flags(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for sub in (
				"commit",
				"push",
				"config",
				"checkout",
				"reset",
				"show",
				"diff",
				"",
				None,
				"LOG",
				["log"],
			):
				self.assertFalse(self.git(sub)["ok"], sub)
			for flag in (
				"--output=/tmp/x",
				"--output",
				"--no-index",
				"--ext-diff",
				"--textconv",
				"-Ofile",
				"-O",
				"--contents",
				"--exec-path=/tmp",
				"--exec",
				"--upload-pack=x",
				"-c",
				"-ccore.pager=sh",
			):
				for sub in ("log", "blame"):
					result = self.git(sub, [flag])
					self.assertFalse(result["ok"], (sub, flag))
					self.assertTrue(result["reason"])
			self.assertFalse(self.git("log", ["--oneline", "--output=/tmp/x"])["ok"])
			self.assertFalse(self.git("log", ["-n", "1", "-c", "--", "src/a.py"])["ok"])
			run.assert_not_called()

			self.assertTrue(self.git("log", ["--stat", "-n", "3"])["ok"])
			self.assertTrue(self.git("blame", ["src/a.py"])["ok"])
			self.assertEqual(run.call_count, 2)

	def test_git_refuses_abbreviated_and_path_carrying_options(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for flag in (
				"--cont=../../outside/x",
				"--conte=../../outside/x",
				"--conten=x",
				"--content=x",
				"--ignore-revs-file=../../outside/x",
				"--ignore-rev=x",
				"-S../../outside/x",
				"--out=/tmp/x",
				"--no-ind",
				"--ext",
				"--text",
				"-pS../../outside/x",
				"-nS../../outside/x",
				"-wO../../outside/x",
				"-pw",
			):
				for sub in ("log", "blame"):
					self.assertFalse(self.git(sub, [flag, "--", "src/a.py"])["ok"], (sub, flag))
			run.assert_not_called()
			for flag in ("--oneline", "--stat", "-n3", "--max-count=5", "--author=bob", "-n"):
				self.assertTrue(self.git("log", [flag])["ok"], flag)

	def test_git_show_and_diff_refused(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for sub in ("show", "diff"):
				for args in (
					["HEAD"],
					["--stat"],
					["HEAD:src/a.py"],
					["src/a.py"],
					["--", "src/a.py"],
					None,
				):
					result = self.git(sub, args)
					self.assertFalse(result["ok"], (sub, args))
					self.assertTrue(result["reason"])
			run.assert_not_called()

	def test_git_log_refuses_patch_printing_flags(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for flag in (
				"-p",
				"-u",
				"--patch",
				"--pat",
				"--patc",
				"--patch-with-stat",
				"--patch-with-raw",
				"-U3",
				"-U",
				"--unified=3",
				"--full-diff",
				"--word-diff",
				"--word-diff=color",
				"--cc",
				"-c",
				"-m",
				"--diff-merges=first-parent",
				"--diff-merges",
				"--diff",
				"--di",
			):
				result = self.git("log", [flag])
				self.assertFalse(result["ok"], flag)
				self.assertFalse(self.git("log", [flag, "--", "src/a.py"])["ok"], flag)
			run.assert_not_called()

	def test_git_refuses_glob_pathspecs(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for bad in (
				["--", "src/*.py"],
				["--", "src/?.py"],
				["--", "src/[a].py"],
				["--", "*"],
				["src/*.py"],
				["*.json"],
				["HEAD:src/*.py"],
				[":(glob)src/**"],
				[":!src/a.py"],
			):
				self.assertFalse(self.git("log", bad)["ok"], bad)
			self.assertFalse(self.git("blame", ["src/*.py"])["ok"])
			run.assert_not_called()

	def test_git_log_checks_nonexistent_pathspec_against_forbidden_names(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			self.assertFalse(self.git("log", ["--", "old/secret.py"])["ok"])
			self.assertFalse(self.git("log", ["old/password.py"])["ok"])
			run.assert_not_called()

	def test_git_blame_takes_exactly_one_checked_file(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for bad in (
				None,
				[],
				["--porcelain"],
				["--"],
				["src/a.py", "src/a.py"],
				["--", "src/a.py", "src/a.py"],
				["HEAD", "src/a.py"],
				["HEAD:src/a.py"],
				["site_config.json"],
				["src"],
				["missing.py"],
				["../../outside/x.py"],
				["/etc/passwd"],
				["-L1,2", "src/a.py"],
			):
				self.assertFalse(self.git("blame", bad)["ok"], bad)
			run.assert_not_called()
			self.assertTrue(self.git("blame", ["src/a.py"])["ok"])
			self.assertTrue(self.git("blame", ["-w", "--line-porcelain", "--", "src/a.py"])["ok"])
			self.assertEqual(run.call_count, 2)

	def test_git_nonzero_exit_hides_stderr(self):
		with patch(RUN_PATH, return_value=completed("", "fatal: secret-path-detail", 128)):
			result = self.git("log")
		self.assertFalse(result["ok"])
		self.assertNotIn("secret-path-detail", result["reason"])

	def test_git_runs_with_closed_stdin(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			self.git("log")
		self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

	def test_git_paths_go_through_safe_path_check(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for bad in (
				["--", "site_config.json"],
				["site_config.json"],
				["HEAD:site_config.json"],
				["/etc/passwd"],
				["--", "../../outside/x.py"],
				["--", "src/../../../outside/x.py"],
			):
				result = self.git("log", bad)
				self.assertFalse(result["ok"], bad)
			run.assert_not_called()
			self.assertTrue(self.git("log", ["--", "src/a.py"])["ok"])
			self.assertTrue(self.git("blame", ["--porcelain", "--", "src/a.py"])["ok"])
			self.assertTrue(self.git("log", ["HEAD~2..HEAD"])["ok"])

	def test_git_refuses_bad_repo_and_args(self):
		with patch(RUN_PATH, return_value=completed("ok")) as run:
			for app in ("nogit", "missing", "../outside", "/etc", "", None, "myapp/src", "."):
				self.assertFalse(self.git("log", app=app)["ok"], app)
			self.assertFalse(self.git("log", ["a"] * 11)["ok"])
			self.assertFalse(self.git("log", "--oneline")["ok"])
			self.assertFalse(self.git("log", [1])["ok"])
			self.assertFalse(source.git_source(None, None)["ok"])
			run.assert_not_called()

	def test_git_missing_returns_not_installed(self):
		with patch(RUN_PATH, side_effect=FileNotFoundError("git")):
			result = self.git("log")
		self.assertEqual(result["ok"], False)
		self.assertIn("chưa cài git", result["reason"])

	def test_git_runs_with_timeout_list_args_no_shell(self):
		with patch(RUN_PATH, return_value=completed("abc commit\n")) as run:
			default = self.git("log")
			stat = self.git("log", ["--stat", "HEAD~1"])
			blame = self.git("blame", ["--", "src/a.py"])
		self.assertEqual(default, {"ok": True, "output": "abc commit\n"})
		calls = run.call_args_list
		self.assertEqual(
			calls[0].args[0],
			[
				"git",
				"--no-pager",
				"-C",
				self.repo,
				"log",
				"--no-ext-diff",
				"--no-textconv",
				"--oneline",
				"-n",
				"15",
			],
		)
		self.assertEqual(
			calls[1].args[0],
			[
				"git",
				"--no-pager",
				"-C",
				self.repo,
				"log",
				"--no-ext-diff",
				"--no-textconv",
				"--stat",
				"HEAD~1",
			],
		)
		self.assertEqual(calls[2].args[0], ["git", "--no-pager", "-C", self.repo, "blame", "--", "src/a.py"])
		self.assertTrue(stat["ok"] and blame["ok"])
		for call in calls:
			self.assertIsInstance(call.args[0], list)
			self.assertEqual(call.kwargs["timeout"], 30)
			self.assertTrue(call.kwargs["capture_output"])
			self.assertTrue(call.kwargs["text"])
			self.assertFalse(call.kwargs.get("shell", False))
			self.assertEqual(call.kwargs["env"]["GIT_PAGER"], "cat")

	def test_git_timeout_nonzero_and_unexpected_errors_are_refusals(self):
		with patch(RUN_PATH, side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
			result = self.git("log")
		self.assertFalse(result["ok"])
		self.assertIn("quá thời gian", result["reason"])

		with patch(RUN_PATH, return_value=completed("", "fatal: bad revision 'zzz'", 128)):
			result = self.git("log", ["zzz"])
		self.assertFalse(result["ok"])
		self.assertIn("128", result["reason"])
		self.assertLessEqual(len(result["reason"]), 200)

		with patch(RUN_PATH, side_effect=OSError("boom")):
			result = self.git("log")
		self.assertFalse(result["ok"])
		self.assertTrue(result["reason"])

	def test_git_output_capped(self):
		with patch(RUN_PATH, return_value=completed("x" * 9000)):
			result = self.git("log")
		self.assertTrue(result["ok"])
		self.assertEqual(len(result["output"]), 8000)


SANDBOX_APPS = ("frappe", "erpnext", "helpdesk", "hrms", "erp_ai", "custom_app")
SANDBOX_EMAIL = "erp-ai-test@sandbox.invalid"
SANDBOX_IDENTITY = f"ERP AI Test\n{SANDBOX_EMAIL}\nERP AI Test\n{SANDBOX_EMAIL}\n"
LEAKED_EMAIL = "real.person@example.com"


class TestGitSandbox(RealCoreReposUntouchedMixin, FrappeTestCase):
	def make_fake_home(self) -> str:
		"""A HOME whose `.gitconfig` sets a real-looking identity and a global commit-msg hook that adds it."""
		home = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, home, True)
		hooks = os.path.join(home, "hooks")
		os.makedirs(hooks)
		hook = os.path.join(hooks, "commit-msg")
		with open(hook, "w", encoding="utf-8") as handle:
			handle.write(f'#!/bin/sh\necho "Signed-off-by: Real Person <{LEAKED_EMAIL}>" >> "$1"\n')
		os.chmod(hook, 0o755)
		with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as handle:
			handle.write(
				f"[user]\n\tname = Real Person\n\temail = {LEAKED_EMAIL}\n[core]\n\thooksPath = {hooks}\n"
			)
		return home

	def test_git_sandbox_redirects_apps_root(self):
		real_root = os.path.realpath(os.path.join(frappe.get_app_path("frappe"), "..", ".."))
		self.assertEqual(source.get_source_root(), real_root)

		host = unittest.TestCase()
		self.addCleanup(host.doCleanups)
		sandbox = GitSandbox(host)
		self.assertEqual(source.get_source_root(), sandbox.root)
		self.assertNotEqual(sandbox.root, real_root)
		self.assertEqual(os.path.basename(sandbox.root), "apps")
		temp_dir = os.path.realpath(tempfile.gettempdir())
		self.assertEqual(os.path.commonpath([temp_dir, sandbox.root]), temp_dir)
		self.assertEqual(
			sorted(os.listdir(sandbox.root)),
			["custom_app", "erp_ai", "erp_ai-wt", "erpnext", "frappe", "helpdesk", "hrms"],
		)
		self.assertEqual(sandbox.repo("erp_ai"), os.path.join(sandbox.root, "erp_ai"))
		self.assertEqual(
			source.resolve_safe_path("erp_ai/README.md"), os.path.join(sandbox.root, "erp_ai", "README.md")
		)

		host.doCleanups()
		self.assertEqual(source.get_source_root(), real_root)
		self.assertFalse(os.path.exists(sandbox.root))

	def test_git_sandbox_repos_are_isolated_from_global_config(self):
		fake_home = self.make_fake_home()
		with patch.dict(os.environ, {"HOME": fake_home, "XDG_CONFIG_HOME": fake_home}):
			sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
			sandbox.commit_file("custom_app", "app.py", "x = 1\n")
			meta = sandbox.log_meta("custom_app")
			first = sandbox.log_meta("custom_app", rev="HEAD~1")
			env = sandbox.env()

		self.assertEqual(meta, SANDBOX_IDENTITY + "add app.py\n")
		self.assertEqual(first, SANDBOX_IDENTITY + "initial commit\n")
		self.assertNotIn(LEAKED_EMAIL, meta + first)
		self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
		self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
		self.assertEqual(env["GIT_AUTHOR_EMAIL"], SANDBOX_EMAIL)
		self.assertEqual(env["GIT_COMMITTER_EMAIL"], SANDBOX_EMAIL)

	def test_git_sandbox_ignores_inherited_git_dir(self):
		stray = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, stray, True)
		stray_git_dir = os.path.join(stray, ".git")
		with patch.dict(os.environ, {"GIT_DIR": stray_git_dir, "GIT_WORK_TREE": stray}):
			sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
			env = sandbox.env()
			count = sandbox.git("custom_app", "rev-list", "--count", "HEAD")
		self.assertEqual(count, "1\n")
		self.assertFalse(os.path.exists(stray_git_dir))
		self.assertNotIn("GIT_DIR", env)
		self.assertNotIn("GIT_WORK_TREE", env)

	def test_git_sandbox_each_repo_has_first_commit_on_main(self):
		sandbox = GitSandbox(self)
		for app in SANDBOX_APPS:
			with self.subTest(app=app):
				repo = sandbox.repo(app)
				self.assertTrue(os.path.isdir(os.path.join(repo, ".git")))
				self.assertEqual(sandbox.git(app, "rev-parse", "--show-toplevel"), repo + "\n")
				self.assertEqual(sandbox.git(app, "symbolic-ref", "HEAD"), "refs/heads/main\n")
				self.assertEqual(sandbox.git(app, "rev-list", "--count", "HEAD"), "1\n")
				self.assertEqual(sandbox.git(app, "ls-tree", "--name-only", "HEAD"), "README.md\n")
				self.assertEqual(sandbox.git(app, "status", "--porcelain"), "")

	def test_git_sandbox_erp_ai_worktree_is_real_worktree(self):
		sandbox = GitSandbox(self)
		main_repo = sandbox.repo("erp_ai")
		worktree = sandbox.repo("erp_ai-wt")
		self.assertEqual(worktree, os.path.join(sandbox.root, "erp_ai-wt"))
		dot_git = os.path.join(worktree, ".git")
		self.assertTrue(os.path.isfile(dot_git))
		admin = os.path.join(main_repo, ".git", "worktrees", "erp_ai-wt")
		with open(dot_git, encoding="utf-8") as handle:
			self.assertEqual(handle.read(), f"gitdir: {admin}\n")
		with open(os.path.join(admin, "commondir"), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), "../..\n")
		self.assertEqual(
			sandbox.git("erp_ai-wt", "rev-parse", "--path-format=absolute", "--git-common-dir"),
			os.path.join(main_repo, ".git") + "\n",
		)
		self.assertEqual(sandbox.git("erp_ai-wt", "symbolic-ref", "HEAD"), "refs/heads/erp_ai-wt\n")
		self.assertEqual(
			sandbox.git("erp_ai-wt", "rev-parse", "HEAD"), sandbox.git("erp_ai", "rev-parse", "main")
		)

	def test_git_sandbox_custom_apps_without_worktree(self):
		sandbox = GitSandbox(self, apps=("frappe", "erp_ai"), erp_ai_worktree=None)
		self.assertEqual(sorted(os.listdir(sandbox.root)), ["erp_ai", "frappe"])

	def test_git_sandbox_commit_stage_unstaged_and_refs(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		first = sandbox.git("custom_app", "rev-parse", "HEAD").strip()
		sha = sandbox.commit_file("custom_app", "pkg/mod.py", "x = 2\n")
		self.assertRegex(sha, r"^[0-9a-f]{40}$")
		self.assertNotEqual(sha, first)
		self.assertEqual(sandbox.git("custom_app", "rev-parse", "HEAD"), sha + "\n")
		self.assertEqual(sandbox.git("custom_app", "rev-parse", "HEAD~1"), first + "\n")
		self.assertEqual(sandbox.git("custom_app", "show", "HEAD:pkg/mod.py"), "x = 2\n")
		self.assertEqual(
			sandbox.git("custom_app", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"),
			"pkg/mod.py\n",
		)
		self.assertEqual(sandbox.refs("custom_app"), {"refs/heads/main": sha})

		sandbox.stage("custom_app", "staged.py", "s = 1\n")
		sandbox.write_unstaged("custom_app", "pkg/mod.py", "x = 3\n")
		self.assertEqual(sandbox.git("custom_app", "status", "--porcelain"), " M pkg/mod.py\nA  staged.py\n")
		self.assertEqual(sandbox.git("custom_app", "show", ":staged.py"), "s = 1\n")
		with open(os.path.join(sandbox.repo("custom_app"), "pkg", "mod.py"), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), "x = 3\n")
		self.assertEqual(sandbox.refs("custom_app"), {"refs/heads/main": sha})

	def test_git_sandbox_refuses_git_outside_its_temp_dir(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		for app in ("..", "../..", "/tmp", "custom_app/../../.."):
			with self.subTest(app=app):
				with self.assertRaises(ValueError):
					sandbox.git(app, "status")

	def test_git_sandbox_refuses_root_and_missing_repo(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		for app in ("", ".", "custom_app/.."):
			with self.subTest(app=app):
				with self.assertRaisesRegex(ValueError, "outside"):
					sandbox.git(app, "status")
		with self.assertRaisesRegex(ValueError, "no repo missing_app"):
			sandbox.git("missing_app", "status")
		self.assertFalse(os.path.exists(sandbox.repo("missing_app")))

	def test_git_sandbox_never_searches_above_its_apps_root(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		self.assertEqual(sandbox.env()["GIT_CEILING_DIRECTORIES"], sandbox.root)
		shutil.copytree(os.path.join(sandbox.repo("custom_app"), ".git"), os.path.join(sandbox.root, ".git"))
		os.makedirs(sandbox.repo("plain"))
		with self.assertRaisesRegex(AssertionError, "not a git repository"):
			sandbox.git("plain", "rev-parse", "--show-toplevel")

	def test_git_sandbox_write_keeps_path_inside_repo(self):
		sandbox = GitSandbox(self, apps=("custom_app", "frappe"), erp_ai_worktree=None)
		escape = os.path.join(sandbox.root, "escape.py")
		cases = {
			"commit_file": lambda rel: sandbox.commit_file("custom_app", rel, "x = 1\n"),
			"stage": lambda rel: sandbox.stage("custom_app", rel, "x = 1\n"),
			"write_unstaged": lambda rel: sandbox.write_unstaged("custom_app", rel, "x = 1\n"),
		}
		for name, call in cases.items():
			for rel in ("../escape.py", escape, "../frappe/README.md", "", "."):
				with self.subTest(helper=name, rel=rel):
					with self.assertRaisesRegex(ValueError, "outside"):
						call(rel)
		self.assertFalse(os.path.exists(escape))
		with open(os.path.join(sandbox.repo("frappe"), "README.md"), encoding="utf-8") as handle:
			self.assertEqual(handle.read(), "# frappe\n")
		self.assertEqual(sandbox.git("custom_app", "status", "--porcelain"), "")

	def test_git_sandbox_write_refuses_app_outside_root(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		outside = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, outside, True)
		base_entries = sorted(os.listdir(sandbox.base))
		cases = {
			"commit_file": lambda app: sandbox.commit_file(app, "escape.py", "x = 1\n"),
			"stage": lambda app: sandbox.stage(app, "escape.py", "x = 1\n"),
			"write_unstaged": lambda app: sandbox.write_unstaged(app, "escape.py", "x = 1\n"),
		}
		for name, call in cases.items():
			for app in (outside, "..", "", "custom_app/.."):
				with self.subTest(helper=name, app=app):
					with self.assertRaisesRegex(ValueError, "outside"):
						call(app)
			with self.subTest(helper=name, app="missing_app"):
				with self.assertRaisesRegex(ValueError, "no repo missing_app"):
					call("missing_app")
		self.assertEqual(os.listdir(outside), [])
		self.assertEqual(sorted(os.listdir(sandbox.base)), base_entries)
		self.assertFalse(os.path.exists(os.path.join(sandbox.root, "escape.py")))
		self.assertFalse(os.path.exists(sandbox.repo("missing_app")))

	def test_sandbox_state_helpers_produce_expected_git_state(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		app = "custom_app"
		first = sandbox.git(app, "rev-parse", "HEAD").strip()
		git_dir = os.path.join(sandbox.repo(app), ".git")

		with self.subTest(helper="add_remote"):
			sandbox.add_remote(app)
			self.assertEqual(sandbox.git(app, "rev-list", "--count", "@{u}..HEAD"), "2\n")
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "@{u}"), "origin/main\n")
			self.assertEqual(sandbox.git(app, "rev-parse", "@{u}"), first + "\n")
			self.assertEqual(
				sandbox.git(app, "config", "--get", "remote.origin.url"), "https://x-token-FAKE@host/r.git\n"
			)
			bare = sandbox.remote_dir(app)
			self.assertEqual(os.path.commonpath([sandbox.base, bare]), sandbox.base)
			self.assertNotEqual(os.path.commonpath([sandbox.root, bare]), sandbox.root)
			self.assertEqual(sandbox.git(app, "ls-remote", "--heads", bare), f"{first}\trefs/heads/main\n")
			with open(os.path.join(git_dir, "config"), encoding="utf-8") as handle:
				config = handle.read()
			self.assertNotIn(bare, config)
			self.assertEqual(
				sandbox.git(app, "log", "--format=%s", "@{u}..HEAD"), "ahead commit 2\nahead commit 1\n"
			)

		with self.subTest(helper="switch_branch"):
			head = sandbox.git(app, "rev-parse", "HEAD")
			sandbox.switch_branch(app, "feature")
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "HEAD"), "feature\n")
			self.assertEqual(sandbox.git(app, "rev-parse", "HEAD"), head)
			sandbox.switch_branch(app, "main", create=False)
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "HEAD"), "main\n")

		with self.subTest(helper="detach"):
			head = sandbox.git(app, "rev-parse", "HEAD")
			sandbox.detach(app)
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "HEAD"), "HEAD\n")
			self.assertEqual(sandbox.git(app, "rev-parse", "HEAD"), head)
			sandbox.switch_branch(app, "main", create=False)

		head = sandbox.git(app, "rev-parse", "HEAD")
		for kind in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
			with self.subTest(helper="mark_in_progress", kind=kind):
				sandbox.mark_in_progress(app, kind)
				with open(os.path.join(git_dir, kind), encoding="utf-8") as handle:
					self.assertEqual(handle.read(), head)
		with self.subTest(helper="mark_in_progress", kind="rebase-merge"):
			sandbox.mark_in_progress(app, "rebase-merge")
			rebase = os.path.join(git_dir, "rebase-merge")
			self.assertTrue(os.path.isdir(rebase))
			with open(os.path.join(rebase, "head-name"), encoding="utf-8") as handle:
				self.assertEqual(handle.read(), "refs/heads/main\n")
			with open(os.path.join(rebase, "onto"), encoding="utf-8") as handle:
				self.assertEqual(handle.read(), head)

		with self.subTest(helper="hold_index_lock"):
			sandbox.hold_index_lock(app)
			self.assertTrue(os.path.isfile(os.path.join(git_dir, "index.lock")))
			with self.assertRaisesRegex(AssertionError, "index.lock"):
				sandbox.stage(app, "blocked.py", "x = 1\n")

	def test_mark_in_progress_is_seen_by_git_status(self):
		expected = {
			"MERGE_HEAD": "All conflicts fixed but you are still merging.",
			"rebase-merge": "You are currently rebasing branch 'main'",
			"CHERRY_PICK_HEAD": "You are currently cherry-picking commit",
			"REVERT_HEAD": "You are currently reverting commit",
		}
		for kind, line in expected.items():
			with self.subTest(kind=kind):
				sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
				self.assertNotIn(line, sandbox.git("custom_app", "status"))
				sandbox.mark_in_progress("custom_app", kind)
				self.assertIn(line, sandbox.git("custom_app", "status"))

	def test_state_helpers_on_worktree_use_its_own_git_dir(self):
		sandbox = GitSandbox(self, apps=("erp_ai",))
		admin = os.path.join(sandbox.repo("erp_ai"), ".git", "worktrees", "erp_ai-wt")
		sandbox.mark_in_progress("erp_ai-wt", "MERGE_HEAD")
		sandbox.hold_index_lock("erp_ai-wt")
		self.assertTrue(os.path.isfile(os.path.join(admin, "MERGE_HEAD")))
		self.assertTrue(os.path.isfile(os.path.join(admin, "index.lock")))
		self.assertFalse(os.path.exists(os.path.join(sandbox.repo("erp_ai"), ".git", "MERGE_HEAD")))

	def test_state_helpers_error_branches(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		app = "custom_app"
		with self.subTest(case="unknown kind"):
			with self.assertRaisesRegex(ValueError, "unknown in-progress kind: 'bisect'"):
				sandbox.mark_in_progress(app, "bisect")
		with self.subTest(case="negative ahead"):
			with self.assertRaisesRegex(ValueError, "ahead must be >= 0"):
				sandbox.add_remote(app, ahead=-1)
			self.assertEqual(sandbox.git(app, "remote"), "")
		with self.subTest(case="ahead zero"):
			sandbox.add_remote(app, name="mirror", ahead=0)
			self.assertEqual(sandbox.git(app, "rev-list", "--count", "@{u}..HEAD"), "0\n")
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "@{u}"), "mirror/main\n")
		with self.subTest(case="duplicate remote"):
			with self.assertRaisesRegex(AssertionError, "already exists"):
				sandbox.add_remote(app, name="mirror")
		outside = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, outside, True)
		remotes = os.path.join(sandbox.base, "remotes")
		climb = os.path.relpath(os.path.join(outside, "r"), os.path.join(remotes, app))
		for name in (os.path.join(outside, "r"), climb, "..", "a/b", ""):
			with self.subTest(case="remote name escapes", name=name):
				with self.assertRaisesRegex(ValueError, "remote name"):
					sandbox.add_remote(app, name=name)
		self.assertEqual(os.listdir(outside), [])
		self.assertEqual(sorted(os.listdir(os.path.join(remotes, app))), ["mirror.git"])
		self.assertEqual(sandbox.git(app, "remote"), "mirror\n")
		with self.subTest(case="switch to missing branch"):
			with self.assertRaisesRegex(AssertionError, "nope"):
				sandbox.switch_branch(app, "nope", create=False)
			self.assertEqual(sandbox.git(app, "rev-parse", "--abbrev-ref", "HEAD"), "main\n")
		with self.subTest(case="create existing branch"):
			with self.assertRaisesRegex(AssertionError, "already exists"):
				sandbox.switch_branch(app, "main")
		with self.subTest(case="add_remote on detached HEAD"):
			sandbox.detach(app)
			with self.assertRaisesRegex(AssertionError, "symbolic-ref"):
				sandbox.add_remote(app, name="other")
		for helper in ("add_remote", "switch_branch", "detach", "mark_in_progress", "hold_index_lock"):
			with self.subTest(case="app without repo", helper=helper):
				args = {"switch_branch": ("x",), "mark_in_progress": ("MERGE_HEAD",)}.get(helper, ())
				with self.assertRaisesRegex(ValueError, "no repo missing_app"):
					getattr(sandbox, helper)("missing_app", *args)
		with self.assertRaisesRegex(ValueError, "no repo missing_app"):
			sandbox.install_marker_hooks("missing_app")

	def test_mark_in_progress_rebase_merge_twice_keeps_state(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		sandbox.mark_in_progress("custom_app", "rebase-merge")
		sandbox.mark_in_progress("custom_app", "rebase-merge")
		self.assertIn("You are currently rebasing branch 'main'", sandbox.git("custom_app", "status"))

	def test_install_marker_hooks_refuses_second_install_on_shared_hooks_dir(self):
		sandbox = GitSandbox(self, apps=("erp_ai",))
		markers = sandbox.install_marker_hooks("erp_ai")
		for app in ("erp_ai", "erp_ai-wt"):
			with self.subTest(app=app):
				with self.assertRaisesRegex(ValueError, "marker hooks already installed"):
					sandbox.install_marker_hooks(app)
		self.assertFalse(os.path.exists(os.path.join(sandbox.base, "markers", "erp_ai-wt")))
		with open(
			os.path.join(sandbox.repo("erp_ai"), ".git", "hooks", "pre-commit"), encoding="utf-8"
		) as handle:
			self.assertIn(f'"{markers}/pre-commit"', handle.read())

	def test_marker_hooks_see_commit_msg_once_pre_commit_passes(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		markers = sandbox.install_marker_hooks("custom_app")
		os.remove(os.path.join(sandbox.repo("custom_app"), ".git", "hooks", "pre-commit"))
		sandbox.commit_file("custom_app", "loud.py", "x = 1\n", run_hooks=True)
		self.assertEqual(
			sorted(os.listdir(markers)),
			["commit-msg", "post-commit", "post-index-change", "prepare-commit-msg", "reference-transaction"],
		)

	def test_install_marker_hooks_records_hooks_only_when_asked(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		app = "custom_app"
		markers = sandbox.install_marker_hooks(app)
		self.assertEqual(os.path.commonpath([sandbox.base, markers]), sandbox.base)
		self.assertEqual(os.listdir(markers), [])
		hooks_dir = os.path.join(sandbox.repo(app), ".git", "hooks")
		for hook in test_utils.MARKER_HOOKS:
			with self.subTest(hook=hook):
				self.assertTrue(os.access(os.path.join(hooks_dir, hook), os.X_OK))
		self.assertEqual(
			test_utils.MARKER_HOOKS,
			(
				"pre-commit",
				"prepare-commit-msg",
				"commit-msg",
				"post-commit",
				"post-index-change",
				"reference-transaction",
			),
		)

		sandbox.commit_file(app, "quiet.py", "x = 1\n")
		sandbox.switch_branch(app, "side")
		sandbox.add_remote(app)
		self.assertEqual(os.listdir(markers), [])

		sandbox.write_unstaged(app, "loud.py", "x = 2\n")
		with self.assertRaisesRegex(AssertionError, "git commit"):
			sandbox.git(app, "add", "--", "loud.py", run_hooks=True)
			sandbox.git(app, "commit", "--quiet", "-m", "loud", "--", "loud.py", run_hooks=True)
		self.assertEqual(sorted(os.listdir(markers)), ["post-index-change", "pre-commit"])
		self.assertEqual(sandbox.git(app, "log", "-1", "--format=%s"), "ahead commit 2\n")

		sandbox.git(app, "commit", "--quiet", "--no-verify", "-m", "loud", "--", "loud.py", run_hooks=True)
		self.assertEqual(
			sorted(os.listdir(markers)),
			["post-commit", "post-index-change", "pre-commit", "prepare-commit-msg", "reference-transaction"],
		)

	def test_commit_file_runs_marker_hooks_when_asked(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		markers = sandbox.install_marker_hooks("custom_app")
		with self.assertRaisesRegex(AssertionError, "git commit"):
			sandbox.commit_file("custom_app", "loud.py", "x = 1\n", run_hooks=True)
		self.assertIn("pre-commit", os.listdir(markers))


class TestRealCoreReposUntouchedMixin(unittest.TestCase):
	def make_probe(self):
		return type("Probe", (RealCoreReposUntouchedMixin, unittest.TestCase), {"runTest": lambda self: None})

	def test_real_core_repos_snapshot_reads_the_four_core_repos(self):
		snapshot = test_utils.real_core_repos_snapshot()
		self.assertEqual(sorted(snapshot), ["erpnext", "frappe", "helpdesk", "hrms"])
		for app, (head, _status) in snapshot.items():
			with self.subTest(app=app):
				self.assertRegex(head, r"^[0-9a-f]{40}$")
		self.assertEqual(test_utils.real_core_repos_snapshot(), snapshot)

	def test_real_core_repos_snapshot_runs_only_read_commands(self):
		calls = []

		def fake_run(args, **kwargs):
			calls.append((args, kwargs))
			return subprocess.CompletedProcess(args, 0, stdout="abc\n", stderr="")

		with patch("erp_ai.test_utils.subprocess.run", side_effect=fake_run):
			snapshot = test_utils.real_core_repos_snapshot()
		apps_dir = os.path.join(frappe.utils.get_bench_path(), "apps")
		expected = []
		for app in ("frappe", "erpnext", "helpdesk", "hrms"):
			repo = os.path.join(apps_dir, app)
			expected.append(["git", "-C", repo, "--no-optional-locks", "rev-parse", "HEAD"])
			expected.append(["git", "-C", repo, "--no-optional-locks", "status", "--porcelain"])
		self.assertEqual([args for args, _ in calls], expected)
		for _, kwargs in calls:
			self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
			self.assertEqual(kwargs["timeout"], test_utils.GIT_SANDBOX_TIMEOUT_S)
			self.assertNotIn("GIT_DIR", kwargs["env"])
		self.assertEqual(snapshot["hrms"], ("abc", "abc\n"))

	def test_real_core_repos_snapshot_fails_on_git_error(self):
		failed = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal: not a git repository")
		with patch("erp_ai.test_utils.subprocess.run", return_value=failed):
			with self.assertRaisesRegex(AssertionError, "not a git repository"):
				test_utils.real_core_repos_snapshot()

	def test_real_core_repos_mixin_detects_change(self):
		probe = self.make_probe()
		clean = {app: ("a" * 40, "") for app in ("frappe", "erpnext", "helpdesk", "hrms")}
		marked = dict(clean, hrms=("a" * 40, "?? erp_ai_marker.txt\n"))
		moved = dict(clean, frappe=("b" * 40, ""))
		with patch("erp_ai.test_utils.real_core_repos_snapshot", side_effect=[clean, marked]):
			probe.setUpClass()
			with self.assertRaisesRegex(AssertionError, r"hrms.*erp_ai_marker\.txt"):
				probe.tearDownClass()
		with patch("erp_ai.test_utils.real_core_repos_snapshot", side_effect=[clean, moved]):
			probe.setUpClass()
			with self.assertRaisesRegex(AssertionError, "frappe"):
				probe.tearDownClass()
		with patch("erp_ai.test_utils.real_core_repos_snapshot", side_effect=[clean, dict(clean)]):
			probe.setUpClass()
			probe.tearDownClass()

	def test_real_core_repos_mixin_on_real_repos_passes_when_untouched(self):
		probe = self.make_probe()
		probe.setUpClass()
		self.assertEqual(sorted(probe._real_core_repos_before), ["erpnext", "frappe", "helpdesk", "hrms"])
		probe.tearDownClass()


EXPECTED_HOOKS_DIR = os.path.realpath(
	os.path.join(os.path.dirname(os.path.abspath(source.__file__)), "..", "git_no_hooks")
)
EXPECTED_READ_SUBCOMMANDS = {
	"rev-parse",
	"rev-list",
	"status",
	"check-ignore",
	"ls-files",
	"merge-base",
	"diff-tree",
	"cat-file",
}
FORBIDDEN_GIT_SUBCOMMANDS = (
	"push",
	"fetch",
	"pull",
	"clone",
	"checkout",
	"switch",
	"restore",
	"branch",
	"reset",
	"rebase",
	"merge",
	"cherry-pick",
	"revert",
	"am",
	"apply",
	"stash",
	"clean",
	"tag",
	"remote",
	"config",
	"update-ref",
	"symbolic-ref",
	"reflog",
	"gc",
	"maintenance",
	"worktree",
	"notes",
	"replace",
	"filter-branch",
	"prune",
)
RUN_PATH = "erp_ai.agent.tools.source.subprocess.run"


class TestGitReadOptions(unittest.TestCase):
	"""ADR-022 QĐ 2, 4; NFR-8; D-13: the one definition of git options, env and the read runner."""

	def test_git_global_options_contents(self):
		self.assertEqual(source.GIT_HOOKS_DIR, EXPECTED_HOOKS_DIR)
		self.assertTrue(EXPECTED_HOOKS_DIR.endswith(os.path.join("erp_ai", "agent", "git_no_hooks")))
		write = [
			"--no-pager",
			"-c",
			f"core.hooksPath={EXPECTED_HOOKS_DIR}",
			"-c",
			"core.fsmonitor=false",
			"-c",
			"maintenance.auto=false",
			"-c",
			"gc.auto=0",
		]
		self.assertEqual(source.git_global_options(read=False), write)
		self.assertEqual(source.git_global_options(read=True), [*write, "--no-optional-locks"])
		self.assertIsNot(source.git_global_options(read=True), source.git_global_options(read=True))

	def test_git_read_constants(self):
		self.assertEqual(source.GIT_READ_SUBCOMMANDS, EXPECTED_READ_SUBCOMMANDS)
		self.assertIsInstance(source.GIT_READ_SUBCOMMANDS, frozenset)
		self.assertEqual(source.TIMEOUT_EXECUTABLE, "timeout")
		self.assertEqual(source.BENCH_EXECUTABLE, "bench")
		self.assertEqual(source.GIT_BACKSTOP_EXTRA_S, 5)
		self.assertEqual(source.GIT_TIMEOUT_S, 30)
		self.assertEqual(source.GIT_SUBCOMMANDS, {"log", "blame"})

	def test_git_env_has_no_home_and_ignores_global_config(self):
		leaky = {
			"PATH": "/opt/x/bin:/usr/bin",
			"HOME": "/home/someone",
			"XDG_CONFIG_HOME": "/home/someone/.config",
			"GIT_DIR": "/elsewhere/.git",
			"GIT_CONFIG_PARAMETERS": "'user.email'='real.person@example.com'",
			"OPENAI_API_KEY": "sk-fake",
		}
		base = {
			"PATH": "/opt/x/bin:/usr/bin",
			"LC_ALL": "C",
			"GIT_CONFIG_GLOBAL": "/dev/null",
			"GIT_CONFIG_NOSYSTEM": "1",
			"GIT_TERMINAL_PROMPT": "0",
		}
		with patch.dict(os.environ, leaky):
			self.assertEqual(source.git_env(identity=False), base)
			self.assertEqual(
				source.git_env(identity=True),
				{
					**base,
					"GIT_AUTHOR_NAME": "ERP AI Agent",
					"GIT_COMMITTER_NAME": "ERP AI Agent",
					"GIT_AUTHOR_EMAIL": "erp-ai-agent@bot.invalid",
					"GIT_COMMITTER_EMAIL": "erp-ai-agent@bot.invalid",
				},
			)

	def test_git_env_path_defaults_when_worker_has_none(self):
		with patch.dict(os.environ, {}, clear=True):
			self.assertEqual(source.git_env(identity=False)["PATH"], "/usr/bin:/bin")
		with patch.dict(os.environ, {"PATH": ""}, clear=True):
			self.assertEqual(source.git_env(identity=False)["PATH"], "/usr/bin:/bin")

	def test_hooks_dir_has_no_hook_files(self):
		self.assertTrue(os.path.isdir(source.GIT_HOOKS_DIR))
		self.assertEqual(os.listdir(source.GIT_HOOKS_DIR), ["README.md"])
		readme = os.path.join(source.GIT_HOOKS_DIR, "README.md")
		self.assertFalse(os.access(readme, os.X_OK))
		with open(readme, encoding="utf-8") as handle:
			text = handle.read()
		self.assertIn("core.hooksPath", text)
		self.assertIn("README.md", text)

		host = unittest.TestCase()
		self.addCleanup(host.doCleanups)
		sandbox = GitSandbox(host, apps=("custom_app",), erp_ai_worktree=None)
		for temp_root in (sandbox.base, os.path.realpath(tempfile.gettempdir())):
			with self.subTest(temp_root=temp_root):
				self.assertNotEqual(os.path.commonpath([temp_root, source.GIT_HOOKS_DIR]), temp_root)

	def test_run_git_read_rejects_unlisted_subcommand(self):
		repo = os.path.realpath(tempfile.gettempdir())
		outsiders = (
			*FORBIDDEN_GIT_SUBCOMMANDS,
			"log",
			"blame",
			"show",
			"diff",
			"grep",
			"hash-object",
			"commit",
			"add",
			"rm",
			"init",
			"REV-PARSE",
			" status",
			"status ",
			"--version",
			"-c",
			"",
			None,
			1,
			b"status",
		)
		with patch(RUN_PATH) as run:
			for subcommand in outsiders:
				with self.subTest(subcommand=subcommand):
					with self.assertRaisesRegex(ValueError, "subcommand"):
						source.run_git_read(repo, subcommand)
		run.assert_not_called()

	def test_run_git_read_rejects_bad_repo_root(self):
		missing = os.path.join(os.path.realpath(tempfile.gettempdir()), "erp-ai-no-such-dir-T37")
		a_file = tempfile.NamedTemporaryFile(delete=False)
		a_file.close()
		self.addCleanup(os.remove, a_file.name)
		with patch(RUN_PATH) as run:
			for repo_root in ("", "relative/dir", missing, a_file.name, "/tmp\0x", None, 3):
				with self.subTest(repo_root=repo_root):
					with self.assertRaisesRegex(ValueError, "repo_root"):
						source.run_git_read(repo_root, "status")
		run.assert_not_called()

	def test_run_git_read_rejects_bad_args(self):
		repo = os.path.realpath(tempfile.gettempdir())
		with patch(RUN_PATH) as run:
			for args in (("HEAD\0",), (None,), (1,), (b"HEAD",), ("HEAD", ["x"])):
				with self.subTest(args=args):
					with self.assertRaisesRegex(ValueError, "argument"):
						source.run_git_read(repo, "rev-parse", *args)
		run.assert_not_called()

	def test_run_git_read_rejects_bad_limit(self):
		repo = os.path.realpath(tempfile.gettempdir())
		with patch(RUN_PATH) as run:
			for limit_s in (0, -1, 31, True, 1.5, "5", None):
				with self.subTest(limit_s=limit_s):
					with self.assertRaisesRegex(ValueError, "limit_s"):
						source.run_git_read(repo, "status", limit_s=limit_s)
		run.assert_not_called()

	def test_run_git_read_argv_and_process_options(self):
		repo = os.path.realpath(tempfile.gettempdir())
		done = subprocess.CompletedProcess([], 0, stdout=b"out\n")
		with patch.dict(os.environ, {"PATH": "/usr/bin:/bin", "HOME": "/home/someone"}):
			with patch(RUN_PATH, return_value=done) as run:
				result = source.run_git_read(repo, "rev-parse", "--verify", "-q", "HEAD", limit_s=7)
		self.assertEqual(result, source.GitRun(exit_code=0, stdout=b"out\n", timed_out=False))
		run.assert_called_once()
		args, kwargs = run.call_args
		self.assertEqual(
			args,
			(
				[
					"timeout",
					"-s",
					"KILL",
					"7",
					"git",
					"--no-pager",
					"-c",
					f"core.hooksPath={EXPECTED_HOOKS_DIR}",
					"-c",
					"core.fsmonitor=false",
					"-c",
					"maintenance.auto=false",
					"-c",
					"gc.auto=0",
					"--no-optional-locks",
					"rev-parse",
					"--verify",
					"-q",
					"HEAD",
				],
			),
		)
		self.assertEqual(
			kwargs,
			{
				"cwd": repo,
				"env": {
					"PATH": "/usr/bin:/bin",
					"LC_ALL": "C",
					"GIT_CONFIG_GLOBAL": "/dev/null",
					"GIT_CONFIG_NOSYSTEM": "1",
					"GIT_TERMINAL_PROMPT": "0",
				},
				"stdin": subprocess.DEVNULL,
				"stdout": subprocess.PIPE,
				"stderr": subprocess.DEVNULL,
				"timeout": 12,
				"start_new_session": True,
			},
		)

	def test_run_git_read_default_limit_is_git_timeout(self):
		repo = os.path.realpath(tempfile.gettempdir())
		done = subprocess.CompletedProcess([], 0, stdout=b"")
		with patch(RUN_PATH, return_value=done) as run:
			source.run_git_read(repo, "status")
		args, kwargs = run.call_args
		self.assertEqual(args[0][:5], ["timeout", "-s", "KILL", "30", "git"])
		self.assertEqual(kwargs["timeout"], 35)

	def test_run_git_read_backstop_timeout_is_timed_out(self):
		repo = os.path.realpath(tempfile.gettempdir())
		expired = subprocess.TimeoutExpired(["timeout"], 35)
		with patch(RUN_PATH, side_effect=expired):
			self.assertEqual(
				source.run_git_read(repo, "status"),
				source.GitRun(exit_code=None, stdout=b"", timed_out=True),
			)

	def test_run_git_read_killed_by_timeout_is_timed_out(self):
		repo = os.path.realpath(tempfile.gettempdir())
		for code in (-9, 124, 137):
			with self.subTest(code=code):
				done = subprocess.CompletedProcess([], code, stdout=b"part")
				with patch(RUN_PATH, return_value=done):
					with patch("erp_ai.agent.tools.source.time.monotonic", side_effect=[100.0, 107.0]):
						self.assertEqual(
							source.run_git_read(repo, "status", limit_s=7),
							source.GitRun(exit_code=code, stdout=b"part", timed_out=True),
						)

	def test_run_git_read_kill_codes_before_limit_are_not_timed_out(self):
		repo = os.path.realpath(tempfile.gettempdir())
		for code in (-9, 124, 137):
			with self.subTest(code=code):
				done = subprocess.CompletedProcess([], code, stdout=b"")
				with patch(RUN_PATH, return_value=done):
					with patch("erp_ai.agent.tools.source.time.monotonic", side_effect=[100.0, 101.0]):
						self.assertEqual(
							source.run_git_read(repo, "status", limit_s=7),
							source.GitRun(exit_code=code, stdout=b"", timed_out=False),
						)

	def test_run_git_read_normal_exit_after_limit_is_not_timed_out(self):
		repo = os.path.realpath(tempfile.gettempdir())
		for code in (0, 1, 128):
			with self.subTest(code=code):
				done = subprocess.CompletedProcess([], code, stdout=b"late")
				with patch(RUN_PATH, return_value=done):
					with patch("erp_ai.agent.tools.source.time.monotonic", side_effect=[100.0, 107.0]):
						self.assertEqual(
							source.run_git_read(repo, "status", limit_s=7),
							source.GitRun(exit_code=code, stdout=b"late", timed_out=False),
						)

	def test_run_git_read_refuses_output_file_options(self):
		# ADR-022 QĐ 2: no argument may make a read subcommand write; diff options take
		# `--output=<file>`, `--output <file>` and unambiguous long-option abbreviations.
		repo = os.path.realpath(tempfile.gettempdir())
		with patch(RUN_PATH) as run:
			for args in (
				("-p", "--output=/tmp/x", "HEAD"),
				("-p", "--output", "/tmp/x", "HEAD"),
				("-p", "--outp=/tmp/x", "HEAD"),
				("-p", "--ou", "/tmp/x", "HEAD"),
			):
				for subcommand in ("diff-tree", "rev-list"):
					with self.subTest(subcommand=subcommand, args=args):
						with self.assertRaisesRegex(ValueError, "argument"):
							source.run_git_read(repo, subcommand, *args)
		run.assert_not_called()

	def test_run_git_read_keeps_other_options_and_end_of_options(self):
		repo = os.path.realpath(tempfile.gettempdir())
		done = subprocess.CompletedProcess([], 0, stdout=b"")
		for args in (("--oneline", "HEAD"), ("--name-only", "-r", "HEAD", "--"), ("--objects", "HEAD")):
			with self.subTest(args=args):
				with patch(RUN_PATH, return_value=done) as run:
					source.run_git_read(repo, "rev-list", *args)
				self.assertEqual(run.call_args.args[0][-len(args) :], list(args))

	def test_run_git_read_missing_executable_is_unknown_exit(self):
		repo = os.path.realpath(tempfile.gettempdir())
		with patch(RUN_PATH, side_effect=FileNotFoundError("timeout")):
			with patch.object(source.logger, "warning") as warning:
				self.assertEqual(
					source.run_git_read(repo, "status"),
					source.GitRun(exit_code=None, stdout=b"", timed_out=False),
				)
		warning.assert_called_once()

	def test_git_run_is_frozen(self):
		result = source.GitRun(exit_code=0, stdout=b"", timed_out=False)
		with self.assertRaises(AttributeError):
			result.exit_code = 1


class TestRunGitReadInSandbox(RealCoreReposUntouchedMixin, unittest.TestCase):
	"""run_git_read against GitSandbox repos only (NFR-9)."""

	def make_fake_home(self) -> str:
		"""A HOME whose `.gitconfig` hides untracked files and points hooks at its own directory."""
		home = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, home, True)
		with open(os.path.join(home, ".gitconfig"), "w", encoding="utf-8") as handle:
			handle.write(
				f"[status]\n\tshowUntrackedFiles = no\n[core]\n\thooksPath = {home}/hooks\n"
				f"[user]\n\temail = {LEAKED_EMAIL}\n"
			)
		return home

	def test_run_git_read_ignores_home_global_config_and_inherited_git_dir(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		repo = sandbox.repo("custom_app")
		sandbox._write("custom_app", "new.txt", "x\n")
		fake_home = self.make_fake_home()
		stray = os.path.realpath(tempfile.mkdtemp())
		self.addCleanup(shutil.rmtree, stray, True)
		inherited = {
			"HOME": fake_home,
			"XDG_CONFIG_HOME": fake_home,
			"GIT_DIR": os.path.join(stray, ".git"),
			"GIT_WORK_TREE": stray,
		}
		with patch.dict(os.environ, inherited):
			status = source.run_git_read(repo, "status", "--porcelain=v1")
			hooks = source.run_git_read(repo, "rev-parse", "--git-path", "hooks")
			top = source.run_git_read(repo, "rev-parse", "--show-toplevel")

		self.assertEqual(status, source.GitRun(exit_code=0, stdout=b"?? new.txt\n", timed_out=False))
		self.assertEqual(
			hooks, source.GitRun(exit_code=0, stdout=f"{EXPECTED_HOOKS_DIR}\n".encode(), timed_out=False)
		)
		self.assertEqual(top, source.GitRun(exit_code=0, stdout=f"{repo}\n".encode(), timed_out=False))
		self.assertFalse(os.path.exists(os.path.join(stray, ".git")))

	def test_run_git_read_nonzero_exit_is_returned_not_raised(self):
		sandbox = GitSandbox(self, apps=("custom_app",), erp_ai_worktree=None)
		result = source.run_git_read(sandbox.repo("custom_app"), "rev-parse", "--verify", "-q", "no-such-ref")
		self.assertEqual(result, source.GitRun(exit_code=1, stdout=b"", timed_out=False))
