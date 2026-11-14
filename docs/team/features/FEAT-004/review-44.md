Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 44 — FEAT-004 T44

- Diff: `team/FEAT-004-task-44` (head d5a407d), khoảng `02a9715..team/FEAT-004-task-44`, 1 commit, 1 file
- Vòng: 2 (vòng 2: khoảng sửa `d5a407d..team/FEAT-004-task-44-r2`, head 2f840d5)
- Verdict: approve (vòng 1: request-changes)

Lệnh đã dùng (chỉ đọc):
```
git log --oneline 02a9715..team/FEAT-004-task-44
git diff --stat 02a9715..team/FEAT-004-task-44
git diff 02a9715..team/FEAT-004-task-44
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T44'
git show team/FEAT-004-task-44:docs/team/adr/ADR-022.md | grep ...
git show team/FEAT-004-task-44:docs/team/features/FEAT-004/design.md | grep ...   (bảng luật 8.2, dòng 945-949)
git show team/FEAT-004-task-44:erp_ai/tests/test_architecture.py | sed -n '520,560p'   (check_import_boundaries)
git grep -n 'git_env(' team/FEAT-004-task-44 -- 'erp_ai/**/test_*.py'
```
Không chạy test; dựa vào RED/GREEN của dev (RED `FAILED (failures=249)`, mỗi lỗi "scanner missed the violation"; GREEN `Ran 165 tests` / `OK`).

Layer 1: đủ tiêu chí. Có `LAYER_RULES` cho `erp_ai.agent.change_text` (bên thứ ba ngoài frappe/helpdesk đã do `check_import_boundaries` chặn theo allowlist, nên "chỉ thư viện chuẩn + `erp_ai.constants`" kín). Có đủ 8 luật/test mà dòng Returns nêu. 30 lệnh con cấm, tập đọc 8 lệnh và cờ cấm của commit khớp ADR-022 QĐ 2 từng chữ. Mỗi luật có ca bắt và ca sạch (`GIT_CLEAN` có mồi: docstring `--amend`/`git push`, `"ngoài apps/"`, `_not_web` không với tới từ whitelist). Test trên mã thật có khẳng định đếm dương, không rỗng. Ba ngoại lệ của dev khớp tài liệu: `git_source` log/blame giữ `os.environ` (ADR-022 QĐ 4 gạch "giữ nguyên, không bắt buộc đổi"); bỏ docstring (Ràng buộc nói "chuỗi dựng lệnh git"); gốc `apps/` chỉ quét `agent/**` (design 8.2 dòng 949 "ở nơi khác trong `agent/`"). Phần thân `git_env` không lẫn `os.environ` đã có test hành vi `erp_ai/agent/tools/test_source.py:1081` ghim cả dict. Không có file ngoài touchpoint.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/tests/test_architecture.py:3358 (ca: :6429-6466) | Nhánh `if value == "config" or value.endswith(("/config", "\\config"))` của `check_no_forbidden_git_operations_in_product` (chỉ trong `SUBPROCESS_FILES`) là chỗ duy nhất bắt cách đọc `.git/config` qua thư mục git động, ví dụ `open(f"{git_dir}/config")` hoặc `os.path.join(git_dir, "config")` trong `source.py`. `_path_parts` và `GIT_CONFIG_PATH` đều cần chữ `.git` hằng. Không ca nào chỉ do nhánh này bắt: 4 ca `config_read` nằm ở `change_guard.py` (không thuộc `SUBPROCESS_FILES`), ca `sub="config"` đã bị luật phần tử argv bắt với `'config'`, mồi sạch `os.path.join(root, 'config')` nằm ở `apply_job.py`. Xóa nhánh thì 165 test vẫn xanh (confirmed khi liệt kê đủ các ca). | Thêm một ca bắt ở `SOURCE_TOOL_FILE`/`PROCESS_RUNNER_FILE` mà không có `.git` hằng, ví dụ `"\n\ndef f(d):\n\treturn open(f'{d}/config')\n"` và `os.path.join(d, 'config')`, assert `"git config file"`. Thêm một ca sạch trong file subprocess (chuỗi như `"configure"` hoặc `"core.fsmonitor=false"`) để ghim ranh giới. |

minor | STD-TEST-8 / STD-TEST-2 | — | 4 điểm nhỏ: (1) nhánh `elif ... "os.environ"` của `check_git_env_single_definition` (:3480) không có ca riêng: ca "env mixed"/"os.environ env" đã rơi vào nhánh "không phải `git_env(...)`"; (2) nhánh chuỗi `value == AGENT_USER_NAME` của `check_bot_identity_constants` (:3557) không có ca riêng (ví dụ `getattr(constants, "AGENT_USER")`); (3) `is_legacy` (:3257) miễn mọi lệnh log/blame viết trực tiếp trong `source.py`, không riêng `git_source`, nên một lệnh `["git", "log", ...]` mới với `env={**os.environ}` cũng được miễn; (4) `rm` chỉ bị buộc có `--cached` (:3409), còn ADR-022 QĐ 2 ghi "chỉ `--cached -q -- <đích>`" (`-r`/`-f` lọt), và `commit --author=...` không bị chặn mặc dù QĐ 5 cố định tác giả (danh sách cờ cấm của ADR không có `--author`, nên đưa designer) | tùy dev

## Review checklist (10)
1. Đúng và đủ tiêu chí, không làm thừa: đạt (STD-DESIGN-5, STD-TEST-2).
2. Trong touchpoint (chỉ `erp_ai/tests/test_architecture.py`), không có file mới: đạt (STD-DESIGN-1, STD-STRUCT-1).
3. Test đỏ trước (249 lỗi "scanner missed"), không skip/xfail; ca biên: trượt một nhánh, xem major (STD-TEST-8). Không có skip marker nào của profile trong diff (STD-TEST-4 đạt).
4. Không sửa test cho khớp hành vi sai. Test độc lập: `git_product` trả dict mới, không đổi `GIT_CLEAN`: đạt (STD-TEST-5, STD-TEST-6).
5. Xử lý lỗi: chỉ là mã test tĩnh. File hoặc bảng thiếu thì trả violation chứ không ném lỗi (`change_guard` thiếu, `BENCH_COMMANDS` không đọc được, `constants.py` thiếu): đạt (STD-ERR-1).
6. Không có bí mật, không injection. Luật siết đúng mục ADR-022 về remote URL, `.invalid` và `os.environ`: đạt (STD-SEC-1).
7. Hợp đồng: không đổi API sản phẩm. `LAYER_RULES` chỉ thêm, luật cũ giữ nguyên: đạt (STD-DESIGN-3).
8. Tên và cấu trúc theo profile, không có mã chết: đạt. Có gọi `scan._is_source_call` từ ngoài lớp, là chuyện phong cách, không phải phát hiện (STD-NAME-1, STD-STYLE-4).
9. Phụ thuộc: chỉ thêm `itertools` và `typing.NamedTuple` của thư viện chuẩn: đạt (STD-DEP-1).
10. Commit `test(architecture): ... (FEAT-004)` theo chuẩn, nhánh `team/FEAT-004-task-44`: đạt (STD-GIT-1, STD-NAME-4).

## Không kiểm được từ diff
- GREEN/RED chỉ là lời dev, reviewer không chạy lại. Gợi ý: `cd /home/miyano/frappe-bench && PYTHONPATH=<checkout nhánh> bench --site miyano run-tests --module erp_ai.tests.test_architecture`.
- Luật no-git-in-web chỉ lần theo hàm cùng module với hàm `@frappe.whitelist`. Một whitelist gọi sang module khác (không phải `source`/`process_runner`) để chạy git thì không bị bắt. Design dòng 947 không đòi lần sâu hơn; tech-lead quyết định có cần không.

## Deferred
- Không có (vòng 1).

## Vòng 2

- Diff sửa: `d5a407d..team/FEAT-004-task-44-r2` (head 2f840d5), 1 commit `test(architecture): cover the git config file branch with runtime git dir cases (FEAT-004)`, 1 file `erp_ai/tests/test_architecture.py`, +17 dòng.
- Verdict: approve

Lệnh đã dùng (chỉ đọc):
```
git log --oneline d5a407d..team/FEAT-004-task-44-r2
git diff --stat d5a407d..team/FEAT-004-task-44-r2
git diff d5a407d..team/FEAT-004-task-44-r2
git show team/FEAT-004-task-44-r2:erp_ai/tests/test_architecture.py | grep -n -A8 -E 'def (assertCaught|git_product)\('
git show team/FEAT-004-task-44-r2:erp_ai/tests/test_architecture.py | sed -n '3350,3366p'   (nhánh config của scanner)
```
Không chạy test; dựa vào RED/GREEN của dev: xóa nhánh thì `FAILED (failures=4)`, ví dụ `(rel='agent/tools/source.py', config_read="open(f'{git_dir}/config')") AssertionError: 0 not greater than 0 : scanner missed the violation`; khôi phục nhánh thì `Ran 165 tests in 20.274s OK`.

### Phát hiện cũ
| Phát hiện vòng 1 | Trạng thái | Chứng cứ |
|---|---|---|
| major STD-TEST-8 `test_architecture.py:3358`: nhánh `value == "config" or endswith("/config")` không có ca nào chỉ do nó bắt | ADDRESSED | `erp_ai/tests/test_architecture.py:6469-6481`: với mỗi file trong `SUBPROCESS_FILES`, 2 ca `open(f'{git_dir}/config')` (phần hằng `/config` → `endswith`) và `open(os.path.join(git_dir, 'config'))` (`value == "config"`). Thư mục git lấy lúc chạy, không có chữ `.git` hằng nên `GIT_CONFIG_PATH` và `_path_parts` không bắt được. Không có argv git, nên luật phần tử argv cũng không bắt. `assertCaught(..., rel, "git config file")` khớp đúng thông điệp của nhánh (:3359-3361). RED của dev ra đúng 4 lỗi, bằng 4 ca mới. Ca sạch `:6489-6492` (`'configure'`, `'etc/configure'` trong cả hai file) ghim ranh giới: nếu nới nhánh thành so khớp chuỗi con `"config" in value` thì ca này đỏ. |

### Phát hiện mới (chỉ blocker/major)
Không có.

minor | STD-TEST-8 | — | 1 điểm nhỏ: phần tử `"\\config"` trong tuple `endswith(("/config", "\\config"))` (:3359) vẫn không có ca riêng (đường dẫn kiểu Windows, sản phẩm chạy trên Linux nên rủi ro thấp) | tùy dev

### Review checklist (10), chỉ trên diff sửa
1. Đúng phần sửa mà phát hiện vòng 1 yêu cầu, không làm thừa: đạt (STD-DESIGN-5, STD-TEST-2).
2. Chỉ sửa `erp_ai/tests/test_architecture.py` (trong touchpoint), không có file mới: đạt (STD-DESIGN-1, STD-STRUCT-1).
3. RED trước (4 lỗi khi xóa nhánh), có ca biên sạch, không có skip/xfail/only: đạt (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Không đổi assertion cũ; `git_product` trả dict mới, ca độc lập, dùng `subTest`: đạt (STD-TEST-5, STD-TEST-6).
5. Xử lý lỗi: diff chỉ thêm ca test, không đổi đường xử lý lỗi: đạt (STD-ERR-1).
6. Không có bí mật, không đụng `protected_paths`: đạt (STD-SEC-1).
7. Không đổi hợp đồng hay scanner: đạt (STD-DESIGN-3).
8. Tên và kiểu theo file sẵn có (tab, `subTest(rel=..., config_read=...)`), có comment giải thích ý định, không có mã chết: đạt (STD-STYLE-4, STD-STYLE-5).
9. Không thêm phụ thuộc: đạt (STD-DEP-1).
10. Commit `test(architecture): ... (FEAT-004)`, nhánh `team/FEAT-004-task-44-r2`: đạt (STD-NAME-4, STD-NAME-5, STD-GIT-1).

### Không kiểm được từ diff
- RED/GREEN chỉ là lời dev, reviewer không chạy lại. Gợi ý: `cd /home/miyano/frappe-bench && PYTHONPATH=<checkout nhánh> bench --site miyano run-tests --module erp_ai.tests.test_architecture`.

### Deferred
- Không có điểm mới ngoài phạm vi. Các minor của vòng 1 (nhánh `os.environ` :3480, `AGENT_USER_NAME` :3557, `is_legacy` :3257, `rm`/`--author`) vẫn để dev và designer quyết định, không chặn vòng này.
