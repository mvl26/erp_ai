# dev-T18 — Xóa `resolve_ticket_values`, chuyển ca test sang `test_routing.py` (FEAT-006)

Nhánh: `team/FEAT-006-task-18` (từ `team/FEAT-006` @ 5718e2f). Criterion: D-12, AC-3.

## Thay đổi
- `erp_ai/agent/classification.py`: xóa `resolve_ticket_values` (PRIORITY_URGENT/URGENT_TAGS giữ nguyên vì `routing.py` còn dùng).
- `erp_ai/agent/routing.py` (mở rộng touchpoint đã được tech-lead chấp nhận): `entry = mapping.get(classification.category) or {}`; `ticket_type=entry.get("ticket_type")`; `agent_group = entry.get("agent_group") or None`; bỏ import `resolve_ticket_values`. Hành vi `decide_route` không đổi.
- `erp_ai/agent/test_routing.py`: 7 ca của `TestResolveTicketValues` chuyển thành ca của `TestDecidePriority` (cùng giá trị kỳ vọng, gọi qua `decide_route`):
  - test_values_come_from_mapping_not_from_model (Classification có team/priority của model, kỳ vọng mapping B)
  - test_missing_category_in_mapping_gives_none
  - test_missing_key_inside_entry_gives_none
  - test_empty_mapping
  - test_urgent_prefix_forces_urgent (5 subject, kèm ticket_type "Câu hỏi, phiếu nhiễu")
  - test_urgent_prefix_overrides_empty_priority_and_missing_category
  - test_no_urgent_without_bracketed_tag
- `erp_ai/agent/test_classification.py`: xóa lớp `TestResolveTicketValues`; ca `test_parse_deeply_nested_json_returns_none` (nằm nhầm trong lớp đó nhưng thuộc parse) chuyển sang `TestParseClassification`, nguyên văn.

## Bằng chứng
1. Test mới xanh khi hàm cũ còn: `erp_ai.agent.test_routing` -> `Ran 56 tests ... OK`.
2. Đột biến R1 (`routing.py:142` thành `if False and ...`): `FAILED (failures=21)`, gồm các ca mới `test_urgent_prefix_forces_urgent`, `test_urgent_prefix_overrides_empty_priority_and_missing_category` (và ca cũ ma trận 36/spec_samples/casefold). Đã hoàn tác (`git checkout`).
3. Sau xóa: `test_routing` -> `Ran 56 tests OK`; `test_classification` -> `Ran 29 tests OK`.
4. `grep -rn resolve_ticket_values erp_ai/` -> (rỗng), exit 1.
5. `cmd.test` toàn app: `Ran 783 tests in 132.653s OK` (các dòng ERROR CSS box-shadow là nhiễu log có sẵn của test khác, không phải test lỗi). Số test trước = sau = 783 (chuyển 7 ca, -7 +7; ca nested JSON chỉ đổi lớp).
6. `pre-commit run --files` 4 file: tất cả Passed (ruff linter, formatter, import sorter).

## Không có skip/xfail; không sửa assertion nào của ca cũ.

## Seen but not touched
Không có.
