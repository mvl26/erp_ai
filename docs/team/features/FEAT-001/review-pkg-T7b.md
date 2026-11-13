# Review package T7b (FEAT-001)

BASE=9010e38, head=2b523ac (branch team/FEAT-001-task-7b)
Diff command: `git diff 9010e38..team/FEAT-001-task-7b` (the reviewer should run it; the stat below is for orientation).

## Commits
2b523ac feat(agent): narrow git_source to log and blame with path and glob guards (FEAT-001)

## Stat
 erp_ai/agent/tools/source.py      |  48 +++++++++++-----
 erp_ai/agent/tools/test_source.py | 117 ++++++++++++++++++++++++++++++++++----
 2 files changed, 141 insertions(+), 24 deletions(-)

## Task criteria (D4)
- git_source keeps only `log` and `blame`; `show` and `diff` removed.
- `log` rejects every patch-printing flag, abbreviations included (-p, -u, --patch*, -U*, --full-diff, --word-diff*, --cc, -m, --diff-merges*).
- Every pathspec or file arg passes `resolve_safe_path`/`TEN_CAM`; glob characters rejected.
- `blame` takes one file, checked the same way as `read_source`.
- Tests added: `show HEAD`, `log -p`, `log --pat`, glob pathspec each refused.
- Touchpoints: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py.

## Diff
Run: `git diff 9010e38..team/FEAT-001-task-7b` in /home/miyano/frappe-bench/apps/erp_ai (branch exists in this repo; worktree at .claude/worktrees/agent-a13a036ff1750cf35). Test file for context: erp_ai/agent/tools/test_source.py on that branch.
