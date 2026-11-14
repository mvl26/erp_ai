Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 25 — FEAT-004 T25

- Diff: `git diff a742cd8..5d3264b` (2 commit `b773166`, `5d3264b`; 3 file). Mã gốc của file do phiên khác viết ngoài quy trình (`git diff 25be823..6d90e79 -- erp_ai/agent/tools/propose_change.py`), reviewer chấm phần T25 của file ở đầu nhánh task, không chỉ phần chênh
- Vòng: 2 (max_rework=3)
- Verdict: approve (phần đường dẫn ký sẵn trong `_comment` thuộc Amendment 2 / CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — request-changes (`git diff a742cd8..b773166`, +271/-106)
Lớp 1: Returns đạt: `PROPOSE_TOOL_NAMES`; schema `find[]`/`replace[]`, thay theo vị trí trên bản gốc; 9 câu từ chối trùng từng chữ bảng 3.1 cùng câu thiếu quyền Comment; kết quả có `comment`; không `.save`, `db_set`, `subprocess`; `read_git` mặc định bật. Đủ 6 test của Expect. Sửa trong touchpoint (chỗ sửa ở `test_registry.py` là chỗ tech-lead cho phép).

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/tools/propose_change.py:135, test_propose_change.py:129 | Design 3.1 [Sửa vòng 1] ghi kết quả thành công của thay đổi code có `"branch": "<target_branch>"`; handler bỏ `branch`, test ghim tập khóa đúng `{"ok","proposal","status","comment"}` nên khóa luôn trường đó ra ngoài | trả `branch` từ `guard.git.branch` cho thay đổi code (không cho lệnh), kiểm trong test |

Assertion cũ bị sửa (STD-TEST-5): mọi chỗ đều bằng hoặc chặt hơn (so cả câu thay vì một phần; so HEAD và `status --porcelain` trước/sau); chỗ bỏ là theo design (giới hạn 20000 ký tự → 1 MiB `TOO_LARGE`; `edits` → `find[]`/`replace[]`; "đang Chờ duyệt" → "đang chờ duyệt" của 3.8).

minor | — | — | 4 điểm nhỏ: chưa có ca `find` khớp hai lần chồng nhau ("aa" trong "aaa"); `test_propose_change.py:50` `assertNotIn("propose_delete_file")` thừa; chú thích `:32` nói các câu là hợp đồng design 3.1 nhưng `FILE_EXISTS`/`FOLDER_MISSING` (`:43-44`, thuộc T26) lệch bảng; `:29` buộc giới hạn cỡ đề xuất vào `SEARCH_FILE_MAX_BYTES` | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff b773166..5d3264b`, 2 file, +10/-4)
- Phát hiện 1: ADDRESSED (`propose_change.py:180-181` trả `{**result, "branch": guard.git.branch}` chỉ cho thay đổi code; `test_propose_change.py:127,131-134` đổi sandbox sang nhánh `feature/propose` nên giá trị viết cứng sẽ đỏ; `:352` kiểm kết quả lệnh không có `branch`)
- Phát hiện mới: không có

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Vòng 1 RED: `AssertionError: {'ok': False, 'reason': 'tham số không hợp lệ: edits'} != {'ok': False, 'reason': 'đoạn find[0] không có trong file'}`; GREEN: test_propose_change `Ran 14 tests in 10.087s` / `OK`, test_registry `Ran 33 tests in 1.111s` / `OK`, test_architecture `Ran 112 tests in 3.084s` / `OK`
- Vòng 2 RED: `AssertionError: Items in the second set but not the first: 'branch'`; GREEN: test_propose_change `Ran 14 tests in 10.966s` / `OK`, test_registry `Ran 33 tests in 1.136s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `HD Ticket.new_comment` trả `comment.name`: reviewer đã đọc `hd_ticket.py:617-629` của helpdesk đang cài, đúng; test của module chạy trên bản đó và xanh.
- Bộ lọc HTML của Comment có che một chỗ thiếu escape không: test ghim `&apos;`; ghi cho T34.

## deferred
- T26: `propose_new_file` cũng là thay đổi code, design 3.1 đòi `branch`; câu `FILE_EXISTS`/`FOLDER_MISSING` theo bảng 3.1.
- Dev thấy ngoài phạm vi: trong `erp_ai_change_proposal.json`, `file_path` và `target_branch` là Data không có `ignore_xss_filter`, đường dẫn có `<`, `>` bị bộ lọc XSS của Frappe đổi → cho designer.
- `_PATH` minLength 3 thay vì 1 của design (schema dùng chung với T26).
