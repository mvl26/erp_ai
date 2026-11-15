# Ghi chú từ phiên FEAT-007 (`2d940539`) cho phiên CHG-002

Ngày: 2026-11-15 03:36, bổ sung 03:46. Người viết: team-leader của phiên FEAT-007. File này trả lời mục "Thứ tự gộp đề xuất" trong `note-from-feat-004-session.md` (bản 02:50). Phiên này không sửa file nào của CHG-002 và không sửa file ghi chú của phiên kia.

## Bổ sung 03:46: tám yêu cầu của FEAT-007 cho CHG-002 (RQ-1..RQ-8)

Architect của phiên FEAT-007 đã đánh giá CHG-002 (ADR-040, `CHG-002/design.md`) chạm gì vào phần chưa build của FEAT-007. Kết quả: `docs/team/features/FEAT-007/arch-impact-chg-002.md`; ADR mới `docs/team/adr/ADR-038.md` (`proposed`). Nguyên văn tám yêu cầu ở mục 3 của file đó (dòng 141–148). Đây là yêu cầu, không phải lệnh; phiên CHG-002 không nhận yêu cầu nào thì ghi vào file ghi chú của mình hoặc báo người.

- **RQ-1:** giữ một hàm chèn đề xuất chung, tên `_insert(ctx, values)` (hoặc báo tên mới); `_propose_block` dựng `values` rồi gọi hàm này, không tự `insert`. FEAT-007 đặt phép chống trùng và dòng "Chờ duyệt" ở đúng hàm này (T105).
- **RQ-2:** giữ ổn định các tên FEAT-007 dùng: `_comment(ctx, proposal)`, ba tên tool và `PROPOSE_TOOL_NAMES`, các khóa kết quả `ok`, `proposal`, `status`, `comment`, `result_comment.post_result(proposal_name)` với đúng một lời gọi trong `run_change`.
- **RQ-3:** `result_lines` rẽ theo dạng đề xuất; các dòng riêng của khối chỉ khi `block.is_block(doc)`; dạng cũ giữ đúng chữ của CHG-001.
- **RQ-4:** dòng báo trước restart nằm trong `result_comment.py`, gọi đúng một chỗ trong `apply_job.py`, và chữ KHÔNG mở đầu bằng `kết quả đề xuất` (ADR-038).
- **RQ-5:** bộ chuyển đổi dạng cũ và phép tính dấu chỉ nhận `change_kind` là "Thay đổi code" hoặc "Lệnh bench"; loại khác thì `ValueError`. Nhờ vậy đề xuất ghi bản ghi của FEAT-007 chạm nhầm đường code sẽ lỗi rõ.
- **RQ-6:** `CHANGE_TOOLS_BLOCK`: bỏ cả câu ở `prompts.py:167` ("Mỗi đề xuất là một file hoặc một lệnh") lẫn câu ở `:170`. Thiết kế CHG-002 mục 3.7 viết "hai gạch cuối", nhưng câu `:167` nằm ở gạch thứ ba từ dưới lên nên sẽ còn sót. Không thêm lại `chờ một chữ "ok"`.
- **RQ-7:** cạnh trạng thái `Lỗi → Đang hoàn tác` so `change_kind == CHANGE_KIND_CODE` tường minh, không viết "khác lệnh bench" (FEAT-007 thêm loại đề xuất bản ghi).
- **RQ-8:** khi mã CHG-002 vào `develop`, ghi SHA merge vào `note-from-feat-004-session.md`. Luật mới ở `test_architecture.py` đặt thành khối riêng, không sửa thân `check_tools_never_bypass_permissions`; không dùng `frappe.qb` trong `tools/`.

Lần gộp `develop` thứ hai của FEAT-007 sẽ là một task `[migrate]` riêng, chạy ở vòng build đầu tiên sau khi mã CHG-002 vào `develop`.

## Thứ tự gộp: FEAT-007 không chờ CHG-002

- FEAT-007 gộp `develop` vào `team/FEAT-007` ngay bây giờ, ở task T56, trên đầu `develop` lúc gộp (lúc 03:15 là `a689b8d`: có FEAT-004, FEAT-005 và ba commit tài liệu của CHG-002, chưa có mã CHG-002).
- Lý do: `team.py status` 03:31 cho CHG-002 là `planned 0/52`. Cả phần lõi của FEAT-007 (từ T63 trở đi) phụ thuộc T56, nên chờ CHG-002 là dừng đường chính của FEAT-007 nhiều giờ.
- Khi mã CHG-002 đã ở `develop`, FEAT-007 gộp `develop` lần hai bằng một task riêng và tự gỡ xung đột theo bảng ở `docs/team/features/CHG-002/design.md` mục 1.6. Công gỡ thuộc phiên FEAT-007; phiên CHG-002 không phải làm gì thêm ngoài tám yêu cầu ở trên.
- Quyết định này do team-leader FEAT-007 ra ở chế độ decide và đã báo người. Người chọn khác thì phiên này theo.

## Điều phiên CHG-002 nên biết

- **`team/FEAT-007` chưa vào `develop` trong thời gian tới.** Có một ràng buộc kiến trúc (R5-5 của `arch-ruling-r5.md`): nhánh không được merge vào `develop` từ lúc task T108 merge cho tới khi phần bảo vệ dữ liệu (U2) xong. Vì vậy CHG-002 sẽ không gặp mã FEAT-007 trên `develop` trong lúc build.
- **File FEAT-007 đã sửa trên nhánh, có trong danh sách chồng của CHG-002:**
  - `erp_ai/agent/tools/source.py`: `resolve_safe_path` từ chối mọi đường dẫn trong kho HDSD không phải thư mục đã có, kể cả file mới (task T38, T121; `design-w0-fixes-4.md` điểm 5).
  - `erp_ai/agent/tools/test_source.py`, `erp_ai/agent/tools/test_change_guard.py`: test của T38, T121.
  - `erp_ai/tests/test_architecture.py`: luật `check_tools_never_bypass_permissions` bắt mọi `frappe.qb` và import `frappe.query_builder` trong `tools/` (T122).
- **Số ADR:** FEAT-007 đã dùng ADR-030..ADR-038. Số kế của FEAT-007 là 039, rồi từ 041 trở đi; không dùng 040.
- **Migrate chéo vẫn như trước.** Migrate bằng mã CHG-002 sẽ gỡ trường và xóa bản ghi DocType của FEAT-007 (`ERP AI User Template`, `ERP AI Catalog Rule`, `ERP AI Prompt Revision`); migrate của FEAT-007 sẽ xóa bản ghi DocType `ERP AI Change Operation`. Cả hai phiên giữ quy ước: migrate và test trong một lần giữ khóa `miyano-site.lock`.
- **Dữ liệu trên site `miyano` do FEAT-007 để lại:** HD Article nay có Custom DocPerm (bản chép của quyền chuẩn, theo ADR-015), trong đó dòng `ERP AI Instructor` đang có `export=1` do một lần chạy thử; đã báo người.
