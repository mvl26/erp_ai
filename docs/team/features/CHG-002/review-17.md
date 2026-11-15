Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 17 — CHG-002 T17

- Diff: `git diff a83923b..8694d7b` (nhánh `team/CHG-002-task-17`, 1 commit, 2 file, +200/−3; merge vào `team/CHG-002` ở `c2c7301`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve (0 blocker, 0 major)

## Vòng 1 — approve
`record_restart` và `confirm_restart` khớp design §3.6 và §4.4 bước 3. Hai thứ thêm ngoài thiết kế, đều nhận: kiểm `sent_at` là `datetime` (kiểm đầu vào, STD-ERR-2) và `_lock(name, *extra)` (hàm riêng, người gọi cũ dùng y như trước; `confirm_restart` đọc `restart_status` dưới cùng khóa dòng). Chữ ký `finish`, `log_step`, `content_digest`, `request_undo` không có hunk nào chạm. `ValueError` ném trước khi khóa nên lời gọi bị từ chối không ghi gì; không try/except. Reviewer thử bỏ từng phép kiểm trong đầu (`expected`, `value`, `change_status != expected`): mỗi phép có một test đỏ; `SENT_AT` khác `NOW` đã patch nên lưu `now_datetime()` cũng đỏ; `confirm_restart` được thử từ mọi `restart_status` khác `Đã gửi` (None, Đã xác nhận, Chưa xác nhận, Lỗi khởi chạy), so toàn bộ trạng thái để bắt ghi lạc.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. 2. Đạt. 3. Đạt (RED 55 lỗi `AttributeError … no attribute 'record_restart'`/`'confirm_restart'`; không skip). 4. Đạt (không assertion cũ nào đổi; L-1: 0). 5. Đạt. 6. Đạt (tên trường `*extra` chỉ từ mã; phân quyền là việc của T24 qua `_decider`). 7. Đạt. 8. Đạt. 9. Đạt (chỉ `datetime` của thư viện chuẩn). 10. Đạt (`feat(changes): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff, tech-lead đã xử lý
- Kết quả test: đợt merge 4 (`e6cda3e`, 06:48–06:57) `test_transitions` `Ran 68 tests in 30.801s` / `OK`, `test_architecture` `Ran 179 tests in 14.019s` / `OK`, cả app `Ran 1616 tests in 491.001s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Nghi vấn tranh chấp, cho T24 và thiết kế (không phải lỗi của T17, chữ ký do §3.6 và plan.md chốt): `confirm_restart(name, value)` chỉ kiểm `restart_status == Đã gửi`, không kiểm kết luận được tính cho `restart_sent_at` nào. Ca: đề xuất `Đã áp dụng` đã gửi restart, rồi bị hoàn tác; ai đó mở form giữa lúc hoàn tác, T24 đọc `restart_sent_at` cũ và bằng chứng; trong khe đó `record_restart(Đã hoàn tác, Đã gửi, t1)` của job hoàn tác commit; kết luận của lần restart cũ bị ghi lên lần mới. Khe vài mili giây → báo team-leader để designer phán (nhận, hoặc thêm tham số chỉ từ khóa mang `sent_at` đã dùng để tính) trước T24.
- T38 (job) và T24 (phương thức) có gọi đúng như §4.4 hay không: thuộc hai task đó.

## deferred
1. STD-TEST-1: RED chạy 67 test, GREEN chạy 68; một test mới (nhiều khả năng `test_reads_restart_status_under_one_lock_before_writing`) thêm sau lần RED, không có đầu ra đỏ riêng.
2. STD-TEST-8: kiểm `name` rỗng/None của `record_restart`, `confirm_restart` chưa có test (`TestTransitionInput._calls` chưa liệt kê hai hàm); phép kiểm là `_lock` dùng chung.
