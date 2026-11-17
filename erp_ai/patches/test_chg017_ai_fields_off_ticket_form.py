from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import install
from erp_ai.agent.policy import OPT_OUT_FIELD
from erp_ai.patches import chg017_ai_fields_off_ticket_form as off_form

PATCHES_TXT = Path(__file__).resolve().parent.parent / "patches.txt"
PATCH_LINE = "erp_ai.patches.chg017_ai_fields_off_ticket_form"
TEMPLATE = install.TEMPLATE_NAME
# The row the app wrote before CHG-017 for a field the bot fills.
APP_ROW = {"required": 0, "visible_to": "Agents", "editable_after_creation": 0}


def post_model_sync_lines() -> list[str]:
	lines = [line.strip() for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()]
	section = lines[lines.index("[post_model_sync]") + 1 :]
	return [line for line in section if line and not line.startswith("#")]


def template_rows() -> list[tuple]:
	return [
		(r.idx, r.fieldname, r.required, r.visible_to, r.editable_after_creation)
		for r in frappe.get_all(
			"HD Ticket Template Field",
			filters={"parent": TEMPLATE},
			fields=["idx", "fieldname", "required", "visible_to", "editable_after_creation"],
			order_by="idx",
		)
	]


class TestAiFieldsOffTicketForm(FrappeTestCase):
	"""CHG-017: the rows the app put on the ticket form for the fields the bot fills are removed once; the field a
	person fills, other fields' rows and a row a person changed stay."""

	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		# The form as the app left it before CHG-017: a person's row, then one app row per AI field.
		frappe.db.delete("HD Ticket Template Field", {"parent": TEMPLATE})
		template = frappe.get_doc("HD Ticket Template", TEMPLATE)
		template.set("fields", [])
		template.append("fields", {"fieldname": "priority", "required": 1, "visible_to": "Everyone"})
		for name in install.ai_filled_fields():
			if name != "ai_created_labels":
				template.append("fields", {"fieldname": name, **APP_ROW})
		template.append("fields", {"fieldname": OPT_OUT_FIELD, **APP_ROW, "editable_after_creation": 1})
		template.flags.ignore_permissions = True
		template.save()

	def test_app_rows_of_fields_the_bot_fills_are_removed(self):
		off_form.execute()

		self.assertEqual(
			template_rows(),
			# the person's row as it was set up (editable after creation by Helpdesk's default)
			[(1, "priority", 1, "Everyone", 1), (2, OPT_OUT_FIELD, 0, "Agents", 1)],
		)

	def test_a_row_a_person_changed_is_kept(self):
		template = frappe.get_doc("HD Ticket Template", TEMPLATE)
		for row in template.fields:
			if row.fieldname == "ai_confidence":
				row.required = 1
			if row.fieldname == "ai_analysis":
				row.placeholder = "Bot ghi"
		template.flags.ignore_permissions = True
		template.save()

		off_form.execute()

		self.assertEqual(
			[row[1] for row in template_rows()],
			["priority", "ai_confidence", "ai_analysis", OPT_OUT_FIELD],
		)

	def test_second_execute_changes_nothing(self):
		off_form.execute()
		first = template_rows()

		off_form.execute()

		self.assertEqual(template_rows(), first)

	def test_no_template_no_error(self):
		frappe.db.delete("HD Ticket Template Field", {"parent": TEMPLATE})
		frappe.db.delete("HD Ticket Template", {"name": TEMPLATE})

		off_form.execute()

		self.assertFalse(frappe.db.exists("HD Ticket Template", TEMPLATE))

	def test_patch_listed_once_after_model_sync(self):
		self.assertEqual(post_model_sync_lines().count(PATCH_LINE), 1)
