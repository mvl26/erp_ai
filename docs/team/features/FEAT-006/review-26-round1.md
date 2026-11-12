# Review T26 — vòng 1: request-changes

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 2cd3ba3..team/FEAT-006-task-26 -- erp_ai` (head 4ad5b17).

## Findings (nguyên văn từ reviewer)

1. major | STD-TEST-2 | erp_ai/tests/test_architecture.py:1418 | ADR-021 Ràng buộc says "`assign_to.add`/`assign_agent` chỉ được gọi từ module ghi của bước định tuyến", and ADR-021 decision 3 names `HDTicket.assign_agent` as an allowed way to assign. `ASSIGN_CALL_SUFFIXES` only has `assign_to.add` and `assign_to.add_multiple`, so `frappe.get_doc("HD Ticket", t).assign_agent(user)` in runner.py would pass every scanner. | Flag calls to `assign_agent` outside `ROUTE_FILE`. Add a self-test case such as `"def f(doc):\n\tdoc.assign_agent('u')\n"` in `agent/runner.py`.

2. major | STD-TEST-2 | erp_ai/tests/test_architecture.py:1491 | ADR-020 Ràng buộc says "(u2)–(u4) không gọi `save`/`db_update` trên HD Ticket", and ADR-020 decision 6 also rules out retrying through `db_update`. The scanner only counts `.save`. `db_update` is also missing from `TOOL_FORBIDDEN_CALL_SUFFIXES` (line 97), so `doc.db_update()` in `assign_owner` would pass. | Treat `db_update` like `save` in `route_ticket.py` (no `db_update` at all; one `save` only, inside `apply_route`). Add a self-test case for it.

3. major | STD-TEST-8 | erp_ai/tests/test_architecture.py:1429 (`_sla_date_writes` at :1558) | The AC-10 scanner misses `doc.set("response_by", x)`, because `"set"` is not in `SLA_WRITE_CALLS`. That is the write pattern this repo already uses at `erp_ai/agent/tools/write_ticket.py:96` (`doc.set(HINT_FIELD, ...)`). It also misses a field name held in a constant: `FIELD = "response_by"` followed by `setattr(doc, FIELD, v)` or `doc.set(FIELD, v)`, because Assign values are never inspected. | Add `"set"` to `SLA_WRITE_CALLS`. Also flag any string constant equal to an SLA field name when it is used as an Assign value or a tuple/list element under `agent/`. Add self-test cases for `doc.set('response_by', 1)` and `F = 'resolution_by'`.

Minor (dev's call; tech-lead cho vào vòng sửa vì cùng file, rẻ):
- (a) `ASSIGN_FIELD_ALLOWED_FILES` exempts all of `authority.py`, but the one legitimate read is `authority.py:53`. Allow only that function, or pin the count to 1.
- (b) Dropping `"assign_to.add_multiple"` keeps tests green because the `a.add_multiple` case is also caught by the import guard (test_architecture.py:2752). Needs a case without import of the module.
- (c) `ASSIGN_FIELD` regex lookbehind/lookahead has no isolating case (`'ai_assign'`, `'_assigned'`); `PERSON_NAME`'s `(?<!\w)` has no prefix case.
- (d) The "clean" fixture at :2760 treats `frappe.get_doc('ToDo').insert()` outside the route module as allowed, but ADR-021 rejects creating ToDo directly.
- (e) Names in `#` comments are not scanned for AC-14 (dev disclosed).
- (f) `check_route_module_is_not_a_tool` does not check other modules' `TOOLS` for the routing write functions (ADR-019 Ràng buộc).

## Không kiểm được từ diff — tech-lead giải quyết
- Bảng đột biến đỏ-xanh và "880 OK": tech-lead sẽ dựa vào dev chạy lại ở vòng sửa (C5 chạy lại toàn bộ).
- ADR-019 Ràng buộc nhắc "tên bộ phận của bảng 16.2" không được xuất hiện trong `erp_ai/agent/`; design dòng 479 và tasks.md T26 chỉ giữ tên người: lệch tài liệu, ghi `deferred` cho designer (không mở rộng T26).
- Design dòng 355 (install ghi `auto_assign_enabled=0`): reviewer xác nhận `install.py` không có ghi literal; mặc định từ DocType. Đã ổn.
- ADR-020 "mã của bước định tuyến" gồm cả `runner._route`: `runner.py` hiện không có `.save()`; ghi `deferred` (phạm vi quét `route_ticket.py` theo tasks.md T26).
