Feature: BUG-003
Stage: build
Author-agent: tech-lead
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance BUG-003

Verdict: accepted

Nghiệm thu tự động cỡ S (ADJ-36) trên `team/BUG-003` @ `2354fe0`; không gọi qa, không As-Built. Lệnh chạy từ worktree `.claude/worktrees/bug-003`: `cd /home/miyano/frappe-bench && PYTHONPATH=<worktree> bench --site miyano run-tests …` (dạng worktree của `cmd.test`/`cmd.test_one`).

## Tiêu chí
| criterion | command | output excerpt | verdict |
|---|---|---|---|
| C1 — không có lần chạy thì khung không hiển thị (lúc tạo, sau `done`, sau hẹn giờ, `reset`) | `cmd.test` (gồm `erp_ai.tests.test_architecture`: `test_status_script_indicator_hides_with_display_none`, `test_status_indicator_scanner_catches_hidden_without_display`) | `Ran 660 tests in 117.672s` `OK` | đạt |
| C2 — có lần chạy thì hiện bố cục flex cũ, cả nổi và gắn | như trên (`render` phải kết thúc bằng `setIndicatorVisible(el, true)`; không hàm nào khác ghi `display` lên khung; hằng docked/floating không có `display`) | `Ran 660 tests in 117.672s` `OK` | đạt |
| C3 — test tái hiện đỏ trước vì đúng hành vi lỗi, xanh sau | `cmd.test_one` với `{file}=erp_ai/tests/test_architecture.py` (dev, trước và sau khi sửa) | trước: `FAIL: test_status_script_indicator_hides_with_display_none … AssertionError: Lists differ: ['setIndicatorVisible is missing', 'line 7[621 chars]se)'] != []`; sau: `Ran 79 tests in 0.798s` `OK` | đạt |
| C4 — không đổi gì khác; suite không có test đỏ (baseline rỗng) | `git diff --stat d425faa..team/BUG-003`; `cmd.test` | 2 file: `agent_status_indicator.js` (+10/−5), `test_architecture.py` (+155); `Ran 660 tests in 117.672s` `OK` | đạt |

## Kiểm chung
- `cmd.test`: `Ran 660 tests in 117.672s` `OK` (lượt 2). Lượt 1 ngay sau merge: `Ran 660 tests in 126.564s` `FAILED (errors=39)`, cả 39 là `QueryDeadlockError (1213, 'Deadlock found when trying to get lock…')` trong `setUp` của `test_agent_runner`, `test_runner_status`, `tools.test_read` — tranh chấp DB với lượt chạy suite của phiên FEAT-004 trên cùng site, không file nào thuộc diff. Baseline trước khi sửa: `Ran 658 tests in 144.871s` `OK`.
- `cmd.lint`: `pre-commit run --all-files` — 12 hook `Passed`.
- `cmd.typecheck`: slot rỗng, không áp dụng.
- Dấu skip mới trong diff: không có (`git diff d425faa..team/BUG-003` lọc `test.skip_markers`: 0 dòng).
- Migration lên/xuống: không áp dụng (không đổi schema).

## Chưa kiểm được tự động (việc của người)
- Bước tay AC-10 trên `miyano`: script trên site là bản HD Form Script do `erp_ai.install.after_migrate` nạp từ file; nhánh chưa nằm trên checkout mà bench đang chạy. Sau khi nhánh được đưa vào checkout của bench: chạy `cmd.migrate`, tải lại trang phiếu, xác nhận 3 chấm không hiện khi bot không chạy và hiện/mất đúng khi có lần chạy (cả khi mở khu vực "Trao đổi với bot").

## DoD
- [x] Test đỏ trước, xanh sau; review approve (review-01.md, 2 vòng)
- [ ] CHANGELOG — dự án có `CHANGELOG.md`; tech-lead chỉ ghi được `docs/team/**`, cần writer/dev thêm một dòng `Fixed`
- [ ] Bước tay AC-10 (người)
