Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 53 — FEAT-004 T53

- Diff: `git diff 7c2a3af..team/FEAT-004-task-53` (head `d50cc3b`, 1 commit; 3 file, +66/-5). Lệnh đã chạy: `git log --oneline 7c2a3af..team/FEAT-004-task-53`, `git diff --stat 7c2a3af..team/FEAT-004-task-53`, `git diff 7c2a3af..team/FEAT-004-task-53`, `git show d50cc3b:<file>` (change_link.py, test_change_link.py, propose_change.py, change_decision.py, erp_ai_change_proposal.js), `git show team/FEAT-004:docs/team/...` (tasks.md, ADR-023, plan.md, spec.md, review-chg001.md)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: khớp T53 Returns và Ràng buộc chung của plan ("Chèn CHG-001"): `change_link.py:29-32` `decision_path` = `FORM_ROUTE/<quote(name, safe='')>?<_signed_query>`, tham số `name`, `action`, `_signature` giữ nguyên; `_signed_query`, `signature_ok` không đổi; `DECIDE_METHOD` giữ (`:13`); không còn chuỗi `/api/method/` trong `change_link.py` (ADR-023 Ràng buộc dòng 59). `propose_change._comment` không cần sửa: đã gọi `decision_path` (`propose_change.py:114-115`) nên comment tự đổi sang đường form; nhãn Duyệt / Từ chối / Xem nội dung thay đổi giữ. Không có phần thừa; chỉ chạm file trong touchpoints.

Test trước mã: `test_change_link.py` `test_decision_path_opens_desk_form_not_api_method` đỏ với mã cũ (RED của dev) và đỏ khi bỏ `quote` (đường dẫn của tên lạ `AICHG/1 ?#&x` khác giá trị viết cứng); `test_module_builds_no_api_method_path` đỏ với nguồn cũ; `test_path_names_the_proposal_the_action_and_a_signature` đổi `PREFIX` theo ADR-023 (đổi vì spec đổi, không phải để khớp hành vi sai — STD-TEST-5 đạt). `test_propose_change.py:183-208` chạy cả 3 tool đề xuất, kiểm đủ 3 nhãn, 3 href khác nhau, liên kết xem = form, 2 liên kết quyết định bắt đầu bằng form và bằng `decision_path(name, action)` — đỏ nếu comment quay về đường API hay mất một liên kết. `test_signature_breaks_when_name_or_action_changes` kiểm đổi tên và đổi `reject`→`approve` như Expect.

Không có blocker hay major.

minor | — | — | 2 điểm nhỏ: (1) STD-DESIGN-4 `propose_change.py:111` vẫn tự viết chuỗi `/app/erp-ai-change-proposal/` trong khi `change_link.FORM_ROUTE` (`change_link.py:14`) giờ là cùng hằng — dùng lại `change_link.FORM_ROUTE`; (2) STD-TEST-8 `test_propose_change.py:194-197` regex chỉ bắt thẻ đúng dạng `<a href="…">`, nên một thẻ `<a>` có thuộc tính khác hay chuỗi `/api/method/` ở chỗ khác trong comment lọt qua kiểm "đúng 3 liên kết" — thêm `assertNotIn("/api/method/", content)` cho cả comment và đếm `content.count("<a ")` | tùy dev

## Review checklist (10)
Đã phủ 10/10.
1. Đúng và đủ task, không thừa (STD-DESIGN-5, STD-TEST-2): đạt.
2. Trong touchpoints, không file mới (STD-DESIGN-1, STD-STRUCT-1/2): đạt.
3. Test đỏ trước; cạnh (tên cần quote, đổi tên/hành động); không skip/xfail (STD-TEST-1/8/4): đạt.
4. Không đổi test để khớp hành vi sai; test độc lập, không phụ thuộc giờ/mạng (STD-TEST-5/6): đạt.
5. Lỗi và kiểm đầu vào (STD-ERR-1/2/5): đạt — `_signed_query` vẫn từ chối tên/hành động sai; không gọi dịch vụ ngoài.
6. Bảo mật (STD-SEC-1/3/4/6): đạt — tên được `quote` trong path, query do `get_signed_params` mã hóa, href được `escape` ở `_comment`; quyền vẫn kiểm ở `decide`/`_decider`; không bí mật.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): đạt — chữ ký ký đúng chuỗi cũ nên `signature_ok` và `test_change_decision` (8 OK theo dev) không đổi; đổi đường dẫn là theo ADR-023.
8. Tên, cấu trúc, style, không mã chết (STD-NAME-1/2, STD-STYLE-4/5): đạt.
9. Không thêm phụ thuộc (`urllib.parse` là thư viện chuẩn) (STD-DEP-1/3/5): đạt.
10. Commit `feat(change-link): … (FEAT-004)`, nhánh `team/FEAT-004-task-53`, không dòng ghi công AI (STD-NAME-4/5, STD-GIT-1/8): đạt.

## Bằng chứng của dev
- RED: `test_decision_path_opens_desk_form_not_api_method`: `AssertionError: False is not true : /api/method/erp_ai.change_decision.decide?name=AICHG-00042&action=approve&_signature=…` (3/6 test của `test_change_link`; 3 subTest của `test_comment_of_each_tool_has_three_links_and_decisions_open_the_form`)
- GREEN: `erp_ai.agent.test_change_link` `Ran 6 tests … OK`; `erp_ai.agent.tools.test_propose_change` `Ran 25 tests … OK`; `erp_ai.test_change_decision` `Ran 8 tests … OK`
- Reviewer không chạy test (site `miyano` dùng chung); gợi ý: `cmd.test_one` cho 3 module trên.

## Không kiểm được từ diff (tech-lead xử lý)
- Thứ tự gộp T53/T54: ở `d50cc3b`, `decide` vẫn `methods=["GET"]` (`change_decision.py:25`) và form JS chưa có lời gọi `decide`; nếu T53 gộp vào `team/FEAT-004` trước T54, bấm Duyệt/Từ chối chỉ mở form, không quyết gì. Docstring `change_link.py:4-5` ("the form then calls `DECIDE_METHOD` by POST") chỉ đúng sau T54. Đề nghị gộp T53 cùng hoặc ngay sau T54.
- Desk có giữ query khi chưa đăng nhập (`/login?redirect-to=…`) và khi router nạp form có sẵn với khóa `name` trong `frappe.route_options` không — thuộc kiểm của T54 (đọc tham số, `replaceState`) và nghiệm thu thủ công trên trình duyệt.
- Mục 8 của plan ("không còn `/api/method/` trong comment") kiểm sau T54 bằng `cmd.test_one` 3 module.

## deferred
- (không có)
