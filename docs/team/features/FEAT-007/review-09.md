Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 09 — FEAT-007 T9

- Diff: `git diff 58b667411121655d13f8d775710bcdcc44721311..1f3513e` (đầu nhánh `team/FEAT-007-task-9` lúc review; merge vào `team/FEAT-007` là `5bb54cf`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `58b6674..1f3513e` (1 commit, 2 file mới: `erp_ai/agent/hard_bans.py` +26, `erp_ai/agent/test_hard_bans.py` +89).
- Bằng chứng của dev: RED `AttributeError: module 'erp_ai.agent.hard_bans' has no attribute 'hard_ban_reason'`, `Ran 7 tests in 0.069s FAILED (errors=5)`; GREEN `erp_ai.agent.test_hard_bans` `Ran 7 tests in 0.078s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.020s OK`.

### Phát hiện (chỉ blocker/major)

Không có finding nào ở mức blocker hay major.

minor | — | — | 2 điểm nhỏ: (a) STD-TEST-6, `erp_ai/agent/test_hard_bans.py:49`: DocType của app được chọn bằng `limit=1` không có `order_by`, bản ghi được chọn có thể khác giữa các lần chạy (phép khẳng định vẫn đúng; thêm `order_by="name"` thì lặp lại được); (b) phép kiểm hằng chuỗi ở `test_hard_bans.py:79-86` chỉ bắt trùng đúng hoa thường, tên viết thường hoặc ghép chuỗi lọt qua (đúng mức thiết kế yêu cầu) | tùy dev

### Ghi nhận của reviewer

- F-3: ba lý do kiểm đúng thứ tự, đúng chữ: `read.denied_doctypes()`, rồi `site_api.DENIED_DOCTYPES`, rồi `get_meta().is_submittable`, không trúng → `None`. Nhánh chưa có `site_api.PERMISSION_DOCTYPES`, dùng `DENIED_DOCTYPES` là đúng F-3 (đổi tên là INT-1/T57). DocType không có → `DoesNotExistError`, đúng F-3.
- C-2: module chỉ import `frappe`, `erp_ai.agent.tools.read`, `erp_ai.agent.tools.site_api`, và test khẳng định điều đó; `policy.py` không import `hard_bans`.
- Test đỏ khi bỏ hành vi: `test_first_matching_reason_wins` ghim trọn thứ tự ba luật; `test_follows_denied_doctypes_source_live` đỏ nếu module giữ bản chép của tập cấm; chuỗi lý do viết thẳng trong test, không import từ module.

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trước; có ca lỗi; không skip) 4. đạt 5. đạt (`DoesNotExistError` cho đi qua có chủ ý, có ghi; kiểm đầu vào thuộc controller T10) 6. đạt 7. đạt (hàm công khai mới) 8. đạt 9. đạt (không dependency) 10. đạt (`feat(agent): … (FEAT-007)`, không dòng ghi công AI)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| GREEN của dev chưa được chạy lại | Sau merge, trên `team/FEAT-007` @ `5bb54cf`: `erp_ai.agent.test_hard_bans` `Ran 7 tests in 0.096s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.170s OK`. |
| `cmd.test` cả bộ chưa chạy | Theo N-6: chạy ở mốc M1. |
| INT-1 còn mở (`DENIED_DOCTYPES` trong `hard_bans.py` phải về 0, ca `Role`) | Là T57, đã có trong `tasks.md`. |
| `cmd.lint` | Chỉ nợ nền `erp_ai/test_change_decision.py` (xem `review-59.md`). |

## deferred

- (minor, tùy dev) hai điểm nhỏ ở trên; (a) nên sửa khi T57 mở lại file test này.
