Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 39 — FEAT-007 T39

- Diff: `git diff 7d10d0f..team/FEAT-007-task-39` (vòng 1: 1 commit `1413512`, 2 file +249/−2)
- Vòng: 2 (trần `max_rework` = 3); vòng 2: `git diff 1413512..4dd4119`
- Verdict: approve (vòng 2); merge `83241c1` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — request-changes

- Bằng chứng của dev: RED với hàm giả trả `[]`: `Ran 35 tests`, `FAILED (failures=16, errors=2)`, `AssertionError: [] is not None` (`test_unconfigured_none`), `AssertionError: Lists differ: [] != [{'document': 'sub/hdsd.md', 'heading': 'L[57 chars]58'}]` (`test_match_returns_document_heading_line`); `test_no_match_empty` xanh với hàm giả. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_knowledge` `Ran 35 tests in 1.559s OK`; `test_architecture` `Ran 112 tests in 4.204s OK`.

### Báo cáo của reviewer (nguyên văn)

**Tier 1 (does the diff match the spec?):** Yes. Nothing is missing, nothing extra and nothing misunderstood.
- **Constants and signature:** `search_manuals(query, limit, manuals_dir)` matches `design.md:491` and AC-47. The three constants are 500 files, 1 MiB and 10 s, and each is pinned by a test that also checks the boundary.
- **Sections:** a section is cut at lines starting with `#`. An indented `#` does not start a section, and text before the first heading is a section with an empty heading.
- **Inputs from earlier tasks:** files are read only through `source.resolve_manual_path` (from T38), and the query goes through `tokenize` (from T37).
- **Excerpt:** it is masked first and cut after (3a of `design-w0-fixes-3.md`), and it comes out in NFC.
- **Required tests:** the three Expect tests are present under `TestManuals` with the exact names.
- **Touchpoints:** only `erp_ai/agent/knowledge.py` and `erp_ai/agent/test_knowledge.py` changed.
- **Dev's two concerns:** neither is a finding. (1) The keyword-only `clock=time.monotonic` follows the task convention "truyền `now` thay đồng hồ thật" (STD-TEST-6), and the positional contract is unchanged. (2) If `manuals_dir` is not the configured directory, the function returns `[]`. That matches `resolve_manual_path`, which would refuse every file anyway. The docstring says so, and the U6b tool (`design-addendum-1-U6b.md` 3.3) only turns `None` into a refusal.

### Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/knowledge.py:129 | The `os.path.isfile(full)` check in `_manual_files` is never tested. No `.md` entry in any test is a non-regular file that `resolve_manual_path` still accepts. `link.md` resolves outside the root, so `resolve_manual_path` returns None for it, and `dir_out` is a directory. So deleting `os.path.isfile(full) and` keeps all 35 tests green. Without that check, a dangling symlink inside the manuals directory (e.g. `docs/cu.md -> docs/da-xoa.md`) makes `getsize` raise `FileNotFoundError` and the whole search fails; a FIFO named `x.md` gets size 0 and `open` hangs. | Add a `TestManuals` case: create `os.symlink(<docs>/khong-con.md, <docs>/cu.md)` next to a matching `hdsd.md`, then assert `_found(word) == [("hdsd.md", 1)]` with no error. It should be red with the check removed. | confirmed (read only: tests not run; no case creates such an entry, and the code path is traced above)

minor | — | — | 8 small points, dev's call: (a) The 10 s budget and the 500-file cap are checked only before each `.md` file (`knowledge.py:123-124`). Walking a deep tree or many non-`.md` entries is not bounded. (b) An unreadable `.md` file (a `PermissionError` in `_sections`, `knowledge.py:135`) fails the whole search instead of skipping that one file. (c) Files are read as `utf-8`, not `utf-8-sig`, so a first heading after a BOM is not recognized. (d) The `.MD` (lower-cased extension) branch has no case. Neither does sorted subdirectory order, which decides which 500 files are kept across subdirectories, or the rule that the document name sorts before the line number. (e) The decoy `myapp/khac.md` in `test_only_md_files_inside_the_manuals_dir` cannot be reached by any mutation, because the walk starts at `docs/`. (f) The `search_manuals` docstring does not mention the `EMPTY_QUERY` error (STD-DOC-7). (g) `limit <= 0` is not validated, so a negative value gives a slice of all-but-last. `search_kb_articles` has the same gap, and the tool clamps the value. (h) A NUL byte in `manuals_dir` raises `ValueError` from `realpath` (`knowledge.py:98`) before the NUL check in `_base_resolve` runs. The value comes from settings.

### Review checklist (10)

1. Does exactly what the spec asks (STD-DESIGN-5, STD-TEST-2): **pass**. AC-47 is fully covered. The `clock` seam is required by the task convention, so it is not scope creep.
2. Touchpoints and file placement (STD-DESIGN-1, STD-STRUCT-1/2): **pass**. Two files, both touchpoints, no new files.
3. Failing test first, edges covered, no skip (STD-TEST-1/8/4): **fail**. The failing run is in the package (16 failures, 2 errors against a stub returning `[]`). `test_no_match_empty` was green against the stub, but it would fail if the "only matching sections" check were removed, so it is a real test. No skip markers from `test.skip_markers` appear. The edge case in the major finding is untested.
4. No test bent to wrong behavior; tests independent and repeatable (STD-TEST-5/6): **pass**. Tests use a temporary `TempAppsRoot`, set `set_agent_settings` per test, and call `keep_agent_settings` plus rollback. Words are random through `_word`, and the clock is injected. The boundary values (9.99 vs 10.00 s, 1 MiB vs 1 MiB + 1 byte, cap 2 of 3 files) pin both `>=` and `>`. Ranking: `in_heading` is pinned by `c.md` vs `b.md`, and the line tiebreak by sections at lines 1 and 3. The mask-before-cut order is pinned: the excerpt starts at character 17, inside `[đã che]`. Unmasked text would give an excerpt starting at `fake-mn`.
5. Errors handled, input validated at boundaries, timeouts (STD-ERR-1/2/5): **pass**, with minors (a), (b) and (h).
6. No secrets, no injection, authorization, no sensitive data exposed (STD-SEC-1/3/4/6): **pass**. Paths stay inside the manuals directory through `resolve_manual_path`, and symlinks pointing outside are refused (tested). The excerpt is masked. `heading` is returned unmasked here; see the "not verifiable" section.
7. API and data contracts compatible (STD-DESIGN-3, STD-OPS-2): **pass**. It is a new function with no schema change. `knowledge` imports `tools.source` in one direction only. `tools/__init__` imports only `registry`, which loads tools through `importlib`, so there is no cycle. `str | None` is valid on Python 3.10.
8. Names, structure, style, no dead code (STD-NAME-1/2, STD-STYLE-4/5): **pass**. Constants are upper case, helpers private, and the docstrings match the code (checked for overclaims).
9. Dependencies (STD-DEP-1/3/5): **pass**. Standard library only (`os`, `time`).
10. Commits, branch, PR, documentation (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2): **pass**. Branch `team/FEAT-007-task-39`, one commit `feat(agent): ... (FEAT-007)`. No `Co-Authored-By` trailer. No user-visible documentation is due until U6b.

### Không kiểm được từ diff (vòng 1) — tech-lead xử lý trước khi tick

- **Unmasked `heading`:** `heading` (and `document`) leave `search_manuals` without `redact_secrets`; only `excerpt` is masked. `design-addendum-1-U6b.md` 3.3 says "Mọi chuỗi trả về đi qua `redact.redact_secrets`" at the tool layer, so NFR-6 for `heading` depends on U6b doing that. I read that section; U6b should add a test with a secret in a heading line.
- **Unreadable files:** whether the U6b tool catches `OSError` from an unreadable manual (minor (b)) is outside this diff.
- **Test runs:** tests were not run (reviewer is read-only). To confirm the major and its fix, run: `cd ../.. && bench --site miyano run-tests --module erp_ai.agent.test_knowledge`.

**Read-only commands used:** `git log --oneline 7d10d0f..team/FEAT-007-task-39`, `git diff --stat …`, `git diff …`, `git log -1 --format='%B%n---%an' 1413512`; `git show team/FEAT-007-task-39:` cho `erp_ai/agent/knowledge.py`, `erp_ai/agent/tools/source.py`, `erp_ai/agent/tools/__init__.py`, `erp_ai/agent/tools/registry.py`, `erp_ai/test_utils.py`, `erp_ai/agent/test_knowledge.py`, `.team/profile.json`; `git grep -n knowledge team/FEAT-007-task-39 -- 'erp_ai/*.py'`; grep/sed trên `tasks.md`, `design.md`, `spec.md`, `plan.md`, `design-w0-fixes-3.md`, `design-addendum-1-U6b.md` 3.3, `ADR-034.md`.

## Vòng 2 — approve (scoped re-review)

- Diff: `git diff 1413512..team/FEAT-007-task-39` (đầu `4dd4119`, 1 commit, 1 file `test_knowledge.py` +8; `knowledge.py` không đổi).
- Bằng chứng của dev: RED của đột biến bỏ `os.path.isfile(full) and` (không commit): `ERROR: test_dangling_symlink_inside_the_manuals_dir_skipped (erp_ai.agent.test_knowledge.TestManuals.test_dangling_symlink_inside_the_manuals_dir_skipped)`, `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp3i0prno0/apps/myapp/docs/khong-con.md'`, `Ran 36 tests in 1.404s`, `FAILED (errors=1)`. GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_knowledge` `Ran 36 tests in 1.348s OK`; `test_architecture` `Ran 112 tests in 4.081s OK`.

### Báo cáo của reviewer (nguyên văn)

**Round-1 finding**
- major | STD-TEST-8 | erp_ai/agent/knowledge.py:129 | untested `os.path.isfile(full)` check → **ADDRESSED**. The new test is at erp_ai/agent/test_knowledge.py:418-424 (`TestManuals.test_dangling_symlink_inside_the_manuals_dir_skipped`). It creates `docs/cu.md` as a symlink to a missing `docs/khong-con.md`, places it next to a matching `hdsd.md`, and asserts `_found(word) == [("hdsd.md", 1)]`. This matches the requested fix.

I traced at the head whether the test fails without the check:
- `_base_resolve` (erp_ai/agent/tools/source.py:108-120) runs `realpath`, which returns `<docs>/khong-con.md`. That path is inside the root and has no secret name.
- The extension check there is gated by `os.path.isfile(full)`, so the missing target skips it and `full` is returned.
- `resolve_manual_path` (source.py:130-134) passes it as well, because `_inside(manuals_root, full)` is true.
- So in `_manual_files` (knowledge.py:129), `os.path.isfile(full)` is the only thing between a dangling link and `os.path.getsize(full)`, which then raises `FileNotFoundError`.
- `cu.md` sorts before `hdsd.md` in `sorted(files)`, so the walker reaches the dangling link before the result is built.
- Dev's RED line matches this path: `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/tmp3i0prno0/apps/myapp/docs/khong-con.md'`, `FAILED (errors=1)`. GREEN: `Ran 36 tests ... OK`.

The test pins the guard. The symlink is created inside the per-test sandbox, so the test stays independent (STD-TEST-6).

**New blockers/majors from the fix diff:** none.

**Regressions of round-1 points:** none. The fix diff does not touch erp_ai/agent/knowledge.py, and no existing test was edited or removed.

**Checklist (fix diff only)** 1. Scope: test only, exactly the requested case. OK. 2. Touchpoints: only `erp_ai/agent/test_knowledge.py`, and no new files. OK. 3. Red-then-green evidence came with the handoff, and the test covers the error path. No skip, xfail or only. OK. 4. No assertion was changed, and the test is independent. OK. 5. Error handling: the code is unchanged, and the guard skips the unreadable entry without raising. N/A, OK. 6. Security: no secrets, and the symlink target stays in the sandbox. OK. 7. Contracts: unchanged. N/A. 8. Naming and style: the test name and layout follow the neighbouring tests, and there is no dead code. OK. 9. Dependencies: none added. N/A. 10. Commit: `test(agent): cover dangling symlink skipped in manuals search (FEAT-007)` follows STD-NAME-5 and has no AI trailer (STD-GIT-8). It is on branch `team/FEAT-007-task-39`. OK.

minor | — | — | 0 điểm | —

**Deferred:** none.

**Not verifiable from the diff:** the GREEN runs (test_knowledge 36 OK, test_architecture 112 OK) are dev's output only. I did not run any tests, as instructed (shared site).

**Read-only commands used:** `git log --oneline 1413512..team/FEAT-007-task-39`, `git diff --stat …`, `git diff …`, `git log --oneline 7d10d0f..team/FEAT-007-task-39`, `git diff --stat 7d10d0f..…`, `git log -1 --format='%an%n%B' 4dd4119`; `git show team/FEAT-007-task-39:` cho `knowledge.py` (95-175), `test_knowledge.py` (330-440), `tools/source.py` (100-145); `git grep -n "def resolve_manual_path\|def manuals_root\|def _inside"`.

## Kết luận của tech-lead (trước khi tick)

- Merge `83241c1` (`git merge --no-ff team/FEAT-007-task-39`, 2 file +257/−2, không xung đột). Sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_knowledge` `Ran 36 tests in 1.485s OK`; `test_source` `Ran 120 tests in 6.425s OK`; `test_architecture` `Ran 112 tests in 3.787s OK`. Khớp số của dev. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- `heading`, `document` không qua `redact_secrets`: không phải thiếu sót của T39. `design.md:491` chỉ đòi cắt mục; `design-addendum-1-U6b.md` 3.3 giao việc che mọi chuỗi trả về cho lớp tool của U6b. Ghi cho kế hoạch đợt 1b: task tool của U6b phải có test bí mật nằm trong dòng tiêu đề.
- File HDSD không đọc được (`PermissionError`) làm hỏng cả lần tìm: ngoài tiêu chí AC-47 của task; tool U6b phải bắt `OSError` hoặc task U6b sửa `_sections`. Ghi cho kế hoạch đợt 1b.

## deferred

- 8 điểm minor (a)–(h) của vòng 1, đáng chú ý: (a) ngân sách 10 giây và trần 500 file chỉ kiểm trước mỗi file `.md`; (b) file không đọc được làm hỏng cả lần tìm; (c) BOM; (g) `limit <= 0`.
- Cho U6b (đợt 1b): che `heading`; bắt `OSError`.
