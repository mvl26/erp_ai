# Progress FEAT-006

Edit không có trong bộ công cụ của tech-lead; tick và đổi touchpoint nằm ở đây, gộp vào `tasks.md` khi xong. Dòng ở đây thắng `tasks.md` khi lệch.
Quy trình:
- role-policy chặn tech-lead chạy `PYTHONPATH=... bench ...`: `cmd.test` do dev chạy trên đầu nhánh task. Tech-lead kiểm cây mã sau merge bằng `git diff --stat <head task> team/FEAT-006 -- . ':!docs'`.
- Site `miyano` dùng chung: hai `cmd.test` đồng thời gây `QueryDeadlockError 1213` giả (R1: 37 error; T4/T5 song song: 45 và 34 error). Từ sau T5: MỘT dev mỗi lần; reviewer chạy song song với dev kế tiếp được vì reviewer không chạy bench.
- `review-NN.md`: NN = số task.

## Đổi touchpoint

- T1 (người duyệt 2026-11-12): thêm `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_status.py`, `erp_ai/tests/test_install.py`. Chỉ sửa kỳ vọng cũ (STD-TEST-5).
- T6 (tech-lead, cần người xác nhận ở lần dừng): thêm `erp_ai/agent/test_runner_routing.py`, chỉ đổi `priority == "High"` → `"Urgent"` cho A + quan trọng 3 (kỳ vọng của bản giả T1 trái R4/AC-3).

## Tick

- [x] T1 — BASE=d8fb3e9, 2 vòng, merge 2393337, review-01, cmd.test 660 OK
- [x] T3 — BASE=4cfd68f, 1 vòng, merge d4a766c, review-03, cmd.test 664 OK
- [x] T6 — BASE=4cfd68f, 1 vòng, merge b8d2607, review-06, cmd.test 668 OK
- [x] T4 — BASE=b1af21f, 1 vòng, merge 6ebb766, review-04; test_one xanh; cmd.test sạch chờ lần nối tiếp ở T7
- [x] T5 — BASE=b1af21f, 1 vòng, merge 1aa1a79, review-05; test_one xanh; cmd.test sạch chờ lần nối tiếp ở T7
- [x] T7 — BASE=686aa3f, 2 vòng, merge 2851bca, review-07; dev cmd.test 679 OK (vòng 1); cmd.test nối tiếp trên nền merge: chờ lần chạy ở C2
- [x] T2 — BASE=686aa3f, 2 vòng, merge 8473884, review-02; dev cmd.test 687 OK; cmd.test nối tiếp trên nền merge: chờ lần chạy ở C2
- [x] T8 — BASE=2851bca, 2 vòng, merge 61e51f2, review-08; dev cmd.test 688 OK (vòng 1); cmd.test nối tiếp trên 61e51f2: chờ lần chạy ở C2

## Đang build

Chặng 2 (--decide) tới C2: T9 → T10 → T11 → T12 theo `depends:`, MỘT dev mỗi lần. Dev của T9 chạy `cmd.test` trên 61e51f2 trước khi viết test đỏ (dán dòng Ran N/OK).

## Nhật ký

- 2026-11-12 T1: dev lần 1 DESIGN_CONFLICT; người duyệt mở rộng touchpoint; dev lần 2 DONE; reviewer vòng 1 request-changes (3 major); dev sửa; vòng 2 approve; merge; 660 test OK.
- 2026-11-12 R1 (T3 ∥ T6): T6 DESIGN_CONFLICT (test T1 giả) → tech-lead mở rộng touchpoint 1 file; cả hai approve vòng 1.
- 2026-11-12 R2/R3 (T4 ∥ T5): hai dev song song làm `cmd.test` deadlock lẫn nhau; cả hai approve vòng 1; merge không xung đột; chuyển sang chạy từng dev một.
- 2026-11-12 T7, T2, T8: mỗi task request-changes vòng 1 (hai major mỗi task, T2/T8 có thêm suspected), approve vòng 2; đã merge; ghi tick và review-02/07/08 ở chặng 2.
