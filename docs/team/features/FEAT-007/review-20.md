Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 20 — FEAT-007 T20

- Diff: `git diff f300d0b..team/FEAT-007-task-20` (đầu `ea89003`, 2 commit: `382de19`, `ea89003`; 4 file +188/−8)
- Vòng: 2 (trần `max_rework` = 3). Vòng 1 `request-changes` (1 major), vòng 2 soát hẹp `approve`.
- Verdict: approve; merge `1cc3f42` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ; chỉ bỏ dòng cuối về bộ nhớ riêng của reviewer.

## Vòng 1 — request-changes

- Diff: `git diff f300d0b..382de19` (1 commit, 4 file +174/−8)
- Bằng chứng của dev: RED một lần giữ khóa có migrate, `MIGRATE_EXIT=0`: `'frm.set_df_property("prompt_revisions", "cannot_add_rows", 1);' not found in ...` (và `cannot_delete_rows`); `AssertionError: 0 != 1` (no_revision_without_change); `AssertionError: 0 != 2` (revisions_restored_on_save); `Lists differ: [] != [(1, 'classify', 'Administrator', datetime...` (row_on_change, override_cleared, per_changed_part); `Lists differ: [] != ['Bạn phân loại phiếu ...` (keeps_old_value_verbatim); `Tuples differ: ('Long Text', 1, 1) != ('Code', 1, 1)`; `Ran 100 tests in 6.815s` / `FAILED (failures=10)`. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 100 tests in 7.418s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.348s OK`; `test_install` `Ran 41 tests in 16.844s OK`; `test_architecture` `Ran 112 tests in 3.434s OK`.

### Báo cáo của reviewer (nguyên văn)

Verdict: request-changes

reviewer -> tech-lead | FEAT-007 T20 | request-changes

Diff: I read it with these commands:
- `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 log --format='%h %an %s%n%b' f300d0b..382de19`
- `git -C … diff --stat f300d0b..382de19` (4 files, +174/-8)
- `git -C … diff f300d0b..382de19`
- `git -C … show 382de19:<path>` for erp_ai_setting.py (validate order), erp_ai_setting.json (override field types), and test_erp_ai_setting.py (`_save`/`_stored`)

All 10 checklist items are covered. Layer 1: every criterion is implemented and the touchpoints are respected. One major is in the tests, not the code.

major | STD-TEST-8 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2363-2371 (same pattern at 2379-2384, 2395-2404) | AC-38 "who" is only checked against `frappe.session.user`. In the test runner that user is `Administrator`, which is also the owner of the Single. If the code wrote the literal `"Administrator"` (or `self.owner`) instead of `frappe.session.user`, every history test would stay green. The code at erp_ai_setting.py:241 is correct today, but no test catches that regression. | In setUp or the test, create a user with role System Manager (the rollback cleans it up), save as that user with `frappe.set_user(...)` (put `self.addCleanup(frappe.set_user, "Administrator")` in place first), and assert `changed_by` equals that user and not "Administrator". | confirmed (the session user is Administrator in bench run-tests; no test switches user)

minor | — | — | 4 small points: (1) Restore order (`order_by="idx"`, erp_ai_setting.py:215) is only half-pinned. Every row is written by one parent save, so the rows share `modified`, and with `order_by` removed `get_all` falls back to `modified desc` with ties. test_revisions_restored_on_save:2418-2432 would then go red only by chance. Rows that differ in `modified` would pin it. (2) For test_revisions_restored_on_save, the RED output stopped at the precondition (`0 != 2`), so the restore assertion itself was never shown red. By reading the code, removing the row on the doc would turn it red. (3) `get_singles_dict` is read twice in one validate (erp_ai_setting.py:201 and the new 239), STD-DESIGN-4. (4) The comment at erp_ai_setting.py:130 says the table is "written only by record_prompt_revisions", but the restore at :205 also writes it. | dev's call

Checklist:
1. pass (STD-DESIGN-5, STD-TEST-2):
   - `record_prompt_revisions` at erp_ai_setting.py:237-254 matches design.md:318: `old_value` raw, `""` when blank, `new_length = len(new)` with no strip.
   - Restore from the DB in idx order at :204-217 matches design.md:291.
   - Call order is restore first (:157), record after `check_prompt_overrides` and before `stamp_agent_enabled_at` (:174). This matches steps 1/12/13.
   - The three self-managed timestamp fields' restore is not rewritten.
   - The JSON matches design-w0-fixes-7 1a: Code, `read_only` 1 and `ignore_xss_filter` 1 kept, description unchanged, `modified` moved (erp_ai_prompt_revision.json:56, :72).
   - erp_ai_setting.js:3-5 sets both flags and adds no formatter.
   - setUp follows 1b (test:2253-2259).
   - All 6 named Expect tests are present. The 3 extra tests add coverage only.
2. pass (STD-DESIGN-1, STD-STRUCT-1): exactly the 4 touchpoint files, no new files, nothing in protected paths.
3. fail (STD-TEST-8 major above). RED shows failures=10, which matches the 9 new or changed tests (one of them has 2 subtests). There is no skip or xfail. Edge cases covered: override cleared, all three parts in one save, a non-prompt field changed.
4. pass (STD-TEST-5, STD-TEST-6):
   - The shape-line change (test:2328) and the verbatim-test rebuild (test:2337-2352) are both ordered by design-w0-fixes-7 1b.
   - The verbatim assertion itself is unchanged.
   - The clock is patched (`_save_at`).
   - The DB overrides and history are blanked before each test, and rollback is registered.
5. pass (STD-ERR-1, STD-ERR-2):
   - The server-side restore runs in validate, so tampering through the form, `frappe.client.save`, `set_value` or `delete` on the child goes through the parent save and is undone.
   - Record runs after all checks, so a refused save writes no row.
   - No external calls.
6. pass (STD-SEC-3, STD-SEC-4): `old_value` is shown as Code, which Desk escapes (design 1a), and the DB value stays raw on purpose. No secrets. The controller adds no permission-switch field name.
7. pass (STD-DESIGN-3, STD-OPS-2): Code and Long Text both map to a `longtext` column, so no data migration is needed. Reverting the JSON undoes it.
8. pass (STD-NAME-2, STD-STYLE-4/5): UPPER_SNAKE constants (erp_ai_setting.py:131-142), tab style matches the file, no dead code.
9. pass (STD-DEP-1): no new dependencies.
10. pass (STD-NAME-5, STD-GIT-8, STD-GIT-1): one commit, `feat(setting): record prompt override history on save (FEAT-007)`, no Co-Authored-By trailer, on branch team/FEAT-007-task-20.

Not verifiable from the diff:
- Whether Desk really renders `old_value` escaped in the row form and in a grid column added via "Configure Columns" (formatters.Code), and whether the add/delete buttons are really hidden on the form. Only a screen can show this; the test pins only the meta and the JS text.
- Whether `cmd.migrate` leaves the `tabERP AI Prompt Revision.old_value` column type and data unchanged on `miyano`.
- Whether the whole app stays green after the merge (tech-lead's post-merge run). I did not run tests; suggested command: `cmd.test_one erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`.
- Lint on the diffed files: I am relying on dev's statement; the ruff-format failure is on a base file outside the diff.

## Vòng 2 — approve (soát hẹp)

- Diff sửa: `git diff 382de19..ea89003` (1 commit, 1 file +14: `test_erp_ai_setting.py`)
- Ghi chú về nhánh: dev vòng 2 không `git switch` được vào `team/FEAT-007-task-20` (worktree của dev vòng 1 còn giữ nhánh), nên commit `ea89003` trên nhánh worktree của mình, cha duy nhất là `382de19`. Tech-lead xóa worktree của dev vòng 1 (sạch) rồi `git branch -f team/FEAT-007-task-20 ea89003` (tiến thẳng, không viết lại lịch sử).
- Bằng chứng của dev: RED với đột biến `changed_by = "Administrator"` trong `erp_ai_setting.py`: `AssertionError: Lists differ: [(1, 'classify', 'Administrator', ...)] != [(1, 'classify', 'erp-ai-prompt-editor@example.com', ...)]`, `Ran 101 tests in 6.785s`, `FAILED (failures=1)`; file sản phẩm trả lại (`git diff` rỗng). GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 101 tests in 7.267s` / `OK`; `test_doctype_descriptions` `Ran 12 tests in 0.342s` / `OK`; `test_install` `Ran 41 tests in 16.476s` / `OK`; `test_architecture` `Ran 112 tests in 3.457s` / `OK`. Bốn minor của vòng 1: dev không làm.

### Báo cáo của reviewer (nguyên văn)

Verdict: approve

reviewer -> tech-lead | FEAT-007 T20 | review round 2 (scoped re-review) | approve

Diff read with: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 log --format='%h %s%n%b' 382de19..ea89003`, `git -C … diff --stat 382de19..ea89003`, `git -C … diff 382de19..ea89003` (1 file, +14 lines). I also read whole files at the task head with `git show ea89003:erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (setUp at lines 2248-2259, helpers at 2261-2290, and the same user-switch pattern in TestCheckKeys at 476-504) and `git show ea89003:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (lines 236-256). STD-short read; its rule says "STD-TEST-8 (2) Test edge cases and error paths, not only the happy path."

**Round 1 finding**
- major | STD-TEST-8 | test_erp_ai_setting.py:2363-2371 | "who" only checked against `frappe.session.user` == Administrator == the Single's owner → **ADDRESSED**. Evidence: test_erp_ai_setting.py:2375-2387, new test `test_revision_row_names_the_saving_user`.
  - It creates `erp-ai-prompt-editor@example.com` with the System Manager role and registers `addCleanup(frappe.set_user, "Administrator")` before calling `frappe.set_user(editor)`. Cleanups run last-registered-first, so the user is switched back before the rollback from setUp (line 2249) undoes the user insert.
  - It saves through the normal `doc.save()` path (helper `_save`, line 2281), so permissions are checked as the editor.
  - It asserts the whole row with hard-coded values, `changed_by == editor`.
  - If the product wrote the literal `"Administrator"` or `self.owner` at erp_ai_setting.py:249, this assertion would fail. Dev's RED output shows the failure for the `"Administrator"` case: `[(1, 'classify', 'Administrator', ...)] != [(1, 'classify', 'erp-ai-prompt-editor@example.com', ...)]`, `FAILED (failures=1)`.
  - The test is repeatable (STD-TEST-6). The RED run inserted the same user and failed after the insert. If that user had survived the rollback, the GREEN run would have raised a duplicate-entry error on insert. It passed (`Ran 101 tests … OK`), so the rollback removed the user.
  - One test for this is enough. All three history tests named in round 1 read the same `changed_by` line (erp_ai_setting.py:249).

**New blocker/major from the fix:** none.

Checklist 10/10 against the fix diff:
1. Scope: test-only, does exactly what the finding asked.
2. Touchpoints: the existing test file only, no new files.
3. Failing test first: RED was pasted; no skip/xfail.
4. No assertion was loosened; the test is isolated by rollback and doesn't depend on site data.
5. Error handling: not applicable, the diff touches no product code.
6. Security: the test user is a throwaway `@example.com` address, and there are no secrets.
7. Contracts: not applicable, no product or contract change.
8. Naming and style: the test name states the behaviour, the code follows the file's existing pattern (TestCheckKeys `_become_hd_agent`), and there is no dead code.
9. Dependencies: none added.
10. Commit: `test(setting): pin prompt revision author to the session user (FEAT-007)` follows `type(scope): description (ID)`, the body is empty and there is no AI attribution trailer.

minor | — | — | 0 small points | —

**Not verifiable from the diff**
- RED and GREEN results come only from dev's pasted output; I ran no tests. To confirm, run `cmd.test_one` on erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py.
- The `--all-files` lint failure that dev reports in erp_ai/test_change_decision.py is outside this diff. Tech-lead should check that it is debt already on the base branch.

**Out of scope (deferred)**
- If the code wrote `self.modified_by` instead of `frappe.session.user`, the new test would still pass. That is not a regression, because Frappe sets `modified_by` from the session user on save. No action needed.

## Kết luận của tech-lead (mục "không kiểm được")

- Test sau merge: một lần giữ khóa site từ worktree `feat-007` trên `1cc3f42` (đã có T22, T121, T122), `MIGRATE_EXIT=0`; `test_erp_ai_setting` `Ran 101 tests in 6.887s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.341s OK`; `test_install` `Ran 44 tests in 16.813s OK`; `test_architecture` `Ran 114 tests in 3.459s OK`; `test_source` `Ran 122 tests in 6.829s OK`. Đạt. `cmd.test` cả bộ không chạy (chính sách N-6; mốc kế là M7).
- `cmd.migrate` với cột `old_value`: lần migrate trên thoát mã 0; `Code` và `Long Text` cùng là `longtext` (`design-w0-fixes-7.md` 1a dẫn `database.py:184-185`). Chưa ai đọc lại kiểu cột và dữ liệu trên site bằng lệnh; để `/team:verify` (ô `cmd.*` không có lệnh đọc schema).
- Desk hiện `old_value` đã escape ở form dòng và ở cột lưới thêm qua "Configure Columns"; nút thêm/xóa dòng lịch sử ẩn: chỉ màn hình cho thấy. Designer đã xác minh bằng đọc mã Frappe (`formatters.js:346-348`), chưa xem màn hình. Chuyển team-leader cho `/team:verify` (profile `ui: false`, cần người xem hoặc Playwright). Không phải lỗ có căn cứ, không tính là review trượt.
- Lint: tech-lead chạy `cmd.lint` trên `1cc3f42`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py`; file đó đỏ từ trước FEAT-007 (dòng DỪNG vòng 11 của `tasks.md`), T88 sẽ định dạng lại. Đạt.
- Bốn minor của vòng 1 (deferred, dev không làm): thứ tự khôi phục `idx` mới ghim một nửa; khẳng định khôi phục chưa từng được thấy đỏ; `get_singles_dict` đọc hai lần trong một `validate`; chữ comment `erp_ai_setting.py:130`. Điểm ngoài phạm vi của vòng 2 (`self.modified_by`): không cần làm.
