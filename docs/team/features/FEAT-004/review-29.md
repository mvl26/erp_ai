Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 29 — FEAT-004 T29

- Diff: vòng 1 `git diff 25be823..6d90e79 -- erp_ai/agent/runner.py erp_ai/agent/test_agent_runner.py` (mã nhận từ ngoài quy trình); vòng 2 `git diff a742cd8..410c58c` (1 commit, 1 file, +110; merge `34762ba`)
- Vòng: 2 (max_rework=3)
- Verdict: approve (phần trong spec gốc; phát hiện 3 thuộc phần CHG-001, xem deferred)

## Vòng 1 — request-changes (review E, mã nhận về)
Lớp 1: `change_settings`, `ToolContext(change_enabled, allowed_apps)`, bộ cấp và `change_tools=grants_change_tools(...)` có. Thêm ngoài spec: đường cấp thứ hai (`get_unrestricted_tool_schemas`) và hai cờ prompt.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/test_agent_runner.py (chưa có) | Thiếu 2/3 test của Expect (`test_switch_off_run_sends_base_tools_and_prompt`, `test_over_budget_l3_drops_change_tools`); AC-2 chưa có test | thêm cả hai, so đúng tên tool và đúng `system` với `build_reason_system(...)` |
| major | STD-TEST-2 | erp_ai/agent/runner.py:597 | Thiếu `test_prompt_variant_follows_grant_result`; đổi thành `change_tools=context.change_enabled` vẫn xanh; `allowed_apps=change.allowed_apps` (runner.py:177) chưa được kiểm | thêm assertNotIn `CHANGE_TOOLS_BLOCK` cho L3 không người ra lệnh và L2 bật công tắc; chụp `allowed_apps` |
| major | STD-DESIGN-2 | erp_ai/agent/runner.py:184-199 | Bật ô toàn quyền thì danh sách tool không còn khớp AC-1, AC-2 của T23/T29; vượt ngân sách L3 → L1 vẫn giữ 7 tool `api_*` | chờ amendment CHG-001 rồi ghim kết quả |

## Vòng 2 — approve (re-review theo phạm vi, `git diff a742cd8..410c58c`)
- Phát hiện 1: ADDRESSED (`test_agent_runner.py:1386-1412`; thêm ca biên `spent == budget` ở :1414 khớp phép so `>` ở `policy.py:75`)
- Phát hiện 2: ADDRESSED (`test_agent_runner.py:1421-1451`; mỗi vế của điều kiện ba vế có một ca từ chối; `allowed_apps` ghim `("frappe", "hrms")`)
- Phát hiện 3: KHÔNG giao dev (phần giữ lại chờ CHG-001); còn nguyên: `runner.py:178`, `:587-590` chưa đổi; test mới đặt `unrestricted_enabled=0`
- Phát hiện mới: không có blocker/major

minor | — | — | 2 điểm nhỏ: `:1394` `assertNotIn("propose_file_change")` lặp phép so danh sách ở trên; ca được cấp (`:1426-1427`) chỉ ghim phần đầu và các tool đề xuất | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Test mới xanh ngay trên mã có sẵn; mỗi test được chứng minh đỏ bằng thay đổi tạm ở `runner.py` rồi bỏ: `Lists differ: [...'create_task', 'propose_file_change', 'propose_new_fil...] != [...'create_task']`; `AssertionError: 'L3' != 'L1'`; `'SỬA CODE VÀ LỆNH BENCH …' unexpectedly found`; `Tuples differ: () != ('frappe', 'hrms')`
- Module: `Ran 70 tests in 15.934s` / `FAILED (failures=3)`, 3 ca đỏ là `TestRunnerL1Classification` đọc `auto_assign_enabled=1` đang lưu của site (không thuộc diff)
- `cmd.test` trên `34762ba` (hai cài đặt tạm để trống): `Ran 1245 tests in 294.045s` / `FAILED (errors=2)`, cả 2 là `QueryDeadlockError` (dev khác chạy `cmd.test_one` cùng lúc trên site chung) ở `test_runner_routing` và `test_route_ticket`; chạy lại riêng hai module: `Ran 62 tests in 33.948s` / `OK`, `Ran 29 tests in 13.997s` / `OK` → xanh

## Không kiểm được từ diff (tech-lead xử lý)
- 3 ca đỏ của `TestRunnerL1Classification` có đỏ trên `a742cd8` không: có khi chạy với cài đặt đang lưu; `cmd.test` với cài đặt tạm để trống thì cả module xanh (dòng trên).

## deferred
- CHG-001 (ADR-023 QĐ 4, biện pháp M4 của `docs/team/features/CHG-001/arch-impact.md`): gộp đường cấp thứ hai vào bảng cấp, rồi ghim danh sách tool cho ca "vượt ngân sách khi toàn quyền bật". Cần task mới (`/team:plan --insert`).
