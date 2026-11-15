# FEAT-007 — design-w1-fixes-18: phán `design-defect` của T52 (việc bot làm hôm qua, AC-51)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `review-52.md:16-19, 25-29, 35`; `design.md:436-456` (3.6.3), `design.md:465` (KPI 3); `spec.md:225-226`; `design-w1-fixes-15.md`; `tasks.md:626-643` (T52–T54); `tasks.md:1288-1292` (T166, bị kéo theo, xem Điểm 2.5); `design-addendum-1-U6b.md:82, 104-111, 227-229, 288, 295`; `design-addendum-1-U6b-fixes.md:190-196`.
- Mã đọc (chỉ đọc): mã nền `team/FEAT-007` @ `05237bb` qua `git -C .claude/worktrees/feat-007 show/grep` — `erp_ai/agent/runner.py:55-105, 296-535, 630-782`; `erp_ai/agent/run_log.py:1-139`; `erp_ai/agent/kpi.py:1-40, 150-211`; `erp_ai/agent/tools/write_ticket.py:100-140, 185-200`; `erp_ai/tasks.py:195-225`; `erp_ai/agent/test_kpi.py:135-160`; `erp_ai_log.json` (trường `ticket`, `entry_type`, `actions`, `applied`, `cost_usd`, `predicted_assignee`). Mã T52 qua `git show 22443a3:erp_ai/agent/daily_report.py` (1-200) và `git show 22443a3:erp_ai/agent/test_daily_report.py` (85-121, 453-525).
- `git diff --stat ed341b9 05237bb -- erp_ai/agent/runner.py erp_ai/agent/kpi.py erp_ai/agent/run_log.py erp_ai/tasks.py erp_ai/agent/tools` → rỗng: số dòng review trích ở `ed341b9` vẫn đúng trên `05237bb`.
- Không đổi kiến trúc: ADR-001 (`daily_report` và `kpi` cùng Lõi agent; `kpi` chỉ import `classification`, `ops_data`, `constants` — `kpi.py:13-15` — nên `daily_report → kpi` không tạo vòng), ADR-024 và A-14 (luật "bot đóng phiếu" là luật của KPI 3, `design.md:465`, mã `kpi.py:188-200`), ADR-033 QĐ 5 (một dạng mục hành động, `run_log.py:14-15`). Không quyết quy tắc nghiệp vụ mới; ba giả định kỹ thuật ở cuối.
- `team.py claim` không chạy: lời giao chỉ cho ghi đúng file này.

---

## Dò mã: mọi nơi ghi `"tool":` trên `05237bb` (ngoài test)

Lệnh: `git -C .claude/worktrees/feat-007 grep -n -E '"tool":|\btool=|action_entry\(|_route_action\(|_action\(' 05237bb -- 'erp_ai/*.py'`, bỏ `test_*`.

| Nơi ghi | Dòng ERP AI Log | Tên tool ghi ra | `ok` có thể là |
|---|---|---|---|
| `runner._route_action` (`runner.py:371-379`) | `classify` (cập nhật một lần ở `_record_route`, `runner.py:524-528`) | `apply_route` (`:494, :497, :499`), `sla_check` (`:519`), `assign_owner` (`:414, :419, :423`), `create_routed_task` (`:438, :463`; lỗi qua `_run_unit` `:394, :398`), `post_routing_comment` (`:481`; lỗi `:394, :398`) | `sla_check` luôn `False`; còn lại `True`/`False` |
| `runner._action` (`runner.py:769-782`, gọi ở `:741, :749`) | `reason` (`runner.py:656-667`) | mọi khóa của `WRITE_TOOL_TARGETS` (`runner.py:72-85`): `set_classification`, `set_resolution_hint`, `post_comment`, `create_task`, `propose_file_change`, `propose_new_file`, `propose_bench_command`, `api_create_record`, `api_update_record`, `api_delete_record`, `api_submit_record`, `api_call_method` | `True`/`False`; chỉ tool bản ghi (`RECORD_TOOLS`, `:89-91`) mang `value_before`/`value_after` (`:776-781`) |
| `run_log.action_entry` (`run_log.py:49-93`) | — | không có nơi gọi ngoài test trên mã nền (grep chỉ thấy `test_run_log.py`); U6b sẽ dùng (`design-addendum-1-U6b.md:104`) | — |
| `runner._write_propose_rows` (`runner.py:709-726`), `changes/transitions.py:124` | `change` | không ghi `actions`; mang `change_step` | — |
| Chỉ đọc: `erp_ai/tasks.py:213`, `runner.py:716`, `kpi.py:192` | — | — | — |

---

## Điểm 1 — nguồn của số "gán" (`review-52.md:16`) — SỬA

- **Phán:** "gán" = số mục `actions` có `tool == "assign_owner"` và `ok is True`, trên dòng ERP AI Log hôm qua. Bỏ hẳn `predicted_assignee` khỏi phép đếm và khỏi `fields` của truy vấn.
- **Căn cứ (dò mã):** bot chỉ gán khi `_run_unit("assign_owner", ...)` thành công rồi ghi mục `ok=True` (`runner.py:422-424`). `predicted_assignee` được ghi lúc tạo dòng `classify` (`runner.py:326`), trước khi định tuyến chạy, nên vẫn có giá trị khi phiếu đã có người (`runner.py:409-415`, mục `ok=False`), khi gán lỗi (`:422, :425`), hay khi `auto_assign` tắt (`:355`, không có mục nào). Mã T52 đếm theo `predicted_assignee` (`22443a3 daily_report.py:111-112`) nên đếm thừa ở ba ca đó, và mục `assign_owner` ok còn bị đếm lần nữa vào "khác" (`:117-118`).
- Mục `assign_owner` ok ghi `name` = người được gán, không phải phiếu (`runner.py:423`). Không ảnh hưởng phép đếm theo tên tool.

## Điểm 2 — ánh xạ tool → loại, "trả lời", "đóng" (`review-52.md:17`) — SỬA

### 2.1 Quy tắc đếm một mục (mỗi mục `ok is True` vào đúng một loại, hoặc không loại nào)
Với mỗi dòng hôm qua, với mỗi mục `action` của `kpi.log_actions(row.actions)` có `action.get("ok") is True`, xét theo thứ tự, dừng ở bước đầu tiên khớp:
1. `kpi.is_bot_close(action, row.ticket)` đúng → **"đóng"**.
2. `action.get("tool") in TOOLS_COUNTED_ELSEWHERE` → **không đếm** (đã có loại ở cột khác của dòng).
3. Còn lại → `ACTION_KIND_BY_TOOL.get(tool, OTHER_ACTION_KIND)`.

Ngoài vòng mục hành động, giữ nguyên ba phép đếm theo dòng của T52: "phân loại" += 1 khi `entry_type == "classify"` và `applied` (`22443a3 daily_report.py:109-110`, không có vế `predicted_assignee`); `change_step` ∈ {propose, approve, reject} → ba loại đề xuất (`:113-114`); `error` khác rỗng sau `strip` → "lỗi" (`:115-116`).

### 2.2 Bảng hằng (đối chiếu đủ mọi tên ở bảng dò mã)

| Tên tool (nơi ghi) | Loại | Lý do |
|---|---|---|
| `assign_owner` (`runner.py:423`) | gán | Điểm 1 |
| `create_task` (`runner.py:76`), `create_routed_task` (`runner.py:463`) | Task | cả hai tạo Task liên kết phiếu |
| `post_comment` (`runner.py:75`, `write_ticket.py:102-112`), `post_routing_comment` (`runner.py:481`) | comment | cả hai ghi `Comment` lên phiếu (`doc.new_comment`), người tạo phiếu không đọc được (`design-addendum-1-U6b.md:295`) |
| `set_classification` (`runner.py:73`) | phân loại | đổi đầu mục/nhóm/ưu tiên theo lệnh ở lượt lý luận là một lần phân loại; không trùng với dòng `classify` (khác dòng, khác lần làm) |
| `apply_route` (`runner.py:499`) | không đếm (`TOOLS_COUNTED_ELSEWHERE`) | lần ghi phiếu của chính dòng `classify` đã đếm vào "phân loại" qua `applied` (`runner.py:527`) |
| `propose_file_change`, `propose_new_file`, `propose_bench_command` (`runner.py:99`) | không đếm (`TOOLS_COUNTED_ELSEWHERE`) | mỗi mục ok đã sinh đúng một dòng `change_step="propose"` (`runner.py:715-726`), dòng đó đếm vào "đề xuất chờ duyệt" |
| mục ok bất kỳ thỏa `kpi.is_bot_close` (trên mã nền chỉ có thể là `api_update_record` HD Ticket có `value_after.status`) | đóng | Điểm 2.4 |
| `set_resolution_hint`, `api_create_record`, `api_update_record` (không đóng), `api_delete_record`, `api_submit_record`, `api_call_method`, tên lạ | khác | không thuộc loại nào của AC-51 |
| `sla_check` (`runner.py:519`) | — | luôn `ok=False`, không bao giờ được đếm |

### 2.3 "Trả lời" — có, U6b thêm tool trả lời riêng
- **Phán:** "trả lời" = mục ok của tool **`reply_to_requester`** (tool của `erp_ai/agent/tools/reply.py`, ghi Communication tới người tạo phiếu — `design-addendum-1-U6b.md:40, 104, 288`; `design-addendum-1-U6b-fixes.md:194` đã chốt `reply_to_requester` → "trả lời"). Câu hỏi để ngỏ ở `review-52.md:29` được đóng: U6b có thêm tool trả lời riêng, nên `post_comment` không bao giờ là "trả lời".
- `runner.ANSWER_TOOL = "post_comment"` (`runner.py:68-69`) chỉ là "tool mà độ trễ D-6 giữ lại" (`runner.py:647`), không phải định nghĩa "trả lời" của AC-51; không đổi.
- Trên mã nền không có nơi ghi `reply_to_requester` (grep trên `05237bb` không thấy) → "trả lời" = 0 trên dữ liệu hôm nay là **đúng thực tế**, không phải lỗi. Khóa `reply_to_requester` được thêm ở T166 (Điểm 2.5), cùng lúc với các tên U6b khác; T52 không thêm tên của tool chưa có.

### 2.4 "Đóng" — dùng luật đã có của ADR-024 / A-14
- **Phán:** "đóng" = mục ok mà `kpi.is_bot_close(action, row.ticket)` đúng, tức đúng vị từ của `kpi._bot_closed` (`kpi.py:193-198`): `action.get("ok") is True`, `action.get("doctype") == "HD Ticket"`, `action.get("name") == ticket`, `(action.get("value_after") or {}).get("status") in ("Resolved", "Closed")` (`CLOSED_STATUSES`, `kpi.py:18`), thêm `ticket` khác rỗng (dòng `bot_action` "chưa cấu hình" của U6b có `ticket` rỗng, `design-addendum-1-U6b.md:111`). Cùng định nghĩa với KPI 3 (`design.md:465`), nên báo cáo 08:00 và KPI tuần không lệch nhau.
- Không cần tên tool: các mục `resolve_on_tasks_done`, `close_silent_f` của U6b mang `value_after={"status": "Resolved"/"Closed"}` (`design-addendum-1-U6b.md:109-110`) nên tự vào "đóng" khi U6b có. Câu "U6b thêm tên tool ... đóng khi có" của `design.md:453` bỏ.
- Truy vấn của `_bot_day` thêm trường `ticket` (Link HD Ticket, có trên `erp_ai_log.json`).

### 2.5 Kéo theo: T166 (`tasks.md:1288-1292`) và `design-addendum-1-U6b-fixes.md` Sửa 7
- Sửa 7 (`U6b-fixes.md:194`) đưa `resolve_on_tasks_done`, `close_silent_f` vào loại "đổi trạng thái" và `create_kb_draft` vào "bài CSKT": hai loại này không có trong danh sách của AC-51 (`spec.md:225`), và "đổi trạng thái" đếm lại đúng những mục mà 2.4 đã đếm vào "đóng". Phán: **bỏ hai loại đó**. Dòng thay của T166 ở Điểm 4.
- `lifecycle_comment` (Comment của job vòng đời, AC-43/AC-44 "1 comment") → "comment", cùng lý do với `post_routing_comment` (Sửa 7 để nó vào "khác" mà không nêu lý do; AC-51 có loại "comment"). `requester_notice` (thông báo đóng gửi người tạo) và `create_kb_draft` → "khác".
- Văn bản thay cho `design-addendum-1-U6b-fixes.md:194` (người giữ file dán; designer không sửa file đó ở lượt này):
  > `erp_ai/agent/daily_report.py` thuộc touchpoint U6b như việc hòa nhập INT-U6b-1. Thêm đúng 2 khóa vào `ACTION_KIND_BY_TOOL`: `reply_to_requester` → "trả lời"; `lifecycle.TOOL_LIFECYCLE_COMMENT` → "comment". `resolve_on_tasks_done`, `close_silent_f` vào "đóng" qua `kpi.is_bot_close` (mục mang `value_after.status`), không có loại "đổi trạng thái". `create_kb_draft`, `requester_notice` rơi vào "khác". Không thêm loại ngoài danh sách AC-51 (`design-w1-fixes-18.md` Điểm 2.5).
- Văn bản thay cho `:196`: xem dòng Expect của T166 ở Điểm 4.

## Điểm 3 — dùng lại hàm đọc `actions` của `kpi.py` (`review-52.md:18`) — CÓ, `kpi.py` vào `files:` của T52

- **Phán:** dùng lại. `kpi._actions` (`kpi.py:203-211`) đổi tên thành hàm công khai `log_actions(raw) -> list[dict]`, thân giữ nguyên (JSON hỏng, không phải list → `[]`; bỏ phần tử không phải dict). Tách vị từ của `_bot_closed` (`kpi.py:193-198`) thành hàm công khai `is_bot_close(action: dict, ticket: str | None) -> bool` (thêm `bool(ticket)`); `_bot_closed` gọi `log_actions` và `is_bot_close`, hành vi không đổi (mọi `ticket` của `_bot_closed` đều khác rỗng vì lọc `ticket in names`). `daily_report` bỏ `_ok_actions` (`22443a3 daily_report.py:123-131`), import `from erp_ai.agent.kpi import is_bot_close, log_actions` và tự lọc `ok is True`.
- **Căn cứ:** không có nơi nào khác gọi `kpi._actions`/`kpi._bot_closed` (grep `05237bb`: chỉ `kpi.py:148, 188, 192, 203`), nên đổi tên an toàn. Không vòng import: `kpi.py:13-15`. `erp_ai/tests/test_architecture.py` chỉ nhắc `kpi`/`daily_report` trong danh sách job lịch (`:147-148, :5984-5985`), không có luật riêng cấm `daily_report → kpi` (dò grep, chưa chạy `test_layer_imports`).
- `erp_ai/tasks.py:124` (`_load_actions`, trả `None` khi hỏng để cảnh báo fail-closed của ADR-024 QĐ 1) có nghĩa khác (phân biệt "hỏng" với "rỗng"), không gộp.
- `erp_ai/agent/test_kpi.py` không sửa; đưa vào `test:` của T52 để chạy lại `TestKpi::test_kpi3_bot_only_closures` (`test_kpi.py:219`) sau khi tách hàm.

---

## Điểm 4 — dòng thay trong `tasks.md` (chép nguyên văn)

### T52 — thay dòng đầu (`tasks.md:626`)
```
- [ ] T52 — Việc bot làm hôm qua trong báo cáo 08:00 — files: erp_ai/agent/daily_report.py, erp_ai/agent/test_daily_report.py, erp_ai/agent/kpi.py — test: erp_ai/agent/test_daily_report.py, erp_ai/agent/test_kpi.py — depends: T179
```

### T52 — thay dòng Tiêu chí (`tasks.md:627`)
```
  - Tiêu chí: AC-51 (mục việc bot và chi phí; `design.md:450-453` theo `design-w1-fixes-18.md`), A-14 và ADR-024 (luật "bot đóng phiếu" dùng chung với KPI 3, `design.md:465`), STD-DESIGN-4 (dùng lại bộ đọc `actions` của `kpi`).
```

### T52 — thay dòng Receives (`tasks.md:628`)
```
  - Receives: `build_daily_report` (T51, T179: dạng phần tử và khóa theo `design-w1-fixes-15.md` Điểm 1); ERP AI Log (`ticket`, `entry_type`, `applied`, `actions`, `change_step`, `cost_usd`, `error`); `kpi._actions`, `kpi._bot_closed` (mã nền, `kpi.py:188-211`); tên tool của mã nền theo bảng dò mã của `design-w1-fixes-18.md`.
```

### T52 — thay dòng Returns (`tasks.md:629`)
```
  - Returns: `kpi.py`: `_actions` đổi tên thành `log_actions(raw) -> list[dict]` (thân giữ nguyên); thêm `is_bot_close(action: dict, ticket: str | None) -> bool` (`ok is True`, `doctype == "HD Ticket"`, `name == ticket`, `ticket` khác rỗng, `(value_after or {}).get("status") in CLOSED_STATUSES`); `_bot_closed` gọi hai hàm này, hành vi không đổi. `daily_report.py`: `ACTION_KIND_BY_TOOL = {"set_classification": "phân loại", "assign_owner": "gán", "create_task": "Task", "create_routed_task": "Task", "post_comment": "comment", "post_routing_comment": "comment"}`; `TOOLS_COUNTED_ELSEWHERE = frozenset({"apply_route", "propose_file_change", "propose_new_file", "propose_bench_command"})`; bỏ `_ok_actions`, dùng `kpi.log_actions` và lọc `ok is True`; mỗi mục ok vào đúng một loại theo thứ tự `is_bot_close(action, row.ticket)` → "đóng", tool ∈ `TOOLS_COUNTED_ELSEWHERE` → không đếm, còn lại `ACTION_KIND_BY_TOOL.get(tool, "khác")`; "phân loại" thêm 1 cho dòng `classify` có `applied`; "gán" chỉ từ `assign_owner` ok (bỏ `predicted_assignee` khỏi phép đếm và `fields`; `fields` thêm `ticket`); "trả lời" không có nơi ghi trên mã nền (T166 thêm `reply_to_requester`); khóa `bot_actions` giữ thứ tự `BOT_ACTION_KINDS`; `cost_yesterday` = `round(float(sum(...)), 6)` (ngày trống `0.0`, kiểu float).
```

### T52 — thay dòng Expect (`tasks.md:630`)
```
  - Expect: đỏ trước trên `22443a3` rồi xanh — `TestBotActions::test_assign_counted_from_ok_assign_owner_only` (ba dòng `classify` `applied=1` đều có `predicted_assignee`: [`apply_route` ok, `assign_owner` ok], [`apply_route` ok, `assign_owner` ok=False lý do "phiếu đã có người được gán"], [`apply_route` ok, `assign_owner` ok=False] → `gán` 1, `phân loại` 3, `khác` 0; đỏ: `gán` 3, `khác` 4), `::test_routing_task_and_comment_kinds` (một dòng `classify` `applied=1` có [`apply_route` ok, `sla_check` ok=False, `assign_owner` ok, `create_routed_task` ok, `post_routing_comment` ok] → `phân loại` 1, `gán` 1, `Task` 1, `comment` 1, `khác` 0; đỏ: `Task` 0, `comment` 0, `khác` 4), `::test_propose_counted_once` (dòng `reason` có [`propose_file_change` ok, `propose_new_file` ok=False] + một dòng `change` `change_step="propose"` → `đề xuất chờ duyệt` 1, `khác` 0; và `daily_report.TOOLS_COUNTED_ELSEWHERE == frozenset({"apply_route", *runner.PROPOSE_TOOLS})`; đỏ: `AttributeError` `TOOLS_COUNTED_ELSEWHERE`), `::test_close_reply_and_classification_kinds` (dòng `reason` có `ticket` = phiếu test T: `api_update_record` HD Ticket `name`=T `value_after={"status": "Closed"}` ok, cùng thế với `"Resolved"`, `name` = phiếu khác với `"Closed"`, `"status": "Open"`, `"Closed"` ok=False, `set_classification` ok, `post_comment` ok → `đóng` 2, `khác` 2, `phân loại` 1, `comment` 1, `trả lời` 0; đỏ: `đóng` 0, `khác` 5), `::test_empty_day_zero_float` (không dòng nào hôm qua → mọi loại 0, `cost_yesterday == 0.0` và `isinstance(..., float)`; đỏ: int `0`); xanh ngay là chấp nhận (test ghim, dev dán đỏ của đột biến) — `::test_unreadable_actions_and_non_classify_applied` (dòng `reason` `applied=1` không vào `phân loại`, đột biến bỏ vế `entry_type == "classify"` → đỏ; `actions` = `"{}"`, `"null"`, `[1, "x", {"tool": "create_task", "ok": "yes"}]` → 0, đột biến đổi `is True` thành truthy → đỏ); `TestBuild::test_bot_actions_and_cost_yesterday` sửa theo spec (STD-TEST-5): `ACTION_KIND_BY_TOOL` và `TOOLS_COUNTED_ELSEWHERE` bằng đúng hằng ở Returns, `gán` 0 (các dòng gieo chỉ có `predicted_assignee`, không có `assign_owner` ok), `set_priority` vẫn vào `khác`, thêm một dòng `cost_usd=0.0000004` → `cost_yesterday == 0.300001` (đúng 6 chữ số, 7 chữ số sẽ ra 0.3000014); `erp_ai/agent/test_kpi.py` xanh (`TestKpi::test_kpi3_bot_only_closures` giữ); `erp_ai/tests/test_architecture.py::TestArchitecture::test_layer_imports` xanh; test ghim `test_empty_due_field_logs_no_warning` (từ `review-179.md`) giữ xanh.
```

### T52 — dòng progress (`tasks.md:631`)
- Giữ; tech-lead nối thêm một mục "round N: design-w1-fixes-18 → dòng T52 thay" theo lệ của file.

### T53 (`tasks.md:632-637`) — không đổi
- Lý do: T53 chỉ in `bot_actions`/`cost_yesterday` từ dict; khóa và thứ tự `BOT_ACTION_KINDS` không đổi; `test_empty_day_sends_zeros` nhận `cost_yesterday` = `0.0` (float) — không cần sửa chữ của dòng nào.

### T54 (`tasks.md:638-643`) — không đổi
- Lý do: nhánh khóa bận, người nhận rỗng, cuối tuần, lỗi gửi không đọc ERP AI Log.

### T166 (`tasks.md:1288-1292`) — thay ba dòng (Điểm 2.5)
- Tiêu chí (`:1289`):
```
  - Tiêu chí: INT-U6b-1; AC-51; `design-w1-fixes-18.md` Điểm 2.3, 2.5 (thay `U6b-fixes.md` Sửa 7 `:194-196`); `design.md:453`.
```
- Receives (`:1290`):
```
  - Receives: `daily_report.ACTION_KIND_BY_TOOL`, `kpi.is_bot_close` (T52); `lifecycle.TOOL_LIFECYCLE_COMMENT`, `lifecycle.TOOL_RESOLVE_ON_TASKS_DONE`, `lifecycle.TOOL_CLOSE_SILENT_F`, `lifecycle.TOOL_REQUESTER_NOTICE` (T142); tên tool `reply_to_requester` (`design-addendum-1-U6b.md:288`).
```
- Returns (`:1291`):
```
  - Returns: đúng 2 khóa thêm vào `ACTION_KIND_BY_TOOL`: `"reply_to_requester"` → "trả lời"; `lifecycle.TOOL_LIFECYCLE_COMMENT` → "comment". Không thêm loại ngoài AC-51 (không có "đổi trạng thái", "bài CSKT"): `resolve_on_tasks_done`, `close_silent_f` vào "đóng" qua `kpi.is_bot_close`; `create_kb_draft`, `requester_notice` → "khác".
```
- Expect (`:1292`):
```
  - Expect: `TestActionKinds::test_u6b_tools_classified` đỏ trước rồi xanh: một dòng ERP AI Log hôm qua có `ticket` = phiếu test và 6 mục ok — `reply_to_requester`, `lifecycle_comment`, `resolve_on_tasks_done` (HD Ticket, `name` = phiếu, `value_after={"status": "Resolved"}`), `close_silent_f` (`value_after={"status": "Closed"}`), `requester_notice`, `create_kb_draft` → `trả lời` 1, `comment` 1, `đóng` 2, `khác` 2 (đỏ: `trả lời` 0, `comment` 0, `khác` 4); các test 08:00 có sẵn giữ xanh; `test_layer_imports` của `test_architecture` xanh.
```

---

## Điểm 5 — chữ thay trong `design.md` (tech-lead dán cùng lúc với `tasks.md`)

Số dòng theo `design.md` hiện tại (review trích lệch 1: `:451` của review = dòng `bot_actions` ở `:450`; `:454` của review = `:453`).

- `design.md:450` — thay cả dòng bảng bằng:
```
| `bot_actions` | đếm theo loại trên ERP AI Log ngày `anchor.date() − 1`: phân loại (`classify` có `applied`), đề xuất chờ duyệt/đã duyệt/bị từ chối (`change_step` propose/approve/reject), lỗi (`error` khác rỗng); mỗi mục hành động `ok` (đọc bằng `kpi.log_actions`) vào đúng một loại: đóng (`kpi.is_bot_close`, luật KPI 3), không đếm (`TOOLS_COUNTED_ELSEWHERE`), hoặc theo `ACTION_KIND_BY_TOOL` (gán, Task, comment, trả lời, phân loại), tool khác → "khác" (design-w1-fixes-18) | ERP AI Log |
```
- `design.md:451` — thay cột "Nội dung" bằng: `tổng `cost_usd` ngày hôm qua, float làm tròn 6 chữ số (ngày trống `0.0`)`.
- `design.md:453` — thay câu đầu (từ `` `ACTION_KIND_BY_TOOL` `` tới `khi có.`) bằng:
```
`ACTION_KIND_BY_TOOL` (hằng trong `daily_report.py`): `assign_owner` → gán; `create_task`, `create_routed_task` → Task; `post_comment`, `post_routing_comment` → comment; `set_classification` → phân loại; U6b thêm `reply_to_requester` → trả lời, `lifecycle_comment` → comment (T166). `TOOLS_COUNTED_ELSEWHERE` = `apply_route` và ba tool `propose_*` (đã đếm qua `applied` và dòng `propose`). "Đóng" không theo tên tool: mục ok trên chính phiếu có `value_after.status` Resolved/Closed (`kpi.is_bot_close`, cùng luật KPI 3, A-14, ADR-024). Tool khác → "khác". Bảng đối chiếu mọi nơi ghi `"tool":`: design-w1-fixes-18.
```
  Câu sau (`Phiếu không còn đầu mục biết được → nhóm "?".`) giữ.
- `design.md:465` — không đổi chữ; thêm ở cuối ô "Định nghĩa": `(vị từ: `kpi.is_bot_close`)`.

---

## Đối chiếu

- **AC-n của spec chạm ở đây:** AC-51 (mục "việc bot đã làm theo loại ... và chi phí hôm qua", `spec.md:225`). AC-52 (`spec.md:226`) không đổi phép đếm (ngày trống số 0 → `test_empty_day_zero_float` ở T52, `test_empty_day_sends_zeros` ở T53).
- **Danh sách loại AC-51 ↔ test:** phân loại → `test_assign_counted_from_ok_assign_owner_only`, `test_routing_task_and_comment_kinds`, `test_close_reply_and_classification_kinds`, `test_unreadable_actions_and_non_classify_applied`; gán → `test_assign_counted_from_ok_assign_owner_only`, `test_routing_task_and_comment_kinds`; Task, comment → `test_routing_task_and_comment_kinds`, `test_close_reply_and_classification_kinds`; trả lời → `test_close_reply_and_classification_kinds` (0 trên mã nền), `test_u6b_tools_classified` (T166); đóng → `test_close_reply_and_classification_kinds`, `test_u6b_tools_classified`; đề xuất chờ duyệt/đã duyệt/bị từ chối, lỗi → `test_bot_actions_and_cost_yesterday`, `test_propose_counted_once`; chi phí → `test_bot_actions_and_cost_yesterday`, `test_empty_day_zero_float`. Đủ 10/10 loại + chi phí.
- **Touchpoint:** sửa `erp_ai/agent/daily_report.py`, `erp_ai/agent/test_daily_report.py`, `erp_ai/agent/kpi.py` (có sẵn); chỉ chạy `erp_ai/agent/test_kpi.py`. File mới: 0. So `protected_paths` (`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`) và `allowed_new_file_roots` (`erp_ai`, `docs`, `.github`): ba file dưới `erp_ai/`, không khớp mẫu bảo vệ nào; file này dưới `docs/`.
- **Hợp đồng:** chỉ thêm (`kpi.log_actions`, `kpi.is_bot_close`, `daily_report.TOOLS_COUNTED_ELSEWHERE`, khóa trong `ACTION_KIND_BY_TOOL`); `kpi._actions` là hàm riêng không ai ngoài `kpi` gọi. Khóa của dict `build_daily_report` không đổi. Không migration, không đổi DocType.

## Giả định kỹ thuật designer đã quyết
1. `set_classification` ok ở lượt lý luận → "phân loại" (là một lần phân loại; mặc định khác là "khác" bị loại vì AC-51 có loại này).
2. `lifecycle_comment` → "comment", `requester_notice` → "khác" (thông báo, không phải trả lời); thay Sửa 7 của U6b-fixes ở hai chỗ "đổi trạng thái", "bài CSKT" vì không có trong AC-51.
3. "Đóng" đếm theo mục (một phiếu Resolved rồi Closed trong ngày = 2), cùng đơn vị "việc bot làm" với các loại khác; KPI 3 đếm theo phiếu là việc của KPI.

## Đã dò mã / chưa chạy
- Đã dò mã (đọc, grep trên `05237bb` và `22443a3`): mọi nơi ghi `"tool":`; nguồn `predicted_assignee` và `applied`; `ANSWER_TOOL`; `post_comment` ghi Comment; `kpi._actions`/`_bot_closed` và nơi gọi; trường `ticket`, `cost_usd` (Float, `precision` 6) của ERP AI Log; tên tool U6b trong thiết kế (chưa có trong mã: grep `reply_to_requester` trên `05237bb` rỗng).
- Chưa chạy: không test nào (kể cả các dòng "đỏ trước" ở Điểm 4 — đó là dự đoán từ mã `22443a3`, dev phải dán đỏ thật); không chạy `test_layer_imports` cho `daily_report → kpi`; không kiểm `creation` của ERP AI Log có cùng giờ site với `anchor` (`review-52.md:28`) và cột DB của `cost_usd` có giữ đủ 7 chữ số khi `db_insert` để ca 0.0000004 có nghĩa (`review-52.md:27`) — dev xác nhận khi chạy ca đó (nếu cột làm tròn khi ghi, đổi giá trị gieo sao cho tổng thô có chữ số thứ 7 khác 0 trong giới hạn cột).
- Không `DESIGN_CONFLICT`: không AC nào cần phá ADR. Không câu hỏi nghiệp vụ.
