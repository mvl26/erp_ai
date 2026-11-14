Feature: CHG-001
Stage: asbuilt
Author-agent: writer
Date: 2026-11-15
Approved-by:
<!-- Cổng: G4 tắt. Người chấp nhận bằng lời ("Chấp nhận như FEAT-004", AskUserQuestion); ngày ghi ở mục "Đã được chấp nhận thế nào". Dòng Approved-by do người điền. -->

<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod. -->

# As-Built CHG-001 — Bot làm luôn, chỉ một bước duyệt / không duyệt (con trỏ)

File này là con trỏ. CHG-001 được build, nghiệm thu và ghi tài liệu bên trong FEAT-004 (task T53–T68, thêm T69–T70 của FEAT-004; tiêu chí AC-24..AC-35). Không có release notes, CHANGELOG hay README riêng: các file của FEAT-004 đã phủ thay đổi này. Không có hành vi nào ở đây mà `FEAT-004/asbuilt.md` không nói.

## Thay đổi là gì

Người ra lệnh "bot làm luôn, chỉ một nút duyệt / không duyệt". Kết quả: việc về bản ghi bot làm thẳng; việc về code và lệnh `bench` dừng ở một đề xuất có liên kết Duyệt / Từ chối / Xem nội dung thay đổi ngay trong comment của bot ở phiếu, và một lần mở liên kết Duyệt là áp dụng, không hộp xác nhận. Thêm ô "Toàn quyền (khẩn cấp)" (mặc định tắt) cho tình huống gấp. Form Desk giữ nguyên hộp xác nhận và nút Hoàn tác (`CHG-001/spec.md`, mục Phạm vi).

## Từng phần nằm ở đâu trong `FEAT-004/asbuilt.md`

Số dòng là dòng của file đó tại ngày viết; nếu file đổi, tìm theo tên mục.

| Phần của CHG-001 | Chỗ trong FEAT-004/asbuilt.md |
|---|---|
| Hai ô công tắc, bảng cấp tool, bản ghi ghi trực tiếp, chế độ thường và "Toàn quyền", điều luôn đóng, tài khoản agent (AC-1, AC-2, AC-30..AC-33) | mục 2, dòng 23-39 |
| Liên kết ký trong comment, form POST một lần, method `decide` POST-only (AC-24..AC-26) | mục 3.1 hàng 3.3, 3.8, 4.2 (dòng 60, 66, 69) |
| Kiểm lại lúc áp dụng; dòng `Info` kết quả về phiếu (AC-27, AC-28) | mục 3.1 hàng 4.3 (dòng 71); mục 3.2 `apply_job.py`, `result_comment.py` (dòng 97, 107) |
| Prompt "làm luôn" (AC-29) | mục 3.1 hàng 3.7 (dòng 65) |
| Công cụ bản ghi, nhật ký `actions` có trần, giá trị trước/sau (AC-30..AC-35) | mục 3.2 dòng 108-109; mục 3.1 hàng 2.5 (dòng 54) |
| Quyền, tài khoản agent bị loại khỏi thẩm quyền duyệt | mục 3.1 hàng 5 (dòng 74) |
| File ngoài touchpoint do CHG-001 sinh ra (`change_link.py`, `change_decision.py`, `site_api.py`, `agent_write_guard.py`) | mục 3.2 dòng 105-109 |
| Rủi ro còn lại: sáu dạng lọt của AC-33, trần nhật ký, không cảnh báo khi Toàn quyền bật, dòng `Info` chưa thấy trên phiếu thật, liên kết không gắn với người, vai trò tài khoản agent | mục 5 hàng 1, 2, 3, 5, 6, 8, 9 (dòng 131-139) |
| Release notes, CHANGELOG, README, checklist cho người nhận | mục "Release notes" và "CHANGELOG" (dòng 114-120); `FEAT-004/release-notes.md` |
| Việc sau G4 đã đóng | mục "Nợ sau G4" (dòng 144-157) |

## Đã được chấp nhận thế nào

- Phán quyết riêng của qa trong `CHG-001/acceptance.md` là `rework` (dòng `Verdict:` ở cuối file, dòng 86): `cmd.test` cả app chưa lần nào `OK`, migration up/down/up chưa do qa chạy, AC-25 và AC-28 còn một phần NOT VERIFIABLE. Qa không chạy lại gì cho CHG-001; mọi bằng chứng lấy từ nghiệm thu FEAT-004. Không có task dev nào phải làm lại.
- Ngày 2026-11-15 người chọn "Chấp nhận như FEAT-004" (AskUserQuestion): áp quyết định "Chấp nhận với bằng chứng hiện có" của 2026-11-14 cho CHG-001. Đây là chấp nhận của người, không phải nghiệm thu sạch của qa; phần `rework` của qa được giữ nguyên. Qa ghi quyết định này vào `CHG-001/acceptance.md`; xem dòng `Verdict:` cuối file ở bản mới nhất.
- Cùng cách xử lý với FEAT-004 (`FEAT-004/asbuilt.md` mục 1, dòng 15). G4 tắt.

## Còn mở cho người

1. **AC-25:** mở liên kết Duyệt/Từ chối bằng trình duyệt thật trên trang phiếu Helpdesk, đăng nhập bằng người có `ERP AI Instructor`: form mở, không hộp xác nhận, trạng thái "Đã duyệt" (`FEAT-004/release-notes.md` checklist bước 6; asbuilt mục 5 hàng 6).
2. **AC-28:** xem dòng `Info` kết quả có hiện trên trang phiếu thật không. Nếu không hiện, báo lại: phương án là ADR mới về cách đánh dấu comment hệ thống hoặc người đồng ý bỏ AC-28 (asbuilt mục 5 hàng 5; `CHG-001/design.md` A-D1).
3. **Gỡ role `ERP AI Instructor` khỏi tài khoản agent** trên `miyano` (Desk, User, tài khoản agent, bỏ dòng role) và dán danh sách role hiện có vào `acceptance.md` (asbuilt mục 5 hàng 9; release notes bước 3). Chưa có bằng chứng đã gỡ.
4. **Migrate và restart trên site `miyano`:** `bench --site miyano migrate`, rồi `bench restart` (release notes bước 1 và 2; ô `unrestricted_enabled` mới cần migrate).
5. Trước khi bật thật "Toàn quyền": ô phải tắt trên môi trường đích và người xác nhận bản tóm tắt giá trị trước/sau đủ dùng (AC-35, A-27; asbuilt mục 5 hàng 3). Lên prod cần G5; `Approved-by-prod:` và `Released:` ở đầu file để trống cho tới lúc đó.
