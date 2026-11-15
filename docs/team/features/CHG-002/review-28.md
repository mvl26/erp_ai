Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 28 — CHG-002 T28

- Diff: `git diff a034a2d..4dddc6f` trên `team/CHG-002-task-28` (vòng 1: `a034a2d..334f852`, phần T28 là `a034a2d..4e1093c`; sửa vòng 1: `git diff 024ba58..4dddc6f`, `024ba58` = merge `team/CHG-002` @ `c44bf86` vào nhánh task)
- Gói: T28 + T29 cùng nhánh, một reviewer chấm cả gói; verdict của T29 ở `review-29.md`
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `238544c`, tick

Nhánh có hai commit `wip` (`8dd78a0`, `4bc45e9`): diff dở của hai lần gọi dev bị cắt (máy khởi động lại 17:38; một dev hết 60 lượt), tech-lead commit nguyên vẹn để dev sau làm tiếp. Reviewer chấm trạng thái cuối của task.

## Vòng 1 — request-changes (`git diff a034a2d..334f852`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-TEST-5 | thân commit `4e1093c` (và `8dd78a0`, `4bc45e9`) | dev khai `L-1: 2, L-2: 0`; diff có 3 đổi hình dạng và 3 lần bỏ L-2c: thiếu dòng `test-shape:` cho `test_bench_command_tool_refuses_enum_outside_and_app_misuse`; thiếu ba dòng `test-drop:` (hàng `{"command": "restart"}`; khẳng định restart của `test_bench_command_proposal_and_its_refusals`; cả test `test_bench_command_handler_refuses_restart_until_blocks`) | commit T28 mới nhất mang đủ danh sách, không viết lại lịch sử |
| major | STD-TEST-3 | `erp_ai/agent/changes/test_apply_job.py:2969` (`TestNoKeyLeak.run_flow`) | test gọi `propose_bench_command` thật rồi áp dụng; sau T28 đề xuất đó là khối chỉ có lệnh, `apply_job._run` trả `OP_UNKNOWN`, test đỏ; GREEN của dev không chạy module này | thêm `test_apply_job.py` vào touchpoint (luật `tasks.md` dòng 19), L-2a với dòng `test-input:`: chặng áp dụng lệnh chạy trên đề xuất lệnh dạng cũ |

minor | — | — | 1 điểm nhỏ: mô tả `propose_new_file` không nhắc `commands` và luật "khối có `.py` kết thúc bằng migrate rồi restart" (đã sửa cùng T29-1) | tùy dev

Tầng 1 ở vòng 1: phần Returns đạt (lệnh dựng bằng `build_bench_args`, lưu `command_list` đúng thứ tự; `propose_new_file` nhận `commands`; `propose_bench_command` qua `_propose_block([], [built], …)` cho khối chỉ có lệnh, `Lệnh bench`, `reversible = 0`, không khóa `branch`; gỡ `_SINGLE_BENCH_COMMANDS`, enum là `BENCH_COMMANDS`; khóa kết quả, 1 `.insert(`, 1 `allow_agent_write()`, không khóa nào của `STATE_FIELDS`); đủ 6 test Expect và `test_result_keys_stable`.

Tech-lead kiểm major trước khi giao sửa (18:36–19:42, sau `migrate`): `test_apply_job` trên `334f852`: `FAIL: test_fake_key_never_in_proposal_result_log_comment` / `Ran 117 tests in 131.162s` / `FAILED (failures=1)`.

## Vòng 2 — approve (`git diff 024ba58..4dddc6f`, 3 file, +26/−4)

1. ADDRESSED | STD-TEST-5 | thân `4dddc6f` (commit T28 mới nhất) mang đủ: 3 dòng `test-shape:`, 3 dòng `test-drop:`, 1 dòng `test-input:`; `L-1: 3, L-2: 4`. Test phủ `test_bench_command_restart_plain_ok` (`test_propose_change.py:1524`); hàng `{"command": "update"}` (`:541`) còn giữ lý do "tham số không hợp lệ: command".
2. ADDRESSED | STD-TEST-3 | `test_apply_job.py:2983-2992`: `run_flow` áp dụng một đề xuất lệnh dạng cũ dựng từ `app` và `command_list[0]` của chính đề xuất tool, cùng phiếu; mọi assertion giữ từng byte; danh sách kho được kiểm thêm `block_command` (`:3003-3005`).

Lỗi mới trong các dòng đổi: không.

minor | — | — | 2 điểm nhỏ: (a) dòng `test-input:` của `4dddc6f` đặt kết quả đỏ mới vào ô "lý do cũ"; (c) `test_apply_job.py:2991` `json.loads(command_list)[0]` bỏ qua các lệnh sau, không có assertion "đúng một lệnh" | tùy dev

Bằng chứng của dev. Lần gọi đầu: RED bằng đột biến 1 (đảo thứ tự `command_list`) `FAIL: test_py_block_with_migrate_restart_stored_in_order` ×3; đột biến 2 (`propose_bench_command` từ chối `["restart"]`) `FAIL: test_bench_command_restart_plain_ok`, `FAIL: test_no_effect_before_approval_tree_head_process_restart_stubs_unchanged`; GREEN `test_propose_change` `Ran 67 tests` / `OK`, `test_registry` `Ran 41 tests` / `OK`, `test_architecture` `Ran 195 tests` / `OK`. Sửa vòng 1: RED `FAIL: test_fake_key_never_in_proposal_result_log_comment` / `Lists differ: ['Đã hoàn tác', 'Lỗi'] != ['Đã hoàn tác', 'Đã áp dụng']` / `Ran 117 tests` / `FAILED (failures=1)`; GREEN (một lần giữ khóa, `MIGRATE 0`) `test_propose_change` `Ran 71` / `OK`, `test_registry` `Ran 41` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_transitions` `Ran 76` / `OK`, `test_architecture` `Ran 195` / `OK`, `test_agent_runner` `Ran 109`, chỉ còn 3 test baseline.

## Review checklist (10)
1 đạt · 2 đạt (`test_apply_job.py` chỉ đổi trong `TestNoKeyLeak`, theo luật dòng 19) · 3 đạt · 4 đạt (vòng 1 trượt STD-TEST-5, đã sửa) · 5 không áp dụng · 6 đạt · 7 đạt · 8 đạt · 9 đạt · 10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Cả app, đợt merge 18, `team/CHG-002` @ `238544c` (20:13–20:25, `cmd.migrate` thoát 0): `Ran 1885 tests in 680.363s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Đếm L-1 / L-2: T28 `L-1: 3, L-2: 4` (ghi ở đây và ở journal; từ lượt 5 không thêm dòng progress vào `tasks.md`).
- Cửa sổ của kế hoạch: từ T28 tới T37, đề xuất lệnh bench do tool tạo là khối và job trả `OP_UNKNOWN` lúc áp dụng. Tech-lead nhận cửa sổ này: `team/CHG-002` không vào `develop` trước T51; T37 đã giao ngay sau merge.
- Dev báo: site dùng chung bị phiên FEAT-007 migrate lại giữa các lần giữ khóa (48 lỗi `'dict' object has no attribute 'idx'` khi không migrate trước). Từ vòng 47 mọi lệnh giao ghi `migrate` ở đầu mỗi lần giữ khóa. Lần gọi đầu dev đã dùng `bench reload-doctype` / `frappe.reload_doc(force=True)` trên site dùng chung để tự gỡ; ghi vào báo cáo lượt 5.

## Nhãn đọc lại (addendum-9 A9-2, A9-4; thân commit đã merge không viết lại)

Tech-lead của lượt 5 đọc `design-addendum-9.md` lúc 21:28, sau khi T28 và T29 đã merge, nên lệnh giao của hai task không nhắc luật L-3.
- T28: ba dòng `test-drop:` và dòng `test-shape:` của enum giữ L-2c / L-1 (A9-4: `restart` thật sự được mở). Dòng `test-input:` của `4dddc6f` cho `test_apply_job.py::TestNoKeyLeak::test_fake_key_never_in_proposal_result_log_comment` ghi theo dạng L-2a; đây là ca "phần dựng từng đi tới bước test kiểm, nay bị chặn sớm hơn bởi một bước mới của CHG-002" (job trả `OP_UNKNOWN` cho khối chỉ có lệnh), đọc là `(addendum-9 L-3a; phần dựng dạng cũ theo addendum-8 A8-5)`. Đếm đã sửa của T28: `L-1: 3, L-2: 3, L-3: 1 (L-3a: 1, L-3b: 0)`.
- T29: `L-1: 3, L-2: 3, L-3: 0` (bỏ ba giới hạn là L-2; không có ca L-3).
- Reviewer chưa chấm cách đọc lại này; qa đối chiếu ở verify.

## deferred

1. Khi job đã chạy được lệnh của khối (T37) và hoàn tác khối (T39, T40): `TestNoKeyLeak.run_flow` quay về áp dụng chính đề xuất của tool (addendum-8 A8-5 "Sai thì hoàn tác"); ghi thành việc cho T40 hoặc T43.
2. `registry.py` kiểm `maxItems` mà không kiểm `minItems`: `changes: []` kèm `commands` qua `propose_file_change` tạo khối chỉ có lệnh trong khi schema ghi `changes` 1..50. Reviewer phán không phải lỗi của T28 / T29 (§3.1 giữ `registry.py`; `BLOCK_EMPTY` và §2.2 cho phép khối không có mục file); có nên chặn ở server hay không là việc của designer. Ca này chưa có test.
3. minor (a), (c) ở trên.
