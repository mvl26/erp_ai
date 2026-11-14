Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 22 — FEAT-004 T22

- Diff: `team/FEAT-004-task-22` (head 7b72cad), dải `3d19fda..team/FEAT-004-task-22`, 1 commit, 2 file
- Vòng: 1
- Verdict: approve

Lệnh git đã dùng (chỉ đọc):
```
git log --oneline 3d19fda..team/FEAT-004-task-22
git diff --stat 3d19fda..team/FEAT-004-task-22
git diff 3d19fda..team/FEAT-004-task-22
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T22'
git show team/FEAT-004-task-22:docs/team/features/FEAT-004/design.md | sed -n '612,636p'
git show team/FEAT-004-task-22:docs/team/features/FEAT-004/design-addendum-2.md | grep -n -A6 'QĐ-A3'
git show team/FEAT-004-task-22:docs/team/features/FEAT-004/spec.md | grep -n -E 'AC-10|AC-13|NFR-3|NFR-5'
git grep -n -E 'COMMAND_TIMED_OUT|lệnh chạy quá giờ' team/FEAT-004-task-22 -- . ':!docs'
git grep -n -E 'subprocess\.|Popen|check_output|execute_in_shell' team/FEAT-004-task-22 -- erp_ai/agent ':!*test_*'
git show team/FEAT-004-task-22:erp_ai/agent/changes/apply_job.py   (dòng 79-139, 251-253, 596-630)
git show team/FEAT-004-task-22:erp_ai/agent/changes/process_runner.py   (dòng 110-160)
git show team/FEAT-004-task-22:erp_ai/agent/changes/test_apply_job.py   (dòng 1-12, 71-93)
git show team/FEAT-004-task-22:erp_ai/test_utils.py   (add_credential)
```

Layer 1 (đúng spec): đủ. `timed_out` được kiểm trước `not_found` và `exit_code`, lý do "quá thời gian" đúng design 4.3 bước 4 (design.md:627-630) và QĐ-A3; hằng `COMMAND_TIMED_OUT` (câu sai của T21) bị xóa, không còn chỗ nào dùng ngoài docs. Có đủ 3 test Expect. Test AC-13 gieo khóa giả vào `os.environ` và credential; bench stub in `env` nhận được; git chạy thật trong sandbox; đọc `git log --format=%an%ae%cn%ce%B` của commit áp dụng và commit hoàn tác; env của mọi lệnh git được spy ghi lại. Không có gì thừa, đúng touchpoints.

Test trước code:
- `test_command_timeout_fails_with_reason` đỏ khi xóa nhánh `timed_out` (lý do thành "lệnh trả mã None"), và đỏ khi trả thứ tự về như cũ (subTest `not_found`). Dev dán output RED.
- `test_limit_passed_is_remaining_budget` đỏ nếu `limit` là hằng 540, hoặc nếu `deadline` lấy lại trong `_apply_command`, vì `started` của `run_change` là lần gọi `monotonic` đầu tiên. Test xanh ngay lần chạy đầu: đây là test cho hành vi T21 đã có.
- `test_fake_key_never_in_proposal_result_log_comment`: mọi kho đều được chứng minh là có dữ liệu ("PATH=" có trong output, 5 dòng log, 2 comment, 2 commit, 4 lần email bot, mọi env git có `GIT_CONFIG_GLOBAL=/dev/null`, nên git chạy không có `env=` cũng làm test đỏ). Bốn lần gieo khóa cố ý vào đường code thật (env bench, env git cùng tên committer, ghi chú comment, tên nhánh) đều làm đỏ đúng các kho tương ứng. Bộ dò không bị che.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major | — |

minor | — | — | 3 điểm nhỏ: (1) STD-TEST-8, suspected: khóa gieo vào credential (`test_apply_job.py:2507` `add_credential`) không có đường nào trong luồng đọc tới (propose/apply/undo không gọi model), nên chỉ đỏ được khi code bắt đầu đọc credential. Cùng họ với FEAT-001 T14 và FEAT-006 T24. Khóa trong `os.environ` mới là phần có tác dụng. (2) STD-TEST-8: hai kho `frappe.logger("erp_ai")` (design 4.3 bước 6) và `frappe.log_error` (đã mock thành `self.log_error`) không được quét tìm khóa; nên thêm `self.log_error.call_args_list` và một spy logger vào `leaks`. (3) STD-TEST-6: `test_limit_passed_is_remaining_budget` (`test_apply_job.py:2447`) patch `time.monotonic` toàn cục và tính lần gọi đầu là mốc bắt đầu job, nên phụ thuộc thứ tự gọi. Subtest `not_found + timed_out` (`:2408`) là trạng thái `_run_wrapped` không bao giờ tạo ra, nhưng vẫn ghim được thứ tự của design | tùy dev

## Review checklist (10)
1. Đạt: làm đúng và đủ AC-10, AC-13, NFR-3, NFR-5 của T22, không thừa (STD-DESIGN-5, STD-TEST-2).
2. Đạt: chỉ 2 file touchpoint, không có file mới (STD-DESIGN-1, STD-STRUCT-1).
3. Đạt: có output RED cho nhánh quá giờ. Hai test còn lại xanh ngay lần đầu vì phủ hành vi đã có, và có bằng chứng gieo khóa làm đỏ. Không có skip/xfail (STD-TEST-1, STD-TEST-4). Phần thiếu (minor) xem trên (STD-TEST-8).
4. Đạt: test cũ `test_timed_out_command_ends_as_failed` đổi giá trị mong đợi sang câu của design, tức là sửa cho đúng spec chứ không chiều theo hành vi sai (STD-TEST-5). Mỗi test rollback và patch `frappe.db.commit` (STD-TEST-6). Patch đồng hồ toàn cục ghi ở minor.
5. Đạt: mọi nhánh lỗi đều `_Stop` kèm lý do và lưu kết quả; lệnh có `timeout -s KILL` (STD-ERR-1, STD-ERR-5).
6. Đạt: không có bí mật thật (khóa giả `sk-ant-ERPAI-T22-LEAK-…` chỉ có trong test); có test bảo đảm không lộ khóa (STD-SEC-1, STD-SEC-6).
7. Đạt: câu `failure_reason` đổi sang câu của design trước khi release. Không có migration, không còn chỗ nào dùng câu cũ (STD-DESIGN-3).
8. Đạt: tên rõ, xóa hằng không dùng, không có code chết (STD-NAME-1, STD-STYLE-5).
9. Đạt: không thêm dependency (STD-DEP-1).
10. Đạt: 1 commit `feat(changes): … (FEAT-004)` trên nhánh `team/FEAT-004-task-22` (STD-GIT-1, STD-NAME-4). Không cần đổi docs.

## Không kiểm được từ diff
- Tôi không chạy test (site dùng chung). Bằng chứng xanh chỉ có ở gói review: `Ran 102 tests … OK`, xanh ở lần chạy lại; lần đầu có 23 `QueryDeadlockError`. Tech-lead cần xác nhận lại bằng một lần chạy riêng module: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.changes.test_apply_job`.
- Tôi không thấy output đỏ của 4 lần gieo khóa cố ý, chỉ có lời dev kể. Code gieo khóa có trong test và chạy cùng test, nên nếu module xanh thì các nhánh đỏ đã được chứng minh.

## Deferred
- Không có.
