Feature: FEAT-004
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:

# Phụ lục design 4 — làm sạch dòng git trước khi lưu `failure_reason` (review-45 deferred)

Theo ADR-022 (Ràng buộc "không trường nào lưu URL", NFR-8), ADR-013 QĐ 7 (đầu ra lệnh), ADR-012 QĐ 7 (nhật ký). Không đổi kiến trúc, không thêm touchpoint, không thêm file mã.
Cơ sở khảo sát (đọc trực tiếp worktree feat-004, 2026-11-14): `apply_job.py:242-246` `_commit_failed_reason` lấy dòng cuối không rỗng, cắt 120, không làm sạch; lý do này vào `failure_reason` và `error` của nhật ký (`transitions.py:266,276`); `process_runner.py:16,33-41` giữ ≤ 20 dòng gộp stdout+stderr. Không có helper che chung: chỉ có `change_text.safe_person_name` (thay cả chuỗi khi gặp `@`/`://`) và `source.py:569` (che upstream); cả hai không dùng được nguyên cho một dòng tự do, nên dùng lại đúng tiêu chí `@`/`://` của chúng.

## QĐ-D1. Lưu gì
- Chỉ dòng cuối không rỗng của `CommandResult.output` (stdout+stderr đã gộp); không lưu dòng nào khác, không lưu `output` lên đề xuất (giữ design 3.5 dòng 468).
- Làm sạch theo thứ tự: (1) ký tự điều khiển Unicode `Cc` → khoảng trắng, gộp khoảng trắng; (2) tách theo khoảng trắng, mỗi từ bị thay bằng `…` khi chứa một trong `/` `\` `@` `=` `~`, hoặc có một đoạn liền `[A-Za-z0-9_+-]` dài ≥ 20 ký tự (dạng khóa/token/mã băm); (3) nối lại bằng một khoảng trắng; (4) SAU khi che mới cắt còn ≤ 120 ký tự (che trước cắt để không lộ nửa đầu một token nằm vắt qua ký tự 120).
- Kết quả rỗng sau làm sạch → chỉ câu `GIT_COMMIT_FAILED`[ ` (quá thời gian)`], không có `: `.
- Hệ quả: đường dẫn tuyệt đối/tương đối (kể cả `'/…/.git/index.lock'`), URL (có hay không token), email, `key=value`, `~/…` và chuỗi dạng khóa không bao giờ tới `failure_reason` hay `error` của nhật ký. Từ thường (`fatal:`, `error:`, tiếng Việt) giữ nguyên.

## QĐ-D2. Chỗ đặt
- Một hàm thuần `_git_short_line(output: str) -> str` trong `erp_ai/agent/changes/apply_job.py`, cạnh `_commit_failed_reason`; `_commit_failed_reason` gọi nó thay cho dòng 245-246. Hằng cùng file: `GIT_MASKED_WORD = "…"`, `GIT_KEY_LIKE = re.compile(r"[A-Za-z0-9_+\-]{20,}")`, giữ `GIT_SHORT_REASON_MAX_CHARS = 120`. Không đặt trong `process_runner` (module chỉ chạy tiến trình, ADR-013 QĐ 3) hay `change_text` (ngoài touchpoint của task mang).
- Áp cho cả commit áp dụng và commit hoàn tác (mọi chỗ gọi `_commit_failed_reason`).

## Design được sửa
- 3.5 dòng 468: thêm "dòng cuối được làm sạch theo phụ lục 4 QĐ-D1 bằng `_git_short_line` trước khi cắt 120".
- Bảng lỗi git 3.2 (dòng 352-368): `GIT_COMMIT_FAILED` "+ lý do ngắn đã làm sạch (phụ lục 4)". Câu hợp đồng không đổi.
- 8.x test plan: thêm 3 dòng dưới đây cho NFR-8 / AC-13.

## Task và file
- **T47** (đang mở, chuỗi `apply_job.py`) mang việc này; files không đổi: `erp_ai/agent/changes/apply_job.py`, `erp_ai/agent/changes/test_apply_job.py`. Tech-lead thêm vào Returns/Expect của T47; không cần `/team:plan --insert`. File mới: 0 (so `allowed_new_file_roots`: không có đường dẫn mới; `protected_paths`: 0 trùng).
- STD-TEST-5 được phép đổi: `test_long_git_output_gives_a_short_reason` (`test_apply_job.py:722-731`) đổi đầu vào `"e" * 300` (nay bị che vì dạng khóa) thành từ thường lặp, ví dụ `"lỗi " * 80`; kỳ vọng = 120 ký tự đầu sau gộp khoảng trắng.

## Test thêm (trong `erp_ai/agent/changes/test_apply_job.py`)
- `test_git_short_line_masks_paths_urls_emails_and_key_like_words`: subTest từng dòng: `fatal: Unable to create '/home/u/bench/apps/x/.git/index.lock': File exists.`, `https://x-token-FAKE@host/r.git`, `real.person@example.com`, `token=abc`, `~/x`, `C:\x`, chuỗi 40 ký tự `[A-Za-z0-9]` → mỗi chuỗi nhạy cảm xuất hiện 0 lần, có `…`, từ `fatal:`/`File exists.` còn.
- `test_git_short_line_masks_before_cut_and_drops_control_chars`: token giả bắt đầu ở ký tự 110 → 0 ký tự của token trong kết quả; `\x1b[31m`, `\r`, `\t` → khoảng trắng; dòng chỉ gồm từ bị che + rỗng → `""`; độ dài ≤ 120.
- `test_commit_failed_reason_stores_no_path_or_secret` (integration, subTest áp dụng và hoàn tác): stub `git_commit_only` thoát 1 với đầu ra chứa đường dẫn repo thật của `GitSandbox`, URL token giả và email mẫu → `failure_reason` và `error` của mọi dòng nhật ký chứa 0 lần mỗi chuỗi; `failure_reason` bắt đầu bằng câu `GIT_COMMIT_FAILED`; `command_output` rỗng; kiểm trước rằng chính đầu ra stub có chứa các chuỗi đó (phép kiểm rò rỉ đọc kho không rỗng).
