# Default Assignee (CHG-015) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A ticket nobody owns that neither the tag table nor the routing rules can give gets ERP AI Setting's "Người nhận mặc định".

**Architecture:** New Link field `default_assignee` on ERP AI Setting; `routing.decide_route(default_assignee=...)` tries it last and marks `RouteDecision.assignee_default`; the runner passes the setting, names it in the route comment and the assign action's `rule`.

**Tech Stack:** Frappe 15, shared dev site `miyano`. **Spec:** `docs/superpowers/specs/2026-11-17-default-assignee-design.md`.

## Global Constraints

- Worktree `.claude/worktrees/chg-015`, branch `team/CHG-015` from develop ab537d1; `git -C`, never `cd` into it.
- Tests via `$SP/wt-test.sh` (loads branch meta, restores develop's in one lock hold); judge the erp_ai_setting module after merge + migrate.
- TDD; descriptions ≤ 400; commits `(CHG-014)`-style with `(CHG-015)` and the Co-Authored-By line; `pre-commit run --files`.

## Review Focus

1. Default person inactive or the bot account → not assigned, a note, the old comment asking the team lead (Task 2 test).
2. Ticket already assigned → default never used (Task 2 runner test).
3. A tag row or a routing-rules person exists → default never used (Task 2 tests).
4. Setting saved with the bot account as default → refused (Task 1 test).
5. Field absent before migrate → `settings.get("default_assignee")` is None, routing unchanged (Task 2 test via decide_route default None).

### Task 1: The field

Files: `erp_ai_setting.json` (field after `routing_rules`, bump `modified`), `erp_ai_setting.py` (`check_default_assignee` in `validate` after `check_tag_assignees`), tests `test_erp_ai_setting.py` (`TestDefaultAssignee`), `test_doctype_descriptions.py` (count 84, phrases `default_assignee: ("bảng tag", "Quy tắc định tuyến", "HD Agent", "Task C/D")`).
Description (exact): `HD Agent nhận phiếu chưa có người được giao khi bảng Gán người theo tag và Quy tắc định tuyến không cho được người (kể cả khi người ở đó không còn hoạt động); nhận luôn Task C/D. Để trống thì bot nhờ trưởng nhóm phân công. Không được là tài khoản agent.`
Tests: field shape (Link, HD Agent, label "Người nhận mặc định", right after `routing_rules`); an HD Agent saves; the bot account (made an HD Agent in the test) refused with `Người nhận mặc định không được là tài khoản agent`.
Commit: `feat(settings): a default person for tickets no rule gives (CHG-015)`.

### Task 2: Routing falls back to it

Files: `routing.py` (`decide_route(..., default_assignee: str | None = None)`, `RouteDecision.assignee_default: bool = False`), `runner.py` (`ROUTE_ASSIGNED_BY_DEFAULT = "Đã gán cho {person} (người nhận mặc định)."`, pass `settings.get("default_assignee") or None`, `rule="default"`, `_route_lines(..., assigned_default=False)`), docs `docs/HuongDan_QuanTri_DinhTuyen.md` (5c), tests `test_routing.py` (`TestDecideDefaultAssignee`), `test_runner_routing.py` (`TestRoutingDefaultAssignee`).
Routing tests: no tag row and empty routing rules → default, `assignee_default` True, `needs_task` for C; tag row wins; routing-rules person wins; routing-rules person inactive → default; default inactive → None plus note `người nhận mặc định {user} không phải HD Agent đang hoạt động`; default = bot account → None plus note `người nhận mặc định: không gán tài khoản agent`; no default → as before.
Runner tests: empty table and rules + default set → assigned, comment `ROUTE_ASSIGNED_BY_DEFAULT`, action rule `default`; ticket already assigned → default not used.
Commit: `feat(routing): the default person takes a ticket no rule gives (CHG-015)`.

After: final review, merge, migrate, restart, wide run on develop.
