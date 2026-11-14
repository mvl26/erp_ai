Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 32 — FEAT-004 T32

- Diff: `team/FEAT-004-task-32` @ `02a9715`, base `efebbe1` (1 commit, 1 file `erp_ai/tests/test_architecture.py`, +369)
- Vòng: 2 (vòng 1: request-changes; vòng 2: diff sửa `02a9715..a9e0f0b`)
- Verdict: approve

Lệnh đã dùng (chỉ đọc):
```
git log --oneline efebbe1..team/FEAT-004-task-32
git diff --stat efebbe1..team/FEAT-004-task-32
git diff efebbe1..team/FEAT-004-task-32
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T32'
git show team/FEAT-004:docs/team/adr/ADR-013.md | grep -n -A12 'Ràng buộc'
git show team/FEAT-004:docs/team/features/FEAT-004/design.md   (mục 8.2)
git show efebbe1:erp_ai/tests/test_architecture.py | grep -n 'def test_.*enqueue|def test_.*subprocess|...'
git show team/FEAT-004-task-32:erp_ai/tests/test_architecture.py | grep -n ...   (số dòng)
```

## Lớp 1 — khớp spec
- `check_fs_writes_only_in_file_writer` (`test_architecture.py:2574`): phủ đủ danh sách của ADR-013 Ràng buộc 2 (`open(` mode `w/a/x/+`, `write_text`, `write_bytes`, `os.replace/rename/remove/unlink`, `shutil.`) và rộng hơn (tempfile, os.open flags, Path.open, alias, tham chiếu như giá trị); miễn đúng `agent/changes/file_writer.py`; `eval/` ngoài phạm vi có test sạch. Test dương trên mã thật kiểm máy quét thấy `os.replace`, `os.remove`, `tempfile.mkstemp`, `os.fdopen ... 'wb'` trong file_writer → không phải quét mù.
- `check_changes_never_set_user_or_publish` (`:2634`): `frappe.set_user`, `publish_realtime`/REALTIME_NAMES, gán `frappe.session.user` dưới mọi dạng (khớp ý ADR-013 QĐ dòng 31 "không gọi `frappe.set_user`: chạy dưới user đã duyệt").
- Xác nhận test âm của luật enqueue (2 lời gọi) và luật subprocess (hai file, shape riêng `process_runner.py`): đã có ở base (`test_enqueue_call_shape_requires_exactly_two_calls`, `..._requires_each_target_once`, `..._rejects_target_outside_set`, `..._requires_five_parameters_on_each_call`; `test_subprocess_call_shape_applies_to_process_runner`, `..._timeout_wrapped_git_needs_group_cwd_and_own_env`, `..._checks_run_wrapped_callers_in_process_runner`); diff thêm 2 test âm cho các file đường thay đổi (`test_single_enqueue_catches_change_path_files`, `test_subprocess_caught_in_change_path_files`).
- Thừa: `sendmail` bị cấm trong `agent/changes/**` — không có trong T32 Returns, ADR-013 Ràng buộc (dòng 55 chỉ `frappe.set_user`, `publish_realtime`), design 8.2; docstring ghi "widened by task T32 to sendmail" nhưng task không nói vậy. Xem phát hiện 1.
- Bằng chứng RED khớp số ca: 35 ca × 6 file = 210, 19 ca × 3 file = 57.

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-5 | erp_ai/tests/test_architecture.py:2499, :2635, :4952-4953 | Luật kiến trúc mới cấm `sendmail` trong `agent/changes/**`: không task, ADR hay design nào yêu cầu; docstring gán nguồn sai ("widened by task T32"). Đây là ràng buộc kiến trúc không có ADR, trong khi cách báo kết quả AC-28 (T56/T57) còn chờ designer — luật này có thể chặn trước một phương án chưa quyết. confirmed | Bỏ `"sendmail"` khỏi `CHANGES_FORBIDDEN_NAMES`, xóa 2 ca `sendmail*`, sửa docstring chỉ còn phần mở rộng có căn cứ (gán session user); hoặc nếu muốn giữ, architect ghi vào ADR-013 Ràng buộc trước rồi docstring trỏ tới đó |

minor | — | — | 5 điểm nhỏ: (a) nhánh import của `_fs_writes` (`:2551`) và nhánh `_names_forbidden(target)` khi import (`:2644`) bị nhánh "uses" che, không ca nào chỉ nhánh import bắt được (STD-TEST-8); (b) nhánh `os.open` với flags qua `**kwargs` (`:2524`) và gán `AugAssign/AnnAssign` lên session (`:2604`) không có ca âm (STD-TEST-8); (c) docstring `:2575` nói "writing, renaming or removing files" nhưng `Path(p).rename(q)` / `Path(p).replace(q)` không bị bắt (ngoài danh sách ADR; cố ý để tránh `str.replace`/`doc.rename`) — nên ghi rõ khoảng hở trong docstring (STD-DOC-7); (d) `zipfile.ZipFile(p, 'w')`, `os.utime`, `os.mkfifo` không bị bắt (ngoài danh sách ADR); (e) `test_changes_never_set_user_or_publish` chống quét mù chỉ bằng "> 3 file" | tùy dev

## Review checklist (10)
1. Đúng và đủ spec, không thừa — trượt (STD-DESIGN-5: `sendmail`); hai hàm Returns và xác nhận test âm enqueue/subprocess: đạt.
2. Touchpoint — đạt: chỉ `erp_ai/tests/test_architecture.py`, không file mới.
3. Test trước, cạnh và lỗi, không skip — đạt: RED 267 lỗi khớp số ca; không thêm marker skip/xfail; điểm phủ nhánh nhỏ ở dòng minor.
4. Không sửa test cho khớp hành vi sai; độc lập — đạt: chỉ thêm test, quét nguồn tĩnh, không DB/mạng/thời gian.
5. Lỗi, biên, timeout — không áp dụng (mã test tĩnh); đạt.
6. Bí mật, injection, quyền — đạt: không chạm `protected_paths`, không bí mật.
7. Hợp đồng API/dữ liệu — đạt: không đổi hàm có sẵn; hằng mới thêm, hằng cũ giữ.
8. Tên, cấu trúc, style, dead code — đạt: tên theo snake_case/UPPER_CASE như file; không dead code.
9. Phụ thuộc mới — không có; đạt.
10. Commit, nhánh — đạt: `test(architecture): ... (FEAT-004)`, nhánh `team/FEAT-004-task-32`, 1 commit.

## Không kiểm được từ diff
- Handoff của tech-lead cho dev có yêu cầu thêm `sendmail` không (docstring nói "widened by task T32") → tech-lead đối chiếu; nếu có, chuyển phát hiện 1 thành việc của architect (ghi vào ADR-013) thay vì của dev.
- GREEN `Ran 141 tests ... OK` với mã sản phẩm sạch dưới hai luật: reviewer không chạy (đề xuất `cmd.test_one erp_ai/tests/test_architecture.py` trên nhánh).
- Mã sản phẩm mới hơn base (T56/T57 nếu chọn `frappe.set_user`/email cho AC-28) sẽ va luật này → tech-lead xếp thứ tự merge.

## Deferred
- Không có (vòng 1).

## Vòng 2

- Diff sửa: `team/FEAT-004-task-32` @ `a9e0f0b`, base `02a9715` (1 commit, 1 file `erp_ai/tests/test_architecture.py`, +6/−61)
- Verdict: approve

Lệnh đã dùng (chỉ đọc):
```
git log --oneline 02a9715..team/FEAT-004-task-32
git diff --stat 02a9715..team/FEAT-004-task-32
git diff 02a9715..team/FEAT-004-task-32
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A5 '^- \[ \] T32'
git show team/FEAT-004:docs/team/adr/ADR-013.md | grep -n -B2 -A12 'Ràng buộc'
git show {02a9715,team/FEAT-004-task-32}:erp_ai/tests/test_architecture.py | grep -n -E 'REALTIME_NAMES|REALTIME_MODULE|_is_constant\(|SESSION_NAMES|_session_user_writes|_is_session|sendmail|publish_progress|module_in\('
git show team/FEAT-004-task-32:erp_ai/tests/test_architecture.py | sed -n '2586,2620p;4880,4925p'
```

### Phát hiện vòng 1
| # | Phát hiện | Trạng thái | Bằng chứng |
|---|---|---|---|
| 1 | major STD-DESIGN-5 — `sendmail` bị cấm trong `agent/changes/**` không có căn cứ; docstring gán nguồn sai | ADDRESSED | `test_architecture.py:2500` `CHANGES_FORBIDDEN_NAMES = ("set_user", "publish_realtime")` — đúng hai tên ở ADR-013 Ràng buộc dòng 55 ("Trong `erp_ai/agent/changes/**` không có `frappe.set_user`, `publish_realtime`."); docstring `:2594-2596` trích đúng câu ADR, bỏ "widened by task T32"; hai ca `sendmail*` đã xóa (`:4893-4901` còn 8 ca) |

Dev thu hẹp thêm ngoài phần phát hiện đề nghị (bỏ `publish_progress`, `emit_via_redis`, import module `frappe.realtime`, và toàn bộ luật ghi session user cùng `SESSION_NAMES`/`_is_session`/`_session_user_writes`). Đối chiếu nguồn: ADR-013 Ràng buộc chỉ nêu `frappe.set_user`, `publish_realtime`; T32 Returns chỉ nêu tên hàm. Thu hẹp về đúng căn cứ → không phải phát hiện. Không còn mã chết: `REALTIME_NAMES`, `REALTIME_MODULE`, `_is_constant`, `module_in` vẫn dùng ở các luật khác (`:313-314`, `:959`, `:971-996`, `:1087-1093`); `aliases` vẫn dùng cho `resolved_name` trong hàm. Số ca khớp bằng chứng của dev: 8 ca × 3 file = 24 ⇒ `FAILED (failures=24)` khi stub luật về `[]`. Test sạch `test_changes_session_reads_and_other_modules_are_clean` không đổi; chuỗi `'never calls set_user or publish_realtime'` vẫn sạch vì `_names_forbidden` cần khớp nguyên tên hoặc hậu tố `.`+tên.

### Phát hiện mới (chỉ blocker/major)
Không có.

### Review checklist (10) — chỉ trên diff sửa
1. Đúng và đủ spec, không thừa — đạt: danh sách cấm bằng đúng ADR-013 Ràng buộc; hàm Returns của T32 giữ nguyên.
2. Touchpoint — đạt: chỉ `erp_ai/tests/test_architecture.py`.
3. Test trước, cạnh và lỗi, không skip — đạt: không thêm marker skip/xfail; stub luật → 24 lỗi (bằng chứng dev, khớp số ca).
4. Không sửa test cho khớp hành vi sai; độc lập — đạt: chỉ xóa ca của phần luật bị gỡ; ca của hai tên ADR giữ nguyên.
5. Lỗi, biên, timeout — không áp dụng (mã test tĩnh).
6. Bí mật, injection, quyền — đạt: không chạm `protected_paths`.
7. Hợp đồng API/dữ liệu — đạt: không đổi hàm/hằng dùng chung (`REALTIME_NAMES` giữ nguyên cho luật realtime ADR-008).
8. Tên, cấu trúc, style, dead code — đạt: helper session đã xóa hết, không còn tham chiếu.
9. Phụ thuộc mới — không có.
10. Commit, nhánh — đạt: `test(architecture): limit the agent/changes rule to set_user and publish_realtime as ADR-013 names (FEAT-004)`, 1 commit trên `team/FEAT-004-task-32`.

### Không kiểm được từ diff
- GREEN `Ran 141 tests ... OK` và `FAILED (failures=24)`: reviewer không chạy (đề xuất `cmd.test_one erp_ai/tests/test_architecture.py` trên nhánh).
- Việc bỏ luật ghi session user là quyết định phạm vi: nếu architect muốn cấm cả việc gán `frappe.session.user` trong `agent/changes/**` (ý ADR-013 QĐ "chạy dưới user đã duyệt"), cần thêm dòng vào ADR-013 Ràng buộc trước → tech-lead/architect quyết định.

### Deferred (không chặn vòng này)
- minor (a) vòng 1 còn đó: nhánh import `_names_forbidden(target)` (`:2603-2604`) bị nhánh "uses" che — mọi ca import có tên được dùng lại; không ca nào chỉ nhánh import bắt được (STD-TEST-8).
- minor (e) vòng 1 còn đó: test chống quét mù của luật này chỉ bằng "> 3 file".
