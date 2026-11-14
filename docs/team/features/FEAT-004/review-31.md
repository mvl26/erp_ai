Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 31 — FEAT-004 T31

- Diff: vòng 1 `git diff 1a82772..352f5c2`; vòng 2 `git diff 352f5c2..3cf8412`; vòng 3 `git diff 3cf8412..6530910` (nhánh `team/FEAT-004-task-31-r2`; cả task: `git diff 1a82772..6530910`, 1 file `erp_ai/tests/test_architecture.py`)
- Vòng: 3 (max_rework=3)
- Verdict: approve

## Vòng 1 — request-changes (`git diff 1a82772..352f5c2`, +492)
Lớp 1: đủ 5 luật, mỗi luật một ca bị bắt và một ca sạch; test dương chạy trên cây thật qua `load_product_sources()` (gồm `change_decision.py`, `site_api.py`, `propose_change.py`, `apply_job.py`); `STATE_FIELDS` so với `transitions.STATE_FIELDS` bằng `literal_eval`; luật transitions bắt cả import có bí danh, import trong thân hàm, import tương đối.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/tests/test_architecture.py:2081-2103 | `check_tool_never_saves_proposal` không thấy tool duy nhất lưu DocType bất kỳ: `site_api.py:165-169`, `:188`; đề xuất chỉ được giữ ngoài nhờ `PROPOSAL_DOCTYPE` trong hai tập cấm; bỏ nó khỏi tập thì luật vẫn xanh | module tool nào `get_doc`/`delete_doc` với DocType không hằng rồi `.save`/`delete` phải có `PROPOSAL_DOCTYPE` trong mọi tập cấm; thêm ca bị bắt |
| major | STD-TEST-2 | erp_ai/tests/test_architecture.py:2016-2048 | `check_change_guard_uses_resolve_safe_path` chỉ kiểm có lời gọi; hàm `_real(p)` làm `realpath` + `commonpath`, hoặc xóa `if full is None: return _refused(...)` vẫn xanh | kiểm kết quả `resolve_safe_path` được so `None` và dẫn tới từ chối; bắt kiểm gốc ngoài `source.py` theo danh sách cho phép viết tay |
| major | STD-TEST-2 | erp_ai/tests/test_architecture.py:1966-1972 | `_state_field_writes` sót `frappe.qb.update(T).set(T.change_status, v)` và `doc.update(dict(change_status=v))` | nhận đối số Attribute; thêm `dict` |

## Vòng 2 — request-changes (`git diff 352f5c2..3cf8412`, +288/-14)
- Phát hiện 1: ADDRESSED (`:2172-2240`)
- Phát hiện 2: ADDRESSED một phần ((b) xong, `_refuses_when_unresolved` ở `:2044`; (a) mới chỉ bắt đúng ví dụ)
- Phát hiện 3: ADDRESSED (`:1995-1996`, `:1908`, ca bị bắt `:4080-4081`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/tests/test_architecture.py:2058-2064 | `_root_check_functions` chỉ bắt khi `realpath` và `commonpath`/`is_relative_to` cùng một hàm; chính `source.py:102-103`, `:112-114` tách hai việc ra hai hàm, bản sao hình dạng đó vẫn xanh | bắt mọi lời gọi `commonpath`/`is_relative_to` ngoài `source.py` không thuộc `ROOT_CHECK_ALLOWLIST` |

## Vòng 3 — approve (`git diff 3cf8412..6530910`, +53/-17)
- Phát hiện vòng 2: ADDRESSED (`:2058-2066`, `:2114-2122` `_root_check_calls`; ca bị bắt `:4153-4172` "root check split from realpath", "root check at module level"); điểm nhỏ `get_doc(doctype=…)` chỉ từ khóa cũng xong (`:2177-2185`, `:4352-4359`)
- Sửa của các vòng trước không bị nới (luật tập cấm chỉ rộng thêm; `_refuses_when_unresolved` nguyên; ca `qb.set`/`dict` nguyên; test danh sách cho phép đóng 2 mục nguyên)
- Phát hiện mới: không có

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Lần 1 RED (trước khi có luật): `FAIL: test_transitions_import_caught_outside_controller_and_changes … AssertionError: 0 not greater than 0 : scanner missed the violation`; luật transitions đỏ đúng trên `runner.py:11` cho tới khi T30 bỏ import; import lại tạm thời: `'agent/runner.py:11: imports erp_ai.agent.changes.transitions (ADR-012: only the proposal controller and agent/changes/ use the state machine)'`
- Vòng 2 RED: `Items in the second set but not the first: ('eval/export_tickets.py', '_inside_repo')`; các ca `denied set lacks it`, `refusal of the resolver not kept`, `qb set attribute`, `dict() keyword`: `scanner missed the violation`; GREEN `Ran 128 tests in 3.508s` / `OK`
- Vòng 3 RED: `FAIL: test_change_guard_without_resolve_safe_path_caught (case='root check split from realpath') AssertionError: 0 not greater than 0 : scanner missed the violation`; GREEN `Ran 128 tests in 3.380s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Mục `("eval/export_tickets.py", "_inside_repo")` trong `ROOT_CHECK_ALLOWLIST` (tech-lead phán ở round 55): reviewer thấy hợp ý định của ADR-011 QĐ 4 (canh đường ghi dùng chung; `_inside_repo` là phép kiểm ngược "từ chối khi nằm trong repo" của bản xuất eval) nhưng KHÔNG hợp chữ Ràng buộc dòng 44 ("không có hàm khử symlink/kiểm gốc thứ hai trong `erp_ai/**`", không ngoại lệ) → cần architect phán: thu hẹp phạm vi Ràng buộc, ghi ngoại lệ vào ADR, hoặc chuyển `export_tickets` sang helper chung ở `source.py`. Không chặn T31; báo team-leader.
- Chữ design 8.2 có hai dòng không thể đúng trên cây thật ("tên trường trạng thái không xuất hiện ngoài `agent/changes/`"; "không `.save(` trong `tools/**`") → cho designer sửa chữ (luật theo ADR-012: chỉ cấm ghi).

## deferred
- Cho architect cùng mục trên: `change_guard.py:210-212` `_app_refusal` dùng `realpath` + `dirname(target) != root`, một kiểu kiểm gốc thứ ba luật chưa thấy; danh sách `ROOT_CHECK_CALLS` chưa có `Path.relative_to`, `commonprefix`, `startswith(root)`.
- Khi làm M3 của CHG-001 (tập cấm dẫn xuất từ `read.denied_doctypes()`): luật tập cấm phải nhận dạng mới.
- Điểm nhỏ: import có bí danh `from os.path import commonpath as cp` chưa bị bắt; `get_doc(**kw)` bị bỏ qua; luật kiểm nội dung tập cấm chứ chưa kiểm `site_api.py:62` có tra tập đó.
