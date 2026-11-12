# Review R1 (T19, rework 1) — approve

- Verdict: approve (vòng 2 / 2 vòng; max_rework=3).
- Diff: `git diff df8de66..team/FEAT-006-rw1-r1b -- erp_ai` (BASE df8de66; vòng 2: `git diff 85c31cd..team/FEAT-006-rw1-r1b`). Merge: 780a08d vào `team/FEAT-006`.
- Vòng 1 (`review-R1-round1.md`): request-changes, 1 major STD-DESIGN-3 (gửi `thinking: disabled` cho mọi model; Sonnet/Opus/Fable trả 400).
- Vòng 2 (re-review có phạm vi): ADDRESSED (chỉ model `claude-haiku-`; test non-Haiku không có `thinking`).
- Nguyên nhân gốc: `claude-haiku-5-5` mặc định chạy adaptive thinking khi request không có `thinking`; token thinking tính vào `max_tokens` (câu trả lời JSON ~250 token, có thinking 450-600+). Sửa: classify gửi `thinking: {"type":"disabled"}` cho model Haiku; trần 600 giữ nguyên.
- Bằng chứng: đỏ `KeyError: 'thinking'`; xanh `erp_ai.gateway.test_gateway` Ran 64 OK; dev chạy cmd.test toàn app Ran 883 OK trên 5fc7a8b (cây `erp_ai/` của đầu merge giống hệt 5fc7a8b); E2 `Classify max_tokens hits: 0`, `Unclassified: 0`, max đầu ra 268/282/274.
- FEAT-003 (d425faa, trần 400, không gửi `thinking`): CÓ cùng lỗi (nhật ký site 4/5 dòng gần nhất `output_tokens=400`, `stop_reason=unparseable`); cần backport nếu FEAT-003 còn được phát hành riêng.

## deferred
- minor STD-DOC-4: design.md D-8 còn ghi "nâng trần khi chạm max_tokens"; cần ghi quyết định mới (tắt thinking cho classify, trần 600). Mô tả trường `model_classify`/`model_classify_default` chưa nói chỉ Haiku bị tắt thinking.
- minor STD-ERR-1 `erp_ai/gateway/__init__.py:154`: nếu cả `model_classify` và `model_classify_default` rỗng thì `model` là None và `model.startswith` ném AttributeError (trước đây là `GatewayError bad_request`). Sửa: `(model or "").startswith(...)`.
- Concern: model không phải Haiku (Sonnet/Opus/Fable) không được tắt thinking, nên cùng lỗi cắt `max_tokens` có thể quay lại nếu site đặt model đó cho classify; hiện mặc định Haiku 5.5.
