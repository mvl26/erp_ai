"""CHG-017: the fields the bot fills leave the Helpdesk ticket form.

Before CHG-017 the install step added a row of HD Ticket Template `Default` for every AI field, so a person
creating a ticket saw a dozen fields only the bot fills; the ERP AI panel already shows them all. This removes,
once, each row of a field the bot fills that is still exactly as the app wrote it. A row a person changed since
(required, placeholder, url method, shown to everyone, editable after creation) stays, and so does the row of the
field a person fills (`ai_opt_out`). From now on the install step adds no such row (`install._ensure_template_rows`).
"""

import frappe

from erp_ai import install

# The row `_ensure_template_rows` wrote for a field the bot fills.
APP_ROW = {"required": 0, "visible_to": "Agents", "editable_after_creation": 0}


def _is_app_row(row, filled: set[str]) -> bool:
	return (
		row.fieldname in filled
		and all(row.get(key) == value for key, value in APP_ROW.items())
		and not row.get("placeholder")
		and not row.get("url_method")
	)


def execute():
	if not frappe.db.exists("HD Ticket Template", install.TEMPLATE_NAME):
		return
	filled = set(install.ai_filled_fields())
	template = frappe.get_doc("HD Ticket Template", install.TEMPLATE_NAME)
	kept = [row for row in template.fields if not _is_app_row(row, filled)]
	if len(kept) == len(template.fields):
		return
	for idx, row in enumerate(kept, 1):
		row.idx = idx
	template.set("fields", kept)
	template.flags.ignore_permissions = True
	template.save()
