Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 18 — FEAT-007 T18

- Diff: `git diff fd670a1..team/FEAT-007-task-18` (đầu `cfd4886`, 2 commit `40eb1bb`, `cfd4886`, 4 file +134/−3)
- Vòng: 1 (trần `max_rework` = 3). Dev được gọi hai lần trước review: lần 2 (`cfd4886`, chỉ test) do tech-lead yêu cầu để dòng `agent_enabled_at` của `test_every_new_field_default` không phụ thuộc giá trị `enabled` đang lưu của site sau T21.
- Verdict: approve; merge `7b0aec1` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — approve

- Bằng chứng của dev. Commit `40eb1bb`: RED `Ran 81 tests`, `FAILED (failures=12)`: `AssertionError: unexpectedly None : ERP AI Setting has no agent_enabled_at field`, `AssertionError: '2031-01-01' != '2030-03-04'`, `AssertionError: '2031-01' != '2030-02'`, `AssertionError: None != '2030-05-06 07:08:09'`. Commit `cfd4886` (chỉ test): RED với sửa tạm không commit (dòng của T21 trong `install.py` và `enabled` = 1): `FAIL: ... test_every_new_field_default (fieldname='agent_enabled_at')`, `AssertionError: datetime.datetime(2026, 11, 15, 1, 28, 25, 844279) != datetime.datetime(1, 1, 1, 0, 0)`. GREEN trên `cfd4886`, một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 82 tests in 7.871s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.392s OK`; `test_architecture` `Ran 112 tests in 3.828s OK`; `test_install` `Ran 37 tests in 26.321s OK`.

### Báo cáo của reviewer (nguyên văn)

**Tier 1 (matches spec and design): yes.**
- **New field.** `agent_enabled_at` is a read-only Datetime with no default. It sits in `section_activation` right after `permission_level`, as `design.md:97, 114` requires. Its description has both required phrases ("Hệ thống tự ghi", "không sửa được") and is about 190 characters, under the 400 limit.
- **Restore on save.** `restore_self_managed_fields()` reloads all 3 watermarks from the database, uncached, as the first step of `validate`.
- **Stamp on enable.** `stamp_agent_enabled_at()` is the last step of `validate` (design §3.1 step 13). It sets `now_datetime()` only when `enabled` goes 0 → 1 compared with the database.
- **Task conventions met.** `field_count` goes from 71 to 72; `section_count` is unchanged. `phrases` and `read_only_fields` are updated. The new row in `FEAT007_NEW_FIELD_DEFAULTS` follows the defaults table. The JSON `modified` date is bumped, which the migrate needs.
- **Scope.** No extra scope; `prompt_revisions` restore belongs to the later task (tasks.md:246-247), not this one.
- **One justified deviation.** The design (§3.1 step 1) names `frappe.db.get_single_value(..., cache=False)`. The code uses `frappe.db.get_singles_dict` instead. I checked that this is an uncached database query (frappe/database/database.py:735-756). The design's literal call would turn an unset Date/Datetime into a year-1 placeholder, and the save would store it. `test_unset_watermarks_stay_unset_on_human_save` pins this case. The design's intent is met, so this is not a finding, but the design text should be brought in line (see below).

**Tests checked first:** each test would fail if the behavior it covers were removed.
- `test_watermarks_restored_on_human_save` fails with no restore (dev's RED: `'2031-01-01' != '2030-03-04'`, `'2031-01' != '2030-02'`).
- `test_unset_watermarks_stay_unset_on_human_save` fails with no restore (the typed value is stored). It also fails if the restore uses `get_single_value`: the year-1 placeholders get stored for the date fields, and `""` for the Data field.
- `test_watermarks_restored_from_db_not_stale_cache` and `test_enable_compared_with_db_not_stale_cache` fail if the database read uses the cache. Frappe clears `value_cache` only in `update_single`, which runs after `validate` (frappe/model/document.py:536-548, 713). So the stale cache entry is still live when the restore and the stamp run.
- `test_agent_enabled_at_stamped_on_enable_only` covers the steps 0→0, 0→1, 1→1, 1→0 and 0→1 again. It fails if: the stamp is dropped (dev's RED: `None != '2030-05-06 07:08:09'`); the code stamps whenever `enabled` is on (step 1→1 breaks); the code stamps on any change of `enabled` (step 1→0 breaks); the stamp runs before the restore (the restore would overwrite it).
- Expected values are hard-coded, the clock is patched, `setUp` calls `keep_agent_settings` and a rollback, and the class creates its own data.
- cfd4886 only adds a precondition (`enabled=0`) to `test_every_new_field_default`. That keeps the `agent_enabled_at` row independent of the site's live `enabled` value once T21 lands, and the other rows don't read `enabled`. Dev showed RED for it using T21's install line as a temporary edit.

**Findings (blocker/major):** none.

minor | — | — | 3 small points: (1) erp_ai_setting.py:38 comment says each watermark is "written only by its job (frappe.db.set_single_value)", but `agent_enabled_at` is written by `stamp_agent_enabled_at` through `doc.save` (and by install after T21); (2) the description says "thời điểm gần nhất ô Bật agent đổi từ tắt sang bật", but after T21 a site that was already enabled will hold the upgrade time, and T21 cannot edit the JSON; (3) the test_erp_ai_setting.py:722-723 comment "holds whatever the site stores" is unclear (the point is that the row does not depend on the site's stored `enabled`) | dev's call

**Checklist**
1. Does exactly what the spec asks, nothing extra (STD-DESIGN-5, STD-TEST-2): **pass.** All 3 "Returns" items are present, and both named Expect tests exist.
2. Touchpoints and file placement (STD-DESIGN-1, STD-STRUCT-1/2): **pass.** Only the 4 listed files changed, and there are no new files.
3. Failing test first, edge cases, no skip (STD-TEST-1/8/4): **pass.** RED output was pasted for both commits. The diff has none of the profile's `skip_markers`. Edge cases covered: unset watermark, stale cache, 1→0, re-enable.
4. No test changed to fit wrong behavior; tests independent (STD-TEST-5/6): **pass.** cfd4886 only adds a precondition. Clock patched, rollback plus `keep_agent_settings`. Frappe clears `value_cache` on save and on rollback, so the cache tweaks don't leak to other tests.
5. Errors and input validation (STD-ERR-1/2/5): **pass.** No catch blocks and no external calls. A human-typed value never reaches storage.
6. Security (STD-SEC-1/3/4/6): **pass.** No secrets, no raw SQL in production code, no `protected_paths` touched.
7. Contracts and migration (STD-DESIGN-3, STD-OPS-2): **pass.** The new nullable field is added by Frappe's schema sync, and nothing existing changes.
8. Names, structure, style, dead code (STD-NAME-1/2, STD-STYLE-4/5): **pass.** Names follow the file's existing `SELF_MANAGED_*` / `check_*` patterns, and there is no dead code. The comment wording issues are in the minor line.
9. Dependencies (STD-DEP-1/3/5): **pass.** None added.
10. Commits, branch, docs (STD-NAME-4/5, STD-GIT-1, STD-DOC-2): **pass.** Both commit messages are `type(setting): … (FEAT-007)`, with no AI-attribution trailer (STD-GIT-8). The task branch `team/FEAT-007-task-18` follows the team's existing task-branch practice. The field description travels with the change.

**Not verifiable from the diff (for tech-lead)**
- **Tests not re-run.** I did not run the tests or the migrate (shared site). GREEN rests on dev's pasted output: test_erp_ai_setting 82 OK, test_doctype_descriptions 12 OK, test_architecture 112 OK, test_install 37 OK, MIGRATE_EXIT=0.
- **Design wording.** `design.md:291` should say "uncached DB read (`get_singles_dict`)" instead of `get_single_value(cache=False)` for the watermarks. Otherwise a later task that "aligns with the design" would bring back the year-1 placeholder. Worth recording in the design or As-Built.
- **Other ways to switch the agent on.** In production code, no path writes `enabled` other than the form save (checked with `git grep` at the task head). Any future `set_single_value(..., "enabled", 1)` path, a fixture, or a manual DB edit would skip the stamp. T21 covers only the install case.
- **Description after T21.** The field description (point 2 of the minor line) should get a tech-lead decision: either a follow-up task that may touch the JSON, or accept the wording as it is.
- **Other ADR-033 decision 6 writers.** The scan (U4a) that reads `agent_enabled_at` and the jobs that write `daily_report_sent_on` / `budget_alert_sent_month` with `set_single_value` are not built yet. That half of decision 6 can't be checked here.

**Read-only commands used:** `git log --oneline fd670a1..team/FEAT-007-task-18`, `git diff --stat …`, `git diff …`, `git log --format='%H%n%B----' …`; `git show team/FEAT-007-task-18:` cho `erp_ai_setting.py`, `erp_ai/test_utils.py`, `test_erp_ai_setting.py` (655-730); `git grep -n …` (nơi ghi `enabled` và các mốc; đường lưu `ignore_validate` / `get_single`); `git show fd670a1 --stat`; grep/sed trên `tasks.md`, `design.md`, các file fixes, `plan.md`, ADR-033, `spec.md` (AC-16), `.team/profile.json`, mã nguồn Frappe (`database.py`, `document.py`).

## Kết luận của tech-lead (trước khi tick)

- Chạy lại sau merge `7b0aec1`, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 82 tests in 7.436s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.380s OK`; `test_architecture` `Ran 112 tests in 3.850s OK`; `test_install` `Ran 37 tests in 21.430s OK`. Khớp số của dev. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- Chữ `design.md:291` (`get_single_value(cache=False)` so với `get_singles_dict`): không phải thiếu sót của task (ý "đọc DB không qua cache" đạt và có test ghim); chuyển team-leader xin một dòng sửa chữ của designer, để T20 (khôi phục `prompt_revisions`) và task sau không "sửa cho khớp thiết kế".
- Đường khác bật agent mà không qua form: hiện không có trong mã sản phẩm (reviewer đã `git grep`); T21 phủ trường hợp cài đặt. Không chặn.
- Mô tả trường sau T21 ("thời điểm gần nhất ô Bật agent đổi từ tắt sang bật" trong khi site bật sẵn sẽ giữ giờ nâng cấp): tech-lead không thêm task (lời giao lượt 8 cấm thêm dòng task); chuyển team-leader/designer quyết: sửa chữ mô tả ở một task đợt sau có `erp_ai_setting.json`, hoặc nhận chữ hiện tại.
- Nửa còn lại của ADR-033 QĐ 6 (job ghi mốc, việc quét đọc mốc): thuộc T33, T34, T53, T54; kiểm ở review của các task đó.

## deferred

- minor (1): chú thích `erp_ai_setting.py:38` nói mọi mốc do job ghi bằng `set_single_value`, trong khi `agent_enabled_at` ghi qua `doc.save`.
- minor (2): chữ mô tả trường sau T21 (xem trên).
- minor (3): chú thích `test_erp_ai_setting.py:722-723` khó hiểu.
- Cho designer: sửa chữ `design.md:291`.
