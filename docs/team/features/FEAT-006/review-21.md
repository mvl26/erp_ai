# Review 21 — T21 Runner (u2) gán người và (u4) comment

- Verdict: approve (vòng 2 sau 1 vòng sửa; max_rework=3)
- Lệnh diff: vòng 1 `git diff b6d3504..8de1908 -- erp_ai`; vòng sửa `git diff 8de1908..9dc0ca8 -- erp_ai`; toàn task `git diff b6d3504..9dc0ca8 -- erp_ai`. Merge f6a7f21.
- Gói: review-pkg-T21.md, review-pkg-T21-r2.md; findings vòng 1: review-21-round1.md. Báo cáo dev: dev-T21.md, dev-T21-r2.md.
- Touchpoint mở rộng (tech-lead chấp nhận): `erp_ai_setting.json` (chỉ `description` của `auto_assign_enabled`, deferred của review-19, nay khớp hành vi; 382 ký tự) và `test_doctype_descriptions.py` (cụm khóa của trường đó).

## Vòng 1: request-changes
| Mức | STD | Vị trí | Nội dung | Vòng 2 |
|---|---|---|---|---|
| major | STD-TEST-8 | test_runner_routing.py:643,667 | ca lỗi (u2)/(u4) không khóa rollback đúng savepoint đơn vị | ADDRESSED (mock ghi thật rồi ném; đột biến bỏ rollback và rollback ra savepoint ngoài đều đỏ) |
| major | STD-TEST-2 | test_runner_routing.py:611 | `comment=` của dòng info chỉ khẳng định 0 | ADDRESSED (`(1,0,1,"ok")`) |
| major | STD-TEST-2 | test_runner_routing.py:626 | `rule` chỉ `assertTrue` | ADDRESSED (`assertEqual` với `assignment_rule` của HD Team) |
| minor | — | — | tên savepoint lồng; test trùng | deferred / dev tùy ý |

## Vòng 2: approve, không có finding mới

## Rulings và đo
- Chạy test: dev chạy `run-tests --app erp_ai` trên đầu nhánh 9dc0ca8: `Ran 826 tests in 152.297s`, `OK`; `test_runner_routing` 45 OK, `test_agent_runner` 56 OK, `test_doctype_descriptions` 10 OK. Tech-lead: `git diff --stat 9dc0ca8 f6a7f21 -- . ':!docs'` rỗng, cây mã sau merge trùng cây đã chạy xanh.
- after_commit/realtime của `assign_to.add` không bị rollback savepoint hủy; callback đăng ký ở bước cuối `notify_assignment` nên thông báo ma chỉ khi lỗi sau bước đó (rất hiếm, không rò dữ liệu phiếu): ghi nhận concern, không sửa mã.

## deferred
- Design 4.2 và tasks.md dòng 143 ghi savepoint `erp_ai_route` cho từng đơn vị; mã dùng `erp_ai_route_unit` lồng trong `erp_ai_route` (đúng kỹ thuật vì MariaDB thay savepoint cùng tên): chuyển designer cập nhật.
- `test_team_rule_assigns_bot_does_not` và `test_rule_assignment_in_route_save_kept` trùng nhiều: tùy dev.
