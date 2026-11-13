# Review raw T30 — round 1 (request-changes)

Diff: `git diff b63a667..team/FEAT-001-task-30` (d9dca07)

## Findings (verbatim from reviewer)
major | STD-ERR-4 | erp_ai/agent/runner.py:316 | When `execute_tool` raises, the exception is turned into an `is_error` tool_result for the model and nothing else. Nothing reaches ERP AI Log (`error` stays empty on the turn's `reason` entry) or Error Log. For a read tool that crashes (for example get_ticket) the only trace is the tool name in `tools_called`. For write tools the only trace is `ok: false`. A tool bug in prod would go unnoticed (design 4.9: "Mỗi lượt ... 1 bản ghi ERP AI Log"). | Collect `f"tool {name}: {type(exc).__name__}"` per failed block and write it into the turn entry's `error` field, joined if there are several. Use the class name only, no message, which fits D-20 and STD-SEC-6. Add an assertion in `test_tool_exception_becomes_error_result_and_run_continues` that `first.error` names the tool and `KeyError` and does not contain "bí mật".

minor (dev's call, fix if cheap): (1) test_runner.py:700 `round(first.cost_usd + second.cost_usd, 6) == 0.02` is not a hand-computed cost check; compute the cost by hand from usage and the configured prices. (2) test_runner.py:600 `test_stops_after_max_turns` depends on the stored `max_turns_per_run` being 8; set it explicitly (like DAILY_LIMIT). (3) runner.py:328 `before`/`after` keyed by tool name overwrite on a second call of the same write tool in one turn; test_runner.py:712 `deadline > monotonic()` is weak.

## Tech-lead ruling
Fix the major in round 1; minors (1) and (2) are cheap and should be done; (3) deferred if not trivial. Known out of scope: skipped/reason of set_classification (review-36 design-gap); fetch_ticket_comments twice per run (authority.py).
