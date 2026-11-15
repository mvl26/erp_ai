Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 26 — CHG-002 T26

- Diff: `git diff ae8edc5..77bfc62` (vòng 1) và `git diff 5d67400..a70a273` (sửa vòng 1), nhánh `team/CHG-002-task-26` (`5d67400` = merge `team/CHG-002` @ `7b7f000`, không mang thay đổi của task)
- Gói: T26 (sửa vòng 1) + T27 cùng nhánh, một reviewer chấm cả gói ở vòng 2; verdict của T27 ở `review-27.md`
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge cùng T27 (sha ở dòng progress của T26 trong `tasks.md`), tick

## Vòng 1 — request-changes (`git diff ae8edc5..77bfc62`, 1 commit, 2 file)

blocker | STD-GIT-2 | erp_ai/agent/changes/test_apply_job.py:53 (`REL = "pkg/mod.py"`), lời gọi ở :2835 và :2938 | Merge nhánh này thì `team/CHG-002` có 2 test đỏ ngoài touchpoint: `test_commit_metadata_has_no_email_url_or_token`, `test_fake_key_never_in_proposal_result_log_comment` (hành vi mới `PY_NEEDS_RESTART`, không phải hình dạng). Dev dừng là đúng; đây là chỗ hở của touchpoint. | Tech-lead thêm `test_apply_job.py` vào touchpoint T26; dev sửa bằng một dòng `test-input:` cho mỗi test, giữ assertion từng byte.

major | STD-TEST-2 | erp_ai/agent/tools/propose_change.py:250-252 ↔ test_propose_change.py:~1050 (`test_edit_and_create_block_one_proposal_rows_in_order`) | Returns A-1.5 đòi `check_block(…, diff_text=diff_text)` nhận đúng chuỗi được lưu; test chỉ ghim `doc.diff`; đổi thành `diff_text=""` vẫn xanh. | Spy `check_block` (`wraps`), assert `kwargs["diff_text"] == doc.diff` và `kwargs["at_apply"] is False`.

minor | — | — | 7 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1 (Lớp 1): `edit` và `create` thành `FileOp`; đọc `TEXT_MAX_BYTES + 1` byte, `text_refusal`, chỉ giải mã khi nó trả `None`, không còn `except UnicodeDecodeError`; bước 2b dựng `diff_text` một lần, truyền vào `check_block`, lưu đúng chuỗi đó; dạng gọi cũ và `propose_new_file` là khối 1 mục; `BLOCK_SHAPE`; đã xóa `NO_PARENT`, `PROPOSAL_FILE_MAX_BYTES`, `TOO_LARGE`; `NOT_UTF8` là `source.TEXT_NOT_UTF8`; không tự `realpath` / `commonpath`; đúng 1 `.insert(` (`:150`) và 1 `allow_agent_write()` (`:149`); `values` không có khóa trạng thái; đủ 11 test Expect.

Đối chiếu thân commit `77bfc62`: 13 dòng `test-shape:` khớp L-1 điểm 3 (so bằng giữ so bằng); 14 dòng `test-input:` khớp diff, assertion giữ nguyên; ca "thứ tự bước" của `test_git_refusal` khớp §4.1 (bước 2 trước bước 3).

Quyết định của tech-lead 14:27 (5 dòng `test-drop:` cho `RESTART_NOTE`): reviewer chấm **không phải design-defect**. design.md:390 (§3.7) và :815 (§8.3) đã bỏ hẳn câu "cần người chạy bench restart" cho mọi đề xuất không phải dạng cũ; mọi đề xuất do tool tạo từ T26 là khối; AC-48 thuộc T30 (`test_restart_line_iff_restart_listed`). Nhưng lý do ghi trong 5 dòng ("không tới được trước T28") sai căn cứ (sau T28 câu này vẫn không có trên khối `.py`), và định dạng không khớp addendum-4:39: designer khi xác nhận cần dẫn §3.7:390, §8.3:815 và đặt định dạng cho nhãn "đầu vào cũ bị luật mới từ chối" (điểm thiết kế mở).

Bằng chứng của dev (vòng 1): RED (`propose_change.py` của BASE + test mới) `Ran 45 tests in 35.335s` / `FAILED (failures=25, errors=7)`; GREEN `test_propose_change` `Ran 46 tests in 57.773s` / `OK`, `test_registry` `Ran 41 tests in 2.667s` / `OK`, `test_change_decision` `Ran 10 tests in 18.580s` / `OK`, `test_architecture` `Ran 195 tests in 27.002s` / `OK`; còn đỏ lúc đó: `test_apply_job` `Ran 117 tests in 200.171s` / `FAILED (failures=2)`, `test_apply_block` `Ran 1 test in 1.624s` / `FAILED (failures=1)`. L-1: 13, L-2: 0, test-input (luật mới): 13, test-drop: 5, test-new: 1.

## Vòng 2 — approve (`git diff 5d67400..a70a273`, 3 file, +59/−20)

Giữa hai vòng: lần gọi dev đầu của vòng sửa dừng `DESIGN_CONFLICT` (0 commit): đổi `.py` → `.txt` gỡ `PY_NEEDS_RESTART`, nhưng hai test vẫn đỏ ở chặng hoàn tác vì từ T26 tool chỉ tạo đề xuất dạng khối mà hoàn tác khối là T39. Quyết định của tech-lead 16:00 (thứ tự task của kế hoạch, không phải thiết kế cho hai hành vi; chờ designer xác nhận): hai test giữ lời gọi tool cho phần assertion đọc đầu ra của tool, chặng áp dụng → hoàn tác chạy trên đề xuất dạng cũ dựng trực tiếp; assertion giữ từng byte.

1. ADDRESSED | STD-GIT-2 | `test_apply_job.py:2833-2835`, `:2853-2862`, `:2939-2942`, `:2975-2986`. Reviewer chấm quyết định trên: mọi giá trị kỳ vọng giữ nguyên chữ ở cả hai test (chỉ đối tượng được đọc đổi sang `legacy`); `TestNoKeyLeak` vẫn đọc đủ các kho (kết quả tool, đề xuất `[legacy, command, code]`, comment theo ticket, log); `TestCommitCrossChecks` đọc comment và log của cả đề xuất tool lẫn `legacy`; không phải STD-TEST-5, không phải design-defect (hoàn tác khối = T39 / T40; rò rỉ khóa của khối = T43 `TestNoKeyLeakBlock::test_seeded_key_zero_in_proposal_comment_log_output`). Hai dòng `test-input:` có trong thân `a70a273`.
2. ADDRESSED | STD-TEST-2 | `test_propose_change.py:1056-1057`, `:1095-1098`: spy, `call_count == 1`, `diff_text == doc.diff`, `at_apply is False`; RED bằng đột biến `diff_text=""`.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev (vòng 2): RED bằng đột biến `AssertionError: '' != '--- a/custom_app/pkg/a.txt\n+++ b/custom_[128 chars] b\n'`, `Ran 46 tests in 57.839s` / `FAILED (failures=1)`; GREEN `test_propose_change` `Ran 46 tests in 57.904s` / `OK`, `test_apply_block` `Ran 9 tests in 12.648s` / `OK`, `test_registry` `Ran 41 tests in 2.462s` / `OK`, `test_change_decision` `Ran 10 tests in 18.521s` / `OK`, `test_architecture` `Ran 195 tests in 27.266s` / `OK`, `test_apply_job` `Ran 117 tests in 204.292s` / `OK`. L-1: 0, L-2: 0, test-input (luật mới): 2.

## Không kiểm được từ diff (tech-lead đã xử lý)

- `_edited_op` băm `after.encode("utf-8")` kiểu chặt: `replace` chứa surrogate lẻ thì `UnicodeEncodeError` nổ trước `check_block` (đã có trên BASE; nhánh `create` dùng `surrogatepass`). CHƯA xử lý: cần xem `execute_tool` có bắt không; ghi thành việc cho T29 (task đổi schema `find` / `replace`) và điểm mở trong báo cáo lượt 4.
- Từ T26 tới T28 không đề xuất được file `.py` qua tool: nhánh feature không giao được trước khi T28 merge (T28 đã giao ở round 45; T51 là cổng cuối).
- Module và cả app sau merge: dòng progress của T26 trong `tasks.md` (đợt merge 16).

## deferred

1. Tên test cũ không còn khớp nội dung (`test_comment_escapes_html_and_adds_restart_note_for_py`, `test_new_file_errors_exists_and_no_parent`); không đổi tên vì tên là khóa của các dòng `test-…:` đã commit.
2. Header diff lấy từ `os.path.normpath(op.path)` còn `file_path` lấy từ `guard.rel_path` (hai nguồn cho một đường dẫn).
3. Mục không phải dict cho tiền tố `mục n (None): `.
4. `test_apply_job.py:2882` `assertIn("origin/main", notes)` nay đúng nhờ giá trị seed tay; `:2941` `if not lexists` trong `run_flow`.
5. RED của vòng 1 lấy sau khi viết mã; `test_py_without_commands_refused_until_commands_exist` không có RED riêng.
