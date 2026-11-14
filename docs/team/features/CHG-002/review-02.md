Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 02 — CHG-002 T2

- Diff: `git diff fd69e5f..bad503a` (nhánh `team/CHG-002-task-2`, 1 commit, còn giữ, CHƯA merge)
- Vòng: 1 (max_rework = 3)
- Verdict: **design-defect** → tech-lead dừng T2, báo team-leader

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-GIT-2 | erp_ai/test_utils.py:586 (làm vỡ erp_ai/agent/tools/test_source.py:930, :947-951, :984) | Thêm khóa `erp_ai` vào ảnh chụp làm ba test có sẵn đỏ mọi lần: `test_real_core_repos_snapshot_reads_the_four_core_repos` (ghim đúng bốn tên repo), `test_real_core_repos_snapshot_runs_only_read_commands` (ghim lệnh git của bốn repo, 8 lời gọi, nay 10), `test_real_core_repos_mixin_on_real_repos_passes_when_untouched`. `test_source.py` không phải touchpoint của T2; dev chỉ chạy `test_test_utils` | Plan thêm `erp_ai/agent/tools/test_source.py` vào touchpoint của T2 (L-1); dev đổi ba giá trị ghim thành `(*CORE_APPS, "erp_ai")`, kể cả đường dẫn `erp_ai` trong danh sách lệnh git kỳ vọng. Reviewer xác nhận bằng đọc mã, chưa chạy |
| major | STD-TEST-6 | erp_ai/test_utils.py:586 cùng :605-623 (`RealCoreReposUntouchedMixin`) | Theo đúng design R-11 / §8.1: mixin so ảnh chụp ở `setUpClass` với `tearDownClass`, nay đọc cả cây chính `/home/miyano/frappe-bench/apps/erp_ai` (HEAD và `status --porcelain`). Cây đó đang được ghi liên tục (`tasks.md`, journal, metrics, ADR chưa track, `.team/miyano-site.lock`, commit tài liệu và merge `team/*` vào `develop` của các phiên khác) → lớp test đỏ ở `tearDownClass` dù không chạm gì; kết quả phụ thuộc phiên khác đang làm gì. Thu hẹp về `status -- erp_ai/` cũng không đủ vì merge vào `develop` đổi cả HEAD | Designer viết lại R-11 / §8.1: (a) bỏ `erp_ai` khỏi ảnh chụp theo lớp, đo NFR-14 như spec ghi ("qa so trước và sau `cmd.test`") cộng một luật kiến trúc; hoặc (b) một chốt dựng từ tín hiệu do chính test sở hữu |

minor | — | — | 6 điểm nhỏ (xem deferred) | tùy dev

Ai đang dùng ảnh chụp: 6 lớp test (`test_apply_job.py:2679`; `test_source.py:518`, `:1362`, `:1428`, `:1847`, `:2009`), thêm `test_source.py:934` chụp hai lần liên tiếp; các lớp AB, BB của T33..T45 sẽ dùng (plan.md:201). `.claude/worktrees/` đã bị git bỏ qua (`.gitignore:15`), nên hoạt động trong worktree dev không hiện ở status.

## Review checklist (10)
1. Đạt. `make_block_proposal` đúng Returns (`Chờ duyệt`, dòng con từ `FileOp` hoặc dict, `command_list` JSON, hash tự tính, `ignore_permissions=True`, không commit).
2. Đạt về diff (2 file), nhưng thay đổi cần ở ngoài touchpoint không được báo (phát hiện 1).
3. Đạt. Có RED và GREEN.
4. **Trượt** (phát hiện 2).
5. Đạt.
6. Đạt.
7. Đạt.
8. Đạt (một docstring cũ).
9. Đạt.
10. **Trượt**: commit không qua được test của app (phát hiện 1).

## Không kiểm được từ diff
- Ba test đỏ ở `test_source.py` là do đọc mã, chưa chạy: `test_one` với `erp_ai/agent/tools/test_source.py` trên nhánh task (làm ở lượt sửa, sau khi designer phán).
- Dev chưa chạy cả app.

## Ghi chú của tech-lead
- Điểm 2 khớp lo ngại của dev (`DONE_WITH_CONCERNS`) và ảnh hưởng thẳng tới cách build đang chạy: tech-lead sửa `tasks.md` và journal ở cây chính trong lúc dev chạy test.
- Điểm 1 thuộc luật L-1 (tech-lead thêm được `test_source.py` vào touchpoint), nhưng giá trị ghim mới phụ thuộc phán quyết của điểm 2 (có khóa `erp_ai` hay không), nên chờ designer; `test_source.py` còn là file của làn 1 (T3 → T4 → T49), lượt sửa T2 không chạy cùng lúc với T4.

## deferred
1. `test_utils.py:606`, `:623`: docstring và câu lỗi của mixin còn nói "real core repo (NFR-9)".
2. `test_test_utils.py:351`: status của `erp_ai` chỉ `assertIsInstance(status, str)`.
3. `:321`: chỉ test `base_hash` cho sẵn được giữ, chưa test `after_hash`.
4. `:313`: chưa assert đầu `/dev/null` của diff tạo và xóa.
5. `:269`: ticket mặc định chỉ kiểm truthy.
6. `:349`: so HEAD với lần `rev-parse` thứ hai có thể đua với một commit đồng thời.
