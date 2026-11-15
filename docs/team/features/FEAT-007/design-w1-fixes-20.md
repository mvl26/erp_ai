# FEAT-007 — design-w1-fixes-20: comment hướng xử lý do hàm ghi dựng sau phụ lục 5 (U4b; T102–T105, T116–T118)

- Người viết: designer, 2026-11-15. Cỡ L. Lượt W2. Chỉ tài liệu.
- Đầu vào: `spec-addendum-5.md:31` (H-4), `:39-50` (bảng AC), `:63-64` (3.1 AC-65 (a), AC-66), `:70-71` (3.2 AC-23, AC-32), `:79` (AC-39 (3)), `:186`, `:192-193`; `ADR-038.md:24-40`; `ADR-036.md:37`; `design-addendum-3-w1.md` (ghi tắt `w1.md`) `:30-70`, `:96-106`, `:160-198`; `design-addendum-1-U4b-U8.md` (ghi tắt `U4b.md`) `:127-131`, `:168`, `:171`, `:182`, `:281`; `design-addendum-1-U4b-U8-fixes.md:266`, `:404`; `arch-review-design-addendum-3.md` (ghi tắt `AD3.md`) `:128-131`, `:171-172`; `design-addendum-3-w2.md:40`, `:110-111`, `:154`; `arch-impact-chg-002.md:91`; `tasks.md:982-1001`, `:1052-1066`.
- Thứ tự thắng của chữ (theo `tasks-w1.md:15`): file này thắng `AD3.md`, `w1.md`, `U4b-fixes.md`, `U4b.md` ở đúng các chỗ nêu dưới; chỗ không nêu giữ nguyên.
- Không đụng: chữ prompt của `prompts.py` (lượt W1, `design-w1-fixes-19.md`); ngăn U7b (chờ architect); U7a (dòng "Chờ duyệt" loại bản ghi). T105 vẫn `depends: T126`. `team.py claim` không chạy: lời giao chỉ cho ghi đúng file này.
- Tên mục và người viết mục lấy đúng `spec-addendum-5.md:63`: **Nhận định** (model), **Hướng xử lý** (model: các bước, việc bot làm khi bấm "Duyệt ngay"; hệ thống thêm: việc người phải làm tay kèm lý do), **Đã làm** (hệ thống, AC-66), **Chờ duyệt** (hệ thống, AC-67). Không mục "Căn cứ", không mục "Cần ai quyết". Không đặt tên mục mới.

---

## Dò mã (chỉ đọc, `team/FEAT-007` @ `c7002de`, qua `git -C .claude/worktrees/feat-007` và `git show`)

| Câu hỏi | Kết quả | Chỗ |
|---|---|---|
| U4b (T100–T118) đã có mã chưa | Chưa: `write_ticket.py` không có `SECTION_`, `GUIDANCE`, `section_text`, `post_guidance`; `propose_change.py` không có `collect`, `PENDING`; `runner.py` không có `_done_suffix`, `_finish_guidance`. `tasks.md:972-1001` đều `[ ]` | grep trên worktree |
| Hàm chèn đề xuất | `_insert(ctx, values)` tạo bản ghi rồi gọi `_comment(ctx, proposal)` (comment đề xuất riêng, AC-33, không đổi) | `erp_ai/agent/tools/propose_change.py:125-139` |
| Tên ngăn trên trang phiếu | `ACTION_LABEL = "Trao đổi với bot"`, `TEXT_CHAT_SECTION = "Trao đổi với bot"` | `erp_ai/public/js/agent_status_indicator.js:4`, `:8` |
| Câu "việc người làm tay kèm lý do" có sẵn ở bước định tuyến | `ASSIGN_REQUEST = "Bot chưa gán được người phụ trách cho phiếu này: {reason}. Nhờ trưởng nhóm phân công."`; `NO_SLA`; `TASK_REQUEST`; `_route` nối chúng vào `lines` | `erp_ai/agent/tools/route_ticket.py:21-29`; `erp_ai/agent/runner.py:437`, `:442`, `:478`, `:529` |
| Tiền tố dòng kết quả (ADR-038 QĐ 3) | `f"kết quả đề xuất {fields.get('name')} ({_target(fields)}): …"`, chữ thô qua `escape_html`, không thẻ HTML ở đầu | `erp_ai/agent/changes/result_comment.py:81-87`, `:97` (`team/FEAT-007`) |
| `post_restart_notice` (CHG-002) | Chưa có trên `develop` lẫn `team/FEAT-007` (`git grep` rỗng); vào nhánh feature qua T126 | — |
| Ai dùng khóa `SECTION_DECIDE` ngoài U4b | `design-addendum-3-w2.md:40`, `:110-111`, `:154` (dòng từ chối của bộ thực thi, môi trường, danh mục; đợt 2, chưa có số task); T115 (`tasks.md:1050`: câu cảnh báo của `_route`) | grep tài liệu |
| ADR có ghi tên mục | `ADR-036.md:37` QĐ 2: "Hàm ghi dựng các mục "Đã làm", "Chờ duyệt", "Cần ai quyết" từ bộ gom" (xem F-1) | — |

**Chưa chạy:** không test nào, không `cmd.*` nào (lời giao cấm chạy test). Mọi chuỗi HTML, vị trí chèn, số `<li>` dưới đây là thiết kế; chưa kiểm trên site. `frappe.utils.escape_html` thoát cả dấu `"` hay không: chưa dò, nên test so `escape_html(dòng)` chứ không so chữ thô.

---

## Điểm 1 — Thứ tự mục, chữ dự phòng, việc bị từ chối và lý do vào "Hướng xử lý" (T102, T103, T104, T116)

### Phán quyết

**1.1 Khóa bộ gom (T102).** Thay `w1.md:34-35`:
```python
GUIDANCE_HEADER = "Hướng xử lý"
SECTION_DONE, SECTION_PENDING = "Đã làm", "Chờ duyệt"
SECTION_DECIDE = GUIDANCE_HEADER   # khóa bộ gom của dòng "việc người phải làm tay kèm lý do"; hiện trong mục "Hướng xử lý", không có tiêu đề riêng
GUIDANCE_SECTIONS = (SECTION_DONE, SECTION_PENDING, SECTION_DECIDE)
```
Giữ tên Python `SECTION_DECIDE` để không đổi lời gọi của T115 (`tasks.md:1050`) và của đợt 2 (`design-addendum-3-w2.md:110-111`, `:154`). Đổi giá trị: chuỗi "Cần ai quyết" không còn trong mã nguồn. Căn cứ: `spec-addendum-5.md:63` ("hệ thống không tự thêm hai mục đó"), `:64` (việc bộ thực thi từ chối "không có mục riêng: ghi trong "Hướng xử lý""), `:70` điều (2).

**1.2 Thân comment hướng (T103, thay bước (3) của `w1.md:64`).** Thứ tự cố định theo `spec-addendum-5.md:63`: Nhận định → Hướng xử lý → Đã làm → Chờ duyệt.
1. `text = analysis or GUIDANCE_FALLBACK` (như cũ). Chữ model chèn nguyên văn, không lọc (A5-9).
2. `manual = sections[SECTION_DECIDE]` khác rỗng → `ul = "<ul>" + "".join(f"<li>{escape_html(d)}</li>" for d in manual) + "</ul>"`, chèn vào mục "Hướng xử lý" của `text`:
   - `_plan_end(text) -> int | None` (riêng của `write_ticket.py`): tìm dòng tiêu đề đầu tiên khớp `^[ \t]*(\*\*)?Hướng xử lý:(\*\*)?` (re.M; cùng luật tiêu đề của `section_text`, `U4b.md:168`); không có → `None`. Có → trả chỉ số của ký tự `\n` đứng trước dòng kế tiếp sau dòng tiêu đề mà khớp `^[ \t]*(\*\*[^*\n]+:\*\*|Độ tin cậy:)`; không có dòng như vậy → `len(text)`.
   - `i = _plan_end(text)`; `None` → `text += "\n<p><strong>Hướng xử lý:</strong></p>" + ul` (đúng một tiêu đề do hệ thống thêm); ngược lại `text = text[:i] + "\n" + ul + text[i:]`.
3. Với `mục` lần lượt `SECTION_DONE`, `SECTION_PENDING`, chỉ khi khác rỗng: `"\n<p><strong>{mục}:</strong>" + (" " + PENDING_NOTE nếu mục là SECTION_PENDING) + "</p><ul>" + li thoát HTML một lần + "</ul>"` (`PENDING_NOTE` ở Điểm 2).
4. `content = GUIDANCE_MARKER + "\n" + text + các khối bước 3`; `counts = {mục: len(sections[mục]) for mục in GUIDANCE_SECTIONS}` (khóa nay là "Đã làm", "Chờ duyệt", "Hướng xử lý"; mục `post_guidance` của nhật ký, `w1.md:112`, đọc theo khóa mới).
5. Bước (1), (2), (4) của `w1.md:64` giữ nguyên; điều kiện "không có nội dung" tính trên cả ba khóa như cũ.

Ví dụ bắt buộc của test (stub `analysis = "**Nhận định:** A\n**Hướng xử lý:** B\nĐộ tin cậy: 90%"`, mỗi mục một dòng `L`, `D`, `P`):
```
<!-- erp_ai:huong-xu-ly -->
**Nhận định:** A
**Hướng xử lý:** B
<ul><li>L</li></ul>
Độ tin cậy: 90%
<p><strong>Đã làm:</strong></p><ul><li>D</li></ul>
<p><strong>Chờ duyệt:</strong> {PENDING_NOTE}</p><ul><li>P</li></ul>
```

**1.3 Chữ dự phòng (T103, thay `w1.md:37-38`).**
```python
GUIDANCE_FALLBACK = ("**Nhận định:** bot chưa viết được nhận định cho phiếu này.\n"
                     "**Hướng xử lý:** người phụ trách làm các việc ghi ngay dưới (nếu có); việc bot đã làm và đề xuất chờ duyệt nằm ở các mục cuối comment; cần bot làm tiếp thì nhắc @ai.")
```
Không chứa "Căn cứ", "Cần ai quyết"; dòng "Hướng xử lý" là dòng cuối nên dòng việc làm tay chèn ngay dưới nó (bước 2). Dùng khi `analysis` là `None`, như cũ (`w1.md:174`).

**1.4 Nhận định giữ trong lần đưa hướng không cần "Căn cứ" (T104, thay thứ tự (3)/(3c) của `w1.md:96`).** Thứ tự mới của `post_comment_tool`: (0) dấu hiệu; (1) `kind`; (2) dưới ngưỡng như cũ (câu hỏi vẫn cần "Căn cứ", không phải comment hướng); (3) `kind == "de_xuat"`: `CONFIDENCE_LINE` như cũ (AC-32 `[changed]` giữ "độ tin cậy", `spec-addendum-5.md:71`); (3b) như cũ; **(3c) `kind == "de_xuat"` ∧ `collecting(ctx.run_id)` → `hold_analysis`, trả `held`, 0 Comment, không kiểm `EVIDENCE_HEADER`**; **(3d) `kind == "de_xuat"` ngoài lần gom → `section_text(content, EVIDENCE_HEADER)` rỗng → `REASON_NO_EVIDENCE`** (AC-22 giữ nguyên chữ cho comment ngoài comment hướng, `spec-addendum-5.md:50`); (4), (5) như cũ. Căn cứ: nhận định giữ lại chính là thân comment hướng (`w1.md:66`); nếu còn đòi "Căn cứ" thì comment hướng buộc có mục đó, trái `spec-addendum-5.md:63`.

**1.5 Mô tả tool `post_comment` (T104, U4b-9 `w1.md:99`, thay câu `kind=de_xuat` của `U4b.md:182`).** Câu `kind=de_xuat` thành: "kind=de_xuat: nhận định và phương án, hoặc báo việc đã làm; phải có dòng 'Độ tin cậy: NN%'." Câu U4b-9 thành: "Không tự liệt kê việc đã làm, đề xuất đang chờ hay việc hệ thống từ chối: hệ thống tự thêm chúng vào comment. Khi phiếu đã có hướng xử lý: chỉ báo kết quả việc vừa làm." Câu `kind=hoi` và `kind=ba_note` giữ. Mô tả không còn chữ "Căn cứ" cho `de_xuat`, không còn "Cần ai quyết". Ngoài lần gom, model biết luật "Căn cứ" qua `REASON_NO_EVIDENCE` trong `tool_result` (`U4b.md:281`, như cũ). Đây là mô tả tool trong `write_ticket.py`, không phải chữ prompt của `prompts.py`; W1 đối chiếu chữ (F-3).

**1.6 Runner (T116).** Runner không dựng mục nào và không có `PENDING_LINE` (AD3-5 giữ). Thua lần chạy song song (`w1.md:105`): comment kết quả không dấu hiệu gồm các dòng của `collected` theo thứ tự `GUIDANCE_SECTIONS`, mỗi dòng một câu qua `post_routing_comment` như cũ, không tiêu đề mục nào.

### Dòng task thay thế

**T102** (chạm thêm, vì giá trị hằng do T102 đặt; tiêu đề, `files:`, `depends:`, Receives, Returns không đổi)
- Tiêu chí (thay `tasks.md:983`): `  - Tiêu chí: AC-65; ADR-036 QĐ 2, 3, 6; `w1.md:30-63`; bảng `AD3.md:126-129` (`collect` nhận chữ thô, cặp (mục, dòng) trùng thì bỏ qua); `design-w1-fixes-20.md` Điểm 1.1 thắng `w1.md:34-35` (`SECTION_DECIDE = GUIDANCE_HEADER`; chuỗi "Cần ai quyết" không có trong mã nguồn; AC-65 (a) `[changed]`, AC-66 `[changed]`, `spec-addendum-5.md:63-64`).`
- Expect (thay `tasks.md:986`): `  - Expect: `TestGuidanceWriter::test_count_ignores_info_other_owner_and_non_prefix`, `::test_marker_survives_save`, `TestCollector::test_collect_without_open_collector_is_noop`, `::test_bad_section_raises`, `::test_same_line_twice_kept_once`, `::test_later_hold_wins`, `::test_sections_are_done_pending_plan` (`GUIDANCE_SECTIONS == ("Đã làm", "Chờ duyệt", "Hướng xử lý")`, `SECTION_DECIDE == GUIDANCE_HEADER`, không giá trị nào là "Cần ai quyết") xanh.`

**T103** (tiêu đề, `files:`, `depends:` không đổi)
- Tiêu chí (thay `tasks.md:988`): `  - Tiêu chí: AC-65 (a) `[changed]`, (d); AC-66 `[changed]` (`spec-addendum-5.md:63-64`); ADR-036 QĐ 1, 4; `w1.md:54`, `:64` (bước (1), (2), (4)); AD3-4 (thoát HTML đúng một lần ở mọi chỗ đổ dòng gom); `design-w1-fixes-20.md` Điểm 1.2, 1.3 (thắng bước (3) của `w1.md:64` và `w1.md:37-38`), Điểm 2.1, Điểm 3.1.`
- Receives (thay `tasks.md:989`): `  - Receives: bộ gom, `count_guidance(lock=True)`, `SECTION_*`, `GUIDANCE_HEADER` (T102); `_post`, luật dòng tiêu đề của `section_text` (T100).`
- Returns (thay `tasks.md:990`): `  - Returns: `GUIDANCE_FALLBACK` (chữ Điểm 1.3), `PENDING_NOTE` (chữ Điểm 2.1), `FAILURE_DONE = "Trước khi lỗi, bot đã làm: "`, `FAILURE_PENDING = "Đề xuất đã tạo, đang chờ duyệt: "`, `FAILURE_MANUAL = "Việc người phải làm tay: "`, `REASON_GUIDANCE_EXISTS`; `_plan_end(text) -> int | None` (Điểm 1.2 bước 2); `post_guidance(ticket_name, run_id) -> dict` (`{"ok": True, "comment", "counts"}` hoặc `{"ok": False, "reason"}`), thân theo thứ tự Nhận định → Hướng xử lý (gồm dòng `SECTION_DECIDE`) → Đã làm → Chờ duyệt, mục rỗng không hiện; `failure_summary(run_id) -> str` (Điểm 3.1; không đang gom → `""`); không phải `ToolSpec`.`
- Expect (thay `tasks.md:991`): `  - Expect: `TestGuidanceWriter::test_writer_posts_once_second_call_refused`, `::test_concurrent_snapshot_does_not_double_post` (hai kết nối), `::test_deleted_guidance_allows_new_one`, `::test_no_analysis_no_items_posts_nothing`, `::test_no_analysis_with_done_items_uses_fallback`, `::test_collected_line_html_escaped_once` (giá trị `"<b>&x"` trong dòng `SECTION_DONE` và dòng `SECTION_DECIDE` → `&lt;b&gt;&amp;x` đúng một lần), `::test_body_order_analysis_plan_done_pending` (thân bằng từng byte ví dụ của Điểm 1.2), `::test_manual_lines_inside_plan_section` (subTest: "Hướng xử lý" là mục cuối; đứng trước `**Độ tin cậy:**`; đứng trước `**Nhận định:**`; không có tiêu đề → đúng 1 tiêu đề `<strong>Hướng xử lý:</strong>` do hệ thống thêm; chữ dự phòng → dòng nằm ngay sau dòng "Hướng xử lý" của nó; mọi ca: `<ul>` của dòng việc làm tay nằm sau tiêu đề "Hướng xử lý" và trước tiêu đề kế tiếp), `::test_no_evidence_or_decide_heading` (analysis có/không × mỗi mục rỗng/khác rỗng: danh sách tiêu đề không có "Căn cứ", "Cần ai quyết"; chuỗi "Cần ai quyết" không có trong thân; `GUIDANCE_FALLBACK`, `PENDING_NOTE` không chứa "Căn cứ", "Cần ai quyết"), `::test_pending_note_and_one_item_per_proposal` (2 dòng `SECTION_PENDING` → đúng 2 `<li>` sau `<strong>Chờ duyệt:</strong>`, `PENDING_NOTE` trong đoạn tiêu đề; mục rỗng → không có `PENDING_NOTE`), `::test_failure_summary_three_parts_escaped_once` (Điểm 3.1) xanh.`

**T104** (tiêu đề, `files:`, `depends:`, Receives không đổi)
- Tiêu chí (thay `tasks.md:993`): `  - Tiêu chí: AC-65 (a) `[changed]`, (c), (d), AC-23 `[changed]`, AC-66 (a); AC-22 giữ nguyên chữ ngoài comment hướng (`spec-addendum-5.md:50`); `w1.md:96` (U4b-6, bước (0), (3b)), `:98` (U4b-8), `:99` (U4b-9); `design-w1-fixes-20.md` Điểm 1.4 (thắng thứ tự (3)/(3c) của `w1.md:96`), Điểm 1.5 (thắng câu `kind=de_xuat` của `U4b.md:182` và chữ U4b-9).`
- Returns (thay `tasks.md:995`): `  - Returns: `REASON_MARKER`, `REASON_GUIDANCE_HEADER`, `HELD_NOTE`; thứ tự (0), (1), (2), (3) `CONFIDENCE_LINE`, (3b), (3c) đang gom ∧ `de_xuat` → giữ, không kiểm `EVIDENCE_HEADER`, (3d) ngoài lần gom ∧ `de_xuat` → kiểm `EVIDENCE_HEADER` như T100, (4), (5); kết quả giữ `{"ok": True, "held": True, "note": HELD_NOTE}`; mô tả tool `post_comment` theo Điểm 1.5; `FIELD_LABELS`, `ROUTE_DONE` (chữ ở `U4b.md:210`, `:215`) đặt ở `write_ticket.py`, không ở `runner.py` (runner import ở T109); `set_classification` thành công trong lần đưa hướng gọi `collect(run_id, SECTION_DONE, ...)`.`
- Expect (thay `tasks.md:996`): `  - Expect: `TestGuidanceWriter::test_post_comment_marker_refused_every_kind`, `::test_marker_case_and_spacing_variants_refused`, `::test_work_only_run_guidance_header_refused`, `::test_de_xuat_held_in_guidance_run`, `::test_set_classification_collects_done_line`, `::test_de_xuat_held_without_evidence_in_guidance_run` (nội dung có "Nhận định", "Hướng xử lý", "Độ tin cậy: 90%", không "Căn cứ" → `held`, 0 Comment, `collected` trả đúng nội dung), `::test_de_xuat_outside_guidance_run_still_needs_evidence` (cùng nội dung, không gom → `REASON_NO_EVIDENCE`, 0 Comment), `::test_held_needs_confidence` (đang gom, thiếu "Độ tin cậy" → `REASON_NO_CONFIDENCE`, không giữ), `::test_post_comment_schema_has_no_section_templates` (mô tả tool không chứa "Cần ai quyết"; câu `kind=de_xuat` không chứa "Căn cứ") xanh.`

**T116** (tiêu đề, `files:`, `depends:`, Receives không đổi)
- Tiêu chí (thay `tasks.md:1053`): `  - Tiêu chí: AC-65 (a) `[changed]`, (c), (d), AC-66 `[changed]`, AC-23 `[changed]` (`spec-addendum-5.md:63-64`, `:70`); ADR-036 QĐ 1, 8; `w1.md:105` (U4b-15), `:106` vế (a); AD3-2 (gọi ở mọi lối ra không lỗi: `not wants_tools`, `not tool_results`, `turn == max_turns`), AD3-4, AD3-5 (`runner.py` không có `PENDING_LINE`, không thêm dòng "Chờ duyệt"); `design-w1-fixes-20.md` Điểm 1.6 (runner không dựng mục; thân và thứ tự mục là của `post_guidance`, T103).`
- Returns (thay `tasks.md:1055`): giữ nguyên chữ hiện có, chèn sau cụm `thua lần chạy song song → 1 comment kết quả không dấu hiệu (dòng gom thoát HTML một lần)` đoạn: `: các dòng của `collected` theo thứ tự `GUIDANCE_SECTIONS`, mỗi dòng một câu, không tiêu đề mục nào`.
- Expect (thay `tasks.md:1056`): `  - Expect: `TestOneGuidance::test_last_turn_log_failure_leaves_no_guidance` (`write_entry` của lượt cuối ném lỗi → 0 comment hướng còn lại, `count_guidance` = 0; R5-16); `TestOneGuidance::test_chain_1_ticket_insert_one_guidance`, `::test_chain_2_insert_then_ai_three_times_one_guidance`, `::test_chain_7_ai_after_guidance_creates_task_no_new_guidance`, `::test_chain_8_level_l0_or_excluded_team_zero`, `::test_chain_9_empty_prompt_two_runs_one_guidance`, `::test_guidance_has_analysis_plan_done_pending` (thay `::test_guidance_has_analysis_done_pending_decide`: stub `de_xuat` theo mẫu Nhận định, Hướng xử lý, "Độ tin cậy", không "Căn cứ"; dòng 1 = dấu hiệu; danh sách tiêu đề = Nhận định, Hướng xử lý, Đã làm, Chờ duyệt; câu cảnh báo của `_route` nằm trong mục "Hướng xử lý"; không tiêu đề "Căn cứ", "Cần ai quyết"; mục rỗng không hiện), `::test_marker_refusal_one_failed_action_entry`, `::test_max_turns_exit_still_posts_guidance`, `::test_lost_race_posts_result_comment_escaped_once` (thêm: comment không có `<strong>` tiêu đề mục nào); `TestAskOnly::test_stub_69_70_100` (ca 70, 100: comment hướng có câu định tuyến); `TestRunNotices::test_matrix_eight_situations` (sửa theo `w1.md:187`) xanh.`

---

## Điểm 2 — Dòng "Chờ duyệt" và lời trỏ tới nút "Duyệt ngay" (T103 phần tiêu đề mục, T105)

### Phán quyết

**2.1 Lời trỏ nằm ở đoạn tiêu đề mục, một lần mỗi comment (T103).**
```python
PENDING_NOTE = 'Nút "Duyệt ngay" nằm ở ngăn "Trao đổi với bot" của phiếu; đề xuất không có nút thì duyệt ở form đề xuất.'
```
Chèn nguyên văn (hằng tin cậy, không `<`, `&`) ngay sau `<strong>Chờ duyệt:</strong>`, trong `<p>`, không phải `<li>`. Lý do:
- `spec-addendum-5.md:63`: mục "nói nút "Duyệt ngay" nằm ở ngăn "Trao đổi với bot" của phiếu" và "có đúng 1 dòng cho mỗi đề xuất vừa tạo". Lời trỏ là `<li>` thì số dòng sai; lời trỏ lặp ở mỗi dòng thì sai cho đề xuất code.
- `spec-addendum-5.md:79` (AC-39 (3)): đề xuất sửa code và lệnh `bench` không có nút trong ngăn, duyệt ở form Desk. Đợt 1 (U4b) chỉ có hai loại này, nên câu phải nói đúng cho cả khi mục toàn đề xuất code: vế sau của `PENDING_NOTE` nói điều đó.
- Tên ngăn lấy từ mã: `agent_status_indicator.js:4`, `:8`.
- Một hằng, một chỗ (`write_ticket.py`); `propose_change.py` không định nghĩa lại.

**2.2 Dòng của đề xuất code và lệnh (T105, thay chữ `PENDING_LINE` của `w1.md:106` và `tasks.md:1000`).**
```python
PENDING_LINE = "Đề xuất {proposal} ({label}): duyệt ở form đề xuất, không có nút Duyệt ngay."
```
Chữ cũ "đang chờ duyệt trong ngăn của bot" trái AC-39 (3). `{label}` giữ nhãn cố định theo `change_kind` (`AD3.md:130`), không chép tham số (B-3), chữ thô (thoát ở T103). Không dấu `"` trong dòng để test so được chữ sau `escape_html` mà không phụ thuộc cách thoát dấu nháy. Dòng của đề xuất loại bản ghi (có nút "Duyệt ngay" trong ngăn) là của U7a (`AD3.md:130`), không phán ở đây; nó không được nói ngược `PENDING_NOTE`.

**Ghi chú thời điểm.** Từ khi T103 merge tới khi U7b vào `develop`, `PENDING_NOTE` nói tới một nút chưa dựng. FEAT-007 chỉ cổng G5, không deploy giữa chừng; AC-39, AC-69 nghiệm thu giao diện sau khi U7a, U7b vào `develop` cùng lượt (`spec-addendum-5.md:166`). Cùng cách chấp nhận với A-W1-4 (`w1.md:85`).

### Dòng task thay thế

**T105** (tiêu đề, `files:`, `depends: T102, T99, T126`, Receives không đổi)
- Tiêu chí (thay `tasks.md:998`): `  - Tiêu chí: AC-65 (a) `[changed]` (`spec-addendum-5.md:63`: mỗi đề xuất một dòng), AC-39 `[changed]` đoạn (3) (`spec-addendum-5.md:79`: đề xuất sửa code và lệnh `bench` duyệt ở form, không có nút trong ngăn), AC-67 (phần đợt 1); AD3-5, AD3-11; bảng `AD3.md:130-131`; `design-w1-fixes-20.md` Điểm 2.2 (thắng chữ `PENDING_LINE` của `w1.md:106`); lời trỏ chung tới nút "Duyệt ngay" là `PENDING_NOTE` của T103 (Điểm 2.1), không ở file này.`
- Returns (thay `tasks.md:1000`): `  - Returns: `PENDING_LINE = "Đề xuất {proposal} ({label}): duyệt ở form đề xuất, không có nút Duyệt ngay."`; `pending_line(proposal) -> str` (chữ thô, nhãn cố định theo `change_kind`, không chép tham số; loại code và lệnh; loại bản ghi là của U7a); `_insert` gọi `collect(ctx.run_id, SECTION_PENDING, pending_line(doc))` khi `collecting(ctx.run_id)`. Luật: tên `SECTION_PENDING` chỉ có ở `write_ticket.py` và `propose_change.py` (ngoài test). Không định nghĩa `PENDING_NOTE` ở file này.`
- Expect (thay `tasks.md:1001`): `  - Expect: `TestPendingLine::test_insert_in_guidance_run_collects_one_line`, `::test_insert_outside_guidance_run_collects_nothing`, `::test_line_has_fixed_label_no_arguments`, `::test_code_and_command_lines_point_to_form` (đề xuất code và đề xuất lệnh: dòng = `PENDING_LINE.format(...)` đúng nhãn từng loại, chứa "form đề xuất", không chứa "ngăn"); `test_architecture.py::test_section_pending_only_in_writer_and_proposal_module` xanh. Chèn 6, ca CI-2 (`arch-impact-chg-002.md:91`): khối 3 mục (sửa, tạo trong thư mục mới, đổi tên) + `migrate`, `restart` trong lần đưa hướng → đúng 1 dòng `SECTION_PENDING`, không chứa đường dẫn hay argv; khối bị từ chối → 0 dòng.`

---

## Điểm 3 — Chữ việc đã làm khi lỗi sau định tuyến; phép kiểm đầu-cuối hai tiêu đề (T117, T118)

### Phán quyết

**3.1 Thông báo lỗi tách ba loại dòng (T103 đặt hàm, T117 gọi).** Chữ cũ (`w1.md:70`, `:104`) nối dòng của cả ba khóa sau "Trước khi lỗi, bot đã làm:", nên đề xuất đang chờ và việc người phải làm tay bị gọi là "đã làm". Phán:
```python
def failure_summary(run_id: str) -> str:   # write_ticket.py (T103)
    # không đang gom → "". Ngược lại, theo thứ tự (FAILURE_DONE, SECTION_DONE), (FAILURE_PENDING, SECTION_PENDING),
    # (FAILURE_MANUAL, SECTION_DECIDE): mỗi khóa khác rỗng cho một phần = tiền tố + "; ".join(escape_html(d) for d in dòng);
    # trả "\n".join(các phần).
```
`_done_suffix(run_id)` (runner, T117) = `"\n" + s` với `s = write_ticket.failure_summary(run_id)` khác rỗng, ngược lại `""`. Hàm đặt ở `write_ticket.py` vì: AD3-5 cấm tên `SECTION_PENDING` trong `runner.py` (`AD3.md:172`); AD3-4 đòi thoát một lần ở chỗ đổ dòng (`AD3.md:171`); T103 đã là chỗ dựng chữ từ bộ gom. Tiền tố `FAILURE_DONE` giữ đúng chuỗi "Trước khi lỗi, bot đã làm: " nên chuỗi 5 (`w1.md:168`) không đổi. Thông báo lỗi không mang dấu hiệu, không có tiêu đề mục, nên lần chạy lại vẫn được đưa hướng (AC-65 (b) giữ). Chống trùng → logger `dropped=<n>` với `n = sum(len(v) for v in collected(run_id)[1].values())`.

**3.2 Đếm comment trong phép kiểm đầu-cuối (T118).** Theo `spec-addendum-5.md:70` điều (1) và `ADR-038.md:29`: "comment kết quả" là `Comment` `comment_type = "Info"` có `content` (sau khi bỏ thẻ HTML ở đầu, nếu có) mở đầu bằng `kết quả đề xuất {name}` (tiền tố thật: `result_comment.py:85`). Không đếm theo "chứa tên đề xuất". Dòng báo trước restart (`post_restart_notice`, CHG-002) đếm riêng, không vào số comment kết quả; `count_guidance` không đổi sau dòng báo (`ADR-038.md:39`).

**3.3 Hai tiêu đề.** Test dùng helper trong file test `_headings(content) -> list[str]` = các tên khớp `(?m)^[ \t]*\*\*([^*\n]+):\*\*` hoặc `<strong>([^<]+):</strong>`, theo thứ tự xuất hiện. Stub model viết đúng mẫu của prompt dựng ra (`spec-addendum-5.md:63` cột kiểm): Nhận định, Hướng xử lý, dòng "Độ tin cậy", không "Căn cứ" (chữ mẫu do W1 chốt, F-3). Việc người làm tay kèm lý do ở đợt 1 lấy từ đường có thật: `ASSIGN_REQUEST` khi bật tự gán mà không có người hợp lệ (`route_ticket.py:21`, `:25`; T115 nối vào `SECTION_DECIDE`). Từ chối của bộ thực thi, môi trường `production`, danh mục (AC-23 (d), AC-66 ca "bộ thực thi từ chối") có người sinh dòng ở đợt 2 (`design-addendum-3-w2.md:110-111`, `:154`), kiểm ở đó (F-2).

### Dòng task thay thế

**T117** (tiêu đề, `files:`, `depends:` không đổi)
- Tiêu chí (thay `tasks.md:1058`): `  - Tiêu chí: AC-65 (b), AC-23; `w1.md:70`, `:104` (U4b-14); AD3-4, AD3-5; A-W1-3; `design-w1-fixes-20.md` Điểm 3.1 (thắng câu nối ba mục sau "Trước khi lỗi, bot đã làm" của `w1.md:70`, `:104`).`
- Receives (thay `tasks.md:1059`): `  - Receives: bộ gom, `failure_summary` (T103); `_notice` `run_failed` (T110).`
- Returns (thay `tasks.md:1060`): `  - Returns: `_done_suffix(run_id) -> str` = `"\n" + write_ticket.failure_summary(run_id)` khi khác rỗng, ngược lại `""` (chữ và thoát HTML ở T103; runner không thoát lại, không nối dòng gom, không có tên `SECTION_PENDING`); thông báo bị chống trùng → logger `dropped=<n>`, `n` = tổng số dòng của bộ gom.`
- Expect (thay `tasks.md:1061`): `  - Expect: `TestOneGuidance::test_chain_5_failed_run_then_rerun_one_guidance`, `TestRunNotices::test_reason_error_after_route_lines_in_failure_notice`, `::test_failure_suffix_html_escaped_once`, `::test_failure_notice_names_done_pending_manual_apart` (câu định tuyến sau `FAILURE_DONE`; 1 đề xuất code tạo ở lượt trước lỗi sau `FAILURE_PENDING`; `ASSIGN_REQUEST` sau `FAILURE_MANUAL`; thông báo không có dấu hiệu, không có chuỗi "Cần ai quyết"; `count_guidance` = 0) xanh.`

**T118** (tiêu đề, `files:`, `depends:` không đổi; vẫn chỉ thêm test, đỏ → `DESIGN_CONFLICT`)
- Tiêu chí (thay `tasks.md:1063`): `  - Tiêu chí: AC-66 (a), AC-66 `[changed]`, AC-65 chuỗi 4 và 6, AC-65 (a) `[changed]`, AC-32 `[changed]` (L1 không có tiêu đề "Căn cứ"), AC-23 `[changed]` ca thêm và điều (1) (`spec-addendum-5.md:63-64`, `:70-71`); ADR-038 QĐ 3 và Ràng buộc (`ADR-038.md:29`, `:37`, `:39`); `w1.md:167`, `:169`, `:186`, `:196-198`; `design-w1-fixes-20.md` Điểm 3.2, 3.3. Task chỉ thêm test trên mã đã merge; test nào đỏ → trả `DESIGN_CONFLICT` kèm tên test và đầu ra, không sửa mã nguồn, không đổi assertion.`
- Receives (thay `tasks.md:1064`): `  - Receives: T103, T104, T105, T116, T117; tiền tố dòng kết quả `kết quả đề xuất {name}` (`result_comment.py:85`); `post_restart_notice` của CHG-002 (vào nhánh qua T126).`
- Returns (thay `tasks.md:1065`): `  - Returns: tám test mới, không mã nguồn; helper trong file test `_headings(content)` (Điểm 3.3) và `_result_lines(ticket, proposal)` (đếm `Info` có `content`, sau khi bỏ thẻ HTML ở đầu, mở đầu bằng `kết quả đề xuất {proposal}`).`
- Expect (thay `tasks.md:1066`): `  - Expect: `TestOneGuidance::test_chain_4_sweep_after_success_one_guidance`, `::test_chain_6_guidance_then_approve_one_guidance_one_result` (đề xuất không có `restart`: `_result_lines` = 1, 0 dòng báo, `count_guidance` = 1), `::test_chain_6_restart_block_one_result_line_one_notice` (khối có `.py`, `migrate`, `restart`, stub khởi chạy: `_result_lines` = 1; đúng 1 `Info` khác không mở đầu bằng `kết quả đề xuất`, `creation` không sau dòng kết quả; `count_guidance` vẫn 1; 0 job agent mới), `::test_guidance_comment_sections_e2e_no_evidence_no_decide` (L2, ghi trường, bật tự gán không người hợp lệ, 1 đề xuất code: `_headings` = Nhận định, Hướng xử lý, Đã làm, Chờ duyệt; `escape_html(ASSIGN_REQUEST…)` nằm sau tiêu đề "Hướng xử lý" và trước `<strong>Đã làm:</strong>`; mục Chờ duyệt có `PENDING_NOTE` và đúng 1 `<li>` = `escape_html(pending_line(doc))`; chuỗi "Cần ai quyết" không có; 0 `Info`); `TestRunNotices::test_guidance_run_fields_assign_task_proposal_one_routing_comment`; `TestDoneInGuidance::test_l1_ticket_only_ticket_fields_and_task` (thêm: `_headings` không có "Căn cứ"), `::test_item_not_in_both_done_and_pending`, `::test_ok_comment_does_not_approve_pending_proposal` xanh.`

---

## Task không đổi

| Task | Vì sao không đổi |
|---|---|
| T100 | Hằng `EVIDENCE_HEADER`, `REASON_NO_EVIDENCE` và kiểm (3) cho `de_xuat` ngoài lần gom giữ (AC-22, `spec-addendum-5.md:50`); T104 đổi thứ tự trong lần gom và câu mô tả tool (Điểm 1.4, 1.5) |
| T101 | `post_notice` không chạm mục nào |
| T115 | Vẫn gọi `collect(SECTION_DONE, …)`, `collect(SECTION_DECIDE, …)` bằng tên; chỉ giá trị hằng đổi (Điểm 1.1). Chữ "Cần ai quyết" ở `w1.md:189` đọc là `SECTION_DECIDE` |
| T106, T107, T156, T170 | Không dựng comment hướng (chữ prompt thuộc W1) |

## Giả định kỹ thuật do designer quyết

- A-20-1: giữ tên `SECTION_DECIDE`, đổi giá trị thành `GUIDANCE_HEADER`, để không sửa lời gọi ở T115 và đợt 2.
- A-20-2: dòng việc làm tay chèn ở cuối mục "Hướng xử lý" của chữ model theo luật dòng tiêu đề của `section_text`, thêm dòng "Độ tin cậy:" là điểm dừng; không có tiêu đề thì hệ thống thêm đúng một tiêu đề.
- A-20-3: lời trỏ "Duyệt ngay" là một câu cố định ở đoạn tiêu đề mục "Chờ duyệt", đúng cho cả đề xuất có nút lẫn không có nút.
- A-20-4: trong lần gom, `de_xuat` không cần "Căn cứ" nhưng vẫn cần "Độ tin cậy".

## Cần người khác xem (không phán ở đây)

- **F-1 (architect):** `ADR-036.md:37` QĐ 2 còn ghi "Hàm ghi dựng các mục "Đã làm", "Chờ duyệt", "Cần ai quyết"". File này không đổi quyết định (một bộ gom, một hàm ghi, model viết nhận định); chỉ dòng của khóa thứ ba hiện trong "Hướng xử lý" theo `spec-addendum-5.md:63-64`. `spec-addendum-5.md:193` ghi ADR-036 "không bị chạm"; cần architect sửa chữ danh sách mục của QĐ 2 (không phải quyết định mới) trước khi T103 merge.
- **F-2 (designer đợt 2, tech-lead):** `design-addendum-3-w2.md:154` ("ghi ở 'Cần ai quyết'") và T-19, T-23 của file đó đọc theo Điểm 1.1: vẫn `SECTION_DECIDE`, hiện trong "Hướng xử lý". Ca AC-23 (d) (`production`) và AC-66 "bộ thực thi từ chối" chạy đầu-cuối ở đó.
- **F-3 (W1, `design-w1-fixes-19.md`):** mẫu VIẾT COMMENT nên giữ dòng `Độ tin cậy: NN%` khớp `CONFIDENCE_LINE` (`U4b.md:127`), nếu không nhận định bị từ chối ở bước (3) và comment rơi về chữ dự phòng; giữ dạng tiêu đề `**Nhận định:**`, `**Hướng xử lý:**` để Điểm 1.2 chèn đúng chỗ (lệch dạng thì hệ thống vẫn thêm tiêu đề của mình, AC vẫn đạt). Đối chiếu câu mô tả tool `post_comment` (Điểm 1.5) với chữ prompt.
- **F-4 (team-leader, Q-18):** ngoài lần gom, `de_xuat` vẫn đòi "Căn cứ" (AC-22 giữ) trong khi prompt mới không còn mẫu đó; model học luật qua `REASON_NO_EVIDENCE` (thêm một lượt). Không đổi ở đây.

## Đối chiếu AC (phần của lượt này)

- AC đổi của `spec-addendum-5.md` mục 3.1, 3.2 chạm U4b: AC-65 (a), AC-66, AC-23, AC-32.
- Test của lượt: AC-65 (a) → T103 `test_body_order_analysis_plan_done_pending`, `test_no_evidence_or_decide_heading`, `test_pending_note_and_one_item_per_proposal`; T116 `test_guidance_has_analysis_plan_done_pending`; T118 `test_guidance_comment_sections_e2e_no_evidence_no_decide`. AC-66 → T103 `test_manual_lines_inside_plan_section`; T118 cùng test e2e (dòng `ASSIGN_REQUEST`). AC-23 điều (1) → T118 `test_chain_6_guidance_then_approve_one_guidance_one_result`, `test_chain_6_restart_block_one_result_line_one_notice`; AC-23 điều (2) → T103, T118 như AC-66. AC-32 → T118 `test_l1_ticket_only_ticket_fields_and_task`. AC-22 giữ → T104 `test_de_xuat_outside_guidance_run_still_needs_evidence`.
- Ngoài lượt: AC-38, AC-48 (prompt, T157), AC-39, AC-69 (U7b), AC-23 (d) (đợt 2, F-2).
