# Review T127 — `policy`: tiêu đề có tiền tố loại trừ

## Vòng 1 (2026-11-15, lượt build 20) — `request-changes`

- Lệnh diff: `git diff 501c104..8809b49` (BASE = `git merge-base team/FEAT-007 team/FEAT-007-task-127` = `501c104`; đầu nhánh task `8809b49`; commit `d55944c` test, `8809b49` mã); 2 file, +65, đều trong touchpoint.
- Review checklist (10): 10/10. Lớp 1: mọi mục Returns và Expect đã dựng; một vế Returns chưa có test đỏ khi thiếu nó.
- Đã kiểm: phạm vi chỉ các hằng và hàm của task (`SUBJECT_FIELD` thêm mà chưa dùng, đúng Returns; `git grep` không thấy nơi gọi mới); thân `ticket_link_fieldnames` (`policy.py:326`), `is_ticket_content_doctype` (`:339`) không nằm trong diff; đủ mọi biên của Expect, thêm `""` và `None`; STD-TEST-6 đạt (`keep_agent_settings`, `addCleanup(rollback)`, chặn commit); "không ném" đúng với trường thiếu (`get_single_value` của Frappe 15 ném `ValidationError`; DocType thiếu ném `DoesNotExistError` là lớp con; single rỗng trả None → `()`), M4 ghim phép bắt; không phụ thuộc mới; hai commit đúng dạng, không trailer AI.

### Findings

- major | STD-TEST-2 | erp_ai/agent/test_policy.py:910 | Dữ liệu cấu hình gieo là `f"[HR]\n\n   \n{ke_toan_nfc}\n"`: các dòng chỉ ở dạng NFC, một dấu cách, không đệm quanh dòng khác rỗng. Nếu `excluded_title_prefixes` dùng `map(_normalize, …)` hoặc `line.strip().casefold()` thay cho `map(_title_key, …)` (policy.py:75) thì test vẫn xanh. Luật thiết kế "mỗi dòng → `_title_key(line)`" (U2.md:126) vì thế chưa được kiểm. Bước NFC và gộp dấu cách chỉ được chạy ở phía tiêu đề, và M2 bỏ NFC ở cả hai phía cùng lúc. Thực tế: admin gõ tiền tố ở dạng NFD (một số bộ gõ tiếng Việt, macOS) sẽ lặng lẽ không có luật. | Thêm một dòng cấu hình dạng NFD có dấu cách thừa, ví dụ `"  " + unicodedata.normalize("NFD", "[Kế   toán]") + " "`. Khẳng định tuple có khóa NFC `"[kế toán]"` và `f"{ke_toan_nfc}X"` bị loại chỉ nhờ dòng đó. | confirmed (reviewer suy đột biến: casefold của U+1EBE cho đúng một điểm mã U+1EBF nên dòng NFC vẫn là NFC khi thiếu bước NFC)
- minor | — | — | 1 điểm: policy.py:73. Trong `get_single_value`, `frappe.throw` của trường thiếu gọi `msgprint` (frappe/__init__.py:491-580), thêm "Field … does not exist on ERP AI Setting" vào `message_log` trước khi ném; bắt ngoại lệ không gỡ thông báo đó, nên trước migrate một request web có thể hiện nó trong hộp đỏ (STD-ERR-3). Test patch `get_single_value` nên không thấy. Lối sửa có thể: kiểm `frappe.get_meta(SETTING_DOCTYPE).has_field(...)` thay cho try/except. | dev's call

### Ngoài phạm vi

Không có.

### Không kiểm được từ diff

- `frappe.db.set_single_value` có xóa `value_cache` để lần đọc thứ hai ở `test_policy.py:918` thấy giá trị mới hay không: dòng GREEN của dev ngụ ý có; chạy lại `test_policy` dưới khóa site quyết định.
- Đầu ra GREEN và đột biến lấy từ lời giao; reviewer không chạy.

### Bằng chứng của dev (nguyên văn, kèm trong lời giao review)

- RED trên `d55944c`: `ERROR: test_prefix_boundaries`, `AttributeError: module 'erp_ai.agent.policy' has no attribute 'EXCLUDED_TITLE_PREFIXES_FIELD'`, `Ran 58 tests in 6.407s` / `FAILED (errors=1)`.
- GREEN trên `8809b49`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_policy `Ran 58 tests in 5.326s` OK; test_architecture `Ran 187 tests in 29.202s` OK. `pre-commit run --all-files`: `LINT_EXIT=0`.
- Đột biến (không commit): M1 `prefix in title` → `AssertionError: True is not false`, `Ran 58 tests in 6.456s` / `FAILED (failures=1)`; M2 bỏ NFC → `AssertionError: False is not true`, `Ran 58 tests in 5.053s` / `FAILED (failures=1)`; M3 không bỏ dòng rỗng → `Tuples differ: ('[hr]', '', '', '[kế toán]') != ('[hr]', '[kế toán]')`, `Ran 58 tests in 4.954s` / `FAILED (failures=1)`; M4 `except ZeroDivisionError` → `frappe.exceptions.ValidationError: Field excluded_title_prefixes does not exist on ERP AI Setting`, `Ran 58 tests in 5.311s` / `FAILED (errors=1)`.
