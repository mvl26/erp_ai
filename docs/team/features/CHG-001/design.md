Feature: CHG-001
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Design CHG-001 — Comment kết quả của đề xuất (AC-28) và bảng truy vết M1–M5

## 1. Bối cảnh
- Phạm vi: chỉ phần còn thiếu thiết kế của CHG-001 là AC-28 (FEAT-004 spec N-7): sau mỗi kết cục áp dụng / lỗi / hết hiệu lực / hoàn tác có 1 comment trên phiếu nói trạng thái cuối, không URL remote, khóa, token (NFR-5, NFR-8). M1–M5 đã có task (bảng cuối). T56, T57 bị đỗ ở round 66 vì: `HD Ticket.new_comment` từ chối người không phải agent Helpdesk; comment `Comment` dưới phiên người duyệt đi qua phép kiểm từ khóa (`handlers.py:111`) và bị `authority` coi là "chỉ thị"; `frappe.set_user` trong `changes/` trái Ràng buộc ADR-013.
- Luật phải giữ: ADR-013 QĐ 1 và Ràng buộc (job chạy dưới user đã duyệt, không `set_user`, không phát realtime), ADR-023 QĐ 2 (M2) và QĐ 5 (M5), ADR-012 QĐ 5 (chữ không bao giờ là duyệt), ADR-010 QĐ 3 và ADR-017 (tác giả comment = `owner`, không đọc trường do client đặt; luật `check_no_legacy_ticket_comment` cấm `comment_email`/`comment_by`), ADR-004 QĐ 1, 4 và Ràng buộc (`ignore_permissions=True` chỉ ở 4 nơi).
- Căn cứ (đọc trực tiếp, không qua Explore, đích đã biết): `apply_job.py:84-173`, `propose_change.py:102-122`, `handlers.py:100-120`, `authority.py:18-41`, `agent_write_guard.py`; Frappe 15 `model/document.py:1608-1629` (`add_comment` dùng `ignore_permissions` của framework), `core/doctype/comment/comment.py:59-104` (realtime chỉ cho `Comment`/`Like`/`Assigned`/`Attachment`, không cho `Info`), `desk/form/load.py:167-178` và `desk/form/activity.py:302-304` (dòng `Info` vào dòng thời gian, hiện "<họ tên owner> <chữ>"); Helpdesk `extends/comment.py:15-22` (chốt `is_agent` chỉ cho `comment_type == "Comment"`), `api/tags.py:96` (Helpdesk tự ghi dòng `Info`), `TicketTimeline.vue:318` (vẽ dòng subtype `info`).

## Quyết định
**Ai ghi, từ đâu:** module mới `erp_ai/agent/changes/result_comment.py`; được gọi đúng một chỗ, `apply_job.run_change`, ngay sau `_locked_run` trả trạng thái cuối (đã commit), khi kết cục khác `OUTCOME_SKIPPED`.
**Dưới tài khoản nào:** user phiên của job, tức người đã duyệt/hoàn tác (`decided_by`/`undo_by`, M2 đã kiểm trùng); không `set_user`, không đổi `owner`.
**Dạng comment:** một bản ghi core `Comment` với `comment_type = "Info"` trên `HD Ticket`, ghi bằng `frappe.get_doc("HD Ticket", ticket).add_comment("Info", text)` — cùng cách Helpdesk ghi dòng đổi tag. Nhờ `Info`: (a) `handlers.comment_after_insert` trả về ở bước 0 (`comment_type != "Comment"`) → 0 job agent, 0 đọc DB; (b) `authority.ticket_comment_filters` chỉ lấy `Comment` → dòng kết quả không bao giờ vào prompt, không được gắn "chỉ thị", không thành `latest_instructor`; (c) `Comment.notify_change` bỏ qua `Info` → 0 `publish_realtime`; (d) chốt `is_agent` của Helpdesk không áp → người duyệt không cần là agent Helpdesk. Không sửa `handlers.py`, `authority.py`, ADR nào.

## Assumptions decided by the team
- **A-D1 `Info` thay `Comment`.** chọn: dòng hoạt động `Info` | vì: là cách duy nhất trong ADR hiện có vừa không kích hoạt agent, vừa không thành "chỉ thị" của người duyệt (tránh nâng thẩm quyền cho lần chạy sau, AC-11), vừa không `set_user` | phương án khác: `Comment` + đánh dấu bằng `comment_email` (trái ADR-017 và luật legacy), `Comment` + đổi `owner` sang tài khoản agent (lách ADR-013 QĐ 1, trái ADR-010 "chỉ `post_comment` tạo comment owner agent") | sai thì (qa thấy dòng không hiện trên trang phiếu Helpdesk thật): team-leader → architect chọn giữa ADR mới cho cách đánh dấu comment hệ thống, hoặc người đồng ý bỏ AC-28 theo thứ tự N-7.
- **A-D2 ADR-004.** Dòng "HD Ticket Comment" của bảng chủ ghi và QĐ 4 (L0) nói về comment `Comment` của agent (ADR-010 dòng 86); dòng `Info` là nhật ký hoạt động như Frappe/Helpdesk tự ghi, không đi qua mức L0–L3. Mã của app không viết `ignore_permissions`; quyền đã kiểm ở `_decider` và ở M2. Sai thì: architect ghi một dòng vào bảng chủ ghi.
- **A-D3 NFR-8.** `owner`/`comment_email` của dòng là email người duyệt như mọi dòng hoạt động người tạo; NFR-8 áp cho chữ của comment: chữ không chứa email, URL, token.

## 2. Mô hình dữ liệu
Không thực thể, trường hay option mới. Ghi thêm 1 dòng `Comment` (`comment_type="Info"`, `reference_doctype="HD Ticket"`, `reference_name=<ticket của đề xuất>`, `content=<chữ đã escape>`) mỗi kết cục. Đọc từ đề xuất: `name`, `ticket`, `change_status`, `change_kind`, `is_new_file`, `file_path`, `command_args`, `failure_reason`, `apply_commit_sha`, `undo_commit_sha`, `exit_code`, `undo_by`. Không đọc `command_output`, `diff`, nội dung file.

## 3. API / hợp đồng
- `result_comment.result_lines(fields: dict) -> list[str]` (thuần, không I/O). Dòng 1: `kết quả đề xuất {name} ({đích}): {change_status}` với đích = `sửa {file_path}` / `tạo {file_path}` / `lệnh bench {args}`. Dòng 2 theo trạng thái cuối:
  | Trạng thái | Dòng 2 |
  |---|---|
  | `Đã áp dụng`, code | `commit {apply_commit_sha[:12]}` |
  | `Đã áp dụng`, lệnh | `mã thoát {exit_code}` |
  | `Lỗi` | `lý do: {lý do đã che}`; có `exit_code` thì thêm `mã thoát N`; có `undo_by` thì mở đầu `khi hoàn tác, ` |
  | `Hết hiệu lực` | `lý do: {lý do đã che}` |
  | `Đã hoàn tác` | `commit hoàn tác {undo_commit_sha[:12]}` |
  Che lý do: gộp khoảng trắng, cắt 300 ký tự, mỗi từ chứa `://` hoặc `@` → `[đã ẩn]`. Trạng thái khác 5 trạng thái trên → `ValueError`.
- `result_comment.post_result(proposal_name: str) -> str | None`: đọc trường bằng `frappe.db.get_value(..., as_dict=True)`; không có đề xuất, không có `ticket`, hoặc phiếu không còn (`frappe.db.exists`) → `None`, không ghi. Ngược lại nối `result_lines` bằng `"; "`, `frappe.utils.escape_html`, gọi `add_comment("Info", …)`, trả tên `Comment`. Không commit, không bắt lỗi (người gọi xử lý). Hằng: `COMMENT_TYPE_INFO = "Info"`, `TITLE_RESULT_COMMENT_FAILED = "erp_ai: ghi kết quả đề xuất lên phiếu lỗi"`.
- Không import `apply_job`, `handlers`, `authority`, runner; không `new_comment`, `set_user`, `publish_realtime`, `allow_agent_write`.
- Không đổi hợp đồng công khai nào: không whitelist mới, không breaking change.

## 4. Luồng
1. `run_change` → `_locked_run` → trạng thái cuối đã `frappe.db.commit()` (đường khóa hết giờ `:121-126`, đường thường `:172`).
2. `outcome != OUTCOME_SKIPPED` → `name = result_comment.post_result(proposal_name)`; thành công → `frappe.db.commit()`.
3. Lỗi bất kỳ ở bước 2 → `frappe.db.rollback()` (chỉ mất phần comment chưa commit; trạng thái cuối đã commit ở bước 1), `frappe.log_error(TITLE_RESULT_COMMENT_FAILED, f"proposal={name} action={action} error={type(exc).__name__}")`, job đi tiếp, không ném lại (STD-ERR-1: lý do ghi ở chú thích ngay chỗ bắt).
4. Dòng `logger.info` hiện có thêm `comment=<tên>|-|error` (STD-OPS-5). `OUTCOME_SKIPPED` → không gọi, `comment=-`.
Không lời gọi ra ngoài, không timeout mới.

## 5. Quyền
Không kiểm quyền mới: ai được duyệt/hoàn tác đã kiểm ở `_decider` (ADR-012 QĐ 4) và lại ở đầu job (M2). Dòng `Info` mang tên người thực hiện thật. M5 không bị chạm (`Comment` không thuộc module app; phiên không phải tài khoản agent). Chữ comment chỉ dựng ở server từ trường của đề xuất, escape trước khi lưu; `Comment.validate` còn `sanitize_html`.

## 6. Migration và rollback
- Lên / Xuống: không có (không đổi schema, không dữ liệu cũ).
- Rollback mã: revert commit của T56/T57; các dòng `Info` đã ghi giữ làm lịch sử, vô hại. Đối soát: số đề xuất theo trạng thái trước = sau `cmd.test`.

## 7. Touchpoints
| file | change | ghi chú |
|---|---|---|
| erp_ai/agent/changes/result_comment.py | mới | dựng chữ, ghi dòng `Info` |
| erp_ai/agent/changes/test_result_comment.py | mới | test module trên |
| erp_ai/agent/changes/apply_job.py | sửa | `run_change`: gọi `post_result`, bắt lỗi, thêm `comment=` vào dòng log |
| erp_ai/agent/changes/test_apply_job.py | sửa | test mỗi kết cục |
Đối chiếu đường mới: `erp_ai/agent/changes/result_comment.py` ↔ `erp_ai`; `erp_ai/agent/changes/test_result_comment.py` ↔ `erp_ai` (tests `colocated`, tên `test_{name}.py`). 0 trong `protected_paths` (`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`). Không chạm `handlers.py`, `authority.py`, `constants.py`, `test_architecture.py` (luật `check_changes_never_set_user_or_publish`, `LAYER_RULES` đã phủ file mới).

## 8. Test plan
| Tiêu chí | Test | Loại / nhánh lỗi-biên |
|---|---|---|
| AC-28 nội dung | erp_ai/agent/changes/test_result_comment.py::test_lines_for_each_final_status | unit; subTest 5 trạng thái + `Lỗi` khi hoàn tác + `Lỗi` lệnh có mã thoát; trạng thái lạ → `ValueError` |
| AC-28, NFR-5, NFR-8 | test_result_comment.py::test_reason_with_url_email_or_token_is_masked | unit; gieo `https://x-token-FAKE@host/repo`, `real.person@example.com` → 0 lần; lý do 1.000 ký tự → ≤ 300 |
| AC-28 ghi | test_result_comment.py::test_post_result_writes_one_info_activity_as_session_user | integration; +1 `Comment` `Info` trên phiếu, `owner` = user phiên, `content` đã escape (`<b>` trong đường dẫn) |
| AC-28, AC-11 | test_result_comment.py::test_result_activity_enqueues_no_agent_run_and_is_not_an_instruction | integration; dưới người có `ERP AI Instructor`, nội dung chứa từ khóa kích hoạt → 0 job agent; `fetch_ticket_comments` không có dòng đó; `latest_instructor` = `None` |
| ADR-013 QĐ 1 | test_result_comment.py::test_post_result_publishes_no_realtime | unit; stub `frappe.publish_realtime` đếm 0 |
| AC-28 biên | test_result_comment.py::test_post_result_without_ticket_or_deleted_ticket_returns_none | integration; 0 `Comment` mới |
| AC-28 mỗi kết cục | erp_ai/agent/changes/test_apply_job.py::test_one_result_comment_per_outcome | integration trên `GitSandbox`; subTest: áp dụng code, lệnh mã ≠ 0, hết hiệu lực do đổi nhánh, hoàn tác, khóa hết giờ, sai người chạy job → mỗi ca đúng +1 dòng `Info` |
| AC-28 biên | test_apply_job.py::test_skipped_job_posts_nothing | integration; job lặp → 0 dòng |
| STD-ERR-1 | test_apply_job.py::test_comment_failure_keeps_final_status_and_logs | integration; `post_result` ném → trạng thái cuối giữ, 1 `Error Log` tiêu đề `TITLE_RESULT_COMMENT_FAILED`, log `comment=error` |
| NFR-8 | test_apply_job.py::test_result_comment_has_no_remote_url_or_fake_token | integration; URL remote có token giả → 0 lần trong dòng `Info` |
qa thêm (sau G4, ghi ở As-Built): mở trang phiếu Helpdesk thật sau một lần duyệt, thấy dòng kết quả (A-D1).

## Truy vết CHG-001 → task FEAT-004
| Mục | Task | Mục | Task |
|---|---|---|---|
| M1 | T53, T54, T68 | AC-24 | T53 |
| M2 | T55 | AC-25, AC-26 | T54 |
| M3 | T59, T60, T68 | AC-27 | T58 |
| M4 | T63, T68 | AC-28 | T56, T57 (+T48 kiểm chéo NFR-8) |
| M5 | T65, T66, T67, T68 | AC-29, AC-34 | mã nhận về (plan dòng 237); AC-34 thêm T64 |
| AC-30 | T60 | AC-31 | T59, T60 |
| AC-32 | T63 | AC-33 | T59, T61, T65, T66, T67 |
| AC-35 | T62, T64 | | |
Chữ T56/T57 cần sửa (việc của tech-lead): `post_result(proposal_name)` thay `post_result(proposal)`; ghi bằng `add_comment("Info", …)` không qua `new_comment`; Receives thêm `is_new_file`, `file_path`, `command_args`, `undo_by`; tên test theo mục 8.
