Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 40 — FEAT-004 T40

- Diff: `git diff 3aa363f..team/FEAT-004-task-40` (1 commit `4f7e85d`, 2 file mới, +166)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: chưa có ca cho DEL `\x7f` hay ký tự điều khiển C1; ký tự định dạng Unicode (U+202E, U+200B) đi qua `safe_person_name` (3.9 và NFR-8 không đòi) | tùy dev

## Review checklist (10)
1–4 đạt; 5 không áp dụng (hàm thuần); 6–10 đạt. Hai mẫu thông điệp trùng design 3.9 từng ký tự.

## Bằng chứng của dev
- RED: `Ran 3 tests in 0.003s` / `FAILED (failures=3)`, ví dụ `AssertionError: '' != 'erp_ai: áp dụng AICHG-00007 (erp_ai/agent/policy.py)'`
- GREEN: `Ran 3 tests in 0.003s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- T18/T45 so thông điệp thật với `commit_message` phải dựng lại bản xem trước bằng `message_text(*apply_message(..., <người duyệt>))`, không `str.replace` tên: đưa vào handoff T18, T49.
- Đầu vào là `get_fullname(decided_by)`, không bao giờ là email: kiểm ở T19/T45/T47.

## deferred
- Không có.
