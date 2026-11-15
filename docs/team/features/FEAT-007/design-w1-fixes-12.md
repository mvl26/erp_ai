# FEAT-007 — design-w1-fixes-12: phán ba điểm pre-flight U4b (G-9, G-6, G-5)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu. Không chặn build.
- Đầu vào: `preflight-w1-u4b.md:29`, `:30`, `:33` (G-5, G-6, G-9); `tasks.md:911-915` (T109), `:941-945` (T115), `:946-950` (T116); `design-addendum-3-w1.md:200-210`, `:68`, `:101` (U4b-11), `:103` (U4b-13), `:105` (U4b-15), `:189-190`; `design-addendum-1-U4b-U8.md:245`; `design-addendum-1-U4b-U8-fixes.md:164-178` (Fix 6); `design-w0-fixes-2.md:73`, `:157`.
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `caa555a` — `erp_ai/agent/runner.py:168-200` (`_classify` chỉ chạy ở `TRIGGER_TICKET_INSERT`, `:196`), `:263`, `:296-304`, `:341-375` (`_route`), `:376-386` (`_route_action`), `:472-487` (`_comment_unit`), `:507-525` (`_check_sla`); `erp_ai/agent/routing.py:55-95` (`decide_route`: bốn tham số mới đều có mặc định `None`; `priority` phụ thuộc `due_at`, `now`); `erp_ai/eval/run_eval.py:198-206`; `erp_ai/eval/test_run_eval.py:312` (`class TestRunEvalRun`), `:516-555`; `erp_ai/agent/test_agent_runner.py:132-136` (`_run`, `_comment_count`), `:508` (`class TestRunnerL1Classification`), `:531-533` (`_single_entry` = dòng `classify` duy nhất), `:550-690`; `erp_ai/agent/test_runner_routing.py:142-160`, `:173-1470` (mọi test chạy `self._run()`/`run_for_ticket`, mức quyền, phép đếm comment), `:615-620` (`_comments_posted`), `:768-774` (`_action`, `_comment_text`). Chuỗi chủ file trong `tasks.md` (`grep` dòng task có `files:`): `test_runner_routing.py` … T108 → T109 → T112 → T115 (không task nào sau T115 có file này); `eval/test_run_eval.py` T41 → T72 (không task U4b nào có); T97 `depends: T72, T22`, T108 `depends: T106, T98, T97, T82, T92`.
- Không đổi kiến trúc: theo ADR-036 QĐ 1, 7, 8 (một comment hướng mỗi phiếu, chế độ của lần chạy, chỗ gọi duy nhất), ADR-019 QĐ 7 / ADR-033 QĐ 1, 5 (mỗi lần ghi một mục hành động trên dòng `classify`), ADR-024 QĐ 2, 5; LAYER_RULES của `test_architecture.py` (`erp_ai.eval` được import `erp_ai.agent`, chiều ngược lại cấm) giữ. Không đổi quy tắc nghiệp vụ, không đổi AC. Ba phán quyết dưới đây chỉ chia lại việc giữa T109, T115, T116 và chốt giá trị chờ của test. Không có `DESIGN_CONFLICT`.

---

## Điểm 1 — G-9: phép đếm comment của test đầu-cuối trong `test_runner_routing.py` giữa T115 và T116

### Hiện trạng (dữ kiện)
- U4b-13 (`w1.md:103`): `_route(..., collect_run_id=None)`; có giá trị và `collecting(...)` → không gọi `_comment_unit`, câu định tuyến vào `SECTION_DONE`, câu khác vào `SECTION_DECIDE`, không mục `post_routing_comment`; `None` → như cũ. U4b-15 (`w1.md:105`): `_finish_guidance` ở lượt cuối của `_reason` là chỗ duy nhất đăng comment hướng (T116).
- Nếu T115 vừa mở bộ gom (`_run`) vừa nối `collect_run_id=run_id` vào lời gọi `_route` của `_classify`, thì giữa T115 và T116 lần tạo phiếu ở L1 có **0** comment (câu định tuyến đã vào bộ gom, chưa ai đăng): đó là trạng thái trái AC-23/AC-65, và mỗi phép đếm phải sửa hai lần (T115 về `== before`, T116 về `+ 1`). Expect của T115 lại ghi "các test T109 giữ xanh".
- Test riêng của T115 không cần lời nối đó: `test_route_collect_mode_posts_nothing` gọi `_route(..., collect_run_id=r)` trực tiếp (`w1.md:189`); `test_ai_after_guidance_no_work_no_comment_one_log_line` là lần chạy `comment_mention`, mà `_classify`/`_route` chỉ chạy ở `ticket_insert` (`runner.py:196`).

### Phán quyết
1. **Lời nối chuyển sang T116.** T115 làm mọi phần của U4b-11 (`_run` đọc `count_guidance`, chọn chế độ, `open_collector`/`mark_work_only`, `finally close_collector`) và nhánh `collect_run_id` của `_route` (U4b-13), nhưng lời gọi `_route` trong `_classify` **giữ nguyên như T109** (không truyền `collect_run_id`). T116 thêm đúng một thay đổi ở lời gọi đó: `collect_run_id=run_id` (U4b-13 tự quyết bằng `collecting(run_id)`), cùng lúc với `_finish_guidance`. Không gộp hai task thành một lần merge; mỗi task merge riêng và xanh.
2. **Trạng thái giữa T115 và T116 = trạng thái sau T109.** Trong `test_runner_routing.py` và `test_agent_runner.py`, T115 không sửa một assertion nào của test chạy `self._run()`/`runner.run_for_ticket`; chỉ thêm test mới.
3. **`_route` vẫn trả `lines`** (cùng danh sách câu đã gom) ở cả hai chế độ: dạng trả không đổi, nên các spy bọc `runner._route` (ví dụ `test_broken_sla_condition_stops_route_cleanly`, `routed == …`) giữ giá trị chờ của T109.
4. **T116 thêm `erp_ai/agent/test_runner_routing.py`** vào `files:` và sửa một lần các test đầu-cuối theo luật dưới đây. Chuỗi chủ file: … T112 → T115 → T116 (T116 đã `depends: T115`; không task nào sau có file này).

### Luật T116 cho test đầu-cuối của `test_runner_routing.py`

Phân loại mỗi lần chạy trên `self.ticket` (đo bằng `git grep -n -E "self\._run\(|run_for_ticket|_comment_count\(\)|_comments_posted|_comment_text|post_routing_comment" -- erp_ai/agent/test_runner_routing.py` trên BASE của T116; số dòng `@ caa555a` dưới đây chỉ để dò, gọi test theo tên):

| Loại | Điều kiện | Giá trị chờ sau T116 |
|---|---|---|
| L0 | test đặt `permission_level="L0"` cho lần chạy đó | **không đổi** |
| G | mức L1 trở lên (`RoutingTestBase` đặt L1, `:155`), trigger `ticket_insert`, phiếu chưa có comment hướng, stub trên ngưỡng (`do_tin_cay_pct` 100, `design-w1-fixes-8.md` Điểm 1) — lần đưa hướng | (a) số comment của phiếu sau lần chạy = `before + 1`, **bất kể kết quả định tuyến**: comment duy nhất là comment hướng (`post_guidance`); (b) dòng `classify` không còn mục `post_routing_comment`; (c) câu định tuyến/cảnh báo nằm trong comment hướng |
| G-lỗi | như G nhưng dòng `reason` cuối của lần chạy có `error` khác rỗng | không có comment hướng (T116 chỉ đăng ở lối ra không lỗi, AD3-2); số đếm theo luật thông báo `run_failed` của T110; dev ghi tên test vào thông điệp commit |
| W | lần chạy `ticket_insert` thứ hai trở đi trên phiếu đã có comment hướng | `mark_work_only`, `collecting` sai → `_route` chế độ None → **như sau T109** |

Sửa cụ thể (không còn lựa chọn):
- Hàm trợ giúp `_comments_posted` (`:615-620`) và `_comment_text` (`:771-774`) đọc comment hướng thay cho comment định tuyến, cùng một thân:
  ```python
  (posted,) = [
      a
      for e in self._entries(entry_type="reason")
      for a in json.loads(e.actions or "[]")
      if a["tool"] == runner.GUIDANCE_TOOL
  ]
  self.assertEqual((posted["doctype"], posted["ok"]), ("Comment", True))
  return frappe.db.get_value("Comment", posted["name"], "content")
  ```
- Mọi `assertEqual(self._comment_text(), X)` → `assertIn(X, self._comment_text())` (`:1172`, `test_sharing_disabled_no_task_one_comment`): comment hướng có nhiều mục.
- Danh sách mục hành động của dòng `classify` trong lần chạy G bỏ phần tử `post_routing_comment`: `:1133` (`test_other_category_or_no_person_no_task`) `[("apply_route", True), ("assign_owner", False), ("post_routing_comment", True)]` → `[("apply_route", True), ("assign_owner", False)]`.
- Phép đếm, loại G (giữ `+ 1` hoặc đổi thành `+ 1`): `test_slow_sla_warning_in_log` (`:560`), `test_no_sla_one_warning_one_comment` (`:636`), `test_no_sla_and_assign_request_share_one_comment` (`:650`), `test_switch_off_no_sla_still_one_comment` (`:665`), `test_broken_sla_condition_stops_route_cleanly` (`:721`), `test_assigns_configured_person_one_notification` (`:792`), `test_agent_account_never_assigned_one_comment` (`:839`), `test_failed_assign_one_comment_and_no_second_try` (`:853`), `test_refused_assign_one_comment` (`:901`), `test_existing_assignment_kept` (`:960`), `test_rule_assignment_in_route_save_kept` (`:973`), `test_human_classified_no_route_writes` (`:989`; `post.assert_not_called()` giữ), `test_switch_off_no_todo_no_task` (`:1001`), `test_c_ticket_one_linked_task_assigned` (`:1068`), `test_sharing_disabled_no_task_one_comment` (`:1171`), `test_other_exception_generic_reason_not_sharing` (`:1193`), `test_refused_task_without_exception_no_task_no_comment` (`:1212`), `test_preassigned_by_human_no_task_no_comment` (`:1225`), `test_preassigned_by_rule_no_task_no_comment` (`:1241`), `test_every_write_in_actions_with_before_after` (`:1352`), `test_ticket_text_does_not_steer_route` (`:1457`): `self.assertEqual(self._comment_count(), before_comments + 1)` (hoặc `comments + 1`). Tên test có chữ "no_comment" không đổi tên (NFR-8: lý do ghi trong commit: "comment định tuyến" nay nằm trong comment hướng).
- `test_fake_key_in_prefixes_absent_from_the_posted_comment` (`:353`): `len(surface["comment"]) == 1` giữ (comment đó nay là comment hướng; phép kiểm không lộ khóa áp trên nó).
- Hai test có tiền đề là vá `runner.post_routing_comment` trong lần chạy đầu-cuối — `test_comment_that_wrote_then_raised_is_undone_but_route_kept` (`:874-886`) và `test_comment_exception_recorded_not_raised_not_retried` (`:904-913`) — ở chế độ gom hàm đó không được gọi. Hai test chuyển sang gọi `runner._route(...)` trực tiếp với `collect_run_id=None` (chế độ None, `w1.md:207`: test gọi `_route` trực tiếp không đổi), dựng đối số theo cùng cách của `TestOneCommentPerAction` (T109); mọi assertion của hai test giữ nguyên chữ.
- Loại L0, không đổi: `test_l0_ticket_unchanged_scores_zero_not_null` (`:199-211`), nửa L0 của `test_model_call_count_unchanged` (`:213-226`; nửa L1 đếm lời gọi Cổng model, `_finish_guidance` không gọi Cổng → không đổi), `test_l0_no_todo_no_task` (`:1009-1018`), `TestRoutingLog` ở `:1249`, `:1277`, `:1285`, `:1294`.
- Lần chạy trên phiếu thứ hai (`second`, `:940`, `:1127`, `:1533`): cũng là loại G của phiếu đó; phép kiểm trên `self.ticket` không đổi vì phiếu khác.
- Hit nào của lệnh `git grep` trên không khớp bảng loại → dev trả `DESIGN_CONFLICT` kèm tên test và đầu ra, không tự chọn.

### Dòng thay trong `tasks.md` (chép nguyên văn)

T115 (`tasks.md:941-945`) — thay cả năm dòng bằng:
```
- [ ] T115 — Runner chọn chế độ của lần chạy: đưa hướng hay chỉ làm việc — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_runner_routing.py — depends: T112, T107
  - Tiêu chí: AC-65 (a), (c), AC-23 `[changed]`; ADR-036 QĐ 7; `w1.md:68`, `:101` (U4b-11), `:103` (U4b-13); `design-w1-fixes-12.md` Điểm 1 (lời nối `collect_run_id` vào lời gọi `_route` của `_classify` thuộc T116), Điểm 2 (ba test `actions` của `TestRunnerL1Classification` không đổi ở T115).
  - Receives: `count_guidance`, `open_collector`, `close_collector`, `mark_work_only`, `collect` (T102); `guidance_posted` (T107).
  - Returns: `_run` đọc `count_guidance` một lần; lần đưa hướng ⇔ đếm 0 ∧ `main_path_level != "L0"` ∧ `not below_threshold`; `finally` gọi `close_collector(run_id)`; `_route(..., collect_run_id=None)`: có giá trị và `collecting(collect_run_id)` → 0 comment, câu định tuyến vào `SECTION_DONE`, câu cảnh báo vào `SECTION_DECIDE`, không mục `post_routing_comment`, vẫn trả `lines`; `None` → như T109. Lời gọi `_route` trong `_classify` giữ nguyên như T109 (không truyền `collect_run_id`; T116 nối). R5-2: `open_collector`, `mark_work_only` và phép chọn chế độ đặt sau chốt dưới ngưỡng của U1, không đặt giữa parse và chốt đó; R5-3: dạng trả của `_classify` không đổi. Reviewer dán đoạn `_classify` từ parse tới chốt dưới ngưỡng vào `review-115.md`.
  - Expect: `TestOneCommentPerAction::test_route_collect_mode_posts_nothing` (gọi `_route` trực tiếp sau `open_collector(r)`); `TestOneGuidance::test_ai_after_guidance_no_work_no_comment_one_log_line` xanh; các test T109 giữ xanh: không sửa assertion nào của test chạy `self._run()`/`run_for_ticket` trong `test_runner_routing.py`, `test_agent_runner.py` (reviewer dán `git diff --stat` và xác nhận diff hai file chỉ thêm test).
```

T116 (`tasks.md:946-950`) — thay cả năm dòng bằng:
```
- [ ] T116 — Lượt cuối đăng một comment hướng xử lý gộp mọi việc của lần chạy — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_agent_runner.py — depends: T115, T105, T103
  - Tiêu chí: AC-65 (a), (c), (d), AC-23 `[changed]`; ADR-036 QĐ 1, 8; `w1.md:103` (U4b-13, lời nối), `:105` (U4b-15), `:106` vế (a); AD3-2 (gọi ở mọi lối ra không lỗi: `not wants_tools`, `not tool_results`, `turn == max_turns`), AD3-4, AD3-5 (`runner.py` không có `PENDING_LINE`, không thêm dòng "Chờ duyệt"); `design-w1-fixes-12.md` Điểm 1 (luật T116 cho test đầu-cuối của `test_runner_routing.py`), Điểm 2 (ba test `actions` của `TestRunnerL1Classification`).
  - Receives: `post_guidance` (T103); bộ gom; `action_entry` (T84); nhánh `collect_run_id` của `_route` (T115).
  - Returns: `GUIDANCE_TOOL = "post_guidance"`; `_classify` truyền `collect_run_id=run_id` vào lời gọi `_route` (U4b-13 tự quyết bằng `collecting(run_id)`); `_finish_guidance(context, actions)` là chỗ duy nhất runner gọi `write_ticket.post_guidance`, trước `write_entry` của lượt cuối; thua lần chạy song song → 1 comment kết quả không dấu hiệu (dòng gom thoát HTML một lần); `outcome.get("held")` → không thêm mục hành động; `_reason` trả `bool`. R5-16 (ADR-024 QĐ 2, QĐ 5): lời gọi `post_guidance` nằm trong khối `try` mở sau `frappe.db.savepoint(REASON_TURN_SAVEPOINT)`, sau vòng tool, trước `write_entry` của lượt cuối; mục hành động của nó nằm trong `actions` của lượt đó; không `frappe.db.commit` giữa savepoint của lượt và commit của dòng `reason`.
  - Expect: `TestOneGuidance::test_last_turn_log_failure_leaves_no_guidance` (`write_entry` của lượt cuối ném lỗi → 0 comment hướng còn lại, `count_guidance` = 0; R5-16); `TestOneGuidance::test_chain_1_ticket_insert_one_guidance`, `::test_chain_2_insert_then_ai_three_times_one_guidance`, `::test_chain_7_ai_after_guidance_creates_task_no_new_guidance`, `::test_chain_8_level_l0_or_excluded_team_zero`, `::test_chain_9_empty_prompt_two_runs_one_guidance`, `::test_guidance_has_analysis_done_pending_decide`, `::test_marker_refusal_one_failed_action_entry`, `::test_max_turns_exit_still_posts_guidance`, `::test_lost_race_posts_result_comment_escaped_once`; `TestAskOnly::test_stub_69_70_100` (ca 70, 100: comment hướng có câu định tuyến); `TestRunNotices::test_matrix_eight_situations` (sửa theo `w1.md:187`); `TestRunnerL1Classification::test_l1_applies_mapping_confidence_and_hint`, `::test_l1_empty_route_still_saves_ai_fields_applied_one`, `::test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one` (giá trị chờ "sau T116" của `design-w1-fixes-12.md` Điểm 2); `cmd.test_one` với `erp_ai/agent/test_runner_routing.py`: cả module xanh, test đầu-cuối sửa đúng bảng loại L0/G/G-lỗi/W của `design-w1-fixes-12.md` Điểm 1, hai test vá `post_routing_comment` chuyển sang gọi `_route` trực tiếp, lý do ghi trong commit (NFR-8, STD-TEST-5).
```

---

## Điểm 2 — G-6: ba test so nguyên `actions` của dòng `classify` trong `test_agent_runner.py`

### Hiện trạng (dữ kiện)
- Ba test thuộc `TestRunnerL1Classification` (`test_agent_runner.py:508`), chạy `self._run()` (`ticket_insert`, L1), đọc `_single_entry()` = dòng `classify` duy nhất (`:531-533`): `test_l1_applies_mapping_confidence_and_hint` (`:581-584`: `[apply_route ok]`), `test_l1_empty_route_still_saves_ai_fields_applied_one` (`:629-635`: `[apply_route ok, sla_action]`), `test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one` (`:678-684`: cùng dạng). Cả ba: định tuyến thành công (`applied == 1`), không có người gán (`ASSIGNEE_NOTE` trong `skipped_fields`) → không mục `assign_owner`, không Task, không người theo dõi.
- Hôm nay `_comment_unit` chỉ đăng khi `lines` khác rỗng (`runner.py:474`); `sla_action` là SLA chậm, không thêm câu → 0 comment. Sau T109 `_route_lines` luôn có `ROUTE_DONE` hoặc `ROUTE_NO_CHANGE` → `_comment_unit` luôn chạy → mục `post_routing_comment` đứng **cuối** danh sách (Fix 6 `:246`: các đơn vị ghi trước, comment sau cùng; `runner.py:362-365`).
- Theo Điểm 1, lời nối chế độ gom thuộc T116, không thuộc T115.

### Phán quyết (team-leader đã phán: T109 thêm `erp_ai/agent/test_agent_runner.py`)

| Test | Sau T109 (và giữ nguyên qua T110–T115) | Sau T116 |
|---|---|---|
| `test_l1_applies_mapping_confidence_and_hint` | `[<apply_route ok>, <post_routing_comment>]` | `[<apply_route ok>]` |
| `test_l1_empty_route_still_saves_ai_fields_applied_one` | `[<apply_route ok>, sla_action, <post_routing_comment>]` | `[<apply_route ok>, sla_action]` |
| `test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one` | `[<apply_route ok>, sla_action, <post_routing_comment>]` | `[<apply_route ok>, sla_action]` |

- `<apply_route ok>` và `sla_action`: đúng chữ đang có ở BASE của task (sau T92 là dạng bảy khóa mà T92 đã đặt); task này không đổi chúng.
- `<post_routing_comment>`: cùng dạng khóa của `<apply_route ok>` trong chính phép so đó, với `"tool": "post_routing_comment"`, `"doctype": "Comment"`, `"name": comment_name`, `"ok": True`, các khóa còn lại mang giá trị mặc định của bộ dựng mục (`_route_action` → `action_entry`, không `reason`, không `rule`). `comment_name` đo trong test, không đoán: lấy tên Comment của phiếu trước và sau `self._run()` bằng `frappe.get_all("Comment", filters=authority.ticket_comment_filters(self.ticket.name), pluck="name")`; `(comment_name,) = set(sau) - set(trước)` (đúng một comment mới, là comment định tuyến).
- Sau T116 (lần đưa hướng, Điểm 1 loại G): mục `post_routing_comment` biến mất khỏi dòng `classify`; phép đo `comment_name` bỏ khỏi ba test; danh sách trở lại đúng dạng của BASE T109. Comment hướng là mục `post_guidance` của dòng `reason`, không thuộc ba phép so này. T116 đã có file trong `files:`.
- T115 không chạm ba test (Điểm 1, phán quyết 2).
- Chuỗi chủ `test_agent_runner.py`: … T108 → **T109** → T110 → … → T115 → T116 (T109 `depends: T108`; T110 đã `depends: T109`). Không đổi `depends:`.

### Dòng thay trong `tasks.md` (chép nguyên văn) — gộp với Điểm 3, xem cuối Điểm 3.

---

## Điểm 3 — G-5: `test_eval_uses_runner_route_function` và bốn tham số mới của `decide_route`

### Hiện trạng (dữ kiện)
- `test_run_eval.py:516-555` (`TestRunEvalRun`): bọc `runner.decide_route` và `run_eval.decide_route`, đòi `call_args.args` bằng nhau (`:546`), `call_args.kwargs` bằng nhau (`:547`), `args[2] == mapping` (`:548`). Hôm nay cả hai truyền ba tham số từ khóa `team_exists`, `is_excluded_team`, `is_active_agent` (`runner.py:296-304`, `run_eval.py:198-206`).
- T109 (U4b `:245` vế (1)) cho runner truyền thêm `due_at=`, `due_field_configured=`, `d_watcher=`, `now=`. `now` khác nhau ở mỗi lời gọi → so nguyên `kwargs` không bao giờ xanh dù eval truyền cùng bộ.
- Phán quyết sẵn có `design-w0-fixes-2.md:157`: "`run_eval.py:198` giữ lời gọi cũ (`None`): eval đo model và mapping, không đo ngoại lệ hạn; ghi rõ trong As-Built". `:73`: nơi gọi không truyền bốn tham số nhận đúng `priority` và `notes` như trước (hợp đồng thêm). Người theo dõi (`d_watcher`) không nằm trong số đo của eval (chỉ `priority`, `team`, `category`).

### Phán quyết
1. **Eval không truyền bốn tham số.** `erp_ai/eval/run_eval.py` không đổi một dòng (giữ `design-w0-fixes-2.md:157`). Không task nào nhận `run_eval.py`.
2. **Test so phần chung, và ghim phần khác.** Thay đúng dòng `:547` (`self.assertEqual(eval_route.call_args.kwargs, runner_route.call_args.kwargs)`) bằng:
   ```python
   shared = {"team_exists", "is_excluded_team", "is_active_agent"}
   runner_kwargs, eval_kwargs = runner_route.call_args.kwargs, eval_route.call_args.kwargs
   # eval measures the model and the mapping, not the due-date exceptions or the D watcher (design-w0-fixes-2.md:157)
   self.assertEqual(set(eval_kwargs), shared)
   self.assertEqual(set(runner_kwargs), shared | {"due_at", "due_field_configured", "d_watcher", "now"})
   self.assertEqual({k: eval_kwargs[k] for k in shared}, {k: runner_kwargs[k] for k in shared})
   ```
   `:546` (`args`), `:548` trở đi giữ nguyên chữ. Tên test giữ. Không so giá trị `now`, `due_at` (đã có `TestRunnerHooks::test_due_value_reaches_decide_route` của T109).
3. **Task: T109 thêm `erp_ai/eval/test_run_eval.py`** (chỉ test). Chuỗi chủ file: T41 → T72 → **T109**; T72 là tổ tiên của T109 qua T97 (`depends: T72, T22`) → T108 (`depends: … T97 …`) → T109, nên `depends:` của T109 không đổi. Không task nào sau T109 có file này.
4. RED của phần này: trên BASE T109 cộng mã runner của T109, `:547` cũ đỏ (`AssertionError` do bốn khóa thêm); sau thay ba phép so mới xanh. Dev dán đầu ra.

### Dòng thay trong `tasks.md` (chép nguyên văn) — T109, gộp Điểm 2 và Điểm 3

T109 (`tasks.md:911-915`) — thay cả năm dòng bằng:
```
- [ ] T109 — Bước định tuyến: hạn hoàn thành, người theo dõi, câu tách phiếu, một comment gộp — files: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py, erp_ai/agent/test_agent_runner.py, erp_ai/eval/test_run_eval.py — test: erp_ai/agent/test_runner_routing.py — depends: T108, T104
  - Tiêu chí: AC-19, AC-23, AC-25, AC-27, AC-28 (phần runner); `U4b.md:246`; `U4b-fixes.md` Fix 6 (dòng 164–178); `design-w0-fixes-3.md` phán quyết (1) (`d_watcher` truyền `or ""`). Test FEAT-006 đếm 0 comment khi định tuyến thành công sửa theo AC (NFR-8). `design-w1-fixes-12.md` Điểm 2 (ba test `actions` của `TestRunnerL1Classification` thêm mục `post_routing_comment` cuối danh sách), Điểm 3 (`erp_ai/eval/run_eval.py` không đổi; `test_eval_uses_runner_route_function` so ba khóa chung, ghim bốn khóa chỉ runner có).
  - Receives: `as_deadline`, `d_watcher`, vị từ của T24–T26; `split_text` của T27, T62; `FIELD_LABELS`, `ROUTE_DONE` (T104).
  - Returns: `ROUTE_NO_CHANGE`, `ROUTE_ASSIGNED`, `ROUTE_TASK`, `ROUTE_WATCHER`; `_route_lines(result, assigned, task, watcher) -> list[str]`; `_watch_unit(watcher, context, actions, errors) -> str | None`; `_classify` gọi `decide_route(..., due_at=, due_field_configured=, d_watcher=settings.d_ticket_watcher or "", now=)` và ghi `split_requested`, `split_requests` (`U4b.md:245` vế (1), (4), (5)); `_route(..., split_text=None)` đăng đúng 1 comment gộp qua `_comment_unit` (chế độ không gom), mục `post_routing_comment` đứng cuối `actions` của dòng `classify`. Lời gọi `decide_route` của `erp_ai/eval/run_eval.py` giữ ba tham số từ khóa (`design-w0-fixes-2.md:157`). R5-3: lời gọi `decide_route` giữ tham số từ khóa `is_excluded_team=`, không gộp vị từ vào chỗ khác; sau merge `git grep -n "is_excluded_team=" team/FEAT-007 -- erp_ai/agent/runner.py` in đúng 1 dòng (tech-lead dán vào progress).
  - Expect: `TestRunnerHooks::test_due_value_reaches_decide_route`, `::test_d_watcher_followed_once`, `::test_watcher_notify_off_logged`, `::test_split_comment_once_in_route_comment`, `::test_watcher_failure_rolls_back_only_watcher_unit`, `::test_routing_step_makes_no_gateway_call`; `TestOneCommentPerAction::test_route_success_one_comment_lists_fields_assignee_task`, `::test_success_with_failure_line_still_one_comment`, `::test_no_field_change_one_comment` xanh; `cmd.test_one` với `erp_ai/agent/test_agent_runner.py`: `TestRunnerL1Classification::test_l1_applies_mapping_confidence_and_hint`, `::test_l1_empty_route_still_saves_ai_fields_applied_one`, `::test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one` xanh với giá trị chờ "sau T109" của `design-w1-fixes-12.md` Điểm 2, cả module xanh; `cmd.test_one` với `erp_ai/eval/test_run_eval.py`: `TestRunEvalRun::test_eval_uses_runner_route_function` xanh với ba phép so của `design-w1-fixes-12.md` Điểm 3, cả module xanh, `git diff <BASE>..HEAD -- erp_ai/eval/run_eval.py` rỗng.
```

T110 (`tasks.md:916`) — không đổi chữ: đã `depends: T109`, nhận `test_agent_runner.py` sau T109 trong chuỗi.

---

## Tổng hợp cho team-leader

| Điểm | Task đổi | `files:` thêm | `depends:` | Giá trị chờ |
|---|---|---|---|---|
| G-9 | T115 (lời nối `collect_run_id` rời T115), T116 (nhận lời nối) | T116 + `erp_ai/agent/test_runner_routing.py` | không đổi (… T112 → T115 → T116) | giữa T115 và T116 = sau T109; sau T116 theo bảng L0/G/G-lỗi/W |
| G-6 | T109 | T109 + `erp_ai/agent/test_agent_runner.py` (team-leader đã phán) | không đổi (T108 → T109 → T110) | sau T109–T115: thêm `post_routing_comment` cuối; sau T116: bỏ |
| G-5 | T109 | T109 + `erp_ai/eval/test_run_eval.py`; `run_eval.py` không task nào | không đổi (T41 → T72 → … → T109) | so ba khóa chung, ghim tập khóa hai phía |

Không có câu hỏi nghiệp vụ. Không có `DESIGN_CONFLICT`.
