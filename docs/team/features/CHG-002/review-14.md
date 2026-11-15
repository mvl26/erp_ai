Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 14 — CHG-002 T14

- Diff: `git diff 0444d89..dc7df69` (nhánh `team/CHG-002-task-14`, 2 commit `eb4d673` + `dc7df69`, 2 file)
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `0499815`, tick

## Vòng 1 — request-changes (`git diff 0444d89..eb4d673`)

major | STD-TEST-8 | erp_ai/agent/tools/test_change_guard.py:1702-1715 (`test_restart_twice_or_not_last_refused`) | §3.2:301 nói lý do đầu tiên tìm thấy là lý do trả về, nhưng không ca nào ghim thứ tự `RESTART_PLACE` trước `RESTART_WITHOUT_PY`: mọi hàng `RESTART_PLACE` có mục file đều dùng `.py`. Đưa khối `if not legacy:` lên trước phép kiểm `RESTART_PLACE` thì mọi test vẫn xanh. | Thêm hàng `[edit(README)]` với `[MIGRATE, RESTART, RESTART]` và `[RESTART, MIGRATE]`, `legacy=False` → `RESTART_PLACE`, ở cả hai thời điểm.

major | STD-TEST-5 | thân commit `eb4d673`, 5 dòng `test-input:` | Các dòng ghi L-2a nhưng ca này không phải L-1 hay L-2 (đầu vào từng được nhận nay bị luật MỚI từ chối); thiếu định dạng của addendum-4:37 (`<file>::`, lý do cũ/mới, `design §`). Bản thân các sửa đổi đúng (§3.8 đòi `migrate` + `restart` cho khối `.py`; assertion không đổi một byte). | Viết lại năm dòng đủ định dạng; tech-lead chọn nhãn.

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1: bốn hằng đúng chữ §3.1; thứ tự §3.2:312-316; `.py` tính trên mọi đường dẫn kể cả nguồn và đích đổi tên; P-6 (đường dẫn rỗng → `OP_FIELDS`) ở cả hai thời điểm; `propose_change.py` không đổi. Phạm vi tiền tố `lệnh {n}: ` (chỉ lý do của `check_bench_args`): reviewer phán đủ chữ design.md:230, §3.2:313, không phải design-defect.

Quyết định của tech-lead cho finding 2 (reviewer giao "You decide the label"): giữ nhãn `test-input:` đủ định dạng kèm câu "đầu vào từng được nhận nay bị luật mới từ chối (PY_NEEDS_RESTART)", không ghi L-2a; lượt build cấm amend nên commit mới nhất mang danh sách đầy đủ. Chỗ thiếu của L-1 / L-2 cho ca này: điểm thiết kế mở, báo team-leader.

Bằng chứng của dev (vòng 1): RED `Ran 83 tests in 9.292s` / `FAILED (failures=128, errors=1)`; GREEN `test_change_guard` `Ran 83 tests in 8.490s` / `OK`, `test_propose_change` `Ran 33 tests in 23.824s` / `OK`, `test_apply_block` `Ran 1 test in 1.200s` / `OK`, `test_architecture` `Ran 185 tests in 15.158s` / `OK`.

## Vòng 2 — approve (`git diff eb4d673..dc7df69`, 1 file, +6)

1. ADDRESSED | STD-TEST-8 | `test_change_guard.py:1715-1720`: hai hàng mới với `edit(README)`, `legacy=False`, qua `assert_refused_in_both_moments` → `RESTART_PLACE`; đột biến của dev cho `FAILED (failures=4)` (2 hàng × 2 thời điểm).
2. ADDRESSED | STD-TEST-5 | thân commit `dc7df69` mang đủ năm dòng `test-input:` đúng định dạng; reviewer đối chiếu từng dòng với mã ở `:1232`, `:1351-1352`, `:1481`, `:1554`, `:1586-1587`: chỉ `commands` đổi, mọi assertion giữ nguyên.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev (vòng 2): RED bằng đột biến `'khối có file nhưng không có file .py thì không restart' != 'restart chỉ được một lần và phải là lệnh cuối'`, `Ran 83 tests in 9.080s` / `FAILED (failures=4)`; GREEN `test_change_guard` `Ran 83 tests in 9.026s` / `OK`, `test_propose_change` `Ran 33 tests in 25.437s` / `OK`, `test_apply_block` `Ran 1 test in 1.365s` / `OK`, `test_architecture` `Ran 185 tests in 15.456s` / `OK`.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Mẫu M3 của addendum-7 (`design-addendum-7.md:183`): khối có `custom_app/pkg/mod.py` với lệnh `build` rồi `restart`, KHÔNG có `migrate`; theo §3.2:316 (đã làm ở T14) `check_block` từ chối khối đó (`RESTART_NEEDS_MIGRATE`), nên nó không tới được bước áp dụng. T32 (đã merge) dựng M3 bằng `make_block_proposal` + `post_result` (hàm thuần, không qua `check_block`), `cmd.test` cả app trên `0499815` đúng baseline → không đỏ. CHƯA xử lý được ở build: mẫu trái luật là việc của designer (điểm mở trong báo cáo lượt 4); lệnh giao T37, T38 ghi rõ không dựng M3 qua job.
- Nơi gọi khác của `check_block` truyền `legacy` đúng chưa: thuộc T26 (`legacy` mặc định `False` ở tool) và T33 (review-33: có ca ghim `legacy` ở cả hai phía).
- Module và cả app sau merge: dòng progress của T14 trong `tasks.md` (đợt merge 13, `0499815`).

## deferred

1. `MIGRATE_COMMAND = SITE_COMMANDS[0]` phụ thuộc vị trí trong tuple (`change_guard.py:86`).
2. `_is_named(path)` không có type hint, tên nói "named" thay vì "non-blank"; `_commands_reason` nhận `allowed_apps`, `site` không có kiểu.
3. Nhãn hàng trong hai dòng `test-input:` rút gọn (thiếu đích đổi tên; liệt kê 3 trong 5 mục).
