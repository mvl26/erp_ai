# FEAT-007 — design-w1-fixes-19: chữ prompt theo `spec-addendum-5.md` (comment của bot bỏ "Căn cứ" và "Cần ai quyết"), lượt W1

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `spec-addendum-5.md` mục 2 (`:39-46`), 3.1 (`:63-64`), 3.2 (`:71-73`), mục 5 (A5-1, A5-4, A5-9, A5-10, `:90-99`), mục 7 (`:168`, `:185-187`, `:192`); `tasks.md` khối T72 (`:789-794`), T78 (`:827-832`), T79 (`:833-838`), T176 (`:839-840`), T82 (`:857`), T87 (`:903`), T106 (`:1002-1006`), T107 (`:1007-1011`), T156 (`:1244-1248`), T157 (`:1249-1253`), T170 (`:1317-1321`); `design-addendum-1-U6b.md:294-295`; `design-addendum-3-w1.md:80`, `:100`; `design-w1-fixes-7.md:81-113`; ADR-036 QĐ 2 (`docs/team/adr/ADR-036.md:37`).
- Mã đọc (chỉ đọc, đường dẫn tuyệt đối, không cd): worktree `.claude/worktrees/feat-007` ở `c7002de`. `git -C … diff --stat 05237bb..HEAD -- erp_ai/agent/prompts.py erp_ai/agent/test_prompts.py erp_ai/agent/test_classification.py erp_ai/erp_ai_agent/doctype/erp_ai_setting/` → rỗng: số dòng của spec (trích ở `05237bb`) vẫn đúng.
- Kiến trúc giữ: ADR-036 QĐ 1-2 (một hàm ghi, bộ gom theo lần chạy dựng các mục hệ thống tự thêm; phần nhận định do model viết), ADR-030 QĐ 3 (prompt theo kết quả cấp), ADR-038 (chữ AC-23, không chạm ở lượt này). Không đổi hàm ghi comment của U4b (T103–T118, lượt W2, `design-w1-fixes-20.md`), không đổi ngăn U7b.
- `team.py claim` không chạy: lời giao chỉ cho ghi đúng file này.

---

## Dò mã: mọi chỗ có "Căn cứ", "Cần ai quyết" trong `erp_ai/` (worktree)

Lệnh: `grep -rn "Căn cứ\|Cần ai quyết" erp_ai` (mọi đuôi file), thêm `grep -rln "prompt_override" erp_ai`.

| Chỗ | Nội dung | Thuộc | Phán |
|---|---|---|---|
| `erp_ai/agent/prompts.py:134` | `**Căn cứ:** bản ghi hoặc dòng code cụ thể đã xem (ghi rõ file và số dòng).` | VIẾT COMMENT (T79) | bỏ, Điểm 1 |
| `erp_ai/agent/prompts.py:136` | `… bot tự thêm các mục "Đã làm", "Chờ duyệt", "Cần ai quyết" …` | VIẾT COMMENT (T79) | viết lại, Điểm 1 |
| `erp_ai/agent/prompts.py:257` | `… thay cho quy tắc 6 và cho mục "Cần ai quyết" của comment:` | `ACT_NOW_BLOCK` (FEAT-004, T79 giữ) | viết lại, Điểm 1 |
| `erp_ai/agent/prompts.py:270-271` | `- Chỉ ghi "Cần ai quyết" khi tool trả ok=false …` | `ACT_NOW_BLOCK` | viết lại, Điểm 1 |
| `erp_ai/agent/prompts.py:111` | `… chờ người bấm Duyệt trong ngăn của bot.` (không có hai mục; tên nút cũ) | `RULE_6_ACT` (T78) | đổi tên nút và tên ngăn, Điểm 1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:129` | `"reasoning": ("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**")` | T72/T79 | bỏ `**Căn cứ:**`, Điểm 2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:666` | mô tả `prompt_override_reasoning` (306 ký tự) nêu `**Căn cứ:**` và "Cần ai quyết" | T79 | thay nguyên văn, Điểm 2 |
| `erp_ai/agent/test_prompts.py:55`, `:57` | trong `OLD_CORE_PROMPT` (bản trước FEAT-007, mốc lịch sử) | T78 | **giữ**, mục STD-TEST-5 |
| `erp_ai/agent/test_prompts.py:74-79`, `:146` | `OLD_WRITING_LINES`, `U1_5_WRITING_LINES`, `assertNotIn("**Cần ai quyết:**", …)` | T79 | sửa |
| `erp_ai/agent/test_classification.py:505` | cụm `"Cần ai quyết"` phải có trong `ACT_NOW_BLOCK` | T79 | sửa |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2345` | `PROMPT_PARTS["reasoning"]` ba mục | T79 | sửa |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2636` | ghi đè cũ có `**Cần ai quyết:**` lưu được | T79 | **giữ**, mục STD-TEST-5 |
| `prompt_override` ngoài `doctype/erp_ai_setting/` | chỉ `erp_ai/tests/test_doctype_descriptions.py` | — | ghi đè `reasoning` chưa được mã nào đọc khi dựng prompt |

Không có chỗ nào khác (`.js`, `.json` khác, dữ liệu eval, stub model trong test runner: 0 dòng). `CHANGE_TOOLS_BLOCK`, `SITE_ADMIN_TOOLS_BLOCK`, `UNRESTRICTED_TOOLS_BLOCK`, `ASK_ONLY_BLOCK`, `CATEGORY_TABLE`, `CONVENTIONS`: 0 lần hai chữ đó.

---

## Điểm 1 — chữ mới của VIẾT COMMENT, quy tắc 6, `ACT_NOW_BLOCK` (AC-65 (a), AC-66, AC-32, AC-23 (2) phần prompt) — SỬA

**Căn cứ.** AC-65 (a) `[changed]` (`spec-addendum-5.md:63`): comment có nhận định; hướng xử lý là phương án (việc bot sẽ làm khi người bấm "Duyệt ngay", việc người làm tay kèm lý do); "Đã làm", "Chờ duyệt"; prompt ở mọi tổ hợp công tắc không có mẫu "Căn cứ", "Cần ai quyết". AC-66 `[changed]` (`:64`): việc bộ thực thi từ chối ghi trong "Hướng xử lý" như việc người làm tay kèm lý do; câu của prompt cho model ghi "Cần ai quyết" (`prompts.py:257-270`) không còn. AC-32 `[changed]` (`:71`): ở L1 comment không có "Căn cứ". AC-48 `[changed]` (`:73`): nguồn nêu ngay trong nhận định hoặc hướng xử lý. A5-10 (`:99`): bot chọn một phương án và nêu phương án kia trong "Hướng xử lý". ADR-036 QĐ 2: việc bị từ chối là dòng của bộ gom, hàm ghi dựng các mục hệ thống thêm; nên prompt vẫn bảo model không tự liệt kê chúng (chia việc như U1-5 đã merge, `design-addendum-3-w1.md:80`), chỉ đổi nơi chúng nằm.

### 1.1 `_CORE_WRITING` (`prompts.py:129-142`) — thay cả hằng bằng

```python
_CORE_WRITING = """VIẾT COMMENT

Tiếng Việt, giọng đồng nghiệp, không trang trọng quá. Ngắn. Cấu trúc:

**Nhận định:** nguyên nhân, một hai câu; nêu luôn bản ghi, dòng code (file và số dòng) hoặc nguồn tra cứu đã dựa vào.
**Hướng xử lý:** phương án của bot: các bước bot sẽ làm sau khi người bấm "Duyệt ngay" (nếu có đề xuất) và các bước người phải làm tay, kèm lý do. Cần người chọn giữa hai cách thì chọn một cách, nêu cách kia ngay trong mục này.
Không tự liệt kê việc đã làm, đề xuất đang chờ hay đề xuất tool không tạo được: bot tự thêm các mục "Đã làm", "Chờ duyệt" và tự ghi đề xuất không tạo được vào "Hướng xử lý" như việc người phải làm tay, kèm lý do.

Không dùng bullet khi chỉ có một điểm. Không nhắc lại nội dung phiếu —
người đọc vừa viết nó. Không xin lỗi, không rào trước.

Khi không chắc, nói không chắc và nói cần gì để chắc. Một chẩn đoán sai mà
viết tự tin thì tệ hơn việc nói "chưa đủ dữ kiện, cần xem thêm X"."""
```

Khác bản T79 đúng ba dòng giữa "Cấu trúc:" và dòng trống: dòng `**Nhận định:**` thêm vế nêu bản ghi/nguồn (chỗ của "Căn cứ" cũ, AC-48); dòng `**Căn cứ:**` bỏ; dòng `**Hướng xử lý:**` và dòng "Không tự liệt kê …" viết lại. Mọi dòng khác giữ từng byte. Chỉ dùng ngoặc kép ASCII, không gạch `–` (RUF001); gạch `—` ở dòng "Không nhắc lại nội dung phiếu —" là chữ cũ, giữ.

### 1.2 `RULE_6_ACT` (`prompts.py:108-112`) — thay bằng

```python
RULE_6_ACT = (
	"6. Việc ghi trên phiếu (điền trường phân loại còn trống, gán người, tạo Task) mà bạn có tool thì làm"
	" luôn, không hỏi. Việc ghi ngoài phiếu chỉ làm qua tool được cấp; tool nào tạo đề xuất thì việc đó chờ"
	' người bấm "Duyệt ngay" trong ngăn "Trao đổi với bot" của phiếu.'
)
```

Một dòng (không `\n`), vẫn bắt đầu `6. `; câu neo P-9 `Việc ghi ngoài phiếu chỉ làm qua tool được cấp` giữ. Tên ngăn lấy đúng chữ đang chạy ở `erp_ai/public/js/agent_status_indicator.js:4,8`. Vì: AC-39 `[changed]` (nút "Duyệt ngay"), AC-65 (a) ("Chờ duyệt" trỏ nút ở ngăn "Trao đổi với bot"); model thấy "Duyệt" cũ thì sẽ viết tên nút cũ vào "Hướng xử lý". Đề xuất code và lệnh `bench` vẫn theo `CHANGE_TOOLS_BLOCK` (thay quy tắc 6, duyệt ở form; A5-8), không đổi.

### 1.3 `ACT_NOW_BLOCK` (`prompts.py:254-271`) — thay hai chỗ, mọi dòng khác giữ từng byte

Dòng `:257`:
```text
các quy tắc dưới đây thay cho quy tắc 6:
```
Hai dòng `:270-271` thay bằng:
```text
- Việc nằm ngoài các tool bạn có thì ghi trong "Hướng xử lý" là việc người phải làm
  tay, kèm lý do. Tool trả ok=false thì không thử đường khác.
```
Không viết "không hỏi lại" ở câu mới: khi `act_now` và `ask_only` cùng bật, khối `ASK_ONLY_BLOCK` đứng sau (`test_each_block_present_iff_its_flag`) và câu mới không được trái nó. Không viết "nêu lý do tool trả về" cho mọi tool: lý do từ chối của tool tạo đề xuất do bot ghi (1.1); lý do `ok=false` của tool bản ghi vẫn theo câu đang có của `SITE_ADMIN_TOOLS_BLOCK` và `UNRESTRICTED_TOOLS_BLOCK` ("Tool trả ok=false thì nêu đúng lý do trong comment", chữ FEAT-004, giữ). Hai câu đó không trái câu mới. Dòng `:262-264` (nút Duyệt / Từ chối trong comment đề xuất code, FEAT-004) giữ.

### 1.4 `PROMPT_CONFLICT_PAIRS` (`prompts.py:281-299`) — thêm hai cặp cuối (AC-65 (a): "thêm vào danh sách cặp câu của AC-6")

```python
	# P-10, P-11 (spec-addendum-5 AC-65 (a)): the retired headings of the old VIẾT COMMENT against the new direction line
	("**Căn cứ:**", "**Hướng xử lý:** phương án của bot"),
	("**Cần ai quyết:**", "**Hướng xử lý:** phương án của bot"),
```
Đứng sau P-9, nên chỉ số `[5]` (P-7) mà `test_every_allowed_sentence_is_in_the_core_or_a_block` dùng không đổi. Hai câu cấm có trong `OLD_CORE_PROMPT` (`test_prompts.py:55`, `:57`), câu cho phép không có ở đó và có trong lõi ở mọi tổ hợp.

### 1.5 Giao diện với lượt W2 (`design-w1-fixes-20.md`, không thiết kế ở đây)

Câu cuối của 1.1 nói hệ thống ghi "đề xuất tool không tạo được" vào "Hướng xử lý". Điều kiện để câu đó đúng: hàm ghi của U4b đặt các dòng từ chối mà bộ gom nhận (ADR-036 QĐ 2; hôm nay là `SECTION_DECIDE`, `design-addendum-3-w1.md:34`, `design-addendum-3-w2.md:154`) dưới "Hướng xử lý", như việc người làm tay kèm lý do (AC-66 `[changed]`, AC-23 (2)). Nếu W2 phán ngược lại (model tự viết dòng từ chối), dòng "Không tự liệt kê …" của 1.1 thay bằng biến thể B, nguyên văn:
```text
Không tự liệt kê việc đã làm hay đề xuất đang chờ: bot tự thêm các mục "Đã làm", "Chờ duyệt". Đề xuất tool không tạo được (ok=false) thì ghi trong "Hướng xử lý" là việc người phải làm tay, kèm lý do tool trả về.
```
Biến thể nào cũng qua mọi phép kiểm của T181 trừ hằng ghim `A5_WRITING_LINES` (chép theo biến thể được chọn). Mặc định: biến thể A (1.1). Tech-lead đối chiếu `design-w1-fixes-20.md` trước khi giao T181.

---

## Điểm 2 — mục bắt buộc phần lập luận (AC-38) và ghi đè đã lưu còn `**Căn cứ:**` — SỬA

**Căn cứ.** AC-38 `[changed]` (`spec-addendum-5.md:72`): mục bắt buộc là "Nhận định" và "Hướng xử lý"; "Căn cứ" không bắt buộc, không có trong bản dựng sẵn; ghi đè cũ có "Căn cứ" vẫn lưu lại được; hệ thống không lọc chữ model (A5-9). Phép kiểm là `marker in text` (`erp_ai_setting.py:481-485`).

1. `erp_ai_setting.py:129` → `"reasoning": ("**Nhận định:**", "**Hướng xử lý:**"),`. Chú thích `:112-113` giữ.
2. `erp_ai_setting.json:666`, `description` của `prompt_override_reasoning`, thay nguyên văn (369 ký tự, ≤ 400; có đủ bốn cụm `Để trống`, `bắt buộc`, `20000`, `không bị ghi đè` của `test_doctype_descriptions.py:194`; có hai mục bắt buộc; không có `**Căn cứ:**`, `**Cần ai quyết:**`), `"modified"` của DocType tăng:
   ```text
   Để trống = dùng bản dựng sẵn. Nội dung thay phần chỉ dẫn lập luận; phải có các mục bắt buộc **Nhận định:**, **Hướng xử lý:** và ≤ 20000 ký tự. Các mục Đã làm, Chờ duyệt do bot tự thêm. Mục Căn cứ, Cần ai quyết đã bỏ: ghi đè cũ còn chúng vẫn lưu được và bot viết theo ghi đè. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt.
   ```
   Câu "Mục Căn cứ, Cần ai quyết đã bỏ …" là chỗ duy nhất báo cho người quản trị có ghi đè cũ (cùng lối `design-w1-fixes-7.md:97`, A5-9).
3. **Ghi đè `reasoning` đã lưu trên site:** không patch, không sửa, không xóa; không bước đối soát, không bộ lọc. Lý do: tập mục mới (2) nằm trong tập cũ (3), nên mọi giá trị đã qua phép kiểm cũ vẫn qua phép kiểm mới và lưu lại được; giá trị là chữ của người (A5-9). Hệ quả đã biết, ghi As-Built: ghi đè cũ còn mẫu "Căn cứ" thì bot viết theo khi ghi đè được dùng. Hôm nay không mã nào đọc `prompt_override_reasoning` để dựng prompt (bảng dò mã), nên hệ quả chỉ có khi phần nối ghi đè vào prompt được dựng.
4. Prompt và phép kiểm đổi **cùng commit**: bỏ `**Căn cứ:**` khỏi `_CORE_WRITING` mà phép kiểm còn ba mục thì `test_builtin_prompts_pass_required_markers` đỏ (bản dựng sẵn trượt phép kiểm của chính nó), như C-4 của T72 và Điểm 3 của `design-w1-fixes-7.md`.

---

## Điểm 3 — T157 (AC-48) và T106, T107, T156, T170 — T157 SỬA, bốn task kia KHÔNG CHẠM

### 3.1 Chữ `KNOWLEDGE_SOURCES_BLOCK` (thắng câu thứ hai của `design-addendum-1-U6b.md:294`)

```text
Ba nguồn tra trước khi kết luận: bài CSKT (search_knowledge_base), HDSD (search_manuals), phiếu cũ (search_resolved_tickets). Nêu nguồn đã dùng ngay trong nhận định hoặc hướng xử lý (tên bài CSKT, tên tài liệu HDSD, số phiếu cũ), không có mục riêng. Tool trả 'chưa có kho HDSD' hoặc không có kết quả thì không nêu nguồn đó.
```
Khác bản `U6b.md:294` đúng một câu ("Nêu nguồn đã dùng trong phần Căn cứ." → câu thứ hai ở trên), theo AC-48 `[changed]`. `REPLY_BLOCK` (`U6b.md:295`) không có hai chữ đó: giữ.

### 3.2 Dòng thay của T157 (`tasks.md:1250`, `:1252`, `:1253`; dòng đầu và Receives giữ)

- Tiêu chí: `  - Tiêu chí: AC-47, AC-48 `[changed]` (`spec-addendum-5.md:73`), AC-40; ADR-030 QĐ 3 (prompt theo kết quả cấp); `U6b.md:294-295`, chữ `KNOWLEDGE_SOURCES_BLOCK` theo `design-w1-fixes-19.md` Điểm 3.1 (thắng câu thứ hai của `U6b.md:294`).`
- Returns: `  - Returns: `KNOWLEDGE_SOURCES_BLOCK` (ghép sau `CONVENTIONS` khi có tool; chữ ở `design-w1-fixes-19.md` Điểm 3.1), `REPLY_BLOCK`; tham số từ khóa `reply_tools: bool = False` của `build_reason_system` (`REPLY_BLOCK` ⇔ `reply_tools`). `PROMPT_CONFLICT_PAIRS` không thêm cặp.`
- Expect: `  - Expect: `TestKnowledgeSources::test_reason_prompt_names_three_sources` (3 tên tool; cụm "ngay trong nhận định hoặc hướng xử lý"; "Căn cứ" và "Cần ai quyết" không có trong `KNOWLEDGE_SOURCES_BLOCK`, `REPLY_BLOCK` và trong `build_reason_system("", "", change_tools=True, reply_tools=True)[0]["text"]`), `TestReplyBlock::test_block_follows_reply_tools_flag` đỏ trước rồi xanh; `TestCorePrompt::test_no_conflict_pair_in_any_flag_combination`, `::test_no_retired_heading_in_any_built_prompt` (T181) xanh không sửa.`

`depends:` của T157 giữ `T156`: T157 → T156 → T107 → T106 → T82 → T181 (sau khi T82 thêm `depends: T181`, Điểm 4.2), nên T181 đứng trước theo bắc cầu.

### 3.3 T106, T107, T156, T170 — không chạm

| Task | Thứ nó thêm vào `prompts.py` (dòng task) | Có chạm VIẾT COMMENT, quy tắc 6, `ACT_NOW_BLOCK`, mục bắt buộc? |
|---|---|---|
| T106 (`tasks.md:1005`) | `TICKET_FIELD_LABELS`, `FIELD_VALUE_MAX_CHARS`, `ticket_fields_text`, tham số `build_classify_request` | Không: request phân loại, không phải prompt suy luận |
| T107 (`:1010`) | `build_initial_message(..., guidance_posted)`, `TASK_AFTER_GUIDANCE` (chữ ở `design-addendum-3-w1.md:100`: "Phiếu đã có comment Hướng xử lý của bot. …") | Không: thông điệp user; chữ không có hai mục |
| T156 (`:1247`) | `TASK_REQUESTER_REPLY`, `TASK_KB_DRAFT` (chữ ở `U6b.md:293`) | Không: chữ không có hai mục |
| T170 (`:1320`) | `TASK_CATEGORY_C` (ý ở `design-addendum-1-U4b-U8.md:203`), `CATEGORY_HINT_TRIGGERS` | Không: chữ không có hai mục |

Bốn task chỉ chung file `prompts.py`, `test_prompts.py` với T181: không sửa dòng nào của chúng; thứ tự theo chuỗi chủ file (Điểm 4.2).

---

## Điểm 4 — task chèn T181 và dòng `depends:` kéo theo (tech-lead `/team:plan --insert`)

T72, T78, T79 đã tick, không mở lại (`spec-addendum-5.md:168`). Số lớn nhất trong `tasks.md` là T180 (`grep -oE '^- \[[ x]\] T[0-9]+'`), nên T181 còn trống.

### 4.1 Khối T181 (chép nguyên văn; đứng ngay sau T176, `tasks.md:840`)

```text
- [ ] T181 — Chữ prompt theo phụ lục 5: VIẾT COMMENT không còn "Căn cứ", "Cần ai quyết"; quy tắc 6 và `ACT_NOW_BLOCK`; mục bắt buộc phần lập luận [migrate] — files: erp_ai/agent/prompts.py, erp_ai/agent/test_prompts.py, erp_ai/agent/test_classification.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/agent/test_prompts.py — depends: T79, T176
  - Tiêu chí: AC-65 (a) `[changed]`, AC-66 `[changed]`, AC-32 `[changed]`, AC-38 `[changed]`, AC-48 `[changed]` (phần lõi), AC-23 `[changed]` (2) (phần prompt), AC-6 (P-10, P-11); `spec-addendum-5.md` mục 3.1, 3.2; `design-w1-fixes-19.md` Điểm 1, Điểm 2. Sửa chữ đã merge của T72 (mục bắt buộc), T78 (quy tắc 6), T79 (VIẾT COMMENT, `ACT_NOW_BLOCK`, mô tả trường); ba task đó không mở lại. Sáu file vì bỏ `**Căn cứ:**` khỏi prompt và khỏi phép kiểm phải cùng commit (Điểm 2.4). Không đổi `build_reason_system`, `core_prompt` (chữ ký), hàm ghi comment của U4b, ngăn U7b. Biến thể dòng "Không tự liệt kê …": A (Điểm 1.1) trừ khi `design-w1-fixes-20.md` chọn B (Điểm 1.5). Ghi đè `reasoning` đã lưu giữ nguyên, không patch. Chuỗi chủ file: `prompts.py`, `test_prompts.py`: T79 → T181 → T82 → T106 …; `test_classification.py`: T72 → T79 → T176 → T181 → T82; `erp_ai_setting.py`, `test_erp_ai_setting.py`: … T72 → T79 → T181 → T87 → T124; `erp_ai_setting.json`: T64 → T125 → T72 → T79 → T181.
  - Receives: `_CORE_WRITING`, `RULE_6_ACT`, `ACT_NOW_BLOCK`, `PROMPT_CONFLICT_PAIRS`, `core_prompt` (T78, T79); `PROMPT_REQUIRED_MARKERS`, `missing_prompt_markers` (T19, T72, T79); `OLD_CORE_PROMPT`, `OLD_WRITING`, `NEW_WRITING`, `ALL_FLAGS`, `_flag_blocks` của `test_prompts.py`; `PROMPT_PARTS`, `_save`, `_stored`, `_missing_error` của `TestPromptOverrides`.
  - Returns: `_CORE_WRITING` theo `design-w1-fixes-19.md` Điểm 1.1; `RULE_6_ACT` theo Điểm 1.2; `ACT_NOW_BLOCK` thay hai chỗ theo Điểm 1.3; `PROMPT_CONFLICT_PAIRS` thêm P-10, P-11 cuối tuple (10 cặp) theo Điểm 1.4; `PROMPT_REQUIRED_MARKERS["reasoning"] == ("**Nhận định:**", "**Hướng xử lý:**")`; mô tả `prompt_override_reasoning` nguyên văn Điểm 2.2 (369 ký tự), `"modified"` tăng. Không tên công khai mới. Ở `test_prompts.py`: `OLD_WRITING_LINES` thành bốn dòng `:54-57` của `OLD_CORE_PROMPT` (từ `**Nhận định:**` tới `**Cần ai quyết:** nếu có.`, kèm `\n` cuối); `U1_5_WRITING_LINES` đổi tên `A5_WRITING_LINES`, là ba dòng của Điểm 1.1 (từ `**Nhận định:**` tới hết dòng "Không tự liệt kê …", kèm `\n` cuối); `NEW_WRITING = OLD_WRITING.replace(OLD_WRITING_LINES, A5_WRITING_LINES)`; chú thích `:73-74` thay bằng `# spec changed (spec-addendum-5 AC-65 (a), AC-66, AC-38): in VIẾT COMMENT only these lines change; no "Căn cứ", no "Cần ai quyết". The rest of VIẾT COMMENT stays the old text byte for byte.`
  - Expect: viết test trước (một commit test), `cmd.migrate` trước `cmd.test_one`, đỏ trên mã T79: test_prompts `TestCorePrompt::test_default_core_prompt_keeps_rules_1_5_and_limits` (sửa: `OLD_WRITING.count(OLD_WRITING_LINES) == 1`; `"Căn cứ"`, `"Cần ai quyết"` đều không có trong `NEW_WRITING`; `CORE_PROMPT == OLD_HEAD + RULE_6_ACT + "\n" + NO_OK_APPROVAL + OLD_LIMITS + NEW_WRITING`) — đỏ vì `CORE_PROMPT` còn VIẾT COMMENT của T79; `::test_limits_follow_tool_flags_only` (không sửa dòng, đỏ theo `NEW_WRITING` mới); `::test_no_conflict_pair_in_any_flag_combination` (sửa đúng một số: `len(...) == 10  # P-1..P-5, P-7..P-11`) — đỏ `8 != 10`; mới `::test_no_retired_heading_in_any_built_prompt` (mọi `flags` của `ALL_FLAGS`: `build_reason_system("DIGEST-XYZ", "ROUTING-ABC", **flags)[0]["text"]` không chứa `"Căn cứ"` và không chứa `"Cần ai quyết"`, có đúng 1 `"**Nhận định:**"` và đúng 1 `"**Hướng xử lý:**"`; năm khối của `_flag_blocks()` không chứa hai chữ đó) — đỏ ở cả 32 tổ hợp; mới `::test_rule_6_points_to_approve_now_in_the_bot_panel` (`'bấm "Duyệt ngay" trong ngăn "Trao đổi với bot"'` ∈ `RULE_6_ACT`; `"ngăn của bot"` ∉ `RULE_6_ACT`; `RULE_6_ACT` không có `"\n"`) — đỏ. test_classification `TestPrompts::test_act_now_block_only_with_action_tools` (sửa danh sách cụm: bỏ `"Cần ai quyết"`, thêm `'"Hướng xử lý" là việc người phải làm'`; thêm `self.assertNotIn("Cần ai quyết", block)`; các cụm khác và phần còn lại của test giữ) — đỏ. test_erp_ai_setting `TestPromptOverrides`: `PROMPT_PARTS["reasoning"]` (`:2345`) thành `("**Nhận định:**", "**Hướng xử lý:**")` → `::test_required_markers_match_design` đỏ (tuple khác), `::test_first_bad_part_in_form_order` đỏ (thông báo còn ba mục); mới `::test_reasoning_override_without_evidence_heading_saves` (lưu `"**Nhận định:** a\n**Hướng xử lý:** b"` → `_save` trả `None`, `_stored` bằng đúng giá trị; rồi lưu `"**Nhận định:** a\n**Căn cứ:** c"` → `_missing_error("chỉ dẫn lập luận", "**Hướng xử lý:**")`, `_stored` vẫn là giá trị trước) — đỏ (mã cũ đòi `**Căn cứ:**`); mới `::test_builtin_reasoning_has_no_retired_heading` (`"Căn cứ"`, `"Cần ai quyết"` ∉ `prompts.CORE_PROMPT`; `"**Căn cứ:**"`, `"**Cần ai quyết:**"` ∉ mô tả `prompt_override_reasoning` đọc qua `frappe.get_meta`) — đỏ. Xanh trước và sau (ghim, không sửa dòng): `::test_reasoning_override_with_retired_marker_still_saves` (`:2634-2638`); mới `::test_reasoning_override_from_before_addendum_5_still_saves` (lưu `prompts.CORE_PROMPT + "\n**Căn cứ:** bản ghi hoặc dòng code cụ thể đã xem (ghi rõ file và số dòng).\n**Cần ai quyết:** nếu có."` → `None`, `_stored` bằng đúng giá trị); `::test_builtin_prompts_pass_required_markers`, `::test_missing_marker_blocked_each_part`, `::test_missing_markers_listed_in_constant_order`, `::test_markers_need_their_exact_form`. Sau commit mã (một commit cho sáu file): mọi test trên xanh; `cmd.test_one` xanh cả file cho `erp_ai/agent/test_prompts.py`, `erp_ai/agent/test_classification.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`; xanh không sửa một dòng: `erp_ai/tests/test_doctype_descriptions.py` (369 ≤ 400, đủ bốn cụm), `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_runner_routing.py`, `erp_ai/eval/test_run_eval.py`, `erp_ai/tests/test_architecture.py`. Không sửa `OLD_CORE_PROMPT` (`test_prompts.py:15-63`). Chèn 6, CI-6 (`arch-impact-chg-002.md:95`): `test_prompts.py` không chép chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1. Lý do từng test bị sửa ghi trong commit test theo `design-w1-fixes-19.md` mục STD-TEST-5.
```

### 4.2 Dòng `depends:` kéo theo (tech-lead sửa khi chèn; chữ khác của task giữ)

| Task | `depends:` hiện (`tasks.md`) | Thành | Vì |
|---|---|---|---|
| T82 (`:857`) | `T81, T79, T65, T176` | `T81, T79, T65, T176, T181` | chung `prompts.py`, `test_classification.py`; T82 chưa bắt đầu (không có dòng progress) |
| T87 (`:903`) | `T86, T72, T32, T79` | `T86, T72, T32, T79, T181` | chung `erp_ai_setting.py`, `test_erp_ai_setting.py`; T124 theo sau T87 nên bắc cầu |
| T157 (`:1249`) | `T156` | giữ | bắc cầu qua T82 (Điểm 3.2) |

T126 (`tasks.md:1075`, `depends: —`) cũng có `prompts.py`, `test_prompts.py` trong `files:`: tech-lead xếp thứ tự T126 và T181 ở preflight vòng 20, không cùng lượt.

---

## STD-TEST-5 — test bị sửa, test giữ, lý do

| Test (worktree @ `c7002de`) | Sửa gì | Lý do (spec đổi) |
|---|---|---|
| `erp_ai/agent/test_prompts.py:73-81` (`OLD_WRITING_LINES`, `U1_5_WRITING_LINES`, `NEW_WRITING`) | bốn dòng cũ → ba dòng của Điểm 1.1 | AC-65 (a) `[changed]`: bỏ "Căn cứ", "Cần ai quyết"; hướng xử lý là phương án. Phép so từng byte giữ, chỉ đổi đoạn spec đổi |
| `erp_ai/agent/test_prompts.py:145-146` | `assertNotIn("**Cần ai quyết:**", …)` → không có cả `"Căn cứ"` lẫn `"Cần ai quyết"` | AC-65 (a); khẳng định chặt hơn, không nới |
| `erp_ai/agent/test_prompts.py:209` | `8` → `10` | AC-65 (a) thêm hai cặp vào danh sách AC-6 |
| `erp_ai/agent/test_classification.py:505` | cụm `"Cần ai quyết"` phải có → phải không có; thêm cụm `'"Hướng xử lý" là việc người phải làm'` | AC-66 `[changed]`: câu cho model ghi "Cần ai quyết" không còn trong prompt |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2345` | ba mục → hai mục | AC-38 `[changed]`: "Căn cứ" không còn bắt buộc. Nới phép kiểm vì spec đổi; bù bằng `test_reasoning_override_without_evidence_heading_saves` (thiếu "Hướng xử lý" vẫn bị chặn) |
| **giữ** `erp_ai/agent/test_prompts.py:15-63` (`OLD_CORE_PROMPT`, có `:55`, `:57`) | không sửa | Mốc chữ trước FEAT-007; quy tắc 1-5, GIỚI HẠN và câu cấm của mọi cặp (P-10, P-11 mới) đối chiếu với nó. Sửa nó là bỏ mốc hồi quy |
| **giữ** `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2634-2638` | không sửa | Vẫn đúng chữ AC-38 `[changed]` ("ghi đè cũ … lưu lại được"); thêm test anh em cho ghi đè có cả `**Căn cứ:**` |

---

## Đối chiếu AC (AC phụ lục 5 giao cho phần prompt ↔ test của T181/T157)

AC đổi ở `spec-addendum-5.md` mục 3.1, 3.2 có phần prompt: AC-65 (a), AC-66, AC-32, AC-38, AC-48, AC-23 (2). AC-23 (1), AC-39, AC-69 không có phần prompt (ADR-038, U7a, U7b, kiểm đầu-cuối).

| AC | Cách kiểm (test) |
|---|---|
| AC-65 (a) `[changed]` (prompt) | `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_retired_heading_in_any_built_prompt` (32 tổ hợp: bao trùm mọi mức L1..L3 vì mức chỉ tới prompt qua năm cờ); `::test_default_core_prompt_keeps_rules_1_5_and_limits`; `::test_no_conflict_pair_in_any_flag_combination` (P-10, P-11) |
| AC-66 `[changed]` (prompt) | `erp_ai/agent/test_classification.py::TestPrompts::test_act_now_block_only_with_action_tools`; `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_retired_heading_in_any_built_prompt` |
| AC-32 `[changed]` (prompt) | `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_retired_heading_in_any_built_prompt` (tổ hợp năm cờ tắt và `ask_only`) |
| AC-38 `[changed]` | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPromptOverrides::test_reasoning_override_without_evidence_heading_saves` (biên: thiếu "Hướng xử lý" → chặn), `::test_reasoning_override_from_before_addendum_5_still_saves`, `::test_reasoning_override_with_retired_marker_still_saves`, `::test_builtin_reasoning_has_no_retired_heading`, `::test_required_markers_match_design`, `::test_first_bad_part_in_form_order` |
| AC-48 `[changed]` | lõi: `erp_ai/agent/test_prompts.py::TestCorePrompt::test_default_core_prompt_keeps_rules_1_5_and_limits` (dòng Nhận định ghim); khối nguồn: `erp_ai/agent/test_prompts.py::TestKnowledgeSources::test_reason_prompt_names_three_sources` (T157) |
| AC-23 `[changed]` (2) (prompt) | `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_retired_heading_in_any_built_prompt` |
| (quy tắc 6, AC-39 tên nút trong prompt) | `erp_ai/agent/test_prompts.py::TestCorePrompt::test_rule_6_points_to_approve_now_in_the_bot_panel` |

Danh sách spec: AC-65 (a), AC-66, AC-32, AC-38, AC-48, AC-23 (2). Danh sách test plan: AC-65 (a), AC-66, AC-32, AC-38, AC-48, AC-23 (2). Khớp 6/6. Phần hàm ghi của các AC này (comment thật không có hai tiêu đề, dòng việc người làm tay, "Chờ duyệt") là của W2/T103–T118 và U7b.

**Touchpoint ↔ `allowed_new_file_roots` ↔ `protected_paths`.** Không file mới. Sáu file sửa đều dưới `erp_ai/` (`allowed_new_file_roots` = `['erp_ai', 'docs', '.github']`). `protected_paths` = `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`: 0 file khớp. File này dưới `docs/`.

---

## Giả định kỹ thuật designer đã quyết

| # | Chọn | Vì | Khác | Sai thì |
|---|---|---|---|---|
| D19-1 | Vế "nêu bản ghi, dòng code hoặc nguồn" chuyển vào dòng Nhận định | AC-48 `[changed]` cho nguồn nằm trong nhận định hoặc hướng xử lý; giữ yêu cầu dẫn chứng của "Căn cứ" cũ mà không có mục | Bỏ hẳn yêu cầu dẫn chứng | Bỏ vế đó, đổi `A5_WRITING_LINES` |
| D19-2 | Dòng từ chối của tool tạo đề xuất do hệ thống ghi vào "Hướng xử lý"; model chỉ tự ghi việc nằm ngoài tool | ADR-036 QĐ 2 (bộ gom dựng mục hệ thống); AC-23 (2) "gộp vào comment hướng"; phép kiểm "đúng 1 dòng" của AC-23 (d) cần nguồn tất định | Model tự viết (biến thể B) | Biến thể B, Điểm 1.5 |
| D19-3 | `RULE_6_ACT` đổi tên nút và tên ngăn | AC-39 `[changed]`, AC-65 (a) | Giữ "Duyệt … ngăn của bot" | Trả lại chữ cũ; bỏ `test_rule_6_points_to_approve_now_in_the_bot_panel` |
| D19-4 | Hai cặp P-10, P-11 thay vì chỉ test vắng mặt | Chữ AC-65 (a) "thêm vào danh sách cặp câu của AC-6" | Chỉ test vắng mặt | Bỏ hai cặp, `len` về 8 |

Câu hỏi nghiệp vụ: 0.

## Ghi chú cho người khác (không chặn)

- **W2 (`design-w1-fixes-20.md`):** Điểm 1.5 là điều kiện giao diện; nếu W2 chọn khác, tech-lead dùng biến thể B.
- **Architect:** ADR-036 QĐ 2 (`ADR-036.md:37`) còn ghi tên mục "Cần ai quyết" do hàm ghi dựng. Cơ chế (bộ gom, mục hệ thống thêm) giữ; chỉ nơi đặt dòng từ chối đổi sang "Hướng xử lý" theo AC-66 `[changed]`. `spec-addendum-5.md:193` nói ADR-036 không bị chạm; nếu architect muốn chữ ADR khớp thì một dòng ghi chú, không phải ADR mới.
- `develop` và site đang chạy giữ mẫu cũ tới khi FEAT-007 lên site (A5-11).

## Đã dò mã / chưa chạy

- **Đã dò (chỉ đọc):** `prompts.py:100-363`; `test_prompts.py:1-272`; `test_classification.py:490-520` (lớp `TestPrompts` từ `:246`); `test_erp_ai_setting.py:2330-2378`, `:2585-2693` (lớp `TestPromptOverrides` từ `:2383`); `erp_ai_setting.py:105-139`, `:470-500`; `erp_ai_setting.json:666`; `test_doctype_descriptions.py:185-205`, `:725-745`; grep mọi đuôi file của `erp_ai/` cho hai chữ và cho `prompt_override`; `git diff --stat 05237bb..c7002de` các file trên (rỗng); `.team/profile.json` (`protected_paths`, `allowed_new_file_roots`, `cmd.test_one`). Độ dài mô tả mới (369) và bốn cụm đo bằng một đoạn `python3` chỉ tính chuỗi, không chạm repo.
- **Chưa chạy:** không test nào, không `cmd.migrate`, không lint. Các dòng "đỏ trước" ở Expect của T181 là suy từ mã đã đọc, chưa đo. Không chạy Explore: mọi điểm nằm ở file và dòng lời giao đã nêu, dò bằng grep.
