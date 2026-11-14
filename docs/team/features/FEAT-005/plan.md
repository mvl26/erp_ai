Feature: FEAT-005
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-005 (Amendment 2, phạm vi thu gọn)

Plan này thay toàn bộ plan 2026-11-12 (52 task, cỡ L). Bản cũ: `git show 1918db2:docs/team/features/FEAT-005/plan.md`.

- Nhánh feature: `team/FEAT-005` từ **đầu `team/FEAT-004` sau khi build xong** (F4-T34 đã tick). Nhánh chưa tạo: plan lập khi FEAT-004 đang build, không `git switch`, không commit, không ghi `.team/current.json`. Khi tạo nhánh, tech-lead ghi mã commit vào dòng BASE của `tasks.md` và chạy `cmd.test` (phải xanh) trước T1. `config.base_branch` = `main` chỉ dùng lúc PR.
- Số task: 16 (T1–T15 giao dev, T16 của tech-lead). Song song: `limits.max_parallel_dev` = 2; team-leader giao `devs=5` cũng chỉ dùng tới 2 vì ba file nóng buộc chạy chuỗi (bảng "Lượt chạy").
- Cỡ M, không cần walking skeleton. Cổng áp dụng: G5 (G3 tắt). Lệnh: `cmd.test_one`, `cmd.test`, `cmd.migrate`, `cmd.lint` của profile.
- Căn cứ: `spec.md` Amendment 2 (AC-13, AC-14, AC-19; NFR-3, NFR-8), `design-amd2.md` (thay `design.md`), ADR-024. Ký hiệu `F4-T<n>` = task của FEAT-004.

## FEAT-004 phải xong trước (đã đối chiếu ID với `FEAT-004/tasks.md` @ `7c2a3af`, 2026-11-14)
Designer gọi đúng tên: **F4-T62** và **F4-T64** là hai task AC-35. Cả hai còn chưa tick lúc lập plan.

| Task FEAT-004 | Nội dung | File chung với FEAT-005 | Task FEAT-005 chờ |
|---|---|---|---|
| F4-T62 (sau chuỗi F4-T59 → T60 → T61) | AC-35: tool ghi trả `value_before`/`value_after` | `site_api.py`, `test_site_api.py` | T1 |
| F4-T63 | M4: một hàm cấp, runner gọi một hàm lấy schema | `runner.py`, `test_agent_runner.py` | T3 |
| F4-T64 | AC-35: runner ghi trước/sau và người ra lệnh vào mục hành động | `runner.py`, `test_agent_runner.py` | T3 |
| F4-T65 | M5: bộ chặn ghi của tài khoản agent | `erp_ai_setting.py` | T7 |
| F4-T68 (sau F4-T32 → T44) | Luật kiến trúc ADR-023 | `test_architecture.py` | T14 |

`tasks.py`, `test_tasks.py`, `erp_ai_setting.json`, `test_erp_ai_setting.py`: không task FEAT-004 nào còn mở chạm tới.

## Ràng buộc chung (chép từ design-amd2/ADR-024; mọi task kế thừa)
- Tên chính xác: `SNAPSHOT_TABLES`, `_snapshot(doc, fields)` (`site_api`); khóa kết quả `_snapshot: {"before", "after"}`; `GENERIC_WRITE_TOOLS`, `_record_snapshot(name, outcome, n, before, after)`, `REASON_TURN_SAVEPOINT = "erp_ai_reason_turn"`, `_undo_turn()` (`runner`); trường `privilege_alert_checked_until`; `check_privilege_escalation(now: datetime | None = None)`, `_privilege_changes_by_agent(lower, upper)`, `_load_snapshots(raw)`, `_advance_privilege_watermark(upper)`, `PRIVILEGE_ALERT_SETTLE_S = 300`, `PRIVILEGE_ALERT_LOCK = "erp_ai_privilege_alert"`, `PRIVILEGE_ALERT_LOCK_TIMEOUT_S = 60` (`tasks`).
- Khóa ảnh chụp trong `value_before`/`value_after` của dòng `reason`: `"<tool>#<n>"`, `n` đếm từ 1 = vị trí mục hành động của lời gọi trong `actions` của cùng dòng. Không thêm trường vào ERP AI Log.
- Chữ mục cảnh báo là hợp đồng, test so đúng chữ (design-amd2 §3.3): `thêm role <role> cho <user> (người ra lệnh <instructor>, <YYYY-MM-DD HH:MM>)`; `gỡ role <role> của <user> (…)`; `<tạo|sửa|xóa|submit/hủy> <DocType> <tên> (người ra lệnh …, …)`; đuôi `, không có trước/sau`; `ERP AI Log <tên dòng>, không có trước/sau`; tiền tố `[QUẢN TRỊ] `; `instructor` rỗng → `không rõ`. Tiêu đề giữ "Agent đã sửa bản ghi phân quyền".
- Chỉ `_advance_privilege_watermark` ghi mốc, chỉ bằng `frappe.db.set_single_value`; `tasks.py` không `save()`/`insert()` ERP AI Setting. `tasks.py` không viết tay tên tool `api_*`, không đọc `Version`, không lọc `modified_by`/`owner` cho điều kiện phân quyền, không `datetime.now`/`utcnow`/`NOW()`.
- `run_log.write_entry` giữ `insert` và `commit` trong cùng lời gọi. Không sửa: `hooks.py`, `alerts.py`, `run_log.py`, `constants.py`, ADR.
- Nhật ký và cảnh báo: 0 byte mật khẩu, khóa, token; log của job không có tên user hay role (STD-SEC-6).
- Test: thời gian giả qua `now=` và `frappe.db.set_value(..., update_modified=False)` trên `creation`; `setUp` đặt mốc T0 để loại dòng thật; lỗi giả bằng `unittest.mock.patch`; dòng gieo dựng bằng `site_api` dưới tài khoản agent cộng `write_entry`. Ba điều kiện cảnh báo còn lại: test không sửa.
- Đường dẫn mới: 0. `protected_paths`: 0.

## File map (touchpoint → trách nhiệm → task)
| Đường dẫn | Loại | Trách nhiệm | Task |
|---|---|---|---|
| `erp_ai/agent/tools/site_api.py` | sửa | `SNAPSHOT_TABLES`, `_snapshot`; bốn tool ghi trả `_snapshot` | T1, T2 |
| `erp_ai/agent/tools/test_site_api.py` | sửa | 4 test ảnh chụp | T1, T2 |
| `erp_ai/agent/runner.py` | sửa | `GENERIC_WRITE_TOOLS`, `_record_snapshot`; hoàn tác lượt | T3, T5, T6 |
| `erp_ai/agent/test_agent_runner.py` | sửa | AC-13 qua runner, hoàn tác lượt, đầu-cuối | T3, T4, T5, T6, T15 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | sửa | trường mốc | T7 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | sửa | khôi phục mốc khi người lưu | T7 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | sửa | test khôi phục mốc | T7 |
| `erp_ai/tasks.py` | sửa | cảnh báo đọc nhật ký, cửa sổ, mốc, khóa | T8–T13 |
| `erp_ai/tests/test_tasks.py` | sửa | AC-14, AC-19, fail-closed; viết lại 5 test | T8–T13 |
| `erp_ai/tests/test_architecture.py` | sửa | Ràng buộc ADR-024 | T14 |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | **ngoài bảng §7 của design-amd2** (plan thêm): `field_count`, `read_only_fields`, `phrases` của ERP AI Setting | T7 |

10/10 touchpoint của design-amd2 §7 có task; 1 file plan thêm (mục Rủi ro).

## AC → task
| Tiêu chí | Task |
|---|---|
| AC-13 (a) dòng con | T1, T2, T3, T4 |
| AC-13 (b) hiệu trước/sau | T4 |
| AC-13 (c) không cắt | T3, T4 |
| AC-13 (d) riêng từng lời gọi | T3 |
| AC-14 | T8 (bản ghi phân quyền, 5 mục, do người → 0, ba điều kiện kia), T9 (thêm/gỡ role, lưu lại → 0), T10 (dấu quản trị), T12 (không có trước/sau, khóa giả), T15 |
| AC-19 | T11 (ba ca, khoảng lắng, mốc không lùi), T13 (lỗi giữa job, khóa bận), T15 |
| NFR-3 | T2, T3, T5, T6 |
| NFR-8 | T11, T13, T15 |
| ADR-024 Ràng buộc | T5, T6, T12, T14 |
| DoD phần build | T16 |

36/36 dòng test của design-amd2 §8 có task chủ: T1 2, T2 2, T3 3, T4 3, T5 2, T6 1, T7 1, T8 5, T9 3, T10 1, T11 5, T12 3, T13 2, T14 2, T15 1.

## Một file, một chủ
| File | Task chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| `site_api.py`, `test_site_api.py` | T1 | T2 | F4-T62 → T1 → T2 |
| `runner.py` | T3 | T5, T6 | F4-T64 → T3 → T5 → T6 |
| `test_agent_runner.py` | T3 | T4, T5, T6, T15 | T3 → T4 → T5 → T6 → T15 |
| `erp_ai_setting.json`, `erp_ai_setting.py`, `test_erp_ai_setting.py`, `test_doctype_descriptions.py` | T7 | — | F4-T65 → T7 |
| `tasks.py`, `test_tasks.py` | T8 | T9–T13 | T8 → T9 → T10 → T11 → T12 → T13 |
| `test_architecture.py` | T14 | — | F4-T68 → T14 |

## Thứ tự
1. Ảnh chụp ở tool (T1, T2), song song với trường mốc (T7, có `cmd.migrate`: chạy một mình trên site, không dev nào khác chạy `cmd.migrate` cùng lúc).
2. Runner ghi ảnh chụp (T3, T4): hợp đồng `"<tool>#<n>"` mà cảnh báo đọc; làm sớm vì là chỗ dễ lệch với mã thật của F4-T64.
3. Hoàn tác lượt (T5, T6) chạy song song với chuỗi cảnh báo (T8 → T13): khác file.
4. Luật kiến trúc (T14) và đầu-cuối (T15) sau khi `tasks.py` xong.
5. T16: kiểm cuối của tech-lead.

## Lượt chạy (tới 5 dev; thực tế tối đa 2 vì chuỗi file)
| Lượt | Dev chạy cùng lúc | Điều kiện mở |
|---|---|---|
| 1 | T1, T7 | BASE xanh |
| 2 | T2 | T1 merge |
| 3 | T3 | T2 merge |
| 4 | T4, T8 | T3 merge (T8 cần thêm T7) |
| 5 | T5, T9 | T4, T8 merge |
| 6 | T6, T10 | T5, T9 merge |
| 7 | T11 | T10 merge |
| 8 | T12 | T11 merge |
| 9 | T13 | T12 merge |
| 10 | T14, T15 | T13 merge (T15 cần thêm T6) |
| 11 | T16 (tech-lead) | T1..T15 tick |

Không chờ cả lượt: task nào đủ `depends:` thì gọi ngay; reviewer của task đã xong đi cùng thông điệp với dev của task kế. Mỗi lần merge một task. `test.shared_state` không khai trong profile; site `miyano` dùng chung nên khi hai dev cùng chạy, mỗi dev chỉ chạy `cmd.test_one`, `cmd.test` chạy sau mỗi lần merge.

## Checkpoint (`cmd.test` xanh trên `team/FEAT-005`)
- Sau T2: bốn tool ghi trả `_snapshot`; test FEAT-004 của `site_api` xanh nguyên.
- Sau T4: AC-13 đạt qua runner.
- Sau T6: NFR-3 đường ngoại lệ đạt.
- Sau T10: AC-14 phần nội dung đạt.
- Sau T13: AC-19, NFR-8 đạt.
- Sau T15: luồng chính chạy đầu-cuối; rồi T16.

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| **design-amd2 §7 thiếu touchpoint `erp_ai/tests/test_doctype_descriptions.py`**: thêm trường vào ERP AI Setting làm `field_count` (27) và `read_only_fields` của test đó đỏ | `cmd.test` đỏ sau T7 nếu không sửa | Plan đã đưa file vào `files:` của T7. Cần designer hoặc team-leader xác nhận một dòng trong design-amd2 §7 trước build; không xác nhận thì T7 trả `DESIGN_CONFLICT` |
| F4-T62, F4-T64 chưa có mã; chữ ký thật có thể khác design-amd2 (vd. `_action`, chỗ `actions.append`, tên `value_before`) | dev T1 hoặc T3 trả `DESIGN_CONFLICT` | tech-lead so mã thật khi tạo nhánh, trước T1; lệch → `/team:plan --insert` hoặc designer sửa design-amd2 |
| F4-T64 ghi `value_before`/`value_after` vào `actions` (Small Text 64 KB): lượt nhiều lời gọi có thể tràn; sau T5 tràn → hoàn tác cả lượt (design-amd2 D-3) | Error Log `TITLE_RUN_FAILED` sau lượt nhiều tool | ghi cho chủ FEAT-004; ngoài phạm vi FEAT-005 |
| Savepoint lượt (T5) đổi hành vi test FEAT-004/FEAT-006 dựa vào ghi dở của lượt lỗi | test cũ của `test_agent_runner.py` đỏ sau T5 | không sửa assertion cũ (STD-TEST-5); trả `DESIGN_CONFLICT` kèm tên test |
| Test gieo bằng tool ghi gây DDL (Custom Field, DocType) làm commit ngầm, rò dữ liệu test | dòng `ERPAI-TEST-*` còn lại sau `cmd.test` | T8 dựng tay dòng nhật ký cho ca DocType `DocType`; không test nào ghi Custom Field/DocType thật |
| T4, T14, T15 chỉ thêm test, có thể xanh ngay | không có đầu ra đỏ | reviewer kiểm test bắt được lỗi (T14: chuỗi mẫu vi phạm trong test); đỏ trên mã thật → `DESIGN_CONFLICT` |
| DoD đòi trạng thái ADR-014, 015, 017 (bị thay), ADR-018 (một phần); lượt này mới sửa ADR-016 | `grep -n 'Trạng thái' docs/team/adr/ADR-01[4-8].md` ở T16 | team-leader/architect sửa bốn dòng trạng thái còn lại trước verify |
| Múi giờ site có DST (ADR-024 QĐ 3.6, UNVERIFIED) | — | qa kiểm ở verify (design-amd2 §6); T16 ghi nhắc |

## Review focus (đã gắn test vào task chủ)
1. Lời gọi đầu bị từ chối, lời gọi sau thành công: khóa là `#2`, không có `#1` (T3, `test_two_calls_same_tool_one_turn_two_snapshots`).
2. Biên cửa sổ: `creation == upper` được báo, `creation == lower` không báo lại (T11, `test_change_inside_settle_margin_waits_for_next_run`).
3. Cột `actions` hỏng: ra mục `ERP AI Log <tên dòng>, không có trước/sau`, job không chết (T12, `test_broken_snapshot_json_listed_without_before_after`).
4. DocType `DocType` có `permissions` trước ≠ sau → 1 mục, giống → 0 (T8, `test_alarm_on_permission_records_modified_by_agent`).
5. Mục `[QUẢN TRỊ]` mới hơn 5 mục thường vẫn nằm trong 5 mục hiện (T10, `test_admin_role_marked_and_listed_first`).

## Việc lượt plan này không làm (theo lệnh của team-leader)
- Không tạo nhánh `team/FEAT-005`, không ghi `.team/current.json`, không commit.
- Đã sửa dòng trạng thái: ADR-016 (một phần, ADR-024), ADR-005, ADR-011, ADR-012 (trỏ ADR-023).
