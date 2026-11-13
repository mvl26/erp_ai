Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 41 — FEAT-004 T41

- Diff: `git diff 66ddf58..team/FEAT-004-task-41` (1 commit `5196ba1`, 2 file, +263/-2)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: `change_text.py:67-70` `_shown` chỉ lọc `://` trong khi 3.2 còn che `@` ở `upstream_ref`; chưa có test cho đề xuất `Lệnh bench` có `is_core_app=1` | tùy dev

## Review checklist (10)
1–10 đạt. Câu chữ trùng design 3.9 mục 1–6; hàm T40 không đổi.

## Bằng chứng của dev
- RED: `Ran 9 tests ... FAILED (failures=5)`, ví dụ `AssertionError: Lists differ: [] != ['Lệnh bench không hoàn tác được.']`
- GREEN: `Ran 9 tests in 0.007s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `design.md:394` liệt kê trường `onload` đọc mà thiếu `change_status`, `apply_commit_sha`, `undo_commit_sha`: T49 truyền cả document (`proposal_notes(self)`), đưa vào handoff T49.
- Escape và nối vào comment/form: T49, T50.

## deferred
- Sửa danh sách trường ở `design.md:394` (writer, As-Built).
