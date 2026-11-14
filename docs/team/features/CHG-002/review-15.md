Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 15 — CHG-002 T15

- Diff: `git diff fd69e5f..067b7d1` (nhánh `team/CHG-002-task-15`, 2 commit `4f3ca35`, `067b7d1`; merge vào `team/CHG-002` ở `f6e8e9d`)
- Vòng: 1 (max_rework = 3). Dev được gọi 2 lần trước khi review: lần 1 dừng `DESIGN_CONFLICT` hẹp (`test_architecture.py` ghim `STATE_FIELDS` 15 tên); tech-lead thêm file đó vào touchpoint theo addendum-2 L-1 điểm 1; lần 2 sửa giá trị ghim.
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | 0 blocker, 0 major | — |

minor | — | — | 5 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. `STATE_FIELDS` thêm 4 tên, `prepare_new` xóa trắng, 4 trường git vẫn ở cuối; `GIT_RESULT_FIELDS` thêm `created_dirs` (JSON); `record_commit(name, expected, *, fields) -> bool` đúng §3.6 (chỉ ở hai trạng thái đang chạy, khóa dòng trước, không đổi trạng thái, không ghi nhật ký, sai `expected` trả `False`); `finish(…, command_results=None)` chỉ-từ-khóa sau `*` có sẵn, ba tham số vị trí và `log_step` không đổi (A3 RQ-2).
2. Đạt. 3 file đúng touchpoint; `test_architecture.py` chỉ đổi hằng `STATE_FIELDS` (19 tên, đúng thứ tự), chú thích phía trên và `15 → 19`.
3. Đạt. Có RED cho từng hành vi mới; không skip.
4. Đạt. Hai dòng `test-shape:` khớp phần sửa, vẫn so bằng (L-1, STD-TEST-5); `now_datetime` được patch.
5. Đạt. Mọi kiểm chạy trước `_lock`.
6. Đạt. Chỉ `set_value` có tham số.
7. Đạt. Chỉ thêm; mặc định của `finish` giữ hành vi cũ.
8. Đạt (một chú thích cũ, minor b).
9. Đạt. Chỉ thêm `inspect` của thư viện chuẩn.
10. Đạt. `type(scope): … (CHG-002)`, không dòng AI.

## Không kiểm được từ diff, tech-lead đã xử lý
- Luật "trường trạng thái chỉ ghi trong `changes/`" nay phủ thêm 4 tên mới: module `erp_ai.tests.test_architecture` và lần chạy cả app trên `team/CHG-002` sau merge, xem dòng progress của T15 trong `tasks.md`.
- Reviewer đề nghị gộp (squash) hai commit khi merge vì `4f3ca35` đứng riêng làm `test_architecture` đỏ: giữ merge `--no-ff` như các task khác (task là một merge commit xem lại được; addendum-2 cho phép commit `test-shape:` riêng).

## deferred
1. STD-TEST-8 `test_transitions.py:966-975`: `TestTransitionInput._calls` chưa có `record_commit` (tên rỗng, đề xuất không tồn tại).
2. STD-STYLE-5 `test_transitions.py:63`: chú thích của `STATE_VALUES` không còn đúng (4 trường mới không có trong đó).
3. STD-TEST-8: chưa test `finish(fields={"created_dirs": […]})` qua `_git_values`; `record_commit(fields={})` chỉ cập nhật `modified`, thiết kế không nói.
4. STD-GIT-2: `4f3ca35` đứng riêng để `test_architecture` đỏ.
5. Dòng `test-shape:` thứ hai thiếu tiền tố lớp `TestArchitecture::`.
