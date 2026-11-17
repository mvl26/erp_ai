from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import labels
from erp_ai.agent.routing import TagRule


class TestParseTags(FrappeTestCase):
	def test_tags_column_read_without_empty_and_helpdesk_tags(self):
		self.assertEqual(labels.parse_tags(",First Ticket,Stock, In ấn ,,"), ["Stock", "In ấn"])
		self.assertEqual(labels.parse_tags(None), [])
		self.assertEqual(labels.parse_tags(""), [])
		self.assertIn("First Ticket", labels.IGNORED_LABELS)


# CHG-014 (spec 2026-11-17-one-tag-design.md, design 2 and 4): the table is the list of tags the bot gives.
class TestTagChoices(FrappeTestCase):
	def test_choices_in_table_order_first_description_per_tag(self):
		rules = (
			TagRule("chấm công", "a@x.com", "", "Bảng công, đi muộn"),
			TagRule("tracecore", "b@x.com", "A", "Phần mềm Tracecore"),
			TagRule("Chấm Công", "c@x.com", "D", "khác"),
		)
		self.assertEqual(
			labels.tag_choices(rules),
			(("chấm công", "Bảng công, đi muộn"), ("tracecore", "Phần mềm Tracecore")),
		)

	def test_no_rules_no_choices(self):
		self.assertEqual(labels.tag_choices(()), ())


class TestChosenTag(FrappeTestCase):
	CHOICES = (("chấm công", "Bảng công"), ("tracecore", "Tracecore"))

	def test_a_choice_is_kept_with_the_table_spelling(self):
		self.assertEqual(labels.chosen_tag(("CHẤM CÔNG",), self.CHOICES), ("chấm công",))

	def test_a_tag_outside_the_table_is_dropped(self):
		self.assertEqual(labels.chosen_tag(("Stock",), self.CHOICES), ())
		self.assertEqual(labels.chosen_tag((), self.CHOICES), ())
		self.assertEqual(labels.chosen_tag(("tracecore",), ()), ())

	def test_only_the_first_label_counts(self):
		self.assertEqual(labels.chosen_tag(("Stock", "chấm công"), self.CHOICES), ())

	# CHG-016: a decomposed answer matches its table tag
	def test_decomposed_answer_matches(self):
		import unicodedata

		self.assertEqual(
			labels.chosen_tag((unicodedata.normalize("NFD", "CHẤM CÔNG"),), self.CHOICES), ("chấm công",)
		)


# CHG-018 (spec 2026-11-17-bot-new-tag-design.md, design 4): an answer outside the table with a description is a new
# tag, except on a noise ticket (F) or for a tag Helpdesk gives itself.
class TestNewTag(FrappeTestCase):
	CHOICES = (("chấm công", "Bảng công"),)

	def test_answer_outside_the_table_with_a_description_is_a_new_tag(self):
		self.assertEqual(labels.new_tag(("kế toán",), "Hóa đơn", "C", self.CHOICES), ("kế toán", "Hóa đơn"))
		self.assertEqual(labels.new_tag(("kế toán", "hr"), "Hóa đơn", "A", ()), ("kế toán", "Hóa đơn"))

	def test_no_new_tag(self):
		cases = {
			"table tag": (("Chấm công",), "x", "C"),
			"no description": (("kế toán",), "", "C"),
			"category F": (("kế toán",), "x", "F"),
			"no answer": ((), "x", "C"),
			"Helpdesk's own tag": (("first ticket",), "x", "C"),
		}
		for name, (answered, description, category) in cases.items():
			with self.subTest(name):
				self.assertIsNone(labels.new_tag(answered, description, category, self.CHOICES))
