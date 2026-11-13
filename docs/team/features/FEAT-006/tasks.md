Feature: FEAT-006
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 tắt (config.json), để trống. -->

# Tasks FEAT-006

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
Đường dẫn trong `files:` và `test:` tính từ gốc app `erp_ai/` (ví dụ `erp_ai/agent/routing.py`). `test_one` = slot `cmd.test_one` với `{file}` là file ở dòng `test:`.
Giá trị dùng chung (tên trường, khóa JSON, chữ ký, hằng) nằm ở `plan.md` mục "Shared constraints"; mọi task thừa hưởng. Số dòng `file:line` trong `design.md` là của nền `7cb654f`: dò lại bằng tên hàm.
Mọi test ca thành công chạy dưới `pin_agent_roles` (có từ T2) khi chạm quyền (AC-17). Task trước T2 không chạm quyền ghi dưới role thật.
Tiến độ: BASE ghi ở dòng `progress:` dưới đây, tech-lead cập nhật trước mỗi lần gọi dev.

progress: (chưa build)

- [ ] T1 — Walking skeleton: điểm đi từ lời gọi phân loại tới trường trên phiếu — files: erp_ai/install.py, erp_ai/agent/classification.py, erp_ai/agent/routing.py, erp_ai/agent/tools/route_ticket.py, erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: —
  - Ngoại lệ cỡ: 6 file vì đây là lát cắt đầu-cuối cỡ L (plan.md "Walking skeleton"); mọi lõi giả, T2..T26 làm thật từng phần.
  - Criterion: AC-1 (khung), AC-2 (ghi lên phiếu từ `L1`; `L0` không ghi), AC-16 (khung `actions`).
  - Receives: `FakeGateway` trả JSON phân loại có `do_phuc_tap`, `do_quan_trong`, `ly_do_diem`; phiếu tạo bằng `make_ticket`.
  - Returns:
    - `install.py`: `_ai_field_specs` có `ai_complexity`/`ai_importance` (Int, `"0"`, permlevel 8, read_only) và `ai_score_reason` (Small Text, permlevel 8, read_only), đặt sau `ai_confidence`;
    - `classification.py`: `Classification` thêm `complexity: int = 0`, `importance: int = 0`, `score_reason: str = ""`, `department: str | None = None` (chưa đổi bộ đọc; khung đọc thẳng khóa JSON, không kiểm, sẽ làm thật ở T3);
    - `routing.py` (mới): `@dataclass(frozen=True) RouteDecision(ticket_type, agent_group, priority, assignee, needs_task, notes)` và `decide_route(classification, subject, mapping, config, *, team_exists, is_excluded_team, is_active_agent) -> RouteDecision` bản giả: ưu tiên/nhóm/loại lấy theo ánh xạ đầu mục + `[GẤP]` (hành vi `resolve_ticket_values` hiện có), `assignee=None`, `needs_task=False`;
    - `tools/route_ticket.py` (mới, không `TOOLS`, không `ToolSpec`): `apply_route(decision, classification, ctx) -> {"ok": True, "before": dict, "after": dict, "skipped": list} | {"ok": False, "reason": str}`, một `doc.save()` HD Ticket ghi `ticket_type`, `agent_group`, `priority`, `ai_confidence`, `ai_complexity`, `ai_importance`, `ai_score_reason`, `ai_classified_by="AI"`, `ai_updated_at`;
    - `runner.py`: `_classify` gọi `decide_route`, ghi bản ghi `classify` `applied=0` rồi commit như cũ; `_apply_classification` thay bằng `_route(log_name, classification, decision, context, auto_assign, subject)` bản khung chỉ gọi `apply_route` trong savepoint `erp_ai_route`, cập nhật bản ghi `classify` (`applied`, `actions`, `value_before/after`). `L0` dừng sau ghi nhật ký.
  - Expect: `cmd.test_one` với `erp_ai/agent/test_runner_routing.py` → `TestRoutingEndToEnd::test_l1_scores_written_to_ticket` (phiếu có `ai_complexity=2`, `ai_importance=3`, lý do, một action `apply_route` `ok=true`) và `test_l0_ticket_unchanged_scores_zero_not_null` xanh; `cmd.test` toàn bộ xanh (kể cả `test_architecture`, `test_agent_runner` hiện có; `check_tools_never_bypass_permissions` phủ `route_ticket.py`).
  - Gộp: đây là lát cắt đầu tiên; reviewer `approve` trước khi T2..T26 bắt đầu.

- [ ] T2 — Helper test: ghim role agent, dữ liệu Helpdesk tự tạo — files: erp_ai/test_utils.py, erp_ai/tests/test_test_utils.py — test: erp_ai/tests/test_test_utils.py — depends: T1
  - Criterion: AC-17 (ghim role, trả lại), A-13 (test tự tạo dữ liệu).
  - Returns (thêm vào `test_utils.py`, tên cố định cho mọi task sau):
    - `pin_agent_roles(testcase) -> None`: đọc tập Has Role hiện tại của `AGENT_USER`, đặt đúng {`ERP AI Agent`, `Agent`} (trừ `AUTOMATIC_ROLES`), `testcase.addCleanup` khôi phục tập cũ (đăng ký sau `addCleanup(frappe.db.rollback)`), khẳng định số Has Role trước = sau khi cleanup;
    - `make_routing_rules(**overrides) -> str` (JSON đúng dạng 3.3, người trong `overrides` do test truyền; không phụ thuộc `DEFAULT_ROUTING_RULES`);
    - `make_sla(testcase, *, condition: str = "", default: bool = False, enabled: bool = True) -> str` (tên SLA, tiền tố `PREFIX`; ghi qua `frappe.get_doc(...).insert()` của test, rollback cuối ca);
    - `make_team(testcase, *, with_rule: bool = False, rule_users: tuple[str, ...] = ()) -> str`;
    - `make_active_agent(testcase) -> str` (user ID có HD Agent `is_active=1`).
  - Expect: `cmd.test_one` với `erp_ai/tests/test_test_utils.py` → `test_pin_agent_roles_sets_exact_set_and_restores`, `test_make_team_with_rule_has_enabled_rule` xanh.

- [ ] T3 — Bộ đọc điểm: điểm sai thì "không có điểm", đầu mục giữ nguyên — files: erp_ai/agent/classification.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_classification.py — depends: T1
  - Criterion: AC-1 (đoạn đọc), D-3, D-4.
  - Receives: `Classification` có 4 trường mới (T1).
  - Returns: `parse_classification(raw: str) -> Classification | None` (chữ ký không đổi, không bao giờ ném lỗi): đọc `do_phuc_tap`, `do_quan_trong` (phải là `int` thật, không `bool`, ∈ `SCORE_VALUES`), `ly_do_diem` (cắt còn `SCORE_REASON_MAX_WORDS` từ), `bo_phan` (không phải chuỗi → `None`); một điểm sai → cả hai = 0 và `score_reason = ""`; thiếu khóa → 0/0/""; thêm hằng `SCORE_VALUES = (1, 2, 3)`, `SCORE_REASON_MAX_WORDS = 25`.
  - Expect: `cmd.test_one` với `erp_ai/agent/test_classification.py` → `TestParseClassification::test_scores_valid_each_level`, `test_bad_scores_mean_no_score` (0, 4, `"2"`, `true`, `2.0`, thiếu khóa, một đúng một sai), `test_score_reason_cut_to_25_words` xanh; các test cũ của file vẫn xanh.

- [ ] T4 — Prompt phân loại: thang điểm, 4 khóa, danh sách bộ phận — files: erp_ai/agent/prompts.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_classification.py — depends: T3
  - Criterion: AC-1 (prompt), AC-5 (D-10), AC-15 (dùng chung request).
  - Returns: `CLASSIFY_PROMPT` thêm bảng thang điểm (chép nguyên văn từ spec mục Dữ liệu) và 4 khóa ở design 3.1; `build_classify_request(subject, description, departments: tuple[str, ...] = ())`: có `departments` thì nối khối text `DANH SÁCH BỘ PHẬN: <tên, cách nhau dấu phẩy>` vào sau `CLASSIFY_PROMPT` trong cùng block system (vẫn `cache_control`); rỗng thì không nối.
  - Expect: `cmd.test_one` → `TestPrompts::test_classify_prompt_has_score_keys_and_scale`, `test_classify_request_appends_departments_only_when_given` xanh; test `TestPrompts` hiện có của prompt suy luận chưa đổi (T23).

- [ ] T5 — Policy: nhóm bị loại trừ, công tắc tự gán — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py — test: erp_ai/agent/test_policy.py — depends: T1
  - Criterion: AC-5 (`excluded_teams` cùng chuẩn hóa), AC-7c (công tắc), ADR-019 QĐ 6.
  - Returns: `is_excluded_team(team: str) -> bool` (đọc `excluded_teams` qua cơ chế của policy, chuẩn hóa bằng `_normalize` giống `can_send_ticket`); `auto_assign_enabled(settings) -> bool` (đọc `settings.auto_assign_enabled`, thiếu hoặc 0 → `False`).
  - Expect: `cmd.test_one` → `TestPolicy::test_is_excluded_team_same_normalization`, `test_auto_assign_enabled_reads_switch` xanh.

- [ ] T6 — Ưu tiên R1–R5 trong `decide_route` — files: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T1
  - Criterion: AC-3 (36 ca, mẫu spec), AC-4 (đọc `importance_priority` từ cấu hình), A-2, A-11.
  - Receives: `Classification.importance`, `mapping[cat].priority`, `config["importance_priority"]` (dạng 3.3; thiếu khóa coi là rỗng).
  - Returns: `PRIORITIES = ("Low", "Medium", "High", "Urgent")`; phần ưu tiên của `decide_route`: R1 tiêu đề chứa `[GẤP]`/`[GẬP]` (casefold) → `Urgent`; R2 F → `Low`; R3 E → `None`; R4 A và `imp == 3` → `Urgent`; R5 mức cao hơn theo `PRIORITIES` giữa `mapping[cat].priority` và `config.importance_priority[str(imp)]` (bỏ giá trị rỗng, `imp == 0` không có mức tối thiểu, cả hai rỗng → `None`). Bỏ giả của T1 cho ưu tiên. Nhóm/người vẫn giả.
  - Expect: `cmd.test_one` với `erp_ai/agent/test_routing.py` → `TestDecidePriority::test_priority_matrix_36_cases`, `test_spec_samples` xanh.

- [ ] T7 — Chọn nhóm A/B/C/F theo ánh xạ, D/E theo bộ phận — files: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T6
  - Criterion: AC-5, A-14.
  - Receives: `Classification.department`, `config["departments"]` (3.3), `team_exists(str) -> bool`, `is_excluded_team(str) -> bool` (đã có ở T5; ở đây chỉ nhận qua tham số).
  - Returns: `agent_group` và `notes` (`{"field": "agent_group", "reason": <câu cố định>}`) theo thuật toán design 3.2: bộ phận khớp `casefold` + gộp khoảng trắng; thứ tự lý do bỏ qua: không có bộ phận → không trong bảng → nhóm rỗng/không tồn tại → bị loại trừ. Câu cố định: "không có bộ phận", "bộ phận '<x>' không có trong bảng bộ phận", "nhóm '<t>' không tồn tại", "nhóm '<t>' bị loại trừ".
  - Expect: `cmd.test_one` → `TestDecideTeam::test_abcf_team_from_mapping`, `test_de_team_from_department` (hoa/thường, thừa khoảng trắng), `test_de_team_skip_reasons` (4 lý do) xanh.

- [ ] T8 — Chọn người theo đầu mục, tiền tố; không bao giờ chọn tài khoản agent; `needs_task` — files: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T7
  - Criterion: AC-6 (chọn người, `[tracecore]`, người không hợp lệ), AC-8, AC-14 (người đến từ cấu hình), D-13, A-7.
  - Receives: `config["assignees"]`, `config["departments"][dept]["head"]`, `is_active_agent(str) -> bool`, `constants.AGENT_USER`.
  - Returns: `assignee` và `needs_task` theo design 3.2: D/E → `head` của bộ phận (bộ phận đã khớp ở T7); A/B/C/F → tiền tố đầu tiên khớp (`casefold`, chuỗi con của tiêu đề, theo thứ tự khai) mà có người, nếu không thì `default`; loại ứng viên rỗng / `== AGENT_USER` / không phải HD Agent hoạt động, mỗi loại một note `{"field": "assignee", "reason": ...}` ("cấu hình không có người cho đầu mục <cat>", "không gán tài khoản agent", "<user> không phải HD Agent đang hoạt động"); `needs_task = category in {"C","D"} and assignee is not None`. Hết phần giả của T1.
  - Expect: `cmd.test_one` → `TestDecideAssignee::test_prefix_overrides_default` (đầu tiêu đề, sau `[GẤP]`, khác hoa/thường), `test_inactive_or_missing_agent_not_chosen`, `test_agent_user_never_chosen` (kể cả là HD Agent), `test_needs_task_only_c_d_with_assignee` xanh.

- [ ] T9 — Cấu hình `routing_rules`: mặc định, bộ nạp, bộ kiểm — files: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T8
  - Criterion: AC-4 (bộ kiểm), AC-14 (không hằng người trong `.py`), D-1, D-11.
  - Returns: `DEFAULT_ROUTING_RULES: str` (JSON đúng 3.3; danh sách người rỗng, `expected_sla` theo D-11); `load_routing_config(raw: str) -> dict` (chuẩn hóa về dạng 3.3, sai dạng → `{}`, không ném); `validate_routing_config(raw: str) -> None` (`frappe.throw` → `frappe.ValidationError`, câu báo nêu đường dẫn khóa sai theo bảng ở design 3.3; kiểm user bằng `frappe.db.exists("User", ...)` khi khác rỗng; không chặn tài khoản agent, không kiểm nhóm tồn tại).
  - Expect: `cmd.test_one` → `TestRoutingConfig::test_default_valid_and_loads`, `test_bad_configs_raise_with_path` (không phải JSON; khóa gốc lạ; mức `Hgh`; thiếu khóa "3"; `assignees.D`; user không tồn tại; phút âm), `test_load_bad_returns_empty` xanh.

- [ ] T10 — `sla_lag` và `departments` — files: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T9
  - Criterion: AC-12 (lệch mức: 2 con số; D/E không kiểm), D-10 (tên bộ phận cho prompt).
  - Returns: `sla_lag(category: str, resolution_s: int | None, config: dict) -> tuple[int, int] | None` (`(actual_min, expected_min)` khi chậm hơn; `None` khi khớp, `resolution_min` null, hoặc cấu hình rỗng); `departments(config: dict) -> tuple[str, ...]` (tên theo thứ tự khai).
  - Expect: `cmd.test_one` → `TestSlaLag::test_slower_sla_returns_two_numbers` (600 > 480), `test_matching_sla_none`, `test_d_e_not_checked`; `TestDepartments::test_names_in_declared_order` xanh.

- [ ] T11 — ERP AI Setting: trường `auto_assign_enabled`, `routing_rules`, kiểm khi lưu — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T9
  - Criterion: AC-4 (chặn lưu cấu hình sai, mặc định lưu được), AC-7c (công tắc có trường).
  - Receives: `validate_routing_config(raw)` (T9).
  - Returns: trong `section_routing`: `auto_assign_enabled` (Check, default `"0"`) và `routing_rules` (Code, `options "JSON"`), mỗi trường có `description` ≤ 400 ký tự theo design 2.4; `validate` gọi `validate_routing_config(self.routing_rules)` cạnh `validate_mapping`; mặc định trường `routing_rules` trong JSON để trống (mặc định cài đặt do T12 ghi khi DB NULL, nên test ở đây gán thẳng `DEFAULT_ROUTING_RULES`).
  - Expect: `cmd.test_one` → `TestRoutingRules::test_bad_rules_blocked_with_location`, `test_default_rules_valid` xanh; `erp_ai/tests/test_doctype_descriptions.py` vẫn xanh (chạy ở checkpoint).

- [ ] T12 — Cài đặt: mặc định setting, `ai_ticket` trên Task, `share` trên dòng Task của app — files: erp_ai/install.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T11
  - Criterion: AC-17 (`share`, tập role, idempotent), AC-2 (dòng template Agents cho 3 trường), AC-13 (trường `ai_ticket`), spec DoD (cài lại không ghi đè).
  - Returns:
    - `_ensure_task_ticket_field()` (mới): Custom Field Task `ai_ticket` Link → HD Ticket, permlevel 0, `search_index 1`, `label "Phiếu Helpdesk"`, `module "ERP AI agent"`, `insert_after "description"`, không `read_only`; gọi trong `ensure_setup`;
    - `_ensure_task_permission`: tạo dòng như cũ nếu chưa có; có rồi thì chỉ bật `share` 0→1 trên dòng (`parent="Task"`, `role=ROLE_AGENT`, `permlevel=0`, `if_owner=1`) rồi `clear_cache(doctype="Task")`;
    - `_ensure_default_settings`: ghi `routing_rules = DEFAULT_ROUTING_RULES` và `auto_assign_enabled = 0` khi DB đang NULL.
  - Expect: `cmd.test_one` → `TestInstall::test_score_fields_int_default_zero_permlevel_8`, `test_task_ticket_field`, `test_task_permission_share_and_role_set` (chạy `ensure_setup` hai lần; dòng role khác nguyên; tập role đúng 2), `test_default_routing_rules_not_overwritten` xanh. `cmd.migrate` chạy được trên site dev (kiểm ở checkpoint C2).

- [ ] T13 — `site_facts`: 5 phép đọc hệ thống chỉ-đọc — files: erp_ai/agent/site_facts.py, erp_ai/agent/test_site_facts.py — test: erp_ai/agent/test_site_facts.py — depends: T12, T2
  - Criterion: AC-6/AC-7a (vị từ "đã có người"), AC-13 (đã có Task), AC-11/AC-12 (SLA đang áp), ADR-019 QĐ 5, ADR-021 QĐ 4.
  - Returns (`frappe.db.get_value`/`exists`/`get_all`; không phải `agent/tools/`):
    - `ticket_assignments(ticket: str) -> list[dict]` (`{"allocated_to", "assignment_rule"}` của ToDo `reference_type="HD Ticket"`, `status != "Cancelled"`, gồm cả Closed);
    - `has_linked_task(ticket: str) -> bool` (`Task.ai_ticket = ticket`);
    - `is_active_agent(user: str) -> bool`;
    - `team_exists(team: str) -> bool`;
    - `applied_sla(ticket: str) -> dict | None` (`{"sla", "priority", "resolution_s"}` từ `HD Ticket.sla` và HD Service Level Priority theo `priority` của phiếu; `None` khi phiếu không có `sla`).
  - Expect: `cmd.test_one` → `TestSiteFacts::test_assignments_include_closed_exclude_cancelled`, `test_has_linked_task_sees_other_owners_task`, `test_is_active_agent_flags`, `test_applied_sla_none_without_sla`, `test_facts_work_under_pinned_agent_roles` (role `Agent` không đọc được SLA mà hàm vẫn đọc được) xanh.

- [ ] T14 — `apply_route` đầy đủ: quyền, từ chối, before/after, SLA do Helpdesk chọn — files: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/test_route_ticket.py — test: erp_ai/agent/tools/test_route_ticket.py — depends: T2, T12
  - Criterion: AC-2 (user `Agent` đọc 3 trường), AC-10 (SLA theo `condition`; ca `>=` ở `L0` và phiếu mới), AC-7b (từ chối khi người đã phân loại), AC-16 (before/after, `ok=false` kèm lý do), NFR-2.
  - Receives: `RouteDecision`, `Classification`, `ToolContext` (T1).
  - Returns: `apply_route` kiểm `doc.has_permission("write")` và `has_permlevel_access_to(field, "write")` cho từng trường; thiếu quyền ghi phiếu hoặc `ai_classified_by` là người → `{"ok": False, "reason": ...}`; thiếu quyền một trường → bỏ trường đó, ghi vào `skipped`; `priority`/`agent_group`/`ticket_type` chỉ ghi giá trị có trên site (`LINKED_DOCTYPES`); `before`/`after` có đúng các trường đã đổi; luôn một `doc.save()` kể cả khi E không có nhóm/ưu tiên. Không bắt ngoại lệ của `save` (lan lên savepoint runner).
  - Expect: `cmd.test_one` → `TestApplyRoute::test_scores_written_readable_by_agent_role_user`, `test_human_classified_refused`, `test_missing_field_permission_skipped`, `test_e_ticket_still_saved_with_scores`; `TestSlaFromHelpdesk::test_sla_chosen_by_complexity_condition`, `test_ge_condition_saves_l0_and_new_ticket` xanh.

- [ ] T15 — `assign_owner` và `post_routing_comment` — files: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/test_route_ticket.py — test: erp_ai/agent/tools/test_route_ticket.py — depends: T14
  - Criterion: AC-6 (đúng 1 ToDo, đúng 1 Notification Log, phiếu không bị chia sẻ), AC-8 (comment xin phân công), AC-11 (comment `NO_SLA`), ADR-021 QĐ 3.
  - Returns: `assign_owner(user: str, ctx) -> {"ok": True, "assignee": user} | {"ok": False, "reason": str}` (thiếu quyền `read` phiếu → từ chối; gọi `frappe.desk.form.assign_to.add({"assign_to": [user], "doctype": "HD Ticket", "name": ctx.ticket_name})`, không truyền cờ bỏ quyền); `post_routing_comment(lines: list[str], ctx)` (nối bằng xuống dòng thành **một** comment qua `post_comment`); hằng `ASSIGN_REQUEST`, `NO_SLA` và 3 câu lý do ở design 3.6 (không chứa nội dung phiếu hay cấu hình thô).
  - Expect: `cmd.test_one` → `TestAssignOwner::test_ticket_never_shared_one_todo_one_notification`, `test_no_read_permission_refused`; `TestRoutingComment::test_lines_joined_in_one_comment` xanh.

- [ ] T16 — `create_routed_task` và `create_task` đặt `ai_ticket` — files: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/tools/test_write_ticket.py — test: erp_ai/agent/tools/test_route_ticket.py — depends: T15, T12
  - Criterion: AC-13 (Task có tham chiếu, giao đúng người; lỗi chia sẻ → ném để runner rollback), NFR-4 (mô tả Task không chứa khóa/cấu hình thô), ADR-021 QĐ 2/5.
  - Returns: `write_ticket.py` tách `_ticket_link_html(name) -> str` và `_existing_values(wanted)` (dùng lại, STD-DESIGN-4); `create_task` đặt `ai_ticket`; `route_ticket.create_routed_task(user: str, ticket_subject: str, classification: Classification, ctx) -> {"ok": True, "task": str} | {"ok": False, "reason": str}`: `subject` = tiêu đề cắt 140 ký tự; `ai_ticket`; `description` = đoạn link phiếu + dòng "Độ phức tạp {c}/3, độ quan trọng {i}/3: {lý do}" (`escape_html`); sau `Task.insert()` gọi `assign_to.add` trên Task; không có DocType Task / thiếu quyền tạo / thiếu quyền đọc phiếu → `ok=false`; lỗi chia sẻ ném `frappe.ValidationError`.
  - Expect: `cmd.test_one` với `erp_ai/agent/tools/test_route_ticket.py` → `TestCreateRoutedTask::test_assignee_without_projects_user_gets_share`, `test_description_escaped_and_has_scores`, `test_sharing_disabled_raises`; với `erp_ai/agent/tools/test_write_ticket.py` → `TestCreateTask::test_sets_ai_ticket` xanh.

- [ ] T17 — `set_classification` dùng chung `decide_route`; `ToolContext.routing_config` — files: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_write_ticket.py — test: erp_ai/agent/tools/test_write_ticket.py — depends: T16, T8
  - Criterion: AC-3 (cùng ưu tiên qua mọi đường ghi), ADR-019 QĐ 4, D-14.
  - Returns: `ToolContext` thêm trường cuối `routing_config: dict | None = None` (`TOOL_MODULES` không đổi); `_mapped_values` trong `write_ticket.py` gọi `decide_route(Classification(category, confidence, complexity=doc.ai_complexity or 0, importance=doc.ai_importance or 0), subject, mapping, ctx.routing_config or {}, team_exists=site_facts.team_exists, is_excluded_team=policy.is_excluded_team, is_active_agent=site_facts.is_active_agent)` với `department=None`; chỉ dùng `ticket_type`/`agent_group`/`priority`. Schema `set_classification` không đổi.
  - Expect: `cmd.test_one` → `TestSetClassification::test_same_priority_as_route`, `test_de_skips_team_without_department` xanh; test cũ của file vẫn xanh.

- [ ] T18 — Xóa `resolve_ticket_values`, chuyển ca test sang `test_routing.py` — files: erp_ai/agent/classification.py, erp_ai/agent/test_classification.py, erp_ai/agent/test_routing.py — test: erp_ai/agent/test_routing.py — depends: T17, T4
  - Criterion: D-12 (R1–R5 chỉ ở một hàm), AC-3.
  - Returns: xóa `resolve_ticket_values` khỏi `classification.py`; chuyển `TestResolveTicketValues` thành ca của `TestDecidePriority`/`TestDecideTeam` ở `test_routing.py` (cùng giá trị kỳ vọng; không bỏ ca nào); `grep -rn resolve_ticket_values erp_ai/` rỗng.
  - Expect: `cmd.test_one` với `erp_ai/agent/test_routing.py` và `erp_ai/agent/test_classification.py` xanh; `grep` rỗng, đầu ra dán vào báo cáo.

- [ ] T19 — Runner: nạp cấu hình, công tắc, `departments`, 4 cột nhật ký, `CLASSIFY_MAX_TOKENS` 600 — files: erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T4, T5, T10, T11
  - Criterion: AC-1 (nhật ký có điểm ở `L0` và `L1`; "không có điểm"), AC-2 (`L0` không đổi giá trị nào, `ai_complexity` khác NULL), D-8, D-15, NFR-1.
  - Returns: `erp_ai_log.json` thêm 4 cột trong `section_prediction` (`predicted_complexity` Int, `predicted_importance` Int, `predicted_score_reason` Small Text, `predicted_assignee` Data, mỗi cột có `description`); `runner.py`: `routing = load_routing_config(settings.routing_rules)` một lần ở bước (b), `auto_assign = policy.auto_assign_enabled(settings)` ở bước (e), `ToolContext(..., routing_config=routing)`, `build_classify_request(subject, description, departments(routing))`, `CLASSIFY_MAX_TOKENS = 600`, `write_entry` ghi 4 cột mới (không điểm → `predicted_score_reason = "không có điểm"`); cấu hình hỏng → lỗi `routing_rules không hợp lệ` ở cột `error`. `_route` nhận `auto_assign` nhưng chưa dùng.
  - Expect: `cmd.test_one` → `TestRoutingLog::test_l0_entry_has_scores_ticket_unchanged`, `test_l1_no_score_writes_zero_logs_no_score`; `TestRoutingEndToEnd::test_model_call_count_unchanged` xanh; `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` và `test_agent_runner.py` vẫn xanh.

- [ ] T20 — Runner `_route` (u1) đầy đủ và kiểm SLA — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T19, T14, T13
  - Criterion: AC-3 (đầu-cuối B + quan trọng 2 → `High`), AC-4 (đổi bảng thì lần chạy sau dùng giá trị mới), AC-11, AC-12, AC-16 (actions, before/after), AC-18 (`condition` lỗi), D-6, D-7, D-9, D-16, NFR-2.
  - Receives: `apply_route` (T14), `site_facts.applied_sla` (T13), `sla_lag` (T10).
  - Returns: `_route` hoàn chỉnh phần (u1) và kiểm SLA theo design 4.2: mỗi đơn vị một savepoint `erp_ai_route`; (u1) ném lỗi hoặc `ok=false` → dừng (u2)–(u4) và kiểm SLA, `actions` ghi `ok=false` + lớp ngoại lệ, không có nội dung phiếu; kiểm SLA chạy ở `L1`+ dù công tắc bật hay tắt, thêm action `sla_check` `ok=false` (không SLA, hoặc lệch kèm 2 con số) và `frappe.logger("erp_ai").warning`; cập nhật bản ghi `classify` một lần (`applied`, `actions`, `value_before/after`, `skipped_fields`, `error`); dòng `erp_ai route ...` info; commit một lần khi không chạy test. Câu `NO_SLA` được gom vào một danh sách `lines` (comment gửi ở T21 để một chỗ gọi `post_routing_comment`).
  - Expect: `cmd.test_one` → `TestRoutingEndToEnd::test_priority_from_scores_through_runner`, `test_changed_importance_table_used_next_run`, `test_no_helpdesk_config_records_created`; `TestRoutingSla::test_slow_sla_warning_in_log`, `test_broken_sla_condition_stops_route_cleanly` xanh.

- [ ] T21 — Runner (u2) gán người và (u4) comment xin phân công / thiếu SLA — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T20, T15, T8
  - Criterion: AC-6 (gán đúng 1 người, nhóm có rule bật), AC-7 (a)(b)(c)(d), AC-8 (đúng 1 comment), AC-11 (đúng 1 comment `NO_SLA`), AC-14 (đổi người mặc định), AC-16 (lần bị từ chối `ok=false` + lý do).
  - Returns: (u2) chỉ khi `auto_assign` và ở `L1`+: `existing = site_facts.ticket_assignments(ticket)` xét **sau** (u1); có → action `assign_owner` `ok=false` "phiếu đã có người được gán: <user...>" kèm `rule`; `decision.assignee is None` → `ok=false` theo note + câu `ASSIGN_REQUEST` "cấu hình không có người hợp lệ"; còn lại `assign_owner`, ok → `assigned = user`, ngoại lệ/`ok=false` → "gán người không thành công". (u4) gom `lines` (cả `NO_SLA` từ T20) → `post_routing_comment`, tối đa 1 comment; ngoại lệ → `ok=false`, không thử lại. Người được gán ghi bằng user ID trong `actions` và `predicted_assignee`.
  - Expect: `cmd.test_one` → `TestRoutingAssign::test_assigns_configured_person_one_notification`, `test_team_rule_assigns_bot_does_not`, `test_agent_account_never_assigned_one_comment`, `test_changed_default_person_assigned_next_run`; `TestRoutingNoOverride::test_existing_assignment_kept`, `test_rule_assignment_in_route_save_kept`, `test_human_classified_no_route_writes`, `test_switch_off_no_todo_no_task`, `test_l0_no_todo_no_task`; `TestRoutingSla::test_no_sla_one_warning_one_comment` xanh.

- [ ] T22 — Runner (u3) tạo Task cho C/D — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T21, T16
  - Criterion: AC-13 (đúng 1 Task; chạy lại vẫn 1; đã có Task; đầu mục khác/không người → 0 Task; nhánh (i) chia sẻ tắt; nhánh (ii) đã có người từ trước), ADR-020 QĐ 7, A-12.
  - Returns: (u3) chỉ khi `assigned` và `decision.needs_task`: `has_linked_task` có → action `create_routed_task` `ok=false` "phiếu đã có Task liên kết"; còn lại `create_routed_task(assigned, subject, classification, ctx)` trong **một** savepoint cùng với lần giao Task; ngoại lệ → rollback cả Task và ToDo của Task, `ok=false`, thêm câu "không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt)" vào `lines` (comment (u4) do T21 gửi).
  - Expect: `cmd.test_one` → `TestRoutingTask::test_c_ticket_one_linked_task_assigned`, `test_rerun_keeps_one_task`, `test_existing_linked_task_no_new_task`, `test_other_category_or_no_person_no_task`, `test_sharing_disabled_no_task_one_comment`, `test_preassigned_by_human_no_task_no_comment`, `test_preassigned_by_rule_no_task_no_comment` xanh.

- [ ] T23 — Prompt suy luận: bảng routing dựng từ cấu hình — files: erp_ai/agent/prompts.py, erp_ai/agent/runner.py, erp_ai/agent/test_classification.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_classification.py — depends: T22, T18
  - Criterion: AC-14 (prompt hiện người mới sau khi đổi cấu hình; không tên người viết cứng trong `.py`), ADR-019 Ràng buộc.
  - Returns: xóa `ROUTING_TABLE`; `build_routing_table(mapping: dict, config: dict, names: dict[str, str]) -> str` (cùng cột với 16.2; `names` = `{user ID: get_fullname}`); `build_reason_system(prompt_digest, routing_table="")` (rỗng thì bỏ phần routing); `runner._reason` truyền `routing_table=build_routing_table(mapping, routing, names)` với `names` lấy cho mọi user có trong cấu hình; `test_agent_runner.py` sửa hai chỗ gọi `build_reason_system` theo chữ ký mới.
  - Expect: `cmd.test_one` với `erp_ai/agent/test_classification.py` → `TestPrompts::test_routing_table_shows_configured_people`, `test_reason_system_without_routing_table`; với `erp_ai/agent/test_agent_runner.py` xanh.

- [ ] T24 — Test chốt: chống chèn lệnh, quyền ghim, thông tin nhạy cảm, bảo vệ schema tool — files: erp_ai/agent/test_runner_routing.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/test_runner_routing.py — depends: T22, T17
  - Criterion: AC-9, AC-16 (mọi ghi có trước/sau; từ chối có lý do), AC-17 (ca thành công dưới role đã ghim; `check_privilege_escalation` trước = sau), NFR-4.
  - Ghi chú quy trình: đây là test bảo vệ nên có thể xanh ngay khi viết; dev phải chứng minh "đỏ đúng lý do" bằng cách tạm phá một chốt (ví dụ cho `TOOL_MODULES` thêm `route_ticket`, hoặc ghi `response_by`) rồi dán đầu ra đỏ, rồi hoàn tác.
  - Returns: không đổi mã sản xuất.
  - Expect: `cmd.test_one` → `TestRoutingInjection::test_ticket_text_does_not_steer_route`, `TestRoutingLog::test_every_write_in_actions_with_before_after`, `test_refusals_have_ok_false_reason`, `TestRoutingPermissions::test_success_cases_under_pinned_roles`, `test_privilege_findings_unchanged`, `TestRoutingEndToEnd::test_fake_key_absent_from_comment_log_task` (file `erp_ai/agent/test_runner_routing.py`); `TestRegistry::test_no_tool_schema_takes_person_sla_priority_or_score`, `test_route_functions_not_executable_as_tools` (file `erp_ai/agent/tools/test_registry.py`) xanh.

- [ ] T25 — Eval offline: khớp ưu tiên, nhóm, phân bố điểm, trần token — files: erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py — test: erp_ai/eval/test_run_eval.py — depends: T4, T5, T10, T13
  - Criterion: AC-15, D-8, A-8.
  - Receives: `build_classify_request(..., departments(routing))`, `decide_route`, `site_facts.team_exists`/`is_active_agent`, `policy.is_excluded_team`.
  - Returns: `_predict(row, routing, mapping) -> {"category", "complexity", "importance", "priority", "agent_group", "output_tokens", "stop_reason"}`; `compute_metrics(rows, mapping)` (vẫn hàm thuần) thêm `priority` = `{"count", "correct", "accuracy"}` (bỏ dòng thiếu nhãn hoặc dự đoán `None`), `team` (cùng dạng, dòng có nhãn `agent_group`), `score_distribution` = `{"complexity": {0..3: n}, "importance": {0..3: n}}`, `classify_output_tokens_max`, `classify_max_tokens_hits`; `format_report` in 4 khối mới; `run` đọc `routing_rules`. Ngưỡng 0,85/0,70 chỉ để đọc, không làm cổng.
  - Expect: `cmd.test_one` → `TestRunEval::test_priority_team_match_and_score_distribution`; `TestRunEvalRun::test_eval_uses_runner_route_function` xanh. Lệnh eval thật trên site dev thuộc bước kiểm của qa (AC-15), không thuộc task này.

- [ ] T26 — Luật kiến trúc của ADR-019..021 và 2 bảo vệ tĩnh — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T23, T24, T25
  - Criterion: AC-10 (không gán `response_by`/`resolution_by`), AC-14 (không tên người viết cứng trong `agent/*.py`), AC-7c (công tắc chỉ đọc ở policy), ADR-019..021 Ràng buộc.
  - Ghi chú quy trình: như T24 (test bảo vệ, dev chứng minh đỏ bằng cách tạm phá chốt).
  - Returns: `POLICY_FIELDS` thêm `auto_assign_enabled`; trong `TestArchitecture`: `test_route_module_not_in_tool_modules_and_has_no_tools`, `test_route_module_single_ticket_save`, `test_assign_to_only_in_route_module`, `test_no_share_bypass` (`ignore_share_permission`, `assign_to._add(`, `add_docshare`, `frappe.share.add`), `test_auto_assign_switch_only_in_policy`, `test_entry_types_unchanged`, `test_assign_field_not_used_for_decision` (`"_assign"` trong `erp_ai/agent/**`), `test_route_module_bypass_rules_apply`, `test_feature_never_assigns_sla_dates`, `test_no_default_people_in_agent_python` (Việt, Tiến, Hiếu, Lan, Hà, Thư, Chi, `ai.agent` dạng tên người); mỗi luật có ca trong `TestScannersCatchViolations` chứng minh bộ quét bắt được vi phạm.
  - Expect: `cmd.test_one` với `erp_ai/tests/test_architecture.py` → các test trên xanh; `cmd.test` toàn bộ xanh, `cmd.lint` sạch.
