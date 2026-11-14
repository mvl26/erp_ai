Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 67 — FEAT-004 T67

- Diff: `team/FEAT-004-task-67` (head 27d5e02), dải `a617cd5..team/FEAT-004-task-67`, 1 commit, 3 file (+217/-2)
- Vòng: 1
- Verdict: approve

Lệnh git đã dùng (chỉ đọc):
- `git log --oneline a617cd5..team/FEAT-004-task-67`
- `git diff --stat a617cd5..team/FEAT-004-task-67`
- `git diff a617cd5..team/FEAT-004-task-67`
- `git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T67'`
- `git show -s --format='%an%n%B' 27d5e02`; `git show 27d5e02:erp_ai/agent/agent_write_guard.py`
- `git show team/FEAT-004:docs/team/adr/ADR-023.md | grep ...` (QĐ 5, Ràng buộc "Test M5", luật cờ)
- `git grep` trên 27d5e02: nơi ghi `PROPOSAL_DOCTYPE`, nơi dùng `AGENT_WRITE_FLAG`/`allow_agent_write`, `is_submittable` của DocType

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major. | — |

minor | — | — | 1 điểm nhỏ: `test_propose_change.py:855` viết cứng tên bảng `` `tabERP AI Change Proposal` `` thay vì dựng từ `PROPOSAL_DOCTYPE` (STD-DESIGN-4) | tùy dev

## Layer 1 — khớp spec
- Returns của T67: controller gọi `refuse_agent_write(self)` ở `before_insert` trước `prepare_new` (`erp_ai_change_proposal.py:49`), `on_trash` (:57), `before_rename(old, new, merge)` (:59-60), `validate` (:63); `_insert` bọc đúng một lần `proposal.insert()` trong `allow_agent_write()` (`propose_change.py:136-137`), `_comment` nằm ngoài khối. Đủ.
- Expect: bốn test được nêu đều có (`:883`, `:911`, `:929`, `:945`); thêm `:871` (từng hook), `:878` (thứ tự trước `prepare_new`), `:968` (cờ tắt khi tool ném lỗi) — là test, không phải phạm vi mã thừa.
- Ràng buộc "Test M5" (phần đề xuất): insert/save/delete trực tiếp, rename, `frappe.client.insert` với chuỗi JSON có `C`, `savedocs` → bị từ chối và bảng đề xuất không đổi (`assert_refused` so `select *` trước/sau); ba tool đề xuất vẫn tạo được dưới tài khoản agent; người có role Instructor duyệt/từ chối/hoàn tác vẫn được. Phần `run_log.write_entry` và các DocType khác thuộc task khác.
- Luật cờ: `git grep` tên cờ ngoài test chỉ thấy `agent_write_guard.py` (T65) và `propose_change.py:13,136`. Đạt.
- DocType không submittable (JSON không có `is_submittable`), nên submit/cancel của QĐ 5 không áp dụng cho đề xuất.
- Touchpoints: đúng 3 file đã liệt kê.

## Test trước mã (có hỏng khi bỏ hành vi không?)
- Mọi kiểm từ chối đều ghim cả kiểu `frappe.PermissionError` lẫn câu `REFUSAL`, nên lỗi khác (kiểm role, validate trạng thái) không làm test xanh giả.
- Bỏ guard ở `before_insert`: `:871` và `:878` đỏ (đường insert vẫn bị `validate` chặn, nhưng hai test này ghim riêng hook và thứ tự). Bỏ `validate`/`on_trash`/`before_rename`: `:871` đỏ theo subTest, cộng đường "direct save"/"direct delete"/"rename" ở `:883`. Dev dán đỏ của riêng `before_rename`.
- Bỏ `allow_agent_write` ở `_insert`: `:911` đỏ cả ba tool. Bọc rộng sang `_comment`: `:945` đỏ (`[None]` → `[True]`), khớp RED đã dán `Tuples differ: ([None], [None]) != ([True], [None])`.
- RED `FAILED (failures=12, errors=1)` và GREEN của 5 module có trong gói review.

## Review checklist (10)
1. Đúng và đủ tiêu chí, không thừa — đạt (STD-DESIGN-5, STD-TEST-2).
2. Trong touchpoints, không file mới — đạt (STD-DESIGN-1, STD-STRUCT-1).
3. Có RED trước; có đường lỗi (tool ném lỗi, sáu đường ghi trái phép); không skip/xfail — đạt (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Không sửa assertion cũ; test độc lập: `commit` bị chặn, rollback + savepoint mỗi đường, `frappe.enqueue` bị patch, cờ được pop ở setUp/cleanup — đạt (STD-TEST-5, STD-TEST-6). Test phụ thuộc user `AGENT_USER` có sẵn trên site nhưng báo lỗi rõ khi thiếu (`:809`).
5. Lỗi: guard ném `PermissionError`, không nuốt lỗi; `allow_agent_write` khôi phục cờ trong `finally` (T65) — đạt (STD-ERR-1).
6. Phân quyền phía server theo danh tính phiên, cờ chỉ ở `frappe.flags` (client không giả được) — đạt (STD-SEC-4). Không secret.
7. Hợp đồng: chữ ký `before_rename(old, new, merge)` khớp cách `rename_doc` gọi; người có role không đổi hành vi (`:929`) — đạt (STD-DESIGN-3).
8. Tên, cấu trúc, docstring đúng với mã (docstring controller và comment ở `propose_change.py:135` khớp hành vi) — đạt; một minor ở trên (STD-STYLE-4, STD-STYLE-5).
9. Không phụ thuộc mới — đạt (STD-DEP-1).
10. Commit `feat(agent): ... (FEAT-004)`, không trailer AI, nhánh `team/FEAT-004-task-67` — đạt (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-GIT-8). Không có thay đổi hành vi người dùng cần cập nhật tài liệu (STD-DOC-2).

## Không kiểm được từ diff
- Cờ của T65 là cờ chung cho mọi DocType có guard: trong khối `allow_agent_write()` quanh `proposal.insert()`, mọi ghi lồng nhau của tài khoản agent vào DocType khác của app (kể cả ERP AI Setting/Credential, vốn QĐ 5 nói "không có đường hợp lệ") cũng được mở. Đã grep: không thấy nơi ghi đề xuất nào khác qua controller; chưa đọc `transitions.prepare_new` và doc_events của app khác để chắc không có ghi lồng → tech-lead xác nhận, hoặc đưa vào câu hỏi cho architect về phạm vi cờ (theo DocType hay chung).
- `approve`/`reject`/`undo` ghi trạng thái bằng `frappe.db.set_value` (`transitions.py:168,275`), không qua controller, nên M5 không phải lớp bảo vệ của AC-33 trên đường này; AC-33 dựa vào kiểm role trong các hàm whitelist (test ở task trước, ngoài diff). ADR-023 QĐ 5 đã ghi nhận giới hạn kiểu `db.set_value`.
- Job áp dụng/hoàn tác chạy dưới user của người bấm duyệt (enqueue giữ session user) — suy từ Frappe, không thấy trong diff; nếu job nào được xếp dưới tài khoản agent mà ghi đề xuất qua `save`, guard sẽ chặn nó.
- Không chạy test (site dùng chung); GREEN chỉ là bằng chứng do dev dán. Gợi ý: `cmd.test_one erp_ai/agent/tools/test_propose_change.py` và `.../erp_ai_change_proposal/test_erp_ai_change_proposal.py`.

## Deferred
- Không có.
