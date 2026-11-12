# Review T23 vòng 1 — request-changes

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 1117974..team/FEAT-006-task-23 -- erp_ai` (a123a3a). Checklist 10/10; lớp 1 (spec) đạt; lớp 2 có 2 major (test che lỗi, mutation vẫn xanh).

## Findings (nguyên văn từ reviewer)

major | STD-TEST-8 | erp_ai/agent/test_classification.py:266,276-293 (code: prompts.py:214-216) | Nhánh `if category in ("D", "E")` chỉ được khẳng định ở dòng D. Dòng E không có assert nào, mà E chính là dòng cũ chứa tên viết cứng "Lan / Hà / Thư / Chi", trọng tâm của AC-14. Đổi thành `== "D"` thì E lấy người từ `assignees`, ra "-", mà test vẫn xanh. Ngoài ra fixture đặt `team` trùng tên bộ phận (`{"Kế toán": {"team": "Kế toán", ...}}`). Vì vậy nếu code lấy khóa dict thay cho `d["team"]` thì test vẫn xanh. Phần gộp nhiều bộ phận (`dict.fromkeys`, `"; ".join`) cũng chưa có case nào. | Thêm assert đầy đủ cho dòng E. Đặt `team` khác tên bộ phận, ví dụ `{"team": "Nhóm KT"}`. Thêm bộ phận thứ hai, một bộ phận dùng chung team để thử phần khử trùng.

major | STD-TEST-8 | erp_ai/agent/test_agent_runner.py:880-891 (code: runner.py:516-523) | `_config_users` gom user từ 3 nguồn: default, `prefixes`, `departments.*.head`. Test runner chỉ đặt `assignees.A.default`. Còn các test unit truyền `names` trực tiếp, không đi qua `_config_users`. Vì vậy bỏ dòng `prefixes` hoặc dòng `head` thì prompt sẽ hiện email thay tên người, mà mọi test vẫn xanh. | Trong test runner, đặt thêm một user prefix và một trưởng bộ phận, đều tạo bằng `make_active_agent`. Khẳng định tên giả `f"{PREFIX}Tên của {uid}"` của cả ba có trong `system`.

minor (dev tự quyết): dòng C (60/1440) không được khẳng định; `_cell` thay `|` và `\n` chưa có case; bước trước/sau nên chặt hơn (`table2 == table1.replace("Người A1", "Người Mới")`); AC-14 nói đổi người đầu mục B, test đổi A (tương đương).

## Cannot verify (tech-lead xử lý)

- cmd.test: dev dán 840 OK; tech-lead kiểm cây mã sau merge trùng cây đã chạy xanh.
- Bảo vệ tĩnh AC-14 thuộc T26 (lưu ý "Việt Nam"/"Tiếng Việt" là trùng chữ, quét phải theo ranh giới từ).
- Trượt cache prompt sau khi sửa `routing_rules`: hệ quả design 3.7, không phải lỗi.
