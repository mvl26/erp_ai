# Review package FEAT-001 T36

BASE=920be6c  head=72b026a (branch team/FEAT-001-task-36)

Diff command (read-only, run from the repo root): `git diff 920be6c..team/FEAT-001-task-36`

## Commits
72b026a feat(erp-ai-setting): check_keys whitelist and Kiểm tra khóa button (FEAT-001)

Touchpoints: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai_setting.js (new), test_erp_ai_setting.py.
Criterion: AC-19 (only System Manager can call; result per key; unknown `label` -> error; never returns exception text or key material; never `.save()`s the setting). Design 3.5/3.6, Amendments 2026-11-11.
Expected test: test_check_keys_system_manager_only_and_per_key_result. Note: dev sets `frappe.local.flags.in_test=False` inside the HD Agent test because `frappe.only_for` returns early under in_test; judge whether that is sound and restored.
Check the JS too (escaping, no key display).
