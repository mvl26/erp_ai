Feature: FEAT-005 (Amendment 2)
Stage: asbuilt (release notes)
Author-agent: writer
Date: 2026-11-15
Approved-by:

# Ghi chú phát hành FEAT-005: nhật ký trước/sau đầy đủ và cảnh báo phân quyền đúng một lần

Đọc cho: quản trị hệ thống (System Manager) và người nhận cảnh báo (`alert_recipients`). Nguồn từng ý nằm trong ngoặc (AC hoặc file); chi tiết kỹ thuật ở `asbuilt.md`.

## Đọc trước: điều chưa được kiểm

- Chưa có bằng chứng thật trên site `miyano` về email cảnh báo: chưa ai cho bot gán thử một role rồi đợi thư hôm sau và thư hôm sau nữa (spec "Success"). Test tự động đạt, cả app `Ran 1564 tests` / `OK` (`acceptance.md`), nhưng đó là thời gian giả.
- CI chưa chạy: nhánh chưa push. CI chạy khi push `develop` hoặc mở PR.
- **Dòng cảnh báo trong Error Log có thể lặp.** Sau một lần chạy kiểm tra hằng ngày bị lỗi giữa chừng, thư cảnh báo vẫn đúng một lần (lần sau gửi lại, không gửi hai lần), nhưng dòng "Agent đã sửa bản ghi phân quyền" của lần lỗi ở lại trong Error Log, và lần sau ghi thêm một dòng: cùng thay đổi hiện hai lần ở đó. Lý do: bảng Error Log của Frappe không hoàn tác được. Chỉ nhìn vào Error Log mới thấy; không có thay đổi nào bị sót (acceptance.md R-1, ADR-024 QĐ 3.8).
- Mục User mà nhật ký không đọc được trước/sau (dòng cũ, hoặc hỏng) hiện là `sửa User <user> (…), không có trước/sau`, không mang dấu `[QUẢN TRỊ]` vì không biết role. Nếu hôm đó có nhiều thay đổi khác, dòng này có thể nằm trong "…và N mục khác". Danh sách đầy đủ luôn tra được ở `ERP AI Log` (R-2).

## Đổi gì

1. **Nhật ký lượt chạy ghi trước và sau của từng lần bot ghi bản ghi.** Với mỗi lần công cụ bản ghi (`api_create_record`, `api_update_record`, và khi bật "Toàn quyền" thì `api_delete_record`, `api_submit_record`) ghi thành công, dòng nhật ký `reason` của lượt trong `ERP AI Log` có giá trị trước và sau gồm cả dòng của bảng con: role của User, ngày của Holiday List, trạng thái và hành động của Workflow. Khi bot sửa bằng cách đưa cả danh sách, so trước với sau cho thấy dòng nào bị bỏ và dòng nào được thêm (AC-13 a, b).
2. **Không cắt, không đè.** Trước/sau lưu đầy đủ, không bị cắt ở trần 20.000 ký tự của kết quả đưa cho model; hai lời gọi cùng công cụ trong một lượt có hai cặp trước/sau riêng, khóa theo thứ tự lời gọi (`api_update_record#1`, `api_update_record#2`) (AC-13 c, d). Trước/sau không đi vào ngữ cảnh của model.
3. **Với User, nhật ký chỉ ghi mã user và danh sách role**, không ghi gì khác về người đó. Trường mật khẩu, khóa, token bị bỏ khỏi mọi ảnh chụp (A-12; `test_snapshot_drops_secret_and_system_fields`).
4. **Cảnh báo hằng ngày "Agent đã sửa bản ghi phân quyền" được làm lại.**
   - Nguồn là nhật ký trước/sau ở mục 1, không còn là dấu "người sửa" của dòng `Has Role`. Vì thế không còn báo nhầm khi bot lưu lại một User mà không đổi role, không còn báo lặp mỗi ngày, và thấy được role bị gỡ (AC-14).
   - Mỗi mục nêu việc, user, role, người ra lệnh và thời điểm. Ví dụ dạng chữ: `thêm role <role> cho <user> (người ra lệnh <người>, <YYYY-MM-DD HH:MM>)`, `gỡ role <role> của <user> (…)`; bản ghi phân quyền: `<tạo|sửa|xóa|submit/hủy> <DocType> <tên> (…)` (`design-amd2.md` §3.3).
   - Role thuộc 6 role quản trị (`System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All`) có dấu `[QUẢN TRỊ]` và đứng trước.
   - Thư vẫn chỉ liệt kê tối đa 5 mục, phần còn lại là "…và N mục khác"; vì dòng quản trị đứng trước nên không bị cắt trước dòng thường. Danh sách đầy đủ tra ở `ERP AI Log`.
   - Không cảnh báo cho: role do người thêm, bản ghi phân quyền do người sửa, bot lưu User mà không đổi role.
   - Ba điều kiện cảnh báo khác (role của tài khoản agent lệch tập; Server Script hoặc Webhook do agent tạo đang bật; khóa đang bật không có giá trị) giữ nguyên chữ và hành vi.
5. **Mỗi thay đổi được báo đúng một lần** (AC-19, NFR-8). Hệ thống nhớ "đã báo tới đâu" trong ô chỉ đọc mới `privilege_alert_checked_until` của `ERP AI Setting` (nhóm cảnh báo, sau `alert_recipients`). Lần chạy kế tiếp xét từ mốc đó tới 5 phút trước giờ chạy; lịch bị lỡ vài ngày thì lần chạy sau gộp đủ các ngày lỡ và không lặp ở lần sau nữa. Người lưu form không đổi được ô này (bị khôi phục). Hai lần chạy cùng lúc không chồng nhau (khóa theo site).
6. **Lần chạy đầu sau khi cập nhật báo một lần mọi thay đổi cũ của bot** mà chưa từng được báo, vì mốc còn rỗng. Các mục cũ ra dạng `…, không có trước/sau` (nhật ký cũ chưa có trước/sau). Đây là bình thường, không phải lỗi; sau đó không lặp.
7. **Lượt chạy lỗi không để lại thay đổi không có nhật ký.** Nếu lượt của bot lỗi trước khi dòng nhật ký `reason` được lưu, mọi thay đổi bot đã làm trong lượt đó (bản ghi, đề xuất, comment) được hoàn tác. Lỗi gốc vẫn ghi vào Error Log như trước (NFR-3, ADR-024 QĐ 2). Hai chuyện đi kèm: dòng nhật ký `change` bước `propose` của FEAT-004 nay được ghi ngay sau dòng `reason` của lượt, không còn giữa lượt; job hoặc thư xếp hàng chờ commit của phần bị hoàn tác cũng bị bỏ.

## Ai bị ảnh hưởng

- System Manager: cần `bench migrate`, thấy ô chỉ đọc mới trên `ERP AI Setting` (không sửa được, 0 DDL). Đọc trước/sau ở `ERP AI Log`.
- Người nhận cảnh báo (`alert_recipients`): thư cảnh báo phân quyền có chữ mới như mục 4; ít thư thừa hơn. Chưa có địa chỉ nào thì chỉ có Error Log (`erp_ai/alerts.py`).
- Người có `ERP AI Instructor`: là "người ra lệnh" ghi trong nhật ký và thư; không đổi gì khi dùng.
- HD Agent và khách: không đổi gì (`ui: false`, không có file frontend trong diff).

## Cần làm gì

Chỉ người làm được (lệnh copy từ `cmd.migrate` của profile; `bench restart` là lệnh của bench):

- [ ] 1. `cd ../.. && bench --site miyano migrate`, rồi `bench restart`.
- [ ] 2. Kiểm `alert_recipients` có ít nhất một địa chỉ trước khi deploy.
- [ ] 3. Trên dev: cho bot gán một role cho user thử; email hôm sau nêu user, role, người ra lệnh; hôm sau nữa không lặp; đọc trước/sau ở `ERP AI Log` và đổi lại bằng tay; gỡ user thử.
- [ ] 4. Quyết định có chấp nhận dòng Error Log lặp sau một lần chạy lỗi không (mục "Đọc trước"); nếu không thì cần amendment.
- [ ] 5. CI sau khi push `develop`.
- [ ] 6. Lên prod cần `Approved-by-prod:` của người (G5).

## Điều không đổi và giới hạn đã biết

- Khi "Toàn quyền (khẩn cấp)" đang bật, đổi role bằng cách gọi hàm whitelist (`api_call_method`) **không có** trong cảnh báo hằng ngày. Vẫn không có cảnh báo khi "Toàn quyền" đang bật (FEAT-004, A-23).
- Commit do mã ngoài `erp_ai` chạy bên trong một công cụ (thay đổi lược đồ ngầm, controller tự commit) cố định các thay đổi trước nó; nếu lượt lỗi ngay sau đó thì thay đổi ở lại mà không có dòng nhật ký (ADR-024 QĐ 5).
- Bước phân loại (FEAT-006) có cùng lỗ hổng callback commit khi lỗi; chưa sửa, ghi ở `docs/team/debt.md`.

## Tắt và quay lại

Revert mã và JSON, rồi `cmd.migrate`. Dòng `privilege_alert_checked_until` thừa trong bảng Singles vô hại. Cảnh báo quay về kiểu cũ (báo lặp). Nên quay lại nếu trong 2 ngày đầu cảnh báo không tới khi có thay đổi thử, hoặc tới lặp (`design-amd2.md` §6).
