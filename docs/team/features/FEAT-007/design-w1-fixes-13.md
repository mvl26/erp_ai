# FEAT-007 — design-w1-fixes-13: phán ba phát hiện pre-flight U4b (G-1, G-10, G-11)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu. Không chặn build.
- Đầu vào: `preflight-w1-u4b.md:25`, `:34`, `:35` (G-1, G-10, G-11); `tasks.md:841-860` (T95, T96, T98), `:961-965` (T119), `:1193` (T168), `:1198-1202` (T169); `design-addendum-1-U4b-U8.md:117`; `design-addendum-1-U4b-U8-fixes.md:53`, `:96`, `:313`, `:476`; `docs/team/adr/ADR-037.md:75-85` (và `:58-60`, QĐ 4); `design-addendum-3-w1.md:59`, `:203`; `arch-review-design-addendum-3.md:173` (AD3-6).
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `caa555a` — `erp_ai/agent/tools/test_write_ticket.py:14`, `:58`, `:68-84`, `:86-102`, `:163-173`, `:213-224`, `:542-614`; `erp_ai/handlers.py:1-82`; `erp_ai/install.py:76-91` (`_ensure_agent_user`); `erp_ai/agent/tools/test_route_ticket.py:108`, `:199`, `:274` (tiền lệ test tool chạy dưới `AGENT_USER`); `erp_ai/tests/test_architecture.py:88-102` (`LAYER_RULES`), `:529` (`check_layer_imports(sources: dict, …)`), `:4548` (khóa `sources` = `path.relative_to(PACKAGE_ROOT)`), `:5599` (ví dụ khóa `"agent/tools/write_ticket.py"`); `erp_ai/constants.py:1`, `:14-15`, `:54` (100 dòng, 0 import); `erp_ai/agent/runner.py` hàm `_route`; `erp_ai/agent/changes/transitions.py:140-153` (`_lock`). `develop` và `team/CHG-002`: `git grep for_update` ngoài test → chỉ `erp_ai/agent/changes/transitions.py` (`:149` trên `develop`; `:198` trên `team/CHG-002`, vẫn trong `def _lock(name, *extra)`). `write_ticket.py`, `runner.py` của `team/FEAT-007`: 0 `for_update` (T99 chưa merge).
- Không đổi kiến trúc, không đổi quy tắc nghiệp vụ. Theo ADR-001 (`LAYER_RULES`), ADR-033 (handler không import `write_ticket`), ADR-036 QĐ 4, ADR-037 QĐ 4 và Ràng buộc, AD3-6. Danh tính của agent là phiên `AGENT_USER` (`U4b.md:117`, Returns của T96 "ghi dưới `AGENT_USER` không thành Người"). Không có `DESIGN_CONFLICT`.

---

## Điểm 1 — G-1: test `set_classification` dưới tài khoản không phải `AGENT_USER`

### Hiện trạng (dữ kiện)
- `TestWriteTicket._run(user, …)` (`test_write_ticket.py:81-84`) đặt phiên `user` rồi gọi `write_ticket.set_classification`. Hai test khẳng định dấu AI sau một lần ghi thành công dưới `AGENT` (`t25.agent@example.com`, do `create_agent(AGENT)` tạo, `:58`): `test_agent_writes_mapped_fields_and_ai_marks` (`:89` gọi, `:93` khẳng định `CLASSIFIED_BY_AI`) và `test_mapping_to_missing_value_skips_field` (`:166` gọi, `:173` khẳng định).
- Sau T96, `ticket_validate` vế (2): phiếu không mới, trường phân loại đổi, phiên ≠ `AGENT_USER`, chưa có dòng `classify` có dự đoán → `ai_classified_by = Người`. Hai khẳng định trên sai. Hôm nay nhánh đó là `skip_reason = "no_prediction"` (`handlers.py:73-79`).
- Mọi lần gọi `set_classification` thành công khác trong file (`:177`, `:183`, `:190`, `:195`, `:223`, `:590`, `:601`, `:612`) không khẳng định `ai_classified_by` → không đỏ (`git grep CLASSIFIED_BY_AI`: chỉ `:14`, `:93`, `:173`).
- `AGENT_USER` có trên mọi site đã cài (`install.py:76-91`, vai trò `ROLE_AGENT` và vai trò agent Helpdesk). `test_route_ticket.py` đã chạy tool ghi HD Ticket dưới `AGENT_USER` (`:108`, `:199`, `:274`, …).

### Phán quyết
1. **Test đổi sang phiên `AGENT_USER`; vế (2) của hook KHÔNG thêm điều kiện.** Lý do: danh tính "agent ghi" chỉ có một nguồn là phiên (`U4b.md:117`, `handlers.py:70`); một điều kiện thứ hai (cờ trên doc, hay "`ai_classified_by` vừa đổi thành AI") là một lối thứ hai để một lần ghi không bị tính là người, mà mã nào trong tiến trình cũng đặt được, và mở đúng lỗ AC-21 đang bịt. Trong vận hành, tool chỉ chạy dưới `AGENT_USER` (runner đặt phiên), nên test dưới `AGENT` không mô tả đường thật.
2. Phạm vi sửa trong `erp_ai/agent/tools/test_write_ticket.py`, đúng hai dòng, không đổi khẳng định nào:
   - `:89` `result = self._run(AGENT)` → `result = self._run(AGENT_USER)`
   - `:166` `result = self._run(AGENT, mapping)` → `result = self._run(AGENT_USER, mapping)`
   `AGENT_USER` đã được import (`:14`). Các lần gọi còn lại giữ `AGENT` (không khẳng định dấu; ca từ chối quyền ở `:104-152` cần tài khoản thử của chúng).
3. Luật cho mọi test mới của U4b/U8 gọi `set_classification` (hoặc `execute_tool("set_classification", …)`) và khẳng định `ai_classified_by == CLASSIFIED_BY_AI`: chạy dưới `frappe.set_user(AGENT_USER)`. Áp ngay cho test mới của T98 (`TestHumanFields`, `TestConfidenceSource`).
4. **Chủ của thay đổi: T98** (đang giữ `test_write_ticket.py`, chuỗi T98 → T104; không thêm file vào T96). Hai dòng đổi xanh cả trước và sau T96 (trước T96 hook bỏ qua với `changed_by_agent`). **T96 thêm `depends: T98`**, để vế (2) không vào nhánh feature trước khi hai test đã đổi phiên. Không vòng: T98 không phụ thuộc T96. Chuỗi "Một file, một chủ" của `test_write_ticket.py` và của `handlers.py`/`test_handlers.py` không đổi thứ tự.

### Dòng thay trong `tasks.md` (chép nguyên văn)

`tasks.md:846` (dòng tiêu đề T96) — thay cả dòng bằng:
```
- [ ] T96 — Người sửa trường trước dòng phân loại đầu tiên vẫn được ghi là người — files: erp_ai/handlers.py, erp_ai/tests/test_handlers.py — test: erp_ai/tests/test_handlers.py — depends: T95, T98
```

`tasks.md:847` (Tiêu chí của T96) — thay cả dòng bằng:
```
  - Tiêu chí: AC-21; `U4b.md:117` (`ticket_validate` vế (2), lý do ghi `human_changed_before_prediction`); test FEAT-001/006 ghim "chưa có dự đoán → bỏ qua" sửa theo AC (NFR-8). Vế (2) chỉ xét phiên (`AGENT_USER`), không thêm điều kiện nào khác; test `test_write_ticket.py` khẳng định dấu AI đã chuyển sang phiên `AGENT_USER` ở T98 (`design-w1-fixes-13.md` Điểm 1).
```

`tasks.md:857` (Tiêu chí của T98) — thay cả dòng bằng:
```
  - Tiêu chí: AC-21, AC-22 (W-2); `U4b.md` mục 3.2 phần U4b (dòng 124–150) với `U4b-fixes.md` Fix 2 (dòng 81–104); `design-w1-fixes-13.md` Điểm 1 (test khẳng định `CLASSIFIED_BY_AI` chạy dưới `AGENT_USER`: `test_write_ticket.py:89` `self._run(AGENT)` → `self._run(AGENT_USER)`, `:166` `self._run(AGENT, mapping)` → `self._run(AGENT_USER, mapping)`; test mới của task này cũng vậy).
```

`tasks.md:860` (Expect của T98) — thay cả dòng bằng:
```
  - Expect: `TestHumanFields::test_set_classification_skips_created_fields`, `::test_invalid_created_labels_write_none_of_three`; `TestConfidenceSource::test_set_classification_never_writes_confidence_pct`, `::test_set_classification_schema_has_no_confidence_pct` xanh; `TestWriteTicket::test_agent_writes_mapped_fields_and_ai_marks`, `::test_mapping_to_missing_value_skips_field` chạy dưới `AGENT_USER` và xanh, khẳng định không đổi.
```

---

## Điểm 2 — G-10: `CREATED_LABELS_FIELD` nằm ở đâu

### Hiện trạng (dữ kiện)
- `LAYER_RULES` (`test_architecture.py:88-99`, ADR-001): `erp_ai.agent` (cả `erp_ai.agent.tools`) không import `erp_ai.handlers`. Luật T119 `test_handlers_do_not_import_write_ticket` (ADR-033) cấm chiều ngược lại.
- Người đọc tên trường: `handlers.py` (T95, T96), `agent/tools/write_ticket.py` (T98, `U4b-fixes.md:96`), `agent/runner.py` (T108).
- `erp_ai/constants.py` là module lá (0 dòng import, A-D6), đã giữ các tên dùng chung của handler và agent: `AGENT_USER` (`:1`), `CLASSIFIED_BY_AI`/`CLASSIFIED_BY_HUMAN` (`:14-15`), `CLASSIFICATION_FIELDS` (`:54`). Cả hai tầng import được nó.

### Phán quyết
1. **`CREATED_LABELS_FIELD = "ai_created_labels"` đặt ở `erp_ai/constants.py`**, ngay sau `CLASSIFICATION_FIELDS` (`:54`), không đặt ở cuối file (khối catalog cuối file của F-1 giữ liền). Module vẫn 0 dòng import. Không viết chuỗi ở hai nơi (hai nguồn sự thật, STD-DESIGN-4).
2. `CREATED_LABELS_FLAG = "erp_ai_created_labels"` **ở lại `erp_ai/handlers.py`**: chỉ `ticket_before_insert` và `ticket_validate` dùng (cờ trong bộ nhớ của doc đang lưu).
3. Người dùng import: `handlers.py`, `agent/tools/write_ticket.py` (T98), `agent/runner.py` (T108) đều `from erp_ai.constants import CREATED_LABELS_FIELD`. Không file nào import tên này từ `erp_ai.handlers`.
4. `erp_ai/install.py:203` (chuỗi `"ai_created_labels"` trong spec trường của T60, đã merge) không đổi: install không thuộc U4b; không thêm file.
5. Thiết kế bị thay: `U4b-fixes.md:53` (khối mã mục 3.1: dòng `CREATED_LABELS_FIELD = …` bỏ, thay bằng chú thích `# CREATED_LABELS_FIELD: erp_ai/constants.py (design-w1-fixes-13 Điểm 2)`); `:476` cột Module của hàng `CREATED_LABELS_FIELD, CREATED_LABELS_FLAG` → "`CREATED_LABELS_FIELD`: `erp_ai/constants.py`; `CREATED_LABELS_FLAG`: `erp_ai/handlers.py`"; `:313` câu "Không sửa: … `constants.py` …" bỏ `constants.py` khỏi danh sách (T95 sửa nó, một dòng).
6. `files:` của T95 thêm `erp_ai/constants.py`. Team-leader đặt T95 vào chuỗi "Một file, một chủ" của `constants.py` (chủ đang mở: T126, T140); điều kiện "không nhánh task nào đang mở trên file của `files:`" của T126 áp như chữ của T126.

### Dòng thay trong `tasks.md` (chép nguyên văn)

`tasks.md:841` (dòng tiêu đề T95) — thay cả dòng bằng:
```
- [ ] T95 — Tập trường người gõ lúc tạo phiếu được lưu vào `ai_created_labels` — files: erp_ai/constants.py, erp_ai/handlers.py, erp_ai/tests/test_handlers.py — test: erp_ai/tests/test_handlers.py — depends: T75, T60
```

`tasks.md:844` (Returns của T95) — thay cả dòng bằng:
```
  - Returns: `erp_ai/constants.py`: `CREATED_LABELS_FIELD = "ai_created_labels"` ngay sau `CLASSIFICATION_FIELDS` (file giữ 0 dòng import); `erp_ai/handlers.py`: `CREATED_LABELS_FLAG = "erp_ai_created_labels"`, `CREATED_LABELS_FIELD` import từ `erp_ai.constants` (`design-w1-fixes-13.md` Điểm 2); lấy ở `before_insert` vào cờ, ghi ở `validate` khi `is_new()`, giữ cố định ở các lần `validate` sau. Handler không `save()`, không `db.set_value` HD Ticket.
```

`tasks.md:845` (Expect của T95) — thay cả dòng bằng:
```
  - Expect: `TestCreatedLabels::test_insert_records_typed_fields_only`, `::test_customer_portal_insert_records_typed_fields`, `::test_user_without_level8_insert_records_typed_fields`, `::test_level8_user_client_value_overwritten`, `::test_only_values_still_on_ticket_recorded`, `::test_created_labels_frozen_after_insert` xanh; `test_architecture.py` (luật tầng ADR-001, `constants.py` 0 import) xanh; ngoài file `test_*.py`, chuỗi `"ai_created_labels"` chỉ có ở `erp_ai/constants.py` và `erp_ai/install.py`.
```

`tasks.md:858` (Receives của T98) — thay cả dòng bằng:
```
  - Receives: `ai_created_labels` trên phiếu (T95); `CREATED_LABELS_FIELD` import từ `erp_ai.constants`, không từ `erp_ai.handlers` (`LAYER_RULES`, ADR-001; `design-w1-fixes-13.md` Điểm 2).
```

Ghi cho T108 (không thay dòng, dòng T108 không nêu nơi import): runner đọc trường qua `from erp_ai.constants import CREATED_LABELS_FIELD`.

---

## Điểm 3 — G-11: phạm vi quét của hai luật khóa của T119

### Hiện trạng (dữ kiện)
- ADR-037 Ràng buộc (`:82`): "AST: `_route` gọi hàm trợ giúp khóa trước đơn vị ghi đầu tiên. Ngoài hàm trợ giúp đó không có `for_update=True` **mới**." ADR-037 QĐ 4 (`:58`): hàm trợ giúp là của ADR-036 QĐ 4; AD3-6: `locked_rows` là chỗ duy nhất có `for_update=True` của ADR-036 QĐ 4, `locked_count` gọi nó.
- `w1.md:203`: `test_dedup_reads_go_through_locked_count` = "`post_notice`, `ba_note`, `create_task`, `post_guidance` không tự khóa/đọc". `create_task` chống trùng (T168) và nhánh `ba_note` của `post_comment_tool` (T169) thuộc U8, sau T119. Expect của T168 (`tasks.md:1193-1197`) đòi luật này xanh; T169 (`:1198-1202`) không nêu luật. `files:` của cả hai không có `erp_ai/tests/test_architecture.py`.
- `for_update` ngoài test, ở mọi nhánh: chỉ `erp_ai/agent/changes/transitions.py`, trong `def _lock` (khóa dòng ERP AI Change Proposal, D-2 của FEAT-004; `:149` trên `team/FEAT-007` và `develop`, `:198` trên `team/CHG-002`). Không phải khóa HD Ticket, có trước ADR-036/037 → không "mới".
- Hàm `_route` (`runner.py`) hôm nay gọi theo thứ tự: `frappe.db.savepoint`, `_apply_route_unit`, `_check_sla`, `_assign_unit`, `_task_unit`, `_comment_unit`, `_record_route`, `frappe.db.commit`.

### Phán quyết
Hai luật, mỗi luật một hàm `check_*(sources: dict) -> list` theo quy ước của `check_layer_imports`: khóa của `sources` là đường dẫn tương đối với `PACKAGE_ROOT` (gói `erp_ai/`), ví dụ `"agent/tools/write_ticket.py"` (`test_architecture.py:4548`, `:5599`). Các tên tập dưới đây là hằng cấp module trong `test_architecture.py`.

**Luật A — `test_dedup_reads_go_through_locked_count`** (ADR-036 QĐ 4, `w1.md:203`)
- File quét: **chỉ** khóa `"agent/tools/write_ticket.py"`.
- Hàm quét ở T119: `DEDUP_WRITERS = ("post_notice", "post_guidance")`. Mở rộng sau (mỗi lần trong cùng commit với mã chống trùng của nó): T168 nối `"create_task"`, T169 nối `"post_comment_tool"` (handler chứa nhánh `ba_note`). Hai task đó vì vậy cần `erp_ai/tests/test_architecture.py` trong `files:`; team-leader phán `files:` và chỗ trong chuỗi chủ của `test_architecture.py`. Luật không đổi, chỉ bộ tên dài thêm.
- Với mỗi tên trong bộ: (a) hàm không có trong file → vi phạm `"<tên>: không thấy hàm"`; (b) thân hàm không có lời gọi `locked_count(...)` nào và không có `count_guidance(..., lock=True)` → vi phạm; (c) thân hàm có lời gọi `frappe.db.count`, `frappe.db.exists`, `frappe.db.get_values`, `frappe.db.get_all`, `frappe.get_all`, `frappe.get_list`, `frappe.db.sql`, hoặc có `keyword(arg="for_update")` → vi phạm. `frappe.db.get_value` (đọc một trường của một doc) không bị bắt.
- Ngoài phạm vi: mọi file khác, mọi hàm khác của `write_ticket.py` (gồm `count_guidance` nhánh `lock=False` của runner, `locked_rows`, `locked_count`). Luật "chỉ `locked_rows` có `for_update` trong `write_ticket.py`" là của T99 (`test_locked_count_queries_use_for_update`), không lặp ở đây.

**Luật B — `test_route_locks_ticket_before_first_write_unit`** (ADR-037 Ràng buộc `:82`, hai câu)
- (B1) Thứ tự trong `_route`. File: **chỉ** khóa `"agent/runner.py"`, hàm `_route`. Lời gọi khóa: tên (`Name.id` hoặc `Attribute.attr`) thuộc `ROUTE_LOCK_CALLS = ("locked_count", "locked_rows")`. Đơn vị ghi: lời gọi có tên kết thúc bằng `_unit`, hoặc thuộc `ROUTE_WRITE_CALLS = ("_record_route", "execute_tool", "set_value", "save", "insert", "db_set", "sql")`. Vi phạm khi: không có lời gọi khóa; không có đơn vị ghi nào (luật không được xanh rỗng); hoặc `(lineno, col_offset)` của lời gọi khóa đầu tiên không nhỏ hơn của đơn vị ghi đầu tiên. `frappe.db.savepoint` không là đơn vị ghi. `sources` không có khóa `"agent/runner.py"` → B1 trả 0 vi phạm (chỉ xảy ra ở chuỗi mẫu).
- (B2) Không `for_update=True` mới. File quét: mọi khóa của `sources` (mọi `.py` trong gói `erp_ai/`) có tên file không bắt đầu bằng `test_` (loại cả `test_utils.py`). Bắt: mọi `keyword(arg="for_update")` có giá trị khác `Constant(False)`. Miễn đúng hai cặp (file, hàm bao gần nhất): `FOR_UPDATE_ALLOWED = {("agent/tools/write_ticket.py", "locked_rows"), ("agent/changes/transitions.py", "_lock")}`. Cặp thứ hai là khóa dòng đề xuất có trước (D-2, FEAT-004), không phải khóa HD Ticket; giữ tên hàm nên vẫn đúng sau khi gộp `team/CHG-002` (T126). Một `for_update` thứ hai trong `agent/changes/` hay bất cứ đâu → vi phạm (đúng chữ "mới" của ADR-037). Không quét chuỗi SQL `FOR UPDATE` (chữ ADR là `for_update=True`).

### Dòng thay trong `tasks.md` (chép nguyên văn)

`tasks.md:964` (Returns của T119) — thay cả dòng bằng:
```
  - Returns: bảy luật mới. Phạm vi quét của hai luật khóa theo `design-w1-fixes-13.md` Điểm 3 (khóa `sources` tương đối với `PACKAGE_ROOT`): `test_dedup_reads_go_through_locked_count` chỉ quét `"agent/tools/write_ticket.py"`, các hàm trong `DEDUP_WRITERS = ("post_notice", "post_guidance")` (T168 nối `create_task`, T169 nối `post_comment_tool`): mỗi hàm có trong file, gọi `locked_count` hoặc `count_guidance(..., lock=True)`, không gọi `frappe.db.count`/`exists`/`get_values`/`get_all`/`sql`, `frappe.get_all`/`get_list`, không có `for_update`. `test_route_locks_ticket_before_first_write_unit`: (B1) trong `"agent/runner.py"::_route`, lời gọi `locked_count`/`locked_rows` đầu tiên đứng trước đơn vị ghi đầu tiên (tên kết thúc `_unit`, hoặc `_record_route`, `execute_tool`, `set_value`, `save`, `insert`, `db_set`, `sql`), có ít nhất một đơn vị ghi; (B2) mọi `.py` của gói không phải `test_*.py`: không `keyword(arg="for_update")` khác `False`, trừ `FOR_UPDATE_ALLOWED = {("agent/tools/write_ticket.py", "locked_rows"), ("agent/changes/transitions.py", "_lock")}`. Luật bắt được vi phạm ở mã đã merge → trả `DESIGN_CONFLICT` kèm danh sách, không sửa mã nguồn.
```

`tasks.md:965` (Expect của T119) — thay cả dòng bằng:
```
  - Expect: `test_guidance_marker_defined_once_used_only_by_writer_module`, `test_runner_calls_post_guidance_in_one_place`, `test_dedup_reads_go_through_locked_count`, `test_handlers_do_not_import_write_ticket`, `test_no_guidance_flag_field`, `test_write_ticket_imports_no_proposal_or_catalog_module`, `test_route_locks_ticket_before_first_write_unit` xanh trên mã đã merge (gồm `erp_ai/agent/changes/transitions.py` có `for_update=True` trong `_lock`), mỗi luật có ca đỏ bằng chuỗi mẫu; hai luật khóa có các ca mẫu của `design-w1-fixes-13.md` Điểm 3 (đỏ: A1, A2, A3, B1a, B1b, B2a, B2b; xanh: A0, B0, B2c, B2d).
```

Câu nối vào cuối dòng Expect của T168 (`tasks.md:1197`) và của T169 (dòng Expect, `:1202`), để team-leader dán cùng lúc phán `files:`:
```
 `DEDUP_WRITERS` của `test_architecture.py` nối tên hàm của task này (`design-w1-fixes-13.md` Điểm 3); `test_dedup_reads_go_through_locked_count` xanh.
```

### Chuỗi mẫu (test dán nguyên văn; `W = "agent/tools/write_ticket.py"`, `R = "agent/runner.py"`)

Luật A (`check_dedup_reads_go_through_locked_count`):
- A0 xanh, 0 vi phạm:
  `{W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name, lock=True):\n        return {}\n"}`
- A1 đỏ (đọc chống trùng tự làm), 1 vi phạm ở `post_notice`:
  `{W: "def post_notice(args, ctx):\n    if frappe.db.count('Comment', {'reference_name': ctx.ticket_name}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name, lock=True):\n        return {}\n"}`
- A2 đỏ (đếm không khóa), 1 vi phạm ở `post_guidance`:
  `{W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n\ndef post_guidance(ctx, text):\n    if count_guidance(ctx.ticket_name):\n        return {}\n"}`
- A3 đỏ (thiếu hàm), 1 vi phạm `post_guidance: không thấy hàm`:
  `{W: "def post_notice(args, ctx):\n    if locked_count(ctx.ticket_name, 'Comment', {}):\n        return {}\n"}`

Luật B (`check_route_locks_ticket_before_first_write_unit`):
- B0 xanh, 0 vi phạm:
  `{R: "def _route(log_name, c, d, context, a, s):\n    frappe.db.savepoint('r')\n    if locked_count(context.ticket_name, LOG_DOCTYPE, {'applied': 1}):\n        return []\n    _apply_route_unit(d, c, context, [], [])\n"}`
- B1a đỏ (ghi trước khóa), 1 vi phạm:
  `{R: "def _route(log_name, c, d, context, a, s):\n    _apply_route_unit(d, c, context, [], [])\n    locked_count(context.ticket_name, LOG_DOCTYPE, {'applied': 1})\n"}`
- B1b đỏ (không khóa), 1 vi phạm:
  `{R: "def _route(log_name, c, d, context, a, s):\n    _apply_route_unit(d, c, context, [], [])\n"}`
- B2a đỏ (`for_update` ở tool khác), 1 vi phạm:
  `{"agent/tools/read.py": "def peek(name):\n    return frappe.db.get_value('HD Ticket', name, 'name', for_update=True)\n"}`
- B2b đỏ (`for_update` thứ hai trong `agent/changes/`, không phải `_lock`), 1 vi phạm:
  `{"agent/changes/apply_job.py": "def claim(name):\n    return frappe.db.get_value('ERP AI Change Proposal', name, 'name', for_update=True)\n"}`
- B2c xanh, 0 vi phạm (hai chỗ được miễn):
  `{W: "def locked_rows(t, d, f, fields=('name',)):\n    frappe.db.get_value('HD Ticket', t, 'name', for_update=True)\n    return frappe.db.get_values(d, f, fields, as_dict=True, for_update=True)\n", "agent/changes/transitions.py": "def _lock(name, *extra):\n    return frappe.db.get_value('ERP AI Change Proposal', name, ['change_status'], as_dict=True, for_update=True)\n"}`
- B2d xanh, 0 vi phạm (file test không quét):
  `{"agent/tools/test_write_ticket.py": "def helper(name):\n    return frappe.db.get_value('HD Ticket', name, 'name', for_update=True)\n"}`

Test trên mã thật gọi cả hai luật trên `sources` đầy đủ của gói `erp_ai/`.

---

## Đối chiếu

| Điểm | Task bị đổi | Dòng `tasks.md` thay | File thêm vào `files:` | ADR |
|---|---|---|---|---|
| 1 (G-1) | T96, T98 | `:846`, `:847`, `:857`, `:860` | không (T96 thêm `depends: T98`) | — (giữ `U4b.md:117`) |
| 2 (G-10) | T95, T98 | `:841`, `:844`, `:845`, `:858` | `erp_ai/constants.py` vào T95 | ADR-001, ADR-033 |
| 3 (G-11) | T119 (thay); T168, T169 (nối câu) | `:964`, `:965`; cuối `:1197`, `:1202` | `erp_ai/tests/test_architecture.py` vào T168, T169 (team-leader phán chuỗi) | ADR-036 QĐ 4, ADR-037 QĐ 4 và Ràng buộc, AD3-6 |

`:858` (Receives T98) chỉ do Điểm 2 thay; `:857`, `:860` chỉ do Điểm 1 thay: không dòng nào bị thay hai lần.
