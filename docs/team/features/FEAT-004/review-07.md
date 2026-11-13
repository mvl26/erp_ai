Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 07 — FEAT-004 T7

- Diff: `git diff cb40420..team/FEAT-004-task-7` (2 commit `5604ba9`, `7ec00cd`; 3 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff cb40420..5604ba9`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/tools/test_change_guard.py:24-99 | mọi test so `reason` với hằng `change_guard.*`, không so với câu chữ bảng 3.1; đổi chữ của hằng thì test vẫn xanh | thêm một test so từng hằng với câu nguyên văn của design bảng 3.1 |
| major | STD-TEST-2 | erp_ai/agent/tools/test_change_guard.py:23-89 | thứ tự kiểm theo bảng 3.1 chỉ được kiểm một phần; không có ca nào dính hai lý do cho các cặp APP/NAME, APP/EXT, APP/GIT, EXT/GIT | thêm mỗi cặp một ca dính cả hai lý do và so lý do đứng trước |

minor | — | — | 2 điểm nhỏ: nhánh `os.path.isabs` (`change_guard.py:35`) chưa có ca riêng; `if full is None` cuối (`:52`) không tới được | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 5604ba9..team/FEAT-004-task-7`)
- Phát hiện 1: ADDRESSED (`test_refusal_wording_matches_design_table`, 5 câu trùng bảng 3.1 từng byte)
- Phát hiện 2: ADDRESSED (`test_double_refusal_returns_earlier_reason_of_table_order`: `otherapp/.env`, `otherapp/run.sh`, `otherapp/.git/x.py`, `myapp/.git/run.sh`, `myapp/.git/config`, `myapp/.git/secret.py`)
- Phát hiện mới: không có. Thêm `test_refuses_absolute_path_even_inside_root` (điểm minor).

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: `Ran 7 tests in 0.013s` / `FAILED (failures=31)`, ví dụ `AssertionError: None != 'app không có trong danh sách được sửa'`; GREEN: `Ran 7 tests in 0.016s` / `OK`
- Vòng 2 RED mẫu: `'đuôi file bị cấm' != 'đuôi file không được phép'`; GREEN: `Ran 10 tests ... OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `allowed_apps` phải là tuple/set ở nơi gọi (chuỗi sẽ thành so khớp chuỗi con): `ToolContext.allowed_apps: tuple[str, ...]` (T23), `ChangeSettings.allowed_apps` (T5); nhắc reviewer T18, T25.
- `new_file` chưa dùng ở T7: T42 dùng cho `read_git_state`.
- Thư mục có tên kết thúc bằng đuôi hợp lệ: lỗi `NOT_FOUND`/`EXISTS` của tầng tool (T25, T26).

## deferred
- Design 8.1 lấy `app/.git/config` làm ví dụ `GIT_DIR`, nhưng theo thứ tự bảng 3.1 đường dẫn đó nhận `EXT_FORBIDDEN`; sửa ví dụ trong design (writer/designer), không phải design-defect.
