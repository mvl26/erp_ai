# dev T22b (FEAT-006) - Câu comment đúng cho ca Task bị từ chối

Branch: team/FEAT-006-task-22b (từ team/FEAT-006 @ 9f3d789)

## Thay đổi
- route_ticket.py: thêm `TASK_REQUEST = "Bot đã gán người phụ trách cho phiếu nhưng không giao được Task: {reason}. Nhờ trưởng nhóm giao Task."`; `REASON_TASK_NOT_ASSIGNED = "chia sẻ tài liệu đang tắt"`.
- runner.py `_task_unit`: dùng `TASK_REQUEST`. Hai ca NO_VALID_ASSIGNEE/ASSIGN_FAILED vẫn dùng `ASSIGN_REQUEST`. Phiếu đã có người: không comment (không đổi).
- test_route_ticket.py: bỏ REASON_TASK_NOT_ASSIGNED khỏi `test_fixed_sentences`, thêm `test_task_refused_sentence_is_its_own`.
- test_runner_routing.py: `test_sharing_disabled_no_task_one_comment` đổi kỳ vọng sang `TASK_REQUEST`, thêm assertNotIn "chưa gán được người".

## RED (đúng lý do, sau khi thêm hằng TASK_REQUEST để không lỗi import)
- runner: `AssertionError: 'Bot đã gán ... Task: không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt). Nhờ trưởng nhóm giao Task.' not found in 'Bot chưa gán được người phụ trách ...'` (Ran 53, failures=1)
- route_ticket: `'không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt)' != 'chia sẻ tài liệu đang tắt'` (Ran 29, failures=1)

## GREEN
- erp_ai.agent.test_runner_routing: Ran 53 tests OK
- erp_ai.agent.tools.test_route_ticket: Ran 29 tests OK
- `bench --site miyano run-tests --app erp_ai`: Ran 835 tests OK
- pre-commit run --files (4 file): tất cả Passed (ruff-format tự sửa 1 file ở lần đầu, chạy lại sạch)
