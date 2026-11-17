# BUG-007 Guidance Uses the Run's Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a run writes its analysis and plan only through `set_resolution_hint` (no `post_comment` kind `de_xuat`), the guidance message in the "Trao đổi với bot" chat shows that hint instead of the fallback "bot chưa viết được nhận định", so "Duyệt hướng xử lý" approves a real plan.

**Architecture:** `write_ticket` already keeps a per-run guidance collector (`collect`, `hold_analysis`, `collected`). Add a held hint next to the held analysis; `set_resolution_hint` holds the text it stored when the run is collecting; `post_guidance` uses `analysis or hint-derived analysis or GUIDANCE_FALLBACK`.

**Tech Stack:** Frappe 15, Python (tabs).

**Spec:** user report 2026-11-17, ticket 43371: the ticket_insert run (category C) called `set_resolution_hint` with "Nhận định: …\n\nHướng xử lý: Dùng Server Script … before_submit …" and `post_comment` kind `ba_note`; no `de_xuat` comment, so `post_guidance` (erp_ai/agent/tools/write_ticket.py ~626) used `GUIDANCE_FALLBACK`; the user clicked "Duyệt hướng xử lý" and the bot answered that the latest guidance had no step for it. The user chose fix A: the guidance takes the run's hint.

## Global Constraints

- Worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/bug-007` (branch `team/BUG-007`). Absolute paths, `git -C`. Never touch the main checkout `/home/miyano/frappe-bench/apps/erp_ai`.
- Tests only via `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/0bf2923d-d2bd-432f-aefc-04f33bc96add/scratchpad/wt-test.sh <WT> <dotted.module> [...]` (site lock, `PYTHONPATH=<WT>`); ONE call for RED and ONE for GREEN; Bash timeout ≥ 7200000 ms. Never migrate, build, or run the whole app.
- Bug fix: failing test first, seen failing for the right reason. No skip/xfail; existing assertions unchanged unless this plan says so (with a `# BUG-007:` reason line).
- No new field, DocType, hook. Commits conventional with `(BUG-007)` and your session's Co-Authored-By line. Never push/merge/switch branches. `pre-commit run --files <changed>` before reporting.

## Review Focus

1. Both an analysis (`de_xuat` held) and a hint in the same run → the analysis wins, exactly as today.
2. A hint without any heading ("Dùng Server Script …") → still a valid guidance: `**Nhận định:** ` prefix, and the manual lines land under a plan heading as `_with_manual_lines` does for text without a plan.
3. A run that is not collecting (no guidance run) → `set_resolution_hint` behaves byte-for-byte as today.
4. Two `set_resolution_hint` calls in one run → the last stored text is used.
5. The hint is model text like the held analysis: same treatment (no extra trust, no extra escaping beyond what the analysis path does).

---

### Task 1: The guidance falls back to the run's hint

**Files:**
- Modify: `erp_ai/agent/tools/write_ticket.py` (collector key, `hold_hint`, `set_resolution_hint`, `post_guidance`)
- Test: `erp_ai/agent/tools/test_write_ticket.py` (unit), and a runner-level regression test in a NEW file `erp_ai/agent/test_runner_guidance_hint.py` (copy the fake-gateway setup pattern from `erp_ai/agent/test_runner_propose_now.py` / `test_agent_runner.py`; import fixtures, do not copy large blocks)

**Interfaces:**
- Produces: `_HINT_KEY = "hint"` in the collector dict (initialised to None where `_ANALYSIS_KEY` is); `hold_hint(run_id: str, text: str) -> None` (no collector → nothing; a later hold replaces an earlier one); `collected(run_id)` keeps its return shape `(analysis, sections)` — add `held_hint(run_id) -> str | None` instead of changing that shape; `hint_analysis(text: str) -> str` returns `text` stripped when its first non-empty line opens with the `Nhận định:` heading (the `**` around it optional, same heading rule as `_heading_line`), else `f"**Nhận định:** {text.strip()}"`.
- `set_resolution_hint`: after a successful save, when `collecting(ctx.run_id)`, `hold_hint(ctx.run_id, args["text"])` (the model's plain text, not the sanitized HTML `after`); return value unchanged.
- `post_guidance`: `analysis = held analysis or (hint_analysis(hint) if hint else None)`; the existing `REASON_NO_CONTENT` check uses this `analysis`; the body uses `analysis or GUIDANCE_FALLBACK`; `_store_run_info` receives this `analysis` (so `ai_analysis` stores the hint-derived text).

- [ ] **Step 1: Failing tests.** Unit (`test_write_ticket.py`, new class `TestGuidanceUsesHint`): (a) collecting run, `set_resolution_hint` with `"Nhận định: X có sẵn.\n\nHướng xử lý: Dùng Server Script before_submit."`, no `de_xuat` comment, one collected done line → `post_guidance` message contains `Nhận định: X có sẵn.` and `Hướng xử lý: Dùng Server Script before_submit.`, does not contain `bot chưa viết được nhận định`; ticket `ai_analysis` equals the hint text; (b) same plus a held `de_xuat` analysis `"**Nhận định:** A\n**Hướng xử lý:** B\n**Căn cứ:** C\nĐộ tin cậy: 80%"` → message uses A/B, not the hint; (c) hint `"Dùng Server Script before_submit."` and a manual line → message starts (after the marker) with `**Nhận định:** Dùng Server Script before_submit.` and the manual line appears under a `Hướng xử lý` heading; (d) two hints → the second is used; (e) no hint, no analysis, a done line → `GUIDANCE_FALLBACK` as today; (f) not collecting → `set_resolution_hint` returns the same dict as before and holds nothing. Runner regression (`test_runner_guidance_hint.py`): `ticket_insert` run on a category-C ticket whose owner holds `ERP AI Instructor`, fake gateway turn 1 calls `set_resolution_hint` (the 43371-like text) and `post_comment` kind `ba_note` (a valid BA note: sections "Mục tiêu", "Phạm vi", "Tính năng sẵn có" starting "Có một phần." with a "Nguồn:" line, "Rủi ro", "Câu hỏi mở" — read `write_ticket` BA note validation), final turn no tool → the guidance `ERP AI Message` of the ticket contains the hint's plan and not the fallback sentence.
- [ ] **Step 2: Run** `erp_ai.agent.tools.test_write_ticket erp_ai.agent.test_runner_guidance_hint` → new cases FAIL (fallback sentence present / names missing).
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4: Run** those two plus `erp_ai.agent.test_agent_runner erp_ai.tests.test_architecture erp_ai.tests.test_ticket_panel` → PASS.
- [ ] **Step 5: Commit** `test(guidance): ...` then `fix(guidance): the guidance takes the run's resolution hint when the bot wrote no analysis comment (BUG-007)`.
