# FEAT-004 — Ghi chú dev

## T1 — Thời gian `bench migrate` và `bench build --app` trên `miyano`

- Ngày đo: 2026-11-13 (khoảng 11:18–11:30 +07), máy 20 nhân, site `miyano` dùng chung với dev khác.
- Tiêu chí: NFR-3, D-10 — mọi số ≤ 540 s thì ghi "đạt".
- Nhánh: `team/FEAT-004-task-1` tạo từ `team/FEAT-004` (`cb40420`); code bằng schema hiện tại của site nên migrate không đổi schema.
- `W` = `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/agent-a586f5b7777a12c1c`.
- Chạy lần lượt từng lệnh, không song song. Không gặp chờ khóa hay deadlock khi migrate.
- App mẫu cho `build --app <app>`: chỉ `hrms` (quyết định team-leader, nhật ký 2026-11-13). Không build `frappe`, `erpnext`, `helpdesk`.

### Môi trường

| Mục | Giá trị |
|---|---|
| `bench --version` | `5.31.0` |
| `git --version` | `git version 2.43.0` |
| `which timeout` | `/usr/bin/timeout` |
| `which bench` | `/home/miyano/.local/bin/bench` |
| `which git` | `/usr/bin/git` |

### Bảng số đo (giây, cột `real` của `time` trong bash)

| Lệnh | Lần 1 | Lần 2 | Lần 3 | Lớn nhất | Mã thoát | ≤ 540 s |
|---|---|---|---|---|---|---|
| `cd /home/miyano/frappe-bench && time PYTHONPATH=$W bench --site miyano migrate` | 35.514 | 39.767 | 38.007 | 39.767 | lần 2, 3: `0`; lần 1: không ghi mã (thiếu `PIPESTATUS`), đầu ra kết thúc bình thường như lần 2, 3 | đạt |
| `cd /home/miyano/frappe-bench && time PYTHONPATH=$W bench build --app erp_ai` | 2.180 | 1.634 | 1.645 | 2.180 | `0` cả 3 lần | đạt |
| `cd /home/miyano/frappe-bench && time bench build --app hrms` | 18.408 | 17.389 | 18.016 | 18.408 | `0` cả 3 lần | đạt |

User/sys (giây): migrate 21.210/1.619, 21.797/1.469, 21.303/1.449; build erp_ai 1.630/0.431, 1.461/0.313, 1.481/0.313; build hrms 26.950/2.636, 26.475/2.386, 27.058/2.412.

**Kết luận: đạt.** Số lớn nhất 39.767 s (migrate lần 2) < 540 s; T11, T21, T22 tiếp tục được.

**UNVERIFIED:** thời gian build các app lớn hơn (`helpdesk`, `frappe`, `erpnext`) chưa đo, vì có file chưa commit của người khác trong các repo đó. Người sẽ đo `bench build --app helpdesk` sau.

### Đầu ra rút gọn

`bench --site miyano migrate` (lần 3, 20 dòng cuối; lần 1 và 2 giống hệt):

```text
[AssetCore] Workflow synced: IMM-16 CAPA Workflow
[AssetCore] Workflow synced: IMM-16 Compliance Finding Workflow
[AssetCore] Workflow synced: IMM-16 Internal Audit Workflow
[AssetCore] Workflow synced: IMM-16 Management Review Workflow
[AssetCore] ERPNext Asset custom fields applied (23 fields).
[AssetCore] RBAC cleanup: 0 legacy DocPerm xóa, 0 Has Role row gỡ khỏi User.
[AssetCore] Role Profile seed: 0 created, 8 updated, 0 unchanged; 0 legacy xoá.
[AssetCore] Legacy Module Profile cleanup: 0 xóa.
[AssetCore] Core DocPerm: 0 insert, 0 update, 926 skip (0 DocType bỏ qua, 0 role bỏ qua).
[AssetCore] Notifications: 7 rule(s) đã sync.
[AssetCore] ac_caps::* busted (cap-set v105.b50a24e5f62f)
[AssetCore] prune_orphan_link_customfields: đã gỡ 0 orphan Custom Field.
[AssetCore FE] dist đã có, bỏ qua build (after_migrate).
  Dọn role: skip: User '…@example.invalid' — còn liên kết với IMM Audit Trail …
  Dọn role: skip: Role 'Internal Auditor' — còn liên kết với Workflow Action …
  Dọn role: skip: 1 Contact của user test còn liên kết (vd. John Doe)
RBAC sync tắt (mvl_rbac_enabled chưa bật)

Queued rebuilding of search index for miyano
```

`bench build --app erp_ai` (lần 3, 8 dòng cuối; lần 1 còn có các dòng `Linking … to ./assets/<app>` cho mọi app và `✔ Application Assets Linked`):

```text
yarn run v1.22.22
$ node esbuild --production --apps erp_ai --run-build-command
File                                                        Size

 DONE  Total Build Time: 90.74ms

Done in 0.62s.
Compiling translations for erp_ai
```

`bench build --app hrms` (lần 1, các dòng cuối; bỏ danh sách file font/asset):

```text
../hrms/public/roster/assets/Home-CZfzyXkm.js                              166.37 kB │ gzip:  53.86 kB
../hrms/public/roster/assets/index-BP1ViDLu.js                             610.68 kB │ gzip: 199.58 kB

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking: https://rollupjs.org/configuration-options/#output-manualchunks
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
✓ built in 4.52s
$ cp ../hrms/public/roster/index.html ../hrms/www/roster.html
Done in 17.38s.
Compiling translations for hrms
```

### Trạng thái repo trước và sau

| Kiểm | Trước | Sau |
|---|---|---|
| `git -C /home/miyano/frappe-bench/apps/hrms status --porcelain` | rỗng, exit 0 | rỗng, exit 0 (build không làm bẩn `hrms`) |
| `git status --porcelain` trong worktree `W` | rỗng | rỗng (build không đổi file đã theo dõi) |

### Điều cần biết

- `bench build` liên kết lại `sites/assets/<app>` cho mọi app ở mỗi lần chạy. Với `PYTHONPATH=$W`, lần build `erp_ai` đầu tiên đã trỏ `sites/assets/erp_ai` vào `$W/erp_ai/public` (thấy trong dòng `Linking …`). Lần `bench build --app hrms` sau đó (không `PYTHONPATH`) trỏ lại về `/home/miyano/frappe-bench/apps/erp_ai/erp_ai/public`; đã kiểm bằng `readlink` sau cùng. Trong khoảng giữa, site dùng chung phục vụ asset `erp_ai` từ worktree này.
- `bench migrate` chạy cả hook `after_migrate` của các app khác (AssetCore, …); phần lớn thời gian là của chúng, không phải của `erp_ai`.
