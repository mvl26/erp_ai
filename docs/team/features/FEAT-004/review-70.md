Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 70 — FEAT-004 T70

- Diff: `git diff b2da34e..e949542` (1 commit trên `team/FEAT-004-task-70`; `erp_ai/test_change_decision.py` +2/−1)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có blocker hay major | — |

minor | — | — | 0 điểm nhỏ | —

## Review checklist (10)
1. Đúng và đủ tiêu chí: đạt. Hằng viết tay `BAD_LINK_REFUSAL = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa."` (`test_change_decision.py:43`) là giá trị kỳ vọng của cả 6 ca trong `test_post_bad_signature_changed_action_or_name_writes_nothing` (`:214`); câu có cụm "không hợp lệ" của AC-26; test không còn tham chiếu `change_decision.BAD_LINK`.
2. Trong touchpoint: đạt (1 file; không sửa mã sản phẩm).
3. Test đỏ trước, không skip: đạt. Bằng chứng đỏ là đột biến không commit; bản cũ so với hằng của mã thì vẫn xanh dưới cùng đột biến. 0 dấu skip.
4. Không nới phép so, test độc lập: đạt. `assertRefused` vẫn so `str(exc) == message`; trạng thái, số dòng nhật ký, 0 job, đề xuất kia vẫn "Chờ duyệt" giữ nguyên.
5. Xử lý lỗi: không áp dụng (chỉ test).
6. Bảo mật: đạt. Không khóa, không `protected_paths`.
7. Hợp đồng: đạt, không đổi.
8. Tên, cấu trúc, phong cách: đạt (theo mẫu `ROLE_REFUSAL`); import `change_decision` vẫn được dùng ở `:187`.
9. Phụ thuộc: đạt, không thêm.
10. Commit, nhánh: đạt (`test(change-decision): … (FEAT-004)`, không dòng ghi công AI).

## Bằng chứng của dev (nguyên văn)
- RED (đột biến tạm, không commit: `BAD_LINK = "Mutated sentence."` trong `erp_ai/change_decision.py`): `AssertionError: 'Mutated sentence.' != 'Đường dẫn duyệt không hợp lệ hoặc đã bị sửa.'` ở cả 6 ca; `Ran 10 tests in 24.488s` / `FAILED (failures=6)`
- GREEN (sau `git checkout -- erp_ai/change_decision.py`): `Ran 10 tests in 24.494s` / `OK`
- Lint: `pre-commit run --files erp_ai/test_change_decision.py` exit 0
- Lần đỏ đầu tiên có thêm một lỗi `OperationalError: (1412, 'Table definition has changed, please retry transaction')` (`Ran 10 tests in 22.659s` / `FAILED (failures=6, errors=1)`); dev không ghi tên test và chạy lại cả file, lần sau chỉ còn 6 lỗi mong đợi.

## Không kiểm được từ diff (tech-lead xử lý trước khi tick)
- Reviewer không chạy test: tech-lead chạy lại sau merge, kết quả ở mục dưới.
- Test chỉ xanh khi `_()` trả nguyên câu tiếng Việt: `erp_ai/translations` không tồn tại; `grep -rn "Đường dẫn duyệt" erp_ai --include=*.csv --include=*.po --include=*.json` không ra dòng nào → không có bản dịch nào đổi câu này. Khép.

## Sau merge (tech-lead, `32132a6`, dưới khóa site, `PYTHONPATH` = worktree feat-004)
- `cmd.test_one` `erp_ai/test_change_decision.py`, chạy riêng: `Ran 10 tests in 25.731s` / `OK`, `bench_exit=0`
- Không chạy `cmd.test` cả app (lệnh team-leader cho chặng này).

## Câu trong mã so với AC-26
- Mã: `erp_ai/change_decision.py:13` `BAD_LINK = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa."`; AC-26: trang báo "không hợp lệ". Khớp; không có phát hiện về chữ.

## deferred
- Ngoài diff (reviewer ghi): ca "unknown action" (`("undo", "0" * 128, None)`) gửi hành động lạ cùng chữ ký sai, nên nếu bỏ điều kiện `action not in DECIDERS` ở `change_decision.py:28` thì test vẫn xanh vì `signature_ok` đã từ chối. Sửa ở một task sau: gửi chữ ký hợp lệ tính cho `"undo"` (`_signature(self.proposal.name, "undo")`) để tách riêng phép kiểm hành động.
