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

	def change(self, edits, path=PATH, **context):
		return self.run_tool(
			"propose_file_change", {"path": path, "edits": edits, "reason": "sửa theo yêu cầu"}, **context
		)

	def on_disk(self, rel=REL):
		with open(os.path.join(self.sandbox.repo(APP), rel), encoding="utf-8", newline="") as handle:
			return handle.read()

	def proposals(self):
		frappe.set_user("Administrator")
		names = frappe.get_all(PROPOSAL_DOCTYPE, filters={"ticket": self.ticket}, pluck="name")
		frappe.set_user(AGENT)
		return names

	def comments(self):
		frappe.set_user("Administrator")
		rows = frappe.get_all(
			"Comment", filters=authority.ticket_comment_filters(self.ticket), fields=["content", "owner"]
		)
		frappe.set_user(AGENT)
		return rows

	def test_file_change_creates_a_pending_proposal_and_touches_nothing(self):
		head = self.sandbox.git(APP, "rev-parse", "HEAD")
		result = self.change([{"old": "x = 1", "new": "x = 2"}, {"old": "y = 1", "new": "y = 3"}])

		self.assertEqual(result["ok"], True, result)
		self.assertEqual(result["status"], CHANGE_STATUS_PENDING)
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
		self.assertEqual((doc.target_branch, doc.upstream_ref, doc.is_core_app), ("main", "", 0))
		self.assertEqual(doc.reason, "sửa theo yêu cầu")
		self.assertIn("-x = 1", doc.diff)
		self.assertIn("+x = 2", doc.diff)
		self.assertIn(doc.name, doc.commit_message)
		# nothing on disk or in git changed
		self.assertEqual(self.on_disk(), BEFORE)
		self.assertEqual(self.sandbox.git(APP, "rev-parse", "HEAD"), head)
		self.assertEqual(self.sandbox.git(APP, "status", "--porcelain").strip(), "")
		(comment,) = self.comments()
		self.assertEqual(comment.owner, AGENT)
		self.assertIn(doc.name, comment.content)
		self.assertIn("Chờ duyệt", comment.content)
		link = f"/app/erp-ai-change-proposal/{doc.name}"
		self.assertIn(f'<a href="{link}">', comment.content)
		approve = frappe.utils.escape_html(change_link.decision_path(doc.name, "approve"))
		reject = frappe.utils.escape_html(change_link.decision_path(doc.name, "reject"))
		self.assertIn(f'<a href="{approve}"><strong>Duyệt</strong></a>', comment.content)
		self.assertIn(f'<a href="{reject}"><strong>Từ chối</strong></a>', comment.content)
		self.assertLess(comment.content.index(approve), comment.content.index(reject))
		self.assertIn("bench restart", comment.content)

	def test_file_change_refusals_create_nothing(self):
		cases = (
			([{"old": "không có", "new": "x"}], PATH, "xuất hiện 0 lần"),
			([{"old": "= 1", "new": "= 2"}], PATH, "xuất hiện 2 lần"),
			([{"old": "x = 1", "new": "x = 1"}], PATH, "giống hệt"),
			([{"old": "", "new": "x"}], PATH, "old không rỗng"),
			([{"old": "x = 1"}], PATH, "old không rỗng"),
			([{"old": "x = 1", "new": "x = 2"}], f"{APP}/pkg/missing.py", "không tồn tại"),
			([{"old": "x", "new": "y"}], "helpdesk/README.md", "không có trong danh sách"),
			([{"old": "x", "new": "y"}], "erp_ai/README.md", "không có trong danh sách"),
			([{"old": "x", "new": "y"}], "../etc/passwd", "không hợp lệ"),
		)
		for edits, path, phrase in cases:
			result = self.change(edits, path)
			self.assertFalse(result["ok"], (edits, path))
			self.assertIn(phrase, result["reason"], (edits, path))
		# an edit that is not an object never reaches the handler
		self.assertEqual(self.change(["x = 1"]), {"ok": False, "reason": "tham số không hợp lệ: edits"})
		self.assertEqual(self.proposals(), [])
		self.assertEqual(self.comments(), [])
		self.assertEqual(self.on_disk(), BEFORE)

	def test_erp_ai_is_refused_even_when_listed(self):
		result = self.change([{"old": "x", "new": "y"}], "erp_ai/README.md", allowed_apps=(APP, "erp_ai"))
		self.assertFalse(result["ok"])
		self.assertIn("erp_ai", result["reason"])
		self.assertEqual(self.proposals(), [])

	def test_dirty_target_and_too_long_file_are_refused(self):
		with open(os.path.join(self.sandbox.repo(APP), REL), "a", encoding="utf-8") as handle:
			handle.write("z = 1\n")
		dirty = self.change([{"old": "x = 1", "new": "x = 2"}])
		self.assertFalse(dirty["ok"])
		self.assertIn("chưa commit", dirty["reason"])
		self.sandbox.commit_file(APP, "pkg/big.py", "a = 1\n" * 4000)
		big = self.change([{"old": "a = 1\n" * 4000, "new": "b"}], f"{APP}/pkg/big.py")
		self.assertFalse(big["ok"])
		self.assertIn("vượt", big["reason"])
		self.assertEqual(self.proposals(), [])

	def test_new_file_proposal_and_its_refusals(self):
		arguments = {"path": f"{APP}/pkg/new_mod.py", "content": "z = 1\n", "reason": "thêm module"}
		result = self.run_tool("propose_new_file", arguments)

		self.assertTrue(result["ok"], result)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, result["proposal"])
		frappe.set_user(AGENT)
		self.assertEqual(
			(doc.is_new_file, doc.content_after, doc.after_hash), (1, "z = 1\n", _sha("z = 1\n"))
		)
		self.assertFalse(doc.content_before)
		self.assertIn("+z = 1", doc.diff)
		self.assertFalse(os.path.lexists(os.path.join(self.sandbox.repo(APP), "pkg/new_mod.py")))
		for path, phrase in (
			(PATH, "đã tồn tại"),
			(f"{APP}/khong_co/new.py", "thư mục chứa file chưa tồn tại"),
			(f"{APP}/pkg/tool.exe", "đuôi file"),
			(f"{APP}/pkg/secret_key.py", "bí mật"),
		):
			refused = self.run_tool("propose_new_file", {**arguments, "path": path})
			self.assertFalse(refused["ok"], path)
			self.assertIn(phrase, refused["reason"], path)
		self.assertEqual(len(self.proposals()), 1)

	def test_bench_command_proposal_and_its_refusals(self):
		result = self.run_tool(
			"propose_bench_command", {"command": "build", "app": APP, "reason": "build lại giao diện"}
		)

		self.assertTrue(result["ok"], result)
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

	def test_not_granted_without_switch_instructor_or_l3(self):
		edits = [{"old": "x = 1", "new": "x = 2"}]
		self.assertEqual(self.change(edits, change_enabled=False), NOT_GRANTED)
		self.assertEqual(self.change(edits, instructor=None), NOT_GRANTED)
		self.assertEqual(self.change(edits, effective_level="L2"), NOT_GRANTED)
		self.assertEqual(self.proposals(), [])

	def test_handler_itself_refuses_without_instructor_or_create_permission(self):
		arguments = {"path": PATH, "edits": [{"old": "x = 1", "new": "x = 2"}], "reason": "x"}
		no_instructor = propose_change.propose_file_change(arguments, self.context(instructor=None))
		self.assertEqual(no_instructor, {"ok": False, "reason": "không có người ra lệnh"})
		with patch.object(frappe, "has_permission", return_value=False):
			no_permission = propose_change.propose_file_change(arguments, self.context())
		self.assertEqual(no_permission, {"ok": False, "reason": "thiếu quyền tạo đề xuất"})
		self.assertEqual(self.proposals(), [])
