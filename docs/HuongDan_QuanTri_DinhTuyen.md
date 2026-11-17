# Hướng dẫn quản trị: định tuyến theo điểm (FEAT-006)

Dành cho System Manager giữ cấu hình agent. Mô tả cách bật việc tự gán người và tạo Task, cách đọc điểm, và cách viết `condition` SLA an toàn. Nguồn: spec và As-Built của FEAT-006 (`docs/team/features/FEAT-006/`), site dev `miyano`.

## 1. Cách đọc điểm trên phiếu

- Ba trường chỉ đọc trên HD Ticket: `ai_complexity` (độ phức tạp), `ai_importance` (độ quan trọng), `ai_score_reason` (lý do chấm, tối đa 25 từ). Chúng có từ mức `L1`; ở `L0` điểm chỉ nằm trong `ERP AI Log` (cột `predicted_complexity`, `predicted_importance`, `predicted_score_reason`, `predicted_assignee`).
- Thang 1–3. Độ phức tạp: 1 dưới 1 giờ làm việc, không đổi hệ thống; 2 trong 1 ngày làm việc; 3 nhiều ngày, cần phân tích, xây mới hoặc tích hợp. Độ quan trọng: 1 ảnh hưởng một người, không chặn việc; 2 chặn việc của một người hoặc một bộ phận, hoặc có hạn trong 24 giờ; 3 chặn nghiệp vụ kế toán, kho, bán hàng hoặc nhiều bộ phận ngừng việc.
- Điểm bằng 0 nghĩa là chưa chấm: phiếu cũ, phiếu ở `L0`, hoặc model trả điểm sai (ngoài 1–3, sai kiểu, thiếu một trong hai điểm). Trường không bao giờ rỗng. Nhật ký ghi "không có điểm" và ưu tiên khi đó theo `category_mapping`.
- Phiếu cũ không được chấm lại và không được chia lại. Phiếu được sửa sau lần chạy đầu cũng không được chấm lại.

## 2. Tám việc làm trước khi bật `auto_assign_enabled`

Không phải điều kiện merge. Bot và feature không làm các việc này (agent không thao tác dữ liệu thật). Số liệu dưới đây là ảnh chụp ngày 2026-11-12 trên site `miyano`; chạy lại câu kiểm để biết trạng thái hiện tại. Trên lần kiểm 2026-11-13, số role của tài khoản agent vẫn là 99, tức chưa làm việc nào.

Các câu kiểm chạy trong cửa sổ MariaDB của site: `cd /home/miyano/frappe-bench && bench --site miyano mariadb`, rồi dán từng câu (tên bảng có khoảng trắng phải đặt trong dấu backtick).

1. **Gỡ role thừa của tài khoản agent.** Tài khoản `ai.agent@miyano.com.vn` đang có 99 role, trong đó có `System Manager`; chỉ được giữ `ERP AI Agent` và `Agent`. Gỡ trên form User (`/app/user/ai.agent@miyano.com.vn`). Kiểm:
   ```sql
   SELECT COUNT(*) FROM `tabHas Role` WHERE parenttype='User' AND parent='ai.agent@miyano.com.vn';
   ```
   Kết quả mong đợi: `2`.
2. **Tắt hoặc xóa SLA rác `SLA Priority`.** Đây là bản ghi rác từ test của Helpdesk: đang bật, `condition` bắt phiếu `High`/`Urgent`/`Low`, dùng lịch nghỉ `Test Holiday List`. Nếu không dùng, bỏ luôn `Test Holiday List` và `_Test Holiday List`. Nếu để nguyên, phiếu bot đặt `High`/`Urgent`/`Low` có thể nhận SLA này thay cho `Standard`. Kiểm:
   ```sql
   SELECT name FROM `tabHD Service Level Agreement` WHERE enabled=1;
   ```
   Mong đợi: chỉ `Standard` và SLA do người tạo.
3. **Sửa team trỏ tới Assignment Rule đã mất.** Team `IT` và `Nhân sự & Hành chính` đang trỏ tới Assignment Rule không còn tồn tại. Tạo lại rule hoặc bỏ link trên form HD Team. Nếu không sửa, lần lưu phiếu đổi sang hai team này có thể lỗi và bot dừng bước định tuyến (phiếu không đổi, 0 ToDo, 0 Task). Kiểm:
   ```sql
   SELECT t.name FROM `tabHD Team` t LEFT JOIN `tabAssignment Rule` r ON r.name=t.assignment_rule WHERE t.assignment_rule IS NOT NULL AND t.assignment_rule<>'' AND r.name IS NULL;
   ```
   Mong đợi: 0 dòng.
4. **Tạo HD Agent đang hoạt động cho mọi người sẽ ghi vào bảng người.** Site có 0 HD Agent. Không có HD Agent, bot không gán ai và mỗi phiếu nhận một comment nhờ trưởng nhóm phân công. Kiểm:
   ```sql
   SELECT COUNT(*) FROM `tabHD Agent` WHERE is_active=1;
   ```
   Mong đợi: không ít hơn số người trong bảng.
5. **Điền `routing_rules` trên `/app/erp-ai-setting`.** Người mặc định cho từng đầu mục A, B, C và F (cả F: nếu để trống, mỗi phiếu F nhận một comment nhờ phân công); tiền tố tiêu đề nếu cần (ví dụ `"[tracecore]": "<user ID>"` ở đầu mục A); bảng `departments` cho D/E (`"<bộ phận>": {"team": "<HD Team>", "head": "<user ID trưởng bộ phận>"}`). Tạo team cho bộ phận còn thiếu (ví dụ `Tài chính Kế toán` chưa có) hoặc bỏ bộ phận đó khỏi bảng; bộ phận trỏ tới nhóm không tồn tại thì bot không ghi nhóm và nhật ký ghi lý do. Người điền phải là user có thật (lưu sẽ báo lỗi kèm đường dẫn khóa sai nếu không). Không điền tài khoản agent: bot không bao giờ gán tài khoản này. Kiểm: lưu `ERP AI Setting` không báo lỗi.
5b. **(Tùy chọn, CHG-011, CHG-014) Điền bảng "Gán người theo tag"** ngay trên ô `routing_rules`. Bảng này vừa là **danh sách tag** của phiếu, vừa là bảng chia việc. Mỗi dòng: **Tag** (gõ tên tự do, ví dụ `chấm công`, `tracecore`, `kế toán`, `hr`; 2 đến 40 ký tự, không dấu phẩy; không cần tạo Tag trước), **Mô tả** (việc nào thuộc tag này, ví dụ "chấm công, bảng công, đi muộn, nghỉ phép"), một HD Agent, đầu mục (để trống là mọi đầu mục). Cách bot dùng bảng:
   - Mỗi phiếu mới nhận **đúng một tag** của bảng: lúc phân loại, bot đọc các dòng "tag: mô tả" và chọn tag có mô tả hợp nhất. Không tag nào hợp thì phiếu không có tag. Bot không đặt tag ngoài bảng và không còn gắn tên phân hệ (Accounts, Stock…) hay nhãn chủ đề.
   - Lần đầu bot gắn một tag, Tag đó được tạo tự động.
   - Một tag có nhiều dòng (khác đầu mục) thì bot đọc mô tả ở dòng đầu tiên của tag. Mô tả nói về loại việc, không nêu tên người.
   - Phiếu đã có tag do HD Agent gắn thì bot không gắn tag của mình; tag do người tạo phiếu tự gắn không được tính (Frappe cho người tạo phiếu gắn tag lên phiếu của mình).
   - Gán người: bot đọc bảng **từ trên xuống**; dòng đầu tiên có tag của phiếu và đầu mục để trống hoặc đúng đầu mục của phiếu quyết người nhận phiếu và Task C/D (cần bật `auto_assign_enabled`). Dòng để trống đầu mục áp cả cho D/E, tức thắng trưởng bộ phận; muốn dòng của một đầu mục thắng dòng để trống cùng tag thì đặt nó lên trên.
   - Người trong dòng không còn là HD Agent đang hoạt động thì bot bỏ qua dòng đó, ghi lý do vào nhật ký, rồi xét dòng tiếp theo; không dòng nào cho được người thì dùng `routing_rules` như cũ.
   - Comment định tuyến ghi "Bot đã gắn nhãn: Y." và "Đã gán cho X (theo tag Y)."; trong `ERP AI Log`, hành động `assign_owner` có `rule` là `tag:Y`.
   - Phiếu cũ đang mang nhiều tag (từ trước CHG-014) giữ nguyên.
   - Site đã điền bảng từ trước CHG-014: lần `migrate` lên CHG-014 tự điền Mô tả cho dòng còn trống, lấy từ Mô tả của bản ghi Tag, không có thì lấy chính tên tag. Nên xem lại và viết Mô tả rõ hơn; Mô tả trên bản ghi Tag không còn được dùng.
   - Kiểm: lưu `ERP AI Setting` không báo lỗi (tên tag sai luật, thiếu mô tả, dòng trùng tag và đầu mục, hoặc dòng chọn tài khoản agent bị chặn).
5c. **(Nên làm, CHG-015) Chọn "Người nhận mặc định"** ngay dưới ô `routing_rules`: một HD Agent nhận phiếu chưa có người được giao khi bảng "Gán người theo tag" và `routing_rules` không cho được người (kể cả khi người ở đó đã nghỉ hoặc không còn là HD Agent đang hoạt động). Người này nhận luôn Task C/D; comment định tuyến ghi "Đã gán cho X (người nhận mặc định)."; trong `ERP AI Log`, `assign_owner` có `rule` là `default`. Phiếu đã có người được giao thì bot không đổi. Để trống thì như cũ: bot đăng comment nhờ trưởng nhóm phân công. Không chọn được tài khoản agent.
6. **Xem lại `excluded_teams`.** Site đang để rỗng, khác mặc định (`Nhân sự & Hành chính`, `Tài chính Kế toán`). Phiếu thuộc nhóm trong danh sách này không gửi lên API và bot không chọn nhóm đó. Kiểm:
   ```sql
   SELECT value FROM tabSingles WHERE doctype='ERP AI Setting' AND field='excluded_teams';
   ```
7. **Tắt Assignment Rule của nhóm nào muốn dùng bảng người mặc định.** Nhóm có Assignment Rule đang bật và có người thì rule gán ngay lúc bot lưu nhóm, bot thấy phiếu đã có người nên không gán (nhật ký ghi tên rule). `Billing` và `Product Experts` đang có rule bật (0 người). Kiểm:
   ```sql
   SELECT name, disabled FROM `tabAssignment Rule`;
   ```
8. **Sau cùng mới tích `auto_assign_enabled`.** Site đang ở mức `L3`, nên công tắc này là chốt chặn duy nhất của việc gán người và tạo Task. Sau khi bật, theo dõi vài phiếu đầu: một người được gán, một thông báo, Task cho C/D, `actions` trong `ERP AI Log`.

Hoàn tác không cần deploy: bỏ tích `auto_assign_enabled` thì phiếu mới không sinh thêm ToDo hay Task. Dấu hiệu nên tắt: nhật ký có `route apply_route:` lặp lại trên nhiều phiếu; có phiếu bị gán hai người; có Task không người được giao.

## 3. Viết `condition` của SLA theo độ phức tạp

Helpdesk chọn SLA mỗi lần lưu phiếu, theo `priority` và `condition` của SLA. `condition` đọc được `doc.ai_complexity`. Phiếu mới (chưa chấm) và phiếu ở `L0` có `ai_complexity = 0`, nên `condition` phải đúng cả khi giá trị là 0.

Mẫu an toàn (đã chạy trong test AC-10, phiếu mới và `L0` vẫn lưu được):
- `doc.ai_complexity == 3`
- `doc.ai_complexity >= 3`

Mẫu cần cẩn thận:
- `doc.ai_complexity < 3` và `doc.ai_complexity == 0` cũng khớp phiếu chưa chấm (điểm 0). Muốn khớp độ phức tạp 1 hoặc 2, viết `doc.ai_complexity in (1, 2)`.
- Nên luôn có một SLA mặc định (không `condition`) cho phiếu chưa chấm và phiếu không khớp.

Cảnh báo:
- Một `condition` gây lỗi khi Helpdesk đánh giá sẽ chặn MỌI lần lưu phiếu mà SLA đó đang bật, của cả người lẫn bot. Với bot: lần định tuyến dừng sạch (phiếu không đổi, 0 ToDo, 0 Task, 0 comment định tuyến, nhật ký có tên lớp lỗi), nhưng người dùng cũng không lưu được phiếu cho tới khi `condition` được sửa hoặc SLA bị tắt.
- Trước khi bật SLA mới có `condition`, lưu thử một phiếu mới và một phiếu có sẵn; nếu báo lỗi thì tắt SLA đó ngay.
- Bot chỉ báo SLA, không tạo hay sửa: không có SLA áp vào phiếu thì một comment "Chưa có SLA áp vào phiếu, cần System Manager cấu hình."; SLA đang áp xử lý chậm hơn `expected_sla` của đầu mục thì một dòng cảnh báo trong `actions` (`sla_check`). Đầu mục D, E không bị kiểm chậm.

## 4. Giới hạn đã biết

- Quay về code trước CHG-011 sau khi đã `migrate` (bảng `ERP AI Tag Assignee` đã có trên site): code cũ không import được bảng con, mọi lần đọc `ERP AI Setting` báo ImportError. Muốn quay về thì phải xóa trường `tag_assignees` khỏi meta của `ERP AI Setting` (reload DocType từ code cũ) hoặc giữ module `erp_ai_tag_assignee`.
- Model phân loại: chỉ `claude-haiku-*` được tắt thinking ở bước phân loại. Model khác có thể bị cắt ở trần 600 token (phiếu thành "không phân loại được"). Chạy eval (`README.md`, "Bộ đánh giá offline") và đọc dòng `Classify max_tokens hits`; khác 0 là phải xem lại model.
- Hiếm khi một lỗi xảy ra sau bước thông báo gán của Helpdesk, người nhận có thể thấy thông báo gán cho một ToDo đã bị hoàn tác. Không mất dữ liệu; nếu gặp, báo cho team kỹ thuật.
- Eval chỉ báo số, không đặt ngưỡng cho khớp ưu tiên và khớp nhóm. Lần đo ngày 2026-11-13 chỉ có 2 phiếu gán nhãn, cùng đầu mục B, nên chưa đủ để kết luận độ đúng chung.
