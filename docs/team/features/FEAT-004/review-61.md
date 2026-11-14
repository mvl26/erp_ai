Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 61 — FEAT-004 T61

- Diff: `team/FEAT-004-task-61` (head 5130c88), base 7b55147 (head T60, review riêng)
- Diff vòng 2: `5130c88..team/FEAT-004-task-61` (head 1b36a51)
- Vòng: 2
- Verdict: request-changes (vòng 1: request-changes; vòng 2: request-changes)

Lệnh đã chạy (chỉ đọc):
```
git log --oneline 7b55147..team/FEAT-004-task-61
git diff --stat 7b55147..team/FEAT-004-task-61
git diff 7b55147..team/FEAT-004-task-61
git show 5130c88:erp_ai/agent/tools/site_api.py
git show team/FEAT-004:docs/team/features/FEAT-004/{tasks.md,review-chg001.md,spec.md,plan.md}
git show team/FEAT-004:docs/team/adr/ADR-023.md ; git show team/FEAT-004:docs/team/features/CHG-001/arch-impact.md
```
Đọc thêm một chỗ ngoài diff (rủi ro: kết quả không có khóa): `apps/frappe/frappe/client.py:126-179` (`get_value`), `oauth_bearer_token.json` (`access_token` là Data), `user.json` (`api_key` là Data, permlevel 1).

1 commit, 2 file (`site_api.py` +62/−4, `test_site_api.py` +67). Không chạy test (theo lệnh tech-lead: site dùng chung).

## Lớp 1 — khớp spec
- T61 Returns: `SECRET_METHODS` có đủ ba hàm bắt buộc (thêm `get_backup_encryption_key`, `oauth2.get_token`); luật đoạn tên cuối `password`/`generate_keys`/`secret` so casefold; `_scrub` đệ quy theo `SECRET_RESULT_KEYS` đúng tập đã định; so tên DocType casefold sau `json.loads` đệ quy. Bốn test ở Expect có đủ, đúng tên.
- Touchpoints: đúng hai file. Không thêm phạm vi.
- Thiếu: quyết định của người 2026-11-14 và AC-33/NFR-5 đòi `api_call_method` **không bao giờ** trả khóa API hay mật khẩu. `_scrub` chỉ nhận giá trị nằm dưới một khóa có tên bí mật; kết quả không có khóa thì lọt (phát hiện 1). Cơ chế này là cơ chế T61 Returns đã ghi, dev làm đúng chữ của task; chỗ hở nằm ở hình dạng kết quả, sửa được trong touchpoints, nên là request-changes, không phải design-defect. Tech-lead cần bổ sung dòng Returns của T61 cho phép kiểm thêm ở tham số.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-SEC-4 | erp_ai/agent/tools/site_api.py:280-292,325 | `_scrub` chỉ thay giá trị theo tên khóa, nên kết quả không có khóa đi thẳng tới model. `frappe.client.get_value` với `as_dict=0` trả giá trị trần (`frappe/client.py:173-179`): `{"doctype": "User", "fieldname": "api_key", "filters": "<user>", "as_dict": 0}` trả chuỗi khóa API; `{"doctype": "OAuth Bearer Token", "fieldname": "access_token", "as_dict": 0}` trả token bearer dùng được (Data, lưu rõ). `frappe.client.get_list(..., as_dict=0)` (hàng là tuple) và bí danh trường `"api_key as k"` cũng lọt. Tên hàm (`get_value`, `get_list`) không chứa từ cấm, tham số không nhắc DocType của app, nên không lớp nào chặn. Trái AC-33 "trường mật khẩu và khóa API của người dùng" và quyết định "không bao giờ trả khóa API hay mật khẩu". Mô tả tool (dòng 509-510) nói "giá trị khóa và mật khẩu trong kết quả được ẩn", nói quá so với mã. | Trong `_method_refusal`, từ chối trước khi gọi khi văn bản tham số đã `_parsed` + casefold chứa tên trong `SECRET_RESULT_KEYS` (cùng cách kiểm tên DocType, lý do riêng). Thêm test: `get_value` User `api_key` `as_dict=0` và `get_list` OAuth Bearer Token `access_token` dạng bí danh → `ok=False`, `frappe.call` 0 lần. Sửa câu mô tả tool cho khớp. confirmed (đọc mã frappe, chưa chạy) |

minor | STD-ERR-1, STD-TEST-8 | site_api.py:266-275,280-292 | 3 điểm nhỏ: `json.loads`/`_parsed`/`_scrub` đệ quy không giới hạn, chuỗi JSON lồng rất sâu ném `RecursionError` (không phải `ValueError`) ra ngoài `_method_refusal`; ba hàm đầu của `SECRET_METHODS` trùng với luật đoạn tên cuối, bỏ khỏi tập thì test vẫn xanh (che nhau, hành vi không đổi); chưa có test cho phạm vi "chỉ đoạn tên cuối" (đường module chứa `password` mà tên hàm không chứa thì không bị chặn) | tùy dev

## Đối chiếu review-chg001 nhóm G
- blocker STD-SEC-4 `site_api.py:213-219` — **ADDRESSED** cho các đường đã nêu: chuỗi `doc` lồng có `S` và tên chữ thường bị từ chối ở `site_api.py:301-303` (`_parsed` + casefold), test `test_site_api.py:796-807`; `generate_keys`, `get_password` bị từ chối trước khi gọi ở `site_api.py:299-300`, test `test_site_api.py:765-779`. Ranh giới thật của DocType app vẫn là M5 (T65–T67), không thuộc diff này. Đường lộ khóa qua kết quả không có khóa là phát hiện mới (phát hiện 1).
- major STD-TEST-2, phần AC-33 — **ADDRESSED** cho `api_call_method`: hàm quyết định với chữ ký hợp lệ bị từ chối, 0 lời gọi (`test_site_api.py:810-822`; xanh từ trước, phủ nhánh tiền tố `erp_ai.` đã có); mật khẩu/khóa API ở chế độ Toàn quyền (`test_site_api.py:765-794`). Các nhánh khác của major đó (đổi tên, Webhook) không thuộc T61.

## Đánh giá test (test trước mã)
- `test_secret_returning_methods_are_refused_before_call`: so nguyên dict lý do và `frappe.call` 0 lần; bỏ `_is_secret_method` thì `get_backup_encryption_key`, `oauth2.get_token` đi tới `frappe.call` đã patch → đỏ; `Generate_Keys_For` phủ casefold. Không phải test luôn xanh.
- `test_result_secrets_are_scrubbed`: bỏ `_scrub` → đỏ; phủ chữ hoa (`API_KEY`, `Access_Token`), list, tuple. Chỉ phủ hình dạng có khóa (xem phát hiện 1).
- `test_nested_json_doc_naming_app_doctype_is_refused`: ca 1 cần cả parse lẫn casefold, ca 3 cần casefold, ca 2 cần đệ quy; kiểm "không được phép" để không nhầm với lý do "không phải hàm whitelist". Khớp RED của dev.
- RED/GREEN của dev: 3 đỏ đúng ba hành vi mới; xanh 50 + 133. Test thứ tư xanh từ trước, đã ghi rõ.

## Review checklist (10)
1. Đúng và đủ spec/criteria — trượt (STD-SEC-4, STD-TEST-2: phát hiện 1).
2. Touchpoints — đạt (hai file đúng task).
3. Test đỏ trước, phủ biên — đạt một phần: có RED; biên kết quả không khóa chưa phủ (phát hiện 1); không skip/xfail.
4. Không sửa test cho khớp hành vi sai; test độc lập — đạt (chỉ thêm test, `frappe.call` patch trong từng vòng).
5. Lỗi, kiểm đầu vào — đạt với minor `RecursionError`.
6. Bí mật, tiêm, phân quyền, lộ dữ liệu — trượt (STD-SEC-4: phát hiện 1). Hằng `FAKE_SECRET` là giá trị giả, không phải bí mật.
7. Hợp đồng — đạt: kết quả đổi tuple → list và giá trị bị ẩn, không có bên gọi nào khác ngoài model.
8. Tên, cấu trúc, không mã chết — đạt.
9. Phụ thuộc mới — không có.
10. Commit, nhánh, tài liệu — đạt: một commit `fix(site_api): ... (FEAT-004)`, nhánh `team/FEAT-004-task-61`; mô tả tool sửa cùng diff (nhưng nói quá, xem phát hiện 1).

## Không kiểm được từ diff
- Hàm whitelist trả về đối tượng `Document` (không phải dict): `_scrub` để nguyên; registry tuần tự hóa nó thế nào (có qua `as_dict()` và lộ `api_key` không) nằm ngoài diff → tech-lead kiểm `registry.execute_tool`.
- Registry có bắt `RecursionError` từ `_method_refusal`/`_scrub` thành `ok=false` hay để sập lần chạy → tech-lead kiểm.
- Lint (`pre-commit run --all-files`) cho dòng mô tả dài ở `site_api.py:509` — chưa chạy.
- Test chưa chạy lại (theo lệnh): đề nghị `cmd.test_one erp_ai/agent/tools/test_site_api.py`.

## Deferred
- Không có (vòng 1).

## Vòng 2 (2026-11-14)
- Diff sửa: `5130c88..team/FEAT-004-task-61` (head 1b36a51), 1 commit `fix(site_api): refuse call_method arguments that name a key or password field (FEAT-004)`, 2 file (`site_api.py` +12/−2, `test_site_api.py` +33). Chỉ xét diff sửa.
- Verdict: **request-changes**

Lệnh đã chạy (chỉ đọc):
```
git log --oneline 5130c88..team/FEAT-004-task-61
git diff --stat 5130c88..team/FEAT-004-task-61
git diff 5130c88..team/FEAT-004-task-61
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A6 '^- \[ \] T61'
git show team/FEAT-004-task-61:erp_ai/agent/tools/site_api.py   # dòng 30-60, vị trí hàm
git -C apps/frappe show HEAD:frappe/model/db_query.py           # dòng 1000-1060 (version-15)
git -C apps/frappe show HEAD:frappe/client.py                   # get_list
```
Rủi ro ngoài diff đã đọc một chỗ: cách Frappe mở rộng `fields=["*"]` (`frappe/model/db_query.py:1047-1050`: `*` được thay bằng toàn bộ trường đọc được, gồm trường permlevel 1 khi tài khoản đọc được) và `frappe.client.get_list` (`as_dict=0` → `as_list`). Không chạy test (theo lệnh tech-lead).

### Đối chiếu phát hiện vòng 1
- major | STD-SEC-4 | site_api.py:280-292,325 — **NOT ADDRESSED (một phần)**.
  - Đã đóng: tên trường bí mật trong tham số bị từ chối trước khi gọi ở `site_api.py:311-312` (`IDENTIFIER_PATTERN` tách `\w+` trên văn bản đã `_parsed` + casefold, nên `api_key as k`, `` `tabUser`.`API_KEY` `` trong chuỗi JSON lồng, `tabUser.reset_password_key`, `["Access_Token"]` đều ra tên trần). Test `test_site_api.py:802-823` phủ 6 ca (`get_value` `as_dict=0`, bí danh, backtick, chuỗi JSON lồng, tiền tố bảng, chữ hoa), so nguyên dict lý do và `frappe.call` 0 lần; RED của dev 6 failures đúng 6 ca. Test đối chứng `test_site_api.py:825-832` chặn việc chặn quá tay với trường thường. Mô tả tool `site_api.py:519-520` và docstring `site_api.py:300-303` nay nói đúng "chặn ở mức cố gắng", không còn nói quá.
  - Còn hở: chọn cột bằng `*` không nhắc tên trường nào. `frappe.client.get_list` với `{"doctype": "User", "fields": ["*"], "as_dict": 0}` → Frappe thay `*` bằng mọi trường đọc được (`db_query.py:1047-1050`), trả hàng dạng list không khóa: `api_key`, `reset_password_key` của mọi người dùng đi thẳng tới model, `_scrub` không có khóa để ẩn. Tương tự `{"doctype": "OAuth Bearer Token", "fields": ["*"], "as_dict": 0}` trả `access_token`, `refresh_token` (permlevel 0), và `frappe.desk.reportview.get` (kết quả `keys`/`values` dạng vị trí) với `fields: ["*"]`. Đây đúng đường "get_list với `as_dict=0` (hàng là tuple)" phát hiện vòng 1 đã nêu, nên chưa đóng. Trái quyết định của người 2026-11-14 "không bao giờ trả khóa API hay mật khẩu" và AC-33.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-SEC-4 | erp_ai/agent/tools/site_api.py:311-312 | Chặn theo tên trường bỏ sót chọn cột `*`: `frappe.client.get_list` `{"doctype": "User", "fields": ["*"], "as_dict": 0}` (và OAuth Bearer Token, `frappe.desk.reportview.get` với `fields: ["*"]`) trả giá trị `api_key`/`access_token` trần, không khóa, `_scrub` không ẩn được. Còn lại của phát hiện vòng 1. | Trong `_method_refusal`, từ chối thêm khi một chuỗi lá của tham số đã `_parsed` là bộ chọn cột `*` (`*`, `tabX.*`, `` `tabX`.* ``, có thể kèm khoảng trắng; `count(*)` có thể cho qua). Thêm ca vào test (hoặc test riêng): `get_list` User `fields ["*"]` `as_dict 0`, `fields "*"` dạng chuỗi, `` ["`tabOAuth Bearer Token`.*"] ``, `frappe.desk.reportview.get` `fields ["*"]` → `ok=False`, `frappe.call` 0 lần. confirmed (đọc mã Frappe version-15, chưa chạy; quyền đọc permlevel 1 của tài khoản agent giả định như vòng 1) |

### Review checklist (10) — diff sửa
1. Đúng và đủ spec/criteria — trượt một phần: dòng "Sửa theo review-61 vòng 1" của T61 làm đủ (tên, casefold, JSON lồng, bí danh, test `as_dict=0`, mô tả tool); "không bao giờ trả khóa" vẫn hở qua `*` (major trên). Không thêm phạm vi.
2. Touchpoints — đạt (đúng hai file của task).
3. Test đỏ trước, phủ biên — đạt một phần: RED 6 failures trước mã; biên bí danh/backtick/chuỗi lồng/chữ hoa và ca đối chứng có; biên `*` chưa phủ. Không skip/xfail.
4. Không sửa test cho khớp hành vi sai; test độc lập — đạt: chỉ thêm test, `frappe.call` patch trong từng `subTest`, lý do viết cứng `SECRET_ARGUMENT_REFUSED`.
5. Lỗi, kiểm đầu vào — đạt: không thêm nhánh lỗi mới; regex trên văn bản đã có sẵn.
6. Bí mật, tiêm, phân quyền, lộ dữ liệu — trượt (STD-SEC-4, major trên).
7. Hợp đồng — đạt: thêm một lý do từ chối mới cho `api_call_method`; bên gọi duy nhất là model.
8. Tên, cấu trúc, không mã chết — đạt (`IDENTIFIER_PATTERN`, `SECRET_ARGUMENT_REASON` theo `naming.constant`, chú thích đúng việc mã làm).
9. Phụ thuộc mới — không có (`re` thư viện chuẩn).
10. Commit, nhánh, tài liệu — đạt: một commit `fix(site_api): ... (FEAT-004)` trên `team/FEAT-004-task-61`; mô tả tool và docstring sửa cùng diff, khớp mã.

minor | — | — | 1 điểm nhỏ: chặn theo từ `token`/`secret`/`password` ở mọi chỗ trong tham số (cả giá trị, ví dụ nội dung ticket "khách quên password" gửi qua `frappe.client.insert`) sẽ từ chối cả lời gọi vô hại; chấp nhận được với quyết định "chặn ở mức cố gắng", nên ghi trong mô tả tool để model biết lý do | tùy dev

### Không kiểm được từ diff
- Vai trò thật của tài khoản agent ở chế độ Toàn quyền (có đọc permlevel 1 của User không) quyết định `api_key` có nằm trong `*` hay không; `access_token` của OAuth Bearer Token là permlevel 0 nên lọt bất kể → tech-lead kiểm.
- Lint (`pre-commit run --all-files`) cho dòng mô tả dài `site_api.py:519-520` — chưa chạy.
- Test chưa chạy lại (theo lệnh): đề nghị `cmd.test_one erp_ai/agent/tools/test_site_api.py`.

### Deferred (vòng 2)
- Mục minor ở vòng 1 (`RecursionError` ở `_parsed`/`_scrub`, `SECRET_METHODS` che nhau với luật đoạn tên cuối, chưa test phạm vi "chỉ đoạn tên cuối") không thuộc diff sửa; giữ nguyên, không chặn vòng này.
