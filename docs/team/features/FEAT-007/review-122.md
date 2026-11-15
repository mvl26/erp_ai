Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 122 — FEAT-007 T122

- Diff: `git diff f300d0b..team/FEAT-007-task-122` (đầu `2b918c4`, 1 commit, 1 file +40/−1)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `70b2df7` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ; chỉ bỏ hai dòng cuối (dòng STD-short đã đọc, bộ nhớ riêng của reviewer).

## Vòng 1 — approve

- Bằng chứng của dev: RED: 10 × `AssertionError: 0 not greater than 0 : scanner missed the violation`, rồi `Ran 114 tests in 3.502s`, `FAILED (failures=10)`. GREEN: `MIGRATE_EXIT=0`, `erp_ai.tests.test_architecture`: `Ran 114 tests in 3.498s`, `OK`.

### Báo cáo của reviewer (nguyên văn)

Verdict: approve

reviewer -> tech-lead | FEAT-007 T122 | approve
Diff: 1 commit, 1 file (`erp_ai/tests/test_architecture.py`, +40/−1). All 10 checklist items covered.

**Layer 1:**
- **Criteria met.** The rule reports every `frappe.qb` attribute reference (alias-resolved), every import of `frappe.query_builder` or its submodules, and `from frappe import qb`. These lines do it: `erp_ai/tests/test_architecture.py:642-649`.
- **Tests match the Expect line.**
  - `test_tools_never_bypass_permissions_flags_query_builder` (:2479-2486) covers design-w0-fixes-5 point 1 (a)–(c) plus 7 more forms. Each form is checked for the exact line and `ADR-034`.
  - `test_query_builder_outside_tools_allowed` (:2488-2493) covers the scope boundary.
  - `test_tools_never_bypass_permissions` (real code, :1922) is unchanged.
- **Touchpoints respected.** No product code is edited and nothing is added beyond the task.

**Findings:** none at blocker or major level.

minor | — | — | 3 small points: (1) the rule misses `frappe.local.qb` (and `from frappe import local` then `local.qb`). In frappe version-15 that is the same object, set at `frappe/__init__.py:183,258`. It also misses `getattr(frappe, "qb")` and a local rebinding like `f = frappe; f.qb`. None of these is an ordinary way to write it, and the existing rules also miss dynamic access. (2) `from frappe.query_builder import DocType` gives two violations for one line, because `imported_modules` yields both `frappe.query_builder` and `frappe.query_builder.DocType`. It is harmless noise. (3) Imports under `if TYPE_CHECKING:` that exist only for type hints are also flagged. That is consistent with the design ("every `from frappe.query_builder import ...`"), but say so in the docstring if it is intended. | dev's call

**Bypass and false-positive check (from the code at 2b918c4):**
- **Caught and tested** (one red sub-case each in `QUERY_BUILDER_SOURCES`, :2467-2476):
  - `import frappe as f; f.qb`, through `import_aliases` + `resolved_name`
  - `from frappe import qb`, through `target == "frappe.qb"`
  - `import frappe.query_builder [as x]`
  - `from frappe.query_builder.functions import ...`, through `module_in` prefix + "."
  - bare `builder = frappe.qb`
- **Not tested but caught:** `from frappe import qb as q`.
- **Each sub-case would fail if its part were removed:**
  - the import branch (sources 3, 7–10)
  - the Attribute branch (1, 2, 4–6)
  - the `== "frappe.qb"` disjunct (7)
  - alias resolution (6)
  - the `module_in` prefix (10)
- **False positives:**
  - The exact match `== "frappe.qb"` ignores other objects' `.qb` attributes, strings and comments.
  - `module_in` will not match `frappe.query_builder_x`.
  - Relative imports cannot resolve to `frappe.*`.
- **Path test is exact:** `scoped` uses `startswith("agent/tools/")` (:410, :52). The outside test pins `agent/tools_x.py`, `agent/toolset/x.py`, `eval/agent/tools/x.py` and `agent/system_read.py`. Changing the prefix to `agent/tools` or to `"tools/" in rel` would turn it red.
- **No other route:** `frappe/database/database.py` (v15) has no `frappe.db.query` query builder, so there is no second route there.

**Checklist:**
1. Pass. Spec fully done, nothing extra: rule at :642-649, tests at :2465-2493. The task's Returns and Expect lines and design point 1 are all covered.
2. Pass. The only file is the touchpoint `erp_ai/tests/test_architecture.py`, and no new file was added.
3. Pass. RED in the package: 10 × "scanner missed the violation", FAILED (failures=10), which matches the 10 sub-cases in `QUERY_BUILDER_SOURCES`. GREEN: 114 tests OK. Edge cases are covered (aliases, submodules, scope boundary). No skip or xfail in the diff.
4. Pass. No existing assertion changed. `test_tools_never_bypass_permissions` (:1922) and the `agent/runner.py` negative test (:2462-2463) are intact. The tests are pure AST checks on literal strings, so they do not depend on run order, time or the network.
5. Pass (N/A). Test-only code with no error handling, no boundary input and no external calls. `parse` raises on bad source, which is correct for a scanner.
6. Pass. No secrets and no `protected_paths`. The change tightens ADR-005/ADR-034 authorization (tools may not use the query builder, which checks no permission).
7. Pass. The function signature `check_tools_never_bypass_permissions(sources) -> list` is unchanged. Only the violation strings were added.
8. Pass. Names are snake_case or UPPER constants, matching the file. The change reuses existing helpers (`import_aliases`, `imported_modules`, `module_in`, `resolved_name`) rather than duplicating them (STD-DESIGN-4). The docstring was updated (:637-638). No dead code.
9. Pass (N/A). No new dependency.
10. Pass. Commit `2b918c4 test(architecture): tools may not use frappe.qb or import frappe.query_builder (FEAT-007)` has no body and no Co-Authored-By or Claude trailer. The branch is `team/FEAT-007-task-122`, one task per commit. No user-visible documentation change is needed.

**Not verifiable from the diff:**
- Green on the real code base after merge into `team/FEAT-007`. The task says `git grep "frappe\.qb\|frappe\.query_builder" -- erp_ai/agent/tools/` returns 0 lines (2026-11-15). Tech-lead should re-run `cmd.test_one erp_ai/tests/test_architecture.py` after the merge.
- Merge order: T122 must merge before T56 and must not run in the same round as any other task touching `test_architecture.py`. Tech-lead to check the build order.
- The `design.md:487` text change belongs to a different owner (design), not this diff.
- The lint claim that `pre-commit` exited 1 only because of base debt in `erp_ai/test_change_decision.py` is not shown in the package beyond dev's statement.

**Git commands used (read-only):**
- `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-007 log --format='%h %an %s%n%b' f300d0b..2b918c4`
- `git -C <same> diff --stat f300d0b..2b918c4`
- `git -C <same> diff f300d0b..2b918c4`
- `git -C <same> show 2b918c4:erp_ai/tests/test_architecture.py` (helpers at :52, :406-500, the rule at :632-670, tests at :1922, :2194, :2462-2493)
- One targeted read of the frappe v15 source to check the `frappe.local.qb` route.

Tests were not run, as instructed. To check: `cmd.test_one erp_ai/tests/test_architecture.py`.

## Kết luận của tech-lead (mục "không kiểm được")

- Xanh trên mã thật sau merge: một lần giữ khóa site từ worktree `feat-007` trên `70b2df7` (đã có T22, T121), `MIGRATE_EXIT=0`; `test_architecture` `Ran 114 tests in 3.500s OK`. Chạy lại trên `1cc3f42` (sau T20): `Ran 114 tests in 3.459s OK`. Đạt.
- Thứ tự merge: T122 đã merge trước T56; trong các vòng 61–63 không task nào khác có `erp_ai/tests/test_architecture.py` trong `files:` (T20, T22, T60, T121 chỉ chạy module đó). Đạt.
- Chữ `design.md:487`: việc của designer hoặc As-Built, chuyển team-leader (không chặn).
- Lint: tech-lead chạy `cmd.lint` trên `70b2df7`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền; đã trả lại file). Đạt.
- Ba minor (deferred): `frappe.local.qb` và truy cập động chưa bắt; một dòng import ra hai vi phạm; import dưới `TYPE_CHECKING` cũng bị bắt. Điểm đầu chuyển team-leader để cân nhắc khi lập luật kiến trúc của U6b.
