# FEAT-007 — Sửa thiết kế đợt 0, lần 7 (vòng build 8)

Người viết: designer · Ngày: 2026-11-15 · Phạm vi: chỉ tài liệu. Văn bản này thắng chữ của `design.md` và `tasks.md` ở đúng các chỗ được nêu. Nó không đổi kiến trúc (ADR-006, ADR-024, ADR-033 giữ nguyên).

Nguồn đã đọc: `review-19.md:85-107`, `review-21.md:25-32, 50-54`, `review-18.md:63-68`, `tasks.md:250-264`, `design.md:286-331, 61, 150-151, 637-639`, `spec.md:178, 204`. Mã chỉ đọc (worktree `feat-007`): `erp_ai_prompt_revision.json`, `erp_ai_setting.js`, `erp_ai_setting.json` (trường `agent_enabled_at`), `test_erp_ai_setting.py:2241-2324`, `install.py:100-112`, `tests/test_install.py:51, 690-708`, `tests/test_doctype_descriptions.py:10, 31, 520-551`. Frappe 15.126.1: `form/formatters.js:18-51, 256-273, 346-348`, `form/controls/base_input.js:139-154`, `form/grid_row.js:731, 1085, 1151, 1507-1517`, `form/controls/code.js:1-38`, `database/mariadb/database.py:184-185`. pymysql: `converters.py:117-125`.

---

## Điểm 1 — Hiển thị `old_value` an toàn; test của T20 không phụ thuộc site

### Xác minh (đọc mã Frappe; chưa xem trên màn hình)

- Ô read-only trong form của dòng bảng con được vẽ qua `set_disp_area` → `frappe.format(...)` → `$(disp_area).html(display_value)` (`base_input.js:139-154`). Với Long Text, `frappe.format` gọi `formatters.Text` → `formatters.Data` (`formatters.js:256-273, 36-51`). Cả hai hàm đều không escape. Nếu không có thẻ `<p`, `<div`, `<br`, `<table`, hàm chỉ đổi `\n` thành `<br>`. Cột lưới cũng dùng `frappe.format` rồi gọi `.html(txt)` (`grid_row.js:1507-1517`). `old_value` không có `in_list_view`, nhưng người dùng tự thêm được cột này qua "Configure Columns" (`grid_row.js:604`). **Kết luận:** nghi ngờ của reviewer là đúng ở cả hai chỗ hiển thị: form của dòng và cột lưới.
- `formatters.Code` trả về `"<pre>" + $("<div>").text(value).html() + "</pre>"` (`formatters.js:346-348`). Hàm này escape mọi ký tự HTML và giữ nguyên khoảng trắng và dòng mới. Ô Code ở chế độ read-only còn có nút sao chép giá trị thô (`code.js:12-37`). Trong MariaDB, `Code` và `Long Text` cùng có kiểu cột `longtext` (`database.py:184-185`).

### Phán quyết 1a — Cách hiển thị và nơi xử lý

- Đổi `old_value` của DocType `ERP AI Prompt Revision` từ `Long Text` sang **`Code`**. Giữ `read_only: 1`, `ignore_xss_filter: 1`, nhãn và mô tả như cũ. Không đặt `options`, không thêm `in_list_view`. Chỉ đổi `modified` của tệp JSON.
- Việc escape thuộc về **lớp hiển thị của Frappe**. Desk tự escape ở cả form của dòng lẫn cột lưới. Giá trị lưu trong DB vẫn là bản thô, đúng nguyên văn: AC-38 cần đúng "giá trị cũ", và test `test_prompt_revision_keeps_old_value_verbatim` ghim điều này.
- **Không** viết formatter riêng trong `erp_ai_setting.js` (`frappe.meta.docfield_map[...].formatter`). Lý do: hàm `_apply_custom_formatter` nhận giá trị **sau khi** `formatters.Text` đã chèn `<br>` (`formatters.js:256-273` chạy trước `:26-33`). Muốn escape ở đó phải đoán lại đâu là `<br>` do Frappe thêm, nên dễ sai. Cách đổi kiểu trường lại không cần mã JS (STD-DESIGN-4, STD-DESIGN-5).
- `erp_ai_setting.js` giữ đúng phạm vi T20 cũ: đặt `cannot_add_rows` và `cannot_delete_rows` cho `prompt_revisions` (`design.md:329`).
- **Lên/xuống (STD-OPS-2):** kiểu cột vẫn là `longtext`, nên `cmd.migrate` không đổi cột và không chuyển dữ liệu. Muốn lùi phiên bản thì trả JSON về `Long Text`; dữ liệu giữ nguyên. Không cần đối soát.
- Bản in: ERP AI Setting là Single, chỉ System Manager đọc được (`review-19.md:88`). Bản in không thuộc phạm vi AC-38 và lần này không phán.

### Phán quyết 1b — Test của T20 không phụ thuộc giá trị ghi đè đã lưu trên site (STD-TEST-6)

- `TestPromptOverrides.setUp` làm việc này **trước** lần `_save(...)` đang có:
  1. Ghi rỗng ba ô ghi đè thẳng vào DB bằng `frappe.db.set_single_value(SETTING_DOCTYPE, <fieldname>, "")`. Cách này không qua controller nên không sinh dòng lịch sử.
  2. Xóa các dòng lịch sử trong DB bằng `frappe.db.delete(PROMPT_REVISION_DOCTYPE, {"parent": SETTING_DOCTYPE, "parentfield": "prompt_revisions"})`.
  3. Sau `_save(...)`, khẳng định số dòng `prompt_revisions` trong DB bằng 0. Nếu việc dọn chưa đủ, test đỏ ngay ở `setUp`.

  `addCleanup(frappe.db.rollback)` đang có sẽ trả lại dữ liệu thật của site.
- Mọi test lịch sử so **toàn bộ danh sách dòng**, không so phần chênh số dòng.
- `test_prompt_revision_keeps_old_value_verbatim` (T19) **phải viết lại phần dựng dữ liệu**. Hiện test `append` một dòng rồi `save`. Sau T20, bước 1 của `validate` thay `prompt_revisions` bằng các dòng đang có trong DB (`design.md:291`), nên dòng vừa `append` bị bỏ và `stored == []` sẽ đỏ. Cách dựng mới đi đúng đường hệ thống:
  - ghi `prompts.CLASSIFY_PROMPT` vào DB bằng `set_single_value`;
  - lưu form với giá trị khác (`prompts.CLASSIFY_PROMPT + "\n<img src=x onerror=alert(1)> & x"`);
  - khẳng định `old_value` của dòng duy nhất bằng đúng `prompts.CLASSIFY_PROMPT`.

  Điều được khẳng định không đổi: giá trị lưu nguyên văn, kể cả `<` và `&`. Vì vậy việc sửa không trái STD-TEST-5, chỉ đổi cách dựng dữ liệu cho hợp với ranh giới T20 đưa vào.
- Một dòng trong `test_prompt_section_and_child_doctype_shape` (`test_erp_ai_setting.py:2299`) đổi từ `("old_value", "Long Text", None, 1)` sang `("old_value", "Code", None, 1)`. Thiết kế đổi theo phán quyết 1a, nên việc sửa test là hợp lệ (STD-TEST-5).

### Chữ `design.md:291` (từ `review-21.md:30`)

- Yêu cầu của bước 1 là "đọc giá trị trong DB, không qua cache". Đọc bằng `frappe.db.get_single_value(..., cache=False)` hay bằng `get_singles_dict` (cách đang làm ở `erp_ai_setting.py:180`) đều đạt. T20 **không** viết lại phần khôi phục ba mốc đã có; T20 chỉ thêm bước khôi phục `prompt_revisions`.

### Căn cứ

- AC-38 (`spec.md:204`: "lịch sử (người, thời điểm, giá trị cũ)"; người không sửa được lịch sử); D-3 (`design.md:61`); `design.md:291, 318, 329, 639`.
- STD-SEC-3 (escape dữ liệu ngoài khi xuất ra); STD-TEST-6 (test độc lập); STD-TEST-5; STD-OPS-2; STD-DESIGN-4, STD-DESIGN-5.
- ADR-024, phần Ràng buộc: app không đọc `Version`. Phán quyết này không đụng tới ràng buộc đó.

### Touchpoints (đường thật, đều đã có; không thêm tệp)

- `erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/erp_ai_prompt_revision.json` (**thêm vào `files:` của T20**)
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js`
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`

So với `protected_paths`: không tệp nào thuộc danh sách này. Đây là bốn tệp đã nằm trong touchpoints của T19 hoặc T20 (`tasks.md:254`, `review-19.md` mục "Kết luận").

### Tests (đỏ trước)

| Đỏ trước | Test | Kiểm điều gì |
|---|---|---|
| có: `'Long Text' != 'Code'` | `TestPromptOverrides::test_prompt_revision_old_value_rendered_escaped` (mới) | meta `old_value`: `fieldtype == "Code"`, `read_only == 1`, `ignore_xss_filter == 1`. Ghi chú trong test: Desk escape qua `formatters.js:346-348` |
| có: dòng `Long Text` | `::test_prompt_section_and_child_doctype_shape` | dòng `old_value` đổi sang `"Code"` |
| có: chưa có `record_prompt_revisions` | `::test_revision_row_on_change` | xem khối T20 bên dưới |
| có | `::test_no_revision_without_change` | xem khối T20 bên dưới |
| có | `::test_revisions_restored_on_save` | xem khối T20 bên dưới |
| có, sau khi thêm bước khôi phục: `[] != [old_value]` | `::test_prompt_revision_keeps_old_value_verbatim` (dựng dữ liệu lại) | giá trị cũ lưu nguyên văn qua đường hệ thống |

## Khối task T20 mới

Có thay đổi. Tech-lead chép nguyên văn khối dưới đây, thay cho `tasks.md:254-258`:

```
- [ ] T20 — Lịch sử ghi đè prompt do hệ thống ghi — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js, erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/erp_ai_prompt_revision.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T19
  - Tiêu chí: AC-38 (người sửa, thời điểm, giá trị cũ nguyên văn; không đổi → không dòng; người không sửa được lịch sử), D-3; `design-w0-fixes-7.md` Điểm 1 (thắng `design.md:150-151` về kiểu `old_value`): `old_value` đổi sang `Code` để Desk hiện giá trị đã escape (STD-SEC-3), giá trị lưu vẫn thô; test không phụ thuộc giá trị ghi đè đã lưu trên site (STD-TEST-6). Chữ `design.md:291`: đọc DB không qua cache, cách hiện tại (`get_singles_dict`) đạt; không viết lại phần khôi phục ba mốc.
  - Receives: `prompt_revisions`, `restore_self_managed_fields()` (T18, T19); `PROMPT_PARTS`, `PROMPT_REVISION_DOCTYPE`, `TestPromptOverrides` với `_save`, `_stored` (T19).
  - Returns: `record_prompt_revisions()` (`design.md:318`): với mỗi phần có giá trị khác giá trị trong DB, thêm một dòng `part`, `changed_by = frappe.session.user`, `changed_at = now_datetime()`, `old_value` = giá trị DB nguyên văn ("" khi trước đó rỗng), `new_length` = `len()` của giá trị mới đúng như sẽ lưu (không cắt khoảng trắng). Bước khôi phục `prompt_revisions` từ DB trong `restore_self_managed_fields()`, giữ thứ tự `idx`: người dùng thêm, sửa hay xóa dòng trên doc đều mất tác dụng. `erp_ai_prompt_revision.json`: `old_value` `fieldtype` từ `Long Text` thành `Code`, giữ `read_only` 1 và `ignore_xss_filter` 1, mô tả không đổi, dời `modified`; cột vẫn là `longtext`, `cmd.migrate` không đổi dữ liệu, chạy `cmd.migrate` trước khi chạy test. `erp_ai_setting.js` đặt `cannot_add_rows` và `cannot_delete_rows` cho `prompt_revisions`; không thêm formatter. `TestPromptOverrides.setUp`, trước `_save(...)` đang có: `frappe.db.set_single_value` ghi "" vào ba ô ghi đè, `frappe.db.delete(PROMPT_REVISION_DOCTYPE, {"parent": SETTING_DOCTYPE, "parentfield": "prompt_revisions"})`; sau `_save(...)`, khẳng định trong DB có 0 dòng lịch sử.
  - Expect: `TestPromptOverrides::test_revision_row_on_change` (lưu phần classify = A với A = `prompts.CLASSIFY_PROMPT + "\n<img src=x onerror=alert(1)> & a"`, rồi lưu B ≠ A: đúng 2 dòng theo `idx`; dòng 2 có `part` "classify", `changed_by` là người dùng phiên, `changed_at` khác rỗng, `old_value == A` nguyên văn, `new_length == len(B)`; dòng 1 có `old_value == ""`), `::test_no_revision_without_change` (lưu lại cùng giá trị, và lưu chỉ đổi một trường không phải prompt → danh sách dòng không đổi), `::test_revisions_restored_on_save` (trên doc: `append` một dòng giả, sửa `old_value` của dòng có sẵn, xóa một dòng; sau `save`, danh sách dòng trong DB giống hệt trước lần lưu), `::test_prompt_revision_old_value_rendered_escaped` (meta `old_value`: `fieldtype == "Code"`, `read_only == 1`, `ignore_xss_filter == 1`) xanh; `::test_prompt_revision_keeps_old_value_verbatim` dựng dữ liệu lại qua đường hệ thống (`set_single_value` ghi `prompts.CLASSIFY_PROMPT` vào DB, lưu form với giá trị khác, `old_value` của dòng duy nhất == `prompts.CLASSIFY_PROMPT`) và xanh; `::test_prompt_section_and_child_doctype_shape` đổi dòng `old_value` thành `"Code"` và xanh; các test khác của T19 vẫn xanh, không sửa.
```

---

## Điểm 2 — `agent_enabled_at`: một dạng lưu duy nhất và chữ mô tả

**Loại: task mới.** Cần đổi mã ở `install.py` và chữ ở `erp_ai_setting.json`, kèm test, nên không chỉ là sửa chữ trong tài liệu. Tech-lead đặt số task và thứ tự. Lưu ý: task này dùng chung tệp với T22, T60 và T23 (`install.py`, `test_install.py`). Nó chỉ phụ thuộc T21.

### Xác minh

- Dòng cài đặt `install.py:112` gọi `set_single_value(..., now_datetime())`. Đường ghi này đi qua pypika `isoformat()` nên lưu `2026-11-15T01:28:25.844279`, có chữ `T` (`review-21.md:29`).
- Lần lưu form đi qua `Document.update_single` và pymysql `escape_datetime`. Hàm này lưu `YYYY-MM-DD HH:MM:SS.ffffff`, phân cách bằng dấu cách, và bỏ phần `.ffffff` khi micro giây bằng 0 (`converters.py:117-125`). Đây đúng là `str(datetime)` của Python.

### Phán quyết 2a — Một dạng lưu duy nhất

- Dạng chuẩn là dạng mà lần lưu form của Frappe đang ghi: `str(datetime)`, tức `YYYY-MM-DD HH:MM:SS[.ffffff]` với dấu cách. Đây cũng là dạng mà mọi trường Datetime khác do form ghi đang dùng.
- `install.py:112` ghi `str(frappe.utils.now_datetime())` thay cho đối tượng `datetime`. **Không** dùng `frappe.utils.now()`, vì hàm đó luôn có `.%f` và sẽ khác dạng của form khi micro giây bằng 0.
- Không đổi controller: `stamp_agent_enabled_at` vẫn gán `datetime`, đường form vẫn ghi đúng dạng chuẩn.
- **Dữ liệu đã có dạng `T`:** không viết patch, không đối soát. Lý do:
  - ADR-006 chỉ cho phép điền trường còn thiếu, nên cài đặt không được sửa giá trị đã có;
  - mọi nơi đang đọc trường này đều phân tích được cả hai dạng (`review-21.md:31`);
  - `team/FEAT-007` chưa vào `develop` nên production chưa nhận dạng `T`. Chỉ site dev `miyano` có thể đang có giá trị này.

  Từ nay, mọi nơi đọc mới **phải** đọc qua `get_datetime` hoặc qua `get_single_value(..., cache=False)`, không so chuỗi thô. Điều này đã đúng với T33, T34, T53, T54 theo ADR-033 QĐ 6. Reviewer của các task đó kiểm điểm này.

### Phán quyết 2b — Chữ mô tả (thay nguyên văn `description` của `agent_enabled_at` trong `erp_ai_setting.json`)

> Hệ thống tự ghi thời điểm gần nhất ô Bật agent đổi từ tắt sang bật; site đã bật agent từ trước khi nâng cấp lên bản có trường này thì mốc là thời điểm nâng cấp. Việc quét phiếu bị lỡ chỉ xét phiếu tạo sau mốc này. Lưu khi agent đã bật thì mốc giữ nguyên; không sửa được.

Chữ này có 270 ký tự (đếm bằng `len()` của Python), dưới trần 400 (`test_doctype_descriptions.py:10`), và vẫn chứa hai cụm bắt buộc "Hệ thống tự ghi" và "không sửa được" (`:31`).

### Căn cứ

- AC-16 (`spec.md:178`: chỉ quét phiếu "tạo sau khi agent bật"); ADR-006 (cài đặt chỉ điền trường thiếu); ADR-033 QĐ 6 (mốc bật là giới hạn dưới của việc quét); `design.md:329`.
- STD-DESIGN-3 (một trường, một dạng lưu; `review-21.md:52` điểm (a)); STD-DOC (mô tả đúng với hành vi); STD-TEST-1.

### Touchpoints (đường thật, đều đã có; không thêm tệp; không tệp nào thuộc `protected_paths`)

- `erp_ai/install.py` (dòng 112)
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` (`description` của `agent_enabled_at`, dời `modified`)
- `erp_ai/tests/test_install.py`
- `erp_ai/tests/test_doctype_descriptions.py` (dòng 31)

### Tests (đỏ trước)

| Đỏ trước | Test | Kiểm điều gì |
|---|---|---|
| có: `'2026-01-02T03:04:05' != '2026-01-02 03:04:05'` | `TestFeat007Migrate::test_agent_enabled_at_stored_as_form_save_shape` (mới, `test_install.py`) | bật agent và xóa dòng mốc. `_setup_at("2026-01-02 03:04:05")` → chuỗi **thô** trong `tabSingles` == `"2026-01-02 03:04:05"`. Chạy lại với `"2026-01-02 03:04:05.000123"` → chuỗi thô == `"2026-01-02 03:04:05.000123"`. Cả hai bằng `str(get_datetime(...))` |
| có: thiếu cụm "thời điểm nâng cấp" | `test_doctype_descriptions.py::...::test_required_phrases_present` | dòng 31 thêm cụm `"thời điểm nâng cấp"` vào bộ cụm bắt buộc của `agent_enabled_at` |
| không (vẫn xanh) | `TestFeat007Migrate::test_agent_enabled_at_filled_once_when_enabled`, `::test_agent_enabled_at_null_or_empty_counts_as_missing`, `::test_second_migrate_changes_nothing` | không sửa. Helper `_enabled_at` giữ cách chuẩn hóa hiện có; test mới đọc chuỗi thô riêng |
