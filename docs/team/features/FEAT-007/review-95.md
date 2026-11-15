# Review T95 — Tập trường người gõ lúc tạo phiếu được lưu vào `ai_created_labels`

## Vòng 1 (2026-11-15, lượt build 20) — `approve`

- Lệnh diff: `git diff 501c104..d968c52` (BASE = `git merge-base team/FEAT-007 team/FEAT-007-task-95` = `501c104`; đầu nhánh task `d968c52`; commit `a9c429d` test, `61821a2` mã, `d968c52` test); 2 file, +186: `erp_ai/handlers.py` +26, `erp_ai/tests/test_handlers.py` +160, đều trong touchpoint.
- Số vòng: 1. Review checklist (10): 10/10, không blocker, không major.
- Lớp 1 (spec): mọi vế Returns có trong diff và khớp Fix 1 dòng 64-67 (hai hằng; cờ lấy ở `before_insert`, trường không ghi ở đó; `ticket_validate` kiểm `has_field` rồi ghi/giữ ở các dòng đầu; `kept` chỉ giữ giá trị người gõ mà phiếu còn mang; không còn gì thì `""`, giá trị client luôn bị ghi đè). Không có gì của T96 lọt vào (nhánh bỏ qua `no_prediction` không đổi). Đủ 6 test của Expect.
- Test trước mã: mỗi vế Returns có test đỏ khi thiếu nó (`before_insert` không ghi trường; giá trị client bị ghi đè; "chỉ giá trị còn trên phiếu": subtest 2 đỏ, subtest 1 xanh trên mã cũ nhưng giết đột biến `kept = typed` nên không bị che; giữ cố định dưới Administrator và `AGENT_USER`; không `save()`/`db.set_value`: cả hai được patch trên đối tượng thật với `assert_not_called`). STD-TEST-6: `HandlerTestCase` đăng ký rollback, `set_user("Administrator")` và chặn commit; ca khách hàng tự gieo dòng template.
- STD-TEST-5 (đổi fixture ở `d968c52`): khẳng định giống từng byte; đổi là cần vì `priority`, `ticket_type`, `agent_group` ở permlevel 7 của HD Ticket (`hd_ticket.json:117,129,137`), patch `[0]` của thiết kế làm Frappe xóa giá trị người gõ trước `validate`; `[0, 7]` chỉ giữ lại mức 8, đúng ý Fix 1; lý do có trong thân commit.

### Findings

Không có blocker, major.

`minor | — | — | 2 điểm nhỏ: (a) STD-TEST-8: chốt doc.meta.has_field(CREATED_LABELS_FIELD) (handlers.py:83) và chốt "before and" (handlers.py:78) chưa có test ở nhánh sai (bỏ đi gần như vô hại hôm nay vì get_valid_dict bỏ trường lạ); (b) chữ thiết kế lệch: Fix 1 dòng 77 và R2 dòng 376 nói patch [0], test dùng [0, 7] | (a) dev's call; (b) tech-lead nhờ designer đổi [0] thành [0, 7] ở Fix 1 dòng 77 và R2 dòng 376`

### Ngoài phạm vi (hoãn, không chặn)

- Tiền đề `assertNotIn(8, …get_permlevel_access("write"))` của ca khách hàng đọc DocPerm HD Customer sống của site; hỏng thì đỏ rõ, không che gì.

### Không kiểm được từ diff (tech-lead giải trước khi tick)

- Thứ tự hook trên site thật khớp Fix 1 dòng 69 (`before_insert` của app chạy sau `apply_ticket_insert_rules` của Helpdesk, không gì sau `validate` đặt lại `ai_created_labels`): lần chạy lại `erp_ai.tests.test_handlers` sau merge dưới khóa site quyết định.
- Dòng GREEN/RED của dev được nhận như đã dán; reviewer không chạy.

### Bằng chứng của dev (nguyên văn, kèm trong lời giao review)

- RED (`erp_ai/handlers.py` của `501c104` trong cây làm việc, test của `d968c52`, migrate exit 0 cùng lần giữ khóa): sáu test `TestCreatedLabels` đỏ (`test_created_labels_frozen_after_insert` `AssertionError: '' != '{"priority": "High"}'`; `test_customer_portal_insert_records_typed_fields` cùng lỗi; `test_insert_records_typed_fields_only` `AssertionError: None != 'ai_created_labels'`; `test_level8_user_client_value_overwritten`; `test_only_values_still_on_ticket_recorded` (subtest thứ hai); `test_user_without_level8_insert_records_typed_fields`), `Ran 38 tests in 14.012s` / `FAILED (failures=6)`.
- Đột biến (mã cuối, không commit): `_freeze_created_labels(doc)` → `pass`: `AssertionError: '{"priority": "Low"}' != '{"priority": "High"}'`, `Ran 38 tests in 17.768s` / `FAILED (failures=3)`; `if doc.is_new():` → `if True:`: `AssertionError: '' != '{"priority": "High"}'`, `Ran 38 tests in 16.711s` / `FAILED (failures=11)`.
- GREEN trên `d968c52`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_handlers `Ran 38 tests in 15.180s` OK; test_agent_runner `Ran 118 tests in 59.244s` OK; test_runner_routing `Ran 62 tests in 73.737s` OK; test_architecture `Ran 187 tests in 28.880s` OK. `pre-commit run --all-files`: 12 hook Passed, `LINT_EXIT=0`.
- Lịch sử: lần gọi dev đầu chạm trần 60 lượt, không có báo cáo (ba commit là của lần đó); lần gọi thứ hai chỉ kiểm commit và chạy bằng chứng, không thêm commit.

## Kết luận của tech-lead

`approve` vòng 1, ghi trước merge. Minor (a): hoãn. Minor (b) và mục ngoài phạm vi: chuyển team-leader (designer sửa chữ `[0]` → `[0, 7]`).
