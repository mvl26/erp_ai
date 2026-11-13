# Review package FEAT-003 T15

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; use `git -C`)
- BASE: b075d2d. Task branch team/FEAT-003-task-15, head 593f736.
- Diff: `git diff b075d2d..team/FEAT-003-task-15`; commits: `git log --oneline b075d2d..team/FEAT-003-task-15`
- Touchpoint allowed: erp_ai/tests/test_architecture.py (no production code)
- Criteria: ADR-009, ADR-010 Amendment 1, AC-12, AC-14, AC-15. tasks.md T15 block lists the 8 rules, reverse LAYER_RULES, and 2 scanner tests in TestScannersCatchViolations. Dev reported `Ran 77 tests ... OK` and a mutation table (all red); new rules passed at once, proven by mutation.
- Check: no existing check removed or loosened; each rule pins values/use sites (STD-TEST-2) and its scanner would catch a real violation; rules match design.md section 8 and the real code; no false-green regex (test the regexes on copies with sed/grep to stdout).
- Review against the Review checklist (10). Reply with verdict first line approve or request-changes.
