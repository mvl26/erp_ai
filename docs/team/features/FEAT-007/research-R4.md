Feature: FEAT-007
Stage: research
Author-agent: researcher
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# R-4 — Tìm HD Article, trạng thái bài, quyền tạo nháp, nơi đặt HDSD

Câu hỏi (spec `## Câu hỏi kỹ thuật`, R-4; tiêu chí AC-45, AC-46, AC-47). Đã có sẵn, không làm lại: `audit-A5.md` dòng A5-1, A5-2, A5-8. Chỉ đọc mã nguồn đã cài, không chạy gì trên site `miyano`, không POC. `H/` = `/home/miyano/frappe-bench/apps/helpdesk/helpdesk/`. Số dòng là của cây đang cài.

## Version in use

- Helpdesk **15.1.0**: `H/__init__.py:1` (`__version__ = "15.1.0"`); commit bản phát hành `a185896` ngày 2026-11-04 (`git log` trên `apps/helpdesk`).
- Frappe **15.126.1**: `apps/frappe/frappe/__init__.py:54`.
- Không có lockfile riêng cho app trong bench; phiên bản đọc từ chính mã nguồn đã cài.

## (a) Tìm nội dung HD Article

**Trả lời: có, bằng `helpdesk.api.article.search(query)`; mã phía server gọi được. Có ba điều cần thử trước khi tin vào kết quả tiếng Việt (xem "Hạn chế").**

| Mục | Kết quả | Chứng cứ |
|---|---|---|
| API | `helpdesk.api.article.search(query: str) -> list`, `@frappe.whitelist()` (không `allow_guest`), gọi `helpdesk.search.search` | `H/api/article.py:92-113`, `H/api/article.py:8-10` |
| Bộ máy | Redis search (RediSearch), chỉ mục `helpdesk_idx`, khóa tiền tố `search_doc`. Không phải bộ SQLite mới của 15.1.0: bộ đó (`sqlite_search` ở `H/hooks.py:33`) chỉ lập chỉ mục HD Ticket, Comment, Communication | `H/search.py:214-237` (`HelpdeskSearch.__init__`), `H/search_sqlite.py:15-60` |
| Đơn vị lập chỉ mục | Mỗi **đoạn dưới một đầu mục** của bài là một tài liệu chỉ mục, tên dạng `<tên bài>#<đầu-mục-scrub>`; chỉ bài `status = Published` | `H/search.py:278-322` (`get_records`, `get_sections`) |
| Trường và trọng số | `subject` (tiêu đề bài) mặc định 6, `description` (nội dung đã bỏ HTML) 5, `headings` 8, `name` 1; các trọng số lấy từ HD Settings (`name_weight`, `subject_weight`, `description_weight`, `headings_weight`) | `H/search.py:229-236`, `H/search.py:249-259` (`index_doc`) |
| Xếp hạng | `scorer("DISMAX")`, `with_scores()`; lấy tối đa `NUM_RESULTS = 5` (hằng số cứng, không cấu hình được) | `H/search.py:165-166`, `H/search.py:31` |
| Dựng truy vấn | Bỏ stopword tiếng Anh + bảng HD Stopword; từ dài hơn 3 ký tự thành `%từ%` (khớp mờ), từ ngắn thành `từ*`; kiểu `and` trước, thiếu kết quả thì rút danh từ/cụm danh từ bằng TextBlob rồi `and`/`or` | `H/search.py:324-355`, `H/api/article.py:27-35,92-113` |
| Lọc | `filter_public_articles` kiểm lại bằng `frappe.get_list("HD Article", status="Published")` vì chỉ mục có thể cũ; `get_list` chạy theo quyền người gọi | `H/api/article.py:38-50` |
| Dạng hạt kết quả | `{"title": "Articles", "items": [...]}`; mỗi item có `id` (`HD Article:<tên>#<đoạn>`), `name`, `subject`, `description` (trích, có thể có thẻ highlight), `headings`, điểm | `H/search.py:324-355`; mẫu giả trong `H/test_utils.py:900-912` |

**Gọi từ mã server dưới tài khoản `ai.agent@miyano.com.vn`.** Hàm không kiểm vai trò; chỉ cần phiên đăng nhập. `filter_public_articles` dùng `get_list`, nên tài khoản cần quyền đọc HD Article: DocType cấp read cho `Agent`, `System Manager`, `HD Customer`, `HD Customer Manager` (`H/helpdesk/doctype/hd_article/hd_article.json`, mục permissions). Tài khoản agent có role `Agent` (`erp_ai/constants.py:4`, `HELPDESK_AGENT_ROLE = "Agent"`) và `ERP AI Agent` (`erp_ai/constants.py:2`), nên đủ. Quyền tùy biến (Custom DocPerm) trên site chưa tra: UNVERIFIED.

**Hạn chế đã thấy trong mã (cần xác nhận bằng một lần chạy thật sau này, ngoài phạm vi vòng này):**

1. **Dấu tiếng Việt.** `sanitize_query` thay mọi ký tự ngoài `a-z0-9` và khoảng trắng bằng dấu cách (`H/api/article.py:53-58`, regex `[^a-z0-9\s]`), và `Search.clean_query` làm tương tự (`H/search.py:96, 180-184`, `unsafe_chars`). Truy vấn "hướng dẫn" thành "h ng d n". Nội dung bài trong chỉ mục giữ nguyên dấu. Một công cụ CSKT gọi nguyên `api.article.search` với câu tiếng Việt sẽ cho kết quả kém hoặc rỗng; stopword và TextBlob cũng là tiếng Anh. Nếu cần tiếng Việt, công cụ phải gọi tầng thấp hơn (hoặc tự lọc) chứ không qua `sanitize_query`. Mức chắc chắn: cao về mã, chưa đo trên chỉ mục thật. Việc RediSearch có gấp dấu hay không: UNVERIFIED.
2. **Độ mới của chỉ mục.** Mã không có hook ghi bài vào chỉ mục khi lưu (`grep index_doc|remove_doc` ngoài `search.py` không có chỗ gọi; `H/hooks.py` không có `doc_events` cho HD Article). Chỉ mục dựng lại ở `after_migrate` (nền, hàng `long`, `H/hooks.py:25-28`) và bởi `build_index_if_not_exists` mỗi tick lịch `all` (`H/hooks.py:36-39`), mà hàm này chỉ dựng khi chỉ mục chưa có hoặc số tài liệu lệch quá 10% so với số đoạn đang có (`H/search.py:203-211, 371-374`, `isclose(..., rel_tol=0.1)`). Suy luận: bài mới xuất bản hoặc bài sửa nội dung có thể chưa tìm được tới khi dựng lại. Công cụ CSKT của bot cần dùng cách khác (gọi `build_index_in_background` sau khi người duyệt xuất bản, hoặc tự tìm trên bảng) hoặc chấp nhận độ trễ. Chưa kiểm bằng chạy thật.
3. **Cần mô-đun RediSearch trên Redis của site.** Một lệnh `redis-cli MODULE LIST` trên cổng 13000 không trả dữ liệu (không kết luận được): UNVERIFIED. Nếu thiếu, `search` ném lỗi `ResponseError`; AC-46 cần đường dự phòng.

**Đối chiếu AC-46** ("không theo tên băm; ≤ N kết quả; không nháp/lưu trữ; hai từ đảo thứ tự vẫn thấy, nhiều từ khớp xếp trước"): chỉ mục chỉ có bài Published và `filter_public_articles` kiểm lần hai (đạt); kiểu `and` với DISMAX không phụ thuộc thứ tự từ và có điểm (đạt về cơ chế, cho tiếng Anh/ASCII); giới hạn cứng 5 và không trả "tiêu đề bài" riêng ngoài `subject` (cấu hình N cần cắt trên kết quả, tối đa 5).

## (b) Trạng thái bài, giữ bản nháp khỏi cổng khách, quyền chèn bản nháp

**Trạng thái:** có đúng ba: `Published`, `Draft`, `Archived`; mặc định `Draft` (`H/helpdesk/doctype/hd_article/hd_article.json`, trường `status`, options `Published\nDraft\nArchived`, `default: "Draft"`). Tên bài là mã băm ngẫu nhiên (`autoname: hash`, đã có ở A5-1).

**Luật trong controller** (`H/helpdesk/doctype/hd_article/hd_article.py`):
- `validate_published_content`: bài Published bắt buộc có `content` (`:23-24`).
- `before_save`: Published thì đặt `published_on`; chuyển về Draft thì xóa `published_on`; chuyển Archived thì **đặt `category = None`** (`:30-36`). Bài Draft không được gán `idx` (chỉ Published mới tính `idx`, `:42-48`).
- `before_insert`: `author = frappe.session.user` (`:28-29`).
- `category` không bắt buộc (không `reqd` trong JSON); quy tắc "mỗi danh mục phải còn ít nhất một bài" chỉ chạy khi đổi danh mục hoặc xóa bài (`:15-20, :55-66`).

**Giữ bản nháp khỏi cổng khách: chỉ ở tầng API, không ở tầng quyền DocType.**
- `H/hooks.py:111-125` không có `permission_query_conditions` hoặc `has_permission` cho HD Article; DocType cho `HD Customer` và `HD Customer Manager` read=1 không kèm điều kiện (`hd_article.json`, permissions).
- Các đường của Helpdesk tự lọc: `get_article` ném `PermissionError` nếu người gọi không phải agent và bài chưa Published (`H/api/knowledge_base.py:12-15`); `get_categories` và `get_category_articles` đếm/liệt kê chỉ bài Published (`knowledge_base.py:97,109`); `get_article_stats` tương tự (`H/api/article.py:61-70`); `search` chỉ có bài Published trong chỉ mục cộng lọc lần hai (xem a). `is_agent` có hiệu lực với tài khoản `ai.agent`: dòng `HD Agent` (nếu có) quyết định bằng `is_active`, không có thì xét role `Agent`/`Agent Manager` (`H/utils.py:42-58`).
- Suy luận: một người có role `HD Customer` gọi thẳng `frappe.client.get` trên HD Article chưa chắc bị chặn ở bản nháp, vì không có điều kiện theo `status` ở tầng DocType. Chưa thử (không chạy trên site). Cổng khách chuẩn của Helpdesk không dẫn tới đường này. Nếu bài nháp từ phiếu có thể chứa dữ liệu nhạy cảm (NFR-1), cần ghi nhận ở thiết kế.
- Tài liệu chính thức nói: "Only agents can see drafts" và "Customers and visitors see only published articles" (https://docs.frappe.io/helpdesk/knowledge-base, truy cập 2026-11-14). Trang này còn nhắc trường **Visibility** và danh mục con; JSON của bản 15.1.0 **không có** trường `visibility` hay danh mục con (`hd_article.json`, `hd_article_category.json`). Ghi là mâu thuẫn tài liệu ↔ mã: trang có vẻ viết cho bản mới hơn; dùng mã đã cài làm chuẩn. Phần trạng thái Draft/Published/Archived thì khớp.

**Role chèn bài nháp:** `Agent` và `System Manager`, cả hai `create=1, write=1, delete=1` (`hd_article.json` permissions). `ERP AI Agent` không có dòng riêng (Custom DocPerm trên site: UNVERIFIED), nhưng tài khoản agent giữ role `Agent`, nên `frappe.get_doc({...}).insert()` dưới phiên của chính tài khoản này, **không** dùng `ignore_permissions`, là hợp lệ về quyền DocType. Hệ quả cho **AC-45 ("Bot không xuất bản được bài")**: role `Agent` có quyền `write` đầy đủ trên HD Article, không có phân quyền theo trường, và controller không chặn đổi `status` (`hd_article.py`), nên bot **có thể** xuất bản nếu gọi `save`. Chốt chặn phải nằm ở mã của app (ví dụ ép `status = Draft` khi chèn và từ chối mọi lần ghi `status` của tài khoản agent lên bài do bot soạn); việc này thuộc về architect/designer, không có sẵn trong Helpdesk.

## (c) Nơi đặt kho HDSD để bot tìm với ít máy móc mới nhất

Hiện trạng đã cài: các file `.md` HDSD nằm dưới `apps/erpnext/docs/` (kích thước: `HDSD_ThongBao_TuThietLap_20260923.md` 8.154 byte, `HDSD-luong-tu-A-den-Z.md` 21.015, `HDSD-quan-ly-vi-tri-kho.md` 92.073; Word `.docx` cạnh đó). Hai điều đáng chú ý cho lựa chọn:

- Tool `read_source`/`search_source` của erp_ai đã đọc được `.md` dưới `apps/` (`erp_ai/agent/tools/source.py:15` `DUOI_CHO_PHEP`, `:100-102` `get_source_root`). Nhưng `search_source` chỉ quét chuỗi con không phân biệt hoa thường theo từng dòng, tối đa 40 kết quả, 30 giây, file ≤ 1 MiB (`source.py:23-29, 168-178, 181-215`): không có xếp hạng, không khớp "hai từ đảo thứ tự". `.docx` không đọc được (không nằm trong `DUOI_CHO_PHEP`).
- AC-47 yêu cầu "nội dung kho không vào được qua tool đọc mã nguồn thay cho tool này". Nếu kho nằm dưới `apps/`, nó đã nằm trong phạm vi `read_source`; điều khoản đó cần được hiểu rõ (câu hỏi cho team-leader/architect ở cuối).

| Hạng | Phương án | Cần gì mới | Ưu | Nhược / rủi ro |
|---|---|---|---|---|
| 1 | **HD Article trong một HD Article Category riêng "HDSD"**, tìm bằng cùng `helpdesk.search` đã có, lọc theo `category` | Không cần DocType, không cần thư viện tìm. Cần: (i) nhập `.md` → HTML vào HD Article (một lần, bằng tập lệnh hoặc nhập tay), (ii) công cụ CSKT dùng chung cho cả hai, lọc `category` ở kết quả (lấy tên bài rồi `frappe.db.get_value("HD Article", name, "category")`), (iii) xử lý dấu tiếng Việt và độ mới chỉ mục (a-1, a-2) | Một bộ máy tìm cho cả CSKT lẫn HDSD; có xếp hạng, có trạng thái Published/Draft/Archived; người dùng sửa HDSD ngay trong giao diện Helpdesk; cổng khách hiển thị được nếu muốn | HDSD trộn vào kho khách: bài Published trong danh mục "HDSD" **hiện trên cổng khách** (hiện không có cờ ẩn, `visibility` không có ở 15.1.0), nên có thể lộ tài liệu nội bộ; vẫn kế thừa hạn chế tiếng Việt và độ mới; mất dòng "tên tài liệu + vị trí" nếu không tự dựng từ `name#đoạn` |
| 2 | **File trên đĩa** (thư mục cấu hình trong ERP AI Setting), công cụ mới `search_manuals` quét `.md` (có thể tái dùng `_scan_file`/`resolve_safe_path` hoặc dựng chỉ mục từ khóa trong bộ nhớ) | 1 công cụ mới + 1 trường đường dẫn trong ERP AI Setting (đã có 27 trường); trả "chưa có kho HDSD" khi trường rỗng (đúng AC-47) | Không đụng cổng khách; đúng chữ AC-47 (tên tài liệu + vị trí = file + dòng/đầu mục); nguồn vẫn là file người đã viết, không phải sao chép; không phụ thuộc Redis | Phải tự xếp hạng nếu cần "đảo thứ tự"; phải lo `.docx` (không có chuyển đổi sẵn); chỉ chạy tốt với kho dạng `.md` |
| 3 | **DocType mới** (ví dụ "ERP AI Manual") với trường văn bản, tìm bằng LIKE hoặc Frappe full-text | DocType, quyền, nhập, giao diện, test, di trú (STD-OPS-2) | Tách hẳn khỏi cổng khách; kiểm soát quyền theo hàng | Nhiều máy móc mới nhất, dữ liệu lặp với file gốc, chi phí lớn hơn cả hai phương án trên; không khuyến nghị cho mục AC-47 vốn là mục "bỏ trước" trong thứ tự cắt (`spec.md:95`) |

**Khuyến nghị (researcher đề xuất, architect quyết):** phương án **2** nếu kho thật nằm dưới dạng file `.md` ở một thư mục cố định, vì ít phụ thuộc nhất và đúng tiêu chí AC-47 (chưa cấu hình → "chưa có kho HDSD"); phương án **1** nếu COO muốn HDSD được sửa trong Helpdesk và chấp nhận hai hạn chế (dấu tiếng Việt, độ mới). Việc chọn phụ thuộc vào chỗ Miyano thực sự giữ HDSD, mà mã nguồn không trả lời được.

## Câu hỏi cho người (team-leader chuyển)

> Miyano giữ các tài liệu hướng dẫn sử dụng chính thức ở đâu, dưới dạng file gì: (1) file `.md` trong repo `apps/erpnext/docs/` hay thư mục khác trên máy chủ; (2) file Word `.docx` hay PDF trên ổ chung hoặc SharePoint; (3) trang trong Helpdesk, ERPNext (Wiki, Web Page) hay công cụ khác? Và HDSD có được cho khách hàng xem trên cổng Helpdesk không?

Câu hỏi phụ cho architect: câu cuối AC-47 ("không vào được qua tool đọc mã nguồn thay cho tool này") nghĩa là kho phải nằm ngoài `apps/` hay chỉ là công cụ HDSD phải là cách chính? `read_source` đọc được mọi `.md` dưới `apps/` hiện nay.

## Confidence

- (a) cơ chế và vị trí mã: cao (đọc trực tiếp). Hành vi tiếng Việt, độ mới của chỉ mục, mô-đun RediSearch: chưa kiểm bằng chạy thật, UNVERIFIED về kết quả thực tế.
- (b) trạng thái và quyền DocType: cao. Quyền thực tế trên site (Custom DocPerm), truy cập thẳng của HD Customer vào bản nháp: UNVERIFIED.
- (c) so sánh phương án: trung bình; phụ thuộc câu hỏi người ở trên.

## Sources

- Mã nguồn Helpdesk 15.1.0 đã cài: `H/api/article.py`, `H/api/knowledge_base.py`, `H/search.py`, `H/search_sqlite.py`, `H/hooks.py`, `H/utils.py`, `H/helpdesk/doctype/hd_article/hd_article.json`, `H/helpdesk/doctype/hd_article/hd_article.py`, `H/helpdesk/doctype/hd_article_category/hd_article_category.json` (đọc 2026-11-14).
- Frappe Helpdesk, Knowledge base: https://docs.frappe.io/helpdesk/knowledge-base (truy cập 2026-11-14). Trang không ghi phiên bản; trường Visibility và danh mục con nhắc ở đó không có trong 15.1.0 (xem mục b).
- Mã erp_ai: `erp_ai/agent/tools/source.py`, `erp_ai/constants.py` (đọc 2026-11-14).
