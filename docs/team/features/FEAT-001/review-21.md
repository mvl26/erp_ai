# Review 21 — FEAT-001 T21 (thẩm quyền theo người, làm lại theo D8)

- Verdict: approve (vòng 2; 1 vòng rework sau lần làm lại; lần đầu là design-defect, review-17)
- Diff: `git diff 1d6976e..team/FEAT-001-task-21 -- erp_ai` (head 0a0ff08); merge 2da5abb. Nhánh cũ 3ed63de giữ ở `team/FEAT-001-task-21-r1`
- Vòng 1 request-changes: major STD-TEST-8 (filter ToDo `allocated_to`/`reference_type` không có test riêng). Vòng 2 (FIX_BASE 3f85124): ADDRESSED (3 test mới đỏ khi bỏ từng filter; limit 1/50; test non-admin)
- Bằng chứng dev: RED 12 test (failures=7 errors=2); GREEN test_authority Ran 16 OK; kiểm đột biến từng guard
- review-17 (blocker nguồn comment; major STD-SEC-4 tác giả; major STD-TEST-8; major STD-TEST-2 D-16): tất cả ADDRESSED

## Findings
Không còn blocker/major.

## Deferred
- minor STD-TEST-2: `test_fetch_ticket_comments_as_non_administrator_uses_permissions` chạy bằng người được phép đọc, đổi `get_list` thành `get_all` vẫn xanh; thêm ca người bị từ chối (liên hệ không phải chủ phiếu).
- minor STD-DESIGN-5: `latest_instructor` còn tối đa 3 truy vấn/comment (≤ 30).
- minor STD-STYLE-5: dòng `_force_assign_list` thừa ở hai test.
