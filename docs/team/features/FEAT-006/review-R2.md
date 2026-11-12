# Review R2 (T21, rework 1, mục 2+5+6) — approve

- Verdict: approve, 1 vòng (max_rework=3). Chỉ đổi test.
- Diff: `git diff 91d8903..team/FEAT-006-rw1-r2 -- erp_ai` (BASE 91d8903, đầu 0c9661e). Merge vào `team/FEAT-006`.
- AC-11: 4 ca không-SLA khẳng định phiếu lưu ưu tiên "Urgent" (khác trạng thái đầu "Medium"), `applied == 1`, số HD SLA trước = sau.
- AC-7(c): `apply_route` `ok=True`, nhóm và "Urgent" trên phiếu.
- AC-14: phiếu kế tiếp là đầu mục B, chỉ đổi người mặc định của B.
- Có răng: dev phá tạm mã sản xuất từng chỗ, đỏ rõ (`'Low' != 'Urgent'`, `3 != 2`, `(team,'Medium') != (team,'Urgent')`, `Lists differ`), hoàn tác, xanh `erp_ai.agent.test_runner_routing` Ran 61 OK; cmd.test toàn app Ran 883 OK; pre-commit sạch.
- Verdict không có blocker/major.

## deferred
- minor: helper `_assert_saved_with_priority` nằm giữa các test thay vì cùng nhóm helper; `other` được tạo trước lần chạy đầu ở AC-14 (vô hại).
