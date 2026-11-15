Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 73 — FEAT-007 T73

- Diff: `git diff 7821d401614544b778d8a13505e82fa35477a337..04edde0` (nhánh `team/FEAT-007-task-73`; 1 commit, 2 file +144/−4)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `43ae572` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `Ran 23 tests in 21.450s` / `FAILED (failures=1, errors=6)`: 6 × `AttributeError: module 'erp_ai.agent.authority' has no attribute 'run_instructor'`, 1 × `test_assigned_by_agent_is_not_instruction` `AssertionError: True is not false`; GREEN `Ran 23 tests in 23.225s` / `OK`; `test_architecture` `Ran 181 tests in 15.385s` / `OK`.
- Nhận xét của tech-lead về RED: đỏ vì hàm `run_instructor` chưa có và vì `_assigned_by_other` còn nhận ToDo do bot giao (thiếu hành vi); 16 test cũ vẫn xanh trong lần đỏ, tức file test nạp được.
- Tier 1 (đối chiếu spec): đạt. `run_instructor` theo `U1.md:197-205`: trigger comment `@ai` đọc chủ của đúng comment đó qua `ticket_comment_filters`, không quét comment khác, không lùi về chủ phiếu; trigger khác dùng chủ phiếu nếu `is_instruction` nhận, không thì `None`; không ném. `_assigned_by_other` loại `assigned_by == AGENT_USER`. `latest_instructor` còn giữ (xóa ở T80). Bảy tên test của Expect khớp diff. Việc tách `AuthorityTestBase` nằm trong touchpoint, không đổi assertion nào.
- Checklist (10): 1 đạt (đủ ba ca AC-13; ADR-030 QĐ 6) · 2 đạt · 3 đạt (mỗi bộ lọc có một mồi nhử riêng và một ca dương; reviewer thử đột biến trong đầu cho từng nhánh) · 4 đạt (`keep_agent_settings`, rollback, giờ cố định) · 5 đạt (đóng khi `None`, `""`, comment lạ, sai phiếu, sai loại) · 6 đạt (tác giả là `owner` do server đặt; lọc bằng dict) · 7 đạt (`is_instruction` giữ chữ ký; ba test ngoài diff khẳng định `is_instruction` True đều dùng người giao là người) · 8 đạt · 9 không áp dụng · 10 đạt (1 commit `feat(authority): … (FEAT-007)`).

### Findings

Không có blocker, không có major.

- minor | STD-TEST-8 | `erp_ai/agent/test_authority.py` (`TestRunInstructor`) | đường không-phải-comment khi phiếu không tồn tại chưa có test; mã trả `None` vì `is_instruction` loại tác giả rỗng, nhưng câu "never raises" của docstring dựa vào điều đó | thêm một ca phiếu không tồn tại

### Không kiểm được từ diff — tech-lead giải

- `_assigned_by_other` hẹp hơn chạm mọi nơi gọi `is_instruction` (`label_comments`, `latest_instructor`, runner); reviewer đề nghị chạy cả app. Chính sách N-6 để `cmd.test` cả bộ ở M8, nên tech-lead chạy đủ mọi module test có chữ `is_instruction`, `latest_instructor`, `label_comments` hoặc `authority` (`git grep -l` trên `team/FEAT-007`), sau merge `43ae572`, một lần giữ khóa site, `MIGRATE_EXIT=0`, 0 `QueryDeadlockError`: `test_authority` `Ran 23 tests in 21.952s OK`; `test_architecture` `Ran 181 tests in 15.543s OK`; `test_agent_runner` `Ran 110 tests in 28.914s OK`; `test_runner_routing` `Ran 62 tests in 32.250s OK`; `tools.test_propose_change` `Ran 32 tests in 22.291s OK`; `tools.test_registry` `Ran 41 tests in 1.379s OK`; `test_change_decision` `Ran 10 tests in 8.791s OK`; `test_erp_ai_change_proposal` `Ran 25 tests in 18.725s OK`; `changes.test_result_comment` `Ran 6 tests in 2.515s OK`; `changes.test_apply_job` `Ran 117 tests in 131.942s OK`. Không phải khoảng trống. Lần cả app kế: M8.
- `cmd.lint`: `pre-commit run --all-files` trên `43ae572`, mọi hook `Passed`.

## deferred

- Minor STD-TEST-8 trên (dev's call); T74 và T80 cùng file `test_authority.py` nhận ở mục "finding hay lặp".
