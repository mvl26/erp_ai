from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import change_text
from erp_ai.agent.change_text import apply_message, message_text, safe_person_name, undo_message


class TestChangeText(FrappeTestCase):
	def test_apply_message_template_and_preview(self):
		subject, body = apply_message("AICHG-00007", "HD-0042", "erp_ai/agent/policy.py", "Nguyễn Văn An")
		self.assertEqual(subject, "erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: Nguyễn Văn An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		self.assertEqual(
			message_text(subject, body),
			"erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: Nguyễn Văn An\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)

		self.assertEqual(change_text.APPROVER_PLACEHOLDER, "<người duyệt>")
		preview = message_text(
			*apply_message("AICHG-00007", "HD-0042", "erp_ai/agent/policy.py", "<người duyệt>")
		)
		self.assertEqual(
			preview,
			"erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Người duyệt: <người duyệt>\n"
			"Commit do ERP AI Agent tạo sau khi người duyệt bấm Duyệt.",
		)
		real = message_text(subject, body)
		self.assertEqual(
			[(a, b) for a, b in zip(preview.splitlines(), real.splitlines(), strict=True) if a != b],
			[("Người duyệt: <người duyệt>", "Người duyệt: Nguyễn Văn An")],
		)

	def test_undo_message_has_apply_commit_and_undoer(self):
		sha = "0123456789abcdef0123456789abcdef01234567"
		subject, body = undo_message(
			"AICHG-00007", "HD-0042", "erp_ai/agent/new_tool.py", sha, "Trần Thị Bình"
		)
		self.assertEqual(subject, "erp_ai: hoàn tác AICHG-00007 (erp_ai/agent/new_tool.py)")
		self.assertEqual(
			body,
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Commit áp dụng: 0123456789abcdef0123456789abcdef01234567\n"
			"Người hoàn tác: Trần Thị Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)
		self.assertEqual(
			message_text(subject, body),
			"erp_ai: hoàn tác AICHG-00007 (erp_ai/agent/new_tool.py)\n"
			"\n"
			"Đề xuất: AICHG-00007\n"
			"Phiếu: HD-0042\n"
			"Commit áp dụng: 0123456789abcdef0123456789abcdef01234567\n"
			"Người hoàn tác: Trần Thị Bình\n"
			"Commit do ERP AI Agent tạo sau khi người hoàn tác bấm Hoàn tác.",
		)

	def test_safe_person_name(self):
		anonymous = "(không hiện tên)"
		self.assertEqual(change_text.ANONYMOUS_PERSON, anonymous)
		cases = [
			# plain name is kept
			("Nguyễn Văn An", "Nguyễn Văn An"),
			# '@' anywhere -> anonymous
			("an@example.com", anonymous),
			("Nguyễn @An", anonymous),
			# '://' -> anonymous
			("https://evil.example/x", anonymous),
			("An ftp://host", anonymous),
			# newlines become one space
			("Nguyễn\nVăn\r\nAn", "Nguyễn Văn An"),
			("Nguyen" + chr(0x2028) + "An", "Nguyen An"),
			# control characters become a space (NUL and BEL are not whitespace for str.split)
			("Nguyễn\x00Văn\x07An\x1b", "Nguyễn Văn An"),
			("Nguyễn\tAn", "Nguyễn An"),
			# whitespace collapsed and trimmed
			("   Nguyễn    Văn   An  ", "Nguyễn Văn An"),
			# cut to 80 characters
			("a" * 200, "a" * 80),
			("Đ" * 200, "Đ" * 80),
			# cut, then no trailing space
			("a" * 79 + " bcd", "a" * 79),
			# '@' or '://' after the 80th character still -> anonymous
			("a" * 100 + "@", anonymous),
			("a" * 100 + "://", anonymous),
			# empty, blank, only control characters, None -> anonymous
			("", anonymous),
			("   ", anonymous),
			("\n\x00\x07", anonymous),
			(None, anonymous),
		]
		for raw, expected in cases:
			with self.subTest(raw=raw):
				self.assertEqual(safe_person_name(raw), expected)
