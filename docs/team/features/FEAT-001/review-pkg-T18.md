# Review package FEAT-001 T18 (BASE 0718c42..ede7983, branch team/FEAT-001-task-18)

Diff command (authoritative, read-only git): `git diff 0718c42..team/FEAT-001-task-18`

Commit: ede7983. Files: erp_ai/gateway/__init__.py, erp_ai/gateway/test_gateway.py.

Task: T18 line in tasks.md; design 3.4.1 (probe_credential, reprobe_exhausted_keys; recovery notice at design lines ~404/494). Criteria: AC-18 (only `Hết hạn mức` keys are re-probed), AC-19 (per-key result).
Scope notes to judge (do not assume either way): (a) the dev extracted the per-key attempt of call_model into `_attempt_key` shared by call_model and probe_credential (STD-DESIGN-4) — check call_model behavior is unchanged; (b) extra error kinds `not_found`, `no_secret`; (c) `reprobe_exhausted_keys` sends a recovery notice via `send_notice` (T35 later wraps it in a scheduler job and must not double-notify); (d) the dev wrote the implementation first and then reverted it to produce the red run (not strict test-first) — judge only whether the tests now truly pin behavior.

Dev evidence (raw): RED 13 errors (AttributeError missing function, after revert); GREEN test_gateway Ran 60 OK; full app Ran 235 OK; pre-commit exit 0.

Run `git diff 0718c42..team/FEAT-001-task-18` for the verbatim code.
