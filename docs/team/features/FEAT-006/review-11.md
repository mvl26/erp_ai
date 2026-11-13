Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 11 — FEAT-006 T11

- Diff: `git diff f1a732b..776839a` (nhánh `team/FEAT-006-task-11-cont`, 2 commit 66c2452 + 776839a; merge `27d18fe`)
- Vòng: 1 (sau một lượt dev làm tiếp do DESIGN_CONFLICT được tech-lead giải, xem dưới)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | (1) test vị trí trường chỉ kiểm sau `section_routing`, chưa kiểm trước `section_alerts`; (2) `DESCRIPTION_MAX_CHARS` và test 400 ký tự lặp lại `MAX_DESCRIPTION_CHARS` ở `test_doctype_descriptions.py` (STD-DESIGN-4); (3) pin `phrases` của `auto_assign_enabled` là token ngắn; (4) commit 66c2452 đứng một mình làm `test_doctype_descriptions` đỏ (STD-GIT-2): đầu nhánh task xanh, merge `--no-ff` giữ cả hai.

## Đổi touchpoint (tech-lead, ghi ở progress.md)
Dev đầu báo DESIGN_CONFLICT: thêm 2 trường làm `erp_ai/tests/test_doctype_descriptions.py` đỏ (`field_count` 24 != 22; `phrases` thiếu 2 trường). Tech-lead mở rộng T11 đúng 1 file, chỉ cho phép thêm dữ liệu ghim (`field_count` 22 -> 24, 2 mục `phrases`), không nới khẳng định cũ (STD-TEST-5). Cần người xác nhận ở lần dừng. Việc đã làm dở của dev đầu được tech-lead commit nguyên trạng (66c2452) để dev sau làm tiếp từ đó.

## Quyết định thiết kế cần người chốt (từ reviewer; chưa phải defect)
Bảo vệ "để trống thì không kiểm" trong `check_routing_rules` là cách đọc duy nhất chạy được của plan (validator từ chối giá trị trống, T12 mới ghi mặc định). Nhưng nó vẫn còn sau T12: người dùng System Manager xóa `routing_rules` rồi lưu được; bộ nạp trả `{}` nên tắt assignees, mức tối thiểu và kiểm SLA, runner ghi "routing_rules không hợp lệ" mỗi lần chạy. Chọn một và ghi vào design 3.3: (a) trống được chấp nhận và nghĩa là "tắt routing" (sửa `description` của `routing_rules`, hiện nói "Cấu hình sai bị chặn khi lưu"); (b) trống bị từ chối sau khi T12 đã ghi mặc định.

## Deferred
- Từ reviewer: soát lại `description` của `auto_assign_enabled` ("từ L1", "chưa có ai được gán", "1 Task cho đầu mục C/D") với hành vi thật ở T19 (mã chưa có).
- Từ review-09: `departments.<d>` thiếu ca riêng cho kiểm chuỗi `team`/`head` ở routing.py.
- Site `miyano` đã được `bench migrate` một lần từ worktree dev T11 để áp 2 trường mới (exit 0).

## Bằng chứng chạy (dev)
- RED: 6 failure + 4 error (thiếu trường; cấu hình xấu không bị chặn). Phần RED của `test_doctype_descriptions`: `24 != 22` và `phrases` lệch tập.
- GREEN: `test_erp_ai_setting` 24 OK; `test_doctype_descriptions` 10 OK; `cmd.test` trên đầu nhánh task 776839a: Ran 728 tests, OK; lint pass.
- Đột biến: `if True` (kiểm cả khi trống) làm nhiều test đỏ; `if False` làm 6 subtest đỏ; đổi một từ trong `phrases` làm test đỏ; đều hoàn tác.
- Sau merge: `git diff --stat 776839a HEAD -- . ':!docs'` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 1).
