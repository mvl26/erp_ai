Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 09 — FEAT-005 T9

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 035689b..a743e35` (nhánh `team/FEAT-005-task-9`, 2 commit; vòng 1 `035689b..5e0f804` 2 file +136/−2, vòng 2 `5e0f804..a743e35` 2 file +11/−5); merge `4cdb4f5`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 request-changes

## Vòng 2 — approve (`5e0f804..a743e35`, chấm lại có phạm vi)

- major STD-DESIGN-2: ADDRESSED. `erp_ai/tests/test_tasks.py:656-657`: dict `after` có `"api_delete_record#2": None`, đúng dạng runner ghi cho lệnh xóa (design §3.2); mục `gỡ role C của gone@…` đúng với dạng đó, T12 không phải đổi phép khẳng định này.
- minor (a): ADDRESSED (`erp_ai/tasks.py:122-127`, docstring nói User cho 0..n mục). minor (b): ADDRESSED (`test_tasks.py:647,654,664-671`: role A từ 3 xuống 1, role B từ 1 lên 3; so theo tập hoặc bỏ `.elements()` đều đỏ). minor (c): để T10 (thứ tự cuối).
- Phát hiện mới: không. Commit `a743e35` đúng dạng, không dòng ghi công AI, 0 dấu skip.
- Bằng chứng của dev vòng 2: cả module `Ran 46 tests in 5.138s` / `OK`; đột biến bỏ `.elements()`: `AssertionError: Lists differ … Second list contains 2 additional elements.`, `Ran 1 test` / `FAILED (failures=1)`.
- Không kiểm được từ diff (vòng 2): khi T12 thêm fail-closed phải tách khóa thiếu (ra "không có trước/sau") khỏi khóa có giá trị `None` (lệnh xóa thật, ra "gỡ role …") → tech-lead ghi vào chữ T12 và handoff T12.

## Vòng 1 — request-changes (`035689b..5e0f804`)

Lớp 1: AC-14 ca (1), (2), (5) và A-18 đạt; chữ mục so đúng từng ký tự; role so theo tên bằng `Counter`; role giữ nguyên không bị liệt kê (D-4); chỉ 2 file touchpoint; không lấn sang T10–T13.

- major | STD-DESIGN-2 | erp_ai/tests/test_tasks.py:651-656 | Ca xóa User bỏ khóa `after["api_delete_record#2"]`. Runner không bao giờ ghi dạng đó: `runner._record_snapshot` (runner.py:720-721) luôn ghi khóa, với `None` cho lệnh xóa (site_api.py:365). Design §4.2 bước 3 và ADR-024 QĐ 1 coi khóa thiếu là ảnh chụp không dùng được, phải ra "không có trước/sau". Test khẳng định điều ngược lại (`gỡ role C của gone@…`), nên T12 sẽ phải đổi một phép khẳng định của T9 (STD-TEST-5), và dạng xóa thật không được gieo. | Thêm `"api_delete_record#2": None` vào dict `after`. Mục kỳ vọng giữ nguyên.
- minor | — | — | 3 điểm nhỏ: (a) dòng đầu docstring `_privilege_changes_by_agent` (tasks.py:122) còn nói "One entry per successful generic write"; (b) ở ca Counter mọi hiệu đếm đều là 1 nên bỏ `.elements()` vẫn qua; (c) test ghim thứ tự "thêm trước gỡ" trong một hành động, T10 có thể phải đặt lại | tùy dev

- Bằng chứng của dev vòng 1: RED `AssertionError: 0 != 1 : []`, `Lists differ: [] != ['thêm role ERPAI-TEST vai thêm cho erpai-[231 chars]10)']`, `Ran 4 tests in 3.786s` / `FAILED (failures=3)`; GREEN cả module `Ran 46 tests in 14.358s` / `OK`; 3 đột biến đỏ. `test_bot_resave_user_without_role_change_no_line` xanh từ trước khi có mã (đột biến M2 "liệt kê mọi role của after" làm nó đỏ).

## Tech-lead đã kiểm

- Sau merge `4cdb4f5`, một lần giữ khóa `miyano-site.lock` (0 lệnh site ngoài khóa trước và sau, migrate exit 0): test_tasks `Ran 46 tests in 5.093s` / `OK`.
- `git diff --name-only 035689b..a743e35` = `erp_ai/tasks.py`, `erp_ai/tests/test_tasks.py` (đúng touchpoint).

## Không kiểm được từ diff

- Lưu `User` của Frappe có tự thêm role (theo `user_type`) làm ảnh chụp `after` có role lạ hay không: test dùng tool thật đã xanh trên site `miyano`; site/cài đặt khác chưa kiểm → qa (verify).

## deferred

- minor (c): thứ tự mục trong một hành động, T10 quyết.
