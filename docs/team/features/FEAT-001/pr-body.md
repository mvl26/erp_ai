## Feature
- ID: FEAT-001 (AI Agent `erp_ai` cho Helpdesk Miyano, `L0`/`L1`)
- Design: `docs/team/features/FEAT-001/design.md`
- As-Built: `docs/team/features/FEAT-001/asbuilt.md`
- Acceptance: `docs/team/features/FEAT-001/acceptance.md` — Verdict: accepted (commit `533180a`)

## Why
Helpdesk tồn 62/71 phiếu mở (guide `:68`). Cần agent phân loại phiếu vào 6 đầu mục A–F và, khi đã đo đủ chính xác, ghi hướng giải quyết/comment, với thẩm quyền theo người, chốt an toàn và kiểm soát chi phí. Nguồn: `docs/team/features/FEAT-001/spec.md` (20 AC, 9 NFR).

## What changed
- App mới `erp_ai`, cài xong tắt, mức `L0`. Mã trong `erp_ai/`: `agent/` (runner, policy, authority, tool), `gateway/` (cổng model duy nhất, quản lý khóa, cầu dao), `eval/` (bộ đánh giá offline), DocType `ERP AI Setting`/`ERP AI Credential`/`ERP AI Log`, báo cáo `ERP AI Accuracy`, `handlers.py` (doc_events), `tasks.py` (scheduler), `install.py`.
- Phạm vi dừng ở `L0`/`L1` (spec A-1); `L2`/`L3` cấp bộ tool `L1`.
- Lệch guide/design gốc đã amend vào design (chi tiết `asbuilt.md`): D2 test vào `erp_ai/tests/`; D3 `cmd.*` một đoạn; D4 `git_source` chỉ `log`/`blame`; D5 nhận `[GẬP]` và `[GẤP]`; D6 trường USD là Float; D7 `ignore_links_on_delete = ["ERP AI Log"]`; D8 comment từ core `Comment`; D9 trường `skipped_fields` trên `ERP AI Log`; D10 đổi tên `test_agent_runner.py` + luật kiến trúc.
- Thay đổi ngoài mã: `README.md`, `CHANGELOG.md`, `pyproject.toml` (`anthropic>=0.103.1,<1`), `.github/workflows/ci.yml`, `.gitignore`, tài liệu `docs/team/**`.
- Việc người phải làm trước khi bật (đặt lại `ERP AI Setting` trên `miyano`, kiểm Helpdesk production ≥ 15.1.0, AC-19, AC-20, khóa API và ngân sách, guide §18, §19, dọn Error Log): `asbuilt.md` mục 6.

## How verified
Từ `acceptance.md` (commit `533180a`), site `miyano`:
- `bench --site miyano run-tests --app erp_ai` → exit 0, `Ran 507 tests ... OK`, bằng tổng theo 25 module.
- `pre-commit run --all-files` → exit 0, 12 hook `Passed`.
- `bench --site miyano migrate` → exit 0.
- `bench --site miyano run-tests --module erp_ai.agent.test_agent_runner` và các module khác → exit 0 (mỗi AC có test, xem bảng trong `acceptance.md`).
- Grep dấu skip trong diff `*.py` → rỗng; grep `protected_paths` → rỗng.
- Chưa kiểm: AC-19 (bấm "Kiểm tra khóa") và AC-20 (chụp màn hình) chờ người; CI workflow thật chưa chạy vì feature cấm push; scheduler thật trên `miyano`; `uninstall-app`.

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
