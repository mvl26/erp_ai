Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 43 — FEAT-007 T43

- Diff: `git diff 07745fc3e3bb96c996963b04ca8682dd58d15f89..3b966e6` (nhánh `team/FEAT-007-task-43`; 2 commit `7dfcf63` test, `3b966e6` mã; 5 file +366, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3). Lần gọi reviewer đầu (round 94) chạm trần 25 lượt, không trả báo cáo; báo cáo dưới đây là của lần gọi lại (round 96), cùng diff, cùng bằng chứng.
- Verdict: approve; merge `56b10be` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau commit test `7dfcf63`, không migrate): test_erp_ai_kpi_week 8 test đỏ ở `setUp` `AssertionError: None is not true : DocType ERP AI KPI Week is missing`, `Ran 8 tests in 0.007s FAILED (failures=8)`; test_doctype_descriptions 7 test `FileNotFoundError: ... erp_ai_kpi_week/erp_ai_kpi_week.json`, `Ran 12 tests in 0.353s FAILED (errors=7)`. GREEN @ `3b966e6`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_erp_ai_kpi_week `Ran 8 tests in 0.568s OK`, test_doctype_descriptions `Ran 12 tests in 0.354s OK`, test_architecture `Ran 182 tests in 16.021s OK`, test_install `Ran 56 tests in 19.990s OK`.

Lớp 1: mọi tiêu chí đạt, chỉ touchpoint đổi. 17 trường và kiểu khớp `design.md:258-268`, không thêm không thiếu; `week_start` là Date, bắt buộc, unique (AC-55, ADR-033 QĐ 6); tên `KPI-<ISO>` đặt trong `autoname` của controller, JSON không có khóa `autoname`; module "ERP AI agent", không `istable`, không submittable; System Manager và ERP AI Instructor chỉ có `read`, `report` (`design.md:270`); hai test của Expect có mặt; không mã `refuse_agent_write` (T58) lọt vào.

Checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đạt. Khóa trường khớp thứ `compute_week` trả (`kpi.py:31-40`); `computed_at` để cho `run_weekly_kpi`. `in_list_view` trên `week_start`, `week_end` là lựa chọn hiển thị vô hại.
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Đúng 5 file.
3. Test trước, biên, không skip (STD-TEST-1/8/4): đạt. RED đúng lý do (DocType chưa có, thiếu file JSON). Biên: tuần trùng, ràng buộc unique riêng (`db_insert` thô dưới tên khác → `UniqueValidationError`), trường bắt buộc, insert bằng Administrator.
4. Không uốn test, độc lập (STD-TEST-5/6): đạt. Quyền so nguyên tập ở cả JSON lẫn dòng DocPerm đã lưu (đúng 2 dòng); quyền bị từ chối kiểm theo role và theo bản ghi bằng `has_permission`, cộng một insert bằng Instructor phải ném `PermissionError`; unique kiểm tách khỏi trùng tên; bỏ `autoname` thì khẳng định tên đỏ; bỏ `reqd` thì test `MandatoryError` đỏ. Dòng test đặt năm 2001, user riêng, `addCleanup(frappe.db.rollback)` ở mọi test.
5. Lỗi và kiểm đầu vào (STD-ERR-1/2/5): không áp dụng.
6. Bảo mật: đạt. Mọi role đều không được ghi.
7. Hợp đồng và migrate (STD-DESIGN-3, STD-OPS-2): đạt. Chỉ thêm bảng mới, gỡ bằng xóa DocType.
8. Tên và style: đạt.
9. Phụ thuộc: không thêm.
10. Commit và tài liệu: đạt.

Nhãn, mô tả, tên mục (thiết kế không cho sẵn): không cái nào bịa nghĩa nghiệp vụ. Hai mục "Tuần và lúc tính", "Sáu KPI của tuần" là tiêu đề trung tính; nhãn dùng lại chữ của spec (A-14); mỗi mô tả nhắc lại một dòng của `design.md:461-468` hoặc AC-55 và khớp `kpi.py` (KPI 1 "chưa phản hồi = không đạt"; KPI 3 hành động của bot; KPI 5 đúng 72 h tính đạt, tuần lùi 3 ngày; KPI 6 đúng 5 ngày không tính, 0 khi không có phiếu; `week_end = start + 6`; `computed_at` theo ADR-033 QĐ 6). Mục `DOCTYPE_CONFIG` cùng bộ khóa với các mục dạng T19.

Findings:

- Không blocker, không major.
- minor | — | — | 3 small points: (a) STD-DOC-2 `erp_ai_kpi_week.json:35`: "Job KPI tuần ghi dòng lúc 08:00 thứ Hai cho tuần trước" is narrower than D-10. `run_weekly_kpi` also fills in up to 8 missing older weeks. Suggest adding "và các tuần còn thiếu, tối đa 8". Confirmed against the design. (b) STD-DOC-2 `erp_ai_kpi_week.json:62`: the median says "Rỗng khi mẫu 0", but `first_response_sample` counts every ticket created that week, while the median is also empty when tickets exist and none has a response yet (`kpi.py:61`). The wording comes straight from the design, so this is a gap for the designer, not a dev error. Confirmed. (c) STD-TEST-6 `test_erp_ai_kpi_week.py:47`: `_make_user` inserts fixed emails without checking whether they exist. Normally the rollback removes them, but if a run is killed mid-test before rollback, the next run fails with a duplicate error. Suggested fix: skip creating the user if it already exists. Suspected. | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Kết quả migrate trên site: index unique của `week_start` có thật trong `tabERP AI KPI Week` không (chỉ gián tiếp qua test `UniqueValidationError` xanh).
- Việc tạo User trong test có commit ở đâu đó và thoát khỏi rollback không.
- Mọi trường có nên `read_only` với chữ "hệ thống ghi" như ERP AI Log không: thiết kế không nói; mọi role đã không có quyền ghi.
- Reviewer không chạy test.

## Kết luận của tech-lead

- Chạy test và migrate: xem dòng progress của T43 trong `tasks.md` (một lần giữ khóa sau merge, có `migrate`; test `UniqueValidationError` xanh sau `migrate` từ cây đã merge là bằng chứng index unique có trên site).
- User của test: test_erp_ai_kpi_week chạy xanh hai lần liên tiếp trên cùng site (dev ở `3b966e6`, tech-lead sau merge) với email cố định, nên lần chạy đầu không để lại user (nếu để lại, lần sau đã đỏ vì trùng). Không còn mở.
- `read_only` cho mọi trường, câu mô tả trung vị (minor (b)) và câu mô tả job (minor (a)): chuyển designer, ghi ở dòng DỪNG lượt 15; không chặn tick.
- minor (c): không mở vòng sửa; dọn khi task kế chạm file test này (T58).
