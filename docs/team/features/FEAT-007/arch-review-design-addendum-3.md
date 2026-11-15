Verdict: approve-with-conditions
w1 (`design-addendum-3-w1.md`): approve-with-conditions · w2 (`design-addendum-3-w2.md`): approve-with-conditions

Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- Không có cổng cho lần soát này (team.py: chỉ G5). Để trống. -->

# Soát hai bản sửa thiết kế theo phụ lục spec 3 (đợt 1: U1, U4b, U6b, U8 AC-62/63; đợt 2: U7a, U7b, U8)

**Kết luận chung.** Cả hai bản đứng được trên ADR-031 Amendment 1 và ADR-036 sau 11 điều kiện AD3-1..AD3-11 (mục 6).
- OI-1 được phán bằng ADR mới `docs/team/adr/ADR-037.md` (`proposed`). ADR này sửa ADR-019 QĐ 2 và giữ nguyên ADR-030 QĐ 4.
- Hợp đồng U4b ↔ U7 chốt theo tên của w1, với ba chỗ đổi:
  - hàm khóa gốc trả dòng (`locked_rows`);
  - dòng gom là chữ thô, thoát HTML đúng một lần ở chỗ đổ ra;
  - dòng "Chờ duyệt" chỉ thêm ở hàm chèn đề xuất duy nhất, do U4b đặt từ đợt 1.
- `latency_ms` và E-1 được nhận có điều kiện.

Không sửa spec, thiết kế, mã. Không chạy migrate hay test, vì phiên build trên `team/FEAT-007` đang chạy. Không ghi `.team/current.json`.

## Ba câu về độ khớp kiến trúc

**w1.**
1. w1 khớp ADR-036 QĐ 1–9 ở khung: một hàm ghi `post_guidance` gọi ở một chỗ; bộ gom theo `run_id` trong `frappe.flags`; dấu hiệu ở vị trí 0 cộng lời từ chối ở bước (0) của `post_comment_tool`; `locked_count` đọc có khóa (QĐ 4, AR3-6, AR3-7).
2. Có hai chỗ lệch kiến trúc:
   - OI-1 không đạt được dưới ADR-019 QĐ 2 (chỉ phân loại ở `ticket_insert`), nên cần ADR-037.
   - Lời gọi `post_guidance` bám vào `final`, mà `final` chưa phủ lối ra `max_turns` của vòng suy luận (`runner.py:609-658`). Ở lối ra đó dòng định tuyến và Task mất hẳn, trái AC-23 `[changed]`.
3. Hợp đồng với U7 phải theo bảng mục 4:
   - dòng "Chờ duyệt" chuyển từ `_run_tool` sang hàm chèn duy nhất;
   - mọi chỗ đổ dòng gom ra Comment thoát HTML đúng một lần;
   - `locked_rows` là hàm khóa gốc.

**w2.**
1. w2 khớp ADR-031 Amendment 1:
   - thứ tự A1-1 (S-1);
   - tập A1-2 định nghĩa một lần trong `catalog.py` (S-2);
   - căn cứ chế độ nằm trong dấu (A1-5, S-4);
   - kiểm lại lúc áp dụng (A1-3, T-12).

   w2 cũng khớp ADR-036 QĐ 2, 5: bộ gom thay comment riêng, chống trùng ở đường chèn duy nhất, "Tự làm" không qua `post_result` (AR3-8).
2. Chỗ lệch nằm ở hợp đồng với U4b:
   - `ctx.direction_run` kéo theo một trường mới trên `ToolContext` của U1;
   - `ticket_lock.locked_find` là module khóa thứ hai;
   - `collector.add(..., line_html)` dẫn tới thoát HTML hai lần.

   Không tên nào trong ba tên này có ở w1, nên phải thay theo bảng mục 4.
3. `latency_ms` (AD3-7) và E-1 (AD3-8) được nhận có điều kiện. Còn thiếu: AC-67 bản phụ lục 4 chưa có ca chạy cả lần chạy cho "Đổi trường" và nhóm loại trừ khi danh mục rỗng (AD3-9).

## Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Vòng suy luận kết thúc thế nào | `return` khi `not wants_tools or not tool_results` (`:655`); hết `max_turns` thì vòng `for` tự hết, không qua `return` (`:609`, `:642`) | `team/FEAT-007:erp_ai/agent/runner.py` |
| Commit trong lần chạy | `write_entry` commit mỗi lượt (`run_log.py:56`); `_route` commit ở cuối (`runner.py:326-358`) | như cột trái |
| `ToolContext` | có `run_id`; không có cờ chế độ; frozen; file của U1 | `team/FEAT-007:erp_ai/agent/tools/registry.py:13-24` |
| Import của `write_ticket.py` | `policy`, `site_facts`, `classification`, `routing`, `registry`, `constants`; không import `propose_change` | `team/FEAT-007:erp_ai/agent/tools/write_ticket.py:1-8` |
| Hàm chèn đề xuất | `_insert(ctx, values)`; U7a đổi tên thành `insert_proposal` | `propose_change.py:104`; `design-addendum-2-U7a.md:216` |
| `latency_ms` | mô tả trên form: "Thời gian chờ của lần gọi … từ lúc gửi đến lúc nhận trả lời"; chỉ `runner._call_fields` ghi; không mã nào gộp hay đọc nó | `erp_ai_log.json`; grep `latency` trên `team/FEAT-007` |
| Dòng `classify` mà báo cáo và handler dùng | báo cáo: dòng có kết quả đầu tiên (`erp_ai_accuracy.py:236-242`); handler ghi sửa của người vào dòng gần nhất (`handlers.py:50`, `:73`, `:84-96`) | như cột trái |
| Đếm lần chạy | `runs_today` đếm `run_id` khác nhau của dòng `classify`/`reason` | `policy.py:80` |
| Trigger | hai trigger khác nhau là hai job (`job_id` có trigger) | `queue.py:18` |
| AC-67 mới | "Đổi trường"/nhóm loại trừ không dòng → 0 đề xuất, "Hướng xử lý" nêu việc tay và lý do "cần dòng danh mục" | `spec-addendum-4.md:47` |

## 1. Phán OI-1: lần chạy sau câu hỏi dưới ngưỡng có phân loại lại → **có**, theo ADR-037

**Chọn.** Lần chạy có trigger khác `ticket_insert`, mức ≠ `L0`, mà vị từ "dưới ngưỡng" (ADR-030 QĐ 4) đúng với dòng `classify` có kết quả gần nhất, sẽ chạy lại **đúng** bước phân loại:
- cùng hàm dựng request, thêm tham số tùy chọn cho tin đến sau câu hỏi;
- ghi một dòng `classify` mới;
- rồi đi như lần tạo phiếu: chọn chế độ ADR-036 QĐ 7 sau parse → `_route` → `_reason`.

**ADR bị chạm:**
- ADR-019 QĐ 2 **sửa** (câu "chỉ chạy trong `ticket_insert`"), QĐ 1 **bổ sung** (tham số tin thêm).
- ADR-030 QĐ 4 **giữ** (một vị từ; "của bước phân loại" = dòng gần nhất).
- ADR-036 QĐ 1, 7 **bổ sung** (chọn chế độ sau khi phân loại lại).

**Hai ràng buộc mới, vì phân loại lại mở ra hai lối lệch mà w1 chưa thấy:**
- `_route` khóa phiếu rồi đọc có khóa "đã có dòng `classify` `applied = 1`". Lý do: hai lần chạy khác trigger có thể cùng vượt ngưỡng và định tuyến hai lần.
- Dòng tham chiếu của phiếu là dòng có kết quả đầu tiên, dùng cho cả `human_corrected_to` và báo cáo. Lý do: hôm nay handler ghi vào dòng gần nhất, còn báo cáo đọc dòng đầu.

**NFR-2.** Cận mỗi lần chạy giữ "1 phân loại + ≤ `max_turns`". Số lần chạy trong ngày không tăng (cùng `run_id`). Lời gọi thêm chỉ có ở lần chạy mà nếu không có nó thì chỉ hỏi.

**Phương án loại:** độ tin cậy do lượt suy luận tự báo, bỏ ngưỡng cho tin trả lời, phân loại lại ở mọi lần chạy, bỏ chuỗi 3. Lý do ở ADR-037.

## 2. Phán hai lựa chọn của w2

**`latency_ms` cho dòng bước áp dụng (S-7, `design-addendum-3-w2.md:134-136`, `:300`): nhận, có điều kiện AD3-7.**
- AR3-9 cho "dòng bước áp dụng hoặc logger, không thêm trường".
- AC-68 đòi "ghi vào nhật ký để đo" và "1 mục nhật ký có thời gian". Logger không phải ERP AI Log mà người xem được trên Desk, nên chỉ logger là chưa đủ chữ AC-68.
- Cột hôm nay chỉ `runner._call_fields` ghi, không ai gộp. Dùng lại thì không vỡ người đọc nào.
- Điều kiện:
  - Mô tả của trường trên form phải nêu cả hai nghĩa, vì hôm nay nó nói "lần gọi … từ lúc gửi đến lúc nhận trả lời", sai cho dòng `change`.
  - Chỉ dòng `change` bước `apply` mang nghĩa mới.

**E-1 (`catalog_list_allowed` trả thêm tập mặc định; một câu của `CATALOG_BLOCK`; `:188-193`): nhận, có điều kiện AD3-8.**
- Tool chỉ import `FIXED_SURFACE_ACTIONS` và đưa ra, không tự quyết (ADR-031 A1-2, Ràng buộc A1 "chỉ import").
- `prompts.py` không đọc cấu hình (ADR-030).
- Không đổi hình dạng ADR nào.
- Thiếu E-1 thì AC-67 "danh mục rỗng → 2 đề xuất" hỏng thật: tool trả `[]`, prompt bảo chỉ làm việc trong danh sách.

## 3. AC-67 bản phụ lục 4 (`spec-addendum-4.md:47`) so với w2

| Vế của AC-67 mới | w2 | Kết luận |
|---|---|---|
| Đề xuất khi có dòng phủ hoặc thuộc tập mặc định | S-1 bước 5–6, S-2 | khớp |
| "Đổi trường" / nhóm loại trừ không dòng → 0 đề xuất, việc tay + lý do "cần dòng danh mục" | S-2, S-3 (`OUT_OF_CATALOG` chứa "cần dòng danh mục"), S-5 (bước 6 → `REFUSED_LINE` vào "Cần ai quyết") | khớp ở hình dạng. **Thiếu test cả lần chạy** (T-23 chỉ có ca cấm cứng và `Cấm`; T-5, T-19 ở mức tool) → AD3-9 |
| "Hướng xử lý nêu việc tay" | dòng `REFUSED_LINE` nằm trong mục "Cần ai quyết" của **comment** hướng xử lý | Đọc "mục 'Hướng xử lý'" là comment hướng (AC-65 (a) liệt kê "Cần ai quyết" là phần của comment đó). Dòng tất định thì kiểm được; chữ model thì không. Test phải assert trên nội dung comment do `count_guidance` đếm (AD3-9). Team-leader ghi một dòng journal cách đọc này |
| Thêm dòng `Cần duyệt` → lần chạy sau có đề xuất | T-9 (mức tool, giữa hai lời gọi) | đủ: dòng có hiệu lực từ lần đọc kế, không phụ thuộc lần chạy |
| Chống trùng: còn chờ hoặc đã duyệt; sau Từ chối/hết hiệu lực nhờ lại → mới | S-6 `DUPLICATE_BLOCKING_STATUSES`, T-17 | khớp |
| Hiện cùng lúc trong ngăn | S-11, T-26 | khớp |
| Cap L1 → 0 đề xuất | không có trong T-1..T-27 | dẫn test AC-32 đã có của U7a, hoặc thêm 1 ca vào T-23 (AD3-9) |
| Đoạn "Phụ thuộc spec" (`:14`) | còn nói analyst phải `--amend` | đã cũ: `spec-addendum-4.md` có rồi; sửa chữ (AD3-10) |

## 4. Hợp đồng U4b ↔ U7: một bộ tên

Quy ước:
- Mọi tên mới nằm trong `erp_ai/agent/tools/write_ticket.py` (U4b), trừ hai dòng ghi chỗ khác.
- Hướng phụ thuộc một chiều: `propose_change`, `catalog_tools` → `write_ticket`. `write_ticket` không import `propose_change`, `catalog`, `catalog_tools`, `runner` (STD-DESIGN-6).
- Chế độ "đưa hướng" chỉ có một nguồn sự thật: `collecting(run_id)`. Không có trường trên `ToolContext`.

| Tên chung | Chữ ký và hành vi | Chủ | Ai gọi | File nào phải đổi chữ |
|---|---|---|---|---|
| `locked_rows` | `(ticket_name: str, doctype: str, filters: dict, fields: tuple[str, ...] = ("name",)) -> list[dict]`. Bước 1: `frappe.db.get_value("HD Ticket", t, "name", for_update=True)`, nếu None thì `ValueError`. Bước 2: `frappe.db.get_values(doctype, filters, list(fields), as_dict=True, for_update=True)`. Là **chỗ duy nhất** có `for_update=True` của ADR-036 QĐ 4 | U4b | `locked_count`, `propose_change` (U7a, chống trùng), `runner._route` (ADR-037 QĐ 4) | w1 `:44`, `:59` (thêm; `locked_count` gọi nó), `:203` (luật AST đổi sang `locked_rows`); w2 `:38` (bỏ `ticket_lock.locked_find`), `:121`, `:253` (đích patch của `test_insert_proposal_uses_locked_helper`) |
| `locked_count` | `(ticket_name, doctype, filters) -> int` = `len(locked_rows(ticket_name, doctype, filters))` | U4b | `post_notice`, `ba_note`, `create_task`, `count_guidance` | w1 `:59` (thân thành lời gọi trên) |
| `collecting` | `(run_id: str) -> bool` | U4b | `write_ticket`, `propose_change`, `catalog_tools` | w2 `:39` (bỏ R-2), `:109`, `:112`, `:125`, `:150-151`, `:154`; `:233` và T-19, T-21 (test dùng `open_collector(run_id)` ở `setUp`, `close_collector` ở `tearDown`, không dựng `ctx.direction_run`) |
| `collect` | `(run_id: str, section: str, line: str) -> None`. `line` là **chữ thô**, không HTML. Bộ gom chưa mở → không làm gì. `section ∉ GUIDANCE_SECTIONS` → `ValueError`. Cặp (mục, dòng) đã có → bỏ qua (cùng đề xuất gọi hai lần trong một lần chạy không ra hai dòng) | U4b | `runner._route`, `set_classification`, `create_task`, `propose_change`, `catalog_tools` | w1 `:62` (thêm câu "chữ thô" và "trùng thì bỏ qua"); w2 `:40` (bỏ R-3), `:110-111`, `:125`, `:150`, `:154`: `collector.add(ctx, S, html)` → `write_ticket.collect(ctx.run_id, S, text)`, bỏ `escape_html` trên giá trị đưa vào dòng gom |
| `SECTION_DONE`, `SECTION_PENDING`, `SECTION_DECIDE` | hằng chữ của w1 `:34` | U4b | như trên, chỉ import | w2 `:40` (import từ `write_ticket`) |
| `open_collector`, `close_collector`, `hold_analysis`, `collected`, `mark_work_only`, `count_guidance`, `guidance_filters`, `post_guidance`, `GUIDANCE_MARKER` | như w1 `:44-54`, `:57-64` | U4b | chỉ `runner.py`, `write_ticket.py` (và test). Không đơn vị U7 nào gọi | không |
| `pending_line` (ở `erp_ai/agent/tools/propose_change.py`) | `(proposal) -> str`, chữ thô. Loại code, bench: `PENDING_LINE.format(proposal=name, label=<nhãn cố định theo change_kind>)`, không chép tham số (B-3). Loại bản ghi: câu tóm tắt đã che (bộ dựng `record_summary`, B-3) + `catalog.mode_basis_text(...)` | U4b tạo (code, bench), U7a mở rộng (bản ghi) | chỉ hàm chèn | w1 `:106` (bỏ vế (b) khỏi `_run_tool`; `PENDING_LINE` và nhãn chuyển vào `propose_change.py`), `:140`; w2 `:90`, `:100`, `:125` (chữ thô; nhận bản ghi đề xuất) |
| Chỗ thêm dòng "Chờ duyệt" | **Một chỗ:** hàm chèn duy nhất (`_insert`, sau U7a là `insert_proposal`). `collecting(ctx.run_id)` ∧ (chèn mới, mọi loại) → `collect(ctx.run_id, SECTION_PENDING, pending_line(doc))`. U7a thêm nhánh trùng có trạng thái `Chờ duyệt`. `runner.py` không thêm dòng "Chờ duyệt" | U4b đặt (đợt 1), U7a thêm nhánh trùng | — | w1 `:106`, `:138`, `:140`, `:205`; w2 `:41`, `:125`, `:302` |
| `DUPLICATE_BLOCKING_STATUSES` | như w2 `:124` | U7a, `propose_change.py` | chỉ hàm chèn | không |
| `_run_tool` | giữ `held` → không thêm mục (w1 U4b-16 (a)); điều kiện bước `propose` thêm `not outcome.get("duplicate")` (w2 S-6) | U4b, rồi U7a | — | w1 `:106` (chỉ còn vế (a)) |

**Vì sao chốt như vậy.**
- **Hàm khóa trả dòng.** Chống trùng đề xuất cần tên và trạng thái của bản ghi cũ (ADR-036 QĐ 5 "trả đề xuất cũ cho bộ gom"). Một hàm đếm không đủ, còn hai hàm khóa độc lập là chép (QĐ 4 "Không chép"). Không mở module mới (`ticket_lock`): STD-STRUCT-3, w1 `:28` "không file nguồn mới".
- **Không cờ trên `ToolContext`.** `registry.py` là của U1, ngoài file chạm của U4b và U7 (w1 `:147`). Một cờ cạnh `collecting` sẽ thành hai sự thật cho cùng một chế độ.
- **Chữ thô, thoát một chỗ.** `Comment.content` có `ignore_xss_filter` (w1 `:18`) và giá trị trong dòng có phần đến từ model (giá trị "Tự làm", DocType trong `TEST_SITE_COMMENT`). Phải thoát đúng một lần. Thoát ở chỗ đổ ra thì một test bắt được cả hai lỗi: thiếu thoát và thoát hai lần.
- **"Chờ duyệt" ở hàm chèn.** Mọi đề xuất, mọi tool, kể cả Project của U8, đều qua hàm chèn duy nhất (ADR-031 QĐ 3). `PROPOSE_TOOLS` của runner là một danh sách phải giữ đồng bộ tay: U8 quên thêm tool Project là mất dòng. U4b đặt lời gọi ngay từ đợt 1 để chuỗi 6 của AC-65 (đề xuất code trong "Chờ duyệt", w1 `:169`) xanh trước khi U7a có mặt.

## 5. Finding

`severity | STD | file:line | description | fix`

- major | STD-DESIGN-2 | `design-addendum-3-w1.md:233`, `:166`; `design-addendum-3-w1.md:128` (U6b-1 ca 2) | OI-1: dưới ADR-019 QĐ 2 và U1 `:260`, độ tin cậy dưới ngưỡng giữ mãi, nên chuỗi 3 của AC-65 và AC-41 ca 2 không bao giờ đạt | AD3-1 theo ADR-037
- major | STD-TEST-8 | `design-addendum-3-w1.md:105` (U4b-15) | `final ∧ collecting` chưa định nghĩa `final`. Hết `max_turns` thì vòng `for` tự hết, không qua `return` (`runner.py:609`, `:642`, `:655`). Lúc đó không gọi `post_guidance`, nên dòng định tuyến, Task, đề xuất đã gom đều mất, trái AC-23 `[changed]` | AD3-2
- major | STD-SEC-3 | `design-addendum-3-w1.md:104` (`_done_suffix`), `:105` (comment kết quả khi thua chạy song song); `design-addendum-3-w2.md:110-111`, `:150`, `:154` | w1 chỉ thoát ở `post_guidance` (`:64`). Hai chỗ đổ dòng khác không nói thoát, còn w2 thoát trước khi gom. Kết quả là thiếu thoát (XSS trên `Comment` có `ignore_xss_filter`) hoặc thoát hai lần (`&amp;lt;`) | AD3-4
- major | STD-DESIGN-4 | `design-addendum-3-w1.md:106` ↔ `design-addendum-3-w2.md:41`, `:125` | Hai chỗ thêm dòng "Chờ duyệt" (`_run_tool` và hàm chèn) cho cùng một đề xuất → hai dòng | AD3-5
- major | STD-DESIGN-4 | `design-addendum-3-w2.md:38` ↔ `design-addendum-3-w1.md:44`, `:59` | Hai hàm trợ giúp khóa (`ticket_lock.locked_find` ở module mới, `write_ticket.locked_count`), trái ADR-036 QĐ 4 "Không chép" và STD-STRUCT-3 | AD3-3, AD3-6
- major | STD-DESIGN-1 | `design-addendum-3-w2.md:39`, `:233` | `ctx.direction_run` thêm trường vào `ToolContext` (`registry.py`, file của U1, ngoài file chạm của U4b/U7) và thành sự thật thứ hai bên cạnh `collecting` | AD3-3
- major | STD-TEST-2 | `design-addendum-3-w2.md:259` (T-23), `:276` | AC-67 `[changed]` (`spec-addendum-4.md:47`) có hai ca mới mức lần chạy ("Đổi trường" rỗng, nhóm loại trừ rỗng → 0 đề xuất, comment hướng nêu việc tay và "cần dòng danh mục"); w2 chỉ có ở mức tool (T-5, T-19) | AD3-9
- major | STD-DOC-2 | `design-addendum-3-w2.md:134`, `:203`, `:300` | `latency_ms` đổi nghĩa trên dòng `change`, trong khi mô tả trên form (`erp_ai_log.json`) nói "lần gọi … từ lúc gửi đến lúc nhận trả lời". Người đọc nhật ký hiểu sai | AD3-7
- minor | — | — | 7 điểm nhỏ:
  - w2 `:14`, `:30` đã cũ (phụ lục 4 có, w1 đã viết);
  - bộ lọc của S-6 `:121` viết tắt ba khóa không có giá trị;
  - khóa `default_needs_approval` trong kết quả E-1 `:191` trùng tên hàm `catalog.default_needs_approval`;
  - `LIST_ALLOWED_NOTE` nên thêm "vẫn gọi tool để hệ thống ghi việc tay vào 'Cần ai quyết'";
  - `LIKE` ở w1 `:60` có `_` là ký tự đại diện (vô hại vì vị trí 0 đã chặn);
  - ADR-036 QĐ 3 nói "sau phép thoát HTML hiện có" trong khi `post_comment` không thoát (w1 `:16`); bước (0) cộng tiền tố vị trí 0 của w1 bù đủ, không cần sửa ADR;
  - ca cap L1 của AC-67 chưa dẫn test

  | dev/designer quyết

## 6. Điều kiện (tech-lead chép vào plan)

| Mã | Điều kiện | Chủ | Kiểm bằng | Chặn gì |
|---|---|---|---|---|
| AD3-1 | Theo ADR-037 QĐ 1–7. Phân loại lại ở lần chạy không phải tạo phiếu khi dòng `classify` có kết quả gần nhất làm vị từ "dưới ngưỡng" đúng (mức ≠ `L0`); cùng hàm dựng request, có tham số tin thêm; chọn chế độ sau khi parse. `_route` khóa phiếu và bỏ qua nếu đã có dòng `applied = 1`. Hàm "dòng tham chiếu" (dòng có kết quả đầu tiên) dùng ở `handlers.py` cho `human_corrected_to`. w1 sửa U4b-11 (`:101`): "lần tạo phiếu **và lần phân loại lại**: quyết sau `_classify` parse", và gỡ chữ "phụ thuộc OI-1" (`:166`, `:130`, `:233`) | designer U4b; U6b chỉ đổi dẫn chiếu | Ràng buộc ADR-037 (chuỗi 3, hai kết nối, request trùng byte, sửa của người, NFR-2) | plan đợt 1 |
| AD3-2 | Gọi `_finish_guidance` ở **mọi lối ra không lỗi** của vòng suy luận: `not wants_tools`, `not tool_results`, hoặc `turn == max_turns`. Luôn gọi trước `write_entry` của lượt đó. Lỗi cổng hoặc hết thời gian vẫn đi U4b-14. Thêm test `TestOneGuidance::test_max_turns_exit_still_posts_guidance` | designer U4b | test | plan đợt 1 |
| AD3-3 | Dùng đúng bảng mục 4: tên, chữ ký, chủ, hướng phụ thuộc. w2 bỏ R-1..R-4 (`:32-41`), thay chữ ở các dòng cột cuối; test U7 mở/đóng bộ gom bằng `open_collector`/`close_collector`. Thêm luật kiến trúc `test_write_ticket_imports_no_proposal_or_catalog_module` (AST: `write_ticket.py` không import `propose_change`, `catalog`, `catalog_tools`, `runner`) | designer U4b (w1), designer U7a/U7b (w2) | AST + đọc chữ | plan đợt 1 (w1), đợt 2 (w2) |
| AD3-4 | Dòng gom là chữ thô. Mọi chỗ đổ dòng gom ra `Comment` thoát HTML đúng một lần, gồm `post_guidance`, `_done_suffix` của thông báo lỗi, và comment kết quả khi thua chạy song song. Người gọi `collect` không thoát. Test: giá trị `"<b>&x"` trong dòng "Tự làm" và trong tên Task → nội dung comment chứa `&lt;b&gt;&amp;x` đúng một lần, ở cả ba chỗ đổ | designer U4b, U7a, U7b | test `test_write_ticket.py`, `test_catalog_tools.py` | plan đợt 1, 2 |
| AD3-5 | Dòng "Chờ duyệt" chỉ thêm trong hàm chèn duy nhất của `propose_change.py`, đặt ở U4b (đợt 1) cho mọi loại; U7a thêm nhánh trùng và dòng loại bản ghi. `runner.py` không có `PENDING_LINE`. Luật kiến trúc: tên `SECTION_PENDING` chỉ xuất hiện trong `write_ticket.py` và `propose_change.py` (ngoài test) | designer U4b; U7a | AST/grep + chuỗi 6 AC-65 + T-17, T-23 | plan đợt 1 |
| AD3-6 | `locked_rows` là chỗ duy nhất có `for_update=True` của ADR-036 QĐ 4; `locked_count` gọi nó. Luật `test_locked_count_queries_use_for_update` của w1 `:203` đổi đích sang `locked_rows`. Test hai kết nối của w1 (`:180`, `:191`) giữ | designer U4b | AST + test hai kết nối | plan đợt 1 |
| AD3-7 | Nhận `latency_ms` trên dòng `change` bước `apply`, ba kết cục, không có cho hoàn tác. Mô tả trường trong `erp_ai_log.json` thêm một câu: "Dòng bước áp dụng của đề xuất: thời gian từ Duyệt tới kết quả". Chạy lại `test_doctype_descriptions`. Không đổi kiểu trường, không migration dữ liệu. Logger `approve_to_result_ms` giữ | designer U7a | T-15, T-16 + test mô tả | plan đợt 2 |
| AD3-8 | Nhận E-1. Tập trả về lấy bằng import `catalog.FIXED_SURFACE_ACTIONS`, không lập danh sách. Đổi tên khóa kết quả cho khác tên hàm (designer chọn). T-27 giữ | designer U7a (tool), U7b (`CATALOG_BLOCK`) | T-27, T-18 | plan đợt 2 |
| AD3-9 | T-23 thêm `test_empty_catalog_update_fields_manual_line` và `test_empty_catalog_excluded_team_manual_line`. Trong cả lần chạy, stub gọi tool → 0 đề xuất, đích không đổi; nội dung comment do `count_guidance` đếm có dòng `REFUSED_LINE` chứa "cần dòng danh mục". Thêm hoặc dẫn ca cap L1 → 0 đề xuất. Mục 8 của w2 thêm các test này vào AC-67 | designer U7a | test | plan đợt 2 |
| AD3-10 | Sửa chữ cũ của w2: `:14` (phụ thuộc spec → `spec-addendum-4.md`), `:30` (w1 đã có), `:300-302` (mục 10 theo phán quyết ở đây) | designer U7a | đọc chữ | plan đợt 2 |
| AD3-11 | Bảng đơn vị của `arch-impact.md` đổi file chạm, thứ tự merge giữ. **U4b** thêm `erp_ai/agent/tools/propose_change.py` (lời gọi "Chờ duyệt", `pending_line` code/bench), `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/handlers.py` (ADR-037 QĐ 5) và test handler hiện có; `prompts.py` thêm phần hàm dựng request phân loại. **U7a** thêm `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` (chỉ mô tả). U6b vẫn merge sau U4b; ca AC-41 thứ hai nay dựa vào ADR-037 trong U4b | tech-lead | plan đợt 1, 2 | plan |

## 7. Quét NFR và chiều (phần chạm bởi lần soát này)

| Mục | Kết luận |
|---|---|
| NFR-2 | Đã quyết (ADR-037 QĐ 6): cận mỗi lần chạy giữ nguyên; +1 lời gọi phân loại chỉ ở lần chạy sau câu hỏi; `runs_today` không đổi cách đếm |
| NFR-3 | Đã quyết: định tuyến tối đa một lần dưới khóa (ADR-037 QĐ 4); "Chờ duyệt" một chỗ, trùng thì bỏ qua (AD3-5, mục 4) |
| NFR-1, NFR-4 | Không đổi; AR3-4 được giữ qua S-2, T-3 |
| Đường ghi | Một hàm khóa (`locked_rows`), một chỗ "Chờ duyệt", một hàm ghi hướng |
| Lỗi, log | Đã quyết: lối ra `max_turns` (AD3-2); `latency_ms` hai nghĩa có mô tả (AD3-7). Để designer: chữ lý do "đã định tuyến" |
| Bảo mật | Đã quyết: thoát HTML một lần ở chỗ đổ (AD3-4); tin thêm cho phân loại lại là dữ liệu, có trần độ dài (ADR-037 QĐ 2) |
| Triển khai, dữ liệu | Không trường mới, không migration; đổi mô tả một trường; không cần điền lại dòng tham chiếu |

## 8. Tự phản biện

Các cặp task cùng tuân mọi ADR (kể cả ADR-037) mà vẫn có thể xung đột, và chỗ đã siết:
1. U4b thêm "Chờ duyệt" ở `_run_tool`, U7a thêm ở hàm chèn → hai dòng. Siết: AD3-5, kèm luật grep `SECTION_PENDING`.
2. U7b thoát giá trị "Tự làm" rồi gom, `post_guidance` thoát lần nữa → `&amp;lt;`. Siết: AD3-4, kèm test ở ba chỗ đổ.
3. U4b phân loại lại và ghi dòng `classify` thứ hai, handler ghi sửa vào dòng gần nhất, báo cáo đọc dòng đầu → mất sửa. Siết: ADR-037 QĐ 5.
4. `@ai` và người tạo trả lời chạy song song, cả hai vượt ngưỡng sau khi phân loại lại → hai lần gán. Siết: ADR-037 QĐ 4.
5. U6b phân loại lại trong handler để "tiết kiệm", U4b làm ở runner. Siết: ADR-037 QĐ 1, 7 và Ràng buộc "handlers không gọi bước phân loại".
6. U7a khóa bằng module riêng, U4b bằng `locked_count` → hai lối `for_update`. Siết: AD3-6, kèm AST.
7. U7 dựng `ctx.direction_run`, U4b dùng `collecting` → hai sự thật, test U7 xanh mà chạy thật thì sai chế độ. Siết: AD3-3 (không trường mới; test dùng `open_collector`).
8. Lần chạy hết `max_turns`, U4b chỉ gọi hàm ghi ở `end_turn` → mất dòng định tuyến. Siết: AD3-2.

Sau khi siết, không còn cặp nào tìm được trong phạm vi hai file.

## 9. Việc tiếp

- **Team-leader:**
  - ghi journal: "arch-review-design-addendum-3: approve-with-conditions; ADR-037 (OI-1); AD3-1..AD3-11";
  - ghi cách đọc "mục Hướng xử lý = comment hướng xử lý" cho AC-67 (mục 3);
  - đưa ADR-037 cho người duyệt cùng ADR-036, ADR-031 A1.
- **Designer:** sửa w1 theo AD3-1..AD3-6; sửa w2 theo AD3-3, AD3-4, AD3-7..AD3-10. Không cần vòng architect mới, trừ khi đổi hình dạng ở bảng mục 4 hoặc ADR-037 QĐ 1–5.
- **Tech-lead:** chép AD3-n vào plan đợt 1, 2; áp AD3-11 vào bảng đơn vị.
