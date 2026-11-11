# Review 46 — FEAT-001 T40 (Test kiến trúc và CI)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff a0039d0..team/FEAT-001-task-40` (head ac31460; vòng 2: `git diff c32cdae..team/FEAT-001-task-40`)

## Vòng 1 (review-raw-T40.md)
- major STD-TEST-2: kiểm import chỉ cấm `workflowcore`, ADR-001 yêu cầu allowlist (stdlib, frappe, helpdesk, erp_ai; `anthropic` chỉ ở gateway/client.py).
- major STD-TEST-2: quy tắc "không traceback có biến cục bộ" bỏ sót `log_error` thiếu message (D-20).
- minor: scanner bị lừa bởi import có bí danh, tên exec/spawn thiếu, `constants.SETTING_DOCTYPE`/`get_doc` dạng khác, `;` trong SELECT; gateway/agent chưa cấm import `erp_ai.erp_ai_agent`.
- Ngoại lệ có tài liệu được chấp nhận: `COMMENT_HIDDEN_FIELDS` ở read.py (design 3.5 amendment 1c), `get_all("DocType")` metadata trong tools, `eval -> agent.runner` (ADR-001). ci.yml thay đổi tối thiểu, không nâng version action.

## Vòng 2
Cả hai major ADDRESSED (allowlist + ca tổng hợp `erpnext`, `telephony`, `hrms`, `requests`, import lười; mọi `log_error` phải có message không rỗng); minor 1 (phần rẻ) và minor 2 ADDRESSED; minor 3-6 hoãn (importlib chuỗi, TestCase, tên `assertCaught`, `prefix`). Cây thật sạch với luật mới, không sửa mã sản phẩm.

## Bằng chứng dev
Vòng 1: RED (ci.yml gốc thiếu 7 mục) -> GREEN 34 OK; 8 mutation thật đều đỏ; CP-5: migrate exit 0, `--app erp_ai` Ran 442 OK x2 (PYTHONPATH worktree), pre-commit exit 0, grep dấu skip rỗng. Vòng 2: RED 21 failure "scanner missed the violation" -> GREEN `Ran 40 tests OK`; mutation `import erpnext` và `log_error` một đối số đều đỏ; pre-commit pass; đếm 4/3/8/0/199/9 trước = sau.

## Deferred
- Quét `importlib` chuỗi (registry.py) chưa có; ADR-004:41,43 (`ignore_permissions`, `db.set_value`/SQL ghi chỉ ở 4 chỗ, ghi trạng thái khóa chỉ ở gateway) chưa được quét: ghi nợ, không thuộc T40.
- ADR-003:37 ("DocType controller không import gateway") lệch với `erp_ai_setting.py` import gateway cho `check_keys` (design 3.6 cho phép): architect/designer thống nhất lời văn.
- CI chưa được chứng minh bằng một lần chạy workflow thật (telephony chỉ có nhánh `develop`, helpdesk tag v15.1.0, `bench build` lâu hơn).
- Minor: ca `import subprocess as sp` đã bị luật import bắt trước nên không kiểm bí danh; `from frappe import log_error as le; le(T)` lọt luật log_error.
