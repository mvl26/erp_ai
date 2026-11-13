Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 49 — FEAT-004 T49

- Diff: `git diff 7b58389..team/FEAT-004-task-49` (1 commit `f46c279`; 2 file, +133/-3)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: AC-22, AC-17, AC-21, D-14 có; chỉ 2 file touchpoint; `validate`/`onload` khớp Returns; đủ 3 test Expect; `test_content_field_change_on_save_is_refused` vẫn phủ `commit_message`.

Các điểm đã chấm:
- (a) STD-TEST-5 không bị phá: assertion cũ của `test_insert_keeps_content_fields` mong chữ mẫu của người gọi sống sót qua insert; D-14 nay bảo controller ghi đè, tức spec đã bỏ hành vi đó; thông điệp đầy đủ được ghim ở test mới (dòng 345).
- (b) Đề xuất lệnh bench: controller đặt `commit_message` = None (dòng 74). Design 4.1 chỉ tả ca code; design 2.1 ghi trường chỉ dùng cho code và lý do D-14 (model không tự thêm chữ, AC-13) nên xóa là hợp design; test ghim ở dòng 357.
- (c) STD-TEST-2 đạt: thông điệp (345-352) và ghi chú (730-748) viết tay, không gọi `change_text` để dựng giá trị mong đợi.
- (d) Bất biến giữ: bản xem trước đặt trong `validate` khi bản ghi mới; sau đó `commit_message` thuộc `CONTENT_FIELDS`; `content_digest` đọc trường đã lưu.

Phát hiện blocker/major: không có.

minor | — | — | 3 điểm nhỏ: tên `test_insert_keeps_content_fields` không còn đúng với `commit_message`; `commit_message` mẫu ở `test_utils.py:650` luôn bị ghi đè (dữ liệu chết, ngoài touchpoint); `_form_as` đặt lại `frappe.response.docs` thành `[]` thay vì trả giá trị cũ | tùy dev

## Review checklist (10)
1–10 đạt.

## Bằng chứng của dev
- RED: `Ran 22 tests in 24.290s` / `FAILED (failures=7)`: `'erp_ai: chữ do model tự viết…' != 'erp_ai: áp dụng AICHG-00001 (myapp/myapp/ok.py)…'`, `None != ['Lệnh bench không hoàn tác được.']`
- GREEN: change_proposal `Ran 22 tests in 22.281s` / `OK`; test_transitions `Ran 42 tests in 25.121s` / `OK`; test_architecture `Ran 108 tests in 1.572s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `flags.ignore_validate`: nếu `propose_change` (T25/T50) insert với cờ này thì bỏ qua cả ghi đè D-14 lẫn kiểm bất biến → ghi vào handoff T25, T50 và review của chúng.
- `cmd.test` sau merge: xem tasks.md.

## deferred
- Designer: design 4.1 chưa nói ca đề xuất lệnh bench cho `commit_message` (mã đặt None).
