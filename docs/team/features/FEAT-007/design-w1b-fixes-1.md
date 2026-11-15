# FEAT-007 — design-w1b-fixes-1: phán hai điểm mở của kế hoạch đợt 1b (R-3, R-7)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `plan-w1b.md:210`, `:213`, `:214`, `:245-246`; `tasks-w1b.md` khối T137 (`:93-97`) và T148 (`:151-155`); `arch-ruling-r5.md:49-53`; `spec.md:144` (NFR-1), `:167` (AC-9), `:217` (AC-47), `:269` (A-21); ADR-037 QĐ 1–3; `design-addendum-1-U2.md:164-174`, `:297-298`; `design-addendum-1-U6b.md:56`, `:176`; `review-39.md:34`, `:52`, `:95`, `:100`; `tasks-w1.md:299`, `:331-334` (T106, T113).
- Mã đọc (chỉ đọc): `.claude/worktrees/feat-007` @ `7821d40` — `erp_ai/agent/runner.py:138-162` (`_run`, chốt (c) `policy.can_send_ticket` đọc lại mỗi lần chạy, trước mọi lời gọi model); `erp_ai/agent/knowledge.py:80-145` (`search_manuals`, `_manual_files`, `_sections`); `erp_ai/agent/test_knowledge.py:404-424` (symlink ngoài kho và symlink treo bị bỏ qua, không lỗi); `erp_ai/agent/tools/source.py:14` (`LOGGER_NAME = "erp_ai.source"`).
- Không đổi kiến trúc: theo ADR-034 QĐ 1, 2, 4; ADR-037 QĐ 1–3; ADR-033 QĐ 2; ADR-019 QĐ 1, 7.

---

## Điểm 1 — R-3: bảo vệ dữ liệu của U2 trên đường phân loại lại (NFR-1)

### Hiện trạng (dữ kiện)
- ADR-037 QĐ 2: lần phân loại lại gọi đúng một lần model qua cùng hàm dựng request, đầu vào thêm các tin đến sau dòng `classify` gần nhất. T106 chốt dạng: `later_messages`, tối đa `LATER_MESSAGES_MAX = 5` tin mới nhất, mỗi tin cắt `FIELD_VALUE_MAX_CHARS = 200` (`tasks-w1.md:299`).
- ADR-037 QĐ 1: phân loại lại chỉ khi trigger khác `ticket_insert`, mức khác L0, phiếu có dòng `classify` có kết quả, dòng gần nhất dưới ngưỡng.
- `runner._run` chốt (c) gọi `policy.can_send_ticket` trên dữ liệu đọc lại **trước** mọi lời gọi model (`runner.py:155-158`); T128 đổi thành `policy.send_refusal`, có `REFUSAL_EXCLUDED_TEAM`, `REFUSAL_EXCLUDED_TITLE`, `REFUSAL_OPTED_OUT`, `REFUSAL_EXCLUDED_BY_CLASSIFICATION`.
- R5-1: mọi kết quả phân loại (cả lần phân loại lại) đi qua đúng một `parse_classification(` trong `_classify`; ô U2 nằm ngay sau parse (R5-2). Vậy chốt loại trừ của T137 phủ luôn kết quả của lần phân loại lại, không cần mã riêng.
- NFR-1 đếm "lời gọi model **sau khi biết nhóm**" = 0. AC-9 nhận rủi ro còn lại cho "lời gọi phân loại đầu tiên" (A-21: tiêu đề + nội dung cắt 6000 ký tự).

### Phán quyết
1. **Không cắt comment khỏi payload phân loại lại.** Câu "payload không chứa comment" của AC-9 (b) chỉ áp cho lần phân loại khi tạo phiếu (test `test_classified_into_excluded_team_stops_before_reasoning` giữ nguyên). Cắt `later_messages` ở đường phân loại lại là trái ADR-037 QĐ 2 (tin đến sau là đầu vào của lần này) → không làm.
2. **Luật U2-R1 (bất biến, thiết kế):** lần phân loại lại không bao giờ bắt đầu trên phiếu đã biết là loại trừ. Lời gọi model của lần phân loại lại chỉ xảy ra sau chốt (c) của `_run` trên dữ liệu đọc lại trong cùng lần chạy; chốt đó từ chối khi: nhóm của phiếu đang là nhóm loại trừ (người vừa đặt), tiêu đề vừa thêm tiền tố loại trừ, cờ không dùng AI bật, hoặc dòng `classify` gần nhất có `stop_reason = excluded_by_classification` (kể cả khi dòng đó cũng dưới ngưỡng: loại trừ thắng dưới ngưỡng, R5-6). Không thêm chốt thứ hai; `handlers.py` không đọc `classify` (ADR-033 QĐ 2). Đây là vế "sau khi biết nhóm: 0 lời gọi" của NFR-1 trên đường này.
3. **Luật U2-R2 (thiết kế):** kết quả lần phân loại lại đi qua ô U2 như lần tạo phiếu (R5-1, R5-2). Ra bộ phận/nhóm loại trừ → dòng `classify` mới (cùng `run_id`, ADR-037 QĐ 2) `applied=0`, `stop_reason=excluded_by_classification`; không `_route`, không comment hướng, không thông báo, không Task, không `_reason`. Từ đó `send_refusal` trả `REFUSAL_EXCLUDED_BY_CLASSIFICATION`; `@ai` và quét bù bỏ qua (`design-addendum-1-U2.md:172`).
4. **Luật U2-R3 (thiết kế, giới hạn phơi lộ):** payload lần phân loại lại chỉ thêm phần `later_messages` đúng trần của T106 (≤ 5 tin, mỗi tin ≤ 200 ký tự, chỉ tin sau dòng `classify` gần nhất). Không thêm comment/tin trước dòng đó, không tệp đính kèm, không trường phiếu ngoài những gì lần tạo phiếu đã gửi. Test khẳng định bằng chuỗi gieo.
5. **Phiếu chưa có nhóm:** đúng là ca của U2-R1..R3. Phiếu đã có nhóm thường (người đặt) ngoài phạm vi NFR-1; có nhóm loại trừ thì chốt (c) chặn.

### Có cần câu spec không
- **NFR-1: không.** U2-R1 + U2-R2 giữ đúng câu NFR-1 trên đường phân loại lại; một luật thiết kế là đủ.
- **Rủi ro còn lại: có, cần một câu spec — giao analyst (`/team:analyze --amend FEAT-007`).** Lần phân loại lại của phiếu chưa có nhóm gửi cho model thêm tối đa 5 × 200 ký tự tin đến sau **trước** khi biết phiếu thuộc bộ phận loại trừ. Câu nhận rủi ro của AC-9 và A-21 chỉ nêu "lời gọi phân loại đầu tiên" với tiêu đề + nội dung; mở rộng rủi ro đã nhận là quyết định nghiệp vụ, designer không tự quyết. Câu đề nghị (thêm vào cuối AC-9 và cột của A-21): "Lần phân loại lại theo ADR-037 của phiếu chưa có nhóm, khi lần phân loại trước chưa chỉ ra bộ phận loại trừ, cũng là rủi ro còn lại đã chấp nhận: gửi thêm tối đa 5 tin đến sau, mỗi tin cắt 200 ký tự."
- Không chặn T137 (hành vi là luật ADR-037 đã có). Chặn nghiệm thu AC-9/NFR-1 của qa tới khi câu đó được người duyệt. Người **không** nhận rủi ro này → `DESIGN_CONFLICT` với ADR-037 QĐ 2 (team-leader → architect: phân loại lại không kèm tin đến sau cho phiếu chưa có nhóm, hoặc không phân loại lại phiếu chưa có nhóm).

### Căn cứ
- NFR-1 (`spec.md:144`); AC-9 (b) và câu rủi ro còn lại (`spec.md:167`); A-21 (`spec.md:269`).
- ADR-037 QĐ 1 (điều kiện), QĐ 2 (một lời gọi, tin đến sau, có trần, dòng `classify` mới); ADR-034 QĐ 1; ADR-033 QĐ 2.
- `arch-ruling-r5.md:51` (R5-6), `:53` (để ngỏ cho designer); R5-1, R5-2.

### Touchpoints (giữ như T137, chỉ thêm test)
| Đường dẫn | Sửa | Ghi chú |
|---|---|---|
| `erp_ai/agent/runner.py` | không thêm chỗ sửa ngoài ô U2 và `is_excluded_team=` (đã có trong T137) | U2-R1 có sẵn nhờ chốt (c) + `send_refusal` (T128); U2-R2 có sẵn nhờ R5-1 |
| `erp_ai/agent/test_agent_runner.py` | thêm 2 test, mở rộng 1 test | file đã có |

Không đường mới; không chạm `protected_paths`.

### Test (đỏ trước)
| Tiêu chí | `file::tên` | Ca / khẳng định |
|---|---|---|
| NFR-1, AC-9 (b), ADR-037 QĐ 2, U2-R2, U2-R3 | `erp_ai/agent/test_agent_runner.py::TestExcludedByClassification::test_reclassified_into_excluded_team_stops` | phiếu chưa nhóm; lần 1 stub trả bộ phận thường, dưới ngưỡng; 1 comment có chuỗi gieo A tạo **trước** dòng `classify` đầu; 7 tin đến sau (comment + trả lời người tạo) có chuỗi gieo B, một tin dài 500 ký tự; lần chạy `requester_reply` → stub trả bộ phận ánh xạ nhóm loại trừ. Khẳng định: tổng lời gọi model = 2; payload lời gọi 2 có đúng 5 tin mới nhất, mỗi tin ≤ 200 ký tự, chuỗi gieo A xuất hiện 0 lần; dòng `classify` mới cùng `run_id`, `applied=0`, `stop_reason=excluded_by_classification`; `count_guidance` = 0; 0 comment mới, 0 Task, 0 thông báo, `modified` không đổi; 0 dòng `reason`; rồi `@ai` và `run_for_ticket(comment_mention)` → tổng vẫn 2. Đỏ trước vì chưa có ô U2 |
| NFR-1, U2-R1 | `erp_ai/agent/test_agent_runner.py::TestExcludedByClassification::test_excluded_low_confidence_row_not_reclassified` | lần 1 stub trả bộ phận loại trừ, dưới ngưỡng (đủ điều kiện 3, 4 của ADR-037 QĐ 1); người tạo trả lời, rồi `@ai` → tổng lời gọi model = 1; có dòng `skip`. Đỏ trước vì chưa ghi `stop_reason` loại trừ (lần 2 phân loại lại) |
| NFR-1, U2-R1 | `erp_ai/agent/test_agent_runner.py::TestExcludedByClassification::test_group_set_excluded_before_reply_not_reclassified` | lần 1 dưới ngưỡng, bộ phận thường; người đặt `agent_group` = nhóm loại trừ; người tạo trả lời → tổng lời gọi model = 1, có dòng `skip`. Test ghim (chốt (c) đã có): xanh ngay là đúng, ghi lý do trong progress |

### Khối task thay thế trong `tasks-w1b.md` — T137
Dòng tiêu đề, `files:`, `depends:` giữ. Cuối dòng "Tiêu chí" thêm: `; design-w1b-fixes-1.md điểm 1 (U2-R1..R3)`. Ba dòng dưới thay nguyên văn ba dòng tương ứng:

```
  - Receives: `_classify` sau U4b: parse → [ô U2 trống] → chốt dưới ngưỡng → chọn chế độ → khóa định tuyến → `_route` (T108, T113, T115); lần phân loại lại của T113 gọi lại `_classify` với `later_messages` (T106: ≤ `LATER_MESSAGES_MAX` tin, mỗi tin ≤ `FIELD_VALUE_MAX_CHARS`); chốt (c) của `_run` dùng `policy.send_refusal` (T128); `policy.EXCLUDED_BY_CLASSIFICATION`, `policy.is_excluded_team`; `write_ticket.count_guidance` (T102).
  - Returns: hàm dò cục bộ `excluded_probe(team)` = `policy.is_excluded_team(team)` có ghi lại lần trả `True`, truyền qua `is_excluded_team=`; `excluded = probe_hit or policy.is_excluded_team(classification.department)`; `excluded` đúng → dòng `classify` với `applied=0`, `stop_reason=policy.EXCLUDED_BY_CLASSIFICATION`, các cột dự đoán giữ; không `_route`, không comment, không thông báo; mức L0 cũng ghi `stop_reason` này. Cùng ô đó phủ kết quả lần phân loại lại (U2-R2); không thêm chốt nào trước lời gọi phân loại lại ngoài chốt (c) của `_run` (U2-R1); không đổi `build_classify_request` hay cách chọn `later_messages` (U2-R3 là trần của T106). SHA commit ghi vào progress cho R5-5.
  - Expect: `TestExcludedByClassification::test_classified_into_excluded_team_stops_before_reasoning` (lần tạo phiếu: lời gọi model = 1, payload không chứa comment; 0 ghi phiếu, 0 comment kể cả comment hướng, comment định tuyến và thông báo; 0 Task; 0 dòng `reason`), `::test_later_mention_and_scan_skip`, `::test_department_named_as_excluded_team`, `::test_excluded_wins_over_low_confidence`, `::test_l0_still_records_exclusion`, `::test_reclassified_into_excluded_team_stops` (R5-6, U2-R2, U2-R3: lần 1 dưới ngưỡng bộ phận thường; 1 comment có chuỗi gieo A trước dòng `classify` đầu; 7 tin đến sau có chuỗi gieo B, một tin 500 ký tự; lần phân loại lại ra bộ phận loại trừ → tổng lời gọi model = 2; payload lời gọi 2 có đúng 5 tin mới nhất, mỗi tin ≤ 200 ký tự, chuỗi gieo A 0 lần; dòng `classify` mới cùng `run_id`, `stop_reason=excluded_by_classification`; `count_guidance` = 0; 0 comment, 0 Task, 0 thông báo, `modified` không đổi; 0 dòng `reason`; `@ai` rồi `run_for_ticket(comment_mention)` → vẫn 2), `::test_excluded_low_confidence_row_not_reclassified` (U2-R1: dòng loại trừ dưới ngưỡng; người tạo trả lời rồi `@ai` → tổng lời gọi = 1, có dòng `skip`), `::test_group_set_excluded_before_reply_not_reclassified` (U2-R1, test ghim: người đặt nhóm loại trừ sau lần 1 → trả lời → tổng lời gọi = 1; xanh ngay là đúng, ghi lý do trong progress), `TestExcludedTitle::test_prefixed_ticket_calls_model_zero_times`, và `erp_ai/agent/test_routing.py::TestExcludedTeam::test_decide_route_consults_excluded_predicate_for_mapped_team` (stub vị từ ghi lại đối số; phân loại ánh xạ tới nhóm X → vị từ được gọi với X). Test runner (trừ test ghim) đỏ trước rồi xanh; test `test_routing.py` là test ghim, xanh ngay là đúng. `git grep -c "parse_classification(" HEAD -- erp_ai/agent/runner.py` = 1; `git grep -n "is_excluded_team=" HEAD -- erp_ai/agent/runner.py` = 1 dòng. `cmd.test_one` xanh cho `erp_ai/agent/test_runner_routing.py`.
```

`plan-w1b.md:210` (R-3) và `:245`: tech-lead thay bằng "Đã phán ở `design-w1b-fixes-1.md` điểm 1; câu rủi ro còn lại → analyst (`--amend`), chặn nghiệm thu AC-9, không chặn T137".

---

## Điểm 2 — R-7: file HDSD không đọc được trong `search_manuals`

### Hiện trạng (dữ kiện)
- `knowledge.search_manuals` gom kết quả qua `_manual_files` rồi `_sections(path)`; `_sections` mở file bằng `open(...)` (`knowledge.py:136`). Một `PermissionError` (hoặc `OSError` khác: file bị xóa giữa lúc liệt kê và lúc đọc, lỗi I/O) ném ra khỏi cả `search_manuals` → mất kết quả của mọi file còn lại (`review-39.md:34` minor (b)).
- Quy ước sẵn có của cùng hàm: thứ không đọc được thì **bỏ qua từng mục, không làm hỏng lần tìm** — file ngoài kho, symlink ra ngoài, symlink treo, file quá `MANUALS_FILE_MAX_BYTES`, quá 500 file (`knowledge.py:125-131`; `test_knowledge.py:404-424`).
- Kế hoạch chọn "tool bắt `OSError`" → `{"ok": False, "reason": MANUALS_UNREADABLE}` chỉ vì `knowledge.py` không thuộc touchpoint U6b (`plan-w1b.md:214`). `knowledge.py` không có chủ trong đợt 1b.

### Phán quyết
1. **Bỏ qua riêng file không đọc được và báo nó; không từ chối cả lần tìm.** Sửa ở `knowledge.search_manuals` (U6a), không ở tool.
   - Mỗi file: đọc các mục của file trong một khối `try` (lấy cả danh sách `list(_sections(path))` trước khi xếp hạng, để lỗi giữa chừng không để lại mục dở của file đó); `except OSError as error` → bỏ file đó, đi tiếp file sau.
   - Báo: đúng một dòng `frappe.logger(source.LOGGER_NAME).warning(...)` cho mỗi file bị bỏ, gồm tên lớp lỗi (`type(error).__name__`) và `document` (đường dẫn tương đối trong kho HDSD, cùng giá trị trả cho model khi file đọc được). Không đường dẫn tuyệt đối, không `str(error)` (chứa đường dẫn tuyệt đối). Dùng lại `source.LOGGER_NAME` (`"erp_ai.source"`, `knowledge.py` đã import `source`) — không thêm tên logger mới.
   - Không bắt gì ngoài `OSError`; lỗi khác vẫn nổi lên (STD-ERR-1). Không đổi chữ ký, không đổi dạng trả `list[dict] | None`, không thêm khóa vào kết quả (thêm trường không phải điều AC-47 cần).
   - Mọi file đều không đọc được → `[]` (tool trả `{"ok": True, "sections": []}`, như "không khớp"); mỗi file một dòng log.
2. **Tool `search_manuals` (T148) không bắt `OSError`.** Sau sửa trên, `OSError` từ đọc file không còn thoát khỏi `knowledge.search_manuals`; một khối bắt ở tool là mã chết (STD-STYLE-5).
3. **Tên `MANUALS_UNREADABLE`: bỏ, không thay.** Không còn lý do từ chối cho ca này. Tên test `test_unreadable_file_refused_not_raised` đổi thành `test_unreadable_file_skipped_others_returned` (tool) và thêm `TestManuals::test_unreadable_file_skipped_and_logged` (U6a).

### Căn cứ
- AC-47 (`spec.md:217`): "khi kho HDSD đã cấu hình, tìm theo nội dung và trả đoạn khớp kèm tên tài liệu và vị trí". Một file hỏng làm mất đoạn khớp của mọi file khác là trái câu này; từ chối cả lần tìm còn khiến model coi như không có nguồn HDSD (khối `KNOWLEDGE_SOURCES_BLOCK`, `design-addendum-1-U6b.md:294`).
- ADR-034 QĐ 4 (tìm tri thức nằm ở `knowledge.py`, tool chỉ bọc) — sửa đúng tầng sở hữu việc đọc file, như `review-39.md:95` nêu lối "task U6b sửa `_sections`".
- STD-ERR-1 (không nuốt lỗi: có log cho từng file bị bỏ, chỉ bắt `OSError`); quy ước bỏ-từng-mục của `knowledge.py:125-131`.

### Touchpoints
| Đường dẫn | Sửa | Ghi chú |
|---|---|---|
| `erp_ai/agent/knowledge.py` | sửa vòng `for document, path in _manual_files(...)` trong `search_manuals` | U6a; không có chủ khác ở đợt 1b (`plan-w1b.md:214`) |
| `erp_ai/agent/test_knowledge.py` | thêm 1 test trong `TestManuals` | file đã có |
| `erp_ai/agent/tools/knowledge_read.py` | bỏ khối bắt `OSError` và hằng `MANUALS_UNREADABLE` khỏi đặc tả T148 | file mới của T148, dưới `erp_ai` (đã trong `allowed_new_file_roots` theo T148) |
| `erp_ai/agent/tools/test_knowledge_read.py` | đổi tên + nội dung 1 test | file mới của T148 |

Không đường mới ngoài hai file T148 đã có; không chạm `protected_paths`. Việc chia task (một task mới cho `knowledge.py` hay gộp vào T148) là của tech-lead; điều kiện thiết kế: task sửa `knowledge.py` merge trước T148 (T148 `depends:` nó), và kiểm bảng "Một file, một chủ" của `plan-w1b.md`.

### Test (đỏ trước)
| Tiêu chí | `file::tên` | Ca / khẳng định |
|---|---|---|
| AC-47, STD-ERR-1 | `erp_ai/agent/test_knowledge.py::TestManuals::test_unreadable_file_skipped_and_logged` | kho có `a.md` và `b.md` cùng chứa từ tìm; patch `open` (chỉ cho đường dẫn thật của `a.md`) ném `PermissionError` → kết quả = các mục của `b.md` (`[("b.md", 1)]`), không ném; logger `erp_ai.source` nhận đúng 1 lần `warning`, chuỗi có `PermissionError` và `a.md`, không có thư mục gốc tuyệt đối của sandbox. Subtest: cả hai file ném → `[]`, 2 dòng `warning`. Subtest: ném `ValueError` → nổi lên (chỉ bắt `OSError`). Đỏ trước: hôm nay `PermissionError` thoát khỏi `search_manuals` |
| AC-47 | `erp_ai/agent/tools/test_knowledge_read.py::TestSearchManuals::test_unreadable_file_skipped_others_returned` | qua tool: patch như trên cho một file, file kia khớp → `ok=True`, `sections` chỉ có file đọc được; trong kết quả không có khóa `reason` |

### Khối task thay thế trong `tasks-w1b.md` — T148
Dòng tiêu đề, `files:` giữ; `depends:` thêm task sửa `knowledge.py` (số do tech-lead đặt). Dòng "Tiêu chí": thay vế "file HDSD không đọc được không làm sập lần chạy" bằng "file HDSD không đọc được bị bỏ riêng ở `knowledge.search_manuals` (`design-w1b-fixes-1.md` điểm 2), tool không bắt `OSError`". Ba dòng dưới thay nguyên văn:

```
  - Receives: `knowledge.search_kb_articles(query, limit)`, `knowledge.search_manuals(query, limit, manuals_dir)` (trả `None` khi chưa cấu hình; file không đọc được đã bị bỏ riêng và ghi log bên trong, không ném `OSError` — `design-w1b-fixes-1.md` điểm 2), `redact.redact_secrets`, `read.TOOL_RESULT_MAX_CHARS`, `ToolSpec`.
  - Returns: `KNOWLEDGE_TOOL_NAMES = frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"})`; `MANUALS_NOT_CONFIGURED = "chưa có kho HDSD"`; `_limits() -> tuple[int, tuple[str, ...], int]` là chỗ đọc cấu hình duy nhất của nhóm; `TOOLS` có `search_knowledge_base(query: string 2..100)` → `{"ok": True, "articles": [{name, title, excerpt}]}` và `search_manuals(query: string 2..100)` → `{"ok": True, "sections": [{document, heading, line, excerpt}]}`, nhóm `read`. Tool không bắt `OSError` và không có hằng lý do cho file không đọc được.
  - Expect: `TestSearchKnowledgeBase::test_published_only`, `::test_reversed_words_found`, `::test_more_matches_ranked_first`, `::test_limit_from_setting`; `TestSearchManuals::test_match_returns_document_heading_line`, `::test_no_match_empty`, `::test_not_configured_refused`, `::test_manuals_not_readable_by_read_source`, `::test_secret_in_heading_masked` (bí mật nằm trong dòng tiêu đề mục → bị che trong `heading`), `::test_unreadable_file_skipped_others_returned` (patch `open` ném `PermissionError` cho một file, file kia khớp → `ok=True`, `sections` chỉ có file đọc được, không có khóa `reason`) đỏ trước (ModuleNotFoundError) rồi xanh.
```

Khối cho task sửa `knowledge.py` (tech-lead đặt số, tiêu đề, `depends:`; `files: erp_ai/agent/knowledge.py, erp_ai/agent/test_knowledge.py — test: erp_ai/agent/test_knowledge.py`):

```
  - Tiêu chí: AC-47; `review-39.md:34` minor (b), `:95`; `design-w1b-fixes-1.md` điểm 2. Chỉ sửa vòng đọc file trong `search_manuals`; không đổi chữ ký, dạng trả, `_manual_files`, `_sections`, hằng số.
  - Receives: `search_manuals`, `_manual_files`, `_sections` hiện có (`knowledge.py:80-145`); `source.LOGGER_NAME`.
  - Returns: không tên mới. Trong `search_manuals`, mỗi file: `sections = list(_sections(path))` trong `try`; `except OSError as error` → `frappe.logger(source.LOGGER_NAME).warning(...)` có `type(error).__name__` và `document` (tương đối trong kho), không đường dẫn tuyệt đối, không `str(error)`; bỏ file, đi tiếp. Lỗi khác nổi lên.
  - Expect: `TestManuals::test_unreadable_file_skipped_and_logged` (patch `open` cho `a.md` ném `PermissionError` → `[("b.md", 1)]`, 1 `warning` có `PermissionError` và `a.md`, không có gốc tuyệt đối; subtest cả hai ném → `[]`, 2 `warning`; subtest `ValueError` → nổi lên) đỏ trước rồi xanh; các test `TestManuals` khác giữ xanh.
```

`plan-w1b.md:213` (R-6): bỏ `MANUALS_UNREADABLE` và `test_unreadable_file_refused_not_raised (T148)`, thay bằng `test_unreadable_file_skipped_others_returned (T148)`. `:214` (R-7) và `:246`: thay bằng "Đã phán ở `design-w1b-fixes-1.md` điểm 2: bỏ riêng file hỏng ở `knowledge.search_manuals`, một task U6a trước T148".

---

## Tóm tắt Explore
Không gọi Explore: các file cần đọc đã biết đường dẫn; đọc trực tiếp từng đoạn (danh sách ở đầu tài liệu). Không giả định nghiệp vụ nào được designer tự quyết; một câu nghiệp vụ chuyển analyst (điểm 1).
