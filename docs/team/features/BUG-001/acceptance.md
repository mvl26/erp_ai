Feature: BUG-001
Stage: verify
Author-agent: qa
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance BUG-001

- Commit kiểm: `64c2c4e0631749effdfe04eebdc39defb0edd643` (`team/BUG-001`), từ `git rev-parse HEAD` trước mọi lệnh bên dưới; lặp lại sau khi chạy xong vẫn là `64c2c4e…`.
- Nhánh gốc để so diff: `team/FEAT-001` (`23ded66`, cũng là merge-base). `git rev-parse --verify main` → `fatal: Needed a single revision`, exit 128 (`base_branch` trong config không tồn tại; team-leader chỉ định `team/FEAT-001`).
- Cây làm việc: `git status --porcelain` không rỗng nhưng chỉ có `docs/team/metrics/{runs,sessions}.jsonl` (sửa) và tệp chưa track `.claude/agent-memory/`, `.github/…` của onboarding; `git status --porcelain -- erp_ai docs/team/features` rỗng → mã và test đang chạy đúng là của commit trên.
- `team.py status BUG-001` → `built  READY  /team:verify BUG-001` (exit 0).
- Bug-fix cỡ S, không có `spec.md`/`design.md` riêng: tiêu chí lấy từ lời giao của team-leader, `intake.md`, `tasks.md` T1 và guide `docs/HuongDan_TrienKhai_erp-ai.md:797`; bảng gốc là FEAT-001 `design.md` §3.4.3.

## Tiêu chí
| criterion | command | exit | output excerpt | covering test | verdict |
|---|---|---|---|---|---|
| AC-1 — 400 có message bắt đầu `Your credit balance is too low` được xếp như hàng 6: `Hết hạn mức`, chuyển khóa, gửi tin (`quota`) | `cd ../.. && bench --site miyano run-tests --module erp_ai.gateway.test_breaker` | 0 | `Ran 6 tests in 0.003s` / `OK` | `erp_ai/gateway/test_breaker.py::TestBreaker::test_breaker_table` subTest `row6 400 credit balance` — kỳ vọng hard-code `Action(QUOTA, None, True, "message", "quota")`, giống hệt ca `row6 400 quota message`; input là message thật của API cắt `[:100]` như `client.py:55` | đạt |
| AC-1 (bằng chứng trên site, chỉ đọc) — khóa thật chuyển trạng thái và có tin | `cd sites && ../env/bin/python -c '…frappe.db.get_all("ERP AI Credential", filters={"label":"Chính"}, fields=[status,error_count,last_error,…]); frappe.db.get_all("Email Queue", order_by="creation desc", limit=1)…'` (chỉ đọc, không commit, không đọc `api_key`) | 0 | `CRED {'label': 'Chính', 'status': 'Hết hạn mức', 'error_count': 1, 'last_error': 'quota status=400 request_id=req_011CgxKhSjL94rcCpaDG857N', 'enabled': 1}` · `EQ {'name': 'tfldrp7li8', 'status': 'Not Sent', 'creation': 2026-11-12 10:27:46}` · thân thư: `Khóa 'Chính': quota (status=400); trạng thái khóa chuyển sang 'Hết hạn mức'.` | Dòng Email Queue tạo 10:27:46, trước lần chạy test đầu tiên của qa (junit `gw.xml` ghi lúc 10:30:42) và test không dùng nhãn `Chính` (`grep -rn "Chính" erp_ai --include=*.py` rỗng) → đây là lần `check_keys` của team-leader (journal BUG-001 dòng cuối), không phải dữ liệu test. `Not Sent` vì scheduler tắt (journal) | đạt |
| AC-1 (đường gateway) — Action `quota` → khóa `Hết hạn mức`, gửi tin, chuyển khóa kế | `cd ../.. && bench --site miyano run-tests --module erp_ai.gateway.test_gateway --junit-xml-output <scratch>/gw.xml` | 0 | `Ran 61 tests in 2.297s` / `OK` | `erp_ai/gateway/test_gateway.py::TestCallModel::test_quota_402_marks_key_sends_notice_and_switches` (status = `Hết hạn mức`, `credential_label == "k2"`, `notice.assert_called_once()`, `alarm.assert_not_called()`). `gateway/__init__.py:110-114` chỉ dùng Action do `decide` trả; Action của ca tín dụng bằng đúng `_quota()` của hàng 5/6 | đạt |
| AC-2 — các hàng khác của bảng cầu dao không đổi | `git diff team/FEAT-001...team/BUG-001 -- erp_ai` và `git diff … -- 'erp_ai/**/test_*.py' \| grep -nE '^-[^-]'` | 0 / 1 | `breaker.py` 2+/2−: chỉ `QUOTA_MESSAGE_PREFIX = "You have reached your specified"` → `QUOTA_MESSAGE_PREFIXES = ("You have reached your specified", "Your credit balance is too low")` và dòng 57 `startswith(QUOTA_MESSAGE_PREFIX)` → `startswith(QUOTA_MESSAGE_PREFIXES)`; `test_breaker.py` 10+/0−; grep dòng bị xóa trong test: rỗng (exit 1) | Toàn bộ 19 ca cũ của `test_breaker_table` giữ nguyên và xanh, gồm biên/đường lỗi: `row8 400 other` (`message_prefix="bad"`) → `bad_request`; `row8 422` → `bad_request`; `test_400_quota_prefix_only_applies_to_400` (422 + tiền tố quota → `bad_request`); `row7 401/403` → `Lỗi khóa`/`alarm` | đạt |
| AC-3 — test tái hiện đỏ trước khi sửa, xanh bây giờ | đỏ: trích `review-01.md` + journal dòng 3; điều kiện cũ: `git show team/FEAT-001:erp_ai/gateway/breaker.py \| grep -n QUOTA_MESSAGE_PREFIX`; xanh: lệnh của AC-1 | 0 | review-01: `RED: Ran 6 tests, FAILED (failures=1): test_breaker_table [row6 400 credit balance] AssertionError: Action(new_status=None, ..., 'bad_request') != Action(new_status='Hết hạn mức', ..., 'quota')` (lỗi assertion, không phải import). Điều kiện cũ: `26:QUOTA_MESSAGE_PREFIX = "You have reached your specified"` · `57: if status == 400 and failure.message_prefix.startswith(QUOTA_MESSAGE_PREFIX):` → chuỗi `Your credit balance…` không khớp, rơi vào nhánh `400 <= status < 500` → `bad_request`, đúng như đỏ đã dán. Xanh: `Ran 6 tests … OK` (AC-1) | `test_breaker_table` subTest `row6 400 credit balance` — bỏ phần tử thứ hai của tuple thì ca này đỏ lại (đã thấy ở RED), nên test có thể trượt (STD-TEST-5) | đạt |
| AC-4 — toàn bộ suite xanh | `cd ../.. && bench --site miyano run-tests --app erp_ai --junit-xml-output <scratch>/app.xml` | 0 | `Ran 507 tests in 114.437s` / `OK`; junit: 507 `<testcase>`, 0 `<failure\|<error\|<skipped` | junit `--app` chứa đủ 6 test của `erp_ai.gateway.test_breaker`; 61 test của `test_gateway` đều có trong `--app` (`comm -23 gw.txt app.txt \| wc -l` → `0`); không còn tệp `test_runner.py` (`find erp_ai -name test_runner.py` rỗng) nên bẫy bỏ sót của Frappe không áp dụng | đạt |

## Kiểm chung
- `cmd.test`: exit 0, `Ran 507 tests … OK`, 0 failure/error/skip (junit). Không có Traceback trong log (`grep -iE "Traceback|Error Log|DeprecationWarning" app.log` rỗng); chỉ có dòng `Enqueuing HelpdeskSearch.index_doc …` của helpdesk.
- `cmd.lint` (`pre-commit run --all-files`): exit 0, 12/12 hook `Passed` (ruff import sorter, ruff linter, ruff formatter, prettier, eslint, …); `git status --porcelain -- erp_ai docs/team/features` sau lint rỗng.
- `cmd.typecheck`: slot rỗng trong profile → không áp dụng.
- `cmd.build` (`bench build --app erp_ai`): exit 0, `DONE Total Build Time: 114.162ms`, `Compiling translations for erp_ai`.
- Dấu skip mới trong diff: `git diff team/FEAT-001...team/BUG-001 -- '*.py' | grep -nE '^\+.*(@unittest\.skip|@unittest\.skipIf|@unittest\.expectedFailure|\.skipTest\()'` → rỗng (exit 1).
- Assertion bị xóa/nới: `git diff … -- '*.py' | grep -nE '^-.*assert'` → rỗng (exit 1).
- Migration lên/xuống: không áp dụng — diff chỉ đổi `breaker.py`, `test_breaker.py` và tài liệu; không có DocType JSON hay patch.

## Acceptance checklist (6)
1. Mỗi tiêu chí có lệnh thật, đầu ra, kết luận — đạt (STD-TEST-2).
2. `cmd.test` xanh, `cmd.lint` xanh, `cmd.typecheck` không có slot — đạt (STD-TEST-3, STD-STYLE-2, STD-STYLE-3).
3. Diff không thêm dấu skip — đạt (STD-TEST-4).
4. Migration — không áp dụng, không có migration trong diff — đạt (STD-OPS-2, STD-OPS-3).
5. Phần build của DoD đủ (test tái hiện + mã trong T1; guide `:797` đã mô tả đúng hành vi mới) — đạt (STD-DOC-1, STD-DOC-2, STD-DOC-3).
6. `git diff --name-only team/FEAT-001...team/BUG-001` không chạm `protected_paths` (grep `.env|.pem|.key|license.txt` rỗng, exit 1); không có khóa trong diff (grep `sk-ant-(api|usr|admin)…` rỗng, exit 1) — đạt (STD-SEC-1).

## DoD
- [x] Test tái hiện viết trước, đỏ rồi xanh (T1, review-01).
- [x] Mã sửa chỉ trong touchpoints T1 (`breaker.py`, `test_breaker.py`).
- [x] Tài liệu người dùng: guide `docs/HuongDan_TrienKhai_erp-ai.md:797` ("Hết credit / vượt spend limit → `Hết hạn mức` … Có, và báo tin") đã khớp hành vi chạy được; không cần sửa.
- [ ] As-Built BUG-001 — chủ: writer, sau G4 (`/team:asbuilt BUG-001`). Kiểm lại: `ls docs/team/features/BUG-001/asbuilt.md`.
- [ ] CHANGELOG — chủ: writer, sau G4. Kiểm lại: `git diff team/FEAT-001...team/BUG-001 -- CHANGELOG.md`.
- [ ] FEAT-001 `design.md` §3.4.3 hàng 6 chưa ghi thêm "hoặc `Your credit balance is too low`" (deferred từ review-01) — chủ: writer/designer trong As-Built BUG-001, sau G4. Kiểm lại: `grep -n "credit balance" docs/team/features/FEAT-001/design.md`. Đây là tài liệu thiết kế nội bộ, không phải README/tài liệu người dùng mô tả sai → không phải lý do rework.

## Ghi chú, hoãn lại
- minor từ review-01 (ca 422 + `CREDIT_PREFIX`) vẫn hoãn; điều kiện `status == 400` dùng chung với tiền tố cũ đã được `test_400_quota_prefix_only_applies_to_400` phủ.
- qa không ghi `.team/current.json` (vai qa chỉ ghi `acceptance.md` và memory); team-leader cập nhật nếu cần.
- Nguyên nhân gốc trên site vẫn là tổ chức Console hết credit — việc của người (nạp credit hoặc khóa workspace `sk-ant-api03-` còn credit), ngoài phạm vi mã.

Verdict: accepted
