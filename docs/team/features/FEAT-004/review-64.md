Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 64 — FEAT-004 T64

- Diff: `git diff 2108dd2..team/FEAT-004-task-64` (head 8a3d963, 1 commit, 2 file: `erp_ai/agent/runner.py` +13/-1, `erp_ai/agent/test_agent_runner.py` +244/-4)
- Lệnh đã chạy (chỉ đọc): `git log --oneline 2108dd2..team/FEAT-004-task-64`, `git diff --stat ...`, `git diff ...`, `git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -A5 T64`, `git show team/FEAT-004-task-64:<file> | grep/sed` cho `runner.py`, `run_log.py`, `tools/site_api.py`, `erp_ai_log.json`, `git show team/FEAT-004:.../spec.md|plan.md | grep`
- Vòng: 2 (vòng 1: request-changes)
- Verdict: approve (vòng 2)

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | erp_ai/agent/test_agent_runner.py:1388 (dùng ở :1418); mã ở erp_ai/agent/runner.py:715 | Giá trị "người ra lệnh" trong test là `INSTRUCTOR = "Administrator"`, trùng với `frappe.session.user` trong test (`RunnerTestBase` đặt Administrator, `_run` vá `frappe.set_user` ở :139 nên runner không chuyển sang `AGENT_USER`). Nếu đổi runner.py:715 thành `frappe.session.user` (khi chạy thật là tài khoản agent) hoặc hằng `"Administrator"`, cả 3 test mới và 3 test cũ đã sửa vẫn xanh. Phần "người ra lệnh" của AC-35 vì vậy không có test nào có thể đỏ. confirmed (suy từ diff + :139) | Vá `latest_instructor` trả về một user riêng khác Administrator (tạo trong test, cấp đủ vai trò mà L3/Toàn quyền đòi, như cách `_call(instructor=...)` ở :1621 nhận tham số) và so `action["instructor"]` với user đó |

minor | — | — | 3 điểm nhỏ: (1) AC-35 nêu "submit/hủy" nhưng test chỉ có ca `action="submit"`, chưa có ca `cancel` (runner chỉ chép nên rủi ro thấp); (2) nhánh `outcome if ok else {}` ở runner.py:712 không test nào phân biệt với `outcome or {}` vì kết quả từ chối của `site_api` (`_refuse`, :73) không có `value_before` — vô hại nhưng không được ghim; (3) `assertIn("value_before"/"value_after", action)` ở test bí mật thừa so với dòng `assertEqual(action["value_before"]["first_name"], ...)` ngay sau | tùy dev

## Lớp 1 — khớp spec
- AC-35: mục hành động của 5 tool `api_*` có `value_before`, `value_after` lấy nguyên từ kết quả tool (runner không đọc lại bản ghi; ca xóa so với `result["value_before"]` và bản ghi đã mất), `instructor` từ `context.instructor`. Đủ, trừ phần test người ra lệnh (major trên).
- AC-34 / NFR-11: 3 lời gọi (từ chối, từ chối, sập) → đúng 3 mục, cả hai khóa giá trị là `None`; đường sập đi qua `_action(name, context, None, False, arguments)` (runner.py:673) nên `written = {}` không lỗi `None.get`.
- Bí mật: test gieo `new_password`/`api_secret` giả vào User, nâng `DELETED_FIELDS_MAX` để chỉ bộ lọc bí mật chặn, xác nhận đã gieo (`planted`) và đếm 0 trong cột `actions`. Bộ lọc là của T62; runner chỉ chép.
- Không thừa: chỉ 2 file đúng touchpoint; khóa đúng tên `value_before`, `value_after` theo plan "Chèn CHG-001".

## Review checklist (10)
1. Đúng và đủ phạm vi, không thêm: đạt (STD-DESIGN-5); test phủ tiêu chí: trượt một phần — người ra lệnh (STD-TEST-5, major).
2. Trong touchpoint, không file mới: đạt (STD-DESIGN-1, STD-STRUCT-1).
3. RED trước (dòng `AssertionError: 'value_before' not found ...` có trong gói), có ca từ chối/sập, không skip/xfail: đạt (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. 3 test cũ chỉ thêm 3 khóa mới vào dict mong đợi, không nới assertion cũ: đạt (STD-TEST-5 phần này); độc lập: mỗi subTest xóa log của phiếu trước khi chạy, dùng tên `PREFIX`: đạt (STD-TEST-6).
5. Lỗi: đường sập/từ chối không làm `_action` sập: đạt (STD-ERR-1); không có đầu vào biên mới.
6. Không bí mật, không truy vấn ghép chuỗi; giá trị đã lọc bí mật ở T62 và có test gieo khóa giả: đạt (STD-SEC-1, STD-SEC-6).
7. Hợp đồng: mục hành động chỉ thêm khóa, khóa cũ giữ nguyên: đạt (STD-DESIGN-3). Kích thước cột: xem "không kiểm được từ diff".
8. Tên `RECORD_TOOLS` theo `naming.constant`, comment đúng hành vi, không mã chết: đạt (STD-NAME-2, STD-STYLE-5).
9. Không phụ thuộc mới: đạt (STD-DEP-1).
10. Commit `feat(runner): ... (FEAT-004)`, nhánh `team/FEAT-004-task-64`, 1 commit riêng: đạt (STD-NAME-5, STD-NAME-4, STD-GIT-1); tài liệu người dùng: không đổi hành vi hiển thị (STD-DOC-2).

## Không kiểm được từ diff
- Cột `ERP AI Log.actions` là `Small Text` (MariaDB `text`, 64 KB). Mỗi mục xóa giờ mang tới `DELETED_FIELDS_MAX`=20 trường × `VALUE_MAX`=200 ký tự (UTF-8 tiếng Việt tới ~3 byte/ký tự) ≈ 4–12 KB; một lượt model có nhiều lời gọi xóa/sửa có thể vượt 64 KB → `write_entry` lỗi "Data too long" ở chế độ strict, mất cả dòng nhật ký. Không thấy trong diff giới hạn số lời gọi mỗi lượt hay cách `write_entry` xử lý lỗi này → tech-lead/designer xem có cần đổi cột sang `Long Text` (ngoài touchpoint T64) hay chặn kích thước. suspected.
- Test không chạy lại (site dùng chung). Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.test_agent_runner`.

## Deferred
- Không có (vòng 1).

## Vòng 2

- Diff sửa: `git diff 8a3d963..team/FEAT-004-task-64` (head 59ab285, 1 commit `test(runner): record tool actions name a real instructor user, not the session user (FEAT-004)`, 1 file: `erp_ai/agent/test_agent_runner.py` +30/-9)
- Lệnh đã chạy (chỉ đọc): `git log --oneline 8a3d963..team/FEAT-004-task-64`, `git diff --stat 8a3d963..team/FEAT-004-task-64`, `git diff 8a3d963..team/FEAT-004-task-64`
- Verdict: approve

### Phát hiện vòng 1
| Phát hiện | Trạng thái | Bằng chứng |
|---|---|---|
| major STD-TEST-5 — người ra lệnh trong test trùng `frappe.session.user` (`"Administrator"`) | ADDRESSED | `test_agent_runner.py:1157` `INSTRUCTOR = "runner.instructor@example.com"` (hằng cũ `"Administrator"` bị xóa ở dòng cũ :1388); `make_instructor` (:1160–1172) tạo user có vai trò `ROLE_INSTRUCTOR` trong giao dịch test, dọn bằng rollback rồi `frappe.clear_cache(user=INSTRUCTOR)`; dùng ở 3 test `TestRunnerSiteAdminTools` (:1247, :1339, :1381) và `setUp` của `TestRunnerRecordToolValues` (:1422); `latest_instructor` vá trả `INSTRUCTOR`, dict mong đợi so `"instructor": INSTRUCTOR`. Giá trị mong đợi giờ khác cả Administrator (người dùng phiên test) lẫn `AGENT_USER` (người dùng phiên khi runner chạy), nên đổi runner.py:715 sang `frappe.session.user` hoặc hằng `"Administrator"` đều làm test đỏ. Gói có dòng RED: `Ran 6 tests … FAILED (failures=9)`, `- 'instructor': 'ai.agent@miyano.com.vn'` / `+ 'instructor': 'runner.instructor@example.com'`. |

### Phát hiện mới (chỉ blocker/major)
- Không có.

minor | — | — | 1 điểm nhỏ: comment ở :1156 nói lý do là "session user in these tests is Administrator", trong khi dòng RED cho thấy lúc runner chạy phiên là `ai.agent@miyano.com.vn`; lý do đúng là user này phải khác cả hai | tùy dev

### Review checklist (10) — chỉ trong diff sửa
1. Đúng phạm vi phát hiện, không thêm hành vi: đạt (STD-DESIGN-5); phần người ra lệnh của AC-35 giờ có test có thể đỏ: đạt (STD-TEST-2).
2. Chỉ sửa file test trong touchpoint, không file mới: đạt (STD-DESIGN-1, STD-STRUCT-1).
3. Có RED với đột biến runner.py:715 trước khi xanh; không skip/xfail: đạt (STD-TEST-1, STD-TEST-4).
4. Không nới assertion; chỉ thay giá trị mong đợi bằng user riêng. Độc lập: user tạo trong giao dịch test và rollback; GREEN `Ran 78 tests` với 6 test cùng gọi `make_instructor` không lỗi trùng khóa, nên user không bị commit sót giữa các test: đạt (STD-TEST-5, STD-TEST-6). 3 lỗi còn lại là nhiễu cài đặt site `auto_assign_enabled=1` đã biết, ngoài phạm vi vòng này.
5. Không có đường lỗi mới: không áp dụng (STD-ERR-1).
6. Không bí mật; email `example.com`, `send_welcome_email: 0`: đạt (STD-SEC-1, STD-SEC-6).
7. Không đổi hợp đồng mã sản phẩm: đạt (STD-DESIGN-3).
8. `INSTRUCTOR`, `make_instructor` theo `naming.constant`/`naming.function`; hằng cũ bị xóa, không mã chết: đạt (STD-NAME-2, STD-STYLE-5).
9. Không phụ thuộc mới: đạt (STD-DEP-1).
10. Commit `test(runner): ... (FEAT-004)` trên `team/FEAT-004-task-64`: đạt (STD-NAME-5, STD-NAME-4, STD-GIT-1); không đổi hành vi người dùng (STD-DOC-2).

### Deferred
- Không có ngoài mục "Không kiểm được từ diff" của vòng 1 (cỡ cột `ERP AI Log.actions`), vẫn chờ tech-lead.
- Test không chạy lại (site dùng chung, đang có merge check). Gợi ý: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.test_agent_runner`.

### Sau merge (tech-lead, 2026-11-14 chặng 10)
- Merge `353018a` (sau T61 `c2762a1`, T62 `8a2a5ef`, sửa ghép `c9abee1`). test_agent_runner với cài đặt site đang lưu: `Ran 78 tests in 34.637s` / `FAILED (failures=3)`, ba ca `TestRunnerL1Classification` (nhiễu `auto_assign_enabled=1`, không ca nào của T64); với hai cài đặt tạm để trống: `Ran 78 tests in 22.463s` / `OK`.
- Phán mục cỡ cột `ERP AI Log.actions` (suspected, chưa tái hiện): sửa đòi đổi kiểu cột hoặc chặn kích thước ở runner, ngoài touchpoint T64 và là quyết định thiết kế → không chặn tick; chuyển team-leader/designer như lo ngại mở, qa thử ở verify (AC-34).

## Sửa lại sau nghiệm thu (2026-11-14, chặng 11) — F-1 của `acceptance-part-3.md`

Tech-lead chép từ tin trả về của reviewer (reviewer chỉ đọc, không ghi file).

- Diff: `git diff abd2fa2..0ea548c` (commit `fix(runner): bound the actions column of ERP AI Log in bytes (FEAT-004)`, `runner.py` +75/−2, `test_agent_runner.py` +142); bổ sung 2 dòng test ở `7894f04` (`git diff f0fefb4..7894f04 -- erp_ai/agent/test_agent_runner.py`)
- Vòng: 1
- Verdict: approve

### Lớp 1 — khớp tiêu chí
- `_bounded_actions` dùng ở cả hai đường ghi (`runner.py:529` `_record_route`, `runner.py:659` vòng reason), đo đúng cách `write_entry` lưu (`json.dumps(ensure_ascii=False)`, `run_log.py:53`). Tổng luôn ≤ `ACTIONS_MAX_BYTES = 60000` byte với mọi danh sách; `sanitize_html` của Frappe bỏ qua chuỗi JSON nên lúc lưu không phình.
- Mỗi chuỗi cắt ở `ACTION_VALUE_MAX_BYTES = 1024` byte, đúng ranh giới ký tự; dấu cắt `ACTION_CUT_MARKER = "[đã cắt]"`. Vượt tổng: `value_before`/`value_after` của mục tốn nhất được thay bằng dấu cắt trước; công cụ, DocType, tên bản ghi, đúng/sai, người ra lệnh còn nguyên.
- Kết quả lưu là JSON hợp lệ dạng list; không sửa assertion cũ; một mục 20 × 200 "ế" (12310 byte) giữ nguyên.
- Test: probe của qa (6 `api_delete_record` × 20 trường × 200 ký tự → 1 dòng nhật ký, 6 mục, định danh từng mục, 4 mục giữ giá trị / 2 mục cắt); ca đúng 60000 byte (giữ nguyên) và 60001 byte (cắt), số tính tay; mỗi giới hạn có ca riêng chỉ nó làm đỏ (reviewer kiểm tay: 59999/60001, 1024, cắt theo ký tự thay vì byte, đảo thứ tự "tốn nhất trước").

### Phát hiện (chỉ blocker/major)
- Không có.

minor | — | — | 3 điểm nhỏ: (1) nhánh `value is not None` chưa có ca giữ → đã thêm ở `7894f04` (`value_after == [None] * 6`, đột biến ra `[None, None, None, None, '[đã cắt]', '[đã cắt]']`), reviewer xác nhận ở vòng 2 của review-62; (2) chú thích `runner.py:91-92` ghi "each string" nhưng khóa dict không bị cắt (tổng vẫn bị chặn); (3) chữ commit "one entry per call stays" không đúng ở nhánh bỏ mục | tùy dev

### Review checklist (10)
1–10: đạt (touchpoint đúng, RED/GREEN có, 0 dấu skip, không `except` mới, cột giữ `Small Text`, không migration, không phụ thuộc mới, commit `fix(runner): … (FEAT-004)` không trailer AI).

### Không kiểm được từ diff — tech-lead phán
- "Mọi danh sách ≤ giới hạn" và "đúng 1 mục mỗi lời gọi" (AC-34) không thể cùng đúng với cột 64 KB và số mục không giới hạn. Dev ưu tiên lần ghi không lỗi: khi các mục đã bỏ giá trị vẫn không vừa, các mục cuối bị bỏ và có một mục đóng `{"cut": "[đã cắt]", "dropped": n}`. Một mục đã bỏ giá trị nặng khoảng 70–700 byte → cần khoảng 85–850 lời gọi ghi trong MỘT lượt; `actions` đặt lại mỗi lượt và `REASON_MAX_TOKENS = 4096`. Phán: thật nhưng không chặn; là giới hạn còn lại, báo team-leader và ghi vào As-Built. Muốn bỏ hẳn giới hạn này phải đổi kiểu cột (migration, quyết định thiết kế).
- AC-35 ở ca vượt tổng: mục bị cắt còn công cụ, DocType, bản ghi, người ra lệnh và dấu cắt, không còn giá trị trước/sau. Giá trị trong `actions` vốn đã là bản cắt (T62: ≤ 20 trường, 200 ký tự). Phán: không chặn; giới hạn còn lại, báo team-leader.
- RED của ca route là `DataError 1366` (MariaDB cắt giữa ký tự nhiều byte), cùng gốc "vượt cột" với 1406 của F-1 → không chặn.

### Sau merge (tech-lead)
- Merge `0558640` (`team/FEAT-004-task-64` @ `7894f04`). `cmd.test_one` test_agent_runner trên `0558640`, `PYTHONPATH` = worktree feat-004, cài đặt site đang lưu: `Ran 85 tests in 24.701s` / `FAILED (failures=3)`: đúng ba ca `TestRunnerL1Classification` (`test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one`, `test_l1_applies_mapping_confidence_and_hint`, `test_l1_empty_route_still_saves_ai_fields_applied_one`), đỏ sẵn trên `abd2fa2` (bảng module của `acceptance-part-3.md`) vì site lưu `auto_assign_enabled=1`; không ca nào của T64. Không để trống cài đặt lần này vì site đang dùng chung với qa phần 1–2, FEAT-005, FEAT-007.

### Deferred
- Không có.
