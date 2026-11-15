---
name: static-pin-mutation-method
description: How to mutation-check static regex pins (STATUS_SCRIPT_REQUIRED) when the reviewer role-policy hook blocks python, bench, file edits and shell variables
metadata:
  type: reference
---

2026-11-12 (FEAT-003 T13 r2): the team role-policy hook blocks for team:reviewer: python3 (even stdin), `bench run-tests`, Write outside agent-memory (scratchpad too), shell loops and `VAR=...` assignments. It allows single `grep`, `sed` to stdout and pipes.

Method that works: one command per mutation, full paths:
`sed -z 's/<old with \n\t*>/<new>/' <file.js> | grep -Pzc '<pin regex>'`
- First confirm the pin matches the clean file (`grep -Pzo 'a|b|c' file | tr '\0' '|'` shows each pin once = unique).
- Count 0 after the mutation = sed applied AND the pin goes red (count 1 would mean the mutation did not apply or a copy elsewhere still matches).
- `grep -P -z` `\s` spans newlines like Python `re.search`, so results match the test's behavior.

2026-11-14 (FEAT-007 T4): `git merge-tree --write-tree` is flagged by the hook as not read-only (it writes objects). To check whether a commit stands alone on another branch, use `git show <branch>:<path> | grep <symbol>` and `git log --oneline A..B -- <path>` instead.

Tell tech-lead that bench runs could not be done by the reviewer; red-then-green stays "not verifiable". Related: [[recurring-masked-tests]].
