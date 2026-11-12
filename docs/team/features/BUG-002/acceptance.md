Feature: BUG-002
Stage: verify
Author-agent: qa
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance BUG-002

- Commit kiểm: `765b696a9c44c198f633879b6a061ad84d56cd12` (nhánh `team/BUG-002`, checkout chính, không đổi nhánh theo chỉ dẫn team-leader). Mọi đầu ra dưới đây chạy sau `git rev-parse HEAD`, trên commit này.
- Cây làm việc: `git status --porcelain -- erp_ai` → rỗng (mã app sạch). Có tệp bẩn/untracked ngoài mã (`docs/team/**/FEAT-003`, `.github/*`, `.gitignore`, `docs/team/metrics/runs.jsonl`) — tài liệu của FEAT-003, không được nạp vào lượt chạy test.
- Base so sánh: `team/FEAT-002` (`base_branch` = `main` không tồn tại); merge-base `a1d03b7`.
- Tiêu chí: 4 ý trong intake "Kết quả mong đợi" (bug-fix không có spec.md), theo cách team-leader tách thành (1)–(4).
- Kết luận: chấp nhận (xem dòng `Verdict:` cuối tệp).

## Tiêu chí
| criterion | command | exit code | output excerpt | covering test | verdict |
|---|---|---|---|---|---|
| AC-1a: 15 test TestCheckPrivilegeEscalation (12F+3E trước đây) xanh trên dữ liệu sống | `cd ../.. && bench --site miyano run-tests --module erp_ai.tests.test_tasks` | 0 | `Ran 34 tests in 1.019s` / `OK` (trước sửa: `Ran 33 … FAILED (failures=12, errors=3)`, review-01) | `erp_ai/tests/test_tasks.py::TestCheckPrivilegeEscalation::*` | đạt |
| AC-1b: 4 test accuracy (4F trước đây) xanh trên log sống | `cd ../.. && bench --site miyano run-tests --module erp_ai.erp_ai_agent.report.erp_ai_accuracy.test_erp_ai_accuracy` | 0 | `Ran 13 tests in 0.431s` / `OK` (trước sửa: `Ran 13 … FAILED (failures=4)`, review-02) | `test_erp_ai_accuracy.py::AccuracyTestCase` và lớp con | đạt |
| AC-1c: toàn bộ suite xanh | `cd ../.. && bench --site miyano run-tests --app erp_ai` (`cmd.test`) | 0 | `Ran 592 tests in 101.912s` / `OK`; `grep -c -i traceback` = 0; `find erp_ai -name test_runner.py` → rỗng (không có module bị `--app` bỏ sót) | toàn app | đạt |
| AC-1 điều kiện dữ liệu sống | snapshot python chỉ đọc (dưới) | 0 | trước lượt chạy: `HAS_ROLE agent count = 99`, `COUNT ERP AI Log classify = 2`, `COUNT ERP AI Log = 35` | — | đạt (dữ liệu thật vẫn còn khi test xanh) |
| AC-2: giữ ý nghĩa test, không skip/xfail, mã sản phẩm không đổi do BUG-002 | `git diff team/FEAT-002...team/BUG-002 -- '*.py' \| grep -E '^\+.*(@unittest\.skip\|@unittest\.skipIf\|@unittest\.expectedFailure\|\.skipTest\(\|xfail)'`; `… \| grep -E '^-.*(assert\|self\.assert\|assertRaises)'`; `git diff --name-only … \| grep -v test_*.py` | 1 / 1 | cả hai grep rỗng; tệp không phải test duy nhất trong `erp_ai/`: `erp_ai/gateway/breaker.py`, đến từ commit `283b174 fix(gateway): treat credit-balance 400 as quota (BUG-001)` (merge BUG-001), không do task T1–T3 | đọc diff `test_tasks.py`, `test_erp_ai_accuracy.py` (mục "Chất lượng test") | đạt (1 minor deferred) |
| AC-3: không rò — snapshot trước = sau | python chỉ đọc qua `/home/miyano/frappe-bench/env/bin/python` từ `sites/` (bỏ trường Password; giá trị chứa `@` bị che) | 0 / 0 | trước = sau: `SETTING sha256 = f0df1729b1250a9e` (toàn bộ trường không phải Password, kể cả bảng con credentials); `enabled = 1`, `permission_level = "L3"`, `excluded_teams = ""`, `monthly_budget_usd = 100.0`, giá 0.1/0.125/0.01/0.5, `trigger_keyword = "@ai"`, `thinking_text = "Đang suy nghĩ…"`, `answer_delay_min_s = 3`, `answer_delay_max_s = 5`; `HAS_ROLE agent count = 99 sha256 = f1fc56aa1e7ad0e3`; HD Team 4/4, HD Ticket 5/5, ERP AI Log 35/35, classify 2/2, HD Form Script 1/1, Custom Field 243/243, Property Setter 182/182, Server Script 0/0, Webhook 0/0, Custom DocPerm 1360/1360, Error Log 213/213; Comment 120392 → 120398 (+6) | — | đạt |
| AC-3 nhiễu Comment | `frappe.get_all('Comment', fields=[comment_type, reference_doctype, creation], order_by='creation desc', limit=8)` | 0 | 6 dòng mới = 3 cặp `Deleted Email Account` / `Deleted Holiday List` lúc 15:52:35–15:52:45 (bootstrap của test runner, nhiễu đã biết +2 mỗi lượt chạy module) | — | đạt (nhiễu đã biết) |
| AC-4: sửa credit-balance của BUG-001 có mặt và xanh | `cd ../.. && bench --site miyano run-tests --module erp_ai.gateway.test_breaker` | 0 | `Ran 6 tests in 0.003s` / `OK`; diff: `QUOTA_MESSAGE_PREFIXES = ("You have reached your specified", "Your credit balance is too low")` | `erp_ai/gateway/test_breaker.py` ca `"row6 400 credit balance"` → `Action(QUOTA, None, True, "message", "quota")` | đạt |

Ca biên/lỗi: các ca dương tính của TestCheckPrivilegeEscalation (thừa `System Manager`, mất role bắt buộc, bản ghi quyền do agent sửa, Server Script/Webhook do agent bật, thiếu tài khoản agent) vẫn chạy trên cùng dữ liệu sống và đều nằm trong `Ran 34 … OK` — chúng khẳng định `call_count == 1` và nội dung cảnh báo, nên bước cách ly ở setUp không che mất cảnh báo thật.

## Chất lượng test (đọc diff `team/FEAT-002...team/BUG-002`)
- `test_tasks.py` setUp: xóa Has Role của agent rồi thêm đúng `{ROLE_AGENT, HELPDESK_AGENT_ROLE}`, `_neutralize_agent_rows()` đổi `modified_by` của 6 PERMISSION_DOCTYPES về Administrator, tắt Server Script/Webhook do agent sở hữu — đúng ba điều kiện mà `tasks.py:79,88,97` đọc; tất cả nằm trong transaction được rollback. Không assertion nào bị xóa/nới; giá trị kỳ vọng vẫn hard-code.
- `test_allowed_roles_do_not_alarm`: trước tự thêm role cho phép nếu thiếu; nay setUp lo phần đó và test thêm `Desk User` (role tự động, bị trừ ở `tasks.py:79`) — ca được mở rộng, không yếu đi.
- `test_alarm_when_agent_lost_a_required_role`: chỉ bỏ đoạn thêm role trùng với setUp; assertion giữ nguyên.
- `test_erp_ai_accuracy.py`: setUp đổi `entry_type` các dòng `classify` có sẵn thành `reason` trong transaction (rollback ở cleanup); kỳ vọng của test không đổi. Snapshot cho thấy classify 2 → 2, không rò.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| minor | STD-TEST-5 | erp_ai/tests/test_tasks.py:339-347 | `test_setup_neutralizes_live_rows_attributed_to_agent` tự gọi `_neutralize_agent_rows()` nên vẫn xanh nếu bỏ lệnh gọi trong setUp; test vẫn đỏ khi helper hỏng (dev ghi `Called 2 times` với helper no-op). Hồi quy "bỏ dây setUp" chỉ lộ ra trên site có dòng thật của agent. Không chặn (đã deferred ở review-01). | Đổi tên test cho đúng việc nó kiểm, hoặc kiểm trong test rằng `setUp` đã vô hiệu hóa dòng tạo trước setUp (vd tạo dòng ở `setUpClass`); ghi vào debt. |
| minor | STD-STYLE-5 | erp_ai/tests/test_tasks.py:197 | Guard `frappe.db.exists("DocType", doctype)` luôn đúng trên Frappe v15 (đã deferred ở review-01). | Bỏ guard khi dọn. |

## Kiểm chung
- `cmd.test`: `bench --site miyano run-tests --app erp_ai` → exit 0, `Ran 592 tests in 101.912s`, `OK` (0 failure, 0 error).
- `cmd.lint`: chạy theo chỉ dẫn team-leader trên các tệp đổi — `pre-commit run --files erp_ai/tests/test_tasks.py erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py erp_ai/gateway/test_breaker.py erp_ai/gateway/breaker.py` → exit 0; ruff import sorter/linter/formatter `Passed`, ast/trailing-whitespace/merge-conflicts/debug statements `Passed`. Không chạy `--all-files` (cây có tệp FEAT-003 bẩn ngoài phạm vi).
- `cmd.typecheck`: slot rỗng trong profile — không áp dụng.
- `cmd.build`: không chạy — diff không chạm asset/JS (chỉ `.py`).
- Dấu skip mới trong diff: không có (grep `@unittest.skip|@unittest.skipIf|@unittest.expectedFailure|.skipTest(|xfail` trên dòng `+` → exit 1, rỗng). Assertion bị xóa: không có (grep dòng `-` chứa assert → exit 1, rỗng).
- Bí mật trong diff: grep `sk-ant|(api_?key|secret|password|token)\s*=\s*"…"` trên `git diff … -- erp_ai` → exit 1, rỗng.
- Migration lên/xuống: không áp dụng (diff không có patch/migration hay đổi DocType JSON).
- Bằng chứng hồi quy (bug-fix): RED trước sửa có trong review-01 (`Ran 33 tests ... FAILED (failures=12, errors=3)`) và review-02 (`Ran 13 tests ... FAILED (failures=4)`).

## Acceptance checklist (6)
1. Mỗi tiêu chí chạy lệnh thật, dán đầu ra, kết luận: đạt (STD-TEST-2).
2. `cmd.test` xanh, `cmd.lint` xanh trên tệp đổi, `cmd.typecheck` không có slot: đạt (STD-TEST-3, STD-STYLE-2, STD-STYLE-3).
3. Diff không thêm dấu skip: đạt (STD-TEST-4).
4. Migration: không áp dụng — không có migration trong diff (STD-OPS-2, STD-OPS-3).
5. Phần build của DoD đủ: test sửa trong T1/T2, T3 điều tra không có diff (review-03), `docs/team/defects.md` dòng BUG-002 "đã sửa (team/BUG-002)": đạt (STD-DOC-1/2/3).
6. Diff không chạm `protected_paths` (grep `.env|*.pem|*.key|license.txt` trên `--name-only` → exit 1, rỗng) và không có bí mật: đạt (STD-SEC-1).

## DoD
- [x] Test: 19 test đỏ → xanh; `Ran 592 … OK` (≥ 591 như tasks.md yêu cầu).
- [x] Mã sản phẩm: không đổi trong BUG-002 (chỉ `breaker.py` từ merge BUG-001, đã có test).
- [x] Site nguyên vẹn sau lượt chạy (AC-3).
- [ ] As-Built  - [ ] README/tài liệu  - [ ] CHANGELOG — owner: writer, sau G4 (`/team:asbuilt BUG-002`); kiểm lại: `ls docs/team/features/BUG-002/as-built.md && grep -n BUG-002 CHANGELOG.md`.

## Deferred
- Hai minor ở bảng phát hiện (STD-TEST-5, STD-STYLE-5) → debt, không chặn.
- Dữ liệu site cho người xử lý (ngoài phạm vi): tài khoản agent còn 99 role; nguồn `permission_level = L0` lúc 13:49–13:51 chưa quy được (review-03).

Verdict: accepted
