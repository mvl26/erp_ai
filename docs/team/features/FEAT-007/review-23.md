Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 23 — FEAT-007 T23

- Diff: `git diff 6457c3c..44fb5d0` (nhánh `team/FEAT-007-task-23`, 1 commit, 1 file +142/−0)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `8d694c7` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): lần chạy đầu một test đỏ do chính test (trường chưa đặt đọc ra `None` trước khi lưu và `''` sau khi lưu); sau khi sửa helper cả 3 test xanh ngay (test ghim). Đỏ thử (sửa tạm rồi trả lại, kiểm bằng `cmp`): (1) bỏ `.save()`: `line 1127 self.assertEqual(set(LEFTOVER_SINGLES) & set(_stored_settings()), set())` `AssertionError: Items in the first set but not the second: 'erp_ai_rolled_back_switch'`; (2) dòng mồ côi mang `parentfield` thật: `line 1165 AssertionError: {'catalog_rules': ['s6i22svfmt'], 'user_templates': ['s6isri[52 chars]jh']} != {'catalog_rules': [], 'user_templates': [], 'prompt_revision[14 chars]qa']}`; (3) bỏ lệnh xóa Custom Field: `line 1199 self.assertFalse(frappe.get_meta("HD Ticket").has_field(CREATED_LABELS_FIELD))` `AssertionError: True is not false`; lần chạy đó `Ran 55 tests in 19.884s` / `FAILED (failures=3)`. GREEN (một lần giữ khóa): `MIGRATE_EXIT=0`; `test_install` `Ran 55 tests in 20.958s` `OK`; `test_architecture` `Ran 114 tests in 3.697s` `OK`.

### Báo cáo của reviewer (nguyên văn)

reviewer -> tech-lead | FEAT-007 T23 | approve

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 diff 6457c3c..44fb5d0` (1 commit, 1 file, +142/-0). Checklist 10/10 covered. Layer 1: criteria met. All three test names match the Expect line. The only file touched is the touchpoint, no product code changed and no existing test was edited (0 deleted lines).

No blocker or major findings.

**1. Do the three tests pin the downgrade behaviour?**
- **`test_leftover_single_rows_dropped_on_next_human_save` (:1111): yes.**
  - It first checks that the three leftover names are absent from the meta.
  - "Harmless before the save" is pinned in two ways: `get_single` loads with the same values, and the save does not raise.
  - "Dropped on the next save" is pinned by `& set() == set()` after `.save()`. Trial red 1 (save removed) turned it red.
  - The leftover values cover `"1"`, a text value and NULL.
- **`test_orphan_child_rows_do_not_break_get_single` (:1130): yes.**
  - Orphan rows exist in all three U0 child tables, plus one live row in the same table as one of them. Only the live row loads, both before and after the save.
  - `frappe.db.exists` checks that the save does not delete the orphans. That would break if a save deleted child rows by parent only.
  - Trial red 2 (giving the orphans their real `parentfield`) turned it red.
  - The tests use made-up names because a rolled-back field cannot be removed from the meta without DDL. This is fine: Frappe filters both singles and children by meta and `parentfield` only, which design.md:529 relies on.
- **`test_leftover_created_labels_column_does_not_break_ticket` (:1182): yes.**
  - After the delete, it checks that the meta no longer has the field while the column still exists.
  - An existing ticket loads and saves: the subject is updated and the leftover labels value stays in the column, so a save that wiped unknown columns would fail.
  - A new ticket inserts with NULL in the column.
  - It puts the record back and checks the meta has the field and `_labels_field() == field`.
  - Trial red 3 (delete removed) turned it red.

**2. STD-TEST-6 on the shared site: met.**
- Nothing in the diff commits. The class `setUp` (:709-716) does `rollback` and then `addCleanup(rollback)`, patches `updatedb` (so no DDL and no implicit commit) and calls `keep_agent_settings`.
- The Custom Field is removed with `frappe.db.delete` (no `on_trash`, so no DDL) and put back with `db_insert`, which skips `updatedb`.
- Cleanup when an assertion fails midway: cleanups run last-registered first. `put_record_back` runs first (registered before any destructive step), then `keep_agent_settings` restore, then `clear_document_cache` and `value_cache.pop`, then `rollback`.
  - The restore deletes every child row whose parent is ERP AI Setting, so the orphans go too. It also rewrites every `tabSingles` row, so the leftover rows go.
  - The HD Ticket meta cache is cleared before the rollback, and nothing rebuilds it before the rollback.
- Site values: tests 1 and 2 build their own state with `_fresh_settings`. Test 3 sets `enabled=0` itself. That makes `ticket_after_insert` (handlers.py:32-46) skip `enqueue_agent_run`, so no real job is queued. `set_single_value` clears the document cache (database.py:829).

**3. `_setting_values` treating `None` and `''` as the same: no weakening.**
- It only merges NULL and `""` for the same field. A human sees both as blank, and Frappe's `update_single` writes `""` for every valid field that was never set.
- A real value cleared to `""` would read as `None` and still fail against the stored value. A numeric field going from `None` to `0` is not merged.
- No STD-TEST-5 (the assertion is not bent to fit wrong behaviour) and no STD-TEST-8 gap.

**4. Markers: none.** The diff has none of the `test.skip_markers` and no `commit(`.

**Checklist (10)**
1. Scope matches, nothing extra. One borderline extra pin, see minor 1.
2. Touchpoint respected.
3. Edge cases covered. Red came from trial edits, as the task allows.
4. Tests are repeatable.
5. Errors: not applicable.
6. Security: no secrets, the raw SQL is parameterised, and the f-string only takes a constant column name.
7. Covers STD-OPS-2's down direction.
8. Names and style: see minor 2.
9. No new dependencies.
10. The commit `test(install): ... (FEAT-007)` follows STD-NAME-5, has no attribution trailer, and the branch is `team/FEAT-007-task-23`.

minor | — | — | 3 small points: (1) test_install.py:1124-1125 also pins that `install.after_migrate()` keeps the leftover rows ("a migrate neither fails nor drops the rows"). design.md:529 only requires them to go on the next human save, and a real downgrade runs the old version's `after_migrate`, not this one. The pin would block a later cleanup step in `after_migrate`. (2) test_install.py:1089/1098/1175: `_fresh_settings`, `_setting_values` and `_stored_labels` are instance methods (`_stored_labels` never uses `self`), while the helpers next to them (`_stored_settings`, `_labels_field`) are module-level (STD-STYLE-4). (3) test_install.py:1202 puts an HD Ticket meta without `ai_created_labels` in redis, where live processes on `miyano` can see it while the test runs. It is cleared before the rollback, and the existing test at :933 does the same | dev's call

**Not verifiable from the diff**
- Lint: dev's evidence has no `pre-commit run --all-files` output (STD-STYLE-2). Tech-lead to run it or ask for it.
- Scope question for tech-lead: design.md:529 also says the leftover columns of `ai_confidence_pct` (HD Ticket) and `ai_source_ticket` (HD Article) are harmless. T23's criteria and Expect only ask for `ai_created_labels`, so this is not a finding. Decide whether acceptance (`acceptance.md` reconciliation) covers the other two.
- I did not run the tests. Suggested check: `cmd.test_one` with `erp_ai/tests/test_install.py`.

Git commands used (read-only):
- `git -C <repo> log --oneline 6457c3c..44fb5d0`, `git -C <repo> diff --stat 6457c3c..44fb5d0`, `git -C <repo> diff 6457c3c..44fb5d0`
- `git -C <repo> log -1 --format='%B%n---%an' 44fb5d0`
- `git -C <repo> show 44fb5d0:{erp_ai/tests/test_install.py, erp_ai/test_utils.py, erp_ai/hooks.py, erp_ai/handlers.py, erp_ai/agent/policy.py}`
- `git -C <repo> grep -c "make_ticket(" 44fb5d0`

`<repo>` = `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007`

STD-short line read: "STD-OPS-2 (2) Write reversible migrations and test both the up and the down direction."

No new recurring defect, so memory is unchanged.

## Kết luận của tech-lead (mục "không kiểm được")

- Test sau merge và lint: xem dòng `progress:` của T23 trong `tasks.md` (một lần giữ khóa site từ worktree `feat-007` trên `8d694c7`).
- Phạm vi: `design.md:529` còn nói cột thừa của `ai_confidence_pct` (HD Ticket) và `ai_source_ticket` (HD Article) vô hại; tiêu chí và Expect của T23 chỉ đòi `ai_created_labels`. Không phải lỗ của task; chuyển team-leader để `/team:verify` quyết có đối soát hai cột kia không.
- Ba minor: deferred (dev tự quyết, không làm ở vòng này). Minor (1) (test ghim việc `after_migrate` giữ dòng thừa) ghi cho designer nếu sau này thêm bước dọn vào `after_migrate`.
