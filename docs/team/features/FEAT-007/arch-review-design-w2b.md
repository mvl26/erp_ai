Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc: design đợt 2b (U7a vòng 2, U7b, U8 AC-64), FEAT-007

**Phán quyết tổng: request-changes cho cả hai tài liệu; không có design-defect; có ADR mới ADR-035 (proposed).**
- `design-addendum-2-U7a-fixes.md`: **request-changes**, hẹp. H-2 đã giải xong. H-1, H-4, H-5 và D-1..D-8 giải xong, chỉ trừ một lỗ ở Sửa 1.2 (J-1). H-3 giải theo nhánh B, vẫn chờ người. Còn hai điểm: A-U7a-10 trái AC-33 (J-2, phán quyết (7)), và một câu sai ở `:286` (phán quyết (9)).
- `design-addendum-2-U7b-U8.md`: **request-changes**. Khung ADR-032 (ngăn, một method quyết định, gọi hàm controller) giữ nguyên. Ba chỗ lệch ADR-032 như đã viết (DocPerm, tập đọc, bit (5)) được chấp nhận và chốt bằng ADR-035. Còn 3 major của chính addendum: J-4 (danh sách rộng hơn hook), J-5 (tool đọc Setting và tự so ngưỡng), J-6 (Custom Field "Tự làm" commit giữa lượt).

Tech-lead và designer đọc file này **sau** `arch-review-design-w2a.md`. Các dòng dưới thắng hai addendum ở chỗ khác nhau.

## Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Hook quyền có cấp được quyền không | Không. "Controllers can only deny permission, they can not explicitly grant" | `apps/frappe/frappe/permissions.py:455-473` |
| `hooks.py` đã có `has_permission`/`permission_query_conditions` chưa | Chưa, chỉ có mẫu comment | `erp_ai/hooks.py:117-127` |
| Thứ tự trong `CustomField.on_update` | `validate_fields_for_doctype(self.dt)` (`:211`) chạy **trước** `frappe.db.updatedb` (`:216`). Commit ngầm nằm trong `sql_ddl` | `apps/frappe/frappe/custom/doctype/custom_field/custom_field.py:206-216`; `database.py:422-425` |
| `commit()` có xóa callback rollback không | Có, `before_rollback.reset()`, `after_rollback.reset()` | `apps/frappe/frappe/database/database.py:1187-1190` |
| `set_user` trong request | Ghi đè `local.session.sid`, `local.session.data`, `local.form_dict`; trong request `frappe.local.session` là `session_obj.data` | `apps/frappe/frappe/__init__.py:646-658`; `frappe/sessions.py:232` |
| `PANEL_METHODS` hôm nay | 2 chuỗi | `erp_ai/constants.py:67-70` |
| ADR-032 QĐ 3 so với dòng test | QĐ 3: "phiếu họ đọc được". Test: "người không được giao, không Instructor → không thấy" | `docs/team/adr/ADR-032.md:24`, `:39` |
| ADR-010 QĐ 5, Ràng buộc import | Kết quả đọc không có giá trị cấu hình nào (kể cả bật/tắt). Module ngăn chỉ được import `policy`, `constants`, `frappe`, `helpdesk` | `docs/team/adr/ADR-010.md:60-64`, `:91` |
| ADR-031 QĐ 4 | Tool nhận mức từ `ToolContext`, **không đọc ERP AI Setting** | `docs/team/adr/ADR-031.md:30` |
| ADR-030 Ràng buộc ngưỡng | Một vị từ "dưới ngưỡng"; "grep phép so ngưỡng ở nơi khác → finding" | `docs/team/adr/ADR-030.md:43`, `:58` |
| ADR-033 QĐ 1 | Ghi phía phiếu (có comment) dưới tài khoản agent, qua một hàm chuyển phiên; nguồn: runner, định tuyến, job lịch, job sự kiện | `docs/team/adr/ADR-033.md` QĐ 1 |
| FEAT-007 AC-33 về Từ chối | "Sau Từ chối: không ghi, có log và comment" | `docs/team/features/FEAT-007/spec.md:199` |
| AC-64 | Chỉ khi có dòng `Cần duyệt`; production không cản | `spec.md:242` |
| Danh mục của U0 | Tuple `CATALOG_ACTIONS` 6 hằng. Option Select `action` của `erp_ai_catalog_rule.json` = `"\n".join(CATALOG_ACTIONS)`, có test ghim. Luật `target_doctype`/`fields` theo từng hành động | `design-w0-fixes.md:64`; `design.md:212-223`, `:298` |
| Tiến độ `team/FEAT-007` | Mới tới T1 (`19e92a7`); U0 T8 chưa tick | `git log team/FEAT-007` |

## 1. Phán quyết từng tài liệu

| Tài liệu | Phán quyết | Lý do (ba ý) |
|---|---|---|
| `design-addendum-2-U7a-fixes.md` | **request-changes** (J-1, J-2, `:286`) | Đúng ADR-031 QĐ 9 và D-1: trạng thái chạy commit trước khi ghi đích (Sửa 1.1). Đúng Ràng buộc 4: `_decider` qua `can_decide`, giữ chữ FEAT-004 (Sửa 2). Comment kết quả có một bộ dựng và một lời gọi (Sửa 3). Nhưng: Sửa 1.2 dùng "dòng có tồn tại" thay cho "đã commit chưa" (J-1); A-U7a-10 bỏ comment sau Từ chối, trái AC-33 (J-2) |
| `design-addendum-2-U7b-U8.md` | **request-changes** (J-4, J-5, J-6, J-2 phần test U7b; gộp phán quyết (1)–(6), (8)) | Đúng ADR-032 QĐ 1, 2, 4, 5 và Ràng buộc 1, 2: một method POST, gọi đúng hàm controller, không `transitions`, không enqueue. Đúng ADR-031 QĐ 2, 6, 7 cho Project. Ba điểm lệch ADR-032 QĐ 3 / ADR-010 QĐ 5 là đúng hướng và nay có ADR-035. Nhưng: `permission_query_conditions` bị coi là "lọc thô" (J-4); tool đọc Setting và tự so ngưỡng (J-5); bỏ qua ghi chú commit ngầm của U7a (J-6) |

## 2. Các finding trước trên U7a (w2a)

| Mục w2a | Trạng thái | Giải bởi |
|---|---|---|
| H-1 (major, commit ngầm, kẹt `Đang áp dụng`) | **Giải phần chính** (không còn kẹt). Còn lỗ dọn dẹp Custom Field: J-1 | Sửa 1.1, 1.3, 1.4, 1.5 |
| H-2 (major, `_decider` so role) | **Giải** | Sửa 2 |
| H-3 (major, AC-28 "không có task", test có điều kiện) | **Giải**, nhánh B **chờ người**; dòng `:286` phải sửa câu (phán quyết (9)) | Sửa 3 (nhánh A ở 3.7) |
| H-4 (minor, giao diện chết giữa U7a và U7b) | **Giải** | Sửa 6; hook ở U7b theo ADR-035 |
| H-5 (minor, luật ADR-005, C-2) | **Giải** | Sửa 7 |
| minor (a) `set_user(previous)` | **Giải** | Sửa 10 |
| minor (b) hồi quy hàng U3 | **Giải** | Sửa 9 (test) |
| minor (c) thứ tự `budget_alert` | Không thuộc U7a (U5b) | — |
| D-1 | **Giải**, trừ J-1 | Sửa 1 |
| D-2 | **Giải** | Sửa 2 |
| D-3 | **Giải** theo nhánh B. Cách kiểm đổi theo phán quyết (9): addendum `:381` vẫn còn chữ, nhưng 3.6 thay nó | Sửa 3 |
| D-4 | **Giải** | Sửa 4 |
| D-5 | **Giải** | Sửa 5 |
| D-6 | **Giải** | Sửa 6 |
| D-7 | **Giải** | Sửa 7 |
| D-8 | **Giải** | Sửa 8 |

## 3. Finding mới

Định dạng: `severity | STD | ADR bị phá | file:line | mô tả | sửa`.

| # | severity | STD | ADR bị phá | file:line | mô tả | sửa |
|---|---|---|---|---|---|---|
| J-1 | major | STD-ERR-7 | ADR-031 QĐ 9; ADR-012 (đích không lệch trạng thái) | `design-addendum-2-U7a-fixes.md:53` | `_undo_partial_write` coi "dòng Custom Field có" là "đã commit ngầm". Sai: `validate_fields_for_doctype` chạy sau `insert`, trước `updatedb` (`custom_field.py:211`, `:216`). Nếu nó ném `ValidationError`, dòng có trong giao dịch nhưng chưa commit, nên `present = True` và savepoint không được lùi. Rồi `_run_record` bước 5 `finish` + commit làm bền một Custom Field **không có cột** | Phân biệt bằng "trong lúc ghi đã có commit chưa" (ví dụ cờ do một callback `frappe.db.after_commit` đặt ngay trước lần ghi; dev chọn cơ chế). Chưa commit → luôn `rollback(save_point)`. Đã commit → không lùi, báo `present`. Thêm test `TC::TestCreateCustomField::test_error_in_on_update_before_ddl_rolls_back` (stub `validate_fields_for_doctype` ném → 0 Custom Field sau job, `present` sai) |
| J-2 | major | STD-TEST-2 | ADR-031 QĐ 3 (cùng comment kết quả); ADR-035 QĐ 6 | `design-addendum-2-U7a-fixes.md:133`, `:148`, `:277` (A-U7a-10); `design-addendum-2-U7b-U8.md:366` ("reject → 0 job") | AC-33 (`spec.md:199`) đòi "Sau Từ chối: không ghi, có log **và comment**". A-U7a-10 dựa vào FEAT-004 AC-28 để bỏ comment đó. Nhưng AC-33 của FEAT-007 là tiêu chí đang giao | Phán quyết (7) |
| J-3 | major | STD-SEC-4 | ADR-032 QĐ 3 → ADR-035 QĐ 3 | `design-addendum-2-U7b-U8.md:162` | Câu "Lọc danh sách thô; chốt chính xác là `has_permission`" sai với Frappe: `get_list`, report view, `/api/resource` chỉ lọc theo `permission_query_conditions`, không gọi hook từng dòng. Điều kiện danh sách viết lại truy vấn ToDo riêng, nên sẽ lệch `authority.is_assigned` khi vế A-U7a-3 thêm vào | ADR-035 QĐ 3: tập danh sách ⊆ tập hook (test đòi bằng nhau). Dạng SQL của "giao mở" đặt cạnh `is_assigned` trong `authority.py` (U7b sửa `authority.py`, đúng 1 hàm, sau U7a). Thay `TP::TestProposalPermissionHook::test_agent_reader_matrix` bằng ma trận của ADR-035 Ràng buộc 4 |
| J-4 | major | STD-DESIGN-2 | ADR-031 QĐ 4 ("tool không đọc ERP AI Setting"); ADR-030 Ràng buộc 4 (một chỗ so ngưỡng) | `design-addendum-2-U7b-U8.md:188-197` | `auto_mode_allowed(..., settings=None)` gọi `policy.confidence_threshold(settings)`, `policy.auto_approve_streak(settings)` từ trong tool, nên tool đọc Setting. Vế 4 tự so `confidence_pct >= ngưỡng`, tức một phép so ngưỡng thứ hai ngoài `policy` | Runner đặt ngưỡng và số chuỗi vào `ToolContext` ở bước (e), cùng chỗ đọc ghi đè prompt (U7b sửa vùng `ToolContext` của `registry.py` và bước (e) của `runner.py`). Phép so "độ tin cậy đạt ngưỡng" là **một** hàm của `policy.py`, dùng chung với vị từ "dưới ngưỡng". Tool chỉ đọc `ctx`. AST: `catalog_tools.py` không gọi `confidence_threshold`, `auto_approve_streak`, `get_single` |
| J-5 | major | STD-ERR-7 | ADR-033 QĐ 5 (mỗi ghi = 1 mục trong dòng của bước); ADR-031 QĐ 4 → ADR-035 QĐ 5 | `design-addendum-2-U7b-U8.md:199-201`; ghi chú bị bỏ qua `design-addendum-2-U7a-fixes.md:57` | "Tự làm" tạo Custom Field commit ngầm giao dịch đang mở của runner. Câu `:201` "dữ liệu không đổi — bộ thực thi đã rollback savepoint" sai với hành động này | Phán quyết (8) |
| J-6 | minor | STD-DESIGN-2 | ADR-010 Ràng buộc import → ADR-035 QĐ 4 | `design-addendum-2-U7b-U8.md:122`, `:134` | `ticket_panel.py` import thẳng `erp_ai.agent.authority` để tính `can_decide` | Lấy `can_decide` qua hàm tóm tắt của controller (`record_summary` hoặc hàm cạnh nó). Module ngăn chỉ import thêm module controller. Dòng `LAYER_RULES` của ngăn ghi đúng điều đó |

`minor | — | — | 6 điểm nhỏ: (a) U7b :40 dùng NOT_ELIGIBLE (đã bỏ ở U7a-fixes Sửa 2; đọc là DECIDE_REFUSAL); :45, :59 (N-7), :393 (bước 7 "cần N-7") đọc theo nhánh B: comment kết quả là của U7a (result_comment.post_result); bảng 1.2 thêm IMPLICIT_COMMIT_ACTIONS, _post_comment, record_summary. (b) N-1 (do_tin_cay_pct vào PROMPT_REQUIRED_MARKERS["classify"]) thuộc U1 đợt 1, cùng commit với khóa mới của CLASSIFY_PROMPT, không thuộc U0: U0 thêm sớm thì test "bản dựng sẵn qua kiểm của chính nó" đỏ ở đợt 0. Nếu U1 đã merge mà thiếu, plan đợt 2 chèn một task 1 dòng trước U7b. (c) catalog_approvals.py không phải tool. Đặt ở agent/tools/ được (luật ADR-005 vẫn áp), nhưng không đăng ký vào TOOL_MODULES; dev ghim bằng test registry. (d) erp_ai_approval_stats.js chép CATALOG_ACTIONS thành JSON tĩnh. U8 phải nối "Tạo Project cho phiếu" trong cùng commit (phán quyết (4)), hoặc lấy options từ server. (e) catalog_create_project có khóa expected_end_date, project_name; chạy test AC-9 của FEAT-006 với danh sách từ cấm thật, trúng từ nào thì nối ROUTE_WORD_EXCEPTIONS trong cùng commit (w2a (7)). (f) U7a-fixes :286 câu sai, xem phán quyết (9) | dev's call`

## 4. Phán quyết (1)–(10)

**(1) ADR-032 QĐ 3 không làm được như đã viết. Chấp nhận dòng DocPerm `Agent` chỉ-đọc + hai hook. Chủ: U7b, đợt 2. Ghi bằng ADR-035 QĐ 1, 3.**
- Bằng chứng: `permissions.py:455-473`. Không có dòng DocPerm thì hook không bao giờ được hỏi.
- Các phương án khác (`ignore_permissions`, DocShare, User Permission) đều trái ADR-010 QĐ 4 hoặc thêm đường ghi (ADR-035 "Phương án").
- Ràng buộc bắt buộc:
  - dòng DocPerm và hai khóa `hooks.py` vào **cùng commit**, có test kiến trúc ghép đôi;
  - test ma trận `get_list` = `has_permission`;
  - rút lui theo thứ tự "gỡ DocPerm → gỡ mã". Mục 6 của addendum đã đúng thứ tự này; As-Built chép lại.
- Rủi ro được nhận (ADR-035 Hệ quả): nếu hook mất mà dòng còn thì mọi agent đọc mọi đề xuất, kể cả diff code.

**(2) Ai thấy đề xuất bản ghi: "được giao" (A-U7b-4). Xác nhận. Chủ: U7b, đợt 2. ADR-035 QĐ 2 thay chữ "phiếu họ đọc được" của ADR-032 QĐ 3.**
- Lý do:
  - Dòng test của ADR-032 kiểm được, còn câu QĐ 3 thì rộng hơn.
  - Tập đọc = tập người duyệt theo phiếu (ADR-031 QĐ 5), nên là quyền tối thiểu.
  - Một định nghĩa "giao mở" cho duyệt và đọc. Nếu người trả lời A-U7a-3 là "không tự gán rồi tự duyệt", vế `assigned_by ≠ user` áp luôn cho đọc mà không sửa hook.
- "Đọc được phiếu" vẫn kiểm ở hook từng bản ghi. Với Helpdesk 15.1, phiếu được giao thì đọc được, nên danh sách không cần vế này. Ma trận ADR-035 thêm một ca "được giao + `restrict_tickets_by_agent_group` khác nhóm". Hai đường lệch nhau thì điều kiện danh sách phải thêm vế đó.

**(3) Bit `proposal_one_step` (A-U7b-5). Chấp nhận. Chủ: U7b, đợt 2. ADR-035 QĐ 4 sửa ADR-010 QĐ 5.**
- Giá trị (5) đã lộ cho mọi người đọc comment: liên kết có chữ ký có mặt khi và chỉ khi (5) bật (ADR-032 QĐ 4). Bit không cho biết gì mới.
- Đúng một khóa suy từ cấu hình, tính lúc request qua `policy.py`. `decide_proposal` không đọc nó. Test `test_switch5_off_panel_still_decides` giữ.
- Kèm J-6: mọi dữ liệu đề xuất cho ngăn đi qua controller. Module ngăn không import `authority`.

**(4) AC-64 (hằng, option Select, `ACTION_TARGET_DOCTYPES["Project"]`, luật đích cố định). Chủ: U8, đợt 2, sau U7a và U7b, đúng một commit.** U8 sửa:
- `erp_ai/constants.py`: `ACTION_CREATE_PROJECT`, nối vào cuối `CATALOG_ACTIONS`, thêm khóa vào `ACTION_TARGET_DOCTYPES`;
- `erp_ai_catalog_rule.json`: option `action`;
- luật lưu của U0 cho "đích cố định" (`target_doctype`, `fields` phải trống): thêm đúng 1 mục, ở file U0 đã đặt luật đó;
- `catalog.py`: `ACTION_HANDLERS`;
- `catalog_tools.py`: tool, chèn `ticket` từ `ctx`, `APPROVAL_ONLY_ACTIONS` cộng vế `approval_only` trong vị từ duy nhất của U7b;
- `erp_ai_approval_stats.js`: options, nếu là JSON tĩnh.

Lý do làm một commit:
- Test ghim của U0 (`option = "\n".join(CATALOG_ACTIONS)`) và test U7a `test_action_target_doctypes_cover_catalog_actions` buộc tên, option và đích đổi cùng lúc.
- **Không giao U0 bây giờ**: thêm ở đợt 0 thì người lưu được dòng danh mục trỏ vào hành động chưa có handler suốt hai đợt, và test phủ của U7a đỏ.

Ghi nhận các file này nằm ngoài ô U8 của `arch-impact.md:182`, như w2a (8). Đòi `cmd.migrate` (option Select) trong lượt merge cuối đợt 2.

**(5) `PANEL_METHODS` thứ ba và hai khóa `hooks.py`. Chủ: U7b, đợt 2. Chấp nhận ngoài ô U7.**
- `constants.py`: đúng 1 dòng trong `PANEL_METHODS`, cùng commit với `decide_proposal` và lời gọi `call("erp_ai.ticket_panel.decide_proposal", …)` trong `.js`. Test ADR-009 so hai tập, nên tách commit là đỏ.
- `hooks.py`: đúng 2 khóa (`has_permission`, `permission_query_conditions`) cho DocType đề xuất, cùng commit với dòng DocPerm `Agent` (ADR-035 Ràng buộc 2). Nối ở cuối, không đụng khóa của U4a, U5a, U6a, U6b.

**(6) Lời đăng comment ở bước 3 của `_propose` là hàm dùng lại được. Chủ: U7a, đợt 2. U7b không tách lại.**
- U7a viết ngay hàm cấp module `_post_comment(ctx, html) -> str` trong `catalog_tools.py`. Hàm dựa vào đường ghi comment phiếu đã có (`propose_change._comment` hoặc tool comment của `write_ticket`). Không thêm bản thứ ba của `get_doc(TICKET_DOCTYPE, …).new_comment(…)` (STD-DESIGN-4).
- Cùng lý do, `record_summary(doc)` của controller do U7a viết làm hàm ngay từ đầu, `onload` gọi nó. U7b chỉ dùng hai hàm này, không tái cấu trúc mã U7a.
- Hai tên này vào hợp đồng U7a (mục 6 dưới).

**(7) Comment sau Từ chối (AC-33). Chủ: U7a, đợt 2. Đảo A-U7a-10.** Comment đến từ **cùng bộ dựng** `result_comment` (`Đã từ chối` là trạng thái cuối, `result_lines` nhận được). Comment được **đăng bởi job**, không trong request (ADR-035 QĐ 6):
- `reject` của controller là điểm cuối chung của ba đường Từ chối: form, liên kết có chữ ký qua `change_decision.decide`, ngăn qua `decide_proposal` (ADR-032 QĐ 2). Sau khi phép chuyển commit, nó xếp `enqueue_change_job(name)` như `approve`. Không thêm đích enqueue (w2a (2) giữ).
- `run_change`: đề xuất ở `Đã từ chối` → kết cục "đã từ chối", không lấy khóa chung, không đổi trạng thái → đi qua **đúng một** lời gọi `_post_result` đã có (A-U7a-12 giữ).
- Chạy lại job → 0 comment thêm (ADR-033 QĐ 6). Dấu chống lặp do designer chọn. Nếu cần trường thì là trường phần trạng thái, chỉ `transitions.py` ghi (ADR-031 Ràng buộc 6).
- Phủ mọi loại (code, lệnh, bản ghi): câu cuối AC-33 "cùng luồng và cùng trạng thái".
- Lý do không ghi trong request: `frappe.set_user` ghi đè sid, dữ liệu phiên (CSRF token) và `form_dict` của request (`__init__.py:646-658`, `sessions.py:232`). Ghi dưới phiên người từ chối thì trái ADR-033 QĐ 1, và `new_comment` từ chối Instructor không phải HD Agent.
- Test đổi:
  - U7a `TP::TestRecordDecision::test_reject_writes_nothing` đổi thành "đích không đổi, 1 dòng `reject`, 1 job; job → 1 comment `owner = AGENT_USER`, chạy lại → 0";
  - U7a 3.6 thêm subTest `Đã từ chối` vào `test_lines_for_each_final_status` và `test_each_outcome_one_result_comment`;
  - U7b `:366` đổi "reject → 0 job" thành "reject → 1 job, đích không đổi".
- Đúng cho cả nhánh A và B của w2a (6), vì lời gọi ở `reject`/`run_change` là của U7a trong cả hai nhánh.

**(8) Tạo Custom Field ở "Tự làm" commit giao dịch của runner. Chủ: U7b, đợt 2. ADR-035 QĐ 5 sửa ADR-031 QĐ 4.**
- Vị từ duy nhất `auto_mode_allowed` thêm vế "hành động ∉ `catalog.IMPLICIT_COMMIT_ACTIONS`" với lý do logger riêng. Vế sai → đề xuất `Cần duyệt`, rồi áp dụng sau duyệt theo D-1 (commit trạng thái chạy trước).
- U7b không chép tập đó: import tên của U7a.
- Thêm test ADR-035 Ràng buộc 7.
- Hệ quả nghiệp vụ: AC-30 "mỗi hành động tuân chế độ của dòng" có ngoại lệ cho Custom Field, chỉ chạm site `test` vì production đã từ chối. **NEEDS_ANSWER không chặn** cho analyst/người: chấp nhận "Custom Field luôn cần duyệt" không. Nếu không, cần ADR mới cho giao thức commit của runner (ADR-035 "Phương án").

**(9) Hai chỗ chữ sai. Chủ: designer, trong vòng sửa kế của từng addendum; không đổi mã.**
- U7b `:229-231`: chữ đúng là **`:231`**. Giá trị lưu ngoài `1..100` → trả `100` (fail-closed, cùng tiền lệ "đầu mục chưa biết → L1" của ADR-030 QĐ 2) cộng 1 dòng logger cảnh báo, không ngoại lệ nào bị nuốt. Bỏ chú thích "→ 20 không; xem dưới" ở `:229` và câu hỏi "ValueError bị nuốt? Không:" ở `:231`. Theo J-4, hàm này được runner gọi khi dựng `ToolContext`, không được tool gọi. Test `TPol::TestAutoApproveStreak::test_out_of_range_is_fail_closed` giữ.
- U7a-fixes `:286`: phần trong ngoặc sai. `grep -n "chỉ viết khi"` trên file fixes chỉ trúng **chính dòng 286**; bảng cuối không có cụm này. Sửa thành "(grep trên file này chỉ trúng chính câu này)". Cách kiểm D-3 viết lại:
  - `grep -n "chỉ viết khi" design-addendum-2-U7a.md` vẫn trả `:381`, vì file fixes không sửa addendum mà **thắng** nó;
  - tech-lead chép dòng test từ Sửa 3.6, không từ `:381`. Plan không có dòng test nào kèm điều kiện.

**(10) ADR mới: ADR-035 (proposed).** Bốn quyết định liên quan:
- thay ADR-032 QĐ 3 và dòng Ràng buộc "hook quyền" (phán quyết (1), (2));
- sửa ADR-010 QĐ 5 và Ràng buộc import (phán quyết (3), J-6);
- sửa ADR-031 QĐ 4 (phán quyết (8));
- bổ sung ADR-033 QĐ 1 (phán quyết (7)).

Không sửa thân ADR nào đã có. Cột trạng thái của ADR-032, ADR-010, ADR-031 chỉ thêm "một phần bị thay bởi ADR-035" khi người duyệt; việc này của team-leader.

## 5. Thứ tự sửa file chung (U7a, U7b, U8 AC-64; đợt 2)

Merge vào `team/FEAT-007` theo thứ tự: U5b ∥ U7a, rồi U7b, rồi U8 (AC-64). U7a, U7b, U8 AC-64 vào `develop` cùng lượt merge cuối đợt 2 (D-6, cộng `cmd.migrate`). Đơn vị sau rebase rồi chạy `cmd.test_one` cho mọi file chung trước khi merge (K-5).

| File | Thứ tự | Vùng của từng đơn vị |
|---|---|---|
| `erp_ai/constants.py` | U0 (T8) → U6b → U7a → U7b → U8 | U7a: 3 hằng (w2a (4)). U7b: 1 dòng `PANEL_METHODS`. U8: `ACTION_CREATE_PROJECT`, phần tử `CATALOG_ACTIONS`, khóa `ACTION_TARGET_DOCTYPES` |
| `erp_ai/hooks.py` | U4a, U5a, U6a, U6b → U7b | U7b: 2 khóa quyền, nối cuối |
| `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.json` + luật lưu đích cố định của U0 | U0 → U8 | U8: 1 option, 1 mục luật |
| `erp_ai/agent/tools/catalog.py` | U7a → U8 | U7a: tạo, có `IMPLICIT_COMMIT_ACTIONS`, sửa J-1. U8: 1 mục `ACTION_HANDLERS` |
| `erp_ai/agent/tools/catalog_tools.py` | U7a → U7b → U8 | U7a: tạo, `_post_comment`. U7b: vị từ ở điểm chen bước 4 (gồm vế tự commit, đọc `ctx`). U8: tool Project, `APPROVAL_ONLY_ACTIONS` + vế `approval_only` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | U7a → U7b | U7a: `_decider`, `record_summary`, `reject` xếp job (7). U7b: hai hàm hook, hàm tóm tắt cho ngăn (gồm `can_decide`) |
| `erp_ai_change_proposal.json` | U7a → U7b | U7a: option `change_kind`, trường loại bản ghi. U7b: dòng DocPerm `Agent`, `report` cho hai role |
| `erp_ai/agent/authority.py` | U1 → U7a → U7b | U7a: 3.2. U7b: dạng SQL của "giao mở", đặt cạnh `is_assigned` (J-3) |
| `erp_ai/agent/changes/apply_job.py`, `result_comment.py` | U7a | nhánh `Đã từ chối` của `run_change` (7). U7b, U8 không chạm |
| `erp_ai/agent/tools/registry.py` | U1 → U6b → U7a → U7b | U7b: điền `Grant.catalog_block`, hai trường mới của `ToolContext` (J-4). U8 không chạm (tool mới nằm trong module đã đăng ký) |
| `erp_ai/agent/runner.py` | … → U6b → U7a → U7b | U7b: bước (e) ghi đè prompt, cờ danh mục, giá trị ngưỡng/chuỗi vào `ToolContext` |
| `erp_ai/agent/policy.py` | U1 → U2 → U6b → U7a → U7b | U7b: `PromptOverrides`, `prompt_overrides`, `auto_approve_streak`, hàm so "đạt ngưỡng" dùng chung (J-4) |
| `erp_ai/agent/prompts.py` | U1 → U4b, U6b, U8 (AC-62/63, đợt 1) → U7b | U7b: tách hằng, ghi đè, `CATALOG_BLOCK`, P-8 |
| `erp_ai/agent/tools/write_ticket.py` | U4b → U8 (AC-62/63) → U8 (AC-64) | U8 AC-64: 1 hằng `TASK_TICKET_FIELD`, `:143` dùng lại |
| `erp_ai/tests/test_architecture.py` | U5b ∥ U7a (K-5) → U7b | U7b: `TestPanelArchitecture`, `POLICY_FIELDS`, luật ADR-035 (DocPerm ↔ hooks, AST chuyển phiên, `LAYER_RULES` ngăn) |
| `erp_ai/agent/tools/test_registry.py` | U7a → U7b → U8 | U8 chỉ nối `ROUTE_WORD_EXCEPTIONS` nếu trúng từ cấm |
| `test_catalog.py`, `test_catalog_tools.py`, `test_apply_job.py`, `test_erp_ai_change_proposal.py` | U7a → U7b → U8 | mỗi đơn vị chỉ thêm lớp test của mình; U7a đổi test Từ chối theo (7) |
| `erp_ai/erp_ai_agent/report/erp_ai_approval_stats/*` | U7b → U8 | U8: option Project nếu JSON tĩnh |

## 6. Hợp đồng U7a bổ sung (U7b, U8 dựa vào được)

Giữ toàn bộ mục 5 của w2a, cộng thêm:
- `catalog.IMPLICIT_COMMIT_ACTIONS`;
- `catalog_tools._post_comment(ctx, html) -> str`;
- `erp_ai_change_proposal.record_summary(doc) -> dict`;
- `result_comment.post_result` (nhánh B; nhánh A: tên của T56);
- `DECIDE_REFUSAL` (chữ cũ FEAT-004), thay cho `NOT_ELIGIBLE`;
- `reject` xếp `enqueue_change_job`, và `run_change` đăng comment cho `Đã từ chối` (7).

## 7. ADR có bị phá không

| ADR | U7a-fixes | U7b + U8 |
|---|---|---|
| ADR-005 | Không | Không (`ticket` chèn từ `ctx`, minor (e)) |
| ADR-009 | — | Không: một script, `textContent`, `call` với literal ∈ `PANEL_METHODS` (5) |
| ADR-010 | — | QĐ 5 và Ràng buộc import: sửa bởi ADR-035 QĐ 4 (3), J-6 |
| ADR-012, ADR-013 | J-1 (orphan Custom Field) | Không chạm |
| ADR-030 | — | Ràng buộc 4 bị J-4 |
| ADR-031 | QĐ 3 bị J-2 | QĐ 4 bị J-4; QĐ 4 sửa bởi ADR-035 QĐ 5 (8). QĐ 2, 6, 7 đúng cho Project |
| ADR-032 | — | QĐ 3 thay bởi ADR-035 QĐ 1–3; QĐ 1, 2, 4, 5 và Ràng buộc 1, 2 đúng |
| ADR-033 | QĐ 1 đúng ở job | QĐ 5 bị J-5 (đã giải bằng (8)); QĐ 1 bổ sung bởi ADR-035 QĐ 6 |

## 8. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR và phán quyết trên mà vẫn xung đột, rồi siết lại:
1. U7b viết điều kiện danh sách bằng truy vấn ToDo riêng; sau đó câu A-U7a-3 thêm vế `assigned_by` vào `is_assigned`. Danh sách lộ đề xuất mà form từ chối. Đã siết: ADR-035 QĐ 3 (một định nghĩa ở `authority.py`, test bằng nhau).
2. Task A thêm dòng DocPerm `Agent`, task B đăng ký hook ở commit sau. Giữa hai commit, mọi agent đọc mọi đề xuất. Đã siết: cùng commit, test ghép đôi (ADR-035 Ràng buộc 2).
3. U8 nối `ACTION_CREATE_PROJECT` vào `CATALOG_ACTIONS` nhưng quên option JSON, hoặc U0 thêm option sớm. Đã siết: (4), một commit ở U8.
4. U7b "Tự làm" tạo Custom Field giữa lượt, lượt lỗi sau đó, nên Custom Field có mà không có mục nhật ký. Đã siết: (8), ADR-035 QĐ 5.
5. U7a đăng comment Từ chối trong request bằng `agent_session`, nên phiên của người duyệt mất CSRF token. Đã siết: (7), ADR-035 QĐ 6 cộng AST cấm chuyển phiên trong module whitelisted.
6. U7a viết đăng comment bước 3 và `onload` trong thân hàm, rồi U7b tái cấu trúc cùng chỗ. Đã siết: (6), U7a viết hàm ngay.
7. U1 đổi cách so ngưỡng, còn tool U7b giữ phép so riêng, nên "Tự làm" lệch "dưới ngưỡng". Đã siết: J-4, một hàm so ở `policy.py`, tool đọc `ctx`.
8. Cờ "đã commit" của J-1 suy từ `transaction_writes` hoặc `exists` ở task khác nhau. Đã siết: J-1 đòi phân biệt bằng "có commit trong lúc ghi", cộng test lỗi ở `on_update` trước DDL.

Sau khi siết, không còn cặp nào trong phạm vi U7a, U7b, U8 AC-64.

## Việc tiếp

- Designer:
  - U7a vòng sửa 2/3: J-1, J-2 / (7), (6), câu `:286`.
  - U7b-U8 vòng sửa 1/3: J-3, J-4, J-5 / (8), J-6, (1)–(5), câu `:229-231`, minor (a)–(e).
  - Tên mới chỉ là **thêm**.
- Team-leader:
  - chuyển ADR-035 cho người duyệt cùng nhánh (6) của w2a, vẫn chờ;
  - hai câu không chặn cho analyst/người: "Custom Field luôn cần duyệt" (8) và A-U7b-7 (AC-64 cần `level_cap_c ≥ L2`). A-U7a-3 vẫn mở;
  - nếu người duyệt ADR-035, thêm chú thích "một phần bị thay bởi ADR-035" vào dòng trạng thái của ADR-010, ADR-031, ADR-032.
- Tech-lead: đưa mục 5 (thứ tự) và (4), (5) (một commit) vào plan đợt 2.
