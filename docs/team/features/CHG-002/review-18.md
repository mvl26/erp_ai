Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 18 — CHG-002 T18

- Diff: `git diff e6cda3e..45452c4` (nhánh `team/CHG-002-task-18`, 1 commit, 3 file, +280/−8; merge vào `team/CHG-002` ở `a6a6560`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve (0 blocker, 0 major)

## Vòng 1 — approve
- Dấu ghim: reviewer dựng lại bằng tay hai danh sách JSON 14 giá trị theo thứ tự `DIGEST_FIELDS` và định dạng `json.dumps`, băm bằng `sha256sum`: `Thay đổi code` → `9722b100…6d38` = `LEGACY_CODE_DIGEST`; `Lệnh bench` → `b03878cb…d73a` = `LEGACY_COMMAND_DIGEST`. Công thức dạng cũ giống nhau ở `f5cfed2`, BASE `e6cda3e` và đầu nhánh.
- Thứ tự rẽ khớp A3 RQ-5 (`transitions.py:129-150`): `_require_proposal` → `is_block` cho dấu khối → chỉ nhánh `else` gọi `block.require_code_kind(doc)` trước công thức cũ. Không thêm `except`. Chữ ký `content_digest(doc)`, `is_block(doc)` không đổi (RQ-2).
- Returns khớp task: dạng cũ `Sửa`/`Tạo` → 1 `FileOp`; lệnh dạng cũ → `operations_of` trả `()`, `commands_of` trả `[json.loads(command_args)]` hoặc `[]`; kiểm loại chạy đầu tiên ở cả hai hàm đọc, cả hai dạng; `ValueError` đúng chữ. 7 test của Expect có đủ. `require_code_kind` dùng chung cho hai module thay vì chép (STD-DESIGN-4). Người gọi ở mã sản phẩm đã có rào: `apply_job.py:205` và `erp_ai_change_proposal.py:89` chỉ gọi khi `is_block`.
- Test thêm ngoài danh sách: `test_legacy_command_empty_args_no_command` (thiết kế có: "hoặc `[]`"); `test_unknown_change_kind_block_digest_is_not_refused_here` (thiết kế có: thứ tự rẽ của RQ-5 §2.4); `test_legacy_edit_empty_contents_and_path` (`test_block.py:120`) ghim hành vi thiết kế KHÔNG nêu: `None` thành `""`, dòng `Thay đổi code` không có `file_path` cho mục `Sửa` đường dẫn rỗng thay vì ném lỗi → câu hỏi thiết kế, không phải phát hiện (xem dưới).

minor | — | — | 3 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. 2. Đạt (file test đặt cạnh mã, `tests: colocated`). 3. Đạt (RED 9 lỗi đúng assertion; 4 test ghim xanh sẵn trên BASE là hợp lệ; không skip). 4. Đạt (L-1: 0; mọi doc trong bộ nhớ, không `insert`). 5. Đạt (không `except`). 6. Không liên quan. 7. Đạt (dấu cũ giữ nguyên byte). 8. Đạt. 9. Đạt (`transitions → block` có sẵn, `block` không nhập `transitions`). 10. Đạt (`feat(changes): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff, tech-lead đã xử lý
- Kết quả test: xem dòng progress của T18 trong `tasks.md` (đợt merge 5 trên `a6a6560`).
- Site `miyano` có đề xuất đã duyệt mang `change_kind` ngoài hai loại không (duyệt ở `transitions.py:216` hay kiểm lại ở `apply_job.py:238` nay ném `ValueError`): đúng là phép đếm của T51 (A3 RQ-5 §6) và nhánh G-10 của FEAT-007; làm ở checkpoint T51, trước khi vào `develop`.
- Bộ chặn lúc áp dụng (T14/T33) có từ chối mục `Sửa` đường dẫn rỗng mà `test_legacy_edit_empty_contents_and_path` ghim không: T33 chưa làm → ghi vào deferred và vào lệnh giao T33; nếu T33 không chặn thì test ghim này phải đổi (báo team-leader như câu hỏi cho designer: §2.3 và RQ-5 không nói về trường rỗng).

## deferred
1. STD-TEST-8 `block.py:85`: bỏ vế `change_kind != CHANGE_KIND_COMMAND` ở `commands_of` dạng cũ vẫn xanh (ca loại code duy nhất có `command_args` rỗng); thêm dòng `Thay đổi code` dạng cũ có `command_args = json.dumps(ARGV)`, chờ `[]`.
2. STD-TEST-8 `block.py:68`: `after_hash` dạng cũ `""` → `None` chưa được chạy qua.
3. STD-TEST-8 `block.py:87`: lệnh dạng cũ có `command_args` là `"[]"` cho `[[]]` (một argv rỗng); thiết kế không nói, chưa có test; bộ chặn của T33 phải phủ.
4. Cho lệnh giao T33: kiểm mục `Sửa` đường dẫn rỗng và argv rỗng bị từ chối lúc áp dụng.
