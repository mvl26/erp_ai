Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 41 — FEAT-007 T41

- Diff: `git diff 66fc4afb47f2bc1727f845919304b94f733776d2..edde2c3` (đầu nhánh task khi merge; merge `0213915` trên `team/FEAT-007`)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 2); vòng 1 là design-defect, đã có phán quyết (3) của `design-w0-fixes-2.md`

## Vòng 1 — design-defect

- Range: `66fc4af..dc96b9a` (1 commit, 2 file mới, +147), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.agent.test_ops_data` `AttributeError: module 'erp_ai.agent.ops_data' has no attribute 'monthly_cycle'`, `Ran 5 tests in 0.056s FAILED (errors=31)`; GREEN `Ran 5 tests in 1.797s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.220s OK`.

### Phát hiện

design-defect | STD-DESIGN-2 | erp_ai/agent/ops_data.py:39 (`design.md:423`) | Thiết kế chỉ viết "đảo `category_mapping`" và không quyết trường hợp hai đầu mục dùng chung một `ticket_type`. Trường hợp đó có thể xảy ra: `classification._mapping_error` (ở `66fc4af`) kiểm khóa và kiểu, không kiểm `ticket_type` trùng. Trong mã, khóa đứng sau cùng theo thứ tự JSON của quản trị viên lặng lẽ thắng và đầu mục kia biến mất khỏi bảng đảo. Phép tra sẵn có `erp_ai/eval/run_eval.py:36-42` (`_expected_category`) làm ngược lại: khớp đầu tiên theo thứ tự A–F thắng. Vậy phần đánh giá độ chính xác và KPI của T45 / báo cáo ngày của T51 (gồm cả `c_missing_ba_note` chỉ dành cho C) sẽ xếp cùng một phiếu vào hai đầu mục khác nhau. Không test nào phủ trường hợp này, docstring cũng không nói. | Designer chọn một: (a) `validate_mapping` từ chối `ticket_type` dùng hai lần (cần thêm `classification.py` và test của nó vào touchpoints); (b) luật phân xử cố định dùng chung với `run_eval` (đứng trước theo thứ tự `CATEGORIES`), ghi vào docstring và có một dòng test va chạm.

minor | — | — | 2 điểm nhỏ: `ticket_row` không có type hint (`ops_data.py:40`); `test_ba_note_marker` chỉ ghim hằng | tùy dev

### Ghi nhận của reviewer

- AC-52 / ADR-033 QĐ 6 đạt: `daily_cycle(2026-11-17 02:00)` cho 2026-11-16; khóa tuần, tháng theo `design.md:420-422`.
- Test bắt các lỗi dễ gặp: `<` thành `<=` ở 08:00 (dòng đúng 08:00); bỏ điều kiện `weekday()==0` (dòng thứ Ba 02:00); bỏ điều kiện `day==1` (dòng 2/12 02:00); bỏ bộ lọc `ticket_type` rỗng (dòng E, F). Biên dùng 07:59:59.999999; có đổi năm và tháng Hai. `now` luôn được truyền vào; lớp test gọi `keep_agent_settings`.

### Review checklist (10)
1. đạt (điểm thiết kế ở trên) 2. đạt 3. đạt (RED trước; không skip) 4. đạt 5–9. không có gì để nêu (hàm thuần, file mới, không dependency) 10. đạt (`feat(agent): … (FEAT-007)`)

## Vòng 2 — approve (chấm lại cả range sau phán quyết)

- Range: `66fc4af..edde2c3` (2 commit, 3 file, +211/−1), đúng touchpoints sau chèn 2; `erp_ai/eval/run_eval.py` không có diff.
- Bằng chứng của dev: RED trên `dc96b9a` `FAIL: test_shared_ticket_type_earliest_category_wins (keys=['B', 'A', 'C'])` `AssertionError: {'Y': 'B', 'X': 'C'} != {'X': 'A', 'Y': 'B'}`, `Ran 7 tests in 0.731s FAILED (failures=2)`; `test_run_eval` `AssertionError: 'A' != 'C'`, `Ran 23 tests in 1.215s FAILED (failures=2)`; GREEN `test_ops_data` `Ran 8 tests in 0.038s OK`, `test_architecture` `Ran 112 tests in 3.257s OK`; `test_run_eval` trên nhánh task (tech-lead chạy lại riêng sau 3 lần dev dính `QueryDeadlockError` ở `TestRunEvalRun`) `Ran 23 tests in 0.646s OK`.
- Kết luận của reviewer: design-defect vòng 1 đã được giải quyết. `ops_data.py:49-53` duyệt `CATEGORIES` (import từ `erp_ai.constants`), giữ đầu mục gặp trước bằng `setdefault`, bỏ `ticket_type` rỗng và khóa ngoài `CATEGORIES`; docstring `:39-46` ghi hệ quả; `ops_data.py` chỉ import `datetime` và `erp_ai.constants`. Các đột biến (duyệt theo khóa mapping, gán đè, bỏ lọc rỗng, bỏ chốt `if not ticket_type`) đều có test đỏ; test khớp luật với `run_eval` phủ mapping va chạm, bản đảo khóa và `DEFAULT_CATEGORY_MAPPING`.

### Phát hiện

Không có blocker/major.

minor | — | — | 2 điểm nhỏ: `test_ops_data.py:128` `test_ba_note_marker` chỉ ghim hằng (từ vòng 1); `setUp` của `TestCycles` / `TestCategoryLookup` gọi `keep_agent_settings` cho hàm thuần | tùy dev

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trước GREEN ở cả hai module; biên 07:59:59.999999, đổi năm, tháng Hai, va chạm, rỗng, thiếu; không skip) 4. đạt (test sẵn có của `test_run_eval.py` chỉ đổi dòng import) 5. không áp dụng 6. không áp dụng 7. đạt 8. đạt 9. không áp dụng 10. đạt (`feat(agent)`, `fix(agent): … (FEAT-007)`)

### Phần kiểm của tech-lead (vòng 2)

- Sau merge `0213915`, tech-lead chạy từ worktree `feat-007`: `test_ops_data` `Ran 8 tests in 0.062s OK`, `test_run_eval` `Ran 23 tests in 0.565s OK`, `test_architecture` `Ran 112 tests in 3.240s OK`; `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`.
- `category_mapping` thật trên `miyano` có trùng `ticket_type` hay không: theo phán quyết (3) chỉ ảnh hưởng số liệu → báo team-leader, không chặn tick.
- deferred vòng 2: 2 điểm nhỏ ở trên; `QueryDeadlockError` ở `TestRunEvalRun` khi hai phiên chạy cùng lúc (nếu lặp lại khi site rảnh thì ghi `debt.md`, STD-TEST-7).

## Phần kiểm của tech-lead

- Dev đã tự nêu đúng điểm này trong báo cáo ("đầu mục liệt kê sau cùng thắng, không có test"). Tech-lead không chọn (a) hay (b): (a) mở rộng touchpoints của T41 sang `classification.py` (file T27 vừa sửa, đã merge).
- `team/FEAT-007-task-41` @ `dc96b9a` giữ nguyên, chưa merge. Task bị chặn theo: T45 (→ T46, T47), T50, T51 (→ T52–T54).

## Không kiểm được từ diff

| Mục | Ghi chú |
|---|---|
| `category_mapping` trên site `miyano` đã có `ticket_type` trùng chưa | Cần đọc dữ liệu thật; quyết định mức gấp của việc sửa thiết kế. Chuyển team-leader. |
| `cmd.test` cả bộ | Mốc kiểm. |

## deferred

- (minor, tùy dev) hai điểm nhỏ ở trên.
