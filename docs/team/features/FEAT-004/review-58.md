Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 58 — FEAT-004 T58

- Diff: `git diff 6e5b94c..team/FEAT-004-task-58` (head 913c2d2, 1 file: `erp_ai/test_change_decision.py`, +192/-1)
- Lệnh đã chạy (chỉ đọc): `git log --oneline 6e5b94c..team/FEAT-004-task-58`, `git diff --stat 6e5b94c..team/FEAT-004-task-58`, `git diff 6e5b94c..team/FEAT-004-task-58`, `git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T58'`, `git show team/FEAT-004-task-58:docs/team/features/FEAT-004/spec.md | grep AC-27/AC-12`, `git show team/FEAT-004-task-58:erp_ai/agent/changes/apply_job.py` (dòng 187-239, 330-352), `git show team/FEAT-004-task-58:erp_ai/test_utils.py` (set_agent_settings, commit_file, switch_branch), `git log -1 --format=%B 913c2d2`
- Vòng: 1
- Verdict: approve

## Layer 1 — khớp spec
- AC-27 (Amendment 2): `test_link_approval_still_rechecked_at_apply` (test_change_decision.py:373) duyệt qua `decide` POST (có chữ ký), lấy đúng job `apply` mà `decide` xếp hàng (khẳng định `user` = người duyệt, `action` = `apply`, dòng 332-334), chạy job dưới phiên người duyệt, rồi kiểm 5 điều kiện: ô code tắt, file đích đổi, nội dung lệch dấu, nhánh đổi, app rút khỏi danh sách. Mỗi ca khẳng định trạng thái + lý do viết tay, byte file và HEAD không đổi, số commit không đổi, worktree không đổi, 0 lần gọi `git_add_new`/`git_commit_only`/`run_bench`, và nhật ký đúng `[("approve", INSTRUCTOR, None), (step, INSTRUCTOR, reason)]`. Có ca đối chứng (dòng 405-412) cho thấy cùng fixture được áp dụng khi không đổi gì, nên mỗi ca từ chối chỉ do điều kiện của nó.
- Mỗi ca cô lập đúng một kiểm: ca nội dung sửa cập nhật luôn `after_hash` (dòng 392-397) nên `STORED_HASH_MISMATCH` không bắt thay, chỉ `approved_digest` bắt được; ca file đích đổi giữ tên nhánh; ca nhánh đổi giữ byte file. Đối chiếu `apply_job._recheck`/`_apply_code` (dòng 187-239, 330-352): các lý do và trạng thái khớp. RED của dev cho 5 lần bỏ từng kiểm đều ra kết quả khác giá trị kỳ vọng (4 ca ra `Đã áp dụng`, ca nhánh ra `Lỗi` do hậu kiểm commit), tức test có thể đỏ.
- AC-12: `test_decide_logs_exactly_one_row_with_the_caller_as_actor` (dòng 468) cho cả approve và reject: 0 dòng trước, đúng 1 dòng sau (giải nén `(row,)`), `actor` = người gọi, khác `instructor` của đề xuất (TICKET_CREATOR) và khác tài khoản agent; thêm `decided_by`.
- review-chg001 Nhóm F, major STD-TEST-2 "thiếu test AC-12 và AC-27": **ADDRESSED** — test_change_decision.py:373 (AC-27), test_change_decision.py:468 (AC-12).
- Không thiếu, không thừa: chỉ sửa đúng touchpoint `erp_ai/test_change_decision.py`, không đổi mã sản phẩm.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major. | — |

minor | — | — | 4 điểm nhỏ: (1) STD-TEST-2 test_change_decision.py:336-338,461 spy `run_bench` không bao giờ được gọi trên đường code (`_apply_code` không chạy bench, ca đối chứng cũng không khẳng định spy > 0), nên phần "0 lệnh chạy" của AC-27 và câu "no git/bench run" trong commit không được ghim cho đề xuất loại lệnh bench; (2) STD-TEST-2 test_change_decision.py:483 `assertIsNotNone(row.creation)` không thể đỏ (Frappe luôn đặt `creation`); (3) STD-STYLE-4 test_change_decision.py:375 chú thích "Runs before the class's rollback" sai: rollback là của từng test (`setUp` addCleanup), không phải của class; (4) STD-STYLE-4 test_change_decision.py:374 docstring "one log row" trong khi khẳng định là 2 dòng (approve + bước job) | tùy dev

## Review checklist (10)
1. Đúng và đủ spec/criteria (STD-DESIGN-5, STD-TEST-2): đạt — AC-27 5 điều kiện qua `decide`, AC-12 1 dòng đúng người gọi.
2. Touchpoint, file mới (STD-DESIGN-1, STD-STRUCT-1, STD-STRUCT-2): đạt — 1 file, đúng touchpoint, không file mới.
3. Test đỏ trước, biên và lỗi, không skip (STD-TEST-1, STD-TEST-8, STD-TEST-4): đạt — task chỉ test; RED bằng bỏ từng kiểm có trong gói; toàn bộ là đường lỗi + ca đối chứng; không skip/xfail.
4. Không sửa test cho khớp sai; độc lập, lặp lại được (STD-TEST-5, STD-TEST-6): đạt — không sửa test cũ; mỗi subTest `reset()` nhánh/kho và cài đặt; kho là `GitSandbox` riêng mỗi test; `frappe.db.commit` của job bị chặn, rollback + xoá cache cài đặt khi dọn.
5. Lỗi, biên, timeout (STD-ERR-1, STD-ERR-2, STD-ERR-5): không áp dụng (chỉ test).
6. Bảo mật (STD-SEC-1, STD-SEC-3, STD-SEC-4, STD-SEC-6): đạt — không bí mật, không `protected_paths`; test chạy trên kho tạm, không đụng `apps/` thật.
7. Hợp đồng API/dữ liệu (STD-DESIGN-3, STD-OPS-2): không áp dụng (không đổi hợp đồng).
8. Tên, cấu trúc, style, không mã chết (STD-NAME-1, STD-NAME-2, STD-STYLE-4, STD-STYLE-5): đạt — theo style của file; 2 chú thích/docstring lệch nhỏ (gộp vào minor).
9. Phụ thuộc mới (STD-DEP-1, STD-DEP-3, STD-DEP-5): không áp dụng (`hashlib` là thư viện chuẩn).
10. Commit, nhánh, tài liệu (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-DOC-2): đạt — nhánh `team/FEAT-004-task-58`, commit `test(change-decision): ... (FEAT-004)`, 1 commit/task, không dòng attribution AI.

## Không kiểm được từ diff
- GREEN `Ran 10 tests` / `OK` và 5 dòng RED chỉ có từ lời dev; reviewer không chạy test (site dùng chung, đang chạy merge check). Đề nghị: `cd ../.. && bench --site miyano run-tests --module erp_ai.test_change_decision` sau khi merge check xong.
- Dev không ghi rõ đã bỏ kiểm "app list" ở chỗ nào: `check_write_path` được gọi 2 lần (`_recheck` và `_apply_code`); kết quả RED `Đã áp dụng` chỉ ra được khi bỏ ở trong `change_guard` (chung cho cả hai). Tech-lead xác nhận với dev nếu cần.
- AC-27 với đề xuất loại lệnh bench (ô tắt, app rút) không được kích hoạt qua `decide` trong task này; đường job là chung, nhưng "0 lệnh chạy" chỉ được ghim ở `test_apply_job` (ngoài diff).

## Deferred
- Không có.
