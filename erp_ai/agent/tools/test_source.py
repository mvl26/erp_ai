import os
import shutil
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
