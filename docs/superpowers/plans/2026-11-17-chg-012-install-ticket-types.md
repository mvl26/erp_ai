# CHG-012 Install Creates the Ticket Types and Team the Bot Classifies Into — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Installing (or migrating) `erp_ai` on a site creates any missing `HD Ticket Type` and `HD Team` named in the bot's category mapping, so the bot can write its classification on a fresh site.

**Architecture:** `erp_ai/install.py` `ensure_setup()` (runs on `after_install` and `after_migrate`) gains one step `_ensure_ticket_types_and_teams()`, run after `_ensure_default_settings()` so the stored `category_mapping` exists. It reads the effective mapping (`classification.load_mapping(<stored category_mapping>)`, falling back to `classification.DEFAULT_CATEGORY_MAPPING` when the stored value is empty or invalid), and creates each missing non-empty `ticket_type` as an `HD Ticket Type` and each missing non-empty `agent_group` as an `HD Team`. Existing records are never changed. Helpdesk's own `HD Team.after_insert` creates the team's "<team> - Support Rotation" Assignment Rule.

**Tech Stack:** Frappe 15, Helpdesk 15.1 (`HD Ticket Type`: autoname Prompt, fields `description`, `priority`, `is_system`, `disabled`; `HD Team`: autoname `field:team_name`).

**Spec:** user request 2026-11-17: "cài erp_ai thì sẽ có sẵn các ticket type như trong tài liệu … hiện tại khi cài erp_ai lên site mới thì không có các ticket type này làm cho bot không phân loại được ticket". The names are the six of `docs/HuongDan_TrienKhai_erp-ai.md` §16.1, identical to `DEFAULT_CATEGORY_MAPPING` (`erp_ai/agent/classification.py:29`). Assignment (who gets the ticket) is out of scope (another change, CHG-011, works on routing).

## Global Constraints

- Worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/chg-012` (branch `team/CHG-012`). Absolute paths, `git -C`. Never touch the main checkout.
- Tests only via `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/0bf2923d-d2bd-432f-aefc-04f33bc96add/scratchpad/wt-test.sh <WT> <dotted.module> [...]` (site lock, `PYTHONPATH=<WT>`); ONE call for RED, ONE for GREEN; Bash timeout ≥ 7200000 ms. Never migrate, build, or run the whole app.
- The shared site `miyano` already has all six types and team `IT` with tickets linked to them: tests must NOT delete or rename those records. Test with fresh, unique names put into the stored `category_mapping` for the test (`set_agent_settings(category_mapping=json.dumps(...))` inside `keep_agent_settings(self)`), never committing.
- TDD: failing test first. No skip/xfail. No new DocType, field or hook (the step is called from the existing `ensure_setup`). Commits `feat(install): … (CHG-012)` / `test(install): … (CHG-012)` + your session's Co-Authored-By line. `pre-commit run --files <changed>`.

## Review Focus

1. A site where a type or team with that name already exists (any description/priority/disabled state) → left byte-for-byte as it is (no save, `modified` unchanged).
2. A stored `category_mapping` that a human customised with other names → the types/teams of THAT mapping are created, not the default six.
3. Empty / invalid stored mapping → fall back to `DEFAULT_CATEGORY_MAPPING`, never crash the install or migrate.
4. A mapping entry with an empty `ticket_type` or `agent_group` (D and E have empty groups) → nothing created for the empty value.
5. Running `ensure_setup()` twice → second run creates nothing.

---

### Task 1: ensure_setup creates the mapping's missing ticket types and teams

**Files:**
- Modify: `erp_ai/agent/classification.py` (add `CATEGORY_TYPE_DESCRIPTIONS`), `erp_ai/install.py`
- Test: `erp_ai/tests/test_install.py` (new class `TestEnsureTicketTypesAndTeams`)

**Interfaces:**
- Produces: `classification.CATEGORY_TYPE_DESCRIPTIONS: dict[str, str]` keyed by category letter, the "Dấu hiệu nhận biết" column of §16.1 verbatim:
  - A: `"lỗi", "mất", "không hiển thị", có mã chứng từ cụ thể, người dùng bị chặn việc`
  - B: `Tạo tài khoản, phân quyền, thêm trường, cấu hình tham số/ngày nghỉ/ngôn ngữ, chặn validation`
  - C: `"xây dựng", "tích hợp", "bot", "tự động", "dashboard"; phạm vi nhiều ngày, cần BA`
  - D: `"bổ sung", "chuẩn hóa", "đưa lên ERP", "rà soát"; đầu vào là dữ liệu nghiệp vụ của phòng ban`
  - E: `Việc của HCNS, Kế toán, Mua hàng; không cần thay đổi hệ thống`
  - F: `Tiêu đề rỗng/không rõ, phiếu test, hỏi cách dùng`
- Produces: `install._ensure_ticket_types_and_teams() -> None`, called in `ensure_setup()` right after `_ensure_default_settings()`. For each category in the effective mapping: if `ticket_type` is non-empty and `not frappe.db.exists("HD Ticket Type", name)` → insert `{"doctype": "HD Ticket Type", "name": name, "description": CATEGORY_TYPE_DESCRIPTIONS[category] if the name equals DEFAULT_CATEGORY_MAPPING[category]["ticket_type"] else "", "priority": entry["priority"] if it names an existing HD Ticket Priority else None}` with `ignore_permissions=True`; if `agent_group` is non-empty and not existing → insert `{"doctype": "HD Team", "team_name": name}` with `ignore_permissions=True`. One info log line per created record (`frappe.logger(LOGGER_NAME)`), none when nothing is created. Effective mapping: `load_mapping(stored)` when it returns a non-empty dict, else `DEFAULT_CATEGORY_MAPPING`.

- [ ] **Step 1: Failing tests** (`TestEnsureTicketTypesAndTeams`, each test inside `keep_agent_settings(self)`, unique names like `f"CHG012 {frappe.generate_hash(length=6)} A"`): (a) mapping with two fresh type names and one fresh team → after `install._ensure_ticket_types_and_teams()` both `HD Ticket Type` exist, the team exists and has an `assignment_rule` (Helpdesk created it); (b) a pre-existing type with description "giữ nguyên" and `disabled=1` → unchanged, `modified` unchanged; (c) stored mapping `""` and `"not json"` → the six default names are ensured (assert `frappe.db.exists` for each; they exist on miyano already, so also assert no exception and that a fresh-name run in the same test still works) — and with the default names, a created type gets the §16.1 description (test this through a mapping that reuses the default name for category A after renaming nothing: assert `CATEGORY_TYPE_DESCRIPTIONS["A"]` equals the §16.1 text verbatim instead of creating the record); (d) entry with `agent_group: ""` → no HD Team named "" created; (e) running twice → the second run inserts nothing (count `HD Ticket Type`/`HD Team` rows before/after); (f) priority that does not exist (`"Rất cao"`) → type created with empty priority, no exception; (g) `ensure_setup` calls the new step after `_ensure_default_settings` (patch both, record call order).
- [ ] **Step 2: Run** `erp_ai.tests.test_install` → new cases FAIL (missing function/constant).
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4: Run** `erp_ai.tests.test_install erp_ai.tests.test_architecture erp_ai.agent.test_classification` → PASS.
- [ ] **Step 5: Commit** `test(install): …` then `feat(install): the install creates the mapping's missing ticket types and teams (CHG-012)`.
