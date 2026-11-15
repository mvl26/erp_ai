Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). Vòng sửa 1/3 của U6b. -->

# Design addendum 1 — U6b, bản sửa theo rà soát kiến trúc (FEAT-007)

**Thứ bậc.** File này **thắng** `design-addendum-1-U6b.md` ở mọi chỗ khác nhau. Mỗi sửa ghi dòng của addendum bị thay và văn bản thay đầy đủ. Dòng nào của addendum không bị sửa ở đây thì giữ nguyên.

**Đầu vào đã đọc (theo thứ tự):** `arch-review-design-w1b.md` (request-changes: X-1..X-3, 6 minor, phán quyết (1b), (3a)–(3e), mục 5); `design-addendum-1-U6b.md` (479 dòng); `arch-review-design-w1a.md` phán quyết (2), (3); `ADR-033.md` QĐ 2, 4, 6 và Ràng buộc.

**Quyết định của team-leader áp dụng** (`docs/team/journal/FEAT-007.md:25`):
- (a) Quyền đọc HD Article cho `ERP AI Instructor` cài ở task T22a của đợt 0. U6b **không** sửa `install.py`. Điều kiện của w1a vẫn giữ: chép DocPerm chuẩn bằng `setup_custom_perms("HD Article")` trước khi thêm dòng.
- (b) Hằng `RUN_LIMIT_TRIGGERS` và bộ lọc trong `policy.runs_today` là của U1 (w1a C-3). Commit của U6b chỉ **nối** `requester_reply` vào hằng đó, **không bao giờ** nối `kb_draft`.

**Luật thi hành (trích):** ADR-033 QĐ 2 ("khóa = tên Communication"), QĐ 4, QĐ 6 ("việc theo sự kiện dùng tên sự kiện làm khóa; chạy lại → 0 tác động thêm") và Ràng buộc ("chạy hai lần cùng thời điểm giả lập", "lỗi giữa chừng"); ADR-034 QĐ 1, Ràng buộc 1–2; ADR-030 QĐ 3; ADR-003/ADR-013 QĐ 2. STD-short đã đọc lại, trích: "STD-DESIGN-1 (2) Edit only within the task's touchpoints; if an edit outside them is needed, stop and report `DESIGN_CONFLICT`."

## 0. Căn cứ đọc trực tiếp (2026-11-14, `develop` @ `431bf55`; đích đã biết nên không gọi Explore)

| Chỗ | Thấy | Dùng ở |
|---|---|---|
| `erp_ai/agent/queue.py:3`, `:14` | `queue` import `TRIGGER_TICKET_INSERT`, `TRIGGER_COMMENT_MENTION` từ `erp_ai/constants.py`; `queue` không import `runner` | Sửa 1, 3 |
| `erp_ai/constants.py:36-38` | `TRIGGER_TICKET_INSERT`, `TRIGGER_COMMENT_MENTION`, `TRIGGER_CHANGE_ACTION` | Sửa 3 |
| `erp_ai/agent/policy.py:80-92` | `runs_today` đếm `run_id` khác nhau của dòng `classify`/`reason`, chưa lọc trigger (U1 thêm theo C-3) | Sửa 1, 3 |
| `erp_ai_log.json` | `run_id` là `Data`, `search_index = 1`; `trigger` là Select 3 giá trị | Sửa 1 |
| `erp_ai/agent/runner.py:139` | `run_id = uuid.uuid4().hex` là chỗ sinh `run_id` duy nhất trong `erp_ai/**` (grep `uuid`, `len(run_id`: không mã nào giả định dạng hex) | Sửa 1 |
| Helpdesk `hd_ticket.py:668-800` | `reply_via_agent` không gọi `frappe.db.commit` (grep 0). Khi `instantly_send_email()` đúng thì gọi `frappe.sendmail(now=True)` (`:769-786`), tức gửi SMTP ngay | Sửa 2 |
| Frappe `background_jobs.py:577-578` (theo w1b) | `deduplicate` bỏ lời xếp hàng khi job **cùng id** đang `QUEUED` hoặc `STARTED` | Sửa 1 |
| `erp_ai/agent/tools/read.py:115`, `:132` | `search_resolved_tickets` lọc `status_category = Resolved`, rồi lọc từng dòng bằng `can_send_ticket` sau truy vấn | Sửa 6 |
| `design.md:453` | `ACTION_KIND_BY_TOOL`: tool không có trong bảng → "khác" | Sửa 7 |
| `design-addendum-1-U4b-U8.md:134-140`, `:236-252` | `NOTICE_PREFIXES` 4 khóa; thông báo `daily_limit`, `over_budget`, `run_failed`, `ask_fallback` do runner đăng | Sửa 9, 10 |
| `design-addendum-1-U2.md:118-119`, `:134`, `:189` | `ticket_content_filters("HD Ticket")` → `([["name", "not in", names]], [])` hoặc `([], [])`; U6b là người dùng | Sửa 6 |
| `design-addendum-1-U1.md:158`, `:179` | `ASK_TOOL_NAMES = {"post_comment"}`; `grant` bước (3) cộng spec `ticket_write` có tên trong `ASK_TOOL_NAMES` khi dưới ngưỡng | Sửa 12 |

---

## 1. Các sửa

### Sửa 1 — X-1: khóa chống trùng của lần chạy "người tạo trả lời" theo tên Communication

**Thay:** addendum `:133` (gạch đầu dòng `enqueue_agent_run`); `:276` (hàng `communication_on_update`); `:279` (đoạn **B-2**); `:283-284` (gạch `run_for_ticket` và phần `requester_reply` của "Bước sau (c)"); `:293` (chữ của `TASK_REQUESTER_REPLY`); `:367` (danh sách lý do `skip`); `:473` (A-U6b-4); các hàng test `:429`, `:430`.

**Văn bản thay (3.1 `queue.py`, thêm vào chữ ký):**

```python
def requester_reply_key(ticket_name: str, communication_name: str) -> str
    # f"{TRIGGER_REQUESTER_REPLY}:{ticket_name}:{communication_name}"
```

- `enqueue_agent_run(ticket_name, trigger, comment_name=None, communication_name=None)`: kiểm biên như cũ (`requester_reply` mà `communication_name` không phải chuỗi khác rỗng → `ValueError`; `communication_name` có giá trị với trigger khác → `ValueError`). **`job_id`:** trigger `requester_reply` → `f"erp_ai::{ticket_name}::{trigger}::{communication_name}"`; trigger khác giữ `f"erp_ai::{ticket_name}::{trigger}"`. Vẫn `deduplicate=True` và `_claim_pending(job_id)`.
- Hệ quả: tin M2 đến lúc job của M1 đang `QUEUED`/`STARTED` có `job_id` khác, nên Frappe không bỏ nó (Frappe chỉ so cùng id, `background_jobs.py:577-578`). Hai lần `on_update` của **cùng** một Communication có cùng `job_id`, nên lần hai bị bỏ: cùng giao dịch thì `_claim_pending` trả `False`, khác giao dịch khi job còn chờ hoặc đang chạy thì `deduplicate` bỏ.
- Có tên phiếu trong khóa vì **B-3**: dòng `skip event_moved` ghi dưới khóa của phiếu cũ thì không được làm sự kiện bị coi là "đã xử lý" ở phiếu đích.

**"Đã xử lý" lưu ở đâu (ADR-033 QĐ 2, 6).** Với trigger `requester_reply`, runner đặt `run_id = queue.requester_reply_key(ticket_name, communication_name)` thay cho `uuid4().hex`. Mọi dòng ERP AI Log của lần chạy đó (`reason` mỗi lượt, `skip`) mang `run_id` này. `run_log.write_entry` insert rồi commit dòng trong cùng lời gọi, cùng giao dịch với tác động của lượt, nên **khóa sự kiện được lưu trong cùng giao dịch với dòng của lần chạy**. Tra cứu dùng chỉ mục có sẵn của `run_id`. `runs_today` đếm `run_id` khác nhau nên một lần chạy vẫn đếm 1. Trigger khác giữ `uuid4().hex`. Runner import `queue`; `queue` không import `runner` nên không có vòng (STD-DESIGN-6).

**3.7, hàng `communication_on_update` (thay `:276`):**

| Handler | Lọc rẻ (không đọc DB) | Lọc có đọc DB → lý do `_log_decision` | Xếp hàng |
|---|---|---|---|
| `communication_on_update` | `reference_doctype != "HD Ticket"` hoặc `sent_or_received != "Received"` hoặc `communication_type != "Communication"` → về | theo thứ tự: `not policy.is_enabled()` → `agent_disabled`; `owner == AGENT_USER` → `written_by_agent`; `not lifecycle.is_requester_sender(doc.sender, raised_by)` → `not_requester`; **B-1:** không có Communication `Sent`, `owner = AGENT_USER` của phiếu với `creation < doc.creation` → `no_bot_message_before`; có dòng ERP AI Log `run_id = requester_reply_key(doc.reference_name, doc.name)` → `already_handled`; `not can_send_ticket(ticket)` → `not_sendable` | `enqueue_agent_run(doc.reference_name, TRIGGER_REQUESTER_REPLY, communication_name=doc.name)` (đọc `reference_name` lúc `on_update`, **B-3**) |

`lifecycle.is_requester_sender(sender, raised_by) -> bool` (mới, công khai) so `extract_email_id(...)` hai bên sau `casefold` (A-U6b-9). Ba chỗ dùng cùng hàm này: handler, `silent_since`, bước `superseded` của runner. `lifecycle.newer_requester_message_exists(ticket_name, communication_name) -> bool` (mới): có Communication khác gắn phiếu đó, `Received`, `communication_type = "Communication"`, `is_requester_sender` đúng, và `(creation, name)` lớn hơn của Communication đã cho.

**3.7, đoạn B-2 (thay `:279`):** Hai lần `on_update` của một thư trong cùng giao dịch: `_claim_pending` trả `False` ở lần hai. Khác giao dịch khi job còn `QUEUED`/`STARTED`: `deduplicate` của Frappe bỏ (cùng `job_id`). Sau khi job đã chạy: handler thấy khóa trong ERP AI Log → `already_handled`, không xếp; nếu vẫn lọt (đua giữa handler và job) thì runner (r1) dừng. Handler không ghi gì, không đổi trạng thái, không import Cổng model.

**3.8 runner (thay `:283-284`, phần `requester_reply`):**
- `run_for_ticket(ticket_name, trigger, comment_name=None, communication_name=None)` → `_run(...)`. `run_id` như trên.
- Với `requester_reply`, các bước sau chạy **trước** bước (c), theo thứ tự:
  - (r1) `frappe.db.exists(LOG_DOCTYPE, {"run_id": run_id})` → một dòng `frappe.logger(LOGGER_NAME).info("erp_ai skip ticket=%s run_id=%s reason=already_handled")`, **không ghi dòng nào**, 0 lời gọi model, dừng. Chạy lại cho 0 tác động thêm, kể cả 0 dòng nhật ký (ADR-033 QĐ 6).
- Bước (c) `not_sendable` như hiện nay (dòng `skip` mang `run_id` = khóa).
- Sau (c), `_requester_reply_skip(ticket, communication_name) -> str | None`:
  - (r2) Communication không có → `"event_missing"`.
  - (r3) `reference_name ≠ ticket` (đọc lại từ DB, **B-3**) → `"event_moved"`.
  - (r4) `lifecycle.newer_requester_message_exists(ticket, communication_name)` → `"superseded"`. Job của tin mới hơn đã được handler của nó xếp hàng; nó bắt đầu sau cả hai tin nên đọc cả hai.
- Có lý do → `_log_skip(..., run_id)`, dừng. Dòng `skip` không đếm vào `runs_today`.
- Rồi tới bước (d), giới hạn ngày (được đếm): `_log_skip("daily_limit")` cùng thông báo của U4b. Phần `kb_draft` của `:284` giữ nguyên.

**Luật gộp (thay A-U6b-4, `:473`):** hai tin của người tạo chỉ gộp vào một lần chạy khi lần chạy đó **bắt đầu sau cả hai tin**. Job M1 bắt đầu khi M2 đã có thì M1 dừng `superseded`, còn job M2 chạy và đọc cả hai. M2 đến sau khi job M1 đã bắt đầu thì M2 có job riêng và lần chạy riêng. Mọi tin đạt lọc của handler đều có một lần chạy bắt đầu sau nó, hoặc một dòng `skip` có lý do. Chỉ có một ngoại lệ: worker sập trước khi ghi dòng nào. Khi đó khóa chưa được lưu, nên lần `on_update` sau của chính thư đó sẽ chạy lại (ít nhất một lần, không mất).

| Ca | Addendum gốc | Sau Sửa 1 |
|---|---|---|
| M2 đến khi job M1 `STARTED` | bị `deduplicate` bỏ → M2 mất | `job_id` riêng → M2 có 1 lần chạy |
| M2 đến giữa lúc model đọc phiếu và lúc ghi dòng | `already_handled` (so `creation` dòng ≥ M2) → mất | khóa đúng tên M2 chưa có → M2 chạy |
| M1, M2 cùng có trước khi job nào bắt đầu | 1 lần chạy | M1 `superseded` (không đếm), M2 1 lần chạy → 1 lần gọi model |
| `on_update` hai lần, cùng giao dịch / job còn chờ | 1 | 1 |
| `on_update` lại sau khi job đã chạy | dòng `skip already_handled` | handler `already_handled`, 0 job; lọt tới runner → 0 dòng |
| Phiếu gộp (B-3) | `event_moved` | `event_moved` dưới khóa phiếu cũ; khóa phiếu đích khác → chạy được |

**3.9 `TASK_REQUESTER_REPLY` (thay chữ ở `:293`):** "Người tạo phiếu vừa trả lời tin của bạn, có thể bằng nhiều tin. Đọc mọi tin của người tạo sau tin gần nhất của bạn. Trả lời người tạo bằng reply_to_requester nếu được cấp, hoặc ghi comment cho người phụ trách."

**Quan sát (thay phần lý do `skip` ở `:367`):** lý do `skip` mới: `event_missing`, `event_moved`, `superseded`, `kb_exists`, `no_resolution_content`, `not_closed`, `kb_draft_off`. `already_handled` chỉ có ở `_log_decision` của handler và một dòng logger của runner, không có dòng ERP AI Log.

**Test (thay `:429`, `:430`; thêm bốn test cho X-1):**

| Test | Ca |
|---|---|
| `erp_ai/agent/test_queue.py::TestEnqueueAgentRun::test_requester_reply_job_id_per_communication` | M1, M2 cùng phiếu → 2 `job_id` khác nhau, mỗi `job_id` chứa tên Communication; trigger khác giữ `erp_ai::{t}::{trigger}` |
| `erp_ai/tests/test_handlers.py::TestRequesterReply::test_reply_while_previous_job_started_gets_own_job` (**X-1, bắt buộc**) | patch `erp_ai.agent.queue.frappe.enqueue` bằng hàm giả theo đúng luật `background_jobs.py:577-578` (bỏ lời xếp khi `job_id` ∈ tập `QUEUED`/`STARTED`); đặt `job_id` của M1 là `STARTED`; tạo M2 → hàm giả nhận đúng 1 job của M2; rồi `run_for_ticket(t, "requester_reply", communication_name=M2)` với model stub → đúng 1 lần chạy (1 lần gọi model, các dòng có `run_id = requester_reply_key(t, M2)`) |
| `::test_on_update_twice_one_job` (giữ) | insert rồi `save()` trong cùng giao dịch → 1 lời `frappe.enqueue` |
| `::test_on_update_after_run_no_job` | có dòng ERP AI Log với khóa của M1 → 0 job, `_log_decision` lý do `already_handled` |
| `::test_merged_ticket_uses_final_reference` (giữ) | job xếp theo phiếu đích |
| `erp_ai/agent/test_agent_runner.py::TestRequesterReplyRun::test_message_during_run_not_lost` (**X-1 (ii)**) | model stub của lần chạy M1 tạo M2 trong lúc chạy → sau M1, job M2 chạy, không `already_handled`; tổng 2 lần gọi model |
| `::test_both_messages_before_start_one_model_run` | M1, M2 có trước; job M1 → dòng `skip superseded`, 0 lần gọi model; job M2 → 1 lần chạy; tổng 1 lần gọi model; `runs_today` = 1 |
| `::test_second_event_after_run_already_handled` (thay ca cũ) | M1 đã chạy; gọi lại job M1 → 0 lần gọi model, số dòng ERP AI Log trước = sau, 1 dòng logger `already_handled` |
| `::test_event_moved_skipped` (giữ), `::test_moved_event_runs_on_new_ticket` (mới) | job phiếu cũ → `event_moved`; job phiếu đích sau đó → 1 lần chạy |

---

### Sửa 2 — X-3: hai test ADR-033 bắt buộc cho việc đóng F im lặng; rollback theo savepoint

**Thay:** addendum `:259` (câu "Lỗi bất kỳ ở (4)–(8) → `frappe.db.rollback()`…"), `:260` (bước (5)–(8) và câu "Lỗi một phiếu → rollback…"). Bước (4) của `:260` sửa ở Sửa 15. Thêm hàng test vào sau `:437` và `:439`.

**Văn bản thay (3.6):**
- **Khóa chu kỳ của việc đóng F** là chính tác động: phiếu sang `Closed` (nhóm `Resolved`). Tác động này được ghi trong cùng giao dịch với thông báo (Communication + Email Queue), comment và dòng `bot_action`. Chỉ `write_bot_action`, gọi cuối cùng, là commit (U3 hợp đồng `:147`). `reply_via_agent`, `doc.save()` và `new_comment` không commit (`hd_ticket.py:668-800`: 0 `commit`). Lần quét sau thấy `Resolved` ở bước (5), nên bỏ qua.
- `scan_silent_f_tickets`, mỗi phiếu: `frappe.db.savepoint("erp_ai_silent_close")` → (5) khóa dòng, các chốt bỏ qua như cũ → (6) `send_to_requester(t, NOTICE_SILENT_CLOSE)`. Lỗi ở (6): `frappe.db.rollback(save_point="erp_ai_silent_close")`, rồi `write_bot_action` một mục `requester_notice` `ok=False` có lý do, **không đóng**; lần quét sau thử lại. → (7) `doc.flags.erp_ai_silent_close = True`, `status = Closed`, `save()`, comment → (8) `write_bot_action` 3 mục (commit). Lỗi ở (7)–(8): `frappe.db.rollback(save_point="erp_ai_silent_close")` (gỡ cả Communication, Email Queue, trạng thái, comment), `frappe.log_error(TITLE_LIFECYCLE_FAILED, f"ticket={t} error={type(exc).__name__}")`, sang phiếu kế.
- `run_task_lifecycle`: bước (4)–(8) nằm trong `frappe.db.savepoint("erp_ai_lifecycle")`. Lỗi → `frappe.db.rollback(save_point="erp_ai_lifecycle")`, `log_error` như trên, job kết thúc bình thường. Dùng savepoint thay cho `frappe.db.rollback()` toàn phần vì hai lý do: lỗi ở một phiếu không xóa việc đã commit của phiếu khác, và test chạy được trong giao dịch của test runner (STD-TEST-6).
- **Rủi ro còn lại (ghi As-Built):** khi Helpdesk bật gửi ngay (`instantly_send_email()` đúng), `frappe.sendmail(now=True)` gửi SMTP ở bước (6). Lỗi ở (7)–(8) thì rollback không thu hồi được thư đã gửi, nên lần quét sau gửi thông báo lần hai. Tối đa một thư thừa cho mỗi lần lỗi. Kiểm R-1 U-1..U-7 trước khi bật `close_silent_f_enabled`.

**Test (thêm; X-3):**

| Test | Ca |
|---|---|
| `erp_ai/agent/test_lifecycle.py::TestSilentClose::test_two_runs_same_now_one_close` | phiếu F, bot `Sent` ngày 0; `now` = ngày 3 + 1 giờ; `scan_silent_f_tickets(now)` hai lần. Sau lần 1: 1 Communication thông báo, 1 Email Queue, 1 Comment `COMMENT_SILENT_CLOSED`, 1 dòng `bot_action`, `status = Closed`. Sau lần 2: cả bốn số đếm **không đổi** (0 email, 0 comment, 0 dòng thêm) |
| `::test_failure_after_notice_rolls_back_then_once` | patch `save` của HD Ticket ném lỗi ở lần lưu đổi trạng thái (bước (7)), một lần. Sau lần quét 1: 0 Communication mới, 0 Email Queue mới, `status` không đổi, 0 dòng ERP AI Log, 1 Error Log `TITLE_LIFECYCLE_FAILED`. Bỏ patch, quét lại cùng `now`: đúng 1 thông báo, 1 comment, 1 dòng, `Closed`. Nếu `reply_via_agent` tự commit thì rollback về savepoint sẽ hỏng và test đỏ, nên test này cũng xác nhận `reply_via_agent` không tự commit |
| `::test_failure_on_one_ticket_others_closed` | 2 phiếu đủ điều kiện, phiếu đầu lỗi ở (7) → phiếu sau vẫn đóng, có 1 dòng |
| `::TestResolveOnTasksDone::test_failure_midway_rolls_back_then_once` | patch `new_comment` ném lỗi một lần → `status` không đổi, 0 dòng; gọi lại → `Resolved` đúng một lần, 1 comment, 1 dòng |
| `::test_notice_failure_not_closed` (giữ) | lỗi ở (6) → không đóng, 1 mục `requester_notice ok=False` |

---

### Sửa 3 — X-2, phán quyết (3e), quyết định (b), w1a phán quyết (2): `RUN_LIMIT_TRIGGERS` và chỗ đặt hai trigger mới

**Thay:** addendum `:79` (hàng `runs_today` của 1.4), `:122-124` (khai báo trigger), `:132` (lý do đặt ở `queue.py`), `:320` (hàng hợp đồng), `:404` (dòng "Không có"), `:470` (A-U6b-1), hàng test `:442` (phần "cần mục 1.4 U1").

**Văn bản thay:**
- **Chủ:** U1 sở hữu hằng `RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)` ở `policy.py` và bộ lọc `trigger in RUN_LIMIT_TRIGGERS` trong `runs_today` (w1a C-3, quyết định (b)). U6b không viết bộ lọc.
- **Hai trigger mới ở `erp_ai/constants.py`** (cạnh `:36-38`): `TRIGGER_REQUESTER_REPLY = "requester_reply"`, `TRIGGER_KB_DRAFT = "kb_draft"`. `queue.py` import từ đó như hai trigger cũ (`queue.py:3`); `policy.py` import `TRIGGER_REQUESTER_REPLY` từ `constants`, nên không lập vòng `policy → queue` (w1a (2)). `queue.VALID_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_KB_DRAFT)`.
- **`policy.py`, đúng một chỗ sửa:** thêm `TRIGGER_REQUESTER_REPLY` vào dòng import từ `erp_ai.constants` và vào `RUN_LIMIT_TRIGGERS`. Kết quả: `RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY)`. Không có `TRIGGER_KB_DRAFT`.
- **Một commit** (gọi là commit trigger của U6b) chứa đủ: `constants.py` (2 hằng), `queue.VALID_TRIGGERS`, `run_log.TRIGGERS` (Sửa 4), option và mô tả `trigger` trong `erp_ai_log.json` (Sửa 4), cụm từ mô tả, `policy.RUN_LIMIT_TRIGGERS` (+ `requester_reply`), luật kiến trúc đổi (dưới đây), các test của sửa này. Commit nào thiếu một phần thì luật tập hợp đỏ (w1a mục 5, ý 1).
- **Điều kiện bắt đầu:** U1 đã merge `RUN_LIMIT_TRIGGERS` và bộ lọc. Thiếu → `DESIGN_CONFLICT`, dừng. Không có nhánh dự phòng trong U6b.
- **Hợp đồng (thay `:320`):** `TRIGGER_REQUESTER_REPLY`, `TRIGGER_KB_DRAFT` | `"requester_reply"`, `"kb_draft"` | `erp_ai/constants.py` | `policy.RUN_LIMIT_TRIGGERS` (import), `queue`, `run_log`, U5a báo cáo.

**Test:**

| Test | Ca |
|---|---|
| `erp_ai/agent/test_policy.py::TestRunsToday::test_kb_draft_reason_row_not_counted` (**X-2**) | một dòng `reason`, `trigger = kb_draft`, hôm nay → `runs_today` không tăng |
| `::test_requester_reply_reason_row_counted` (**X-2**) | một dòng `reason`, `trigger = requester_reply` → `runs_today` tăng đúng 1; hai lượt cùng `run_id` → vẫn 1; một dòng `skip superseded` → +0 |
| `erp_ai/tests/test_architecture.py::test_run_limit_triggers_subset_of_log_triggers` (sửa test của U1, C-3) | luật đổi thành `set(run_log.TRIGGERS) - set(policy.RUN_LIMIT_TRIGGERS) == {TRIGGER_KB_DRAFT}` (w1a (2)). Lý do sửa test: AC-41, AC-45 thêm trigger (NFR-8, STD-TEST-5) |
| `erp_ai/agent/test_agent_runner.py::TestKbDraftRun::test_not_counted_in_daily_limit` (giữ, bỏ chữ "cần mục 1.4 U1") | `runs_today` = giới hạn → lần chạy `kb_draft` vẫn chạy |

---

### Sửa 4 — phán quyết (3a): `run_log.py`, `erp_ai_log.json` vào touchpoint, sau U3

**Thay:** addendum `:388-389` (cột "Trong ô arch-impact?") và tiêu đề `:312`. Nội dung `:314` giữ nguyên.

**Văn bản thay:** `erp_ai/agent/run_log.py` và `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` thuộc touchpoint U6b **theo phán quyết (3a)** (D-5/F-5). Thứ tự: sửa sau khi U3 merge, vì U3 sửa cùng hai file (`BOT_ACTION_TRIGGERS`, `ENTRY_TYPES`). Nằm trong commit trigger của Sửa 3. `run_log.TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply", "kb_draft")`; hai giá trị cuối là hằng import từ `constants`, nếu U3 đã đổi `TRIGGERS` sang dùng hằng. Option JSON `trigger` = `TRIGGERS + CHANGE_TRIGGERS + BOT_ACTION_TRIGGERS`. `BOT_ACTION_TRIGGERS` không đổi.

**Test:** `erp_ai/agent/test_run_log.py::TestTriggers::test_triggers_match_queue_and_json` (giữ) và `erp_ai/tests/test_architecture.py::test_log_trigger_options_match_run_log` (của U3) xanh sau commit trigger.

---

### Sửa 5 — phán quyết (3b): `tests/test_architecture.py`, 6 đích enqueue

**Thay:** addendum `:391` (cột "Trong ô arch-impact?") và hàng test `:452`.

**Văn bản thay:** `erp_ai/tests/test_architecture.py` thuộc touchpoint U6b **theo phán quyết (3b)** (ADR-003, ADR-013 QĐ 2, F-2). `ENQUEUE_TARGETS` = 5 đích của U5a + `"erp_ai.agent.lifecycle.run_task_lifecycle"` = 6 đích. Thay đổi nằm trong cùng commit với `queue.enqueue_lifecycle_job`. `enqueue_agent_run` vẫn là một lời gọi cho mọi trigger, kể cả hai trigger mới ("mỗi đích một lời gọi"). Cùng file còn có luật của Sửa 3 và Sửa 13.

**Test:** `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_enqueue_targets_pinned` ghim tuple 6 đích; `check_enqueue_call_shape` xanh.

---

### Sửa 6 — phán quyết (3c) và minor (e): `tools/read.py` dùng dạng truy vấn của U2

**Thay:** addendum `:81` (hàng U2 của 1.4), `:301` (gạch "Lọc phiếu loại trừ"), `:390` (cột "Trong ô arch-impact?"), hàng test `:447` (thêm ca).

**Văn bản thay:**
- `erp_ai/agent/tools/read.py` thuộc touchpoint U6b **theo phán quyết (3c)** (bảng module `arch-impact.md:62` "tool đọc mới"). Chỉ sửa `search_resolved_tickets` (AC-48).
- **Điều kiện bắt đầu:** U2 đã merge (dòng Đợt `arch-impact.md:185`; N-2 của w1a). Nhánh "nếu U2 chưa có" bỏ.
- Lọc phiếu loại trừ **trong truy vấn**, trước khi quét và cắt `limit`: `extra, ticket_or = policy.ticket_content_filters("HD Ticket")`. Theo hợp đồng U2 (`design-addendum-1-U2.md:134`), `ticket_or` luôn là `[]` với HD Ticket; khác `[]` thì ném `ValueError` (hợp đồng bị đổi, fail-closed; `execute_tool` bắt như nay). Truy vấn: `frappe.get_all("HD Ticket", filters=[["status_category", "=", "Resolved"], *extra], or_filters=<LIKE từng từ>, limit_page_length=SEARCH_SCAN_MAX, ...)`. Phiếu loại trừ không chiếm chỗ trong `SEARCH_SCAN_MAX` và không ảnh hưởng thứ tự (ADR-034 QĐ 1, Ràng buộc 1–2).
- Bỏ lọc từng dòng bằng `can_send_ticket` sau truy vấn (`read.py:132`). Dạng truy vấn là đúng vị từ đó (A-U2-1), nên chỉ còn một đường lọc.

**Test (thêm):** `erp_ai/agent/tools/test_read.py::TestSearchResolvedTickets::test_excluded_match_does_not_change_result_count`: 3 phiếu thường khớp, `limit` 3 → 3 kết quả. Thêm 1 phiếu loại trừ khớp nhiều từ hơn → vẫn 3 kết quả, không có phiếu loại trừ. Patch `SEARCH_SCAN_MAX = 3`, thêm 3 phiếu loại trừ mới hơn cùng khớp → 3 phiếu thường vẫn có trong kết quả. Hàng `:447` giữ các ca cũ.

---

### Sửa 7 — phán quyết (3d): `agent/daily_report.py` (INT-U6b-1)

**Thay:** addendum `:82` (cột "Chủ") và phần `daily_report.py` của `:404`.

**Văn bản thay:** `erp_ai/agent/daily_report.py` thuộc touchpoint U6b như việc hòa nhập INT-U6b-1 **theo phán quyết (3d)**. U5a đã merge ở đợt 0. Sửa đúng 4 khóa thêm vào `ACTION_KIND_BY_TOOL`: `reply_to_requester` → "trả lời"; `resolve_on_tasks_done`, `close_silent_f` → "đổi trạng thái"; `create_kb_draft` → "bài CSKT". `lifecycle_comment`, `requester_notice` không thêm, nên rơi vào "khác" theo `design.md:453`.

**Test:** `erp_ai/agent/test_daily_report.py::TestActionKinds::test_u6b_tools_classified`: dòng nhật ký có 4 mục mang 4 tên tool trên → báo cáo 08:00 xếp đúng 4 loại. Chạy cùng các test 08:00 có sẵn của U5a, các test đó xanh.

---

### Sửa 8 — phán quyết (1b), w1a phán quyết (3), quyết định (a): quyền đọc HD Article cho Instructor ở T22a

**Thay:** addendum `:73` (hàng 1.3), `:355` (hàng "Đọc bài nháp của bot").

**Văn bản thay:**
- 1.3: Quyền đọc HD Article cho `ERP AI Instructor` (`read=1`, `report=1`, `permlevel 0`) do **T22a của đợt 0 (U0)** cài, trong `erp_ai/install.py`, theo mẫu `_ensure_task_permission`: `setup_custom_perms("HD Article")` trước, rồi thêm dòng nếu chưa có. **U6b không sửa `install.py` hay `test_install.py`.** Điều kiện bắt đầu task chứa `test_instructor_lists_bot_drafts`: T22a đã merge vào `team/FEAT-007`. Thiếu thì `DESIGN_CONFLICT` cho câu cuối của AC-45. Đường lùi "Instructor kèm role Agent" chỉ dùng khi người không chấp nhận hệ quả (1b), và team-leader quyết việc đó.
- Mục 5: `Đọc bài nháp của bot` | `ERP AI Instructor` | Custom DocPerm đọc HD Article do T22a cài; quyền của Agent, System Manager, HD Customer, HD Customer Manager không đổi (test của T22a).

**Test:** `erp_ai/agent/tools/test_kb_draft.py::TestCreateKbDraft::test_instructor_lists_bot_drafts` (giữ, U6b): user chỉ có `ERP AI Instructor`, không có `Agent`, đọc được danh sách HD Article `Draft` có `ai_source_ticket`.

---

### Sửa 9 — mục 5 w1b và minor (f): thứ tự sửa `prompts.py`, `runner.py` là U4b → U6b → U8; điều kiện trigger cho thông báo của U4b

**Thay:** thêm vào đầu 3.8 (`:281`) và 3.9 (`:291`). Thêm vào cuối 3.8.

**Văn bản thay:**
- **Thứ tự:** `erp_ai/agent/runner.py`: U1 → U2 → U3 → **U4b → U6b**. `erp_ai/agent/prompts.py`: U1 → **U4b → U6b → U8**. Task `runner.py` và task `prompts.py` của U6b cắt nhánh sau khi U4b đã merge vào `team/FEAT-007`. Task `prompts.py` của U8 cắt sau U6b. Task file mới của U6b (`knowledge_read.py`, `reply.py`, `kb_draft.py`, `lifecycle.py`) chạy song song với U4b được.
- **`prompts.py`:** U6b chỉ sửa phép chọn `task` theo trigger trong `build_initial_message` (bản có `ticket_fields` của U4b), thêm `TASK_REQUESTER_REPLY` (chữ ở Sửa 1) và `TASK_KB_DRAFT` cạnh hằng `TASK_*`, `KNOWLEDGE_SOURCES_BLOCK`, `REPLY_BLOCK` và cờ `reply_tools` của `build_reason_system`. Gợi ý đầu mục C chỉ ghép khi trigger ∈ {`ticket_insert`, `comment_mention`}; điều kiện đó do U8 thêm (w1b mục 5), U6b không viết nó.
- **`runner.py`, xung đột về nghĩa với U4b:** lần chạy `kb_draft` **không** đăng thông báo `over_budget` hay `run_failed`, vì phiếu đã đóng và dòng cấp cố định không có tool comment. Chỉ có **một** điều kiện: trong hàm đăng thông báo dùng chung của U4b (`_notice`), `trigger == TRIGGER_KB_DRAFT` → trả `None`, không đăng, không có mục hành động. `daily_limit` không tới được với `kb_draft` vì kiểm (d) được miễn. `ask_fallback` cũng không tới được vì `below_threshold=False` ở `kb_draft`. Với `requester_reply`, cả bốn thông báo của U4b áp như U4b định.

**Test:** `erp_ai/agent/test_agent_runner.py::TestKbDraftRun::test_no_notice_comments_on_kb_draft`: (1) vượt ngân sách, mức gốc L3 → 0 Comment `owner = AGENT_USER` trên phiếu; (2) cổng model ném lỗi → 0 Comment, dòng lỗi có. `erp_ai/agent/test_prompts.py::TestTaskByTrigger::test_requester_reply_and_kb_draft_tasks`: mỗi trigger chọn đúng hằng `TASK_*`.

---

### Sửa 10 — mục 5 w1b, hàng `write_ticket.py`: câu hỏi gửi qua email không phải "lần hỏi" của AC-22

**Thay:** thêm assumption A-U6b-10; `reply.py` (3.4) giữ nguyên, không gọi hàm nào của `write_ticket.py`.

**Văn bản thay:** `reply_to_requester(kind="question")` **không** đánh dấu `asked_in_run`. Khi dưới ngưỡng, lần chạy vẫn có đúng 1 comment hỏi: comment `post_comment(kind="hoi")` của model, hoặc `ask_fallback` của runner U4b ở lượt cuối. Người tạo có thể nhận thêm một câu hỏi qua email. Căn cứ trong spec: AC-22 viết "không trả lời ngoài câu hỏi … và đăng đúng 1 **comment** hỏi". Communication không phải comment; nếu tính email là lần hỏi thì sẽ có 0 comment, trái AC-22. AC-40 "dưới ngưỡng chỉ được hỏi lại" vẫn đúng nhờ kiểm 3 của tool.

**Test:** `erp_ai/agent/test_agent_runner.py::TestKnowledgeActions::test_below_threshold_email_question_still_one_ask_comment`: `reply_enabled`, độ tin cậy 69, ngưỡng 70; model stub chỉ gọi `reply_to_requester(kind="question", "…?")` → 1 Communication `Sent` tới `raised_by` và đúng 1 Comment `ask_fallback`.

---

### Sửa 11 — chữ `classify` thừa ở mục 2

**Thay:** addendum `:107`.

**Văn bản thay:**

| Đường | `entry_type` / `trigger` | `actions` (mỗi lần ghi một mục, qua `action_entry`) |
|---|---|---|
| Lần chạy người tạo trả lời | `reason`/`skip` / `requester_reply`; `run_id = requester_reply_key(ticket, communication)` | mục của lượt; `reply_to_requester` → `("Communication", tên)`; thông báo của U4b nếu có |

Lý do: `_classify` chỉ chạy cho `ticket_insert`. Lần chạy không phải tạo phiếu lấy đầu mục bằng `policy.latest_classification` (U1 `:260`), không ghi dòng `classify`.

---

### Sửa 12 — minor (b): `reply_to_requester` vào `ASK_TOOL_NAMES`, một định nghĩa "tool hỏi"

**Thay:** addendum `:156` (hàng `requester_reply` của bảng cấp), câu "`ASK_TOOL_NAMES` **không đổi**" ở `:159`, A-U6b-3 (`:472`).

**Văn bản thay (3.2):**
- `ASK_TOOL_NAMES = frozenset({"post_comment", "reply_to_requester"})`.
- Hàng bảng cấp: `requester_reply` | `reply_enabled ∧ ¬kb ∧ ¬below_threshold`.
- Bước (3) của `grant` (U1 `:179`), tổng quát hóa: khi `below_threshold`, cộng mọi spec có tên ∈ `ASK_TOOL_NAMES` mà nhóm của nó được cấp khi tính bảng với `dataclasses.replace(inputs, below_threshold=False)`. Với `post_comment` kết quả trùng U1, vì hàng `ticket_write` của U1 chỉ có vế `¬below_threshold`. Với `reply_to_requester`, tool có mặt dưới ngưỡng khi và chỉ khi `reply_enabled ∧ ¬kb`. Bảng hành vi không đổi so với addendum, chỉ còn một định nghĩa "tool hỏi" (ADR-030 QĐ 3).
- Kiểm 3 của `reply.py` (`ctx.below_threshold ∧ kind != "question"`) giữ, như chốt thứ hai ở mức tool.
- A-U6b-3 (thay): dưới ngưỡng, `reply_to_requester` được cấp qua `ASK_TOOL_NAMES` và chỉ nhận `kind=question` có `?`. Sai thì sửa: bỏ tên khỏi `ASK_TOOL_NAMES`.

**Test:** `erp_ai/agent/tools/test_registry.py::TestKnowledgeGrant::test_reply_tool_present_when_switch_on` (giữ, có ca `below_threshold=True`); `::test_ask_tools_below_threshold_follow_ask_tool_names` (mới): dưới ngưỡng, L3, `reply_enabled` đúng → tên = `read` ∪ {`post_comment`, `reply_to_requester`}; `reply_enabled` sai → `read` ∪ {`post_comment`}; `kb_draft_run` đúng → không có tên nào thuộc `ASK_TOOL_NAMES`. Hồi quy U1: `TestGrantFeat007::test_below_threshold_grants_read_and_ask_tool_only` xanh không sửa (vì `reply_enabled` mặc định là False).

---

### Sửa 13 — minor (c) (và w1b minor (a) của U4b): ràng buộc AST cho `lifecycle.py`

**Thay:** thêm vào bảng test, cạnh `:453`.

**Văn bản thay:** `erp_ai/agent/lifecycle.py` không import `erp_ai.agent.tools` (mọi module con), `erp_ai.agent.tools.registry`, `erp_ai.agent.runner`, hay Cổng model. Chiều cho phép: `tools/reply.py` → `lifecycle`, `handlers` → `lifecycle`, `runner` → `lifecycle`. `lifecycle` tự đọc `field_origin` qua `lifecycle_settings`, không dùng `runner._ticket_fields` (STD-DESIGN-6, ADR-033 Ràng buộc 4).

**Test:** `erp_ai/agent/test_lifecycle.py::TestArchitecture::test_lifecycle_imports_no_tools_or_runner` (AST trên `lifecycle.py`, có một ca đỏ dựng bằng chuỗi mẫu `from erp_ai.agent import runner`). Gộp với `::test_no_model_gateway_import` có sẵn.

---

### Sửa 14 — minor (d): `hooks.py` trỏ cron thẳng vào Lõi

**Thay:** không đổi `:310` và A-U6b-6. Thêm một dòng vào mục 6 "Quan sát / As-Built".

**Văn bản thay:** Chấp nhận theo w1b minor (d) (chuỗi hook không phải import, không phá ADR). As-Built ghi: "`scheduler_events.cron['0 * * * *']` trỏ thẳng `erp_ai.agent.lifecycle.scan_silent_f_tickets`, không qua `schedules.py` như U5a."

---

### Sửa 15 — minor (a): lọc trạng thái phiếu ngay trong truy vấn ứng viên của `scan_silent_f_tickets`

**Thay:** bước (4) của `:260`.

**Văn bản thay:** (4) `now = now or now_datetime()`, `cutoff = now − close_silent_f_days ngày`. Ứng viên lấy bằng một truy vấn `frappe.qb`: Communication nối HD Ticket theo `Communication.reference_name = HD Ticket.name`, với `reference_doctype = "HD Ticket"`, `sent_or_received = "Sent"`, `Communication.owner = AGENT_USER`, `Communication.creation <= cutoff`, `HD Ticket.status_category != "Resolved"`; trả `distinct` tên phiếu. Tập ứng viên chỉ gồm phiếu còn mở, nên không lớn dần theo mọi phiếu bot từng trả lời (trần 300 s của hàng `default`, ADR-033 QĐ 6). Bước (5) vẫn khóa dòng và kiểm lại `status_category`, vì trạng thái có thể đổi giữa lúc truy vấn và lúc khóa.

**Test:** `erp_ai/agent/test_lifecycle.py::TestSilentClose::test_resolved_tickets_not_candidates`: 1 phiếu F `Closed` và 1 phiếu F mở, cả hai có tin bot cũ → ứng viên chỉ gồm phiếu mở (patch `send_to_requester` đếm lời gọi = 1).

---

## 2. Touchpoints (thay toàn bộ mục 7, `:372-404`)

| Đường dẫn | Mới/sửa | Căn cứ | Sửa / mục |
|---|---|---|---|
| `erp_ai/agent/tools/registry.py` | sửa | ô U6b `arch-impact.md:180` | 3.2, Sửa 12 |
| `erp_ai/agent/runner.py` | sửa (sau U4b) | ô U6b | 3.8, Sửa 1, 9 |
| `erp_ai/agent/queue.py` | sửa | ô U6b | 3.1, Sửa 1, 3 |
| `erp_ai/handlers.py` | sửa | ô U6b | 3.7, Sửa 1 |
| `erp_ai/hooks.py` | sửa | ô U6b | 3.11, Sửa 14 |
| `erp_ai/agent/prompts.py` | sửa (sau U4b, trước U8) | ô U6b | 3.9, Sửa 1, 9 |
| `erp_ai/agent/tools/knowledge_read.py` | mới | ô U6b (tool mới) | 3.3 |
| `erp_ai/agent/tools/reply.py` | mới | ô U6b (tool mới) | 3.4, Sửa 10, 12 |
| `erp_ai/agent/tools/kb_draft.py` | mới | ô U6b (tool mới) | 3.5 |
| `erp_ai/agent/lifecycle.py` | mới | ô U6b (file job vòng đời) | 3.6, Sửa 1, 2, 13, 15 |
| `erp_ai/agent/run_log.py` | sửa (sau U3) | phán quyết (3a) | 3.12, Sửa 4 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa (sau U3) | phán quyết (3a) | 3.12, Sửa 4 |
| `erp_ai/agent/tools/read.py` | sửa (sau U2) | phán quyết (3c) | 3.10, Sửa 6 |
| `erp_ai/agent/daily_report.py` | sửa (U5a đã merge) | phán quyết (3d), INT-U6b-1 | Sửa 7 |
| `erp_ai/agent/policy.py` | sửa, **một chỗ**: import + phần tử `TRIGGER_REQUESTER_REPLY` trong `RUN_LIMIT_TRIGGERS` (sau U1, U2) | phán quyết (3e), quyết định (b), w1a (2) | Sửa 3 |
| `erp_ai/constants.py` | sửa: 2 hằng trigger | w1a (2) | Sửa 3 |
| `erp_ai/tests/test_architecture.py` | sửa | phán quyết (3b), w1a (2) | Sửa 3, 5 |
| Test cùng chỗ: `erp_ai/agent/tools/test_registry.py`, `test_read.py`, `erp_ai/agent/test_queue.py`, `test_agent_runner.py`, `test_run_log.py`, `test_policy.py`, `test_daily_report.py`, `erp_ai/tests/test_handlers.py`, `test_doctype_descriptions.py` (sửa); `erp_ai/agent/tools/test_knowledge_read.py`, `test_reply.py`, `test_kb_draft.py`, `erp_ai/agent/test_lifecycle.py` (mới); `erp_ai/agent/test_prompts.py` (mới nếu U1/U4b chưa tạo, ngược lại sửa) | — | test của các file trên | mục 3 |

**Bỏ khỏi touchpoint U6b:** `erp_ai/install.py`, `erp_ai/tests/test_install.py` (T22a, quyết định (a)). **Không chạm:** `tools/write_ticket.py` (Sửa 10), `tools/route_ticket.py`, `schedules.py`, `tasks.py`.

**Đường dẫn mới ↔ `structure.allowed_new_file_roots` = `['erp_ai', 'docs', '.github']`:**

| Đường dẫn mới | Gốc khớp |
|---|---|
| `erp_ai/agent/tools/knowledge_read.py`, `reply.py`, `kb_draft.py` | `erp_ai` |
| `erp_ai/agent/lifecycle.py` | `erp_ai` |
| `erp_ai/agent/tools/test_knowledge_read.py`, `test_reply.py`, `test_kb_draft.py`, `erp_ai/agent/test_lifecycle.py`, `erp_ai/agent/test_prompts.py` | `erp_ai` |

**So với `protected_paths` = `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`:** 0 đường dẫn khớp.

**Thứ tự sửa file chung (tech-lead dùng khi lập plan đợt 1):**

| File | Thứ tự | Vùng của U6b |
|---|---|---|
| `runner.py` | U1 → U2 → U3 → U4b → **U6b** | chữ ký, `run_id` theo khóa, (r1)–(r4), `_kb_draft_skip`, miễn (d), L0, context, `WRITE_TOOL_TARGETS`, cờ `reply_tools`, điều kiện `kb_draft` trong `_notice` |
| `prompts.py` | U1 → U4b → **U6b** → U8 | chọn `task`, 2 hằng `TASK_*`, 2 khối, cờ `reply_tools` |
| `policy.py` | U1 → U2 → **U6b** | một phần tử của `RUN_LIMIT_TRIGGERS` |
| `registry.py` | U1 → **U6b** | 3.2, Sửa 12 |
| `handlers.py` | U1 → U2 → {U4b, **U6b**} (thứ tự nào cũng được) | hàm mới, tách `ticket_on_update` |
| `run_log.py`, `erp_ai_log.json` | U3 → **U6b** | `TRIGGERS`, option, mô tả |
| `test_architecture.py` | U5a (đợt 0) → U1 → … → **U6b** | `ENQUEUE_TARGETS`, luật trigger |
| `constants.py` | U0 (đợt 0) → **U6b** | 2 hằng |
| `daily_report.py` | U5a (đợt 0) → **U6b** | 4 khóa |

**Điều kiện bắt đầu U6b (thay `:66`):** U1, U2, U3, U4b (với `runner.py` và `prompts.py`), U6a và T22a đã merge vào `team/FEAT-007`. Thiếu một tên → `DESIGN_CONFLICT`, dừng.

## 3. Test plan sau sửa

Chạy từng file bằng `cmd.test_one`, trước merge chạy `cmd.test`. Bảng mục 8 của addendum giữ nguyên, trừ các thay đổi sau:

| AC / ràng buộc | Thay đổi | Test (`file::Class::name`) |
|---|---|---|
| AC-41 (X-1) | thêm | `test_queue.py::TestEnqueueAgentRun::test_requester_reply_job_id_per_communication`; `test_handlers.py::TestRequesterReply::test_reply_while_previous_job_started_gets_own_job`, `::test_on_update_after_run_no_job`; `test_agent_runner.py::TestRequesterReplyRun::test_message_during_run_not_lost`, `::test_both_messages_before_start_one_model_run`, `::test_moved_event_runs_on_new_ticket` |
| AC-41 B-2 | thay ca | `test_agent_runner.py::TestRequesterReplyRun::test_second_event_after_run_already_handled` (0 dòng thêm, không còn dòng `skip`) |
| AC-44, ADR-033 Ràng buộc (X-3) | thêm | `test_lifecycle.py::TestSilentClose::test_two_runs_same_now_one_close`, `::test_failure_after_notice_rolls_back_then_once`, `::test_failure_on_one_ticket_others_closed`, `::test_resolved_tickets_not_candidates` |
| AC-43, ADR-033 Ràng buộc | thêm | `test_lifecycle.py::TestResolveOnTasksDone::test_failure_midway_rolls_back_then_once` |
| AC-41/AC-45, NFR-2 (X-2) | thêm / sửa | `test_policy.py::TestRunsToday::test_kb_draft_reason_row_not_counted`, `::test_requester_reply_reason_row_counted`; `test_architecture.py::test_run_limit_triggers_subset_of_log_triggers` (luật đổi) |
| AC-48 (3c) | thêm | `test_read.py::TestSearchResolvedTickets::test_excluded_match_does_not_change_result_count` |
| INT-U6b-1 (3d) | thêm | `test_daily_report.py::TestActionKinds::test_u6b_tools_classified` |
| AC-45 (mục 5 w1b) | thêm | `test_agent_runner.py::TestKbDraftRun::test_no_notice_comments_on_kb_draft` |
| AC-22 × AC-40 | thêm | `test_agent_runner.py::TestKnowledgeActions::test_below_threshold_email_question_still_one_ask_comment` |
| AC-40 (minor b) | thêm | `test_registry.py::TestKnowledgeGrant::test_ask_tools_below_threshold_follow_ask_tool_names` |
| STD-DESIGN-6 (minor c) | thêm | `test_lifecycle.py::TestArchitecture::test_lifecycle_imports_no_tools_or_runner` |
| AC-45 câu cuối | giữ, đổi tiền đề | `test_kb_draft.py::TestCreateKbDraft::test_instructor_lists_bot_drafts` (quyền do T22a cài) |
| AC-41, AC-45 prompt | thêm | `test_prompts.py::TestTaskByTrigger::test_requester_reply_and_kb_draft_tasks` |

**Đối chiếu AC:**
- AC của spec cho U6b (`spec.md:210-220`; AC-42 theo `spec-addendum-1.md:94`): AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50.
- AC có test (addendum mục 8 cùng bảng trên): AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50. Khớp 11/11, cả 11 có ca lỗi hoặc biên. Mỗi finding major có test riêng: X-1 → `test_reply_while_previous_job_started_gets_own_job`, `test_message_during_run_not_lost`; X-2 → `test_kb_draft_reason_row_not_counted`, `test_requester_reply_reason_row_counted`; X-3 → `test_two_runs_same_now_one_close`, `test_failure_after_notice_rolls_back_then_once`.

## 4. Assumptions decided by the team (thay A-U6b-1, A-U6b-3, A-U6b-4; thêm A-U6b-10, A-U6b-11)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U6b-1 (thay) | Hai trigger mới ở `erp_ai/constants.py` | w1a (2): `policy` import được mà không lập vòng `policy → queue` | `queue.py` (addendum gốc) | — (theo phán quyết) |
| A-U6b-3 (thay) | Xem Sửa 12 | ADR-030 QĐ 3, một định nghĩa tool hỏi | dòng riêng không xét ngưỡng | bỏ tên khỏi `ASK_TOOL_NAMES` |
| A-U6b-4 (thay) | Khóa sự kiện `requester_reply:{ticket}:{communication}` làm `job_id` và `run_id`; gộp chỉ khi lần chạy bắt đầu sau cả hai tin (`superseded`) | ADR-033 QĐ 2, 6; không mất tin khi job đang chạy; vẫn tiết kiệm NFR-2 khi tin dồn | khóa theo thời điểm bắt đầu của lần chạy trước (cần trường mới) | thêm trường thời điểm bắt đầu vào ERP AI Log (cần architect) |
| A-U6b-10 | Câu hỏi qua email không là "lần hỏi" của AC-22 | AC-22 đòi đúng 1 **comment** hỏi | đánh dấu `asked_in_run` từ `reply.py` | `reply.py` gọi hàm đánh dấu của `write_ticket.py` (thêm touchpoint U6b) |
| A-U6b-11 | Rollback theo savepoint mỗi phiếu ở job vòng đời | lỗi một phiếu không gỡ việc phiếu khác; test được trong giao dịch test | `frappe.db.rollback()` toàn phần | đổi về rollback toàn phần, giữ hai test X-3 |

## 5. Bảng đóng: finding / phán quyết → sửa

| Finding hoặc phán quyết | Nguồn | Được giải bởi |
|---|---|---|
| X-1 khóa "người tạo trả lời" không theo tên Communication | w1b mục 3 | Sửa 1 |
| X-2 `runs_today` không ai lọc trigger | w1b mục 3 | Sửa 3 |
| X-3 thiếu hai test ADR-033 cho đóng F im lặng | w1b mục 3 | Sửa 2 |
| minor (a) ứng viên không lọc trạng thái | w1b mục 3 | Sửa 15 |
| minor (b) `ASK_TOOL_NAMES` | w1b mục 3 | Sửa 12 |
| minor (c) ràng buộc AST `lifecycle.py` | w1b mục 3 | Sửa 13 |
| minor (d) cron thẳng vào Lõi | w1b mục 3 | Sửa 14 |
| minor (e) vị từ dạng truy vấn của U2 | w1b mục 3 | Sửa 6 |
| minor (f) thứ tự sửa với U4b | w1b mục 3 | Sửa 9 |
| Phán quyết (1) `ai_created_labels` | w1b mục 4 | không thuộc U6b (U4b, T22a); U6b không đọc trường này |
| Phán quyết (1b) quyền HD Article cho Instructor | w1b mục 4 | Sửa 8 (T22a, quyết định (a)) |
| Phán quyết (2) `ai_confidence_pct` ở `route_ticket.py` | w1b mục 4 | không thuộc U6b (U4b); U6b chỉ đọc qua `latest_classification` |
| Phán quyết (3a) `run_log.py`, `erp_ai_log.json` | w1b mục 4 | Sửa 4 |
| Phán quyết (3b) `test_architecture.py`, 6 đích | w1b mục 4 | Sửa 5 |
| Phán quyết (3c) `tools/read.py` | w1b mục 4 | Sửa 6 |
| Phán quyết (3d) `daily_report.py` | w1b mục 4 | Sửa 7 |
| Phán quyết (3e) `policy.py` `RUN_LIMIT_TRIGGERS` | w1b mục 4 | Sửa 3 (theo quyết định (b): U1 sở hữu, U6b nối một phần tử) |
| Phán quyết (4) runner AC-19/25/27/28 | w1b mục 4 | không thuộc U6b (U4b) |
| Mục 5: `prompts.py` hằng `TASK_*`, `build_initial_message` | w1b mục 5 | Sửa 9 (U4b → U6b → U8) |
| Mục 5: `runner.py` thông báo `over_budget`/`run_failed` ở `kb_draft` | w1b mục 5 | Sửa 9 |
| Mục 5: `write_ticket.py` email hỏi vs `ask_fallback` | w1b mục 5 | Sửa 10 |
| Mục 5: `handlers.py`, `registry.py` | w1b mục 5 | không xung đột; thứ tự ở mục 2 |
| Chữ `classify` thừa ở mục 2 | journal `:17` | Sửa 11 |
| w1a phán quyết (2) (chủ U1, trigger ở `constants.py`, luật tập hợp) | w1a mục 4 | Sửa 3 |
| w1a phán quyết (3) (U6b sửa `install.py`) | w1a mục 4 | thay bằng quyết định (a) → Sửa 8 |
| w1b mục 6: rủi ro NFR-1 của `read_error_logs` | w1b mục 6 | **chưa giải trong U6b**: team-leader chọn giữa thêm test gieo chuỗi vào Error Log (tool của U6b, hàm che của U6a) và ghi As-Built |
