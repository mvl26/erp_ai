Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 10 — FEAT-007 T10

- Diff: `git diff e17164e..89bba5a` (nhánh `team/FEAT-007-task-10`, 2 commit `ed8ff90`, `89bba5a`); diff sửa vòng 2: `git diff ed8ff90..89bba5a`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng: `git log --oneline e17164e..ed8ff90`, `git diff --stat e17164e..ed8ff90`, `git diff e17164e..ed8ff90`, `git show ed8ff90:<path>` (`hard_bans.py`, `constants.py`, `install.py`, `site_api.py`, `hooks.py`, `.github/workflows/ci.yml`, `.team/profile.json`, phần lớp `TestCatalogRules`/`TestFeat007Defaults` của file test), `git grep -n` cho số dòng. Đọc thêm (chỉ đọc) `frappe/database/database.py:834-872` (`get_single_value`).
- Range: 1 commit, 4 file, +120/−3, đúng 4 file của touchpoints; không file mới, không đụng `protected_paths`, không marker skip của `test.skip_markers`.
- Bằng chứng của dev: RED sau khi đổi JSON + migrate, trước controller: `FAILED (failures=7)` với `None != 'Danh mục dòng 1: DocType Custom Role bị cấm cứng: DocType phân quyền'`, `'Row #1: Hành động cannot be "Xóa bản ghi"…' != 'Danh mục dòng 1: hành động không hợp lệ'`, `None != 'Danh mục dòng 1: DocType Note bị cấm cứn…'`. GREEN `test_erp_ai_setting` `Ran 44 tests` `OK`, `test_doctype_descriptions` `Ran 12 tests` `OK`, `test_architecture` `Ran 112 tests` `OK`.
- Lớp 1 (khớp spec): đủ phần Returns của T10 — `section_catalog` "Danh mục trắng" đứng sau `auto_approve_streak`, trước `section_limits` (`design.md:95-110` hàng 4); `catalog_rules` Table `ERP AI Catalog Rule`; mô tả trùng từng chữ `design.md:168` (251 ký tự, đủ 5 cụm bắt buộc); `check_catalog_rules()` gọi trong `validate`, lỗi `"Danh mục dòng {idx}: {lý do}"`, ba lý do đúng chữ E-4 (`design.md:299-302`). `DOCTYPE_CONFIG` tăng đúng 1 trường, 1 section, 1 hàng `phrases`, 1 hàng `sections`; `read_only_fields` không đổi (đúng). Không viết tên công tắc quyền (D-7); controller import `erp_ai.agent.hard_bans` (chiều đúng của F-1). Phần E-4 của T11 không bị làm trước. Thêm ngoài Expect: `test_unknown_doctype_blocked` (phủ lý do "không có DocType", hợp lệ).
- Kiểm đột biến bằng đọc (không chạy): bỏ bước `CATALOG_ACTIONS` → `_validate_selects` của Frappe ra chữ khác → đỏ; bỏ bước `frappe.db.exists` → `get_meta` ném `DoesNotExistError` chữ khác → đỏ; giữ bản sao tập cấm trong controller → ca (a) Note đỏ; chuyển kiểm sang `on_update` → khẳng định `stored_before` đỏ; ca (a) có khẳng định nền (Note lưu được trước patch). Chỗ còn hở xem minor (a), (b).

## Phát hiện (chỉ blocker/major)

major | STD-TEST-5 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:607 | Hàng `"catalog_rules": None` của `FEAT007_NEW_FIELD_DEFAULTS` không bao giờ đỏ được: `_value_after_install` (`:625`) đọc `frappe.db.get_single_value`, mà hàm này chỉ đọc `tabSingles` (`frappe/database/database.py:852-857`); trường Table không có dòng `tabSingles`, nên kết quả luôn là `None` dù `install` có gieo dòng danh mục mặc định hay không (chính comment ở `:606` nói vậy). "Mặc định không có dòng nào" là một vế của AC-29 và là mặc định an toàn (rỗng = bot không ghi ERP), hiện không có khẳng định nào giữ nó | Với trường Table, kiểm dòng con thật: xóa dòng `ERP AI Catalog Rule` của setting (`parent`/`parenttype` = `SETTING_DOCTYPE`, `parentfield` = `catalog_rules`), chạy `install._ensure_default_settings()` (hoặc `after_install` đủ bước), rồi khẳng định `frappe.get_all(CATALOG_RULE_DOCTYPE, filters={"parent": SETTING_DOCTYPE, "parentfield": "catalog_rules"})` == `[]`; giữ một hàng trong bảng mặc định nhưng cho helper rẽ theo `fieldtype == "Table"` để vẫn một test cho mọi trường | confirmed

minor | — | — | 4 điểm nhỏ: (a) STD-TEST-8: nhánh `if not doctype: return None` (`erp_ai_setting.py:181`) không có ca (dòng không DocType, ví dụ `ACTION_CREATE_USER`); bỏ nhánh thì dòng hợp lệ bị từ chối "không có DocType None" mà vẫn xanh — T11 `test_valid_rule_saves_and_categories_normalized` nên có ca này; (b) STD-TEST-8: mọi ca đều ở dòng 1; chưa có ca dòng cấm đứng sau một dòng hợp lệ (ghim `{idx}` = 2 và "kiểm mọi dòng"); (c) STD-ERR-2 (suspected): `frappe.db.exists("DocType", …)` (`:183`) không phân biệt hoa thường trên MariaDB còn tập cấm so khớp đúng chữ, nên khi link không được kiểm (đúng tiền đề của `test_unknown_doctype_blocked`) `"custom role"` qua được cả hai; lưu qua form/REST thì `_validate_links` sửa về đúng chữ nên chỉ hở ở đường bỏ kiểm link — cân nhắc lấy tên chuẩn từ `frappe.db.get_value("DocType", doctype, "name")` rồi kiểm trên tên đó; (d) STD-STYLE-4: docstring `catalog_rule_error` "The first E-4 reason" trong khi mới cài 3/9 lý do của E-4 (T11 bổ sung) | tùy dev

## Review checklist (10)
1. đạt lớp 1 (đủ Returns, không làm trước T11) 2. đạt (4/4 file của touchpoints) 3. chưa đạt (major: hàng mặc định `catalog_rules` không đỏ được; minor a, b; RED có trước, không skip) 4. đạt (không sửa khẳng định cũ; lớp có `keep_agent_settings` + rollback) 5. đạt (minor c) 6. đạt (không bí mật; kiểm lúc lưu chạy phía server) 7. đạt (chỉ thêm trường/section; migrate lên/xuống chưa kiểm — bảng dưới) 8. đạt (minor d) 9. đạt (không phụ thuộc mới) 10. đạt (`feat(setting): … (FEAT-007)`, không trailer; tài liệu người dùng là mô tả trường đi cùng diff)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.migrate` rồi `cmd.test_one` cho `test_erp_ai_setting`, `test_doctype_descriptions`, `test_architecture` sau merge (luật site dùng chung: reviewer không chạy) | |
| `field_count` 40 / `section_count` 10 khớp meta thật sau migrate (con số do dev báo) | |
| Ca `Sales Invoice` cần ERPNext trên site: `required_apps` chỉ có `helpdesk`; CI có `install-app erpnext` (`.github/workflows/ci.yml:94,100`), site `miyano` chưa kiểm | |
| Thứ tự `run_before_save_methods` trước `_validate_selects` của Frappe (để ra "hành động không hợp lệ" thay vì lỗi Select) chỉ được chứng bằng GREEN của dev | |

## deferred

- (T11) ca dòng không DocType và ca dòng cấm ở `idx` ≥ 2 (minor a, b) có chỗ tự nhiên trong `test_row_shape_rules` / `test_valid_rule_saves_and_categories_normalized`.
- (INT-1) ca (c) `Role` của `test_hard_ban_follows_denied_doctypes_source` (`design-w0-fixes.md:118`) chưa thuộc T10.
- (minor, tùy dev) c, d ở trên.

## Vòng 2 — approve

- Lệnh đã dùng: `git log --oneline e17164e..89bba5a`, `git diff --stat ed8ff90..89bba5a`, `git diff ed8ff90..89bba5a`, `git show 89bba5a:erp_ai/install.py` (`_ensure_default_settings`, `:90-104`), `git show 89bba5a:<file test>` (đầu file, lớp `TestFeat007Defaults`), `git grep -n` cho số dòng và `CATALOG_RULE_DOCTYPE`; đối chiếu `design.md:124` (mặc định `catalog_rules` = rỗng, AC-29) và `tasks.md:16`.
- Range sửa: 1 commit `89bba5a` `test(setting): … (FEAT-007)`, 1 file (`test_erp_ai_setting.py`, +7/−2), trong touchpoints; không đụng code chạy, không marker skip, không trailer.
- Bằng chứng của dev: RED (không commit; thêm và lưu một dòng ngay sau lệnh install): `FAIL: test_catalog_starts_empty_after_install` / `AssertionError: Lists differ: [{'name': '0a4fm0dlk1'}] != []` / `FAILED (failures=1)`. GREEN `test_erp_ai_setting` `Ran 45 tests` `OK`, `test_doctype_descriptions` `Ran 12 tests` `OK`, `test_architecture` `Ran 112 tests` `OK`.

### Phát hiện vòng 1

- major STD-TEST-5 `test_erp_ai_setting.py:607` (hàng `"catalog_rules": None` không đỏ được) — **ADDRESSED**: hàng bị bỏ khỏi `FEAT007_NEW_FIELD_DEFAULTS` (`:592-605` @ `89bba5a`); thay bằng `test_catalog_starts_empty_after_install` (`:654-659`) xóa dòng con `ERP AI Catalog Rule` theo `parent` = `SETTING_DOCTYPE`, `parentfield` = `catalog_rules`, chạy `install._ensure_default_settings()`, khẳng định `frappe.get_all(...)` == `[]`. Kiểm đột biến bằng đọc: cho bước install gieo một dòng danh mục (vô điều kiện hoặc "khi chưa có dòng") → bảng không rỗng → đỏ (RED của dev cho đúng dạng này); bộ lọc dùng `parent` + `parentfield` nên dòng của bảng con khác không lọt vào. Lớp có `keep_agent_settings` + `rollback` nên lệnh xóa không rò sang test khác (STD-TEST-6). `CATALOG_RULE_DOCTYPE` khai báo cấp module (`:811`), được tra lúc chạy nên dùng ở `:657` hợp lệ.
- Quy ước `tasks.md:16` ("dòng mới của `test_every_new_field_default` cho mọi trường"): dev chọn test riêng thay vì cho helper rẽ theo `fieldtype` — cả hai đều nằm trong cách sửa vòng 1 đề xuất; mục đích của quy ước (mặc định của mỗi trường mới có khẳng định đỏ được, theo `design.md:124` "rỗng") đạt. Không phải phát hiện.

### Phát hiện mới (chỉ blocker/major)

Không có.

minor | — | — | 1 điểm nhỏ: STD-STYLE-4: comment `:592` vẫn nói `FEAT007_NEW_FIELD_DEFAULTS` có "one row per field as tasks add them", nay `catalog_rules` nằm ở test riêng — thêm một câu "Table fields: see test_catalog_starts_empty_after_install" để task sau (ví dụ `user_templates`) không thêm lại hàng `None` | tùy dev

### Review checklist (10), phạm vi diff sửa
1. đạt (vế "mặc định rỗng" của AC-29 có khẳng định; không thêm gì ngoài) 2. đạt (1 file trong touchpoints) 3. đạt (RED trước, không skip/xfail) 4. đạt (bỏ một khẳng định không đỏ được, không nới khẳng định đúng; độc lập nhờ rollback) 5. không áp dụng (chỉ sửa test) 6. đạt (không bí mật, không dữ liệu nhạy cảm) 7. không áp dụng (không đổi JSON/hợp đồng) 8. đạt (minor comment `:592`) 9. đạt (không phụ thuộc mới) 10. đạt (`test(setting): … (FEAT-007)`, không trailer AI)

### Không kiểm được từ diff — tech-lead xử lý trước khi tick (vòng 2)

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.test_one` cho `test_erp_ai_setting` (45 test), `test_doctype_descriptions`, `test_architecture` sau merge (luật site dùng chung: reviewer không chạy) | |
| Bốn mục của bảng vòng 1 ở trên vẫn mở (migrate + `field_count`/`section_count`, ca `Sales Invoice` cần ERPNext trên `miyano`, thứ tự `run_before_save_methods` trước `_validate_selects`) | |

### deferred (vòng 2)

- Giữ nguyên các mục deferred của vòng 1 (minor a, b cho T11; ca `Role` cho INT-1; minor c, d tùy dev).
- (task thêm `user_templates`, cùng section) trường Table thứ hai cần test dòng con giống `test_catalog_starts_empty_after_install`, không thêm hàng `None` vào `FEAT007_NEW_FIELD_DEFAULTS`.
