## Feature
- ID: FEAT-002
- Design: `docs/team/features/FEAT-002/design.md`
- As-Built: `docs/team/features/FEAT-002/asbuilt.md`
- Acceptance: `docs/team/features/FEAT-002/acceptance.md` — Verdict: accepted (AC-10 và AC-11 là bước tay của người, chưa làm; `cmd.test` đỏ do BUG-002 có sẵn từ FEAT-001)

## Why
Bot trả lời `@ai` tức thì, người dùng không biết agent đang làm gì (`docs/team/features/FEAT-002/spec.md`, intake). Người quyết định: bỏ comment tạm, dùng chỉ báo trạng thái trực tiếp "Đang suy nghĩ…/Đang làm: <việc>…" và giữ độ trễ 3–5 giây chỉnh được trong cấu hình (ADR-004 giữ nguyên; thêm ADR-007, ADR-008).

## What changed
- Trang phiếu HD Agent hiện chỉ báo nổi (tên agent + "Đang suy nghĩ…" / "Đang làm: <nhãn>…"), tự mất khi lần chạy kết thúc kể cả lỗi. Không tạo comment, task hay bản ghi nào; không hiện trên cổng khách (AC-2, AC-4, AC-9, NFR-6).
- 3 trường mới trên `ERP AI Setting`: `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s`, có kiểm khi lưu (AC-1). Câu trả lời `@ai` đầu tiên trễ d ∈ [min, max], trần là hạn chót lần chạy; phiếu mới không trễ (AC-3, AC-5).
- Hợp đồng realtime (ADR-008): `erp_ai:agent_status`, payload 7 khóa, `done` luôn là tín hiệu cuối; lỗi phát không chặn lần chạy (AC-7, NFR-4').
- Bản ghi HD Form Script `ERP AI Agent Status` do app sở hữu: tạo hoặc đặt lại từ `erp_ai/public/js/agent_status_indicator.js` mỗi lần cài/`migrate` (sửa tay trên site bị ghi đè, theo thiết kế); xóa ở `before_uninstall` (AC-12, ADR-007).
- Main files: `erp_ai/agent/run_status.py`, `erp_ai/agent/answer_delay.py`, `erp_ai/agent/runner.py`, `erp_ai/install.py`, `erp_ai/hooks.py`, `erp_ai/public/js/agent_status_indicator.js`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/`, `erp_ai/tests/test_architecture.py`.
- Khác design: 2 điểm, code theo ADR-008 và mục 3.6; xem `asbuilt.md` mục 2 và "Differences from design". Cần `bench --site <site> migrate` sau khi cập nhật mã (restart không đủ). README và CHANGELOG đã cập nhật.

## How verified
Từ `acceptance.md` (commit kiểm `7ea066a`; mọi lệnh là `cmd.*` của profile):
- 8 module của FEAT-002 chạy bằng `cmd.test_one`, đều `OK`, cộng 242 test: `test_agent_runner` 56, `test_answer_delay` 8, `test_runner_status` 39, `test_run_status` 9, `test_erp_ai_setting` 19, `test_architecture` 58, `test_handlers` 31, `test_install` 22.
- `cmd.lint` (`pre-commit run --all-files`): 12 dòng `Passed`, 0 `Failed` (gồm ruff, prettier, eslint cho `.js`).
- `cmd.migrate` lên → lên → gỡ (`before_uninstall`) → lên: không `Traceback`; đối soát khớp (1 bản ghi, script bằng tệp repo, giá trị cấu hình cũ không bị ghi đè).
- `cmd.test` (`bench --site miyano run-tests --app erp_ai`): `Ran 591 tests`, `FAILED (failures=16, errors=3)`. 19 test đỏ giống hệt trên code FEAT-001 với cùng dữ liệu site, nằm trong 2 module FEAT-002 không sửa (BUG-002, STD-TEST-6): chưa xanh về chữ, không phải hồi quy.
- Không dấu skip mới; không chạm `protected_paths`; Helpdesk không bị FEAT-002 sửa.
- Chưa kiểm: AC-10 (a)–(i) và AC-11 là bước tay của người trên `miyano` (`acceptance.md`, "Bước tay cho người"); cần chạy lại sau mỗi lần nâng Helpdesk/Frappe. Người cũng cần xử lý sự cố quyền tài khoản agent (`acceptance.md`, bảng lỗi, dòng critical) trước khi phát hành. G5 (prod) chỉ người duyệt.

## Review checklist (handbook/STD.md)
- [ ] 1. Implements the spec correctly and completely, nothing extra (STD-DESIGN-5, STD-TEST-2)
- [ ] 2. Only within touchpoints; new files in the right place (STD-DESIGN-1, STD-STRUCT-1, STD-STRUCT-2)
- [ ] 3. Failing test first; edges and errors covered; no skip/xfail/only (STD-TEST-1, STD-TEST-8, STD-TEST-4)
- [ ] 4. Tests not changed to match wrong behavior; tests independent (STD-TEST-5, STD-TEST-6)
- [ ] 5. Errors handled; input validated; external calls have timeouts (STD-ERR-1, STD-ERR-2, STD-ERR-5)
- [ ] 6. No secrets, no injection, authorization in place (STD-SEC-1, STD-SEC-3, STD-SEC-4, STD-SEC-6)
- [ ] 7. Contracts compatible or migration reversible (STD-DESIGN-3, STD-OPS-2)
- [ ] 8. Naming, structure, style per the profile; no dead code (STD-NAME-1, STD-NAME-2, STD-STYLE-4, STD-STYLE-5)
- [ ] 9. New dependencies are justified (STD-DEP-1, STD-DEP-3, STD-DEP-5)
- [ ] 10. Commits, branch and PR follow the standard; docs come along (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-DOC-2)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
