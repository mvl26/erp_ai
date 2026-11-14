Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 59 — FEAT-004 T59

- Diff: `git diff 7c2a3af..team/FEAT-004-task-59-r2` (head 8eebed8; 2 commit: 9ce5239 `site_api.py` + test, 8eebed8 luật kiến trúc; 3 file, +540 −55)
- Lệnh đã chạy (chỉ đọc): `git log --oneline 7c2a3af..team/FEAT-004-task-59-r2`, `git diff --stat 7c2a3af..team/FEAT-004-task-59-r2`, `git diff 7c2a3af..team/FEAT-004-task-59-r2 -- erp_ai/agent/tools/site_api.py erp_ai/agent/tools/test_site_api.py`, `git diff 7c2a3af..team/FEAT-004-task-59-r2 -- erp_ai/tests/test_architecture.py`, `git show team/FEAT-004-task-59-r2:erp_ai/{modules.txt,agent/tools/read.py,agent/tools/site_api.py,agent/tools/test_site_api.py}`, `git show team/FEAT-004:docs/team/{features/FEAT-004/tasks.md,features/FEAT-004/review-chg001.md,features/FEAT-004/spec.md,adr/ADR-023.md}`
- Vòng: 1
- Verdict: request-changes

## Lớp 1 — khớp spec
- Missing: không. `always_denied_doctypes()` = mọi DocType của `read.AI_MODULE`, tính lúc gọi (`modules.txt` chỉ có một module "ERP AI agent"); chế độ thường = `(read.denied_doctypes() − {"User"}) ∪ {"Custom Role", "Custom DocPerm", "DocType", "Role"}` đúng từng chữ của T59; mọi `api_*` tra tên DocType đang lưu trước khi so; role (kể cả trong Role Profile) và user tra tên đang lưu rồi so `casefold`; lời từ chối giữ "không được phép". Đủ 4 test của Expect, test cũ `:164-166` đã kiểm lý do và dùng DocType có thật.
- Extra: `test_architecture.py` thay nhánh `SITE_API_DENY_SETS` bằng luật "cổng cấm dẫn xuất trước mọi lệnh ghi" và chuyển các ca fixture chung từ `site_api.py` sang `cleanup.py`/`write_any.py`; nằm trong phần của `check_tool_never_saves_proposal` mà plan owner cho phép (2026-11-14). Không có file ngoài touchpoint.
- Misunderstood: không.

## Phán các phát hiện review-chg001 nhóm G thuộc T59
| Phát hiện cũ | Kết quả | Chỗ |
|---|---|---|
| blocker STD-SEC-4 `site_api.py:62,118,159` | ADDRESSED về hành vi (`site_api.py:79`, `:136-137`, `:178`; `_stored_name` ở `:66-70` cho DocType tại `:160,172,202,218,263,293`); phần test của lớp tra tên đang lưu còn hở, xem major dưới | `site_api.py:53-79,136,178` |
| major STD-DESIGN-2 `site_api.py:32-34` | ADDRESSED: hết tập viết tay, `PERMISSION_DOCTYPES` thêm `DocType`, `Role`; test M3 `test_normal_mode_denies_doctype_and_role_records` đổi `_write` thành mock và `assert_not_called` (bỏ một tên khỏi tập → mock trả MagicMock truthy → đỏ) | `site_api.py:23-26,53-63`; `test_site_api.py:234-246` |
| major STD-TEST-5 `test_site_api.py:164-166` | ADDRESSED: thêm `assertIn("không được phép", …)` và `assertTrue(frappe.db.exists("DocType", …))`; bỏ "Role Permission" (không phải DocType) | `test_site_api.py:202-206` |

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/tools/test_site_api.py:248-346 (che `site_api.py:136`, `:178`) | Lớp tra tên đang lưu cho role và user không có test nào bắt được: mọi ca chỉ dùng chữ thường/chữ hoa, `casefold` một mình đã chặn. Xóa `_stored_name(ROLE_DOCTYPE, …)` ở `:136` hoặc `_stored_name(USER_DOCTYPE, …)` ở `:178` → toàn bộ test vẫn xanh (confirmed bằng đọc mã: `_named_in` casefold vẫn khớp `"system manager"`, `"administrator"`, `AGENT.upper()`). Nhưng đó là lớp chịu tải của blocker STD-SEC-4: MariaDB `utf8mb4_unicode_ci` khớp tên bỏ khoảng trắng cuối và không phân biệt dấu, `casefold` thì không (`"System Manager "`, `"Administrator "` qua được casefold rồi Frappe sửa link thành tên đang lưu — suspected, chưa chạy) | thêm subTest có tên mà `casefold` không khớp nhưng DB khớp (ví dụ role `"System Manager "`, user `"Administrator "` có khoảng trắng cuối) và assert từ chối; kiểm lại test đỏ khi bỏ `_stored_name` |

minor | — | — | 2 điểm nhỏ: commit 9ce5239 để `test_architecture` đỏ (luật cũ đòi `DENIED_DOCTYPES` — chính RED 1 của commit 2), trái STD-GIT-2 "mỗi commit qua test"; ca "role profile of a user" (`PROFILE.lower()`) xanh cả với mã cũ vì `frappe.db.exists`/`get_doc` vốn không phân biệt hoa thường, nên không ghim thay đổi ở `_profile_roles` (`site_api.py:101-105`) | tùy dev

## Review checklist (10)
1. Đúng và đủ spec, không thừa — đạt (STD-DESIGN-5, STD-TEST-2).
2. Trong touchpoint, không file mới — đạt (STD-DESIGN-1, STD-STRUCT-1).
3. Test đỏ trước (RED commit 1: `'không được phép' not found in 'hệ thống từ chối: Note Note not found'`, `True is not false` cho `"system manager"`; RED commit 2: luật cũ + 16 ca "scanner missed"); không skip/xfail; cạnh và nhánh lỗi — trượt một phần (STD-TEST-8, major ở trên).
4. Không sửa test cho khớp hành vi sai; test độc lập (setUp `addCleanup(frappe.db.rollback)`, `patch.object` có phạm vi) — đạt (STD-TEST-5, STD-TEST-6). Test cũ chỉ được làm chặt hơn.
5. Lỗi và đầu vào: `_stored_name` chặn giá trị không phải `str` trước `frappe.db.get_value` (không biến dict thành bộ lọc) — đạt (STD-ERR-1, STD-ERR-2); `_write` thuộc T60.
6. Bảo mật: so tên DocType/role/user không còn phân biệt hoa thường; `get_value` tham số hóa — đạt về hành vi (STD-SEC-4, STD-SEC-3); `_method_refusal` vẫn so chuỗi phân biệt hoa thường (`site_api.py:236`) là phạm vi T61 (blocker `:213-219`), không tính ở đây.
7. Hợp đồng: bỏ hằng `DENIED_DOCTYPES`/`ALWAYS_DENIED_DOCTYPES` khỏi `site_api` — không thấy nơi khác dùng trong diff, luật kiến trúc đã đổi theo; không migration — đạt (STD-DESIGN-3).
8. Tên, cấu trúc, style, không mã chết — đạt (STD-NAME-2, STD-STYLE-5).
9. Không thêm phụ thuộc — đạt (STD-DEP-1).
10. Nhánh `team/FEAT-004-task-59-r2`, commit `type(scope): … (FEAT-004)` — đạt (STD-NAME-4, STD-NAME-5); STD-GIT-2 xem minor.

## Không kiểm được từ diff (tech-lead xử lý)
- Có module nào ngoài `erp_ai/**` import `site_api.DENIED_DOCTYPES` / `ALWAYS_DENIED_DOCTYPES` (đã bị xóa) không: diff chỉ đổi 3 file; cần `git grep -n 'ALWAYS_DENIED_DOCTYPES\|site_api.DENIED_DOCTYPES' team/FEAT-004-task-59-r2` (GREEN `test_architecture`/`test_site_api` của dev không phủ cả app). Tests không chạy (site dùng chung); đề xuất `cmd.test_one erp_ai/agent/tools/test_site_api.py` và `erp_ai/tests/test_architecture.py`.
- Frappe có sửa link role `"System Manager "` (khoảng trắng cuối) thành tên đang lưu khi lưu `Has Role` không: chỉ chạy trên site mới xác nhận được (nền của major STD-TEST-8).
- Chi phí: `always_denied_doctypes()` và `read.denied_doctypes()` mỗi lần gọi tool là một truy vấn `DocType` (đúng "tính lúc gọi" của spec); không đo được từ diff.

## deferred
- `_method_refusal` (`site_api.py:232-237`) so tên DocType phân biệt hoa thường, trên JSON ngoài cùng → T61 (đã ghi trong task).
- `_write` chỉ bắt hai loại lỗi → T60.
