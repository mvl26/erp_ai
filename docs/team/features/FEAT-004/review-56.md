Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 56 — FEAT-004 T56

- Diff: `git diff ab802fe..b792fb8` (nhánh `team/FEAT-004-task-56`, 1 commit `feat(changes): result line of a change proposal as one Info activity on its ticket (FEAT-004)`, 2 file mới, +450; đã merge `7724fca`, nhánh đã xóa)
- Vòng: 1
- Verdict: approve

Tech-lead chép từ tin trả về của reviewer. Lệnh reviewer đã chạy (chỉ đọc):

```
git log --oneline ab802fe..team/FEAT-004-task-56
git diff --stat ab802fe..team/FEAT-004-task-56
git diff ab802fe..team/FEAT-004-task-56
```

Bằng chứng của dev: RED `Ran 6 tests in 5.037s` / `FAILED (errors=31)`, `AttributeError: module 'erp_ai.agent.changes.result_comment' has no attribute 'post_result'`; GREEN test_result_comment `Ran 6 tests in 5.400s` / `OK`, test_architecture `Ran 177 tests in 20.369s` / `OK`. Không chạy lại trong review (site dùng chung).

## Lớp 1 — khớp spec

- Đủ design CHG-001 mục 2, 3, 8, không thêm gì: đọc đúng 12 trường, không đọc `diff`, `command_output`, nội dung file; hai hàm đúng chữ ký, hai hằng, `escape_html`, `add_comment("Info", …)`, ba ca trả `None`; không commit, không bắt lỗi; không `set_user`, `publish_realtime`, `ignore_permissions`, `new_comment`; không import cấm.
- Touchpoints: đúng hai file, đúng chỗ, đúng tên.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 3 điểm nhỏ: (1) STD-DOC-7 `result_comment.py:4`: docstring module còn chữ "publishes no realtime event", lệch với phán round 81 và test `:265`; (2) STD-TEST-8 `result_comment.py:97`: phép kiểm `not fields.ticket` không bao giờ đổi kết quả (`frappe.db.exists("HD Ticket", "")` đã trả `None`); (3) STD-TEST-6 `test_result_comment.py:290`: test đếm mọi `Comment` của site, nên lọc theo `reference_name` | tùy dev

## Đánh giá test

- Mỗi trạng thái cuối một ca (code/lệnh, mã thoát chỉ hiện khi ≠ 0, tiền tố "khi hoàn tác", cắt 12 ký tự commit); 5 trạng thái chưa cuối, `""`, `None` → `ValueError`.
- Luật che (STD-TEST-8): URL không `@` chỉ `://` bắt; email chỉ `@` bắt; gộp khoảng trắng, cắt 300 (1.000 → 300, đúng 300 giữ nguyên), "gộp trước cắt", "che trước cắt" (email nằm vắt qua chỗ cắt) mỗi luật một ca.
- STD-SEC-4: che được kiểm trên `Comment.content` đã lưu.
- Escape: `<b>` trong đường dẫn kiểm trên dòng đã lưu.
- "Không phải chỉ thị": cùng chữ đó ghi bằng `Comment` thật của cùng người hướng dẫn thì khởi động 1 lần chạy và thành `latest_instructor`; nên số 0 của dòng `Info` đến từ kiểu dòng, không từ cách dựng test.
- Realtime: test đòi đúng `[doc_update Comment, list_update]`; một `Like` trong cùng test phát `docinfo_update`, chứng minh stub bắt được.

## Phán round 81 của tech-lead (realtime)

Không trái ADR-013, không phải design-defect: dòng 55 cấm lời gọi `publish_realtime` viết trong `changes/**`; dòng 30 cấm tín hiệu trạng thái agent (ADR-008). `doc_update`/`list_update` do `Document.notify_update` của Frappe phát cho mọi lần insert (`model/document.py:1375-1385`); `Comment.notify_change` trả về sớm với `Info`.

## Review checklist (10)

1–2 đạt (spec, touchpoints). 3–4 đạt (RED → GREEN, biên, không skip/xfail, chỉ test mới). 5 đạt (lỗi đi lên người gọi, có test ghim). 6 đạt (không tiêm: tham số lệnh lấy từ allow-list `change_guard.BENCH_COMMANDS`; quyền kiểm trước, design mục 5). 7 đạt (không đổi hợp đồng). 8 đạt. 9 không có phụ thuộc mới. 10 đạt (commit đúng dạng, không dòng ghi công AI).

## Không kiểm được từ diff

- Chữ design mục 3 liệt kê gộp, cắt, che; mã che trước rồi cắt và test ghim thứ tự đó (thứ tự duy nhất không giữ lại nửa bí mật ở chỗ cắt). → tech-lead: giữ mã, ghi cho designer sửa chữ mục 3.
- Luật che chỉ bắt từ có `://` hoặc `@`; `failure_reason` do `apply_job` ghi có thể chứa token trần hay không nằm ngoài diff → T57 `test_result_comment_has_no_remote_url_or_fake_token` và T48 kiểm.
- Dòng `Info` có hiện trên trang phiếu Helpdesk thật không (A-D1): qa sau G4.
- Nối vào job: T57.
- Test: tech-lead chạy lại sau merge `7724fca`: test_result_comment `Ran 6 tests in 5.339s` / `OK`, test_architecture `Ran 177 tests in 20.447s` / `OK`.

## Deferred

- 3 điểm minor ở trên; chữ design CHG-001 mục 3 (thứ tự che/cắt) và mục 3(c), 8 ("0 `publish_realtime`") cần designer sửa.
