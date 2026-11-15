Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 34 — CHG-002 T34

- Diff: `git diff ca9a03d..094ebd9` trên `team/CHG-002-task-33`, bỏ merge `330ec2e` của nhánh T33 đã merge riêng (commit của T34: `50a66ff`, `86d2f23`, `094ebd9`); vòng 3 chấm `git diff 86d2f23..094ebd9` (2 file, +57/−1)
- Gói: T33 + T34 giao cùng một dev ở lượt 4; T33 chấm ở `review-33.md`
- Vòng: 3 (max_rework = 3; vòng 3 là bước sau phán quyết thiết kế, không phải dev sửa lỗi của mình)
- Verdict: **approve** ở vòng 3 → merge `b8451bc`, tick

Ghi chú về nguồn: verdict của vòng 1 và vòng 2 nằm trong phiên build lượt 4, phiên đó bị cắt khi máy khởi động lại lúc 17:38 trước khi file này được viết. Hai vòng đó chép lại từ các dòng `round 40`, `round 41`, `round 42` của `tasks.md`; chi tiết `file:line` của từng phát hiện không còn.

## Vòng 1 — design-defect một điểm, kèm 2 major sửa được ngay (round 40)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| design-defect | STD-DESIGN-1 | design.md:478-491, design.md:808-815 | §4.2 bước 4–5 viết cho cả hai dạng, còn task và §8.3 không đưa `test_apply_job.py` hay test cũ vào: (a) dạng cũ cũng qua bước 4–5 có tiền tố mục, hay (b) tiền tố chỉ cho khối | designer phán |
| major | STD-DESIGN-2 | `apply_job.py` `_precheck_block` | chưa "nhớ `old_head`" như dòng Returns | trả `old_head` |
| major | STD-TEST-8 | `test_apply_block.py` | ba nhánh của bước 4–5 không có test | thêm ca cho từng nhánh |

## Vòng 2 — approve chờ thiết kế (`86d2f23`, round 42)

- 2/2 major ADDRESSED.
- Còn hai điểm thiết kế mở, giữ nhánh, chưa merge: (a) như trên; (b) HEAD khác nhau giữa các đường dẫn của một khối là `Lỗi` hay `Hết hiệu lực`.

## Vòng 3 — approve (`git diff 86d2f23..094ebd9`)

Phán quyết: `design-addendum-8.md` A8-1 (tiền tố mục ở bước 4–5 chỉ cho khối; dạng cũ giữ `_apply_code`) và A8-2 (HEAD lệch → `Lỗi`, `mục n (path): ` + `source.GIT_ERROR`). Mã `86d2f23` giữ nguyên; dev thêm một test ghim.

1. (a) A8-1: ADDRESSED. `apply_job.py:206-207` gọi `_precheck_block` chỉ dưới `if block.is_block(proposal)`; dạng một file đi tiếp `_apply_code` (`:208-210`), không tiền tố.
2. (b) A8-2: ADDRESSED. `apply_job.py:344-345` ném `_Stop(CHANGE_STATUS_FAILED, prefix + source.GIT_ERROR)`; `test_apply_block.py:412-428` không đổi.
3. "Test thêm" của A8-1: ADDRESSED. `TestLegacyThroughAdapter::test_legacy_steps_4_5_reasons_have_no_item_prefix` (`test_apply_block.py:581-635`): ba subTest `[stale]`, `[git refusal]`, `[branch]`; ba chuỗi viết tay trùng `apply_job.TARGET_CHANGED`, `source.GIT_LOCKED`, `apply_job.GIT_BRANCH_CHANGED`; spy `_precheck_block` `assert_not_called()`; `assert_failed_untouched` so trạng thái, lý do, sha và ảnh chụp cây, HEAD, số commit.

Phát hiện blocker/major: không.

Bằng chứng của dev (vòng 3): RED bằng đột biến (dòng 206 thành `if True:`, đã trả lại, không commit): `[stale]` `Tuples differ: ('Hết hiệu lực', 'mục 1 (custom_app/pkg/legacy.py): file đí[30 chars]None) != ('Hết hiệu lực', 'file đích đã đổi kể từ lúc đề xuất', None)`; `[branch]` `Expected '_precheck_block' to not have been called. Called 1 times.`; `Ran 1 test` / `FAILED (failures=3)`. GREEN `Ran 1 test in 1.524s` / `OK`.

## Review checklist (10)
1–10: đạt (phạm vi vòng 3: diff đúng A8-1 và A8-2; chỉ hai touchpoint; không skip; không đổi test có sẵn; không đổi hợp đồng; commit `test(apply): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff (tech-lead đã xử lý)

- Module trên `094ebd9` sau `migrate` (một lần giữ khóa 19:06–19:09): `test_apply_block` `Ran 19 tests in 14.386s` / `OK`, `test_apply_job` `Ran 117 tests in 135.483s` / `OK`, `test_block` `Ran 10 tests in 0.041s` / `OK`, `test_architecture` `Ran 185 tests in 15.068s` / `OK`. Lần chạy của dev báo 27 lỗi `'dict' object has no attribute 'idx'` vì site vừa bị phiên FEAT-007 migrate lại; chạy lại sau `migrate` thì xanh.
- Sau merge `b8451bc` + `9b0422b` (19:36–19:42): `test_apply_block` `Ran 28 tests in 28.021s` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_block` `Ran 10` / `OK`, `test_architecture` `Ran 195` / `OK`.
- Cả app, đợt merge 17, `team/CHG-002` @ `c44bf86` (19:42–19:53, `cmd.migrate` thoát 0): `Ran 1853 tests in 619.227s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Hai câu A8-1, A8-2 thêm vào `design.md` §4.2: addendum-8 ghi rõ không sửa `design.md`, addendum là nguồn; không phải việc của T34.

## deferred

1. minor: comment ở `test_apply_block.py:413` còn ghi "Design 4.2 step 5 has no sentence for it", nay A8-2 đã có câu đó.
