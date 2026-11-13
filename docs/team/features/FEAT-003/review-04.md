# Review T4 (FEAT-003) — approve, 2 rounds

- Verdict: approve (round 2, scoped). Round 1: request-changes (1 major STD-DESIGN-5: `provider` description said calls go to the chosen provider, but the gateway only uses Anthropic; 2 minors). Details: review-T4-r1.md.
- Diff command: `git diff f7dc6b1..909a08d` (BASE f7dc6b1, head 909a08d); fix diff `git diff 42fbd10..909a08d`.
- Round 2: all findings ADDRESSED. Evidence: RED `provider: thiếu cụm ['bỏ qua']`; mutation proof (credential JSON restored from f7dc6b1): 4 failures (missing 18/18 descriptions, breaks); GREEN test_doctype_descriptions 8 OK, test_erp_ai_credential 6 OK, test_erp_ai_setting 19 OK; migrate with Setting values equal; full `Ran 621 tests ... OK` after the merge of T1..T7 (T4 included).
- Deferred: `enabled` check is not pinned by the new wording; the AC-4 stored-value test only compares Setting rows (QA to check Credential labels such as the example "Khóa chính", which the dev found not to be a real label on the site).
