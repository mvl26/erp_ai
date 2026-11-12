# dev T17 rework 1 (FEAT-006)

Nhánh `team/FEAT-006-task-17-rework1`, đầu nhánh 566e26f (FIX_BASE 887fa2c).

## Finding
major | STD-DESIGN-2 | write_ticket.py:55-60: D/E không bộ phận bỏ qua agent_group nhưng lý do rơi thành "ánh xạ không có giá trị".

## Thay đổi
- `_existing_values(wanted, reasons=None)`: field rỗng lấy lý do từ `reasons`, mặc định giữ "ánh xạ không có giá trị".
- `_mapped_values`: `reasons` = các note của `decision.notes` có field nằm trong `wanted` (agent_group). Mapping thật sự rỗng không có note nên giữ lý do cũ.
- Tham số `reasons` tùy chọn vì `route_ticket.py` (ngoài touchpoint) gọi `_existing_values` một đối số; bản đầu bắt buộc làm hỏng 21 test, đã sửa.

## Test phủ
- `test_de_skips_team_without_department`: thêm assert reason == "không có bộ phận".
- `test_category_a_without_team_in_mapping_keeps_mapping_reason` (mới): A với agent_group None giữ "ánh xạ không có giá trị".

## Lệnh và đầu ra
- RED: `AssertionError: 'ánh xạ không có giá trị' != 'không có bộ phận'` (test_de_skips_team_without_department), Ran 37, failures=1.
- GREEN test_write_ticket: Ran 37 tests ... OK.
- cmd.test toàn app: Ran 783 tests in 129.194s ... OK (baseline 887fa2c: 782 OK).
- pre-commit --files (2 file): tất cả Passed.

## Seen but not touched
`route_ticket.py:41` gọi `_existing_values` không truyền lý do nên D/E không bộ phận ở route_ticket vẫn ghi "ánh xạ không có giá trị" (cùng lỗi, ngoài touchpoint).
