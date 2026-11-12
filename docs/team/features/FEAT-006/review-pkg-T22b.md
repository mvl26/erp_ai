# Review package FEAT-006 T22b (câu comment (u4) đúng từng ca), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai` (worktree `.claude/worktrees/feat-006`). BASE=9f3d789; head=team/FEAT-006-task-22b (8282aae).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 9f3d789..team/FEAT-006-task-22b -- erp_ai`
Commits: `git -C ... log --oneline 9f3d789..team/FEAT-006-task-22b`; stat: `git -C ... diff --stat 9f3d789..team/FEAT-006-task-22b`.

Commits:
- 8282aae fix(routing): câu comment riêng cho ca Task bị từ chối (FEAT-006)

Stat (mã): runner.py 3 dòng, test_runner_routing.py 5, tools/route_ticket.py 5, tools/test_route_ticket.py 12.

Touchpoints cho phép: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/runner.py, erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/test_runner_routing.py.

Tiêu chí: comment (u4) nói đúng sự thật từng ca. Ca Task bị từ chối (chia sẻ tài liệu tắt): bot ĐÃ gán người cho phiếu ở (u2) nên không được nói "Bot chưa gán được người", chỉ nói không giao được Task. Hai ca chưa gán được người (không người hợp lệ; gán thất bại) giữ câu cũ. Phiếu đã có người từ trước: không comment. Câu cố định, không tên người/nội dung phiếu (NFR-4).

Diff đầy đủ: chạy lệnh diff ở trên (nhỏ, ~25 dòng thay đổi mã).
