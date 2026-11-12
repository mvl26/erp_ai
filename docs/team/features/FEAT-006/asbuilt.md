Feature: FEAT-006
Stage: asbuilt
Author-agent: writer
Date: 2026-11-13
Approved-by:
<!-- Cổng: G4 tắt (config.json), để trống. -->
<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod; writer không điền. -->

# As-Built FEAT-006 — Chấm độ phức tạp và độ quan trọng; chọn ưu tiên, nhóm, người phụ trách; SLA và Task theo điểm

Người đọc: người dùng (`user`: System Manager giữ cấu hình, HD Agent, người duyệt). Verdict của acceptance: `accepted` (lần 2, 6/6), commit kiểm `e5e1a16`, nhánh `team/FEAT-006`. G4 tắt (chế độ decide).

## 0. Nguồn so sánh
- Mã thật: `git diff d425faa e5e1a16 -- erp_ai` (nền `team/FEAT-003` = `d425faa`): 35 file, +6075/-204. Không có file `diff.patch` trong thư mục feature; writer dùng thẳng lệnh git này.
- So với design: `design.md` (viết trên nền `7cb654f`, số dòng của design không còn đúng; mọi `file:line` dưới đây là của `e5e1a16`).
- Lý do của từng chỗ lệch chỉ lấy từ `review-*.md`, `progress*.md`, `rework-1.md`, journal ngày 2026-11-13 và `acceptance.md`. Chỗ nào không có thì ghi "không ghi nhận".
- Không có hành vi trong diff nằm ngoài spec. Một thay đổi hạ tầng cần nói rõ: cổng model gửi `thinking: disabled` cho bước phân loại với model `claude-haiku-*` (mục 1.1). Nó sửa lỗi làm AC-1 và AC-15 không đạt (lần verify 1), do team-leader chốt (journal 2026-11-13), ảnh hưởng mọi lời gọi phân loại, không riêng eval.

## 1. Lệch so với design (đọc trước)

### 1.1 Tắt thinking cho model phân loại `claude-haiku-*`, không nâng trần token (design D-8)
- Design D-8 nói: `CLASSIFY_MAX_TOKENS` 400 → 600, "có ca `max_tokens` thì nâng".
- Thực tế: trần vẫn 600 (`erp_ai/agent/runner.py:52`). Eval thật lần 1 (`df8de66`) cho 2/2 phiếu bị cắt ở `max_tokens` (output 600, `Unclassified: 2`). Nguyên nhân gốc (rework-1.md, R1): Haiku 5.5 mặc định bật adaptive thinking và token thinking tính vào `max_tokens`; một JSON phân loại ngắn không cần 600 token.
- Sửa: `call_model` gửi `thinking: {"type": "disabled"}` khi `task == "classify"` và tên model bắt đầu bằng `claude-haiku-` (`erp_ai/gateway/__init__.py:23-24`, `:154-155`). Bước `reason` không đổi. Model rỗng vẫn ra `GatewayError bad_request` như trước (R4: `(model or "")`).
- Đo lại (E2, `e5e1a16`, model thật): `max_tokens hits: 0`, `Unclassified: 0`, output lớn nhất 285/600 token.
- Giới hạn đã biết: model phân loại KHÔNG phải `claude-haiku-*` không được tắt thinking và vẫn có thể bị cắt ở trần 600. Điều này được ghi ở mô tả field `model_classify` (`ERP AI Credential`) và `model_classify_default` (`ERP AI Setting`); `tests/test_doctype_descriptions.py` khóa cụm "claude-haiku" và "trần token".
- **Backport.** Mã nền FEAT-003 (`d425faa`: trần 400, không gửi `thinking`) có cùng lỗi: nhật ký site ghi `output_tokens=400`, `stop_reason=unparseable` (rework-1.md). Nếu FEAT-003 được phát hành riêng, không kèm FEAT-006, cần backport đúng thay đổi ở `gateway/__init__.py` (7 dòng) hoặc mở BUG riêng cho `main`. Journal 2026-11-13 (mục b) giao việc "báo để mở BUG riêng"; chưa có BUG nào được mở trong artifact đã đọc.
- Design.md D-8 vẫn ghi chữ cũ (review-R1-round1.md: STD-DOC-4, "deferred (designer/asbuilt)"). Bản As-Built này là bản ghi chính thức.

### 1.2 Giao Task bị chặn bởi chia sẻ tài liệu: `TaskSharingDisabled` và `REASON_TASK_FAILED` (design 3.4, 3.6, 4.2 bước 4)
- Design: ngoại lệ ở (u3) là `frappe.ValidationError` thường; câu comment là `ASSIGN_REQUEST` với lý do "không giao được Task… (chia sẻ tài liệu đang tắt)" cho MỌI ngoại lệ của (u3).
- Thực tế:
  - Lớp mới `TaskSharingDisabled(frappe.ValidationError)` (`erp_ai/agent/tools/route_ticket.py:34-35`), ném trong `create_routed_task` sau `task.insert()` khi `disable_document_sharing` bật và người được giao không đọc được Task (`:115-118`). Nó lặp điều kiện kiểm của Frappe `assign_to.add` (review-R3.md, deferred, STD-DESIGN-4).
  - Câu comment là `TASK_REQUEST` ("Bot đã gán người phụ trách cho phiếu nhưng không giao được Task: {lý do}. Nhờ trưởng nhóm giao Task.", `route_ticket.py:22-27`), không phải `ASSIGN_REQUEST`. Lý do: ca này người đã được bot gán ở (u2) và ToDo của phiếu không bị rollback, nên "xin phân công" sẽ sai thực tế (T22b; team-leader chốt ĐẠT cho AC-13 (i), journal 2026-11-13).
  - `REASON_TASK_NOT_ASSIGNED` = "chia sẻ tài liệu đang tắt" chỉ dùng khi bắt được `TaskSharingDisabled`. Mọi ngoại lệ khác dùng `REASON_TASK_FAILED` = "giao Task không thành công" (`route_ticket.py:27-28`, `runner.py:407-427`); comment không lộ tên ngoại lệ hay nội dung phiếu.
- Lý do: acceptance lần 1 (AC-13 (i), điểm 2) thấy comment nêu sai nguyên nhân cho lỗi không liên quan chia sẻ; sửa ở rework 1, R3 (`review-R3.md`).
- Task bị từ chối KHÔNG ném lỗi (không có DocType Task, thiếu quyền): không Task, không comment, chỉ có `actions` `ok=false` và log (progress.md:56; test `RR::TestRoutingTask::test_refused_task_without_exception_no_task_no_comment`). Design không nói rõ ca này.
- Design.md 3.4, 3.6, 4.2 chưa được sửa theo (review-R3.md, STD-DOC-4); bản này là bản ghi chính thức.

### 1.3 Savepoint
- Design 4.2: mỗi bước `uN` dùng `frappe.db.savepoint("erp_ai_route")`.
- Thực tế: hai lớp lồng nhau. Lớp ngoài `erp_ai_route` (`runner.py:74`, `:316`, `:331`) bao cả lần lưu phiếu (u1) lẫn lần cập nhật bản ghi nhật ký, để ngoại lệ ở giữa không để lại `applied=0` trên phiếu đã đổi (docstring `runner.py:309-313`). Lớp trong `erp_ai_route_unit` cho từng đơn vị ghi sau (u1) (`runner.py:76`, `:353`, `:362`).
- Lý do tên lệch: progress.md:54 ghi "deferred cho designer"; journal 2026-11-13: ghi As-Built, không đổi mã. Lý do thiết kế lồng hai lớp: không ghi nhận ngoài docstring.

### 1.4 `value_before` chỉ có `ticket` (design 3.5)
- Design 3.5 liệt kê `ticket`, `assign`, `task` cho cả trước và sau.
- Thực tế: `value_before = {"ticket": {...}}`, `value_after = {"ticket", "assign": [user], "task": <tên>}` (`runner.py:497-504`). Thiếu khóa trong `value_before` nghĩa là "trống trước" (review-24-round1.md: "câu hỏi thiết kế, ghi cho designer"). Qa chấp nhận AC-16 `pass` với dạng này.

### 1.5 Hai khe hở của bảo vệ tĩnh T26 và một miễn trừ
Bộ quét AST trong `erp_ai/tests/test_architecture.py` (10 luật, 10 ca tự kiểm, đột biến đỏ rõ: `dev-T26-r2.md`) còn các chỗ chưa phủ. Team-leader nhận và không mở task thêm (journal 2026-11-13):
1. ADR-019 Ràng buộc nhắc "tên bộ phận của bảng 16.2" không được xuất hiện trong `erp_ai/agent/`; luật `test_no_default_people_in_agent_python` (AC-14) chỉ quét tên người (Việt, Tiến, Hiếu, Lan, Hà, Thư, Chi) và `ai.agent`, không quét tên bộ phận (review-26.md, deferred).
2. ADR-020 coi `runner._route` là "mã của bước định tuyến", nhưng luật "đúng một `.save()` HD Ticket" chỉ quét `route_ticket.py`; `runner.py` hôm nay không có `.save()` nên chưa vi phạm, nhưng nếu có người thêm vào thì bộ quét không bắt.
3. Miễn trừ có chủ ý: `authority.py` đọc `_assign` (FEAT-002, hàm `_assigned_by_other`) được miễn khỏi luật `test_assign_field_not_used_for_decision`; chỉ đúng hàm đó. Đồng thời `db_update` bị cấm ở mọi module tool.
Các điểm minor khác của bộ quét (đối số từ khóa như `db_set(fieldname="response_by")`, `getattr(doc, "db_update")()`, handler bọc `lambda`/`partial`, tên trường SLA trong giá trị dict) cũng chưa phủ (review-26.md, deferred).

### 1.6 Thông báo "ma" (giới hạn đã biết, không sửa)
- `_run_unit` rollback về savepoint khi một đơn vị lỗi. Rollback tới savepoint không hủy các callback `after_commit` của Frappe (`database.py:1200-1204`). Trên site thật (không chạy test), nếu ngoại lệ xảy ra SAU `notify_assignment` trong cùng đơn vị, ToDo bị hoàn tác nhưng job tạo Notification Log (và email nếu bật) vẫn chạy: người nhận có thể thấy thông báo gán cho một ToDo không còn. Sự kiện realtime `list_update` của bản ghi đã hoàn tác cũng vẫn phát (vô hại).
- Ai có thể gặp: (u2) `assign_owner` và (u3) `create_routed_task` đều gọi `assign_to.add` ở dòng cuối; sau `notify_assignment` chỉ còn `msgprint` và đọc lại, nên xác suất thấp. Ca chia sẻ tắt (AC-13 (i)) ném lỗi TRƯỚC `notify_assignment` nên không sinh thông báo ma.
- Test không bắt được: trong test `in_test=True`, thông báo tạo ngay trong savepoint và bị rollback cùng.
- Quyết định: team-leader nhận là giới hạn đã biết, không gọi architect (journal 2026-11-13, mục a). Sửa cần dời thông báo ra sau commit ngoài; nếu xảy ra thật thì mở task gia cố riêng.

### 1.7 Bảng đối chiếu từng mục của design
| Mục thiết kế | Thực tế | file:line | Lý do |
|---|---|---|---|
| D-1, 2.4 `routing_rules` (Code JSON) và `auto_assign_enabled` (Check, mặc định 0) trong `section_routing` | đúng thiết kế | `erp_ai_setting.json:203,210`; `install.py:90-100` | — |
| D-2, 2.1 HD Ticket: `ai_complexity`, `ai_importance` (Int, 0, permlevel 8), `ai_score_reason` | đúng thiết kế | `install.py:123` (`_ai_field_specs`), `:185` (`_ensure_template_rows`) | — |
| 2.2 Task `ai_ticket` (Link → HD Ticket, permlevel 0) | đúng thiết kế | `install.py:213` | — |
| 2.3 dòng Custom DocPerm Task của app bật `share` | đúng thiết kế | `install.py:236` | — |
| 2.5, D-15 ERP AI Log +4 cột `predicted_*` | đúng thiết kế | `erp_ai_log.json` (+32 dòng) | — |
| 2.6 đọc chỉ-đọc ToDo, Task, HD Agent, HD Team, SLA | đúng thiết kế | `site_facts.py:11,21,26,30,34` | — |
| 3.1 JSON phân loại thêm 4 khóa; `build_classify_request(..., departments=())`; điểm đi theo cặp (D-4) | đúng thiết kế | `prompts.py:166`; `classification.py` | — |
| 3.2 hàm của lõi agent | đúng thiết kế (đủ 12 hàm: `routing.py:49,157,171,276,292`, `site_facts.py`, `policy.py:37,46`, `prompts.py:202,231`) | các file trái | — |
| D-12 xóa `resolve_ticket_values` và `ROUTING_TABLE` | đúng thiết kế (grep không còn trong mã không phải test) | `classification.py`, `prompts.py` | — |
| 3.3 `routing_rules` mặc định và luật kiểm | đúng thiết kế | `routing.py:12,252,276,292`; `erp_ai_setting.py` (+5 dòng) | — |
| 3.4 `route_ticket.py` (u1)–(u4), không `ToolSpec` | khác một chỗ: lớp `TaskSharingDisabled` | `route_ticket.py:34,115-118` | xem 1.2 |
| 3.5 nhật ký, `actions` theo thứ tự chạy | khác một chỗ: `value_before` chỉ có `ticket` | `runner.py:497-504` | xem 1.4 |
| 3.6 câu chữ cố định | khác: thêm `TASK_REQUEST`, `REASON_TASK_FAILED`; `NO_SLA` đúng | `route_ticket.py:20-28` | xem 1.2 |
| 3.7 prompt đổi, test "trùng từng byte" cập nhật | đúng thiết kế | `test_agent_runner.py`, `test_handlers.py:2` | — |
| D-8, 4.1 bước 4.1 `max_tokens` | khác: tắt thinking cho haiku, trần vẫn 600 | `gateway/__init__.py:23-24,154-155`; `runner.py:52` | xem 1.1 |
| 4.1 bước (b)/(e), công tắc, `ToolContext.routing_config` | đúng thiết kế | `runner.py`; `registry.py:20` | — |
| 4.2 savepoint từng bước `erp_ai_route` | khác: hai lớp `erp_ai_route` + `erp_ai_route_unit` | `runner.py:74,76,316,353` | xem 1.3 |
| 4.2 (u1) lỗi/từ chối → dừng (u2)–(u4), kiểm SLA | đúng thiết kế (AC-7b, AC-18) | `runner.py:302-331` | — |
| 4.2 kiểm SLA, D-9 chạy dù công tắc bật hay tắt | đúng thiết kế | `runner.py:469-487` | — |
| 4.2 (u2), (u3), (u4) | đúng thiết kế trừ ca Task bị chặn bởi chia sẻ | `runner.py:395-440` | xem 1.2 |
| 4.3 bảng luồng lỗi | đúng thiết kế trừ dòng `disable_document_sharing` (câu `TASK_REQUEST`) | — | xem 1.2 |
| 4.4 eval: `_predict`, `compute_metrics`, `format_report` | đúng thiết kế (thêm 3 dòng báo cáo: ưu tiên, nhóm, phân bố điểm, token) | `run_eval.py:56,65,146,179` | — |
| 5 Quyền, ghim role bằng `pin_agent_roles` | đúng thiết kế | `test_utils.py:165` | — |
| 6 Migration: không patch, `ALTER ADD COLUMN`, cài lại không ghi đè | đúng thiết kế (`migrate` exit 0 hai lần; MD5 `tabSingles` trước = sau) | `install.py:44-56` | — |
| 7 Touchpoint: 28 dòng của design | cả 28 đều có trong diff; thêm 7 file không có trong design (3 dòng bên dưới) | — | — |
| 7 thêm `gateway/__init__.py`, `gateway/test_gateway.py`, `erp_ai_credential.json` | khác (ngoài design) | `gateway/__init__.py:23-24,154-155`; `erp_ai_credential.json` (mô tả) | rework 1, R1/R4 (xem 1.1) |
| 7 thêm `test_doctype_descriptions.py`, `test_handlers.py`, `test_runner_status.py` | khác (ngoài design) | `test_handlers.py:2`; `test_runner_status.py:367` (đổi tên đơn vị `set_classification` → `apply_route`) | T19 `DESIGN_CONFLICT` hai lần (kỳ vọng 31 trường mô tả, kỳ vọng `max_tokens` 400), tech-lead mở rộng touchpoint (progress.md:122) |
| 7 thêm `erp_ai/tests/test_test_utils.py` (file mới) | khác (ngoài design) | `test_test_utils.py` (+209) | không ghi nhận |
| 8 Test plan: 64 tên test | 63 tên khớp và `pass`; 1 tên tách đôi | `test_runner_routing.py:339,355` | NFR-4: `test_fake_key_absent_from_comment_log_task` thành `test_fake_key_in_prefixes_absent_from_the_posted_comment` và `test_fake_key_in_read_config_absent_from_comment_log_task_logger` (acceptance.md, NFR-4); review-24.md: mở rộng "gieo vào credential" thành mọi đầu vào cấu hình lần chạy đọc |
| 8 AC-13 (i) test | khác: bật `disable_document_sharing` thật, không vá `create_routed_task` | `test_runner_routing.py:1136-1172` | rework 1, mục 4 (review-R3.md) |
| 8 Test luật ADR (8 test) | đúng thiết kế (8/8 `pass`; T26 thêm 2 luật và 10 ca tự kiểm bộ quét) | `test_architecture.py` | xem 1.5 |

Đã so: 8 mục của design (1 bối cảnh và D-1..D-17, 2 dữ liệu, 3 hợp đồng, 4 luồng, 5 quyền, 6 migration, 7 touchpoint, 8 test plan) với 28 touchpoint của design và 35 file thực tế. Bảng trên có 29 dòng, trong đó 11 dòng "khác" (3.4, 3.5, 3.6, D-8, savepoint, 4 dòng touchpoint/mở rộng touchpoint, 2 dòng test plan); các D-3, D-5, D-6, D-7, D-10, D-11, D-13, D-14, D-16, D-17 đúng thiết kế theo acceptance AC-3..AC-16 (`pass`), không có dòng riêng.

## 2. Kết quả đo được (từ acceptance.md, `e5e1a16`)
- `cmd.test`: `Ran 885 tests in 162.894s`, OK; junit 885 pass, 0 fail, 0 error, 0 skip, 34 module. `cmd.lint` exit 0 (12 hook). `cmd.build` exit 0. `cmd.migrate` exit 0 (log không có `error`/`traceback`).
- AC-1..AC-18 và NFR-1..NFR-4: đạt. Chạy cả bộ không đổi Has Role của tài khoản agent (99 → 99), số HD Ticket, Task, ToDo, ERP AI Log, Comment, SLA, HD Team, Assignment Rule trước = sau.
- Eval thật (AC-15, E1/E2): `Overall accuracy: 100.0% (2/2)`, `Priority match 2/2`, `Team match 2/2`, `max_tokens hits: 0`, output lớn nhất 285. Mẫu chỉ 2 phiếu có nhãn, cùng đầu mục B, nên 100% không nói gì về độ đúng chung (spec A-8: eval chỉ báo số).
- Phát hiện còn mở của qa: không blocker, không major.

## 3. Nợ kỹ thuật còn lại (đề xuất đưa vào `docs/team/debt.md`; writer không sửa file đó, team-leader quyết)
| Mục | Nguồn |
|---|---|
| Thông báo "ma" khi lỗi sau `notify_assignment` | mục 1.6 |
| Model phân loại không phải Haiku vẫn có thể bị cắt ở 600 token; FEAT-003 nền chưa có bản sửa | mục 1.1 |
| 2 khe hở bảo vệ tĩnh (tên bộ phận; `runner._route` không bị quét `.save()`) và minor của bộ quét | mục 1.5 |
| `route_ticket.py:115` lặp kiểm tra chia sẻ của Frappe; cờ `sharing_off` ở `runner.py:407` có thể thay bằng đọc lý do action cuối | review-R3.md |
| `design.md` chưa cập nhật D-8, 3.4–3.6, 4.2 (STD-DOC-4) | review-R1-round1.md, review-R3.md |
| AC-6 ca `[tracecore]`, ca người không hợp lệ và AC-12 ca D chỉ ở mức unit, không qua runner | acceptance.md |
| AC-10 ca "phiếu ở `L0`" thay bằng `apply_route` điểm 0 | acceptance.md |
| Eval mẫu 2 phiếu cùng đầu mục B | acceptance.md |

## 4. Release notes (cho người dùng)
Người đọc: System Manager (giữ cấu hình), HD Agent, người duyệt. Mỗi câu có nguồn AC hoặc file trong ngoặc. Bản đầy đủ cho người quản trị ở `docs/HuongDan_QuanTri_DinhTuyen.md`.

### Đổi gì
- **Điểm trên phiếu.** Mỗi phiếu mới được bot chấm hai điểm: độ phức tạp và độ quan trọng, mỗi điểm 1–3, kèm một câu lý do (tối đa 25 từ). Điểm ghi vào `ERP AI Log` ở mọi mức, kể cả `L0`; từ `L1` ghi thêm lên phiếu ở ba trường chỉ đọc `ai_complexity`, `ai_importance`, `ai_score_reason` (AC-1, AC-2). Model trả điểm sai hoặc thiếu thì coi là "không có điểm": hai điểm bằng 0, lý do rỗng, ưu tiên theo ánh xạ đầu mục như trước. 0 nghĩa là chưa chấm; trường điểm không bao giờ rỗng (AC-1, Amendment 1 mục 3).
- **Mức ưu tiên lấy từ điểm.** Thứ tự xét, gặp quy tắc nào khớp trước thì dừng (AC-3): tiêu đề có `[GẤP]` → `Urgent`; đầu mục F → `Low`; đầu mục E → bot không ghi ưu tiên (theo COO đặt); đầu mục A và độ quan trọng 3 → `Urgent`; còn lại → mức cao hơn giữa mức mặc định của đầu mục trong `category_mapping` và mức theo độ quan trọng trong bảng `importance_priority` (mặc định: 2 và 3 → `High`, 1 → không nâng). Độ phức tạp không đổi mức ưu tiên; nó dành cho `condition` của SLA. Sửa bảng `importance_priority` thì lần chạy sau dùng giá trị mới, không cần deploy (AC-4).
- **Nhóm.** A, B, C, F lấy nhóm theo `category_mapping` như trước. D và E lấy nhóm của bộ phận mà model chọn, chỉ khi bộ phận đó có trong bảng `departments`, nhóm có tồn tại và không nằm trong `excluded_teams`; ngược lại bot không ghi nhóm và nhật ký ghi lý do (AC-5).
- **Người phụ trách** (cần bật công tắc). Bot gán đúng một người theo bảng người mặc định theo đầu mục; tiền tố tiêu đề (ví dụ `[tracecore]` cho đầu mục A) chọn người khác; D/E dùng trưởng bộ phận. Người đó nhận đúng một thông báo gán của Helpdesk (AC-6, AC-14). Bot không bao giờ gán tài khoản agent (AC-8) và chỉ gán HD Agent đang hoạt động (AC-6). Không có người hợp lệ thì bot đăng đúng một comment nhờ trưởng nhóm phân công (AC-8).
- **Không giành việc.** Phiếu đã có người được gán (bất kể ai gán, kể cả Assignment Rule của nhóm gán ngay trong lần lưu nhóm của bot), phiếu do người đã phân loại, công tắc tắt, hoặc mức `L0` thì bot không gán, không tạo Task (AC-7). Nhóm có Assignment Rule đang bật và có người thì rule gán, bảng người mặc định không có hiệu lực (AC-6, Amendment 1 mục 4).
- **SLA do Helpdesk tính.** Bot không tự gán `response_by`, `resolution_by` (AC-10). Muốn SLA khác nhau theo độ phức tạp, người cấu hình tạo SLA có `condition` đọc `doc.ai_complexity`. Bot chỉ báo: phiếu không có SLA nào áp vào → một dòng cảnh báo trong nhật ký và một comment "Chưa có SLA áp vào phiếu, cần System Manager cấu hình." (AC-11); SLA đang áp xử lý chậm hơn mức mong đợi của đầu mục trong `expected_sla` → một dòng cảnh báo nêu hai con số, không comment (AC-12). Đầu mục D, E không bị kiểm.
- **Task cho đầu mục C/D** (cần bật công tắc). Khi bot vừa gán được người, bot tạo đúng một Task có trường `ai_ticket` trỏ tới phiếu, giao cho người đó. Chạy lại vẫn một Task; phiếu đã có Task liên kết thì không tạo thêm (AC-13). Nếu site đang tắt chia sẻ tài liệu và người đó không đọc được Task: không Task, một comment "…không giao được Task: chia sẻ tài liệu đang tắt. Nhờ trưởng nhóm giao Task." (AC-13 (i)); người vẫn được gán vào phiếu.
- **Truy vết.** Mọi lần ghi (ưu tiên, nhóm, người, Task) và mọi lần từ chối nằm trong `actions` của bản ghi `classify` ở `ERP AI Log`, kèm giá trị trước/sau; người ghi bằng user ID (AC-16). Bản ghi có thêm 4 cột `predicted_complexity`, `predicted_importance`, `predicted_score_reason`, `predicted_assignee`.
- **Cấu hình mới trên `ERP AI Setting`** (nhóm "Quy tắc định tuyến"): `routing_rules` (JSON: người mặc định, bộ phận → nhóm và trưởng bộ phận, bảng độ quan trọng → ưu tiên tối thiểu, SLA mong đợi theo phút) và công tắc `auto_assign_enabled` ("Tự gán người và tạo Task", tắt sẵn). Lưu `routing_rules` sai dạng bị chặn, thông báo nêu chỗ sai (AC-4). Cài lại không ghi đè giá trị đã sửa.
- **Eval offline** báo thêm: tỷ lệ khớp ưu tiên, tỷ lệ khớp nhóm, phân bố hai điểm, số token đầu ra lớn nhất của bước phân loại và số lần bị cắt (AC-15).
- **Sửa lỗi cắt phân loại:** bước phân loại với model `claude-haiku-*` tắt thinking nên không còn bị cắt ở 600 token (AC-15, mục 1.1). Model phân loại khác Haiku không được tắt thinking và vẫn có thể bị cắt.
- Không thêm lời gọi model cho mỗi phiếu (NFR-1). Không tạo, sửa SLA, HD Team hay Assignment Rule (NFR-2).

### Ai bị ảnh hưởng
- System Manager: phải điền `routing_rules` và làm các việc ở mục 5 trước khi bật công tắc.
- HD Agent: thấy điểm và lý do chấm (user role `Agent` đọc được ba trường, AC-2); nhận thông báo gán và Task khi công tắc bật.
- Người tạo phiếu: không đổi cách tạo phiếu.

### Cần làm gì
- Mặc định sau khi nâng cấp: công tắc `auto_assign_enabled` tắt; danh sách người rỗng. Bot vẫn chấm điểm và đặt ưu tiên theo điểm từ `L1`, nhưng chưa gán ai và chưa tạo Task (AC-7 (c)). Chạy `bench --site <site> migrate`.
- Ưu tiên có thể khác trước vì nay lấy theo điểm (mục 4, "Mức ưu tiên lấy từ điểm"). Muốn giữ ưu tiên theo ánh xạ như cũ, đặt `importance_priority` = `{"1": "", "2": "", "3": ""}` (design mục 6). Riêng `[GẤP]` → `Urgent`, F → `Low`, A với quan trọng 3 → `Urgent` là quy ước cố định.
- Làm 8 việc ở mục 5 theo thứ tự, công tắc là việc cuối.

## 5. Việc của người trên site `miyano` (DoD "phần việc của người")
Không phải điều kiện merge. Không agent nào làm các việc này (STD-OPS-7). Số liệu là ảnh chụp của qa ngày 2026-11-12 (`research-site.md`), chạy lại câu kiểm trước khi làm. Chi tiết từng bước và câu kiểm ở `docs/HuongDan_QuanTri_DinhTuyen.md`. Tại lần verify 2 (2026-11-13), Has Role của tài khoản agent vẫn 99: chưa làm việc nào.
1. Gỡ 97 role thừa khỏi tài khoản agent, chỉ giữ `ERP AI Agent` và `Agent`.
2. Tắt hoặc xóa SLA `SLA Priority` (rác test của Helpdesk, đang bật, `condition` bắt `High`/`Urgent`/`Low`) và dọn `Test Holiday List`, `_Test Holiday List` nếu không dùng.
3. Sửa team `IT` và `Nhân sự & Hành chính` đang trỏ tới Assignment Rule không còn tồn tại.
4. Tạo HD Agent đang hoạt động cho mọi người sẽ ghi vào bảng người (site đang có 0 HD Agent).
5. Điền `routing_rules`: người mặc định cho từng đầu mục A, B, C, F (cả F, nếu để trống mỗi phiếu F nhận một comment xin phân công, design D-17), bảng bộ phận → nhóm và trưởng bộ phận cho D/E; tạo team cho bộ phận còn thiếu (ví dụ `Tài chính Kế toán`).
6. Xem lại `excluded_teams` (đang rỗng, khác mặc định hai team).
7. Tắt Assignment Rule của nhóm nào muốn dùng bảng người mặc định (`Billing`, `Product Experts` đang có rule bật, chưa có người).
8. Sau cùng mới bật `auto_assign_enabled` (site đang ở `L3`, công tắc là chốt chặn duy nhất của việc gán và Task).

Mẫu `condition` SLA an toàn trên trường điểm: xem `docs/HuongDan_QuanTri_DinhTuyen.md`, mục 3. Một `condition` lỗi chặn mọi lần lưu phiếu, của cả người lẫn bot (AC-18: bot dừng sạch, 0 ToDo, 0 Task, 0 comment định tuyến, phiếu không đổi).

## 6. CHANGELOG
Đã thêm dưới `## [Unreleased]` trong `CHANGELOG.md`: 3 mục Added, 1 mục Changed, 1 mục Fixed, mỗi mục kết thúc `(FEAT-006)`. Kiểm: `grep -c "FEAT-006" CHANGELOG.md` (kỳ vọng 5).

## 7. Nợ sau G4
| Mục DoD qa ghi chủ | Đã làm | Kiểm lại (lệnh → kết quả) |
|---|---|---|
| As-Built | `docs/team/features/FEAT-006/asbuilt.md` | `test -f docs/team/features/FEAT-006/asbuilt.md` → có |
| Tài liệu người dùng (đọc điểm, bảng người/mức, SLA theo độ phức tạp, mẫu `condition`, Assignment Rule, gỡ role thừa); STD-DOC-2 (README dòng 10, 39) | `README.md` (bảng mức `L1`, bước 2–5 "Cấu hình và bật", mục "Định tuyến theo điểm", mục "Bộ đánh giá offline"), `docs/HuongDan_QuanTri_DinhTuyen.md` | `grep -n "routing_rules\|ai_complexity" README.md` → khớp (mục 8) |
| CHANGELOG | `CHANGELOG.md` | `grep -n "FEAT-006" CHANGELOG.md` → khớp |
| As-Built ghi `thinking: disabled` cho `claude-haiku-*`, không nâng trần; D-8 lỗi thời; `TaskSharingDisabled`, `REASON_TASK_FAILED` chưa có trong design | mục 1.1, 1.2 của file này | `grep -n "claude-haiku\|TaskSharingDisabled\|REASON_TASK_FAILED" docs/team/features/FEAT-006/asbuilt.md` → khớp |
| CI xanh trên PR | chưa có PR | để `/team:pr` và `/team:release` kiểm (`gh pr checks`) |

## 8. Đối chiếu README với hành vi đã nghiệm thu
README cũ, dòng 10 (bảng `L1`) ghi ưu tiên và Task như trước FEAT-006, dòng 39 (bước 3) mô tả `category_mapping` là nguồn ưu tiên. Hai chỗ đã sửa: ưu tiên nay lấy từ điểm (AC-3), Task có thêm đường tự tạo cho C/D khi công tắc bật (AC-13). Kết quả `grep` dán trong phần trả lời của writer.

## Rollback
<!-- /team:release viết trước lần deploy đầu: điều kiện kích hoạt, lệnh (từ docs/team/ci.md), phần dữ liệu, thời gian dự kiến -->
Gợi ý từ design mục 6 (để `/team:release` dùng): tắt `auto_assign_enabled` thì 0 ToDo, 0 Task mới; `permission_level = L0` thì bot không ghi gì lên phiếu. Gỡ mã: revert các commit của feature rồi `migrate` (revert mã TRƯỚC, nếu không `after_migrate` tạo lại trường). Điều kiện tắt công tắc: log có `route apply_route:` lặp lại trên nhiều phiếu; có phiếu bị gán hai người; có Task không người được giao.

<!-- devops thêm dòng sau khi lên prod thành công: Released: <tag> <YYYY-MM-DD> -->
