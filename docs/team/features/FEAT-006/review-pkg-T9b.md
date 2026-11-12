# Review package FEAT-006 T9b (bộ kiểm `routing_rules`: từ chối trống và khóa tiền tố rỗng), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=8a1bd31; head=team/FEAT-006-task-9b (1a870d5).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 8a1bd31..team/FEAT-006-task-9b`

Commit: `1a870d5 fix(routing): reject blank routing_rules and empty prefix keys (FEAT-006)`

Stat:
```
 erp_ai/agent/routing.py                              | 12 +++++++++++-
 erp_ai/agent/test_routing.py                         | 20 ++++++++++++++++++++
 .../doctype/erp_ai_setting/erp_ai_setting.py         |  4 +---
 .../doctype/erp_ai_setting/test_erp_ai_setting.py    |  4 ++--
 4 files changed, 34 insertions(+), 6 deletions(-)
```
Touchpoint của T9b: 4 file trên và không file nào khác.

Tiêu chí (quyết định người, journal FEAT-006 "quyết định 4 điểm"):
1. `routing_rules` trống/NULL/chỉ khoảng trắng: `validate_routing_config` ném `frappe.ValidationError`, câu báo nêu cách khôi phục mặc định đúng sự thật với `install._ensure_default_settings` (chỉ ghi khi DB NULL). `ERP AI Setting.check_routing_rules` kiểm cả khi trống. `load_routing_config` vẫn trả `{}` cho trống, không ném.
3. Khóa tiền tố rỗng/khoảng trắng trong `assignees.<A|B|C|F>.prefixes`: bộ kiểm từ chối, câu báo nêu đường dẫn. `_category_assignee` (T8) vẫn bỏ qua khóa rỗng.
Test cũ `test_blank_rules_save_until_install_writes_default` đổi kỳ vọng theo hành vi mới (STD-TEST-5), không nới khẳng định khác.
AC-4: cấu hình sai dạng bị chặn khi lưu. Design: design.md mục 3.3.

Điểm cần soi: tính đúng của câu khôi phục; trống ở mọi dạng (None, "", khoảng trắng, "\n"); khóa rỗng ở cả bốn đầu mục; không làm lỏng ca của T9/T11 (đổi tên/kỳ vọng chỉ đúng một test).
