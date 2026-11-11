# Review T7 (FEAT-001)

Verdict: approve (round 3; 2 vòng rework)
Diff: `git diff 212f77b..team/FEAT-001-task-7` (head 12229e3).
Vòng 1 request-changes: blocker STD-SEC-3 source.py:186 (blame chấp nhận tên dài viết tắt như `--cont=` nên `--contents` lọt qua kiểm `startswith`, đọc được common_site_config.json); major STD-SEC-3 (giá trị đính kèm tùy chọn không qua kiểm đường dẫn); major STD-TEST-8 (không có test cho hai trường hợp trên). Sửa: thay danh sách cấm bằng danh sách cho phép khớp đúng tên (GIT_ALLOWED_FLAGS + `-n<số>`), đóng stdin, không trả stderr của git.
Vòng 2 request-changes: major STD-TEST-8 test_source.py:265-277 (test không ghim khớp đúng tên; thay bằng startswith vẫn xanh). Sửa: thêm `-pS../../outside/x`, `-nS../../outside/x`, `-wO../../outside/x`, `-pw`, và test ẩn stderr; RED chứng minh bằng cách tạm nới thành startswith. Vòng 3: ADDRESSED, không còn blocker/major.
minor | — | — | `_git_repo` kiểm os.sep và ./.. chưa có test; capture_output giữ toàn bộ stdout trong bộ nhớ trước khi cắt 8000 ký tự; assert_called_once cho test stderr | dev's call (deferred)
deferred / cần người quyết (design 5.4): (1) design chưa nêu `-S`, `--ignore-revs-file` của blame, nay bị chặn bởi allowlist; nên cập nhật design theo allowlist. (2) Đầu ra git có thể lộ bí mật đã commit: `git show HEAD`/`log -p` không pathspec, pathspec glob như `*.pe[m]`, `git show <blob-sha>`; kiểm tên bí mật AC-13 không thực sự phủ git. Cần quy tắc ở design hoặc chấp nhận rủi ro. (3) blame vẫn áp textconv của cấu hình repo (không bị tham số bật được). (4) Xác nhận `git --version` trên máy chủ (hành vi parse-options giả định git >= 2.2x).
Bằng chứng dev: RED các vòng (6 fail bằng stub; `--cont=` được chấp nhận; startswith nới lỏng làm test đỏ), GREEN Ran 23 tests OK, pre-commit exit 0.
