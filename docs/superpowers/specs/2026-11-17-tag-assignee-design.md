# Gán người theo tag (CHG-011) — thiết kế ngắn

Ngày: 2026-11-17. Trạng thái: chờ duyệt.

## Ý định

Trưởng nhóm chia việc theo nhóm công việc hay loại phiếu: phiếu kế toán giao Hiếu, phiếu tracecore giao e2e, v.v.
Người dùng muốn ghi cách chia này **một lần** trong ERP AI Setting để bot tự áp cho mọi phiếu về sau: gán người
phụ trách phiếu và giao Task C/D cho người đó, thay cho việc trưởng nhóm phân công tay từng phiếu.

Hiện nay bot chọn người bằng code từ ô JSON "Quy tắc định tuyến", chỉ theo đầu mục A–F, tiền tố tiêu đề và bộ phận
(D/E); không nhìn tag ([routing.py](../../../erp_ai/agent/routing.py) `_assignee`).

## Mục tiêu

- ERP AI Setting có bảng **"Gán người theo tag"**: mỗi dòng là một tag, một người phụ trách, đầu mục tùy chọn.
- Khi định tuyến, bot chọn người theo bảng này trước; không dòng nào khớp thì dùng cấu hình cũ như nay.
- Bot biết các tag trong bảng để gắn chúng lên phiếu khi hợp nghĩa.

## Không làm

- Không thay ô JSON "Quy tắc định tuyến": nó vẫn là chỗ khai báo người mặc định theo đầu mục, tiền tố tiêu đề,
  bộ phận, ưu tiên và SLA.
- AI không chọn người. Người nhận vẫn do code chọn.
- Không chia đều hay xoay vòng giữa nhiều người.
- Không đổi người trên phiếu đã có người được gán; không định tuyến lại phiếu đã định tuyến.
- Nhắc cập nhật bảng khi người đổi người được gán nhiều lần cho cùng một tag: để sau.

## Điều không được xảy ra

- Nội dung phiếu (người viết phiếu ghi "giao cho X") làm đổi người nhận.
- Bảng sai làm bot gán cho tài khoản bot hoặc cho người không phải HD Agent đang hoạt động.

## Các cách đã cân nhắc

1. **Bảng "tag → người" trên form, code chọn người.** Đã chọn. Đúng cách trưởng nhóm đang chia việc ("tag nào → ai"),
   nhìn bảng là biết phiếu nào về ai, cùng một phiếu luôn ra cùng một người, nội dung phiếu không lái được.
2. **Ô "Hướng dẫn phân việc" viết bằng lời, AI đọc và chọn người.** Bỏ: AI có thể gán sai mà khó thấy vì sao,
   nội dung phiếu lái được, và đổi nguyên tắc "AI không chọn người".

Người dùng chọn cách 1 (2026-11-17).

## Thiết kế

1. **Bảng con mới `ERP AI Tag Assignee`** (istable, module ERP AI Agent), gắn vào ERP AI Setting bằng trường Table
   `tag_assignees`, nhãn "Gán người theo tag", trong mục "Phân loại và nhóm loại trừ", ngay trước "Quy tắc định tuyến".
   Cột:
   - **Tag**: Link → Tag, bắt buộc.
   - **Người phụ trách**: Link → HD Agent (tên bản ghi HD Agent là user id), bắt buộc.
   - **Đầu mục**: Select trống/A/B/C/D/E/F. Trống = mọi đầu mục.

   Khi lưu form: chặn hai dòng trùng (tag không phân biệt hoa thường, cùng đầu mục); chặn tài khoản bot làm người
   phụ trách. Mô tả trường nói rõ: dòng có đầu mục cụ thể thắng dòng để trống; bảng đi trước "Quy tắc định tuyến".

2. **Chọn người** (thay `_assignee` trong `routing.py`, vẫn là code, không gọi model):
   - Danh sách tag của phiếu = tag người đã gắn trên phiếu lúc định tuyến (theo thứ tự trên phiếu), rồi các nhãn AI
     vừa đặt (nhãn quan trọng nhất trước), bỏ trùng không phân biệt hoa thường.
   - Duyệt từng tag theo thứ tự đó. Với mỗi tag, dòng có đúng đầu mục của phiếu thắng dòng để trống. Dòng khớp đầu
     tiên có người là HD Agent đang hoạt động và không phải tài khoản bot → chọn người đó.
   - Dòng khớp mà người không hợp lệ → ghi một note vào log rồi xét tiếp tag sau.
   - Không dòng nào cho được người → cấu hình cũ y như nay (tiền tố tiêu đề, mặc định đầu mục, trưởng bộ phận D/E).

3. **Bot biết tag trong bảng:** mọi tag trong bảng luôn có trong "Nhãn đang dùng" gửi ở bước phân loại
   (`labels.classify_inputs`), kèm Mô tả của Tag, kể cả tag chưa phiếu nào mang. Người dùng viết Mô tả cho Tag (ví
   dụ Tag "tracecore": "phiếu về phần mềm Tracecore") để AI biết khi nào gắn tag đó.

4. **Báo lại:** comment định tuyến ghi "Đã gán cho {person} (theo tag {tag})." khi người được chọn từ bảng; dòng hành
   động trong ERP AI Log ghi quy tắc `tag:<tag>`.

5. **Giữ nguyên:** công tắc "Tự gán người và tạo Task" phải bật; phiếu đã có người được gán (kể cả do Assignment Rule)
   thì bot không gán; Task C/D giao cho người được gán; mỗi phiếu định tuyến một lần; bài học khi người đổi người
   được gán vẫn ghi như cũ.

## Quyết định của tôi (người dùng chưa nói, có thể sửa)

- Bảng đi **trước** tiền tố tiêu đề và mặc định đầu mục, áp cho cả D/E (thắng trưởng bộ phận) khi cột Đầu mục để trống.
  Muốn D/E giữ trưởng bộ phận thì ghi Đầu mục cụ thể cho dòng.
- Tag người đã gắn sẵn trên phiếu xét **trước** nhãn AI đặt.
- Người trong bảng không còn là agent hoạt động thì bot bỏ qua dòng đó (có note), không dừng định tuyến.

## Để người làm quyết

- Tên test, cách chia commit, giới hạn số tag thêm vào "Nhãn đang dùng" (tag trong bảng không bị cắt bởi giới hạn 40).
- Theo `CLAUDE.md`: test hỏng trước; chạy test dưới khóa site `miyano`; cần `migrate` cho DocType và trường mới;
  prod cần người duyệt.
