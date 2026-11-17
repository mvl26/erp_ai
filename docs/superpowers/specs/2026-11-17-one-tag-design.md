# Một phiếu một tag, tag do bảng định nghĩa (CHG-014) — thiết kế ngắn

Ngày: 2026-11-17. Trạng thái: đã duyệt 2026-11-17 (người dùng: "duyệt, làm đi").
Nối tiếp CHG-011 (`2026-11-17-tag-assignee-design.md`); thay ADR-049 Quyết định 2 (1–3 nhãn, nhãn đầu là phân hệ).

## Ý định

Người dùng muốn mỗi phiếu chỉ mang **một tag**, và tag là **nhóm việc chung** do người dùng đặt (`tracecore`, `hr`,
`kế toán`, `chấm công`…), không phải tên phân hệ ERPNext tiếng Anh. Danh sách tag chính là bảng "Gán người theo tag":
mỗi dòng có tên tag và **mô tả**; bot chọn tag theo mô tả và **tự tạo** bản ghi Tag khi gắn lần đầu, người dùng không
phải tạo Tag trước.

## Mục tiêu

- Bảng "Gán người theo tag": cột Tag thành ô gõ tự do (Data); thêm cột **Mô tả** bắt buộc.
- Bước phân loại đưa cho model danh sách "tag: mô tả" lấy từ bảng; model trả tối đa **một** tag; code bỏ tag ngoài bảng
  và viết tag đúng như trong bảng.
- Bỏ nhãn phân hệ, nhãn chủ đề, danh sách nhãn đang dùng và nhãn của phiếu cũ khỏi yêu cầu phân loại.
- Phiếu đã có tag do HD Agent gắn thì bot không gắn tag của mình, và chỉ tag của agent dùng để gán người.
- Gán người giữ nguyên CHG-011 (bảng từ trên xuống).

## Không làm

- Không dọn tag cũ trên phiếu cũ; không xóa Tag cũ (Accounts, Stock…).
- Không ghi Mô tả của dòng vào bản ghi Tag (bot đọc mô tả từ bảng).
- Không gắn nhiều tag, không gắn lại khi bảng đổi.

## Điều không được xảy ra

- Bot gắn tag không có trong bảng.
- Một phiếu mới nhận từ bot hơn một tag.

## Các cách đã cân nhắc

1. **Lần gọi model phân loại có sẵn chọn tag theo mô tả** — chọn: không tốn thêm lời gọi, hiểu cách diễn đạt khác nhau.
2. So từ khóa của mô tả với nội dung phiếu bằng code — bỏ: trượt khi người viết diễn đạt khác.
3. Một lời gọi model riêng để chọn tag — bỏ: tốn thêm mà không hơn.

## Thiết kế

1. **Bảng** `ERP AI Tag Assignee`: `tag` Data bắt buộc; thêm `description` (Small Text, bắt buộc, nhãn "Mô tả") ngay sau
   `tag`. Khi lưu Setting: tên tag chuẩn hóa như nhãn (NFC, gộp khoảng trắng, 2–40 ký tự, chỉ chữ, số, khoảng trắng và
   `& ( ) + . / # -`), sai thì chặn với lý do; vẫn chặn trùng (tag, đầu mục) và tài khoản agent.
2. **Danh sách chọn**: `(tag, mô tả)` theo thứ tự bảng, mỗi tag một lần (không phân biệt hoa thường), mô tả lấy ở dòng
   đầu tiên của tag. Bảng trống thì không có khối tag nào trong yêu cầu (yêu cầu giống hệt khi chưa có nhãn).
3. **Yêu cầu phân loại**: khối "NHÃN PHIẾU" mới ở phần system: khóa `"nhan"` là danh sách tối đa một tag, chọn trong
   DANH SÁCH TAG theo mô tả, viết y hệt tên; không hợp thì `[]`. Danh sách đánh dấu là dữ liệu, mỗi mô tả một dòng, cắt
   độ dài.
4. **Đọc kết quả**: giữ tối đa một nhãn hợp lệ (`LABELS_MAX = 1`); runner chỉ nhận nhãn đó nếu nó là một tag của bảng
   và đổi về cách viết của bảng.
5. **Gắn tag**: phiếu có tag do HD Agent đang hoạt động (không phải bot) gắn → bot không gắn; ngược lại gắn tag đã chọn
   qua `add_tag` của Helpdesk (Tag chưa có thì được tạo).
6. **Gán người**: tag của phiếu = tag của agent nếu có, không thì tag bot vừa chọn; rồi bảng đọc từ trên xuống như CHG-011.
7. **Tài liệu**: mô tả trường, hướng dẫn quản trị mục 5b, ADR-049 Amendment.

## Quyết định của tôi (có thể sửa)

- Model trả nhiều tag thì chỉ xét tag đầu; tag đầu không thuộc bảng thì phiếu không có tag.
- Gắn tag không phụ thuộc công tắc "Tự gán người" (như nhãn hiện nay).
