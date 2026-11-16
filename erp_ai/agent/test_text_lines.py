from unittest import TestCase

from erp_ai.agent.text_lines import filled_lines


class TestFilledLines(TestCase):
	def test_trims_and_drops_blank_lines(self):
		self.assertEqual(filled_lines("a@x.vn\n\n  b@x.vn  \n \t \n"), ["a@x.vn", "b@x.vn"])

	def test_none_empty_and_whitespace_only_give_empty_list(self):
		for value in (None, "", "  ", "\n\n \t\n"):
			self.assertEqual(filled_lines(value), [], repr(value))

	def test_keeps_order_and_duplicates(self):
		self.assertEqual(filled_lines("b\na\nb\n"), ["b", "a", "b"])
