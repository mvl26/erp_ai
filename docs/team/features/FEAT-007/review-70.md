Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 70 — FEAT-007 T70

- Diff: `git diff 67f0fcbbc096e5e718f813a25ed75dbf6a20b117..723c8db` (nhánh `team/FEAT-007-task-70`; 2 commit `cee1785` test, `723c8db` mã; 3 file +243, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `aedc360` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED, `MIGRATE_EXIT=0`: `ERROR: test_values_and_fail_closed … AttributeError: module 'erp_ai.agent.policy' has no attribute 'SITE_ENVIRONMENT_FIELD'`, test_policy `Ran 56 tests in 2.630s FAILED (errors=1)`; `FAIL: test_site_environment_read_only_via_policy … AssertionError: 'SITE_ENVIRONMENT_FIELD = "site_environment"' not found in '<policy.py source>'`, test_architecture `Ran 182 tests in 16.450s FAILED (failures=1)`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_policy `Ran 56 tests in 2.679s OK`, test_architecture `Ran 182 tests in 16.167s OK`.
- Lớp 1: C-1, C-2 và ADR-031 QĐ 7 đều đạt, không có file ngoài touchpoint.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đủ 4 tên Returns, đúng hành vi C-1. Luật và danh sách cho phép theo C-2. `assertNotIn(SITE_ENVIRONMENT_FIELD, POLICY_FIELDS)` ghim việc không đưa trường vào `POLICY_FIELDS`. Mọi file được gọi `policy.site_environment(`. Điều này C-1 đã ngầm đòi (đơn vị gọi U7 nằm ngoài danh sách) và khớp U7a-fixes Sửa 7 / w2a D-7, nên không phải lan phạm vi.
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1): chỉ 3 file khai báo, không thêm file mới.
3. Test trước (STD-TEST-1, -8, -4): `cee1785` chỉ có test, `723c8db` chỉ có mã. Có RED cho cả hai module. Ca biên đủ: `""`, None, `"staging"`, khác hoa thường, có khoảng trắng, 0/1/True, list, trường thiếu, `object()`, giá trị lưu sai, `settings` truyền vào thắng giá trị lưu. Ca đỏ Expect đòi có mặt: "tasks.py reads settings.site_environment" → `tasks.py:12`, reviewer đã đếm dòng và khớp. Không có skip/xfail.
4. Độc lập (STD-TEST-5, -6): có chốt chặn commit, rollback và `keep_agent_settings`. Reviewer đã soát đột biến từng vế bằng cách đọc code: bỏ nhánh `continue` của danh sách cho phép; bỏ một mục cho phép (mẫu tuân thủ đỏ); bỏ quét chuỗi; bỏ loại trừ docstring (docstring của executor đỏ); bỏ kiểm hằng `SITE_ENVIRONMENT_FIELD`; nới miễn trừ hàm đọc; bỏ lọc `module` của import. Mọi đột biến đều làm một ca đỏ. Đổi `is None` thành `not settings` cũng bị bắt (`frappe._dict()` rỗng mà giá trị lưu là "test").
5. Lỗi và đầu vào (STD-ERR-1, -2): fail closed về production, không có nhánh nào raise. Không gọi ngoài.
6. Bảo mật (STD-SEC-1, -3, -4, -6): không có bí mật, không đụng protected_paths.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): chỉ thêm tên mới, không đổi schema, không cần migrate.
8. Tên và style (STD-NAME-2, STD-STYLE-4, -5): hằng UPPER_SNAKE, theo đúng mẫu luật có sẵn (`assertRuleSamples`, `changed`). Không có code chết.
9. Phụ thuộc (STD-DEP-1): không thêm phụ thuộc mới.
10. Commit (STD-NAME-5, STD-GIT-1, STD-GIT-8): `test(policy)…`/`feat(policy)… (FEAT-007)`, không có trailer AI. Task không đổi hành vi người dùng thấy, nên không cần cập nhật tài liệu.

Danh sách cho phép so với chữ C-2: cả 4 mục (`agent/policy.py`, `erp_ai_setting.py`, `agent/run_log.py`, `install.py`) đều có tên trong C-2. `run_log.py` và `install.py` hôm nay chưa nêu tên trường, nhưng C-2 liệt kê đích danh nên vẫn trong phạm vi task. Grep ở base chỉ thấy `erp_ai_setting.py:211`, chưa có báo cáo nào đọc cột Log, nên chưa có mục U5a. Code sản phẩm không có import tương đối nào, nên việc luật chặn `from .policy import …` không chặn nhầm ai hôm nay. f-string hay phép nối có `policy.site_environment()` không bị chặn, vì `_string_shape` với `NO_CONSTANTS_SCAN` thay lời gọi bằng `UNKNOWN_PIECE`.

### Findings

- Không có blocker hay major.
- minor | — | — | 3 điểm nhỏ: (a) `policy.py:265` vế `isinstance(value, str)` thừa so với `value in SITE_ENVIRONMENTS` và không ca nào phân biệt được; (b) lý do ghi cho `RUN_LOG_FILE` ("writes the ERP AI Log column") mới đúng sau T85, lý do cho `INSTALL_FILE` là vai trò chung vì install không nêu tên trường; (c) lời báo của luật khuyên dùng `policy.site_environment()` cả khi người viết đã gọi hàm đó qua import tương đối | dev tự quyết

### Không kiểm được từ diff

- Danh sách cho phép tính theo cả file (đúng chữ C-2), nên `run_log.py`, `install.py` và controller đọc thẳng trường Setting mà luật không bắt. Lúc review T85 cần kiểm `write_entry` điền cột Log bằng `policy.site_environment()` (A-U3-6, `test_every_row_gets_site_environment`).
- Theo U3:147/:213, người gọi `write_bot_action(site_environment=…)` ngoài controller sẽ bị chặn vì truyền tham số khóa. Thiết kế chỉ cho controller truyền giá trị này. Cần kiểm lại ở U5b, U6b, U7.
- Báo cáo U5a đọc cột Log (w1a:104): khi merge đợt 1, grep lại `site_environment` trong `erp_ai/**/*.py` trên nhánh đã gộp.
- Reviewer chưa chạy test.

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline 67f0fcb..723c8db`; `git log --format='%h %s%n%b---' <range>`; `git diff --stat <range>`; `git diff --stat 67f0fcb..cee1785`; `git diff <range>`; `git grep -n site_environment 67f0fcb -- 'erp_ai/**/*.py' 'erp_ai/**/*.json'`; `git grep -nE '^from \.' 723c8db -- 'erp_ai/**/*.py'`; `git show 723c8db:erp_ai/tests/test_architecture.py`.

## Kết luận của tech-lead

- Test sau merge (tech-lead, worktree `feat-007` @ `aedc360`, đã có T125 và T123 nằm sau BASE của task; một lần giữ khóa site, `MIGRATE_EXIT=0`): `erp_ai.agent.test_policy` `Ran 56 tests in 2.751s` / `OK`; `erp_ai.tests.test_architecture` `Ran 182 tests in 16.444s` / `OK` → luật mới không bắt vi phạm nào trên cây đã gộp (`install.py` của T125 không nêu tên trường).
- Ba mục "không kiểm được" đầu là việc của task sau, không phải chỗ hở của T70: ghi vào dòng DỪNG lượt 14 của `tasks.md` (mục chuyển team-leader số 5) để vào lời giao reviewer của T85 và các task U5b, U6b, U7.
- Tick T70: 66/174.

## deferred

- minor (a), (b), (c) ở trên; (b) tự hết khi T85 merge.
- Lời giao reviewer T85: `write_entry` điền cột Log bằng `policy.site_environment()`.
