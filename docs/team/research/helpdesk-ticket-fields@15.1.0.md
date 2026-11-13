# Helpdesk @ 15.1.0 — hiện/ẩn trường HD Ticket (cache)

Ngày: 2026-11-11 · Phiên bản: helpdesk v15.1.0 (commit a1858964) trên frappe 15.126.1 · Nguồn gốc: FEAT-001 research Q2-H-2.

- HD Ticket Template (`Default`) vẫn quyết định tab chi tiết của agent: các dòng template đang hiện, rồi tới các trường lõi priority/ticket_type/customer/agent_group (`helpdesk/ticket_fields.py`). "Will be deprecated" chỉ là cảnh báo; HD Field Layout chỉ có kiểu "Landing Page".
- Dòng template có `visible_to` = Everyone/Agents, thay cho "Hide from customer" cũ. Chỉ ẩn trên trang Helpdesk, không ẩn ở API.
- Permlevel 7 = khách đọc được; 8 = chỉ agent (System Manager, Agent, Agent Manager đọc/ghi). Chỉ permlevel mới ẩn được ở API. Level 8 không tự cấp cho role tự tạo.
- Lưu template báo lỗi nếu trường permlevel ≥ 8 nằm ở dòng Visible to = Everyone.
- Kết luận cho trường nội bộ: custom field permlevel 8 + dòng template `Default` với Visible to = Agents.

## Sources
- https://docs.frappe.io/helpdesk/customization/perm-levels-in-helpdesk (truy cập 2026-11-11)
