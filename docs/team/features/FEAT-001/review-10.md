# Review 10 — T9 (DocType ERP AI Setting và validate)

- Verdict: approve (vòng 2)
- Số vòng: 2
- Diff: `git diff f455f3b..team/FEAT-001-task-9` (vòng 2: `git diff f32354f..team/FEAT-001-task-9`); merge 68932d9
- Checklist (10): 10/10 sau vòng 2; 19 trường khớp design 2.1, validate (a)-(f) khớp 3.6

## Findings
- Vòng 1: major | STD-TEST-6 | test_erp_ai_setting.py:160-161 | trạng thái rò giữa các test (rollback chỉ cuối lớp) nên ca âm không thể đỏ. Vòng 2: ADDRESSED (setUp đặt nền + addCleanup rollback, assertRaisesRegex theo từng guard; dev chứng minh đỏ khi gỡ từng guard).
- Vòng 1: major | STD-TEST-2 | test_erp_ai_setting.py:67-100 | tiêu chí (a) chỉ kiểm 3/8 trường tự quản. Vòng 2: ADDRESSED (cả 8 trường ở test khôi phục và dòng mới).

## Đã giải quyết "không kiểm được từ diff"
- Red/green: dev dán đỏ (7 test thiếu DocType), migrate exit 0, xanh; sau merge migrate exit 0, `--app erp_ai` Ran 94 tests OK, pre-commit exit 0.
- Khôi phục chạy ở mọi `save()`: các task sau (gateway T16/T17, tasks T33) phải ghi trạng thái khóa bằng `frappe.db.set_value`, không `doc.save()` (ADR-004).

## Deferred
- minor: `assertFalse(row.tokens_remaining)` yếu hơn `assertIsNone`.
- Cho người: Currency hiển thị theo VND (concern của dev); cân nhắc đổi sang Float "(USD)" — thay đổi design.
