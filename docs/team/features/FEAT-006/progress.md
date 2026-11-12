# Progress FEAT-006

Edit không có trong bộ công cụ của tech-lead; tick và đổi touchpoint nằm ở đây, gộp vào `tasks.md` khi xong (hoặc khi có Edit). Dòng ở đây thắng `tasks.md` khi lệch.
Lưu ý quy trình: role-policy chặn tech-lead chạy `PYTHONPATH=... bench ...`, nên `cmd.test` do dev chạy trên đầu nhánh task; tech-lead kiểm cây mã sau merge bằng `git diff --stat <head task> team/FEAT-006 -- . ':!docs'` rỗng (ghi lại ở review-NN.md).

## Đổi touchpoint (người duyệt 2026-11-12, journal FEAT-006)

- T1 `files:` thêm `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_status.py`, `erp_ai/tests/test_install.py` (9 file). Chỉ sửa kỳ vọng cũ theo hành vi mới (STD-TEST-5): không xóa, không skip, không nới test.

## Tick

- [x] T1 — BASE=d8fb3e9, 2 vòng, merge 2393337, review-01 approve, cmd.test 660 OK (C0: bằng chứng ở review-01.md)

## Đang build

(chưa có)

## Nhật ký

- 2026-11-12 T1: dev lần 1 DESIGN_CONFLICT; người duyệt mở rộng touchpoint; dev lần 2 DONE; reviewer vòng 1 request-changes (3 major: nới ca test, tên test sai, commit wip); dev sửa; reviewer vòng 2 approve; merge; 660 test OK.
