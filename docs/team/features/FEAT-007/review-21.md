Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 21 — FEAT-007 T21

- Diff: `git diff 7b0aec1..team/FEAT-007-task-21` (đầu `7120fd5`, 1 commit, 2 file +60/−0)
- Vòng: 1 (trần `max_rework` = 3). Reviewer được gọi hai lần cho vòng này: lần 1 hết trần 25 lượt, không trả báo cáo; lần 2 (lời giao có giới hạn số lệnh) trả báo cáo dưới đây.
- Verdict: approve; merge `2ac3a4e` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — approve

- Bằng chứng của dev: RED (`test_install`, trước khi sửa mã): `AssertionError: '<missing>' != '2026-01-02 03:04:05'`; `(stored=None) AssertionError: None != '2026-01-02 03:04:05'`; `(stored='') AssertionError: '' != '2026-01-02 03:04:05'`; `FAILED (failures=3)`. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_install` `Ran 41 tests in 24.445s OK`; `test_erp_ai_setting` `Ran 82 tests in 7.970s OK`; `test_architecture` `Ran 112 tests in 3.878s OK`.

### Báo cáo của reviewer (nguyên văn)

**Tier 1 (spec and design):** The diff matches. `design.md:329` asks for one added line in `_ensure_default_settings`: `enabled` = 1 and `agent_enabled_at` missing → `now_datetime()`. That is `erp_ai/install.py:105-112`. "Missing" covers an absent row, NULL and `""`, so it only fills a missing field (ADR-006), and a stored value is never moved (AC-16). Nothing is missing, nothing extra, nothing misunderstood. Edits stay in the two touchpoints.

The `Expect` line names one test with three clauses. Dev put the first two in `test_agent_enabled_at_filled_once_when_enabled`: enabled + missing gets a value, and a second `ensure_setup` changes nothing. The third clause, "disabled → stays empty", is in a separate test, `test_agent_enabled_at_left_unset_when_disabled` (`test_install.py:727`). Same coverage, different test name.

**Findings (blocker/major):** none.

**Answer to "what ends up in `tabSingles`" (confirmed from source):**
- **What the install line writes:** `frappe.db.set_single_value` writes through `frappe.qb.into("Singles")...insert()` (`frappe/database/database.py:827-828`). The `ParameterizedValueWrapper` patch fixes only `timedelta` and `time` (`frappe/query_builder/terms.py:53-65`). A `datetime` therefore goes to pypika `get_value_sql`, which calls `value.isoformat()` (`pypika/terms.py:439-440`). The stored text is `2026-11-15T01:28:25.844279`, with a `T`.
- **What a form save writes:** `stamp_agent_enabled_at` (`erp_ai_setting.py:182`) puts a `datetime` on the doc. `Document.update_single` (`frappe/model/document.py:707-711`) inserts it with raw `%s`, and pymysql `escape_datetime` writes `2026-11-15 01:28:25.844279`, with a space. So one field gets two text shapes.
- **Readers on the branch cope:** `get_single_value(..., cache=False)` casts with `get_datetime`, which parses both shapes. `restore_self_managed_fields` (`erp_ai_setting.py:157-159`) and `Document.load_from_db` (`document.py:281`) read the raw text through `get_singles_dict` and pass it back unchanged. A later human save keeps the `T` text; nothing breaks. No other reader of `agent_enabled_at` exists on the branch (`git grep`). The new tests normalize with `get_datetime` (`test_install.py:697`), so they do not pin the shape.
- Rated minor, because no reader on the branch breaks. See "not verifiable" below for later readers.

**Do the tests fail when the behavior is removed? (traced by hand, not run)**
- Removing the line turns `filled_once` and both `null_or_empty` subtests red. Dev's RED output shows these 3.
- Dropping the `enabled` condition turns `left_unset_when_disabled` red.
- Always overwriting turns `already_set_is_kept` and the second-run assertion red.
- Treating only an absent row as missing turns the NULL and `""` subtests red.
- Expected values are hard-coded constants (`test_install.py:50-52`). The clock is patched, and `frappe.utils.now_datetime` is looked up at call time, so the patch takes effect. `setUp` rolls back and calls `keep_agent_settings`, and `updatedb` is patched.

**Checklist**
1. pass. Spec and design done fully, nothing extra (STD-DESIGN-5, STD-TEST-2).
2. pass. Only `erp_ai/install.py` and `erp_ai/tests/test_install.py`; no new files (STD-DESIGN-1, STD-STRUCT-1/2).
3. pass. RED was pasted (`FAILED (failures=3)`). Edge cases covered: absent, NULL, `""`, already set, disabled with no row, disabled with a NULL row. No skip/xfail (STD-TEST-1/8/4).
4. pass. No existing assertion changed (+0/−0 in old tests). Clock patched, rollback isolation (STD-TEST-5/6).
5. pass. Nothing is caught or swallowed; no boundary input; no external call (STD-ERR-1/2/5).
6. pass. Raw SQL is parameterized (`%s` for the doctype; the field name is a literal). No secrets; no `protected_paths` touched (STD-SEC-1/3/4/6).
7. pass, with one minor point. No API change. The Datetime field gets two text shapes depending on the writer; readers on the branch cope (STD-DESIGN-3).
8. pass. Constants are UPPER_CASE, helpers are `_snake_case`, no dead code, style matches the file (STD-NAME-1/2, STD-STYLE-4/5).
9. pass. No new dependency (STD-DEP-1/3/5).
10. pass. Branch `team/FEAT-007-task-21`. Commit `feat(install): … (FEAT-007)` has no AI trailer. No user documentation needed for an internal fill (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2).

minor | — | — | 3 small points: (a) STD-DESIGN-3, install.py:112: the install path stores ISO text with a T while a form save stores text with a space for the same Datetime field; passing str(frappe.utils.now_datetime()) to set_single_value would give one shape, and the tests could then pin the raw text instead of normalizing it in _enabled_at (test_install.py:697); (b) STD-DESIGN-4, install.py:106-111: the "missing" check repeats the raw tabSingles select from the default-filling loop just above instead of sharing one helper; (c) the Expect clause "disabled → stays empty" lives in test_agent_enabled_at_left_unset_when_disabled, not in the test named in Expect | dev's call

**Not verifiable from the diff (for tech-lead):**
- **Desk display of the `T` text:** the form loads the raw `T` text through `get_singles_dict` without a cast. Whether the Datetime control shows `2026-11-15T01:28:25.844279` correctly needs a UI check.
- **Later readers of `agent_enabled_at`** (e.g. KPI windows in later tasks) are not on this branch. SQL comparisons accept `T`. A Python string comparison of raw stored values across the two shapes would order wrongly (`'T'` > `' '`). The task that adds such a reader should cast with `get_datetime`, or this task should normalize the shape (minor (a)).
- **Lint:** no `cmd.lint` output is in dev's evidence. Line length of the comment at `install.py:105` is unchecked.
- **Tests not run** by me, per the instruction. GREEN comes from dev's evidence only.
- **`test_second_migrate_changes_nothing`** does not pin `enabled`. Its coverage of the new line depends on the site's stored `enabled`; the explicit second-run assertion in `filled_once` covers idempotence regardless.

**Read-only commands used:** `git log --format='%h %an%n%B' 7b0aec1..team/FEAT-007-task-21`, `git diff --stat …`, `git diff …`; `git show team/FEAT-007-task-21:` cho `erp_ai/install.py`, `erp_ai/tests/test_install.py`, `erp_ai_setting.py`; `git grep -n agent_enabled_at team/FEAT-007-task-21 -- '*.py' '*.js'`; đọc mã Frappe và thư viện: `frappe/database/database.py` (735, 796-829), `frappe/query_builder/terms.py` (39-70), `frappe/model/document.py` (278-290, 699-711), `pymysql/converters.py` `escape_datetime`, `pypika/terms.py` (439-440); grep/sed trên `tasks.md`, `design.md`, `design-w0-fixes*.md`, `spec.md`.

## Kết luận của tech-lead (trước khi tick)

- Chạy lại sau merge `2ac3a4e`, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_install` `Ran 41 tests in 16.676s OK`; `test_erp_ai_setting` `Ran 82 tests in 5.258s OK`; `test_architecture` `Ran 112 tests in 3.459s OK`. Khớp số của dev.
- `cmd.lint` trên `2ac3a4e`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền); `install.py`, `test_install.py` sạch (E501 không bật trong `pyproject.toml`).
- Hai dạng chữ của cùng một trường Datetime (`T` so với dấu cách): không phải thiếu sót so với tiêu chí của task (AC-16, `design.md:329` đạt; mọi nơi đọc trên nhánh chịu được). CHƯA kiểm: màn hình Desk hiện chữ có `T` ra sao (profile `ui: false`, tech-lead không có công cụ xem UI) → ghi cho `/team:verify` và luồng tay của mốc M. Lần `migrate` sau merge này đã chạy dòng mới trên site `miyano` thật, nên nếu site đang bật thì trường đang giữ chữ dạng `T`; người mở form ERP AI Setting là thấy ngay.
- Nơi đọc về sau (T33/T34 việc quét, cửa sổ KPI): phải đọc qua `get_single_value`/`get_datetime`, không so chuỗi thô. Ghi để lời bàn giao T33 nhắc.
- `test_second_migrate_changes_nothing` không ghim `enabled`: phép khẳng định lần chạy thứ hai trong `filled_once` đã phủ; không chặn.

## deferred

- minor (a): chuẩn hóa một dạng chữ (`str(now_datetime())`) và ghim chuỗi thô trong test (STD-DESIGN-3).
- minor (b): phép kiểm "thiếu" lặp lại câu select `tabSingles` (STD-DESIGN-4).
- minor (c): vế "tắt → vẫn rỗng" nằm ở test riêng, khác tên trong dòng Expect.
- Cho `/team:verify`: xem form ERP AI Setting hiện `agent_enabled_at` dạng `T`.
