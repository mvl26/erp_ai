# Tiến độ chặng 5 (T22b, T23..T26) — gộp thẳng vào tasks.md ở C5

Quy ước như progress.md. Task chèn T22b (team-leader, journal 2026-11-13): `- T22b — Câu comment (u4) đúng từng ca — files: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/runner.py, erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T22`.
Criterion: phiếu đã có người được gán (bot vừa gán, ở ca Task bị từ chối) thì comment không nói "Bot chưa gán được người", chỉ nói không giao được Task; các ca chưa gán được người vẫn nói như cũ.
Đổi touchpoint T22b: `route_ticket.py` + `test_route_ticket.py` (hằng câu ở đó; `test_route_ticket.py:426` ghim câu cũ).

Thứ tự còn lại: T25 → T26, MỘT dev mỗi lần (site miyano dùng chung).

- [x] T22b — BASE=9f3d789 (a8f0f34 là đầu nhánh trước commit docs progress-c5), 2 vòng (1 vòng sửa), merge a0bf05b, review-22b; cmd.test đầu nhánh task 5c2215b: Ran 835 tests, OK
  - Đầu thật là `team/FEAT-006-task-22b-rework1`. Deferred cho designer: design 3.6, 4.2 bước 4, tasks.md:153 (câu `TASK_REQUEST`).
- [x] T23 — BASE=1117974, 2 vòng (1 vòng sửa), merge 1d35b81, review-23; cmd.test đầu nhánh task 2a8cf58: Ran 841 tests, OK
  - Đầu thật là `team/FEAT-006-task-23-rework1`. Lưu ý T26: quét tên người theo ranh giới từ ("Việt Nam", "Tiếng Việt" trong prompts.py là trùng chữ).
- [x] T24 — BASE=9135b85, 3 vòng (2 vòng sửa), merge 0ab015a, review-24; cmd.test đầu nhánh task 6788b93: Ran 851 tests, OK
  - Đầu thật là `team/FEAT-006-task-24-rework2`. Không đổi mã sản xuất. `RoutingTestBase.setUp` nay ghim role (AC-17). Deferred cho designer: `value_before` vs design 3.5; hàng test-plan 493.
