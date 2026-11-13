# dev-R1: phân loại bị cắt (rework 1, mục 1 acceptance.md, FEAT-006)

Nhánh `team/FEAT-006-rw1-r1` (từ `team/FEAT-006` df8de66).

## Nguyên nhân gốc

claude-haiku-5-5 chạy adaptive thinking MẶC ĐỊNH khi request không có tham số `thinking` (tra skill claude-api: Haiku 5.5 "runs adaptive (on by default)", effort mặc định `medium`; `budget_tokens` bị 400; `{"type":"disabled"}` được chấp nhận ở effort `high` trở xuống). Block `thinking` có văn bản bị ẩn (display mặc định `omitted`, độ dài 0) nhưng VẪN tính vào `usage.output_tokens` và ăn `max_tokens`. Gateway không gửi `thinking` nên thinking luôn bật. Nâng trần chỉ che triệu chứng.

## Phản hồi thật (site miyano, gateway.call_model("classify"), max_tokens=600)

| cấu hình | stop_reason | output_tokens (6 lần/2 phiếu) | khối |
|---|---|---|---|
| mặc định (thinking bật) | end_turn x5, max_tokens x1 | 455, 552, 544, 600(cắt), 452... | thinking(0 ký tự) + text 437-481 ký tự |
| effort=low | end_turn | 431-510 | thinking + text (effort không tắt thinking) |
| thinking disabled | end_turn x4 | 238-268 | chỉ text |

JSON thật chỉ ~250 token; thinking ẩn thêm ~200-300 token, nên trần 600 bị chạm ngẫu nhiên (cắt giữa `"bo_ph`).

## Sửa

`erp_ai/gateway/__init__.py`: hằng `CLASSIFY_THINKING = {"type": "disabled"}`, gắn vào request khi `task == "classify"`. Task `reason` không đổi. `CLASSIFY_MAX_TOKENS` giữ 600 (dùng ~270, dư hơn 2 lần) nên test runner/handlers/run_eval khẳng định 600 không phải sửa. Eval dùng chung gateway nên được sửa theo.

## Đỏ / xanh

Test mới trong `erp_ai/gateway/test_gateway.py`: `test_classify_request_turns_thinking_off`, `test_reason_request_leaves_thinking_unset`. Test cũ `test_success_builds_result_and_records_success` khẳng định nguyên request classify nên thêm `"thinking": {"type": "disabled"}` (hành vi đổi có chủ đích, STD-TEST-5).

ĐỎ: `KeyError: 'thinking'` tại `request["thinking"]` (thiếu hành vi), Ran 63, errors=1.
XANH: `erp_ai.gateway.test_gateway` Ran 63 / OK. Toàn app `bench --site miyano run-tests --app erp_ai`: Ran 882 / OK. `pre-commit run --files` hai file: sạch (ruff lint/format Passed).

## E1/E2

E1 export: 2 dòng. E2 run_eval (2 phiếu thật, chạy 2 lần):
```
Overall accuracy: 100.0% (2/2)
Unclassified (counted wrong): 0
Classify output tokens max: 274
Classify max_tokens hits: 0
```
(Nhãn là nhãn nhẹ của 2 phiếu hiện có; số cần chú ý là hits=0 và Unclassified=0.)

## Mã nền FEAT-003 (d425faa, trần 400)

CÓ cùng lỗi. d425faa/erp_ai/agent/runner.py:208 gọi classify với max_tokens=400 và gateway (d425faa) không gửi `thinking`. Nhật ký ERP AI Log của site: 4/5 dòng classify gần nhất có `output_tokens=400` đúng bằng trần, `stop_reason=unparseable` (model claude-haiku-5-5); chỉ 1 dòng end_turn (319 token). Cùng cơ chế: thinking ẩn ăn trần, JSON bị cắt, không parse được. FEAT-003 đã phát hành mang lỗi này; bản sửa này (gateway) áp dụng cho nó nếu backport.

## Lưu ý (concern)

`thinking: disabled` bị 400 trên Sonnet 5.5 / Opus 5.5 / Fable. Nếu người vận hành đặt `model_classify` của một khóa sang các model đó, classify sẽ 400 (`bad_request`). Mặc định và hiện tại là Haiku 5.5 nên ổn; nên ghi chú vào tài liệu cấu hình hoặc xử lý ở bước khác.
