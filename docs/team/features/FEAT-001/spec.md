Feature: FEAT-001
Stage: analyze
Author-agent: analyst
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-001 — AI Agent `erp_ai` cho Helpdesk Miyano (theo guide v2.2)

Nguồn yêu cầu duy nhất: `docs/HuongDan_TrienKhai_erp-ai.md` v2.2 (sau đây gọi là "guide", trích theo `:dòng`). Mode: decide (intake `:15`) → không có `questions.md`; mọi điểm lớn nằm ở mục Assumptions với đủ 4 trường.

## Mục tiêu

**Giả thuyết (độ tin cậy 75%):** người yêu cầu muốn một app `erp_ai` cài được lên site Helpdesk ở trạng thái **tắt**, khi bật thì chạy được mức `L0` (shadow: chỉ ghi dự đoán) và `L1` (phân loại, comment, hướng giải quyết trên phiếu), với mô hình thẩm quyền theo người, các chốt an toàn, quản lý nhiều khóa API và kiểm soát chi phí đúng guide; kèm bộ đánh giá offline để đo độ chính xác phân loại trước khi bật. Dưới 85% vì: (1) guide mô tả tới `L3` nhưng tool của `L2`/`L3` chưa có đặc tả (guide `:1462-1470`) và chỉ được mở sau nhiều tuần đo (guide `:1285-1287`) — đội tự quyết để ngoài phạm vi (A-1); (2) chưa biết phiên bản Helpdesk/Frappe trên production (`open-questions.md` câu 6); (3) trích yếu HDSD đưa vào prompt do Hiếu chọn, chưa có (guide `:1470`).

| Mục | Nội dung |
|---|---|
| Outcome | Phiếu Helpdesk mới được agent đọc, phân loại vào 1 trong 6 đầu mục A–F và (ở `L1`) được ghi hướng giải quyết + comment, trong khi agent không thể tự nâng quyền, không gửi dữ liệu nhạy cảm ra ngoài và không vượt ngân sách |
| Users | Hiếu (IT, đọc comment, cấu hình), COO (người ra lệnh), HD Agent nội bộ (Việt, Tiến…), trưởng bộ phận (Hà, Lan, Xuân, Thư), người ngoài (HD Contact: Himedic, NCC) — chi tiết ở mục Người dùng |
| Why now | Helpdesk tồn 62/71 phiếu mở, backlog 87% (guide `:68`); GĐ0 (6 đầu mục + gán tay 71 phiếu) hạn 14/11 (guide `:69`); bước 2–6 lộ trình chạy song song được với GĐ0 (guide `:1301`) |
| Success | Lúc build: mọi AC-1..AC-20 đạt trên site dev `miyano`. Sau G4 (đo trên production, việc của người): bộ đánh giá offline trên 71 phiếu ≥ 85% tổng (guide `:1293`); sau 1 tuần `L0` ≥ 85% tổng và không đầu mục nào sai liên tiếp 3 lần (guide `:1285`) thì mới mở `L1` |
| Constraints | Chỉ commit local trên `team/FEAT-001` và `team/FEAT-001-task-N`, không push, không đụng `develop`/`main` (intake `:28`); không deploy lên `erp.miyano.com.vn` (intake `:29`); app cài xong ở trạng thái tắt, mức `L0` (guide `:33`, `:650-651`); agent không sửa file trong `apps/`, không git ghi, không deploy (guide `:26`) |
| Out of scope | Tool của `L2`/`L3` (cấu hình giao diện, dữ liệu nghiệp vụ, User, Data Import, Server Script/Webhook tạo-ở-trạng-thái-tắt); dự phòng nhà cung cấp thứ hai cho phân loại; agent tự giao phiếu cho người; đổi `status` phiếu; cài/chạy trên production — chi tiết ở mục Phạm vi |

## Người dùng

| Ai | Tình huống | Quan hệ với agent |
|---|---|---|
| Người tạo phiếu (nội bộ hoặc HD Contact bên ngoài) | Tạo HD Ticket, viết comment | Lời của họ là **dữ liệu**, không phải lệnh, trừ khi họ có thẩm quyền (guide `:85-91`) |
| Người có role "người ra lệnh" (khởi điểm COO + Hiếu, guide `:147`) | Viết comment có từ khóa gọi agent (mặc định `@ai`) | Lời có hiệu lực **chỉ thị** trên mọi phiếu |
| Người được giao phiếu (HD Agent, do người khác giao) | Xử lý phiếu được giao | Chỉ thị trên đúng phiếu đó; tự giao cho mình thì không có thẩm quyền (guide `:93`) |
| Hiếu / System Manager | Mở form cấu hình, dán khóa API, đặt ngân sách, đọc báo cáo, nhận cảnh báo | Quản trị agent |
| Tiến (dev) | Xuất 71 phiếu đã gán nhãn, chạy bộ đánh giá offline | Đo chất lượng phân loại trước khi bật (guide `:1278`) |
| Người nhận cảnh báo (mặc định `info@miyano.com.vn`, guide `:523`) | Nhận email khi agent bị nâng quyền hoặc hết khóa dùng được | Giám sát |

Quy mô: công ty ~10 người (guide `:1410`); 71 phiếu lịch sử (guide `:44`); 56/71 phiếu do COO viết (guide `:1262`).

## Phạm vi

- Trong:
  1. Bộ đánh giá offline: xuất phiếu đã gán nhãn người ra một tệp dòng-JSON, chạy prompt phân loại trên từng phiếu, in độ chính xác tổng, theo từng đầu mục, ma trận nhầm lẫn, độ chính xác riêng trên phiếu không do người viết nhiều nhất tạo, và kết luận theo bảng ngưỡng guide `:1291-1295` (guide `:1240-1263`).
  2. Cài app: tạo role agent + role người ra lệnh, tài khoản agent không có System Manager, các trường AI trên HD Ticket ẩn với khách, nơi cấu hình agent (tắt, `L0`), nhật ký từng lượt gọi (guide `:435-458`, `:580-601`, `:646-680`, `:957-987`).
  3. Điều kiện kích hoạt: phiếu mới, comment có từ khóa; chống tự kích hoạt, chống trùng, cờ "không dùng AI", nhóm loại trừ, phiếu đã phân loại đủ (guide `:991-1045`).
  4. Chốt tài khoản job nền: chỉ chạy khi job đang chạy đúng dưới tài khoản agent (guide `:460-486`).
  5. Mô hình thẩm quyền theo người (guide `:77-143`) và bộ tool = mức quyền × thẩm quyền (guide `:153-182`).
  6. Hành vi `L0` (shadow) và `L1` (Helpdesk): phân loại, độ tin cậy, hướng giải quyết, comment, Task liên kết phiếu (guide `:669-676`, `:1265-1267`).
  7. Ghi nhận người sửa tay phân loại để đo độ chính xác, và một báo cáo độ chính xác theo đầu mục (guide `:1267`).
  8. Tool đọc: phiếu, comment, phiếu đã giải quyết tương tự, đọc mã nguồn chỉ trong `apps/` (guide `:329-431`, `:736-749`).
  9. Vòng lặp agent có giới hạn lượt, giới hạn số lần chạy/phiếu/ngày, tính chi phí, ngân sách tháng, prompt caching, hai lượt (phân loại rẻ → lập luận có tool) (guide `:1049-1167`, `:1222-1234`).
  10. Quản lý nhiều khóa API trên form web: chọn khóa theo việc, cầu dao theo loại lỗi, đọc hạn mức từ phản hồi, nút "Kiểm tra khóa", dò lại khóa hết hạn mức mỗi giờ, reset đầu tháng (guide `:682-953`).
  11. Scheduler hằng ngày: kiểm tra nâng quyền + cộng chi phí (guide `:488-527`, `:947`, `:1225`).
- Ngoài:
  - Tool `L2`/`L3`: Client Script, Property Setter, Custom Field, Workflow, Report, Notification, Translation, dữ liệu nghiệp vụ, User, Data Import, Server Script/Webhook tạo-ở-trạng-thái-tắt, xác nhận một lượt trước hành động không hoàn tác (guide `:238-327`, `:1286-1287`) → feature sau (A-1).
  - Dự phòng nhà cung cấp thứ hai cho bước phân loại (guide `:751-786`) → A-6.
  - Agent tự giao phiếu cho người theo bảng routing (cột "Người mặc định", guide `:1324-1331`) → A-7.
  - Đổi `status` phiếu, đóng phiếu (guide `:1217-1220`).
  - Agent tự tách phiếu gộp (guide `:1340`) — agent chỉ đề xuất trong comment.
  - Gửi file đính kèm lên API (guide `:1211`).
  - Nút Custom Action trên trang ticket Helpdesk (guide `:576`) — guide không mô tả nút nào ngoài "Kiểm tra khóa" trên form cấu hình.
  - Mọi bước trên production: backup, script kiểm chứng mục 6, gán nhãn 71 phiếu (GĐ0), chạy eval với dữ liệu thật, probe mục 5.2, bật agent, cấp role người ra lệnh, các việc COO chốt (guide `:1494-1502`) và 12 điểm kiểm chứng (guide `:1506-1519`) — việc của người, sau G4.
  - Tạo/xóa bản ghi HD Ticket Type cho 6 đầu mục trên production (GĐ0, việc của người) → A-8.
  - Sửa CI, `.gitignore`, nâng version action (nợ ở `docs/team/debt.md`) — chỉ trong phạm vi "CI xanh" của DoD.

## Dữ liệu

| Thực thể (nghiệp vụ) | Agent làm gì | Khối lượng | Nhạy cảm |
|---|---|---|---|
| Phiếu Helpdesk (tiêu đề, nội dung, loại phiếu, nhóm, ưu tiên, người tạo, người được giao) | Đọc; ở `L1` ghi loại phiếu/nhóm/ưu tiên + các trường AI | 71 phiếu lịch sử; phiếu mới/tuần: chưa có số đo | Có: phiếu nhóm Nhân sự & Kế toán (CCCD #1742, lương #1708 — guide `:1207`) |
| Comment của phiếu | Đọc; ở `L1` thêm comment | — | Như trên |
| Phân công (giao phiếu, ai giao) | Chỉ đọc, để xét thẩm quyền | — | Không |
| Task liên kết phiếu | Ở `L1` tạo khi có người có thẩm quyền ra lệnh (A-5) | — | Không |
| Trường AI trên phiếu: hướng giải quyết, độ tin cậy (Cao/Trung bình/Thấp), phân loại bởi (AI/Người), cập nhật lúc, số lượt hôm nay, cờ không dùng AI (guide `:584-592`) | Ghi | 1 bộ/phiếu | Không |
| Cấu hình agent: bật/tắt, mức quyền, model mặc định, giới hạn, ngân sách, đơn giá, từ khóa, nhóm loại trừ, bảng ánh xạ đầu mục → loại phiếu/nhóm/ưu tiên (guide `:646-680`, `:1333`) | Runner đọc trực tiếp; tool đọc **không** đọc được | 1 bản | Có: chứa khóa API |
| Khóa API (nhiều dòng; nhãn, nhà cung cấp, khóa, model, ưu tiên, mục đích, ngân sách tháng, đã dùng, trạng thái, nghỉ đến, token còn lại, mốc reset, số lần lỗi, lỗi gần nhất…) (guide `:711-731`) | Runner đọc/ghi trạng thái | ~1–10 dòng | **Rất nhạy cảm**: lưu mã hóa, không bao giờ hiện bản rõ ở log, comment, lỗi |
| Nhật ký từng lượt gọi (guide `:961-983`) | Ghi mỗi lượt | ≤ 5 lần chạy × 8 lượt = 40 dòng/phiếu/ngày (giới hạn NFR-3) | Có thể chứa trích nội dung phiếu |
| Tệp xuất phiếu cho eval (guide `:1245-1256`) | Ghi ra máy người chạy, ngoài repo | 71 dòng | Có — không xuất phiếu nhóm loại trừ (A-9) |

Dữ liệu sẵn có: app **không** sửa phiếu, comment hay bản ghi nào đã có khi cài; không xóa bản ghi nào trong mọi trường hợp (guide `:259`). Lưu trữ nhật ký: không tự xóa trong feature này (A-10).

## Giao diện / tích hợp

| Hệ thống | Chiều | Ghi chú |
|---|---|---|
| Helpdesk 15.1.0 trên site dev `miyano` (intake `:30`) | Sự kiện phiếu mới, comment mới, phiếu được sửa → agent | Trường dự kiến ở guide `:556-567` khớp mã nguồn dev: HD Ticket có `subject`, `description`, `status`, `priority`, `ticket_type`, `agent_group`, `raised_by`; HD Ticket Comment có `content`, `reference_ticket`, `commented_by` (`apps/helpdesk/helpdesk/helpdesk/doctype/hd_ticket*/…json`). Production chưa đối chiếu (A-2) |
| Claude API (Anthropic Console, khóa workspace chuẩn `sk-ant-api03-`, guide `:684-707`) | Agent → API | Bước phân loại: một lượt, không tool, trả JSON theo guide `:1389-1399`. Bước lập luận: vòng lặp tool-use. Model và đơn giá lấy từ cấu hình, không viết cứng (guide `:680`) |
| Form cấu hình trên Desk | Người → agent | Thêm/sửa khóa, bật/tắt, đặt mức quyền, nút "Kiểm tra khóa" (guide `:896-943`) |
| Giao diện Helpdesk (trang ticket của agent) | Agent → người | Trường AI hiển thị cho HD Agent, ẩn với khách (guide `:575`). Cơ chế hiển thị: HD Ticket Template đã ghi "will be deprecated" ở bản dev (`hd_ticket_template.json:7`) → câu hỏi cho designer/researcher (H-2) |
| Email | Agent → người nhận cảnh báo | Cảnh báo quyền, hết khóa, khóa lỗi (guide `:521-524`, `:798`, `:821`) |
| Hệ thống tệp `apps/` và git của các app | Agent chỉ đọc | Không đọc ngoài `apps/` (guide `:331-356`) |
| Hàng đợi job nền + scheduler của bench | Nội bộ | Job dài, không bao giờ gọi API trong lúc người dùng lưu phiếu (guide `:216`) |

## NFR

| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | 0 lời gọi API model trong luồng lưu phiếu/comment của người dùng; công việc chỉ được đưa vào hàng đợi sau khi giao dịch lưu đã commit (guide `:216`, `:1043`) | Test tự động: lưu phiếu với lời gọi model bị thay bằng stub đếm số lần gọi → 0 lần trong luồng lưu; job chỉ thấy phiếu đã commit |
| NFR-2 | Một lần chạy agent có thời hạn 600 s, chạy ở hàng đợi dài (guide `:216`) | Test tự động kiểm tham số hàng đợi của job được đưa vào |
| NFR-3 | Tối đa 8 lượt/lần chạy, 5 lần chạy/phiếu/ngày, ngân sách mặc định 10 USD/tháng; cả ba sửa được trên form (guide `:656-658`, `:1224-1227`) | AC-15, AC-16 |
| NFR-4 | Phiếu thuộc nhóm loại trừ (mặc định "Nhân sự & Hành chính", "Tài chính Kế toán") hoặc có cờ "không dùng AI": 0 byte nội dung gửi lên API; file đính kèm: không bao giờ gửi (guide `:664`, `:1209-1211`) | AC-5 (stub đếm lời gọi = 0), AC-2 |
| NFR-5 | Khóa API lưu mã hóa; bản rõ không xuất hiện trong: kết quả tool, nhật ký, comment, Error Log, thông báo lỗi cho người dùng (guide `:717`, `:736-749`, STD-SEC-6) | AC-14: test gieo một khóa giả có chuỗi nhận diện, chạy cả đường thành công và đường lỗi, tìm chuỗi đó trong mọi bản ghi sinh ra → 0 kết quả |
| NFR-6 | Đọc mã nguồn: ≤ 400 dòng/lần đọc, ≤ 40 kết quả/lần tìm, mỗi lệnh ngoài có thời hạn 30 s (guide `:365-386`, `:399`, `:403`) | AC-13 |
| NFR-7 | Gọi API có thời hạn và số lần thử có giới hạn: tối đa `max_key_thu` (mặc định 3) khóa mỗi lượt (guide `:655`, `:804-822`, STD-ERR-5) | AC-17 |
| NFR-8 | Chủ động cho khóa nghỉ khi số token còn lại báo về < 20.000 (guide `:854`) | AC-17 |
| NFR-9 | Độ chính xác phân loại ≥ 85% tổng (guide `:1293`, `:1285`) — mục tiêu nghiệp vụ, đo sau G4 trên dữ liệu thật, không phải điều kiện build | Bộ đánh giá offline (AC-1) chạy trên 71 phiếu thật; báo cáo độ chính xác (AC-12) sau 1 tuần `L0` |

Không có số độ trễ phản hồi người dùng: guide chỉ nêu ước lượng 5–40 s/lượt, 3–8 lượt/phiếu (guide `:216`) — là mô tả, không phải yêu cầu (A-11).

## Tiêu chí nghiệm thu

Mọi "test tự động" dưới đây chạy bằng `cmd.test_one` (từng file) và `cmd.test` (toàn app) trên site `miyano`, không gọi mạng thật: lời gọi model được thay bằng stub (STD-TEST-6).

| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Bộ đánh giá offline, với một tệp dòng-JSON N phiếu có nhãn người và kết quả phân loại cho trước, in ra: độ chính xác tổng, độ chính xác từng đầu mục A–F, ma trận nhầm lẫn 6×6, độ chính xác riêng trên phiếu không do người viết nhiều nhất tạo (guide `:1262`), và đúng một kết luận theo ngưỡng ≥ 85% / 70–85% / < 70% (guide `:1291-1295`) | Test tự động với bộ mẫu tổng hợp 12 phiếu có đáp số tính tay (ví dụ 10/12 đúng → 83,3% → kết luận "70–85%"); so từng con số |
| AC-2 | Bước xuất phiếu cho eval ghi một dòng/phiếu gồm tiêu đề, nội dung, loại phiếu, nhóm, ưu tiên, người tạo; bỏ phiếu thuộc nhóm loại trừ; không ghi file đính kèm; không cần agent đang bật | Test tự động: tạo 3 phiếu (1 thuộc nhóm loại trừ) → tệp có đúng 2 dòng, đủ 6 khóa |
| AC-3 | Bộ đánh giá và agent thật dùng **cùng một** nội dung prompt phân loại (guide `:1344`); phản hồi phân loại không đúng định dạng JSON guide `:1389-1399` được ghi là "không phân loại được", không làm hỏng lần chạy | Test tự động: so nội dung prompt hai đường bằng nhau; stub trả chuỗi không phải JSON → kết quả "không phân loại được", không ngoại lệ lọt ra |
| AC-4 | Sau khi cài + `cmd.migrate` trên `miyano`: migrate thoát mã 0; agent tắt, mức `L0`; có role agent và role người ra lệnh; tài khoản agent tồn tại, có đúng role agent + Agent, **không** có System Manager; các trường AI có trên HD Ticket và ẩn với khách; tạo phiếu khi agent tắt → 0 job, 0 lời gọi model | `cmd.migrate` (dán exit code) + test tự động kiểm role, tài khoản, trường, cấu hình mặc định, stub đếm = 0 |
| AC-5 | Khi agent bật: (a) phiếu mới do người tạo, chưa đủ loại/nhóm/ưu tiên → đúng 1 job; (b) phiếu người tạo đã điền đủ 3 trường → 0 job; (c) phiếu hoặc comment do tài khoản agent tạo → 0 job; (d) comment không chứa từ khóa (không phân biệt hoa thường) → 0 job, có từ khóa → 1 job; (e) phiếu có cờ "không dùng AI" hoặc thuộc nhóm loại trừ → 0 job và 0 byte gửi API; (f) hai lần kích hoạt cùng phiếu + cùng loại khi job đầu còn chờ → 1 job | Test tự động, mỗi trường hợp (a)–(f) một test, đếm job trong hàng đợi và lời gọi stub |
| AC-6 | Job chạy agent không gọi model và ghi lỗi "sai tài khoản" khi người dùng phiên làm việc ≠ tài khoản agent sau bước chuyển tài khoản (guide `:482-486`) | Test tự động ép bước chuyển tài khoản thất bại → 0 lời gọi stub, có 1 Error Log chứa tên tài khoản thật |
| AC-7 | Thẩm quyền theo người (guide `:85-93`): người có role người ra lệnh → chỉ thị trên mọi phiếu; người được người khác giao phiếu P → chỉ thị trên P, dữ liệu trên phiếu Q; người tự giao P cho mình → dữ liệu; người còn lại (kể cả HD Contact) → dữ liệu; "người ra lệnh gần nhất" = tác giả gần nhất có thẩm quyền trong comment rồi đến người tạo phiếu (guide `:132-142`) | Test tự động bảng 6 trường hợp |
| AC-8 | Bộ tool đưa vào mỗi lượt lập luận = mức quyền × thẩm quyền: `L0` → không có lượt lập luận (A-3); `L1` → tool đọc + tool ghi phiếu (phân loại, hướng giải quyết, comment); tool tạo Task chỉ có khi có người ra lệnh; `L2`/`L3` trong feature này → đúng bộ của `L1`. Không tồn tại tool ghi nào nhận tên DocType tùy ý; tool ghi không bỏ qua phân quyền: khi tài khoản agent không có quyền ghi, tool trả `ok=false` kèm lý do, không ghi (guide `:1179-1180`, `:1203`) | Test tự động: liệt kê tên tool theo từng tổ hợp (4 mức × có/không thẩm quyền); test thu quyền ghi của role agent rồi gọi tool → `ok=false`, bản ghi không đổi |
| AC-9 | `L0` (shadow): phiếu mới → 1 bản ghi nhật ký có loại phiếu/nhóm/ưu tiên dự đoán, đánh dấu "chưa áp dụng"; số comment, giá trị loại/nhóm/ưu tiên và các trường AI của phiếu trước = sau (guide `:673`, `:1267`) | Test tự động với stub phân loại cố định |
| AC-10 | `L1`: phiếu mới → loại phiếu/nhóm/ưu tiên được ghi theo bảng ánh xạ đầu mục trong cấu hình, cùng độ tin cậy, "phân loại bởi = AI", thời điểm cập nhật, hướng giải quyết; `status` không đổi; phiếu có "phân loại bởi = Người" không bị ghi đè loại/nhóm/ưu tiên; đầu mục ánh xạ tới giá trị không tồn tại → không ghi trường đó, lý do vào nhật ký; tiêu đề có `[GẬP]` → ưu tiên Urgent (guide `:1337`) | Test tự động, mỗi nhánh một test |
| AC-11 | Người (không phải agent) sửa loại/nhóm/ưu tiên của phiếu đã có dự đoán → bản ghi nhật ký gần nhất của phiếu đó lưu giá trị người sửa, và "phân loại bởi" thành Người; agent sửa thì không ghi nhận | Test tự động hai nhánh |
| AC-12 | Báo cáo độ chính xác trên nhật ký, lọc theo khoảng ngày: số dự đoán, số bị người sửa, độ chính xác từng đầu mục và tổng (A-12) | Test tự động với 10 bản ghi nhật ký mẫu, đáp số tính tay |
| AC-13 | Tool đọc mã nguồn: đường dẫn ra ngoài `apps/` (kể cả qua `../` hay liên kết), tên khớp mẫu bí mật (`site_config.json`, `common_site_config.json`, `.env`, `.pem`, `.key`, `id_rsa`, `credential`, `secret`, `password`), đuôi ngoài danh sách guide `:342` → từ chối có lý do; một lần đọc ≤ 400 dòng; một lần tìm ≤ 40 kết quả; git chỉ nhận `log`/`show`/`diff`/`blame`; thiếu công cụ tìm kiếm trên máy → trả `ok=false` "chưa cài", không ngoại lệ (local hiện không có `rg`: `which rg` exit 1) | Test tự động mỗi trường hợp, dùng thư mục mẫu tạm |
| AC-14 | Tool đọc bản ghi từ chối cấu hình agent, khóa API và danh sách nhạy cảm guide `:742-746` (Salary Slip, Employee, Purchase Invoice, Payment Entry, GL Entry, User, Role Permission, Custom DocPerm); bản rõ khóa API không xuất hiện trong kết quả tool, nhật ký, comment, Error Log (NFR-5) | Test tự động: gọi tool trên từng DocType bị cấm → `ok=false`; test gieo khóa giả và tìm chuỗi → 0 kết quả |
| AC-15 | Stub luôn trả "gọi tool" → lần chạy dừng sau đúng `max_turns_per_run` lượt (mặc định 8); lần kích hoạt thứ `max_runs_per_ticket_per_day + 1` (mặc định 6) trong cùng ngày → 0 lời gọi; mỗi lượt có 1 bản ghi nhật ký có: token vào/ra, token cache tạo/đọc, chi phí = token × đơn giá trong cấu hình, nhãn khóa, độ trễ, lý do dừng, tool đã gọi, người ra lệnh | Test tự động; chi phí so với số tính tay từ usage của stub |
| AC-16 | Job hằng ngày cộng chi phí nhật ký vào "đã dùng tháng"; khi đã dùng > ngân sách tháng, mức hiệu lực = min(mức cấu hình, `L1`) — không bao giờ nâng `L0` lên `L1` (A-4); đầu tháng reset "đã dùng tháng" về 0 | Test tự động ba nhánh |
| AC-17 | Chọn khóa: bỏ khóa tắt, "Lỗi khóa", "Hết hạn mức", đang nghỉ, vượt ngân sách riêng; việc lập luận chỉ dùng khóa Anthropic có model lập luận; sắp theo ưu tiên rồi số lần lỗi. Cầu dao theo bảng guide `:792-799`: 429 → nghỉ đến retry-after + 1 s, chuyển khóa; 529 → nghỉ 30 s × số lần lỗi, tối đa 10 phút, chuyển khóa; 500/timeout → nghỉ 30 s, chuyển khóa; hết credit → "Hết hạn mức", chuyển khóa, báo tin; 401/403 → "Lỗi khóa", chuyển khóa, báo động; 400 → không chuyển, lỗi trả về. Tối đa `max_key_thu` khóa/lượt; hết khóa → báo động. Token còn lại < 20.000 → nghỉ đến mốc reset | Test tự động: stub ném từng loại lỗi, kiểm trạng thái khóa, số khóa đã thử, báo động |
| AC-18 | Job mỗi giờ chỉ dò lại khóa "Hết hạn mức" (không dò "Lỗi khóa"), dò được → "Hoạt động" + báo tin. Job hằng ngày báo động (Error Log + email người nhận cấu hình được) khi: role tài khoản agent ≠ {role agent, Agent}; tài khoản agent đã sửa bản ghi phân quyền (guide `:496-510`); Server Script/Webhook do agent tạo đang bật; có khóa đang bật mà rỗng (guide `:947`) | Test tự động mỗi điều kiện, đếm email trong hàng đợi gửi |
| AC-19 | Form cấu hình: chỉ System Manager (và role quản lý agent nếu có) đọc/ghi được; người dùng HD Agent thường → bị từ chối; các trường tự quản (trạng thái, nghỉ đến, token còn lại, mốc reset, số lần lỗi, đã dùng tháng) chỉ đọc với người, trừ chuyển "Lỗi khóa" → "Hoạt động"; "Kiểm tra khóa" trả kết quả ok/lỗi từng khóa và chỉ System Manager gọi được | Test tự động phân quyền + stub dò khóa; sau G4: người bấm nút trên `/app/<form cấu hình>` của site dev, chụp kết quả |
| AC-20 | Các trường AI hiển thị trên trang ticket của giao diện Helpdesk cho HD Agent và không hiển thị trên cổng khách | Sau G4, người kiểm trên site dev: mở 1 phiếu bằng tài khoản HD Agent và 1 bằng HD Contact, chụp màn hình (`ui: false` trong profile → không có QA trình duyệt tự động) |

**Thứ tự bỏ trước nếu thiếu thời gian (bước 8 của analyze, cỡ L > 5 AC):** (1) AC-12 báo cáo độ chính xác — nhật ký đã đủ dữ liệu để truy vấn tay; (2) nút "Kiểm tra khóa" trong AC-19; (3) tool tạo Task trong AC-8; (4) AC-17 rút về một khóa không chuyển khóa (giữ phân loại lỗi 401/403 vs khác). Không được bỏ: AC-4..AC-8, AC-13..AC-16 (an toàn, thẩm quyền, chi phí) và AC-1..AC-3 (cửa quyết định của guide `:1289`).

## Assumptions decided by the team

Định dạng: chọn | vì | phương án khác | sai thì sửa thế nào.

- **A-1 Phạm vi dừng ở `L1`.** chọn: FEAT-001 giao `L0`/`L1`; `L2`/`L3` có trong lựa chọn mức quyền nhưng cấp đúng bộ tool `L1` | vì: guide chỉ mở `L2` sau ≥ 85% và `L3` sau 2 tuần `L2` không sự cố (guide `:1285-1287`); JSON schema các tool `TOOL_CONFIG`/`TOOL_DATA` chưa viết (guide `:1466`); tool chưa dùng được trên prod trong nhiều tuần là việc thừa (STD-DESIGN-5) | phương án khác: làm trọn tới `L3` trong FEAT-001 (cỡ vượt L) | sai thì: mở feature mới "erp_ai L2/L3 tools" qua `/team:intake`; không phải sửa phần đã làm vì bộ tool đã tách theo mức (AC-8).
- **A-2 Production giống dev.** chọn: Helpdesk 15.1.0 / Frappe 15 như site `miyano` | vì: không truy cập được production (`open-questions.md` câu 6 chưa trả lời) | phương án khác: dừng chờ người | sai thì: người chạy script guide mục 6 trên production sau G4, designer sửa ánh xạ trường, mở `--amend`.
- **A-3 `L0` không chạy lượt lập luận.** chọn: ở `L0` chỉ chạy bước phân loại và ghi nhật ký; comment có từ khóa ở `L0` được ghi nhật ký "bỏ qua do L0", 0 lời gọi | vì: `L0` "chỉ đọc, ghi dự đoán" (guide `:673`, `:1284`), lượt lập luận đắt mà kết quả không hiện cho ai | phương án khác: chạy lập luận và lưu bản nháp hướng giải quyết vào nhật ký | sai thì: bật lượt lập luận ở `L0` với đầu ra chỉ ghi nhật ký; sửa AC-8, AC-9.
- **A-4 Lui về khi vượt ngân sách không bao giờ nâng quyền.** chọn: mức hiệu lực = min(mức cấu hình, `L1`) | vì: mã mẫu guide `:1074-1077` đặt `L1` cả khi đang `L0`, tức nâng quyền khi vượt ngân sách — ngược ý "lui về" (guide `:1226`) | phương án khác: theo đúng mã mẫu | sai thì: sửa một dòng logic và AC-16.
- **A-5 Task chỉ tạo khi có người ra lệnh.** chọn: tool tạo Task liên kết phiếu chỉ có khi có người có thẩm quyền | vì: guide liệt kê Task trong `L1` (guide `:674`) nhưng bộ `TOOL_TICKET` không có Task (guide `:161`); tạo việc cho người theo lời người ngoài là hành động ra ngoài phiếu | phương án khác: luôn có tool tạo Task ở `L1` | sai thì: chuyển tool vào bộ `L1` không điều kiện; sửa AC-8.
- **A-6 Chỉ một nhà cung cấp.** chọn: chỉ Anthropic cho cả hai bước; trường "nhà cung cấp" vẫn có, giá trị khác bị từ chối khi chọn khóa | vì: giảm một tích hợp ngoài trong feature cỡ L; guide xếp dự phòng đa nhà cung cấp là lợi ích, không phải điều kiện (guide `:753-760`) | phương án khác: làm dự phòng OpenAI cho bước phân loại | sai thì: feature nhỏ thêm một đường gọi cho bước phân loại; AC-17 thêm trường hợp.
- **A-7 Agent không tự giao phiếu cho người.** chọn: agent ghi nhóm nhận, không gán người | vì: người được giao có thẩm quyền chỉ thị (guide `:88`); agent gán người = agent tạo ra thẩm quyền mới cho người khác; guide `L1` không liệt kê gán người (guide `:674`) | phương án khác: gán "Người mặc định" theo bảng routing | sai thì: thêm tool gán, kèm quyết định bảo mật của COO.
- **A-8 6 đầu mục do người cài.** chọn: app không tạo/xóa bản ghi loại phiếu; ánh xạ A–F → loại phiếu/nhóm/ưu tiên nằm trong cấu hình, Hiếu sửa trên form (guide `:1311`, `:1333`); test tự tạo dữ liệu mẫu | vì: cài 6 đầu mục là GĐ0, việc của người (guide `:69`) | phương án khác: fixtures tạo 6 loại phiếu | sai thì: thêm dữ liệu cài đặt; không đụng tới phiếu cũ.
- **A-9 Eval không xuất phiếu nhóm loại trừ.** chọn: cùng quy tắc nhóm loại trừ như agent thật | vì: guide `:1209` "không gửi gì lên API" cho nhóm này; eval gửi nội dung lên API y như agent | phương án khác: xuất đủ 71 phiếu để đo cả đầu mục E | sai thì: thêm tùy chọn xuất cả nhóm loại trừ, COO đồng ý (guide `:1498`).
- **A-10 Nhật ký giữ vô hạn.** chọn: không tự xóa | vì: là nguồn số liệu duy nhất để đo (guide `:959`), guide không nêu hạn lưu | phương án khác: xóa sau N ngày | sai thì: thêm job dọn theo hạn do người đặt.
- **A-11 Không có NFR độ trễ.** chọn: không đặt ngưỡng thời gian phản hồi phiếu | vì: không có số nào từ intake/guide/đo thật (guide `:216` chỉ ước lượng) | phương án khác: đặt p95 | sai thì: đo `latency_ms` trong nhật ký 1 tuần `L0`, người chốt ngưỡng, `--amend`.
- **A-12 "Đúng" trong báo cáo độ chính xác.** chọn: dự đoán đúng = người không sửa loại/nhóm/ưu tiên trong 7 ngày sau dự đoán | vì: guide chỉ nói "độ chính xác tính tự động" (guide `:1267`), không định nghĩa; 7 ngày khớp chu kỳ "1 tuần `L0`" (guide `:1285`) | phương án khác: chỉ tính phiếu đã đóng | sai thì: đổi định nghĩa trong báo cáo, sửa AC-12.
- **A-13 Tài khoản agent tạo khi cài.** chọn: cài/migrate tạo tài khoản agent (email theo guide `:32`) và 2 role nếu chưa có, lặp lại không lỗi, không mật khẩu dùng được, không khóa API của ERP | vì: guide `:437-458`; AC-4 cần kiểm được tự động | phương án khác: người tạo tay theo script guide | sai thì: bỏ bước tạo, AC-4 kiểm điều kiện "nếu có thì không có System Manager".
- **A-14 Trích yếu HDSD rỗng.** chọn: phần trích yếu trong prompt chính là nội dung người điền, mặc định rỗng | vì: Hiếu chọn phần nào (guide `:1470`) | phương án khác: đội tự trích | sai thì: Hiếu điền sau G4, không cần sửa code.
- **A-15 Quyết định COO (guide `:1494-1502`) lấy đề xuất của guide làm mặc định.** chọn: nhóm loại trừ = Nhân sự & Kế toán, ngân sách 10 USD, người nhận cảnh báo `info@miyano.com.vn`; cấp role người ra lệnh là việc quản trị của người, app không tự cấp cho ai | vì: decide mode; đều sửa được trên form | phương án khác: dừng chờ COO | sai thì: sửa trên form cấu hình, không cần code.

### Chuyển cho architect / designer / researcher (kỹ thuật, không hỏi người)
- H-1 Vị trí module: module thật là `ERP AI agent` (`erp_ai/modules.txt:1`, thư mục `erp_ai/erp_ai_agent/`) trong khi guide đặt ở `erp_ai/erp_ai/doctype/` (guide `:634`) — chốt trước DocType đầu tiên (`docs/team/debt.md`, `open-questions.md` câu 3).
- H-2 Cơ chế hiện trường AI trên giao diện Helpdesk 15.1.0: HD Ticket Template "will be deprecated" (`apps/helpdesk/.../hd_ticket_template/hd_ticket_template.json:7`), có DocType `hd_field_layout` và `hd_form_script` ở bản dev.
- H-3 Chống trùng job: bản Frappe dev có tham số chống trùng (`apps/frappe/frappe/utils/background_jobs.py:73`, `:87-93`); ToDo có `allocated_to` (guide `:1515`).
- H-4 Phiên bản SDK gọi API, tên header hạn mức và cách lấy header (guide `:868`, `:1518`); bench env đang có sẵn một bản SDK — researcher xác nhận và ghim theo STD-DEP-4.
- H-5 Công cụ tìm mã nguồn chưa có trên máy dev (`which rg` exit 1) — chọn cách tìm hoặc yêu cầu cài (guide `:1516`).
- H-6 Khai phụ thuộc trong `pyproject.toml` thay vì `requirements.txt` (guide `:640` vs `pyproject.toml:10-12`).

### Đề xuất về cỡ (cho team-leader, analyst không tự đổi)
Giữ cỡ L cho FEAT-001 (20 AC, 11 nhóm hành vi). Phần cắt ra ở A-1 (tool `L2`/`L3`), A-6 (dự phòng nhà cung cấp) và A-7 (gán người) nên thành feature riêng khi production đạt điều kiện guide `:1285-1287`.

## Definition of Done

Phần build (đội làm, trước G4):
- [ ] AC-1..AC-19 có test tự động; `cmd.test` xanh trên site `miyano`, đầu ra dán trong acceptance.md
- [ ] `cmd.migrate` thoát mã 0 trên `miyano` sau khi cài app
- [ ] `cmd.lint` sạch; không có dấu skip trong `test.skip_markers`
- [ ] CI xanh trên nhánh feature (CI hiện đỏ vì 0 test, `docs/team/debt.md`)
- [ ] Không có khóa API, mật khẩu hay dữ liệu cá nhân trong repo, nhật ký đội, artifact (STD-SEC-1, STD-SEC-6)
- [ ] Commit chỉ trên `team/FEAT-001` và `team/FEAT-001-task-N`, không push (intake `:28`)

Sau G4 (`/team:asbuilt`, chủ: writer; kiểm lại ở release):
- [ ] As-Built viết xong (asbuilt.md) — sau G4, `/team:asbuilt`
- [ ] README/tài liệu người dùng cập nhật nếu hành vi đổi — sau G4, `/team:asbuilt`: cách cài (tắt sẵn), cấu hình khóa API, các mức `L0`/`L1`, nhóm loại trừ, cách chạy bộ đánh giá offline
- [ ] Mục CHANGELOG — sau G4, `/team:asbuilt`
- [ ] AC-19 (bấm "Kiểm tra khóa") và AC-20 (hiển thị trường AI) được người kiểm trên site dev, có ảnh chụp

Việc của người, ngoài DoD của đội (ghi để không ai tưởng đã xong): backup + script kiểm chứng mục 6 trên production; gán tay 71 phiếu; chạy bộ đánh giá với khóa thật và đạt NFR-9; probe tài khoản job nền trên production; 12 điểm kiểm chứng guide `:1506-1519`; các việc COO chốt guide `:1494-1502`; quyết định bật agent.
