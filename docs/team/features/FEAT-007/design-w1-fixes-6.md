# FEAT-007 — design-w1-fixes-6: phán hẹp hai điểm (T82 luật `test_registry_has_one_grant_function`; T34 trần tập ứng viên)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu, không chặn build.
- Đầu vào: `tasks.md:177`, `:741-746` (T82, dòng "Chèn 8"), `:414-425` (T33, T34); `design-w1-fixes-3.md:109-110`; `review-33.md:44-70`; `design.md:74`, `:364-377` (D-16); `design-addendum-1-U1.md:161-166`, `:179-189`, `:263`, `:401`; `spec.md:178` (AC-16).
- Mã đọc (chỉ đọc, `git show`): `team/FEAT-007` @ `aedc360` — `erp_ai/tests/test_architecture.py:466-476` (`dotted_name`), `:494-498` (`resolved_name`), `:3690-3705`, `:3870-3973`, `:4983-4986`, `:7990-7998` (`changed`), `:8097-8204`, `:8375-8411`; `erp_ai/agent/tools/registry.py` (danh sách hàm), `erp_ai/agent/runner.py:25-28`, `:44-50`, `:602-611`. `team/FEAT-007-task-33` @ `86683d7` — `erp_ai/agent/missed_scan.py`, `erp_ai/agent/test_missed_scan.py:51-73`, `:151-163`.
- Không đổi kiến trúc: theo ADR-023 Ràng buộc (một bảng cấp, một hàm cấp, một lời gọi schema của runner), ADR-030 QĐ 3 (cờ khối nằm trong `Grant`), ADR-003 (nhóm loại trừ, opt-out chỉ qua `policy.can_send_ticket`, không đọc trong SQL), ADR-033 QĐ 2 (xếp lại như trigger tạo phiếu). Không đổi quy tắc nghiệp vụ: AC-16 giữ nguyên chữ.

---

## Điểm 1 — T82: các chỗ sửa của `erp_ai/tests/test_architecture.py`

### Hiện trạng (dữ kiện)
- `:3695` `SCHEMA_FUNCTION = "get_tool_schemas"` dùng cho HAI việc khác nhau: (a) là phần tử của `SPEC_CONSUMERS` (`:3700`) — hàm cấp cao nhất của `registry.py` phải tồn tại và gọi hàm cấp (`_grant_path_violations`, `:3899-3907`); (b) là tên DUY NHẤT được phép trong danh sách lời gọi có chữ "schema" của `runner.py` (`:3961-3971`), và `test_registry_has_one_grant_function` (`:4985`) còn `assertIn(f"{SCHEMA_FUNCTION}(", runner)`.
- Sau T82, (a) vẫn đúng với `get_tool_schemas`: hàm còn, chữ ký `(inputs: GrantInputs)`, thân `grant(inputs).schemas()` (`U1.md:162`), `tools/__init__.py` xuất lại. Chỉ (b) đổi: runner gọi `granted.schemas()` (`U1.md:263`). `dotted_name` cho `granted.schemas` → `"granted.schemas"`, cho `grant(x).schemas` → `"grant().schemas"`; `rpartition(".")[2]` cả hai là `"schemas"`.
- Vì thế đổi giá trị `SCHEMA_FUNCTION` thành `"schemas"` (cách đọc chữ của quyết định 07:21 (b)) là SAI: `SPEC_CONSUMERS` sẽ đòi hàm cấp cao nhất `schemas` trong `registry.py` (không có; `schemas` là phương thức của `Grant`) → vi phạm "`schemas` missing" trên mã thật.
- Nguồn giả `GRANT_CLEAN` (`:8375-8411`) và các ca của `test_registry_one_grant_function_clean` / `_caught` (`:8097-8204`) chép chữ `get_tool_schemas(*grant)` và `_granted_specs(level))` của `_grants_group`. `changed` (`:7990-7998`) `assert replace[0] in source`, nên mọi chuỗi thay thế cũ phải đổi cùng nguồn giả, nếu không test vỡ bằng `AssertionError`.
- Ba chỗ đỏ ngay sau T82 nếu chỉ sửa theo 07:21 (b): `_grants_group missing` (`:3899-3903`), `schema calls [...]` (`:3967`), `assertIn` (`:4985`); cộng các ca giả nói trên khi luật đổi.

### Phán: tách nghĩa (b) ra một hằng mới, giữ nghĩa (a)
Ý nghĩa của luật sau T82 giữ nguyên: một bảng cấp, một hàm cấp (`grant`), mọi hàm tiêu thụ spec còn lại (`get_tool_schemas`, `execute_tool`) đi qua nó; runner lấy danh sách tool đúng một lần, bằng `.schemas()` của `Grant`, và không quay về `get_tool_schemas`. `_grants_group` bị xóa nên ra khỏi danh sách tiêu thụ; cờ khối nay nằm trong `Grant` (ADR-030 QĐ 3), luật đầy đủ về cờ là của T83.

Danh sách sửa ĐẦY ĐỦ (số dòng ở `team/FEAT-007` @ `aedc360`; T80 có thể dịch dòng, tìm theo chữ). Không chỗ nào khác của file đổi.

| # | Chỗ | Cũ | Mới |
|---|---|---|---|
| E1 | hằng, sau `:3696` (`SCHEMA_CALL_MARK = "schema"`) | — | thêm dòng `RUNNER_SCHEMA_CALL = "schemas"`; `:3695` `SCHEMA_FUNCTION = "get_tool_schemas"` GIỮ NGUYÊN |
| E2 | `:3700` | `SPEC_CONSUMERS = (SCHEMA_FUNCTION, "_grants_group", "execute_tool")` | `SPEC_CONSUMERS = (SCHEMA_FUNCTION, "execute_tool")` |
| E3 | docstring `check_registry_has_one_grant_function`, dòng 2-3 (`:3913-3914`) | `` removed names `_unrestricted_specs`, `get_unrestricted_tool_schemas` exist nowhere; runner.py calls one`` / `` schema function, `get_tool_schemas`, once."""`` | `` removed names `_unrestricted_specs`, `get_unrestricted_tool_schemas` exist nowhere; runner.py makes one`` / `` schema call, `.schemas()` on the Grant (U1), once."""`` |
| E4 | thân luật runner `:3967` | `if [name for _node, name in schema_calls] != [SCHEMA_FUNCTION]:` | `if [name for _node, name in schema_calls] != [RUNNER_SCHEMA_CALL]:` |
| E5 | thân luật runner `:3970` | `f"exactly one {SCHEMA_FUNCTION}() call (ADR-023)"` | `f"exactly one .{RUNNER_SCHEMA_CALL}() call on the grant (ADR-023)"` |
| E6 | `test_registry_has_one_grant_function` `:4985` | `self.assertIn(f"{SCHEMA_FUNCTION}(", self.sources[RUNNER_FILE])` | `self.assertIn(f".{RUNNER_SCHEMA_CALL}()", self.sources[RUNNER_FILE])` |
| E7 | `GRANT_CLEAN[REGISTRY_FILE]` `:8395-8398` | khối `def _grants_group(group, level):` + `return any(spec.group == group for spec in _granted_specs(level))` + 2 dòng trống | xóa cả khối (4 dòng) |
| E8 | `GRANT_CLEAN[RUNNER_FILE]` `:8403-8408` | `from erp_ai.agent.tools.registry import {SCHEMA_FUNCTION}` … `def run(grant):` / `return {SCHEMA_FUNCTION}(*grant)` | `from erp_ai.agent.tools.registry import grant` … `def run(inputs):` / `granted = grant(inputs)` / `return granted.{RUNNER_SCHEMA_CALL}()` (giữ 2 dòng trống sau import, tab thụt như cũ) |
| E9 | `test_registry_one_grant_function_clean` `:8099-8104` (ca `aliased`) | `replace=("import get_tool_schemas\n", "import get_tool_schemas as schemas\n")` và `.replace("return get_tool_schemas(", "return schemas(")` | `replace=("import grant\n", "import grant as issue\n")` và `.replace("granted = grant(", "granted = issue(")` |
| E10 | cùng test, ngay sau `self.assertEqual(check_registry_has_one_grant_function(aliased), [])` | — | thêm ca sạch `chained = self.changed(GRANT_CLEAN, RUNNER_FILE, replace=("\tgranted = grant(inputs)\n\treturn granted.", "\treturn grant(inputs)."))` rồi `self.assertEqual(check_registry_has_one_grant_function(chained), [])` |
| E11 | `_caught`, ca `"second schema call"` `:8139-8143` | extra `"\n\ndef again(grant):\n\treturn get_tool_schemas(*grant)\n"` | extra `"\n\ndef again(granted):\n\treturn granted.schemas()\n"` |
| E12 | ca `"other schema function"` `:8144-8148` | `("return get_tool_schemas(*grant)", "return registry.schemas_for(*grant)")` | `("return granted.schemas()", "return registry.schemas_for(inputs)")` |
| E13 | ca `"no schema call"` `:8149` | `("return get_tool_schemas(*grant)", "return []")` | `("return granted.schemas()", "return []")` |
| E14 | ngay sau ca `"no schema call"` | — | thêm ca `"runner back on the legacy schema function": (RUNNER_FILE, "", ("return granted.schemas()", f"return {SCHEMA_FUNCTION}(inputs)")),` |
| E15 | ca `"_grants_group skips the grant function"` `:8178-8182` | 5 dòng của ca | xóa (chuỗi `for spec in _granted_specs(level))` không còn trong nguồn giả sau E7) |

Ghi chú cho dev và reviewer:
- Nguồn giả là "hình dạng", không chạy: hàm cấp của `GRANT_CLEAN[REGISTRY_FILE]` vẫn tên `_granted_specs` (luật tìm hàm cấp theo người đọc `GRANT_TABLE`, không theo tên), còn runner giả import `grant`. Không đổi tên `_granted_specs` trong nguồn giả: sẽ kéo theo chuỗi thay thế của ba ca khác (`"no grant function"`, `"spec source listed outside the grant function"`, `"execute_tool skips the grant function"`), ngoài danh sách trên.
- Không thêm `_grants_group`, `grants_change_tools`, `grants_site_admin_tools`, `grants_unrestricted_tools`, `_legacy_inputs` vào `REMOVED_GRANT_NAMES`: runner không gọi `grants_*` là luật `test_runner_takes_tools_and_flags_from_grant` của T83 (`U1.md:401`); T82 không thêm luật.
- Ca E14 giữ đúng nghĩa cũ của luật theo hướng mới: runner chỉ có một đường lấy tool, quay về `get_tool_schemas` là vi phạm.

### Dòng "Chèn 8" thay thế cho T82 (dán nguyên văn, thay dòng `tasks.md:743`)
```
  - Chèn 8 (quyết định 07:21 (b) của team-leader, sửa theo `design-w1-fixes-6.md` Điểm 1; file thứ tám của `files:`): T82 thêm `erp_ai/tests/test_architecture.py` vào `files:` và sửa ĐÚNG 15 chỗ E1..E15 của bảng `design-w1-fixes-6.md` Điểm 1, không chỗ nào khác: thêm hằng `RUNNER_SCHEMA_CALL = "schemas"` (giữ `SCHEMA_FUNCTION = "get_tool_schemas"` vì `get_tool_schemas` vẫn là hàm tiêu thụ spec, `U1.md:162`); `SPEC_CONSUMERS` bỏ `"_grants_group"`; luật runner, chữ lỗi, docstring và `assertIn` của `test_registry_has_one_grant_function` so với `RUNNER_SCHEMA_CALL` (hệ quả `design-addendum-1-U1.md:263`); `GRANT_CLEAN` bỏ `_grants_group`, runner giả gọi `granted = grant(inputs)` / `granted.schemas()`; ca sạch `aliased` đổi sang `grant as issue`, thêm ca sạch `chained`; ca đỏ `"second schema call"`, `"other schema function"`, `"no schema call"` đổi chuỗi theo runner giả mới, thêm ca `"runner back on the legacy schema function"`, xóa ca `"_grants_group skips the grant function"`. Đỏ trước: trên mã T82 (registry, runner đã đổi), chưa sửa file này, `cmd.test_one` `erp_ai/tests/test_architecture.py` FAILED ở `test_registry_has_one_grant_function` (`_grants_group missing`, `schema calls`, `assertIn`); sau 15 chỗ → cả file xanh. Reviewer kiểm diff của file chỉ có 15 chỗ này. Chuỗi chủ file: … T80 → T82 → T83 …; T83 vẫn giữ ba luật mới của nó.
```
Thêm vào cuối dòng `Expect:` của T82 (`tasks.md:746`), trước "Chèn 6": `` `cmd.test_one` xanh cả file `erp_ai/tests/test_architecture.py` (Chèn 8). ``

---

## Điểm 2 — T34: trần của tập ứng viên (D-16, mốc 300 s)

### Hiện trạng (dữ kiện)
- `missed_scan.py` @ `86683d7`: `CANDIDATES_SQL` không có `LIMIT`, `order by t.creation asc, t.name asc`; `find_missed_tickets` duyệt từng tên, gọi `policy.can_send_ticket(name)` và `policy.runs_today(name, now)`, dừng khi đủ `SCAN_BATCH = 50`.
- Phiếu nhóm loại trừ hoặc có cờ opt-out không bao giờ có dòng `classify`, nên nằm trong kết quả SQL tới khi `Resolved` hoặc đủ 3 trường phân loại. Vì thứ tự tăng, mỗi lượt quét xét lại toàn bộ khối phiếu kẹt cũ TRƯỚC phiếu mới. Lượng việc mỗi lượt = số phiếu kẹt đang mở × (2 lời gọi policy), không có trần → mốc 300 s của hàng `default` (D-16, R-5) không được bảo đảm; tệ hơn, phiếu MỚI (đúng đối tượng của G1 "mốc 5 phút") bị xếp sau.
- Phiếu chạm `max_runs_per_ticket_per_day` tự ra khỏi tập trong ngày và quay lại hôm sau: đúng AC-16 ("đã dùng hết số lần chạy trong ngày"), không phải lỗi.
- Không lọc được nhóm loại trừ / opt-out trong SQL: ADR-003 chỉ cho đọc qua `policy.can_send_ticket`.
- AC-16 (`spec.md:178`) không có giới hạn tuổi phiếu: "xếp hàng đúng các phiếu: tạo sau khi agent bật, chưa có dòng phân loại thành công, tạo quá 5 phút", và phiếu bỏ cờ opt-out sau đó phải được xếp. Cắt theo tuổi (cửa sổ N giờ/ngày) là đổi quy tắc nghiệp vụ → KHÔNG chọn.

### Phán (bổ sung D-16; `design.md:368` đọc thêm vế "trong cửa sổ ứng viên mới nhất")
1. **Trần truy vấn:** hằng mới `SCAN_CANDIDATE_LIMIT = 1000`. `CANDIDATES_SQL` thêm `limit %(limit)s` ở cuối; tham số `"limit": SCAN_CANDIDATE_LIMIT` đọc lúc gọi (không nhúng vào f-string, để test vá được).
2. **Thứ tự:** SQL đổi thành `order by t.creation desc, t.name desc` (lấy 1000 ứng viên MỚI nhất); `find_missed_tickets` duyệt `reversed(candidates)` (tức `creation` tăng, `name` tăng trong cửa sổ), giữ nguyên điều kiện lọc và chỗ dừng ở `SCAN_BATCH`. Đầu ra không đổi: tối đa 50 tên, cũ nhất trước, phiếu bị từ chối không chiếm chỗ. Chữ ký `find_missed_tickets(now: datetime) -> list[str]` không đổi.
3. **Phiếu kẹt ra khỏi tập thế nào:** không cắt theo tuổi. Phiếu không đủ điều kiện ra khỏi tập ứng viên khi `Resolved`, đủ 3 trường, hoặc có dòng `classify` thành công (như nay); và ra khỏi phần được XÉT khi có từ `SCAN_CANDIDATE_LIMIT` phiếu ứng viên mới hơn nó. Trong cửa sổ, phiếu bỏ cờ opt-out được xếp ở lượt kế (AC-16 đúng). Phiếu mới không bao giờ bị khối phiếu kẹt cũ chắn.
4. **Tín hiệu (STD quan sát được, đường mới):** khi `len(candidates) == SCAN_CANDIDATE_LIMIT`, `find_missed_tickets` ghi đúng một dòng `frappe.logger(LOGGER_NAME).warning("missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét", SCAN_CANDIDATE_LIMIT)` (`LOGGER_NAME` từ `erp_ai.constants`, như `runner.py:44-50`). Dòng info của D-17 (`"missed_scan: xếp {n} phiếu"`) vẫn đúng một dòng mỗi lượt; dòng warning chỉ có ở lượt bất thường.
5. **Ngân sách 300 s:** mỗi lượt ≤ 1 truy vấn ứng viên + ≤ 1000 × (`can_send_ticket` + `runs_today`) + ≤ 50 `enqueue_agent_run`. Giả định (chưa đo): ≤ 20 ms cho một ứng viên → ≤ 20 s, dư ≥ 10 lần so với 300 s. Phép đo EXPLAIN (`creation` của `tabHD Ticket`) và thời gian một lượt với ~1000 ứng viên ở lại `/team:verify` (đã ghi ở `review-33.md:65`, `:70`).

### T33 có cần task tiếp không? KHÔNG.
T33 merge như đã duyệt (`team/FEAT-007-task-33` @ `86683d7`). Thay đổi nằm trong T34: `files:` của T34 đã có `erp_ai/agent/missed_scan.py` và `erp_ai/agent/test_missed_scan.py`, và `depends: T33`. Tám test của T33 giữ nguyên chữ và phải còn xanh sau T34 (`test_batch_limit_oldest_first` vẫn đúng: 52 phiếu của test nằm trong cửa sổ 1000).

### Dòng T34 thay thế (dán nguyên văn, thay ba dòng `tasks.md:423-425`)
```
  - Receives: `find_missed_tickets`, `CANDIDATES_SQL`, `SCAN_BATCH` (T33); `queue.enqueue_agent_run(ticket, trigger)`, `TRIGGER_TICKET_INSERT`, `policy.is_enabled()`, `LOGGER_NAME` của `erp_ai.constants` (hiện có); `hooks.py` sau T40; trần ứng viên theo `design-w1-fixes-6.md` Điểm 2.
  - Returns: `scan_missed_tickets(now: datetime | None = None) -> None`; dòng `"*/15 * * * *": ["erp_ai.agent.missed_scan.scan_missed_tickets"]` trong `hooks.py`. Trần ứng viên (`design-w1-fixes-6.md` Điểm 2, bổ sung D-16): hằng `SCAN_CANDIDATE_LIMIT = 1000`; `CANDIDATES_SQL` đổi `order by t.creation asc, t.name asc` thành `order by t.creation desc, t.name desc` và thêm `limit %(limit)s`, tham số `"limit": SCAN_CANDIDATE_LIMIT` đọc lúc gọi; `find_missed_tickets` duyệt `reversed(candidates)`, điều kiện lọc, chỗ dừng `SCAN_BATCH`, chữ ký và thứ tự đầu ra không đổi; khi `len(candidates) == SCAN_CANDIDATE_LIMIT` ghi đúng một dòng `frappe.logger(LOGGER_NAME).warning("missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét", SCAN_CANDIDATE_LIMIT)`. Không cắt theo tuổi phiếu (AC-16 không có giới hạn tuổi), không lọc nhóm loại trừ/opt-out trong SQL (ADR-003).
  - Expect: `TestMissedScan::test_two_scans_one_job_per_ticket`, `::test_agent_disabled_noop`, `::test_cron_declared_every_15_minutes` xanh. Trần ứng viên, test viết trước, đỏ trên mã T33: `::test_candidate_window_keeps_the_newest` (vá `SCAN_CANDIDATE_LIMIT` = 3, bốn phiếu đủ điều kiện a < b < c < d theo `creation` → `_found` = [b, c, d]; trên mã T33 ra [a, b, c, d]), `::test_old_refused_tickets_do_not_starve_a_new_one` (vá trần = 3, năm phiếu opt-out cũ hơn và một phiếu mới đủ điều kiện e, bọc `policy.can_send_ticket` bằng `wraps` → `_found` = [e] và `can_send_ticket` được gọi đúng 3 lần; trên mã T33 gọi 6 lần), `::test_warns_once_when_candidate_limit_reached` (vá trần = 3 và vá `missed_scan.frappe.logger`: ba phiếu ứng viên → `warning` gọi đúng một lần, chữ có `"chạm trần"`; hai phiếu → không gọi). Tám test của T33 (`test_constants`, `test_seven_ticket_kinds`, `test_runs_below_daily_limit_still_found`, `test_failed_run_requeued`, `test_predicted_category_on_other_entry_type_does_not_count`, `test_grace_edge_exactly_five_minutes`, `test_no_enabled_at_noop`, `test_batch_limit_oldest_first`) không sửa chữ và còn xanh. `cmd.test_one` xanh cả file `erp_ai/agent/test_missed_scan.py` và `erp_ai/tests/test_architecture.py`.
```
Dòng `Tiêu chí:` của T34 (`tasks.md:421`) thêm cuối: `; D-16 trần ứng viên (`design-w1-fixes-6.md` Điểm 2).`

---

## Kết
- Danh sách AC/NFR của hai điểm và test kiểm: AC-3 (luật ADR-023 sau T82) → `erp_ai/tests/test_architecture.py::test_registry_has_one_grant_function`, `::test_registry_one_grant_function_clean`, `::test_registry_one_grant_function_caught`; AC-16 + D-16 (trần, thứ tự, không chắn phiếu mới, tín hiệu) → `erp_ai/agent/test_missed_scan.py::TestMissedScan::test_candidate_window_keeps_the_newest`, `::test_old_refused_tickets_do_not_starve_a_new_one`, `::test_warns_once_when_candidate_limit_reached`, cộng tám test của T33 giữ nguyên; NFR-3 → `::test_two_scans_one_job_per_ticket` (không đổi).
- Touchpoint: chỉ file có sẵn trong `files:` của T82 (`erp_ai/tests/test_architecture.py`) và T34 (`erp_ai/agent/missed_scan.py`, `erp_ai/agent/test_missed_scan.py`). File mới duy nhất: tài liệu này, dưới `docs/` ∈ `allowed_new_file_roots` (`erp_ai`, `docs`, `.github`). `protected_paths` (`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`): không đường dẫn nào khớp.
- Giả định kỹ thuật nhóm tự quyết: `SCAN_CANDIDATE_LIMIT = 1000` và ước lượng ≤ 20 ms/ứng viên (đo ở `/team:verify`). Câu hỏi nghiệp vụ: 0.
- Không `DESIGN_CONFLICT`: Điểm 1 theo ADR-023, ADR-030 QĐ 3; Điểm 2 theo ADR-003, ADR-033 QĐ 2, AC-16 nguyên chữ.
