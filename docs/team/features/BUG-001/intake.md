Feature: BUG-001
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake BUG-001 — Hết credit (400 "credit balance is too low") bị xếp `bad_request` thay vì `Hết hạn mức`

- Yêu cầu gốc: "sửa lỗi key api, tôi nhập key đúng (curl … --header "x-api-key: sk-ant-usr-…[đã che]" --header "anthropic-version: 2026-10-21" … "model": "claude-opus-5-5" …) nhưng nó báo lỗi 400, thiết lập hệ thống luôn để tôi test chức năng erp ai trên helpdesk"
- Nguồn: hội thoại
- Loại việc: bug
- Playbook: bug-fix
- Size: S
- Mode: decide
- Lý do chọn playbook/cỡ: Hành vi lệch guide và tái hiện được — guide `docs/HuongDan_TrienKhai_erp-ai.md:797` quy định "Hết credit / vượt spend limit → `Hết hạn mức`, dò lại mỗi giờ, báo tin", nhưng `erp_ai/gateway/breaker.py:57` chỉ nhận 400 có message bắt đầu `You have reached your specified` (design `FEAT-001/design.md` §3.4.3 hàng 6), nên 400 `Your credit balance is too low to access the Anthropic API…` rơi vào hàng 8 → `bad_request`: khóa không chuyển `Hết hạn mức`, không báo tin, không chuyển khóa dự phòng, scheduler không dò lại; sửa một nhánh của hàm thuần `decide` + test, một file mã → S.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Tái hiện (2026-11-12, site `miyano`)
- `check_keys` → `[{"label": "Chính", "ok": false, "error_kind": "bad_request", "status": 400}]`; dòng khóa vẫn `status = Hoạt động`, `error_count = 0`, `last_error = ""`.
- Gọi thẳng SDK bằng cùng khóa (`claude-haiku-5-5`, `max_tokens` 1 và 16): `400 invalid_request_error: Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing to upgrade or purchase credits.` (request_id `req_011CgxJw87AVM7k6qB2NDAAa`).

## Điều người cần biết (không phải mã)
- Khóa hợp lệ (không 401). Lỗi 400 là do **tổ chức Console sở hữu khóa hết credit**; sửa BUG-001 làm app báo đúng trạng thái `Hết hạn mức` và gửi tin, **không** làm lời gọi thành công. Muốn agent chạy được: nạp credit (Plans & Billing) hoặc dùng khóa của tổ chức còn credit.
- Khóa dạng `sk-ant-usr-` là khóa theo người; guide mục 9.1 yêu cầu khóa workspace `sk-ant-api03-`. Khóa đã bị dán vào hội thoại nhiều lần → nên thu hồi, tạo khóa mới.

## Phạm vi
- Trong: nhận diện 400 hết credit là `quota` (`Hết hạn mức`, chuyển khóa, báo tin) trong `breaker.py`; test tái hiện trước.
- Ngoài: đổi `anthropic-version`/SDK; thay đổi luồng dò lại hàng giờ (đã có `reprobe_exhausted_keys`); cấu hình site (đã làm 2026-11-12, journal FEAT-001).

## Ràng buộc của người yêu cầu
- Như FEAT-001: commit local trên `team/BUG-001` (tách từ `team/FEAT-001`, vì mã FEAT-001 chưa vào `develop`), không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật; không ghi khóa vào artifact, log hay commit.

## Đổi cỡ (nếu có)
- —
