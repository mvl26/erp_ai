Feature: FEAT-005
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks FEAT-005

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
`cmd.test_one` = lệnh của profile với `{file}` là file ở `test:`. Mọi task: viết test đỏ trước (STD-TEST-1), chỉ sửa trong `files:`, không skip/xfail. Tên hàm, hằng, chuỗi chính xác: `plan.md` mục Ràng buộc chung và `design.md` mục 2–4 (bản sửa vòng 1). Task sửa `*.json` của DocType: chạy `cmd.migrate` rồi mới `cmd.test_one`.

Ký hiệu `F4-T<n>` = task `T<n>` trong `docs/team/features/FEAT-004/tasks.md`. Lúc build FEAT-004 đã `verified` nên mọi `F4-T<n>` đã xong; dòng `depends:` vẫn nêu để dev biết file đó đã bị FEAT-004 sửa, phải đọc mã thật trên `team/FEAT-004` rồi mới sửa, và nếu chữ ký thật khác design thì `DESIGN_CONFLICT`.

Nhánh nền: `team/FEAT-004` (đã tạo 2026-11-13 từ `team/FEAT-006` @ `f039112`; **đang build**, chưa verify; lúc đối chiếu mới có commit tài liệu, mã `erp_ai/` còn giống `f039112`). Build FEAT-005 chỉ bắt đầu khi FEAT-004 qua verify. Khi đó tech-lead tạo `team/FEAT-005` từ đầu nhánh `team/FEAT-004`, ghi mã commit thật vào dòng BASE dưới, rồi chạy `cmd.test` (phải xanh) trước T1.
Tiến độ: BASE ghi ở đây trước mỗi lần gọi dev.
- BASE nhánh nền = team/FEAT-004 @ <chưa có: ghi mã commit khi tạo nhánh> (cập nhật khi tạo nhánh)

Quy tắc chung cho task chạm file cả hai feature sửa: `registry.py`, `prompts.py`, `runner.py`, `run_log.py`, `erp_ai_log.json`, `erp_ai_setting.json`, `constants.py`, `test_registry.py`, `test_agent_runner.py`, `test_architecture.py`, `test_doctype_descriptions.py`, `test_utils.py`, `test_tasks.py`, `test_install.py`, `test_erp_ai_setting.py`, `policy.py` (design mục 7). Đọc bản FEAT-004 đã gộp trước, giữ nguyên hành vi và test của nó (STD-TEST-5), chỉ thêm.
Nền có cả mã FEAT-006 (FEAT-004 build trên `team/FEAT-006`): `install.py`, `write_ticket.py`, `test_write_ticket.py` là file FEAT-006 đã sửa mà FEAT-004 không chạm; `ToolContext` có `routing_config`, `build_reason_system` có `routing_table`. Cùng quy tắc: đọc mã thật, chỉ thêm, không đổi assertion của FEAT-006.
Git (ADR-022 của FEAT-004): FEAT-005 không dựng lệnh git, không gọi `subprocess`, không sửa `source.py`, `process_runner.py`, `GitSandbox`, `RealCoreReposUntouchedMixin`. Test FEAT-005 không gọi tool `propose_*` (tool đó nay chạy lệnh git đọc); test nào stub `subprocess.run` toàn cục phải biết điều này.

## Đối chiếu với plan FEAT-004 mới (2026-11-13; FEAT-004: 51 task, Amendment 1, ADR-022)
Mọi `F4-T<n>` đang trích (T2–T7, T12, T13, T23–T25, T28–T33, T36, T44, T51) có trong `FEAT-004/tasks.md` hiện nay và giữ nghĩa; không thêm, không bỏ, không đổi số task (vẫn 52). Task đã sửa chữ:
| Task | Sửa | Vì |
|---|---|---|
| T1 | chữ ký `build_reason_system` có `routing_table`; mốc băm 4 biến thể; băm trên JSON của `list[dict]` | nền FEAT-006, F4-T24 |
| T3 | số dự kiến 26 → 27 trường, 7 → 8 section; chỗ đặt theo `field_order` thật | nền FEAT-006 (24/6), F4-T3 (+2/+1) |
| T4 | ghi số trường Log dự kiến 38, không đổi | FEAT-006 +4, F4-T4 +3 |
| T7 | `depends:` F4-T32 → F4-T44; `POLICY_FIELDS` có 3 tên của FEAT-006/004 | chuỗi `test_architecture.py` của FEAT-004 nay kết thúc ở T44 |
| T8 | `depends:` thêm F4-T25, F4-T44; thêm ca sạch cho luật git | F4-T25 có thể đã sửa luật "tool không ghi"; luật git ADR-022 |
| T13 | chữ ký `(prompt_digest, routing_table="", *, change_tools=False, groups=())` | F4-T24, design FEAT-004 "Chỗ đụng FEAT-005" điểm 2 |
| T15 | `depends:` thêm T8 | chuỗi `test_architecture.py` thành phụ thuộc rõ (chạy 5 dev) |
| T16 | `depends:` thêm F4-T36, F4-T51; `ToolContext` dựng bằng đối số tên | `test_utils.py` nay có `GitSandbox`; `ToolContext` thêm trường |
| T21, T45 | nêu tên test đếm spec của F4-T28 phải đổi số | `test_all_specs_count_is_14` |
| T22 | giữ `routing_table` khi gọi `build_reason_system` | F4-T29 |
| T23 | câu "ai gọi `write_entry`": `transitions.log_step` của FEAT-004 cũng gọi | F4-T13 |
| T30 | ghi chú file FEAT-006 đã sửa | nền FEAT-006 |
| T48 | `depends:` thêm T23 | chuỗi `test_architecture.py` thành phụ thuộc rõ |
| T50 | dòng `agent/tools` ↛ `changes` đã có từ F4-T13: chỉ kiểm, không thêm trùng | F4-T13, F4-T44 |
| T52 | thêm kiểm NFR-9 (4 repo lõi), sửa câu Custom DocPerm | ADR-022; FEAT-004 không cài Custom DocPerm |

Chạy song song 5 dev: bảng lượt ở `plan.md` mục "Nhóm song song 5 dev".
Quy tắc dọn test: test có tool tự commit (`add_custom_field`, `create_workflow`, `update_workflow`, `activate_workflow`: DDL hoặc `commits=True`) KHÔNG dựa `frappe.db.rollback`. Dùng helper dọn của T16 (`register_cleanup`): xóa bản ghi theo thứ tự ngược, dưới `Administrator`, có `frappe.db.commit()`, tên có tiền tố `erpai_test_` hoặc `ERPAI-TEST`. Mọi test khác dùng `addCleanup(frappe.db.rollback)` như hiện nay.

## Phần 0, chụp nền

- [ ] T1 — Chụp prompt và danh sách tool của nhánh nền (test đặc trưng) — files: erp_ai/agent/test_prompts.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/test_prompts.py — depends: F4-T23, F4-T24, F4-T28, F4-T29
  - Criterion: AC-1, NFR-6 (mốc "trùng từng byte" và "trùng danh sách" phải chụp TRƯỚC mọi sửa)
  - Receives: `build_reason_system(prompt_digest, routing_table="", *, change_tools=False) -> list[dict]` (F4-T24 trên nền FEAT-006) và `get_tool_schemas(level, has_instructor, change_enabled)` của `team/FEAT-004`; chưa sửa mã sản phẩm
  - Returns: `test_prompts.py` (mới; test prompt của FEAT-004/006 nằm ở `test_classification.py`, không chuyển) với `BASE_PROMPT_SHA256[(routing_table, change_tools)]` cho 4 biến thể (`routing_table` ∈ `""`, `"bang-mau"` × `change_tools` ∈ `False`, `True`) tại `prompt_digest` cố định `"digest-mau"`; băm = sha256 của `json.dumps(kết quả, ensure_ascii=False, sort_keys=True)` (hàm trả `list[dict]`); `test_registry.py` thêm `BASE_TOOL_NAMES[(level, has_instructor, change_enabled)] -> tuple[str, ...]` (L0..L3 × 2 × 2, theo thứ tự trả về) và test so khớp, không đổi hằng tên tool có sẵn của FEAT-004/006 (`READ_TOOL_NAMES`…); hằng dán từ đầu ra thật của mã nền, không tính tay
  - Expect: test xanh ngay (đặc trưng). Chứng minh bắt được lỗi: đổi 1 byte trong một hằng → đỏ (dán), trả lại → xanh. `test_registry.py` hiện có vẫn xanh

## Phần 1, cấu hình, nhật ký, hằng

- [ ] T2 — Chuyển hằng DocType phân quyền sang `constants.py` — files: erp_ai/constants.py, erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: F4-T2, F4-T4
  - Criterion: nền AC-14, ADR-014 Ràng buộc (`PERMISSION_DOCTYPES` định nghĩa một lần), design 2.5
  - Receives: `tasks.py:19` (`PERMISSION_DOCTYPES` và các tên lẻ); `constants.py` đã có hằng của FEAT-004
  - Returns: `CUSTOM_DOCPERM_DOCTYPE`, `ROLE_DOCTYPE`, `HAS_ROLE_DOCTYPE`, `PERMISSION_DOCTYPES` trong `constants.py`, thứ tự tuple đúng như cũ; `tasks.py` import từ đó, không định nghĩa lại
  - Expect: đỏ (ImportError) rồi xanh: `test_tasks.py::test_permission_doctypes_come_from_constants` (so tuple với chuỗi viết tay: `Custom DocPerm`, `DocPerm`, `Role`, `Has Role`, `User Permission`, `Role Profile`); test cũ của `test_tasks.py` xanh nguyên

- [ ] T3 — `ERP AI Setting`: trường `assignable_roles` + Section Break, có mô tả — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/tests/test_doctype_descriptions.py — depends: F4-T3, F4-T4
  - Criterion: AC-6 (mặc định rỗng), design 2.1, luật mô tả FEAT-003 (field mới có `description` tiếng Việt ≤ 400 ký tự, không `sk-`, không `miyano`, không giá trị đang lưu)
  - Receives: `DOCTYPE_CONFIG["ERP AI Setting"]` sau FEAT-004 (đọc số thật: dự kiến `field_count` 26, `section_count` 7 = nền FEAT-006 24/6 + F4-T3 2/1); `field_order` nền kết thúc `section_alerts`, `alert_recipients`, `credentials`; trường FEAT-006 (`auto_assign_enabled`, `routing_rules`) nằm trong `section_routing`; `section_code_change`, `code_change_enabled`, `code_change_apps` của F4-T3 (đọc vị trí thật)
  - Returns: JSON thêm `section_accounts` (label "Tài khoản") và `assignable_roles` (Small Text, nhãn "Role bot được gán (mỗi dòng một role)", không khóa `default`), đặt sau nhóm `section_alerts` (sau `credentials`; design 2.1) và trước `section_code_change` nếu F4-T3 đặt nhóm đó ở cuối; không dời trường của FEAT-004/006; mô tả nêu: mỗi dòng một role, bỏ trống thì bot không gán được role nào, chỉ System Manager sửa, role quản trị và role có quyền sửa User/phân quyền bị bỏ qua dù có ghi ở đây; test: `field_count` +1, `section_count` +1, `phrases["assignable_roles"] = ("mỗi dòng", "Bỏ trống", "System Manager")`, `sections` thêm `("section_accounts", "Tài khoản", "assignable_roles")`. Nếu test đọc thứ tự trường mà chỗ đặt ở trên làm nó đỏ, đặt ngay sau `code_change_apps` và ghi lý do vào commit
  - Expect: đỏ trước (đếm lệch, thiếu mô tả); xanh sau `cmd.migrate` + `cmd.test_one`; `test_erp_ai_setting.py` hiện có xanh

- [ ] T4 — `ERP AI Log`: giá trị `entry_type` `config_change` + mô tả — files: erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/tests/test_doctype_descriptions.py — depends: F4-T4, T3
  - Criterion: ADR-018 QĐ 1 (không thêm trường), D-12, luật mô tả FEAT-003 cho trường `entry_type` đã đổi chữ
  - Receives: `entry_type.options` sau FEAT-004 (`classify\nreason\nskip\nchange`); mô tả hiện nêu `classify`, `reason`, `skip` (và `change` nếu FEAT-004 đã thêm)
  - Returns: `options` nối thêm `config_change` ở cuối (giữ `change` của FEAT-004); `description` của `entry_type` nêu thêm "config_change là một lần gọi tool cấu hình hoặc tài khoản", vẫn ≤ 400 ký tự, vẫn có chữ "Hệ thống tự ghi" và "không sửa được"; test: `phrases["entry_type"]` thêm `"config_change"`. `field_count` của ERP AI Log KHÔNG đổi (dự kiến 38 = nền FEAT-006 35 + F4-T4 3; đọc số thật)
  - Expect: đỏ rồi xanh sau `cmd.migrate` + `cmd.test_one`; số dòng `ERP AI Log` trước = sau migrate (dán)

- [ ] T5 — `run_log`: `config_change` và `update_entry` — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py — test: erp_ai/agent/test_run_log.py — depends: F4-T4, T4
  - Criterion: AC-13, NFR-3 (nền), ADR-018 QĐ 1/2, D-12, D-13
  - Receives: `write_entry` đã nhận `change` (F4-T4); mẫu `_apply_classification` ở `runner.py` (cập nhật bằng `frappe.db.set_value`, commit khi không phải test)
  - Returns: `ENTRY_TYPES` thêm `"config_change"`; `update_entry(name, **fields) -> None` JSON hóa list/dict, `frappe.db.set_value(LOG_DOCTYPE, name, values, update_modified=False)`, commit khi không phải test, không cắt giá trị; `write_entry(entry_type="config_change", ...)` nhận `tools_called`, `actions`, `value_before/after`, `stop_reason`, `applied`, `instructor`
  - Expect: `test_config_change_entry_written_and_updated` (stop_reason `pending` → `applied`; giá trị 30.000 ký tự không bị cắt), `test_config_change_entry_not_counted_in_runs_or_cost` (`policy.runs_today` và tổng chi phí tháng không đổi khi có dòng này), `test_update_entry_json_encodes_and_keeps_modified`; test cũ xanh

- [ ] T6 — Test: chỉ System Manager sửa danh sách role được gán — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: F4-T6, T3
  - Criterion: AC-6 (chỉ System Manager sửa), design 2.1; không sửa `erp_ai_setting.py`
  - Receives: trường `assignable_roles` (T3); quyền hiện có của DocType
  - Returns: test mới, không đổi mã sản phẩm
  - Expect: `test_assignable_roles_only_system_manager_can_write` (user chỉ có `ERP AI Agent` rồi chỉ có `ERP AI Instructor` lưu → `frappe.PermissionError`; System Manager lưu được; lưu dòng role cấm và dòng role không tồn tại đều lưu được, không kiểm); test cũ của file xanh

## Phần 2, chính sách role

- [ ] T7 — `policy`: `HARD_BANNED_ROLES`, `PRIVILEGED_DOCTYPES`, `banned_roles` — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_policy.py — depends: T2, F4-T5, F4-T44
  - Criterion: AC-4 (role cấm cứng; role có quyền tạo/sửa trên User, DocType phân quyền, Custom Field, Property Setter, System Settings), NFR-1; ADR-016 QĐ 2
  - Receives: `PERMISSION_DOCTYPES` (T2); `POLICY_FIELDS` và `current_settings` của `policy.py` sau F4-T5 (`POLICY_FIELDS` của `test_architecture.py` đã có `auto_assign_enabled` của FEAT-006 và `code_change_enabled`, `code_change_apps` của F4-T5: giữ cả ba); `ChangeSettings`, `validate_change_apps` của F4-T5 không đổi; `frappe.get_meta(dt).permissions`
  - Returns: `HARD_BANNED_ROLES`, `PRIVILEGED_DOCTYPES` đúng chữ design 2.5; `banned_roles() -> frozenset[str]` = hằng ∪ role có `create` hoặc `write` (mọi permlevel) trên `PRIVILEGED_DOCTYPES`, tính mỗi lần gọi; `test_architecture.py`: `POLICY_FIELDS` thêm `assignable_roles`
  - Expect: `test_banned_roles_include_constants_and_roles_with_write_on_privileged_doctypes` (subTest: User, Role Profile, Custom Field, Property Setter, System Settings; role thử được cấp bằng Custom DocPerm tạo trong test), `test_agent_role_is_banned_by_constant_and_by_user_write`; `test_architecture::test_level_and_send_policy_fields_only_in_policy` xanh

- [ ] T8 — Kiểm phạm vi luật "tool không ghi" của FEAT-004 — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T7, F4-T25, F4-T31, F4-T44
  - Criterion: AC-15 (`cmd.test` xanh khi tool tài khoản và tool cấu hình lưu bản ghi), ADR-014 Ràng buộc; tránh luật đỏ ở T17..T44
  - Receives: `check_tool_never_saves_proposal` (F4-T31; F4-T25 có thể đã sửa luật "tool không ghi" có sẵn): "không `.save(`, `db_set`, `set_value` trong `agent/tools/**`"; `write_ticket.py` đã dùng `doc.save()` nên luật phải chỉ áp cho `propose_change.py`; FEAT-005 tool dùng `insert()`/`save()` qua ORM có phân quyền; luật git của F4-T44 (`test_git_subcommands_only_allowed_sets_per_file`, `test_no_forbidden_git_operations_in_product`: theo design FEAT-004 chỉ xét phần tử `argv` của lệnh git)
  - Returns: đọc luật thật. Nếu nó bắt mọi file trong `agent/tools/` thì thu hẹp về đúng `agent/tools/propose_change.py`, giữ ca âm (mã giả có `.save(` trong `propose_change.py` vẫn bị bắt); `db_set`/`set_value`/SQL ghi vẫn cấm cho cả thư mục (luật `check_tools_never_bypass_permissions` giữ nguyên, không ngoại lệ). Nếu luật đã đúng phạm vi: chỉ thêm test ghi nhận (`test_tool_save_rule_scope_allows_orm_save_outside_propose_change`). Thêm ca sạch `test_git_rules_ignore_config_group_literal`: mã giả không có lệnh git, có chuỗi `"config"`, `"account"`, `"config_change"` (tên nhóm, tên loại log) không bị hai luật git bắt; nếu bị bắt → `DESIGN_CONFLICT` (không nới luật git của ADR-022 ở FEAT-005)
  - Expect: đỏ nếu luật quá rộng (nạp mã giả `account.py` có `.save(` → bị bắt sai), rồi xanh; ca âm cho `propose_change.py` còn bắt; ca sạch luật git xanh; toàn bộ `test_architecture.py` xanh

- [ ] T9 — `policy`: `assignable_roles`, `is_protected_account` — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py — test: erp_ai/agent/test_policy.py — depends: T7, T3
  - Criterion: AC-4 (role ngoài danh sách; role cấm cứng lỡ nằm trong danh sách), AC-5 (đích bị bảo vệ), AC-6 (rỗng → không gán được); ADR-016 QĐ 1/3; A-5
  - Receives: `banned_roles` (T7); trường `assignable_roles` (T3); `authority.NEVER_AUTHORITY`; `frappe.permissions.AUTOMATIC_ROLES`
  - Returns: `ASSIGNABLE_ROLES_FIELD = "assignable_roles"`; `assignable_roles() -> frozenset[str]` (đọc bằng `frappe.db.get_single_value(..., cache=False)`; dòng strip, bỏ rỗng, bỏ trùng; ∩ Role đang có và không disabled; − `banned_roles()`); `is_protected_account(user, instructor, agent_user) -> bool` (user ∈ {Administrator, Guest, agent_user, instructor} hoặc có role (trừ tự động) thuộc `banned_roles()`); `assignable_roles` thêm vào `POLICY_FIELDS` ở code (tên hằng, không chuỗi rải rác)
  - Expect: `test_assignable_roles_ignores_blank_duplicate_missing_and_banned_lines`, `test_assignable_roles_empty_by_default`, `test_is_protected_account_each_case` (5 subTest: người ra lệnh, tài khoản agent, Administrator, Guest, user có role cấm; user thường → False)

## Phần 3, registry và prompt

- [ ] T10 — Registry: validator `object`, `minItems` — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T1, F4-T28
  - Criterion: nền AC-3, AC-9, AC-10 (bảng con: ngày nghỉ, state, transition, người nhận); D-16, ADR-014 Ràng buộc
  - Receives: `_value_ok` hiện có (`string/integer/boolean/array`, `enum`, `minLength/maxLength`, `minimum/maximum`, `maxItems`, `items`, khóa lạ bị từ chối)
  - Returns: kiểu `object` (`properties`, `required`, khóa lạ bị từ chối, đệ quy qua `items`) và `minItems` cho `array`; không đổi hành vi với schema đang có
  - Expect: `test_validator_object_required_and_unknown_key_refused`, `test_validator_nested_object_in_array`, `test_validator_min_items`; test cũ (kể cả `test_schemas_use_only_types_the_validator_knows`, nới theo kiểu `object` nếu đỏ) xanh

- [ ] T11 — Registry: `ToolSpec.writes`, `write_permlevels`, `commits`; không savepoint khi `commits`; `declared_write_permissions`, `call_log_doctype` — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T10
  - Criterion: AC-13 (một dòng nhật ký mỗi lời gọi cần biết DocType chính), AC-15 (quyền cài suy ra từ khai báo), ADR-014 QĐ 5, ADR-015 QĐ 2, ADR-018 QĐ 3
  - Receives: `ToolSpec` sau F4-T23/T28 (nhóm `change_propose`); `execute_tool` bọc savepoint `erp_ai_tool`
  - Returns: `ToolSpec` thêm `writes: tuple[str, ...] = ()`, `write_permlevels: tuple[int, ...] = (0,)`, `commits: bool = False` (giữ nguyên mặc định cho spec cũ); `group` Literal thêm `"config"`, `"account"`; `execute_tool`: `spec.commits` → gọi handler không savepoint; `call_log_doctype(name) -> str | None` (phần tử đầu của `writes` nếu tool nhóm `config`/`account`, tra trên mọi spec, không chỉ spec được cấp); `declared_write_permissions() -> dict[str, tuple[int, ...]]` (hợp `writes` × `write_permlevels` của spec nhóm `config`/`account`, sắp xếp)
  - Expect: `test_commit_tool_runs_without_savepoint` (`commits=True` không gọi `savepoint`/`release_savepoint`; `False` vẫn gọi), `test_call_log_doctype_only_for_config_and_account_groups`, `test_declared_write_permissions_unions_writes_and_permlevels`; mọi test cũ và `test_switch_off_*` của FEAT-004 xanh

- [ ] T12 — Registry: nhóm `config`, `account` vào bảng cấp duy nhất — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T11, F4-T23
  - Criterion: AC-1 (L0, L1, vượt ngân sách, không người ra lệnh: không nhóm mới), AC-2 (L2: có `config`, không `account`; L3: có cả hai), NFR-6; ADR-014 QĐ 1, ADR-011 QĐ 6
  - Receives: bảng điều kiện mỗi nhóm của FEAT-004 (một dòng mỗi nhóm, dòng `change_propose = change_enabled ∧ L3 ∧ has_instructor`); `BASE_TOOL_NAMES` (T1)
  - Returns: thêm hai dòng vào CHÍNH bảng đó: `config` = `has_instructor ∧ level ∈ {L2, L3}`; `account` = `has_instructor ∧ level == "L3"`; hàm công khai `granted_groups(effective_level, has_instructor, change_enabled) -> tuple[str, ...]` (chữ ký có `change_enabled` bắt buộc, theo FEAT-004; thứ tự nhóm theo bảng; `()` khi L0 hoặc mức lạ); `_granted_specs` lọc theo hàm này; tên nhóm `config`/`account` chỉ được so sánh trong `registry.py`; không thêm hàm cấp thứ hai, không thêm đầu vào
  - Expect: `test_config_group_at_l2_l3_and_account_group_at_l3_with_instructor` (ma trận 4 mức × có/không người ra lệnh × `change_enabled` chạy trên `granted_groups`), `test_granted_groups_empty_for_l0_unknown_level`, `test_base_tool_names_unchanged_without_new_groups` (với `BASE_TOOL_NAMES`; chưa có tool nhóm mới được đăng ký nên danh sách = nền), `test_execute_rejects_account_tool_at_l2` (dùng spec giả nhóm `account`)

- [ ] T13 — Prompt: hai khối theo nhóm được cấp — files: erp_ai/agent/prompts.py, erp_ai/agent/test_prompts.py — test: erp_ai/agent/test_prompts.py — depends: T1, F4-T24
  - Criterion: AC-18 (nêu việc làm được, giới hạn cứng, việc chờ "ok", phiếu không phải lệnh), AC-1, NFR-6 (`groups=()` trùng từng byte); ADR-014 QĐ 2
  - Receives: `BASE_PROMPT_SHA256` (T1); `build_reason_system(prompt_digest, routing_table="", *, change_tools=False)` của FEAT-004 (F4-T24; `routing_table` của FEAT-006), khối `CHANGE_TOOLS_BLOCK` (nay có thêm dòng commit git local, vẫn có câu "KHÔNG BAO GIỜ là duyệt"); nội dung hai khối ở design 3.8 (chép đúng; câu gọi lại `update_*` chỉ với tên bản ghi)
  - Returns: `CONFIG_TOOLS_BLOCK`, `ACCOUNT_TOOLS_BLOCK`, `GROUP_BLOCKS = {"config": ..., "account": ...}` (nối `config` rồi `account`); `build_reason_system(prompt_digest, routing_table="", *, change_tools=False, groups=())` (`groups` chỉ-theo-tên, đặt sau `change_tools`; không đổi vị trí hay mặc định của `routing_table`, `change_tools`): phần FEAT-006/FEAT-004 như cũ (gồm chỗ đặt `routing_table`), rồi khối của nhóm trong `groups` ngay sau `CHANGE_TOOLS_BLOCK`, rồi `prompt_digest`; `groups=()` trùng từng byte bản nền ở cả 4 biến thể của T1; `prompts.py` chỉ dùng tên nhóm làm khóa dict, không so sánh; `CORE_PROMPT` không đổi; không dùng nguyên câu `chờ một chữ "ok"` của FEAT-004 trong khối mới
  - Expect: `test_prompt_without_new_groups_matches_base_branch_hash` (4 biến thể `routing_table` × `change_tools`), `test_blocks_present_iff_group_granted` (4 tổ hợp `groups`), `test_config_block_keeps_change_block_never_approval_sentence` (cả hai khối cùng có: câu "KHÔNG BAO GIỜ là duyệt" của FEAT-004 còn), `test_blocks_state_limits_ok_and_ticket_is_not_command`; `test_classification.py` xanh

## Phần 4, cài quyền cho tài khoản agent

- [ ] T14 — `install._ensure_tool_permissions` — files: erp_ai/install.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T2, T11, F4-T33
  - Criterion: AC-15 (tài khoản agent không System Manager mà tool vẫn ghi được), ADR-015 QĐ 2/3, design 2.3, 4.7
  - Receives: `registry.declared_write_permissions()` (T11); `setup_custom_perms`; `_ensure_task_permission` làm mẫu; hằng `CUSTOM_DOCPERM_DOCTYPE`, `ROLE_DOCTYPE` (T2); test patch hàm khai báo trả `{"User": (0, 1), "Holiday List": (0,), ...}`
  - Returns: `_ensure_tool_permissions() -> None`: DocType không có trên site → `logger.warning` rồi bỏ; bảng con → bỏ; `setup_custom_perms(dt)`; mỗi level chưa có dòng `{parent, role: ERP AI Agent, permlevel}` → tạo (level 0: read/write/create; level > 0: read/write); không delete/submit/cancel/amend; không sửa hay xóa dòng có sẵn; `frappe.clear_cache(doctype=dt)`; dùng hằng của T2 thay chuỗi; CHƯA gọi trong `ensure_setup` (T15)
  - Expect: `test_tool_permissions_installed_twice_match_declarations` (2 lần → số dòng không đổi), `test_tool_permissions_keep_rows_added_by_humans`, `test_tool_permissions_skip_missing_doctype_and_child_tables`, `test_no_delete_submit_cancel_amend_granted`

- [ ] T15 — `ensure_setup` gọi cài quyền; kiểm tập role agent và Version — files: erp_ai/install.py, erp_ai/tests/test_install.py, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_install.py — depends: T14, T3, T8
  - Criterion: AC-6 (rỗng sau khi cài), AC-15 (đúng tập role {`ERP AI Agent`, `Agent`}), ADR-015 QĐ 3, ADR-016 Ràng buộc (agent không có quyền trên Version)
  - Receives: `_ensure_tool_permissions` (T14); `ensure_setup`; luật kiến trúc hiện có về installer
  - Returns: `ensure_setup` gọi `_ensure_tool_permissions()` ngay sau `_ensure_task_permission()`; `test_architecture.py`: sửa luật hiện có nếu thành đỏ (theo ADR-015), thêm `test_ignore_permlevel_for_fields_never_used` (0 lần trong `erp_ai/**` ngoài test), `test_single_installer_function_reads_tool_declarations` (chỉ `install._ensure_tool_permissions` gọi `declared_write_permissions`)
  - Expect: `test_assignable_roles_empty_after_setup`, `test_agent_role_set_unchanged_after_setup`, `test_agent_role_has_no_permission_on_version` (meta Version không có dòng `ERP AI Agent`), `test_ensure_setup_twice_does_not_change_permission_rows`; hai test kiến trúc mới có ca dương và ca âm theo mẫu của file

- [ ] T16 — `test_utils` A: user agent thử, ngữ cảnh tool, gọi qua registry, dọn bản ghi tự commit — files: erp_ai/test_utils.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T15, F4-T7, F4-T12, F4-T36, F4-T51
  - Criterion: AC-15 (ca thành công chạy dưới tài khoản agent chỉ có {`ERP AI Agent`, `Agent`}), quy tắc dọn test; design 7 (`test_utils.py`), 8
  - Receives: helper hiện có (`make_log_entry`, `set_agent_settings`, `FakeGateway`; helper FEAT-006 `make_routing_rules`, `make_sla`, `make_active_agent`, `make_team`; helper FEAT-004: gốc `apps/` tạm F4-T7, `GitSandbox` F4-T36/F4-T51, `RealCoreReposUntouchedMixin` F4-T51, đề xuất mẫu F4-T12; tất cả giữ nguyên, helper mới thêm cạnh, không trùng tên); `install._ensure_tool_permissions` (T14)
  - Returns: `make_agent_test_user() -> str` (user chỉ có {`ERP AI Agent`, `Agent`}, không System Manager); `make_tool_context(level="L3", instructor="<user>", **kw) -> ToolContext` (có `agent_user`; dựng `ToolContext` bằng đối số tên, để mặc định `routing_config`, `change_enabled=False`, `allowed_apps=()` của FEAT-006/FEAT-004); `grant_agent_permissions(testcase, *modules)`: vá `registry.TOOL_MODULES` thêm các module rồi gọi `_ensure_tool_permissions()`; `call_registered(testcase, module, name, args, context)`: vá `TOOL_MODULES` rồi gọi `registry.execute_tool` (để schema và nhóm được kiểm như thật, dùng được trước T21/T45); `register_cleanup(testcase, doctype, name)`: `addCleanup` chạy ngược thứ tự, dưới `Administrator`, `frappe.delete_doc(..., force=True)` rồi `frappe.db.commit()`, bỏ qua DocType/bản ghi đã mất
  - Expect: test tự kiểm của helper đặt trong `test_install.py`: `test_make_agent_test_user_has_exact_roles`, `test_register_cleanup_removes_committed_record_without_rollback` (bản ghi đã commit bị xóa sau `doCleanups()`); `test_utils` hiện có không đổi hành vi

## Phần 5, walking skeleton S1 (tài khoản qua runner, một Cổng model giả)

S1 = T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25. Đường rủi ro nhất: tự nâng quyền qua gán role (NFR-1). Không task nhánh tool cấu hình (T35..T46) bắt đầu trước khi review T25 là approve. Nhánh "xác nhận ok" và bộ chặn đích (T26..T34) không chung file với S1 nên chạy song song được.

- [ ] T17 — `account.py`: `create_user` thành công, đường gán role duy nhất — files: erp_ai/agent/tools/account.py, erp_ai/agent/tools/test_account.py — test: erp_ai/agent/tools/test_account.py — depends: T9, T11, T15, T16
  - Criterion: AC-3 (1 User bật, người dùng nội bộ, đúng 2 role ngoài role tự động, không mật khẩu, `send_welcome_email = 1`, `undo`), AC-4 (role cấm cứng, role ngoài danh sách), NFR-1, A-6, A-12; ADR-016 QĐ 4; design 3.4, 4.5
  - Receives: `policy.assignable_roles()`, `policy.banned_roles()` (T7, T9); `ToolSpec(... writes=("User",), write_permlevels=(0, 1))` (T11); `write_once`-kiểu bắt lỗi do T33 CHƯA có, nên tool này tự bắt `frappe.ValidationError` (D-17, savepoint cục bộ `erp_ai_account_write`)
  - Returns: `TOOLS` với `create_user(email, full_name, language?, roles?)` group `account`; chuẩn hóa email (`strip().lower()`, `validate_email_address`); `_save_user_with_roles(user_doc, roles, *, is_new)` là hàm DUY NHẤT gọi `append_roles`/`add_roles`/`append("roles", ...)` ngoài `install.py`: savepoint cục bộ → append → `insert()` (mới) → đọc lại `roles` từ DB, thiếu role → rollback savepoint cục bộ, từ chối `Frappe không lưu role: <r…>`; `first_name = full_name`, không mật khẩu, không `user_type`; kết quả theo design 3.1/3.4; `has_permission("User", "create")`; một role sai → từ chối cả lời gọi (0 User)
  - Expect: `test_create_user_with_two_assignable_roles` (đếm User = 1, enabled, System User, tập role = 2, `new_password` rỗng, `send_welcome_email = 1`, `undo` có), `test_create_user_refuses_each_hard_banned_role` (6 subTest, 0 User, 0 Has Role mới), `test_create_user_refuses_role_outside_list`; test chạy dưới `make_agent_test_user()` sau `grant_agent_permissions`

- [ ] T18 — `create_user`: các từ chối còn lại — files: erp_ai/agent/tools/account.py, erp_ai/agent/tools/test_account.py — test: erp_ai/agent/tools/test_account.py — depends: T17
  - Criterion: AC-4 (role cấm lỡ nằm trong danh sách; role có quyền User/phân quyền/Custom Field/Property Setter/System Settings; Role Profile, Module Profile; email sai; email đã có), AC-6 (danh sách rỗng: gán bị từ chối, tạo user 0 role vẫn được), NFR-1
  - Receives: `create_user` (T17); `banned_roles` (T7)
  - Returns: từ chối đúng chữ design 3.4: `email không hợp lệ`, `email <e> đã có tài khoản` (hoa/thường khác nhau vẫn trùng; user cũ không đổi), `role <r> bị cấm gán`, `ngôn ngữ <l> không có hoặc đang tắt`, `thiếu quyền create User`; khóa lạ (`role_profile_name`, `module_profile`, `user_type`, `new_password`, `api_key`) bị registry từ chối `tham số không hợp lệ: <key>` trước khi tool chạy (test qua `call_registered`)
  - Expect: `test_create_user_refuses_banned_role_listed_by_mistake`, `test_create_user_refuses_role_with_write_on_user`, `test_create_user_refuses_role_with_write_on_permission_doctype`, `test_create_user_refuses_role_with_write_on_custom_field_property_setter_system_settings` (3 subTest), `test_create_user_refuses_role_profile_and_module_profile`, `test_create_user_refuses_bad_email` (`"a@"`, `"x"`, chuỗi 141 ký tự), `test_create_user_refuses_existing_email_and_keeps_user`, `test_empty_list_refuses_roles_but_creates_user_without_roles`

- [ ] T19 — `add_user_roles` — files: erp_ai/agent/tools/account.py, erp_ai/agent/tools/test_account.py — test: erp_ai/agent/tools/test_account.py — depends: T18
  - Criterion: AC-5 (thêm đúng role, role cũ còn nguyên; từ chối 5 đích bị bảo vệ), NFR-1; ADR-016 QĐ 3/4; A-4, A-5; design 3.4, 4.5
  - Receives: `_save_user_with_roles` (T17); `policy.is_protected_account`, `policy.assignable_roles` (T9)
  - Returns: `add_user_roles(user, roles)`: user có; `not is_protected_account(user, ctx.instructor, ctx.agent_user)`; `has_permission("User", "write", doc=user)`; mọi role ∈ `assignable_roles()`; role mới = yêu cầu − đã có; rỗng → từ chối `user đã có đủ các role này` và KHÔNG gọi `save()`; còn lại lưu bằng `save(ignore_version=False)`; `before/after = {"user", "roles"}` (bỏ role tự động); `undo` đúng chữ design 3.4; từ chối `không tìm thấy tài khoản <u>`, `tài khoản <u> được bảo vệ, bot không đổi role`, `thiếu quyền write User`
  - Expect: `test_add_user_roles_keeps_existing_roles`, `test_add_user_roles_refuses_protected_targets` (5 subTest; user không đổi), `test_add_user_roles_refuses_when_nothing_new`

- [ ] T20 — Tài khoản: Version, đọc lại sau lưu — files: erp_ai/agent/tools/account.py, erp_ai/agent/tools/test_account.py — test: erp_ai/agent/tools/test_account.py — depends: T19
  - Criterion: AC-5, AC-14 (nền: Version đúng một bản, `owner` = agent), ADR-016 QĐ 4 (hai điều kiện lưu) và Ràng buộc; research U3
  - Receives: `add_user_roles` (T19); `frappe/core/doctype/version/version.py:152-180` (dòng con thêm theo `name`)
  - Returns: khóa lỗi nhỏ nếu T17/T19 chưa đạt: đường gán lưu user có sẵn bằng `save(ignore_version=False)` kể cả khi `in_test`; đọc lại thiếu role → rollback savepoint cục bộ (Version của lần lưu đó cũng mất)
  - Expect: `test_add_roles_writes_one_version_owned_by_agent_and_recall_writes_none` (1 lần thêm → đúng 1 Version, `owner` = agent, `added` của `roles` = đúng các dòng mới; gọi lại với role đã có → 0 Version mới, `modified` không đổi), `test_role_readback_failure_is_refused_and_rolled_back` (thu quyền level 1 của role agent trong test → `Frappe không lưu role`, 0 dòng mới)

- [ ] T21 — Đăng ký module `account` — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/tools/test_registry.py — depends: T20, T12, F4-T28
  - Criterion: AC-2 (cấp thật: `create_user`, `add_user_roles` ở `L3` có người ra lệnh; không ở `L2`), AC-1 (công tắc/mức khác: danh sách như nền)
  - Receives: `account.TOOLS` (T17..T20); `TOOL_MODULES` sau F4-T28 (có `propose_change`)
  - Returns: `TOOL_MODULES` nối `account` ở CUỐI (danh sách cũ giữ thứ tự); `test_registry.py`: số spec nền (14 sau FEAT-004) + 2; test đếm của F4-T28 (`test_all_specs_count_is_14`) sẽ đỏ: đổi số và tên test thành `test_all_specs_count_matches_modules` (thay đổi số spec là chỗ design cho phép sửa, không đổi assertion khác của FEAT-004); `test_no_write_tool_accepts_doctype_or_field` vẫn phủ `account`; `TestRealToolsRunWithoutCommit` chỉ chạy tool nền (không chạy tool tài khoản, vì cần `ToolContext` người ra lệnh); `test_architecture.py`: sửa luật đỏ nếu có (theo ADR-014, 015, 016), thêm `test_single_role_assignment_site` (chỉ `account._save_user_with_roles` và `install.py` gọi `append_roles`/`add_roles`/`append("roles"`)
  - Expect: `test_all_specs_count_matches_modules` (nền + 2), `test_account_group_only_at_l3_with_instructor` (tên tool trên ma trận), `test_base_tool_names_unchanged_without_new_groups` vẫn xanh (nhóm `account` chỉ hiện khi đủ điều kiện, nên các ô nền không đổi), `test_single_role_assignment_site`; `test_no_tool_module_commits` xanh

- [ ] T22 — Runner: cấp nhóm → prompt — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T21, T13, F4-T29, F4-T30
  - Criterion: AC-1 (vượt ngân sách → `L1` → schema và prompt như nền), AC-2, AC-18 (prompt theo kết quả cấp), NFR-6; ADR-014 QĐ 2
  - Receives: `granted_groups` (T12); `build_reason_system(prompt_digest, routing_table="", *, change_tools=False, groups=())` (T13); `_reason` sau F4-T29 (`system = build_reason_system(settings.prompt_digest, routing_table=<như FEAT-006>, change_tools=grants_change_tools(...))`)
  - Returns: `_reason`: `groups = registry.granted_groups(level, bool(instructor), context.change_enabled)`; `system = build_reason_system(settings.prompt_digest, routing_table=<như FEAT-006>, change_tools=<như FEAT-004>, groups=groups)` (chỉ thêm đối số tên `groups`); không đọc lại cấu hình; không import/gọi git (luật `test_no_git_in_web_and_runner` của F4-T44); không đổi gì khác ở runner
  - Expect: `test_over_budget_l3_run_gets_base_tools_and_prompt` (L3 + người ra lệnh + vượt ngân sách → schema và system gửi cổng = bản nền), `test_l3_instructor_run_sends_config_and_account_blocks`, `test_l2_instructor_run_sends_config_block_only`; test của FEAT-004 xanh nguyên

- [ ] T23 — Runner: một dòng `config_change` mỗi lời gọi (áp dụng, từ chối, sập) — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_agent_runner.py — depends: T22, T5, T11, F4-T4
  - Criterion: AC-13, NFR-3 (100% lời gọi có 1 dòng, kể cả từ chối), ADR-018 QĐ 1–3; design 4.2 bước 1–2, 4
  - Receives: `registry.call_log_doctype`, `run_log.write_entry/update_entry` (T5, T11); `_run_tool` sau F4-T30 (đã ghi dòng `change` cho tool đề xuất, giữ nguyên); mẫu phân loại `runner.py:229-286`
  - Returns: `_run_tool(block, context, log_base, ...)` với `log_base = {ticket, run_id, trigger, turn, instructor}`: `call_log_doctype(name)` `None` → luồng cũ không đổi (gồm nhánh `propose_*` của FEAT-004); có → `write_entry(**log_base, entry_type="config_change", tools_called=[name], actions=[{tool, doctype, name: None, ok: None}], applied=0, stop_reason="pending")` + commit (ngoài test) TRƯỚC khi chạy tool; sau tool `update_entry(... applied=1 nếu ok, stop_reason=applied|refused, actions=[{tool, doctype, name, ok, reason?}], value_before, value_after)`; exception → `stop_reason="crashed"`, `error="tool <tên>: <lớp>"`, `applied` giữ 0; `frappe.logger("erp_ai").info(...)` không giá trị trường; `test_architecture.py`: sửa luật "ai gọi `write_entry`" nếu đỏ theo ADR-018 (runner là chỗ duy nhất tạo dòng `config_change`; `changes/transitions.log_step` của F4-T13 vẫn tạo dòng `change`, giữ nguyên)
  - Expect: `test_each_new_tool_call_has_one_config_change_entry` (chạy trên `create_user`; hai lời gọi cùng tool trong một lượt → hai dòng), `test_refused_call_has_one_unapplied_entry_and_action_ok_false`, `test_crash_after_autocommit_leaves_pending_entry` (tool giả có `commits=True` ném sau lần lưu → `crashed`, `applied 0`), `test_log_entries_created_only_in_agent_core` xanh

- [ ] T24 — Runner: dòng `awaiting_ok`, bỏ `pending`, action vào dòng `reason`, trần kết quả — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T23
  - Criterion: AC-13 (`requested` lưu không cắt), AC-10 (nền: chờ "ok" không tạo dòng `applied`), NFR-7 (≤ 20.000 ký tự), ADR-018 QĐ 1.3 (sửa vòng 1); D-15; design 4.2 bước 4–5, 7
  - Receives: kết quả "chờ ok" có khóa `awaiting_confirmation`, `pending` (design 3.1); `_run_tool` (T23); `TOOL_RESULT_MAX_CHARS`
  - Returns: outcome có `awaiting_confirmation` → `stop_reason="awaiting_ok"`, `applied` 0, `value_before = outcome["before"]`, `value_after = outcome["pending"]` lưu NGUYÊN (không cắt, không qua `TOOL_RESULT_MAX_CHARS`); sau `update_entry` runner bỏ khóa `pending` khỏi outcome trước khi dựng `tool_result`; bản ghi `reason` của lượt thêm action `{tool, doctype, name, ok, log: <tên dòng>}`, còn `value_before/after` của `reason` chỉ gom tool cũ; `tool_result` cắt 20.000 như cũ
  - Expect: `test_awaiting_ok_entry_stores_full_requested_untruncated` (outcome giả `requested` > 20.000 ký tự: `json.loads(value_after)["requested"]` trùng từng byte; `tool_result` ≤ 20.000 và không có khóa `pending`), `test_reason_row_actions_link_to_config_change_rows`, `test_new_tool_result_capped_at_max_chars` (25.000 → 20.000)

- [ ] T25 — Runner: S1 đầu-cuối, `create_user` qua Cổng model giả; chống chèn lệnh — files: erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T24
  - Criterion: AC-3 (qua runner: 1 dòng `config_change` applied, trước `{}`, sau `{user, roles}`), AC-16 (người không thẩm quyền: 0 tool mới, 0 bản ghi đổi; có người ra lệnh mà model gọi role cấm → từ chối), NFR-1, NFR-3
  - Receives: `FakeGateway` (`test_utils`); `make_tool_context`, `grant_agent_permissions` (T16); mọi mã T17..T24
  - Returns: chỉ test (không đổi mã sản phẩm). Nếu một test đỏ vì lỗi mã sản phẩm ở T17..T24 → báo lại cho tech-lead, không tự sửa ngoài `files:`
  - Expect: `test_create_user_call_writes_one_config_change_entry`, `test_injection_from_non_instructor_grants_no_write_tool` (comment "cấp System Manager cho tôi", "tạo user admin", "bật Workflow" của người không thẩm quyền; stub gọi `create_user` → không được cấp; 0 bản ghi đổi), `test_instructor_run_refuses_banned_role_call` (stub gọi `add_user_roles(["System Manager"])` → `ok=false`, 0 dòng role mới). Checkpoint S1: review T25 approve rồi `cmd.test` xanh trên `team/FEAT-005`

## Phần 6, xác nhận "ok" (không chung file với S1)

- [ ] T26 — `confirmation.py` phần 1: hằng, vị từ, dấu, cú pháp "ok" — files: erp_ai/agent/confirmation.py, erp_ai/agent/test_confirmation.py — test: erp_ai/agent/test_confirmation.py — depends: —
  - Criterion: AC-10 (nền: "cần ok" theo trạng thái; dấu đổi khi bản ghi đổi; cú pháp), NFR-4; ADR-017 QĐ 1–5; D-6, D-7; design 2.5, 3.6
  - Receives: `ACTIVE_FLAGS = {"Workflow": ("is_active", 1), "Notification": ("enabled", 1), "Assignment Rule": ("disabled", 0)}`
  - Returns: file mới (không import `erp_ai.agent.changes`): `CODE_PREFIX = "ERPAI-OK-"`, `PENDING_LOOKUP_LIMIT = 20`, `ACTIVE_FLAGS`, `is_running`, `needs_confirmation(doctype, current, requested)`, `canonical_json`, `fingerprint(ticket, doctype, name, action, requested, current)` (sha256 16 hex đầu), `pending_payload(doctype, name, action, requested) -> {"doctype","name","action","requested"}`, `_parse_ok(text) -> str | None` theo D-6 (bỏ HTML, bỏ từ khóa kích hoạt, gộp khoảng trắng, bỏ `.`/`!` cuối, casefold, khớp `ok` | `ok <16 hex>` | `ok erpai-ok-<16 hex>`)
  - Expect: `test_needs_confirmation_by_state` (tạo → False; bật bản ghi đang tắt → True; sửa bản ghi đang chạy → True; sửa bản ghi đang tắt → False), `test_record_changed_after_notice_changes_fingerprint` (`modified` hoặc nội dung đổi → dấu khác), `test_canonical_json_is_key_order_independent`, `test_ok_syntax_variants` (`@ai ok`, `OK.`, `ok erpai-ok-<mã>` khớp; `okay`, `không ok`, `ok ok` không khớp)

- [ ] T27 — `test_utils` B: gieo lời báo trước, "ok", dòng chờ — files: erp_ai/test_utils.py, erp_ai/agent/test_confirmation.py — test: erp_ai/agent/test_confirmation.py — depends: T16, T26, T5
  - Criterion: AC-10, design 8 (test tool cần dòng chờ ghi bằng helper đúng như runner bước 4.2.4)
  - Receives: `confirmation.pending_payload`, `fingerprint` (T26); `run_log.write_entry/update_entry` (T5)
  - Returns: `make_ticket_for_confirmation()` (HD Ticket tối thiểu); `seed_comment(ticket, user, html, *, creation=None)`; `seed_notice(ticket, agent_user, code)` (comment của agent chứa `ERPAI-OK-<code>`); `seed_ok(ticket, user, text="@ai ok")`; `seed_awaiting_row(ticket, instructor, outcome)` ghi `write_entry` rồi `update_entry(value_after=outcome["pending"], stop_reason="awaiting_ok")` nguyên như runner; `make_instructor_user()`, `make_plain_user()` (không role)
  - Expect: test dùng helper nằm ở T28/T29; ở đây: `test_seed_helpers_create_ordered_comments_and_row` thêm vào `test_confirmation.py` (thứ tự `creation`, tác giả đúng, dòng chờ có `value_after.requested`)

- [ ] T28 — `confirmation.py` phần 2: `find_notice`, `is_confirmed` — files: erp_ai/agent/confirmation.py, erp_ai/agent/test_confirmation.py — test: erp_ai/agent/test_confirmation.py — depends: T27
  - Criterion: AC-10 (từ chối: người không có `ERP AI Instructor` kể cả người tạo phiếu và người được giao; "ok" trước lời báo trước; "ok" ở phiếu khác; "ok" trơn gắn lời báo trước gần nhất; không dùng lại), NFR-4; ADR-017 QĐ 1–5; D-6, D-8
  - Receives: `authority.fetch_ticket_comments(ticket, authority.MAX_COMMENT_LIMIT)`, `NEVER_AUTHORITY`, `ROLE_INSTRUCTOR`; `_parse_ok` (T26); helper T27
  - Returns: `find_notice(ticket, code, agent_user) -> dict | None` (comment của `agent_user` chứa đúng `ERPAI-OK-<code>`, tìm trên nội dung thô); `is_confirmed(ticket, code, agent_user) -> bool` đúng khi và chỉ khi: có lời báo trước N; có comment C cùng phiếu, `C.creation > N.creation`, tác giả ∉ `NEVER_AUTHORITY`, `ROLE_INSTRUCTOR ∈ frappe.get_roles(tác giả)` (không dùng `is_instruction`), cú pháp khớp, và (C có mã = `code` hoặc C là "ok" trơn với lời báo trước gần nhất của agent trước C chính là N)
  - Expect: `test_ok_by_user_without_instructor_role_is_rejected` (người tạo phiếu; người được giao có ToDo mà không role), `test_ok_before_notice_is_rejected`, `test_ok_on_other_ticket_is_rejected`, `test_bare_ok_binds_only_to_nearest_notice` (A, B rồi "ok" → chỉ B; `ok <mã A>` → A), `test_notice_by_non_agent_author_is_ignored`

- [ ] T29 — `confirmation.py` phần 3: `notice_html`, `confirmed_request` — files: erp_ai/agent/confirmation.py, erp_ai/agent/test_confirmation.py — test: erp_ai/agent/test_confirmation.py — depends: T28
  - Criterion: AC-10 (lời báo trước do hệ thống sinh, chữ model không lọt vào; nội dung dài; sửa kho lưu bị từ chối; phiếu khác không dùng được), NFR-4; ADR-017 QĐ 3, 6; D-8, D-15; design 2.2 (đọc lại dòng chờ), 3.6
  - Receives: `is_confirmed`, `fingerprint`, `canonical_json` (T26, T28); `frappe.get_all(LOG_DOCTYPE, ...)` chỉ trong file này; `frappe.utils.escape_html`
  - Returns: `notice_html(doctype, name, action, changes, side_effects, code) -> str` đúng khuôn design 3.6 (mọi giá trị qua `escape_html`, giá trị cắt 300 ký tự, không tham số chữ tự do); `confirmed_request(ticket, doctype, name, action, current, agent_user) -> dict | None`: lọc `ticket` + `entry_type="config_change"` + `stop_reason="awaiting_ok"`, `order_by creation desc`, `limit=PENDING_LOOKUP_LIMIT`; giải JSON `value_after` (hỏng → bỏ dòng); giữ dòng có `doctype`, `name`, `action` khớp; theo thứ tự tính `code = fingerprint(...)` từ `row.requested` + `current`, `is_confirmed` → trả `requested` của dòng đầu đạt, không có → `None`; chỗ duy nhất đọc ERP AI Log để lấy dòng chờ
  - Expect: `test_notice_text_is_built_from_record_and_request_only` (chuỗi đánh dấu trong `ToolContext` và `post_comment` cùng lượt không xuất hiện; cùng đầu vào → HTML và mã giống hệt), `test_notice_escapes_html_and_truncates_values`, `test_confirmed_request_uses_row_bound_to_nearest_notice` (hai dòng A, B + "ok" trơn → B; `ok <mã A>` → A; JSON hỏng bị bỏ; không dòng → `None`), `test_confirmed_request_ignores_other_ticket_rows`, `test_tampered_requested_row_does_not_match_notice_code`

- [ ] T30 — `write_ticket`: tách `add_ticket_comment`, `post_comment` từ chối mã xác nhận — files: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_write_ticket.py — test: erp_ai/agent/tools/test_write_ticket.py — depends: T26
  - Criterion: AC-10 (model không giả được lời báo trước), AC-16; D-8; ADR-017 Ràng buộc; design 3.7
  - Receives: `post_comment` hiện có (bản nền đã có sửa của FEAT-006 ở `write_ticket.py`, `test_write_ticket.py`: đọc mã thật, giữ nguyên hành vi và test đó); `CODE_PREFIX` (T26)
  - Returns: `add_ticket_comment(ticket_name: str, html: str) -> dict` (kiểm quyền đọc phiếu, quyền tạo Comment, `doc.new_comment`); `post_comment` = kiểm mã rồi gọi hàm đó; từ chối nội dung mà bản thô hoặc bản bỏ HTML chứa `ERPAI-OK-` (không phân biệt hoa thường) bằng câu `nội dung không được chứa mã xác nhận`; hành vi cũ của `post_comment` giữ nguyên
  - Expect: `test_post_comment_refuses_confirmation_code` (`ERPAI-OK-`, `erpai-ok-`, mã chèn thẻ HTML như `ERPAI-<b>OK-</b>…`), `test_add_ticket_comment_posts_for_permitted_user`; test cũ xanh

## Phần 7, bộ chặn đích dùng chung

- [ ] T31 — `config_guard.py` phần 1: hằng và bất biến tĩnh — files: erp_ai/agent/tools/config_guard.py, erp_ai/agent/tools/test_config_guard.py — test: erp_ai/agent/tools/test_config_guard.py — depends: —
  - Criterion: AC-7 (giao của khóa nhận khi tạo với tập thuộc tính phân quyền = rỗng), AC-8, NFR-2; ADR-014 QĐ 3; design 2.5
  - Receives: danh sách ở design 2.5 (`PERMISSION_ATTRIBUTES` 13 khóa, `DISPLAY_PROPERTIES` 11 khóa kèm kiểu, `CUSTOM_FIELD_TYPES` 15 kiểu, `CUSTOM_FIELD_FORCED`)
  - Returns: file mới, chỉ hằng (không `TOOLS`, không import `erp_ai.agent.changes`): `PERMISSION_ATTRIBUTES`, `DISPLAY_PROPERTIES`, `CUSTOM_FIELD_TYPES`, `CUSTOM_FIELD_FORCED` (mọi khóa của `PERMISSION_ATTRIBUTES` trừ `options` về `0`/`""`, cộng `unique = 0`)
  - Expect: `test_custom_field_inputs_and_display_properties_disjoint_from_permission_attributes` (`set(DISPLAY_PROPERTIES) ∩ PERMISSION_ATTRIBUTES = ∅`), `test_forced_values_cover_every_permission_attribute_except_options`, `test_custom_field_types_exclude_code_attach_table_password`

- [ ] T32 — `config_guard`: `forbidden_targets`, `check_target`, `check_field` — files: erp_ai/agent/tools/config_guard.py, erp_ai/agent/tools/test_config_guard.py — test: erp_ai/agent/tools/test_config_guard.py — depends: T31, T11
  - Criterion: AC-7, AC-8, AC-11 (DocType đích bị cấm; Single; bảng con), NFR-2; ADR-014 QĐ 3; D-9, D-19; design 3.3, 3.7
  - Receives: `read.denied_doctypes()`, `constants.PERMISSION_DOCTYPES` (T2), `registry.declared_write_permissions()` (T11); `frappe.get_meta`
  - Returns: `forbidden_targets() -> frozenset[str]` (= `read.denied_doctypes()` ∪ `PERMISSION_DOCTYPES` ∪ khóa của `declared_write_permissions()`); `check_target(doctype, *, allow_child) -> str | None` với `DocType <dt> không tồn tại` / `bị cấm cấu hình` / `là trang cài đặt, ngoài phạm vi` / `là bảng con, không dùng được`; `check_field(doctype, fieldname) -> str | None` (`trường <f> không có trên <dt>`, `trường <f> có permlevel khác 0, bot không đổi`)
  - Expect: `test_forbidden_targets_compose_existing_definitions`, `test_check_target_each_refusal` (cấm, không có, Single, bảng con), `test_check_field_refuses_missing_and_nonzero_permlevel`

- [ ] T33 — `config_guard.write_once` — files: erp_ai/agent/tools/config_guard.py, erp_ai/agent/tools/test_config_guard.py — test: erp_ai/agent/tools/test_config_guard.py — depends: T32
  - Criterion: AC-7..AC-10, AC-12 (lỗi Frappe → lý do dùng được, không nửa chừng); D-17; ADR-018 QĐ 3
  - Receives: `ToolSpec.commits` (T11)
  - Returns: `write_once(write: Callable[[], None], *, commits: bool) -> str | None`: chạy lần ghi cuối; bắt `frappe.ValidationError` (và lớp con) → `Frappe từ chối: <thông điệp bỏ HTML, cắt 150>`; tool không tự commit bọc savepoint cục bộ `erp_ai_config_write` (rollback khi lỗi); tool `commits=True` không savepoint; exception khác ném tiếp
  - Expect: `test_write_once_returns_reason_for_validation_error_and_rolls_back_local_savepoint`, `test_write_once_commits_true_uses_no_savepoint`, `test_write_once_other_exception_propagates`, `test_write_once_strips_html_and_cuts_message`

- [ ] T34 — `config_guard.request_confirmation` — files: erp_ai/agent/tools/config_guard.py, erp_ai/agent/tools/test_config_guard.py — test: erp_ai/agent/tools/test_config_guard.py — depends: T33, T29, T30
  - Criterion: AC-10 (chờ "ok", ghi đúng bản đã được "ok", không trộn bản), NFR-4; ADR-017 QĐ 3, 6; D-15, D-18; design 3.7, 4.4
  - Receives: `confirmation.{needs_confirmation, fingerprint, canonical_json, find_notice, notice_html, pending_payload, confirmed_request}` (T26..T29); `write_ticket.add_ticket_comment` (T30); tool KHÔNG đọc ERP AI Log
  - Returns: `request_confirmation(ctx, doctype, name, action, requested, current, changes, side_effects) -> tuple[dict | None, dict | None]` (đúng một phần tử khác `None`): `requested is None` → `confirmed_request(...)` có → `(bản lưu, None)`, không → `(None, từ chối "không có thay đổi đã được ok cho <dt> <n>")`; `requested` có và `not needs_confirmation` → `(requested, None)`; cần "ok": bản lưu đạt và `canonical_json(bản lưu) == canonical_json(requested)` → `(bản lưu, None)`; còn lại là yêu cầu mới → dấu từ `requested` + `current`, đăng lời báo trước qua `add_ticket_comment` (không đăng lại nếu `find_notice` đã có), trả `(None, kết quả "chờ ok" kèm pending_payload)` theo design 3.1; không bao giờ trộn bản lưu với nội dung mới
  - Expect: `test_request_confirmation_without_ok_posts_one_notice_and_returns_pending`, `test_recall_does_not_repost_notice`, `test_recall_with_same_content_writes_stored_request`, `test_recall_with_different_content_returns_new_notice_and_no_write`, `test_requested_none_without_stored_row_is_refused`, `test_create_actions_never_need_confirmation`

## Phần 8, tool cấu hình (sau review S1 approve)

Tool tài khoản dùng chung mẫu: mỗi tool khai `ToolSpec(group="config", writes=(...), commits=...)`; đích đi qua `check_target`/`check_field`; `document_type`, `fieldname`, `property` là GIÁ TRỊ; không `ignore_permissions`, `make_property_setter`, `ignore_permlevel_for_fields`. Chưa đăng ký vào `TOOL_MODULES` (T45); test gọi qua `call_registered` và `grant_agent_permissions`. Test tool tự commit dùng `register_cleanup`.

- [ ] T35 — `add_custom_field`: thành công và từ chối cơ bản — files: erp_ai/agent/tools/config_fields.py, erp_ai/agent/tools/test_config_fields.py — test: erp_ai/agent/tools/test_config_fields.py — depends: T25, T34
  - Criterion: AC-7 (trường vào meta với `permlevel = 0`, `ignore_user_permissions = 0`; bản đồ phân quyền trước/sau chỉ khác trường mới; từ chối DocType cấm, trường duy nhất, tên trùng), NFR-2; ADR-014 QĐ 3/5; D-3, D-4; design 3.3, 4.3
  - Receives: `config_guard.{check_target, write_once, CUSTOM_FIELD_FORCED, CUSTOM_FIELD_TYPES, DISPLAY_PROPERTIES}`; `ToolSpec(writes=("Custom Field",), commits=True)`
  - Returns: `TOOLS` với `add_custom_field` đúng schema design 3.3 (không khóa trong `PERMISSION_ATTRIBUTES` và không `options`: Link dùng `link_doctype`, Select dùng `select_options`); dựng tài liệu từ danh sách khóa tường minh + `CUSTOM_FIELD_FORCED`; `insert()`; `undo` = `Desk → Customize Form → <dt> → xóa trường <f>`; từ chối `DocType … bị cấm cấu hình`, `trường <f> đã có trên <dt>` (kể cả trường mặc định Frappe như `name`), khóa `unique` bị registry chặn
  - Expect: `test_add_custom_field_appears_in_meta_with_level_zero` (bản đồ `{trường: permlevel, ignore_user_permissions}` trước/sau chỉ khác trường mới), `test_add_custom_field_refuses_forbidden_doctype` (`User`, `ERP AI Setting`, `Custom DocPerm`), `test_add_custom_field_refuses_unique`, `test_add_custom_field_refuses_duplicate_fieldname`; dọn bằng `register_cleanup`, không rollback

- [ ] T36 — `add_custom_field`: khóa phân quyền, Link, kiểu, tên — files: erp_ai/agent/tools/config_fields.py, erp_ai/agent/tools/test_config_fields.py — test: erp_ai/agent/tools/test_config_fields.py — depends: T35
  - Criterion: AC-7 (mỗi khóa trong tập thuộc tính phân quyền kể cả giá trị 0 → từ chối; Link tới DocType bị cấm), NFR-2; ADR-014 QĐ 3
  - Receives: `add_custom_field` (T35); `PERMISSION_ATTRIBUTES`
  - Returns: từ chối đúng chữ design 3.3: `tên trường <f> không hợp lệ` (mẫu `^[a-z][a-z0-9_]{2,60}$`), `<kiểu> cần <khóa>` / `<khóa> chỉ dùng với kiểu <kiểu>`, `link_doctype <x> bị cấm` / `… không tồn tại` / `… là bảng con`, `giá trị <p> không hợp lệ`; mọi khóa phân quyền gửi vào bị registry từ chối `tham số không hợp lệ: <key>`
  - Expect: `test_add_custom_field_refuses_each_permission_attribute_key` (13 subTest gồm `permlevel=0`, `ignore_user_permissions`, `fetch_from`, `reqd`; 0 Custom Field mới), `test_add_custom_field_refuses_link_to_forbidden_doctype` (`link_doctype="User"`), `test_add_custom_field_refuses_bad_fieldname_and_type_combinations` (`A`, `1x`, 62 ký tự; Link thiếu `link_doctype`; Select thiếu `select_options`)

- [ ] T37 — `set_field_property` — files: erp_ai/agent/tools/config_fields.py, erp_ai/agent/tools/test_config_fields.py — test: erp_ai/agent/tools/test_config_fields.py — depends: T36
  - Criterion: AC-8 (property hợp lệ có hiệu lực ngay; mọi property khác, phạm vi DocType, trường permlevel ≠ 0 bị từ chối), NFR-2; ADR-014 QĐ 3/5; D-9; design 3.3, 4.3
  - Receives: `DISPLAY_PROPERTIES`, `check_field` (T31, T32); `ToolSpec(writes=("Property Setter",), commits=False)`
  - Returns: `set_field_property(document_type, fieldname, property, value)`: `property` enum từ `DISPLAY_PROPERTIES`; chuẩn hóa `value` theo kiểu (Check ∈ {"0","1"}, `columns` 0..10, `width`/`print_width` khớp `^\d{1,4}(px)?$`); bằng giá trị cũ → từ chối `không có gì thay đổi`; dựng `frappe.get_doc({... "doctype_or_field": "DocField"}).insert()`, KHÔNG `make_property_setter`; `before` = `meta.get_field(f).get(property)`; `undo` đúng design 4.3
  - Expect: `test_set_allowed_property_takes_effect_on_next_meta` (`label` mới ở `frappe.get_meta`; bản đồ permlevel trước/sau không đổi), `test_set_field_property_refuses_each_forbidden_property` (12 subTest: `reqd`, `hidden`, `read_only`, `permlevel`, `fieldtype`, `options`, `fetch_from`, `depends_on`, `mandatory_depends_on`, `default`, `unique`, `ignore_user_permissions`; bản ghi không đổi), `test_set_field_property_refuses_doctype_scope` (`doctype_or_field="DocType"`, `property="allow_guest_to_view"`), `test_set_field_property_refuses_field_above_level_zero_and_bad_values` (permlevel 1; `columns = 11`; `bold = "2"`)

- [ ] T38 — `config_holidays`: `create_holiday_list`, `add_holidays` — files: erp_ai/agent/tools/config_holidays.py, erp_ai/agent/tools/test_config_holidays.py — test: erp_ai/agent/tools/test_config_holidays.py — depends: T33, T25
  - Criterion: AC-9 (đúng các ngày; ngày cũ còn; sai dạng, ngoài khoảng, trùng bị từ chối); design 3.3, 4.3
  - Receives: `write_once`; `ToolSpec(writes=("Holiday List",), commits=False)`; `frappe.utils.getdate`
  - Returns: `create_holiday_list(name, from_date, to_date, holidays?)`, `add_holidays(name, holidays)` (chỉ `append`, không sửa/xóa dòng cũ; `weekly_off = 0`); từ chối `ngày <d> không hợp lệ`, `ngày <d> ngoài khoảng <from>..<to>`, `ngày <d> đã có`, `khoảng ngày không hợp lệ`, `Holiday List <n> đã tồn tại`, `không tìm thấy Holiday List <n>`; `undo` = xóa các dòng ngày đã thêm
  - Expect: `test_create_list_and_add_holidays_keeps_old_dates`, `test_refuses_bad_format_out_of_range_and_duplicate_dates` (`2027-02-30`, `27/01/2027`, `to_date + 1`, ngày đã có, ngày lặp trong yêu cầu, `to_date < from_date`)

- [ ] T39 — `config_workflow`: `create_workflow`, `update_workflow` — files: erp_ai/agent/tools/config_workflow.py, erp_ai/agent/tools/test_config_workflow.py — test: erp_ai/agent/tools/test_config_workflow.py — depends: T34, T25
  - Criterion: AC-10 (Workflow tạo ở trạng thái chưa kích hoạt; sửa bản ghi đang chạy cần "ok"), AC-11, NFR-4; ADR-014 QĐ 4; G-1, A-7 sửa; D-10, D-11; design 3.3, 4.3
  - Receives: `request_confirmation`, `write_once`, `check_target(allow_child=False)` (T32..T34); `ToolSpec(writes=("Workflow", "Workflow State", "Workflow Action Master", "Custom Field"), commits=True)`
  - Returns: `create_workflow(name, document_type, states, transitions)` luôn `is_active=0`, `override_status=0`, `send_email_alert=0`, `workflow_state_field="workflow_state"`, không `condition`/`update_field`/`update_value`/`next_action_email_template`; tạo Workflow State/Action còn thiếu (chỉ tạo); `update_workflow(name, states?, transitions?)`: có cả hai = thay hai bảng, không có cái nào = gọi lại sau "ok"; một trong hai → `cần đủ định nghĩa hoặc chỉ name`; bản ghi đang chạy → đi qua `request_confirmation(action="update")`; `notes` khi trường `workflow_state` mới được tạo: `Frappe tạo trường ẩn workflow_state trên <dt>; chỉ Administrator xóa được` và `Các chứng từ <dt> có sẵn được điền trạng thái mặc định <state đầu> vào cột ẩn`; từ chối `<dt> đã có trường workflow_state không phải của Workflow`, `role <r> không dùng được trong Workflow` (`Guest`/`All`), `tên <x> không hợp lệ` (ký tự `<>{}`)
  - Expect: `test_create_workflow_inactive_with_side_effect_notes`, `test_update_active_workflow_requires_ok` (không "ok" → bản ghi không đổi, 1 comment báo trước), `test_refuses_existing_non_workflow_state_field_and_guest_roles`, `test_update_with_partial_definition_is_refused`; dọn Workflow, Workflow State/Action, Custom Field `workflow_state` bằng `register_cleanup`, không rollback; dùng DocType thử ít bản ghi nhất

- [ ] T40 — `activate_workflow` và luồng "ok" của Workflow — files: erp_ai/agent/tools/config_workflow.py, erp_ai/agent/tools/test_config_workflow.py — test: erp_ai/agent/tools/test_config_workflow.py — depends: T39
  - Criterion: AC-10 (kích hoạt chỉ sau "ok" hợp lệ; không dùng lại "ok"), NFR-4; D-15, D-18; design 4.4
  - Receives: `request_confirmation` (T34); helper `seed_ok`, `seed_awaiting_row` (T27)
  - Returns: `activate_workflow(name)`: `requested = {"is_active": 1}`; `side_effects` liệt kê Workflow đang chạy khác của cùng DocType (Frappe sẽ tắt); bật bản ghi đang bật → `Workflow <n> đã bật sẵn`; `undo` = `Desk → Workflow <n> → bỏ tick Is Active`
  - Expect: `test_activate_without_ok_posts_notice_and_keeps_inactive` (gọi lại không đăng thêm), `test_activate_after_valid_ok_succeeds_and_ok_cannot_be_reused` (lần hai → `đã bật sẵn`; sau khi ghi, dấu cũ không còn khớp)

- [ ] T41 — `config_notification`: `create_notification`, `enable_notification` — files: erp_ai/agent/tools/config_notification.py, erp_ai/agent/tools/test_config_notification.py — test: erp_ai/agent/tools/test_config_notification.py — depends: T34, T25
  - Criterion: AC-10 (tạo `enabled = 0`; bật cần "ok"), AC-11 (người nhận chỉ role/User có sẵn/trường chứng từ; bất biến), NFR-4; A-11; D-5, D-10, D-11; design 3.3, 4.3
  - Receives: `request_confirmation`, `write_once`, `check_target` (T32..T34); `ToolSpec(writes=("Notification",), commits=False)`
  - Returns: `create_notification(...)` đúng schema design 3.3 (`message` ≤ 50.000), giá trị tự đặt: `enabled=0`, `is_standard=0`, `set_property_after_alert=""`, `property_value=""`, `attach_print=0`, `send_to_all_assignees=0`, không `sender`, `bcc` rỗng; `kind=user` → `cc` = email của User; `enable_notification(name)`: kiểm bất biến của bản ghi hiện có (kênh, `set_property_after_alert`, `is_standard`, `bcc`, `cc` ngoài hệ thống) rồi `requested = {"enabled": 1}` qua `request_confirmation`; từ chối `người nhận <x> không hợp lệ`, `value_changed <f> không hợp lệ`, `Notification <n> có cấu hình bot không được bật: <trường>`, `Notification <n> đã bật sẵn`
  - Expect: `test_create_notification_disabled_and_enable_requires_ok`, `test_refuses_external_address_and_bad_recipients` (email không thuộc User; user tắt; role `Guest`/`All`; trường không phải email/User), `test_enable_refuses_record_violating_invariants` (`channel=Slack`, `set_property_after_alert`, `bcc` ngoài)

- [ ] T42 — `update_notification` và "ok" cho nội dung dài (D-15) — files: erp_ai/agent/tools/config_notification.py, erp_ai/agent/tools/test_config_notification.py — test: erp_ai/agent/tools/test_config_notification.py — depends: T41
  - Criterion: AC-10 (sửa bản ghi đang chạy ghi đúng bản đã "ok"; sửa kho lưu, đổi nội dung, phiếu khác bị từ chối), NFR-4; ADR-017 QĐ 6; D-15
  - Receives: `request_confirmation` (T34); helper T27; Notification đang bật dựng trong test
  - Returns: `update_notification(name, <khóa nội dung>?)`: đủ các khóa bắt buộc của create = thay toàn bộ định nghĩa; chỉ `name` = gọi lại sau "ok", ghi bản đã lưu; một phần → `cần đủ định nghĩa hoặc chỉ name`; giữ `enabled` hiện có; `requested` = trường tool quản lý (gồm dòng người nhận đã dựng)
  - Expect: `test_update_running_notification_long_html_message_applies_stored_request` (`message` > 2.000 ký tự có HTML và nhiều dòng; lời gọi 1 chờ "ok", bản ghi không đổi; "ok" hợp lệ; gọi lại chỉ `name` → `message` trùng từng byte), `test_tampered_stored_request_is_refused_and_record_unchanged`, `test_recall_with_different_content_posts_new_notice_and_writes_nothing`, `test_stored_request_on_other_ticket_is_not_used`, `test_update_with_partial_definition_is_refused`

- [ ] T43 — `config_assignment_rule`: `create_assignment_rule`, `update_assignment_rule`, `enable_assignment_rule` — files: erp_ai/agent/tools/config_assignment_rule.py, erp_ai/agent/tools/test_config_assignment_rule.py — test: erp_ai/agent/tools/test_config_assignment_rule.py — depends: T34, T25
  - Criterion: AC-10 (tạo `disabled = 1`; bật và sửa bản ghi đang bật cần "ok"), NFR-4; research C7 (người được giao phải đọc được DocType); D-11, D-15; design 3.3, 4.3
  - Receives: `request_confirmation`, `write_once`, `check_target` (T32..T34); `ToolSpec(writes=("Assignment Rule",), commits=False)`
  - Returns: `create_assignment_rule(...)` (`disabled=1`, `close_condition=""`, `due_date_based_on=""`, `field=""`), `update_assignment_rule(name, ...)` (đủ hoặc chỉ `name`, như `update_notification`), `enable_assignment_rule(name)` (`disabled = 0`); từ chối `người được giao <u> không đọc được <dt>` (kiểm cả lúc bật), `Assignment Rule <n> đã bật sẵn`
  - Expect: `test_create_rule_disabled_and_enable_requires_ok`, `test_refuses_user_without_read_permission` (khi tạo và khi bật), `test_update_running_rule_requires_ok_and_applies_stored_request`

- [ ] T44 — `config_system`: `set_system_settings` — files: erp_ai/agent/tools/config_system.py, erp_ai/agent/tools/test_config_system.py — test: erp_ai/agent/tools/test_config_system.py — depends: T33, T25
  - Criterion: AC-12 (6 trường hiển thị/khu vực đổi được; mật khẩu, 2FA, phiên, scheduler, email bị từ chối), NFR-2; A-1; design 3.3, 4.3
  - Receives: `write_once`; `ToolSpec(writes=("System Settings",), commits=False)`; `frappe.utils.momentjs.get_all_timezones()`
  - Returns: `set_system_settings(language?, time_zone?, date_format?, time_format?, number_format?, first_day_of_the_week?)` (≥ 1 khóa; giá trị Select ngoài `options` của meta bị từ chối; `language` không có/đang tắt; múi giờ ngoài danh sách); chỉ 6 trường này; `doc = frappe.get_doc("System Settings")`, `update`, `save()`; `before/after` chỉ 6 trường
  - Expect: `test_display_region_fields_change` (6 trường so trước/sau), `test_refuses_password_2fa_session_scheduler_email_fields` (`minimum_password_score`, `enable_two_factor_auth`, `session_expiry`, `enable_scheduler`, `email_footer_address`; mỗi khóa một subTest; không đổi), `test_refuses_values_outside_options_and_empty_call` (`date_format="yy"`, múi giờ lạ, ngôn ngữ tắt, `{}`)

- [ ] T45 — Đăng ký sáu module cấu hình, cập nhật số spec — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T37, T38, T40, T42, T43, T44, T21, F4-T28
  - Criterion: AC-2 (đủ cấp thật: `L2` có 14 tool `config`, không `account`; `L3` có cả hai), AC-1 (các ô nền không đổi), AC-15 (nới đúng một chỗ), NFR-6; ADR-014 QĐ 1, 5
  - Receives: `TOOLS` của sáu module (T35..T44); `TOOL_MODULES` sau T21
  - Returns: `TOOL_MODULES` nối `config_fields`, `config_holidays`, `config_workflow`, `config_notification`, `config_assignment_rule`, `config_system` (rồi `account` đã có từ T21: thứ tự cuối `... propose_change, config_fields, config_holidays, config_workflow, config_notification, config_assignment_rule, config_system, account`); `test_registry.py`: tổng spec = nền + 16 (30 sau FEAT-004; design ghi 27 là con số trước FEAT-004; FEAT-006 không thêm `ToolSpec`), test đếm đã đổi ở T21 (gốc `test_all_specs_count_is_14` của F4-T28) nay là 30, `test_no_write_tool_accepts_doctype_or_field` nới đúng một chỗ: bỏ qua nhóm `config`, giữ cho `ticket_write`, `task_write`, `account`, `change_propose`; `TestRealToolsRunWithoutCommit` chỉ chạy tool nền; `test_no_schema_property_looks_like_confirmation` (không khóa chứa `confirm`, `approved`, `ok_`, đệ quy object); `test_no_tool_module_commits` phủ module mới
  - Expect: `test_config_group_at_l2_l3_and_account_group_at_l3_with_instructor` chạy lại với tool thật, `test_all_specs_count_is_base_plus_16`, `test_no_schema_property_looks_like_confirmation`, `test_base_tool_names_unchanged_without_new_groups` (với `BASE_TOOL_NAMES` của T1)

- [ ] T46 — Từ chối mọi đích cấm ở mọi tool cấu hình; tool không bỏ qua phân quyền — files: erp_ai/agent/tools/test_config_guard.py — test: erp_ai/agent/tools/test_config_guard.py — depends: T45
  - Criterion: AC-11 (mọi tool cấu hình × một DocType cấm → `ok=false`, đích không đổi), AC-15 (chạy dưới tài khoản agent không System Manager), NFR-2; ADR-014 QĐ 3
  - Receives: 11 tool nhận hoặc đọc `document_type`; `make_agent_test_user`, `call_registered`, `grant_agent_permissions` (T16)
  - Returns: chỉ test; lỗi mã sản phẩm → báo tech-lead
  - Expect: `test_every_target_tool_refuses_forbidden_doctype` (11 tool × `User` hoặc DocType phân quyền; bản ghi đích không đổi), `test_success_cases_run_with_agent_role_set_only` (một ca thành công mỗi tool dưới user chỉ có {`ERP AI Agent`, `Agent`}), `test_tools_never_use_permission_bypass_flags` (quét nguồn của sáu module `config_*` và `account`: 0 lần `ignore_permissions`, `ignore_permlevel_for_fields`, `make_property_setter`)

## Phần 9, cảnh báo hằng ngày

- [ ] T47 — `tasks._role_row_adders` — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T2, F4-T4
  - Criterion: AC-14 (nguồn gốc dòng Has Role đọc từ Version, fail-closed), ADR-016 QĐ 5 (sửa vòng 1); D-14; design 3.7, 4.6 bước 3
  - Receives: `frappe.get_all("Version", ...)`; `frappe/core/doctype/version/version.py:152-180`
  - Returns: `_role_row_adders(user) -> dict[str, str] | None` đúng bước 3 design 4.6: lấy `modified, owner` của User; Version theo `creation asc`; không bản nào có `creation ≥ modified` → `None`; `data` hỏng JSON → `None`; còn lại map `row["name"] -> version.owner` cho mọi phần tử `["roles", row]` trong `data["added"]`; HÀM DUY NHẤT trong `erp_ai/**` (trừ test) đọc `Version`
  - Expect: `test_role_row_adders_maps_added_rows_to_version_owner`, `test_role_row_adders_none_when_last_save_has_no_version`, `test_role_row_adders_none_on_corrupt_version_data`

- [ ] T48 — Cảnh báo: ngoại lệ A-9 theo nguồn gốc dòng role — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_tasks.py — depends: T47, T9, T20, T23
  - Criterion: AC-14 (dòng role do tool gán trong danh sách: 0 cảnh báo; role cấm hoặc ngoài danh sách do agent: đúng 1 cảnh báo nêu tên user; role của tài khoản agent giữ nguyên), ADR-016 QĐ 5; A-9; design 4.6
  - Receives: `_role_row_adders` (T47); `policy.assignable_roles`, `policy.is_protected_account` (T9); `_permission_records_by_agent` hiện có
  - Returns: `_permission_records_by_agent` giữ vòng lặp trên `PERMISSION_DOCTYPES`; với `HAS_ROLE_DOCTYPE` lấy cột `name, role, parent, parenttype`; `parenttype ≠ "User"` → cảnh báo như cũ; gom theo `parent`, gọi `_role_row_adders` một lần mỗi user; người thêm = `AGENT_USER` khi `adders is None`, else `adders.get(row.name, owner của User)`; người thêm ≠ agent → bỏ qua; agent thêm → bỏ qua khi `row.role ∈ assignable_roles()` và `not is_protected_account(parent, None, AGENT_USER)`, còn lại ghi `Has Role <role> của <user>`; `assignable_roles()` tính một lần mỗi lần job; `_agent_role_drift` không đổi; `test_architecture.py`: `test_tasks_uses_policy_for_role_exception`, `test_version_read_only_in_tasks_origin_function` (chuỗi `"Version"` trong lời gọi đọc/ghi ngoài test chỉ ở `tasks._role_row_adders`; `agent/tools/**` 0 lần)
  - Expect: `test_assignable_role_row_by_agent_raises_no_alarm`, `test_banned_or_unlisted_role_row_by_agent_raises_one_alarm_naming_user`, `test_existing_user_with_unlisted_role_gets_assigned_role_without_alarm`, `test_user_created_by_tool_with_assignable_role_raises_no_alarm`, `test_role_removed_from_list_alarms_once_for_agent_row_only`, `test_agent_save_without_version_is_fail_closed`, `test_agent_save_with_version_adding_banned_role_alarms`, `test_agent_role_drift_unchanged`; hai test kiến trúc có ca âm

## Phần 10, luật kiến trúc, ADR, kiểm cuối

- [ ] T49 — Luật kiến trúc ADR-014, ADR-015 — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T45, T48
  - Criterion: AC-15 (test ràng buộc ADR-005 hiện có xanh hoặc nới đúng theo ADR mới), ADR-014/015 Ràng buộc
  - Receives: mã `registry.py`, `prompts.py`, `constants.py`, `read.py`, `install.py`, các module tool mới
  - Returns: `test_new_group_names_compared_only_in_registry` (chuỗi `"config"`, `"account"` dùng làm nhóm chỉ so sánh trong `registry.py`; `prompts.py` chỉ làm khóa dict), `test_permission_doctype_names_only_in_shared_definition` (6 tên chỉ ở `constants.py`, `read.DENIED_DOCTYPES`, JSON, test), `test_make_property_setter_never_used`, `test_agent_role_is_banned_by_constant_and_by_user_write` (nếu chưa có ở T7); `check_tools_never_bypass_permissions` giữ nguyên, không ngoại lệ, phủ module mới; mỗi luật có ca dương và ca âm
  - Expect: từng test xanh với `cmd.test_one`; chứng minh ca âm bắt được mã giả vi phạm

- [ ] T50 — Luật kiến trúc ADR-016/017/018 và kiểm ADR tồn tại — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T49
  - Criterion: AC-18 (có `ADR-014.md`, `ADR-015.md`; chứa `ADR-005`; `ADR-015.md` chứa `ADR-006`), AC-15; ADR-016/017/018 Ràng buộc
  - Receives: `docs/team/adr/ADR-014.md`, `ADR-015.md` (đã có, proposed); `confirmation.py`, `config_guard.py`, `runner.py`
  - Returns: `test_feat005_adrs_exist_and_cite_replaced_adrs`; `test_confirmation_imported_by_workflow_notification_assignment_tools`; `test_confirmation_code_prefix_only_in_confirmation_and_post_comment_guard`; `LAYER_RULES` thêm dòng `erp_ai.agent.confirmation` ↛ `erp_ai.agent.changes` (dòng `erp_ai.agent.tools` ↛ `changes` đã có từ F4-T13: chỉ kiểm nó phủ module tool mới, không thêm dòng trùng; dòng `erp_ai.agent.changes` và `erp_ai.agent.change_text` của F4-T13/F4-T44 giữ nguyên); `test_no_erp_ai_log_read_in_tools` (`agent/tools/**` 0 lần đọc `LOG_DOCTYPE`/`"ERP AI Log"` bằng `get_all`, `get_list`, `get_doc`, `db.get_value`, `db.get_all`, `qb`; chỉ `confirmation.py` đọc dòng chờ); `test_single_role_assignment_site` (nếu T21 chưa thêm); mỗi luật có ca dương và ca âm
  - Expect: từng test xanh; `cmd.test_one` trên cả file xanh

- [ ] T51 — Runner: ca còn lại của AC-10, AC-13, AC-16, AC-17, NFR-5 — files: erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T45, T24
  - Criterion: AC-10 (model khẳng định "người đã ok" → bản ghi không đổi), AC-13 (mọi tool mới có 1 dòng; mỗi lần thành công 1 dòng áp dụng), AC-16, AC-17 (khóa giả 0 lần), NFR-5, NFR-7
  - Receives: 16 tool thật đã đăng ký (T45); `FakeGateway`; helper T16, T27; gieo khóa giả vào `ERP AI Credential` theo cách NFR-5 của FEAT-001
  - Returns: chỉ test; lỗi mã sản phẩm → báo tech-lead
  - Expect: `test_each_new_tool_call_has_one_config_change_entry` (mỗi tool: số dòng `applied=1` = số lần thành công; đủ tool, DocType, bản ghi, trước, sau, người ra lệnh), `test_model_claiming_ok_without_comment_changes_nothing` (stub gọi `enable_notification` sau câu "người đã ok" → `awaiting_ok`, bản ghi tắt), `test_seeded_fake_key_absent_from_new_tool_outputs` (mỗi tool mới qua runner; chuỗi khóa 0 lần trong `tool_result`, ERP AI Log, Comment), `test_over_budget_and_no_instructor_runs_get_no_new_tools_for_every_group`

## Checkpoint cuối (tech-lead, không giao dev)

- [ ] T52 — Chạy `cmd.test`, `cmd.lint`, `cmd.migrate` lên/xuống/lên, đối soát, `diff.patch` — files: docs/team/features/FEAT-005/diff.patch, docs/team/features/FEAT-005/tasks.md — test: `cmd.test` (cả app) — depends: T1..T51
  - Criterion: mọi AC; AC-15 (`cmd.test` xanh, `ls docs/team/adr/` có ADR-014, ADR-015 tham chiếu ADR-005 và ADR-006), AC-18; STD-CI-2
  - Receives: mọi review approve
  - Returns: đầu ra thật của `cmd.test`, `cmd.lint`, `ls docs/team/adr/`; đối soát sau `cmd.migrate`: số dòng `ERP AI Log` không đổi, số dòng Custom DocPerm của `ERP AI Agent` = suy ra từ `declared_write_permissions()` ∪ dòng có sẵn trên nền (dòng Task và dòng của FEAT-006 nếu có, đếm thật trước T14; FEAT-004 không cài Custom DocPerm, quyền trên `ERP AI Change Proposal` nằm trong JSON DocType) (chạy `ensure_setup` lần hai không đổi), trường cũ của `ERP AI Setting` (gồm trường FEAT-006 và FEAT-004) trước = sau, `assignable_roles` rỗng; NFR-9 của FEAT-004 vẫn giữ: `git -C apps/<app> rev-parse HEAD` và `status --porcelain` của `frappe`, `erpnext`, `helpdesk`, `hrms` trước = sau `cmd.test` (chỉ đọc); kiểm `grep -rn "make_property_setter\|ignore_permlevel_for_fields" erp_ai/ --include=*.py` chỉ ở test; `.team/active-build` đã xóa; `diff.patch` đã ghi; ghi cho người (không phải build): mức `permission_level` trên production phải kiểm trước khi deploy (A-2)
  - Expect: tất cả xanh; lệch → không tick, đi tìm nguyên nhân
