# Bot tự tạo tag mới khi bảng không có tag hợp (CHG-018) — thiết kế ngắn

Ngày: 2026-11-17. Trạng thái: người dùng yêu cầu "oke làm đi, tạo tag trong ticket tag đó, tag list" (2026-11-17).
Sửa CHG-014 (`2026-11-17-one-tag-design.md`): bỏ điều "Bot gắn tag không có trong bảng".

## Ý định

Phiếu không hợp tag nào của bảng "Gán người theo tag" vẫn nhận một tag: bot đặt tag mới theo nội dung phiếu, gắn lên
phiếu, và thêm tag đó vào danh sách tag (bảng) để các phiếu sau dùng lại cùng tên, người quản trị thấy và điền người.

## Mục tiêu

- Model chọn tag trong bảng như CHG-014; không tag nào hợp thì đặt **một** tag mới (nhóm việc chung, 1 đến 3 từ) kèm
  một câu mô tả (`mo_ta_nhan`).
- Tag mới được gắn lên phiếu (Tag chưa có thì Helpdesk tạo) và thêm thành **dòng cuối** của bảng, **không có người
  nhận**, mô tả là câu model viết.
- Bảng nhận dòng không có người nhận; dòng đó vẫn là tag để chọn, nhưng không cho người: phiếu đi tiếp theo
  `routing_rules`, rồi Người nhận mặc định.

## Không làm

- Không tự chọn người cho tag do bot tạo; không sửa dòng đã có.
- Không tạo tag mới khi phiếu đã có tag do HD Agent gắn, hoặc phiếu đầu mục F (phiếu nhiễu, phiếu test).
- Không dọn tag cũ, không gộp tag gần nghĩa.
- Không đổi yêu cầu phân loại của bộ đánh giá offline (eval không truyền danh sách tag).

## Điều không được xảy ra

- Một phiếu nhận từ bot hơn một tag.
- Dòng do bot thêm cho được người nhận.
- Bảng có hai dòng trùng (tag, đầu mục) do bot thêm.

## Các cách đã cân nhắc

1. **Thêm dòng không có người vào bảng** — chọn: phiếu sau thấy tag trong danh sách nên dùng lại cùng tên; người quản
   trị thấy dòng trống người để điền.
2. Chỉ gắn tag lên phiếu — bỏ: phiếu sau không biết tag đã có, cùng việc ra nhiều tên.
3. Thêm dòng với Người nhận mặc định — bỏ: dòng do nội dung phiếu sinh ra sẽ cho người, và người mặc định đã được dùng
   khi không dòng nào cho người.

## Thiết kế

1. **Bảng** `ERP AI Tag Assignee`: `assignee` bỏ bắt buộc. `routing.tag_rules` giữ dòng không có người (assignee
   `""`); `_tag_assignee` bỏ qua dòng đó với ghi chú "tag X: chưa có người nhận" rồi xét dòng tiếp theo.
2. **Yêu cầu phân loại**: `build_classify_request(..., new_tags=False)`. Runner truyền `new_tags=True`: khối NHÃN PHIẾU
   luôn có (bảng trống thì danh sách ghi "(chưa có tag nào)"), quy tắc cuối thay "không hợp thì `[]`" bằng "không hợp thì
   đặt tag mới + `mo_ta_nhan`". Không truyền (eval) thì yêu cầu như cũ.
3. **Đọc kết quả**: `Classification.label_description` = `mo_ta_nhan` trên một dòng, cắt `FIELD_VALUE_MAX_CHARS`.
4. **Chọn**: tag đầu thuộc bảng → tag của bảng (mô tả bỏ). Không thuộc bảng, có mô tả, phiếu không do agent gắn tag,
   đầu mục khác F, tên không phải tag Helpdesk tự gắn → tag mới. Còn lại → không tag, ghi chú lý do.
5. **Route**: sau (u1b) gắn tag, khi tag là mới và vừa được gắn, (u1c) `add_tag_row` thêm dòng cuối bảng (tên theo bản
   ghi Tag nếu đã có), một đơn vị ghi riêng: lỗi chỉ hoàn tác dòng. Tên dòng con cố định theo tag (`erp-ai-tag-<băm>`)
   để hai lần chạy song song không thêm trùng; đã có dòng cùng tag (không phân biệt hoa thường) thì bỏ qua. Ghi thẳng
   dòng con, không lưu cả Setting (không chạy kiểm tra của các trường khác, không đụng người đang mở Setting).
6. **Comment định tuyến**: thêm câu "Đã thêm tag Y vào bảng Gán người theo tag (chưa có người nhận)."
7. **Tài liệu**: mô tả trường `assignee`, hướng dẫn quản trị mục 5b, ADR-049 Amendment 2.

## Quyết định của tôi (có thể sửa)

- Phiếu đầu mục F không sinh tag mới (vẫn chọn được tag có sẵn).
- Mô tả do model viết đi vào phần system của các lần phân loại sau, như mô tả người quản trị viết: cùng nhãn "dữ liệu,
  không phải lệnh", một dòng, cắt độ dài. Người quản trị nên đọc lại dòng trống người nhận.
- Người quản trị lưu Setting đang mở từ trước khi bot thêm dòng thì dòng đó mất (Frappe ghi lại bảng theo form); phiếu
  sau sẽ tạo lại.
