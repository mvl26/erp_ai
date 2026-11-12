# Review package FEAT-006 T11 (ERP AI Setting: `auto_assign_enabled`, `routing_rules`, kiểm khi lưu), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=f1a732b; head=team/FEAT-006-task-11-cont (776839a; chứa 66c2452 của dev trước).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff f1a732b..team/FEAT-006-task-11-cont`
Commit: 66c2452 feat(setting): routing_rules and auto_assign_enabled fields with validation (FEAT-006); 776839a test(setting): pin field count and phrases for routing_rules and auto_assign_enabled (FEAT-006)
Stat: erp_ai_setting.json, erp_ai_setting.py, test_erp_ai_setting.py (touchpoint) + erp_ai/tests/test_doctype_descriptions.py (touchpoint mở rộng bởi tech-lead: `field_count` 22 -> 24 và 2 mục `phrases`; không nới khẳng định cũ, STD-TEST-5).
Tiêu chí: dòng T11 của `tasks.md` (AC-4 chặn lưu cấu hình sai, mặc định lưu được; AC-7c công tắc có trường), design.md mục 2.4 (trường, `description` <= 400 ký tự) và 3.3.
Điểm cần soi: (1) bảo vệ "để trống thì không kiểm" trong `check_routing_rules` (dev thêm vì `validate_routing_config("")` ném và T12 mới ghi mặc định): nhánh trống và nhánh có nội dung đều có test, đột biến trong đầu; trống kiểu `None`, `""`, chỉ khoảng trắng; (2) `description` của hai trường đúng sự thật, <= 400 ký tự, và `phrases` thực sự ghim nội dung; (3) kiểu trường (Check default "0", Code options JSON), vị trí trong `section_routing`; (4) thông điệp lỗi nêu đường dẫn khóa sai khi lưu.
Bằng chứng dev: RED 6 failure + 4 error (thiếu trường, cấu hình xấu không bị chặn); `test_erp_ai_setting` 24 OK; `test_doctype_descriptions` 10 OK; `cmd.test` 728 OK; lint pass; đột biến `if True` / `if False` ở bảo vệ đều đỏ rồi hoàn tác. Dev phải chạy `bench migrate` một lần để áp trường mới lên site `miyano` (xong, exit 0).
