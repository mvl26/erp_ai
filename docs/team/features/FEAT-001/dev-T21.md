# dev-T21 — Thẩm quyền theo người (làm lại, D8)

Nhánh `team/FEAT-001-task-21` (từ 1d6976e). Files: `erp_ai/agent/authority.py`, `erp_ai/agent/test_authority.py`.

## RED (stub trả False/None/[])
`Ran 12 tests` → `FAILED (failures=7, errors=2)`; ví dụ: `AssertionError: None != 'authority.instructor@example.com'`, `AssertionError: Lists differ: [] != ['authority.plain@example.com']`, `AssertionError: {} != {'reference_doctype': 'HD Ticket', ...}`.

## GREEN
`bench --site miyano run-tests --module erp_ai.agent.test_authority` → `Ran 12 tests OK`.
`bench --site miyano run-tests --app erp_ai` → `Ran 134 tests OK`.
`pre-commit run --files <2 file>` → tất cả Passed.

## Mutation check (bỏ riêng từng guard, test đỏ)
| Guard bị bỏ | Test đỏ |
|---|---|
| `not author` (rỗng/None) | test_instructor_role_has_authority_on_any_ticket |
| Guest / AGENT_USER khỏi NEVER_AUTHORITY | test_never_authority_accounts_even_with_role_or_assignment |
| Administrator khỏi NEVER_AUTHORITY | test_latest_instructor..., test_comments_read_from_core_comment_only |
| `author in _assign` | test_closed_cancelled_or_reassigned_todo_is_data |
| ToDo `status == Open` | test_closed_cancelled_or_reassigned_todo_is_data |
| `assigned_by` khác rỗng | test_self_assigned_is_data |
| `assigned_by != author` | test_self_assigned_is_data, test_self_assign_on_other_ticket_is_data |
| filter `reference_name` của ToDo | test_self_assign_on_other_ticket_is_data |
| ToDo `order_by creation desc` | test_closed_cancelled_or_reassigned_todo_is_data |
| `comment_type` filter | test_comments_read_from_core_comment_only |
| `order_by creation desc` của Comment | ban đầu sống sót (OK); đã sửa test chèn comment lệch thứ tự ngày → đỏ |
| gọi `is_instruction` một lần/tác giả | test_label_comments_overwrites_role_and_checks_each_author_once |
| `role` đầu vào bị ghi đè | cùng test trên |
| giới hạn limit dưới/trên | test_comments_read_from_core_comment_only |

## Ghi chú
- `MAX_COMMENTS` import từ `prompts.py` (đã có, không sửa).
- Không còn `except ValueError`; `_assign` parse bằng `json.loads` (lỗi JSON sẽ nổi lên thay vì bị nuốt).
- N+1: `latest_instructor` còn gọi `is_instruction` mỗi comment (≤ 30, minor review-17, giữ đơn giản).
- Không đọc `commented_by`/`comment_email`/`comment_by`; dữ liệu test qua `new_comment`/`add_comment`.
- Đã thêm test riêng cho `label_comments` ghi đè `role` + một lần/tác giả; test limit ngoài 1..50.

## Vòng 1/3 - sửa finding STD-TEST-8 (major) + 2 minor
Không đổi `authority.py`; chỉ thêm test trong `test_authority.py`.

| Finding | Test phủ |
|---|---|
| ToDo filter `allocated_to` không bị test bắt | `test_newest_todo_is_the_authors_own_on_this_ticket` (ASSIGNEE tự giao, ToDo mới hơn của PLAIN do ASSIGNER giao -> False); `test_newer_self_assigned_todo_of_someone_else_does_not_revoke` (ASSIGNEE do ASSIGNER giao, ToDo mới hơn của PLAIN assigned_by rỗng -> True; dùng assigned_by rỗng vì self-assign của PLAIN vẫn != ASSIGNEE nên không phân biệt được) |
| `reference_type` | `test_todo_of_another_reference_type_is_ignored` (ToDo mới hơn tự giao cho ASSIGNEE, reference_type đổi sang "User" -> vẫn True) |
| minor a: `<` vs `<=` | `test_comments_read_from_core_comment_only`: limit=1 và 50 được chấp nhận |
| minor b: get_list permission | `test_fetch_ticket_comments_as_non_administrator_uses_permissions` (set_user PLAIN) |

## Mutation (đỏ)
- bỏ `allocated_to`: FAIL test_newer_self_assigned_todo_of_someone_else_does_not_revoke, FAIL test_newest_todo_is_the_authors_own_on_this_ticket (2 failures)
- bỏ `reference_type`: FAIL test_todo_of_another_reference_type_is_ignored (1 failure)
- `limit < MAX`: ERROR test_comments_read_from_core_comment_only; `MIN < limit`: cùng test đỏ

## Green
`bench --site miyano run-tests --module erp_ai.agent.test_authority` -> Ran 16 tests OK. pre-commit: all Passed.
