# Review 40 — FEAT-001 T36 (Nút "Kiểm tra khóa" `check_keys`)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff 920be6c..team/FEAT-001-task-36` (head c8d7660; vòng 2: `git diff 72b026a..team/FEAT-001-task-36`)

## Vòng 1 (review-raw-T36.md)
- major STD-SEC-4: `@frappe.whitelist()` mặc định cho GET, không CSRF; endpoint đổi trạng thái khóa và gọi API trả phí.
- minor: `label` thô vào `frappe.throw` (STD-SEC-3); tên `one`/`r` (STD-NAME-6); `PROBE_RESULT_FIELDS` giữa module (STD-STYLE-4).

## Vòng 2
Tất cả ADDRESSED: `methods=["POST"]` (test khẳng định `allowed_http_methods_for_whitelisted_func == ["POST"]`, RED `['GET','POST','PUT','DELETE'] != ['POST']`); `escape_html(label)` (test `<img` đỏ trước khi sửa); đổi tên, chuyển hằng. Không finding mới.

## Bằng chứng dev
Vòng 1: RED 5 test (thiếu `check_keys`) -> GREEN 15 OK; mutation từng guard (only_for, chiếu 4 trường, `.save()`, label lạ) đều đỏ. Vòng 2: Ran 16 tests OK; pre-commit pass; đếm Error Log 196 trước = sau (ERP AI Log trước chưa in riêng, test khẳng định không đổi).

## Deferred
Không. Kiểm tay sau G4: nhấn nút trên `/app/erp-ai-setting` (design test plan).
