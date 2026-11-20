# Nút "Cho bot làm" và "Xác nhận xong, đóng phiếu" rõ ràng (CHG-019) — thiết kế

Ngày: 2026-11-20. Trạng thái: người dùng đồng ý 5 điểm sửa và chọn hướng A ("đồng ý, làm đi theo hướng A",
2026-11-20). Sửa ADR-050 (nút duyệt hướng xử lý), CHG-010 (câu mời duyệt), CHG-017 (nút duyệt kết quả).

## Ý định

Trong ngăn "Trao đổi với bot", người dùng phải biết ngay nút nào làm gì, ai bấm được, và nút nằm đúng chỗ đang đọc.
Hiện nay (xem 4 phiếu trên `miyano`, 2026-11-20):

- Ba nút khác nghĩa cùng chữ "Duyệt": "Duyệt hướng xử lý" (bot bắt đầu làm), "Duyệt" xanh lá (phiếu sang Resolved),
  "Duyệt" trên thẻ đề xuất (áp dụng thay đổi code).
- Nút gắn dưới hướng xử lý gần nhất, có thể cách xa tin cuối. Phiếu 43406: nút đóng phiếu dưới tin 13:48, tin cuối 14:04
  của bot nói "Bot chưa đóng phiếu".
- Phiếu 43454 được đóng bằng nút trong khi 4 Task bot tạo cho phiếu còn Open.
- Mọi người thấy nút, kể cả người không có quyền; bấm thì nhận "hãy thử lại" thay vì lý do.
- Nút "Duyệt hướng xử lý" chỉ hiện khi bot viết đúng nguyên văn một câu mẫu; không phiếu nào trên `miyano` có nút.

## Mục tiêu

1. Đổi tên: "Cho bot làm" (xanh dương), "Xác nhận xong, đóng phiếu" (xanh lá), "Chưa đạt" (viền đỏ). Thẻ đề xuất
   giữ "Duyệt / Từ chối".
2. Cả hai loại nút chỉ nằm dưới **tin mới nhất** của luồng, và chỉ khi tin đó là của bot.
3. Không có nút đóng phiếu khi phiếu còn Task đang mở hoặc đề xuất chưa xong; thay vào đó một dòng nêu còn gì.
4. Nút chỉ hiện cho người bấm được; người khác thấy một dòng nói ai bấm được. Bị từ chối thì thấy đúng lý do.
5. Hướng A: bot khai các bước chờ duyệt bằng tool; hệ thống lưu các bước trên tin và gắn nút. Không dò chữ nữa.

## Không làm

- Không đổi thẻ đề xuất sửa code / console (nút, luồng duyệt, quyền).
- Không đổi ai có quyền ra lệnh (`authority.is_instruction`) hay ai được xác nhận kết quả (`lifecycle.result_confirmer`).
- Không đổi cách đóng phiếu ngoài ngăn (người vẫn đổi status trên Helpdesk như cũ).
- Không mở lại phiếu 43454 (việc riêng, chờ người dùng quyết).
- Không tạo nút cho tin cũ: tin cũ có câu mẫu không có nút nữa.

## Điều không được xảy ra

- Người không có quyền ra lệnh bấm được "Cho bot làm" và bot chạy theo.
- Bấm "Cho bot làm" gửi đi các bước khác với các bước đang hiện dưới tin.
- Phiếu sang Resolved qua ngăn trong khi còn Task đang mở hoặc đề xuất chưa xong (server chặn, không chỉ ẩn nút).
- Nút nằm dưới một tin không phải tin mới nhất.
- Tin "Chưa đạt" / "Đã xác nhận" gửi trước bản này không còn được nhận ra (hệ thống phải nhận cả chữ cũ).

## Các cách đã cân nhắc

1. **A1 — tham số `approval_steps` của `post_comment`** — chọn. Các bước đi cùng đúng tin bot đăng, một lời gọi. Trong
   lượt chạy hướng xử lý, tin `de_xuat` được giữ làm nhận định thì các bước được giữ cùng và lưu trên tin hướng xử lý.
2. A2 — tool riêng `offer_steps` gọi trong lượt — bỏ: thêm một lời gọi, và phải đoán các bước thuộc tin nào (tin hướng
   xử lý đăng cuối lượt, tin trả lời đăng giữa lượt).
3. B — nới điều kiện dò câu mẫu — bỏ (người dùng chọn A): model viết lệch một chữ là mất nút.

## Thiết kế

### 1. Bot khai các bước

- `post_comment` có thêm `approval_steps`: không bắt buộc, mảng 1–8 chuỗi, mỗi chuỗi 1–200 ký tự, một dòng. Mô tả
  tool: các bước bot sẽ làm bằng tool khi người có quyền ra lệnh bấm "Cho bot làm"; việc người làm tay không ghi vào đây.
- Từ chối (không đăng gì, lý do rõ): `approval_steps` với `kind` khác `de_xuat`; lượt dưới ngưỡng tin cậy; chuỗi rỗng,
  quá dài, có xuống dòng; hơn 8 bước.
- Lượt hướng xử lý (`collecting`): `hold_analysis` giữ cả các bước; lần giữ sau thay lần trước (như nhận định).
  `post_guidance` truyền các bước vào tin hướng xử lý.
- Lượt sau (đã có hướng xử lý): `_post_message` truyền các bước vào tin trả lời.
- Prompt (`OWN_DECISIONS_BLOCK`): thay quy tắc câu mẫu bằng "còn bước bot làm được bằng tool (kể cả tool chỉ mở khi có
  người ra lệnh) mà chưa làm trong lượt này thì ghi từng bước vào `approval_steps`; không viết câu mời bấm nút, không
  nhắc chữ duyệt trong nội dung. Chỉ còn việc người làm tay thì không dùng `approval_steps`."
- Bot phải biết bấm nút sẽ mở thêm tool nào: lượt không có người ra lệnh, không phải lượt chỉ hỏi, mà
  `_instructor_tools` (BUG-010) khác rỗng thì phần việc cần làm có thêm một dòng "Người có quyền bấm Cho bot làm thì lượt
  sau có thêm tool: …; bước cần các tool này ghi vào `approval_steps`." Áp cho mọi trigger (cả lượt tạo phiếu), không chỉ
  lượt `@ai`. Lượt `@ai` của người không có quyền vẫn có thêm câu BUG-010 như cũ.
- Bỏ `APPROVE_GUIDANCE_OFFER` và mọi chỗ dò nó.

### 2. Lưu trên tin

- `ERP AI Message` thêm hai trường chỉ đọc, mô tả tiếng Việt như các trường khác. Cần `bench migrate`; không cần patch
  dữ liệu.
  - `approval_steps` (Long Text, JSON mảng chuỗi).
  - `reply_kind` (Select: trống, `guidance`, `de_xuat`, `hoi`): loại tin trả lời của bot. Hướng xử lý ghi `guidance`;
    `post_comment` ghi `de_xuat` hoặc `hoi` theo `kind`; thông báo và tin định tuyến của hệ thống, tin của người để
    trống. Tin cũ để trống, trừ hướng xử lý vẫn nhận ra bằng dấu đầu tin như nay.
- `messages.add_message(..., approval_steps=None, reply_kind=None)` là chỗ ghi duy nhất. Controller từ chối tin có hai
  trường này mà `owner` không phải tài khoản agent.
- `messages.history` (khối conversation gửi model): tin có các bước thì nội dung kèm thêm dòng "Các bước chờ duyệt:" và
  từng bước, để lượt sau model biết mình đã đề nghị gì.

### 3. Nút nào, dưới tin nào

`messages.thread(ticket)` trả mỗi tin thêm `approval_steps` (mảng, rỗng nếu không có) và tính trên **tin cuối** của
luồng, khi tin đó của bot (`is_bot`):

- Tin cuối có các bước → `actions = "order"` (nút "Cho bot làm"). Các tin cũ hơn vẫn hiện danh sách các bước của
  mình, không có nút.
- Tin cuối không có các bước, là **tin trả lời** của bot (hướng xử lý hoặc tin `de_xuat`; không phải câu hỏi `hoi`,
  không phải thông báo hệ thống như hết lượt, lỗi lượt chạy, tin định tuyến), bot đã có kết quả trên phiếu (mục "Đã làm"
  của hướng xử lý có dòng nào đó, **hoặc** một lời gọi ghi thành công của `LINKED_WRITE_TOOLS` trong `ERP AI Log` của
  phiếu, **hoặc** một đề xuất của phiếu ở `Đã áp dụng`), và các luật CHG-017 còn lại vẫn đúng (không ngay sau một "Chưa
  đạt" chưa ai trả lời, `lifecycle.result_refusal` không chặn). Bỏ điều "hướng xử lý không có mục Chờ duyệt" của
  CHG-017: tình trạng đề xuất được xét trực tiếp ở dưới, nên phiếu sửa bằng đề xuất đóng được sau khi đề xuất áp dụng.
  - còn việc dở → `actions = "blocked"` và `blockers`: Task có `ai_ticket` = phiếu, status khác `Completed`,
    `Cancelled`, `Template`; đề xuất `ERP AI Change Proposal` của phiếu có `change_status` là `Chờ duyệt`, `Đã duyệt`,
    `Đang áp dụng` hoặc `Đang hoàn tác`. Mỗi mục `{label, url}` (Task kèm đường dẫn form, chỉ mục người xem đọc được;
    đề xuất chỉ đếm, vì thẻ của nó đã có trong luồng).
  - không còn gì → `actions = "confirm"` kèm `result_links` như CHG-017.
- Còn lại → không nút.

Cờ cũ `approvable`, `result_confirmable` bỏ; một trường `actions` trên tin cuối thay cho cả hai (chỉ một loại hiện).

### 4. Ai thấy nút

`get_panel_data` trả thêm `viewer = {"can_order": authority.is_instruction(user, ticket),
"can_confirm": lifecycle.result_confirmer(user, ticket)}`.

- `order` + `can_order` → nút "Cho bot làm". `order` không có quyền → dòng "Người có vai trò ERP AI Instructor hoặc
  người được giao phiếu bấm Cho bot làm."
- `confirm` + `can_confirm` → "Xác nhận xong, đóng phiếu" và "Chưa đạt". Không có quyền → dòng "Người tạo phiếu hoặc
  người có vai trò ERP AI Instructor xác nhận đóng phiếu."
- `blocked` → mọi người thấy dòng "Chưa đóng phiếu được: còn N Task đang mở, M đề xuất chưa xong." và liên kết Task.

### 5. Bấm nút

- **"Cho bot làm"** gọi method mới `ticket_panel.approve_steps(ticket, message)` (POST), không qua ô gửi:
  cổng ngăn như các method khác; `is_instruction` sai → PermissionError có lý do; `message` không phải tin cuối của
  phiếu, không phải của bot, hoặc không có các bước → ValidationError "Bot đã có tin mới hơn hoặc tin này không còn chờ
  duyệt." Đúng thì `add_message(ticket, text, trusted=True)` của người bấm, `text` = `APPROVE_STEPS_TEXT` ("Cho bot làm
  các bước sau, đúng phạm vi đã nêu:") rồi từng bước trên một dòng "- …", đúng như đã lưu. Handler tin nhắn chạy bot như
  mọi tin; runner kiểm quyền người bấm như cũ (BUG-009).
- Prompt: tin bắt đầu bằng `APPROVE_STEPS_TEXT` của người có role "chỉ thị" là lệnh làm đúng các bước liệt kê trong tin,
  bằng tool được cấp; xong thì liệt kê bản ghi đã tạo, sửa, xóa, hủy. Từ người không có role "chỉ thị" thì không làm
  gì, chỉ nói cần người có quyền bấm. Quy tắc cũ về `APPROVE_GUIDANCE_TEXT` bỏ.
- **"Xác nhận xong, đóng phiếu" / "Chưa đạt"**: `decide_result` như CHG-017, thêm: tin cuối phải có `actions =
  "confirm"` (cùng hàm của mục 3); còn việc dở → ValidationError nêu đúng số Task và đề xuất.
- Panel hiện **lời của server** khi bị từ chối (PermissionError, ValidationError); lỗi mạng mới hiện câu "thử lại".

### 6. Chữ cố định

- `RESULT_APPROVED_TEXT` = "Đã xác nhận xong: phiếu chuyển sang Resolved.";
  `RESULT_REJECTED_TEXT` = "Chưa đạt: bot hỏi tôi chưa đạt ở điểm nào."
- Chữ cũ ("Đã duyệt kết quả: …", "Không duyệt kết quả: …") vẫn được nhận ra ở handler (không gọi bot), prompt (lượt
  hỏi "chưa đạt ở điểm nào") và luật "ngay sau Chưa đạt": mỗi chữ thành một bộ (mới, cũ).
- Câu giải thích đầu ngăn (`TEXT_BOT_GUIDANCE`) viết lại theo tên nút mới.

### 7. Tài liệu

README (đoạn về ngăn trao đổi), CHANGELOG (Changed, cần `bench migrate`), ADR-050 Amendment ghi việc bỏ câu mẫu và
nút dưới tin cuối, mô tả trường mới.

## Quyết định của người viết thiết kế (sau khi rà, chờ người dùng xem)

1. Nút đóng phiếu chỉ dưới tin trả lời có kết quả (hướng xử lý, `de_xuat`), không dưới câu hỏi hay thông báo; cần
   trường `reply_kind`.
2. Bỏ điều "không có mục Chờ duyệt"; đề xuất đã áp dụng tính là kết quả.
3. Mọi lượt không có người ra lệnh được biết tool nào mở khi bấm "Cho bot làm".

## Để người làm quyết

- Tên hàm, chỗ đặt hàm tính `actions` (gợi ý: `messages.py`, dùng chung cho `thread` và `decide_result`).
- Cách hiện danh sách các bước dưới tin (gạch đầu dòng, chữ nhỏ hơn nội dung).
- Thứ tự test và chia commit.
