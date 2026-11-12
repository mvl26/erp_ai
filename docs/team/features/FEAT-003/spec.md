Feature: FEAT-003
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-003 — Chú thích và mô tả rõ ràng cho các field của ERP AI Setting, ERP AI Credential, ERP AI Log

## Mục tiêu
Giả thuyết: người yêu cầu muốn người quản trị mở form của 3 DocType trong app là hiểu ngay mỗi field dùng để làm gì, nhập giá trị nào là hợp lệ, nhập vào thì có hệ quả gì, và field nào do hệ thống tự ghi. Muốn vậy mỗi field hiển thị cần một dòng mô tả tiếng Việt ngay dưới field, và các field được xếp vào những nhóm có tiêu đề. Hành vi của agent không thay đổi. Độ tin cậy: 85%. Còn thiếu: không có số liệu về cách người dùng đọc form hiện nay, nên giới hạn độ dài và cách chia nhóm là giả định của nhóm (xem Assumptions).

- **Kết quả:** 71/71 field hiển thị của 3 DocType có mô tả không rỗng (hiện chỉ có 1/71), và form được chia thành các nhóm có tiêu đề.
- **Người dùng:** System Manager cấu hình agent (ERP AI Setting và bảng con Khóa API), và người tra cứu ERP AI Log.
- **Vì sao lúc này:** FEAT-001 và FEAT-002 vừa tạo 71 field, phần lớn có quy tắc không đoán được từ label. Ví dụ ngân sách 0 ở Setting và ở Credential có nghĩa ngược nhau; L2 và L3 hiện chỉ có quyền như L1; trường "Mục đích" chưa có tác dụng. Đặt sai cấu hình thì tốn tiền hoặc agent tự hạ quyền.
- **Thành công:** AC-1..AC-5 đạt; một test tự động giữ cho field thêm về sau cũng phải có mô tả.
- **Ràng buộc:** không đổi hành vi, không thêm hoặc đổi cột, không đổi kiểu, label, mặc định hay quyền của field. Không đổi giá trị ERP AI Setting đang lưu trên site `miyano`. Nhánh nền là `team/FEAT-002`; chỉ bắt đầu build sau khi FEAT-002 qua verify. Chỉ commit local, không push.
- **Ngoài phạm vi:** report `ERP AI Accuracy`; bản dịch (`translations`/`.csv`); mô tả ở mức DocType; đổi label; sửa các hành vi lạ mà spec này phát hiện (xem Phạm vi, mục Ngoài).

## Người dùng
- **System Manager (người quản trị):** mở `/app/erp-ai-setting` để bật hoặc tắt agent, đặt mức quyền, ngân sách, đơn giá, nhóm loại trừ, người nhận cảnh báo, và thêm hoặc sửa khóa API trong bảng con. Họ đọc form khi cấu hình lần đầu và khi có cảnh báo (khóa lỗi, hết hạn mức, vượt ngân sách).
- **Người tra cứu nhật ký (System Manager, chỉ đọc):** mở một dòng ERP AI Log để biết agent đã làm gì trên phiếu, tốn bao nhiêu, vì sao dừng, và người có sửa lại phân loại không. Không ai sửa Log bằng tay: theo quyền của DocType, System Manager chỉ có read/report/export (`erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:244-256`).
- Nhân viên helpdesk không thấy các form này, nên không thuộc nhóm người dùng.

## Phạm vi
- **Trong:**
  - Thuộc tính mô tả hiển thị dưới field cho mọi field hiển thị (không phải Section/Column/Tab Break, không ẩn) của 3 DocType: `ERP AI Setting` (22 field), `ERP AI Credential` (18 field, bảng con), `ERP AI Log` (31 field). Tổng cộng 71 field.
  - Trong đó có 3 field mới của FEAT-002: `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` (tên và quy tắc lấy từ `docs/team/features/FEAT-002/design.md:74-76`). Cả 3 đã có trên nhánh nền `team/FEAT-002`. Mô tả của `thinking_text` (FEAT-002 viết sẵn) được giữ nguyên hoặc viết đầy đủ hơn, nhưng không được nói khác ý cũ. Nếu verify FEAT-002 làm đổi quy tắc của 3 field này, mô tả theo quy tắc cuối cùng của FEAT-002.
  - Chia field của form thành các nhóm có tiêu đề tiếng Việt (Section Break có label), áp dụng cho cả 3 DocType. Designer quyết định chia nhóm thế nào.
  - Một test tự động kiểm AC-1 và AC-3.
- **Ngoài:**
  - Report `ERP AI Accuracy` và các bộ lọc, cột của nó.
  - Bản dịch sang ngôn ngữ khác; mô tả ở mức DocType.
  - Đổi label, kiểu, mặc định, `options`, `read_only`, quyền, thứ tự nghiệp vụ của field.
  - Sửa hành vi. Các điểm sau chỉ được mô tả đúng như code đang chạy, không sửa trong FEAT-003; muốn đổi thì mở yêu cầu riêng:
    - `purpose` chưa có tác dụng (`erp_ai/gateway/credentials.py:30`).
    - Ngân sách tháng = 0 ở Setting làm hạ quyền về L1 ngay khi đã có chi phí (`erp_ai/agent/policy.py:51-52`).
    - Nếu cả `model_classify` lẫn `model_classify_default` đều trống thì không có kiểm tra nào chặn.
    - `enabled = 0` không dừng hook ghi nhận người sửa và các job định kỳ (`erp_ai/handlers.py:62-97`, `erp_ai/tasks.py`).
  - Tài liệu HDSD riêng ngoài form.

## Dữ liệu
Không có dữ liệu mới, không có cột mới, không migrate dữ liệu. Thứ thay đổi là siêu dữ liệu (metadata) của 3 DocType. Dữ liệu nhạy cảm: `api_key` (Password), địa chỉ email người nhận cảnh báo, giá trị cấu hình thật trên `miyano`. Không mô tả nào được chứa các thứ này (AC-4).

Mỗi mô tả trả lời được những ý sau, ý nào áp dụng cho field thì phải có:
1. field là gì;
2. đơn vị;
3. giá trị hợp lệ hoặc ví dụ;
4. hệ quả khi đặt giá trị;
5. ai ghi. Field tự quản hoặc chỉ đọc phải nói rõ là hệ thống tự ghi và người không sửa được.

Bảng dưới là nội dung bắt buộc của các field có quy tắc không đoán được từ label. Nguồn là code trên `team/FEAT-002`, đường dẫn tính từ `erp_ai/`. Các field còn lại chỉ cần đủ 5 ý trên.

| DocType | Field | Nội dung bắt buộc phải nêu | Nguồn |
|---|---|---|---|
| Setting | `enabled` | Tắt thì không xếp lần chạy mới cho phiếu hay bình luận. Muốn bật phải có đủ 4 đơn giá > 0 và từ khóa kích hoạt không rỗng | `erp_ai_setting.py:116-122`, `handlers.py:34,107` |
| Setting | `permission_level` | L0: chỉ phân loại phiếu mới và ghi vào Log, không sửa phiếu, không trả lời bình luận. L1: đọc dữ liệu, ghi phân loại hoặc gợi ý lên phiếu, đăng bình luận. L2 và L3 hiện có đúng bộ công cụ như L1. Khi đã chi vượt ngân sách tháng thì tự hạ về L1 (L0 giữ nguyên) | `agent/policy.py:48-53`, `agent/tools/registry.py:37,48-52` |
| Setting | `max_turns_per_run`, `max_runs_per_ticket_per_day`, `max_keys_per_call`, `request_timeout_s` | Khoảng hợp lệ lần lượt 1–20, 1–50, 1–10, 5–300 (giây). Hệ quả khi chạm giới hạn: dừng vòng lặp (`max_turns`); bỏ qua phiếu đến hết ngày (tính từ 00:00); hết khóa thì báo lỗi và gửi cảnh báo; quá thời gian thì khóa đó tạm nghỉ và chuyển sang khóa kế tiếp | `erp_ai_setting.py:36-44`, `agent/policy.py:56-68`, `gateway/__init__.py:129-135` |
| Setting | `monthly_budget_usd` | USD mỗi tháng dương lịch. Vượt thì hạ quyền về L1, không chặn chạy. Nhập 0 nghĩa là hạ về L1 ngay khi có chi phí, không phải "không giới hạn" | `agent/policy.py:51-52` |
| Setting | `spent_this_month_usd` | Hệ thống tự tính mỗi ngày bằng tổng chi phí trong Log của tháng hiện tại, nên ngày 1 bắt đầu lại từ khoảng 0. Người không sửa được; giá trị gõ vào bị bỏ khi lưu | `tasks.py:143-167`, `erp_ai_setting.py:66` |
| Setting | `price_*_per_mtok` (4 field) | USD cho 1 triệu token. Dùng để tính chi phí ghi vào Log. Không được âm; bằng 0 thì không bật được agent. Không ghi giá thật trong mô tả | `gateway/cost.py:4-14`, `erp_ai_setting.py:104-106` |
| Setting | `model_classify_default` | Model dùng để phân loại khi dòng khóa không ghi model phân loại riêng | `gateway/__init__.py:145-147` |
| Setting | `trigger_keyword` | Bình luận trên phiếu chứa cụm này (không phân biệt hoa thường) thì agent được gọi. Ví dụ: @ai | `agent/policy.py:41-45` |
| Setting | `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` | Đơn vị là giây, khoảng 0–30, tối thiểu ≤ tối đa. Độ trễ chỉ áp dụng khi agent được gọi bằng bình luận. Để `thinking_text` trống thì tắt chỉ báo, nhưng độ trễ vẫn áp dụng | `docs/team/features/FEAT-002/design.md:74-76,118-121`, `agent/answer_delay.py:36-38` |
| Setting | `excluded_teams` | Mỗi dòng một tên nhóm, so với Nhóm xử lý của phiếu, không phân biệt hoa thường. Phiếu thuộc các nhóm này thì agent bỏ qua | `agent/policy.py:18-38` |
| Setting | `category_mapping` | JSON gồm các đầu mục A–F. Mỗi đầu mục có thể có loại phiếu, nhóm xử lý, ưu tiên. Sai cú pháp thì không lưu được. Tiêu đề phiếu có `[GẤP]` thì ưu tiên thành Urgent | `agent/classification.py:79-122` |
| Setting | `prompt_digest` | Người tự nhập (hệ thống không tự điền). Được nối vào cuối hướng dẫn của bước lập luận, không dùng ở bước phân loại | `agent/prompts.py:174-177` |
| Setting | `alert_recipients` | Mỗi dòng một email, không tách bằng dấu phẩy. Những cảnh báo được gửi: khóa lỗi, khóa hết hạn mức, hết khóa dùng được, khóa hoạt động lại, cảnh báo leo quyền hằng ngày. Ví dụ email không dùng địa chỉ thật | `alerts.py:6-8`, `gateway/__init__.py:67-84`, `tasks.py:252-262` |
| Setting | `credentials` | Danh sách khóa API. Nhãn bắt buộc và không trùng nhau (không phân biệt hoa thường). Có nút Kiểm tra khóa | `erp_ai_setting.py:88-96,125-143` |
| Credential | `try_order` | Số nhỏ được thử trước. Để trống hoặc 0 thì coi như 99 | `gateway/credentials.py:70` |
| Credential | `purpose` | Chỉ để ghi chú, hiện không ảnh hưởng việc chọn khóa | `gateway/credentials.py:30` |
| Credential | `budget_month_usd` | USD mỗi tháng của riêng khóa này. Nhập 0 là không giới hạn; đạt ngân sách thì bỏ qua khóa này. Lưu ý: nghĩa này ngược với ngân sách ở Setting | `gateway/credentials.py:52` |
| Credential | `spent_month_usd` | Hệ thống tự tính mỗi ngày từ Log, người không sửa | `tasks.py:168-177` |
| Credential | `status` | Hệ thống tự đặt Tạm nghỉ, Hết hạn mức, Lỗi khóa. Người chỉ được đổi Lỗi khóa → Hoạt động sau khi đã thay khóa | `erp_ai_setting.py:82-86`, `gateway/breaker.py:37-54` |
| Credential | `paused_until`, `tokens_remaining`, `limit_reset_at`, `error_count`, `last_error`, `last_success_at` | Hệ thống tự ghi sau mỗi lần gọi, người không sửa. `last_error` không bao giờ chứa khóa | `gateway/credentials.py:82-134` |
| Credential | `model_classify`, `model_reason` | Trống thì phân loại dùng model mặc định ở Setting. Trống `model_reason` thì khóa này không dùng cho bước lập luận | `gateway/credentials.py:54` |
| Log | mọi field | Agent tự ghi khi chạy, không ai sửa. Riêng `human_corrected_to/by/at` do hệ thống ghi khi người đổi loại phiếu, nhóm xử lý hoặc ưu tiên sau khi AI đã dự đoán; `at` chỉ ghi ở lần sửa đầu | `agent/run_log.py:11-33`, `handlers.py:62-97` |
| Log | `entry_type`, `turn`, `stop_reason`, `predicted_confidence`, `keys_tried` | Giải thích các giá trị: classify, reason, skip. Lượt 0 là phân loại hoặc bỏ qua, lượt 1..N là lập luận. Lý do dừng gồm max_turns, time_budget, gateway_error. Độ tin cậy là Cao, Trung bình hoặc Thấp. `keys_tried` là danh sách nhãn khóa và kết quả | `agent/runner.py:90-329`, `constants.py:12` |

## Giao diện / tích hợp
- **Màn hình:** form ERP AI Setting (`/app/erp-ai-setting`), form dòng của bảng con ERP AI Credential, form ERP AI Log. Mô tả hiện dưới field theo cách Frappe vẫn làm; không có màn hình mới.
- **API hay hệ thống ngoài:** không có. Helpdesk, Anthropic và email không bị ảnh hưởng.
- **Ràng buộc từ test hiện có** (test không được sửa để đi qua, STD-TEST-5):
  - Label chứa "(USD)" vẫn giữ (`test_erp_ai_setting.py:73-90,232-234`, `test_erp_ai_credential.py:36`, `test_erp_ai_log.py:71-97`).
  - Trong thứ tự field của ERP AI Log, `skipped_fields` vẫn phải đứng ngay sau `value_after` (`test_erp_ai_log.py:71-97`). Cách chia nhóm không được chen Section Break vào giữa hai field này.
  - Test chống lộ khóa vẫn chạy trên mọi field văn bản của Log (`test_gateway.py:851-858`).

## NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Mỗi mô tả ngắn, đọc được ngay trên form: ≤ 400 ký tự (giả định A-3, không có số đo nào từ người dùng) | Đếm `len(description)` của từng field trong cùng lệnh in ở AC-2 |
| NFR-2 | Không đổi hiệu năng và hành vi chạy | AC-5 (`cmd.test` xanh, siêu dữ liệu ngoài phần mô tả và nhóm không đổi) |

## Tiêu chí nghiệm thu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Mọi field hiển thị của 3 DocType (fieldtype không phải Section Break, Column Break hay Tab Break, và `hidden` ≠ 1) có mô tả không rỗng sau khi bỏ khoảng trắng: 71/71 field (22 + 18 + 31). Field thêm sau này mà thiếu mô tả thì test đỏ | `cmd.test_one` trên file test mới, kết quả OK. Đầu ra đỏ trước khi thêm mô tả (STD-TEST-1) được dán vào build log; danh sách field thiếu phải in ra tên DocType và fieldname |
| AC-2 | Mỗi mô tả viết bằng tiếng Việt, ≤ 400 ký tự, đủ các ý áp dụng trong 5 ý ở mục Dữ liệu, và đủ nội dung bắt buộc trong bảng ở mục Dữ liệu. Field tự quản hoặc chỉ đọc nói rõ "hệ thống tự ghi" và người không sửa. Kiểm tối thiểu: `permission_level` có đủ "L0", "L1", "L2", "L3"; 4 field đơn giá có "USD" và "triệu token"; `excluded_teams` và `alert_recipients` có "mỗi dòng"; `budget_month_usd` của Credential nêu "0" nghĩa là không giới hạn | QA chạy một lệnh chỉ đọc in `doctype | fieldname | len | description` của 71 field trên `miyano`, rồi đối chiếu từng dòng với bảng ở mục Dữ liệu (kết quả đạt hay không đạt cho từng dòng ghi vào `acceptance.md`). Các chuỗi kiểm tối thiểu được kiểm bằng `grep` trên đầu ra đó |
| AC-3 | Mỗi DocType trong 3 DocType có ít nhất 2 Section Break có label tiếng Việt không rỗng, và không Section Break nào có label rỗng. Mô tả của Section Break là tùy chọn | Cùng file test ở AC-1, kết quả OK |
| AC-4 | Không mô tả nào chứa dữ liệu nhạy cảm. Cụ thể: không có chuỗi `sk-`, không có địa chỉ email thật (biểu thức `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` chỉ được khớp với ví dụ dùng tên miền giả `congty.vn` hoặc `example.com`), không có `miyano`, không có giá trị cấu hình đang lưu trên site | Chạy `grep -nE` với 3 mẫu trên đầu ra của AC-2: 0 dòng khớp ngoài tên miền ví dụ. So thêm với giá trị đang lưu của ERP AI Setting, không có giá trị nào xuất hiện trong mô tả |
| AC-5 | Hành vi không đổi. Với mọi field không phải Break, mọi thuộc tính khác `description` giống hệt nhánh nền `team/FEAT-002` (fieldname, fieldtype, label, options, default, read_only, read_only_depends_on, reqd, precision, in_list_view, search_index). Thứ tự tương đối giữa các field không phải Break không đổi. `cmd.test` xanh. `cmd.migrate` thành công, và giá trị ERP AI Setting đang lưu trên `miyano` giống nhau trước và sau migrate | Một script chỉ đọc so JSON của 3 DocType giữa `team/FEAT-002` và `team/FEAT-003`: 0 khác biệt ngoài `description`, các Section Break mới, `modified`. Đầu ra của `cmd.test` và `cmd.migrate` dán vào `acceptance.md`. Bản ghi ERP AI Setting trước và sau migrate giống nhau (bỏ qua `modified`) |

## Assumptions decided by the team
- **A-1. Phạm vi gồm 3 DocType, 3 field FEAT-002 và Section Break có tiêu đề; không gồm report ERP AI Accuracy.**
  - Chọn: như mục Phạm vi.
  - Vì sao: người yêu cầu đồng ý mọi đề xuất mặc định (2026-11-12, "tôi đồng ý mọi đề xuất"); report không có field cấu hình.
  - Thay thế: thêm mô tả cho bộ lọc của report.
  - Sai thì: mở yêu cầu riêng cho report; spec này không phải đổi.
- **A-2. Chỉ thêm mô tả và nhóm có tiêu đề; label giữ nguyên.**
  - Chọn: không đổi label.
  - Vì sao: test hiện có bám vào label "(USD)"; người quản trị đã quen label; phần giải thích đặt ở mô tả.
  - Thay thế: chuẩn hóa label (ví dụ "Người sửa thành" → "Giá trị người sửa thành").
  - Sai thì: `--amend` thêm một AC đổi label, kèm danh sách label cũ và mới, và nới AC-5 cho thuộc tính `label`.
- **A-3. Mỗi mô tả ≤ 400 ký tự.**
  - Chọn: 400.
  - Vì sao: mô tả hiện dưới field nên dài quá thì rối form. `permission_level` cần khoảng 250–300 ký tự để nói đủ L0–L3 và việc tự hạ về L1. Không có số đo từ người dùng.
  - Thay thế: 250 ký tự; hoặc không giới hạn.
  - Sai thì: sửa số trong NFR-1 và AC-2; các mô tả dài hơn thì rút gọn.
- **A-4. Mô tả nói đúng hành vi code đang chạy, kể cả chỗ có thể chưa như ý muốn.**
  - Chọn: mô tả đúng hành vi hiện tại (ví dụ `purpose` chưa có tác dụng, ngân sách 0 ở Setting hạ về L1).
  - Vì sao: FEAT-003 không đổi hành vi; mô tả sai sự thật còn tệ hơn không có mô tả.
  - Thay thế: sửa hành vi ngay trong FEAT-003.
  - Sai thì: mở feature riêng để sửa hành vi, và sửa mô tả trong cùng feature đó.
- **A-5. Chia nhóm cho cả 3 DocType, mỗi DocType ít nhất 2 nhóm; designer quyết định nhóm cụ thể.**
  - Chọn: ít nhất 2 Section Break có label; mô tả nhóm là tùy chọn.
  - Vì sao: người yêu cầu chọn "Section Break có tiêu đề". Hiện cả 3 DocType chưa có Section Break nào (đã đọc 3 tệp JSON), nên nhóm phải được thêm mới. Section Break không tạo cột trong cơ sở dữ liệu.
  - Thay thế: chỉ chia nhóm cho ERP AI Setting.
  - Sai thì: sửa AC-3 thành chỉ áp dụng cho Setting và bỏ các Section Break ở 2 DocType kia.
- **A-6. Chỉ tiếng Việt, không có bản dịch.**
  - Chọn: viết mô tả tiếng Việt, không tạo tệp bản dịch.
  - Vì sao: label hiện có là tiếng Việt; repo chưa có tệp bản dịch nào (đã tìm `*.csv`, `*.po`, thư mục `translations`).
  - Thay thế: thêm bản dịch tiếng Anh.
  - Sai thì: mở feature riêng cho bản dịch.
- **A-7. Phụ thuộc FEAT-002.**
  - Chọn: nhánh nền là `team/FEAT-002`; build chỉ bắt đầu sau khi FEAT-002 qua verify.
  - Vì sao: FEAT-002 cũng sửa `erp_ai_setting.json`; 3 field mới đã có trên nhánh nền.
  - Thay thế: tách nhánh từ `team/FEAT-001`, bỏ 3 field và mô tả chúng sau.
  - Sai thì: rebase lên nhánh đúng và chạy lại AC-5 với nhánh nền mới.

## Definition of Done
**Phần build (trước G4):**
- [ ] AC-1..AC-5 đạt; đầu ra của từng AC được dán trong `acceptance.md`.
- [ ] Đầu ra đỏ của test mới (trước khi thêm mô tả) được dán vào build log (STD-TEST-1).
- [ ] `cmd.test` xanh, `cmd.lint` sạch; không có dấu skip nào trong `test.skip_markers`.
- [ ] `cmd.migrate` thành công trên `miyano`; giá trị ERP AI Setting không đổi.
- [ ] Commit local trên `team/FEAT-003` (nhánh từ `team/FEAT-002`), không push.

**Phần sau G4 (`/team:asbuilt`):**
- [ ] As-Built viết xong (`asbuilt.md`), ghi lại các điểm hành vi lạ ở mục Phạm vi (phần Ngoài) để mở yêu cầu riêng nếu cần.
- [ ] Tài liệu người dùng: hành vi không đổi nên không bắt buộc; As-Built ghi rõ "không áp dụng" hoặc trỏ tới mô tả trên form.
- [ ] Mục CHANGELOG cho FEAT-003.
- [ ] CI xanh trên nhánh.
