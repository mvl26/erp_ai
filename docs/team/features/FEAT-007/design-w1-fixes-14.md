# FEAT-007 — design-w1-fixes-14: phán ba điểm chuyển designer của lượt 15 (T72, T172, T43)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `tasks.md:199` (mục 1–3 của dòng "Chuyển designer"); `review-72.md:28,46,51`; `review-172.md:29,58`; `review-43.md:39,45,52`; `design-w1-fixes-8.md` Điểm 1 (`policy.latest_classification`, `SEEDED_CLASSIFICATION`); `tasks-amend-w1.md:130-176` (khối T80, T81); `design-addendum-1-U1.md:249-253` (mục 3.6); `design-w0-fixes-2.md:20-42` (mục 1, -1 = không biết); `design.md:68` (D-10), `:254-270` (`ERP AI KPI Week`), `:470` (`run_weekly_kpi`).
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` — `erp_ai/agent/classification.py:13-15,35-48,79-111`; `erp_ai/agent/policy.py:128-168` (`_known_pct`, `is_below_confidence`, `latest_classification`); `erp_ai/agent/prompts.py:68,82`; `erp_ai/agent/tools/write_ticket.py:43-49`; `erp_ai/agent/test_classification.py:137-183`; `erp_ai/agent/knowledge.py:100-122`; `erp_ai/agent/tools/source.py:14-24` (`_logger`); `erp_ai/agent/test_knowledge.py:346,361,525-580`; `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/erp_ai_kpi_week.json`; `erp_ai/agent/kpi.py:1-5,47-65`; `erp_ai/tests/test_doctype_descriptions.py:10-16,462-490,526-532,566-620`; `pyproject.toml:34-58`.
- Không đổi kiến trúc: theo ADR-030 QĐ 4 (không biết = dưới ngưỡng, trừ khi có người ra lệnh VÀ `act_now`), ADR-033 (khóa chu kỳ; D-10 bù tối đa 8 tuần), ADR-034 QĐ 4 (tìm HDSD). Không đổi quy tắc nghiệp vụ. Không có `DESIGN_CONFLICT`.
- Số task mới: T176, T177, T178 (`grep -rhoE '\bT1(7[6-9]|8[0-9]|9[0-9])\b' docs/team/features/FEAT-007/` ra 0 dòng trước file này; số lớn nhất trong `tasks.md` là T175).

---

## Điểm 1 — T72: mặc định của `Classification.confidence_pct`

### Hiện trạng (dữ kiện)
- `classification.py:48`: `confidence_pct: int = 0`. Thiết kế `U1.md:251` chỉ ghi `confidence_pct: int`, không ghi mặc định.
- `parse_classification` (`classification.py:90-92`) chỉ trả `Classification` khi `do_tin_cay_pct` là `int` 0..100, không phải `bool`; mọi đường qua parse (`runner.py:290`, `run_eval.py:195`) luôn mang số thật.
- Nơi dựng `Classification(...)` trực tiếp, không truyền `confidence_pct`: `tools/write_ticket.py:44-49` (`_mapped_values`, tool `set_classification`), `test_routing.py` (8 chỗ), `tools/test_route_ticket.py:101`, `tools/test_write_ticket.py:580` (`review-72.md:28`). Hôm nay chưa mã nào đọc `Classification.confidence_pct` (`git grep '\.confidence_pct'` ngoài file test: 0 dòng).
- `policy._known_pct(0)` trả 0 ("biết, 0%"); `is_below_confidence(0, 0, …)` là `False` (`0 < 0` sai) → một `Classification` dựng trực tiếp với mặc định 0 bị coi là "đủ ngưỡng 0" (fail-open, trái NFR-4). `design-w0-fixes-2.md:24,27` đã chốt: "không biết" là -1/`None`, "không bao giờ ghi 0 thay cho 'không biết'"; `U1.md:262` (theo `w0-fixes-2.md:41`) đã viết "`classification.confidence_pct` là `None` hoặc ngoài 0..100 → không truyền `predicted_confidence_pct`", tức thiết kế đã chờ `None`.
- `depends:` hiện có: T80 `— depends: T75, T77, T72, T69`, T81 `— depends: T80` (`tasks.md`, `tasks-amend-w1.md`); T77 đã tick. T80 không có tổ tiên T79. `files:` của T80, T81 không có `classification.py` hay `test_classification.py`.

### Phán quyết
1. **`confidence_pct: int | None = None`** ("không biết"). Không chọn `0` (đọc là "biết, 0%", trái `w0-fixes-2.md` mục 1). Không chọn "không mặc định" (buộc sửa 11 nơi dựng trực tiếp ngoài touchpoint, trong đó `write_ticket.py` của chuỗi T98 và `test_routing.py`, mà không thêm gì cho hành vi: tool `set_classification` không có số phần trăm để truyền).
2. `parse_classification` không đổi (vẫn luôn trả `int` 0..100). `write_ticket.py` **không đổi** (mặc định `None` đúng nghĩa cho `set_classification`; T98 "không ghi độ tin cậy" giữ nguyên chữ). Các test dựng trực tiếp không đổi.
3. **Task:** T176 mới (khối dưới). Chuỗi chủ `test_classification.py` thành T72 → **T176** → T79 → T82 (T126 trôi, không cùng lượt). T176 sẵn sàng ngay (T72 đã tick); `classification.py` không còn task mở nào khác sau T72.
4. **T80, T81: không task nào phải chờ T176.** Không chung file (mục Hiện trạng), không đổi chữ khối nào, không thêm `depends:`. Lý do đủ an toàn: T81 ghi `predicted_confidence_pct` từ kết quả `parse_classification` (luôn số thật); `None` nếu có cũng hợp lệ theo `w0-fixes-2.md:27` ("truyền `None` → Frappe điền -1"). Chỉ T79 thêm `depends: T176` (chuỗi chủ file). Tech-lead nên chạy T176 ở lượt 16 song song T74/T78 (T78 không sửa `test_classification.py`, `design-w1-fixes-7.md:21`), để T79 không phải đợi.
5. **Gạch nối `0-100` trong prompt (RUF001):** chấp nhận gạch nối thường U+002D ở `prompts.py:68` (`"do_tin_cay_pct": <số nguyên 0-100>,`). Căn cứ: `pyproject.toml:35-43` chọn `"RUF"`, danh sách `ignore` (`:44-58`) không có `RUF001`, không có `allowed-confusables`; RUF001 bắt EN DASH U+2013 trong chuỗi; `git grep -P '\x{2013}' team/FEAT-007 -- 'erp_ai/*.py'` ra 0 dòng (không file `.py` nào của app có ký tự này). Nghĩa với model không đổi. Văn bản thiết kế sửa cho khớp (dưới).

### Dòng thay trong tài liệu thiết kế (chép nguyên văn)

`design-addendum-1-U1.md:250` — thay đoạn `` `"do_tin_cay_pct": <số nguyên 0–100>` `` bằng `` `"do_tin_cay_pct": <số nguyên 0-100>` (gạch nối thường U+002D trong chuỗi Python: RUF001, design-w1-fixes-14.md Điểm 1) `` (phần còn lại của dòng giữ nguyên).

`design-addendum-1-U1.md:251` — thay đoạn `` `Classification` thêm trường `confidence_pct: int`. `` bằng `` `Classification` thêm trường `confidence_pct: int | None = None` (None = không biết, cho nơi dựng trực tiếp như `set_classification`; design-w1-fixes-14.md Điểm 1). `` (phần còn lại của dòng giữ nguyên).

### Dòng thay trong `tasks.md` (chép nguyên văn)

Khối mới, chèn ngay sau khối T72:

```
- [ ] T176 — `Classification.confidence_pct` mặc định `None` (không biết) — files: erp_ai/agent/classification.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_classification.py — depends: T72
  - Tiêu chí: AC-22, NFR-4; `design-w1-fixes-14.md` Điểm 1; `design-w0-fixes-2.md` mục 1 (không dùng 0 cho "không biết"); ADR-030 QĐ 4. Chuỗi chủ `test_classification.py`: T72 → T176 → T79 → T82 (T126 không cùng lượt).
  - Receives: `Classification`, `parse_classification`, `CONFIDENCE_PCT_MIN` (T72); `policy.is_below_confidence` (T69).
  - Returns: `classification.py:48` thành `confidence_pct: int | None = None` với chú thích một dòng ngay trên: `# None = unknown (direct builders such as set_classification); never 0 for unknown (design-w0-fixes-2.md section 1).`; không đổi `parse_classification`; không đổi `erp_ai/agent/tools/write_ticket.py` và mọi nơi dựng `Classification(...)` trực tiếp.
  - Expect: `TestConfidencePct::test_direct_build_is_unknown_and_below_any_threshold` mới: `result = classification.Classification(category="A", confidence="Cao")` → `self.assertIsNone(result.confidence_pct)`; `self.assertTrue(policy.is_below_confidence(result.confidence_pct, classification.CONFIDENCE_PCT_MIN, has_instructor=False, act_now=False))`. Đỏ trước trên mã T72: `AssertionError: 0 is not None`. `::test_parse_accepts_0_to_100`, `::test_parse_rejects_missing_bool_negative_over_100_float` xanh không sửa. `cmd.test_one` xanh cả file: `erp_ai/agent/test_classification.py`, `erp_ai/agent/test_routing.py`, `erp_ai/agent/tools/test_route_ticket.py`, `erp_ai/agent/tools/test_write_ticket.py`.
```

T79 (`tasks.md:754` và khối `tasks-amend-w1.md:123`) — chỉ thay đuôi dòng tiêu đề `— depends: T78` bằng `— depends: T78, T176`; phần còn lại giữ nguyên.

T80, T81 (`tasks-amend-w1.md:130-176`): không đổi chữ.

---

## Điểm 2 — T172: `frappe.logger(...)` trong khối `except OSError` của `search_manuals`

### Hiện trạng (dữ kiện)
- `knowledge.py:115-120` (đánh số theo file): trong `except OSError as error:` gọi `frappe.logger(source.LOGGER_NAME).warning("search_manuals skipped %s: %s", document, type(error).__name__)` rồi `continue`. `frappe.logger` mở file log của site; nếu nó ném (file log không mở được, `PermissionError`/`OSError`), lỗi mới thoát khỏi khối `except` và cả lần tìm hỏng, đúng điều `design-w1b-fixes-1.md` điểm 2 (T172) định chặn.
- `source._logger()` (`source.py:17-24`) đã có đúng lối dự phòng: `frappe.logger(LOGGER_NAME)`, ném bất kỳ `Exception` → `logging.getLogger(LOGGER_NAME)`; chú thích ở đó nói rõ lý do (nơi gọi log từ trong xử lý lỗi của chính nó). `source.py` dùng nó 9 lần. Tiền lệ gọi hàm có gạch dưới qua module khác: `source.py:10` (`from erp_ai.agent.tools.read import _schema`). `knowledge.py:17` đã `from erp_ai.agent.tools import source`.
- Test có sẵn `TestManuals::test_unreadable_file_skipped_and_logged` (`test_knowledge.py:525`) vá `knowledge.frappe.logger` (chính `frappe.logger`) và khẳng định `get_logger.assert_called_with(knowledge.source.LOGGER_NAME)` cùng các dòng `warning`. `source._logger()` gọi đúng `frappe.logger(LOGGER_NAME)` qua thuộc tính module `frappe`, nên test này vẫn xanh không sửa sau khi đổi.
- Không task mở nào có `erp_ai/agent/knowledge.py` hay `erp_ai/agent/test_knowledge.py` trong `files:` (T37, T39, T120, T123, T172 đã tick). T126 có `erp_ai/agent/tools/source.py`, nhưng T177 không sửa `source.py`.

### Phán quyết
1. **Có task nối: T177.** `knowledge.py` gọi `source._logger().warning(...)` thay cho `frappe.logger(source.LOGGER_NAME).warning(...)`; chữ dòng log và tham số giữ nguyên. Không chép lại khối `try/except` vào `knowledge.py` (STD-DESIGN-4: một lối dự phòng duy nhất) và không đổi tên `_logger` thành công khai (sẽ đòi `source.py`, file của T126).
2. Không chặn T80/T81 hay task nào khác; T177 sẵn sàng ngay (`depends: T172`, đã tick). Không chung file với task mở nào.

### Dòng thay trong `tasks.md` (chép nguyên văn)

Khối mới, chèn ngay sau khối T172:

```
- [ ] T177 — `search_manuals`: log file bỏ qua qua `source._logger()`, log hỏng không làm hỏng lần tìm — files: erp_ai/agent/knowledge.py, erp_ai/agent/test_knowledge.py — test: erp_ai/agent/test_knowledge.py — depends: T172
  - Tiêu chí: AC-47; `design-w1b-fixes-1.md` điểm 2 (một file lỗi không làm hỏng cả lần tìm); `design-w1-fixes-14.md` Điểm 2; STD-ERR-1. Không sửa `erp_ai/agent/tools/source.py`.
  - Receives: `source._logger()` (`source.py:17-24`), `source.LOGGER_NAME` (có sẵn).
  - Returns: trong khối `except OSError as error:` của `search_manuals`, `frappe.logger(source.LOGGER_NAME).warning(` thành `source._logger().warning(`; chuỗi `"search_manuals skipped %s: %s"`, `document`, `type(error).__name__` và chú thích dòng trên giữ nguyên.
  - Expect: `TestManuals::test_unreadable_file_logged_even_when_log_file_fails` mới: `sub/a.md` và `b.md` cùng một từ; `patch.object(knowledge, "open", …)` ném `PermissionError(errno.EACCES, …)` cho `a.md`; `patch.object(knowledge.frappe, "logger", side_effect=PermissionError(errno.EACCES, "log"))`; trong `self.assertLogs(knowledge.source.LOGGER_NAME, "WARNING") as logs` → `self._found(word) == [("b.md", 1)]` và `[r.getMessage() for r in logs.records] == ["search_manuals skipped sub/a.md: PermissionError"]`. Đỏ trước trên mã T172: `PermissionError: [Errno 13] log`. `TestManuals::test_unreadable_file_skipped_and_logged` xanh không sửa; `cmd.test_one` xanh cả file `erp_ai/agent/test_knowledge.py`.
```

---

## Điểm 3 — T43 (đã merge): chữ mô tả `ERP AI KPI Week` và `read_only`

### Hiện trạng (dữ kiện)
- (a) `erp_ai_kpi_week.json:34` (`week_start`): "… Job KPI tuần ghi dòng lúc 08:00 thứ Hai cho tuần trước." D-10 (`design.md:68`) và `design.md:470`: tuần cần tính = các tuần từ `max(tuần sau dòng mới nhất, W − 7 tuần)` tới `W` (tuần trước) chưa có dòng → tối đa 8 tuần mỗi lần chạy, gồm cả `W`. Job `run_weekly_kpi` chưa có trên `team/FEAT-007` (T47, `depends: T43, T46`, Tiêu chí "D-10 (bù tối đa 8 tuần)").
- (b) `erp_ai_kpi_week.json:61` (`first_response_median_min`): "… trên các phiếu tạo trong tuần đã có phản hồi. Rỗng khi mẫu 0." `kpi.py:61`: `median(minutes) if minutes else None`, `minutes` chỉ gồm phiếu có `first_responded_on`; `first_response_sample` (`:59`) đếm mọi phiếu tạo trong tuần. Mã đúng với chính câu đầu của mô tả và `kpi.py:4` ("KPI có mẫu 0 là `None`") cho các tỷ lệ; chỉ câu cuối của trung vị sai: có phiếu mà chưa phiếu nào được phản hồi thì mẫu > 0 nhưng trung vị vẫn rỗng. Gốc chữ: `design.md:261` ("rỗng khi mẫu 0"). Cụm bắt buộc hiện tại: `test_doctype_descriptions.py:469` `("KPI 1", "trung vị", "phút", "Rỗng khi mẫu 0")`.
- (c) DocPerm (`erp_ai_kpi_week.json:151-162`, `design.md:270`): System Manager và ERP AI Instructor chỉ `read`, `report`; không ai `create/write/delete`; job chạy phiên scheduler (Administrator). M5 (`refuse_agent_write`, T58) chặn tài khoản agent. `test_doctype_descriptions.py:485` ghim `"read_only_fields": ()`; luật `test_read_only_fields_say_system_writes` (`:610-620`) đòi mỗi trường `read_only` có "Hệ thống tự ghi" và "không sửa được".
- Task mở có `erp_ai/tests/test_doctype_descriptions.py` trong `files:`: T49 (`depends: T43`), T85 → T140 (`plan-w1.md:126`, `plan-w1b.md:116`). Không task mở nào có `erp_ai_kpi_week.json`.

### Phán quyết
1. **(a) Sửa chữ:** mô tả `week_start` nêu phần bù của D-10; thêm cụm bắt buộc `"tối đa 8 tuần"`.
2. **(b) Sửa chữ, không sửa mã:** `kpi.py:61` đúng; câu cuối mô tả trung vị đổi thành "Rỗng khi không phiếu nào tạo trong tuần có phản hồi, kể cả khi mẫu 0."; cụm bắt buộc `"Rỗng khi mẫu 0"` của trường này đổi thành `"Rỗng khi không phiếu nào"`, và thêm cụm cấm `"Rỗng khi mẫu 0"` cho trường này (ghim bằng `test_forbidden_phrases_absent` có sẵn). Ba trường tỷ lệ/trung bình khác giữ "Rỗng khi mẫu 0" (đúng: `_pct` theo mẫu).
3. **(c) Không đặt `read_only`.** Không vai nào có quyền ghi (DocPerm), agent bị M5 chặn, job ghi bằng `insert` phía server (không bị `read_only` cản) → `read_only` không đổi điều gì job hay người dùng làm được, chỉ thêm 17 câu "Hệ thống tự ghi … không sửa được"; spec và thiết kế không đòi (chỉ thêm điều spec cần). `"read_only_fields": ()` giữ nguyên.
4. **Task: T178** (khối dưới), `[migrate]` vì đổi JSON DocType. `depends: T49, T140` để xếp sau mọi task mở trên `test_doctype_descriptions.py` mà không đổi `depends:` của task nào khác. Không chặn ai; phải xong trước `/team:verify`.
5. Độ dài, đo bằng lệnh `python3 -c` (`len`, `unicodedata.is_normalized("NFC", …)`, có chứa `"rỗng khi mẫu 0"` không), đầu ra: chuỗi `week_start` `247 True False`; chuỗi `first_response_median_min` `173 True False`. Cả hai ≤ 400 (`MAX_DESCRIPTION_CHARS`), NFC.

### Dòng thay trong tài liệu thiết kế (chép nguyên văn)

`design.md:261` — thay cả dòng bằng:
```
| `first_response_median_min` | Float | rỗng khi không phiếu nào tạo trong tuần có phản hồi, kể cả mẫu 0 (`kpi.py:61`; design-w1-fixes-14.md Điểm 3) |
```

### Dòng thay trong `tasks.md` (chép nguyên văn)

Khối mới, chèn ngay sau khối T43:

```
- [ ] T178 — Mô tả `ERP AI KPI Week`: job bù tối đa 8 tuần, trung vị rỗng khi chưa phiếu nào được phản hồi [migrate] — files: erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/erp_ai_kpi_week.json, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/tests/test_doctype_descriptions.py — depends: T49, T140
  - Tiêu chí: AC-55, D-10 (`design.md:68`, `:470`), STD-DOC-2; `design-w1-fixes-14.md` Điểm 3. Chỉ đổi hai giá trị `"description"` và `"modified"`; không đổi `read_only`, `reqd`, `unique`, DocPerm, `kpi.py`.
  - Receives: DocType `ERP AI KPI Week` (T43); `DOCTYPE_CONFIG`, `FORBIDDEN_PHRASES` (có sẵn).
  - Returns: `erp_ai_kpi_week.json`: `week_start` `"description"` ĐÚNG chuỗi (247 ký tự) `Thứ Hai 00:00 của tuần ISO được tính. Khóa chu kỳ: mỗi tuần một dòng, tên dòng là KPI-<ngày này>. Job KPI tuần chạy lúc 08:00 thứ Hai, ghi dòng cho tuần trước và bù các tuần liền trước còn thiếu dòng, tối đa 8 tuần mỗi lần chạy (kể cả tuần trước).`; `first_response_median_min` `"description"` ĐÚNG chuỗi (173 ký tự) `KPI 1. Trung vị số phút từ lúc tạo tới phản hồi đầu tiên, trên các phiếu tạo trong tuần đã có phản hồi. Rỗng khi không phiếu nào tạo trong tuần có phản hồi, kể cả khi mẫu 0.`; `"modified"` từ `"2026-11-15 10:00:00.000000"` lên `"2026-11-15 12:00:00.000000"`. `test_doctype_descriptions.py`: `DOCTYPE_CONFIG["ERP AI KPI Week"]["phrases"]` — `"week_start": ("thứ Hai", "mỗi tuần một dòng", "KPI-", "tối đa 8 tuần")`, `"first_response_median_min": ("KPI 1", "trung vị", "phút", "Rỗng khi không phiếu nào")`; `FORBIDDEN_PHRASES` thêm `"ERP AI KPI Week": {"first_response_median_min": ("Rỗng khi mẫu 0",)}` với chú thích `# FEAT-007 design-w1-fixes-14.md Điểm 3: the median is empty when no ticket of the week has a response (kpi.py:61), not only when the sample is 0.`
  - Expect: test sửa trước, đỏ trên JSON của T43: `TestDoctypeDescriptions::test_required_phrases_present` (`thiếu cụm`: `week_start` thiếu `tối đa 8 tuần`, `first_response_median_min` thiếu `Rỗng khi không phiếu nào`), `::test_forbidden_phrases_absent` (`còn cụm sai`); sau JSON → xanh, cùng `::test_descriptions_at_most_400_chars`, `::test_read_only_fields_say_system_writes`, `::test_every_visible_field_has_description` (vẫn 17 trường). `cmd.migrate` trước `cmd.test_one`; `cmd.test_one` xanh cả file `erp_ai/tests/test_doctype_descriptions.py` và `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/test_erp_ai_kpi_week.py` (không sửa).
```

---

## Không thuộc phán quyết này
- Mục (4) `review-51.md` và (5) `preflight-w1.md` F-7 của `tasks.md:199`: ngoài lời giao (F-7 đã phán ở `design-w1-fixes-8.md` Điểm 3).
- `prompt_override_classify` đã lưu thiếu `"do_tin_cay_pct"` (`review-72.md:51`) và `docs/HuongDan_TrienKhai_erp-ai.md:1393-1401`: của team-leader / `/team:asbuilt`, như `tasks.md:199` đã ghi.
- Tên lớp test `TestDoctypeDescriptions` trong Expect của T178 là tên lớp chứa các test `:566-620`; nếu tên lớp khác, dev dùng tên thật, giữ tên hàm test.
