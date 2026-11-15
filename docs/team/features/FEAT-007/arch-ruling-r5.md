Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- G2 tắt cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Phán quyết kiến trúc: R-5 (thứ tự đơn vị trong `runner.py`) và nền của T56, FEAT-007

**Mục tiêu 1, R-5: nhận thứ tự của `plan-w1.md`, kèm điều kiện R5-1..R5-6.** U2 **không** phải đứng trước U4b và không vào đường tới U7. Trong `runner.py` thứ tự mới là U1 → U3 (T91, T92) → U4b → U2 (đợt 1b) → U6b. Điều kiện chính: lần phân loại lại của U4b đi qua đúng một chỗ parse, để khối "bị loại bởi phân loại" của U2 có đúng một chỗ đặt. Thêm nữa, `team/FEAT-007` không được merge vào `develop` khi đã có U4b mà chưa có U2.

**Mục tiêu 2, nền của T56: xác nhận quyết định (b) của team-leader lúc 00:59.** T56 gộp đầu `develop` (≥ `cf69b57`, có FEAT-004, FEAT-005, FEAT-006, CHG-001) một lần. T90 nhập vào T56. T91–T94 về chỗ trong U3, ngay sau U1. Không có lý do kiến trúc nào để giữ hai lần gộp: `arch-impact.md:185` vốn đã ghi "`team/FEAT-007` merge `develop` một lần"; hai lần gộp chỉ là cách tránh R-1, mà R-1 đã hết. Điều kiện R5-7..R5-12.

Không ADR nào đổi, không có amendment. Thứ tự của `arch-review-design-w1a.md` mục 4 (5), dòng 89-92, và của `design-addendum-1-U4b-U8-fixes.md:328` (U1 → U2 → U3 → U4b → U6b), cùng cụm "U1 (một mình) → U2 ∥ U3 → U4b" ở `arch-impact.md:185`, được file này thay, chỉ ở phần thứ tự. Vùng hàm của từng đơn vị ở các bảng đó giữ nguyên. File này không sửa ba file đó.

## Căn cứ (đọc trực tiếp ngày 2026-11-15, read-only; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Nền hôm nay | `develop` @ `cf69b57` chứa `4469287` (FEAT-004) và `464063f` (FEAT-005). `team/FEAT-007` @ `e920c08` chưa chứa `4469287`; merge-base `1918db2` | `git log`, `git merge-base` |
| FEAT-005 đổi gì so với `4469287` | 12 file: `runner.py` +134, `tasks.py` +205, `site_api.py` +76, `erp_ai_setting.{py,json}`, `test_erp_ai_setting.py` +46, `test_architecture.py` +762 (2 luật mới: `test_privilege_alert_reads_shared_generic_write_tools`, `test_privilege_alert_watermark_and_clock_rules`), `test_tasks.py`, `test_agent_runner.py`, `test_runner_routing.py`, `test_site_api.py`, `test_doctype_descriptions.py` | `git diff --stat 4469287 develop -- erp_ai` |
| `team/FEAT-007` đã sửa file ADR-024 chưa | **Chưa.** `runner.py`, `tasks.py`, `site_api.py`, `test_tasks.py`, `test_runner_routing.py`: 0 dòng đổi từ merge-base | `git diff --name-only 1918db2 team/FEAT-007 -- …` |
| Xung đột khi gộp, chạy thử bằng `git merge-tree` (không ghi cây làm việc) | Gộp `cf69b57`: `test_architecture.py` 2 khối, `erp_ai_setting.py` 2, `test_doctype_descriptions.py` 2, `erp_ai_setting.json` 1, `erp_ai/agent/tools/test_source.py` 1. Gộp `4469287`: chỉ `test_architecture.py` 2, `test_source.py` 1. Phần FEAT-005 thêm 5 khối, cả 5 nằm trong 3 file mà `files:` của T56 đã có; 0 khối ở `runner.py`, `tasks.py`. `test_agent_runner.py`, `test_erp_ai_setting.py`, `source.py` tự gộp được | `git merge-tree 1918db2 team/FEAT-007 {develop,4469287}` |
| Nếu giữ hai lần gộp | Lần gộp thứ hai (T90, sau T83) sẽ gặp phần FEAT-005 của `runner.py` (`_reason` vòng lượt `:641-702` với `REASON_TURN_SAVEPOINT`, `_undo_turn`; `_run_tool`, `_record_snapshot`, `_action` `:750-790`) chồng lên các dòng mà U1 T82 (`_reason`) đã sửa, và sau đó T91 (`_action`) cũng sửa | `develop:erp_ai/agent/runner.py:647`, `:675`, `:684`, `:765`; `tasks-w1.md:135-138` |
| Report `ERP AI Accuracy` | `develop` không đổi file nào của report từ merge-base, nên lần gộp không có xung đột ở đây. Chỗ lệch role là giữa bản ghi trên site và mã, việc của designer | `git diff --name-only 1918db2 develop -- erp_ai/erp_ai_agent/report/` = rỗng |
| Mốc ADR-024 trên Setting | `develop` `erp_ai_setting.py` thêm `read_privilege_watermark` và dòng khôi phục `privilege_alert_checked_until` trong lúc lưu (ADR-024 QĐ 3.2); nhánh FEAT-007 có `restore_self_managed_fields` (`:141`) | `git diff 4469287 develop -- …/erp_ai_setting.py` |
| Số dòng đổi trên nền mới | `policy.effective_level(settings)`: `runner.py:160` → `:164`; `_values_refusal`: `site_api.py:161` → `:165`; `PERMISSION_DOCTYPES` vẫn ở `site_api.py:29` | `git show {4469287,develop}:…` |
| Phân loại lại (U4b) đi đường nào | ADR-037 QĐ 2: "chạy lại đúng bước phân loại của ADR-019 QĐ 1", cùng hàm dựng request. QĐ 3: sau đó "đi như lần tạo phiếu", chọn chế độ sau parse, trước `_route` | `docs/team/adr/ADR-037.md:48-57` |
| Vùng của U2 và U4b trong `_classify` | U2: khối "bị loại" sau `parse_classification`, trước chốt dưới ngưỡng của U1, nhánh `(False, classification, context)`, giá trị `is_excluded_team=` của lời gọi `decide_route` (hàm dò, C-8). U4b: đọc phiếu, gọi model, nhánh lỗi cổng, các tham số khác của `decide_route` (T109), `keep_human_fields`, cột log, logger | `design-addendum-1-U4b-U8-fixes.md:337`; `design-addendum-1-U2.md:164-172`; `arch-review-design-w1a.md:59`, `:62` |
| U7 cần U2 không | Không: U7 cần U1, U3, U4b, T63 | `arch-impact.md:181`; AR3-11 (`plan-w1.md:136`) |

## 1. Mục tiêu 1: R-5

### Phán quyết

Nhận thứ tự của `plan-w1.md`. U2 đến sau U4b trong `runner.py`. Lý do:
- Không có xung đột gộp nào, vì không đơn vị nào sửa song song. Mỗi task cắt từ đầu nhánh, nên đơn vị đến sau sửa trên mã của đơn vị đến trước. Phán quyết cũ "U2 trước U3" (`arch-review-design-w1a.md:87`) dựa vào việc U2 sửa `runner.py` hẹp hơn và có ít tiền đề hơn; cả hai lý do không còn quyết định, vì FEAT-004 và FEAT-005 đều đã ở `develop`.
- Thứ tự không đổi kết quả cuối: U2 chỉ thêm một chốt dừng **trước** mọi chốt và mọi lần ghi của U1, U4b sau parse. Chốt này đặt trước hay sau U4b thì cũng là chốt thắng.
- Đặt U2 trước U4b thì cả đợt 1b của U2 vào đường tới U7 (U7 cần U4b, `arch-impact.md:181`), chỉ để tránh một khoảng thời gian mà lỗ A5-3a (1) còn mở **trên nhánh feature**. Lỗ đó đã có trên `develop` hôm nay. Khoảng thời gian này được giữ kín bằng R5-5.
- Chỗ U4b có thể làm hỏng việc U2 đến sau: tạo ra một đường phân loại thứ hai (phân loại lại) mà khối của U2 không thấy. R5-1 chặn đúng chỗ đó.

### Điều kiện

| # | Điều kiện | Ai/task | Kiểm xong (có đầu ra) |
|---|---|---|---|
| R5-1 | **Một chỗ parse.** Sau U4b, mọi kết quả phân loại (lần tạo phiếu và lần phân loại lại của T113) đi qua đúng một lời gọi `parse_classification(` trong `runner.py`, nằm trong `_classify`. T113 dùng lại `_classify`, không dựng hàm parse và chốt thứ hai (ADR-037 QĐ 2, 3). Cần thêm một đường → `DESIGN_CONFLICT` | T113; reviewer T113 | `git grep -c "parse_classification(" team/FEAT-007 -- erp_ai/agent/runner.py` = 1 sau merge T113 |
| R5-2 | **Ô của U2 để trống, nằm ngay sau parse.** Trong `_classify` của U4b, giữa lúc parse hợp lệ và chốt dưới ngưỡng của U1, không có lần ghi phiếu, comment, thông báo, Task, lời gọi `_route`, `open_collector`/`mark_work_only` hay lời gọi model nào. Thứ tự sau U4b: parse → [ô U2] → chốt dưới ngưỡng (U1, C-5) → chọn chế độ (T115) → khóa định tuyến một lần (T112) → `_route`. Dòng `classify` vẫn là chỗ U2 ghi `stop_reason` | T108, T112, T113, T115; reviewer | reviewer T115 và T113 dán đoạn `_classify` từ parse tới chốt dưới ngưỡng vào `review-115.md`, `review-113.md` |
| R5-3 | **Hợp đồng trả của `_classify` giữ C-5.** U4b không đổi dạng `(proceed, classification, context)`. `_run` dừng khi `proceed` sai, **trước** `_reason` và mọi lần đăng của bộ gom. Nếu bộ gom đã mở trước `_classify` thì lối ra này chỉ đi qua `close_collector` trong `finally`, không đăng gì. T109 giữ tham số từ khóa `is_excluded_team=` trong lời gọi `decide_route`, không gộp vị từ vào chỗ khác, để U2 chỉ thay giá trị bằng hàm dò (C-8) | T109, T113, T115 | `git grep -n "is_excluded_team=" team/FEAT-007 -- erp_ai/agent/runner.py` = 1 dòng sau T109; `test_agent_runner` xanh |
| R5-4 | **Kế hoạch đợt 1b đặt U2 sau từng chuỗi file, không "rebase".** Task U2 sửa `runner.py`/`test_agent_runner.py` `depends:` task cuối của chuỗi file đó ở `plan-w1.md` (hôm nay là T113 và T118). Task U2 sửa `handlers.py`/`test_handlers.py` `depends:` T114. Task U2 sửa `site_api.py`/`test_site_api.py` `depends:` T82. Task U2 sửa `policy.py` `depends:` T71. Các task U2 không chạm `runner.py`, `handlers.py` được chạy xen với U4b theo bảng "Một file, một chủ" | tech-lead, kế hoạch đợt 1b | dòng `depends:` của task U2 trong kế hoạch đợt 1b |
| R5-5 | **Không merge nửa vời.** `team/FEAT-007` không merge vào `develop`, và không vào bản phát hành nào, khi đã có task runner đầu tiên của U4b (T108) mà task runner của U2 chưa merge. Mốc "cuối đợt 1" của `arch-impact.md:185` (`cmd.test` xanh rồi merge vào `develop`) là sau đợt 1b, không phải sau M11. Lý do: trong khoảng đó, phiếu chưa có nhóm mà phân loại ra bộ phận loại trừ vẫn được suy luận và nay còn nhận thêm một comment hướng xử lý (thêm một đầu ra vào lỗ A5-3a (1), trái NFR-1 và ADR-034 QĐ 1) | team-leader, tech-lead | `git merge-base --is-ancestor <commit runner U2> develop` trước mọi lần merge `team/FEAT-007` → `develop` sau T108 |
| R5-6 | **Test của U2 viết trên mã U4b.** AC-9 (b) `test_classified_into_excluded_team_stops_before_reasoning` (`design-addendum-1-U2.md:297`) đếm 0 comment, gồm cả comment hướng (T116), comment định tuyến (T109) và thông báo (T110). Thêm một ca trên đường T113: lần chạy phân loại lại ra bộ phận loại trừ → `stop_reason=excluded_by_classification`, `count_guidance` = 0, 0 dòng `reason`. Ca `test_excluded_wins_over_low_confidence` giữ | kế hoạch đợt 1b | hai test đó xanh qua `cmd.test_one` ở task runner của U2 |

Để designer (đợt 1b), không phải thứ tự: T113 đưa `later_messages` (tin đến sau, gồm comment) vào request phân loại lại. Câu "payload không chứa comment" của AC-9 (b) chỉ đúng cho lần tạo phiếu. Có cần một câu cho đường phân loại lại theo NFR-1 hay không là việc của designer khi viết lại thiết kế U2 trên nền U4b.

## 2. Mục tiêu 2: nền T56, T90 nhập vào T56

### Phán quyết

Xác nhận (b) lúc 00:59. Lý do kiến trúc:
- `arch-impact.md:185` đặt cổng đợt 0 là "FEAT-004 và phần ADR-024 của FEAT-005 vào `develop`; `team/FEAT-007` merge `develop` một lần". Gộp một lần là trở lại đúng thiết kế.
- Gộp ngay bây giờ, phần ADR-024 vào nhánh **trước** khi U1, U3, U4b sửa `runner.py`. Mọi task sau đó (T67, T74, T75, T80–T82, T91, T92, T108–T117) được viết và test trên vòng lượt có savepoint (ADR-024 QĐ 2) và trên `_record_snapshot` (QĐ 1). Như vậy các ràng buộc của ADR-024 được giữ ở từng task, không phải gỡ lại một lần ở cuối.
- Chi phí của phần FEAT-005 ở T56: thêm 5 khối xung đột, đều trong 3 file mà `files:` của T56 đã có, và 0 khối ở `runner.py`, `tasks.py`.

### Điều kiện cho T56, T57 (phần ADR-024)

| # | Điều kiện | Task | Kiểm xong (có đầu ra) |
|---|---|---|---|
| R5-7 | **Điều kiện bắt đầu của T90 chuyển sang T56.** Trước khi gọi dev, trên đúng commit `develop` sẽ gộp: `git grep -c "GENERIC_WRITE_TOOLS\|REASON_TURN_SAVEPOINT" <commit> -- erp_ai/agent/runner.py` > 0 và `git grep -c "privilege_alert_checked_until" <commit> -- erp_ai/tasks.py` > 0. Ghi SHA đó vào `Receives` của T56. Nếu `develop` đã đi quá `cf69b57`, chạy lại `git merge-tree <merge-base> team/FEAT-007 <commit>` (read-only). Có khối xung đột ở `runner.py` hoặc `tasks.py` → dừng, báo architect | T56 (tech-lead trước khi gọi dev) | hai số > 0 và danh sách file xung đột dán vào dòng progress của T56 |
| R5-8 | **`files:` và `depends:` của T56 theo xung đột thật.** Thêm `erp_ai/agent/tools/test_source.py`. Khối xung đột này đến từ FEAT-004, không phải FEAT-005, nên hàng T56 của `tasks-w1.md` đang thiếu nó dù không có quyết định (b). Thêm `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (cả hai bên cùng sửa; hôm nay tự gộp được, nhưng T17–T20 còn sửa nó). `depends:` thêm T38 (đang mở, sửa `source.py`, `test_source.py`) | T56 | `git merge-tree` ở R5-7 không còn file xung đột nằm ngoài `files:` |
| R5-9 | **Phần ADR-024 vào nguyên vẹn.** Sau merge T56: `git diff <commit develop> HEAD -- erp_ai/agent/runner.py erp_ai/tasks.py erp_ai/agent/tools/site_api.py erp_ai/tests/test_tasks.py erp_ai/agent/test_runner_routing.py erp_ai/agent/tools/test_site_api.py` rỗng (FEAT-007 chưa sửa các file này, nên chúng phải giống hệt `develop`). `test_architecture.py` sau gộp còn đủ mọi hàm `def test_` của bản `develop`, gồm `test_privilege_alert_reads_shared_generic_write_tools` và `test_privilege_alert_watermark_and_clock_rules` | T56 | lệnh diff không in dòng nào; `comm -23` danh sách tên test của `develop` với bản gộp = rỗng |
| R5-10 | **Mốc ADR-024 trên Setting (QĐ 3.2).** `erp_ai_setting.py` sau gộp vẫn khôi phục `privilege_alert_checked_until` từ DB lúc lưu, cạnh `spent_this_month_usd`, và giữ `read_privilege_watermark`. JSON có trường đó, chỉ đọc. Trường này nằm trong số "số thật trên nền mới" của `field_count`. Tên trường chỉ có ở JSON, `erp_ai_setting.py`, một hàm ghi trong `tasks.py`, và test (ADR-024 Ràng buộc 3) | T56 | `git grep -l "privilege_alert_checked_until" HEAD -- 'erp_ai/*.py' ':!*test*'` = `erp_ai_setting.py`, `tasks.py`; `test_architecture` xanh |
| R5-11 | **Lần chạy kiểm.** Một lần giữ khóa site: `cmd.migrate` từ worktree `feat-007`, rồi `cmd.test_one` cho `erp_ai/tests/test_tasks.py`, `erp_ai/agent/test_agent_runner.py`, `erp_ai/tests/test_architecture.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`, `erp_ai/agent/tools/test_site_api.py`. `cmd.test` cả bộ ở M7 (sau T57) thay cho mốc "cả bộ ở M8" mà T90 từng ghi. Sau migrate này, site mang trường của cả FEAT-005 lẫn FEAT-007. Hết chuyện migrate của nhánh này gỡ trường của nhánh kia (`note-from-feat-004-session.md:34`) | T56; M7 | đầu ra `Ran … OK` của năm module và của `cmd.test` dán vào progress |
| R5-12 | **T57 không thêm kiểm ADR-024 riêng.** `site_api.PERMISSION_DOCTYPES` vẫn còn trên `develop` (`site_api.py:29`), nên T57 giữ nguyên `files:`, `Expect`. Chỉ đổi: chạy trên nền R5-9 và là task ngay trước M7 | T57 | như hiện có |

### Ràng buộc ADR-024 mà các task sau T56 phải giữ (do nay được viết trên nền FEAT-005)

| # | Điều kiện | Task | Kiểm xong |
|---|---|---|---|
| R5-13 | Trước/sau theo dòng và khóa `"<tool>#<n>"` của `_record_snapshot` giữ nguyên khi `_action` chuyển sang `action_entry` (`design-addendum-1-U3.md:167`). Đây là thứ cảnh báo hằng ngày đọc (ADR-024 QĐ 1) | T91 | `Expect` của T91 thêm `cmd.test_one` cho `erp_ai/tests/test_tasks.py` xanh |
| R5-14 | `write_entry` giữ `insert` và `commit` trong cùng lời gọi. Kiểm của T85 (`bot_action`) và T93 (`ACTION_KEYS`) chạy trước `insert`, ném lỗi thì 0 dòng (ADR-024 Ràng buộc 5) | T85, T93 | reviewer dán thân `write_entry` sau merge; `test_agent_runner` (gồm test QĐ 2 của FEAT-005) xanh |
| R5-15 | **T93 đứng trước T110.** Mọi mục hành động mới của U4b (thông báo T110, hướng T116) dựng bằng `action_entry` lúc viết, nhờ luật của T93 đã có (ADR-033 Ràng buộc). Nếu T93 đến sau thì luật đó gặp mục viết tay đã merge và task trả `DESIGN_CONFLICT`. Rủi ro R-1 "reviewer kiểm tay" vì thế hết | T93 → T110 | `depends:` của T110 có T93 |
| R5-16 | Lời gọi `post_guidance` của `_finish_guidance` nằm trong khối `try` bắt đầu sau `frappe.db.savepoint(REASON_TURN_SAVEPOINT)` (`develop:runner.py:647`), sau vòng tool, trước `write_entry` của lượt cuối. Mục hành động của nó nằm trong `actions` của lượt đó (ADR-024 QĐ 2). Các hàm của `write_ticket.py` chạy trong lượt (`post_guidance`, `post_notice`, `locked_rows`, `count_guidance`) không commit (ADR-024 QĐ 5: "mã erp_ai không commit gì giữa savepoint của lượt và commit của dòng `reason`") | T99–T104, T116 | `git grep -c "frappe.db.commit" team/FEAT-007 -- erp_ai/agent/tools/write_ticket.py` = 0 ở M10. Ở T116 thêm một ca: `write_entry` của lượt cuối ném lỗi → 0 comment hướng còn lại, `count_guidance` = 0 |

## 3. Dòng và mục phải sửa (tech-lead sửa, file này không sửa)

### `plan-w1.md`

| Chỗ | Sửa |
|---|---|
| "Thứ tự" mục 2 (dòng 17) | "T56 (gộp `develop` @ `4469287` có FEAT-004)" → "T56 (gộp đầu `develop`, ≥ `cf69b57`, có FEAT-004 và FEAT-005; SHA ghi ở `Receives`)" |
| "Thứ tự" mục 5 (dòng 20) | "U3: T84–T89, T91 → T92 → T93 ngay sau U1 (T91, T92 trong chuỗi `runner.py` ngay sau T82, trước T108); T94 sau T66" |
| Đoạn dòng 23 | thay bằng: "`runner.py`: U1 → U3 → U4b → U2 (đợt 1b) → U6b, theo `arch-ruling-r5.md` R5-1..R5-6" |
| "Nhóm song song" (dòng 31-35) | hàng "U1 giữa" làn A: thêm "→ T91 → T92" sau T82 (hoặc một hàng mới "U3 runner" trước "U3 và đầu U4b"); hàng "U3 và đầu U4b" thêm T93 sau T89, thêm T94 vào làn B; **xóa** hàng "Khi FEAT-005 ở `develop`" (dòng 35) |
| "Ràng buộc chung" (sau dòng 49) | thêm một gạch: R5-13, R5-14, R5-16 (ADR-024 trên nền mới) |
| "Một file, một chủ" dòng 94 (`runner.py`) | `T67 → T74 → T75 → T80 → T81 → T82 → T91 → T92 → T108 → T109 → T110 → T111 → T112 → T115 → T116 → T117 → T113`; bỏ vế "T91 → T92 chen vào sau T82 khi T90 xong" |
| dòng 95 (`test_agent_runner.py`) | `T72 → T80 → T81 → T82 → T91 → T92 → T108 → T110 → T111 → T115 → T116 → T117 → T113 → T118`; bỏ "T91 → T92 như trên" |
| dòng 97 (`test_architecture.py`) | `T70 → T71 → T74 → T80 → T83 → T85 → T88 → T89 → T93 → T99 → T105 → T119`; bỏ vế "T90 và T93 đến khi FEAT-005 có…" |
| dòng 109 (`tasks.py`, `test_tasks.py`) | `T94` |
| bảng đó, thêm hàng | `erp_ai/agent/tools/source.py`, `test_source.py`: `T38 → T56` (R5-8) |
| dòng 116 | "… (và T56 là lần gộp duy nhất, có `cmd.migrate`)" |
| "Điều kiện → task" (sau dòng 145) | thêm hàng R5-1..R5-3 → T109, T113, T115; R5-4, R5-6 → đợt 1b; R5-5 → team-leader; R5-7..R5-11 → T56; R5-12 → T57; R5-13 → T91; R5-14 → T85, T93; R5-15 → T110; R5-16 → T99–T104, T116 |
| "Mốc kiểm" M7 (dòng 185) | thêm: năm module của R5-11 và R5-9 trước `cmd.test` |
| "Mốc kiểm" M9 (dòng 187) | "Sau T93 (hết U3, trừ T94)"; bỏ "(phần U3 không chờ FEAT-005)" |
| "Mốc kiểm" M10 (dòng 188) | thêm phép grep của R5-16 |
| "Rủi ro" R-1 (dòng 195) | xóa (hết: FEAT-005 ở `develop` `464063f`; quyết định (b) 00:59) |
| R-2 (dòng 196) | thêm T38 vào "chỉ chạy khi …" (R5-8) |
| R-3 (dòng 197) | đếm lại: `runner.py` 17 task, `test_architecture.py` 12 task, không còn T90 |
| R-5 (dòng 199) | thay bằng "Đã phán: `arch-ruling-r5.md`; điều kiện R5-1..R5-6; R5-5 là việc của team-leader" |
| "Gộp vào tasks.md" bước 1, 4 (dòng 220, 223) | bước 1 áp thêm hàng T56 mới (R5-7..R5-11) và hàng T57 (R5-12); bước 4: `= 118` nếu xóa dòng T90 (khuyên xóa; số T90 không cấp lại) |
| "Việc cần team-leader" (dòng 227-228) | xóa gạch R-1 và R-5; thêm: "R5-5: không merge `team/FEAT-007` → `develop` sau T108 cho tới khi task runner của U2 merge" |

### `tasks-w1.md`

| Chỗ | Sửa |
|---|---|
| Dòng 19 (nhánh nền) | "… sau khi T56 đã merge (nhánh đã chứa `develop` @ `<SHA của R5-7>`, ≥ `cf69b57`, có FEAT-004 và FEAT-005)" |
| Bảng "Sửa dòng task cũ khi gộp", hàng T56 thứ nhất (dòng 27) | `depends: T20, T23, T38, T59` và `[affected]`; cột "Vì": FEAT-004 và FEAT-005 đã ở `develop` @ `cf69b57`; `test_source.py` xung đột (FEAT-004); phần còn lại giữ (kèm câu sửa T43, T49 ở `plan-w1.md:149`) |
| Hàng T56 thứ hai (dòng 28, Receives) | "`develop` @ `<SHA>` (FEAT-004 đủ 70 task, FEAT-005 17/17, phần ADR-024 có); kiểm theo R5-7" |
| Bảng đó, hàng mới T56 `files:` | thêm `erp_ai/agent/tools/test_source.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` (R5-8) |
| Bảng đó, hàng mới T56 `Expect` | thêm R5-9, R5-10, R5-11; bỏ chữ "phần ADR-024 … nếu đã vào" ở `Receives` của `tasks.md:476` |
| Hàng T57 (dòng 29) | giữ; thêm "trên nền R5-9, ngay trước M7" (R5-12) |
| T65 `Receives` (dòng 47) | "`develop` @ `cf69b57`, `site_api.py:165-180`" |
| T67 `Returns` (dòng 63) | "`runner.py:164` của `develop` @ `cf69b57`" |
| Đoạn đầu U3 (dòng 148) | thay bằng: "Phần FEAT-005 mà T91, T92, T94 cần đã vào nhánh ở T56 (`arch-ruling-r5.md` mục 2)" |
| T90 (dòng 180-184) | xóa dòng task (nhập vào T56); không cấp lại số T90 |
| T91 `depends:` (dòng 185) | `T84, T82`; `Expect` thêm `erp_ai/tests/test_tasks.py` xanh (R5-13) |
| T93 (dòng 195) | `Returns` thêm: kiểm chạy trước `insert`, `insert` và `commit` vẫn cùng lời gọi (R5-14) |
| T94 `depends:` (dòng 200) | `T66` |
| Đoạn đầu U4b (dòng 208) | "T91 → T92 (U3) đứng trước T108; T93 trước T110 (`arch-ruling-r5.md` R5-15). Thứ tự `_classify` sau U4b theo R5-1..R5-3" |
| T85 (dòng 155) | `Returns` thêm phần của R5-14 về `write_entry` |
| T108 `depends:` (dòng 275) | thêm T92 |
| T109 (dòng 280) | `Returns` thêm: giữ `is_excluded_team=` trong lời gọi `decide_route` (R5-3) |
| T110 `depends:` (dòng 285) | thêm T93 (R5-15) |
| T113 (dòng 300) | `Returns` thêm R5-1 (một lời gọi `parse_classification(`, phân loại lại qua `_classify`) và R5-3 |
| T115 (dòng 310) | `Returns` thêm R5-2 (không gì giữa parse và chốt dưới ngưỡng) |
| T116 (dòng 315) | `Returns` thêm R5-16 (chỗ của `post_guidance` trong khối savepoint); `Expect` thêm ca `write_entry` lỗi → 0 comment hướng |

## 4. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR và mọi phán quyết trước mà vẫn xung đột, rồi siết:
1. T113 dựng `_reclassify` có parse riêng; task U2 (đợt 1b) đặt khối "bị loại" trong `_classify` → lần phân loại lại ra bộ phận loại trừ vẫn định tuyến và đăng hướng. Siết bằng R5-1 (một lời gọi parse, có grep) và R5-6 (ca trên đường T113).
2. T115 đặt `open_collector` và `mark_work_only` ngay sau parse; U2 chèn sau đó → không ghi gì nhưng thứ tự chốt lệch C-5. Siết bằng R5-2 (ô trống ngay sau parse).
3. T109 gộp `policy.is_excluded_team` vào hàm khác; hàm dò của U2 (C-8) không còn chỗ gắn. Siết bằng R5-3.
4. T110 dựng dict thông báo viết tay; T93 (đến sau như kế hoạch cũ) thêm luật → `DESIGN_CONFLICT` trên mã đã merge. Siết bằng R5-15.
5. T116 gọi `post_guidance` sau `write_entry` của lượt cuối → comment được commit khi job trả về mà dòng `reason` không có mục của nó. Siết bằng R5-16.
6. T91 viết lại `_action` và bỏ khóa `"<tool>#<n>"`; cảnh báo hằng ngày ra một loạt mục "không có trước/sau". Siết bằng R5-13 (`test_tasks` vào `Expect`).
7. T56 gộp trong khi T38 merge `source.py`, `test_source.py` → xung đột ngoài `files:`, T56 trả `NEEDS_CONTEXT`. Siết bằng R5-8.
8. Tech-lead merge `team/FEAT-007` → `develop` ở mốc "cuối đợt" sau M11 (U4b có, U2 chưa); phiên FEAT-004/005 phát hành từ `develop` → lỗ A5-3a có thêm comment hướng ở bản phát hành. Siết bằng R5-5.

Sau khi siết, không còn cặp nào tìm được trong phạm vi T56, T57, U1, U3, U4b và chỗ nối với U2.
