Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 62 — FEAT-004 T62

- Diff: `team/FEAT-004-task-62` (head 337ccd8), so với 5130c88 (head của T61), 1 commit, 2 file
- Diff sửa ghép: `git diff ab802fe..81b7186` (nhánh `team/FEAT-004-task-62-fix`, 1 commit, chỉ `test_site_api.py` +32/−6; merge `c9abee1`)
- Vòng: 1 (+ 1 lần sửa sau merge, review riêng: approve)
- Verdict: approve

## Sửa sau merge (2026-11-14) — approve

Tech-lead chép từ tin trả về của reviewer. Merge T62 (`8a2a5ef`) lên nền đã có T61 vòng 2–4 làm đỏ `test_site_api`: `Ran 60 tests in 46.013s` / `FAILED (failures=4)` (`test_get_value_on_an_ordinary_field_still_goes_through`, 3 subTest của `test_star_outside_a_column_selector_still_goes_through`; hai test đối chứng của T61 so nguyên dict, thiếu `value_before`/`value_after`). Lỗi do ghép: T62 cắt từ T61 vòng 1.

- Sửa: giá trị kỳ vọng thêm `value_before=None`, `value_after={"method", "argument_keys"}` viết tay, `argument_keys` theo thứ tự `sorted(arguments)` (`site_api.py:404`); vẫn so bằng nguyên dict, giữ `assert_called_once`. Đổi vì hợp đồng đổi theo T62 (STD-TEST-5), không nới test.
- Bằng chứng của dev: RED `Ran 60 tests in 47.094s` / `FAILED (failures=4)`; GREEN `Ran 60 tests in 46.641s` / `OK`. Tech-lead chạy lại sau merge `c9abee1`: `Ran 60 tests in 46.005s` / `OK`.
- Phát hiện: không có. minor | — | — | 1 điểm nhỏ: chú thích "T62 contract" lặp hai chỗ (`test_site_api.py:1088,1141`) | tùy dev
- Phán của tech-lead về mục "bảng con" bên dưới (suspected): không tái hiện, không DocType lõi nào được nêu; không chặn tick. Ghi vào rủi ro còn lại cho As-Built và cho designer: `value_before` khi xóa có thể mang trường kiểu Data tên `api_key`/`api_secret` nằm trong bảng con.

Lệnh đã dùng (chỉ đọc):
```
git log --oneline 5130c88..team/FEAT-004-task-62
git diff --stat 5130c88..team/FEAT-004-task-62
git diff 5130c88..team/FEAT-004-task-62 -- erp_ai/agent/tools/site_api.py
git diff 5130c88..team/FEAT-004-task-62 -- erp_ai/agent/tools/test_site_api.py
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T62'
git show team/FEAT-004:docs/team/features/FEAT-004/plan.md | grep -n -A30 'Chèn CHG-001'
git show team/FEAT-004:docs/team/features/FEAT-004/spec.md | grep -n -E 'AC-35|S-7'
git log -1 --format='%an%n%B' 337ccd8
git grep -n -E '"ok": True, "doctype"' 337ccd8 -- 'erp_ai/**/*.py'
```

Lớp 1 (khớp spec): đạt. Năm công cụ ghi đều trả `value_before`/`value_after` khi `ok=true`: tạo (trước `None`), xóa (sau `None`, ≤ 20 trường có giá trị), submit/hủy (`docstatus`), `api_call_method` (`None` / `{"method", "argument_keys"}` đúng plan). Bỏ trường mật/`Password`/hệ thống qua `_is_secret` và `SYSTEM_FIELDS` sẵn có; cắt 200 ký tự. Kết quả từ chối/lỗi không mang hai khóa. Không có phần thừa, không file ngoài touchpoint.

Test trước code: mỗi công cụ ghi có test so dict chính xác với bản ghi đọc lại từ DB (tạo: `test_create_returns_the_saved_values_and_no_before`; sửa: `test_updates_note_in_place` + `test_update_reads_the_saved_value_back_from_the_document` (validate đổi giá trị → giá trị sau đọc từ doc); xóa: `row ⊆ value_before`; submit/hủy: stub `db_set` rồi so DB; gọi hàm: dict chính xác). `test_before_after_never_carry_secret_fields` gieo `new_password`, `api_secret` giả, gỡ trần 20 trường để chỉ bộ lọc mật giữ chúng ngoài, đếm = (0, 0); dev dán kết quả đột biến `(1, 1) != (0, 0)`. Test sẽ đỏ nếu bỏ hành vi. RED/GREEN có trong gói.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major | — |

minor | — | — | 4 điểm nhỏ: (1) STD-TEST-2 site_api.py update_record `save()` (~:251-255): sửa trả mọi trường được ghi (kể cả trường không đổi, vd Webhook `{"enabled": 0}` → `{"enabled": 0}`) trong khi task ghi "chỉ trường bị đổi"; cách hiểu "trường được ghi" có ích cho kiểm toán (thấy model định bật webhook) — tech-lead xác nhận cách hiểu; (2) STD-TEST-8 test_site_api.py `test_before_after_never_carry_secret_fields`: hai trường gieo đều vừa thuộc `SECRET_FIELDS` vừa có kiểu `Password`, nên bỏ riêng nhánh `fieldtype == "Password"` của `_is_secret` vẫn xanh trên đường này; (3) STD-STYLE-4 site_api.py `_shown_value` (~:169): giá trị date/datetime/Decimal qua `json.dumps(default=str)` thành chuỗi có dấu nháy (`'"2026-11-14"'`), khác cách biểu diễn của chuỗi thường; (4) STD-TEST-2 `_deleted_values` coi `0` là "có giá trị" (vd `notify_on_login: 0`), nên 20 trường của bản ghi lớn có thể bị các cờ 0 chiếm chỗ | tùy dev

## Review checklist (10)
1. Đúng và đủ tiêu chí AC-35/NFR-5/NFR-11 của T62, không thừa (STD-DESIGN-5, STD-TEST-2): đạt (minor 1, 4).
2. Chỉ 2 file touchpoint, không file mới (STD-DESIGN-1, STD-STRUCT-1/2): đạt.
3. RED trước (55 test, failures=8, errors=6), có test lỗi/từ chối không mang khóa, trần 20, cắt 200, không skip/xfail (STD-TEST-1/8/4): đạt (minor 2).
4. Assertion cũ đổi theo hợp đồng mới (thêm khóa), không theo hành vi sai; test độc lập, dữ liệu tự gieo (STD-TEST-5/6): đạt.
5. Lỗi vẫn đi qua `_write` (savepoint, rollback, ánh xạ PermissionError/ValidationError); `get_doc` trước `delete_doc` vẫn ra "không tìm thấy bản ghi" (test có) (STD-ERR-1/2/5): đạt.
6. Không bí mật; bộ lọc mật/`Password` trên mọi đường; `call_method` chỉ trả tên khóa đối số, `_scrub` giữ nguyên; tạo/sửa không thể ghi trường mật vì `_values_refusal` chặn từ trước (STD-SEC-1/3/4/6): đạt.
7. Hợp đồng kết quả công cụ chỉ thêm khóa (tương thích); không migration (STD-DESIGN-3, STD-OPS-2): đạt.
8. Tên hằng `VALUE_MAX`, `DELETED_FIELDS_MAX`, hàm `_shown`, `_deleted_values` theo kiểu file; docstring `_write` đã cập nhật; không code chết (STD-NAME-1/2, STD-STYLE-4/5): đạt (minor 3).
9. Không phụ thuộc mới (STD-DEP-1/3/5): đạt.
10. Nhánh `team/FEAT-004-task-62`, commit `feat(site_api): … (FEAT-004)` một task một commit, không dòng AI attribution; mô tả công cụ cho model thuộc T63 (STD-NAME-4/5, STD-GIT-1, STD-DOC-2): đạt.

## Không kiểm được từ diff
- Bảng con: `_shown_value` json hóa cả dòng bảng con; `_is_secret` chỉ xét trường cấp cha. Một DocType cha có bảng con chứa trường tên `api_key`/`api_secret` (kiểu Data) sẽ lộ giá trị ở `value_before` khi xóa. Trường `Password` của bảng con thường đã thành `*****` trong DB, nhưng chưa kiểm. → tech-lead quyết có cần lọc đệ quy (suspected).
- `test_agent_runner.py:1237` còn stub kết quả `api_delete_record` không có hai khóa mới; việc ghi `value_before`/`value_after` vào mục hành động của nhật ký thuộc T64.
- Không chạy test (site dùng chung); dựa vào RED/GREEN và kết quả đột biến dev dán.

## Deferred
- Không có.
