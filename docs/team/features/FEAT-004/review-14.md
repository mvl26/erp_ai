Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 14 — FEAT-004 T14

- Diff: `git diff dee2daa..team/FEAT-004-task-14` (2 commit `2a4ad58`, `bdd79e1`; 2 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff dee2daa..2a4ad58`)
Lớp 1: AC-5, AC-6 (khi chạy lần lượt), AC-12, NFR-2, NFR-6 có; đủ 7 test Expect; chỉ 2 file touchpoint. Thiếu phủ D-2.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/changes/transitions.py:149 | D-2 là tiêu chí của T14 (khóa dòng bằng `get_value(..., for_update=True)` rồi so, rồi `set_value`) nhưng không test nào kiểm khóa; bỏ `for_update=True` thì 40 test vẫn xanh; hai lần duyệt chạy đua sẽ cùng qua kiểm `Chờ duyệt` (AC-6, ADR-012 QĐ 3) | thêm test bọc `frappe.db.get_value` bằng `wraps=`, kiểm mỗi phép chuyển đọc `PROPOSAL_DOCTYPE` với `for_update=True` trước `set_value` |

minor | — | — | 3 điểm nhỏ: `raise frappe.DoesNotExistError(...)` thay vì `frappe.throw(msg, frappe.DoesNotExistError)` (design 3.3); `update_modified=True` chỉ kiểm cho approve; 27 s cho 40 test không phải lỗi STD-TEST-6 (khoảng 200 lần insert đề xuất) | tùy dev

Các điểm đã chấm:
- (a) `finish` thêm `before=`, `after=` so với design 3.5 và Returns; design 4.3 bước 3.7, 4.4 bước 7 và khối T19/T20 gọi `finish` với hai tham số đó → mã theo nơi gọi; design 3.5 lạc hậu (việc của designer), không là phát hiện.
- (b) QĐ-A3 ghi `exit_code` rỗng (`None`) trên đề xuất: cột Int của Frappe 15 là `not null default 0` nên không lưu được; mã lưu 0 trên đề xuất và `None` ở `value_after` của dòng log; form sẽ hiện "Mã thoát 0" cho lệnh lỗi. Designer sửa QĐ-A3 trước T21.
- (c) Câu lỗi khớp 3.3. Tên rỗng/không phải chuỗi → `ValueError` ở đây; 3.3 và 4.2 đặt kiểm đó ở method → T16 phải kiểm trước khi gọi transitions.
- (d) 6 cạnh của `finish` + approve, reject, begin_apply, request_undo = đúng 11 cạnh design 2.2; test so 81 cặp trạng thái với bảng viết tay.

## Vòng 2 — approve (re-review theo phạm vi, `git diff 2a4ad58..team/FEAT-004-task-14`)
- Phát hiện 1: ADDRESSED (`test_transitions.py:834-876` `TestLockBeforeWrite`: 5 phép chuyển, mỗi phép đúng một `get_value(..., for_update=True)` trước `set_value` đầu tiên)
- Minor dev đã sửa: `frappe.throw(msg, frappe.DoesNotExistError)` (`transitions.py:152`, test `:814-820`); `update_modified=True` kiểm ở mọi phép chuyển (`:876`)
- Phát hiện mới: không có blocker/major; minor: test kiểm khóa đứng trước ghi, chưa kiểm đứng trước phép so

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: `AttributeError: module 'erp_ai.agent.changes.transitions' has no attribute 'finish'`, `FAILED (errors=273)`; GREEN: test_transitions `Ran 40 tests in 27.847s` / `OK`; test_architecture `Ran 108 tests in 1.768s` / `OK`
- Vòng 2 RED: `(function='approve') AssertionError: 0 != 1 : [call.get_value('ERP AI Change Proposal', 'AICHG-00001', ['change_status', 'change_kind'], as_dict=True), …]`, `FAILED (failures=10)`; `(function='begin_apply') AssertionError: False is not True`, `FAILED (failures=1)`; GREEN: test_transitions `Ran 42 tests in 28.985s` / `OK`; test_architecture `Ran 108 tests in 1.895s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Design 2.5: dòng `fail` có `apply_commit_sha` phải mang `value_after.commit`; `finish` không tự điền → ghi vào handoff T19, T45, T47 (`after={"commit": sha}`).
- `finish` ghi `set_value` trước `log_step`; commit/rollback quanh `finish` là việc của `run_change` (T18) → ghi vào handoff T18.
- T16: kiểm tên rỗng/không phải chuỗi trước khi gọi transitions → ghi vào handoff T16.
- `cmd.test` sau merge: xem tasks.md.

## deferred
- Designer: design 3.5 thêm `before=`, `after=` vào chữ ký `finish`; QĐ-A3 `exit_code` rỗng không lưu được (cột Int NOT NULL) → chốt trước T21.
