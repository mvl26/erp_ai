Feature: FEAT-004
Stage: architect
Author-agent: architect
Date: 2026-11-13

# Phán quyết: clean/smudge/process filter của repo khi `read_git_state` chạy `git status` (ADR-022 QĐ 4)

## Câu hỏi
Dev T38 (`18b5cff`, `erp_ai/agent/tools/source.py:528-537`): `git status` vẫn có thể chạy clean filter của chính repo đích; tùy chọn QĐ 4 (`git_global_options`, `git_env`) không tắt. (a) Có là đường chạy thật không? (b) Nếu có, chặn thế nào, task nào mang?

## Bằng chứng (git 2.43.0; repo tạm `/tmp/cf-probe.MrfntG`, đúng argv/env của `run_git_read`; script `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/6c38287b-bf21-45d8-bbe6-babd0767ec62/scratchpad/clean_filter_probe.sh`)
- Ca 1: chỉ `.gitattributes` `* filter=x`, không khai driver → không chạy gì; gitattributes(5): driver không khai trong config "makes the filter a no-op passthru".
- Ca 2: `filter.x.clean` trong `.git/config` của repo, file chỉ đổi mtime → `status --porcelain=v1 -z -- :(literal)f.txt` **chạy** filter (có tệp đánh dấu). Đường chạy là thật; QĐ 4 không phủ.
- Ca 3: thêm `-c filter.x.clean=` → không chạy, nhưng phải biết tên driver, tức phải đọc config (`config` bị cấm, QĐ 2).
- Ca 4/5: `--attr-source=<cây rỗng>` bỏ `.gitattributes` của worktree (ca 4 không chạy) nhưng `$GIT_DIR/info/attributes` vẫn áp dụng (ca 5 chạy) → không tắt chung được.
- Ca 6: clean filter đổi nội dung → `commit --only` lưu blob `Z` cho worktree `b`.
- Máy (đọc 2026-11-13): 12 repo dưới `apps/`, mọi `.git/config` chủ `miyano` mode 664; 0 khối `[filter`/`[include`; 0 dòng `filter=` trong `.gitattributes`/`.git/info/attributes`. Worker bench chạy bằng chính user `miyano`.

## Phán quyết
(a) **Có thật về kỹ thuật, nhưng không mở biên tin cậy mới → chấp nhận; T38 không đổi.**
Lệnh filter chỉ đến được từ `.git/config` của repo (và tệp nó `include`), vì `GIT_CONFIG_GLOBAL=/dev/null` và `GIT_CONFIG_NOSYSTEM=1` đã bỏ cấu hình máy. Feature không ghi được `.git/**` (bộ chặn từ chối mọi thành phần `.git`, `design.md:213`) và không ghi repo `erp_ai` (QĐ 8); model sửa `.gitattributes` (có người duyệt) chỉ trỏ tới driver người đã khai, không tự khai được lệnh (ca 1). Ai ghi được `.git/config` là user OS `miyano`, cũng là chủ mọi file `.py` mà worker import: filter không cho thêm quyền nào. Thời gian bị chặn bởi `timeout -s KILL` + nhóm tiến trình riêng (QĐ 4); filter đổi nội dung bị bước 5 QĐ 1 bắt (so byte blob, ca 6) → `Lỗi` có mã commit. Tắt filter chung không làm được trong tập lệnh cho phép (ca 3–5); tắt còn sai với repo khai LFS ở `.git/config` (commit byte thô thay pointer).
Khác hook (QĐ 4 tắt): hook chạy ở mọi commit, vô điều kiện, và có một cờ tắt chung; filter chỉ chạy khi người đã khai cả driver lẫn thuộc tính, và là phép biến nội dung mà bước 5 kiểm được.

(b) Không thêm tùy chọn hay luật từ chối cho `status`. Siết một chỗ cùng loại mà cờ tắt được, để các task không chọn khác nhau:
- Ràng buộc: đối số của nhóm đọc (QĐ 2) không bao giờ chứa `--filters`, `--textconv`, `--ext-diff` (git-cat-file(1), git-diff-tree(1): các cờ này chạy chương trình khai trong config). Kiểm ở chỗ kiểm đối số đọc chung của T37, có test một ca cho mỗi cờ.
- Task mang: **T39** (`git_blob`, `git_commit_summary` dùng `cat-file`/`diff-tree`), trong `files:` hiện có (`source.py`, `test_source.py`). `git_source` hiện có giữ `--no-ext-diff --no-textconv` cho `log`.

## Rủi ro còn lại (ghi lại, không chặn)
- Nếu sau này người khai `include.path` trỏ vào một tệp trong worktree, một thay đổi đã duyệt sửa tệp đó có thể khai filter; hiện có 0 dòng `[include`. Người duyệt thấy toàn bộ diff (AC-22).
- Khi ADR-022 được sửa lần tới, thêm câu này vào Hệ quả/Ràng buộc; phán quyết này không sửa ADR.
