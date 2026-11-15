Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 20/53, READY build). -->

# Design addendum 7 — CHG-002 (hẹp: câu chữ của "Comment kết quả", T32; năm điểm của T30)

Phạm vi: bảy câu hỏi của T32 (`tasks.md` dòng 327) về `design.md` §3.7 "Comment kết quả" (dòng 402–414), và năm điểm cùng loại ở "Comment đề xuất trên phiếu" (dòng 367–388, T30). Không đổi AC, không đổi NFR, không đổi phạm vi. Không sửa `design.md`. Câu của addendum này **thay** dòng 402–412 ở những chỗ được dẫn, như các addendum trước.

Nguồn đã đọc (không Explore, theo lệnh giao): `tasks.md` T30 (305–309), T31 (313–319), T32 (321–327), T38 (362–367), T40 (375–378); `design.md` §2 dòng 150, §3.1 dòng 226–230, §3.7 dòng 366–414, §4.2–4.4 dòng 478–579; `design-addendum-3.md` RQ-3, RQ-4 (52–86); `design-addendum-5.md`; `fc01f10:erp_ai/agent/changes/test_result_comment.py`; `990d7b3:erp_ai/agent/changes/result_comment.py`; `990d7b3:erp_ai/agent/change_text.py`; `5f418c1:erp_ai/agent/changes/transitions.py` (`prepare_new`, `request_undo`, `begin_apply`); `5f418c1:erp_ai/agent/changes/block.py` (tên hàm).

**Giữ nguyên, không đổi chữ ký (đã hứa với phiên FEAT-007 ở A3 RQ-3, RQ-4):** `result_lines(fields, *, doc=None)`; `post_result(proposal_name)` đọc `doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)` và truyền vào; dòng riêng của khối khi và chỉ khi `doc is not None and block.is_block(doc)`; tiền tố `kết quả đề xuất` chỉ cho comment kết quả; dạng cũ đúng từng byte như `f5cfed2`; tập trạng thái nhận được không đổi (`Đã áp dụng`, `Lỗi`, `Hết hiệu lực`, `Đã hoàn tác`; còn lại `ValueError`); nhánh FEAT-007 chèn **trước** nhánh khối; `block.py` không nhập `result_comment`. `RESULT_FIELDS` **không đổi** (chữ dạng cũ phụ thuộc vào nó).

## Assumptions decided by the team
- A7-1. Lúc `post_result` chạy (§4.2 bước 12, sau bước 11 = §4.4), `restart_status` chỉ có thể rỗng, `Đã gửi` hoặc `Lỗi khởi chạy`. `Đã xác nhận` / `Chưa xác nhận` chỉ được ghi về sau khi mở form (§4.4 bước 5), nên comment kết quả không bao giờ thấy hai giá trị đó trên đường thật; hàm thuần vẫn phải có chữ cho chúng.
- A7-2. `command_results` có một phần tử cho mỗi lệnh **đã chạy** (`design.md:150`), không có phần tử cho `restart` (§4.2 bước 9 "trừ `restart`") và không có phần tử cho lệnh bị bỏ sau lệnh lỗi.
- A7-3. `prepare_new` chỉ chạy lúc `insert` (`transitions.py:117`); `request_undo` không xóa `command_results`, `restart_status` (`transitions.py:237-266`). Nên khi hoàn tác, hai trường này còn giữ giá trị của lần áp dụng cho tới khi job hoàn tác ghi đè. Luật P7-5, P7-6 dưới đây dựa vào điều đó.
- A7-4. `block.operations_of(doc)` trả các mục theo `idx` (thuộc tính `kind`, `path`, `new_path`), nên "mục n" trong `failure_reason` là phần tử thứ n (đếm từ 1) của tuple đó (`design.md:229`). `restart` trong danh sách là đúng argv `["restart"]` (`change_text._RESTART_ARGV`).
- A7-5. Job chạy trong ngữ cảnh site, `frappe.local.site` có giá trị (cùng giá trị `site` mà §4.2 bước 2 truyền cho `check_block`).

---

## P7-1. Luật chung của dạng khối

Đầu vào của nhánh khối (chỉ đọc, ngoài `fields`):
- `operations = block.operations_of(doc)`, `commands = block.commands_of(doc)`;
- `doc.command_results`: đọc **chỉ** ba khóa `args`, `exit_code`, `timed_out` (hằng mới `COMMAND_RESULT_KEYS = ("args", "exit_code", "timed_out")` trong `result_comment.py`); khóa `output`, `duration_ms` **không bao giờ đọc**;
- `doc.restart_status`, `doc.app`.

Không đọc nội dung file (`content_before`, `content_after`), `diff`, `command_output`, `upstream_ref`. `RESULT_FIELDS` không thêm tên nào.

Ba đại lượng dẫn xuất (dùng ở P7-2..P7-7):
- **lượt hoàn tác** = `bool(fields.undo_by)` (`undo_by` chỉ do `request_undo` ghi).
- **lượt này đã đổi file** = `(not lượt hoàn tác and apply_commit_sha) or (lượt hoàn tác and undo_commit_sha)`.
- **đã qua bước restart** = `change_status ∈ {Đã áp dụng, Đã hoàn tác}` (§4.4 chỉ chạy sau `finish` tới hai trạng thái này, §4.2 bước 11, §4.3 bước 7).

Mọi đoạn chữ lấy từ dữ liệu (nhãn, đường dẫn, argv, lý do) đi qua `_masked_reason` có sẵn (gấp khoảng trắng, che từ chứa `://` hoặc `@` thành `[đã ẩn]`, cắt 300 ký tự). Toàn chuỗi vẫn qua `frappe.utils.escape_html` một lần trong `post_result` như hôm nay. Các nhóm nối bằng `LINE_SEPARATOR = "; "` như hôm nay; nhóm rỗng thì không có phần tử nào (không có `; ; `).

Thứ tự phần tử: dòng 1 → dòng lý do (P7-4, nếu có) → nhóm 2 → nhóm 3 → nhóm 4 → nhóm 5 → nhóm 6.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Dòng riêng của khối đọc từ `doc`, `RESULT_FIELDS` giữ nguyên | `post_result` đã đọc `doc` (A3 RQ-3); thêm tên vào `RESULT_FIELDS` là đổi tập trường của dạng cũ mà `test_legacy_text_byte_identical_per_status` ghim | Thêm `command_results`, `restart_status`, `app` vào `RESULT_FIELDS` | Thêm ba tên vào `RESULT_FIELDS`, nhánh khối đọc `fields`; test dạng cũ giữ xanh vì chữ cũ không đọc ba trường đó |
| Che bằng `_masked_reason` cả nhãn, đường dẫn, argv | Một luật che cho mọi chuỗi lấy từ dữ liệu, nên "0 URL, khóa, token" của AC-49 không phụ thuộc vào việc bộ chặn đường dẫn/lệnh có lọt chữ `@` hay không | Chỉ che lý do như dạng cũ | Bỏ `_masked_reason` ở đường dẫn và argv; `test_seeded_token_zero` không đổi vì hạt giống nằm ở lý do, nội dung, đầu ra |

## P7-2. Câu hỏi (1): `{nhãn}` của dòng 1

Dòng 1: `kết quả đề xuất {tên} ({nhãn}): {trạng thái}`, `{trạng thái}` là `change_status` nguyên chữ.
- Có mục file → `{nhãn}` = `_masked_reason(change_text.block_label(operations))`: đường dẫn khi đúng 1 mục, `{n} file` khi nhiều hơn (cùng nhãn với tiêu đề commit, §3.7 dòng 394).
- Khối chỉ có lệnh (0 mục) → `{nhãn}` = `{m} lệnh bench`, `m = len(commands)` (tính cả `restart`). Không bao giờ in `0 file`.
- Khối có cả mục và lệnh → nhãn của mục (lệnh hiện ở nhóm 4).

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Dùng lại `block_label`; chỉ lệnh → `{m} lệnh bench` | STD-DESIGN-4; cùng chữ `{m} lệnh bench` với câu đầu của comment đề xuất (§3.7 dòng 373), người đọc ghép được hai comment | Nhãn `{n} mục, {m} lệnh` cho mọi khối | Đổi một hàm `_block_result_label`; sửa chuỗi kỳ vọng của mẫu M1–M5 |

## P7-3. Câu hỏi (2) và (3): nhóm 2, động từ, đổi tên, trạng thái từng mục

Mỗi mục một phần tử, theo thứ tự `operations`:

`{động từ} {path}: {tình trạng}` — đổi tên: `đổi tên {path} → {new_path}: {tình trạng}`.

- **Động từ:** chữ thường của `change_text._ITEM_VERBS` (`sửa`, `tạo`, `xóa`, `đổi tên`), tức chữ của thân commit, **không** dùng `XÓA` / `ĐỔI TÊN`.
- **`{tình trạng}`** (luật theo dữ liệu, một luật cho mọi trạng thái):

| Điều kiện (xét theo thứ tự) | `{tình trạng}` |
|---|---|
| `undo_commit_sha` có | `đã hoàn tác` |
| `apply_commit_sha` có | `đã áp dụng` |
| còn lại | `chưa áp dụng` |

Hệ quả theo trạng thái:

| `change_status` | Tình trạng mục |
|---|---|
| `Đã áp dụng` | `đã áp dụng` |
| `Lỗi`, lượt áp dụng, lỗi trước commit (kiểm lại, so đĩa, git, ghi mục k đã trả lại) | `chưa áp dụng` |
| `Lỗi`, lượt áp dụng, sau commit (lệnh lỗi/quá giờ; `GIT_COMMIT_MISMATCH` giữ sha) | `đã áp dụng` (A-33: không trả lại file) |
| `Lỗi`, lượt hoàn tác bị từ chối hoặc trả lại trước commit hoàn tác | `đã áp dụng` (file vẫn ở trạng thái đã áp dụng, `apply_commit_sha` giữ) |
| `Lỗi`, lượt hoàn tác, commit hoàn tác đã có rồi lệnh lỗi | `đã hoàn tác` |
| `Hết hiệu lực` | `chưa áp dụng` |
| `Đã hoàn tác` | `đã hoàn tác` |

`đã hoàn tác` là từ thứ ba thêm vào hai từ của §3.7 dòng 404: in `đã áp dụng` cho mục đã hoàn tác là sai sự thật.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Động từ chữ thường của thân commit | Comment kết quả là bản báo sau sự việc, đọc cạnh commit; chữ hoa của ghi chú đề xuất là để người duyệt chú ý **trước** khi bấm | `XÓA` / `ĐỔI TÊN` như `proposal_notes` | Dùng `change_text._NOTE_VERBS`; sửa mẫu M1, M4, M6 |
| Tình trạng mục suy từ hai sha, thứ tự hoàn tác → áp dụng → chưa | Sha là sự thật đã commit; không cần trường mới; đúng cho mọi trạng thái kể cả hai cạnh hoàn tác | Suy từ `change_status` | Thay bảng điều kiện bằng bảng trạng thái; test `test_item_state_follows_commits` đổi ca |

Ghi chú: với `GIT_RESTORE_FAILED` (trả lại không trọn, không có sha) mục hiện `chưa áp dụng`; dòng lý do (P7-4) nói rõ việc trả lại không trọn, người đọc lý do đó.

## P7-4. Câu hỏi (2), phần lý do, và câu hỏi (5): lý do không gắn mục

Có lý do khi và chỉ khi `change_status ∈ {Lỗi, Hết hiệu lực}` **và** `failure_reason.strip()` khác rỗng (lý do cũ còn sót trên `Đã hoàn tác` sau hoàn tác từ `Lỗi` không in).

**Đoạn lý do** = `lý do: {_masked_reason(failure_reason)}`; khi `change_status = Lỗi` và lượt hoàn tác → `khi hoàn tác, lý do: …` (cùng chữ dạng cũ, `result_comment.py:647-652`). Đoạn lý do in **đúng một lần**:
- **Gắn mục:** `failure_reason.strip()` khớp `ITEM_REASON = re.compile(r"^(?:ghi )?mục (\d+) \(")` và `1 ≤ n ≤ len(operations)` → nối vào phần tử của mục n: `{động từ} {path}: {tình trạng}, {đoạn lý do}`. Hai mẫu lý do có mục của §4.2/§4.3: `mục n (path): …` (bước 2, 4, 5; hoàn tác bước 2) và `ghi mục k (path) lỗi, …` (bước 6). Lý do giữ nguyên cả tiền tố (không bóc `mục n (path): `), để mọi lý do đi qua đúng một hàm che như dạng cũ.
- **Không gắn mục** (kiểm lại người chạy, vai trò, công tắc, dấu; `lệnh n: …`; `lệnh j (bench …): …`; `GIT_*`; `STORED_HASH_MISMATCH` không có tiền tố mục; n ngoài khoảng) → một phần tử riêng ngay sau dòng 1, trước nhóm 2 (cùng chỗ đứng của dòng lý do ở dạng cũ).

Dạng khối **không** nối `, mã thoát {x}` vào lý do (dạng cũ có); mã thoát nằm ở nhóm 4.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Khớp tiền tố `mục n (` bằng một regex, lý do in một lần, phần còn lại một dòng sau dòng 1 | Đúng câu §3.7 dòng 404 "mục nêu trong `failure_reason` có thêm lý do"; tiền tố là hợp đồng có sẵn (`design.md:229`); không lặp lý do | (a) luôn một dòng lý do sau dòng 1, không gắn mục; (b) bóc tiền tố khi gắn | (a): bỏ `ITEM_REASON`, đổi mẫu M6; (b): thêm bước bóc, đổi mẫu M6 |

## P7-5. Câu hỏi (4): nhóm 3, commit

- `apply_commit_sha` có → `commit {apply_commit_sha[:12]}`.
- `undo_commit_sha` có → thêm `commit hoàn tác {undo_commit_sha[:12]}` (chữ dạng cũ).
- Có cả hai (`Đã hoàn tác`, hoặc `Lỗi` sau commit hoàn tác) → in cả hai, áp dụng trước.
- Không có sha nào (khối chỉ có lệnh; lỗi trước commit; `Hết hiệu lực`) → **bỏ** nhóm 3.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| In cả hai sha, bỏ nhóm khi không có | Người cần sha áp dụng để đối chiếu và sha hoàn tác để biết file đã về; `commit ` rỗng là lỗi giống `review-31.md` | Chỉ in sha hoàn tác khi `Đã hoàn tác` (như dạng cũ) | Bỏ phần tử `commit {apply}` khi có `undo_commit_sha`; sửa mẫu M4 |

## P7-6. Nhóm 4, lệnh

- Lượt hoàn tác mà `undo_commit_sha` rỗng → bỏ nhóm 4 (lượt đó chưa tới bước lệnh, §4.3 bước 5 chạy sau commit hoàn tác; `command_results` còn là của lượt áp dụng, A7-3).
- Còn lại: mỗi phần tử của `command_results` (rỗng/`None` → không phần tử nào), theo thứ tự lưu:
  - `timed_out` đúng → `bench {argv}: quá thời gian`;
  - ngược lại → `bench {argv}: mã thoát {exit_code}`;
  - `{argv}` = `_masked_reason(" ".join(args))`.
- `command_results` không phải JSON list các object có `args` là list, hoặc phần tử không `timed_out` mà `exit_code` không phải `int` → `ValueError("command_results không đọc được: …")` (cùng luật chặt của `_stored_commands`; job ghi log như mọi lỗi của `post_result`).

Điều kiện cho T40: job hoàn tác truyền `command_results` **của lượt hoàn tác** cho `finish` ở mọi lần kết thúc sau commit hoàn tác (`Đã hoàn tác`, hoặc `Lỗi` khi lệnh chạy lại lỗi). Không thế thì comment `Đã hoàn tác` in mã thoát của lần áp dụng.

## P7-7. Câu hỏi (7): nhóm 5, restart

| Điều kiện (xét theo thứ tự) | Phần tử |
|---|---|
| đã qua bước restart, `restart_status = Đã gửi` | `restart: đã gửi` |
| đã qua bước restart, `Lỗi khởi chạy` | `restart: lỗi khởi chạy` |
| đã qua bước restart, `Đã xác nhận` | `restart: đã xác nhận` |
| đã qua bước restart, `Chưa xác nhận` | `restart: chưa xác nhận` |
| đã qua bước restart, giá trị khác khác rỗng | `ValueError(f"restart_status không hỗ trợ: {value!r}")` (cùng chữ P-1 của addendum-5) |
| `["restart"]` có trong `commands` (còn lại) | `restart: không chạy` |
| còn lại | `restart: không cần` |

Ở `Lỗi` và `Hết hiệu lực` không đọc `restart_status` (giá trị còn lại có thể là của lượt áp dụng, A7-3). `không chạy` là từ thứ tư thêm vào ba từ của §3.7 dòng 407: khối có `restart` mà bị dừng thì `không cần` là sai sự thật (AC-45 "lỗi thì 0 restart; kết quả ghi trên … comment").

Câu hỏi về `test_unconfirmed_label_…` của T32: test của T32 kiểm **comment** (`result_lines`), không kiểm nhãn form (nhãn form là T21). Đổi tên ở bảng "tasks.md đổi gì".

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Đọc `restart_status` chỉ khi đã qua bước restart; thêm `không chạy` | Comment nói đúng lượt vừa xong; không cần sửa `transitions` (T16, T17 đã tick) để xóa trường khi bắt đầu hoàn tác | `request_undo` xóa `command_results`, `restart_status`, `restart_sent_at` | Thêm việc xóa ba trường vào `request_undo` (mở lại T16), rồi đọc `restart_status` ở mọi trạng thái |

## P7-8. Câu hỏi (6): nhóm 6, việc người còn phải làm

Dạng: `việc người còn phải làm: {gợi ý nối bằng ", "}`, hoặc `việc người còn phải làm: không` khi không có gợi ý nào. Không gợi ý nào chứa dấu phẩy, nên `, ` không lẫn.

Gợi ý, đúng thứ tự này, mỗi gợi ý tối đa một lần:
1. `restart bench` khi nhóm 5 là `lỗi khởi chạy` hoặc `chưa xác nhận`, **hoặc** nhóm 5 là `không chạy` và lượt này đã đổi file.
2. `nếu sau {RESTART_TIMEOUT_S // 60} phút form đề xuất chưa ghi "Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)` khi nhóm 5 là `đã gửi`. Với `RESTART_TIMEOUT_S = 700` là `11 phút`.
3. `chạy bench build --app {app}` khi lượt này đã đổi file, có `path` hoặc `new_path` của một mục mà `PurePosixPath(p).suffix.lower() ∈ {.js, .ts, .vue, .css, .scss, .less}`, và **không** có phần tử `command_results` nào thỏa: `args[0] == "build"`, (`"--app"` không có trong `args` hoặc phần tử sau `--app` bằng `app`), `exit_code == 0`, `timed_out` sai.
4. `chạy bench --site {site} migrate` khi lượt này đã đổi file, có mục `.json` (cùng cách đọc đuôi), và không có phần tử `command_results` nào có `"migrate"` trong `args`, `exit_code == 0`, `timed_out` sai.

- `{app}` = `_masked_reason(doc.app)`.
- `{site}` = `frappe.local.site` đọc trong nhánh khối của `result_lines` (A7-5; đọc biến ngữ cảnh, không I/O; chữ ký không đổi).
- Gợi ý build/migrate **không** áp khi file chưa được áp dụng (lượt này không đổi file: `Hết hiệu lực`, lỗi trước commit, hoàn tác bị từ chối).

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| "Khối không có build" đọc là "không có build **chạy xong mã 0** trong lượt này" | Build lỗi hay quá giờ thì file `.js` vẫn chưa được build; gợi ý phải nói việc còn lại thật | Đọc nguyên chữ "khối không có lệnh build trong `command_list`" | Đổi điều kiện 3, 4 sang `commands`; sửa mẫu M3 |
| Thêm gợi ý `restart bench` cho `không chạy` khi lượt này đã đổi file | File `.py` đã commit nằm trên đĩa nhưng chưa có hiệu lực; AC-49 đòi nêu việc người còn phải làm | Chỉ gợi ý restart theo `restart_status` như §3.7 dòng 409 | Bỏ vế "hoặc" của gợi ý 1; sửa mẫu M3 |
| `{site}` = `frappe.local.site` trong `result_lines` | Đúng site job đang chạy (cùng giá trị §4.2 bước 2); không đổi chữ ký đã hứa | (a) tham số mới `site=` chỉ từ khóa; (b) `post_result` ghi khóa `site` vào `fields` | (a): thêm `site=None`, `post_result` truyền `frappe.local.site`; test truyền site |

## P7-9. Chuỗi comment mẫu (chữ trước `escape_html`; test so `escape_html(mẫu)`)

Chung: `{tên}` = `P-7`, app `custom_app`, site `miyano`, `apply_commit_sha = 0123456789abcdef0123456789abcdef01234567`, `undo_commit_sha = fedcba9876543210fedcba9876543210fedcba98`. `"` trong M4, M5 thành `&quot;` sau `escape_html`.

**M1 — khối 2 mục + 1 lệnh, `Đã áp dụng`** (mục: sửa `custom_app/public/js/form.js`, tạo `custom_app/fixtures/role.json`; lệnh `["build", "--app", "custom_app"]` mã 0; không `restart`):

> kết quả đề xuất P-7 (2 file): Đã áp dụng; sửa custom_app/public/js/form.js: đã áp dụng; tạo custom_app/fixtures/role.json: đã áp dụng; commit 0123456789ab; bench build --app custom_app: mã thoát 0; restart: không cần; việc người còn phải làm: chạy bench --site miyano migrate

**M2 — khối chỉ có lệnh, `Đã áp dụng`** (lệnh `["build", "--app", "custom_app"]` mã 0; không sha):

> kết quả đề xuất P-7 (1 lệnh bench): Đã áp dụng; bench build --app custom_app: mã thoát 0; restart: không cần; việc người còn phải làm: không

**M3 — `Lỗi` giữa chừng** (mục: sửa `custom_app/pkg/mod.py`, sửa `custom_app/public/js/form.js`; lệnh `build --app custom_app` rồi `restart`; commit xong, build trả mã 1, `failure_reason = "lệnh 1 (bench build --app custom_app): lệnh trả mã 1"`):

> kết quả đề xuất P-7 (2 file): Lỗi; lý do: lệnh 1 (bench build --app custom_app): lệnh trả mã 1; sửa custom_app/pkg/mod.py: đã áp dụng; sửa custom_app/public/js/form.js: đã áp dụng; commit 0123456789ab; bench build --app custom_app: mã thoát 1; restart: không chạy; việc người còn phải làm: restart bench, chạy bench build --app custom_app

Cùng khối, build quá giờ (`timed_out = true`, lý do `lệnh 1 (bench build --app custom_app): quá thời gian`): phần tử nhóm 4 là `bench build --app custom_app: quá thời gian`, phần còn lại như trên (AC-49: nêu tên lệnh, giữ file, không restart).

**M4 — `Đã hoàn tác`** (mục: sửa `custom_app/pkg/mod.py`, đổi tên `custom_app/pkg/old.py → custom_app/pkg/new.py`; lệnh `restart`; T40 chạy lại, `command_results = []`, `restart_status = Đã gửi`):

> kết quả đề xuất P-7 (2 file): Đã hoàn tác; sửa custom_app/pkg/mod.py: đã hoàn tác; đổi tên custom_app/pkg/old.py → custom_app/pkg/new.py: đã hoàn tác; commit 0123456789ab; commit hoàn tác fedcba987654; restart: đã gửi; việc người còn phải làm: nếu sau 11 phút form đề xuất chưa ghi "Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)

**M5 — có restart `Đã gửi`, 1 mục** (sửa `custom_app/pkg/mod.py`; lệnh `restart`):

> kết quả đề xuất P-7 (custom_app/pkg/mod.py): Đã áp dụng; sửa custom_app/pkg/mod.py: đã áp dụng; commit 0123456789ab; restart: đã gửi; việc người còn phải làm: nếu sau 11 phút form đề xuất chưa ghi "Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)

Cùng khối, `Lỗi khởi chạy`: `…; commit 0123456789ab; restart: lỗi khởi chạy; việc người còn phải làm: restart bench`.

**M6 — `Hết hiệu lực`, lý do gắn mục** (sửa `custom_app/pkg/mod.py`, xóa `custom_app/pkg/old.py`; lệnh `restart`; `failure_reason = "mục 2 (custom_app/pkg/old.py): file đích đã đổi kể từ lúc đề xuất"`):

> kết quả đề xuất P-7 (2 file): Hết hiệu lực; sửa custom_app/pkg/mod.py: chưa áp dụng; xóa custom_app/pkg/old.py: chưa áp dụng, lý do: mục 2 (custom_app/pkg/old.py): file đích đã đổi kể từ lúc đề xuất; restart: không chạy; việc người còn phải làm: không

Dạng cũ: không mẫu mới; chữ là sáu hàng đã ghim ở `fc01f10:test_result_comment.py:318-369` (`TestLegacyResult`), không đổi.

---

## P7-10. T30 "Comment đề xuất của khối": năm điểm cùng loại

1. **`…` của câu đầu khối chỉ có lệnh** viết đủ: `Đề xuất {tên} đang chờ duyệt: {m} lệnh bench.` Vì: tránh hai cách đọc dấu `…`. Khác: giữ `…`. Sai thì: sửa chuỗi kỳ vọng của `test_command_only_first_sentence`.
2. **Khối có cả mục và lệnh** dùng câu mục `…: khối {n} mục trong app {app}.`; số lệnh nằm ở dòng `Gồm … {m} lệnh.` của `proposal_notes`. Vì: app chỉ có nghĩa với mục file; cùng luật nhãn P7-2. Khác: `…: khối {n} mục và {m} lệnh trong app {app}.` Sai thì: đổi câu đầu, thêm ca vào `test_comment_counts_…`.
3. **`{n}` = `len(operations)`** (mỗi đổi tên là 1 mục), **`{m}` = `len(commands)` tính cả `restart`**, bằng đúng số `{m}` của dòng `Gồm …` (`change_text._block_notes` đếm `len(commands)`). Vì: hai số trên cùng một comment phải khớp. Khác: `{m}` không tính `restart`. Sai thì: trừ `["restart"]` ở cả câu đầu và `_block_notes` (T20).
4. **`{tên}`, `{app}` đi qua `_shown` trước `escape_html`**; khối chỉ có lệnh không có câu nhánh/remote (vì `change_kind = Lệnh bench`, `proposal_notes` chỉ in câu nhánh khi `is_code`). Vì: NFR-8 như hôm nay, `test_no_remote_url` phủ được. Khác: không lọc. Sai thì: bỏ `_shown` ở câu đầu.
5. **Dạng cũ** giữ câu đầu và toàn bộ comment hôm nay đúng từng byte; rẽ bằng `block.is_block(doc)` như RQ-3. Vì: T30 không nói dạng cũ; cùng luật một chỗ phân dạng. Khác: không có. Sai thì: không áp dụng (chỉ thêm test ghim). Test thêm `TestBlockComment::test_legacy_comment_unchanged`.

---

## Việc dev T32 phải làm trên `fc01f10` (nhánh `team/CHG-002-task-32`)
1. Giữ `TestLegacyResult::test_legacy_text_byte_identical_per_status` như đã viết (xanh trên mã cũ là đúng: đó là test ghim, không phải RED).
2. Viết trước các test `TestBlockResult` ở bảng dưới, dùng `make_block_proposal` (T2), qua `post_result` và so `escape_html(mẫu)`; dán RED (`TypeError … unexpected keyword argument 'doc'` hoặc chuỗi khác) bằng `cmd.test_one` với `erp_ai/agent/changes/test_result_comment.py`.
3. `result_comment.py`:
   - `result_lines(fields, *, doc=None)`; `doc is None or not block.is_block(doc)` → trả đúng danh sách hôm nay (không đụng `_target`, `_outcome_line`).
   - Nhánh khối theo P7-1..P7-8, thứ tự phần tử P7-1; `_outcome_line` vẫn gọi trước để giữ `ValueError` cho trạng thái không phải kết cục.
   - Hằng mới: `COMMAND_RESULT_KEYS`, `ITEM_REASON`, `BUILD_SUFFIXES = (".js", ".ts", ".vue", ".css", ".scss", ".less")`, `MIGRATE_SUFFIX = ".json"`, các chữ nhóm 5 và nhóm 6. `RESTART_TIMEOUT_S` nhập từ chỗ hằng đó đang ở (không viết số 11).
   - Nhập: `from erp_ai.agent.changes import block`, `from erp_ai.agent import change_text` (dùng `block_label`, `_ITEM_VERBS`); không nhập ngược. `RESULT_FIELDS`, `NOTICE_FIELDS`, `post_restart_notice` không đổi.
   - `post_result`: thêm `doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)` sau kiểm phiếu, gọi `result_lines(fields, doc=doc)`; phần còn lại không đổi.
   - Docstring module và hàm nêu luật mới; không đọc `output`.
4. GREEN: `cmd.test_one` với `erp_ai/agent/changes/test_result_comment.py`; rồi với `erp_ai/tests/test_architecture.py` (luật phụ thuộc một chiều).
5. Không đụng `change_text.py`, `block.py`, `apply_job.py`, `transitions.py`.

## tasks.md đổi gì (tech-lead ghi; designer không sửa tasks.md)

| Phán quyết | Task | Returns / Receives đổi | Expect (tên test) |
|---|---|---|---|
| P7-1..P7-9 | T32 | Returns: nhánh khối theo P7-1..P7-8 (đọc `doc`, chỉ `COMMAND_RESULT_KEYS`; `RESULT_FIELDS` không đổi; nhãn P7-2; tình trạng mục 3 từ; lý do một lần theo `ITEM_REASON`; nhóm 3 hai sha hoặc bỏ; nhóm 4 bỏ ở lượt hoàn tác chưa commit; nhóm 5 bảy hàng gồm `không chạy`; nhóm 6 bốn gợi ý nối `, `, `{site}` = `frappe.local.site`); `command_results` hỏng, `restart_status` lạ → `ValueError` | Giữ: `TestBlockResult::test_one_result_comment_per_outcome_with_items_commit_exit_codes_restart_todo`, `test_command_timeout_names_command_keeps_files_no_restart`, `test_build_and_migrate_todo_hints`, `test_seeded_token_zero` (hạt giống ở `failure_reason`, `content_after`, `command_results[].output`, `upstream_ref`), `test_block_only_lines_absent_when_not_block`, `TestLegacyResult::test_legacy_text_byte_identical_per_status`. Bỏ `test_legacy_result_text_unchanged` (thay bởi test trên, A3 RQ-3). Đổi tên `test_unconfirmed_label_says_permission_may_be_missing_and_todo_restart` → `test_sent_todo_says_permission_may_be_missing_unconfirmed_todo_restart` (kiểm comment). Thêm: `test_addendum7_samples_exact_text` (M1–M6 và hai biến thể), `test_item_state_follows_commits`, `test_item_reason_attached_once_other_reason_own_line`, `test_restart_line_per_status_and_not_run`, `test_bad_command_results_or_restart_status_raises_value_error` |
| P7-6 | T40 | Returns thêm: `finish(Đang hoàn tác → …, command_results=<lượt hoàn tác>)` ở mọi kết thúc sau commit hoàn tác (`[]` khi danh sách chỉ có `restart`) | Thêm `AB::TestUndo::test_undo_writes_its_own_command_results` (tên lớp theo file của T40) |
| P7-7, P7-8 | T38 | Returns thêm: `post_result` chạy sau `record_restart` và commit DB (§4.2 bước 12), nên comment kết quả đọc được `Đã gửi` / `Lỗi khởi chạy` | `test_exactly_one_result_comment_after_notice` kiểm thêm comment chứa `restart: đã gửi`; `test_launch_failure_records_launch_failed_status_unchanged` kiểm thêm `restart: lỗi khởi chạy; việc người còn phải làm: restart bench` |
| P7-10 | T30 | Returns: câu đầu chỉ lệnh viết đủ; khối hỗn hợp dùng câu mục; `{n}`, `{m}` như điểm 3; `_shown` trước `escape_html`; dạng cũ đúng từng byte | Thêm `TestBlockComment::test_mixed_block_first_sentence_counts_items`, `test_command_count_includes_restart`, `test_legacy_comment_unchanged` |

## Đối chiếu AC/NFR và test plan
- AC của spec (CHG-002): AC-35, AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50, AC-51, AC-52, AC-53, AC-54, AC-55, AC-56 (22). NFR: NFR-12, NFR-13, NFR-14, NFR-15 (4).
- Addendum này chỉ bỏ `test_legacy_result_text_unchanged` (đã thay bởi `test_legacy_text_byte_identical_per_status` theo A3 RQ-3, cùng AC-49) và đổi tên một test T32; còn lại chỉ thêm. 22/22 AC, 4/4 NFR vẫn có ≥ 1 dòng `file::name`.
- AC chạm tới: AC-49 ← P7-1..P7-9 (`erp_ai/agent/changes/test_result_comment.py::TestBlockResult::*`); AC-45 ← P7-7 (`test_restart_line_per_status_and_not_run`, T38); AC-48 ← P7-10 (`erp_ai/agent/tools/test_propose_change.py::TestBlockComment::*`); AC-42 ← P7-6 (T40).

## Touchpoints (đường dẫn có sẵn, không tạo file mới)
`erp_ai/agent/changes/result_comment.py`, `erp_ai/agent/changes/test_result_comment.py` (T32); `erp_ai/agent/tools/propose_change.py`, `erp_ai/agent/tools/test_propose_change.py` (T30); `erp_ai/agent/changes/apply_job.py`, `erp_ai/agent/changes/test_apply_block.py` (T38, T40). 0 đường dẫn mới, nên so sánh với `allowed_new_file_roots`: không có dòng nào để so; không file nào thuộc `protected_paths` (không secrets, không cấu hình site). Explore: không gọi (theo lệnh giao); nguồn đọc ghi ở đầu file.
