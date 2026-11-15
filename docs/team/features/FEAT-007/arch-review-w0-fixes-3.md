Verdict: approve-with-conditions

Feature: FEAT-007
Stage: architect (review)
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc — phán quyết (2) của `design-w0-fixes-3.md` (T8, T15; chữ U2, U6b)

Phạm vi: chỉ phán quyết (2) (`design-w0-fixes-3.md:58-109`). Phán quyết (1), (3) ngoài phạm vi.

**Kết luận.** Xác nhận phán quyết (2). Đặt `TICKET_CONTENT_DOCTYPES` = 4 tên của ADR-034 QĐ 1, rồi nhận ra mọi DocType có trường Link tới HD Ticket qua meta trong `policy.py`: cách này vẫn là **một** vị từ đặt ở `policy.py` (ADR-034 QĐ 1, Ràng buộc 1), là tập cha fail-closed của danh sách mà QĐ 3 nêu, và nằm trong phần ADR-034 để cho designer ("danh sách DocType mang nội dung phiếu", `ADR-034.md:51`). Luật kiến trúc giữ nguyên độ chặt. Thứ tự sửa `policy.py` chỉ thêm một bước đầu, không xung đột. Có 1 major (U2) và 5 minor. Tất cả sửa bằng các điều kiện ở mục 3, không cần thêm vòng designer.

## 1. Căn cứ (đọc trực tiếp, đích đã biết, không qua Explore; `develop` @ `5cfc0ec`, 2026-11-14)

- `ADR-034.md:21` (QĐ 1: một vị từ; `site_api` lọc HD Ticket, Comment, Communication, File trong truy vấn), `:23` (QĐ 3: chặn lúc lưu báo cáo có `ref_doctype` mang nội dung phiếu, fail-closed), `:32` (Ràng buộc 1: mọi tool gọi hàm của `policy.py`, không tự lọc), `:51` (designer chốt danh sách).
- `erp_ai/tests/test_architecture.py:354` `LEGACY_NAMES = ("HD Ticket Comment", "commented_by", "comment_email", "comment_by")`, `:357` `LEGACY_ALLOWED_ASSIGNMENTS = {READ_TOOL_FILE: "COMMENT_HIDDEN_FIELDS"}`, `:860-885` `check_no_legacy_ticket_comment` (quét hằng chuỗi, keyword, tên định danh trong mã sản phẩm), `:1945-1949` test. Phán quyết không đụng ba chỗ này.
- `erp_ai/agent/policy.py:5-9`: chỉ import `frappe` và `erp_ai.constants`. `git diff --stat develop team/FEAT-004|team/FEAT-005|team/FEAT-007 -- erp_ai/agent/policy.py erp_ai/agent/test_policy.py erp_ai/constants.py` → rỗng cả ba: không nhánh nào khác đang sửa các file này.
- `erp_ai/install.py:221-224`: Custom Field `Task.ai_ticket` là `Link` → `HD Ticket`. `erp_ai/agent/tools/route_ticket.py:109-111`: Task do bot tạo có `subject = ticket_subject` và mô tả có liên kết phiếu. Như vậy Task **mang nội dung phiếu**. Danh sách 4 tên cũ bỏ sót Task (lỗ NFR-1 có thật); phán quyết vá lỗ đó.
- Các DocType có Link tới HD Ticket: Helpdesk `hd_ticket_comment`, `hd_ticket_activity`, `hd_notification`, `hd_email_feedback` (và `hd_ticket` tự trỏ); app: `erp_ai_log.json:64`, `erp_ai_change_proposal.json:114`.
- Người đọc Task không qua `site_api`: `site_facts.py:23` (`frappe.db.exists`), `route_ticket.py:110` (insert trực tiếp), `design-addendum-1-U6b.md:257` (`tasks_done`, `frappe.get_all`).
- `arch-review-design-w1a.md:91` (thứ tự `policy.py`: U1 → U2 → U6b), `:61` (C-7), `:49` (N-4 ToDo); `design-addendum-1-U2.md:152-153` (bảng 3.1), `:156-160` (3.2, 3.3), `:184-190` (hợp đồng cho đơn vị sau); `design-addendum-1-U6b.md:178`; `arch-impact.md:166-188` (U1 sở hữu `policy.py` ở đợt 1, U2 sau U1); `tasks.md:115` (T8), `:153-155` (T15).

## 2. Kiểm ba câu hỏi

**(a) Tập rộng hơn so với ADR-034 QĐ 1 và nhu cầu của U2, U6b, bước định tuyến.**
- QĐ 1 đòi một định nghĩa cho mọi đầu ra. Hai hàm mới nằm ở `policy.py` và mọi nơi gọi (controller, `site_api`, tool báo cáo U6b) import từ đó. Đây không phải định nghĩa thứ hai. Tập mới chứa trọn 4 tên của QĐ 1 và 3 tên của QĐ 3, nên chỉ chặn thêm, không nới.
- Bot tạo Task (`route_ticket.py:110`), bước định tuyến đọc Task (`site_facts.py:23`) và job vòng đời U6b (`U6b.md:257`) đều đi qua ORM trực tiếp, không qua `site_api`. Vì vậy không đường nào bị đổi. Bot chỉ chạy trên phiếu `can_send_ticket` đúng, nên khi tạo Task qua `site_api` (Toàn quyền), Task trỏ tới phiếu hiện tại và vẫn được phép.
- Task của phiếu loại trừ bị ẩn khỏi `list_records`/`get_record` ở mọi chế độ. Đó đúng là NFR-1 (Task mang tiêu đề phiếu). Dùng `create_record`/`update_record` để chuyển một Task vào phiếu loại trừ thì bị từ chối, nhờ C-7 khi C-7 đọc `ticket_link_columns`.
- ERP AI Log và ERP AI Change Proposal nay cũng là "nội dung phiếu". Chúng vốn nằm trong vùng cấm của app, nên chỉ thêm lọc và `excluded_note` nếu có lúc được liệt kê. Vô hại.
- Báo cáo có `ref_doctype = "Task"` (các báo cáo dự án của ERPNext) nay bị chặn lúc lưu và chặn lại lúc chạy (U6b `:178` vế 4). Điều này đúng với AC-49 ("kết quả không chứa nội dung phiếu nhóm loại trừ") và với Hệ quả xấu đã ghi của ADR-034, nhưng người dùng thấy được (minor M-3).

**(b) Thứ tự sửa `policy.py`.** Thứ tự mới là T15 (đợt 0) → U1 → U2 → U6b. U1 cắt nhánh sau khi đợt 0 vào `develop` (`arch-impact.md`, cổng đợt), nên U1 thấy sẵn hai hàm. FEAT-004/FEAT-005 không sửa `policy.py`, `test_policy.py`, `constants.py` (diff rỗng), nên lần merge `team/FEAT-004` không có xung đột ở đây. Điều kiện duy nhất là T15 chỉ **thêm** mã (C-T15-1). Bảng ở `arch-review-design-w1a.md:91` đổi thành dòng ở mục 4.

**(c) Luật kiến trúc.** `LEGACY_NAMES`, `LEGACY_ALLOWED_ASSIGNMENTS` và test giữ nguyên. Không có ngoại lệ mới, và T8, T15 không thêm `test_architecture.py` vào `files:`. DocType ghi chú phiếu cũ được phủ bằng cấu trúc, mã sản phẩm không viết tên. Đây là cách luật D8 / ADR-010 muốn (không dùng DocType cũ làm đường ghi; `ADR-010.md:86`). Luật **không yếu đi**. Phán quyết còn tự cấm thêm `"reference_ticket"` (C-T15-3).

## 3. Phát hiện

| severity | STD | file:line | ADR | mô tả | sửa |
|---|---|---|---|---|---|
| major | STD-SEC-4 | `design-w0-fixes-3.md:86` (`ticket_link_columns`), `:87`, `:91` | ADR-034 QĐ 1, Ràng buộc 2 | Theo phán quyết, một DocType là nội dung phiếu khi nó có **bất kỳ** trường Link tới HD Ticket (`:65`). Nhưng `ticket_link_columns` trả **chỉ** cặp động khi DocType là khóa của `TICKET_LINK_FIELDS`. Nếu ai đó thêm Custom Field Link HD Ticket vào Comment, Communication hay File, `ticket_content_filters`, `is_ticket_record_excluded` và C-7 bỏ qua trường đó: dòng của phiếu loại trừ lọt vào danh sách, trong khi `is_ticket_content_doctype` vẫn đúng. Một DocType bị phủ theo hai định nghĩa khác nhau. | C-U2-1 |

`minor | — | — | 5 điểm: M-1 STD-ERR-2: so tên DocType với hằng phân biệt hoa thường, còn site_api so tên không phân biệt (_named_in) → C-T15-2; M-2 STD-GIT-2: T15 import TICKET_CONTENT_DOCTYPES mà T8 tạo, nhưng depends chỉ ghi T14 → C-T15-4; M-3 STD-DOC-4: báo cáo trên Task và trên mọi DocType sau này có Link tới phiếu bị chặn (người dùng thấy được, AC-49) mà chưa ghi ở đâu → C-T15-5; M-4 STD-TEST-8: test_empty_ticket_link_row_still_listed chỉ thử DocType cũ, không thử Task có ai_ticket NULL (Custom Field) → C-U2-2; M-5 STD-TEST-3: slot test: của T15 không có test_policy.py → C-T15-4 | dev's call trong phạm vi các điều kiện dưới`

## 4. Điều kiện (tech-lead chép nguyên vào `tasks.md`)

**T8**
- C-T8-1. `erp_ai/constants.py`: `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")`, đúng thứ tự này. Không còn hằng chuỗi `"HD Ticket Comment"` hay `"reference_ticket"` ở bất kỳ file nào của T8.
- C-T8-2. Diff của T8 không đụng `erp_ai/tests/test_architecture.py`. `cmd.test_one` cho `erp_ai/tests/test_architecture.py` (có `test_no_legacy_ticket_comment_or_spoofable_author`) và `test_erp_ai_setting.py::TestCatalogRules::test_ticket_content_doctypes_is_adr_034_list` phải xanh, đầu ra dán vào journal.

**T15**
- C-T15-1 (thứ tự `policy.py`). Chỉ **thêm**: một khối mới ở cuối `erp_ai/agent/policy.py` gồm `ticket_link_fieldnames`, `is_ticket_content_doctype`, và thêm `TICKET_CONTENT_DOCTYPES` vào dòng `from erp_ai.constants import …` (`policy.py:9`). Không sửa hàm, hằng hay import nào khác, và không import `erp_ai.agent.*` hay `erp_ai.erp_ai_agent.*` (ADR-001 Ràng buộc 2). Trong `test_policy.py` chỉ thêm lớp `TestTicketContentDoctype`.
- C-T15-2 (một tên, một kết quả). Hai hàm làm việc trên tên DocType chuẩn: `name = frappe.db.get_value("DocType", doctype, "name")`. Không có → `()` / `False`, không ném. Phép thuộc `TICKET_CONTENT_DOCTYPES` và `frappe.get_meta` dùng `name`. Test thêm vào `test_constant_and_ticket_links`: `is_ticket_content_doctype("comment")` đúng; `is_ticket_content_doctype("Task")` đúng (Custom Field `ai_ticket`); `ticket_link_fieldnames("Task") == ("ai_ticket",)`.
- C-T15-3 (luật D8). Chữ lỗi lúc lưu được dựng từ biến `ref_doctype`, không viết sẵn tên. Trong `erp_ai/**` ngoài file test, `"HD Ticket Comment"` và `"reference_ticket"` xuất hiện 0 lần. Reviewer kiểm bằng grep trên diff, và `test_architecture.py` xanh.
- C-T15-4 (kế hoạch). `depends:` của T15 ghi thêm `T8`. Slot `test:` ghi thêm `erp_ai/agent/test_policy.py`. Trước khi merge chạy `cmd.test_one` cho `test_erp_ai_setting.py`, `erp_ai/agent/test_policy.py`, `erp_ai/tests/test_architecture.py`, đầu ra dán vào journal.
- C-T15-5 (hệ quả cho người dùng). Thêm vào `test_report_on_ticket_linked_doctype_blocked` một ca: báo cáo có `ref_doctype = "Task"` bị chặn. team-leader ghi một dòng journal và chuyển cho analyst như câu hỏi **không chặn**: "báo cáo trên Task (và mọi DocType có Link tới phiếu) không chạy được qua bot (AC-49, ADR-034 QĐ 3)". Writer đưa câu này vào As-Built. Nếu chưa có câu trả lời thì giữ mặc định (chặn).

## 5. U2 thay đổi gì (đợt 1; thêm vào chữ của `design-w0-fixes-3.md:81-95` và C-6..C-8)

- C-U2-1 (major ở trên). `ticket_link_columns(doctype)` = cặp động `TICKET_LINK_FIELDS[doctype]` (nếu có) **cộng** `(None, f)` cho mỗi `f` của `ticket_link_fieldnames(doctype)`, không loại trừ nhau. `ticket_content_filters`, `owning_ticket`/`is_ticket_record_excluded`, kiểm `create_record` và C-7 (`update_record`) đều chỉ đọc cột qua `ticket_link_columns`. Không chỗ nào còn đọc `TICKET_LINK_FIELDS` trực tiếp, trừ chính `ticket_link_columns`. Test mới `test_site_api.py::TestExcludedTicketReads::test_static_link_on_dynamic_doctype_also_filtered`: dùng một DocType test (hoặc Custom Field tạm trong test) có cả cặp động lẫn Link tĩnh tới phiếu loại trừ; dòng chỉ trỏ qua Link tĩnh vẫn bị ẩn.
- C-U2-2. `test_empty_ticket_link_row_still_listed` thêm ca Task có `ai_ticket` NULL (Task người tạo, A-11) vẫn có trong danh sách. Thêm `TestExcludedTicketReads::test_task_of_excluded_ticket_hidden` (Task có `ai_ticket` = phiếu loại trừ, ở cả hai chế độ). C-7 thêm ca: đổi `ai_ticket` của Task sang phiếu loại trừ → `ok=false`.
- Bảng thứ tự `arch-review-design-w1a.md:91` đổi thành: `erp_ai/agent/policy.py` — **T15 (đợt 0, chỉ khối 2 hàm)** → U1 → U2 → (U6b, một dòng `RUN_LIMIT_TRIGGERS`). U1, U2 không sửa thân hai hàm của T15. Đổi nghĩa của hai hàm đó cần một phán quyết designer mới.
- Hợp đồng `design-addendum-1-U2.md:184-190` thêm: `is_ticket_content_doctype`, `ticket_link_fieldnames` (chủ T15), đơn vị gọi U2, U6b, controller ERP AI Setting; `ticket_link_columns` (chủ U2), đơn vị gọi U6b. U6b `:178` vế (4) kiểm lại lúc chạy bằng **đúng** `policy.is_ticket_content_doctype` (ADR-034 Ràng buộc 1), không giữ phép thuộc hằng.
- `arch-review-design-w1a.md:49` (N-4, ToDo). Nếu qa thấy ToDo lộ tiêu đề phiếu, không thể chỉ thêm ToDo vào hằng, vì test của T8 khóa đúng 4 tên. Cách sửa phải là phán quyết designer mới: thêm ToDo vào `TICKET_LINK_FIELDS` và vào nhánh tên của `is_ticket_content_doctype`, đổi test T8 theo lý do thiết kế đổi (STD-TEST-5). Ghi lại để không ai sửa test cho xanh.

## 6. Tự phản biện

Hai task tuân đủ điều kiện mà vẫn va nhau:
1. U2 lọc bằng `TICKET_LINK_FIELDS` trong khi controller lọc bằng meta → đã chặn bằng C-U2-1 (một lối vào cột duy nhất).
2. T15 và U1 cùng sửa đầu `policy.py` → đã chặn bằng C-T15-1 (T15 chỉ thêm khối cuối và một tên import; U1 cắt nhánh sau đợt 0).

Sau khi siết, không tìm được cặp nào khác trong phạm vi phán quyết (2).
