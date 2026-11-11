# Review 13 — T11 (cài đặt: role, tài khoản agent, cấu hình mặc định, hook)

- Verdict: approve (vòng 2)
- Số vòng: 2
- Diff: `git diff bc0411c..team/FEAT-001-task-11` (vòng 2: `git diff 260f6c3..team/FEAT-001-task-11`, head 828e102); merge f398df8
- Checklist (10): 10/10 sau vòng 2

## Findings
- Vòng 1: major | STD-TEST-6 | test_install.py:33-36 | setUp chạy ensure_setup trên site đã có role/user/default nên nhánh "tạo nếu thiếu" không bao giờ chạy. Vòng 2: ADDRESSED (setUp xóa Singles, Has Role, User, 2 Role trong giao dịch rollback; thêm test user thiếu Agent; dev chứng minh đỏ khi gỡ từng nhánh).
- Vòng 1: major | STD-TEST-2 | test_install.py:68-71 | test phiếu so hai danh sách rỗng. Vòng 2: ADDRESSED (tạo 1 phiếu + 1 comment, assert không rỗng; đỏ khi ensure_setup sửa phiếu).
- Phát hiện thật khi sửa: DocType sync có thể để hàng NULL trong tabSingles nên default bị bỏ qua; install.py nay điền khi giá trị thiếu hoặc None (test_cleared_default_is_refilled).

## Đã giải quyết "không kiểm được từ diff"
- Red/green: dev dán đỏ (ImportError install), xanh; sau merge migrate hai lần exit 0, `--app erp_ai` Ran 109 tests OK, pre-commit exit 0 (qua dev, D3).
- `make_ticket` trong test phụ thuộc cài đặt helpdesk trên site; chạy xanh trong `cmd.test` trên miyano. Trên site CI mới cần xem ở T40.

## Deferred
- minor STD-TEST-2 test_install.py:73: `int(... or 0) == 0` vẫn xanh nếu `enabled` không được điền; nên assert hàng Singles tồn tại giá trị "0".
- minor STD-TEST-8 test_install.py:61: chưa có ca thiếu role `Agent` của helpdesk.
- Cho người: design mục 6 bước 5 ghi "value is None"; code coi hàng NULL/thiếu là chưa đặt (khớp).
