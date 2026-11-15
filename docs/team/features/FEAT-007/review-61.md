Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 61 — FEAT-007 T61

- Diff: `git diff 5e265563c4f76864dd650e626870a771ef32e9d6..29abb3f` (đầu nhánh task khi merge; merge `d4661aa` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `5e26556..29abb3f` (1 commit, 2 file, +58/−2), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `FAIL: test_restores_auth_rows_of_credentials ... AssertionError: Lists differ` (phép khẳng định sau `doCleanups()`), `Ran 13 tests ... FAILED (failures=1)`; GREEN `test_test_utils` `Ran 13 tests ... OK`, `test_architecture` `Ran 112 tests ... OK`, `test_erp_ai_setting` `Ran 34 tests ... OK`.
- Kết luận của reviewer: bản chụp đọc dòng `__Auth` với các cột `doctype, name, fieldname, password, encrypted` cho ERP AI Setting và DocType các bảng con (`erp_ai/test_utils.py:122-127`); bước trả lại xóa dòng hiện có của các DocType đó rồi chèn bản chụp (`:140-145`); chép nguyên bản mã hóa, không gọi `get_password` / `get_decrypted_password`; hai câu SQL có tham số; không commit; chữ ký không đổi; `test_restores_singles_and_child_rows` không đổi. Test mới đổi một dòng có trước bản chụp, thêm một dòng, và xóa một dòng (nhiều hơn thiết kế đòi); so bằng sha256 của bản mã hóa nên không in giá trị; bỏ bước trả lại, chỉ chèn không xóa, hoặc upsert đều làm test đỏ.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 3 điểm nhỏ: (1) `erp_ai/tests/test_test_utils.py:310` lặp phép kiểm độ dài ngay sau phép so danh sách (STD-STYLE-5); (2) không test nào phủ dòng `__Auth` của chính ERP AI Setting (hiện Setting không có trường Password nên chưa quan sát được; trường Password thêm sau sẽ không có test) (STD-TEST-8); (3) docstring `erp_ai/test_utils.py:103` nói "their `__Auth` rows" trong khi bước trả `__Auth` phủ mọi parent của từng DocType con còn bước trả dòng con chỉ phủ parent = Setting; bản chụp cùng phạm vi với bước trả nên vô hại | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (RED được dán; đường đổi, xóa, thêm; không skip) 4. đạt (không khẳng định sẵn có nào đổi; test tự tạo dòng và rollback) 5. đạt 6. đạt (không giải mã; thông báo khẳng định chỉ có sha256 và tên dòng; giá trị giả; SQL có tham số; commit bị chốt test chặn) 7. đạt 8. đạt 9. đạt (`hashlib` là thư viện chuẩn) 10. đạt (`test(utils): … (FEAT-007)`, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Các nơi gọi khác của `keep_agent_settings` chưa được dev chạy lại (`test_classification.py:523`, `test_hard_bans.py:38`, `test_install.py:650`, `test_feat007_unknown_confidence_pct.py:45`) | Tech-lead chạy từ worktree `feat-007` sau merge `d4661aa`: `test_test_utils` `Ran 13 tests in 1.287s OK`; `test_erp_ai_setting` `Ran 36 tests in 1.252s OK`; `test_classification` `Ran 49 tests in 0.116s OK`; `test_hard_bans` `Ran 7 tests in 0.092s OK`; `test_install` `Ran 36 tests in 17.013s OK`; `test_feat007_unknown_confidence_pct` `Ran 5 tests in 0.092s OK`; `test_routing` `Ran 62 tests in 0.066s OK`; `test_ops_data` `Ran 8 tests in 0.064s OK`; `test_architecture` `Ran 112 tests in 3.122s OK`. `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`. |
| Hai lần chạy đỏ đầu của dev dính `QueryDeadlockError`: do câu `delete from __Auth where doctype in (...)` hay do phiên khác trên site | Chín module ở dòng trên chạy liền nhau sau merge, 0 deadlock. Chưa loại trừ được khi hai phiên chạy cùng lúc: theo dõi ở lần `cmd.test` cả bộ của mốc M1; lặp lại thì ghi `debt.md` (STD-TEST-7). Không chặn tick. |

## deferred

- (minor, tùy dev) 3 điểm nhỏ ở trên.
