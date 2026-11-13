# Review 39 — FEAT-001 T38 (Eval: chạy phân loại bằng chính prompt của runner)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff 609c12d..team/FEAT-001-task-38` (head b542d64; vòng 2: `git diff 86b360c..team/FEAT-001-task-38`)

## Vòng 1 (review-raw-T38.md)
- major STD-TEST-5: test ánh xạ từ Setting đối xứng, bỏ qua Setting vẫn xanh.
- minor: số dòng khi JSON hỏng (STD-ERR-2); cảnh báo log tiêu đề phiếu (STD-ERR-4/SEC-6); import trùng kiểu (STD-STYLE-4).
- Hướng import `eval -> agent.runner` được ADR-001 cho phép; T40 `test_layer_imports` không được cấm hướng này.

## Vòng 2
Tất cả ADDRESSED (2 hàng Custom A + 1 hàng mặc định, khẳng định (2,1) và (1,2) sau khi xóa mapping; mutation bỏ Setting -> `(1, 2) != (2, 1)`). Không finding mới.

## Bằng chứng dev
Vòng 1: RED (stub rỗng, 6 test đỏ đúng lý do) -> GREEN 12 OK, test_runner 30 OK; mutation từng guard đỏ. Vòng 2: Ran 13 tests OK; Error Log 196 trước = sau; pre-commit chạy ở bước cmd.test tổng.

## Deferred
- Nợ: chuyển `CLASSIFY_MAX_TOKENS` ra `constants.py`/`prompts.py` để eval không nạp cả runner (ngoài touchpoint T38).
- Khóa `_line` thêm vào mỗi dòng dữ liệu: bỏ nếu sau này ghi ngược ra file.
- Không `deadline` cho cả lần chạy eval; báo cáo không phân biệt lỗi cổng với phân loại sai (câu hỏi thiết kế, design 3.7).
