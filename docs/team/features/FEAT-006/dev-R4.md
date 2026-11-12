# dev-R4 (FEAT-006 rework 1)

Nhánh: team/FEAT-006-rw1-r4 (từ team/FEAT-006 @ 8c8741d).

## (a) AttributeError khi model rỗng
- Test mới: `test_classify_with_no_model_anywhere_raises_gateway_error_not_attribute_error` (erp_ai/gateway/test_gateway.py). Dựng: xóa hàng Singles `model_classify_default`, `model_classify` của khóa = None, `err(400)`.
- ĐỎ (đúng lý do): `AttributeError: 'NoneType' object has no attribute 'startswith'` tại gateway/__init__.py:154. Ran 65 tests, FAILED (errors=1).
- Sửa: `(model or "").startswith(THINKING_OFF_MODEL_PREFIX)`; request["model"] giữ nguyên.
- XANH: erp_ai.gateway.test_gateway -> Ran 65 tests OK. Kết quả: GatewayError kind bad_request, không có "thinking".

## (b) description
- Test ghim: thêm "claude-haiku", "trần token" cho model_classify và model_classify_default.
- ĐỎ: `{'model_classify_default': ['claude-haiku', 'trần token']}` và `{'model_classify': [...]}` thiếu cụm; Ran 10 tests FAILED (failures=2).
- Sửa 2 file JSON (221 và 222 ký tự, <= 400).
- XANH: erp_ai.tests.test_doctype_descriptions -> Ran 10 tests OK.

## Toàn app / lint
- `bench --site miyano run-tests --app erp_ai` -> Ran 885 tests in 161.130s, OK.
- pre-commit run --files (5 file): tất cả Passed/Skipped.
