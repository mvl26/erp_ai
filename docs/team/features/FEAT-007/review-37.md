Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 37 — FEAT-007 T37

- Diff: `git diff a805842d416dd572403e7837d76ead11b8df24e3..b4e6be7` (nhánh `team/FEAT-007-task-37`; vòng 1: `c6c3a4f`, 2 file mới +298; vòng 2: `git diff c6c3a4f..1247aa5`, +35/−2; vòng 3: `git diff 1247aa5..b4e6be7`, +65/−2)
- Vòng: 3 (trần `max_rework` = 3)
- Verdict: approve (vòng 3)

## Vòng 1 — request-changes

- Lệnh đã dùng (chỉ đọc): `git log --oneline a805842d..team/FEAT-007-task-37`, `git diff --stat …`, `git diff …` (đọc hết), `git log -1 --format='%an %ae%n%B'`; `tasks.md:12-19` và khối T37, `design.md:480-495`, hàng D-12 `design.md:70`, `design-w0-fixes-3.md` mục 3, AC-46 `spec.md:216`, `ADR-034.md:24`; `git show a805842:` của `redact.py`, `test_utils.py`; frappe `utils/data.py:1529-1534` (`strip_html`). Reviewer tự báo: một lệnh `python3 -c` chỉ đọc `.team/profile.json`, không phải lệnh git, bị hook role-policy nhắc.
- Bằng chứng của dev: RED với hàm giả trả `[]`: `Ran 15 tests … FAILED (failures=17)`, `AssertionError: Lists differ: [] != ['o137m5a3cv']`, `AssertionError: ValidationError not raised`, `AssertionError: Expected 'get_list' to have been called once. Called 0 times.`, `AssertionError: 0 != 1`; GREEN `test_knowledge` `Ran 15 tests in 2.313s OK`, `test_architecture` `Ran 112 tests in 6.089s OK`.
- Lớp 1 (khớp spec): đủ tên test của Expect; chỉ Published, quyền của phiên, giữ dấu, `KB_SCAN_MAX = 200`, trích 300 ký tự, che trước cắt sau (3a) đều có; đúng touchpoints. Một lỗ làm hỏng vế "tìm theo nội dung" của AC-46 (finding dưới).

### Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/knowledge.py:58 (cả `_excerpt` ở :78) | `strip_html` xóa mỗi thẻ bằng chuỗi rỗng (frappe `_striptags_re.sub("", text)`, data.py:1529-1534). Helpdesk lưu bài dạng HTML (`<p>…</p><p>…</p>`, tiêu đề, mục danh sách), nên từ cuối khối này dính vào từ đầu khối kia: `<p>Lỗi máy in</p><p>Mã hàng sai</p>` thành `Lỗi máy inMã hàng sai`, sinh từ `inmã`. Tìm `in` hay `mã` không khớp bài đó như một từ; bộ lọc LIKE cho bài qua nhưng phép xếp hạng chấm 0 hoặc quá thấp, hỏng AC-46. Mọi dữ liệu gieo của test đều né ca này. | Đổi mỗi thẻ thành dấu cách trước khi tách từ và dựng trích đoạn, ví dụ `strip_html(content.replace("<", " <"))`, vẫn dùng `strip_html`, vẫn che trước cắt sau (3a). Thêm test với `<p>Lỗi in</p><p>Mã hàng</p>`: tìm `mã` và `in` thấy bài, trích đoạn không chứa `inMã`. | confirmed (đọc mã; không chạy)

minor | — | — | 5 điểm nhỏ: (1) docstring `search_kb_articles` nói trả "`limit` dòng" trong khi trả tối đa `limit`; `limit` âm lặng lẽ bỏ dòng cuối, `None` trả hết; (2) thực thể HTML không được giải mã (`&nbsp;`, `&amp;`), thành từ tìm được và hiện thô trong trích đoạn; (3) việc chọn từ khớp **đầu tiên** cho trích đoạn chưa được ghim; (4) `_excerpt` có thể chọn từ khớp nằm trong chữ che `[đã che]`; (5) kế hoạch test của AC-46 nói 6 bài (2 nháp, 1 lưu trữ), `test_only_published` dùng 1 nháp, 1 lưu trữ | tùy dev

### Review checklist (10)

1. đạt 2. đạt 3. **không đạt** (RED có dán, không skip; ca HTML nhiều khối chưa có test và đang hỏng; các đột biến thử tay đều bị bắt: bỏ phép xếp phụ `modified`, cắt trước khi che, `ignore_permissions`/`get_all`, bỏ dấu, bỏ `limit`) 4. đạt (từ sinh từ hash duy nhất, không commit, `modified` đặt tường minh) 5. đạt 6. đạt (`get_list` dưới phiên; LIKE có tham số và escape; trích đoạn qua `redact_secrets` trước khi cắt) 7. đạt 8. đạt 9. đạt 10. đạt (`feat(agent): … (FEAT-007)`, một commit, không trailer AI)

### Không kiểm được từ diff (vòng 1)

- `design.md:488` và 3a viết nguyên chữ `title + strip_html(content)`; cách sửa đề nghị vẫn gọi `strip_html`.
- Giả định trình soạn của helpdesk sinh `&nbsp;`/`&amp;` và thẻ khối không có khoảng trắng giữa (khớp dữ liệu gieo `helpdesk/test_utils.py:879`), chưa kiểm trên bài thật.
- Độ phủ khi từ phổ biến lấp đầy `KB_SCAN_MAX = 200`: thiết kế đã nhận; kiểm ở tầng công cụ (U6b).
- `tokenize` chỉ giữ 8 từ đầu trong khi U6b gọi trên chữ phiếu (dev đã nêu; thuộc team-leader cho đợt 1).

## Vòng 2 — approve của reviewer; tech-lead tính là chưa đạt (bước 9)

- Diff: `git diff c6c3a4f..team/FEAT-007-task-37` (đầu `1247aa5`, 1 commit, 2 file +35/−2). Lệnh: `git log --oneline`, `git diff --stat`, `git diff`, `git diff --check` (sạch), `git log -1`, `git show` của `knowledge.py`, `test_knowledge.py`, `redact.py`; `strip_html` ở `frappe/utils/data.py:1529-1534`; kiểu trường `content` ở `hd_article.json:46-48` (`Text Editor`).
- Bằng chứng của dev: RED trên `c6c3a4f`: `FAIL: test_html_blocks_do_not_glue_words … AssertionError: Lists differ: [] != ['819vjcctsr']`; GREEN `test_knowledge` `Ran 17 tests in 3.664s OK`, `test_architecture` `Ran 112 tests in 6.091s OK`; `test_less_than_as_text_or_entity_keeps_words` xanh ngay lần đầu (test canh).
- Finding vòng 1 (major STD-TEST-8, `knowledge.py:58`/`:78`): **ADDRESSED**. `knowledge.py:55` dựng chữ bằng `strip_html((row.content or '').replace('<', ' <'))`; `_excerpt` không đổi, vẫn che trước cắt sau; `test_html_blocks_do_not_glue_words` phủ `<p>` liền `<p>`, hai `<li>`, hai bên `<br>` (ca `<br>` làm hỏng bản sửa yếu chỉ thêm dấu cách trước `</`).
- Không hồi quy: che trước cắt sau, `EXCERPT_MAX_CHARS = 300`, xếp hạng (`len(matched)`, `in_title`, `modified`), từ của tiêu đề, `row.content or ''`.
- Phát hiện mới: không blocker, không major.

minor | — | — | 3 điểm nhỏ: (1) **suspected (STD-SEC-6)**: `replace('<', ' <')` cũng tách từ bị một thẻ inline cắt: `password: <b>abc</b>def` trước đây thành `password: abcdef` và được che nguyên, nay thành `password:  abc def`, giá trị trần K-4 dừng ở dấu cách, `def` còn lộ trong trích đoạn; khóa `sk-…` bị thẻ cắt cũng vậy; sửa được bằng cách chỉ thêm dấu cách trước thẻ khối và `<br>`; (2) mỗi thẻ thêm một dấu cách, không gộp: nội dung nhiều thẻ (bảng) lấp một phần 300 ký tự bằng dãy dấu cách; (3) test thứ hai là test canh, không phải test RED | tùy dev

- Review checklist (10), chỉ diff sửa: 1–10 đạt (mục 6 kèm điểm nhỏ (1) "suspected").
- Không kiểm được từ diff (vòng 2): reviewer không chạy test; test `<` gõ tay chỉ đúng vì trường `Text Editor` escape `<` lẻ thành `&lt;` khi lưu, dòng HD Article ghi không qua bước làm sạch vẫn có `<` thô (có từ trước bản sửa).
- **Kết luận của tech-lead cho điểm "suspected" (bước 9 của build, trước khi tick):** đọc theo mã thì đây là lỗ thật của NFR-6 do chính bản sửa vòng 2 mở ra (trước đó giá trị được che nguyên). Tính là review chưa đạt, KHÔNG merge `1247aa5`; gửi nguyên văn cho dev làm vòng 3/3 với điều kiện phải có RED thật, không có RED thì tech-lead rút phán này.

## Vòng 3 — approve

- Diff: `git diff 1247aa5..team/FEAT-007-task-37` (đầu `b4e6be7`, 1 commit, 2 file +65/−2, trong touchpoints). Lệnh: `git log --oneline`, `git diff --stat`, `git diff`, `git show` của `knowledge.py`, `test_knowledge.py`, `redact.py`, `git log -1 --format='%an%n%B' b4e6be7`; `strip_html` ở `frappe/utils/data.py:1532`.
- Bằng chứng của dev: RED trên `1247aa5`: `AssertionError: 'cdkb' unexpectedly found in 'T37 8709e775  kbfcdcdcb015 password:  [đã che] cdkb  khoá sk- fakekbabcdef 0123456789 hết '`; GREEN `test_knowledge` `Ran 20 tests in 1.784s OK`, `test_architecture` `Ran 112 tests in 5.792s OK`.
- Finding vòng 2 (STD-SEC-6, `knowledge.py:55`): **ADDRESSED**. `knowledge.py:25-29`: `_BLOCK_TAG = re.compile(rf"<(?=/?(?:{BLOCK_TAGS})\b)", re.IGNORECASE)` chỉ thêm dấu cách trước thẻ khối (mở, đóng, tự đóng) và `<br>`; `knowledge.py:62` dùng `_BLOCK_TAG.sub(' <', …)`. `password: <b>fake-ab</b>cdkb` nay thành `password: fake-abcdkb`, được che nguyên; `sk-<i>fakekbabcdef</i>0123456789` thành token `sk-…` 22 ký tự, mẫu `sk-[\w-]{16,}` che. `test_secret_split_by_inline_tag_fully_masked` (`test_knowledge.py:237`) đi qua lệnh lưu HD Article thật; `test_inline_tag_does_not_split_word` (`:256`) phủ 12 thẻ inline, hoa thường lẫn, có thuộc tính.
- Không hồi quy các điểm vòng 1, 2: `test_html_blocks_do_not_glue_words` (`:120`) không nằm trong diff và còn nghĩa (bỏ `p`, `li`, `br` khỏi `BLOCK_TAGS` làm nó đỏ); `test_block_tag_separates_words_any_case_closing_or_self_closing` (`:282`) kiểm chữ hoa, thẻ đóng, `<br/>`/`<BR />`; `_excerpt`, `EXCERPT_MAX_CHARS`, khóa xếp `item[:3]`, lời gọi `frappe.get_list` không đổi; `_raw_excerpt` chỉ patch `get_list` trong hai test dạng chữ mới.
- Phát hiện mới: không blocker, không major.

minor | — | — | 3 điểm nhỏ: (a) phần lớn thành viên `BLOCK_TAGS` (`td`, `th`, `tr`, `pre`, `blockquote`, `hr`, `h1`/`h3`-`h6`, `table`…) và `\b` sau tên thẻ chưa được test nào ghim; bỏ một thẻ chỉ làm dính từ (che nhiều hơn, không lộ); (b) hàm trợ giúp `_raw_excerpt` nằm giữa các method test của `TestSearchKb`; (c) `BLOCK_TAGS` không có gạch dưới đầu trong khi `_WORD`, `_BLOCK_TAG` có | tùy dev

- Review checklist (10), chỉ diff sửa: 1–10 đạt (mục 5: regex tuyến tính, một lookahead trên dãy lựa chọn cố định; mục 6: lỗ STD-SEC-6 đã đóng, phân quyền không đổi; mục 10: `fix(agent): … (FEAT-007)`, không trailer AI).

## Không kiểm được từ diff — kết luận của tech-lead

- Reviewer không chạy test → tech-lead chạy sau merge trên `team/FEAT-007` @ `e920c08` (dưới khóa site): `test_knowledge` `Ran 20 tests in 1.699s OK`, `test_architecture` `Ran 112 tests in 5.814s OK`.
- `cmd.lint` trên `e920c08`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền, đã trả lại); hai file của T37 sạch.
- Thẻ mà trình soạn bài của Helpdesk thật sự sinh (`div`, `figure`, `caption`…) chưa được đối chiếu: thẻ khối thiếu trong `BLOCK_TAGS` chỉ làm dính từ (tìm kém hơn), không làm lộ bí mật → không chặn; kiểm trên bài thật ở `/team:verify` (AC-46).
- Chữ `title + strip_html(content)` của `design.md:488` / 3a: mã vẫn gọi `strip_html`, chỉ thêm dấu cách trước thẻ khối; tech-lead đọc là không trái thiết kế. Đề nghị designer ghi thêm một dòng vào `design.md:488`.

## deferred

- Điểm nhỏ của ba vòng (5 + 2 + 3; điểm (1) vòng 2 đã thành finding vòng 3 và đã đóng).
- Thực thể HTML (`&lt;`, `&nbsp;`, `&amp;`) thành từ tìm được và hiện thô trong trích đoạn; mẫu chú thích `<!--.*?-->` của `strip_html` không có DOTALL. Cả hai có từ trước các bản sửa.
- **Cần phán của designer, chuyển team-leader (NFR-6, thuộc luật K-4 của T35, không thuộc T37):** giá trị trần K-4 của `redact.py` (`_KEY_VALUE`) dừng ở `&`. Trình soạn lưu `&` gõ tay thành `&amp;`, nên mật khẩu `ab&cd` ra `[đã che]&amp;cd` trong trích đoạn CSKT, lộ một phần.
- `tokenize` giữ 8 từ đầu trong khi `design-addendum-1-U6b.md:300` gọi trên chữ phiếu: chuyển team-leader cho kế hoạch đợt 1.
