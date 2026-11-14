Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 65 — FEAT-004 T65

- Diff: `team/FEAT-004-task-65` (head 02493b3), range `7c2a3af..team/FEAT-004-task-65`, 1 commit, 4 file (+286/-1)
- Vòng: 1
- Verdict: approve

Lệnh đã dùng (chỉ đọc):
```
git log --oneline 7c2a3af..team/FEAT-004-task-65
git diff --stat 7c2a3af..team/FEAT-004-task-65
git diff 7c2a3af..team/FEAT-004-task-65
git log --format='%H%n%B' -1 team/FEAT-004-task-65
git ls-tree --name-only team/FEAT-004-task-65 erp_ai/erp_ai_agent/doctype/
git show team/FEAT-004-task-65:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | grep '"Table'
git grep -n -E "(get_single|get_doc|get_cached_doc)\((SETTING_DOCTYPE|...)" team/FEAT-004-task-65 -- 'erp_ai/*.py'
git grep -n -E "\.save\(|\.insert\(|delete_doc\(" team/FEAT-004-task-65 -- 'erp_ai/*.py'
grep -n -E "def (insert|save|...)|ignore_validate|run_method(...)" frappe/model/document.py   (+ đọc dòng 1280-1292)
```

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major. | — |

minor | — | — | 2 điểm nhỏ: (1) STD-TEST-6 `erp_ai/agent/test_agent_write_guard.py:201-216` — `test_human_system_manager_still_saves_setting` chạy toàn bộ `ERPAISetting.validate` trên cấu hình đang sống của site (`check_enabled_requirements`, `check_labels`…), không gieo trạng thái; site có cấu hình không hợp lệ thì test đỏ vì lý do khác (suspected, cùng dạng BUG-002 cách ly dữ liệu sống); (2) STD-STYLE-4 `erp_ai/agent/agent_write_guard.py:32` — thông điệp `frappe.throw` không bọc `_()` (chỉ là minor nếu các controller khác của app đều dịch) | tùy dev

## Layer 1 — khớp spec
- AC-33 / ADR-023 QĐ 5 / Ràng buộc "Test M5" (phần Setting, Credential): đạt. `AGENT_WRITE_FLAG`, `allow_agent_write()` (khôi phục giá trị cũ trong `finally`), `refuse_agent_write(doc)` đúng chữ ký của task; cờ đọc từ `frappe.flags`, không từ `doc.flags` hay trường doc; hai controller gọi `refuse_agent_write(self)` ở đúng 6 hook, không controller nào gọi `allow_agent_write`.
- Bốn test Expect của task đều có, cộng một test cho từng hook (12 trường hợp).
- Luật cờ của ADR-023: tên cờ chỉ xuất hiện trong module bộ chặn và test; chưa ai ngoài phạm vi gọi `allow_agent_write` (T66/T67 sẽ là `run_log.py`, `propose_change.py`).
- Rủi ro "runner lưu ERP AI Setting dưới tài khoản agent" (task: → `NEEDS_CONTEXT`): đã kiểm bằng `git grep` — `runner.py:135` và `alerts.py:7` chỉ đọc `get_single`, không `.save()`; `tasks.py:29` ghi thẳng DB, không qua controller. Không có đường ghi hợp lệ nào bị gãy.
- Setting chỉ có một bảng con (`credentials` → ERP AI Credential), nên không còn bảng con nào của Setting lưu thẳng mà lọt bộ chặn. ERP AI Log, ERP AI Change Proposal là T66/T67.
- Mục Trọng tâm review 1 của plan (dict client mang khóa `flags`): có test `client.save setting` với `{"flags": {AGENT_WRITE_FLAG: True}, AGENT_WRITE_FLAG: 1}` và `doc.flags`/trường doc đặt trực tiếp → vẫn bị từ chối. Đột biến "đọc thêm `doc.flags` hoặc `doc.get(FLAG)`" bị subtest `doc.flags and field` bắt.
- Không thừa: chỉ 4 file đúng touchpoint.

## Review checklist (10)
1. Đúng và đủ spec, không thừa (STD-DESIGN-5, STD-TEST-2): đạt.
2. Trong touchpoint; file mới `erp_ai/agent/` đúng chỗ, test colocated (STD-DESIGN-1, STD-STRUCT-1, STD-STRUCT-2): đạt.
3. Test đỏ trước (RED: `PermissionError not raised` cho 12 hook và từng đường, `None is not True` cho cờ); có đường lỗi (finally khi lỗi, lồng cờ "outer"), có đường người hợp lệ; không skip/xfail (STD-TEST-1, STD-TEST-8, STD-TEST-4): đạt. Test có thể đỏ khi gỡ hành vi: regex `REFUSAL` tách lỗi của bộ chặn khỏi `PermissionError` của Frappe, và setUp cấp `System Manager` cho agent nên quyền Frappe không che bộ chặn.
4. Không sửa test cũ; độc lập: savepoint + rollback mỗi đường, cleanup LIFO, cache role xóa (STD-TEST-5, STD-TEST-6): đạt (minor (1) ở trên).
5. Lỗi: `frappe.throw(..., PermissionError)`, context manager khôi phục trong `finally`; không gọi ngoài (STD-ERR-1, STD-ERR-2, STD-ERR-5): đạt.
6. Phân quyền phía server theo danh tính phiên; không bí mật, SQL trong test có tham số (STD-SEC-1, STD-SEC-3, STD-SEC-4, STD-SEC-6): đạt.
7. Hợp đồng: không đổi API công khai; không migration (STD-DESIGN-3, STD-OPS-2): đạt.
8. Tên, cấu trúc, style; không code chết (STD-NAME-1, STD-NAME-2, STD-STYLE-4, STD-STYLE-5): đạt (minor (2)).
9. Không thêm phụ thuộc (STD-DEP-1, STD-DEP-3, STD-DEP-5): đạt.
10. Commit `feat(agent): … (FEAT-004)`, nhánh `team/FEAT-004-task-65`, không trailer AI; không cần sửa tài liệu người dùng (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-GIT-8, STD-DOC-2): đạt.

## Không kiểm được từ diff
- Lỗ theo cờ phía server (thiết kế, không phải lỗi dev): `frappe/model/document.py:1284-1290` chạy `before_validate` rồi `return` khi `doc.flags.ignore_validate`, nên `validate` (chỗ đặt bộ chặn trên đường save) bị bỏ qua; tương tự `frappe.delete_doc(..., ignore_on_trash=True)` bỏ `on_trash`. Client không đặt được `doc.flags` (khóa `flags` bị bỏ khi dựng doc — chưa đọc `base_document.py` vì giới hạn grep), nên chỉ mã server chạy dưới phiên agent mới mở được; cùng lớp rủi ro ADR-023 QĐ 6 (b) đã chấp nhận. Gợi ý cho tech-lead/designer: thêm `before_validate` (chạy trước kiểm `ignore_validate`) vào danh sách hook của T65 nếu muốn đóng cả đường này — một dòng mỗi controller.
- `frappe.delete_doc` của Single có chạy `on_trash` trước khi xóa `tabSingles` hay không nằm ở `frappe/model/delete_doc.py` (ngoài phạm vi grep); bằng chứng duy nhất là RED/GREEN của subtest `setting delete`.
- Test chưa chạy bởi reviewer (site dùng chung). Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.test_agent_write_guard`; tech-lead chạy `cmd.test` đầy đủ sau merge (đường lưu Setting của các test khác dưới tài khoản agent, nếu có, sẽ đỏ ở đó).

## Deferred
- Không có.
