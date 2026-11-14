## Feature
- ID: FEAT-005 (Amendment 2)
- Spec: `docs/team/features/FEAT-005/spec.md` (Amendment 2); design: `docs/team/features/FEAT-005/design-amd2.md`; ADR: `docs/team/adr/ADR-024.md`
- As-Built: `docs/team/features/FEAT-005/asbuilt.md`; release notes: `docs/team/features/FEAT-005/release-notes.md`
- Acceptance: `docs/team/features/FEAT-005/acceptance.md`, Verdict: accepted (qa, `03373f1`)

## Why
Bot ghi bản ghi trực tiếp, không còn bước duyệt (FEAT-004), nên lưới còn lại là nhìn lại sau. Nhật ký chưa có trước/sau của dòng con, hai lời gọi cùng công cụ đè nhau, và cảnh báo hằng ngày báo lặp, báo nhầm và không thấy role bị gỡ. Người chọn "Thu gọn còn phần còn ích" (CHG-001): FEAT-005 giữ đúng hai việc, dựng lại được bot đã đổi gì và cảnh báo mỗi thay đổi role/phân quyền đúng một lần (AC-13, AC-14, AC-19; NFR-3, NFR-8).

## What changed
- `site_api` trả ảnh chụp trước/sau (kể cả dòng con); runner ghi mỗi lời gọi vào `value_before`/`value_after` của dòng `reason` khóa `"<tool>#<n>"`, không cắt, không vào ngữ cảnh model. User chỉ ghi mã và role (AC-13).
- `check_privilege_escalation` đọc nhật ký thay vì `modified_by`: mỗi mục nêu việc, user, role, người ra lệnh, thời điểm; dòng `[QUẢN TRỊ]` đứng trước; 5 mục rồi "…và N mục khác"; hỏng ảnh chụp thì vẫn báo ("không có trước/sau"); ba điều kiện kia giữ nguyên (AC-14).
- Báo đúng một lần: trường chỉ đọc mới `privilege_alert_checked_until` trên `ERP AI Setting` (Single, 0 DDL), cửa sổ `(mốc, now − 300 s]`, khóa `filelock` theo site, mốc không lùi, mốc rỗng báo cả lịch sử một lần (AC-19).
- Lượt của runner có savepoint; lỗi trước dòng `reason` thì hoàn tác mọi ghi của lượt và bỏ callback commit; dòng `propose` của FEAT-004 ghi sau dòng `reason` (NFR-3).
- Khác thiết kế: `asbuilt.md` mục "Differences from design" (đáng chú ý: Error Log là MyISAM nên không rollback cùng thư và mốc, `design-amd2.md` §4.2 "Vì sao báo đúng một lần" chưa nói điều đó; `test_doctype_descriptions.py` đổi 5 dòng vì trường mới).
- Rủi ro còn lại (`acceptance.md`): R-1 sau một lần chạy lỗi dòng Error Log cảnh báo có thể lặp (thư thì không); R-2 mục User ảnh chụp hỏng không có dấu `[QUẢN TRỊ]`; R-3 nợ trong `docs/team/debt.md`; R-4 site dùng chung (migrate từ nhánh này xóa hai DocType "Orphaned" của FEAT-007).
- File chính: `erp_ai/agent/tools/site_api.py`, `erp_ai/agent/runner.py`, `erp_ai/tasks.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/*`, `CHANGELOG.md`, `README.md`.
- Hướng xuống: revert mã và JSON, `cmd.migrate`; cảnh báo quay về kiểu cũ (báo lặp).

## How verified
Lệnh và kết quả copy từ `acceptance.md`; chạy từ `/home/miyano/frappe-bench` dưới `flock` trên `.team/miyano-site.lock`, trong cùng một lần giữ khóa 23:43:13–23:53:36 trên `03373f1`. `bench run-tests` thoát 0 cả khi đỏ, nên bằng chứng là dòng `Ran`/`OK`.

| Kiểm | Kết quả |
|---|---|
| `cmd.test` = `PYTHONPATH=$W bench --site miyano run-tests --app erp_ai` | exit 0; `Ran 1564 tests in 488.122s` / `OK`; `deadlock lines: 0` |
| AC-13: `--module erp_ai.agent.test_agent_runner` + 6 `--test`; `--module erp_ai.agent.tools.test_site_api` + 4 `--test` | `Ran 6 tests in 2.363s OK`; `Ran 4 tests in 1.361s OK` |
| AC-14: `--module erp_ai.tests.test_tasks` + 13 `--test`; `test_privilege_findings_unchanged`; `test_privilege_alert_reads_shared_generic_write_tools` | `Ran 13 tests in 3.038s OK`; `Ran 1 test in 1.571s OK`; `Ran 1 test in 0.373s OK` |
| AC-19: `--module erp_ai.tests.test_tasks` + 8 `--test`; `test_role_change_via_record_tool_alarmed_once`; `test_privilege_alert_watermark_restored_on_human_save`; `test_privilege_alert_watermark_and_clock_rules` | `Ran 8 tests in 1.772s OK`; `Ran 1 test in 0.747s OK`; `Ran 1 test in 0.116s OK`; `Ran 1 test in 0.568s OK` |
| NFR-3: `--module erp_ai.agent.test_agent_runner` + 7 `--test` (hoàn tác lượt) | `Ran 7 tests in 3.298s OK` |
| NFR-8 | các lần chạy AC-19 ở trên; đạt theo cách đo thư + mốc; khe Error Log ở R-1 |
| `cmd.lint` = `pre-commit run --all-files` (bản clone tạm ở `03373f18…`) | exit 0, 12 hook `Passed`, 0 file bị sửa |
| `cmd.migrate` lên/xuống/lên | `has_field` true/false/true; `ERP AI Log` 42 = 42 = 42 = 42; 0 `ALTER TABLE`; múi giờ không DST |
| Skip marker mới trong diff | 0 dòng |
| `protected_paths` | 0 file trùng |
| `cmd.typecheck` | slot rỗng, không áp dụng |
| `cmd.build` | không chạy: diff không có file frontend |
| Chưa kiểm | email cảnh báo thật trên `miyano` (R-5); CI (nhánh chưa push) |

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
