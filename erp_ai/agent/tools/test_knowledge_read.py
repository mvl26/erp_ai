import errno
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import knowledge
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import knowledge_read, source
from erp_ai.agent.tools.registry import ToolContext, _first_invalid_key
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE
from erp_ai.test_utils import TempAppsRoot, keep_agent_settings, pin_agent_roles, set_agent_settings

EMPTY_QUERY = "Câu tìm cần ít nhất một từ dài 2 ký tự"
EXCLUDED_TEAM = "T148 Nhóm loại trừ"
# Every test Error Log is dated in 2001: no live row of the shared site falls in a test's window.
DAY = datetime(2001, 2, 3, 10, 0, 0)
WINDOW = {"since": "2001-02-03 09:00:00", "until": "2001-02-03 11:00:00"}


def _word(label="kr"):
	"""A word no other record on the site contains."""
	return f"{label}{frappe.generate_hash(length=10).lower()}"


def _ctx(ticket_name="TKT-0"):
	return ToolContext(
		ticket_name=ticket_name,
		effective_level="L1",
		instructor=None,
		run_id="ERPAI-TEST-knowledge-read",
		category_mapping={},
		agent_user=AGENT_USER,
	)


class KnowledgeToolCase(FrappeTestCase):
	"""Own data, rolled back after each test; the tools run under the agent account, pinned to its roles."""

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
		self._settings(knowledge_search_limit=5, report_row_limit=20, allowed_reports="", manuals_dir="")

	def _settings(self, **fields) -> None:
		set_agent_settings(**fields)
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)

	def _as_agent(self, tool, args):
		frappe.set_user(AGENT_USER)
		try:
			return tool(args, _ctx())
		finally:
			frappe.set_user("Administrator")


class TestToolSpecs(KnowledgeToolCase):
	def test_search_specs_in_read_group_with_query_bounds(self):
		specs = {spec.name: spec for spec in knowledge_read.TOOLS}
		self.assertEqual(knowledge_read.MANUALS_NOT_CONFIGURED, "chưa có kho HDSD")
		self.assertEqual(
			knowledge_read.KNOWLEDGE_TOOL_NAMES,
			frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"}),
		)
		for name in ("search_knowledge_base", "search_manuals"):
			with self.subTest(name):
				spec = specs[name]
				self.assertEqual((spec.group, spec.schema["name"]), ("read", name))
				schema = spec.schema["input_schema"]
				self.assertEqual(schema["required"], ["query"])
				self.assertEqual(set(schema["properties"]), {"query"})
				self.assertIsNone(_first_invalid_key({"query": "ab"}, schema))
				self.assertIsNone(_first_invalid_key({"query": "x" * 100}, schema))
				for bad in ({"query": "a"}, {"query": "x" * 101}, {"query": 12}):
					self.assertEqual(_first_invalid_key(bad, schema), "query")

	def test_limits_read_from_setting(self):
		self._settings(knowledge_search_limit=7, report_row_limit=30, allowed_reports=" A \n\n  \nB\n")

		self.assertEqual(knowledge_read._limits(), (7, ("A", "B"), 30))


class TestSearchKnowledgeBase(KnowledgeToolCase):
	"""AC-46 at the tool: published articles only, ranked by matched words, as many as the setting says."""

	def _article(self, content, status="Published", title_words="", **values):
		title = f"T148 {frappe.generate_hash(length=8)} {title_words}".strip()
		return (
			frappe.get_doc(
				{"doctype": "HD Article", "title": title, "content": content, "status": status, **values}
			)
			.insert()
			.name
		)

	def _search(self, query):
		return self._as_agent(knowledge_read.search_knowledge_base, {"query": query})

	def _names(self, query):
		result = self._search(query)
		self.assertTrue(result["ok"], result)
		return [row["name"] for row in result["articles"]]

	def test_published_only(self):
		word = _word()
		published = {self._article(f"<p>Bài {index} {word}</p>") for index in range(3)}
		for index in range(2):
			self._article(f"<p>Nháp {index} {word}</p>", status="Draft")
		self._article(f"<p>Lưu trữ {word}</p>", status="Archived")

		result = self._search(word)

		self.assertTrue(result["ok"], result)
		self.assertEqual({row["name"] for row in result["articles"]}, published)
		for row in result["articles"]:
			self.assertEqual(set(row), {"name", "title", "excerpt"})
			self.assertEqual(row["title"], frappe.db.get_value("HD Article", row["name"], "title"))
			self.assertIn(word, row["excerpt"])

	def test_reversed_words_found(self):
		one, two = _word(), _word()
		article = self._article(f"<p>{one} rồi mới tới {two}</p>")

		self.assertEqual(self._names(f"{two} {one}"), [article])

	def test_more_matches_ranked_first(self):
		one, two, three = _word(), _word(), _word()
		only_one = self._article(f"<p>{one}</p>")
		all_three = self._article(f"<p>{one} {two} {three}</p>")
		two_of_them = self._article(f"<p>{one} và {two}</p>")

		self.assertEqual(self._names(f"{one} {two} {three}"), [all_three, two_of_them, only_one])

	def test_limit_from_setting(self):
		word = _word()
		for index in range(3):
			self._article(f"<p>{index} {word}</p>")

		self._settings(knowledge_search_limit=2)
		self.assertEqual(len(self._names(word)), 2)
		self._settings(knowledge_search_limit=3)
		self.assertEqual(len(self._names(word)), 3)

	def test_secret_in_title_masked(self):
		word = _word()
		self._article(f"<p>{word}</p>", title_words="password: fake-kr-title")

		(row,) = self._search(word)["articles"]

		self.assertNotIn("fake-kr-title", row["title"])
		self.assertIn(MASK, row["title"])

	def test_query_without_two_letter_word_refused(self):
		self.assertEqual(self._search("a b"), {"ok": False, "reason": EMPTY_QUERY})

	def test_article_of_excluded_ticket_left_out(self):
		"""NFR-1: a published article whose source ticket the agent may not take never reaches the model."""
		word = _word()
		self._settings(excluded_teams=EXCLUDED_TEAM)
		excluded = make_ticket(subject="T148 phiếu loại trừ").name
		# db.set_value skips the link check: the send predicate compares team names only.
		frappe.db.set_value("HD Ticket", excluded, "agent_group", EXCLUDED_TEAM)
		kept = self._article(f"<p>{word} {_word()}</p>", ai_source_ticket=make_ticket(subject="T148").name)
		self._article(f"<p>{word}</p>", ai_source_ticket=excluded)

		self.assertEqual(self._names(word), [kept])


class TestSearchManuals(KnowledgeToolCase):
	"""AC-47 at the tool: sections of the manuals directory; every returned string masked."""

	def setUp(self):
		super().setUp()
		self.sandbox = TempAppsRoot(self, apps=("myapp",))
		self._settings(manuals_dir="myapp/docs")

	def _manual(self, rel, text):
		return self.sandbox.write(os.path.join("myapp", "docs", rel), text)

	def _search(self, query):
		return self._as_agent(knowledge_read.search_manuals, {"query": query})

	def test_match_returns_document_heading_line(self):
		word = _word("mn")
		self._manual("a.md", "# Đăng nhập\nnội dung\n")
		self._manual("sub/b.md", f"Mở đầu\n# Lỗi in\ndòng {word}\n")
		self._manual("c.md", "# Báo cáo\nkhác\n")

		self.assertEqual(
			self._search(word),
			{
				"ok": True,
				"sections": [
					{
						"document": "sub/b.md",
						"heading": "Lỗi in",
						"line": 2,
						"excerpt": f"# Lỗi in\ndòng {word}",
					}
				],
			},
		)

	def test_no_match_empty(self):
		self._manual("a.md", "# Đăng nhập\nnội dung\n")

		self.assertEqual(self._search(_word("mn")), {"ok": True, "sections": []})

	def test_not_configured_refused(self):
		self._manual("a.md", "# Đăng nhập\nnội dung\n")
		for value in ("", "   "):
			with self.subTest(manuals_dir=value):
				self._settings(manuals_dir=value)
				self.assertEqual(
					self._search("đăng nhập"),
					{"ok": False, "reason": knowledge_read.MANUALS_NOT_CONFIGURED},
				)

	def test_manuals_not_readable_by_read_source(self):
		word = _word("mn")
		self._manual("hdsd.md", f"# Mục\n{word}\n")
		(section,) = self._search(word)["sections"]

		frappe.set_user(AGENT_USER)
		result = source.read_source({"path": f"myapp/docs/{section['document']}"}, _ctx())

		self.assertFalse(result["ok"], result)
		self.assertNotIn(word, str(result))

	def test_secret_in_heading_masked(self):
		word = _word("mn")
		self._manual("hdsd.md", f"# Cấu hình password: fake-heading-mn\n{word}\n")

		(section,) = self._search(word)["sections"]

		self.assertNotIn("fake-heading-mn", section["heading"])
		self.assertIn(MASK, section["heading"])
		self.assertNotIn("fake-heading-mn", section["excerpt"])

	def test_unreadable_file_skipped_others_returned(self):
		"""`design-w1b-fixes-1.md` điểm 2: the file that cannot be read is skipped inside the search, not here."""
		word = _word("mn")
		self._manual("a.md", f"# Mục\n{word}\n")
		self._manual("b.md", f"# Mục\n{word}\n")
		real_open = open

		def fake_open(path, *args, **kwargs):
			if os.path.basename(path) == "a.md":
				raise PermissionError(errno.EACCES, "denied", path)
			return real_open(path, *args, **kwargs)

		with patch.object(knowledge, "open", side_effect=fake_open, create=True):
			result = self._search(word)

		self.assertEqual(set(result), {"ok", "sections"})
		self.assertTrue(result["ok"])
		self.assertEqual([row["document"] for row in result["sections"]], ["b.md"])

	def test_query_without_two_letter_word_refused(self):
		self._manual("a.md", "# Mục\nnội dung\n")

		self.assertEqual(self._search("a b"), {"ok": False, "reason": EMPTY_QUERY})


class TestReadErrorLogs(KnowledgeToolCase):
	"""AC-50 at the tool: bounded, filtered, masked; the agent account needs no extra role (ADR-034)."""

	def _error_log(self, creation, method, error="Traceback ERPAI-TEST") -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Error Log",
				"method": method,
				"error": error,
				"owner": "Administrator",
				"creation": creation,
				"modified": creation,
			}
		)
		doc.db_insert()
		return doc.name

	def _read(self, **args):
		return self._as_agent(knowledge_read.read_error_logs, args)

	def _names(self, **args):
		result = self._read(**args)
		self.assertTrue(result["ok"], result)
		return [row["name"] for row in result["errors"]]

	def test_time_and_keyword_filter(self):
		key = _word("el")
		by_method = self._error_log(DAY, f"T149 {key}")
		by_error = self._error_log(DAY + timedelta(minutes=1), "T149 khác", f"lỗi có {key}")
		self._error_log(DAY + timedelta(minutes=2), "T149 không có từ khóa")
		self._error_log(DAY - timedelta(hours=2), f"T149 trước {key}")
		self._error_log(DAY + timedelta(hours=2), f"T149 sau {key}")

		self.assertEqual(self._names(**WINDOW, keyword=key), [by_error, by_method])
		self.assertEqual(len(self._names(**WINDOW)), 3)
		(row,) = self._read(**WINDOW, keyword=key, limit=1)["errors"]
		self.assertEqual(set(row), {"name", "creation", "method", "error"})

		for key_name in ("since", "until"):
			for bad in ("không phải ngày", "", "2001-02-03T09:00:00+07:00"):
				with self.subTest(key_name=key_name, value=bad):
					self.assertEqual(
						self._read(**{**WINDOW, key_name: bad}),
						{"ok": False, "reason": f"thời điểm không hợp lệ: {key_name}"},
					)
		self.assertEqual(
			self._read(since="2001-01-01 00:00:00", until="2001-02-03 11:00:00"),
			{"ok": False, "reason": "Khoảng thời gian tối đa 7 ngày"},
		)

	def test_limit(self):
		names = [
			self._error_log(DAY + timedelta(minutes=minute), f"T149 limit {minute}") for minute in range(4)
		]

		self.assertEqual(self._names(**WINDOW, limit=2), [names[3], names[2]])
		self.assertEqual(len(self._names(**WINDOW, limit=50)), 4)
		spec = next(spec for spec in knowledge_read.TOOLS if spec.name == "read_error_logs")
		self.assertEqual(spec.group, "read")
		schema = spec.schema["input_schema"]
		self.assertEqual(
			(set(schema["properties"]), schema["required"]), ({"since", "until", "keyword", "limit"}, [])
		)
		for bad in ({"limit": 0}, {"limit": 51}, {"keyword": "a"}, {"keyword": "x" * 101}, {"since": 1}):
			with self.subTest(bad):
				self.assertEqual(_first_invalid_key(bad, schema), next(iter(bad)))

	def test_seeded_key_masked(self):
		name = self._error_log(
			DAY,
			"T149 password: fake-el-method",
			"Traceback\napi_key=fake-el-key-1234567890\nAuthorization: Bearer fake-el-bearer-token\n",
		)

		(row,) = self._read(**WINDOW, keyword="T149 password")["errors"]

		self.assertEqual(row["name"], name)
		text = f"{row['method']} {row['error']}"
		for secret in ("fake-el-method", "fake-el-key-1234567890", "fake-el-bearer-token"):
			self.assertNotIn(secret, text)
		self.assertIn(MASK, row["method"])
		self.assertIn(MASK, row["error"])

	def test_agent_roles_unchanged(self):
		self._error_log(DAY, "T149 roles")
		before = sorted(frappe.get_roles(AGENT_USER))

		self.assertEqual(len(self._names(**WINDOW)), 1)

		self.assertEqual(sorted(frappe.get_roles(AGENT_USER)), before)
		self.assertNotIn("System Manager", before)
