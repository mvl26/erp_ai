Feature: FEAT-005
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-005

- Nhánh feature: `team/FEAT-005` từ **`team/FEAT-004`** (BASE nhánh nền = `team/FEAT-004`; nhánh đó đã tạo 2026-11-13 từ `team/FEAT-006` @ `f039112` và **đang build**, chưa verify). Chuỗi nền: FEAT-003 → FEAT-006 → FEAT-004 → FEAT-005. `config.base_branch` = `main` chỉ dùng lúc PR; thứ tự merge: FEAT-006, FEAT-004 trước, FEAT-005 rebase sau.
- Điều kiện bắt đầu build: FEAT-004 đã qua verify. Khi đó tech-lead tạo `team/FEAT-005` từ đầu nhánh `team/FEAT-004`, ghi mã commit thật vào dòng Tiến độ của `tasks.md`, chạy `cmd.test` (phải xanh) trước T1. Plan này lập và đối chiếu khi chưa có nhánh `team/FEAT-005`: không `git switch`, không commit, không ghi `.team/current.json`.
- Số task: 52 (51 giao dev, T52 của tech-lead); song song: 2 theo `limits.max_parallel_dev`, hoặc 5 khi team-leader giao `devs=5` (bảng "Nhóm song song 5 dev").
- Cỡ L, gate áp dụng: G5 (G3 tắt trong `.team/config.json`). Lệnh: `cmd.test_one`, `cmd.test`, `cmd.migrate`, `cmd.lint` của profile.
- Plan dựa trên `spec.md` (bản có hiệu lực ở Amendment 1), `design.md` (sửa vòng 1), ADR-014..ADR-018 và `docs/team/features/FEAT-004/{design,plan,tasks}.md`. Ký hiệu `F4-T<n>` = task của FEAT-004.
- **Đối chiếu 2026-11-13** với plan FEAT-004 lập lại (51 task: T1–T34 giữ ID, T35–T51 mới; spec Amendment 1, ADR-022: mỗi thay đổi đã áp dụng là một commit git local; nền FEAT-006). Không thêm, không bỏ task; 15 dòng task sửa chữ, liệt kê ở đầu `tasks.md`. Đối chiếu với `tasks.md`/`design.md` của FEAT-004, chưa với mã (FEAT-004 chưa có commit mã): khi tạo nhánh phải so lại chữ ký thật.

## Ràng buộc chung (chép từ design/ADR; mọi task kế thừa)
- Tên chính xác (không đổi): 16 tool (14 nhóm `config`: `add_custom_field`, `set_field_property`, `create_holiday_list`, `add_holidays`, `create_workflow`, `update_workflow`, `activate_workflow`, `create_notification`, `update_notification`, `enable_notification`, `create_assignment_rule`, `update_assignment_rule`, `enable_assignment_rule`, `set_system_settings`; 2 nhóm `account`: `create_user`, `add_user_roles`); nhóm tool `config`, `account`; trường `assignable_roles` (Small Text, trên `ERP AI Setting`, section `section_accounts`); `entry_type = config_change`; `stop_reason ∈ pending|applied|refused|awaiting_ok|crashed`; `CODE_PREFIX = "ERPAI-OK-"`; savepoint cục bộ `erp_ai_config_write`, `erp_ai_account_write`.
- Chữ ký (design 3.2, 3.5–3.7, bản sửa vòng 1) giữ nguyên: `registry.{ToolSpec(writes, write_permlevels, commits), granted_groups, call_log_doctype, declared_write_permissions}`; `policy.{HARD_BANNED_ROLES, PRIVILEGED_DOCTYPES, banned_roles, assignable_roles, is_protected_account}`; `confirmation.{is_running, needs_confirmation, canonical_json, fingerprint, find_notice, is_confirmed, pending_payload, confirmed_request, notice_html}`; `config_guard.{PERMISSION_ATTRIBUTES, DISPLAY_PROPERTIES, CUSTOM_FIELD_TYPES, CUSTOM_FIELD_FORCED, forbidden_targets, check_target, check_field, request_confirmation, write_once}`; `run_log.update_entry`; `write_ticket.add_ticket_comment`; `tasks._role_row_adders`; `install._ensure_tool_permissions`.
- Câu lý do từ chối (design 3.3, 3.4) là hợp đồng với test: chép nguyên, không diễn đạt lại. Mọi giá trị model đưa nhắc lại trong `reason` cắt 80 ký tự; `reason` ≤ 200 ký tự.
- Không `ignore_permissions`, `ignore_permlevel_for_fields`, `make_property_setter`, `db.set_value`, SQL ghi, `get_all` trong `agent/tools/**`; tool không đọc ERP AI Log (chỉ `confirmation.py`); chỉ runner tạo dòng ERP AI Log; chỉ `account._save_user_with_roles` và `install.py` gán role; chỉ `tasks._role_row_adders` đọc `Version`.
- Không khóa schema nào chứa `confirm`, `approved`, `ok_`; không khóa thuộc `PERMISSION_ATTRIBUTES` (gồm `options`), không `doctype_or_field`.
- **Trường mới phải có `description` (FEAT-003, `erp_ai/tests/test_doctype_descriptions.py`):** `ERP AI Setting.assignable_roles` (T3): tiếng Việt, ≤ 400 ký tự, không `sk-`, không `miyano`, không giá trị đang lưu; `field_count` +1 và `section_count` +1 so với số thật sau FEAT-004 (dự kiến 26 → 27 và 7 → 8: nền FEAT-006 là 24 trường, 6 section, F4-T3 thêm 2 và 1; đọc `DOCTYPE_CONFIG` lúc build). `ERP AI Log` không thêm trường; giá trị `config_change` làm mô tả của `entry_type` phải đổi (T4), `field_count` giữ nguyên (dự kiến 38: nền FEAT-006 35, F4-T4 thêm 3).
- **Dọn test (design `design.md:431,475`):** test có tool tự commit (Custom Field, Workflow) không dựa `frappe.db.rollback`: xóa bản ghi theo thứ tự ngược dưới `Administrator` bằng helper T16 (`register_cleanup`), có commit, tên `erpai_test_*`/`ERPAI-TEST-*`.
- Thêm file/đường dẫn mới chỉ dưới `erp_ai` (19 đường dẫn ở design mục 7 + `test_confirmation.py`/`test_prompts.py` đã nằm trong số đó; 0 trong `protected_paths`). Test cũ không sửa assertion (STD-TEST-5); chỉ các chỗ design liệt kê (`test_no_write_tool_accepts_doctype_or_field` nới đúng nhóm `config`).
- Task nào sửa `*.json` của DocType: chạy `cmd.migrate` trên `miyano` trước `cmd.test_one`, dán đầu ra. Mọi task: test đỏ trước (STD-TEST-1), chỉ sửa trong `files:`, không skip/xfail. Test đặc trưng (T1) chứng minh bắt được lỗi bằng cách đổi 1 byte hằng.
- Luật kiến trúc (`test_architecture.py`): task nào làm một luật HIỆN CÓ đỏ thì sửa luật đó theo đúng ADR ngay trong chính task (các task có `test_architecture.py` ở `files:`: T7, T8, T15, T21, T23, T48; luật MỚI ở T49, T50). Những task này chạy theo thứ tự số; thứ tự đó nay nằm trong `depends:` (T7 → T8 → T15 → T21 → T23 → T48 → T49 → T50). Chuỗi `test_architecture.py` của FEAT-004 (F4-T37 → T5 → T11 → T43 → T13 → T15 → T25 → T31 → T32 → T44) đã xong trước T7.
- Git (ADR-022 của FEAT-004): FEAT-005 không dựng lệnh git, không gọi `subprocess`, không sửa `source.py`, `changes/**`, `change_text.py`, `change_guard.py`, `GitSandbox`. `cmd.test` của FEAT-005 chạy cả test git của FEAT-004 trong `GitSandbox`; HEAD và `status` của 4 repo lõi thật phải không đổi (T52).

## Hợp nhất với FEAT-004 (design mục 7 "Phối hợp"; điều chỉnh so với chữ design)
Build chạy trên `team/FEAT-004` đã verify, nên mọi chỗ chung dưới đây đọc từ mã đã gộp và chỉ THÊM. Design FEAT-005 viết khi FEAT-004 chưa có mã; các lệch đã biết (bảng sửa 2026-11-13 theo `FEAT-004/tasks.md` mới và `FEAT-004/design.md` mục "Chỗ đụng FEAT-005"):

| Chỗ chung | FEAT-004 (đã có lúc build; nền FEAT-006) | FEAT-005 thêm | Task |
|---|---|---|---|
| `registry.py` bảng cấp | một bảng điều kiện mỗi nhóm; `_granted_specs`/`get_tool_schemas(level, has_instructor, change_enabled)` bắt buộc; `grants_change_tools` (F4-T23); không đổi ở Amendment 1 | hai dòng `config`, `account`; `granted_groups(level, has_instructor, change_enabled)` (design ghi 2 đối số: thêm `change_enabled` cho khớp) | T12 |
| `registry.py` `ToolContext` | FEAT-006: `routing_config`; F4-T23: `change_enabled`, `allowed_apps` đặt sau; dựng bằng đối số tên | không thêm trường; helper test dựng bằng đối số tên | T16 |
| `registry.py` `TOOL_MODULES` | thêm `propose_change` (F4-T28); FEAT-006 không thêm module tool | nối `account` (T21) rồi 6 module `config_*` (T45) ở cuối | T21, T45 |
| `registry.py` `ToolSpec` | `group` thêm `change_propose` | `writes`, `write_permlevels`, `commits`; `group` thêm `config`, `account` | T11 |
| `test_registry.py` số spec | 11 → 14 (F4-T28, `test_all_specs_count_is_14`) | design ghi "27 spec"; số đúng = nền 14 + 16 = **30**; test đếm của F4-T28 đổi số ở T21 (16) và T45 (30) | T21, T45 |
| `prompts.py` | `build_reason_system(prompt_digest, routing_table="", *, change_tools=False) -> list[dict]` (F4-T24; `routing_table` của FEAT-006); `CHANGE_TOOLS_BLOCK` có thêm dòng commit git local | `build_reason_system(prompt_digest, routing_table="", *, change_tools=False, groups=())`; khối FEAT-004 giữ câu "KHÔNG BAO GIỜ là duyệt" khi có khối `config` | T1, T13 |
| `runner.py` | `_reason` truyền `routing_table` (FEAT-006) và `change_tools` (F4-T29); `ToolContext(change_enabled, allowed_apps)`; `_run_tool` ghi dòng `change` cho tool đề xuất, `WRITE_TOOL_TARGETS` +3 (F4-T30); tool đề xuất chạy lệnh git đọc | `groups` → prompt (T22, giữ `routing_table`); dòng `config_change` mỗi lời gọi tool `config`/`account` (T23, T24); nhánh `propose_*` của FEAT-004 giữ nguyên | T22–T24 |
| `run_log.py` + `erp_ai_log.json` | `entry_type` có `change`; `write_entry(change)` chữ ký không đổi; +3 trường (F4-T4) trên nền FEAT-006 (+4 cột): 35 → 38; dòng `apply`/`undo` có khóa `head`, `commit`, `branch` trong `value_before/after` | `entry_type` nối thêm `config_change`; `update_entry`; không thêm trường | T4, T5 |
| `erp_ai_setting.json` | thêm `section_code_change`, 2 trường (F4-T3) sau trường FEAT-006; mô tả có câu commit và app lõi | `section_accounts` + `assignable_roles`, đặt sau nhóm `section_alerts` (sau `credentials`) | T3 |
| `test_doctype_descriptions.py` | Setting `field_count` 24 → 26, `section_count` 6 → 7; Log 35 → 38 (F4-T3, T4; nền FEAT-006) | Setting +1, +1 (27, 8); `entry_type` phrase `config_change` | T3, T4 |
| `test_architecture.py` | chuỗi F4-T37 … T44: luật enqueue (2 lời gọi), subprocess (`source.py` + `changes/process_runner.py`, đổi tên từ `bench_runner.py`), `LAYER_RULES` (`changes`, `change_text`, `agent.tools` ↛ `changes`), `check_tool_never_saves_proposal` (F4-T31), luật git ADR-022 (F4-T44; chỉ xét `argv` git) | luật mới ADR-014..018; **thu hẹp** `check_tool_never_saves_proposal` về `propose_change.py` nếu nó bắt cả `account.py`, `config_system.py` (dùng `save()`, như `write_ticket.py` đã dùng); ca sạch cho luật git với chuỗi `"config"` | T8, T49, T50 |
| `test_utils.py` | FEAT-006: `make_routing_rules`, `make_sla`, `make_team`…; FEAT-004: helper `apps/` tạm (F4-T7), `GitSandbox` (F4-T36, T51), `RealCoreReposUntouchedMixin` (F4-T51), đề xuất mẫu (F4-T12) | user agent thử, `call_registered`, `register_cleanup`, gieo comment/dòng chờ; thêm cạnh, không sửa helper cũ | T16, T27 |
| `policy.py` | FEAT-006: `auto_assign_enabled`, `is_excluded_team`; F4-T5: `ChangeSettings`, `validate_change_apps`, `POLICY_FIELDS` +2 (không đổi ở Amendment 1) | `HARD_BANNED_ROLES`, `banned_roles`, `assignable_roles`, `is_protected_account` | T7, T9 |
| `constants.py` | F4-T2: hằng `CHANGE_*`, `CORE_APPS`, `BOT_GIT_NAME`, `BOT_GIT_EMAIL` | `PERMISSION_DOCTYPES` và 3 tên DocType; không trùng tên | T2 |
| `install.py`, `write_ticket.py`, `test_write_ticket.py` | FEAT-004 không chạm; FEAT-006 đã sửa | `_ensure_tool_permissions` (T14, T15); `add_ticket_comment` (T30) | T14, T15, T30 |
| Mốc AC-1 "như nền" | nền = `team/FEAT-004` ở công tắc tắt: 11 tool; công tắc bật + `L3` + người ra lệnh: 14 tool (FEAT-006 không thêm `ToolSpec`) | chụp hằng tên tool và sha256 prompt (4 biến thể `routing_table` × `change_tools`) TRƯỚC mọi sửa | T1 |

Không đụng FEAT-005: `run_change`, `enqueue_change_job`, `approve/reject/undo`, `transitions.finish(fields=)`, `STATE_FIELDS`, `process_runner`, `source.py` git, `change_text`, `change_guard`, DocType `ERP AI Change Proposal` (FEAT-005 không gọi, không sửa).

Nếu chữ ký thật của FEAT-004 khác chữ trong bảng → `DESIGN_CONFLICT` (dev dừng, tech-lead báo team-leader), không tự đổi.

## Thứ tự
1. T1 chụp mốc nền (prompt, tên tool) trước khi sửa bất cứ mã nào: AC-1/NFR-6 đo theo mốc này.
2. Nền dữ liệu và chính sách (T2–T9): hằng DocType phân quyền, trường `assignable_roles`, loại log `config_change`, `update_entry`, `banned_roles`/`assignable_roles`/`is_protected_account`, kiểm phạm vi luật FEAT-004 (T8).
3. Registry và prompt (T10–T13), cài quyền Custom DocPerm cho `ERP AI Agent` suy ra từ khai báo (T14, T15), helper test (T16).
4. **Walking skeleton S1 (T17–T25)**: tài khoản (`create_user`, `add_user_roles`) đăng ký vào registry, runner cấp nhóm, một dòng `config_change` mỗi lời gọi, chạy bằng Cổng model giả. Đây là đường rủi ro nhất (tự nâng quyền, NFR-1). **Không task nhánh tool cấu hình (T35–T46) bắt đầu trước khi review T25 là approve.**
5. Song song với S1 (không chung file): xác nhận "ok" (T26–T30), bộ chặn đích (T31–T34), cảnh báo hằng ngày (T47, T48).
6. Tool cấu hình (T35–T44), đăng ký (T45), kiểm đích cấm toàn bộ (T46).
7. Luật kiến trúc (T49, T50), ca runner còn lại (T51), checkpoint tech-lead (T52).

## Nhóm song song (≤ 2 dev, không chung file)
| Lượt | Cùng chạy | Ghi chú |
|---|---|---|
| 1 | T1 ∥ T2 | |
| 2 | T3 ∥ T7 | |
| 3 | T4 ∥ T8 | `test_doctype_descriptions.py` T3 → T4; `test_architecture.py` T7 → T8 |
| 4 | T5 ∥ T9 | |
| 5 | T6 ∥ T10 | |
| 6 | T11 ∥ T13 | |
| 7 | T12 ∥ T14 | |
| 8 | T15 ∥ T26 | |
| 9 | T16 ∥ T31 | |
| 10 | T17 ∥ T27 | |
| 11 | T18 ∥ T28 | |
| 12 | T19 ∥ T29 | |
| 13 | T20 ∥ T30 | |
| 14 | T21 ∥ T32 | |
| 15 | T22 ∥ T33 | |
| 16 | T23 ∥ T34 | |
| 17 | T24 ∥ T47 | |
| 18 | T25 ∥ T48 | hết lượt: checkpoint S1 (review T25 approve, `cmd.test` xanh) |
| 19 | T35 ∥ T38 | chỉ sau review T25 approve |
| 20 | T36 ∥ T39 | |
| 21 | T37 ∥ T40 | |
| 22 | T41 ∥ T43 | |
| 23 | T42 ∥ T44 | |
| 24 | T45 | |
| 25 | T46 ∥ T49 | |
| 26 | T50 ∥ T51 | |
| 27 | T52 | tech-lead |
Lịch là gợi ý; ràng buộc thật là cột `depends:` và bảng một chủ. Hai task chung file không bao giờ chạy cùng lúc.

## Nhóm song song 5 dev (khi team-leader giao `devs=5`; file rời nhau trong mỗi lượt)
| Lượt | Cùng chạy | File của từng task (rời nhau) | Ghi chú |
|---|---|---|---|
| 1 | T1 ∥ T2 ∥ T3 ∥ T26 ∥ T31 | test_prompts + test_registry; constants + tasks + test_tasks; setting.json + test_doctype_descriptions; confirmation; config_guard | 5 dev |
| 2 | T4 ∥ T6 ∥ T7 ∥ T10 ∥ T13 | log.json + test_doctype_descriptions; test_erp_ai_setting; policy + test_architecture; registry; prompts | 5 dev; T30, T47 cũng sẵn sàng, chờ chỗ |
| 3 | T5 ∥ T8 ∥ T9 ∥ T11 ∥ T30 | run_log; test_architecture; policy; registry; write_ticket | 5 dev |
| 4 | T12 ∥ T14 ∥ T32 ∥ T47 | registry; install + test_install; config_guard; tasks + test_tasks | 4 dev |
| 5 | T15 ∥ T33 | install + test_install + test_architecture; config_guard | chuỗi S1 bắt đầu hẹp lại |
| 6 | T16 | test_utils + test_install | |
| 7 | T17 ∥ T27 | account; test_utils + test_confirmation | |
| 8 | T18 ∥ T28 | account; confirmation | |
| 9 | T19 ∥ T29 | account; confirmation | |
| 10 | T20 ∥ T34 | account; config_guard | |
| 11 | T21 | registry + test_architecture | |
| 12 | T22 | runner | |
| 13 | T23 | runner + test_architecture | |
| 14 | T24 ∥ T48 | runner; tasks + test_tasks + test_architecture | |
| 15 | T25 | test_agent_runner | checkpoint S1: review T25 approve, `cmd.test` xanh |
| 16 | T35 ∥ T38 ∥ T39 ∥ T41 ∥ T43 | config_fields; config_holidays; config_workflow; config_notification; config_assignment_rule | 5 dev; T44 sẵn sàng, chờ chỗ |
| 17 | T36 ∥ T40 ∥ T42 ∥ T44 | config_fields; config_workflow; config_notification; config_system | 4 dev |
| 18 | T37 | config_fields | |
| 19 | T45 | registry | |
| 20 | T46 ∥ T49 ∥ T51 | test_config_guard; test_architecture; test_agent_runner | 3 dev |
| 21 | T50 | test_architecture | |
| 22 | T52 | tech-lead | |

22 lượt thay 27. Rộng 5 chỉ có ở lượt 1–3 và 16; S1 (T14 → T15 → T16 → T17 … T25) là chuỗi một file nên không rộng hơn 2. Điều phối theo vòng: task nào đủ `depends:` và không chung file với task đang chạy thì gọi ngay, không chờ hết lượt; gộp từng task một, `cmd.test` sau mỗi lần gộp. `test.shared_state` (một site `miyano`): khi ≥ 2 dev đang chạy, dev chỉ chạy `cmd.test_one`; hai task cùng cần `cmd.migrate` (T3, T4) không chạy cùng lúc (đã là chuỗi). Test tool tự commit (T35, T39) chạy cùng lượt 16: mỗi test dùng tên bản ghi riêng `erpai_test_<task>_*` để không đụng nhau trên cùng site.

## Bảng mỗi file một chủ
| File | Chủ | Task khác chạm | Thứ tự | FEAT-004 đã chạm |
|---|---|---|---|---|
| erp_ai/constants.py, erp_ai/tests/test_tasks.py | T2 | T47, T48 (chỉ test_tasks.py) | T2 → T47 → T48 | F4-T2; F4-T4 (test_tasks) |
| erp_ai/tasks.py | T2 | T47, T48 | T2 → T47 → T48 | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | T3 | — | — | F4-T3 |
| erp_ai/tests/test_doctype_descriptions.py | T3 | T4 | T3 → T4 | F4-T3, F4-T4 |
| erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json | T4 | — | — | F4-T4 |
| erp_ai/agent/run_log.py, test_run_log.py | T5 | — | — | F4-T4 |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py | T6 | — | — | F4-T6 |
| erp_ai/agent/policy.py, test_policy.py | T7 | T9 | T7 → T9 | F4-T5 |
| erp_ai/tests/test_architecture.py | T7 | T8, T15, T21, T23, T48, T49, T50 | theo số (đã nằm trong `depends:`) | F4-T37, T5, T11, T43, T13, T15, T25, T31, T32, T44 (chuỗi của FEAT-004); FEAT-006 |
| erp_ai/agent/tools/registry.py | T10 | T11, T12, T21, T45 | T10 → T11 → T12 → T21 → T45 | F4-T23, F4-T28 |
| erp_ai/agent/tools/test_registry.py | T1 | T10, T11, T12, T21, T45 | T1 → T10 → T11 → T12 → T21 → T45 | F4-T23, F4-T28 |
| erp_ai/agent/prompts.py | T13 | — | — | F4-T24 |
| erp_ai/agent/test_prompts.py | T1 | T13 | T1 → T13 | — (file mới) |
| erp_ai/install.py | T14 | T15 | T14 → T15 | — (FEAT-006 đã sửa) |
| erp_ai/tests/test_install.py | T14 | T15, T16 | T14 → T15 → T16 | F4-T33; FEAT-006 |
| erp_ai/test_utils.py | T16 | T27 | T16 → T27 | F4-T7, F4-T36, F4-T51, F4-T12; FEAT-006 |
| erp_ai/agent/tools/account.py, test_account.py | T17 | T18, T19, T20 | T17 → T18 → T19 → T20 | — |
| erp_ai/agent/runner.py, test_agent_runner.py | T22 | T23, T24, T25 (chỉ test), T51 (chỉ test) | T22 → T23 → T24 → T25 → T51 | F4-T23, F4-T29, F4-T30 |
| erp_ai/agent/confirmation.py, test_confirmation.py | T26 | T27 (test), T28, T29 | T26 → T27 → T28 → T29 | — |
| erp_ai/agent/tools/write_ticket.py, test_write_ticket.py | T30 | — | — | — (FEAT-006 đã sửa) |
| erp_ai/agent/tools/config_guard.py | T31 | T32, T33, T34 | T31 → T32 → T33 → T34 | — |
| erp_ai/agent/tools/test_config_guard.py | T31 | T32, T33, T34, T46 | T31 → T32 → T33 → T34 → T46 | — |
| erp_ai/agent/tools/config_fields.py, test_config_fields.py | T35 | T36, T37 | T35 → T36 → T37 | — |
| erp_ai/agent/tools/config_holidays.py, test_config_holidays.py | T38 | — | — | — |
| erp_ai/agent/tools/config_workflow.py, test_config_workflow.py | T39 | T40 | T39 → T40 | — |
| erp_ai/agent/tools/config_notification.py, test_config_notification.py | T41 | T42 | T41 → T42 | — |
| erp_ai/agent/tools/config_assignment_rule.py, test_config_assignment_rule.py | T43 | — | — | — |
| erp_ai/agent/tools/config_system.py, test_config_system.py | T44 | — | — | — |
| docs/team/features/FEAT-005/{diff.patch, tasks.md} | T52 | — | — | — |

Touchpoint của design mục 7 → task (đủ 41 dòng, không dòng trống): constants T2; policy T7/T9; confirmation T26/T28/T29; prompts T13; run_log T5; runner T22–T24; registry T10–T12/T21/T45; write_ticket T30; config_guard T31–T34; config_fields T35–T37; config_holidays T38; config_workflow T39/T40; config_notification T41/T42; config_assignment_rule T43; config_system T44; account T17–T20; tasks.py T2/T47/T48; install.py T14/T15; erp_ai_setting.json T3; erp_ai_log.json T4; test_utils T16/T27; test_confirmation T26–T29; test_prompts T1/T13; test_policy T7/T9; test_run_log T5; test_agent_runner T22–T25/T51; test_registry T1/T10–T12/T21/T45; test_write_ticket T30; test_config_guard T31–T34/T46; test_config_fields T35–T37; test_config_holidays T38; test_config_workflow T39/T40; test_config_notification T41/T42; test_config_assignment_rule T43; test_config_system T44; test_account T17–T20; test_erp_ai_setting T6; test_tasks T2/T47/T48; test_install T14–T16; test_architecture T7/T8/T15/T21/T23/T48–T50. Ngoài bảng design (file có sẵn, nằm dưới `erp_ai`, không protected): `erp_ai/tests/test_doctype_descriptions.py` (T3, T4: luật mô tả FEAT-003 bắt buộc).

## AC / NFR → task
| Mã | Task |
|---|---|
| AC-1 | T1 (mốc nền), T12 (ma trận cấp), T13 (prompt trùng byte), T22 (runner, vượt ngân sách), T51 |
| AC-2 | T12, T21 (account thật), T45 (config thật) |
| AC-3 | T17, T25 |
| AC-4 | T17, T18 |
| AC-5 | T19, T20 |
| AC-6 | T6 (chỉ System Manager sửa), T9 (rỗng/trùng/thiếu), T15 (rỗng sau cài), T18 (rỗng: tạo user không role) |
| AC-7 | T31 (giao rỗng), T35, T36 |
| AC-8 | T37 |
| AC-9 | T38 |
| AC-10 | T26, T28, T29, T30, T34, T39, T40, T41, T42, T43, T51 |
| AC-11 | T32, T41 (người nhận), T46 (11 tool × DocType cấm) |
| AC-12 | T44 |
| AC-13 | T4, T5, T11, T23, T24, T51 |
| AC-14 | T47, T48 |
| AC-15 | T8, T14, T15, T16, T46, T49, T50, T52 |
| AC-16 | T25, T30, T51 |
| AC-17 | T51 |
| AC-18 | T13, T50 (`ADR-014.md`, `ADR-015.md` tồn tại và tham chiếu ADR-005, ADR-006), T52 |
| NFR-1 | T17, T18, T19, T25 |
| NFR-2 | T35, T36, T37, T44, T46 |
| NFR-3 | T23, T25, T51 |
| NFR-4 | T26, T28, T29, T34, T39–T43 |
| NFR-5 | T51 (khóa giả); STD: không mật khẩu/token trong tool (T17) |
| NFR-6 | T1, T12, T13, T22 |
| NFR-7 | T24, T51 |
18/18 AC, 7/7 NFR. Mục ngoài AC: mô tả field của `assignable_roles` (T3), mô tả `entry_type` (T4), thu hẹp luật FEAT-004 (T8), `README`/tài liệu người dùng và As-Built thuộc `/team:asbuilt` sau G4.

Thứ tự bỏ trước nếu thiếu thời gian (spec): AC-12 → bỏ T44 + một dòng `TOOL_MODULES` ở T45 (quyền System Settings tự không được cài, ADR-015 QĐ 2); rồi Assignment Rule → T43; Notification → T41, T42; Workflow → T39, T40. Mỗi lần bỏ sửa số tool ở T45, T46, T51. AC-1..AC-6 và AC-13..AC-18 không bỏ.

## Preflight (cặp task chung file hoặc giao diện)
| Cặp | Chung | Xử lý |
|---|---|---|
| T3 ↔ T4 | `test_doctype_descriptions.py` | T3 → T4 |
| T7 ↔ T8 ↔ T15 ↔ T21 ↔ T23 ↔ T48 ↔ T49 ↔ T50 | `test_architecture.py` | chạy theo số, đã thành `depends:` (T15 thêm T8, T48 thêm T23; các mắt khác có sẵn qua phụ thuộc bắc cầu); chỉ sửa luật hiện có khi mã của chính task làm nó đỏ; không nới luật git ADR-022 |
| T1 ↔ T13 ↔ T22 | `build_reason_system` | một chữ ký `(prompt_digest, routing_table="", *, change_tools=False, groups=())` ở cả ba task |
| T7 ↔ T9 | `policy.py` | T7 làm `banned_roles`, T9 làm `assignable_roles`, `is_protected_account` |
| T1 ↔ T10..T12, T21, T45 | `test_registry.py` | T1 chụp mốc trước; sau đó chuỗi cố định |
| T11 ↔ T32 | `declared_write_permissions` | T32 `forbidden_targets` đứng sau T11 |
| T12 ↔ T21 | `registry.py` | T12 làm bảng cấp, T21 chỉ nối module |
| T14 ↔ T15 ↔ T16 | `install.py`, `test_install.py` | chuỗi; T16 dùng `_ensure_tool_permissions` của T14 |
| T16 ↔ T27 | `test_utils.py` | T16 → T27 |
| T17 → T20 | `account.py` | chuỗi; mỗi task thêm nhánh, không đổi nhánh cũ |
| T17 ↔ T33 | `write_once` chưa có khi làm tài khoản | T17/T19 tự bắt `frappe.ValidationError` bằng savepoint cục bộ (D-17); không import `config_guard` |
| T22 ↔ T23 ↔ T24 ↔ T25 ↔ T51 | `runner.py`, `test_agent_runner.py` | chuỗi |
| T26 ↔ T30 | `CODE_PREFIX` | T30 sau T26 (tool import hằng từ `confirmation`) |
| T26..T29 ↔ T34 | `request_confirmation` | T34 sau T29 và T30 |
| T35 → T37; T39 → T40; T41 → T42 | module tool | chuỗi |
| T45 ↔ T46 | `registry.py` / test | T45 → T46 (T46 chỉ chạm `test_config_guard.py`) |
| T47 ↔ T48 | `tasks.py` | chuỗi |
Không có task tự mâu thuẫn. Task cần chữ ký chưa có đều đứng sau task tạo ra nó. Nếu chữ ký trong design không khớp mã thật (nhất là chỗ chung với FEAT-004 ở bảng "Hợp nhất") → `DESIGN_CONFLICT`.

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Nhánh nền `team/FEAT-004` đang build, có thể đổi trước hoặc sau verify | `git log` khác lúc ghi BASE; xung đột ở `registry.py`, `prompts.py`, `runner.py`, `erp_ai_log.json`, `erp_ai_setting.json`, `test_architecture.py` | build chỉ sau FEAT-004 verify; tạo `team/FEAT-005` từ đầu nhánh thật; chạy `cmd.test` xanh trước T1; mốc AC-1 chụp ở T1 từ chính nhánh đó |
| Chữ ký FEAT-004 thật khác bảng "Hợp nhất" (đối chiếu 2026-11-13 dựa trên tài liệu, FEAT-004 chưa có mã; FEAT-004 còn có thể rework hoặc gặp `DESIGN_CONFLICT` ở D-18) | `TypeError`, test FEAT-004 đỏ; `FEAT-004/tasks.md` đổi sau 2026-11-13 | trước T1 tech-lead so lại 6 chữ ký: `build_reason_system`, `get_tool_schemas`, `ToolContext`, `write_entry`, `POLICY_FIELDS`, `DOCTYPE_CONFIG`; lệch → `DESIGN_CONFLICT`, không tự đổi; cập nhật plan bằng `/team:plan --insert` |
| `design.md` FEAT-005 còn chữ cũ: `granted_groups` 2 đối số (dòng 125), `build_reason_system(prompt_digest, groups=())` (dòng 249, 293), "27 tool/spec" (dòng 433, 482) | dev đọc design thay vì task | task và bảng "Hợp nhất" là chuẩn khi lệch design; cần designer ghi "Sửa vòng 2" vào design (đã báo team-leader, plan không tự sửa design) |
| Chạy 5 dev trên một site `miyano` | test của hai task đụng bản ghi chung; `cmd.migrate` chồng nhau | dev đang song song chỉ chạy `cmd.test_one`; `cmd.test` sau mỗi lần gộp; T3 → T4 là chuỗi; tên bản ghi thử có mã task |
| Luật `check_tool_never_saves_proposal` của FEAT-004 đỏ với tool tài khoản/hệ thống | `test_architecture` đỏ ở T17..T44 | T8 kiểm phạm vi và thu hẹp trước tool đầu tiên dùng `save()` |
| Tool tự lưu (Custom Field, Workflow) commit DDL: test để lại bản ghi/cột trên `miyano` | bản ghi `erpai_test_*` còn sau test; migrate lệch | `register_cleanup` (T16); mỗi test tool tự commit dọn rõ ràng; kiểm `frappe.get_all` sau suite ở T52 |
| Workflow đụng DocType đang có bản ghi (cột `workflow_state` bị điền) | cột ẩn mới trên DocType thử | dùng DocType thử ít bản ghi; dọn Custom Field `workflow_state` ở cleanup; ghi vào tool_result (G-1) |
| Cảnh báo hằng ngày fail-closed làm lộ nhiều cảnh báo | AC-14 đỏ ở ca user có sẵn | đây là hành vi đúng (D-14); đối chiếu 5 ca ADR-016 ở T48; sai thì chỉ đổi `_role_row_adders` |
| Site `miyano` duy nhất: migrate JSON và Custom DocPerm ảnh hưởng phiên khác | test lạ ở phiên song song | build chỉ sau FEAT-003, FEAT-004 verify; `cmd.migrate` chỉ ở T3, T4 |
| Mức `L2`/`L3` đang bật trên production | tool ghi có hiệu lực ngay khi deploy (A-2) | việc của người sau G4: kiểm mức trước deploy; ghi lại ở T52; không deploy prod |
| Test AC-1 đúng nhưng mốc chụp sai | hằng không trùng đầu ra thật | T1 dán đầu ra thật và chứng minh bắt lỗi bằng đổi 1 byte |
| Thiếu thời gian/ngân sách agent | quá `max_agents_per_feature` (L = 10) | báo team-leader; thứ tự bỏ trước ở trên; hoặc tách đợt 1 (T1–T25, T26–T34, T35–T38, T47–T51) và đợt 2 (Workflow, Notification, Assignment Rule, System Settings) theo đề xuất của spec |

## Walking skeleton (cỡ L)
S1 = T17 → T25: `create_user` và `add_user_roles` (nhóm `account`) được khai `writes=("User",)`, được đăng ký vào registry (T21), được cấp ở `L3` khi có người ra lệnh (T12, T22), có Custom DocPerm cài từ khai báo (T14, T15), chạy dưới tài khoản agent chỉ có {`ERP AI Agent`, `Agent`}, qua runner có đúng một dòng `config_change` mỗi lời gọi (T23, T24), đọc lại role sau lưu, và bị chặn khi phiếu của người không thẩm quyền chèn lệnh (T25). Cổng model giả, không gọi mạng. Đây là đường rủi ro nhất (NFR-1: 0 lần gán role cấm cứng), nên đi trước các tool cấu hình. Sau review T25 approve mới mở nhánh tool cấu hình.

## Checkpoint (`cmd.test` xanh trên `team/FEAT-005`, dán đầu ra)
1. Trước T1: `cmd.test` xanh trên `team/FEAT-005` vừa tạo từ `team/FEAT-004`; ghi mã commit nền vào `tasks.md`.
2. Sau T6: `cmd.migrate` thành công; `cmd.test` xanh; trường cũ của `ERP AI Setting` trước = sau; số dòng `ERP AI Log` không đổi.
3. Sau T16: `cmd.test` xanh; tài khoản agent thử có đúng {`ERP AI Agent`, `Agent`}.
4. Sau T25 (S1): review approve; `cmd.test` xanh.
5. Sau T34, T48: bộ chặn đích và cảnh báo xong; `cmd.test` xanh.
6. Sau T46, T50: `cmd.test`, `cmd.lint` sạch; `ls docs/team/adr/` có ADR-014, ADR-015 tham chiếu ADR-005 (và ADR-006); `cmd.migrate` lên/xuống/lên đối soát (qa chạy lại ở verify).
7. Hết build: `diff.patch`; xóa `.team/active-build`; báo roles đã gọi.
