import ast
import inspect
import unicodedata
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import knowledge
from erp_ai.test_utils import keep_agent_settings, make_active_agent

EMPTY_QUERY = "Câu tìm cần ít nhất một từ dài 2 ký tự"


def _word(label="kb"):
	"""A word no other article on the site contains."""
	return f"{label}{frappe.generate_hash(length=10).lower()}"


class KnowledgeCase(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")

	def _article(self, content, status="Published", title_words="", modified=None):
		"""Insert an HD Article of this test (unique title) and return its name."""
		title = f"T37 {frappe.generate_hash(length=8)} {title_words}".strip()
		article = frappe.get_doc(
			{"doctype": "HD Article", "title": title, "content": content, "status": status}
		).insert()
		if modified:
			frappe.db.set_value("HD Article", article.name, "modified", modified, update_modified=False)
		return article.name

	def _names(self, query, limit=5):
		return [row["name"] for row in knowledge.search_kb_articles(query, limit)]


class TestKbSearch(KnowledgeCase):
	def test_only_published(self):
		word = _word()
		published = self._article(f"<p>Cách xử lý {word}</p>")
		self._article(f"<p>Nháp {word}</p>", status="Draft")
		self._article(f"<p>Lưu trữ {word}</p>", status="Archived")

		rows = knowledge.search_kb_articles(word, 5)

		self.assertEqual([row["name"] for row in rows], [published])
		self.assertEqual(set(rows[0]), {"name", "title", "excerpt"})
		self.assertEqual(rows[0]["title"], frappe.db.get_value("HD Article", published, "title"))

	def test_only_articles_the_session_user_may_read(self):
		word = _word()
		readable = self._article(f"<p>{word} được đọc</p>")
		hidden = self._article(f"<p>{word} bị ẩn</p>")
		user = make_active_agent(self)
		frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": "HD Article", "for_value": readable}
		).insert(ignore_permissions=True)
		self.addCleanup(frappe.clear_cache, user=user)

		self.assertEqual(set(self._names(word)), {readable, hidden})
		frappe.set_user(user)
		self.assertEqual(self._names(word), [readable])

	def test_rank_by_matched_words(self):
		one, two, three = _word(), _word(), _word()
		all_three = self._article(f"<p>{one} {two} {three}</p>")
		only_one = self._article(f"<p>{one}</p>")
		first_two = self._article(f"<p>{one} và {two}</p>")
		self._article("<p>không khớp từ nào</p>")

		self.assertEqual(self._names(f"{one} {two} {three}"), [all_three, first_two, only_one])

	def test_tie_broken_by_title_matches_then_modified(self):
		one, two = _word(), _word()
		in_title = self._article(f"<p>{two}</p>", title_words=one, modified="2020-01-01 00:00:00")
		newer = self._article(f"<p>{one} {two}</p>", modified="2025-01-02 00:00:00")
		older = self._article(f"<p>{one} {two}</p>", modified="2025-01-01 00:00:00")
		real_get_list = frappe.get_list

		# the scan order must not decide the ranking: hand the rows over in reverse
		def reversed_rows(*args, **kwargs):
			return list(reversed(real_get_list(*args, **kwargs)))

		with patch("frappe.get_list", side_effect=reversed_rows):
			self.assertEqual(self._names(f"{one} {two}"), [in_title, newer, older])

	def test_reversed_two_words(self):
		one, two = _word(), _word()
		article = self._article(f"<p>Lỗi {one} khi {two}</p>")

		self.assertEqual(self._names(f"{two} {one}"), [article])

	def test_limit(self):
		one, two = _word(), _word()
		both_a = self._article(f"<p>{one} {two}</p>")
		both_b = self._article(f"<p>{two} {one}</p>")
		self._article(f"<p>{one}</p>")

		self.assertEqual(set(self._names(f"{one} {two}", limit=2)), {both_a, both_b})
		self.assertEqual(len(self._names(f"{one} {two}", limit=3)), 3)

	def test_vietnamese_accents_distinguish(self):
		suffix = frappe.generate_hash(length=10).lower()
		accented = self._article(f"<p>Sai mã{suffix} khi in</p>")

		self.assertEqual(self._names(f"ma{suffix}"), [])
		self.assertEqual(self._names(f"mã{suffix}"), [accented])
		# NFC + casefold: a decomposed, upper-case query finds the same article
		self.assertEqual(self._names(unicodedata.normalize("NFD", f"MÃ{suffix.upper()}")), [accented])

	def test_whole_word_only(self):
		word = _word()
		self._article(f"<p>{word}xyz</p>")

		self.assertEqual(self._names(word), [])

	def test_empty_query_refused(self):
		for query in ("", "   ", "a b c", "!! ?", None):
			with self.subTest(query=query):
				with self.assertRaises(frappe.ValidationError) as caught:
					knowledge.search_kb_articles(query, 5)
				self.assertIn(EMPTY_QUERY, str(caught.exception))

	def test_tokenize(self):
		self.assertEqual(knowledge.tokenize("a Bé, x9 lỗi_in! đ"), ["bé", "x9", "lỗi_in"])
		self.assertEqual(knowledge.tokenize("Mã ma"), ["mã", "ma"])
		self.assertEqual(knowledge.tokenize(unicodedata.normalize("NFD", "MÃ")), ["mã"])
		words = [f"w{index}" for index in range(10)]
		self.assertEqual(knowledge.tokenize(" ".join(words)), words[:8])
		self.assertEqual(knowledge.tokenize(None), [])

	def test_scan_bounded_under_session_and_wildcards_escaped(self):
		self.assertEqual(knowledge.KB_SCAN_MAX, 200)
		suffix = frappe.generate_hash(length=10).lower()
		self._article(f"<p>ab{suffix}x</p>")

		with patch("frappe.get_list", wraps=frappe.get_list) as get_list:
			self.assertEqual(self._names(f"ab{suffix}_"), [])

		get_list.assert_called_once()
		args, kwargs = get_list.call_args
		self.assertEqual(args[0], "HD Article")
		self.assertEqual(kwargs["filters"], {"status": "Published"})
		self.assertEqual(kwargs["limit_page_length"], knowledge.KB_SCAN_MAX)
		self.assertNotIn("ignore_permissions", kwargs)
		patterns = [condition[-1] for condition in kwargs["or_filters"]]
		self.assertEqual(patterns, [f"%ab{suffix}\\_%", f"%ab{suffix}\\_%"])

	def test_no_helpdesk_search_import(self):
		tree = ast.parse(inspect.getsource(knowledge))
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				modules = [alias.name for alias in node.names]
			elif isinstance(node, ast.ImportFrom):
				modules = [node.module or ""]
			elif isinstance(node, ast.Constant) and isinstance(node.value, str):
				self.assertNotIn("helpdesk.api.article.search", node.value)
				self.assertNotIn("helpdesk.search", node.value)
				continue
			else:
				continue
			for module in modules:
				self.assertFalse(module.startswith("helpdesk"), module)
				self.assertFalse(module.startswith("erp_ai.erp_ai_agent"), module)


class TestSearchKb(KnowledgeCase):
	def test_excerpt_masked_before_cut(self):
		word = _word()
		# The match sits 150 characters after the start of `fake-kb`: cutting first would start the excerpt
		# on the bare value and drop the `password:` key that the masking needs.
		filler = "z" * 141
		self._article(f"password: fake-kb {filler} {word} {'w ' * 200}")

		rows = knowledge.search_kb_articles(word, 5)
		self.assertEqual(len(rows), 1)
		row = rows[0]

		self.assertNotIn("fake-kb", row["excerpt"])
		self.assertIn(word, row["excerpt"])

	def test_excerpt_300_chars_around_first_match_without_html(self):
		word = _word()
		self._article(f"<p>{'đầu ' * 200}</p><p><b>{word}</b> {'cuối ' * 200}</p>")

		rows = knowledge.search_kb_articles(word, 5)
		self.assertEqual(len(rows), 1)
		row = rows[0]

		self.assertEqual(len(row["excerpt"]), 300)
		self.assertIn(word, row["excerpt"])
		self.assertIn("đầu", row["excerpt"])
		self.assertIn("cuối", row["excerpt"])
		self.assertNotIn("<", row["excerpt"])

	def test_short_article_excerpt_whole_text(self):
		word = _word()
		name = self._article(f"<p>Cách xử lý {word}</p>")

		rows = knowledge.search_kb_articles(word, 5)
		self.assertEqual(len(rows), 1)
		row = rows[0]

		self.assertIn(frappe.db.get_value("HD Article", name, "title"), row["excerpt"])
		self.assertIn(f"Cách xử lý {word}", row["excerpt"])
