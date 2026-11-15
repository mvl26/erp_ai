Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 78 — FEAT-007 T78

- Diff: `git diff f2ab42ea931bfcb1ad4cc5a760a047f40249d153..958456a` (nhánh `team/FEAT-007-task-78`; 2 commit `3c018f7` test, `958456a` mã; 2 file +256/−15, đều là touchpoint; `test_prompts.py` là file mới)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `2aeb6f6` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `3c018f7`: `AttributeError: module 'erp_ai.agent.prompts' has no attribute 'core_prompt'` / `'PROMPT_CONFLICT_PAIRS'` / `'RULE_6_ACT'` / `'LIMIT_APPS_PROPOSE_ONLY'`, `Ran 6 tests … FAILED (errors=6)`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_prompts `Ran 6 tests in 0.225s OK`, test_classification `Ran 55 tests in 0.290s OK`, test_erp_ai_setting `Ran 103 tests in 21.090s OK`, test_architecture `Ran 183 tests in 27.832s OK`.

Các phép kiểm chính của reviewer:

1. Returns: `core_prompt(*, 5 cờ) -> str`, `CORE_PROMPT = core_prompt()`, `RULE_6_ACT`, `RULE_6_ASK`, `NO_OK_APPROVAL`, `PROMPT_CONFLICT_PAIRS` với 8 cặp (P-1..P-5, P-7, P-8, P-9): có đủ.
2. Chữ chính xác: `RULE_6_ACT`, `NO_OK_APPROVAL` (có 3 dấu cách đầu), `RULE_6_ASK` khớp `w1.md:77-78`; dòng thay của P-1, P-2 khớp `U1.md:235-236`; P-8, P-9 khớp `w1.md:79`.
3. Logic cờ: quy tắc 6 chỉ theo `ask_only` (U1-1); `NO_OK_APPROVAL` có ở mọi tổ hợp; `unrestricted_tools` bỏ dòng P-3, P-4, P-5 và thắng P-2; `act_now` không đổi gì trong lõi.
4. Chữ cũ giữ: ngoài quy tắc 6, `CORE_PROMPT` bằng chữ cũ từng byte (U1-6), kiểm bằng diff blob: dòng 87-134 của `prompts.py` cũ nằm nguyên trong `OLD_CORE_PROMPT` của test. Khối VIẾT COMMENT không đổi (việc của T79).
5. `build_reason_system`: không hunk nào chạm (Điểm 1). `test_classification.py`, `test_erp_ai_setting.py` không có trong diff.
6. CI-6: `test_prompts.py` không chép chữ nào của `CHANGE_TOOLS_BLOCK`, chỉ trỏ hằng `prompts.*`; dòng neo P-1 chỉ có ở `prompts.py:278`.
7. Lần theo đột biến: bỏ qua `change_tools`, `site_admin_tools` hay `unrestricted_tools` → `test_limits_follow_tool_flags_only`, `test_each_tool_flag_changes_its_limit_lines` đỏ; giữ quy tắc 6 cũ → `test_rule_6_follows_ask_only_alone` và phép kiểm P-8/P-9 đỏ; bỏ qua `ask_only` → `test_rule_6_follows_ask_only_alone` đỏ; để `act_now` đổi lõi → `assertEqual(core_prompt(act_now=True), default)` đỏ. Dòng neo P-1..P-5 có thật trong các khối (`prompts.py:194, 217, 237, 242, 244`); neo P-5 dừng ở "không áp" vì khối xuống dòng ở đó, đúng.
8. Commit: `test(prompts): … (FEAT-007)` rồi `feat(prompts): … (FEAT-007)`; không dòng ghi công AI.

Checklist (10): 1 đạt (hằng `LIMIT_*` là điều `U1.md:231` đòi); 2 đạt; 3 đạt (commit RED trước; 2⁵ tổ hợp; không skip); 4 đạt; 5 không áp dụng (không I/O); 6 đạt; 7 đạt (`CORE_PROMPT` giữ tên và kiểu; chữ đổi là điều AC-66 đòi); 8 đạt; 9 không thêm phụ thuộc; 10 đạt.

Findings: không blocker, không major.

- minor | — | — | 2 điểm nhỏ: (a) `setUp` của `test_prompts.py` gọi `keep_agent_settings`, các test hàm thuần này không cần (STD-DESIGN-5); (b) không gì kiểm câu được phép của từng cặp có mặt trong một khối nào đó, nên gõ sai dòng neo sẽ qua im lặng, và P-7 chưa kiểm gì cho tới khi T79 thêm `ASK_ONLY_BLOCK` (STD-TEST-5) | dev's call; gợi ý T79 thêm `assertIn(allowed, core + all blocks)` cho từng cặp

Mục "không kiểm được từ diff" của reviewer:

- Lint: gói không có đầu ra `pre-commit run --all-files`; vài dòng `prompts.py` (quanh 85, 109-115) gần 105 ký tự.
- Phiên bản Python: `zip(..., strict=True)` ở `test_prompts.py:11` cần Python 3.10 trở lên.
- GREEN của test_classification, test_erp_ai_setting, test_architecture chỉ có trong lời của dev.

## Kết luận của tech-lead

- Chạy test: sau merge `2aeb6f6`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_prompts `Ran 6 tests in 0.108s OK`, test_classification `Ran 55 tests in 0.177s OK`, test_erp_ai_setting `Ran 103 tests in 7.426s OK`, test_architecture `Ran 185 tests in 16.458s OK` (185 vì cây đã có luật của T74).
- Lint: dev chạy `pre-commit run --files` trên hai file, 0 hook đỏ (ruff-format đã chạy trước commit); `cmd.lint` cả cây chạy cuối lượt.
- Python: `test_prompts` chạy xanh trên bench nên `strict=True` dùng được; `test_redact.py::test_every_pattern_is_python_310_syntax` đã ghim mức 3.10 cho app.
- Minor (a) đúng quy ước "mọi lớp test mới gọi `keep_agent_settings(self)`" của `tasks.md:17`, giữ. Minor (b) đưa vào lời giao dev T79. Không mở vòng sửa.

## deferred

- minor (b): phép kiểm "câu được phép có mặt" cho từng cặp và nửa còn lại của P-7 → lời giao T79 (cùng file `test_prompts.py`).
