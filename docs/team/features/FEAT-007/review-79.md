Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 79 — FEAT-007 T79

- Diff: `git diff 2aeb6f6..40e5df4` (nhánh `team/FEAT-007-task-79`; 2 commit `1e327eb` test, `40e5df4` mã; 6 file +157/−32, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `9a5a0bd` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.
- Ghi chú: lần review đầu của round 101 chạy trong một ngữ cảnh skill build tách riêng, ngữ cảnh đó kết thúc khoảng 13:18 mà không trả báo cáo. Bản dưới đây là lần gọi lại ở round 102 (cùng khoảng diff). Merge chỉ làm sau verdict này.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED, `MIGRATE_EXIT=0`: test_prompts `FAILED (failures=2, errors=5)`: `AttributeError: module 'erp_ai.agent.prompts' has no attribute 'ASK_ONLY_BLOCK'` (4 test), `TypeError: build_reason_system() got an unexpected keyword argument 'act_now'`; test_classification `FAILED (failures=3)` (ba `test_reason_system_with_*`); test_erp_ai_setting `FAILED (failures=2)` (`test_required_markers_match_design` `...'**Cần ai quyết:**'), ... != ...`, `test_first_bad_part_in_form_order`). GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_prompts `Ran 10 tests … OK`, test_classification `Ran 55 tests … OK`, test_erp_ai_setting `Ran 104 tests … OK`, test_doctype_descriptions (không sửa) `Ran 12 tests … OK`, test_agent_runner (không sửa) `Ran 110 tests … OK`, test_architecture `Ran 185 tests … OK`; pre-commit exit 0.

Các phép kiểm chính của reviewer:

1. Phạm vi và commit: diff chạm đúng sáu file của `files:`; không file patch, ghi đè đã lưu không bị đụng. Commit test `1e327eb` đứng trước commit mã `40e5df4`; hai tiêu đề đúng `type(scope): description (FEAT-007)`; không dòng ghi công AI; thân commit có lý do thiết kế đòi ("NFR-8, STD-TEST-5 ...").
2. `prompts.py`: `build_reason_system` (`:378-403`) đúng chữ ký của Returns, lõi là `core_prompt(**năm cờ)`; `ACT_NOW_BLOCK` bật với `act_now` hoặc một trong ba cờ công cụ; `SITE_ADMIN_TOOLS_BLOCK` giữ `and not unrestricted_tools`; hai phép suy còn; `ASK_ONLY_BLOCK` chỉ bật với `ask_only`, đứng ngay sau `ACT_NOW_BLOCK`, chữ theo ý `U1.md:229`; khối VIẾT COMMENT khớp từng ký tự các dòng U1-5 của `w1.md:80`, dòng `**Cần ai quyết:** nếu có.` đã bỏ.
3. `erp_ai_setting.py`, `erp_ai_setting.json`: `PROMPT_REQUIRED_MARKERS["reasoning"]` đúng ba mục; mô tả `prompt_override_reasoning` khớp từng ký tự chuỗi Điểm 3 (`design-w1-fixes-7.md:95`); `"modified"` từ 17:00 sang 18:00; bỏ mục, mô tả, `modified` và bỏ dòng prompt cùng một commit `40e5df4`.
4. Test: hai test của Expect có (`test_prompts.py:142`, `:258`), mỗi cái đỏ khi hành vi bị trả lại (`NEW_WRITING` viết cứng các dòng U1-5; đếm mỗi khối 1 hoặc 0 và kiểm thứ tự bằng `endswith`); `test_reasoning_override_with_retired_marker_still_saves` có (`test_erp_ai_setting.py:2572`), là test ghim theo thiết kế; không dấu skip nào; `test_prompts.py` không chép chữ của `CHANGE_TOOLS_BLOCK` (CI-6).
5. Khẳng định bị đổi, chấm theo STD-TEST-5 (không cái nào vi phạm): `test_prompts.py:151` và `:176` `OLD_WRITING` thành `NEW_WRITING` (spec đổi: U1-5, U1-6; test còn kiểm dòng cũ có đúng một lần và `**Cần ai quyết:**` vắng); `test_prompts.py:208` nay phủ 5 khối và kiểm cả đầu ra thật của `build_reason_system` (chặt hơn); ba `test_reason_system_with_*` của `test_classification.py` chỉ đổi mốc sang `core_prompt(<cờ>)`, thêm `assertNotEqual(core, CORE_PROMPT)`, khớp Điểm 1 mục 3a–3c từng chỗ; `test_erp_ai_setting.py:2283` `PROMPT_PARTS["reasoning"]` từ 4 mục còn 3 (phép nới do Điểm 3 mục 1 phán, spec đổi theo AC-65 (a)).
6. Còn lại: không đổi xử lý lỗi hay biên đầu vào, không gọi ngoài, không bí mật; hai cờ mới chỉ nhận theo từ khóa, mặc định False, nơi gọi `runner.py:601` và các test gọi khác còn chạy; tập mục bắt buộc mới là tập con của tập cũ (STD-DESIGN-3); tên theo kiểu có sẵn, không mã chết, không phụ thuộc mới.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 3 small points: test_prompts.py:230 finds P-7 by position (`PROMPT_CONFLICT_PAIRS[5]`), so a reorder would silently point at another pair; `_expected_blocks` (test_prompts.py:96) repeats the two derivations by design and must be updated at T82; the retired-marker test is also green on 2aeb6f6, so it guards against future regressions rather than proving a red-first step | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Độ dài đúng 306 của mô tả (review chỉ đọc, không có công cụ đếm); chữ khớp chuỗi thiết kế từng ký tự.
- Lần GREEN và `cmd.migrate` có nạp lại meta DocType trên site miyano hay không: chỉ có đầu ra của dev, reviewer không chạy test.
- `U1.md:242` ("đã xét, giữ" nên thành "đã bỏ, ...") là chỗ sửa tài liệu thiết kế ngoài `files:` của T79, reviewer không kiểm.
- Reviewer dùng 11/16 lượt.

## Kết luận của tech-lead

- Chạy test: sau merge `9a5a0bd`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_prompts `Ran 10 tests in 0.145s OK`, test_classification `Ran 55 tests in 0.179s OK`, test_erp_ai_setting `Ran 104 tests in 7.963s OK`, test_doctype_descriptions `Ran 12 tests in 0.348s OK`, test_agent_runner `Ran 110 tests in 30.676s OK`, test_architecture `Ran 185 tests in 16.737s OK`; mọi `TEST_EXIT=0`. `migrate` chạy từ worktree `feat-007` trong cùng lần giữ khóa, nên meta DocType đã nạp lại trước test.
- Độ dài mô tả: `test_doctype_descriptions` (trần 400, đủ bốn cụm) xanh sau `migrate`; reviewer xác nhận chữ khớp chuỗi của `design-w1-fixes-7.md:95` từng ký tự, con số 306 là số designer đo bằng lệnh trên chính chuỗi đó. Tech-lead không đếm lại.
- `U1.md:242`: file thiết kế không sửa trong build; file phán quyết đứng trên chữ cũ → ghi cho As-Built.

## deferred

- minor (1): phép tìm P-7 theo vị trí trong `test_prompts.py:230` → `/team:clean` hoặc task kế chạm `PROMPT_CONFLICT_PAIRS`.
- minor (2): `_expected_blocks` (`test_prompts.py:96`) phải cập nhật ở T82 → vào lời giao dev của T82.
- minor (3): test ghim không có bước đỏ → không việc (dòng Expect chỉ đòi xanh).
- `U1.md:242` còn chữ cũ → As-Built.
