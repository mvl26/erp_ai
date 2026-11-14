Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 60 — FEAT-004 T60

- Diff: `team/FEAT-004-task-60` (head 7b55147), khoảng `8eebed8..team/FEAT-004-task-60` (base 8eebed8 = đầu T59, review riêng)
- Vòng: 1
- Verdict: approve

Lệnh git đã chạy (chỉ đọc):
```
git log --oneline 8eebed8..team/FEAT-004-task-60
git diff --stat 8eebed8..team/FEAT-004-task-60
git diff 8eebed8..team/FEAT-004-task-60
git log -1 --format='%B' 7b55147
git show team/FEAT-004-task-60:erp_ai/agent/tools/site_api.py
git show team/FEAT-004-task-60:erp_ai/agent/tools/test_site_api.py
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md          (dòng T60)
git show team/FEAT-004:docs/team/features/FEAT-004/review-chg001.md  (Nhóm G)
git show team/FEAT-004:docs/team/features/FEAT-004/spec.md           (AC-30, AC-31)
```
Một commit, 2 file (`site_api.py` +9, `test_site_api.py` +68), đúng touchpoint.

## Lớp 1 — khớp spec
- AC-30 "từ chối thì 0 bản ghi đổi": `_write` (site_api.py:157-163) bắt mọi `Exception` còn lại, `rollback(save_point=SAVEPOINT)`, trả `ok=false` lý do ngắn, không đưa `str(exc)` ra lý do; lỗi không phải Permission/Validation gọi `frappe.log_error`. Khớp dòng "Returns" của T60.
- AC-31 Webhook luôn tắt ở chế độ thường (tạo và sửa) và từ chối đổi tên: đã có test.
- Không thiếu, không thừa: không có file ngoài touchpoint, không thêm tính năng.

## Đối chiếu phát hiện cũ (review-chg001 Nhóm G)
| Phát hiện | Trạng thái | Bằng chứng |
|---|---|---|
| major STD-ERR-7 `site_api.py:127-136` `_write` chỉ bắt Permission/Validation | ADDRESSED | erp_ai/agent/tools/site_api.py:157-163; test erp_ai/agent/tools/test_site_api.py:451-463 (tên trùng), 465-481 (lỗi hook) |
| major STD-TEST-2 nhánh chưa test — phần từ chối đổi tên | ADDRESSED | erp_ai/agent/tools/test_site_api.py:438-449 |
| major STD-TEST-2 nhánh chưa test — phần Webhook luôn tắt | ADDRESSED | erp_ai/agent/tools/test_site_api.py:418-436 |
| major STD-TEST-2 — phần AC-33 (liên kết bot đọc được, mật khẩu/khóa API ở chế độ toàn quyền) | ngoài phạm vi T60 | thuộc T61 |

## Test trước mã (đọc test trước)
- `test_hook_error_leaves_no_partial_write`: `on_update` chạy sau `db_insert`, `hook.assert_called_once()` xác nhận dòng Note đã được ghi trước lỗi; `count`/`exists` sau đó chỉ xanh khi thật sự rollback → test đổ khi bỏ rollback. Lý do được ghim nguyên văn, `assertNotIn("hook boom")` ghim việc không lộ chi tiết.
- `test_duplicate_name_rolls_back_to_savepoint`: insert trùng không để lại dòng nên `count` tự nó không phân biệt; nhưng `rollback` được `wraps` và `assert_any_call(save_point=SAVEPOINT)`, lý do "đã có bản ghi cùng tên" chỉ nhánh mới trả → bỏ nhánh hay bỏ rollback đều đổ.
- `test_rename_is_refused`: lý do ghim nguyên văn, RED của dev (xóa phép kiểm) cho lý do khác → test đổ khi bỏ nhánh.
- `test_webhook_always_saved_disabled_in_normal_mode`: kiểm cả tạo lẫn sửa `enabled=1`; RED của dev (xóa mục Webhook của `FORCED_VALUES`) cho `1 != 0`. Đếm Webhook tương đối (`before + 1`), không phụ thuộc dữ liệu site.
- RED/GREEN có trong gói: 2 test fix ERROR trước khi sửa; 2 test nhánh cũ FAIL khi gỡ nhánh; GREEN `Ran 46 tests ... OK`, test_architecture `Ran 133 tests ... OK`.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major | — |

minor | — | — | 2 điểm nhỏ: (1) STD-ERR-4 site_api.py:159 `frappe.log_error(title, message)` làm `message` thay cho traceback (frappe/utils/error.py:47-51), Error Log chỉ còn tên lớp lỗi và DocType, không có tên bản ghi hay vị trí hook → lỗi hook thật khó lần; cân nhắc thêm `name` (khi sửa) và traceback không kèm biến cục bộ; (2) STD-STYLE-4 site_api.py:161 lý do "đã có bản ghi cùng tên" là chuỗi trực tiếp trong khi lý do còn lại là hằng `UNEXPECTED_ERROR_REASON` | tùy dev

## Review checklist (10)
1. Đạt — làm đúng và đủ T60 (AC-30, AC-31 phần Webhook/đổi tên), không thừa (STD-DESIGN-5, STD-TEST-2).
2. Đạt — chỉ 2 file touchpoint, không file mới (STD-DESIGN-1, STD-STRUCT-1, STD-STRUCT-2).
3. Đạt — RED trước GREEN có trong gói; có test đường lỗi (tên trùng, lỗi hook); không skip/xfail (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Đạt — không sửa assertion cũ; test dùng rollback của `setUp`, chặn commit, đếm tương đối (STD-TEST-5, STD-TEST-6).
5. Đạt — lỗi được rollback, ghi log, trả lý do; không nuốt im (STD-ERR-1); ghi chú STD-ERR-4 ở dòng minor.
6. Đạt — lý do trả cho model không chứa `str(exc)` hay traceback; log không ghi giá trị trường (STD-SEC-4, STD-SEC-6).
7. Đạt — dạng trả `{"ok", "reason", "doctype"}` giữ nguyên (STD-DESIGN-3).
8. Đạt — tên hằng UPPER_SNAKE, không mã chết (STD-NAME-2, STD-STYLE-5).
9. Đạt — không thêm phụ thuộc (STD-DEP-1).
10. Đạt — nhánh `team/FEAT-004-task-60`, commit `fix(site_api): ... (FEAT-004)` không có trailer AI (STD-NAME-4, STD-NAME-5, STD-GIT-8, STD-GIT-1).

## Không kiểm được từ diff
- Lỗi làm MariaDB rollback cả giao dịch (deadlock, `QueryDeadlockError`, mất kết nối) xóa luôn savepoint; khi đó `rollback(save_point=SAVEPOINT)` trong nhánh `except` (site_api.py:158, cùng mẫu ở các nhánh cũ) có thể tự ném "SAVEPOINT does not exist" và thoát khỏi `_write` — nghi vấn, chưa chạy; tech-lead cân nhắc có cần test hay ghi debt.
- `frappe.log_error` chèn Error Log ngay trong giao dịch ngoài; nếu vòng agent sau đó rollback cả giao dịch thì bản log mất — phụ thuộc nơi gọi `execute_tool`, ngoài diff.
- Test không chạy lại (site dùng chung). Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.tools.test_site_api`.

## Deferred
- Không có.
