# Review T2 (FEAT-003) — approve, 2 rounds

- Verdict: approve (round 2, scoped). Round 1: request-changes (1 major STD-DESIGN-2: `state.call(METHOD_GET_PANEL_DATA, ...)` passed a variable, ADR-009 needs a string literal; minors a, b, c). Details: review-T2-r1.md.
- Diff command: `git diff 1560098..10990fa` (BASE 1560098, head 10990fa); fix diff `git diff 31c4b75..10990fa`.
- Round 2: major ADDRESSED (literal call; new static test `test_status_script_calls_use_literal_panel_methods` + checker test; RED against the old JS "line 227: first argument of call( is not a string literal", GREEN test_architecture 60 OK); minors a, b ADDRESSED; c left for T14.
- Evidence: RED `test_status_script_static_rules` "function setupForm({ doc, call, router })' not found"; GREEN test_architecture 58 -> 60 OK, test_install 22 OK; after merge of T1..T7 `Ran 621 tests ... OK`.
- Deferred (to the T15 handoff): module docstring says "Nothing here imports product code" but test_architecture.py now imports `PANEL_METHODS` (parse as text or fix the docstring); regex at the literal-call check misses `call (`, `call?.(`, `["call"](`; ADR-009 forbidden list gaps: `setAttribute("src"|"href", ...)`, `removeEventListener`, `innerText +=`, `createElement("A")` (design-level; add if ADR-009 forbids them); old-state edge: an old script's `reset` does not close the panel on leaving the ticket.
