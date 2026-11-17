# BUG-008 The Console Switch Is a Permission Switch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `console_enabled` ("Cho phép chạy bench console (qua duyệt)", CHG-010) sits in ERP AI Setting's `section_permissions` but is missing from `policy.PERMISSION_SWITCH_FIELDS`, so turning it on or off is not written to the permission-switch log and it never appears in the daily privilege alarm. Make it a full permission switch.

**Architecture:** `policy.PERMISSION_SWITCH_FIELDS` becomes the six fields in the section's field order: `unrestricted_enabled, record_tools_enabled, act_now_enabled, code_change_enabled, console_enabled, one_click_approval_enabled`. The `PermissionSwitches` dataclass keeps its attribute order (console stays the 6th attribute). Every consumer that pairs field names with switch values by position must pair them by name instead: add `policy.SWITCH_FLAGS: dict[str, str]` (field → `PermissionSwitches` attribute) and use it in `erp_ai/tasks.py` `_enabled_permission_switches` (which today slices `astuple(...)` to the first five and zips by position).

**Tech Stack:** Frappe 15, Python (tabs).

**Spec:** the existing rule pinned by `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` `TestPermissionSwitchLog.test_switch_set_matches_section_checks`: every Check in `section_permissions` is a permission switch (logged on change). It fails on `develop` 212216a since the shared site was migrated (the field is now in the meta). Bug found 2026-11-17; the final reviewer of CHG-010 also recommended the console switch in the daily privilege alarm.

## Global Constraints

- Worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/bug-008` (branch `team/BUG-008`). Absolute paths, `git -C`. Never touch the main checkout.
- Tests only via `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/0bf2923d-d2bd-432f-aefc-04f33bc96add/scratchpad/wt-test.sh <WT> <dotted.module> [...]`; read the output (the helper may exit 0 on a failed module); Bash timeout ≥ 7200000 ms. Never migrate, build, or run the whole app.
- Bug fix: the failing test already exists (`test_switch_set_matches_section_checks`, red on develop) — show it red first, then green. Add a test for the alarm. Existing pins of "five switches" change to six only where they pin `PERMISSION_SWITCH_FIELDS`, each with a `# BUG-008:` reason line. No skip/xfail.
- No new field/DocType/hook. Commits `fix(policy): … (BUG-008)` / `test(…): … (BUG-008)` + your session's Co-Authored-By line. `pre-commit run --files <changed>`.

## Review Focus

1. Pairing by name: with only `console_enabled` on, the alarm lists exactly the console label (not the one-click label) — the position shift must not mislabel any switch.
2. With every switch on, the alarm lists six labels in section order.
3. Toggling `console_enabled` on the setting form writes one switch-log entry like the other five.
4. Nothing else that iterates `PERMISSION_SWITCH_FIELDS` breaks or changes meaning (grep every use).
5. `permission_switches(settings)` still returns the same values for the same settings (dataclass untouched).

---

### Task 1: console_enabled joins the permission switches

**Files:**
- Modify: `erp_ai/agent/policy.py`, `erp_ai/tasks.py`
- Test: `erp_ai/agent/test_policy.py`, `erp_ai/tests/test_tasks.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (the existing red test; add a console toggle log case if the class has a pattern for one switch), `erp_ai/tests/test_install.py` only if it pins the five-switch list against `PERMISSION_SWITCH_FIELDS`

**Interfaces:**
- Produces: `policy.PERMISSION_SWITCH_FIELDS` (6, section order above); `policy.SWITCH_FLAGS = {UNRESTRICTED_FIELD: "unrestricted", RECORD_TOOLS_FIELD: "record_tools", ACT_NOW_FIELD: "act_now", CODE_CHANGE_ENABLED_FIELD: "code_change", CONSOLE_FIELD: "console", ONE_CLICK_APPROVAL_FIELD: "one_click_approval"}` with keys in `PERMISSION_SWITCH_FIELDS` order; `tasks._enabled_permission_switches()` returns the labels of the fields whose `getattr(switches, SWITCH_FLAGS[field])` is true, in `PERMISSION_SWITCH_FIELDS` order (no slicing, no positional zip). Remove the CHG-010 comments that say console is outside the switches/alarm.

- [ ] **Step 1: Red.** Run `erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting` → `test_switch_set_matches_section_checks` FAILS (console missing). Add failing tests: `test_tasks.py` — only `console_enabled` on → alarm switch list == [console label]; all six on → six labels in section order; `test_policy.py` — `SWITCH_FLAGS` keys == `PERMISSION_SWITCH_FIELDS` and every value is a `PermissionSwitches` field.
- [ ] **Step 2: Run** those modules → the new and existing cases FAIL for the expected reason.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `erp_ai.agent.test_policy erp_ai.tests.test_tasks erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting erp_ai.tests.test_install erp_ai.tests.test_architecture erp_ai.agent.tools.test_registry` → PASS.
- [ ] **Step 5: Commit** `test(…): … (BUG-008)` then `fix(policy): the console switch is a permission switch: logged on change and listed in the daily alarm (BUG-008)`.
