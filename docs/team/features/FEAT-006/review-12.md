Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 12 — FEAT-006 T12

- Diff: `git diff 449e2b5..1db4533` (nhánh `team/FEAT-006-task-12-rework1` trên `team/FEAT-006-task-12`; merge `1f0b3f7`)
- Vòng: 2 (vòng 1 request-changes, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1 (blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-8 | test_install.py:337 (install.py:214-215) | bảo vệ "Task chưa cài" của `_ensure_task_ticket_field` bị che bởi setUp (đã tạo `Task-ai_ticket`) | xóa Custom Field trước `ensure_setup`, kiểm vẫn vắng | ADDRESSED |
| major | STD-TEST-8 | test_install.py:228 (install.py:241-245) | không có dòng mồi cho bộ lọc `share` "đúng dòng" | 3 dòng mồi (if_owner 0; permlevel 1; role khác) giữ share=0; `_other_task_perms` chọn `share` | ADDRESSED |
| major | STD-TEST-6 | test_install.py:239 | nghi meta Task cũ nằm lại trong cache redis sau rollback | `addCleanup(frappe.clear_cache, doctype="Task")` | ADDRESSED (reviewer rút lại phần nghi rò: Frappe 15.126.1 `clear_doctype_cache` đã đăng ký `after_rollback`; cleanup thừa nhưng vô hại) |

## Deferred
- minor: comment test_install.py:231 nói rollback không xóa meta redis, sai (xóa qua `after_rollback`, cache_manager.py:133): sửa lời hoặc bỏ cleanup.
- Không có decoy cho khóa `parent` (dòng ROLE_AGENT, permlevel 0, if_owner 1 trên DocType khác): bỏ `parent` khỏi bộ lọc install.py:241 vẫn xanh.
- Câu hỏi mở từ reviewer: khi System Manager xóa `routing_rules` trên form desk, Frappe lưu `""` hay NULL? Nếu NULL thì migrate kế tiếp ghi lại mặc định, ngược với phương án (a) ở review-11. Cần thử bằng một lần lưu form trên site.
- `search_index` DDL thật của `ai_ticket` bị vá `updatedb` trong test; đã kiểm bằng `cmd.migrate` ở C2 (xem dưới).

## Bằng chứng chạy (dev)
- RED: 7 test mới đỏ đúng lý do (ví dụ `(1, 1, 1, 0) != (1, 1, 1, 1)`, `unexpectedly None`); vòng 2: bỏ bảo vệ Task, bỏ `if_owner`, bỏ `permlevel` đều đỏ rồi hoàn tác.
- `test_install` 32 OK; `cmd.test` trên đầu nhánh task 1db4533: Ran 738 tests, OK; lint pass.
- Sau merge: `git diff --stat 1db4533 HEAD -- . ':!docs'` rỗng; `git diff --name-only 449e2b5..1db4533` chỉ gồm 2 file touchpoint.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
