Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 47 — CHG-002 T47

- Diff: `git diff 3e1cddd..b46d730` (vòng 1) và `git diff e6a18af..25dfd11` (sửa vòng 1), nhánh `team/CHG-002-task-47`, 1 file `erp_ai/tests/test_architecture.py`
- Gói: T47 + T48 cùng nhánh, một reviewer chấm cả gói; verdict của T48 ở `review-48.md`
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `ae8edc5` (cùng T48), tick

## Vòng 1 — request-changes (`git diff 3e1cddd..b46d730`, +343)

major | STD-TEST-8 | erp_ai/tests/test_architecture.py:8641,8648 | Luật `sudo` / `supervisorctl` và luật `setsid` chỉ tách chuỗi theo `[\s/]+` và chỉ đọc hằng `str`. Hai dạng vi phạm rõ ràng lọt cả hai luật, nên AC-45 ("0 lần trong mã sản phẩm") và A-5 ("đúng 1 lần") chưa được ép đủ: (1) chữ shell dính nháy hoặc ký tự shell (`"bench restart||sudo bench restart"`, `"$(sudo x)"`, `"x;sudo y"`, `"'setsid' -f …"`); (2) argv `bytes` (`[b"sudo", …]`). | Tách theo `[^\w.-]+`; quét cả hằng `bytes` sau `decode("utf-8", "replace")`; mỗi dạng một ca tự kiểm ở cả hai test.

minor | — | — | 3 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1: lớp `TestChangeBlockRules` là khối riêng cuối file, hai hàm `check_change_block_*` liền nhau; diff chỉ thêm dòng (`test_single_enqueue_call_site`, `check_tools_never_bypass_permissions` không đổi); mỗi điều kiện A-5 có ca tự kiểm riêng (DEVNULL ×3, `timeout=`, `cwd=`, các dạng `env=`, `setsid` ở file khác / trong chuỗi lệnh / viết lại trong `RESTART_ARGV`, `SETSID_EXECUTABLE` không ở phần tử 0 / dùng hai lần / dùng ở file khác / không khởi chạy / khởi chạy lần hai); test trên mã sản phẩm ghim `setsid_texts == [(source.py, "setsid")]` và đúng 1 lời gọi khởi chạy.

Bằng chứng của dev (vòng 1): RED `NameError: name 'check_change_block_restart_launch_shape' is not defined` ×24, `… 'check_change_block_no_sudo_or_supervisorctl_argv' …` ×6, `… '_code_strings' …` ×1, `Ran 190 tests in 15.674s` / `FAILED (errors=31)`; GREEN `Ran 190 tests in 15.833s` / `OK`.

## Vòng 2 — approve (`git diff e6a18af..25dfd11`, +110/−19)

- ADDRESSED | STD-TEST-8 | `_command_tokens` tách theo `[^\w.-]+` (`:8639-8642`; `"pseudo-restart"` vẫn là một token); `_code_strings` trả `(node, text)` cho cả `str` và `bytes` (`:8645-8655`), ba nơi gọi đều đổi theo; ca tự kiểm mới cho `||`, `;`, `$(`, có nháy, argv `bytes` ở cả hai test (`:8920-8948`, `:9050-9062`). Phần của T48 không bị đụng.

Lỗi mới trong các dòng đổi: không (2 minor, xem deferred).

Bằng chứng của dev (vòng 2): RED 12 ca `AssertionError: 0 not greater than 0 : scanner missed the violation`, `Ran 195 tests in 15.889s` / `FAILED (failures=12)`; GREEN `Ran 195 tests in 16.196s` / `OK`.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Luật chỉ quét file `.py` (`load_product_sources` mặc định), còn A-5 nói `erp_ai/**` ngoài test: reviewer đã `git grep` trên `e6a18af`, không có `setsid` / `sudo` / `supervisorctl` ở file sản phẩm nào ngoài `source.py:90`. Mở rộng luật sang `.sh` / `.json`: điểm deferred, không chặn.
- Module và cả app sau merge: dòng progress của T47 trong `tasks.md` (đợt merge 14, `ae8edc5`).

## deferred

1. Luật "bản sao `list()` / `tuple()` không tính là một lần khởi chạy" không có ca sạch ghim (`Popen(list(RESTART_ARGV), …)` đúng hình dạng → `[]`); `tuple()` không có ca.
2. `:8753-8754`: biến lặp `text` bị ghi đè bởi chuỗi thông điệp.
3. argv ghép bằng phép cộng (`RESTART_ARGV + ["-v"]`), `bytearray`, chuỗi ghép lúc chạy không bị bắt (ngoài tầm luật tĩnh).
4. Kiểm `env=` chỉ đi trong biểu thức (`env=_full_env()` lọt); khớp chữ của task.
