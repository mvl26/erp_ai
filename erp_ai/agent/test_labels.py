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
