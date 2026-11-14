## Feature
- ID: FEAT-004 (kèm CHG-001, task T53–T70)
- Design: `docs/team/features/FEAT-004/design.md` (+ phụ lục 2–4), `docs/team/features/CHG-001/design.md`
- As-Built: `docs/team/features/FEAT-004/asbuilt.md`; release notes: `docs/team/features/FEAT-004/release-notes.md`
- Acceptance: `docs/team/features/FEAT-004/acceptance.md` — Verdict: accepted, theo quyết định của người ngày 2026-11-14 ("Chấp nhận với bằng chứng hiện có"); không phải nghiệm thu sạch: không có lần chạy cả app xanh, phán quyết riêng của qa vẫn là `rework` (xem "How verified")

## Why
Người ra lệnh cho bot sửa code và chạy lệnh `bench` dưới sự duyệt của người, rồi (CHG-001) "làm luôn, không cần hỏi, chỉ cần một nút duyệt hoặc không duyệt" (spec Amendment 1, 2, 3). Không có tính năng này bot chỉ ghi phân loại và comment.

## What changed
- Hai công tắc `ERP AI Setting`, cài xong đều tắt: `code_change_enabled` và `unrestricted_enabled`. Cả hai tắt thì tool và prompt giống bản trước.
- Công tắc code bật + `L3` + có người ra lệnh: bot ghi bản ghi trực tiếp, không qua duyệt (tạo User, gán vai trò nghiệp vụ, sửa cấu hình), và đề xuất sửa file hoặc lệnh `bench` (`migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build`, `version`). Mọi thay đổi code và lệnh chờ người có `ERP AI Instructor` bấm Duyệt trong comment của bot (form Desk, một lần POST, không hộp xác nhận); áp dụng = ghi file + đúng một commit git local; hoàn tác = commit hoàn tác; bot không push.
- "Toàn quyền (khẩn cấp)" bật, từ `L1`, có người ra lệnh: thêm xóa, submit/hủy, gọi hàm whitelist, bỏ giới hạn vai trò và tài khoản (gán được `System Manager`). Không hẹn giờ tắt, không cảnh báo khi đang bật. Chặn đọc khóa/mật khẩu qua hàm gọi tự do chỉ ở mức cố gắng, sáu dạng còn lọt ở `asbuilt.md` mục 5.
- DocType mới `ERP AI Change Proposal`; `ERP AI Log` thêm `entry_type=change`, `trigger=change_action`, `change_proposal`, `change_step`, `actor`; cột `actions` có trần 60000 byte.
- Tài khoản agent bị từ chối ở duyệt, áp dụng, hoàn tác kể cả khi mang `ERP AI Instructor`; sau mỗi kết cục có một dòng `Info` trên phiếu.
- Khác thiết kế: `asbuilt.md` mục "Differences from design" (đáng chú ý: hai nhóm cấp tool mới, ô `unrestricted_enabled`, method `decide`, trần cỡ nhật ký, chữ ký `validate_change_apps`).
- File chính: `erp_ai/agent/changes/*`, `erp_ai/agent/tools/{change_guard,propose_change,site_api,registry}.py`, `erp_ai/change_decision.py`, `erp_ai/agent/change_link.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/*`, `CHANGELOG.md`, `README.md`.
- Hướng xuống: đặt cả hai công tắc về 0; revert mã xóa DocType `ERP AI Change Proposal` và mọi đề xuất (mất dữ liệu kiểm toán).
- Lưu ý: commit `789d524` có dòng `Co-Authored-By` (STD-GIT-8), chưa amend.

## How verified
Lệnh và kết quả copy từ `acceptance.md`; chạy từ `/home/miyano/frappe-bench` với `cmd.test_one`/`cmd.test`, dưới `flock` trên `.team/miyano-site.lock`. `bench run-tests` thoát 0 cả khi đỏ, nên bằng chứng là dòng `Ran`/`OK|FAILED`.

| Kiểm | Kết quả |
|---|---|
| `cmd.test` cả app (một lần giữ khóa, `da00518`) | exit 0; `Ran 1499 tests in 802.131s` / `FAILED (failures=2, errors=12)`; lần trước `Ran 1496 tests in 1079.598s` / `FAILED (failures=1, errors=128)`; **chưa lần nào OK** (deadlock 1213 do site dùng chung); 14 test đỏ chạy lại theo tên: 6 xanh, 8 vẫn 1213 |
| `cmd.test_one` `test_apply_job` (`ba89ab3`) | `Ran 117 tests in 178.351s` / `OK` |
| `cmd.test_one` `test_agent_runner` | `Ran 85 tests in 36.358s` / `OK` |
| `cmd.test_one` `test_agent_write_guard` | `Ran 5 tests in 1.226s` / `OK` |
| `cmd.test_one` `test_erp_ai_change_proposal` | `Ran 25 tests in 74.421s` / `OK` |
| `cmd.test_one` `test_change_decision` (sau T70) | `Ran 10 tests in 25.731s` / `OK` |
| `cmd.test_one` `test_gateway` (dev/reviewer, sau T69) | `Ran 65 tests in 8.204s` / `OK`; qa chưa có lần chạy riêng xanh (F-3) |
| `cmd.lint` `pre-commit run --all-files` | exit 0, 12 hook `Passed`, 0 `Failed` |
| `cmd.migrate` | exit 0 (qa 20:18); up-down-up do qa chưa làm (R-3) |
| Skip marker trong diff | `0` |
| NFR-9, HEAD và `status` của `frappe`, `erpnext`, `helpdesk`, `hrms` trước = sau `cmd.test` | `diff` rỗng |
| `protected_paths` | 0 file trùng |
| Chưa kiểm: form duyệt bằng mắt (AC-22), một lần bấm Duyệt thật (AC-25), dòng kết quả trên trang phiếu thật (AC-28), model thật (AC-29) | việc của người sau merge |

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
