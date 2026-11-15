# FEAT-007 — design-w1-fixes-17: phán hai điểm (T80 khẳng định danh sách tool dưới ngưỡng; cô lập từng phiếu của việc quét 15 phút)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `tasks.md:823-840` (T80 với dòng `progress:` `:828`, T81, T82); `design-w1-fixes-8.md:30-45` và Điểm 1 mục 4–5 (`:75-80`); `design-addendum-1-U1.md:259-263`; `review-34.md:20,41,50,68,69,77`; `design.md:74-75` (D-16, D-17), mục 3.5.1 (`:366-377`).
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `ed341b9` — `erp_ai/agent/runner.py:23-30` (import registry), `:583-606` (`_reason`), `:729-737` (`_run_tool`); `erp_ai/agent/tools/registry.py:14-58` (`GrantInputs`, `ToolContext.grant_inputs`), `:98-174` (`ASK_TOOL_NAMES`, `GRANT_TABLE`, `grant`), `:176-218` (`_legacy_inputs`, `get_tool_schemas`, `_grants_group`, `grants_*`), `:272-286` (`execute_tool`); `erp_ai/agent/test_agent_runner.py:909-913,939,1210,1253-1267` (cách test đọc `self.gateway.calls[i]["tools"]`); `erp_ai/agent/missed_scan.py` (cả file); `erp_ai/agent/queue.py:15-44` (`enqueue_agent_run`); `erp_ai/agent/test_missed_scan.py:1-82`, `:174-180`, `:270-322`; `erp_ai/hooks.py:164-168`; `tasks.md:476-485` (T33, T34), `:559-562` (T44). Mã Frappe đã cài (chỉ đọc, `apps/frappe` @ `v15.118.0-1106-g2e9ecdc03f`): `frappe/core/doctype/scheduled_job_type/scheduled_job_type.py:142-156`, `:197-204`; `frappe/utils/error.py:36-77`; `frappe/utils/background_jobs.py:168-172`, `:246-257`.
- Không gọi Explore: lời giao giới hạn đúng các phần đầu vào trên.
- Không đổi kiến trúc: ADR-030 QĐ 3, QĐ 4 (bảng cấp, một vị từ dưới ngưỡng), ADR-011 (một hàm cấp `grant`), ADR-033 QĐ 2 (quét bù xếp lại như trigger tạo phiếu). Không đổi quy tắc nghiệp vụ. Chuẩn áp dụng: STD-TEST-5 ("Do not change an assertion to match wrong behavior; change a test only when the spec changes."), STD-TEST-8 ("Test edge cases and error paths, not only the happy path."), STD-ERR-1 ("Do not swallow errors; every catch must handle the error, add context and rethrow, or state clearly why it is ignored."), STD-SEC-6. Không có `DESIGN_CONFLICT` (lý do ở từng điểm).

---

## Điểm 1 — T80: khẳng định danh sách tool gửi model khi dưới ngưỡng

### Hiện trạng (dữ kiện, đọc ở `ed341b9`)
- `_reason` (`runner.py:597-606`): `grant = (context.effective_level, bool(context.instructor), context.change_enabled, context.unrestricted)`; `tools = get_tool_schemas(*grant)`; ba cờ khối lấy từ `grants_change_tools(*grant)`, `grants_site_admin_tools(*grant)`, `grants_unrestricted_tools(*grant)`. Dev trích `:597-598` đúng.
- `get_tool_schemas` chữ ký cũ (`registry.py:190-193`) gọi `grant(_legacy_inputs(...))`; `_legacy_inputs` (`:176-187`) dựng `GrantInputs` chỉ với `effective_level`, `main_path_level=effective_level`, `has_instructor`, `record_tools=code_change=change_enabled`, `unrestricted`; `over_budget`, `below_threshold`, `act_now` lấy mặc định `False`. Vậy trước T82, danh sách tool gửi model **không bao giờ** theo `context.below_threshold`.
- `execute_tool` (`:272-276`) gọi `grant(context.grant_inputs())`; `grant_inputs()` (`:42-58`) mang `below_threshold=self.below_threshold`. Dưới ngưỡng, `GRANT_TABLE` (`:116`) tắt `ticket_write` và `grant` (`:158-162`) chỉ thêm lại spec có tên ∈ `ASK_TOOL_NAMES = {"post_comment"}` → `set_classification` trả `{"ok": False, "reason": "tool không được cấp ở mức/thẩm quyền hiện tại"}`, `post_comment` chạy. `_run_tool` (`runner.py:734-737`) đưa thẳng `block["name"]` vào `execute_tool`, không lọc theo `tools` đã gửi. Ranh giới cấp quyền phía server đã đúng từ T80.
- Test đọc danh sách tool bằng `self.gateway.calls[i]["tools"]` (`test_agent_runner.py:909`, `:939`, `:1210`).

### Ba test của T80 và dòng Expect của T81, xét phụ thuộc danh sách tool
| Test | Khẳng định theo `design-w1-fixes-8.md:76-80` | Phụ thuộc `tools` của lời gọi `reason`? |
|---|---|---|
| `test_comment_run_reads_latest_classification_of_its_ticket` | `self.latest_classification` gọi đúng một lần với tên phiếu (lần `comment_mention`), không gọi ở lần `ticket_insert` | Không. |
| `test_comment_run_below_threshold_from_classify_row_is_ask_only` | `set_classification` `ok` False chứa `"không được cấp"`, `post_comment` `ok` True; **và** mọi tool `ticket_write` trong `tools` có tên ∈ `ASK_TOOL_NAMES` | **Có, vế cuối** — đỏ ở T80 vì `tools` đến từ `_legacy_inputs` (`below_threshold=False`), còn `set_classification`, `set_resolution_hint`. |
| `test_comment_run_at_threshold_from_classify_row_gets_ticket_write` | `set_classification` `ok` True | Không: kết quả do `execute_tool` quyết; trên ngưỡng `set_classification` có cả trong danh sách cũ. |
| `test_plain_user_mention_after_instructor_gets_no_write_tools` | không có `task_write`, `change_propose`, `site_admin` (mặc định trên ngưỡng) | Không: khi `has_instructor` False, cả `_legacy_inputs` lẫn `grant_inputs()` đều tắt ba nhóm này (`GRANT_TABLE` `:117-137`, `unrestricted_granted` `:101-109` đòi người ra lệnh); hai đường cho cùng tập tên dù test khẳng định trên `tools` hay trên kết quả `execute_tool`. |
| T81 `test_low_confidence_insert_skips_routing_writes`, `::test_insert_at_threshold_routes_and_writes` | không `apply_route`, `applied` 0 / `_route` chạy; `predicted_confidence_pct` của dòng `classify` | Không: chỉ khẳng định bước `_classify`/`_route` và dòng `classify`; không đọc `tools`. |

### Phán quyết: chọn (a)
1. **T80** bỏ vế "mọi tool `ticket_write` trong `tools` của lời gọi `reason` có tên ∈ `ASK_TOOL_NAMES`" khỏi `test_comment_run_below_threshold_from_classify_row_is_ask_only`. Test vẫn giữ tên, giữ dòng `classify` 69, ngưỡng 70, L1, không người ra lệnh, `act_now` tắt, model gọi `set_classification` rồi `post_comment` trong một lượt. **T80 khẳng định thay**: (i) kết quả `set_classification` có `ok` False và `reason` chứa `"không được cấp"`; (ii) kết quả `post_comment` có `ok` True; (iii) không khẳng định gì trên `self.gateway.calls[i]["tools"]` và trên chữ `system` của lời gọi `reason`. Đây là chứng minh luật ngưỡng ở ranh giới server (`execute_tool`), đúng phần T80 làm. Không test nào khác của T80, T81 được khẳng định trên `tools` khi dưới ngưỡng.
2. **T82** thêm lại vế đó vào chính test này (T82 sở hữu `test_agent_runner.py` và sửa `_reason`), viết đỏ trước: trên mã T81, thêm khẳng định → `cmd.test_one` của `erp_ai/agent/test_agent_runner.py` FAILED ở test đó (`set_classification` có trong danh sách); đổi `_reason` sang `granted = grant(context.grant_inputs())`, `tools = granted.schemas()` (`U1.md:263`) → xanh. Cách viết khẳng định (không lựa chọn mở):
   ```python
   offered = {tool["name"] for tool in self.gateway.calls[0]["tools"]}
   ticket_write = {spec.name for spec in registry._all_specs() if spec.group == "ticket_write"}
   self.assertLessEqual(offered & ticket_write, ASK_TOOL_NAMES)
   self.assertIn("post_comment", offered)
   ```
   (`registry` là `erp_ai.agent.tools.registry`, `ASK_TOOL_NAMES` từ cùng module; T82 thêm import nếu file chưa có.)
3. **Vì sao không (b), (c).** (b) bỏ mất test duy nhất ở T80 chứng minh `latest_classification` thật (dòng `classify` thật, `side_effect = self.real_latest_classification`) dẫn tới `below_threshold` trong context của lần `comment_mention`; T80 khi đó không có test cho AC-22 phía lần chạy không tạo phiếu. (c) kéo `_reason` về T80 buộc kéo theo: ba cờ khối mới của `build_reason_system` (T79, mà T80 không `depends:` T79), việc xóa `grants_*`/`_legacy_inputs` và 15 chỗ E1..E15 của `test_architecture.py` (Chèn 8 của T82: luật `test_registry_has_one_grant_function` đòi runner gọi đúng một hàm lấy schema, đổi từ `SCHEMA_FUNCTION` sang `RUNNER_SCHEMA_CALL`) — tức gần hết T82 dồn vào một task đang bị chặn; T82 còn lại chỉ phần gỡ cầu. Lối (a) không chuyển file nào, không đổi `files:`, `depends:` của task nào.
4. **Trạng thái giữa T80 và T82 trên nhánh tính năng: chấp nhận được.** Trong khoảng này, lần chạy dưới ngưỡng (cả lần `comment_mention` từ T80, cả lần tạo phiếu từ T81) vẫn được mời `set_classification`, `set_resolution_hint` và prompt chưa có khối "chỉ hỏi"; model gọi thì `execute_tool` trả "không được cấp", không ghi gì. Lý do chấp nhận: (i) quyền được kiểm ở server, nơi duy nhất có hiệu lực (mục 5 của thiết kế: quyền ở ranh giới và phía server); danh sách tool chỉ là gợi ý cho model; (ii) so với trước T80 (`below_threshold` luôn False, ghi được thật), T80 chỉ siết chặt; (iii) chỉ trên `team/FEAT-007`, không tới `develop`/prod trước M8 (sau T83, `cmd.test` cả bộ) và G5; giá phải trả chỉ là vài lượt model bị từ chối trong test nội bộ. Điều kiện: không merge `team/FEAT-007` vào `develop` khi T80 đã merge mà T82 chưa — chuỗi T80 → T81 → T82 → T83 → M8 đã bảo đảm.
5. Không mâu thuẫn ADR: ADR-030 QĐ 4 (một vị từ `is_below_confidence`) và ADR-011 (một hàm `grant`) giữ nguyên ở cả T80 (`execute_tool`) và T82 (`_reason`); không ADR nào đòi danh sách tool và quyền thực thi đổi trong cùng một task.

### Dòng task thay thế (dán nguyên văn)
**T80 — dòng `Tiêu chí:` (`tasks.md:824`), thay cả dòng:**

  - Tiêu chí: AC-13 (đầu-cuối), AC-22 (lần chạy không tạo phiếu, phía `execute_tool`); `U1.md:259-260`, `:207`; `design-w1-fixes-8.md` Điểm 1, Điểm 2, Điểm 3 mục 2; F-3 theo `design-w1-fixes-9.md` Điểm 1; `design-w1-fixes-17.md` Điểm 1 (khẳng định danh sách tool gửi model dưới ngưỡng thuộc T82, không thuộc T80). Lần chạy tạo phiếu ở T80: `category=None`, `below_threshold=False` (chuyển tiếp, T81 thay; không test nào ghim). `RunnerTestBase.setUp` vá `policy.latest_classification` trả `SEEDED_CLASSIFICATION = (f"{PREFIX}category", 100)` và đặt `confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD` (STD-TEST-6); không sửa `test_runner_status.py`, `test_runner_routing.py`. T80 không sửa `_reason`: `tools` vẫn từ `get_tool_schemas` chữ ký cũ tới T82.

**T80 — dòng `Expect:` (`tasks.md:827`), thay cả dòng:**

  - Expect: `TestRunnerGrant::test_plain_user_mention_after_instructor_gets_no_write_tools` (khẳng định trên `task_write`, `change_propose`, `site_admin`, với mặc định trên ngưỡng), `::test_comment_run_reads_latest_classification_of_its_ticket`, `::test_comment_run_below_threshold_from_classify_row_is_ask_only` (dòng `classify` 69, ngưỡng 70; chỉ khẳng định kết quả: `set_classification` `ok` False, `reason` chứa `"không được cấp"`, `post_comment` `ok` True; không khẳng định trên `tools` hay `system` của lời gọi `reason` — `design-w1-fixes-17.md` Điểm 1), `::test_comment_run_at_threshold_from_classify_row_gets_ticket_write` (dòng 70) xanh; `erp_ai/tests/test_architecture.py::test_authority_has_no_comment_scan_for_instructor` xanh; `erp_ai/agent/test_runner_status.py` (gồm `TestRunnerStatus::test_whole_turn_waits_before_its_first_tool`) và `erp_ai/agent/test_runner_routing.py` (gồm `TestRoutingInjection::test_ticket_text_does_not_steer_route`) xanh không sửa. Đỏ F-3: xóa `latest_instructor` trước khi sửa `test_result_comment.py` → `cmd.test_one` của file đó ra `AttributeError: module 'erp_ai.agent.authority' has no attribute 'latest_instructor'`; sửa hai khẳng định → xanh. `cmd.test_one` xanh cả file: `erp_ai/agent/changes/test_result_comment.py`, `erp_ai/agent/test_authority.py`, `erp_ai/agent/test_agent_runner.py`. Ngoài `erp_ai/tests/test_architecture.py`, `git grep -n latest_instructor -- '*.py'` trên nhánh task ra 0 dòng.

**T80 — dòng `progress:` (`tasks.md:828`):** không thay chữ cũ; tech-lead nối thêm cuối dòng: ` · phán: designer chọn (a), `design-w1-fixes-17.md` Điểm 1; chuỗi T80 → T81 mở lại`.

**T81:** không đổi dòng nào (dòng Expect không phụ thuộc danh sách tool, xem bảng trên).

**T82 — dòng `Expect:` (`tasks.md:840`), thay cả dòng:**

  - Expect: `TestRunnerGrant::test_reason_prompt_flags_come_from_grant`, `::test_over_budget_run_offers_l1_tool_set`, `::test_log_seeded_midday_over_budget_next_run_l1`, `::test_low_confidence_with_instructor_and_act_now_keeps_record_tools`; `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_wait_for_ok_five_switches_off_l1_to_l3`, `::TestReasonSystem::test_each_block_present_iff_its_flag` (đủ 5 khối) xanh. Thêm lại khẳng định danh sách tool dưới ngưỡng (`design-w1-fixes-17.md` Điểm 1 mục 2): trong `TestRunnerGrant::test_comment_run_below_threshold_from_classify_row_is_ask_only` (T80) thêm `offered = {tool["name"] for tool in self.gateway.calls[0]["tools"]}`, `ticket_write = {spec.name for spec in registry._all_specs() if spec.group == "ticket_write"}`, `self.assertLessEqual(offered & ticket_write, ASK_TOOL_NAMES)`, `self.assertIn("post_comment", offered)`, không đổi khẳng định nào khác của test; đỏ trước trên mã T81 (chưa sửa `_reason`): `cmd.test_one` `erp_ai/agent/test_agent_runner.py` FAILED ở test đó (`AssertionError`, `set_classification` trong `offered`); sau `_reason` dùng `grant(context.grant_inputs())` → xanh. Gỡ cầu đỏ trước: đổi `erp_ai/agent/tools/test_registry.py::TestGrantInputs::test_bridge_change_switch_still_brings_record_tools` thành `::test_record_tools_only_from_its_own_switch` (`change_enabled=True, record_tools=False` → (2) False) → đỏ (`AssertionError: True is not false`), gỡ vế `or self.change_enabled` → xanh. `cmd.test_one` xanh cả file: `erp_ai/agent/tools/test_site_api.py`, `erp_ai/tests/test_tasks.py`, `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/agent/test_agent_runner.py`. `cmd.test_one` xanh cả file `erp_ai/tests/test_architecture.py` (Chèn 8). Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py`, `test_agent_runner.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1. `erp_ai/agent/test_classification.py` xanh cả file (`cmd.test_one`), bốn test của Điểm 2 đỏ trước trên mã T79.

T82: `files:`, `depends:`, `Tiêu chí:`, `Returns:` không đổi (`test_agent_runner.py` đã trong `files:`; AC-22 đã trong `Tiêu chí:`).

### Khẳng định chưa chạy (Điểm 1)
- Không chạy test nào. Việc vế danh sách tool đỏ ở T80 và xanh sau T82 là suy từ mã đọc (`runner.py:597-598`, `registry.py:176-193`, `:151-174`), chưa thực thi.
- Không đọc mã của `test_plain_user_mention_after_instructor_gets_no_write_tools` (T80 viết mới, chưa có ở `ed341b9`); kết luận "không phụ thuộc" dựa trên định nghĩa ở `design-w1-fixes-8.md:80` và bảng cấp.
- Đã đọc `_run_tool` (`runner.py:729-737`) đưa tên tool thẳng vào `execute_tool`; không đọc phần còn lại của `_run_tool` và vòng lượt sau `:640`.

---

## Điểm 2 — T34 (đã merge): việc quét 15 phút dừng ở lỗi đầu tiên

### Hiện trạng (dữ kiện, đọc ở `ed341b9`)
- `scan_missed_tickets` (`missed_scan.py:78-98`): cả thân nằm trong một `try`; lỗi bất kỳ → một `frappe.log_error(TITLE_RUN_FAILED, f"missed_scan error={type(exc).__name__}")`, một `logger.error(...)`, `return`. Lỗi có thể đến từ hai chỗ theo phiếu: vị từ `policy.can_send_ticket(name)`, `policy.runs_today(name, now)` trong vòng lặp của `find_missed_tickets` (`:68-74`), và `queue.enqueue_agent_run(name, …)` trong vòng của `scan_missed_tickets` (`:89-91`).
- Thứ tự: SQL lấy `SCAN_CANDIDATE_LIMIT` ứng viên mới nhất (`order by t.creation desc`), rồi `reversed(...)` → xét **cũ trước**. Một phiếu luôn ném ở vị từ là phiếu cũ nhất còn là ứng viên mãi (không có dòng `classify` có `predicted_category`) → mọi lần quét dừng ở nó, `find_missed_tickets` không trả gì, không phiếu mới nào được xếp: vi phạm AC-16 cho mọi phiếu sau nó. Lỗi ở `enqueue_agent_run` của phiếu thứ k bỏ các phiếu k+1..n của lần đó.
- Commit sau lối lỗi (đọc mã Frappe, chưa chạy): cron `*/15` (`hooks.py:167`) chạy qua `run_scheduled_job` → `ScheduledJobType.execute` (`scheduled_job_type.py:142-156`): hàm trả về bình thường → `frappe.db.commit()`; hàm ném → `frappe.db.rollback()` và chỉ ghi `"Failed"` vào logger `scheduler`, **không** tạo Error Log. `frappe.log_error` (`error.py:74-77`) `insert` Error Log ngay trong giao dịch đang mở (trừ khi `frappe.flags.read_only` hoặc `defer_insert`). `enqueue_agent_run` gọi `frappe.enqueue(..., enqueue_after_commit=True)` → `frappe.db.after_commit.add(enqueue_call)` (`background_jobs.py:168-170`): job chỉ vào RQ khi commit. Kết luận: vì `scan_missed_tickets` bắt lỗi rồi `return` bình thường, Error Log **và** các job đã xếp trước lỗi đều được commit; nếu để ngoại lệ thoát ra, cả hai mất và lỗi không hiện ở Error Log. Việc quét không ghi bảng nào của app (chỉ đọc và xếp job sau commit), nên commit sau lỗi không để lại ghi dở.

### Phán quyết: cô lập từng phiếu, có trần số lỗi
1. **Lỗi theo phiếu** (vị từ `can_send_ticket`/`runs_today` của một tên, `enqueue_agent_run` của một tên): bắt `Exception` cho riêng phiếu đó, ghi tên lớp lỗi vào danh sách `failures`, xét phiếu kế. Phiếu lỗi không tính vào `SCAN_BATCH`. Không cần savepoint: phần theo phiếu không ghi DB (STD-ERR-1: lỗi không bị nuốt — gom lại và báo một lần ở cuối, lý do ghi trong docstring).
2. **Trần**: hằng mới `SCAN_MAX_FAILURES = SCAN_BATCH` (50). Khi `len(failures)` đạt trần, dừng xét thêm (cả trong `find_missed_tickets` lẫn vòng xếp job); phiếu đã tìm được vẫn được xếp. Trần giữ mỗi lần chạy trong giới hạn job hàng `default` 300 s (D-16) khi lỗi là lỗi chung (ví dụ mất kết nối, mọi phiếu đều ném). Một phiếu (hoặc dưới 50 phiếu) luôn ném không còn chặn phiếu mới.
3. **Lỗi cả lần chạy** (`policy.is_enabled`, `_agent_enabled_at`, đọc `max_runs_per_ticket_per_day`, SQL ứng viên): giữ nguyên như T34 — một `log_error(TITLE_RUN_FAILED, f"missed_scan error={…}")`, một `logger.error("missed_scan: lỗi %s, đã xếp %s phiếu", …)`, `return` bình thường.
4. **Log mỗi lần chạy (D-17 giữ nguyên chữ):** đúng một dòng logger mỗi lần chạy và tối đa một `frappe.log_error` tiêu đề hằng mỗi lần chạy (không một Error Log mỗi phiếu). Khi `failures` khác rỗng: `frappe.log_error(TITLE_RUN_FAILED, f"missed_scan failed={len(failures)} error={failures[0]}")` và `logger.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", failures[0], len(failures), queued)`, không có dòng `info`. Chữ log chỉ có tên lớp lỗi và con số, không tên phiếu, không chữ phiếu (STD-SEC-6, như `review-34.md` đã kiểm).
5. **Chữ ký:** `find_missed_tickets(now: datetime, *, failures: list[str] | None = None) -> list[str]` — thêm tham số chỉ-từ-khóa, không đổi gì khi gọi kiểu cũ: `failures is None` → lỗi vị từ ném ra như nay (test T33 và người gọi trực tiếp không đổi); `scan_missed_tickets` truyền một danh sách. Mục 3.5.1 đọc kèm điểm này.
6. **Không mâu thuẫn ADR:** ADR-033 QĐ 2 (xếp lại như trigger tạo phiếu, chống trùng bằng `job_id` + `deduplicate`) giữ; ADR-033 QĐ 5 không áp (D-17: việc đợt 0 không ghi phiếu). T44 chỉ thêm 3 dòng vào khóa `cron` của `hooks.py`, không chạm `missed_scan.py`; T180 không chạm `hooks.py` → không chung file, không cần `depends:` T44.
7. **Đổi hai test có sẵn (STD-TEST-5):** `test_enqueue_error_logged_once_and_swallowed` và `test_policy_error_logged_once_and_swallowed` ghim hành vi "dừng ở lỗi đầu tiên" mà phán quyết này đổi → xóa, thay bằng test mới ở khối T180 dưới (không nới khẳng định: test mới khẳng định chặt hơn, cả số phiếu đã xếp).

Hình dạng mã (để dev và reviewer cùng đọc; tên hằng, chữ log là ràng buộc):
```python
SCAN_MAX_FAILURES = SCAN_BATCH

# trong find_missed_tickets, thay vòng hiện có
for name in reversed(candidates):
	name = str(name)
	try:
		missed = policy.can_send_ticket(name) and policy.runs_today(name, now) < max_runs
	except Exception as exc:
		if failures is None:
			raise
		failures.append(type(exc).__name__)
		if len(failures) >= SCAN_MAX_FAILURES:
			break
		continue
	if missed:
		found.append(name)
		if len(found) == SCAN_BATCH:
			break

# trong scan_missed_tickets
failures: list[str] = []
try:
	...  # is_enabled như cũ
	for name in find_missed_tickets(now or now_datetime(), failures=failures):
		try:
			if queue.enqueue_agent_run(name, TRIGGER_TICKET_INSERT):
				queued += 1
		except Exception as exc:
			failures.append(type(exc).__name__)
			if len(failures) >= SCAN_MAX_FAILURES:
				break
except Exception as exc:
	...  # như cũ: log_error "missed_scan error=…", logger.error, return
if failures:
	frappe.log_error(TITLE_RUN_FAILED, f"missed_scan failed={len(failures)} error={failures[0]}")
	logger.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", failures[0], len(failures), queued)
	return
logger.info(f"missed_scan: xếp {queued} phiếu")
```

### Khối task T180 (dán nguyên văn vào `tasks.md`, sau T34)

- [ ] T180 — Việc quét 15 phút cô lập lỗi từng phiếu — files: erp_ai/agent/missed_scan.py, erp_ai/agent/test_missed_scan.py — test: erp_ai/agent/test_missed_scan.py — depends: T34
  - Tiêu chí: AC-16 (một phiếu luôn lỗi không chặn phiếu mới); D-16 (trần thời gian job hàng `default`); D-17 (một dòng logger mỗi lần chạy, lỗi → một `frappe.log_error` tiêu đề hằng); `design-w1-fixes-17.md` Điểm 2; `review-34.md:20,77`. Không đổi `hooks.py` (T44 sở hữu phần thêm vào khóa `cron`).
  - Receives: `find_missed_tickets`, `scan_missed_tickets`, `SCAN_BATCH`, `TITLE_RUN_FAILED`, helper `_scan_with_error`, `_assert_one_constant_title_error`, `_ticket`, `_enable_agent` của `test_missed_scan.py` (T33, T34).
  - Returns: hằng `SCAN_MAX_FAILURES = SCAN_BATCH`; `find_missed_tickets(now, *, failures: list[str] | None = None)` — `failures is None` ném như cũ, có danh sách thì ghi tên lớp lỗi rồi xét phiếu kế, dừng khi đạt `SCAN_MAX_FAILURES`; `scan_missed_tickets` bắt lỗi `enqueue_agent_run` từng phiếu vào cùng danh sách, cuối lần chạy nếu có lỗi thì đúng một `frappe.log_error(TITLE_RUN_FAILED, f"missed_scan failed={len(failures)} error={failures[0]}")` và đúng một `logger.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", failures[0], len(failures), queued)`; lỗi cả lần chạy giữ nguyên lối T34. `_assert_one_constant_title_error` thêm tham số `message="missed_scan error=RuntimeError"`. Xóa `test_enqueue_error_logged_once_and_swallowed`, `test_policy_error_logged_once_and_swallowed` (lý do trong commit: hành vi "dừng ở lỗi đầu tiên" đổi theo `design-w1-fixes-17.md` Điểm 2).
  - Expect (đỏ trước trên mã `ed341b9`, ba test đầu): `TestMissedScan::test_ticket_that_always_raises_does_not_starve_newer_ones` (ba phiếu `OLD_ENOUGH + 0, 1, 2 s`; `policy.can_send_ticket` vá bằng hàm ném `RuntimeError(SECRET_TEXT)` khi `name` là phiếu cũ nhất, ngược lại trả `policy.can_send_ticket` thật; `queue.enqueue_agent_run` vá `wraps=` hàm thật, `frappe.enqueue` vá → tên phiếu trong các lời gọi `enqueue_agent_run` là đúng `[phiếu thứ hai, phiếu thứ ba]`; `log_error.call_args_list == [call(TITLE_RUN_FAILED, "missed_scan failed=1 error=RuntimeError")]`; `logger.return_value.method_calls == [call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 1, 2)]`; không `SECRET_TEXT`, không tên phiếu trong đối số `log_error`) — đỏ: `enqueue_agent_run` không được gọi; `::test_enqueue_error_on_one_ticket_still_queues_the_rest` (ba phiếu, `_scan_with_error(queue, "enqueue_agent_run", [True, RuntimeError(SECRET_TEXT), True])` → `_assert_one_constant_title_error(log_error, tickets, message="missed_scan failed=1 error=RuntimeError")`; logger `[call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 1, 2)]`) — đỏ: lần chạy dừng sau phiếu thứ nhất; `::test_per_ticket_failures_stop_at_the_cap` (ba phiếu, `patch.object(missed_scan, "SCAN_MAX_FAILURES", 2, create=True)`, `policy.can_send_ticket` luôn ném `RuntimeError` → `can_send_ticket` được gọi đúng 2 lần; `log_error` `[call(TITLE_RUN_FAILED, "missed_scan failed=2 error=RuntimeError")]`; logger `[call.error("missed_scan: lỗi %s ở %s phiếu, đã xếp %s phiếu", "RuntimeError", 2, 0)]`; ngoài khối vá, `missed_scan.SCAN_MAX_FAILURES == missed_scan.SCAN_BATCH`) — đỏ: `can_send_ticket` gọi 1 lần và chữ `log_error` khác. Xanh trước và sau (giữ hành vi): `::test_run_level_error_logged_once_and_swallowed` (`_scan_with_error(policy, "is_enabled", RuntimeError(SECRET_TEXT))` → `_assert_one_constant_title_error(log_error, tickets)` với chữ mặc định `"missed_scan error=RuntimeError"`; logger `[call.error("missed_scan: lỗi %s, đã xếp %s phiếu", "RuntimeError", 0)]`), `::test_find_without_failures_list_still_raises` (`policy.can_send_ticket` ném `RuntimeError` → `assertRaises(RuntimeError)` quanh `missed_scan.find_missed_tickets(NOW)`). Các test khác của file (gồm `test_two_scans_one_job_per_ticket`, `test_agent_disabled_noop`, `test_batch_limit_oldest_first`, `test_old_refused_tickets_do_not_starve_a_new_one`, `test_warns_once_when_candidate_limit_reached`, `test_cron_declared_every_15_minutes`) xanh không sửa. `cmd.test_one` xanh cả file `erp_ai/agent/test_missed_scan.py`. Không `[migrate]` (không đổi schema).

### Khẳng định chưa chạy (Điểm 2)
- Không chạy test, không chạy job quét. "Error Log và job đã xếp được commit khi hàm trả về bình thường" suy từ đọc `scheduled_job_type.py:142-156`, `error.py:74-77`, `background_jobs.py:168-170`; không đọc phần Frappe chạy `after_commit` khi commit và xóa nó khi rollback, không đọc đường scheduler xếp `run_scheduled_job` lên hàng.
- Không đọc điều gì xảy ra khi một callback `after_commit` (đưa job vào Redis) ném lúc commit — ngoài phạm vi `try` của việc quét, không đổi bởi T180.
- Không đọc mã `policy.can_send_ticket`, `policy.runs_today` để biết chúng có ghi DB hay không; "phần theo phiếu không ghi DB" dựa trên tên/vai trò (vị từ, đếm) và mục 3.5.1.
- Ba test đầu đỏ trên `ed341b9` là suy từ mã đọc, chưa thực thi. `ENABLED_AT = 2099-01-01` (`test_missed_scan.py:20`) làm phiếu khác của site không thành ứng viên, nên số lời gọi trong test là tất định (đọc, chưa chạy).
