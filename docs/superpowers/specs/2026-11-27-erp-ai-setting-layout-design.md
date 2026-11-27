# Bố cục form ERP AI Setting: tab, hai cột, mô tả rõ hơn — thiết kế ngắn

Ngày: 2026-11-27. Yêu cầu của quản trị: chia form thành các phần rõ ràng, bố trí hai bên (hai cột), không xếp hết một
bên; cài đặt khó hiểu nên rất khó dùng.

## Vì sao

Trước: 85 trường dữ liệu trong 15 Section Break, không Tab Break, không Column Break; mỗi trường có mô tả tới 400 ký
tự ngay dưới, nên trang rất dài. Nhãn "Năm quyền mở rộng" đã sai vì nay có bảy công tắc.

## Thiết kế

1. Bảy tab theo mục đích. Thứ tự các phần đổi để gom theo tab; giá trị vẫn nằm trong `tabSingles` theo fieldname nên
   không mất dữ liệu. Không đổi tên, kiểu, mặc định, options, reqd, read_only của trường dữ liệu nào.
2. Phần có từ hai trường ngắn (Check, Select, Int, Float, Data, Link, Date, Datetime và ô chữ một dòng
   `thinking_text`) có Column Break: cột trái, cột phải. Trường rộng (Table, Code, Long Text, danh sách Small Text)
   không nằm trong cột: phần chứa nó chỉ có một cột và nhiều nhất một trường ngắn. Vì vậy vài phần dài được tách
   thành phần nhỏ có nhãn (10 phần mới), thứ tự trường bên trong giữ nguyên.
3. `section_permissions` giữ đúng bảy Check theo thứ tự cũ và `site_environment`; Column Break nằm giữa
   `code_change_enabled` và `console_enabled`. Code đọc danh sách công tắc từ `policy.PERMISSION_SWITCH_FIELDS`.
4. Phần ít dùng gập sẵn (`collapsible: 1`): tên trường của phiếu, app được phép sửa code, ghi đè prompt.
5. Mô tả: câu đầu nói ô làm gì, sau đó bật/tắt thì sao; giữ mọi dữ kiện và mọi cụm bắt buộc của
   `test_doctype_descriptions.py`, tối đa 400 ký tự. "năm quyền mở rộng" thành "các quyền mở rộng". Ba mô tả là hợp
   đồng nguyên văn trong test (`code_change_enabled`, `code_change_apps`, `console_enabled`) nên giữ nguyên.
6. Nhãn trường dữ liệu giữ nguyên: thông báo lỗi, thông báo bật quyền, cảnh báo leo quyền và các mô tả khác gọi
   trường theo nhãn.
7. `modified` của DocType nâng lên 2026-11-27 để `bench migrate` đồng bộ bố cục mới.

## Cây tab → phần → cột

| Tab | Phần (fieldname: nhãn) | Cột trái | Cột phải |
| --- | --- | --- | --- |
| `tab_activation` Kích hoạt & quyền | `section_activation`: Bật agent và mức quyền | enabled, permission_level | agent_enabled_at |
| | `section_permissions`: Quyền mở rộng (mặc định tắt) | unrestricted_enabled, record_tools_enabled, act_now_enabled, code_change_enabled | console_enabled, one_click_approval_enabled, server_script_read_enabled, site_environment |
| `tab_autonomy` Mức tự chủ | `section_autonomy`: Mức tối đa theo đầu mục | level_cap_a, level_cap_b, level_cap_c | level_cap_d, level_cap_e, level_cap_f |
| | `section_confidence` (mới): Ngưỡng độ tin cậy và Tự làm | confidence_threshold | auto_approve_streak |
| | `section_catalog`: Danh mục trắng và mẫu tài khoản | catalog_rules, user_templates (cả bề ngang) | |
| `tab_model` Model & chi phí | `section_model`: Model, từ khóa và chỉ báo trả lời | model_classify_default, trigger_keyword | thinking_text, answer_delay_min_s, answer_delay_max_s |
| | `section_credentials` (mới): Khóa API | credentials (cả bề ngang) | |
| | `section_limits`: Giới hạn mỗi lần chạy | max_turns_per_run, max_runs_per_ticket_per_day | max_keys_per_call, request_timeout_s |
| | `section_budget`: Ngân sách và đơn giá | monthly_budget_usd, spent_this_month_usd | bốn đơn giá |
| `tab_routing` Phiếu & định tuyến | `section_routing`: Phiếu bỏ qua và ánh xạ đầu mục | excluded_teams, excluded_title_prefixes, category_mapping (cả bề ngang) | |
| | `section_assignment` (mới): Tự gán người và bảng tag | auto_assign_enabled, tag_assignees | |
| | `section_routing_rules` (mới): Quy tắc định tuyến và người nhận mặc định | routing_rules, default_assignee | |
| | `section_ticket_fields` (gập): Tên trường có sẵn trên phiếu | field_ticket_nature, field_erp_module, field_origin, origin_board_value | field_due_date, field_project, field_item_code, field_serial_no |
| `tab_knowledge` Trả lời & tri thức | `section_knowledge`: Trả lời, đóng phiếu và tri thức | reply_enabled, resolve_on_tasks_done_enabled, close_silent_f_enabled, close_silent_f_days | kb_draft_enabled, knowledge_search_limit, manuals_dir |
| | `section_reports` (mới): Báo cáo bot được chạy | allowed_reports, report_row_limit | |
| | `section_digest` (mới): Trích yếu HDSD | prompt_digest | |
| | `section_lessons`: Bài học của bot | lessons_enabled | lessons_max_per_request, lessons_max_chars, lesson_teach_marker |
| `tab_reports` Báo cáo & cảnh báo | `section_operations`: Báo cáo 08:00 hằng ngày | coo_report_recipients, daily_report_weekends | |
| | `section_review` (mới): Rà soát tháng | monthly_reviewers, review_sample_size | |
| | `section_reminders` (mới): Theo dõi và nhắc hạn | d_ticket_watcher, due_reminder_hours, ba_note_due_hours | task_due_days, max_tasks_per_run |
| | `section_kpi` (mới): Mục tiêu KPI | kpi_targets | |
| | `section_report_marks` (mới): Mốc gửi do hệ thống ghi | daily_report_sent_on | budget_alert_sent_month |
| | `section_alerts`: Người nhận cảnh báo | alert_recipients, privilege_alert_checked_until | |
| `tab_advanced` Nâng cao | `section_code_change` (gập): App được phép sửa code | code_change_apps | |
| | `section_prompts` (gập): Ghi đè prompt | ba ô ghi đè, prompt_revisions | |

## Khác với gợi ý ban đầu

- Bảng Khóa API rời khỏi phần cảnh báo sang tab Model & chi phí: khóa dùng để gọi model, đi cùng giới hạn lời gọi
  và đơn giá; phần cảnh báo chỉ còn người nhận cảnh báo.
- Trích yếu HDSD rời phần định tuyến sang tab Trả lời & tri thức, cạnh Kho HDSD: nó là tri thức nối vào bước lập
  luận, không liên quan định tuyến.
- Ngưỡng độ tin cậy và số lần duyệt liên tiếp tách khỏi sáu mức tối đa thành phần riêng (cột A–C, D–F gọn).

## Kiểm thử

`erp_ai/tests/test_doctype_descriptions.py`: `SETTING_LAYOUT` ghim cả cây; luật hai cột và trường rộng; hình dạng
Tab Break và Column Break; form mở bằng tab. Các test cũ ghim thứ tự trường đọc thứ tự bỏ qua Column/Tab Break và vẫn
ghim cùng thành viên và thứ tự trong từng phần; nơi một phần được tách, các phần con nối nhau đúng thứ tự cũ.
