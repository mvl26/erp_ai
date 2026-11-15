Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Không có cổng (G2b tắt). Phán quyết thiết kế cho ba điểm hoãn từ review T36, T16, T37 của đợt 0. -->

# FEAT-007 — Sửa thiết kế sau đợt 0, lần 5 (3 điểm)

Phạm vi: ba điểm thiết kế mà reviewer của T36, T16, T37 để lại cho designer; U5a và U6b xây trên chúng. Tài liệu này **không** sửa `design.md` hay `design-addendum-1-U6b.md`; team-leader/tech-lead chép phần "chữ thiết kế" vào đó và nhận các dòng "task mới" vào kế hoạch. Mã đọc ở worktree `feat-007` @ `7d10d0f`. Không quy tắc nghiệp vụ nào được quyết ở đây; không đổi ADR.

| Điểm | Phán quyết ngắn | Loại |
|---|---|---|
| 1 | Chữ `design.md:487` theo mã (`frappe.qb`); luật ADR-005/034 bắt mọi `frappe.qb` trong `tools/` | task mới (nhỏ) + chữ |
| 2 | Phép kiểm chặt của mã thắng; U5a đọc người nhận = các dòng khác rỗng đã `strip`, không phân tích thêm | chữ (U5a nhận như dòng Receives) |
| 4 | 8 từ chỉ áp cho **câu tìm**; chữ phiếu (phía tài liệu) lấy mọi từ, không giới hạn | task mới (nhỏ, U6a) + chữ U6b |

## Điểm 1 — `frappe.qb` thay `frappe.get_all` cho Error Log (`design.md:487`); luật kiến trúc ADR-034

### Phán quyết
1. **Chữ thiết kế:** `design.md:487` đổi `frappe.get_all("Error Log", ...)` thành: "`frappe.qb` trên `Error Log` (chọn `name, creation, method, error`; `creation` giảm dần, phụ `name` giảm dần), LIKE có escape `\`, `%`, `_` trên `method` hoặc `error`". Mã đã merge (`system_read.py:46-60`) là chuẩn; không đổi mã.
2. **Luật kiến trúc:** có, phải bắt dạng query builder. Luật mở rộng thành: trong `erp_ai/agent/tools/**` **mọi** tham chiếu `frappe.qb` (gồm `frappe.qb.DocType(...)`, `frappe.qb.from_(...)`, `frappe.qb.get_query(...)`) và `from frappe.query_builder import ...` là vi phạm — không chỉ khi tên là `"Error Log"`.
3. Không cần architect: đây là cài đặt ràng buộc đã có (ADR-005, ADR-034), không đổi quyết định nào.

### Căn cứ
- AC-50 ("LIKE có escape") thắng chữ `frappe.get_all`: `get_all` nhân đôi `\` hai lần và không thêm được `ESCAPE` (review-36 dòng 24-25), nên hai yêu cầu của dòng 487 không cùng đúng.
- ADR-034 Ràng buộc dòng 35: "Phép đọc Error Log là đường bỏ quyền duy nhất của nhóm tool mới, nằm ngoài `tools/`". `frappe.qb` không kiểm quyền (review-36 dòng 26) nên là đường bỏ quyền ngang `get_all`; grep chỉ theo `frappe.get_all("Error Log"` bỏ lọt dạng này.
- ADR-005 Ràng buộc dòng 28 (tool không bỏ quyền) và luật hiện có `check_tools_never_bypass_permissions` (`test_architecture.py:632-666`) đã cấm mọi `get_all` trong `tools/` trừ `get_all("DocType")`; `qb` là cùng loại truy vấn không kiểm quyền nên cấm toàn bộ là nhất quán. Hiện không file nào trong `erp_ai/agent/tools/` dùng `qb` (grep 2026-11-15: 0 file) → luật mở rộng không làm đỏ mã có sẵn.
- Phạm vi chỉ `tools/`: `system_read.py` nằm ngoài `tools/` (ADR-021 QĐ 4) nên vẫn hợp lệ.

### Touchpoints
- `docs/team/features/FEAT-007/design.md` dòng 487 (chữ).
- `erp_ai/tests/test_architecture.py` — `check_tools_never_bypass_permissions` (`:632-666`): thêm nhánh vi phạm khi `dotted_name(node)` của một `ast.Attribute`/`ast.Call` bắt đầu bằng `frappe.qb`, và khi `ast.ImportFrom.module` bắt đầu bằng `frappe.query_builder`; docstring nêu ADR-005 + ADR-034.

### Test thêm (đỏ trước)
- `erp_ai/tests/test_architecture.py::test_tools_never_bypass_permissions_flags_query_builder` — nguồn giả `erp_ai/agent/tools/x.py`: (a) `t = frappe.qb.DocType("Error Log")`, (b) `frappe.qb.from_("HD Ticket").select("*").run()`, (c) `from frappe.query_builder import DocType` → mỗi dạng ≥ 1 vi phạm. Đỏ với luật hiện tại (0 vi phạm).
- `erp_ai/tests/test_architecture.py::test_query_builder_outside_tools_allowed` — nguồn (a) đặt ở `erp_ai/agent/system_read.py` → 0 vi phạm (biên phạm vi).
- Test luật trên mã thật hiện có phải còn xanh.

### Loại
**Task mới** (một task nhỏ: luật kiến trúc + 2 test) **và** sửa chữ `design.md:487`.

## Điểm 2 — E-8: một email mỗi dòng (`erp_ai_setting.py:280`) so với `design.md:309`

### Phán quyết
1. **Mã thắng.** Mỗi dòng khác rỗng của `coo_report_recipients` phải là **đúng một địa chỉ email trần**: không dấu phẩy, không dạng `"Tên <email>"`; `validate_email_address(line, throw=False)` phải trả lại chính dòng đó. Dòng trống bị bỏ qua. Không đổi mã.
2. **Chữ thiết kế `design.md:309`** đổi thành: "mỗi dòng khác rỗng (đã `strip`) của `coo_report_recipients` phải là đúng một email trần — `validate_email_address(line, throw=False) == line` và không có `,`; dạng `"Tên <email>"` hay danh sách phẩy bị từ chối → `"Người nhận báo cáo COO: '{x}' không phải email hợp lệ"` (`{x}` qua `escape_html`)".
3. **U5a đọc trường theo đúng luật đó:** `recipients` = các dòng của `coo_report_recipients` sau `strip`, bỏ dòng trống, giữ thứ tự, bỏ trùng; **không** tách phẩy, không bóc `<...>`. Lý do phải `strip`: giá trị lưu giữ nguyên khoảng trắng người gõ (test hiện có lưu `"  ke.toan@congty.vn  "` nguyên văn). Dùng lại hàm tách dòng của `erp_ai_setting.py` (`_filled_lines`, `:293-295`) thay vì viết lại (STD-DESIGN-4): task U5a đổi tên nó thành `filled_lines` (công khai) và import ở `daily_report`; rỗng → bước 4 của `design.md:433`.
4. Thêm vào `design.md:433` bước 4: "Người nhận = `filled_lines(coo_report_recipients)` bỏ trùng; rỗng → ...".

### Căn cứ
- `design.md:138` (bảng trường: "Small Text (mỗi dòng một email)") và `design.md:177` (mô tả: "Mỗi dòng một email nhận báo cáo 08:00 hằng ngày") đã nói một email mỗi dòng; dòng 309 chỉ chưa nói `validate_email_address` trả về phần địa chỉ khi gặp `"Tên <email>"` (docstring `erp_ai_setting.py:276-277`). Phép kiểm chặt là cách duy nhất để chữ ở dòng 138/177 đúng.
- AC-51, AC-52 (báo cáo 08:00 tới người nhận cấu hình; người nhận rỗng → chỉ log): không cần tên hiển thị; `frappe.sendmail(recipients, ...)` nhận list địa chỉ trần (`design.md:435`).
- Review-16 dòng 46: tech-lead đề nghị U5a (T51–T54) đọc theo cách chặt.
- Đây là phép kiểm định dạng, không phải quy tắc nghiệp vụ mới: không đổi ai nhận báo cáo.

### Touchpoints
- `docs/team/features/FEAT-007/design.md` dòng 309, 433 (chữ).
- (thuộc task U5a đã có, không phải task mới) `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (`_filled_lines` → `filled_lines`, sửa 3 chỗ gọi trong file) và module báo cáo 08:00 của U5a (`daily_report`, đường dẫn theo `design.md` mục U5a).

### Test thêm (đỏ trước)
- Phía lưu cấu hình: đã có — `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_bad_email_blocked` (gồm `"Giám đốc <coo@example.com>"`, dòng trống, khoảng trắng). Không thêm.
- Phía U5a: `erp_ai/agent/test_daily_report.py::TestRun::test_recipients_trimmed_blank_and_duplicate_dropped` — gieo `"coo@example.com\n\n  ke.toan@congty.vn  \ncoo@example.com\n"` (ghi bằng `db.set_single_value` để qua mặt validate), patch `frappe.sendmail` → nhận đúng `["coo@example.com", "ke.toan@congty.vn"]`. Cùng chỗ với `::test_no_recipients_logs_only` của `design.md:677`; dòng chỉ có khoảng trắng → coi là rỗng (biên của AC-52).

### Loại
**Chữ** (`design.md:309`, `:433`); phần mã đi vào task U5a sẵn có như một dòng Receives, không cần task mới.

## Điểm 4 — giới hạn từ của `tokenize` khi U6b gọi trên chữ phiếu

### Phán quyết
1. **Giới hạn 8 từ (`QUERY_MAX_WORDS`, D-12) chỉ áp cho câu tìm.** Phía tài liệu (bài CSKT, mục HDSD, chữ phiếu cũ) lấy **mọi** từ, không giới hạn — đúng như `search_kb_articles` đang làm (`knowledge.py:63` gọi `_words`, không phải `tokenize`).
2. `design-addendum-1-U6b.md:300` sai khi gọi `tokenize(subject + description + resolution_details)`: sẽ chỉ so 8 từ đầu của phiếu, bỏ sót phiếu khớp ở cuối mô tả. Chữ đúng: "Điểm = số từ khác nhau của câu tìm có mặt trong `knowledge.text_words(f"{subject} {plain_text(description)} {plain_text(resolution_details)}")`" — nối bằng một dấu cách (nối `+` trần dính từ cuối trường này với từ đầu trường sau).
3. U6a công khai hai hàm dùng chung trong `erp_ai/agent/knowledge.py` (không đổi hành vi):
   - `text_words(text) -> set[str]`: NFC + `casefold`, `\w+` ≥ 2 ký tự, **không** giới hạn số từ (tên công khai của `_words`, trả set).
   - `plain_text(html) -> str`: đúng phép ở `knowledge.py:62` (chèn dấu cách trước thẻ khối `_BLOCK_TAG`, rồi `strip_html`), để từ ở hai khối HTML liền nhau không dính.
   `tokenize` giữ nguyên (8 từ, cho câu tìm); `search_kb_articles` dùng hai hàm mới thay mã tại chỗ. U6b dùng `tokenize(query)` (dòng 299 đúng) và `text_words` + `plain_text` (dòng 300).
4. Không thêm trần số ký tự cho chữ phiếu: khối lượng đã bị chặn bởi `SEARCH_SCAN_MAX` dòng; phép tách từ là tuyến tính.

### Căn cứ
- D-12 (`design.md:70`): "tối đa 8 từ" là giới hạn của **câu tìm** (giảm số mệnh đề LIKE `or_filters`, mỗi từ 2–3 mệnh đề); ADR-034 QĐ 4 "xếp theo số từ khớp" đòi so với toàn bộ chữ tài liệu.
- AC-48 (tìm phiếu cũ đã giải quyết, xếp theo khớp; test `test_read.py::TestSearchResolvedTickets::test_ranked_b...` ở `design-addendum-1-U6b.md:447`) và AC-46 (tìm CSKT) dùng cùng cách tính điểm; nếu chỉ lấy 8 từ đầu của phiếu thì một phiếu chứa từ khóa ở câu thứ hai bị điểm 0 và bị bỏ.
- STD-DESIGN-4: dùng lại `_words` và phép tách khối HTML đã có thay vì U6b viết lại.
- Review-37 dòng 35, 75.

### Touchpoints
- `erp_ai/agent/knowledge.py` (U6a, đã merge): thêm `text_words`, `plain_text`; `search_kb_articles` gọi chúng (dòng 62-65).
- `erp_ai/agent/test_knowledge.py` (thêm test).
- `docs/team/features/FEAT-007/design-addendum-1-U6b.md` dòng 300 (chữ); `design.md:489` thêm hai chữ ký mới dưới `tokenize`.
- `erp_ai/agent/tools/read.py` — `search_resolved_tickets` (task U6b đã có, dùng chữ mới).

### Test thêm (đỏ trước)
- `erp_ai/agent/test_knowledge.py::test_text_words_not_capped` — chữ 20 từ phân biệt → `text_words` trả 20 từ; `tokenize` trên cùng chữ vẫn 8 (biên D-12). Đỏ vì `text_words` chưa có.
- `erp_ai/agent/test_knowledge.py::test_plain_text_keeps_block_words_apart` — `"<p>một</p><p>hai</p>"` → `text_words(plain_text(...)) == {"một", "hai"}`; thẻ inline `"<b>ha</b>i"` không tách từ (giữ hành vi `knowledge.py:23-29`).
- `erp_ai/agent/tools/test_read.py::TestSearchResolvedTickets::test_match_beyond_eighth_word_found` — phiếu đã giải quyết có từ khóa là từ thứ 30 của `description` → có trong kết quả. Đỏ với chữ hiện tại của dòng 300.
- `erp_ai/agent/tools/test_read.py::TestSearchResolvedTickets::test_words_of_adjacent_fields_not_joined` — `subject` kết thúc "máy", `description` bắt đầu "in" → câu tìm "máyin" không khớp.
- Test hiện có của `search_kb_articles` (`test_knowledge.py`) phải còn xanh (thay mã tại chỗ, không đổi hành vi).

### Loại
**Task mới** (nhỏ, trên U6a: `text_words`, `plain_text` + 2 test, đặt trước task `search_resolved_tickets` của U6b) **và** chữ `design-addendum-1-U6b.md:300`, `design.md:489`; hai test `test_read.py` gắn vào task U6b sẵn có.

## Explore / đối chiếu
- Không gọi Explore: các đọc đều là file đã biết (Read/grep theo dòng được giao). Đọc: review-36:20-46, review-16:40-51, review-37:35,75, `design.md:70,138,177,305-312,429-435,480-491`, `design-addendum-1-U6b.md:292-300,444-447`, ADR-034, ADR-005:28; mã `system_read.py:30-60`, `erp_ai_setting.py:262-296`, `test_erp_ai_setting.py:1825-1853`, `knowledge.py:14-93`, `test_architecture.py:137,632-666`.
- Touchpoints mới: không có file mới (mọi test thêm vào file đã có); 0 chạm `protected_paths`.
