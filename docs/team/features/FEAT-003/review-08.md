# Review 08 (T9, T13, T10, T14) approve

- T9: round 1 request-changes (2 major STD-TEST-5), round 2 approve. Diff: `git diff c3f32b5..team/FEAT-003-task-9` (head 68ad1a1). Merge 260db00. Rounds: 2 (max_rework=3).
- T13: round 1 request-changes (1 major STD-TEST-2), round 2 approve. Diff: `git diff c3f32b5..team/FEAT-003-task-13` (head b52847e). Merge 1f6787c. Rounds: 2.
- T10: round 1 approve. Diff: `git diff 1f6787c..team/FEAT-003-task-10` (head 8df8ba2). Merge in team/FEAT-003. Rounds: 1. Dev: green `test_ticket_panel` 35 OK, `test_architecture` 60 OK.
- T14: round 1 approve. Diff: `git diff 1f6787c..team/FEAT-003-task-14` (head 9225b22). Merge b075d2d. Rounds: 1. Dev: green `test_architecture` 60 OK, `test_install` 22 OK.
- Deferred (minor): T10 reviewer (a) sanitize_html without `disallowed_tags` (no effect on stored form), (b) keyword read twice, (c) no check of `denied method=send reason=no_read` log; T13 reviewer: pin `formEl.append(inputEl, sendEl)`, `"keydown"`, end of onSendFailed body; T13 minors 1, 3, 5; T14 reviewer: pin `NARROW_SCREEN_PX = 640` (second time a pin misses a constant value).
- Reviewer cannot run bench (role-policy); tests were run by dev in the worktrees.
