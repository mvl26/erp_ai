Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 20/53, READY build). -->

# Phụ lục thiết kế 6 — CHG-002 (hẹp: T11)

Phạm vi: chỉ `DESIGN_CONFLICT` của T11 (`tasks.md:165`): thêm `restart` vào `change_guard.BENCH_COMMANDS` làm tool `propose_bench_command` nhận luôn `restart`, vì enum của tool là `list(change_guard.BENCH_COMMANDS)` (`propose_change.py:376`). Phụ lục này nói thêm cách T14 và T28 đọc phán quyết. Nó không đổi AC và không đổi phạm vi "Giữ vành đai an toàn". Danh sách lệnh bench chỉ thêm đúng `restart`. Phụ lục này chỉ siết, không nới.

Tuân theo: ADR-040 QĐ 6 (`restart` chỉ có dạng `["restart"]`), ADR-022 QĐ 2 (`BENCH_COMMANDS` là bảng hằng chuỗi), design §3.1 (bảng tool, dòng `propose_bench_command`), §3.2 (`BENCH_COMMANDS`, `check_block` bước 4), addendum-4 L-2 (giữ nguyên, phụ lục này chỉ áp L-2).

Nguồn đã đọc (không gọi Explore, theo lệnh của team-leader):
- `tasks.md:160-187` (T11..T14), `:280-298` (T26..T28, cột depends);
- `design.md:204-320`; `design-addendum-4.md`;
- diff `50c5f80..e64a269` (`change_guard.py`, `test_change_guard.py`) và thân commit `e64a269`;
- `990d7b3:erp_ai/agent/tools/propose_change.py:276-292`, `:360-385`;
- `990d7b3:erp_ai/agent/tools/test_propose_change.py:43`, `:461-570`. Hai file này giống hệt nhau ở `990d7b3` và `50c5f80` (`git diff --stat` rỗng);
- `50c5f80:erp_ai/agent/changes/apply_job.py:240-262`;
- `50c5f80:erp_ai/tests/test_architecture.py` (grep `BENCH_COMMANDS`).

---

## P-1. Phán quyết: phương án (a), tool đơn lệnh giữ `restart` đóng cho tới T28

**Chọn (a).** T11 thêm `RESTART_COMMAND = "restart"` vào `change_guard.BENCH_COMMANDS` như mã của dev ở `e64a269`. Tool `propose_bench_command` vẫn từ chối `restart` cho tới T28, ở hai lớp:
1. **Schema:** enum `command` lấy từ một hằng riêng của `propose_change.py`. Hằng này là `BENCH_COMMANDS` trừ `RESTART_COMMAND`.
2. **Handler:** `propose_bench_command` từ chối lệnh ngoài hằng đó bằng `change_guard.CMD_NOT_LISTED`, trước `build_bench_args`. Lý do: test cũ đã ghim nguyên tắc "handler tự từ chối lệnh ngoài bảng, dù gì đi tới nó" (`test_propose_change.py:563-566`).

T28 gỡ cả hai lớp, vì lúc đó `propose_bench_command` đi qua `_propose_block` (T28 Returns).

Mã cho T11, ở `erp_ai/agent/tools/propose_change.py`, đặt gần các hằng của module:

```python
# CHG-002 addendum-6: `restart` reaches the model only as a block command (T28); the single-command
# apply path would run it inside the worker instead of through `launch_restart`.
_SINGLE_BENCH_COMMANDS = tuple(
	command for command in change_guard.BENCH_COMMANDS if command != change_guard.RESTART_COMMAND
)
```

- Trong schema của `propose_bench_command`: `"enum": list(_SINGLE_BENCH_COMMANDS)`.
- Trong `propose_bench_command`, ngay sau `_entry_refusal`: `if args["command"] not in _SINGLE_BENCH_COMMANDS: return _fail(change_guard.CMD_NOT_LISTED)`.

**Vì:**
1. **Vành đai trong các trạng thái giữa của nhánh.** Đường lệnh đơn cũ (`change_kind` lệnh bench) lúc áp dụng chỉ kiểm `check_bench_args` (`apply_job.py:250-252`) rồi chạy argv như mọi lệnh bench khác. `launch_restart` (T8, `setsid -f`, `timeout -s KILL`) chỉ được gọi ở bước restart của khối (`tasks.md:364-366`). Từ T11 trở đi, `check_bench_args(["restart"])` trả `None`. Với (b), từ lúc T11 merge tới lúc T28 merge, model sẽ tạo được một đề xuất lệnh đơn `["restart"]`. Khi được duyệt, đề xuất đó chạy `bench restart` đồng bộ ngay trong worker đang chạy job, tức là giết chính job đó: không ghi kết quả, không có comment, trạng thái treo ở "Đang áp dụng". Với (a), tool là nơi **duy nhất** tạo ra dòng đề xuất. Nó vẫn đóng, nên không có dòng `["restart"]` nào đi vào đường lệnh đơn. Trước T11 cũng không có dòng nào như vậy, vì `build_bench_args` từ chối.
2. **Luật vị trí restart (T14) chưa có ở T11.** Theo R-5, khối chỉ có `["restart"]` là hợp lệ, nên luật T14 không thiếu cho đúng ca đơn lệnh. Vấn đề là ca đơn lệnh ở T11 chưa đi qua `check_block`: nó đi qua đường cũ ở mục 1. Mở tool ở T11 là mở trước cả T14 lẫn đường khối. Chuỗi depends `T28 → T27 → T26 → T14, T2` (`tasks.md:280-292`) bảo đảm tool chỉ mở sau khi luật T14 và đường `_propose_block` đã có.
3. **L-2 ở T11 không giải được hai test cũ.** Với (b):
   - L-2c không dùng được, vì test chấp nhận cùng đầu vào (`test_bench_command_restart_plain_ok`) thuộc Expect của T28, không của T11.
   - L-2b sẽ biến dòng `:546` thành ca chấp nhận một đề xuất **lệnh đơn** `restart`. T28 lại phải đổi ca đó thành đề xuất khối. Như vậy test đổi hai lần và một hành vi trung gian được ghim mà design không muốn (STD-TEST-5).

   Với (a), hai test cũ ở `:490` và `:535-546` xanh lại mà không đổi một byte nào.
4. **Đúng chữ của design.** §3.1 ghi enum "đã có `restart`" là đích cuối của tool, và T28 là task được giao "enum `command` có `restart`". (a) chỉ xếp thứ tự để đích đó đến ở T28. §3.2 (`BENCH_COMMANDS` có `restart`) đúng ngay từ T11.

**Phương án khác:**
- **(b) mở ở T11, hai test cũ sửa theo L-2b/L-2c.** Bác vì cả ba lý do 1–3: mở lỗ restart đồng bộ trong worker giữa T11 và T28, ghim hành vi trung gian, và L-2c không đủ điều kiện ở T11.
- **(c) hoãn thêm `restart` vào `BENCH_COMMANDS` tới T28.** Bác. Làm vậy trái §3.2 và trái AC-47 Returns của T11. T14 (`Receives: RESTART_COMMAND, check_bench_args`) và các task job cần `check_bench_args(["restart"])` trả `None`. `test_architecture` đọc `BENCH_COMMANDS` như bảng lệnh của vành đai (`test_architecture.py:3683`, `:4855`).
- **(d) chỉ đóng ở schema, không chặn trong handler.** Bác. Làm vậy bỏ lớp thứ hai mà test cũ đã ghim cho lệnh ngoài bảng (`:563-566`), và một lời gọi handler trực tiếp sẽ tạo được đề xuất `restart`.
- **(e) cờ cấu hình bật hoặc tắt `restart`.** Bác: đây là điểm mở rộng không ai yêu cầu (STD-DESIGN-5).

**Sai thì hoàn tác:**
- Nếu `cmd.test_one` của `erp_ai/tests/test_architecture.py` hoặc `erp_ai/agent/tools/test_registry.py` đỏ vì hằng `_SINGLE_BENCH_COMMANDS` (ví dụ có quét đòi enum là bảng hằng), dev viết hằng thành tuple hằng chuỗi `("migrate", "clear-cache", "clear-website-cache", "list-apps", "build", "version")`, theo đúng thứ tự của `BENCH_COMMANDS` trừ `restart`. Test mới ở P-2 bước 1 thêm một assertion: `set(_SINGLE_BENCH_COMMANDS) == set(change_guard.BENCH_COMMANDS) - {change_guard.RESTART_COMMAND}`. Không đổi gì khác.
- Nếu đỏ vì lý do khác, dev trả `DESIGN_CONFLICT` nêu tên test.
- Nếu sau này cần mở `restart` trước T28: hoàn tác là làm sớm đúng các dòng T28 ở bảng "tasks.md đổi gì" (xóa hằng và dòng chặn, rồi chạy L-2c cho ba chỗ). Không đổi gì ở `change_guard.py`.

## P-2. Việc dev T11 phải sửa trên e64a269

Nhánh `team/CHG-002-task-11`. Tạo **một commit mới** trên `e64a269`: không viết lại lịch sử, không force-push. Phần `change_guard.py` và `test_change_guard.py` của `e64a269` được nhận nguyên, trừ một việc đổi tên ở bước 3.

1. **Test đỏ trước.** Thêm vào `erp_ai/agent/tools/test_propose_change.py` test mới `TestProposeChange::test_bench_command_handler_refuses_restart_until_blocks`, gồm các khẳng định:
   - `self.assertIn(change_guard.RESTART_COMMAND, change_guard.BENCH_COMMANDS)`;
   - enum `command` của spec `propose_bench_command` **không** chứa `change_guard.RESTART_COMMAND`;
   - `propose_change.propose_bench_command({"command": "restart", "reason": "x"}, self.context(allowed_apps=(APP,)))` bằng đúng `{"ok": False, "reason": change_guard.CMD_NOT_LISTED}`;
   - `self.proposals() == []` và `self.comments() == []`.

   Chạy `cmd.test_one` với `erp_ai/agent/tools/test_propose_change.py` trên `e64a269` cộng riêng test này, rồi dán dòng đỏ. Trên `e64a269`, handler tạo được đề xuất, và hai test cũ `test_bench_command_proposal_and_its_refusals` (`:490`) và `test_bench_command_tool_refuses_enum_outside_and_app_misuse` (`:535`, `:546`) đang đỏ. Dán cả hai dòng đỏ đó.
2. **Mã.** Ở `erp_ai/agent/tools/propose_change.py`, thêm hằng `_SINGLE_BENCH_COMMANDS` cùng chú thích hai dòng như P-1. Đổi enum của schema `propose_bench_command`. Thêm một dòng chặn trong `propose_bench_command`. Không sửa câu mô tả của tool và không sửa tool nào khác.
3. **Đổi tên test ghim danh sách cho phép.** Ở `erp_ai/agent/tools/test_change_guard.py`, đổi tên `TestBenchArgs::test_bench_allow_list_is_exactly_the_six_design_commands` thành `test_bench_allow_list_is_exactly_the_seven_design_commands`, vì tên phải nói đúng giá trị mới (STD-NAME-6). Phần thân giữ đúng như `e64a269`: tập 7 lệnh, `len == 7`. Không sửa gì khác trong file.
4. **Không sửa** `:490` hay `:535-546` của `test_propose_change.py`. Hai test đó phải xanh lại mà không đổi byte nào.
5. **Chạy `cmd.test_one`** với từng file sau và dán `Ran … / OK` của từng file:
   - `erp_ai/agent/tools/test_change_guard.py`;
   - `erp_ai/agent/tools/test_propose_change.py`;
   - `erp_ai/agent/tools/test_registry.py`;
   - `erp_ai/agent/changes/test_apply_job.py`;
   - `erp_ai/tests/test_architecture.py`.
6. **Thân commit** mang danh sách đầy đủ, thay cho kế hoạch "L-1: 2, L-2: 1" của dev. Mỗi test một dòng:
   - `test-shape: erp_ai/agent/tools/test_change_guard.py::TestBenchArgs::test_bench_allow_list_is_exactly_the_six_design_commands → test_bench_allow_list_is_exactly_the_seven_design_commands — 6 lệnh → 7 lệnh (thêm restart) — design §3.2, §8.3 (addendum-6 P-2)`
   - `test-drop: erp_ai/agent/tools/test_change_guard.py::TestBenchArgs::test_bench_args_refuse_every_a6_denied_command[restart] — phủ bởi TestBenchArgs::test_restart_plain_accepted (build → ["restart"], check → None) và TestBenchArgs::test_restart_with_any_arg_refused; đếm 23 → 22 — design §3.2 (addendum-4 L-2c)`
   - `test-new: erp_ai/agent/tools/test_propose_change.py::TestProposeChange::test_bench_command_handler_refuses_restart_until_blocks — tool đơn lệnh đóng restart tới T28 — addendum-6 P-1`
   - Không có dòng nào cho `:490` và `:535-546`, vì hai test đó không đổi.
   - Dòng progress: `L-1: 1, L-2: 1`.

   Lý do bỏ dòng `[restart]` theo L-2c: `CMD_NOT_LISTED` vẫn còn 22 dòng khác, và test bị bỏ dòng không phải test ghim AC: test ghim AC-47 cho danh sách cấm là `test_every_denied_command_refused`, thuộc Expect.
7. **Đối chiếu của reviewer.**
   - Mã của `e64a269` khớp T11 Returns: `RESTART_COMMAND`, `build_bench_args("restart", None, …) == ["restart"]`, `check_bench_args(["restart"], …) is None`, có đối số khác thì `CMD_NOT_LISTED` hoặc `CMD_TAKES_NO_APP`.
   - Hằng mới ở `propose_change.py` loại **đúng** `restart`, không loại lệnh nào khác.

---

## tasks.md đổi gì (tech-lead sửa; designer không sửa tasks.md)

| Task | Touchpoint | Returns / Expect đổi |
|---|---|---|
| T11 | Thêm vào `files:` và `test:`: `erp_ai/agent/tools/propose_change.py`, `erp_ai/agent/tools/test_propose_change.py` | **Returns thêm:** "`propose_change._SINGLE_BENCH_COMMANDS` = `BENCH_COMMANDS` trừ `RESTART_COMMAND`; enum `command` của `propose_bench_command` lấy từ hằng này; handler trả `CMD_NOT_LISTED` cho lệnh ngoài hằng, trước `build_bench_args` (addendum-6 P-1); tool đơn lệnh đóng `restart` cho tới T28". **Expect:** đổi tên `test_bench_allow_list_is_exactly_the_six_design_commands` thành `…_seven_design_commands` (7 lệnh); thêm `TestProposeChange::test_bench_command_handler_refuses_restart_until_blocks` xanh; `test_one` của `test_propose_change.py`, `test_registry.py`, `test_apply_job.py`, `erp_ai/tests/test_architecture.py` xanh, trong đó `test_bench_command_proposal_and_its_refusals` và `test_bench_command_tool_refuses_enum_outside_and_app_misuse` không đổi. Dòng progress ghi `L-1: 1, L-2: 1`. |
| T14 | Không đổi | **Returns thêm một câu ghi chú:** "luật restart chỉ áp cho `check_block`; tool đơn lệnh còn đóng `restart` (addendum-6), nên T14 không có ca ở mức tool". Expect không đổi. |
| T28 | Không đổi (`propose_change.py` và `test_propose_change.py` đã có trong touchpoint) | **Returns thêm:** "xóa `_SINGLE_BENCH_COMMANDS` và dòng chặn trong handler; enum `command` = `list(change_guard.BENCH_COMMANDS)` (addendum-6)". **Expect thêm:** `test_bench_command_restart_plain_ok` khẳng định cả `RESTART_COMMAND` có trong enum và lời gọi handler trực tiếp với `restart` trả `ok`. Các test cũ sửa theo L-1 và L-2: (1) `test-shape` cho `test_bench_command_tool_refuses_enum_outside_and_app_misuse`: set và len của enum so với `set(BENCH_COMMANDS_TABLE) \| {"restart"}` và `len + 1`; giữ `BENCH_COMMANDS_TABLE` 6 lệnh của đường cũ; (2) `test-drop` (L-2c) cho dòng `{"command": "restart"}` (`:546`), phủ bởi `test_bench_command_restart_plain_ok`; lý do `tham số không hợp lệ: command` còn dòng `update`; (3) `test-drop` (L-2c) cho khẳng định `restart` ở `:489-492` của `test_bench_command_proposal_and_its_refusals`, cùng phủ bởi test đó; `len(self.proposals()) == 2` giữ nguyên; (4) `test-drop` (L-2c) cả test `test_bench_command_handler_refuses_restart_until_blocks`, phủ bởi `test_bench_command_restart_plain_ok`; `CMD_NOT_LISTED` của handler còn dòng `update` (`:563-566`). |

Không đổi AC, cột `depends` hay thứ tự task. T11 vẫn chặn T12..T14, T26..T30, T33..T45, T48..T50 cho tới khi merge. Không task nào chưa xong cùng sửa `propose_change.py` song song với T11: T26..T30 đều nằm sau T11 trong chuỗi depends.

## design.md đọc theo phụ lục này (không sửa design.md)
- §3.1, dòng `propose_bench_command`: "Enum thêm `restart`" đọc là "Enum thêm `restart` ở T28, khi tool đi qua `_propose_block`; từ T11 tới T28, enum là `BENCH_COMMANDS` trừ `restart` (addendum-6)".
- §8.3 "Test cũ phải sửa" thêm hai mục:
  - T11: `CG::TestBenchArgs::test_bench_allow_list_is_exactly_the_six_design_commands` đổi tên và đổi sang 7 lệnh; bỏ dòng `[restart]` của `test_bench_args_refuse_every_a6_denied_command` theo L-2c.
  - T28: ba chỗ `restart` của `PC` theo L-2c và một `test-shape` theo bảng trên.

## Assumptions decided by the team
- **A6-1.** Đường lệnh đơn cũ chạy argv qua `process_runner.run_bench`, đồng bộ trong worker, không qua `launch_restart`. Căn cứ: `apply_job.py:250-252` chỉ kiểm `check_bench_args`, và `launch_restart` chỉ được nhận ở task bước restart của khối (`tasks.md:364`). Nếu sai, lý do 2–4 của P-1 vẫn đủ để chọn (a).
- **A6-2.** Không có dòng đề xuất lệnh đơn nào đang lưu `["restart"]`, vì `build_bench_args` từ chối `restart` cho tới `e64a269`. Vì vậy (a) không cần migration hay đối soát.

Câu hỏi nghiệp vụ: 0.

## Kiểm tra
**Touchpoint so với `allowed_new_file_roots` và `protected_paths`.** Theo `.team/profile.json` như đã dán ở addendum-4: roots `['erp_ai', 'docs', '.github']`; protected `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`.

| Đường dẫn | Mới/sửa | Root | Khớp protected |
|---|---|---|---|
| `docs/team/features/CHG-002/design-addendum-6.md` | mới | `docs` | không |
| `erp_ai/agent/tools/change_guard.py` | sửa (đã có ở `e64a269`) | `erp_ai` | không |
| `erp_ai/agent/tools/test_change_guard.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/tools/propose_change.py` | sửa | `erp_ai` | không |
| `erp_ai/agent/tools/test_propose_change.py` | sửa | `erp_ai` | không |

Không có file mã mới.

**Danh sách lệnh bench.** Sau T11, `BENCH_COMMANDS` có `migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build`, `version`, `restart`. Như vậy chỉ thêm đúng `restart`, khớp `e64a269` và §3.2. Enum của tool đơn lệnh từ T11 tới T28 vẫn là 6 lệnh cũ.

**AC và NFR.**
- Danh sách của spec: `AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15`.
- Danh sách của test plan (`design.md` §8.1): `AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15`.

Phụ lục này không bỏ test nào có tên trong §8.1. Test AC-47 của T11 (`test_restart_plain_accepted`, `test_restart_with_any_arg_refused`, `test_every_denied_command_refused`, `test_force_shell_other_site_refused`) và của T28 (`test_bench_command_restart_plain_ok`, `test_denied_command_refused_names_command`) giữ nguyên. Còn **22/22 AC, 4/4 NFR** có test.
