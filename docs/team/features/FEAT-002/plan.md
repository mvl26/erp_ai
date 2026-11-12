Feature: FEAT-002
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-002

- Nhánh feature: `team/FEAT-002`, tạo từ `team/FEAT-001` (spec Constraints: "nền `team/FEAT-001`"). Lý do không dùng `config.base_branch = main`: ref `main` không tồn tại trong repo này (`git log main` báo lỗi), và mã FEAT-001 chỉ có trên nhánh `team/FEAT-001`. Nhánh `team/BUG-001` chứa thêm sửa gateway mà FEAT-002 không chạm; team-leader quyết nếu muốn nền khác.
- Số task: 10; song song tối đa: 2 (`limits.max_parallel_dev`).
- Cỡ L. Cổng áp dụng: chỉ G5 (`team.py status`), nên G3 không chặn build. `design.md` còn dòng `Approved-by:` trống, không chặn.

## Shared constraints
Sao nguyên văn từ spec/design; mọi task thừa hưởng.
- Sự kiện: `AGENT_STATUS_EVENT = "erp_ai:agent_status"`; phòng `doc:HD Ticket/<tên>` qua `frappe.realtime.get_doc_room`; phát bằng `frappe.publish_realtime(..., room=room, after_commit=False)`.
- Payload đúng 7 khóa theo thứ tự `PAYLOAD_KEYS`: `ticket_id`, `run_id`, `agent_user`, `agent_name`, `state` (`thinking`|`working`|`done`), `text`, `expires_in_s` (= `JOB_TIMEOUT_S`).
- Trường cấu hình: `thinking_text` (mặc định `Đang suy nghĩ…`, ≤ 5000 ký tự, rỗng/khoảng trắng = tắt chỉ báo, lưu `""` không phải `NULL`), `answer_delay_min_s` = 3, `answer_delay_max_s` = 5, cận 0..`ANSWER_DELAY_MAX_S` = 30, min ≤ max.
- Thông báo lỗi (so đúng chuỗi): `Trễ trả lời tối thiểu phải từ 0 đến 30`; `Trễ trả lời tối đa phải từ 0 đến 30`; `Trễ trả lời tối thiểu không được lớn hơn trễ trả lời tối đa`; `Chữ chỉ báo khi đang suy nghĩ không được dài quá 5000 ký tự`.
- Hằng: `TITLE_STATUS_FAILED = "erp_ai: chỉ báo trạng thái lỗi"`; `AGENT_STATUS_SCRIPT = "ERP AI Agent Status"`; `FALLBACK_WORK_LABEL = "xử lý yêu cầu"`; `WORKING_TEXT = "Đang làm: {label}…"`.
- Không ghi bản ghi nào để hiện chỉ báo; không sửa `apps/helpdesk`; không thêm lời gọi model; ADR-004 giữ nguyên.
- Chuỗi `HD Form Script` chỉ có trong `erp_ai/install.py`; `publish_realtime` chỉ có trong `erp_ai/agent/run_status.py`.
- Test: không chạm Redis thật, không `time.sleep` thật (patch `emit_via_redis`, `answer_delay._sleep`); không skip/xfail (STD-TEST-4).
- Mỗi task: đỏ đúng lý do trước, xanh sau, dán cả hai đầu ra `cmd.test_one`; `cmd.format` cho file đã sửa.

## Thứ tự
1. T1: walking skeleton. Chạy qua runner → `RunStatus` → `publish_realtime` (patch `emit_via_redis`) → bộ ghi tín hiệu, với `done` trong `finally`. Mạo hiểm nhất nên làm trước: kiểu phát `after_commit=False` và chỗ đặt `try/finally` trong `_run`. Không task nào khác bắt đầu trước khi review T1 là `approve`.
2. {T2, T3}: cấu hình và khoảng trễ, hai khối độc lập (không chung file).
3. T4: nối khoảng trễ, cô lập test cũ khỏi Redis/`sleep` (cần T2 để đặt trường, T3 để có module).
4. T5 → T6 → T7: cùng chung `runner.py` và `test_runner_status.py`, nên tuần tự: nhãn "đang làm" và `ticket_insert`; mọi nhánh kết thúc kèm rollback; lỗi khi phát.
5. T8 → T9 → T10: phần giao diện và cài đặt; T8 chỉ cần T1; T9 cần T2 (cùng `test_install.py`) và T8 (tệp `.js`); T10 chốt luật kiến trúc, cần T7 và T9.

## Nhóm song song
- {T2, T3} (không chung file).
- {T4, T8} (T8 chỉ chạm `public/js/agent_status_indicator.js` và `tests/test_architecture.py`).
- {T5, T9} (T5: `run_status.py`, `runner.py`, `test_run_status.py`, `test_runner_status.py`; T9: `install.py`, `hooks.py`, `test_install.py`).
- T6, T7, T10: chạy một mình. Không đủ điều kiện chạy chung vì T6/T7 chung file với T5, T10 chung `test_architecture.py` với T8.

## Bảng một file, một chủ
| File | Task chủ (theo thứ tự sửa) |
|---|---|
| `erp_ai/constants.py` | T1 |
| `erp_ai/test_utils.py` | T1 |
| `erp_ai/agent/run_status.py` | T1, T5, T7 |
| `erp_ai/agent/runner.py` | T1, T4, T5, T6, T7 |
| `erp_ai/agent/test_runner_status.py` | T1, T4, T5, T6, T7 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | T2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | T2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | T2 |
| `erp_ai/agent/answer_delay.py`, `erp_ai/agent/test_answer_delay.py` | T3 |
| `erp_ai/agent/test_agent_runner.py`, `erp_ai/tests/test_handlers.py` | T4 |
| `erp_ai/agent/test_run_status.py` | T5, T7 |
| `erp_ai/public/js/agent_status_indicator.js` | T8 |
| `erp_ai/tests/test_architecture.py` | T8, T10 |
| `erp_ai/tests/test_install.py` | T2, T9 |
| `erp_ai/install.py`, `erp_ai/hooks.py` | T9 |

Mọi file có chủ khác nhau chỉ được sửa tuần tự theo `depends:`.

## Touchpoint → task
| Touchpoint (`design.md` mục 7) | Task |
|---|---|
| `erp_ai_setting.json`, `erp_ai_setting.py`, `test_erp_ai_setting.py` | T2 |
| `constants.py` | T1 |
| `agent/run_status.py` | T1, T5, T7 |
| `agent/answer_delay.py` | T3 |
| `agent/runner.py` | T1, T4, T5, T6, T7 |
| `install.py`, `hooks.py` | T9 |
| `public/js/agent_status_indicator.js` | T8 |
| `test_utils.py` | T1 |
| `agent/test_agent_runner.py`, `tests/test_handlers.py` | T4 |
| `tests/test_install.py` | T2, T9 |
| `agent/test_run_status.py` | T5, T7 |
| `agent/test_answer_delay.py` | T3 |
| `agent/test_runner_status.py` | T1, T4, T5, T6, T7 |
| `tests/test_architecture.py` | T8, T10 |

15/15 touchpoint có task, không dòng trống.

## AC → task
| Tiêu chí | Task | Ghi chú |
|---|---|---|
| AC-1 | T2 | |
| AC-2 | T1, T5 | T5: `ticket_insert` |
| AC-3 | T3, T4 | |
| AC-4 | T1, T6 | T1: nhánh có câu trả lời; T6: mọi nhánh |
| AC-5 | T4, T5 | |
| AC-6 | T4 | |
| AC-7 | T7 | |
| AC-8 | T4; `cmd.test` ở checkpoint cuối | |
| AC-9 | T5 | |
| AC-10 | T8 (test tĩnh) + bước tay của người | `ui: false`, A-21 |
| AC-11 | T8 (test tĩnh) + bước tay của người | J1 |
| AC-12 | T9 | kèm đầu ra `cmd.migrate` ở checkpoint cuối |
| NFR-1, NFR-2 | T2, T3 | |
| NFR-3 | T4 | |
| NFR-4' | T1, T5, T7 | |
| NFR-5 | T6 | bước tay (b), (c) |
| NFR-6 | T6, T10 | |

12/12 AC có ít nhất một task.

## Checkpoint
- Sau T1: review `approve` mới mở khóa các task khác; `cmd.test` xanh trên `team/FEAT-002`.
- Sau T3 (kết thúc nhóm {T2, T3}): `cmd.test` xanh.
- Sau T7 (cả đường runner xong): `cmd.test` xanh; chuỗi tín hiệu ở `design.md` 4.1 bước 6 và 4.2 bước 4–5 chạy được.
- Sau T10 (cuối): `cmd.test` xanh toàn app; `cmd.lint` sạch (gồm tệp `.js`); `cmd.migrate` chạy được trên `miyano` (3 trường mới có mặc định, đúng 1 bản ghi `ERP AI Agent Status`), đầu ra dán vào `acceptance.md`; `git -C ../helpdesk status --porcelain` đúng 3 dòng gốc ở `design.md` 1.3.
- Phần hiển thị trên trang (AC-10, AC-11) là bước tay của người sau bàn giao, không nằm trong task nào.

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| `try/finally` trong `_run` đổi hành vi hiện có (ngoại lệ vẫn phải lan tới `run_for_ticket`) | test cũ trong `test_agent_runner.py` đỏ ở T1 | T1 chạy cả `test_agent_runner.py` và `test_handlers.py`; không đổi chữ ký `_run` |
| Test cũ publish thật lên Redis giữa T1 và T4 | log kết nối Redis, test chậm | `emit_via_redis` nuốt `ConnectionError`; T4 vá toàn bộ setUp; chấp nhận tạm thời |
| `test_architecture.py` (`LAYER_RULES`) đỏ khi thêm module mới | `test_architecture` đỏ ở T1 hoặc T3 | dev sửa `LAYER_RULES` trong task đó, ghi chú trong báo cáo; nếu thêm file thứ 6 vào task thì báo `NEEDS_CONTEXT` |
| Chạy trên site `miyano` có Redis thật khác môi trường test | tín hiệu lọt ra ngoài khi dev quên patch | `record_status_signals` là bắt buộc trong mọi test runner mới |
| Script JS không có test tự động | lỗi chỉ lộ ở bước tay | test tĩnh T8 + bước tay AC-10; nếu người thêm `cmd.test_js` thì `/team:plan FEAT-002 --insert` (A-21) |
| T9 sửa bản ghi HD Form Script trên site thật khi chạy test | bản ghi đổi sau `cmd.test` | `setUp` của `test_install.py` chạy trong giao dịch và rollback; kiểm `modified` sau `cmd.test` |

## Review focus
Các đầu vào/lỗi mà spec ngụ ý nhưng task cần có test (đã gắn vào task chủ):
1. Câu chữ chỉ có khoảng trắng (`"   "`) coi như rỗng: 0 tín hiệu, vẫn chờ (T4, T2).
2. Giá trị cấu hình ngoài cận khi ghi thẳng DB, không qua form: kẹp [0, 30], đổi chỗ nếu min > max (T3).
3. Tên tool do model bịa chứa chuỗi đánh dấu: `text` = nhãn dự phòng (T5).
4. `post_comment` và `set_classification` cùng lượt: chờ trước tool đầu của lượt (D-6) và `done` vẫn là tín hiệu cuối khi rollback (T4, T6).
5. `setupForm` chạy lại nhiều lần trên cùng trang: không đăng ký trùng listener (T8: test tĩnh cờ `state.socket`; bước tay AC-10 (i)).

## Walking skeleton (cỡ L)
T1 chạy từ lời gọi `run_for_ticket` (`comment_mention`, `L1`) qua `_run` → `RunStatus.start()` → `frappe.publish_realtime` → `frappe.realtime.emit_via_redis` (bị patch, đi đúng đường thật) → bộ ghi tín hiệu của test, rồi `finally: status.done()` sau commit cuối. Phần "lõi" được giả: chưa có khoảng trễ, chưa có nhãn "đang làm", chưa có cấu hình mới (T1 đọc `thinking_text` qua `settings.get("thinking_text")` nên chưa đòi T2: test T1 gán trực tiếp, hoặc để mặc định `RunStatus(thinking_text=...)`). Bằng chứng: hai test `test_start_signal_before_first_model_call` và `test_done_last_when_answered` chạy bằng `cmd.test_one`; trang (JS) và cài đặt nằm ngoài skeleton vì là bước tay/đường độc lập (T8, T9).
