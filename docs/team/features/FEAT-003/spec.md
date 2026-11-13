Feature: FEAT-003
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-003 — Chú thích và mô tả rõ ràng cho các field của ERP AI Setting, ERP AI Credential, ERP AI Log **[changed — Amendment 1: thêm phần 2, khu vực "Hướng giải quyết & trao đổi với bot" trên trang phiếu]**

> **Amendment 1 (2026-11-12):** người gộp yêu cầu 2 vào FEAT-003 (intake dòng 12): "thêm 1 tab dành riêng cho hướng giải quyết và trao đổi với bot cho user dễ sử dụng". Phần 1 (AC-1..AC-5, mô tả field) giữ nguyên chữ. Phần 2 thêm AC-6..AC-15 ở mục `## Amendment 1` cuối file. Các dòng có dấu `[changed — Amendment 1]` được bổ sung ở mục đó; chữ cũ giữ để đối chiếu. Mode decide, không có câu hỏi mở.

## Mục tiêu
Giả thuyết: người yêu cầu muốn người quản trị mở form của 3 DocType trong app là hiểu ngay mỗi field dùng để làm gì, nhập giá trị nào là hợp lệ, nhập vào thì có hệ quả gì, và field nào do hệ thống tự ghi. Muốn vậy mỗi field hiển thị cần một dòng mô tả tiếng Việt ngay dưới field, và các field được xếp vào những nhóm có tiêu đề. Hành vi của agent không thay đổi. Độ tin cậy: 85%. Còn thiếu: không có số liệu về cách người dùng đọc form hiện nay, nên giới hạn độ dài và cách chia nhóm là giả định của nhóm (xem Assumptions). **[changed — Amendment 1: đây là giả thuyết của phần 1; giả thuyết phần 2 ở mục Amendment 1]**

- **Kết quả:** 71/71 field hiển thị của 3 DocType có mô tả không rỗng (hiện chỉ có 1/71), và form được chia thành các nhóm có tiêu đề. **[changed — Amendment 1: thêm kết quả của phần 2]**
- **Người dùng:** System Manager cấu hình agent (ERP AI Setting và bảng con Khóa API), và người tra cứu ERP AI Log. **[changed — Amendment 1: phần 2 thêm nhân viên helpdesk]**
- **Vì sao lúc này:** FEAT-001 và FEAT-002 vừa tạo 71 field, phần lớn có quy tắc không đoán được từ label. Ví dụ ngân sách 0 ở Setting và ở Credential có nghĩa ngược nhau; L2 và L3 hiện chỉ có quyền như L1; trường "Mục đích" chưa có tác dụng. Đặt sai cấu hình thì tốn tiền hoặc agent tự hạ quyền.
- **Thành công:** AC-1..AC-5 đạt; một test tự động giữ cho field thêm về sau cũng phải có mô tả. **[changed — Amendment 1: thêm AC-6..AC-15]**
- **Ràng buộc:** không đổi hành vi, không thêm hoặc đổi cột, không đổi kiểu, label, mặc định hay quyền của field. Không đổi giá trị ERP AI Setting đang lưu trên site `miyano`. Nhánh nền là `team/FEAT-002`; chỉ bắt đầu build sau khi FEAT-002 qua verify. Chỉ commit local, không push. **[changed — Amendment 1: "không đổi hành vi" áp cho phần 1 và cho hành vi của agent; phần 2 thêm giao diện mới, xem ràng buộc phần 2]**
- **Ngoài phạm vi:** report `ERP AI Accuracy`; bản dịch (`translations`/`.csv`); mô tả ở mức DocType; đổi label; sửa các hành vi lạ mà spec này phát hiện (xem Phạm vi, mục Ngoài). **[changed — Amendment 1: thêm ngoài phạm vi của phần 2]**

## Người dùng
- **System Manager (người quản trị):** mở `/app/erp-ai-setting` để bật hoặc tắt agent, đặt mức quyền, ngân sách, đơn giá, nhóm loại trừ, người nhận cảnh báo, và thêm hoặc sửa khóa API trong bảng con. Họ đọc form khi cấu hình lần đầu và khi có cảnh báo (khóa lỗi, hết hạn mức, vượt ngân sách).
- **Người tra cứu nhật ký (System Manager, chỉ đọc):** mở một dòng ERP AI Log để biết agent đã làm gì trên phiếu, tốn bao nhiêu, vì sao dừng, và người có sửa lại phân loại không. Không ai sửa Log bằng tay: theo quyền của DocType, System Manager chỉ có read/report/export (`erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:244-256`).
- Nhân viên helpdesk không thấy các form này, nên không thuộc nhóm người dùng. **[changed — Amendment 1: đúng với phần 1; nhân viên helpdesk là người dùng chính của phần 2]**

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
Không có dữ liệu mới, không có cột mới, không migrate dữ liệu. Thứ thay đổi là siêu dữ liệu (metadata) của 3 DocType. Dữ liệu nhạy cảm: `api_key` (Password), địa chỉ email người nhận cảnh báo, giá trị cấu hình thật trên `miyano`. Không mô tả nào được chứa các thứ này (AC-4). **[changed — Amendment 1: phần 2 cũng không có dữ liệu mới hay cột mới, nhưng đọc comment và field AI của phiếu; xem Dữ liệu phần 2]**

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
- **Màn hình:** form ERP AI Setting (`/app/erp-ai-setting`), form dòng của bảng con ERP AI Credential, form ERP AI Log. Mô tả hiện dưới field theo cách Frappe vẫn làm; không có màn hình mới. **[changed — Amendment 1: phần 2 thêm một khu vực trên trang phiếu nhân viên của Helpdesk]**
- **API hay hệ thống ngoài:** không có. Helpdesk, Anthropic và email không bị ảnh hưởng. **[changed — Amendment 1: phần 2 tích hợp với trang phiếu Helpdesk (không sửa mã nguồn Helpdesk) và tái dùng luồng `@ai` của FEAT-001; Anthropic và email vẫn không bị ảnh hưởng]**
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
- [ ] Tài liệu người dùng: hành vi không đổi nên không bắt buộc; As-Built ghi rõ "không áp dụng" hoặc trỏ tới mô tả trên form. **[changed — Amendment 1: phần 2 đổi hành vi người dùng thấy, nên tài liệu người dùng là bắt buộc cho phần 2; xem DoD bổ sung]**
- [ ] Mục CHANGELOG cho FEAT-003.
- [ ] CI xanh trên nhánh.

## Amendment 1 (2026-11-12)

Nguồn: `intake.md` yêu cầu gốc 2 (dòng 12), "Điểm analyst phải làm rõ — phần 2" (dòng 22-27), "Mặc định người đã đồng ý" (dòng 29-30), "Ràng buộc của người yêu cầu" (dòng 35-38). Người đã đồng ý mọi đề xuất (2026-11-12), nên mỗi điểm của intake được chốt bằng phương án khuyến nghị, ghi ở B-1..B-14 với đủ 4 trường. Phần 1 (AC-1..AC-5, A-1..A-7) không đổi chữ.

### Thay đổi gì
- Thêm phần 2: một khu vực riêng tên "Hướng giải quyết & trao đổi với bot" trên trang phiếu của nhân viên (desktop). Khu vực gồm hướng giải quyết AI chỉ đọc, luồng hỏi–đáp với bot, ô gửi tin, và chỉ báo của FEAT-002.
- Tiêu chí: AC-1..AC-5 giữ nguyên. Thêm AC-6..AC-15. Thêm NFR-3..NFR-5. Thêm B-1..B-14. DoD có thêm phần 2.
- Các dòng phía trên có dấu `[changed — Amendment 1]`: tiêu đề, giả thuyết, Kết quả, Người dùng (2 dòng), Thành công, Ràng buộc, Ngoài phạm vi, Dữ liệu, Màn hình, API, DoD "Tài liệu người dùng".
- Lưu ý đánh số: NFR-3..NFR-5 dưới đây là của FEAT-003. Khi nói tới quy tắc nhóm loại trừ của FEAT-001, spec này luôn viết "NFR-4 của FEAT-001".

### Mục tiêu (phần 2)
**Giả thuyết (độ tin cậy 75%):** nhân viên helpdesk đang mở một phiếu muốn có một chỗ riêng, mở bằng tối đa 1 lần bấm. Ở đó họ thấy ngay hướng giải quyết của AI, kèm độ tin cậy, ai phân loại và lúc cập nhật. Họ đọc lại các lần hỏi–đáp với bot trên phiếu mà không lẫn với comment khác, và gửi câu hỏi cho bot mà không phải nhớ gõ từ khóa. Câu trả lời và chỉ báo "đang suy nghĩ" hiện ngay tại chỗ đó, không cần tải lại trang. Độ tin cậy dưới 85% vì: (1) chưa biết có chèn được tab vào trang phiếu Helpdesk 15.1.0 mà không sửa mã nguồn hay không, vì danh sách tab viết cứng (`apps/helpdesk/desk/src/components/ticket-agent/TicketActivityPanel.vue:78-109`, đã đọc). Nếu không chèn được, vị trí đi theo thứ tự dự phòng ở B-1; (2) "trao đổi với bot" cũng có thể hiểu là một kênh riêng không hiện trên timeline phiếu; đội chọn dùng comment (B-4); (3) yêu cầu không nói luồng gồm những comment nào; đội chọn quy tắc ở B-5.

| Mục | Nội dung |
|---|---|
| Outcome | Trên trang phiếu của nhân viên (desktop), khu vực "Hướng giải quyết & trao đổi với bot" mở được bằng ≤ 1 lần bấm. Khu vực có: 4 mục AI chỉ đọc, luồng hỏi–đáp với bot, ô gửi tin không cần gõ từ khóa. Tin gửi đi theo đúng luồng `@ai` của FEAT-001 và qua mọi chốt an toàn đang có. Câu trả lời và chỉ báo FEAT-002 hiện trực tiếp, không cần tải lại |
| Users | Nhân viên helpdesk có role Agent; người có role `ERP AI Instructor`; người được người khác giao phiếu. Không phải người dùng: khách (HD Contact) trên trang khách |
| Why now | Người gộp yêu cầu vào FEAT-003 ngày 2026-11-12 (intake dòng 12). Hiện nay hướng giải quyết nằm trong section "ERP AI" ở thanh bên (`erp_ai/install.py:114-151`, hiện cho Agents qua template `install.py:156-175`). Lời gọi bot và câu trả lời lẫn với comment khác. Muốn gọi bot thì phải nhớ gõ từ khóa (`erp_ai/handlers.py:100-120`) |
| Success | Lúc build: phần tự động của AC-6..AC-15 đạt, `cmd.test` xanh. Sau bàn giao (việc của người): các bước tay của AC-6, AC-7, AC-11, AC-12, AC-13 đạt trên `miyano` |
| Constraints | Không sửa mã nguồn Helpdesk (intake dòng 36). Không nới ADR-004, mô hình thẩm quyền `ERP AI Instructor`, NFR-4 của FEAT-001 (nhóm loại trừ, cờ không dùng AI), và quy tắc khách không thấy dữ liệu AI. Không đổi hành vi agent (điều kiện kích hoạt, runner, bộ tool, giới hạn, ngân sách). Không thêm field vào HD Ticket hay 3 DocType của phần 1 (để AC-5 vẫn đúng). Không đổi giá trị ERP AI Setting trên `miyano`. Chỉ commit local. Build sau khi FEAT-002 qua verify |
| Out of scope | Bản di động (`MobileTicketAgent.vue`); sửa mã nguồn Helpdesk; tool L2/L3; sửa hoặc xóa tin từ khu vực; đính kèm tệp; nhắc tên người (@người); sửa hướng giải quyết từ khu vực; xem chi phí hay ERP AI Log; báo lý do cụ thể vì sao bot không trả lời (B-8); kênh trao đổi riêng ngoài comment; trang khách; form Desk `/app/hd-ticket/<id>` (trừ khi rơi xuống P4 của B-1) |

### Đã có câu trả lời sẵn (không hỏi lại)
- Tab của trang phiếu nhân viên viết cứng: Activity, Emails, Comments, Calls, Analytics (`apps/helpdesk/desk/src/components/ticket-agent/TicketActivityPanel.vue:78-109`, đã đọc).
- Trang phiếu nhân viên là route `/tickets/:ticketId` (`TicketAgent`, chọn bản di động qua `handleMobileView`). Trang phiếu của khách là `/my-tickets/:ticketId` (`TicketCustomer`) (`apps/helpdesk/desk/src/router/index.ts:42-45,145-147`).
- 4 field AI và label: "Hướng giải quyết (AI)" (Text Editor), "Độ tin cậy (AI)", "Phân loại bởi", "AI cập nhật lúc", đều chỉ đọc (`erp_ai/install.py:114-151`).
- Kích hoạt bằng comment: core `Comment`, `comment_type = "Comment"`, tác giả khác tài khoản agent, có từ khóa, `can_send_ticket` (`erp_ai/handlers.py:100-120`). Từ khóa so không phân biệt hoa thường (`erp_ai/agent/policy.py:41-45`).
- Các nhánh bỏ qua trong runner: `not_sendable`, `daily_limit`, `level_L0` (`erp_ai/agent/runner.py:95-106`). Vượt ngân sách thì hạ về L1 (`erp_ai/agent/policy.py:48-53`).
- Bot trả lời bằng `post_comment` → `doc.new_comment` (`erp_ai/agent/tools/write_ticket.py:73-83`). Chỉ tool này tạo comment của agent (ADR-004 Quyết định 1).
- Thẩm quyền: có role `ERP AI Instructor`, hoặc được người khác giao phiếu (`erp_ai/agent/authority.py:44-60`). Tác giả comment lấy từ `owner` (FEAT-001 asbuilt dòng 53, D8).
- Kênh giao diện duy nhất là một HD Form Script của app. Script không gọi server, không ghi HTML (ADR-007 Quyết định 1, 5, 6). Tín hiệu chỉ báo đi qua phòng `doc:` của phiếu (ADR-008).
- Sự kiện `helpdesk:ticket-update` không bao giờ tới trình duyệt trên `miyano` (FEAT-002 spec, Amendment 2).
- Không có `docs/team/glossary.md`.

### Người dùng (phần 2)
| Ai | Tình huống | Quan hệ với khu vực |
|---|---|---|
| Nhân viên helpdesk (role Agent), trên desktop | Mở phiếu ở `/helpdesk/tickets/<id>` để xử lý | Đọc hướng giải quyết, đọc luồng, gửi câu hỏi. Lời của họ là "dữ liệu" nếu họ không có thẩm quyền |
| Người có role `ERP AI Instructor` | Gửi chỉ thị cho bot trên bất kỳ phiếu nào | Như trên; tin của họ là "chỉ thị" (FEAT-001 AC-7) |
| Người được người khác giao phiếu | Xử lý phiếu được giao | Tin của họ là "chỉ thị" trên đúng phiếu đó |
| Khách (HD Contact) | Xem phiếu của mình ở `/helpdesk/my-tickets/<id>` | Không thấy khu vực, không thấy dữ liệu AI |

### Phạm vi (phần 2)
- **Trong:**
  - Một khu vực có tiêu đề "Hướng giải quyết & trao đổi với bot" trên trang phiếu nhân viên (desktop), ở vị trí theo B-1.
  - Phần (1): 4 mục AI chỉ đọc, đọc từ field hiện có của phiếu.
  - Phần (2): luồng hỏi–đáp theo quy tắc B-5, một dòng hướng dẫn cố định (B-8), ô nhập và nút gửi, chỉ báo FEAT-002 (B-9).
  - Cập nhật trực tiếp, không cần tải lại (NFR-3).
  - Test tự động cho mọi phần kiểm được ở server và mọi kiểm tra tĩnh trên mã giao diện. Bước tay cho phần chỉ thấy được trên trình duyệt (`ui: false`, chưa có Playwright, chưa có slot test JavaScript, giống FEAT-002 A-21).
- **Ngoài:** như dòng Out of scope ở bảng trên.

### Dữ liệu (phần 2)
- Không có DocType mới, không có field mới, không có bản ghi nào tạo ra chỉ để hiển thị (AC-14).
- **Đọc:** 4 field AI của phiếu đang mở; các core `Comment` của phiếu đó; từ khóa kích hoạt đang cấu hình (để tự thêm vào tin). Mọi lần đọc chạy dưới phiên và quyền của chính người dùng (B-11).
- **Ghi:** chỉ khi người bấm gửi. Mỗi lần gửi tạo đúng 1 core `Comment` do chính người đó làm chủ (`owner`). Câu trả lời của bot vẫn do `post_comment` tạo như hiện nay. Bảng chủ ghi ADR-004 không đổi.
- **Quy tắc chọn tin cho luồng (B-5):** comment của phiếu có `comment_type = "Comment"`, và một trong hai: tác giả là tài khoản agent; hoặc tác giả là người và nội dung chứa từ khóa kích hoạt đang cấu hình (không phân biệt hoa thường).
- **Nhạy cảm:** nội dung comment là nội dung phiếu, chỉ nhân viên thấy, giống tab Comments. Không lưu vào `localStorage`, `sessionStorage` hay cookie. Không hiện giá trị cấu hình nào khác ngoài từ khóa (B-8).

### Giao diện / tích hợp (phần 2)
- **Màn hình:** trang phiếu nhân viên desktop `/helpdesk/tickets/<id>`. Trang di động và trang khách `/helpdesk/my-tickets/<id>` không có khu vực.
- **Tích hợp:** handler `comment_after_insert` của FEAT-001 (không đổi); tín hiệu trạng thái của ADR-008 (không đổi phía phát); lớp giao diện của ADR-007.
- **Câu hỏi kỹ thuật cho research/architect (không hỏi người):**
  - RQ-1: Có cách nào có tài liệu, hoặc kiểm được trong mã Helpdesk 15.1.0, để thêm một tab vào `TicketActivityPanel.vue:78-109` mà không sửa `apps/helpdesk` không (ngữ cảnh `setupForm` của HD Form Script, slot, cấu hình)? Nếu không, P2 làm sao cho an toàn: chỉ dùng DOM API an toàn, không phá cập nhật trực tiếp sẵn có (FEAT-002 AC-10 (h)), và chịu được việc Vue dựng lại phần trang.
  - RQ-2: Đọc 4 field AI và comment của phiếu: ngữ cảnh `setupForm` có sẵn dữ liệu này không, hay phải gọi server? Nếu phải gọi server thì trái ADR-007 Quyết định 5, nên architect phải sửa ADR-007 hoặc viết ADR mới, trong giới hạn B-11.
  - RQ-3: Gửi tin: làm thế nào tạo core `Comment` dưới phiên của người, giống hệt ô Comments của Helpdesk 15.1.0, để `comment_after_insert` chạy như cũ? Nhân viên (role Agent) có quyền đọc `trigger_keyword` không? Nếu không, lấy từ khóa bằng cách nào mà không lộ giá trị cấu hình khác?
  - RQ-4: Cập nhật trực tiếp: trên Frappe 15 cùng Helpdesk 15.1.0, sự kiện nào báo cho trình duyệt rằng phiếu có comment mới hoặc field phiếu đã đổi? Cơ chế mà FEAT-002 AC-10 (h) đang dựa vào là gì?
  - RQ-5: Làm sao hiện nội dung HTML (nội dung `Comment`, field Text Editor) thành chữ thường, giữ ngắt dòng, chỉ bằng DOM API an toàn?
  - RQ-6: Với trang khách: `apply_to_customer_portal = 0` có đủ để `TicketCustomer` không có khu vực không? Mọi đường server mới (nếu có) kiểm role và quyền đọc phiếu ở server như thế nào (STD-SEC-4)?
  - RQ-7: Ghép với chỉ báo FEAT-002: làm sao để mỗi lần chạy chỉ có một chỉ báo trên trang, dù khu vực đang hiện hay không (B-9), với cùng tên sự kiện của ADR-008?
  - RQ-8 (chỉ khi cần P3): trang riêng của app nên là trang Desk hay trang web, kiểm quyền thế nào, và mở từ trang phiếu bằng cách nào mà không sửa Helpdesk?
- **Thứ tự phương án vị trí (B-1)**, dùng phương án đầu tiên khả thi:
  - P1: tab trên trang phiếu nhân viên, cạnh Activity/Emails/Comments, không sửa Helpdesk.
  - P2: một khối hoặc ngăn riêng trên cùng trang phiếu nhân viên, do HD Form Script dựng bằng DOM API an toàn, mở bằng ≤ 1 lần bấm hoặc hiện sẵn.
  - P3: một trang riêng của app `erp_ai`, chỉ nhân viên vào được (kiểm ở server), mở từ trang phiếu bằng 1 lần bấm.
  - P4: tab trên form Desk `/app/hd-ticket/<id>`. Chỉ dùng khi P1–P3 đều không khả thi. Khi đó AC-6 phải `--amend` (`[changed]`), vì nhân viên ít dùng Desk (intake dòng 23).
  - Không xét: sửa `apps/helpdesk`, ghi đè `www/helpdesk`, chèn qua `after_request`, fixture (ADR-007 đã loại).

### NFR (phần 2)
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-3 | Cập nhật trực tiếp: comment trả lời của bot, tin có từ khóa của người khác, và 4 mục AI do bot ghi hiện trong khu vực chậm nhất 10 s sau khi được lưu, không cần tải lại. Số 10 s lấy theo NFR-5 của FEAT-002 (mức Helpdesk tự dùng cho chỉ báo "đang gõ", `realtime.ts:106-119`) (B-13) | AC-11, bước tay, đo bằng đồng hồ |
| NFR-4 | Không tốn thêm: xem khu vực tạo 0 lời gọi model, 0 bản ghi ERP AI Log, 0 bản ghi ghi vào DB. Gửi một tin tốn đúng như một comment `@ai` gõ ở ô Comments | AC-10, AC-14 |
| NFR-5 | An toàn: nội dung hiện dưới dạng chữ thường (STD-SEC-3); người không phải nhân viên không nhận dữ liệu AI (STD-SEC-4); khu vực không cho làm điều gì mà ô Comments của Helpdesk không cho | AC-12, AC-13 |
| — | Thời gian mở khu vực: không có, vì intake và người không cho số nào, và chưa có số đo (B-13) | — |

### Tiêu chí nghiệm thu (phần 2)
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-6 | **Vị trí và số thao tác.** Trên `miyano`, người có role Agent mở `/helpdesk/tickets/<id>` trên desktop. Từ trang đó, họ tới được khu vực có tiêu đề "Hướng giải quyết & trao đổi với bot" bằng ≤ 1 lần bấm. Họ gửi một câu hỏi cho bot bằng cách gõ nội dung rồi làm 1 thao tác (Enter hoặc nút Gửi), không phải gõ từ khóa. Vị trí là phương án đầu tiên khả thi trong P1 → P3 (B-1). Trang di động và các tab Activity, Emails, Comments, Analytics vẫn hoạt động như trước. Console trình duyệt không có lỗi mới do `erp_ai`, trên cả trang desktop lẫn trang di động. `git -C ../helpdesk status --porcelain` không có dòng nào do FEAT-003 tạo | Bước tay (`ui: false`): đếm số lần bấm, ghi phương án đã dùng, kèm ảnh chụp nếu có, vào `acceptance.md`. Dán đầu ra lệnh `git` |
| AC-7 | **Phần hướng giải quyết.** Khu vực hiện 4 mục với đúng label hiện có: "Hướng giải quyết (AI)", "Độ tin cậy (AI)", "Phân loại bởi", "AI cập nhật lúc" (`install.py:114-151`). Giá trị bằng giá trị đang lưu trên phiếu. Không có ô sửa nào. Mục nào trống thì hiện chữ "Chưa có" | Test tự động trên đường đọc dữ liệu của khu vực, nếu đường đó nằm ở server: giá trị trả về bằng giá trị trên phiếu. Bước tay: đối chiếu 1 phiếu có đủ 4 giá trị và 1 phiếu chưa có giá trị nào |
| AC-8 | **Luồng trao đổi.** Luồng gồm đúng các comment chọn theo quy tắc B-5, xếp theo thời gian tạo, cũ ở trên, mới ở dưới. Mỗi tin hiện tên người viết, thời điểm và nội dung. Tin của bot phân biệt được với tin của người. Comment của người mà không có từ khóa, và comment của phiếu khác, không hiện. Khu vực có một dòng hướng dẫn cố định tiếng Việt, nêu các trường hợp bot không trả lời (B-8), không chứa giá trị cấu hình nào | Test tự động với dữ liệu gieo: 3 comment của người có từ khóa (1 comment viết hoa khác), 2 comment của người không có từ khóa, 2 comment của agent, 1 comment có từ khóa trên phiếu khác → đúng 5 tin, đúng thứ tự. Nếu quy tắc chọn nằm hoàn toàn ở trang mà profile chưa có slot test JavaScript → bước tay với cùng bộ dữ liệu gieo |
| AC-9 | **Gửi tin.** Nội dung rỗng sau khi bỏ khoảng trắng → không gửi, hiện thông báo tiếng Việt. Nội dung khác rỗng → tạo đúng 1 core `Comment` trên phiếu, có `comment_type = "Comment"` và `owner` là người đang đăng nhập (không phải tài khoản agent). Nội dung lưu là chữ người gõ, cộng thêm từ khóa kích hoạt đang cấu hình nếu chữ đó chưa chứa từ khóa (không viết cứng `@ai`). Ký tự `<`, `>`, `&` người gõ hiện ra đúng như đã gõ, không thành thẻ HTML. Tin vừa gửi hiện trong luồng ngay khi gửi xong, và hiện ở tab Comments/Activity của Helpdesk như mọi comment khác. Gửi thất bại (mất mạng, thiếu quyền) → hiện thông báo tiếng Việt, chữ đã gõ không mất, không có comment nào được tạo | Test tự động trên đường gửi, các trường hợp: rỗng; chưa có từ khóa; đã có từ khóa viết hoa khác; có `<b>`; thiếu quyền. Bước tay: gửi 1 tin, thấy tin trong luồng và trong tab Comments |
| AC-10 | **Chốt an toàn như cũ.** Ở mỗi nhánh sau, tin gửi từ khu vực cho kết quả giống hệt một comment cùng nội dung tạo bằng cách hiện có: agent tắt; mức L0 (bot không trả lời, 0 comment của bot); phiếu thuộc nhóm loại trừ; phiếu có cờ "Không dùng AI cho phiếu này"; phiếu đã đủ `max_runs_per_ticket_per_day` lần trong ngày; đã vượt ngân sách tháng (hạ về L1); người có role `ERP AI Instructor` (chỉ thị); người được người khác giao phiếu (chỉ thị trên phiếu đó); người còn lại (dữ liệu). "Giống hệt" nghĩa là: cùng quyết định xếp hàng và cùng lý do bỏ qua; cùng bản ghi ERP AI Log (`entry_type`, `stop_reason`, người ra lệnh); cùng bộ tool; cùng số lời gọi gateway với cùng stub. Ở nhánh nhóm loại trừ và cờ không dùng AI: 0 lời gọi gateway (NFR-4 của FEAT-001) | Test tự động, tham số hóa theo 9 nhánh, so hai đường với cùng stub gateway |
| AC-11 | **Trực tiếp, không tải lại (NFR-3).** Đang mở khu vực trên phiếu P và gửi tin ở mức L1 trở lên: (a) chỉ báo FEAT-002 (câu chữ cấu hình, rồi "Đang làm: <nhãn>…") hiện trong khu vực; (b) comment trả lời của bot hiện trong luồng ≤ 10 s sau khi được lưu; (c) chỉ báo mất ≤ 10 s sau khi câu trả lời hiện ra, và tự mất sau 600 s nếu không có tín hiệu kết thúc (FEAT-002 AC-11); (d) tại mỗi thời điểm, một lần chạy chỉ có một chỉ báo trên cả trang (FEAT-002 AC-10 (i)); (e) 4 mục AI do bot ghi trong lần chạy hiện giá trị mới ≤ 10 s; (f) tin có từ khóa do người khác thêm vào (ở phiên thứ hai) hiện ≤ 10 s; (g) khi đang xem phiếu Q thì không hiện tin hay chỉ báo của phiếu P. Cập nhật trực tiếp sẵn có của trang Helpdesk vẫn chạy (FEAT-002 AC-10 (h)) | Bước tay với hai phiên, đo bằng đồng hồ, ghi kết quả từng ý (a)–(g) vào `acceptance.md` |
| AC-12 | **Văn bản an toàn.** Mọi nội dung lấy từ phiếu, comment hay model đều hiện dưới dạng chữ thường. Không phần tử HTML nào được tạo ra từ nội dung đó. Ngắt dòng được giữ; định dạng (đậm, danh sách) và liên kết không được giữ (B-7). Dữ liệu gieo: `<img src=x onerror="window.__erp_ai_xss=1">`, `<script>window.__erp_ai_xss=1</script>` và `<a href="javascript:window.__erp_ai_xss=1">x</a>`, đặt trong comment của bot và trong hướng giải quyết. Kết quả phải là: chuỗi hiện ra dưới dạng chữ (hoặc mất thẻ); `window.__erp_ai_xss` vẫn là `undefined`; không có phần tử `img`, `script` hay `a` mới trong khu vực. Mã giao diện phần 2 không chứa `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `new Function` (danh sách ở Ràng buộc của ADR-007) | Test Python đọc các tệp mã giao diện, theo cách ràng buộc của ADR-007. Bước tay với dữ liệu gieo, kiểm cả console |
| AC-13 | **Khách và người không có quyền.** (a) HD Contact mở `/helpdesk/my-tickets/<id>`: không thấy khu vực, không thấy 4 mục AI, không thấy luồng. (b) Mỗi đường đọc hoặc gửi phía server mà khu vực dùng (nếu có) kiểm quyền ngay tại server. Các tài khoản sau bị từ chối và không nhận dữ liệu AI hay comment: người không có role Agent (HD Contact, Website User), Guest, và người không có quyền đọc phiếu. (c) Người không có quyền tạo comment trên phiếu thì cũng không tạo được comment qua khu vực | Test tự động gọi từng đường server bằng tài khoản HD Contact, Guest, và Agent không có quyền đọc phiếu → `PermissionError` hoặc 0 dữ liệu. Bước tay cho (a) trên trang khách |
| AC-14 | **Không ghi để hiển thị, không tốn tiền (NFR-4).** Khi mở khu vực, chuyển phiếu và nhận cập nhật trực tiếp: 0 bản ghi được tạo, sửa hay xóa (đếm `Comment`, `HD Ticket.modified`, `ERP AI Log`, `ToDo`, `Task`); 0 lời gọi gateway; không ghi `localStorage`, `sessionStorage` hay cookie. Không có DocType mới, không có field mới trên HD Ticket hay trên 3 DocType của phần 1. Gửi 1 tin → đúng 1 `Comment` mới của người. Phần còn lại do luồng FEAT-001/FEAT-002 làm như khi comment được gõ ở ô Comments | Test tự động đếm bản ghi trước và sau khi gọi đường đọc (nếu có), với stub gateway đếm được 0 lời gọi. Test Python đọc tệp mã giao diện: không có `localStorage`, `sessionStorage`, `document.cookie`. `git diff --stat team/FEAT-002...team/FEAT-003` không có tệp JSON DocType mới |
| AC-15 | **Không lùi.** AC-1..AC-5 vẫn đạt (AC-5 vẫn đúng vì không có field mới). Toàn bộ test của FEAT-001 và FEAT-002 xanh mà không sửa assertion (STD-TEST-5). `cmd.test` xanh. `cmd.migrate` thành công. Giá trị ERP AI Setting trên `miyano` trước và sau như nhau. Khi khu vực không hiện, chỉ báo FEAT-002 ở vị trí cũ vẫn chạy (FEAT-002 AC-10) | Dán đầu ra `cmd.test` và `cmd.migrate` vào `acceptance.md`. Chạy lại bước tay FEAT-002 AC-10 |

**Thứ tự bỏ trước nếu thiếu thời gian** (cỡ L, > 5 AC; bước 8 của analyze):
1. Chữ "Chưa có" cho mục trống ở AC-7 → để trống.
2. Dòng hướng dẫn cố định ở AC-8 → không có.
3. AC-11 (e): 4 mục AI cập nhật trực tiếp → chỉ cập nhật khi mở lại khu vực hoặc tải lại trang.
4. AC-11 (f): tin của người khác hiện trực tiếp → hiện khi tải lại trang.

Không được bỏ: AC-6 (trừ ý dòng hướng dẫn), AC-9, AC-10, AC-11 (a)(b)(c)(d)(g), AC-12, AC-13, AC-14, AC-15. Đây là các tiêu chí người yêu cầu đòi phải có: khách không thấy, văn bản an toàn, đúng policy, không ghi để hiển thị, cập nhật trực tiếp khi bot trả lời, ghép chỉ báo FEAT-002.

### Assumptions decided by the team (phần 2)
- **B-1. Vị trí: tab trên trang phiếu nhân viên (desktop); không được thì P2 → P3 → P4.**
  - Chọn: P1, tab cạnh Activity/Emails/Comments, nếu research tìm được cách không sửa Helpdesk. Nếu không: P2 (khối riêng trên cùng trang), rồi P3 (trang riêng của app mở từ phiếu), cuối cùng P4 (tab Desk).
  - Vì sao: nhân viên làm việc ở `/helpdesk`, ít dùng Desk (intake dòng 23); sửa Helpdesk bị cấm (intake dòng 36). P2 và P3 vẫn giữ được "≤ 1 lần bấm từ trang phiếu"; P4 thì không.
  - Thay thế: làm trang riêng ngay từ đầu; hoặc tab Desk.
  - Sai thì: architect ghi phương án đã chọn vào ADR. Nếu phải dùng P4 thì `--amend` AC-6 (`[changed]`) và team-leader báo người. Nếu mọi phương án đều buộc sửa Helpdesk thì dừng, `NEEDS_ANSWER`.
- **B-2. Bản di động ngoài phạm vi.**
  - Chọn: `MobileTicketAgent.vue` không có khu vực; chỉ yêu cầu trang di động không có lỗi mới (AC-6).
  - Vì sao: trang di động có danh sách tab riêng; FEAT-002 cũng chỉ làm desktop (FEAT-002 AC-10); người yêu cầu nêu mặc định này.
  - Thay thế: làm cả bản di động.
  - Sai thì: mở feature riêng cho di động.
- **B-3. Nội dung khu vực.**
  - Chọn: 4 mục AI chỉ đọc + luồng + dòng hướng dẫn + ô gửi + chỉ báo FEAT-002 (intake dòng 24, 27).
  - Vì sao: đúng mục "Nội dung tab" của intake mà người đã đồng ý.
  - Thay thế: thêm ERP AI Log, chi phí, lịch sử phân loại.
  - Sai thì: `--amend` thêm AC; chi phí và Log cần quyết định quyền vì nhân viên hiện không đọc được.
- **B-4. Tin trao đổi vẫn là core `Comment` trên phiếu, tái dùng toàn bộ luồng FEAT-001.**
  - Chọn: ô gửi tạo comment của chính người dùng (có từ khóa); bot trả lời bằng `post_comment` như hiện nay. Không có DocType mới.
  - Vì sao: giữ nguyên ADR-004 (một chủ ghi; chỉ `post_comment` tạo comment của agent; agent không xóa bản ghi) và D8 (tác giả lấy từ `owner`). Điều kiện kích hoạt, thẩm quyền và các chốt an toàn đã có test. Kênh riêng thì cần dòng mới trong bảng chủ ghi, đường kích hoạt mới, và `authority.py` (đọc core `Comment`) sẽ không thấy tin, tức là nới ADR-004 và mô hình thẩm quyền.
  - Thay thế: kênh riêng (DocType mới), không hiện trên timeline phiếu.
  - Sai thì: mở feature riêng kèm ADR mới, và phải hỏi người vì đụng ADR-004.
- **B-5. Quy tắc chọn tin cho luồng.**
  - Chọn: comment của tài khoản agent, cộng comment của người có từ khóa kích hoạt (xem Dữ liệu phần 2). Comment bot đăng trong lần chạy do tạo phiếu (L1) cũng hiện, vì đó là lời của bot trên phiếu.
  - Vì sao: đúng tập comment gọi bot và comment bot viết; các comment khác vẫn ở tab Comments.
  - Thay thế: hiện mọi comment; hoặc ghép thành từng cặp hỏi–đáp theo lần chạy.
  - Sai thì: sửa quy tắc trong AC-8.
- **B-6. Tự thêm từ khóa kích hoạt khi tin chưa có.**
  - Chọn: dùng giá trị `trigger_keyword` đang cấu hình, chỉ thêm khi chữ người gõ chưa chứa từ khóa. Vị trí chèn do designer chọn.
  - Vì sao: "cho user dễ sử dụng", không phải nhớ `@ai`; vẫn dùng đúng điều kiện kích hoạt hiện có, không mở đường kích hoạt mới.
  - Thay thế: một đường kích hoạt riêng không cần từ khóa. Cách này phải sửa handler và runner nên không chọn.
  - Sai thì: bỏ phần tự thêm; AC-9 `[changed]`.
- **B-7. Hiện dạng chữ thường, giữ ngắt dòng.**
  - Chọn: không giữ định dạng hay liên kết.
  - Vì sao: ADR-007 Quyết định 6 và STD-SEC-3. Nội dung bot là HTML do model sinh qua `post_comment`; hướng giải quyết là Text Editor. Muốn cho phép một tập thẻ HTML thì phải có ADR riêng.
  - Thay thế: HTML đã lọc theo danh sách thẻ an toàn.
  - Sai thì: viết ADR nêu bộ lọc; AC-12 `[changed]`.
- **B-8. Không báo lý do cụ thể khi bot không trả lời.**
  - Chọn: một dòng hướng dẫn cố định, ví dụ "Bot có thể không trả lời khi đang tắt, đang ở chế độ chỉ ghi nhận, phiếu không dùng AI hoặc thuộc nhóm loại trừ, hoặc đã hết lượt hôm nay". Không đọc cấu hình, không nói nhánh nào đang áp dụng.
  - Vì sao: muốn nói đúng lý do thì phải đọc cấu hình hoặc Log, mà nhân viên không có quyền đọc; làm vậy còn lộ danh sách nhóm loại trừ. Intake cũng không yêu cầu.
  - Thay thế: hiện trạng thái "bot có trả lời phiếu này không" qua một đường đọc có kiểm quyền.
  - Sai thì: thêm AC mới; architect quyết định đường đọc và những gì được lộ.
- **B-9. Chỉ báo FEAT-002 trong khu vực.**
  - Chọn: khi khu vực đang hiện, chỉ báo của lần chạy nằm trong khu vực. Trên cả trang, mỗi lần chạy chỉ có một chỉ báo. Khi khu vực không hiện, chỉ báo ở vị trí của FEAT-002.
  - Vì sao: intake dòng 27; FEAT-002 AC-10 (i) đã đòi "một lần chạy chỉ hiện một chỉ báo".
  - Thay thế: hai chỉ báo cùng lúc (trong khu vực và ở vị trí cũ).
  - Sai thì: bỏ AC-11 (d).
- **B-10. Không có công tắc riêng cho khu vực.**
  - Chọn: không thêm field cấu hình. Khu vực luôn có cho nhân viên khi app đã cài. Khi agent tắt, khu vực vẫn hiện nội dung và dòng hướng dẫn.
  - Vì sao: AC-5 cấm đổi metadata ngoài mô tả và nhóm; STD-DESIGN-5.
  - Thay thế: thêm field bật/tắt khu vực trong ERP AI Setting.
  - Sai thì: `--amend` nới AC-5 cho field mới.
- **B-11. Đọc và gửi chạy dưới đúng phiên và quyền của người dùng; cách làm do architect chọn.**
  - Chọn: yêu cầu nghiệp vụ là không dùng tài khoản agent, không bỏ qua phân quyền, không cấp quyền mới cho ai. Nếu cần gọi server (trái ADR-007 Quyết định 5) thì architect sửa ADR-007 hoặc viết ADR mới. Đây là quyết định kỹ thuật, không hỏi người.
  - Vì sao: không có ô gửi thì không có "trao đổi"; ADR-007 Quyết định 5 là quy tắc về kênh giao diện, không nằm trong bốn quy tắc an toàn mà người giữ lại quyền quyết.
  - Thay thế: khu vực chỉ hiển thị, người gửi tin bằng tab Comments. Cách này trái yêu cầu gốc.
  - Sai thì: nếu architect kết luận mọi cách gửi đều phải nới ADR-004, mô hình thẩm quyền, NFR-4 của FEAT-001 hay quy tắc khách không thấy dữ liệu AI, hoặc phải sửa Helpdesk, thì dừng và trả `NEEDS_ANSWER` qua team-leader.
- **B-12. Chỉ đọc và chỉ gửi.**
  - Chọn: không sửa hướng giải quyết, không sửa hay xóa tin, không đính kèm, không nhắc tên người trong khu vực.
  - Vì sao: theo ADR-004, hướng giải quyết do tool ghi; đính kèm không bao giờ được gửi lên API (NFR-4 của FEAT-001); các việc này vẫn làm được ở tab Comments.
  - Thay thế: cho làm các việc trên ngay trong khu vực.
  - Sai thì: mở feature riêng.
- **B-13. Số đo.**
  - Chọn: 10 s lấy từ NFR-5 của FEAT-002. Không có NFR về thời gian mở khu vực. Luồng không phân trang.
  - Vì sao: intake và người không cho số nào. Phiếu có ít comment (71 phiếu lịch sử, FEAT-001 spec mục Người dùng).
  - Thay thế: chỉ hiện N tin gần nhất; đặt giới hạn thời gian mở.
  - Sai thì: thêm NFR khi có số đo trên `miyano`.
- **B-14. Thẩm quyền không đổi.**
  - Chọn: tin gửi từ khu vực là comment của chính người gửi, nên thẩm quyền theo FEAT-001 AC-7. Khu vực không hiện nhãn "chỉ thị" hay "dữ liệu".
  - Vì sao: không cấp thêm quyền qua kênh mới (intake dòng 26).
  - Thay thế: hiện cho người gửi biết lời mình là "chỉ thị" hay "dữ liệu".
  - Sai thì: thêm AC; nhãn chỉ được tính ở server.

### Đề xuất về cỡ
- Giữ cỡ L. Tiêu chí chia thành hai nhóm độc lập: phần 1 (AC-1..AC-5, chỉ metadata) và phần 2 (AC-6..AC-15, giao diện trên trang phiếu). Tech-lead có thể lên kế hoạch và build phần 1 trước, không phải chờ research của phần 2. Analyst không tự đổi cỡ.

### Artifact bị ảnh hưởng (cho team-leader điều phối)
- FEAT-003 chưa có `design.md`, `plan.md` hay `tasks.md`, nên không có artifact nào phải sửa lại.
- Mới cần làm: `research.md` cho RQ-1..RQ-8 (`/team:research FEAT-003`), rồi `arch-impact.md` (`/team:architect FEAT-003`), rồi `design.md`.
- ADR cần architect xem lại: ADR-007 Quyết định 5–6 (script gọi server để đọc và gửi; hiện văn bản), ADR-008 Quyết định 6 (một bên nghe tín hiệu nữa ở phía trang; một chỉ báo mỗi lần chạy). ADR-004 và mô hình thẩm quyền không đổi (B-4, B-14).
- FEAT-002: phải chạy lại bước tay AC-10 (h)(i) sau khi build phần 2 (AC-15).

### Definition of Done (bổ sung cho phần 2)
**Phần build (trước G4):**
- [ ] AC-6..AC-15: phần tự động đạt; đầu ra dán trong `acceptance.md`; đầu ra đỏ trước khi viết mã dán vào build log (STD-TEST-1).
- [ ] Bước tay của AC-6, AC-7, AC-8 (nếu không có slot test JavaScript), AC-11, AC-12, AC-13 có kịch bản trong `acceptance.md`, ghi rõ ai làm và khi nào (sau bàn giao).
- [ ] ADR cho kênh giao diện của phần 2 (sửa ADR-007 hoặc ADR mới) đã viết trước khi build (STD-DOC-4).
- [ ] `git -C ../helpdesk status --porcelain` không có dòng nào do FEAT-003 tạo.
- [ ] `cmd.test` xanh, `cmd.lint` sạch, không có dấu skip; `cmd.migrate` thành công; giá trị ERP AI Setting không đổi.

**Phần sau G4 (`/team:asbuilt`):**
- [ ] As-Built ghi phương án vị trí đã dùng (P1–P4) và lý do.
- [ ] Tài liệu người dùng (bắt buộc, STD-DOC-2): cách mở khu vực, cách gửi câu hỏi, khi nào bot không trả lời; ghi rõ chạy lại bước tay AC-6, AC-11 sau mỗi lần nâng Helpdesk/Frappe.
- [ ] Mục CHANGELOG cho phần 2.
- [ ] CI xanh trên nhánh.
