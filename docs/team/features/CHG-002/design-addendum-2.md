# CHG-002 — Phụ lục thiết kế 2 (hẹp: chỉ T1)

- Ngày: 2026-11-15 · Người viết: designer · Chế độ: `--amend --decide`
- Lý do: build lượt 1 trả `DESIGN_CONFLICT` ở T1 (tasks.md T1 progress; journal `docs/team/journal/CHG-002.pending-build2.md`).
- Phạm vi: chỉ T1 và một luật chung (L-1) cho test cũ ghim hình dạng. **Không đổi AC nào, không đổi NFR nào, không đổi phạm vi "Giữ vành đai an toàn".** Không đổi ADR nào; tuân ADR-012 (nhóm trường), ADR-040 QĐ 4–7, ADR-031 QĐ 3 (qua RQ-1).
- Nguồn đã đọc: design.md §2.2 (dòng 145-166), §3.1 (204-264), §8.3 (802-816); tasks.md T1 (36-52); `dd444ad` bốn test cũ; `f8b4e62` `propose_change.py`, `registry.py:135-196`, `erp_ai_change_proposal.json`, diff `constants.py`; RQ-1 ở `docs/team/features/FEAT-007/arch-impact-chg-002.md:141`.
- Explore: không gọi (theo lệnh của team-leader; mọi chỗ cần đọc đã được chỉ đích danh và đọc bằng `git show`).

## Assumptions decided by the team
- A2-a: dạng `{path, edits, reason}` (đầu vào cũ trước CHG-001) chưa bao giờ là dạng hợp lệ của `propose_file_change`; "dạng cũ vẫn nhận" ở §3.1 nói về `{path, find, replace, commands?, reason}`.
- A2-b: 6 lỗi baseline của lần chạy cả app đã có trên `dd444ad`, không thuộc T1. "cmd.test xanh" của T1 được đọc là: không thêm lỗi nào so với BASE.

---

## A2-1. Ba test DocType đề xuất ghim trường/bố cục/Select

**Sự việc.** T1 thêm đúng 6 trường §2.2 (`operations`, `command_list`, `command_results`, `created_dirs`, `restart_status`, `restart_sent_at`), đều `read_only = 1`. Ba test ở `test_erp_ai_change_proposal.py` so **bằng** với danh sách cũ: tập Select (`:235-236`), tập Code và số trường dữ liệu 35 (`:239-247`), `FIELD_ORDER` (`:392-393`). Chúng đỏ vì hình dạng mà §2.2 đã duyệt đổi, không vì hành vi sai.

**Chọn.** Sửa ba test **ngay trong T1**, giữ phép so bằng (không đổi sang tập con hay `>=`), thêm giá trị mới lấy từ §2.2 và từ hằng trong `constants.py`. Thêm `test_erp_ai_change_proposal.py` vào touchpoint của T1. Bố cục dev chọn ở `f8b4e62` được nhận: không thêm section hay column nào; `operations` ngay sau `diff` (section Diff); `command_list` sau `command_args`, `command_results` sau `command_output` (section Lệnh bench); `created_dirs`, `restart_status`, `restart_sent_at` cuối section Duyệt và kết quả.

**Vì.** (1) T1 là task làm đổi hình dạng, và T1 phải để cả app không thêm lỗi; test đỏ do T1 thì T1 sửa (STD-TEST-5: spec/design đổi thì test được đổi). (2) Giữ so bằng thì test vẫn bắt được trường thừa hoặc thiếu ở các task sau. (3) Không thêm section mới thì `test_form_layout_git_sections` chỉ đổi `FIELD_ORDER`, phần section và column giữ nguyên từng chữ.

**Phương án khác.** (a) Dời sửa test sang task làm form (sau T1): bị loại, vì T1 sẽ merge với 3 test đỏ, phá cổng "Gộp: reviewer approve trước T2..T50". (b) Nới test thành "chứa ít nhất các trường cũ": bị loại, mất khả năng bắt trường lạ (ADR-012 cần biết đủ nhóm trường). (c) Bắt T1 tạo section riêng cho khối: bị loại, ngoài phạm vi walking skeleton.

**Sai thì hoàn tác.** Đổi lại 3 test về bản `dd444ad` bằng `git revert` commit sửa test, đồng thời gỡ 6 trường khỏi JSON (cả hai cùng một commit T1). Không có dữ liệu cần dọn: 6 trường mới, chỉ đọc, chưa có bản ghi khối nào ngoài site dev.

**Ghi chú cho task sau (không làm ở T1).** `section_command` hiện `depends_on: eval:doc.change_kind=='Lệnh bench'`, nên khối có file và lệnh (`change_kind = Thay đổi code`) sẽ ẩn `command_list`/`command_results` trên form. Task làm form khối được đổi `depends_on` này theo L-1 (sửa đúng bộ ba của `section_command` trong `test_form_layout_git_sections`).

## A2-2. Lời gọi dạng cũ khi `required = ["reason"]`

**Sự việc.** Trên `dd444ad`, `required = ["path","find","replace","reason"]`; `registry._first_invalid_key` (`registry.py:173-184`) duyệt `required` trước, nên `{path, edits, reason}` bị từ chối `tham số không hợp lệ: find`. Từ T1, `required = ["reason"]` (§3.1); vòng `required` qua được, vòng thứ hai gặp khóa lạ `edits` trước → `tham số không hợp lệ: edits`. Registry từ chối **trước** handler, nên vòng `LEGACY_EDIT_KEYS` của dev (`propose_change.py:252-254`) không chạy tới cho ca này.

**Chọn (2a).** Câu từ chối cho `{path, edits, reason}` **đổi** thành `tham số không hợp lệ: edits`. Kiểu lỗi giữ nguyên (`{"ok": false, "reason": "tham số không hợp lệ: <khóa>"}`), 0 đề xuất, 0 comment.

**Vì.** Giữ chữ `find` chỉ có hai cách, cả hai trái thiết kế đã duyệt: thêm `find`/`replace` lại vào `required` (chặn lời gọi chỉ có `changes`, trái §3.1) hoặc sửa thứ tự kiểm trong `registry.py` (§3.1: `registry.py` không đổi). Câu mới nêu đúng khóa sai mà model đã gửi. `edits` không phải dạng hợp lệ (A2-a), nên không có người gọi đúng nào bị đổi kết quả.

**Phương án khác.** (a) Thêm `edits` vào `properties` làm khóa mồi để handler trả `find`: bị loại, thêm trường không spec nào cần (STD-DESIGN-5) và lộ trong schema gửi model. (b) Trả `BLOCK_SHAPE`: bị loại, đổi câu cho cả lời gọi dạng cũ thiếu khóa mà không cần.

**Giữ từng chữ ở chỗ còn giữ được.** Lời gọi dạng cũ **không có khóa lạ** nhưng thiếu khóa (ví dụ `{path, replace, reason}`) vẫn tới handler và phải trả đúng `tham số không hợp lệ: find` như hôm nay. Đây là việc của vòng `LEGACY_EDIT_KEYS`; T1 phải có assertion cho nó (xem mục Việc dev), vì hiện chưa test nào chạy qua dòng 254.

**Chọn (2b).** **Được** nhập `registry._invalid` (dạng `from erp_ai.agent.tools.registry import _invalid as registry_invalid` như `f8b4e62:16`).
- Vì: một nguồn duy nhất cho câu `tham số không hợp lệ: …` (STD-DESIGN-4), kể cả phép cắt `KEY_REASON_MAX`; cùng gói `erp_ai.agent.tools`; §3.1 cấm sửa `registry.py` nên không đặt được tên công khai; `propose_change` đã phụ thuộc `registry` (`ToolContext`, `ToolSpec`), không sinh vòng phụ thuộc (STD-DESIGN-6).
- Phương án khác: chép chuỗi `f"tham số không hợp lệ: {key}"` vào `propose_change.py` (bị loại: hai nguồn, lệch khi registry đổi cách cắt); thêm hàm công khai trong registry (bị loại: §3.1 giữ `registry.py`).
- Điều kiện: chỉ một chỗ nhập, giữ bí danh `registry_invalid`, một dòng chú thích trỏ "design-addendum-2 A2-2". Khi một task sau có quyền sửa `registry.py` (cần đổi §3.1), đổi sang tên công khai và bỏ chú thích.
- Sai thì hoàn tác: thay lời gọi bằng `_fail(...)` với chuỗi chép; 1 dòng nhập + 1 dòng gọi; test A2-2 giữ nguyên vì cùng chữ.

**Ngoài T1 (ghi để tech-lead biết, không làm ở T1).** `{reason}` đứng một mình hiện trả `…: path`; §3.1 bảng `BLOCK_SHAPE` ("không thiếu cả hai") muốn `BLOCK_SHAPE`. Task nào có test `BLOCK_SHAPE` thì đổi ca này; T1 không đổi.

## A2-3. RQ-1 (yêu cầu của FEAT-007, `arch-impact-chg-002.md:141`)

**Chọn.** **Nhận** RQ-1 làm ràng buộc của CHG-002: một hàm chèn chung `_insert(ctx, values)`; `values` mang cả `operations` và (khi có lệnh) `command_list`; `get_doc` → `insert()` trong `allow_agent_write()` → `_comment`; trả `{ok, proposal, status, comment}`; `_propose_block` chỉ kiểm và dựng `values` rồi gọi `_insert`; cả file đúng 1 `.insert(` và đúng 1 lời gọi `allow_agent_write()`.

**`f8b4e62` đã đúng.** Kiểm bằng `git show f8b4e62:erp_ai/agent/tools/propose_change.py | grep -n "\.insert(\|allow_agent_write\|registry_invalid"`:
```
13:from erp_ai.agent.agent_write_guard import allow_agent_write
16:from erp_ai.agent.tools.registry import _invalid as registry_invalid
143:	with allow_agent_write():
144:		proposal.insert()
254:			return registry_invalid(key)
```
Dòng 13 là lệnh nhập, không phải lời gọi: đúng 1 `allow_agent_write()` và đúng 1 `.insert(`. `_propose_block` (`:198-246`) dựng `values` có `operations` rồi `return {**_insert(ctx, values), "branch": ...}`, không tự chèn. Khóa `branch` thêm ngoài `_insert` là tập lớn hơn, khớp §3.1 "Đầu ra". T1 chưa có lệnh nên `values` chưa có `command_list`; task thêm `commands` phải đặt `command_list` vào **cùng** `values` này, không thêm `.insert(` thứ hai.

**Vì.** RQ-1 trùng đúng với §3.1 "cả ba handler đi về một hàm nội bộ" và không đổi AC; nhận nó không tốn gì ở T1 và giữ đường bản ghi một cửa mà ADR-031 QĐ 3 cần.

**Phương án khác.** Không nhận và để `_propose_block` tự chèn: bị loại, hai cửa mở guard ghi của agent, trái ADR-031 QĐ 3 và ADR-023 QĐ 5.

**Sai thì hoàn tác.** Không có mã cần đổi: `f8b4e62` đã thỏa. Nếu FEAT-007 rút RQ-1, chỉ gỡ dòng ràng buộc này khỏi phụ lục.

---

## L-1. Luật chung: test cũ ghim hình dạng mà §2/§3 đổi

Áp dụng cho mọi task T2..T51 của CHG-002.

1. **Ở đâu.** Test cũ đỏ vì hình dạng đổi được sửa **trong chính task làm đổi hình dạng đó** (task mà diff của nó làm test đỏ), không dời sang task khác. Tech-lead thêm file test vào touchpoint của task ấy khi biết trước (§8.3 "Test cũ phải sửa" là danh sách biết trước).
2. **"Hình dạng" chỉ gồm:** danh sách/thứ tự/kiểu/thuộc tính trường DocType (§2), tùy chọn Select, bố cục form (section, column, `depends_on`), schema tool (`required`, `properties`, `enum`, `maxItems`, `minLength`, `maxLength`), câu từ chối có trong bảng §3.1 hoặc hệ quả trực tiếp của schema §3.1 (như A2-2), và các mục §8.3.
3. **Giới hạn của lần sửa.**
   - Chỉ thay giá trị ghim cũ bằng giá trị mới ghi trong design hoặc phụ lục; lấy từ hằng nếu hằng có.
   - Giữ kiểu so: so bằng thì vẫn so bằng (đủ tập, đủ danh sách, đúng số đếm). Cấm đổi sang `assertIn`, tập con, `>=`; cấm xóa assertion hay test; cấm skip/xfail (STD-TEST-4).
   - Assertion về phần không đổi giữ nguyên từng byte.
   - Được thêm assertion cho giá trị mới; không thêm test mới cho hành vi khác.
4. **Dev gặp test chưa có trong touchpoint.** Được sửa không dừng **chỉ khi** đủ: (a) đỏ chỉ vì một mục ở điểm 2; (b) đã dán dòng đỏ của lần chạy cả app trên nhánh task và chứng minh test đó xanh trên BASE; (c) lần sửa nằm trong điểm 3. Thiếu một điều kiện, hoặc test đỏ vì logic/hành vi, hoặc test ghim một AC, hoặc file nằm trong `protected_paths` → `DESIGN_CONFLICT` như cũ.
5. **Ghi lý do gì.** Thân commit có một dòng cho mỗi test: `test-shape: <file>::<tên test> — <giá trị cũ> → <giá trị mới> — design §x.y (addendum-2 L-1)`. Dòng progress của task trong tasks.md ghi `L-1: <số test>`. Reviewer đối chiếu từng dòng với STD-TEST-5 và điểm 3; một dòng không khớp là lỗi chặn merge.

---

## Việc dev T1 phải sửa trên `f8b4e62`

Nhánh `team/CHG-002-task-1` @ `f8b4e62`; mã sản phẩm **không đổi** (A2-2b và A2-3 nhận đúng như đang có). Chỉ sửa test.

| File | Test | Khẳng định mới |
|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py` | `test_select_options_match_constants` | `select_fields == {"change_status", "change_kind", "restart_status"}`; `fields["restart_status"]["options"].split("\n") == ["", "Đã gửi", "Đã xác nhận", "Chưa xác nhận", "Lỗi khởi chạy"]` và danh sách này bằng `["", RESTART_STATUS_SENT, RESTART_STATUS_CONFIRMED, RESTART_STATUS_UNCONFIRMED, RESTART_STATUS_LAUNCH_FAILED]`; `fields["restart_status"].get("default")` rỗng (rỗng = "không cần", ADR-040 QĐ 7). Các assertion của `change_status`/`change_kind` giữ nguyên. |
| cùng file | `test_content_fields_are_code_and_read_only` | Thêm hằng mô-đun `BLOCK_CODE_FIELDS = {"command_list", "command_results", "created_dirs"}` (giữ `CODE_FIELDS` cũ nguyên); `code_fields == CODE_FIELDS \| BLOCK_CODE_FIELDS`; ba trường đó `options == "JSON"`; `len(data_fields) == 41` (35 + 6); `fields["operations"]["fieldtype"] == "Table"` và `options == OPERATION_DOCTYPE`; `fields["restart_sent_at"]["fieldtype"] == "Datetime"`. Vòng `read_only == 1` giữ nguyên (đã phủ 6 trường mới). |
| cùng file | `test_form_layout_git_sections` | Chỉ đổi hằng `FIELD_ORDER` thành đúng `field_order` của `f8b4e62` (chèn `operations` sau `diff`; `command_list` sau `command_args`; `command_results` sau `command_output`; `created_dirs`, `restart_status`, `restart_sent_at` sau `approved_digest`). Danh sách section, `columns`, `GIT_FIELDS` giữ nguyên từng chữ. |
| `erp_ai/agent/tools/test_propose_change.py` | `test_edit_errors_create_nothing` | Ca `old_shape = {"path", "edits", "reason"}`: kỳ vọng đổi thành `{"ok": False, "reason": "tham số không hợp lệ: edits"}` (A2-2a), vẫn `assert_nothing_created()`. Thêm ca `{"path": PATH, "replace": ["x = 2"], "reason": "x"}` → `{"ok": False, "reason": "tham số không hợp lệ: find"}` và `assert_nothing_created()` (giữ chữ dạng cũ qua `LEGACY_EDIT_KEYS`). Bốn ca schema `find`/`replace` phía trên giữ nguyên ở T1. |

Commit theo L-1 điểm 5 (4 dòng `test-shape:`). Kiểm: `cmd.test_one` cho hai file test trên và cho `erp_ai/agent/changes/test_apply_block.py`; rồi `cmd.migrate` và `cmd.test` cả app: chỉ còn đúng 6 lỗi baseline của `dd444ad` (A2-b), 0 lỗi mới.

## tasks.md đổi gì (tech-lead ghi)

- T1 `files:` thêm `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py` và `erp_ai/agent/tools/test_propose_change.py` (14 file; dòng "Ngoại lệ cỡ" đổi 12 → 14, lý do "test ghim hình dạng, design-addendum-2 A2-1, A2-2").
- T1 `test:` thêm hai file trên.
- T1 `Expect:` thêm bốn test ở bảng trên xanh; "cả app không thêm lỗi so với BASE".
- T1 `Criterion:` thêm "design-addendum-2 A2-1..A2-3; RQ-1 (FEAT-007) đã thỏa trên `f8b4e62`".
- Phần đầu tasks.md (hoặc mục chung của plan): một dòng "Test cũ ghim hình dạng: theo design-addendum-2 L-1".
- Không đổi task nào khác, không thêm task, không đổi AC.

## Kiểm lại
- AC spec ↔ test plan: không đổi so với design.md §8.3 (22/22 AC, 4/4 NFR):
```
spec:      AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
test plan: AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
```
- Đường dẫn mới: không có (hai touchpoint thêm là file test đã có trên `dd444ad`); không file nào trong `protected_paths`.
