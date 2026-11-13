# Review package FEAT-001 T13 (BASE 8a5be57..7330919, branch team/FEAT-001-task-13)

Diff command (authoritative, read-only git): `git diff 8a5be57..team/FEAT-001-task-13`

Commits:
- 7330919 (feat(install): Task permission for the agent role, FEAT-001)

Files: erp_ai/install.py, erp_ai/tests/test_install.py only.

Contents:
- install.py: `_ensure_task_permission()` called from `ensure_setup()`: if DocType `Task` exists -> `setup_custom_perms("Task")`, then insert exactly one Custom DocPerm {role ERP AI Agent, permlevel 0, read/write/create = 1, if_owner = 1} if the agent has none on Task, then `frappe.clear_cache(doctype="Task")`; no Task DocType -> `frappe.logger(LOGGER_NAME).warning("DocType Task not found; ...")` and return.
- test_install.py: setUp deletes the agent's Task Custom DocPerm and clears the cache (so the create path runs inside the rolled-back transaction); tests: exactly 1 perm after repeated installs with if_owner=1 and delete/submit=0, other roles' Task perms unchanged, copy path when no Custom DocPerm exists, no-Task warning.

Dev evidence: RED 3 tests "0 != 1" (behavior missing); GREEN test_install Ran 13 OK; full `--app erp_ai` Ran 122 OK; migrate x2 exit 0; mutations (if_owner=0 -> 1 fail; step dropped -> 3 fail; duplicate guard removed -> 1 fail) reverted; pre-commit clean. No DDL/implicit commit in Custom DocPerm insert or setup_custom_perms (nothing patched). On miyano Task exists and already had 2 Custom DocPerm rows.

Run `git diff 8a5be57..team/FEAT-001-task-13` for the verbatim code.
