# FEAT-007 — design-w1-fixes-15: phán ba điểm của báo cáo 08:00 (T51 → T52–T54)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `review-51.md:32-58`; `tasks.md:199` (mục 4), `:200` (mục 4), `:553-575` (T51–T54); `design.md:427-455` (3.6.3); `spec.md:225-226` (AC-51, AC-52).
- Mã đọc (chỉ đọc, `git show`): `team/FEAT-007-task-51` @ `2288533` — `erp_ai/agent/daily_report.py:1-158`, `erp_ai/agent/test_daily_report.py:36-62` (`_ticket`, `_resolved`), `:211-290`; `team/FEAT-007` — `erp_ai/agent/ops_data.py:11-60`, `erp_ai/agent/routing.py:202-220` (`response_overdue`, `processing_deadline`), `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:88-99`, `:335-347` (`check_ticket_field_names`), `erp_ai/constants.py:65` (`LOGGER_NAME`). Helpdesk cài trên bench @ `a185896`: `helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py:110-111`, `:947-967`; `helpdesk/helpdesk/doctype/hd_service_level_agreement/hd_service_level_agreement.py:272-280`; `helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.json:111-117`.
- Không đổi kiến trúc: theo ADR-001 (`daily_report` thuộc Lõi agent, không import controller — `LAYER_RULES`, đã nêu ở dòng T53 `tasks.md:565`), ADR-033 QĐ 6 (mốc chu kỳ theo lịch), luật AC-10 (`test_feature_never_assigns_sla_dates`: chỉ đọc `resolution_by`, không ghi). Không đổi quy tắc nghiệp vụ; một điểm hiển thị để ngỏ ghi "Q" kèm mặc định (Điểm 3).

---

## Điểm 1 — năm khoảng trống (a)–(e) của T51

### (a) "Phiếu mở" — XÁC NHẬN, sửa docstring
- Phán: phiếu mở = `creation < anchor` ∧ `status_category != "Resolved"`, trạng thái đọc lúc job chạy (đúng mã `daily_report.py:32-34`). `status_category` "Paused" (chờ khách) vẫn là mở: phiếu chưa giải quyết. Hệ quả đã biết, chấp nhận: Helpdesk xóa `resolution_by` khi phiếu vào Paused (`hd_service_level_agreement.py:276-279`), nên phiếu A–C đang Paused không có mốc xử lý → không vào `due_soon`/`overdue`; D/E có Hạn hoàn thành vẫn vào (D-18).
- Lý do không dựng lại "trạng thái tại `anchor`": Helpdesk không giữ lịch sử `status_category` đọc được bằng một truy vấn; phiếu giải quyết trong `[anchor, lúc chạy)` không mất: nó vào `done` của báo cáo hôm sau (cửa sổ hôm sau chứa thời điểm đó). Chỉ `new` và `done` theo cửa sổ; mọi trạng thái khác (mở, `first_responded_on`, BA note, Task) đọc lúc chạy.
- Sửa minor (a) của review (STD-DOC-7) — docstring module `daily_report.py:3-4` thay bằng (chép nguyên văn):
  ```
  Windows come from `anchor` (the cycle's 08:00): "new" means created in `[anchor - 24 h, anchor)`, "done" means
  resolved in that window. Every state is read when the job runs: "open" means created before `anchor` and
  `status_category` not "Resolved"; first response, BA notes and Tasks are read as they are at run time.
  ```

### (b) Dạng đếm `new_by_category_priority` — XÁC NHẬN, thêm một quy tắc
- Phán: `dict[str, dict[str, int]]` = `{category: {priority: count}}`, thưa (chỉ cặp có phiếu; ngày trống → `{}`). Khóa đầu mục: `"A"`…`"F"` hoặc `"?"` (`UNKNOWN_CATEGORY`).
- Thêm: `priority` của HD Ticket không bắt buộc (`hd_ticket.json:111-117`, không có `reqd`) → phiếu có `priority` rỗng/`None` đếm vào khóa ưu tiên `"?"` (cùng hằng `UNKNOWN_CATEGORY`), và phần tử danh sách mang `"priority": "?"`. Lý do: khóa `None` làm `sorted()` ở nơi dựng email ném `TypeError` (so `None` với `str`). Đổi mã → task nối (Điểm 4).

### (c) Dạng phần tử danh sách — XÁC NHẬN, thêm `deadline` cho hai danh sách hạn
- Phán: mọi danh sách (`new_list`, `due_soon`, `overdue`, `response_overdue`, `c_missing_ba_note`, `cd_missing_task`) dùng một dạng:
  - phiếu gửi được: `{"name", "category", "priority", "subject", "excluded": False}`;
  - phiếu loại trừ (A-D5, `policy.can_send_ticket` sai): `{"name", "category", "priority", "excluded": True}` — không `subject`.
- Thêm cho `due_soon` và `overdue`, chỉ phiếu gửi được: khóa `"deadline"` = giá trị `processing_deadline(...)` đã dùng để xếp phiếu vào danh sách (`datetime` naive, giờ site; Hạn hoàn thành kiểu Date thành 23:59:59 của ngày đó theo `routing.as_deadline`). Phiếu loại trừ KHÔNG mang `deadline` (AC-52: phiếu loại trừ chỉ có số đếm và mã phiếu; cùng lối với `subject`). Các danh sách khác không mang `deadline`.
- Lý do: AC-51 nói "còn ≤ 24 giờ tới mốc xử lý hoặc Hạn hoàn thành"; nơi dựng email (T53) cần mốc để in. Đổi mã → task nối (Điểm 4).

### (d) Thứ tự danh sách — XÁC NHẬN
- Phán: mọi danh sách theo `creation asc, name asc` (cũ trước; `name` phá hòa), kể cả `due_soon`/`overdue`. `render_daily_report` (T53) giữ nguyên thứ tự này, không xếp lại. Không đổi mã.

### (e) `done` khi phiếu mở lại — SỬA: thêm điều kiện `status_category = "Resolved"`
- Phán: `de_progress[c]["done"]` = số phiếu đầu mục `c` có `resolution_date` trong `[anchor − 24 h, anchor)` **và** `status_category == "Resolved"` (đọc lúc chạy). `in_progress` = số phiếu mở (định nghĩa (a)) của `c`; `overdue` = số phiếu của `c` trong danh sách `overdue`. Ba số rời nhau ở `done`/`in_progress` theo cấu tạo: `done` đòi Resolved, `in_progress` đòi khác Resolved.
- Lý do: Helpdesk đã xóa `resolution_date` khi phiếu rời Resolved (Điểm 2), nên trên dữ liệu do Helpdesk ghi, điều kiện thêm không đổi số; nó giữ cho `done` và `in_progress` không chồng nhau cả khi dữ liệu được ghi thẳng (nhập liệu, `db_set`, bản Helpdesk khác). Đổi mã → task nối (Điểm 4).

### Ba minor của `review-51.md:43` (tech-lead giao T52 dọn, `review-51.md:58`) — chuyển sang task nối
- minor (a): docstring như (a) trên.
- minor (b) — GIỮ bộ lọc `comment_type: "Comment"` (`daily_report.py:123`): "Comment" của `design.md:447` là bình luận người đọc được; các `comment_type` khác (Info, Assigned, Edit…) là dòng hệ thống. Thêm test có mồi: Comment của `AGENT_USER` bắt đầu bằng `BA_NOTE_MARKER` nhưng `comment_type="Info"` → phiếu vẫn ở `c_missing_ba_note`.
- minor (c): thêm một phiếu loại trừ sắp hạn vào `test_excluded_ticket_number_only_in_every_list` và thêm `"due_soon"` vào bộ khóa của vòng lặp; tên test giữ.
- Ba việc này làm ở task nối T176 (cùng hai file, trước T52), không ở T52.

---

## Điểm 2 — Helpdesk có giữ `resolution_date` khi phiếu mở lại không

### Dữ kiện (Helpdesk @ `a185896`)
- `hd_ticket.py:110-111`: `before_save` gọi `self.set_resolution_date()` mỗi lần lưu.
- `hd_ticket.py:956-967` (`set_resolution_date`):
  ```
  if not self.is_valid_status_transition():
      return
  if self.status_category != "Resolved":
      self.resolution_date = None
      self.resolution_time = None
      return
  if self.resolution_date and not self.has_value_changed("status_category"):
      return
  self.resolution_date = now_datetime()
  ```
- `hd_ticket.py:947-954` (`is_valid_status_transition`): sai khi phiếu mới hoặc `status` không đổi; đổi sang "Closed" từ một trạng thái Resolved khác cũng sai (giữ `resolution_date` cũ).
- `hd_service_level_agreement.py:276-278`: vào trạng thái Paused cũng đặt `doc.resolution_date = None`.

### Kết luận
- KHÔNG giữ. Mở lại (đổi `status` sang trạng thái có `status_category` khác "Resolved", qua `save()`) → `resolution_date = None` ngay lần lưu đó. Giải quyết lại → `resolution_date = now_datetime()` mới. Resolved → Closed giữ mốc cũ (vẫn là một lần giải quyết).
- Báo cáo đếm (với (e)): phiếu D/E giải quyết trong cửa sổ rồi mở lại trước lúc chạy → `done` 0, `in_progress` 1 (và `overdue` 1 nếu quá mốc). Giải quyết lại trước `anchor` → `done` 1, `in_progress` 0. Giải quyết lại trong `[anchor, lúc chạy)` → báo cáo này 0/0, báo cáo hôm sau `done` 1 (đúng (a)). Không có trường hợp một phiếu vừa `done` vừa `in_progress`: Helpdesk bảo đảm khi ghi qua `save()`, điều kiện (e) bảo đảm cả khi dữ liệu ghi thẳng.
- Test (task nối): gieo bằng `frappe.db.set_value` (không qua hook Helpdesk, như `_ticket`) một phiếu D `status="Open"`, `status_category="Open"`, `resolution_date` trong cửa sổ — trạng thái Helpdesk không tự sinh, mô phỏng ghi thẳng → `done` 0, `in_progress` 1. Đỏ trên mã T51 (`done` 1).

---

## Điểm 3 — trường Hạn hoàn thành chưa cấu hình hoặc đã bị gỡ

### Hai ca
1. `field_due_date` rỗng (chưa cấu hình): mã T51 đã đúng (`daily_report.py:28`, `:37`; test `test_no_due_field_uses_resolution_by`). `processing_deadline` nhận `due_at=None` → mọi đầu mục, kể cả D/E, dùng `resolution_by` của Helpdesk (D-18). Phiếu không có `resolution_by` (không SLA, hoặc đang Paused) → không có mốc → không vào `due_soon`/`overdue`, không tính `de_progress.overdue`; vẫn vào `in_progress` nếu là D/E. Không đổi mã.
2. `field_due_date` có tên nhưng trường không còn trên HD Ticket hoặc không còn kiểu Date/Datetime (Custom Field bị xóa/đổi sau lần lưu Setting; lúc lưu `check_ticket_field_names` `erp_ai_setting.py:335-347` đã kiểm): mã T51 ném ở `frappe.get_all` (`review-51.md:49`) và dừng cả báo cáo. Phán: coi như ca 1, báo cáo vẫn dựng.
   - Kiểm lúc dựng, trong `build_daily_report`: `field = frappe.get_meta("HD Ticket").get_field(due_field)` khi `due_field` khác rỗng; `field is None` hoặc `field.fieldtype not in DUE_FIELD_TYPES` → `due_field = None` và một dòng `frappe.logger(LOGGER_NAME).warning("erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, using resolution_by", due_field)` (`LOGGER_NAME` của `erp_ai.constants`), mỗi lần dựng một dòng.
   - `DUE_FIELD_TYPES = ("Date", "Datetime")` là hằng mới trong `daily_report.py`, chú thích một dòng "same rule as the setting's E-2 check; the agent core may not import the controller (ADR-001)". Không import `erp_ai_setting.DUE_FIELD_TYPES` (luật tầng, ADR-001).
   - Không ghi `frappe.log_error`, không đổi Setting (job báo cáo không sửa cấu hình).

### Email hiển thị gì
- Hai ca giống nhau: mục "sắp quá hạn"/"đã quá hạn" và cột mốc của nó (khóa `deadline`, Điểm 1 (c)) in mốc `resolution_by`; phiếu không có mốc không xuất hiện ở hai mục đó. Không có dòng chú thích riêng trong email.
- **Q (cho người, không chặn):** có muốn email in một dòng "Chưa cấu hình trường Hạn hoàn thành: D/E dùng mốc SLA của Helpdesk" khi ca 1 hoặc 2 xảy ra không? Mặc định của designer: KHÔNG (STD-DESIGN-5; spec AC-51 không đòi; ô Setting rỗng đã nhìn thấy trên form; ca 2 có dòng log). Nếu người chọn CÓ: một khóa `due_field_used: bool` thêm vào `build_daily_report` và một dòng ở `render_daily_report` — là một task mới, không sửa T176/T53 đã phán ở đây.

---

## Điểm 4 — task nối (đặt TRƯỚC T52) và dòng thay cho T52–T54

Số `T176` là số kế sau T175 (cao nhất trong `tasks.md`); tech-lead đánh lại số khi dán nếu cần.

### Khối task nối (chép nguyên văn vào `tasks.md`, ngay sau T51, trước T52)
```
- [ ] T176 — Báo cáo 08:00: mốc hạn trong mục, `done` chỉ phiếu Resolved, trường hạn mất không dừng báo cáo — files: erp_ai/agent/daily_report.py, erp_ai/agent/test_daily_report.py — test: erp_ai/agent/test_daily_report.py — depends: T51
  - Chèn (`design-w1-fixes-15.md` Điểm 1 (b), (c), (e), ba minor; Điểm 2; Điểm 3 ca 2). Không thêm file, không thêm khóa của dict.
  - Tiêu chí: AC-51 (mốc của mục sắp/đã quá hạn; tiến độ D/E), AC-52 (phiếu loại trừ chỉ mã phiếu), D-18, A-D5, ADR-001 (`design.md:439-449`; `design-w1-fixes-15.md`).
  - Receives: `build_daily_report` (T51); `routing.processing_deadline`; `erp_ai.constants.LOGGER_NAME`; `frappe.get_meta("HD Ticket").get_field`.
  - Returns: hằng `DUE_FIELD_TYPES = ("Date", "Datetime")` trong `daily_report.py`; phần tử `due_soon`/`overdue` của phiếu gửi được thêm `"deadline": datetime` (giá trị `processing_deadline` đã dùng), phiếu loại trừ không có `deadline`; `priority` rỗng → `"?"` trong `new_by_category_priority` và trong phần tử; `de_progress[c]["done"]` thêm điều kiện `status_category = "Resolved"`; `field_due_date` không phải trường Date/Datetime của HD Ticket → dựng như khi rỗng + một dòng logger warning; docstring module theo `design-w1-fixes-15.md` Điểm 1 (a); giữ `comment_type: "Comment"`.
  - Expect: đỏ trước rồi xanh — `TestBuild::test_due_lists_carry_deadline` (một phiếu A sắp hạn theo `resolution_by`, một phiếu E quá Hạn hoàn thành kiểu Date → `deadline` = `resolution_by` / ngày đó 23:59:59; phiếu loại trừ quá hạn không có khóa `deadline`; đỏ: `KeyError: 'deadline'`), `::test_empty_priority_counted_as_unknown` (phiếu mới `priority=None` → `new_by_category_priority["A"]["?"] == 1`, phần tử `"priority": "?"`), `::test_reopened_ticket_not_done` (Điểm 2: D `status_category="Open"` + `resolution_date` trong cửa sổ → `done` 0, `in_progress` 1; đỏ: `done` 1), `::test_due_field_not_on_ticket_uses_resolution_by` (`frappe.db.set_single_value(SETTING_DOCTYPE, "field_due_date", "erpai_test_no_such_field")` bỏ qua validate; phiếu D có `resolution_by = anchor − 1 h` → trong `overdue` với `deadline` đó, không ném; `self.assertLogs` hoặc vá `frappe.logger` thấy đúng một dòng warning; đỏ: ngoại lệ từ `get_all`), `::test_ba_note_other_comment_type_not_counted` (mồi minor (b); xanh ngay trên mã T51 là chấp nhận: test ghim bộ lọc, đỏ khi bỏ bộ lọc — dev dán đỏ của đột biến bỏ `"comment_type": "Comment"`); `::test_excluded_ticket_number_only_in_every_list` thêm phiếu loại trừ sắp hạn và khóa `"due_soon"`; `::test_twelve_tickets_sections`, `::test_de_progress_window_edges`, `::test_hours_and_days_come_from_settings`, `::test_no_due_field_uses_resolution_by` xanh (kỳ vọng phần tử `due_soon`/`overdue` thêm `deadline` theo thiết kế này — đổi theo spec, STD-TEST-5); `erp_ai/tests/test_architecture.py` xanh (`test_layer_imports`, `test_feature_never_assigns_sla_dates`).
```

### T52 — dòng thay
- Thay `— depends: T51` ở dòng đầu T52 (`tasks.md:559`) bằng `— depends: T176`.
- Thay dòng Receives (`tasks.md:561`) bằng:
  `  - Receives: `build_daily_report` (T51, T176: dạng phần tử và khóa theo `design-w1-fixes-15.md` Điểm 1); ERP AI Log (`actions`, `change_step`, `cost_usd`, `error`).`
- Returns, Expect: không đổi. Ba minor của `review-51.md` KHÔNG còn là việc của T52 (đã ở T176).

### T53 — dòng thay
- Thay dòng Receives (`tasks.md:567`) bằng:
  `  - Receives: `build_daily_report` (T52; dạng dữ liệu theo `design-w1-fixes-15.md` Điểm 1: phần tử `{name, category, priority, excluded, subject?}`, `due_soon`/`overdue` của phiếu gửi được thêm `deadline: datetime`; đếm thưa `{category: {priority: count}}` với khóa `"?"`); `redact_secrets` (T35); `daily_cycle` (T41); `coo_report_recipients`, `daily_report_sent_on` (T16).`
- Thay dòng Returns (`tasks.md:568`) bằng:
  `  - Returns: `render_daily_report(data) -> str` (phiếu gửi được: `#<name>`, đầu mục, ưu tiên, `subject` qua `redact_secrets` rồi `escape_html`; ở `due_soon`/`overdue` thêm mốc `deadline` dạng `%d/%m/%Y %H:%M`; phiếu loại trừ chỉ `"#<name> (nhóm loại trừ)"`, không đầu mục, ưu tiên, tiêu đề hay mốc; danh sách giữ thứ tự của dữ liệu; bảng đếm: đầu mục theo `CATEGORIES` rồi `"?"`, ưu tiên theo tên tăng dần rồi `"?"`, ô không có phiếu in 0; danh sách rỗng in "Không có"); `run_daily_report(now=None) -> None` (bước 1–6, 8; chỗ ghi duy nhất của `daily_report_sent_on` bằng `frappe.db.set_single_value`, cùng giao dịch với `frappe.sendmail(..., delayed=True)`).`
- Thay dòng Expect (`tasks.md:569`) bằng:
  `  - Expect: `TestRun::test_twice_same_day_one_email`, `::test_empty_day_sends_zeros`, `::test_excluded_ticket_number_only_no_subject` (phiếu loại trừ quá hạn có tiêu đề gieo: HTML không chứa tiêu đề và không chứa mốc `%d/%m/%Y %H:%M` của nó), `::test_secret_in_subject_redacted`, `::test_due_lists_show_deadline` (phiếu gửi được sắp hạn: HTML chứa mốc `%d/%m/%Y %H:%M`) xanh.`
- Dòng "Chèn 4" (`tasks.md:565`) giữ nguyên.

### T54 — không đổi
- Lý do: Điểm 3 ca 2 không còn ném từ `build_daily_report`, nên nhánh lỗi của T54 (bước 7, `design.md:436`: chỉ `frappe.ValidationError`/`frappe.OutgoingEmailError` ở bước gửi) giữ nguyên; Receives/Returns/Expect và dòng "Chèn 4" (`tasks.md:571-575`) giữ.

### Dòng thay trong `design.md` (cho As-Built; tech-lead dán cùng lúc với `tasks.md`)
- `design.md:445` — thay cột "Nội dung" bằng: `phiếu đang mở có `processing_deadline` trong `(anchor, anchor + due_reminder_hours]` / `≤ anchor`; phần tử của phiếu gửi được thêm `deadline` (design-w1-fixes-15 Điểm 1 (c)); trường hạn không còn là Date/Datetime của HD Ticket → như chưa cấu hình + log (Điểm 3)`.
- `design.md:449` — thay `` `done` (Resolved trong cửa sổ) `` bằng `` `done` (`resolution_date` trong cửa sổ và `status_category` = Resolved; design-w1-fixes-15 Điểm 1 (e), Điểm 2) ``.
- Sau `design.md:453` thêm một câu: `Phiếu mở = tạo trước anchor và status_category khác Resolved, đọc lúc chạy (Paused là mở); mọi danh sách theo creation asc, name asc; ưu tiên rỗng → "?" (design-w1-fixes-15 Điểm 1).`

---

## Đối chiếu
- Touchpoint mới: 0 (T176 chỉ sửa hai file T51 đã tạo, dưới `erp_ai/agent/`). Không file nào thuộc `protected_paths`.
- AC chạm: AC-51 → `test_due_lists_carry_deadline`, `test_reopened_ticket_not_done`, `test_empty_priority_counted_as_unknown`, `test_due_field_not_on_ticket_uses_resolution_by`, `test_due_lists_show_deadline`; AC-52 → `test_due_lists_carry_deadline` (phiếu loại trừ không `deadline`), `test_excluded_ticket_number_only_in_every_list` (+`due_soon`), `test_excluded_ticket_number_only_no_subject` (+mốc); AC-58 (BA note) → `test_ba_note_other_comment_type_not_counted`.
- Không lựa chọn nào còn mở ngoài Q ở Điểm 3 (đã có mặc định). Không `DESIGN_CONFLICT`.
