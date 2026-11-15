Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 123 — FEAT-007 T123

- Diff: `git diff a3dd63fdf9d06fc6f86df9f5e4d8737f8353b6b0..da8eb85` (nhánh `team/FEAT-007-task-123`; 2 commit `5a00deb` test, `da8eb85` mã; 2 file +41/−5, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `b0358c1` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED sau commit test, `MIGRATE_EXIT=0`: `ERROR: test_plain_text_keeps_block_words_apart`, `ERROR: test_text_words_not_capped`, cả hai `AttributeError: module 'erp_ai.agent.knowledge' has no attribute 'text_words'`; `Ran 39 tests in 1.258s FAILED (errors=2)`. GREEN, `MIGRATE_EXIT=0`: test_knowledge `Ran 39 tests in 1.117s OK`, test_architecture `Ran 181 tests in 15.480s OK`.
- Lớp 1: đạt mọi tiêu chí, chỉ sửa trong touchpoints.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): diff có `text_words(text) -> set[str]` (`set(_words(text))`, không cắt 8 từ) và `plain_text(html)`. `plain_text` làm đúng như mã cũ: `strip_html(_BLOCK_TAG.sub(" <", html or ""))`. `search_kb_articles` gọi hai hàm này thay cho mã tại chỗ, và hai bên tương đương từng ký tự. `tokenize` vẫn lấy 8 từ, `search_manuals` không đổi. Không có phần thừa. Đạt.
2. Touchpoints (STD-DESIGN-1, STD-STRUCT-1/2): chỉ sửa `erp_ai/agent/knowledge.py` và `erp_ai/agent/test_knowledge.py`, không có file mới. Đạt.
3. Test trước (STD-TEST-1/8/4): commit test `5a00deb` đứng trước commit mã, RED là AttributeError cho cả hai test. Đã thử từng đột biến trong đầu, test bắt được cả 7: `text_words` gọi `tokenize` (trả 8 phần tử, khác 20); trả list thay set; bỏ NFC (chữ NFD tách thành `ma` + dấu rời, khác `mã`); bỏ ngưỡng 2 ký tự (lọt `a`, `đ`); `plain_text` không chèn dấu cách (ra `mộthai`); chèn dấu cách trước mọi thẻ (ra `ha i`); bỏ `or ""` (TypeError với None). Không có skip hay xfail. Đạt.
4. Không sửa khẳng định cũ; test mới là hàm thuần, không đụng DB, không phụ thuộc giờ (STD-TEST-5/6). Đạt.
5. Lỗi và đầu vào (STD-ERR-1/2/5): None và chuỗi rỗng đều có nhánh xử lý và có test. Không có lệnh bắt lỗi nào, không gọi dịch vụ ngoài. Đạt.
6. Bảo mật (STD-SEC-1/3/4/6): không chứa secret. `search_kb_articles` vẫn dùng `frappe.get_list` theo quyền của phiên và giữ nguyên cách thoát ký tự LIKE. Đạt.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): chỉ thêm hai hàm công khai, chữ ký khớp `Returns`. Không đổi API cũ, không có migration. Đạt.
8. Tên và kiểu viết (STD-NAME-1/2, STD-STYLE-4/5): tên snake_case, theo kiểu tab của file. Comment cũ được rút gọn đúng ý: phần nói về thẻ khối nay nằm ở docstring của `plain_text`. Không có mã chết. Đạt.
9. Phụ thuộc (STD-DEP-1/3/5): không thêm phụ thuộc. Đạt.
10. Commit, nhánh (STD-NAME-4/5, STD-GIT-1/8): message theo mẫu `type(scope): ... (FEAT-007)`, nhánh `team/FEAT-007-task-123`, không có dòng ghi công AI. Đạt.

### Findings

- Không có blocker hay major.
- minor | — | — | 1 điểm nhỏ: `test_knowledge.py:189` có comment "any case" nhưng không ghim được `re.IGNORECASE` (`<DIV>` đứng đầu chuỗi, còn `</LI>` có `<li>` thường đi liền sau). Bỏ IGNORECASE thì test vẫn xanh. Muốn ghim thì thêm một ca như `"một<BR>hai"`, nơi thẻ hoa là chỗ ngăn duy nhất giữa hai từ (STD-TEST-8). Hành vi này đã có từ trước, ngoài tiêu chí T123 | dev's call

### Không kiểm được từ diff

- Phần sửa tài liệu ở mục "Loại" của `design-w0-fixes-5.md` điểm 4 chưa làm. `design.md:489` chưa có hai chữ ký mới. `design-addendum-1-U6b.md` chưa có `text_words`/`plain_text` (grep ra 0 dòng). Việc này của designer, không phải của dev T123.
- Hai test `test_read.py` (`test_match_beyond_eighth_word_found`, `test_words_of_adjacent_fields_not_joined`) thuộc task U6b, nằm ngoài diff này.
- Reviewer không chạy test.

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline a3dd63f..da8eb85`; `git log --format='%H%n%B---' <range>`; `git diff --stat <range>`; `git diff <range>`; `git diff --stat a3dd63f..5a00deb`; `git show da8eb85:erp_ai/agent/knowledge.py`; `git show da8eb85:erp_ai/agent/test_knowledge.py`.

## Kết luận của tech-lead

- Test sau merge (tech-lead, worktree `feat-007` @ `b0358c1`, một lần giữ khóa site, `MIGRATE_EXIT=0`): `erp_ai.agent.test_knowledge` `Ran 39 tests in 1.287s` / `OK`; `erp_ai.tests.test_architecture` `Ran 181 tests in 15.916s` / `OK`.
- Tài liệu thiết kế chưa có hai chữ ký mới: không phải chỗ hở của T123 (dòng task đã ghi "task `search_resolved_tickets` của U6b dùng hai hàm này và mang hai test `test_read.py`") → chuyển team-leader: designer cập nhật `design.md:489` và `design-addendum-1-U6b.md` trước khi task U6b đó được gọi.
- Tick T123: 65/174.

## deferred

- minor: ca ghim `re.IGNORECASE` (`"một<BR>hai"`).
- Cập nhật tài liệu thiết kế của U6b (designer).
