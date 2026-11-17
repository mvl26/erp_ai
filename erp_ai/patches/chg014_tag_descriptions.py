"""CHG-014: rows of the tag table made under CHG-011 get the description the bot now chooses by.

CHG-011 told the admin to write what a tag is for on the Tag record; CHG-014 reads a required description on the
row instead. A row with no description takes the Tag's description, or else the tag's own name, so the next save of
ERP AI Setting is not refused and the classify step does not list bare names. A tag name the label rule can clean is
stored clean; one it cannot is left for the person to fix at the next save. Running it again changes nothing.
"""

import frappe
from frappe.utils import strip_html

from erp_ai.agent.classification import clean_label
from erp_ai.constants import SETTING_DOCTYPE, TAG_ASSIGNEE_DOCTYPE


def execute():
	rows = frappe.get_all(
		TAG_ASSIGNEE_DOCTYPE,
		filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE},
		fields=["name", "tag", "description"],
	)
	for row in rows:
		values = {}
		label = clean_label(row.tag)
		if label and label != row.tag:
			values["tag"] = label
		if not (row.description or "").strip():
			on_tag = strip_html(frappe.db.get_value("Tag", row.tag, "description") or "").strip()
			values["description"] = on_tag or label or row.tag
		if values:
			frappe.db.set_value(TAG_ASSIGNEE_DOCTYPE, row.name, values, update_modified=False)
