Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 30 — FEAT-004 T30

- Diff: vòng 1 `git diff 25be823..6d90e79 -- erp_ai/agent/runner.py erp_ai/agent/test_agent_runner.py` (mã nhận từ ngoài quy trình); vòng 2 `git diff 34762ba..563d4c7` (1 commit, 2 file)
- Diff vòng 3: `git diff 1a82772..122fd4c` (nhánh `team/FEAT-004-task-30b`, 1 commit, 1 file, +10/-2)
- Vòng: 3 (max_rework=3)
- Verdict: approve (5 dòng `api_*` của `WRITE_TOOL_TARGETS`, `_action` đọc doctype và đường `get_unrestricted_tool_schemas` thuộc Amendment 2 / CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — request-changes (review E, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-2 | erp_ai/agent/runner.py:11,681 | `runner.py` import `erp_ai.agent.changes.transitions`; Ràng buộc ADR-012 cấm; kéo cả `process_runner` vào runner | gọi `write_entry(entry_type="change", trigger="change_action", change_step="propose", actor=AGENT_USER, change_proposal=..., ticket, run_id, instructor)` như design 4.1 bước 4 |
| major | STD-TEST-2 | erp_ai/agent/runner.py:681 | `log_step` không truyền `instructor`; test duy nhất (`test_agent_runner.py:1300`) chỉ kiểm `(change_step, actor)` | kiểm entry_type, trigger, ticket, run_id, instructor trên dòng |
| major | STD-TEST-2 | erp_ai/agent/test_agent_runner.py (chưa có) | Thiếu 2 test AC-11: `test_injection_without_instructor_gets_no_change_tools_and_no_proposal`, `test_model_claims_approved_after_proposing_zero_applies` | thêm cả hai |

minor | — | — | 1 điểm nhỏ: `PROPOSE_TOOLS` (runner.py:87) lặp tên tool vì `propose_change.PROPOSE_TOOL_NAMES` chưa có (STD-DESIGN-4) | tùy dev

## Vòng 2 — approve (`git diff 34762ba..563d4c7`)
- Phát hiện 1: ADDRESSED (`runner.py:11` không còn import `changes`; `runner.py:681-692` gọi `write_entry` đúng design 4.1 bước 4)
- Phát hiện 2: ADDRESSED (`runner.py:691` truyền `instructor=context.instructor`; `test_agent_runner.py:1525-1531` so với giá trị viết tay `PROPOSE_ROW_FIELDS`)
- Phát hiện 3: ADDRESSED (`:1533` dùng `latest_instructor` thật, mọi điều kiện cấp khác đều bật nên chỉ việc thiếu người ra lệnh giữ tool lại; `:1555` patch `frappe.enqueue` và `subprocess.Popen`, đỏ khi có duyệt, job, argv ghi hay commit; `assertTrue(argvs)` chứng minh lệnh git đọc của bộ chặn có chạy). Hai test này xanh ngay lần đầu vì mã đã có; reviewer xét từ mã test là đỏ được
- Phát hiện mới: không có blocker/major

## Vòng 3 — approve (sửa sau khi `cmd.test` đỏ trên nhánh đã merge, `git diff 1a82772..122fd4c`)
- Lỗi: trên `1a82772` (merge T25 và T30 cùng lượt), `ERROR: test_model_claims_approved_after_proposing_zero_applies` → `ValueError: not enough values to unpack (expected 1, got 0)` (tái hiện 2 lần: cả app và chạy riêng module trên site yên). Nguyên nhân do ghép hai task, không do riêng task nào: test của T30 viết trên nền tool còn nhận `edits[{old,new}]`; T25 đổi tool sang `find[]`/`replace[]` của design 3.1 nên lời gọi của test bị từ chối, không có đề xuất
- ADDRESSED: `test_agent_runner.py:1497-1498`, `1506-1513` gửi `find`/`replace`. Test 1 dùng `execute_tool` thật, được đúng 1 đề xuất `Chờ duyệt`; test chèn lệnh nay bị từ chối bởi kiểm cấp (`registry.py:170-172`) chứ không bởi tham số sai, tức chặt hơn trước; test dòng nhật ký vẫn giả `execute_tool`, chấp nhận vì nó phủ dòng `change`/`reason` của runner (AC-12)
- Phát hiện mới: không có blocker/major; 1 điểm nhỏ: test chèn lệnh chỉ kiểm `ok: False`, không kiểm lý do
- Bằng chứng của dev: RED trên nền `ERROR: test_model_claims_approved_after_proposing_zero_applies … line 1578 … ValueError: not enough values to unpack (expected 1, got 0)`; GREEN `Ran 73 tests in 15.518s` / `FAILED (failures=3)` (3 ca nhiễu `auto_assign_enabled=1` đang lưu)

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `test_propose_writes_one_change_row_besides_reason … AssertionError: Lists differ: [... 'AICHG-00001', '43069', 'ERPAI-TEST-run'] != [... '0f83dcdee4e84fe19476f9d6cb6b0ab7']` (mã cũ lấy `run_id` từ đề xuất, không từ lượt chạy)
- GREEN: module `Ran 73 tests in 20.639s` / `FAILED (failures=3)`, 3 ca đỏ là `TestRunnerL1Classification` đọc `auto_assign_enabled=1` đang lưu (không thuộc diff); test_architecture `Ran 112 tests in 3.123s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- 3 ca đỏ của module có đỏ trên nền không: có khi chạy với cài đặt đang lưu; `cmd.test` với cài đặt tạm để trống trên `34762ba` và `db0ce2c` xanh cả module (dòng progress round 51, 52 của `tasks.md`).
- Luật T31 (transitions chỉ controller và `changes` import) phải xanh trên `runner.py` mới: kiểm ở T31 lần 2.

## deferred
- Sau khi T25 merge: `runner.PROPOSE_TOOLS` nên dùng `propose_change.PROPOSE_TOOL_NAMES` (STD-DESIGN-4) → gộp vào task M4 của CHG-001 (cùng sửa `runner.py`).
