Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 48 — FEAT-004 T48

- Diff: nhánh `team/FEAT-004-task-48` (vòng 1 `6cf568e..f24cdaa`; vòng 2 `b83e3e8..bbd6534`)
- Vòng: 2
- Verdict: approve

## Vòng 1 — `git diff 6cf568e..f24cdaa` — request-changes

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/changes/test_apply_job.py:571-583 | phép kiểm "0 lần trong comment" không bao giờ đỏ vì `make_change_proposal` không ghi comment nào | ghi comment của đề xuất như sản phẩm làm, khẳng định kho comment không rỗng rồi mới `assertNotIn` |
| major | STD-TEST-5 | erp_ai/agent/changes/test_apply_job.py:501-502,516,524 | phép kiểm ref trên remote bare không bao giờ đỏ vì `add_remote` chỉ ghi URL giả | đặt push URL về repo bare, giữ fetch URL giả cho phép kiểm rò rỉ |

## Vòng 2 — phạm vi: chỉ diff sửa

Lệnh đã chạy (chỉ đọc):
```
git log --oneline b83e3e8..team/FEAT-004-task-48        # bbd6534, 1 commit
git diff --stat b83e3e8..team/FEAT-004-task-48          # 1 file, +107 -17, chỉ test_apply_job.py
git diff b83e3e8..team/FEAT-004-task-48
git show bbd6534:erp_ai/agent/changes/test_apply_job.py   # đọc 2628-2760 và 135-145
git grep ticket_comment_filters / new_comment ở bbd6534    # rủi ro ngoài diff: comment do ai ghi
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md   # tiêu chí T48, trạng thái T57
```

### Phát hiện cũ
- (1) STD-TEST-2 — ADDRESSED — `erp_ai/agent/changes/test_apply_job.py:2691-2702,2729-2734`: đề xuất nay tạo qua `execute_tool("propose_file_change")`, tức đúng đường sản phẩm ghi comment phiếu (`propose_change.py:121` `new_comment`). Test khẳng định kho comment của phiếu có đúng 1 comment, chứa tên đề xuất và "Nhánh này theo origin/main", rồi mới `assertNotIn`. Truy vấn `comments` (`reference_name in [name, doc.ticket]`) bao trùm comment này. Bằng chứng đỏ của dev: thêm URL vào ghi chú → `'x-token-FAKE' unexpectedly found` (thêm `host/r.git`, `://`), failures=3.
- (2) STD-TEST-5 — ADDRESSED — `erp_ai/agent/changes/test_apply_job.py:2630-2633,2644-2645,2659,2668`: `remote set-url --push origin <bare>`, có kiểm push URL = bare và fetch URL = `REMOTE_URL`; `remote_refs()` đọc `ls-remote` của bare. Bằng chứng đỏ: thêm tạm `git push origin main` → `assertEqual(remote_refs(), remote_before)` hỏng (`b4e13d6… != 9a22900…`).
- Yêu cầu thêm (review-45) — đã làm — `erp_ai/agent/changes/test_apply_job.py:2578-2625` `test_failure_reason_has_no_hook_output`: hook đánh dấu được gắn thêm dòng in `HOOK_OUTPUT`; khóa `refs/heads/main.lock` làm commit hỏng sau điểm hook chạy, cho cả apply và undo; kiểm `failure_reason` không chứa đầu ra hook/email, file và HEAD trả về như cũ, 0 tệp đánh dấu. Phần đối chứng (2617-2625) bật hook qua `GIT_HOOKS_DIR` và thấy `HOOK_OUTPUT pre-commit` trong `failure_reason`, nên việc gắn dòng `echo` vào hook được chứng minh có tác dụng. Bằng chứng đỏ: bật hook trong job → chuỗi hook xuất hiện ở [apply] và [undo].

### Phát hiện mới (chỉ blocker/major)
Không có.

minor | — | — | 1 điểm nhỏ: `apply_then_undo` (2544-2553) không trả session về `ACTOR` khi một assert ở giữa hỏng (không dùng `try/finally`/`addCleanup`); không ảnh hưởng kết quả khi xanh | tùy dev

### Deferred (ngoài phạm vi vòng này, không chặn)
- T48 ghi `depends: … T57` nhưng T57 (AC-28, comment kết quả của job) chưa làm; `assertEqual(len(ticket_comments), 1)` (2732) sẽ đỏ khi T57 ghi comment kết quả lên phiếu, và lúc đó phép kiểm rò rỉ phải đọc thêm comment kết quả. Tech-lead cần chốt thứ tự merge/sửa lại test khi T57 vào.
- Lần chạy cả module có 2 lỗi `Deadlock found` (1213) ở test ngoài lớp; chạy lại theo tên thì xanh. Nếu lặp lại thì ghi vào `docs/team/debt.md` (STD-TEST-7).
- `team/FEAT-004` hiện tại không phải tổ tiên của `bbd6534`; tech-lead kiểm xung đột khi merge.

### Không kiểm được từ diff
- Không chạy test (site dùng chung đang chạy kiểm merge); chỉ dựa vào RED/GREEN trong gói review. Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.changes.test_apply_job` sau khi merge.

## Review checklist (10)
1. Đúng spec, không thừa (STD-DESIGN-5, STD-TEST-2): đạt — AC-19 c, AC-23, NFR-7..9, AC-13 có test; test thứ 4 là yêu cầu của review-45; refactor `add_proposer`/`tool_context` trong `TestNoKeyLeak` giữ nguyên hành vi.
2. Touchpoint, vị trí file (STD-DESIGN-1, STD-STRUCT-1/2): đạt — chỉ `erp_ai/agent/changes/test_apply_job.py`, không có file mới.
3. Test đỏ trước, cạnh/lỗi, không skip (STD-TEST-1, STD-TEST-8, STD-TEST-4): đạt — có RED cho cả 3 chỗ sửa; nhánh commit hỏng được test cho apply và undo; không có skip/xfail.
4. Không sửa test cho khớp sai, độc lập (STD-TEST-5, STD-TEST-6): đạt — hai phép kiểm trước đây không thể đỏ nay đỏ được; khóa ref được gỡ trong `finally`; repo sandbox tạm.
5. Xử lý lỗi, timeout (STD-ERR-1, STD-ERR-2, STD-ERR-5): đạt — chỉ có test; `failure_reason` được kiểm tiền tố `GIT_COMMIT_FAILED_TEXT`.
6. Bảo mật (STD-SEC-1/3/4/6): đạt — dùng khóa/URL/email giả; test kiểm không rò đầu ra hook, email, token.
7. Hợp đồng API/dữ liệu (STD-DESIGN-3, STD-OPS-2): đạt — không đổi mã sản phẩm.
8. Tên, cấu trúc, không code chết (STD-NAME-1/2, STD-STYLE-4/5): đạt — trích `hook_dir`, `add_proposer`, `tool_context` bỏ lặp; một điểm nhỏ ở trên.
9. Phụ thuộc mới (STD-DEP-1/3/5): đạt — không có.
10. Commit, nhánh, tài liệu (STD-NAME-4/5, STD-GIT-1, STD-DOC-2): đạt — `test(changes): … (FEAT-004)` trên `team/FEAT-004-task-48`.
