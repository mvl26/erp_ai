Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 04 — FEAT-004 T4

- Diff: `git diff 77c411f..team/FEAT-004-task-4` (commit `8679d5d`, merge nhánh feature, `13645c1`, `844edae`; 6 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 77c411f..13645c1`)
Lớp 1: AC-12 và ADR-012 QĐ 6 đạt. Trường, option, kiểm `change_step`/`actor`/`change_proposal`, `ignore_permissions` chỉ cho `change`, test tổng chi phí, `field_count` 38 khớp design 2.5. Sửa `test_architecture.py` nằm trong quyết định của người 2026-11-13: chỉ `ENTRY_TYPES_EXPECTED`, docstring và test tự kiểm của chính luật đó. 4 cột FEAT-006 của Log không đổi.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DOC-2 | erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:80,95 | Diff thêm `change` vào `entry_type` và `change_action` vào `trigger` nhưng hai mô tả không đổi: vẫn liệt kê giá trị cũ như là đủ và ghi "Hệ thống tự ghi khi agent chạy", trong khi dòng `change` được ghi ở từng bước đề xuất, phần lớn do người duyệt | mở rộng hai mô tả (≤ 400 ký tự), sửa câu "agent chạy"; thêm `"change"`, `"change_action"` vào `phrases` ở test_doctype_descriptions.py:136-138 |

minor | — | — | 2 điểm nhỏ: commit `8679d5d` tự nó đỏ (task merge thành một khối); mô tả `change_proposal` ghi loại khác "để trống" nhưng `write_entry` không chặn loại cũ truyền `change_proposal` | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 13645c1..team/FEAT-004-task-4`)
- Phát hiện 1: ADDRESSED (`erp_ai_log.json:80,95` nêu `change`/`change_action` và người ghi ở bước đề xuất, mỗi mô tả 260–290 ký tự; `test_doctype_descriptions.py:136-146` thêm `"change"`, `"change_action"`, `"bước của đề xuất"`)
- Phát hiện mới: không có blocker/major
- Câu hỏi RED của vòng 1 (phán từ diff): không có mã `run_log.py` và JSON thì `test_change_entry_requires_step_actor_proposal_and_trigger`, `test_change_entry_keeps_git_keys_of_apply_and_undo_rows`, `test_change_entry_bypasses_permission_but_other_types_do_not`, `test_log_change_fields_match_design`, `test_tasks::test_recompute_spend_unchanged_by_change_rows` đều đỏ (`ENTRY_TYPES` cũ không có `change` → `ValueError`)

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Lần gọi 2 RED: `FAIL: test_entry_types_unchanged (erp_ai.tests.test_architecture.TestArchitecture.test_entry_types_unchanged)`, `Ran 107 tests in 1.574s` / `FAILED (failures=1)`; GREEN: test_run_log `Ran 12 tests in 3.111s OK`, test_tasks `Ran 35 tests in 1.445s OK`, test_doctype_descriptions `Ran 11 tests in 0.332s OK`, test_architecture `Ran 107 tests in 1.422s OK`
- Vòng 2 RED: `AssertionError: {'entry_type': ['change', 'bước của đề xuấ[49 chars]ất']} != {}` / `Ran 11 tests in 0.331s` / `FAILED (failures=1)`; migrate: `Queued rebuilding of search index for miyano`; GREEN: test_doctype_descriptions `Ran 11 tests in 0.354s OK`, test_run_log `Ran 12 tests in 2.490s OK`, test_tasks `Ran 35 tests in 1.400s OK`, test_architecture `Ran 107 tests in 1.376s OK`

## Không kiểm được từ diff (tech-lead xử lý)
- RED của lần gọi 1 (round 14) không được giữ lại: reviewer phán từ diff là các test mới đỏ khi thiếu mã (xem vòng 2) → chấp nhận, ghi lệch.
- Site `miyano` đã migrate theo JSON của nhánh task-4 (dev vòng 2 chạy `cmd.migrate` một lần); `cmd.test` sau merge: xem tasks.md.
- ADR-012 Ràng buộc: đúng 2 chỗ `ignore_permissions`; chưa có luật quét `run_log.py` → việc của T13 (luật layer) và T31.

## deferred
- `erp_ai/tests/test_tasks.py:120`: `recompute_monthly_spend` cộng `cost_usd`, dòng `change` để trống cột này, nên test chỉ đỏ qua `write_entry`, không chứng minh có lọc `entry_type`; giữ làm test hồi quy.
- Mô tả `change_proposal` ("để trống" với loại khác) không được `write_entry` ép.
