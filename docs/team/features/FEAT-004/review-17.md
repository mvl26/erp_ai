Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 17 — FEAT-004 T17

- Diff: `git diff 630f05d..team/FEAT-004-task-17` (2 commit `7f14fec`, `6cafa7c`; 3 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 630f05d..7f14fec`)
Lớp 1: nút, kiểm role, xác nhận → POST → tải lại và `set_intro` có escape khớp design 3.3; đúng touchpoint; AC-5 giữ ở server.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-5 | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js:45 | Hộp thoại Duyệt luôn ghi "File sẽ được ghi và có một commit." kể cả với đề xuất `Lệnh bench` (lệnh chạy và không hoàn tác được) | chọn câu theo `change_kind`; với lệnh dùng "Lệnh bench sẽ chạy" và nhắc `Lệnh bench không hoàn tác được.`; thêm dòng kiểm tay |
| major | STD-TEST-2 | docs/team/features/FEAT-004/dev-notes.md:109 | Bước kiểm tay duy nhất về hiển thị nút mong "không có nút" cho Administrator; Frappe cho Administrator mọi role (`permissions.py:519-520`) nên nút vẫn hiện, chỉ server từ chối (`NEVER_AUTHORITY`) | sửa kết quả mong đợi: nút hiện, bấm trả 403, không đổi gì (AC-5) |
| major | STD-TEST-5 | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py:922-949 | subTest "approve confirmation repeats branch line and core warning" chỉ kiểm tên hằng có trong thân hàm; bỏ `lines.push(branch_note)`, bỏ push cảnh báo lõi, đổi chỗ hai tiền tố hay bỏ `.split(". ")[0]` vẫn xanh | ghim nguyên câu lệnh; bỏ chú thích khỏi nguồn trước khi so |

minor | — | — | 4 điểm nhỏ: mẫu nút khớp cả lời gọi trong `/* */`; chuyển `frm.reload_doc()` ra ngoài `callback` vẫn xanh; chữ Từ chối "Không có gì được ghi" chưa đúng; chữ Hoàn tác không hợp với file mới | tùy dev

Các điểm đã chấm: design chốt 3 nhãn nút và yêu cầu hộp thoại Duyệt nhắc dòng nhánh + câu đầu cảnh báo lõi (escape), để mở câu hỏi của hộp thoại; không đường nào hiện chữ chưa escape (STD-SEC-3 đạt); tiền tố khớp `change_text.py:88,99` được test ghim bằng cách chạy `proposal_notes`.

## Vòng 2 — approve (re-review theo phạm vi, `git diff 7f14fec..team/FEAT-004-task-17`, +98/-8)
- Phát hiện 1: ADDRESSED (`erp_ai_change_proposal.js:48-51` chọn câu theo `change_kind`; test ghim cả biểu thức, dùng `CHANGE_KIND_COMMAND`, kiểm "File sẽ được ghi" xuất hiện đúng 1 lần)
- Phát hiện 2: ADDRESSED (`dev-notes.md:109-110`: Administrator thấy nút, server trả 403)
- Phát hiện 3: ADDRESSED (test khớp nguyên câu lệnh push của `branch_note` và `core_warning`, `return` có escape, đúng 2 `lines.push(`; chú thích bị bỏ trước khi so)
- Minor vòng 1: làm cả 4
- Phát hiện mới: không có blocker/major; minor: `_statement` đổi khoảng trắng trong chuỗi thành `\s+`; `_without_comments` chỉ bảo vệ chuỗi nháy kép

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: `AssertionError: form script missing: erp_ai_change_proposal.js`, `Ran 23 tests in 18.740s` / `FAILED (failures=1)`; GREEN: `Ran 23 tests in 18.334s` / `OK`
- Vòng 2 RED: `Ran 23 tests in 17.789s` / `FAILED (failures=3)`; mutation (bỏ `lines.push(branch_note)`): `FAIL: … (rule='approve confirmation repeats branch line and core warning, escaped') AssertionError: Regex didn't match: 'const\\s+branch_note…`; GREEN: `Ran 23 tests in 17.897s` / `OK`; lint (prettier, eslint, ruff) sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Form hiện thật trên trình duyệt (màu intro, bấm "Không" không gửi request, Administrator bấm nhận 403): `ui: false`, bước tay ghi ở `dev-notes.md`, người kiểm sau G4 (qa ghi vào `acceptance.md`).
- `cmd.test` sau merge: xem tasks.md.

## deferred
- Designer: design 3.3 chưa có chữ của các hộp thoại xác nhận; dev tự viết, cần người xác nhận câu chữ.
