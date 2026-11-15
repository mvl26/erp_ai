Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 13 — FEAT-007 T13

- Diff: `git diff a3bddb8..756755d` (nhánh `team/FEAT-007-task-13`, 2 commit `4faf729`, `756755d`; `4faf729` là `242a73f` của vòng 1 với message đã sửa, cùng cây); diff sửa vòng 2: `git diff 4faf729..756755d`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng (chỉ đọc): `git log --oneline a3bddb8..242a73f`, `git diff --stat a3bddb8..242a73f`, `git diff a3bddb8..242a73f`, `git log -1 --format=%B 242a73f`; `git show 242a73f:erp_ai_setting.py` (các lời `frappe.throw(f…`, chỗ dùng `escape_html`), `git show 242a73f:erp_ai_setting.json` (`permissions`), `git show 242a73f:test_erp_ai_setting.py` (`test_every_new_field_default`); `git grep '= "HD Ticket"'`, `git branch -r --contains 242a73f` (rỗng, nhánh chưa push). Tài liệu: `tasks.md` dòng 1-25 và khối T13; `design.md:90-184`, `:288-300`; grep T13/AC-24 trong `design-w0-fixes*.md`; C-1, C-2 của `arch-review-design-w0-r2.md` (không liên quan T13).
- Bằng chứng của dev: RED cho E-1, E-2, E-3 (`AssertionError: None != "Trường 'khong_co_truong_nay' không có trên HD Ticket (Tính chất phiếu)"`, `None != 'Trường Hạn hoàn thành phải có kiểu Date hoặc Datetime'`, `None != 'Đặt giá trị Chỉ đạo BGĐ thì phải đặt tên trường Nguồn phát sinh'`), `41 != 50`, `10 != 11`. GREEN 4 module sau migrate exit 0: `test_erp_ai_setting` `Ran 58 tests in 2.603s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.347s OK`; `test_architecture` `Ran 112 tests in 3.268s OK`; `test_install` `Ran 37 tests in 17.000s OK`.
- Lớp 1 (khớp spec):
  - Đủ: 8 trường Data của `section_ticket_fields` đúng thứ tự hàng 9 (`design.md:105`), section nằm giữa `prompt_digest` và `section_code_change`. `excluded_title_prefixes` là Small Text, mặc định `[HR]\n[Kế toán]`, ngay sau `excluded_teams`, mô tả đúng nguyên văn `design.md:170`. Mô tả `field_*` và `origin_board_value` theo `:171-172`. `check_ticket_field_names()` chạy ngay trước `check_catalog_rules()`, đúng bước 4 → 5 của `:294`. Ba chuỗi E-1, E-2, E-3 đúng từng chữ. Dòng mặc định mới có trong `FEAT007_NEW_FIELD_DEFAULTS`. `field_count` +9, `section_count` +1.
  - Không thừa: 4 file, đúng touchpoints. Không hiểu sai.
- Các điểm dev tự quyết (thiết kế im lặng): tên trường so khớp chính xác (`Meta.get_field`): hợp lý, có test cho chữ hoa, Title Case, tên có dấu. Trim tên trường và giá trị BGĐ trước khi kiểm và lưu: hợp lý, có test. Kiểm theo thứ tự form, E-1 trước E-2: hợp lý, có test. Vị trí trước `check_catalog_rules`: đúng thiết kế, chưa có test ghim thứ tự (minor). Section Break/Table qua được E-1: đúng chữ thiết kế ("có trên meta"), rủi ro cho phía đọc ghi ở bảng dưới. E-1 không escape HTML: chỉ System Manager lưu được form và thông điệp chỉ trả về cho chính người gõ; file không thống nhất (`:156` không escape, `:308` có) → minor.
- STD-TEST-5, phép khẳng định thứ tự trong `test_code_change_block_follows_feat006_fields`: bản cũ ghim `order[start:start+4]`; bản mới ghim `order[start:start+13]`, chứa nguyên 4 phần tử cũ đúng thứ tự tương đối và ghim thêm 9 phần tử theo hàng 8 → 9 → 10 của `design.md:104-106`: chặt hơn, không nới. Không phép khẳng định cũ nào khác bị đổi (chỗ khác chỉ thêm `phrases`, thêm dòng `sections`, và số `field_count`/`section_count`). **Nhưng message của `242a73f` không nhắc tới việc sửa test này**, trong khi dòng "Bổ sung của tech-lead" đặt điều kiện "lý do ghi trong commit (STD-TEST-5 / NFR-8)" → major dưới đây.
- Test đỏ được không (đột biến đọc theo mã): bỏ `fieldname == DUE_FIELD_SETTING` → lần lưu nền đỏ (`ticket_type` là Link); chỉ nhận `Date` → `resolution_by` đỏ; nhận thêm `Time` → `opening_time` đỏ; `has_column` thay `get_field` → các biến thể đỏ; bỏ `self.set` khi trim → `test_existing_custom_field_saves` đỏ; không trim `origin_board_value` → đỏ; lấy nhãn sai → chuỗi E-1 đỏ. Không có test luôn xanh. `setUp` không tạo Custom Field nào (không ALTER, không commit ngầm); có rollback và `keep_agent_settings`.

### Phát hiện (chỉ blocker/major)

major | STD-TEST-5 | commit `242a73f` (message); erp_ai/tests/test_doctype_descriptions.py:557-575 | Phép khẳng định thứ tự của `test_code_change_block_follows_feat006_fields` đã bị sửa, nhưng message commit không ghi lý do. Điều kiện để được sửa (dòng "Bổ sung của tech-lead", T13) là lý do phải nằm trong commit; người đọc lịch sử không biết vì sao một test cũ đổi. | Sửa lại message (nhánh chưa push, `git branch -r --contains` rỗng), thêm một đoạn: "test_doctype_descriptions: test_code_change_block_follows_feat006_fields now pins prompt_digest → section_ticket_fields … section_code_change per design.md:104-106 (rows 8-10); old 4-item slice kept as a sub-sequence, not loosened (STD-TEST-5, NFR-8)". | confirmed

minor | — | — | 4 điểm nhỏ: (1) STD-STYLE-5: comment trỏ sai số dòng design. `design.md:107` thực ra là hàng 12; `120-121` không phải bảng trường. Đúng phải là `:104-106`, `:127-128` (test_doctype_descriptions.py:557, test_erp_ai_setting.py ở comment trên `TICKET_FIELD_LABELS` và trong `test_section_and_field_shape`). (2) STD-SEC-3: E-1 đưa tên người gõ vào `frappe.throw` mà không qua `frappe.utils.escape_html`, khác với `:308` cùng file. (3) STD-TEST-8: chưa test nào ghim thứ tự bước 4 trước bước 5 (một lần lưu vừa có tên trường sai vừa có dòng danh mục sai thì phải ra E-1). (4) STD-TEST-1: handoff không dán dòng RED riêng của `test_existing_custom_field_saves`; theo diff thì test này đỏ được | tùy dev

### Review checklist (10)

1. đạt (AC-24 đủ E-1/E-2/E-3; D-19 chỉ là trường) 2. đạt (4 file trong touchpoints) 3. đạt (RED trước; cạnh hoa thường, dấu, khoảng trắng, None, hai lỗi cùng lúc; không skip/xfail/only) 4. **có vấn đề** (việc sửa test có căn cứ thiết kế và chặt hơn, nhưng thiếu lý do trong commit: major) 5. đạt 6. đạt, kèm minor (escape) 7. đạt (chỉ thêm trường vào Single; `modified` đã nâng) 8. đạt (số dòng sai trong comment: minor) 9. không có phụ thuộc mới 10. **một phần** (commit đúng dạng, không trailer AI, nhưng message thiếu lý do sửa test cũ)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| E-1 cho qua tên Section Break/Column Break/Table của HD Ticket. Nơi đọc ở U4b/U6b nếu dùng `frappe.db.get_value("HD Ticket", …, <tên>)` sẽ gặp lỗi `Unknown column`. Cần ghi vào task U4b/U6b: chịu được trường không có cột, hoặc siết E-1 bằng `no_value_fields` qua designer. | |
| Mô tả `excluded_title_prefixes`, `field_*`, `origin_board_value` (nguyên văn thiết kế) hứa hành vi mà U2/U4b/U6b mới làm. Cần xác nhận các task đó còn trong plan trước khi đóng feature. | |
| Site đã cài từ trước: giá trị mặc định `[HR]\n[Kế toán]` có được ghi vào Singles sau migrate không (`test_every_new_field_default` đi qua `_value_after_install`). U2 phải đọc đúng khi chưa có dòng. | |
| Không chạy test (site dùng chung): `cmd.test_one` cho `test_erp_ai_setting.py` và `erp_ai/tests/test_doctype_descriptions.py` sau `cmd.migrate`. | |

## deferred

Không có (vòng 1).

## Vòng 2 — approve

- Lệnh đã dùng (chỉ đọc): `git diff 242a73f 4faf729 --stat` (không in gì: cùng cây), `git log -1 --format=%B 4faf729`, `git log -1 --format=%B 242a73f`, `git branch -r --contains 4faf729` / `242a73f` (rỗng, chưa push), `git log --oneline 4faf729..756755d`, `git diff --stat 4faf729..756755d`, `git diff 4faf729..756755d`, `git log -1 --format=%B 756755d`; `git show 756755d:<file>` cho `design.md` (dòng 104-106, 127-128, 294), `erp_ai_setting.py` (`:95-105`, `:199`, `:308`), `test_erp_ai_setting.py` (`:1320-1330`), `pyproject.toml`. Không chạy bench hay test.
- Range sửa: 1 commit `756755d` `fix(setting): escape the typed HD Ticket field name in E-1 and pin step 4 before 5 (FEAT-007)`, không trailer AI; 3 file trong touchpoints, +35/−4. Phần sửa ở `test_doctype_descriptions.py:557` chỉ là comment.
- Bằng chứng của dev: minor (2) RED `"Trường '<b>sai</b>' …" != "Trường '&lt;b&gt;sai&lt;/b&gt;' …"` (`FAILED (failures=1)`), rồi GREEN `Ran 60 tests OK`. Minor (3) xanh ngay lần đầu, đỏ khi đảo thứ tự hai lời gọi trong `validate` (`'Danh mục dòng 1: …' != "Trường 'sai_mot' …"`). GREEN cuối sau migrate: 60 / 12 / 112 test OK.

### Phát hiện vòng 1

- major STD-TEST-5, commit `242a73f` (message): **ADDRESSED** tại commit `4faf729` (message). Cây giống hệt `242a73f`. Message có thêm đoạn nêu lý do sửa `test_code_change_block_follows_feat006_fields` theo `design.md:104-106` (hàng 8-10), giữ lát cắt 4 phần tử cũ làm dãy con, không nới (STD-TEST-5, NFR-8). Viết lại lịch sử ở đây không vi phạm STD-GIT-4 vì nhánh chưa từng push.
- minor (1): đã làm (comment trỏ `design.md:104-106` và `:127-128`, đã đối chiếu, đúng). minor (2): đã làm (`erp_ai_setting.py:199` gọi `frappe.utils.escape_html(name)`, thống nhất với `:308`; `test_unknown_field_name_escaped` đỏ khi bỏ escape). minor (3): đã làm (`test_ticket_fields_checked_before_catalog`; đảo hai lời gọi ở `:104-105` hoặc bỏ `check_ticket_field_names()` thì đỏ). minor (4): chưa làm, tùy dev, không chặn.

### Phát hiện mới (chỉ blocker/major)

Không có.

### Review checklist (10), phạm vi diff sửa

1. đạt 2. đạt (3 file trong touchpoints) 3. đạt (RED cho escape; ca thứ tự có đột biến đỏ; không skip/xfail/only) 4. đạt (không đổi phép khẳng định cũ nào; lý do sửa test ở vòng 1 đã nằm trong commit) 5. đạt 6. đạt (escape đầu vào ở E-1, STD-SEC-3) 7. không áp dụng 8. đạt 9. không có phụ thuộc mới 10. đạt (`type(scope): … (FEAT-007)`, không trailer AI)

### deferred (vòng 2)

Không có.

### Kết luận của tech-lead trước khi tick (2026-11-14, sau merge `354e3c1`)

- Test sau merge trên `team/FEAT-007` @ `354e3c1`, một lần giữ khóa site: `cmd.migrate` exit 0; `test_erp_ai_setting` `Ran 60 tests in 2.613s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.344s OK`; `test_architecture` `Ran 112 tests in 3.397s OK`; `test_install` `Ran 37 tests in 16.420s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- E-1 cho qua tên Section Break/Column Break/Table của HD Ticket: KHÔNG giải được trong T13 (đúng chữ thiết kế). Chuyển team-leader: ghi vào kế hoạch U4b/U6b (nơi đọc phải chịu được trường không có cột) hoặc hỏi designer có siết E-1 bằng `no_value_fields` không.
- Mô tả trường hứa hành vi của U2/U4b/U6b: các đơn vị đó thuộc đợt 1 và 2 của FEAT-007, chưa lập kế hoạch; team-leader giữ khi lập `/team:plan` đợt 1.
- Mặc định `[HR]\n[Kế toán]` trên site đã cài từ trước: `test_every_new_field_default` (đi qua `_value_after_install`) và `test_install` xanh sau migrate trên `miyano`; việc U2 đọc đúng khi chưa có dòng thuộc U2.
- Số vòng: 2 (vòng 1 `request-changes`, vòng 2 `approve`).
