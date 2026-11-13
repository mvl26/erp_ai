Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 35 — FEAT-004 T35

- Diff: `git diff cb40420..team/FEAT-004-task-35b` (2 commit `587e780`, `9399efe`; 1 file `dev-notes-git.md`, +134)
- Vòng: 1 (trước review có một lần sửa do tech-lead yêu cầu: che tên/email thật, STD-SEC-6)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: `dev-notes-git.md:24` chỉ liệt kê `hookspath`, `gpgsign`, `user.*` của cấu hình git chung, không phải toàn bộ khóa (vd `init.templateDir`); commit `587e780` còn giữ tên/email trong nội dung file (cùng danh tính với trường tác giả của commit) | tùy dev

## Review checklist (10)
1–2 đạt; 3 không áp dụng (bước kiểm có đầu ra, có thể sai); 4 đạt; 5, 7 không áp dụng; 6, 8–10 đạt.

## Bằng chứng của dev (bước kiểm, không có RED/GREEN)
- Sau `rm new.txt` và `commit --only --no-gpg-sign --quiet -m .. -m .. -- new.txt`: `show --stat`: `new.txt | 1 -`, `1 file changed, 1 deletion(-)`; `ls-tree HEAD`: chỉ `keep.txt`, `other.txt`; `diff --cached --name-only`: `keep.txt`; `status --porcelain`: `M  keep.txt` / ` M other.txt`; git 2.43.0 → D-18 đạt
- Lần gọi dev 1: BLOCKED (hook worktree chặn lệnh git có tiền tố `GIT_CONFIG_GLOBAL=` và script nhiều bước); lần 2 dùng `git -C <thư mục tạm>` từng lệnh, danh tính test đặt trong repo tạm; lệch so với task đã ghi trong ghi chú

## Không kiểm được từ diff (tech-lead xử lý)
- Đầu ra thật nằm ở thư mục tạm đã xóa: chấp nhận vì khớp báo cáo dev từng dòng; `test_undo_new_file_removes_from_disk_and_tree` (T20) kiểm lại bằng `GitSandbox` với `GIT_CONFIG_GLOBAL=/dev/null`.
- Cách merge: giữ cả hai commit (merge thường); tên/email trong `587e780` trùng trường tác giả của mọi commit nên không lộ thêm gì; nhánh chưa push.

## deferred
- git của runner CI có thể khác 2.43.0: T20 kiểm lại trên runner.
