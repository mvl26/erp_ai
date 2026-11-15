import hashlib
import json
import os
import re
import subprocess
from unittest.mock import patch

import frappe
import frappe.client
from frappe.desk.form.save import savedocs
from frappe.model.rename_doc import rename_doc
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai import constants
from erp_ai.agent import authority, change_link
from erp_ai.agent.agent_write_guard import AGENT_WRITE_FLAG
from erp_ai.agent.changes import process_runner, transitions
from erp_ai.agent.tools import change_guard, propose_change, source
from erp_ai.agent.tools.registry import ToolContext, execute_tool, get_tool_schemas
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_MAX_COMMANDS,
	CHANGE_MAX_FILE_OPS,
	CHANGE_OP_CREATE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_UNDOING,
	PROPOSAL_DOCTYPE,
	ROLE_AGENT,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as controller
from erp_ai.test_utils import GitSandbox, pin_agent_roles

AGENT = "propose.agent@example.com"
BOSS = "propose.boss@example.com"
APP = "custom_app"
REL = "pkg/mod.txt"
PATH = f"{APP}/{REL}"
BEFORE = "x = 1\r\n# Tiếng Việt\r\ny = 1\r\n"
TOOL_NAMES = ["propose_file_change", "propose_new_file", "propose_bench_command"]
# Command table of design 3.1, written by hand
BENCH_COMMANDS_TABLE = ("migrate", "build", "clear-cache", "clear-website-cache", "list-apps", "version")
NOT_GRANTED = {"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}
# Sentences of design 3.9, written by hand
NO_UPSTREAM_NOTE = "<p>Nhánh này không theo nhánh remote nào.</p>"
CORE_WARNING_START = "<p>Cảnh báo app lõi: "
CORE_WARNING = (
	"<p>Cảnh báo app lõi: frappe dùng chung cho mọi site trên bench này, nên thay đổi ảnh hưởng tất cả các "
	"site. bench update không giữ commit local: nó dừng nếu kho có thay đổi chưa commit; khi kho sạch, nó "
	"kéo bằng git pull (merge) từ remote upstream hoặc remote đầu tiên, có thể tạo merge commit hoặc xung "
	"đột; bench update --reset xóa vĩnh viễn commit chưa đẩy. Đẩy commit lên fork là việc của người, làm "
	"trước khi chạy bench update.</p>"
)
REMOTE_URL = "https://x-token-FAKE@host/r.git"
GIT_FIELDS = ("target_branch", "upstream_ref", "ahead_count", "is_core_app")
REFUSAL = "Tài khoản agent không được ghi"
GUARDED_HOOKS = ("before_insert", "validate", "on_trash", "before_rename")
# As frappe.model.rename_doc passes them: old name, new name, merge.
HOOK_ARGUMENTS = {"before_rename": ("old-name", "new-name", False)}
GUARD_SAVEPOINT = "erp_ai_proposal_guard_path"
GUARD_INSTRUCTOR = "propose.guard.instructor@example.com"
# The DocType name spelled with a JSON escape, as a model could send it through call_method.
PROPOSAL_ESCAPED = "ERP AI \\u0043hange Proposal"
BENCH_ARGUMENTS = {"command": "migrate", "reason": "sau khi sửa DocType"}


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
		(op,) = doc.operations
		self.assertEqual(
			(doc.change_kind, doc.app, op.file_path, int(op.operation == CHANGE_OP_CREATE), doc.reversible),
			(CHANGE_KIND_CODE, APP, PATH, 0, 1),
		)
		self.assertEqual((op.content_before, op.content_after), (BEFORE, after))
		self.assertEqual((op.base_hash, op.after_hash), (_sha(BEFORE), _sha(after)))
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
		first = f'<p>Đề xuất <a href="{link}">{doc.name}</a> đang chờ duyệt: khối 1 mục trong app {APP}.</p>'
		self.assertTrue(comment.content.startswith(first), comment.content)
		approve = frappe.utils.escape_html(change_link.decision_path(doc.name, "approve"))
		reject = frappe.utils.escape_html(change_link.decision_path(doc.name, "reject"))
		self.assertIn(f'<a href="{approve}"><strong>Duyệt</strong></a>', comment.content)
		self.assertIn(f'<a href="{reject}"><strong>Từ chối</strong></a>', comment.content)
		self.assertLess(comment.content.index(approve), comment.content.index(reject))

	def test_comment_of_each_tool_has_three_links_and_decisions_open_the_form(self):
		results = (
			self.change(["x = 1"], ["x = 2"]),
			self.new_file(),
			self.run_tool("propose_bench_command", {"command": "migrate", "reason": "sau khi sửa DocType"}),
		)
		frappe.set_user("Administrator")
		contents = {row.name: row.content for row in self.comments()}
		for tool, result in zip(TOOL_NAMES, results, strict=True):
			with self.subTest(tool=tool):
				self.assertTrue(result["ok"], result)
				name = result["proposal"]
				form = f"/app/erp-ai-change-proposal/{name}"
				labelled = re.findall(
					r'<a href="([^"]*)">(?:<strong>)?([^<]*)(?:</strong>)?</a>', contents[result["comment"]]
				)
				labelled = [(frappe.utils.html_utils.unescape_html(href), text) for href, text in labelled]
				links = {text: href for href, text in labelled if text != name}
				self.assertEqual(set(links), {"Duyệt", "Từ chối", "Xem nội dung thay đổi"}, labelled)
				self.assertEqual(len({href for href, _ in labelled}), 3, labelled)
				self.assertEqual(links["Xem nội dung thay đổi"], form)
				for label, action in (("Duyệt", "approve"), ("Từ chối", "reject")):
					href = links[label]
					self.assertTrue(href.startswith(f"{form}?"), href)
					self.assertNotIn("/api/method/", href)
					self.assertEqual(href, change_link.decision_path(name, action))

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
				frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"]).operations[0].content_after, after
			)

	def test_edit_errors_create_nothing(self):
		shape = "find và replace phải cùng số phần tử, ít nhất 1"
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
				self.assertEqual(
					self.change(find, replace), {"ok": False, "reason": f"mục 1 ({PATH}): {reason}"}
				)
		# shapes the schema refuses before the handler runs
		for find, replace, key in (
			("x = 1", ["x = 2"], "find"),
			([""], ["x"], "find"),
			([1], ["x"], "find"),
			(["x = 1"], [1], "replace"),
		):
			with self.subTest(key=key, find=find[:1]):
				refused = self.change(find, replace)
				self.assertEqual(refused, {"ok": False, "reason": f"tham số không hợp lệ: {key}"})
		old_shape = {"path": PATH, "edits": [{"old": "x = 1", "new": "x = 2"}], "reason": "x"}
		self.assertEqual(
			self.run_tool("propose_file_change", old_shape),
			{"ok": False, "reason": "tham số không hợp lệ: edits"},
		)
		self.assert_nothing_created()
		# old shape without a stray key reaches the handler and keeps the old refusal
		legacy_missing_find = {"path": PATH, "replace": ["x = 2"], "reason": "x"}
		self.assertEqual(
			self.run_tool("propose_file_change", legacy_missing_find),
			{"ok": False, "reason": "tham số không hợp lệ: find"},
		)
		self.assert_nothing_created()

	def test_tool_cannot_insert_non_pending_state(self):
		real_insert = propose_change._insert

		def forged(ctx, values):
			return real_insert(ctx, {**values, "change_status": "Đã duyệt", "commit_message": "forged"})

		with patch.object(propose_change, "_insert", side_effect=forged):
			result = self.change(["x = 1"], ["x = 2"])

		self.assertEqual((result["ok"], result["status"]), (True, "Chờ duyệt"), result)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		self.assertEqual(doc.change_status, "Chờ duyệt")
		self.assertEqual(
			doc.commit_message,
			f"erp_ai: áp dụng {doc.name} ({PATH})\n\n"
			f"Đề xuất: {doc.name}\nPhiếu: {self.ticket}\nsửa {PATH}\nNgười duyệt: <người duyệt>\n"
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
			(f"{APP}/pkg/tool.sh", propose_change.NOT_FOUND),
			(f"{APP}/.git/notes.md", change_guard.GIT_DIR),
			(
				f"{APP}/pkg/star*.py",
				'tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được',
			),
			(f"{APP}/pkg/missing.py", "file không tồn tại"),
			(f"{APP}/pkg/big.txt", "đoạn find[0] không có trong file"),
			(f"{APP}/pkg/latin1.py", source.TEXT_NOT_UTF8),
		)
		# erp_ai is on the list here: it is refused all the same
		allowed = (APP, "erp_ai")
		for path, reason in cases:
			with self.subTest(path=path):
				result = self.change(["x"], ["y"], path, allowed_apps=allowed)
				self.assertEqual(result, {"ok": False, "reason": f"mục 1 ({path}): {reason}"})
		self.assert_nothing_created()

	def test_file_of_exactly_one_mib_is_read(self):
		self.sandbox.commit_file(APP, "pkg/edge.txt", "b" + "a" * (1024 * 1024 - 1))
		result = self.change(["b"], ["c"], f"{APP}/pkg/edge.txt")
		self.assertTrue(result["ok"], result)

	def test_git_refusal_creates_zero_proposals(self):
		target = "pkg/mod.py"
		for app in ("frappe", "erpnext", "helpdesk"):
			self.sandbox.commit_file(app, target, BEFORE)
		self.sandbox.write_unstaged(APP, REL, "x = 1\nx = 9\n")
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
				self.assertEqual(result, {"ok": False, "reason": f"mục 1 ({path}): {reason}"})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])

	def test_comment_escapes_html_and_adds_restart_note_for_py(self):
		# `<` and `>` are left out of the path and branch: Frappe's XSS filter rewrites them in Data fields
		self.sandbox.switch_branch(APP, "a&b\"c'd")
		self.sandbox.commit_file(APP, "pkg/x&y'z.txt", "v = 1\n")
		self.sandbox.commit_file(APP, "pkg/notes.md", "v = 1\n")
		python = self.change(["v = 1"], ["v = 2"], f"{APP}/pkg/x&y'z.txt")
		markdown = self.change(["v = 1"], ["v = 2"], f"{APP}/pkg/notes.md")
		with patch.object(propose_change.change_text, "proposal_notes", return_value=["<script>x</script>"]):
			scripted = self.change(["y = 1"], ["y = 2"])
		self.assertTrue(python["ok"], python)
		self.assertTrue(markdown["ok"], markdown)
		self.assertTrue(scripted["ok"], scripted)

		contents = {row.name: row.content for row in self.comments()}
		python_comment, markdown_comment = contents[python["comment"]], contents[markdown["comment"]]
		self.assertIn(f"<p>sửa {APP}/pkg/x&amp;y&apos;z.txt</p>", python_comment)
		self.assertIn(f"<p>Commit sẽ vào nhánh a&amp;b&quot;c&apos;d của app {APP}.</p>", python_comment)
		self.assertIn("<p>&lt;script&gt;x&lt;/script&gt;</p>", contents[scripted["comment"]])
		self.assertNotIn("<script>", contents[scripted["comment"]])
		self.assertIn(f"<p>sửa {APP}/pkg/notes.md</p>", markdown_comment)
		self.assertNotIn("bench restart", markdown_comment)

	def new_file(self, path=f"{APP}/pkg/new_mod.txt", content="z = 1\n"):
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
		new_path = f"{APP}/pkg/new_mod.txt"
		(op,) = doc.operations
		self.assertEqual(
			(doc.change_kind, doc.app, op.file_path, int(op.operation == CHANGE_OP_CREATE), doc.reversible),
			(CHANGE_KIND_CODE, APP, new_path, 1, 1),
		)
		self.assertEqual((op.content_after, op.after_hash), ("z = 1\n", _sha("z = 1\n")))
		self.assertEqual((op.content_before, op.base_hash), (None, None))
		self.assertEqual(doc.target_branch, "feature/new")
		self.assertIn("+z = 1", doc.diff)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "pkg/new_mod.txt")))
		self.assertEqual(self.on_disk(), BEFORE)
		self.assertEqual(self.git_snapshot(), git_before)
		self.assertEqual(self.proposals(), [doc.name])
		(comment,) = self.comments()
		self.assertEqual(result["comment"], comment.name)
		self.assertIn(f"<p>tạo {new_path}</p>", comment.content)
		self.assertIn(f"đang chờ duyệt: khối 1 mục trong app {APP}.</p>", comment.content)

	def test_new_file_errors_exists_and_no_parent(self):
		self.sandbox.commit_file(APP, ".gitignore", "pkg/ignored_new.py\n")
		cases = (
			(PATH, "file đã tồn tại"),
			(f"{APP}/khong_co/new.py", change_guard.PY_NEEDS_RESTART),
			(f"{APP}/pkg/.gitattributes", change_guard.GIT_DIR),
			(f"{APP}/pkg/secret_key.py", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			(f"{APP}/pkg/ignored_new.py", "file đích bị git bỏ qua (.gitignore)"),
			# path minLength is 1 (design 3.1): a one-character path reaches the guard, not the schema
			("a", "app không có trong danh sách được sửa"),
			("", "tham số không hợp lệ: path"),
		)
		unprefixed = ("", f"{APP}/khong_co/new.py")
		for path, reason in cases:
			with self.subTest(path=path):
				reason = reason if path in unprefixed else f"mục 1 ({path}): {reason}"
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
		self.assertEqual((content.get("minLength"), content.get("maxLength")), (None, None))
		self.assertEqual(new_file.schema["input_schema"]["properties"]["path"]["minLength"], 1)

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
			(doc.change_kind, json.loads(doc.command_list), doc.reversible, doc.commit_message),
			(CHANGE_KIND_COMMAND, [["build", "--app", APP]], 0, None),
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
		self.assertEqual(set(properties["command"]["enum"]), set(BENCH_COMMANDS_TABLE) | {"restart"})
		self.assertEqual(len(properties["command"]["enum"]), len(BENCH_COMMANDS_TABLE) + 1)
		self.assertNotIn("update", properties["command"]["enum"])
		self.assertEqual((properties["app"]["minLength"], properties["app"]["maxLength"]), (1, 100))
		self.assertEqual(spec.schema["input_schema"]["required"], ["command", "reason"])

		allowed = (APP, "frappe", "erp_ai", "erp_ai-wt")
		forbidden = "không được sửa app erp_ai hoặc kho git của nó"
		cases = (
			# outside the enum: the schema refuses before the handler
			({"command": "update"}, "tham số không hợp lệ: command"),
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
				self.assertEqual(json.loads(doc.command_list), [command_args])
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
				self.assertIn(f"<p>lệnh: bench {shown}</p>", comment.content)
				self.assertIn("đang chờ duyệt: 1 lệnh bench.</p>", comment.content)
				self.assertIn(
					"<p>Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file.</p>",
					comment.content,
				)
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

	def stored(self, proposal):
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal)
		frappe.set_user(AGENT)
		return doc

	def comment_of(self, result):
		(content,) = [row.content for row in self.comments() if row.name == result["comment"]]
		return content

	def assert_in_order(self, text, parts):
		positions = [text.index(part) for part in parts]
		self.assertEqual(positions, sorted(positions), text)

	def test_core_app_proposal_created_when_listed(self):
		core_path = f"frappe/{REL}"
		self.sandbox.commit_file("frappe", REL, BEFORE)
		self.sandbox.switch_branch("frappe", "feature/core")
		unlisted = self.change(["x = 1"], ["x = 2"], core_path)
		self.assertEqual(
			unlisted, {"ok": False, "reason": f"mục 1 ({core_path}): app không có trong danh sách được sửa"}
		)
		self.assertEqual(self.proposals(), [])

		result = self.change(["x = 1"], ["x = 2"], core_path, allowed_apps=(APP, "frappe"))

		self.assertEqual(set(result), {"ok", "proposal", "status", "comment", "branch"}, result)
		self.assertEqual(
			(result["ok"], result["status"], result["branch"]), (True, "Chờ duyệt", "feature/core")
		)
		doc = self.stored(result["proposal"])
		self.assertEqual(
			(doc.change_kind, doc.app, doc.operations[0].file_path), (CHANGE_KIND_CODE, "frappe", core_path)
		)
		self.assertEqual(tuple(doc.get(field) for field in GIT_FIELDS), ("feature/core", "", 0, 1))
		# core app without an upstream: branch, no-upstream sentence, core warning, in that order
		content = self.comment_of(result)
		branch = "<p>Commit sẽ vào nhánh feature/core của app frappe.</p>"
		self.assert_in_order(content, [branch, NO_UPSTREAM_NOTE, CORE_WARNING])
		self.assertNotIn("Nhánh này theo ", content)

	def test_comment_shows_branch_upstream_ahead_and_core_warning(self):
		core_path = f"frappe/{REL}"
		self.sandbox.commit_file("frappe", REL, BEFORE)
		self.sandbox.switch_branch("frappe", "feature/core")
		self.sandbox.add_remote("frappe", url=REMOTE_URL, ahead=3)
		# the store the leak check reads from holds the URL with its token
		self.assertEqual(self.sandbox.git("frappe", "remote", "get-url", "origin").strip(), REMOTE_URL)

		result = self.change(["x = 1"], ["x = 2"], core_path, allowed_apps=(APP, "frappe"))

		self.assertTrue(result["ok"], result)
		doc = self.stored(result["proposal"])
		self.assertEqual(
			tuple(doc.get(field) for field in GIT_FIELDS), ("feature/core", "origin/feature/core", 3, 1)
		)
		content = self.comment_of(result)
		branch = "<p>Commit sẽ vào nhánh feature/core của app frappe.</p>"
		upstream = (
			"<p>Nhánh này theo origin/feature/core và đang đi trước 3 commit "
			"(tính theo lần fetch cuối trên máy chủ).</p>"
		)
		self.assert_in_order(content, [branch, upstream, CORE_WARNING])
		self.assertNotIn(NO_UPSTREAM_NOTE, content)
		# NFR-8: the remote URL and its token appear 0 times in the comment, the proposal and the result
		stored_fields = json.dumps(doc.as_dict(), default=str, ensure_ascii=False)
		self.assertIn("origin/feature/core", stored_fields)
		for store, text in (
			("comment", content),
			("proposal", stored_fields),
			("result", json.dumps(result)),
		):
			for secret in (REMOTE_URL, "x-token-FAKE", "host/r.git"):
				with self.subTest(store=store, secret=secret):
					self.assertEqual(text.count(secret), 0)

	def test_non_core_app_comment_has_no_core_warning(self):
		# non-core app without an upstream
		alone = self.change(["x = 1"], ["x = 2"])
		self.assertTrue(alone["ok"], alone)
		self.assertEqual(
			tuple(self.stored(alone["proposal"]).get(field) for field in GIT_FIELDS), ("main", "", 0, 0)
		)
		content = self.comment_of(alone)
		branch = f"<p>Commit sẽ vào nhánh main của app {APP}.</p>"
		self.assert_in_order(content, [branch, NO_UPSTREAM_NOTE])
		self.assertNotIn(CORE_WARNING_START, content)

		# non-core app with an upstream
		self.sandbox.add_remote(APP, url=REMOTE_URL, ahead=1)
		tracked = self.change(["x = 1"], ["x = 2"])
		self.assertTrue(tracked["ok"], tracked)
		self.assertEqual(
			tuple(self.stored(tracked["proposal"]).get(field) for field in GIT_FIELDS),
			("main", "origin/main", 1, 0),
		)
		content = self.comment_of(tracked)
		upstream = (
			"<p>Nhánh này theo origin/main và đang đi trước 1 commit "
			"(tính theo lần fetch cuối trên máy chủ).</p>"
		)
		self.assert_in_order(content, [branch, upstream])
		self.assertNotIn(CORE_WARNING_START, content)
		self.assertNotIn(NO_UPSTREAM_NOTE, content)

	def test_tool_cannot_set_git_fields_or_commit_message(self):
		self.sandbox.switch_branch(APP, "feature/real")
		forged = {
			"target_branch": "forged-branch",
			"upstream_ref": REMOTE_URL,
			"ahead_count": 99,
			"is_core_app": 1,
			"commit_message": "forged message",
		}
		calls = {
			"propose_file_change": {"path": PATH, "find": ["x = 1"], "replace": ["x = 2"], "reason": "x"},
			"propose_new_file": {"path": f"{APP}/pkg/new_mod.txt", "content": "z = 1\n", "reason": "x"},
			"propose_bench_command": {"command": "build", "app": "frappe", "reason": "x"},
		}
		allowed = (APP, "frappe")
		# pinned: the schema refuses every extra key the model sends
		for name, arguments in calls.items():
			for key, value in forged.items():
				with self.subTest(tool=name, key=key):
					refused = self.run_tool(name, {**arguments, key: value}, allowed_apps=allowed)
					self.assertEqual(refused, {"ok": False, "reason": f"tham số không hợp lệ: {key}"})
		self.assertEqual(self.proposals(), [])

		# whatever reaches the handler, the git fields come from the guard and the message from the controller
		results = {
			name: getattr(propose_change, name)({**arguments, **forged}, self.context(allowed_apps=allowed))
			for name, arguments in calls.items()
		}
		for name, verb in (("propose_file_change", "sửa"), ("propose_new_file", "tạo")):
			with self.subTest(tool=name):
				result = results[name]
				self.assertEqual((result["ok"], result["branch"]), (True, "feature/real"), result)
				doc = self.stored(result["proposal"])
				self.assertEqual(tuple(doc.get(field) for field in GIT_FIELDS), ("feature/real", "", 0, 0))
				item_path = doc.operations[0].file_path
				self.assertEqual(
					doc.commit_message,
					f"erp_ai: áp dụng {doc.name} ({item_path})\n\n"
					f"Đề xuất: {doc.name}\nPhiếu: {self.ticket}\n{verb} {item_path}\nNgười duyệt: <người duyệt>\n"
					"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
				)
		# design 2.1: a bench command, even a build of core app frappe, has its 5 git fields empty / 0
		command = results["propose_bench_command"]
		self.assertTrue(command["ok"], command)
		self.assertNotIn("branch", command)
		doc = self.stored(command["proposal"])
		self.assertEqual(json.loads(doc.command_list), [["build", "--app", "frappe"]])
		self.assertEqual(
			(*(doc.get(field) for field in GIT_FIELDS), doc.commit_message or ""), ("", "", 0, 0, "")
		)
		for result in results.values():
			self.assertNotIn("forged", self.comment_of(result))
			self.assertNotIn("x-token-FAKE", self.comment_of(result))

	def test_bench_app_checked_by_check_bench_args_at_proposal_time(self):
		# "a;b" passes the list and the folder checks; only check_bench_args refuses it
		shell = self.bench("build", "a;b", allowed_apps=("a;b",))
		self.assertEqual(shell, {"ok": False, "reason": "đối số chứa ký tự điều khiển shell"})
		# an app of only spaces passes the schema (minLength 1) and counts as no app
		spaces = self.bench("build", "   ", allowed_apps=(APP, "   "))
		self.assertEqual(spaces, {"ok": False, "reason": "lệnh build cần app"})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])


class TestProposalAgentWriteGuard(FrappeTestCase):
	"""M5 (ADR-023 QĐ 5, valid path 2): the agent account creates proposals only through the propose tools."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.flags.pop, AGENT_WRITE_FLAG, None)
		frappe.set_user("Administrator")
		frappe.flags.pop(AGENT_WRITE_FLAG, None)
		if not frappe.db.exists("User", AGENT_USER):
			raise AssertionError(f"{AGENT_USER} does not exist on this site")
		# The agent account as the runner uses it: ERP AI Agent (create on proposals) and helpdesk Agent.
		pin_agent_roles(self)
		create_agent(BOSS)
		create_agent(GUARD_INSTRUCTOR)
		frappe.get_doc("User", GUARD_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		enqueue = patch("frappe.enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)
		self.sandbox = GitSandbox(self)
		self.sandbox.commit_file(APP, REL, BEFORE)
		self.ticket = str(make_ticket(subject="ERPAI-TEST propose guard").name)
		frappe.set_user(AGENT_USER)
		created = self.run_tool("propose_bench_command", BENCH_ARGUMENTS)
		self.assertTrue(created["ok"], created)
		self.existing = created["proposal"]

	def context(self):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L3",
			instructor=BOSS,
			run_id="run-propose-guard",
			category_mapping={},
			agent_user=AGENT_USER,
			change_enabled=True,
			allowed_apps=(APP,),
		)

	def run_tool(self, name, arguments):
		return execute_tool(name, arguments, self.context())

	def values(self) -> dict:
		return {
			"doctype": PROPOSAL_DOCTYPE,
			"ticket": self.ticket,
			"run_id": "run-propose-guard",
			"instructor": BOSS,
			"change_kind": CHANGE_KIND_COMMAND,
			"command_args": json.dumps(["migrate"]),
			"reversible": 0,
			"reason": "forged",
		}

	def snapshot(self) -> tuple:
		"""Every proposal row, as stored."""
		rows = frappe.db.sql("select * from `tabERP AI Change Proposal` order by name", as_dict=True)
		return tuple(tuple(sorted(row.items())) for row in rows)

	def assert_refused(self, write):
		"""Run `write` as the agent: refused by the guard, proposal rows unchanged; undone for the next path."""
		before = self.snapshot()
		frappe.db.savepoint(GUARD_SAVEPOINT)
		frappe.set_user(AGENT_USER)
		try:
			with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
				write()
			self.assertEqual(self.snapshot(), before)
		finally:
			frappe.set_user(AGENT_USER)
			frappe.db.rollback(save_point=GUARD_SAVEPOINT)

	def test_every_guarded_hook_refuses_the_agent(self):
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, self.existing)
		for hook in GUARDED_HOOKS:
			with self.subTest(hook=hook):
				with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
					doc.run_method(hook, *HOOK_ARGUMENTS.get(hook, ()))

	def test_before_insert_refuses_before_prepare_new(self):
		with patch.object(transitions, "prepare_new") as prepare_new:
			self.assert_refused(lambda: frappe.get_doc(self.values()).run_method("before_insert"))
		prepare_new.assert_not_called()

	def test_agent_cannot_insert_or_edit_proposal_outside_tool(self):
		def save_existing():
			doc = frappe.get_doc(PROPOSAL_DOCTYPE, self.existing)
			doc.change_status = CHANGE_STATUS_APPROVED
			doc.save(ignore_permissions=True)

		def savedocs_insert():
			doc = {**self.values(), "name": "new-erp-ai-change-proposal-1", "__islocal": 1}
			savedocs(frappe.as_json(doc), "Save")

		paths = {
			"direct insert": lambda: frappe.get_doc(self.values()).insert(ignore_permissions=True),
			"direct save": save_existing,
			"direct delete": lambda: frappe.delete_doc(
				PROPOSAL_DOCTYPE, self.existing, ignore_permissions=True
			),
			"rename": lambda: rename_doc(
				PROPOSAL_DOCTYPE, self.existing, f"{self.existing}-x", force=True, ignore_permissions=True
			),
			"client.insert JSON string": lambda: frappe.client.insert(
				json.dumps(self.values()).replace(json.dumps(PROPOSAL_DOCTYPE), f'"{PROPOSAL_ESCAPED}"')
			),
			"savedocs insert": savedocs_insert,
		}
		for path, write in paths.items():
			with self.subTest(path=path):
				self.assert_refused(write)

	def test_three_propose_tools_still_create_proposals_under_agent(self):
		results = {
			"propose_file_change": self.run_tool(
				"propose_file_change", {"path": PATH, "find": ["x = 1"], "replace": ["x = 2"], "reason": "r"}
			),
			"propose_new_file": self.run_tool(
				"propose_new_file", {"path": f"{APP}/pkg/new.txt", "content": "z = 1\n", "reason": "r"}
			),
			"propose_bench_command": self.run_tool("propose_bench_command", BENCH_ARGUMENTS),
		}
		for tool, result in results.items():
			with self.subTest(tool=tool):
				self.assertTrue(result["ok"], result)
				stored = frappe.db.get_value(
					PROPOSAL_DOCTYPE, result["proposal"], ["owner", "change_status"], as_dict=True
				)
				self.assertEqual((stored.owner, stored.change_status), (AGENT_USER, CHANGE_STATUS_PENDING))

	def test_instructor_can_still_approve_and_reject(self):
		to_reject = self.run_tool("propose_bench_command", BENCH_ARGUMENTS)["proposal"]
		to_undo = self.run_tool(
			"propose_file_change", {"path": PATH, "find": ["x = 1"], "replace": ["x = 2"], "reason": "r"}
		)["proposal"]
		frappe.db.set_value(PROPOSAL_DOCTYPE, to_undo, "change_status", CHANGE_STATUS_APPLIED)
		frappe.set_user(GUARD_INSTRUCTOR)
		self.assertEqual(controller.approve(self.existing)["status"], CHANGE_STATUS_APPROVED)
		self.assertEqual(controller.reject(to_reject)["status"], CHANGE_STATUS_REJECTED)
		self.assertEqual(controller.undo(to_undo)["status"], CHANGE_STATUS_UNDOING)
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value(PROPOSAL_DOCTYPE, self.existing, ["change_status", "decided_by"]),
			(CHANGE_STATUS_APPROVED, GUARD_INSTRUCTOR),
		)

	def test_flag_is_off_after_tool_returns(self):
		flag_during_insert, flag_during_comment = [], []
		prepare_new = transitions.prepare_new
		comment = propose_change._comment

		def record_insert(doc):
			flag_during_insert.append(frappe.flags.get(AGENT_WRITE_FLAG))
			return prepare_new(doc)

		def record_comment(ctx, proposal):
			flag_during_comment.append(frappe.flags.get(AGENT_WRITE_FLAG))
			return comment(ctx, proposal)

		with (
			patch.object(transitions, "prepare_new", side_effect=record_insert),
			patch.object(propose_change, "_comment", side_effect=record_comment),
		):
			self.assertTrue(self.run_tool("propose_bench_command", BENCH_ARGUMENTS)["ok"])
		# The opening covers exactly the tool's own insert, not the comment written after it.
		self.assertEqual((flag_during_insert, flag_during_comment), ([True], [None]))
		self.assertIsNone(frappe.flags.get(AGENT_WRITE_FLAG))
		self.assert_refused(lambda: frappe.get_doc(self.values()).insert(ignore_permissions=True))

	def test_flag_is_off_after_tool_raises(self):
		with patch.object(transitions, "prepare_new", side_effect=RuntimeError("boom")):
			with self.assertRaisesRegex(RuntimeError, "boom"):
				propose_change.propose_bench_command(BENCH_ARGUMENTS, self.context())
		self.assertIsNone(frappe.flags.get(AGENT_WRITE_FLAG))
		self.assert_refused(lambda: frappe.get_doc(self.values()).insert(ignore_permissions=True))


class TestProposeBlock(FrappeTestCase):
	"""CHG-002 T26: `_propose_block` for `edit` and `create` items (design 3.1, 4.1 steps 1-4)."""

	setUp = TestProposeChange.setUp
	context = TestProposeChange.context
	run_tool = TestProposeChange.run_tool
	change = TestProposeChange.change
	proposals = TestProposeChange.proposals
	comments = TestProposeChange.comments
	git_snapshot = TestProposeChange.git_snapshot

	def block(self, changes, **context):
		return self.run_tool("propose_file_change", {"changes": changes, "reason": "khối"}, **context)

	def create(self, path, content="a\n", **context):
		arguments = {"path": path, "content": content, "reason": "r"}
		return self.run_tool("propose_new_file", arguments, **context)

	def stored(self, result):
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		frappe.set_user(AGENT)
		return doc

	def assert_refused_whole(self, result, reason, snapshot):
		self.assertEqual(result, {"ok": False, "reason": reason})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])
		self.assertEqual(self.git_snapshot(), snapshot)

	def test_block_shape_sentence_and_removed_constants(self):
		shape = "đưa changes hoặc path, không cả hai và không thiếu cả hai"
		self.assertEqual(propose_change.BLOCK_SHAPE, shape)
		self.assertEqual(propose_change.NOT_UTF8, "file không phải văn bản UTF-8")
		for gone in ("NO_PARENT", "PROPOSAL_FILE_MAX_BYTES", "TOO_LARGE"):
			with self.subTest(name=gone):
				self.assertFalse(hasattr(propose_change, gone))

	def test_file_over_two_mib_refused_names_2_mib(self):
		self.sandbox.commit_file(APP, "pkg/big.txt", "a" * (2 * 1024 * 1024 - 1) + "\nb")
		snapshot = self.git_snapshot()
		result = self.change(["b"], ["c"], f"{APP}/pkg/big.txt")
		self.assert_refused_whole(result, f"mục 1 ({APP}/pkg/big.txt): file lớn hơn 2 MiB", snapshot)

	def test_edit_and_create_block_one_proposal_rows_in_order(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "một\nhai\n")
		snapshot = self.git_snapshot()
		changes = [
			{"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["hai"], "replace": ["ba"]},
			{"action": "create", "path": f"{APP}/pkg/new/b.md", "content": "# b\n"},
		]
		with patch.object(change_guard, "check_block", wraps=change_guard.check_block) as check_block:
			result = self.block(changes)
		self.assertEqual(set(result), {"ok", "proposal", "status", "comment", "branch"})
		self.assertTrue(result["ok"])
		self.assertEqual(self.proposals(), [result["proposal"]])
		self.assertEqual(len(self.comments()), 1)
		doc = self.stored(result)
		rows = [
			(
				row.idx,
				row.operation,
				row.file_path,
				row.content_before,
				row.content_after,
				row.base_hash,
				row.after_hash,
			)
			for row in doc.operations
		]
		self.assertEqual(
			rows,
			[
				(
					1,
					"Sửa",
					f"{APP}/pkg/a.txt",
					"một\nhai\n",
					"một\nba\n",
					_sha("một\nhai\n"),
					_sha("một\nba\n"),
				),
				(2, "Tạo", f"{APP}/pkg/new/b.md", None, "# b\n", None, _sha("# b\n")),
			],
		)
		expected_diff = (
			f"--- a/{APP}/pkg/a.txt\n+++ b/{APP}/pkg/a.txt\n@@ -1,2 +1,2 @@\n một\n-hai\n+ba\n"
			f"--- a/{APP}/pkg/new/b.md\n+++ b/{APP}/pkg/new/b.md\n@@ -0,0 +1 @@\n+# b\n"
		)
		self.assertEqual(doc.diff, expected_diff)
		# design-addendum-1 A-1.5: the bytes counted by `check_block` are the bytes stored.
		self.assertEqual(check_block.call_count, 1)
		self.assertEqual(check_block.call_args.kwargs["diff_text"], doc.diff)
		self.assertIs(check_block.call_args.kwargs["at_apply"], False)
		self.assertEqual(
			(doc.change_kind, doc.app, doc.reversible, doc.change_status),
			(CHANGE_KIND_CODE, APP, 1, CHANGE_STATUS_PENDING),
		)
		self.assertFalse(doc.file_path or doc.content_before or doc.content_after or doc.base_hash)
		self.assertEqual(result["branch"], doc.target_branch)
		self.assertEqual(self.git_snapshot(), snapshot)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "pkg/new")))

	def test_legacy_call_shape_is_one_edit_item(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "x = 1\n")
		result = self.change(["x = 1"], ["x = 2"], f"{APP}/pkg/a.txt")
		self.assertTrue(result["ok"], result)
		doc = self.stored(result)
		self.assertEqual(
			[(row.operation, row.file_path, row.content_after) for row in doc.operations],
			[("Sửa", f"{APP}/pkg/a.txt", "x = 2\n")],
		)
		expected_diff = f"--- a/{APP}/pkg/a.txt\n+++ b/{APP}/pkg/a.txt\n@@ -1 +1 @@\n-x = 1\n+x = 2\n"
		self.assertEqual(doc.diff, expected_diff)
		self.assertFalse(doc.file_path)

	def test_changes_and_path_together_refused(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "x = 1\n")
		snapshot = self.git_snapshot()
		item = {"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["1"], "replace": ["2"]}
		arguments = {"changes": [item], "path": f"{APP}/pkg/a.txt", "reason": "r"}
		result = self.run_tool("propose_file_change", arguments)
		self.assert_refused_whole(result, change_guard.BLOCK_SHAPE, snapshot)

	def test_create_in_new_three_level_dir_ok(self):
		snapshot = self.git_snapshot()
		result = self.create(f"{APP}/a/b/c/x.txt", "x\n")
		self.assertTrue(result["ok"], result)
		doc = self.stored(result)
		self.assertEqual(
			[(row.operation, row.file_path) for row in doc.operations], [("Tạo", f"{APP}/a/b/c/x.txt")]
		)
		self.assertEqual(self.git_snapshot(), snapshot)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "a")))

	def test_text_files_any_extension_created(self):
		cases = {
			"x.txt": "t\n",
			"x.md": "# x\n",
			"x.js": "let a;\n",
			"x.json": "{}\n",
			"x.csv": "a,b\n",
			"Makefile": "a:\n",
			"x.yml": "a: 1\n",
			"x.yaml": "a: 1\n",
			"x.toml": "a = 1\n",
			"x.po": 'msgid "a"\n',
			"x.sql": "select 1;\n",
			"x.scss": "a { b: c; }\n",
			"x.ts": "let a: number;\n",
			"x.xml": "<a/>\n",
		}
		for name, content in cases.items():
			with self.subTest(name=name):
				result = self.create(f"{APP}/pkg/{name}", content)
				self.assertTrue(result["ok"], result)
				self.assertEqual(self.stored(result).operations[0].content_after or "", content)
		# empty content is allowed by the handler too (the schema path: test_new_file_20001_chars_accepted)
		arguments = {"path": f"{APP}/pkg/empty.md", "content": "", "reason": "r"}
		empty = propose_change.propose_new_file(arguments, self.context())
		self.assertTrue(empty["ok"], empty)
		self.assertEqual(self.stored(empty).operations[0].content_after or "", "")
		self.assertEqual(len(self.proposals()), len(cases) + 1)

	def test_binary_png_pyc_refused(self):
		self.sandbox.commit_file(APP, "pkg/img.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
		self.sandbox.commit_file(APP, "pkg/old.pyc", b"\xa7\r\r\n\x00\x00\x00\x00")
		self.sandbox.commit_file(APP, "pkg/latin1.txt", b"x = '\xe9'\n")
		snapshot = self.git_snapshot()
		cases = (
			("pkg/img.png", "file có byte NUL, không phải văn bản"),
			("pkg/old.pyc", "file có byte NUL, không phải văn bản"),
			("pkg/latin1.txt", "file không phải văn bản UTF-8"),
		)
		for rel, reason in cases:
			with self.subTest(rel=rel):
				result = self.change(["x"], ["y"], f"{APP}/{rel}")
				self.assert_refused_whole(result, f"mục 1 ({APP}/{rel}): {reason}", snapshot)

	def test_create_with_nul_refused(self):
		snapshot = self.git_snapshot()
		result = self.create(f"{APP}/pkg/x.txt", "a\0b")
		reason = f"mục 1 ({APP}/pkg/x.txt): file có byte NUL, không phải văn bản"
		self.assert_refused_whole(result, reason, snapshot)

	def test_pem_key_gitignore_refused(self):
		snapshot = self.git_snapshot()
		cases = (
			("pkg/server.pem", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			("pkg/id.key", "tên file thuộc loại bí mật hoặc được bảo vệ"),
			("pkg/.gitignore", change_guard.GIT_DIR),
		)
		for rel, reason in cases:
			with self.subTest(rel=rel):
				result = self.create(f"{APP}/{rel}", "a\n")
				self.assert_refused_whole(result, f"mục 1 ({APP}/{rel}): {reason}", snapshot)

	def test_two_apps_refused_names_both_zero_proposals(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		self.sandbox.commit_file("hrms", "pkg/b.txt", "b\n")
		snapshot = self.git_snapshot()
		changes = [
			{"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["a"], "replace": ["c"]},
			{"action": "edit", "path": "hrms/pkg/b.txt", "find": ["b"], "replace": ["c"]},
		]
		result = self.block(changes, allowed_apps=(APP, "hrms"))
		reason = f"mục 2 (hrms/pkg/b.txt): các mục file thuộc hai app {APP} và hrms; mỗi app một đề xuất"
		self.assert_refused_whole(result, reason, snapshot)

	def test_py_without_commands_refused_until_commands_exist(self):
		# R-5: a .py item needs migrate then restart; the tool takes no `commands` before T28
		self.sandbox.commit_file(APP, "pkg/mod.py", BEFORE)
		snapshot = self.git_snapshot()
		item = {"action": "edit", "path": f"{APP}/pkg/mod.py", "find": ["x = 1"], "replace": ["x = 2"]}
		results = {
			"legacy edit": self.change(["x = 1"], ["x = 2"], f"{APP}/pkg/mod.py"),
			"legacy create": self.create(f"{APP}/pkg/new_mod.py", "z = 1\n"),
			"changes": self.block([item]),
		}
		for shape, result in results.items():
			with self.subTest(shape=shape):
				self.assert_refused_whole(result, change_guard.PY_NEEDS_RESTART, snapshot)

	def test_refusal_makes_zero_proposals_zero_comments(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		snapshot = self.git_snapshot()
		good = {"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["a"], "replace": ["b"]}
		cases = (
			(
				{"action": "edit", "path": f"{APP}/pkg/none.txt", "find": ["a"], "replace": ["b"]},
				f"mục 2 ({APP}/pkg/none.txt): file không tồn tại",
			),
			(good, f"mục 2 ({APP}/pkg/a.txt): " + change_guard.BLOCK_PATH_TWICE),
			(
				{"action": "create", "path": PATH, "content": "a\n"},
				f"mục 2 ({PATH}): file đã tồn tại",
			),
			(
				{"action": "create", "path": f"{APP}/pkg/b.txt"},
				f"mục 2 ({APP}/pkg/b.txt): mục create thiếu hoặc thừa trường",
			),
			(
				{"action": "edit", "path": f"{APP}/pkg/c.txt", "content": "a"},
				f"mục 2 ({APP}/pkg/c.txt): mục edit thiếu hoặc thừa trường",
			),
			(
				{"action": "move", "path": f"{APP}/pkg/c.txt"},
				f"mục 2 ({APP}/pkg/c.txt): " + change_guard.OP_UNKNOWN,
			),
			(
				{"action": "edit", "path": PATH, "find": ["zzz"], "replace": ["b"]},
				f"mục 2 ({PATH}): đoạn find[0] không có trong file",
			),
			(
				{"action": "edit", "path": PATH, "find": ["x = 1"], "replace": ["x = 1"]},
				f"mục 2 ({PATH}): nội dung sau trùng nội dung trước",
			),
			(
				{"action": "create", "path": f"{APP}/pkg/n.py", "content": "a = 1\n"},
				change_guard.PY_NEEDS_RESTART,
			),
			(
				{"action": "create", "path": f"{APP}/pkg/n.json", "content": "{"},
				f"mục 2 ({APP}/pkg/n.json): file .json không phải JSON hợp lệ: dòng 1",
			),
		)
		for second, reason in cases:
			with self.subTest(reason=reason):
				self.assert_refused_whole(self.block([good, second]), reason, snapshot)
		self.assert_refused_whole(self.block([]), change_guard.BLOCK_EMPTY, snapshot)

	# CHG-002 T27: `delete` and `rename` items (design 3.1, 4.1 step 2; R-7, R-8, D-8).

	def test_five_item_block_makes_one_pending_proposal_one_comment_three_links(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "một\nhai\n")
		self.sandbox.commit_file(APP, "pkg/d.txt", "xóa\n")
		self.sandbox.commit_file(APP, "pkg/r.txt", "giữ\n")
		snapshot = self.git_snapshot()
		changes = [
			{"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["hai"], "replace": ["ba"]},
			{"action": "create", "path": f"{APP}/pkg/n.md", "content": "n\n"},
			{"action": "delete", "path": f"{APP}/pkg/d.txt"},
			{"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/doc/r.txt"},
			{"action": "create", "path": f"{APP}/doc/sub/x.yaml", "content": "a: 1\n"},
		]
		with patch.object(change_guard, "check_block", wraps=change_guard.check_block) as check_block:
			result = self.block(changes)
		self.assertTrue(result["ok"], result)
		self.assertEqual(self.proposals(), [result["proposal"]])
		doc = self.stored(result)
		rows = [
			(row.idx, row.operation, row.file_path, row.new_path, row.content_before, row.content_after)
			for row in doc.operations
		]
		self.assertEqual(
			rows,
			[
				(1, "Sửa", f"{APP}/pkg/a.txt", None, "một\nhai\n", "một\nba\n"),
				(2, "Tạo", f"{APP}/pkg/n.md", None, None, "n\n"),
				(3, "Xóa", f"{APP}/pkg/d.txt", None, "xóa\n", None),
				(4, "Đổi tên", f"{APP}/pkg/r.txt", f"{APP}/doc/r.txt", "giữ\n", "giữ\n"),
				(5, "Tạo", f"{APP}/doc/sub/x.yaml", None, None, "a: 1\n"),
			],
		)
		hashes = [(row.base_hash, row.after_hash) for row in doc.operations[2:4]]
		self.assertEqual(hashes, [(_sha("xóa\n"), None), (_sha("giữ\n"), _sha("giữ\n"))])
		expected_diff = (
			f"--- a/{APP}/pkg/a.txt\n+++ b/{APP}/pkg/a.txt\n@@ -1,2 +1,2 @@\n một\n-hai\n+ba\n"
			f"--- a/{APP}/pkg/n.md\n+++ b/{APP}/pkg/n.md\n@@ -0,0 +1 @@\n+n\n"
			f"--- a/{APP}/pkg/d.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-xóa\n"
			f"rename from {APP}/pkg/r.txt\nrename to {APP}/doc/r.txt\n"
			f"--- a/{APP}/doc/sub/x.yaml\n+++ b/{APP}/doc/sub/x.yaml\n@@ -0,0 +1 @@\n+a: 1\n"
		)
		self.assertEqual(doc.diff, expected_diff)
		self.assertEqual(check_block.call_args.kwargs["diff_text"], doc.diff)
		self.assertEqual(doc.change_status, CHANGE_STATUS_PENDING)
		(comment,) = self.comments()
		links = re.findall(r'<a href="([^"]+)"', comment["content"])
		decisions = [
			change_link.decision_path(doc.name, action)
			for action in (change_link.ACTION_APPROVE, change_link.ACTION_REJECT)
		]
		form = f"/app/erp-ai-change-proposal/{doc.name}"
		self.assertEqual(links[1:], [frappe.utils.escape_html(path) for path in (*decisions, form)])
		self.assertEqual(self.git_snapshot(), snapshot)
		self.assertTrue(os.path.isfile(os.path.join(self.sandbox.repo(APP), "pkg/d.txt")))
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "doc")))

	def test_ten_item_block(self):
		for number in range(5):
			self.sandbox.commit_file(APP, f"pkg/f{number}.txt", f"{number}\n")
		snapshot = self.git_snapshot()
		changes = [
			{"action": "delete", "path": f"{APP}/pkg/f0.txt"},
			{"action": "delete", "path": f"{APP}/pkg/f1.txt"},
			{"action": "rename", "path": f"{APP}/pkg/f2.txt", "new_path": f"{APP}/pkg/g2.txt"},
			{"action": "rename", "path": f"{APP}/pkg/f3.txt", "new_path": f"{APP}/pkg/g3.txt"},
			{"action": "edit", "path": f"{APP}/pkg/f4.txt", "find": ["4"], "replace": ["5"]},
			*(
				{"action": "create", "path": f"{APP}/pkg/c{number}.md", "content": "c\n"}
				for number in range(5)
			),
		]
		result = self.block(changes)
		self.assertTrue(result["ok"], result)
		self.assertEqual(self.proposals(), [result["proposal"]])
		self.assertEqual(len(self.comments()), 1)
		operations = [row.operation for row in self.stored(result).operations]
		self.assertEqual(operations, ["Xóa", "Xóa", "Đổi tên", "Đổi tên", "Sửa", *["Tạo"] * 5])
		self.assertEqual(self.git_snapshot(), snapshot)

	def assert_item_refused(self, item, reason, number=1, **context):
		snapshot = self.git_snapshot()
		result = self.block([item], **context)
		self.assert_refused_whole(result, f"mục {number} ({item['path']}): {reason}", snapshot)

	def test_delete_directory_refused(self):
		self.sandbox.commit_file(APP, "pkg/dir/a.txt", "a\n")
		item = {"action": "delete", "path": f"{APP}/pkg/dir"}
		self.assert_item_refused(item, change_guard.NOT_REGULAR_FILE)

	def test_delete_missing_refused(self):
		item = {"action": "delete", "path": f"{APP}/pkg/none.txt"}
		self.assert_item_refused(item, change_guard.NOT_REGULAR_FILE)

	def test_delete_dirty_refused(self):
		self.sandbox.commit_file(APP, "pkg/d.txt", "d\n")
		self.sandbox.write_unstaged(APP, "pkg/d.txt", "e\n")
		item = {"action": "delete", "path": f"{APP}/pkg/d.txt"}
		self.assert_item_refused(item, source.GIT_DIRTY)

	def test_delete_untracked_refused(self):
		self.sandbox.write_unstaged(APP, "pkg/u.txt", "u\n")
		item = {"action": "delete", "path": f"{APP}/pkg/u.txt"}
		self.assert_item_refused(item, source.GIT_DIRTY)

	def test_delete_binary_refused(self):
		self.sandbox.commit_file(APP, "pkg/img.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
		item = {"action": "delete", "path": f"{APP}/pkg/img.png"}
		self.assert_item_refused(item, "file có byte NUL, không phải văn bản")

	def test_delete_executable_refused(self):
		self.sandbox.commit_file(APP, "pkg/run.sh", "echo a\n")
		os.chmod(os.path.join(self.sandbox.repo(APP), "pkg/run.sh"), 0o744)
		for item in (
			{"action": "delete", "path": f"{APP}/pkg/run.sh"},
			{"action": "rename", "path": f"{APP}/pkg/run.sh", "new_path": f"{APP}/pkg/go.sh"},
		):
			with self.subTest(action=item["action"]):
				self.assert_item_refused(item, change_guard.EXECUTABLE_FILE)

	def test_delete_symlink_refused(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		os.symlink("a.txt", os.path.join(self.sandbox.repo(APP), "pkg/link.txt"))
		for item in (
			{"action": "delete", "path": f"{APP}/pkg/link.txt"},
			{"action": "rename", "path": f"{APP}/pkg/link.txt", "new_path": f"{APP}/pkg/moved.txt"},
		):
			with self.subTest(action=item["action"]):
				self.assert_item_refused(item, change_guard.PATH_SYMLINK)
		self.assertTrue(os.path.islink(os.path.join(self.sandbox.repo(APP), "pkg/link.txt")))

	def test_symlink_past_guard_is_not_regular_file(self):
		"""design-addendum-8 A8-4: the `islink` branch of `_removed_text` refuses a symlink the guard let by."""
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		link = os.path.join(self.sandbox.repo(APP), "pkg/link.txt")
		os.symlink("a.txt", link)
		rel = f"{APP}/pkg/link.txt"
		real = change_guard.check_write_path

		def guard(path, *args, **kwargs):
			# only the step-2 read of `_removed_text`; `check_block` keeps the real guard
			if path == rel and kwargs.get("read_git") is False:
				return change_guard.GuardResult(full_path=link, rel_path=rel, app=APP, reason=None)
			return real(path, *args, **kwargs)

		with patch.object(change_guard, "check_write_path", side_effect=guard):
			self.assert_item_refused({"action": "delete", "path": rel}, change_guard.NOT_REGULAR_FILE)
		self.assertTrue(os.path.islink(link))

	def test_rename_dest_exists_refused(self):
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		self.sandbox.commit_file(APP, "pkg/s.txt", "s\n")
		item = {"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/pkg/s.txt"}
		self.assert_item_refused(item, propose_change.EXISTS)

	def test_rename_source_missing_refused(self):
		item = {"action": "rename", "path": f"{APP}/pkg/none.txt", "new_path": f"{APP}/pkg/s.txt"}
		self.assert_item_refused(item, change_guard.NOT_REGULAR_FILE)

	def test_rename_across_apps_refused(self):
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		self.sandbox.commit_file("hrms", "pkg/b.txt", "b\n")
		item = {"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": "hrms/pkg/r.txt"}
		reason = change_guard.BLOCK_TWO_APPS.format(a=APP, b="hrms")
		self.assert_item_refused(item, reason, allowed_apps=(APP, "hrms"))

	def test_rename_end_in_ring_refused(self):
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		item = {"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": "erp_ai/r.txt"}
		self.assert_item_refused(item, change_guard.APP_FORBIDDEN, allowed_apps=(APP, "erp_ai"))

	def test_nine_valid_plus_one_erp_ai_refused_whole(self):
		self.sandbox.commit_file(APP, "pkg/d.txt", "d\n")
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		snapshot = self.git_snapshot()
		changes = [
			{"action": "delete", "path": f"{APP}/pkg/d.txt"},
			{"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/pkg/s.txt"},
			*(
				{"action": "create", "path": f"{APP}/pkg/c{number}.md", "content": "c\n"}
				for number in range(7)
			),
			{"action": "create", "path": "erp_ai/x.md", "content": "x\n"},
		]
		result = self.block(changes, allowed_apps=(APP, "erp_ai"))
		reason = f"mục 10 (erp_ai/x.md): {change_guard.APP_FORBIDDEN}"
		self.assert_refused_whole(result, reason, snapshot)

	def test_create_under_a_parent_that_is_a_file_refused(self):
		self.sandbox.commit_file(APP, "README.md", "r\n")
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		for item in (
			{"action": "create", "path": f"{APP}/README.md/x.txt", "content": "x\n"},
			{"action": "create", "path": f"{APP}/README.md/sub/x.txt", "content": "x\n"},
			{"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/README.md/r.txt"},
		):
			with self.subTest(item=item):
				self.assert_item_refused(item, propose_change.PARENT_NOT_DIR)
		self.assertEqual(propose_change.PARENT_NOT_DIR, "thư mục cha trên đường dẫn là một file")
		self.assertTrue(os.path.isfile(os.path.join(self.sandbox.repo(APP), "README.md")))

	# CHG-002 T28: commands in a block; the three tools go through `_propose_block`.

	def tree(self):
		"""Every file under the sandbox `apps/` (outside `.git`) with its bytes."""
		root = os.path.dirname(self.sandbox.repo(APP))
		files = {}
		for folder, dirs, names in os.walk(root):
			dirs[:] = [name for name in dirs if name != ".git"]
			for name in names:
				full = os.path.join(folder, name)
				with open(full, "rb") as handle:
					files[os.path.relpath(full, root)] = handle.read()
		return files

	def test_py_block_with_migrate_restart_stored_in_order(self):
		self.sandbox.commit_file(APP, "pkg/mod.py", "x = 1\n")
		site = frappe.local.site
		migrate, build, restart = (
			{"command": "migrate"},
			{"command": "build", "app": APP},
			{"command": "restart"},
		)
		item = {"action": "edit", "path": f"{APP}/pkg/mod.py", "find": ["x = 1"], "replace": ["x = 2"]}
		calls = {
			"changes": ("propose_file_change", {"changes": [item], "commands": [migrate, build, restart]}),
			"legacy edit": (
				"propose_file_change",
				{
					"path": item["path"],
					"find": ["x = 1"],
					"replace": ["x = 3"],
					"commands": [build, migrate, restart],
				},
			),
			"new file": (
				"propose_new_file",
				{"path": f"{APP}/pkg/new_mod.py", "content": "z = 1\n", "commands": [migrate, restart]},
			),
		}
		expected = {
			"changes": [["--site", site, "migrate"], ["build", "--app", APP], ["restart"]],
			"legacy edit": [["build", "--app", APP], ["--site", site, "migrate"], ["restart"]],
			"new file": [["--site", site, "migrate"], ["restart"]],
		}
		for shape, (tool, arguments) in calls.items():
			with self.subTest(shape=shape):
				result = self.run_tool(tool, {**arguments, "reason": "r"})
				self.assertTrue(result["ok"], result)
				doc = self.stored(result)
				self.assertEqual(json.loads(doc.command_list), expected[shape])
				self.assertEqual(
					(doc.change_kind, doc.reversible, doc.app, len(doc.operations)),
					(CHANGE_KIND_CODE, 1, APP, 1),
				)

	def test_py_block_without_restart_refused(self):
		self.sandbox.commit_file(APP, "pkg/mod.py", "x = 1\n")
		snapshot = self.git_snapshot()
		item = {"action": "edit", "path": f"{APP}/pkg/mod.py", "find": ["x = 1"], "replace": ["x = 2"]}
		for commands in ([{"command": "migrate"}], [{"command": "migrate"}, {"command": "version"}]):
			with self.subTest(commands=commands):
				result = self.run_tool(
					"propose_file_change", {"changes": [item], "commands": commands, "reason": "r"}
				)
				self.assert_refused_whole(result, change_guard.PY_NEEDS_RESTART, snapshot)

	def test_command_only_block_has_no_branch(self):
		snapshot = self.git_snapshot()
		result = self.run_tool("propose_bench_command", {"command": "build", "app": APP, "reason": "r"})
		self.assertEqual(set(result), {"ok", "proposal", "status", "comment"}, result)
		doc = self.stored(result)
		self.assertEqual(json.loads(doc.command_list), [["build", "--app", APP]])
		self.assertEqual(
			(doc.change_kind, doc.reversible, doc.app, len(doc.operations), doc.command_args or ""),
			(CHANGE_KIND_COMMAND, 0, APP, 0, ""),
		)
		self.assertEqual(
			(doc.target_branch, doc.upstream_ref, doc.ahead_count, doc.is_core_app), ("", "", 0, 0)
		)
		migrate = self.stored(self.run_tool("propose_bench_command", {"command": "migrate", "reason": "r"}))
		self.assertEqual(
			(migrate.app or "", json.loads(migrate.command_list)),
			("", [["--site", frappe.local.site, "migrate"]]),
		)
		self.assertEqual(self.git_snapshot(), snapshot)

	def test_bench_command_restart_plain_ok(self):
		(spec,) = [spec for spec in propose_change.TOOLS if spec.name == "propose_bench_command"]
		self.assertIn(
			change_guard.RESTART_COMMAND, spec.schema["input_schema"]["properties"]["command"]["enum"]
		)
		self.assertFalse(hasattr(propose_change, "_SINGLE_BENCH_COMMANDS"))
		through_tool = self.run_tool("propose_bench_command", {"command": "restart", "reason": "r"})
		direct = propose_change.propose_bench_command({"command": "restart", "reason": "r"}, self.context())
		for result in (through_tool, direct):
			with self.subTest(result=result):
				self.assertEqual((result["ok"], result["status"]), (True, CHANGE_STATUS_PENDING), result)
				doc = self.stored(result)
				self.assertEqual((json.loads(doc.command_list), doc.reversible), ([["restart"]], 0))
		self.assertEqual(len(self.proposals()), 2)

	def test_new_file_20001_chars_accepted(self):
		# design 3.1 / 2.5: `content` has no minLength / maxLength (AC-43 case 1); empty is `__init__.py`
		for content in ("x" * 20001 + "\n", ""):
			with self.subTest(length=len(content)):
				path = f"{APP}/pkg/big_{len(content)}.txt"
				result = self.run_tool("propose_new_file", {"path": path, "content": content, "reason": "r"})
				self.assertTrue(result["ok"], result)
				self.assertEqual(self.stored(result).operations[0].content_after or "", content)
		self.assertEqual(len(self.proposals()), 2)

	def test_new_file_description_tells_parent_and_commands_rules(self):
		# design 3.1: the parent folder may be missing (no NO_PARENT); commands as in propose_file_change
		(spec,) = [spec for spec in propose_change.TOOLS if spec.name == "propose_new_file"]
		description = spec.schema["description"]
		self.assertNotIn("phải có sẵn", description)
		self.assertIn("thư mục cha chưa có sẽ được tạo", description)
		self.assertIn("commands là các lệnh bench chạy sau khi ghi file, đúng thứ tự", description)
		self.assertIn("có file .py thì kết thúc bằng migrate rồi restart", description)

	def test_edit_with_11_replacements_accepted(self):
		# design 3.1: no limit on the number of edits in one item (AC-43 case 2), in both call shapes
		before = "".join(f"v{i} = {i}\n" for i in range(11))
		find = [f"v{i} = {i}" for i in range(11)]
		replace = [f"v{i} = {i + 100}" for i in range(11)]
		after = "".join(f"v{i} = {i + 100}\n" for i in range(11))
		shapes = {
			"changes": lambda path: {
				"changes": [{"action": "edit", "path": path, "find": find, "replace": replace}],
				"reason": "r",
			},
			"legacy edit": lambda path: {"path": path, "find": find, "replace": replace, "reason": "r"},
		}
		for number, (shape, arguments) in enumerate(shapes.items()):
			with self.subTest(shape=shape):
				self.sandbox.commit_file(APP, f"pkg/many_{number}.txt", before)
				result = self.run_tool("propose_file_change", arguments(f"{APP}/pkg/many_{number}.txt"))
				self.assertTrue(result["ok"], result)
				self.assertEqual(self.stored(result).operations[0].content_after, after)

	def test_schema_matches_design_table(self):
		schemas = {spec.name: spec.schema["input_schema"] for spec in propose_change.TOOLS}
		self.assertEqual(list(schemas), TOOL_NAMES)
		change, new_file, bench = (schemas[name] for name in TOOL_NAMES)
		self.assertEqual(
			(change["required"], new_file["required"], bench["required"]),
			(["reason"], ["path", "content", "reason"], ["command", "reason"]),
		)
		changes = change["properties"]["changes"]
		self.assertEqual((changes.get("minItems"), changes.get("maxItems")), (1, CHANGE_MAX_FILE_OPS))
		for commands in (change["properties"]["commands"], new_file["properties"]["commands"]):
			self.assertEqual(
				(commands.get("minItems"), commands.get("maxItems")), (None, CHANGE_MAX_COMMANDS)
			)
		for key in ("find", "replace"):
			array = change["properties"][key]
			with self.subTest(key=key):
				self.assertEqual((array.get("maxItems"), array["items"].get("maxLength")), (None, None))
		content = new_file["properties"]["content"]
		self.assertEqual((content.get("minLength"), content.get("maxLength")), (None, None))
		self.assertIn(change_guard.RESTART_COMMAND, bench["properties"]["command"]["enum"])
		self.assertEqual(propose_change.EDIT_SHAPE, "find và replace phải cùng số phần tử, ít nhất 1")
		self.assertEqual(
			[hasattr(constants, name) for name in ("PROPOSAL_TEXT_MAX_CHARS", "REPLACE_MAX_ITEMS")],
			[False, False],
		)
		# the registry checks maxItems before the handler (51 items, 7 commands); it does not check
		# minItems, so an empty block reaches check_block and gets BLOCK_EMPTY
		self.assertEqual(
			self.run_tool("propose_file_change", {"changes": [], "reason": "r"}),
			{"ok": False, "reason": change_guard.BLOCK_EMPTY},
		)
		item = {"action": "delete", "path": f"{APP}/pkg/a.txt"}
		for arguments, key in (
			({"changes": [item] * (CHANGE_MAX_FILE_OPS + 1), "reason": "r"}, "changes"),
			({"changes": [item], "commands": [{"command": "version"}] * 7, "reason": "r"}, "commands"),
		):
			with self.subTest(key=key, size=len(arguments[key])):
				self.assertEqual(
					self.run_tool("propose_file_change", arguments),
					{"ok": False, "reason": f"tham số không hợp lệ: {key}"},
				)
		self.assertEqual(len(self.proposals()), 0)

	def test_denied_command_refused_names_command(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		snapshot = self.git_snapshot()
		item = {"action": "edit", "path": f"{APP}/pkg/a.txt", "find": ["a"], "replace": ["b"]}
		cases = (
			(
				[{"command": "version"}, {"command": "update"}],
				"lệnh 2: lệnh không có trong danh sách cho phép",
			),
			([{"command": "build", "app": "helpdesk"}], "lệnh 1: app không có trong danh sách được sửa"),
			([{"command": "version"}, {"command": "build"}], "lệnh 2: lệnh build cần app"),
			([{"command": "migrate", "app": APP}], "lệnh 1: lệnh này không nhận app"),
			([{"command": "version", "extra": 1}], "tham số không hợp lệ: commands"),
			([{"app": APP}], "tham số không hợp lệ: commands"),
			(["version"], "tham số không hợp lệ: commands"),
			({"command": "version"}, "tham số không hợp lệ: commands"),
		)
		for commands, reason in cases:
			with self.subTest(commands=commands):
				arguments = {"changes": [item], "commands": commands, "reason": "r"}
				direct = propose_change.propose_file_change(arguments, self.context())
				self.assert_refused_whole(direct, reason, snapshot)
		new_file = {
			"path": f"{APP}/pkg/n.txt",
			"content": "n\n",
			"commands": [{"command": "update"}],
			"reason": "r",
		}
		refused = propose_change.propose_new_file(new_file, self.context())
		self.assert_refused_whole(refused, "lệnh 1: lệnh không có trong danh sách cho phép", snapshot)

	def test_no_effect_before_approval_tree_head_process_restart_stubs_unchanged(self):
		self.sandbox.commit_file(APP, "pkg/a.py", "a = 1\n")
		self.sandbox.commit_file(APP, "pkg/d.txt", "d\n")
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		snapshot, tree = self.git_snapshot(), self.tree()
		changes = [
			{"action": "edit", "path": f"{APP}/pkg/a.py", "find": ["a = 1"], "replace": ["a = 2"]},
			{"action": "create", "path": f"{APP}/pkg/new/n.py", "content": "n = 1\n"},
			{"action": "delete", "path": f"{APP}/pkg/d.txt"},
			{"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/doc/r.txt"},
		]
		commands = [{"command": "migrate"}, {"command": "build", "app": APP}, {"command": "restart"}]
		with (
			patch.object(process_runner, "run_bench") as run_bench,
			patch.object(process_runner, "launch_restart") as launch_restart,
			# proposal time reads git (rev-parse, status); it must never start anything else
			patch("subprocess.Popen", wraps=subprocess.Popen) as popen,
		):
			block = self.run_tool(
				"propose_file_change", {"changes": changes, "commands": commands, "reason": "r"}
			)
			alone = self.run_tool("propose_bench_command", {"command": "restart", "reason": "r"})
		self.assertTrue(block["ok"], block)
		self.assertTrue(alone["ok"], alone)
		self.assertEqual([len(self.stored(block).operations), len(self.proposals())], [4, 2])
		self.assertEqual((run_bench.call_count, launch_restart.call_count), (0, 0))
		# git reads run as `timeout -s KILL <s> git ...`; anything that is not git (bench, setsid) is an effect
		argvs = [[os.path.basename(str(part)) for part in call.args[0]] for call in popen.call_args_list]
		self.assertEqual(([argv for argv in argvs if "git" not in argv], bool(argvs)), ([], True))
		self.assertEqual(self.git_snapshot(), snapshot)
		self.assertEqual(self.tree(), tree)

	def test_result_keys_stable(self):
		self.sandbox.commit_file(APP, "pkg/a.txt", "a\n")
		self.assertEqual(propose_change.PROPOSE_TOOL_NAMES, tuple(TOOL_NAMES))
		with patch.object(propose_change, "_insert", wraps=propose_change._insert) as insert:
			code = self.change(["a"], ["b"], f"{APP}/pkg/a.txt")
			command = self.run_tool("propose_bench_command", {"command": "version", "reason": "r"})
		self.assertEqual(set(code), {"ok", "proposal", "status", "comment", "branch"}, code)
		self.assertEqual(set(command), {"ok", "proposal", "status", "comment"}, command)
		for call in insert.call_args_list:
			values = call.args[1]
			with self.subTest(kind=values["change_kind"]):
				self.assertIn("command_list", values)
				self.assertEqual(set(values) & set(transitions.STATE_FIELDS), set())
		with open(propose_change.__file__, encoding="utf-8") as handle:
			code_text = handle.read()
		self.assertEqual((code_text.count(".insert("), code_text.count("allow_agent_write()")), (1, 1))


class TestBlockComment(FrappeTestCase):
	"""CHG-002 T30: the ticket comment of a block proposal (design 3.7, design-addendum-7 P7-10)."""

	setUp = TestProposeChange.setUp
	context = TestProposeChange.context
	run_tool = TestProposeChange.run_tool
	comments = TestProposeChange.comments
	block = TestProposeBlock.block
	stored = TestProposeBlock.stored

	def content(self, result):
		(comment,) = [row for row in self.comments() if row.name == result["comment"]]
		return comment.content

	def expected(self, name, first, lines):
		"""The whole comment: the first sentence, one paragraph per note line, the three links."""
		escape = frappe.utils.escape_html
		form = f"/app/erp-ai-change-proposal/{name}"
		approve = change_link.decision_path(name, change_link.ACTION_APPROVE)
		reject = change_link.decision_path(name, change_link.ACTION_REJECT)
		return (
			f'<p>Đề xuất <a href="{escape(form)}">{escape(name)}</a> đang chờ duyệt: {escape(first)}</p>'
			+ "".join(f"<p>{escape(line)}</p>" for line in lines)
			+ f'<p><a href="{escape(approve)}"><strong>Duyệt</strong></a> · '
			f'<a href="{escape(reject)}"><strong>Từ chối</strong></a> · '
			f'<a href="{escape(form)}">Xem nội dung thay đổi</a></p>'
		)

	def four_kinds(self):
		self.sandbox.commit_file(APP, "pkg/a.py", "x = 1\n")
		self.sandbox.commit_file(APP, "pkg/d.txt", "d\n")
		self.sandbox.commit_file(APP, "pkg/r.txt", "r\n")
		return [
			{"action": "edit", "path": f"{APP}/pkg/a.py", "find": ["x = 1"], "replace": ["x = 2"]},
			{"action": "create", "path": f"{APP}/pkg/n.md", "content": "n\n"},
			{"action": "delete", "path": f"{APP}/pkg/d.txt"},
			{"action": "rename", "path": f"{APP}/pkg/r.txt", "new_path": f"{APP}/doc/r.txt"},
		]

	def run_block(self, changes, commands):
		arguments = {"changes": changes, "commands": commands, "reason": "khối"}
		result = self.run_tool("propose_file_change", arguments)
		self.assertTrue(result["ok"], result)
		return result

	def test_comment_counts_paths_delete_rename_lines_commands_restart_note(self):
		result = self.run_block(self.four_kinds(), [{"command": "migrate"}, {"command": "restart"}])
		doc = self.stored(result)
		lines = [
			"Gồm 1 sửa, 1 tạo, 1 xóa, 1 đổi tên; 2 lệnh.",
			f"sửa {APP}/pkg/a.py",
			f"tạo {APP}/pkg/n.md",
			f"XÓA {APP}/pkg/d.txt",
			f"ĐỔI TÊN {APP}/pkg/r.txt → {APP}/doc/r.txt",
			f"lệnh: bench --site {frappe.local.site} migrate",
			"lệnh: bench restart",
			"Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).",
			"Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file.",
			f"Commit sẽ vào nhánh {doc.target_branch} của app {APP}.",
			"Nhánh này không theo nhánh remote nào.",
		]
		first = f"khối 4 mục trong app {APP}."
		self.assertEqual(self.content(result), self.expected(doc.name, first, lines))

	def test_restart_line_iff_restart_listed(self):
		# a `.py` item needs `restart`, any other file refuses it; a block of commands may list it alone
		self.sandbox.commit_file(APP, "pkg/t.txt", "t\n")
		self.sandbox.commit_file(APP, "pkg/t.py", "t = 1\n")
		text = {"action": "edit", "path": f"{APP}/pkg/t.txt", "find": ["t"], "replace": ["u"]}
		code = {"action": "edit", "path": f"{APP}/pkg/t.py", "find": ["t = 1"], "replace": ["t = 2"]}
		site = frappe.local.site
		restart_line = "<p>Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).</p>"
		legacy_line = "<p>Sau khi áp dụng cần người chạy bench restart.</p>"
		runs = {
			"file, migrate": (lambda: self.run_block([text], [{"command": "migrate"}]), 0),
			"py, migrate, restart": (
				lambda: self.run_block([code], [{"command": "migrate"}, {"command": "restart"}]),
				1,
			),
			"command migrate": (
				lambda: self.run_tool("propose_bench_command", {"command": "migrate", "reason": "r"}),
				0,
			),
			"commands migrate, restart": (
				lambda: propose_change._propose_block(
					[], [["--site", site, "migrate"], ["restart"]], "r", self.context()
				),
				1,
			),
			"commands restart": (
				lambda: propose_change._propose_block([], [["restart"]], "r", self.context()),
				1,
			),
		}
		for shape, (run, count) in runs.items():
			with self.subTest(shape=shape):
				result = run()
				self.assertTrue(result["ok"], result)
				content = self.content(result)
				# design-addendum-9 A9-1: the old sentence never, the new line once when `restart` is listed
				self.assertEqual(
					(
						content.count("Sau khi áp dụng cần người chạy bench restart."),
						content.count("Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối)."),
					),
					(0, count),
				)
				self.assertEqual(content.count(restart_line), count)
				self.assertNotIn(legacy_line, content)

	def test_no_remote_url(self):
		self.sandbox.add_remote(APP, url=REMOTE_URL, ahead=1)
		commands = [{"command": "migrate"}, {"command": "restart"}]
		content = self.content(self.run_block(self.four_kinds(), commands))
		for secret in (REMOTE_URL, "x-token-FAKE", "host/r.git"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, content)
		# `{tên}` and `{app}` of the first sentence go through `_shown` too (P7-10 point 4); the
		# links carry the name as it is, so only the sentence is checked for the forged name
		ctx = self.context()
		forged = frappe._dict(
			name="CP://T30",
			change_kind=CHANGE_KIND_CODE,
			app=REMOTE_URL,
			operations=[frappe._dict(idx=1, operation=CHANGE_OP_CREATE, file_path=f"{APP}/pkg/x.md")],
			command_list="[]",
		)
		forged_content = frappe.db.get_value("Comment", propose_change._comment(ctx, forged), "content")
		self.assertIn('"></a> đang chờ duyệt: khối 1 mục trong app .</p>', forged_content)
		for secret in (REMOTE_URL, "x-token-FAKE", "host/r.git"):
			with self.subTest(forged=secret):
				self.assertNotIn(secret, forged_content)
		# the app is escaped after `_shown`; a block of only commands filters its name too
		marked = frappe._dict(forged, name="CP-T30-HTML", app="<b>&x")
		marked_content = frappe.db.get_value("Comment", propose_change._comment(ctx, marked), "content")
		self.assertIn("khối 1 mục trong app &lt;b&gt;&amp;x.</p>", marked_content)
		commands_only = frappe._dict(
			name="CP://T30",
			change_kind=CHANGE_KIND_COMMAND,
			operations=[],
			command_list='[["restart"]]',
		)
		commands_content = frappe.db.get_value(
			"Comment", propose_change._comment(ctx, commands_only), "content"
		)
		self.assertIn('"></a> đang chờ duyệt: 1 lệnh bench.</p>', commands_content)

	def test_command_only_first_sentence(self):
		result = self.run_tool("propose_bench_command", {"command": "migrate", "reason": "r"})
		self.assertTrue(result["ok"], result)
		lines = [
			"Gồm 0 sửa, 0 tạo, 0 xóa, 0 đổi tên; 1 lệnh.",
			f"lệnh: bench --site {frappe.local.site} migrate",
			"Lệnh trong khối không hoàn tác được; hoàn tác chỉ trả lại phần file.",
		]
		name = result["proposal"]
		self.assertEqual(self.content(result), self.expected(name, "1 lệnh bench.", lines))

	def test_fifty_items_all_paths_listed(self):
		self.assertEqual(CHANGE_MAX_FILE_OPS, 50)
		changes = [
			{"action": "create", "path": f"{APP}/pkg/many/f{number:02d}.md", "content": "f\n"}
			for number in range(50)
		]
		content = self.content(self.run_block(changes, []))
		self.assertIn(f"đang chờ duyệt: khối 50 mục trong app {APP}.</p>", content)
		self.assertIn("<p>Gồm 0 sửa, 50 tạo, 0 xóa, 0 đổi tên; 0 lệnh.</p>", content)
		for change in changes:
			with self.subTest(path=change["path"]):
				self.assertEqual(content.count(f"<p>tạo {change['path']}</p>"), 1)

	def test_mixed_block_first_sentence_counts_items(self):
		self.sandbox.commit_file(APP, "pkg/t.py", "t = 1\n")
		changes = [
			{"action": "edit", "path": f"{APP}/pkg/t.py", "find": ["t = 1"], "replace": ["t = 2"]},
			{"action": "create", "path": f"{APP}/pkg/m.md", "content": "m\n"},
		]
		commands = [{"command": "migrate"}, {"command": "build", "app": APP}, {"command": "restart"}]
		content = self.content(self.run_block(changes, commands))
		self.assertIn(f"đang chờ duyệt: khối 2 mục trong app {APP}.</p>", content)
		self.assertNotIn("lệnh bench.</p>", content)
		self.assertIn("<p>Gồm 1 sửa, 1 tạo, 0 xóa, 0 đổi tên; 3 lệnh.</p>", content)

	def test_command_count_includes_restart(self):
		site = frappe.local.site
		result = propose_change._propose_block(
			[], [["--site", site, "migrate"], ["restart"]], "r", self.context()
		)
		self.assertTrue(result["ok"], result)
		content = self.content(result)
		self.assertIn("đang chờ duyệt: 2 lệnh bench.</p>", content)
		self.assertIn("<p>Gồm 0 sửa, 0 tạo, 0 xóa, 0 đổi tên; 2 lệnh.</p>", content)

	def test_legacy_comment_unchanged(self):
		"""A proposal without child rows and without `command_list` keeps today's comment byte for byte."""
		ctx = self.context()
		approve = frappe.utils.escape_html(
			change_link.decision_path("CP-T30-OLD", change_link.ACTION_APPROVE)
		)
		reject = frappe.utils.escape_html(change_link.decision_path("CP-T30-OLD", change_link.ACTION_REJECT))
		links = (
			f'<p><a href="{approve}"><strong>Duyệt</strong></a> · '
			f'<a href="{reject}"><strong>Từ chối</strong></a> · '
			'<a href="/app/erp-ai-change-proposal/CP-T30-OLD">Xem nội dung thay đổi</a></p>'
		)
		head = '<p>Đề xuất <a href="/app/erp-ai-change-proposal/CP-T30-OLD">CP-T30-OLD</a> đang chờ duyệt: '
		code = {
			"name": "CP-T30-OLD",
			"change_kind": CHANGE_KIND_CODE,
			"app": APP,
			"target_branch": "develop",
			"upstream_ref": "",
		}
		cases = {
			"edit .py": (
				{**code, "file_path": f"{APP}/pkg/<m>.py", "is_new_file": 0},
				head + f"sửa <code>{APP}/pkg/&lt;m&gt;.py</code>.</p>"
				f"<p>Commit sẽ vào nhánh develop của app {APP}.</p>"
				"<p>Nhánh này không theo nhánh remote nào.</p>"
				"<p>Sau khi áp dụng cần người chạy bench restart.</p>" + links,
			),
			"new file": (
				{**code, "file_path": f"{APP}/pkg/n.md", "is_new_file": 1},
				head + f"tạo <code>{APP}/pkg/n.md</code>.</p>"
				f"<p>Commit sẽ vào nhánh develop của app {APP}.</p>"
				"<p>Nhánh này không theo nhánh remote nào.</p>" + links,
			),
			"command": (
				{"name": "CP-T30-OLD", "change_kind": CHANGE_KIND_COMMAND, "command_list": ""},
				head + "lệnh <code>bench </code>.</p><p>Lệnh bench không hoàn tác được.</p>" + links,
			),
		}
		for shape, (fields, expected) in cases.items():
			with self.subTest(shape=shape):
				name = propose_change._comment(ctx, frappe._dict(fields))
				self.assertEqual(frappe.db.get_value("Comment", name, "content"), expected)
