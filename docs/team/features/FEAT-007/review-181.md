# Review T181 — Chữ prompt theo phụ lục 5 (VIẾT COMMENT, quy tắc 6, `ACT_NOW_BLOCK`, mục bắt buộc phần lập luận)

## Vòng 1 (2026-11-15, lượt build 20) — `approve`

- Lệnh diff: `git diff 69a56cf..376c32e` (BASE = `git merge-base team/FEAT-007 team/FEAT-007-task-181` = `69a56cf`; đầu nhánh task `376c32e`; commit `60df4fa` test, `376c32e` mã); 6 file, +81/−23, đúng sáu touchpoint.
- Số vòng: 1. Review checklist (10): 10/10.
- Đối chiếu từng byte với `design-w1-fixes-19.md` (reviewer `diff` máy từng khối trên `376c32e`), đều GIỐNG: Điểm 1.1 `_CORE_WRITING` (dòng thiết kế 42-54; dòng "Không tự liệt kê …" là biến thể A, chữ của biến thể B xuất hiện 0 lần trong `prompts.py`); 1.2 `RULE_6_ACT` (một dòng, vẫn mở đầu `6. `); 1.3 `ACT_NOW_BLOCK` (chỉ dòng 4 và dòng 17-18 của khối đổi, mọi dòng khác giữ); 1.4 P-10, P-11 là hai phần tử cuối, tuple có 10 cặp, chỉ số `[5]` (P-7) không đổi; 2.2 mô tả `prompt_override_reasoning` đúng 369 ký tự, `"modified"` 18:00:00 → 19:29:13; `PROMPT_REQUIRED_MARKERS["reasoning"] == ("**Nhận định:**", "**Hướng xử lý:**")`; `A5_WRITING_LINES`, `OLD_WRITING_LINES` đúng dòng Returns; `OLD_CORE_PROMPT` (dòng 1-66 của `test_prompts.py`) giống hệt BASE; không chuỗi mới nào của `test_prompts.py` nằm trong `CHANGE_TOOLS_BLOCK`; không tên công khai mới ở `prompts.py`, `erp_ai_setting.py`.
- Kiểm 1 của quyết định 19:19 (e), bảng STD-TEST-5: mọi khẳng định bị sửa đều có trong bảng và chỉ đổi đúng phần bảng và Expect cho phép (`test_prompts.py:73-81`, `:149-151` chặt hơn, `:214` `8` → `10`; `test_classification.py:505`; `test_erp_ai_setting.py:2345`); lý do từng dòng nằm trong thân commit `60df4fa`; test giữ `:2634-2638` không đổi.
- Kiểm 2 của quyết định 19:19 (e), biến thể A: đạt (mục 1.1 ở trên).
- Test mới đỏ khi thiếu hành vi (reviewer suy từ mã): trả `RULE_6_ACT` cũ → `test_rule_6_points_to_approve_now_in_the_bot_panel` đỏ; đặt lại một trong hai đầu mục → `test_no_retired_heading_in_any_built_prompt` đỏ; giữ `**Căn cứ:**` bắt buộc → lần lưu đầu của `test_reasoning_override_without_evidence_heading_saves` đỏ, bỏ `**Hướng xử lý:**` → khẳng định thứ hai đỏ; `test_reasoning_override_from_before_addendum_5_still_saves` ghim A5-9.
- Rủi ro khác đã soát: `git grep PROMPT_CONFLICT_PAIRS` chỉ ra `test_prompts.py`, không validator nào dùng cặp P-10/P-11 để chặn ghi đè đã lưu.

### Findings

Không có blocker, major.

`minor | — | — | 2 điểm nhỏ: (a) câu mới "Tool trả ok=false thì không thử đường khác." của ACT_NOW_BLOCK (prompts.py:270, STD-TEST-2) chưa có test vì danh sách cụm của Expect không nêu; (b) test_prompts.py:85 thêm hằng RETIRED_HEADINGS của module test, dòng Returns không liệt kê (không phải mã sản phẩm) | dev's call`

### Ngoài phạm vi

Không có.

### Không kiểm được từ diff (tech-lead giải trước khi tick)

- Test chưa chạy bởi reviewer: dựa vào dòng GREEN của dev; lần chạy lại 8 module sau merge dưới khóa site quyết định.
- `test_builtin_reasoning_has_no_retired_heading` đọc mô tả qua `frappe.get_meta`: cần `cmd.migrate` trên site sau merge.
- Các lần merge sau của `erp_ai_setting.json` (T87, T124) có giữ mô tả và `modified` hay không: kiểm JSON sau từng merge đó.
- Biến thể A phụ thuộc `design-w1-fixes-20.md` không chọn B (Điểm 1.5).

### Bằng chứng của dev (nguyên văn, kèm trong lời giao review)

- RED trên `60df4fa`, `MIGRATE_EXIT=0`: test_prompts `Ran 12 tests in 0.148s` / `FAILED (failures=5)`; test_classification `Ran 56 tests in 0.166s` / `FAILED (failures=1)`; test_erp_ai_setting `Ran 112 tests in 7.450s` / `FAILED (failures=4)`.
- GREEN trên `376c32e`, `MIGRATE_EXIT=0`, một lần giữ khóa: test_prompts `Ran 12 tests in 0.167s` OK; test_classification `Ran 56 tests in 0.201s` OK; test_erp_ai_setting `Ran 112 tests in 8.252s` OK; test_doctype_descriptions `Ran 12 tests in 0.352s` OK; test_agent_runner `Ran 118 tests in 31.227s` OK; test_runner_routing `Ran 62 tests in 33.608s` OK; test_run_eval `Ran 23 tests in 0.657s` OK; test_architecture `Ran 187 tests in 17.116s` OK.
- `pre-commit run --all-files`: `LINT_EXIT=0` trên BASE `69a56cf` (không hook nào sửa file) và trên đầu nhánh `376c32e`.

## Kết luận của tech-lead

`approve` vòng 1, ghi trước merge. Hai điểm minor: hoãn (deferred), chuyển team-leader.
