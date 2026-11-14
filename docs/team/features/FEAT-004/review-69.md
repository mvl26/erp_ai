Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 69 — FEAT-004 T69

- Diff: `git diff 5e5e403..team/FEAT-004-task-69` (1 commit, `cef90a3`; `source.py` +20/−10, `test_source.py` +55/−3)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có blocker hay major | — |

minor | — | — | 2 điểm nhỏ: (1) STD-DESIGN-5: nhánh lùi về logger chuẩn của Python trong `_logger()` (`source.py:19-24`) vượt điều tiêu chí yêu cầu; nó giữ đường từ chối chạy được khi không mở được file log, có test và có lý do ghi cạnh. (2) STD-TEST-2: chỉ chỗ ghi log của `read_source` được so với tên `"erp_ai.source"`; các chỗ còn lại được phủ vì cùng gọi `_logger()` | tùy dev

## Review checklist (10)
1. Đúng và đủ tiêu chí: đạt. `source.py:14` chỉ còn hằng `LOGGER_NAME`; `git grep` không còn lời gọi `frappe.logger(` mức module nào trong `erp_ai/**`; chữ và mức log không đổi.
2. Trong touchpoint: đạt (2 file; `test_gateway.py` giống hệt nền, phép so `used_sinks()` ở `:937` không bị đụng).
3. Test đỏ trước, có ca lỗi, không skip: đạt. `test_import_creates_no_logger` đỏ `AssertionError: 1 != 0` trước khi sửa; `test_logger_failure_keeps_the_original_error_handling` phủ nhánh lỗi; 0 dấu skip.
4. Không đổi phép so theo hành vi sai, test độc lập: đạt. Hai test cũ (`test_source.py:112`, `:1348`) chỉ đổi cách vá, giữ `exception.assert_called_once()` và `warning.assert_called_once()`; test import nạp một bản sao của module dưới tên khác, không thay module đang nạp.
5. Xử lý lỗi: đạt. `except` rộng trong `_logger()` có lý do ghi cạnh và có test.
6. Bảo mật: đạt. Không khóa; đối số log không đổi.
7. Hợp đồng: đạt. Thuộc tính module `logger` mất, không chỗ nào trong repo dùng.
8. Tên, cấu trúc, phong cách: đạt (`LOGGER_NAME`, `_logger`).
9. Phụ thuộc: đạt (chỉ thêm `logging` của thư viện chuẩn).
10. Commit, nhánh: đạt (`fix(source): ... (FEAT-004)`, không dòng ghi công AI).

## Bằng chứng của dev (nguyên văn)
- RED: `test_gateway` chạy riêng: `'frappe.logger' : success` / `Ran 65 tests in 13.386s` / `FAILED (failures=1)`; `test_source`: `test_import_creates_no_logger` `AssertionError: 1 != 0` / `Ran 113 tests in 7.503s` / `FAILED (failures=5)`
- GREEN: `test_source` `Ran 113 tests in 6.500s` `OK`; `test_gateway` chạy riêng `Ran 65 tests in 5.033s` `OK`; `test_erp_ai_setting` `Ran 27 tests in 3.970s` `OK`; `test_architecture` `Ran 177 tests in 23.602s` `OK`; thứ tự `source` nạp trước (một tiến trình import `source` rồi chạy `test_gateway`): `Ran 65 tests in 5.121s` `OK`
- `bench --site miyano run-tests` của bench này không nhận `--module` lặp lại (hai `--module` chỉ chạy 65 test của gateway), nên thứ tự "nạp trước" được chạy bằng một script trong một tiến trình.

## Không kiểm được từ diff (tech-lead xử lý trước khi tick)
- `test_architecture` có luật nào về logger mức module hay `except` rộng mà `_logger()` phải đạt không: tech-lead chạy lại sau merge, kết quả ở mục dưới.
- Kiểm cuối của F-3 là một lần `cmd.test` cả app trên nhánh đã merge: ngoài phạm vi review, chờ khung giờ site độc quyền do team-leader xếp cho qa.

## Sau merge (tech-lead, `9adcdd6`, dưới khóa site, `PYTHONPATH` = worktree feat-004)
- `cmd.test_one` `erp_ai/gateway/test_gateway.py`, chạy riêng (thứ tự từng đỏ ở F-3): `Ran 65 tests in 8.204s` / `OK`
- `cmd.test_one` `erp_ai/agent/tools/test_source.py`: `Ran 113 tests in 8.060s` / `OK`
- `cmd.test_one` `erp_ai/tests/test_architecture.py`: `Ran 177 tests in 21.229s` / `OK` → mục "không kiểm được" thứ nhất khép: không luật nào phản đối `_logger()`
- `cmd.test_one` `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`: `Ran 27 tests in 11.066s` / `FAILED (errors=2)`, cả hai là `QueryDeadlockError (1213)` ở `setUp` (`test_utils.py:99`); chạy lại theo tên một lần (`test_blank_rules_message_has_default_json_not_constant_name`, `test_default_rules_valid`): `Ran 2 tests in 0.159s` / `OK`
- Thứ tự `source` nạp trước: dùng bằng chứng của dev (`Ran 65 tests in 5.121s` / `OK`); lần cả app của qa sẽ chạy lại thứ tự này.
- Không chạy `cmd.test` cả app (lệnh team-leader cho chặng này).

## deferred
- minor (1), (2) ở trên: không sửa ở chặng này.
