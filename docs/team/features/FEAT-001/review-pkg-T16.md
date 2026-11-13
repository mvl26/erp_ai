# Review package FEAT-001 T16 (BASE 0c5e216..545d4be, branch team/FEAT-001-task-16)

Diff command (authoritative, read-only git): `git diff 0c5e216..team/FEAT-001-task-16`

Commit: 545d4be. Files: erp_ai/gateway/credentials.py (new), erp_ai/gateway/test_gateway.py, erp_ai/test_utils.py (add_credential only).

Task: T16 line in tasks.md; design 3.4.2/3.4.3 (key selection, apply_failure / apply_success, header thresholds). Criteria: AC-17, NFR-5 (decryption only here), ADR-004 (single writer of key status).

Dev evidence (raw): RED Ran 22 FAILED (errors=12, stubs NotImplementedError); GREEN Ran 22 OK; full app Ran 198 OK; pre-commit exit 0.

Run `git diff 0c5e216..team/FEAT-001-task-16` for the verbatim code.
