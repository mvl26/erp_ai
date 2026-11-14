Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 28 — FEAT-004 T28

- Diff: vòng 1 `git diff 25be823..6d90e79 -- erp_ai/agent/tools/registry.py erp_ai/agent/tools/test_registry.py` (mã nhận từ ngoài quy trình); vòng 2 `git diff 1a82772..4a045f9` (1 commit, 1 file, +54/-9)
- Vòng: 2 (max_rework=3)
- Verdict: approve (hai hàm cấp `_unrestricted_specs`, `get_unrestricted_tool_schemas` thuộc biện pháp M4 của CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — request-changes (review E, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | erp_ai/agent/tools/test_registry.py:393 | Assertion đếm tool bị sửa 11 → 21 theo hành vi chưa có spec (site_api); spec ghi 14 | kiểm 14; số của CHG-001 vào test mới sau amendment |
| major | STD-TEST-2 | erp_ai/agent/tools/test_registry.py (chưa có) | Thiếu test đếm của Expect; `test_all_specs_collects_tools_of_each_module` dựng giả từ chính `TOOL_MODULES` nên không chứng minh `propose_change` có trong danh sách | thêm test với danh sách module viết tay |
| major | STD-TEST-8 | erp_ai/agent/tools/registry.py:127 | Dòng kiểm kiểu `"object"` mới không có ca từ chối | test gửi list hoặc chuỗi cho luật object nhận `tham số không hợp lệ` |

minor | — | — | `test_every_real_handler_runs_without_committing` chấp nhận từ chối của bộ chặn cho hai tool file nên đường insert và comment không chạy dưới bộ canh commit | tùy dev

## Vòng 2 — approve (`git diff 1a82772..4a045f9`)
- Phát hiện 1: ADDRESSED bởi spec Amendment 2, N-3 mục 18–19: 21 = 11 nền + 3 đề xuất + 4 công cụ bản ghi + 3 toàn quyền (`test_registry.py:424`)
- Phát hiện 2: ADDRESSED (`test_registry.py:385-405` `TOOLS_BY_MODULE` viết tay; `:426-435` kiểm `TOOL_MODULES == tuple(TOOLS_BY_MODULE)`, tên tool từng module, thứ tự và số 21; tên test theo 21)
- Phát hiện 3: ADDRESSED (`test_registry.py:201-208`: `["a"]`, `"a"`, `1`, `None` bị từ chối, dict được nhận)
- Điểm nhỏ: ADDRESSED (`:540-542`, `:587`, `:616-617`: `GitSandbox` với `custom_app`, cả hai tool file phải trả `ok` và có bản ghi đề xuất)
- Assertion bị bỏ (từ chối `APP_NOT_ALLOWED` cũ ở `:602-604`): không vi phạm STD-TEST-5; cách dựng test đổi và assertion mới chặt hơn; đường từ chối vẫn có test ở `test_propose_change.py:243`, `test_change_guard.py:118`, `test_apply_job.py:215,308`
- Phát hiện mới: không có

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Test mới xanh trên mã có sẵn; mỗi test được chứng minh đỏ bằng thay đổi tạm rồi bỏ: `AssertionError: Tuples differ: ('erp[91 chars]_ai.agent.tools.site_api') != (…'erp_ai.agent.tools.propose_change', 'erp_ai.agent.tools.site_api')`; `{'ok': True, 'echo': {'values': ['a']}, …} != {'ok': False, 'reason': 'tham số không hợp lệ: values'}`; `FAIL: test_every_real_handler_runs_without_committing … AssertionError: commit in tool test`
- GREEN: `Ran 35 tests in 2.904s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Chữ Returns/Expect của T28 trong `tasks.md` còn ghi "11 → 14" và `test_all_specs_count_is_14`: tech-lead đã thêm dòng "Sửa theo Amendment 2" dưới T28 (21 tool).

## deferred
- M4 (CHG-001): gộp đường cấp thứ hai; ma trận cấp theo ô toàn quyền.
