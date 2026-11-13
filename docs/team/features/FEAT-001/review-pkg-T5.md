# Review package T5 (FEAT-001)

Diff command: `git diff a85f798..team/FEAT-001-task-5` (BASE=a85f798, head 4268655)
Commits: 4268655 feat(eval): offline accuracy metrics and report (FEAT-001)
Files (new): erp_ai/eval/__init__.py, erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py
Run the diff command in /home/miyano/frappe-bench/apps/erp_ai (branch is local).
Criteria (tasks.md T5): AC-1, NFR-9; compute_metrics(rows, mapping) with exact keys labeled, correct, accuracy, per_category, confusion, unclassified, top_owner, non_top_owner, verdict, skipped_unlabeled (design 3.7); format_report(metrics) -> str; 10/12 -> 83.3% -> "70–85%"; thresholds at 85 and 70; unparseable and unlabeled rows.
Touchpoints: the three files above.
