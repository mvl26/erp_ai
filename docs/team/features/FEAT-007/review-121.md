Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 121 — FEAT-007 T121

- Diff: `git diff f300d0b..team/FEAT-007-task-121` (đầu `48cc793`, 1 commit, 3 file +68/−4)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `f8cfaa0` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ; chỉ bỏ dòng cuối về bộ nhớ riêng của reviewer.

## Vòng 1 — approve

- Bằng chứng của dev: RED `test_source`: `AssertionError: '/tmp/tmp69sireis/apps/myapp/docs/new.md' is not None`; 7 subtest của `test_new_path_inside_manuals_refused` (file mới, thư mục con có sẵn, thư mục lồng chưa có, dấu `/` cuối, `./`, `vi/../`, đường dẫn tuyệt đối) và 3 của `test_new_path_via_symlink_into_manuals_refused` (`docs_link/new.md`, `docs_link/new_dir/new.md`, `ghost_link.md` treo); `Ran 122 tests in 4.389s` / `FAILED (failures=10)`. RED `test_change_guard`: `AssertionError: None != 'đường dẫn không hợp lệ hoặc nằm ngoài apps/'` ×2; `Ran 36 tests in 1.515s` / `FAILED (failures=2)`. GREEN một lần giữ khóa: `MIGRATE_EXIT=0`; `test_source` `Ran 122 tests in 4.423s` OK; `test_change_guard` `Ran 36 tests in 1.491s` OK; `test_erp_ai_setting` `Ran 93 tests in 6.484s` OK; `test_architecture` `Ran 112 tests in 3.420s` OK.

### Báo cáo của reviewer (nguyên văn)

Verdict: approve

reviewer -> tech-lead | FEAT-007 T121 | approve
Diff: the range has 1 commit (48cc793) and 3 files, +68/−4. Checklist 10/10 covered. Layer 1: every Returns and Expect item is met, edits stay in the touchpoints, and the forbidden files are untouched.

Git commands run (read-only):
- `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 log --format='%h %s%n%b' f300d0b..48cc793`
- `git -C <same> diff --stat f300d0b..48cc793`
- `git -C <same> diff f300d0b..48cc793`
- `git -C <same> show 48cc793:erp_ai/agent/tools/source.py`
- `git -C <same> show 48cc793:erp_ai/agent/tools/change_guard.py`
- `git -C <same> show 48cc793:erp_ai/agent/tools/test_source.py`
- `git -C <same> show 48cc793:erp_ai/agent/tools/test_change_guard.py`
- `git -C <same> show 48cc793:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`
- `git -C <same> show 48cc793:erp_ai/test_utils.py`
- `git -C <same> grep -n "resolve_safe_path\|_base_resolve(" 48cc793 -- 'erp_ai/*.py'`

Findings (blocker/major): none.

minor | — | — | 2 small points: (1) the class docstring at test_source.py:2328 still says only "files inside the manuals directory are not source"; it should now also cover paths that do not exist yet. (2) test_source.py:2357 is a long comment line (pre-commit passed). | dev's call

Checklist:
1. pass. source.py:146 changes `isfile` to `not isdir`, which is what the Returns line asks for: refuse an existing file or a path not yet on disk, including inside a subdirectory that does not exist; `manuals_root()` and existing subdirectories still resolve; the comparison uses the real path (`_base_resolve` and `manuals_root` both call realpath, source.py:112,126). The signature is unchanged, there is no new error code, and nothing extra was added.
2. pass. Only source.py, test_source.py and test_change_guard.py changed. `change_guard.py`, `knowledge.py`, `resolve_manual_path` and `manuals_root` are untouched, and no new files were added.
3. pass. The pasted RED output names the 10 failing subtests in test_source and the 2 in test_change_guard; GREEN follows. Edge cases tested at test_source.py:2368-2409:
   - a new file, a new file in an existing subdirectory, a nested directory that does not exist
   - trailing slash, `./`, `vi/../`, an absolute path
   - prefix confusion: `docs-other/new.md` and `docsnew.md` still resolve
   - `docs/../new.md` still resolves
   - a symlink pointing into the store, including a new subdirectory under it
   - a dangling `ghost_link.md`
   - a symlink inside the store pointing out of it, which still resolves
   - `read_source` refusal

   Removing the behavior turns these tests red: reverting to `isfile` fails the new-path subtests, and dropping `_inside` or `not isdir` fails the decoys or the existing-subdirectory assertions. No skip or xfail was added.
4. pass. In test_source.py:2357 only the comment changed; the assertions in the existing tests are unchanged. The new change_guard test (test_change_guard.py:246-262) undoes its settings change with `addCleanup(frappe.db.rollback)` plus `keep_agent_settings`, and runs in a temp root (`TempAppsRoot`) with `read_git=False`. Symlinks are created only under that temp root.
5. pass. I checked every caller on the task head that can now get `None`:
   - `change_guard.check_write_path` (change_guard.py:151,170) falls through to the existing branch `full is None` → `PATH_INVALID`, which is the intended effect.
   - `read_source` (source.py:165) already gave the same refusal text for `None` and for "not a file", so the user sees no change.
   - `search_source` (source.py:233) walks existing files, so the only extra refusal is a dangling link inside the store (stricter).
   - `_git_path_ok` / `_git_args_ok` (source.py:258,296): `git log -- <path deleted from disk inside the store>` is now refused. This is stricter and matches AC-47; blame already required an existing file.
   - `check_manuals_dir` (erp_ai_setting.py:317) already required `isdir`, and existing directories still resolve (E-7).
6. pass. This closes the write path into the manuals store: new files, new subdirectories, and symlinks or dangling links pointing in (test_change_guard.py:252-258). There are no secrets, no injection surface, and no `protected_paths` touched.
7. pass. Callers see a stricter rule but the same contract: the return type is still str or None, and the error code is the existing `PATH_INVALID`. No migration is needed.
8. pass. The new names follow the existing ones (`PATH_INVALID_REFUSAL` at test_change_guard.py:24, `test_new_*` tests), and the docstring at source.py:140-142 matches the code. No dead code.
9. pass. No new dependency. The `import frappe` in test_change_guard.py:5 is used for rollback.
10. pass. The commit message is `fix(source): refuse new paths inside the manuals store in resolve_safe_path (FEAT-007)` with an empty body and no `Co-Authored-By` trailer. The branch is `team/FEAT-007-task-121` and this is one task in one commit.

Not verifiable from the diff:
- The post-merge runs of test_source, test_change_guard, test_erp_ai_setting and test_architecture. I ran no tests; the green results come only from dev's pasted output. Tech-lead runs them after merge.
- The text replacements at design.md:492 and :308 required by design-w0-fixes-4 point 5. design.md is not a touchpoint of this task; tech-lead should check whether designer has done them.
- The remaining risk named in the design: if `manuals_dir` is saved but the directory is deleted from disk, `manuals_root()` returns None and nothing is excluded. It is still open whether the change_guard apply job creates parent directories. Tech-lead should check, and pass it to architect if it does.
- Changing files on disk between the check and the apply step (TOCTOU, e.g. creating a symlink after the proposal check) is outside this diff. The apply job does call `check_write_path` again, with `read_git=False`.

## Kết luận của tech-lead (mục "không kiểm được")

- Test sau merge: một lần giữ khóa site từ worktree `feat-007` trên `f8cfaa0` (đã có T22), `MIGRATE_EXIT=0`; `test_source` `Ran 122 tests in 4.224s OK`; `test_change_guard` `Ran 36 tests in 1.207s OK`; `test_erp_ai_setting` `Ran 93 tests in 5.911s OK`; `test_architecture` `Ran 112 tests in 3.437s OK`. Sau merge T20 (`1cc3f42`): `test_source` `Ran 122 tests in 6.829s OK`, `test_erp_ai_setting` `Ran 101 tests in 6.887s OK`. Đạt.
- Chữ `design.md:492`, `:308`: chưa sửa trong `design.md` (`design-w0-fixes-4.md` thắng ở đúng hai dòng đó, và `tasks-w1.md` ghi "hai file thiết kế đó không được chép vào `design.md`; task dẫn thẳng tới chúng"). Chuyển team-leader vào danh sách chữ cần sửa khi viết As-Built. Không chặn.
- Rủi ro còn lại của thiết kế (`design-w0-fixes-4.md:73`: `manuals_dir` đã lưu mà thư mục bị xóa khỏi đĩa): tech-lead kiểm bằng `git grep -n "makedirs\|mkdir" <ref> -- erp_ai ':!*test*'` trên `team/FEAT-007` @ `70b2df7` và trên `develop` @ `2fd42ad`: 0 dòng ở cả hai. Theo phép kiểm đó, mã áp thay đổi không tự tạo thư mục cha bằng hai lời gọi này. Phép kiểm chỉ tìm hai tên hàm; job áp của FEAT-004 nằm ở `develop` và chưa vào nhánh, nên kiểm lại sau T56 (ví dụ lời gọi `git` tự tạo thư mục khi áp patch). Chuyển team-leader; chưa đủ căn cứ để gọi architect.
- TOCTOU giữa lúc kiểm và lúc áp: ngoài phạm vi task; job áp gọi lại `check_write_path` (reviewer đã nêu). Chuyển team-leader như một điểm cho `/team:verify` của FEAT-004/U6b, không chặn.
- Hai minor (deferred): docstring lớp test `test_source.py:2328`; dòng comment dài `:2357`.
