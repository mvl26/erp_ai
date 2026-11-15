Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 172 — FEAT-007 T172

- Diff vòng 1: `git diff caa555a7158708ed8ff377c864da338ea7a9464a..a538b11` (nhánh `team/FEAT-007-task-172`; 2 commit `e545697` test, `a538b11` mã; 2 file +60/−3, đều là touchpoint)
- Diff vòng 2 (soát lại có phạm vi): `git diff a538b11..5b190db` (2 commit `8fdd775` test, `5b190db` style; 2 file +27/−16)
- Diff vòng 3 (soát lại có phạm vi): `git diff 5b190db a986362` (rỗng: chỉ viết lại tiêu đề commit đầu nhánh, chưa push; cây `83f5e165570320358acc04190c735aa27afef445` ở cả hai)
- Vòng: 3 (hai vòng sửa; trần `max_rework` = 3)
- Verdict: approve (vòng 3); merge `e0bd5c3` trên `team/FEAT-007`. Sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_knowledge `Ran 40 tests in 2.569s OK`, test_architecture `Ran 183 tests in 27.729s OK`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — changes-requested

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau `e545697`), `MIGRATE_EXIT=0`: `ERROR: test_unreadable_file_skipped_and_logged (erp_ai.agent.test_knowledge.TestManuals.test_unreadable_file_skipped_and_logged)` `PermissionError: [Errno 13] secret-detail-mn: '/tmp/tmpw8h4c6cn/apps/myapp/docs/a.md'`, `Ran 40 tests in 1.143s FAILED (errors=1)`. GREEN @ `a538b11`, `MIGRATE_EXIT=0`: test_knowledge `Ran 40 tests in 1.105s OK`, test_architecture `Ran 182 tests in 15.818s OK`.
- Lớp 1: mọi tiêu chí làm đủ: `list(_sections(path))` trong `try`; chỉ bắt `OSError`; log `frappe.logger(source.LOGGER_NAME).warning("search_manuals skipped %s: %s", document, type(error).__name__)` rồi `continue`; không đổi chữ ký, dạng trả, `_manual_files`, `_sections`, hằng; không tên mới. Một câu docstring và một chú thích thêm không vượt tiêu chí (STD-DOC-7). RED đúng lý do.
- Checklist (10): 1 đạt; 2 đạt; 3 KHÔNG đạt (xem major); 4 đạt (`TempAppsRoot` vá `get_source_root` sang thư mục tạm, không đọc kho thật; `manuals_dir` đặt qua `set_agent_settings` + `keep_agent_settings`); 5 đạt; 6 đạt (`assertNotIn(self.sandbox.root)`, `assertNotIn(marker)`); 7 đạt; 8 đạt kèm minor; 9 đạt; 10 đạt.
- Đột biến lần theo bằng đọc mã, đều đỏ: bỏ `try`; `except Exception`; bỏ `list()`; `break`/`return` thay `continue`; không log hoặc `.info`; tên logger khác; đường dẫn tuyệt đối, `str(error)`, `repr(error)` trong log.

Findings:

- major | STD-TEST-8 | erp_ai/agent/test_knowledge.py:540,551 | Catching all of `OSError` and logging `type(error).__name__` are not tested: every case raises `PermissionError`. The `error_class` parameter of `run` is never given another value, and line 551 checks the hard-coded string `"PermissionError"`. So `except PermissionError:` with the name `"PermissionError"` typed into the log stays green on every test. That brings back the whole-search failure for the very case the design names (`design-w1b-fixes-1.md:67`: a file deleted between the walk and the read raises `FileNotFoundError`, and an I/O error raises `OSError`). | Change line 551 to `self.assertIn(error_class.__name__, line)`. Add a subtest `run({"a.md"}, FileNotFoundError)` that expects `[("b.md", 1)]` and one line containing `FileNotFoundError`. A bare `OSError` case is also worth adding. Both go red under the mutation above.
- minor | — | — | 3 small points, dev's call: (a) STD-STYLE-4 `knowledge.py:97`: the reflowed docstring line is 190 characters. The rest of the file wraps at 110. E501 is ignored and ruff-format does not rewrap docstrings, so lint will not flag it. (b) STD-TEST-8 `test_knowledge.py:559,565`: `assertIn("a.md", …)` cannot tell the manuals-relative `document` apart from `os.path.basename(path)` or from the path relative to the source root (`myapp/docs/a.md`). Neither is absolute, so both mutations stay green. Put the unreadable file in a subfolder (`sub/a.md`) and assert the whole log line. (c) STD-STYLE-5: the unused `error_class` parameter goes away once the major is fixed.

Mục "không kiểm được từ diff" của reviewer: (1) `frappe.logger(source.LOGGER_NAME)` gọi trong khối `except OSError` (`knowledge.py:116`); `source._logger()` (`source.py:17-24`) tồn tại vì file log không mở được không được thay lỗi của nơi gọi; nếu `frappe.logger` ném ở đây thì cả lần tìm lại hỏng, đúng điều T172 định chặn. Thiết kế và dòng Returns đòi rõ `frappe.logger(...)`, `_logger` là hàm riêng, nên không phải finding với dev; tech-lead hoặc designer quyết có cần việc nối không. (2) Reviewer không chạy test. (3) Lint chưa chạy trên hai file.

## Vòng 2 — changes-requested (soát lại có phạm vi, `a538b11..5b190db`)

- Bằng chứng của dev (đưa nguyên văn cho reviewer): đột biến 1 (`except PermissionError:` và tên viết cứng, không commit): `ERROR: … [FileNotFoundError]` `FileNotFoundError: [Errno 2] secret-detail-mn: '/tmp/tmpga8khtcy/apps/myapp/docs/sub/a.md'`; `ERROR: … [OSError]` `OSError: [Errno 5] secret-detail-mn: …`; `Ran 40 tests in 1.204s FAILED (errors=2)`. Đột biến 2 (giữ `except OSError`, ghi tên viết cứng): `AssertionError: Lists differ: ['search_manuals skipped sub/a.md: PermissionError'] != ['search_manuals skipped sub/a.md: FileNotFoundError']`, tương tự cho `OSError`; `Ran 40 tests in 1.325s FAILED (failures=2)`; rồi `git restore`. GREEN @ `5b190db`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_knowledge `Ran 40 tests in 1.277s OK`, test_architecture `Ran 182 tests in 16.199s OK`.
- major STD-TEST-8: ADDRESSED. `test_knowledge.py:557-566` chạy cùng ca làm subtest cho `PermissionError`, `FileNotFoundError`, `OSError` trần (EACCES/ENOENT/EIO), mỗi cái chờ `[("b.md", 1)]` và đúng dòng `f"search_manuals skipped sub/a.md: {name}"`.
- minor (a): ADDRESSED (`knowledge.py:96-99`). minor (b): ADDRESSED (`test_knowledge.py:528,566`, `:568-576`; thứ tự do `subdirs.sort()`, `sorted(files)` ở `knowledge.py:136,137`). minor (c): ADDRESSED (`test_knowledge.py:533,541`).
- Checklist mục 1-9 đạt với phần sửa; mục 10: commit `8fdd775` đạt, commit `5b190db` không đạt.

Findings mới:

- major | STD-NAME-5 | commit 5b190db | The type `style` is not one the kit accepts. `teamlib.py:28` `COMMIT_RE` and `skills/commit/SKILL.md:107` allow only `feat\|fix\|refactor\|docs\|test\|chore\|ci\|build\|perf`, so this message fails a level-3 hook rule. In the 40 commits on `team/FEAT-007` the types are feat, fix, test, refactor and docs. Across the whole repo, `5b190db` is the only `style(` commit. Task commits do reach `team/FEAT-007` history (15 `test(...)` commits appear there), so this one would too. | The commit is not pushed, so rewording it does not break STD-GIT-4. Reword to `docs(knowledge): rewrap the search_manuals docstring to the file's width (FEAT-007)`, or `refactor(knowledge): …`, then re-point the review range at the new head. No code change.
- minor | — | — | 1 small point: STD-STYLE-5 `test_knowledge.py:551-553`: the per-line `assertNotIn(sandbox.root/marker)` loop is now implied by the exact-line checks. It does no harm and still guards future callers of `run`. | dev's call

Ngoài phạm vi (deferred): không. Không kiểm được: reviewer không chạy test; không có đầu ra `pre-commit run --all-files`; hook STD-NAME-5 đã để `5b190db` đi qua, tech-lead nên xem hook commit có nối cho worktree task không.

## Vòng 3 — approve (soát lại có phạm vi, chỉ tiêu đề commit)

- Bằng chứng của dev (đưa nguyên văn cho reviewer): `git log --format='%h %s' a538b11..HEAD`: `a986362 docs(knowledge): rewrap the search_manuals docstring to the file's width (FEAT-007)` / `8fdd775 test(knowledge): pin OSError subclasses and the full log line for an unreadable manual (FEAT-007)`; `git diff 5b190db HEAD` không in gì; không chạy lại test (cây giống hệt vòng 2).
- major STD-NAME-5 (commit `5b190db`): ADDRESSED. Đầu mới `a986362`, type `docs` hợp lệ; cùng cha `8fdd775`, chỉ tiêu đề đổi; `5b190db` không còn trên nhánh nào; `a986362` chỉ ở nhánh local, không remote nào có, nên viết lại không phạm STD-GIT-4.
- minor STD-STYLE-5 (`test_knowledge.py:551-553`): NOT ADDRESSED, dev quyết từ vòng 2, không chặn.
- Cây: `5b190db^{tree}` và `a986362^{tree}` cùng là `83f5e165570320358acc04190c735aa27afef445`; hai lệnh diff không in gì.
- Bốn tiêu đề commit của `caa555a..a986362` đạt STD-NAME-5; STD-GIT-8: bốn thân commit rỗng, không trailer.
- Finding mới: không.
- Không kiểm được: khi merge, kiểm rằng nhánh mang `a986362` chứ không phải `5b190db`; reviewer không chạy test.

## Kết luận của tech-lead

- Chạy test và commit được merge: xem dòng progress của T172 trong `tasks.md` (sau merge, một lần giữ khóa có `migrate`; `git log` của merge nêu `a986362`).
- `frappe.logger` có thể ném trong khối `except` (vòng 1, mục không kiểm được (1)): không phải chỗ hở của T172 so với dòng task (Returns đòi đúng lời gọi đó); chuyển designer quyết có cần task nối dùng lối dự phòng như `source._logger()`; ghi ở dòng DỪNG lượt 15.
- Hook commit trong worktree dev không chặn type `style` (chỉ cảnh báo sau commit, theo báo cáo của dev): ghi cho team-leader, cùng loại với ghi nhận "hook git không chạy trong worktree dev" của lượt 14.
- minor còn lại (vòng 2): không mở vòng sửa.
