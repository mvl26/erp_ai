Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 26 — FEAT-007 T26

- Diff: `git diff 631fa36d153066788a2025b7612f98a7a21fc9fe..49862ef017c59721dd836780bbfad7764d433610` (đầu nhánh task khi merge)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `631fa36..49862ef` (1 commit, 2 file, +113/−0), đúng 2 file của touchpoints; chỉ thêm dòng, không test hay hàm phụ sẵn có nào bị sửa.
- Bằng chứng của dev: RED (hàm giả trả `False` / `resolution_by`) `FAIL: test_over_exact_answered (...TestResponseOverdue.test_over_exact_answered) (case='B over the mark by 1 s')`, `AssertionError: False is not True`; `FAIL: test_processing_deadline_d_with_and_without_due (...) (case='D with a date')`, `AssertionError: datetime.datetime(2026, 11, 14, 17, 0) != datetime.datetime(2026, 11, 20, 23, 59, 59)`; `Ran 70 tests in 1.316s`, `FAILED (failures=6)`. GREEN `test_routing` `Ran 70 tests in 2.638s OK`; `test_architecture` `Ran 112 tests in 5.338s OK`.
- Kết luận của reviewer: `response_overdue` theo `design.md:390`; `processing_deadline` theo `design-w0-fixes-2.md` 5c(i) (thắng `design.md:391`): D hoặc E có `due_at` → `as_deadline(due_at)`, ngược lại `resolution_by`; `design-w0-fixes-3.md` không đụng hai hàm này.
- Vế → ca đỏ khi đột biến: `>` thành `>=` → "B exactly at the mark"; `>` thành `<` → "B over the mark by 1 s", "B before the mark"; bỏ kiểm đã trả lời → hai ca "answered"; bỏ chắn `response_min is None` → "response_min null" (`TypeError`); bỏ `(config or {})` → "config None"; mọi đầu mục dùng mốc của B → hai ca của C; bỏ "E" hoặc "D" khỏi kiểm D/E → các ca E, D; bỏ kiểm đầu mục → "A/B/C/F due_at ignored", "None category"; trả `due_at` thô → hai ca `date` (giá trị và `assertIs(type(...))`). Cấu hình test đặt `response_min` của B là 30 (khác mặc định 15), nên test chỉ xanh khi mã đọc cấu hình.

### Bốn điều tech-lead hỏi

| Hành vi | Thiết kế | Loại |
|---|---|---|
| Đã trả lời (trước hay sau mốc) → `False` | khớp `design.md:390` ("`first_responded_on` rỗng ∧ …") và AC-26 ("chưa có phản hồi nào ra ngoài") | không phải finding; câu hỏi cho designer, không chặn: phiếu trả lời muộn không bao giờ được đếm "quá mốc phản hồi" ở báo cáo 08:00 (T51) |
| `response_min` null → `False` | khớp (thiết kế đòi có `response_min`; bộ kiểm lúc lưu cho phép null) | — |
| thiếu `expected_sla` hoặc cả cấu hình → `False` | im lặng; nhất quán với "không biết đầu mục → `False`" | chỗ hở của thiết kế, không phải finding |
| `processing_deadline` trả `resolution_by` ở mọi ca khác | khớp D-18 và 5c(i) | — |

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 1 điểm nhỏ: `routing.py:219-220` gọi `as_deadline(due_at)` hai lần; gán một lần (như `_priority` ở `:186`) thì rõ hơn | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trên cả hai test được nêu; 26 ca con; không skip) 4. đạt (chỉ thêm; hàm thuần, `now` truyền vào; `keep_agent_settings`) 5. đạt (`None` và cấu hình thiếu được xử lý) 6. đạt 7. đạt (chỉ thêm hàm; chữ ký khớp `tasks.md`) 8. đạt 9. đạt (không thêm) 10. đạt (`feat(agent): … (FEAT-007)`, một commit, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `design-addendum-2-U5b.md:45` còn tả luật cũ của `design.md:391` (`due_at` trả nguyên) | Không ảnh hưởng mã đợt 0 (`ticket_deadline` ở `:113` của addendum đã đổi date thành 23:59:59 trước khi gọi). Ghi cho designer / `/team:plan` đợt 2; không chặn tick. |
| Test sau merge | Xem dòng progress của T26 trong `tasks.md` (tech-lead chạy từ worktree `feat-007` sau merge). |

## deferred

- (minor, tùy dev) 1 điểm nhỏ ở trên.
- (designer, không chặn) phiếu trả lời muộn không được đếm "quá mốc phản hồi"; hành vi khi thiếu `expected_sla`; chữ `design-addendum-2-U5b.md:45`.
