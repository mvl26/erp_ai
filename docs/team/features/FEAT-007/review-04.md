Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 04 — FEAT-007 T4

- Diff: `git diff 02139151e528b0bb0fbd52f43ea2967ffa87ffb6..f1cea06` (đầu nhánh task khi merge; merge `aff309d` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `0213915..f1cea06` (1 commit, 2 file, +47/−1), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `FAILED (failures=2, errors=1)`: `pymysql.err.DataError: (1406, "Data too long for column 'actions' at row 1")`, `AssertionError: 'text' != 'longtext'`, `AssertionError: 'Small Text' != 'Long Text'`; GREEN sau migrate `test_erp_ai_log` `Ran 10 tests in 1.320s OK`, `test_doctype_descriptions` 12 OK, `test_feat007_unknown_confidence_pct` 5 OK, `test_architecture` 112 OK.
- Kết luận của reviewer: `erp_ai_log.json:233` chỉ đổi `"fieldtype": "Small Text"` → `"Long Text"`; tên, vị trí, nhãn, mô tả, `read_only: 1` giữ nguyên từng byte. `TestActionsLongText` có đủ ba test của F-6. Test khứ hồi dùng payload đúng 65 536 byte UTF-8 và khẳng định cả số byte lẫn số ký tự (dưới 65 535), nên thử đúng giới hạn theo byte; giá trị mong đợi là `json.dumps(..., ensure_ascii=False)`, khớp `run_log.py:51`. Test meta và test cột kiểm riêng JSON và DDL đã migrate. `write_entry` không commit khi `frappe.flags.in_test`; `addCleanup(frappe.db.rollback)` gỡ dòng 64 KB.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 2 điểm nhỏ: (1) `test_erp_ai_log.py:148` tên `_actions_just_over_small_text(byte_size)` tả nơi gọi duy nhất chứ không tả tham số (STD-NAME-6); (2) `test_erp_ai_log.py:163` `keep_agent_settings` không bảo vệ gì ở đây (`write_entry` không đọc ERP AI Setting), nhưng quy ước của task đòi | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (RED trước, 3 lỗi khác nhau; biên byte so với ký tự; meta so với DDL; không skip) 4. đạt 5. không áp dụng 6. đạt (truy vấn `information_schema` có tham số) 7. đạt (cột chỉ rộng ra; Frappe v15 nhập lại JSON theo `migration_hash`, không cần đổi `modified`; chiều xuống thuộc kế hoạch rollback của As-Built theo F-6) 8. đạt 9. không áp dụng 10. đạt (`feat(log): … (FEAT-007)`, một commit, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Đưa sớm commit `f1cea06` vào `develop` (F-6, Returns của T4) không đứng một mình được: test import `keep_agent_settings`, hàm này chưa có trên `develop` (đến từ `5e5bde3` của T1, commit đó còn thêm trường `site_environment`) | Trong `team/FEAT-007` commit đứng riêng được, nên không chặn tick. Mâu thuẫn nằm giữa quy ước "mọi lớp test mới gọi `keep_agent_settings`" và chữ "commit độc lập" của F-6. Báo team-leader: nếu muốn đưa sớm thì phải lấy cả T1 (và T61), hoặc chờ cả nhánh. Tech-lead không cherry-pick. |
| Test, migrate, lint sau merge | Tech-lead chạy từ worktree `feat-007` sau merge `aff309d`: `cmd.migrate` exit 0; `test_erp_ai_log` `Ran 10 tests in 1.442s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.341s OK`; `test_feat007_unknown_confidence_pct` `Ran 5 tests in 0.097s OK`; `test_architecture` `Ran 112 tests in 3.141s OK`; `information_schema.columns.DATA_TYPE` của `actions` → `longtext`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền). |

## deferred

- (minor, tùy dev) 2 điểm nhỏ ở trên.
