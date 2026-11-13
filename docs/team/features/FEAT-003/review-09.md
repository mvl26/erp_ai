# Review 09 (T11, T15) approve

- T11: round 1 request-changes (1 major STD-TEST-2: skip reason of AC-10 not compared), round 2 approve. Diff: `git diff b075d2d..team/FEAT-003-task-11` (head 7bd0706). Rounds: 2 (max_rework=3). Dev green `test_ticket_panel` 36 OK; mutations red (AGENT_USER owner: 11 red; keyword not appended: red).
- T15: round 1 approve. Diff: `git diff b075d2d..team/FEAT-003-task-15` (head 593f736). Merge c76d89e. Rounds: 1. Dev green `test_architecture` 77 OK; 20+ mutations red.
- Deferred (minor): T11 `TITLE_RUN_FAILED` / `self.log_error` unused (assert not logged or remove), redundant `call_count` assert, no check that `decisions` has exactly 1 entry; T15 gate scanner self-test loops over its own tuple, no string-only case for the forbidden-call scanner, `socket.once(` / `call (` / `doc.add_comment(` bypasses not covered.
