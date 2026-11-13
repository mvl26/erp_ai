# Review package FEAT-001 T27

BASE=57704e5 .. team/FEAT-001-task-27 (head 87f6f4b). Diff: `git diff 57704e5..team/FEAT-001-task-27`; files: erp_ai/agent/tools/source.py (adds ToolSpec import, `_schema`, `TOOLS`), erp_ai/agent/tools/test_registry.py (TestRealToolSet, 6 tests). registry.py unchanged (already wired via TOOL_MODULES).

Task criterion (T27): AC-8 (ma trận 4 mức × có/không thẩm quyền; không tool ghi nào nhận DocType/trường), NFR-6. Returns: `_all_specs()` thật; `source.TOOLS` (search_source, read_source, git_source). Expect: test_tool_names_per_level_and_authority, test_no_write_tool_accepts_doctype_or_field, test_git_source_schema_only_log_and_blame (enum log/blame; D4).
Debts from review T23 to check: schema types only string/integer/boolean/array across all schemas (registry._validate KeyError otherwise); no handler commits (savepoint). Total specs are 11 (read 4, source 3, ticket_write 3, task_write 1) vs "10" in task text: check against design 3.5.
Test data rule: no records left on miyano.
