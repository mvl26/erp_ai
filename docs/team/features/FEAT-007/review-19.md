Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 19 — FEAT-007 T19

- Diff: `git diff 7b0aec1..team/FEAT-007-task-19` (vòng 1: 1 commit `7608e22`, 7 file +469/−6)
- Vòng: 2 (trần `max_rework` = 3); vòng 2: `git diff 7608e22..8d2fc5c`
- Verdict: approve (vòng 2); merge `f300d0b` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — request-changes

- Bằng chứng của dev: RED `FAILED (failures=30, errors=6)`, `AssertionError: None != 'Ghi đè prompt phân loại thiếu mục bắt buộc: "dau_muc"'`, `AssertionError: None != 20000`. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 92 tests … OK`; `test_doctype_descriptions` `Ran 12 tests … OK`; `test_architecture` `Ran 112 tests … OK`; `test_install` `Ran 37 tests … OK`. `field_count` 72 → 76, `section_count` 13 → 14.

### Báo cáo của reviewer (nguyên văn)

Layer 1: the code meets the T19 criteria and every name listed under Returns, and stays inside the touchpoints. One property gap in the new child DocType breaks the "giá trị cũ" part of AC-38 that T20 builds on. T20 cannot fix it, because the JSON is not one of T20's files.

**Tier 1 (does it match the spec and design?)**
- **Missing:** nothing from the T19 criteria.
  - `PROMPT_OVERRIDE_MAX_CHARS = 20000` and `PROMPT_REQUIRED_MARKERS` are present. `classify` has exactly the 11 keys of `design.md:314`, without `do_tin_cay_pct`. `reasoning` has the 4 headings. `category_guide` uses the regex `^\|\s*X\s*\|` in multiline mode, as `design.md:316` asks.
  - Both error strings match E-10 (`design.md:312-313`).
  - `check_prompt_overrides()` sits in the controller and runs after `check_kpi_targets` (step 11 before step 13). The core under `erp_ai/agent/**` does not import it; `git grep` found no use there.
  - The child DocType has the 5 fields with the types and options of `design.md:227`, all read-only. The section sits at row 13, between `budget_alert_sent_month` and `section_alerts`.
  - Counts went 72 → 76 and 13 → 14, which gives 76 / 14 from base 27 / 7. `read_only_fields` gained `prompt_revisions`. `DOCTYPE_CONFIG` has an entry for the child table.
  - `test_every_new_field_default` now asserts that 49 fields are covered (3 new default rows plus 3 Table fields) and that each one exists in meta.
- **Extra:** properties the design does not ask for.
  - `ignore_xss_filter: 1` on the 3 override fields. This is needed: `CLASSIFY_PROMPT` contains `<...>` placeholders and `&` (`prompts.py:20-32` and `:68-76`), so without it the built-in prompt would not save back unchanged. The test pins it.
  - `in_list_view` on 4 child fields and `editable_grid: 1`. These match the sibling `ERP AI User Template` and do no harm.
  - `TABLE_ROW_PART` and `PROMPT_OVERRIDE_FIELDS` are extra public names.
- **Misunderstood:** none. Two readings of the design that the dev made are acceptable: the 20000 limit is measured after trimming blanks at both ends, while the stored value keeps those blanks; the part names in error messages repeat the field label suffix.

### Phát hiện (chỉ blocker/major)

major | STD-TEST-2 | erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/erp_ai_prompt_revision.json:55 | `old_value` (Long Text) has no `ignore_xss_filter`, but it stores copies of the override text that the dev exempted from the XSS filter because of `<...>` and `&`. Frappe cleans child rows in `_validate()`, which runs after the controller's validate (`frappe/model/document.py:536-539`, child loop `:768 d._sanitize_content()`). So when T20 appends a row with `old_value` = the previous override (`design.md:318`), any text containing `<` will be stored HTML-escaped or stripped. The history then no longer holds the real old value (AC-38). T20's files do not include this JSON, so T20 cannot fix it without `DESIGN_CONFLICT`. The test `test_erp_ai_setting.py:2299` pins the child fields without this property. | Add `"ignore_xss_filter": 1` to `old_value`. Pin it in `test_prompt_section_and_child_doctype_shape` (add an `ignore_xss_filter` column to the child-field tuple at :2299), or better, add a save test: append a `prompt_revisions` row with `old_value=prompts.CLASSIFY_PROMPT`, save, and assert the stored value equals it. If the tech-lead prefers, add the JSON to T20's files instead and move the fix there. | confirmed (the mechanism is in Frappe source and the prompt text; the damage appears once T20 writes rows)

minor | — | — | 5 small points: (1) `TABLE_ROW_PART` (erp_ai_setting.py:123) is a public constant used only by `_has_marker`. (2) The description of `prompt_override_category_guide` is not pinned against its markers; `test_required_markers_match_design` only checks classify and reasoning. (3) The `prompt_revisions` description says "; không sửa được." where the design says ". Không sửa được." (the phrase check ignores case). (4) The length is measured after trimming, but the stored value keeps the surrounding blanks; whether U7 trims too cannot be checked yet. (5) `test_prompt_revisions_start_empty_after_install` deletes rows before install, so it only proves install adds none, the same pattern as its sibling tests. | dev's call

### Review checklist (10)

1. Does exactly and fully what the task asks (STD-DESIGN-5, STD-TEST-2): **fail.** All T19 criteria are met; the extras are justified or harmless. But the child schema cannot carry AC-38's "giá trị cũ" faithfully (the major above).
2. Touchpoints and file placement (STD-DESIGN-1, STD-STRUCT-1/2): **pass.** All 7 files are in `files:`, and the new DocType folder sits under the module's doctype directory.
3. Failing test first, edges, no skip (STD-TEST-1/8/4): **pass.** RED was `FAILED (failures=30, errors=6)` with the expected assertions. Edges covered: 20000 saves and 20001 is refused; blanks around the text; length checked before markers; each marker removed alone; two missing markers listed in constant order; quoted key vs unquoted; spaced cell vs indented row; blank and whitespace-only values; first bad part in form order. Each test fails if its behavior is removed: dropping `strip`, `re.MULTILINE`, the length check, the blank skip, or changing the order would turn a test red. No skip markers from `test.skip_markers`.
4. No test bent to fit, tests independent (STD-TEST-5/6): **pass.** Expected values are hard-coded (20000, the marker tuples, the error text). `setUp` calls `keep_agent_settings`, rolls back, and resets the KPI, COO and override fields, and asserts that this reset save succeeds, so bad data on the site fails the test loudly instead of hiding a problem.
5. Errors handled, input validated at the boundary (STD-ERR-1/2/5): **pass.** Validation happens on save with `frappe.throw`; nothing swallows errors; no external calls.
6. Security (STD-SEC-1/3/4/6): **pass.** No secrets, and no `protected_paths` touched. The `ignore_xss_filter` on the overrides is acceptable: the text goes to the model, the form shows it in a textarea, and only privileged settings users can edit it. The regex input is `re.escape`d.
7. Contracts and migration (STD-DESIGN-3, STD-OPS-2): **pass.** Fields are only added, all blank by default, and the migrate step is reported (`MIGRATE_EXIT=0`).
8. Names, structure, style, dead code (STD-NAME-1/2, STD-STYLE-4/5): **pass.** The child module and class follow the sibling pattern; no dead code. (One minor: the extra constant.)
9. Dependencies (STD-DEP-1/3/5): **pass.** Only the stdlib `re` was added.
10. Commit, branch, docs (STD-NAME-4/5, STD-GIT-1, STD-DOC-2): **pass.** The message reads `feat(setting): … (FEAT-007)` and has no AI trailer. It is one task commit on `team/FEAT-007-task-19`, which is the build's task-branch convention. The field descriptions serve as the user documentation.

### Không kiểm được từ diff (vòng 1) — tech-lead xử lý trước khi tick

- Whether U7 (`prompts.py` via the runner) trims the override before use. The 20000 limit counts characters after trimming, but the full stored value is what reaches the model.
- The GREEN lines (92 / 12 / 112 / 37 OK, `MIGRATE_EXIT=0`) come from the dev's handoff; I did not run them, because the site is shared.
- Restoring `prompt_revisions` on save, and `cannot_add_rows` / `cannot_delete_rows`, belong to T20. Until T20 lands, a user can post rows into the read-only table through the API.

**Read-only commands used:** `git log --oneline 7b0aec1..team/FEAT-007-task-19`, `git diff --stat …`, `git diff …`, `git log -1 --format='%an%n%B' team/FEAT-007-task-19`; `git show team/FEAT-007-task-19:<path>` cho `erp_ai/agent/prompts.py`, `erp_ai_prompt_revision.json`, `erp_ai_user_template.json`, `erp_ai_setting.py`, `test_erp_ai_setting.py`, `erp_ai/tests/test_doctype_descriptions.py`; `git grep -n ignore_xss_filter team/FEAT-007-task-19 -- erp_ai`; `git grep -n "prompt_override|PROMPT_REQUIRED|PROMPT_OVERRIDE" team/FEAT-007-task-19 -- erp_ai/agent/ erp_ai/install.py`; `git -C /home/miyano/frappe-bench/apps/frappe grep -n -A40 "def _sanitize_content" HEAD -- frappe/model/`; `git -C /home/miyano/frappe-bench/apps/frappe show HEAD:frappe/model/document.py` (735-775); grep/sed trên `tasks.md`, `design*.md`, `plan.md`, `spec.md`, `.team/profile.json`.

## Vòng 2 — approve (scoped re-review)

- Diff: `git diff 7608e22..team/FEAT-007-task-19` (đầu `8d2fc5c`, 1 commit, 2 file +20/−1).
- Bằng chứng của dev: RED (test hành vi chạy trước khi thêm thuộc tính, `MIGRATE_EXIT=0`): `FAIL: test_prompt_revision_keeps_old_value_verbatim`, `AssertionError: Lists differ: ['Bạn[215 chars] cố &amp; lỗi hệ thống — có cái đang hỏng. Dấu[3090 chars]ơn.'] != ['Bạn[215 chars] cố & lỗi hệ thống — có cái đang hỏng. Dấu hiệ[3044 chars]ơn.']`. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 93 tests in 6.192s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.340s OK`; `test_architecture` `Ran 112 tests in 3.384s OK`; `test_install` `Ran 37 tests in 16.069s OK`.

### Báo cáo của reviewer vòng 2 (nguyên văn)

**Round-1 finding**
- major | STD-TEST-2 | erp_ai_prompt_revision.json:55 | `old_value` had no `ignore_xss_filter` → **ADDRESSED**
  - `erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/erp_ai_prompt_revision.json:57` now has `"ignore_xss_filter": 1` on `old_value`. `modified` moved from 14:00 to 16:00, so migrate reloads the DocType. Dev reports MIGRATE_EXIT=0.
  - The dev took the reviewer's preferred option, a save test: `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2308-2324`, `test_prompt_revision_keeps_old_value_verbatim`. It first asserts that `CLASSIFY_PROMPT` contains `<` and `&`. `prompts.py:20,68-76` confirms both characters are there. It appends a `prompt_revisions` row, saves, and reads the row back from the database with `frappe.get_all(..., pluck="old_value")`, not from the in-memory doc. It requires the exact list `[old_value]`.
  - Would the test fail without the property? Yes. The dev's RED output shows the stored value with `&` escaped to `&amp;` (`Sự cố &amp; lỗi` != `Sự cố & lỗi`). The expected value is the real source constant, not a copy of the output. Isolation holds: `setUp` registers `frappe.db.rollback` and resets the overrides through `_save`. Old rows left on the site would make the test fail loudly, not hide a problem.
  - GREEN (one lock hold): test_erp_ai_setting 93 tests OK (92 + this one), descriptions 12 OK, architecture 112 OK, install 37 OK.

**New blockers/majors from the fix diff:** none.

**Round-1 points that regressed:** none. The whole-task stat still shows the same 7 touchpoint files, and the fix touched only 2 of them.

**Checklist (fix diff)** 1. Does what the task asks (STD-DESIGN-5/TEST-2): pass. AC-38 needs the real old value stored (design.md:318), and the new test proves it. 2. Touchpoints (STD-DESIGN-1/STRUCT-1): pass. Both files are in T19's `files:`. 3. Failing test first, no skip (STD-TEST-1/4/8): pass. The RED output is quoted and no skip markers were added. 4. No test bent to fit, tests independent (STD-TEST-5/6): pass. The expected value comes from the source constant, and each test rolls back. 5. Errors (STD-ERR-1/2/5): pass. No error handling changed. 6. Security (STD-SEC-1/3/4/6): pass, with a deferred note below. No secrets or `protected_paths` touched. 7. Contracts and migration (STD-DESIGN-3/OPS-2): pass. Only a field property was added; `modified` was bumped and migrate ran clean. 8. Names, style, dead code (STD-NAME/STYLE): pass. The test name and comment state the business meaning. 9. Dependencies: pass. None added. 10. Commit (STD-NAME-5/GIT-1/GIT-8): pass. The message is `fix(setting): keep prompt revision old_value out of the XSS filter (FEAT-007)` with no AI trailer, one commit on `team/FEAT-007-task-19`.

minor | — | — | 1 small point: the shape test's child-field tuple (test_erp_ai_setting.py:2296-2305) does not list `ignore_xss_filter` for `old_value`. The new save test covers the behavior, so this is optional. | dev's call

**Deferred (not blocking this round)**
- **T20, STD-SEC-3, suspected:** `old_value` is now stored raw and is read-only. Frappe shows read-only Long Text through `frappe.form.formatters.Text` → `Data` (`apps/frappe/frappe/public/js/frappe/form/formatters.js:256-273, 36-51`), and neither escapes HTML. So an override containing `<img onerror=…>` would run as script when someone opens a revision row. The only role with read and write on ERP AI Setting is System Manager (permissions in `erp_ai_setting.json`), and that role can already run scripts, so it gains no privilege. T20 owns `erp_ai_setting.js` and could escape or format `old_value` there.
- **T20, STD-TEST-6:** after `record_prompt_revisions()` exists, the `setUp` reset save in `TestPromptOverrides` will add a revision row whenever the site has a non-blank override. That would make `stored == [old_value]` fail. It fails loudly, so nothing is hidden. T20 should filter or clear `prompt_revisions` in that test or in `setUp`.

**Not verifiable from the diff**
- Whether Frappe's grid row form renders read-only Long Text through the formatter path above. I read the formatter source only, not the grid control.
- The RED and GREEN results come from the dev's quoted output. I did not run tests or migrate, because the site is shared.

**Commands used (read-only):** `git log --oneline 7608e22..team/FEAT-007-task-19`, `git diff --stat …`, `git diff …`; `git show team/FEAT-007-task-19:<path>` cho JSON bảng con, file test (2241-2310), `prompts.py`, `erp_ai_setting.json` (quyền; đọc bằng một lệnh `python3 -c` chỉ đọc), `tasks.md`, `design.md:311-318`; `git log -1 --format='%an%n%B' 8d2fc5c`; `git diff --stat 7b0aec1..team/FEAT-007-task-19`; `git -C /home/miyano/frappe-bench/apps/frappe grep` và đọc `frappe/public/js/frappe/form/formatters.js`.

## Kết luận của tech-lead (trước khi tick)

- Merge `f300d0b` (`git merge --no-ff team/FEAT-007-task-19`, 7 file +488/−6, không xung đột; nền đã có T21 `2ac3a4e`). Sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 93 tests in 6.137s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.343s OK`; `test_architecture` `Ran 112 tests in 3.561s OK`; `test_install` `Ran 41 tests in 17.059s OK` (41 = 37 + 4 test của T21). Khớp số của dev. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- U7 có cắt khoảng trắng của bản ghi đè trước khi dùng hay không: chưa có mã U7 trên nhánh; trần 20000 đo sau khi cắt, giá trị lưu giữ nguyên. Ghi cho kế hoạch U7; không chặn.
- Trước khi T20 merge, người dùng gửi được dòng vào bảng read-only qua API: đúng phạm vi đã chia (T20 khôi phục `prompt_revisions` khi lưu); T20 là task kế, cùng đợt, và `team/FEAT-007` chưa vào `develop`. Không chặn.
- Điểm "suspected" STD-SEC-3 (Desk hiện `old_value` thô, không escape): tech-lead đọc là có thật về cơ chế nhưng không thêm quyền cho ai (chỉ System Manager đọc và ghi ERP AI Setting, theo quyền trong `erp_ai_setting.json` mà reviewer đã đọc); CHƯA ai kiểm trên màn hình. Không tính là review chưa đạt của T19 (thuộc tính này do chính finding vòng 1 yêu cầu và AC-38 cần giá trị cũ nguyên văn). Việc escape ở `erp_ai_setting.js` không có trong dòng task T20, tech-lead không tự thêm → chuyển team-leader xin phán của designer trước khi gọi dev T20.
- Ghi chú STD-TEST-6 cho T20 (`setUp` của `TestPromptOverrides` sẽ sinh dòng lịch sử): `test_erp_ai_setting.py` nằm trong `files:` của T20; đưa vào lời bàn giao T20 như một điểm phải giữ xanh.

## deferred

- 5 điểm minor của vòng 1 và 1 điểm minor của vòng 2 (cột `ignore_xss_filter` trong test hình dạng).
- Cho designer/T20: escape `old_value` khi hiện (STD-SEC-3, suspected).
- Cho T20: `TestPromptOverrides.setUp` và dòng lịch sử (STD-TEST-6).
- Cho U7: cắt khoảng trắng của bản ghi đè trước khi dùng.
