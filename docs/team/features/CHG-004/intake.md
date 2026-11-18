Feature: CHG-004
Stage: intake
Author-agent: team-leader
Date: 2026-11-16
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake CHG-004 — Model mặc định là Claude Opus 5.5, thay cho Haiku

- Yêu cầu gốc: "chuyển mohình mặc định là opus 5.5 nhé, thay thế cho haku" (người dùng, 2026-11-16).
- Nguồn: hội thoại; team-leader đọc cấu hình trên site `miyano` (chỉ đọc, không đọc khóa).
- Loại việc: change-request
- Playbook: change-request
- Size: S
- Mode: decide
- Lý do chọn playbook/cỡ: một hành vi nhìn thấy được (model bot dùng), ba chỗ mã: mặc định `model_classify_default = claude-haiku-5-5` (`erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:353`), gateway chỉ tắt thinking cho `claude-haiku-*` và không gửi gì cho model khác (`erp_ai/gateway/__init__.py:154-155`), trần `CLASSIFY_MAX_TOKENS = 600` (`erp_ai/agent/runner.py:94`).
- Cách làm: người dùng đã bảo trong phiên này "ko dùng team làm luôn đi cho tôi"; team-leader tự làm trực tiếp, test trước, không gọi vai nào.
- Skill tạm: không cần
- Ngân sách: không gọi vai nào; chi phí gọi model để kiểm thử vài cent.

## Hiện trạng (đọc 2026-11-16 ~15:20)
- ERP AI Setting: `model_classify_default = claude-haiku-5-5`; đơn giá 0,1 / 0,125 / 0,01 / 0,5 USD mỗi triệu token (giá Haiku 5.5); ngân sách tháng 100 USD.
- Dòng khóa "Chính": `model_classify = claude-haiku-5-5`, `model_reason = claude-haiku-5-5`. Tức cả bước phân loại lẫn bước lập luận đang chạy Haiku.
- 7 ngày gần nhất: 59 lần lập luận (0,0603 USD), 8 lần phân loại (0,0032 USD).

## Điều Claude Opus 5.5 khác Haiku 5.5 (hướng dẫn chuyển model của Anthropic)
- Không tắt được thinking: `thinking: {"type": "disabled"}` trả 400. Điều khiển bằng `output_config.effort`; mặc định `medium`.
- Thinking tính vào `max_tokens`, nên trần 600 của bước phân loại sẽ cắt câu trả lời (đây cũng là nguyên nhân chính của BUG-004 với phiếu dài).
- Giá 4 / 20 USD mỗi triệu token vào / ra, ghi cache 5 phút 5 USD, đọc cache 0,20 USD: gấp 40 lần Haiku 5.5 theo token.
- Bộ phân loại an toàn rộng hơn (`cyber`, `bio`); khi từ chối, API trả 200 với `stop_reason = "refusal"`.

## Tiêu chí xong
1. Mặc định `model_classify_default` là `claude-opus-5-5`; mô tả hai trường model phân loại nói đúng hành vi mới.
2. Bước phân loại với model không phải `claude-haiku-*` gửi `output_config = {"effort": "low"}` và không gửi `thinking`; Haiku giữ như cũ; bước lập luận không đổi.
3. Trần token của bước phân loại đủ chỗ cho thinking và câu trả lời JSON.
4. Site `miyano`: Setting và dòng khóa "Chính" dùng `claude-opus-5-5` cho cả hai bước; đơn giá theo Opus 5.5.
5. Một lần gọi thật qua gateway cho mỗi bước xác nhận model và tham số được chấp nhận.
6. `cmd.test` các module đụng tới xanh; cả app xanh trừ phần đang làm dở của FEAT-007.

## Ngoài phạm vi
- Fallback khi model từ chối (`fallbacks` phía server): SDK `anthropic` đang cài (0.103.1) chưa có tham số này; cần nâng SDK, là việc riêng.
- Các tiêu chí còn lại của BUG-004 (giữ `stop_reason` thật, đoạn đầu câu trả lời thô trong log).
- Chỉnh effort và trần token của bước lập luận.
- Triển khai production (G5).

## Đổi cỡ (nếu có)
- Không có.
