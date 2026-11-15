Feature: FEAT-007
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-007 — đợt 0 (U0, U4a, U5a, U6a)

- Nhánh feature: `team/FEAT-007` từ `develop` @ `1918db2` (`config.base_branch` = `main` không có trong repo; `design.md` và luật dự án lấy `develop`). Build trong worktree riêng, không checkout ở cây chính, không ghi `.team/current.json` (DoD của spec).
- Số task: 62 (T1–T55, T59–T62 làm ngay; T56–T58 chờ `team/FEAT-004` vào `develop`); song song tối đa: 2 (`limits.max_parallel_dev`). T59, T60 do lần chèn 1 thêm (mục "Chèn 1"); T61, T62 do lần chèn 2 thêm (mục "Chèn 2" cuối file, theo `design-w0-fixes-2.md`, file thắng `design.md` và `design-w0-fixes.md`).
- Phạm vi: chỉ đợt 0 của `arch-impact.md`. Đợt 1, 2 (U1–U3, U4b, U5b, U6b, U7, U8) lập kế hoạch sau bằng `/team:plan FEAT-007 --insert` khi có `design-addendum-N.md`.
- Đầu vào: `spec.md` + `spec-addendum-1.md`; `design.md`; `design-w0-fixes.md` (thắng `design.md`); `arch-review-design-w0-r2.md` (approve kèm C-1 → T42, C-2 → T9).
- Cổng: `team.py status` chỉ áp G5; G3 không áp dụng.

## Thứ tự
1. **T1 (bộ khung)** một mình; chưa task nào khác bắt đầu trước khi review T1 `approve`.
2. **Chuỗi U0** T2 → T3 → T4 → T5 và T6 → T7 → T8 → T10 → … → T20 (cùng `erp_ai_setting.json/.py`, `test_erp_ai_setting.py`, `test_doctype_descriptions.py` nên bắt buộc nối tiếp), rồi T21 → T22 → T60 → T23. **T59** vào vòng build đầu tiên sau T1 (không chung file với task sẵn sàng nào), để các task sau đọc `cmd.test` trên nền xanh. Phần Log (T3–T5) đặt sớm vì T4 đóng cửa sổ tràn 64 KB (F-6) và T28, T31, T55 cần nó.
3. **Việc thuần, không cần trường cấu hình** chạy song song với chuỗi U0 ngay sau T1: T9, T24 → T25 → T26, T27 → T62, T35 → T36, T37, T40, T41, T42, T61 (T44 không còn ở nhóm này: chèn 2 dời nó ra sau T34, T47, T50, T54). Đây là lệch có lý do so với câu "U0 trước mọi đơn vị" của `design.md:87`: các task này không đọc trường nào của U0 (phụ thuộc lấy từ luồng dữ liệu), và rủi ro lớn nhất của đợt (ghim `test_architecture.py`, T42) được thử sớm.
4. **Việc cần trường của U0**: T28 → T31 (sau T3, T5); T32 (sau T20, T29); T33 → T34 (sau T18); T38 → T39 (sau T14); T43 → T45 … T50 (sau T19); T51 → T54 (sau T16, T26); T55 (sau T5).
5. **Hòa nhập** T56 → T57, T58 sau khi `team/FEAT-004` vào `develop`. `team/FEAT-007` không vào `develop` trước khi T57, T58 tick (`design-w0-fixes.md:214`).

## Nhóm song song
Hai làn, mỗi làn một dev; bộ điều phối của build chọn task sẵn sàng không chung file với task đang chạy.
- Làn A (chuỗi U0): T1 → T2 → T3 → T4 → T5 → T7 → T8 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 → T19 → T20 → T32 (T6 chen sau T2; T21 → T22 → T60 → T23 chen sau T18).
- Làn B: T59 trước tiên; T9, T24–T27, T35–T37, T40–T42, T61, T62 trước; rồi T28–T31, T33, T34, T38, T39, T43, T45–T55 khi phụ thuộc đã tick; T44 sau cùng của làn (sau T34, T47, T50, T54).
- Không bao giờ song song: hai task `[migrate]` (22 task: T1–T5, T7, T8, T10, T12–T14, T16, T18, T19, T31, T34, T40, T43, T44, T48, T49, T55; T56 cũng chạy `cmd.migrate` nên tính như một task `[migrate]`); hai task chung file (bảng dưới).

## Ràng buộc chung
Chép nguyên văn từ `design.md` / `design-w0-fixes.md`; mọi task thừa hưởng.
- Khối hằng cuối `erp_ai/constants.py` (T8), file giữ là module lá:
  - `ACTION_CREATE_USER = "Tạo tài khoản theo mẫu"`, `ACTION_ADD_TEAM_MEMBER = "Thêm người vào nhóm Helpdesk"`, `ACTION_ADD_HOLIDAY = "Thêm ngày nghỉ"`, `ACTION_SET_ITEM_GROUP = "Đổi nhóm hàng"`, `ACTION_CREATE_CUSTOM_FIELD = "Tạo Custom Field"`, `ACTION_UPDATE_FIELDS = "Đổi trường"`; `CATALOG_ACTIONS` = tuple 6 hằng theo thứ tự đó.
  - `MODE_DENY = "Cấm"`, `MODE_NEEDS_APPROVAL = "Cần duyệt"`, `MODE_AUTO = "Tự làm"`; `CATALOG_MODES = (MODE_DENY, MODE_NEEDS_APPROVAL, MODE_AUTO)`.
  - `KPI_IDS = ("first_response_minutes", "complete_fields_pct", "closed_without_human_pct", "b_resolution_hours", "c_task_in_3_days_pct", "stale_over_5_days")`.
  - `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` (chèn 3: bốn DocType của ADR-034 QĐ 1; chuỗi `"HD Ticket Comment"` và `"reference_ticket"` không xuất hiện trong mã sản phẩm, DocType có trường Link tới HD Ticket được nhận ra qua meta).
- Vị từ "mang nội dung phiếu" (chèn 3, T15): `policy.ticket_link_fieldnames(doctype: str) -> tuple[str, ...]`, `policy.is_ticket_content_doctype(doctype: str) -> bool` ở `erp_ai/agent/policy.py`; controller và tool đợt sau import từ đó, không tự dò meta.
- `decide_route(..., d_watcher: str | None = None)` (chèn 3, T25): `None` = nơi gọi không nói (không ghi chú), chuỗi rỗng sau `strip()` = chưa cấu hình (ghi chú `D_WATCHER_MISSING_NOTE`), chuỗi khác rỗng = xét `is_active_agent`; phân biệt bằng `is None`, không bằng giá trị thật/giả.
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
| U0 | `erp_ai/agent/policy.py`, `test_policy.py` | sửa (chèn 3) | T15 |
| U0 | `erp_ai/install.py` | sửa | T21, T22, T60 |
| nền test (A-18) | `erp_ai/agent/test_agent_runner.py` | sửa | T59, T56 |
| nền test (A-18) | `erp_ai/agent/test_runner_routing.py` | sửa (dự kiến 0 dòng) | T59 |
| U0 | `D/erp_ai_log/erp_ai_log.json` | sửa | T3, T4, T5 |
| U0 | `S/test_erp_ai_setting.py` | sửa | T1, T2, T6, T7, T8, T10–T20, T32, T57 |
| U0 | `erp_ai/agent/test_hard_bans.py` | mới | T9, T57 |
| U0 | `D/erp_ai_log/test_erp_ai_log.py` | sửa | T4, T5 |
| U0 | `erp_ai/tests/test_install.py` | sửa | T2, T5, T21, T22, T60, T23 |
| U0, U5a | `erp_ai/tests/test_doctype_descriptions.py` | sửa | T1, T2, T3, T7, T8, T10, T12, T13, T14, T16, T18, T19, T43, T49, T56 |
| U0 | `erp_ai/test_utils.py` | sửa | T1 |
| U4a | `erp_ai/agent/missed_scan.py`, `test_missed_scan.py` | mới | T33, T34 |
| U4a, U5a, U6a | `erp_ai/hooks.py` | sửa | T40, T34, T44 |
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
| `erp_ai/tests/test_install.py` | T2 | T5, T21, T22, T60, T23 | T2 → T5 → T21 → T22 → T60 → T23 |
| `erp_ai/install.py` | T21 | T22, T60 | T21 → T22 → T60 |
| `erp_ai/agent/test_agent_runner.py` | T59 | T56 | T59 → T56 |
| `D/erp_ai_log/erp_ai_log.json` | T3 | T4, T5 | T3 → T4 → T5 |
| `D/erp_ai_log/test_erp_ai_log.py` | T4 | T5 | T4 → T5 |
| `erp_ai/agent/hard_bans.py`, `test_hard_bans.py` | T9 | T57 | T9 → T57 |
| `erp_ai/agent/routing.py`, `test_routing.py` | T24 | T25, T26 | T24 → T25 → T26 |
| `R/erp_ai_accuracy/erp_ai_accuracy.py` | T28 | T29, T30 | T28 → T29 → T30 |
| `R/erp_ai_accuracy/test_erp_ai_accuracy.py` | T28 | T29, T30, T31 | T28 → T29 → T30 → T31 |
| `erp_ai/agent/missed_scan.py`, `test_missed_scan.py` | T33 | T34 | T33 → T34 |
| `erp_ai/hooks.py` | T40 | T34, T44 | T40 → T34 → T44 (chèn 2, 5d) |
| `erp_ai/test_utils.py`, `erp_ai/tests/test_test_utils.py` | T1 | T61 | T1 → T61 |
| `erp_ai/agent/classification.py`, `test_classification.py` | T27 | T62 | T27 → T62 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` | T37 | T39 | T37 → T39 |
| `erp_ai/tests/test_architecture.py` | T42 | T56 | T42 → T56 |
| `erp_ai/agent/kpi.py`, `test_kpi.py` | T45 | T46, T47 | T45 → T46 → T47 |
| `D/erp_ai_kpi_week/erp_ai_kpi_week.py`, `test_erp_ai_kpi_week.py` | T43 | T58 | T43 → T58 |
| `D/erp_ai_review_month/erp_ai_review_month.py`, `test_erp_ai_review_month.py` | T49 | T58 | T49 → T58 |
| `erp_ai/agent/daily_report.py`, `test_daily_report.py` | T51 | T52, T53, T54 | T51 → T52 → T53 → T54 |
| `erp_ai/agent/policy.py`, `test_policy.py` | T15 | (đợt 1: U1, U2) | T15 trước U1/U2; trong đợt 0 không task nào khác chạm (chèn 3) |

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
| AC-45 câu cuối (quyền đọc của Instructor; phán quyết (1b)) | T60 |
| A-U4b-1 (trường `ai_created_labels`; phán quyết (1)) | T60, T23 |
| A-18 (5 test đỏ sẵn có) | T59 |
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
| M0b | T59 | `cmd.test` trên `team/FEAT-007`: không còn 5 test của dòng `baseline:`; viết lại dòng đó thành "red: không có" kèm đầu ra |
| M1 | T5 | `cmd.test`, `cmd.lint`; luồng chính: lưu form ERP AI Setting dưới System Manager không lỗi; tài khoản chỉ có ERP AI Instructor mở được Report View của ERP AI Log |
| M2 | T12 | `cmd.test`, `cmd.lint`; lưu một dòng danh mục hợp lệ và một dòng trỏ `Custom Role` (bị chặn) |
| M3 | T23 và T32 | U0 xong (gồm T60): `cmd.test`, `cmd.lint`; `cmd.migrate` lần hai không đổi `tabSingles`, không đổi Custom DocPerm của HD Article |
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

## Chèn 1 (2026-11-14, `/team:plan FEAT-007 --insert`)
Hai task thêm vào đợt 0; không task nào đổi số. Các bảng phía trên đã cập nhật.

| Task | Nguồn | Vị trí | Task đổi theo |
|---|---|---|---|
| T59 — năm test đỏ sẵn có tự đặt `auto_assign_enabled` | A-18 (`spec.md:266`, `spec-addendum-1.md:118`); quyết định ở `journal-part5.md:23` | sau T1, làn B, vòng build kế tiếp | T56 `[affected]`: thêm `test_agent_runner.py` vào `files:`, thêm T59 vào `depends:` |
| T60 — task mà thiết kế gọi là "T22a": trường `ai_created_labels`, quyền đọc HD Article cho Instructor | `arch-review-design-w1b.md` mục 4 điểm (1), (1b); `arch-review-design-w1b-r2.md:88` (ii) | sau T22, làn A | T23 `[affected]`: `depends:` T20, T60; thêm test thứ ba cho trường mới |

- **Mã task.** `team.py` nhận dòng task bằng `(T\d+)\b`, nên "T1a", "T22a" không được đếm. Điều kiện bắt đầu của U4b (`design-addendum-1-U4b-U8-fixes.md:126`) và U6b (`design-addendum-1-U6b-fixes.md:341`) ghi "T22a": đọc là T60.
- **Ràng buộc chung thêm.** Trường HD Ticket `ai_created_labels`: Small Text, `hidden`, `read_only`, `no_copy`, permlevel 8, trong `_ai_field_specs`. Quyền HD Article: `setup_custom_perms("HD Article")` trước, rồi một dòng `ERP AI Instructor`, permlevel 0, `read=1`, `report=1`; không sửa dòng nào khác. Hai tài liệu thiết kế không định vị trí của trường trong `_ai_field_specs`; kế hoạch đặt nó ở cuối danh sách để `insert_after` của trường sẵn có không đổi.
- **Phạm vi T59.** Chỉ ghim `auto_assign_enabled=0` ở `RunnerTestBase.setUp`. `keep_agent_settings` không thêm vào lớp này: `addCleanup(frappe.db.rollback)` của lớp đã trả lại cấu hình và lớp cấm commit, nên thêm vào là mã không test nào làm đỏ được (STD-DESIGN-5). Đây là lệch so với chữ "bằng `keep_agent_settings`" của `journal-part5.md:23`.

| Rủi ro của lần chèn | Dấu hiệu | Cách xử lý |
|---|---|---|
| `team/FEAT-004` cũng sửa `test_agent_runner.py` (+299 dòng ở khối import và cuối file); phiên đó đang tránh 5 test đỏ bằng cách tạm đặt `auto_assign_enabled=0` trên site, không sửa test | xung đột ở T56; hoặc phiên kia sửa cùng test theo A-18 `[changed]` | T59 chỉ chạm `setUp` và thêm lớp ngay sau `RunnerTestBase`; T56 nhận file này. Team-leader báo phiên FEAT-004 rằng FEAT-007 đã nhận phần sửa test (A-18 `[changed]`: "FEAT-004 bỏ phần việc đó") |
| Trường `hidden` vẫn có dòng mẫu phiếu `visible_to` "Agents" (`_ensure_template_rows` thêm cho mọi dòng của `_ai_field_specs`); chưa kiểm giao diện agent của Helpdesk có hiện chuỗi JSON của trường này không | agent thấy ô "ai_created_labels" trên phiếu | Kiểm bằng mắt ở `/team:verify` sau U4b (khi trường có giá trị). Có hiện → hỏi architect: loại trường `hidden` khỏi `_ensure_template_rows` (đổi phán quyết (1), không tự sửa trong build) |
| Sau `cmd.migrate` từ cây FEAT-007 có T60, quyền HD Article của site `miyano` thành Custom DocPerm và ở lại cả khi phiên khác migrate từ cây không có T60 | quyền HD Article trên site không theo file chuẩn của Helpdesk nữa | Hệ quả (1b) đã được nhận (`journal-part4.md:16` (ii)); ghi As-Built. Cách gỡ: `arch-review-design-w1b-r2.md:88` |

| # | Đầu vào / kiểu lỗi thêm vào trọng tâm review | Test | Task |
|---|---|---|---|
| 6 | Site đã có Custom DocPerm của HD Article do người sửa trước khi cài | `test_install.py::TestFeat007Migrate::test_existing_article_custom_perm_kept` | T60 |
| 7 | Site chưa cài DocType HD Article | `::test_article_perm_skipped_when_doctype_missing` | T60 |
| 8 | Giá trị `auto_assign_enabled` đang lưu trên site đổi giữa hai lần chạy (phiên FEAT-004 bật tắt ô này) | `test_agent_runner.py::TestRunnerBaseSettings::test_setup_overrides_stored_auto_assign` | T59 |

## Chèn 2 (2026-11-14, phán quyết của designer ở `design-w0-fixes-2.md`)
`design-w0-fixes-2.md` thắng `design.md` và `design-w0-fixes.md`. Chữ đầy đủ của từng task nằm ở dòng "Chèn 2" trong `tasks.md`; bảng dưới chỉ ghi phần kế hoạch đổi. Không task nào đổi số; 62 task.

| Phán quyết | Task | Đổi gì trong kế hoạch |
|---|---|---|
| (1) `predicted_confidence_pct` Int `default "-1"` = không biết | T3 | `files:` thêm `erp_ai/patches.txt` (sửa), `erp_ai/patches/feat007_unknown_confidence_pct.py` (mới), `erp_ai/patches/test_feat007_unknown_confidence_pct.py` (mới); patch và `default` cùng một commit; 3 test `TestUnknownConfidencePct` |
| (2), (5c-i) `due_field_configured: bool \| None = None`, `as_deadline` | T24, T26 | cùng 2 file; T24 thêm `test_old_call_shape_no_due_note`, `test_date_due_is_end_of_day`; T26 thêm ca `date` |
| (3) trùng `ticket_type` → đầu mục đứng trước A–F thắng | T41 | `files:` thêm `erp_ai/eval/test_run_eval.py` (chỉ test; `run_eval.py` không đổi) |
| (4) trường ẩn không có dòng HD Ticket Template | T60 | cùng 2 file; `_ensure_template_rows` bỏ qua spec `hidden`; thêm `test_hidden_labels_field_has_no_template_row` |
| (5a) `is_secret_key` theo đoạn tên | T35 | cùng 2 file; tiêu chí và 4 test theo 5a |
| (5b) `{n}` là tổng số yêu cầu, bỏ yêu cầu rỗng | T62 (mới, sau T27) | `erp_ai/agent/classification.py`, `test_classification.py`; AC-28 |
| (5d) cron sau ba module đích | T44, T34 | T44 `depends:` T34, T40, T42, T47, T50, T54 và thêm `test_job_targets_importable`; T34 `depends:` T33, T40 và tự tạo khóa `cron`; `hooks.py` T40 → T34 → T44 |
| (5e) `keep_agent_settings` trả lại dòng `__Auth` | T61 (mới, sau T1) | `erp_ai/test_utils.py`, `erp_ai/tests/test_test_utils.py`; NFR-7 |

- **Bảng AC → task, phần thêm.** AC-22 / NFR-4: T3; AC-26: T26 (ca `date`); AC-28: T62; AC-51: T44 (`test_job_targets_importable`); AC-52: T41 (hai test va chạm); NFR-7: T61; STD-OPS-2: T3 (patch, đối soát `count(*) = 0` ở verify).
- **File mới.** Hai file dưới `erp_ai/patches/` nằm trong `structure.allowed_new_file_roots`; không đường dẫn nào khớp `protected_paths`.
- **Mốc kiểm.** M4 (sau T34, T39) không còn có T44 đứng trước: dòng `*/15` do T34 tạo. Rủi ro "Scheduled Job Type trỏ tới module cây chính chưa có" chỉ còn áp cho T34 ở M4; phần của T44 được 5d gỡ.
- **Việc của đợt 1 mà phán quyết chèn 2 nêu (chưa có task).** Chữ U1 `design-addendum-1-U1.md:61, 130, 262, 339, 459` và 2 test `TestConfidence`; `due_route_kwargs` của U4b (5c-ii, phải truyền `date`/`datetime` thật, `as_deadline` ném `TypeError` với chuỗi); chữ `design-addendum-1-U3.md:69`. Đưa vào `/team:plan FEAT-007 --insert` của đợt 1.

## Chèn 3 (2026-11-14, phán quyết của designer ở `design-w0-fixes-3.md`)
`design-w0-fixes-3.md` thắng `design.md`, `design-w0-fixes.md` và `design-w0-fixes-2.md`. Chữ đầy đủ của từng task nằm ở dòng "Chèn 3" trong `tasks.md`; bảng dưới chỉ ghi phần kế hoạch đổi. Không task mới, không task nào đổi số; vẫn 62 task. Các mục "Ràng buộc chung", bảng touchpoint và "Một file, một chủ" phía trên đã cập nhật.

| Phán quyết | Task | Đổi gì trong kế hoạch |
|---|---|---|
| (1) `d_watcher` ba trạng thái (`None` / chuỗi rỗng / tên người) | T25 | cùng 2 file; gỡ chữ chặn; thêm hằng `D_WATCHER_MISSING_NOTE`; 5 test `TestDWatcher` (sửa đầu vào 2 test, thêm `test_old_call_shape_no_watcher_note`); T26, T51–T54 và T44 (qua T54) hết bị chặn bởi T25 |
| (2) `TICKET_CONTENT_DOCTYPES` còn 4 tên; DocType có Link tới HD Ticket nhận ra qua meta | T8, T15 | T8: cùng `files:`, thêm `test_ticket_content_doctypes_is_adr_034_list`, `test_architecture.py` không vào `files:`; T15: `files:` thêm `erp_ai/agent/policy.py`, `erp_ai/agent/test_policy.py` (đều có sẵn), hai hàm `ticket_link_fieldnames`, `is_ticket_content_doctype`, thêm 2 test. **Điểm giữ:** cả hai chỉ gọi dev khi `arch-review-w0-fixes-3.md` ghi `Verdict: approve` hoặc `approve-with-conditions`; điều kiện của architect chép vào dòng task |
| (3a) đầu ra `redact_secrets` luôn NFC; che trước, cắt sau | T35, T36, T37 | T36 thêm `test_secret_at_tail_cut_masked`; T37 thêm `test_excerpt_masked_before_cut` |
| (3b), (3c), (3d) `SECRET_PATTERNS` = 5 mẫu giá trị; luật N-1..N-7, K-1..K-8, R-1..R-5 | T35 | cùng 2 file; tiêu chí và test theo mục 3 của phán quyết. **Điểm giữ:** vòng sửa thứ 4 là quyền của người; chưa có trả lời thì không gọi dev cho T35, T36, T37, T53 |

- **Bảng AC → task, phần thêm.** AC-27: T25 (ba trạng thái); AC-49 / ADR-034 QĐ 1, 3: T8 (hằng), T15 (vị từ theo meta); NFR-6: T36, T37 (che trước, cắt sau).
- **Hệ quả lên chuỗi U0.** T10–T20 đứng sau T8 trong làn A, nên làn A dừng ở T5 cho tới khi có kết luận của architect; làn B chạy T25 → T26, T62, T28 → T29 → T30, T40 và T55 (sau T5).
- **Việc của đợt 1 mà phán quyết chèn 3 nêu (chưa có task).** U4b: `design-addendum-1-U4b-U8.md:245` đổi thành `d_watcher=settings.d_ticket_watcher or ""`, thêm `test_runner_routing.py::TestRunnerHooks::test_d_watcher_unconfigured_logged`; U2: các dòng `design-addendum-1-U2.md:34, 56, 80, 105-110, 134, 135, 145, 148-154, 192, 279, 329`, hàm mới `policy.ticket_link_columns`, test `test_empty_ticket_link_row_still_listed`; U6b: `design-addendum-1-U6b.md:178` vế (4); U3: `design-addendum-1-U3.md:69` đọc là luật N-1..N-7. Đưa vào `/team:plan FEAT-007 --insert` của đợt 1.
- **Rủi ro thêm.** Vị từ theo meta kéo mọi DocType có Link tới HD Ticket vào tập "nội dung phiếu" (ví dụ `HD Ticket Activity`, Task có `ai_ticket`, HD Article có `ai_source_ticket`): hệ quả chủ ý của phán quyết (fail-closed), architect đang xét; nếu architect trả `request-changes` thì T8, T15 giữ chặn và báo team-leader.
