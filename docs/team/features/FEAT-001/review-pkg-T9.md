# Review package T9 (FEAT-001)

BASE=f455f3b, head=f32354f (branch team/FEAT-001-task-9)
Diff command: `git diff f455f3b..team/FEAT-001-task-9` in /home/miyano/frappe-bench/apps/erp_ai (also `git log --oneline` and `--stat` for the same range).

## Task T9 criteria
Single DocType `ERP AI Setting` with the fields of design.md section 2.1 (including child table `credentials` -> ERP AI Credential), System Manager only permissions, defaults: agent disabled, level L0, `category_mapping` default = DEFAULT_CATEGORY_MAPPING (carried note). `ERPAISetting.validate()` implements (a)-(f) of design 3.6 (restore self-managed fields on human save; human may move a key from "Lỗi khóa" to "Hoạt động" only; mapping via `classification.validate_mapping`; numeric limits NFR-3; prices required when enabled; STD-ERR-6/D-25). No `check_keys`, no `.js` (T36). `test_utils.set_agent_settings(**fields) -> None` via `frappe.db.set_single_value`. AC-19, AC-4, NFR-3.
Touchpoints: erp_ai/erp_ai_agent/doctype/erp_ai_setting/{__init__.py, erp_ai_setting.json, erp_ai_setting.py, test_erp_ai_setting.py}, erp_ai/test_utils.py.
Tests must not commit to the DB; no skip markers.
