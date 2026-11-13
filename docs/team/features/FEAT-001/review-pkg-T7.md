# Review package T7 (FEAT-001)

Diff command: `git diff 212f77b..team/FEAT-001-task-7` (BASE=212f77b, head 4be4d3f)
Files changed: erp_ai/agent/tools/source.py (adds git_source), erp_ai/agent/tools/test_source.py
Run the diff command in /home/miyano/frappe-bench/apps/erp_ai (branch is local).
Criteria (tasks.md T7, design 5.4): AC-13 git part, NFR-6 (30 s): git_source(args, ctx) -> dict; argument list, no shell, timeout=30, only log/show/diff/blame, refuse the flags listed in design 5.4, FileNotFoundError -> ok=false "chưa cài git", never raises.
Touchpoints: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py. No ToolSpec / TOOLS yet (T27).
Compare the refused-flag list with design 5.4 exactly, and check each test would fail if its guarded behavior were removed.
