Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 02 — FEAT-002 T2

- Diff: `git diff a4cb74f..team/FEAT-002-task-2`
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có blocker/major.

minor | — | — | 3 điểm nhỏ (deferred): (a) `test_install.py:204-208` `test_emptied_thinking_text_survives_setup` ghi `""` bằng `set_single_value` thay vì lưu form (chuỗi đầy đủ D-8 đã phủ ở `test_erp_ai_setting.py:165-171`); (b) `test_status_fields_defaults` chỉ kiểm default trong meta, phần giá trị lưu phủ ở `test_status_defaults_filled_only_when_missing`; (c) ca min > max dùng 6/5 thay vì 4/3, cùng ý | dev tùy

## Review checklist (10)
1–10: đạt. Thông báo lỗi khớp từng chữ với design 3.1; cận dùng `ANSWER_DELAY_MAX_S` duy nhất; `check_status_settings()` gọi sau `check_limits()`; `""` không thành NULL (kiểm thẳng `tabSingles`).

## Bằng chứng dev (mục "không kiểm được từ diff" do tech-lead đã đối chiếu)
- ĐỎ: 2 file, 34 test, 12 failures/errors đúng lý do (`ValidationError not raised` với -1, 31, 6>5, 5001 ký tự; `'NoneType' has no attribute 'fieldtype'`; `'<missing>' != 'Đang suy nghĩ…'`).
- XANH: `test_erp_ai_setting` 19 OK; `test_install` 15 OK; lint `pre-commit` đạt.
- Toàn bộ: Ran 515, failures=16, errors=3, danh sách đỏ giống nền. Lần chạy đầu 37 errors + 102 "Deadlock" do một lần chạy khác đồng thời trên site chung; chạy lại 0 deadlock (bài học: không chạy full suite song song).
- `migrate` chạy một lần sau khi sửa JSON: `enabled`=1, `permission_level`="L1", 1 dòng khóa không đổi; 3 trường mới có mặc định `Đang suy nghĩ…`/3/5 (không in khóa).
- DB HD Team/HD Ticket/HD Form Script/ERP AI Log: 4/4/0/22 trước và sau. Merge `dbb035f`; cây `erp_ai/` sau merge giống nhánh task.

## deferred
review-02 minor (a)–(c) ở trên. Ghi cho T9: `_ensure_default_settings` chỉ điền khi NULL/thiếu, T9 sửa `install.py` phải giữ quy tắc đó (D-8).
