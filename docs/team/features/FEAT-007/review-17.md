Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 17 — FEAT-007 T17

- Diff: `git diff 7d10d0f..team/FEAT-007-task-17` (đầu `10c0407`, 1 commit, 2 file +207/−0)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `fd670a1` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo nguyên văn của reviewer (reviewer chỉ đọc, không ghi file). Phần "Báo cáo của reviewer" giữ nguyên chữ.

## Vòng 1 — approve

- Bằng chứng của dev: RED `Ran 76 tests`, `FAILED (failures=29)`, `AssertionError: None != 'Mục tiêu KPI: stale_over_5_days bị thiếu'`, `AssertionError: None != 'Mục tiêu KPI: không được để trống. Muốn [343 chars]}\n}'`; `test_default_targets_valid` xanh trước khi sửa (test canh). GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 76 tests in 7.191s OK`; `test_architecture` `Ran 112 tests in 3.864s OK`.

### Báo cáo của reviewer (nguyên văn)

**Tier 1 (does it match the spec?):** Yes. Nothing is missing, nothing extra, nothing misunderstood.
- `check_kpi_targets()` is called as validate step 10, right after `check_operation_people()` (step 9), as `design.md:310` orders.
- `KPI_IDS` is imported from `erp_ai.constants`. This follows design-w0-fixes.md:45, which wins over `design.md:198`.
- It requires exactly the 6 KPI keys. Each value must be an object with exactly `gd2` and `gd4`, and each of those must be a finite number ≥ 0. `true`/`false`, strings, `null`, NaN and Infinity are refused.
- Errors use the format `"Mục tiêu KPI: {key path} {reason}"`.
- A blank value (`""`, whitespace or None) is refused. The message includes the default JSON, read from the field meta, as `routing_rules` does.
- The two tests named in Expect exist under those names. They cover a missing key, a negative value, broken JSON and blank, plus unknown keys at both levels, a wrong type, HTML escaping, and the check order against step 9.
- The task stays inside its touchpoints. The `kpi_targets` description at `design.md:180` ("không lưu được") is now true, which closes concern (3) from T16.

**Findings (blocker/major):** none.

**How I tested the tests.** For each line I asked whether removing it would turn a test red. Each of these changes turns at least one case red: dropping the `bool` exclusion; dropping `isfinite`; changing `>= 0` to `> 0` (the `gd2: 0` case catches it); rejecting floats; dropping the `isinstance(dict)` check at either level; dropping either `escape_html` call; checking unknown keys after missing ones; checking all missing keys before any values; dropping the blank branch; not calling the check from `validate`.

The stored value is checked against `good`, a value that differs from the default, so a reset to the default would also show. Expected texts are literal strings (`KPI_ALLOWED`), not built from `KPI_IDS`. The RED count of 29 fits: 25 table cases, 3 blank cases, and the final `_stored()` check after the blank saves.

minor | — | — | 3 small points: (1) the comment at `test_erp_ai_setting.py:1953` says "the first fault in KPI_IDS order wins", but every multi-fault case builds its JSON from `DEFAULT_KPI_TARGETS`, which is already in `KPI_IDS` order, so checking keys in the JSON's own order would also pass (the spec does not require an order; add a reversed-key multi-fault case or reword the comment, STD-TEST-8); (2) suspected: at `erp_ai_setting.py:303`, a non-string `kpi_targets` (for example a dict sent through the API) would crash on `.strip()` and `json.loads` would raise an uncaught TypeError, giving a 500 instead of a validation message (STD-ERR-2; low impact, the setting can only be edited by System Manager); (3) duplicate JSON keys silently collapse to the last value, and the root-level "không phải JSON object hợp lệ" message has no key path (the design leaves the wording to dev) | dev's call

**Review checklist (10)**
1. pass: does exactly what AC-55/E-9 asks, nothing extra (the local `KPI_STAGES` is the simplest form).
2. pass: only the 2 touchpoint files; no new files.
3. pass: RED came first (29 failures); `test_default_targets_valid` was green before the change, and the Expect line allows that for a guard test. Edge and error paths are covered; no skip/xfail.
4. pass: no existing test changed. The new class calls `keep_agent_settings` and rolls back in `addCleanup`. `setUp` saves the default and an empty `coo_report_recipients` itself, so it does not depend on live values. No clock or network use.
5. pass: input is validated at the save boundary; the `ValueError` catch is narrow (`JSONDecodeError` is a subclass of it). Minor (2) above.
6. pass: user-typed keys are escaped in both messages; no secrets, no SQL, no permission change.
7. pass: no schema or contract change; a new check on an existing field only.
8. pass: names follow the file's existing pattern (`kpi_targets_error` matches `allowed_report_error`); tab style; no dead code. Long lines are allowed (E501 is ignored in `pyproject.toml`).
9. pass: no new dependencies (`json` and `math` are standard library).
10. pass: branch `team/FEAT-007-task-17`; commit `feat(setting): refuse KPI targets with a wrong shape on save (FEAT-007)` fits STD-NAME-5 and has no AI trailer (STD-GIT-8); one commit for one task. User docs are not needed here: the field description already states the rule.

**Not verifiable from the diff (for tech-lead)**
- I did not run anything. RED, GREEN and `MIGRATE_EXIT=0` come only from dev's evidence. Suggest re-running `cmd.test_one` on `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` and `erp_ai/tests/test_architecture.py` after the merge.
- `cmd.lint` / ruff-format output for the two files is not in the package.
- Downstream: T47/T48 (`kpi.py`, the KPI Weekly report) will read `kpi_targets`. They can rely on finite numbers ≥ 0 that may be int or float. They cannot import `kpi_targets_error`, because the ADR-001 layer rule forbids it, so they need their own fail-safe parsing.

**Read-only commands used:** `git log --oneline 7d10d0f..team/FEAT-007-task-17`, `git diff --stat …`, `git diff …`, `git log -1 --format='%H%n%an <%ae>%n%B' team/FEAT-007-task-17`; `git show team/FEAT-007-task-17:` cho `erp_ai_setting.py`, `test_erp_ai_setting.py`, `pyproject.toml`; grep/sed trên `tasks.md`, `design.md`, `design-w0-fixes*.md`, `spec.md`, `plan.md`, `erp_ai/agent/routing.py`.

## Kết luận của tech-lead (trước khi tick)

- Chạy lại sau merge `fd670a1`, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 76 tests in 7.164s OK`; `test_architecture` `Ran 112 tests in 3.887s OK`. Khớp số của dev.
- `cmd.lint` trên `fd670a1`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền, không thuộc task); hai file của task sạch.
- Điểm "suspected" (2), `kpi_targets` không phải chuỗi: tech-lead đọc `erp_ai_setting.py:298-310`. Có thật là giá trị dict gửi qua API sẽ ném `AttributeError` thay vì lời báo kiểm tra; nhưng lỗi làm việc lưu dừng lại (không lưu sai), chỉ System Manager gửi được, AC-55/E-9 không nói tới kiểu khác chuỗi, và các trường một-dòng-một-mục khác của controller dùng cùng cách `(value or "")`. Không tính là thiếu sót của task; để ở `deferred`.
- T47/T48 đọc `kpi_targets`: phải tự phân tích an toàn, không import `kpi_targets_error` (ADR-001). Ghi để lời bàn giao T47, T48 nhắc.

## deferred

- minor (1): test thứ tự lỗi dùng JSON vốn đã theo thứ tự `KPI_IDS` (STD-TEST-8); thêm ca khóa đảo hoặc sửa chú thích.
- minor (2): `kpi_targets` không phải chuỗi → lỗi 500 thay vì lời báo kiểm tra (STD-ERR-2).
- minor (3): khóa JSON trùng lấy giá trị sau; lời báo ở gốc không có đường dẫn khóa.
