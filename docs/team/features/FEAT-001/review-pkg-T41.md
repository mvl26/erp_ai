# Review package T41 (FEAT-001)

Diff command: `git diff -M cc29060..team/FEAT-001-task-41` (BASE=cc29060, head 40ee67f)

Commits:
- 40ee67f test(architecture): rename agent test runner so Frappe collects it, forbid Frappe-skipped test names (FEAT-001)

Stat:
```
 .../agent/{test_runner.py => test_agent_runner.py} |  0
 erp_ai/tests/test_architecture.py                  | 43 ++++++++++++++++++++++
 2 files changed, 43 insertions(+)
```

Diff:
```diff
diff --git a/erp_ai/agent/test_runner.py b/erp_ai/agent/test_agent_runner.py
similarity index 100%
rename from erp_ai/agent/test_runner.py
rename to erp_ai/agent/test_agent_runner.py
diff --git a/erp_ai/tests/test_architecture.py b/erp_ai/tests/test_architecture.py
@@ -109,6 +109,9 @@ CI_REQUIRED_APPS = (
+# frappe/test_runner.py:160 skips any file with this name when running `run-tests --app`
+FRAPPE_SKIPPED_TEST_FILENAMES = ("test_runner.py",)
@@ def check_no_legacy_ticket_comment
+def check_no_frappe_skipped_test_files(rel_paths) -> list:
+	"""D-34: no file, at any depth, is named like a file Frappe skips when collecting tests."""
+	return [
+		f"{rel}: file name {Path(rel).name} is skipped by Frappe's test runner, rename it"
+		for rel in rel_paths
+		if Path(rel).name in FRAPPE_SKIPPED_TEST_FILENAMES
+	]
@@ class TestArchitecture
+	def test_no_test_file_named_like_frappe_skips(self):
+		rel_paths = [
+			path.relative_to(PACKAGE_ROOT).as_posix()
+			for path in sorted(PACKAGE_ROOT.rglob("*.py"))
+			if "__pycache__" not in path.parts
+		]
+		self.assertGreater(len(rel_paths), 0)
+		self.assertEqual(check_no_frappe_skipped_test_files(rel_paths), [])
+		self.assertIn("agent/test_agent_runner.py", rel_paths)
@@ class TestScannersCatchViolations
+	def test_frappe_skipped_test_name_check_catches_any_depth(self):
+		violating = ["agent/test_runner.py", "tests/test_runner.py",
+			"erp_ai_agent/doctype/x/test_runner.py", "test_runner.py"]
+		clean = ["agent/test_agent_runner.py", "tests/test_runner_utils.py",
+			"agent/runner.py", "agent/my_test_runner.py"]
+		violations = check_no_frappe_skipped_test_files(violating)
+		self.assertEqual(len(violations), len(violating))
+		for rel in violating:
+			self.assertCaught(violations, rel)
+		self.assertEqual(check_no_frappe_skipped_test_files(clean), [])
```
(The full diff is the output of the diff command above; this file abridges only whitespace/context.)
