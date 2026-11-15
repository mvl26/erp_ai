Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 55 — FEAT-007 T55

- Diff: `git diff f7da325..c55e54a` (nhánh `team/FEAT-007-task-55`, 2 commit `9f48359`, `c55e54a`); diff sửa vòng 2: `git diff 9f48359..c55e54a`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng (chỉ đọc): `git log --oneline f7da325..9f48359`, `git diff --stat f7da325..9f48359`, `git diff f7da325..9f48359`, `git diff --check f7da325..9f48359` (exit 0); `git show -s --format='%an%n%B' 9f48359`; `git show 9f48359:` cho `erp_ai/tasks.py` (`recompute_monthly_spend`), `erp_ai_accuracy.py` (`_validate_dates`), `erp_ai/test_utils.py` (`make_log_entry`), `erp_ai_log.json`, `erp_ai_setting.json` (`spent_this_month_usd`); `git ls-tree -r --name-only 9f48359 erp_ai/erp_ai_agent/report/`; `git grep` tìm helper tháng, chỗ import `_validate_dates`, chỗ dùng năm `2031`. Đọc mã Frappe 15.126.1: `frappe/desk/query_report.py:202-233`, `frappe/public/js/frappe/views/reports/query_report.js:443-445`, `report_filter.json`, `frappe/database/mariadb/database.py:167,180`, `frappe/database/schema.py:10-14,197-203,346-353`. Hai lệnh không phải git, chỉ đọc (`python3 -c` in `permissions` của `erp_ai_log.json` từ stdin, `od -c` so byte `Phiếu`/`Lần chạy`); hook đã nhắc. Tài liệu: `tasks.md` dòng 1-25 và khối T55; `design.md:470-490` (3.6.6), `:282`, `:516`, `:688-689`; `design-w0-fixes.md:153,249,256,344-345`; `spec.md:182` (AC-20), `:234` (AC-60); các addendum không đổi AC-60.
- Bằng chứng của dev: RED `DoesNotExistError: Report ERP AI Cost not found`, `KeyError: 'Tổng tháng này (ERP AI Log)'`, `Lists differ: [] != ['ticket', 'runs', 'cost_usd']`, `ValidationError not raised` ×6, `Ran 5 tests in 0.338s FAILED (failures=8, errors=2)`. GREEN một lần giữ khóa sau migrate: `test_erp_ai_cost` `Ran 5 tests in 0.979s OK`; `test_architecture` `Ran 112 tests in 3.485s OK`.

### Lớp 1 (khớp spec)

- Đủ: Script Report `ERP AI Cost` có `ref_doctype` ERP AI Log, `roles` System Manager và ERP AI Instructor, `is_standard` Yes, module `ERP AI agent`. Bộ lọc `from_date`, `to_date` (bắt buộc), `group_by` = `Phiếu\nLần chạy` (byte trong JSON và `.py` trùng nhau, cùng NFC). Dòng theo phiếu: `ticket`, `runs` (`Count(run_id).distinct()`), `cost_usd` (Float, precision 6). Dòng theo lần chạy: `run_id`, `ticket`, `started_at` (min `creation`), `cost_usd`. `report_summary` đủ ba giá trị theo `design.md:482`. `execute` kiểm quyền phía server bằng `has_permission(LOG_DOCTYPE, "report", throw=True)`. Đủ ba test của Expect; AC-60 dùng 3 phiếu × 4 lần chạy, tổng tính tay, so bằng nhau ở 6 chữ số; AC-20 dùng ba tài khoản.
- Không thừa: 4 file, đúng touchpoints; test thứ năm và thứ sáu là ca biên và ca lỗi (STD-TEST-8). Không hiểu sai.

### Đánh giá 10 điểm dev tự quyết

1. `group_by` bắt buộc, giá trị lạ → `ValidationError`: khớp `design.md:482`. Đạt.
2. Bộ lọc khai trong JSON, không `.js`: Frappe 15.126.1 hỗ trợ (`query_report.py:233`, `query_report.js:443-445`). Đạt, nhưng không test nào ghim (major dưới).
3. Sắp dòng phiếu, "(không gắn phiếu)" ở cuối, gộp NULL với rỗng: đúng "rỗng → nhãn"; bỏ `IfNull` → 5 dòng, đỏ. Đạt.
4. Sắp dòng lần chạy theo `started_at` rồi `run_id`; phiếu lấy `Max(ticket)`: thiết kế để ngỏ, hợp lý; tie-break và `Max` chưa có ca (minor, deferred).
5. `execute(filters, now=None)`: khớp quy ước "truyền `now`". Đạt.
6. "Tháng này" là tháng lịch của `now`: ghim bằng ca `other_month`. Đạt.
7. Ba giá trị summary là chuỗi 6 chữ số, datatype `Data`: hợp lý; định dạng chuỗi chưa được ghim (minor).
8. `Decimal(str(float)).quantize(1e-6)`: đúng (`decimal(21,6)`, Frappe đổi NEWDECIMAL sang float). Đạt.
9. Import `_validate_dates` của báo cáo `erp_ai_accuracy`: dùng lại đúng STD-DESIGN-4, nhưng ràng buộc ngầm vào hàm `_` của module khác (minor, deferred).
10. Biên tháng chép công thức của `tasks.recompute_monthly_spend`: lặp logic; tính ngang nhau được ghim bằng decoy ở hai mép tháng. Gộp phải sửa `tasks.py`, ngoài touchpoints (minor, deferred).

### Test đỏ được không

- Khoảng ngày: mép đầu và mép cuối đều có dòng mẫu; đổi `<` thành `<=` hoặc bỏ `+1 ngày` → đỏ. Tổng tháng: decoy trong tháng ngoài khoảng và ngoài tháng; lấy tháng theo khoảng ngày → đỏ. Summary "đã chi": ca cũ (`1.234567` trước job) chứng giá trị đọc từ Setting. `runs`: bỏ `distinct` → 8 thay vì 4. Quyền: ca Agent gọi thẳng `execute` cô lập `has_permission`; ca `run_report` của Instructor ghim `roles`; `sorted(roles)` ghim tập role. Số tính tay kiểm lại: T1 0.922472, T2 1.722480, T3 2.522488, khoảng 5.167445, tháng 17.167450. Độc lập (STD-TEST-6): rollback, chặn commit, `keep_agent_settings`, tháng 3/2031 riêng.

### Phát hiện (chỉ blocker/major)

major | STD-TEST-2 | erp_ai/erp_ai_agent/report/erp_ai_cost/test_erp_ai_cost.py:221-227 (đối chiếu erp_ai_cost.json:7-28) | Mảng `filters` của JSON là nguồn bộ lọc duy nhất trên giao diện (không có `.js`) và là một mục Returns của T55, nhưng không test nào đọc `report.filters`. Mọi test đều truyền `filters` thẳng vào `execute`/`run_report`. Xóa mảng `filters`, bỏ `mandatory`, hoặc để `options` lệch khỏi `GROUP_BY_OPTIONS` (gõ sai, khác dạng Unicode) thì test vẫn xanh, trong khi trên desk báo cáo hoặc không có ô lọc, hoặc luôn ném `ValidationError` | Trong `test_access_three_accounts` (hoặc một test riêng), khẳng định bằng literal `[(f.fieldname, f.fieldtype, f.mandatory, f.options, f.default) for f in report.filters] == [("from_date", "Date", 1, None, None), ("to_date", "Date", 1, None, None), ("group_by", "Select", 1, "Phiếu\nLần chạy", "Phiếu")]` (lấy đúng giá trị DB trả về cho các cột rỗng), và thêm `report.filters[2].options.split("\n") == list(GROUP_BY_OPTIONS)` | confirmed

minor | — | — | 4 điểm nhỏ: (1) STD-TEST-8: tie-break `run_id` khi hai lần chạy cùng `started_at` chưa có ca, và `Max(ticket)` chưa gặp lần chạy nào có nhiều giá trị `ticket`. (2) STD-TEST-2: test bọc `_six()` quanh giá trị summary và `cost_usd`, nên quyết định "chuỗi đúng 6 chữ số" không được ghim; "Tổng trong khoảng" chỉ được khẳng định ở chế độ `Phiếu`. Nên so chuỗi thô `"5.167445"`, `"17.167450"` và khẳng định summary ở cả chế độ `Lần chạy`. (3) STD-DESIGN-4: biên tháng và câu `Sum` chép lại từ `recompute_monthly_spend` (erp_ai_cost.py:109-120). (4) Import helper riêng `_validate_dates` của `erp_ai_accuracy` (erp_ai_cost.py:10) | tùy dev / tech-lead

### Review checklist (10)

1. **chưa đạt** (đủ AC-60 và AC-20 cho phần dữ liệu; mục Returns "bộ lọc" chưa có test, major) 2. đạt (4 file mới, đúng touchpoints) 3. đạt (RED thật cho 5 test; ca biên và ca lỗi; không skip/xfail/only) 4. đạt 5. đạt (kiểm bộ lọc ở biên báo cáo) 6. đạt (`frappe.qb` có tham số; quyền phía server; chỉ hiện mã phiếu) 7. đạt (Report mới, JSON chuẩn) 8. đạt 9. không có phụ thuộc mới 10. đạt (`feat(report): … (FEAT-007)`, không trailer AI)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Sau merge vào `team/FEAT-007` (đã có T31 `a3bddb8`, T12 `5f64531`): `cmd.migrate` rồi `cmd.test_one` cho `test_erp_ai_cost.py`, `test_architecture.py`, `test_erp_ai_accuracy.py` trong một lần giữ khóa site | |
| Site `miyano` không có Custom Role nào cho Report "ERP AI Cost" ghi đè `roles` của JSON | |
| Trên desk, báo cáo mở ra với 3 ô lọc từ JSON, `group_by` mặc định `Phiếu`, summary hiện 6 chữ số (để `/team:verify` hoặc Playwright kiểm) | |
| Site không có dòng ERP AI Log đã commit trong tháng 3/2031 (test giả định tháng đó trống) | |

## deferred

- (câu hỏi cho designer) Một `run_id` có nhiều giá trị `ticket` thì cột `ticket` của dòng lần chạy lấy giá trị nào? Mã đang lấy `Max`; `design.md:482` không nói.
- (minor, STD-DESIGN-4) Gộp biên tháng và tổng `cost_usd` theo tháng thành một helper dùng chung với `tasks.recompute_monthly_spend`; phải sửa `tasks.py`, ngoài touchpoints của T55.
- (minor) Chuyển `_validate_dates` sang module dùng chung cho các báo cáo (KPI Weekly sẽ cần).
- (minor, STD-TEST-8) Ca tie-break `run_id` khi hai lần chạy cùng `started_at`.

## Vòng 2 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline 9f48359..c55e54a`, `git diff --stat 9f48359..c55e54a`, `git diff 9f48359..c55e54a`, `git diff --check 9f48359..c55e54a` (exit 0), `git show -s --format='%an%n%B' c55e54a`; `git show c55e54a:` cho `erp_ai_cost.py` (`GROUP_BY_OPTIONS`, `:14`), `erp_ai_cost.json` (`filters`, `:7-28`), `test_erp_ai_cost.py`. Không chạy bench hay test.
- Range sửa: 1 commit `c55e54a` `test(report): pin the ERP AI Cost JSON filters and the raw 6-place summary strings (FEAT-007)`, không trailer AI; chỉ 1 file test (+21/−8) trong touchpoints. Mã `.py` và JSON không đổi.
- Bằng chứng của dev: RED theo đột biến (bỏ `"mandatory": 1` của `group_by`, migrate): `Lists differ: … ('group_by', 'Select', 0, …) != … ('group_by', 'Select', 1, …)`, `Ran 5 tests … FAILED (failures=1)`. GREEN sau khi trả JSON về và migrate: `test_erp_ai_cost` `Ran 5 tests in 0.899s OK`, `test_architecture` `Ran 112 tests in 3.233s OK`.

### Phát hiện vòng 1

- major STD-TEST-2 `test_erp_ai_cost.py:221-227`: **ADDRESSED** tại `test_erp_ai_cost.py:230-239` @ `c55e54a`: `:231-238` so literal danh sách `(fieldname, fieldtype, mandatory, options, default)` của `report.filters` với 3 bộ lọc; `:239` so `options.split("\n")` với `list(GROUP_BY_OPTIONS)`. Đột biến đọc theo mã đều đỏ: xóa mảng `filters`, bỏ `mandatory` (khớp RED của dev), gõ sai `options`, đổi `default`, đổi thứ tự bộ lọc; JSON và `.py` lệch dạng Unicode → `:239` đỏ.
- minor (2) vòng 1: đã làm (`:167-170` chuỗi thô `"5.167445"` ở cả hai chế độ; `:178-179`, `:186-187`, `:192-193` chuỗi thô `"1.234567"`, `"17.167450"`, `"13.000000"`); chặt hơn bản dùng `_six()`, không khẳng định cũ nào bị nới.
- minor (1), (3), (4) vòng 1: chưa làm, tùy dev, không chặn.

### Phát hiện mới (chỉ blocker/major)

Không có.

### Review checklist (10), phạm vi diff sửa

1. đạt (mục Returns "bộ lọc" đã có test) 2. đạt 3. đạt (RED bằng đột biến có trước GREEN; không skip/xfail/only) 4. đạt 5. không áp dụng 6. không áp dụng 7. đạt (JSON không đổi) 8. đạt (import `GROUP_BY_OPTIONS`, không chép lại) 9. không có phụ thuộc mới 10. đạt (`test(report): … (FEAT-007)`)

### deferred (vòng 2)

- Giữ nguyên các mục deferred của vòng 1 (câu hỏi `Max(ticket)` cho designer; helper biên tháng dùng chung; `_validate_dates` dùng chung; ca tie-break `run_id`).

### Kết luận của tech-lead trước khi tick (2026-11-14, sau merge `37a5f51`)

- Test sau merge trên `team/FEAT-007` @ `37a5f51`, một lần giữ khóa site: `cmd.migrate` exit 0; `test_erp_ai_cost` `Ran 5 tests in 0.949s OK`; `test_architecture` `Ran 112 tests in 3.405s OK`; `test_erp_ai_accuracy` `Ran 39 tests in 4.081s OK` (lo ngại của dev ở vòng 1 hết khi nhánh có T31); `test_erp_ai_setting` `Ran 53 tests in 2.357s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- Custom Role cho Report "ERP AI Cost" trên site: không truy vấn riêng; `test_access_three_accounts` xanh sau merge trên `miyano`; để `/team:verify` kiểm trên màn hình.
- 3 ô lọc trên desk, `group_by` mặc định `Phiếu`, summary 6 chữ số: mảng `filters` nay được ghim bằng test; phần màn hình để `/team:verify`.
- Tháng 3/2031 trống trên site: tổng tháng tính tay khớp ở GREEN sau merge nên đang trống.
- Trạng thái site: ở vòng 2 dev chạy `bench execute frappe.reload_doc` (`force`) để trả Report về JSON đã commit sau đột biến; lệnh này ngoài các ô `cmd.*`, đã báo team-leader. Lần `migrate` sau merge của tech-lead chạy trên cây đã merge và test xanh.
- Số vòng: 2 (vòng 1 `request-changes`, vòng 2 `approve`).
