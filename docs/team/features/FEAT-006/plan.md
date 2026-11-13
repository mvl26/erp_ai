Feature: FEAT-006
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 tắt (config.json), để trống. -->

# Plan FEAT-006

- Nhánh feature: `team/FEAT-006` từ `team/FEAT-003` @ `d425faa`, worktree riêng `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006` (worktree chính đang do phiên khác dùng, không checkout ở đó). `config.base_branch` là `main`; PR sau cùng rebase theo thứ tự merge ở dưới.
- Số task: 26 (T1 walking skeleton); song song tối đa: 2 (`limits.max_parallel_dev`)
- Cỡ L. Nguồn: `spec.md` (Amendment 1), `design.md` mục 7 (Touchpoints), mục 8 (Test plan), `arch-impact.md` (Thứ tự merge).
- Số dòng `file:line` trong `design.md` là của nền `7cb654f`; dev dò lại bằng tên hàm.

## Thứ tự
1. **T1** walking skeleton, chạy một mình. Reviewer `approve` rồi mới mở các task còn lại.
2. **T2..T10** nền cho mọi thứ sau: helper test (T2), bộ đọc điểm (T3), prompt phân loại (T4), policy (T5), và chuỗi `routing.py` (T6 ưu tiên → T7 nhóm → T8 người → T9 cấu hình → T10 SLA/bộ phận). Hàm thuần đặt sớm vì rẻ, và mọi bước sau dựa vào hợp đồng của nó.
3. **T11..T13** đưa cấu hình và đọc site vào: Setting (T11), cài đặt (T12, có migrate), `site_facts` (T13).
4. **T14..T17** lớp ghi (`route_ticket.py`, `write_ticket.py`): rủi ro cao nhất (quyền, Assignment Rule, chia sẻ Task) nên làm trước runner `_route`. T18 dọn `resolve_ticket_values`.
5. **T19..T22** runner theo từng đơn vị: nhật ký (T19) → (u1) + SLA (T20) → (u2)(u4) (T21) → (u3) (T22). Mỗi bước dùng lại `_route` của bước trước.
6. **T23..T26** prompt suy luận theo cấu hình, test chốt (chống chèn lệnh, role ghim), eval, luật kiến trúc.

## Nhóm song song
Mỗi dòng là một đợt chạy; hai task trong cùng đợt không chung file (đã đối chiếu bảng "một file một chủ"). Một đợt chỉ mở khi mọi `depends:` của nó đã ticked.
| Đợt | Task | Ghi chú |
|---|---|---|
| R0 | T1 | một mình |
| R1 | T3 ∥ T6 | `classification.py` vs `routing.py` |
| R2 | T4 ∥ T7 | `prompts.py` vs `routing.py` |
| R3 | T5 ∥ T8 | `policy.py` vs `routing.py` |
| R4 | T2 ∥ T9 | `test_utils.py` vs `routing.py` |
| R5 | T10 ∥ T11 | `routing.py` vs Setting |
| R6 | T12 ∥ T19 | `install.py` vs `runner.py` + log JSON |
| R7 | T13 ∥ T14 | `site_facts.py` vs `route_ticket.py` |
| R8 | T15 ∥ T20 | `route_ticket.py` vs `runner.py` |
| R9 | T16 ∥ T21 | `route_ticket.py`+`write_ticket.py` vs `runner.py` |
| R10 | T17 ∥ T22 | `write_ticket.py`+`registry.py` vs `runner.py` |
| R11 | T18 ∥ T25 | `classification.py`+test vs `eval/` |
| R12 | T23 ∥ T24 | prompt+runner+`test_classification` vs `test_runner_routing`+`test_registry` |
| R13 | T26 | `test_architecture.py` |
Migration, `install.py` và JSON DocType chỉ nằm ở T11, T12, T19: không có hai task cùng chạm.

## Shared constraints
Giá trị chép nguyên văn từ spec/design. Mọi task thừa hưởng.
- **Trường HD Ticket** (Custom Field, permlevel 8, `read_only 1`, `module "ERP AI agent"`): `ai_complexity` Int default `"0"`; `ai_importance` Int default `"0"`; `ai_score_reason` Small Text. Điểm ∈ {0,1,2,3}, 0 = không có điểm, không bao giờ NULL (D-2, ADR-020 QĐ 5).
- **Trường Task:** `ai_ticket` Link → HD Ticket, permlevel 0, `search_index 1`, không `read_only` (D-2).
- **Trường ERP AI Setting** (`section_routing`): `auto_assign_enabled` Check default `"0"`; `routing_rules` Code `options "JSON"` (D-1).
- **Cột ERP AI Log** (`section_prediction`): `predicted_complexity` Int; `predicted_importance` Int; `predicted_score_reason` Small Text; `predicted_assignee` Data (D-15). `run_log.ENTRY_TYPES = ("classify", "reason", "skip")` không đổi.
- **Khóa JSON phân loại:** thêm `do_phuc_tap`, `do_quan_trong` (số 1–3), `ly_do_diem` (≤ 25 từ), `bo_phan` (chỉ D/E) (D-3). Điểm theo cặp: một điểm sai thì cả hai 0 và lý do rỗng (D-4).
- **Hằng:** `SCORE_VALUES = (1, 2, 3)`, `SCORE_REASON_MAX_WORDS = 25`, `PRIORITIES = ("Low", "Medium", "High", "Urgent")`, `CLASSIFY_MAX_TOKENS = 600`.
- **Chữ ký cố định** (dùng ở nhiều task, chỉ đổi ở một chỗ):
  - `decide_route(classification, subject, mapping, config, *, team_exists, is_excluded_team, is_active_agent) -> RouteDecision`
  - `RouteDecision(ticket_type, agent_group, priority, assignee, needs_task, notes)` (frozen dataclass)
  - `apply_route(decision, classification, ctx)`, `assign_owner(user, ctx)`, `create_routed_task(user, ticket_subject, classification, ctx)`, `post_routing_comment(lines, ctx)`
  - `site_facts`: `ticket_assignments`, `has_linked_task`, `is_active_agent`, `team_exists`, `applied_sla`
  - `policy`: `auto_assign_enabled(settings)`, `is_excluded_team(team)`
  - `ToolContext.routing_config: dict | None = None` (trường cuối)
- **Cấu hình `routing_rules`:** dạng 3.3 của `design.md`: khóa gốc `assignees`, `departments`, `importance_priority`, `expected_sla`. Mặc định `expected_sla` (phút, phản hồi / xử lý): A 15/480, B 15/240, C 60/1440, D 60/null, E 60/null, F 5/60. `importance_priority` mặc định `{"1": "", "2": "High", "3": "High"}`.
- **Luật ưu tiên:** R1 `[GẤP]`/`[GẬP]` → `Urgent`; R2 F → `Low`; R3 E → không ghi; R4 A + quan trọng 3 → `Urgent`; R5 mức cao hơn giữa ánh xạ đầu mục và bảng `importance_priority`.
- **Thang điểm và 4 khóa JSON** chép nguyên văn từ spec mục Dữ liệu và `design.md` 3.1 vào prompt (T4).
- **Nhật ký:** mọi ghi/từ chối là một phần tử `actions` của bản ghi `classify`: `{"tool", "doctype", "name", "ok", "reason"?, "rule"?}`; `tool` ∈ `apply_route|assign_owner|create_routed_task|post_routing_comment|sla_check`. Không ghi nội dung phiếu (NFR-4').
- **Ràng buộc kiến trúc** (ADR-019..021): `route_ticket.py` không có `TOOLS`/`ToolSpec`, không có trong `TOOL_MODULES`; đúng một `doc.save()` HD Ticket (ở `apply_route`); `assign_to.add` chỉ ở `route_ticket.py`; trong `agent/tools/**` cấm `ignore_permissions`, `db.set_value`, SQL ghi, `set_user`, `get_all`; không `ignore_share_permission`, `assign_to._add(`, `add_docshare`, `frappe.share.add`; công tắc chỉ đọc ở `policy.py`; không phép gán `response_by`/`resolution_by`; không đọc `_assign` để quyết định.
- **Test:** dùng `FrappeTestCase`, `addCleanup(frappe.db.rollback)`, `FakeGateway`, `pin_agent_roles` (T2); test tự tạo team/HD Agent/SLA, không dùng `IT`, `Standard`, `SLA Priority` hay HD Agent có sẵn (A-13). Không `skip`/`xfail` (STD-TEST-4).
- **Chuỗi cố định** (`ASSIGN_REQUEST`, `NO_SLA`, 3 lý do): `design.md` 3.6.

## Một file một chủ
Bảng liệt kê mọi file của build. Hai task cùng file thì chuỗi `depends:` (cột Thứ tự).
| File | Task chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| erp_ai/agent/routing.py (mới) | T1 | T6, T7, T8, T9, T10 | T1 → T6 → T7 → T8 → T9 → T10 |
| erp_ai/agent/test_routing.py (mới) | T6 | T7, T8, T9, T10, T18 | T6 → T7 → T8 → T9 → T10 → T18 |
| erp_ai/agent/site_facts.py (mới) | T13 | — | — |
| erp_ai/agent/test_site_facts.py (mới) | T13 | — | — |
| erp_ai/agent/tools/route_ticket.py (mới) | T1 | T14, T15, T16 | T1 → T14 → T15 → T16 |
| erp_ai/agent/tools/test_route_ticket.py (mới) | T14 | T15, T16 | T14 → T15 → T16 |
| erp_ai/agent/test_runner_routing.py (mới) | T1 | T19, T20, T21, T22, T24 | T1 → T19 → T20 → T21 → T22 → T24 |
| erp_ai/agent/classification.py | T1 | T3, T18 | T1 → T3; T17 → T18 |
| erp_ai/agent/test_classification.py | T3 | T4, T18, T23 | T3 → T4; T18 → T23 |
| erp_ai/agent/prompts.py | T4 | T23 | T4 → T23 |
| erp_ai/agent/runner.py | T1 | T19, T20, T21, T22, T23 | T1 → T19 → T20 → T21 → T22 → T23 |
| erp_ai/agent/test_agent_runner.py | T23 | — | — |
| erp_ai/agent/policy.py | T5 | — | — |
| erp_ai/agent/test_policy.py | T5 | — | — |
| erp_ai/agent/tools/registry.py | T17 | — | — |
| erp_ai/agent/tools/test_registry.py | T24 | — | — |
| erp_ai/agent/tools/write_ticket.py | T16 | T17 | T16 → T17 |
| erp_ai/agent/tools/test_write_ticket.py | T16 | T17 | T16 → T17 |
| erp_ai/install.py | T1 | T12 | T1 → T12 |
| erp_ai/tests/test_install.py | T12 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | T11 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py | T11 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py | T11 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json | T19 | — | — |
| erp_ai/eval/run_eval.py | T25 | — | — |
| erp_ai/eval/test_run_eval.py | T25 | — | — |
| erp_ai/test_utils.py | T2 | — | — |
| erp_ai/tests/test_test_utils.py (mới, ngoài danh sách của `design.md` mục 7: test cho helper T2, nằm dưới `erp_ai`) | T2 | — | — |
| erp_ai/tests/test_architecture.py | T26 | — | — |

## Touchpoint → task (design mục 7)
| Touchpoint | Task |
|---|---|
| routing.py | T1, T6, T7, T8, T9, T10 |
| site_facts.py | T13 |
| tools/route_ticket.py | T1, T14, T15, T16 |
| classification.py | T1, T3, T18 |
| prompts.py | T4, T23 |
| runner.py | T1, T19, T20, T21, T22, T23 |
| policy.py | T5 |
| tools/registry.py | T17 |
| tools/write_ticket.py | T16, T17 |
| install.py | T1, T12 |
| erp_ai_setting.json | T11 |
| erp_ai_setting.py | T11 |
| erp_ai_log.json | T19 |
| eval/run_eval.py | T25 |
| test_utils.py | T2 |
| test_routing.py | T6..T10, T18 |
| test_site_facts.py | T13 |
| tools/test_route_ticket.py | T14, T15, T16 |
| test_runner_routing.py | T1, T19..T22, T24 |
| test_classification.py | T3, T4, T18, T23 |
| test_agent_runner.py | T23 |
| test_policy.py | T5 |
| tools/test_registry.py | T24 |
| tools/test_write_ticket.py | T16, T17 |
| test_erp_ai_setting.py | T11 |
| eval/test_run_eval.py | T25 |
| tests/test_install.py | T12 |
| tests/test_architecture.py | T26 |
28/28 touchpoint có task; không có dòng trống. 0 touchpoint nằm trong `protected_paths`; mọi file mới nằm dưới `erp_ai` (`allowed_new_file_roots`).

## AC → task
| AC | Task |
|---|---|
| AC-1 | T1 (khung), T3, T4, T19 |
| AC-2 | T1, T14, T19 |
| AC-3 | T6, T17, T18, T20 |
| AC-4 | T6, T9, T11, T20 |
| AC-5 | T4, T5, T7 |
| AC-6 | T8, T15, T21 |
| AC-7 | T21 (a, b, c, d) |
| AC-8 | T8, T15, T21 |
| AC-9 | T24 (+ T26 phần tĩnh) |
| AC-10 | T14, T26 |
| AC-11 | T13, T15, T20, T21 |
| AC-12 | T10, T13, T20 |
| AC-13 | T16, T22 |
| AC-14 | T8, T21, T23, T26 |
| AC-15 | T4, T25 (+ bước qa chạy eval thật) |
| AC-16 | T1 (khung), T14, T20, T21, T24 |
| AC-17 | T2, T12, T24 (+ `cmd.test` ở C5) |
| AC-18 | T20 |
| NFR-1 | T19 |
| NFR-2 | T14, T20 |
| NFR-3 | T23 (`test_agent_runner` hiện có xanh) |
| NFR-4 | T16, T24 |
AC-1..AC-18: 18/18 có task. Ghi chú: AC-15 phần lệnh eval thật trên site dev và dán vào `acceptance.md` là việc của qa; AC-15 phần phân bố điểm và AC-12 là mục cắt đầu tiên nếu bị ép (spec "Thứ tự bỏ trước"), không cắt trong kế hoạch này.

## Checkpoints
Mỗi checkpoint: `cmd.test` xanh trên `team/FEAT-006` (đầu ra thật dán vào `review-NN.md`).
| # | Khi | Kiểm |
|---|---|---|
| C0 | Sau T1 (trước khi mở R1) | `cmd.test_one` với `erp_ai/agent/test_runner_routing.py` xanh; `cmd.test` xanh (kể cả `test_architecture`). Reviewer `approve` T1. Kiểm cách chạy trong worktree: `erp_ai` được import từ worktree `feat-006` chứ không từ cây chính (xem Rủi ro R-1) |
| C1 | Sau R5 (T1..T11) | `cmd.test` xanh; `erp_ai/tests/test_doctype_descriptions.py` xanh (mô tả trường ≤ 400 ký tự) |
| C2 | Sau T12 | `cmd.migrate` chạy được trên site dev; chạy `ensure_setup` lần hai không đổi gì; `cmd.test` xanh |
| C3 | Sau T16 (R9) | `cmd.test` xanh; lớp ghi chạy qua Helpdesk thật (SLA, rule, chia sẻ Task) |
| C4 | Sau T22 (R10) | luồng chính chạy đầu-cuối qua runner với `FakeGateway`: phiếu C → ưu tiên, nhóm, người, Task, SLA ghi trong `actions`; `cmd.test` xanh |
| C5 | Sau T26 (cuối) | `cmd.test` xanh toàn bộ; `cmd.lint` sạch; `cmd.migrate` chạy được; `grep -rnE "response_by|resolution_by" erp_ai/agent/` không có phép gán; `grep -rn "resolve_ticket_values\|ROUTING_TABLE" erp_ai/` rỗng; số Has Role của tài khoản agent trước = sau cả bộ test |

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| R-1: `cmd.test_one`/`cmd.test` chạy qua `bench` có thể import `erp_ai` từ cây chính (`apps/erp_ai`, đang ở `team/FEAT-003`, phiên khác dùng) thay vì từ worktree `feat-006` | `python -c "import erp_ai; print(erp_ai.__file__)"` trỏ ra `apps/erp_ai/erp_ai/__init__.py` | T1 và C0 phải xác nhận đường import trước khi dev viết mã. Nếu bench đọc cây chính → dừng và báo team-leader (`NEEDS_CONTEXT`); không đổi file của cây chính |
| R-2: site `miyano` dùng chung với phiên khác; T12 (`cmd.migrate`) thêm cột lên site đó; test ghim role ghi Has Role của tài khoản agent | Phiên khác thấy trường mới; test dừng giữa chừng để lại tập role sai | Mọi test `addCleanup(frappe.db.rollback)`; `pin_agent_roles` khôi phục trong cleanup và khẳng định số Has Role trước = sau (T2); C5 đếm lại Has Role. Cột thêm vào là cộng, không hại |
| R-3: Assignment Rule của nhóm đích gán người trong chính lần lưu (u1), bot gán thêm | 2 ToDo đang mở trên một phiếu | `ticket_assignments` xét sau (u1) (T13, T21); test `test_team_rule_assigns_bot_does_not`, `test_rule_assignment_in_route_save_kept` |
| R-4: `condition` SLA lỗi chặn lưu phiếu | ngoại lệ từ `doc.save()` ở (u1) | (u1) trong savepoint, lỗi → dừng (u2)–(u4), không thử lại bằng `db.set_value` (T20); `test_broken_sla_condition_stops_route_cleanly` |
| R-5: Prompt nền đổi, sau khi rebase lên FEAT-004/005 test "trùng từng byte" đỏ | test `build_reason_system` của FEAT-004/005 đỏ ở bước gộp | Tech-lead nhắc dev sửa ảnh chụp nền theo spec FEAT-006 (STD-TEST-5); chạy `cmd.test` sau mỗi lần gộp |
| R-6: Trần token phân loại (600) chưa đo | eval báo `classify_max_tokens_hits > 0` | T25 in `classify_output_tokens_max`; qa dán đầu ra vào `acceptance.md`; nâng hoặc hạ trần qua D-8 |
| R-7: `check_tools_never_bypass_permissions` có thể bắt `route_ticket.py` ở T1 | `cmd.test` đỏ ở `test_architecture` | T1 viết theo ràng buộc (không `ignore_permissions`, `db.set_value`, `get_all`); nếu cần đọc dữ liệu thì dùng `site_facts` (ngoài `tools/`) |
| R-8: T24/T26 là test bảo vệ, xanh ngay khi viết | không có đầu ra đỏ để dán | Dev tạm phá một chốt, dán đầu ra đỏ, hoàn tác (đã ghi ở từng task) |

## Review focus
≤ 5 đầu vào hoặc kiểu lỗi mà spec ngụ ý, kèm test chủ:
1. `true`/`2.0`/`"2"` làm điểm: không được lọt thành điểm hợp lệ → T3 `test_bad_scores_mean_no_score`.
2. `[tracecore]` đứng sau `[GẤP]`, khác hoa/thường → T8 `test_prefix_overrides_default`.
3. Rule của nhóm gán người trong chính lần lưu (u1): bot không gán, không Task → T21 `test_rule_assignment_in_route_save_kept`, T22 `test_preassigned_by_rule_no_task_no_comment`.
4. `condition` SLA lỗi giữa chừng: 0 ToDo/Task/comment, phiếu trước = sau → T20 `test_broken_sla_condition_stops_route_cleanly`.
5. Chạy `ensure_setup` hai lần và cài lại sau khi người sửa cấu hình: không ghi đè, `share` chỉ bật 0→1 → T12 `test_task_permission_share_and_role_set`, `test_default_routing_rules_not_overwritten`.

## Walking skeleton (cỡ L)
T1 chạy qua mọi tầng bằng lõi giả:
- `install.py`: 3 trường điểm trên HD Ticket (cột Int mặc định 0).
- `classification.py`: `Classification` có 4 trường mới.
- `routing.py`: `decide_route` bản giả (ưu tiên/nhóm theo ánh xạ như hôm nay, người `None`).
- `tools/route_ticket.py`: `apply_route` ghi một lần `doc.save()`.
- `runner.py`: `_classify` → `decide_route` → bản ghi `classify` → `_route` (savepoint + `apply_route` + cập nhật nhật ký); `L0` dừng ở nhật ký.
- Bằng chứng: `cmd.test_one` với `erp_ai/agent/test_runner_routing.py` (phiếu `L1` có điểm trên trường; phiếu `L0` không đổi, điểm 0 khác NULL), cộng `cmd.test` xanh.
Không task nào khác bắt đầu trước khi review T1 là `approve`.

## Thứ tự merge với FEAT-003/004/005
FEAT-003 → FEAT-004 → FEAT-005 → FEAT-006 (arch-impact). Nhánh `team/FEAT-006` hiện từ `team/FEAT-003` @ `d425faa`. Khi FEAT-004/005 vào `main`, `/team:pr` rebase `team/FEAT-006` lên `main`: điểm va ở `prompts.py`, `runner.py`, `registry.py` (`ToolContext`), `install.py`, `erp_ai_setting.json`, `test_architecture.py`, `test_registry.py` (bảng ở `arch-impact.md` "Thứ tự merge"). Sau rebase: sửa ảnh chụp "bản nền" của test FEAT-004/005 theo prompt mới, chạy `cmd.test` và `cmd.migrate`.
