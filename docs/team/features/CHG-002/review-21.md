Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 21 — CHG-002 T21

- Diff: vòng 1 `git diff a6a6560..b09eb30` (2 file, +228/−1); vòng 2 (sửa) `git diff b09eb30..6f65cb3` (2 file, +17/−3); nhánh `team/CHG-002-task-21`
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 **approve** → merge `a1d968f`, tick
- Lần gọi dev trước đó (build lượt 2, round 16) trả `DESIGN_CONFLICT` với 0 commit; phán ở `design-addendum-5.md` P-1.

## Vòng 1 — request-changes

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-6 | erp_ai/agent/test_change_text.py:771 | `SENT_AT.replace(tzinfo=datetime.UTC)`: `datetime.UTC` chỉ có từ Python 3.11; CI chạy bộ test trên Python 3.10 (`.github/workflows/ci.yml:50`; `pyproject` `requires-python >= 3.10`). Trên 3.10 test `test_aware_or_bad_sent_at_raises_value_error` lỗi `AttributeError`, CI đỏ; lần chạy xanh ở máy (3.12.3) không lộ ra | dùng `datetime.timezone.utc` |

minor | — | — | 2 điểm nhỏ: (a) STD-DOC-7 docstring `proposal_notes` chưa nói `ValueError`; (b) STD-ERR-2 `and sent_at` coi mọi giá trị falsy kiểu khác (0, False, []) là "rỗng" | tùy dev

Lớp 1 (khớp đặc tả): P-1 đạt đủ (vị trí dòng cuối cho cả hai dạng, năm dòng chữ đúng từng byte, `ValueError` cho trạng thái lạ, `%H:%M %d/%m/%Y` không đổi múi giờ, `Đã gửi` thiếu giờ); đủ tám tên test của P-1; chỉ hai file touchpoint.

Bằng chứng của dev: RED `Ran 25 tests` / `FAILED (failures=23)` (ví dụ `test_unknown_status_raises_value_error … ValueError not raised`); GREEN `test_change_text` `Ran 25 tests` / `OK`, `test_architecture` `Ran 179 tests` / `OK`, `test_propose_change` `Ran 32 tests` / `OK`, `test_erp_ai_change_proposal` `Ran 25 tests` / `OK`.

## Vòng 2 — scoped re-review (`b09eb30..6f65cb3`), approve

- Phát hiện 1: ADDRESSED. `test_change_text.py:771` nay là `SENT_AT.replace(tzinfo=datetime.timezone.utc)`; `git grep -n "datetime\.UTC" -- erp_ai` in 0 dòng; không còn tên nào chỉ có từ 3.11 trong hai file.
- Minor (b) dev nhận sửa: `change_text.py:194` thành `sent_at not in (None, "")`; test mới `TestRestartLabel::test_falsy_sent_at_of_other_type_raises_value_error` (0, False, [], {}, 0.0); RED trước khi sửa `FAILED (failures=5)`, mỗi ca `ValueError not raised`.
- Minor (a) dev nhận sửa: docstring thêm dòng Raises (còn thiếu, xem deferred).
- Blocker/major mới từ diff sửa: không.
- GREEN sau sửa: `test_change_text` `Ran 26 tests` / `OK`, `test_architecture` `Ran 179 tests` / `OK`.
- Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)

- Cả app sau merge (đợt 8, `team/CHG-002` @ `c2af4d7`, một lần giữ khóa 09:00–09:09 gồm `cmd.migrate` thoát 0): `Ran 1683 tests in 528.543s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Python 3.10: máy bench chạy 3.12.3, chỉ job CI 3.10 cho thấy được; ghi vào checkpoint T51 và báo team-leader (kiểm job CI khi mở PR).
- Form ném lỗi khi `restart_status` hỏng cho tới khi T22 (P-5) merge: T22 nay phụ thuộc T21 và đang ở vòng review; hai task đi cùng một lần phát hành.
- `propose_change.py:121` cũng gọi `proposal_notes`: an toàn nhờ A5-4 (lúc đề xuất `restart_status` rỗng); `test_propose_change` trên `c2af4d7` `Ran 32 tests in 24.616s` / `OK`.

## deferred

1. STD-DOC-7 `change_text.py:207-208`: dòng Raises của `proposal_notes` thiếu `ValueError` của `_stored_commands` (`:131`) và `int(ahead_count)` (`:225`); chưa nói `restart_sent_at` chỉ được kiểm khi trạng thái là `Đã gửi`.
2. Không test nào ghim việc `restart_sent_at` hỏng bị bỏ qua ở ba trạng thái còn lại (đặc tả không đòi).
