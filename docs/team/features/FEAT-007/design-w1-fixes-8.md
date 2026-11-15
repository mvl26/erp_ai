# FEAT-007 — design-w1-fixes-8: phán ba điểm "dưới ngưỡng" của pre-flight đợt 1 (F-5, F-6, F-7; T80, T81, T72)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `preflight-w1.md:27-29` (F-5, F-6, F-7), `:56-57`; `tasks.md:702-706` (T72), `:745-749` (T80), `:750-754` (T81), `:905` (T108); `design-addendum-1-U1.md:255-263`, `:166-187` (bảng cấp); `design-w1-fixes-4.md:71-126` (phán quyết T72, không nêu giá trị stub).
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `caa555a` — `erp_ai/agent/policy.py:100-161` (`category_level_cap`, `confidence_threshold`, `is_below_confidence`, `latest_classification`), `:163-175` (`runs_today`); `erp_ai/agent/runner.py:9`, `:160-200`; `erp_ai/agent/test_agent_runner.py:60-147` (`CLASSIFY_A`, `RunnerTestBase`), mọi lớp test của file kế thừa `RunnerTestBase`; `erp_ai/agent/test_runner_status.py:35-60`, `:197-218`; `erp_ai/agent/test_runner_routing.py:59-90` (stub), `:142-160` (`RoutingTestBase(RunnerTestBase)`), `:1404-1469`; `erp_ai/tests/test_architecture.py:169-177` (`POLICY_FIELDS` không có `confidence_threshold`). Ba module dùng `RunnerTestBase`: `test_agent_runner.py`, `test_runner_routing.py`, `test_runner_status.py`. Số stub có `"dau_muc"` @ `caa555a`: `test_agent_runner.py` 1, `test_runner_routing.py` 5, `eval/test_run_eval.py` 4.
- Không đổi kiến trúc: theo ADR-030 QĐ 4 (một vị từ dưới ngưỡng `policy.is_below_confidence`, "chưa biết là dưới ngưỡng"), QĐ 3 (bảng cấp), QĐ 6 (`run_instructor`); ADR-019 (định tuyến tất định). Không đổi quy tắc nghiệp vụ. Chuẩn áp dụng: STD-TEST-6 ("Write tests that are independent and repeatable: no dependence on run order, wall-clock time or external networks."), STD-TEST-5 (không nới khẳng định). Không có `DESIGN_CONFLICT` (lý do ở Điểm 2).

---

## Điểm 1 — F-5: lần chạy không tạo phiếu trong test cần phân loại trên ngưỡng

### Hiện trạng (dữ kiện)
- Từ T80, lần chạy không tạo phiếu đọc `category, pct = policy.latest_classification(ticket_name)` (`U1.md:260`). Phiếu test (`make_ticket` trong `RunnerTestBase.setUp`) không có dòng `classify` → `(None, None)` → `is_below_confidence(None, …)` là `True` trừ khi `has_instructor ∧ act_now` (`policy.py:139-146`) → bảng cấp chỉ còn spec `ticket_write` có tên ∈ `ASK_TOOL_NAMES`; `task_write`, `change_propose`, `site_admin` đều tắt (`U1.md:173-176`).
- Phạm vi đỏ lớn hơn một test: `test_agent_runner.py` có 36 test chạy `comment_mention` (đếm bằng AST ở `caa555a`); các test gọi hoặc đòi được mời tool ghi nằm ở ít nhất `TestRunnerReasoning` (`set_resolution_hint`, `create_task`, `post_comment`, `set_classification`), `TestRunnerSiteAdminTools` (công cụ bản ghi, công cụ đề xuất), `TestRunnerRecordToolValues`, `TestRunnerPrivilegeAlarmEndToEnd`, `TestRunnerProposeLogAndInjection`. Cộng `test_runner_status.py:197-218`.
- Dựng dòng `classify` thật trong từng test không dùng được làm cách chung: `policy.runs_today` đếm mọi `run_id` của dòng `classify`/`reason` từ 00:00 (`policy.py:163-175`, `run_id=None` cũng tính) → mỗi dòng dựng sẵn ăn một lượt của `DAILY_LIMIT = 2`, làm sai các test giới hạn ngày và các test đếm `self._entries(entry_type="classify")`.
- Đầu mục của dòng dựng sẵn có hậu quả: `main_path_level` đọc `level_cap_<x>` của site dùng chung cho đầu mục ∈ `CATEGORIES` (`policy.py:103-109`); đầu mục ngoài `CATEGORIES` luôn đọc `UNKNOWN_CATEGORY_LEVEL = "L1"`, đúng bằng giá trị T80 tính khi chưa có dòng `classify` (`category=None`).
- `runner.py:9` gọi qua thuộc tính module (`from erp_ai.agent import authority, policy, site_facts`) → `patch.object(policy, "latest_classification", …)` có hiệu lực với runner.

### Phán quyết
1. **Cách:** `RunnerTestBase.setUp` (`test_agent_runner.py`) vá `policy.latest_classification` một lần cho mọi test của ba module, theo mẫu `month_spend_usd` có sẵn (`:121-124`). Hằng mới cấp module, ngay sau `DAILY_LIMIT`:
   ```python
   # A classified ticket above every threshold (pct 100 >= any 0..100 threshold); the category is outside
   # policy.CATEGORIES so main_path_level reads UNKNOWN_CATEGORY_LEVEL and no level_cap_<x> of the shared site (STD-TEST-6).
   SEEDED_CLASSIFICATION = (f"{PREFIX}category", 100)
   ```
   Trong `setUp`, ngay sau khối `month_spend_patch`:
   ```python
   # The newest classify row never comes from the shared site's live ERP AI Log rows (STD-TEST-6); a test that needs
   # the real reader sets `self.latest_classification.side_effect = self.real_latest_classification`.
   self.real_latest_classification = policy.latest_classification
   latest_patch = patch.object(policy, "latest_classification", return_value=SEEDED_CLASSIFICATION)
   self.latest_classification = latest_patch.start()
   self.addCleanup(latest_patch.stop)
   ```
   Không dựng dòng `classify` trong `setUp`. Không sửa `test_runner_status.py` (`TestRunnerStatus` kế thừa `RunnerTestBase`, nên `test_whole_turn_waits_before_its_first_tool` xanh mà không đổi dòng nào) và không sửa các test `comment_mention` có sẵn của `test_agent_runner.py`.
2. **Ngưỡng biết trước:** cũng trong `RunnerTestBase.setUp`, thêm `confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD` vào lời gọi `set_agent_settings(...)` có sẵn (`:98-107`). `confidence_threshold` không thuộc `POLICY_FIELDS` (`test_architecture.py:169-177`); `test_policy.py:681` đã viết `set_agent_settings(confidence_threshold=70)`, nên luật kiến trúc không bắt.
3. **Task:** T80 (task đầu tiên runner đọc `latest_classification` và ngưỡng; T80 sở hữu `test_agent_runner.py`). Không thêm file vào `files:` của T80.
4. **Test chứng minh dây nối thật** (vì bản vá che lời gọi thật), ba test trong `TestRunnerGrant` của T80, mỗi test một phiếu (của `setUp`):
   - `test_comment_run_reads_latest_classification_of_its_ticket`: mức L1, chạy `comment_mention` → `self.latest_classification.assert_called_once_with(self.ticket.name)`; `self.latest_classification.reset_mock()`, chạy `ticket_insert` → `self.latest_classification.assert_not_called()` (hai lần chạy: `runs_today` trước lần hai = 1 < `DAILY_LIMIT`).
   - `test_comment_run_below_threshold_from_classify_row_is_ask_only`: `self.latest_classification.side_effect = self.real_latest_classification`; một dòng `write_entry(ticket=self.ticket.name, run_id=f"{PREFIX}run-classified", entry_type="classify", trigger="ticket_insert", turn=0, predicted_category="A", predicted_confidence_pct=69)` (ngưỡng 70 của `setUp`; `runs_today` = 1 < `DAILY_LIMIT`); mức L1, không người ra lệnh, `act_now` tắt; model gọi `set_classification` rồi `post_comment` trong một lượt → kết quả `set_classification` có `ok` False và chứa `"không được cấp"`, `post_comment` có `ok` True; mọi tool `ticket_write` trong `tools` của lời gọi `reason` có tên ∈ `ASK_TOOL_NAMES`.
   - `test_comment_run_at_threshold_from_classify_row_gets_ticket_write` (biên): như trên với `predicted_confidence_pct=70` → `set_classification` `ok` True (`is_below_confidence` dùng `<`).
   Hai test có dòng thật dùng đầu mục `"A"`; `level_cap_a` của site chỉ ảnh hưởng `task_write`, mà không người ra lệnh thì `task_write` tắt bất kể mức, nên kết quả không phụ thuộc site.
5. **Test do T80 viết mới khác** (`TestRunnerGrant::test_plain_user_mention_after_instructor_gets_no_write_tools`): chạy với mặc định của `setUp` (trên ngưỡng) và khẳng định trên các nhóm cần người ra lệnh (`task_write`, `change_propose`, `site_admin`), để kết quả chứng minh luật người ra lệnh (AC-13), không phải luật ngưỡng.
6. **Test viết sau** cần lần chạy không tạo phiếu dưới ngưỡng, hoặc cần đầu mục thật trong tin nhắn đầu (T108, `U4b.md:238`), tự đặt `self.latest_classification.return_value` (hoặc `side_effect` như mục 4). Đây là luật cho người viết test, không phải lựa chọn mở.

---

## Điểm 2 — F-6: ranh giới T80/T81 cho lần chạy tạo phiếu

### Hiện trạng (dữ kiện)
- Trước T80, `ToolContext` không có `below_threshold` trong lời khởi tạo (`runner.py:183-195`), nên mặc định `False` (`U1.md:166`): mọi lần chạy hiện nay là "trên ngưỡng".
- `U1.md:261` (phạm vi T81) mới là chỗ lần chạy tạo phiếu tính lại `below_threshold` từ `classification.confidence_pct`. Nếu T80 dựng context tạo phiếu với `pct=None` qua vị từ thì lần chạy tạo phiếu thành dưới ngưỡng cả lần → `test_runner_routing.py:1441-1469` (`TestRoutingInjection::test_ticket_text_does_not_steer_route`, khẳng định `results["t_cls"]["ok"]` ở `:1469`) đỏ từ merge T80 tới merge T81.

### Phán quyết
**T80 giữ `below_threshold=False` cho lần chạy tạo phiếu; T80 và T81 là hai merge riêng** (không gộp). Ở T80, mã dựng context (bước (e), chỗ `ToolContext(...)` hiện có) có dạng:
```python
if trigger == TRIGGER_TICKET_INSERT:
	# T81 (U1.md:261) recomputes main_path_level and below_threshold from the classification, before _route.
	category, below_threshold = None, False
else:
	category, pct = policy.latest_classification(ticket_name)
	below_threshold = policy.is_below_confidence(
		pct, threshold, has_instructor=bool(instructor), act_now=switches.act_now
	)
```
rồi `ToolContext(..., main_path_level=policy.main_path_level(settings, level, category), below_threshold=below_threshold)`. Lý do chọn: giữ đúng hành vi hiện có của lần chạy tạo phiếu thêm một merge, không đổi `files:` của T80/T81, không làm T80 phình (T80 đã có 5 file và việc xóa `latest_instructor`, `preflight-w1.md:56`). Không test nào ghim giá trị chuyển tiếp này (một test như vậy sẽ phải xóa ở T81). Bằng chứng ở T80: module `test_runner_routing.py` xanh không sửa.

**Không phải `DESIGN_CONFLICT`:** ADR-030 QĐ 4 vẫn một vị từ; ở T80 lần chạy tạo phiếu chưa có kết quả phân loại để đưa vào vị từ (giống hệt trước T80). T81 xóa nhánh `TRIGGER_TICKET_INSERT` này và đưa cả hai loại lần chạy qua cùng `policy.is_below_confidence`; T82 (`depends: T81`) và mọi bản phát hành đều sau T81. Reviewer T81 kiểm: `runner.py` không còn `below_threshold = False` hay `below_threshold=False` dạng chữ.

---

## Điểm 3 — F-7: giá trị `do_tin_cay_pct` của stub và ngưỡng trong `setUp`

### Hiện trạng (dữ kiện)
- Từ T81, `_route` chỉ chạy khi `not context.below_threshold` (`U1.md:262`). Các test `test_runner_routing.py:252-270`, `:578-590`, `:694-705`, `:1469` đòi `_route` chạy. Stub phân loại (`test_runner_routing.py:59-90`, `CLASSIFY_A` ở `test_agent_runner.py:66`) nhận khóa `do_tin_cay_pct` ở T72, dòng T72 không nêu số.
- `policy.confidence_threshold` luôn trả số nguyên trong 0..100 (giá trị rác hay ngoài khoảng đọc 70, `policy.py:127-136`); `is_below_confidence(100, t, …)` là `False` với mọi `t` trong 0..100.
- `RoutingTestBase` kế thừa `RunnerTestBase` (`test_runner_routing.py:142`), nên ngưỡng đặt ở `RunnerTestBase.setUp` (Điểm 1 mục 2, T80) áp cho cả file routing mà không sửa file đó.

### Phán quyết
1. **Giá trị stub: `100`.** Mọi JSON stub có `"dau_muc"` có sẵn trong `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_routing.py`, `erp_ai/eval/test_run_eval.py` thêm `"do_tin_cay_pct": 100` ngay sau `"do_tin_cay"` (ví dụ `CLASSIFY_A = json.dumps({"dau_muc": "A", "do_tin_cay": "Cao", "do_tin_cay_pct": 100, "ly_do": "x"})`). Riêng `test_classification.py` của T72 dùng giá trị riêng của test parse (0, 100, biên).
2. **Ngưỡng trong `setUp`: có**, một chỗ, `RunnerTestBase.setUp` đặt `confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD` (Điểm 1 mục 2), ở T80. Không đặt riêng trong `RoutingTestBase`. Hai lớp bảo vệ độc lập: stub 100 không dưới ngưỡng nào; ngưỡng 70 biết trước cho test cần ca dưới ngưỡng (STD-TEST-6).
3. **Task:** giá trị stub ở T72 (T72 chưa merge: `tasks.md:702` `[ ]`, round 84 dừng; nhánh `team/FEAT-007-task-72` không có @ `caa555a`). Nếu khi áp phán quyết này T72 đã merge: chạy `git grep -n '"do_tin_cay_pct"' team/FEAT-007 -- erp_ai/agent/test_agent_runner.py erp_ai/agent/test_runner_routing.py erp_ai/eval/test_run_eval.py` (chỉ đọc).
   - (A) mọi giá trị ≥ 70 → không sửa stub; dùng dòng T81 bản A ở dưới.
   - (B) có giá trị < 70 trong `test_runner_routing.py` → dùng dòng T81 bản B (thêm file đó; T81 sửa giá trị thành 100, cùng commit với mã `_route` có điều kiện). Giá trị < 70 trong `test_agent_runner.py` → T80 sửa thành 100 (T80 sở hữu file, không đổi `files:`). `eval/test_run_eval.py` không qua runner thật nên giá trị nào trong 0..100 cũng giữ.

---

## Chuỗi chủ file (sau phán quyết)

- `erp_ai/agent/test_agent_runner.py`: T67 → T72 → T80 → T81 → T82 → … → T108. (Ghi chú: T74 không có file này trong `files:` (`tasks.md:714`); T74 ở chuỗi `runner.py`: T67 → T74 → T80 → T81 → T82.)
- `erp_ai/agent/test_runner_routing.py`: bản A: T72 → T108 → T109 → …; bản B: T72 → T81 → T108 → T109 → ….
- `erp_ai/agent/test_runner_status.py`: không task nào trong ba điểm này sửa.
- `erp_ai/eval/test_run_eval.py`: T72 (chỉ thêm khóa, giá trị 100).

---

## Dòng thay trong `tasks.md` (chép nguyên văn)

### T72 (`tasks.md:702-706`)

Tiêu đề (`:702`) giữ nguyên. Ở dòng Tiêu chí (`:703`), thay đoạn `` ba file test cuối chỉ thêm khóa `do_tin_cay_pct` vào JSON stub có sẵn. `` bằng:
```
ba file test cuối chỉ thêm `"do_tin_cay_pct": 100` ngay sau `"do_tin_cay"` vào mọi JSON stub có `"dau_muc"` có sẵn (`design-w1-fixes-8.md` Điểm 3: 100 không dưới ngưỡng nào trong 0..100, test không phụ thuộc ngưỡng của site dùng chung, STD-TEST-6).
```
Ở dòng Expect (`:706`), thay đoạn `` `test_agent_runner`, `test_runner_routing`, `eval/test_run_eval` giữ xanh. `` bằng:
```
`test_agent_runner`, `test_runner_routing`, `eval/test_run_eval` giữ xanh; mọi `"do_tin_cay_pct"` trong ba file đó bằng 100.
```

### T80 (`tasks.md:745-749`) — thay cả khối bằng:
```
- [ ] T80 — Runner dựng context từ `policy` và `run_instructor` — files: erp_ai/agent/runner.py, erp_ai/agent/authority.py, erp_ai/agent/test_authority.py, erp_ai/agent/test_agent_runner.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/test_agent_runner.py — depends: T75, T77, T72, T69
  - Tiêu chí: AC-13 (đầu-cuối), AC-22 (lần chạy không tạo phiếu); `U1.md:259-260`, `:207`; `design-w1-fixes-8.md` Điểm 1, Điểm 2, Điểm 3 mục 2. Lần chạy tạo phiếu ở T80: `category=None`, `below_threshold=False` (chuyển tiếp, T81 thay; không test nào ghim). `RunnerTestBase.setUp` vá `policy.latest_classification` trả `SEEDED_CLASSIFICATION = (f"{PREFIX}category", 100)` và đặt `confidence_threshold=policy.DEFAULT_CONFIDENCE_THRESHOLD` (STD-TEST-6); không sửa `test_runner_status.py`, `test_runner_routing.py`.
  - Receives: T66–T69, T73, T75, T76; `policy.latest_classification`, `policy.confidence_threshold`, `policy.is_below_confidence`, `policy.main_path_level`, `policy.DEFAULT_CONFIDENCE_THRESHOLD` (T69); `ASK_TOOL_NAMES` (T77).
  - Returns: `_run` bước (e) và context theo `U1.md:259-260` (lần chạy không tạo phiếu đọc `latest_classification`; lần chạy tạo phiếu `category=None`, `below_threshold=False`); xóa `authority.latest_instructor` và test `test_latest_instructor_prefers_latest_comment_then_owner` (lý do trong commit: ADR-030 QĐ 6, NFR-8); `test_agent_runner.py`: hằng `SEEDED_CLASSIFICATION`, `self.latest_classification`, `self.real_latest_classification` trong `RunnerTestBase.setUp`.
  - Expect: `TestRunnerGrant::test_plain_user_mention_after_instructor_gets_no_write_tools` (khẳng định trên `task_write`, `change_propose`, `site_admin`, với mặc định trên ngưỡng), `::test_comment_run_reads_latest_classification_of_its_ticket`, `::test_comment_run_below_threshold_from_classify_row_is_ask_only` (dòng `classify` 69, ngưỡng 70), `::test_comment_run_at_threshold_from_classify_row_gets_ticket_write` (dòng 70) xanh; `erp_ai/tests/test_architecture.py::test_authority_has_no_comment_scan_for_instructor` xanh; `erp_ai/agent/test_runner_status.py` (gồm `TestRunnerStatus::test_whole_turn_waits_before_its_first_tool`) và `erp_ai/agent/test_runner_routing.py` (gồm `TestRoutingInjection::test_ticket_text_does_not_steer_route`) xanh không sửa.
```

### T81 (`tasks.md:750-754`) — thay cả khối bằng một trong hai bản (chọn theo Điểm 3 mục 3; T72 chưa merge hoặc merge theo dòng T72 mới → bản A).

Bản A:
```
- [ ] T81 — Lần tạo phiếu: context sau phân loại, dưới ngưỡng không định tuyến — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T80
  - Tiêu chí: AC-22; `U1.md:261-262`; C-5 (`w1a.md:59`); `design-w1-fixes-8.md` Điểm 2, Điểm 3. Xóa nhánh chuyển tiếp `below_threshold=False` của T80: lần chạy tạo phiếu dựng context với `category=None, pct=None` qua cùng `policy.is_below_confidence`, rồi `dataclasses.replace` sau phân loại, trước `_route`. Ngưỡng 70 của `RunnerTestBase.setUp` (T80); stub có sẵn mang `do_tin_cay_pct` 100 (T72).
  - Receives: `Classification.confidence_pct` (T72), `is_below_confidence` (T69); `RunnerTestBase` có `confidence_threshold=70` (T80).
  - Returns: `_classify` trả `(proceed: bool, classification, context)`; `_run` dùng `context` trả về cho `_reason`; `_route` chỉ gọi khi `not context.below_threshold`; dòng `classify` ghi `predicted_confidence_pct`; `runner.py` không còn nhánh `TRIGGER_TICKET_INSERT` gán `below_threshold` thẳng.
  - Expect: `TestRunnerGrant::test_low_confidence_insert_skips_routing_writes` (stub `do_tin_cay_pct` 69, ngưỡng 70: không `apply_route`, `applied` 0, dòng `classify` có `predicted_confidence_pct` 69), `::test_insert_at_threshold_routes_and_writes` (stub 70: `_route` chạy, `predicted_confidence_pct` 70) xanh; `erp_ai/agent/test_runner_routing.py` (gồm `:252-270`, `:578-590`, `:694-705`, `TestRoutingInjection::test_ticket_text_does_not_steer_route`) và `erp_ai/agent/test_runner_status.py` xanh không sửa.
```

Bản B (chỉ khi `git grep` của Điểm 3 mục 3 thấy giá trị < 70 trong `test_runner_routing.py`):
```
- [ ] T81 — Lần tạo phiếu: context sau phân loại, dưới ngưỡng không định tuyến — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py — test: erp_ai/agent/test_agent_runner.py — depends: T80
  - Tiêu chí: AC-22; `U1.md:261-262`; C-5 (`w1a.md:59`); `design-w1-fixes-8.md` Điểm 2, Điểm 3 (bản B). Xóa nhánh chuyển tiếp `below_threshold=False` của T80: lần chạy tạo phiếu dựng context với `category=None, pct=None` qua cùng `policy.is_below_confidence`, rồi `dataclasses.replace` sau phân loại, trước `_route`. Ngưỡng 70 của `RunnerTestBase.setUp` (T80). `test_runner_routing.py`: chỉ đổi mọi `"do_tin_cay_pct"` của stub thành 100, cùng commit với mã `_route` có điều kiện; không đổi khẳng định nào. Chuỗi chủ `test_runner_routing.py`: T72 → T81 → T108.
  - Receives: `Classification.confidence_pct` (T72), `is_below_confidence` (T69); `RunnerTestBase` có `confidence_threshold=70` (T80).
  - Returns: `_classify` trả `(proceed: bool, classification, context)`; `_run` dùng `context` trả về cho `_reason`; `_route` chỉ gọi khi `not context.below_threshold`; dòng `classify` ghi `predicted_confidence_pct`; `runner.py` không còn nhánh `TRIGGER_TICKET_INSERT` gán `below_threshold` thẳng; mọi `"do_tin_cay_pct"` trong `test_runner_routing.py` bằng 100.
  - Expect: `TestRunnerGrant::test_low_confidence_insert_skips_routing_writes` (stub `do_tin_cay_pct` 69, ngưỡng 70: không `apply_route`, `applied` 0, dòng `classify` có `predicted_confidence_pct` 69), `::test_insert_at_threshold_routes_and_writes` (stub 70: `_route` chạy, `predicted_confidence_pct` 70) xanh; `erp_ai/agent/test_runner_routing.py` (gồm `:252-270`, `:578-590`, `:694-705`, `TestRoutingInjection::test_ticket_text_does_not_steer_route`) xanh, chỉ đổi giá trị stub; `erp_ai/agent/test_runner_status.py` xanh không sửa.
```

T108 (`tasks.md:905`): bản A không đổi; bản B không đổi dòng (T108 đã `depends:` T82, mà T82 `depends:` T81).

---

## Không thuộc phán quyết này
- `preflight-w1.md:56` (`latest_instructor` còn được gọi ở `test_authority.py:163`, `:203` và 20 chỗ `patch.object(authority, "latest_instructor", …)` trong `test_agent_runner.py`): không phán ở đây; dòng T80 ở trên giữ nguyên `files:` và Returns về `latest_instructor` như cũ.
- `preflight-w1.md:57` (khối lượng test `comment_mention` cần dòng `classify`): đóng bởi Điểm 1 (bản vá ở `RunnerTestBase`, không sửa từng test).
