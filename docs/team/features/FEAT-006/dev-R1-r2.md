# dev-R1-r2: rework 1 vong 2, R1 (FEAT-006)

Nhánh `team/FEAT-006-rw1-r1b` (từ 85c31cd).

## Finding -> thay đổi -> test phủ

major | STD-DESIGN-3 | gateway/__init__.py:152-153 | classify luôn gửi `thinking: disabled`; Sonnet/Opus/Fable trả 400 với giá trị này, gateway bỏ cuộc `bad_request` không thử key khác.

- Thay đổi (`erp_ai/gateway/__init__.py`): thêm hằng `THINKING_OFF_MODEL_PREFIX = "claude-haiku-"`; chỉ gắn `thinking` khi `task == "classify"` VÀ `model.startswith(THINKING_OFF_MODEL_PREFIX)`. Model khác (và task reason) không có trường `thinking`.
- Test (`erp_ai/gateway/test_gateway.py`):
  - `test_classify_request_turns_thinking_off_for_haiku` (test Haiku cũ, nay đặt `model_classify="claude-haiku-5-5"`).
  - `test_classify_request_leaves_thinking_unset_for_non_haiku` (mới, `claude-sonnet-5-5`).
  - `test_success_builds_result_and_records_success`: model `default-model` không phải Haiku nên bỏ `thinking` khỏi request kỳ vọng (hành vi đổi có chủ đích, STD-TEST-5).
  - `test_reason_request_leaves_thinking_unset` giữ nguyên.

## ĐỎ (hành vi thiếu)

Ghi chú: `bench` nạp app từ checkout chính (editable .pth), nên chạy với `PYTHONPATH=<worktree>` để test đúng mã trong worktree này.

```
FAIL: test_classify_request_leaves_thinking_unset_for_non_haiku
AssertionError: 'thinking' unexpectedly found in {'model': 'claude-sonnet-5-5', ..., 'thinking': {'type': 'disabled'}}
FAIL: test_success_builds_result_and_records_success  (request thừa 'thinking')
Ran 64 tests ... FAILED (failures=2)
```

## XANH

- `erp_ai.gateway.test_gateway`: Ran 64 / OK.
- `bench --site miyano run-tests --app erp_ai`: Ran 883 / OK.
- `pre-commit run --files erp_ai/gateway/__init__.py erp_ai/gateway/test_gateway.py`: tất cả Passed (ruff lint, import sorter, format).

## E2 chạy lại (scratch: .../scratchpad/e2/in.jsonl, 2 phiếu tổng hợp không nhãn, site model Haiku 5.5, 2 lần)

```
Classify output tokens max: 268   Classify max_tokens hits: 0   Unclassified: 0
Classify output tokens max: 282   Classify max_tokens hits: 0   Unclassified: 0
```
(Không nhãn nên độ chính xác không áp dụng; chỉ kiểm hits = 0.)

## Seen but not touched

`model_classify` mô tả trường (erp_ai_credential.json:61, erp_ai_setting.json:148) chưa nói rằng chỉ Haiku được tắt thinking; ngoài touchpoints.
