Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 30 — CHG-002 T30

- Diff: `git diff 238544c..dd7376e` trên `team/CHG-002-task-30` (2 commit: `d3a1eb5` = phần addendum-8 A8-3 / A8-4, `dd7376e` = comment của khối; 2 file, +268/−21); `238544c` = `git merge-base team/CHG-002 team/CHG-002-task-30`
- Vòng: 2 (max_rework = 3); vòng 2 chấm `git diff dd7376e..73e8b8d`
- Verdict: request-changes ở vòng 1 → **approve** ở vòng 2 (3/3 ADDRESSED) → merge `42f430c` vào `team/CHG-002`, tick T30

## Vòng 1 — request-changes (`git diff 238544c..dd7376e`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | thân commit `dd7376e` (4 dòng `test-shape:`) | addendum-2 L-1 điểm 5 đòi mẫu `test-shape: <file>::<test> — <cũ> → <mới> — design §x.y (addendum-2 L-1)`; cả bốn dòng dừng sau `<mới>`, thiếu phần `— design §3.7, addendum-7 P7-10 (addendum-2 L-1)`; L-1 ghi dòng không khớp thì chặn merge. Nội dung cũ → mới khớp diff (4 test đổi, 4 dòng) | viết lại 4 dòng có phần design; mang các dòng đã sửa trong commit mới nhất của task (hoặc thân commit merge); không force-push |
| major | STD-TEST-8 | `erp_ai/agent/tools/test_propose_change.py:1833` (đề xuất giả trong `test_no_remote_url`); mã ở `propose_change.py:130-133` | P7-10 điểm 4 và Returns ("mọi giá trị qua `escape_html`") áp cho cả hai dạng khối; test giả chỉ phủ `_shown` trên khối có mục, không test nào đưa `app` có ký tự HTML. Hai thay đổi vẫn để mọi test xanh: bỏ `escape(app)`; hoặc dời `name = change_text._shown(...)` vào nhánh `operations` | (a) đặt `app` giả có ký tự HTML và không có `://` (ví dụ `"<b>&x"`), khẳng định `khối 1 mục trong app &lt;b&gt;&amp;x.`; (b) thêm một dict giả chỉ có lệnh (`command_list='[["restart"]]'`, tên `"CP://T30"`), khẳng định `"></a> đang chờ duyệt: 1 lệnh bench.</p>` |

minor | — | — | 4 điểm nhỏ: (1) STD-DESIGN-4 phép thử khối (`operations or command_list`) nay có ở 3 chỗ (`block.py:20`, `change_text.py:213`, `propose_change.py:129`), không gì giữ chúng khớp nhau; (2) STD-STYLE-5 ở nhánh `else` dạng cũ, `json.loads(proposal.command_list or "[]")` chỉ còn gặp `command_list` rỗng; (3) STD-TEST-5 / L-1 điểm 3: `test_comment_escapes_html…` (dòng 389, 393) dời phép kiểm escape từ câu đầu sang dòng mục thay vì thay giá trị cũ và thêm assertion mới (có khai, câu đầu ghim ở chỗ khác); (4) STD-DESIGN-4 `{m}` dùng `json.loads` còn dòng `Gồm` đếm qua `change_text._stored_commands` | tùy dev

Tầng 1: đạt, chỉ hai file touchpoint. AC-48 (P7-10 điểm 1–5): khối chỉ có lệnh ghi `{m} lệnh bench.`; khối trộn dùng câu mục; `{n}` = `len(operations)` (bộ dựng 4 mục có đổi tên); `{m}` tính `restart`; `_shown` chạy trước `escape_html`; dạng cũ ghim từng byte. A8-3: `PARENT_NOT_DIR` ngay dưới `EXISTS`, hai `return` dùng nó. A8-4: mã không đổi; subTest xóa và đổi tên ghim đúng chuỗi lý do; có test lớp phòng thủ `islink`. Hai dòng `test-ruling:` khớp addendum-8 dòng 92 và 113 từng ký tự.

Phán về ba điểm dev nêu: (1) phép thử khối viết tại chỗ thay `block.is_block(doc)`: nhận (`test_architecture.py:103-107` cấm `erp_ai.agent.tools` nhập `erp_ai.agent.changes`; `change_text.py:212-213` đã làm y vậy ở T20); không phải design-defect. (2) bỏ phần dò dòng đầu của dạng cũ: nhận (`test_legacy_comment_unchanged` ghim từng byte). (3) tên thô trong liên kết: nhận (Returns "ba liên kết như hôm nay").

Bằng chứng của dev. Commit 1: RED `{'ok'[38 chars]README.md/x.txt): đường dẫn không hợp lệ hoặc nằm ngoài apps/'} != {'ok'[38 chars]README.md/x.txt): thư mục cha trên đường dẫn là một file'}` (cả 3 subTest); RED bằng đột biến (bỏ `or os.path.islink(full)`) `… 1 (custom_app/pkg/link.txt): đường dẫn đi qua symlink'} != … 1 (custom_app/pkg/link.txt): đường dẫn không phải file thường'}`; GREEN `test_propose_change` `Ran 72` / `OK`, `test_registry` `Ran 41` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_agent_runner` `Ran 109` chỉ còn 3 test baseline, `test_architecture` `Ran 195` / `OK`. Commit 2: RED (6 trên 8 test mới) `'đang chờ duyệt: 2 lệnh bench.</p>' not found in '… đang chờ duyệt: lệnh <code>bench --site miyano migrate; restart</code>.</p>…'`; GREEN `test_propose_change` `Ran 80` / `OK`, các module khác như trên. L-1: 4, L-2: 0.

## Review checklist (10)
1 đạt · 2 đạt · 3 đạt (khe ở major 2) · 4 trượt (STD-TEST-5, major 1) · 5 không đổi · 6 đạt (độ phủ escape ở major 2) · 7 đạt · 8 đạt (3 minor) · 9 đạt · 10 trượt ở thân commit (major 1).

## Không kiểm được từ diff (tech-lead đã xử lý một phần)

- `design-addendum-9.md` (đến 17:56, tech-lead của lượt 5 chỉ dò phụ lục 8 nên bỏ sót tới 21:28): A9-1 giao thêm cho T30 một khẳng định trong `TestBlockComment::test_restart_line_iff_restart_listed` (comment của khối `.py` + `[migrate, restart]` và của khối chỉ `[restart]` chứa câu `Sau khi áp dụng cần người chạy bench restart.` 0 lần và dòng `Sau khi áp dụng, hệ thống sẽ restart bench (lệnh cuối).` đúng 1 lần, hai chuỗi viết literal). Diff CHƯA có. Đã chép vào dòng task T30; vòng sửa 1 phải làm cùng hai major.
- Nhãn L-3 (addendum-9 A9-2, A9-4): minor (3) ở trên có thể là ca L-3b; dev đối chiếu ở vòng sửa 1, dòng đếm ghi thêm `L-3: <k>`.
- `cmd.lint` cả cây trên `team/CHG-002` @ `238544c` (21:29): 12 hook `Passed`, thoát 0. Nhánh T30 chưa chạy lint cả cây.

## Vòng 2 — approve (`git diff dd7376e..73e8b8d`, 1 commit `73e8b8d`, 1 file `test_propose_change.py` +26/−0)

- Major 1 (STD-TEST-5): ADDRESSED. Thân commit `73e8b8d` mang đủ danh sách của T30; cả 4 dòng `test-shape:` kết bằng `— design §3.7, addendum-7 P7-10 (addendum-2 L-1)`; từng cặp cũ → mới khớp `git diff 238544c..dd7376e` (`:200`, `:389` / `:393`, `:428-429`, `:606-607`), giữ `assertIn` → `assertIn`. Không force-push.
- Major 2 (STD-TEST-8): ADDRESSED (`test_propose_change.py:1858-1870`). (a) `app="<b>&x"` khẳng định `khối 1 mục trong app &lt;b&gt;&amp;x.</p>`; (b) dict chỉ có lệnh tên `CP://T30` khẳng định `"></a> đang chờ duyệt: 1 lệnh bench.</p>`.
- Addendum-9 A9-1: ADDRESSED (`test_propose_change.py:1814-1831`). Hàng `"py, migrate, restart"` và hàng mới `"commands restart"` khẳng định `(đếm câu cũ, đếm dòng mới) == (0, 1)`, hai chuỗi viết literal; ba hàng còn lại `(0, 0)`.
- Nhãn cả task (A9-2, A9-4): 4 dòng đều là L-1; minor (3) của vòng 1 là L-1, không phải L-3b (câu đầu đổi chứ không bị gỡ, đường dẫn đã escape ghim lại ở dòng mục). Dòng đếm: `L-1: 4, L-2: 0, L-3: 0 (L-3a: 0, L-3b: 0)`.
- Finding mới: 0 blocker, 0 major, 0 minor. Checklist (10) trong phạm vi vòng: đạt cả 10 (mục 5, 7, 9 không đổi).
- Deferred (ngoài phạm vi): 4 minor của vòng 1 (phép thử khối ở 3 chỗ; nhánh `else` dạng cũ; `{m}` đếm bằng `json.loads` còn dòng `Gồm` đếm qua `_stored_commands`); hai dòng `test-ruling:` lặp lại từ `d3a1eb5` không chấm lại ở vòng 2 (vòng 1 đã đối chiếu từng ký tự với addendum-8 dòng 92, 113); bộ đếm mới và `assertNotIn` cũ ở `:1832-1833` trùng nhau (A9-1 đòi, không phải lỗi).

Bằng chứng của dev (vòng sửa 1, `propose_change.py` không đổi, ba đột biến đã hoàn lại):
- RED M1 (bỏ `escape(app)`): `AssertionError: 'khối 1 mục trong app &lt;b&gt;&amp;x.</p>' not found in '<p>Đề xuất <a href="/app/erp-ai-change-proposal/CP-T30-HTML">CP-T30-HTML</a> đang chờ duyệt: khối 1 mục trong app <b>&amp;x.</b></p>...'`, `Ran 80 tests in 105.470s` / `FAILED (failures=1)`
- RED M2 (dời `name = change_text._shown(...)` vào nhánh `operations`): `AssertionError: '"></a> đang chờ duyệt: 1 lệnh bench.</p>' not found in '<p>Đề xuất <a href="/app/erp-ai-change-proposal/CP://T30">CP://T30</a> đang chờ duyệt: 1 lệnh bench.</p>...'`, `Ran 80 tests in 104.804s` / `FAILED (failures=1)`
- RED M3 (thêm câu restart cũ vào mọi comment của khối): `(shape='py, migrate, restart') AssertionError: Tuples differ: (1, 1) != (0, 1)`
- GREEN: `test_propose_change` `Ran 80 tests in 108.795s` / `OK`; `test_architecture` `Ran 195 tests in 27.987s` / `OK`

"Không kiểm được từ diff" của vòng 2, tech-lead xử lý: reviewer không chạy test → đợt merge 19, `team/CHG-002` @ `42f430c`, một lần giữ khóa 21:46–22:07 (`cmd.migrate` thoát 0 rồi `cmd.test`): `Ran 1894 tests in 1204.874s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`; `cmd.lint` cả cây @ `42f430c`: 12 hook `Passed`, thoát 0. Dòng đếm của T30 ghi ở đây và ở journal (từ lượt 5 `tasks.md` không nhận dòng progress).

## Việc của vòng sửa 1 (đã giao 21:31, xong ở vòng 2 trên)

Trong worktree của dev: `git switch team/CHG-002-task-30`. Ba việc: major 1, major 2 (nguyên văn ở bảng trên), và khẳng định của addendum-9 A9-1. Commit mới nhất của task mang đủ danh sách dòng `test-shape:` / `test-ruling:` / L-3 đã sửa. Sau đó re-review vòng 2 trên `dd7376e..HEAD`.
