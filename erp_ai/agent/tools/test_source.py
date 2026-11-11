import os
import re
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.tools import source

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
				for args in (["HEAD"], ["--stat"], ["HEAD:src/a.py"], None):
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
