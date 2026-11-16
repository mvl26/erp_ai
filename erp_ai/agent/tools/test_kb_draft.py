from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import labels
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import kb_draft
from erp_ai.agent.tools.registry import ToolContext, _first_invalid_key
from erp_ai.constants import AGENT_USER, ROLE_INSTRUCTOR, SETTING_DOCTYPE
from erp_ai.test_utils import keep_agent_settings, pin_agent_roles, set_agent_settings

EXCLUDED_TEAM = "T152 Nhóm loại trừ"
REFUSED_TICKET = "phiếu không được phép đưa cho AI"
ARGS = {
	"title": "ERPAI-TEST Máy in không in hóa đơn",
	"problem": "ERPAI-TEST máy in báo kẹt giấy khi in hóa đơn bán hàng.",
	"resolution_steps": ["Tắt máy in", "Lấy giấy kẹt ra", "In lại hóa đơn"],
}


def _unique(label: str) -> str:
	return f"erpai-test-{label}-{frappe.generate_hash(length=10).lower()}"


class KbDraftCase(FrappeTestCase):
	"""Own data, rolled back after each test; the tool runs under the agent account, pinned to its roles."""

	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		pin_agent_roles(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(excluded_teams=EXCLUDED_TEAM, excluded_title_prefixes="")
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)

	def _ticket(self, resolved=True, **values) -> str:
		ticket = make_ticket(
			subject="ERPAI-TEST kb draft", description=values.pop("description", "ERPAI-TEST")
		).name
		if resolved:
			values = {"status": "Resolved", "status_category": "Resolved", **values}
		if values:
			# db.set_value skips the link check: the send predicate compares team names only.
			frappe.db.set_value("HD Ticket", ticket, values, update_modified=False)
		return str(ticket)

	def _ctx(self, ticket) -> ToolContext:
		return ToolContext(
			ticket_name=ticket,
			effective_level="L1",
			instructor=None,
			run_id=_unique("run"),
			category_mapping={},
			agent_user=AGENT_USER,
		)

	def _draft(self, ticket, **args) -> dict:
		frappe.set_user(AGENT_USER)
		try:
			return kb_draft.create_kb_draft({**ARGS, **args}, self._ctx(ticket))
		finally:
			frappe.set_user("Administrator")

	def _articles(self, ticket) -> list[str]:
		return frappe.get_all("HD Article", filters={"ai_source_ticket": ticket}, pluck="name")


class TestCreateKbDraft(KbDraftCase):
	def test_spec_and_bounds(self):
		(spec,) = kb_draft.TOOLS
		self.assertEqual(
			(spec.name, spec.group, spec.handler), ("create_kb_draft", "kb_draft", kb_draft.create_kb_draft)
		)
		self.assertEqual(kb_draft.KB_TITLE_MAX, 140)
		schema = spec.schema["input_schema"]
		self.assertEqual(schema["required"], ["title", "problem", "resolution_steps"])
		self.assertIsNone(_first_invalid_key(ARGS, schema))
		for bad in (
			{"title": "x" * 4},
			{"title": "x" * 141},
			{"problem": "x" * 19},
			{"problem": "x" * 4001},
			{"resolution_steps": ["x"] * 21},
			{"resolution_steps": [""]},
			{"resolution_steps": ["x" * 1001]},
		):
			with self.subTest(bad):
				self.assertEqual(_first_invalid_key({**ARGS, **bad}, schema), next(iter(bad)))
		# the registry does not check minItems: the tool refuses an empty list itself
		ticket = self._ticket()
		self.assertEqual(
			self._draft(ticket, resolution_steps=[]),
			{"ok": False, "reason": "tham số không hợp lệ: resolution_steps"},
		)
		self.assertEqual(self._articles(ticket), [])

	def test_draft_linked_to_ticket(self):
		ticket = self._ticket()

		result = self._draft(ticket)

		self.assertEqual(set(result), {"ok", "article"})
		self.assertTrue(result["ok"], result)
		self.assertEqual(self._articles(ticket), [result["article"]])
		article = frappe.get_doc("HD Article", result["article"])
		self.assertEqual(
			(article.status, article.ai_source_ticket, article.owner, article.title),
			("Draft", ticket, AGENT_USER, ARGS["title"]),
		)
		parts = [
			"<h2>Vấn đề</h2>",
			f"<p>{ARGS['problem']}</p>",
			"<h2>Các bước đã giải quyết</h2>",
			"<ol><li>Tắt máy in</li><li>Lấy giấy kẹt ra</li><li>In lại hóa đơn</li></ol>",
			f"<p>Phiếu nguồn: #{ticket}</p>",
		]
		positions = [article.content.find(part) for part in parts]
		self.assertNotIn(-1, positions, article.content)
		self.assertEqual(positions, sorted(positions), article.content)

	def test_draft_carries_the_ticket_labels(self):
		# ADR-049: the knowledge base keeps the labels of the ticket the article came from
		ticket = self._ticket()
		names = ("ERPAI-TEST-Kho", "ERPAI-TEST-In ấn")
		for name in names:
			frappe.get_doc("HD Ticket", ticket).add_tag(name)

		result = self._draft(ticket)

		self.assertTrue(result["ok"], result)
		links = frappe.get_all(
			"Tag Link",
			filters={"document_type": "HD Article", "document_name": result["article"]},
			pluck="tag",
		)
		self.assertEqual(sorted(links), sorted(names))
		tags = frappe.db.get_value("HD Article", result["article"], "_user_tags")
		self.assertEqual(sorted(labels.parse_tags(tags)), sorted(names))

	def test_draft_of_an_unlabelled_ticket_has_no_tag(self):
		ticket = self._ticket()
		result = self._draft(ticket)
		self.assertFalse(frappe.db.get_value("HD Article", result["article"], "_user_tags"))

	def test_open_ticket_refused(self):
		ticket = self._ticket(resolved=False)

		self.assertEqual(self._draft(ticket), {"ok": False, "reason": "phiếu chưa đóng"})
		self.assertEqual(self._articles(ticket), [])

	def test_second_article_refused(self):
		ticket = self._ticket()
		self.assertTrue(self._draft(ticket)["ok"])

		self.assertEqual(self._draft(ticket), {"ok": False, "reason": "phiếu đã có bài CSKT"})
		self.assertEqual(len(self._articles(ticket)), 1)

	def test_agent_cannot_publish(self):
		ticket = self._ticket()
		name = self._draft(ticket)["article"]

		frappe.set_user(AGENT_USER)
		article = frappe.get_doc("HD Article", name)
		article.status = "Published"
		with self.assertRaises(frappe.PermissionError):
			article.save()
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "HD Article",
					"title": "ERPAI-TEST xuất bản",
					"content": "<p>x</p>",
					"status": "Published",
				}
			).insert()
		frappe.set_user("Administrator")

		self.assertEqual(frappe.db.get_value("HD Article", name, "status"), "Draft")

	def test_excluded_seed_string_absent(self):
		"""NFR-1: a closed ticket of an excluded team, or one opted out of AI, never becomes an article."""
		seed = f"ERPAI-SEED-{frappe.generate_hash(length=10)}"
		for values in ({"agent_group": EXCLUDED_TEAM}, {"ai_opt_out": 1}):
			with self.subTest(values):
				ticket = self._ticket(description=f"<p>{seed}</p>", **values)
				result = self._draft(ticket, problem=f"ERPAI-TEST lỗi có chuỗi {seed} trong nội dung")
				self.assertEqual(result, {"ok": False, "reason": REFUSED_TICKET})
				self.assertEqual(self._articles(ticket), [])
		self.assertEqual(frappe.db.count("HD Article", {"content": ("like", f"%{seed}%")}), 0)

	def test_instructor_lists_bot_drafts(self):
		"""`U6b-fixes.md` Sửa 8: the HD Article read permission of ERP AI Instructor is installed by T22a."""
		name = self._draft(self._ticket())["article"]
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert()
		instructor = f"{_unique('instructor')}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": instructor, "first_name": "T152", "send_welcome_email": 0}
		).insert()
		frappe.get_doc("User", instructor).add_roles(ROLE_INSTRUCTOR)
		self.assertNotIn("Agent", frappe.get_roles(instructor))

		frappe.set_user(instructor)
		drafts = frappe.get_list(
			"HD Article", filters={"status": "Draft", "ai_source_ticket": ("is", "set")}, pluck="name"
		)

		self.assertIn(name, drafts)

	def test_content_escaped_and_masked(self):
		ticket = self._ticket()
		title = "ERPAI-TEST password: ab " + "t" * 116

		result = self._draft(
			ticket,
			title=title,
			problem="ERPAI-TEST <script>alert(1)</script> api_key=fake-kb-key-123",
			resolution_steps=["token: fake-kb-step", "<b>Xong</b>"],
		)

		article = frappe.get_doc("HD Article", result["article"])
		self.assertEqual(len(title), 140)
		self.assertLessEqual(len(article.title), kb_draft.KB_TITLE_MAX)
		self.assertNotIn("password: ab", article.title)
		self.assertIn(MASK, article.title)
		for secret in ("fake-kb-key-123", "fake-kb-step", "<script>", "<b>"):
			self.assertNotIn(secret, article.content)
		self.assertIn("&lt;script&gt;", article.content)
		self.assertIn(MASK, article.content)

	def test_value_starting_with_angle_bracket_masked(self):
		"""R17a (NFR-6): each piece is masked before it is escaped, so a value that starts with `<` is still caught
		(escaped first, it would start with `&lt;`, which no masking rule reads as a value)."""
		ticket = self._ticket()

		result = self._draft(
			ticket,
			problem="ERPAI-TEST máy in lỗi, password: <fake-kb-angle> trong cấu hình",
			resolution_steps=["api_key=<fake-kb-step-angle>", "In lại"],
		)

		self.assertTrue(result["ok"], result)
		content = frappe.db.get_value("HD Article", result["article"], "content")
		for secret in ("fake-kb-angle", "fake-kb-step-angle"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, content)
		self.assertEqual(content.count(MASK), 2, content)

	def test_ticket_locked_before_article_check(self):
		"""R17e: the ticket row is locked (`for_update`, as lifecycle does) before the check for an existing article,
		so two runs on one ticket cannot both pass that check."""
		ticket = self._ticket()
		db = MagicMock()

		with (
			patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value,
			patch.object(frappe.db, "exists", wraps=frappe.db.exists) as exists,
		):
			db.attach_mock(get_value, "get_value")
			db.attach_mock(exists, "exists")
			self.assertTrue(self._draft(ticket)["ok"])

		calls = db.mock_calls
		check = next(
			index
			for index, entry in enumerate(calls)
			if entry[0] == "exists" and entry.args[:1] == (kb_draft.ARTICLE_DOCTYPE,)
		)
		locks = [
			entry
			for entry in calls[:check]
			if entry[0] == "get_value"
			and entry.args[:2] == ("HD Ticket", ticket)
			and entry.kwargs.get("for_update") is True
		]
		self.assertEqual(len(locks), 1, calls[:check])
