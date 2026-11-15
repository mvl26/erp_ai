Feature: FEAT-007
Stage: intake
Author-agent: team-leader
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Đối chiếu A4 — Công cụ cấp cho agent

Mốc: `develop` @ `7cc37bb`, đọc ngày 2026-11-14 bằng một lệnh Explore chỉ-đọc. Team-leader đã tự đọc `erp_ai/agent/tools/site_api.py:1-300`, `erp_ai/agent/tools/registry.py:1-112` và `erp_ai/agent/tools/change_guard.py:20-40` để soát A4-3, A4-13, A4-18, A4-20, A4-22. Trạng thái và quy ước đường dẫn: xem đầu `audit-A1.md`. Viết tắt: `T/` = `erp_ai/agent/tools/`.

| Mã | Công cụ tài liệu nêu (mục 4) | Trạng thái | Tương đương trong app | Thiếu hoặc khác |
|---|---|---|---|---|
| A4-1 | `get_ticket` | MET | `get_ticket` (`T/read.py:62-73`), nhóm `read`, L1+ | Không có ở L0 (L0 không có bước lập luận). |
| A4-2 | `search_tickets` (phiếu cũ tương tự) | MET | `search_resolved_tickets` (`T/read.py:103-138`) | "Tương tự" là khớp một chuỗi con 2–100 ký tự, không xếp hạng; chỉ phiếu đã Resolved. |
| A4-3 | `get_doc` (bất kỳ DocType) | DECIDED-DIFFERENTLY | `get_record` cho 6 DocType (`T/read.py:23-25,149-173`), danh sách cấm ở `T/read.py:8-22`; hướng dẫn `docs/HuongDan_TrienKhai_erp-ai.md:1482` | `api_get_record`/`api_list_records` (`T/site_api.py:243-300`) đưa "đọc bất kỳ DocType" trở lại dưới dạng danh sách cấm (mặc định cho phép), không có ADR. Chúng không gọi `can_send_ticket` nên đọc được phiếu của nhóm loại trừ. Mục cấm "Role Permission" không phải DocType của Frappe 15 nên không có tác dụng. |
| A4-4 | `run_report` | PARTIAL | Không có tool báo cáo. Chỉ với tới qua `api_call_method` → `frappe.desk.query_report.run` (`T/site_api.py:222-240`) | Chỉ khi bật Toàn quyền. |
| A4-5 | `read_error_log` | PARTIAL | Error Log không bị cấm trong `site_api`, đọc được bằng `api_list_records`/`api_get_record` | Chỉ khi có nhóm `site_admin` hoặc Toàn quyền, và tài khoản agent phải có System Manager. |
| A4-6 | `search_knowledge_base` | PARTIAL | HD Article chỉ đọc theo đúng tên bằng `get_record` (`T/read.py:24`); tìm theo tiêu đề chỉ qua `api_list_records` | Không tìm được CSKT ở L1, L2. |
| A4-7 | `search_hdsd` | PARTIAL | `prompt_digest` "Trích yếu HDSD", người gõ tay, nối vào prompt lập luận (`erp_ai/agent/prompts.py:332-333`; FEAT-001 spec A-14) | Trích yếu cố định, mặc định rỗng; không có tìm kiếm trên bộ HDSD. |
| A4-8 | `set_ticket_fields` | PARTIAL | `set_classification` (chỉ loại/nhóm/ưu tiên theo ánh xạ, `T/write_ticket.py:68-86`), `set_resolution_hint` (`:89-99`) | Đặt trường tự do và đổi trạng thái bị loại theo quyết định (FEAT-001 `spec.md:23,56`; FEAT-006 AC-9). Nhưng `api_update_record` trên HD Ticket đặt được mọi trường, trái AC-9. |
| A4-9 | `add_comment` | MET | `post_comment` (`T/write_ticket.py:102-112`) | Comment nội bộ, chỉ agent thấy. |
| A4-10 | `reply_to_user` | MISSING | Đã tìm `reply_via_agent`, `reply_to_user`, `Communication`, `sendmail`, `ask_user` trong `erp_ai/`: chỉ có email cảnh báo (`erp_ai/alerts.py:14`) | Người tạo phiếu không bao giờ nhận được trả lời của bot. `ask_user` của hướng dẫn (`:161`) chưa được dựng. |
| A4-11 | `create_task_linked` | MET | `create_task` (`T/write_ticket.py:132-148`), nhóm `task_write`, cần người ra lệnh; runner tự tạo Task cho C/D khi bật gán | — |
| A4-12 | `assign` | DECIDED-DIFFERENTLY | Không phải tool của model; runner gán theo cấu hình (`T/route_ticket.py:77-83`); FEAT-006 AC-9, ADR-021 QĐ 3 | ToDo không bị cấm trong `site_api`, nên model tạo được việc gán qua `api_create_record("ToDo")`, trái AC-9. |
| A4-13 | `create_user` | PARTIAL | `api_create_record(doctype="User")` (`T/site_api.py:140-149`); cấm gán System Manager, Administrator, ERP AI Instructor, ERP AI Agent, Guest, All (`:36,90-121`); từ chối trường mật khẩu | Chỉ là tool chung, không có "tài khoản theo mẫu". Chế độ Toàn quyền bỏ kiểm role (`:113-114`). Tool riêng với tập role cho phép của FEAT-005 (ADR-014/016) chưa dựng. |
| A4-14 | `add_to_team` | PARTIAL | `api_update_record("HD Team", …, {"users": […]})` | Tool chung; thay cả danh sách thành viên. |
| A4-15 | `update_holiday_list` | PARTIAL | Cùng tool, `{"holidays": […]}` | Tool chung; thay cả bảng. |
| A4-16 | `set_item_group` | PARTIAL | Cùng tool, `("Item", mã, {"item_group": X})` | Tool chung. |
| A4-17 | `create_custom_field` | PARTIAL | `api_create_record("Custom Field", …)` | Không lọc thuộc tính: `permlevel`, `fetch_from`, `ignore_user_permissions` đều nhận, trái ADR-014 QĐ 3 và hướng dẫn 4.5. |
| A4-18 | `create_server_script` (chỉ site test) | DECIDED-DIFFERENTLY | Hướng dẫn `:1483`: viết trên production, luôn tắt. Chế độ thường ép `disabled=1` cho Server Script và `enabled=0` cho Webhook (`T/site_api.py:43,76-77`) | Chế độ Toàn quyền bỏ giá trị ép, lưu được Server Script đang bật trên site đang chạy: trái cả tài liệu lẫn hướng dẫn. Client Script không bị ép tắt ở chế độ nào. |
| A4-19 | `data_import` (sau duyệt) | PARTIAL | Không có tool import. `site_admin` tạo được bản ghi Data Import nháp; chạy thì cần `form_start_import`, chỉ với tới qua `api_call_method` | Không có bước duyệt. |
| A4-20 | Cấm tuyệt đối 4 điều | CONTRADICTS | Xem bảng dưới | — |
| A4-21 | Tool là hàm bọc REST, chạy bằng quyền tài khoản agent | DECIDED-DIFFERENTLY | Tool chạy trong tiến trình (hướng dẫn `:1480`); job đổi sang tài khoản agent (`erp_ai/agent/runner.py:125-131`); `agent/tools/*.py` không có `ignore_permissions`, `set_user`, `db.set_value`, `db.sql` | Ngoại lệ: lệnh bench và git sau duyệt chạy bằng user hệ điều hành; `api_call_method` chạy mọi hàm whitelist qua `frappe.call` (`T/site_api.py:227-234`). |

## Bốn điều cấm tuyệt đối (A4-20)

| Điều cấm | Công tắc Toàn quyền tắt | Công tắc Toàn quyền bật |
|---|---|---|
| Xóa bản ghi | Mã chặn: không có tool xóa (`T/site_api.py:387` chỉ thuộc nhóm `site_unrestricted`). Lưu ý: sửa một trường bảng con là thay toàn bộ dòng con. | Làm được: `api_delete_record` trên mọi DocType trừ 4 DocType của app (`T/site_api.py:182-191,62`). |
| Sửa Role Permission | Chặn một phần: Custom DocPerm bị cấm, DocPerm và Has Role bị từ chối vì là bảng con (`T/site_api.py:32,66-67`). Còn hở: quyền của DocType tùy biến, Role Profile, User Permission, DocShare, Role, `permlevel` qua Property Setter. | Làm được: gán được mọi role kể cả System Manager, sửa được Custom DocPerm và chính User của bot (`T/site_api.py:113-114,158`). |
| Chạy migrate/deploy production | Làm được sau một lần bấm của Instructor: `propose_bench_command` cho `migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build --app`, `version` (`T/change_guard.py:33-36`). Không có gì phân biệt site production. Không có `restart`, `update`. Nguồn: FEAT-004 spec A-6. | Như bên trái. |
| Thao tác trên Purchase Invoice / Payment Entry đã submit | Mã chặn: hai DocType bị cấm (`T/read.py:15-16`), sửa chỉ cho bản nháp (`T/site_api.py:166-167`), không có tool submit/hủy. | Làm được: `api_submit_record(action="cancel")` rồi `api_delete_record` (`T/site_api.py:198-210`). |

## Danh mục 21 tool và điều kiện cấp

| Nhóm | Tool | Điều kiện cấp |
|---|---|---|
| `read` | `get_ticket`, `list_comments`, `search_resolved_tickets`, `get_record`, `search_source`, `read_source`, `git_source` | Mức hiệu lực L1–L3 (`T/registry.py:50,74-75`) |
| `ticket_write` | `set_classification`, `set_resolution_hint`, `post_comment` | Như trên (`:51`) |
| `task_write` | `create_task` | Có người ra lệnh (`:52`) |
| `change_propose` | `propose_file_change`, `propose_new_file`, `propose_bench_command` | `code_change_enabled` ∧ L3 ∧ có người ra lệnh (`:53-56`) |
| `site_admin` | `api_list_records`, `api_get_record`, `api_create_record`, `api_update_record` | Như `change_propose` (`:57-61`), hoặc `unrestricted_enabled` ∧ có người ra lệnh ∧ mức ≥ L1 (`:84-89`) |
| `site_unrestricted` | `api_delete_record`, `api_submit_record`, `api_call_method` | `unrestricted_enabled` ∧ có người ra lệnh ∧ mức ≥ L1; không cần L3, không cần `code_change_enabled`, vẫn còn khi vượt ngân sách |

"Có người ra lệnh" = trong 30 comment gần nhất có tác giả mang role ERP AI Instructor hoặc được người khác giao phiếu, nếu không thì xét người tạo phiếu (`erp_ai/agent/authority.py:44-77`). Người đó không cần là người vừa viết `@ai`. L2 có đúng bộ tool của L1.

## Điểm đáng chú ý

- Đường mạnh nhất ở chế độ thường: một đề xuất sửa code trong app được phép (app lõi cũng liệt kê được) rồi một lệnh `migrate` được duyệt, tức là chạy mã tùy ý với đủ quyền trên cơ sở dữ liệu.
- Chốt "luôn đóng" của `api_call_method` (`T/site_api.py:213-219`) là so chuỗi con trên JSON của tham số; đọc mã thì thấy có thể lách bằng ký tự thoát `\u` trong chuỗi JSON lồng. Chưa chạy thử.
- Qua `api_call_method`, nếu tài khoản agent có System Manager thì gọi được `system_console.execute_code` của Frappe, tức là chạy mã trên site. Chưa chạy thử.
