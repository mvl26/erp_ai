# Review 38 — FEAT-001 T30 (Runner: vòng lập luận có giới hạn lượt và nhật ký từng lượt)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff b63a667..team/FEAT-001-task-30` (head b656975; vòng 2: `git diff d9dca07..team/FEAT-001-task-30`)

## Vòng 1 (review-raw-T30.md)
- major STD-ERR-4 runner.py:316: ngoại lệ tool chỉ thành `is_error` cho model, không dấu vết ở ERP AI Log/Error Log.
- minor: (1) kiểm chi phí tổng không tính tay; (2) test_stops_after_max_turns phụ thuộc giá trị lưu của `max_turns_per_run`; (3) `before`/`after` khóa theo tên tool bị ghi đè khi gọi lần hai trong một lượt, assert `deadline > monotonic()` yếu.

## Vòng 2
Major ADDRESSED (`tool <name>: <ExcClass>` nối bằng "; " vào `error` của dòng lượt; chỉ tên lớp, không thông điệp; test khẳng định `first.error == "tool get_ticket: KeyError"`, không chứa "bí mật", test hai tool lỗi). Minor 1, 2 ADDRESSED. Minor 3 NOT ADDRESSED (hoãn theo phán quyết, không chặn).

## Bằng chứng dev
Vòng 1: RED 51 test (8 failures, 12 errors đúng lý do thiếu hành vi) -> GREEN 51 OK, test_registry 24 OK; mutation từng guard đỏ (trừ `cache_control` chưa xác nhận). Vòng 2: RED (`None != 'tool get_ticket: KeyError'`), GREEN test_runner 52 OK, mutation bỏ ghi lỗi -> 2 test đỏ; pre-commit pass; đếm HD Team/HD Ticket/User/ERP AI Log/Error Log 4/3/8/0/196 trước = sau.

## Deferred
- minor 3 (before/after ghi đè; assert deadline yếu).
- `skipped`/`reason` của `set_classification` chưa vào dòng classify (design-gap AC-10, review-36).
- `fetch_ticket_comments` chạy hai lần mỗi lượt (authority.latest_instructor tự đọc; authority.py ngoài touchpoint).
- Ngữ cảnh/`latest_instructor` dựng trước lời gọi classify trên ticket_insert: hành vi giống, nhưng truy vấn comment chạy cả khi classify lỗi cổng.
- Test `test_reason_entries_are_committed_one_by_one` ghim thứ tự commit [0,1,1,2] phụ thuộc `_call_model`/`write_entry` ngoài hunk; xanh khi chạy.
