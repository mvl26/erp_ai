Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 13 — FEAT-004 T13

- Diff: `git diff 1df5552..team/FEAT-004-task-13` (2 commit `6cce2b7`, `f09ab8e`; 5 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 1df5552..6cce2b7`)
Lớp 1: AC-3 đạt (`before_insert` → `prepare_new` ép `Chờ duyệt`, xóa nhóm trạng thái; 8 trạng thái × 2 loại + None). AC-12 đạt (`log_step` ghim 10 trường của dòng; 5 ca từ chối không ghi dòng nào). Luật layer khớp design 8.2, có ca cấm và ca cho phép. 5 file đúng touchpoint.
`STATE_FIELDS`: 15 tên trong diff trùng từng tên với bảng trạng thái design 2.1 (9 dòng chứa 11 tên + 4 dòng git); "9 + 4 = 13" của tasks.md đếm dòng, là lỗi chữ của tasks.md (tech-lead đã sửa T13, T31). 14 trường của `content_digest` khớp design 2.3 về nội dung, thứ tự, `ensure_ascii=False`.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/changes/test_transitions.py:213 (`test_content_digest_is_sha256_of_the_fourteen_fields`) | Thứ tự 14 trường chỉ được ghim một phần: cả hai mẫu đặt `is_new_file`, `ahead_count`, `is_core_app` bằng 0, nên đổi chỗ 3 vị trí đó trong `DIGEST_FIELDS` vẫn xanh; khi digest đã lưu vào `approved_digest`, đổi thứ tự về sau biến đề xuất đã duyệt thành "nội dung đề xuất đã bị sửa" | thêm một ca hand-digest mà 3 số nguyên khác nhau (`is_new_file=1, ahead_count=2, is_core_app=0`) |

minor | — | — | 1 điểm nhỏ: chú thích test "11 fields + 4 git fields" đúng nhưng lệch chữ "9 + 4" của tasks.md (đã sửa tasks.md) | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 6cce2b7..team/FEAT-004-task-13`)
- Phát hiện 1: ADDRESSED (`test_transitions.py:221-228` `test_content_digest_pins_the_order_of_the_three_int_fields`; `_hand_digest` liệt kê trường bằng tay theo design 2.3, không đọc `DIGEST_FIELDS`)
- Phát hiện mới: không có blocker/major

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: test_transitions `FAILED (failures=37)`; test_erp_ai_change_proposal `AssertionError: 'Đã từ chối' != 'Chờ duyệt'`; test_architecture `FAILED (failures=5)` (`test_layer_imports_catches_changes_directions`). GREEN: test_transitions `Ran 17 tests in 0.850s` / `OK`; test_erp_ai_change_proposal `Ran 10 tests in 3.929s` / `OK`; test_architecture `Ran 108 tests in 1.482s` / `OK`
- Vòng 2 RED (đổi chỗ `ahead_count`, `is_core_app`): `AssertionError: '4f0c3a67…' != '52bd01de…'`, `Ran 18 tests in 0.875s` / `FAILED (failures=1)`; GREEN: `Ran 18 tests in 0.972s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Từ chối `step` lạ và `actor` rỗng của `write_entry` đến từ mã T4 (đã merge, review-04 approve) → đạt.
- `cmd.test` sau merge: xem tasks.md.
- Đếm `STATE_FIELDS` trong tasks.md T13/T31: đã sửa thành 15 tên.

## deferred
- Không có.
