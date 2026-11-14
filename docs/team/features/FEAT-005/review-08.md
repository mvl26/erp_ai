Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 08 — FEAT-005 T8

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 5223674..941d81c` (nhánh `team/FEAT-005-task-8`, 2 commit; vòng 1 `5223674..1753c56`, vòng 2 `1753c56..941d81c` 4 file +88/−22); merge `cc8f00d`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 design-defect, gỡ bằng design-amd2 "Sửa vòng 2"

## Vòng 2 — approve (`1753c56..941d81c`, chấm lại có phạm vi + phạm vi mới của design-amd2 vòng 2)

- (1) blocker STD-DESIGN-1: ADDRESSED. `erp_ai/agent/test_runner_routing.py:1482-1502` ghim mốc và trả lại; `:1564` gọi `_privilege_changes_by_agent(self.since, now)`; `:1566-1570` đọc thẳng `permission_rows_by_agent`; `:1581-1583` khẳng định `privilege_changes == []` và trước == sau; khớp "Luật cho test FEAT-006" của §8. `git grep _permission_records_by_agent` tại `941d81c`: không còn.
- (2) major STD-TEST-8: ADDRESSED. `erp_ai/tests/test_tasks.py:558-575`: dòng Note chỉ đổi `description` (`permissions` giống) và dòng ToDo vắng `permissions` cả hai phía, kỳ vọng 0 mục; so cả ảnh chụp thì test đỏ.
- Phạm vi mới: `read_privilege_watermark()` ở `erp_ai_setting.py:62-69` (`cache=False`, năm 1 → `None`), `restore_self_managed_fields` dùng nó (`:106`); `tasks.py` không còn `EMPTY_DATETIME` và tên trường mốc, đọc `lower` qua hàm đó (`:177`); `test_empty_watermark_reads_from_the_start` 3 dạng thô; không ghi mốc (T11), không mục User (T9), không fail-closed (T12); không vòng import; rà nơi gọi §7 khớp.
- Phát hiện mới: không có blocker/major.
- minor | — | — | 4 điểm nhỏ: (a) commit `1753c56` đứng riêng vẫn để `test_runner_routing` đỏ (STD-GIT-2; §7 muốn "cùng commit", nhánh gộp `--no-ff` nên trên `team/FEAT-005` hai commit vào cùng một merge); (b) `if lower is not None` so với `if lower` không khác hành vi; (c) cleanup trả mốc trong `TestRoutingPermissions` thừa; (d) hai minor vòng 1 còn mở (chú thích `_neutralize_agent_rows`, `upper` tính ngoài `try`) | tùy dev
- Checklist 1–10: đạt cả 10.
- Bằng chứng của dev vòng 2: RED `--case TestRoutingPermissions` → `AttributeError: module 'erp_ai.tasks' has no attribute '_permission_records_by_agent'`, `Ran 2 tests` / `FAILED (errors=1)`; GREEN `Ran 2 tests in 8.716s` / `OK`; test_tasks `Ran 42 tests in 10.626s` / `OK`; test_erp_ai_setting `Ran 28 tests in 3.191s` / `OK`; cả module test_runner_routing hai lượt `Ran 62 tests` / `FAILED (errors=2)`, `QueryDeadlockError` ở các test khác nhau mỗi lượt.
- Không kiểm được từ diff (vòng 2): cả module `test_runner_routing` sạch deadlock; `cmd.lint`; kết quả sau merge → tech-lead chạy sau merge (dòng round 11 của `tasks.md`).
- deferred: minor (a)–(d) ở trên; phán của tech-lead cho (a): không squash (lệnh "không amend/reset"), merge `--no-ff` `cc8f00d` đưa cả hai commit vào nhánh cùng lúc.

## Vòng 1 — design-defect (`5223674..1753c56`)

Lớp 1 (khớp spec): mọi ý của Returns T8 có trong mã (tham số `now`, `PRIVILEGE_ALERT_SETTLE_S`, cận trên, đọc mốc `cache=False`, `datetime(1, 1, 1)` coi là rỗng, lọc `reason` + cửa sổ `(lower, upper]` + `like "%api_%"` + sắp `creation` tăng, lọc `ok` và `GENERIC_WRITE_TOOLS`, loại `Has Role`, so `permissions` trước/sau của DocType `DocType`, bảng động từ dựng từ tập tool dùng chung, `không rõ`, định dạng thời điểm). Không có phần ngoài phạm vi (không ghi mốc, không mục User/`[QUẢN TRỊ]`/fail-closed). Năm test viết lại so nguyên chữ mục.

- blocker | STD-DESIGN-1 | erp_ai/agent/test_runner_routing.py:1544 | `_findings()` còn gọi `tasks._permission_records_by_agent()` mà T8 xóa đúng theo chữ task; `test_privilege_findings_unchanged` (FEAT-006) sẽ lỗi `AttributeError` khi chạy cả app. File này không có trong design-amd2 §7 và không thuộc `files:` của T8; dev chỉ chạy test_tasks.py | Sửa plan: thêm `erp_ai/agent/test_runner_routing.py` vào touchpoint của T8 (hoặc chèn một task nhỏ); thay khóa `permission_records` bằng `tasks._privilege_changes_by_agent(None, now_datetime())` hoặc bỏ khóa đó và giữ phép so `alarms`; designer thêm dòng vào §7 | confirmed
- major | STD-TEST-8 | erp_ai/tests/test_tasks.py:552-570 (và :464-474) | Ảnh chụp DocType dựng tay chỉ khác nhau ở `permissions`: nếu mã so cả ảnh chụp thì mọi test vẫn xanh, báo nhầm (vd. bot sửa `description` của DocType) quay lại | Thêm một dòng DocType có ảnh chụp đổi trường khác (vd. `{"description": ...}`) trong khi `permissions` giống hoặc vắng ở cả hai phía, kỳ vọng 0 mục | confirmed
- minor | — | — | 3 điểm nhỏ: chú thích `_neutralize_agent_rows` còn nói tới điều kiện bản ghi phân quyền dù `modified_by` không còn được đọc (vòng lặp `PERMISSION_DOCTYPES` và `_add_perm(AGENT_USER)` trong `test_setup_neutralizes_live_rows_attributed_to_agent` hết tác dụng cho điều kiện này); `test_email_failure_keeps_alarm_logs_failure_and_continues` bị đổi phần gieo (bắt buộc vì `_add_perm` cũ không còn gây cảnh báo; số kỳ vọng 3 giữ nguyên, đạt STD-TEST-5); `upper` tính ngoài `try` nên `now=` sai sẽ ném thay vì được ghi log (D-20; scheduler không truyền đối số) | tùy dev

Bằng chứng của dev: nền chưa sửa `Ran 35 tests` / `OK`; RED `FAILED (failures=4, errors=6)`, vd. `'…phân quyền: Has Role mknaln34i5, User Permission …' != '…: tạo Role Profile ERPAI-TEST hồ sơ 1 (người ra lệnh …'`; GREEN `Ran 41 tests` / `OK`.

## Tech-lead đã kiểm

- `git grep -n "_permission_records_by_agent" team/FEAT-005-task-8 -- erp_ai`: kết quả ghi ở dòng progress của T8 trong `tasks.md` (xác nhận nơi gọi ngoài touchpoint).
- Theo skill build bước 9: `design-defect` → dừng T8, báo team-leader; tech-lead không tự thêm touchpoint và không thiết kế lại. Hai phát hiện gửi nguyên văn cho dev ở vòng 2 sau khi design-amd2 §7 và `files:` của T8 được sửa.

## Không kiểm được từ diff

- `test_runner_routing.py` và các module khác có xanh với thay đổi này không: cần lượt cả app.
- `cmd.lint` sạch.
- Bỏ dòng `EMPTY_DATETIME` có làm `test_empty_watermark_reads_from_the_start` đỏ trên site này không (theo nguồn Frappe thì có).

## deferred

Chưa có.
