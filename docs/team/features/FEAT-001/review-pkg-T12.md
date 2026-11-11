# Review package FEAT-001 T12 (BASE ead8e36..86ca6ca, branch team/FEAT-001-task-12)

Diff command: `git diff ead8e36..team/FEAT-001-task-12`

Commits:
- 86ca6ca feat(install): AI custom fields on HD Ticket and Default template rows (FEAT-001)

Stat: erp_ai/install.py (+106 -?), erp_ai/tests/test_install.py (+93); 197 insertions, 2 deletions

## Diff: erp_ai/install.py

```diff
 import frappe
+from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
 
-from erp_ai.constants import AGENT_USER, HELPDESK_AGENT_ROLE, ROLE_AGENT, ROLE_INSTRUCTOR, SETTING_DOCTYPE
+from erp_ai.constants import (AGENT_USER, HELPDESK_AGENT_ROLE, LOGGER_NAME, ROLE_AGENT, ROLE_INSTRUCTOR, SETTING_DOCTYPE)  # (wrapped one per line)
+
+TICKET_DOCTYPE = "HD Ticket"
+TEMPLATE_NAME = "Default"
+AI_MODULE = "ERP AI agent"
+AI_SECTION_FIELD = "ai_section"
+OPT_OUT_FIELD = "ai_opt_out"
+AI_PERMLEVEL = 8
@@ def ensure_setup() -> None:
 	_ensure_default_settings()
+	_ensure_ticket_custom_fields()
+	_ensure_template_rows()
@@ (appended)
+def _ensure_ticket_custom_fields() -> None:
+	# Keep the section where it was first placed; the last field of the meta changes once ours exist.
+	insert_after = frappe.db.get_value(
+		"Custom Field", {"dt": TICKET_DOCTYPE, "fieldname": AI_SECTION_FIELD}, "insert_after"
+	) or (frappe.get_meta(TICKET_DOCTYPE).fields[-1].fieldname)
+	common = {"permlevel": AI_PERMLEVEL, "module": AI_MODULE}
+	fields = [
+		{"fieldname": AI_SECTION_FIELD, "label": "ERP AI", "fieldtype": "Section Break", "insert_after": insert_after},
+		{"fieldname": "ai_resolution_hint", "label": "Hướng giải quyết (AI)", "fieldtype": "Text Editor", "read_only": 1},
+		{"fieldname": "ai_confidence", "label": "Độ tin cậy (AI)", "fieldtype": "Select", "options": "\nCao\nTrung bình\nThấp", "read_only": 1},
+		{"fieldname": "ai_classified_by", "label": "Phân loại bởi", "fieldtype": "Select", "options": "\nAI\nNgười", "read_only": 1},
+		{"fieldname": "ai_updated_at", "label": "AI cập nhật lúc", "fieldtype": "Datetime", "read_only": 1},
+		{"fieldname": OPT_OUT_FIELD, "label": "Không dùng AI cho phiếu này", "fieldtype": "Check"},
+	]
+	previous = None
+	for field in fields:
+		field.update(common)
+		field.setdefault("insert_after", previous)
+		previous = field["fieldname"]
+	create_custom_fields({TICKET_DOCTYPE: fields}, update=True)
+
+
+def _ensure_template_rows() -> None:
+	if not frappe.db.exists("HD Ticket Template", TEMPLATE_NAME):
+		frappe.logger(LOGGER_NAME).warning("HD Ticket Template %s not found; AI rows not added", TEMPLATE_NAME)
+		return
+	template = frappe.get_doc("HD Ticket Template", TEMPLATE_NAME)
+	present = {row.fieldname for row in template.fields}
+	missing = [name for name in ("ai_resolution_hint", "ai_confidence", "ai_classified_by", "ai_updated_at", OPT_OUT_FIELD) if name not in present]
+	for name in missing:
+		template.append("fields", {"fieldname": name, "required": 0, "visible_to": "Agents",
+			"editable_after_creation": 1 if name == OPT_OUT_FIELD else 0})
+	if missing:
+		template.flags.ignore_permissions = True
+		template.save()
```
(The above is a condensed rendering; the exact diff is the diff command. Formatting differences are ruff-format only.)

## Diff: erp_ai/tests/test_install.py (additions)

- `AI_FIELDS` tuple of the 6 fieldnames; `TEMPLATE = "Default"`; `_counts()` gains `ai_fields` (Custom Field count of `ai\_%` on HD Ticket) and `template_rows`.
- test_setup_twice_is_idempotent: additionally `assertEqual(before["ai_fields"], 6)` (before == after counts already asserted).
- test_ai_fields_permlevel_8_and_template_rows_agents_only: each of the 6 Custom Fields exists with permlevel 8 and module "ERP AI agent"; `ai_confidence.options == "\nCao\nTrung bình\nThấp"`; exactly 5 template rows for the AI fields except `ai_section`, each `visible_to == "Agents"`, `required == 0`, `editable_after_creation == 1` only for ai_opt_out; no Custom DocPerm on HD Ticket with permlevel 8 and role HD Customer.
- test_existing_template_row_preserved: wipes the template's rows, inserts one raw `priority` row (name `erp-ai-t12-keep`, idx 1, required 1, visible_to Everyone, editable_after_creation 1) via SQL, runs `ensure_setup()`, asserts 6 rows, first row unchanged, idx == [1..6].
- test_missing_template_is_skipped_with_warning: deletes the template, patches `install.frappe.logger`, runs `ensure_setup()`; `logger.assert_called_with(LOGGER_NAME)`, `warning.assert_called_once()`, template still absent.
- Existing setUp (reset + rebuild inside a rolled-back transaction, addCleanup rollback) unchanged.

Run `git diff ead8e36..team/FEAT-001-task-12` for the verbatim diff.
