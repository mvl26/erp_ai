# Review T6 (FEAT-001)

Verdict: approve (round 2; 1 vòng rework)
Diff: `git diff be71629..team/FEAT-001-task-6` (head ecffc99); vòng 2: `git diff 4234e45..team/FEAT-001-task-6`.
Vòng 1 request-changes: major STD-TEST-2 test_source.py:51-53 (TEN_CAM bị che bởi bước kiểm đuôi file nên xóa mẫu vẫn xanh). Vòng 2: ADDRESSED (mỗi mẫu có test với đuôi hợp lệ, regex được ghim, RED chứng minh bằng cách tạm bỏ một mẫu).
Soát an ninh: chặn thoát đường dẫn (.., tuyệt đối, symlink, thư mục anh em `apps_evil` nhờ commonpath), tên bí mật khớp trên đường dẫn đã giải, không hàm nào ném lỗi, trần 400 dòng/40 kết quả/1 MB/30 s.
minor | — | — | read_source chưa có trần kích thước file; log lỗi chưa kèm đường dẫn; search_source chưa có test đường log | dev's call (deferred)
deferred cho T23/T27: design §8 dòng 692 đòi `limit = 401` bị từ chối; `read_source` kẹp về 400. Registry (`execute_tool`) phải từ chối `limit > 400` bằng kiểm tham số, hoặc sửa dòng design 692. `frappe.logger("erp_ai.source")` tạo lúc import (có thể ghi vào log bench thay vì log site).
Bằng chứng dev: vòng 1 RED (stub) GREEN 9 test, `--app erp_ai` 56 OK; vòng 2 RED (bỏ mẫu khỏi TEN_CAM) GREEN 13 test, pre-commit pass.
