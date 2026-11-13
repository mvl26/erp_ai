Feature: FEAT-004
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks FEAT-004 (lập lại sau spec Amendment 1 và design "Sửa vòng 1")

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn. Nhãn `[F6]` = task sửa ít nhất một trong các file FEAT-006 cũng sửa (danh sách ở `plan.md`); dev phải đọc mã FEAT-006 thật trước và không đổi hành vi hay assertion của nó (STD-TEST-5).
`cmd.test_one` = lệnh của profile với `{file}` là file ở `test:`. Mọi task: viết test đỏ trước (STD-TEST-1), chỉ sửa trong `files:`, không skip/xfail. Tên hàm, hằng, chuỗi chính xác: `plan.md` mục Ràng buộc chung và `design.md` mục 2–4 (số dòng `file:line` trong design là của `team/FEAT-003`; dò lại trên nền thật). Task sửa `*.json` của DocType: chạy `cmd.migrate` rồi mới `cmd.test_one`. Mọi test có git dùng `GitSandbox` (T36, T51), không chạy git trong `apps/` thật (NFR-9).

Nhánh nền: **`team/FEAT-006 (hash at build time)`**. Build chỉ bắt đầu sau khi FEAT-006 qua verify; tech-lead tạo `team/FEAT-004` từ đầu nhánh đó, ghi mã commit thật vào dòng dưới và chạy `cmd.test` trước T1.
Tiến độ: BASE ghi ở đây trước mỗi lần gọi dev.
- BASE nhánh nền = team/FEAT-006 @ f039112 (FEAT-006 verified 2026-11-13); `team/FEAT-004` cắt tại đó, commit tài liệu FEAT-004 = 0a95ac3
- Lệnh bench: `cd /home/miyano/frappe-bench && PYTHONPATH=/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-004 bench --site miyano run-tests ...` (role-policy chặn tech-lead chạy bench: dev chạy; một `cmd.test` toàn app mỗi lần trên site `miyano`)
- Lượt 0 (nền): `cmd.test` trên đầu nhánh `team/FEAT-004`; mã nguồn (`erp_ai/`) giống hệt `f039112`, chỉ khác `docs/`. BASE của mọi lần gọi dev ở chặng 1 là đầu nhánh `team/FEAT-004` ngay sau commit "ghi lệnh bench" (hash ghi ở từng dòng tick bên dưới)
- Chặng 2 (2026-11-13 11:15, devs=5 reviewers=5 theo lệnh người): `cmd.test` do tech-lead chạy sau mỗi lần merge; dev chỉ chạy `cmd.test_one` (site `miyano` dùng chung), không chạy `cmd.migrate` trừ task DocType JSON (T3, T4, T12, chạy riêng lẻ, không song song với nhau và với T1); báo cáo dev nằm trong tin trả về, không ghi file
- baseline: Ran 885 tests in 225.897s, OK (trên `cb40420`, 2026-11-13 11:20) — red: không có
- Quy ước merge chặng 2: merge từng task một (mỗi task một merge commit); khi nhiều task không chung file được approve cùng lúc thì chạy MỘT lần `cmd.test` trên đầu nhánh sau cả lô (lệch chữ "sau mỗi merge" của skill, vì người yêu cầu gấp và mỗi lần chạy ~4 phút trên site chung); đỏ → chạy lại theo từng merge commit để tìm task gây ra, không tick task nào của lô
- round 1: BASE=cb40420 · dev T35, T2, T7, T24, T33 (T1 và T3 chờ `cmd.test` nền xong vì có `bench migrate`) · T35 lần 1 BLOCKED (hook worktree chặn git có biến môi trường trong thư mục tạm)
- round 2: BASE=cb40420 · review T2 approve, T24 approve, T33 approve, T7 request-changes (2 major STD-TEST-2) · dev T35 lần 2 (nhánh `team/FEAT-004-task-35b`, DONE, D-18 đạt), dev T1 (DONE, lớn nhất 39.767 s ≤ 540 s)
- merge lô 1: T2 `90e9f20`, T24 `941f6b2`, T33 `f0054f5`
- `cmd.test` lô 1 trên `f0054f5`: Ran 892 tests, FAILED (errors=16), cả 16 là `QueryDeadlockError` (phiên BUG-003 chạy `run-tests --app erp_ai` cùng lúc trên site `miyano`, PID thấy bằng `ps`); chạy lại riêng: `test_route_ticket` 29 OK, `test_install` 33 OK, `test_ticket_panel` 36 OK, `test_agent_runner` vẫn deadlock (19 rồi 29 lỗi, phiên kia còn chạy) → chưa tick
- round 4: review T7 vòng 2 approve (2 phát hiện ADDRESSED), T35 approve, T3 approve · merge lô 2: T1 `b9f0079`, T7 `93a27a8`, T35 `000150a`, T3 `3aa363f`
- `cmd.test` lô 2 trên `3aa363f`: Ran 903 tests, FAILED (errors=77), cả 77 là `QueryDeadlockError` (phiên BUG-003 lại chạy cả bộ test cùng lúc) → chưa tick; chạy lại sau khi tiến trình kia kết thúc
- round 5: BASE=3aa363f · dev T10, T40, T23, T36, T8 — bắt đầu khi T2/T7 đã merge và review approve nhưng CHƯA tick (lệch chữ "depends đã tick": bộ test bị nghẽn bởi phiên khác, lỗi chỉ là deadlock; nếu lần chạy sạch lộ lỗi thật thì các task này rebase)
- `cmd.test` trên `3aa363f` (phủ lô 1 và lô 2, chạy sau khi tiến trình của phiên kia kết thúc): Ran 903 tests in 321.253s, FAILED (errors=6), cả 6 là `QueryDeadlockError` ở `test_route_ticket` (3), `test_ticket_panel` (2), `test_gateway` (1); chạy lại riêng từng module: `Ran 29 tests ... OK`, `Ran 36 tests ... OK`, `Ran 65 tests ... OK` → xanh (không test đỏ nào ngoài nhiễu deadlock) → tick T1, T2, T3, T7, T24, T33, T35 (review-01, 02, 03, 07, 24, 33, 35 approve; T7 2 vòng)
- round 6: review T10 approve, T40 approve, T36 approve, T23 request-changes (1 major STD-TEST-2), T8 request-changes (1 major STD-TEST-8) · merge lô 3: T10, T40, T36
- round 3: BASE=f0054f5 · dev T3 (có `cmd.migrate`) · rework T7 vòng 2 (FIX_BASE=5604ba9) · rework T35 (bỏ tên/email thật khỏi ghi chú, FIX_BASE=587e780) · review T1 (cb40420..team/FEAT-004-task-1)

## Bảng đổi ID cũ → mới (plan lần 1, 34 task → lần này 51 task)
FEAT-005 trích `F4-T<n>` (T2–T7, T12, T23, T24, T28–T33): các ID đó KHÔNG đổi nghĩa lớn; ID cũ T1–T34 giữ nguyên, task mới nhận T35–T51 và nằm xen đúng chỗ trong file.
| ID | Trạng thái | Thay đổi |
|---|---|---|
| T1 | giữ | không đổi |
| T2 | giữ, sửa | thêm `CORE_APPS`, `BOT_GIT_NAME`, `BOT_GIT_EMAIL` |
| T3, T4 | giữ, sửa | số trường đọc trên nền FEAT-006, mô tả có câu commit/app lõi |
| T5, T6 | giữ, sửa | nền FEAT-006; app lõi hợp lệ |
| T7 | giữ | không đổi (chỉ ghi chú: `source.get_source_root` là hàm gốc duy nhất) |
| T8 | giữ, sửa | danh tính repo `erp_ai` theo hợp hai common dir (gói đang chạy ∪ gốc tạm) |
| T9 | giữ, sửa | thêm `switch-to-branch`, `new-app`, `init` vào danh sách cấm (23 tên) |
| T10 | giữ | không đổi |
| T11 | giữ, đổi tên file | `bench_runner.py` → `process_runner.py`, `test_bench_runner.py` → `test_process_runner.py` (D-12); `TIMEOUT_EXECUTABLE`/`BENCH_EXECUTABLE` import từ `source.py` |
| T12 | giữ, sửa | thêm 9 trường git, bố cục `section_git`, `section_git_result` |
| T13, T14 | giữ, sửa | `STATE_FIELDS` +4, `content_digest` +5 trường git, `finish(fields=)` |
| T15, T16 | giữ | không đổi |
| T17 | giữ, sửa | `set_intro` từ `change_notes` |
| T18 | giữ, sửa | thêm kiểm `commit_message`; `check_write_path(read_git=False)` |
| T19 | giữ, viết lại | nhánh code: dấu file, kiểm trước git, ghi, add, commit, kiểm sau, `Đã áp dụng` |
| T20 | giữ, viết lại | hoàn tác = ghi lại byte + 1 commit hoàn tác; file mới theo D-18 |
| T21, T22 | giữ, sửa | 0 lệnh git khi chạy lệnh bench; khóa giả không vào env/metadata git |
| T23 | giữ, sửa | nền FEAT-006: `change_enabled`, `allowed_apps` đặt sau `routing_config` |
| T24 | giữ, sửa | `build_reason_system(prompt_digest, routing_table="", *, change_tools=False)`; khối có dòng commit |
| T25–T27 | giữ, sửa | dùng `GitSandbox`; bộ chặn đọc git mặc định bật |
| T28–T30 | giữ, sửa | T29 truyền cả `routing_table`; T28, T30 không đổi |
| T31 | giữ, sửa | `STATE_FIELDS` +4 |
| T32, T33 | giữ | không đổi |
| T34 | giữ, sửa | thêm NFR-9, ADR-022, `git status` sạch |
| T35 | MỚI | kiểm sớm D-18: git 2.43 ghi việc xóa với `commit --only`, không thì `DESIGN_CONFLICT` |
| T36 | MỚI | `GitSandbox` phần lõi (repo tạm, thay `get_source_root`) |
| T37 | MỚI | `source.py`: tùy chọn/môi trường git, `run_git_read`, thư mục hook rỗng |
| T38 | MỚI | `read_git_state` và các câu từ chối (AC-18) |
| T39 | MỚI | `git_head`, `git_commit_summary`, `git_blob`, `git_is_ancestor`, upstream, ahead |
| T40 | MỚI | `change_text.py`: thông điệp commit, `safe_person_name` |
| T41 | MỚI | `change_text.proposal_notes`: nhánh, upstream, cảnh báo app lõi |
| T42 | MỚI | bộ chặn: `read_git`, `is_core_app`, tích hợp `GitState` |
| T43 | MỚI | `process_runner`: `git_add_new`, `git_commit_only`, `git_unstage_new` |
| T44 | MỚI | luật kiến trúc git của ADR-022 |
| T45 | MỚI | `apply_job`: commit lỗi/quá giờ → trả lại; D-17; kiểm sau sai |
| T46 | MỚI | `apply_job`: kiểm trước git, đổi nhánh → `Hết hiệu lực`, khóa git nhanh |
| T47 | MỚI | `apply_job`: hoàn tác lỗi (không là tổ tiên, kiểm trước, commit hoàn tác lỗi) |
| T48 | MỚI | test chéo: hook không chạy, ref remote không đổi, metadata commit sạch |
| T49 | MỚI | controller: `commit_message`, `onload` → `change_notes`, test dữ liệu form |
| T50 | MỚI | `propose_change`: 4 trường git, comment theo `proposal_notes` |
| T51 | MỚI | `GitSandbox` phần trạng thái (remote, nhánh, khóa, hook) + `RealCoreReposUntouchedMixin` |

## Phần 0, đo và kiểm sớm (cổng)

- [x] T1 — Đo thời gian `bench migrate` và `bench build --app` trên `miyano` — files: docs/team/features/FEAT-004/dev-notes.md — test: — (bước kiểm có đầu ra) — depends: —
  - Criterion: NFR-3, D-10 (AC-10 dựa vào mốc 540 s)
  - Receives: `cmd.migrate` của profile; `cmd.build` = `bench build --app erp_ai`; thêm một app khác trong `apps/` (không phải `erp_ai`) làm mẫu `build --app <app>`
  - Returns: `dev-notes.md` có bảng: lệnh, lần chạy 1..3, thời gian giây (dùng `time`), đầu ra rút gọn (≤ 20 dòng, không bí mật), phiên bản bench, `which timeout bench git`
  - Expect: mọi số ≤ 540 s → ghi "đạt" và tiếp tục. Bất kỳ số > 540 s → `STOP` theo mẫu 4 dòng, không làm T11, T21, T22. Không sửa file ngoài `dev-notes.md`

- [x] T35 — Kiểm sớm D-18: `commit --only` ghi việc xóa file đã theo dõi — files: docs/team/features/FEAT-004/dev-notes-git.md — test: — (bước kiểm có đầu ra) — depends: —
  - Criterion: D-18 (nền AC-20: hoàn tác file mới = gỡ file khỏi đĩa rồi `commit --only -- <đích>`), ADR-022 QĐ 2
  - Receives: `git --version` (máy này 2.43.0); thư mục tạm bằng `mktemp -d` (không đụng `apps/`); cờ như `process_runner`: `commit --only --no-gpg-sign --quiet -m a -m b -- <rel>`, `GIT_CONFIG_GLOBAL=/dev/null`
  - Returns: `dev-notes-git.md` ghi lệnh và đầu ra thật: (1) repo tạm có `keep.txt` staged sửa và `other.txt` unstaged sửa; (2) commit `new.txt`; (3) `rm new.txt` khỏi đĩa (không `git rm`); (4) `git commit --only -- new.txt`; (5) `git show --stat --format=%H HEAD`, `git ls-tree HEAD`, `git diff --cached --name-only`, `git status --porcelain`
  - Expect: commit mới chứa đúng 1 đường dẫn `new.txt` ở trạng thái xóa, `ls-tree` không còn `new.txt`, `keep.txt` vẫn staged, `other.txt` vẫn unstaged → ghi "đạt". Một điều sai → `DESIGN_CONFLICT` (architect mở rộng ADR-022 QĐ 2 cho `rm --cached` trước commit); tech-lead dừng T20, T47, T36 không bị chặn nhưng không tick T20. Không sửa file ngoài `dev-notes-git.md`

## Phần 1, nền: hằng số, cấu hình, log, policy

- [x] T2 — Hằng số, gói `changes`, test hằng — files: erp_ai/constants.py, erp_ai/agent/changes/__init__.py, erp_ai/agent/changes/test_transitions.py — test: erp_ai/agent/changes/test_transitions.py — depends: —
  - Criterion: nền cho NFR-3, NFR-4, AC-12 (hằng), AC-16 (`CORE_APPS`), NFR-8 (`BOT_GIT_*`); ADR-013 QĐ 2/3; ADR-022 QĐ 5
  - Receives: `JOB_TIMEOUT_S`, `JOB_SAFETY_MARGIN_S` (đã có trong constants.py), `KEY_STATUS_*` làm mẫu
  - Returns: `PROPOSAL_DOCTYPE`, 9 `CHANGE_STATUS_*`, `CHANGE_KIND_CODE`, `CHANGE_KIND_COMMAND`, `CHANGE_STEPS = ("propose","approve","reject","apply","fail","stale","undo")`, `TRIGGER_CHANGE_ACTION`, `TITLE_CHANGE_FAILED`, `COMMAND_TIMEOUT_S`, `RUN_BACKSTOP_S`, `PROPOSAL_TEXT_MAX_CHARS`, `REPLACE_MAX_ITEMS`; **[Sửa vòng 1]** `CORE_APPS = ("frappe","erpnext","helpdesk","hrms")`, `BOT_GIT_NAME = "ERP AI Agent"`, `BOT_GIT_EMAIL = "erp-ai-agent@bot.invalid"`; gói `erp_ai.agent.changes` rỗng; class `TestChangeConstants` trong test_transitions.py (`OUTPUT_MAX_LINES` và `PROPOSAL_FILE_MAX_BYTES` do T10/T11 tạo ở module của chúng)
  - Expect: đỏ (ImportError) rồi xanh: `test_status_values`, `test_command_timeout_is_job_timeout_minus_margin` (540), `test_run_backstop` (570), `test_core_apps_and_bot_identity` (`BOT_GIT_EMAIL` kết thúc `.invalid`)

- [x] T3 — `ERP AI Setting`: 2 trường mới + Section Break, có mô tả — [F6] — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/tests/test_doctype_descriptions.py — depends: —
  - Criterion: design 2.4; luật mô tả FEAT-003 (≤ 400 ký tự); AC-1 (mặc định tắt), AC-4/AC-16 (danh sách app mặc định rỗng)
  - Receives: bảng design 2.4; `DOCTYPE_CONFIG` thật trên nền FEAT-006 (FEAT-006 đã thêm 2 trường Setting)
  - Returns: JSON có `section_code_change` ("Sửa code và lệnh bench"), `code_change_enabled` (Check, default 0), `code_change_apps` (Small Text, mặc định rỗng) đặt SAU trường FEAT-006; mô tả đúng mục 2.4, **[Sửa vòng 1]** có câu về commit local và câu về app lõi; test: `field_count` = số thật + 2, `section_count` = số thật + 1, thêm `phrases` cho 2 trường và dòng `sections`
  - Expect: đỏ trước; xanh sau `cmd.migrate` + `cmd.test_one`; `test_erp_ai_setting.py` hiện có vẫn xanh; trường FEAT-006 không đổi

- [ ] T4 — `ERP AI Log`: loại `change`, 3 trường, `write_entry(change)`, test tổng chi phí — [F6] — files: erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json, erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py, erp_ai/tests/test_tasks.py, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/agent/test_run_log.py — depends: T2, T3, T12
  - Criterion: AC-12 (một dòng mỗi bước), ADR-012 QĐ 6, luật mô tả FEAT-003 cho 3 trường log mới
  - Receives: `CHANGE_STEPS`, `TRIGGER_CHANGE_ACTION` (T2); `write_entry` hiện có; số trường thật của Log trên nền FEAT-006 (FEAT-006 +4 cột)
  - Returns: JSON: `entry_type` thêm `change`, `trigger` thêm `change_action`, trường `change_proposal` (Link `ERP AI Change Proposal`), `change_step` (Select 7 giá trị), `actor` (Link User), mỗi trường có mô tả tiếng Việt ≤ 400 ký tự; `write_entry` nhận `entry_type="change"` với kiểm `trigger`, `change_step ∈ CHANGE_STEPS`, `actor`, `change_proposal`, sai/thiếu → `ValueError`; chỉ loại này `insert(ignore_permissions=True)`; `test_doctype_descriptions.py`: `field_count` của Log = số thật + 3, thêm `phrases` (nền chưa có "ERP AI Log" → `NEEDS_CONTEXT`). **[Sửa vòng 1]** Dòng `apply`/`undo` thêm khóa `head`, `commit`, `branch` trong `value_before`/`value_after`: chỉ là dữ liệu truyền vào, `write_entry` không đổi chữ ký
  - Expect: `test_change_entry_requires_step_actor_proposal_and_trigger`, `test_change_entry_bypasses_permission_but_other_types_do_not`; `test_tasks.py::test_recompute_spend_unchanged_by_change_rows`; `test_doctype_descriptions.py` xanh; 4 cột FEAT-006 của Log không đổi

- [ ] T5 — `policy`: đọc 2 trường mới, kiểm danh sách app — [F6] — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_policy.py — depends: T3, T4, T37
  - Criterion: AC-1, AC-2 (nền công tắc), AC-16 (`validate_change_apps` cho app lõi), ADR-012 QĐ 6 (`runs_today` bỏ qua dòng `change`), ADR-011 QĐ 3
  - Receives: `POLICY_FIELDS`, `current_settings` kiểu cũ; `auto_assign_enabled`, `is_excluded_team` của FEAT-006 (đặt hàm mới cuối file, không đổi chúng); tên trường `code_change_enabled`, `code_change_apps` (T3)
  - Returns: `ChangeSettings(enabled: bool, allowed_apps: tuple[str, ...])`; `change_settings(settings)`; `current_change_settings()` (đọc DB `cache=False`); `validate_change_apps(settings) -> None` ném `frappe.throw` 3 câu design 3.6 (`Tên app '<x>' không hợp lệ`, `Không được thêm erp_ai vào danh sách app được sửa`, `Không có thư mục apps/<x>`), bỏ dòng trùng/rỗng; `frappe`, `erpnext`, `helpdesk`, `hrms` hợp lệ khi có thư mục (không câu lỗi mới ở vòng 1); `POLICY_FIELDS` thêm 2 tên (giữ `auto_assign_enabled`)
  - Expect: `test_change_settings_defaults_off_and_empty`, `test_change_apps_parsing_and_dedup`, `test_validate_change_apps_rejects_erp_ai_dotdot_missing_dir`, `test_validate_change_apps_accepts_core_apps` (thư mục tạm), `test_runs_today_ignores_change_rows`; `test_architecture::test_policy_fields_only_in_policy` xanh

- [ ] T6 — `ERPAISetting.validate` gọi kiểm danh sách app — [F6] — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: T5
  - Criterion: AC-4/AC-16 (nền: `erp_ai` không bao giờ vào danh sách), A-3, A-3'
  - Receives: `policy.validate_change_apps` (T5); lời gọi `validate_routing_config` của FEAT-006
  - Returns: `validate` gọi thêm `policy.validate_change_apps(self)` cạnh lời gọi của FEAT-006; không đổi hàm khác
  - Expect: `test_change_apps_validation` (lỗi: `erp_ai`, `../x`, thư mục không có; biên: None/rỗng; **[Sửa vòng 1]** `frappe`, `hrms` lưu được); test cũ và test FEAT-006 vẫn xanh

## Phần 2, bộ chặn, ghi file, chạy lệnh, nền git

- [x] T7 — Bộ chặn đường dẫn ghi (phần chung) + helper `apps/` tạm — [F6: test_utils.py] — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py, erp_ai/test_utils.py — test: erp_ai/agent/tools/test_change_guard.py — depends: —
  - Criterion: AC-4 (app ngoài danh sách; `..` và symlink ra ngoài `apps/`; tên bí mật/`protected_paths`; đuôi ngoài danh sách kể cả file chưa tồn tại; `.git`; `sites/`)
  - Receives: `source.resolve_safe_path`, `TEN_CAM`, `DUOI_CHO_PHEP`, `source.get_source_root` (hàm gốc duy nhất của `apps/`)
  - Returns: `GuardResult` (frozen dataclass, 4 trường đầu; `is_core_app`, `git` do T42), `check_write_path(rel_path, allowed_apps, *, new_file) -> GuardResult` theo thứ tự bảng 3.1 (`PATH_INVALID`, `APP_NOT_ALLOWED`, `NAME_FORBIDDEN` gồm `license.txt`, `EXT_FORBIDDEN`, `GIT_DIR`), `reason` đúng chữ bảng 3.1; helper `test_utils`: dựng gốc `apps/` tạm (app được phép, symlink ra ngoài, `.env`, `x.pem`, `site_config.json`), patch `source.get_source_root`; chưa có kiểm danh tính `erp_ai` (T8), chưa đọc git
  - Expect: đỏ rồi xanh: `test_refuses_app_not_in_allowed_list`, `test_refuses_escape_with_dotdot_and_symlink`, `test_refuses_secret_and_protected_names`, `test_refuses_extension_outside_read_list_even_for_new_file`, `test_refuses_git_dir_component`, `test_allows_file_in_allowed_app`; không đụng `apps/` thật

- [ ] T36 — `GitSandbox` phần lõi: repo git tạm, thay gốc `apps/` — [F6: test_utils.py] — files: erp_ai/test_utils.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T7
  - Criterion: NFR-9, ADR-022 QĐ 8; nền cho mọi test git (AC-16..AC-23)
  - Receives: design 8.5; `source.get_source_root` (patch); helper `apps/` tạm của T7 (không đổi hành vi); không phải file sản phẩm nên được gọi `subprocess` để dựng repo
  - Returns: `GitSandbox(testcase, apps=("frappe","erpnext","helpdesk","hrms","erp_ai","custom_app"), *, erp_ai_worktree="erp_ai-wt")` với `root`, `repo(app)`, `commit_file(app, rel, content) -> sha`, `stage`, `write_unstaged`, `refs(app)`, `log_meta(app, rev="HEAD")`; mỗi repo có commit đầu và nhánh `main`; lệnh git của helper dùng `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, danh tính test cố định; thư mục tạm dưới `tempfile.mkdtemp()`, `addCleanup` xóa; `patch` `source.get_source_root` trong `setUp`; repo `erp_ai-wt` là worktree thật (`.git` là file + `commondir`). Các hàm còn lại của design 8.5 do T51
  - Expect: `test_source.py::test_git_sandbox_redirects_apps_root` (`get_source_root()` = `root` trong sandbox, ngoài sandbox là gốc thật), `test_git_sandbox_repos_are_isolated_from_global_config` (HOME giả có `.gitconfig` email thật: không lọt vào `log_meta`)

- [ ] T51 — `GitSandbox` phần trạng thái: remote, nhánh, khóa, hook + mixin repo lõi thật — [F6: test_utils.py] — files: erp_ai/test_utils.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T36
  - Criterion: NFR-9, AC-18 (tạo từng điều kiện git), AC-19 (hook đánh dấu), AC-21 (remote URL token giả); ADR-022 QĐ 8
  - Receives: `GitSandbox` lõi (T36); design 8.5
  - Returns: `add_remote(app, name="origin", url="https://x-token-FAKE@host/r.git", ahead=2)` (remote là repo bare tạm; URL giả chỉ lưu trong `.git/config` tạm), `switch_branch(app, branch, *, create=True)`, `detach(app)`, `mark_in_progress(app, kind)` (`MERGE_HEAD`, `rebase-merge`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`), `hold_index_lock(app)`, `install_marker_hooks(app) -> thư mục tệp đánh dấu` (hook `pre-commit` từ chối, `prepare-commit-msg`, `commit-msg`, `post-commit`, `post-index-change`, `reference-transaction` ghi tệp đánh dấu); `RealCoreReposUntouchedMixin` (`setUpClass` chụp `git -C <bench>/apps/<app> --no-optional-locks rev-parse HEAD` và `status --porcelain` của `frappe`, `erpnext`, `helpdesk`, `hrms`; `tearDownClass` so; chỉ đọc)
  - Expect: `test_sandbox_state_helpers_produce_expected_git_state` (mỗi hàm một subTest: `rev-parse --abbrev-ref HEAD` = `HEAD` khi detach; tệp `index.lock` có; tệp `MERGE_HEAD` có; `rev-list @{u}..HEAD` đếm 2), `test_real_core_repos_mixin_detects_change` (mixin phát hiện khi tệp đánh dấu giả lập)

- [ ] T37 — `source.py`: tùy chọn và môi trường git, `run_git_read`, thư mục hook rỗng + luật subprocess — [F6: test_architecture.py] — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py, erp_ai/agent/git_no_hooks/README.md, erp_ai/tests/test_architecture.py — test: erp_ai/agent/tools/test_source.py — depends: T2, T36
  - Criterion: NFR-8 (git không đọc `~/.gitconfig`, không HOME), AC-23, D-13, ADR-022 QĐ 2, 4
  - Receives: `GIT_SUBCOMMANDS`, `GIT_TIMEOUT_S` có sẵn; `git_source`/`log`/`blame` giữ nguyên; design 3.2 (đoạn `source.py`) và 3.5 (tùy chọn git)
  - Returns: `GIT_READ_SUBCOMMANDS`, `TIMEOUT_EXECUTABLE = "timeout"`, `BENCH_EXECUTABLE = "bench"` (T11 import), `GIT_HOOKS_DIR` (trỏ `erp_ai/agent/git_no_hooks`), `GIT_BACKSTOP_EXTRA_S = 5`, `git_global_options(read: bool)` (`core.hooksPath`, `core.fsmonitor=false`, `maintenance.auto=false`, `gc.auto=0`; read có thêm `--no-optional-locks`), `git_env(identity: bool)` (khóa env đúng tập, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, không `HOME`; `identity=True` thêm danh tính từ `BOT_GIT_*`), `GitRun`, `run_git_read(repo_root, subcommand, *args, limit_s)` (subcommand ngoài tập → `ValueError`; bọc `timeout -s KILL`, `start_new_session=True`); `git_no_hooks/README.md` nói vì sao thư mục rỗng và cấm thêm tệp; `test_architecture`: sửa `check_subprocess_call_shape`/`check_subprocess_only_in_source_tool` chỉ ở mức cần để lời gọi git mới của `source.py` xanh
  - Expect: `test_git_env_has_no_home_and_ignores_global_config`, `test_hooks_dir_has_no_hook_files` (chỉ `README.md`; không nằm dưới gốc tạm), `test_run_git_read_rejects_unlisted_subcommand`, `test_git_global_options_contents`; `test_architecture` xanh

- [ ] T38 — `read_git_state` và các câu từ chối (AC-18) — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T37, T51
  - Criterion: AC-18 (kiểm trước, mỗi điều kiện một câu), D-20 (thư mục app phải là gốc repo), ADR-022 QĐ 3, 7
  - Receives: `run_git_read` (T37); `GitSandbox` (T36, T51); bảng 3.2 (câu từ chối chính xác); `GitState` theo design 3.2
  - Returns: `GitState(refusal, repo_root, rel_in_repo, branch, head, upstream_ref, ahead_count, …)` và `read_git_state(full_path, *, new_file, limit_s) -> GitState`: từ chối khi staged hoặc unstaged của file đích, file có sẵn chưa theo dõi, file mới bị `.gitignore`, không phải repo, thư mục app nằm trong repo khác (so `toplevel`), repo chưa có commit, HEAD detached, `MERGE_HEAD`/`rebase-merge`/`CHERRY_PICK_HEAD`/`REVERT_HEAD`, `index.lock`; file khác bẩn thì không chặn; mọi lệnh chỉ trong `GIT_READ_SUBCOMMANDS`
  - Expect: `test_read_git_state_refusals` (13 subTest, câu đúng bảng 3.2), `test_read_git_state_other_dirty_file_does_not_block`

- [ ] T39 — `source.py`: `git_head`, `git_commit_summary`, `git_blob`, `git_is_ancestor`, upstream, ahead — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T38
  - Criterion: AC-17 (kiểm sau), AC-20 (tổ tiên), AC-21 (upstream, ahead, mặt nạ URL), NFR-8
  - Receives: `GitState` (T38); `GitSandbox.add_remote` (T51); design 3.2
  - Returns: `CommitSummary(commit, parents, paths, branch, author_email)` (email tác giả của commit HEAD; [Sửa vòng 2]), `git_head(repo) -> str | None`, `git_commit_summary(repo)` (HEAD so với cha của chính nó bằng diff-tree, không nhận HEAD cũ; [Sửa vòng 2]), `git_blob(repo, rev, rel) -> bytes | None`, `git_is_ancestor(repo, a, b) -> bool | None` (None = lỗi git), `GitState.upstream_ref`/`ahead_count` điền theo ref remote có sẵn ở máy (không `fetch`, không đọc `.git/config`); `branch.<n>.remote` là URL → `upstream_ref = "(remote không tên)"`
  - Expect: `test_upstream_with_url_like_name_is_masked`, `test_ahead_count_and_upstream_ref`, `test_git_blob_none_for_deleted_path`, `test_git_is_ancestor_true_false_none`, `test_commit_summary_parents_paths_branch` (thêm kiểm `author_email` và `paths` tính theo cha của HEAD, kể cả khi trước đó có commit của người)

- [ ] T8 — Bộ chặn: danh tính kho git của `erp_ai` và worktree — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T7
  - Criterion: AC-4, AC-16 (đường dẫn khử symlink rơi vào repo `erp_ai`, kể cả worktree `apps/erp_ai-wt` hoặc tên khác; `erp_ai` có trong danh sách vẫn bị chặn)
  - Receives: `check_write_path` (T7); helper tạm (T7)
  - Returns: thêm `APP_FORBIDDEN` (`không được sửa app erp_ai hoặc kho git của nó`): đi từ thư mục đích lên `apps/` tìm `.git`; thư mục → `realpath(.git)`; file `gitdir: X` → đọc `X/commondir` nếu có; so với **hợp hai common dir** (repo chứa gói `erp_ai` đang chạy, đi lên từ `os.path.dirname(erp_ai.__file__)`; và `os.path.join(source.get_source_root(), "erp_ai")` của gốc tạm); chỉ đọc file, không `git`/`subprocess`
  - Expect: `test_refuses_erp_ai_app`, `test_refuses_erp_ai_worktree_under_other_name_even_if_allowed`, `test_refuses_symlink_into_erp_ai_repo`, `test_running_erp_ai_package_repo_refused`, `test_erp_ai_refused_even_when_listed_in_temp_root`; test T7 vẫn xanh

- [ ] T9 — Bộ chặn lệnh bench: dựng và kiểm đối số — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T8
  - Criterion: AC-9 (ngoài danh sách; lệnh cấm A-6; ký tự điều khiển shell; site khác; `--force`; sửa thành lệnh cấm vẫn bị chặn lúc áp dụng), nền AC-8; ADR-022 QĐ 2 (không lệnh bench nào chạy git)
  - Receives: bảng lệnh 3.1; `check_write_path` (T7, T8) cho `app` của `build`
  - Returns: `build_bench_args(command, app, allowed_apps, site) -> list[str] | str` (str = reason: `lệnh build cần app` / `lệnh này không nhận app` / lý do app); `check_bench_args(args, allowed_apps, site) -> str | None` 4 bước theo thứ tự (`đối số chứa ký tự điều khiển shell`, `cờ --force bị cấm`, `chỉ chạy cho site đang chạy`, `lệnh không có trong danh sách cho phép`, so khớp ĐÚNG một dạng); danh sách cấm 23 tên (thêm `switch-to-branch`, `new-app`, `init`)
  - Expect: `test_bench_args_refuse_every_a6_denied_command` (đủ 23 tên), `test_bench_args_refuse_shell_metacharacters`, `test_bench_args_refuse_other_site_and_force`, `test_bench_args_refuse_unlisted_and_build_of_disallowed_app`, `test_build_args_for_each_allowed_command`

- [ ] T10 — `file_writer`: ghi nguyên tử, gỡ file đã tạo — files: erp_ai/agent/changes/file_writer.py, erp_ai/agent/changes/test_file_writer.py — test: erp_ai/agent/changes/test_file_writer.py — depends: T2
  - Criterion: AC-6, AC-7 (từng byte; hoàn tác file mới = gỡ), NFR-2; ADR-013 QĐ 6
  - Receives: gói `changes` (T2); thư mục tạm của test
  - Returns: `sha256_of(full_path) -> str | None`; `write_atomic(full_path, content, *, new_file) -> str` (mkstemp cùng thư mục prefix `.erp_ai_`, UTF-8, flush, fsync, chmod theo file cũ hoặc 0o644, `os.replace`, đọc lại, sha256; lỗi giữa chừng gỡ tệp tạm rồi raise); `remove_created(full_path)`; không ghi trực tiếp tệp trong `.git`
  - Expect: `test_write_atomic_keeps_mode_and_leaves_no_temp` (cả nhánh lỗi), `test_write_atomic_exact_bytes` (`\r\n`, tiếng Việt, không newline cuối), `test_sha256_of_missing_is_none`, `test_remove_created`

- [ ] T11 — `process_runner`: `run_bench`, cắt đầu ra, môi trường tối thiểu + luật subprocess — [F6: test_architecture.py] — files: erp_ai/agent/changes/process_runner.py, erp_ai/agent/changes/test_process_runner.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/changes/test_process_runner.py — depends: T1, T2, T5, T37
  - Criterion: AC-8 (không shell, cwd bench, có timeout), AC-10, AC-13, NFR-3, NFR-4, NFR-5; ADR-013 QĐ 3, 7; D-3, D-5, **D-12 (tên file mới `process_runner.py`, không có `bench_runner.py` trong repo)**
  - Receives: số đo T1 (≤ 540 s); `COMMAND_TIMEOUT_S`, `JOB_SAFETY_MARGIN_S` (T2); `source.TIMEOUT_EXECUTABLE`, `source.BENCH_EXECUTABLE` (T37); `frappe.utils.get_bench_path`
  - Returns: `ENV_ALLOWLIST = ("PATH","HOME","LANG","LC_ALL","USER")`, `OUTPUT_MAX_LINES = source.READ_MAX_LINES`, `CommandResult`, `run_bench(args, limit_s)` đúng hình dạng design 4.3 (`timeout -s KILL`, `cwd=` bench, `env=_minimal_env()`, `stdin=DEVNULL`, `start_new_session=True`, `timeout=limit_s + JOB_SAFETY_MARGIN_S // 2`); quá giờ: `TimeoutExpired` hoặc `returncode ∈ (-9,124,137)` ∧ thời gian ≥ limit; `127` → `not_found`; đầu ra ≤ 400 dòng (399 dòng cuối + dòng đầu `… đã cắt <n> dòng đầu`, mỗi dòng ≤ 1000 ký tự); `test_architecture`: `check_subprocess_only_in_source_tool` cho phép `{source.py, agent/changes/process_runner.py}`, `check_subprocess_call_shape` áp cả hai; riêng `process_runner.py`: `env=` không chứa `os.environ`, có `cwd=`, `start_new_session=True`
  - Expect: `test_output_cut_to_400_lines`, `test_limit_comes_from_deadline_and_kills_group`, `test_env_is_allowlist_only`, `test_exit_127_is_not_found`; `test_architecture` xanh

- [ ] T43 — `process_runner`: `git_add_new`, `git_commit_only`, `git_unstage_new` — [F6: test_architecture.py] — files: erp_ai/agent/changes/process_runner.py, erp_ai/agent/changes/test_process_runner.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/changes/test_process_runner.py — depends: T11, T37
  - Criterion: AC-17 (hình dạng lệnh), AC-13/NFR-8 (env git), AC-23 (không `-a`, `--amend`), ADR-022 QĐ 2, 4, 5
  - Receives: `run_bench`, `CommandResult` (T11); `source.git_global_options(read=False)`, `source.git_env(identity=True)`, `TIMEOUT_EXECUTABLE`, `GIT_BACKSTOP_EXTRA_S` (T37); bảng đuôi đối số design 3.5
  - Returns: `git_add_new(repo_root, rel, limit_s)` đuôi `["add","--",rel]`; `git_commit_only(repo_root, rel, subject, body, limit_s)` đuôi `["commit","--only","--no-gpg-sign","--quiet","-m",subject,"-m",body,"--",rel]`; `git_unstage_new` đuôi `["rm","--cached","-q","--",rel]`; mọi lệnh bọc `timeout -s KILL`, `cwd=repo_root`, `env=source.git_env(identity=True)`, `stdin=DEVNULL`, `start_new_session=True`, `timeout=limit_s + GIT_BACKSTOP_EXTRA_S`; đầu ra ≤ 20 dòng; không `user.name`/`user.email`/`AGENT_USER` trong file; `test_architecture`: luật shape của `process_runner.py` chấp nhận lời gọi git
  - Expect: `test_git_write_argv_shapes` (stub `subprocess.run`; không `-a`/`--amend`), `test_git_commands_use_git_env_without_os_environ_or_keys`, `test_git_timeout_detected_like_bench`; `test_architecture` xanh

## Phần 3, walking skeleton S1 (server, không model; gồm cả bước commit)

- [ ] T12 — DocType `ERP AI Change Proposal` + controller bất biến + helper đề xuất mẫu — [F6: test_utils.py] — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py, erp_ai/test_utils.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T2, T7, T51
  - Criterion: ADR-012 QĐ 1, Ràng buộc (bất biến, quyền JSON); NFR-5; nền AC-5; AC-22 (bố cục git)
  - Receives: bảng trường design 2.1, 2.2, 3.3 (bố cục); hằng (T2); `GitSandbox` (T36, T51; giữ nguyên, chỉ thêm helper cạnh)
  - Returns: DocType `autoname AICHG-.#####`, module `ERP AI agent`, 15 trường nội dung + 9 trường trạng thái, **[Sửa vòng 1]** 9 trường git (`target_branch`, `upstream_ref`, `ahead_count`, `is_core_app`, `commit_message` lúc đề xuất; `applied_branch`, `applied_ahead_count`, `apply_commit_sha`, `undo_commit_sha` ở nhóm trạng thái), `read_only=1`, bố cục `section_git` (`depends_on`), `section_git_result`; `Code`+`read_only=1` cho nội dung/đầu ra; quyền `ERP AI Agent` create+read, `ERP AI Instructor` read, `System Manager` read, không `write/delete/submit/cancel/amend`; controller `validate` từ chối đổi trường nội dung (gồm `target_branch`, `commit_message`) khi `not is_new()`; helper `test_utils`: đề xuất mẫu `Chờ duyệt` (file và lệnh, có điền trường git) bằng `frappe.get_doc(...).insert(ignore_permissions=True)`
  - Expect: `cmd.migrate` thành công; `test_proposal_json_permissions_have_no_write_delete_submit_cancel_amend`, `test_select_options_match_constants`, `test_content_fields_are_code_and_read_only`, `test_content_field_change_on_save_is_refused`, `test_form_layout_git_sections` (thứ tự trường JSON theo 3.3; 9 trường git `read_only=1`)

- [ ] T13 — `transitions`: `prepare_new`, `content_digest`, `log_step`, hook `before_insert` + luật layer — [F6: test_architecture.py] — files: erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/test_transitions.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/changes/test_transitions.py — depends: T4, T11, T12, T43
  - Criterion: AC-3 (không chèn được trạng thái khác `Chờ duyệt`), AC-12, ADR-012 QĐ 2, 5, 7; design 2.3
  - Receives: `write_entry(change)` (T4); DocType (T12); helper đề xuất mẫu (T12)
  - Returns: `InvalidTransition(frappe.ValidationError)`; `STATE_FIELDS` (9 tên + **[Sửa vòng 1]** `applied_branch`, `applied_ahead_count`, `apply_commit_sha`, `undo_commit_sha`); `prepare_new(doc)` đặt `Chờ duyệt`, xóa mọi trường trạng thái; `content_digest(doc)` = sha256 JSON 14 trường theo design 2.3 (9 cũ + `target_branch`, `upstream_ref`, `ahead_count`, `is_core_app`, `commit_message`, `ensure_ascii=False`); `log_step(proposal, step, actor, *, error=None, before=None, after=None) -> str`; controller `before_insert` gọi `prepare_new`; `LAYER_RULES` thêm dòng cho `erp_ai.agent.changes` (cấm `gateway`, `agent.runner`, `agent.run_status`, `eval`, `handlers`, `tasks`, `install`, `erp_ai_agent`) và `erp_ai.agent.tools` cấm import `changes`; sửa luật hiện có nếu việc `changes` gọi `write_entry` làm nó đỏ, theo ADR-012
  - Expect: `test_prepare_new_forces_pending_and_clears_state_fields` (gồm 4 trường git), `test_content_digest_changes_with_any_field` (mỗi trong 14 trường), `test_log_step_writes_one_change_row`; `test_insert_with_non_pending_status_is_forced_pending`; `test_architecture::test_layer_imports` xanh

- [ ] T14 — `transitions`: duyệt, từ chối, xin hoàn tác, bắt đầu áp dụng, `finish` — files: erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/test_transitions.py — test: erp_ai/agent/changes/test_transitions.py — depends: T13
  - Criterion: AC-5, AC-6 (duyệt hai lần/ job lặp không đổi gì), AC-12, NFR-2, NFR-6; ADR-012 QĐ 3, 7; D-2
  - Receives: `prepare_new`, `content_digest`, `log_step` (T13); máy trạng thái design 2.2
  - Returns: `approve(name, user) -> str`, `reject`, `request_undo(name, user)` (chỉ `Thay đổi code` ở `Đã áp dụng`; ghi `undo_by`, `undo_at`), `begin_apply(name) -> bool`, `finish(name, expected, new_status, *, step, actor, reason=None, result=None, fields=None) -> bool` (**[Sửa vòng 1]** `fields` là dict con của 4 trường git; khóa khác → `ValueError`); mỗi phép chuyển: `get_value(..., for_update=True)` rồi so trạng thái rồi `set_value`; sai trạng thái → `InvalidTransition` (method) hoặc `False` (job); câu lỗi từ 3.3; `approve` ghi `decided_by`, `decided_at`, `approved_digest`
  - Expect: `test_each_step_writes_exactly_one_change_row` (7 bước), `test_approve_twice_second_raises_and_logs_nothing`, `test_reject_then_approve_raises`, `test_begin_apply_only_from_approved_and_second_call_false`, `test_finish_with_wrong_expected_does_nothing`, `test_request_undo_refused_for_command`, `test_finish_fields_only_git_keys_else_valueerror`

- [ ] T15 — `enqueue_change_job` + luật enqueue — [F6: test_architecture.py] — files: erp_ai/agent/queue.py, erp_ai/agent/test_queue.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_queue.py — depends: T2, T13
  - Criterion: AC-6 (job áp dụng sau commit, không trùng), ADR-013 QĐ 2
  - Receives: lời gọi `frappe.enqueue` runner hiện có (mẫu 5 tham số)
  - Returns: `enqueue_change_job(proposal_name: str, action: str) -> None`: `action ∉ ("apply","undo")` → `ValueError`; lời gọi thứ hai `frappe.enqueue("erp_ai.agent.changes.apply_job.run_change", queue="long", timeout=JOB_TIMEOUT_S, enqueue_after_commit=True, job_id=f"erp_ai_change::{proposal_name}::{action}", deduplicate=True, proposal_name=..., action=...)`; `check_single_enqueue_site`/`check_enqueue_call_shape` sửa thành đúng 2 lời gọi, đích ∈ {runner, `run_change`}, đủ 5 tham số, chỉ ở `agent/queue.py`
  - Expect: `test_enqueue_change_job_shape`, `test_enqueue_change_job_rejects_unknown_action`, `test_runner_enqueue_unchanged`; `test_architecture` xanh

- [ ] T16 — 3 method POST `approve`/`reject`/`undo` — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T14, T15
  - Criterion: AC-5, AC-7 (từ chối hoàn tác lệnh và trạng thái sai), AC-12; ADR-012 QĐ 4
  - Receives: `transitions.approve/reject/request_undo` (T14), `enqueue_change_job` (T15), `authority.NEVER_AUTHORITY`
  - Returns: `approve(name: str)`, `reject(name: str)`, `undo(name: str)` đều `@frappe.whitelist(methods=["POST"])`; role bằng `frappe.get_roles` và `NEVER_AUTHORITY` → `PermissionError` câu `Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được`; `name` không phải chuỗi/không tồn tại → `DoesNotExistError` `Không có đề xuất <name>` (escape); `approve`, `undo` xếp job sau khi chuyển trạng thái; lỗi thì DB, nhật ký và job không đổi; không `subprocess`, không hàm git của `source` trong method (ADR-022 QĐ 3)
  - Expect: `test_methods_refuse_agent_admin_guest_and_user_without_role`, `test_assigned_user_without_role_cannot_approve`, `test_ok_comment_by_instructor_keeps_pending`, `test_rejected_never_applies`, `test_methods_are_post_only_and_not_guest`, `test_undo_refused_for_command_and_non_applied`, `test_approve_success_enqueues_one_job_and_logs_one_row`

- [ ] T49 — Controller: `commit_message` lúc `insert`, `onload` → `change_notes` — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T16, T41
  - Criterion: AC-22 (form hiện đủ trước duyệt; mã commit sau áp dụng/hoàn tác), AC-17 (bản xem trước thông điệp), AC-21 (cảnh báo ở form), D-14
  - Receives: `change_text.apply_message` (bản xem trước, dòng người duyệt là `<người duyệt>`), `proposal_notes` (T40, T41); chuỗi tĩnh, không HTML thô
  - Returns: `validate` (khi `is_new()`) đặt `commit_message` = bản xem trước, ghi đè giá trị tool truyền (D-14); `onload` đặt `__onload.change_notes` từ `proposal_notes` theo trạng thái (`Chờ duyệt`: cảnh báo; `Đã áp dụng`: câu "Commit áp dụng" + `apply_commit_sha`; `Đã hoàn tác`: `undo_commit_sha`)
  - Expect: `test_form_data_per_state` (3 trạng thái), `test_commit_message_set_by_controller_not_by_tool`, `test_content_field_change_on_save_is_refused` vẫn xanh (gồm `commit_message`)

- [ ] T17 — Form Desk: 3 nút có xác nhận và dòng giới thiệu — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T49
  - Criterion: AC-5 (nút chỉ để tiện; server vẫn kiểm), AC-22, design 3.3 (Form Desk), ADR-022 QĐ 9
  - Receives: đường dẫn 3 method (T16); `__onload.change_notes` (T49)
  - Returns: `frappe.ui.form.on("ERP AI Change Proposal", { refresh(frm) {...} })`: `Duyệt`, `Từ chối` khi `Chờ duyệt`; `Hoàn tác` khi `Đã áp dụng` ∧ `Thay đổi code`; chỉ khi `frappe.user.has_role("ERP AI Instructor")`; mỗi nút `frappe.confirm` rồi `frappe.call({method, args:{name}, type:"POST"})` rồi `frm.reload_doc()`; `set_intro` từ `change_notes`
  - Expect: đỏ rồi xanh `test_form_script_static_rules` (3 tên method, `type: "POST"`, `frappe.confirm`, `set_intro`, không `innerHTML`/`eval(`/`document.write`); bước tay (nút và cảnh báo hiện đúng) ghi vào `dev-notes.md`: ui false, người kiểm sau G4

- [ ] T42 — Bộ chặn: `read_git`, `is_core_app`, tích hợp `GitState` — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T9, T39, T51
  - Criterion: AC-16 (app lõi cho qua khi có trong danh sách; `erp_ai` vẫn bị chặn), AC-18 (lúc đề xuất), ADR-022 QĐ 3
  - Receives: `source.read_git_state`, `GitState` (T38, T39); `CORE_APPS` (T2); `GitSandbox` (T36, T51); `check_write_path` (T7–T9)
  - Returns: `GuardResult` thêm `is_core_app: bool = False`, `git: GitState | None = None`; `check_write_path(..., *, new_file, read_git: bool = True)`: sau các kiểm cũ, `read_git=True` → `read_git_state`; `refusal` → `reason`; cho qua → `git=state`, `is_core_app = app in CORE_APPS`; `read_git=False` (job lúc kiểm lại) không gọi git; không `subprocess` trong file này
  - Expect: `test_core_apps_allowed_only_when_listed` (4 app; có/không trong danh sách), `test_non_core_app_has_no_core_flag`, `test_guard_returns_git_state_when_allowed`, `test_guard_refuses_with_git_reason_and_read_git_false_skips_git`; test T7–T9 xanh (dùng `GitSandbox` hoặc `read_git=False`; cập nhật test cũ chỉ ở cách gọi, không đổi assertion)

- [ ] T18 — `run_change`: bộ khung, khóa chung, commit trạng thái trước khi chạy, kiểm lại — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T5, T9, T14, T15, T40, T42
  - Criterion: AC-6 (job lặp không làm gì; kiểm lại), AC-9 (kiểm lại bộ chặn lệnh), NFR-1, NFR-2; ADR-013 QĐ 1, 4, 5; design 4.3 bước 1–4.2
  - Receives: `begin_apply`, `finish`, `content_digest` (T14); `current_change_settings` (T5); `check_write_path(read_git=False)`, `check_bench_args` (T7–T9, T42); `apply_message` (T40) để dựng thông điệp thật; `filelock`; `COMMAND_TIMEOUT_S`, `TITLE_CHANGE_FAILED` (T2)
  - Returns: `run_change(proposal_name, action) -> None`, không raise; `deadline`; trạng thái ≠ `Đã duyệt` → thoát không ghi; `with filelock("erp_ai_change", is_global=True)` (hết hạn khóa → `Lỗi`); `begin_apply` rồi `_commit()`; kiểm lại 7 điều kiện bảng 4.3 (sai người chạy job, người duyệt mất quyền, công tắc tắt, digest, bộ chặn, `sha256(content_after) == after_hash`, **[Sửa vòng 1]** thông điệp thật khớp `commit_message`) → `finish(→ Lỗi, step="fail")` với lý do đúng chữ; exception bất ngờ → `frappe.log_error(TITLE_CHANGE_FAILED, ...)` và `Lỗi` nếu còn khớp; một dòng `frappe.logger("erp_ai").info(...)` có `commit=%s`, không nội dung file; chưa có nhánh code/lệnh: `apply` sau kiểm lại tạm chưa làm gì
  - Expect: `test_rechecks_fail_without_writing` (công tắc tắt; mất role; digest bị sửa; app bị bỏ khỏi danh sách; sai user phiên; `commit_message` bị sửa), `test_lock_timeout_fails_without_writing`, `test_repeat_job_does_nothing_when_not_approved`, `test_applying_state_committed_before_rechecks_run`

- [ ] T19 — `run_change` nhánh thay đổi code: dấu file, kiểm trước git, ghi, commit, kiểm sau — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T10, T18, T39, T43
  - Criterion: AC-6, AC-17, AC-12 (mã commit), NFR-1, NFR-2, NFR-6, NFR-7; ADR-013 QĐ 6; ADR-022 QĐ 1; D-19 (dấu file trước, git sau); design 4.3 bước 4.3 mục 1–5, 7
  - Receives: khung (T18); `sha256_of`, `write_atomic` (T10); `read_git_state`, `git_head`, `git_commit_summary`, `git_blob` (T38, T39); `git_add_new`, `git_commit_only` (T43); `apply_message`, `safe_person_name` (T40); `GitSandbox` (T36, T51)
  - Returns: nhánh `Thay đổi code`: (1) dấu file: file mới mà đã có, hoặc hash ≠ `base_hash` → `finish(→ Hết hiệu lực, step="stale")`; (2) `read_git_state` (refusal → `Lỗi` với câu đó; giữ `old_head`, `repo`, `rel`); (3) `write_atomic`, hash đọc lại ≠ `after_hash` → `Lỗi` `đọc lại sau khi ghi không khớp` (chưa có trả lại, T45); (4) file mới → `git_add_new`; `git_commit_only(repo, rel, *apply_message(...))`, `limit_s = min(GIT_TIMEOUT_S, max(1, int(deadline − now)))`; (5) kiểm sau `git_commit_summary` (cha = `old_head`, đường dẫn = `(rel,)`, nhánh, `git_blob` = `content_after`); (7) `finish(→ Đã áp dụng, step="apply", fields={apply_commit_sha, applied_branch, applied_ahead_count}, before={sha256, head}, after={sha256, commit, branch})`
  - Expect: `test_apply_writes_exact_approved_bytes` (`\r\n`, `<script>`, không newline cuối, tiếng Việt), `test_apply_creates_one_commit_with_only_target_path` (1 file staged + 1 unstaged khác nguyên trạng; `diff-tree` = [đích]; thông điệp có `AICHG-…`), `test_apply_new_file_commit_adds_only_that_path`, `test_second_approve_and_second_job_change_nothing` (0 commit mới), `test_target_changed_after_proposal_becomes_stale` (0 commit, cả khi người đã commit thay đổi đó), `test_new_file_appeared_meanwhile_becomes_stale`, `test_two_proposals_same_file_second_is_stale` (đúng 1 commit), `test_apply_and_undo_rows_carry_commit_sha` (phần `apply`). Ghi chú: task lớn nhất của S1; nếu dev báo > 5 phút, tech-lead tách phần 4–5 ra, không đổi ID

- [ ] T46 — `run_change`: kiểm trước git, đổi nhánh → `Hết hiệu lực`, khóa git nhanh — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T19
  - Criterion: AC-18 (lúc áp dụng), spec D-1 (nhánh đổi → `Hết hiệu lực`), NFR-3 (khóa git không chờ vô hạn); ADR-022 QĐ 3, 6, 7
  - Receives: nhánh code của T19; `GitSandbox.switch_branch`, `hold_index_lock`, `detach`, `mark_in_progress` (T51)
  - Returns: sau `read_git_state`: `state.branch ≠ target_branch` → `finish(→ Hết hiệu lực, step="stale", reason=GIT_BRANCH_CHANGED)`, không ghi, 0 commit trên cả hai nhánh; `GIT_LOCKED` (khóa git đang bị giữ) → `Lỗi` trong < `GIT_TIMEOUT_S`, không xóa khóa; mã lý do `GIT_*` đúng chữ bảng 3.2
  - Expect: `test_git_precheck_fails_at_apply_without_write_or_commit` (subTest `index.lock`, detached, `MERGE_HEAD`, đích bị `.gitignore` sau, `.git` bị gỡ: file không đổi, 0 commit, `Lỗi` + lý do, 1 dòng `fail`), `test_branch_changed_after_approval_becomes_stale`, `test_index_lock_fails_fast`, `test_other_dirty_files_do_not_block_apply`

- [ ] T45 — `run_change`: commit lỗi hoặc quá giờ → trả lại file (D-17); kiểm sau sai — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T46
  - Criterion: AC-19 (file về từng byte, vùng staged như trước, `Lỗi` có lý do, 1 dòng `fail`), AC-12, D-17, D-2 (spec), ADR-022 QĐ 1, 7; design 4.3 bước 3.3, 3.4, 3.5, 3.6, 5
  - Receives: nhánh code (T19, T46); `remove_created`, `write_atomic` (T10); `git_unstage_new` (T43); `git_head`, `git_commit_summary` (có `author_email`) (T39); `BOT_GIT_EMAIL` (T2)
  - Returns: hàm trả lại (3.6): file sửa → `write_atomic(content_before)` hash = `base_hash`; file mới → `remove_created`, rồi `git_unstage_new` nếu `add` đã thành; kiểm `git_head == old_head` và `read_git_state().refusal is None`, sai → lý do `GIT_RESTORE_FAILED`; lệnh commit lỗi hoặc quá giờ → đọc `git_head` TRƯỚC: bằng `old_head` → trả lại → `Lỗi` `GIT_COMMIT_FAILED` (+ lý do ngắn ≤ 120 ký tự, "(quá thời gian)" khi quá giờ); khác → [Sửa vòng 2] đọc `s = git_commit_summary(repo)`; `s.author_email ≠ BOT_GIT_EMAIL` (HEAD là commit của người) → trả lại (so HEAD với `head_now` thay `old_head`) → `Lỗi` `GIT_COMMIT_FAILED`, không lưu `apply_commit_sha`; là bot → kiểm sau như thành công; kiểm sau [Sửa vòng 2] = `len(s.parents) == 1` và `git_is_ancestor(repo, old_head, s.parents[0]) is True` (không dùng `parents == (old_head,)`, vì commit người có thể xen giữa), cùng `paths == (rel,)`, nhánh, `git_blob`; sai → `Lỗi` `GIT_COMMIT_MISMATCH` + `fields={"apply_commit_sha"}`, không trả lại, không sửa lịch sử; exception sau ghi mà trước `finish` → trả lại (bọc riêng) rồi `finish`; đọc lại sau ghi sai → trả lại
  - Expect: `test_commit_failure_restores_file_and_index` (stub `git_commit_only` mã 1; subTest file sửa và file mới), `test_commit_timeout_restores_file`, `test_commit_reported_failed_but_head_moved_goes_to_postcheck`, `test_postcheck_mismatch_keeps_commit_and_fails`, `test_unexpected_exception_after_write_restores_file`, `test_commit_failed_while_human_commit_moved_head_restores` (của designer; stub tạo commit người trên file khác rồi trả mã 1: file về byte cũ, HEAD = commit người, `GIT_COMMIT_FAILED`, không lưu `apply_commit_sha`), `test_apply_accepted_when_bot_commit_lands_after_human_commit` (Sửa vòng 2, Fix 1; commit tay của người trên cùng nhánh xen giữa lúc đọc `old_head` và commit của bot, bot commit đúng → `Đã áp dụng`; kiểm `parents == (old_head,)` chặt sẽ làm test này đỏ). **Hết T45 là checkpoint S1** (review approve rồi mới mở nhánh tool/runner)

## Phần 4, hoàn tác, lệnh, registry, prompt

- [ ] T20 — `run_change` nhánh `undo`: ghi lại byte cũ và 1 commit hoàn tác — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T45, T35
  - Criterion: AC-7, AC-20 (đúng 1 commit hoàn tác, commit áp dụng vẫn trong lịch sử, file mới bị gỡ khỏi đĩa và khỏi cây), AC-12, NFR-7; ADR-012 QĐ 7; ADR-022 QĐ 1, 6; D-18 (T35 đạt); G-1; design 4.4 bước 1–3, 5–7
  - Receives: `request_undo`, `finish` (T14), `remove_created`, `write_atomic`, `sha256_of` (T10), `git_commit_only`, `undo_message` (T40, T43), `read_git_state`, `git_commit_summary`, `git_blob` (T38, T39), khung kiểm lại (T18). Nếu T35 báo D-18 không đạt → không làm task này, `DESIGN_CONFLICT`
  - Returns: nhánh `action="undo"`: khóa chung; trạng thái `Đang hoàn tác`; kiểm `session.user == undo_by`, role, digest, bộ chặn (`read_git=False`), KHÔNG kiểm công tắc; `sha256_of(full) ≠ after_hash` → `Lỗi` `file đã đổi sau khi áp dụng, không hoàn tác`, 0 commit; `read_git_state(full, new_file=False)`, giữ `old_head`; file mới → `remove_created` rồi kiểm không còn; còn lại `write_atomic(content_before)` hash = `base_hash`; `git_commit_only(...)`; kiểm sau (cha = `old_head`, đường dẫn, `git_blob` = `content_before` hoặc `None`); `finish(→ Đã hoàn tác, step="undo", fields={"undo_commit_sha"}, before={sha256, head}, after={sha256, commit, branch})`; chưa có nhánh lỗi git (T47)
  - Expect: `test_undo_restores_previous_bytes`, `test_undo_removes_created_file`, `test_undo_refused_when_file_changed_after_apply` (0 commit), `test_undo_allowed_with_switch_off`, `test_undo_creates_one_commit_restoring_previous_bytes`, `test_undo_new_file_removes_from_disk_and_tree`

- [ ] T47 — `run_change` hoàn tác: từ chối git và commit hoàn tác lỗi — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T20
  - Criterion: AC-20 (từ chối: không là tổ tiên; điều kiện AC-18), AC-19 (áp cả hoàn tác), D-2 (spec), D-17; design 4.4 bước 4, 6
  - Receives: nhánh `undo` (T20); hàm trả lại (T45); `git_is_ancestor` (T39); `GitSandbox.switch_branch`, `hold_index_lock`, `detach` (T51)
  - Returns: trước khi ghi: `read_git_state.refusal` → `Lỗi`, 0 commit; `git_is_ancestor(repo, apply_commit_sha, state.head)`: `False` → `Lỗi` `GIT_NOT_ANCESTOR`, `None` → `Lỗi` `GIT_ERROR`; commit hoàn tác lỗi/quá giờ → `git_head == old_head` → trả lại `content_after` (file mới tạo lại), hash = `after_hash`, kiểm HEAD và `read_git_state` → `Lỗi` `GIT_COMMIT_FAILED` (hoặc `GIT_RESTORE_FAILED`); HEAD đã đổi → [Sửa vòng 2] cùng quy tắc T45: `git_commit_summary(repo).author_email ≠ BOT_GIT_EMAIL` → trả lại (so HEAD với `head_now`), `Lỗi` `GIT_COMMIT_FAILED`, không lưu `undo_commit_sha`; là bot → kiểm sau; kiểm sau [Sửa vòng 2] = `len(parents) == 1` và `git_is_ancestor(repo, old_head, parents[0]) is True` (không dùng `parents == (old_head,)`); sai → `Lỗi` `GIT_COMMIT_MISMATCH` + `fields={"undo_commit_sha"}`
  - Expect: `test_undo_refused_when_apply_commit_not_ancestor`, `test_undo_refused_on_git_precheck` (`index.lock`, detached), `test_undo_commit_failure_restores_applied_bytes` (subTest stub lỗi và quá giờ; file sửa và file mới); (Sửa vòng 2) `test_commit_failed_while_human_commit_moved_head_restores` (của designer, subTest hoàn tác cùng subTest áp dụng ở T45), `test_undo_accepted_when_bot_commit_lands_after_human_commit` (Fix 1; commit tay của người xen giữa trên cùng nhánh, commit hoàn tác của bot đúng → `Đã hoàn tác`, `undo_commit_sha` lưu; kiểm `parents == (old_head,)` chặt sẽ làm test đỏ)

- [ ] T21 — `run_change` nhánh lệnh `bench` — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T11, T47
  - Criterion: AC-8 (đúng 1 lời gọi, đối số đã duyệt, không shell, cwd bench, có timeout, thứ tự commit trước, **0 lệnh git**), AC-9, NFR-2; ADR-013 QĐ 5, 7; ADR-022 QĐ 1 (lệnh không commit)
  - Receives: `run_bench`, `CommandResult` (T11); khung (T18)
  - Returns: nhánh lệnh: `limit = max(0, int(deadline − time.monotonic()))`, `run_bench(args, limit)`; `not_found` → `Lỗi` `không tìm thấy bench trên máy chủ`; `exit_code ≠ 0` → `Lỗi` `lệnh trả mã <n>`; 0 → `Đã áp dụng`; mọi nhánh lưu `exit_code`, `duration_ms`, `command_output` (≤ 400 dòng) lên đề xuất và `value_after` của dòng log; không gọi hàm git nào
  - Expect: `test_approved_command_runs_once_with_exact_args` (1 lời gọi; đuôi đối số = `command_args`; `timeout -s KILL <n>`; không `shell`; `cwd` = bench; `timeout=`; `start_new_session=True`; 0 lệnh git), `test_applying_state_committed_before_subprocess`, `test_nonzero_exit_and_missing_bench_fail`, `test_approved_command_tampered_to_denied_is_blocked_at_apply`

- [ ] T22 — Lệnh: quá giờ và không lộ khóa — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T21
  - Criterion: AC-10, AC-13 (khóa giả 0 lần trong đề xuất, `tool_result`, log, comment, **thông điệp/metadata commit và env của lệnh git**), NFR-3, NFR-5
  - Receives: nhánh lệnh (T21); `CommandResult.timed_out`
  - Returns: `timed_out` → `Lỗi` `quá thời gian`, `step="fail"`; test gieo khóa giả vào `os.environ` và vào credential, stub in `env` của cả lệnh bench và lệnh git
  - Expect: `test_command_timeout_fails_with_reason`, `test_fake_key_never_in_proposal_result_log_comment` (gồm `git log --format=%an%ae%cn%ce%B` của commit áp dụng và hoàn tác; env git không có khóa), `test_limit_passed_is_remaining_budget`

- [ ] T48 — Test chéo của commit: hook không chạy, ref remote không đổi, metadata sạch — files: erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_job.py — depends: T22, T45, T47
  - Criterion: AC-19 (c: hook repo không chạy), AC-23 (ref remote không đổi), NFR-7, NFR-8, NFR-9 (mixin repo lõi thật), AC-13
  - Receives: toàn bộ `apply_job.py` (T18–T22, T45–T47); `GitSandbox.install_marker_hooks`, `add_remote`, `refs`, `log_meta`, `RealCoreReposUntouchedMixin` (T51); chỉ thêm test, không đổi `apply_job.py` (nếu test đỏ do mã → `NEEDS_CONTEXT`/mở task sửa)
  - Returns: lớp test dùng `RealCoreReposUntouchedMixin`; chỉ file test
  - Expect: `test_repo_hooks_never_run` (6 hook; áp dụng và hoàn tác thành công; 0 tệp đánh dấu), `test_remote_refs_and_other_branches_unchanged_after_apply_and_undo` (kể cả ref trên remote bare tạm), `test_commit_metadata_has_no_email_url_or_token` (HOME giả có `.gitconfig` email thật; URL `x-token-FAKE`; họ tên người duyệt chứa `@` → tác giả = `ERP AI Agent <erp-ai-agent@bot.invalid>`; 0 lần trong `git log`, comment, `__onload`, trường đề xuất)

- [ ] T40 — `change_text.py`: thông điệp commit và `safe_person_name` — files: erp_ai/agent/change_text.py, erp_ai/agent/test_change_text.py — test: erp_ai/agent/test_change_text.py — depends: T2
  - Criterion: AC-17 (mẫu thông điệp: mã đề xuất, số phiếu, họ tên người duyệt), AC-20 (thông điệp hoàn tác có mã commit áp dụng), NFR-8; ADR-022 QĐ 5; design 3.9
  - Receives: `BOT_GIT_*` (T2); mẫu 3.9; chỉ import thư viện chuẩn và `erp_ai.constants`
  - Returns: `safe_person_name(name) -> str` (loại `@`, `://`, xuống dòng, ký tự điều khiển; ≤ giới hạn 3.9; rỗng/`None` → giá trị thay thế theo 3.9), `apply_message(name, ticket, file_path, approver) -> tuple[str, str]` (subject, body), `undo_message(name, ticket, file_path, apply_commit, undoer)`, `message_text(subject, body)`; bản xem trước chỉ khác ở dòng người duyệt
  - Expect: `test_apply_message_template_and_preview`, `test_safe_person_name` (`@`, `://`, xuống dòng, điều khiển, 200 ký tự, rỗng, `None`), `test_undo_message_has_apply_commit_and_undoer`

- [ ] T41 — `change_text.py`: `proposal_notes` (nhánh, upstream, cảnh báo app lõi) — files: erp_ai/agent/change_text.py, erp_ai/agent/test_change_text.py — test: erp_ai/agent/test_change_text.py — depends: T40
  - Criterion: AC-21 (tên nhánh; `origin/<n>`, số commit đi trước; cảnh báo app lõi 3 ý; app khác không có; URL 0 lần), AC-22 (văn bản form), NFR-8
  - Receives: câu cảnh báo 3.9 (mọi site trên bench; `bench update` có thể xung đột hoặc, với `--reset`, xóa; đẩy lên fork là việc của người); chuỗi chỉ từ trường đề xuất, không từ git
  - Returns: `proposal_notes(proposal_fields) -> list[str]` (comment và `change_notes` dùng chung); có/không `upstream_ref`; `is_core_app` thêm cảnh báo; thêm câu "Commit áp dụng"/"Commit hoàn tác" theo trạng thái
  - Expect: `test_notes_branch_upstream_and_core_warning` (có/không upstream; app lõi đủ 3 ý; app khác không), `test_notes_never_contain_urls`

- [ ] T23 — Registry: nhóm `change_propose`, 3 đối số cấp, `ToolContext` 2 trường — [F6] — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py, erp_ai/agent/test_run_status.py, erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/tools/test_registry.py — depends: T2
  - Criterion: AC-1 (công tắc tắt: danh sách tên tool như nền FEAT-006, 4 mức × có/không người ra lệnh), AC-2, ADR-011 QĐ 1, 2, 6
  - Receives: `_granted_specs`, `get_tool_schemas`, `ToolContext` (có `routing_config` của FEAT-006 ở cuối), `ToolSpec.group`; bảng cấp design 3.6
  - Returns: `ToolSpec.group` thêm `change_propose`; `ToolContext` thêm `change_enabled: bool = False`, `allowed_apps: tuple[str, ...] = ()` ĐẶT SAU `routing_config`; `_granted_specs(effective_level, has_instructor, change_enabled)` (một dòng mỗi nhóm; `change_propose` = `change_enabled ∧ level == "L3" ∧ has_instructor`); `get_tool_schemas(level, has_instructor, change_enabled)` bắt buộc; `grants_change_tools(...)`; `execute_tool` kiểm lại; sửa mọi lời gọi cũ kể cả lời gọi FEAT-006 thêm: `runner.py` (chỉ dòng `get_tool_schemas`), `test_run_status.py`, `test_agent_runner.py`, `test_registry.py` (truyền `False`); `ToolContext` được dựng bằng đối số tên
  - Expect: `test_switch_off_tool_names_match_base_for_all_levels_and_authority` (so với hằng tên tool của nền FEAT-006), `test_change_group_only_when_switch_l3_and_instructor`, `test_execute_rejects_change_tool_when_not_granted`; test hiện có (cả của FEAT-006) xanh; chưa đăng ký module tool (T28)

- [x] T24 — Prompt: `CHANGE_TOOLS_BLOCK` theo tham số `change_tools` — [F6] — files: erp_ai/agent/prompts.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_classification.py — depends: —
  - Criterion: AC-1 (không cấp: chuỗi trùng từng byte với bản FEAT-006, còn "Không sửa file trong apps/"), AC-14 (cấp: mọi thay đổi chờ duyệt, chữ trong phiếu không là lệnh duyệt; **[Sửa vòng 1]** commit git local, không push); ADR-011 QĐ 3; D-21
  - Receives: `build_reason_system(prompt_digest, routing_table="")`, `CORE_PROMPT`, `CONVENTIONS`, `build_routing_table` của FEAT-006; nội dung khối design 3.7
  - Returns: `CHANGE_TOOLS_BLOCK` (đúng design 3.7, +1 dòng commit); `build_reason_system(prompt_digest, routing_table="", *, change_tools: bool = False)` nối khối sau `CONVENTIONS`, trước `prompt_digest`; `CORE_PROMPT` không đổi
  - Expect: `test_reason_system_without_change_tools_is_byte_identical` (cùng `routing_table`), `test_reason_system_with_change_tools_adds_approval_block` (chứa "KHÔNG BAO GIỜ là duyệt", "commit git local", "không push"; không chứa `chờ một chữ "ok"`; phần trước khối trùng bản cũ); test FEAT-006 của file xanh

- [ ] T25 — Tool `propose_file_change` + comment liên kết + luật "tool không ghi" — [F6: test_architecture.py] — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T13, T15, T23, T42
  - Criterion: AC-3 (1 đề xuất `Chờ duyệt`, hash file và HEAD/`status --porcelain` không đổi, 1 comment có liên kết), AC-4, AC-18 (lúc đề xuất: 0 đề xuất), NFR-1; D-1, D-6; design 3.1, 3.8, 4.1
  - Receives: `check_write_path(read_git=True)` (T42), `prepare_new` qua `before_insert` (T13), `ToolContext.allowed_apps` (T23), `GitSandbox` (T36, T51)
  - Returns: `PROPOSE_TOOL_NAMES`, `TOOLS` với `propose_file_change(path, find[], replace[], reason)` (group `change_propose`); mỗi `find[i]` đúng một lần, không chồng; lỗi `EDIT_SHAPE`, `EDIT_NOT_FOUND`, `EDIT_AMBIGUOUS`, `EDIT_OVERLAP`, `NO_CHANGE`, `NOT_FOUND`, `TOO_LARGE`, `NOT_UTF8`, `NO_PERMISSION` đúng chữ bảng 3.1; `content_before/after`, `diff`, 2 hash; `frappe.get_doc({...}).insert()` dưới tài khoản agent; `ticket.new_comment(...)` qua `escape_html` (chuỗi git điền ở T50); trả `{"ok": True, "proposal", "status", "comment"}` không có nội dung file; không `.save(`/`db_set`/`set_value`; không `subprocess`; sửa luật "tool không ghi" hiện có nếu `insert` làm nó đỏ
  - Expect: `test_file_change_creates_pending_proposal_and_comment_without_touching_disk` (hash và HEAD trước = sau), `test_edit_errors_create_nothing`, `test_tool_cannot_insert_non_pending_state`, `test_each_guard_refusal_creates_zero_proposals`, `test_git_refusal_creates_zero_proposals` (0 đề xuất, 0 comment), `test_comment_escapes_html_and_adds_restart_note_for_py`

- [ ] T26 — Tool `propose_new_file` — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T25
  - Criterion: AC-3 (file không được tạo), AC-4 (không có thao tác xóa/đổi tên; `content=""` bị schema chặn), AC-18 (file mới bị `.gitignore` bị chặn lúc đề xuất)
  - Receives: tool và hàm dùng chung trong T25
  - Returns: `propose_new_file(path, content, reason)` (`content` minLength 1, ≤ 20000); lỗi `EXISTS`, `NO_PARENT`; `is_new_file=1`, `base_hash=""`, `content_before=""`
  - Expect: `test_new_file_proposal_does_not_create_file`, `test_new_file_errors_exists_and_no_parent`, `test_no_delete_or_rename_operation_exists`

- [ ] T27 — Tool `propose_bench_command` — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T26
  - Criterion: AC-8 (đề xuất lệnh: `Chờ duyệt`, 0 lời gọi tiến trình con), AC-9, NFR-1
  - Receives: `build_bench_args`, `check_bench_args` (T9); `frappe.local.site`
  - Returns: `propose_bench_command(command enum, app, reason)`; server dựng `command_args` theo bảng 3.1; `reversible=0`; comment thêm câu `Lệnh bench không hoàn tác được.`; không có trường git (rỗng/0)
  - Expect: `test_command_proposal_makes_zero_subprocess_calls`, `test_bench_command_tool_refuses_enum_outside_and_app_misuse`, `test_command_args_built_by_server_for_each_command`

- [ ] T50 — `propose_change`: 4 trường git và comment theo `proposal_notes` — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T27, T39, T41
  - Criterion: AC-16 (đề xuất app lõi tạo được), AC-21 (comment có nhánh, upstream, ahead, cảnh báo; URL 0 lần), NFR-8, D-14
  - Receives: `GuardResult.git`, `is_core_app` (T42); `proposal_notes` (T41); `GitSandbox.add_remote` (T51)
  - Returns: đề xuất file điền `target_branch`, `upstream_ref`, `ahead_count`, `is_core_app` từ `GuardResult` (không từ model); comment dựng từ `proposal_notes`; `commit_message` do controller đặt (T49), tool không truyền
  - Expect: `test_core_app_proposal_created_when_listed`, `test_comment_shows_branch_upstream_ahead_and_core_warning` (URL và `x-token-FAKE` 0 lần), `test_non_core_app_comment_has_no_core_warning`, `test_tool_cannot_set_git_fields_or_commit_message`

- [ ] T28 — Đăng ký module tool vào registry — [F6] — files: erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_registry.py — depends: T23, T27
  - Criterion: AC-2, AC-1 (công tắc tắt: vẫn 11 tool như nền)
  - Receives: `propose_change.TOOLS` (T25–T27); `TOOL_MODULES` (không đổi bởi FEAT-006)
  - Returns: `TOOL_MODULES` thêm `propose_change`; `len(_all_specs())` 11 → 14, ma trận cấp dùng tool thật
  - Expect: `test_all_specs_collects_tools_of_each_module`, `test_all_specs_count_is_14`; ma trận T23 chạy lại với 3 tool thật

## Phần 5, runner, luật kiến trúc, cài đặt

- [ ] T29 — Runner: cấp tool và prompt theo kết quả cấp — [F6] — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T5, T24, T28
  - Criterion: AC-1, AC-2 (vượt ngân sách → `L1` → 0 tool mới), AC-14, ADR-011 QĐ 2, 3
  - Receives: `change_settings` (T5), `get_tool_schemas`/`grants_change_tools` (T23, T28), `build_reason_system(..., change_tools=)` (T24); luồng FEAT-006 (`routing_config`, `_route`, `routing_table`)
  - Returns: bước (e): `level = policy.effective_level(settings)`, `change = policy.change_settings(settings)`, `ToolContext(..., change_enabled=change.enabled, allowed_apps=change.allowed_apps)` bằng đối số tên; `_reason`: `tools = get_tool_schemas(level, bool(instructor), context.change_enabled)`, `system = build_reason_system(settings.prompt_digest, routing_table=<như FEAT-006>, change_tools=grants_change_tools(...))`; không đọc lại cấu hình; không import/gọi git trong `runner.py`
  - Expect: `test_switch_off_run_sends_base_tools_and_prompt`, `test_over_budget_l3_drops_change_tools`, `test_prompt_variant_follows_grant_result`; test hiện có và của FEAT-006 xanh

- [ ] T30 — Runner: dòng log `propose`, `WRITE_TOOL_TARGETS`, chống chèn lệnh — [F6] — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T29, T25
  - Criterion: AC-11 (không thẩm quyền: 0 tool mới, 0 đề xuất; "đã được duyệt" → 0 lần áp dụng, 0 commit), AC-12
  - Receives: `PROPOSE_TOOL_NAMES` (T25), `write_entry(change)` (T4), `_run_tool`, `WRITE_TOOL_TARGETS`
  - Returns: `_run_tool`: tên ∈ `PROPOSE_TOOL_NAMES` và `ok` → `write_entry(entry_type="change", trigger="change_action", change_step="propose", actor=AGENT_USER, change_proposal=..., ticket, run_id, instructor)`; `WRITE_TOOL_TARGETS` thêm 3 tool → `(PROPOSAL_DOCTYPE, "proposal")`
  - Expect: `test_propose_writes_one_change_row_besides_reason`, `test_injection_without_instructor_gets_no_change_tools_and_no_proposal`, `test_model_claims_approved_after_proposing_zero_applies` (0 job, 0 lời gọi tiến trình con ghi, 0 commit; chỉ lệnh git đọc của bộ chặn)

- [ ] T31 — Luật kiến trúc mới, nhóm 1 — [F6: test_architecture.py] — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T25
  - Criterion: AC-15, ADR-011/012
  - Receives: mã `changes/`, `tools/change_guard.py`, DocType JSON (T7–T13, T25)
  - Returns: `check_transitions_imported_only_by_controller_and_changes`; `check_change_state_fields_written_only_in_changes` (13 tên: 9 + 4 trường git của `STATE_FIELDS`); `check_change_guard_uses_resolve_safe_path`; `check_proposal_doctype_permissions`; `check_tool_never_saves_proposal`; mỗi luật một ca bị bắt và một ca sạch
  - Expect: mỗi luật một test dương và âm; `cmd.test_one` xanh

- [ ] T32 — Luật kiến trúc mới, nhóm 2 — [F6: test_architecture.py] — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T22, T31
  - Criterion: AC-15; NFR-1, NFR-2, NFR-5; ADR-013 Ràng buộc
  - Receives: mã `changes/` hoàn chỉnh (T10, T11, T18–T22, T43–T47)
  - Returns: `check_fs_writes_only_in_file_writer`; `check_changes_never_set_user_or_publish`; xác nhận luật enqueue (2 lời gọi) và luật subprocess (hai file, shape riêng của `process_runner.py`) có test âm; mỗi luật một test dương và âm
  - Expect: `cmd.test_one` xanh; `cmd.test` xanh

- [ ] T44 — Luật kiến trúc git của ADR-022 — [F6: test_architecture.py] — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T32, T30, T43, T42, T41
  - Criterion: AC-23 (không đường nào push/đổi nhánh), AC-15, NFR-8; ADR-022 QĐ 2, 3, 4, 5, 8, Ràng buộc; design 8.2 phần Sửa vòng 1
  - Receives: mã hoàn chỉnh (`source.py`, `process_runner.py`, `change_text.py`, `change_guard.py`, `runner.py`, controller); luật của T37, T43
  - Returns: `LAYER_RULES` thêm `erp_ai.agent.change_text` (chỉ thư viện chuẩn và `erp_ai.constants`); `test_git_subcommands_only_allowed_sets_per_file` (`source.py` ∈ `{log, blame}` ∪ `GIT_READ_SUBCOMMANDS`; `process_runner.py` ∈ `{add, commit, rm}`; file khác không có `"git"` làm phần tử `argv`); `test_no_forbidden_git_operations_in_product` (30 lệnh con cấm; chuỗi `get-url`, `ls-remote`, `remote.`, `--amend`, `update-ref`; không đọc `.git/config`); `test_git_commit_add_rm_argv_shape`; `test_git_env_single_definition`; `test_bot_identity_constants`; `test_no_git_in_web_and_runner` (controller, `@frappe.whitelist`, `handlers.py`, `runner.py`); `test_bench_allowlist_has_no_git_running_subcommands`; `test_apps_root_single_function`; mỗi luật một ca bị bắt và một ca sạch
  - Expect: `cmd.test_one` xanh với từng luật dương và âm; luật cũ giữ nguyên

- [x] T33 — Test: người duyệt vào được Desk — [F6] — files: erp_ai/tests/test_install.py — test: erp_ai/tests/test_install.py — depends: —
  - Criterion: AC-5 (người có `ERP AI Instructor` vào được form để bấm nút), D-11, design mục 5
  - Receives: `install._ensure_roles` (hiện có, không sửa); `frappe.get_doc("User", ...)`; test FEAT-006 trong file giữ nguyên
  - Returns: test mới cạnh test cũ, không sửa `install.py`
  - Expect: `test_instructor_role_has_desk_access_and_makes_system_user`: role `desk_access=1` sau khi chạy lại cài đặt; user chỉ có `ERP AI Instructor` → `System User`; user không có role nào có `desk_access` → `Website User`; tạo và xóa user qua `addCleanup(frappe.db.rollback)`

## Checkpoint cuối (tech-lead, không giao dev)

- [ ] T34 — Chạy `cmd.test`, `cmd.lint`, `cmd.migrate` lên/xuống/lên, kiểm AC-15 và NFR-9, `diff.patch` — files: docs/team/features/FEAT-004/diff.patch, docs/team/features/FEAT-004/tasks.md — test: `cmd.test` (cả app) — depends: T1..T33, T35..T51
  - Criterion: AC-15 (`ls docs/team/adr/` có ADR-011/012/013/022 tham chiếu ADR-005; ADR-022 ghi: commit local được phép, không push, không đổi nhánh, không sửa lịch sử, cách hoàn tác), mọi AC, NFR-9; STD-CI-2
  - Receives: mọi review approve
  - Returns: đầu ra thật của `cmd.test`, `cmd.lint`, `ls docs/team/adr/`; đối soát: số dòng `ERP AI Log`, `runs_today`, `spent_this_month_usd`, trường cũ `ERP AI Setting` (gồm trường FEAT-006) trước = sau; `git -C apps/<app> rev-parse HEAD` và `status --porcelain` của `frappe`, `erpnext`, `helpdesk`, `hrms` trước/sau `cmd.test` (NFR-9, chỉ đọc); `.team/active-build` đã xóa; `diff.patch` đã ghi
  - Expect: tất cả xanh; lệch → không tick, đi tìm nguyên nhân
