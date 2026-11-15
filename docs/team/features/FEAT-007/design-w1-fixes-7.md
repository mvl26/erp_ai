# FEAT-007 — design-w1-fixes-7: phán ba điểm pre-flight của đợt 1 (F-2, F-10, F-8)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `preflight-w1.md:23` (F-2), `:24` (F-8), `:31` (F-10); `tasks.md:735-739` (T78), `:740-744` (T79), `:755-759` (T82); `design-addendum-1-U1.md:227-245`; `design-addendum-3-w1.md:75-85` (U1-1..U1-8); `design-w1-fixes-4.md:71-126` (tiền lệ T72).
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `caa555a` — `erp_ai/agent/test_classification.py:322-460` (`class TestPrompts`, `:205`); `erp_ai/agent/prompts.py:126`, `:313-334` (`build_reason_system`, hai phép suy `:327`, `:330`; preflight ghi `:328,330`, cùng hai dòng); `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:108-130`, `:449-458`; `erp_ai_setting.json:661-667`, `:712`; `test_erp_ai_setting.py:2278-2283`, `:2536-2569`; `erp_ai/tests/test_doctype_descriptions.py:192-200`.
- Không đổi kiến trúc, không đổi quy tắc nghiệp vụ: chỉ phân việc giữa T78, T79, T82 theo đúng `U1.md:227` (mỗi khối đúng một cờ, luật cấp ở `grant`, ADR-030 QĐ 3) và U1-5 (`w1.md:80`). Không ADR nào bị chạm; không có `DESIGN_CONFLICT`.

---

## Điểm 1 — F-2: task nào nối cờ vào `core_prompt`; ba test `test_reason_system_with_*` đổi ra sao

### Hiện trạng (dữ kiện)
- `build_reason_system` (`prompts.py:313-334`) ghép hằng `CORE_PROMPT`, không nhận cờ nào cho phần lõi.
- T78 (Returns, `tasks.md:738`) tạo `core_prompt(**5 cờ)` và `CORE_PROMPT = core_prompt()`; T79 (Returns, `:743`) là task đổi chữ ký `build_reason_system` sang năm cờ. Dòng task không nói ai thay `CORE_PROMPT` bằng `core_prompt(**cờ)` trong `build_reason_system`.
- Ba test của `TestPrompts` (`test_classification.py:205`) ghim "lõi có cờ = `CORE_PROMPT`": `test_reason_system_with_change_tools_adds_approval_block` (`:379` dựng `old` không cờ, `:384`, `:385`, `:386`, danh sách `:389-399` bắt đầu bằng `prompts.CORE_PROMPT` ở `:393`); `test_reason_system_with_site_admin_tools_adds_record_block` (`:411`, `:413`); `test_reason_system_with_unrestricted_tools_adds_full_access_block` (`:435`, `:437`).
- Ở T78, `CORE_PROMPT` đổi quy tắc 6 (U1-2) nhưng các test trên so với chính hằng `prompts.CORE_PROMPT`, không chép chuỗi → vẫn xanh nếu `build_reason_system` còn ghép hằng. `test_erp_ai_setting.py:2281` cũng dùng hằng, và VIẾT COMMENT chưa đổi ở T78 → bốn mục bắt buộc vẫn có.
- Tên ba test và `test_act_now_block_only_with_action_tools` được trích trong `docs/team/features/FEAT-004/acceptance.md:60`, `acceptance-part-3.md:38` (AC-29 của FEAT-004) → **không đổi tên test nào** (ở Điểm 1 và Điểm 2).

### Phán quyết
1. **T79 nối cờ.** Trong T79, phần tử đầu của `parts` trong `build_reason_system` thành `core_prompt(change_tools=change_tools, site_admin_tools=site_admin_tools, unrestricted_tools=unrestricted_tools, act_now=act_now, ask_only=ask_only)`. Hai phép suy (`SITE_ADMIN_TOOLS_BLOCK if site_admin_tools and not unrestricted_tools`, và `ACT_NOW_BLOCK` theo ba cờ công cụ) **giữ** ở T79; điều kiện của `ACT_NOW_BLOCK` thành `act_now or change_tools or site_admin_tools or unrestricted_tools`; `ASK_ONLY_BLOCK if ask_only` đứng ngay sau `ACT_NOW_BLOCK` (thứ tự `U1.md:227`). Lý do: T79 là task đổi chữ ký `build_reason_system`; nối ở T78 thì T78 phải làm trước một phần chữ ký của T79 và cũng phải nhận `test_classification.py`, trong khi T79 vẫn phải nhận file đó → hai task cùng sửa một file, không lợi gì.
2. **T78 không chạm `build_reason_system`**, không sửa `test_classification.py`; file đó phải xanh **không đổi một dòng** sau T78 (thêm vào Expect).
3. **T79 sửa ba test** (thêm `erp_ai/agent/test_classification.py` vào `files:` của T79). Chỉ đổi đúng các chỗ sau, không đổi khẳng định nào khác; test chỉ dùng hằng và hàm của `prompts`, không chép chuỗi (STD-DESIGN-4):
   - `test_reason_system_with_change_tools_adds_approval_block`: thay `old = …` (`:379`) bằng `core = prompts.core_prompt(change_tools=True)` và `head = "\n\n".join([core, prompts.CATEGORY_TABLE, "ROUTING-ABC", prompts.CONVENTIONS])`; thêm `self.assertNotEqual(core, prompts.CORE_PROMPT)` (chứng minh lõi theo cờ, P-1); `:384` `old` → `head`; `:385` `prompts.CORE_PROMPT` → `core`; `:386` `old + "\n\n"` → `head + "\n\n"`; `:393` `prompts.CORE_PROMPT` → `core`. `:397` (`ACT_NOW_BLOCK`) giữ ở T79.
   - `test_reason_system_with_site_admin_tools_adds_record_block`: thay `old = …` (`:411`) bằng `head = "\n\n".join([prompts.core_prompt(site_admin_tools=True), prompts.CATEGORY_TABLE, "ROUTING-ABC", prompts.CONVENTIONS])`; `:413` `old` → `head`. `:414-418` giữ.
   - `test_reason_system_with_unrestricted_tools_adds_full_access_block`: thay `old = …` (`:435`) bằng `head = "\n\n".join([prompts.core_prompt(unrestricted_tools=True), prompts.CATEGORY_TABLE, "ROUTING-ABC", prompts.CONVENTIONS])`; `:437` `old` → `head`. `:438-441` giữ ở T79.
   - RED của T79 cho phần này: sửa ba test trước, chúng đỏ vì `build_reason_system` còn ghép `CORE_PROMPT` (khẳng định theo `head`), rồi xanh. Lý do trong commit: "U1.md:227 (lõi theo cờ, AC-6); NFR-8, STD-TEST-5: đổi mốc so sánh, không nới khẳng định".
   - Số dòng đo ở `caa555a`; T72 sửa cùng file trước T79, dev dò theo nội dung câu lệnh, không theo số dòng.

### Dòng thay trong `tasks.md` (chép nguyên văn)

T78 (`tasks.md:739`, Expect) — chèn vào cuối dòng:
```
 `design-w1-fixes-7.md` Điểm 1: T78 không chạm `build_reason_system` (vẫn ghép hằng `CORE_PROMPT`; nối cờ ở T79); `erp_ai/agent/test_classification.py` và `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` xanh không sửa một dòng (chạy `cmd.test_one` cho cả hai file).
```

T79: dòng tiêu đề, Tiêu chí, Returns, Expect ở mục "Dòng thay T79" của Điểm 3 (Điểm 1 và Điểm 3 cùng sửa T79, gộp một chỗ).

---

## Điểm 2 — F-10: khẳng định thay cho hai phép suy T82 xóa

### Hiện trạng (dữ kiện)
- T82 xóa `prompts.py:327` (`… and not unrestricted_tools`) và phép suy của `ACT_NOW_BLOCK` (`:330`); sau T82 mỗi khối chỉ theo cờ của nó (`U1.md:227`). Luật "khối toàn quyền thay khối bản ghi" và "khối LÀM LUÔN đi cùng tool hành động" nay ở `grant` (`U1.md:185`; `Grant.act_now_block`, `record_block`), đã có test của T77: `erp_ai/agent/tools/test_registry.py::TestGrantFeat007::test_record_block_hidden_when_unrestricted_granted` (`U1.md:407`, `tasks.md:734`). T82 `depends:` T81 → T80 → T77, nên test đó đã có khi T82 chạy.
- Ngoài ba chỗ preflight nêu (`:411-418`, `:435-441`, `:443-460`), test change_tools cũng dựa vào phép suy `:330`: `:384` và `:397` chờ `ACT_NOW_BLOCK` khi chỉ có `change_tools=True`. Preflight bỏ sót; gộp vào đây.

### Phán quyết
**T82 sở hữu** (thêm `erp_ai/agent/test_classification.py` vào `files:` của T82, file thứ chín). Trên trạng thái sau T79, chỉ đổi đúng các chỗ sau, không đổi tên test, không đổi khẳng định nào khác:
- `test_reason_system_with_change_tools_adds_approval_block`: `:384` → `self.assertEqual(text, "\n\n".join([head, block, "DIGEST-XYZ"]))` và thêm `self.assertNotIn(prompts.ACT_NOW_BLOCK, text)`; bỏ phần tử `prompts.ACT_NOW_BLOCK` (`:397`) khỏi danh sách của `no_digest`.
- `test_reason_system_with_site_admin_tools_adds_record_block`: `:413` → `"\n\n".join([head, block, "DIGEST-XYZ"])`; `:416` → `both.endswith("\n\n".join([prompts.CHANGE_TOOLS_BLOCK, block]))`.
- `test_reason_system_with_unrestricted_tools_adds_full_access_block`: `:437` → `"\n\n".join([head, block, "DIGEST-XYZ"])`; chú thích `:438` → `# U1.md:227: the builder follows each flag; grant() keeps record_block off when unrestricted (U1.md:185)`; `:441` `assertNotIn(prompts.SITE_ADMIN_TOOLS_BLOCK, both)` → `assertIn(prompts.SITE_ADMIN_TOOLS_BLOCK, both)`; `:440` giữ. Luật "thay, không ghép" vẫn được kiểm ở `test_record_block_hidden_when_unrestricted_granted` (T77), nên không mất phép kiểm nào (STD-TEST-5).
- `test_act_now_block_only_with_action_tools`: phần câu của khối (`:444-455`) và `:456` giữ (thân khối FEAT-004 không đổi). Thay vòng lặp `:457-460` bằng: với mỗi `flags` trong ba cờ cũ, `self.assertNotIn(block, prompts.build_reason_system("", "", **flags)[0]["text"], flags)`, rồi `text = prompts.build_reason_system("", "", act_now=True, **flags)[0]["text"]` có `text.count(block) == 1` và `text.endswith(block)`; thêm ca `act_now=True` một mình: `count == 1`, `endswith(block)`. Thêm một dòng chú thích đầu vòng lặp: `# U1.md:227: ACT_NOW_BLOCK follows act_now alone; grant() sets act_now_block with the action tools`. Giữ tên test vì AC-29 của FEAT-004 trích tên đó.
- RED: sửa test trước trên mã T79 → đỏ (phép suy còn: `ACT_NOW_BLOCK` có mặt, `SITE_ADMIN_TOOLS_BLOCK` vắng), rồi xanh sau khi xóa hai phép suy. Lý do trong commit: "U1.md:227 (mỗi khối một cờ, luật ở grant); NFR-8, STD-TEST-5".

### Dòng thay trong `tasks.md` (chép nguyên văn)

T82 (`tasks.md:755`, tiêu đề) — thay cả dòng bằng:
```
- [ ] T82 — `_reason` lấy tool và cờ khối từ `grant`; bỏ đường cấp cũ và cầu của T76 — files: erp_ai/agent/runner.py, erp_ai/agent/tools/registry.py, erp_ai/agent/prompts.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/tools/test_registry.py, erp_ai/agent/tools/test_site_api.py, erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py, erp_ai/agent/test_classification.py — test: erp_ai/agent/test_agent_runner.py — depends: T81, T79, T65
```

T82 (`tasks.md:759`, Returns) — chèn ngay trước đoạn `` (dòng số đo ở `team/FEAT-007` @ `10781fc`, dịch theo T80, T81). `` đoạn sau:
```
; `test_classification.py` (`design-w1-fixes-7.md` Điểm 2, file thứ chín) — bốn test `test_reason_system_with_change_tools_adds_approval_block`, `test_reason_system_with_site_admin_tools_adds_record_block`, `test_reason_system_with_unrestricted_tools_adds_full_access_block`, `test_act_now_block_only_with_action_tools` đổi đúng các chỗ của Điểm 2, giữ tên test
```

T82 (`tasks.md:758`, Receives) — thay cả dòng bằng:
```
  - Receives: `grant`, `Grant` (T76, T77); `build_reason_system` năm cờ và lõi `core_prompt(**cờ)` (T79); `test_registry.py::TestGrantFeat007::test_record_block_hidden_when_unrestricted_granted` (T77) giữ luật "khối toàn quyền thay khối bản ghi".
```

T82 Expect (dòng ngay sau `:759`) — chèn vào cuối dòng:
```
 `erp_ai/agent/test_classification.py` xanh cả file (`cmd.test_one`), bốn test của Điểm 2 đỏ trước trên mã T79.
```

---

## Điểm 3 — F-8: mục bắt buộc của `reasoning`, chữ mô tả mới, ghi đè đã lưu

### Hiện trạng (dữ kiện)
- `PROMPT_REQUIRED_MARKERS["reasoning"]` (`erp_ai_setting.py:122`) có bốn mục, mục thứ tư `"**Cần ai quyết:**"`; phép kiểm là `marker in text` (`:454-456`). Test ghim cùng bốn mục ở `PROMPT_PARTS["reasoning"]` (`test_erp_ai_setting.py:2282`); `test_required_markers_match_design` (`:2536-2542`) đòi (a) tuple nguồn = tuple test, (b) mọi mục có trong `description`; `test_builtin_prompts_pass_required_markers` (`:2544`) lưu `prompts.CORE_PROMPT` và đòi qua phép kiểm; `test_missing_markers_listed_in_constant_order` (`:2564-2569`) dùng `markers[0]`, `markers[-1]` (với ba mục: `**Nhận định:**`, `**Hướng xử lý:**`, vẫn hai mục khác nhau).
- U1-5 (`w1.md:80`) bỏ dòng `**Cần ai quyết:** nếu có.` (`prompts.py:126`) và nói mục đó do hàm ghi dựng. Sau T79, `CORE_PROMPT` không còn chuỗi `**Cần ai quyết:**` (chỉ còn `"Cần ai quyết"` trong ngoặc kép và trong `ACT_NOW_BLOCK`, không phải phần ghi đè được).
- `description` hiện ở `erp_ai_setting.json:666` (269 ký tự) liệt kê bốn mục. Bốn cụm bắt buộc của trường này: `("Để trống", "bắt buộc", "20000", "không bị ghi đè")` (`test_doctype_descriptions.py:195-200`). Trần 400 ký tự (`MAX_DESCRIPTION_CHARS`, `test_doctype_descriptions.py:10`).
- Ở `caa555a` không file nào dưới `erp_ai/agent/` đọc `prompt_override_*` (`git grep "prompt_override\|PROMPT_OVERRIDE_FIELDS" -- 'erp_ai/agent/*.py'` ngoài file test: 0 dòng): ghi đè `reasoning` hiện chỉ được lưu và kiểm khi lưu; U7 mới ghép nó vào lúc chạy (`U1.md:247`, `:300`).

### Phán quyết
1. **Ba mục bắt buộc**: `("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**")`. Giữ bốn thì `CORE_PROMPT` dựng sẵn trượt phép kiểm của chính nó (đỏ `:2544`) và trái U1-5; không có phương án bốn mục hợp lệ. Bỏ mục là nới phép kiểm theo spec đổi (AC-65 (a), AC-23 `[changed]`): lý do trong commit "spec đổi (AC-65 (a)); mục Cần ai quyết do hàm ghi dựng (U1-5); NFR-8, STD-TEST-5".
2. **Cùng commit với T79** (bỏ dòng ở `prompts.py` và bỏ mục ở phép kiểm phải cùng lần merge, nếu không `test_builtin_prompts_pass_required_markers` đỏ ngay sau merge). T79 thêm ba file `erp_ai_setting.py`, `erp_ai_setting.json`, `test_erp_ai_setting.py` và nhãn `[migrate]`.
3. **Chữ mô tả chốt** của `prompt_override_reasoning` (thay giá trị `"description"` ở `erp_ai_setting.json:666`; chữ hiển thị):
```
Để trống = dùng bản dựng sẵn. Nội dung thay phần chỉ dẫn lập luận; phải có các mục bắt buộc **Nhận định:**, **Căn cứ:**, **Hướng xử lý:** và ≤ 20000 ký tự. Các mục Đã làm, Chờ duyệt, Cần ai quyết do bot tự thêm. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt.
```
   Dòng JSON chép nguyên văn (thay cả dòng `:666`, giữ thụt lề 3 dấu cách như hiện có; chữ không có dấu `"` nên không cần thoát):
```
   "description": "Để trống = dùng bản dựng sẵn. Nội dung thay phần chỉ dẫn lập luận; phải có các mục bắt buộc **Nhận định:**, **Căn cứ:**, **Hướng xử lý:** và ≤ 20000 ký tự. Các mục Đã làm, Chờ duyệt, Cần ai quyết do bot tự thêm. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt."
```
   Khác chữ cũ đúng hai chỗ: bỏ `, **Cần ai quyết:**`; chèn câu `Các mục Đã làm, Chờ duyệt, Cần ai quyết do bot tự thêm.` ngay sau câu `… ≤ 20000 ký tự.` Câu chèn là chỗ duy nhất báo cho người quản trị có ghi đè cũ (mục 5). Giữa lần merge U1 và U4b câu này đi trước hàm ghi, cùng lối chấp nhận A-W1-4 (`w1.md:85`).

   Đo bằng lệnh (`git show team/FEAT-007:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | python3 -I -c '<đọc JSON, lấy description cũ, so với chuỗi mới>'`, chỉ đọc, không chạm site), dán nguyên kết quả:
```
old len 269 NFC True
new len 306 NFC True strip 306
missing_markers []
missing_phrases []
old_marker_gone True
old_clauses_kept True
```
   (`missing_markers`: ba mục mới; `missing_phrases`: bốn cụm của `test_doctype_descriptions.py:197`; `old_marker_gone`: không còn `**Cần ai quyết:**`; `old_clauses_kept`: mọi câu của chữ cũ, sau khi bỏ mục thứ tư, có nguyên trong chữ mới.) **306 ≤ 400.** `test_doctype_descriptions.py` xanh không sửa.
4. **Ba chỗ đi kèm**, cùng commit:
   - `erp_ai_setting.py:122` → `"reasoning": ("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**"),`.
   - `test_erp_ai_setting.py:2282` → `("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**"),`. Thêm một test trong `TestPromptOverrides`: `test_reasoning_override_with_retired_marker_still_saves` — lưu `prompts.CORE_PROMPT + "\n**Cần ai quyết:** nếu có."` vào `prompt_override_reasoning` → `self._save(...)` trả `None` và `self._stored(...)` bằng đúng chuỗi đã lưu (chứng minh ghi đè dạng cũ vẫn hợp lệ, STD-DESIGN-3); dùng lại `_save`, `_stored` có sẵn.
   - `erp_ai_setting.json:712` `"modified"`: tăng thêm 1 giờ so với mốc đang có trên nhánh lúc dev bắt đầu (sau T72 là `"2026-11-15 17:00:00.000000"` → `"2026-11-15 18:00:00.000000"`), để `cmd.migrate` nạp lại DocType.
5. **Ghi đè `reasoning` đã lưu trên site**: không patch, không sửa, không xóa giá trị đã lưu; không bước đối soát. Lý do: tập mục mới (3) nằm trong tập cũ (4), nên mọi giá trị đã qua phép kiểm cũ vẫn qua phép kiểm mới, lần lưu sau không bị từ chối; đó là chữ của người quản trị (sửa là đụng nội dung người dùng, cần quyết định của người, không thuộc thiết kế). Hiện chưa có mã nào đọc ghi đè lúc chạy (dữ kiện trên), nên không có hành vi chạy nào đổi ở T79. Khi U7 ghép ghi đè, một giá trị còn dòng `**Cần ai quyết:** nếu có.` có thể khiến model tự viết mục đó; chặn ở hai chỗ đã có: mô tả trường (câu chèn ở mục 3) và chữ của schema `post_comment` "Không tự viết mục Đã làm/Chờ duyệt/Cần ai quyết" (U4b-9, `w1.md:99`), áp cho mọi bản chỉ dẫn. `cmd.migrate` chỉ nạp lại meta (mô tả, `modified`), không đụng dữ liệu; đường lùi là revert commit rồi `cmd.migrate`. Không thêm task.

### Dòng thay T79 trong `tasks.md` (chép nguyên văn; gồm Điểm 1 và Điểm 3)

T79 (`tasks.md:740`, tiêu đề) — thay cả dòng bằng:
```
- [ ] T79 — Khối VIẾT COMMENT mới, `ASK_ONLY_BLOCK`, mỗi khối đúng một cờ [migrate] — files: erp_ai/agent/prompts.py, erp_ai/agent/test_prompts.py, erp_ai/agent/test_classification.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — test: erp_ai/agent/test_prompts.py — depends: T78
```

T79 (`tasks.md:741`, Tiêu chí) — chèn vào cuối dòng:
```
 `design-w1-fixes-7.md` Điểm 1 và Điểm 3: T79 nối `core_prompt(**cờ)` vào `build_reason_system` (hai phép suy giữ); ba test `test_reason_system_with_*` của `test_classification.py` đổi mốc so sánh sang `core_prompt(<cờ>)`; mục bắt buộc `reasoning` còn ba (`**Nhận định:**`, `**Căn cứ:**`, `**Hướng xử lý:**`) ở `PROMPT_REQUIRED_MARKERS` và `PROMPT_PARTS` của test, chữ mô tả `prompt_override_reasoning` thay nguyên văn (306 ký tự), `"modified"` tăng, cùng commit với việc bỏ dòng `**Cần ai quyết:** nếu có.`; ghi đè `reasoning` đã lưu giữ nguyên, không patch. Sáu file vì bỏ dòng ở prompt và bỏ mục ở phép kiểm phải cùng commit. Chuỗi chủ `erp_ai_setting.json`: T64 → T125 → T72 → T79; `erp_ai_setting.py`, `test_erp_ai_setting.py`: … → T64 → T72 → T79 → T87 → T124; `test_classification.py`: T72 → T79 → T82.
```

T79 (`tasks.md:743`, Returns) — thay cả dòng bằng:
```
  - Returns: `build_reason_system(prompt_digest, routing_table="", *, change_tools=False, site_admin_tools=False, unrestricted_tools=False, act_now=False, ask_only=False) -> list[dict]`, phần lõi là `core_prompt(**năm cờ)`, `ACT_NOW_BLOCK` khi `act_now` hoặc một trong ba cờ công cụ, `SITE_ADMIN_TOOLS_BLOCK` khi `site_admin_tools and not unrestricted_tools` (hai phép suy xóa ở T82), `ASK_ONLY_BLOCK` khi `ask_only`, đứng sau `ACT_NOW_BLOCK`; `ASK_ONLY_BLOCK`; khối VIẾT COMMENT theo U1-5 (bỏ dòng "Cần ai quyết"); `PROMPT_REQUIRED_MARKERS["reasoning"] == ("**Nhận định:**", "**Căn cứ:**", "**Hướng xử lý:**")`; mô tả `prompt_override_reasoning` theo `design-w1-fixes-7.md` Điểm 3.
```

T79 (`tasks.md:744`, Expect) — chèn vào cuối dòng:
```
 `cmd.migrate` trước `cmd.test_one`; `erp_ai/agent/test_classification.py` xanh cả file, ba test `test_reason_system_with_*` đỏ trước (mốc `core_prompt(<cờ>)` khi lõi còn là `CORE_PROMPT`) rồi xanh; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPromptOverrides::test_required_markers_match_design`, `::test_builtin_prompts_pass_required_markers`, `::test_missing_markers_listed_in_constant_order`, `::test_missing_marker_blocked_each_part` xanh, `::test_reasoning_override_with_retired_marker_still_saves` mới xanh; `erp_ai/tests/test_doctype_descriptions.py` xanh không sửa (306 ≤ 400, đủ bốn cụm).
```

---

## Chuỗi chủ file (sau phán quyết)
- `erp_ai_setting.json`: T64 → T125 → T72 → **T79**. Không task mở nào khác có file này (`grep` các dòng `- [ ]` ở `tasks.md`: chỉ T72).
- `erp_ai_setting.py`, `test_erp_ai_setting.py`: U0 → T56 → T32 → T63 → T64 → T72 → **T79** → T87 → T124. Để giữ thứ tự, team-leader thêm `T79` vào cuối `depends:` của T87 (`tasks.md:799`, nay `— depends: T86, T72, T32` → `— depends: T86, T72, T32, T79`), không đổi gì khác của dòng đó.
- `test_classification.py`: T72 → **T79** → **T82**. T126 (gộp `develop`, `[migrate]`) cũng có `test_classification.py` và `prompts.py`: không cùng lượt với T78, T79, T82.
- `prompts.py`: T72 → T78 → T79 → T82 (như cũ; không đổi).
- Không task nào đổi số; ngoài `depends:` của T87, không `depends:` nào đổi.

## Đối chiếu AC
AC trong ba điểm: AC-6, AC-23 `[changed]`, AC-65 (a), AC-66 (theo `tasks.md:736`, `:741`, `:756`). Có test trong các dòng thay: AC-6 (ba test `test_reason_system_with_*`, `test_record_block_hidden_when_unrestricted_granted`), AC-65 (a) và AC-23 (`test_required_markers_match_design`, `test_builtin_prompts_pass_required_markers`, `test_reasoning_override_with_retired_marker_still_saves`), AC-66 (Expect sẵn có của T78). Khớp 4/4.
