Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Phán quyết thiết kế đợt 0, lần 2 — FEAT-007 (sau ba design-defect T3, T24, T41)

## 0. Cách đọc

- File này **thắng** `design.md` và `design-w0-fixes.md` ở mọi chỗ khác nhau. Mỗi phán quyết ghi: dòng bị thay, văn bản thay đầy đủ, task bị đổi (file, tiêu chí, test), test chứng minh. Phần không nhắc ở đây giữ nguyên.
- Không đổi spec, AC, luật nghiệp vụ hay ADR. Tuân ADR-001 (lớp import), ADR-003/ADR-013 QĐ 2 và ADR-033 QĐ 6 (một chỗ enqueue, job theo lịch), ADR-006 (permlevel 8), ADR-030 QĐ 4 (một vị từ dưới ngưỡng), ADR-034 QĐ 2 (một hàm che bí mật).
- Designer không đánh số task mới; "task sửa nhỏ" dưới đây do tech-lead đặt số và chèn vào `tasks.md`.

**Căn cứ đọc trực tiếp (đích đã biết, không qua Explore), 2026-11-14:** `review-03.md`, `review-24.md`, `review-41.md`, `review-35.md`, `review-27.md`; `journal-part8.md` dòng "19:00 DỪNG build" và dòng "tech-lead chọn skill"; `design.md:229-252, 364-430, 484-495`; `design-w0-fixes.md`; `design-addendum-1-U1.md:61, 117, 129-130, 262, 339, 423, 459`; `design-addendum-1-U4b-U8.md:33, 245`; `design-addendum-1-U3.md:69`; `design-addendum-2-U5b.md:48`; `tasks.md` T3, T22, T24, T26, T34, T35, T41, T44, T60; mã: `erp_ai/install.py:107-212` (`develop`), `erp_ai/eval/run_eval.py:36-42, 198`, `team/FEAT-007-task-24:erp_ai/agent/routing.py:60-85, 147-166`, `team/FEAT-007-task-41:erp_ai/agent/ops_data.py`, `team/FEAT-007-task-35:erp_ai/agent/redact.py`, `team/FEAT-007:erp_ai/agent/classification.py:118-160`, `team/FEAT-007:erp_ai/test_utils.py:102-136`, `team/FEAT-007:erp_ai/tests/test_architecture.py` (`LAYER_RULES`: `erp_ai.agent` cấm import `erp_ai.eval`); Frappe v15 `frappe/database/schema.py:197-203` (Check, Int, Currency, Float, Percent đều `not null default <số>`), `frappe/model/document.py:978-984, 1935-1945` (`_set_defaults` → `update_if_missing` điền mặc định khi giá trị là `None`); `erp_ai/patches.txt` (hai mục rỗng), `erp_ai/agent/tools/site_api.py:38` (`SECRET_FIELDS`), ERP AI Credential `api_key` là Password.

---

## 1. Phán quyết (1) — T3: `predicted_confidence_pct` Int, mặc định -1 = không biết

**Vấn đề.** Frappe không có kiểu số rỗng được: Int (và Float, Percent, Currency) luôn là `NOT NULL DEFAULT <số>` (`schema.py:197-203`). Với mặc định 0, dòng cũ đọc ra 0, mà 0 ≥ ngưỡng 0 → độ tin cậy không biết bị tính là đủ ngưỡng (fail-open, trái NFR-4); U1 (`:130, :339, :459`) chờ `None`.

**Quyết định.** Giữ Int; đặt `default` = `"-1"`. **-1 nghĩa là "không biết".** Giá trị hợp lệ là 0..100. Vì -1 nhỏ hơn mọi ngưỡng 0..100, kể cả người đọc quên quy đổi cũng fail-closed. Bỏ phương án Data (số dạng chuỗi): mỗi người đọc phải tự parse, so sánh và sắp xếp trong SQL sai, báo cáo không cộng được.

**Thay dòng `design.md:234`** bằng:
> | `predicted_confidence_pct` | Int, `default` `"-1"` (cột `NOT NULL DEFAULT -1`). Giá trị hợp lệ 0..100; **-1 = không biết** (dòng có trước cột, lần phân loại không trả số, dòng không phải `classify`) | runner (U1/U4b): chỉ ghi số nguyên 0..100; không có số hợp lệ thì không truyền khóa hoặc truyền `None` (Frappe điền -1); không bao giờ ghi 0 thay cho "không biết" | U1 (`latest_classification`), báo cáo: giá trị ngoài 0..100 đọc là không biết, hiển thị rỗng (không hiện "-1", không hiện "0%") | AC-22, D-14, NFR-4 |

**Mô tả trường** (DocField `description`, thay chữ T3 đang có): `"Độ tin cậy 0–100 của bước phân loại. -1 = không biết (dòng tạo trước khi có cột, hoặc model không trả số)."` Cụm bắt buộc trong `DOCTYPE_CONFIG["ERP AI Log"]` cho trường này: `"-1"` và `"không biết"`.

**Đối soát dữ liệu (site đã migrate cột với mặc định 0, tức `miyano`).** Patch `post_model_sync` mới:
- `erp_ai/patches/feat007_unknown_confidence_pct.py`, `execute()`: đổi `predicted_confidence_pct` từ 0 thành -1 trên `tabERP AI Log`, theo lô 10 000 dòng (`UPDATE … WHERE predicted_confidence_pct = 0 LIMIT 10000`, lặp tới khi 0 dòng đổi). Không có tham số người dùng.
- `erp_ai/patches.txt`, mục `[post_model_sync]`: thêm `erp_ai.patches.feat007_unknown_confidence_pct`.
- Vì sao an toàn: ở đợt 0 chưa mã nào ghi cột này (người ghi là U1, đợt 1), nên mọi số 0 đang có đều là "không biết". Patch chạy đúng một lần (Patch Log). Trên site chưa có cột (production), cột được tạo với mặc định -1 trước khi patch chạy, nên patch không đổi dòng nào. Patch phải vào **cùng commit** với việc đổi `default`.
- Kiểm có đầu ra: sau `cmd.migrate` trên `miyano`, `select count(*) from tabERP AI Log where predicted_confidence_pct = 0` = 0. Dán kết quả vào `acceptance.md`.
- **Chiều xuống (STD-OPS-2):** revert commit → lần `cmd.migrate` sau đặt lại mặc định cột về 0; các giá trị -1 còn lại vẫn đọc là "không biết" theo luật đọc dưới đây, nên không cần đảo dữ liệu. Lùi cả feature: cột thừa xử lý theo T23 (dòng thừa vô hại).

**Văn bản U1 phải theo** (addendum đợt 1 đã duyệt `design-addendum-1-U1.md`; chỉ làm rõ, **không đổi chữ ký hay kiểu**):
- `:61` → `| predicted_confidence_pct (Int, mặc định -1 = không biết) trên ERP AI Log | Có (design.md:234 theo design-w0-fixes-2.md mục 1, D-5) |`
- `:130` → `| latest_classification | dòng classify mới nhất của phiếu có predicted_category khác rỗng → (predicted_category, pct), với pct = predicted_confidence_pct khi giá trị nằm trong 0..100, ngược lại (-1, None, ngoài khoảng) None; không có dòng → (None, None) | — |`
- `:262` thêm câu cuối: "`classification.confidence_pct` là `None` hoặc ngoài 0..100 → không truyền `predicted_confidence_pct` (cột nhận -1)."
- `:339` → "- **Schema:** không (U0 làm chủ). **Dữ liệu:** không ghi dữ liệu cũ. Dòng ERP AI Log có trước cột, và mọi dòng không ghi số, mang `predicted_confidence_pct = -1` (mặc định cột của U0; site đã có cột với mặc định 0 được patch `feat007_unknown_confidence_pct` của U0 đổi 0 → -1 một lần) → `latest_classification` trả pct None (A-U1-1)."
- `:459` (A-U1-1, cột "Chọn") → "Độ tin cậy không biết (`predicted_confidence_pct` = -1 hoặc ngoài 0..100: phiếu cũ, phân loại không trả số, chưa phân loại thành công) = dưới ngưỡng, kể cả khi ngưỡng = 0; trừ người ra lệnh ∧ (3) bật".
- Test plan U1 (`:423`): `erp_ai/agent/test_policy.py::TestConfidence::test_threshold_boundaries` thêm ca ngưỡng 0: `None` → dưới; `-1` → dưới; `0` → không dưới. Thêm dòng: `erp_ai/agent/test_policy.py::TestConfidence::test_latest_classification_minus_one_reads_none` (dòng `classify` -1 → `(cat, None)`; 0 → `(cat, 0)`; 70 → `(cat, 70)`; 101 → `(cat, None)`).

**Task bị đổi.**
- **T3** (làm lại trên `team/FEAT-007-task-3` @ `d66389a`): files thêm `erp_ai/patches.txt`, `erp_ai/patches/feat007_unknown_confidence_pct.py` (mới), `erp_ai/patches/test_feat007_unknown_confidence_pct.py` (mới). Returns: `predicted_confidence_pct` Int **`default "-1"`**, mô tả như trên; patch như trên. Các cột khác, `field_count` 43, `test_feat007_log_columns_have_design_types` giữ nguyên.
- U1 (đợt 1): chỉ văn bản và test nêu trên.

**Test chứng minh** (T3, `erp_ai/patches/test_feat007_unknown_confidence_pct.py`, lớp gọi `keep_agent_settings`):
- `TestUnknownConfidencePct::test_column_default_is_minus_one`: meta `default` = `"-1"`; `information_schema.columns.COLUMN_DEFAULT` của cột trong `tabERP AI Log` = `-1` (chứng cứ đã migrate).
- `::test_row_without_pct_reads_minus_one`: chèn dòng `classify` không có `predicted_confidence_pct` → DB đọc -1; dòng ghi 0 → đọc 0.
- `::test_patch_turns_zero_into_minus_one_only`: ba dòng 0, 55, -1 → sau `execute()` là -1, 55, -1; chạy lần hai không đổi dòng nào.
- NFR-4 ở ngưỡng 0: hai test U1 nêu trên (đợt 1).

**Ghi chú ngoài phạm vi (không chặn, chuyển team-leader):** HD Ticket `ai_confidence_pct` (T22, Int) cũng `NOT NULL DEFAULT 0`, nên câu "phiếu chưa định tuyến giữ trường rỗng" ở `design-addendum-1-U4b-U8-fixes.md:460` (A-U4b-11) không đúng được: phiếu sẽ hiện 0. Trường này chỉ để hiển thị (nguồn quyết định duy nhất là `latest_classification`, Fix 2), nên NFR-4 không bị ảnh hưởng; cách hiển thị do designer U4b quyết ở đợt 1.

---

## 2. Phán quyết (2) — T24: `due_field_configured: bool | None = None`, `None` = nơi gọi không nói

**Quyết định.** Chọn phương án (b) của `review-24.md`. Ba trạng thái:

| `due_field_configured` | Ghi chú `due_at` cho B/D | Dùng `due_at` cho ngoại lệ |
|---|---|---|
| `None` (mặc định; ba nơi gọi cũ `runner.py:281`, `write_ticket.py:50`, `run_eval.py:198`) | không | có, nếu `due_at` được truyền (nơi gọi cũ không truyền → không có ngoại lệ) |
| `False` | có: `{"field": "due_at", "reason": DUE_FIELD_MISSING_NOTE}` | không (bỏ qua `due_at`) |
| `True` | không | có |

Điều kiện trong mã: `classification.category in ("B", "D") and due_field_configured is False`. Không dùng `not due_field_configured`.

**Thay `design.md:382`** bằng:
> - `decide_route(..., *, team_exists, is_excluded_team, is_active_agent, due_at: date | datetime | None = None, due_field_configured: bool | None = None, d_watcher: str | None = None, now: datetime | None = None)`: tham số mới đều có mặc định. Nơi gọi không truyền chúng (ba nơi gọi hiện có: `runner.py:281`, `write_ticket.py:50`, `run_eval.py:198`) nhận **đúng** `priority` và `notes` như trước (hợp đồng thêm, không sửa). `due_field_configured = None` nghĩa là "nơi gọi không nói": không ghi chú, không ngoại lệ trừ khi có `due_at`.

**Thay `design.md:387`** bằng:
> - B hoặc D ∧ `due_field_configured is False` → thêm `notes` `{"field": "due_at", "reason": "chưa cấu hình trường Hạn hoàn thành, bỏ qua ngoại lệ theo hạn"}` và bỏ qua `due_at` (runner ghi notes vào log như hiện nay; đây là "1 dòng log" của AC-25). `None` → không ghi chú.

**Task bị đổi.** **T24** (làm lại trên `team/FEAT-007-task-24` @ `c02e355`, cùng 2 file): Returns `due_field_configured: bool | None = None`; điều kiện `is False`; thêm `as_deadline` (phán quyết 5c). Expect thêm 2 test dưới đây; minor (1) của `review-24.md` làm cùng lần (ca A dùng mapping có A là Medium). U4b (`design-addendum-1-U4b-U8.md:245`) truyền `due_field_configured=<bool>` nên không đổi kiểu, chỉ có thêm ràng buộc ở phán quyết 5c(ii).

**Test chứng minh** (`erp_ai/agent/test_routing.py`):
- `TestPriorityExceptions::test_old_call_shape_no_due_note` (mới): 6 đầu mục, lời gọi kiểu cũ (không tham số mới) → `notes` không có mục `field == "due_at"`; `priority` bằng giá trị viết thẳng của luật cũ.
- `::test_missing_due_field_note` (sửa): truyền rõ `due_field_configured=False` → B, D có ghi chú; A, C, E, F không.
- `::test_truth_table`, `::test_existing_rules_kept`: giữ, phải xanh.

---

## 3. Phán quyết (3) — T41: một `ticket_type` cho nhiều đầu mục → đầu mục đứng trước theo `CATEGORIES` thắng

**Quyết định.** Chọn phương án (b) của `review-41.md`. Luật: khi nhiều đầu mục trong `category_mapping` có cùng `ticket_type`, đầu mục **đứng trước theo thứ tự `CATEGORIES` (A → F)** thắng, không phụ thuộc thứ tự khóa trong JSON. Đây đúng là luật đang có của `run_eval._expected_category` (`run_eval.py:36-42`), nên `run_eval.py` không đổi.

Bỏ phương án (a) (chặn lúc lưu): `_mapping_error` được `load_mapping` dùng, nên một site đã có `ticket_type` trùng sẽ nhận mapping `{}` và việc định tuyến tắt hẳn; cấm admin đặt trùng cũng là một luật nghiệp vụ, designer không tự đặt.

**Thay `design.md:423`** bằng:
> - `category_by_ticket_type(mapping) -> dict[str, str]`: đảo `category_mapping` (ticket_type → đầu mục). Duyệt theo `CATEGORIES` (import từ `erp_ai.constants`), không theo thứ tự JSON; bỏ đầu mục có `ticket_type` rỗng và khóa không thuộc `CATEGORIES`; `ticket_type` trùng → giữ đầu mục gặp trước (`setdefault`), cùng luật với `run_eval._expected_category`. Hệ quả ghi trong docstring: phiếu của đầu mục thua được tính vào đầu mục thắng ở báo cáo độ chính xác, KPI (U5a), báo cáo 08:00 (kể cả `c_missing_ba_note`). `ticket_category(ticket_row: dict, reverse_map: dict[str, str]) -> str | None`: tra `ticket_row.get("ticket_type")`; rỗng hoặc không có → `None`.

**Task bị đổi.** **T41** (làm lại trên `team/FEAT-007-task-41` @ `dc96b9a`): files thêm `erp_ai/eval/test_run_eval.py` (sửa, chỉ test; `run_eval.py` không đổi). Test kiểm sự khớp đặt dưới `eval` vì `LAYER_RULES` cấm `erp_ai.agent` import `erp_ai.eval`, còn `eval` được import `agent`. Minor của `review-41.md` (type hint của `ticket_row`) làm cùng lần. `design-addendum-2-U5b.md:48` giữ tên và kiểu; hành vi nay đã xác định. T45, T50, T51 nhận luật này qua `Receives`, không đổi chữ.

**Test chứng minh.**
- `erp_ai/agent/test_ops_data.py::TestCategoryLookup::test_shared_ticket_type_earliest_category_wins` (mới): mapping JSON `{"C": {"ticket_type": "X"}, "A": {"ticket_type": "X"}, "B": {"ticket_type": "Y"}}` → `{"X": "A", "Y": "B"}`; cùng mapping với thứ tự khóa đảo → cùng kết quả.
- `erp_ai/eval/test_run_eval.py::TestCategoryRuleShared::test_expected_category_agrees_with_ops_data` (mới): với mapping va chạm trên và `DEFAULT_CATEGORY_MAPPING`, mọi `ticket_type` t: `run_eval._expected_category(t, m) == ops_data.ticket_category({"ticket_type": t}, ops_data.category_by_ticket_type(m))`.

**Không chặn (team-leader):** `category_mapping` thật trên `miyano` có trùng hay không chỉ ảnh hưởng số liệu, không ảnh hưởng tính đúng của mã nữa.

---

## 4. Phán quyết (4) — T60: trường ẩn `ai_created_labels` không có dòng trong HD Ticket Template

**Quyết định.** Không có dòng mẫu phiếu. Dòng mẫu của trường AI là `visible_to: "Agents"` (`install.py:203`); giao diện agent của Helpdesk hiện các trường theo dòng mẫu, trong khi trường này chỉ để server dùng (ghi ở `validate`, `design-addendum-1-U4b-U8-fixes.md` Fix 1). Luật viết chung, không theo tên: `_ensure_template_rows` **bỏ qua mọi spec có `hidden` = 1**. Hàm không xóa dòng mẫu đã có (dòng do người thêm là quyết định của người).

**Thay chữ `Returns` của T60** đoạn "dòng mẫu phiếu của trường này sinh ra như mọi trường AI khác" bằng:
> trường này **không** có dòng trong HD Ticket Template: `_ensure_template_rows` bỏ qua mọi spec có `hidden` = 1 (điều kiện thêm vào bộ lọc `spec["fieldname"] != AI_SECTION_FIELD` ở `install.py:195`); không xóa dòng mẫu có sẵn.

`Receives` của T60: `_ensure_template_rows` (sửa: bỏ qua spec ẩn) thay cho "(không đổi)". Touchpoint không đổi (`install.py`, `test_install.py`). Không addendum đợt 1/2 nào nói khác (`design-addendum-1-U4b-U8-fixes.md:124` chỉ nêu thuộc tính trường).

**Test chứng minh** (`erp_ai/tests/test_install.py`):
- `TestFeat007Migrate::test_hidden_labels_field_has_no_template_row` (mới, vào Expect của T60): sau `ensure_setup` hai lần → 0 dòng `HD Ticket Template Field` có `fieldname = "ai_created_labels"` trong mẫu `Default`; Custom Field `HD Ticket-ai_created_labels` có `hidden` = 1.
- `TestInstall::test_ai_fields_permlevel_8_and_template_rows_agents_only`: không sửa, phải xanh (`AI_FIELDS` là danh sách viết thẳng, không có trường mới).

---

## 5. Phán quyết (5) — năm điểm không chặn

### 5a — T35: luật "tên chứa một từ bí mật" theo **đoạn tên**, không theo chuỗi con

**Vấn đề.** Theo chuỗi con, `input_tokens`, `output_tokens` (`runner.py:97` `USAGE_COLUMNS`, `gateway/__init__.py:25` `USAGE_FIELDS`) bị che, làm hỏng số đếm sử dụng trong log (NFR-6 đưa log qua hàm này).

**Thay `design.md:486`** từ "và giá trị sau `api_key|…|mật khẩu` + `:`/`=` (giữ tên khóa)" đến hết câu bằng:
> và giá trị sau một **tên khóa bí mật** + `:`/`=` (giữ tên khóa). Tên khóa bí mật được quyết bằng `is_secret_key(name)`:
> 1. Chuẩn hóa NFC; chèn ranh giới ở chỗ chữ thường hoặc số đứng trước chữ hoa (`accessToken` → `access|Token`); `casefold()`; tách theo `[\s_\-.]+`; bỏ đoạn rỗng.
> 2. `SECRET_WORDS = ("api_key", "api_secret", "token", "secret", "password", "passwd", "pwd", "mật khẩu")`, mỗi từ tách cùng cách thành dãy đoạn (`api_key` → `api`, `key`).
> 3. Tên là bí mật khi dãy đoạn của một từ xuất hiện **liền nhau** trong dãy đoạn của tên.
>
> Ví dụ `True`: `api_key`, `x_api_key`, `apiKey`, `api_secret`, `access_token`, `accessToken`, `clientSecret`, `new_password`, `reset_password_key`, `Mật khẩu` (cả dạng NFD), `smtp_pwd`. Ví dụ `False`: `input_tokens`, `output_tokens`, `max_tokens`, `tokenizer`, `primary_key`, `subject`.
> `redact_secrets` chuẩn hóa NFC văn bản trước khi so. Mẫu khóa-giá trị tìm **ứng viên** tên khóa một lần cho mỗi dãy chữ (`(?<![\w-])`, tên = một hoặc hai cụm `[\w-]+` cách nhau đúng một dấu cách), rồi callback thay thế gọi `is_secret_key(tên)`. Không phải bí mật → trả nguyên đoạn khớp. Công việc tuyến tính theo độ dài văn bản. Năm mẫu còn lại (`sk-ant-…`, `sk-…` ≥ 16, `Bearer`, `token <key>:<secret>`, JWT) giữ nguyên.

**Task bị đổi.** **T35** vòng 3 (FIX_BASE `9a39527`, cùng 2 file). Đây là thay đổi thiết kế, không phải finding của dev. Vòng này gộp cả finding STD-TEST-8 vòng 2 (cách callback ở trên giải luôn finding đó). Tiêu chí T35: thay "`name.casefold()` chứa một từ của cùng danh sách" bằng luật đoạn tên ở trên. **Addendum đợt 1 đã duyệt bị đổi chữ:** `design-addendum-1-U3.md:69` (hành vi cần của `is_secret_key`: "`name.casefold()` chứa…" → "luật đoạn tên của `design-w0-fixes-2.md` 5a"). Tên và chữ ký `is_secret_key(name: str) -> bool` không đổi. 4 tên của `site_api.SECRET_FIELDS` vẫn là `True`.

**Test** (`erp_ai/agent/test_redact.py`): `TestRedact::test_is_secret_key_names` (thêm mọi ví dụ True/False trên); `::test_usage_counters_not_masked` (mới: `"input_tokens: 1200, output_tokens: 512, api_key=abc"` → chỉ `abc` bị che); `::test_nfd_vietnamese_key_masked` (mới); `::test_long_run_without_secret_untouched` thêm `"pwd" * 33_334` và `"Token" * 20_000` (không `:`/`=`), giữ biên thời gian hiện có.

### 5b — T27: `{n}` là tổng số yêu cầu; yêu cầu rỗng không tính

**Thay `design.md:409`** bằng:
> `split_request_comment(classification) -> str | None`: mỗi yêu cầu được gộp mọi dãy khoảng trắng (kể cả xuống dòng) thành một dấu cách, trim, bỏ yêu cầu rỗng; gọi n là số yêu cầu còn lại. `needs_split` ∧ n ≥ 2 → chuỗi `"Phiếu này có vẻ gồm {n} yêu cầu:\n1. …\nk. …\n"` liệt kê **tối đa 10** yêu cầu đầu (mỗi yêu cầu cắt 200 ký tự). Khi n > 10, thêm ngay sau mục 10 dòng `"… và {n − 10} yêu cầu khác không liệt kê."`. Dòng cuối: `"Anh/chị xác nhận có muốn tách thành các phiếu riêng không? Bot không tự tách phiếu."`. Trần 10 áp **sau** khi bỏ yêu cầu rỗng. Ngược lại → `None`.

**Task bị đổi.** Task sửa nhỏ mới (tech-lead đặt số), sau T27, trước U4b; files `erp_ai/agent/classification.py`, `erp_ai/agent/test_classification.py`. U4b (`design-addendum-1-U4b-U8.md:245`) dùng hàm với chữ ký không đổi.

**Test** (`erp_ai/agent/test_classification.py`): `TestSplitComment::test_caps_at_ten` (sửa chuỗi mong đợi: 11 yêu cầu → "gồm 11 yêu cầu", 10 mục, dòng "… và 1 yêu cầu khác không liệt kê."; lý do sửa: thiết kế đổi, STD-TEST-5); `::test_cap_applies_after_dropping_empty` (mới: 10 yêu cầu thật + 3 rỗng → n = 10, không có dòng thêm); `::test_newline_inside_request_collapsed` (mới: `"x\n2. y"` → mục `"x 2. y"`).

### 5c — AC-25: Date so với datetime; `set_classification` không được hạ mức đã nâng

**(i) Date/datetime.** Hàm thuần mới trong `routing.py`: `as_deadline(value: date | datetime | None) -> datetime | None`. `None` hoặc rỗng → `None`; `datetime` → giữ nguyên (giờ hệ thống, naive); `date` không phải `datetime` → `datetime.combine(value, time(23, 59, 59))` ("hạn ngày X" = hết ngày X). `_priority` (T24) và `processing_deadline` (T26) gọi `as_deadline` trước mọi phép so. **Thay `design.md:385-386`** (hai dòng B, D) bằng:
> - B ∧ `as_deadline(due_at)` ∧ `as_deadline(due_at) − now ≤ 24 h` → ít nhất High (quá hạn cũng tính);
> - D ∧ `as_deadline(due_at)` → ít nhất High.

**Thay `design.md:391`** bằng: "`processing_deadline(category, resolution_by, due_at: date | datetime | None) -> datetime | None` (D-18): D, E có `due_at` → `as_deadline(due_at)`; ngược lại `resolution_by`."

**(ii) `set_classification`.** Mọi đường ghi `priority` qua `decide_route` phải truyền cùng đầu vào hạn. U4b thêm một hàm dùng chung trong `erp_ai/agent/tools/write_ticket.py`: `due_route_kwargs(ticket: dict, settings, now: datetime) -> dict` trả `{"due_at": <giá trị trường settings.field_due_date của phiếu (Frappe trả date cho Date, datetime cho Datetime), None khi chưa cấu hình>, "due_field_configured": <cùng điều kiện của :245>, "now": now}`. `runner._classify` và `set_classification` (`write_ticket.py:50`, qua `_mapped_values`) cùng gọi hàm này. `run_eval.py:198` giữ lời gọi cũ (`None`): eval đo model và mapping, không đo ngoại lệ hạn; ghi rõ trong As-Built.

**Addendum đợt 1 đã duyệt bị đổi chữ:** `design-addendum-1-U4b-U8.md:33` (thêm `write_ticket.py:50`: `set_classification` truyền `**due_route_kwargs(...)`); `:245` (vế (1) dùng `**write_ticket.due_route_kwargs(ticket, settings, now_datetime())` thay cho ba tham số viết tay). Không đổi tên hay kiểu đã có.

**Task bị đổi.** T24 (thêm `as_deadline`), T26 (Expect thêm ca date), U4b (đợt 1).

**Test.** `erp_ai/agent/test_routing.py::TestPriorityExceptions::test_date_due_is_end_of_day` (T24, mới): B với `due_at = date(2026, 11, 15)`; `now = 2026-11-14 23:59:59` → High (đúng 24 giờ, `<=`); `now = 2026-11-14 23:59:58` → không nâng; D với `date` → High; không có `TypeError`. `TestResponseOverdue::test_processing_deadline_d_with_and_without_due` (T26) thêm ca `date` → `datetime(…, 23, 59, 59)`. U4b: `erp_ai/agent/tools/test_write_ticket.py::TestDueException::test_set_classification_keeps_due_raised_priority` (D, mapping D Medium, phiếu có hạn → sau `set_classification` vẫn High).

### 5d — T44: cron chỉ bật khi ba module đích đã có

**Quyết định.** T44 (khai báo `cron` trong `hooks.py`) chỉ làm sau task **cuối** của mỗi module đích: `kpi.py` (T47), `monthly_review.py` (T50), `daily_report.py` (T54, không phải T53, để job theo lịch có sẵn phần "lỗi không ném ra khỏi job"). Trước đó, scheduler của site sẽ xếp job có đích chuỗi trỏ tới module chưa có, và worker lỗi import mỗi lần chạy. `queue.*_job` (T42, đã merge) không bị ảnh hưởng.

**Task bị đổi.** T44 `depends`: T40, T42, T47, T50, T54. Thứ tự chủ của `erp_ai/hooks.py` (`plan.md` bảng "Một file, một chủ") đổi từ T40 → T44 → T34 thành **T40 → T34 → T44**; T34 bỏ phụ thuộc T44 (giữ T33). Tech-lead sửa `tasks.md`, `plan.md`.

**Test** (T44, `erp_ai/tests/test_schedules.py`): `TestCron::test_job_targets_importable` (mới): với 3 chuỗi đích job theo lịch trong `ENQUEUE_TARGETS`, `frappe.get_attr(target)` trả hàm gọi được. Test này đỏ nếu T44 chạy trước module đích.

### 5e — NFR-7: `keep_agent_settings` phải trả lại dòng `__Auth`

**Quyết định.** Có. `api_key` của ERP AI Credential là Password: giá trị thật nằm ở `__Auth` (khóa `doctype, name, fieldname`), không nằm ở bảng con. Bản hiện có (`test_utils.py:102-136`) chỉ trả lại bảng con, nên test đổi khóa sẽ ghi đè khóa thật của site dùng chung, còn test thêm dòng sẽ để lại dòng `__Auth` mồ côi. Hai việc này trái NFR-7 ("số bản ghi cấu hình trước = sau").

**Thay dòng `design.md:558`** (ghi chú `erp_ai/test_utils.py`) bằng:
> thêm `keep_agent_settings(testcase)`: chụp `tabSingles` của Setting, dòng các bảng con, **và dòng `__Auth` có `doctype` ∈ {Setting} ∪ DocType các bảng con** (cột `doctype, name, fieldname, password, encrypted`), trả lại cả ba trong `addCleanup` (xóa dòng hiện có của các DocType đó rồi chèn bản chụp). Chép nguyên bản mã hóa, không giải mã (không `get_password`, không `get_decrypted_password`; STD-SEC-1). SQL có tham số; không commit (NFR-7).

**Task bị đổi.** Task sửa nhỏ mới (tech-lead đặt số), sau T1, trước task đầu tiên có test lưu khóa Credential; files `erp_ai/test_utils.py`, `erp_ai/tests/test_test_utils.py`.

**Test:** `erp_ai/tests/test_test_utils.py::TestKeepAgentSettings::test_restores_auth_rows_of_credentials` (mới): chụp các dòng `__Auth` của ERP AI Credential; trong một testcase con: đổi `api_key` của một dòng có sẵn (giá trị giả) và thêm một dòng mới; chạy `doCleanups()` → tập dòng `__Auth` (gồm cả bản mã hóa) bằng đúng bản chụp, số dòng bằng nhau.

---

## 6. Thay đổi đối với addendum đợt 1/2 đã duyệt

| Addendum : dòng | Đổi gì | Phán quyết | Đổi tên/kiểu? |
|---|---|---|---|
| `design-addendum-1-U1.md:61, :130, :262, :339, :459`; test plan `:423` + 1 dòng mới | luật đọc -1 → `None`; người ghi không ghi 0 thay cho không biết | 1 | Không (chữ ký `latest_classification -> tuple[str \| None, int \| None]` giữ nguyên; `None` vẫn là "không biết") |
| `design-addendum-1-U3.md:69` | luật `is_secret_key` theo đoạn tên | 5a | Không (tên, chữ ký giữ nguyên) |
| `design-addendum-1-U4b-U8.md:33, :245` | `due_route_kwargs` dùng chung cho runner và `set_classification` | 5c | Không; thêm một hàm mới của U4b |
| `design-addendum-2-U5b.md:48` | hành vi `category_by_ticket_type` khi trùng `ticket_type` đã xác định | 3 | Không |

**Hợp đồng của U1: không đổi.** Phán quyết 1 chỉ thêm luật đọc vào chữ.

## 7. Touchpoints thêm hoặc đổi

| file | change | task | ghi chú |
|---|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa | T3 | `default "-1"`, mô tả |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | T3 | cụm `"-1"`, `"không biết"` |
| `erp_ai/patches.txt` | sửa | T3 | 1 dòng `[post_model_sync]` |
| `erp_ai/patches/feat007_unknown_confidence_pct.py` | mới | T3 | patch 0 → -1 theo lô |
| `erp_ai/patches/test_feat007_unknown_confidence_pct.py` | mới | T3 | 3 test |
| `erp_ai/agent/routing.py`, `erp_ai/agent/test_routing.py` | sửa | T24, T26 | `None` mặc định, `as_deadline` |
| `erp_ai/agent/ops_data.py`, `erp_ai/agent/test_ops_data.py` | mới | T41 | luật thứ tự `CATEGORIES` |
| `erp_ai/eval/test_run_eval.py` | sửa (test) | T41 | test khớp luật |
| `erp_ai/install.py`, `erp_ai/tests/test_install.py` | sửa | T60 | bỏ qua spec ẩn |
| `erp_ai/agent/redact.py`, `erp_ai/agent/test_redact.py` | mới | T35 | luật đoạn tên, callback |
| `erp_ai/agent/classification.py`, `erp_ai/agent/test_classification.py` | sửa | task sửa nhỏ sau T27 | `{n}`, rỗng, khoảng trắng |
| `erp_ai/tests/test_schedules.py` | mới | T44 | test đích import được |
| `erp_ai/test_utils.py`, `erp_ai/tests/test_test_utils.py` | sửa | task sửa nhỏ sau T1 | `__Auth` |

So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:
```
erp_ai/patches/feat007_unknown_confidence_pct.py        -> erp_ai  OK
erp_ai/patches/test_feat007_unknown_confidence_pct.py   -> erp_ai  OK
docs/team/features/FEAT-007/design-w0-fixes-2.md        -> docs    OK
```
`protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`: không đường dẫn nào ở bảng trên có tên `.env*`, đuôi `.pem`/`.key` hay là `license.txt` → 0 trùng.

## 8. Đối chiếu tiêu chí → test

Tiêu chí mà file này chạm tới:
```
AC-22, AC-25, AC-26, AC-28, AC-51, AC-52, NFR-4, NFR-6, NFR-7, STD-OPS-2
```
Tiêu chí có ít nhất một dòng test ở file này:
```
AC-22 / NFR-4 : test_feat007_unknown_confidence_pct.py ×3 (T3); test_policy.py::TestConfidence ×2 (U1)
AC-25         : test_routing.py::TestPriorityExceptions::test_old_call_shape_no_due_note, ::test_missing_due_field_note, ::test_date_due_is_end_of_day; test_write_ticket.py::TestDueException::test_set_classification_keeps_due_raised_priority (U4b)
AC-26         : test_routing.py::TestResponseOverdue::test_processing_deadline_d_with_and_without_due (ca date)
AC-28         : test_classification.py::TestSplitComment::test_caps_at_ten, ::test_cap_applies_after_dropping_empty, ::test_newline_inside_request_collapsed
AC-51         : test_schedules.py::TestCron::test_job_targets_importable
AC-52         : test_ops_data.py::TestCategoryLookup::test_shared_ticket_type_earliest_category_wins; test_run_eval.py::TestCategoryRuleShared::test_expected_category_agrees_with_ops_data
NFR-6         : test_redact.py::TestRedact::test_is_secret_key_names, ::test_usage_counters_not_masked, ::test_nfd_vietnamese_key_masked, ::test_long_run_without_secret_untouched
NFR-7         : test_test_utils.py::TestKeepAgentSettings::test_restores_auth_rows_of_credentials
STD-OPS-2     : test_feat007_unknown_confidence_pct.py::TestUnknownConfidencePct::test_patch_turns_zero_into_minus_one_only + kiểm count = 0 dán vào acceptance.md
```
AC-1 (T60 thuộc cài đặt): `test_install.py::TestFeat007Migrate::test_hidden_labels_field_has_no_template_row`. Không tiêu chí nào của danh sách thiếu test. Không test nào bị bỏ; một chuỗi mong đợi được sửa (`test_caps_at_ten`), một test được sửa ca (`test_missing_due_field_note`).

## 9. Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-W0F2-1 | -1 là giá trị "không biết" của `predicted_confidence_pct` | Frappe không có số rỗng được; -1 nhỏ hơn mọi ngưỡng nên vẫn fail-closed | kiểu Data | đổi `default`, đổi luật đọc ở U1 |
| A-W0F2-2 | "Hạn ngày X" (trường Date) = 23:59:59 ngày X | ngày hạn thường được hiểu là còn làm được tới hết ngày | 00:00 ngày X | đổi một dòng trong `as_deadline` và ca biên test |
| A-W0F2-3 | Trùng `ticket_type` → đầu mục đứng trước theo A–F thắng; không chặn lúc lưu | khớp `run_eval` sẵn có; không làm hỏng site đang có trùng | chặn lúc lưu (cần analyst) | thêm kiểm vào `validate` của Setting, không vào `_mapping_error` |
| A-W0F2-4 | Quá 10 yêu cầu: `{n}` là tổng, có dòng "… và k yêu cầu khác" | người tạo phiếu thấy đúng số yêu cầu | `{n}` = số liệt kê | đổi chuỗi |

Câu hỏi nghiệp vụ: 0.

## 10. Bảng kết

| Điểm | Phán quyết | Task bị ảnh hưởng |
|---|---|---|
| (1) T3 pct Int luôn 0 | Int `default "-1"` = không biết; patch 0 → -1 một lần; U1 đọc ngoài 0..100 là `None` | T3 (làm lại, +3 file); U1 đợt 1 (chữ `:61, :130, :262, :339, :459`, 2 test); chặn tiếp theo T4, T5, T7, T28 như cũ |
| (2) T24 `:382` với `:387` | `due_field_configured: bool \| None = None`; ghi chú chỉ khi `is False` | T24 (làm lại); T25, T26, T51 theo sau |
| (3) T41 trùng `ticket_type` | đầu mục đứng trước theo `CATEGORIES` thắng, giống `run_eval`; test khớp đặt dưới `eval` | T41 (làm lại, + `erp_ai/eval/test_run_eval.py`); T45, T50, T51 nhận luật |
| (4) T60 dòng mẫu của trường ẩn | không có dòng mẫu; `_ensure_template_rows` bỏ qua spec `hidden` | T60 (chữ Returns, Receives, +1 test) |
| (5a) `*_tokens` bị che | `is_secret_key` theo đoạn tên, NFC, camelCase; callback tuyến tính | T35 vòng 3; U3 (chữ `:69`) |
| (5b) `{n}` > 10, yêu cầu rỗng | `{n}` = tổng, dòng "… và k yêu cầu khác"; rỗng bỏ, không tính; gộp khoảng trắng | task sửa nhỏ sau T27 (tech-lead đặt số) |
| (5c) Date/datetime, `set_classification` | `as_deadline` (date → 23:59:59); `due_route_kwargs` dùng chung cho runner và `set_classification` | T24, T26; U4b đợt 1 (chữ `:33, :245`, 1 test) |
| (5d) cron T44 trước module đích | T44 depends thêm T47, T50, T54; thứ tự `hooks.py` T40 → T34 → T44 | T44, T34 (bỏ phụ thuộc T44) |
| (5e) `__Auth` của `api_key` | `keep_agent_settings` chụp và trả lại `__Auth` của Setting và các bảng con, không giải mã | task sửa nhỏ sau T1 (tech-lead đặt số) |
