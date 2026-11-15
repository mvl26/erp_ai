# FEAT-007 — design-w1-fixes-4: phán hai điểm chặn của build đợt 1 (T76, T72)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `tasks.md:174-175` (CHẶN 2, CHẶN 3), `:688-693` (T72 và dòng progress), `:710-715` (T76 và dòng progress); `design-addendum-1-U1.md:136-146`, `:166-187`.
- Mã đọc (chỉ đọc, `git show`/`git grep`): `team/FEAT-007` @ `aedc360` — `erp_ai/tests/test_architecture.py:168-176` (`POLICY_FIELDS`), `:805-822` (`check_policy_fields_only_in_policy`), `:6102-6118`, `:1280-1289` (`PANEL_GATE_NAMES`); `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:654-660`, `:712`; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:108-120` (`PROMPT_REQUIRED_MARKERS`); `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:411-418`, `:2258-2276` (`PROMPT_PARTS`), `:2320` (`class TestPromptOverrides`), `:2529-2543`, `:2566-2578`; `erp_ai/tests/test_doctype_descriptions.py:10`, `:192-200`. `1402e89` (nhánh `team/FEAT-007-task-76`) — `erp_ai/agent/tools/test_registry.py:819`.
- Không đổi kiến trúc: theo ADR-003/ADR-005 (luật "trường cấu hình mức và chính sách gửi chỉ đọc ở `agent/policy.py`", `test_architecture.py:806`), ADR-030 QĐ 2 (mức quyền = `effective_level`), QĐ 3 (bảng cấp). `arch-ruling-r5.md` không nhắc `GrantInputs` hay `permission_level` (`grep` 0 dòng). Không đổi quy tắc nghiệp vụ.

---

## Điểm 1 — T76: tên trường mức quyền của `GrantInputs`

### Hiện trạng (dữ kiện)
- `POLICY_FIELDS` (`test_architecture.py:168-176`) có `"permission_level"`. `check_policy_fields_only_in_policy` (`:805-822`) báo vi phạm cho mọi `referenced_name` trùng `POLICY_FIELDS` (tên, thuộc tính, khai báo trường dataclass) và mọi hằng chuỗi đúng bằng tên đó, ở mọi file `.py` ngoài `agent/policy.py`. Test `:6102-6118` ghim đúng hành vi đó (`settings.permission_level` ở `agent/tools/read.py` phải bị bắt).
- `design-addendum-1-U1.md:139` đặt `GrantInputs.permission_level` trong `agent/tools/registry.py` → 2 test đỏ (`test_auto_assign_switch_only_in_policy`, `test_level_and_send_policy_fields_only_in_policy`, dòng progress T76 round 83). Sửa luật là nới một luật của ADR-003/ADR-005 và đòi `test_architecture.py` (chuỗi chủ T71 → T74 → T80 → T82 → T83) → loại.
- Chính chú thích `U1.md:139` đã ghi nguồn của trường là `policy.effective_level`; `ToolContext.effective_level` có sẵn trong `registry.py` (16 lần ở `1402e89`), `U1.md:166` nói "`effective_level` của context nay mang nghĩa mức quyền"; `_legacy_inputs(effective_level, …)` của T76 cũng dùng tên này. `effective_level` không thuộc `POLICY_FIELDS`; danh sách duy nhất khác có tên đó là `PANEL_GATE_NAMES` (`:1280-1289`), chỉ áp cho file panel, không áp cho `agent/tools/`.

### Phán quyết
Đổi tên trường `GrantInputs.permission_level` → **`GrantInputs.effective_level`** (kiểu `str`, nghĩa "mức quyền", ADR-030 QĐ 2). Không đổi kiểu, thứ tự trường, mặc định, hay bất kỳ điều kiện nào của bảng cấp; chỉ đổi tên biến trong công thức. `test_architecture.py` không sửa một dòng ở T76. Cùng lối với tiền lệ `design-addendum-2-U7b-U8-fixes.md:27` (tránh tên trường cấu hình trên `ToolContext`).

Hệ quả trong `files:` của T76 (không thêm file): mã `registry.py` chưa commit trong worktree `agent-aa9df0388fd4e0631` dùng lại được, chỉ đổi tên ở khai báo trường và mọi chỗ đọc (`:15`, `:101`, `:113`, `:120`, `:138` theo báo cáo của dev); test commit `1402e89` sửa một dòng `test_registry.py:819` (`context.grant_inputs().permission_level` → `context.grant_inputs().effective_level`); RED vẫn là `ImportError`/`AttributeError` do thiếu `GrantInputs`/`grant`/`grant_inputs`/`_legacy_inputs`. Trong `registry.py` không được còn tên, thuộc tính hay hằng chuỗi `"permission_level"` nào (một câu docstring có chữ đó không bị bắt, `:6116-6117`, nhưng không cần viết).

### Dòng thay trong tài liệu thiết kế (chép nguyên văn)

`design-addendum-1-U1.md:139` — thay cả dòng bằng:
```
    effective_level: str           # policy.effective_level ("mức quyền"); không đặt tên permission_level: luật check_policy_fields_only_in_policy (design-w1-fixes-4.md Điểm 1)
```

`design-addendum-1-U1.md:168` — thay đoạn `switches.unrestricted ∧ permission_level > L0 ∧ has_instructor` bằng `switches.unrestricted ∧ effective_level > L0 ∧ has_instructor` (phần còn lại của dòng giữ nguyên).

`design-addendum-1-U1.md:175` — thay cả dòng bằng:
```
| `change_propose` | `switches.code_change ∧ effective_level == L3 ∧ has_instructor ∧ ¬below_threshold` |
```

`design-addendum-1-U1.md:176` — thay cả dòng bằng:
```
| `site_admin` (công cụ bản ghi) | `((switches.record_tools ∧ effective_level == L3 ∧ has_instructor) ∨ u) ∧ ¬below_threshold` |
```

`design-addendum-1-U1.md:179` — thay đoạn `` (1) `permission_level ∉ LEVELS` hoặc `== L0` `` bằng `` (1) `effective_level ∉ LEVELS` hoặc `== L0` `` (phần còn lại giữ nguyên).

`design-addendum-1-U1.md:285` (bảng hợp đồng) — thay `` dataclass frozen `(permission_level, main_path_level, `` bằng `` dataclass frozen `(effective_level, main_path_level, `` (phần còn lại giữ nguyên).

`plan-w1.md:50` — thay `GrantInputs(permission_level, main_path_level,` bằng `GrantInputs(effective_level, main_path_level,` (phần còn lại giữ nguyên).

Không đổi: `U1.md:114`, `:125`, `:127`, `:281` (đó là trường cấu hình `settings.permission_level` và tham số của `policy.main_path_level` trong `policy.py`, nơi luật cho phép).

### Dòng thay trong `tasks.md` (chép nguyên văn)

T76 (`tasks.md:712`, Tiêu chí) — thay đoạn `` `U1.md:136-179` với ranh giới `` bằng:
```
`U1.md:136-179` (tên trường mức quyền theo `design-w1-fixes-4.md` Điểm 1) với ranh giới
```
(phần còn lại của dòng giữ nguyên).

T76 (`tasks.md:713`, Returns) — thay đoạn mở đầu `` - Returns: `GrantInputs`, `Grant` `` bằng:
```
  - Returns: `GrantInputs` (trường mức quyền tên `effective_level`, không phải `permission_level`: `design-w1-fixes-4.md` Điểm 1; trong `registry.py` không còn tên, thuộc tính hay hằng chuỗi `"permission_level"`), `Grant`
```
(phần sau, từ `` (`.schemas()`, `.names()`, năm cờ) `` trở đi, giữ nguyên chữ hiện có).

T76 (`tasks.md:714`, Expect) — không đổi chữ: `TestGrantInputs::test_grant_inputs_maps_context_fields` đã nói "`main_path_level` None → bằng `effective_level`", khớp tên mới; `erp_ai/tests/test_architecture.py` vẫn trong danh sách "xanh, không sửa một dòng".

T77 (`tasks.md:716-720`), T82 (`tasks.md:741-746`) — không đổi chữ. Đo bằng `grep -n permission_level tasks.md`: trong khoảng `:710-746` chỉ có dòng progress `:715` (lịch sử, không sửa); T77 và T82 dẫn bảng `U1.md:168-187` theo số dòng, nên nhận tên mới qua các dòng U1 thay ở trên. Dev của T82 dựng `GrantInputs` ở `test_site_api.py:858-863` bằng `effective_level=`.

Chuỗi chủ file không đổi: T76 vẫn chỉ `registry.py`, `test_registry.py`; không vào chuỗi `test_architecture.py` (T71 → T74 → T80 → T82 → T83).

---

## Điểm 2 — T72: chữ mô tả `prompt_override_classify`

### Hiện trạng (dữ kiện)
- `TestPromptOverrides::test_required_markers_match_design` (`test_erp_ai_setting.py:2320`, `:2529-2543`) đòi (a) `PROMPT_REQUIRED_MARKERS` của nguồn bằng đúng `PROMPT_PARTS` của test (so tuple, có thứ tự), (b) mọi mục bắt buộc có trong `description` của trường (`:2542`). Mô tả nằm ở `erp_ai_setting.json:659` (task ghi `:655`, số đúng là `:659`), chưa có `"do_tin_cay_pct"`.
- Giới hạn độ dài: `MAX_DESCRIPTION_CHARS = 400` (`test_doctype_descriptions.py:10`, `len` Python); cụm bắt buộc của trường này `("Để trống", "bắt buộc", "20000", "không bị ghi đè")` (`:195-200`). `test_new_field_descriptions_at_most_400_chars` (`test_erp_ai_setting.py:411`) chỉ đo `auto_assign_enabled`, `routing_rules`, không đo trường này.
- `:2566-2569` dùng `markers[0]`, `markers[-1]`; `test_markers_need_their_exact_form` (`:2571-2578`) ghim `"bo_phan"`. Giữ `"bo_phan"` ở cuối tuple thì hai test này không đổi.
- Chủ file `erp_ai_setting.json`: T64 → T125 (đã tick, `tasks.md:642`); không task mở nào khác có file này (`grep` các dòng `- [ ]`). `"modified"` hiện là `"2026-11-15 16:00:00.000000"` (`:712`); T125 (`47cadf3`) đã tăng mốc này để `cmd.migrate` nạp lại DocType.

### Phán quyết: chuỗi chốt (thay giá trị `"description"` ở `erp_ai_setting.json:659`)

Chữ hiển thị (sau khi đọc JSON):
```
Để trống = dùng bản dựng sẵn. Nội dung thay bước phân loại; phải có các mục bắt buộc là 12 khóa JSON "dau_muc", "do_tin_cay", "do_tin_cay_pct", "ly_do", "nhom", "uu_tien", "can_tach", "cac_yeu_cau", "do_phuc_tap", "do_quan_trong", "ly_do_diem", "bo_phan" và ≤ 20000 ký tự. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt.
```

Dòng JSON chép nguyên văn (thay cả dòng `:659`, giữ thụt lề 3 dấu cách như hiện có):
```
   "description": "Để trống = dùng bản dựng sẵn. Nội dung thay bước phân loại; phải có các mục bắt buộc là 12 khóa JSON \"dau_muc\", \"do_tin_cay\", \"do_tin_cay_pct\", \"ly_do\", \"nhom\", \"uu_tien\", \"can_tach\", \"cac_yeu_cau\", \"do_phuc_tap\", \"do_quan_trong\", \"ly_do_diem\", \"bo_phan\" và ≤ 20000 ký tự. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt."
```

Khác chữ cũ đúng hai chỗ: `11 khóa` → `12 khóa`; chèn `"do_tin_cay_pct", ` ngay sau `"do_tin_cay", `. Mọi vế khác giữ nguyên chữ.

Đo bằng lệnh (`git show team/FEAT-007:…/erp_ai_setting.json | python3 -I <script trong scratchpad>`, chỉ đọc, không chạm site), dán nguyên kết quả:
```
old len 349 NFC True
new len 367 NFC True changed True
new.strip() len 367
missing_markers []
missing_phrases []
old_clauses_kept True
```
(`missing_markers`: 12 mục; `missing_phrases`: bốn cụm của `test_doctype_descriptions.py:197`; `old_clauses_kept`: mọi câu của chữ cũ, sau hai chỗ đổi, có nguyên trong chữ mới.) 367 ≤ 400.

Ba chỗ đi kèm, cùng commit với cặp C-4 (đều trong `files:` của T72):
- `erp_ai_setting.py` `PROMPT_REQUIRED_MARKERS["classify"]`: chèn `'"do_tin_cay_pct"',` ngay sau `'"do_tin_cay"',` (`:111`); thứ tự này trùng thứ tự trong chữ mô tả, `"bo_phan"` vẫn cuối.
- `test_erp_ai_setting.py` `PROMPT_PARTS["classify"]`: chèn `'"do_tin_cay_pct"',` ngay sau `'"do_tin_cay"',` (`:2266`); chú thích `:2530` thay bằng `# design.md:314-316, U1.md:249-253 (T72): classify holds exactly the 12 keys, "do_tin_cay_pct" right after "do_tin_cay".`. Đây là thêm mục vào phép kiểm (siết, không nới, STD-TEST-5).
- `erp_ai_setting.json:712`: `"modified": "2026-11-15 16:00:00.000000"` → `"modified": "2026-11-15 17:00:00.000000"` (mốc phải lớn hơn mốc hiện có lúc dev bắt đầu; nếu nhánh đã có mốc ≥ 17:00 thì dùng mốc đó cộng 1 giờ).

### Dòng thay trong `tasks.md` (chép nguyên văn)

T72 (`tasks.md:688`, tiêu đề) — thay cả dòng bằng:
```
- [ ] T72 — Độ tin cậy số `do_tin_cay_pct` của bước phân loại [migrate] — files: erp_ai/agent/classification.py, erp_ai/agent/prompts.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/agent/test_classification.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/test_runner_routing.py, erp_ai/eval/test_run_eval.py — test: erp_ai/agent/test_classification.py — depends: T56, T19, T64, T67, T125
```

T72 (`tasks.md:689`, Tiêu chí) — thay đoạn `` Tám file vì C-4 buộc cùng commit; ba file test cuối chỉ thêm khóa `do_tin_cay_pct` vào JSON stub có sẵn. `` bằng:
```
Chín file vì C-4 buộc cùng commit; ba file test cuối chỉ thêm khóa `do_tin_cay_pct` vào JSON stub có sẵn. `erp_ai_setting.json` (`design-w1-fixes-4.md` Điểm 2): chữ mô tả `prompt_override_classify` thay nguyên văn theo Điểm 2 (12 khóa, 367 ký tự), `"modified"` tăng; `"do_tin_cay_pct"` đứng ngay sau `"do_tin_cay"` trong `PROMPT_REQUIRED_MARKERS["classify"]` và `PROMPT_PARTS["classify"]` của test, cùng commit. Chuỗi chủ `erp_ai_setting.json`: T64 → T125 → T72.
```
(phần trước của dòng giữ nguyên).

T72 (`tasks.md:692`, Expect) — chèn ngay sau đoạn `` test "prompt dựng sẵn qua kiểm mục bắt buộc" của T19 xanh; `` đoạn sau:
```
`cmd.migrate` trước `cmd.test_one`; `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPromptOverrides::test_required_markers_match_design` đỏ trước (thêm mục vào `PROMPT_PARTS` của test khi nguồn chưa có) rồi xanh, cùng `::test_builtin_prompts_pass_required_markers`, `::test_markers_need_their_exact_form` không đổi khẳng định; `erp_ai/tests/test_doctype_descriptions.py` xanh không sửa (mô tả ≤ 400, đủ bốn cụm);
```
(phần còn lại giữ nguyên).
