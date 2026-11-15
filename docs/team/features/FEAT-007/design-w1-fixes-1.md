# FEAT-007 — design-w1-fixes-1: phán ba điểm mở của build đợt 1 (T64, T65, T67)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu.
- Đầu vào: `review-64.md:52-62` (và `:25-27`, `:40`, `:45-46` để biết finding nào đã đạt); `tasks.md:572-583` (T64, T65), `:628-633` (T67); `design.md:175,184`; `design-addendum-1-U1.md:110-112`, `:123-125`.
- Mã đọc (chỉ đọc, `git show`): `team/FEAT-007` — `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:118` (bằng `aef271c`); `erp_ai/agent/tools/site_api.py:105-118`, `:142-182`; `erp_ai/agent/test_agent_runner.py:90-118`, `:2749-2842` (và vị trí `monthly_budget_usd` của các lớp test khác); `erp_ai/agent/runner.py:164`. `7fbd1b3` (nhánh `team/FEAT-007-task-64`) — `erp_ai/tests/test_doctype_descriptions.py:10`, `:27-43`, `:491-500`, `:541-547`.
- Không đổi kiến trúc: theo ADR-030 QĐ 2 (mức quyền), ADR-033 QĐ 5 (dòng không phải lần chạy có `cost_usd = 0`), `LAYER_RULES` (`erp_ai.agent` không import `erp_ai.erp_ai_agent`). Không đổi quy tắc nghiệp vụ: AC-29, AC-61, AC-7 giữ nguyên chữ.

---

## Điểm 1 — T64: nguyên văn mô tả `permission_level`

### Hiện trạng (dữ kiện)
- Chữ đã duyệt ở `aef271c` (= `team/FEAT-007`, `erp_ai_setting.json:118`) dài đúng 400 ký tự (đo bên dưới). Returns của T64 đòi bỏ "L2 có công cụ như L1" và thêm ý L2 mà vẫn ≤ 400 → buộc phải bớt chữ ở vế khác. Hai vòng review bắt hai lần vì dev tự chọn vế bớt (`review-64.md:45`, `:56`).
- Finding đã đạt, không được làm hỏng lại: "L3: mức của công cụ bản ghi chung, sửa code", "tự hạ về L1", câu `design.md:184` nguyên văn (`review-64.md:25`, `:40`). Minor vòng 2 ("hoặc" → ","): không khác nghĩa (`review-64.md:46`).
- `test_descriptions_at_most_400_chars` đo `len(description)` của Python (điểm mã Unicode, `MAX_DESCRIPTION_CHARS = 400`); chuỗi lưu ở dạng NFC.

### Phán quyết: chuỗi chốt (thay cho chữ `permission_level` ở `design.md:175,184`)

```
L0: chỉ phân loại phiếu mới vào Log, không ghi gì lên phiếu. L1: đọc dữ liệu, ghi phân loại, gợi ý lên phiếu, bình luận. Từ L2: ghi ERP ngoài phiếu qua đề xuất hoặc dòng Tự làm. L3: mức của công cụ bản ghi chung, sửa code. Mức thực tế của từng phiếu trên đường danh mục trắng không vượt Mức tối đa của đầu mục; năm quyền mở rộng tính theo ô này. Vượt ngân sách tháng thì tự hạ về L1 (L0 giữ nguyên).
```

Đo bằng lệnh (`python3 -I -c`, chỉ đọc, không chạm site), dán nguyên kết quả:

```
chữ cũ aef271c:  400 True            # len, NFC (đọc từ erp_ai_setting.json qua git show)
chuỗi chốt:      len 399 NFC True utf8_bytes 523
missing []                           # 14 cụm `phrases` bên dưới, so không phân biệt hoa thường như test
forbidden_found []                   # FORBIDDEN_PHRASES["ERP AI Setting"]["permission_level"] của 7fbd1b3
```

Chuỗi này trùng chuỗi reviewer đề nghị ở `review-64.md:60` (reviewer đếm tay ~399, nay đã đo: 399).

### Đối chiếu từng vế với chữ đã duyệt (`aef271c`)

| Vế cũ (`aef271c`) | Vế mới | Chữ bỏ | Hành vi |
|---|---|---|---|
| "L0: chỉ phân loại phiếu mới, ghi vào Log, không sửa phiếu, không trả lời bình luận." | "L0: chỉ phân loại phiếu mới vào Log, không ghi gì lên phiếu." | ", ghi"; "sửa phiếu, không trả lời bình luận" (gộp thành "ghi gì lên phiếu") | Giữ. "không ghi gì lên phiếu" bao cả không sửa phiếu và không bình luận (bình luận là ghi lên phiếu); đúng sửa đề nghị của `review-64.md:45` ("viết L0 rõ là không ghi gì lên phiếu"). |
| "L1: đọc dữ liệu, ghi phân loại hoặc gợi ý lên phiếu, đăng bình luận." | "L1: đọc dữ liệu, ghi phân loại, gợi ý lên phiếu, bình luận." | "hoặc" (→ ","), "đăng" | Giữ, kể cả "đọc dữ liệu". |
| "L2 có công cụ như L1." | (bỏ) | cả câu | Bỏ theo Returns T64 / `spec-addendum-3.md:88`; câu này nằm trong `FORBIDDEN_PHRASES`. |
| (không có) | "Từ L2: ghi ERP ngoài phiếu qua đề xuất hoặc dòng Tự làm." | — | Câu L2 mới ("Từ L2" = L2 trở lên). |
| "L3: mức của công cụ bản ghi chung, sửa code." | nguyên văn | — | Giữ (finding vòng 1 đã đạt). |
| "Mức thực tế của từng phiếu trên đường danh mục trắng không vượt Mức tối đa của đầu mục; năm quyền mở rộng tính theo ô này." | nguyên văn | — | Giữ (câu `design.md:184`). |
| "Chi vượt ngân sách tháng thì tự hạ về L1 (L0 giữ nguyên)." | "Vượt ngân sách tháng thì tự hạ về L1 (L0 giữ nguyên)." | "Chi" | Giữ, kể cả "tự" (tự động) và "(L0 giữ nguyên)". |

Tổng chữ bỏ: ", ghi" (vế L0), "sửa phiếu, không trả lời bình luận" (gộp thành "ghi gì lên phiếu"), "hoặc" và "đăng" (vế L1), "Chi" (vế ngân sách), cả câu "L2 có công cụ như L1.". Không vế hành vi nào mất.

### `phrases` của `permission_level` (thay bộ hiện có ở `7fbd1b3:test_doctype_descriptions.py:32-43`)
- Giữ 10 cụm đang có: `"L0"`, `"L1"`, `"L2"`, `"L3"`, `"ngân sách"`, `"đề xuất"`, `"Tự làm"`, `"L3: mức của công cụ bản ghi chung"`, `"tự hạ về L1"`, `"Mức thực tế của từng phiếu"`.
- Thêm 4 cụm: `"đọc dữ liệu"`, `"không ghi gì lên phiếu"`, `"Từ L2: ghi ERP ngoài phiếu"`, `"(L0 giữ nguyên)"`.
- `FORBIDDEN_PHRASES["ERP AI Setting"]["permission_level"]` giữ nguyên: `("ô Cho phép sửa code", "L2 có công cụ như L1")`.

### Dòng task T64 (dán thay dòng Returns và Expect; các dòng khác giữ)

```
  - Returns: mô tả `catalog_rules` giữ như `7fbd1b3` (385 ký tự, đã đạt hai vòng). Mô tả `permission_level` là ĐÚNG NGUYÊN VĂN chuỗi ở `design-w1-fixes-1.md` Điểm 1 (399 ký tự), không đổi một chữ; chuỗi này thay chữ `permission_level` ở `design.md:175,184`. `phrases` của `permission_level` = 10 cụm hiện có + `"đọc dữ liệu"`, `"không ghi gì lên phiếu"`, `"Từ L2: ghi ERP ngoài phiếu"`, `"(L0 giữ nguyên)"`; `FORBIDDEN_PHRASES` không đổi. Cụm bắt buộc của `catalog_rules` giữ như `7fbd1b3`.
  - Expect: vòng 3/3 trên `7fbd1b3`: thêm 4 cụm vào `phrases` trước → `test_required_phrases_present` đỏ (`ERP AI Setting: thiếu cụm`, ít nhất "đọc dữ liệu", "không ghi gì lên phiếu", "Từ L2: ghi ERP ngoài phiếu"); dán chuỗi → `test_doctype_descriptions` và `test_erp_ai_setting` xanh sau `cmd.migrate`. Scoped re-review `7fbd1b3..HEAD`: diff `erp_ai_setting.json` chỉ dòng `description` của `permission_level`.
```

---

## Điểm 2 — T65: biến thể khoảng trắng của tên vai trò cấm viết

### Hiện trạng (dữ kiện, theo đo của dev ở round 73, `tasks.md:583`)
- Biến thể có dấu và khác hoa thường đã bị từ chối sẵn ở mọi đường: `_stored_name` (`site_api.py:107-110`) tra tên lưu qua collation của DB, rồi `_named_in` so `casefold`.
- Biến thể khoảng trắng đầu/cuối: vẫn `ok=false`, bản ghi không đổi, nhưng lý do từ chối là kiểm tra Link của Frappe khi lưu (`hệ thống từ chối: Could not find Row #1: Role:   System Manager`), không phải chốt của ta (`_values_refusal`, `site_api.py:174-180`). Không có lỗ quyền hôm nay, nhưng việc chặn dựa vào hành vi của framework chứ không phải kiểm tra ở biên của công cụ.
- Phép chuẩn hóa của T12 (`erp_ai_setting.py:516`) không import được từ `erp_ai.agent` (`LAYER_RULES`) → nhánh "không chép hàm" của Returns cũ đúng.
- User trên bản Frappe này không có trường `role_profiles` → `_values_refusal` trả `DocType không có trường: role_profiles` ở vòng kiểm trường (`site_api.py:167-169`), trước bước vai trò.

### Phán quyết: chọn (a), `.strip()` chỉ trong `_wanted_roles`
1. Lý do chọn (a), không chọn (b): STD-SEC-4 đòi kiểm quyền ở biên của công cụ; với (b), việc chặn " System Manager" phụ thuộc kiểm tra Link của Frappe, một bản Frappe sau mà tự cắt khoảng trắng khi lưu Link thì vai trò cấm được gán qua công cụ. (a) đóng việc đó tại chốt của ta, sửa 2–3 dòng, cục bộ, không đụng `LAYER_RULES`, và cho đúng chữ lỗi hiện có mà Returns cũ đã hứa.
2. Phạm vi sửa: chỉ `_wanted_roles` (`site_api.py:149-162`). Mỗi tên vai trò (`row.get("role")`) và mỗi tên Role Profile (`values.get("role_profile_name")`, `row.get("role_profile")`) mà là `str` thì `.strip()` trước khi tra (`_profile_roles`) và trước khi trả; giá trị không phải `str` giữ nguyên (`_stored_name` đã bỏ qua chúng, nhánh hình dạng sai trả `None` không đổi).
3. Không sửa `_stored_name` (dùng chung cho tên DocType và tên User ở 7 chỗ gọi khác: `site_api.py:307`, `:321`, `:327`, `:356`, `:375`, `:502`, `:532`), `_named_in`, `_profile_roles`. Không đổi `values` được ghi xuống DB: với vai trò không cấm có khoảng trắng, chốt của ta cho qua và Frappe vẫn từ chối như hôm nay (hành vi giữ nguyên).
4. Hệ quả phụ chấp nhận: đường Role Profile (`doctype == ROLE_PROFILE_DOCTYPE`, dòng `roles`) đi qua cùng `_wanted_roles` nên cũng được phủ; không cần test riêng ngoài phạm vi T65.
5. `role_profiles`: không thêm mã; subTest khẳng định `ok=false` với chữ `DocType không có trường: role_profiles` (ghi lại sự thật của bản Frappe này; bản sau có trường đó thì test đỏ và lộ ra để xét lại).

### Dòng task T65 (dán thay dòng Returns và Expect; các dòng khác giữ)

```
  - Returns: ở chế độ thường, `create_record`/`update_record` trên User với tên vai trò cấm viết biến thể (có dấu, khác hoa thường, khoảng trắng đầu, khoảng trắng cuối) qua `roles` hoặc `role_profile_name` → `ok=false`, chữ lỗi `vai trò không được gán qua công cụ: <tên lưu>`, bản ghi không đổi. Sửa duy nhất trong `site_api._wanted_roles`: tên vai trò (`row.get("role")`) và tên Role Profile (`role_profile_name`, `row.get("role_profile")`) là `str` thì `.strip()` trước khi tra và trả; giá trị không phải `str` giữ nguyên. Không sửa `_stored_name`, `_named_in`, `_profile_roles`; không đổi `values` ghi xuống. `role_profiles` trên User: không có trường ở bản Frappe này → `ok=false`, `DocType không có trường: role_profiles` (nhánh có sẵn, không thêm mã). `ctx.unrestricted` giữ hành vi. Không import `erp_ai.erp_ai_agent`, không chép `user_template_error` (theo `design-w1-fixes-1.md` Điểm 2).
  - Expect: `TestForbiddenRoleSpelling::test_variant_spellings_refused` (subTest: có dấu, hoa thường, khoảng trắng đầu, khoảng trắng cuối × `roles`, `role_profile_name` × `create_record`, `update_record`; mỗi subTest khẳng định `ok=false`, đúng chữ lỗi trên, bản ghi không đổi) đỏ trước ở các subTest khoảng trắng (round 73 đã đo `FAILED (failures=4)`, chữ lỗi `hệ thống từ chối: Could not find Row #1: Role: ...`); các subTest có dấu, hoa thường xanh ngay và ở lại làm hồi quy. Thêm subTest `role_profiles` khẳng định `ok=false`, `DocType không có trường: role_profiles`. Sau `.strip()`: cả file `erp_ai/agent/tools/test_site_api.py` xanh.
```

---

## Điểm 3 — T67: ba test vượt ngân sách của runner không đọc `spent_this_month_usd` và không phụ thuộc dòng Log sống

### Hiện trạng (dữ kiện)
- Sau T67, runner (`runner.py:164` trên `team/FEAT-007`: `level = policy.effective_level(settings)`) gọi `policy.is_over_budget(settings)` → `month_spend_usd()` → `SUM(cost_usd)` của ERP AI Log tháng hiện tại trên site dùng chung (`design-addendum-1-U1.md:123-124`).
- `TestRunnerChangeGrant` (`test_agent_runner.py:2749`) làm vượt ngân sách bằng `spent_this_month_usd=10.01` (`:2787`, `:2804`) và ca bằng ngân sách bằng `spent_this_month_usd=10` (`:2837`); ca bằng hiện xanh chỉ nhờ tổng log thật của tháng ≤ 10 USD → phụ thuộc dữ liệu sống (STD-TEST-6).
- Rộng hơn ba test: sau T67, MỌI test runner ở L1 trở lên đọc tổng log sống: các lớp đặt `monthly_budget_usd=1000` (`:1201`, `:1440`, `:1804`, `:2180`, `:2669`, `:2760`, `:2899`) chỉ xanh khi tổng tháng ≤ 1000; `RunnerTestBase.setUp` (`:91-118`) không đặt ngân sách nên các lớp khác đọc ngân sách đang lưu trên site. Trước T67 các test này độc lập vì đọc `spent_this_month_usd` do test đặt; T67 tự tạo ra sự phụ thuộc này.

### Phán quyết
1. **Đường nối (seam) duy nhất: `policy.month_spend_usd`.** `is_over_budget` gọi `month_spend_usd(now)` qua tên toàn cục của module `policy` (không gán bí danh, không bắt làm tham số mặc định), để test vá được bằng `patch.object(policy, "month_spend_usd", ...)`. Đây là ràng buộc Returns của T67.
2. **`RunnerTestBase.setUp` vá `policy.month_spend_usd` trả `0.0`** (một patcher, `start` + `addCleanup(stop)`, giữ trong `self.month_spend`). Mọi test runner vì thế không đọc dòng Log sống cho ngân sách. Đây là phần nối rộng thêm của phán quyết của team-leader "chỉ ba test": cần đúng một patcher trong `RunnerTestBase.setUp` cùng file, không sửa test nào khác. Thiếu nó thì T67 để lại phụ thuộc dữ liệu sống ở mọi lớp test runner (STD-TEST-6) → designer chốt là bắt buộc.
3. **Ba test `test_over_budget_*`:** bỏ `spent_this_month_usd` khỏi lời gọi `set_agent_settings` (giá trị `0` của `setUp` lớp giữ nguyên, nên test chứng minh luôn runner không đọc trường đó); đặt `monthly_budget_usd=10` và `self.month_spend.return_value`:
   - `test_over_budget_l3_drops_change_tools`: `10.01` → giữ mọi khẳng định hiện có (`effective_level == "L1"`, `change_enabled is True`, không công cụ đổi, không khối `CHANGE_TOOLS_BLOCK`); thêm `self.month_spend.assert_called()` (chứng minh runner đi qua seam).
   - `test_over_budget_l3_keeps_unrestricted_tools`: `10.01`, `unrestricted_enabled=1` → giữ mọi khẳng định hiện có.
   - `test_over_budget_edge_spent_equal_to_budget_keeps_change_tools`: `10.0` → giữ khẳng định hiện có (đủ `CHANGE_TOOL_NAMES`, có `CHANGE_TOOLS_BLOCK`).
4. **Ca bằng ngân sách Ở LẠI mức runner** (chỉ nguồn số bị vá, phép so `>` thật của `is_over_budget` vẫn chạy qua runner), **và thêm một test cùng biên ở `test_policy`** (`TestBudget::test_spend_equal_to_budget_is_not_over`), nơi luật `>` sống.
5. **Test của `test_policy` cũng không phụ thuộc dòng sống:** mọi test gọi `month_spend_usd`/`is_over_budget` truyền `now` cố định trong một tháng không có dòng thật (`2001-02-15 12:00`); dòng ERP AI Log gieo có `creation` đặt trong tháng đó (ghi DB trực tiếp trong transaction của test, rollback ở cleanup, không commit), thêm một dòng ở `2001-01-31 23:59:59` và một dòng ở `2001-03-01 00:00:00` để khẳng định biên nửa mở `[start, end)`; giá trị `cost_usd` biểu diễn chính xác (ví dụ `4.0 + 6.0 = 10.0`). `settings` là `frappe._dict` dựng trong test, không đọc single của site.
6. **STD-TEST-5:** ba test cũ của `effective_level(settings)` mà nhánh `5e5d1f4` đã xóa phải được viết lại theo chữ ký mới, không xóa trắng: L3 + `over_budget=True` → `L1`; L0 + `over_budget=True` → `L0`; L2 + `over_budget=False` → `L2`. Reviewer đối chiếu ca cũ ↔ ca mới.
7. Đã do team-leader chốt, ghi lại: `erp_ai/agent/test_agent_runner.py` vào `files:` của T67; T72 thêm `depends: T67`.

### Dòng task T67 (dán thay dòng tiêu đề, Receives, Returns, Expect; Tiêu chí giữ)

```
- [ ] T67 — `policy`: ngân sách tính từ ERP AI Log sống — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py, erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_policy.py — depends: T66
  - Receives: cột `cost_usd` của ERP AI Log; `runner.py:164` (`level = policy.effective_level(settings)`, `team/FEAT-007`); `RunnerTestBase.setUp` (`test_agent_runner.py:91-118`) và ba test `TestRunnerChangeGrant.test_over_budget_*` (`:2786-2840`).
  - Returns: `month_spend_usd(now=None) -> float`, `is_over_budget(settings, now=None) -> bool`, `effective_level(settings, *, over_budget: bool) -> str` theo `design-addendum-1-U1.md:110-112`, `:123-125`; `is_over_budget` gọi `month_spend_usd(now)` qua tên toàn cục của module (để test vá được), không đọc `spent_this_month_usd`. `runner.py`: đúng một lời gọi đổi (`runner.py:164`) thành `policy.effective_level(settings, over_budget=policy.is_over_budget(settings))`; không sửa gì khác trong runner. `test_agent_runner.py`: chỉ (1) một patcher `policy.month_spend_usd` trả `0.0` trong `RunnerTestBase.setUp`, giữ ở `self.month_spend`; (2) ba test `test_over_budget_*` bỏ `spent_this_month_usd`, đặt `monthly_budget_usd=10` và `self.month_spend.return_value` = `10.01` (`drops_change_tools`, `keeps_unrestricted_tools`) hoặc `10.0` (`edge_spent_equal_to_budget_keeps_change_tools`); khẳng định hiện có giữ nguyên, `drops_change_tools` thêm `self.month_spend.assert_called()`. Không sửa test runner nào khác (theo `design-w1-fixes-1.md` Điểm 3).
  - Expect: `TestBudget::test_month_spend_sums_live_log_rows`, `::test_over_budget_reads_log_not_spent_field`, `::test_over_budget_caps_permission_level_at_l1`, `::test_spend_equal_to_budget_is_not_over` đỏ trước rồi xanh; mọi test của `TestBudget` gọi `month_spend_usd`/`is_over_budget` dùng `now` cố định `2001-02-15 12:00`, dòng gieo có `creation` trong tháng đó cộng hai dòng biên `2001-01-31 23:59:59` và `2001-03-01 00:00:00` (không tính), `settings` là `frappe._dict`, không commit. Ba test cũ của `effective_level(settings)` được viết lại theo chữ ký mới (L3+vượt → L1; L0+vượt → L0; L2+không vượt → L2), không xóa trắng (STD-TEST-5). `erp_ai/agent/test_agent_runner.py` xanh cả file, kể cả ba `TestRunnerChangeGrant.test_over_budget_*`, không phụ thuộc tổng ERP AI Log sống của site (STD-TEST-6). `test_architecture` xanh.
```

---

## Kiểm tra cuối
- Ba điểm, mỗi điểm một mục, mỗi mục có dòng task dán được nguyên văn; không còn lựa chọn mở.
- Không file mới ngoài tài liệu này (nằm dưới `docs/team/`). Không đổi đường dẫn nào trong `protected_paths`; touchpoint của ba task giữ trong `files:` hiện có, riêng T67 thêm `erp_ai/agent/test_agent_runner.py` (file có sẵn, team-leader đã chốt).
- Một điểm cần team-leader xác nhận lại phạm vi (không phải lựa chọn thiết kế): Điểm 3 mục 2 nới "chỉ ba test" thêm đúng một patcher trong `RunnerTestBase.setUp`.
