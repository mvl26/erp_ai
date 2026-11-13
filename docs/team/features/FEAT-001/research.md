Feature: FEAT-001
Stage: research
Author-agent: researcher
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Research FEAT-001 — các câu hỏi kỹ thuật H-2..H-6 của spec

Câu hỏi lấy từ spec mục "Chuyển cho architect / designer / researcher" (`spec.md:157-163`). H-1 (vị trí module) là quyết định cấu trúc của architect, không cần tài liệu ngoài → không xét ở đây.

| Câu | Nội dung | Dạng câu trả lời |
|---|---|---|
| Q1 (H-4, H-6) | SDK Anthropic: ghim bản nào; lấy header hạn mức thế nào; phân loại lỗi cho cầu dao AC-17; prompt caching và các trường usage cho AC-15 | bảng phương án ghim + bảng sự kiện đã kiểm |
| Q2 (H-2, H-3) | Helpdesk 15.1.0 hiện trường `ai_*` cho HD Agent và ẩn với khách bằng cơ chế nào; `frappe.enqueue(job_id, deduplicate, enqueue_after_commit)` của Frappe 15.126.1 có chống trùng đủ cho AC-5(f) không | có/không + lỗ hổng + phương án |
| Q3 (H-5, H-6) | Công cụ tìm mã nguồn cho tool đọc (AC-13); khai phụ thuộc ở đâu | bảng phương án |

## Câu trả lời ngắn
- **Q1:** Bench env đang có `anthropic` 0.103.1, và app `workflowcore` dùng chung env này, gọi `temperature=` — tham số này bị gỡ ở SDK 1.x. Khuyến nghị ghim `anthropic>=0.103.1,<1` trong `pyproject.toml`, tạo client với `max_retries=0` và `timeout` tường minh để cầu dao của app (không phải SDK) quyết định chuyển khóa. Đọc header bằng `client.messages.with_raw_response.create(...)` → `.headers` + `.parse()` (có trong 0.103.1). Tên header guide `:829-834` khớp tài liệu hiện hành. Ba điểm guide thiếu: 402 `billing_error`, 429 vượt trần chi tiêu không có `retry-after` (`error_code = enforced_spend_limit_reached`), và 400 khi chạm hạn mức tự đặt. Độ tin cậy: **cao** cho phần SDK (đọc mã 0.103.1 + docs); **trung bình** cho tên header với API version `2023-06-01` mà SDK 0.103.1 gửi (docs hiện hành mô tả SDK 2.x / API `2026-10-21`).
- **Q2:** Helpdesk v15.1.0 **vẫn dùng** HD Ticket Template (mô tả "will be deprecated in the future", nhưng chưa có cơ chế thay: HD Field Layout chỉ có kiểu "Landing Page"). Để ẩn trường: đặt permlevel 8 cho custom field (ẩn cả ở API), rồi thêm dòng vào template `Default` với `Visible to = Agents` (ẩn trên trang Helpdesk). Ô "Hide from Customer" trong guide `:575` đã được thay bằng `Visible to`. `deduplicate=True` có trên Frappe 15.126.1, nhưng việc kiểm trùng chạy lúc gọi `enqueue` còn việc đẩy job chạy sau commit. Vì vậy hai lần kích hoạt **trong cùng một giao dịch** đều qua được bước kiểm và đẩy cùng một job id hai lần vào RQ. Thêm nữa, job chạy dưới user đã lưu phiếu, không phải tài khoản agent. Độ tin cậy: **cao** (mã nguồn đúng tag + docs Helpdesk).
- **Q3:** Máy dev không có `rg`; `/usr/bin/grep` là ugrep 7.8.4. Khuyến nghị tìm bằng Python thuần (`os.walk`, không theo symlink, `realpath` + `commonpath` để chặn đường dẫn thoát ra ngoài `apps/`), không phụ thuộc lệnh ngoài. Phụ thuộc Python khai ở `[project] dependencies` của `pyproject.toml`, không cần `requirements.txt`. Độ tin cậy: **cao** cho phần khai phụ thuộc; **trung bình** cho hiệu năng tìm bằng Python trên `apps/` của production (chưa đo, `UNVERIFIED`).

## Phiên bản đang dùng
Lấy từ bench env `/home/miyano/frappe-bench/env/lib/python3.12/site-packages/*.dist-info` và manifest của từng app (`erp_ai/pyproject.toml:10-12` chưa khai phụ thuộc nào):

| Gói | Phiên bản | Nguồn |
|---|---|---|
| frappe | 15.126.1 | `apps/frappe/frappe/__init__.py` (`__version__`), `frappe-15.126.1.dist-info` |
| helpdesk | 15.1.0 (tag `v15.1.0`, commit `a1858964`) | `apps/helpdesk/helpdesk/__init__.py`, `git log -1` |
| anthropic | 0.103.1 (cài bằng pip ngày 2026-05-20; `Requires-Python >=3.9`) | `anthropic-0.103.1.dist-info/METADATA`, `anthropic/_version.py:4` |
| httpx | 0.28.1 | `httpx-0.28.1.dist-info` |
| rq | 1.15.1 | `rq-1.15.1.dist-info` |
| pydantic | 2.12.5 (frappe ghim `~=2.12.0`, `apps/frappe/pyproject.toml:64`) | `pydantic-2.12.5.dist-info` |
| Python | 3.12 | `env/lib/python3.12` |
| ai dùng chung `anthropic` | `workflowcore` khai `anthropic>=0.39.0` (`apps/workflowcore/requirements.txt:5`), gọi `temperature=` (`workflowcore/services/ai_service.py:81`) | đọc mã |

Bản mới nhất trên PyPI là 2.8.0 (2026-11-10); 1.0.0 ra ngày 2026-08-20, 2.0.0 ra ngày 2026-10-21 (PyPI, truy cập 2026-11-11). Production chưa đối chiếu (spec A-2).

## Q1 — SDK Anthropic

### Sự kiện đã kiểm
| Mục | Giá trị cho 0.103.1 | Nguồn |
|---|---|---|
| Đọc header | `client.messages.with_raw_response.create(...)` trả `APIResponse`; `.headers` là `httpx.Headers`; `.parse()` trả `Message` | `anthropic/resources/messages/messages.py:88`, `anthropic/_response.py:83,301-312`; docs Python SDK "Accessing raw response data" |
| Tên header hạn mức | `anthropic-ratelimit-{requests,tokens,input-tokens,output-tokens}-{limit,remaining,reset}`; `*-reset` theo RFC 3339; `tokens-remaining` "rounded to the nearest thousand"; `retry-after` tính bằng giây | docs Rate limits "Response headers" |
| `anthropic-ratelimit-tokens-*` | "display the values for the most restrictive limit currently in effect"; không có giới hạn workspace thì là tổng input+output | docs Rate limits "Response headers" |
| API version SDK gửi | `anthropic-version: 2023-06-01` | `anthropic/_client.py:359` |
| Retry mặc định | `DEFAULT_MAX_RETRIES = 2`; SDK tự retry khi có header `x-should-retry`, 408, 409, 429, ≥500 | `anthropic/_constants.py:10`, `anthropic/_base_client.py:806-833`; docs Python SDK "Retries" |
| Timeout mặc định | `httpx.Timeout(timeout=600, connect=5.0)`; timeout cũng được retry 2 lần | `anthropic/_constants.py:9`; docs Python SDK "Timeouts" |
| Ánh xạ mã lỗi → lớp | 400 `BadRequestError`, 401 `AuthenticationError`, 403 `PermissionDeniedError`, 404, 409, 413 `RequestTooLargeError`, 422, 429 `RateLimitError`, 529 `OverloadedError`, ≥500 `InternalServerError`, còn lại `APIStatusError`; **402 không có lớp riêng** → `APIStatusError` với `status_code == 402` | `anthropic/_client.py:495-531` |
| Lỗi kết nối / hết giờ | `APIConnectionError`, `APITimeoutError` (lớp con của `APIConnectionError`) | `anthropic/_exceptions.py:86-91` |
| 402 | `billing_error`: "There's an issue with your billing or payment information" | docs Errors "HTTP errors" |
| 429 do trần chi tiêu theo tier | `rate_limit_error`, **không có `retry-after`**, `error.details.error_code = "enforced_spend_limit_reached"`; retry sẽ thất bại tới 00:00 UTC ngày 1 tháng sau | docs Rate limits "Reaching your spend cap" |
| 400 do hạn mức tự đặt | `invalid_request_error`, message bắt đầu "You have reached your specified API usage limits" (hoặc "...workspace API usage limits") | docs Rate limits "Setting your own spend limit" |
| 529 | `overloaded_error` | docs Errors |
| Request id | header `request-id`; `message._request_id` | docs Errors "Request ID" |
| `cache_control` | `TextBlockParam` và `ToolParam` có `cache_control: CacheControlEphemeralParam` | `anthropic/types/text_block_param.py:19`, `anthropic/types/tool_param.py:49` |
| Trường usage | `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `cache_creation` (theo TTL) | `anthropic/types/usage.py:14-20`; docs Prompt caching |
| Prompt caching | thứ tự tiền tố `tools` → `system` → `messages`; tối đa 4 breakpoint; TTL mặc định 5 phút; sửa định nghĩa tool làm mất cả cache; prompt ngắn hơn ngưỡng của model thì không cache và **không báo lỗi** | docs Prompt caching |
| Đơn giá cache | ghi 5 phút = 1,25× giá input; ghi 1 giờ = 2×; đọc = 0,1× (một số model có ngoại lệ, ví dụ 0,05×) | docs Prompt caching "Pricing" |
| Tổng input | `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` | docs Rate limits "Cache-aware ITPM" |

Hệ quả cho thiết kế (designer chốt):
- Chi phí mỗi lượt (AC-15) phải tính riêng ba loại token input với ba đơn giá (input, ghi cache, đọc cache) cộng output. Một đơn giá input duy nhất sẽ tính sai. Hệ số ghi/đọc cache khác nhau theo model → để trong cấu hình như đơn giá (guide `:680`).
- Cầu dao AC-17 cần bổ sung vào bảng guide `:792-799`: 402 → "Hết hạn mức" (hoặc "Lỗi khóa", architect chọn); 429 có `error_code = enforced_spend_limit_reached` → "Hết hạn mức", không dùng giá trị mặc định 60 s của guide `:863`; 400 với message "You have reached your specified ... usage limits" → "Hết hạn mức". Nếu không bổ sung, cả ba trường hợp rơi vào nhánh 400 "không chuyển khóa" hoặc nhánh 429 "nghỉ 60 s rồi thử lại", và sẽ thử lại vô ích.
- Đặt `max_retries=0`: nếu để mặc định 2, SDK tự retry 429/5xx/timeout trên **cùng một khóa** trước khi cầu dao của app thấy lỗi. Khi đó số lần thử thật bằng `max_key_thu × 3`, sai NFR-7. Trường hợp tệ nhất, timeout mặc định 600 s × 3 lần vượt thời hạn job 600 s (NFR-2).
- Với SDK 0.103.1, tên header hạn mức khi gửi API version `2023-06-01` chưa được kiểm trên một response thật: `UNVERIFIED`. Guide `:868` / `:1518` đã ghi việc này thành điểm kiểm chứng của người. Vì vậy mã đọc header phải chịu được header vắng mặt (không có header → không cập nhật `token_con_lai`).

### Phương án ghim SDK
| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| A. `anthropic>=0.103.1,<1` (giữ bản đang có) | Không đổi env dùng chung; `workflowcore` không vỡ; mọi API cần dùng (`with_raw_response`, `cache_control`, lớp lỗi) đã kiểm trên mã 0.103.1 | Dòng 0.x đã cũ (mới nhất 2.8.0); docs hiện hành viết cho 2.x (httpx2, API `2026-10-21`) → phải đối chiếu mã, không chép ví dụ docs nguyên văn | 0.x còn được vá bảo mật hay không: `UNVERIFIED`; model mới có thể cần tính năng chỉ có ở 1.x/2.x (`UNVERIFIED`) | Thấp |
| B. `anthropic>=2,<3` (bản hiện hành) | Khớp docs hiện hành; API version mới | `bench setup requirements` nâng gói trong env dùng chung → `workflowcore` truyền `temperature` (đã gỡ ở 1.x theo MIGRATION.md) sẽ vỡ; thêm gói `httpx2`; phải đọc thêm hướng dẫn chuyển 1.x→2.x | Làm hỏng một app khác ngoài phạm vi FEAT-001 (intake: không đụng app khác) | Trung bình–cao (sửa app khác hoặc tách env) |
| C. Không dùng SDK, gọi HTTP bằng `httpx` 0.28.1 có sẵn | Kiểm soát trọn header/retry/timeout; không phụ thuộc phiên bản SDK | Tự viết ánh xạ lỗi, kiểu tool-use, phân tích usage; thêm mã phải test | Lệch đặc tả API khi API đổi | Trung bình |

### Khuyến nghị Q1
Phương án **A**, chờ architect quyết. Lý do: đây là lựa chọn duy nhất không làm vỡ `workflowcore` trong env dùng chung, và mọi API mà FEAT-001 cần đã có trong 0.103.1. Cấu hình client: `Anthropic(api_key=..., max_retries=0, timeout=<giá trị trong cấu hình, ví dụ 120 s>)`. Lý do chọn 120 s: 8 lượt × 120 s > 600 s, nên vòng lặp phải kiểm thời gian còn lại của job; con số cụ thể là quyết định của designer, `UNVERIFIED` về độ trễ thật. Khi nâng lên 1.x/2.x thì mở feature `dependency-upgrade` riêng, gồm cả `workflowcore`.

## Q2 — Helpdesk 15.1.0 và Frappe 15.126.1

### Hiện trường `ai_*` (H-2)
Sự kiện:
- `HD Ticket Template` vẫn là nguồn bố cục tab chi tiết của agent: `TicketFields.get_layout()` trả các dòng template đang hiện, rồi tới các trường lõi `priority`, `ticket_type`, `customer`, `agent_group` (`apps/helpdesk/helpdesk/ticket_fields.py:31-46`, `helpdesk/consts.py:48`). Một custom field **không** có dòng trong template `Default` thì không hiện ở tab này (suy ra từ mã; chưa thử trên giao diện → `UNVERIFIED` cho phần frontend).
- `HD Field Layout` ở bản này chỉ có `type = "Landing Page"` (`hd_field_layout.json`), nên chưa phải cơ chế thay thế cho trường phiếu. Mô tả "This doctype will be deprecated in the future" (`hd_ticket_template.json:7`) chỉ là cảnh báo.
- Dòng template có `visible_to` (`Everyone`/`Agents`, mặc định `Everyone`) thay cho ô "Hide from customer" cũ (`hd_ticket_template_field.json:32-38`; docs Helpdesk: "Visible to replaces the old 'Hide from customer' checkbox").
- Permlevel: 7 = khách đọc được; 8 = chỉ agent (`helpdesk/consts.py:7-9`). HD Ticket cấp permlevel 8 đọc/ghi cho `System Manager`, `Agent`, `Agent Manager` (`hd_ticket.json:600-612`). Docs: permission level là "the only thing that hides a field from the API"; "Level 8 is never given to your own roles". Do đó role agent riêng của erp_ai không tự có quyền level 8 — tài khoản agent cần thêm role `Agent` (đúng như AC-4) hoặc được cấp quyền level 8 tường minh.
- Template báo lỗi khi lưu nếu một trường permlevel ≥ 8 nằm ở dòng `Visible to = Everyone` (`hd_ticket_template.py:48-69`).
- Bản ghi phân quyền theo trường ở level 7 cho `Agent` có đọc/ghi (`hd_ticket.json:578-581`), nên tài khoản agent (role `Agent`) ghi được `ticket_type`/`agent_group`/`priority`.
- `HD Form Script.apply_to` có `Form`/`List` (`hd_form_script.json:31-35`) — không cần cho FEAT-001 (nút Custom Action nằm ngoài phạm vi theo spec).

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| A. Custom field `ai_*` permlevel 8 (fixture) **và** app tự thêm dòng vào template `Default` với `Visible to = Agents` (lúc cài/migrate, lặp lại không lỗi) | Ẩn với khách ở cả trang và API; AC-20 lặp lại được trên mọi site; test tự động kiểm được dòng template | Sửa một bản ghi cấu hình do Helpdesk sở hữu; bản Helpdesk sau có thể bỏ template | Nâng Helpdesk lên bản bỏ template → mất hiển thị (không mất dữ liệu) | Thấp |
| B. Custom field permlevel 8 (fixture); Hiếu thêm dòng template bằng tay (guide bước 4, `:1281`) | Không đụng bản ghi của Helpdesk | Phụ thuộc thao tác tay; AC-20 chỉ kiểm được sau khi người làm | Quên làm → trường không hiện, agent tưởng app hỏng | Thấp |
| C. Chỉ dùng `Visible to = Agents`, giữ permlevel 0 | Đơn giản | Khách vẫn đọc được `ai_*` qua API (docs: Visible to "does not change API access") | Lộ hướng giải quyết nội bộ cho HD Contact bên ngoài | Thấp nhưng sai NFR ẩn với khách |

Khuyến nghị: **A**, chờ designer/architect quyết. Lý do: chỉ A đáp ứng "ẩn với khách" ở tầng API và kiểm tự động được. Permlevel 8 là bắt buộc trong cả A và B.

### Chống trùng job (H-3)
Sự kiện (Frappe 15.126.1, `apps/frappe/frappe/utils/background_jobs.py`):
- Chữ ký có `enqueue_after_commit`, `job_id`, `deduplicate` (`:58-73`). `deduplicate=True` mà thiếu `job_id` → `frappe.throw` (`:91-93`).
- Việc kiểm trùng chạy **ngay lúc gọi** `enqueue`: job cùng id đang `QUEUED`/`STARTED` → bỏ qua; job cũ đã xong → xóa rồi tạo lại (`:91-103`).
- Với `enqueue_after_commit=True`, lệnh đẩy job chỉ được thêm vào `frappe.db.after_commit` (`:160-162`). `CallbackManager.add` chỉ `append`, không lọc trùng (`frappe/utils/__init__.py:1216-1218`). RQ 1.15.1 `_enqueue_job` gọi `rpush` id mà không kiểm (`rq/queue.py:484-495`, `:1098-1128`). Hệ quả: hai lần kích hoạt cùng `job_id` **trong cùng một request/giao dịch** đều qua bước kiểm (job chưa tồn tại), rồi sau commit đẩy cùng id hai lần → job có thể chạy hai lần. Đây là suy luận từ mã, chưa chạy thử: độ tin cậy trung bình cho hành vi worker khi id lặp. Hai request khác nhau thì request sau thấy job `QUEUED` và bỏ qua. Bước kiểm và bước đẩy không nguyên tử, nên hai request đồng thời vẫn có khe hở nhỏ.
- Hàng đợi `long` mặc định 1500 s (`:40-55`; docs Background Jobs cũng ghi 1500 s). NFR-2 (600 s) → phải truyền `timeout=600` tường minh.
- **Job chạy dưới user đã gọi `enqueue`:** `queue_args["user"] = frappe.session.user` (`:138-146`), và `execute_job` gọi `frappe.set_user(user)` (`:203-204`). Tức là job do người lưu phiếu kích hoạt sẽ chạy với quyền của người đó, không phải tài khoản agent. Chốt tài khoản (guide `:460-486`, AC-6) phải đổi sang tài khoản agent bên trong job rồi kiểm `frappe.session.user`.
- Test: `after_commit` chỉ chạy trong `frappe.db.commit()` (`frappe/database/database.py:1192-1198`). Test không commit thì không bao giờ có job trong hàng đợi. Test AC-5 nên đếm callback trong `frappe.db.after_commit` hoặc thay `frappe.enqueue` bằng stub, không đọc Redis (suy ra từ mã; designer chốt).

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| A. Chỉ `frappe.enqueue(..., job_id=f"erp-ai::{ticket}::{trigger}", deduplicate=True, enqueue_after_commit=True, queue="long", timeout=600)` như guide `:1023-1028` | Ít mã, đúng guide | Lỗ hổng trùng trong cùng giao dịch (ví dụ `after_insert` của phiếu và comment tạo cùng lúc) | AC-5(f) có thể đỏ nếu test kích hoạt hai lần trong một giao dịch; tốn 2 lần gọi API | Thấp |
| B. A + chặn trùng trong request: lưu tập `job_id` đã đưa vào trong `frappe.flags` (hoặc `frappe.local`), gọi lần hai thì bỏ | Đóng lỗ hổng cùng giao dịch; vài dòng mã; test được không cần Redis | Không che khe hở giữa hai request đồng thời | Rất thấp | Thấp |
| C. B + khóa ở đầu job (trường `ai_dang_chay` hoặc khóa cache theo phiếu) | Che cả khe hở đồng thời; guide `:1045` đã gợi ý cách dự phòng này | Thêm trạng thái phải dọn khi job chết giữa chừng | Khóa treo nếu worker bị giết → cần hạn khóa | Trung bình |

Khuyến nghị: **B**, chờ designer quyết. Giới hạn `max_runs_per_ticket_per_day` (AC-15) đã chặn trần chi phí nếu lỡ chạy trùng ở khe hở đồng thời.

## Q3 — Công cụ tìm mã nguồn và khai phụ thuộc

### Tìm mã nguồn (H-5)
Sự kiện: `which rg` → không có; `/usr/bin/grep` là `ugrep 7.8.4` (`grep --version`). Công cụ trên production chưa biết (`UNVERIFIED`). Python: `os.walk` mặc định không đi vào symlink trỏ tới thư mục; `os.path.realpath` khử symlink; `os.path.commonpath` cho tiền tố đường dẫn hợp lệ (docs Python 3.12). ripgrep mặc định bỏ qua `.gitignore`, file ẩn, file nhị phân và không theo symlink (ripgrep GUIDE).

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| A. Python thuần: `os.walk(followlinks=False)` dưới `apps/`, lọc đuôi theo guide `:342` và mẫu tên bí mật, so chuỗi cố định (hoặc `re` với mẫu giới hạn độ dài), dừng ở 40 kết quả và theo hạn thời gian | Không cần lệnh ngoài trên dev hay prod; cùng một mã chặn đường dẫn cho cả đọc lẫn tìm; test bằng thư mục tạm | Chậm hơn rg trên cây lớn; `re` không có timeout, mẫu regex do model đưa vào có thể chạy rất lâu (ReDoS) → nên chỉ nhận chuỗi cố định | Chậm trên `apps/` của prod (chưa đo, `UNVERIFIED`) | Thấp |
| B. `rg` qua `subprocess.run(..., timeout=30)` như guide `:365-386`; thiếu thì `ok=false` | Nhanh; bỏ qua sẵn file nhị phân/`.gitignore` | Dev không có `rg` → tool tìm không chạy được ở dev; prod phải `apt install ripgrep` (việc của người, guide `:1516`) | Tool "chưa cài" kéo dài; AC-13 chỉ kiểm được nhánh lỗi ở dev | Thấp (code), có thêm việc vận hành |
| C. `grep -rnF` hệ thống qua subprocess | Có sẵn ở dev | Dev là ugrep, prod có lẽ là GNU grep → cờ và đầu ra có thể khác (`UNVERIFIED`) | Hành vi khác giữa hai máy | Thấp |

Khuyến nghị: **A**, chờ designer quyết. Lý do: chạy giống nhau trên dev và prod, AC-13 kiểm được trọn vẹn ở local. Ràng buộc NFR-6 (30 s cho lệnh ngoài) vẫn áp cho `git log/show/diff/blame`. Nếu chọn A, nhánh "thiếu công cụ → `ok=false`" của AC-13 chỉ còn áp cho `git`.

### Khai phụ thuộc (H-6)
- Docs Frappe Cloud: "Only third-party Python packages your app imports belong in that list" (`[project] dependencies`); khai phiên bản Frappe tương thích ở `[tool.bench.frappe-dependencies]`. Docs không nhắc `requirements.txt` (trang App versioning).
- Helpdesk 15.1.0 làm đúng mẫu này: `[project] dependencies = ["textblob==..."]` và `[tool.bench.frappe-dependencies] frappe = ">=15.123.1,<16.0.0"` (`apps/helpdesk/pyproject.toml`). Helpdesk cũng khai app phụ thuộc bằng `required_apps = ["telephony"]` trong `hooks.py:9`.
- Đề xuất cho dev (không phải quyết định): `erp_ai/pyproject.toml` có `dependencies = ["anthropic>=0.103.1,<1"]`, `[tool.bench.frappe-dependencies] frappe = ">=15.126.1,<16.0.0"`, và `required_apps = ["helpdesk"]` trong `erp_ai/hooks.py`. Bỏ `requirements.txt` của guide `:640`. Liệu `bench setup requirements` có ép cài lại `anthropic` khi bản trong env đã thỏa ràng buộc hay không: `UNVERIFIED` (theo hành vi pip thông thường thì không).

## Khuyến nghị
Tóm tắt, mọi mục đều chờ architect (Q1, H-6) / designer (Q2, Q3) quyết:
1. Q1: phương án A — ghim `anthropic>=0.103.1,<1`; client `max_retries=0` + `timeout` tường minh; bổ sung 402 / `enforced_spend_limit_reached` / 400 "specified ... usage limits" vào cầu dao AC-17; chi phí AC-15 tính ba loại token input riêng.
2. Q2-H-2: phương án A — custom field `ai_*` permlevel 8 + dòng template `Default` với `Visible to = Agents` do app tạo.
3. Q2-H-3: phương án B — `deduplicate` + chặn trùng trong request; `timeout=600` tường minh; đổi user sang tài khoản agent bên trong job.
4. Q3: phương án A — tìm bằng Python thuần; khai phụ thuộc ở `pyproject.toml` + `required_apps`.

## POC (nếu có)
Không làm POC. Mã nguồn đúng phiên bản (frappe 15.126.1, helpdesk v15.1.0, anthropic 0.103.1, rq 1.15.1) trong bench và docs chính thức đã đủ trả lời. Riêng tên header hạn mức trên một response thật cần khóa API thật — không có trong phạm vi đội (spec: không gọi mạng thật) → để thành điểm kiểm chứng của người, guide `:1518`. Không tạo worktree nào.

## Nháp ADR (nếu có)
Không đánh số; architect đánh số khi quyết.

**Tiêu đề:** Ghim Anthropic SDK 0.x và để cầu dao của app tự xử lý retry

- **Bối cảnh:** bench env dùng chung có `anthropic` 0.103.1; `workflowcore` dùng SDK với `temperature`, tham số bị gỡ ở 1.x. FEAT-001 cần cầu dao theo loại lỗi, chuyển khóa (AC-17), giới hạn số lần thử (NFR-7) và thời hạn job 600 s (NFR-2). SDK mặc định retry 2 lần và timeout 600 s.
- **Phương án:** A ghim `>=0.103.1,<1`; B nâng lên `>=2,<3`; C gọi HTTP trực tiếp bằng httpx.
- **Khuyến nghị:** A, với `max_retries=0`, `timeout` lấy từ cấu hình, đọc header qua `with_raw_response`, ánh xạ lỗi theo bảng Q1 (gồm 402 và trần chi tiêu).
- **Hệ quả:** không đổi env dùng chung; phải đối chiếu mã 0.103.1 khi đọc docs viết cho 2.x; nâng SDK sau này là một feature `dependency-upgrade` gộp cả `workflowcore`; cầu dao của app là nơi duy nhất quyết định thử lại.

## Sources
- https://platform.claude.com/docs/en/api/rate-limits#response-headers — Rate limits: Response headers (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/rate-limits#reaching-your-spend-cap — Rate limits: Reaching your spend cap (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/rate-limits#setting-your-own-spend-limit — Rate limits: Setting your own spend limit (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/rate-limits#cache-aware-itpm — Rate limits: Cache-aware ITPM (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/errors#http-errors — Claude API errors: HTTP errors (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/api/errors#request-id — Claude API errors: Request ID (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python#retries — Python SDK: Retries, Timeouts, Handling errors, Accessing raw response data (truy cập 2026-11-11)
- https://platform.claude.com/docs/en/build-with-claude/prompt-caching — Prompt caching: cache_control, thứ tự tiền tố, usage, đơn giá (truy cập 2026-11-11)
- https://github.com/anthropics/anthropic-sdk-python/blob/main/MIGRATION.md — SDK migration 0.x → 1.x (httpx2, gỡ `temperature`) (truy cập 2026-11-11)
- https://github.com/anthropics/anthropic-sdk-python/blob/v0.103.1/README.md — README tại tag v0.103.1 (xác nhận tag) (truy cập 2026-11-11)
- https://pypi.org/project/anthropic/#history — Lịch sử phát hành anthropic (truy cập 2026-11-11)
- https://docs.frappe.io/helpdesk/customization/perm-levels-in-helpdesk — Helpdesk: Permission levels, Visible to (truy cập 2026-11-11)
- https://docs.frappe.io/framework/user/en/api/background_jobs — Frappe Background Jobs: enqueue, timeout hàng đợi (truy cập 2026-11-11)
- https://docs.frappe.io/cloud/private-benches/common-issues/frappe-listed-as-a-python-dependency — Frappe Cloud: khai phụ thuộc Python (truy cập 2026-11-11)
- https://docs.frappe.io/cloud/custom-apps/app-versioning/versioning — Frappe Cloud: pyproject.toml, `[tool.bench.frappe-dependencies]` (truy cập 2026-11-11)
- https://docs.python.org/3.12/library/os.html#os.walk — Python 3.12 `os.walk` followlinks (truy cập 2026-11-11)
- https://docs.python.org/3.12/library/os.path.html#os.path.realpath — Python 3.12 `os.path.realpath`, `commonpath` (truy cập 2026-11-11)
- https://github.com/BurntSushi/ripgrep/blob/master/GUIDE.md — ripgrep GUIDE: lọc mặc định, symlink, `-F` (truy cập 2026-11-11)

Mã nguồn đúng phiên bản đã đọc trong bench (đọc 2026-11-11): `apps/frappe/frappe/utils/background_jobs.py`, `apps/frappe/frappe/utils/__init__.py:1191-1221`, `apps/frappe/frappe/database/database.py:99-102,1190-1215`, `apps/helpdesk/helpdesk/ticket_fields.py`, `apps/helpdesk/helpdesk/consts.py`, `apps/helpdesk/helpdesk/helpdesk/doctype/{hd_ticket,hd_ticket_template,hd_ticket_template_field,hd_field_layout,hd_form_script}/*`, `env/lib/python3.12/site-packages/anthropic/{_client.py,_constants.py,_exceptions.py,_base_client.py,_response.py,types/usage.py}`, `env/lib/python3.12/site-packages/rq/queue.py`, `apps/workflowcore/requirements.txt`, `apps/workflowcore/workflowcore/services/ai_service.py`.
