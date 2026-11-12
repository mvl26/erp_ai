Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 09 — FEAT-002 T9

- Diff: `git diff 177f013..team/FEAT-002-task-9` (vòng 2: `git diff 218fc88..8a1f3cf`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-8 | erp_ai/install.py:212-216, :57 | hai chốt "thiếu doctype HD Form Script" (bước 7 của `ensure_setup`, `before_uninstall`) không có test | `test_missing_form_script_doctype_is_skipped_with_warning` |
| major (vòng 1, ADDRESSED) | STD-TEST-8 | erp_ai/tests/test_install.py:362 | bản ghi mồi `enabled: 0` khác bản của app nên xóa theo cờ vẫn xanh; không kiểm tổng số | mồi dựng từ `**AGENT_STATUS_SCRIPT_FLAGS` chỉ khác tên; kiểm tổng sau = trước − 1 |

minor (ADDRESSED): kiểm cờ viết cứng 6 giá trị; docstring `ensure_setup` một dòng.

## Review checklist (10)
1–10: đạt. Ràng buộc: chuỗi `HD Form Script` chỉ ở `install.py`; `before_uninstall` là lệnh xóa duy nhất, chỉ xóa `ERP AI Agent Status`; luật mặc định của T2 giữ nguyên.

## Bằng chứng dev
- ĐỎ vòng 1: `Ran 21, FAILED (errors=21)`, `AttributeError: module 'erp_ai.install' has no attribute 'FORM_SCRIPT_DOCTYPE'`.
- Đột biến vòng 2: bỏ chốt ở `ensure` → `0 != 1`; bỏ chốt ở `before_uninstall` → `0 != 1`; xóa theo cờ → đỏ ở `test_uninstall_removes_only_status_script`; đã hoàn lại.
- XANH: `test_install` Ran 22 OK (hai lần), `test_architecture` Ran 44 OK; lint đạt.
- HD Form Script trên `miyano`: 0 trước và 0 sau; không test nào commit; telemetry (posthog/pulse) không cấu hình trên site nên insert trong test không gửi gì ra mạng. Full suite cuối T6 sẽ phủ cây đã merge.
- Một lần `test_setup_never_writes_existing_tickets` lỗi thoáng qua khi chạy đồng thời với dev T5 trên DB chung (deadlock); xanh khi chạy lại, theo dõi ở full suite cuối (nếu tái diễn ghi vào `debt.md`, STD-TEST-7).

## deferred
Hai minor của reviewer: (1) `test_install.py:388` `c.args[1]` có thể IndexError nếu site thiếu doctype Task (chỉ ở site không có ERPNext); (2) comment `:392` đặt sai chỗ. Design D-13 ("cảnh báo cả khi cài và khi gỡ") mâu thuẫn với 3.6 ("gỡ: không làm gì"); code theo 3.6; designer cần chọn một.
