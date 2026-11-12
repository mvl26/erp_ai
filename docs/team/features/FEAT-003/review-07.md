# Review T7 (FEAT-003) — approve, 2 rounds

- Verdict: approve (round 2, scoped). Round 1: request-changes (1 major STD-TEST-2: AC-8 test data was cut down: 2/3/2 instead of 3/2/2 plus a decoy keyword comment on another ticket). Details: review-T7-r1.md.
- Diff command: `git diff 3cfa6bf..a0c75f5` (BASE 3cfa6bf, head a0c75f5); fix diff `git diff 32dd12e..a0c75f5`.
- Round 2: major ADDRESSED (exact AC-8 data, 5 names in order; mutation: wrong-ticket read shows decoy as a 6th message); minors 3, 4 ADDRESSED (bot XSS payload; created_at derived via format_datetime). The literal `<script>` text left after `html_to_plain_text` is accepted (AC-12 allows text; page uses textContent).
- Evidence: RED 4 failed + 1 error (round 1); GREEN test_ticket_panel 16 OK, test_architecture 60 OK; full after merge T1..T7 `Ran 621 tests ... OK`.
- Deferred minors: keyword is matched on markdown-rendered content (load.py:169), a keyword with `_`/`*` could drift from the gate; deleted-user author falls back to the owner email (activity.py:335); `assertRegex` on created_at assumes dd-mm-yyyy site format.
