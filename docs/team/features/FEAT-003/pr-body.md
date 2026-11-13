## Feature
- ID: FEAT-003
- Design: `docs/team/features/FEAT-003/design.md`
- As-Built: `docs/team/features/FEAT-003/asbuilt.md`
- Acceptance: `docs/team/features/FEAT-003/acceptance.md` — Verdict: accepted

## Why
Phần 1: người quản trị phải đoán đơn vị, khoảng hợp lệ và field nào do hệ thống tự ghi trên 3 form ERP AI (71 field chưa có mô tả, chưa chia nhóm). Phần 2: nhân viên mở phiếu ở `/helpdesk/tickets/<id>` không có chỗ riêng để đọc hướng giải quyết AI, xem các lần hỏi–đáp với bot và hỏi bot mà không phải nhớ từ khóa. Xem `docs/team/features/FEAT-003/spec.md`.

## What changed
- Phần 1: `description` cho 71/71 field hiển thị của `ERP AI Setting` (22), `ERP AI Credential` (18), `ERP AI Log` (31) và 16 Section Break có nhãn tiếng Việt (6, 4, 6). Chỉ thêm `description` và Section Break; không đổi field nào khác (AC-5).
- Phần 2, vị trí P2: nút "Trao đổi với bot" trên header trang phiếu mở một ngăn gắn vào `document.body` (desktop, từ 640 px). Lý do không dùng tab (P1): tab của Helpdesk viết cứng, thêm phải sửa Helpdesk. Mã: `erp_ai/public/js/agent_status_indicator.js`.
- Phần 2, server: `erp_ai/ticket_panel.py` với 2 method chỉ POST, không Guest: `get_panel_data` (đọc, 0 câu ghi SQL) và `send_message` (đúng 1 comment của người gửi qua `HD Ticket.new_comment`, tự thêm từ khóa, escape HTML). `erp_ai/constants.py` thêm `PANEL_METHODS`, `PANEL_MAX_MESSAGE_CHARS`; `erp_ai/agent/policy.py` thêm `get_trigger_keyword()` (`contains_keyword` không đổi).
- Ngăn không ghi field, không tự xét chốt agent, không trả từ khóa hay cấu hình, chỉ dùng `textContent`.
- Tài liệu: `README.md` (mục khu vực trao đổi với bot), `CHANGELOG.md`, `docs/team/debt.md` (minor hoãn).
- Lệch design (chi tiết ở `asbuilt.md`): DEV-1 `text` sai kiểu ném `FrappeTypeError` thay vì `ValidationError` (review-T9-r1); DEV-2 ERP AI Setting có 6 Section Break, thiếu `section_reply` của design; DEV-3 từ khóa đọc hai lần mỗi lần gửi.
- Lưu ý: `diff.patch` của feature cắt từ `a1d03b7` nên còn chứa mã BUG-001/BUG-002; diff đúng của FEAT-003 là `git diff 0051042 7cb654f -- erp_ai` (11 file).

## How verified
Trên commit `7cb654f` (lệnh và đầu ra trong `acceptance.md`):
- `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`): `Ran 658 tests in 118.339s` `OK`, junit 0 failure/error/skipped. Lưu ý `bench run-tests` trả exit 0 cả khi test đỏ; bằng chứng là dòng `OK` và junit.
- `cmd.lint` (`pre-commit run --all-files`, trong worktree sạch tại `7cb654f`): 13 hook `Passed`, `lint_exit=0`.
- `cmd.migrate` (`cd ../.. && bench --site miyano migrate`): exit 0, ERP AI Setting và role `ai.agent` giống trước/sau.
- 8/8 đột biến (M1–M7, M4b) bị test bắt; POST Guest vào `get_panel_data`: `http=403`, `PermissionError`.
- Chưa chạy (`ui: false`, không có Playwright): bước tay J1.1–J1.7 trên trình duyệt, gồm AC-11 và NFR-3 (thời gian thực). Việc của người sau bàn giao, trước mọi lần lên prod (G5); kịch bản ở `acceptance.md`.

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
