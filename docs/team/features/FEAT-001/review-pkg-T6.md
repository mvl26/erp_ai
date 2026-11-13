# Review package T6 (FEAT-001)

Diff command: `git diff be71629..team/FEAT-001-task-6` (BASE=be71629, head 4234e45)
Commits: 4234e45 (one commit) on team/FEAT-001-task-6
Files (new): erp_ai/agent/tools/__init__.py (empty), erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py
Run the diff command in /home/miyano/frappe-bench/apps/erp_ai (branch is local).
Criteria (tasks.md T6, design 5.4, guide docs/HuongDan_TrienKhai_erp-ai.md:342-345): AC-13 (except git), NFR-6 (400 lines / 40 results). get_source_root, resolve_safe_path, search_source, read_source return {"ok": ...} and never raise; DUOI_CHO_PHEP and TEN_CAM exactly as the guide; path escape (.., absolute, symlink) refused; secret names/extensions refused. No ToolSpec and no git function (T7, T27).
Touchpoints: the three files above.
