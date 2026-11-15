---
name: acceptance-gap-patterns
description: Recurring acceptance gaps in erp_ai (design §8 note clauses vs asserts; patched-raise vs real setting; stubbed model hides token-cap failure; savepoint rollback keeps after_commit jobs)
metadata:
  type: project
---

Gaps seen in FEAT-006 acceptance (2026-11-13), likely to recur:
- Design §8 "note" column promises assertions (e.g. "priority correct; SLA count before = after") that the integration test silently drops. Compare each note clause with the assert lines, not just the test name.
- Error-branch tests patch the unit to "write then raise" a stand-in exception instead of flipping the real site setting; the real raise is proven only in a separate tool-level test. Record as two-halves coverage.
- Runner maps any exception of a write unit to one fixed comment reason, which may misstate the cause.
- All runner tests stub the model gateway, so a too-low `max_tokens` is invisible to `cmd.test`. The real eval (`bench execute erp_ai.eval.export_tickets.export` then `erp_ai.eval.run_eval.run`, JSONL in scratchpad) showed 2/2 `max_tokens` at 600; site ERP AI Log already had `unparseable` at 400. Always run the real eval when a criterion touches classification, and cross-check `SELECT model, MAX(output_tokens), stop_reason FROM tabERP AI Log`.
  Root cause found in rework (2026-11-13): Haiku 5.5 thinks by default and thinking tokens count against `max_tokens`; fix was `thinking: disabled` for `claude-haiku-*` in `gateway.call_model`, after which the same eval gave 0 hits, output max 285. Labeled tickets on site dev: only 2 (both category B) — eval numbers are not a quality signal.
- DocType JSON description edits without bumping `modified` still reach the site on migrate (Frappe compares `migration_hash`); check with `SELECT description FROM tabDocField`.
- Frappe `rollback(save_point=...)` does not reset `after_commit`; `enqueue_create_notification` is after-commit outside tests but `now=True` in tests, so ghost notifications cannot show up in tests.

**Why:** junit all-green hid an AC-11 coverage gap and a production-breaking token cap; only reading assertions and a live eval revealed them.
**How to apply:** for every AC row, read the asserts against each AC clause; for model-facing criteria run the live eval. See [[bench-run-tests-quirks]].
