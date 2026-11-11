# Review 28 — FEAT-001 T20c (test_policy không commit giao dịch test)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff 3f63ec7..team/FEAT-001-task-20c` (head 6e0ca14); merge e267dab
- Vòng 1 request-changes: major STD-TEST-1 (kiểm rò ở tearDownClass rỗng khi site đã có team, không có đỏ). Vòng 2 (FIX_BASE 6f7a566): ADDRESSED bằng guard `patch.object(frappe.db, "commit", side_effect=AssertionError)` trong setUp (độc lập dữ liệu site)
- Bằng chứng dev: đỏ 21 lỗi khi khôi phục `delete_doc("HD Team")` (hd_team.py:46 commit), xanh Ran 21 OK; `--app erp_ai` Ran 262 OK hai lần; pre-commit pass
- Dọn dữ liệu test rò trên miyano (do dev, theo lệnh tech-lead): phiếu 43063, 43064, HD Team "IT", "Nhân sự & Hành chính"; (dev T25) phiếu 43065, HD Team "T25 Nhóm", user/HD Agent/contact/ticket type T25

## Findings
Không còn blocker/major.

## Deferred
- Mẫu "commit guard trong setUp" là chuẩn cho test có tạo HD Team (ghi trong memory của reviewer); T25 dùng cách khác (rollback + tearDownClass) đang được re-review.
- minor: guard không bắt `frappe.db.sql("commit")` hay commit ngầm do DDL.
