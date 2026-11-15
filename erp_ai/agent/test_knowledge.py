import ast
import errno
import inspect
import os
import unicodedata
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import knowledge
from erp_ai.test_utils import TempAppsRoot, keep_agent_settings, make_active_agent, set_agent_settings

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

	def test_html_blocks_do_not_glue_words(self):
		suffix = frappe.generate_hash(length=10).lower()
		end, start = f"in{suffix}", f"mã{suffix}"
		li_end, li_start = _word("li"), _word("li")
		br_end, br_start = _word("br"), _word("br")
		blocks = self._article(f"<p>Lỗi {end}</p><p>{start.upper()} hàng</p>")
		items = self._article(f"<ul><li>{li_end}</li><li>{li_start}</li></ul>")
		line_break = self._article(f"<p>{br_end}<br>{br_start}</p>")

		# word at the end of one block, word at the start of the next
		self.assertEqual(self._names(end), [blocks])
		self.assertEqual(self._names(start), [blocks])
		self.assertEqual(self._names(f"{li_end} {li_start}"), [items])
		self.assertEqual(self._names(f"{br_start} {br_end}"), [line_break])
		[row] = knowledge.search_kb_articles(start, 5)
		self.assertNotIn(f"{end}{start.upper()}", row["excerpt"])
		self.assertIn(end, row["excerpt"])
		self.assertIn(start.upper(), row["excerpt"])

	def test_less_than_as_text_or_entity_keeps_words(self):
		typed_before, typed_after = _word("lt"), _word("lt")
		entity_before, entity_after = _word("lt"), _word("lt")
		typed = self._article(f"<p>{typed_before} < 5 {typed_after}</p>")
		entity = self._article(f"<p>{entity_before}&lt;{entity_after}&gt;</p>")

		self.assertEqual(self._names(typed_before), [typed])
		self.assertEqual(self._names(typed_after), [typed])
		self.assertEqual(self._names(f"{entity_before} {entity_after}"), [entity])
		# the editor stores a typed `<` as `&lt;`: the words on both sides stay apart in the excerpt
		[row] = knowledge.search_kb_articles(typed_after, 5)
		self.assertIn(f"{typed_before} &lt; 5 {typed_after}", row["excerpt"])

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

	def test_text_words_not_capped(self):
		words = [f"w{index}" for index in range(20)]
		self.assertEqual(knowledge.text_words(" ".join(words)), set(words))
		self.assertEqual(knowledge.tokenize(" ".join(words)), words[:8])
		# same rules as `tokenize`: NFC + casefold, words of at least 2 characters, duplicates once
		self.assertEqual(knowledge.text_words("a Bé, x9 lỗi_in! đ BÉ"), {"bé", "x9", "lỗi_in"})
		self.assertEqual(knowledge.text_words(unicodedata.normalize("NFD", "MÃ Mã")), {"mã"})
		for blank in (None, "", "   ", "a b c", "!! ?"):
			with self.subTest(text=blank):
				self.assertEqual(knowledge.text_words(blank), set())

	def test_plain_text_keeps_block_words_apart(self):
		self.assertEqual(knowledge.text_words(knowledge.plain_text("<p>một</p><p>hai</p>")), {"một", "hai"})
		# inline tags do not split a word
		self.assertEqual(knowledge.text_words(knowledge.plain_text("<b>ha</b>i")), {"hai"})
		self.assertEqual(knowledge.plain_text("<b>ha</b>i"), "hai")
		# nested blocks, any case, self-closing, a block tag never closed
		self.assertEqual(
			knowledge.text_words(knowledge.plain_text("<DIV><ul><li>một<br/>hai</LI><li>ba<p>bốn")),
			{"một", "hai", "ba", "bốn"},
		)
		# entities stay as text (no unescaping): the words on both sides of one stay apart
		self.assertEqual(knowledge.plain_text("<p>một&lt;hai</p>"), " một&lt;hai ")
		for blank in (None, ""):
			with self.subTest(html=blank):
				self.assertEqual(knowledge.plain_text(blank), "")

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

	def test_secret_split_by_inline_tag_fully_masked(self):
		word = _word()
		self._article(
			f"<p>{word} password: <b>fake-ab</b>cdkb</p><p>khoá sk-<i>fakekbabcdef</i>0123456789 hết</p>"
		)

		[row] = knowledge.search_kb_articles(word, 5)

		self.assertIn(word, row["excerpt"])
		for part in ("fake-ab", "cdkb", "fakekbabcdef", "0123456789"):
			self.assertNotIn(part, row["excerpt"])

	def test_excerpt_password_with_ampersand_masked(self):
		word = _word()
		# The editor stores `&` as `&amp;`; the excerpt is masked without decoding the entity (K-4).
		self._article(f"<p>{word} mật khẩu: fakepw&amp;tailFAKE</p>")

		[row] = knowledge.search_kb_articles(word, 5)

		self.assertIn(word, row["excerpt"])
		self.assertIn("[đã che]", row["excerpt"])
		self.assertNotIn("fakepw", row["excerpt"])
		self.assertNotIn("tailFAKE", row["excerpt"])

	def _raw_excerpt(self, content, query):
		"""Excerpt of one row whose content is this raw HTML (the editor's sanitizer would rewrite the tags)."""
		row = frappe._dict(name="raw", title="", content=content, modified="2025-01-01 00:00:00")
		with patch("frappe.get_list", return_value=[row]):
			[found] = knowledge.search_kb_articles(query, 5)
		return found["excerpt"]

	def test_inline_tag_does_not_split_word(self):
		anchor, head, tail = _word("an"), _word("in"), _word("in")
		tags = (
			"b",
			"I",
			"EM",
			"strong",
			"span class='x'",
			"a href='#'",
			"code",
			"u",
			"s",
			"mark",
			"sub",
			"sup",
		)
		cut = _word("tg")
		cut_by_tags = (
			"".join(f"<{tag}>{cut[index]}</{tag.split()[0]}>" for index, tag in enumerate(tags))
			+ cut[len(tags) :]
		)

		excerpt = self._raw_excerpt(f"<p>{anchor} {head}<B>{tail}</B> {cut_by_tags}</p>", anchor)

		self.assertIn(f"{anchor} {head}{tail} {cut}", excerpt)

	def test_block_tag_separates_words_any_case_closing_or_self_closing(self):
		words = [_word("bl") for _index in range(8)]
		content = (
			f"<P>{words[0]}</P><DIV>{words[1]}</DIV>{words[2]}</LI>{words[3]}"
			f"<br/>{words[4]}<BR />{words[5]}<H2>{words[6]}</h2><td>{words[7]}</td>"
		)

		excerpt = self._raw_excerpt(content, words[0])

		self.assertEqual(knowledge._words(excerpt), words)

	def test_short_article_excerpt_whole_text(self):
		word = _word()
		name = self._article(f"<p>Cách xử lý {word}</p>")

		rows = knowledge.search_kb_articles(word, 5)
		self.assertEqual(len(rows), 1)
		row = rows[0]

		self.assertIn(frappe.db.get_value("HD Article", name, "title"), row["excerpt"])
		self.assertIn(f"Cách xử lý {word}", row["excerpt"])


class TestManuals(FrappeTestCase):
	"""AC-47 (`design.md:491`): sections of the `.md` files in the manuals directory, ranked like the KB search."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.sandbox = TempAppsRoot(self, apps=("myapp",))
		set_agent_settings(manuals_dir="myapp/docs")

	def _manual(self, rel, text):
		return self.sandbox.write(os.path.join("myapp", "docs", rel), text)

	def _search(self, query, limit=10, manuals_dir="myapp/docs", **kwargs):
		return knowledge.search_manuals(query, limit, manuals_dir, **kwargs)

	def _found(self, query, **kwargs):
		return [(row["document"], row["line"]) for row in self._search(query, **kwargs)]

	def test_match_returns_document_heading_line(self):
		word = _word("mn")
		self._manual("sub/hdsd.md", f"Lời mở đầu\n# Đăng nhập\nnội dung\n## Lỗi in\ndòng {word}\n")

		self.assertEqual(
			self._search(word),
			[
				{
					"document": "sub/hdsd.md",
					"heading": "Lỗi in",
					"line": 4,
					"excerpt": f"## Lỗi in\ndòng {word}",
				}
			],
		)

	def test_no_match_empty(self):
		self._manual("hdsd.md", "# Đăng nhập\nnội dung\n")

		self.assertEqual(self._search(_word("mn")), [])

	def test_unconfigured_none(self):
		self._manual("hdsd.md", "# Đăng nhập\nnội dung\n")
		for value in ("", "   ", None):
			with self.subTest(manuals_dir=value):
				self.assertIsNone(self._search("đăng nhập", manuals_dir=value))

	def test_empty_query_refused(self):
		for query in ("", "a b", None):
			with self.subTest(query=query):
				with self.assertRaises(frappe.ValidationError) as caught:
					self._search(query)
				self.assertIn(EMPTY_QUERY, str(caught.exception))

	def test_sections_cut_at_hash_lines(self):
		one, two = _word("mn"), _word("mn")
		self._manual(
			"hdsd.md",
			f"# Phần một\n{one}\n# Phần hai\n{two}\n#Không cách\n{one} {two}\n  # thụt lề không phải mục\n",
		)

		rows = self._search(f"{one} {two}")

		self.assertEqual(
			[(row["heading"], row["line"]) for row in rows],
			[
				("Không cách", 5),
				("Phần một", 1),
				("Phần hai", 3),
			],
		)
		self.assertEqual(rows[1]["excerpt"], f"# Phần một\n{one}")
		self.assertNotIn(two, rows[1]["excerpt"])
		self.assertIn("thụt lề", rows[0]["excerpt"])

	def test_text_before_first_heading(self):
		word = _word("mn")
		self._manual("hdsd.md", f"Giới thiệu {word}\n# Mục\nkhác\n")

		self.assertEqual(
			self._search(word),
			[{"document": "hdsd.md", "heading": "", "line": 1, "excerpt": f"Giới thiệu {word}"}],
		)

	def test_rank_by_matched_words_then_heading_matches(self):
		one, two = _word("mn"), _word("mn")
		self._manual("a.md", f"# Mục\n{one}\n")
		self._manual("b.md", f"# Mục\n{one} {two}\n")
		self._manual("c.md", f"# {one}\n{two}\n")

		self.assertEqual(self._found(f"{one} {two}"), [("c.md", 1), ("b.md", 1), ("a.md", 1)])

	def test_limit(self):
		word = _word("mn")
		for name in ("a.md", "b.md", "c.md"):
			self._manual(name, f"# Mục\n{word}\n")

		self.assertEqual(self._found(word, limit=2), [("a.md", 1), ("b.md", 1)])
		self.assertEqual(len(self._search(word, limit=3)), 3)

	def test_only_md_files_inside_the_manuals_dir(self):
		word = _word("mn")
		self._manual("hdsd.md", f"# Mục\n{word}\n")
		self._manual("ghi-chu.txt", f"# Mục\n{word}\n")
		self.sandbox.write("myapp/khac.md", f"# Mục\n{word}\n")
		self.sandbox.write("plain.md", f"# Mục\n{word}\n", root=self.sandbox.outside)
		os.symlink(
			os.path.join(self.sandbox.outside, "plain.md"),
			os.path.join(self.sandbox.root, "myapp", "docs", "link.md"),
		)
		os.symlink(self.sandbox.outside, os.path.join(self.sandbox.root, "myapp", "docs", "dir_out"))

		self.assertEqual(self._found(word), [("hdsd.md", 1)])

	def test_dangling_symlink_inside_the_manuals_dir_skipped(self):
		word = _word("mn")
		self._manual("hdsd.md", f"# Mục\n{word}\n")
		docs = os.path.join(self.sandbox.root, "myapp", "docs")
		os.symlink(os.path.join(docs, "khong-con.md"), os.path.join(docs, "cu.md"))

		self.assertEqual(self._found(word), [("hdsd.md", 1)])

	def test_dir_other_than_configured_or_outside_root_finds_nothing(self):
		word = _word("mn")
		self._manual("hdsd.md", f"# Mục\n{word}\n")
		self.sandbox.write("plain.md", f"# Mục\n{word}\n", root=self.sandbox.outside)

		for value in ("myapp", "../outside", self.sandbox.outside, "myapp/docs/../../myapp"):
			with self.subTest(manuals_dir=value):
				self.assertEqual(self._search(word, manuals_dir=value), [])
		self.assertEqual(self._found(word, manuals_dir=" myapp/docs/ "), [("hdsd.md", 1)])

	def test_at_most_max_files_scanned(self):
		self.assertEqual(knowledge.MANUALS_MAX_FILES, 500)
		word = _word("mn")
		for name in ("a.md", "b.md", "c.md"):
			self._manual(name, f"# Mục\n{word}\n")

		with patch.object(knowledge, "MANUALS_MAX_FILES", 2):
			self.assertEqual(self._found(word), [("a.md", 1), ("b.md", 1)])

	def test_file_over_one_mib_skipped(self):
		self.assertEqual(knowledge.MANUALS_FILE_MAX_BYTES, 1024 * 1024)
		word = _word("mn")
		head = f"# Mục\n{word}\n"
		self._manual("a_vua.md", head + "x" * (1024 * 1024 - len(head.encode())))
		self._manual("b_qua.md", head + "x" * (1024 * 1024 - len(head.encode()) + 1))

		self.assertEqual(self._found(word), [("a_vua.md", 1)])

	def test_time_budget(self):
		self.assertEqual(knowledge.MANUALS_BUDGET_S, 10)
		word = _word("mn")
		for name in ("a.md", "b.md", "c.md"):
			self._manual(name, f"# Mục\n{word}\n")
		# start, then one reading before each file: 9.99 s still scans b.md, 10 s stops before c.md
		ticks = iter([100.0, 100.0, 109.99, 110.0])

		self.assertEqual(self._found(word, clock=lambda: next(ticks)), [("a.md", 1), ("b.md", 1)])

	def test_excerpt_masked_before_cut(self):
		word = _word("mn")
		filler = "z" * 141
		self._manual("hdsd.md", f"# Mục\npassword: fake-mn {filler} {word} {'w ' * 200}\n")

		[row] = self._search(word)

		self.assertNotIn("fake-mn", row["excerpt"])
		self.assertIn(word, row["excerpt"])
		self.assertEqual(len(row["excerpt"]), knowledge.EXCERPT_MAX_CHARS)

	def test_decomposed_text_found_and_excerpt_nfc(self):
		suffix = frappe.generate_hash(length=10).lower()
		self._manual("hdsd.md", unicodedata.normalize("NFD", f"# Lỗi in\nSai mã{suffix}\n"))

		[row] = self._search(f"mã{suffix}")

		self.assertEqual(row["heading"], "Lỗi in")
		self.assertTrue(unicodedata.is_normalized("NFC", row["excerpt"]))
		self.assertEqual(self._search(f"ma{suffix}"), [])

	def test_unreadable_file_skipped_and_logged(self):
		"""`design-w1b-fixes-1.md` điểm 2: an `OSError` on one file skips it with one warning; other errors raise."""
		word = _word("mn")
		self._manual("sub/a.md", f"# Mục\n{word}\n")
		self._manual("b.md", f"# Mục\n{word}\n")
		real_open = open
		marker = "secret-detail-mn"

		def failing_open(names, make_error):
			def fake(path, *args, **kwargs):
				if os.path.basename(path) in names:
					raise make_error(path)
				return real_open(path, *args, **kwargs)

			return fake

		def run(names, make_error):
			logger = patch.object(knowledge.frappe, "logger")
			with (
				logger as get_logger,
				patch.object(knowledge, "open", side_effect=failing_open(names, make_error), create=True),
			):
				found = self._found(word)
			get_logger.assert_called_with(knowledge.source.LOGGER_NAME)
			calls = get_logger.return_value.warning.call_args_list
			lines = [call.args[0] % call.args[1:] if call.args[1:] else call.args[0] for call in calls]
			for line in lines:
				self.assertNotIn(self.sandbox.root, line)
				self.assertNotIn(marker, line)
			return found, lines

		errors = {
			"PermissionError": lambda path: PermissionError(errno.EACCES, marker, path),
			"FileNotFoundError": lambda path: FileNotFoundError(errno.ENOENT, marker, path),
			"OSError": lambda path: OSError(errno.EIO, marker, path),
		}
		for name, make_error in errors.items():
			with self.subTest(name):
				found, lines = run({"a.md"}, make_error)
				self.assertEqual(found, [("b.md", 1)])
				self.assertEqual(lines, [f"search_manuals skipped sub/a.md: {name}"])

		with self.subTest("both unreadable"):
			found, lines = run({"a.md", "b.md"}, errors["PermissionError"])
			self.assertEqual(found, [])
			self.assertEqual(
				lines,
				[
					"search_manuals skipped b.md: PermissionError",
					"search_manuals skipped sub/a.md: PermissionError",
				],
			)

		with self.subTest("not an OSError"):
			with patch.object(knowledge, "open", side_effect=ValueError(marker), create=True):
				with self.assertRaises(ValueError):
					self._found(word)

	def test_unreadable_file_logged_even_when_log_file_fails(self):
		"""`design-w1-fixes-14.md` Điểm 2: a log file that cannot be opened does not break the search."""
		word = _word("mn")
		self._manual("sub/a.md", f"# Mục\n{word}\n")
		self._manual("b.md", f"# Mục\n{word}\n")
		real_open = open

		def fake_open(path, *args, **kwargs):
			if os.path.basename(path) == "a.md":
				raise PermissionError(errno.EACCES, "denied", path)
			return real_open(path, *args, **kwargs)

		with (
			patch.object(knowledge, "open", side_effect=fake_open, create=True),
			patch.object(knowledge.frappe, "logger", side_effect=PermissionError(errno.EACCES, "log")),
			self.assertLogs(knowledge.source.LOGGER_NAME, "WARNING") as logs,
		):
			found = self._found(word)

		self.assertEqual(found, [("b.md", 1)])
		self.assertEqual(
			[record.getMessage() for record in logs.records],
			["search_manuals skipped sub/a.md: PermissionError"],
		)
