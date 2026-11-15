Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 03 — FEAT-007 T3

- Diff: `git diff 80469e76ffd8008fd2d74bf72b625692b157e7c9..54de02d` (đầu nhánh task khi merge; merge `5e26556` trên `team/FEAT-007`)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 2); vòng 1 là design-defect, đã có phán quyết (1) của `design-w0-fixes-2.md`

## Vòng 1 — design-defect

- Range: `80469e7..d66389a` (1 commit, 2 file, +74/−1), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.tests.test_doctype_descriptions` `AssertionError: 38 != 43` ở `test_every_visible_field_has_description` (doctype='ERP AI Log'), `Ran 12 tests in 0.383s FAILED (failures=4)`; GREEN sau `migrate`: `test_doctype_descriptions` `Ran 12 tests in 0.354s OK`; `test_architecture` `Ran 112 tests in 3.278s OK`; `test_erp_ai_log` `Ran 7 tests in 4.649s OK`.

### Phát hiện

design-defect | STD-DESIGN-3 | erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:280-286 (và `design.md:234`, `design-w0-fixes.md` F-5) | Frappe lưu Int là NOT NULL DEFAULT 0 (`frappe/database/schema.py:197-199`), nên sau migrate mọi dòng ERP AI Log sẵn có đọc ra `predicted_confidence_pct` = 0. `design-addendum-1-U1.md:130, 339, 459` (A-U1-1) nói dòng `classify` cũ cho pct None, đọc là "không biết = dưới ngưỡng, fail-closed". Nếu `confidence_threshold` = 0 (khoảng cho phép 0..100) thì 0 < 0 sai, tức độ tin cậy không biết được tính là đủ ngưỡng (fail-open, trái NFR-4). Báo cáo cũng sẽ hiện dòng cũ là "0%". Mô tả ở `:284` nói dòng cũ "chỉ có nhãn" trong khi cột sẽ hiện 0. | Designer chọn một: (a) giữ Int và sửa U1 dòng 130/339/459 để không còn chờ None (quyết cách hiểu số 0, ví dụ "0 hoặc dòng tạo trước khi có cột pct = không biết"), T3 thêm một câu vào mô tả rằng dòng cũ hiện 0, không phải 0%; hoặc (b) đổi sang kiểu có thể rỗng (Data/Small Text chứa số), T3 làm lại.

Mã của dev theo đúng thiết kế, nên không có finding request-changes nào cho dev.

minor | — | — | 1 điểm nhỏ: cụm bắt buộc `"test"` của `site_environment` là phép kiểm yếu (trùng cả chữ tiếng Anh), ba cụm còn lại mới mang phép kiểm | tùy dev

### Ghi nhận của reviewer

- 5 cột đúng kiểu: `created_labels` Small Text, `predicted_confidence_pct` Int, `split_requested` Check, `split_requests` Small Text, `site_environment` Data; `field_count` 38 → 43; mỗi trường có cụm bắt buộc; không đụng option `entry_type`/`trigger`, không đổi DocPerm, không đổi `actions`.
- Bỏ một cột bất kỳ làm đỏ 4 test; đổi kiểu một cột chỉ `test_feat007_log_columns_have_design_types` bắt được (kiểu mong đợi viết thẳng).

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED `38 != 43`; không skip) 4. đạt (`field_count` đổi theo F-5) 5. không áp dụng 6. đạt 7. chỉ thêm cột; lỗi thiết kế ở trên là hợp đồng dữ liệu với U1 8. đạt 9. đạt 10. đạt (`feat(log): … (FEAT-007)`)

## Vòng 2 — approve (chấm lại cả range sau phán quyết)

- Range: `80469e7..54de02d` (2 commit, 5 file, +181/−2), đúng 5 file của touchpoints sau chèn 2; commit thứ hai `d66389a..54de02d` mang cả việc đổi `default` và patch.
- Bằng chứng của dev: RED `erp_ai.patches.test_feat007_unknown_confidence_pct` `AssertionError: None != '-1'`, `Lists differ: [0, 55, -1] != [-1, 55, -1]`, `Ran 4 tests in 0.114s FAILED (failures=4)`; `test_doctype_descriptions` `AssertionError: {'predicted_confidence_pct': ['-1', 'không biết']} != {}`; GREEN patch test `Ran 5 tests in 0.227s OK`, `test_doctype_descriptions` `Ran 12 tests in 0.365s OK`, `test_erp_ai_log` `Ran 7 tests in 28.749s OK`, `test_architecture` `Ran 112 tests in 3.163s OK`.
- Kết luận của reviewer: design-defect vòng 1 đã được phán quyết (1) giải quyết và nhánh làm đủ phán quyết đó: Int `default "-1"`; mô tả giữ nguyên chữ của phán quyết; cụm `"-1"`, `"không biết"`; patch đổi 0 → -1 theo lô 10 000, lặp tới khi `rowcount` = 0; đúng một dòng ở `[post_model_sync]`; cùng commit với `default`; `field_count` 43; option `entry_type`, `trigger` không đổi.
- Hai lo ngại của dev, reviewer chấm không phải finding: câu "Hệ thống tự ghi khi agent chạy, không sửa được." thêm sau chữ của phán quyết là do `test_read_only_fields_say_system_writes` đòi cho mọi trường read-only; `frappe.db._cursor.rowcount` là cách chính Frappe v15 dùng (`frappe/tests/utils.py:179`), test vòng lặp sẽ đỏ nếu đọc sai số dòng.

### Phát hiện

Không có blocker/major.

minor | — | — | 3 điểm nhỏ: (1) RED ghi "Ran 4 tests" còn file có 5 test, một test (nhiều khả năng `test_patch_loops_until_no_row_changes`) không có dòng đỏ được dán (dev báo đã thử đột biến: `[-1, 0, 0] != [-1, -1, -1]`); (2) `test_feat007_unknown_confidence_pct.py:79` chỉ đếm dòng patch trong mục `[post_model_sync]`, bản chép thứ hai ở `[pre_model_sync]` không bị bắt; (3) patch chạy mọi lô trong một giao dịch nên chia lô không nhả khóa, vô hại ở số dòng hiện nay | tùy dev

### Review checklist (10)
1. đạt 2. đạt (5/5 file là touchpoint; file mới dưới `erp_ai/patches/`) 3. đạt (RED cho các test của phán quyết; không skip; có ca vòng lặp và ca chạy lần hai) 4. đạt 5. đạt 6. đạt (SQL có tham số) 7. đạt (chỉ thêm cột; đổi `default` đi cùng patch dữ liệu; chiều xuống mô tả trong phán quyết) 8. đạt 9. không áp dụng 10. đạt (`feat(log): … (FEAT-007)`, không trailer)

## Phần kiểm của tech-lead

- Đã đối chiếu ba chỗ reviewer dẫn: `design.md:234` ghi `predicted_confidence_pct` là Int; `design-addendum-1-U1.md:130` ("không có → `(None, None)`"), `:339` ("Dòng `classify` cũ không có `predicted_confidence_pct` → `latest_classification` trả pct None") và `:459` (A-U1-1, fail-closed). Hai tài liệu thiết kế nói khác nhau; tech-lead không tự chọn (a) hay (b).
- `team/FEAT-007-task-3` @ `d66389a` và worktree của dev được giữ nguyên, chưa merge. Site `miyano` đã có 5 cột (dev đã `migrate` từ worktree của task): nếu designer chọn (b), cột Int còn lại trên site phải được xét ở bước làm lại.
- Task bị chặn theo: T4, T5, T7 (tức cả phần còn lại của chuỗi U0), T28.

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| 5 cột có trong DB sau migrate | Chờ phán quyết; kiểm sau merge. |
| `cmd.test` cả bộ | Mốc M1. |
| (vòng 2) `COLUMN_DEFAULT` và số dòng = 0 sau `cmd.migrate` trên `miyano` | Tech-lead chạy sau merge `5e26556`, từ worktree `feat-007`: `cmd.migrate` exit 0; `select count(*) … where predicted_confidence_pct = 0` → `0`; `information_schema.columns.COLUMN_DEFAULT` → `-1`. Qa dán lại vào `acceptance.md` ở verify. |
| (vòng 2) test sau merge | `test_feat007_unknown_confidence_pct` `Ran 5 tests in 0.083s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.390s OK`; `test_erp_ai_log` `Ran 7 tests in 1.352s OK`; `test_architecture` `Ran 112 tests in 3.147s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền, đã trả file về nguyên trạng trong worktree). |
| (vòng 2) chiều xuống STD-OPS-2 (revert rồi migrate đặt lại mặc định 0) | Kiểm ở `/team:verify` (mốc M6); không chặn tick. |
| (vòng 2) chữ và 2 test của U1 mà phán quyết (1) nêu (`design-addendum-1-U1.md:61, 130, 262, 339, 459, 423`) | Thuộc đợt 1; báo team-leader để đưa vào `/team:plan` đợt 1. |

## deferred

- (minor, tùy dev) cụm `"test"` của `site_environment`.
- (minor, tùy dev) 3 điểm nhỏ của vòng 2.
- (thiết kế, đã chuyển designer U4b theo phán quyết (1)) HD Ticket `ai_confidence_pct` (T22) cũng `NOT NULL DEFAULT 0`, phiếu chưa định tuyến sẽ hiện 0.
- `erp_ai/patches.txt` không có dòng trống cuối file (có từ nền).
