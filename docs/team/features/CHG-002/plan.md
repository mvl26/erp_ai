Feature: CHG-002
Stage: plan
Author-agent: tech-lead
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 tắt (config.json), để trống. -->

# Plan CHG-002

- Nhánh feature: `team/CHG-002`, **chưa tạo** (team-leader: chưa có nhánh hay worktree ở bước plan); `/team:build` tạo từ `develop` (lúc lập plan là `2fd42ad`). `config.base_branch` ghi `main` nhưng repo không có nhánh `main`; design §1.6 và quyết định của người ngày 2026-11-13 dùng `develop`.
- Số task: 52 (T0..T51; T51 là checkpoint của tech-lead); song song tối đa: 4 dev theo yêu cầu của team-leader (`devs=` trong handoff build quyết định; `limits.max_parallel_dev` của config đang ghi 2, không có `devs=` thì dùng 2 làn đầu rồi tới 2 làn sau).
- Nguồn: `spec.md` (con trỏ tới FEAT-004 Amendment 4), `design.md` (§ = mục của design), ADR-040.
- Mọi `cmd.test_one`, `cmd.test`, `cmd.migrate` chạy qua khóa `.team/miyano-site.lock` (phiên FEAT-007 dùng chung site `miyano`).

## Thứ tự
1. **T0** (T-0 của design §8.0): test đặc tả `git commit --only` ghi nhận file đã xóa. Đỏ thì dừng cả kế hoạch, cần ADR mới.
2. **T1** walking skeleton. Không task nào khác bắt đầu trước khi review T1 là `approve`.
3. **Nền, không phụ thuộc nhau** (T2..T25, T31, T46): helper test, luật văn bản, `file_writer`, `process_runner`, bộ chặn, `transitions`, bộ chuyển đổi, câu chữ, controller, kiểm restart, prompt. Phần rủi ro cao làm sớm: T7 (đổi chữ ký commit), T10 (symlink, kho lồng), T14 (luật restart).
4. **Tool đề xuất** (T26..T30): cần bộ chặn khối (T14).
5. **Job áp dụng và hoàn tác** (T33..T40): một chuỗi trên `apply_job.py`, cần T7, T14, T18, T22.
6. **Test nghiệm thu theo AC** (T41..T45): giới hạn, một lần duyệt, không tự duyệt, không lọt khóa, ma trận 40 phép thử.
7. **Luật kiến trúc** (T47..T49) và **T50** (giá trị trần mỗi file theo phán quyết C-1).
8. **T51** checkpoint cuối của tech-lead (không giao dev): cả app trong một lần giữ khóa site, lint, migrate lên/xuống/lên, `diff.patch`.

## Nhóm song song
Tối đa 4 dev cùng lúc. Hai task chung file không bao giờ chạy cùng lúc (bảng "Một file một chủ"); trong một nhóm, không file nào xuất hiện ở hai làn. Mũi tên là thứ tự trong làn. Nhóm chỉ là khung: task nào đủ `depends:` và không chung file với task đang chạy thì giao ngay, không chờ cả nhóm tick; merge từng task một.

| Nhóm | Làn 1 | Làn 2 | Làn 3 | Làn 4 |
|---|---|---|---|---|
| 0 (tuần tự) | T0 → T1 | — | — | — |
| A (sau T1) | bộ chặn: T3 → T4 → T9 → T10 → T11 → T12 → T13 → T14 | ghi file và git: T5 → T6 → T7 → T8 | trạng thái và comment: T15 → T16 → T17 → T31 → T32 (T32 cần T2) | nhỏ, rời nhau: T2 → T19 → T20 → T21 → T18 → T23 → T46 |
| B | tool: T26 → T27 → T28 → T29 → T30 (cần T14, T2; T30 cần T20) | job: T33 → T34 → T35 → T36 → T37 → T38 → T39 → T40 (cần T7, T14, T18, T22, T2; T38 cần T8, T17, T32) | luật kiến trúc: T47 → T48 (cần T8; T48 cần T11, T6) | controller và form: T22 → T24 → T25 (cần T19, T2; T24 cần T23, T17; T25 cần T21) |
| C | nghiệm thu: T41 → T42 → T43 (cần T40, T29, T24) | ma trận AC-53: T44 → T45 (cần T40, T30) | T49 (cần T48, T9, T29) | — |
| D (tuần tự) | T50 → T51 | — | — | — |

- Làn 4 của nhóm B (T22 → T24 → T25) bắt đầu ngay khi T19 và T2 xong, tức còn trong nhóm A: nó chỉ chạm ba file của controller. T33 chờ T22.
- File theo làn, nhóm A: làn 1 `source.py`, `test_source.py`, `change_guard.py`, `test_change_guard.py`, `test_propose_change.py`; làn 2 `file_writer.py`, `process_runner.py`, `apply_job.py`, `test_apply_job.py`, hai file test của chúng, `test_architecture.py`; làn 3 `transitions.py`, `result_comment.py` và test; làn 4 `test_utils.py`, `tests/test_test_utils.py`, `change_text.py`, `block.py`, `restart_check.py`, `prompts.py` và test.
- Đường găng (23 task): T0 → T1 → T3 → T4 → T9..T14 → T33..T40 → T41..T43 → T50 → T51.
- `test.shared_state` (một site `miyano`): khi từ 2 dev trở lên đang chạy, dev chỉ chạy `cmd.test_one`; `cmd.test` cả app chạy sau mỗi merge, khi giữ khóa site.
- Ma trận vành đai AC-53 là hai task riêng (T44, T45) trên file riêng `test_block_boundary.py`.

## Shared constraints
Chép nguyên văn từ design; mọi task thừa hưởng. Số dòng `file:line` trong design là của `develop` @ `2fd42ad`: dò lại bằng tên hàm.

**Tên DocType và trường** (§2.1, §2.2):
- DocType con `ERP AI Change Operation`, `istable = 1`, module `ERP AI agent`, mọi trường `read_only = 1`: `operation` (Select `Sửa` / `Tạo` / `Xóa` / `Đổi tên`), `file_path`, `new_path`, `content_before`, `content_after`, `base_hash`, `after_hash`.
- Trường thêm trên `ERP AI Change Proposal`: `operations` (Table), `command_list` (Code JSON), `command_results` (Code JSON), `created_dirs` (Code JSON), `restart_status` (Select rỗng / `Đã gửi` / `Đã xác nhận` / `Chưa xác nhận` / `Lỗi khởi chạy`), `restart_sent_at` (Datetime).
- `command_results`: `[{"args":[…],"exit_code":int|null,"duration_ms":int,"timed_out":bool,"output":str}]`.

**Hằng trong `erp_ai/constants.py`, khối "CHG-002" ở cuối file** (§2.5; tên `CHANGE_OP_*` và `RESTART_STATUS_*` do plan này đặt, T1 tạo, mọi task dùng đúng tên):
- `OPERATION_DOCTYPE = "ERP AI Change Operation"`
- `CHANGE_OP_EDIT = "Sửa"`, `CHANGE_OP_CREATE = "Tạo"`, `CHANGE_OP_DELETE = "Xóa"`, `CHANGE_OP_RENAME = "Đổi tên"`, `CHANGE_OPS = (CHANGE_OP_EDIT, CHANGE_OP_CREATE, CHANGE_OP_DELETE, CHANGE_OP_RENAME)`
- `RESTART_STATUS_SENT = "Đã gửi"`, `RESTART_STATUS_CONFIRMED = "Đã xác nhận"`, `RESTART_STATUS_UNCONFIRMED = "Chưa xác nhận"`, `RESTART_STATUS_LAUNCH_FAILED = "Lỗi khởi chạy"`
- `CHANGE_MAX_FILE_OPS = 50`, `CHANGE_MAX_TOTAL_BYTES = 8 * 1024 * 1024`, `CHANGE_MAX_COMMANDS = 6`
- `RESTART_WEB_STOP_S = 40`, `RESTART_TIMEOUT_S = JOB_TIMEOUT_S + RESTART_WEB_STOP_S + JOB_SAFETY_MARGIN_S` (= 700), `RESTART_LAUNCH_TIMEOUT_S = 10`
- Xóa `PROPOSAL_TEXT_MAX_CHARS`, `REPLACE_MAX_ITEMS` (T29).
- Giới hạn mỗi file: chỉ một tên, `source.TEXT_MAX_BYTES` (= `SEARCH_FILE_MAX_BYTES` cho tới T50).

**Chữ ký** (§3.2–§3.6):
- `source.text_refusal(rel_path: str, data: bytes | None = None) -> str | None`
- `change_guard.check_write_path(rel_path, allowed_apps, *, new_file, read_git=True) -> GuardResult` (giữ chữ ký)
- `change_guard.FileOp` (dataclass frozen): `kind`, `path`, `new_path`, `before: str | None`, `after: str | None`, `base_hash`, `after_hash`; `kind` là một giá trị của `CHANGE_OPS`
- `change_guard.check_block(ops, commands, allowed_apps, site, *, at_apply: bool, legacy: bool = False) -> BlockCheck`; `BlockCheck(reason, app, targets)`; `OpTarget(op, full_path, full_new_path, new_dirs, guard)`
- `change_guard.RESTART_COMMAND = "restart"`; hình dạng duy nhất `["restart"]`
- `block.is_block(doc) -> bool`, `block.operations_of(doc) -> tuple[FileOp, ...]`, `block.commands_of(doc) -> list[list[str]]`
- `process_runner.git_commit_only(repo_root, rels: tuple[str, ...], subject, body, limit_s)`; `process_runner.launch_restart() -> tuple[bool, str | None]`; `process_runner.RESTART_ARGV`
- `file_writer.make_parents(full_path, app_dir) -> list[str]`, `file_writer.remove_file(full)`, `file_writer.remove_empty_dirs(dirs) -> list[str]`
- `transitions.record_commit(name, expected, *, fields) -> bool`, `transitions.finish(…, command_results=None)`, `transitions.record_restart(name, expected, value, sent_at) -> bool`, `transitions.confirm_restart(name, value) -> bool`
- `change_text.apply_message(proposal, ticket, label, approver, operations=None)`, `change_text.undo_message(…, operations=None)`; `operations=None` cho ra đúng chữ cũ; `change_text.block_label(operations) -> str` (đường dẫn khi 1 mục, `{n} file` khi nhiều hơn; tên do plan đặt, T19 tạo)
- `result_comment.post_restart_notice(name, action)`
- `restart_check.outcome(sent_epoch, now_epoch, web, workers)` trả `RESTART_STATUS_CONFIRMED`, `RESTART_STATUS_UNCONFIRMED` hoặc `None`
- Phương thức whitelisted mới `confirm_restart(name)` (POST) trả `{"name", "restart_status"}`
- `test_utils.make_block_proposal(operations, commands, **fields)` (T2)

**Câu từ chối:** đúng từng chữ theo bảng §3.1 (hằng ở `change_guard.py`; nhóm `TEXT_*` ở `source.py`). Tiền tố `mục {n} ({đường dẫn}): ` và `lệnh {n}: `, n đếm từ 1.

**Câu cho người đọc:** đúng từng chữ theo §3.7 (comment đề xuất, comment trước restart, comment kết quả, nhãn restart, thân prompt).

**Luật chung của build:**
- Ba tên tool giữ nguyên (D-1). Không sửa `site_api.py`, `registry.py`, `policy.py`, `runner.py`, `erp_ai_setting.json`, `queue.py`, `hooks.py`, `patches.txt`.
- Chiều import: `changes/` import `tools/`; `tools/` không import `changes/`.
- Mọi test git, thư mục, xóa, đổi tên chạy trên `GitSandbox` hoặc `TempAppsRoot`; restart luôn là stub `process_runner.launch_restart`, không bao giờ chạy `bench restart` thật.
- Test cũ chỉ được sửa ở các nhánh liệt kê tại §8.3 "Test cũ phải sửa"; không sửa assertion cho khớp mã (STD-TEST-5).
- Không có patch dữ liệu; `cmd.migrate` chỉ đồng bộ DocType.

## Một file một chủ
Đường dẫn tính từ gốc repo. `P/` = `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/`. "Thứ tự" là chuỗi `depends:` bắt buộc.

| File | Task chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| `docs/team/features/CHG-002/diff.patch` | T51 (tech-lead) | — | — |
| `erp_ai/constants.py` | T1 | T29, T50 | T1 → T29 → T50 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/*` (3 file mới) | T1 | — | — |
| `P/erp_ai_change_proposal.json` | T1 | — | — |
| `P/erp_ai_change_proposal.py` | T1 | T22, T24 | T1 → T22 → T24 |
| `P/erp_ai_change_proposal.js` | T25 | — | — |
| `P/test_erp_ai_change_proposal.py` | T22 | T24, T25 | T22 → T24 → T25 |
| `erp_ai/agent/tools/source.py` | T3 | T4, T49, T50 | T3 → T4 → T49 → T50 |
| `erp_ai/agent/tools/test_source.py` | T3 | T4, T49 | T3 → T4 → T49 |
| `erp_ai/agent/tools/change_guard.py` | T1 | T9..T14 | T1 → T9 → T10 → T11 → T12 → T13 → T14 |
| `erp_ai/agent/tools/test_change_guard.py` | T9 | T10..T14 | T9 → … → T14 |
| `erp_ai/agent/tools/propose_change.py` | T1 | T26..T30 | T1 → T26 → T27 → T28 → T29 → T30 |
| `erp_ai/agent/tools/test_propose_change.py` | T9 | T26..T30 | T9 → T26 → … → T30 |
| `erp_ai/agent/tools/test_registry.py` | T29 | T1 (có điều kiện: chỉ assertion ghim `required`) | T1 → T29 |
| `erp_ai/agent/changes/block.py` | T1 | T18 | T1 → T18 |
| `erp_ai/agent/changes/test_block.py` | T18 | T40 | T18 → T40 |
| `erp_ai/agent/changes/restart_check.py`, `test_restart_check.py` | T23 | — | — |
| `erp_ai/agent/changes/file_writer.py`, `test_file_writer.py` | T5 | T6 | T5 → T6 |
| `erp_ai/agent/changes/process_runner.py` | T7 | T8 | T7 → T8 |
| `erp_ai/agent/changes/test_process_runner.py` | T0 | T7, T8 | T0 → T7 → T8 |
| `erp_ai/agent/changes/transitions.py` | T1 | T15, T16, T17 | T1 → T15 → T16 → T17 |
| `erp_ai/agent/changes/test_transitions.py` | T15 | T16, T17 | T15 → T16 → T17 |
| `erp_ai/agent/changes/result_comment.py`, `test_result_comment.py` | T31 | T32 | T31 → T32 |
| `erp_ai/agent/changes/apply_job.py` | T1 | T6, T7, T33..T40 | T1 → T6 → T7 → T33 → … → T40 |
| `erp_ai/agent/changes/test_apply_job.py` | T6 | T7, T33, T36 | T6 → T7 → T33 → T36 |
| `erp_ai/agent/changes/test_apply_block.py` | T1 | T33..T43, T50 | T1 → T33 → … → T40 → T41 → T42 → T43 → T50 |
| `erp_ai/agent/changes/test_block_boundary.py` | T44 | T45 | T44 → T45 |
| `erp_ai/agent/change_text.py`, `erp_ai/agent/test_change_text.py` | T19 | T20, T21 | T19 → T20 → T21 |
| `erp_ai/agent/prompts.py`, `erp_ai/agent/test_classification.py`, `erp_ai/agent/test_agent_runner.py` | T46 | — | — |
| `erp_ai/test_utils.py`, `erp_ai/tests/test_test_utils.py` | T2 | — | — |
| `erp_ai/tests/test_architecture.py` | T7 | T47, T48, T49 | T7 → T47 → T48 → T49 |
| `erp_ai/test_change_decision.py` (có điều kiện) | T7 | — | — |

## Touchpoint → task (design §7)
| Touchpoint | Task |
|---|---|
| `erp_ai/agent/tools/source.py` | T3, T4, T49, T50 |
| `erp_ai/agent/tools/change_guard.py` | T1, T9, T10, T11, T12, T13, T14 |
| `erp_ai/agent/tools/propose_change.py` | T1, T26, T27, T28, T29, T30 |
| `erp_ai/agent/changes/block.py` (mới) | T1, T18 |
| `erp_ai/agent/changes/restart_check.py` (mới) | T23 |
| `erp_ai/agent/changes/apply_job.py` | T1, T6, T7, T33..T40 |
| `erp_ai/agent/changes/file_writer.py` | T5, T6 |
| `erp_ai/agent/changes/process_runner.py` | T7, T8 |
| `erp_ai/agent/changes/transitions.py` | T1, T15, T16, T17 |
| `erp_ai/agent/changes/result_comment.py` | T31, T32 |
| `erp_ai/agent/change_text.py` | T19, T20, T21 |
| `erp_ai/agent/prompts.py` | T46 |
| `erp_ai/constants.py` | T1, T29 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/__init__.py` (mới) | T1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/erp_ai_change_operation.json` (mới) | T1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/erp_ai_change_operation.py` (mới) | T1 |
| `P/erp_ai_change_proposal.json` | T1 |
| `P/erp_ai_change_proposal.py` | T1, T22, T24 |
| `P/erp_ai_change_proposal.js` | T25 |
| `erp_ai/test_utils.py` | T2 |
| `erp_ai/tests/test_architecture.py` | T7, T47, T48, T49 |
| `erp_ai/agent/tools/test_change_guard.py` | T9..T14 |
| `erp_ai/agent/tools/test_propose_change.py` | T9, T26..T30 |
| `erp_ai/agent/tools/test_source.py` | T3, T4, T49 |
| `erp_ai/agent/tools/test_registry.py` | T29 |
| `erp_ai/agent/test_classification.py` | T46 |
| `erp_ai/agent/test_agent_runner.py` (có điều kiện) | T46 |
| `erp_ai/agent/changes/test_apply_job.py` | T6, T7, T33, T36 |
| `erp_ai/agent/changes/test_apply_block.py` (mới) | T1, T33..T43, T50 |
| `erp_ai/agent/changes/test_block_boundary.py` (mới) | T44, T45 |
| `erp_ai/agent/changes/test_block.py` (mới) | T18, T40 |
| `erp_ai/agent/changes/test_restart_check.py` (mới) | T23 |
| `erp_ai/agent/changes/test_file_writer.py` | T5, T6 |
| `erp_ai/agent/changes/test_process_runner.py` | T0, T7, T8 |
| `erp_ai/agent/changes/test_transitions.py` | T15, T16, T17 |
| `erp_ai/agent/changes/test_result_comment.py` | T31, T32 |
| `P/test_erp_ai_change_proposal.py` | T22, T24, T25 |
| `/etc/sudoers.d/erp-ai-restart` | ngoài repo; người làm sau G4 (§5.1), không có task build |

38/38 hàng của §7 có task. **Hai file plan thêm ngoài bảng §7** (thiếu sót của design, không phải thay đổi thiết kế; báo team-leader):
- `erp_ai/agent/test_change_text.py`: file test có sẵn của `change_text.py` (35 chỗ gọi `proposal_notes`, `apply_message`, `undo_message`; ghim câu "cần người chạy bench restart" ở dòng 129). Spec "Chạm" ghi "`change_text.py` … và test của chúng". Task T19..T21.
- `erp_ai/test_change_decision.py`: dòng 338 patch `git_commit_only` theo tên. Chỉ sửa khi stub của nó hỏng vì chữ ký mới (T7); không hỏng thì không chạm.

## AC → task
| Tiêu chí | Task |
|---|---|
| AC-36 | T1, T26, T27, T28, T36 |
| AC-37 | T33, T34, T35, T36 |
| AC-38 | T0, T7, T36 |
| AC-39 | T5, T12, T26, T35, T39; sau G4: bước người |
| AC-40 | T27, T34, T35, T39 |
| AC-41 | T27, T35, T39 |
| AC-42 | T16, T39, T40 |
| AC-43 | T13, T29, T41, T50 |
| AC-44 | T3, T4, T9, T26, T27 |
| AC-45 | T14, T21, T38, T40; sau G4: bước người |
| AC-46 | T13, T23, T24, T31, T33, T38 |
| AC-47 | T11, T14, T28, T33 |
| AC-48 | T20, T25, T30 |
| AC-49 | T32, T37, T38 |
| AC-50 | T9, T27, T44 |
| AC-51 | T43, T44 |
| AC-52 | T7, T43, T45 |
| AC-53 | T45 (đếm 40) |
| AC-54 | T22, T42 |
| AC-55 | T24, T42 |
| AC-56 | T29, T46 |
| AC-57 | T47 (luật không `sudo`); sau G4: bước người §5.1 |
| NFR-12 | T28 |
| NFR-13 | T35, T39 |
| NFR-14 | T2 (mixin thêm `erp_ai`), dùng ở T33..T45 |
| NFR-15 | sau G4: bước người |

22/22 AC và 4/4 NFR có task.

## Checkpoints
Tại mỗi điểm: `cmd.test` xanh trên `team/CHG-002` (không test đỏ nào ngoài dòng `baseline:` của `tasks.md`), `cmd.lint` sạch, và luồng chính của điểm đó chạy.

| Sau task | Luồng chính phải chạy |
|---|---|
| T1 | tool đề xuất khối 1 mục sửa → duyệt → job áp dụng → 1 commit, trên gốc tạm |
| T8, T14, T17 | đề xuất dạng cũ vẫn tạo, áp dụng, hoàn tác như trước (`test_apply_job.py`, `test_change_decision.py` xanh) |
| T25, T30 | tool tạo khối 5 mục kèm lệnh, comment đủ dòng; form mở được |
| T38 | khối có `.py`: ghi, 1 commit, lệnh theo thứ tự, stub restart được gọi đúng 1 lần |
| T40 | hoàn tác khối 5 mục trả đúng từng byte; đề xuất dạng cũ hoàn tác được |
| T45 | ma trận AC-53 đếm đủ 40 |
| T50 | tạo, áp dụng, hoàn tác file 1 MiB + 1 byte |
| T51 | toàn bộ, trong một lần giữ khóa site: `cmd.migrate` lên/xuống/lên, `cmd.test` cả app, `cmd.lint`; `git diff --stat develop...team/CHG-002` không có file nào trong danh sách "Không đụng"; `diff.patch` |

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| `commit --only` không ghi nhận file đã xóa trên git 2.43 | T0 đỏ | Dừng, báo team-leader, cần ADR mới (ADR-040 Ràng buộc Git) |
| C-1 chưa có phán quyết khi build tới T50 | ADR-040 QĐ 5 vẫn ghi 1 MiB | T50 không bắt đầu; mọi task khác dùng `source.TEXT_MAX_BYTES` nên không bị chặn; báo team-leader |
| `arch-review-design.md` (architect, 2026-11-15) trả `REVIEW: fix`, 0 blocker, 3 major; `design.md` chưa sửa lúc lập plan | F-1 (tổng 8 MiB phải đếm cả `diff`; hằng trần mỗi file ở `constants.py`) chạm T1, T3, T13, T29, T49, T50; F-2 (`confirm_restart` chỉ nhận `ERP AI Instructor` qua `_decider`) chạm T24, T42; F-3 (`remove_file`, `remove_empty_dirs` kiểm `.git*` và symlink) chạm T5, T6 | Plan không tự sửa hợp đồng của design. Sau khi designer sửa `design.md`, tech-lead sửa đúng các dòng Returns/Expect của những task trên (`/team:plan --insert`) trước khi giao chúng; T0, T2 và mọi task khác không chờ |
| Chiều "xuống" của migrate xóa DocType mồ côi (journal FEAT-004, T34) trái chữ design §6 | T51 thấy `tabERP AI Change Operation` biến mất sau chiều xuống | Xem lưu ý ở T51; chỉ DocType con mới, 0 dòng; khác thế thì dừng và báo |
| T1 chạm 12 file | review T1 dài | Ngoại lệ cỡ của walking skeleton (như FEAT-006 T1); mọi lõi giả, chỉ 1 loại mục |
| Đổi chữ ký `git_commit_only` làm đỏ `test_apply_job.py` (71 chỗ dùng) | T7 đỏ ở test cũ | T7 chỉ đổi cách gọi và stub, không đổi assertion hành vi |
| Phiên FEAT-007 dùng chung site | `run-tests` chờ khóa hoặc test đỏ vì dữ liệu của phiên kia | Luôn chạy qua `.team/miyano-site.lock`; đỏ thì chạy lại một lần sau khi có khóa, vẫn đỏ thì tìm nguyên nhân, không tick |
| Chuỗi `apply_job.py` dài 10 task tuần tự | build chậm | Chuỗi tool (T26..T30) và chuỗi test khác chạy song song với nó |
| `bench build` cộng `migrate` vượt 540 s trong một khối | lệnh `quá thời gian` khi đo thật | Không thuộc build; dev ghi số đo `bench build --app` vào báo cáo T37 (design "Việc cần nguồn") |
| DocType mới cần `cmd.migrate`, mà site `miyano` chạy mã ở thư mục app chính chứ không phải worktree của dev | T1 đỏ vì thiếu bảng `tabERP AI Change Operation`, hoặc test của phiên FEAT-007 đỏ sau migrate | Trước khi giao T1, tech-lead chốt cách chạy test cho nhánh task theo cách các build trước đã làm (journal FEAT-006, FEAT-007), giữ khóa trong suốt lúc migrate và chạy; bảng và cột thừa vô hại với mã cũ (§6 "Xuống") |
| Bảng con do tài khoản agent chèn bị M5 hoặc quyền chặn | T1 đỏ ở bước `insert` | Đây là lý do T1 đi qua tool thật; sửa trong `_insert` (cùng `allow_agent_write`), không nới `site_api` |

## Review focus
Năm đầu vào hoặc lỗi mà spec ngụ ý, mỗi cái có test ở task chủ:
1. Lỗi ghi ở mục đổi tên có đích trong thư mục mới, sau khi đã `git add`: trả lại phải bỏ stage và gỡ thư mục. Test `AB::TestBlockAllOrNothing::test_rename_into_new_dir_fails_after_add_restores_index_and_dirs` (T35).
2. Một đường dẫn của khối nằm trong thư mục mà mục khác coi là file (`a/b` và `a/b/c.py`). Test `CG::TestCheckBlock::test_path_inside_another_path_refused` (T12).
3. Hoàn tác khi thư mục do khối tạo đã có `__pycache__`: thư mục được để nguyên, hoàn tác vẫn thành công. Test `AB::TestNewDirs::test_undo_removes_created_empty_dirs_keeps_preexisting_and_nonempty` (T39).
4. Đề xuất dạng cũ đã duyệt trước khi triển khai: dấu không đổi và job áp dụng qua bộ chuyển đổi. Test `BL::TestLegacyDigest::test_legacy_digest_is_byte_identical` (T18) và `AB::TestLegacyThroughAdapter::test_legacy_approved_proposal_applies` (T33).
5. Job chết giữa commit và `record_commit`: sha được giữ, không trả lại file. Test `AB::TestBlockCommit::test_crash_after_commit_keeps_sha_and_files` (T36).

## Walking skeleton (cỡ L)
T1 đi qua mọi lớp với lõi giả, chỉ cho **một** mục `edit`, không có lệnh:
- dữ liệu: DocType con và 6 trường mới trên bản ghi cha (đủ theo §2.1, §2.2), hằng khối "CHG-002";
- tool: `propose_file_change` nhận `changes` có 1 mục `edit` → `_propose_block` giả → một `insert` cha cùng dòng con trong `allow_agent_write()` → 1 comment;
- dấu: `content_digest` dạng khối; bản xem trước commit của khối 1 mục;
- duyệt: phương thức `approve` có sẵn;
- job: `run_change(name, "apply")` đọc qua `block.operations_of` → ghi → 1 commit bằng `git_commit_only` chữ ký cũ → `Đã áp dụng`.

Bằng chứng: `cmd.test_one` với `erp_ai/agent/changes/test_apply_block.py` → `TestWalkingSkeleton::test_one_edit_block_proposed_approved_applied_one_commit`. Các lớp làm thật ở T9..T40. T0 đứng trước T1 vì nó chỉ thêm một test và quyết định có cần ADR mới hay không.

## Thứ tự merge với FEAT-007
Theo design §1.6 và quyết định ngày 2026-11-15: CHG-002 vào `develop` trước; FEAT-007 gộp `develop` một lần ở task T56 của nó, giải xung đột theo bảng §1.6. Push bị từ chối 403 nên chuỗi dừng ở merge cục bộ vào `develop`; không có PR và CI.
