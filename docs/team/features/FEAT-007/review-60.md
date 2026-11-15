Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 60 — FEAT-007 T60

- Diff: `git diff 5c395d5..e9dc6a0` (nhánh `team/FEAT-007-task-60`, 2 commit `df46ff4`, `e9dc6a0`; 2 file +265/−3)
- Vòng: 1 vòng review (trần `max_rework` = 3); 2 lần gọi dev (lần 1 trả `DESIGN_CONFLICT` chưa review; lần 2 sau quyết định 02:46 (a), (b), (d) của team-leader)
- Verdict: approve; merge `6457c3c` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED lần gọi 1, trước mã: `test_install` 52 test, `FAILED (failures=6, errors=1)` (`AssertionError: unexpectedly None`, `0 != 1`, `5 != 6`, `Lists differ: [] != [('Agent', 0, ...)]`, `ValidationError: Field ai_created_labels does not exist in Ticket`). Sau mã (lần gọi 1): `MIGRATE_EXIT=0`, `test_install` `Ran 52 tests in 19.683s FAILED (failures=1)` (`AssertionError: 11 != 10` ở `test_install.py:120`), `test_architecture` `Ran 112 tests in 3.429s OK`. RED lần gọi 2 (test mới trên mã `df46ff4`): `FAIL: test_article_field_skipped_when_doctype_missing` `AssertionError: 0 != 1`; `FAIL: test_article_perm_skipped_when_doctype_missing` `AssertionError: 'source ticket field' unexpectedly found in 'DocType HD Article not found; source ticket field and instructor permission not added'`; `FAIL: test_setup_twice_is_idempotent` `AssertionError: 11 != 10`; `Ran 52 tests in 21.535s` `FAILED (failures=3)`. GREEN lần gọi 2 (một lần giữ khóa): `MIGRATE_EXIT=0`; `test_install` `Ran 52 tests in 19.919s` `OK`; `test_architecture` `Ran 112 tests in 3.452s` `OK`.

### Báo cáo của reviewer (nguyên văn)

reviewer -> tech-lead | FEAT-007 T60 | approve

**Verdict: approve.** There are no blockers or majors. The code does what T60 and Chèn 2 ask, the six T60 tests would fail if the behaviour were removed, and checks (a), (b) and (d) all pass. There are three small points, listed under Findings.

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 diff 5c395d5..e9dc6a0` (2 files, +265/−3). All 10 checklist items are covered.

**Spec match (layer 1):**
- **Criteria met.** `ai_created_labels` is the last entry in `_ai_field_specs`: Small Text, `hidden`, `read_only`, `no_copy` (`install.py:200-208`). Its permlevel 8 and module come from the existing T22 path.
- **Chèn 2.** The template-row filter now skips hidden fields (`install.py:224-228`), and nothing deletes existing rows. Chèn 2 takes precedence over the "row created like every AI field" clause in Returns.
- **Permission function.** `_ensure_article_instructor_permission` is called right after `_ensure_task_permission` (`install.py:56`). It warns and returns when HD Article is missing. It runs `setup_custom_perms` first, then inserts one Instructor row (permlevel 0, read/report, `export: 0`) only if that role has no row yet, and edits nothing else (`install.py:322-343`). This matches ruling (1b), ruling (ii) and design Fix 4.
- **Touchpoints.** Only `erp_ai/install.py` and `erp_ai/tests/test_install.py` changed. No new files, no new dependencies, no `protected_paths`.
- **Nothing missing or extra.** I compared against the task's Tiêu chí, Chèn 2, Returns and Expect lines.

**Tests (layer 2):** I checked that each test would fail if its behaviour were removed.
- **Hidden-field filter removed:** `test_hidden_labels_field_has_no_template_row` fails (count would be 1).
- **Field missing or not placed last:** `test_created_labels_field_installed` fails (it checks `insert_after == "ai_opt_out"` and that `ai_opt_out`'s own anchor is unchanged).
- **`setup_custom_perms` dropped or moved after the insert:** `test_article_perms_of_other_roles_unchanged` fails.
- **`export: 0` dropped:** the per-flag check over all `rights` plus `if_owner` fails.
- **Existence check narrowed to the exact flags:** `test_second_setup_keeps_labels_field_and_article_perms` fails. A human edits the row to `export=1` and the test expects no second row and an identical snapshot.
- **Missing-DocType guard removed:** `test_article_perm_skipped_when_doctype_missing` fails (wrong warning count and non-empty perms).
- **Changed pre-existing T22 test**, `test_article_field_skipped_when_doctype_missing` (`test_install.py:868-872`): the edit is legitimate under STD-TEST-5. T60's Returns adds a second "HD Article not found" warning, so the filter now excludes warnings that mention "permission". The test still catches the df46ff4 regression (merged message, so 0 warnings counted), as dev's call-2 RED output shows.
- **Extra test** `test_existing_template_row_of_hidden_field_kept` (`:958`): within scope. Chèn 2 says existing template rows are not deleted, and this test pins that. It is a guard and was not red against the old code (see Findings).
- **Unmodified tests:** `TestInstall::test_ai_fields_permlevel_8_and_template_rows_agents_only` has no hunk in the range, and neither does the `AI_FIELDS` constant.
- **Skip markers:** none of the profile's `skip_markers` appear in the diff. The grep hits are just words like "only" in names.
- **Rest of the checklist:**
  - Error handling: missing DocType gives a warning and a return, the same as T22.
  - Security: no secrets or injection; `ignore_permissions` is used only in install code, as in `_ensure_task_permission`.
  - Contracts: the change only adds a field and a row. Rollback is T23's job.
  - Naming and style: follows the file's existing style, no dead code.
  - Commits: subjects follow `type(scope): … (FEAT-007)`, the branch is `team/FEAT-007-task-60`, and there are no AI trailers.

**Required checks:**
- **(a) PASS.** Comparing `test_setup_twice_is_idempotent` at 5c395d5 (lines 106-113) and e9dc6a0 (lines 113-120), the only changed line is `self.assertEqual(before["ai_fields"], 10)` becoming `11` at `erp_ai/tests/test_install.py:120`. Every other line of the test is the same; only the line numbers moved by +7 because of the new constants block. `_counts()` (lines 66-76) has no hunk in the range.
- **(b) PASS.** At e9dc6a0, `install.py:269-271` logs `"DocType HD Article not found; source ticket field not added"` and returns. Fix commit e9dc6a0 restored it after df46ff4 had replaced it with `return  # _ensure_article_instructor_permission logs …`. The permission function has its own message, `"…; instructor permission not added"`.
- **(d) PASS.** Every T60 test that asserts on permissions first deletes all Custom DocPerm rows on HD Article:
  - `test_instructor_article_perm_read_report_only`
  - `test_article_perms_of_other_roles_unchanged`
  - `test_existing_article_custom_perm_kept`
  - `test_second_setup_keeps_labels_field_and_article_perms`
  - `test_article_perm_skipped_when_doctype_missing`

  So the stale `export=1` row on the site does not affect them. The three field and template tests make no permission assertions. Pre-existing tests that call `ensure_setup` count neither Custom DocPerm rows nor permissions. The tests should pass with or without the stale row; I did not run them.

**Findings:**
minor | — | — | 3 small points: (1) STD-GIT-2: df46ff4 on its own is red (`11 != 10`) and drops the T22 warning, so merge T60 as a squash, or at least never land df46ff4 alone; (2) `test_install.py:958` `test_existing_template_row_of_hidden_field_kept` passes against the base code too (it guards Chèn 2's "do not delete") and depends on the migrated `ai_created_labels` Custom Field already being on the site, because template validation needs it; it could call `install.ensure_setup()` before appending the row; (3) `test_install.py:981` compares only `(permlevel, read, report, write)` in the meta, so `export` is pinned only on the database row | dev's call

**Not verifiable from the diff:**
- The RED and GREEN results come only from dev's pasted output; I ran no tests. Suggested command: `cmd.test_one erp_ai/tests/test_install.py`, plus `test_architecture`.
- Whether `TestInstall` tests (which roll back only per class) leave the inserted HD Article Custom DocPerm rows or their redis meta in place on a site without the stale row. Tech-lead could run `test_install` once on a site without that row, or check at M7.
- Merge strategy for the two commits (minor point 1).
- The comment at `:901` says "rollback does not clear" redis meta. An earlier review in this project found that rollback does clear it, and I did not re-check here. The extra cleanup is harmless either way.

Git commands used (read-only): `git -C <wt> log --format='%h %s%n%b' 5c395d5..e9dc6a0`, `git -C <wt> diff --stat 5c395d5..e9dc6a0`, `git -C <wt> diff 5c395d5..e9dc6a0`, `git -C <wt> diff df46ff4..e9dc6a0 -- erp_ai/install.py`, `git -C <wt> show {5c395d5,e9dc6a0}:erp_ai/tests/test_install.py`, `git -C <wt> show e9dc6a0:erp_ai/install.py`, where `<wt>` = `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007`. Standards line read from STD-short: "STD-TEST-5 (2) Do not change an assertion to match wrong behavior; change a test only when the spec changes."

## Kết luận của tech-lead (mục "không kiểm được")

- Test sau merge: một lần giữ khóa site từ worktree `feat-007` trên `6457c3c`, `MIGRATE_EXIT=0`; `test_install` `Ran 52 tests in 19.129s` `OK`; `test_architecture` `Ran 114 tests in 3.457s` `OK`. Đạt.
- Site không có dòng `export=1`: không kiểm được trong lượt này, vì quyết định 02:46 (d) cấm mọi agent sửa dòng đó trên site `miyano`. Các test có khẳng định về quyền đều tự xóa dòng Custom DocPerm của HD Article trong giao dịch của test (reviewer đã đọc từng test). Để `/team:verify` chạy lại `test_install` sau khi người gỡ dòng đó. Không phải lỗ của task.
- Cách merge hai commit: merge `--no-ff` như mọi task trước của feature (`6457c3c`); `df46ff4` không bao giờ là đầu của `team/FEAT-007`, lịch sử theo cha thứ nhất của nhánh feature xanh ở mọi commit. Không squash để giữ đúng commit mà reviewer đã chấm.
- Chú thích ở `test_install.py:901` về cache meta: vô hại, không xử lý.
- Lint: `cmd.lint` trên `6457c3c` chỉ đỏ `ruff-format` ở `erp_ai/test_change_decision.py` (nợ nền; đã trả lại file).
- Ba minor: deferred (dev tự quyết, không làm ở vòng này).
