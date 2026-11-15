Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). Vòng sửa 1/3 sau arch-review-design-w1b.md (request-changes). -->

# Bản sửa của design addendum 1 — U4b + U8 (FEAT-007)

**Thứ tự ưu tiên.** File này thắng `design-addendum-1-U4b-U8.md` (gọi tắt "addendum") ở mọi chỗ hai file khác nhau. Mỗi fix nêu dòng addendum bị thay và toàn văn thay thế; chỗ nào không nêu thì addendum giữ nguyên. Touchpoint (mục R1), test plan (mục R2) và giả định (mục R3) được viết lại đầy đủ ở cuối file và thay hẳn mục 7, mục 8 và bảng "Assumptions decided by the team" của addendum.

**Luật thi hành (trích, không chép):** ADR-006 QĐ 2 và Ràng buộc "mọi custom field AI trên HD Ticket có `permlevel` = 8" (ADR-020 QĐ 5 nhắc lại); ADR-005 QĐ 1, QĐ 2 (mức tính một lần ở runner, tool không tự tính mức); ADR-030 QĐ 2 (mức đường chính tính ở `policy.py`, runner tính một lần), QĐ 4 ("độ tin cậy số của bước phân loại", một vị từ); ADR-033 QĐ 1, QĐ 3, Ràng buộc 3; ADR-019 QĐ 7, ADR-021 (đơn vị savepoint của bước định tuyến). Phán quyết: `arch-review-design-w1b.md` mục 4 (1), (2), (4) và mục 5; điều kiện C-5 của `arch-review-design-w1a.md`.

## Explore summary (đọc trực tiếp, 2026-11-14, `develop` @ `431bf55`)

| Chỗ | Điều đã xác nhận | Dùng ở fix |
|---|---|---|
| `frappe/model/document.py:417`, `:425`, `:428`, `:431`, `:459` | `insert`: đặt `__islocal` (`:417`) → `run_method("before_insert")` (`:425`) → `validate_higher_perm_levels()` (`:428`) → `run_before_save_methods()` (`:431`, gồm `before_validate` rồi `validate`) → xóa `__islocal` (`:459`). Vậy `doc.is_new()` đúng trong `validate` lúc tạo | 1 |
| `frappe/model/document.py:928-940` | `validate_higher_perm_levels` trả trường permlevel > 0 về mặc định khi người lưu không có quyền mức đó; bỏ qua khi `flags.ignore_permissions`, `in_install`, Administrator | 1 |
| `helpdesk/.../hd_ticket/hd_ticket.py:82-99` | `before_insert` của controller gọi `apply_ticket_insert_rules`; `validate_higher_perm_levels` bị ghi đè: gọi `prevent_customer_edits()` rồi `super()`; `before_validate` điền Loại, Ưu tiên mặc định | 1 |
| `helpdesk/.../hd_ticket/customer_edit_controller.py:17-29`, `:45-67` | `apply_ticket_insert_rules`: phiếu khách tạo đặt `ignore_permlevel_for_fields` cho trường được miễn; `prevent_customer_edits` trả về ngay khi `is_new()` (`:47`), nên không từ chối lúc tạo; lần lưu sau, trường khách không đọc được và rỗng thì không bị tính là sửa | 1 |
| `erp_ai/handlers.py:27-29`, `:60-81` | `ticket_before_insert` chỉ đặt `erp_ai_prefilled`; `ticket_validate` trả về sớm khi `doc.is_new()` | 1 |
| `erp_ai/hooks.py:143-145` | HD Ticket đã có `before_insert` và `validate` trỏ vào `erp_ai.handlers` (không cần hook mới) | 1 |
| `erp_ai/install.py:20`, `:112`, `:123` | `AI_PERMLEVEL = 8`; mọi dòng `_ai_field_specs` nhận permlevel 8 | 1, 4 |
| `erp_ai/agent/tools/route_ticket.py:41-71` | `apply_route`: `values.update(ai_confidence=…, ai_complexity=…, …)`, vòng kiểm `has_permlevel_access_to` cho từng giá trị, một `doc.save()` | 5 |
| `erp_ai/agent/runner.py:372-386` | `_run_unit` mở savepoint `ROUTE_UNIT_SAVEPOINT`, ngoại lệ → rollback về savepoint, ghi mục `ok=false` | 6 |
| `erp_ai/constants.py:36-38` | `TRIGGER_TICKET_INSERT`, `TRIGGER_COMMENT_MENTION`, `TRIGGER_CHANGE_ACTION` | 7, 8 |
| `erp_ai/agent/tools/*.py` (không tính test) | 0 lời gọi `main_path_level(`, `category_level_cap(`, `effective_level(`; `registry.py` chỉ dùng `effective_level` làm tên tham số/trường | 3 |
| `erp_ai/**/*.py` (không tính test) | 0 chỗ chứa `ai_confidence_pct` hôm nay (T22 chưa merge) | 5 |
| `design-addendum-1-U1.md:140`, `:166`, `:260-261`, `:281-298` | `ToolContext.main_path_level` (None → bằng `effective_level` qua `grant_inputs()`), `latest_classification`, `confidence_threshold`; không có trường đầu mục trong `ToolContext` | 3 |
| `arch-review-design-w1a.md:59` (C-5) | `_classify` trả `(proceed, classification, context)` | 12 |
| `docs/team/features/FEAT-007/tasks.md:134` | T22 (`ai_confidence_pct`) chưa xong; T22a chưa có (team-leader chèn) | 4 |

---

## Fix 1 — W-1: `ai_created_labels` ghi ở `validate`, không ở `before_insert`

**Thay:** addendum `:22` (dòng `handlers.py:27-29` của bảng 1.1), `:78` (dòng `ai_created_labels` của bảng mục 2), `:107-119` (toàn bộ mục 3.1), `:277` (đoạn "Tạo phiếu" đến chữ "Helpdesk điền mặc định"), `:306` (gạch đầu dòng thứ hai của mục 5).

**Toàn văn sửa:**

`:22` →

| `erp_ai/handlers.py:27-29` | `ticket_before_insert` chỉ đặt cờ `erp_ai_prefilled` khi đủ 3 trường; giá trị người gõ không được lưu | `before_insert` giữ tập trường người gõ trong `doc.flags.erp_ai_created_labels`; `validate` (doc mới) ghi tập đó vào `ai_created_labels` (AC-19, AC-21) |

`:78` →

| HD Ticket `ai_created_labels` (permlevel 8, do T22a cài) | ghi (JSON `{ticket_type?, agent_group?, priority?}`, chỉ khóa người gõ mà phiếu còn giữ đúng giá trị; không có → `""`) | `handlers.ticket_validate` khi `doc.is_new()`, trên chính doc đang insert (không `save()` thêm); giữ cố định ở mọi lần lưu sau | đọc theo tên phiếu, 1 lần mỗi lần chạy |

**Mục 3.1 viết lại:**

```python
CREATED_LABELS_FIELD = "ai_created_labels"
CREATED_LABELS_FLAG = "erp_ai_created_labels"

def ticket_before_insert(doc, method=None)   # thêm: doc.flags[CREATED_LABELS_FLAG] = tập người gõ; KHÔNG ghi trường
def ticket_validate(doc, method=None)        # thêm: doc mới → ghi trường; doc cũ → giữ cố định; đánh dấu người khi chưa có log
def _record_created_labels(doc) -> None      # mới, gọi từ ticket_validate
def _freeze_created_labels(doc) -> None      # mới, gọi từ ticket_validate
```

| Hàm | Hành vi | Lỗi / lối ra |
|---|---|---|
| `ticket_before_insert` | Giữ `erp_ai_prefilled`. Thêm: `doc.flags[CREATED_LABELS_FLAG] = {f: doc.get(f) for f in CLASSIFICATION_FIELDS if doc.get(f)}`. Không chạm `CREATED_LABELS_FIELD`: ở `before_insert`, giá trị một trường permlevel 8 bị `validate_higher_perm_levels` (`document.py:428`) xóa ngay sau đó khi người tạo không có quyền mức 8 | không ném |
| `ticket_validate` | **Dòng đầu hàm**, trước mọi lối ra sớm: nếu `doc.meta.has_field(CREATED_LABELS_FIELD)`: `doc.is_new()` → `_record_created_labels(doc)`; ngược lại → `_freeze_created_labels(doc)`. Phần còn lại như addendum `:117` (2) (đánh dấu `Người` khi chưa có dòng log có dự đoán) | không ném |
| `_record_created_labels` | `typed = doc.flags.get(CREATED_LABELS_FLAG) or {}`; `kept = {f: v for f, v in typed.items() if doc.get(f) == v}` (chỉ giữ giá trị người gõ mà phiếu còn mang: nếu bước xóa của Frappe đã bỏ một giá trị người không có quyền ghi, Helpdesk điền mặc định ở `before_validate`, thì trường đó không phải "người điền"); `doc.set(CREATED_LABELS_FIELD, json.dumps(kept, ensure_ascii=False, sort_keys=True) if kept else "")`. Luôn ghi đè giá trị client gửi, ở mọi phiên (khách, Agent có mức 8, Administrator, insert `ignore_permissions` như kéo email) | không ném |
| `_freeze_created_labels` | `doc.has_value_changed(CREATED_LABELS_FIELD)` → `doc.set(CREATED_LABELS_FIELD, doc.get_doc_before_save().get(CREATED_LABELS_FIELD))`, mọi phiên kể cả `AGENT_USER` | không ném |

Vì sao đúng thời điểm: `validate` chạy trong `run_before_save_methods()` (`document.py:431`), tức là **sau** bước xóa trường permlevel cao (`:428`) và sau `before_validate` của Helpdesk, và trước `db_insert`; không bước nào sau đó trả trường về mặc định. Cờ lấy ở `before_insert` của app chạy sau `before_insert` của controller Helpdesk (`apply_ticket_insert_rules` chỉ đặt `raised_by`, `via_customer_portal`, cờ miễn; không điền Loại/Nhóm/Ưu tiên). `prevent_customer_edits` trả về ngay với doc mới (`customer_edit_controller.py:47`), nên khách tạo phiếu không bị từ chối; ở lần lưu sau, khách không đọc được trường này, giá trị rỗng gửi lên không bị tính là sửa và Frappe trả về giá trị đã lưu.

Không thêm `save()`/`db.set_value` trên HD Ticket (ADR-033 Ràng buộc 3): mọi thay đổi nằm trên doc đang được lưu.

`:277` (đầu đoạn) → "Người tạo phiếu → `ticket_before_insert` giữ tập người gõ trong cờ (ví dụ `{"priority": "High"}`) → Frappe xóa trường permlevel cao mà người tạo không có quyền → Helpdesk điền mặc định → `ticket_validate` ghi `ai_created_labels` = `{"priority": "High"}` → `after_insert` xếp job → …" (phần sau giữ nguyên).

`:306` → "- `ai_created_labels` (permlevel 8, ẩn với khách cả ở API theo ADR-006) do server tính ở `validate` của lần tạo và bị giữ cố định ở `validate` của mọi lần lưu sau (mọi phiên): người không giả mạo được "đã điền" để chặn bot, kể cả người có quyền mức 8."

**Test (major W-1):** `erp_ai/tests/test_handlers.py::TestCreatedLabels::test_customer_portal_insert_records_typed_fields`, `::test_user_without_level8_insert_records_typed_fields`, `::test_level8_user_client_value_overwritten`, `::test_only_values_still_on_ticket_recorded` (mục R2). Ca thứ hai chạy dưới một user role `Agent` với `HD Ticket.get_permlevel_access` được patch trả `[0]` (giả lập người không có mức 8, tất định, không tạo Custom DocPerm); test tự kiểm điều kiện đầu `8 not in doc.get_permlevel_access("write")`. Với thiết kế cũ (ghi ở `before_insert`), hai ca đầu đỏ vì trường rỗng.

---

## Fix 2 — W-2: một nguồn độ tin cậy; `set_classification` bỏ `confidence_pct`

**Thay:** addendum `:26` (dòng `write_ticket.py:43-86`), `:80` (dòng ghi `ai_confidence_pct` của mục 2), `:149` (chú thích chữ ký `set_classification`), `:173` (dòng `set_classification` của bảng 3.2), `:181` (dòng `set_classification` của bảng schema).

**Toàn văn sửa:**

`:26` → | `erp_ai/agent/tools/write_ticket.py:43-86` | `set_classification` gọi `decide_route` rồi ghi cả 3 trường | bỏ trường người điền; **không** nhận, **không** ghi độ tin cậy |

`:80` → | HD Ticket `ticket_type`, `agent_group`, `priority`, `ai_classified_by` | ghi | `apply_route`, `set_classification` | — |
và thêm dòng: | HD Ticket `ai_confidence_pct` | ghi | **chỉ** `route_ticket.apply_route`, giá trị = `classification.confidence_pct` của bước phân loại cùng lần chạy (Fix 5) | — |

`:149` → `def set_classification(args: dict, ctx: ToolContext) -> dict      # thêm bỏ trường người điền`

`:173` →

| `set_classification` | Như nay, thêm: sau `decide_route` trong `_mapped_values`, `decision = keep_human_fields(decision, created_labels(doc.get(CREATED_LABELS_FIELD)))` (trường người điền vào `skipped` với `REASON_HUMAN_FILLED`). Không có tham số độ tin cậy; khóa `confidence_pct` model gửi thừa bị bỏ qua như mọi khóa lạ; `values` không bao giờ chứa `ai_confidence_pct` | như nay |

`:181` → | `set_classification` | — (schema không đổi) | — |

Hệ quả nêu rõ: số trên phiếu và số của vị từ dưới ngưỡng (`latest_classification(...)[1]`, ADR-030 QĐ 4) cùng lấy từ `classification.confidence_pct` của bước phân loại. Phiếu chưa định tuyến (dưới ngưỡng, hoặc người đã phân loại) giữ `ai_confidence_pct` rỗng; xem A-U4b-11.

**Test (major W-2):** `erp_ai/agent/test_agent_runner.py::TestConfidenceSource::test_after_mention_ticket_pct_equals_latest_classification` (lần tạo phiếu stub 85 → định tuyến; lần `@ai` stub gọi `set_classification` kèm `confidence_pct: 40` → `ai_confidence_pct == 85 == policy.latest_classification(phiếu)[1]`); `erp_ai/agent/tools/test_write_ticket.py::TestConfidenceSource::test_set_classification_never_writes_confidence_pct`, `::test_set_classification_schema_has_no_confidence_pct`.

---

## Fix 3 — W-3: tool BA note không tính lại mức đường chính

**Thay:** addendum `:175` (dòng `post_comment_tool`, `kind == "ba_note"` của bảng 3.2).

**Toàn văn sửa:**

| `post_comment_tool`, `kind == "ba_note"` (U8) | Trước bước (5): `category = policy.latest_classification(ctx.ticket_name)[0]` (đầu mục của lần chạy: cùng hàm runner dùng để dựng context cho lần chạy không phải tạo phiếu; với lần tạo phiếu, dòng `classify` của chính lần chạy đã commit trước `_reason`) và `level = ctx.grant_inputs().main_path_level` (mức đường chính runner đã tính một lần và đặt vào context; `grant_inputs()` của U1 là chỗ duy nhất đổi `None` thành `effective_level`). `category != "C"` hoặc `level == "L0"` → `REASON_BA_NOTE_NOT_C`. Không gọi `policy.main_path_level`, `policy.category_level_cap`, `policy.effective_level` và không đọc trường mức của Setting. Phần còn lại như addendum: `CONFIDENCE_LINE` bắt buộc; đủ 5 mục `BA_NOTE_SECTIONS` → ngược lại `REASON_BA_NOTE_MISSING`; mục "Tính năng sẵn có" bắt đầu bằng Có/Không và có "Nguồn" → ngược lại `REASON_BA_NOTE_FEATURE`; khóa dòng phiếu; đã có comment agent bắt đầu bằng `BA_NOTE_MARKER` → `REASON_BA_NOTE_EXISTS`; nội dung đăng = `BA_NOTE_MARKER + "\n" + content` (bỏ marker trùng). Dưới ngưỡng, nhánh (2) chặn trước (chỉ `hoi`) | như trên |

**Test (major W-3):** `erp_ai/agent/tools/test_write_ticket.py::TestBaNote::test_gate_reads_context_level_not_settings` (đầu mục C; `ctx.main_path_level = "L0"` trong khi Setting cap C = L3 → từ chối; `ctx.main_path_level = "L1"` trong khi Setting cap C = L0 → đăng được: chứng minh tool đọc context, không đọc cấu hình); `erp_ai/agent/tools/test_write_ticket.py::TestLevelNotRecomputed::test_no_level_function_called_in_tools` (AST mọi `erp_ai/agent/tools/*.py` không phải `test_*.py`: 0 nút `Call` có tên hoặc thuộc tính `main_path_level`, `category_level_cap`, `effective_level`; hôm nay đã 0, Explore summary).

---

## Fix 4 — Phán quyết (1): trường `ai_created_labels` do U0 cài ở task T22a

**Thay:** addendum `:56` (thêm dòng sau), `:60` (điều kiện bắt đầu), `:66` (dòng `ai_created_labels` của bảng 1.3, xóa), `:74` (câu dẫn mục 2), `:315` (gạch "Schema" của mục 6), `:462` (A-U4b-1).

**Toàn văn sửa:**

Thêm sau `:56`: | Trường HD Ticket `ai_created_labels` (Small Text, `hidden`, `read_only`, `no_copy`, permlevel 8, trong `_ai_field_specs`) | U0 task T22a (`arch-review-design-w1b.md` mục 4 (1)) | Không (T22a) |

`:60` → "**Điều kiện bắt đầu.** U4b: U0 (gồm T22a, hoặc task tích hợp đường lùi của chủ U0 ở đầu đợt 1), U4a, U5a (đợt 0), U1, U3 đã merge vào `team/FEAT-007`. Task `write_ticket.py` của U8: sau U4b. Task `prompts.py` của U8: sau task `prompts.py` của U6b (Fix 7). Cắt sớm hơn → `DESIGN_CONFLICT`, dừng."

`:66` → xóa dòng (đã có chủ, không còn thiếu). Bảng 1.3 chỉ còn dòng "Mọi tên ở bảng 1.2 dòng U1, U3"; dòng `ai_confidence_pct` (`:67`) do Fix 5 thay.

`:74` → "U4b, U8 **không thêm** DocType hay trường và không sửa `install.py`. `ai_created_labels` do T22a của U0 cài (permlevel 8 theo ADR-006); thời điểm ghi do U4b quyết (Fix 1). Đọc và ghi:"

`:315` → "- **Schema:** không trong U4b/U8. Trường `ai_created_labels` và đường lùi phiên bản của nó thuộc T22a và T23 (U0). `handlers.py` giữ phép `doc.meta.has_field(CREATED_LABELS_FIELD)` để hook không lỗi trong lúc migrate chưa tạo trường. **Dữ liệu:** không ghi lại dữ liệu cũ. Phiếu tạo trước khi U4b deploy có trường rỗng → `created_labels("")` = `{}` → hành vi như nay (bot điền trường trống theo dự đoán)."

A-U4b-1: viết lại ở mục R3.

---

## Fix 5 — Phán quyết (2): `route_ticket.py` vào touchpoint U4b; `apply_route` là đường ghi duy nhất của `ai_confidence_pct`

**Thay:** addendum `:25` (dòng `route_ticket.py:41-71` của bảng 1.1), `:58` (dòng FEAT-006 của bảng 1.2), `:67` (dòng `ai_confidence_pct` của bảng 1.3, xóa), `:333` (đoạn ô file), `:463` (A-U4b-2). Thêm mục 3.6 mới.

**Toàn văn sửa:**

`:25` → | `erp_ai/agent/tools/route_ticket.py:41-71` | `apply_route` ghi mọi trường `decision` có giá trị và 4 trường điểm; không ghi độ tin cậy số | thêm **một** giá trị `ai_confidence_pct=classification.confidence_pct` vào `values.update(...)`; trường người điền vẫn do runner bỏ khỏi `decision` trước khi gọi (A-U4b-2) |

`:58` → | `post_routing_comment`, `apply_route`, `create_routed_task` | FEAT-006 `route_ticket.py` | Có (U4b thêm một giá trị vào `apply_route`) |

`:67` → xóa dòng (phán quyết (2) đã chọn).

**Mục 3.6 mới — `tools/route_ticket.py` (U4b):**

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `apply_route` | Chỉ một thay đổi: `values.update(ai_confidence=…, ai_complexity=…, ai_importance=…, ai_score_reason=…, ai_confidence_pct=classification.confidence_pct)`. Vòng `has_permlevel_access_to` có sẵn xử lý thiếu quyền mức 8 (bỏ khỏi `values`, vào `skipped`). Giá trị nằm trong cùng `doc.save()` của đơn vị định tuyến (ADR-019 QĐ 7, ADR-021). Không đổi chữ ký, không đổi lối từ chối (`ai_classified_by == Người` → `ok=false`, không ghi gì) | như nay |

Ràng buộc kiểm được: trong `erp_ai/**/*.py` không phải test, chỉ `erp_ai/agent/tools/route_ticket.py` (và `erp_ai/install.py`, nơi khai báo trường) gán `ai_confidence_pct`. Dòng `classify` có `predicted_confidence_pct` (U1 ghi) bằng giá trị trên phiếu sau khi định tuyến. Dưới ngưỡng (không định tuyến) phiếu không đổi.

`:333` → "Đều nằm trong ô "Module, file chạm" của U4b (`arch-impact.md:179`: `runner.py`, `prompts.py`, `handlers.py`, `tools/write_ticket.py`) cộng `tools/route_ticket.py` theo phán quyết (2) của `arch-review-design-w1b.md` (không đơn vị nào khác ở đợt 1 sửa file này; `team/FEAT-004` không sửa), và ô của U8 (`arch-impact.md:182`: `prompts.py`, `tools/write_ticket.py`; module danh mục chỉ cho AC-64, không đụng). U8 không sửa `runner.py`. Không sửa: `registry.py`, `policy.py`, `queue.py`, `run_log.py`, `install.py`."

**Test (phán quyết 2):** `erp_ai/agent/tools/test_route_ticket.py::TestConfidencePct::test_apply_route_writes_confidence_pct` (pct 85 → phiếu 85, có trong `after`; người đã phân loại → `ok=false`, trường không đổi), `::test_only_route_ticket_assigns_ai_confidence_pct` (AST trên `erp_ai/**/*.py` không phải `test_*.py`: nút `keyword(arg="ai_confidence_pct")`, gán thuộc tính `.ai_confidence_pct =`, khóa dict hằng `"ai_confidence_pct"`, đối số hằng `"ai_confidence_pct"` của lời gọi `set`/`db_set`/`set_value` chỉ có ở `route_ticket.py` và `install.py`); `erp_ai/agent/test_runner_routing.py::TestConfidencePct::test_classify_row_pct_equals_ticket_after_route`, `::test_below_threshold_ticket_pct_unchanged`.

---

## Fix 6 — Phán quyết (4): phần runner của AC-19, AC-25, AC-27, AC-28

**Thay:** addendum `:246` (dòng `_route` của bảng 3.4) và `:248` (dòng `_watch_unit`); thêm câu cuối cho `:10`.

**Toàn văn sửa:**

`:246` → | `_route` | Bước định tuyến là mã tất định, **không** gọi Cổng model (ADR-033 QĐ 3). Sau `_apply_route_unit` thành công: `_check_sla`, `_assign_unit`, `_task_unit` như nay; thêm `watcher = _watch_unit(decision.watcher, …)` khi `decision.watcher`; mọi ghi là một đơn vị `_run_unit` riêng (savepoint `ROUTE_UNIT_SAVEPOINT`), mỗi lần ghi đúng một mục hành động qua `_route_action` vào `actions` của **dòng `classify`** (ADR-019 QĐ 7, ADR-021, ADR-033 QĐ 1, 5). Rồi `lines = _route_lines(result, assigned, task, watcher) + lines` (+ `split_text` cuối nếu có: comment tách phiếu nằm **trong** comment định tuyến, AC-23, AC-28); `_comment_unit(lines, …)` như nay → **đúng 1 comment** cho định tuyến thành công. `result` None → chỉ các câu lỗi cũ (nếu có) |

`:248` → | `_watch_unit` | Đã có Document Follow (`ref_doctype` "HD Ticket", `ref_docname`, `user`) → mục `_route_action("add_watcher", "HD Ticket", ticket, False, "đã theo dõi")`, trả None. Ngược lại `_run_unit("add_watcher", lambda: _follow(watcher, ticket), "HD Ticket", ticket, actions, errors)`; `_follow` gọi `follow_document("HD Ticket", ticket, watcher)`; trả về falsy → `{"ok": False, "reason": "người theo dõi tắt nhận theo dõi tài liệu"}`; ngoại lệ → `_run_unit` rollback về savepoint, chỉ mất phần theo dõi (trường, gán, Task đã ghi giữ nguyên); thành công → mục `ok=True`, `value_after={"watcher": watcher}`, trả `watcher` |

Thêm cuối `:10`: "AC-19, AC-25, AC-27, AC-28 chỉ nghiệm thu xong sau khi U4b merge; plan ghi rõ, QA không đóng các AC này ở cuối đợt 0 (`arch-review-design-w1b.md` mục 4 (4))."

**Test (phán quyết 4):** `erp_ai/agent/test_runner_routing.py::TestRunnerHooks::test_watcher_failure_rolls_back_only_watcher_unit` (`follow_document` ném → 0 Document Follow; Loại/Nhóm và việc gán vẫn ghi; dòng `classify` có mục `add_watcher` `ok=false`), `::test_routing_step_makes_no_gateway_call` (đếm lời gọi stub cổng model từ đầu `_route` tới cuối `_route` = 0), cùng bốn test `TestRunnerHooks` có sẵn ở addendum `:434`.

---

## Fix 7 — Mục 5, `prompts.py`: thứ tự U4b → U6b → U8; gợi ý C chỉ cho hai trigger (kèm minor (c))

**Thay:** addendum `:203` (gạch U8 của mục 3.3), `:347` (câu thứ tự build), `:349-359` (bảng `prompts.py` của 7.2). Bảng mới ở R1.

**Toàn văn sửa:**

`:203` → "- U8: `TASK_CATEGORY_C` (ý, dev giữ ý): "Phiếu đầu mục C: tìm tính năng sẵn có bằng search_source trước, rồi đăng BA note bằng post_comment kind = ba_note (một lần mỗi phiếu). Nếu có tool create_task, tách việc thành các Task, mỗi Task có ước lượng giờ." Thêm hằng `CATEGORY_HINT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)` (import từ `erp_ai/constants.py`, không viết chuỗi literal). `build_initial_message` ghép `"\n" + TASK_CATEGORY_C` sau dòng việc **chỉ khi** `trigger in CATEGORY_HINT_TRIGGERS` ∧ `(classification or {}).get("category") == "C"`. Lần chạy `kb_draft` (dòng cấp cố định không có `post_comment`, `create_task`, ADR-033 QĐ 3), `requester_reply`, `change_action` không nhận gợi ý: prompt phải theo kết quả cấp (ADR-030 QĐ 3, ADR-011)."

`:347` → "Dòng theo `develop` @ `1918db2`. Thứ tự build: U1 → U3 → U4b → (U6b) → U8. Với `prompts.py`: **U4b → U6b → U8** (task `prompts.py` của U8 làm sau cùng); task `write_ticket.py` của U8 làm được ngay sau U4b. Mỗi task cắt từ `team/FEAT-007` sau khi task trước trên cùng file đã merge."

**Test:** `erp_ai/agent/test_prompts.py::TestCategoryC::test_hint_skipped_for_other_triggers` (C + `TRIGGER_KB_DRAFT` → không có `TASK_CATEGORY_C`; C + `TRIGGER_REQUESTER_REPLY` → không có; C + `TRIGGER_CHANGE_ACTION` → không có). Hai hằng của U6b đã có trên nhánh vì task `prompts.py` của U8 cắt sau U6b.

---

## Fix 8 — Mục 5, `runner.py`: thứ tự U4b → U6b; không thông báo vượt ngân sách, lỗi lần chạy, hỏi dự phòng ở lần chạy `kb_draft`

**Thay:** addendum `:226` (chữ ký `_notice`), `:236`, `:237`, `:239`, `:240`, `:242`, `:251`, `:252` (các dòng thông báo của bảng 3.4), `:381` (đoạn "Song song"). Thêm hằng sau `:221`.

**Toàn văn sửa:**

Thêm sau `:221`:

```python
NOTICE_TRIGGERS = {
    "over_budget": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
    "run_failed": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
    "ask_fallback": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
}   # "daily_limit" không có trong bảng: áp cho mọi trigger tới được bước (d)
```

`:226` → `def _notice(ticket_name, notice, body, since, *, trigger, instructor=None) -> dict | None`

| Chỗ | Hành vi chính xác |
|---|---|
| `_notice` (`:240`) | `notice in NOTICE_TRIGGERS ∧ trigger not in NOTICE_TRIGGERS[notice]` → trả `None`, không đọc, không ghi (không có mục). Ngược lại `write_ticket.post_notice(...)`; `ok` → `run_log.action_entry(NOTICE_TOOL, "Comment", r["comment"], True, value_after={"notice": notice}, instructor=instructor)`; không ok (đã thông báo) → `None` |
| `_run` (d) (`:236`) | như addendum, gọi `_notice(..., trigger=trigger)` |
| `_run` sau (e) (`:237`) | như addendum, gọi `_notice(..., "over_budget", ..., trigger=trigger)` |
| `_log_skip` (`:239`) | tham số `notice: tuple[str, str, datetime] \| None = None` và `trigger`; chuyển `trigger` cho `_notice` |
| `_classify` lỗi cổng (`:242`) | như addendum, gọi `_notice(..., "run_failed", ..., trigger=trigger)`; trả `(False, None, context)` (Fix 12) |
| `_reason` lỗi cổng (`:251`) | như addendum, gọi `_notice(..., "run_failed", ..., trigger=trigger)` |
| `_reason` lượt cuối (`:252`) | `final ∧ context.below_threshold ∧ not write_ticket.asked_in_run(run_id)` → `_notice(…, "ask_fallback", …, trigger=trigger)`; có mục → thêm vào `actions` trước `write_entry` và `write_ticket.mark_asked(run_id)` (Fix 9) |

Bảng là danh sách cho phép (fail-closed): trigger mới không có thông báo nào ngoài `daily_limit` cho tới khi đơn vị của nó thêm vào đúng ô. Ba trigger có trên `develop` hôm nay (`constants.py:36-38`) giữ đúng hành vi của addendum. Hợp đồng cho U6b (mục R4): U6b thêm `TRIGGER_REQUESTER_REPLY` vào ô nào U6b cần, **không bao giờ** thêm `TRIGGER_KB_DRAFT`; `daily_limit` vẫn áp cho `requester_reply` mà không cần sửa gì (U6b dựa vào nó; `kb_draft` được miễn bước (d) ở task runner của U6b nên không tới thông báo này).

`:381` → "Song song với U6b: `runner.py` theo thứ tự **U4b → U6b** (task `runner.py` của U6b cắt sau khi U4b merge; task file mới của U6b chạy song song được). `prompts.py` theo **U4b → U6b → U8** (Fix 7). `handlers.py`: hàm khác nhau, merge lần lượt theo thứ tự nào cũng được (Fix 10)."

**Test:** `erp_ai/agent/test_agent_runner.py::TestRunNotices::test_notice_only_for_listed_triggers` (gọi `_notice` với trigger `"x_unlisted"`: `over_budget`, `run_failed`, `ask_fallback` → 0 Comment, `None`; `daily_limit` → 1 Comment, 1 mục). Ca `kb_draft` cụ thể là test của task runner U6b (mục R4), vì hằng `TRIGGER_KB_DRAFT` chưa có lúc U4b build.

---

## Fix 9 — Mục 5, `write_ticket.py`: câu hỏi gửi qua email tính là "lần hỏi" của lần chạy

**Thay:** addendum `:95` (dòng khóa "Comment hỏi dưới ngưỡng"), `:145` (thêm hàm sau), `:169` (dòng `asked_in_run`), `:171` (cuối bước (2) "thành công → thêm `ctx.run_id`…"), `:266` (dòng hợp đồng `asked_in_run`).

**Quyết định (A-U4b-12):** một lần chạy có tối đa **một** câu hỏi, bất kể kênh. Câu hỏi gửi người tạo bằng `reply_to_requester(kind="question")` của U6b tính là lần hỏi đó: comment hỏi (`post_comment` `kind="hoi"`) bị từ chối và runner không đăng `ask_fallback`. Đây là quyết định kỹ thuật architect giao designer chốt (`arch-review-design-w1b.md` mục 5); không đổi chữ AC-22 hay AC-40.

**Toàn văn sửa:**

`:95` → | Câu hỏi dưới ngưỡng (AC-22, AC-40) | `run_id` (tập `frappe.flags.erp_ai_asked_runs`, sống trong một job), đánh dấu qua `mark_asked` bởi comment hỏi, `ask_fallback` và (U6b) câu hỏi qua email | lần hỏi thứ hai trong cùng lần chạy bị từ chối (`REASON_ONE_ASK`) hoặc không đăng |

Thêm sau `:145`: `def mark_asked(run_id: str) -> None`

`:169` → | `asked_in_run`, `mark_asked` | `asked_in_run`: `run_id in frappe.flags.get("erp_ai_asked_runs", set())`. `mark_asked`: `frappe.flags.setdefault("erp_ai_asked_runs", set()).add(run_id)`; `run_id` rỗng → `ValueError`. Hai hàm là chỗ duy nhất đọc/ghi cờ này | `ValueError` |

`:171` (cuối bước (2)) → "…; thành công → `mark_asked(ctx.run_id)`;"

`:266` → | `asked_in_run`, `mark_asked` | `(run_id: str) -> bool`, `(run_id: str) -> None` | `write_ticket.py` | U6b: `reply.py` gọi `mark_asked(ctx.run_id)` khi gửi câu hỏi thành công (`kind="question"`), và kiểm `asked_in_run` trước khi gửi |

**Test:** `erp_ai/agent/tools/test_write_ticket.py::TestPostCommentKinds::test_marked_run_refuses_comment_question` (`mark_asked(run)` rồi `post_comment(kind="hoi")` dưới ngưỡng → `REASON_ONE_ASK`, 0 Comment); `erp_ai/agent/test_agent_runner.py::TestAskOnly::test_marked_run_no_fallback` (cờ đã đặt → lượt cuối không đăng `ask_fallback`).

---

## Fix 10 — Mục 5, `handlers.py` và `registry.py`: không xung đột, ghi rõ

**Thay:** addendum `:379`.

**Toàn văn sửa:** "`erp_ai/handlers.py`: U1 sửa `comment_after_insert`; U4b sửa `ticket_before_insert`, `ticket_validate` (đầu hàm, Fix 1) và thêm `_record_created_labels`, `_freeze_created_labels`; U6b tách `ticket_on_update`, thêm `communication_on_update`, `task_on_update`. Khác hàm, không xung đột về nghĩa; merge lần lượt, thứ tự nào cũng được. `registry.py`: U4b, U8 không sửa (A-U8-1); chỉ U6b sửa sau U1."

---

## Fix 11 — Minor (a)–(e) của W-mục 2

**Thay:** addendum `:264`, `:265`, `:269` (hợp đồng), `:25`, `:67`, `:333` (đã ở Fix 5), không sửa mã cho (e).

- **(a)** Xóa dòng `:269` (`TICKET_FIELD_SETTINGS`, `_ticket_fields` cho U6b). Hai tên vẫn là nội bộ của `runner.py`; job vòng đời của U6b không import `runner` (ADR-033 Ràng buộc 4).
- **(b)** `:264` → | `COMMENT_KINDS` | `("de_xuat", "hoi", "ba_note")` sau U8 | `write_ticket.py` | U7 (comment đề xuất bản ghi, nếu dùng `post_comment`) |
  `:265` → | `CONFIDENCE_LINE`, `section_text`, `EVIDENCE_HEADER` | mục 3.2 | `write_ticket.py` | U7 (AC-33), không bắt buộc; U6b hiện không dùng |
  `:266` → như Fix 9 (`asked_in_run`, `mark_asked` cho U6b).
- **(c)** Gợi ý C chặn theo trigger: Fix 7.
- **(d)** Touchpoint `route_ticket.py`: Fix 5; A-U4b-2 giữ (mục R3, chỉ đổi cột "Vì").
- **(e)** Lời gọi `policy.confidence_threshold(frappe.get_single(SETTING_DOCTYPE))` trong `post_comment_tool` (addendum `:171`) đúng hợp đồng U1 (`design-addendum-1-U1.md:282`) và giữ nguyên. Test grep `test_threshold_compared_only_in_policy` của U1 phải bỏ qua lời gọi accessor `policy.confidence_threshold(`; việc đó thuộc file test của U1 (ghi chú cho team-leader, `arch-review-design-w1b.md` mục 6).

---

## Fix 12 — Điều kiện C-5 của `arch-review-design-w1a.md`: hình dạng trả của `_classify`

**Thay:** addendum `:238` (dòng "lần chạy không phải tạo phiếu"), `:242` (đuôi), `:245` (đuôi bước (5)), `:368`, `:370` (bảng thứ tự `runner.py`).

**Toàn văn sửa:**

`:238` → | `_run`, lần chạy không phải tạo phiếu | `classification = {"category": category, "confidence_pct": pct}` từ chính cặp `category, pct` mà U1 đã đọc bằng `policy.latest_classification` khi dựng context (không đọc lần hai), thay vì `None` khi `category` khác None. Dùng cho gợi ý đầu mục C (U8, chỉ khi trigger thuộc `CATEGORY_HINT_TRIGGERS`) |

`:242` đuôi → "… Ở L0 → không comment (AC-23). Nhánh trả `(False, None, context)`."

`:245` bước (5) đuôi → "… `_classify` trả `(proceed, classification, context)` như C-5; U4b không đổi hình dạng này và không thêm phần tử."

`:368`, `:370`: xem bảng `runner.py` ở R1 (cột U2 thêm vào; U4b sửa sau U3).

---

## R1 — Touchpoints (thay mục 7 của addendum)

### R1.1 File

| File | Đơn vị | Sửa |
|---|---|---|
| `erp_ai/handlers.py` | U4b | 3.1 theo Fix 1 |
| `erp_ai/agent/tools/write_ticket.py` | U4b, rồi U8 | 3.2 theo Fix 2, 3, 9 |
| `erp_ai/agent/tools/route_ticket.py` | U4b | 3.6 (Fix 5): một giá trị trong `apply_route` |
| `erp_ai/agent/prompts.py` | U4b, rồi (U6b), rồi U8 | 3.3 theo Fix 7 |
| `erp_ai/agent/runner.py` | U4b | 3.4 theo Fix 6, 8, 12 |

Test (cạnh mã, `structure.tests = colocated`; không file mới):

| File | Trạng thái |
|---|---|
| `erp_ai/tests/test_handlers.py` | thêm; sửa test FEAT-001/006 ghim "người sửa khi chưa có dự đoán → bỏ qua" (NFR-8: AC-21) |
| `erp_ai/agent/tools/test_write_ticket.py` | thêm; sửa test gọi `post_comment` không có `kind`, `create_task` không có `expected_hours` (NFR-8: AC-22, AC-63) |
| `erp_ai/agent/tools/test_route_ticket.py` | thêm (Fix 5) |
| `erp_ai/agent/test_prompts.py` | thêm (file do U1 tạo) |
| `erp_ai/agent/test_agent_runner.py` | thêm |
| `erp_ai/agent/test_runner_routing.py` | thêm; sửa test FEAT-006 đếm 0 comment khi định tuyến thành công (NFR-8: AC-23) |

Không sửa: `install.py` (T22a của U0), `registry.py`, `policy.py`, `queue.py`, `run_log.py`, `constants.py`, `tests/test_architecture.py`.

### R1.2 Thứ tự sửa theo khối

`erp_ai/agent/prompts.py` (thứ tự U1 → U4b → U6b → U8)

| Khối | U1 | U4b | U6b | U8 |
|---|---|---|---|---|
| `CLASSIFY_PROMPT` `:14-81` | khóa `do_tin_cay_pct` | — | — | — |
| `CORE_PROMPT` → `core_prompt`; khối quyền; `ASK_ONLY_BLOCK`; `PROMPT_CONFLICT_PAIRS` | toàn khối | — | — | — |
| `TASK_NEW_TICKET`, `TASK_COMMENT` `:236-237` | — | — | thêm `TASK_REQUESTER_REPLY`, `TASK_KB_DRAFT` | thêm `TASK_CATEGORY_C`, `CATEGORY_HINT_TRIGGERS` sau hằng của U6b |
| `ticket_text`, `build_classify_request` `:244-256` | — | hằng, `ticket_fields_text`, tham số | — | — |
| `build_reason_system` `:313-334` | toàn hàm | — | `KNOWLEDGE_SOURCES_BLOCK`, `REPLY_BLOCK`, cờ `reply_tools` | — |
| `build_initial_message` `:337-362` | — | tham số `ticket_fields`, khóa `fields` | chọn `task` theo trigger | 2 dòng ghép `TASK_CATEGORY_C` có điều kiện trigger (Fix 7) |

`erp_ai/agent/runner.py` (thứ tự U1 → U2 → U3 → U4b → U6b)

| Khối | U1 | U2 | U3 | U4b |
|---|---|---|---|---|
| import `:13-44` | registry (`grant`), authority | — | `run_log.action_entry` | `write_ticket` (`post_notice`, `created_labels`, `keep_human_fields`, `asked_in_run`, `mark_asked`, `ASK_FOOTER`), `follow_document`, `TRIGGER_CHANGE_ACTION` |
| hằng `:61-97` | — | — | `ACTION_DOCTYPE_MAX` chuyển đi | hằng 3.4 + `NOTICE_TRIGGERS` sau `:97` |
| `WRITE_TOOL_TARGETS` `:72-85` | — | — | — | — (U8 cũng không) |
| `run_for_ticket`, `_run` `:100-190` | (a), (e), context, `comment_name`, mở gói 3 phần tử (C-5) | — | — | (d) thông báo; `_ticket_fields`; thông báo ngân sách trước `_reason`; `classification` cho lần không tạo phiếu |
| `_log_skip` `:223-234` | — | — | — | tham số `notice`, `trigger` |
| `_classify` `:248-323` | context sau parse, chốt `_route`, `predicted_confidence_pct`, trả 3 phần tử | khối "bị loại" sau parse | chỉ lời gọi `_route_action` | đọc phiếu; gọi model; nhánh lỗi cổng; `decide_route`; `keep_human_fields`; cột log mới; logger độ trễ |
| `_route` `:326-358` | — | — | lời gọi `_route_action` | `_watch_unit`, `_route_lines`, `split_text` |
| `_route_action`, `_run_unit` `:361-390` | — | — | thân → `action_entry` | chỉ gọi |
| `_reason` `:570-658` | `:584-599` | — | — | `:578-583`, `:600`, `:620-629`, lượt cuối trước `write_entry` |
| `_run_tool`, `_action` `:661-700` | — | — | `_action`, `_entry_values` | — |

U6b sửa `runner.py` sau U4b (chữ ký, kiểm bỏ qua, (d) miễn cho `kb_draft`, context, `WRITE_TOOL_TARGETS`, cờ `reply_tools`, và nếu cần thêm `TRIGGER_REQUESTER_REPLY` vào ô `NOTICE_TRIGGERS`).

`erp_ai/agent/tools/write_ticket.py`: U1, U3 không sửa. U4b: `_mapped_values`, `set_classification`, `post_comment` (tách `_post`), hàm mới (gồm `mark_asked`), `TOOLS` của `post_comment` (schema `set_classification` không đổi). U8 sau U4b: `create_task`, nhánh `ba_note`, `COMMENT_KINDS`, `TOOLS` của `post_comment`, `create_task`.

`erp_ai/agent/tools/route_ticket.py`: chỉ U4b (một dòng trong `apply_route`).

### R1.3 So khớp đường dẫn

```
new: docs/team/features/FEAT-007/design-addendum-1-U4b-U8-fixes.md (artifact này) -> prefix "docs/" khớp
new code/test: không có
allowed_new_file_roots = ["erp_ai", "docs", ".github"]
protected_paths = [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]
modified nguồn (5): erp_ai/handlers.py, erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/route_ticket.py,
                    erp_ai/agent/prompts.py, erp_ai/agent/runner.py
modified test (6):  erp_ai/tests/test_handlers.py, erp_ai/agent/tools/test_write_ticket.py,
                    erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/test_prompts.py,
                    erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py
-> đều dưới erp_ai/; không file nào khớp protected_paths
```

---

## R2 — Test plan (thay mục 8 của addendum)

Chạy từng file bằng `cmd.test_one`, cả app bằng `cmd.test`. Stub cổng model (JSON phân loại có `do_tin_cay_pct` theo ca; lượt `tool_use` theo kịch bản), không mạng; mốc thời gian đặt bằng `creation` của bản ghi test (STD-TEST-6). Mỗi test tự đặt Setting (mức, ngưỡng, 7 trường, `max_tasks_per_run`, cap đầu mục) và trả lại. `[mới]` = thêm ở file này; `[sửa]` = thay dòng addendum.

| AC | Test (`file::name`) | Ca biên / lỗi |
|---|---|---|
| AC-17 | `erp_ai/agent/test_agent_runner.py::TestClassifyLatency::test_success_row_written_at_result_time` | `creation` phiếu = lúc chạy − 6 phút → `creation(dòng) − creation(phiếu) ≥ 360 s`; logger có `latency_s` |
| AC-17 | `…test_agent_runner.py::TestClassifyLatency::test_gateway_error_row_has_no_prediction` | dòng có `error`, `predicted_category` rỗng |
| AC-21 | `erp_ai/tests/test_handlers.py::TestCreatedLabels::test_insert_records_typed_fields_only` `[sửa]` | 8 ca (rỗng, 3 tập 1 trường, 3 tập 2 trường, đủ 3) dưới Administrator; giá trị ghi ở `validate`, không ở `before_insert` |
| AC-21 (W-1) | `…test_handlers.py::TestCreatedLabels::test_customer_portal_insert_records_typed_fields` `[mới]` | user HD Customer (điều kiện đầu `8 not in get_permlevel_access("write")`), tạo phiếu có `priority` → tạo được, trường = `{"priority": …}` |
| AC-21 (W-1) | `…test_handlers.py::TestCreatedLabels::test_user_without_level8_insert_records_typed_fields` `[mới]` | user role `Agent`, `get_permlevel_access` patch trả `[0]` → tạo được, trường = tập người gõ |
| AC-21 (W-1) | `…test_handlers.py::TestCreatedLabels::test_level8_user_client_value_overwritten` `[mới]` | Agent có mức 8 gửi sẵn `ai_created_labels` giả → bị ghi đè bằng tập người gõ |
| AC-21 (W-1) | `…test_handlers.py::TestCreatedLabels::test_only_values_still_on_ticket_recorded` `[mới]` | cờ `{"priority": "High"}` nhưng phiếu mang `Medium` lúc `validate` → trường `""` |
| AC-21 | `…test_handlers.py::TestCreatedLabels::test_created_labels_frozen_after_insert` | người sửa trường → giá trị cũ; dưới agent cũng vậy |
| AC-21 | `erp_ai/agent/test_runner_routing.py::TestHumanFilledFields::test_partial_fill_kept_blank_filled` | 6 tập con × L1, L2, L3 (subTest) |
| AC-21 | `…test_runner_routing.py::TestHumanFilledFields::test_log_keeps_model_prediction_and_created_labels` | `predicted_priority` = giá trị model; `created_labels` = tập người gõ |
| AC-21 | `erp_ai/agent/tools/test_write_ticket.py::TestHumanFields::test_set_classification_skips_created_fields` | lần `@ai` sau không đè trường người điền |
| AC-21 | `…test_write_ticket.py::TestHumanFields::test_invalid_created_labels_write_none_of_three` | JSON hỏng → 0 trường trong 3 |
| AC-21 | `erp_ai/tests/test_handlers.py::TestHumanCorrection::test_edit_before_first_log_marks_human` | không có dòng `classify` → `ai_classified_by = Người` |
| AC-21 | `…test_runner_routing.py::TestHumanFilledFields::test_insert_run_after_pre_log_edit_writes_nothing` | `apply_route` từ chối; dòng `classify` có `human_corrected_to` |
| AC-21 | `erp_ai/tests/test_handlers.py::TestHumanCorrection::test_record_tool_write_is_not_human` | dưới `AGENT_USER` → không thành Người |
| AC-22 (W-2) | `erp_ai/agent/test_agent_runner.py::TestConfidenceSource::test_after_mention_ticket_pct_equals_latest_classification` `[mới]` | tạo phiếu stub 85; `@ai` gọi `set_classification` kèm `confidence_pct: 40` → phiếu 85 = `latest_classification[1]` |
| AC-22 (W-2) | `erp_ai/agent/tools/test_write_ticket.py::TestConfidenceSource::test_set_classification_never_writes_confidence_pct` `[mới]` | khóa thừa `confidence_pct` → `values` không có `ai_confidence_pct`, phiếu không đổi |
| AC-22 (W-2) | `…test_write_ticket.py::TestConfidenceSource::test_set_classification_schema_has_no_confidence_pct` `[mới]` | schema tool không có thuộc tính `confidence_pct` |
| AC-22 (phán quyết 2) | `erp_ai/agent/tools/test_route_ticket.py::TestConfidencePct::test_apply_route_writes_confidence_pct` `[mới]` | 85 → phiếu 85 và trong `after`; người đã phân loại → không ghi |
| AC-22 (phán quyết 2) | `…test_route_ticket.py::TestConfidencePct::test_only_route_ticket_assigns_ai_confidence_pct` `[mới]` | AST: chỉ `route_ticket.py`, `install.py` gán trường |
| AC-22 (phán quyết 2) | `erp_ai/agent/test_runner_routing.py::TestConfidencePct::test_classify_row_pct_equals_ticket_after_route` `[mới]` | `predicted_confidence_pct` = `ai_confidence_pct` |
| AC-22 (phán quyết 2) | `…test_runner_routing.py::TestConfidencePct::test_below_threshold_ticket_pct_unchanged` `[mới]` | 69 → phiếu không đổi |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_proposal_needs_confidence_and_evidence` | thiếu dòng độ tin cậy; `101%`; thiếu/rỗng "Căn cứ"; đủ → đăng; từ chối → 0 Comment |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_bad_kind_refused` | `kind` thiếu, `"x"` |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_below_threshold_one_question_with_footer` | `de_xuat` → `REASON_ASK_ONLY`; `hoi` thiếu Căn cứ → từ chối; `hoi` đủ → đăng "69% (ngưỡng 70%)"; lần hai → `REASON_ONE_ASK` |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_footer_threshold_80_and_unknown_pct` | ngưỡng 80; pct None → "chưa có" |
| AC-22 (Fix 9) | `…test_write_ticket.py::TestPostCommentKinds::test_marked_run_refuses_comment_question` `[mới]` | `mark_asked` trước → `REASON_ONE_ASK`, 0 Comment; `mark_asked("")` → `ValueError` |
| AC-22 | `erp_ai/agent/test_agent_runner.py::TestAskOnly::test_stub_69_70_100` | 69 → 0 ghi, đúng 1 comment hỏi; 70, 100 → định tuyến |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_model_posts_nothing_fallback_one_comment` | mục `post_notice` `ask_fallback` ở dòng `reason` cuối |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_model_asks_twice_one_posted` | 1 Comment |
| AC-22 (Fix 9) | `…test_agent_runner.py::TestAskOnly::test_marked_run_no_fallback` `[mới]` | cờ đặt sẵn → 0 `ask_fallback` |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_threshold_80_with_75_asks` | |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_missing_evidence_error_reaches_model_comment_not_posted` | `tool_result` có `REASON_NO_EVIDENCE`; 0 Comment |
| AC-23 | `erp_ai/agent/test_runner_routing.py::TestOneCommentPerAction::test_route_success_one_comment_lists_fields_assignee_task` | 1 comment có Loại, Nhóm, "Đã gán", "Đã tạo Task" |
| AC-23 | `…test_runner_routing.py::TestOneCommentPerAction::test_success_with_failure_line_still_one_comment` | gán lỗi → 1 comment |
| AC-23 | `…test_runner_routing.py::TestOneCommentPerAction::test_no_field_change_one_comment` | `ROUTE_NO_CHANGE` |
| AC-23 | `erp_ai/agent/test_agent_runner.py::TestRunNotices::test_matrix_eight_situations` | 8 ca: 1,1,1,1,0,0,0,0 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_daily_limit_repeated_same_day_one_comment` | 3 lần → 1; hôm qua → thêm 1 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_over_budget_once_a_day_only_when_level_lost` | L3 hai lần → 1; gốc L1 → 0 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_failures_one_comment_until_next_success` | lỗi, lỗi → 1; thành công; lỗi → 2 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_gateway_error_at_l0_no_comment` | |
| AC-23 (Fix 8) | `…test_agent_runner.py::TestRunNotices::test_notice_only_for_listed_triggers` `[mới]` | trigger `"x_unlisted"`: 3 thông báo → 0; `daily_limit` → 1 |
| AC-23 (AC-10) | `…test_agent_runner.py::TestRunNotices::test_each_notice_has_one_action_entry` | mục có `ACTION_KEYS`; chống trùng → 0 mục |
| AC-24 | `erp_ai/agent/test_agent_runner.py::TestTicketFields::test_four_cases` | có/không trường × có/không cấu hình |
| AC-24 | `…test_agent_runner.py::TestTicketFields::test_unconfigured_one_log_line_per_run` | 1 dòng logger; trường bị xóa → lần chạy tiếp tục |
| AC-24 | `erp_ai/agent/test_prompts.py::TestTicketFields::test_classify_request_unchanged_without_fields` | bằng từng byte |
| AC-24 | `…test_prompts.py::TestTicketFields::test_fields_labelled_cut_and_ordered` | 300 → 200 ký tự; HTML bỏ; khóa lạ → `ValueError` |
| AC-19, 25, 27, 28 (runner) | `erp_ai/agent/test_runner_routing.py::TestRunnerHooks::test_due_value_reaches_decide_route`, `::test_d_watcher_followed_once`, `::test_watcher_notify_off_logged`, `::test_split_comment_once_in_route_comment` | B hạn 10 giờ → High; D 2 lần → 1 Document Follow; tách phiếu trong comment định tuyến, không lặp |
| AC-27 (phán quyết 4) | `…test_runner_routing.py::TestRunnerHooks::test_watcher_failure_rolls_back_only_watcher_unit` `[mới]` | `follow_document` ném → 0 Document Follow, trường và gán vẫn ghi, mục `add_watcher` `ok=false` trên dòng `classify` |
| AC-23, 28 (phán quyết 4) | `…test_runner_routing.py::TestRunnerHooks::test_routing_step_makes_no_gateway_call` `[mới]` | 0 lời gọi cổng model trong `_route` |
| AC-62 | `erp_ai/agent/tools/test_write_ticket.py::TestBaNote::test_full_note_posted_with_marker` | dòng 1 = marker; không lặp marker |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_missing_or_empty_section_refused` | 5 mục thiếu/rỗng; Có/Không; Nguồn; độ tin cậy → 0 Comment |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_second_note_refused` | `REASON_BA_NOTE_EXISTS` |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_not_c_or_main_path_l0_refused` `[sửa]` | đầu mục B; `ctx.main_path_level = "L0"` (không đặt qua Setting) |
| AC-62 (W-3) | `…test_write_ticket.py::TestBaNote::test_gate_reads_context_level_not_settings` `[mới]` | ctx L0 + cap C L3 → từ chối; ctx L1 + cap C L0 → đăng |
| AC-62 (W-3) | `…test_write_ticket.py::TestLevelNotRecomputed::test_no_level_function_called_in_tools` `[mới]` | AST `erp_ai/agent/tools/*.py`: 0 lời gọi `main_path_level`, `category_level_cap`, `effective_level` |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_below_threshold_only_question` | 69% → `ba_note` bị `REASON_ASK_ONLY`; `hoi` đăng được |
| AC-62 | `erp_ai/agent/test_prompts.py::TestCategoryC::test_hint_only_for_c` | C + `ticket_insert`/`comment_mention` có gợi ý; A–F khác, `classification=None` không có |
| AC-62 (Fix 7) | `…test_prompts.py::TestCategoryC::test_hint_skipped_for_other_triggers` `[mới]` | C + `kb_draft`, `requester_reply`, `change_action` → không có `TASK_CATEGORY_C` |
| AC-62 | `erp_ai/agent/test_agent_runner.py::TestCategoryC::test_two_runs_one_ba_note` | 2 lần chạy → 1 BA note |
| AC-63 | `erp_ai/agent/tools/test_write_ticket.py::TestCreateTaskEstimate::test_three_tasks_with_estimates` | `expected_time`, `ai_ticket` |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_missing_or_non_positive_estimate_refused` | thiếu, 0, −1, `"2"`, `True` |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_eleventh_task_in_run_refused` | mặc định 10; cấu hình 3; `run_id` mới đếm lại |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_same_subject_not_duplicated` | khoảng trắng, hoa thường |
| AC-63 (AC-10) | `erp_ai/agent/test_agent_runner.py::TestCategoryC::test_each_task_one_action_entry` | 3 mục, `value_after` có `expected_hours` |

Test cũ phải sửa theo AC (NFR-8, STD-TEST-5, ghi lý do trong commit): như addendum `:448`; thêm: không test cũ nào gọi `set_classification` với `confidence_pct` (tham số chưa từng có trên `develop`).

### Đối chiếu AC (Done criteria)

```
AC giao (arch-impact.md:179, :182, lệnh giao việc): AC-17, AC-21, AC-22, AC-23, AC-24, AC-62, AC-63
  (+ phần runner: AC-19, AC-25, AC-27, AC-28 — phán quyết (4))
AC có trong test plan R2:                         AC-17, AC-21, AC-22, AC-23, AC-24, AC-62, AC-63
  (+ AC-19, AC-25, AC-27, AC-28 ở TestRunnerHooks)
Khớp 7/7 (+4/4). Mỗi finding major có ít nhất 1 test: W-1 (4), W-2 (3), W-3 (2).
```

---

## R3 — Giả định (thay bảng "Assumptions decided by the team" của addendum)

A-U4b-3 … A-U4b-10, A-U8-1 … A-U8-4 giữ nguyên văn addendum `:464-475`. Dòng thay và dòng thêm:

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U4b-1 `[sửa]` | Tập trường người gõ lúc tạo lưu ở HD Ticket `ai_created_labels` (permlevel 8, T22a cài); lấy ở `before_insert` vào cờ, ghi ở `validate` khi `is_new()`, giữ cố định ở `validate` các lần sau | phán quyết (1): trường bền qua quét bù và mọi lần `@ai`; ghi sau bước xóa permlevel cao của Frappe nên không mất với khách và người không có mức 8 (W-1); không `save()` thêm (ADR-033 Ràng buộc 3) | tham số job `created_labels` (bị loại ở phán quyết (1)) | — (đã có phán quyết) |
| A-U4b-2 `[sửa cột Vì]` | Bước định tuyến tôn trọng trường người điền bằng cách đưa `decision` đã bỏ trường vào `apply_route` | `apply_route` chỉ thêm một giá trị (Fix 5); giữ phần lọc ở runner để `predicted_*` của dòng log vẫn là dự đoán gốc (AC-19) và `set_classification` dùng cùng `keep_human_fields` | lọc trong `apply_route` | chuyển `keep_human_fields` vào `apply_route` |
| A-U4b-11 `[mới]` | `ai_confidence_pct` chỉ do `apply_route` ghi; phiếu chưa định tuyến (dưới ngưỡng, người đã phân loại) giữ trường rỗng, kể cả khi sau đó `set_classification` chạy trong lần lệnh trực tiếp có (3) bật | phán quyết (2), W-2: một đường ghi, một nguồn; số vẫn có trên dòng `classify` (AC-19, AC-22) | `set_classification` chép `latest_classification[1]` lên phiếu (đường ghi thứ hai) | thêm vào `set_classification` một lời gọi tới hàm ghi của `route_ticket.py` (vẫn một chỗ gán) |
| A-U4b-12 `[mới]` | Mỗi lần chạy tối đa một câu hỏi, mọi kênh; câu hỏi qua email của U6b đánh dấu bằng `mark_asked` | tránh hai câu hỏi trong một lần chạy (mục 5 của review); cờ sống trong một job như A-U4b-8 | email không tính, có thể có 2 câu hỏi | `reply.py` không gọi `mark_asked` |
| A-U4b-13 `[mới]` | Thông báo `over_budget`, `run_failed`, `ask_fallback` theo danh sách trigger cho phép `NOTICE_TRIGGERS`; `daily_limit` không lọc | fail-closed: lần chạy `kb_draft` trên phiếu đã đóng, dòng cấp cố định không có tool comment (mục 5 của review); ba trigger hiện có giữ hành vi | danh sách cấm do U6b thêm điều kiện | thêm/bớt trigger trong ô của bảng |
| A-U8-5 `[mới]` | Chốt BA note lấy đầu mục của lần chạy bằng `policy.latest_classification` và mức đường chính bằng `ctx.grant_inputs().main_path_level` | `ToolContext` (U1, `registry.py`) không có trường đầu mục và U8 không sửa `registry.py`; không tính lại mức trong tool (W-3). Ca lệch duy nhất: `@ai` dựng context trước khi dòng `classify` đầu tiên của phiếu được ghi (đầu mục chưa biết → L1 theo ADR-030 QĐ 2) rồi tool thấy C; lần chạy đó không có gợi ý C nên model hiếm gọi `ba_note` | thêm trường `category` vào `ToolContext` | U1/chủ `registry.py` thêm `ToolContext.category`, runner đặt, tool đọc |

Câu hỏi nghiệp vụ: 0.

---

## R4 — Hợp đồng mới hoặc đổi cho đơn vị sau (bổ sung mục 3.5 của addendum)

| Tên | Chữ ký / giá trị | Module | Đơn vị gọi |
|---|---|---|---|
| `mark_asked` | `(run_id: str) -> None` | `erp_ai/agent/tools/write_ticket.py` | U6b `reply.py` (Fix 9) |
| `NOTICE_TRIGGERS` | `dict[str, tuple[str, ...]]`, 3 khóa | `erp_ai/agent/runner.py` | U6b: thêm `TRIGGER_REQUESTER_REPLY` vào ô cần; không thêm `TRIGGER_KB_DRAFT`; cùng commit thêm `kb_draft` có test `kb_draft` + vượt ngân sách / lỗi cổng → 0 thông báo |
| `CATEGORY_HINT_TRIGGERS` | `(TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)` | `erp_ai/agent/prompts.py` | U7 nếu thêm gợi ý theo đầu mục |
| `CREATED_LABELS_FIELD`, `CREATED_LABELS_FLAG` | `"ai_created_labels"`, `"erp_ai_created_labels"` | `erp_ai/handlers.py` | U4a báo cáo đọc `created_labels` trên log, không đọc trường |
| `apply_route` | ghi thêm `ai_confidence_pct`; đường ghi duy nhất | `erp_ai/agent/tools/route_ticket.py` | không đơn vị nào khác gán trường này |

---

## Bảng đóng: finding hoặc phán quyết → fix

| Finding / phán quyết (`arch-review-design-w1b.md`) | Giải bởi |
|---|---|
| W-1 (major, `ai_created_labels` permlevel 0, ghi ở `before_insert`) | Fix 1 (+ Fix 4 cho chủ trường); test W-1 ×4 ở R2 |
| W-2 (major, hai nguồn độ tin cậy) | Fix 2 (+ Fix 5); test W-2 ×3 ở R2 |
| W-3 (major, tool tính lại mức đường chính) | Fix 3; test W-3 ×2 ở R2; A-U8-5 |
| Minor (a)–(e) của mục 2 | Fix 11 ((c) qua Fix 7, (d) qua Fix 5) |
| Phán quyết (1) `ai_created_labels` ở T22a | Fix 4 (thời điểm ghi: Fix 1) |
| Phán quyết (1b) quyền HD Article | không thuộc U4b/U8 (U0 T22a) |
| Phán quyết (2) `route_ticket.py`, `apply_route` ghi duy nhất | Fix 5 |
| Phán quyết (3a)–(3e) | không thuộc U4b/U8 (U6b) |
| Phán quyết (4) phần runner AC-19, 25, 27, 28 | Fix 6 |
| Mục 5 `prompts.py` (thứ tự, gợi ý C với `kb_draft`) | Fix 7 |
| Mục 5 `runner.py` (thứ tự, thông báo ở `kb_draft`) | Fix 8 |
| Mục 5 `write_ticket.py` (hai câu hỏi) | Fix 9 |
| Mục 5 `handlers.py`, `registry.py` | Fix 10 |
| Mục 6 ghi chú grep `confidence_threshold` của U1 | Fix 11 (e) — sửa ở test của U1, ngoài file U4b/U8 |
| `arch-review-design-w1a.md` C-5 (hình dạng `_classify`) | Fix 12 |
