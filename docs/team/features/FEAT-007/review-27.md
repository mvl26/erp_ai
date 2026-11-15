Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 27 — FEAT-007 T27

- Diff: `git diff 66fc4afb47f2bc1727f845919304b94f733776d2..9ff1e98` (đầu nhánh `team/FEAT-007-task-27` lúc review; merge vào `team/FEAT-007` là `fb8fd5f`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `66fc4af..9ff1e98` (1 commit, 2 file, +105/−1), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.agent.test_classification` `AttributeError: module 'erp_ai.agent.classification' has no attribute 'split_request_comment'`, `Ran 49 tests in 0.077s FAILED (errors=10)`; GREEN `Ran 49 tests in 0.144s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.185s OK`.

### Phát hiện (chỉ blocker/major)

Không có finding nào ở mức blocker hay major.

minor | — | — | 3 điểm nhỏ: (a) `classification.py:115-116`: trần 10 áp sau khi bỏ yêu cầu rỗng, nhưng không test nào ghim thứ tự đó (cắt trước rồi lọc rỗng vẫn qua mọi test); (b) dấu xuống dòng trong một yêu cầu được giữ nguyên, `"x\n2. y"` sẽ trông như thêm một mục đánh số; (c) phép cắt `[:200]` đếm code point, chữ Việt dạng Unicode tách dấu có thể bị cắt giữa chữ và dấu | tùy dev

### Ghi nhận của reviewer

- Chữ ký hàm, dòng đầu, câu hỏi cuối, phép cắt 200 ký tự và trần 10 yêu cầu khớp đúng `design.md:409`; `design-w0-fixes.md` không nói gì về AC-28; hàm không thêm gì ngoài việc dựng chữ.
- Mỗi lỗi dễ gặp đều có test bắt: bỏ kiểm `None` hoặc `needs_split`; đổi ngưỡng "ít nhất 2 yêu cầu"; trần 9 hoặc 11; bỏ phép cắt, cắt ở 199 hoặc 201; bỏ phép trim; hiện tổng thay cho số liệt kê. Chuỗi mong đợi viết đủ trong test.

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trước; không skip) 4. đạt (`keep_agent_settings`, không dùng đồng hồ) 5. đạt (không ném, trả `None`) 6. đạt 7. đạt (chỉ thêm) 8. đạt 9. đạt 10. đạt (`feat(agent): ... (FEAT-007)`, không dòng ghi công AI)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Thiết kế không quyết: quá 10 yêu cầu thì `{n}` là tổng hay số liệt kê. Dev theo mẫu chữ: 11 yêu cầu → "gồm 10 yêu cầu", yêu cầu thứ 11 bị bỏ không báo (`classification.py:116-117`, `test_classification.py:566-573`); người tạo phiếu nhận số đếm sai | Chỗ hở của thiết kế, không phải lỗi của dev; không chặn T27 vì chữ `design.md:409` được làm đúng. Chuyển team-leader để designer thêm một câu. Nếu chọn hiện tổng: đổi một dòng mã và chuỗi mong đợi của `test_caps_at_ten` (task sửa nhỏ trước U4b). |
| Thiết kế im lặng về yêu cầu rỗng; dev trim, bỏ rỗng, không tính vào ngưỡng 2 | Cách đọc hợp lý, có docstring và 2 test ghim; nhờ designer xác nhận cùng câu trên. |
| Phần đăng comment (runner U4b) phải đặt `split_requested`, `split_requests` theo việc `split_request_comment(...)` có trả `None` hay không, không theo `needs_split` thô | Ghi cho kế hoạch đợt 1 (U4b). |
| Escape HTML và cách hiện `\n` khi đăng comment Helpdesk | Thuộc U4b. |
| GREEN chưa được chạy lại; cả bộ chưa chạy | Sau merge, trên `team/FEAT-007` @ `fb8fd5f`: `erp_ai.agent.test_classification` `Ran 49 tests in 0.054s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.068s OK`. Cả bộ: mốc M1. `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`. |

## deferred

- (minor, tùy dev) 3 điểm nhỏ ở trên.
- (thiết kế) nghĩa của `{n}` khi quá 10 yêu cầu; yêu cầu rỗng.
- (đợt 1, U4b) cờ `split_requested` đi theo kết quả của `split_request_comment`; escape khi đăng.
