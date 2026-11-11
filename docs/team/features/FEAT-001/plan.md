Feature: FEAT-001
Stage: plan
Author-agent: tech-lead
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-001

- Nhánh feature: `team/FEAT-001` từ `develop` (repo không có `main`; `.team/config.json` vẫn ghi `base_branch = main` → xem mục Việc cần người làm)
- Số task: 40; song song tối đa: 2 (`limits.max_parallel_dev`)
- Đầu vào: `spec.md` (AC-1..AC-20), `design.md` (65 touchpoint), ADR-001..006. G3 tắt trong `.team/config.json`, nhưng plan vẫn chờ team-leader cho phép bắt đầu build.

## Thứ tự

1. **T1 walking skeleton** (không task nào khởi động trước khi review T1 `approve`).
2. **Nhóm thuần T2–T7** (không DocType, không migrate): hàng đợi chống trùng, prompt + phân loại, bảng cầu dao, số liệu eval, tool mã nguồn. Làm trước để lộ sớm rủi ro an toàn (đường dẫn, git, khóa) và để chuỗi migrate phía sau không bị chặn.
3. **Chuỗi migrate T8–T13, tuần tự:** Credential → Setting → Log → cài đặt (role + tài khoản + mặc định) → custom field + template → quyền Task. Mỗi task chạy `bench migrate` trên site `miyano`, nên không chạy song song với task nào khác.
4. **Cổng model T14–T19:** cảnh báo → chi phí/client → chọn khóa → `call_model` → dò khóa → chứng minh không rò khóa. Khóa API là rủi ro lớn nhất (NFR-5) nên đi trước runner.
5. **Lõi agent T20–T27:** chính sách, thẩm quyền, nhật ký, registry + 10 tool (đọc, mã nguồn, ghi).
6. **Runner T28–T30:** chốt tài khoản/điều kiện dừng/L0 → L1 ghi phân loại → vòng lập luận.
7. **Cửa vào và job nền T31–T35**, **nút Kiểm tra khóa T36**, **eval T37–T38**, **báo cáo T39**.
8. **T40** kiểm kiến trúc + CI.

Cắt theo thứ tự bỏ trước của spec, nếu thiếu thời gian: (1) T39 (AC-12), (2) T36, (3) `create_task` trong T26, (4) chuyển khóa trong T17. Không cắt: T1–T7, T9–T13, T17, T19–T22, T24–T25, T28–T31.

## Nhóm song song

Chỉ ghép task **không migrate**, **không chung file** và **không chung `test_utils.py`/`hooks.py`**. Mọi task còn lại chạy một mình.

| Nhóm | Task | Lý do an toàn |
|---|---|---|
| P1 | T2, T3 | `queue.py` vs `prompts/classification.py` |
| P2 | T4, T5 | `breaker.py` vs `eval/run_eval.py` |
| P3 | T14, T20 | `alerts.py` vs `policy.py` (sau T13) |
| P4 | T15, T21 | `gateway/{cost,client}.py`, `pyproject.toml` vs `authority.py` |
| P5 | T24, T25 | `tools/read.py` vs `tools/write_ticket.py` |
| P6 | T28, T31 | `runner.py` vs `handlers.py` |
| P7 | T36, T37 | `erp_ai_setting.py/js` vs `eval/export_tickets.py` |

Tuần tự (một mình): T1, T6→T7, T8→T13, T16→T19, T22, T23, T26→T27, T29→T30, T32→T35, T38, T39, T40.

## Môi trường chạy test (người đã chốt, lúc gọi plan)

- Test chạy qua bench trên site `miyano`. Dev trong worktree phải dùng `cmd.test_one` dạng:
  `R=$(git rev-parse --show-toplevel) && cd /home/miyano/frappe-bench && PYTHONPATH="$R" bench --site miyano run-tests --module <module>`
  trong đó `<module>` là đường dẫn file test đổi `/` thành `.` và bỏ `.py` (ví dụ `erp_ai.agent.test_queue`). Đã probe exit 0.
- DocType/Report mới (T8, T9, T10, T39) và mọi task `[migrate]` cần `bench migrate` cùng `PYTHONPATH="$R"` **trước** khi test: `cd /home/miyano/frappe-bench && PYTHONPATH="$R" bench --site miyano migrate`.
- Mọi task `[migrate]` tuần tự vì dùng chung site `miyano`.
- Slot `cmd.test_one` trong `.team/profile.json` hiện còn dạng cũ (`cd ../..`, không có `PYTHONPATH`). Chưa sửa vì hook chặn tech-lead; xem mục Việc cần người làm.

## Ràng buộc chung (chép nguyên văn từ spec/design; mọi task thừa hưởng)

Hằng (`erp_ai/constants.py`, T1): `AGENT_USER = "ai.agent@miyano.com.vn"`, `ROLE_AGENT = "ERP AI Agent"`, `ROLE_INSTRUCTOR = "ERP AI Instructor"`, `HELPDESK_AGENT_ROLE = "Agent"`, `SETTING_DOCTYPE = "ERP AI Setting"`, `CREDENTIAL_DOCTYPE = "ERP AI Credential"`, `LOG_DOCTYPE = "ERP AI Log"`, `LEVELS = ("L0","L1","L2","L3")`, `CATEGORIES = ("A".."F")`, `CONFIDENCE_VALUES = ("Cao","Trung bình","Thấp")`, `CLASSIFIED_BY_AI = "AI"`, `CLASSIFIED_BY_HUMAN = "Người"`, `TRIGGER_TICKET_INSERT = "ticket_insert"`, `TRIGGER_COMMENT_MENTION = "comment_mention"`, `JOB_TIMEOUT_S = 600`, `JOB_SAFETY_MARGIN_S = 60`, `PROBE_TIMEOUT_S = 10`, `CLASSIFICATION_FIELDS = ("ticket_type","agent_group","priority")`, `TITLE_WRONG_USER = "erp_ai: sai tài khoản job"`, `TITLE_RUN_FAILED = "erp_ai: lần chạy lỗi"`, `TITLE_ALARM = "erp_ai: CẢNH BÁO"`, `TITLE_NOTICE = "erp_ai: thông báo"`, `LOGGER_NAME = "erp_ai"`; 4 trạng thái khóa: `Hoạt động`, `Tạm nghỉ`, `Hết hạn mức`, `Lỗi khóa`.

Giá trị số: `max_turns_per_run` mặc định 8 (1..20); `max_runs_per_ticket_per_day` 5 (1..50); `max_keys_per_call` 3 (1..10); `request_timeout_s` 60 (5..300); `monthly_budget_usd` 10; job `queue="long"`, `timeout=600`; hạn chót job = 540 s; đọc mã ≤ 400 dòng/lần, tìm ≤ 40 kết quả, lệnh ngoài 30 s; token còn lại < 20.000 → khóa nghỉ; `DESCRIPTION_MAX_CHARS = 6000`; `TOOL_RESULT_MAX_CHARS = 20000`; trigger mặc định `@ai`; người nhận cảnh báo mặc định `info@miyano.com.vn`; nhóm loại trừ mặc định `Nhân sự & Hành chính`, `Tài chính Kế toán`.

Tên trường và hàm (không đổi giữa các task): tên Việt trong guide đã đổi sang tiếng Anh theo design 2.6 (`permission_level`, `max_keys_per_call`, `try_order`, `status`, `paused_until`, `tokens_remaining`, `limit_reset_at`, `error_count`, `last_error`, `last_success_at`, `ai_resolution_hint`, `ai_confidence`, `ai_classified_by`, `ai_updated_at`, `ai_opt_out`, `category_mapping`, `instructor`, `keys_tried`, `actions`, `value_before`, `value_after`…).

Kiểu lỗi mỗi biên (design mục 3): whitelist/controller `frappe.throw`/`frappe.only_for`; tool luôn trả `{"ok": False, "reason": <tiếng Việt ≤ 200 ký tự>}`, không ném lỗi; cổng ném `GatewayError`; handler/job/scheduler không ném ra framework, ghi `frappe.log_error(<tiêu đề hằng>, <message tường minh>)` (luôn 2 đối số; D-20).

Quyết định của kế hoạch (bổ sung cho design, để các task khớp nhau):
- Mọi test của runner/handler patch `erp_ai.gateway.call_model` bằng `test_utils.FakeGateway`; không test nào dùng mạng thật, Redis hay commit.
- `ToolContext` và `ToolSpec` định nghĩa ở `registry.py` (T23); `read.py`, `source.py`, `write_ticket.py` nhập chúng và mỗi module xuất `TOOLS: list[ToolSpec]`; `registry._all_specs()` nhập ba module đó **bên trong hàm** để tránh vòng nhập.
- `test_utils.py` là file chung, chỉ **thêm** hàm, theo chuỗi T1 → T9 → T15 → T16 → T22; không task nào ngoài chuỗi này được sửa nó.
- `test_eval_and_runner_share_classify_request` đặt ở `eval/test_run_eval.py` (T38), không ở `test_classification.py` như design, để T3 không chờ eval.
- Touchpoint test bổ sung ngoài 65 của design: `erp_ai/erp_ai_agent/doctype/erp_ai_credential/test_erp_ai_credential.py` (T8), `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` (T10), `erp_ai/test_alerts.py` (T14), `erp_ai/agent/test_run_log.py` (T22). Đều dưới `erp_ai/` (nằm trong `allowed_new_file_roots`), không chạm `protected_paths`.
- Hộp ngữ cảnh dev: chỉ sửa trong touchpoint của task; tên module/đường dẫn dưới `erp_ai/erp_ai_agent/` (không `erp_ai/erp_ai/`).

## Bảng một file, một chủ

Chỉ liệt các file có nhiều hơn một task chạm. Các file còn lại (khoảng 40) chỉ có một task.

| File | Task chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| `erp_ai/hooks.py` | T1 | T11, T31, T32, T33, T35 | T1 → T11 → T31 → T32 → T33 → T35 |
| `erp_ai/handlers.py`, `erp_ai/test_handlers.py` | T1 | T31, T32 | T1 → T31 → T32 |
| `erp_ai/agent/queue.py` | T1 | T2 | T1 → T2 |
| `erp_ai/agent/runner.py` | T1 | T28, T29, T30 | T1 → T28 → T29 → T30 |
| `erp_ai/agent/test_runner.py` | T28 | T29, T30 | T28 → T29 → T30 |
| `erp_ai/gateway/__init__.py` | T1 | T17, T18, T19 | T1 → T17 → T18 → T19 |
| `erp_ai/gateway/test_gateway.py` | T15 | T16, T17, T18, T19 | T15 → T16 → T17 → T18 → T19 |
| `erp_ai/gateway/client.py` | T15 | T19 | T15 → T19 |
| `erp_ai/test_utils.py` | T1 | T9, T15, T16, T22 | T1 → T9 → T15 → T16 → T22 |
| `erp_ai/install.py`, `erp_ai/test_install.py` | T11 | T12, T13 | T11 → T12 → T13 |
| `erp_ai/tasks.py`, `erp_ai/test_tasks.py` | T33 | T34, T35 | T33 → T34 → T35 |
| `erp_ai/agent/tools/source.py`, `test_source.py` | T6 | T7, T27 (chỉ `source.py`) | T6 → T7 → T27 |
| `erp_ai/agent/tools/registry.py`, `test_registry.py` | T23 | T27 | T23 → T27 |
| `erp_ai/agent/tools/write_ticket.py`, `test_write_ticket.py` | T25 | T26 | T25 → T26 |
| `erp_ai/eval/run_eval.py`, `test_run_eval.py` | T5 | T38 | T5 → T38 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`, `test_erp_ai_setting.py` | T9 | T36 | T9 → T36 |

## Touchpoint → task (65 của design + 4 test bổ sung; không hàng nào trống)

| Touchpoint | Task |
|---|---|
| `pyproject.toml` | T15 |
| `erp_ai/hooks.py` | T1, T11, T31, T32, T33, T35 |
| `.github/workflows/ci.yml` | T40 |
| `erp_ai/constants.py` | T1 |
| `erp_ai/alerts.py` (+ `test_alerts.py` bổ sung) | T14 |
| `erp_ai/handlers.py`, `erp_ai/test_handlers.py` | T1, T31, T32 |
| `erp_ai/tasks.py`, `erp_ai/test_tasks.py` | T33, T34, T35 |
| `erp_ai/install.py`, `erp_ai/test_install.py` | T11, T12, T13 |
| `erp_ai/test_utils.py` | T1, T9, T15, T16, T22 |
| `erp_ai/test_architecture.py` | T40 |
| `erp_ai/agent/__init__.py` | T1 |
| `erp_ai/agent/queue.py`, `test_queue.py` | T1, T2 |
| `erp_ai/agent/policy.py`, `test_policy.py` | T20 |
| `erp_ai/agent/authority.py`, `test_authority.py` | T21 |
| `erp_ai/agent/prompts.py`, `classification.py`, `test_classification.py` | T3 |
| `erp_ai/agent/run_log.py` (+ `test_run_log.py` bổ sung) | T22 |
| `erp_ai/agent/runner.py`, `test_runner.py` | T1, T28, T29, T30 |
| `erp_ai/agent/tools/__init__.py`, `registry.py`, `test_registry.py` | T23, T27 |
| `erp_ai/agent/tools/read.py`, `test_read.py` | T24 |
| `erp_ai/agent/tools/source.py`, `test_source.py` | T6, T7, T27 |
| `erp_ai/agent/tools/write_ticket.py`, `test_write_ticket.py` | T25, T26 |
| `erp_ai/gateway/__init__.py` | T1, T17, T18, T19 |
| `erp_ai/gateway/client.py` | T15, T19 |
| `erp_ai/gateway/breaker.py`, `test_breaker.py` | T4 |
| `erp_ai/gateway/credentials.py` | T16 |
| `erp_ai/gateway/cost.py` | T15 |
| `erp_ai/gateway/test_gateway.py` | T15–T19 |
| `erp_ai/eval/__init__.py` | T5 |
| `erp_ai/eval/export_tickets.py`, `test_export_tickets.py` | T37 |
| `erp_ai/eval/run_eval.py`, `test_run_eval.py` | T5, T38 |
| `erp_ai/erp_ai_agent/doctype/__init__.py`, `erp_ai_credential/*` (+ `test_erp_ai_credential.py` bổ sung) | T8 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/{__init__,json,py,test}` | T9 |
| `erp_ai_setting.js`, `check_keys` trong `erp_ai_setting.py` | T36 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/*` (+ `test_erp_ai_log.py` bổ sung) | T10 |
| `erp_ai/erp_ai_agent/report/**` (6 file) | T39 |

## Tiêu chí → task (20/20)

| Tiêu chí | Task |
|---|---|
| AC-1 | T5, T38 |
| AC-2 | T37 |
| AC-3 | T3, T28, T38 |
| AC-4 | T9, T11, T12, T31 |
| AC-5 | T1, T2, T31 |
| AC-6 | T28 |
| AC-7 | T21 |
| AC-8 | T23, T25, T26, T27 |
| AC-9 | T28 |
| AC-10 | T3, T25, T29, T30 |
| AC-11 | T32 |
| AC-12 | T39 |
| AC-13 | T6, T7 |
| AC-14 | T19, T24 |
| AC-15 | T15, T22, T28, T30 |
| AC-16 | T20, T33 |
| AC-17 | T4, T16, T17 |
| AC-18 | T18, T34, T35 |
| AC-19 | T8, T9, T36 (+ người kiểm sau G4) |
| AC-20 | T12 (phần tự động; người kiểm sau G4) |

NFR-1 → T1, T2, T31. NFR-2 → T1, T2, T17. NFR-3 → T9, T28, T30. NFR-4 → T20, T24, T28, T31. NFR-5 → T14, T19, T40. NFR-6 → T6, T7. NFR-7 → T15, T17. NFR-8 → T16. NFR-9 → T5, T39 (số đo thật sau G4).

## Điểm kiểm (`cmd.test` xanh trên `team/FEAT-001` và luồng chính chạy)

| Điểm | Sau task | Điều phải thấy |
|---|---|---|
| CP-0 | T1 | Phiếu mới → đúng 1 job → `run_for_ticket` gọi cổng giả 1 lần; lưu phiếu không gọi model |
| CP-1 | T13 | `bench migrate` exit 0 hai lần liên tiếp; `cmd.test` xanh; số đối soát design mục 6 khớp |
| CP-2 | T19 | `cmd.test` xanh; `test_api_key_never_leaks` xanh |
| CP-3 | T27 | `cmd.test` xanh; ma trận bộ tool 4 mức × thẩm quyền xanh |
| CP-4 | T30 | `cmd.test` xanh; runner L0 và L1 chạy đầu-cuối với cổng giả |
| CP-5 | T40 | `cmd.test` xanh toàn app; `cmd.lint` sạch; không có dấu skip trong `test.skip_markers` |

## Walking skeleton (cỡ L)

T1 chạy đầu-cuối: tạo HD Ticket → `ticket_after_insert` (hook `doc_events`) → `queue.enqueue_agent_run` (`frappe.enqueue` sau commit, hàng đợi `long`) → `runner.run_for_ticket` → `gateway.call_model` (giả bằng `FakeGateway`). Bằng chứng: một lần chạy `cmd.test_one` erp_ai/test_handlers.py, đỏ rồi xanh. Cổng thật, nhật ký, thẩm quyền, tool chưa có; chúng nối vào các điểm đã có này ở các task sau. T1 vượt 5 file (9 file) vì phải xuyên mọi tầng; mỗi file chỉ là bản tối thiểu.

## Rủi ro

| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Khóa API rò vào log/comment/Error Log (NFR-5) | `test_api_key_never_leaks` đỏ; `log_error` thiếu `message` | T19 là task riêng; T40 quét `log_error(` luôn 2 đối số; `import anthropic` và `get_decrypted_password` chỉ ở `gateway/**` |
| Nhiều task chạm `bench migrate` trên cùng site `miyano` | migrate lỗi vì DocType nửa vời từ worktree khác | T8–T13, T39 tuần tự; không ghép với task khác; migrate fail → dừng, không tick |
| Tool ghi bị Frappe âm thầm đặt lại giá trị do permlevel (7/8) | `set_classification` trả `ok=true` mà bản ghi không đổi | T25 kiểm `has_permlevel_access_to` trước khi ghi; test thu quyền (`test_write_without_permission_returns_ok_false_unchanged`) |
| ERPNext/`Task` không có trên `miyano` | `frappe.db.exists("DocType","Task")` sai (D-14) | T13 ghi warning và báo tech-lead; tool `create_task` là mục cắt số (3) |
| Header hạn mức API chưa kiểm chứng (guide `:1518`) | header vắng/sai định dạng | T16 bỏ qua an toàn; test `test_low_tokens_pause_until_reset_and_missing_headers_ignored` |
| Hook `doc_events` làm hỏng lượt lưu phiếu của người | ngoại lệ ở `ticket_after_insert` | handler chỉ đọc có kiểm trước, không `try/except` nuốt lỗi, không gọi mạng; T31, T40 |
| Mẫu 71 phiếu thật/khóa thật chưa có | không kiểm NFR-9 được lúc build | ngoài DoD của đội; đo sau G4 (việc của người) |

## Review focus (≤ 5 đầu vào/lỗi mà spec ngụ ý, mỗi cái đã có test ở task chủ)

1. Phiếu Helpdesk tự điền `ticket_type`/`priority` mặc định trước `after_insert` → AC-5(a) vẫn xếp job (cờ `erp_ai_prefilled` ở `before_insert`) — T31, `test_new_unclassified_ticket_enqueues_one_job`.
2. Tên nhóm loại trừ gõ khác hoa/thường hoặc dư khoảng trắng vẫn bị loại, 0 byte gửi API — T20, T28, T31.
3. Vượt ngân sách không bao giờ nâng `L0` thành `L1`; đúng bằng ngân sách thì không lui — T20, `test_effective_level_over_budget_never_raises`.
4. Đường dẫn đọc mã thoát khỏi `apps/` qua `../`, đường tuyệt đối, symlink, và git với cờ `--output`/`--no-index` — T6, T7.
5. Timeout sau khi request đã đi (kết quả không rõ) → khóa nghỉ, chuyển khóa, bản ghi nhật ký có `error` không có usage — T17, T30.

## Việc cần người làm (tech-lead không tự làm được)

- `.team/config.json`: `base_branch = "main"` nhưng repo chỉ có `develop`. Nhánh `team/FEAT-001` đã tạo từ `develop`. Sửa `base_branch` thành `develop` trước `/team:pr` (hook chặn tech-lead sửa).
- `.team/profile.json`: sửa `cmd.test_one` sang dạng `PYTHONPATH` ở mục Môi trường (hiện dev chỉ có chỉ dẫn trong plan này); thêm slot `cmd.uninstall` nếu muốn qa chạy lên/xuống/lên (design mục 6).
- Giả định ERPNext có trên `miyano` (D-14) chưa kiểm; T13 sẽ lộ ra.
