Feature: FEAT-002
Stage: design
Author-agent: designer
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Design FEAT-002 — Chỉ báo "Đang suy nghĩ… / Đang làm: <việc>…" trên trang phiếu agent, câu trả lời `@ai` trễ 3–5 giây chỉnh được trong cấu hình

> Bản viết lại (2026-11-12) theo spec Amendment 1 + 2 (AC-1..AC-12), `arch-impact.md`, ADR-007, ADR-008. Bản cũ (comment tạm, mục `DESIGN_CONFLICT`) bỏ hẳn. Design này không tạo, sửa hay xóa bản ghi nghiệp vụ nào lúc chạy. ADR-004 giữ nguyên.

## 1. Bối cảnh

### 1.1 Vấn đề và phạm vi (trích spec)
- **Trong phạm vi:**
  - 3 mục cấu hình: câu chữ chỉ báo, trễ tối thiểu, trễ tối đa (AC-1).
  - Chỉ báo trạng thái cho mọi lần chạy có gọi model: `comment_mention` ở `L1+` và `ticket_insert` ở mọi mức (AC-2, A-11).
  - Trạng thái "Đang làm: <nhãn>…" khi chạy tool hoặc bước phân loại (AC-9).
  - Đúng 1 tín hiệu kết thúc ở mọi nhánh, kể cả nhánh rollback (AC-4, R-2).
  - Câu trả lời đầu tiên của `@ai` trễ `d` ∈ [min, max] kể từ tín hiệu bắt đầu (AC-3).
  - Lỗi phát tín hiệu không chặn lần chạy (AC-7).
  - Phần giao diện nằm trong repo `erp_ai`, về site khi cài/cập nhật app (AC-10, AC-11, AC-12).
- **Ngoài phạm vi:** tạo/sửa/xóa bản ghi để hiện chỉ báo; sửa `apps/helpdesk`; chỉ báo lúc job còn chờ hàng đợi (A-17); lịch sử trạng thái; trang khách (A-13); mobile không bắt buộc (A-19); trễ trước comment thứ hai trở đi (A-5); đổi giới hạn lần chạy, dedup, ngân sách; đổi giá trị cấu hình trên `miyano`.
- Giả định của spec mà design làm theo: A-3..A-6, A-8, A-10..A-17, A-19..A-22, A-18'.

### 1.2 ADR phải tuân
| ADR | Ràng buộc áp vào design này |
|---|---|
| ADR-001 | Module mới `run_status.py`, `answer_delay.py` thuộc Lõi agent (`erp_ai/agent/`, ngoài `tools/`), theo `LAYER_RULES`. Không import mới tới `erp_ai.gateway` |
| ADR-002 | Không thêm lời gọi Claude API. Số lời gọi gateway không đổi (NFR-3) |
| ADR-003 | Tín hiệu đầu chỉ phát sau bước (e) và sau chốt `level_L0`. Thời gian chờ dùng chung `deadline` của lần chạy, không nới. Không thêm job, không đổi `enqueue` |
| ADR-004 | **Không đổi.** 3 trường cấu hình chỉ người ghi qua form, runner chỉ đọc. Phát realtime không phải "ghi", nên phát ở `L0` không trái quyết định 4. Chỉ runner tạo nhật ký |
| ADR-005 | Tool không biết tới tín hiệu. Registry và schema tool không đổi. Nhãn việc nằm ngoài `tools/` |
| ADR-006 | `after_migrate` chỉ điền giá trị còn thiếu cho 3 trường mới. Ngoại lệ hẹp duy nhất là bản ghi HD Form Script theo ADR-007 Quyết định 4 |
| ADR-007 | Một bản ghi HD Form Script tên cố định, nguồn là một tệp `.js` trong repo, đặt lại mỗi lần cài/migrate, xóa ở `before_uninstall`. Script chỉ nghe, không gọi server, chỉ dùng `textContent` |
| ADR-008 | `publish_realtime` chỉ ở `run_status.py`, chỉ runner gọi. `room` tường minh `doc:HD Ticket/<tên>`, `after_commit=False`. Payload đúng 7 khóa. `done` trong `finally` sau commit cuối. Không ghi DB, cache hay tệp |

### 1.3 Tóm tắt khảo sát (cơ sở của design)
Explore cache `docs/team/explore/erp_ai.md` = `MISS` (cache cũ từ lúc takeover 2026-11-10, trước FEAT-001). Các file cần biết đã biết trước, nên đọc thẳng từng phần (tool-map: "One known file → Read"). Số dòng lấy từ cây làm việc `team/BUG-001` (= `team/FEAT-001` + sửa gateway; `runner.py`, `install.py`, `erp_ai_setting.py` không đổi so với `team/FEAT-001`).
- **Kiểu lỗi.**
  - Form: `frappe.throw("<nhãn> phải từ <a> đến <b>")` tiếng Việt, cận đọc từ bảng `INT_LIMITS` (`erp_ai_setting.py:30-36`, `:88-96`).
  - Runner: nhật ký chỉ ghi tên lớp lỗi; `error` của một lượt là các mảnh nối bằng `"; "` (`runner.py:301`, `:322`).
  - Lỗi ngoài nhật ký đi `frappe.log_error(<TITLE_*>, "ticket=… … error=<Class>")` (`runner.py:57-59`).
- **Vòng đời lần chạy.**
  - `run_for_ticket` không bao giờ ném và không rollback (`runner.py:48-59`).
  - `_run`: (a)…(e) `:71-97`; chốt `level_L0` `:99-101`; `_classify` cho `ticket_insert` `:115-118`; `_reason` cho `L1+` `:119-120`.
  - Commit: sau mỗi lời gọi gateway (`_call_model` `:62-68`), sau mỗi `write_entry` (`run_log.py:31-32`), sau `_apply_classification` (`:235-236`). Trong test không commit (`frappe.flags.in_test`), `RunnerTestBase` chặn mọi `commit` (`test_agent_runner.py:59-61`).
  - `_apply_classification` dùng savepoint, rollback rồi ném lại khi lỗi (`:206-234`). Đây là nhánh rollback của R-2.
- **Tool.** 11 tool trong 3 module (`registry.py:30-34`): `get_ticket`, `list_comments`, `search_resolved_tickets`, `get_record` (`tools/read.py:200-254`); `search_source`, `read_source`, `git_source` (`tools/source.py:282-325`); `set_classification`, `set_resolution_hint`, `post_comment`, `create_task` (`tools/write_ticket.py:111-175`). `get_tool_schemas("L3", True)` trả đủ 11.
- **Realtime (Frappe 15.126.1).**
  - `frappe.publish_realtime` → `frappe.realtime.publish_realtime`. Với `after_commit=False`, hàm gọi ngay `emit_via_redis(event, message, room)` (biến toàn cục của module, `frappe/realtime.py:83`).
  - Với `after_commit=True`, tín hiệu chờ `frappe.db.after_commit` và bị xóa khi rollback (`:73-81`). `emit_via_redis` nuốt `redis.ConnectionError` (`:108`).
  - Hệ quả cho test: patch `frappe.realtime.emit_via_redis` ghi lại tín hiệu đi qua đúng đường thật. Nếu ai đó đổi sang `after_commit=True`, test sẽ thấy 0 tín hiệu, vì test không commit.
- **HD Form Script (Helpdesk 15.1.0).**
  - `autoname = prompt` (tên do mã đặt); trường `dt`, `apply_to`, `enabled`, `script`, `apply_to_customer_portal`, `apply_on_new_page`, `is_standard`.
  - `before_save`/`on_trash` chỉ làm việc khi `is_standard = 1` (`hd_form_script.py:15-58`).
  - `get_form_script(dt, apply_to, is_customer_portal, apply_on_new_page)` lọc đủ 4 cờ (`:61-84`).
  - SPA chạy `new Function(script + "\nreturn setupForm")()` rồi đọc `actions`/`onChange` của kết quả (`formCustomisation.ts:92-99`). Ngữ cảnh có `doc, call, router, toast, $dialog, updateField, createToast` (`TicketHeader.vue:318-326`). `setupForm` chạy lại trong `watchEffect` (`:329-338`). Route trang phiếu agent là `TicketAgent`, `/tickets/:ticketId` (`router/index.ts:42-43`).
- **Cài đặt.** `ensure_setup()` gọi 6 bước "tạo phần còn thiếu" (`install.py:30-37`). `_ensure_default_settings` điền mặc định khi giá trị trong `tabSingles` là `NULL` hoặc chưa có (`:66-75`). Bước nào cần doctype của app khác thì kiểm doctype có tồn tại, thiếu thì ghi cảnh báo logger rồi bỏ qua (`:164-167`). `hooks.py` chưa có `before_uninstall` (`:92` là dòng comment mẫu).
- **Lint JS.** `.eslintrc`: `eslint:recommended`, `sourceType: module`, `no-unused-vars: off`, `no-console: warn`, env browser. Prettier/eslint chạy cho `javascript` trong `erp_ai/**`, trừ `public/dist`, `public/js/lib` (`.pre-commit-config.yaml:34-64`). `erp_ai/public/js/` đang rỗng (`public/.gitkeep`).
- **Test.**
  - Test đặt cạnh mã (`structure.tests = colocated`), tên `test_{name}.py`, dùng `FrappeTestCase`, mỗi test rollback.
  - Stub gateway: `FakeGateway` (`test_utils.py:30-46`). Phiếu dựng bằng `helpdesk.test_utils.make_ticket`.
  - `test_agent_runner.py` đã 1021 dòng. `test_handlers.py::test_run_for_ticket_calls_classify_once` chạy runner thật cho `ticket_insert` (`:213-225`).
  - `test_architecture.py` là luật ADR máy kiểm (`LAYER_RULES` `:36-64`; `load_product_sources(suffixes=…)` `:131-138` đọc được cả `.js`).
- **Helpdesk hiện trạng:** `git -C ../helpdesk status --porcelain` đã có sẵn 3 dòng không do FEAT-002 tạo: `M desk/auto-imports.d.ts`, `M desk/yarn.lock`, `M yarn.lock`. Bước DoD "Helpdesk không bị sửa" so với đúng 3 dòng gốc này.
- **Phân trang.** Không áp dụng.

## 2. Mô hình dữ liệu

### 2.1 `ERP AI Setting` (Single, đã có): thêm 3 trường người đặt (ADR-004 hàng 1)
| fieldname | fieldtype | label | default | Ràng buộc (kiểm khi lưu, mục 3.1) |
|---|---|---|---|---|
| `thinking_text` | Small Text | Chữ chỉ báo khi đang suy nghĩ | `Đang suy nghĩ…` | ≤ 5000 ký tự; rỗng hoặc chỉ khoảng trắng = tắt chỉ báo (D-8). `description`: "Hiện trên chỉ báo trạng thái ở trang phiếu. Để trống để tắt chỉ báo; khoảng trễ vẫn áp dụng." |
| `answer_delay_min_s` | Int | Trễ trả lời tối thiểu (giây) | `3` | 0 ≤ giá trị ≤ 30 |
| `answer_delay_max_s` | Int | Trễ trả lời tối đa (giây) | `5` | 0 ≤ giá trị ≤ 30; tối thiểu ≤ tối đa |

- Vị trí trong `field_order`: ngay sau `trigger_keyword`. Cập nhật `modified` của DocType.
- Single không có cột riêng: mỗi trường là một dòng `tabSingles`. Runner đọc cả tài liệu một lần mỗi lần chạy (`runner.py:82`), nên không cần chỉ mục.
- Cận 30 lấy từ hằng mới `ANSWER_DELAY_MAX_S = 30` trong `erp_ai/constants.py`. Đây là nguồn duy nhất, dùng chung cho `INT_LIMITS` và `answer_delay.py`.
- Ghi: chỉ người, qua form. Runner chỉ đọc. Không mã nào lưu tài liệu cấu hình (ADR-004).

### 2.2 Bản ghi `HD Form Script` của app (cấu hình lúc cài, ADR-007)
| Trường | Giá trị |
|---|---|
| `name` | `AGENT_STATUS_SCRIPT = "ERP AI Agent Status"` (hằng trong `erp_ai/install.py`; không chứa "Field Dependency", nên `get_parent_child_field` của Helpdesk trả `None`) |
| `dt` | `"HD Ticket"` |
| `apply_to` | `"Form"` |
| `enabled` | `1` |
| `apply_to_customer_portal` | `0` (chỉ trang agent, A-13) |
| `apply_on_new_page` | `0` |
| `is_standard` | `0` (hook `before_save`/`on_trash` của Helpdesk không làm gì) |
| `script` | Nội dung tệp `erp_ai/public/js/agent_status_indicator.js`, đọc bằng `frappe.get_app_path("erp_ai", "public", "js", "agent_status_indicator.js")`, UTF-8. Không có bản sao trong Python hay JSON |

- Chủ ghi: chỉ `erp_ai/install.py` (ADR-007 Quyết định 3). Không mã nào trong `erp_ai/agent/**`, `gateway/**`, handler hay tasks đọc hoặc ghi bản ghi này.
- Vòng đời: tạo hoặc đặt lại ở mỗi `after_install`/`after_migrate`; xóa ở `before_uninstall`. Luôn đúng 1 bản ghi.

### 2.3 Trạng thái chỉ báo: không lưu ở server
- Không có bản ghi DB, khóa Redis cache hay tệp nào mới lúc chạy (ADR-008 Quyết định 5, A-14, NFR-6).
- Trạng thái chỉ nằm trong bộ nhớ của script trên trang (`window.__erpAiAgentStatus`, mục 3.7).
- `ERP AI Log`: không thêm trường, không thêm `entry_type`. Lỗi phát tín hiệu đi vào trường `error` có sẵn (mục 3.5). Khoảng trễ đã áp dụng ghi ra logger, không ghi vào nhật ký (D-10, A-8).

## 3. API / hợp đồng
Không có thay đổi phá vỡ. Mọi thay đổi là thêm vào; hợp đồng sự kiện là phiên bản đầu (v1). Không cần hướng dẫn chuyển đổi (STD-DESIGN-3).

### 3.1 Form `ERP AI Setting`: kiểm tra khi lưu (`ERPAISetting.validate`)
- `INT_LIMITS` thêm 2 dòng, cận trên là `ANSWER_DELAY_MAX_S`:
  - `"answer_delay_min_s": ("Trễ trả lời tối thiểu", 0, ANSWER_DELAY_MAX_S)`
  - `"answer_delay_max_s": ("Trễ trả lời tối đa", 0, ANSWER_DELAY_MAX_S)`

  Thông báo đi qua mẫu có sẵn `f"{label} phải {bound}"`.
- Phương thức mới `check_status_settings()`, gọi ngay sau `check_limits()`:
  1. `self.thinking_text = self.thinking_text or ""`. Lý do: giá trị rỗng phải lưu là `""` chứ không phải `NULL`, nếu không `_ensure_default_settings` sẽ điền lại mặc định ở lần migrate sau và bật lại chỉ báo người đã tắt (D-8).
  2. Kiểm min ≤ max và độ dài câu chữ.

| Điều kiện từ chối (`frappe.ValidationError`) | Thông báo (là hợp đồng, test so đúng chuỗi) |
|---|---|
| `answer_delay_min_s` < 0 hoặc > 30 | `Trễ trả lời tối thiểu phải từ 0 đến 30` |
| `answer_delay_max_s` < 0 hoặc > 30 | `Trễ trả lời tối đa phải từ 0 đến 30` |
| tối thiểu > tối đa (cả hai đã trong khoảng) | `Trễ trả lời tối thiểu không được lớn hơn trễ trả lời tối đa` |
| `len(thinking_text)` > 5000 | `Chữ chỉ báo khi đang suy nghĩ không được dài quá 5000 ký tự` |

- Lưu được khi 0 ≤ min ≤ max ≤ 30 (gồm 0/0 và min = max), và khi câu chữ rỗng.
- Giá trị `None` của trường Int được coi là 0 (cùng quy tắc `or 0` của `check_limits`).

### 3.2 Sự kiện realtime `erp_ai:agent_status` (hợp đồng nội bộ v1, ADR-008)
| Mục | Giá trị |
|---|---|
| Tên sự kiện | `AGENT_STATUS_EVENT = "erp_ai:agent_status"` (định nghĩa một lần trong `erp_ai/constants.py`; tệp `.js` chứa đúng chuỗi này, có test so) |
| Phòng | `frappe.realtime.get_doc_room("HD Ticket", ticket_name)` → `doc:HD Ticket/<tên>`; truyền `room=` tường minh |
| Cách phát | `frappe.publish_realtime(AGENT_STATUS_EVENT, message=payload, room=room, after_commit=False)` |
| Người phát / người nghe | chỉ `erp_ai/agent/run_status.py` (do runner gọi) / chỉ script ở mục 3.7 |

Payload: đúng 7 khóa, không khóa nào khác (NFR-4').
| Khóa | Kiểu | Giá trị |
|---|---|---|
| `ticket_id` | str | `str(ticket_name)`. Tên HD Ticket là số tự tăng, nên phía trang so bằng `String(...)` |
| `run_id` | str | `run_id` của lần chạy (hex 32) |
| `agent_user` | str | `AGENT_USER` |
| `agent_name` | str | `frappe.utils.get_fullname(AGENT_USER)` |
| `state` | str | `thinking` \| `working` \| `done` |
| `text` | str | `thinking`: câu chữ cấu hình đã `strip()`. `working`: `f"Đang làm: {nhãn}…"` (nhãn ở mục 3.3). `done`: `""` |
| `expires_in_s` | int | `JOB_TIMEOUT_S` (600) |

Hành vi là hợp đồng (test kiểm):
- Với mỗi `run_id`: tín hiệu đầu là `thinking`; có đúng 1 `done` và `done` là tín hiệu cuối.
- Không có 2 tín hiệu `thinking` liền nhau (D-3).
- Lần chạy bị bỏ qua, hoặc câu chữ rỗng: 0 tín hiệu.
- `text` không bao giờ chứa tham số tool, nội dung phiếu hay câu trả lời.
- Phía nghe bỏ qua khóa lạ và `state` lạ. Sau này chỉ được thêm khóa (tương thích ngược).

### 3.3 Module mới `erp_ai/agent/run_status.py` (chỉ runner import, ADR-008 Quyết định 2–4)
Hằng của module:
- `CLASSIFY_STEP = "classify"`.
- `PAYLOAD_KEYS` = 7 khóa ở mục 3.2.
- `WORKING_TEXT = "Đang làm: {label}…"`.
- `FALLBACK_WORK_LABEL = "xử lý yêu cầu"`.
- `WORK_LABELS` (bảng nhãn duy nhất, A-15):

| Khóa | Nhãn | Khóa | Nhãn |
|---|---|---|---|
| `get_ticket` | đọc phiếu | `git_source` | xem lịch sử mã nguồn |
| `list_comments` | đọc comment | `set_classification` | ghi phân loại |
| `search_resolved_tickets` | tìm phiếu đã giải quyết | `set_resolution_hint` | ghi hướng giải quyết |
| `get_record` | tra bản ghi | `post_comment` | viết trả lời |
| `search_source` | tra mã nguồn | `create_task` | tạo task |
| `read_source` | đọc mã nguồn | `classify` (`CLASSIFY_STEP`) | phân loại phiếu |

| Lớp / phương thức | Hành vi | Lỗi |
|---|---|---|
| `RunStatus(ticket_name: str, run_id: str, thinking_text: str \| None)` | Chỉ lưu tham số. `active = bool((thinking_text or "").strip())`. Không đọc DB, không phát | Không ném |
| `start() -> None` | Nếu `active` và chưa start: đánh dấu `started` **trước** khi phát (để `done` vẫn được thử khi phát hỏng, AC-7), rồi phát `thinking` với câu chữ cấu hình | Không ném |
| `thinking() -> None` | Phát `thinking` khi đã start, chưa `done`, và tín hiệu gần nhất không phải `thinking` | Không ném |
| `working(step: str) -> None` | Phát `working` với nhãn `WORK_LABELS.get(step, FALLBACK_WORK_LABEL)`. Tên tool lạ do model bịa ra không bao giờ vào `text` (D-5) | Không ném |
| `done() -> None` | Phát `done` đúng 1 lần khi đã start. Gọi lại thì không làm gì | Không ném |
| `take_errors() -> list[str]` | Trả các mảnh lỗi đang chờ rồi xóa danh sách | — |
| `signal_count` (thuộc tính) | Số lần đã thử phát; dùng cho dòng logger | — |
| `_emit(state, text)` (riêng) | Dựng payload bằng `dict(zip(PAYLOAD_KEYS, …))`, gọi `frappe.publish_realtime(...)` như mục 3.2. `agent_name` lấy một lần, bên trong `try`. Mọi `Exception` được bắt, thêm mảnh `f"status_{state}: {type(exc).__name__}"` | Bắt hết; không ném ra runner |

Module không import `erp_ai.gateway`. Module không gọi `frappe.cache`, `frappe.db.*` ghi, `.insert(`, `.save(`, `delete_doc`.

### 3.4 Module mới `erp_ai/agent/answer_delay.py` (chỉ runner import)
| Hàm / lớp | Hành vi |
|---|---|
| `_now()`, `_sleep(seconds)`, `_pick(low, high)` | Bọc `time.monotonic`, `time.sleep`, `random.uniform`. Đây là điểm thay thế cho test (STD-TEST-6) |
| `AnswerDelay.start(low_s, high_s) -> AnswerDelay` | `low, high` = `None → 0`, kẹp vào [0, `ANSWER_DELAY_MAX_S`], sắp lại để low ≤ high (phòng trường hợp DB ghi thẳng, không qua form). `delay_s = _pick(low, high)` (`low == high` → đúng `k`). `anchor = _now()`. `waited_s = 0.0` |
| `wait_before_answer(deadline: float) -> float` | Chỉ có tác dụng ở lần gọi đầu (A-5). `remaining = anchor + delay_s - _now()`; `wait = min(remaining, deadline - _now())`. `wait > 0` thì `_sleep(wait)`. Ghi `waited_s`, trả về số giây đã chờ. Không bao giờ ngủ quá `deadline`, và không nới `deadline` (NFR-2) |

### 3.5 Nhật ký lần chạy và Error Log: giá trị mới (thêm vào)
- Trường `error` của bản ghi `classify`/`reason` **kế tiếp** trong lần chạy có thể có thêm mảnh `status_thinking: <Class>` hoặc `status_working: <Class>`, nối với lỗi có sẵn bằng `"; "`.
- Mảnh lỗi của `done`, và mảnh còn chờ khi lần chạy kết thúc mà không còn bản ghi nào được viết (nhánh ngoại lệ), đi vào Error Log:
  - tiêu đề `TITLE_STATUS_FAILED = "erp_ai: chỉ báo trạng thái lỗi"` (hằng mới trong `constants.py`);
  - nội dung `f"ticket={ticket} run_id={run_id} {mảnh}"`.
- Chỉ có mã và tên lớp lỗi, không có câu chữ, nhãn hay nội dung phiếu (NFR-4', D-9).

### 3.6 Cài đặt (`erp_ai/install.py`, `hooks.py`)
- `ensure_setup()` thêm bước thứ 7 `_ensure_agent_status_script()`. Docstring đổi thành: "Create what is missing; never overwrite or remove anything a human set — except the app-owned HD Form Script, reset from the repo file (ADR-007)."
- `_ensure_agent_status_script()`:
  1. Không có `DocType` `HD Form Script` → `frappe.logger(LOGGER_NAME).warning(...)` rồi bỏ qua (cùng kiểu `_ensure_task_permission`).
  2. `wanted = {**AGENT_STATUS_SCRIPT_FLAGS, "script": <nội dung tệp>}`.
  3. Chưa có bản ghi → `frappe.get_doc({"doctype": FORM_SCRIPT_DOCTYPE, "name": AGENT_STATUS_SCRIPT, **wanted}).insert(ignore_permissions=True)`.
  4. Đã có và khác ở bất kỳ khóa nào của `wanted` → `doc.update(wanted)`, `doc.save(ignore_permissions=True)`. Giống hệt thì không lưu, để `modified` không đổi vô ích.
- `before_uninstall()` (hàm mới, `hooks.py` thêm `before_uninstall = "erp_ai.install.before_uninstall"`):
  - Doctype tồn tại và bản ghi tồn tại → `frappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)`.
  - Không có thì không làm gì.
  - Đây là lệnh xóa duy nhất trong mã cài đặt (ADR-007 Quyết định 4).
- Hằng trong `install.py`:
  - `FORM_SCRIPT_DOCTYPE = "HD Form Script"`;
  - `AGENT_STATUS_SCRIPT = "ERP AI Agent Status"`;
  - `AGENT_STATUS_SCRIPT_FILE = ("public", "js", "agent_status_indicator.js")`;
  - `AGENT_STATUS_SCRIPT_FLAGS = {"dt": "HD Ticket", "apply_to": "Form", "enabled": 1, "apply_to_customer_portal": 0, "apply_on_new_page": 0, "is_standard": 0}`.

  Chuỗi `"HD Form Script"` chỉ được xuất hiện ở đây (ADR-007 Ràng buộc).

### 3.7 Script trang phiếu `erp_ai/public/js/agent_status_indicator.js` (nguồn duy nhất của bản ghi 2.2)
- **Hình dạng.**
  - Một hàm cấp cao nhất `function setupForm({ doc, router })`, luôn trả `{ actions: [] }`.
  - Thân hàm bọc `try/catch`. `catch` không làm gì, có comment ghi lý do: chỉ báo không bao giờ được làm hỏng trang phiếu (ADR-007 Quyết định 5, STD-ERR-1).
  - Không `import`/`export`, vì Helpdesk nạp bằng `new Function`.
  - Không dùng tham số `call`, `updateField`; không viết chữ `call` ở đâu trong tệp (test tĩnh, mục 8).
  - Tệp không chứa chuỗi `HD Form Script` (ADR-007 Ràng buộc 1 quét cả `.js`).
- **Trạng thái trong bộ nhớ:** `window.__erpAiAgentStatus = { ticket, runs: Map(run_id → {timer, text, name, at}), finished: Set(run_id), el, socket, bound }`. Không `localStorage`, `sessionStorage`, cookie.
- **Mỗi lần `setupForm` chạy:**
  1. `socket = document.querySelector("#app")?.__vue_app__?.config?.globalProperties?.$socket`. Không có socket (hoặc `socket.on` không phải hàm), hoặc không có `doc?.name` → trả về ngay, không lỗi, không log (AC-10 g).
  2. `String(doc.name)` khác `state.ticket` → `reset()`: xóa mọi hẹn giờ, `runs`, `finished`, ẩn phần tử. Sau đó gán `state.ticket` (AC-10 i).
  3. `socket.emit("doc_subscribe", "HD Ticket", state.ticket)`. Không bao giờ `doc_unsubscribe` (R-3).
  4. Lần đầu với socket này (`state.socket !== socket`):
     - `socket.on(EVENT, onStatus)`;
     - `socket.on("connect", …)` để `doc_subscribe` lại phiếu hiện tại;
     - `router.afterEach(to => …)`: rời route `TicketAgent` hoặc `ticketId` khác phiếu hiện tại → `reset()`.

     Cờ `state.socket` chống đăng ký trùng khi `setupForm` chạy lại.
- **`onStatus(msg)`:**
  1. Bỏ qua khi `String(msg?.ticket_id) !== state.ticket`, khi `run_id` đã nằm trong `finished`, hoặc khi `state` lạ.
  2. `done` → xóa hẹn giờ và `runs[run_id]`, thêm vào `finished`, `render()`.
  3. `thinking`/`working`:
     - Lần đầu thấy `run_id`: `ms = Number(msg.expires_in_s) * 1000`. Không hợp lệ (≤ 0 hoặc NaN) thì bỏ qua tín hiệu (D-14). Hợp lệ thì đặt `setTimeout(ms)` **một lần** tính từ tín hiệu đầu; hết hạn thì như `done` (AC-11).
     - Mỗi tín hiệu: cập nhật `text`, `name = msg.agent_name || msg.agent_user`, `at = Date.now()`, rồi `render()`.
- **`render()`:**
  - `runs` rỗng → ẩn phần tử (`hidden = true`).
  - Ngược lại hiện **một** chỉ báo cho `run_id` có `at` mới nhất (AC-10 i).
  - Phần tử tạo một lần bằng `document.createElement`, gắn vào `document.body`, có `role="status"` và `aria-live="polite"`.
  - Bên trong có: một chấm động (3 chấm, `Element.animate` của Web Animations, không cần stylesheet), tên agent (`textContent`, in đậm) và chữ trạng thái (`textContent`). Không dùng HTML (AC-10 f).
  - Kiểu dáng inline qua `el.style`: cố định ở góc dưới phải (`right: 24px; bottom: 88px`), nền trắng, viền xám nhạt, bo góc, bóng nhẹ, `z-index: 40`, chữ 13px (D-11).
- **Từ cấm trong tệp** (test tĩnh): `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval(`, `new Function`, `doc_unsubscribe`, `localStorage`, `sessionStorage`, `document.cookie`, `fetch(`, `XMLHttpRequest`, `frappe.call`, `updateField`, `open_doc:`, `\bcall\b`, `600`.

### 3.8 Hỗ trợ test (`erp_ai/test_utils.py`, thêm vào, không đổi hành vi cũ)
- `FakeGateway(*results, on_call=None)`: `on_call(task, kwargs)` chạy trước khi trả kết quả. Dùng để ghi thứ tự tín hiệu/lời gọi model và đẩy đồng hồ giả (AC-2, AC-3). Mặc định `None`.
- `record_status_signals(testcase) -> list[dict]`:
  - patch `frappe.realtime.emit_via_redis` bằng một hàm ghi `{"event", "message", "room"}` cho các sự kiện `AGENT_STATUS_EVENT`;
  - các sự kiện khác bị bỏ, không gửi Redis;
  - `addCleanup` gỡ patch.

  Test không bao giờ chạm Redis thật (STD-TEST-6). Muốn làm hỏng việc phát, test truyền `side_effect`.

## 4. Luồng

### 4.1 Đường chính `comment_mention`, `L1+`, câu chữ khác rỗng
1. `_run` chạy (a)…(e), rồi chốt `level_L0` như cũ (ADR-003). Ở mọi nhánh dừng sớm, `RunStatus` chưa được tạo, nên không có tín hiệu nào (AC-5).
2. `status = RunStatus(ticket_name, run_id, settings.thinking_text)`.
3. `try:`
   1. `status.start()` → tín hiệu `thinking` (câu chữ cấu hình).
   2. `delay = AnswerDelay.start(settings.answer_delay_min_s, settings.answer_delay_max_s)` nếu trigger là `comment_mention`, ngược lại `None`. `anchor` = ngay sau tín hiệu bắt đầu (AC-3). Câu chữ rỗng thì cùng điểm này là "lúc bắt đầu lập luận".
   3. `mapping`, `context`, `_classify` (chỉ `ticket_insert`), `_reason` như cũ, có thêm tham số `status` (và `delay` cho `_reason`).
4. `finally: _end_status(status, delay, ticket_name, run_id, trigger)` (mục 4.5).
5. Trong `_reason`, mỗi lượt:
   1. `status.thinking()` ngay trước `_call_model("reason", …)`. Ở lượt 1 lệnh này không phát gì, vì tín hiệu gần nhất đã là `thinking`.
   2. Gọi gateway như cũ. Thời gian model chạy tự trừ vào `d` (A-3).
   3. Nếu `delay` khác `None` và có khối `tool_use` tên `post_comment` (`ANSWER_TOOL`, hằng mới trong runner): `delay.wait_before_answer(deadline)` **trước khi chạy tool nào của lượt** (D-6). Trong lúc chờ, chỉ báo vẫn ở `thinking` (AC-3).
   4. Với mỗi khối: `status.working(block["name"])`, rồi `_run_tool(...)` như cũ (`_run_tool` không đổi).
   5. `write_entry(..., error="; ".join([*tool_errors, *status.take_errors()]) or None)`. Nhánh `GatewayError` cũng nối `status.take_errors()` vào `error`.
6. Chuỗi tín hiệu ví dụ (model gọi `get_ticket`, rồi `post_comment`, rồi `end_turn`): `thinking(câu chữ)`, `working(đọc phiếu)`, `thinking`, `working(viết trả lời)`, `thinking`, `done`.

### 4.2 `ticket_insert` (mọi mức, có chỉ báo, không trễ)
1. Như 4.1 bước 1–3, `delay = None`.
2. Trong `_classify`:
   - `status.working(CLASSIFY_STEP)` ngay trước `_call_model("classify", …)`. Lời gọi phân loại là việc cố định, không phải lập luận mở (D-4).
   - Ở `L1+`: `status.working("set_classification")` ngay trước `_apply_classification`.
   - Các `write_entry` của `classify` nối `status.take_errors()` vào `error`, cùng các lỗi có sẵn (`UNPARSEABLE_ERROR`, `BAD_MAPPING_ERROR`, lỗi gateway).
3. `L1+` → `_reason` như 4.1 bước 5, với `delay = None` nên không chờ.
4. Chuỗi ở `L0`: `thinking`, `working(phân loại phiếu)`, `done`.
5. Chuỗi ở `L1` (model `end_turn` ngay): `thinking`, `working(phân loại phiếu)`, `working(ghi phân loại)`, `thinking`, `done`.

### 4.3 Khoảng trễ (AC-3, NFR-1, NFR-2)
| Trường hợp | Kết quả |
|---|---|
| Model trả lời ngay | ngủ ≈ `d`; `post_comment` chạy lúc ≥ `anchor + d` |
| `min = max = k` | `d = k` |
| Model mất > `d` | `remaining ≤ 0` → không gọi `_sleep` |
| `0/0` | `d = 0` → không gọi `_sleep` |
| Gần hạn chót | chờ ≤ `deadline - now`; không ngủ quá hạn chót; hạn chót không nới |
| Câu chữ rỗng, `d > 0` | 0 tín hiệu; vẫn chờ, tính từ `anchor` (AC-5) |
| `post_comment` thứ hai trở đi | không chờ (A-5) |
| Lượt có `post_comment` trả `ok=false` | đã chờ một lần; lần sau không chờ thêm |
| `ticket_insert` | `delay = None`, không chờ |

### 4.4 Nhánh kết thúc (AC-4): `done` luôn là tín hiệu cuối
| Nhánh | Tín hiệu cuối phát ở | Commit cuối trước `done` |
|---|---|---|
| Có câu trả lời, model `end_turn` | `finally` của `_run` | `write_entry` của lượt cuối |
| Model không gọi `post_comment` | như trên | như trên |
| Lỗi gateway / hết thời gian (`deadline`) trong `_reason` | như trên | `write_entry` của bản ghi lỗi |
| Lỗi gateway ở `_classify` (`proceed = False`) | như trên | `write_entry` `classify` |
| Hết số lượt (`max_turns`) | như trên | `write_entry` lượt `max_turns` |
| Tool lỗi (ngoại lệ trong tool) | lần chạy tiếp tục như cũ; `done` theo nhánh kết thúc thực tế | như nhánh đó |
| Ngoại lệ bất kỳ trong `_run` sau điểm start (ví dụ `build_initial_message` ném) | `finally`, rồi ngoại lệ lan tới `run_for_ticket` (ghi `TITLE_RUN_FAILED` như cũ) | lần commit gần nhất |
| Nhánh rollback (R-2): `_apply_classification` rollback savepoint rồi ném | `finally`. `after_commit=False`, nên `done` không bị xóa theo rollback | `write_entry` `classify` |

### 4.5 `_end_status(status, delay, ticket_name, run_id, trigger)`: hàm riêng của runner, chạy ở `finally`
1. `status.done()`.
2. Mỗi mảnh trong `status.take_errors()` → `frappe.log_error(TITLE_STATUS_FAILED, f"ticket={ticket_name} run_id={run_id} {mảnh}")`.
3. Ghi một dòng `frappe.logger(LOGGER_NAME).info`, chỉ có mã và số (STD-OPS-5, mục 6.4):
   `"erp_ai run_status ticket=%s run_id=%s trigger=%s signals=%d errors=%d delay_s=%.1f waited_s=%.1f"`
   `delay = None` thì `delay_s` và `waited_s` = 0.
4. Không commit, không rollback.

### 4.6 Lỗi khi phát (AC-7)
- `RunStatus` không ném. Phát hỏng ở bất kỳ bước nào thì lần chạy vẫn gọi model và vẫn đăng câu trả lời như khi không có tính năng.
- Start hỏng: `started` đã được đặt, nên `done` vẫn được thử. Các tín hiệu sau vẫn được thử.
- Mảnh lỗi `thinking`/`working` vào `error` của bản ghi nhật ký kế tiếp. Mảnh lỗi `done` vào Error Log (D-9).
- `emit_via_redis` tự nuốt `redis.ConnectionError`: thiếu Redis hoặc `socketio` thì chỉ báo im lặng, không có mảnh lỗi.

### 4.7 Phía trang (ADR-007, ADR-008 Quyết định 6)
1. Agent mở trang phiếu → Helpdesk gọi `get_ticket_customizations` → nhận script (chỉ trang agent) → `setupForm({doc, router, …})`.
2. Script lấy socket, `doc_subscribe` phòng `doc:HD Ticket/<tên>` (Frappe kiểm quyền đọc), đăng ký listener một lần.
3. Worker phát tín hiệu → Redis → `socketio` → mọi socket trong phòng.
4. `thinking`/`working` → hiện hoặc cập nhật chỉ báo. `done` → ẩn ngay. Không có `done` → ẩn sau `expires_in_s` kể từ tín hiệu đầu.
5. Tải lại trang làm mất bộ nhớ, nên chỉ báo không hiện lại (AC-11). Người mở trang giữa chừng thấy chỉ báo từ tín hiệu kế tiếp (A-12).
6. Chuyển phiếu → `reset()` (qua `setupForm` với `doc.name` mới, hoặc `router.afterEach`).

### 4.8 Lời gọi ra ngoài (STD-ERR-5)
- Không có lời gọi mạng mới ra ngoài bench, và không thêm lời gọi model.
- `publish_realtime` → `emit_via_redis` là một lệnh `PUBLISH` tới Redis nội bộ của bench, không retry.
  - Thành công: tín hiệu tới `socketio`.
  - Thất bại: `ConnectionError` bị Frappe nuốt (im lặng); lỗi khác bị `RunStatus` bắt (mảnh lỗi).
  - Không rõ kết quả: không có, vì `PUBLISH` không có trạng thái treo cần dọn.
  - Timeout theo cấu hình kết nối Redis của bench. Trần cứng là `timeout=600` của job (ADR-003). Ghi nhận là rủi ro chấp nhận, không thêm timeout riêng.
- `time.sleep` nằm trong worker hàng đợi `long`: tối đa 30 s mỗi lần chạy `@ai` (A-6), trong `deadline` 540 s.

## 5. Quyền
- **Cấu hình.** Không đổi: chỉ `System Manager` đọc/ghi (`test_hd_agent_cannot_read_or_write_settings`). Kiểm đầu vào ở biên là `validate` của DocType (STD-ERR-2).
- **Phát tín hiệu.** Chạy dưới `AGENT_USER` trong worker; `publish_realtime` không cần quyền.
  - Ai nhận được do Frappe kiểm ở `doc_subscribe` → `can_subscribe_doc` → `frappe.has_permission("HD Ticket", doc=…)` (STD-SEC-4, phía server).
  - Khách có quyền đọc phiếu tự gửi `doc_subscribe` vẫn nhận payload. Vì vậy payload chỉ chứa 7 khóa NFR-4' (ADR-008 Hệ quả).
- **Script.** Chỉ chạy trên trang agent (`apply_to_customer_portal = 0`, A-13). Không endpoint mới, không lời gọi server từ script. Chữ hiện bằng `textContent`, nên câu chữ cấu hình có thẻ HTML vẫn hiện nguyên văn (STD-SEC-3, AC-10 f). Dữ liệu từ socket coi là không tin cậy: chỉ đọc đúng các khóa đã biết, so kiểu bằng `String(...)`/`Number(...)`.
- **Cài/gỡ.** Chạy dưới Administrator trong `migrate`/`install-app`/`uninstall-app`, `ignore_permissions=True` như các bước cài khác. Lệnh xóa chỉ nhắm đúng tên hằng.
- **Mức `L0`.** Phát realtime không ghi bản ghi, nên `ticket_insert` ở `L0` có chỉ báo mà không trái ADR-004 Quyết định 4.
- **Model.** Model không điều khiển được `text`: tên tool lạ → nhãn dự phòng; tham số tool không bao giờ vào payload.

## 6. Migration và rollback

### 6.1 Lên
- Sửa `erp_ai_setting.json` (3 trường, `field_order`, `modified`), thêm tệp `.js` và mã cài đặt, rồi chạy `cmd.migrate`.
  - Single không có DDL. `after_migrate` → `ensure_setup`:
    - `_ensure_default_settings` chèn 3 dòng `tabSingles` với giá trị mặc định, **chỉ khi chưa có** (ADR-006);
    - `_ensure_agent_status_script` tạo bản ghi HD Form Script.
  - Các giá trị cấu hình khác trên `miyano` không đổi (spec Constraints).
- Không có patch, không chuyển dữ liệu. Không đổi schema `Comment`, `HD Ticket`, `Task`, `ERP AI Log`.
- `cmd.build` không cần: tệp `.js` được đọc bằng Python lúc cài, không phải tài sản bundle (không có hậu tố `.bundle.js`).
- Đổi tệp `.js` về sau thì phải chạy `cmd.migrate` để bản ghi được đặt lại (ADR-007 Hệ quả).

### 6.2 Xuống
1. Trên site, gọi `erp_ai.install.before_uninstall` một lần, **trước** khi revert mã. Hàm xóa bản ghi `ERP AI Agent Status`. Sau khi revert thì không còn mã nào quản bản ghi này.
2. Revert các commit của FEAT-002, rồi chạy `cmd.migrate`.
3. Frappe không xóa dòng `tabSingles` của trường đã bỏ. 3 dòng còn lại vô hại, vì không mã nào đọc. Muốn sạch hẳn thì người xóa tay trên bản sao trước: `frappe.db.delete("Singles", {"doctype": "ERP AI Setting", "field": ("in", ["thinking_text", "answer_delay_min_s", "answer_delay_max_s"])})`.
4. Gỡ cả app thì `before_uninstall` tự xóa bản ghi.
- **Điều kiện kích hoạt rollback:**
  - `cmd.migrate` lỗi;
  - trang phiếu agent có lỗi console mới hoặc không dùng được (AC-10 g);
  - comment mới không còn hiện trực tiếp (AC-10 h);
  - lần chạy `@ai` trên `miyano` không ra câu trả lời.
- **Lùi một nửa** (giữ phần server, tắt phần trang): đặt `thinking_text` rỗng trên form. Khi đó không còn tín hiệu nào; script vẫn nạp nhưng không hiện gì.

### 6.3 Đối soát (dev chạy trên bản sao, qa chạy lên → xuống → lên)
| Thời điểm | Kiểm |
|---|---|
| Trước khi lên | chụp `(field, value)` của `tabSingles` với `doctype = 'ERP AI Setting'`; đếm `HD Form Script` tên `ERP AI Agent Status` (= 0); đếm `Comment`, `Task` |
| Sau khi lên | số dòng `tabSingles` = trước + số trường còn thiếu (≤ 3); mọi cặp cũ giống hệt; 3 dòng mới = `Đang suy nghĩ…` / `3` / `5`; đúng 1 bản ghi HD Form Script với các cờ ở mục 2.2 và `script` bằng tệp |
| Lên lần hai | vẫn 1 bản ghi, `modified` không đổi (không có gì khác) |
| Sau xuống (bước 1–2) | 0 bản ghi HD Form Script |
| Lên lại | như "sau khi lên"; 3 giá trị đã có không bị ghi đè |
| Sau một lần chạy `@ai` | số `Comment` của phiếu tăng đúng bằng số câu trả lời agent đăng; `Task` không đổi khi không có lệnh tạo task (NFR-6) |

Dữ liệu nhỏ (1 Single, 1 bản ghi), không cần chia lô.

### 6.4 Quan sát (STD-OPS-5)
- Mỗi lần chạy đã qua mọi chốt ghi đúng 1 dòng logger `erp_ai`:
  `erp_ai run_status ticket=<t> run_id=<r> trigger=<trigger> signals=<n> errors=<k> delay_s=<d:.1f> waited_s=<w:.1f>`
- Dòng này chỉ có mã và số, không có câu chữ (NFR-4').
- Lỗi phát tín hiệu: mảnh `status_*` trong `ERP AI Log.error`, và Error Log `erp_ai: chỉ báo trạng thái lỗi`.
- `/team:release` dùng dòng logger và các mảnh lỗi này để chứng minh tính năng chạy. Phần hiển thị chỉ chứng minh được bằng bước tay AC-10.

## 7. Touchpoints
| file | change | ghi chú |
|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | sửa | 3 trường mục 2.1, `field_order` sau `trigger_keyword`, cập nhật `modified` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | sửa | 2 dòng `INT_LIMITS` dùng `ANSWER_DELAY_MAX_S`; `check_status_settings()` (chuẩn hóa `""`, min ≤ max, độ dài) gọi trong `validate` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | sửa | Test AC-1: mặc định, từng ca từ chối, biên hợp lệ |
| `erp_ai/constants.py` | sửa | `AGENT_STATUS_EVENT`, `TITLE_STATUS_FAILED`, `ANSWER_DELAY_MAX_S` |
| `erp_ai/agent/run_status.py` | mới | Module phát duy nhất, bảng nhãn, payload 7 khóa (mục 3.3) |
| `erp_ai/agent/answer_delay.py` | mới | Chọn `d`, chờ có trần `deadline`, điểm thay thế đồng hồ (mục 3.4) |
| `erp_ai/agent/runner.py` | sửa | `RunStatus`/`AnswerDelay` sau chốt `level_L0`; `try/finally` + `_end_status`; `thinking()` trước mỗi lời gọi `reason`; `working()` trước mỗi tool, trước `classify` và `_apply_classification`; chờ trước tool của lượt có `post_comment`; nối `take_errors()` vào `error` |
| `erp_ai/install.py` | sửa | `_ensure_agent_status_script()`, `before_uninstall()`, hằng mục 3.6, docstring `ensure_setup` |
| `erp_ai/hooks.py` | sửa | `before_uninstall = "erp_ai.install.before_uninstall"` |
| `erp_ai/public/js/agent_status_indicator.js` | mới | Nguồn của bản ghi HD Form Script (mục 3.7) |
| `erp_ai/test_utils.py` | sửa | `FakeGateway(on_call=None)`, `record_status_signals()` (mục 3.8) |
| `erp_ai/agent/test_agent_runner.py` | sửa | `RunnerTestBase.setUp`: đặt `answer_delay_min_s = answer_delay_max_s = 0`, gắn `record_status_signals`, patch `answer_delay._sleep` thành bộ ghi. Test cũ giữ nguyên hành vi, không ngủ thật, không chạm Redis |
| `erp_ai/agent/test_run_status.py` | mới | Test đơn vị `run_status.py` |
| `erp_ai/agent/test_answer_delay.py` | mới | Test đơn vị `answer_delay.py` với đồng hồ giả |
| `erp_ai/agent/test_runner_status.py` | mới | Test tích hợp runner AC-2..AC-9, NFR-3..NFR-6. Dùng lại `RunnerTestBase` (import từ `test_agent_runner`), vì file đó đã 1021 dòng (STD-STRUCT-5) |
| `erp_ai/tests/test_handlers.py` | sửa | `HandlerTestCase.setUp` gắn `record_status_signals`, để `test_run_for_ticket_calls_classify_once` không publish lên Redis thật |
| `erp_ai/tests/test_install.py` | sửa | `setUp` xóa bản ghi `ERP AI Agent Status` trong giao dịch; `_counts()` đếm bản ghi; test AC-12 và mặc định AC-1 |
| `erp_ai/tests/test_architecture.py` | sửa | Luật máy kiểm của ADR-007/ADR-008 (mục 8.2), kèm test bộ quét bắt được vi phạm |

Kiểm "sửa": cả 12 file đã có (đã đọc, hoặc `ls` thư mục `erp_ai/`, `erp_ai/agent/`, `erp_ai/tests/`, `erp_ai_setting/` ở mục 1.3). Không có touchpoint nào trong `apps/helpdesk`.

Kiểm đường dẫn mới so với `structure.allowed_new_file_roots = ["erp_ai", "docs", ".github"]`:
```
erp_ai/agent/run_status.py                 -> erp_ai   OK (naming.file snake_case)
erp_ai/agent/answer_delay.py               -> erp_ai   OK (naming.file snake_case)
erp_ai/public/js/agent_status_indicator.js -> erp_ai   OK (thư mục public/js có sẵn)
erp_ai/agent/test_run_status.py            -> erp_ai   OK (naming.test_file test_{name}.py)
erp_ai/agent/test_answer_delay.py          -> erp_ai   OK (naming.test_file test_{name}.py)
erp_ai/agent/test_runner_status.py         -> erp_ai   OK (naming.test_file test_{name}.py)
```
Kiểm so với `protected_paths = [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`: không file nào là `.env*`, `*.pem`, `*.key` hay `license.txt`. **0 in protected_paths.**

## 8. Test plan
Lệnh chạy theo slot: `cmd.test_one` với `{file}` = đường dẫn file test; trước khi merge chạy `cmd.test`; tệp `.js` qua `cmd.format`/`cmd.lint`. Không có slot test JavaScript (J1, A-21), nên phần trang là bước tay.

Viết tắt:
- `S` = `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestERPAISetting`
- `I` = `erp_ai/tests/test_install.py::TestInstall`
- `D` = `erp_ai/agent/test_answer_delay.py::TestAnswerDelay`
- `E` = `erp_ai/agent/test_run_status.py::TestRunStatus`
- `R` = `erp_ai/agent/test_runner_status.py::TestRunnerStatus`
- `A` = `erp_ai/tests/test_architecture.py::TestArchitecture`

Trong `R`:
- tín hiệu đọc từ `record_status_signals`;
- "timeline" = một danh sách chung mà `FakeGateway(on_call=…)`, bộ ghi tín hiệu và bộ ghi `_sleep` cùng ghi vào;
- so bật/tắt dùng `frappe.db.savepoint` → chạy → ghi kết quả → `frappe.db.rollback(save_point=…)` → đổi cấu hình → chạy lại trên cùng phiếu.

### 8.1 Theo tiêu chí
| Tiêu chí | Test | Loại | Nhánh lỗi / biên |
|---|---|---|---|
| AC-1 | `S::test_status_fields_defaults` (meta default và `get_doc` sau khi xóa `Singles`: `Đang suy nghĩ…` / 3 / 5) | integration | — |
| AC-1 | `S::test_status_fields_rejections` (subTest: min −1, 31; max −1, 31; min 4 > max 3; câu chữ 5001 ký tự; mỗi ca so đúng chuỗi mục 3.1) | integration | biên −1/31, min > max, 5001 |
| AC-1 | `S::test_status_fields_valid_edges_save` (0/0, 30/30, 3/3, 0/30, câu chữ rỗng, câu chữ 5000 ký tự) | integration | biên 0, 30, min = max, 5000 |
| AC-1 | `I::test_status_defaults_filled_only_when_missing` | integration | đã có giá trị → không ghi đè |
| AC-1 | `I::test_emptied_thinking_text_survives_setup` (lưu form với câu chữ rỗng → `ensure_setup()` → vẫn rỗng) | integration | rỗng không bị điền lại (D-8) |
| AC-2 | `R::test_start_signal_before_first_model_call` (`comment_mention`, L1: tại lời gọi model đầu, timeline có đúng 1 tín hiệu `thinking`; `text` = câu chữ cấu hình; `agent_user`, `ticket_id`, `room = "doc:HD Ticket/<tên>"` đúng) | integration | — |
| AC-2 | `R::test_ticket_insert_l0_gets_start_signal` | integration | `ticket_insert` ở `L0` |
| AC-2 | `R::test_feature_adds_no_comment_task_or_ticket_change` (bật/tắt, cùng stub có `post_comment`: số `Comment`, `Task` tăng như nhau; `modified` của phiếu đổi/không đổi như nhau) | integration | — |
| AC-3 | `D::test_full_delay_when_model_instant` (đồng hồ giả; `_sleep(d)`) | unit | — |
| AC-3 | `D::test_delay_always_within_min_max` (50 lần, `_pick` thật, min 1 / max 4: mọi `d` ∈ [1, 4]) | unit | biên khoảng |
| AC-3 | `D::test_fixed_delay_when_min_equals_max` | unit | min = max |
| AC-3 | `D::test_no_wait_when_model_slower_than_delay` (`_sleep` không được gọi) | unit | model chậm hơn `d` |
| AC-3 | `D::test_no_wait_when_zero_zero` | unit | 0/0 |
| AC-3 | `D::test_wait_capped_by_run_deadline` (`deadline - now` = 1, `d` = 5 → chờ 1) | unit | gần hạn chót |
| AC-3 | `D::test_waits_only_once` | unit | A-5 |
| AC-3 | `D::test_out_of_range_db_values_are_clamped` (−5/99, 9/2) | unit | giá trị DB không qua form |
| AC-3 | `R::test_answer_waits_from_start_signal` (min = max = 4; `on_call` đẩy đồng hồ 1 s; timeline: `thinking` → model → `sleep(3)` → `working(viết trả lời)` → comment được tạo) | integration | — |
| AC-3 | `R::test_indicator_stays_thinking_while_waiting` (giữa model và `sleep` không có tín hiệu nào khác `thinking`) | integration | — |
| AC-4 | `R::test_done_last_when_answered` | integration | — |
| AC-4 | `R::test_done_last_when_no_post_comment` | integration | `end_turn` |
| AC-4 | `R::test_done_last_on_gateway_error` | integration | lỗi gateway |
| AC-4 | `R::test_done_last_on_deadline` | integration | hết thời gian |
| AC-4 | `R::test_done_last_on_max_turns` | integration | hết số lượt |
| AC-4 | `R::test_done_last_after_tool_exception` | integration | tool lỗi |
| AC-4 | `R::test_done_last_on_classify_gateway_error` | integration | `ticket_insert` dừng ở phân loại |
| AC-4 | `R::test_done_last_on_unexpected_runner_exception` (`runner.build_initial_message` ném) | integration | ngoại lệ bất kỳ |
| AC-4 | `R::test_done_reaches_page_on_rollback_branch` (R-2: L1 `ticket_insert`, `frappe.db.set_value` trên `LOG_DOCTYPE` ném như `test_failure_after_tool_rolls_ticket_back_and_keeps_entry`; bộ ghi trên `emit_via_redis` thật vẫn thấy `done`) | integration | rollback |
| AC-5 | `R::test_skipped_runs_emit_nothing_and_never_wait` (subTest: agent tắt, `not_sendable`, `daily_limit`, `comment_mention` ở `L0`; delay 3/5) | integration | 4 nhánh bỏ qua |
| AC-5 | `R::test_empty_text_no_signal_delay_still_applies` (subTest `""`, `"   "`; 3/5: 0 tín hiệu, `_sleep` được gọi) | integration | rỗng / chỉ khoảng trắng |
| AC-5 | `R::test_ticket_insert_never_waits` (subTest L0, L1 có `post_comment`; delay 3/5: có tín hiệu, 0 lần `_sleep`) | integration | `ticket_insert` |
| AC-6 | `R::test_mention_run_counts_once_for_daily_limit` (`policy.runs_today` = 1) | integration | — |
| AC-6 | `R::test_model_messages_same_with_feature_on_and_off` (`messages` của mọi lời gọi stub bằng nhau) | integration | — |
| AC-7 | `R::test_start_signal_failure_still_answers_and_logs_class` (`emit_via_redis` ném `RuntimeError` khi `state == thinking`: có câu trả lời; `error` lượt 1 chứa `status_thinking: RuntimeError`; vẫn thử `done`) | integration | phát bắt đầu hỏng |
| AC-7 | `R::test_working_signal_failure_still_answers_and_logs_class` | integration | phát "đang làm" hỏng |
| AC-7 | `R::test_done_signal_failure_logged_to_error_log_class_only` (`frappe.log_error` được gọi với `TITLE_STATUS_FAILED`, `ticket=… run_id=… status_done: RuntimeError`) | integration | phát kết thúc hỏng |
| AC-7 | `R::test_status_text_never_in_logs` (câu chữ cấu hình = chuỗi đánh dấu; không có trong mọi trường `ERP AI Log`, mọi lời gọi `frappe.log_error` đã patch, dòng logger) | integration | NFR-4' |
| AC-7 | `E::test_emit_never_raises_and_records_class` | unit | ngoại lệ bất kỳ |
| AC-7 | `E::test_done_sent_after_failed_start` | unit | start hỏng |
| AC-8 | `R::test_same_gateway_calls_and_cost_with_feature_on_and_off` (bật 3/5 + câu chữ, tắt 0/0 + rỗng: `call_count` và tổng `cost_usd` của nhật ký bằng nhau) | integration | — |
| AC-8 | Toàn bộ test có sẵn của app: `cmd.test`, dán đầu ra | suite | hồi quy |
| AC-9 | `R::test_signal_sequence_read_tool_then_answer` (stub: lượt 1 `get_ticket`, lượt 2 `post_comment`, lượt 3 `end_turn` → đúng chuỗi ở 4.1 bước 6) | integration | — |
| AC-9 | `R::test_ticket_insert_l1_signal_sequence` (đúng chuỗi ở 4.2 bước 5) | integration | — |
| AC-9 | `E::test_every_granted_tool_and_classify_step_has_label` (mọi tên trong `get_tool_schemas("L3", True)` và `CLASSIFY_STEP` có nhãn khác rỗng trong `WORK_LABELS`) | unit | tool mới quên nhãn |
| AC-9 | `E::test_unknown_tool_gets_fallback_label` (tên tool chứa chuỗi đánh dấu → `text` = nhãn dự phòng) | unit | tên tool do model bịa |
| AC-9 | `R::test_tool_arguments_and_ticket_text_never_in_payload` (chuỗi đánh dấu trong tham số `post_comment`/`search_resolved_tickets` và trong tiêu đề phiếu không có trong payload nào) | integration | NFR-4' |
| AC-10 | Bước tay (a)–(i), kịch bản ở mục "Việc của người" | manual | lỗi khóa API (c); HTML (f); hai phiên (h); đổi phiếu (i) |
| AC-10 | `A::test_status_script_static_rules` (từ cấm mục 3.7; có `textContent`, `doc_subscribe`, `"connect"`; có `try`) — hỗ trợ (f), (g), (h); không thay bước tay | static | — |
| AC-11 | Bước tay AC-11 (kịch bản ở mục "Việc của người") | manual | worker bị giết |
| AC-11 | `A::test_status_script_static_rules` (đọc `expires_in_s`, có `setTimeout`, không có `600` viết cứng) | static | — |
| AC-12 | `I::test_status_script_installed_once_matching_repo_file` (`ensure_setup()` ×2 + `after_migrate()`: đúng 1 bản ghi, các cờ mục 2.2, `script` = tệp) | integration | gọi lặp |
| AC-12 | `I::test_status_script_reset_when_changed_on_site` (subTest: sửa `script`, `enabled = 0`, `apply_to_customer_portal = 1` → `ensure_setup()` → về đúng như repo) | integration | sửa tay trên site (A-22) |
| AC-12 | `I::test_status_script_served_to_agent_page_only` (`helpdesk…hd_form_script.get_form_script("HD Ticket")` chứa script; `is_customer_portal=True` thì không) | integration | trang khách |
| AC-12 | `I::test_unchanged_status_script_is_not_saved_again` (`modified` không đổi ở lần gọi hai) | integration | — |
| AC-12 | `I::test_uninstall_removes_only_status_script` (thêm 1 HD Form Script khác; `before_uninstall()` → 0 bản ghi của app, bản ghi kia còn) | integration | bản ghi người khác |
| AC-12 | `I::test_uninstall_without_record_is_noop` | integration | đã bị xóa trước |
| AC-12 | Đầu ra `cmd.migrate` trên `miyano`, dán trong `acceptance.md` | manual | — |
| NFR-1 | `D::test_delay_always_within_min_max`, `D::test_fixed_delay_when_min_equals_max` | unit | — |
| NFR-2 | `S::test_status_fields_rejections` (cận 30), `D::test_wait_capped_by_run_deadline`, `D::test_out_of_range_db_values_are_clamped` | unit/integration | biên 30, hạn chót |
| NFR-3 | `R::test_same_gateway_calls_and_cost_with_feature_on_and_off` | integration | — |
| NFR-4' | `E::test_payload_has_exactly_seven_keys` (mọi trạng thái); `R::test_tool_arguments_and_ticket_text_never_in_payload`; `R::test_status_text_never_in_logs` | unit/integration | — |
| NFR-5 | `R::test_done_after_last_log_entry` (patch `runner.write_entry` có `wraps`, ghi vào timeline: `done` đứng sau lần `write_entry` cuối, tức sau commit cuối); bước tay AC-10 (b), (c) | integration/manual | — |
| NFR-6 | `R::test_feature_adds_no_comment_task_or_ticket_change`; `A::test_run_status_writes_nothing` | integration/static | — |

### 8.2 Luật kiến trúc máy kiểm (ADR-007, ADR-008) trong `erp_ai/tests/test_architecture.py`
| Test | Kiểm |
|---|---|
| `A::test_publish_realtime_only_in_run_status` | `publish_realtime` chỉ có trong `agent/run_status.py`. Mọi lời gọi có `room=` và `after_commit=False` (hằng `False`) tường minh. Không có `publish_progress`, `emit_via_redis`, `frappe.realtime.` ở tệp sản phẩm khác |
| `A::test_run_status_imported_only_by_runner` | Chỉ `agent/runner.py` import `erp_ai.agent.run_status` |
| `A::test_run_status_writes_nothing` | `run_status.py` không import `erp_ai.gateway`; không có `frappe.cache`, `.insert(`, `.save(`, `delete_doc`, `db.set_value`, `db.sql`, `db.delete` |
| `A::test_no_open_doc_or_all_room` | Chuỗi `open_doc:` và `room="all"` không có trong `.py`/`.js` của `erp_ai/**` (trừ test) |
| `A::test_form_script_only_in_install` | Chuỗi `HD Form Script` chỉ có trong `install.py` (quét `.py`, `.js`, `.json`) |
| `A::test_hooks_have_no_page_injection` | AST `hooks.py` không gán `app_include_js`, `web_include_js`, `app_include_css`, `web_include_css`, `after_request`, `website_route_rules`; `fixtures` (nếu có) không chứa `HD Form Script`; có `before_uninstall = "erp_ai.install.before_uninstall"` |
| `A::test_install_deletes_only_status_script_on_uninstall` | Trong `install.py` chỉ có đúng 1 lệnh xóa (`delete_doc`, `db.delete`, `.delete(`), nằm trong hàm `before_uninstall`, với tham số là hằng `FORM_SCRIPT_DOCTYPE` và `AGENT_STATUS_SCRIPT` |
| `A::test_status_script_static_rules` | Như mục 8.1 hàng AC-10/AC-11 |
| `A::test_status_event_name_matches_script` | `f'"{AGENT_STATUS_EVENT}"'` có trong tệp `.js` |
| `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_status_scanners_catch_violations` | Mỗi bộ quét mới bắt được một nguồn vi phạm giả (cùng kiểu các test bộ quét hiện có) |

### 8.3 Đối chiếu
- Tiêu chí trong spec: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12; NFR-1, NFR-2, NFR-3, NFR-4', NFR-5, NFR-6.
- Tiêu chí trong test plan: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12; NFR-1, NFR-2, NFR-3, NFR-4', NFR-5, NFR-6.
- Khớp 18/18. AC-10 và AC-11 là bước tay theo spec (J1); có test tĩnh hỗ trợ, nhưng test tĩnh không thay bước tay.

## Assumptions decided by the team
- **D-1 Tên.**
  - Chọn: module phát `erp_ai/agent/run_status.py`; sự kiện `erp_ai:agent_status`; bản ghi `ERP AI Agent Status`; tệp `erp_ai/public/js/agent_status_indicator.js`.
  - Vì: theo `naming.file`; `public/js` là chỗ JS sẵn có của app (STD-STRUCT-3); tên sự kiện có tiền tố app, nên lệnh `$socket.off("<tên>")` của Helpdesk không gỡ nhầm.
  - Thay thế: đặt tệp ngoài `public/` để không phục vụ như tài sản tĩnh.
  - Sai thì: đổi `AGENT_STATUS_SCRIPT_FILE`; test AC-12 tự theo.
- **D-2 `text` là chữ hiển thị đầy đủ, do server dựng.**
  - Vì: mọi chữ tiếng Việt nằm một chỗ (bảng nhãn, cấu hình); script không có chuỗi trạng thái riêng.
  - Thay thế: gửi mã bước, script tự dịch.
  - Sai thì: thêm khóa mới vào payload (thêm vào, tương thích), giữ `text`.
- **D-3 Không phát hai `thinking` liền nhau.**
  - Vì: lượt 1 của `_reason` đã ở `thinking` sau tín hiệu bắt đầu; bỏ tín hiệu thừa.
  - Thay thế: phát trước mọi lời gọi model.
  - Sai thì: bỏ điều kiện "tín hiệu gần nhất" trong `thinking()`; sửa chuỗi kỳ vọng ở test AC-9.
- **D-4 Bước phân loại có nhãn "phân loại phiếu", phát trước lời gọi model `classify`. Áp phân loại ở `L1+` có nhãn của tool `set_classification`.**
  - Vì: lời gọi phân loại là việc cố định, không phải lập luận mở; AC-9 đòi nhãn "trước khi việc đó chạy".
  - Thay thế: chỉ phát nhãn phân loại lúc áp kết quả.
  - Sai thì: dời `working(CLASSIFY_STEP)` xuống sau lời gọi model.
- **D-5 Tên tool lạ → nhãn dự phòng "xử lý yêu cầu".**
  - Vì: tên tool do model sinh ra là dữ liệu không tin cậy, không được vào payload (NFR-4').
  - Thay thế: bỏ tín hiệu với tool lạ.
  - Sai thì: đổi `FALLBACK_WORK_LABEL`.
- **D-6 Chờ trước khi chạy tool của lượt có `post_comment`, không phải ngay trước khối `post_comment`.**
  - Vì: lúc đó giao dịch vừa commit (sau lời gọi gateway), nên không giữ khóa dòng `HD Ticket` trong lúc ngủ (ví dụ khi `set_classification` đứng trước trong cùng lượt). Các tool khác trong lượt chỉ chậm theo, vô hại.
  - Thay thế: chờ đúng trước khối `post_comment` (có thể giữ khóa phiếu tới 30 s).
  - Sai thì: chuyển lệnh chờ vào vòng chạy tool, kèm một lần commit trước khi ngủ.
- **D-7 `d` là số thực, `random.uniform(min, max)`.**
  - Vì: tự nhiên hơn, vẫn ∈ [min, max]; min = max cho đúng `k`.
  - Thay thế: `randint`.
  - Sai thì: đổi `_pick`; test khoảng giữ nguyên.
- **D-8 Câu chữ chỉ có khoảng trắng = rỗng; câu chữ rỗng lưu là `""`.**
  - Vì: một chỉ báo trắng vô nghĩa. Nếu lưu `NULL` thì `_ensure_default_settings` điền lại mặc định ở lần migrate sau và bật lại chỉ báo người đã tắt.
  - Thay thế: hiện nguyên văn; hoặc thêm một ô Check "bật chỉ báo".
  - Sai thì: bỏ `strip()` trong `RunStatus`; test `I::test_emptied_thinking_text_survives_setup` vẫn giữ.
- **D-9 Lỗi `thinking`/`working` vào `error` của bản ghi nhật ký kế tiếp; lỗi `done` (và lỗi còn chờ) vào Error Log.**
  - Vì: ADR-008 đặt `done` sau commit cuối, nên không còn bản ghi nhật ký nào để ghi. Sửa ngược bản ghi đã commit sẽ thêm một đường ghi mới vào nhật ký. Không thêm `entry_type`, nên `runs_today` và báo cáo không đổi.
  - Thay thế: `db.set_value` cập nhật `error` của bản ghi cuối.
  - Sai thì: runner giữ tên bản ghi cuối, và `_end_status` cập nhật `error` của nó thay vì gọi `log_error`.
- **D-10 Khoảng trễ đã áp dụng ghi ra logger, không thêm cột nhật ký (A-8).**
  - Vì: không đổi schema `ERP AI Log`, mà vẫn đủ để quan sát.
  - Thay thế: thêm cột `answer_delay_s`.
  - Sai thì: thêm cột Float vào `erp_ai_log.json`, truyền vào `write_entry` của lượt có câu trả lời.
- **D-11 Chỉ báo nổi ở góc dưới phải, gắn vào `body`, kiểu inline, ba chấm bằng Web Animations; luôn hiện một chỉ báo cho lần chạy có tín hiệu mới nhất.**
  - Vì: không phụ thuộc DOM của Helpdesk (A-20); ADR-007 chỉ cho một kênh, nên không có tệp CSS; mobile có luôn mà không thêm việc (A-19).
  - Thay thế: chèn dưới khung soạn như "is typing".
  - Sai thì: chỉ sửa `render()` trong tệp `.js`, rồi chạy `cmd.migrate`.
- **D-12 Khoảng trễ ở module riêng `answer_delay.py`.**
  - Vì: một trách nhiệm mỗi tệp (STD-STRUCT-5); thay đồng hồ trong test mà không đụng `time.monotonic` của `deadline`.
  - Thay thế: hàm riêng trong `runner.py`.
  - Sai thì: gộp vào `runner.py`, giữ tên điểm thay thế.
- **D-13 Thiếu doctype HD Form Script → cảnh báo logger rồi bỏ qua (cả lúc cài và lúc gỡ).**
  - Vì: cùng kiểu `_ensure_task_permission`; `migrate` không được hỏng vì một bước giao diện.
  - Thay thế: ném lỗi.
  - Sai thì: đổi thành `frappe.throw` (STD-ERR-6).
- **D-14 Script bỏ qua tín hiệu không có `expires_in_s` hợp lệ.**
  - Vì: không viết cứng 600 trong JS (ADR-008); một chỉ báo không có hạn có thể kẹt.
  - Thay thế: dùng một hạn mặc định trong JS.
  - Sai thì: thêm hằng mặc định vào script.
- **D-15 Script nhớ `run_id` đã `done` để bỏ qua tín hiệu đến muộn.**
  - Vì: chỉ báo không được hiện lại sau khi đã tắt.
  - Thay thế: không nhớ.
  - Sai thì: bỏ tập `finished`.
- **D-16 Mốc của khoảng trễ là ngay sau tín hiệu bắt đầu, kể cả khi câu chữ rỗng (khi đó là lúc bắt đầu lập luận).**
  - Vì: AC-3/AC-5; một điểm duy nhất trong mã.
  - Thay thế: mốc ngay trước lời gọi model đầu.
  - Sai thì: dời `AnswerDelay.start` xuống `_reason`.

## Việc của người (đội không làm được)
1. **`.team/profile.json`**: thêm `javascript` vào `language` (`notes.language` đã dự trù). Không chặn build: `formatters_by_ext` đã có `.js`, `cmd.format`/`cmd.lint` đã chạy prettier + eslint cho `.js`.
2. **Không có `cmd.test_js` → J1:** phần trang (lọc phiếu, hẹn giờ 600 s, đổi phiếu, ẩn khi `done`) **chỉ kiểm bằng bước tay**. Muốn J2 thì người thêm:
   - slot `cmd.test_js` (ví dụ test runner có sẵn của Node 20 trên bench);
   - quy ước tên tệp test JS vào `naming` (hiện chỉ có `test_{name}.py`).

   Sau đó chạy `/team:plan FEAT-002 --insert` để thêm task test JS cho AC-11 và AC-10 (i). Tệp `.js` đã viết dạng một hàm `setupForm` thuần, nạp được bằng `vm` nếu sau này có J2.
3. **Bước tay sau bàn giao** trên `miyano`, desktop, kết quả từng ý ghi vào `acceptance.md`:
   - **Chuẩn bị:** `bench start` đang chạy, có tiến trình `socketio` (Procfile). Agent bật, mức `L1+`. Một phiếu gửi được cho agent. Mở trang phiếu agent của phiếu đó, mở DevTools Console.
   - **(a)** Gõ comment `@ai <câu hỏi>` → trong vài giây thấy chỉ báo góc dưới phải: "ERP AI" + "Đang suy nghĩ…", rồi "Đang làm: <nhãn>…". Không tải lại trang.
   - **(b)** Câu trả lời hiện ra → chỉ báo mất trong ≤ 10 s.
   - **(c)** Tạm làm hỏng lần chạy trên bản sao, hoặc dùng site không có khóa API hợp lệ → gõ `@ai` → chỉ báo mất trong ≤ 10 s sau khi lần chạy kết thúc.
   - **(d)** Mở cùng phiếu ở trang khách (`/helpdesk/my-tickets/<tên>`) bằng tài khoản khách → không có chỉ báo.
   - **(e)** Đổi "Chữ chỉ báo khi đang suy nghĩ" thành `Đang xử lý thử…`, gõ `@ai` → chỉ báo hiện đúng chuỗi đó. Trả lại giá trị cũ.
   - **(f)** Đổi câu chữ thành `<b>x</b>`, gõ `@ai` → chỉ báo hiện nguyên văn `<b>x</b>`. Trả lại giá trị cũ.
   - **(g)** Mở trang phiếu, danh sách phiếu và vài trang Helpdesk khác khi không có lần chạy nào → không có lỗi mới trong Console.
   - **(h)** Hai phiên (hai tài khoản agent): phiên B thêm comment vào phiếu → phiên A thấy ngay mà không tải lại. Làm cả lúc có và lúc không có lần chạy.
   - **(i)** Gõ `@ai` trên phiếu A, chuyển sang phiếu B rồi về A trong lúc chạy → chỉ có một chỉ báo; trên phiếu B không thấy chỉ báo của A.
   - **AC-11:** gõ `@ai` (để delay 30/30 cho dễ canh), khi thấy chỉ báo thì dừng worker (`Ctrl+C` tiến trình worker của `bench start`) → chỉ báo tự mất chậm nhất 600 s sau khi hiện, và không hiện lại khi tải lại trang. Trả cấu hình về cũ, khởi động lại worker.
   - **Sau mỗi lần nâng Helpdesk hoặc Frappe:** chạy lại (a), (g), (h).
4. **DoD "Helpdesk không bị sửa":** `git -C ../helpdesk status --porcelain` phải đúng bằng 3 dòng gốc ở mục 1.3. Có thêm dòng nào là do FEAT-002.
5. **Production:** xác nhận có tiến trình `socketio` (câu hỏi mở A-2 của FEAT-001). Thiếu nó thì chỉ báo im lặng, lần chạy không đổi.
