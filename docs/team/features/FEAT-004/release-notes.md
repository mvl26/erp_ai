Feature: FEAT-004 (kèm CHG-001)
Stage: asbuilt (release notes)
Author-agent: writer
Date: 2026-11-14
Approved-by:

# Ghi chú phát hành FEAT-004: bot sửa code, chạy lệnh bench và ghi bản ghi trực tiếp

Đọc cho: quản trị hệ thống (System Manager), người có role `ERP AI Instructor` (người ra lệnh và người duyệt). Nguồn từng ý nằm trong ngoặc; chi tiết kỹ thuật ở `asbuilt.md`.

## Đọc trước: điều chưa được kiểm

- Người đã chấp nhận tính năng này ngày 2026-11-14 với bằng chứng đang có, **không có một lần chạy toàn bộ test của app ra kết quả xanh**. Lần tốt nhất: 1499 test, 2 failure, 12 error; 14 test đó chạy lại riêng thì 6 xanh, 8 vẫn lỗi deadlock `1213` do nhiều phiên cùng chạy test trên một site. Không có bằng chứng 8 test đó là lỗi của tính năng, nhưng cũng chưa có lần chạy sạch để chứng minh điều ngược lại.
- Chưa ai xem bằng mắt: form duyệt ở từng trạng thái, một lần bấm Duyệt thật trên trình duyệt, dòng kết quả trên trang phiếu Helpdesk thật, và bot có "hỏi lại 0 lần" với model thật hay không (AC-22, AC-25, AC-28, AC-29).
- Chưa kiểm hướng "xuống" của migration (lên, xuống, lên).

## Đổi gì

1. **Hai công tắc mới trên `ERP AI Setting`, cài xong đều tắt** (`code_change_enabled` "Cho phép sửa code và lệnh bench", `unrestricted_enabled` "Toàn quyền (khẩn cấp)"). Chỉ System Manager đặt được; bot không đọc, không ghi được hai ô này (AC-32, AC-33).
2. **Công tắc code bật, mức `L3`, có người có `ERP AI Instructor` ra lệnh: bot ghi bản ghi trực tiếp, không qua duyệt.** Bot tạo và sửa bản ghi theo quyền của tài khoản agent (tạo User, gán vai trò nghiệp vụ, sửa cấu hình, bản ghi nháp) ngay trong lượt, không hỏi lại (AC-29, AC-30). Vẫn bị từ chối: gán `System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All`; sửa `Administrator`, `Guest` và tài khoản agent; sửa phân quyền; xóa, submit, hủy (AC-31). **Site nào đã bật ô này chỉ để đề xuất code thì sau cập nhật bot cũng ghi được bản ghi ngay.** Site `miyano` đang ở trạng thái đó.
3. **Cùng điều kiện, bot đề xuất sửa file trong app cho phép hoặc chạy một lệnh `bench` trong danh sách cố định** (`migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build`, `version`). Mỗi đề xuất là một bản ghi `ERP AI Change Proposal` không sửa được sau khi tạo; bot đăng một comment trên phiếu với mã đề xuất, đích, nhánh nhận commit, cảnh báo nếu là app lõi, rồi ba liên kết "Duyệt", "Từ chối", "Xem nội dung thay đổi" (AC-3, AC-22, AC-24). Mọi thay đổi code và lệnh chỉ xảy ra sau khi một người có `ERP AI Instructor` bấm; chữ "ok" hay "duyệt" trong phiếu không phải là duyệt; bot không tự duyệt đề xuất của mình (AC-5, AC-11).
4. **Duyệt bằng một lần bấm trên phiếu.** Mở liên kết "Duyệt" sẽ mở form Desk của đề xuất; form gửi đúng một lời gọi POST, không hộp xác nhận, rồi bạn ở lại form và thấy diff và trạng thái mới. Mở lại liên kết sau khi đề xuất đã xử lý chỉ hiện trạng thái hiện tại, không làm gì thêm (AC-25, AC-26). Form vẫn có ba nút Duyệt, Từ chối, Hoàn tác, có hộp xác nhận.
5. **Áp dụng một file là đúng một commit git local** trên nhánh đang checkout, nội dung đúng bằng nội dung đã duyệt. Hoàn tác bằng một commit hoàn tác; bị từ chối nếu file đã đổi sau đó. Bot không push, không đổi nhánh, không chạy hook của repo (AC-6, AC-7, AC-17, AC-23). Sau mỗi kết cục (áp dụng, lỗi, hết hiệu lực, hoàn tác) có một dòng hoạt động trên phiếu nêu trạng thái cuối, mã commit hoặc mã thoát hoặc lý do, đã che URL và email (AC-28).
6. **"Toàn quyền (khẩn cấp)": công tắc riêng, từ `L1`, có người ra lệnh, không cần công tắc code.** Bot thêm xóa, submit/hủy, gọi hàm whitelist, và các giới hạn vai trò, tài khoản, DocType không còn: bot gán được `System Manager` cho bất kỳ ai, sửa được phân quyền. **Không hẹn giờ tự tắt, không có cảnh báo khi đang bật; xóa và submit không hoàn tác.** Vẫn đóng ở mọi chế độ: cấu hình, khóa API, `ERP AI Log`, `ERP AI Change Proposal`, mật khẩu và khóa API của người dùng, hàm của app `erp_ai` (AC-32, AC-33).
7. **Điều chỉ chặn ở mức cố gắng:** bot gọi hàm whitelist bất kỳ khi Toàn quyền bật, nên việc chặn đọc mật khẩu và khóa API của người dùng qua đường này không kín. Người đã chọn giữ gọi hàm bất kỳ thay vì danh sách hàm cho phép. Sáu dạng còn lọt ghi ở `asbuilt.md` mục 5 (AC-33).
8. **Nhật ký.** Mỗi bước đề xuất, duyệt, từ chối, áp dụng, hoàn tác là một dòng `ERP AI Log` (`entry_type=change`). Mỗi lời gọi công cụ bản ghi có một mục trong cột `actions` với giá trị trước/sau dạng tóm tắt. Cột này có trần 60000 byte mỗi lượt: mục vượt trần chỉ còn dấu `[đã cắt]`, lượt có quá nhiều lệnh ghi bỏ các mục cuối (AC-34, AC-35).

## Ai bị ảnh hưởng

- System Manager: thấy hai công tắc mới và mục "Sửa code và lệnh bench" trên `ERP AI Setting`; cần `bench migrate` (tạo DocType `ERP AI Change Proposal`, thêm ô vào `ERP AI Setting`, thêm giá trị và 3 trường vào `ERP AI Log`).
- Người có `ERP AI Instructor`: là người duyệt, phải vào được Desk. Chưa kiểm cho Hiếu, Việt, Tiến.
- Người không có `ERP AI Instructor`, người tạo phiếu, người được giao phiếu: nội dung của họ là dữ liệu, không phải lệnh; bot không có công cụ ghi hay đề xuất nào từ phiếu của họ (AC-11).
- Cả hai công tắc tắt: danh sách tool và prompt của bot giống bản trước (AC-1).

## Cần làm gì: danh sách việc sau merge

Thứ tự cho người nhận (lệnh copy từ `cmd.migrate`, `cmd.run` của profile; `bench restart` là lệnh của bench, không phải slot `cmd.*`):

- [ ] 1. `bench --site miyano migrate` (hoặc `cd ../.. && bench --site miyano migrate` từ thư mục app).
- [ ] 2. `bench restart`.
- [ ] 3. **Gỡ role `ERP AI Instructor` khỏi tài khoản agent** (Desk, User, tài khoản agent, bỏ dòng role). Mã đã từ chối tài khoản agent ở bước duyệt, áp dụng và hoàn tác dù đang mang role này, nhưng quyết định của người là gỡ; chưa có bằng chứng đã gỡ trên `miyano` (A-31). Tài khoản agent giữ `System Manager` theo quyết định của người. Dán danh sách role hiện có của tài khoản vào `acceptance.md`.
- [ ] 4. Xác nhận từng người duyệt (ít nhất Hiếu, Việt, Tiến) mở được Desk và form `ERP AI Change Proposal`.
- [ ] 5. Xem form duyệt ở cả 3 trạng thái (chờ duyệt, đã áp dụng, đã hoàn tác hoặc lỗi): app, đường dẫn, diff, nhánh nhận commit, thông điệp commit, cảnh báo app lõi, cờ hoàn tác được, mã commit sau áp dụng/hoàn tác (AC-22).
- [ ] 6. Một lần bấm "Duyệt" thật trên trang phiếu Helpdesk, bằng trình duyệt thật, đang đăng nhập bằng người có `ERP AI Instructor`: xem form mở, không hộp xác nhận, trạng thái "Đã duyệt", và dòng kết quả xuất hiện trên trang phiếu (AC-25, AC-28). Nếu dòng kết quả không hiện: báo lại, phương án là ADR mới cho cách đánh dấu comment hệ thống hoặc bỏ AC-28.
- [ ] 7. Kiểm ADR-023 vẫn ở trạng thái `proposed` (chưa ai chuyển); architect chốt khi người xác nhận QĐ 1 và QĐ 6 (b).
- [ ] 8. Trước khi bật lâu dài: chạy một vòng đề xuất, duyệt, áp dụng, hoàn tác trên 1 app ở site dev (có commit áp dụng và commit hoàn tác); chạy 3 phiếu kịch bản với model thật, đếm số lần bot hỏi lại trước khi làm (AC-29).
- [ ] 9. `unrestricted_enabled` để **tắt** trên môi trường đích. Nếu bật thử trên dev, làm đúng một việc xóa hoặc submit thử rồi tắt ngay, kiểm dòng nhật ký (AC-34).
- [ ] 10. Lên prod cần `Approved-by-prod:` của người (G5). Điều kiện kèm theo (spec A-27): `unrestricted_enabled` tắt, và người xác nhận bản tóm tắt trước/sau trong nhật ký là đủ dùng (hoặc chờ bản đầy đủ của FEAT-005).

## Tắt và quay lại

- Tắt hành vi: đặt `code_change_enabled = 0` và `unrestricted_enabled = 0` trên `ERP AI Setting`. Bot trở lại như bản trước; không cần đổi mã. Phải tắt cả hai, vì Toàn quyền cấp công cụ độc lập với công tắc code.
- Commit bot đã tạo ở lại lịch sử git: bấm Hoàn tác trên từng đề xuất trước khi tắt, hoặc `git revert` thủ công.
- **Revert mã xóa DocType `ERP AI Change Proposal`** cùng toàn bộ bản ghi đề xuất: mất dữ liệu kiểm toán, cần người duyệt trước khi làm. Cột thừa trên `ERP AI Log` vô hại.
- Bản ghi bot đã tạo hoặc sửa trực tiếp, và việc xóa, submit, gọi hàm khi Toàn quyền bật, không có bước hoàn tác tự động; chỉ dựng lại từ `ERP AI Log` (bản tóm tắt, có trần).

## Rủi ro còn lại, nói thẳng

- Bot ghi bản ghi trực tiếp, không qua duyệt, và chốt chặn duy nhất cho chế độ thường là danh sách cấm trong mã cộng việc chỉ người ra lệnh mới có công cụ. Hiểu sai một lệnh thì việc đã xảy ra.
- Danh sách cấm không kín. Gán một vai trò có quyền sửa người dùng hay phân quyền (không nằm trong 6 vai trò cấm) là cách nâng quyền gián tiếp; sửa User thay toàn bộ dòng vai trò nên bot có thể bớt vai trò của người khác.
- Ở chế độ Toàn quyền, tài khoản agent giữ `System Manager`; Server Script bật được nghĩa là chạy code do bot viết trên site.
- Liên kết "Duyệt" không gắn với người và không hết hạn: người có `ERP AI Instructor` mở một liên kết được chuyển tiếp là duyệt ngay, không còn hộp xác nhận ở đường này (lưới còn lại: kiểm lại lúc áp dụng và hoàn tác bằng commit).
- Kịch bản "câu chèn lệnh trong phiếu khi Toàn quyền bật" không có test (AC-11).
- Cột `actions` có trần: "đúng một mục mỗi lời gọi" không giữ khi lượt có hàng trăm lệnh ghi.
- Dòng kết quả trên phiếu chưa từng thấy trên trang Helpdesk thật.
