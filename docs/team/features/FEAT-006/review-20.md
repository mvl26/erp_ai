# Review 20 — T20 Runner `_route` (u1) đầy đủ và kiểm SLA

- Verdict: approve (vòng 2 sau 1 vòng sửa; max_rework=3)
- Lệnh diff: vòng 1 `git diff 77dce93..581a6b3 -- erp_ai`; vòng sửa `git diff 581a6b3..d9fad65 -- erp_ai`; toàn task `git diff 77dce93..d9fad65 -- erp_ai`. Merge 31d1dba.
- Gói: review-pkg-T20.md, review-pkg-T20-r2.md; findings vòng 1: review-20-round1.md. Báo cáo dev: dev-T20.md, dev-T20-r2.md.
- Touchpoint mở rộng (tech-lead chấp nhận, kỳ vọng cũ đổi theo design 3.5/4.2, không nới assertion): erp_ai/agent/test_agent_runner.py.

## Vòng 1: request-changes
| Mức | STD | Vị trí | Nội dung | Vòng 2 |
|---|---|---|---|---|
| major | STD-TEST-6 | test_agent_runner.py:579,633 | kỳ vọng SLA "Standard" 1440 phút phụ thuộc dữ liệu site | ADDRESSED (patch `applied_sla` với dữ kiện cố định) |
| major | STD-TEST-2 | test_runner_routing.py:381-409 | test (u1) lỗi không khóa việc dừng kiểm SLA | ADDRESSED (actions đúng `["apply_route"]`, không warning, `_route` trả `[]`) |
| major | STD-TEST-8 | runner.py:369-371 | không test error cũ + error mới | ADDRESSED (`test_apply_exception_keeps_earlier_error_and_adds_its_own`) |
| minor | — | — | dòng info, tên logger, lý do no-SLA, nhánh `skipped` | ADDRESSED (bỏ `lines=`; thêm khẳng định) |

## Vòng 2: approve, không có finding mới

## Rulings của tech-lead (mục "cannot verify")
- Khi (u1) bị từ chối/ném lỗi, `decision.notes` không vào `skipped_fields`: giữ (không có gì áp dụng thì không có trường bị bỏ qua).
- after_commit: `rollback(save_point)` không xóa hàng đợi `after_commit`; dev và reviewer xác nhận chỉ có thông báo realtime/chỉ mục tìm kiếm tạm thời, không rò dữ liệu, không đổi mã.
- Chạy test: dev chạy `run-tests --app erp_ai` trên đầu nhánh d9fad65: `Ran 807 tests in 140.144s`, `OK`; `test_runner_routing` 26 OK, `test_agent_runner` 56 OK. Tech-lead: `git diff --stat d9fad65 31d1dba -- . ':!docs'` rỗng, cây mã sau merge trùng cây đã chạy xanh (role-policy chặn tech-lead chạy bench với PYTHONPATH).

## deferred
- Dòng info `erp_ai route` chưa có `assigned=`/`task=`/`comment=` (design 4.2 dòng 296): T21/T22 thêm.
- Minor STD-GIT-2: cc82977 để 5 test cũ đỏ ở commit giữa (đầu nhánh xanh).
