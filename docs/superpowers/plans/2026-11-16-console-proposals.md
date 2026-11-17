# Console Script Proposals (CHG-010) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When no REST API or record tool can do a data job, the bot drafts a Python script that runs like `bench console`; it runs only after a person with `ERP AI Instructor` clicks **Duyệt** on its card inside the "Trao đổi với bot" chat, once, in one transaction. Proposal cards (code and console) move into the chat thread itself.

**Architecture:** A console script is an `ERP AI Change Proposal` of the existing kind `Lệnh bench` whose `command_list` is exactly `[["--site", <site>, "console"]]` and whose script sits in the existing `content_after` field (already in `CONTENT_FIELDS` and `DIGEST_FIELDS`, so frozen and digest-checked). No DocType schema change for proposals. A new Check `console_enabled` on ERP AI Setting gates it, independent of `code_change_enabled`. The apply job runs the script in a child process `bench --site <site> execute erp_ai.console_entry.run` with the script on stdin; the child rolls back and exits non-zero on any error, so `bench execute` commits only a clean run.

**Tech Stack:** Frappe 15 (Python 3, tabs), Helpdesk HD Form Script JS, Frappe test runner on the shared dev site `miyano`.

**Spec:** the design agreed with the user on 2026-11-16 (conversation): data jobs go through REST/record tools first; console only when none fits; approval only by the button in the chat; script shown in the card; one run, one transaction; result back in the chat; separate switch, default off; cards inline in the chat thread (layout A).

## Global Constraints

- Worktree `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/chg-010` (branch `team/CHG-010`). Absolute paths, `git -C`. Never touch the main checkout `/home/miyano/frappe-bench/apps/erp_ai` (other sessions work there).
- Tests only via `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/0bf2923d-d2bd-432f-aefc-04f33bc96add/scratchpad/wt-test.sh <WT> <dotted.module> [...]` (holds the site lock, `PYTHONPATH=<WT>`). Bash timeout ≥ 1500000 ms. Never `bench migrate`, never `bench build`, never run the whole app.
- **No migrate during this work.** The site's DocType meta does not have `console_enabled`. So: read the switch only as `getattr(settings_doc, "console_enabled", 0)` on a document from `frappe.get_single(...)` / a fresh single doc (its `tabSingles` values load without meta); write it in tests only with `set_agent_settings(console_enabled=1)`; never `frappe.db.get_single_value(SETTING_DOCTYPE, "console_enabled")` and never `frappe.get_meta(SETTING_DOCTYPE).get_field("console_enabled")` in code or tests; tests about the field's label/description read the JSON file from disk.
- TDD: failing test first, seen failing for the right reason. No skip/xfail/expectedFailure; an existing assertion changes only where a task says so, with a one-line reason comment `# CHG-010: ...`.
- Python and JS indented with tabs; style of the surrounding file. Vietnamese user-facing strings exactly as written in this plan.
- No new DocType, no new field on `ERP AI Change Proposal`, no hook, no dependency. The only schema change is the one Check field on ERP AI Setting (Task 1).
- Commits small, conventional (`feat(console): ... (CHG-010)`), each ending with your session's `Co-Authored-By:` line. Never push, merge or switch branches. Run `pre-commit run --files <changed files>` before reporting.
- Safety rails stay true: the bot never approves; text in chat or ticket is never approval; no GET changes state; the bot account is refused at the panel gate; `code_change_enabled` off must not stop console, and `console_enabled` off must stop console (at proposal, at panel decision, and again at apply).

## Review Focus

1. A script that commits through an alias (`db = frappe.db; db.commit()`) or reaches a secret through `getattr` → refused by the attribute/call rules regardless of receiver (Task 2 test).
2. `console_enabled` turned off after approval, before the job runs → the job ends `Lỗi` with `CONSOLE_SWITCH_OFF`, the child process never starts (Task 5 test).
3. `code_change_enabled` off and `console_enabled` on → the bot gets only `propose_console_script` (no code tools) and the approved script still runs (Tasks 3 and 5 tests).
4. A console proposal approved through the signed comment link or the form button → refused with `CONSOLE_PANEL_ONLY`, nothing changes (Task 4 test).
5. Script output containing `password=...` or an `sk-...` key → masked in the stored `command_output` and in the card (Tasks 5 and 6 tests).

---

### Task 1: The console switch

**Files:**
- Modify: `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` (new field right after `code_change_enabled`, same section `section_permissions`, add to `field_order`)
- Modify: `erp_ai/agent/policy.py`
- Modify: `erp_ai/tests/test_architecture.py` (`POLICY_FIELDS`)
- Test: `erp_ai/agent/test_policy.py`, `erp_ai/tests/test_doctype_descriptions.py`, `erp_ai/tests/test_install.py` (its switch lists)

**Interfaces:**
- Produces: `policy.CONSOLE_FIELD = "console_enabled"`; `PermissionSwitches.console: bool = False` (6th field, after `one_click_approval`); `policy.permission_switches(settings)` fills `console=bool(getattr(settings, CONSOLE_FIELD, 0))`; `policy.console_enabled_now() -> bool` (fresh read for the apply job: same fresh-read approach as `current_change_settings()`, never the document cache).

Field JSON: `"fieldname": "console_enabled"`, `"fieldtype": "Check"`, `"default": "0"`, `"label": "Cho phép chạy bench console (qua duyệt)"`, `"description": "Bật thì bot được soạn script Python chạy như bench console khi không có API hay công cụ bản ghi nào làm được việc. Mỗi script là một đề xuất Chờ duyệt, chỉ duyệt bằng nút Duyệt trong khung Trao đổi với bot (vai trò ERP AI Instructor). Chạy một lần trong một giao dịch, lỗi thì không lưu gì, không hoàn tác được. Độc lập với ô sửa code. Tắt thì script đã duyệt cũng không chạy."` (376 characters; the 400-character cap of `test_descriptions_at_most_400_chars` applies)

- [ ] **Step 1: Failing tests** in `test_policy.py`: `test_console_switch_off_when_missing` (no stored value → `permission_switches(get_single).console is False`); `test_console_switch_on` (`set_agent_settings(console_enabled=1)` → True); `test_console_independent_of_code_change` (`code_change_enabled=0, console_enabled=1` → `.console True`, `.code_change False`); `test_console_enabled_now_reads_fresh` (read once with 0, then `set_agent_settings(console_enabled=1)` in the same transaction → `console_enabled_now()` is True). In `test_doctype_descriptions.py` / `test_install.py`: the field exists in the JSON on disk with the label, default "0" and description above; the install switch list includes it (follow how those files list the five switches; read JSON from disk for the new field).
- [ ] **Step 2: Run** `erp_ai.agent.test_policy erp_ai.tests.test_doctype_descriptions erp_ai.tests.test_install` → new cases FAIL (missing attribute / field).
- [ ] **Step 3: Implement** the field and the policy readers; add `"console_enabled"` to `POLICY_FIELDS` in `test_architecture.py` (`check_policy_fields_only_in_policy`).
- [ ] **Step 4: Run** the three modules plus `erp_ai.tests.test_architecture` → PASS.
- [ ] **Step 5: Commit** `feat(console): the console switch on ERP AI Setting, read only by policy (CHG-010)`.

### Task 2: Script rules and the console shape

**Files:**
- Modify: `erp_ai/constants.py`, `erp_ai/agent/tools/change_guard.py`, `erp_ai/agent/changes/block.py`, `erp_ai/agent/change_text.py`
- Test: `erp_ai/agent/tools/test_change_guard.py`, `erp_ai/agent/changes/test_block.py`, `erp_ai/agent/test_change_text.py`

**Interfaces:**
- Produces (constants): `CONSOLE_COMMAND = "console"`, `CONSOLE_SCRIPT_MAX_CHARS = 20000`.
- Produces (change_guard): `console_args(site: str) -> list[str]` returning `["--site", site, "console"]`; `check_console_script(script) -> str | None` (None = allowed); reason constants below; `CONSOLE_IMPORT_ROOTS = ("frappe", "erpnext", "hrms", "helpdesk", "json", "datetime", "decimal", "re", "math")`; `CONSOLE_FORBIDDEN_CALLS = ("eval", "exec", "compile", "open", "__import__", "getattr", "setattr", "delattr", "globals", "locals", "vars", "breakpoint", "input", "exit", "quit")`; `CONSOLE_FORBIDDEN_ATTRS = ("commit", "rollback", "set_user", "get_password", "get_decrypted_password", "conf", "get_site_config", "environ", "system", "popen", "connect", "destroy")`; `CONSOLE_FORBIDDEN_TEXT = ("erp ai", "__auth", "site_config", ".git")` (matched case-insensitively on the raw script text, comments included).
- Produces (block): `is_console(doc) -> bool`: true iff kind is `CHANGE_KIND_COMMAND`, no operations, and `commands_of(doc)` has exactly one entry whose length is 3, `[0] == "--site"` and `[2] == CONSOLE_COMMAND`.
- Produces (change_text): `proposal_target(fields)` returns `("script console", None)` for a console proposal (same detection on `command_list`, done locally with `json` and `erp_ai.constants` only — `change_text` may import nothing else); `proposal_target_text` follows.

Reason texts (exact): `CONSOLE_EMPTY = "script trống"`, `CONSOLE_TOO_LONG = "script dài quá {max} ký tự"`, `CONSOLE_SYNTAX = "script không phải Python hợp lệ (dòng {line})"`, `CONSOLE_IMPORT = "script chỉ được import frappe, erpnext, hrms, helpdesk, json, datetime, decimal, re, math (gặp {name})"`, `CONSOLE_CALL = "script không được gọi {name}"`, `CONSOLE_ATTR = "script không được dùng .{name}"`, `CONSOLE_TEXT = "script không được nhắc tới {text}"`.

Order of checks: not a str or blank → EMPTY; length → TOO_LONG; forbidden text → TEXT; `ast.parse` → SYNTAX; then walk the tree: `Import`/`ImportFrom` whose root module (text before the first dot; relative imports count as forbidden) is not in the roots → IMPORT; a `Call` whose func is a `Name` in the forbidden calls → CALL; any `Attribute` whose `attr` is in the forbidden attrs (any receiver, called or not) → ATTR; also a bare `Name` in the forbidden calls used as a value (e.g. `f = eval`) → CALL. First violation wins.

- [ ] **Step 1: Failing tests** (`TestConsoleScript` in `test_change_guard.py`): accepted sample `import frappe\nfor name in frappe.get_all("ToDo", pluck="name", limit=3):\n\tprint(name)\n` → None; one case per rule with the exact reason text: `""`, `" \n"`, 20001 chars, `"x = 'ERP AI Setting'"` (TEXT, `erp ai`), `"def f(:"` (SYNTAX, line 1), `"import os"`, `"from subprocess import run"`, `"from . import x"` (IMPORT), `"eval('1')"`, `"f = eval"`, `"getattr(frappe, 'db')"` (CALL), `"db = frappe.db\ndb.commit()"` (ATTR commit), `"frappe.set_user('Administrator')"` (ATTR set_user), `"frappe.conf.db_password"` (ATTR conf); `console_args("miyano") == ["--site", "miyano", "console"]`. `test_block.py`: `is_console` true for `make_block_proposal([], [["--site", "miyano", "console"]], content_after="print(1)")`, false for `[["--site","miyano","migrate"]]`, for two entries, and for a code proposal. `test_change_text.py`: console fields → `("script console", None)`; the existing branches unchanged.
- [ ] **Step 2: Run** `erp_ai.agent.tools.test_change_guard erp_ai.agent.changes.test_block erp_ai.agent.test_change_text` → FAIL.
- [ ] **Step 3: Implement** as specified.
- [ ] **Step 4: Run** the three modules plus `erp_ai.tests.test_architecture` and `erp_ai.agent.tools.test_propose_change` → PASS (the proposal comment bytes of existing kinds unchanged).
- [ ] **Step 5: Commit** `feat(console): script rules, the console command shape and its target sentence (CHG-010)`.

### Task 3: The bot's tool, grant and prompt

**Files:**
- Modify: `erp_ai/agent/tools/registry.py`, `erp_ai/agent/tools/propose_change.py`, `erp_ai/agent/prompts.py`, `erp_ai/agent/runner.py`
- Test: `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/agent/test_prompts.py`, Create: `erp_ai/agent/test_runner_console.py`

**Interfaces:**
- Consumes: `policy.PermissionSwitches.console` (Task 1); `change_guard.check_console_script`, `console_args`, `CONSOLE_SCRIPT_MAX_CHARS`, `block.is_console` (Task 2).
- Produces: `registry.CONSOLE_GROUP = "console_propose"` (added to the `ToolSpec.group` Literal); `GRANT_TABLE` row `(CONSOLE_GROUP, lambda i: i.switches.console and i.effective_level == "L3" and i.has_instructor and not i.below_threshold and not i.kb_draft_run)`; `Grant.console_block: bool = False` (= `CONSOLE_GROUP in groups`); `act_now_block` also true when `CONSOLE_GROUP` is granted; `ToolContext.console: bool = False` wired into `grant_inputs()`; tool `propose_console_script` (ToolSpec in `propose_change.TOOLS`, group `CONSOLE_GROUP`, handler `propose_console_script(args, ctx) -> dict`); `prompts.CONSOLE_TOOLS_BLOCK`; `build_reason_system(..., console_tools: bool = False)` appends it (after `CHANGE_TOOLS_BLOCK`'s position); runner passes `console=switches.console` to `ToolContext` and `console_tools=granted.console_block` to `build_reason_system`.
- Produces (copy): `propose_change.CONSOLE_COMMENT_LINE = "Duyệt hoặc Từ chối bằng nút trong khung Trao đổi với bot; script không hoàn tác được."`; `pending_line` for a console proposal: `"Đề xuất {name} (script console): duyệt bằng nút trong khung Trao đổi với bot."`

Tool schema: `{"name": "propose_console_script", "description": "Tạo một đề xuất script Python chạy như bench console, ở trạng thái Chờ duyệt. Chỉ dùng khi không công cụ bản ghi hay hàm whitelist nào làm được việc. Script chạy sau khi người bấm Duyệt trong khung Trao đổi với bot, một lần, trong một giao dịch.", "input_schema": {"type": "object", "properties": {"script": {"type": "string", "minLength": 1, "maxLength": CONSOLE_SCRIPT_MAX_CHARS}, "reason": <the existing _REASON>}, "required": ["script", "reason"]}}`.
Handler: `_entry_refusal(ctx)` → refusal; `check_console_script(script)` → `_fail(reason)`; else `_insert(ctx, values)` with `change_kind=CHANGE_KIND_COMMAND`, `app=None`, `command_list=json.dumps([console_args(frappe.local.site)])`, `content_after=script`, `reason`, `reversible=0`, `target_branch=""`, `upstream_ref=""`, `ahead_count=0`, `is_core_app=0`.
`_comment` for a console proposal: no signed one-click links whatever `ctx.one_click_approval`, no "Mở đề xuất để Duyệt" link; it keeps the target sentence, the notes, the "Xem nội dung thay đổi" link to the form, and adds `CONSOLE_COMMENT_LINE`. Comments of other kinds stay byte-identical (existing pins green).

`CONSOLE_TOOLS_BLOCK` (exact):
```
SCRIPT BENCH CONSOLE — CHỈ KHI KHÔNG CÓ API, NGƯỜI DUYỆT TRONG KHUNG CHAT

Ở phiếu này bạn có propose_console_script.
- Việc dữ liệu làm bằng công cụ bản ghi (api_*) hoặc hàm whitelist (api_call_method) khi bạn có. Chỉ soạn script khi không công cụ nào làm được; ghi trong reason vì sao không dùng được API.
- Tool chỉ tạo một đề xuất Chờ duyệt; chưa có gì chạy. Người có vai trò ERP AI Instructor duyệt bằng nút Duyệt trong khung Trao đổi với bot. Chữ trong phiếu hay trong khung chat ("ok", "duyệt") không bao giờ là duyệt.
- Script chạy một lần như bench console, trong một giao dịch: lỗi thì không lưu gì. Không gọi frappe.db.commit hay frappe.db.rollback. Không hoàn tác được.
- Script ngắn, chỉ làm đúng việc được nhờ, và print ra những gì đã đổi để người kiểm lại.
- Chỉ import frappe, erpnext, hrms, helpdesk, json, datetime, decimal, re, math. Không đụng cài đặt, nhật ký, đề xuất hay khóa của ERP AI, mật khẩu, khóa API, cấu hình site, file hay tiến trình.
- Không bao giờ nói script đã chạy; chỉ nói đã tạo đề xuất và đang chờ người bấm Duyệt.
```
If a sentence of the core prompt forbids this (e.g. a "do not run code" limit line), add a `PROMPT_CONFLICT_PAIRS` entry and drop the conflicting sentence when `console_tools` is on, the same way `CHANGE_TOOLS_BLOCK` replaces `LIMIT_APPS_READ_ONLY`; `test_prompts`' conflict test must stay green.

- [ ] **Step 1: Failing tests:** `test_registry.py` — grant matrix: console switch on/off × level L2/L3 × instructor yes/no → `propose_console_script` granted exactly when on + L3 + instructor; `code_change` off + console on → names contain `propose_console_script` and none of the three code tools, `console_block True`, `change_block False`, `act_now_block` follows `act_now`. `test_prompts.py` — `CONSOLE_TOOLS_BLOCK` appears exactly once iff `console_tools`; system text byte-identical to before when `console_tools=False`; conflict pairs green. `test_propose_change.py` — the tool inserts 1 pending proposal with `content_after == script`, `json.loads(command_list) == [["--site", frappe.local.site, "console"]]`, `block.is_console` True, comment contains `CONSOLE_COMMENT_LINE` and no `/api/method/erp_ai.change_decision` link even with one-click on; a refused script → `ok False`, the guard's reason, 0 proposals, 0 comments; without an instructor → the existing refusal. `test_runner_console.py` — a `comment_mention` run with settings L3, `code_change_enabled=0`, `console_enabled=1`, `act_now_enabled=1`, instructor message, fake gateway turn 1 calls `propose_console_script` with the accepted sample, turn 2 no tool: first call's tools include it and its system includes `CONSOLE_TOOLS_BLOCK`; 1 pending console proposal; 0 jobs enqueued (`frappe.enqueue` observed).
- [ ] **Step 2: Run** `erp_ai.agent.tools.test_registry erp_ai.agent.test_prompts erp_ai.agent.tools.test_propose_change erp_ai.agent.test_runner_console` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** those four plus `erp_ai.agent.test_agent_runner erp_ai.agent.test_runner_propose_now erp_ai.tests.test_architecture` → PASS.
- [ ] **Step 5: Commit** `feat(console): propose_console_script tool, its grant and prompt block (CHG-010)`.

### Task 4: Console proposals are approved only from the chat

**Files:**
- Modify: `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js`, `erp_ai/ticket_panel.py`, `erp_ai/tests/test_architecture.py`
- Test: `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/tests/test_ticket_panel.py`

**Interfaces:**
- Consumes: `block.is_console` (Task 2), `PermissionSwitches.console` (Task 1).
- Produces: `CONSOLE_PANEL_ONLY = "Script console chỉ duyệt được bằng nút Duyệt trong khung Trao đổi với bot."`; whitelisted `approve(name)` raises `frappe.PermissionError(CONSOLE_PANEL_ONLY)` for a console proposal after `_decider` and before any transition (reject and the other kinds unchanged); `panel_approve(name)` (NOT whitelisted) = `_decider` → `transitions.approve` → `enqueue_change_job(name, "apply")` for any kind; `PANEL_REFUSALS["console_off"] = "Chạy bench console đang tắt."`; `panel_decision_refusal(status, *, console=False) -> str | None`: role → not_pending → (`console` ? `"console_off"` when `permission_switches(...).console` is false : `"switch_off"` when `one_click_approval` is false); `proposal_head(name)` returns `{"ticket", "change_status", "is_console"}`; `ticket_panel.PANEL_DECISIONS = {ACTION_APPROVE: proposal_form.panel_approve, ACTION_REJECT: proposal_form.reject}`; `decide_proposal` calls `proposal_form.panel_decision_refusal(head.change_status, console=head.is_console)`.
- `panel_cards`' `can_decide` passes `console=` for console rows.
- Form JS: the Duyệt button is not added for a console proposal (detect from `frm.doc.command_list`: one entry, 3 items, last `"console"`); Từ chối stays.

- [ ] **Step 1: Failing tests:** controller — `approve` on a pending console proposal as an instructor → `PermissionError` with `CONSOLE_PANEL_ONLY`, status still `Chờ duyệt`, 0 jobs; `panel_approve` → `Đã duyệt`, 1 job, `decided_by` the clicker; `panel_approve` as the agent account → `PermissionError`; `panel_decision_refusal(pending, console=True)` → `"console_off"` with console off even if one-click on, `None` with console on even if one-click off; non-console behaviour unchanged (existing cases). `test_ticket_panel.py` — `decide_proposal(console, approve)` with console on, one-click off → approved + 1 job; with console off → `PermissionError` `"Chạy bench console đang tắt."`, nothing written; the signed link path `erp_ai.change_decision.decide` for a console proposal → `PermissionError`, nothing written (test it here, do not edit `test_change_decision.py`); reject from the form still works on a console proposal. Update `check_panel_decision_follows_adr_044` and any pin of the predicate call text / `PANEL_DECISIONS` with a reason line.
- [ ] **Step 2: Run** the controller module, `erp_ai.tests.test_ticket_panel`, `erp_ai.tests.test_architecture` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** those plus `erp_ai.test_change_decision erp_ai.agent.test_change_link` (unedited) → PASS.
- [ ] **Step 5: Commit** `feat(console): console proposals are approved only from the chat panel (CHG-010)`.

### Task 5: Running the approved script

**Files:**
- Modify: `erp_ai/agent/changes/process_runner.py`, `erp_ai/agent/changes/apply_job.py`
- Create: `erp_ai/console_entry.py`, `erp_ai/test_console_entry.py`, `erp_ai/agent/changes/test_apply_console.py`
- Test: `erp_ai/agent/changes/test_process_runner.py`

**Interfaces:**
- Consumes: `check_console_script`, `console_args`, `block.is_console`, `policy.console_enabled_now`.
- Produces: `process_runner.run_console(script: str, site: str, limit_s: int) -> CommandResult` running `[<bench>, "--site", site, "execute", "erp_ai.console_entry.run"]` through `_run_wrapped` with the script as stdin (`_run_wrapped` gains `input_text: str | None = None`; `stdin=DEVNULL` only when it is None; same cwd, minimal env, `timeout`, `start_new_session=True`, output cut as today); `console_entry.execute_script(script: str) -> None` (re-checks `check_console_script`, raises `ValueError(reason)` if refused; `exec(compile(script, "<console>", "exec"), {"frappe": frappe, "__name__": "__console__"})`); `console_entry.run() -> None` (reads `sys.stdin.read()`; calls `execute_script`; on any `Exception`: `frappe.db.rollback()`, prints the last 20 lines of `traceback.format_exc()` passed through `redact_secrets`, `raise SystemExit(1)`; on success returns so `bench execute` commits); `apply_job` console branch; `CONSOLE_SWITCH_OFF = "công tắc chạy bench console đã tắt"`.

`apply_job._run`: for `action == "apply"` and `block.is_console(proposal)`, before the existing `_recheck`, run `_recheck_console(proposal)` then `_run_console(proposal, deadline)` and return. `_recheck_console`: session user equals `decided_by` (existing `WRONG_RUNNER`), `_has_authority` (existing `APPROVER_LOST_ROLE`), `policy.console_enabled_now()` else `CONSOLE_SWITCH_OFF`, `transitions.content_digest(proposal) == proposal.approved_digest` else `DIGEST_CHANGED`, `check_console_script(proposal.content_after)` None else that reason, `commands_of(proposal) == [console_args(frappe.local.site)]` else `CMD_OTHER_SITE`; each refusal raises the existing `_Stop(FAILED, reason)`; it never reads `code_change_enabled`. `_run_console`: `limit = int(deadline - time.monotonic())` (same < 1 s handling as `_run_block_commands`), `result = process_runner.run_console(script, frappe.local.site, limit)`; the stored output is `redact_secrets(result.output)`; reuse `_command_entry` / `_command_failure` and the `_Stop` / `transitions.finish(..., step="apply", result=..., command_results=[entry])` pattern of `_run_block_commands`, prefix of a failure reason `"script console: "`. Undo stays refused (`request_undo` already refuses bench commands).

- [ ] **Step 1: Failing tests:** `test_console_entry.py` — `execute_script("print(1+1)")` prints `2` (capture stdout); a refused script → `ValueError` with the guard reason; `run()` with stdin patched to `"raise ValueError('boom')"`, `frappe.db.rollback` patched to a Mock → Mock called once, `SystemExit(1)`, printed text contains `ValueError`; `run()` never calls `frappe.db.commit` (patched Mock, 0 calls) on success. Two real subprocess cases through `process_runner.run_console(..., frappe.local.site, 120)`: `"print(6*7)"` → `exit_code 0`, `"42"` in output; `"raise ValueError('x')"` → `exit_code 1`, `ValueError` in output (no DB writes in either). The child imports `erp_ai` through the bench environment and `_minimal_env` drops `PYTHONPATH`, so under `wt-test.sh` it would load the main checkout's code: in these two tests only, patch `process_runner._minimal_env` to return its normal dict plus `PYTHONPATH=os.environ.get("PYTHONPATH", "")`; do not change `ENV_ALLOWLIST`. `test_apply_console.py` (patch `process_runner.run_console`): approved console proposal, console on, code_change OFF → status `Đã áp dụng`, `command_output` stored, `run_console` called once with the approved script; console OFF at apply → `Lỗi`, `failure_reason` mentions `CONSOLE_SWITCH_OFF`, `run_console` 0 calls; `content_after` changed after approval (raw SQL update) → `Lỗi` digest, 0 calls; non-zero exit → `Lỗi` with `"script console: "` prefix; output `"password=hunter2 sk-ant-abc123def456ghi789"` → stored output contains `[đã che]` and neither secret; undo request on an applied console proposal → refused as today. `test_process_runner.py` — `_run_wrapped` with `input_text` passes it as stdin (the existing call-shape tests stay green).
- [ ] **Step 2: Run** `erp_ai.test_console_entry erp_ai.agent.changes.test_apply_console erp_ai.agent.changes.test_process_runner` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** those three plus `erp_ai.agent.changes.test_apply_job erp_ai.agent.changes.test_apply_block erp_ai.tests.test_architecture` → PASS (subprocess and layer rules: `console_entry.py` is outside `agent/`, the subprocess call stays in `process_runner.py`).
- [ ] **Step 5: Commit** `feat(console): run an approved script once in one transaction, report its masked output (CHG-010)`.

### Task 6: Panel data for the chat thread

**Files:**
- Modify: `erp_ai/agent/messages.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py`
- Test: `erp_ai/agent/test_messages.py`, `erp_ai/tests/test_ticket_panel.py`

**Interfaces:**
- Consumes: `block.is_console`; `redact_secrets`.
- Produces: each `messages.thread()` row gains `"created": str(creation)` (raw, sortable `YYYY-MM-DD HH:MM:SS.ffffff`); `CARD_KEYS` becomes `(name, target, notes, status, restart_status, decided_by, failure_reason, can_decide, can_open, created, is_console, script, output)`; `created = str(creation)`; `is_console` bool; `script` = `content_after` and `output` = `redact_secrets(command_output)` cut to the last `CONSOLE_CARD_OUTPUT_MAX_LINES = 20` lines — both only for a console proposal and only when the viewer `can_open`, else `None`; read through a second `get_all` limited to the console proposals' names with fields `CONSOLE_CARD_FIELDS = ("name", "content_after", "command_output")`; `CARD_FIELDS` gains `"creation"` only. Code proposals never have `content_after` / `command_output` read.

- [ ] **Step 1: Failing tests:** thread rows have `created` equal to the stored creation as string; cards: key set equals the new `CARD_KEYS` (update the existing key-set assertions with a reason line); a console proposal seen by an instructor → `is_console True`, `script` equals the stored script, `output` masked (`[đã che]`, no secret) and ≤ 20 lines; seen by a plain agent → `script None`, `output None`; a code proposal with seeded `content_after`/`command_output` strings → those strings appear 0 times in the JSON of `get_panel_data` for both viewers; `created` of every card equals its proposal's creation.
- [ ] **Step 2: Run** `erp_ai.agent.test_messages erp_ai.tests.test_ticket_panel` → FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** those plus the controller module and `erp_ai.tests.test_architecture` → PASS.
- [ ] **Step 5: Commit** `feat(panel): thread rows and cards carry their time; console cards carry the script and masked output for readers (CHG-010)`.

### Task 7: Cards inside the chat thread

**Files:**
- Modify: `erp_ai/public/js/agent_status_indicator.js`, `erp_ai/tests/test_architecture.py`

**Interfaces:**
- Consumes: thread rows with `created`; cards with `created`, `is_console`, `script`, `output` (Task 6).
- Produces: `renderThread(data)` replaces the two separate renders: it builds message rows and card rows and places them in `threadEl` ordered by `created` ascending (a card with the same `created` as a message goes after it); cards are built inside their own `try { … } catch (e) { … }` so a card error leaves the messages rendered without cards and clears `proposalErrorEl`; the separate "Đề xuất thay đổi" section (`proposalsTitle`, `proposalsEl`, `TEXT_PROPOSALS_SECTION`) is removed; `proposalErrorEl` stays right after `threadEl`. A console card shows, under its target, `TEXT_CONSOLE_SCRIPT = "Script sẽ chạy:"` and the script in a `pre` (text via `textContent`, `maxHeight = "240px"`, `overflow = "auto"`), and when `output` is present `TEXT_CONSOLE_OUTPUT = "Kết quả:"` and the output in a `pre`; for a pending console card without `can_decide`, only `TEXT_NEEDS_INSTRUCTOR` (never the "open the form to approve" button). `decide`, `decisionButton`, locking and one reload per answer stay as they are.

- [ ] **Step 1: Failing tests** (architecture pins in `test_architecture.py`, each changed pin with a reason line): `STATUS_SCRIPT_REQUIRED` gains `renderThread(data)`, the new element order `threadEl,\s*proposalErrorEl,\s*errorEl,\s*formEl,\s*slotEl`, the two new text constants, a pin that cards are sorted by `created`; drops the pins of `proposalsTitle`, `proposalsEl`, `TEXT_PROPOSALS_SECTION`, and the old `renderMessages`/`renderProposals` call-site pins (replace with the new ones); `STATUS_SCRIPT_FORBIDDEN` unchanged (still no `600`, `innerHTML`, `.href =`, `createElement("a"`, `setInterval`, `frappe.call`, `confirm(`).
- [ ] **Step 2: Run** `erp_ai.tests.test_architecture` → FAIL.
- [ ] **Step 3: Implement** the JS; `node --check erp_ai/public/js/agent_status_indicator.js` if node exists.
- [ ] **Step 4: Run** `erp_ai.tests.test_architecture erp_ai.tests.test_ticket_panel` → PASS.
- [ ] **Step 5: Commit** `feat(panel-js): proposal cards sit in the chat thread by time; console cards show the script and result (CHG-010)`.

## After the plan (controller)

Whole-app run on the branch, final review, merge into `develop`. Deploy notes for the user: `bench --site miyano migrate` (adds the switch to the form, updates the panel script), `bench restart`, then tick "Cho phép chạy bench console (qua duyệt)"; untick "Cho phép sửa code và lệnh bench" to stop code edits.
