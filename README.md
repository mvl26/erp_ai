### ERP AI agent

Agent AI hỗ trợ công việc trên ERP Miyano. Giai đoạn 1: Helpdesk. Agent đọc phiếu mới (và comment có từ khóa), phân loại vào 1 trong 6 đầu mục A–F, chấm độ phức tạp và độ quan trọng, và ở mức `L1` ghi hướng giải quyết, comment trên phiếu. App cài xong ở trạng thái **tắt**.

Phạm vi mặc định: mức `L0` và `L1`. Mức `L2`/`L3` chọn được trên form; khi hai công tắc "Sửa code và lệnh bench" và "Toàn quyền (khẩn cấp)" đều tắt (mặc định) chúng chỉ cấp đúng bộ tool của `L1`. Hai công tắc đó mở thêm tool, xem mục "Sửa code, lệnh bench và ghi bản ghi trực tiếp".

| Mức | Agent làm gì |
|---|---|
| `L0` (shadow) | Chỉ chạy bước phân loại, ghi dự đoán (đầu mục, nhóm, ưu tiên, hai điểm, người dự kiến) vào `ERP AI Log`, không đổi phiếu. Comment có từ khóa được ghi nhật ký "bỏ qua do L0", không gọi API |
| `L1` | Ghi loại phiếu, nhóm, ưu tiên (tính từ hai điểm, xem mục "Định tuyến theo điểm"), độ tin cậy, hai điểm và lý do chấm, hướng giải quyết, comment; tạo Task khi có người có role `ERP AI Instructor` ra lệnh. Khi công tắc `auto_assign_enabled` bật (tắt sẵn): gán người phụ trách và tạo Task cho đầu mục C/D. Không đổi `status`, không ghi đè phân loại do người đã đặt, không giành phiếu đã có người được gán |

Khi vượt ngân sách tháng, mức hiệu lực lui về `L1` (không bao giờ nâng `L0` lên `L1`).

### Yêu cầu

- Frappe `>=15.126.1,<16.0.0`, Helpdesk 15.1.0 trở lên (comment phiếu là core `Comment`; bản Helpdesk cũ hơn sẽ không kích hoạt được bằng comment).
- Thư viện `anthropic>=0.103.1,<1` (khai trong `pyproject.toml`).
- Khóa API Anthropic loại workspace chuẩn (`sk-ant-api03-`), nhập trên form cấu hình.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench --site <site> install-app erp_ai
bench --site <site> migrate
```

Cài và migrate (chạy lại được, không ghi đè cấu hình đã lưu) tạo: role `ERP AI Agent` và `ERP AI Instructor`; tài khoản `ai.agent@miyano.com.vn` chỉ có role `ERP AI Agent` và `Agent` (không có System Manager); các trường AI trên HD Ticket (permlevel 8, ẩn với khách), gồm ba trường điểm `ai_complexity`, `ai_importance`, `ai_score_reason`; trường `ai_ticket` trên Task và quyền `share` cho dòng quyền Task của app; `ERP AI Setting` ở trạng thái tắt, mức `L0`, công tắc `auto_assign_enabled` tắt, hai công tắc `code_change_enabled` và `unrestricted_enabled` tắt; DocType `ERP AI Change Proposal`; bản ghi HD Form Script `ERP AI Agent Status` (xem mục "Chỉ báo trạng thái trên trang phiếu").

### Cấu hình và bật

Mở `/app/erp-ai-setting` (chỉ System Manager). Mỗi field trên các form `ERP AI Setting`, `ERP AI Credential` và `ERP AI Log` có mô tả ngay dưới ô nhập (đơn vị, khoảng hợp lệ, ví dụ, field nào do hệ thống tự ghi), và form chia thành các nhóm có tiêu đề.

1. Thêm khóa API ở bảng khóa; bấm "Kiểm tra khóa" để thử từng khóa.
2. Đặt `monthly_budget_usd` (mặc định 10), bốn đơn giá token (mặc định 0; phải > 0 mới bật được) và model (không có giá trị nào viết cứng trong mã). Model phân loại nên là `claude-haiku-*`: chỉ với model này bước phân loại tắt thinking; model khác không được tắt thinking và có thể bị cắt ở trần token.
3. Rà các giá trị mặc định: `excluded_teams` (mặc định "Nhân sự & Hành chính" và "Tài chính Kế toán", mỗi nhóm một dòng: phiếu các nhóm này và phiếu có cờ "không dùng AI" không bao giờ được gửi lên API), `trigger_keyword` (mặc định `@ai`), `category_mapping` (đầu mục A–F sang loại phiếu, nhóm và ưu tiên mặc định của đầu mục; ưu tiên cuối cùng của phiếu còn phụ thuộc hai điểm và bảng `importance_priority` trong `routing_rules`, không chỉ ánh xạ này), `routing_rules` (mục "Định tuyến theo điểm"), `alert_recipients` (mặc định `info@miyano.com.vn`).
4. Giữ `L0` đủ lâu để đo độ chính xác (báo cáo `ERP AI Accuracy`), rồi mới tích `enabled` và chuyển `L1`.
5. Công tắc `auto_assign_enabled` ("Tự gán người và tạo Task") để tắt cho tới khi xong các việc chuẩn bị trong `docs/HuongDan_QuanTri_DinhTuyen.md`.
6. Hai công tắc `code_change_enabled` và `unrestricted_enabled` để tắt, trừ khi đã đọc mục "Sửa code, lệnh bench và ghi bản ghi trực tiếp".

Cấp role `ERP AI Instructor` cho người được phép ra lệnh agent trên mọi phiếu; người được giao phiếu chỉ có thẩm quyền trên đúng phiếu đó. Không cấp role này cho tài khoản agent.

Chi tiết các việc phải làm trước khi bật: `docs/team/features/FEAT-001/asbuilt.md`, mục 6.

### Sửa code, lệnh bench và ghi bản ghi trực tiếp

Hai công tắc trên `/app/erp-ai-setting`, chỉ System Manager đặt được, mặc định tắt. Cả hai tắt thì danh sách tool và prompt giống bản trước. Bot không đọc, không ghi được hai ô này, `ERP AI Credential`, `ERP AI Log` và `ERP AI Change Proposal` ở mọi chế độ.

| Công tắc | Điều kiện | Bot làm được |
|---|---|---|
| `code_change_enabled` ("Cho phép sửa code và lệnh bench") | mức `L3`, có người có role `ERP AI Instructor` ra lệnh | (1) Ghi bản ghi trực tiếp, không qua duyệt, theo quyền của tài khoản agent: `api_list_records`, `api_get_record`, `api_create_record`, `api_update_record` (tạo User, gán vai trò nghiệp vụ, sửa cấu hình, bản ghi nháp). Vẫn bị từ chối: gán `System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All`; sửa `Administrator`, `Guest`, tài khoản agent; ghi Role Permission, Custom DocPerm; xóa, submit, hủy. (2) Đề xuất sửa file trong app của `code_change_apps` hoặc chạy một lệnh `bench` trong danh sách `migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build`, `version`; mọi thay đổi code và lệnh phải được người duyệt |
| `unrestricted_enabled` ("Toàn quyền (khẩn cấp)") | từ `L1`, có người ra lệnh, không cần công tắc code | Thêm `api_delete_record`, `api_submit_record`, `api_call_method` (hàm whitelist) và bỏ giới hạn vai trò, tài khoản, DocType ở trên: gán được cả `System Manager`, sửa được phân quyền và mọi tài khoản. Không có hẹn giờ tự tắt và không có cảnh báo khi đang bật: xong việc thì tắt tay. Xóa và submit không hoàn tác được |

`code_change_apps`: mỗi dòng một tên thư mục app trong `apps/`; thêm được `frappe`, `erpnext`, `helpdesk`, `hrms` (sửa app lõi ảnh hưởng mọi site trên bench); không bao giờ `erp_ai`; để trống thì không file nào được sửa. Giới hạn đã biết: bot chỉ chặn ở mức cố gắng việc đọc mật khẩu và khóa API của người dùng qua `api_call_method`; chi tiết ở `docs/team/features/FEAT-004/asbuilt.md`.

**Duyệt.** Khi bot đề xuất, nó đăng một comment trên phiếu: mã đề xuất, loại, đích (file hoặc lệnh), nhánh nhận commit, cảnh báo app lõi, ghi chú cần `bench restart` (file `.py`) hoặc "lệnh bench không hoàn tác được", rồi ba liên kết "Duyệt", "Từ chối", "Xem nội dung thay đổi". Chỉ người có role `ERP AI Instructor` và vào được Desk duyệt được; tài khoản agent, `Administrator`, `Guest` bị từ chối. Mở liên kết "Duyệt" mở form Desk của đề xuất; form gửi đúng một lời gọi POST, không hộp xác nhận, rồi người bấm ở lại form và thấy diff và trạng thái mới. Chữ "ok" hay "duyệt" trong phiếu không phải là duyệt. Trên form `ERP AI Change Proposal` vẫn có ba nút Duyệt, Từ chối, Hoàn tác (có hộp xác nhận).

**Áp dụng và hoàn tác.** Một thay đổi file được áp dụng thành đúng một commit git local trên nhánh đang checkout; bot không push, không đổi nhánh, không chạy hook của repo. Hoàn tác (nút trên form) là một commit hoàn tác và bị từ chối nếu file đã đổi sau đó. Sau mỗi kết cục có một dòng hoạt động `Info` trên phiếu nêu trạng thái cuối, mã commit hoặc mã thoát hoặc lý do. Mỗi bước có một dòng `ERP AI Log` (`entry_type=change`).

**Tắt.** Đặt `code_change_enabled` và `unrestricted_enabled` về 0: bot trở lại như cũ. Commit bot đã tạo ở lại trong lịch sử git; muốn bỏ thì bấm Hoàn tác trên từng đề xuất trước khi tắt, hoặc `git revert` thủ công. Revert mã của tính năng làm mất DocType `ERP AI Change Proposal` và các bản ghi đề xuất, tức mất dữ liệu kiểm toán.

### Nhật ký trước/sau và cảnh báo phân quyền hằng ngày

Khi bot ghi bản ghi trực tiếp (mục trên), bạn dựng lại được bot đã đổi gì từ nhật ký, và mỗi ngày nhận một thư nếu bot đã đổi role hay phân quyền.

**Đọc trước/sau.** Mở `ERP AI Log`, dòng `reason` của lượt chạy. Cột `actions` liệt kê từng lời gọi (công cụ, DocType, tên bản ghi, đúng hay sai) theo thứ tự; lời gọi thứ `n` có giá trị trước và sau ở hai cột `value_before` và `value_after`, khóa `"<công cụ>#<n>"` (ví dụ `api_update_record#2`), nên hai lời gọi cùng công cụ trong một lượt không đè nhau. Giá trị gồm cả dòng của bảng con: role của User, ngày của Holiday List, trạng thái và hành động của Workflow. Khi bot sửa bằng cách đưa cả danh sách, so trước với sau cho thấy dòng nào bị bỏ và dòng nào được thêm. Giá trị lưu đầy đủ, không cắt. Tạo mới có trước là rỗng; xóa có sau là rỗng. Với User chỉ có mã user và danh sách role; mật khẩu, khóa, token không bao giờ có trong đó. Chỉ System Manager đọc được `ERP AI Log`.

**Hoàn tác bằng tay.** Bot không có công cụ hoàn tác. Đọc giá trị trước, mở bản ghi trong Desk và đặt lại: thêm lại role bị gỡ, bỏ role bị thêm, trả giá trị cũ. Bản ghi bị xóa hay đã submit bằng "Toàn quyền" thì không hoàn tác được.

**Cảnh báo hằng ngày.** Job `check_privilege_escalation` chạy mỗi ngày và gửi một thư tới `alert_recipients` (cùng dòng ở Error Log) với tiêu đề "Agent đã sửa bản ghi phân quyền" khi bot đã thêm hoặc gỡ role của một user, hoặc tạo, sửa, xóa một bản ghi phân quyền (Custom DocPerm, DocPerm, Role, User Permission, Role Profile, hoặc phần `permissions` của một DocType). Mỗi mục nêu việc, user, role, người ra lệnh và thời điểm, ví dụ `thêm role <role> cho <user> (người ra lệnh <người>, <YYYY-MM-DD HH:MM>)` hoặc `gỡ role <role> của <user> (…)`.
- Dòng có role quản trị (`System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All`) có dấu `[QUẢN TRỊ]` ở đầu và đứng trước các dòng khác.
- Thư chỉ liệt kê tối đa 5 mục rồi "…và N mục khác", để thư ngắn; vì dòng quản trị đứng trước nên không bị cắt trước dòng thường. Danh sách đầy đủ tra ở `ERP AI Log`.
- Mục ghi `, không có trước/sau` là thay đổi mà nhật ký không đọc được trước/sau (nhật ký cũ trước khi có tính năng này, hoặc dữ liệu hỏng). Nó vẫn được báo, không bị bỏ qua. Mục `sửa User …, không có trước/sau` không có dấu `[QUẢN TRỊ]` vì không biết role, và có thể nằm trong "…và N mục khác": tra `ERP AI Log`.
- Không cảnh báo: role hay phân quyền do người đổi, và bot lưu lại một User mà không đổi role.
- Ba cảnh báo khác trong cùng job không đổi: role của tài khoản agent lệch tập, Server Script hoặc Webhook do agent tạo đang bật, khóa đang bật nhưng không có giá trị.

**Báo đúng một lần.** Ô chỉ đọc `privilege_alert_checked_until` (nhóm cảnh báo trên `ERP AI Setting`) là mốc "đã báo tới đâu"; chỉ job ghi, form lưu không đổi được. Mỗi lần chạy xét từ mốc tới 5 phút trước giờ chạy, rồi dời mốc: một thay đổi vào đúng một thư; lịch lỡ vài ngày thì lần sau gộp đủ. Lần chạy đầu sau khi cập nhật báo một lần mọi thay đổi cũ của bot (mục `không có trước/sau`), không phải lỗi. Lần chạy lỗi giữa chừng không dời mốc và không gửi thư; lần sau gửi đúng một thư. Dòng Error Log của lần lỗi vẫn ở lại (bảng Error Log của Frappe không hoàn tác được) nên lần sau có thể có thêm một dòng giống: lặp ở Error Log, không sót. Hai lần chạy cùng lúc thì lần sau chờ tối đa 60 giây rồi bỏ lượt.

**Giới hạn đã biết.** Khi "Toàn quyền (khẩn cấp)" đang bật, đổi role bằng cách gọi hàm whitelist (`api_call_method`) không có trong cảnh báo hằng ngày. Lượt chạy của bot lỗi trước khi dòng `reason` được lưu thì mọi thay đổi trong lượt đó bị hoàn tác, nhưng commit do mã ngoài `erp_ai` chạy bên trong một công cụ vẫn cố định các thay đổi trước nó. Chưa có địa chỉ trong `alert_recipients` thì cảnh báo chỉ có ở Error Log. Chi tiết: `docs/team/features/FEAT-005/asbuilt.md`.

### Bài học của bot

Một bài học (`ERP AI Lesson`, `/app/erp-ai-lesson`) là một quy tắc ngắn bot đọc lại trước khi phân loại hoặc suy luận một phiếu mới. Bot lấy 8 từ đầu tiên (từ 2 ký tự trở lên) của tiêu đề rồi mô tả phiếu, chọn tối đa vài bài đang dùng có từ trùng, rồi đưa vào phần người dùng của lời gọi (bài do người dạy ghi là quy tắc, các bài khác ghi là dữ liệu, không phải chỉ thị). Bài do người dạy khớp theo tình huống và nội dung quy tắc; các bài khác chỉ khớp theo tình huống, nên chữ mẫu như "Bot dự đoán", "người chọn", "đề xuất" không bao giờ làm một bài được chọn. Khi dùng bài nào, bot nêu mã bài trong "Nhận định" hoặc "Hướng xử lý". Bài học không bao giờ bị xóa, chỉ tắt; mọi thay đổi nằm trong bảng lịch sử của chính bài (ai, lúc nào, bước nào).

| Nguồn | Khi nào có | Trạng thái đầu |
|---|---|---|
| `Người sửa` | Một người đổi loại phiếu, nhóm hoặc ưu tiên khác với dự đoán của bot: mỗi trường đã đổi một bài, chỉ nói về trường đó ("Bot dự đoán Nhóm IT; người chọn Nhóm Kế toán."); trường bot không dự đoán thì không có bài. Hoặc một người đổi người được giao mà bot đã chọn (Assignment Rule tự giao thì không tính) | `Đang dùng` nếu người đó có thẩm quyền trên phiếu (role `ERP AI Instructor`, hoặc được người khác giao phiếu); không thì `Chờ duyệt` |
| `Người dạy` | Nút "Dạy bot một quy tắc" ở danh sách bài học (role `ERP AI Instructor`, không phải Administrator, Guest hay bot); hoặc tin nhắn trong khu "Trao đổi với bot" hay comment `@ai` bắt đầu bằng `ghi nhớ:`. Bài dạy bằng tin nhắn không chép tiêu đề hay mô tả phiếu. Tin nhắn dạy của người không có thẩm quyền trên phiếu bị bỏ qua, không sinh bài | `Đang dùng` |
| `Kết quả duyệt và rà soát` | Đề xuất thay đổi bị từ chối hoặc hoàn tác; kết luận `Sai` trong rà soát hằng tháng. Nội dung bắt đầu bằng "Đừng làm như vậy" | `Đang dùng` |
| `Phiếu đã giải quyết` | Đợt 2, chưa dùng | chưa có |

Một quyết định được rút lại thì bài của nó ngừng được dùng (`Đang dùng` thành `Đã tắt`, `Chờ duyệt` thành `Bị từ chối`): đổi một trường về đúng giá trị bot đã dự đoán, đổi kết luận `Sai` của rà soát tháng sang giá trị khác, hoặc giao phiếu lại đúng người bot đã chọn. Bài `Bị từ chối` là cuối cùng: lần sửa sau của cùng trường (hoặc người được giao) trên cùng phiếu không cập nhật hay dùng lại bài đó. Phiếu thuộc nhóm loại trừ hoặc có cờ "không dùng AI" không bao giờ sinh bài học; bài của một phiếu sau này thành loại trừ không được gửi cho bot. Khóa, mật khẩu trong nội dung bị che trước khi lưu.

**Duyệt và tắt.** Duyệt hoặc từ chối bài `Chờ duyệt`: người trong `monthly_reviewers` và System Manager. Tắt hoặc bật lại: role `ERP AI Instructor`. Nút "Các lần dùng" trên form mở các dòng `ERP AI Log` đã gửi bài đó; ở mỗi dòng log, trường `lessons_used` liệt kê các bài bước đó đã gửi. Bộ đánh giá offline không bao giờ dùng bài học.

**Cài đặt.** Mục "Bài học của bot" trên `/app/erp-ai-setting`:

| Ô | Mặc định | Ý nghĩa |
|---|---|---|
| `lessons_enabled` | bật | Tắt thì bot không gửi và không ghi bài học mới |
| `lessons_max_per_request` | 5 (1 đến 20) | Số bài tối đa mỗi lời gọi |
| `lessons_max_chars` | 2000 (1300 đến 20000) | Tổng số ký tự bài học mỗi lời gọi; mức thấp nhất vẫn chứa được một bài dài nhất (300 + 1000 ký tự) |
| `lesson_teach_marker` | `ghi nhớ:` | Từ khóa dạy bằng tin nhắn; để trống thì tắt dạy bằng tin nhắn |

Bot chỉ xét 500 bài đang dùng mới nhất.

**Đợt 2 (sau này).** Bài do bot tự soạn từ phiếu đã đóng (chờ duyệt), bản tóm tắt hằng tháng kèm đề xuất cải tiến, báo cáo mức dùng bài học và độ chính xác khi có và không có bài học.

### Định tuyến theo điểm

Mỗi phiếu mới được chấm hai điểm 1–3 trong cùng lời gọi phân loại: độ phức tạp (1: dưới 1 giờ làm việc; 2: trong 1 ngày; 3: nhiều ngày, cần phân tích hoặc xây mới) và độ quan trọng (1: ảnh hưởng một người, không chặn việc; 2: chặn việc của một người hoặc bộ phận, hoặc có hạn trong 24 giờ; 3: chặn nghiệp vụ kế toán, kho, bán hàng hoặc nhiều bộ phận). Điểm có ở `ERP AI Log` (các cột `predicted_complexity`, `predicted_importance`, `predicted_score_reason`) ở mọi mức; từ `L1` có thêm trên phiếu ở ba trường chỉ đọc `ai_complexity`, `ai_importance`, `ai_score_reason`, HD Agent (role `Agent`) đọc được. Điểm 0 nghĩa là chưa chấm hoặc model trả điểm sai; ưu tiên khi đó theo `category_mapping`.

**Mức ưu tiên** (từ `L1`), xét lần lượt, quy tắc nào khớp trước thì dừng:

| Điều kiện | Ưu tiên |
|---|---|
| Tiêu đề có `[GẤP]` hoặc `[GẬP]` | `Urgent` |
| Đầu mục F | `Low` |
| Đầu mục E | Bot không ghi ưu tiên (COO đặt) |
| Đầu mục A và độ quan trọng 3 | `Urgent` |
| Còn lại | Mức cao hơn giữa ưu tiên của đầu mục trong `category_mapping` và mức theo độ quan trọng trong `importance_priority` (mặc định: 2 và 3 là `High`, 1 không nâng) |

Độ phức tạp không đổi mức ưu tiên; nó dành cho `condition` của SLA. Sửa `importance_priority` là lần chạy sau dùng giá trị mới, không cần deploy. Đặt `{"1": "", "2": "", "3": ""}` để quay về ưu tiên theo ánh xạ đầu mục.

**Nhóm.** A, B, C, F lấy nhóm trong `category_mapping`. D và E lấy nhóm của bộ phận model chọn, chỉ khi bộ phận có trong bảng `departments`, nhóm có tồn tại và không nằm trong `excluded_teams`; không thì bot không ghi nhóm và `ERP AI Log` ghi lý do.

**Cấu hình `routing_rules`** (một trường JSON trên `ERP AI Setting`; sai dạng thì không lưu được, thông báo nêu chỗ sai):

| Khóa | Nội dung |
|---|---|
| `assignees` | Đầu mục A, B, C, F: `default` (user ID người mặc định) và `prefixes` (tiền tố tiêu đề, ví dụ `[tracecore]`, sang user ID). Danh sách người để trống khi cài |
| `departments` | Cho D/E: `"<bộ phận>": {"team": "<HD Team>", "head": "<user ID trưởng bộ phận>"}` |
| `importance_priority` | Độ quan trọng "1", "2", "3" sang `Low`/`Medium`/`High`/`Urgent` hoặc rỗng (mức tối thiểu) |
| `expected_sla` | Mỗi đầu mục `response_min` và `resolution_min` (phút, hoặc `null` thì không kiểm); mặc định theo bảng 16.2 (A 15/480, B 15/240, C 60/1440, D và E 60/null, F 5/60) |

**Gán người và Task** (chỉ khi công tắc `auto_assign_enabled` bật, từ `L1`): bot gán đúng một người theo `assignees` (tiền tố tiêu đề được ưu tiên hơn `default`; D/E dùng trưởng bộ phận) bằng cơ chế gán của Helpdesk, người đó nhận một thông báo. Bot không gán khi: phiếu đã có người được gán (kể cả Assignment Rule của nhóm gán ngay lúc bot lưu nhóm; muốn dùng bảng người mặc định cho nhóm nào thì tắt rule của nhóm đó); người trong bảng không phải HD Agent đang hoạt động; người đó là tài khoản agent (không bao giờ); người đã phân loại phiếu. Không có người hợp lệ: một comment nhờ trưởng nhóm phân công. Đầu mục C/D, khi chính bot vừa gán được người: một Task có trường `ai_ticket` trỏ tới phiếu, giao cho người đó; chạy lại hoặc đã có Task liên kết thì không tạo thêm. Site tắt chia sẻ tài liệu mà người đó không đọc được Task: không Task, một comment nhờ trưởng nhóm giao Task. Mọi lần ghi và từ chối nằm ở cột `actions` của bản ghi `classify` trong `ERP AI Log`.

**SLA.** Bot không tạo, sửa SLA và không tự gán `response_by`, `resolution_by`; Helpdesk chọn và tính SLA mỗi lần lưu phiếu. Bot báo: phiếu không có SLA nào áp vào thì một comment "Chưa có SLA áp vào phiếu, cần System Manager cấu hình." và một dòng cảnh báo; SLA đang áp xử lý chậm hơn `expected_sla` thì một dòng cảnh báo (`sla_check` trong `actions`). Muốn SLA khác nhau theo độ phức tạp, tạo SLA với `condition` đọc `doc.ai_complexity`; mẫu an toàn và cảnh báo ở `docs/HuongDan_QuanTri_DinhTuyen.md`, mục 3. Một `condition` lỗi chặn mọi lần lưu phiếu, của cả người lẫn bot.

**Trước khi bật công tắc** làm các việc ở `docs/HuongDan_QuanTri_DinhTuyen.md`, mục 2 (gỡ role thừa của tài khoản agent, tắt SLA test, sửa team trỏ Assignment Rule đã mất, tạo HD Agent, điền người cho từng đầu mục kể cả F). Chi tiết thiết kế và các giới hạn đã biết: `docs/team/features/FEAT-006/asbuilt.md`.

### Chỉ báo trạng thái trên trang phiếu

Khi agent đang chạy (comment có từ khóa `@ai`, hoặc phiếu mới), trang phiếu của HD Agent hiện một chỉ báo nổi ở góc dưới phải, kèm tên tài khoản agent: `Đang suy nghĩ…`, đổi thành `Đang làm: <việc>…` khi agent chạy một tool, rồi tự mất khi lần chạy kết thúc (kể cả lỗi). Các nhãn việc: đọc phiếu, đọc comment, tìm phiếu đã giải quyết, tra bản ghi, tra mã nguồn, đọc mã nguồn, xem lịch sử mã nguồn, ghi phân loại, ghi hướng giải quyết, viết trả lời, tạo task, phân loại phiếu. Chỉ báo không tạo comment hay bản ghi nào và không hiện trên cổng khách. Cần tiến trình `socketio` của bench; thiếu nó thì chỉ báo không hiện, lần chạy vẫn bình thường.

Ba trường trên `/app/erp-ai-setting`:

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `thinking_text` | `Đang suy nghĩ…` | Chữ hiện khi agent đang suy nghĩ (tối đa 5000 ký tự). Để trống để tắt chỉ báo |
| `answer_delay_min_s` | `3` | Trễ tối thiểu (giây, 0 đến 30) trước khi đăng câu trả lời đầu tiên của `@ai` |
| `answer_delay_max_s` | `5` | Trễ tối đa (giây, 0 đến 30, không nhỏ hơn mức tối thiểu) |

Trễ được tính từ lúc chỉ báo bắt đầu (thời gian model chạy được trừ vào), và không áp dụng cho phiếu mới. Đặt `0` và `0` để không trễ.

**Cảnh báo:** chỉ báo chạy bằng bản ghi HD Form Script `ERP AI Agent Status`, nội dung lấy từ `erp_ai/public/js/agent_status_indicator.js`. Mỗi lần `bench --site <site> migrate` (và `install-app`) đặt lại bản ghi này theo tệp trong repo, nên mọi sửa tay trên site bị ghi đè; gỡ app thì bản ghi bị xóa. Sửa tệp `.js` xong phải chạy `migrate`, restart là không đủ. Sau mỗi lần nâng cấp Helpdesk hoặc Frappe, kiểm lại chỉ báo bằng tay: các bước ở `docs/team/features/FEAT-002/acceptance.md`, mục "Bước tay cho người".

### Khu vực trao đổi với bot trên trang phiếu

Khu vực "Hướng giải quyết & trao đổi với bot" cho HD Agent đọc hướng giải quyết của AI, xem các lần hỏi–đáp với bot và hỏi bot ngay trên trang phiếu, không phải nhớ từ khóa. Chạy bằng cùng bản ghi HD Form Script `ERP AI Agent Status` ở mục trên (cùng cảnh báo: sửa `.js` xong phải `migrate`).

**Mở khu vực.** Mở phiếu ở `/helpdesk/tickets/<id>` trên máy tính (cửa sổ rộng từ 640 px), bấm nút "Trao đổi với bot" ở đầu trang. Một ngăn hiện bên phải, bấm "Đóng" để đóng. Nút không có trên cửa sổ hẹp hoặc bản di động, và không có trên cổng khách (`/helpdesk/my-tickets/<id>`).

**Trong khu vực có:**
- 4 mục AI chỉ đọc: hướng giải quyết, độ tin cậy, phân loại bởi, AI cập nhật lúc. Mục chưa có giá trị hiện "Chưa có". Không sửa được ở đây.
- Luồng tin: các comment có từ khóa kích hoạt và các comment của bot trên phiếu này, cũ ở trên, mới ở dưới; tin của bot có nhãn "Bot". Nội dung hiện dạng chữ thuần.
- Chỉ báo "Đang suy nghĩ…" khi bot đang chạy (nằm trong ngăn khi ngăn mở).

**Gửi câu hỏi.** Gõ câu hỏi vào ô nhập rồi nhấn Enter (hoặc bấm "Gửi"); Shift+Enter để xuống dòng. Không cần gõ từ khóa: hệ thống tự thêm từ khóa kích hoạt vào cuối tin nếu bạn chưa gõ. Tin dài tối đa 2000 ký tự, không gửi được tin rỗng. Tin gửi đi là một comment bình thường của chính bạn trên phiếu (hiện cả ở tab Comments), chữ như `<b>` được hiện nguyên chữ chứ không thành định dạng. Gửi thất bại (mất mạng, hết quyền) thì ngăn báo "Không gửi được tin" và giữ nguyên chữ bạn đã gõ. Khu vực tự cập nhật khi có comment mới hoặc khi bot đổi field AI, không cần tải lại trang.

**Khi nào bot không trả lời.** Gửi tin chỉ tạo comment; việc bot có trả lời hay không do cùng các chốt như khi gõ từ khóa ở tab Comments, và khu vực không tự báo lý do. Bot có thể không trả lời khi: agent đang tắt; mức đang là `L0` (chỉ ghi nhận); phiếu có cờ "không dùng AI" hoặc thuộc nhóm loại trừ; hoặc đã hết lượt hôm nay (xem `ERP AI Log` để biết lý do bỏ qua). Ngăn cũng hiện dòng nhắc này. Nếu quản trị đặt `trigger_keyword` có ký tự `<`, `>` hoặc `&`, khu vực từ chối gửi và báo quản trị viên đổi từ khóa (ô Comments cũng không kích hoạt được bot với từ khóa đó).

**Quyền.** Chỉ HD Agent đang hoạt động và có quyền đọc phiếu dùng được khu vực. Khu vực chỉ đọc và chỉ gửi qua hai method `erp_ai.ticket_panel.get_panel_data` và `erp_ai.ticket_panel.send_message` (POST, không cho Guest); không bao giờ hiện từ khóa hay cấu hình agent, không sửa hay xóa tin, không đính kèm, không nhắc tên.

**Sau mỗi lần nâng cấp Helpdesk hoặc Frappe**, chạy lại bằng tay hai bước ở `docs/team/features/FEAT-003/acceptance.md`, mục "Bước tay J1 cho người": J1 AC-6 (nút, tiêu đề, gửi bằng Enter, các tab cũ vẫn chạy) và J1 AC-11 (cập nhật trực tiếp bằng hai phiên, chỉ báo chỉ một nơi). Khu vực dựa vào điểm mở rộng `actions` của HD Form Script và hai sự kiện `docinfo_update`, `doc_update` của Frappe; nâng cấp có thể làm chúng đổi.

### Bộ đánh giá offline

Đo độ chính xác phân loại trên phiếu đã gán nhãn người, trước khi bật agent. Phiếu nhóm loại trừ không được xuất.

```bash
bench --site <site> execute erp_ai.eval.export_tickets.export --args '["<đường dẫn .jsonl ngoài repo>"]'
bench --site <site> execute erp_ai.eval.run_eval.run --args '["<đường dẫn .jsonl>"]'
```

`export` từ chối đường dẫn nằm trong repo. `run` gửi nội dung lên API bằng cùng prompt với agent thật và in: độ chính xác tổng, theo từng đầu mục, ma trận nhầm lẫn 6×6, độ chính xác trên phiếu không do người viết nhiều nhất tạo, tỷ lệ khớp ưu tiên và khớp nhóm so với giá trị người đã đặt, phân bố hai điểm, token đầu ra lớn nhất của bước phân loại, số lần bị cắt ở `max_tokens` (`Classify max_tokens hits`), và kết luận (≥ 85% / 70–85% / < 70%). Số lần bị cắt khác 0 nghĩa là trần token đang chạm: kiểm model phân loại (mục "Cấu hình và bật", bước 2).

### Running tests

```bash
cd $PATH_TO_YOUR_BENCH
bench --site <site> run-tests --app erp_ai
```

Site phải bật `allow_tests`. Test không gọi mạng thật (lời gọi model được thay bằng stub). Không đặt file test tên `test_runner.py`: Frappe bỏ qua tên này (test kiến trúc kiểm điều đó).

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erp_ai
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
