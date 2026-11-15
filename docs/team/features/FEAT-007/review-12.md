Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 12 — FEAT-007 T12

- Diff: `git diff 888f5dc..347ca00` (nhánh `team/FEAT-007-task-12`, 2 commit `c5e063e`, `347ca00`); diff sửa vòng 2: `git diff c5e063e..347ca00`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng: `git log --oneline 888f5dc..c5e063e`, `git diff --stat 888f5dc..c5e063e`, `git diff 888f5dc..c5e063e`, `git log -1 --format='%an%n%B' c5e063e`, `git show c5e063e:<path>` (`erp_ai/agent/tools/site_api.py` dòng 36 và 105-121, `erp_ai/tests/test_doctype_descriptions.py` phần so cụm chữ, `erp_ai_setting.py:160-186`), `git grep -n … c5e063e` cho số dòng. Đọc thêm (chỉ đọc): `tasks.md` dòng 12-19 và khối T12, `design.md:100, 125, 169, 225, 294-306, 635`, `design-w0-fixes.md:100-125, 302`, `arch-review-design-w0-r2.md:60`, `spec.md:196` (AC-30), `review-11.md`, `.team/profile.json` (`allowed_new_file_roots`, `skip_markers`, `protected_paths`). Có một lần đọc ngoài diff vì một rủi ro gọi tên được (collation): `frappe/database/mariadb/database.py:130, 307` và `schema.py:61` → `utf8mb4_unicode_ci`.
- Range: 1 commit, 7 file, +260/−4. Cả 7 file đều nằm trong touchpoints. 3 file mới nằm dưới `erp_ai/` (STD-STRUCT-1). Không đụng `protected_paths`, không có marker nào của `test.skip_markers`. Diff test chỉ thêm, không sửa khẳng định cũ nào.
- Bằng chứng của dev: RED `test_doctype_descriptions` `AssertionError: 40 != 41`, `FAILED (failures=2)`. RED `test_erp_ai_setting` cho cả 4 loại lý do (`None != 'Mẫu tài khoản dòng 2: vai trò System Manager bị cấm cho bot'`, `… không có vai trò …`, `… trùng tên với dòng 1`, và lỗi bắt buộc của Frappe `'[ERP AI Setting, ERP AI Setting]: template_name'` cho tên trống). GREEN sau migrate: `Ran 53 tests` / `OK`, `Ran 12 tests` / `OK`, `test_architecture` `Ran 112 tests` / `OK`. Số test: 48 (sau T11) + 1 ở `TestFeat007Defaults` + 4 ở `TestUserTemplates` = 53, khớp.
- Lớp 1 (khớp spec):
  - DocType con `ERP AI User Template` có `template_name` (Data, reqd), `roles` (Small Text), `note` (Small Text), `istable: 1`, controller rỗng. Đúng `design.md:225`. Trường `user_templates` (Table) đứng ngay sau `catalog_rules` trong `section_catalog`, đúng `design.md:100`. Mô tả trường trùng từng chữ với `design.md:169`.
  - `check_user_templates()` báo lỗi theo dạng `"Mẫu tài khoản dòng {idx}: {lý do}"`. Hai lý do có chữ trong thiết kế (`"không có vai trò {r}"`, `"vai trò {r} bị cấm cho bot"`) đúng từng chữ. `FORBIDDEN_ROLES` lấy từ `site_api.FORBIDDEN_ROLES` (`design-w0-fixes.md:115`). Ba lý do thiết kế chỉ nêu ý (tên trống, tên trùng, không có vai trò nào) được dev đặt chữ là `"tên mẫu không được để trống"`, `"trùng tên với dòng {j}"`, `"cần ít nhất một vai trò"`. Ba câu này cùng giọng với E-4 (`"cần ít nhất một trường"`, `"trùng với dòng {j}"`). Thiết kế không bắt buộc thứ tự kiểm nên thứ tự dev chọn (tên trống → lỗi vai trò → tên trùng) không phải phát hiện. Phần dư so với `Returns` là lưu lại vai trò theo tên thật, mỗi dòng một vai trò. Việc này cùng kiểu với cách T11 chuẩn hóa `categories`/`target_doctype`, nằm trong touchpoints và không phải mở rộng phạm vi.
  - `DOCTYPE_CONFIG`: `ERP AI Setting` có `field_count` 40 → 41, `section_count` giữ nguyên, có cụm chữ của `user_templates`. Mục mới cho bảng con: 3 trường, 2 section. Hàm so cụm chữ dùng `.lower()`, nên `"ghi chú"` khớp với `"Ghi chú …"`.
  - Phần deferred chuyển từ `review-10.md` đều đã làm. Có test dòng con `test_user_templates_start_empty_after_install` (`test_erp_ai_setting.py:663`). Không thêm dòng `None` vào `FEAT007_NEW_FIELD_DEFAULTS`, chỉ thêm một dòng chú thích. → ADDRESSED.
  - **Missing (một phần của AC-30 (1)):** có cách viết khác mà vẫn lưu được vai trò cấm, xem phát hiện 1.
- Kiểm đột biến bằng cách đọc mã (không chạy):
  - Bỏ kiểm vai trò cấm → 12 subtest đỏ.
  - So khớp đúng chữ thay cho `casefold` → ca `role.upper()` lưu được, đỏ.
  - Thông điệp lấy chữ người gõ thay tên chuẩn → ca chữ hoa đỏ.
  - Chỉ kiểm vai trò đầu dòng → ca `OFFICE_ROLE\n<cấm>` đỏ.
  - Bỏ kiểm vai trò không có → đỏ.
  - Bỏ lọc dòng trống → ca `"\n  \n"` và ca hợp lệ đỏ.
  - Lưu chữ người gõ thay tên thật → `_stored_templates` đỏ.
  - Khóa trùng không `strip` hoặc không `casefold` → ca `"  thủ kho "` / `"THỦ KHO"` đỏ.
  - Bỏ nhánh tên trống → lỗi bắt buộc của Frappe ra chữ khác, đỏ.
  - Chuyển kiểm sang `on_update` → khẳng định `stored_before` đỏ.
  - Còn hai chỗ sống sót: (a) dạng có dấu của vai trò cấm, là phát hiện 1; (b) `{idx}`/`{j}` ghi cứng `2`/`1`, xem minor (a).

### Phát hiện (chỉ blocker/major)

major | STD-ERR-2 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:210-215 | Mã kiểm vai trò cấm trên **chữ người gõ** (`role.casefold() in forbidden`, dòng 210), sau đó mới tra tên thật bằng `frappe.db.get_value("Role", role)` (dòng 212) và lưu tên thật đó (dòng 216). Bảng `tabRole` dùng collation `utf8mb4_unicode_ci` (`frappe/database/mariadb/database.py:130`, `schema.py:61`). Collation này không phân biệt hoa thường **và cũng không phân biệt dấu**. Vì vậy `"Gúest"`, `"Sýstem Manager"`, `"Âll"`, `"Ádministrator"` không trùng khóa `casefold` nào, nhưng `get_value` vẫn trả `"Guest"`, `"System Manager"`, ... Kết quả: mẫu lưu được và chứa đúng vai trò cấm dưới tên thật. Đây là việc AC-30 (1) cấm (`spec.md:196`). T11 đã tránh lỗi này bằng cách kiểm cấm trên tên đã lưu (`review-11.md`: "kiểm cấm trên chữ gõ → … đỏ"). Test chỉ có biến thể chữ hoa (`test_erp_ai_setting.py:1196`), nên lỗ này không có ca đỏ (STD-TEST-8) | Tra `real` trước, rồi kiểm `real in site_api.FORBIDDEN_ROLES` và báo `"vai trò {real} bị cấm cho bot"`. Giữ cả bước kiểm `casefold` trên chữ gõ cho trường hợp vai trò cấm không có trên site. Thêm vào `test_forbidden_role_blocked` một biến thể có dấu cho mỗi vai trò (ví dụ thay một nguyên âm bằng dạng có dấu sắc), vẫn chờ thông điệp mang tên chuẩn | confirmed (đọc mã + collation của Frappe; chưa chạy trên site, xem bảng dưới)

minor | — | — | 3 điểm nhỏ: (a) STD-TEST-8: mọi ca lỗi đều nằm ở dòng 2 và mọi ca trùng đều trùng với dòng 1 (`test_erp_ai_setting.py:1189-1225`), nên ghi cứng `"dòng 2"` / `"dòng 1"` hoặc dùng `len(self.user_templates)` thay `row.idx` vẫn xanh. Nên thêm một ca có dòng hỏng ở vị trí 3 và trùng với dòng 2. (b) STD-NAME-6: `user_template_error` (`erp_ai_setting.py:202`) có tên như hàm chỉ đọc nhưng lại sửa `row.roles` (dòng 216). Docstring có nói điều này, nhưng nên đổi tên (ví dụ `normalize_user_template`) hoặc đưa việc gán vào `check_user_templates`, như T11 làm với `target_doctype`. (c) STD-DESIGN-4: `check_user_templates` và `check_catalog_rules` lặp cùng khung vòng lặp `seen`/`idx`/`throw`. Chấp nhận được ở 2 nơi; nếu T13+ thêm nơi thứ ba thì nên gộp | tùy dev

### Review checklist (10)

1. **chưa đạt**: thiếu một phần AC-30 (1), vai trò cấm viết có dấu vẫn lưu được (phát hiện 1). Phần còn lại đạt: DocType con, trường, 5 lý do E-5, `DOCTYPE_CONFIG`, deferred của T10.
2. đạt: 7/7 file của touchpoints; 3 file mới dưới `erp_ai/`.
3. **chưa đạt**: RED có trước và đủ 4 loại lý do; có biên (chữ hoa, khoảng trắng, dòng trống, `None`, tên khác một chữ); không skip/xfail. Thiếu biên chữ có dấu (phát hiện 1); `{idx}` chỉ ghim một vị trí (minor a).
4. đạt: không sửa khẳng định cũ. Lớp mới gọi `keep_agent_settings` + `rollback`, tự tạo 2 Role riêng, không phụ thuộc thứ tự chạy, không dùng đồng hồ thật.
5. **chưa đạt**: kiểm đầu vào ở ranh giới lưu có, nhưng kiểm trên chữ gõ thay vì giá trị đã chuẩn hóa (STD-ERR-2). Không có `except` nuốt lỗi.
6. đạt có điều kiện: không bí mật; `get_value` đi qua ORM, không ghép truy vấn. Nhưng lỗ ở phát hiện 1 là lỗ cấp vai trò cấm, phải đóng trước khi U7 đọc mẫu.
7. đạt: thêm DocType và trường Table, chưa có bên đọc. Migrate xuống thuộc test lên/xuống của U0 (`design.md:711`), xem bảng dưới.
8. đạt: tên theo profile (`ERPAIUserTemplate`, snake_case); không có mã chết; minor b.
9. đạt: không thêm phụ thuộc mới.
10. đạt: `feat(setting): … (FEAT-007)`, không trailer AI, nhánh `team/FEAT-007-task-12`. Mô tả trường cho người dùng đi cùng thay đổi.

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.test_one` cho `test_erp_ai_setting` (53 test), `test_doctype_descriptions` (12) và `test_architecture` (112) sau rework/merge. Luật dùng chung site: reviewer không chạy | |
| Xác nhận trên site `miyano` rằng `frappe.db.get_value("Role", "Gúest")` trả `"Guest"` (collation không phân biệt dấu của `tabRole`). Đây là bằng chứng chạy thật cho phát hiện 1; ca test mới của rework cũng chứng được điều này | |
| `cmd.migrate` đã tạo bảng `tabERP AI User Template` trên site (dev báo `migrate_exit=0`). Đường migrate xuống của DocType con mới chưa có test; hiện để cho test lên/xuống của U0 | |
| Thứ tự Frappe chạy `validate` của controller trước `_validate_mandatory`, để ra `"tên mẫu không được để trống"` thay vì lỗi bắt buộc của Frappe. Chỉ được chứng bằng GREEN của dev | |
| `cmd.lint` (`pre-commit run --all-files`) trên nhánh task | |

## deferred

- (ngoài diff, suspected) `site_api._values_refusal` (`erp_ai/agent/tools/site_api.py:118`) so `role in FORBIDDEN_ROLES` đúng từng chữ. Nếu kiểm Link của Frappe chuẩn hóa `"system manager"` / `"Sýstem Manager"` thành tên thật khi lưu User, đường công cụ có cùng lỗ như phát hiện 1. Cần chủ của `site_api` hoặc bộ thực thi U7 xem; không chặn T12.
- (U7, thiết kế im lặng) Role có `disabled = 1` vẫn được nhận vào mẫu; `design.md:225, 306` không nói. U7 quyết khi tạo tài khoản.
- (minor, tùy dev) a, b, c ở trên.
- Deferred của `review-10.md` cho T12 (test dòng con của Table thứ hai, không có dòng `None`): ADDRESSED tại `test_erp_ai_setting.py:663` và dòng chú thích trên `FEAT007_NEW_FIELD_DEFAULTS`.

## Vòng 2 — approve

- Lệnh đã dùng: `git log --oneline c5e063e..347ca00`, `git diff --stat c5e063e..347ca00`, `git diff c5e063e..347ca00`, `git log -1 --format='%an%n%B' 347ca00`, `git diff --stat 888f5dc..347ca00` (cả task), `git show 347ca00:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (dòng 170-225), `git show 347ca00:erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (dòng 1125-1260), `git grep -n … 347ca00`. Không chạy bench hay test.
- Range sửa: 1 commit `347ca00` `fix(setting): check forbidden roles on the real role name too (FEAT-007)`, không trailer AI; 2 file, +29/−3, cả hai trong touchpoints. Không file mới, không marker của `test.skip_markers`, không đụng `protected_paths`. Không khẳng định cũ nào bị nới.
- Bằng chứng của dev: RED `Ran 53 tests`, `FAILED (failures=7)`: 6 lỗi `AssertionError: None != 'Mẫu tài khoản dòng 2: vai trò … bị cấm cho bot'` (mỗi vai trò cấm một lỗi) và `Lists differ: [... ('Quản trị', 'ERP AI Test Văn phòng\nAll', None)] != []`. GREEN sau migrate (exit 0): `test_erp_ai_setting` `Ran 53 tests` `OK`, `test_doctype_descriptions` `Ran 12 tests` `OK`, `test_architecture` `Ran 112 tests` `OK`. RED này là bằng chứng chạy thật cho phát hiện vòng 1: trên `miyano`, `get_value("Role", "<dạng có dấu>")` trả tên thật.

### Phát hiện vòng 1

- major STD-ERR-2 `erp_ai_setting.py:210-215` — **ADDRESSED** tại `erp_ai_setting.py:215-219` @ `347ca00`: sau `real = frappe.db.get_value("Role", role)` (`:215`), mã kiểm `real in site_api.FORBIDDEN_ROLES` và báo `f"vai trò {real} bị cấm cho bot"` (`:218-219`). Test `test_forbidden_role_blocked` (`test_erp_ai_setting.py:1198-1213`) thêm `ACCENTED_FORBIDDEN_ROLES` (`:1138-1145`) cho đủ 6 vai trò; `:1203` ghim tập khóa bằng `SPEC_FORBIDDEN_ROLES`. Đột biến đọc theo mã: bỏ `:218-219` → 7 lỗi của RED; báo `{role}` thay `{real}` → đỏ; kiểm `real` sau `stored.append(real)` mà không `return` → đỏ; dời bước kiểm lên trước `get_value` → đỏ.
- minor (a) vòng 1 — đã làm: ca 4 dòng ở `test_erp_ai_setting.py:1237-1246` chờ `"Mẫu tài khoản dòng 3: trùng tên với dòng 2"`; ghi cứng `2`, `1` hay dùng `len(self.user_templates)` đều đỏ. Ca xanh ngay lần đầu là đúng (mã đã dùng `row.idx`/`seen[key]` từ vòng 1).
- minor (b), (c) vòng 1: chưa làm, tùy dev, không chặn.

### Phát hiện mới (chỉ blocker/major)

Không có.

minor | — | — | 1 điểm nhỏ: STD-TEST-8. Bước kiểm `casefold` trên chữ gõ (`erp_ai_setting.py:213-214`) giữ theo đề xuất vòng 1, nhưng không test nào đỏ khi bỏ nó, vì cả 6 vai trò cấm đều có trên site và bước kiểm tên thật ở `:218` cho cùng thông điệp. Bỏ bước này cũng không mở lỗ: nếu một vai trò cấm không có trên site, mẫu vẫn bị chặn, chỉ khác chữ. Hai cách: (1) thêm ca patch `frappe.db.get_value` trả `None` cho riêng tên đó và chờ `"bị cấm"`; (2) một dòng chú thích ở `:213` | tùy dev

### Review checklist (10), phạm vi diff sửa

1. đạt (vế "vai trò cấm viết có dấu vẫn lưu được" của AC-30 (1) đã đóng) 2. đạt (2 file trong touchpoints) 3. đạt (RED 7 lỗi có trước; biên chữ có dấu cho 6 vai trò, biên `{idx}`/`{j}`; không skip/xfail/only) 4. đạt 5. đạt (kiểm trên giá trị đã chuẩn hóa, STD-ERR-2) 6. đạt (lỗ cấp vai trò cấm qua mẫu tài khoản đã đóng) 7. không áp dụng 8. đạt 9. đạt 10. đạt (`fix(setting): … (FEAT-007)`, không trailer AI)

### deferred (vòng 2)

- Giữ các mục deferred của vòng 1: `site_api._values_refusal` (`erp_ai/agent/tools/site_api.py:118`) so đúng từng chữ, cùng loại lỗ trên đường công cụ (suspected; nay thêm cơ sở vì RED của dev cho thấy collation của `tabRole` trên `miyano` không phân biệt dấu) → chủ `site_api` / U7; Role `disabled = 1` vẫn được nhận vào mẫu (U7 quyết); minor (b), (c) và minor vòng 2 tùy dev.

### Kết luận của tech-lead trước khi tick (2026-11-14, sau merge `5f64531`)

- Test sau merge trên `team/FEAT-007` @ `5f64531`, một lần giữ khóa site: `cmd.migrate` exit 0; `test_erp_ai_setting` `Ran 53 tests in 2.191s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.343s OK`; `test_architecture` `Ran 112 tests in 3.313s OK`; `test_install` `Ran 37 tests in 16.472s OK`.
- `cmd.lint` trên nhánh feature sau merge: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền); dev báo hook xanh cho 2 file của mình.
- `get_value("Role", "Gúest")` → `"Guest"`: xác nhận bằng RED chạy thật của dev ở vòng 2 (`Áll` lưu thành `All`).
- Migrate tạo bảng con: migrate exit 0 và `TestUserTemplates` xanh sau merge. Đường migrate xuống: để test lên/xuống của U0 (`design.md:711`), chưa có ở task này.
- Thứ tự `validate` trước `_validate_mandatory`: đạt theo GREEN sau merge (ca "tên mẫu không được để trống").
- Chuyển team-leader: mục deferred về `site_api._values_refusal` (nghi cùng lỗ không phân biệt dấu trên đường công cụ, STD-SEC-4) cần có chủ trước U7.
