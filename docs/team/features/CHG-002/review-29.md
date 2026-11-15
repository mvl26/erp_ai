Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 29 — CHG-002 T29

- Diff: `git diff 4e1093c..334f852` trên `team/CHG-002-task-28` (vòng 1); sửa vòng 1: `git diff 024ba58..4dddc6f`, commit của T29 là `7d52bda`
- Gói: T28 + T29 cùng nhánh, một reviewer chấm cả gói; verdict của T28 ở `review-28.md`
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `238544c`, tick

## Vòng 1 — request-changes (`git diff 4e1093c..334f852`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DOC-7 | `erp_ai/agent/tools/propose_change.py:501` | mô tả `propose_new_file` còn ghi "(thư mục chứa phải có sẵn)"; hàng §3.1 ghi "Thư mục cha có thể chưa có", `NO_PARENT` đã xóa, test của chính gói tạo được `pkg/new/n.py`; model bị báo sai | bỏ ngoặc hoặc viết ngược lại, ví dụ "thư mục cha chưa có sẽ được tạo" |

minor | — | — | 1 điểm nhỏ: các hàng từ chối `length=0/20001` bị bỏ rồi thành hàng chấp nhận trong test Expect, giống L-2b hơn L-2c; nhãn nào cũng được vì nằm trong touchpoint | tùy dev

Tầng 1 ở vòng 1: schema khớp §3.1 / §2.5 (`changes` 1..50, `commands` 0..6, bỏ `maxItems` / `maxLength` của `find` / `replace`, `content` bỏ `minLength` / `maxLength`); `EDIT_SHAPE` chữ mới; hai hằng đã xóa, `git grep` không còn chỗ dùng; `PROPOSE_TOOL_NAMES` và thứ tự tool không đổi (AC-56); đủ ba test Expect; số đếm trong thân commit khớp diff (L-1: 3; L-2: 2 `test-input` + 1 `test-drop`).

Phán về `erp_ai/agent/changes/test_transitions.py` (ngoài touchpoint): được phép theo luật `tasks.md` dòng 19; giữ `assertEqual`, `334f852` có dòng `test-shape:` khớp (addendum-2 L-1).

## Vòng 2 — approve (`git diff 024ba58..4dddc6f`)

1. ADDRESSED | STD-DOC-7 | `propose_change.py:501-503`: mô tả ghi "thư mục cha chưa có sẽ được tạo" (khớp §3.1 dòng 214), câu về lệnh cùng chữ với `propose_file_change` (`:472`); test mới `TestProposeBlock::test_new_file_description_tells_parent_and_commands_rules` (`test_propose_change.py:1549-1556`) có `assertNotIn("phải có sẵn")`.

Lỗi mới trong các dòng đổi: không.

minor | — | — | 1 điểm nhỏ: (b) STD-TEST-1 test mới không có RED dán kèm (dev khai viết trước khi sửa mô tả nhưng không chạy đỏ); đỏ chứng minh được bằng đọc diff (chữ cũ so với `assertNotIn`) | tùy dev

Bằng chứng của dev. Lần gọi đầu: RED `FAIL: test_edit_with_11_replacements_accepted` (changes, legacy edit), `FAIL: test_new_file_20001_chars_accepted` (length=20002, length=0), `FAIL: test_schema_matches_design_table`; GREEN `test_propose_change` `Ran 70 tests` / `OK`, `test_registry` `Ran 41 tests` / `OK`, `test_transitions` `Ran 76 tests` / `OK`, `test_architecture` `Ran 195 tests` / `OK`. Sửa vòng 1: GREEN như ở `review-28.md` (`test_propose_change` `Ran 71` / `OK`).

## Review checklist (10)
1 đạt · 2 đạt · 3 đạt (RED của test mô tả không dán, minor) · 4 đạt · 5 không áp dụng · 6 đạt · 7 đạt (chỉ mô tả đổi ở vòng 2) · 8 đạt · 9 đạt · 10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Cả app, đợt merge 18, `team/CHG-002` @ `238544c` (20:13–20:25): `Ran 1885 tests in 680.363s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Đếm L-1 / L-2: T29 `L-1: 3, L-2: 3`.
- Các module khác nhắc tên ba tool (`test_agent_runner.py`, `test_classification.py`, `prompts.py`): phủ bởi lần chạy cả app ở trên.

## deferred

1. `registry.py` không kiểm `minItems` (xem `review-28.md` deferred 2): việc của designer.
2. Điểm mở từ `review-26.md` chưa có task nào nhận: `_edited_op` băm `after.encode("utf-8")` kiểu chặt, `replace` chứa surrogate lẻ thì `UnicodeEncodeError` nổ trước `check_block`. Lượt 4 ghi "việc cho T29" nhưng không chép vào dòng task; T29 không làm. Đưa lên team-leader trong báo cáo lượt 5.
