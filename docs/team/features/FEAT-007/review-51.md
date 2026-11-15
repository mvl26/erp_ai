Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 51 — FEAT-007 T51

- Diff: `git diff 07745fc3e3bb96c996963b04ca8682dd58d15f89..2288533` (nhánh `team/FEAT-007-task-51`; 2 commit `367aca4` test, `2288533` mã; 2 file mới +443, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3). Lần gọi reviewer đầu (round 94) chạm trần 25 lượt, không trả báo cáo; báo cáo dưới đây là của lần gọi lại (round 96), cùng diff, cùng bằng chứng.
- Verdict: approve; CHƯA merge, CHƯA tick (lượt 15 chạm trần T33 + 6 merge mới trước khi tới lượt task này; nhánh `team/FEAT-007-task-51` @ `2288533` giữ lại, merge đầu lượt 16)
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau commit test `367aca4`, với một stub chưa commit `build_daily_report` trả `{}`), `MIGRATE_EXIT=0`: `FAIL: test_twelve_tickets_sections`: `AssertionError: Items in the second set but not the first: 'new_list' 'c_missing_ba_note' 'due_soon' …`; `ERROR: test_de_progress_window_edges`: `KeyError: 'de_progress'`; `ERROR: test_excluded_ticket_number_only_in_every_list`: `KeyError: 'overdue'`; `ERROR: test_hours_and_days_come_from_settings`: `KeyError: 'due_soon'`; `ERROR: test_no_due_field_uses_resolution_by`: `KeyError: 'overdue'`; `Ran 5 tests in 1.984s FAILED (failures=1, errors=4)`. Lần chạy mã đầu có hai chỗ đỏ sửa trước commit mã: `test_architecture` `test_feature_never_assigns_sla_dates` ("holds the name of an SLA date (AC-10)"); `test_de_progress_window_edges` (kỳ vọng của test sửa từ E `done: 1` thành 0 cho phiếu giải quyết đúng lúc `anchor`). GREEN @ `2288533`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_daily_report `Ran 5 tests in 2.083s OK`, test_architecture `Ran 182 tests in 16.250s OK`.

Checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đạt. Dict có đúng tám khóa của Returns, test ghim (`set(result) == REPORT_KEYS`); `bot_actions`, `cost_yesterday` để task sau. Mỗi mục theo `design.md:439-449`. Một điều kiện thêm không có test (minor).
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Chỉ hai file.
3. Test trước, biên, không skip (STD-TEST-1/8/4): đạt. RED hình thức: stub trả `{}` cho một AssertionError thiếu khóa và bốn KeyError. Hai mép cửa sổ ghim cho "mới" (start trong, start−1s ngoài, anchor−1s trong, anchor ngoài) và cho `done`; mép `due_soon`/`overdue` ghim (anchor là quá hạn, anchor+1s và anchor+24h là sắp hạn, anchor+24h+1s không thuộc); ngưỡng 24 h, 48 h, 3 ngày ghim hai phía; mỗi ngưỡng đọc từ cấu hình.
4. Không uốn test, độc lập (STD-TEST-5/6): đạt. Kỳ vọng sửa (E giải quyết đúng `anchor` → `done: 0`) là điều cửa sổ nửa mở `[anchor − 24 h, anchor)` của thiết kế cho; test sửa theo spec, không theo mã sai; đổi `<` thành `<=` thì đỏ. Mốc là ngày cố định năm 2002, cấu hình gieo từng test; khẳng định danh sách lọc theo phiếu của test; khẳng định đếm chỉ đếm loại phiếu `ERPAI-TEST daily *` trong cửa sổ 2002; mọi test rollback.
5. Lỗi và biên: đạt (hàm dựng chỉ đọc).
6. Bảo mật: đạt. Theo A-D5 phiếu loại trừ không mang `subject`.
7. Hợp đồng: đạt. Dùng đúng các tên Receives, không viết lại.
8. Tên, cấu trúc, mã chết: đạt; docstring module nói quá (minor).
9. Phụ thuộc: không thêm.
10. Commit và tài liệu: đạt.

Định nghĩa từng mục so với thiết kế, đều theo thiết kế: mới = tạo trong `[start, anchor)`; sắp hạn / quá hạn = `processing_deadline` của phiếu mở trong `(anchor, anchor+due_reminder_hours]` / `≤ anchor`, D-18 chọn mốc; quá mốc phản hồi = `routing.response_overdue(...)`; C thiếu BA note; C/D thiếu task; tiến độ D/E.

Chỗ thiết kế để mở, dev điền bằng lựa chọn hợp lý không thêm nghĩa nghiệp vụ (khoảng trống cho designer, không phải finding, không phải `design-defect`): (a) "mở" chưa định nghĩa: mã dùng `status_category != "Resolved"` với `creation < anchor`, đọc trạng thái lúc chạy; (b) dạng của `new_by_category_priority`: `{category: {priority: count}}`; (c) dạng phần tử của các danh sách ngoài `new_list`: dùng lại `{name, category, priority, subject | excluded}`, phần tử `due_soon`/`overdue` không mang mốc hạn nên nơi dựng email không ghi được "còn X giờ"; (d) thứ tự danh sách: `creation asc, name asc`; (e) `done` có phải đang Resolved không: mã chỉ xét `resolution_date` trong cửa sổ.

A-D5: phiếu opt-out chỉ hiện số ở `new_list` (test mười hai phiếu) và ở `overdue`, `response_overdue`, `c_missing_ba_note`, `cd_missing_task`; `due_soon` chưa phủ (đi cùng `_items`, minor).

`test_feature_never_assigns_sla_dates`: luật giữ AC-10 (không gì dưới `agent/` ghi `response_by`, `resolution_by`) và bắt cả phép gán giữ tên đó. Module chỉ đặt `"resolution_by"` trong `fields=[…]` của một lần đọc `frappe.get_all`, không có đường ghi nào; đọc trường không phải điều luật canh, nên module tuân thủ, không lách.

Findings:

- Không blocker, không major.
- minor | — | — | 3 small points: (a) STD-DOC-7, `daily_report.py:3-4`: the docstring says every figure is computed "as of `anchor`, never from the moment the job runs". In fact open status, `first_responded_on`, BA-note comments and Tasks are all read at run time. Fix: say that "open" and the other states are read at run time. (b) STD-TEST-8 / STD-DESIGN-5, `daily_report.py:123`: the `comment_type: "Comment"` filter is not in the design, and no test has a decoy for it. Fix: drop it, or keep it and add a bot comment with the marker and another `comment_type`. (c) STD-TEST-8, `test_daily_report.py` (`test_excluded_ticket_number_only_in_every_list`, key tuple): `due_soon` is missing from "every list". Fix: add an excluded ticket that is due soon, or rename the test. | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Nơi đăng BA note thật (U8) có lưu Comment `comment_type="Comment"`, chủ `AGENT_USER`, nội dung bắt đầu bằng đúng `**BA note**` không bọc HTML (`<p>`) hay không; test gieo nội dung bằng `db_insert`.
- Helpdesk có giữ `resolution_date` khi phiếu mở lại không (nếu giữ, phiếu vừa `done` vừa `in_progress`).
- Hành vi khi cột `field_due_date` đã cấu hình bị gỡ: `get_all` ném và dừng cả báo cáo.
- Chi phí truy vấn: `can_send_ticket(row.name)` một `get_value` mỗi phần tử.
- Reviewer không chạy test.

## Kết luận của tech-lead

- Chưa merge nên chưa có lần chạy sau merge; lượt 16: merge, một lần giữ khóa `migrate` + test_daily_report + test_architecture, rồi tick.
- Nơi đăng BA note: trên `team/FEAT-007` @ `56b10be` hằng `BA_NOTE_MARKER` chỉ được định nghĩa ở `erp_ai/agent/ops_data.py:11`, chưa có mã nào đăng BA note (`git grep`); phép so "bắt đầu bằng marker, `comment_type="Comment"`" phải được kiểm lại ở task đăng BA note của U8. Ghi ở dòng DỪNG lượt 15, không chặn T51.
- Năm khoảng trống (a)–(e), `resolution_date` khi mở lại, cột hạn bị gỡ: chuyển designer trước T52–T54 (cùng module) và trước task dựng email; ghi ở dòng DỪNG lượt 15.
- minor (a), (b), (c): không mở vòng sửa; T52 (task kế trên hai file này) dọn.
