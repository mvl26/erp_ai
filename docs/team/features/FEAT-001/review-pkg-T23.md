# Review package FEAT-001 T23 (BASE c7df05b..104a1c8, branch team/FEAT-001-task-23)

Diff command (authoritative, read-only git): `git diff c7df05b..team/FEAT-001-task-23`

Commits:
- 104a1c8 feat(agent): tool registry, context, parameter validation (FEAT-001)

Files: erp_ai/agent/tools/__init__.py (new), erp_ai/agent/tools/registry.py (new), erp_ai/agent/tools/test_registry.py (new). Use `git diff --stat c7df05b..team/FEAT-001-task-23`.

Dev evidence (raw): RED Ran 16 FAILED (failures=10, errors=2) against a behaviour-less stub; GREEN Ran 16 OK; full app Ran 169 OK; pre-commit exit 0.

Known by design: read.py / write_ticket.py do not exist yet (T24/T25); `_all_specs` skips a module only when that module itself is missing (T27 removes the skip).

Run `git diff c7df05b..team/FEAT-001-task-23` for the verbatim code.
