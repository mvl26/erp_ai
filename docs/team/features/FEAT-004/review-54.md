Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 54 — FEAT-004 T54

- Diff: `team/FEAT-004-task-54` (head 95493ec), dải `7c2a3af..team/FEAT-004-task-54`, 2 commit, 4 file
- Vòng: 1
- Verdict: request-changes

Lệnh đã dùng (chỉ đọc):
```
git log --oneline 7c2a3af..team/FEAT-004-task-54
git diff --stat 7c2a3af..team/FEAT-004-task-54
git diff 7c2a3af..team/FEAT-004-task-54
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T54'
git show team/FEAT-004-task-54:erp_ai/agent/run_log.py | grep -n commit
git show team/FEAT-004-task-54:erp_ai/agent/change_link.py | grep -n -A14 'def signature_ok'
git show team/FEAT-004-task-54:erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py (`_decider`, `approve`, `reject`)
```
Nguồn Frappe 15 đã đọc: `frappe/app.py:451-465` (`sync_database`), `frappe/handler.py:99-110` (`is_valid_http_method`), `frappe/permissions.py:510-545` (`get_roles`, cache `roles`), `frappe/cache_manager.py:80-95` (`clear_user_cache`), `frappe/__init__.py:1237-1248` (`clear_document_cache`).

## Lớp 1 — khớp spec
- AC-5, AC-25, AC-26 (theo M1), NFR-10, ADR-023 QĐ 1 và "Test M1": đạt. `decide` chỉ POST, không `allow_guest`, trả `{"ok": True, "status": …}`; chữ ký sai, `action` lạ → `PermissionError(BAD_LINK)` trước khi ghi; bỏ `respond_as_web_page`, chuyển hướng, `PAGE_TITLE`. JS: `decide_from_link` chạy ở `refresh`, xóa tham số trước (mọi trạng thái), chỉ gọi khi "Chờ duyệt", đúng 1 `frappe.call` POST, không `frappe.confirm`, rồi `frm.reload_doc()`; 3 nút cũ không đổi.
- Đủ 7 test có tên trong Expect. Không thiếu, không thừa; touchpoint đúng (sửa `test_erp_ai_change_proposal.py` chỉ trong `test_form_script_static_rules`, theo phán quyết của chủ plan).

## Phát hiện cũ (review-chg001 nhóm F)
| Phát hiện | Trạng thái | Bằng chứng |
|---|---|---|
| blocker STD-ERR-7 `change_decision.py:122-136` (GET bị rollback cuối request, mất job) | ADDRESSED | `erp_ai/change_decision.py:20` `methods=["POST"]` → `sync_database` commit (`app.py:453`); `test_change_decision.py:189-207` chạy `sync_database` thật, đếm 0 job trước, 1 job và 1 COMMIT sau |
| blocker STD-SEC-4 `change_decision.py:122` (GET đổi trạng thái, không CSRF) | ADDRESSED | `change_decision.py:20` chỉ POST; `test_change_decision.py:155-164` GET qua `frappe.handler.execute_cmd` → "Not permitted", không ghi; form gọi qua `frappe.call` (mang token phiên) |
| major STD-TEST-2 `test_change_decision.py:173-175,210-223` (đếm trên `frappe.enqueue` đã patch) | ADDRESSED | `test_change_decision.py:72-77` chỉ stub `get_queue`/`get_job`, `frappe.enqueue` thật; `:189-207` đếm `enqueue_call` sau `sync_database` |
| major STD-TEST-8 `test_change_decision.py:247-251` (thiếu loại tài khoản) | ADDRESSED | `test_change_decision.py:234-258`: agent (có role, chỉ `NEVER_AUTHORITY` chặn), Administrator, Guest, không role, người được giao phiếu (`is_instruction` đúng), người tạo phiếu; mỗi ca kiểm đúng câu lỗi, trạng thái, số dòng nhật ký, 0 job |

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-6 | erp_ai/test_change_decision.py:237 | `add_roles(ROLE_INSTRUCTOR)` trên tài khoản agent thật của site; `User.on_update` xóa cache rồi `frappe.get_roles(AGENT_USER)` (dòng 238 và trong `_decider`) nạp lại hash Redis `roles` có "ERP AI Instructor" (`permissions.py:538`); `clear_user_cache` không đăng ký `after_rollback` (`cache_manager.py:80-95`), nên sau `frappe.db.rollback` tài khoản bot trên site dùng chung vẫn mang role trong cache tới lần xóa cache sau → test sau phụ thuộc thứ tự, quyền của bot trên site dev bị đổi. Confirmed (cơ chế đọc trong nguồn Frappe; chưa chạy) | `self.addCleanup(frappe.clear_cache, user=AGENT_USER)` ngay sau `add_roles` (chạy trước rollback của setUp theo LIFO, không có `get_roles` nào giữa hai bước), hoặc thêm `self.addCleanup(frappe.cache.hdel, "roles", AGENT_USER)` đăng ký trước `frappe.db.rollback` để chạy sau nó; một dòng kiểm sau cleanup nếu muốn chốt |

minor | — | — | 3 điểm nhỏ: docstring `decide` (`change_decision.py:21-27`, STD-DOC-7) chỉ nêu `PermissionError`, thiếu `ValidationError` khi trạng thái không còn "Chờ duyệt" (lần bấm lại) và `DoesNotExistError` của `_decider`; `test_form_script_posts_once_without_confirm_and_strips_params` lặp gần nguyên ghim tĩnh của subTest mới trong `test_erp_ai_change_proposal.py:972-982`; `end_request` gọi `frappe.db.commit()` thật nên `after_rollback` đăng ký trước đó trong test bị `reset` (cache tài liệu của đề xuất có thể còn sau rollback, nghi vấn) | tùy dev

## Review checklist (10)
1. Đúng và đủ spec, không thừa (STD-DESIGN-5, STD-TEST-2): đạt.
2. Touchpoint, nơi đặt file (STD-DESIGN-1, STD-STRUCT-1/2): đạt; không file mới.
3. Test đỏ trước, cạnh và nhánh lỗi, không skip (STD-TEST-1/8/4): đạt; RED/GREEN của cả hai commit có trong gói; GET, chữ ký sai/rỗng/đổi `action`/đổi `name`, `action` lạ, bấm lại, 6 loại tài khoản. Các test sẽ đỏ nếu bỏ hành vi: `methods` thêm GET → GET duyệt được; bỏ `enqueue_after_commit` → job có trước `sync_database`; bỏ `NEVER_AUTHORITY` → agent có role duyệt được; JS đổi thứ tự `replaceState`/gọi → `assertLess`. Vế `action not in DECIDERS` bị che bởi `signature_ok` (`change_link.py:22-23,38`) nhưng `signature_ok` tự chặn `action` lạ, không mất hành vi.
4. Không sửa test cho khớp hành vi sai; độc lập, lặp lại được (STD-TEST-5/6): trượt STD-TEST-6 (cache role của tài khoản agent rò sau rollback). Sửa test cũ là do spec đổi (M1), đúng STD-TEST-5; đếm `frappe.call(` toàn file chuyển thành đếm trong helper + 1 ngoài helper, tổng vẫn ghim là 2.
5. Lỗi, kiểm đầu vào ở biên (STD-ERR-1/2/5): đạt; bỏ `except` nuốt lỗi cũ, lỗi lên `frappe.call`; request POST có ngoại lệ thì Frappe rollback.
6. Bảo mật (STD-SEC-1/3/4/6): đạt; POST + CSRF + role ở server, chữ ký so thời gian hằng, không `allow_guest`.
7. Hợp đồng API (STD-DESIGN-3, STD-OPS-2): đạt; đổi GET → POST là thay đổi do ADR-023 QĐ 1 yêu cầu, đường dẫn trong comment do T53 lo.
8. Tên, cấu trúc, style, không mã chết (STD-NAME-1/2, STD-STYLE-4/5): đạt; import `PROPOSAL_DOCTYPE` thừa đã bỏ.
9. Phụ thuộc mới (STD-DEP-1/3/5): không có (`werkzeug` đã đi kèm Frappe).
10. Commit, nhánh, tài liệu (STD-NAME-4/5, STD-GIT-1, STD-DOC-2): đạt; 2 commit `feat(...)/test(...) … (FEAT-004)`, nhánh `team/FEAT-004-task-54`.

## Không kiểm được từ diff
- Hành vi thật trên Desk: router Frappe 15 có giữ `?name=…&action=…&_signature=…` trong `window.location.search` khi mở `/app/erp-ai-change-proposal/<name>` hay không, và `refresh` có chạy trước khi router dọn query → cần chạy tay hoặc Playwright (tech-lead).
- Token CSRF: test gọi `execute_cmd` trực tiếp, không qua `frappe/auth.py` `validate_csrf_token`; chỉ suy ra từ việc `frappe.call` gửi `X-Frappe-CSRF-Token`.
- Ghép với T53 (đã merge vào `team/FEAT-004` sau base 7c2a3af): test mới dùng `change_link._signed_query`; kiểm xung đột merge và rằng `decision_path` của T53 dẫn tới đúng form mà `decide_from_link` đọc.
- Trong request thật `run_log.write_entry` commit giữa chừng (`run_log.py:55-56`, tắt khi `in_test`): nếu `get_queue` lỗi (Redis tắt) ở `enqueue_change_job` sau commit đó, đề xuất kẹt "Đã duyệt"; mã controller ngoài diff, đường nút form cũng vậy.

## Deferred
- Không có (vòng 1).

Test không chạy (site dùng chung). Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.test_change_decision`, rồi `--module erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.test_erp_ai_change_proposal`.
