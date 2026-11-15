Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 56 — FEAT-007 T56

- Diff: `git diff 8d694c7..7347604` và `git show --remerge-diff 7347604` (nhánh `team/FEAT-007-task-56`; commit gộp `develop` @ `a689b8d`, cha `8d694c7` và `a689b8d`; 4 file xung đột giải tay, đều trong `files:`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `7821d40` trên `team/FEAT-007` (cùng một lần merge với T57, quyết định 03:36 (a) của team-leader; review của T57: `review-57.md`)
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.
- Ghi chú về lượt gọi: round 70 gọi MỘT reviewer cho cả dải `8d694c7..8323fda` (T56 + T57); reviewer đó chạm trần 25 lượt khi chưa viết báo cáo nào (không tính là một vòng review). Round 71 tech-lead đổi một thứ: tách thành hai reviewer chạy cùng lúc, mỗi người một commit, kèm trần số lệnh; cả hai trả `approve`.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): ở đầu nhánh `8323fda`, một lần giữ khóa site, `MIGRATE_EXIT=0`, đều `OK`: `test_tasks` `Ran 66 tests`, `test_agent_runner` 110, `test_architecture` 181, `test_erp_ai_setting` 102, `test_site_api` 74, `test_source` 125, `test_doctype_descriptions` 12, `test_change_guard` 36, `test_hard_bans` 8. `pre-commit run --all-files` exit 0. Số của dev: `field_count` `develop` 28, nhánh trước gộp 76, sau gộp 77; `section_count` 14.
- Quyết định 03:36 áp cho vòng này: (a) Expect (4) chạy ở đầu nhánh sau commit INT-1, nên `test_erp_ai_setting` đỏ ngay tại `7347604` với `AttributeError … 'DENIED_DOCTYPES'` được nhận; (b) `comm -23` của Expect (1) được in đúng một dòng `test_enqueue_call_shape_requires_exactly_two_calls`.

### Báo cáo của reviewer (nguyên văn)

reviewer -> tech-lead | FEAT-007 T56 (merge commit 7347604, review round 1) | approve

**Diff read with:** `git show --remerge-diff [--stat] 7347604`, `git diff a689b8d 7347604 -- <files>`, `git diff 8d694c7 7347604 -- <files>`, `git show <sha>:<file> | grep/jq`, `git grep … 7347604`. I read STD-short ("STD-TEST-4 (3) Do not use skip, xfail or only to get green — a violation is a blocker.").

**Layer 1 (does it match the spec): met.** The hand edits from the remerge-diff are only in the 4 conflicted files, and all 4 are touchpoints. The other touchpoints (test_architecture.py, test_agent_runner.py, test_erp_ai_setting.py, source.py) match git's automatic merge exactly. Nothing is out of scope.

**Returns clauses, checked in the merged tree:**
- **`validate` order:** `refuse_agent_write(self)` is the first line of `validate` (erp_ai_setting.py:177), followed by `restore_self_managed_fields()`. This matches design.md:289-290.
- **R5-10, the watermark:**
  - `self.privilege_alert_checked_until = read_privilege_watermark()` sits right after the `spent_this_month_usd` restore (erp_ai_setting.py:228-232).
  - `read_privilege_watermark` (:161), `EMPTY_DATETIME` and `restore_self_managed_fields` (:226) are all kept.
  - The field is not also in `SELF_MANAGED_WATERMARKS`, so it is never written twice.
- **The field in the JSON:** `privilege_alert_checked_until` is in the JSON, is Datetime with `read_only: 1`, and sits in `section_alerts` after `alert_recipients`, the same place as on develop. Its definition is identical to develop's.
- **JSON shape:**
  - The merged JSON parses with jq: 91 fields, field_order also 91 and exactly equal to the fieldnames in `fields`.
  - No fieldname appears twice (91 unique).
  - Every develop field and every branch field is present.
  - Top-level keys other than fields, field_order and modified equal the branch's.
  - `modified` is set to 2026-11-15 15:00, later than both sides.
- **`field_count`:** I counted fields with the test's own rule (no break types, no hidden fields): develop 28, branch before the merge 76, merged 77. 77 = 28 + 49, and the test says 77. There are 14 section breaks and `section_count` is 14.
- **test_doctype_descriptions:** `read_only_fields` has the branch's tuple plus `privilege_alert_checked_until`. Develop's phrase entry for the field (line 113) and its section rows are kept. Compared with the branch, the file differs only in the conflict lines (3+/1-).
- **erp_ai_accuracy report:** `git diff 8d694c7 7347604 -- erp_ai/erp_ai_agent/report/erp_ai_accuracy/` prints 0 lines.
- **T121:** `resolve_safe_path` (source.py:149-160) still returns `None` for any non-directory path strictly inside the manuals directory, so a path not on disk yet is still refused. The only change from the branch is develop's `_logger()` rewrite (+21/-9).
- **T122:** `check_tools_never_bypass_permissions` still catches `frappe.qb` (test_architecture.py:669-673).
- **T59:** `auto_assign_enabled=0` is still in `RunnerTestBase.setUp` (test_agent_runner.py:107), and the assertion at :152 is kept.
- **T42:** the renamed test `test_enqueue_call_shape_requires_one_call_per_target` is present (count 1).

**Expect checks I re-ran (git only):**
- **(1)** `git diff a689b8d 7347604 --` on runner.py, tasks.py, site_api.py, test_tasks.py, test_runner_routing.py and test_site_api.py prints 0 lines. `comm -23` (develop minus merged) prints exactly one line, `test_enqueue_call_shape_requires_exactly_two_calls`, which ruling (b) accepts. Branch minus merged prints nothing.
- **(2)** prints only erp_ai_setting.py and tasks.py.
- **(3)** prints 0 lines (base `8d694c7`).
- **(5)** both counts are 1.

**Nothing lost from either side.** Counts of `def test_` (branch / develop / merged) and names dropped:

| File | Branch | Develop | Merged | Names missing from merged |
|---|---|---|---|---|
| test_source.py | 122 | 113 | 125 | none |
| test_doctype_descriptions.py | 12 | 11 | 12 | none |
| test_erp_ai_setting.py | 101 | 28 | 102 | none |
| test_agent_runner.py | 67 | 109 | 110 | none |
| test_architecture.py | 114 | 179 | 181 | only the accepted T42 rename |

- In test_source.py, `class` count goes 10 / 10 → 11: develop's `TestSourceLogger` and its constants come after the branch's `TestManualsExcluded`. Develop's added imports (`TempAppsRoot`, `keep_agent_settings`, `set_agent_settings`) are in the merged file.
- No conflict markers are left in any .py or .json under erp_ai/.

**Checklist (10/10 covered):**
- Tests: no skip or xfail added, and no assertion was weakened. The only change to a test value is `field_count` 77, and I recomputed it from the JSON.
- Spec: met.
- Naming: no new names.
- Structure: no new files.
- Style: the import order `from datetime import datetime` after `import re` follows ruff's default order. I did not run lint.
- Error handling: the code that catches errors came unchanged from develop's side.
- Security: no secrets and no protected paths.
- Design and touchpoints: respected.
- Git: a single merge commit with message `merge(setting): T56 … (FEAT-007)`.
- Docs: none required.

**Findings:** none at blocker or major level.

**Minors:** none with an STD code.

**Not verifiable from the diff:**
- At 7347604, `erp_ai/agent/hard_bans.py:22` and `test_hard_bans.py:41,55,65` still use `site_api.DENIED_DOCTYPES`, which develop no longer has (0 matches in hard_bans.py or site_api.py at a689b8d). So `hard_ban_reason`, called from `check_catalog_rules`, fails with AttributeError at this commit. This is the red that ruling (a) accepts. Whether T57 (8323fda) removes it belongs to that review: tech-lead to confirm T57's Expect "`DENIED_DOCTYPES` count in hard_bans.py = 0", and also clean up the test_hard_bans.py references.
- Expect (4), the test runs and migrate, and `pre-commit` exit 0: I only have dev's pasted lines at 8323fda. I ran no tests or lint (no bench on the shared site). Suggest checking at milestone M7 with the full `cmd.test`.
- Whether the migrated site's ERP AI Setting really holds the 77 fields depends on migrate syncing the new `modified` timestamp. Not visible from git.

## Kết luận của tech-lead về mục "không kiểm được"

- `DENIED_DOCTYPES` ở `hard_bans.py`, `test_hard_bans.py` tại `7347604`: T57 (`8323fda`) đã đổi; tech-lead kiểm `git grep -c DENIED_DOCTYPES team/FEAT-007-task-56 -- erp_ai/agent/hard_bans.py erp_ai/agent/test_hard_bans.py`: không in dòng nào (0 ở cả hai file). `review-57.md` xác nhận cùng điều đó. Không thiếu gì.
- Expect (4), migrate, lint: tech-lead chạy lại sau merge `7821d40` từ worktree `feat-007`, một lần giữ khóa site (M7): `MIGRATE_EXIT=0`; `cmd.test` cả bộ `Ran 1843 tests in 516.529s` / `OK`, 0 dòng `ERROR:`/`FAIL:`, 0 `QueryDeadlockError` (tám module của Expect (4) nằm trong bộ này; dev đã chạy riêng từng module ở `8323fda`, đều `OK`). `cmd.lint` (`pre-commit run --all-files`) trên `7821d40`: exit 0, mọi hook `Passed`. Không thiếu gì.
- Site có đủ 77 trường sau migrate: `test_doctype_descriptions` (đếm `field_count` 77 trên meta của site) và `TestFeat007Defaults` xanh trong lần chạy M7 ngay sau `migrate` exit 0 trong cùng lần giữ khóa. Không thiếu gì.

## deferred

- Không có finding nào hoãn. Ghi chú của dev, ngoài phạm vi task: `RUN_PATH` được định nghĩa hai lần trong `erp_ai/agent/tools/test_source.py` (dòng 212 và 1039), giống nhau ở cả hai phía của lần gộp; để `/team:clean`.
- Hook commit in cảnh báo STD-NAME-5 cho kiểu `merge` của commit `7347604` (chữ commit do tech-lead đưa); commit merge trên `team/FEAT-007` (`7821d40`) dùng kiểu `feat`.
