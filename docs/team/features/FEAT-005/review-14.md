Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 14 — FEAT-005 T14

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 79ad5d0..0a7ca58` (nhánh `team/FEAT-005-task-14`, 3 commit, chỉ `erp_ai/tests/test_architecture.py`; vòng 1 `79ad5d0..41ab1c1` +665/−3, vòng 2 `41ab1c1..c9ca535` +136/−92, vòng 3 `c9ca535..0a7ca58` +41/−5); merge `8898f3c`
- Vòng: 3 (`max_rework=3`; mỗi vòng một lỗi khác nhau, không lỗi nào lặp hai vòng)
- Verdict: approve (vòng 3); vòng 1 và vòng 2 request-changes

## Vòng 3 — approve (`c9ca535..0a7ca58`, chấm lại có phạm vi)

- major STD-TEST-2 của vòng 2: ADDRESSED. `test_architecture.py:4200`: luật gọi `_string_texts(function, docstrings, scan, TASKS_FILE)` nên giải được hằng; `:4201-4208` thêm phép quét nút Name/Attribute trần trỏ tới hằng cấp module. Hai ca bắt mới (`:5031-5046`), mỗi ca đỏ nếu bỏ đúng đường của nó: job đọc `CUTOFF_SQL` không có chuỗi bao quanh (chỉ đường tên trần bắt); helper dùng f-string `{CUTOFF}` (chỉ `_string_texts` có giải hằng bắt).
- major STD-DESIGN-5 của vòng 1: vẫn ADDRESSED. Luật chỉ buộc `_reached_functions(..., PRIVILEGE_JOB_FUNCTION)`; ca "không vi phạm" cho `frappe.utils.now()` và chuỗi "now" còn nguyên (`:5062-5063`); ca mới (`:5064-5072`): hằng có `NOW()` chỉ job khác đọc thì không bị bắt.
- Luật có từ trước T14: không đổi. `check_privilege_job_reads_no_other_clock` không có ở `79ad5d0`; vòng này chỉ sửa luật đó và test của nó.
- minor vòng 2: `QUERY_BUILDER_NOW` khớp theo tên cuối: chưa làm; dòng docstring dài: đã làm (`:4176` còn 110 cột).
- Phát hiện mới: không có blocker/major. minor | — | — | 2 điểm nhỏ: (1) hằng là tuple hoặc dict chứa `NOW()` vẫn lọt (`_string_shape` trả UNKNOWN_PIECE cho vật chứa; `QUERIES["stale"]` trong job qua được; bản quét cả file của vòng 1 bắt được; `tasks.py:27,45` đã có hằng tuple và dict); (2) chưa có test cho phép loại trùng `id(node) not in in_texts` (`:4206`) | tùy dev
- Bằng chứng của dev vòng 3: RED trước khi sửa bộ quét: `FAIL … (case='module constant with NOW() read by the job')`, `(case='module constant with NOW() in an f-string of a helper')`, `AssertionError: 0 not greater than 0 : scanner missed the violation`, `Ran 179 tests in 13.299s` / `FAILED (failures=2)`; đột biến `tasks.py` thật → `"tasks.py:283: _check_privilege_escalation_locked: SQL clock in 'select NOW()' (ADR-024)"`, `Ran 179 tests in 13.548s` / `FAILED (failures=1)`; GREEN `Ran 179 tests in 13.639s` / `OK`.

## Vòng 2 — request-changes (`41ab1c1..c9ca535`, chấm lại có phạm vi)

- major STD-DESIGN-5 của vòng 1: ADDRESSED (`:4021`, `:4042-4050`, `:4174-4204`; `frappe.utils.now` và nhánh `^\s*now\s*$` đã bỏ, `:4022-4024`).
- Luật có từ trước T14 không đổi (STD-TEST-5, STD-STYLE-4): `_change_link_shapes` (`:3805-3809`) trả cùng kết quả; `assertCaught` chỉ được dùng lại; `_text_lines` và phép đếm dòng VERSION_JS tính cùng tập; giới hạn `RESOLVE_DEPTH`=20 không che gì.
- major | STD-TEST-2 | erp_ai/tests/test_architecture.py:4198-4202 | Bản quét hẹp để lọt một ca ADR-024 mà vòng 1 bắt được. Nó chỉ gộp chuỗi bên trong thân FunctionDef và dùng NO_CONSTANTS_SCAN, nên SQL `NOW()` nằm trong hằng cấp module của tasks.py bị sót khi job đọc nó (vd. `CUTOFF_SQL = "… creation <= NOW()"` ở cấp module, `frappe.db.sql(CUTOFF_SQL)` hoặc `f"…{CUTOFF}"` trong job). tasks.py:27-46 phần lớn là hằng cấp module. | Truyền `GitScan(sources), TASKS_FILE` cho `_string_texts` trong luật này, thêm một ca bắt có hằng chứa `NOW()` được job đọc. Luật 7 (4237) có cùng lỗ hổng (deferred)
- minor | — | — | 2 điểm nhỏ: `QUERY_BUILDER_NOW` khớp mọi lời gọi có tên cuối là `Now`, bất kể module; dòng docstring ở 4176 dài hơn các dòng khác | tùy dev
- Bằng chứng của dev vòng 2: với mẫu mới trước khi sửa `Ran 179 tests … FAILED (failures=9)`, vd. `"tasks.py:22: SQL clock in 'now' (ADR-024)"`; đột biến `tasks.py` thật → `'tasks.py:274: check_privilege_escalation reads the clock with datetime.datetime.now() (ADR-024)'` / `FAILED (failures=1)`; GREEN `Ran 179 tests in 13.292s` / `OK`.

## Vòng 1 — request-changes (`79ad5d0..41ab1c1`)

Lớp 1: hai test kỳ vọng có mặt; cả 5 dòng Ràng buộc của ADR-024 có bộ kiểm chạy xanh trên cây thật; luật tên tool kiểm từng tên trong `WRITE_TOOL_TARGETS`, không kiểm chuỗi con `api_`. Chỉ `test_architecture.py` đổi. 3 dòng bị xóa là chữ docstring của module (không đổi phép khẳng định nào, STD-TEST-5 không chạm). Import `erp_ai.agent.runner` trong tiến trình là có lý do (`GENERIC_WRITE_TOOLS` tính từ `WRITE_TOOL_TARGETS`, `literal_eval` không đọc được). 668 dòng = 8 bộ kiểm + 2 test với 39 mẫu vi phạm, cùng mật độ với luật F4-T68, cân xứng. Mỗi mẫu vi phạm chạy trong subTest riêng với mảnh thông điệp riêng.

- major | STD-DESIGN-5 | erp_ai/tests/test_architecture.py:4012-4013,4166 | Luật đồng hồ phủ rộng hơn ADR-024 và gắn nhãn "(ADR-024)". Ràng buộc (dòng 66) và Expect của T14 chỉ áp cho job cảnh báo, chỉ nêu `datetime.now`, `utcnow`, `NOW()`. Luật lại: quét cả `tasks.py` (buộc luôn `recompute_monthly_spend`, `reprobe_exhausted_keys`); cấm thêm `frappe.utils.now()` (cùng đồng hồ với `now_datetime`); bắt mọi chuỗi đúng bằng `"now"`. | Giới hạn quét ở `check_privilege_escalation` và các hàm `tasks.py` nó tới, như luật 7; bỏ `frappe.utils.now` và nhánh `^\s*now\s*$`, hoặc nhờ designer thêm vào ADR-024
- minor | — | — | 5 điểm nhỏ: (a) ca "SQL NOW() nối chuỗi" (:4982) bị hằng `"NOW()"` trần bắt, không thử được phép gộp `+`; (b) `_folded_string`/`_string_texts` lặp `_string_shape`/`_change_link_shapes` (STD-DESIGN-4); (c) luật Version nạp `.html`, `.json` nhưng chỉ kiểm `.py`, `.js`; (d) docstring module thiếu `from erp_ai.constants import …`; (e) `assertRuleSamples` lặp `assertCaught` | tùy dev (vòng 2 đã làm a, b, d, e; c để designer)
- Bằng chứng của dev vòng 1: đột biến `tasks.py` thật → `"tasks.py:328: writes the tool name 'api_update_record' by hand; read GENERIC_WRITE_TOOLS (ADR-024)"` / `'tasks.py:284: names privilege_alert_checked_until outside the Setting and _advance_privilege_watermark (ADR-024)'`, `Ran 179 tests in 12.924s` / `FAILED (failures=2)`; GREEN `Ran 179 tests in 13.327s` / `OK`.

## Tech-lead đã kiểm

- Sau merge `8898f3c`, trong lần giữ khóa của T16: xem dòng `== ARCH` ở phần Tiến độ của `tasks.md`.
- `git diff --name-only 79ad5d0..0a7ca58` = `erp_ai/tests/test_architecture.py` (đúng touchpoint).
- `cmd.lint` trên `8898f3c`: `pre-commit run --all-files` mọi hook `Passed`.
- Lỗi điều phối của tech-lead: vòng 3 gọi dev lần đầu `BLOCKED` vì chưa gỡ worktree dev vòng 2 đang giữ nhánh; gỡ rồi gọi lại (không tính là một vòng review).

## Không kiểm được từ diff

- Hàm job tới được ở module khác: ADR không nêu phạm vi, luật chỉ quét `tasks.py` → ghi debt.md.

## deferred

- Luật 7 (`check_privilege_condition_ignores_owner`) sót chữ `modified_by`/`owner` nằm trong hằng cấp module; hằng tuple/dict chứa `NOW()`; `QUERY_BUILDER_NOW` khớp theo tên cuối; luật Version chưa kiểm `.html`/`.json` → debt.md.
