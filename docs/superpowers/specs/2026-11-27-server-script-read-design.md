# Cho bot đọc Server Script — thiết kế ngắn

Ngày: 2026-11-27. Nguồn: phiếu "Server Script thông báo hạn thanh toán Purchase Invoice không gửi", bot trả lời
"DocType Server Script chưa được mở". Người quản trị muốn mở việc đọc từ form ERP AI Setting, không sửa code.

## Làm gì

Công tắc `server_script_read_enabled` (nhãn "Cho bot đọc Server Script", mặc định tắt, trong `section_permissions`).
Bật thì bot có hai tool của nhóm `script_read` (`erp_ai/agent/tools/script_read.py`):

- `list_server_scripts`: lọc theo `reference_doctype`, một phần tên (`name_contains`), `script_type`; gồm cả script đang
  tắt; mới sửa trước; `limit` mặc định 20, tối đa 50; `more` cho biết còn script bị bỏ ngoài. Trả tên, loại, DocType,
  sự kiện, hàm API, tần suất, trạng thái tắt, lúc sửa; không trả nội dung.
- `get_server_script(name)`: các trường trên, `cron_format` và `script` đã che bí mật. Script dài bị cắt phần cuối
  (`script_cut`) sao cho cả kết quả vừa `read.TOOL_RESULT_MAX_CHARS`, trần runner đặt cho JSON của mỗi kết quả tool.
  Không có tên đó: `{"ok": false, "reason": "không tìm thấy Server Script"}`.

`get_record` vẫn không đọc Server Script. Lời từ chối nói cách đọc: dùng `get_server_script` khi lượt chạy có tool đó
(hỏi `registry.grant`), "chưa được mở (công tắc … đang tắt)" khi công tắc tắt, và chỉ "chưa được mở" khi công tắc bật
mà lượt không có tool (dưới ngưỡng, soạn bài KB). Không đổi đường ghi: Server Script ghi qua `site_api` vẫn luôn bị lưu
ở trạng thái tắt.

## Cấp quyền

Trong `registry.GRANT_TABLE`: công tắc bật, không dưới ngưỡng độ tin cậy, không phải lượt soạn bài KB. `grant()` không
cấp gì ở L0 hay mức lạ, nên "từ L1". Vì chỉ đọc, nhóm theo nhóm `read` ở chỗ còn lại: không cần ERP AI Instructor,
vẫn có khi vượt ngân sách và khi trần đầu mục hạ mức luồng chính. Khác `read`: dưới ngưỡng thì không có. Lượt đó chỉ
đăng một câu hỏi về một phân loại chưa chắc (`ASK_ONLY_BLOCK`), nên bộ tool của nó giữ nguyên: nhóm `read` và tool hỏi.
Lượt soạn bài KB giữ hàng cố định của nó (`read` + `kb_draft`). Handler tự kiểm lại công tắc trong `ToolContext`.

Công tắc là một công tắc quyền (`policy.PERMISSION_SWITCH_FIELDS`, `SWITCH_FLAGS`, `PermissionSwitches.
server_script_read`): bật/tắt có dòng `bot_action` trong ERP AI Log, bật thì có thông báo trên form, và cảnh báo hằng
ngày về quyền mở rộng liệt kê nó (`tasks._enabled_permission_switches`).

## Vì sao bỏ qua phân quyền role

Chỉ Script Manager đọc được Server Script. Tài khoản agent chỉ có ERP AI Agent và Agent, và không được thêm role:
`tasks._agent_role_drift` báo động mọi role thừa, và một role mở cả DocType cho mọi tool, kể cả ghi. Công tắc là lời
cấp: ERP AI Setting chỉ System Manager ghi được. Nên `erp_ai/agent/server_script_read.py` đọc thẳng bằng
`frappe.get_all` / `frappe.db.get_value`, chỉ các cột đã nêu, không ghi gì. Module nằm ngoài `agent/tools/` như
`system_read.py` (Error Log), vì ADR-005 cấm đọc bỏ qua quyền trong `agent/tools/` (`test_architecture`).

## Che bí mật

`script` qua `redact.redact_secrets` trong `server_script_read.get_script`, trước khi cắt: khóa `sk-…`, `Bearer …`,
`token a:b`, JWT, và giá trị sau tên khóa có `api_key`, `api_secret`, `token`, `secret`, `password`, `passwd`, `pwd`,
`mật khẩu`. Tên khóa và tiền tố giữ lại. Ví dụ:

```
api_key = "sk-a1B2…"                       ->  api_key = "[đã che]"
{"Authorization": "Bearer eyJ0eXAi…"}      ->  {"Authorization": "Bearer [đã che]"}
password = "Mat-khau-2026!"                ->  password = "[đã che]"
```

Mô tả tool nói với model rằng `[đã che]` không phải giá trị thật. Không có lọc theo nội dung script: một phép LIKE trên
thân script sẽ cho dò từng ký tự của bí mật đã che.

## Log

Mỗi lời gọi tool nằm trong cột `tools_called` của dòng `reason` của lượt đó trong ERP AI Log, theo thứ tự gọi (runner
ghi cho mọi tool, cả tool bị từ chối). Tên script đã đọc không được ghi riêng: `actions` chỉ dành cho việc ghi.
