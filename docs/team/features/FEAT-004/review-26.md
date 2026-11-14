Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 26 — FEAT-004 T26

- Diff: `git diff 1a82772..318fddb` (1 commit, 2 file, +69/-24). Hàm có từ trước do phiên khác viết ngoài quy trình; reviewer chấm phần T26 của file ở đầu nhánh task
- Vòng: 1 (max_rework=3)
- Verdict: approve (đường dẫn ký sẵn trong `_comment` thuộc Amendment 2 / CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — approve
Lớp 1: Returns đạt đủ. `EXISTS` = "file đã tồn tại", `NO_PARENT` = "thư mục cha chưa có" trùng từng chữ bảng design (dòng 259); `is_new_file=1`, `base_hash=""`, `content_before=""`; `path` 1..300, `content` 1..20000; kết quả có đúng các khóa của design dòng 218 cùng `branch`; 3 test đúng tên Expect; chỉ 2 file touchpoint.
- AC-3: `test_new_file_proposal_does_not_create_file` (không tạo file, HEAD và status không đổi, 1 đề xuất, 1 comment có động từ "tạo"; nhánh đổi sang `feature/new` nên giá trị viết cứng không qua)
- AC-4: `test_no_delete_or_rename_operation_exists` (quét tên và tham số mọi tool được cấp; `content=""` và 20001 ký tự bị từ chối)
- AC-18: file mới bị `.gitignore` che bị từ chối với đúng câu
- STD-TEST-5: hai câu mong đợi đổi theo bảng design; test gộp cũ tách thành 3, mọi assertion cũ còn, nay so khớp cả dict
- `_PATH` minLength 3 → 1 áp cả `propose_file_change`: đúng design 3.1 (`path` 1..300 cho cả hai tool)

Không có blocker, major.

minor | — | — | 3 điểm nhỏ: không có dòng đỏ riêng cho `(content_before, base_hash) == ("", "")`; test "không có thao tác xóa/đổi tên" không tự kiểm tool đề xuất có trong schema nó quét (`test_propose_change.py:42` đã phủ); test comment của T26 chỉ kiểm câu đầu | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `Ran 16 tests` / `FAILED (failures=5)`: `'file đã tồn tại; dùng propose_file_change để sửa'} != {… 'file đã tồn tại'}`; `'thư mục chứa file chưa tồn tại'} != {… 'thư mục cha chưa có'}`; `Items in the second set but not the first:` (`branch`); `3 != 1`
- GREEN: test_propose_change `Ran 16 tests in 42.584s` / `OK`; test_registry `Ran 33 tests in 1.062s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Đổi hợp đồng dữ liệu `base_hash`/`content_before` từ `None` sang `""` cho file mới: tech-lead đã đọc `apply_job.py` ở đầu nhánh T19 (`git grep base_hash`): dòng 328 `if not new_file and on_disk != proposal.base_hash` nên file mới không so `base_hash`; hoàn tác file mới gỡ file, không ghi `content_before`. Không vỡ. Đề xuất file mới đã lưu với `None` trên site dev: dấu nội dung lúc duyệt tính từ giá trị đang lưu nên vẫn khớp chính nó.
- Symlink treo ở đường dẫn yêu cầu (`os.path.lexists` chạy trên realpath): phụ thuộc bộ chặn T42 → ghi deferred cho designer.

## deferred
- Symlink treo: xem trên.
