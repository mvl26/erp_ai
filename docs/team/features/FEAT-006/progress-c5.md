# Tiến độ chặng 5 (T22b, T23..T26) — gộp thẳng vào tasks.md ở C5

Quy ước như progress.md. Task chèn T22b (team-leader, journal 2026-11-13): `- T22b — Câu comment (u4) đúng từng ca — files: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/runner.py, erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T22`.
Criterion: phiếu đã có người được gán (bot vừa gán, ở ca Task bị từ chối) thì comment không nói "Bot chưa gán được người", chỉ nói không giao được Task; các ca chưa gán được người vẫn nói như cũ.
Đổi touchpoint T22b: `route_ticket.py` + `test_route_ticket.py` (hằng câu ở đó; `test_route_ticket.py:426` ghim câu cũ).

- [ ] T22b — BASE=a8f0f34
