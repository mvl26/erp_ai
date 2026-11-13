# Review 18 — FEAT-001 T13 (quyền Task cho role agent)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 8a5be57..team/FEAT-001-task-13` (head 7330919); merge de5062b
- Bằng chứng dev: RED 3 test "0 != 1"; GREEN test_install Ran 13 OK; kiểm đột biến (if_owner=0, bỏ bước, bỏ guard trùng) đều đỏ; migrate x2 exit 0
- Sau merge (qua dev): migrate x2 exit 0; cmd.test `Ran 122 tests OK`; pre-commit exit 0; Custom DocPerm Task trên miyano: ERP AI Agent (pl0, r/w/c, if_owner=1), Projects User, Employee Self Service (hai dòng sau không đổi)

## Findings
Không có blocker/major.

## Deferred
- minor STD-TEST-8: snapshot quyền role khác nên chụp trong setUp trước `ensure_setup()`; test copy-path chỉ đếm dòng, chưa so role/cờ.
- minor STD-DESIGN-5: guard "có dòng agent ở bất kỳ permlevel" coi như đã có.
- Ghi vào As-Built/ops: khi có Custom DocPerm trên Task, Frappe bỏ qua thay đổi DocPerm chuẩn sau này của ERPNext; thu quyền agent phải hạ cấp/vô hiệu agent chứ không chỉ xóa dòng (migrate sẽ tạo lại).
