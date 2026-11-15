Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 176 — FEAT-007 T176

- Diff: `git diff 09b5438..eb89c42` (nhánh `team/FEAT-007-task-176`; 2 commit `4a66e21` test, `eb89c42` mã; 2 file +13/−2, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn. Ghi trước khi merge.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `4a66e21`, một lần giữ khóa: `MIGRATE_EXIT=0`; `FAIL: test_direct_build_is_unknown_and_below_any_threshold (erp_ai.agent.test_classification.TestConfidencePct.test_direct_build_is_unknown_and_below_any_threshold)`; `AssertionError: 0 is not None`; `Ran 56 tests in 0.160s`; `FAILED (failures=1)`. GREEN, một lần giữ khóa: `MIGRATE_EXIT=0`; test_classification `Ran 56 tests in 0.170s OK`; test_routing `Ran 70 tests in 0.165s OK`; tools.test_route_ticket `Ran 29 tests in 12.984s OK`; tools.test_write_ticket `Ran 37 tests in 19.503s OK`; tests.test_architecture `Ran 185 tests in 16.517s OK`.

Các phép kiểm chính của reviewer (theo thứ tự lời giao, dùng 6/12 lượt):

1. Phạm vi và commit: chỉ hai file touchpoint; commit test `4a66e21` đứng trước commit mã `eb89c42`; hai tiêu đề đúng `type(scope): description (FEAT-007)`; không thân commit, không dòng ghi công AI.
2. `classification.py:48-49`: dòng trường `confidence_pct: int | None = None` và chú thích một dòng ngay trên khớp dòng Returns từng ký tự; `parse_classification`, `write_ticket.py` và các nơi dựng `Classification(...)` trực tiếp không đổi.
3. `test_classification.py:184-192`: test mới khớp dòng Expect (cùng lời dựng, `assertIsNone`, `assertTrue(policy.is_below_confidence(..., classification.CONFIDENCE_PCT_MIN, has_instructor=False, act_now=False))`); thay đổi khác duy nhất là thêm `policy` vào dòng import có sẵn; không khẳng định nào bị đổi, không dấu skip.
4. Test đỏ khi không có sửa, ở cả hai khẳng định: mặc định 0 làm `assertIsNone` đỏ (đúng RED `0 is not None`); `CONFIDENCE_PCT_MIN` là 0 (`constants.py:14`), `_known_pct(0)` trả 0, `0 < 0` sai nên khẳng định thứ hai cũng đỏ.
5. `None` ở đầu nhánh: `policy._known_pct(None)` trả `None`, `is_below_confidence` trả `pct is None or pct < threshold`, nên `None` đọc là "không biết, dưới ngưỡng" trừ khi có người ra lệnh và `act_now`. Không mã ngoài test nào đọc `Classification.confidence_pct` (chỉ `classification.py:49/91/92/112` của đường parse luôn cho số thật, và `policy.py:148/153` nhận `int | None`); không hàm tuần tự hóa dataclass chung nào (`asdict`, `vars`, `__dict__`) chạm `Classification`.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 1 small point: the test comment says "Point 1" where the design heading is "Điểm 1" | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Lint: kết quả pre-commit chỉ có trong ghi chú tiến độ, không có trong bằng chứng nguyên văn; reviewer tính dòng mã mới dài nhất 109/110 cột, không chạy gì.
- Mã thoát: `TEST_EXIT=0` có cả ở lần RED, nên mã thoát không phân biệt đỏ xanh; chỉ dòng `Ran … OK/FAILED` phân biệt, và chúng cho thấy đỏ rồi xanh.
- Dòng tiêu đề T79: chỗ sửa `depends: T78, T176` của thiết kế không nằm trong diff (quyết định 10:58 đã đổi thứ tự).

## Kết luận của tech-lead

- Merge `33b0970` trên `team/FEAT-007` (sau khi file này có verdict). Chạy test sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_classification `Ran 56 tests in 0.192s OK`, test_routing `Ran 70 tests in 0.159s OK`, test_route_ticket `Ran 29 tests in 13.525s OK`, test_write_ticket `Ran 37 tests in 20.699s OK`, test_architecture `Ran 185 tests in 16.695s OK`. Đọc theo dòng `Ran … OK`, không theo mã thoát.
- Lint: dev chạy `pre-commit run --files` trên hai file, qua. Sửa lại lúc 14:45: repo không cài hook pre-commit nào (`.git/hooks` chỉ có file mẫu), nên không commit nào "đi qua hook". Bằng chứng đứng được: `cmd.lint` cả cây @ `32fa2bb` (chứa T176) do một dev chạy: hook đỏ duy nhất là ruff-format trên `erp_ai/agent/knowledge.py` (của T177), hai file của T176 không bị hook nào sửa; sau khi T177 sửa, `cmd.lint` cả cây @ `ac8386b` (cùng cây với đầu nhánh `ed341b9`): 12 hook Passed, `LINT_EXIT=0`.
- Dòng tiêu đề T79: không phải khoảng trống; quyết định 10:58 (c) của team-leader giữ `depends:` của T79, T176 đứng sau T79 (dòng "Chèn 12" của khối T176).

## deferred

- minor (1): chú thích test ghi "Point 1" thay cho "Điểm 1" → không việc.
