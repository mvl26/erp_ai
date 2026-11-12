# Progress FEAT-006

Edit không có trong bộ công cụ của tech-lead; tick và đổi touchpoint nằm ở đây, gộp vào `tasks.md` khi xong. Dòng ở đây thắng `tasks.md` khi lệch.

Quy trình:

- role-policy chặn tech-lead chạy `PYTHONPATH=... bench ...`: `cmd.test` do dev chạy trên đầu nhánh task. Tech-lead kiểm cây mã sau merge bằng `git diff --stat <head task> team/FEAT-006 -- . ':!docs'` (rỗng = cây mã trùng đầu nhánh đã chạy xanh).
- Site `miyano` dùng chung: hai `cmd.test` đồng thời gây `QueryDeadlockError 1213` giả (R1: 37 error; T4/T5 song song: 45 và 34 error). Từ sau T5: MỘT dev mỗi lần; reviewer chạy song song với dev kế tiếp được vì reviewer không chạy bench.
- Nhánh task đang được checkout trong worktree dev cũ thì dev sửa vòng sau tạo nhánh `-reworkN` (hoặc `-cont`); tech-lead `merge --ff-only` vào nhánh task từ worktree của dev cũ, hoặc merge thẳng nhánh mới.
- `review-NN.md`: NN = số task (T9b → `review-09b.md`).
- BASE của task = `git rev-parse team/FEAT-006` ngay trước lần gọi dev (commit docs đứng trước lần gọi dev nên BASE là đầu nhánh sau commit docs đó).
- role-policy chặn tech-lead ghi `.team/active-build` (chỉ cho `docs/team/**`, `.team/current.json`, `.team/session/**`): chặng 4a không tạo được cờ này; `stop-check.sh` không chạy lint/test cho lần dừng này (đã báo team-leader).

## Đổi touchpoint

- T1 (người duyệt 2026-11-12): thêm `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_status.py`, `erp_ai/tests/test_install.py`. Chỉ sửa kỳ vọng cũ (STD-TEST-5).
- T6 (tech-lead; team-leader chấp nhận ngày 2026-11-12, journal "quyết định 4 điểm"): thêm `erp_ai/agent/test_runner_routing.py`, chỉ đổi `priority == "High"` → `"Urgent"` cho A + quan trọng 3 (kỳ vọng của bản giả T1 trái R4/AC-3).
- T11 (tech-lead; team-leader chấp nhận ngày 2026-11-12): thêm `erp_ai/tests/test_doctype_descriptions.py`, chỉ thêm dữ liệu ghim (`field_count` 22 → 24 và `phrases` cho `auto_assign_enabled`, `routing_rules`); không nới khẳng định cũ.
- T9b (task chèn mới, quyết định (1)+(3) của team-leader): touchpoint `erp_ai/agent/routing.py`, `erp_ai/agent/test_routing.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`; depends: T9, T11.
- T14 (tech-lead, cần team-leader xác nhận ở C3): thêm `erp_ai/agent/test_agent_runner.py`, chỉ sửa kỳ vọng `after` của 3 test (bỏ `ai_complexity`/`ai_importance` không đổi) vì `before`/`after` nay chỉ chứa trường đã đổi (tiêu chí T14, AC-16); cùng kiểu T1/T6/T11 (STD-TEST-5).
- T18 (tech-lead, cần team-leader xác nhận ở C4a, ngày 2026-11-12): thêm `erp_ai/agent/routing.py`, chỉ thay lời gọi `resolve_ticket_values` (đã xóa) bằng tra thẳng `mapping` (`ticket_type`, `agent_group or None`) và bỏ import thừa; hành vi `decide_route` không đổi. Design mục 7 giao việc đổi chỗ gọi này cho T18.
- T19 (tech-lead, cần team-leader xác nhận ở C4a, ngày 2026-11-12): thêm `erp_ai/tests/test_doctype_descriptions.py` (chỉ dữ liệu ghim cho 4 cột mới: `field_count` 31 → 35, 4 khóa `phrases`, `read_only_fields`), `erp_ai/agent/test_agent_runner.py` (dòng 240: `max_tokens` 400 → 600 theo D-8; setUp thêm `routing_rules=make_routing_rules()` theo finding review), `erp_ai/tests/test_handlers.py` (dòng 241: 400 → 600). Cùng kiểu T1/T6/T11/T14 (STD-TEST-5).

## Tick

- [x] T1 — BASE=d8fb3e9, 2 vòng, merge 2393337, review-01, cmd.test 660 OK
- [x] T3 — BASE=4cfd68f, 1 vòng, merge d4a766c, review-03, cmd.test 664 OK
- [x] T6 — BASE=4cfd68f, 1 vòng, merge b8d2607, review-06, cmd.test 668 OK
- [x] T4 — BASE=b1af21f, 1 vòng, merge 6ebb766, review-04; test_one xanh; cmd.test nối tiếp: xem dòng nền 703 OK bên dưới
- [x] T5 — BASE=b1af21f, 1 vòng, merge 1aa1a79, review-05; test_one xanh; cmd.test nối tiếp: xem dòng nền 703 OK bên dưới
- [x] T7 — BASE=686aa3f, 2 vòng, merge 2851bca, review-07; dev cmd.test 679 OK (vòng 1)
- [x] T2 — BASE=686aa3f, 2 vòng, merge 8473884, review-02; dev cmd.test 687 OK
- [x] T8 — BASE=2851bca, 2 vòng, merge 61e51f2, review-08; dev cmd.test 688 OK (vòng 1)
- Nền nối tiếp (T4, T5, T7, T2, T8 gộp): `cmd.test` trên cây mã của 61e51f2 (đồng nhất với 8c5af9c): Ran 703 tests, OK.
- [x] T9 — BASE=8c5af9c, 3 vòng (2 vòng sửa), merge 896b7ac, review-09; cmd.test đầu nhánh task 989c37d: Ran 710 tests, OK
- [x] T10 — BASE=7fa9ad9, 1 vòng, merge a9e7e2e, review-10; cmd.test đầu nhánh task 2f0b871: Ran 723 tests, OK
- [x] T11 — BASE=f1a732b, 1 vòng (sau DESIGN_CONFLICT được giải), merge 27d18fe, review-11; cmd.test đầu nhánh task 776839a: Ran 728 tests, OK
- [x] T12 — BASE=449e2b5, 2 vòng, merge 1f0b3f7, review-12; cmd.test đầu nhánh task 1db4533: Ran 738 tests, OK
- [x] T9b — BASE=8a1bd31, 2 vòng (1 vòng sửa), merge 4dc14d7, review-09b; cmd.test đầu nhánh task 566f796: Ran 744 tests, OK
- [x] T13 — BASE=5688f13, 2 vòng (1 vòng sửa), merge 43cca1f, review-13; cmd.test đầu nhánh task 388f562: Ran 751 tests, OK
- [x] T14 — BASE=b74303f, 2 vòng (1 vòng sửa, một lần DESIGN_CONFLICT được giải), merge 8fdc05f, review-14; cmd.test đầu nhánh task 809fac6: Ran 764 tests, OK
- [x] T15 — BASE=6b4b9f7, 1 vòng, merge 434fa4e, review-15; cmd.test đầu nhánh task e3e2500: Ran 769 tests, OK
- [x] T16 — BASE=24f04a4, 1 vòng, merge 7fdf122, review-16; cmd.test đầu nhánh task a24b9a2: Ran 780 tests, OK
- [x] T17 — BASE=ebe8431, 2 vòng (1 vòng sửa), merge 6ab22a8, review-17; cmd.test đầu nhánh task 68da7fc: Ran 783 tests, OK
- [x] T18 — BASE=5718e2f (docs commit 5718e2f là đầu nhánh sau review-17; dev dựng nhánh từ a62944e... xem dưới), 1 vòng, merge efba510, review-18; cmd.test đầu nhánh task 029890e: Ran 783 tests, OK
- [x] T19 — BASE=a62944e, 2 vòng (1 vòng sửa; hai DESIGN_CONFLICT được giải bằng mở rộng touchpoint), merge 13a67f1, review-19; cmd.test đầu nhánh task c4d821f: Ran 792 tests, OK

Ghi chú BASE T18: tech-lead ghi `BASE=5718e2f` (đầu nhánh `team/FEAT-006` ngay trước lần gọi dev T18, sau commit docs review-17); diff của review là `5718e2f..029890e`. Đầu nhánh sau docs review-18 là a62944e (BASE của T19).

## Checkpoint C2 (trên 1f0b3f7)

- `bench --site miyano migrate` (cmd.migrate): exit 0; chỉ có dòng `Updating DocTypes for erp_ai ... 100%` và `Updating Dashboard for erp_ai`, không lỗi.
- `ensure_setup` chạy hai lần (sau migrate đã chạy một lần qua after_migrate): ảnh chụp 2 và 3 bằng nhau ở `Task-ai_ticket` (mọi cột, kể cả modified), dòng Custom DocPerm Task/ERP AI Agent (share 1, if_owner 1), `routing_rules` và `auto_assign_enabled` trong tabSingles, 11 field `ai_*` của HD Ticket, Has Role của tài khoản agent (99 dòng), HD Form Script, User; tổng Custom Field 247, Custom DocPerm 1360.
- `cmd.test` (`bench --site miyano run-tests --app erp_ai`) trên 1f0b3f7: exit 0, `Ran 738 tests in 116.196s`, `OK`.
- `routing_rules` trong DB là JSON mặc định; `auto_assign_enabled` = 0; `validate_routing_config` chấp nhận.

## Checkpoint C3 (trên 7fdf122; cây mã trùng a24b9a2, đầu nhánh T16)

- `cmd.test` (`bench --site miyano run-tests --app erp_ai`, dev chạy một mình trên đầu nhánh T16 a24b9a2): `Ran 780 tests in 129.264s`, `OK`. Tech-lead: `git diff --stat a24b9a2 team/FEAT-006 -- . ':!docs'` rỗng, tức cây mã sau merge 7fdf122 trùng cây đã chạy xanh (role-policy chặn tech-lead chạy bench với PYTHONPATH).
- Lớp ghi chạy qua Helpdesk thật (không giả lập), mỗi ca có đột biến đỏ rồi xanh trong review:
  - SLA do Helpdesk chọn theo `condition`: `TestSlaFromHelpdesk::test_sla_chosen_by_complexity_condition`, `test_ge_condition_saves_l0_and_new_ticket` (review-14).
  - Assignment Rule / gán người qua `assign_to.add` thật: `TestAssignOwner::test_ticket_never_shared_one_todo_one_notification` (1 ToDo, 1 Notification Log, DocShare của phiếu = 0; review-15). Rule do Helpdesk chạy trong cùng lần `doc.save()` của `apply_route` là việc của T20/T21 (runner), chưa thuộc C3.
  - Chia sẻ Task: `TestCreateRoutedTask::test_assignee_without_projects_user_gets_share` (người được giao không có Projects User vẫn thấy Task nhờ DocShare read=1), `test_sharing_disabled_raises` (lỗi chia sẻ ném lên, không bị bắt; review-16).
- Đã thêm ở chặng 3: `erp_ai/agent/site_facts.py` (T13), `apply_route` đầy đủ (T14), `assign_owner`/`post_routing_comment` (T15), `create_routed_task` + `create_task` đặt `ai_ticket` (T16), bộ kiểm `routing_rules` từ chối trống và khóa tiền tố rỗng (T9b).
- Chưa chạy `migrate` ở C3: chặng 3 không đổi schema/DocType/install (chỉ `agent/` và `routing.py`, `erp_ai_setting.py` logic kiểm).

## Checkpoint C4a (trên đầu nhánh sau merge 13a67f1; cây mã trùng c4d821f)

- `cmd.test` (`bench --site miyano run-tests --app erp_ai`, dev chạy một mình trên đầu nhánh T19 c4d821f, cơ sở a62944e có T17 + T18): `Ran 792 tests in 135.148s`, `OK`. Tech-lead: `git diff --stat c4d821f 13a67f1 -- . ':!docs'` rỗng, tức cây mã sau merge 13a67f1 trùng cây đã chạy xanh.
- `migrate` (dev T19, `PYTHONPATH=<worktree> bench --site miyano migrate`): exit 0; `show columns` của `tabERP AI Log` có `predicted_complexity` int, `predicted_importance` int, `predicted_score_reason` text, `predicted_assignee` varchar.
- Đã thêm ở chặng 4a: `set_classification` dùng `decide_route` (R1–R5 một chỗ, T17); `resolve_ticket_values` đã xóa, `grep` rỗng (T18); runner nạp `routing_rules`/`auto_assign`/`departments`, 600 token, 4 cột nhật ký, `decide_route` dùng `site_facts`/`policy` thật (T19). Chưa có (u1)–(u4) trong runner: `_route` nhận `auto_assign` và `subject` nhưng chưa dùng (T20/T21).

## Quyết định của team-leader sau C2 (journal "quyết định 4 điểm")

1. `routing_rules` trống: bộ kiểm từ chối khi lưu (T9b, xong).
2. Mở rộng touchpoint T6 và T11: chấp nhận (ghi ở trên).
3. Khóa tiền tố rỗng `""`: T8 giữ bỏ qua; bộ kiểm từ chối khi lưu (T9b, xong).
4. 99 Has Role của tài khoản agent: ngoài FEAT-006.

## Việc dặn trước cho các task sau (từ review)

- T20: `applied` của bản ghi `classify` dùng `result["ok"]`, không dùng "`after` khác rỗng" (review-14, `runner.py:276`); `applied_sla` có thể trả `resolution_s=None` khi phiếu có `sla` mà không có `priority`, T20 phải xử lý (review-13).
- T20: `skipped_fields` = `skipped` của (u1) cộng `decision.notes` (design 4.2); `apply_route` (`route_ticket.py:41`) gọi `_existing_values` không truyền `notes` nên có thể ghi lý do "ánh xạ không có giá trị" cho D/E không bộ phận: bảo đảm bản ghi không có hai lý do mâu thuẫn (review-17).
- T21: chỉ gọi `post_routing_comment` khi `lines` khác rỗng (review-15; `post_routing_comment([], ctx)` sẽ đăng comment rỗng).
- T21/T26: sửa `description` của `auto_assign_enabled` (`erp_ai_setting.json:207`) cho khớp hành vi: "chưa có ai được gán" xét sau (u1) nên Assignment Rule của nhóm gán trong cùng lần save thì bot không gán; Task chỉ tạo khi bot tự gán được người, phiếu chưa có Task, chia sẻ tài liệu bật (review-19).
- T22: lỗi chia sẻ ném `frappe.ValidationError` từ `create_routed_task` (không bị bắt); runner rollback Task + ToDo trong savepoint (review-16).
- T26: thêm kiểm tĩnh `test_assign_to_only_in_route_module`, `test_no_share_bypass` (review-15, review-16).
- design.md: bổ sung 2 hàng lỗi mới ở 3.3 (trống; khóa tiền tố rỗng, review-09b) và chỉnh 3.4 cho khớp tasks.md T14 (review-14); chỉnh dòng 108 ("không đọc bảng hệ thống trong `tools/`") cho khớp dòng 234 (`tools/` truyền `site_facts.is_active_agent`, review-17); việc của designer/khi gộp.
- Dọn minor khi gộp: review-18 (`test_routing.py:92-104` dùng `_decide`; ca khẩn trùng), review-17 (không có ca phân biệt `routing_config or {}`).

## Đang build

Dừng ở C4a theo `--decide` (chặng 4a: T17, T18, T19 xong). Việc kế tiếp: T20 (depends T19, T14, T13), T21 (T20, T15, T8), T22.. theo `depends:`; MỘT dev mỗi lần.

## Nhật ký

- 2026-11-12 T1: dev lần 1 DESIGN_CONFLICT; người duyệt mở rộng touchpoint; dev lần 2 DONE; reviewer vòng 1 request-changes (3 major); dev sửa; vòng 2 approve; merge; 660 test OK.
- 2026-11-12 R1 (T3 ∥ T6): T6 DESIGN_CONFLICT (test T1 giả) → tech-lead mở rộng touchpoint 1 file; cả hai approve vòng 1.
- 2026-11-12 R2/R3 (T4 ∥ T5): hai dev song song làm `cmd.test` deadlock lẫn nhau; cả hai approve vòng 1; merge không xung đột; chuyển sang chạy từng dev một.
- 2026-11-12 T7, T2, T8: mỗi task request-changes vòng 1, approve vòng 2; đã merge; ghi tick và review-02/07/08 ở chặng 2.
- 2026-11-12 T9: vòng 1 request-changes (major STD-TEST-8: 5 hàng bộ kiểm không có ca); vòng 2 còn thiếu bảo vệ `default`/`prefixes` của `assignees`; vòng 3 approve. Nền nối tiếp 703 OK nhờ dev T9 chạy trước khi sửa.
- 2026-11-12 T10: dev DONE, reviewer approve vòng 1; merge a9e7e2e; 723 OK.
- 2026-11-12 T11: dev DESIGN_CONFLICT (`test_doctype_descriptions` ghim 22 trường); tech-lead mở rộng touchpoint 1 file và commit phần dở; dev sau DONE; reviewer approve vòng 1; reviewer nêu quyết định thiết kế "routing_rules trống" cần người chốt (review-11); merge 27d18fe; 728 OK.
- 2026-11-12 T12: reviewer vòng 1 request-changes (3 major: bảo vệ Task bị che, thiếu dòng mồi share, nghi cache meta); vòng 2 approve (finding cache được reviewer rút lại); merge 1f0b3f7; 738 OK.
- 2026-11-12 C2: migrate exit 0, ensure_setup lần hai không đổi gì, cmd.test 738 OK; dừng báo cáo.
- 2026-11-12 T9b: vòng 1 request-changes (major STD-ERR-3: thông báo trống nhắc tên hằng Python; minor: `.strip()` trên giá trị không phải chuỗi); vòng 2 approve; merge 4dc14d7; 744 OK.
- 2026-11-12 T13: vòng 1 request-changes (major STD-TEST-2: bộ lọc `reference_type` không có ca mồi; 3 minor); vòng 2 approve; merge 43cca1f; 751 OK.
- 2026-11-12 T14: vòng 1 request-changes (2 major: `before`/`after` liệt kê trường không đổi; test giả quyền bỏ qua `permission_type`); dev sửa DESIGN_CONFLICT vì 3 test `test_agent_runner.py` (kỳ vọng cũ) → tech-lead mở rộng touchpoint 1 file, dev khác sửa kỳ vọng; vòng 2 approve; merge 8fdc05f; 764 OK.
- 2026-11-12 T15: reviewer approve vòng 1 (minor: `deny_read` của test từ chối đọc bỏ qua đối số user); merge 434fa4e; 769 OK.
- 2026-11-12 T16: reviewer approve vòng 1 (3 minor); merge 7fdf122; 780 OK.
- 2026-11-12 C3: dừng báo cáo; vai đã dùng: dev, reviewer (không tính lần gọi lại).
- 2026-11-12 T17: vòng 1 request-changes (major STD-DESIGN-2: D/E không bộ phận ghi sai lý do "ánh xạ không có giá trị"); dev sửa (lý do từ `decision.notes`); vòng 2 approve; merge 6ab22a8; 783 OK.
- 2026-11-12 T18: tech-lead phát hiện ở preflight `routing.py` còn import/gọi `resolve_ticket_values` (ngoài touchpoint) nên mở rộng touchpoint; reviewer approve vòng 1 (đủ 8 ca cũ); merge efba510; 783 OK.
- 2026-11-12 T19: dev DESIGN_CONFLICT hai lần (kỳ vọng `test_doctype_descriptions` 31 trường; kỳ vọng `max_tokens` 400 ở `test_agent_runner`, `test_handlers`) → tech-lead mở rộng touchpoint và commit phần dở; dev lần 3 DONE; reviewer vòng 1 request-changes (major STD-TEST-6: test phụ thuộc cấu hình định tuyến của site); dev sửa và gom thành một commit; vòng 2 approve; merge 13a67f1; 792 OK; soát `description` của `auto_assign_enabled` xong, lệch ghi vào việc dặn trước (T21/T26).
- 2026-11-12 C4a: dừng báo cáo sau T19; vai đã dùng: dev, reviewer (không tính lần gọi lại).
