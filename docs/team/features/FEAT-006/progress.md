# Progress FEAT-006

Edit không có trong bộ công cụ của tech-lead; tick và đổi touchpoint nằm ở đây, gộp vào `tasks.md` khi xong (hoặc khi có Edit). Dòng ở đây thắng `tasks.md` khi lệch.
Lưu ý quy trình:
- role-policy chặn tech-lead chạy `PYTHONPATH=... bench ...`, nên `cmd.test` do dev chạy trên đầu nhánh task; tech-lead kiểm cây mã sau merge bằng `git diff --stat <head task> team/FEAT-006 -- . ':!docs'` (ghi ở review-NN.md). Dev của task kế tiếp chạy `cmd.test` trên nền đã merge.
- Site `miyano` dùng chung: hai dev chạy `cmd.test` đồng thời gây lỗi tranh chấp giả (lần R1: 32 và 37 error không lặp lại). Từ T2 chạy MỘT dev mỗi lần (max_parallel_dev=2 là trần, không phải bắt buộc), reviewer chạy song song với dev kế tiếp được vì reviewer không chạy bench.
- `review-NN.md`: NN = số task.

## Đổi touchpoint

- T1 (người duyệt 2026-11-12): `files:` thêm `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_status.py`, `erp_ai/tests/test_install.py` (9 file). Chỉ sửa kỳ vọng cũ theo hành vi mới (STD-TEST-5).
- T6 (tech-lead, cần người xác nhận ở lần dừng): thêm `erp_ai/agent/test_runner_routing.py`, chỉ đổi khẳng định `priority == "High"` → `"Urgent"` cho A + quan trọng 3 (kỳ vọng của bản giả T1 trái R4/AC-3).

## Tick

- [x] T1 — BASE=d8fb3e9, 2 vòng, merge 2393337, review-01 approve, cmd.test 660 OK
- [x] T3 — BASE=4cfd68f, 1 vòng, merge d4a766c, review-03 approve, cmd.test 664 OK
- [x] T6 — BASE=4cfd68f, 1 vòng, merge b8d2607, review-06 approve, cmd.test 668 OK

## Đang build

(chưa có) — tiếp theo: T4, T5, T7 (một dev mỗi lần), rồi T8, T9, T2, T10, T11 ... theo plan.md

## Nhật ký

- 2026-11-12 T1: dev lần 1 DESIGN_CONFLICT; người duyệt mở rộng touchpoint; dev lần 2 DONE; reviewer vòng 1 request-changes (3 major); dev sửa; vòng 2 approve; merge; 660 test OK.
- 2026-11-12 R1 (T3 ∥ T6): hai dev song song; T6 DESIGN_CONFLICT (test T1 giả) → tech-lead mở rộng touchpoint 1 file; cả hai approve vòng 1; merge không xung đột.
