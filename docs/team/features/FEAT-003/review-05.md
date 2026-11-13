# Review T5 (FEAT-003) — approve, 2 rounds

- Verdict: approve (round 2, scoped). Round 1: request-changes (4 majors STD-DOC-2: `predicted_confidence`, `instructor`, `stop_reason`, `tools_called` descriptions contradicted the code that writes them; 4 minors). Details: review-T5-r1.md.
- Diff command: `git diff b433459..3765c3e` (BASE b433459, head 3765c3e); fix diff `git diff 15d4aa3..3765c3e`.
- Round 2: all 4 majors and 4 minors ADDRESSED (each reworded text re-verified against runner.py, authority.py, write_ticket.py, tasks.py; new `test_forbidden_phrases_absent`; shared harness not weakened).
- Evidence: RED 4 failures (round 1) / 2 failures `test_required_phrases_present` + `test_forbidden_phrases_absent` (round 2); GREEN test_doctype_descriptions 10 OK; migrate with Setting equal; full on branch `Ran 613 tests ... OK` with complete snapshots equal; after merge T1..T7 `Ran 621 tests ... OK`.
- Deferred minors: `cost_usd` says "cộng vào" the month's spent but tasks.py:52 replaces it with the recomputed total; label "Khóa đã trả lời" still contradicts the new `credential_label` text for gateway_error rows; `time_budget` rows also store the last key tried and the label is empty on `no_key` rows.
