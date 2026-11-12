Feature: BUG-001
Stage: asbuilt
Author-agent: writer
Date: 2026-11-12
Approved-by:

# As-Built BUG-001 — Hết credit (400 "credit balance is too low") được nhận là `Hết hạn mức`

Bug-fix cỡ S, không có `spec.md`/`design.md` riêng; so với hàng 6 và hàng 8 của FEAT-001 `design.md` §3.4.3 và guide `docs/HuongDan_TrienKhai_erp-ai.md:797`.

## Đã đổi gì
- `erp_ai/gateway/breaker.py`: hàm thuần `decide` trước đây chỉ coi 400 là hạn mức khi message bắt đầu `You have reached your specified` (vượt spend limit). Nay nhận thêm tiền tố `Your credit balance is too low` (tổ chức hết credit): hằng `QUOTA_MESSAGE_PREFIX` thành `QUOTA_MESSAGE_PREFIXES` (tuple hai tiền tố), điều kiện `startswith(QUOTA_MESSAGE_PREFIXES)` vẫn chỉ áp cho status 400. Diff 2+/2−.
- Hành vi: 400 hết credit trả đúng Action của hàng 6 (`Action(QUOTA, None, True, "message", "quota")`): khóa chuyển `Hết hạn mức`, gateway chuyển sang khóa kế tiếp, gửi tin báo, scheduler dò lại mỗi giờ (`reprobe_exhausted_keys`, không đổi). Trước đây 400 này rơi hàng 8 → `bad_request`: khóa vẫn `Hoạt động`, không chuyển khóa, không báo tin, không dò lại.
- Không đổi: các hàng khác của bảng cầu dao (400 khác, 422 vẫn `bad_request`; 401/403 vẫn `Lỗi khóa`), `anthropic-version`, SDK, luồng dò lại.

## Đối chiếu design ↔ thực tế (FEAT-001 `design.md` §3.4.3)
| Mục | Design | Thực tế | Khác? |
|---|---|---|---|
| Hàng 6 (400 hạn mức) | chỉ tiền tố `You have reached your specified` | thêm `Your credit balance is too low` (`breaker.py:26`, `:57`) | khác; lý do: BUG-001 intake (guide `:797` coi hết credit là `Hết hạn mức`) |
| Hàng 8 (4xx khác) | `bad_request` | giữ nguyên, ca `row8 400 other` và `row8 422` còn xanh | không |
| Chữ trong `design.md` | — | chưa ghi tiền tố mới (xem Nợ sau G4) | — |

## Test
- `erp_ai/gateway/test_breaker.py`: ca mới `row6 400 credit balance` (message thật cắt 100 ký tự như `client.py:55`). Đỏ trước sửa (`AssertionError … 'bad_request' != 'quota'`, review-01), xanh sau. 19 ca cũ không đổi.
- `cd ../.. && bench --site miyano run-tests --module erp_ai.gateway.test_breaker` → `Ran 6 tests … OK`; `--app erp_ai` lúc nghiệm thu → `Ran 507 tests … OK` (acceptance BUG-001, verdict accepted).

## Cách kiểm trên site
1. Mở `ERP AI Setting`, bấm "Kiểm tra khóa".
2. Khóa của tổ chức hết credit: kết quả có `error_kind` = `quota` (trước đây `bad_request`), dòng khóa chuyển `Hết hạn mức`, có một thư trong Email Queue.
3. Evidence đã có trên `miyano` (acceptance): khóa "Chính" → `Hết hạn mức`, `last_error` ghi `quota status=400`; thư ở trạng thái `Not Sent` vì scheduler đang tắt.

## Việc của người (không phải mã)
- Sửa hẳn lỗi hết credit: nạp credit ở Claude Console (Plans & Billing), hoặc dùng khóa của tổ chức còn credit.
- Sau khi nạp: đặt lại trạng thái khóa về `Hoạt động` ở `ERP AI Setting`, hoặc chờ lần dò lại mỗi giờ (scheduler phải đang chạy; hiện đang tắt trên `miyano`).
- Bản sửa chỉ làm app báo đúng trạng thái và báo tin; nó không làm lời gọi thành công khi tổ chức hết credit.
- Khóa dạng `sk-ant-usr-` là khóa theo người, guide mục 9.1 yêu cầu khóa workspace `sk-ant-api03-`; khóa đã bị dán vào hội thoại nên nên thu hồi và tạo mới (intake).

## Nợ sau G4
- README/tài liệu người dùng: guide `:797` đã khớp hành vi mới, không cần sửa.
- CHANGELOG: đã thêm dòng `Fixed` (BUG-001) dưới `[Unreleased]`.
- FEAT-001 `design.md` §3.4.3 hàng 6: ghi thêm tiền tố mới (xem kết quả cuối tệp này).
- minor hoãn từ review-01: ca 422 + `CREDIT_PREFIX`; đã được `test_400_quota_prefix_only_applies_to_400` phủ, không cần xử lý.
