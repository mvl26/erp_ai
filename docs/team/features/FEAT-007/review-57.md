Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 57 — FEAT-007 T57

- Diff: `git diff 7347604..8323fda` (nhánh `team/FEAT-007-task-56`, chung nhánh với T56 theo quyết định 03:36 (a) của team-leader; 1 commit, 3 file +22/−4)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `7821d40` trên `team/FEAT-007` (cùng một lần merge với T56; review của T56: `review-56.md`)
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.
- Ghi chú về lượt gọi: xem `review-56.md` (round 70 một reviewer cho cả hai task chạm trần 25 lượt, không có báo cáo; round 71 tách hai reviewer).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau migrate, trước khi sửa): `test_hard_bans` `Ran 8 tests … FAILED (errors=8)`, cả 8 phát ra từ `hard_bans.py`, dòng 22, `if doctype in site_api.DENIED_DOCTYPES:` — `AttributeError: module 'erp_ai.agent.tools.site_api' has no attribute 'DENIED_DOCTYPES'`; có `test_permission_doctypes_banned (doctype='Role')`. `test_erp_ai_setting` `Ran 102 tests … FAILED (errors=17)`, có `test_hard_ban_follows_denied_doctypes_source`. GREEN: `erp_ai.agent.test_hard_bans`: `Ran 8 tests in 0.148s` / `OK`; `erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting`: `Ran 102 tests in 7.142s` / `OK`. `test_architecture` `Ran 181 tests … OK`; `pre-commit run --all-files` exit 0.
- Nhận xét của tech-lead về RED: đỏ vì tên `site_api.DENIED_DOCTYPES` không còn sau lần gộp (hành vi thiếu đúng là thứ T57 sửa: điều cấm cứng chưa đọc tập phân quyền của FEAT-004), không phải lỗi import hay cú pháp của test.

### Báo cáo của reviewer (nguyên văn)

reviewer -> tech-lead | FEAT-007 T57 | approve

I found no blockers or majors.

**Git commands used (all read-only):**
- `git log --oneline 7347604..8323fda`, then `git diff --stat` and `git diff` on the same range. The range is one commit, `8323fda`, touching 3 files with 22 insertions and 4 deletions.
- `git show 8323fda:` on `erp_ai/agent/hard_bans.py`, `erp_ai/agent/test_hard_bans.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (lines 1140–1180), `erp_ai/agent/tools/site_api.py` (lines 15–32), `erp_ai/agent/tools/read.py` (lines 8–30) and `erp_ai/test_utils.py` (`keep_agent_settings`).
- `git show 7347604:erp_ai/agent/test_hard_bans.py`, to count the tests at the base.
- `git grep -n "DENIED_DOCTYPES\|PERMISSION_DOCTYPES" 8323fda` and `git grep hard_ban_reason`.
- `git log -1 --format='%an%n%B' 8323fda`.

**Layer 1 (does it match the spec):** all criteria are met and every edit stays inside the 3 touchpoints.
- `hard_bans.py:22` now reads `site_api.PERMISSION_DOCTYPES`. The string `DENIED_DOCTYPES` appears 0 times in `hard_bans.py`, as INT-1 requires.
- `test_permission_doctypes_banned` exists at `test_hard_bans.py:60`.
- `test_hard_ban_follows_denied_doctypes_source` has a `Role` case at `test_erp_ai_setting.py:1173-1177`.
- Nothing extra was added. No code outside `test_*.py` still uses the removed `site_api.DENIED_DOCTYPES`. The remaining `DENIED_DOCTYPES` hits are `read.DENIED_DOCTYPES` and the scanner in `test_architecture`.

**Checking that the tests can fail:**
- If the fix is reverted, both new tests fail with an AttributeError.
- If the set is hard-coded without `Role`, both the `Role` assertion and the catalog `Role` case fail.
- If the set is copied instead of read live, the `patch.object(site_api, "PERMISSION_DOCTYPES", {"ToDo"})` block fails (`ToDo` would not get the permission reason and `Role` would not lose it).
- If the denied check and the permission check swap places, `test_first_matching_reason_wins` fails, because it expects "Custom Role" to get the denied reason under a patched `read.denied_doctypes`.
- If the permission check and the submittable check swap places, `test_first_matching_reason_wins` also fails.

**Checking dev's RED output:** "Ran 8 tests … errors=8" matches the head file. There are 8 tests (7 at the base plus the new one). `subTest` counts its errors separately: 3 sub-cases (Custom Role, DocType, Role) plus the `Role` line after the loop give 4 errors, and 4 other tests each give 1.

**Review checklist (10/10):**
1. Spec, nothing extra (STD-DESIGN-5, STD-TEST-2): pass.
2. Touchpoints, no new files (STD-DESIGN-1, STD-STRUCT-1): pass.
3. Failing test first, edge cases, no skip (STD-TEST-1, STD-TEST-8, STD-TEST-4): pass. The RED output is pasted and the live-set case is covered.
4. No test bent to wrong behavior, independent (STD-TEST-5, STD-TEST-6): pass. In the old tests only the attribute name changed and every assertion is the same. Dependence on site data ("ToDo", a submittable DocType outside the ban sets) existed before this task.
5. Error handling and input checks (STD-ERR-1, STD-ERR-2, STD-ERR-5): pass. Nothing changed here; an unknown DocType still raises `DoesNotExistError`, which a test covers.
6. Security (STD-SEC-1, STD-SEC-3, STD-SEC-4, STD-SEC-6): pass. The ban set gets wider (DocType and Role added), not narrower. No secrets and no protected paths.
7. Contracts (STD-DESIGN-3): pass. The signature and reason strings of `hard_ban_reason` are unchanged.
8. Names, style, dead code (STD-NAME-2, STD-STYLE-4, STD-STYLE-5): pass.
9. Dependencies (STD-DEP-1, STD-DEP-3, STD-DEP-5): none added.
10. Commit, branch, docs (STD-NAME-5, STD-GIT-1): pass. The message follows `fix(hard-bans): … (FEAT-007)`, it is one commit on its own, and it has no AI attribution trailer.

**Minor findings:**
`minor | — | — | 2 small points: (1) test_erp_ai_setting.py:1158 the test name test_hard_ban_follows_denied_doctypes_source no longer matches the source it tests (site_api.PERMISSION_DOCTYPES); Expect fixes this name, so it stays as is; (2) test_hard_bans.py:54-58 test_permission_set_gives_permission_reason now partly overlaps the new test_permission_doctypes_banned (both loop over the permission set) | dev's call`

**Cannot verify from the diff:**
- GREEN results: `test_hard_bans` 8 OK, `test_erp_ai_setting` 102 OK, `test_architecture` 181 OK, and pre-commit exit 0. I ran no tests (suggest: `cmd.test_one erp_ai/agent/test_hard_bans.py` and `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`).
- Whether `team/FEAT-007` is now clear to merge into `develop`. Design §4 needs INT-2 (U5a) as well as INT-1, plus a green `cmd.test` on the combined branch. T57 covers INT-1 only, so tech-lead should check INT-2 before the merge.
- The ADR-031 A1 context (line 74) says `hard_ban_reason` does not block the child tables `DocPerm` and `Has Role`. That gap is outside T57's criteria and this diff, so the ADR-031 A1 tasks own it.

## Kết luận của tech-lead về mục "không kiểm được"

- Kết quả GREEN và lint: tech-lead chạy lại sau merge `7821d40` từ worktree `feat-007`, một lần giữ khóa site (M7): `MIGRATE_EXIT=0`; `cmd.test` cả bộ `Ran 1843 tests in 516.529s` / `OK`, 0 dòng `ERROR:`/`FAIL:` (gồm `test_hard_bans`, `test_erp_ai_setting`, `test_architecture`). `cmd.lint` trên `7821d40`: exit 0. Không thiếu gì.
- `team/FEAT-007` đã được merge vào `develop` chưa: CHƯA và lượt này không làm việc đó. INT-2 là T58 (`depends: T56, T43, T49`), chưa build; ràng buộc đứng R5-5 của team-leader vẫn giữ. Không phải thiếu sót của T57; đã chuyển team-leader ở dòng DỪNG lượt 11 của `tasks.md`.
- `hard_ban_reason` chưa chặn bảng con `DocPerm`, `Has Role` (ADR-031 A1 dòng 74): ngoài tiêu chí của T57 (F-3, INT-1 chỉ đòi đọc `site_api.PERMISSION_DOCTYPES`); thuộc các task của ADR-031 Amendment 1. Đã chuyển team-leader, không chặn.

## deferred

- minor (không hoãn việc gì bắt buộc): tên test `test_hard_ban_follows_denied_doctypes_source` không còn khớp nguồn nó kiểm (Expect của T57 ghim tên này); `test_permission_set_gives_permission_reason` trùng một phần với `test_permission_doctypes_banned`. Để `/team:clean`.
