# Review T3 (FEAT-001)

Verdict: approve (round 2; 1 vòng rework)
Diff: `git diff a351af1..team/FEAT-001-task-3` (head 423f698); vòng 2: `git diff fb3be74..team/FEAT-001-task-3`.
Vòng 1 request-changes: major STD-DESIGN-5 prompts.py:52,149 (dev tự đổi `[GẬP]` thành `[GẤP]` trong prompt, lệch design 3.3 và đo eval). Ruling tech-lead: khôi phục nguyên văn guide; resolver vẫn nhận cả hai cách viết. Vòng 2: ADDRESSED (so khớp byte với guide, test không còn khóa `[GẤP]`).
minor | — | — | điểm nhỏ còn lại (tiêu đề phụ trong bảng prompt, test B–E của D-8 chưa khẳng định, test đặt nhầm lớp) | dev's call (deferred)
deferred: `_mapping_error` chỉ bắt ValueError (RecursionError từ cấu hình admin lồng sâu); `load_mapping` trả `{}` không nêu lý do, runner (T28) phải gọi `validate_mapping`; `resolve_ticket_values` trả "" cho giá trị rỗng của D-8 (writer T25 coi "" là không ghi); T9 phải đặt mặc định `category_mapping` = JSON của `DEFAULT_CATEGORY_MAPPING`.
Ghi nhận cho người: guide/spec viết `[GẬP]`, tiếng Việt đúng có thể là `[GẤP]`; chưa đổi vì đổi prompt ảnh hưởng phép đo NFR-9.
Bằng chứng dev: vòng 1 RED 26 lỗi/fail (stub) GREEN 29 test, `--app erp_ai` 35 OK; vòng 2 RED (RecursionError, `[GẬP]` không thấy) GREEN 30 test, pre-commit exit 0.
