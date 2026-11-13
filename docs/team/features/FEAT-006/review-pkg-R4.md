# Review package R4 (FEAT-006 rework 1)

BASE=8c8741d, head=7002d0f (nhánh team/FEAT-006-rw1-r4). Lệnh diff: `git diff 8c8741d..team/FEAT-006-rw1-r4 -- erp_ai`

Commits:
- 7002d0f fix(gateway): model phân loại rỗng vẫn ra GatewayError, mô tả chỉ haiku tắt thinking (FEAT-006)

Tiêu chí:
(a) `call_model` không văng AttributeError khi model_classify của khóa và model_classify_default đều rỗng/None; hành vi như trước rework (GatewayError bad_request); có test đỏ trước.
(b) description của `model_classify` (ERP AI Credential) và `model_classify_default` (ERP AI Setting) nói rõ chỉ `claude-haiku-*` được tắt thinking ở phân loại, model khác có thể bị cắt ở trần token; <= 400 ký tự; dữ liệu ghim trong tests/test_doctype_descriptions.py cập nhật.

Stat:
```
 erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json |  2 +-
 erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json       |  2 +-
 erp_ai/gateway/__init__.py                                           |  2 +-
 erp_ai/gateway/test_gateway.py                                       | 10 ++++++++++
 erp_ai/tests/test_doctype_descriptions.py                            |  4 ++--
```

Diff: chạy lệnh ở dòng đầu (5 file nguồn/test ở trên; đã đọc đủ).
