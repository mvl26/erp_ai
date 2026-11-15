# R-2: thêm 6 KPI hằng tuần lên Trang tổng quan Helpdesk, không sửa lõi

Cho: FEAT-007, AC-56, A-15. Trạng thái: hoàn chỉnh, còn các mục UNVERIFIED nêu rõ cách kiểm. Ngày: 2026-11-14.
Không dùng POC, không chạm site `miyano`; mọi điều dưới đây đọc từ mã nguồn đã cài.

## Phiên bản đang dùng
- Helpdesk 15.1.0: `apps/helpdesk/helpdesk/__init__.py:1`.
- Frappe 15.126.1: `apps/frappe/frappe/__init__.py:54`.
- Thứ tự app trên bench: `sites/apps.txt` (erp_ai đứng trước helpdesk).

## Trả lời ngắn
KHÔNG. Helpdesk 15.1.0 không có điểm mở rộng cho thẻ số hoặc biểu đồ của app khác trên Trang tổng quan. Danh sách thẻ và biểu đồ được viết cứng ở cả hai phía:
- Màn `/dashboard` (thẻ số, biểu đồ, bộ lọc kỳ): `desk/src/pages/dashboard/Dashboard.vue:400-406` gọi `helpdesk.api.dashboard.get_dashboard_data`; năm thẻ cố định ở `helpdesk/api/dashboard.py:155-167`; biểu đồ cố định ở `dashboard.py:277-281`; các nhánh `dashboard_type` cố định ở `dashboard.py:64-75`.
- Màn `/home` (widget kéo thả): `helpdesk/api/agent_home/agent_home.py:40-48` chỉ gọi hàm `get_<chart>` có sẵn trong chính module `agent_home`; `desk/src/pages/home/components/ChartItem.vue:3-26` chỉ vẽ 7 tên `chart` có sẵn; menu "New" (`Home.vue:289`) cũng viết cứng. Tên widget lạ trong `HD Field Layout` ra `data=None` và không được vẽ.
- `helpdesk/hooks.py` không có mục nào cho dashboard (đã tìm `dashboard`, `extend`).
- Ghi chú quyền: `is_manager` của giao diện chỉ là role `Agent Manager` (`helpdesk/api/auth.py:49`), không tính System Manager; phía máy chủ cũng vậy (`dashboard.py:22-24`): người không phải `Agent Manager` chỉ xem dữ liệu của chính mình. COO và Instructor cần role `Agent Manager` mới xem cả đội ở màn này.

Cách duy nhất không sửa file của Helpdesk là ghi đè API bằng hook của Frappe (phương án 2). Đó là vá API nội bộ, không phải điểm mở rộng.

## Cơ chế chuẩn của Frappe 15.126.1 và ai xem được
| Cơ chế (app chuyển bằng file) | Ai thấy | Nguồn |
|---|---|---|
| Script Report (`<module>/report/<tên>/<tên>.json` + `.py`) | Bảng `roles` trong JSON báo cáo (rỗng = mọi người), cộng quyền `report` trên `ref_doctype`. Không có ngoại lệ cho System Manager, phải liệt kê trong `roles` (như `erp_ai_accuracy.json`) | `core/doctype/report/report.py:120-137`, `desk/query_report.py:~51,283`; `erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.json` |
| Number Card (JSON, `is_standard`, `module`) | KHÔNG có bảng role. System Manager luôn thấy. Người khác: thẻ `Custom` hoặc `Document Type` chỉ thấy khi `document_type` của thẻ nằm trong các DocType họ đọc được; thẻ `Custom` để trống `document_type` thì chỉ System Manager thấy. Có thêm lọc theo module | `desk/doctype/number_card/number_card.py:84-124` |
| Number Card kiểu `Custom` | Gọi phương thức Python `@frappe.whitelist()`, trả `{value, fieldtype, route_options, route}`: một con số. Phần trăm so kỳ trước chỉ có với thẻ `Document Type` | `public/js/frappe/widgets/number_card_widget.js:128-134,189-196,282` |
| Dashboard Chart (JSON; kiểu `Custom` dùng Dashboard Chart Source) | Có bảng `roles`: điền thì ai trùng role đều thấy; trống thì theo quyền đọc DocType hoặc báo cáo. System Manager luôn thấy | `desk/doctype/dashboard_chart/dashboard_chart.py:26-83` |
| Dashboard (JSON, màn `/app/dashboard-view/<tên>`) | KHÔNG có bảng role; chỉ lọc theo module; thẻ và biểu đồ bên trong lọc lại theo quyền riêng | `desk/doctype/dashboard/dashboard.py:70-106` |
| Workspace (JSON trong `<module>/workspace/`) | Bảng `roles`; rỗng thì mọi người dùng desk thấy; thẻ số và biểu đồ bên trong lọc lại theo quyền riêng | `desk/desktop.py:78-93,273-284,362-374` |
| Trang `www/` của app (hiện `erp_ai/www/` rỗng) | Không có bảng role; phải tự kiểm trong `get_context`, ví dụ `frappe.only_for([...])` (báo `PermissionError` nếu thiếu role; bỏ qua với Administrator và khi chạy test) | `frappe/__init__.py:949-961` |

Ba loại người dùng trong câu hỏi:
- System Manager: thấy mọi cơ chế trên; riêng Script Report cần có trong `roles` của báo cáo.
- Role `Agent` của Helpdesk (tên thật là `Agent`, không phải "Helpdesk Agent"): có `read` và `report` trên HD Ticket (`helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.json:539-541`). Thẻ `Custom` với `document_type = "HD Ticket"` hiện cho Agent. Role mới mặc định `desk_access=1` (`frappe/core/doctype/role/role.json:37-41`; Helpdesk chỉ tắt cho `HD Customer*`, `helpdesk/setup/install.py:225`); giá trị thật của role `Agent` trên site chưa kiểm: UNVERIFIED. Kiểm: đăng nhập tài khoản chỉ có role `Agent`, mở `/app`; đúng là vào được desk, sai là bị chuyển về `/helpdesk`.
- Role riêng (ví dụ `ERP AI Instructor`, `erp_ai/constants.py:3`): dùng bảng `roles` của Report, Dashboard Chart, Workspace. Number Card và Dashboard không có bảng role.

## Phương án (xếp hạng, tối đa 3)

### 1. Script Report của app (khuyến nghị cho AC-56)
- Cần: báo cáo `ERP AI KPI Weekly` ở `erp_ai/erp_ai_agent/report/` theo mẫu `erp_ai_accuracy`; sáu hàng KPI, cột: tuần này, tuần trước, mục tiêu GĐ2, mục tiêu GĐ4; `roles` = role của COO, `ERP AI Instructor`, System Manager; `ref_doctype` mà các role đó có quyền `report`.
- Ưu: đúng hình dạng AC-56 (6 KPI cùng một màn, mỗi KPI có tuần này, tuần trước, hai mục tiêu); đã có tiền lệ trong app; không phụ thuộc cấu trúc nội bộ Helpdesk; quyền kiểm được bằng test.
- Giới hạn: không nằm trong Trang tổng quan Helpdesk (mở ở `/app/query-report/...`, cần desk access); nếu Instructor không có quyền `report` trên `ref_doctype` thì bị chặn ở `query_report.py:283`.
- UNVERIFIED, cần trình duyệt: đăng nhập tài khoản có `ERP AI Instructor` nhưng không có System Manager, mở `/app/query-report/ERP AI KPI Weekly`; đúng là thấy bảng, sai là "Must have report permission". Tài khoản chỉ có role `Agent` phải bị từ chối.

### 2. Ghi đè `helpdesk.api.dashboard.get_dashboard_data` bằng `override_whitelisted_methods` (đưa thẻ lên đúng Trang tổng quan)
- Cần: trong `erp_ai/hooks.py` thêm `override_whitelisted_methods = {"helpdesk.api.dashboard.get_dashboard_data": "erp_ai.<module>.get_dashboard_data"}`; hàm mới gọi bản gốc, khi `dashboard_type == "number_card"` thì thêm 6 dict `{title, value, delta, suffix, tooltip}` (hình dạng ở `dashboard.py:155-188`). Cơ chế: `frappe/__init__.py:2551-2555`, dùng ở `frappe/handler.py:67`; ghi đè cuối cùng thắng.
- Ưu: không sửa file nào của Helpdesk; thẻ hiện ở `/dashboard`.
- Giới hạn: vá API nội bộ, hình dạng dữ liệu có thể đổi khi nâng Helpdesk; hai app cùng ghi đè một hàm thì chỉ app cuối thắng; thẻ theo bộ lọc kỳ của trang (mặc định 30 ngày) chứ không cố định "tuần này, tuần trước"; chỉ có `value`, `delta`, `tooltip` nên mục tiêu GĐ2 và GĐ4 phải nhét vào tooltip; hàm ghi đè phải giữ kiểm quyền của bản gốc (`@agent_only` và kiểm `Agent Manager`, `dashboard.py:22-24`); lưới `lg:grid-cols-5` thành 11 thẻ; chỉ `/dashboard`, không phải `/home`.
- UNVERIFIED, cần trình duyệt: sau khi ghi đè, mở `/helpdesk/dashboard` bằng tài khoản `Agent Manager`; đúng là 6 thẻ mới hiện, sai là không hiện hoặc giao diện vỡ.
- Hệ quả cho A-15: nếu architect coi "vá API qua hook" là "không sửa lõi", AC-56 dùng được phương án này; nếu coi là sửa lõi, A-15 chuyển sang phương án 1.

### 3. Workspace của app với Number Card (và Dashboard Chart)
- Cần: Workspace `ERP AI KPI` (`module` của app, `public=1`, `roles` điền), sáu Number Card `Custom` có `document_type="HD Ticket"` (Agent thấy được; để trống thì chỉ System Manager thấy) kèm phương thức whitelisted; hoặc Dashboard Chart kiểu `Custom`.
- Ưu: file thuần, không động Helpdesk, quen thuộc cho quản trị.
- Giới hạn: Number Card không có role nên người có role riêng (Instructor) chỉ thấy thẻ khi có quyền đọc DocType của thẻ; mỗi thẻ chỉ một con số, nên "tuần này, tuần trước, hai mục tiêu" cần 12 thẻ hoặc nhét vào nhãn; cũng ở `/app`, không phải Trang tổng quan Helpdesk; phương thức whitelisted phải tự kiểm role vì mọi người đăng nhập đều gọi được.

Loại: trang `www/` (không có kiểm quyền sẵn, phải tự viết giao diện và bảo mật; không hơn phương án 1).

## Sources
- Mã nguồn đã cài, đọc ngày 2026-11-14: các đường dẫn trong bảng và phần trả lời ở trên.
- Frappe Framework docs, Hooks, mục `override_whitelisted_methods`: https://docs.frappe.io/framework/user/en/python-api/hooks (truy cập 2026-11-14). Dùng: phương thức ghi đè phải cùng chữ ký với bản gốc; khi nhiều app ghi đè, giá trị cuối trong danh sách thắng (khớp `frappe/__init__.py:2551-2555`).
- `https://docs.frappe.io/framework/user/en/desk/scripting/script-report` trả 404 ngày 2026-11-14; phần Script Report và `roles` chỉ dựa vào mã đã cài và `erp_ai_accuracy.json`, chưa có trang tài liệu chính thức: UNVERIFIED về mặt tài liệu, đã khớp mã.
