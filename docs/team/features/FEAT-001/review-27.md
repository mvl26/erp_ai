# Review 27 — FEAT-001 T18 (cổng: dò khóa và dò lại khóa hết hạn mức)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 0718c42..team/FEAT-001-task-18` (head ede7983); merge 3f63ec7
- Bằng chứng dev: RED 13 lỗi (AttributeError thiếu hàm; dev viết mã trước rồi hoàn tác để có đỏ, không test-first đúng nghĩa; reviewer xác nhận test ghim hành vi); GREEN test_gateway Ran 60 OK; mọi đột biến một nhánh đều đỏ
- Sau merge (cây e267dab = cây gồm T16, T17, T18, T24, T20c): `--app erp_ai` Ran 262 tests OK hai lần liên tiếp, 0 lỗi (dev T20c chạy trên site miyano)

## Findings
Không có blocker/major.

## Deferred
- T35: wrapper scheduler không gửi thông báo hồi phục lần nữa (gateway đã gửi), chỉ commit sau khi dò.
- T36: `check_keys` hiển thị có ý nghĩa `not_found`, `no_secret`; design 3.4.1 cần liệt kê hai kind này (asbuilt).
- minor: test thứ tự idx của reprobe đỏ theo may rủi (modified trùng); khối "gửi tin, ghi log khi lỗi" lặp 3 lần; khóa bị tạm nghỉ do token thấp vẫn nhận tin "dùng lại được".
