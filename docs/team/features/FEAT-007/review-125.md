Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 125 — FEAT-007 T125

- Diff: `git diff 566ff695fb7c937670c6637dbe26502e03f1d259..47cadf3` (nhánh `team/FEAT-007-task-125`; 2 commit `5e7b4b1` test, `47cadf3` mã; 4 file +18/−4, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `e8f0cbd` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED, một lần giữ khóa, `MIGRATE_EXIT=0`: `AssertionError: '2026-01-02T03:04:05' != '2026-01-02 03:04:05'`; `AssertionError: '2026-01-02T03:04:05.000123' != '2026-01-02 03:04:05.000123'`; test_install `Ran 56 tests FAILED (failures=2)`; `AssertionError: {'agent_enabled_at': ['thời điểm nâng cấp']} != {}`; test_doctype_descriptions `Ran 12 tests FAILED (failures=1)`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_install `Ran 56 tests OK`, test_doctype_descriptions `Ran 12 tests OK`, test_erp_ai_setting `Ran 103 tests OK`, test_architecture `Ran 181 tests OK`.
- Lớp 1: đáp ứng hết tiêu chí, không có gì thừa, giữ đúng touchpoint.

Theo từng mục checklist (10):

1. Spec/tiêu chí (STD-DESIGN-5, STD-TEST-2): đạt. `install.py:117` giờ ghi `str(frappe.utils.now_datetime())`, không dùng `now()`. Controller không đổi, không có patch, giá trị dạng `T` đã có không bị sửa. Mô tả mới khớp phán quyết 2b. Cụm bắt buộc mới là "thời điểm nâng cấp", vẫn giữ hai cụm cũ.
2. Touchpoint, cấu trúc (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Diff chỉ chạm 4 file khai báo, không thêm file mới, không đụng `protected_paths`.
3. Test đỏ trước, biên (STD-TEST-1/8/4): đạt. Commit test `5e7b4b1` tách riêng, dòng RED khớp mục Expect. Có hai biên: micro giây bằng 0 và micro giây khác 0. Không có skip/xfail. Kiểm đột biến bằng cách đọc mã: bỏ thay đổi (ghi đối tượng datetime) thì ra `T...` → đỏ; dùng `frappe.utils.now()` → đỏ, vì `now()` thêm `.000000` và gọi `now_datetime` của `frappe.utils.data`, hàm không bị patch; test đọc chuỗi thô trong `tabSingles` qua `_stored_settings`, không chuẩn hóa → không bị che.
4. Không sửa assertion cũ (STD-TEST-5/6): đạt. Ba test "xanh trước và sau" và helper `_enabled_at` giữ nguyên. Mỗi subTest xóa dòng mốc trước khi chạy. `setUp` rollback và gọi `keep_agent_settings`. Thời gian được patch, không phụ thuộc đồng hồ thật.
5. Lỗi, biên vào (STD-ERR-1/2/5): không áp dụng. Diff không thêm `except` hay lời gọi ngoài.
6. Bảo mật (STD-SEC-1/3/4/6): đạt. Không có secret. Các câu SQL trong test đều có tham số.
7. Hợp đồng dữ liệu (STD-DESIGN-3, STD-OPS-2): đạt. Một trường giờ chỉ còn một dạng lưu, đúng 2a. Diff `.json` chỉ có hai dòng: `description` (hunk ở dòng 125) và `modified` (15:00 → 16:00). Không đổi `field_count`, mặc định, kiểu hay vị trí khóa. So mô tả từng byte: chữ lấy bằng `git show 47cadf3:...json` và chữ ở `design-w0-fixes-7.md:109` (đã bỏ "> ") → `IDENTICAL`. Cả hai 270 ký tự (`wc -m`), md5 trùng nhau `7fb9f651b2bc14397a1e02e75884728d`. Chuỗi này xuất hiện đúng 1 lần trong file.
8. Tên, phong cách, không có mã chết (STD-NAME-1/2, STD-STYLE-4/5): đạt. Hằng mới `ENABLED_AT_MICROSECONDS` theo đúng kiểu `ENABLED_AT`. Hai dòng chú thích thêm vào đều đúng với hành vi.
9. Phụ thuộc mới (STD-DEP-1/3/5): không có.
10. Commit, nhánh, tài liệu (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2): đạt. Nhánh là `team/FEAT-007-task-125`. Hai commit đúng dạng `type(scope): mô tả (FEAT-007)`, không có trailer AI. Mô tả trường (chữ người dùng thấy) được sửa ngay trong task này.

### Findings

- Không có blocker hay major.
- minor | — | — | 1 điểm nhỏ: `test_doctype_descriptions.py:50` chỉ ghim 3 cụm chứ không ghim nguyên văn 270 ký tự (thiết kế chọn vậy; reviewer đã so tay, khớp) | tùy dev

### Không kiểm được từ diff

- `cmd.migrate` có nạp mô tả mới vào DocField của site `miyano` không.
- Kết quả chạy thật của test_install (56), test_doctype_descriptions (12), test_erp_ai_setting (103), test_architecture (181). Reviewer không chạy test.
- `pre-commit run --all-files` (lint/format).

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline 566ff69..47cadf3`; `git diff --stat 566ff69..47cadf3`; `git diff 566ff69..47cadf3`; `git show 47cadf3:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` so với dòng 109 của `design-w0-fixes-7.md` (`wc -m`, `md5sum`); `git show 47cadf3:erp_ai/tests/test_install.py`; `git show 47cadf3:erp_ai/install.py`; `git show --stat --format='%an %s%n%b' 5e7b4b1 47cadf3`; `git log --format=%D -1 47cadf3`.

## Kết luận của tech-lead

- Test sau merge (tech-lead, worktree `feat-007` @ `e8f0cbd`, một lần giữ khóa site, `migrate` chạy trước và `MIGRATE_EXIT=0`): `erp_ai.tests.test_install` `Ran 56 tests in 21.276s` / `OK`; `erp_ai.tests.test_doctype_descriptions` `Ran 12 tests in 0.343s` / `OK`; `erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting` `Ran 103 tests in 8.200s` / `OK`; `erp_ai.tests.test_architecture` `Ran 181 tests in 15.832s` / `OK`.
- "migrate có nạp mô tả mới vào site không": đo gián tiếp, chưa đo thẳng. `MIGRATE_EXIT=0` và test_doctype_descriptions xanh sau migrate; tech-lead không truy vấn `tabDocField` (không có ô lệnh nào của profile cho việc đó). Site dùng chung: lần `migrate` kế của phiên CHG-002 (JSON của họ còn chữ cũ) sẽ ghi lại chữ cũ cho tới khi hai nhánh gộp; ghi cho `/team:verify`.
- Lint: dev chạy `pre-commit run --files` trên bốn file, exit 0; `cmd.lint` cả cây chưa chạy ở lượt này (xem dòng DỪNG lượt 14 của `tasks.md`).
- Tick T125: 64/174.

## deferred

- minor: ghim nguyên văn 270 ký tự (thiết kế chọn ghim cụm).
- `/team:verify`: kiểm chữ mô tả `agent_enabled_at` trên site sau khi gộp với CHG-002.
