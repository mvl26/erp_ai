from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import labels
from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.routing import TagRule
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE, TAG_ASSIGNEE_DOCTYPE
from erp_ai.test_utils import PREFIX, keep_agent_settings, pin_agent_roles, set_tag_assignees


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


class TestAddTagRow(FrappeTestCase):
	"""CHG-018 (spec 2026-11-17-bot-new-tag-design.md, design 5): a tag the bot made goes at the end of the tag table,
	with its description and no person; a tag the table has (any case) is not added again."""

	TAG = f"{PREFIX}kế toán"

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.addCleanup(frappe.set_user, "Administrator")

	def _rows(self):
		return frappe.get_all(
			TAG_ASSIGNEE_DOCTYPE,
			filters={
				"parent": SETTING_DOCTYPE,
				"parenttype": SETTING_DOCTYPE,
				"parentfield": "tag_assignees",
			},
			fields=["idx", "tag", "assignee", "category", "description", "bot_added"],
			order_by="idx",
		)

	def _add_as_agent(self, tag, description="Hóa đơn, công nợ"):
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		try:
			return labels.add_tag_row(tag, description)
		finally:
			frappe.set_user("Administrator")

	def test_a_new_tag_goes_at_the_end_without_a_person(self):
		set_tag_assignees((f"{PREFIX}hr", "a@x.com", "", "Nhân sự"))

		self.assertEqual(
			self._add_as_agent(self.TAG), {"ok": True, "added": True, "description": "Hóa đơn, công nợ"}
		)

		rows = self._rows()
		self.assertEqual([(row.idx, row.tag) for row in rows], [(1, f"{PREFIX}hr"), (2, self.TAG)])
		self.assertEqual(
			(rows[1].description, rows[1].assignee or "", rows[1].category or ""),
			("Hóa đơn, công nợ", "", ""),
		)
		# review fix I1: the row says the bot made it and nobody has read it yet
		self.assertEqual((rows[0].bot_added, rows[1].bot_added), (0, 1))
		# the Setting the next run reads has the row
		tags = [row.tag for row in frappe.get_single(SETTING_DOCTYPE).tag_assignees]
		self.assertEqual(tags, [f"{PREFIX}hr", self.TAG])

	def test_first_row_of_an_empty_table(self):
		set_tag_assignees()
		self.assertTrue(self._add_as_agent(self.TAG)["added"])
		self.assertEqual([(row.idx, row.tag) for row in self._rows()], [(1, self.TAG)])

	def test_a_tag_the_table_has_is_not_added_again(self):
		set_tag_assignees((f"{PREFIX}Kế Toán", "a@x.com", "C", "x"))
		self.assertEqual(self._add_as_agent(self.TAG), {"ok": True, "added": False})
		self.assertEqual([row.tag for row in self._rows()], [f"{PREFIX}Kế Toán"])

	def test_a_run_that_read_the_table_too_early_adds_no_second_row(self):
		set_tag_assignees()
		self._add_as_agent(self.TAG)
		# a second run whose read of the table came before the first run's row: the row's name comes from the tag
		with patch.object(labels, "_known_tag", return_value=False):
			self.assertEqual(self._add_as_agent(self.TAG), {"ok": True, "added": False})
		self.assertEqual([row.tag for row in self._rows()], [self.TAG])

	# review fix I2: a bot row a System Manager renamed does not keep the tag's old name taken
	def test_a_renamed_bot_tag_can_be_added_again(self):
		set_tag_assignees()
		self._add_as_agent(self.TAG)
		frappe.db.set_value(TAG_ASSIGNEE_DOCTYPE, {"tag": self.TAG}, "tag", f"{PREFIX}đổi tên")

		self.assertTrue(self._add_as_agent(self.TAG)["added"])
		self.assertEqual([row.tag for row in self._rows()], [f"{PREFIX}đổi tên", self.TAG])

	# review fix M3: the database takes two spellings differing in accents only for one tag (check_tag_assignees)
	def test_a_tag_differing_in_accents_only_is_not_added(self):
		set_tag_assignees((f"{PREFIX}ke toan", "a@x.com", "", "x"))
		self.assertEqual(self._add_as_agent(self.TAG), {"ok": True, "added": False})
		self.assertEqual([row.tag for row in self._rows()], [f"{PREFIX}ke toan"])

	# review fix I1: the description comes from ticket content; a secret in it is masked
	def test_the_description_is_masked(self):
		set_tag_assignees()
		description = "Lỗi đăng nhập Bearer abcdefgh12345678"
		result = self._add_as_agent(self.TAG, description)
		(row,) = self._rows()
		self.assertEqual(row.description, redact_secrets(description))
		self.assertEqual(result["description"], row.description)
		self.assertNotIn("abcdefgh12345678", row.description)

	# review fix I1: at most BOT_TAGS_UNREVIEWED_MAX rows nobody has read; a reviewed row does not count
	def test_unreviewed_bot_rows_are_capped(self):
		set_tag_assignees()
		for number in range(labels.BOT_TAGS_UNREVIEWED_MAX):
			self.assertTrue(self._add_as_agent(f"{PREFIX}tag {number}")["added"])

		self.assertEqual(
			self._add_as_agent(self.TAG), {"ok": False, "reason": labels.TOO_MANY_UNREVIEWED_TAGS}
		)
		self.assertEqual(len(self._rows()), labels.BOT_TAGS_UNREVIEWED_MAX)
		frappe.db.set_value(TAG_ASSIGNEE_DOCTYPE, {"tag": f"{PREFIX}tag 0"}, "bot_added", 0)
		self.assertTrue(self._add_as_agent(self.TAG)["added"])
		self.assertEqual(labels.BOT_TAGS_UNREVIEWED_MAX, 20)

	# review fix M4: a cached Setting does not hide the new row from the next run
	def test_the_cached_setting_sees_the_row(self):
		set_tag_assignees()
		self.assertEqual(frappe.get_cached_doc(SETTING_DOCTYPE).tag_assignees, [])
		self._add_as_agent(self.TAG)
		self.assertEqual(
			[row.tag for row in frappe.get_cached_doc(SETTING_DOCTYPE).tag_assignees], [self.TAG]
		)
