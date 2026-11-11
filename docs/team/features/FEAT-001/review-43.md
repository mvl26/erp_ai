# Review 43 — FEAT-001 T39 (Report ERP AI Accuracy)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff a947607..team/FEAT-001-task-39` (head 14330fd; vòng 2: `git diff 1b69de0..team/FEAT-001-task-39`)

## Vòng 1 (review-raw-T39.md)
- major STD-TEST-5: test chuẩn hóa rỗng so None với None nên bỏ `or ""` vẫn xanh.
- minor: thiếu ca biên pending đúng now-7d; dòng `has_permission` yếu; patch `log_error` thừa.
- Diễn giải (1) của dev được chấp nhận: `data == []` chỉ khi khoảng ngày không có dự đoán nào; còn lại hàng có mẫu 0 hiện `accuracy_pct = None` (design 2.5 vs 3.8, câu hỏi cho designer).

## Vòng 2
Tất cả ADDRESSED (hai subTest "" vs None và None vs ""; dev chạy mutation bỏ `or ""` -> cả hai đỏ; thêm test biên đúng 7 ngày với `now_datetime` được vá; bỏ dòng yếu và patch thừa). Không finding mới ở mức blocker/major.

## Bằng chứng dev
Vòng 1: RED (stub rỗng, 8 failure + 6 error đúng lý do) -> GREEN 12 OK; migrate exit 0; 11 mutation đều đỏ; Report "ERP AI Accuracy" được migrate tạo (bản ghi mới tất yếu). Vòng 2: Ran 13 tests OK; pre-commit pass; đếm 4/3/8/0/198 trước = sau. Error Log +1 ở vòng 1 do migrate.

## Deferred
- minor: `self._log("B", 7, corrected_after=None)` không được assert; đặt lại `entry_type` nên vào addCleanup/finally.
- Test biên `>` vs `>=` chưa được dev chạy mutation (reviewer đọc test thấy có thể đỏ).
- Câu hỏi thiết kế: `human_corrected_to` không parse được khi cả ba trường dự đoán rỗng; sửa lần đầu trong 7 ngày rồi sửa về đúng giá trị dự đoán tính là "không sửa".
- Test `test_report_record_*` phụ thuộc migrate đã chạy trên site.
