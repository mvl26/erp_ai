Feature: FEAT-001
Stage: plan
Author-agent: tech-lead
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks FEAT-001

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
Đường dẫn trong `files:` tính từ gốc repo `apps/erp_ai/`. `test:` là file chạy bằng `cmd.test_one` (dạng chạy trong worktree: xem `plan.md` mục Ràng buộc chung). Task có `[migrate]` đụng DocType/hook cần `bench migrate` trước khi test → chạy tuần tự. Tên hằng, hàm, trường dùng đúng `plan.md` mục Ràng buộc chung và `design.md`; không đổi tên.

Tiến độ: 9/42 (T1, T1b, T2..T7, T7b xong; cmd.test sau merge T7b: Ran 80 tests OK, pre-commit exit 0). Việc tiếp theo: T8 (DocType ERP AI Credential, [migrate]), rồi chuỗi migrate T8..T13 tuần tự (T14 song song được sau T9). Cần người xem: deferred của review-07 (design 5.4 vs allowlist git, git có thể lộ bí mật đã commit). Deferred: xem review-02..06 (limit=401 phải bị registry từ chối ở T23/T27; T9 đặt mặc định category_mapping = DEFAULT_CATEGORY_MAPPING; runner T28 gọi validate_mapping). Lưu ý: T31 phải bỏ guard `frappe.db.exists("DocType", SETTING_DOCTYPE)` trong handlers.py (tạm thời từ T1). BASE của từng task ghi vào dòng tiến độ ở đây trước khi gọi dev.

## Walking skeleton (cỡ L)

- [x] T1 — Walking skeleton: phiếu mới → handler → hàng đợi → runner (cổng giả) — files: erp_ai/constants.py, erp_ai/hooks.py, erp_ai/handlers.py, erp_ai/agent/__init__.py, erp_ai/agent/queue.py, erp_ai/agent/runner.py, erp_ai/gateway/__init__.py, erp_ai/test_utils.py, erp_ai/tests/test_handlers.py — test: erp_ai/tests/test_handlers.py — depends: —
  - progress: BASE=34e4c8f · dev call 1 · review round 1 request-changes (STD-DESIGN-2 guard) · round 2 request-changes (STD-TEST-5) · round 3 approve (head 12e8c92) · merged into team/FEAT-001 · test_handlers 6 OK; `--app erp_ai` runs 0 tests (xem journal)
  - Ngoại lệ cỡ: 9 file vì skeleton chạy xuyên mọi tầng; mỗi file chỉ là bản tối thiểu, các task sau mở rộng theo bảng một-file-một-chủ trong plan.md.
  - Criterion: AC-5(a) phần đường chính, NFR-1, NFR-2 (đường đầu-cuối với lõi giả)
  - Receives: `frappe.db.get_single_value("ERP AI Setting", "enabled")` (test patch trả 1 vì DocType chưa có); HD Ticket tạo bởi `helpdesk.test_utils.make_ticket`
  - Returns: `constants.py` (toàn bộ hằng ở mục 3 của design, đủ để các task sau chỉ import); `handlers.ticket_after_insert(doc, method=None)` (chỉ điều kiện: bật, `doc.owner != AGENT_USER`); `queue.enqueue_agent_run(ticket_name: str, trigger: str) -> bool` (đúng lời gọi `frappe.enqueue` của design 3.2, chưa có chặn trùng trong giao dịch); `runner.run_for_ticket(ticket_name: str, trigger: str) -> None` (gọi `gateway.call_model("classify", system=[...], messages=[...], max_tokens=400)` một lần rồi dừng; chưa ghi nhật ký); `gateway.ModelResult` (frozen dataclass đủ trường design 3.4.1), `gateway.GatewayError(kind, status, credential_label, request_id, keys_tried)`, `gateway.call_model(task, *, system, messages, max_tokens, tools=None, deadline=None)` (ném `NotImplementedError`, test patch); `test_utils.FakeGateway` (hàng đợi `ModelResult`/`GatewayError`, đếm lời gọi), `test_utils.make_model_result(**kw)`; `hooks.py`: `required_apps = ["helpdesk"]`, `doc_events["HD Ticket"]["after_insert"]`
  - Expect: `cmd.test_one` erp_ai/tests/test_handlers.py → test: tạo phiếu (agent "bật" qua patch) → đúng 1 lời gọi `frappe.enqueue` có `queue="long"`, `timeout=600`, `enqueue_after_commit=True`, `deduplicate=True`; chạy `run_for_ticket` trực tiếp với `FakeGateway` → đúng 1 lời gọi `call_model`; lưu phiếu không gọi `call_model` lần nào. Đỏ trước khi viết mã (ImportError/AssertionError), xanh sau.

- [x] T1b — Chuyển test vào gói `erp_ai/tests/` để `--app erp_ai` tìm thấy test (D2: lỗi `_add_test` của Frappe) — files: erp_ai/tests/__init__.py, erp_ai/tests/test_handlers.py, erp_ai/test_handlers.py (xóa/di chuyển bằng `git mv`) — test: erp_ai/tests/test_handlers.py — depends: T1
  - progress: BASE=88c1a2c · dev call 1 (+1 lượt chứng cứ) · review round 1 approve (head 9c0a390) · merged · `--app erp_ai` Ran 6 tests OK, pre-commit exit 0
  - Criterion: `cmd.test` (`--app erp_ai`) chạy thật các test (không còn "NO TESTS RAN")
  - Returns: `git mv erp_ai/test_handlers.py erp_ai/tests/test_handlers.py`, thêm `erp_ai/tests/__init__.py` rỗng; sửa import nếu cần; `test_utils.py` giữ nguyên tại `erp_ai/`
  - Expect: `bench --site miyano run-tests --app erp_ai` → "Ran 6 tests … OK"; `--module erp_ai.tests.test_handlers` xanh. Mọi task sau dùng đường dẫn test `erp_ai/tests/test_*.py` (test_handlers, test_install, test_alerts, test_tasks, test_architecture).

## Nhóm thuần (không migrate, không file chung)

- [x] T2 — Chặn trùng job trong cùng giao dịch — files: erp_ai/agent/queue.py, erp_ai/agent/test_queue.py — test: erp_ai/agent/test_queue.py — depends: T1
  - progress: BASE=a351af1 · dev call 1 (song song với T3)
  - Criterion: AC-5(f), NFR-1, NFR-2 (D-3)
  - Receives: `queue.enqueue_agent_run` từ T1
  - Returns: cùng chữ ký; lần gọi thứ hai cùng `job_id` trong một giao dịch → `False`, không gọi `frappe.enqueue`; tập `frappe.flags.erp_ai_pending_job_ids` xóa ở `after_commit`/`after_rollback`; `trigger` ngoài {`ticket_insert`, `comment_mention`} → `ValueError`
  - Expect: `cmd.test_one` erp_ai/agent/test_queue.py → test_duplicate_trigger_same_transaction_one_job, test_enqueue_parameters, và test sau rollback xếp lại được đều xanh

- [x] T3 — Prompt và bộ đọc phân loại — files: erp_ai/agent/prompts.py, erp_ai/agent/classification.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_classification.py — depends: T1
  - progress: BASE=a351af1 · dev call 1 (song song với T2)
  - Criterion: AC-3 (JSON sai → `None`), AC-10 (nhánh thuần: ánh xạ, `[GẬP]`)
  - Receives: `constants.CATEGORIES`, `CONFIDENCE_VALUES`
  - Returns: `prompts.build_classify_request(subject: str, description: str) -> dict`, `prompts.ticket_text`, `prompts.build_reason_system(prompt_digest: str) -> list[dict]`, `prompts.build_initial_message(ticket: dict, comments: list[dict], trigger: str, classification: dict | None) -> str`; `classification.Classification`, `parse_classification(text: str) -> Classification | None`, `load_mapping(raw) -> dict`, `validate_mapping(raw) -> None`, `resolve_ticket_values(classification, subject, mapping) -> dict`; ánh xạ mặc định D-8 là hằng `DEFAULT_CATEGORY_MAPPING` trong `classification.py`
  - Expect: `cmd.test_one` erp_ai/agent/test_classification.py → test_parse_rejects_non_json_and_bad_values, test_urgent_prefix_forces_urgent, test mapping sai schema → ValidationError, xanh

- [x] T4 — Bảng cầu dao (hàm thuần) — files: erp_ai/gateway/breaker.py, erp_ai/gateway/test_breaker.py — test: erp_ai/gateway/test_breaker.py — depends: T1
  - progress: BASE=a85f798 · dev call 1 (song song với T5)
  - Criterion: AC-17 (hàng 1–9 của design 3.4.3), NFR-8 (một phần, nghỉ khi token < 20.000 làm ở T16)
  - Receives: không
  - Returns: `ApiFailure(status, kind, error_type, error_code, message_prefix, retry_after)` (dataclass), `Action(new_status, pause_seconds, switch_key, notify, kind)`, `decide(failure: ApiFailure, error_count: int) -> Action`
  - Expect: `cmd.test_one` erp_ai/gateway/test_breaker.py → test_breaker_table (subTest 9 hàng; 529 trần 600 s; 429 thiếu `retry-after` → 61 s) xanh

- [x] T5 — Số liệu đánh giá offline (hàm thuần) — files: erp_ai/eval/__init__.py, erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py — test: erp_ai/eval/test_run_eval.py — depends: T1
  - progress: BASE=a85f798 · dev call 1 (song song với T4)
  - Criterion: AC-1, NFR-9 (phép đo)
  - Receives: không (mapping truyền vào dạng dict)
  - Returns: `compute_metrics(rows: list[dict], mapping: dict) -> dict` (khóa đúng design 3.7: `labeled`, `correct`, `accuracy`, `per_category`, `confusion`, `unclassified`, `top_owner`, `non_top_owner`, `verdict`, `skipped_unlabeled`), `format_report(metrics: dict) -> str`
  - Expect: `cmd.test_one` erp_ai/eval/test_run_eval.py → test_metrics_twelve_ticket_sample (10/12 → 83,3% → "70–85%"), test_verdict_thresholds_at_85_and_70, test_unparseable_and_unlabeled_rows xanh

- [x] T6 — Tool mã nguồn: chặn đường dẫn, đọc, tìm — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T1
  - progress: BASE=be71629 · dev call 1 (song song với rework T5)
  - Criterion: AC-13 (trừ git), NFR-6 (400 dòng / 40 kết quả)
  - Receives: `constants.py`
  - Returns: `get_source_root() -> str`, `resolve_safe_path(rel: str) -> str | None`, `search_source(args: dict, ctx) -> dict`, `read_source(args: dict, ctx) -> dict` (trả `{"ok": bool, ...}` hoặc `{"ok": False, "reason": str}`; không ném lỗi), hằng `DUOI_CHO_PHEP`, `TEN_CAM` đúng guide `:342-345`; chưa có `ToolSpec` (T23 định nghĩa, T27 nối)
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_source.py → test_path_escape_refused, test_secret_names_and_extensions_refused, test_read_capped_at_400_lines, test_search_capped_at_40_hits xanh (thư mục tạm, patch `get_source_root`)

- [x] T7 — Tool mã nguồn: git chỉ đọc — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T6
  - progress: BASE=212f77b · dev call 1 · round 1 request-changes (blocker STD-SEC-3 abbreviation) · round 2 request-changes (STD-TEST-8) · round 3 approve (head 12229e3) · merged · cmd.test Ran 75 tests OK, pre-commit exit 0
  - Criterion: AC-13 (git), NFR-6 (30 s)
  - Receives: `get_source_root`, `resolve_safe_path` từ T6
  - Returns: `git_source(args: dict, ctx) -> dict`: danh sách lệnh, không `shell`, `timeout=30`, chỉ `log`/`show`/`diff`/`blame`, từ chối các cờ ở design 5.4, `FileNotFoundError` → `ok=false` "chưa cài git"
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_source.py → test_git_only_read_subcommands_and_safe_flags, test_git_missing_returns_not_installed, test_git_runs_with_timeout_list_args_no_shell xanh

- [x] T7b — Tool git: thu hẹp còn `log` và `blame` (D4) — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T7
  - progress: BASE=9010e38 · dev call 1 (2b523ac) · review round 1 request-changes (major STD-TEST-2: test show/diff bị che bởi blame checker) · rework FIX_BASE=2b523ac · round 2 approve (head 34d1450) · merged a97adc1 · cmd.test Ran 80 tests OK, pre-commit exit 0
  - Criterion: AC-13 (git), NFR-6; D4 (journal): `show`/`diff`/`log -p` in được nội dung file bí mật đã commit
  - Returns: `git_source` chỉ còn `log` và `blame` (bỏ `show`, `diff`); `log` từ chối mọi cờ in patch kể cả viết tắt (-p, -u, --patch*, -U*, --full-diff, --word-diff*, --cc, -m, --diff-merges*); mọi pathspec/file arg phải qua `resolve_safe_path`/`TEN_CAM`, ký tự glob bị từ chối; `blame` nhận đúng một file, kiểm như `read_source`
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_source.py → test mới: `show HEAD`, `log -p`, `log --pat`, pathspec glob đều bị từ chối; test cũ về `show`/`diff` được sửa theo D4 (spec đổi, STD-TEST-5)

## Chuỗi migrate: DocType và cài đặt (tuần tự)

- [ ] T8 — DocType ERP AI Credential (bảng con) [migrate] — files: erp_ai/erp_ai_agent/doctype/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json, erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/test_erp_ai_credential.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_credential/test_erp_ai_credential.py — depends: T4, T5, T6, T7
  - Ghi chú: `test_erp_ai_credential.py` là touchpoint bổ sung (test) so với design; ghi trong plan.md.
  - Criterion: AC-4 (nền), NFR-5 (`api_key` kiểu Password), AC-19 (trường tự quản read_only)
  - Receives: `constants` 4 hằng trạng thái khóa
  - Returns: DocType `ERP AI Credential` (`istable = 1`, module `ERP AI agent`) với đúng trường design 2.2; `status` có `read_only_depends_on: eval:doc.status!='Lỗi khóa'`
  - Expect: `cmd.migrate` exit 0 (PYTHONPATH worktree), rồi `cmd.test_one` → test: meta là bảng con, kiểu trường `api_key` = Password, mặc định `status` = "Hoạt động", `try_order` = 10, `enabled` = 1 xanh

- [ ] T9 — DocType ERP AI Setting và kiểm hợp lệ khi lưu [migrate] — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py, erp_ai/test_utils.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T3, T8
  - Criterion: AC-19 (phân quyền, trường tự quản), AC-4 (mặc định tắt/L0), NFR-3 (giới hạn số), STD-ERR-6 (D-25)
  - Receives: `classification.validate_mapping(raw) -> None` (T3)
  - Returns: DocType Single `ERP AI Setting` đủ trường design 2.1, quyền chỉ System Manager; `ERPAISetting.validate()` thực hiện (a)–(f) của design 3.6 (chưa có `check_keys`, `.js` — T36); `test_utils.set_agent_settings(**fields) -> None` (đặt cấu hình bằng `frappe.db.set_single_value`, dùng cho mọi test sau)
  - Expect: `cmd.migrate` exit 0, rồi `cmd.test_one` → test_hd_agent_cannot_read_or_write_settings, test_self_managed_fields_restored_on_human_save, test_human_can_move_key_error_to_active_only, test_validation_rejects_bad_mapping_limits_and_missing_prices xanh

- [ ] T10 — DocType ERP AI Log (nhật ký, không ai sửa/xóa) [migrate] — files: erp_ai/erp_ai_agent/doctype/erp_ai_log/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py — depends: T9
  - Ghi chú: `test_erp_ai_log.py` là touchpoint bổ sung (test).
  - Criterion: AC-15 (đủ trường nhật ký), A-10 (không xóa), ADR-004
  - Receives: không
  - Returns: DocType `ERP AI Log` đúng trường design 2.3, `autoname = hash`, chỉ mục `search_index` cho `ticket`, `run_id`; quyền: System Manager đọc/báo cáo/export, `ERP AI Agent` đọc/tạo, không ai write/delete
  - Expect: `cmd.migrate` exit 0, rồi `cmd.test_one` → test: tạo bản ghi dưới tài khoản có role agent được; HD Agent thường bị `PermissionError`; không role nào có quyền write/delete xanh

- [ ] T11 — Cài đặt: role, tài khoản agent, cấu hình mặc định, hook cài [migrate] — files: erp_ai/install.py, erp_ai/hooks.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T10
  - Criterion: AC-4 (role, tài khoản không có System Manager, mặc định tắt/L0, chạy lặp lại không lỗi), A-13, ADR-006 #4
  - Receives: `constants.AGENT_USER`, `ROLE_AGENT`, `ROLE_INSTRUCTOR`, `HELPDESK_AGENT_ROLE`
  - Returns: `install.ensure_setup() -> None` (bước 1, 2, 5 của design mục 6; bước 3, 4, 6 là T12, T13), `install.after_install()`, `install.after_migrate()`; `hooks.py`: `after_install`, `after_migrate`
  - Expect: `cmd.migrate` exit 0 hai lần liên tiếp, rồi `cmd.test_one` → test_setup_twice_is_idempotent, test_agent_user_has_exact_roles_without_system_manager, test_default_settings_disabled_level_l0 (giá trị người đã đặt không bị ghi đè), test_setup_never_writes_existing_tickets xanh

- [ ] T12 — Cài đặt: custom field AI trên HD Ticket và dòng template [migrate] — files: erp_ai/install.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T11
  - Criterion: AC-4 (trường AI có trên HD Ticket), AC-20 (phần tự động: permlevel 8, `visible_to = Agents`, HD Customer không có quyền pl 8), ADR-006 #3
  - Receives: `ensure_setup` từ T11
  - Returns: bước 3, 4 của design mục 6: 6 custom field `ai_section`, `ai_resolution_hint`, `ai_confidence`, `ai_classified_by`, `ai_updated_at`, `ai_opt_out` (permlevel 8, `module = "ERP AI agent"`, `create_custom_fields(update=True)`); thêm 5 dòng vào template `Default` (không sửa dòng có sẵn); template không tồn tại → logger warning
  - Expect: `cmd.migrate` exit 0 hai lần, rồi `cmd.test_one` → test_ai_fields_permlevel_8_and_template_rows_agents_only, test_existing_template_row_preserved, test_setup_twice_is_idempotent (đủ 6 field và k + 5 dòng sau lần 2) xanh

- [ ] T13 — Cài đặt: quyền Task cho role agent [migrate] — files: erp_ai/install.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: T12
  - Criterion: AC-8 (nền cho `create_task`), D-14
  - Receives: `ensure_setup` từ T12
  - Returns: bước 6 của design mục 6: nếu có DocType `Task` → `setup_custom_perms("Task")` + 1 Custom DocPerm {role `ERP AI Agent`, permlevel 0, read/write/create = 1, `if_owner = 1`}, `frappe.clear_cache(doctype="Task")`; không có Task → bỏ qua, ghi logger warning (báo tech-lead nếu `frappe.db.exists("DocType", "Task")` sai trên `miyano`)
  - Expect: `cmd.migrate` exit 0 hai lần, rồi `cmd.test_one` → test: đúng 1 Custom DocPerm cho role agent trên Task sau 2 lần cài; `cmd.test` toàn app xanh (điểm kiểm CP-1)

## Cổng model và lõi agent

- [ ] T14 — Cảnh báo: báo động và thông báo — files: erp_ai/alerts.py, erp_ai/tests/test_alerts.py — test: erp_ai/tests/test_alerts.py — depends: T9
  - Ghi chú: `test_alerts.py` là touchpoint bổ sung (test).
  - Criterion: AC-17 (báo động hết khóa), AC-18 (kênh email), NFR-5 (nội dung không chứa khóa), D-2, D-21
  - Receives: `set_agent_settings` (T9), `constants.TITLE_ALARM`, `TITLE_NOTICE`, `LOGGER_NAME`
  - Returns: `alerts.send_alarm(subject: str, message: str) -> None` (Error Log tiêu đề `TITLE_ALARM` có message tường minh + `frappe.sendmail(..., delayed=True)` tới các dòng `alert_recipients`), `alerts.send_notice(subject, message) -> None` (logger info + email, không Error Log)
  - Expect: `cmd.test_one` erp_ai/tests/test_alerts.py → test: patch `frappe.sendmail` đếm 1 lần cho mỗi lệnh gọi; `log_error` luôn có 2 đối số; người nhận lấy từ cấu hình xanh

- [ ] T15 — Cổng: tính chi phí, client SDK, khai phụ thuộc — files: erp_ai/gateway/cost.py, erp_ai/gateway/client.py, erp_ai/gateway/test_gateway.py, pyproject.toml, erp_ai/test_utils.py — test: erp_ai/gateway/test_gateway.py — depends: T4, T9
  - Criterion: AC-15 (chi phí = token × đơn giá), NFR-7 (`max_retries=0`, có timeout), NFR-5 (client là chỗ duy nhất `import anthropic`), STD-DEP-1 (`anthropic>=0.103.1,<1`)
  - Receives: `breaker.ApiFailure` (T4)
  - Returns: `cost.compute_cost(usage: dict, prices: dict) -> float`; `client._build_client(api_key: str, timeout: float)`; `client.send(api_key: str, *, timeout: float, request: dict) -> RawReply(message: dict, headers: dict, request_id: str)`; `client.to_api_failure(exc) -> ApiFailure | None`; `test_utils.fake_anthropic_client(...)`; `pyproject.toml`: `dependencies = ["anthropic>=0.103.1,<1"]`, `[tool.bench.frappe-dependencies]`
  - Expect: `cmd.test_one` erp_ai/gateway/test_gateway.py → test_cost_uses_four_token_prices (usage `None` → 0), test client tạo với `max_retries=0` và `timeout` xanh

- [ ] T16 — Cổng: chọn khóa và ghi trạng thái khóa — files: erp_ai/gateway/credentials.py, erp_ai/gateway/test_gateway.py, erp_ai/test_utils.py — test: erp_ai/gateway/test_gateway.py — depends: T15
  - Criterion: AC-17 (bộ lọc và thứ tự chọn khóa), NFR-5 (giải mã chỉ ở đây), ADR-004 (một chủ ghi trạng thái khóa)
  - Receives: `Action` từ T4; `set_agent_settings`
  - Returns: `credentials.select_keys(task: str, exclude: set[str]) -> list[dict]`, `credentials.get_api_key(row_name: str) -> str | None`, `credentials.apply_failure(row_name, action, failure) -> None`, `credentials.apply_success(row_name, headers) -> None` (header `anthropic-ratelimit-tokens-remaining`/`-reset`, < 20.000 → nghỉ đến mốc reset); `test_utils.add_credential(label, **fields) -> str`
  - Expect: `cmd.test_one` erp_ai/gateway/test_gateway.py → test_selection_filters_and_order, test_reason_requires_model_reason, test_low_tokens_pause_until_reset_and_missing_headers_ignored (19.999 nghỉ, 20.000 không, header vắng → không đổi) xanh

- [ ] T17 — Cổng: `call_model` chuyển khóa theo cầu dao — files: erp_ai/gateway/__init__.py, erp_ai/gateway/test_gateway.py — test: erp_ai/gateway/test_gateway.py — depends: T14, T16
  - Criterion: AC-17 (chuyển khóa, báo, 400 không chuyển, hết khóa báo động), NFR-7 (`max_keys_per_call`), NFR-2 (hạn chót), AC-15 (nhãn khóa, `keys_tried`, `latency_ms`)
  - Receives: `breaker.decide`, `credentials.*`, `cost.compute_cost`, `client.send`, `alerts.send_alarm`/`send_notice`
  - Returns: `call_model` thật (chữ ký đã có từ T1), `GatewayError.kind` ∈ `no_key`, `all_keys_failed`, `bad_request`, `deadline`, `unexpected`; ném `from None`
  - Expect: `cmd.test_one` erp_ai/gateway/test_gateway.py → test_max_keys_per_call (5 khóa 529, `max_keys_per_call=3` → đúng 3 lần thử), test_bad_request_does_not_switch_key, test_no_usable_key_alarm (hết khóa → 1 email báo động; 401 → `Lỗi khóa` + báo động; 402 → `Hết hạn mức` + tin), test_deadline_limits_attempt_timeout (còn 3 s → `deadline`, 0 lời gọi client) xanh

- [ ] T18 — Cổng: dò khóa và dò lại khóa hết hạn mức — files: erp_ai/gateway/__init__.py, erp_ai/gateway/test_gateway.py — test: erp_ai/gateway/test_gateway.py — depends: T17
  - Criterion: AC-18 (chỉ dò `Hết hạn mức`), AC-19 (kết quả từng khóa)
  - Receives: `call_model` nội bộ từ T17
  - Returns: `gateway.probe_credential(row_name: str) -> dict` (`{"label","ok","error_kind","status"}`), `gateway.reprobe_exhausted_keys() -> list[dict]`; `provider ≠ Anthropic` → `error_kind="unsupported_provider"`, trạng thái không đổi
  - Expect: `cmd.test_one` erp_ai/gateway/test_gateway.py → test: probe thành công → `Hoạt động`; chỉ khóa `Hết hạn mức` bị dò lại, `Lỗi khóa` thì không xanh

- [ ] T19 — Cổng: bằng chứng khóa API không rò rỉ — files: erp_ai/gateway/test_gateway.py, erp_ai/gateway/__init__.py, erp_ai/gateway/client.py — test: erp_ai/gateway/test_gateway.py — depends: T18
  - Criterion: AC-14 (phần khóa), NFR-5
  - Receives: toàn bộ đường lỗi và thành công của cổng
  - Returns: không hàm mới; chỉ sửa mã cổng nếu test tìm thấy rò rỉ (dev sửa mã sản phẩm, không nuốt lỗi)
  - Expect: `cmd.test_one` erp_ai/gateway/test_gateway.py → test_api_key_never_leaks (khóa giả có chuỗi nhận diện; đường thành công, 401, ngoại lệ lạ; tìm trong ERP AI Log, HD Ticket Comment, Error Log, email đã gửi, `last_error` → 0 kết quả) xanh. Điểm kiểm CP-2: `cmd.test` xanh

- [ ] T20 — Chính sách: điều kiện gửi, mức hiệu lực, giới hạn ngày — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py — test: erp_ai/agent/test_policy.py — depends: T12
  - Criterion: AC-16 (mức hiệu lực không bao giờ nâng `L0`), NFR-4 (một hàm điều kiện gửi), AC-5(d), AC-15 (giới hạn ngày đếm từ nhật ký)
  - Receives: `set_agent_settings`; trường `ai_opt_out` (T12); DocType `ERP AI Log` (T10)
  - Returns: `policy.is_enabled() -> bool`, `can_send_ticket(ticket) -> bool`, `contains_keyword(content) -> bool`, `effective_level(settings) -> str`, `runs_today(ticket_name, now=None) -> int`; hằng `OPT_OUT_FIELD`, `EXCLUDED_TEAMS_FIELD`, `SEND_POLICY_FIELDS`
  - Expect: `cmd.test_one` erp_ai/agent/test_policy.py → test_effective_level_over_budget_never_raises (L3/L2 → L1; L1 → L1; L0 → L0; đúng bằng ngân sách → không lui), test nhóm loại trừ khác hoa thường/khoảng trắng vẫn bị loại, test phiếu không tồn tại → False, test từ khóa không phân biệt hoa thường xanh

- [ ] T21 — Thẩm quyền theo người — files: erp_ai/agent/authority.py, erp_ai/agent/test_authority.py — test: erp_ai/agent/test_authority.py — depends: T11
  - Criterion: AC-7 (bảng 6 trường hợp), D-16, D-24
  - Receives: `constants.ROLE_INSTRUCTOR`, `AGENT_USER`; factory `helpdesk.test_utils` (`create_agent`, `create_contact`, `make_todo`)
  - Returns: `authority.is_instruction(author: str, ticket_name: str) -> bool`, `latest_instructor(ticket_name: str) -> str | None`, `label_comments(ticket_name: str, comments: list[dict]) -> list[dict]`
  - Expect: `cmd.test_one` erp_ai/agent/test_authority.py → test_instructor_role_has_authority_on_any_ticket, test_assigned_by_other_authority_only_on_that_ticket, test_self_assigned_is_data, test_contact_and_plain_agent_are_data, test_latest_instructor_prefers_latest_comment_then_owner xanh

- [ ] T22 — Ghi nhật ký lượt gọi — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py, erp_ai/test_utils.py — test: erp_ai/agent/test_run_log.py — depends: T11, T16
  - Ghi chú: `test_run_log.py` là touchpoint bổ sung (test).
  - Criterion: AC-15 (đủ trường nhật ký mỗi lượt), ADR-004 (nơi duy nhất tạo `ERP AI Log`), D-20 (commit khi `not frappe.flags.in_test`)
  - Receives: DocType `ERP AI Log` (T10)
  - Returns: `run_log.write_entry(**fields) -> str` (serialize `keys_tried`, `tools_called`, `actions` thành JSON; tạo dưới tài khoản agent có phân quyền); `test_utils.make_log_entry(**fields) -> str`
  - Expect: `cmd.test_one` erp_ai/agent/test_run_log.py → test: trường JSON được serialize, bản ghi tên hash, người không có role agent bị `PermissionError` xanh

- [ ] T23 — Registry tool: bối cảnh, kiểm tham số, bộ tool theo mức × thẩm quyền (lõi) — files: erp_ai/agent/tools/__init__.py, erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T1
  - Criterion: AC-8 (khung), STD-ERR-2 (kiểm tham số tại biên), ADR-005
  - Receives: `constants.LEVELS`
  - Returns: `ToolContext` (frozen dataclass: `ticket_name`, `effective_level`, `instructor`, `run_id`, `category_mapping`, `agent_user`); `ToolSpec(name: str, group: Literal["read","ticket_write","task_write"], schema: dict, handler: Callable[[dict, ToolContext], dict])`; `get_tool_schemas(effective_level: str, has_instructor: bool) -> list[dict]` (L0 → `[]`; L1+ → nhóm read + ticket_write, cộng task_write khi `has_instructor`; trả bản sao); `execute_tool(name: str, arguments: dict, context: ToolContext) -> dict` (tên ngoài bộ cấp → `ok=false`; sai tham số → `ok=false` "tham số không hợp lệ: <khóa>"; savepoint, ngoại lệ bất ngờ → rollback về savepoint rồi ném lên); `_all_specs()` nhập lười `read.TOOLS`, `source.TOOLS`, `write_ticket.TOOLS` bên trong hàm (tránh vòng nhập); `tools/__init__.py` export `get_tool_schemas`, `execute_tool`, `ToolContext`
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_registry.py → test_execute_rejects_tool_not_granted_and_bad_arguments (patch `_all_specs` bằng `ToolSpec` giả; tên ngoài bộ, sai enum, quá độ dài) xanh

- [ ] T24 — Tool đọc: phiếu, comment, phiếu tương tự, bản ghi — files: erp_ai/agent/tools/read.py, erp_ai/agent/tools/test_read.py — test: erp_ai/agent/tools/test_read.py — depends: T20, T21, T23
  - Criterion: AC-14 (DocType bị cấm, không trả trường Password), NFR-4 (phiếu nhóm loại trừ không bao giờ trả), AC-7 (nhãn `role` của comment)
  - Receives: `policy.can_send_ticket`, `authority.label_comments` (T21), `ToolContext`, `ToolSpec`
  - Returns: `get_ticket`, `list_comments`, `search_resolved_tickets`, `get_record` (handler `(args: dict, ctx: ToolContext) -> dict`), `DENIED_DOCTYPES`, `ALLOWED_READ_DOCTYPES`, `TOOL_RESULT_MAX_CHARS = 20000`, `TOOLS: list[ToolSpec]`
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_read.py → test_denied_doctypes_refused (subTest từng DocType), test_password_fields_never_returned, test_excluded_tickets_never_returned (cả `get_ticket`, `get_record`, `search_resolved_tickets`) xanh

- [ ] T25 — Tool ghi: `set_classification` — files: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_write_ticket.py — test: erp_ai/agent/tools/test_write_ticket.py — depends: T3, T12, T23
  - Criterion: AC-10 (ánh xạ, người đã phân loại không bị ghi đè, giá trị không tồn tại → bỏ trường), AC-8 (không nhận tên DocType/trường; thu quyền → `ok=false`, bản ghi không đổi), ADR-005 #2
  - Receives: `ToolContext.category_mapping`, `classification.resolve_ticket_values`
  - Returns: `set_classification(args: dict, ctx) -> dict` (`{"ok": True, "before", "after", "skipped": [{"field","reason"}]}`); kiểm `has_permission("write")` và `has_permlevel_access_to(field, permission_type="write")` trước khi ghi; hằng `TOOLS: list[ToolSpec]` (mới có 1 tool)
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_write_ticket.py → test_write_without_permission_returns_ok_false_unchanged, test_mapping_to_missing_value_skips_field, test người đã phân loại không bị ghi đè xanh

- [ ] T26 — Tool ghi: hướng giải quyết, comment, Task — files: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_write_ticket.py — test: erp_ai/agent/tools/test_write_ticket.py — depends: T13, T25
  - Criterion: AC-8 (`create_task` chỉ khi có người ra lệnh; thiếu quyền → `ok=false`), A-5, D-14
  - Receives: `set_classification` và `TOOLS` từ T25
  - Returns: `set_resolution_hint(args, ctx) -> dict`, `post_comment(args, ctx) -> dict`, `create_task(args, ctx) -> dict` (dòng đầu `description` có tên và đường dẫn phiếu; không có người ra lệnh hoặc không có DocType `Task` → `ok=false`); `TOOLS` đủ 4 tool, nhóm `task_write` cho `create_task`
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_write_ticket.py → test_create_task_requires_instructor và test hướng giải quyết/comment thiếu quyền → `ok=false` xanh

- [ ] T27 — Registry: nối đủ 10 tool và kiểm ma trận bộ tool — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T7b, T24, T26
  - Criterion: AC-8 (ma trận 4 mức × có/không thẩm quyền; không tool ghi nào nhận DocType/trường), NFR-6
  - Receives: `read.TOOLS`, `source.TOOLS` (T6, T7 bổ sung `TOOLS` cho 3 tool nguồn qua task này: dev thêm danh sách `TOOLS` vào `source.py`), `write_ticket.TOOLS`
  - Returns: `_all_specs()` thật; `source.TOOLS: list[ToolSpec]` (`search_source`, `read_source`, `git_source`)
  - Expect: `cmd.test_one` erp_ai/agent/tools/test_registry.py → test_tool_names_per_level_and_authority, test_no_write_tool_accepts_doctype_or_field xanh. Điểm kiểm CP-3: `cmd.test` xanh
  - Ghi chú: task này sửa thêm `erp_ai/agent/tools/source.py` (chỉ thêm `TOOLS`); T27 là chủ duy nhất của `source.py` ở thời điểm này (T6, T7 đã xong).

## Runner (tuần tự: cùng file)

- [ ] T28 — Runner: chốt tài khoản, điều kiện dừng, bước phân loại ở L0 — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner.py — test: erp_ai/agent/test_runner.py — depends: T2, T3, T19, T20, T22
  - Criterion: AC-6, AC-9 (L0: phiếu trước = sau), AC-3 (UNPARSEABLE, lần chạy không hỏng), AC-15 (`daily_limit`), NFR-4 (không gửi khi `can_send_ticket` sai lúc chạy), ADR-003 (a)–(e)
  - Receives: `policy.*`, `prompts.build_classify_request`, `classification.parse_classification`, `resolve_ticket_values`, `run_log.write_entry`, `gateway.call_model`, `test_utils.FakeGateway`
  - Returns: `run_for_ticket(ticket_name, trigger)` thân bọc `try/except Exception` → `frappe.log_error(TITLE_RUN_FAILED, <message tường minh>)`; bước (a)–(e) và bước phân loại của design 4.3; nhật ký `skip` với `stop_reason` ∈ {`not_sendable`, `daily_limit`, `level_L0`}
  - Expect: `cmd.test_one` erp_ai/agent/test_runner.py → test_wrong_session_user_stops_before_model, test_missing_agent_user_stops, test_disabled_at_run_time_no_model_call, test_not_sendable_at_run_time_no_model_call, test_l0_logs_prediction_ticket_unchanged, test_l0_comment_mention_skipped_no_call, test_unparseable_classification_logged_run_continues, test_sixth_run_same_day_no_call xanh

- [ ] T29 — Runner: L1 ghi phân loại qua tool — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner.py — test: erp_ai/agent/test_runner.py — depends: T27, T28
  - Criterion: AC-10 (L1: ghi theo ánh xạ + độ tin cậy + "phân loại bởi = AI", `status` không đổi, người đã phân loại không bị ghi đè), ADR-004 (runner cập nhật `applied` của bản ghi `classify` do mình tạo)
  - Receives: `execute_tool("set_classification", ...)`, `ToolContext`
  - Returns: ở `level ≥ L1` sau bước phân loại: `ToolContext` dựng một lần, gọi `set_classification`, `ok=true` → `applied = 1`, `value_before/after`, `actions` của bản ghi `classify` vừa tạo
  - Expect: `cmd.test_one` erp_ai/agent/test_runner.py → test_l1_applies_mapping_confidence_and_hint (phần phân loại), test_l1_human_classified_not_overwritten xanh

- [ ] T30 — Runner: vòng lập luận có giới hạn lượt và nhật ký từng lượt — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner.py — test: erp_ai/agent/test_runner.py — depends: T21, T29
  - Criterion: AC-15 (đúng `max_turns_per_run` lượt, `stop_reason = max_turns` ở lượt cuối, đủ trường nhật ký), AC-10 (hướng giải quyết), AC-8 (bộ tool theo mức × thẩm quyền), NFR-2 (`time_budget`)
  - Receives: `get_tool_schemas`, `execute_tool`, `authority.latest_instructor`, `prompts.build_reason_system`, `build_initial_message`
  - Returns: bước lập luận của design 4.3 mục 8, 9: `tool_result` ghép đúng `tool_use_id`; ngoại lệ tool → `{"type":"tool_result","is_error":true,"content":"Lỗi: <tên lớp>"}`; `GatewayError(deadline)` → `time_budget`
  - Expect: `cmd.test_one` erp_ai/agent/test_runner.py → test_stops_after_max_turns (stub luôn `tool_use` → đúng 8 bản ghi `reason`, bản cuối `max_turns`), test_turn_log_fields (chi phí so với số tính tay), test_l1_applies_mapping_confidence_and_hint (đủ cả hướng giải quyết) xanh. Điểm kiểm CP-4: `cmd.test` xanh

## Handler, scheduler, báo cáo, eval

- [ ] T31 — Handler: điều kiện xếp job cho phiếu và comment — files: erp_ai/handlers.py, erp_ai/hooks.py, erp_ai/tests/test_handlers.py — test: erp_ai/tests/test_handlers.py — depends: T2, T20
  - Criterion: AC-5(a)–(e), AC-4 (agent tắt → 0 job, 0 lời gọi), NFR-1 (không gọi model trong luồng lưu), NFR-4
  - Receives: `policy.is_enabled`, `can_send_ticket`, `contains_keyword`, `queue.enqueue_agent_run`
  - Returns: `ticket_before_insert(doc, method=None)` (cờ `erp_ai_prefilled`), `ticket_after_insert` thay điều kiện tạm của T1 bằng `policy.*`, `comment_after_insert(doc, method=None)`; `hooks.py`: `before_insert`, `comment after_insert`; mỗi quyết định → `frappe.logger(LOGGER_NAME).info` không chứa nội dung phiếu
  - Expect: `cmd.test_one` erp_ai/tests/test_handlers.py → test_disabled_agent_new_ticket_no_job_no_model_call, test_new_unclassified_ticket_enqueues_one_job (kể cả khi Helpdesk tự điền mặc định), test_prefilled_ticket_no_job, test_agent_created_ticket_and_comment_no_job, test_comment_keyword_case_insensitive, test_opt_out_or_excluded_team_no_job_no_model_call, test_save_ticket_and_comment_make_no_model_call xanh

- [ ] T32 — Handler: ghi nhận người sửa phân loại — files: erp_ai/handlers.py, erp_ai/hooks.py, erp_ai/tests/test_handlers.py — test: erp_ai/tests/test_handlers.py — depends: T22, T31
  - Criterion: AC-11 (người sửa → nhật ký gần nhất lưu giá trị, "phân loại bởi" thành Người; agent sửa thì không), ADR-004 #5
  - Receives: `ERP AI Log` có bản ghi `classify`
  - Returns: `ticket_validate(doc, method=None)`, `ticket_on_update(doc, method=None)`; `human_corrected_at` chỉ đặt lần đầu; ghi bằng `frappe.db.set_value(..., update_modified=False)`; `hooks.py`: `validate`, `on_update`
  - Expect: `cmd.test_one` erp_ai/tests/test_handlers.py → test_human_correction_updates_latest_log (sửa 2 lần → giá trị cuối, `human_corrected_at` lần đầu), test_agent_correction_not_recorded xanh

- [ ] T33 — Job hằng ngày: tính lại chi phí tháng — files: erp_ai/tasks.py, erp_ai/hooks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T20, T22, T32
  - Criterion: AC-16 (cộng chi phí; vượt ngân sách → mức hiệu lực lùi; đầu tháng reset), D-19
  - Receives: `ERP AI Log.cost_usd`, `credential_label`
  - Returns: `tasks.recompute_monthly_spend(now=None) -> None`; `hooks.py`: `scheduler_events.daily`
  - Expect: `cmd.test_one` erp_ai/tests/test_tasks.py → test_recompute_spend_from_log (tổng chung + theo khóa), test_month_start_resets_to_zero xanh

- [ ] T34 — Job hằng ngày: kiểm nâng quyền — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T14, T33
  - Criterion: AC-18 (role ≠ {ERP AI Agent, Agent}; bản ghi phân quyền do agent sửa; Server Script/Webhook do agent tạo đang bật; khóa bật mà rỗng)
  - Receives: `alerts.send_alarm`
  - Returns: `tasks.check_privilege_escalation() -> None` (một báo động cho mỗi điều kiện đúng; liệt kê ≤ 5 tên; không giải mã khóa)
  - Expect: `cmd.test_one` erp_ai/tests/test_tasks.py → test_alarm_on_role_drift, test_alarm_on_permission_records_modified_by_agent, test_alarm_on_enabled_server_script_or_webhook_by_agent, test_alarm_on_enabled_key_without_secret (không có điều kiện → 0 email) xanh

- [ ] T35 — Job mỗi giờ: dò lại khóa hết hạn mức — files: erp_ai/tasks.py, erp_ai/hooks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T18, T34
  - Criterion: AC-18 (chỉ dò `Hết hạn mức`; hồi phục → `Hoạt động` + 1 email tin)
  - Receives: `gateway.reprobe_exhausted_keys()`
  - Returns: `tasks.reprobe_exhausted_keys() -> None`; `hooks.py`: `scheduler_events.hourly`
  - Expect: `cmd.test_one` erp_ai/tests/test_tasks.py → test_reprobe_only_exhausted_keys xanh

- [ ] T36 — Nút "Kiểm tra khóa" (`check_keys`) — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T9, T18
  - Criterion: AC-19 (chỉ System Manager gọi được; kết quả từng khóa; `label` lạ → lỗi)
  - Receives: `gateway.probe_credential`
  - Returns: `check_keys(label: str | None = None) -> list[dict]` (`@frappe.whitelist()`, `frappe.only_for("System Manager")` trước mọi việc, không `.save()` cấu hình, không trả văn bản ngoại lệ); `.js`: nút gọi `check_keys`, hiện bảng, `frm.reload_doc()`
  - Expect: `cmd.test_one` erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py → test_check_keys_system_manager_only_and_per_key_result (HD Agent → `PermissionError`; `label` lạ → `ValidationError`) xanh

- [ ] T37 — Eval: xuất phiếu đã gán nhãn — files: erp_ai/eval/export_tickets.py, erp_ai/eval/test_export_tickets.py — test: erp_ai/eval/test_export_tickets.py — depends: T5, T20
  - Criterion: AC-2, A-9, NFR-4
  - Receives: `policy.can_send_ticket`
  - Returns: `export_tickets.export(path: str) -> int` (JSONL, mỗi dòng đúng 6 khóa `subject, description, ticket_type, agent_group, priority, owner`; không ghi file đính kèm; `path` trong thư mục repo của app → `ValueError("Không ghi dữ liệu phiếu vào repo")`)
  - Expect: `cmd.test_one` erp_ai/eval/test_export_tickets.py → test_export_skips_excluded_team (3 phiếu, 1 loại trừ → 2 dòng), test_export_skips_opt_out_and_runs_when_disabled, test_export_refuses_path_inside_repo xanh

- [ ] T38 — Eval: chạy phân loại bằng chính prompt của runner — files: erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py — test: erp_ai/eval/test_run_eval.py — depends: T3, T5, T17
  - Criterion: AC-1 (in báo cáo đủ), AC-3 (cùng một prompt với runner), D-22 (không ghi `ERP AI Log`)
  - Receives: `build_classify_request`, `parse_classification`, `gateway.call_model`, `compute_metrics`, `format_report` (T5)
  - Returns: `run_eval.run(path: str) -> dict` (dòng đã có `predicted_category` thì không gọi cổng)
  - Expect: `cmd.test_one` erp_ai/eval/test_run_eval.py → test_run_uses_given_predictions_without_gateway, test_eval_and_runner_share_classify_request (request của runner == của eval cùng phiếu; đặt trong file này thay cho `test_classification.py` để không chung file với T3 và khỏi chạy ngược chiều phụ thuộc) xanh

- [ ] T39 — Report ERP AI Accuracy [migrate] — files: erp_ai/erp_ai_agent/report/__init__.py, erp_ai/erp_ai_agent/report/erp_ai_accuracy/__init__.py, erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.json, erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.py, erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.js, erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py — test: erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py — depends: T32, T38
  - Ghi chú: 6 file do __init__.py và .js là mẫu bắt buộc của Frappe; logic nằm ở một file `.py`.
  - Criterion: AC-12, A-12, D-17, NFR-9 (phép đo)
  - Receives: `test_utils.make_log_entry` (T22)
  - Returns: `execute(filters: dict) -> tuple[list, list]`; bộ lọc `from_date`, `to_date`; cột `category`, `predictions`, `corrected`, `pending`, `accuracy_pct`; 6 dòng A–F + `Tổng`; mẫu = 0 → trống
  - Expect: `cmd.migrate` exit 0, rồi `cmd.test_one` → test_accuracy_ten_log_sample (10 bản ghi, đáp số tính tay; sửa sau 7 ngày không tính; sửa về đúng giá trị dự đoán không tính sửa; mẫu = 0 → trống) xanh

## Kiểm kiến trúc và CI

- [ ] T40 — Test kiến trúc (quét mã) và CI — files: erp_ai/tests/test_architecture.py, .github/workflows/ci.yml — test: erp_ai/tests/test_architecture.py — depends: T30, T35, T36, T38, T39
  - Criterion: ADR-001..005, NFR-1, NFR-5, DoD "CI xanh" (D-23)
  - Receives: toàn bộ cây `erp_ai/**`
  - Returns: test_layer_imports, test_single_enqueue_call_site, test_no_save_on_settings_in_product_code, test_tools_never_bypass_permissions, test_subprocess_only_in_source_tool, test_level_and_send_policy_fields_only_in_policy, test_handlers_do_not_import_gateway_or_runner, test_secret_handling_rules, test_ci_installs_required_apps (đọc `ci.yml`: có `helpdesk` tag `v15.1.0`, `erpnext` `version-15`, `telephony`, `bench init` nhánh `version-15`); `ci.yml` cài thêm các app đó trước `install-app erp_ai`, không nâng version action
  - Expect: `cmd.test_one` erp_ai/tests/test_architecture.py → các test trên xanh; `cmd.test` toàn app xanh; `cmd.lint` sạch; `grep` các dấu skip trong `test.skip_markers` → rỗng (điểm kiểm CP-5, cuối build)
