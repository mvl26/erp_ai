Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 08 — FEAT-005 T8

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 5223674..1753c56` (nhánh `team/FEAT-005-task-8`, 1 commit, `erp_ai/tasks.py` + `erp_ai/tests/test_tasks.py` +326/−35; CHƯA merge)
- Vòng: 1
- Verdict: design-defect (vòng 1) — T8 dừng, chờ team-leader

## Vòng 1 — design-defect (`5223674..1753c56`)

Lớp 1 (khớp spec): mọi ý của Returns T8 có trong mã (tham số `now`, `PRIVILEGE_ALERT_SETTLE_S`, cận trên, đọc mốc `cache=False`, `datetime(1, 1, 1)` coi là rỗng, lọc `reason` + cửa sổ `(lower, upper]` + `like "%api_%"` + sắp `creation` tăng, lọc `ok` và `GENERIC_WRITE_TOOLS`, loại `Has Role`, so `permissions` trước/sau của DocType `DocType`, bảng động từ dựng từ tập tool dùng chung, `không rõ`, định dạng thời điểm). Không có phần ngoài phạm vi (không ghi mốc, không mục User/`[QUẢN TRỊ]`/fail-closed). Năm test viết lại so nguyên chữ mục.

- blocker | STD-DESIGN-1 | erp_ai/agent/test_runner_routing.py:1544 | `_findings()` còn gọi `tasks._permission_records_by_agent()` mà T8 xóa đúng theo chữ task; `test_privilege_findings_unchanged` (FEAT-006) sẽ lỗi `AttributeError` khi chạy cả app. File này không có trong design-amd2 §7 và không thuộc `files:` của T8; dev chỉ chạy test_tasks.py | Sửa plan: thêm `erp_ai/agent/test_runner_routing.py` vào touchpoint của T8 (hoặc chèn một task nhỏ); thay khóa `permission_records` bằng `tasks._privilege_changes_by_agent(None, now_datetime())` hoặc bỏ khóa đó và giữ phép so `alarms`; designer thêm dòng vào §7 | confirmed
- major | STD-TEST-8 | erp_ai/tests/test_tasks.py:552-570 (và :464-474) | Ảnh chụp DocType dựng tay chỉ khác nhau ở `permissions`: nếu mã so cả ảnh chụp thì mọi test vẫn xanh, báo nhầm (vd. bot sửa `description` của DocType) quay lại | Thêm một dòng DocType có ảnh chụp đổi trường khác (vd. `{"description": ...}`) trong khi `permissions` giống hoặc vắng ở cả hai phía, kỳ vọng 0 mục | confirmed
- minor | — | — | 3 điểm nhỏ: chú thích `_neutralize_agent_rows` còn nói tới điều kiện bản ghi phân quyền dù `modified_by` không còn được đọc (vòng lặp `PERMISSION_DOCTYPES` và `_add_perm(AGENT_USER)` trong `test_setup_neutralizes_live_rows_attributed_to_agent` hết tác dụng cho điều kiện này); `test_email_failure_keeps_alarm_logs_failure_and_continues` bị đổi phần gieo (bắt buộc vì `_add_perm` cũ không còn gây cảnh báo; số kỳ vọng 3 giữ nguyên, đạt STD-TEST-5); `upper` tính ngoài `try` nên `now=` sai sẽ ném thay vì được ghi log (D-20; scheduler không truyền đối số) | tùy dev

Bằng chứng của dev: nền chưa sửa `Ran 35 tests` / `OK`; RED `FAILED (failures=4, errors=6)`, vd. `'…phân quyền: Has Role mknaln34i5, User Permission …' != '…: tạo Role Profile ERPAI-TEST hồ sơ 1 (người ra lệnh …'`; GREEN `Ran 41 tests` / `OK`.

## Tech-lead đã kiểm

- `git grep -n "_permission_records_by_agent" team/FEAT-005-task-8 -- erp_ai`: kết quả ghi ở dòng progress của T8 trong `tasks.md` (xác nhận nơi gọi ngoài touchpoint).
- Theo skill build bước 9: `design-defect` → dừng T8, báo team-leader; tech-lead không tự thêm touchpoint và không thiết kế lại. Hai phát hiện gửi nguyên văn cho dev ở vòng 2 sau khi design-amd2 §7 và `files:` của T8 được sửa.

## Không kiểm được từ diff

- `test_runner_routing.py` và các module khác có xanh với thay đổi này không: cần lượt cả app.
- `cmd.lint` sạch.
- Bỏ dòng `EMPTY_DATETIME` có làm `test_empty_watermark_reads_from_the_start` đỏ trên site này không (theo nguồn Frappe thì có).

## deferred

Chưa có.
