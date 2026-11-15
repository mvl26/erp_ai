# FEAT-007 — Phán thiết kế đợt 0, bản sửa 4 (hai điểm bảo mật)

Người viết: designer. Ngày: 2026-11-15. Loại: phán thiết kế, chỉ tài liệu. Gate: không áp dụng (G2b tắt).
Nguồn câu hỏi: `review-37.md:74` (điểm 3), `review-38.md:32`, `:59` (điểm 5).
Văn bản bị sửa chữ: luật K-4 của `design-w0-fixes-3.md:164` (điểm 3); `design.md:492` và `design.md:308` (điểm 5). Designer không sửa `design.md`, `tasks.md`; tech-lead chép các thay chữ dưới đây khi lập task.

Mã đã đọc (chỉ đọc, worktree `feat-007`): `erp_ai/agent/redact.py:28-82` (`_KEY_CANDIDATE`, `_KEY_VALUE`, `_mask_key_values`), `erp_ai/agent/knowledge.py:62`, `:84-86` (`_excerpt` che trước rồi cắt), `erp_ai/agent/test_redact.py:138-224`, `erp_ai/agent/tools/source.py:100-148` (`_base_resolve`, `manuals_root`, `resolve_manual_path`, `resolve_safe_path`), `erp_ai/agent/tools/change_guard.py:138-175` (`check_write_path`), tên test `erp_ai/agent/tools/test_source.py:2327-2430` (`TestManualsExcluded`), `erp_ai/agent/tools/test_change_guard.py:75` (`TestCheckWritePath`).

---

## Điểm 3 — Giá trị trần K-4 dừng ở `&` (NFR-6)

### Hiện trạng
`redact.py:34`: nhánh trần `(?P<bare>[^\s,;&"'}\]]+)` dừng ở bất kỳ `, ; &`. Hệ quả:
- `password=ab&cd` → `password=[đã che]&cd` (lộ `cd`) ở **mọi** kênh (nhật ký, kết quả tool, Error Log, email), không riêng CSKT.
- Trình soạn HD Article lưu `&` thành `&amp;`; `knowledge.py:62` chỉ `strip_html`, không giải thực thể, nên `ab&amp;cd` → `[đã che]&amp;cd`. Dù có giải thực thể, chỗ hở vẫn còn (`ab&cd` ở trên); và `;` của `&amp;` cũng là dấu dừng.
- Lý do `& , ;` là dấu dừng (giữ lại): chuỗi truy vấn URL `?token=abc&page=2` và danh sách `api_key=x, pwd=y` / `a=1; pwd=y` phải tách thành nhiều cặp (`test_redact.py:138-143`).

### Phán
**Sửa ở `redact.py`, luật K-4, một chỗ duy nhất; không vá ở `knowledge.py` hay nơi gọi nào khác** (ADR-034 QĐ 2: một hàm che dùng chung; sửa ở nơi gọi sẽ để hở các kênh còn lại).

Thay `design-w0-fixes-3.md:164` (K-4) bằng:

> - **K-4.** Giá trị: `"…"` (không chứa `"`), `'…'` (không chứa `'`), hoặc giá trị trần. Giá trị trần bắt đầu bằng một ký tự không phải khoảng trắng và không thuộc `, ; & " ' } ]`, rồi kéo dài qua mọi ký tự không phải khoảng trắng và không thuộc `" ' } ]`, **trừ** dấu phân cách danh sách `,` `;` `&`: một dấu phân cách **kết thúc** giá trị khi ngay sau nó là (a) hết văn bản, (b) một khoảng trắng, hoặc (c) đầu một ứng viên khóa theo K-1..K-3 (`[\w-]+` tối đa 3 cụm cách một dấu cách, tùy chọn nháy, khoảng trắng tùy ý, `:` hoặc `=`); trường hợp khác dấu phân cách là **một phần** của giá trị. Không có giá trị (`"api_key= , pwd=x"` ở `api_key`) → không che ứng viên đó.
> - **K-4a (giới hạn đã chấp nhận).** Mật khẩu trần chứa `&x=`/`;x:`/`,x=` (dấu phân cách theo sau là dạng khóa), chứa khoảng trắng, hoặc chứa `" ' } ]` vẫn lộ phần sau chỗ dừng. Mật khẩu trong nháy không bị giới hạn này. Thêm vào As-Built.
> - **K-8 (bổ sung).** Phép nhìn trước (c) đọc tối đa phần cụm ngay sau dấu phân cách; phần đó hoặc thuộc giá trị, hoặc là ứng viên kế tiếp được quét ngay, nên mỗi ký tự vẫn bị đọc một số lần có chặn trên hằng. Cụm trong phép nhìn trước dùng cùng dạng possessive `(?=(?P<x>…))(?P=x)` (Python 3.10, `test_every_pattern_is_python_310_syntax`).

Thêm vào mục 3a (nơi gọi): `knowledge.py` **không** giải thực thể HTML (`html.unescape` hay tương đương) trước `redact_secrets`. Giải thực thể sẽ biến `&quot;` thành `"` (dấu dừng không điều kiện) và mở lại chỗ hở. Câu hỏi thực thể hiện thô trong trích đoạn (điểm nhỏ đã hoãn của `review-37.md:73`) giữ nguyên trạng hoãn; muốn giải thực thể phải có phán thiết kế mới, kèm test của điểm này.

Lần theo: `password=ab&cd` → `[đã che]`; `password=ab&amp;cd` → sau `&` là `amp;` (sau cụm là `;`, không phải `:`/`=`) → tiếp; sau `;` là `cd` rồi hết → tiếp → cả `ab&amp;cd` bị che; `token=abc&page=2` → sau `&` là `page=` → dừng → `token=[đã che]&page=2`; `api_key=fake-a, Bearer …` → sau `,` là khoảng trắng → dừng (giữ `test_several_secrets_in_one_text`); `password=abc;` → hết văn bản → `password=[đã che];`; `api_key=x;pwd=y` → sau `;` là `pwd=` → dừng → hai giá trị đều che.

### Cơ sở
- NFR-6 (`spec.md:149`): mật khẩu giả xuất hiện 0 lần trong kết quả tool, bài nháp, nhật ký, email; một phần mật khẩu lộ là vi phạm.
- AC-46 (trích đoạn CSKT qua `redact_secrets`, `design.md:490`), AC-50 (Error Log).
- ADR-034 QĐ 2 (một hàm che dùng chung) → nơi sửa là `redact.py`.
- STD-SEC-6.

### Touchpoints
- Sửa: `erp_ai/agent/redact.py` (`_KEY_VALUE` nhánh trần; có thể cần đổi `_mask_key_values` nếu phép nhìn trước không viết gọn trong một biểu thức; chữ ký `redact_secrets`, `is_secret_key`, `SECRET_PATTERNS` không đổi).
- Sửa test: `erp_ai/agent/test_redact.py`, `erp_ai/agent/test_knowledge.py`.
- Không file mới; không đổi `knowledge.py`.

### Test phải thêm (đỏ trước)
- `erp_ai/agent/test_redact.py::TestRedact::test_list_separator_inside_bare_value_masked` — đỏ hôm nay: `password=ab&cd` → `password=[đã che]`; `password=ab&amp;cd` → `password=[đã che]`; `pwd=ab;cd` → `pwd=[đã che]`; `pwd=ab,cd` → `pwd=[đã che]`; `password=ab&cd tiếp` → `password=[đã che] tiếp`.
- `erp_ai/agent/test_redact.py::TestRedact::test_list_separator_before_next_key_ends_value` — biên, phải xanh trước và sau (khóa hành vi URL/danh sách): `token=abc&page=2` → `token=[đã che]&page=2`; `api_key=x;pwd=y` → `api_key=[đã che];pwd=[đã che]`; `password=abc;` → `password=[đã che];`; `password=abc, tiếp` → `password=[đã che], tiếp`; `api_key= , pwd=x` → `api_key= , pwd=[đã che]`.
- `erp_ai/agent/test_knowledge.py::TestSearchKb::test_excerpt_password_with_ampersand_masked` — đỏ hôm nay: bài `Published` có nội dung `<p>mật khẩu: fakepw&amp;tailFAKE</p>` cùng một từ tìm; kết quả: `tailFAKE` và `fakepw` xuất hiện 0 lần trong `excerpt`, có `[đã che]`.
- Các test hiện có của `test_redact.py` (đặc biệt `test_several_secrets_in_one_text`, `test_usage_counters_not_masked`, `test_key_value_rules`, `test_secret_key_without_value_untouched`) phải xanh không đổi khẳng định (STD-TEST-5).

### Loại việc
**Task mới** (sửa mã `redact.py` + test). Phụ thuộc: T35 (đã merge). Nên làm trước U6b và trước T56.

---

## Điểm 5 — `change_guard` vẫn tạo được file mới trong kho HDSD

### Hiện trạng
- `source.py:137-147`: `resolve_safe_path` trả `None` chỉ khi đích là **file có sẵn** nằm trong `manuals_root()`. Đường dẫn chưa tồn tại trong kho phân giải bình thường.
- `change_guard.py:150-151`: `check_write_path` dùng `resolve_safe_path` làm bộ phân giải duy nhất. Sửa một file HDSD có sẵn → `PATH_INVALID`; tạo file mới `<kho>/x.md` (`new_file=True`) → qua mọi chốt đường dẫn.
- Hệ quả: bot sửa mã đề xuất được một file HDSD mới; sau khi áp, tool HDSD (AC-47, U6b) trả nội dung đó cho người dùng như hướng dẫn chính thức, không qua người duyệt.
- Ràng buộc phải giữ: `design.md:308` (E-7) kiểm giá trị `manuals_dir` mới bằng `resolve_safe_path` và cần thư mục có sẵn trong kho cũ vẫn phân giải (đổi kho sang một thư mục con); test `test_source.py::TestManualsExcluded::test_manuals_subdirectory_resolves_but_its_files_do_not` khóa điều đó.

### Phán
**File mới trong kho HDSD phải bị từ chối như file có sẵn. Chốt đặt ở `source.resolve_safe_path`, không ở `change_guard`** — giữ một bộ phân giải duy nhất cho đọc và ghi (docstring `check_write_path`; ADR-034 QĐ 5 "dùng lại bộ chặn đường dẫn của `source.py`"). `change_guard.py` không đổi mã; lần từ chối đi theo nhánh sẵn có `full is None` → `PATH_INVALID` (`change_guard.py:170-171`), cùng mã với file có sẵn — không đổi hợp đồng, không mã lỗi mới.

Thay chữ `resolve_safe_path` trong `design.md:492` bằng:

> `resolve_safe_path(rel)` = `_base_resolve` và trả `None` khi đích nằm **hẳn trong** `manuals_root()` và **không phải thư mục có sẵn** — tức file có sẵn, hoặc đường dẫn chưa tồn tại (file mới mà bot sửa mã định tạo, kể cả trong thư mục con chưa có); chính `manuals_root()` và thư mục con có sẵn của nó vẫn phân giải (E-7, `design.md:308`). Phép so dùng đường dẫn thật (`realpath`), nên symlink trỏ vào kho cũng bị chặn.

Thay câu ngoặc cuối `design.md:308` bằng: "(U6a chặn file và đường dẫn chưa tồn tại trong kho ở `resolve_safe_path`, thư mục có sẵn vẫn phân giải, nên kiểm thư mục này không bị chặn bởi chính giá trị đã lưu.)"

Hệ quả phía đọc: `read_source`/`git_source` với một đường dẫn chưa tồn tại trong kho nay trả lời từ chối đường dẫn sẵn có thay vì "không tìm thấy" — chấp nhận, đúng câu cuối AC-47.

Rủi ro còn lại, không phán ở đây: `manuals_dir` đã lưu nhưng thư mục bị xóa khỏi đĩa → `manuals_root()` = `None` → không loại gì. Bot muốn đặt file vào đó phải tạo thư mục; tech-lead kiểm khi lập task xem job áp của `change_guard` có tự tạo thư mục cha không; nếu có → chuyển architect (mở rộng ADR-034 QĐ 5 sang đường dẫn đã cấu hình chưa tồn tại).

### Cơ sở
- ADR-034 QĐ 5: kho HDSD bị loại khỏi đường dẫn mã nguồn; tool HDSD riêng dùng lại bộ chặn của `source.py` → một bộ chặn, nằm ở `source.py`.
- AC-47 (câu cuối: thư mục kho bị loại khỏi `read_source`/`search_source`).
- ADR-034 QĐ 6 / AC-45 (nội dung bot gửi người dùng qua người duyệt — bài CSKT chỉ ở `Draft`): kho HDSD không có trạng thái nháp, nên bot không được ghi vào đó.
- `design.md:308` E-7 → thư mục có sẵn vẫn phân giải.

### Touchpoints
- Sửa: `erp_ai/agent/tools/source.py` (`resolve_safe_path`; chữ ký không đổi).
- Sửa test: `erp_ai/agent/tools/test_source.py`, `erp_ai/agent/tools/test_change_guard.py`.
- Không đổi: `erp_ai/agent/tools/change_guard.py`, `erp_ai/agent/knowledge.py`, `resolve_manual_path`, `manuals_root`. Không file mới.

### Test phải thêm (đỏ trước)
- `erp_ai/agent/tools/test_source.py::TestManualsExcluded::test_new_path_inside_manuals_refused` — đỏ hôm nay: `resolve_safe_path("<kho>/moi.md")` và `resolve_safe_path("<kho>/con-chua-co/moi.md")` (cả hai chưa tồn tại) → `None`; biên: `resolve_safe_path("<app ngoài kho>/moi.md")` chưa tồn tại → vẫn trả đường dẫn.
- `erp_ai/agent/tools/test_source.py::TestManualsExcluded::test_new_path_via_symlink_into_manuals_refused` — đỏ hôm nay: symlink thư mục ngoài kho trỏ vào kho, `"<symlink>/moi.md"` chưa tồn tại → `None`.
- `erp_ai/agent/tools/test_change_guard.py::TestCheckWritePath::test_new_file_in_manuals_refused` — đỏ hôm nay: kho đặt trong một app thuộc `allowed_apps`; `check_write_path("<kho>/moi.md", allowed_apps, new_file=True)` → `PATH_INVALID`; cùng lời gọi cho file có sẵn trong kho (`new_file=False`) → `PATH_INVALID` (khóa cả hai); file mới cùng app, ngoài kho → không bị từ chối vì đường dẫn.
- Các test hiện có phải xanh không đổi khẳng định (STD-TEST-5): `TestManualsExcluded::test_manuals_directory_itself_still_resolves`, `::test_manuals_subdirectory_resolves_but_its_files_do_not`, `::test_empty_manuals_dir_excludes_nothing`, `::test_missing_or_unsafe_manuals_dir_has_no_root`, `::test_resolve_manual_path_only_inside`, và test E-7 của `check_manuals_dir`.

### Loại việc
**Task mới** (sửa mã `source.py` + test) và **sửa chữ** `design.md:492`, `:308`. Phụ thuộc: T38 (đã merge). Nên làm trước U6b và trước T56. Độc lập với task của điểm 3 (khác file).

---

## Tóm tắt cho team-leader

| Điểm | Phán | Nơi | Loại việc | Cơ sở |
|---|---|---|---|---|
| 3 | `, ; &` chỉ kết thúc giá trị trần khi theo sau là hết văn bản, khoảng trắng hoặc một khóa | `redact.py` (K-4) | task mới | NFR-6, AC-46, AC-50, ADR-034 QĐ 2 |
| 5 | Đường dẫn chưa tồn tại trong kho HDSD bị từ chối như file có sẵn; thư mục có sẵn vẫn phân giải | `source.resolve_safe_path` | task mới + sửa chữ `design.md:492`, `:308` | ADR-034 QĐ 5, QĐ 6, AC-47, AC-45, E-7 |

Câu hỏi nghiệp vụ: 0. Giả định kỹ thuật đã quyết: 2 (giữ `PATH_INVALID`, không mã mới; không giải thực thể HTML trước khi che).
