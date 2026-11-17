# Người nhận mặc định (CHG-015) — thiết kế ngắn

Ngày: 2026-11-17. Trạng thái: đã duyệt 2026-11-17 (người dùng: "duyệt, làm đi"). Nối tiếp CHG-011, CHG-014.

## Ý định

Phiếu nào cũng phải có người làm. Phiếu đã có người được giao thì giữ người đó. Phiếu chưa có ai mà bảng tag và Quy tắc
định tuyến không cho được người thì giao cho **một người mặc định**. Cột Người phụ trách của bảng tag vẫn bắt buộc.

## Thiết kế

1. ERP AI Setting thêm `default_assignee` (Link → HD Agent, nhãn "Người nhận mặc định"), ngay sau `routing_rules`.
   Lưu: chặn tài khoản agent ("Người nhận mặc định không được là tài khoản agent").
2. Thứ tự gán khi phiếu chưa có ai (code, không gọi model): bảng tag từ trên xuống → Quy tắc định tuyến (tiền tố,
   mặc định đầu mục, trưởng bộ phận D/E) → **người nhận mặc định**, kể cả khi người ở hai bước trước không dùng được.
   Người mặc định cũng phải là HD Agent đang hoạt động, không phải tài khoản agent; không dùng được thì ghi chú và giữ
   như nay (comment nhờ trưởng nhóm phân công).
3. Phiếu đã có người được giao: không đổi (bot không gán).
4. Task C/D theo người được gán, kể cả người mặc định. Comment: "Đã gán cho {person} (người nhận mặc định)."; hành động
   `assign_owner` ghi `rule` = `default`. Ghi chú của các bước trước vẫn vào nhật ký (giải thích vì sao dùng mặc định).
5. Vẫn cần công tắc "Tự gán người và tạo Task". Tài liệu: mô tả trường, hướng dẫn quản trị.

## Cách đã cân nhắc

Một ô riêng trên form (chọn) — thay vì điền người mặc định cho từng đầu mục trong JSON `routing_rules`: JSON khó sửa và
không phủ D/E khi chưa có bảng bộ phận.
