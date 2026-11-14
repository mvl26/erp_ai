Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 12 — FEAT-005 T12

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff aaad5ec..1657f6a` (nhánh `team/FEAT-005-task-12`, 2 commit; vòng 1 `aaad5ec..827d5f8` 2 file +258/−26, vòng 2 `827d5f8..1657f6a` 2 file +72/−2); merge `67f926b`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 request-changes

## Vòng 2 — approve (`827d5f8..1657f6a`, chấm lại có phạm vi)

- major STD-TEST-8: ADDRESSED. `erp_ai/tests/test_tasks.py:1056-1084` thử mọi hình dạng hỏng ở phía `after` khi `before` dùng được; `:1124-1132` thêm dòng có cột `value_after` hỏng, mục của nó được khẳng định ở `:1152-1153`; `:1086-1113` thêm ca Custom DocPerm và DocType với ảnh chụp là chuỗi ở từng phía và cả hai phía `None`. Reviewer lần theo mã `tasks.py:139-150`: đột biến `pair[:1]` và đột biến "chỉ kiểm cho User" đều làm test đỏ.
- minor (a) vòng 1: ADDRESSED. `tasks.py:134-136` đòi `role` là chuỗi không rỗng; `test_tasks.py:1070-1072` phủ dòng thiếu `role` ở từng phía.
- Phát hiện mới: không có blocker/major. minor | — | — | 1 điểm nhỏ: STD-TEST-8 `tasks.py:135`: vế `and row["role"]` chỉ được thử bằng dòng thiếu khóa `role`; bỏ vế đó test vẫn xanh, `{"role": ""}` sẽ ra `thêm role  cho u` | tùy dev
- Bằng chứng của dev vòng 2: đỏ trên `827d5f8` chỉ hai subTest dòng role thiếu khóa `role`: `AssertionError: Lists differ: ['thêm role None cho u (…08:19)', 'gỡ role A của u …'] != ['sửa User u (…08:19), không có trước/sau']`, `Ran 61 tests in 6.947s` / `FAILED (failures=2)`; đột biến `pair[:1]` ở cả hai `all(...)` → `FAILED (failures=4, errors=4)`; đột biến "kiểm dict / (None, None) chỉ cho User" → `FAILED (failures=4, errors=2)`; GREEN `Ran 61 tests in 6.855s` / `OK`.

## Vòng 1 — request-changes (`aaad5ec..827d5f8`)

Lớp 1 đạt: `_load_snapshots` trả `{}` khi `ValueError`/`TypeError` (có chú thích lý do) và khi cột không phải dict; khóa thiếu, một phía không phải dict, cả hai phía `None`, hoặc User không có danh sách dòng role → 1 mục có đuôi `, không có trước/sau`; `actions` không đọc được → `ERP AI Log <dòng>, không có trước/sau`. Ghi chú review-09 giữ nguyên: lệnh xóa có `after=None` vẫn ra `gỡ role C của deleted` (`test_tasks.py:1006`), phép khẳng định của T9 không đổi. Chỉ sửa trong touchpoint.

Phép khẳng định có sẵn bị đổi, chấm theo STD-TEST-5: bốn test (`test_window_excludes…` `:515,517`, `test_empty_watermark…` `:563`, `test_only_ok_generic_writes…` `:954-956`, `test_empty_instructor…` `:1131`) thêm đuôi `NO_BEFORE_AFTER`; cả bốn gieo dòng không có khóa ảnh chụp, design-amd2 §3.3 / §4.2 bước 3 ("dòng cũ, khóa thiếu") nay đòi đuôi đó → đổi theo spec, đạt. `test_admin_items_first_each_group_by_time` (`:892-924`) đổi phần gieo và giá trị kỳ vọng để sắp theo chữ trong nhóm thì đỏ (đóng minor (a) của review-10) → test mạnh hơn, đạt. Test thêm `test_unusable_snapshot_shapes_listed_without_before_after` phủ đúng các hình dạng tiêu chí liệt kê, không phải việc thừa. Chữ mục cho User có ảnh chụp không dùng được (`sửa User <user> (…), không có trước/sau`) theo mẫu bản ghi của §3.3 và nêu tên user như ADR-024 đòi.

- major | STD-TEST-8 | erp_ai/tests/test_tasks.py:1012-1054 (code tasks.py:137-149) | Mọi ca hình dạng hỏng chỉ đổi phía `before` của một hành động User, `after` luôn dùng được (`after or usable_after`). Tương tự ở :1058-1062 (cột `value_before` hỏng, `value_after` lành). Không test nào đưa ảnh chụp không phải dict hoặc cả hai `None` cho DocType phân quyền khác User (Custom DocPerm, DocType). Hai đột biến vẫn xanh: chỉ kiểm `pair[:1]` ở cả hai `all(...)`, và chỉ chạy phép kiểm dict / (None, None) cho User. Với `after` hỏng, `_role_counts` ném AttributeError (cho `"u"` hoặc `["System Manager"]`), làm im cả bốn điều kiện, đúng ca ADR-024 QĐ 1 cấm. Với `roles: {}` thì ra mục `gỡ role …` sai. | Thêm subTest `before` dùng được và `after` mang từng hình dạng hỏng (không phải dict, roles không phải list, `{}`, dòng role không phải dict, thiếu roles), thêm một dòng có cột `value_after` hỏng; thêm một hành động Custom DocPerm và một hành động DocType với ảnh chụp là chuỗi và với cả hai phía `None`, mỗi ca kỳ vọng đuôi
- minor | — | — | 2 điểm nhỏ: (a) dòng role là dict nhưng thiếu khóa `role` tính là `None`, ra `thêm role None cho u` (STD-TEST-8); (b) thân commit nêu 4 chỗ thêm đuôi nhưng không nêu việc đổi phần gieo của `test_admin_items…` (STD-GIT-1) | tùy dev

- Bằng chứng của dev vòng 1: RED `json.decoder.JSONDecodeError` / `AttributeError: 'str' object has no attribute 'get'` / `AssertionError: Expected 'log_error' to not have been called. Called 1 times.`, `Ran 59 tests in 12.339s` / `FAILED (failures=11, errors=8)`; GREEN `Ran 59 tests in 6.952s` / `OK`.

## Tech-lead đã kiểm

- Sau merge `67f926b`, một lần giữ khóa `miyano-site.lock` (migrate exit 0): test_tasks `Ran 61 tests in 8.105s` / `OK`.
- `git diff --name-only aaad5ec..1657f6a` = `erp_ai/tasks.py`, `erp_ai/tests/test_tasks.py` (đúng touchpoint).

## Không kiểm được từ diff

- Mục User có ảnh chụp không dùng được không mang dấu `[QUẢN TRỊ]` (không biết role) nên xếp sau nhóm quản trị; 5 mục thường có thể đẩy nó vào "…và N mục khác" dù nó có thể che một lần cấp role quản trị. design-amd2 §3.3 không quyết ca này → tech-lead: không phải lỗi của dev, ghi debt.md (điểm thiết kế), báo team-leader.
- `actions LIKE "%api_%"` (mã có từ trước): cột `actions` hỏng mà không có chuỗi đó thì không bao giờ được đọc; design-amd2 §2 chấp nhận.

## deferred

- minor mới của vòng 2 (`{"role": ""}` chưa có ca) → debt.md.
