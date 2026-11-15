Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 40 — FEAT-007 T40

- Diff: `git diff 6c231aa..a12dd68` (nhánh `team/FEAT-007-task-40`, 2 commit; BASE `6c231aa` = đầu `team/FEAT-007` sau merge T30); diff sửa vòng 2: `git diff 42f1b45..a12dd68`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng: `git log --oneline 6c231aa..42f1b45`, `git diff --stat 6c231aa..42f1b45`, `git diff 6c231aa..42f1b45`; đọc thêm `git show 6c231aa:erp_ai/test_utils.py`, `git show 6c231aa:erp_ai/hooks.py`, `git show 6c231aa:erp_ai/agent/tools/site_api.py` (`_values_refusal`, `_method_refusal`, `call_method`), `git show 6c231aa:erp_ai/install.py`, cùng mã nguồn Frappe/Helpdesk đã cài (`frappe/model/document.py:502-546, 716-736, 2363-2392`; `frappe/client.py:191-262`; `helpdesk/.../hd_article.py`, `hd_article.json`).
- Range: 1 commit `42f1b45`, 3 file, +169/−0 (28 dòng mã, 137 dòng test, 6 test), đúng 3 file của touchpoints. Commit `feat(agent): … (FEAT-007)`, không trailer.
- Bằng chứng của dev: **không có** (báo cáo của dev mất khi vòng build trước chạm trần lượt). Không có dòng RED/GREEN nào để đối chiếu.
- Lớp 1 (khớp spec): ba nhánh của `design.md:493` có đủ và cùng thứ tự thông báo (bản mới khác `Draft` → `DRAFT_ONLY`; bản cũ không do bot tạo → `NOT_OWN`; bản cũ khác `Draft` → `DRAFT_ONLY`); `on_trash` chặn mọi lần xóa dưới phiên agent; `hooks.py` thêm đúng khối `design.md:346-349`, đặt sau `Comment` (T40 là chủ đầu tiên theo `design-w0-fixes-2.md` 5d). Ba chuỗi lỗi khớp từng chữ. Module chỉ import `erp_ai.constants` (F-1 giữ). Thiếu: mệnh đề "mọi sửa bài không do bot tạo" (ADR-034 QĐ 6) bị vượt được bằng cách gửi kèm `owner` (finding 1).
- Phân tích đột biến từ diff (không chạy được): bỏ kiểm phiên → `test_human_publishes_bot_draft` đỏ (`DRAFT_ONLY`), phần dựng bài `Published` của người trong `test_agent_edit_human_article_refused` cũng đỏ; bỏ mệnh đề owner → hai ca của `test_agent_edit_human_article_refused` đỏ (ca nháp của người chỉ mệnh đề owner chặn được); bỏ mệnh đề trạng thái → `test_agent_publish_refused` đỏ; `!= "Draft"` thành `== "Published"` → subtest `Archived` đỏ; bỏ chặn xóa → `test_agent_delete_refused` đỏ; bỏ dòng hook → `test_hooks_registered` và mọi test chặn đỏ. Mọi phép khẳng định từ chối đều kiểm chữ thông báo (`assertRefused`), nên `PermissionError` của chính Frappe (thiếu quyền) không làm test xanh nhầm. Bỏ `not doc.is_new()` là đột biến tương đương (bản mới luôn có `owner` = người dùng phiên, `document.py:723-727`), không test nào giết được, không cần.

## Phát hiện (chỉ blocker/major)

1. major | STD-SEC-4 | erp_ai/agent/article_guard.py:19 | Mệnh đề "bài không do bot tạo" đọc `doc.owner` trong bộ nhớ, tức giá trị người gọi gửi lên. Frappe chỉ đặt lại `owner` cho bản mới (`frappe/model/document.py:723-727`); khi lưu bản cũ, `db_update` ghi nguyên `owner` trong bộ nhớ (`document.py:2368-2386`). Vì vậy một lần lưu dưới phiên agent kèm `owner = AGENT_USER` qua cả hai mệnh đề: `api_call_method` → `frappe.client.save` với dict có `owner` (hoặc `frappe.client.set_value` với `fieldname` là dict; `_method_refusal` ở `site_api.py:213-219` không chặn) sửa được bài nháp của người, hoặc chuyển bài `Published` của người về `Draft` rồi viết lại, và chiếm luôn quyền sở hữu. Trái ADR-034 QĐ 6 ("mọi sửa bài không do bot tạo"). Không test nào thử trường hợp này | So với chủ sở hữu đã lưu: `before = doc.get_doc_before_save()` (Frappe nạp ở `check_if_latest`, `document.py:530`, trước `validate`) và từ chối khi `before.owner != AGENT_USER` (không có `before` thì `frappe.db.get_value(doc.doctype, doc.name, "owner")`); thêm ca vào `test_agent_edit_human_article_refused`: agent nạp bài nháp của người, đặt `doc.owner = AGENT_USER`, sửa tiêu đề, lưu → `NOT_OWN`, `owner` và `title` đã lưu không đổi | confirmed

minor | — | — | 1 điểm nhỏ: (a) STD-TEST-8: ca agent sửa bài `Published` của người mà giữ `Published` (cả hai mệnh đề cùng đúng) không có test, nên thứ tự thông báo `NOT_OWN` trước `DRAFT_ONLY` không được ghim | tùy dev

## Review checklist (10)
1. chưa đạt (finding 1: QĐ 6 vượt được; ngoài ra đủ và không thừa, phép khẳng định `override_whitelisted_methods` không trỏ `helpdesk.*` trong `test_hooks_registered` là chữ Ràng buộc của ADR-034) 2. đạt (3 file đúng touchpoints, file mới trong `erp_ai/`, test cạnh mã) 3. không kiểm được phần "test đỏ trước" (không có RED; từ diff, 4/6 test sẽ đỏ đúng lý do khi thiếu guard, 2 test còn lại là ca đối chứng đường đúng); ca lỗi/biên có (Archived, `ignore_permissions`, xóa có/không `ignore_permissions`, người vẫn xóa được nháp của bot); không skip/xfail; thiếu ca giả `owner` (finding 1) 4. đạt (không test cũ nào bị sửa; `keep_agent_settings`, `pin_agent_roles` sau `addCleanup(rollback)`, chặn `commit`, tiêu đề ngẫu nhiên; không dùng đồng hồ) 5. đạt (`frappe.throw(..., frappe.PermissionError)`, không nuốt lỗi, không gọi ngoài) 6. chưa đạt (finding 1, STD-SEC-4) 7. đạt (chỉ thêm khóa `HD Article` vào `doc_events`, không đổi hợp đồng có sẵn) 8. đạt (tên theo profile, hằng UPPER_SNAKE, không mã chết) 9. đạt (không thêm) 10. đạt (`feat(agent): … (FEAT-007)`, không trailer; tài liệu người dùng thuộc `/team:asbuilt`)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| STD-TEST-1/STD-TEST-3: không có dòng RED/GREEN của dev. Từ diff chỉ lập luận được rằng 4/6 test đỏ đúng lý do khi thiếu guard; chưa ai thấy chúng đỏ thật và xanh thật. Cần `cmd.migrate` rồi `cmd.test_one` cho `erp_ai/agent/test_article_guard.py` và `erp_ai/tests/test_architecture.py` sau khi sửa finding 1 | |
| Test chèn/xóa HD Article dưới `AGENT_USER` **không** `ignore_permissions`: cần role `Agent` có `create/write/delete` trên HD Article (`hd_article.json` chuẩn có; `pin_agent_roles` ghim {ERP AI Agent, Agent}). Khi T60 ("T22a") cài Custom DocPerm cho HD Article, quyền của Agent phải còn nguyên, nếu không các test này đỏ vì `PermissionError` của Frappe (chữ khác) | |
| `frappe.get_hooks("doc_events", app_name="erp_ai")` trả `{"validate": [..], "on_trash": [..]}` dạng danh sách như `test_hooks_registered` khẳng định — chỉ xác nhận được khi chạy | |
| `test_architecture.py` có luật nào quét `hooks.py` hay module mới dưới `erp_ai/agent/` (ví dụ `test_hooks_have_no_page_injection`) mà khối mới vi phạm không — chỉ xác nhận được khi chạy | |

## Vòng 2 — approve

- Lệnh đã dùng: `git log --oneline 6c231aa..a12dd68`, `git diff --stat 42f1b45..a12dd68`, `git diff 42f1b45..a12dd68`, `git diff --stat 6c231aa..a12dd68`, `git show -s a12dd68`, `git show a12dd68:erp_ai/agent/test_article_guard.py` (helper `_stored`, `assertRefused`), `git show a12dd68:erp_ai/agent/article_guard.py`; đọc mã Frappe đã cài để đối chiếu dòng RED: `frappe/model/document.py:502-546` (`_save`), `:746-776` (`_validate` → `validate_set_only_once`), `:822-848`, `:995-1007` (`check_if_latest` → `load_doc_before_save`), `:1305-1314`; `frappe/model/meta.py:114-117, 200-210` (`standard_set_once_fields` gồm `owner`).
- Range sửa: 1 commit `a12dd68` `fix(agent): … (FEAT-007)`, không trailer; 2 file, +31/−1, nằm trong touchpoints. Cả task: 3 file, +199/−0, đúng 3 touchpoints.
- Bằng chứng của dev (trong gói): RED `test_agent_spoofed_owner_refused` → `ERROR` tại `assertRefused` với `CannotChangeConstantError: Value cannot be changed for Created By`, `Ran 7 tests`, `FAILED (errors=1)`; GREEN `test_article_guard` `Ran 7 tests … OK`, `test_architecture` `Ran 112 tests … OK`.

### Finding vòng 1

1. major | STD-SEC-4 | erp_ai/agent/article_guard.py:19 — **ADDRESSED** (`erp_ai/agent/article_guard.py:19, 26-31`; test `erp_ai/agent/test_article_guard.py:103-123`). Mệnh đề owner giờ đọc `_stored_owner(doc)`: `get_doc_before_save()` (Frappe nạp từ DB trong `check_if_latest`, trước hook `validate`), không có thì `frappe.db.get_value(..., "owner")`. Test mới phủ đúng ca đã yêu cầu (nháp của người, `doc.owner = AGENT_USER`, sửa tiêu đề → `NOT_OWN`, `owner` và `title` đã lưu không đổi) và thêm ca bài `Published` của người bị kéo về `Draft` kèm `ignore_permissions` → `NOT_OWN`, `owner`/`status` đã lưu không đổi. Đột biến quay về `doc.owner` → cả hai ca đổi sang `CannotChangeConstantError` (không phải `PermissionError`), `assertRefused` báo lỗi; dòng RED của dev khớp đúng điều đó.
   - Đính chính vòng 1: dòng RED cho thấy Frappe vốn đã từ chối đổi `owner` của bản cũ — `owner` nằm trong `standard_set_once_fields` (`meta.py:114-117`), và `_validate` → `validate_set_only_once` (`document.py:776, 822-848`) chạy sau hook `validate`, trước `db_update`. Đường khai thác "sửa được bài của người và chiếm quyền sở hữu" ở vòng 1 vì vậy **không xảy ra** trên bản Frappe đang cài; độ chắc chắn `confirmed` của vòng 1 là sai, mức thật là thiếu phòng thủ trong guard (guard để lọt, chặn nhờ cơ chế khác của Frappe với thông báo khác). Bản sửa vẫn đúng hướng: lời từ chối của QĐ 6 nay do chính guard đưa ra, không phụ thuộc thứ tự nội bộ của Frappe.

### Phát hiện mới (chỉ blocker/major)

Không có.

minor | — | — | 1 điểm nhỏ: (a) STD-TEST-8: nhánh dự phòng `frappe.db.get_value(...)` của `_stored_owner` (`article_guard.py:31`) không test nào chạm tới — trên đường `save` Frappe luôn nạp `_doc_before_save` trước `validate`, nên nhánh này chỉ chạy khi hook được gọi ngoài `save`; ca `NOT_OWN` trước `DRAFT_ONLY` (minor vòng 1) vẫn chưa ghim | tùy dev

### Review checklist (10) — vòng 2, trong phạm vi bản sửa

1. đạt (QĐ 6 không còn vượt được ở tầng guard; không thêm gì ngoài yêu cầu) 2. đạt (2 file trong touchpoints, không file mới) 3. đạt (RED đúng lý do có trong gói, rồi GREEN; ca biên `Published` → `Draft` + `ignore_permissions`; không skip/xfail) 4. đạt (không sửa test cũ; test mới dùng cùng `setUp` cô lập, rollback, chặn `commit`) 5. đạt (`frappe.throw(..., frappe.PermissionError)`, không nuốt lỗi) 6. đạt (STD-SEC-4: chủ sở hữu lấy từ DB, không từ dữ liệu người gọi) 7. đạt (không đổi hợp đồng; hàm mới là private `_stored_owner`) 8. đạt (tên rõ nghĩa, docstring đúng hành vi, không mã chết ngoài nhánh dự phòng nêu ở minor) 9. đạt (không thêm phụ thuộc) 10. đạt (`fix(agent): … (FEAT-007)`, không trailer; thông điệp commit mô tả đúng mã)

### Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| STD-TEST-3: GREEN của dev chạy trên nhánh task; sau merge vào `team/FEAT-007` cần chạy lại `cmd.migrate` rồi `cmd.test_one` cho `erp_ai/agent/test_article_guard.py` và `erp_ai/tests/test_architecture.py` (site dùng chung, reviewer không chạy) | |
| Ba mục vòng 1 còn mở (quyền `create/write/delete` của role `Agent` trên HD Article khi T60 cài Custom DocPerm; dạng trả về của `frappe.get_hooks("doc_events", ...)`; luật quét của `test_architecture.py`): GREEN của dev cho thấy đạt trên site hiện tại, cần giữ khi T60 merge | |
