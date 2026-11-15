Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 20 — CHG-002 T20

- Diff: vòng 1 `git diff f0b737c..8b9725d`; vòng 2 (sửa) `git diff 8b9725d..39ccf07` (nhánh `team/CHG-002-task-20`; merge vào `team/CHG-002` ở `e6cda3e`)
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 approve

## Vòng 1 — request-changes
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-1 | erp_ai/agent/change_text.py:126-129 (`_stored_commands`) | `except ValueError: return []` và "không phải list → []" lặng lẽ coi `command_list` không đọc được nhưng khác rỗng là "không có lệnh". Khối khi đó hiện cho người duyệt `0 lệnh`, không dòng restart, không dòng "không hoàn tác được". `block.commands_of` (đường áp dụng dùng) đọc cùng trường đó chặt và ném lỗi (design §2.3). Ghi chú và job áp dụng đọc trường khác nhau, trái mục tiêu của AC-54 là hiện mọi restart trước khi duyệt. Phần nới cũng làm dở: list phẳng cho `r e s t a r t`, phần tử không phải chuỗi thì ném lỗi. Test ghim nó ở `test_commands_not_undoable_line` (subtest `"not json"`, `'{"args": ["restart"]}'`) | Đọc bằng cùng luật chặt như `block.commands_of`: `json.loads(command_list or "[]")`, không `except`. Hai subtest sai dạng đổi thành `assertRaises`. Nếu muốn `onload` không ném lỗi thì đó là câu hỏi thiết kế: xin designer một dòng §3.7, không tự đặt đường lui |
| major | STD-TEST-5 | erp_ai/agent/test_change_text.py `test_counts_then_items_then_commands_in_order` | Ở mọi ca test số `tạo` bằng số `xóa` (1/1, còn lại 0/0), nên đổi chỗ `kinds.count(CHANGE_OP_CREATE)` và `kinds.count(CHANGE_OP_DELETE)` ở `change_text.py:137-138` vẫn xanh | Thêm một ca bốn số đếm khác nhau, hoặc thêm dòng tạo thứ hai vào ca đang có |

Chín câu của khối so từng byte với design.md §3.7: khớp. Nhắc lại luật `is_block` tại chỗ (không gọi `block.is_block`) là do luật kiến trúc "change_text chỉ nhập thư viện chuẩn và erp_ai.constants", không phải phát hiện.

minor | — | — | 2 điểm nhỏ: `_NOTE_VERBS` lặp `_ITEM_VERBS` (STD-DESIGN-4); `is_block` không có chú thích trỏ §2.3 | tùy dev (dev đã sửa cả hai ở vòng 2)

## Vòng 2 — scoped re-review (`8b9725d..39ccf07`), approve
- Phát hiện 1 (STD-ERR-1): ADDRESSED. `change_text.py:124-127`: bỏ `except`; `json.loads(command_list or "[]")` rồi ném `ValueError` nếu không phải list của list. `test_change_text.py:528-533`: ba giá trị sai (`"not json"`, `'{"args": ["restart"]}'`, `'["restart"]'`) nay `assertRaises(ValueError)`. RED của dev: `Ran 17 tests` / `FAILED (failures=3)`, mỗi subtest `AssertionError: ValueError not raised`; GREEN `Ran 17 tests` / `OK`.
- Phát hiện 2 (STD-TEST-5): ADDRESSED. `test_change_text.py:428,434,440`: dòng tạo thứ hai cho `2 sửa, 2 tạo, 1 xóa, 1 đổi tên`. Dev đổi chỗ tạm: `FAILED (failures=1)`, `Lists differ: ['Gồm 2 sửa, 1 tạo, 2 xóa, 1 đổi tên; 3 lệnh.', ...] != ['Gồm 2 sửa, 2 tạo, 1 xóa, 1 đổi tên; 3 lệnh.', ...]`; trả lại: `Ran 17 tests` / `OK`. Mọi cặp trong bốn số đếm khác nhau ở ít nhất một ca (dòng 454, 474, 490, 587).
- Blocker/major mới từ diff sửa: không.

## Review checklist (10), sau vòng 2
1. Đạt. 2. Đạt. 3. Đạt (RED 11 lỗi ở vòng 1; đường lỗi có test; không skip). 4. Đạt. 5. Đạt sau vòng 2. 6. Đạt. 7. Đạt (chữ ký `proposal_notes` không đổi; đầu ra dạng cũ trùng từng byte). 8. Đạt. 9. Đạt (`json` là thư viện chuẩn). 10. Đạt (`feat(change_text): …`, `fix(change_text): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff, tech-lead đã xử lý
- Kết quả test: đợt merge 4 (`e6cda3e`, 06:48–06:57) `test_change_text` `Ran 17 tests in 0.007s` / `OK`, cả app `Ran 1616 tests in 491.001s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- `check_block` lúc áp dụng có từ chối `cmds` là dict hay list phẳng không, và `propose_change` có luôn lưu list các argv không: thuộc T14, T28, T33 (chưa làm); ghi vào deferred để reviewer của các task đó đối chiếu.
- Câu hỏi thiết kế → báo team-leader: `onload` (`erp_ai_change_proposal.py:54`) gọi `proposal_notes(self)`; bản ghi có `command_list` hỏng nay ném lỗi, form không mở. Muốn form vẫn mở thì designer thêm một dòng §3.7.

## deferred
1. `change_text.py:119`: docstring nói "đọc chặt như `block.commands_of`" nhưng thực tế chặt hơn (`commands_of` ở `block.py:34-36` chỉ `json.loads`, không kiểm dạng).
2. `change_text.py:126`: chữ của `ValueError` lặp lại cả `command_list` đã lưu, không giới hạn độ dài.
3. `block.commands_of` (`block.py:36`) không kiểm dạng: dict đã lưu sẽ tới đường áp dụng như "lệnh" → T14/T33 phải chặn.
4. Đường dẫn và lệnh không qua `_shown` (chỉ remote, nhánh, app, sha bị lọc URL); dựa vào `change_guard` và danh sách lệnh.
