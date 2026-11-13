# FEAT-004 — Ghi chú kiểm git (T35, kiểm sớm D-18)

Ngày: 2026-11-13. Lần chạy: 2 (lần 1 bị bộ chặn Bash của worktree từ chối, không chạy gì).

## Mục tiêu

Xác nhận D-18 (nền AC-20, ADR-022 QĐ 2): hoàn tác một file mới bằng cách gỡ file khỏi đĩa (`rm`, không `git rm`)
rồi `git commit --only -- <đích>` ghi được việc xóa file đã theo dõi, và không kéo theo thay đổi staged/unstaged khác.

## Môi trường

- `git --version` → `git version 2.43.0`
- Repo tạm: `mktemp -d` → `/tmp/tmp.enCoH8QF4g` (ngoài `apps/`, không đụng repo nào của bench).
- Mỗi lệnh git chạy riêng một lần gọi, dạng `git -C /tmp/tmp.enCoH8QF4g <lệnh>`; file tạo/sửa bằng công cụ Write, xóa bằng `rm` đường dẫn tuyệt đối.
- Danh tính test đặt trong repo tạm: `config user.name "T35 Test"`, `config user.email "t35@test.invalid"`.

### Sai lệch so với khối task

Khối task yêu cầu `GIT_CONFIG_GLOBAL=/dev/null` (như `process_runner`). Không đặt được: bộ chặn Bash của worktree dev
từ chối lệnh có tiền tố biến môi trường cấu hình git ("injecting git configuration whose effect on where git writes
can't be verified"). Vì vậy cấu hình global của máy vẫn được đọc. Cấu hình thực tế áp dụng:

```
$ git -C /tmp/tmp.enCoH8QF4g config --show-origin --get-regexp '^(core\.hookspath|commit\.gpgsign|user\.)'
file:/home/miyano/.gitconfig	user.name hivx
file:/home/miyano/.gitconfig	user.email chuvanhieu357@gmail.com
file:.git/config	user.name T35 Test
file:.git/config	user.email t35@test.invalid
```

Không có `core.hookspath`, không có `commit.gpgsign`; `user.*` của repo tạm ghi đè global. Vậy cấu hình global
không ảnh hưởng đến hành vi được kiểm (chọn đường dẫn của `commit --only`); kết luận vẫn áp dụng cho `process_runner`.

## Các bước và đầu ra thật

Chuẩn bị: `init -q -b main`; Write `keep.txt` = `keep v1`, `other.txt` = `other v1`; `add keep.txt other.txt`;
`commit --no-gpg-sign --quiet -m base` (không đầu ra).

### (1) `keep.txt` staged sửa, `other.txt` unstaged sửa

Write `keep.txt` = `keep v2 staged`, `other.txt` = `other v2 unstaged`, `new.txt` = `new file`; `add keep.txt new.txt`.

```
$ git -C /tmp/tmp.enCoH8QF4g status --porcelain
M  keep.txt
A  new.txt
 M other.txt
```

### (2) Commit `new.txt`

```
$ git -C /tmp/tmp.enCoH8QF4g commit --only --no-gpg-sign --quiet -m "add new" -m "step 2" -- new.txt
(không đầu ra)
$ git -C /tmp/tmp.enCoH8QF4g status --porcelain
M  keep.txt
 M other.txt
```

### (3) `rm new.txt` khỏi đĩa (không `git rm`)

```
$ rm /tmp/tmp.enCoH8QF4g/new.txt
$ git -C /tmp/tmp.enCoH8QF4g status --porcelain
M  keep.txt
 D new.txt
 M other.txt
```

### (4) `git commit --only -- new.txt`

```
$ git -C /tmp/tmp.enCoH8QF4g commit --only --no-gpg-sign --quiet -m "undo new" -m "step 4" -- new.txt
(không đầu ra)
```

### (5) Kiểm kết quả

```
$ git -C /tmp/tmp.enCoH8QF4g show --stat --format=%H HEAD
044e1654b9733c960f72828a3e0c50b7f250cd39

 new.txt | 1 -
 1 file changed, 1 deletion(-)

$ git -C /tmp/tmp.enCoH8QF4g ls-tree HEAD
100644 blob f49f7d1572019b58c28976428032d9546bf00eaa	keep.txt
100644 blob cd29c6fbbf3bf214d8a3ca3310912624020f6ae3	other.txt

$ git -C /tmp/tmp.enCoH8QF4g diff --cached --name-only
keep.txt

$ git -C /tmp/tmp.enCoH8QF4g status --porcelain
M  keep.txt
 M other.txt
```

Bổ sung (xác nhận trạng thái xóa và `keep.txt` không bị commit lẫn):

```
$ git -C /tmp/tmp.enCoH8QF4g show --name-status --format=%s HEAD
undo new

D	new.txt

$ git -C /tmp/tmp.enCoH8QF4g log --oneline --name-status
044e165 undo new
D	new.txt
e1a28b9 add new
A	new.txt
04bd7fb base
A	keep.txt
A	other.txt

$ git -C /tmp/tmp.enCoH8QF4g show HEAD:keep.txt
keep v1
```

## Đối chiếu Expect

| Kỳ vọng | Bằng chứng | Kết quả |
|---|---|---|
| Commit mới chứa đúng 1 đường dẫn `new.txt`, trạng thái xóa | `show --stat`: `1 file changed, 1 deletion(-)`; `--name-status`: `D	new.txt` | đúng |
| `ls-tree` không còn `new.txt` | chỉ `keep.txt`, `other.txt` | đúng |
| `keep.txt` vẫn staged | `diff --cached --name-only` → `keep.txt`; porcelain `M  keep.txt`; `HEAD:keep.txt` = `keep v1` | đúng |
| `other.txt` vẫn unstaged | porcelain ` M other.txt` | đúng |

## Kết luận

**đạt** — `git commit --only -- <đích>` (git 2.43.0) ghi được việc xóa file đã theo dõi sau khi chỉ `rm` khỏi đĩa,
không cần `git rm --cached` trước; chỉ mục và cây làm việc của các file khác giữ nguyên. ADR-022 QĐ 2 không cần mở rộng.

Ghi chú phụ: hook PreToolUse in cảnh báo STD-NAME-5 cho các message `base`, `add new`, `undo new` của repo tạm;
đây là repo thử ngoài dự án nên không áp dụng.
