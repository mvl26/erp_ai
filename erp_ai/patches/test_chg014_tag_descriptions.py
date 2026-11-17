from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import SETTING_DOCTYPE, TAG_ASSIGNEE_DOCTYPE
from erp_ai.patches import chg014_tag_descriptions
from erp_ai.test_utils import keep_agent_settings, make_active_agent, make_tag, set_tag_assignees

PREFIX = "ERPAI-TEST-"
PATCHES_TXT = Path(__file__).resolve().parent.parent / "patches.txt"
PATCH_LINE = "erp_ai.patches.chg014_tag_descriptions"


def post_model_sync_lines() -> list[str]:
	lines = [line.strip() for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()]
	section = lines[lines.index("[post_model_sync]") + 1 :]
	return [line for line in section if line and not line.startswith("#")]


def stored_rows() -> list[tuple[str, str]]:
	return [
		(row.tag, row.description)
		for row in frappe.get_all(
			TAG_ASSIGNEE_DOCTYPE,
			filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE},
			fields=["tag", "description"],
			order_by="idx",
		)
	]


class TestTagDescriptions(FrappeTestCase):
	"""CHG-014 review: rows made under CHG-011 have no description of their own (the guide said to write it on the Tag),
	so the next save of ERP AI Setting would refuse them and the classify step would list bare tag names."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.person = make_active_agent(self)

	def test_listed_after_model_sync(self):
		self.assertIn(PATCH_LINE, post_model_sync_lines())

	def test_empty_description_takes_the_tag_description_or_the_tag_name(self):
		make_tag(f"{PREFIX}HR", "Nhân sự, nghỉ phép")
		make_tag(f"{PREFIX}Kho", "mô tả trên Tag")
		set_tag_assignees(
			(f"{PREFIX}HR", self.person, "", ""),
			(f"{PREFIX}Phân quyền", self.person, "", " "),
			(f"{PREFIX}Kho", self.person, "", "Phiếu kho"),
		)

		chg014_tag_descriptions.execute()

		self.assertEqual(
			stored_rows(),
			[
				(f"{PREFIX}HR", "Nhân sự, nghỉ phép"),
				(f"{PREFIX}Phân quyền", f"{PREFIX}Phân quyền"),
				(f"{PREFIX}Kho", "Phiếu kho"),
			],
		)

	def test_tag_name_cleaned_when_it_can_be(self):
		set_tag_assignees((f"  {PREFIX}a   b ", self.person, "", "x"), ("x", self.person, "", "y"))

		chg014_tag_descriptions.execute()

		# a name no label rule accepts is left for the person to fix at the next save
		self.assertEqual(stored_rows(), [(f"{PREFIX}a b", "x"), ("x", "y")])

	def test_second_run_changes_nothing(self):
		set_tag_assignees((f"{PREFIX}HR", self.person, "", ""))
		chg014_tag_descriptions.execute()
		first = stored_rows()
		chg014_tag_descriptions.execute()
		self.assertEqual(stored_rows(), first)
