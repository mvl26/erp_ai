Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 22 — FEAT-007 T22

- Diff: `git diff f300d0b..team/FEAT-007-task-22` (đầu `88d142a`, 1 commit, 2 file +129/−3)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `5c395d5` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ; chỉ bỏ hai dòng cuối (bộ nhớ riêng của reviewer, danh sách file đã đọc).

## Vòng 1 — approve

- Bằng chứng của dev: RED (`erp_ai.tests.test_install`, migrate exit 0): `test_confidence_pct_field_installed`: `AssertionError: unexpectedly None`; `test_article_source_field_installed_idempotent`: `AssertionError: unexpectedly None`; `test_article_field_skipped_when_doctype_missing`: `AssertionError: 0 != 1`; `test_setup_twice_is_idempotent`: `AssertionError: 9 != 10`; `Ran 44 tests in 17.747s` / `FAILED (failures=4)`. GREEN một lần giữ khóa: `MIGRATE_EXIT=0`; `test_install` `Ran 44 tests in 18.627s` `OK`; `test_architecture` `Ran 112 tests in 3.442s` `OK`.

### Báo cáo của reviewer (nguyên văn)

Verdict: approve

reviewer -> tech-lead | FEAT-007 T22 | approve

Git commands used (read-only):
- `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 log --format='%h %s%n%b' f300d0b..88d142a`
- `git -C <same> diff --stat f300d0b..88d142a` and `git -C <same> diff f300d0b..88d142a`
- `git -C <same> show 88d142a:erp_ai/install.py` and `git -C <same> show 88d142a:erp_ai/tests/test_install.py`, read only around the hunks and the fixtures
- One targeted read outside the diff: `grep '"fieldname": "category"'` in the helpdesk `hd_article.json` (line 32). It confirms the `insert_after` target exists.

The diff is one commit and touches 2 files (+129/−3), both inside the touchpoints. All 10 checklist items are covered. Layer 1: every criterion is met and nothing outside the scope was added. Tests run before code: each new test would fail if its behavior were removed.

Findings: none at blocker or major level.

minor | — | — | 3 small points: (a) the `AI_FIELDS` tuple at `erp_ai/tests/test_install.py:22-32` was not given `ai_confidence_pct`, so the existing loop at `test_ai_fields_permlevel_8_and_template_rows_agents_only` does not cover it; `test_confidence_pct_field_installed` covers it instead. (b) `test_article_field_skipped_when_doctype_missing` (test_install.py about line 815) has no AC/D docstring, unlike the two tests next to it. (c) The warning text at `install.py:216` does not use the `%s` form of the earlier template warning, which is harmless. | dev's call

Checklist:
1. Pass. The spec is done fully and with nothing extra.
   - `ai_confidence_pct` (Int, read-only) is added to `_ai_field_specs` right after `ai_confidence` (`install.py:155-160`). permlevel 8 and `module` come from `common` (`install.py:123`).
   - `_ensure_article_source_field` is called after `_ensure_task_ticket_field` (`install.py:54`). It creates a Link to HD Ticket with read_only 1, search_index 1, module set, after `category`, using `update=False` (`install.py:253-274`).
   - When HD Article is missing, it logs a warning and returns (`install.py:254-256`).
2. Pass. Only `erp_ai/install.py` and `erp_ai/tests/test_install.py` changed, and no new files were added.
3. Pass. Dev's RED output shows 4 failures that match the 4 changed or new tests. Edge and error paths are tested:
   - the missing-DocType path checks one warning plus no field (test_install.py about 815-830);
   - a human edit survives `after_migrate`;
   - running twice leaves count = 1.
   - No skip, xfail or only markers in the diff.
   - Each test fails if its behavior is removed: `update=True` would reset the label and fail the edit check; removing the guard would create the field and log no warning; wrong placement fails both `insert_after` checks.
4. Pass. The changed assertions (9→10 at test_install.py:113 and :164, plus the idx list and fieldname order at :177-183) follow the spec change from AC-22 / D-14. They are not bent to fit wrong behavior. The new tests run inside `TestFeat007Migrate.setUp`, which rolls back and patches `updatedb` (test_install.py:656-663). The Custom Field deletes and re-creates therefore stay in the rolled-back transaction with no DDL implicit commit, and each test seeds its own state.
5. Pass. The missing-DocType path logs with context (`install.py:255`). No error is swallowed and there are no external calls.
6. Pass. No secrets, queries built from input, permission changes or sensitive data in logs. The new ticket field gets permlevel 8, the same as the other AI fields.
7. Pass. The change only adds fields, and install only fills what is missing (`update=False` for the article field), following ADR-006. Existing ticket fields keep their `update=True` path; this task did not change it.
8. Pass. Constants follow the module's existing style (`ARTICLE_DOCTYPE`, `ARTICLE_SOURCE_FIELD`, `install.py:23-24`). The new function mirrors `_ensure_task_ticket_field`. No dead code.
9. Pass. No new dependencies.
10. Pass. The commit message is `feat(install): add ai_confidence_pct ticket field and ai_source_ticket article field (FEAT-007)` and has no Co-Authored-By trailer. The branch is `team/FEAT-007-task-22`, there is one commit for the task, and the change has no user-doc impact at task level.

Not verifiable from the diff:
- Tests were not run here (shared site). Dev reports GREEN as test_install 44 OK and test_architecture 112 OK; tech-lead should run `erp_ai.tests.test_install` after the merge.
- **Upgrade path on an existing site:**
  - On an existing site, `_ensure_template_rows` appends the `ai_confidence_pct` template row after `ai_opt_out` (last idx), not after `ai_confidence`. The design accepts this ("tự thêm như các trường AI khác"). Whether the helpdesk agent UI shows it in an acceptable place needs a screen check.
  - On a real migrate, `updatedb` is not patched, so the HD Article column and its index get created by real DDL. This only shows on a real `bench migrate`, including that `search_index` 1 creates the index.
- Lint: dev reports `pre-commit` red only on ruff-format in `erp_ai/test_change_decision.py`, which is old debt and not in this diff.

Tests not run (suggested command: `cd ../.. && bench --site miyano run-tests --module erp_ai.tests.test_install`).

## Kết luận của tech-lead (mục "không kiểm được")

- Test sau merge: một lần giữ khóa site từ worktree `feat-007` trên `5c395d5`, `MIGRATE_EXIT=0`; `test_install` `Ran 44 tests in 17.088s OK`; `test_architecture` `Ran 112 tests in 3.448s OK`. Đạt.
- DDL thật: lần `cmd.migrate` đó chạy không vá `updatedb` và thoát mã 0, nên cột `ai_source_ticket` của HD Article và chỉ mục của nó đã được tạo trên site `miyano` mà không lỗi. Chưa ai đọc lại `SHOW INDEX`; để `/team:verify`.
- Chỗ đứng của dòng mẫu phiếu `ai_confidence_pct` trên site đã có (cuối danh sách): thiết kế chấp nhận; cần xem màn hình ở `/team:verify`. Không phải lỗ của task.
- Lint: `cmd.lint` trên `5c395d5` chỉ đỏ `ruff-format` ở `erp_ai/test_change_decision.py` (nợ nền, có từ trước FEAT-007; đã trả lại file).
- Ba minor: để dev tự quyết, không làm ở vòng này (deferred).
- Ghi chú cho T60: số ghim trường `ai_` (`test_install.py:113`, nay `:120` trên nhánh T60) vừa đổi 9 → 10 ở task này sẽ đỏ lại khi T60 thêm `ai_created_labels`; xem dòng `progress:` của T60.
