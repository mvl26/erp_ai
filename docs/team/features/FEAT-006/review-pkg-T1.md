# Review package FEAT-006 T1 (walking skeleton, vòng 1)

Task: T1 trong `docs/team/features/FEAT-006/tasks.md` (+ `progress.md`: touchpoint mở rộng 9 file, người duyệt 2026-11-12).
Design: `docs/team/features/FEAT-006/design.md`; plan: `plan.md` mục "Walking skeleton".
Repo: `/home/miyano/frappe-bench/apps/erp_ai` (nhánh `team/FEAT-006-task-1`, worktree riêng; không checkout ở worktree chính).

BASE=d8fb3e9, head=team/FEAT-006-task-1 (4ecde9f).

Lệnh diff (tạo diff đầy đủ, 545 dòng; chạy bằng git chỉ-đọc):

    git -C /home/miyano/frappe-bench/apps/erp_ai diff d8fb3e9..team/FEAT-006-task-1

Commit:
- 4ecde9f test(routing): update old expectations to apply_route and 9 AI fields (FEAT-006)
- 57f7d4a wip(routing): T1 skeleton code from first dev run, 3 old tests still red (FEAT-006)

`git diff --stat d8fb3e9..team/FEAT-006-task-1`:

    erp_ai/agent/classification.py      | 12 +++++
    erp_ai/agent/routing.py             | 35 ++++++++++++++
    erp_ai/agent/runner.py              | 42 +++++++++++------
    erp_ai/agent/test_agent_runner.py   | 48 +++++++++++++++----
    erp_ai/agent/test_runner_routing.py | 91 +++++++++++++++++++++++++++++++++++++
    erp_ai/agent/test_runner_status.py  | 13 +++++-
    erp_ai/agent/tools/route_ticket.py  | 45 ++++++++++++++++++
    erp_ai/install.py                   | 20 ++++++++
    erp_ai/tests/test_install.py        | 22 +++++++--
    9 files changed, 297 insertions(+), 31 deletions(-)

Tiêu chí T1: AC-1 (khung), AC-2 (ghi lên phiếu từ `L1`; `L0` không ghi), AC-16 (khung `actions`). Returns/Expect của T1 ở dòng T1 của `tasks.md`.
Yêu cầu riêng cho vòng này: 3 file test cũ (`test_agent_runner.py`, `test_runner_status.py`, `tests/test_install.py`) chỉ được đổi kỳ vọng theo hành vi mới (STD-TEST-5), không xóa/skip/nới ca nào; hãy kiểm từng thay đổi trong 3 file đó từng dòng.
Ngoài phạm vi (khung giả, làm thật ở T3, T6..T10, T14, T20..T22): bộ đọc điểm không kiểm, `decide_route` bản giả, `apply_route` chưa kiểm quyền.
