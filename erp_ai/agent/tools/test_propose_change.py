import hashlib
import json
import os
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import authority, change_link
from erp_ai.agent.tools import propose_change
from erp_ai.agent.tools.registry import ToolContext, execute_tool, get_tool_schemas
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_PENDING,
	PROPOSAL_DOCTYPE,
	ROLE_AGENT,
)
from erp_ai.test_utils import GitSandbox

AGENT = "propose.agent@example.com"
BOSS = "propose.boss@example.com"
APP = "custom_app"
REL = "pkg/mod.py"
PATH = f"{APP}/{REL}"
BEFORE = "x = 1\r\n# Tiếng Việt\r\ny = 1\r\n"
TOOL_NAMES = ["propose_file_change", "propose_new_file", "propose_bench_command"]
# Command table of design 3.1, written by hand
BENCH_COMMANDS_TABLE = ("migrate", "build", "clear-cache", "clear-website-cache", "list-apps", "version")
NOT_GRANTED = {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}


def _sha(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestProposeGrant(FrappeTestCase):
	def test_offered_only_with_switch_l3_and_instructor(self):
		def names(level, has_instructor, change_enabled):
			granted = get_tool_schemas(level, has_instructor, change_enabled)
			return [spec["name"] for spec in granted if spec["name"] in TOOL_NAMES]

		self.assertEqual(names("L3", True, True), TOOL_NAMES)
		for case in (("L3", True, False), ("L3", False, True), ("L2", True, True), ("L0", True, True)):
			self.assertEqual(names(*case), [], case)

	def test_propose_tool_names_are_the_three_tools(self):
		names = ("propose_file_change", "propose_new_file", "propose_bench_command")
		self.assertEqual(propose_change.PROPOSE_TOOL_NAMES, names)
		self.assertEqual(tuple(spec.name for spec in propose_change.TOOLS), names)
		self.assertNotIn("propose_delete_file", propose_change.PROPOSE_TOOL_NAMES)


class TestProposeChange(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT)
		# `instructor` is a Link to User: the person who gave the order must exist.
		create_agent(BOSS)
		frappe.get_doc("User", AGENT).add_roles(ROLE_AGENT)
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		self.ticket = str(make_ticket(subject="ERPAI-TEST propose", raised_by=AGENT).name)
		frappe.set_user(AGENT)

	def context(self, **fields):
		values = {
			"ticket_name": self.ticket,
			"effective_level": "L3",
			"instructor": BOSS,
			"run_id": "run-propose",
			"category_mapping": {},
			"agent_user": AGENT,
			"change_enabled": True,
			"allowed_apps": (APP,),
		}
		return ToolContext(**{**values, **fields})

	def run_tool(self, name, arguments, **context):
		return execute_tool(name, arguments, self.context(**context))

	def change(self, find, replace, path=PATH, **context):
		arguments = {"path": path, "find": find, "replace": replace, "reason": "sửa theo yêu cầu"}
		return self.run_tool("propose_file_change", arguments, **context)

	def on_disk(self, rel=REL):
		with open(os.path.join(self.sandbox.repo(APP), rel), encoding="utf-8", newline="") as handle:
			return handle.read()

	def disk_hash(self, rel=REL):
		with open(os.path.join(self.sandbox.repo(APP), rel), "rb") as handle:
			return hashlib.sha256(handle.read()).hexdigest()

	def git_snapshot(self):
		return (
			self.sandbox.git(APP, "rev-parse", "HEAD"),
			self.sandbox.git(APP, "status", "--porcelain", "--untracked-files=all"),
		)

	def assert_nothing_created(self):
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])
		self.assertEqual(self.on_disk(), BEFORE)

	def proposals(self):
		frappe.set_user("Administrator")
		names = frappe.get_all(PROPOSAL_DOCTYPE, filters={"ticket": self.ticket}, pluck="name")
		frappe.set_user(AGENT)
		return names

	def comments(self):
		frappe.set_user("Administrator")
		rows = frappe.get_all(
			"Comment",
			filters=authority.ticket_comment_filters(self.ticket),
			fields=["name", "content", "owner"],
		)
		frappe.set_user(AGENT)
		return rows

	def test_file_change_creates_pending_proposal_and_comment_without_touching_disk(self):
		# a branch other than the sandbox default, so a hard-coded branch cannot pass
		self.sandbox.switch_branch(APP, "feature/propose")
		file_hash, git_before = self.disk_hash(), self.git_snapshot()
		result = self.change(["x = 1", "y = 1"], ["x = 2", "y = 3"])

		self.assertEqual(set(result), {"ok", "proposal", "status", "comment", "branch"}, result)
		self.assertEqual(
			(result["ok"], result["status"], result["branch"]), (True, "Chờ duyệt", "feature/propose")
		)
		after = "x = 2\r\n# Tiếng Việt\r\ny = 3\r\n"
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		self.assertEqual(
			(doc.change_kind, doc.app, doc.file_path, doc.is_new_file, doc.reversible),
			(CHANGE_KIND_CODE, APP, PATH, 0, 1),
		)
		self.assertEqual((doc.content_before, doc.content_after), (BEFORE, after))
		self.assertEqual((doc.base_hash, doc.after_hash), (_sha(BEFORE), _sha(after)))
		self.assertEqual((doc.ticket, doc.run_id, doc.instructor), (self.ticket, "run-propose", BOSS))
		self.assertEqual((doc.target_branch, doc.upstream_ref, doc.is_core_app), ("feature/propose", "", 0))
		self.assertEqual(doc.reason, "sửa theo yêu cầu")
		self.assertIn("-x = 1", doc.diff)
		self.assertIn("+x = 2", doc.diff)
		self.assertIn(doc.name, doc.commit_message)
		# nothing on disk or in git changed
		self.assertEqual(self.disk_hash(), file_hash)
		self.assertEqual(self.git_snapshot(), git_before)
		self.assertEqual(self.proposals(), [doc.name])
		(comment,) = self.comments()
		self.assertEqual(result["comment"], comment.name)
		self.assertEqual(comment.owner, AGENT)
		link = f"/app/erp-ai-change-proposal/{doc.name}"
		first = f'<p>Đề xuất <a href="{link}">{doc.name}</a> đang chờ duyệt: sửa <code>{PATH}</code>.</p>'
		self.assertTrue(comment.content.startswith(first), comment.content)
		approve = frappe.utils.escape_html(change_link.decision_path(doc.name, "approve"))
		reject = frappe.utils.escape_html(change_link.decision_path(doc.name, "reject"))
		self.assertIn(f'<a href="{approve}"><strong>Duyệt</strong></a>', comment.content)
		self.assertIn(f'<a href="{reject}"><strong>Từ chối</strong></a>', comment.content)
		self.assertLess(comment.content.index(approve), comment.content.index(reject))
		self.assertIn("<p>Sau khi áp dụng cần người chạy bench restart.</p>", comment.content)

	def test_finds_replace_by_position_on_the_original_content(self):
		# out of order, swapping each other's text, and touching without overlapping
		swapped = self.change(["y = 1", "x = 1"], ["x = 1", "y = 1"])
		touching = self.change(["x = 1", "\r\n# Tiếng"], ["a", "|"])

		frappe.set_user("Administrator")
		for result, after in (
			(swapped, "y = 1\r\n# Tiếng Việt\r\nx = 1\r\n"),
			(touching, "a| Việt\r\ny = 1\r\n"),
		):
			self.assertTrue(result["ok"], result)
			self.assertEqual(
				frappe.db.get_value(PROPOSAL_DOCTYPE, result["proposal"], "content_after"), after
			)

	def test_edit_errors_create_nothing(self):
		shape = "find và replace phải cùng số phần tử, từ 1 đến 10"
		no_change = "nội dung sau trùng nội dung trước"
		cases = (
			(["không có"], ["x"], "đoạn find[0] không có trong file"),
			(["x = 1", "không có"], ["x = 2", "z"], "đoạn find[1] không có trong file"),
			(["= 1"], ["= 2"], "đoạn find[0] xuất hiện nhiều hơn một lần"),
			(["x = 1", "= 1"], ["x = 2", "= 2"], "đoạn find[1] xuất hiện nhiều hơn một lần"),
			(["x = 1\r\n#", "\n# Tiếng"], ["a", "b"], "các đoạn find chồng nhau"),
			(["# Tiếng Việt", "Tiếng"], ["a", "b"], "các đoạn find chồng nhau"),
			(["x = 1", "y = 1"], ["x = 2"], shape),
			(["x = 1"], ["x = 2", "y = 2"], shape),
			([], [], shape),
			(["x = 1"], ["x = 1"], no_change),
			(["x = 1", "y = 1"], ["x = 1", "y = 1"], no_change),
		)
		for find, replace, reason in cases:
			with self.subTest(find=find, replace=replace):
				self.assertEqual(self.change(find, replace), {"ok": False, "reason": reason})
		# shapes the schema refuses before the handler runs
		for find, replace, key in (
			(["x = 1"] * 11, ["x = 2"] * 11, "find"),
			([""], ["x"], "find"),
			([1], ["x"], "find"),
			(["x = 1"], ["x" * 20001], "replace"),
		):
			with self.subTest(key=key, find=find[:1]):
				refused = self.change(find, replace)
				self.assertEqual(refused, {"ok": False, "reason": f"tham số không hợp lệ: {key}"})
		old_shape = {"path": PATH, "edits": [{"old": "x = 1", "new": "x = 2"}], "reason": "x"}
		self.assertEqual(
			self.run_tool("propose_file_change", old_shape),
			{"ok": False, "reason": "tham số không hợp lệ: find"},
		)
		self.assert_nothing_created()

	def test_tool_cannot_insert_non_pending_state(self):
		real_values = propose_change._code_values

		def forged(*args, **kwargs):
			return {**real_values(*args, **kwargs), "change_status": "Đã duyệt", "commit_message": "forged"}

		with patch.object(propose_change, "_code_values", side_effect=forged):
			result = self.change(["x = 1"], ["x = 2"])

		self.assertEqual((result["ok"], result["status"]), (True, "Chờ duyệt"), result)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		self.assertEqual(doc.change_status, "Chờ duyệt")
		self.assertEqual(
			doc.commit_message,
			f"erp_ai: áp dụng {doc.name} ({PATH})\n\n"
			f"Đề xuất: {doc.name}\nPhiếu: {self.ticket}\nNgười duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)

	def test_each_guard_refusal_creates_zero_proposals(self):
		self.sandbox.commit_file(APP, "pkg/big.txt", "a" * (1024 * 1024 + 1))
		self.sandbox.commit_file(APP, "pkg/latin1.py", b"x = '\xe9'\n")
		cases = (
			("../etc/passwd", "đường dẫn không hợp lệ hoặc nằm ngoài apps/"),
			("helpdesk/README.md", "app không có trong danh sách được sửa"),
			("erp_ai/README.md", "không được sửa app erp_ai hoặc kho git của nó"),
			(f"{APP}/pkg/secret_key.py", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			(f"{APP}/pkg/tool.sh", "đuôi file không được phép"),
			(f"{APP}/.git/notes.md", "không được chạm thư mục .git"),
			(
				f"{APP}/pkg/star*.py",
				'tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được',
			),
			(f"{APP}/pkg/missing.py", "file không tồn tại"),
			(f"{APP}/pkg/big.txt", "file lớn hơn 1 MiB"),
			(f"{APP}/pkg/latin1.py", "file không phải UTF-8"),
		)
		# erp_ai is on the list here: it is refused all the same
		allowed = (APP, "erp_ai")
		for path, reason in cases:
			with self.subTest(path=path):
				result = self.change(["x"], ["y"], path, allowed_apps=allowed)
				self.assertEqual(result, {"ok": False, "reason": reason})
		self.assert_nothing_created()

	def test_file_of_exactly_one_mib_is_read(self):
		self.sandbox.commit_file(APP, "pkg/edge.txt", "b" + "a" * (1024 * 1024 - 1))
		result = self.change(["b"], ["c"], f"{APP}/pkg/edge.txt")
		self.assertTrue(result["ok"], result)

	def test_git_refusal_creates_zero_proposals(self):
		target = "pkg/mod.py"
		for app in ("frappe", "erpnext", "helpdesk"):
			self.sandbox.commit_file(app, target, BEFORE)
		self.sandbox.write_unstaged(APP, REL, "x = 9\n")
		self.sandbox.detach("frappe")
		self.sandbox.mark_in_progress("erpnext", "MERGE_HEAD")
		self.sandbox.hold_index_lock("helpdesk")
		self.sandbox.commit_file("hrms", ".gitignore", "pkg/ignored.py\n")
		self.sandbox.write_unstaged("hrms", "pkg/ignored.py", BEFORE)
		cases = (
			(PATH, "file đích có thay đổi chưa commit"),
			(f"frappe/{target}", "HEAD của kho git không nằm trên nhánh nào (detached)"),
			(f"erpnext/{target}", "kho git đang dở merge, rebase, cherry-pick hoặc revert"),
			(
				f"helpdesk/{target}",
				"kho git đang bị khóa (index.lock): có thao tác git khác đang chạy hoặc bị dừng giữa chừng",
			),
			("hrms/pkg/ignored.py", "file đích bị git bỏ qua (.gitignore)"),
		)
		allowed = (APP, "frappe", "erpnext", "helpdesk", "hrms")
		for path, reason in cases:
			with self.subTest(path=path):
				result = self.change(["x = 1"], ["x = 2"], path, allowed_apps=allowed)
				self.assertEqual(result, {"ok": False, "reason": reason})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])

	def test_comment_escapes_html_and_adds_restart_note_for_py(self):
		# `<` and `>` are left out of the path and branch: Frappe's XSS filter rewrites them in Data fields
		self.sandbox.switch_branch(APP, "a&b\"c'd")
		self.sandbox.commit_file(APP, "pkg/x&y'z.py", "v = 1\n")
		self.sandbox.commit_file(APP, "pkg/notes.md", "v = 1\n")
		python = self.change(["v = 1"], ["v = 2"], f"{APP}/pkg/x&y'z.py")
		markdown = self.change(["v = 1"], ["v = 2"], f"{APP}/pkg/notes.md")
		with patch.object(propose_change.change_text, "proposal_notes", return_value=["<script>x</script>"]):
			scripted = self.change(["y = 1"], ["y = 2"])
		self.assertTrue(python["ok"], python)
		self.assertTrue(markdown["ok"], markdown)
		self.assertTrue(scripted["ok"], scripted)

		contents = {row.name: row.content for row in self.comments()}
		python_comment, markdown_comment = contents[python["comment"]], contents[markdown["comment"]]
		self.assertIn(f"sửa <code>{APP}/pkg/x&amp;y&apos;z.py</code>.</p>", python_comment)
		self.assertIn(f"<p>Commit sẽ vào nhánh a&amp;b&quot;c&apos;d của app {APP}.</p>", python_comment)
		self.assertIn("<p>&lt;script&gt;x&lt;/script&gt;</p>", contents[scripted["comment"]])
		self.assertNotIn("<script>", contents[scripted["comment"]])
		restart = "<p>Sau khi áp dụng cần người chạy bench restart.</p>"
		self.assertIn(restart, python_comment)
		self.assertIn(f"sửa <code>{APP}/pkg/notes.md</code>.</p>", markdown_comment)
		self.assertNotIn("bench restart", markdown_comment)

	def new_file(self, path=f"{APP}/pkg/new_mod.py", content="z = 1\n"):
		return self.run_tool("propose_new_file", {"path": path, "content": content, "reason": "thêm module"})

	def test_new_file_proposal_does_not_create_file(self):
		# a branch other than the sandbox default, so a hard-coded branch cannot pass
		self.sandbox.switch_branch(APP, "feature/new")
		git_before = self.git_snapshot()
		result = self.new_file()

		self.assertEqual(set(result), {"ok", "proposal", "status", "comment", "branch"}, result)
		self.assertEqual(
			(result["ok"], result["status"], result["branch"]), (True, "Chờ duyệt", "feature/new")
		)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		frappe.set_user(AGENT)
		new_path = f"{APP}/pkg/new_mod.py"
		self.assertEqual(
			(doc.change_kind, doc.app, doc.file_path, doc.is_new_file, doc.reversible),
			(CHANGE_KIND_CODE, APP, new_path, 1, 1),
		)
		self.assertEqual((doc.content_after, doc.after_hash), ("z = 1\n", _sha("z = 1\n")))
		self.assertEqual((doc.content_before, doc.base_hash), ("", ""))
		self.assertEqual(doc.target_branch, "feature/new")
		self.assertIn("+z = 1", doc.diff)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "pkg/new_mod.py")))
		self.assertEqual(self.on_disk(), BEFORE)
		self.assertEqual(self.git_snapshot(), git_before)
		self.assertEqual(self.proposals(), [doc.name])
		(comment,) = self.comments()
		self.assertEqual(result["comment"], comment.name)
		self.assertIn(f"đang chờ duyệt: tạo <code>{new_path}</code>.</p>", comment.content)

	def test_new_file_errors_exists_and_no_parent(self):
		self.sandbox.commit_file(APP, ".gitignore", "pkg/ignored_new.py\n")
		cases = (
			(PATH, "file đã tồn tại"),
			(f"{APP}/khong_co/new.py", "thư mục cha chưa có"),
			(f"{APP}/pkg/tool.exe", "đuôi file không được phép"),
			(f"{APP}/pkg/secret_key.py", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			(f"{APP}/pkg/ignored_new.py", "file đích bị git bỏ qua (.gitignore)"),
			# path minLength is 1 (design 3.1): a one-character path reaches the guard, not the schema
			("a", "app không có trong danh sách được sửa"),
			("", "tham số không hợp lệ: path"),
		)
		for path, reason in cases:
			with self.subTest(path=path):
				self.assertEqual(self.new_file(path), {"ok": False, "reason": reason})
		self.assert_nothing_created()

	def test_no_delete_or_rename_operation_exists(self):
		operation_words = ("delete", "remove", "rename", "move", "unlink", "xoa", "xóa", "doi_ten", "đổi tên")
		for spec in get_tool_schemas("L3", True, True):
			words = [spec["name"], *spec["input_schema"].get("properties", {})]
			for word in words:
				with self.subTest(tool=spec["name"], word=word):
					self.assertFalse([w for w in operation_words if w in word.lower()])
		(new_file,) = [spec for spec in propose_change.TOOLS if spec.name == "propose_new_file"]
		content = new_file.schema["input_schema"]["properties"]["content"]
		self.assertEqual((content["minLength"], content["maxLength"]), (1, 20000))
		self.assertEqual(new_file.schema["input_schema"]["properties"]["path"]["minLength"], 1)
		# an empty file is the closest a new-file proposal gets to a delete: the schema refuses it
		for text in ("", "x" * 20001):
			with self.subTest(length=len(text)):
				self.assertEqual(
					self.new_file(content=text), {"ok": False, "reason": "tham số không hợp lệ: content"}
				)
		self.assert_nothing_created()

	def test_bench_command_proposal_and_its_refusals(self):
		result = self.run_tool(
			"propose_bench_command", {"command": "build", "app": APP, "reason": "build lại giao diện"}
		)

		self.assertTrue(result["ok"], result)
		self.assertNotIn("branch", result)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		frappe.set_user(AGENT)
		self.assertEqual(
			(doc.change_kind, json.loads(doc.command_args), doc.reversible, doc.commit_message),
			(CHANGE_KIND_COMMAND, ["build", "--app", APP], 0, None),
		)
		migrate = self.run_tool(
			"propose_bench_command", {"command": "migrate", "reason": "sau khi sửa DocType"}
		)
		self.assertTrue(migrate["ok"], migrate)
		(comment,) = [row for row in self.comments() if result["proposal"] in row.content]
		self.assertIn("không hoàn tác được", comment.content)
		for arguments, phrase in (
			({"command": "build", "reason": "x"}, "cần app"),
			({"command": "build", "app": "helpdesk", "reason": "x"}, "không có trong danh sách"),
			({"command": "migrate", "app": APP, "reason": "x"}, "không nhận app"),
		):
			refused = self.run_tool("propose_bench_command", arguments)
			self.assertFalse(refused["ok"], arguments)
			self.assertIn(phrase, refused["reason"], arguments)
		self.assertEqual(
			self.run_tool("propose_bench_command", {"command": "restart", "reason": "x"})["reason"],
			"tham số không hợp lệ: command",
		)
		self.assertEqual(len(self.proposals()), 2)

	def bench(self, command, app=None, **context):
		arguments = {"command": command, "reason": "chạy lệnh bench"}
		if app is not None:
			arguments["app"] = app
		return self.run_tool("propose_bench_command", arguments, **context)

	def test_command_proposal_makes_zero_subprocess_calls(self):
		git_before = self.git_snapshot()
		with (
			patch("subprocess.Popen") as popen,
			patch("subprocess.run") as run,
			patch("subprocess.call") as call,
			patch("subprocess.check_call") as check_call,
			patch("subprocess.check_output") as check_output,
			patch("os.system") as system,
			patch("os.popen") as os_popen,
		):
			results = [self.bench(command) for command in BENCH_COMMANDS_TABLE if command != "build"]
			results.append(self.bench("build", APP))
		spawns = {
			"subprocess.Popen": popen,
			"subprocess.run": run,
			"subprocess.call": call,
			"subprocess.check_call": check_call,
			"subprocess.check_output": check_output,
			"os.system": system,
			"os.popen": os_popen,
		}
		self.assertEqual({name: spawn.call_count for name, spawn in spawns.items()}, dict.fromkeys(spawns, 0))
		for result in results:
			with self.subTest(result=result):
				self.assertEqual(set(result), {"ok", "proposal", "status", "comment"}, result)
				self.assertEqual((result["ok"], result["status"]), (True, "Chờ duyệt"))
		self.assertEqual(self.git_snapshot(), git_before)
		self.assertEqual(self.on_disk(), BEFORE)
		self.assertEqual(len(self.proposals()), len(BENCH_COMMANDS_TABLE))

	def test_bench_command_tool_refuses_enum_outside_and_app_misuse(self):
		(spec,) = [spec for spec in propose_change.TOOLS if spec.name == "propose_bench_command"]
		properties = spec.schema["input_schema"]["properties"]
		self.assertEqual(set(properties["command"]["enum"]), set(BENCH_COMMANDS_TABLE))
		self.assertEqual(len(properties["command"]["enum"]), len(BENCH_COMMANDS_TABLE))
		self.assertNotIn("update", properties["command"]["enum"])
		self.assertEqual((properties["app"]["minLength"], properties["app"]["maxLength"]), (1, 100))
		self.assertEqual(spec.schema["input_schema"]["required"], ["command", "reason"])

		allowed = (APP, "frappe", "erp_ai", "erp_ai-wt")
		forbidden = "không được sửa app erp_ai hoặc kho git của nó"
		cases = (
			# outside the enum: the schema refuses before the handler
			({"command": "update"}, "tham số không hợp lệ: command"),
			({"command": "restart"}, "tham số không hợp lệ: command"),
			({"command": "build", "app": ""}, "tham số không hợp lệ: app"),
			({"command": "build", "app": "a" * 101}, "tham số không hợp lệ: app"),
			# build needs an app that passes the app guard
			({"command": "build"}, "lệnh build cần app"),
			({"command": "build", "app": "helpdesk"}, "app không có trong danh sách được sửa"),
			({"command": "build", "app": "erp_ai"}, forbidden),
			({"command": "build", "app": "erp_ai-wt"}, forbidden),
			# any other command takes no app: a site command and `version`
			({"command": "migrate", "app": APP}, "lệnh này không nhận app"),
			({"command": "version", "app": APP}, "lệnh này không nhận app"),
		)
		for arguments, reason in cases:
			with self.subTest(arguments=arguments):
				result = self.run_tool(
					"propose_bench_command", {**arguments, "reason": "x"}, allowed_apps=allowed
				)
				self.assertEqual(result, {"ok": False, "reason": reason})
		# the handler itself refuses a command outside the table, whatever reaches it
		direct = propose_change.propose_bench_command(
			{"command": "update", "reason": "x"}, self.context(allowed_apps=allowed)
		)
		self.assertEqual(direct, {"ok": False, "reason": "lệnh không có trong danh sách cho phép"})
		# an app of 100 characters passes the schema and reaches the app guard
		longest = self.bench("build", "a" * 100, allowed_apps=allowed)
		self.assertEqual(longest, {"ok": False, "reason": "app không có trong danh sách được sửa"})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])

	def test_command_args_built_by_server_for_each_command(self):
		site = frappe.local.site
		expected = {
			"migrate": ["--site", site, "migrate"],
			"build": ["build", "--app", "frappe"],
			"clear-cache": ["--site", site, "clear-cache"],
			"clear-website-cache": ["--site", site, "clear-website-cache"],
			"list-apps": ["--site", site, "list-apps"],
			"version": ["version"],
		}
		self.assertEqual(set(expected), set(BENCH_COMMANDS_TABLE))
		for command, command_args in expected.items():
			with self.subTest(command=command):
				app = "frappe" if command == "build" else None
				result = self.bench(command, app, allowed_apps=(APP, "frappe"))
				self.assertEqual(set(result), {"ok", "proposal", "status", "comment"}, result)
				self.assertEqual((result["ok"], result["status"]), (True, "Chờ duyệt"))
				frappe.set_user("Administrator")
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
				frappe.set_user(AGENT)
				self.assertEqual(json.loads(doc.command_args), command_args)
				self.assertEqual(
					(doc.change_kind, doc.change_status, doc.reversible, doc.is_new_file),
					(CHANGE_KIND_COMMAND, CHANGE_STATUS_PENDING, 0, 0),
				)
				self.assertEqual((doc.app or "", doc.reason), (app or "", "chạy lệnh bench"))
				# a command proposal carries no git field, even for a core app such as frappe
				self.assertEqual(
					(doc.target_branch, doc.upstream_ref, doc.ahead_count, doc.is_core_app), ("", "", 0, 0)
				)
				self.assertEqual(
					(doc.file_path or "", doc.base_hash or "", doc.content_after or ""), ("", "", "")
				)
				(comment,) = [row for row in self.comments() if row.name == result["comment"]]
				shown = " ".join(command_args)
				self.assertIn(f"đang chờ duyệt: lệnh <code>bench {shown}</code>.</p>", comment.content)
				self.assertIn("<p>Lệnh bench không hoàn tác được.</p>", comment.content)
				self.assertNotIn("Commit sẽ vào nhánh", comment.content)
				self.assertNotIn("Cảnh báo app lõi", comment.content)

	def test_not_granted_without_switch_instructor_or_l3(self):
		edit = (["x = 1"], ["x = 2"])
		self.assertEqual(self.change(*edit, change_enabled=False), NOT_GRANTED)
		self.assertEqual(self.change(*edit, instructor=None), NOT_GRANTED)
		self.assertEqual(self.change(*edit, effective_level="L2"), NOT_GRANTED)
		self.assertEqual(self.proposals(), [])

	def test_handler_itself_refuses_without_instructor_or_create_permission(self):
		arguments = {"path": PATH, "find": ["x = 1"], "replace": ["x = 2"], "reason": "x"}
		no_instructor = propose_change.propose_file_change(arguments, self.context(instructor=None))
		self.assertEqual(no_instructor, {"ok": False, "reason": "không có người ra lệnh"})
		with patch.object(frappe, "has_permission", return_value=False):
			no_permission = propose_change.propose_file_change(arguments, self.context())
		self.assertEqual(no_permission, {"ok": False, "reason": "thiếu quyền tạo đề xuất"})

		def comment_refused(doctype, *args, **kwargs):
			return doctype != "Comment"

		with patch.object(frappe, "has_permission", side_effect=comment_refused):
			no_comment = propose_change.propose_file_change(arguments, self.context())
		self.assertEqual(no_comment, {"ok": False, "reason": "thiếu quyền tạo comment"})
		self.assert_nothing_created()
