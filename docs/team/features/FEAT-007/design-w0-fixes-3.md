Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Phán quyết thiết kế đợt 0, lần 3 — FEAT-007 (T25, T8 `DESIGN_CONFLICT`; hai câu hỏi T35)

## 0. Cách đọc

- File này **thắng** `design.md`, `design-w0-fixes.md` và `design-w0-fixes-2.md` ở mọi chỗ khác nhau. Mỗi phán quyết ghi: dòng bị thay, văn bản thay đầy đủ, task bị đổi (file, tiêu chí, test), test chứng minh. Phần không nhắc ở đây giữ nguyên.
- Không đổi spec, AC, luật nghiệp vụ hay ADR. **Không phán quyết nào cần sửa ADR**: phán quyết 2 làm `TICKET_CONTENT_DOCTYPES` khớp đúng danh sách của ADR-034 QĐ 1, và giữ nguyên luật "không `HD Ticket Comment` trong mã sản phẩm" (FEAT-001 journal D8, ADR-010:75, `test_architecture.py::TestArchitecture::test_no_legacy_ticket_comment_or_spoofable_author`).
- Designer không đánh số task mới, không sửa `tasks.md`/`plan.md`; tech-lead chép các thay đổi dưới đây vào hai file đó.
- Không đường dẫn mới nào. Mọi file được nêu đã có: `erp_ai/agent/policy.py`, `erp_ai/agent/test_policy.py`, `erp_ai/agent/routing.py`, `erp_ai/agent/test_routing.py`, `erp_ai/agent/redact.py`, `erp_ai/agent/test_redact.py`, `erp_ai/constants.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/*` (đều dưới gốc `erp_ai`, thuộc `allowed_new_file_roots` = `['erp_ai', 'docs', '.github']`; không khớp `protected_paths` = `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`).

**Căn cứ đọc trực tiếp (đích đã biết, không qua Explore), 2026-11-14:** `tasks.md` T8, T15, T24, T25, T35 (chữ `BLOCKED:` và `progress`); `journal-part9.md` ba dòng cuối; `design.md:382-391, 486-488, 71, 307`; `design-w0-fixes.md:55, 58, 66, 189, 309`; `design-w0-fixes-2.md:60-84, 121-138`; `review-35.md` từ "Vòng 3" đến hết; `design-addendum-1-U2.md:34, 56, 80, 100-110, 125-138, 145, 153, 192, 279, 293, 329`; `design-addendum-1-U6b.md:52, 178`; `design-addendum-1-U4b-U8.md:33, 245, 434`; `design-addendum-1-U4b-U8-fixes.md:284, 419`; `design-addendum-1-U3.md:69`; `spec.md:189` (AC-27); `spec-addendum-2.md:49` (AC-8, vế ghi có nêu `HD Ticket Comment`); `docs/team/adr/ADR-010.md`, `ADR-034.md` QĐ 1–3; FEAT-001 `design.md:41-46`, journal D8; mã: `erp_ai/tests/test_architecture.py:354-357, 380-397, 845-880, 1945-1949, 2738-2760`; `erp_ai/agent/tools/read.py:26, 141-166`; `erp_ai/agent/tools/site_api.py:26-34, 62`; `erp_ai/agent/policy.py:1-9` (chỉ import `erp_ai.constants`); `team/FEAT-007:erp_ai/agent/routing.py:40-137`; `team/FEAT-007-task-35:erp_ai/agent/redact.py` (@ `b286281`) và `test_redact.py`; Helpdesk `hd_ticket_comment.json` (role Agent đọc được; trường Link `reference_ticket` → HD Ticket).

---

## 1. Phán quyết (1) — T25: `d_watcher` ba trạng thái, `None` = nơi gọi không nói

**Vấn đề.** `design.md:389` thêm ghi chú "chưa cấu hình người theo dõi phiếu D" khi không có `d_watcher`, nên ba nơi gọi cũ (không truyền tham số mới) nhận thêm ghi chú ở mọi phiếu D, trái `design-w0-fixes-2.md:73` ("nhận **đúng** `priority` và `notes` như trước").

**Quyết định.** Không thêm tham số. Cùng mẫu với phán quyết (2) của `design-w0-fixes-2.md` (`due_field_configured is None` = không nói): `d_watcher: str | None = None` giữ chữ ký, nghĩa ba trạng thái phân biệt bằng `is None`, **không** bằng giá trị thật/giả (`if not d_watcher` là sai). Bỏ phương án cờ `d_watcher_configured`: cờ cùng giá trị tạo tổ hợp vô nghĩa (cờ `True`, người `None`). Bỏ phương án nhận ghi chú mới: trái hợp đồng thêm.

**Thay `design.md:389`** bằng:
> - `watcher` (AC-27). `d_watcher` có ba trạng thái, phân biệt bằng `d_watcher is None` và `d_watcher.strip() == ""`:
>
>   | `d_watcher` | đầu mục D | đầu mục khác D |
>   |---|---|---|
>   | `None` (mặc định; nơi gọi không nói: `runner.py:281` hiện có, `write_ticket.py:50`, `run_eval.py:198`) | `watcher = None`; **không** ghi chú | `watcher = None`; không ghi chú |
>   | chuỗi rỗng sau `strip()` (nơi gọi đã đọc cấu hình, `d_ticket_watcher` để trống) | `watcher = None`; thêm `notes` `{"field": "watcher", "reason": D_WATCHER_MISSING_NOTE}`, `D_WATCHER_MISSING_NOTE = "chưa cấu hình người theo dõi phiếu D"` (đây là "1 dòng log" của AC-27) | `watcher = None`; không ghi chú |
>   | chuỗi khác rỗng, `is_active_agent(d_watcher)` đúng | `watcher = d_watcher` | `watcher = None`; không ghi chú; không gọi `is_active_agent` |
>   | chuỗi khác rỗng, `is_active_agent(d_watcher)` sai | `watcher = None`; thêm `notes` `{"field": "watcher", "reason": f"{d_watcher} không phải HD Agent đang hoạt động"}` (cùng chữ với ghi chú `assignee` ở `routing.py:137`) | như trên |
>
>   Ghi chú `watcher` có nhiều nhất một mục mỗi lần gọi. "Đúng một lần" là việc của bên ghi (U4b: `follow_document` chỉ khi chưa có Document Follow).

`design-w0-fixes-2.md:73` (chữ ký `decide_route`) giữ nguyên và nay đúng cả với `d_watcher`.

**Addendum đợt 1 đã duyệt bị đổi chữ (không đổi tên, không đổi kiểu):** `design-addendum-1-U4b-U8.md:245` vế (1): `d_watcher=settings.d_ticket_watcher or None` → `d_watcher=settings.d_ticket_watcher or ""` (runner luôn "nói": cấu hình trống → chuỗi rỗng → ghi chú). `set_classification` (`write_ticket.py:50`) **không** truyền `d_watcher` (nó không thêm người theo dõi), nên không ghi chú; đúng như ý.

**Task bị đổi.**
- **T25** (cùng 2 file `erp_ai/agent/routing.py`, `erp_ai/agent/test_routing.py`; nhánh task rỗng, làm từ đầu): Tiêu chí "AC-27 phần quyết định (`design.md:389`)" → "AC-27 phần quyết định (`design-w0-fixes-3.md` phán quyết 1)". Returns thêm hằng `D_WATCHER_MISSING_NOTE`. Expect như mục test dưới đây (4 test cũ, sửa đầu vào của 2 test, thêm 1 test). Gỡ `BLOCKED:`.
- **U4b** (đợt 1): chữ `:245` như trên; test plan thêm 1 dòng dưới đây.

**Test chứng minh** (`erp_ai/agent/test_routing.py`, T25):
- `TestDWatcher::test_d_configured`: D, `d_watcher="it@x"`, `is_active_agent` đúng → `watcher == "it@x"`; `notes` không có mục `field == "watcher"`.
- `::test_other_category_none`: A, B, C, E, F × `d_watcher` ∈ {`"it@x"`, `""`} → `watcher is None`, không có mục `watcher`; với `"it@x"`, `is_active_agent` không được gọi (đếm bằng hàm giả).
- `::test_d_unconfigured_note` (sửa đầu vào): D × `d_watcher` ∈ {`""`, `"  "`} → `watcher is None`; đúng **một** mục `{"field": "watcher", "reason": "chưa cấu hình người theo dõi phiếu D"}`.
- `::test_inactive_watcher_none` (sửa mong đợi): D, `is_active_agent` sai → `watcher is None`; đúng một mục `{"field": "watcher", "reason": "it@x không phải HD Agent đang hoạt động"}`.
- `::test_old_call_shape_no_watcher_note` (mới): 6 đầu mục, lời gọi kiểu cũ (không truyền tham số mới) → `watcher is None`, `notes` không có mục `field == "watcher"`; với D: kết quả lời gọi kiểu cũ `==` kết quả cùng lời gọi có `d_watcher=None` (so cả `RouteDecision`).
- `TestPriorityExceptions::test_old_call_shape_no_due_note`, `::test_truth_table`, `::test_existing_rules_kept` (T24, đã merge): không sửa, phải xanh.
- U4b (đợt 1): `erp_ai/agent/test_runner_routing.py::TestRunnerHooks::test_d_watcher_unconfigured_logged` (mới): D, `d_ticket_watcher` trống → dòng `classify` có ghi chú `watcher` đúng chữ trên; 0 Document Follow.

---

## 2. Phán quyết (2) — T8: `TICKET_CONTENT_DOCTYPES` = danh sách của ADR-034 QĐ 1; DocType có trường Link tới HD Ticket được nhận ra qua meta

**Vấn đề.** D-13 (`design.md:71`) đặt chuỗi `"HD Ticket Comment"` vào hằng ở `erp_ai/constants.py`; luật kiến trúc (FEAT-001 journal D8) cấm chuỗi đó trong mọi mã sản phẩm, chỉ cho `read.py::COMMENT_HIDDEN_FIELDS`. Nhưng spec vẫn cần phủ DocType đó: AC-8 `[changed]` (`spec-addendum-2.md:49`) nêu nó ở vế ghi, và Helpdesk 15.1.0 vẫn giữ DocType này với dòng cũ đã chép sang `Comment` (FEAT-001 `design.md:43`), role Agent đọc được.

**Quyết định.**
1. **Không** thêm ngoại lệ vào `LEGACY_ALLOWED_ASSIGNMENTS` và không sửa `test_architecture.py`: luật giữ nguyên độ chặt.
2. `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")`, vẫn ở `erp_ai/constants.py` (khối hằng FEAT-007, F-1). Đây đúng là bốn DocType của ADR-034 QĐ 1.
3. DocType ghi chú phiếu cũ (và mọi DocType khác) được phủ bằng **cấu trúc**, không bằng tên: một DocType mang nội dung phiếu khi nó thuộc `TICKET_CONTENT_DOCTYPES` **hoặc** meta của nó có ít nhất một trường `fieldtype == "Link"` với `options == "HD Ticket"` (kể cả Custom Field). Hai hàm mới trong `erp_ai/agent/policy.py` (Lõi, chỉ import `frappe` và `erp_ai.constants` như hiện nay; controller import được, như `hard_bans` ở F-1):
   - `ticket_link_fieldnames(doctype: str) -> tuple[str, ...]`: `doctype == "HD Ticket"` → `()`; DocType không tồn tại (`frappe.db.exists("DocType", doctype)` sai) → `()`, không ném; ngược lại tên mọi trường Link có `options == "HD Ticket"` trong `frappe.get_meta(doctype).fields`, theo thứ tự meta.
   - `is_ticket_content_doctype(doctype: str) -> bool`: `doctype in TICKET_CONTENT_DOCTYPES or bool(ticket_link_fieldnames(doctype))`.
   Hệ quả chủ ý (fail-closed, NFR-1): DocType có Link tới phiếu như `HD Ticket Activity`, hay HD Article có Custom Field `ai_source_ticket` (U6b), cũng được lọc theo phiếu loại trừ và không được làm nguồn báo cáo cho bot. ToDo (Dynamic Link) không bị phủ, đúng A-U2-5.
4. Không chuỗi `"HD Ticket Comment"` hay `"reference_ticket"` nào trong mã sản phẩm của FEAT-007. Tên đó chỉ được viết trong file test (luật quét bỏ qua `tests/` và `test_*`, `test_architecture.py:385-387`).

**Thay `design.md:71`** (D-13) bằng:
> | D-13 | Danh sách DocType "mang nội dung phiếu" (ADR-034 QĐ 1, 3) | `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` (ADR-034 QĐ 1) ∪ mọi DocType có trường Link `options = "HD Ticket"` (`policy.is_ticket_content_doctype`) ∪ `read.denied_doctypes()` ở các chỗ cấm | Luật FEAT-001 D8 cấm tên DocType ghi chú phiếu cũ trong mã sản phẩm; DocType đó có trường Link `reference_ticket` → HD Ticket nên được phủ qua meta. File chứa đính kèm phiếu. |

**Thay `design-w0-fixes.md:55`** (văn bản thay cho `design.md:307`), phần từ "khi `ref_doctype` ∈" đến hết đoạn, bằng:
> khi `policy.is_ticket_content_doctype(ref_doctype)` đúng **hoặc** `ref_doctype ∈ read.denied_doctypes()`. Hằng `TICKET_CONTENT_DOCTYPES` (D-13) đặt trong `erp_ai/constants.py`; hai hàm `ticket_link_fieldnames`, `is_ticket_content_doctype` ở `erp_ai/agent/policy.py`; controller này và tool U6b import từ đó, không tự dò meta.

**Thay `design-w0-fixes.md:66`** bằng: `- TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` (D-13 theo `design-w0-fixes-3.md` phán quyết 2; DocType có Link tới HD Ticket được nhận ra bằng `policy.is_ticket_content_doctype`).

`design-w0-fixes.md:58` và `:189` (tên và chỗ của hằng) giữ nguyên.

**U2 phải đọc gì thay cho tên cũ** (addendum đợt 1 đã duyệt `design-addendum-1-U2.md`; không đổi tên nào, đổi **nội dung** của `TICKET_CONTENT_DOCTYPES`, `TICKET_LINK_FIELDS`, thêm 1 hàm U2):
- `:34` cột cuối → "phủ qua trường Link `options = "HD Ticket"` (`policy.ticket_link_fieldnames`, `design-w0-fixes-3.md` phán quyết 2)".
- `:56` → `| TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File") | Có (D-13 theo design-w0-fixes-3.md phán quyết 2; erp_ai/constants.py) |`; thêm dòng `| policy.ticket_link_fieldnames(doctype) -> tuple[str, ...], policy.is_ticket_content_doctype(doctype) -> bool | Có (T15, đợt 0) |`.
- `:80` cột 2: thay "`HD Ticket Comment.reference_ticket`" bằng "mọi trường Link `options = "HD Ticket"` của DocType khác (`ticket_link_fieldnames`)".
- `:105-110` `TICKET_LINK_FIELDS`: bỏ dòng `"HD Ticket Comment": (None, "reference_ticket"),`; còn đúng 3 khóa `Comment`, `Communication`, `File`. Chú thích trên hằng → `# DocType có liên kết động tới phiếu -> (cột loại tham chiếu, cột tên phiếu); Link tĩnh tới HD Ticket: ticket_link_fieldnames`.
- Thêm hàm U2 trong `policy.py`: `ticket_link_columns(doctype: str) -> tuple[tuple[str | None, str], ...]`: `doctype in TICKET_LINK_FIELDS` → `(TICKET_LINK_FIELDS[doctype],)`; ngược lại `tuple((None, f) for f in ticket_link_fieldnames(doctype))`.
- `:134` `ticket_content_filters` → "`not is_ticket_content_doctype(doctype)` hoặc `excluded_ticket_names()` rỗng → `([], [])`. `HD Ticket` → `([["name", "not in", names]], [])`. Có cột loại (`TICKET_LINK_FIELDS`) → `([], [[type_col, "!=", "HD Ticket"], [name_col, "not in", names]])`. Ngược lại, với mỗi `(None, f)` của `ticket_link_columns(doctype)` → thêm `[f, "not in", names]` vào `filters` (AND: dòng bị loại khi **một** trường Link bất kỳ trỏ tới phiếu loại trừ). Dòng có trường Link rỗng vẫn hiện."
- `:135` `owning_ticket` → "`HD Ticket` → `name`; DocType có `ticket_link_columns` khác rỗng: với cột loại, như cũ; với Link tĩnh, giá trị khác rỗng đầu tiên theo thứ tự meta; DocType khác → `None`". `is_ticket_record_excluded` → "có **một** phiếu được trỏ tới (mọi cột của `ticket_link_columns`) mà `can_send_ticket` sai".
- `:138` giữ chữ ("`TICKET_LINK_FIELDS` phải phủ đúng `set(TICKET_CONTENT_DOCTYPES) − {"HD Ticket"}`"): nay là 3 = 3.
- `:145` "Với `doctype ∈ TICKET_CONTENT_DOCTYPES`, kết quả thêm `excluded_note`" → "Với `policy.is_ticket_content_doctype(doctype)` đúng, kết quả thêm `excluded_note`".
- `:153` và mọi chỗ khác của `:148-154` viết "`doctype ∈ TICKET_LINK_FIELDS`" → "`policy.ticket_link_columns(doctype)` khác rỗng"; "giá trị liên kết trỏ tới phiếu có `can_send_ticket` sai" xét trên **mọi** cột của `ticket_link_columns` có trong `values` (và giá trị hiện có khi sửa).
- `:192` bảng tên: thêm `ticket_link_columns` (U2, `policy.py`); thêm `ticket_link_fieldnames`, `is_ticket_content_doctype` (U0/T15, `policy.py`, U2 và U6b dùng).
- `:279` "5 DocType (`TICKET_CONTENT_DOCTYPES`)" → "4 DocType của `TICKET_CONTENT_DOCTYPES` + DocType ghi chú phiếu cũ của Helpdesk (tên viết thẳng trong file test)"; ma trận còn lại giữ.
- `:293` giữ chữ (đẳng thức vẫn đúng với 4 DocType).
- `:329` A-U2-5 cột "Chọn" → "Phủ 4 DocType của ADR-034 QĐ 1 bằng tên và mọi DocType có trường Link tới HD Ticket bằng meta (gồm DocType ghi chú phiếu cũ, `HD Ticket Activity`); không phủ ToDo".

**Addendum U6b (`design-addendum-1-U6b.md`)**: `:52` giữ (tên, chỗ không đổi); `:178` vế (4) → "`policy.is_ticket_content_doctype(ref_doctype) or ref_doctype in read.denied_doctypes()` (kiểm lại lúc chạy, …)"; lời từ chối giữ nguyên.

**Task bị đổi.**
- **T8** (worktree dev `.claude/worktrees/agent-a9a8bc9cbb9f7ce31` giữ được; cùng `files:`): Returns `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` (thay chữ `plan.md:35`). Expect thêm `TestCatalogRules::test_ticket_content_doctypes_is_adr_034_list` và `test_architecture` xanh. Gỡ `BLOCKED:`. Không thêm `test_architecture.py` vào `files:`.
- **T15**: files thêm `erp_ai/agent/policy.py`, `erp_ai/agent/test_policy.py` (đều có sẵn; trong đợt 0 không task nào khác giữ hai file này, tech-lead ghi vào bảng "Một file, một chủ": T15 trước U1/U2). Tiêu chí thêm "`design-w0-fixes-3.md` phán quyết 2". Receives: `TICKET_CONTENT_DOCTYPES` (T8), `read.denied_doctypes()`, `allowed_reports` (T14). Returns: `check_allowed_reports()`; `policy.ticket_link_fieldnames`, `policy.is_ticket_content_doctype`. Expect thêm hai test dưới đây.
- **U2, U6b** (đợt 1): chữ như trên.

**Test chứng minh.**
- T8: `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestCatalogRules::test_ticket_content_doctypes_is_adr_034_list` (mới): `constants.TICKET_CONTENT_DOCTYPES == ("HD Ticket", "Comment", "Communication", "File")`.
- T8: `erp_ai/tests/test_architecture.py::TestArchitecture::test_no_legacy_ticket_comment_or_spoofable_author` (có sẵn, **không sửa**): xanh trên nhánh T8 (hôm nay đỏ với `constants.py:100: mentions HD Ticket Comment`).
- T15: `erp_ai/agent/test_policy.py::TestTicketContentDoctype::test_constant_and_ticket_links` (mới): `is_ticket_content_doctype` đúng với 4 tên của hằng và với `"HD Ticket Comment"`; `ticket_link_fieldnames("HD Ticket Comment") == ("reference_ticket",)`; `ticket_link_fieldnames("HD Ticket") == ()`; `is_ticket_content_doctype("User")` sai; `"Không có DocType này"` → sai, không ném.
- T15: `test_erp_ai_setting.py::TestAllowedReports::test_report_on_ticket_linked_doctype_blocked` (mới): Report (Query Report, không tắt) có `ref_doctype = "HD Ticket Comment"` trong `allowed_reports` → lưu bị chặn với chữ `"Báo cáo '{r}' dựa trên HD Ticket Comment, mang nội dung phiếu hoặc dữ liệu của app: bot không được chạy"`. Ba test cũ của `TestAllowedReports` giữ, phải xanh.
- U2 (đợt 1): `erp_ai/agent/tools/test_site_api.py::TestExcludedTicketReads::test_list_hides_excluded_rows_in_both_modes` với ma trận mới ở `:279`; thêm `::test_empty_ticket_link_row_still_listed` (mới): dòng DocType ghi chú phiếu cũ có `reference_ticket` rỗng vẫn có trong danh sách.

---

## 3. Phán quyết (3) — T35: đầu ra NFC, nghĩa của `SECRET_PATTERNS`, và luật tên đầy đủ (thay 5a)

Phán quyết này **thay toàn bộ** `design-w0-fixes-2.md` 5a (đoạn thay `design.md:486`) và câu "Chèn 2" trong tiêu chí T35. Mọi hành vi của `redact.py` nằm trong các tiêu chí đánh số N-1..N-7, K-1..K-8, R-1..R-5 dưới đây; **không có luật nào ngoài chúng**. Một dòng mã không truy về được một tiêu chí là finding STD-DESIGN-5.

### 3a. Đầu ra luôn ở dạng NFC

**Quyết định.** `redact_secrets` trả văn bản ở dạng NFC, kể cả khi không che gì. Lý do: thư điện tử và văn bản dán vào phiếu có thể ở NFD; một dạng duy nhất cho log, kết quả tool, email; `policy._title_key` đã dùng NFC; hiển thị không đổi.

Ràng buộc cho nơi gọi (T36, T37, T53, U3, U6b):
- Không dùng `redact_secrets(x) != x` (hay `==`) để biết có che hay không. Hôm nay không dòng thiết kế nào làm vậy.
- Che **trước**, cắt **sau**; độ dài đo trên đầu ra. `design.md:487` (`read_error_logs`): `error` = `redact_secrets(error)[-2000:]`, `method` = `redact_secrets(method)`. `design.md:488` (`search_kb_articles`): `excerpt` lấy từ `redact_secrets(title + strip_html(content))`, không che sau khi cắt. (Cắt trước có thể bỏ mất tên khóa và để lộ giá trị đứng sau.)

### 3b. `SECRET_PATTERNS` = đúng năm mẫu giá trị

**Quyết định.** `SECRET_PATTERNS` là tuple **đúng 5** mẫu, theo thứ tự: `sk-ant-…`, `sk-…` (≥ 16 ký tự sau `sk-`), `Bearer <token>`, `token <key>:<secret>`, JWT `eyJ….….…`. Mỗi đoạn khớp, trừ nhóm có tên `prefix`, **là** giá trị bí mật. Mẫu tìm ứng viên tên khóa không phải mẫu bí mật: nó là tên riêng `_KEY_CANDIDATE`, không nằm trong `SECRET_PATTERNS`, không export. Mã không truy cập `SECRET_PATTERNS` theo chỉ số (`[0]`, `[1:]`). Không addendum đợt 1/2 nào dùng tên `SECRET_PATTERNS` (chỉ `redact_secrets`, `is_secret_key`), nên không addendum nào đổi chữ vì điểm này.

### 3c. Luật tên khóa bí mật — `is_secret_key(name: str) -> bool`

- **N-1.** Chuẩn hóa `name` về NFC.
- **N-2.** Chèn một ranh giới trước ký tự thứ i (i ≥ 1) khi ký tự i là chữ hoa (`str.isupper()`) **và** (a) ký tự i−1 là chữ thường (`islower()`) hoặc chữ số (`isdigit()`), **hoặc** (b) ký tự i−1 là chữ hoa và ký tự i+1 tồn tại và là chữ thường. Vế (b) là **mới** so với 5a (từ viết tắt: `DBPassword` → `DB|Password`, `APIKey` → `API|Key`); theo 5a hai tên này ra `False` và giá trị bị lộ.
- **N-3.** `casefold()`.
- **N-4.** Tách theo `[\s_\-.]+` (khoảng trắng Unicode, `_`, `-`, `.`); bỏ đoạn rỗng. Không ký tự nào khác là dấu tách (`/`, `:`, chữ số không tách).
- **N-5.** `SECRET_WORDS = ("api_key", "api_secret", "token", "secret", "password", "passwd", "pwd", "mật khẩu")`; dãy đoạn của mỗi từ tính bằng N-1..N-4: `(api, key)`, `(api, secret)`, `(token)`, `(secret)`, `(password)`, `(passwd)`, `(pwd)`, `(mật, khẩu)`. Một danh sách, dùng chung cho K-5.
- **N-6.** `True` ⟺ có một từ w và một vị trí s mà `đoạn[s : s + len(w)] == w`: các đoạn của w xuất hiện **liền nhau, đúng thứ tự, khớp nguyên đoạn** (không khớp chuỗi con trong một đoạn).
- **N-7.** Không có luật nào khác: không danh sách ngoại lệ, không số nhiều (`tokens` ≠ `token`), không bỏ dấu (`mat khau` ≠ `mật khẩu`).

| Tên | Kết quả | Tiêu chí quyết định |
|---|---|---|
| `api_key`, `x_api_key`, `api_secret`, `access_token`, `new_password`, `reset_password_key`, `smtp_pwd`, 4 tên của `site_api.SECRET_FIELDS` | True | N-6 |
| `apiKey`, `accessToken`, `clientSecret` | True | N-2a |
| `oauth2Token` | True | N-2a (chữ số trước chữ hoa) |
| `DBPassword`, `APIKey`, `JWTToken` | True | N-2b |
| `api-key`, `smtp.password`, `Secret Key` | True | N-4 (`-`, `.`, khoảng trắng) |
| `Mật khẩu` (NFC và NFD), `MẬT KHẨU` | True | N-1, N-3 |
| `input_tokens`, `output_tokens`, `max_tokens`, `MAX_TOKENS`, `tokenizer`, `passwords` | False | N-6, N-7 (không khớp chuỗi con, không số nhiều) |
| `api_primary_key` | False | N-6 (`api`, `key` không liền nhau) |
| `apikey`, `primary_key`, `subject`, `mat khau` | False | N-4, N-6, N-7 |

### 3d. Luật khóa-giá trị và thứ tự trong `redact_secrets(text: str | None) -> str`

Thứ tự (sửa finding vòng 3 #1 của `review-35.md`):
- **R-1.** `text` là `None` hoặc rỗng → `""`.
- **R-2.** Chuẩn hóa toàn văn về NFC (3a).
- **R-3.** Lần lượt từng mẫu của `SECRET_PATTERNS` theo thứ tự tuple: `pattern.sub` thay đoạn khớp bằng `prefix` (nếu có) + `MASK`.
- **R-4.** Quét khóa-giá trị K-1..K-8 trên kết quả của R-3, một lượt từ trái sang phải.
- **R-5.** Trả kết quả (NFC). `MASK = "[đã che]"`.

Quét khóa-giá trị:
- **K-1.** Ứng viên chỉ bắt đầu ở vị trí mà ký tự đứng trước không thuộc `[\w-]` (hoặc đầu văn bản).
- **K-2.** Tên ứng viên là **tối đa 3** cụm `[\w-]+` cuối cùng của một chuỗi cụm cách nhau đúng một dấu cách U+0020, đứng ngay trước dấu phân cách K-3. (5a cho tối đa 2; nâng lên 3 để che "Mật khẩu mới: …", "password của anh: …".) Ví dụ: `"ghi chú: x"` → tên `"ghi chú"`; `"Mật khẩu mới: x"` → `"Mật khẩu mới"`; `"Mật khẩu đăng nhập mới: x"` → `"đăng nhập mới"` (giới hạn đã chấp nhận: không che).
- **K-3.** Sau tên: tùy chọn một `"` hoặc `'`, khoảng trắng tùy ý, rồi `:` hoặc `=`, rồi khoảng trắng tùy ý.
- **K-4.** Giá trị: `"…"` (không chứa `"`), `'…'` (không chứa `'`), hoặc dãy trần các ký tự không phải khoảng trắng và không thuộc `, ; & " ' } ]`. Không có giá trị (`"api_key= , pwd=x"` ở `api_key`) → không che ứng viên đó.
- **K-5.** Ứng viên là bí mật ⟺ `is_secret_key(tên)`, với tên = các cụm của K-2 nối bằng một dấu cách. **Không** luật bỏ cặp, **không** xét lại một cụm đứng một mình (bỏ nhánh ở `redact.py:51-56` @ `b286281`). Vì dãy đoạn của một cụm nằm liền trong dãy đoạn của cả tên, tên nhiều cụm luôn che ít nhất mọi trường hợp mà một cụm của nó che.
- **K-6.** Bí mật → giữ tên, dấu nháy và dấu phân cách, thay nội dung giá trị bằng `MASK` (`"…"` → `"[đã che]"`, `'…'` → `'[đã che]'`, trần → `[đã che]`), quét tiếp ngay sau giá trị. Không bí mật → giữ nguyên đoạn khớp, quét tiếp ngay sau dấu phân cách.
- **K-7.** Giá trị trần bắt đầu bằng `MASK` (đã che ở R-3) → giữ nguyên, quét tiếp sau `MASK` (không che lần hai thành `[đã che] che]`).
- **K-8.** Công tuyến tính theo độ dài văn bản: cụm là possessive/không lùi, ứng viên chỉ bắt đầu ở đầu cụm (K-1), nên mỗi ký tự được đọc bởi số lần có chặn trên hằng.

Lần theo các khẳng định đã có và finding vòng 3: `"Authorization: token K:S"` → R-3 ra `"Authorization: token [đã che]"`, R-4 không đổi (giữ khẳng định cũ); `"token abc: fake-c"` → R-3 không khớp (sau `:` là dấu cách), K-5 tên `"token abc"` là bí mật → `"token abc: [đã che]"`; `"Secret Key: fake-x"` → `"Secret Key: [đã che]"`; `"password=sk-ant-x…"` → R-3 rồi K-7 → `"password=[đã che]"`; `"pwd password=fake-d"` → `"pwd password=[đã che]"`; `"input_tokens: 1200, output_tokens: 512, api_key=abc"` → chỉ `abc` bị che.

**Thay `design.md:486`** bằng:
> - `erp_ai/agent/redact.py` (mới): `MASK = "[đã che]"`; `SECRET_WORDS` (N-5); `SECRET_PATTERNS` = đúng 5 mẫu giá trị (3b); `redact_secrets(text: str | None) -> str` theo R-1..R-5 và K-1..K-8; `is_secret_key(name: str) -> bool` theo N-1..N-7 (`design-w0-fixes-3.md` mục 3). Đầu ra NFC; nơi gọi che trước rồi cắt (3a). Một hàm dùng chung cho nhật ký, kết quả tool, Error Log, email (ADR-034 QĐ 2); đơn vị sau dùng lại.

**Addendum đợt 1 đã duyệt bị đổi chữ:** `design-addendum-1-U3.md:69` (hành vi cần của `is_secret_key`): "luật đoạn tên của `design-w0-fixes-2.md` 5a" → "luật N-1..N-7 của `design-w0-fixes-3.md` mục 3c". Tên, chữ ký giữ nguyên.

**Task bị đổi.**
- **T35** (nếu team-leader cho vòng 4; FIX_BASE `b286281`; cùng 2 file `erp_ai/agent/redact.py`, `erp_ai/agent/test_redact.py`): Tiêu chí: thay câu "`name.casefold()` chứa…" và đoạn "Chèn 2" bằng "N-1..N-7, K-1..K-8, R-1..R-5, 3a, 3b của `design-w0-fixes-3.md` mục 3; không luật nào ngoài các tiêu chí này". Returns: `MASK`, `SECRET_WORDS`, `SECRET_PATTERNS` (5 mẫu giá trị), `redact_secrets`, `is_secret_key`. Expect như dưới. Mã đổi: bỏ `_KEY_CANDIDATE` khỏi `SECRET_PATTERNS`; bỏ nhánh bỏ cặp; R-3 chạy trước R-4; K-7; tên tối đa 3 cụm (K-2); vế N-2b. Mẫu JWT (`"eyJ-" * 25_000`) giữ ở mục deferred của `review-35.md`, không thuộc phán quyết này.
- **T36, T37**: Expect thêm một test mỗi task (dưới đây) cho ràng buộc "che trước, cắt sau".
- **U3** (đợt 1): chữ `:69` như trên.

**Test chứng minh** (`erp_ai/agent/test_redact.py`, T35):
- `TestRedact::test_is_secret_key_names` (sửa): mọi tên của bảng 3c với đúng kết quả; mỗi dòng là một `subTest` mang tên tiêu chí (N-2a, N-2b, N-4, N-6, N-7). Bắt được đột biến của finding vòng 3 #2: bỏ vế "chữ số" (`oauth2Token`), bỏ `-`/`.` khỏi dấu tách (`api-key`, `smtp.password`), đổi "liền nhau" thành "tập con" (`api_primary_key`).
- `::test_key_value_rules` (mới; thay `::test_secret_word_before_another_run_is_not_the_key`, lý do sửa: thiết kế đổi, STD-TEST-5): `"token abc: fake-c"` → `"token abc: [đã che]"`; `"Secret Key: fake-x"` → `"Secret Key: [đã che]"`; `"password mới: fake-y"` → `"password mới: [đã che]"`; `"Mật khẩu mới: fake-m"` → `"Mật khẩu mới: [đã che]"`; `"Mật khẩu đăng nhập mới: fake-n"` không đổi (giới hạn K-2); `"pwd password=fake-d"` → `"pwd password=[đã che]"`; `"ghi chú: token=fake-a"` → `"ghi chú: token=[đã che]"`.
- `::test_value_patterns_run_before_key_scan` (mới): `"Authorization: token FAKEKEY:FAKESECRET"` → `"Authorization: token [đã che]"`; `"password=sk-ant-FAKE0000"` → `"password=[đã che]"` (không có `che]` thừa); `'api_key: "sk-FAKE0000000000000000"'` → `'api_key: "[đã che]"'`.
- `::test_secret_patterns_are_the_five_value_patterns` (mới): `len(SECRET_PATTERNS) == 5`; mỗi mẫu một mẫu thử của `::test_each_pattern` được đúng một phần tử của `SECRET_PATTERNS` khớp; không phần tử nào khớp `"api_key=abc"`.
- `::test_output_is_nfc` (mới): văn bản NFD không có bí mật (`unicodedata.normalize("NFD", "Mật khẩu đã đổi xong")`) → bằng dạng NFC của nó; `unicodedata.is_normalized("NFC", kết quả)` đúng.
- `::test_long_run_without_secret_untouched` (giữ, thêm `"a " * 50_000 + ": x"` và `"Mật khẩu " * 20_000`): kết quả đúng, giữ biên thời gian hiện có (K-8).
- `::test_each_pattern`, `::test_plain_text_untouched`, `::test_usage_counters_not_masked`, `::test_nfd_vietnamese_key_masked`, `::test_one_word_list_for_both_functions` và các test còn lại: giữ, phải xanh.
- T36: `erp_ai/agent/test_system_read.py::TestReadErrorLogs::test_secret_at_tail_cut_masked` (mới): Error Log có `"api_key=fake-tail"` đặt sao cho 2000 ký tự cuối bắt đầu giữa tên khóa → `fake-tail` không có trong `error`.
- T37: `erp_ai/agent/test_knowledge.py::TestSearchKb::test_excerpt_masked_before_cut` (mới): bài có `"password: fake-kb"` gần từ khớp → `fake-kb` không có trong `excerpt`.

---

## 4. Thay đổi đối với addendum đợt 1/2 đã duyệt

| Addendum : dòng | Đổi gì | Phán quyết | Đổi tên/kiểu? |
|---|---|---|---|
| `design-addendum-1-U4b-U8.md:245` vế (1) | `d_watcher=settings.d_ticket_watcher or ""` (thay `or None`) | 1 | Không |
| `design-addendum-1-U4b-U8-fixes.md:419` (test plan U4b) | thêm `test_runner_routing.py::TestRunnerHooks::test_d_watcher_unconfigured_logged` | 1 | Không |
| `design-addendum-1-U2.md:34, :56, :80, :105-110, :134, :135, :145, :148-154, :192, :279, :329` | nội dung `TICKET_CONTENT_DOCTYPES` (4 tên), `TICKET_LINK_FIELDS` (3 khóa); đọc `is_ticket_content_doctype` / `ticket_link_columns` thay cho phép thuộc tập; hàm U2 mới `ticket_link_columns` | 2 | Không đổi tên có sẵn; thêm 3 hàm (2 của T15, 1 của U2) |
| `design-addendum-1-U6b.md:178` vế (4) | `policy.is_ticket_content_doctype(ref_doctype) or ref_doctype in read.denied_doctypes()` | 2 | Không |
| `design-addendum-1-U3.md:69` | luật N-1..N-7 thay "5a" | 3 | Không |

Không ADR nào phải sửa. Không addendum đợt 2 nào dùng tên bị đổi nội dung (`design-addendum-2-U5b.md:356` chỉ nêu DocType ghi chú phiếu cũ trong một ghi chú rủi ro, không dùng hằng).

## 5. Đối chiếu đường dẫn

| Đường dẫn được nêu | Mới? | Gốc cho phép | Khớp `protected_paths`? |
|---|---|---|---|
| `erp_ai/agent/policy.py`, `erp_ai/agent/test_policy.py` (T15 thêm) | không (có sẵn) | `erp_ai` | không |
| `erp_ai/agent/routing.py`, `test_routing.py` (T25); `redact.py`, `test_redact.py` (T35); `system_read.py`/`test_system_read.py` (T36), `knowledge.py`/`test_knowledge.py` (T37) | không (đã trong `files:` của task) | `erp_ai` | không |
| `erp_ai/constants.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (T8, T15) | không | `erp_ai` | không |

## 6. Bảng tổng hợp

| Điểm | Phán quyết | Task bị đổi |
|---|---|---|
| (1) T25: `design.md:389` thêm ghi chú cho nơi gọi cũ | `d_watcher` ba trạng thái: `None` = không nói (không ghi chú), chuỗi rỗng = chưa cấu hình (ghi chú `D_WATCHER_MISSING_NOTE`), tên người dùng = xét `is_active_agent` (sai → ghi chú); thay `design.md:389` | T25 (gỡ BLOCKED, 5 test), U4b (`:245` `or ""`, 1 test) |
| (2) T8: `"HD Ticket Comment"` trong `constants.py` trái luật D8 | Luật giữ nguyên; `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` ở `erp_ai/constants.py` (ADR-034 QĐ 1); DocType có Link tới HD Ticket phủ qua meta bằng `policy.ticket_link_fieldnames` / `is_ticket_content_doctype`; thay D-13, `design-w0-fixes.md:55, :66` | T8 (gỡ BLOCKED, 1 test mới), T15 (thêm `policy.py`, `test_policy.py`, 2 test), U2, U6b (chữ) |
| (3a) T35: đầu ra có NFC không | Có, luôn NFC; nơi gọi che trước rồi cắt, không so đầu ra với đầu vào | T35, T36, T37 (mỗi task 1 test) |
| (3b) T35: nghĩa của `SECRET_PATTERNS[0]` | `SECRET_PATTERNS` = đúng 5 mẫu giá trị; mẫu ứng viên là `_KEY_CANDIDATE` riêng; không truy cập theo chỉ số | T35 |
| (3c, 3d) T35: luật tên đầy đủ | N-1..N-7 (thêm N-2b từ viết tắt), K-1..K-8 (tối đa 3 cụm, không bỏ cặp, bỏ qua giá trị đã che), R-1..R-5 (mẫu giá trị chạy trước quét khóa-giá trị); thay 5a và `design.md:486` | T35 (vòng 4 nếu được cho), U3 (`:69` chữ) |
