Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 55 — FEAT-004 T55

- Diff: `7b72cad..team/FEAT-004-task-55` (head 874bf62, 1 commit, chỉ `erp_ai/agent/changes/test_apply_job.py` +105)
- Vòng: 1
- Verdict: approve

Lệnh git đã chạy (chỉ đọc):
```
git log --oneline 7b72cad..team/FEAT-004-task-55
git diff --stat 7b72cad..team/FEAT-004-task-55
git diff 7b72cad..team/FEAT-004-task-55
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T55'
git show 874bf62:erp_ai/agent/changes/apply_job.py      # run_change, _locked_run, _has_authority, _recheck
git show 874bf62:erp_ai/agent/changes/test_apply_job.py # ApplyJobTestCase, test_rechecks_fail_without_writing, test_undo_rechecks_fail_without_writing
git show 874bf62:erp_ai/agent/changes/process_runner.py # cách import subprocess
git show 874bf62:erp_ai/agent/authority.py              # NEVER_AUTHORITY
git show 874bf62:erp_ai/test_utils.py                   # pin_agent_roles
```

## Lớp 1 — khớp spec
Tiêu chí T55 (ADR-023 QĐ 2 + "Test M2"; ADR-012 QĐ 7; NFR-6): mỗi vế một test không thể xanh khi bỏ vế đó, cả áp dụng và hoàn tác.

| Vế | Test | Kết luận |
|---|---|---|
| Người thực hiện thuộc `NEVER_AUTHORITY`, kể cả khi tài khoản agent mang `ERP AI Instructor` | `TestActorRecheckAndLock.test_apply_refused_when_decider_is_agent_account_even_with_role` (subTest apply, undo) | Đạt. Agent mang role và là `session.user` = người thực hiện, nên chỉ vế `user not in NEVER_AUTHORITY` (`apply_job.py:184`) có thể từ chối; `AGENT_USER` có trong `NEVER_AUTHORITY` (`authority.py:12`). Assert trạng thái + lý do (chuỗi cứng), byte file, HEAD, worktree sạch, đúng 1 dòng `fail`. |
| Mất role trước job | `test_rechecks_fail_without_writing` case "role lost" (apply), `test_undo_rechecks_fail_without_writing` case "role lost" (undo) | Đạt. Cả hai assert lý do cứng, file không đổi, số commit/HEAD không đổi, `steps == [..., "fail"]`. Bỏ vế role → ACTOR/UNDOER qua được kiểm → đỏ. |
| `session.user` khác người thực hiện | cùng hai test, case "wrong session user" (Administrator cho apply, ACTOR cho undo) | Đạt. Bỏ vế `apply_job.py:196` → ACTOR/UNDOER vẫn có quyền → job chạy → đỏ. |
| Khóa hết giờ → `Lỗi` có lý do, 1 dòng `fail`, 0 tiến trình con | `test_lock_timeout_fails_with_reason_one_log_row_zero_subprocess` (code apply, command apply, undo ở `Đang hoàn tác`) | Đạt. `filelock` bị patch ném `LockTimeoutError`; assert `lock.assert_called_once()`, `popen.assert_not_called()` (process_runner dùng `import subprocess` nên patch `subprocess.Popen` có hiệu lực), lý do cứng, đúng 1 dòng `fail`, byte + HEAD không đổi. |

- Missing: không. Hai tên test trong dòng Expect (`test_apply_and_undo_refused_after_role_removed`, `test_session_user_other_than_actor_fails`) không được tạo; hai vế đó đã được ghim bởi test có sẵn đáp ứng đủ các assert mà Expect yêu cầu (đã đọc, xem bảng). Docstring lớp mới ghi rõ điều này.
- Extra: không. Chỉ sửa file test trong touchpoint; `apply_job.py` không đổi (hợp với "mã chỉ sửa nếu test đỏ").
- Misunderstood: không.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|

Không có blocker/major.

minor | — | — | 3 điểm nhỏ: (1) STD-NAME-6 `test_apply_job.py:2673` tên test nói "apply" nhưng ghim cả undo (tên lấy nguyên từ tasks.md); (2) STD-TEST-8 `test_apply_job.py:2705` timeout được giả lập bằng `filelock()` ném ngay khi gọi, không phải ở `__enter__` — đường khóa thật chỉ có `test_lock_timeout_fails_without_writing` cho code apply, chưa có cho command/undo; (3) dòng Expect của T55 trong tasks.md nêu hai tên test không tồn tại — tech-lead cập nhật dòng Expect trỏ về hai test có sẵn | tùy dev

## Review checklist (10)
1. Đạt — làm đúng và đủ các vế tiêu chí, không thêm (STD-DESIGN-5, STD-TEST-2).
2. Đạt — chỉ `test_apply_job.py`, trong touchpoint (STD-DESIGN-1, STD-STRUCT-1).
3. Đạt — RED bằng đột biến tạm cho cả 4 vế có trong gói review; có đường lỗi; không skip/xfail (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Đạt — không sửa assert cũ; subTest tạo sandbox riêng hoặc trạng thái tất định; role agent được `pin_agent_roles` khôi phục + rollback (STD-TEST-5, STD-TEST-6).
5. Đạt — không đổi mã xử lý lỗi; nhánh `except LockTimeoutError` được ghim (STD-ERR-1).
6. Đạt — test củng cố kiểm quyền phía server cho tài khoản agent; không có bí mật (STD-SEC-1, STD-SEC-4).
7. Đạt — không đổi hợp đồng API/dữ liệu (STD-DESIGN-3).
8. Đạt — tên/hằng theo quy ước file; không code chết (STD-NAME-2, STD-STYLE-5); xem minor (1).
9. Đạt — không thêm phụ thuộc (STD-DEP-1).
10. Đạt — commit `test(changes): ... (FEAT-004)`, nhánh `team/FEAT-004-task-55` (STD-NAME-4, STD-NAME-5, STD-GIT-1); không đổi hành vi người dùng nên không cần tài liệu.

## Không kiểm được từ diff
- Lint/format (`pre-commit run --all-files`) không có output trong gói review → tech-lead kiểm.
- GREEN `Ran 104 tests ... OK` chỉ là lời dev; reviewer không chạy test (site dùng chung). Gợi ý: `cmd.test_one erp_ai/agent/changes/test_apply_job.py`.
- Test cho thấy `transitions.approve(name, AGENT_USER)` và `transitions.request_undo(name, AGENT_USER)` không từ chối tài khoản agent; job (M2) là lớp chặn. Nếu ADR-023/ADR-012 muốn chặn cả ở bước duyệt thì nằm ngoài T55 → tech-lead đối chiếu.

## Deferred
Không có.
