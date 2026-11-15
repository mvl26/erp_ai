# CHG-002 — Rà trước kiến trúc 1 (arch-preflight-1)

- Người viết: architect, 2026-11-15, chế độ `--decide`, chỉ đọc.
- Phạm vi: hợp đồng (dòng files / Receives / Returns / Expect) của T25–T30, T33–T40, T47–T49 trong `docs/team/features/CHG-002/tasks.md`, đối chiếu với các luật `check_*` của `990d7b3:erp_ai/tests/test_architecture.py` (viết tắt `ARCH`).
- Không phán T24 (một architect khác đang sửa ADR-040 cho T24). Không sửa ADR, design hay tasks nào.
- Căn cứ mã: mọi số dòng là của `git show 990d7b3:<file>`.

## Tóm tắt

- 17 task được rà, 3 task có vấn đề: **T49** (3 điểm), **T48** (1 điểm), **T26** (1 điểm, nối với T49). 14 task còn lại: không thấy luật nào bắt, có ghi chú "đừng làm" ở vài hàng.
- Cả ba vấn đề đều sửa được bằng câu chữ của task, **không phải nới luật đang có** và **không cần ngoại lệ có tên mới** trong `ARCH`.

## Các luật đã đọc thân (áp cho `agent/changes/`, `agent/tools/`, controller, JS)

| Luật | `ARCH` dòng | Nội dung đang có |
|---|---|---|
| `check_layer_imports` + `LAYER_RULES` | 537, 75-141 | `erp_ai.agent.tools` không nhập `erp_ai.agent.changes`; `erp_ai.agent.changes` không nhập `erp_ai.erp_ai_agent`, `runner`, `run_status`, … |
| `check_import_boundaries` | 551-583 | chỉ stdlib/frappe/helpdesk/erp_ai; ngoại lệ có tên `NAMED_LIBRARY_IMPORTS` (167) |
| `check_tools_never_bypass_permissions` | 726-760 | trong `agent/tools/**`: không `ignore_permissions`, `db.set_value`, `set_user`, `get_all` |
| `check_subprocess_only_in_source_tool` | 763-783 | tiến trình chỉ ở `source.py`, `process_runner.py` |
| `check_policy_fields_only_in_policy` | 866-882 | `code_change_apps`, `code_change_enabled`, … chỉ đọc ở `policy.py` (177-185) |
| `check_no_default_people_in_agent_python` | 1923-1931 | không tên người (1707) trong chuỗi dưới `agent/` |
| `check_change_state_fields_written_only_in_changes` + `_state_field_writes` | 2130-2142, 2096-2128 | 19 trường `STATE_FIELDS` (1994-2014, có `restart_status`, `created_dirs`, `command_results`) chỉ được ghi dưới `agent/changes/`; "ghi" gồm cả khóa dict, `dict(k=)`, `get_doc(k=)` |
| `check_change_guard_uses_resolve_safe_path` | 2195-2251 | ngoài `source.py`: không hàm tên chứa `safe_path`, không `commonpath`/`is_relative_to` ngoài `ROOT_CHECK_ALLOWLIST` (1983) |
| `check_tool_never_saves_proposal` | 2539-2566 | tool chỉ `.insert()` đề xuất, không `save`/`db_set`/`set_value` |
| `check_fs_writes_only_in_file_writer` + `FS_WRITE_FUNCTIONS` | 2682-2694, 2576-2595 | trong `agent/**` và controller: ghi/đổi tên/xóa file chỉ ở `file_writer.py` |
| `check_file_writer_rechecks_through_resolver` | 2706-2772 | mọi hàm cấp module của `file_writer.py` chạm hệ tệp phải có tên trong `FILE_WRITER_RECHECKERS` (T6 bật, tasks.md:129) |
| `check_changes_never_set_user_or_publish` | 2775-2805 | trong `agent/changes/**`: không `set_user`, `publish_realtime`, kể cả trong chuỗi |
| `GIT_ALLOWED_SUBCOMMANDS`, `check_git_commit_add_rm_argv_shape` | 2812-2851, 3530-3544 | git ghi chỉ `add`/`commit`/`rm` ở `process_runner.py`; `add`, `rm --cached` đúng 1 đường dẫn (T7 đổi `commit` thành 1..N, tasks.md:136) |
| `check_bench_allowlist_has_no_git_running_subcommands` | 3755-3781 | `BENCH_COMMANDS` của `change_guard.py` là bảng chuỗi hằng |
| `check_apps_root_single_function` + `code_texts` | 3784-3823, 3076-3088 | trong `agent/**`: chuỗi khớp `(^|/)apps(/|$)` (kể cả chuỗi `"apps"` trơn) chỉ trong `source.get_source_root` |
| luật quét `.js` | 4596-4600, 4729-4740, 4375-4390 | `check_no_legacy_ticket_comment`, `check_no_open_doc_or_all_room`, `check_form_script_only_in_install`, `check_no_version_reads` |

## Bảng theo task

| Task | Luật hiện có sẽ bắt | Vì sao hợp đồng đụng luật | Cách làm đúng không nới luật |
|---|---|---|---|
| T25 | không thấy | JS form chỉ thêm nút, hộp xác nhận, `frappe.call` tới `confirm_restart`; bốn luật quét `.js` (ARCH 4596-4600, 4729-4740, 4375) chỉ bắt `comment_by`/`HD Ticket Comment`, phòng `open_doc:`/`all`, `HD Form Script`, chuỗi `"Version"`. `restart_status` đọc trong JS không thuộc `_state_field_writes` (luật chỉ quét `.py`, ARCH 2134). | Tải lại bằng `frm.reload_doc()`, không `frappe.realtime.on`/phòng socket. Không phán lời gọi `confirm_restart` phía server (T24). |
| T26 | (nối với T49 điểm 3) `test_single_text_rule_no_extension_list` của T49 (tasks.md:439) | Hợp đồng T26 giữ bước giải mã nội dung file `edit` để áp `find`/`replace`; hôm nay đó là `data.decode("utf-8")` ở `propose_change.py:183` kèm `except UnicodeDecodeError` ở `:184`. Câu T49 "chỉ `source.text_refusal` giải mã UTF-8 chặt" sẽ bắt dòng này. | **Chọn:** T26 gọi `text_refusal(rel, data)` trước, chỉ giải mã khi nó trả `None`, và **bỏ** `except UnicodeDecodeError` ở `:184` (câu lỗi `NOT_UTF8` trỏ tới `source.TEXT_NOT_UTF8`, đúng tasks.md:283). **Vì:** quyết định "có phải văn bản" chỉ còn ở `text_refusal` (`source.py:145-163`), phần giải mã sau đó chỉ đổi kiểu. **Sai thì hoàn tác:** nếu T49 viết luật đúng nghĩa đen "0 `.decode(` ngoài `text_refusal`", dời phần giải mã vào một hàm của `source.py` ở T49 (T49 đã có `source.py` trong touchpoint), không đổi T26. Ngoài ra: lấy `full` từ `change_guard.check_write_path`/`check_block`, không tự `realpath` + `commonpath` (ARCH 2236-2249); xóa `PROPOSAL_FILE_MAX_BYTES` ở `propose_change.py:34` như hợp đồng đã ghi. |
| T27 | không thấy | `isfile`, `islink`, `os.stat(...).st_mode`, `lexists` là phép đọc, không có trong `FS_WRITE_FUNCTIONS` (ARCH 2576-2595) và không phải `ROOT_CHECK_CALLS` (ARCH 1979). | Kiểm trên đường dẫn đầy đủ do `check_block`/`check_write_path` trả về; không `os.path.realpath` + `commonpath` trong `propose_change.py` (ARCH 2236-2249). `FileOp` nhập từ `change_guard` (`change_guard.py:61`), không từ `agent/changes/block.py` (ARCH 103-106). |
| T28 | không thấy | `command_list`, `change_kind`, `reversible` không thuộc `STATE_FIELDS` (ARCH 1994-2014); `build_bench_args` ở `change_guard` (tools), không đụng tầng. | Không đặt bất kỳ khóa nào của `STATE_FIELDS` (đặc biệt `restart_status`, `change_status`, `command_results`) vào `values` của `_insert`: khóa dict ngoài `agent/changes/` là vi phạm (ARCH 2112-2115), cùng dạng đã chặn T24. Giá trị đầu lấy từ mặc định của DocType JSON. |
| T29 | không thấy | `PROPOSAL_TEXT_MAX_CHARS`, `REPLACE_MAX_ITEMS` chỉ dùng ở `constants.py:47-48` và `propose_change.py:23-24, 43, 76, 301-302, 334-335, 356`; `ARCH` không ghim hai tên này. | Xóa đủ các dòng trên trong cùng task. |
| T30 | không thấy | Câu comment không có chuỗi `apps/`/`"apps"` (ARCH 3812-3816) và không tên người (ARCH 1707). | Câu "trong app {app}" giữ chữ `app` số ít; không viết `apps/{app}` trong `propose_change.py` (ARCH 3812). |
| T33 | không thấy | `apply_job.py` (changes) nhập `change_guard` (tools): không cấm (ARCH 107-121). Đọc app qua `policy.current_change_settings()` / `settings.allowed_apps` như `apply_job.py:232-235`, không đọc trường `code_change_apps` (ARCH 177-185, 866-882). | Giữ cách đọc ở `apply_job.py:232-252`. |
| T34 | không thấy | `lexists`, `sha256_of`, `read_git_state` là đọc; `read_git_state` ở `source.py:531`, git đọc chỉ ở `source.py` (ARCH 2816-2818). | Đường dẫn đầy đủ lấy từ kết quả `check_block`; không ghép `"apps"` bằng chuỗi (ARCH 3812-3816 bắt cả chuỗi `"apps"` trơn). |
| T35 | không thấy (nếu chỉ ghép bốn hàm của `file_writer`) | Trả lại "đổi tên" và "tạo lại file đã xóa" là thao tác hệ tệp; ngoài `file_writer.py` mọi `os.rename`/`os.replace`/`os.remove`/`shutil.*` bị bắt (ARCH 2576-2596, 2682-2694); T35 không có `file_writer.py` trong touchpoint nên không được thêm hàm mới ở đó (ARCH 2754-2770). | Trả đổi tên = `write_atomic(nguồn, before, new_file=True)` rồi `remove_file(đích)`; tạo lại file đã xóa = `write_atomic(…, new_file=True)`; gỡ file đã tạo = `remove_file`. `git_add_new`/`git_unstage_new` gọi **từng đường dẫn một** (`process_runner.py:104, 122`; `add` và `rm --cached` vẫn đúng 1 đường dẫn, tasks.md:136). |
| T36 | không thấy, với điều kiện T7 đã merge | Một commit nhiều đường dẫn bị `_write_argv_problems` bắt hôm nay (ARCH 3531-3532, "exactly one path"); T7 đổi luật thành 1..N cho `commit` (tasks.md:136). T36 → T35 → T34 → T33 → T7 nên thứ tự đã đúng. | Gọi `git_commit_only(repo, rels, …)` một lần. `source.git_commit_summary`, `git_blob`, `git_is_ancestor` có sẵn (`source.py:686, 741, 767`). |
| T37 | không thấy | `run_bench` ở `process_runner.py:53`; `apply_job.py` không mở tiến trình (ARCH 763-783). | Không nhập `subprocess` trong `apply_job.py`. |
| T38 | không thấy | `post_restart_notice` ở `result_comment.py` (changes); chuỗi log không chứa `publish_realtime`/`set_user` (ARCH 2794-2800 bắt cả chuỗi). | Chữ `proposal=… action=restart error=<lớp>` không chứa tên hai hàm đó. |
| T39 | không thấy | `settings.allowed_apps ∪ {app}` đi qua `policy.current_change_settings()` như `apply_job.py:232-235`. | Như T33, T34, T35. |
| T40 | không thấy | `test_block.py` là file test, không nằm trong mã sản phẩm được quét (ARCH 428-435). | — |
| T47 | không thấy | `"setsid"` hôm nay đúng 1 lần, `source.py:90`; không có `sudo`/`supervisorctl` trong mã sản phẩm (grep toàn `erp_ai/**/*.py` ngoài test, 0 dòng). | Đếm qua `load_product_sources` (ARCH 428), không `rglob` thô (file test này chứa chính chuỗi `"setsid"`). |
| T48 | không phải luật bắt mã, mà **không có RED** (STD-TEST-1) | `FS_WRITE_FUNCTIONS` đã có đủ bảy tên `os.mkdir`, `os.makedirs`, `os.rmdir`, `os.rename`, `os.replace`, `os.remove`, `os.unlink` (ARCH 2576-2595). Phần 1 của Returns (tasks.md:430) và ca mẫu "`os.mkdir` ngoài `file_writer` bị bắt" (tasks.md:432) xanh ngay trên `990d7b3`. | **Chọn:** ghi phần 1 là "đã có, chỉ thêm ca tự kiểm hồi quy"; RED của T48 đến từ phần `BENCH_COMMANDS` có `restart` (đỏ khi T11 chưa thêm — nếu T11 đã merge thì RED là ca mẫu bảng thiếu `restart`). **Vì:** dev sẽ báo DONE_WITH_CONCERNS/không có RED nếu Expect đòi đỏ ở phần đã xanh. **Sai thì hoàn tác:** nếu reviewer cần RED riêng cho phần 1, dùng ca mẫu `shutil.move` qua bí danh, không thêm tên mới vào bảng. Bảng `BENCH_COMMANDS` giữ dạng tuple chuỗi hằng trong `change_guard.py` (`change_guard.py:40-43`; ARCH 3762-3767 đòi bảng chuỗi hằng). |
| T49 | ba luật mới của chính T49 bắt mã đã có hoặc mã của task khác | xem ba điểm dưới | xem ba điểm dưới |

### T49 — ba điểm

**Điểm 1 — `RESTART_*` chỉ gán ở `constants.py` (tasks.md:439).**
- Đụng: `change_text.py:158, 159, 168` (`RESTART_SENT_AT_LABEL`, `RESTART_LABELS`, `RESTART_SENT_AT_FORMAT`), `transitions.py:94-96` (`RESTART_EXPECTED_STATES`, `RESTART_LAUNCH_VALUES`, `RESTART_CONCLUSIONS`), `change_guard.RESTART_COMMAND` của T11 (tasks.md:294), `process_runner.RESTART_ARGV` của T8 (tasks.md:423). Tất cả là nhãn, tập trạng thái, argv; không phải giới hạn.
- **Chọn:** luật liệt kê đúng ba giới hạn thời gian `RESTART_WEB_STOP_S`, `RESTART_TIMEOUT_S`, `RESTART_LAUNCH_TIMEOUT_S` (`constants.py:88-90`) thay cho mẫu `RESTART_*`.
- **Vì:** ý của luật (ADR-040 QĐ 5, "giới hạn định nghĩa một lần") là giới hạn; dời nhãn và argv vào `constants.py` sẽ kéo `RESTART_COMMAND` ra khỏi `change_guard.py`, mà `BENCH_COMMANDS` phải là bảng chuỗi hằng đọc được trong chính file đó (ARCH 3762-3767).
- **Sai thì hoàn tác:** nếu designer muốn giữ mẫu, thêm hậu tố: mọi tên `RESTART_*_S` chỉ gán ở `constants.py`; không đổi tên các hằng đã có.

**Điểm 2 — "xuất hiện 0 lần trong `erp_ai/**`" cho `DUOI_CHO_PHEP` và `SEARCH_FILE_MAX_BYTES` (tasks.md:438-439).**
- Đụng: chính `erp_ai/tests/test_architecture.py` phải viết hai tên đó để tìm chúng; `test_source.py:85` dùng `source.DUOI_CHO_PHEP` (T49 có file này trong touchpoint, phải xóa).
- **Chọn:** quét bằng `load_product_sources(suffixes=(".py", ".js", ".json", ".html"))` (ARCH 428-435) như mọi luật khác, cộng xóa `test_source.py:85`.
- **Vì:** `rglob` thô qua `erp_ai/**` luôn đỏ vì chính file test.
- **Sai thì hoàn tác:** nếu muốn phủ cả test, loại trừ đúng một file `tests/test_architecture.py` bằng tên.
- Phụ thuộc: `SEARCH_FILE_MAX_BYTES` hôm nay còn hai người dùng `file_writer.py:11` (T6 xóa, tasks.md:130) và `propose_change.py:34` (T26 xóa); `source.py` không dùng nó ngoài dòng định nghĩa `:46`. T49 depends đã có T29 (sau T26) nhưng **không có T6**; T6 tới trước qua T48 → T11? Không chắc từ dòng depends; tech-lead kiểm `depends:` của T49 có T6 trực tiếp hoặc gián tiếp.

**Điểm 3 — "chỉ `source.text_refusal` giải mã UTF-8 chặt" (tasks.md:439).**
- Đụng mã đã có: `source.py:191` (`read_source`), `source.py:233` (`_read_text`), `propose_change.py:183-184` (T26 giữ bước giải mã), `change_guard.py:89-91` (`_first_line` đọc file con trỏ `.git` với `encoding="utf-8"`, không phải nội dung file đề xuất).
- **Chọn:** luật đọc là "chỉ `text_refusal` **bắt `UnicodeDecodeError`** và so `TEXT_MAX_BYTES` cho nội dung file; mọi `.decode("utf-8")` khác trong `agent/**` phải nằm trong hàm đã gọi `text_refusal(...)` trước đó". `source.py:191` và `:233` đã đúng dạng này (`:189`, `:231`); T26 theo hàng T26 ở trên.
- **Vì:** giữ một luật văn bản duy nhất mà không phải viết lại `read_source`/`_read_text` (ngoài Returns của T49).
- **Cần ngoại lệ có tên:** `("agent/tools/change_guard.py", "_first_line")` — đọc con trỏ gitdir, không phải văn bản đề xuất; luật không có lý do bắt nó. Ghi ngoại lệ ngay cạnh hằng trong `ARCH` kèm một câu lý do, như `ROOT_CHECK_ALLOWLIST` (ARCH 1983-1990).
- **Sai thì hoàn tác:** nếu designer muốn nghĩa đen "0 giải mã ngoài `text_refusal`", T49 thêm một hàm của `source.py` trả chuỗi đã giải mã sau `text_refusal` và đổi ba nơi gọi; khi đó T49 phải thêm `propose_change.py` vào touchpoint.

## tasks.md đổi gì (cho tech-lead)

1. **T49, dòng 439:** thay "`RESTART_*` chỉ gán ở `constants.py`" bằng "`RESTART_WEB_STOP_S`, `RESTART_TIMEOUT_S`, `RESTART_LAUNCH_TIMEOUT_S` chỉ gán ở `constants.py`".
2. **T49, dòng 438-439:** "xuất hiện 0 lần trong `erp_ai/**`" → "0 lần trong mã sản phẩm (`load_product_sources`)"; ghi rõ xóa `source.DUOI_CHO_PHEP` ở `test_source.py:85`.
3. **T49, dòng 439:** viết lại câu "chỉ `source.text_refusal` giải mã UTF-8 chặt" theo điểm 3 ở trên, kèm ngoại lệ có tên `change_guard._first_line`.
4. **T49, dòng `depends`:** kiểm có T6 (người xóa `file_writer.py:11`) trực tiếp hoặc qua chuỗi; nếu không, thêm `T6`.
5. **T48, dòng 430/432:** ghi "phần `os.*` đã có ở `ARCH` 2576-2595, chỉ thêm ca tự kiểm; RED đến từ phần `BENCH_COMMANDS`".
6. **T26, dòng 283:** thêm "bỏ `except UnicodeDecodeError` ở `propose_change.py:184`; giải mã chỉ sau khi `text_refusal` trả `None`".
7. **T28, dòng 296:** thêm "`values` của `_insert` không có khóa nào của `STATE_FIELDS` (`ARCH` 1994-2014)".
8. **T35, dòng 347:** thêm "trả đổi tên/tạo lại chỉ bằng `write_atomic` và `remove_file`; `git_add_new`/`git_unstage_new` từng đường dẫn".

## Chưa rà

- Thân các luật không áp trực tiếp hoặc chưa đọc: `check_subprocess_call_shape` (ARCH 786), `check_secret_handling` (910), `check_git_subcommands_only_allowed_sets_per_file` (3395), `check_no_forbidden_git_operations_in_product` (3445), `check_registry_has_one_grant_function` (4051), `check_agent_write_flag_only_in_run_log_and_propose_tool` (4140), `check_no_get_whitelist_reaches_change_state` (3920), `_builds_proposal`/`_proposal_deny_violations` của `check_tool_never_saves_proposal`, `is_product_file`.
- Chưa đối chiếu design.md §3.2-§3.6, §4.2-§4.4 từng dòng; bảng trên chỉ dựa trên tasks.md và mã `990d7b3`.
- Không rà T7, T8, T11, T24 (ngoài danh sách; T24 có architect khác).
