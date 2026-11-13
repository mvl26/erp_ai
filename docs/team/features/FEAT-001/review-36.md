# Review 36 — FEAT-001 T29 (Runner: L1 ghi phân loại qua tool)

Verdict: approve
Vòng: 1 (không rework)
Diff: `git diff a39ee7c..team/FEAT-001-task-29 -- erp_ai/` (a291535; runner.py, test_runner.py)
Reviewer: team:reviewer, checklist (10) đủ 10/10; không blocker, không major.

## Tầng 1
- AC-10 L1: phiếu nhận giá trị ánh xạ, độ tin cậy, `ai_classified_by = AI`, `status` không đổi; người đã phân loại không bị ghi đè.
- ADR-004: runner chỉ cập nhật dòng `classify` của mình bằng `set_value(update_modified=False)`.
- Nợ review-34 đã xử lý: `applied = 1` chỉ khi `ok` và `after` không rỗng (runner.py:180); dòng log ghi và commit trước; ghi tool + cập nhật dòng log cùng savepoint `erp_ai_apply`, commit sau cả hai; ngoại lệ -> rollback về savepoint, dòng log giữ `applied=0`. Mỗi guard (after, ok, savepoint rollback, commit cuối, L0) có test đỏ khi bỏ.

## Bằng chứng dev
RED: 3 failure đúng lý do + 1 error do chưa có `runner.execute_tool`. GREEN: test_runner 30 OK (4 lần), test_registry 24 OK. Đếm HD Team/HD Ticket/User/ERP AI Log/Error Log 4/3/8/0/195 trước = sau.

## Minor (deferred)
- test_runner.py:432 comment sai thứ tự cleanup `hdel` (đăng ký sau nên chạy trước); sửa comment hoặc đăng ký trước `super().setUp()`.
- test_runner.py:487 `test_l1_empty_after_keeps_applied_zero` thiếu `self.log_error.assert_not_called()`.

## Không kiểm được từ diff -> quyết định của tech-lead
- Khoảng trống spec/design AC-10: spec nói giá trị ánh xạ không tồn tại thì bỏ trường và ghi lý do vào log; `set_classification` trả `skipped`/`reason` nhưng runner bỏ chúng; design 4.3/2.3 không có trường cho lý do. Ba trường hợp (người đã phân loại, thiếu quyền, mọi trường bị bỏ) cùng để lại dòng `applied=0` không lý do. Xử lý: ghi nhận là `design-gap`, đưa cho team-leader quyết định (đề xuất: đặt `skipped` vào `value_after` hoặc `error` của dòng classify) trước `/team:verify` AC-10; T30 (cùng runner.py) có thể áp dụng khi có quyết định. Không chặn T29 vì T29 đúng theo design hiện hành.
- Team không có thành viên khi lưu HD Ticket có thể ném lỗi ở prod -> savepoint rollback, dòng `applied=0` không lý do (cùng khoảng trống).
- Cần xác nhận cmd.test toàn app sau merge (làm qua dev, D3).
