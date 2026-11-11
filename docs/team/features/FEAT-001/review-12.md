# Review 12 — T10 (DocType ERP AI Log)

- Verdict: approve (vòng 1)
- Số vòng: 1
- Diff: `git diff 8aaf703..team/FEAT-001-task-10` (head 9512a0c); merge 842a5dd
- Checklist (10): 10/10; 30 trường khớp design 2.3, quyền khớp 5.1, cost_usd Float/6/"(USD)" theo D6

## Findings
- Không có blocker/major.
- minor | test_erp_ai_log.py:69-78 | test trường chỉ kiểm tồn tại, không kiểm fieldtype/options Select (trừ cost_usd, ticket).

## Đã giải quyết "không kiểm được từ diff"
- Red/green: dev dán đỏ (6 test "DocType ERP AI Log is missing"), migrate, xanh; sau merge migrate exit 0, `--app erp_ai` Ran 102 tests OK, pre-commit exit 0 (qua dev, D3).
- Role "ERP AI Agent" chưa có đến T11: migrate exit 0 nên DocPerm không làm hỏng; test tự tạo role.

## Deferred
- minor: bảng (fieldname → fieldtype, options) trong test trường.
- Cho T22/T39: tên trường `trigger` là từ khóa MariaDB, mọi SQL thô phải quote; `entry_type`/`trigger` là Select không có dòng trống, `write_entry` phải đặt giá trị rõ ràng.
- Cho người: `ticket` là Link HD Ticket và log không xóa được, nên phiếu đã có log không xóa được (A-10).
