# Review 26 — FEAT-001 T24 (tool đọc: phiếu, comment, phiếu tương tự, bản ghi)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff 0c5e216..team/FEAT-001-task-24 -- erp_ai` (head f4e21a9); merge 6440e10
- Vòng 1 request-changes: major STD-TEST-8 (`apply_fieldlevel_read_permissions` chỉ test bằng Administrator); major STD-DESIGN-2 (get_ticket không cắt mô tả 6000 ký tự). Vòng 2 (FIX_BASE a19f376): cả hai ADDRESSED; 6 minor cũng đã sửa
- Bằng chứng dev (trên cây trước T16/T17): module test_read Ran 27 OK; `--app erp_ai` Ran 213 OK; pre-commit pass; 17+ đột biến đỏ
- cmd.test trên cây sau merge (gồm T16, T17, T24): xem dòng tiến độ tasks.md (chờ chạy qua dev; tick sau khi xanh)
- Lưu ý: commit f4e21a9 do tech-lead thực hiện từ thay đổi chưa commit trong worktree của dev (dev được dặn không commit ở vòng này)

## Findings
Không còn blocker/major.

## Deferred
- `frappe.get_list` nhân đôi dấu `\` (db_query.py:1286): `%`, `_`, `\` trong truy vấn tìm phiếu không khớp ký tự thật; an toàn (không injection). Cần thay đổi design nếu muốn tìm theo ký tự đó.
- minor: `read.py` import `prompts._clean` (private); cắt ở read.py:155/164 chưa test; thuộc tính `name` của schema `get_record` chưa có `maxLength`; mô tả password chỉ cắt ở cấp trên (child table chưa).
- T27/T28: `TOOL_RESULT_MAX_CHARS` chỉ khai báo, runner/registry phải áp; datetime trong kết quả tool phải serialize được.
- Quyền thật của AGENT_USER (Comment read, permlevel 7/8, team) chưa được test bằng tài khoản thật; kiểm ở T28/T40.
