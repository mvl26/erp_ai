Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 08 — FEAT-007 T8

- Diff: `git diff b403799457c8780834f44bfa6f45e33cb1018332..3bdb53f` (nhánh `team/FEAT-007-task-8`, 1 commit); lệnh đã chạy: `git log --oneline b403799..3bdb53f`, `git diff --stat b403799..3bdb53f`, `git diff b403799..3bdb53f`, `git show 3bdb53f:<path>` (test_doctype_descriptions.py, test_erp_ai_setting.py, erp_ai_credential.{json,py}, agent/tools/read.py, modules.txt), `git grep "HD Ticket Comment\|reference_ticket" 3bdb53f -- erp_ai/constants.py erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule`, `git log -1 --format='%an%n%B' 3bdb53f`
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `b403799..3bdb53f` (1 commit, 6 file, +225/−1: 114 dòng sản phẩm gồm 29 dòng hằng, JSON 80 dòng, controller 5 dòng; 112 dòng test, 5 test mới trong `TestCatalogRules`, 1 mục `DOCTYPE_CONFIG`), đúng 6 file của touchpoints.
- Bằng chứng của dev: RED `FAIL: test_ticket_content_doctypes_is_adr_034_list ... Tuples differ: ('HD Ticket', 'HD Ticket Comment', ...) != ('HD Ticket', 'Comment', 'Communication', 'File')`, `Ran 41 tests ... FAILED (failures=1)`; trước đó `DocType ERP AI Catalog Rule is missing`, `module 'erp_ai.constants' has no attribute 'CATALOG_ACTIONS'`. GREEN `test_erp_ai_setting` `Ran 41 tests in 6.306s OK`, `test_doctype_descriptions` `Ran 12 tests in 0.578s OK`, `test_architecture` `Ran 112 tests in 5.347s OK`; `grep -cE "^(import|from)" erp_ai/constants.py` → `0`.
- Layer 1 (khớp spec):
  - AC-29 (một nguồn option): option `action`/`mode` của JSON = `"\n".join` của `CATALOG_ACTIONS`/`CATALOG_MODES`, đúng cơ chế `design-w0-fixes.md:64`; test ghim cả hai chiều (JSON = hằng, hằng = giá trị viết tay theo `design.md:214-221`), đổi một bên là đỏ. `mode` mặc định `Cần duyệt` ghim ở JSON và qua `frappe.new_doc`.
  - F-1: 13 tên đúng `plan.md` "Ràng buộc chung" (`ACTION_*` ×6, `CATALOG_ACTIONS`, `MODE_*` ×3, `CATALOG_MODES`, `KPI_IDS`, `TICKET_CONTENT_DOCTYPES`), đúng giá trị và thứ tự, một khối liền ở cuối `erp_ai/constants.py:73-100`.
  - A-D6: `constants.py` vẫn 0 dòng import; test kiểm cả dòng chữ và AST.
  - C-T8-1: `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "Comment", "Communication", "File")` (`constants.py:100`), đúng thứ tự; `git grep` hai chuỗi cấm trên `constants.py` và thư mục `erp_ai_catalog_rule/` → 0 dòng (chuỗi chỉ còn trong dòng RED của dev, không trong file sản phẩm). C-T8-2: diff không chạm `erp_ai/tests/test_architecture.py`.
  - DocType con: 5 trường đúng bảng `design.md:204-210` (kiểu, bắt buộc, `Link` → `DocType`, `Small Text`, `Data`), `istable: 1`, module `ERP AI agent`, `permissions: []` như bảng con có sẵn `ERP AI Credential`; controller là lớp `Document` rỗng (`design-w0-fixes.md:48`). Hai Section Break là bắt buộc của test có sẵn `test_section_breaks_labelled_in_vietnamese` (`assertGreaterEqual(len(breaks), 2)`), không phải thêm ngoài phạm vi.
  - Mô tả `target_doctype` "dữ liệu của app, phân quyền, tài khoản hay chứng từ submit bị chặn khi lưu": khớp AC-29 và T10 (`User` nằm trong `read.DENIED_DOCTYPES`); hành vi chặn do T10/T11 làm, không phải T8.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 2 điểm nhỏ: (a) STD-DOC-2: mô tả `mode` (`erp_ai_catalog_rule.json:60`) nói "Tự làm: chạy không cần duyệt sau khi đủ số đề xuất liên tiếp được duyệt không sửa" — chỉ nêu điều kiện (5) của AC-36 `[changed]`, thiếu L3, đầu mục, ngưỡng tin cậy, và trái với ngoại lệ "Tạo Custom Field luôn Cần duyệt" (AC-30/AC-36 `[changed]`) dù chính bảng này có option `Tạo Custom Field`; thiết kế không cho chữ của trường bảng con, nên sửa thành "khi đủ mọi điều kiện tự làm; Tạo Custom Field luôn cần duyệt" hoặc để task U7b viết lại; (b) STD-TEST-8: `test_constants_stay_leaf_with_block_at_end` (`test_erp_ai_setting.py:875-882`) chỉ lấy các nút `ast.Assign`, nên một `def`/phép gán có chú thích kiểu chen giữa khối FEAT-007 vẫn xanh — "một khối liền" của F-1 chỉ được ghim một phần | tùy dev

## Review checklist (10)
1. đạt (AC-29, F-1, A-D6, C-T8-1, C-T8-2 đủ; không thêm gì ngoài task) 2. đạt (6/6 file trong touchpoints; file mới dưới `erp_ai/erp_ai_agent/doctype/`) 3. đạt (RED trước, có dán; không skip/xfail) 4. đạt (không phép khẳng định cũ nào đổi; test mới không đọc dữ liệu site ngoài meta DocType) 5. đạt (không có mã xử lý lỗi; kiểm lúc lưu là T10/T11) 6. đạt (không bí mật; bảng con không DocPerm riêng, theo quyền của Single cha) 7. đạt (DocType mới, chỉ thêm; chưa gắn vào bảng cha cho tới T10) 8. đạt (tên theo `plan.md`; tên lớp `ERPAICatalogRule` cùng kiểu `ERPAICredential`) 9. đạt (không thêm phụ thuộc) 10. đạt (`feat(setting): … (FEAT-007)`, không trailer; minor a về tài liệu)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.migrate` sau merge tạo DocType `ERP AI Catalog Rule` trên site `miyano` (dev báo một phiên khác migrate từ cây không có T8 đã làm mất DocType một lần); `TestCatalogRules.setUp` và `frappe.new_doc(...).mode` cần meta đã migrate | |
| Test sau merge trên `team/FEAT-007` (`6c231aa` + T8): `test_erp_ai_setting`, `test_doctype_descriptions`, `test_architecture` (có `test_no_legacy_ticket_comment_or_spoofable_author`), đầu ra dán vào journal theo C-T8-2 | |
| `cmd.lint` / `cmd.format` cho 6 file (reviewer không chạy lệnh) | |
| Minor (a): chữ mô tả `mode` so với AC-36 `[changed]` cần có chủ (dev sửa ngay, hoặc ghi cho task U7b / T10 thêm cụm cấm vào `FORBIDDEN_PHRASES`) | |

## deferred

- (minor, tùy dev) 2 điểm nhỏ ở trên.
