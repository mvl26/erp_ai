Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 64 — FEAT-007 T64

- Diff: `git diff aef271c7b12094afe23711003ee2d7a5fc32cbef..7fbd1b3` (nhánh `team/FEAT-007-task-64`; 2 commit `57b9ae8`, `7fbd1b3`; 2 file)
- Vòng: 3 (trần `max_rework` = 3); diff cả task sau vòng 3: `git diff aef271c7b12094afe23711003ee2d7a5fc32cbef..aedd97f`
- Verdict cuối: approve ở vòng 3; merge `b7c925d` trên `team/FEAT-007` (mục "Vòng 3" bên dưới).
- Verdict hai vòng đầu: request-changes ở cả hai vòng; CHƯA merge. Tech-lead DỪNG task theo luật phá vòng lặp (cùng một lỗi hai vòng liền) và báo team-leader; phán quyết ở cuối file.
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — request-changes

- Diff vòng: `git diff aef271c..57b9ae8` (`erp_ai_setting.json` +2/−2, `test_doctype_descriptions.py` +18/−3).
- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `test_doctype_descriptions` `Ran 12 tests ... FAILED (failures=2)`: `test_required_phrases_present`: `- {'catalog_rules': ['chờ Duyệt', 'Đổi trường', 'bảng con'], 'permission_level': ['đề xuất', 'Tự làm']} : ERP AI Setting: thiếu cụm`; `test_forbidden_phrases_absent`: `- {'catalog_rules': ['bot không ghi ERP ngoài phiếu'], 'permission_level': ['L2 có công cụ như L1']} : ERP AI Setting: còn cụm sai`; GREEN (một lần giữ khóa, migrate rồi test): `Ran 12 tests in 0.359s OK`; `test_erp_ai_setting` `Ran 103 tests in 7.664s OK`.
- Tier 1: ba ý mới của AC-29 có đủ trong `catalog_rules`; ý L2 có trong `permission_level`; không đổi mã, `default`, `field_count`, dữ liệu; 399 và 385 ký tự. Có lỗi hiểu sai: khi rút gọn cho vừa 400 ký tự dev sửa cả vế cũ ngoài tiêu chí.
- Checklist (10): 1 trượt · 2 đạt · 3 đạt · 4 đạt · 5 không áp dụng · 6 đạt · 7 đạt · 8 đạt · 9 không áp dụng · 10 đạt.

### Findings

- major | STD-DESIGN-5 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:118` | Viết lại các vế `permission_level` mà tiêu chí không yêu cầu, làm đổi nghĩa: "L3: thêm công cụ bản ghi chung, sửa code" bỏ điều kiện hai ô công tắc của AC-3(2) và nghịch với mô tả `record_tools_enabled`; "tự hạ về L1" thành "hạ về L1" mất ý tự động khi vượt ngân sách | Giữ "L3: mức của công cụ bản ghi chung, sửa code" và giữ "tự hạ về L1"; lấy chỗ trong 400 ký tự từ những vế không mang hành vi; cân nhắc thêm "mức của" hoặc "tự hạ" vào `phrases`
- minor | STD-DESIGN-5 | `erp_ai_setting.json:118` | (a) bỏ "Mức thực tế" khỏi câu `design.md:184` đặt sẵn | giữ nguyên câu
- minor | STD-DESIGN-5 | `erp_ai_setting.json:252` | (b) "Không có dòng nào" thu AC-29 (5) "không dòng nào phủ" về bảng rỗng (Returns cũng viết vậy) | dev's call
- minor | STD-TEST-8 | `erp_ai/tests/test_doctype_descriptions.py:69-79` | (c) ghim chữ "Đổi trường" nhưng không ghim ý "bị từ chối/cần một dòng" | thêm cụm

### Không kiểm được từ diff (vòng 1)

- Meta trên site `miyano` sau migrate có trùng JSON không: chỉ có lời dev; tech-lead chạy lại sau merge (chưa tới bước đó).
- Bảng chữ ở `design.md:175,184` vẫn là chữ cũ: việc của designer, chuyển team-leader.
- Thông báo AC-4 (D-7) có lấy chữ của `permission_level` không: chưa giải, xem lúc task chạy tiếp.

## Vòng 2 — request-changes (scoped re-review)

- Diff vòng: `git diff 57b9ae8..7fbd1b3` (`erp_ai_setting.json` +1/−1, `test_doctype_descriptions.py` +15/−1).
- Ghi chú về nhánh: dev vòng 2 không `git switch` được nhánh task (worktree vòng 1 còn giữ nó), commit `7fbd1b3` ở HEAD rời trên `57b9ae8`; tech-lead gỡ worktree vòng 1 (sạch) rồi `git branch -f team/FEAT-007-task-64 7fbd1b3` (fast-forward).
- Bằng chứng của dev: RED trên `57b9ae8`: `AssertionError: {'permission_level': ['L3: mức của công cụ[57 chars]ếu']} != {}` … `Ran 12 tests in 0.373s` `FAILED (failures=1)`; GREEN `Ran 12 tests in 0.338s` `OK`, `test_erp_ai_setting` `Ran 103 tests in 7.070s` `OK`.
- Finding vòng 1: major → ADDRESSED ("L3: mức của công cụ bản ghi chung, sửa code" và "tự hạ về L1" đã về; `test_doctype_descriptions.py:30-43` ghim ba cụm) · minor (a) → ADDRESSED · minor (b) → NOT ADDRESSED, không cần làm (`design.md` nêu đúng cụm đó là bắt buộc) · minor (c) → ADDRESSED (`test_doctype_descriptions.py:91` ghim "bị từ chối").
- Độ dài `permission_level`: `aef271c` 400, `57b9ae8` 399, `7fbd1b3` 398 ký tự.

### Findings mới (do chính lần sửa gây ra)

- major | STD-DESIGN-5 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:118` | Để về dưới 400 ký tự, lần sửa viết lại thêm hai vế cũ mà tiêu chí không đòi đổi: (1) L1 mất "đọc dữ liệu" (chữ gốc và vòng 1 đều có "L1: đọc dữ liệu, ..."; nay "L1: ghi phân loại, gợi ý lên phiếu, bình luận", và vì L0 nói "chỉ phân loại" nên form không còn nói mức nào được đọc dữ liệu); (2) L0 đổi "không sửa phiếu, không bình luận" thành "không sửa phiếu hay bình luận", đọc được thành "không sửa phiếu hay sửa bình luận", mất lệnh cấm đăng bình luận | Trả lại "đọc dữ liệu" cho L1, viết L0 rõ là không ghi gì lên phiếu; lấy chỗ từ chữ không mang hành vi; thêm "đọc dữ liệu" vào `phrases` của `permission_level`
- minor | STD-DESIGN-5 | `erp_ai_setting.json:118` | "ghi phân loại hoặc gợi ý" thành "ghi phân loại, gợi ý": không khác nghĩa | dev's call

### Không kiểm được từ diff (vòng 2)

- Mức nào mở công cụ đọc dữ liệu trong mã: reviewer không tìm ra bằng `git grep`; tech-lead cũng chưa xác định được bằng một phép `git grep` trên `registry.py`. Phán quyết dưới không dựa vào điểm này: vế "L1: đọc dữ liệu" là chữ đã duyệt ở `aef271c` và tiêu chí của T64 không cho đổi nó.

## Phán quyết của tech-lead (dừng ở vòng 2/3: cùng lỗi STD-DESIGN-5 ở `erp_ai_setting.json:118` hai vòng liền)

| Finding còn mở | Phán |
|---|---|
| major vòng 2 (L1 mất "đọc dữ liệu", L0 mơ hồ) | Có thật, CHẶN merge. Nguyên nhân không nằm ở dev: mô tả `permission_level` gốc đã đúng 400 ký tự, Returns đòi thêm ý L2 và giữ ≤ 400, nên vòng nào cũng phải bớt một vế cũ; vế nào được bớt là việc chọn chữ của thiết kế (`design.md:184`), dev tự chọn thì reviewer lại bắt. Một vòng nữa theo cách cũ sẽ lặp lần ba. |
| minor vòng 2 | Có thật, hoãn (dev's call). |
| minor (b) vòng 1 | Reviewer tự rút: giữ nguyên là đúng. |

- Cần: team-leader nhờ designer chốt NGUYÊN VĂN mô tả `permission_level` ≤ 400 ký tự (và sửa `design.md:175,184`). Chuỗi reviewer đề nghị, reviewer đếm tay khoảng 399 ký tự, chưa đo lại: "L0: chỉ phân loại phiếu mới vào Log, không ghi gì lên phiếu. L1: đọc dữ liệu, ghi phân loại, gợi ý lên phiếu, bình luận. Từ L2: ghi ERP ngoài phiếu qua đề xuất hoặc dòng Tự làm. L3: mức của công cụ bản ghi chung, sửa code. Mức thực tế của từng phiếu trên đường danh mục trắng không vượt Mức tối đa của đầu mục; năm quyền mở rộng tính theo ô này. Vượt ngân sách tháng thì tự hạ về L1 (L0 giữ nguyên)."
- Sau khi có chuỗi: vòng 3/3 (vòng cuối trong trần), một dev mới dán đúng chuỗi đó, thêm "đọc dữ liệu" vào `phrases`, test đỏ trước; scoped re-review `7fbd1b3..HEAD`.
- Trạng thái: nhánh `team/FEAT-007-task-64` @ `7fbd1b3` giữ lại, chưa merge, không còn worktree dev. Phần `catalog_rules` (385 ký tự) đã đạt ở cả hai vòng.

## Vòng 3 — approve (scoped re-review, vòng cuối của trần 3)

- Cập nhật đầu file: diff cả task `git diff aef271c7b12094afe23711003ee2d7a5fc32cbef..aedd97f`; diff của vòng `git diff 7fbd1b3..aedd97f` (2 commit `492d8c9` test, `aedd97f` chuỗi; 2 file, 6 dòng đổi). Vòng: 3 (trần `max_rework` = 3). Verdict cuối: approve; merge `b7c925d` trên `team/FEAT-007`.
- Căn cứ của vòng: `design-w1-fixes-1.md` Điểm 1 (designer chốt nguyên văn chuỗi `permission_level`, 399 ký tự) và dòng Returns, Expect của T64 đã thay theo đó (chèn 7 của `tasks.md`).
- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `7fbd1b3` + 4 cụm, `MIGRATE_EXIT=0`: `AssertionError: {'permission_level': ['đọc dữ liệu', 'khôn[46 chars]ếu']} != {}` … `: ERP AI Setting: thiếu cụm`, `Ran 12 tests in 0.366s FAILED (failures=1)`; phép đo của dev `len 399 NFC True utf8_bytes 523 identical_to_design_line20 True ref_len 399`, `catalog_rules len 385`; GREEN @ `aedd97f`, `MIGRATE_EXIT=0`: test_doctype_descriptions `Ran 12 tests in 0.355s OK`, test_erp_ai_setting `Ran 103 tests in 7.560s OK`.
- Finding vòng 2 (major STD-DESIGN-5, `erp_ai_setting.json:118`): `ADDRESSED`. Reviewer tự đo, không dùng số của dev: `git show aedd97f:…/erp_ai_setting.json | python3 -I -c …` → `len 399 NFC True bytes 523 identical True ref_len 399`, `catalog_rules len 385`. L1 có lại "đọc dữ liệu"; L0 nay là "không ghi gì lên phiếu".
- Bốn phép kiểm tech-lead yêu cầu: (1) trùng từng byte với dòng 20 của phán quyết: đạt; (2) diff JSON của vòng đúng một dòng (`description` của `permission_level`), cả task chỉ hai hunk (`permission_level`, `catalog_rules`), thứ tự trường, mặc định, số trường không đổi: đạt; (3) diff test của vòng chỉ thêm 4 cụm, 10 cụm cũ giữ, `FORBIDDEN_PHRASES` nguyên, không nới khẳng định, không skip: đạt; (4) file đổi nằm trong `files:`, commit đúng dạng, không dòng ghi công AI: đạt.
- Finding mới trong dải sửa: không có.

### Không kiểm được từ diff (vòng 3) — tech-lead giải

- Reviewer không chạy test site. Tech-lead chạy sau merge trên `team/FEAT-007` @ `b7c925d`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_doctype_descriptions `Ran 12 tests in 0.350s OK`, test_erp_ai_setting `Ran 103 tests in 7.064s OK`, test_architecture `Ran 181 tests in 15.427s OK`; `cmd.lint` mọi hook `Passed`.

## deferred

- `test_doctype_descriptions.py:89-92` ghim "Đổi trường" và "bị từ chối" thành hai cụm rời, không kiểm chúng cùng một câu.
- `design.md:175,184` còn chữ cũ (designer).
- Vòng 3: test ghim cụm, không ghim cả chuỗi 399 ký tự; chữ không nằm trong cụm nào (ví dụ "gợi ý lên phiếu", "bình luận" của L1) đổi được mà không test nào đỏ. Đây là bộ cụm phán quyết đã chọn, không phải finding.
