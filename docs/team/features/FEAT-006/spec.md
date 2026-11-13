Feature: FEAT-006
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G1 tắt (config.json), để trống. -->

# Spec FEAT-006 — Bot chấm độ phức tạp, độ quan trọng; chọn nhóm, người phụ trách; SLA và Task theo điểm

## Mục tiêu
Giả thuyết: người yêu cầu muốn mỗi phiếu mới được bot chấm độ phức tạp và độ quan trọng, rồi từ đó tự đặt mức ưu tiên, chọn nhóm và người phụ trách, để Helpdesk áp SLA tương ứng. Phiếu đầu mục C/D thì có thêm Task giao cho người đó. Mọi việc này không được giành việc người đã chia. Độ tin cậy 75%. Còn thiếu hai điều: site đang có bản ghi HD Service Level Agreement nào, và trên phiếu có trường "Hạn hoàn thành", "Nguồn phát sinh" hay không. Analyst không đọc được DB, vì role-policy chặn lệnh `bench execute`; xem mục Assumptions A-9 và A-10. [changed] (Amendment 1, mục 12: hai điều còn thiếu đã được xác minh, độ tin cậy 85%)

- **Outcome:** phiếu mới vào hệ thống thì trong cùng lần chạy bot đã có đủ: mức ưu tiên, nhóm nhận, người phụ trách, SLA do Helpdesk tính. Đầu mục C/D có thêm 1 Task. Người phụ trách và người duyệt xem lại được điểm chấm và lý do.
- **Users:** người tạo phiếu (nhân viên các phòng), người phụ trách IT và trưởng bộ phận, COO, System Manager (người giữ cấu hình).
- **Why now:** hiện bot chỉ ghi nhóm/ưu tiên theo bảng ánh xạ cố định theo đầu mục (`erp_ai/agent/classification.py:15-22`, `:116-122`). Không tool nào gán người (`erp_ai/agent/tools/write_ticket.py:111-177`). Người mặc định và SLA chỉ là chữ trong prompt (`erp_ai/agent/prompts.py:135-145`). Vì vậy phiếu vẫn chờ người chia tay.
- **Success:** đạt AC-1..AC-17. Bộ eval offline in ra được tỷ lệ khớp mức ưu tiên và nhóm so với giá trị người đã đặt trên phiếu cũ (AC-15). [changed] (Amendment 1, mục 9: đạt AC-1..AC-18)
- **Constraints:** 5 quyết định QĐ-1..QĐ-5 trong `intake.md` (đã chốt). Không đổi role tài khoản agent (ADR-006). Ghi chỉ qua registry tool, đi qua phân quyền Frappe (ADR-005). Nội dung phiếu là dữ liệu (STD-SEC-5). Không ghi cấu hình Helpdesk (QĐ-5, phạm vi FEAT-005). [changed] (Amendment 1, mục 2: thêm quyền `share` trên Task do chính tài khoản agent tạo, ADR-021)
- **Out of scope:** bot tự tách phiếu (QĐ-2); bot tạo, sửa HD Team, Assignment Rule hay HD Service Level Agreement (QĐ-5); bot tự tính `response_by`/`resolution_by` (QĐ-1); bot tự gán chính tài khoản agent làm người phụ trách; chia lại phiếu cũ đã có trước khi bật tính năng; chấm lại điểm khi phiếu được sửa sau lần chạy đầu. [changed] (Amendment 1, mục 13: thêm "bot hoặc feature tự dọn dữ liệu site")

Đã có sẵn, không cần hỏi:
- Luồng chạy: bước phân loại chỉ chạy khi `ticket_insert`. Ở `L0` chỉ ghi nhật ký, từ `L1` trở lên mới ghi lên phiếu (`erp_ai/agent/runner.py:115-135`, `:228-246`; ADR-003 bước e).
- Helpdesk chọn SLA mỗi lần lưu phiếu, theo `priority` và `condition` (`apps/helpdesk/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py:101,112,970-999`). Khi cài, Helpdesk tạo một SLA mặc định nếu chưa có (`apps/helpdesk/helpdesk/setup/install.py:66-75`). Không tìm được SLA nào thì Helpdesk xóa các trường SLA trên phiếu (`hd_ticket.py:975-990`).
- Gán người qua `assign_agent` sẽ gửi thông báo và email (`hd_ticket.py:483-487`). Khi đổi nhóm, Helpdesk tự gỡ người không thuộc nhóm đó, nếu nhóm có Assignment Rule đang bật và có user (`hd_ticket.py:428-481`).
- `create_task` hiện chỉ có khi có người ra lệnh, và Task chỉ mang link phiếu trong mô tả (`write_ticket.py:86-108`; ADR-005 Quyết định 1).
- Eval offline dựng request bằng chính `build_classify_request`, và đã có ngưỡng 0,85 / 0,70 cho độ đúng đầu mục (`erp_ai/eval/run_eval.py:15-16`, `erp_ai/agent/prompts.py:166-171`).
- Chưa có `docs/team/glossary.md`. Cache explore `erp_ai` báo MISS; các file trên đã đọc trực tiếp.

## Người dùng
| Ai | Tình huống | Cần gì |
|---|---|---|
| Người tạo phiếu | Tạo phiếu qua Helpdesk | Phiếu có người nhận và có hạn phản hồi ngay, không phải chờ người chia |
| Người phụ trách (IT: ERP core, tracecore/app riêng, BA; trưởng bộ phận cho D; HCNS/Kế toán/Mua hàng/Marketing cho E) | Nhận thông báo được giao | Biết vì sao mình được giao và phiếu khó/gấp đến đâu (điểm + lý do) |
| COO | Đặt ưu tiên cho C, E (bảng 16.2) | Bot không đè lên ưu tiên hay người COO đã đặt |
| System Manager | Đổi nhân sự, đổi bảng mức | Sửa người mặc định và các bảng mức trong cấu hình, không cần deploy (QĐ-4) |

## Phạm vi
- Trong:
  1. Chấm 2 điểm cho mỗi phiếu mới: độ phức tạp và độ quan trọng, mỗi điểm theo thang 1–3 (định nghĩa ở mục Dữ liệu), kèm một câu lý do. Ghi vào nhật ký ở mọi mức. Từ `L1` thì ghi thêm lên phiếu.
  2. Từ điểm, đầu mục và các ngoại lệ của bảng 16.2, tính ra mức ưu tiên theo quy tắc R1–R5 (mục Dữ liệu).
  3. Chọn nhóm nhận. A/B/C/F lấy theo ánh xạ đầu mục như hiện nay. D/E chọn nhóm của bộ phận theo bảng bộ phận → nhóm trong cấu hình.
  4. Chọn người phụ trách theo bảng người mặc định trong cấu hình, rồi gán qua cơ chế gán của Helpdesk (có thông báo).
  5. SLA: để Helpdesk tự chọn và tính. Bot báo khi phiếu không có SLA nào áp vào, hoặc khi SLA đang áp chậm hơn mức mong đợi của bảng 16.2 trong cấu hình.
  6. Đầu mục C/D: tạo đúng 1 Task cho phiếu, giao cho người phụ trách đã chọn.
  7. Một công tắc bật/tắt việc tự gán người và tạo Task. Sau khi cài, công tắc ở trạng thái tắt.
  8. Mở rộng eval offline: đo độ khớp mức ưu tiên và nhóm.
- Ngoài: như dòng Out of scope ở trên. Thêm: giao diện riêng để xem điểm (chỉ cần xem được trên phiếu hoặc trong nhật ký); bot đổi người phụ trách khi người cũ nghỉ; thống kê tải việc theo người.
- Ngoài (Amendment 1, mục 13): feature không dọn hay sửa dữ liệu site `miyano` (SLA rác, link Assignment Rule hỏng, HD Agent, role thừa của tài khoản agent, team còn thiếu). Đó là phần việc của người trong DoD.

## Dữ liệu
**Thang điểm** (giá trị chọn ở Assumptions A-1):

| Điểm | Độ phức tạp | Độ quan trọng |
|---|---|---|
| 1 | Làm xong dưới 1 giờ làm việc, không cần đổi hệ thống: hỏi đáp, thao tác có sẵn | Ảnh hưởng một người, không chặn việc, không có hạn gần |
| 2 | Trong 1 ngày làm việc: cấu hình có sẵn, sửa một lỗi xác định, một đợt dữ liệu nhỏ | Chặn việc của một người hoặc một bộ phận; hoặc có hạn trong 24 giờ; hoặc (đầu mục D) có Hạn hoàn thành |
| 3 | Nhiều ngày, cần phân tích trước (BA), xây mới hoặc tích hợp | Chặn nghiệp vụ kế toán, kho hoặc bán hàng; hoặc nhiều bộ phận ngừng việc |

**Quy tắc mức ưu tiên.** Xét lần lượt, gặp quy tắc nào khớp đầu tiên thì dừng (giá trị ở Assumptions A-2):
- R1. Tiêu đề có `[GẤP]`/`[GẬP]` → `Urgent` (quy ước 1, `classification.py:11-12`, giữ nguyên).
- R2. Đầu mục F → `Low`.
- R3. Đầu mục E → bot không ghi ưu tiên, vì bảng 16.2 ghi "theo COO đặt".
- R4. Đầu mục A có độ quan trọng 3 → `Urgent` (16.2: "Urgent nếu chặn nghiệp vụ kế toán/kho").
- R5. Còn lại → lấy mức cao hơn giữa (mức mặc định của đầu mục trong ánh xạ) và (mức theo độ quan trọng: 2 hoặc 3 → `High`, 1 → không nâng). Hai ngoại lệ "B: High nếu có hạn trong 24h" và "D: High nếu có Hạn hoàn thành" đi qua độ quan trọng 2.
- Bảng "độ quan trọng → mức tối thiểu" nằm trong cấu hình, sửa được. R1–R4 là quy ước nghiệp vụ, cố định.
- Độ phức tạp không đổi mức ưu tiên. Nó là đầu vào để người cấu hình chọn SLA qua `condition` (A-3), và nằm trong lời giải thích cho người phụ trách.

**Thông tin mới cần lưu và xem lại được:**
- Trên phiếu (từ `L1`): độ phức tạp, độ quan trọng, lý do chấm (≤ 25 từ, cùng giới hạn với `ly_do` ở `prompts.py`). Người phụ trách xem được. `condition` của SLA phải đọc được độ phức tạp. Chọn trường nào, permlevel nào là việc của designer. [changed] (Amendment 1, mục 3: điểm là số nguyên, 0 = "không có điểm/chưa chấm", không bao giờ rỗng; cùng mức phân quyền với các trường AI khác theo ADR-020 QĐ 5)
- Trong nhật ký ERP AI Log (mọi mức): 2 điểm, lý do, nhóm, người và mức ưu tiên dự kiến; giá trị trước/sau khi ghi.

**Cấu hình mới** (System Manager sửa; nơi đặt và hình dạng do designer chọn):
- Bảng người mặc định theo đầu mục, có thể khác theo tiền tố tiêu đề (16.2: A → ERP core, nhưng `[tracecore]` → người phụ trách tracecore/app riêng).
- Bảng bộ phận → nhóm và trưởng bộ phận, dùng cho D/E.
- Bảng độ quan trọng → mức ưu tiên tối thiểu (R5).
- Bảng SLA mong đợi theo đầu mục, lấy từ 16.2: phản hồi / xử lý. Nguồn: QĐ-1.
- Công tắc tự gán người và tạo Task.
- Không giá trị nào trong các bảng trên được viết cứng trong code (QĐ-4, STD-DESIGN-7).

**Khối lượng:** vài chục phiếu mỗi tháng (tài liệu triển khai ghi 71 phiếu ở thời điểm khảo sát, `docs/HuongDan_TrienKhai_erp-ai.md:1035`).

**Dữ liệu nhạy cảm:** tên và email người phụ trách đã có trên hệ thống. Không thêm dữ liệu cá nhân mới. Nội dung phiếu không được chép vào nhật ký lỗi (giữ NFR-4' hiện có).

## Giao diện / tích hợp
- **Helpdesk, gán người:** dùng cơ chế gán sẵn có (ToDo, thông báo, email). Không thêm kênh thông báo mới.
- **Helpdesk, SLA:** chỉ đọc kết quả (`sla`, `response_by`, `resolution_by`) sau khi lưu phiếu. Không tạo, không sửa bản ghi SLA.
- **Task (ERPNext Projects):** tạo Task, giao người, có tham chiếu tới phiếu. Cách tham chiếu để quy ước 3 ("C/D có ≥ 1 Task liên kết") đếm được là việc của designer.
- **Cổng model:** dùng lại các bước hiện có. Không thêm lời gọi model nào cho mỗi phiếu (NFR-1).
- **Eval offline** (`erp_ai/eval/`): thêm chỉ số ưu tiên và nhóm.
- **Câu hỏi cho architect** (analyst không quyết):
  - Q-A1: tạo Task và gán người khi không có "người ra lệnh" là nới ADR-005 Quyết định 1 (`create_task` hiện chỉ có khi có người ra lệnh). Cần ADR mới, hoặc ADR sửa đổi. [changed] (Amendment 1, mục 1: đã trả lời, ADR-019)
  - Q-A2: tài khoản agent có đủ quyền gán (ToDo, Task) với bộ role hiện có ({`ERP AI Agent`, `Agent`}, ADR-006) không, hay phải thêm quyền vào role `ERP AI Agent`. [changed] (Amendment 1, mục 1: đã trả lời, ADR-021)
  - Q-A3: thứ tự giữa bước gán của bot và Assignment Rule của Helpdesk khi bot đổi nhóm sau lúc tạo phiếu (`hd_ticket.py:428-481`). [changed] (Amendment 1, mục 1: đã trả lời, ADR-020)
  - Q-A4: chấm điểm ở bước phân loại hay bước suy luận. Spec chỉ đòi điểm có ở `L0` và đo được bằng eval offline (A-4). [changed] (Amendment 1, mục 1: đã trả lời, ADR-019)

## NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Số lời gọi model cho mỗi phiếu mới không tăng so với nhánh nền: 1 lời gọi phân loại + số lượt suy luận như hiện nay. Nguồn: hành vi hiện có (`runner.py:128-135`) | Test runner với stub cổng model: đếm lời gọi theo loại, so với số đếm của cùng kịch bản trên nhánh nền |
| NFR-2 | Không thêm bản ghi cấu hình Helpdesk nào: số bản ghi HD Service Level Agreement, HD Team, Assignment Rule trước/sau một lần chạy bằng nhau. Nguồn: QĐ-5 | Test đếm bản ghi trước/sau |
| NFR-3 | Không có giới hạn thời gian mới. Lần chạy vẫn nằm trong `JOB_TIMEOUT_S` hiện có. Intake không cho số mới nên không đặt ngưỡng (A-8) | Test runner hiện có vẫn xanh |
| NFR-4 | Không lộ dữ liệu nhạy cảm: khóa API giả gieo vào cấu hình xuất hiện 0 lần trong comment, nhật ký và mô tả Task. Nguồn: cách làm NFR-5 của FEAT-001 | Test tự động |

## Tiêu chí nghiệm thu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Với mỗi phiếu mới có trả lời hợp lệ từ model, nhật ký có độ phức tạp ∈ {1,2,3}, độ quan trọng ∈ {1,2,3}, lý do ≤ 25 từ, ở cả `L0` lẫn `L1`. Model trả điểm ngoài khoảng, thiếu điểm hoặc sai kiểu → coi như không có điểm: mức ưu tiên lấy theo ánh xạ đầu mục như hiện nay, nhật ký ghi rõ "không có điểm" [changed] (Amendment 1, mục 3) | Test tự động với stub cổng model: 1 ca hợp lệ ở mỗi mức; 1 ca cho mỗi kiểu sai (0, 4, chuỗi, thiếu khóa) |
| AC-2 | Ở `L1` trở lên, sau lần chạy, trên phiếu có độ phức tạp, độ quan trọng, lý do. Một user có role `Agent` (không phải System Manager) đọc được 3 giá trị đó. Ở `L0`, trên phiếu không có giá trị nào đổi | Test tự động: đọc phiếu dưới user Agent; so giá trị phiếu trước/sau ở `L0` |
| AC-3 | Mức ưu tiên đúng quy tắc R1–R5 cho từng ô của bảng (đầu mục A–F × độ quan trọng 1–3 × có/không `[GẤP]`), tổng 36 ca. Mẫu: B + quan trọng 2 → `High`; C + quan trọng 1 → `Medium`; A + quan trọng 3 → `Urgent`; F + quan trọng 3 → `Low`; E → mức ưu tiên trên phiếu không đổi; mọi đầu mục + `[GẤP]` → `Urgent` | Test tham số hóa 36 ca trên hàm tính ưu tiên, và 1 test đầu-cuối qua runner |
| AC-4 | Sửa bảng "độ quan trọng → mức tối thiểu" trong cấu hình (ví dụ quan trọng 2 → `Medium`) thì lần chạy kế tiếp dùng giá trị mới, không cần deploy. Cấu hình sai dạng bị chặn khi lưu, có thông báo nêu chỗ sai | Test tự động: đổi cấu hình rồi chạy; lưu cấu hình sai → `ValidationError` |
| AC-5 | Nhóm: A/B/C/F ghi nhóm theo ánh xạ như hiện nay. D/E ghi nhóm của bộ phận mà model chọn, chỉ khi bộ phận đó có trong bảng bộ phận → nhóm, nhóm có tồn tại, và nhóm không nằm trong `excluded_teams`. Ngược lại thì không ghi nhóm, và nhật ký ghi lý do bỏ qua | Test tự động: 1 ca hợp lệ; 1 ca cho mỗi lý do bỏ qua |
| AC-6 | Người phụ trách: khi công tắc bật, ở `L1`+, phiếu chưa có ai được gán và chưa do người phân loại, bot gán đúng 1 người theo bảng người mặc định (có tính tiền tố tiêu đề). Người đó nhận đúng 1 thông báo gán của Helpdesk. Người cấu hình không phải HD Agent đang hoạt động → không gán, nhật ký ghi lý do [changed] (Amendment 1, mục 4) | Test tự động: đếm ToDo đang mở và Notification Log của người được gán; 1 ca `[tracecore]`; 1 ca người không hợp lệ |
| AC-7 | Không ghi đè: (a) phiếu đã có người được gán (bất kể ai gán) → danh sách người gán không đổi; (b) `ai_classified_by` là người → nhóm và người không đổi; (c) công tắc tắt → 0 ToDo mới, 0 Task mới, phần phân loại vẫn ghi như hiện nay; (d) ở `L0` → 0 ToDo, 0 Task [changed] (Amendment 1, mục 5) | Test tự động, mỗi nhánh một test |
| AC-8 | Bot không bao giờ gán tài khoản agent làm người phụ trách, kể cả khi cấu hình ghi tài khoản đó. Hệ quả: phiếu `Chỉ đạo BGĐ` luôn có người phụ trách là con người hoặc chưa có ai (quy ước 2). Không có người hợp lệ → 1 comment xin người phân công | Test tự động: cấu hình trỏ tới tài khoản agent → 0 ToDo cho tài khoản đó, có đúng 1 comment |
| AC-9 | Chống chèn lệnh: phiếu chứa câu như "giao cho <tên user khác>", "SLA 1 phút", "đặt Urgent", "assign to Administrator" (không có tag `[GẤP]`) → người được gán là người theo cấu hình (hoặc không ai), mức ưu tiên theo R2–R5, SLA do Helpdesk chọn. Không tool nào bot gọi được nhận tên người, tên SLA hay mức ưu tiên làm tham số | Test tự động với stub model "bị dụ" (stub trả về đúng các yêu cầu đó trong lời gọi tool) → bị từ chối hoặc bỏ qua; test tĩnh: schema mọi tool trong registry không có thuộc tính chỉ người, SLA hay ưu tiên |
| AC-10 | SLA do Helpdesk tính: trong test tạo 2 SLA, gồm 1 SLA mặc định và 1 SLA có `condition` theo độ phức tạp = 3. Phiếu độ phức tạp 3 nhận SLA thứ hai, phiếu độ phức tạp 1 nhận SLA mặc định. Cả hai có `response_by`, `resolution_by` khác rỗng. Code của feature không gán `response_by`/`resolution_by` [changed] (Amendment 1, mục 8) | Test tự động; `grep -rnE "response_by\|resolution_by" erp_ai/agent/` không có phép gán |
| AC-11 | Thiếu SLA: site không có SLA nào áp vào phiếu → phiếu vẫn lưu với mức ưu tiên đúng. Có đúng 1 dòng cảnh báo trong nhật ký và đúng 1 comment "chưa có SLA áp vào phiếu, cần System Manager cấu hình". Số bản ghi SLA trước/sau bằng nhau (NFR-2) | Test tự động: tắt mọi SLA trong test, chạy, đếm comment/nhật ký/SLA |
| AC-12 | SLA lệch mức mong đợi: SLA đang áp cho mức ưu tiên của phiếu có thời hạn xử lý dài hơn mức 16.2 trong cấu hình cho đầu mục đó → 1 dòng cảnh báo trong nhật ký nêu 2 con số. Đầu mục có mức "theo Hạn hoàn thành" (D, E) không bị kiểm | Test tự động: 1 ca lệch, 1 ca khớp, 1 ca D |
| AC-13 | Task C/D: ở `L1`+, công tắc bật, đầu mục C hoặc D, đã chọn được người → đúng 1 Task có tham chiếu tới phiếu, giao cho người đó. Chạy lại cho cùng phiếu → vẫn 1 Task. Phiếu đã có Task liên kết (người tạo) → 0 Task mới. Đầu mục khác, hoặc không chọn được người → 0 Task (không người thì có 1 comment xin phân công, dùng chung với AC-8) [changed] (Amendment 1, mục 6) | Test tự động: đếm Task theo phiếu ở mỗi nhánh |
| AC-14 | Đổi người mặc định chỉ bằng sửa cấu hình: đổi người của đầu mục B trong cấu hình → phiếu B kế tiếp được gán người mới, và phần routing trong prompt suy luận hiện người mới. Không file `.py` nào trong `erp_ai/agent/` chứa danh sách người mặc định của bảng 16.2 | Test tự động; test so prompt trước/sau khi đổi cấu hình |
| AC-15 | Eval offline: chạy export + eval trên phiếu cũ đã có nhãn → báo cáo có thêm tỷ lệ khớp mức ưu tiên (dự đoán so với `priority` người đặt), tỷ lệ khớp nhóm, và phân bố điểm phức tạp/quan trọng. Vẫn dùng chung request với runner | Test `compute_metrics` với dữ liệu mẫu; chạy lệnh eval thật trên site dev và dán đầu ra vào acceptance.md |
| AC-16 | Truy vết: mỗi lần ghi (ưu tiên, nhóm, người, Task) có trong `actions` của nhật ký, kèm giá trị trước/sau. Người được gán ghi bằng user ID. Lần bị từ chối có `ok=false` kèm lý do | Test tự động đếm dòng nhật ký theo từng việc |
| AC-17 | Không đổi role: mọi ca thành công của AC-2..AC-13 chạy dưới tài khoản agent với đúng bộ role theo ADR hiện hành. `check_privilege_escalation` không có cảnh báo mới. `cmd.test` xanh [changed] (Amendment 1, mục 7) | Test chạy dưới tài khoản agent; `cd ../.. && bench --site miyano run-tests --app erp_ai` |
| AC-18 | (Amendment 1, mục 9) SLA có `condition` lỗi: một SLA đang bật có `condition` gây lỗi khi Helpdesk đánh giá → lần chạy của bot kết thúc bình thường (không ngoại lệ lọt ra ngoài job); nhật ký có lỗi của lần lưu phiếu (lớp ngoại lệ, không có nội dung phiếu); 0 ToDo mới, 0 Task mới, 0 comment do bước định tuyến; giá trị trên phiếu trước = sau | Test tự động: tạo phiếu, rồi bật 1 SLA có `condition` lỗi, chạy runner ở `L1` với công tắc bật; đếm ToDo/Task/comment, so giá trị phiếu, đọc nhật ký |

Thứ tự bỏ trước nếu phải cắt (cỡ L, bước 8): AC-12 (SLA lệch mức) → AC-15 phần phân bố điểm → AC-14 phần prompt. AC-1..AC-11, AC-13, AC-16, AC-17 là lõi, không cắt. [changed] (Amendment 1, mục 9: AC-18 cũng là lõi, không cắt)

## Assumptions decided by the team
| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-1 | Thang 1–3 cho cả hai điểm, định nghĩa như bảng ở mục Dữ liệu | Đủ phân biệt cho khoảng 6 đầu mục và vài chục phiếu/tháng. Mỗi mức có mô tả nghiệp vụ, nên model và người chấm giống nhau dễ hơn thang 1–5 | Thang 1–5; nhãn chữ Thấp/Vừa/Cao | Đổi thang qua change-request; AC-1, AC-3 đổi theo |
| A-2 | Độ quan trọng quyết định mức ưu tiên (R1–R5). Độ phức tạp không đổi mức ưu tiên | Theo bảng 16.2, mức ưu tiên phụ thuộc mức chặn việc và hạn, không theo độ khó. Thời gian xử lý khác nhau theo độ khó thì do SLA lo (A-3) | Ma trận quan trọng × phức tạp → ưu tiên | Sửa bảng R5 trong cấu hình (AC-4); muốn thêm chiều phức tạp thì change-request |
| A-3 | "SLA theo độ phức tạp" = Helpdesk chọn SLA theo `condition` đọc độ phức tạp trên phiếu. Bản ghi SLA do người (hoặc FEAT-005) tạo | QĐ-1 và QĐ-5: không tự tính hạn, không ghi cấu hình Helpdesk | Bot tự ghi hạn chót; bot tạo SLA | Change-request sau FEAT-005 |
| A-4 | Điểm có ở mọi mức (kể cả `L0`), dùng chung request với eval offline. Chấm ở bước nào là việc của architect (Q-A4) | `L0` chỉ chạy phân loại. Muốn đo trên phiếu cũ thì điểm phải nằm trong request mà eval dùng | Chấm ở bước suy luận, chỉ từ `L1` | Bỏ yêu cầu `L0` trong AC-1; AC-15 đo bằng cách khác |
| A-5 | Chọn người theo bảng người mặc định trong cấu hình. Nếu phiếu đã có người gán (kể cả do Assignment Rule của Helpdesk gán) thì bot không gán thêm [changed] (Amendment 1, mục 4) | Đúng bảng 16.2 (người cụ thể theo đầu mục). Không giành việc (QĐ-3). Nếu nhóm đã có rule thì đó là chủ ý của người cấu hình | Luôn dùng rule của nhóm; bot cân tải theo số phiếu mở | Đổi điều kiện trong tool; muốn cân tải thì change-request |
| A-6 | Tự gán người và tạo Task chạy từ `L1`, nhưng có công tắc riêng, tắt sẵn khi cài | Gán người gửi email/thông báo cho người thật, nên phải được bật có chủ ý (cùng tinh thần "tắt sẵn" của ADR-006) | Gắn với `L2` | Đổi mức trong ADR mới; bật/tắt công tắc |
| A-7 | Bot không bao giờ tự gán tài khoản agent, kể cả đầu mục F (bảng 16.2 ghi `ai.agent`) | Quy ước 2 (BGĐ luôn có người là con người) đúng mà không cần đọc trường "Nguồn phát sinh". Phiếu F vẫn được bot trả lời như hiện nay | Cho gán agent ở F trừ phiếu BGĐ | Change-request thêm ngoại lệ F |
| A-8 | Không đặt ngưỡng độ trễ hay ngưỡng độ đúng mới làm cổng build. Eval chỉ báo số. Ngưỡng 0,85/0,70 hiện có được dùng để đọc kết quả | Intake không cho số. Không bịa NFR | Đặt ngưỡng ≥ 0,85 cho ưu tiên | Khi có số thật từ AC-15, thêm AC qua amend |
| A-9 | Trên phiếu có thể chưa có trường "Hạn hoàn thành" và "Nguồn phát sinh" (không thấy trong code của `erp_ai`/`helpdesk`; chỉ có trong tài liệu triển khai). Khi đó model đọc hạn từ nội dung phiếu để chấm độ quan trọng. Quy ước 2 vẫn giữ nhờ A-7 [changed] (Amendment 1, mục 13: đã xác minh trên site) | Không đọc được DB (role-policy) | Bắt buộc có trường trước khi làm | Designer xác minh trên site. Nếu có trường thì R5 đọc thẳng trường đó |
| A-10 | Site có thể chỉ có SLA mặc định của Helpdesk (`install.py:66-75`). Feature vẫn chạy được, và AC-11/AC-12 báo phần thiếu [changed] (Amendment 1, mục 13: site có thêm SLA rác đang bật) | Không đọc được DB | Chờ FEAT-005 tạo SLA | Designer hoặc researcher liệt kê SLA trên site; cập nhật cấu hình |
| A-11 | Người tạo phiếu có thể thổi phồng độ quan trọng bằng lời. Rủi ro này được chấp nhận: mức cao nhất từ điểm chấm là `High`, trừ đầu mục A quan trọng 3 → `Urgent` (đúng như 16.2). Tag `[GẤP]` vẫn là quy ước công khai | Nội dung phiếu là dữ liệu, nhưng muốn chấm thì phải đọc nó. Giới hạn trần thay cho cấm | Chỉ người mới được nâng lên trên `Medium` | Hạ trần trong bảng R5 (AC-4) |
| A-12 | (Amendment 1, mục 6) Bot chỉ tạo Task cho người chính nó vừa gán trong cùng lần chạy. Phiếu C/D đã có người được gán từ trước (do người, hoặc do Assignment Rule, kể cả rule gán trong lần lưu nhóm của bot) → 0 Task, 0 comment, nhật ký ghi lý do | Không giành việc (QĐ-3): Task là việc giao kèm lần gán của bot; người đã nhận phiếu tự quyết có tách Task hay không. Khớp mặc định G-3 của architect, ADR-020 QĐ 3 không phải đổi | Tạo Task cho đúng người đã được gán sẵn | Change-request đổi AC-13 nhánh (ii) và một câu của ADR-020 QĐ 3; quy ước 3 ("C/D có ≥ 1 Task") khi đó do người đã nhận phiếu bảo đảm |
| A-13 | (Amendment 1, mục 13) Dữ liệu site `miyano` lệch (research-site mục 1–6) là phần việc của người, làm trước khi bật công tắc. Feature không dọn, không viết patch sửa. Không test nào dựa vào dữ liệu site; test tự tạo team, HD Agent, SLA của mình | QĐ-5 (không ghi cấu hình Helpdesk), STD-OPS-7 (agent không thao tác trực tiếp dữ liệu thật), ADR-006 (role chỉ do thủ tục cài đặt). Site đang ở `L3`, nên công tắc là chốt chặn duy nhất của việc gán/Task | Thêm patch cài đặt dọn dữ liệu site; gộp vào FEAT-005 | Change-request (có thể gộp FEAT-005); cho tới lúc đó giữ công tắc tắt |
| A-14 | (Amendment 1, mục 13) Trên site không có team `Tài chính Kế toán`, và `excluded_teams` đang rỗng (khác mặc định). Feature giữ hành vi AC-5: bộ phận trỏ tới nhóm không tồn tại → không ghi nhóm, nhật ký ghi lý do | AC-5 đã định nghĩa nhánh này; `excluded_teams` là cấu hình người giữ từ FEAT-001 | Bot đoán nhóm gần nhất; dùng giá trị mặc định của `excluded_teams` khi rỗng | Người tạo team hoặc sửa bảng bộ phận → nhóm; người điền lại `excluded_teams` |

## Definition of Done
Phần build (trong các task):
- [ ] Mọi AC-1..AC-17 đạt, đầu ra lệnh được dán trong `acceptance.md` [changed] (Amendment 1, mục 9: AC-1..AC-18)
- [ ] Mỗi AC có ít nhất 1 test tự động hoặc 1 bước kiểm có đầu ra (STD-TEST-2); không skip/xfail
- [ ] ADR mới hoặc sửa đổi cho Q-A1 (nới ADR-005: ghi không cần người ra lệnh), và Q-A2 nếu đổi quyền role [changed] (Amendment 1, mục 1: ADR-019..ADR-021 đã viết; Q-A2 có đổi quyền của role, không đổi tập role)
- [ ] Cấu hình mới có giá trị cài đặt mặc định: bảng 16.2 cho SLA mong đợi; công tắc tắt; danh sách người rỗng hoặc do người điền. Cài lại không ghi đè giá trị người đã sửa (ADR-006)
- [ ] `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`) xanh; `cmd.lint` (`pre-commit run --all-files`) sạch
- [ ] `cmd.migrate` chạy được trên site dev nếu có thay đổi trường/DocType
- [ ] Làm trên nhánh `team/FEAT-006` trong worktree riêng (intake: phiên khác đang build FEAT-003 ở worktree chính)
- [ ] (Amendment 1) Test AC-6, AC-10, AC-11, AC-18 tự tạo team, HD Agent, SLA; không dùng team `IT`, SLA `Standard`/`SLA Priority` hay HD Agent có sẵn trên site (A-13)
- [ ] (Amendment 1) Test ghim tập role của tài khoản agent trả lại tập role cũ khi xong; số Has Role của tài khoản agent trước = sau cả bộ test (AC-17)

Phần sau G4 (`/team:asbuilt`; G4 tắt nên làm ngay sau verify):
- [ ] As-Built viết xong (`docs/team/features/FEAT-006/asbuilt.md`)
- [ ] Tài liệu người dùng cập nhật: cách đọc điểm, cách sửa bảng người mặc định và các bảng mức, cách tạo SLA theo độ phức tạp [changed] (Amendment 1, mục 4, 7, 10: thêm 3 dòng dưới)
- [ ] (Amendment 1, mục 10) Tài liệu người dùng: mẫu `condition` an toàn trên trường điểm (điểm 0 = chưa chấm); cảnh báo `condition` lỗi chặn mọi lần lưu phiếu, của cả người lẫn bot; thử trên một phiếu trước khi bật SLA
- [ ] (Amendment 1, mục 4) Tài liệu người dùng: nhóm có Assignment Rule đang bật thì rule gán, bảng người mặc định không có hiệu lực; muốn dùng bảng thì tắt rule của nhóm
- [ ] (Amendment 1, mục 7) Tài liệu người dùng: gỡ role thừa của tài khoản agent (chỉ giữ {`ERP AI Agent`, `Agent`}) trước khi bật công tắc
- [ ] Mục CHANGELOG
- [ ] CI xanh trên PR

Phần việc của người (Amendment 1, mục 13; trên site `miyano`, trước khi bật công tắc tự gán; không phải điều kiện merge; không agent nào làm, STD-OPS-7). Nguồn: `research-site.md` mục 1–6, đọc DB ngày 2026-11-12. Mỗi dòng có một câu `SELECT` để kiểm (chạy từ `/home/miyano/frappe-bench`, `bench --site miyano mariadb -e "<câu>"`):
- [ ] Gỡ 97 role thừa khỏi tài khoản agent (đang 99 role, có `System Manager`; BUG-002). Kiểm: `SELECT COUNT(*) FROM tabHas Role WHERE parenttype='User' AND parent='ai.agent@miyano.com.vn'` → `2`
- [ ] Tắt hoặc xóa SLA rác `SLA Priority` (rác test của helpdesk, đang bật, `condition` bắt `High`/`Urgent`/`Low`, dùng `Test Holiday List`), nếu không dùng thì dọn cả `Test Holiday List`, `_Test Holiday List`. Kiểm: `SELECT name FROM tabHD Service Level Agreement WHERE enabled=1` → chỉ `Standard` và SLA do người tạo
- [ ] Sửa link Assignment Rule hỏng của team `IT` và `Nhân sự & Hành chính` (tạo lại rule hoặc bỏ link); nếu không sửa, lần lưu phiếu đổi sang hai team này có thể lỗi và bot dừng theo AC-18. Kiểm: `SELECT t.name FROM tabHD Team t LEFT JOIN tabAssignment Rule r ON r.name=t.assignment_rule WHERE t.assignment_rule IS NOT NULL AND t.assignment_rule<>'' AND r.name IS NULL` → 0 dòng
- [ ] Tạo HD Agent đang hoạt động cho mọi người sẽ ghi vào bảng người mặc định (site đang có 0 HD Agent; nếu không, AC-6 không gán ai và mỗi phiếu nhận 1 comment xin phân công theo AC-8). Kiểm: `SELECT COUNT(*) FROM tabHD Agent WHERE is_active=1` ≥ số người trong bảng
- [ ] Điền bảng người mặc định và bảng bộ phận → nhóm; tạo team cho bộ phận còn thiếu (ví dụ `Tài chính Kế toán`) hoặc bỏ bộ phận đó khỏi bảng (A-14). Kiểm: lưu ERP AI Setting không báo lỗi (AC-4)
- [ ] Xem lại `excluded_teams` (đang rỗng, khác mặc định 2 team) (A-14). Kiểm: `SELECT value FROM tabSingles WHERE doctype='ERP AI Setting' AND field='excluded_teams'`
- [ ] Tắt Assignment Rule của nhóm nào muốn dùng bảng người mặc định (`Billing`, `Product Experts` đang có rule bật, chưa có người). Kiểm: `SELECT name, disabled FROM tabAssignment Rule`
- [ ] Sau cùng mới bật công tắc tự gán người và tạo Task (site đang ở `L3`)

## Amendment 1 (2026-11-12)
Nguồn: `docs/team/features/FEAT-006/arch-impact.md` mục "Mục spec phải sửa (cho analyst `--amend`)" (11 mục); `docs/team/features/FEAT-006/research-site.md` mục 1–6 (qa đọc DB, chỉ `SELECT`, 2026-11-12); lệnh của team-leader, mode `decide`. Văn bản cũ giữ nguyên. Dòng bị đổi có dấu `[changed]` và trỏ tới mục dưới. Khi dòng cũ và mục dưới khác nhau, mục dưới thắng.

### Các thay đổi
1. **Q-A1..Q-A4 đã trả lời.** Q-A1 và Q-A4: ADR-019. Q-A2: ADR-021. Q-A3: ADR-020. Q-A2 **có** đổi quyền của role `ERP AI Agent` (thêm `share` trên Task do chính tài khoản agent tạo), **không** đổi tập role. Dòng DoD về ADR được thỏa bằng ADR-019..ADR-021 và dòng trạng thái bổ sung trên ADR-004, ADR-005, ADR-006, ADR-015 (arch-impact mục ADR).
2. **Constraints.** Giữ "Không đổi role tài khoản agent (ADR-006)". Thêm: quyền của role `ERP AI Agent` có thêm `share` trên Task do chính tài khoản agent tạo (ADR-021).
3. **Điểm trên phiếu.** Điểm là số nguyên; 0 = "không có điểm / chưa chấm"; không bao giờ rỗng, kể cả phiếu cũ và phiếu ở `L0`. Cùng mức phân quyền với các trường AI khác (ADR-006, ADR-020 QĐ 5). AC-1: "không có điểm" ghi lên phiếu (từ `L1`) là 0. Phiếu cũ có điểm 0, không chuyển dữ liệu.
4. **"Phiếu chưa có ai được gán" (A-5, AC-6).** Nghĩa là phiếu không có việc gán (ToDo) nào ở trạng thái khác `Cancelled`. Điều kiện này xét **sau** lần lưu nhóm của bot. Nhóm đích có Assignment Rule đang bật và có user → rule gán trong chính lần lưu đó; bot không gán; nhật ký ghi tên rule. Test AC-6 dùng nhóm không có rule đang bật. Thêm 1 ca test: nhóm có rule đang bật có user → 0 lần gán của bot, đúng 1 người do rule gán, nhật ký có tên rule.
5. **AC-7(a).** "Bất kể ai gán" gồm cả Assignment Rule gán trong cùng lần lưu nhóm của bot.
6. **AC-13 thêm 2 nhánh.**
   - (i) Site bật `disable_document_sharing` mà người được giao không đọc được Task → 0 Task, 1 comment xin phân công, nhật ký `ok=false`.
   - (ii) Luật đã chốt (A-12): phiếu C/D đã có người được gán từ trước lần gán của bot → 0 Task, 0 comment, nhật ký ghi lý do. Bot chỉ tạo Task cho người chính nó vừa gán.
7. **AC-17.** Mọi ca thành công chạy dưới tài khoản agent với tập role {`ERP AI Agent`, `Agent`}, do test ghim lúc đầu ca và trả lại khi xong. "`check_privilege_escalation` không có cảnh báo mới" = tập mục cảnh báo trước = sau lần chạy; cảnh báo role thừa đang có trên site không tính.
8. **AC-10 thêm ca.** Một SLA đang bật có `condition` dạng `>=` trên trường độ phức tạp → phiếu ở `L0` và phiếu mới (điểm 0) vẫn lưu được (ADR-020 Ràng buộc).
9. **Thêm AC-18 (lõi, không cắt).** SLA có `condition` lỗi → lần chạy kết thúc bình thường, nhật ký có lỗi của lần lưu, 0 ToDo, 0 Task, phiếu trước = sau (ADR-020 QĐ 6).
10. **DoD phần sau G4.** Tài liệu người dùng thêm mẫu `condition` an toàn trên trường điểm và cảnh báo `condition` lỗi chặn mọi lần lưu phiếu.
11. **Ghi nhận, không đổi chữ tiêu chí.**
    - AC-11, AC-12: bot đọc SLA bằng phép đọc hệ thống chỉ-đọc, vì role `Agent` không đọc được HD Service Level Agreement (ADR-021 QĐ 4). Test AC-11 phải tắt cả `Standard` lẫn SLA tự tạo (site còn có `SLA Priority`, research-site mục 1).
    - AC-14 phần prompt: prompt suy luận nền đổi, đụng các test "trùng từng byte" của FEAT-004/005. Thứ tự merge FEAT-003 → FEAT-004 → FEAT-005 → FEAT-006 (arch-impact mục Thứ tự merge).
12. **Giả thuyết.** Hai điều còn thiếu đã được xác minh trên site: không có trường "Hạn hoàn thành"/"Nguồn phát sinh" (A-9); có SLA `Standard` và SLA rác `SLA Priority` (A-10). Độ tin cậy lên 85%. Còn thiếu một điều: trần token của bước phân loại chưa được đo với các khóa điểm mới (designer đo trên eval, arch-impact mục Rủi ro).
13. **Dữ liệu site `miyano`** (research-site mục 1–6). Chỉ là đầu vào cho phần việc của người. Không phải căn cứ của tiêu chí hay test (A-13):
    - SLA: 2 SLA đang bật. `Standard` (mặc định, không `condition`). `SLA Priority` (rác test helpdesk, `condition` `doc.priority in ['High','Urgent','Low']`, lịch nghỉ `Test Holiday List`). Thời hạn 4 mức ưu tiên giống nhau ở hai SLA. Phiếu bot đặt `High`/`Urgent`/`Low` có thể nhận SLA rác thay cho `Standard`. 6 phiếu hiện có đều `Standard`, `Medium`.
    - HD Team: `Billing`, `Product Experts` có rule bật nhưng 0 user. `IT` và `Nhân sự & Hành chính` trỏ tới Assignment Rule không còn tồn tại. Không có team `Tài chính Kế toán`.
    - HD Agent: 0 bản ghi. 2 user có role `Agent`, đều chưa có HD Agent.
    - HD Ticket: không có trường "Hạn hoàn thành"/"Nguồn phát sinh". A-9 đúng, giữ nhánh "model đọc hạn từ nội dung phiếu".
    - Tài khoản agent: 99 role, có `System Manager` (BUG-002, chưa gỡ). Quyền tạo Task đã có qua dòng quyền Task của app (`if_owner`).
    - ERP AI Setting: `category_mapping` trùng mặc định; `excluded_teams` rỗng; `permission_level = L3`.

### Bản đầy đủ của các tiêu chí `[changed]` sau Amendment 1
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 [changed] | Như AC-1, thêm: ở `L1`+, khi "không có điểm" thì hai điểm trên phiếu là 0, lý do chấm rỗng; ở mọi mức không ô điểm nào trên phiếu rỗng (NULL) | Như AC-1; thêm kiểm giá trị trường điểm trên phiếu = 0 ở các ca sai kiểu, và ≠ NULL ở phiếu `L0` |
| AC-6 [changed] | Như AC-6, với "phiếu chưa có ai được gán" = không có ToDo của phiếu ở trạng thái khác `Cancelled`, xét sau lần lưu nhóm của bot. Nhóm đích có Assignment Rule bật có user → bot không gán, nhật ký ghi tên rule | Như AC-6 (dùng nhóm không có rule bật); thêm 1 ca nhóm có rule bật có user: 0 ToDo do bot, đúng 1 ToDo do rule, nhật ký có tên rule |
| AC-7 [changed] | Như AC-7; nhánh (a) gồm cả Assignment Rule gán trong cùng lần lưu nhóm của bot | Như AC-7; nhánh (a) có thêm 1 ca rule gán trong lần lưu nhóm |
| AC-10 [changed] | Như AC-10, thêm: 1 SLA đang bật có `condition` dạng `>=` trên trường độ phức tạp → phiếu ở `L0` và phiếu mới (điểm 0) vẫn lưu được, không lỗi | Như AC-10; thêm 1 test tạo phiếu ở `L0` và 1 phiếu mới khi SLA đó đang bật |
| AC-13 [changed] | Như AC-13, thêm 2 nhánh: (i) site bật `disable_document_sharing` mà người được giao không đọc được Task → 0 Task, 1 comment xin phân công, `ok=false`; (ii) phiếu C/D đã có người được gán từ trước lần gán của bot (người hoặc rule) → 0 Task, 0 comment, nhật ký ghi lý do (A-12) | Như AC-13; thêm 1 test cho (i), 2 test cho (ii) (người gán sẵn; rule gán trong lần lưu nhóm) |
| AC-17 [changed] | Mọi ca thành công AC-2..AC-13 và AC-18 chạy dưới tài khoản agent với tập role {`ERP AI Agent`, `Agent`}, do test ghim lúc đầu ca và trả lại khi xong. `check_privilege_escalation`: tập mục cảnh báo trước = sau lần chạy (cảnh báo role thừa đang có không tính). `cmd.test` xanh | Test chạy dưới tập role đã ghim; đếm Has Role của tài khoản agent trước = sau; so tập cảnh báo trước/sau; `cd ../.. && bench --site miyano run-tests --app erp_ai` |
| AC-18 | Xem dòng AC-18 trong bảng Tiêu chí nghiệm thu | Xem dòng AC-18 |

### Artifact sau bị ảnh hưởng (để team-leader định tuyến)
- `arch-impact.md`, ADR-019..ADR-021: không phải sửa. A-12 khớp mặc định G-3, ADR-020 QĐ 3 giữ nguyên.
- `design.md` (chưa có): designer đọc Amendment 1. Phải có ca test mới của AC-6, AC-7(a), AC-10, AC-13 (i)/(ii), AC-18, và helper ghim role của AC-17.
- `tasks.md` (chưa có): không có gì để chèn. Bước kế: `/team:design FEAT-006`.
- Tài liệu người dùng, As-Built: 3 dòng DoD mới ở phần sau G4. Phần việc của người do team-leader chuyển cho người.
- Cỡ: 18 tiêu chí, vẫn trong cỡ L. Không đề xuất đổi cỡ.
