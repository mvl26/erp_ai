# Review package FEAT-001 T11

BASE=bc0411c .. team/FEAT-001-task-11 head 260f6c3
Commits: 260f6c3 feat(install): roles, agent user, default settings hooks (FEAT-001)
Command: `git diff bc0411c..team/FEAT-001-task-11` (read it in full)
Stat: erp_ai/hooks.py 3 +-, erp_ai/install.py 56 +, erp_ai/tests/test_install.py 71 +; 3 files, 129 insertions, 1 deletion

Decisions that supersede design.md (journal docs/team/journal/FEAT-001.md):
- D4: git_source is log/blame only. Not relevant here.
- D6: USD money fields are Float precision 6 with "(USD)" label, never Currency.

Criterion (tasks.md T11): AC-4 (roles exist; agent account has exactly roles ERP AI Agent + Agent and not System Manager; defaults disabled / L0; re-run idempotent, never overwrites human-set values), A-13, ADR-006 #4. Design section 6 steps 1, 2, 5 only (steps 3, 4, 6 are T12/T13). Returns: install.ensure_setup, after_install, after_migrate; hooks.py after_install/after_migrate. Tickets are never written.
