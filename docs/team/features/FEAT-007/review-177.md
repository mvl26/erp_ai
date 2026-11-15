Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 177 — FEAT-007 T177

- Diff: `git diff 09b5438..f3d6cad` (nhánh `team/FEAT-007-task-177`; 2 commit `b6d5cb2` test, `f3d6cad` mã; 2 file +26/−1, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn. Ghi trước khi merge.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `b6d5cb2`, cùng lần giữ khóa với migrate: `MIGRATE_EXIT=0`; `ERROR: test_unreadable_file_logged_even_when_log_file_fails (erp_ai.agent.test_knowledge.TestManuals.test_unreadable_file_logged_even_when_log_file_fails)`; `PermissionError: [Errno 13] log`; `Ran 41 tests in 1.305s` / `FAILED (errors=1)`. GREEN, một lần giữ khóa: `MIGRATE_EXIT=0`; `erp_ai.agent.test_knowledge`: `Ran 41 tests in 1.268s` / `OK`; `erp_ai.tests.test_architecture`: `Ran 185 tests in 16.945s` / `OK`.

Các phép kiểm chính của reviewer (theo thứ tự lời giao, dùng 5/12 lượt):

1. Commit: 2 file, +26/−1. Commit test `b6d5cb2` (chỉ file test) đứng trước commit mã `f3d6cad` (chỉ `knowledge.py`); hai tiêu đề đúng `type(scope): description (FEAT-007)`, không dòng ghi công. `source.py` không đổi (diff 0 dòng).
2. `knowledge.py:117` là dòng duy nhất đổi: `frappe.logger(source.LOGGER_NAME).warning(` thành `source._logger().warning(`. Chuỗi thông điệp, `document`, `type(error).__name__` và chú thích dòng trên giữ nguyên. `frappe` còn được dùng ở dòng 61 và 66 nên import không chết. Sửa dùng lại lối dự phòng có sẵn, không chép (STD-DESIGN-4).
3. Test mới (`test_knowledge.py:583-606`) khớp dòng Expect ở mọi điểm: hai bản vá, `assertLogs(knowledge.source.LOGGER_NAME, "WARNING")`, hai giá trị chờ viết cứng. Đỏ nếu trả lại sửa (RED của dev xác nhận); cũng đỏ nếu sửa nuốt lỗi log mà không ghi (không bản ghi nào tới `assertLogs`) hoặc ghi thông điệp khác. Vá `frappe.logger` ném lỗi giữ file log thật của site ngoài test; `assertLogs` tự đặt mức và handler nên không phụ thuộc thứ tự test (STD-TEST-6). Test có sẵn `test_unreadable_file_skipped_and_logged` không sửa (diff chỉ thêm dòng sau dòng 581). Không dấu skip.
4. `source._logger()` ở đầu nhánh: gọi `frappe.logger(LOGGER_NAME)` qua thuộc tính module `frappe`; ném bất kỳ ngoại lệ nào thì lùi về `logging.getLogger(LOGGER_NAME)`. `knowledge.frappe` là cùng một đối tượng module nên bản vá tới được `source`.
5. Còn lại: file lỗi vẫn bị bỏ kèm lý do có log, file log hỏng không còn thoát khỏi khối `except` (STD-ERR-1); log không có đường dẫn tuyệt đối, không `str(error)`; không bí mật, không chạm `protected_paths`; dạng trả của `search_manuals` không đổi; tên theo profile, không phụ thuộc mới.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 1 small point: the new test does not check that `frappe.logger` is tried before the fallback. The existing `test_unreadable_file_skipped_and_logged` already covers that with `assert_called_with`, so nothing is missing overall | dev's call

Mục "không kiểm được từ diff" của reviewer:

- pre-commit qua ở cả hai commit: gói lời giao không có đầu ra pre-commit, chỉ có ghi chú ở dòng tiến độ.
- Lần GREEN có đúng trên `f3d6cad` không: reviewer dựa vào dòng dev dán, không chạy test. Đề nghị: `cmd.test_one erp_ai/agent/test_knowledge.py`.

## Kết luận của tech-lead

- Merge `48e4477` trên `team/FEAT-007` (sau khi file này có verdict và T176 đã tick). Chạy test sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_knowledge `Ran 41 tests in 1.143s OK`, test_architecture `Ran 185 tests in 16.565s OK`. Cây sau merge chứa đúng `f3d6cad` cộng T176 (không chung file), nên lần chạy này trả lời mục "GREEN có đúng trên `f3d6cad` không".
- pre-commit: KHOẢNG TRỐNG THẬT, tính là một lần review trượt. `cmd.lint` cả cây @ `32fa2bb` (một dev chạy sau merge T32): `LINT_EXIT=1`, hook ruff-format định dạng lại `erp_ai/agent/knowledge.py` (lời gọi log ở `:117-119` chia ba dòng). Repo không cài hook pre-commit nào (`.git/hooks` chỉ có file mẫu, `core.hooksPath` không đặt), nên câu "commit đi qua hook" của tech-lead ở trên dòng này lúc 14:27 là sai. Tick T177 đã gỡ lúc 14:30; vòng sửa 1/3 dưới đây.

## Vòng 2 — soát lại phạm vi sửa, approve

- Finding của vòng 1 (tech-lead nêu sau `cmd.lint`, đưa nguyên văn cho dev và reviewer): `major | STD-STYLE-1 | erp_ai/agent/knowledge.py:117 | the call source._logger().warning("search_manuals skipped %s: %s", document, type(error).__name__) is split over 3 lines (:117-119); the profile's formatter (pre-commit hook "Run ruff formatter", ruff-format v0.8.1) rewrites it onto one line (1 insertion, 3 deletions), so cmd.lint exits 1 on the feature branch | format the file with the profile's formatter and commit the result`
- Diff: `git diff 32fa2bb..ac8386b` (nhánh `team/FEAT-007-task-177` tua nhanh lên `32fa2bb`, một commit `ac8386b fix(knowledge): format the search_manuals log call with the profile formatter (FEAT-007)`; 1 file +1/−3).
- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `32fa2bb`: `Run ruff formatter...Failed`; `- hook id: ruff-format`; `- files were modified by this hook`; `1 file reformatted, 145 files left unchanged`; `LINT_EXIT=1`. GREEN trên `ac8386b`: 12 hook `Passed`, `LINT_EXIT=0`, `git status --short` rỗng; một lần giữ khóa: `MIGRATE_EXIT=0`; test_knowledge `Ran 41 tests in 1.621s OK`; test_architecture `Ran 185 tests in 25.333s OK`.
- Reviewer (2/6 lượt): STD-STYLE-1 `knowledge.py:117` ADDRESSED: lời gọi ba dòng nay một dòng; chuỗi `"search_manuals skipped %s: %s"`, `document`, `type(error).__name__` khớp từng byte; chú thích `:116` là dòng ngữ cảnh không đổi; hành vi giữ nguyên. Dòng dài 92 ký tự kể 3 tab (khoảng 101 cột nếu tab tính 4), dưới `line-length = 110` (`pyproject.toml:31`). Một commit, một file, tiêu đề khớp mẫu, không dòng ghi công. Finding mới: không. Ngoài phạm vi: không.
- "Không kiểm được từ diff" của reviewer: `pre-commit run --all-files` và hai module test có xanh không (chỉ có đầu ra của dev).

## Kết luận của tech-lead (vòng 2)

- Merge `ed341b9` trên `team/FEAT-007` (sau verdict vòng 2). Test sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_knowledge `Ran 41 tests in 2.169s OK`, test_architecture `Ran 185 tests in 28.436s OK`. Tick lại T177: 83/178. Cây sau merge trùng cây `ac8386b` (nhánh task đã tua nhanh lên đầu nhánh feature trước khi sửa), nên `LINT_EXIT=0` của dev trên `ac8386b` là kết quả `cmd.lint` cả cây của đầu nhánh feature.

## deferred

- minor (1): test mới không kiểm `frappe.logger` được thử trước lối dự phòng; test có sẵn đã phủ → không việc.
