Feature: CHG-001
Stage: analyze
Author-agent: analyst
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec CHG-001 — Bot làm luôn, chỉ một bước duyệt / không duyệt (con trỏ)

Mode: decide, cỡ L, playbook change-request. File này là con trỏ: nội dung đầy đủ nằm ở `docs/team/features/FEAT-004/spec.md`, mục "Amendment 2 — 2026-11-14". Amendment ghi lại điều người đã ra lệnh và code đã được nhận về (`25be823`, `6d90e79`); không thiết kế lại.

## Mục tiêu
**Giả thuyết (độ tin cậy 85%):** người muốn bot làm xong việc được giao ngay trong lượt, không hỏi lại. Việc về bản ghi làm thẳng. Việc về code và lệnh `bench` dừng ở một đề xuất có liên kết Duyệt / Từ chối ngay trong phản hồi của bot ở phiếu; một lần mở liên kết Duyệt là áp dụng ngay, không hộp xác nhận. Ô "Toàn quyền (khẩn cấp)" cho tình huống gấp. Chưa tới 100% vì chưa thử với model thật, chưa xem comment hiển thị trên trang phiếu Helpdesk, chưa mở liên kết qua HTTP thật.

| Mục | Nội dung |
|---|---|
| Outcome | Người có `ERP AI Instructor` giao việc, bot làm luôn; thay đổi code và lệnh chỉ xảy ra sau một lần mở liên kết Duyệt của người có vai trò. |
| Users | Người có `ERP AI Instructor` (ra lệnh và duyệt); System Manager (bật hai ô công tắc). Người tạo phiếu và người comment không có thẩm quyền là nguồn dữ liệu. |
| Why now | Người đã ra lệnh và phiên khác đã viết code; site `miyano` đang chạy mã đó; reviewer của FEAT-004 không chấm được phần vượt spec khi chưa có amendment. |
| Success | Lúc build: AC-1..AC-35 của FEAT-004 đạt. Sau G4: 3 phiếu kịch bản có đủ thông tin, bot hỏi lại 0 lần; duyệt một đề xuất code bằng 1 lần mở liên kết, 0 hộp xác nhận, có comment kết quả; bật "Toàn quyền" thử một lần rồi tắt. |
| Constraints | Không push, không deploy prod (G5). Bot không tự duyệt đề xuất của mình. Mật khẩu, khóa API, cấu hình, nhật ký và đề xuất của app đóng ở mọi chế độ. |
| Out of scope | Hoàn tác một lần bấm; hẹn giờ tắt Toàn quyền; bỏ hộp xác nhận ở form Desk; thiết kế lại danh sách cấm; sửa spec FEAT-005 và FEAT-006. |

## Người dùng
Như bảng trên. Chi tiết: FEAT-004 spec, mục Người dùng (dòng `[changed: Amd-2]`) và N-1.

## Phạm vi
- **Trong:** bot làm luôn; duyệt một lần bấm trên phiếu; báo kết quả về phiếu; công cụ bản ghi trực tiếp; ô "Toàn quyền (khẩn cấp)" (FEAT-004 N-3, mục 15–19).
- **Ngoài:** như dòng Out of scope ở trên; mọi điều cấm vẫn giữ ở FEAT-004 N-2, đoạn "Những điều vẫn bị cấm".

## Dữ liệu
Một ô "Toàn quyền (khẩn cấp)" trên cấu hình agent (mặc định tắt); ô "Cho phép sửa code và lệnh bench" đổi nghĩa (cũng mở công cụ bản ghi). Không thực thể mới. Chi tiết: FEAT-004 N-4.

## Giao diện / tích hợp
Comment của bot trên phiếu có ba liên kết (Duyệt, Từ chối, Xem nội dung thay đổi); form Desk giữ nguyên, kể cả hộp xác nhận và nút Hoàn tác. Chi tiết: FEAT-004 N-5. Các chỗ trái ADR (ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7) do architect phán quyết ở tài liệu riêng.

## NFR
NFR-1 sửa phạm vi (chỉ đề xuất code và lệnh); thêm NFR-10 (1 lần mở liên kết, 0 hộp xác nhận) và NFR-11 (100% lời gọi công cụ bản ghi có mục nhật ký). Chi tiết: FEAT-004 N-6.

## Tiêu chí nghiệm thu
Các tiêu chí nằm ở FEAT-004 spec, mục N-7. Danh sách:

| Mã | Tiêu chí (tóm tắt) | Cách kiểm |
|---|---|---|
| AC-1 [changed] | Cả hai ô tắt thì danh sách tool và prompt trùng bản nền (32 tổ hợp) | Test ma trận |
| AC-2 [changed] | Ba đường cấp: tool đề xuất, công cụ bản ghi, nhóm Toàn quyền | Test ma trận |
| AC-5 [changed] | Chỉ `ERP AI Instructor` duyệt, qua cả form và liên kết | Test từng người dùng |
| AC-11 [changed] | Phiếu của người không có thẩm quyền: 0 công cụ ghi, 0 bản ghi đổi | Test Cổng model giả |
| AC-12 [changed] | Duyệt qua liên kết ghi đúng người mở liên kết | Test đếm nhật ký |
| AC-14 [changed] | Prompt: chờ người bấm Duyệt; "ok" không phải duyệt | Test so chuỗi |
| AC-15 [changed] | ADR cho từng chỗ trái; cách hoàn tác là tắt hai ô | `ls docs/team/adr/`; `cmd.test` |
| AC-22 [changed] | Comment của bot cho thấy đủ thông tin trước khi mở liên kết; form giữ nguyên | Test HTML comment; qa mở trang phiếu thật |
| AC-24 | Comment có 3 liên kết, chữ ký gắn đề xuất và hành động | Test đọc HTML |
| AC-25 | Mở liên kết Duyệt: "Đã duyệt", 1 job, về trang phiếu, 0 hộp xác nhận | Test + qa trình duyệt thật |
| AC-26 | Liên kết bị từ chối với chữ ký sai, người không có vai trò, đề xuất đã quyết | Test từng nhánh |
| AC-27 | Duyệt qua liên kết không bỏ qua kiểm tra lúc áp dụng | Test từng điều kiện |
| AC-28 | Kết quả áp dụng, lỗi, hết hiệu lực, hoàn tác được comment về phiếu | Test job trên repo tạm (chưa có code) |
| AC-29 | Prompt "làm luôn"; bot hỏi lại 0 lần với phiếu đủ thông tin | Test so chuỗi; 3 phiếu thật sau G4 |
| AC-30 | Công cụ bản ghi theo phân quyền Frappe, từ chối thì không đổi gì | Test `test_site_api` |
| AC-31 | Chế độ thường vẫn cấm 6 vai trò, tài khoản quản trị, Role Permission… | Test từng nhánh |
| AC-32 | Ô "Toàn quyền": mặc định tắt; bật thì thêm xóa, submit/hủy, gọi hàm | Test ma trận và từng công cụ |
| AC-33 | Vẫn đóng ở mọi chế độ: cấu hình, khóa, nhật ký, đề xuất, hàm `erp_ai` | Test từng nhánh |
| AC-34 | Mỗi lời gọi công cụ bản ghi có mục trong cột hành động của nhật ký | Test qua runner |
| AC-35 | Giá trị trước/sau của mỗi lần ghi (chưa có code) | Test từng công cụ ghi |

Trả lời 5 điểm mở của intake (căn cứ: handoff mục 5): "làm luôn" áp cho cả bản ghi và code; nút nằm trên phản hồi của bot ở phiếu; chỉ bỏ hộp xác nhận ở liên kết trong comment (form giữ hộp xác nhận và nút Hoàn tác); luồng chữ "ok" của FEAT-005 được thay bằng nút cho code và lệnh, còn bản ghi không có bước duyệt; danh sách cấm giữ như mã nhận về (AC-31, AC-33).

## Assumptions decided by the team
Đủ 4 trường ở FEAT-004 spec, N-8: A-1', A-2', A-19..A-27, và A-28 ở N-9. Các điểm lớn nhất: một ô công tắc nay có hai nghĩa (A-24); Toàn quyền tắt bằng tay, không hẹn giờ (A-23); liên kết ký không hết hạn và không gắn với người (A-25); AC-27 (phần liên kết), AC-28, AC-35 là chỗ mã nhận về còn thiếu (A-26).

## Definition of Done
**Phần build (trước G4):** AC-1..AC-35 của FEAT-004 đạt; ADR cho các chỗ trái; `cmd.test` xanh (lưu ý thời gian chạy khoảng 558 s và 5 lỗi do cài đặt site, xem DoD FEAT-004); reviewer đã chấm các file nhận về; luật kiến trúc mới cho `apply_job.py`, `propose_change.py`, `site_api.py`, `change_decision.py`.

**Sau G4 (`/team:asbuilt`, người làm phần đo thực tế):** As-Built; README/tài liệu người dùng (hai ô công tắc, liên kết Duyệt, "Quy tắc an toàn đã đổi"); mục CHANGELOG; 3 phiếu kịch bản với model thật; một lần bật rồi tắt "Toàn quyền" trên dev; trước khi deploy ô "Toàn quyền" tắt và AC-35 đạt hoặc người đồng ý (A-27); lên prod cần G5.

## Amendment
Không có; file này là con trỏ tới FEAT-004 Amendment 2. Artifact sau bị ảnh hưởng: xem FEAT-004 N-10 (arch-impact, ADR, design, plan, tasks, review) và N-9 (hệ quả cho FEAT-005, FEAT-006).
