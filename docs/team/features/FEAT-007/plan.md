Feature: FEAT-007
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-007 — đợt 0 (U0, U4a, U5a, U6a)

- Nhánh feature: `team/FEAT-007` từ `develop` @ `1918db2` (`config.base_branch` = `main` không có trong repo; `design.md` và luật dự án lấy `develop`). Build trong worktree riêng, không checkout ở cây chính, không ghi `.team/current.json` (DoD của spec).
- Số task: 58 (T1–T55 làm ngay; T56–T58 chờ `team/FEAT-004` vào `develop`); song song tối đa: 2 (`limits.max_parallel_dev`).
- Phạm vi: chỉ đợt 0 của `arch-impact.md`. Đợt 1, 2 (U1–U3, U4b, U5b, U6b, U7, U8) lập kế hoạch sau bằng `/team:plan FEAT-007 --insert` khi có `design-addendum-N.md`.
- Đầu vào: `spec.md` + `spec-addendum-1.md`; `design.md`; `design-w0-fixes.md` (thắng `design.md`); `arch-review-design-w0-r2.md` (approve kèm C-1 → T42, C-2 → T9).
- Cổng: `team.py status` chỉ áp G5; G3 không áp dụng.

## Thứ tự
1. **T1 (bộ khung)** một mình; chưa task nào khác bắt đầu trước khi review T1 `approve`.
2. **Chuỗi U0** T2 → T3 → T4 → T5 và T6 → T7 → T8 → T10 → … → T20 (cùng `erp_ai_setting.json/.py`, `test_erp_ai_setting.py`, `test_doctype_descriptions.py` nên bắt buộc nối tiếp), rồi T21 → T22 → T23. Phần Log (T3–T5) đặt sớm vì T4 đóng cửa sổ tràn 64 KB (F-6) và T28, T31, T55 cần nó.
3. **Việc thuần, không cần trường cấu hình** chạy song song với chuỗi U0 ngay sau T1: T9, T24 → T25 → T26, T27, T35 → T36, T37, T40, T41, T42 → T44. Đây là lệch có lý do so với câu "U0 trước mọi đơn vị" của `design.md:87`: các task này không đọc trường nào của U0 (phụ thuộc lấy từ luồng dữ liệu), và rủi ro lớn nhất của đợt (ghim `test_architecture.py`, T42) được thử sớm.
4. **Việc cần trường của U0**: T28 → T31 (sau T3, T5); T32 (sau T20, T29); T33 → T34 (sau T18); T38 → T39 (sau T14); T43 → T45 … T50 (sau T19); T51 → T54 (sau T16, T26); T55 (sau T5).
5. **Hòa nhập** T56 → T57, T58 sau khi `team/FEAT-004` vào `develop`. `team/FEAT-007` không vào `develop` trước khi T57, T58 tick (`design-w0-fixes.md:214`).

## Nhóm song song
Hai làn, mỗi làn một dev; bộ điều phối của build chọn task sẵn sàng không chung file với task đang chạy.
- Làn A (chuỗi U0): T1 → T2 → T3 → T4 → T5 → T7 → T8 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T32 (T6 chen sau T2; T21 → T22 → T23 chen sau T18).
- Làn B: T9, T24–T27, T35–T37, T40–T42, T44 trước; rồi T28–T31, T33, T34, T38, T39, T43, T45–T55 khi phụ thuộc đã tick.
- Không bao giờ song song: hai task `[migrate]` (22 task: T1–T5, T7, T8, T10, T12–T14, T16, T18, T19, T31, T34, T40, T43, T44, T48, T49, T55; T56 cũng chạy `cmd.migrate` nên tính như một task `[migrate]`); hai task chung file (bảng dưới).

## Ràng buộc chung
Chép nguyên văn từ `design.md` / `design-w0-fixes.md`; mọi task thừa hưởng.
- Khối hằng cuối `erp_ai/constants.py` (T8), file giữ là module lá:
  - `ACTION_CREATE_USER = "Tạo tài khoản theo mẫu"`, `ACTION_ADD_TEAM_MEMBER = "Thêm người vào nhóm Helpdesk"`, `ACTION_ADD_HOLIDAY = "Thêm ngày nghỉ"`, `ACTION_SET_ITEM_GROUP = "Đổi nhóm hàng"`, `ACTION_CREATE_CUSTOM_FIELD = "Tạo Custom Field"`, `ACTION_UPDATE_FIELDS = "Đổi trường"`; `CATALOG_ACTIONS` = tuple 6 hằng theo thứ tự đó.
  - `MODE_DENY = "Cấm"`, `MODE_NEEDS_APPROVAL = "Cần duyệt"`, `MODE_AUTO = "Tự làm"`; `CATALOG_MODES = (MODE_DENY, MODE_NEEDS_APPROVAL, MODE_AUTO)`.
  - `KPI_IDS = ("first_response_minutes", "complete_fields_pct", "closed_without_human_pct", "b_resolution_hours", "c_task_in_3_days_pct", "stale_over_5_days")`.
  - `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "HD Ticket Comment", "Comment", "Communication", "File")`.
- `hard_ban_reason(doctype: str) -> str | None` ở `erp_ai/agent/hard_bans.py`; chỉ import `frappe`, `erp_ai.agent.tools.read`, `erp_ai.agent.tools.site_api`; `erp_ai/agent/policy.py` không import nó.
- Chiều phụ thuộc (ADR-001): không file nào dưới `erp_ai/agent/**` import `erp_ai.erp_ai_agent.*`. Tên ở lại controller/report, Lõi không dùng: `PROMPT_REQUIRED_MARKERS`, `PROMPT_OVERRIDE_MAX_CHARS`, `INT_LIMITS`, `l0_l1_gate`, `GateResult`, `GATE_*`.
- Xếp hàng (ADR-003/013, ADR-033 QĐ 6): mọi `frappe.enqueue` ở `erp_ai/agent/queue.py`; `SCHEDULED_JOB_TIMEOUT_S = 1200`; ba lời gọi `queue="long"`, `enqueue_after_commit=True`, `deduplicate=True`, không kwarg khác:

  | Hàm ở `queue.py` | Đích | `job_id` | Hàm `cron` ở `schedules.py` | Lịch |
  |---|---|---|---|---|
  | `enqueue_daily_report_job` | `erp_ai.agent.daily_report.run_daily_report` | `erp_ai::daily_report` | `enqueue_daily_report` | `0 8 * * *` |
  | `enqueue_weekly_kpi_job` | `erp_ai.agent.kpi.run_weekly_kpi` | `erp_ai::weekly_kpi` | `enqueue_weekly_kpi` | `0 8 * * 1` |
  | `enqueue_monthly_review_job` | `erp_ai.agent.monthly_review.run_monthly_review` | `erp_ai::monthly_review` | `enqueue_monthly_review` | `0 8 1 * *` |

- Việc quét: `"*/15 * * * *": ["erp_ai.agent.missed_scan.scan_missed_tickets"]`, xếp hàng qua `queue.enqueue_agent_run(name, TRIGGER_TICKET_INSERT)`.
- ERP AI Setting sau U0: + 49 trường, + 7 section so với nhánh nền (27 → 76 trường, 7 → 14 section trên `develop` @ `1918db2`); thứ tự section và trường theo `design.md:95-110`; mặc định và khoảng theo `design.md:114-151`; mô tả ≤ 400 ký tự với cụm bắt buộc theo `design.md:157-184`.
- ERP AI Log ở đợt 0: + 5 cột, `actions` Long Text, DocPerm `ERP AI Instructor` chỉ `read`, `report`; option `entry_type`, `trigger` và `run_log.ENTRY_TYPES` không đổi.
- Trường tự quản: `agent_enabled_at`, `daily_report_sent_on`, `budget_alert_sent_month`, `prompt_revisions`; mỗi mốc đúng một hàm job ghi bằng `frappe.db.set_single_value`, controller khôi phục khi người lưu.
- Một dạng lỗi (D-20): kiểm lúc lưu và hàm Lõi đợt 0 dùng `frappe.throw(msg)`; `article_guard` ném `frappe.PermissionError`.
- Việc theo lịch: nhận `now: datetime | None = None`; 1 dòng `frappe.logger("erp_ai")` mỗi lần chạy; lỗi → `frappe.log_error` với tiêu đề hằng đặt trong module của việc (`TITLE_DAILY_REPORT_FAILED`, `TITLE_KPI_FAILED`, `TITLE_REVIEW_FAILED`), không sửa `constants.py` cho các tiêu đề này.
- Lệnh: chỉ các ô `cmd.test_one`, `cmd.test`, `cmd.lint`, `cmd.migrate`, `cmd.format` của `.team/profile.json`. Cách chạy từ worktree: mục "Chạy test từ worktree trên site dùng chung" ngay dưới.

## Chạy test từ worktree trên site dùng chung
Bench mặc định nạp `erp_ai` từ cây chính (`apps/erp_ai`, đang ở `develop`); cây chính không bị đụng. Site `miyano` là site duy nhất và phiên build FEAT-004 đang dùng nó (`intake.md` N-3: người đã chấp nhận test chập chờn).

**Cách chạy.** Vẫn là các ô `cmd.*` của profile, chỉ đổi hai chỗ (tiền lệ: dòng "Lệnh bench" ở `docs/team/features/FEAT-004/tasks.md:16`):
- `cd ../..` của ô lệnh thay bằng `cd /home/miyano/frappe-bench`, vì từ một worktree `../..` rơi vào `apps/erp_ai/.claude`, không phải thư mục bench.
- Đặt `PYTHONPATH=<gốc worktree>` trước `bench` để Python nạp `erp_ai` của worktree đó thay cho cây chính.

| Việc | Ai chạy | Lệnh |
|---|---|---|
| `cmd.test_one` của một task | dev, từ worktree của task | `cd /home/miyano/frappe-bench && PYTHONPATH=<worktree của dev> bench --site miyano run-tests --module <module của file test>` |
| `cmd.migrate` của task `[migrate]` | dev, từ worktree của task | `cd /home/miyano/frappe-bench && PYTHONPATH=<worktree của dev> bench --site miyano migrate` |
| `cmd.test` sau mỗi lần merge, và M0 | dev được giao (role-policy chặn tech-lead chạy bench) | `cd /home/miyano/frappe-bench && PYTHONPATH=/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 bench --site miyano migrate` rồi cùng tiền tố với `run-tests --app erp_ai` |

Lời bàn giao cho mỗi dev chỉ nêu worktree của chính dev đó (K-14).

**Chứng minh cách chạy có tác dụng (ở T1, chưa kiểm lúc lập kế hoạch).** Test của T1 đỏ khi chạy không có `PYTHONPATH` (cây chính chưa có `site_environment`) và xanh khi có: đó là bằng chứng bench đã nạp mã của worktree. Nếu có `PYTHONPATH` mà vẫn nạp cây chính → dừng, trả `NEEDS_CONTEXT`; không checkout ở cây chính, không đổi cách cài app của bench.

**Không làm phiền phiên build FEAT-004.**
- Không chạy `cmd.install`, `cmd.build`, `cmd.run`, `bench restart`; không sửa `site_config.json`, `apps.txt`; không checkout, commit, stash ở cây chính; không đụng nhánh `team/FEAT-004*` và các worktree của nó; không ghi `.team/current.json`.
- Mỗi lúc FEAT-007 chỉ có một lệnh `migrate` hoặc một `cmd.test` toàn app trên site. Khi hai dev đang chạy, mỗi dev chỉ chạy `cmd.test_one`; `cmd.test` toàn app chạy sau mỗi lần merge, khi không task `[migrate]` nào đang dở.
- Test tự tạo dữ liệu của mình và trả lại cấu hình (`keep_agent_settings`, NFR-7); không xóa bản ghi mình không tạo.
- Một lần đỏ (`QueryDeadlockError`, thiếu trường/DocType vừa thêm): chạy lại `migrate` từ worktree rồi chạy lại riêng module đó trước khi kết luận (DoD của spec dòng 295).

**Phần không tránh được trên một site.** `migrate` từ cây FEAT-007 thêm cột và DocType vào DB dùng chung; `migrate` từ cây FEAT-004 gỡ lại bản ghi DocType mà cây đó không có. Hai phiên cản nhau quá 2 lần → dừng, báo team-leader (bảng Rủi ro, dòng 1).

## Touchpoint → task
Mọi file của `design-w0-fixes.md` mục 5.1, 5.2 và `design.md:560-570, 585-593`. Đường dẫn rút gọn: `S/` = `erp_ai/erp_ai_agent/doctype/erp_ai_setting/`, `D/` = `erp_ai/erp_ai_agent/doctype/`, `R/` = `erp_ai/erp_ai_agent/report/`.

| Đơn vị | File | change | Task |
|---|---|---|---|
| U0 | `S/erp_ai_setting.json` | sửa | T1, T2, T7, T10, T12, T13, T14, T16, T18, T19, T56 |
| U0 | `S/erp_ai_setting.py` | sửa | T6, T7, T10–T20, T32, T56 |
| U0 | `S/erp_ai_setting.js` | sửa | T20 |
| U0 | `D/erp_ai_catalog_rule/*` | mới | T8 |
| U0 | `D/erp_ai_user_template/*` | mới | T12 |
| U0 | `D/erp_ai_prompt_revision/*` | mới | T19 |
| U0 | `erp_ai/constants.py` | sửa | T8 |
| U0 | `erp_ai/agent/hard_bans.py` | mới | T9, T57 |
| U0 | `erp_ai/install.py` | sửa | T21, T22 |
| U0 | `D/erp_ai_log/erp_ai_log.json` | sửa | T3, T4, T5 |
| U0 | `S/test_erp_ai_setting.py` | sửa | T1, T2, T6, T7, T8, T10–T20, T32, T57 |
| U0 | `erp_ai/agent/test_hard_bans.py` | mới | T9, T57 |
| U0 | `D/erp_ai_log/test_erp_ai_log.py` | sửa | T4, T5 |
| U0 | `erp_ai/tests/test_install.py` | sửa | T2, T5, T21, T22, T23 |
| U0, U5a | `erp_ai/tests/test_doctype_descriptions.py` | sửa | T1, T2, T3, T7, T8, T10, T12, T13, T14, T16, T18, T19, T43, T49, T56 |
| U0 | `erp_ai/test_utils.py` | sửa | T1 |
| U4a | `erp_ai/agent/missed_scan.py`, `test_missed_scan.py` | mới | T33, T34 |
| U4a, U5a, U6a | `erp_ai/hooks.py` | sửa | T40, T44, T34 |
| U4a | `R/erp_ai_accuracy/erp_ai_accuracy.py` | sửa | T28, T29, T30 |
| U4a | `R/erp_ai_accuracy/erp_ai_accuracy.json` | sửa | T31 |
| U4a | `R/erp_ai_accuracy/test_erp_ai_accuracy.py` | sửa | T28, T29, T30, T31 |
| U4a | `erp_ai/agent/routing.py`, `test_routing.py` | sửa | T24, T25, T26 |
| U4a | `erp_ai/agent/classification.py`, `test_classification.py` | sửa | T27 |
| U5a | `erp_ai/schedules.py`, `erp_ai/tests/test_schedules.py` | mới | T44 |
| U5a | `erp_ai/agent/queue.py`, `test_queue.py` | sửa | T42 |
| U5a | `erp_ai/tests/test_architecture.py` | sửa | T42, T56 |
| U5a | `erp_ai/agent/ops_data.py`, `test_ops_data.py` | mới | T41 |
| U5a | `erp_ai/agent/daily_report.py`, `test_daily_report.py` | mới | T51, T52, T53, T54 |
| U5a | `erp_ai/agent/kpi.py`, `test_kpi.py` | mới | T45, T46, T47 |
| U5a | `erp_ai/agent/monthly_review.py`, `test_monthly_review.py` | mới | T50 |
| U5a | `D/erp_ai_kpi_week/*`, `test_erp_ai_kpi_week.py` | mới | T43, T58 |
| U5a | `D/erp_ai_review_month/*`, `D/erp_ai_review_item/*`, `test_erp_ai_review_month.py` | mới | T49, T58 |
| U5a | `R/erp_ai_kpi_weekly/*`, `test_erp_ai_kpi_weekly.py` | mới | T48 |
| U5a | `R/erp_ai_cost/*`, `test_erp_ai_cost.py` | mới | T55 |
| U6a | `erp_ai/agent/redact.py`, `test_redact.py` | mới | T35 |
| U6a | `erp_ai/agent/system_read.py`, `test_system_read.py` | mới | T36 |
| U6a | `erp_ai/agent/knowledge.py`, `test_knowledge.py` | mới | T37, T39 |
| U6a | `erp_ai/agent/article_guard.py`, `test_article_guard.py` | mới | T40 |
| U6a | `erp_ai/agent/tools/source.py`, `test_source.py` | sửa | T38 |

Thêm ngoài bảng touchpoint của thiết kế (một file): `erp_ai/tests/test_test_utils.py` (sửa, T1) — test của chính `keep_agent_settings`; file này đã là nơi test các hàm của `test_utils.py`. Đã kiểm: mọi file "sửa" có trên `develop` @ `1918db2`; mọi file "mới" chưa có và nằm dưới `erp_ai/` (`structure.allowed_new_file_roots`); không đường dẫn nào khớp `protected_paths`.

## Một file, một chủ
Chỉ liệt kê file có từ hai task trở lên; file còn lại có đúng một task.

| File | Task chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| `S/erp_ai_setting.json` | T1 | T2, T7, T10, T12, T13, T14, T16, T18, T19, T56 | theo số |
| `S/erp_ai_setting.py` | T6 | T7, T10–T20, T32, T56 | theo số |
| `S/test_erp_ai_setting.py` | T1 | T2, T6, T7, T8, T10–T20, T32, T57 | theo số |
| `erp_ai/tests/test_doctype_descriptions.py` | T1 | T2, T3, T7, T8, T10, T12, T13, T14, T16, T18, T19, T43, T49, T56 | theo số |
| `erp_ai/tests/test_install.py` | T2 | T5, T21, T22, T23 | T2 → T5 → T21 → T22 → T23 |
| `erp_ai/install.py` | T21 | T22 | T21 → T22 |
| `D/erp_ai_log/erp_ai_log.json` | T3 | T4, T5 | T3 → T4 → T5 |
| `D/erp_ai_log/test_erp_ai_log.py` | T4 | T5 | T4 → T5 |
| `erp_ai/agent/hard_bans.py`, `test_hard_bans.py` | T9 | T57 | T9 → T57 |
| `erp_ai/agent/routing.py`, `test_routing.py` | T24 | T25, T26 | T24 → T25 → T26 |
| `R/erp_ai_accuracy/erp_ai_accuracy.py` | T28 | T29, T30 | T28 → T29 → T30 |
| `R/erp_ai_accuracy/test_erp_ai_accuracy.py` | T28 | T29, T30, T31 | T28 → T29 → T30 → T31 |
| `erp_ai/agent/missed_scan.py`, `test_missed_scan.py` | T33 | T34 | T33 → T34 |
| `erp_ai/hooks.py` | T40 | T44, T34 | T40 → T44 → T34 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` | T37 | T39 | T37 → T39 |
| `erp_ai/tests/test_architecture.py` | T42 | T56 | T42 → T56 |
| `erp_ai/agent/kpi.py`, `test_kpi.py` | T45 | T46, T47 | T45 → T46 → T47 |
| `D/erp_ai_kpi_week/erp_ai_kpi_week.py`, `test_erp_ai_kpi_week.py` | T43 | T58 | T43 → T58 |
| `D/erp_ai_review_month/erp_ai_review_month.py`, `test_erp_ai_review_month.py` | T49 | T58 | T49 → T58 |
| `erp_ai/agent/daily_report.py`, `test_daily_report.py` | T51 | T52, T53, T54 | T51 → T52 → T53 → T54 |

## AC → task (đợt 0)
Danh sách AC đợt 0 theo `design-w0-fixes.md` mục 6.4. Phần còn lại của mỗi AC ở đơn vị đợt sau: bảng `design.md:24-36`. 61 AC của FEAT-007 trừ các AC dưới đây chưa có task (đợt 1, 2).

| Tiêu chí | Task |
|---|---|
| AC-1 | T2 |
| AC-4 (form) | T6 |
| AC-12 | T1 |
| AC-16 | T18, T21, T33, T34 |
| AC-17 | T30 |
| AC-18 | T29, T32 |
| AC-19 | T3, T28 |
| AC-20 | T5, T31, T48, T55 |
| AC-22 (cấu hình, trường) | T7, T22 |
| AC-24 | T13 |
| AC-25 | T24 |
| AC-26 | T16, T26, T51 |
| AC-27 | T16, T25 |
| AC-28 | T27 |
| AC-29 | T8, T10, T11, T57 |
| AC-30 | T12 |
| AC-31 | T7 |
| AC-36 | T7 |
| AC-38 | T19, T20 |
| AC-44 | T14 |
| AC-45 (chặn) | T22, T40 |
| AC-46 | T14, T37 |
| AC-47 | T14, T38, T39 |
| AC-49 | T15 |
| AC-50 | T36 |
| AC-51 | T16, T44, T51, T52 |
| AC-52 | T41, T53, T54 |
| AC-53 | T45 |
| AC-54 | T46 |
| AC-55 | T17, T43, T47 |
| AC-56 | T48 (+ kiểm màn hình thật ở verify) |
| AC-59 | T16, T49, T50 |
| AC-60 | T55 |
| AC-63 (cấu hình) | T16 |
| NFR-4 | mọi task sửa `erp_ai_setting.json` (`test_every_new_field_default`), chốt ở T19 |
| NFR-6 | T35, T36, T53 |
| NFR-7 | T1 (+ `cmd.test` hai lần liên tiếp ở verify) |
| NFR-8 | T2, T5, T28, T42 (lý do sửa test ghi trong commit) |
| STD-OPS-2 | T23 (+ đối soát lên/xuống thật ở verify) |
| ADR-001 / F-1 | T8, T9 |
| ADR-031 / F-3, C-2 | T9, T57 |
| ADR-003, ADR-013, ADR-033 QĐ 6 / F-2, C-1 | T42, T44 |
| ADR-033 QĐ 8, M5 / F-4 | T58 |
| D-5, D-6 / F-5, F-6 | T3, T4, T5 |

## Mốc kiểm
Sau mỗi lần merge một task: `cmd.test` trên `team/FEAT-007` (luật của build). Thêm các mốc:

| Mốc | Sau task | Kiểm |
|---|---|---|
| M0 | trước T1 | `cmd.test` trên đầu nhánh, ghi dòng `baseline:` của `tasks.md` |
| M1 | T5 | `cmd.test`, `cmd.lint`; luồng chính: lưu form ERP AI Setting dưới System Manager không lỗi; tài khoản chỉ có ERP AI Instructor mở được Report View của ERP AI Log |
| M2 | T12 | `cmd.test`, `cmd.lint`; lưu một dòng danh mục hợp lệ và một dòng trỏ `Custom Role` (bị chặn) |
| M3 | T23 và T32 | U0 xong: `cmd.test`, `cmd.lint`; `cmd.migrate` lần hai không đổi `tabSingles` |
| M4 | T34, T39 | U4a, U6a xong: `cmd.test`, `cmd.lint`; `frappe.get_hooks("scheduler_events")["cron"]` có dòng `*/15` |
| M5 | T55 | đợt 0 trước hòa nhập: `cmd.test`, `cmd.lint`; gọi tay `run_daily_report`, `run_weekly_kpi`, `run_monthly_review` hai lần, lần hai không tạo thêm email/dòng |
| M6 | T58 | cửa merge: `cmd.test`, `cmd.lint` xanh trên nhánh đã gộp `develop`; rồi `/team:verify FEAT-007` (đối soát migrate (a)–(d) của `design.md:530`, ảnh màn hình AC-56) |

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Site `miyano` dùng chung với phiên build FEAT-004 ở worktree khác: 22 task `[migrate]` của FEAT-007 (và T56) đồng bộ meta từ cây FEAT-007; `cmd.migrate` từ cây FEAT-004 đồng bộ ngược và `remove_orphan_doctypes` xóa bản ghi DocType mới của FEAT-007 | test FEAT-007 đỏ vì thiếu trường/DocType vừa thêm; test FEAT-004 đỏ vì meta lạ; `QueryDeadlockError` khi hai `cmd.test` chạy cùng lúc | Trước mỗi `cmd.test_one` của task `[migrate]` và trước mỗi `cmd.test`: chạy lại `cmd.migrate` từ cây FEAT-007. Hai task `[migrate]` không song song. Team-leader xếp cửa sổ dùng site giữa hai phiên; đỏ do deadlock thì chạy lại riêng module trước khi kết luận (DoD của spec). Nếu hai phiên cản nhau quá 2 lần: dừng, báo team-leader (cần quyết định của người: site thứ hai hoặc chạy luân phiên) |
| `test_architecture.py` (T42) xung đột chữ với `team/FEAT-004` (+802 dòng) và FEAT-005 T14 | xung đột khi gộp ở T56 | T42 chỉ sửa đúng các chỗ của F-2 và C-1; T56 gộp tay, giữ phần hai nhánh kia |
| Chuỗi U0 dài 22 task (T1–T23 trừ T9), phần lớn trên cùng 4 file | làn A chậm, làn B hết việc không cần U0 | Làn B có 12 task không cần U0; phần Log và T16, T18 đứng trước các task U4a/U5a cần chúng |
| `DOCTYPE_CONFIG` / luật quét khác của `test_architecture.py` (`POLICY_FIELDS`, `DEFAULT_PEOPLE`, quy tắc `agent/tools/**`) chặn mã mới | `cmd.test_one` của `test_architecture.py` đỏ ở task thêm file `.py` | Mỗi task thêm `.py` chạy file đó; không qua được trong `files:` → `DESIGN_CONFLICT`, không sửa luật |
| FEAT-004 chưa vào `develop` khi T1–T55 xong | T56 chưa có điều kiện | Ghi chữ chặn ở T56, báo team-leader; `arch-impact.md` đã nêu lựa chọn tách U4a + U5a thành feature riêng |
| T59 của FEAT-004 không còn công khai tập DocType phân quyền | `site_api.PERMISSION_DOCTYPES` không có ở T57 | Dừng, `DESIGN_CONFLICT` với ADR-031 (`design-w0-fixes.md:214`) |
| Giữa lúc đợt 0 vào `develop` và U1, mô tả ô (4) nói khác hành vi mã cũ (A-D1) | người đọc form trên site dev hiểu nhầm | Đã chấp nhận trong thiết kế; production chỉ nhận cả feature qua G5 |
| `design-addendum-1-U1.md:63` muốn U0 thêm `"do_tin_cay_pct"` vào `PROMPT_REQUIRED_MARKERS["classify"]`, nhưng `CLASSIFY_PROMPT` chỉ có khóa này từ U1 (`prompts.py` không phải touchpoint đợt 0) | thêm ở T19 thì `test_builtin_prompts_pass_required_markers` đỏ | T19 giữ 11 khóa của `design.md:314`. Khóa thứ 12 đi cùng commit của U1 sửa `CLASSIFY_PROMPT` (cùng nguyên tắc với F-5: giá trị ghim đổi cùng commit với mã). Cần team-leader xác nhận chủ là U1 khi lập kế hoạch đợt 1; không đưa vào lời bàn giao build đợt 0 |
| Sau `migrate` của T34, T44, bảng Scheduled Job Type của site có việc trỏ tới `erp_ai.agent.missed_scan`, `erp_ai.schedules`, là module cây chính chưa có; nếu scheduler của bench đang chạy thì worker (nạp mã cây chính) báo lỗi import mỗi 15 phút (suy từ cách Frappe đồng bộ việc theo lịch, chưa kiểm trên site) | Error Log / Scheduled Job Log của site có lỗi `ModuleNotFoundError` của `erp_ai` | Kiểm ở M4: đọc Scheduled Job Log sau T34. Có lỗi lặp → báo team-leader trước khi làm T44; không tắt scheduler, không sửa bản ghi của site khi chưa có quyết định |
| `max_agents_per_feature.L` = 10, đợt 0 có 58 task | bộ đếm agent của feature vượt trần | Việc của team-leader khi lập lịch build |

## Walking skeleton (cỡ L)
T1 đi một đường mỏng qua mọi tầng mà đợt 0 dựa vào, với phần lõi là một trường duy nhất: JSON DocType (`site_environment` trong section mới) → `cmd.migrate` trên site dùng chung từ worktree của nhánh → `install._ensure_default_settings` điền mặc định → controller lưu form → bộ kiểm mô tả (`DOCTYPE_CONFIG`) → hàm trả lại cấu hình cho test (`keep_agent_settings`). Bằng chứng: `cmd.test_one` với `test_erp_ai_setting.py::TestFeat007Defaults::test_site_environment_default_production_and_options` xanh sau khi đã đỏ vì chưa có trường. T1 chưa đi qua Cửa vào lịch → `queue.py` → job; đường đó được thử sớm nhất ở T42 → T44 (làn B, ngay sau T1).

## Trọng tâm review
Đầu vào và kiểu lỗi mà spec/thiết kế ngụ ý nhưng bảng test của thiết kế chưa nêu tên; đã thêm test vào task chủ.

| # | Đầu vào / kiểu lỗi | Test thêm | Task |
|---|---|---|---|
| 1 | Site đã bật agent trước khi nâng cấp: `agent_enabled_at` rỗng thì việc quét không bao giờ chạy | `test_install.py::TestFeat007Migrate::test_agent_enabled_at_filled_once_when_enabled` | T21 |
| 2 | Hai trường tùy biến mới (`design.md:249-250`) không có test; HD Article chưa cài | `::test_confidence_pct_field_installed`, `::test_article_source_field_installed_idempotent`, `::test_article_field_skipped_when_doctype_missing` | T22 |
| 3 | Mục "việc bot làm" và chi phí hôm qua của báo cáo 08:00 không có trong `test_twelve_tickets_sections` | `test_daily_report.py::TestBuild::test_bot_actions_and_cost_yesterday` | T52 |
| 4 | Hai lần chạy job 08:00 chồng nhau (khóa file bận) | `test_daily_report.py::TestRun::test_lock_busy_returns_without_email` | T54 |
| 5 | Từ khóa Error Log chứa `%`, `_`, hoặc dài 1 / 101 ký tự (STD-SEC-3) | `test_system_read.py::TestErrorLogs::test_keyword_wildcards_escaped_and_length_bounds` | T36 |
