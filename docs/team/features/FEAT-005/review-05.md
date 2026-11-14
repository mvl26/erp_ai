Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — FEAT-005 T5

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 9add0dc..f8c6bbd` (nhánh `team/FEAT-005-task-5`, 1 commit, `erp_ai/agent/runner.py` + `erp_ai/agent/test_agent_runner.py` +242/−24; CHƯA merge)
- Vòng: 1
- Verdict: design-defect (vòng 1) — T5 dừng, chờ team-leader/designer

## Vòng 1 — design-defect (`9add0dc..f8c6bbd`)

Lớp 1 (khớp spec): Returns và Expect của T5 đạt đúng chữ; chỉ hai file touchpoint đổi. Test không nông: phép kiểm thứ tự sự kiện, việc đổi tên Note ở lượt 1, trạng thái khóa và Error Log đều sẽ đỏ nếu savepoint đặt trước lời gọi model, nếu hoàn tác thành rollback toàn bộ, nếu lỗi không được ném lại, hoặc nếu thêm `release`.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-7 | erp_ai/agent/runner.py:697 (cùng :637 và run_log.py:59-60) | design-amd2 §4.1/§D-1 nói chỉ DDL mới commit giữa lượt. Sai: ở production, `write_entry` của tool `propose_*` commit giữa lượt, và commit đó làm mất savepoint `erp_ai_reason_turn`. Ví dụ một lượt: `api_update_record` thêm role, rồi `propose_file_change`, rồi `write_entry` của chính lượt đó lỗi → role đã commit mà không có dòng `reason`, trái NFR-3. Hai nhóm tool có thể được cấp cùng lúc (setUp của T5 dùng L3 + `code_change_enabled=1`). Trước khi T6 xong, `rollback to savepoint` hỏng còn thay lớp lỗi gốc trong Error Log. Test không thấy vì không bao giờ commit (`in_test`) | designer xử lý đường này ở §4.1/ADR-024 QĐ 5. Phương án: không commit dòng propose giữa lượt; đặt savepoint mới sau nó (chấp nhận khe hở); hoặc chấp nhận và ghi rõ. Sau đó sửa chú thích ở runner.py:635-636 | confirmed (đọc mã; chưa chạy đường commit) |

minor | — | — | 1 điểm nhỏ: lỗi giả trong test được ném sau lệnh insert thật của `write_entry`, điểm mà production không tới được nếu chưa commit; test vẫn ghim việc hoàn tác dòng | tùy dev

## Review checklist (10)

1. đạt · 2. đạt · 3. đạt (RED 4/4 rồi GREEN, không dấu skip) · 4. đạt · 5. TRƯỢT (STD-ERR-7, khe hở thiết kế ở trên) · 6. đạt · 7. đạt · 8. đạt · 9. đạt · 10. đạt

Bằng chứng của dev: RED `Ran 4 tests` / `FAILED (failures=4)`, `['Blogger', 'Knowledge Base Contributor'] != ['Blogger']`; GREEN `Ran 4 tests` / `OK`; cả module `Ran 91 tests` / `FAILED (failures=3)` (ba ca nhiễu cài đặt của dòng `baseline:`).

## Tech-lead đã kiểm

- `erp_ai/agent/run_log.py:59-60`: `if not frappe.flags.in_test: frappe.db.commit()` nằm trong `write_entry`; `git grep -n "write_entry(" team/FEAT-004` cho thấy `erp_ai/agent/changes/transitions.py:121` gọi `write_entry` ngoài runner (đường của dòng `change`). Phát hiện đứng vững ở mức đọc mã.
- Theo skill build bước 9: `design-defect` → dừng T5 (T6 và T15 phụ thuộc T5 cũng dừng), báo team-leader; tech-lead không thiết kế lại.

## Không kiểm được từ diff

- Gộp `team/FEAT-004` @ `ba89ab3`: dòng `actions=_bounded_actions(actions) if actions else None` (runner.py:659 của `ba89ab3`) nằm trong khối T5 thụt lề lại → sẽ xung đột chữ khi merge nhánh T5; lời gọi đó phải ở trong `try` để lỗi ở đó cũng được hoàn tác. Khi cột đã có trần, ca "tràn 64 KB → hoàn tác" của design gần như hết ý nghĩa.
- Callback sống qua hoàn tác: `frappe.db.rollback(save_point=…)` không xóa `before_commit`/`after_commit`; callback xếp trong lượt bị hoàn tác vẫn chạy ở commit sau. `ROUTE_SAVEPOINT` đã có cùng điểm hở. Designer/tech-lead cần xét tool nào đăng ký việc chạy sau commit.
- Ba ca `TestRunnerL1Classification` đỏ: nhiễu cài đặt đã biết, reviewer không kiểm lại. Reviewer không chạy test (không worktree nào giữ nhánh task).

## deferred

Chưa có.
