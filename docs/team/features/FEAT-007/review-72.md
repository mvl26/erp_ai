Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 72 — FEAT-007 T72

- Diff: `git diff caa555a7158708ed8ff377c864da338ea7a9464a..3fb63e2` (nhánh `team/FEAT-007-task-72`; 2 commit `648106b` test, `3fb63e2` mã; 9 file +67/−9, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `07745fc` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau commit test `648106b`), `MIGRATE_EXIT=0`: test_classification `Ran 55 tests in 0.162s FAILED (failures=9, errors=2)` (`AttributeError: module 'erp_ai.agent.classification' has no attribute 'CONFIDENCE_PCT_MIN'`; 9 subtest từ chối `AssertionError: Classification(category='A', …) is not None`; `TypeError: Classification.__init__() got an unexpected keyword argument 'confidence_pct'`); test_erp_ai_setting `Ran 103 tests in 7.096s FAILED (failures=2)` (`test_required_markers_match_design`, `test_missing_marker_blocked_each_part`). GREEN @ `3fb63e2`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_classification `Ran 55 tests in 0.168s OK`, test_erp_ai_setting `Ran 103 tests in 6.977s OK`, test_agent_runner `Ran 110 tests in 28.487s OK`, test_runner_routing `Ran 62 tests in 31.277s OK`, test_run_eval `Ran 23 tests in 0.538s OK`, test_doctype_descriptions `Ran 12 tests in 0.339s OK`, test_architecture `Ran 182 tests in 16.046s OK`.

Các phép kiểm riêng của reviewer:

- Đỏ đúng lý do: ở `648106b` chỉ file test đổi; lỗi do thiếu `CONFIDENCE_PCT_MIN`, tham số `confidence_pct` lạ, 9 subtest từ chối trả kết quả thay vì `None`, tuple mục bắt buộc và mô tả lệch. Không lỗi nào từ stub.
- C-4 một commit: khóa prompt mới, phần tử `PROMPT_REQUIRED_MARKERS` mới và mô tả JSON cùng ở `3fb63e2`.
- Diff JSON: dòng thô khớp `design-w1-fixes-4.md:88` từng byte (`diff` không báo khác); chữ hiển thị 367 ký tự, NFC, đủ bốn cụm của `test_doctype_descriptions`; chữ cũ áp hai chỗ sửa bằng chữ mới; `"modified"` từ 16:00 lên 17:00.
- Đầu vào bị từ chối có ghim: thiếu, null, True, False, -1, 101, 50.0, 80.5, "80". Được nhận có ghim: 0, 1, 50, 99, 100; kiểm cả kiểu `int` và nhãn `do_tin_cay` giữ. Dùng `isinstance` (ca bool đỏ), `<` chặt (100 đỏ), tối thiểu 1 (0 đỏ).
- Không khẳng định nào nới: `PROMPT_PARTS["classify"]` chỉ thêm mục; chú thích khớp phán quyết từng chữ; JSON tối thiểu của `test_optional_fields_default_safely` thêm khóa vì nay bắt buộc (đổi theo spec).
- Ba file test cuối chỉ thêm `"do_tin_cay_pct": 90` vào stub có sẵn.
- Chữ của `CHANGE_TOOLS_BLOCK` không xuất hiện trong diff.
- Mọi nơi dựng và đọc ở `3fb63e2` còn chạy: `runner.py:290`, `run_eval.py:195` đi qua `parse_classification`; nơi dựng `Classification(...)` trực tiếp chạy nhờ mặc định: `tools/write_ticket.py:44`, `test_routing.py` (8 chỗ), `tools/test_route_ticket.py:101`, `tools/test_write_ticket.py:580`; mọi stub JSON được parse đều có khóa, kể cả `test_runner_status.py` (import `CLASSIFY_A`). Chưa mã nào đọc `Classification.confidence_pct`.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đạt. Đủ Returns/Expect, không thừa.
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Đúng 9 file, không file mới.
3. Test trước, biên, không skip (STD-TEST-1/8/4): đạt.
4. Không uốn test, độc lập (STD-TEST-5/6): đạt.
5. Lỗi và đầu vào (STD-ERR-1/2/5): đạt. Đầu ra của model được kiểm chặt ở biên, cùng đường `None` như `do_tin_cay` sai.
6. Bảo mật (STD-SEC-1/3/4/6): đạt.
7. Hợp đồng và migrate (STD-DESIGN-3, STD-OPS-2): đạt. JSON chỉ đổi chữ mô tả và `"modified"`; hợp đồng parse chặt hơn như thiết kế đòi; nơi dựng trực tiếp chạy nhờ mặc định.
8. Tên, cấu trúc, style (STD-NAME-1/2, STD-STYLE-4/5): đạt.
9. Phụ thuộc (STD-DEP-1/3/5): không thêm.
10. Commit và tài liệu (STD-NAME-5, STD-GIT-1, STD-GIT-8, STD-DOC-2): đạt.

Findings:

- Không blocker, không major.
- minor | — | — | 2 small points: (a) STD-DESIGN-2, `erp_ai/agent/classification.py:48`: `confidence_pct: int = 0` adds a default that design section 3.6 does not have. It is needed so the direct `Classification(...)` builders outside the touchpoints keep working. But elsewhere in the project 0 is a real "0% sure" value: `policy._known_pct` treats it as known, and the meaning "unknown = -1/None" was set in `design-w0-fixes-2` section 1. So a `Classification` built in `write_ticket.py:44` would carry a known 0. The designer should rule on the default (0 vs `int | None = None`) before any code writes `confidence_pct` to the log. (b) STD-TEST-2, `erp_ai/agent/prompts.py:82-83`: no test checks the guidance sentence "Đặt do_tin_cay_pct = số phần trăm …"; only the key itself is checked, through the marker tests. | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Chạy test: reviewer không chạy; đề nghị chạy lại sau merge, thêm `test_runner_status` (dùng `CLASSIFY_A`), `test_routing`, `tools/test_write_ticket` (dựng `Classification` trực tiếp), ba module không có trong danh sách GREEN của dev.
- `cmd.lint`: dev nói RUF001 buộc viết `0-100` gạch nối thường thay cho `0–100` của thiết kế; reviewer không thấy lần chạy lint.
- `cmd.migrate` nạp lại DocType sau khi tăng `"modified"`: chỉ có `MIGRATE_EXIT=0` của dev.
- Ghi đè đã lưu: `build_classify_request` chưa dùng `prompt_override_classify` ở `3fb63e2`, nên ghi đè lưu trước T72 thiếu `"do_tin_cay_pct"` hôm nay vô hại; task nào nối ghi đè vào lúc chạy phải xử lý, nếu không mọi lần phân loại sẽ không parse được.
- Tài liệu: `docs/HuongDan_TrienKhai_erp-ai.md:1393-1401` còn JSON phân loại cũ; ngoài `files:` của T72, để `/team:asbuilt`.

## Kết luận của tech-lead

- Chạy test và migrate: xem dòng progress của T72 trong `tasks.md` (một lần giữ khóa sau merge, có `migrate`, mười module gồm cả ba module reviewer kê thêm; `test_erp_ai_setting` và `test_doctype_descriptions` đọc mô tả từ DocType đã nạp nên xanh là bằng chứng `migrate` đã nạp lại).
- Lint: dev chạy `pre-commit run --files` trên từng file, mọi hook `Passed`; `cmd.lint` cả cây chạy lại ở cuối lượt trên đầu `team/FEAT-007`. Chữ `0-100` khác ký tự gạch của `U1.md:250` là lệch chữ so với thiết kế, không lệch nghĩa; ghi cho designer/As-Built, không chặn tick.
- minor (a) (mặc định `confidence_pct = 0` mang nghĩa "biết, 0%"): chuyển designer phán trước T80/T81 (nơi đầu tiên đọc giá trị này); ghi vào dòng DỪNG lượt 15. Không mở vòng sửa vì sửa đúng cần chữ thiết kế.
- Ghi đè đã lưu và tài liệu triển khai: ghi cho team-leader ở dòng DỪNG lượt 15.
