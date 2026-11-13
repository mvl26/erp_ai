# Review 16 — FEAT-001 T12 (custom field AI và dòng template)

Diff: `git diff ead8e36..team/FEAT-001-task-12`

## Round 1 — request-changes (head 86ca6ca)

major | STD-TEST-5 | erp_ai/tests/test_install.py:54-62 (and :73-101) | Same problem as review-13 (T11), confirmed. setUp resets roles, user and Singles but not the `ai_*` Custom Field rows or the Default template's AI rows. `cmd.migrate` (required by the task's Expect) has already committed those on `miyano`. So `test_ai_fields_permlevel_8_and_template_rows_agents_only` passes with the behavior removed: dropping `_ensure_ticket_custom_fields()` (install.py:34) or `"permlevel": AI_PERMLEVEL` (install.py:81) keeps it green, because `update=True` leaves the old permlevel 8 in place; changing `"visible_to": "Agents"` (install.py:154) to "Everyone" keeps it green, because the checked rows are the committed ones; `test_existing_template_row_preserved` does recreate rows, but it only checks row 1 and the count, never the `visible_to`/`required`/`editable_after_creation` of the 5 new rows. The automated part of AC-20 is therefore not proven. | Fix: in setUp, before `install.ensure_setup()`, add `frappe.db.delete("Custom Field", {"dt": "HD Ticket", "fieldname": ("like", "ai\\_%")})`, `frappe.db.delete("HD Ticket Template Field", {"parent": "Default", "fieldname": ("like", "ai\\_%")})` and `frappe.clear_cache(doctype="HD Ticket")`, so the create path runs inside the rolled-back transaction; in `test_existing_template_row_preserved`, also assert rows 2-6: fieldnames in order, `visible_to == "Agents"`, `required == 0`, and `editable_after_creation` set only for `ai_opt_out`; paste red output from removing `common["permlevel"]` and from changing `visible_to`, both runs on `miyano`.

minor | STD-DESIGN-4 | install.py:90-116 and :139-144 | repeats the AI field names as literals in two lists | derive the template list from the field list.
minor | STD-TEST-8 | test_install.py:99-102 | HD Customer check only queries Custom DocPerm and can never fail | check effective meta permissions.
minor | STD-TEST-6 | test_missing_template_is_skipped_with_warning | patches global `frappe.logger` | assert on `warning.call_args`.

## Round 2 — approve (scoped re-review, FIX_BASE 86ca6ca..021440c)

Diff: `git diff 86ca6ca..team/FEAT-001-task-12`. Cả 4 finding vòng 1 ADDRESSED (major STD-TEST-5; minor STD-DESIGN-4, STD-TEST-8, STD-TEST-6). Số vòng: 2. Merge b24ca80; migrate x2 exit 0; cmd.test `Ran 119 tests OK`; pre-commit exit 0; DB miyano: 6 Custom Field ai_*, 5 dòng template Default ai_*.

Deferred: `updatedb` bị patch trong setUp nên test đơn vị không bắt được cột thiếu, chỉ `cmd.migrate` x2 bắt (giữ bước này cho T13 trở đi); kiểm HD Customer pl 8 là guard hồi quy; `install.py` dựa vào section là `fields[0]` (minor).

Cannot verify (tech-lead resolves, vòng 1): `OPT_OUT_FIELD` định nghĩa trong install.py vì policy.py (T20) chưa có -> xung đột thứ tự kế hoạch, ghi vào deferred (T20 sẽ import/di chuyển); recreate Custom Field trong setUp có gây DDL commit hay không (dev kiểm khi chạy).
