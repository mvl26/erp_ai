# Frappe @ 15.126.1 (ERPNext 15.83.0): ghi User/role và DocType cấu hình dưới tài khoản không có System Manager (cache)

Ngày: 2026-11-12. Phiên bản: frappe 15.126.1 (`apps/frappe/frappe/__init__.py`; checkout `2e9ecdc03f`), erpnext 15.83.0, hrms 15.51.0. Nguồn gốc: research FEAT-005 (`docs/team/features/FEAT-005/research.md`, bảng U1–U10, C1–C9).

- **User:** `roles` (Has Role) nằm ở permlevel 1, cùng `role_profile_name`, `user_type`, `block_modules`, `restrict_ip`, `login_after/before`, `api_key/secret` (`user.json:227-649`, quyền `:890-913`). Muốn gán role thì cần quyền `write` ở level 1.
- **Frappe không kiểm role nào được gán.** Ai ghi được `roles` thì gán được cả System Manager (`user.py:172-206`, `:605-642`). Tool là chốt duy nhất.
- **Thiếu quyền level 1 thì role mới bị bỏ đi mà không báo lỗi** (`document.py:928-951`, `:3018-3046`). Cờ hẹp `doc.flags.ignore_permlevel_for_fields = ["roles"]` có trong mã và test (`test_user.py:237-269`), nhưng tài liệu không có.
- `role_profile_name` có giá trị thì `roles` bị thay toàn bộ (`user.py:208-212`). User `Administrator`/`Guest` chỉ Administrator sửa được (`user.py:1243-1246`). `send_welcome_email` không có mặc định, tool phải tự đặt. Không có Email Account thì Frappe không ném lỗi. Throttle 60 user/60 giây.
- **Custom DocPerm thay toàn bộ DocPerm** của DocType khi có ít nhất 1 dòng (`meta.py:553-566`). `setup_custom_perms` chép DocPerm chuẩn trước (`permissions.py:660-712`).
- **Custom Field:** `on_update` chạy DDL qua `sql_ddl`, mà `sql_ddl` commit trước nên không rollback được (`custom_field.py:206-216`, `database.py:422-426`).
- **Property Setter:** `make_property_setter` bỏ qua phân quyền (`property_setter.py:64-90`). Ai ghi được Property Setter thì đổi được `permlevel` của mọi trường.
- **Workflow:** `on_update` chạy cả khi `is_active = 0`. Nó tạo Custom Field trạng thái (owner Administrator) và chạy UPDATE SQL thẳng lên chứng từ có sẵn. Kích hoạt thì tắt các Workflow khác bằng SQL (`workflow.py:34-121`).
- **Notification:** `set_property_after_alert` khiến lúc gửi ghi chứng từ bằng `save(ignore_permissions=True)`. Có kênh Slack/SMS; `cc`/`bcc` là trường `Code` tự do; `is_standard` thì ghi file vào app. Frappe chỉ cấm `Email Queue` (`notification.py:21`, `:112-131`, `:200-223`).
- **Assignment Rule:** khi chạy, nếu người được giao thiếu quyền đọc thì Frappe tự chia sẻ chứng từ cho họ, trừ khi bật `disable_document_sharing` (`assign_to.py:122-134`; `assignment_rule.py:78-98`).
- **System Settings:** không trường nào ở permlevel > 0, nên có `write` là sửa được mọi trường bảo mật. **Holiday List:** chỉ HR Manager có quyền; `validate` tự chặn ngày ngoài khoảng và ngày trùng.

## Sources
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/user/user.json (truy cập 2026-11-12)
- https://raw.githubusercontent.com/frappe/frappe/v15.126.1/frappe/core/doctype/user/user.py (truy cập 2026-11-12)
- https://raw.githubusercontent.com/frappe/frappe/v15.126.1/frappe/model/document.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/user/test_user.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/custom/doctype/custom_field/custom_field.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/database/database.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/custom/doctype/property_setter/property_setter.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/workflow/doctype/workflow/workflow.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/email/doctype/notification/notification.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/desk/form/assign_to.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/system_settings/system_settings.json (truy cập 2026-11-12)
- https://github.com/frappe/erpnext/blob/v15.83.0/erpnext/setup/doctype/holiday_list/holiday_list.json (truy cập 2026-11-12)
- https://docs.frappe.io/erpnext/user/manual/en/role-based-permissions (truy cập 2026-11-12)
- https://docs.frappe.io/erpnext/user/manual/en/workflows (truy cập 2026-11-12)
- https://docs.frappe.io/erpnext/user/manual/en/notifications (truy cập 2026-11-12)
