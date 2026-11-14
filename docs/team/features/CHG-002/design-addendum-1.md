Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- G2b tắt cho CHG-002 (team.py: designed). Để trống. -->

# Design addendum 1 — CHG-002: tiếp nhận rà soát kiến trúc (F-1, F-2, F-3 và 3 điểm nhỏ)

**Thứ tự ưu tiên.** Addendum này **thắng `design.md`** ở mọi chỗ hai tài liệu khác nhau. `design.md` không bị sửa. Mỗi mục dưới đây nêu đúng mục và dòng của `design.md` (bản 886 dòng, 2026-11-15) bị thay. Chỗ nào addendum không nhắc tới thì `design.md` giữ nguyên.

**Nguồn:** `arch-review-design.md` (REVIEW: fix; F-1, F-2, F-3, 3 điểm nhỏ); `docs/team/adr/ADR-040.md`, mục "Phán quyết C-1 (2026-11-15, architect)" và "Ràng buộc của phán quyết". Luật áp: ADR-040 QĐ 4, 5 (đã sửa bởi C-1), 7, 8 và Ràng buộc; ADR-012 QĐ 4 và Ràng buộc; ADR-013 QĐ 7.

## 0. Bảng kết quả

| # | Mức | Trạng thái | Mục của addendum | Mục `design.md` bị thay |
|---|---|---|---|---|
| F-1 | major | **ADDRESSED** | A-1 | §0 dòng 10; §1.4 dòng 61; §1.5 R-1 dòng 70; §1.6 dòng 120; §2.5 dòng 188, 190, 196–199; §3.1 dòng 239, 258; §3.2 dòng 272, 278–279, 297, 311; §4.1 dòng 470, 473; §4.2 dòng 480; §4.3 dòng 532; §8.1 dòng 770; dòng 851 |
| F-2 | major | **ADDRESSED** | A-2 | §3.3 dòng 326; §5 dòng 615; §7 dòng 698; §8.1 dòng 773, 782 |
| F-3 | major | **ADDRESSED** | A-3 | §3.5 dòng 343, 345, 346; §7 dòng 686, 712; §8.1 dòng 767 |
| Nhỏ (1) | minor | **ADDRESSED** (quyết ở đây) | A-4 | §5.1 dòng 642 |
| Nhỏ (2) | minor | **ADDRESSED** (quyết ở đây) | A-5 | §3.4 dòng 336; §8.2 dòng 794 |
| Nhỏ (3) | minor | **ADDRESSED** (quyết ở đây) | A-6 | §4.4 dòng 572–577; §7 dòng 684; §8.1 dòng 773 |

Không còn DESIGN_CONFLICT: C-1 đã có phán quyết của architect (ADR-040) và được đưa vào ở A-1.

---

## A-1. F-1: giới hạn mỗi file 2 MiB, tổng 8 MiB tính cả `diff` (Phán quyết C-1)

### A-1.1 Câu thay thế
| `design.md` | Chữ cũ (tóm) | Chữ mới |
|---|---|---|
| dòng 10 | "DESIGN_CONFLICT ở 1 điểm hẹp (C-1)…" | `Kết quả: DESIGNED. C-1 đã có phán quyết (ADR-040, Phán quyết C-1) và được đưa vào design-addendum-1 A-1.` |
| dòng 61 (§1.4, hàng C-1) | cột "Design đang làm": chờ phán quyết | Hàng C-1 **đóng**: "Đã phán quyết 2026-11-15 (ADR-040 Phán quyết C-1). Thi hành ở design-addendum-1 A-1." Cột Đề nghị giữ làm lịch sử. |
| dòng 70 (§1.5 R-1) | "C-1, chờ architect" | `Theo Phán quyết C-1: mỗi file tối đa CHANGE_FILE_MAX_BYTES = 2 MiB; ca "1 MiB + 1 byte" qua (AC-43 ca 3).` |
| dòng 851 | "Điểm chờ vai khác: C-1 (architect)." | `Điểm chờ vai khác: 0.` |

### A-1.2 §2.5 Giới hạn (thay dòng 188, 190, 196–199)
Bảng hằng, chỉ ghi các hàng đổi; các hàng khác của bảng §2.5 giữ nguyên:

| Hằng | Giá trị | Đếm thế nào |
|---|---|---|
| **mới** `CHANGE_FILE_MAX_BYTES` (`erp_ai/constants.py`, khối CHG-002) | `2 * 1024 * 1024` | byte UTF-8 của nội dung trước và của nội dung sau, mỗi file, tính riêng |
| `CHANGE_MAX_TOTAL_BYTES` | `8 * 1024 * 1024` (không đổi) | **Σ trên mọi dòng của `len(before.encode("utf-8")) + len(after.encode("utf-8"))`** (thiếu thì tính 0) **cộng `len(diff.encode("utf-8"))` của trường `diff` trên bản ghi cha**. Đổi tên lưu nội dung hai lần nên tính hai lần (ADR-040 C-1, Hệ quả) |
| `source.TEXT_MAX_BYTES` | **tên nhập lại** của `CHANGE_FILE_MAX_BYTES`: `from erp_ai.constants import CHANGE_FILE_MAX_BYTES` rồi `TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES`. Không phải định nghĩa thứ hai | mỗi file, trước và sau |

Thay đoạn "Kiểm sức chứa" và "Tải form" (dòng 196–199):
- **Ngân sách gói SQL** (ADR-040 C-1, không chép lại phép tính): dòng con ≤ 4 MiB thô, ≤ 8 MiB sau khi thoát chuỗi; bản ghi cha có `diff` ≤ khoảng 5,4 MiB thô, ≤ khoảng 10,7 MiB sau khi thoát chuỗi. Cả hai dưới `max_allowed_packet` 16M. Chứng minh bằng test `AB::TestPacketBudget` (A-1.6), không bằng ước lượng.
- Bỏ câu "3% tiền tố dòng" (sai với dòng ngắn, ADR-040 C-1 Căn cứ đo).
- **Tải form:** tổng lưu của khối, kể cả `diff`, ≤ 8 MiB; JSON gửi về trình duyệt ≤ khoảng 16 MiB ở trường hợp xấu nhất (thoát JSON của `"`, `\`, xuống dòng). Thời gian tải đo ở `AB::TestLimits::test_form_load_at_ceiling_measured` và ghi vào `acceptance.md`.

Hằng bị xóa vì không còn người dùng (STD-STYLE-5; Phán quyết C-1 điểm 1: `SEARCH_FILE_MAX_BYTES` không còn là giới hạn mỗi file):
- `source.SEARCH_FILE_MAX_BYTES` (`source.py:37`; người dùng duy nhất còn lại là `source.py:220`, được thay ở A-1.4);
- `propose_change.PROPOSAL_FILE_MAX_BYTES` và `propose_change.TOO_LARGE` (`propose_change.py:31`, `:38`, `:172-174`; thay bằng `text_refusal` với dữ liệu đọc tối đa `TEXT_MAX_BYTES + 1` byte);
- `file_writer.PROPOSAL_FILE_MAX_BYTES` (`file_writer.py:11`, không dùng trong module; chỉ có test ghim `test_file_writer.py:11`, `:147` bị gỡ theo).

### A-1.3 §3.1 câu từ chối (thay dòng 239, 258)
| Hằng | Câu mới | Cách dựng |
|---|---|---|
| `BLOCK_TOO_LARGE` (`change_guard.py`) | `tổng nội dung của khối (kể cả diff) lớn hơn 8 MiB` | `f"… lớn hơn {CHANGE_MAX_TOTAL_BYTES // (1024 * 1024)} MiB"` |
| `source.TEXT_TOO_LARGE` | `file lớn hơn 2 MiB` | `f"file lớn hơn {TEXT_MAX_BYTES // (1024 * 1024)} MiB"` |

`read_source` từ chối file quá cỡ bằng **đúng** câu `TEXT_TOO_LARGE` (ADR-040 C-1, Ràng buộc: "cùng lý do").

### A-1.4 §3.2 hợp đồng nội bộ (thay dòng 272, 278–279, 297, 311)
- **`text_refusal`** (dòng 272): giữ thứ tự. Phép so `len(data) > TEXT_MAX_BYTES` là **phép so kích thước duy nhất** với `TEXT_MAX_BYTES`/`CHANGE_FILE_MAX_BYTES` trong `erp_ai/**` ngoài test. Nơi khác chỉ được dùng hằng làm cỡ đọc (`read(TEXT_MAX_BYTES + 1)`), không so.
- **`read_source`** (dòng 278): mở `rb`, `data = handle.read(TEXT_MAX_BYTES + 1)`, `reason = text_refusal(rel, data)`; có lý do thì `_refuse(reason)`; không thì giải mã UTF-8 chặt và chia trang như hôm nay (`READ_MAX_LINES` không đổi).
- **`search_source`** (dòng 279): thay `os.path.getsize(full) > SEARCH_FILE_MAX_BYTES` (`source.py:220`) bằng: đọc `TEXT_MAX_BYTES + 1` byte, `text_refusal(rel, data) is not None` thì bỏ file; còn lại quét chuỗi đã giải mã. `_scan_file(full, …)` đổi thành `_scan_text(text, rel, needle, hits)` (file không mở lần hai).
- **`check_block`** (dòng 297): chữ ký mới
  `check_block(ops, commands, allowed_apps, site, *, at_apply: bool, diff_text: str, legacy: bool = False) -> BlockCheck`.
  `diff_text` là tham số bắt buộc, không có mặc định, để không chỗ gọi nào quên đếm `diff`.
- **Bước 3 "Tổng byte"** (dòng 311): `total = Σ(before + after) + len(diff_text.encode("utf-8"))` theo bảng A-1.2; `total > CHANGE_MAX_TOTAL_BYTES` → `BLOCK_TOO_LARGE`. Đúng bằng trần thì nhận.

### A-1.5 Luồng (thay dòng 470, 473, 480, 532)
- §4.1 bước 2 (dòng 470): mục `edit`, `delete`, nguồn `rename` đọc tối đa `TEXT_MAX_BYTES + 1` byte rồi `text_refusal(rel, data)` (không còn `PROPOSAL_FILE_MAX_BYTES`).
- §4.1, chèn **bước 2b** trước bước 3 (dòng 473): `_propose_block` dựng `diff_text` gộp đúng một lần (từng mục bằng `_diff` hiện có, nối theo thứ tự như §2.2), gọi `check_block(…, at_apply=False, diff_text=diff_text)`, rồi `insert` **chính chuỗi đó** vào trường `diff`. Byte đã đếm và byte đã lưu là một.
- §4.2 bước 2 (dòng 480): `check_block(…, at_apply=True, diff_text=cstr(doc.diff), legacy=not is_block)`.
- §4.3 bước 1 (dòng 532): `check_block(…, at_apply=True, diff_text=cstr(doc.diff))`.
- Đề xuất dạng cũ: `diff` của chúng cũng được đếm; một file ≤ 1 MiB nên luôn dưới 8 MiB.

### A-1.6 Ghi chú gộp với FEAT-007 (thay dòng 120)
`source.py` khi FEAT-007 gộp `develop`: ngoài việc thay hai dòng kiểm trong `_base_resolve` bằng `text_refusal`, thay luôn dòng `os.path.getsize(full) > SEARCH_FILE_MAX_BYTES` của nhánh FEAT-007 (`source.py:236` trên `team/FEAT-007`) bằng đọc + `text_refusal` như A-1.4, và bỏ `SEARCH_FILE_MAX_BYTES = 1024 * 1024` (`source.py:25` trên nhánh đó). Kiểm bằng `git grep SEARCH_FILE_MAX_BYTES` = 0 dòng sau khi gộp.

### A-1.7 Touchpoints (đều đã có ở §7; 0 file mới)
| file | đổi gì |
|---|---|
| `erp_ai/constants.py` | thêm `CHANGE_FILE_MAX_BYTES` vào khối CHG-002 |
| `erp_ai/agent/tools/source.py` | `TEXT_MAX_BYTES` là tên nhập lại; `TEXT_TOO_LARGE` lấy số từ hằng; `read_source`, `search_source` qua `text_refusal`; xóa `SEARCH_FILE_MAX_BYTES`; `_scan_text` |
| `erp_ai/agent/tools/change_guard.py` | `check_block(…, diff_text)`; cách đếm tổng; chữ `BLOCK_TOO_LARGE` |
| `erp_ai/agent/tools/propose_change.py` | bước 2b; xóa `PROPOSAL_FILE_MAX_BYTES`, `TOO_LARGE` |
| `erp_ai/agent/changes/file_writer.py` | xóa `PROPOSAL_FILE_MAX_BYTES` |
| `erp_ai/agent/changes/apply_job.py` | truyền `diff_text=cstr(doc.diff)` ở áp dụng và hoàn tác |
| test: `test_source.py`, `test_change_guard.py`, `test_propose_change.py`, `test_file_writer.py`, `test_apply_block.py`, `tests/test_architecture.py` | xem A-1.8 |

### A-1.8 Test đổi và thêm
| File::test | Đổi / thêm | Kiểm gì |
|---|---|---|
| `AB::TestLimits::test_source_file_one_mib_plus_one` | đổi: bỏ chữ "chờ C-1", là test AC-43 ca 3 chính thức | 1 MiB + 1 byte: tạo, áp dụng trùng từng byte, hoàn tác trùng từng byte |
| `AB::TestLimits::test_file_over_two_mib_refused_at_apply_names_2_mib` | thêm (thay tên `test_file_over_new_ceiling_refused_names_number`) | đề xuất dựng thẳng có `after` = `CHANGE_FILE_MAX_BYTES + 1` byte → `Lỗi`, lý do chứa `2 MiB`, 0 byte ghi |
| `AB::TestLimits::test_block_over_total_bytes_refused_at_apply_names_limit` | đổi: tổng tính cả `diff`; lý do chứa `(kể cả diff)` và `8 MiB` | thời điểm áp dụng |
| `AB::TestLimits::test_form_load_at_ceiling_measured` | đổi: khối ở đúng trần mới (kể cả `diff`) | ghi số đo vào `acceptance.md` |
| `AB::TestPacketBudget::test_ceiling_block_all_empty_lines_inserts_and_reads_back` | **thêm** | khối mục `create` toàn dòng rỗng, mỗi file ≤ 2 MiB, `total == CHANGE_MAX_TOTAL_BYTES` đúng bằng (test tự assert), qua `propose_file_change` thật trên site test: `ok=true`, không có lỗi gói SQL, đọc lại bằng `frappe.get_doc` trùng từng byte ở mọi dòng con và `diff` |
| `AB::TestPacketBudget::test_ceiling_block_all_quote_lines_inserts_and_reads_back` | **thêm** | như trên, nội dung toàn dòng `'` (mỗi byte thoát thành 2) |
| `AB::TestPacketBudget::test_child_row_two_full_files_of_quotes_inserts_and_reads_back` | **thêm** | mục `edit` trên file `"'\n" × 1 Mi` dòng (đúng `CHANGE_FILE_MAX_BYTES` byte), đổi một dòng `'` thành `"` (sau cũng đúng `CHANGE_FILE_MAX_BYTES`): `insert` thành công, đọc lại trùng từng byte |
| `CG::TestCheckBlock::test_total_bytes_at_limit_ok_plus_one_refused` | đổi: tổng có `diff_text`; cả `at_apply=False` và `True` | đúng trần nhận, +1 byte từ chối `BLOCK_TOO_LARGE` |
| `CG::TestCheckBlock::test_total_counts_diff_bytes` | **thêm** | trước + sau ≤ 8 MiB nhưng cộng `diff_text` > 8 MiB → `BLOCK_TOO_LARGE`; cả hai thời điểm |
| `CG::TestCheckBlock::test_file_at_text_max_ok_plus_one_refused` | đổi: biên là `CHANGE_FILE_MAX_BYTES` (2 MiB); lý do chứa `2 MiB` | cả hai thời điểm |
| `erp_ai/agent/tools/test_source.py::TestTextRefusal::test_two_mib_ok_plus_one_refused_names_2_mib` | **thêm** | `text_refusal` ở đúng 2 MiB → `None`; +1 → `TEXT_TOO_LARGE` |
| `erp_ai/agent/tools/test_source.py::TestReadSource::test_file_between_one_and_two_mib_readable` | **thêm** | file 1,5 MiB văn bản đọc được (trước đây cũng không có trần đọc; nay có trần 2 MiB) |
| `erp_ai/agent/tools/test_source.py::TestReadSource::test_file_over_two_mib_refused_same_reason` | **thêm** | `reason == source.TEXT_TOO_LARGE` |
| `erp_ai/agent/tools/test_source.py::TestSearchSource::test_file_between_one_and_two_mib_searched_over_two_skipped` | **thêm** | file 1,5 MiB có kết quả tìm; file 2 MiB + 1 không có |
| `PC::TestProposeBlock::test_file_over_two_mib_refused_names_2_mib` | **thêm** | lúc đề xuất, 0 đề xuất |
| `erp_ai/agent/changes/test_file_writer.py::TestFileWriter` (dòng 147) | **gỡ** assertion `PROPOSAL_FILE_MAX_BYTES == 1048576` và import dòng 11 | hằng không còn; giới hạn nay ghim ở `ARCH` và `test_source` (đổi vì ADR đổi, STD-TEST-5) |
| `ARCH::TestArchitecture::test_change_file_max_bytes_defined_once_compared_only_in_text_refusal` | **thêm** | AST: `CHANGE_FILE_MAX_BYTES = <số>` đúng 1 lần, ở `erp_ai/constants.py`; phép gán khác chỉ được là `TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES` trong `source.py`; mọi phép so (`<`, `<=`, `>`, `>=`) có `TEXT_MAX_BYTES` hoặc `CHANGE_FILE_MAX_BYTES` chỉ nằm trong hàm `text_refusal` |
| `ARCH::TestArchitecture::test_search_file_max_bytes_gone` | **thêm** | tên `SEARCH_FILE_MAX_BYTES` xuất hiện 0 lần trong `erp_ai/**` (chặt hơn đòi hỏi của C-1, vì hằng đã xóa) |

---

## A-2. F-2: `confirm_restart` dùng đúng `_decider`

### A-2.1 Chữ mới
- **§3.3 dòng 326**, hàng `confirm_restart(name)` (POST):
  > Gọi `_decider(name)` đầu tiên, đúng hàm của `approve`/`reject`/`undo` (`erp_ai_change_proposal.py:93-112`): người gọi phải có `ERP AI Instructor` và không thuộc `NEVER_AUTHORITY`, nếu không thì `PermissionError` với câu của `_decider`; `System Manager` không có `ERP AI Instructor` bị từ chối. Không có đề xuất thì `DoesNotExistError` (cũng từ `_decider`). Chỉ ghi khi `restart_status = Đã gửi` và có kết luận (mục 4.4). Trả `{"name", "restart_status"}`.
- **§5 dòng 615**:
  > **`confirm_restart`:** cùng luật quyền với duyệt, từ chối, hoàn tác: `_decider` (chỉ `ERP AI Instructor`, ngoài `NEVER_AUTHORITY`; ADR-012 QĐ 4 và Ràng buộc, ADR-040 QĐ 8). Không có luật quyền thứ hai trên form. Hàm chỉ ghi kết luận rút từ bằng chứng.
- **§7 dòng 698** (`erp_ai_change_proposal.js`): form chỉ gọi `confirm_restart` khi `frappe.user.has_role("ERP AI Instructor")`. Người chỉ có `System Manager` mở form thì không có lời gọi, không có hộp lỗi; nhãn vẫn là `Restart: đã gửi lúc {giờ}, chờ xác nhận.` Kiểm quyền thật vẫn ở server.

Hệ quả ghi nhận: kết luận restart chỉ được ghi khi một Instructor mở form. Đây vẫn là xác nhận lười của §4.4 (D-5); không thêm lối chạy nền.

### A-2.2 Touchpoints
`erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` (gọi `_decider`), `erp_ai_change_proposal.js` (điều kiện vai trò), `test_erp_ai_change_proposal.py`. Đều đã có ở §7.

### A-2.3 Test đổi và thêm
| File::test | Đổi / thêm | Kiểm gì |
|---|---|---|
| `DOC::TestConfirmRestart::test_system_manager_allowed` | **thay** bằng `test_system_manager_without_instructor_refused_status_unchanged` | user chỉ có `System Manager` → `PermissionError`; `restart_status` vẫn `Đã gửi`; `transitions.confirm_restart` (stub) 0 lần gọi |
| `DOC::TestConfirmRestart::test_instructor_records_conclusion` | **thêm** | user có `ERP AI Instructor` (có hoặc không có `System Manager`), bằng chứng stub cho kết luận → ghi `Đã xác nhận` |
| `DOC::TestConfirmRestart::test_uses_decider` | **thêm** | `patch.object(module, "_decider")` → được gọi đúng 1 lần với `name` trước mọi lần đọc bằng chứng |
| `DOC::TestConfirmRestart::test_agent_account_refused`, `test_administrator_guest_no_role_refused`, `test_missing_proposal_does_not_exist`, `test_only_from_sent`, `test_no_conclusion_writes_nothing` | giữ | — |
| `DOC::TestChangeProposalFormScript::test_confirm_restart_called_only_for_instructor` | **thêm** | lời gọi `confirm_restart` trong JS nằm trong nhánh `frappe.user.has_role("ERP AI Instructor")` |

---

## A-3. F-3: `remove_file` và `remove_empty_dirs` kiểm lại `.git*` và symlink

### A-3.1 Chữ mới (§3.5, thay dòng 343, 345, 346)
Một hàm riêng trong `file_writer.py`, dùng chung cho mọi thao tác ghi, xóa, tạo thư mục (STD-DESIGN-4), thay `_refuse_git_dir`:

`_refuse_unsafe_path(full_path) -> None`, ném `ValueError` khi:
1. `rel = os.path.relpath(os.path.abspath(full_path), os.path.realpath(source.get_source_root()))` bắt đầu bằng `..` hoặc là tuyệt đối (ngoài gốc `apps/`);
2. một thành phần của `rel` bắt đầu bằng `.git` (`.git`, `.github`, `.gitignore`, `.gitmodules`…), cùng luật với `text_refusal`;
3. `os.path.realpath(os.path.dirname(abspath)) != os.path.dirname(abspath)` (một thư mục cha nào đó là symlink).

| Hàm | Hợp đồng mới |
|---|---|
| `write_atomic(full, content, *, new_file)` (dòng 343) | Gọi `_refuse_unsafe_path(full)` trước khi tạo file tạm. Còn lại giữ nguyên. |
| `make_parents(full_path, app_dir)` | Như `design.md` dòng 344; kiểm sau mỗi thư mục dùng `_refuse_unsafe_path(d)` cộng `os.path.islink(d)`. |
| `remove_file(full)` (dòng 345) | Thứ tự: `_refuse_unsafe_path(full)`; rồi `os.path.islink(full)` hoặc `not os.path.isfile(full)` → `ValueError`; rồi `os.remove(full)`. Mọi kiểm làm **ngay trước** `os.remove`, sau `check_block` lúc áp dụng. Dùng cho Xóa, gỡ file đã tạo, đích đổi tên khi hoàn tác, và đường trả lại. |
| `remove_empty_dirs(dirs)` (dòng 346) | Duyệt từ sâu nhất lên. Với mỗi `d`: **bỏ qua** (không `rmdir`, không lỗi, không có trong danh sách trả về) khi `os.path.islink(d)`, hoặc `_refuse_unsafe_path(d)` ném lỗi, hoặc `realpath(d) != abspath(d)`, hoặc thư mục không rỗng. Còn lại `os.rmdir(d)`. Trả danh sách đã gỡ. |

`ValueError` của `remove_file` ở bước 6 của §4.2 đi vào đường trả lại ngược hiện có (kết quả `Lỗi`, 0 commit); ở bước 3 của §4.3 đi vào đường trả về trạng thái đã áp dụng. Không thêm trạng thái hay câu lỗi cho model.

Rủi ro còn lại, ghi nhận: giữa phép kiểm và `os.remove` vẫn còn một khe rất ngắn. Chỉ một tiến trình của chính user `miyano` mới thay được thư mục trong khe đó, và user đó vốn đã ghi được mọi file của bench. Không thêm cơ chế `dir_fd` (STD-DESIGN-5).

### A-3.2 Touchpoints
`erp_ai/agent/changes/file_writer.py`, `erp_ai/agent/changes/test_file_writer.py`, `erp_ai/agent/changes/test_apply_block.py`. Đều đã có ở §7; chú thích dòng 686 và 712 thêm "`_refuse_unsafe_path`; `remove_file` và `remove_empty_dirs` kiểm lại `.git*` và symlink (ADR-040 Ràng buộc)".

### A-3.3 Test thêm
| File::test | Kiểm gì |
|---|---|
| `erp_ai/agent/changes/test_file_writer.py::TestRemoveFile::test_parent_dir_symlink_refused_zero_removed` | trong `TempAppsRoot`: thư mục `myapp/pkg` bị thay bằng symlink tới một thư mục ngoài app có file cùng tên → `ValueError`; file ngoài app còn nguyên byte; 0 file bị xóa |
| `…::TestRemoveFile::test_git_component_refused_file_kept` | `myapp/.github/x.yml` và `myapp/.gitignore` → `ValueError`, file còn |
| `…::TestRemoveFile::test_symlink_or_directory_refused` | đích là symlink, hoặc thư mục → `ValueError`, không gì bị xóa |
| `…::TestRemoveFile::test_outside_source_root_refused` | đường dẫn ngoài gốc `apps/` → `ValueError` |
| `…::TestRemoveFile::test_regular_file_removed` | file thường → bị xóa |
| `…::TestRemoveEmptyDirs::test_symlink_dir_skipped_target_untouched` | thư mục trong danh sách là symlink tới thư mục rỗng ngoài app → không `rmdir`, đích còn, không có trong kết quả |
| `…::TestRemoveEmptyDirs::test_git_component_dir_skipped` | `myapp/.github/empty` rỗng → không bị gỡ |
| `…::TestRemoveEmptyDirs::test_deepest_first_nonempty_kept` | thứ tự sâu nhất lên; thư mục còn `__pycache__` được để nguyên |
| `…::TestWriteAtomic::test_parent_symlink_and_git_component_refused` | điều kiện mới của `write_atomic` |
| `AB::TestDelete::test_parent_swapped_to_symlink_after_check_zero_deleted_outside` | `patch` bọc `change_guard.check_block` thật, sau khi nó trả về thì đổi thư mục cha của mục Xóa thành symlink ra ngoài app → `Lỗi`, 0 commit, file ngoài app còn nguyên, các mục trước trả lại trùng từng byte |

---

## A-4. Điểm nhỏ (1): đầu ra của `sudo -n -l` (§5.1 bước 3, thay dòng 642)
Quyết ở đây. Chữ mới của gạch đầu tiên:

> `sudo -n -l` → có **một** mục `(root) NOPASSWD:` liệt kê đúng ba lệnh `/usr/bin/supervisorctl status`, `/usr/bin/supervisorctl restart frappe-bench-web:`, `/usr/bin/supervisorctl restart frappe-bench-workers:` (sudo có thể in chúng trên một dòng cách nhau bởi dấu phẩy, hoặc xuống dòng), không lệnh nào khác trong mục đó. Nếu `miyano` thuộc nhóm `sudo` thì còn có mục `(ALL : ALL) ALL`; mục này có từ trước, đòi mật khẩu, không do tệp của CHG-002 sinh ra và **không** làm AC-57 trượt. AC-57 đạt khi mục `NOPASSWD` đúng ba lệnh và hai gạch "bị từ chối" bên dưới vẫn bị từ chối với `sudo -n`.

Không có test tự động đổi (AC-57 là bước người). Touchpoint: không có (chỉ chữ của design và của `acceptance.md`).

## A-5. Điểm nhỏ (2): `SETSID_EXECUTABLE` (§3.4, thay dòng 336; §8.2 dòng 794)
Quyết ở đây: **làm**.
- Căn cứ đã đọc: `source.py:77-78` cho `TIMEOUT_EXECUTABLE = "timeout"` và `BENCH_EXECUTABLE = "bench"`, cũng là tên trần, tra theo `PATH` của `_minimal_env()` (`process_runner.py:13`, `:29-30`). "Do server xác định" (ADR-013 QĐ 7) ở mã hiện có nghĩa là hằng trong mã, không lấy từ đầu vào của model. Vì vậy `setsid` đi theo đúng mẫu đó; không đổi sang đường dẫn tuyệt đối (sẽ lệch với hai hằng kia, và đường dẫn production là `UNVERIFIED`).
- Chữ mới: thêm `SETSID_EXECUTABLE = "setsid"` ở `source.py`, ngay cạnh `TIMEOUT_EXECUTABLE` và `BENCH_EXECUTABLE`.
  `RESTART_ARGV = (source.SETSID_EXECUTABLE, "-f", source.TIMEOUT_EXECUTABLE, "-s", "KILL", str(RESTART_TIMEOUT_S), source.BENCH_EXECUTABLE, "restart")`.
- §8.2 hàng `test_restart_launch_shape` (dòng 794), luật mới: chuỗi `"setsid"` xuất hiện đúng 1 lần trong `erp_ai/**` ngoài test, là giá trị của `SETSID_EXECUTABLE` trong `source.py`; tên `SETSID_EXECUTABLE` được dùng làm phần tử argv đúng 1 lần, là phần tử 0 của `RESTART_ARGV` trong `process_runner.py`; các điều kiện DEVNULL ×3, `timeout=`, `cwd=`, `env=` không chứa `os.environ` giữ nguyên. Như vậy vẫn đúng Ràng buộc của ADR-040 ("phần tử argv đúng một lần, ở `process_runner.py`").
- Touchpoints: `source.py`, `process_runner.py`, `test_process_runner.py` (`TestLaunchRestart::test_argv_shape` so với các hằng), `tests/test_architecture.py`.

## A-6. Điểm nhỏ (3): cùng gốc thời gian trước khi so (§4.4, thay dòng 572–577)
Quyết ở đây. Căn cứ đã đọc: rq 1.15.1 ghi `birth_date = utcnow()` là `datetime.utcnow()` không múi giờ (`rq/worker.py:799-801`) và đọc lại bằng `utcparse` cũng không múi giờ (`rq/worker.py:1111`, `rq/utils.py:143-148`); `psutil.Process.create_time()` là epoch; `restart_sent_at` là Datetime của Frappe, ghi bằng `now_datetime()`, không múi giờ, theo múi giờ hệ thống của site.

Chữ mới: `restart_check.py` đổi mọi mốc về **epoch giây (UTC)** trước khi gọi `outcome`, bằng hai hàm thuần:
- `epoch_of_naive_utc(dt) -> float` = `dt.replace(tzinfo=datetime.timezone.utc).timestamp()`, cho `birth_date` của rq;
- `epoch_of_system_time(dt, tz_name) -> float` = `dt.replace(tzinfo=zoneinfo.ZoneInfo(tz_name)).timestamp()`, cho `restart_sent_at`, với `tz_name = frappe.utils.get_system_timezone()`;
- web: `create_time()` dùng thẳng; now: `time.time()`.
- Cấm gọi `.timestamp()` trên `datetime` không múi giờ trong `restart_check.py` (khi đó Python dùng múi giờ của tiến trình).
- `outcome(sent_epoch, now_epoch, web_epoch, workers_epoch)` giữ nguyên luật so (dòng 574–577).

Touchpoints: `erp_ai/agent/changes/restart_check.py`, `erp_ai/agent/changes/test_restart_check.py` (đều đã có ở §7; chú thích dòng 684 thêm "đổi mọi mốc về epoch UTC").

Test thêm:
| File::test | Kiểm gì |
|---|---|
| `RS::TestEpoch::test_rq_naive_utc_and_system_tz_compare_on_same_base` | `restart_sent_at` = 10:00 với `tz_name = "Asia/Ho_Chi_Minh"` (UTC+7) và `birth_date` = 03:00:01 không múi giờ (UTC) → worker sau lúc gửi; 02:59:59 → trước lúc gửi |
| `RS::TestEpoch::test_independent_of_process_timezone` | đặt `TZ=America/New_York` bằng `patch.dict(os.environ)` + `time.tzset()`, trả lại trong `finally`/`addCleanup` (STD-TEST-6) → kết quả hai hàm không đổi so với khi `TZ=UTC` |

---

## 7. Bảng touchpoints sau addendum
Không thêm file mới; không bớt file. Mọi file ở A-1..A-6 đã có trong §7 của `design.md`. Thay đổi chỉ ở cột "ghi chú" (dòng 680, 681, 682, 684, 686, 687, 698, 712, 713, 716 và `erp_ai/tests/test_architecture.py` dòng 700) như các mục trên.

**Đối chiếu file mới với `allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
(không có file mã mới)
docs/team/features/CHG-002/design-addendum-1.md -> docs
```
**Đối chiếu với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** 0 khớp.

## 8. Test plan sau addendum

### 8.1 Hàng thay thế của bảng tiêu chí
Chỉ ghi các hàng đổi. Các hàng AC khác của `design.md` §8.1 giữ nguyên.

| Tiêu chí | Test | Loại | Đường lỗi / biên |
|---|---|---|---|
| AC-40 (thay dòng 767) | `AB::TestDelete::test_delete_removes_file_commit_records_deletion` | integration | `PC::TestProposeBlock::test_delete_directory_refused`; `…::test_delete_missing_refused`; `…::test_delete_dirty_refused`; `…::test_delete_untracked_refused`; `…::test_delete_binary_refused`; `…::test_delete_executable_refused`; `AB::TestDelete::test_changed_since_proposal_stale_zero_deleted`; `AB::TestDelete::test_undo_restores_bytes`; **mới** `AB::TestDelete::test_parent_swapped_to_symlink_after_check_zero_deleted_outside`; **mới** `erp_ai/agent/changes/test_file_writer.py::TestRemoveFile::test_parent_dir_symlink_refused_zero_removed`, `…::test_git_component_refused_file_kept`, `…::TestRemoveEmptyDirs::test_symlink_dir_skipped_target_untouched` |
| AC-43 (thay dòng 770) | `AB::TestLimits::test_new_file_20001_chars_applies_and_undoes`; `…::test_edit_with_11_replacements`; `…::test_source_file_one_mib_plus_one` | integration | `CG::TestCheckBlock::test_ops_50_ok_51_refused`; `…::test_total_bytes_at_limit_ok_plus_one_refused` (có `diff`); **mới** `…::test_total_counts_diff_bytes`; `…::test_commands_6_ok_7_refused`; `…::test_file_at_text_max_ok_plus_one_refused` (2 MiB); cả hai thời điểm; **mới** `PC::TestProposeBlock::test_file_over_two_mib_refused_names_2_mib`; **mới** `AB::TestLimits::test_file_over_two_mib_refused_at_apply_names_2_mib`; `AB::TestLimits::test_block_over_total_bytes_refused_at_apply_names_limit`; **mới** `AB::TestPacketBudget::test_ceiling_block_all_empty_lines_inserts_and_reads_back`, `…::test_ceiling_block_all_quote_lines_inserts_and_reads_back`, `…::test_child_row_two_full_files_of_quotes_inserts_and_reads_back`; `AB::TestLimits::test_form_load_at_ceiling_measured` (ghi số đo) |
| AC-44 (thay dòng 771) | `PC::TestProposeBlock::test_text_files_any_extension_created` | integration | `…::test_binary_png_pyc_refused`; `…::test_create_with_nul_refused`; `…::test_pem_key_gitignore_refused`; `erp_ai/agent/tools/test_source.py::TestTextRefusal::test_order_and_reasons`; **mới** `…::TestTextRefusal::test_two_mib_ok_plus_one_refused_names_2_mib`; **mới** `…::TestReadSource::test_file_between_one_and_two_mib_readable`, `…::TestReadSource::test_file_over_two_mib_refused_same_reason`, `…::TestSearchSource::test_file_between_one_and_two_mib_searched_over_two_skipped` |
| AC-46 (thay dòng 773) | `CG::TestCheckBlock::test_py_syntax_error_refused_with_line`; `…::test_json_invalid_refused_with_line` | unit | `AB::TestRestart::test_syntax_rechecked_at_apply_zero_written`; `…::test_notice_comment_exists_before_launch_stub_called`; `RS::TestOutcome::test_both_started_after_confirmed`; `…::test_web_old_after_deadline_unconfirmed`; `…::test_before_deadline_no_conclusion`; `…::test_redis_or_psutil_error_is_no_evidence`; **mới** `RS::TestEpoch::test_rq_naive_utc_and_system_tz_compare_on_same_base`, `…::test_independent_of_process_timezone`; `DOC::TestConfirmRestart::test_only_from_sent`; **mới** `DOC::TestConfirmRestart::test_instructor_records_conclusion` |
| AC-55 (thay dòng 782) | `AB::TestNoSelfApproval::test_agent_admin_guest_no_role_refused_both_paths_block` | integration | `…::test_model_claims_approved_zero_applied_zero_restart`; `DOC::TestConfirmRestart::test_agent_account_refused`; **mới** `DOC::TestConfirmRestart::test_system_manager_without_instructor_refused_status_unchanged`; **mới** `…::test_uses_decider`; **mới** `DOC::TestChangeProposalFormScript::test_confirm_restart_called_only_for_instructor`; các test AC-33 có sẵn của site_api vẫn xanh |
| AC-57 (thay dòng 784) | Bước người sau G4 (A-4: mục `(root) NOPASSWD:` đúng ba lệnh; `(ALL : ALL) ALL` của nhóm `sudo` nếu có không làm trượt), hai lệnh `supervisorctl` khác bị từ chối với `sudo -n`; `grep` repo tìm mật khẩu = 0 | manual | `ARCH::TestArchitecture::test_no_sudo_or_supervisorctl_argv` |

### 8.2 Luật kiến trúc: hàng đổi và thêm
| Luật | Tên test |
|---|---|
| `"setsid"` đúng 1 lần (giá trị `SETSID_EXECUTABLE` ở `source.py`); `SETSID_EXECUTABLE` là phần tử argv đúng 1 lần, phần tử 0 của `RESTART_ARGV` ở `process_runner.py`; DEVNULL ×3, `timeout=`, `cwd=`, `env=` không chứa `os.environ` (thay dòng 794) | `test_restart_launch_shape` |
| `CHANGE_FILE_MAX_BYTES` định nghĩa 1 lần ở `constants.py`; chỉ `text_refusal` so kích thước với nó (ADR-040 C-1, Ràng buộc của phán quyết) | **mới** `test_change_file_max_bytes_defined_once_compared_only_in_text_refusal` |
| `SEARCH_FILE_MAX_BYTES` không còn trong `erp_ai/**` | **mới** `test_search_file_max_bytes_gone` |
| Giới hạn được định nghĩa một lần trong `constants.py` (nay gồm `CHANGE_FILE_MAX_BYTES`) | `test_change_limits_defined_once` (mở rộng) |

### 8.3 Đối chiếu AC (spec ↔ test plan) sau addendum
```
spec:      AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
test plan: AC-36 AC-37 AC-38 AC-39 AC-40 AC-41 AC-42 AC-43 AC-44 AC-45 AC-46 AC-47 AC-48 AC-49 AC-50 AC-51 AC-52 AC-53 AC-54 AC-55 AC-56 AC-57 | NFR-12 NFR-13 NFR-14 NFR-15
```
Vẫn trùng 22/22 AC và 4/4 NFR. Addendum chỉ thay 6 hàng (AC-40, 43, 44, 46, 55, 57); không AC nào mất test.

**Test cũ phải sửa, thêm vào danh sách §8.3 của `design.md`** (đổi vì ADR-040 C-1 và ADR-012 QĐ 4, STD-TEST-5):
- `test_file_writer.py:147` (ghim `PROPOSAL_FILE_MAX_BYTES == 1048576`): gỡ;
- câu `file lớn hơn 1 MiB` ở test của `propose_change` nếu có: thành `file lớn hơn 2 MiB` qua `source.TEXT_TOO_LARGE`.

## Ghi chú cho tech-lead (con trỏ, không chia task)
Các dòng của `tasks.md` (bản đang viết, đọc 2026-11-15) trích chữ mà addendum này thay:
- `tasks.md:53`: `TEXT_MAX_BYTES = SEARCH_FILE_MAX_BYTES` → A-1.2;
- `tasks.md:69`: `remove_file` → A-3.1 (`_refuse_unsafe_path`, kiểm cha);
- `tasks.md:64`: `remove_empty_dirs` → A-3.1 (bỏ qua symlink và `.git*`);
- `tasks.md:81`: `RESTART_ARGV` → A-5;
- `tasks.md:109-111`, `:186`: chữ ký `check_block` có `diff_text`; test tổng → A-1.4, A-1.8;
- `tasks.md:167`: `web_started`/`workers_started`/`outcome` → A-6;
- `tasks.md:173-174`: luật quyền và `test_system_manager_allowed` → A-2;
- `tasks.md:333-335`: giá trị và tên hằng đã có (`CHANGE_FILE_MAX_BYTES` ở `constants.py`, đã là touchpoint), không cần `NEEDS_CONTEXT`.

## Assumptions decided by the team (thêm)
| # | Chọn | Vì | Phương án khác | Sai thì sửa thế nào |
|---|---|---|---|---|
| D-15 | `diff_text` là tham số bắt buộc của `check_block`; `_propose_block` đếm và lưu cùng một chuỗi | Không chỗ gọi nào quên đếm `diff`; byte đếm = byte lưu (ADR-040 C-1 điểm 3) | `check_block` tự dựng diff | Dời việc dựng diff vào `check_block` |
| D-16 | Xóa `SEARCH_FILE_MAX_BYTES`, `propose_change.PROPOSAL_FILE_MAX_BYTES`, `TOO_LARGE`, `file_writer.PROPOSAL_FILE_MAX_BYTES` | Không còn người dùng sau C-1 (STD-STYLE-5) | Giữ làm tên khác | Thêm lại tên nhập lại của `CHANGE_FILE_MAX_BYTES` |
| D-17 | Form chỉ gọi `confirm_restart` cho người có `ERP AI Instructor` | Người chỉ có `System Manager` sẽ gặp hộp `PermissionError` mỗi lần mở form | Gọi cho mọi người, nuốt lỗi ở JS | Bỏ điều kiện ở JS |
| D-18 | `remove_empty_dirs` bỏ qua thư mục không an toàn, không ném lỗi | Thư mục rỗng còn sót là vô hại; ném lỗi ở cuối hoàn tác sẽ biến một hoàn tác đã đúng file thành `Lỗi` | Ném `ValueError` | Đổi thành ném lỗi và cho đường hoàn tác xử lý |
| D-19 | `setsid` là hằng tên trần, theo mẫu của `timeout`/`bench` | ADR-013 QĐ 7 theo cách mã hiện có hiểu | Đường dẫn tuyệt đối cho cả ba | ADR mới nếu cần đường dẫn tuyệt đối |

Câu hỏi nghiệp vụ: 0. Câu hỏi cho người: 0. Điểm chờ vai khác: 0.

## Căn cứ đã đọc (2026-11-15, `develop` @ `2fd42ad`, chỉ đọc)
- `docs/team/features/CHG-002/arch-review-design.md` (toàn bộ); `docs/team/adr/ADR-040.md` (toàn bộ, gồm Phán quyết C-1); `docs/team/features/CHG-002/design.md` (886 dòng, toàn bộ); `docs/team/features/CHG-002/tasks.md` (grep các dòng liên quan).
- `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:93-112`: `_decider` chỉ nhận `ERP AI Instructor`, ngoài `NEVER_AUTHORITY`.
- `erp_ai/agent/changes/file_writer.py:11`, `:18-20`, `:31-53`: `PROPOSAL_FILE_MAX_BYTES` không dùng trong module; `_refuse_git_dir` chỉ chặn đúng tên `.git`; `remove_created` không kiểm thư mục cha.
- `erp_ai/agent/tools/source.py:37`, `:77-78`, `:146-160`, `:180-190`, `:196-226`: `SEARCH_FILE_MAX_BYTES`; `TIMEOUT_EXECUTABLE`, `BENCH_EXECUTABLE` là tên trần; `read_source` hôm nay không có trần kích thước và đọc `errors="replace"`; `search_source` so `getsize` với `SEARCH_FILE_MAX_BYTES`.
- `erp_ai/agent/tools/propose_change.py:31`, `:38`, `:172-174`: `PROPOSAL_FILE_MAX_BYTES`, `TOO_LARGE`.
- `erp_ai/agent/changes/process_runner.py:13`, `:29-30`: `ENV_ALLOWLIST` có `PATH`; `_minimal_env`.
- `erp_ai/agent/changes/test_file_writer.py:11`, `:147`: ghim 1 MiB.
- `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json:226-229`: `diff` là `Code` (longtext).
- `erp_ai/test_utils.py:304-308`, `:361`: `TempAppsRoot`/`GitSandbox` vá `source.get_source_root`, nên `_refuse_unsafe_path` chạy được trong test.
- `env/lib/python3.12/site-packages/rq/worker.py:799-801`, `:1111`; `rq/utils.py:127-148`: `birth_date` là UTC không múi giờ.
- `git grep SEARCH_FILE_MAX_BYTES team/FEAT-007`: `file_writer.py:11`, `source.py:25`, `source.py:236`, cùng các chỗ như `develop`.
