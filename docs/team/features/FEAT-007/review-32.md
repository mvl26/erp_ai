Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 32 — FEAT-007 T32

- Diff: `git diff 33b0970..bd32c1d` (nhánh `team/FEAT-007-task-32`; 2 commit `bb10803` test, `bd32c1d` mã; 2 file +88, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn. Ghi trước khi merge.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên commit test `0466126` (nhánh nay mang `bb10803` là commit test: commit test được sửa bằng `--amend` sau lần chạy đỏ): `MIGRATE_EXIT=0`, `Ran 109 tests in 7.989s`, `FAILED (failures=4)`: `FAIL: test_raise_from_l0_not_passed_warns_and_saves`: `AssertionError: 0 != 1`; `FAIL: test_raise_from_l0_not_enough_sample_warns_for_every_higher_level` (after='L1', 'L2', 'L3'): `AssertionError: 0 != 1` mỗi ca. GREEN trên `bd32c1d`, một lần giữ khóa: `MIGRATE_EXIT=0`; test_erp_ai_setting `Ran 109 tests in 7.667s OK`; test_architecture `Ran 185 tests in 16.490s OK`. `pre-commit run --all-files` exit 0.

Các phép kiểm chính của reviewer (theo thứ tự lời giao, dùng 6/14 lượt):

1. Commit: commit test `bb10803` đứng trước commit mã `bd32c1d`; hai tiêu đề đúng `type(scope): description (FEAT-007)`, không dòng ghi công AI. Lần đỏ chạy trên `0466126`; chênh lệch `0466126` → `bb10803` là một khẳng định được nối về một dòng, nên bằng chứng đỏ vẫn áp cho commit test.
2. Controller (`erp_ai_setting.py:206-225`): `warn_level_raise_without_gate()` được gọi từ `on_update`; đọc mức cũ qua `get_doc_before_save()` và cả hai mức qua `policy.effective_level(..., over_budget=False)` (hàm này chỉ trả `settings.permission_level`), tên trường không xuất hiện trong controller nên D-7 / `POLICY_FIELDS` giữ; chỉ cảnh báo khi mức cũ là `L0`, mức mới có chỉ số trên `L0` trong `LEVELS`, và verdict khác `"Đạt"`; chữ `msgprint` khớp `design.md:323` chính xác, `title="Chưa đạt cửa L0 → L1"`, `indicator="orange"`; không gì ném nên A-8 giữ; chưa có bản lưu hoặc mức cũ rỗng thì trả về không cảnh báo (đúng: mức không đổi); module báo cáo chỉ import `policy` và `constants` nên không vòng import; không gì dưới `erp_ai/agent/**` import báo cáo (F-1 giữ).
3. Test (`test_erp_ai_setting.py:1017-1072`): đủ ba test của Expect cộng hai test thêm; lớp gọi `keep_agent_settings(self)` và rollback khi dọn; cửa được vá bằng một `GateResult` cố định (không dòng log, không đồng hồ), bản vá nhắm đúng module của controller; chữ chờ viết cứng, gồm 14 và 33/40; mỗi điều kiện có một test đỏ khi bỏ nó: phép kiểm mức cũ `L0` bởi `test_change_l1_to_l2_no_gate_warning`, mức mới ≥ `L1` bởi `test_stay_at_l0_no_gate_warning`, verdict bởi `test_raise_from_l0_passed_no_warning`; đột biến thành `== "Chưa đạt"` bị test `"Chưa đủ mẫu"` L1/L2/L3 bắt; các test "không cảnh báo" không rỗng nghĩa vì các test cảnh báo dùng cùng helper và đi từ đỏ sang xanh; không khẳng định có sẵn nào đổi, không dấu skip.
4. Lỗi: `l0_l1_gate` không có kiểu hỏng riêng (`_parse_labels` đã bắt `ValueError`); lỗi cơ sở dữ liệu sẽ nổi lên và hoàn tác lần lưu, đó là hỏng của chính site chứ không phải kiểu chặn theo chính sách mà A-8 loại, và không bị nuốt (STD-ERR-1).
5. Còn lại: không bí mật, không injection, quyền không đổi (truy vấn dùng `frappe.qb`, form chỉ System Manager dùng); không đổi hợp đồng, không phụ thuộc mới, tên theo kiểu của file.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 4 small points: (a) no test for the branch with no saved version (`get_doc_before_save()` is None), `erp_ai_setting.py:212`; (b) no test for the `level not in LEVELS` guard at `:215`; (c) `GATE_PASSED_VERDICT = "Đạt"` (`:89`) repeats the report's literal at `erp_ai_accuracy.py:60` instead of sharing one constant; (d) a database error raised by `l0_l1_gate` inside `on_update` rolls the save back, which is acceptable but neither documented nor tested | dev's call

Mục "không kiểm được từ diff" của reviewer:

- `msgprint` có hiện trên trình duyệt sau một lần lưu form thật không: test giả `frappe.msgprint`, cần kiểm tay trên UI.
- Các lần chạy đỏ/xanh và `pre-commit`: reviewer không chạy test.
- `l0_l1_gate` đọc mọi dòng `classify` không có mốc bắt đầu trong SQL; chỉ chạy khi lưu L0 → mức cao hơn, nhưng chi phí trên bảng log lớn chưa đo.

## Kết luận của tech-lead

- Merge `32fa2bb` trên `team/FEAT-007` (sau khi file này có verdict và T179 đã tick). Chạy test sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_erp_ai_setting `Ran 109 tests in 7.909s OK`, test_erp_ai_accuracy `Ran 39 tests in 4.123s OK`, test_architecture `Ran 185 tests in 16.622s OK`.
- pre-commit: `cmd.lint` cả cây @ `32fa2bb` do một dev chạy sau merge: hook đỏ duy nhất là ruff-format trên `erp_ai/agent/knowledge.py` (của T177); hai file của T32 không bị hook nào sửa.
- `msgprint` trên trình duyệt: profile `ui: false`, không có Playwright trong lượt build; chuyển `/team:verify` (kiểm tay AC-18 phần form), không chặn tick: lời gọi `frappe.msgprint` với `title`, `indicator` đã được test khẳng định.
- Chi phí `l0_l1_gate` trên bảng log lớn: hàm của T29 (đã merge), ngoài diff của T32; chuyển designer qua team-leader, không chặn.

## deferred

- minor (a), (b): thiếu test cho nhánh chưa có bản lưu và nhánh `level not in LEVELS` → `/team:clean` hoặc task kế chạm `TestLevelRaiseWarning`.
- minor (c): `GATE_PASSED_VERDICT = "Đạt"` lặp chữ của `erp_ai_accuracy.py:60` → `/team:clean` (gom một hằng).
- minor (d): lỗi cơ sở dữ liệu của `l0_l1_gate` trong `on_update` hoàn tác lần lưu, chưa ghi tài liệu → As-Built.
