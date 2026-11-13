Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 12 — FEAT-004 T12

- Diff: `git diff 7f4f5c9..team/FEAT-004-task-12` (1 commit `04707df`, 5 file, +859/-1)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 3 điểm nhỏ: `erp_ai_change_proposal.py:34-37` bước `cint`/`cstr` làm đều kiểu trước khi so chưa có test (vd `ahead_count="0"`, `""` so với None); `:44` dòng DB biến mất thì `AttributeError` thay vì lỗi rõ; `test_utils.py:686` `ValueError` cho loại đề xuất lạ chưa có test | tùy dev

## Review checklist (10)
1–10 đạt. 35 trường dữ liệu (15 nội dung, 11 trạng thái, 9 git), mọi trường `read_only=1`; quyền đúng ADR-012 (kiểm cả JSON và DocPerm trong DB); bố cục đúng design 3.3.

## Bằng chứng của dev
- RED 1: `AssertionError: False is not true : erp_ai_change_proposal.json is missing`, `FAILED (failures=8)`; RED 2: `AssertionError: ValidationError not raised`, `FAILED (failures=20)`
- migrate: `Queued rebuilding of search index for miyano`
- GREEN: `Ran 8 tests in 2.092s` / `OK`; `test_doctype_descriptions` `Ran 11 tests ... OK`; `test_architecture` `Ran 97 tests ... OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `make_ticket` của helpdesk có commit/xếp job sống sót sau rollback không: theo dõi qua `cmd.test` (số dòng không lệch), qa đối soát ở T34.
- `make_change_proposal` ghi `change_status` ngoài `transitions.py`: luật T13/T31 phải giữ ngoại lệ cho `test_utils.py` → đưa vào handoff T13, T31.
- T49 đặt `commit_message` lúc insert sẽ ghi đè chuỗi mẫu của helper → đưa vào handoff T49.
- `validate` có thể bị vượt qua bằng `db_set`: ADR-012 chấp nhận, dựa vào digest lúc áp dụng (T13, T18).

## deferred
- Tên 3 Column Break (`column_proposal`, `column_git`, `column_git_result`) do dev đặt vì design 3.3 không ghi: writer đưa vào As-Built.
