Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — FEAT-005 T5

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 9add0dc..f8c6bbd` (nhánh `team/FEAT-005-task-5`, 1 commit, `erp_ai/agent/runner.py` + `erp_ai/agent/test_agent_runner.py` +242/−24; CHƯA merge)
- Diff vòng 2: `git diff f8c6bbd..a928625` (gộp `team/FEAT-005` @ `035689b` = `e7343be`, sửa `a928625`); phần riêng của task so với nhánh feature: `git diff 035689b..a928625 -- erp_ai/agent/runner.py erp_ai/agent/test_agent_runner.py`; merge vào `team/FEAT-005` = `3b306a2`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 design-defect, gỡ bằng design-amd2 "Sửa vòng 3" (D-7, D-8)

## Vòng 2 — approve (`f8c6bbd..a928625`, chấm lại có phạm vi + phạm vi mới của design-amd2 vòng 3)

- Gộp `e7343be`: sạch. Xung đột `runner.py` gỡ bằng cách giữ `_bounded_actions(actions) if actions else None` trong `try` của lượt; so với `035689b` chỉ `runner.py` và `test_agent_runner.py` đổi; file test chỉ thêm dòng, test FEAT-004 còn nguyên (`test_six_large_deletes_keep_one_bounded_log_row` `:1611`, ba test dòng `propose` `:1296`, `:2721`, `:2782`).
- major STD-ERR-7 `runner.py:697`: ADDRESSED. `_run_tool` không còn ghi dòng `propose` (`runner.py:733-735`); `_write_propose_rows` chạy sau `try` (`runner.py:677`, `:697-711`); ghim bởi `test_agent_runner.py:2422` và `assertNotIn("change", …)` trong `_assert_turn_and_proposals_undone` (`:2447`, `:2457`).
- Mục "Không kiểm được từ diff" vòng 1 (callback commit sống qua hoàn tác): ADDRESSED. `_undo_turn` (`runner.py:684-694`) rollback savepoint, `reset` `before_commit`/`after_commit`, chạy `after_rollback`; ghim bởi `:2504`, `:2515` (đối chứng), `:2525`.
- Lớp 1: NFR-3, ADR-024 QĐ 2, design vòng 3 §3.2, §4.1, D-7, D-8 đạt; đủ 7 test (v3), không test nào bị che; chữ ký `_run_tool` không đổi; 0 dấu skip; chỉ hai file touchpoint. Checklist (10): 10/10 đạt. Không blocker, không major.
- minor | — | — | 2 điểm nhỏ: (1) chưa có gì ghim việc `_write_propose_rows` đọc `actions` trong bộ nhớ chứ không phải bản `_bounded_actions` (chỉ khác khi mục bị bỏ quá 60000 byte, STD-TEST-8); (2) `_write_entry` trong test `:2388` vẫn ném lỗi sau lần insert thật của dòng `reason` (minor vòng 1) | tùy dev
- Bằng chứng của dev vòng 2: RED `--case TestRunnerTurnUndo` `Ran 11 tests` / `FAILED (failures=6)`, `[('reason', 2), ('reason', 3)] != [('reason', 2), ('change', None), ('change', None), ('reason', 3)]`, `['before_commit', 'after_commit'] != []`; GREEN cả module `Ran 105 tests in 53.731s` / `OK`; 5 đột biến đỏ.
- Không kiểm được từ diff (vòng 2) và cách tech-lead xử lý: (a) lượt GREEN của dev chưa lặp lại → sau merge `3b306a2`, một lần giữ khóa (migrate exit 0, hai cài đặt để trống rồi trả lại, 0 lệnh site ngoài khóa trước và sau): test_agent_runner `Ran 105 tests in 52.962s` / `OK`, 0 deadlock (lượt ngay trước đó `FAILED (failures=1, errors=5)` không tính: migrate của tôi exit 1 vì phiên khác đang giữ `bench_migrate.lock` ngoài `flock`, 5 `QueryDeadlockError`); (b) `_undo_turn` `reset` cả hàng callback chỉ đúng vì `_call_model` commit ngay trước savepoint (`runner.py:129-135`), trong test không có commit nên đường này chỉ kiểm bằng đọc mã → chuyển qa (verify), không chặn tick.
- deferred: 2 minor trên; cùng lỗ hổng callback ở `ROUTE_SAVEPOINT`/`ROUTE_UNIT_SAVEPOINT` (design D-8) → ghi nợ, team-leader; nhánh rollback savepoint ném và callback `after_rollback` ném thuộc T6; thông điệp commit gộp `e7343be` dạng `merge(runner):` (STD-NAME-5, không amend theo lệnh).

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
