# git_no_hooks

Thư mục này là `core.hooksPath` của mọi lệnh git do FEAT-004 chạy (`source.GIT_HOOKS_DIR`,
`source.git_global_options`; ADR-022 QĐ 4, D-13). Vì thư mục không có hook nào, hook của repo app
đích (pre-commit, commit-msg, post-commit, reference-transaction...) không bao giờ chạy khi agent
đọc trạng thái git hoặc commit một thay đổi đã duyệt.

Git không giữ thư mục rỗng, nên tệp `README.md` này là tệp duy nhất được phép ở đây.
Không thêm tệp nào khác vào thư mục này: một tệp mang tên hook sẽ chạy trong mọi repo app.
`test_source.py::test_hooks_dir_has_no_hook_files` kiểm điều đó.
