Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 11 — FEAT-007 T11

- Diff: `git diff a9e0704..c2967dd` (nhánh `team/FEAT-007-task-11`, 1 commit `c2967dd`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng: `git log --oneline a9e0704..c2967dd`, `git diff --stat a9e0704..c2967dd`, `git diff a9e0704..c2967dd`, `git log -1 --format='%an%n%B' c2967dd`, `git show c2967dd:<path>` (`tasks.md` dòng 1-25 và khối T11, `design.md:200-225, 294-310`, `design-w0-fixes*.md`, `arch-review-design-w0-r2.md`, `plan.md` "Ràng buộc chung", `erp_ai/constants.py`, `.team/profile.json`, lớp `TestCatalogRules` của file test), `git grep -n` cho số dòng. Đọc `review-10.md` (mục deferred).
- Range: 1 commit, 2 file, +185/−10, đúng 2 file của touchpoints; không file mới, không đụng `protected_paths`, không marker của `test.skip_markers`; không sửa khẳng định cũ nào (diff test chỉ thêm).
- Bằng chứng của dev: RED `FAIL: test_row_shape_rules [...] AssertionError: None != 'Danh mục dòng 2: hành động này không nhận DocType'`, `test_valid_rule_saves_and_categories_normalized: Lists differ ... 'C,A' != 'A,C'`, `Ran 48 tests in 1.896s` / `FAILED (failures=25)`. GREEN `test_erp_ai_setting` `Ran 48 tests in 1.678s` / `OK`; `test_architecture` `Ran 112 tests in 3.159s` / `OK`. Số test 45 (sau T10) + 3 mới = 48 khớp.
- Lớp 1 (khớp spec): đối chiếu từng chữ với `design.md:214-221` và E-4 `design.md:298-305` (các file `design-w0-fixes*.md` không sửa phần này; `design-w0-fixes.md:64` chỉ chốt bước "hành động không hợp lệ" so với `CATALOG_ACTIONS`).
  - Bảng hành động: 4 hành động cố định (`CREATE_USER`, `ADD_TEAM_MEMBER`, `ADD_HOLIDAY`, `SET_ITEM_GROUP`) cấm cả `target_doctype` lẫn `fields`; `CREATE_CUSTOM_FIELD` cần DocType, cấm `fields`; `UPDATE_FIELDS` cần DocType và ≥ 1 trường — đúng bảng (`erp_ai_setting.py:67, 194-216`).
  - 9 lý do của E-4 đúng chữ, đúng thứ tự liệt kê; chuỗi `A–F` là U+2013 như trong `design.md:304` (đã so byte `e2 80 93`), test ghim cùng ký tự.
  - Dòng trùng: khóa `(action, target_doctype)` theo E-4 "cùng `action` + `target_doctype`"; `fields`, `categories` không nằm trong khóa (ca dòng 3 khác cả hai vẫn trùng); `{j}` là dòng đầu.
  - `categories` chuẩn hóa `A,B` (bỏ trùng, sắp xếp) đúng `design.md:209` và Returns.
  - Thêm ngoài Expect: `test_unknown_action_and_case_variant_doctype` và đổi bước T10 sang tên DocType đã lưu (`:200-205`). Đây là phần deferred của `review-10.md` (minor a, b cho T11; minor c tùy dev), nằm trong touchpoints; không phải mở rộng phạm vi.
  - Quy ước `tasks.md:12-19`: controller không viết tên công tắc quyền; không thêm `"HD Ticket Comment"` / `"reference_ticket"`; `test_architecture.py` không bị sửa.
- Kiểm đột biến bằng đọc (không chạy), mỗi luật của mã:
  - bỏ "hành động không hợp lệ" → `_validate_selects` của Frappe ra chữ khác → `test_unknown_action_and_case_variant_doctype` đỏ;
  - bỏ "không nhận DocType", hoặc thêm một hành động cố định vào `DOCTYPE_ACTIONS` → dòng `(hành động cố định, Note)` lưu được → đỏ (đủ 4 hành động có ca);
  - bỏ "cần DocType" → 2 ca đỏ;
  - bỏ "không nhận danh sách trường" → 5 ca đỏ (4 hành động cố định + Custom Field);
  - bỏ "cần ít nhất một trường", hoặc bỏ lọc dòng trống → ca `None` / `"\n  \n"` đỏ;
  - chỉ kiểm trường đầu → ca `"title\nkhong_co_truong"` đỏ;
  - `all` → `any`, bỏ `strip`, bỏ `set`, bỏ `sorted`, hoặc lọc phần rỗng → các ca `"A,G"`, `" F ,E,F,D "`, `"B,B"`, `"C,A"`, `"A,,B"` / `"A,"` đỏ;
  - khóa trùng chỉ theo `action` → cặp Custom Field Note/ToDo đỏ;
  - khóa trùng chỉ theo DocType → cặp Custom Field/Đổi trường trên Note đỏ;
  - khóa trùng theo chữ gõ thay tên đã lưu → ca `Note`/`NOTE` đỏ;
  - bỏ `row.target_doctype = doctype` → `_stored_rows` ra `"note"` → đỏ;
  - kiểm cấm trên chữ gõ → ca `"erp ai log"` lưu được → đỏ;
  - `{idx}` cố định → mọi ca dòng 2/3 đỏ;
  - chuyển kiểm sang `on_update` → khẳng định `stored_before` đỏ.

  Không thấy luật nào bỏ đi mà mọi test vẫn xanh.
- Thiết kế im lặng (không phải phát hiện của dev): (i) `meta.has_field` nhận cả trường bố cục (Section/Column/Tab Break), trường Table và tên trường lặp (`"title\ntitle"`), còn từ chối cột chuẩn (`name`, `owner`); E-4 chỉ nói "trường {f} không có trên {dt}". (ii) `categories` có khoảng trắng quanh chữ (`" F ,E"`) được nhận rồi chuẩn hóa; `design.md:209` không cấm, hợp lý. Cả hai không chặn việc chấm T11; (i) là chỗ bộ thực thi U7 phải quyết.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 2 điểm nhỏ: (a) STD-DESIGN-4: `fields` được kiểm sau khi `strip` và bỏ dòng trống (`erp_ai_setting.py:207`) nhưng lưu nguyên chữ gõ (`" title "` qua được kiểm mà lưu kèm khoảng trắng), nên bộ thực thi U7 phải tách đúng như vậy mới khớp — cân nhắc lưu `"\n".join(fields)` như đã làm với `categories`, hoặc để U7 gọi chung một hàm tách; (b) STD-DESIGN-4 (suspected): `DOCTYPE_ACTIONS` (`erp_ai_setting.py:67`) là tri thức "hành động nào nhận DocType" chỉ đặt ở controller; nếu U7 cần thì chuyển xuống `erp_ai/constants.py` (F-1), không chép | tùy dev

## Review checklist (10)
1. đạt (đủ 9 lý do E-4, bảng hành động, dòng trùng, chuẩn hóa `categories`; test thứ ba là deferred của T10) 2. đạt (2/2 file của touchpoints, không file mới) 3. đạt (RED có trước; mỗi luật có ca đỏ được, gồm biên `"A,,B"`, `"A,"`, dòng trống, chữ hoa/thường; không skip/xfail) 4. đạt (không sửa khẳng định cũ; lớp có `keep_agent_settings` + `rollback`; dữ liệu là DocType lõi `Note`/`ToDo`) 5. đạt (kiểm đầu vào ở ranh giới lưu; không `except` nuốt lỗi) 6. đạt (không bí mật; `get_value` qua ORM, không ghép truy vấn) 7. đạt (không đổi JSON; dòng mới lưu dưới tên DocType chuẩn và `categories` dạng `A,B`, chưa có bên đọc) 8. đạt (tên theo profile; docstring khớp hành vi; minor a, b) 9. đạt (không phụ thuộc mới) 10. đạt (`feat(setting): … (FEAT-007)`, không trailer AI; không có tài liệu người dùng phải đổi ngoài mô tả trường đã có ở T10)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.test_one` cho `test_erp_ai_setting` (48 test) và `test_architecture` sau merge (luật site dùng chung: reviewer không chạy) | |
| Site `miyano` đã có dòng `catalog_rules` lưu theo luật T10 mà nay sai luật T11 (ví dụ hành động cố định có `target_doctype`, `categories` thường hay có khoảng trắng) không: nếu có, mọi lần lưu ERP AI Setting (kể cả `set_agent_settings` của test khác) sẽ ném lỗi "Danh mục dòng …" | |
| Thứ tự `run_before_save_methods` trước `_validate_selects` / `_validate_mandatory` của Frappe (để ra "hành động không hợp lệ" và lỗi `categories` thay vì lỗi của Frappe) chỉ được chứng bằng GREEN của dev — vẫn mở từ `review-10.md` | |
| `frappe.db.get_value("DocType", "note")` trả `"Note"` (so khớp không phân biệt hoa thường của MariaDB) chỉ được chứng bằng GREEN của `test_unknown_action_and_case_variant_doctype` | |

## deferred

- (U7, bộ thực thi) loại trường nào `Đổi trường` được ghi (bố cục, Table, cột chuẩn, tên lặp) — thiết kế im lặng (i) ở trên.
- (minor, tùy dev) a, b ở trên.
- Giữ mục deferred của `review-10.md` còn lại: ca (c) `Role` cho INT-1; minor d (docstring) nay đã đúng sau T11.
