# Review 22 — T22 Runner (u3) tạo Task cho C/D

- Verdict: approve (vòng 2 sau 1 vòng sửa; max_rework=3)
- Lệnh diff: vòng 1 `git diff 1b79b96..ada855c -- erp_ai`; vòng sửa `git diff ada855c..3db98bf -- erp_ai`; toàn task `git diff 1b79b96..3db98bf -- erp_ai`. Merge 5c6efd5.
- Gói: review-pkg-T22.md, review-pkg-T22-r2.md; findings vòng 1: review-22-round1.md. Báo cáo dev: dev-T22.md, dev-T22-r2.md.

## Vòng 1: request-changes
| Mức | STD | Vị trí | Nội dung | Vòng 2 |
|---|---|---|---|---|
| major | STD-TEST-8 | runner.py:406 | không test `create_routed_task` trả `ok=false` mà không ném | ADDRESSED (`test_refused_task_without_exception_no_task_no_comment`; đột biến `if True:` đỏ ở `1 != 0`) |
| major | STD-TEST-6 | test_runner_routing.py:915 | đếm ToDo Task toàn site | ADDRESSED (đếm theo `self.person`, so với `before`) |
| minor | — | — | test (i) dùng `PermissionError` thay vì `disable_document_sharing` | giữ (đường thật có ở `test_route_ticket.py:499`) |

## Vòng 2: approve, không có finding mới

## Rulings và đo
- Chạy test: dev chạy `run-tests --app erp_ai` trên đầu nhánh 3db98bf: `Ran 834 tests in 157.432s`, `OK`; `test_runner_routing` 53 OK, `test_agent_runner` 56 OK. Tech-lead: `git diff --stat 3db98bf 5c6efd5 -- . ':!docs'` rỗng, cây mã sau merge trùng cây đã chạy xanh.
- Bị từ chối không ném (thiếu quyền tạo Task / không có DocType): phiếu có người, không Task, không comment, chỉ log: giữ, vì thêm câu "chia sẻ tài liệu đang tắt" sẽ sai lý do.

## deferred
- Cho team-leader/designer: (a) có cần câu comment riêng cho trường hợp Task bị từ chối không ném; (b) câu "Bot chưa gán được người phụ trách…: không giao được Task…" xuất hiện khi phiếu đã được gán, đúng chữ design 4.2 nhưng dễ hiểu nhầm.
- Kiểu commit `fix(runner)` cho thay đổi chỉ-test (đúng hơn là `test(runner)`), minor STD-NAME-5.
- Chưa có ca đầu mục D ở runner (`needs_task` tính ở `decide_route`, có test ở test_routing.py).
