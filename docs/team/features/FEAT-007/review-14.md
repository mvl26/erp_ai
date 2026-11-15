Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 14 — FEAT-007 T14

- Diff: `git diff 354e3c11c8247ee0d5847ad638aa1ce15064e2b2..e0fae80` (nhánh `team/FEAT-007-task-14`, 1 commit `e0fae80`, 4 file +235/−5)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline 354e3c1..team/FEAT-007-task-14`, `git diff --stat …`, `git diff …`, `git log -1 --format='%an <%ae>%n%B' e0fae80`; `git show team/FEAT-007-task-14:` cho `erp_ai_setting.py`, `agent/tools/source.py`, `test_utils.py` (`TempAppsRoot`), `install.py` (`_ensure_default_settings`), `test_erp_ai_setting.py:640-760`.
- Bằng chứng của dev: RED khi đã migrate trường mà chưa có kiểm, `Ran 64 tests in 3.149s FAILED (failures=19)`: `AssertionError: ValidationError not raised` (6 giá trị biên của 3 trường Int), `AssertionError: None != "Kho HDSD 'myapp/khong_co' phải là thư mục có sẵn dưới apps/"` (cùng dạng cho 10 đường dẫn sai), `AssertionError: '\tmyapp ' != 'myapp'`; không có lần RED riêng cho `test_doctype_descriptions`. GREEN một lần giữ khóa, migrate exit 0: `test_erp_ai_setting` `Ran 64 tests in 3.082s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.347s OK`; `test_architecture` `Ran 112 tests in 3.324s OK`; `test_install` `Ran 37 tests in 16.788s OK`.
- Lớp 1 (khớp spec):
  - Đủ: `section_knowledge` giữ 9 trường đúng thứ tự `design.md:107`, đứng sau `code_change_apps` và trước `section_alerts` (hàng 12–13 chưa dựng). Kiểu và mặc định khớp `design.md:129-137`: 4 ô Check mặc định 0; `close_silent_f_days` 3, `knowledge_search_limit` 5, `report_row_limit` 20. Ba dòng `INT_LIMITS` mới là 1..30, 1..20, 1..100, chữ lỗi "<nhãn> phải từ a đến b". E-7 (`check_manuals_dir`): ô trống thì bỏ qua; ngược lại giá trị được trim, phải qua `resolve_safe_path` và `os.path.isdir`; chính `apps/` bị từ chối vì `_inside` ở `source.py` kiểm `full != root`. Thông điệp có thêm escape HTML so với chữ thiết kế, cùng cách đã nhận ở E-1 của T13. `allowed_reports` chỉ là trường (kiểm thuộc T15). Các file `design-w0-fixes*.md` và addendum không đổi E-7 hay các trường này.
  - Không thừa: 4 file, đúng touchpoints, không file mới.
- STD-TEST-5, phép khẳng định thứ tự trong `test_code_change_block_follows_feat006_fields`: được nối dài theo bảng thứ tự của `design.md`, không nới; message của commit ghi lý do, đúng điều kiện ở dòng "Bổ sung của tech-lead" (T13).
- Test đỏ được không (đột biến đọc theo mã): bỏ `isdir` → hai mục là file (`myapp/docs/hdsd.md`, `myapp/ok.py`) lưu được, test đỏ; đi vòng `resolve_safe_path` → `../outside`, đường dẫn tuyệt đối bên ngoài, symlink `myapp/dir_out`, `.`, `myapp/..` và đường dẫn gốc lưu được, test đỏ; bỏ `strip` → giá trị bị từ chối được gõ kèm khoảng trắng và thông điệp mong đợi dùng chữ đã trim, `\tmyapp ` phải lưu thành `myapp`, cả hai đỏ; bỏ escape → ca `<b>x</b>` đỏ. Sau mỗi lần từ chối test kiểm giá trị đã lưu không đổi. Mỗi trường Int được thử ở low−1 và high+1 (bị chặn, đúng chữ) và ở low, high (lưu được, đọc lại). Mặc định: test đọc giá trị cài đặt ghi từ `default` của trường; đổi một mặc định là đỏ.

### Phát hiện (chỉ blocker/major)

Không có blocker, không có major.

minor | — | — | 3 điểm nhỏ: (a) STD-TEST-1: không có lần RED riêng cho `test_doctype_descriptions` và `test_section_and_field_shape`; đọc diff thì chúng đỏ ở BASE (`field_count` 50 so với 59, thiếu trường); (b) STD-DOC-2: mô tả của `allowed_reports` nói báo cáo "bị chặn khi lưu", nhưng phép kiểm đó chỉ có từ T15, nên chữ nói quá cho tới lúc đó; (c) mô tả của `kb_draft_enabled` nói "khi phiếu được giải quyết", còn AC-45 phủ Resolved hoặc Closed trừ đóng sau im lặng | tùy dev

### Review checklist (10)

1. đạt (đủ tiêu chí, không thừa) 2. đạt (4 file trong `files:`, không file mới) 3. đạt (RED cho 3 trường Int, 10 đường dẫn sai và trim, biên hai phía; không skip/xfail; RED thiếu của test mô tả ở dòng minor) 4. đạt (phép khẳng định thứ tự chặt hơn theo bảng thiết kế; lớp test mới dùng `keep_agent_settings`, rollback và `TempAppsRoot`) 5. đạt (đầu vào form được kiểm khi lưu; không thêm catch, không gọi dịch vụ ngoài) 6. đạt (đường dẫn người gõ được escape; không ra khỏi `apps/` kể cả qua symlink; không đụng `protected_paths`) 7. đạt (chỉ thêm trường Single có mặc định; dev báo migrate exit 0) 8. đạt (tên theo thiết kế, theo kiểu sẵn có của file) 9. đạt (chỉ thêm `os` của thư viện chuẩn) 10. đạt (một task một commit, `feat(setting): … (FEAT-007)`, không trailer AI; mô tả trường mang chữ cho người dùng)

## Không kiểm được từ diff — kết luận của tech-lead

- Reviewer không chạy test; `cmd.lint` chưa thấy → tech-lead chạy `cmd.migrate` rồi `cmd.test_one` cho 4 module trên `team/FEAT-007` sau merge (một lần giữ khóa site) và `cmd.lint`; đầu ra ở dòng `progress:` của T14 trong `tasks.md`.
- RED ghi 19 failure, các phần liệt kê cộng lại khoảng 17–18: phần dư là các subtest (ca escape `<b>x</b>`, ca `'   ' != ''`) dev đã liệt kê trong báo cáo; mọi dòng RED là phép khẳng định, không phải lỗi import. Nhận.
- `resolve_safe_path` cũng từ chối thư mục có tên bị chặn (ví dụ chứa `secret`, `credential`) với thông điệp E-7 chung: đúng lựa chọn của thiết kế (`design.md` E-7 dùng `resolve_safe_path`); kho HDSD thật có tên như vậy thì người cấu hình sẽ gặp lỗi lúc lưu, không lộ gì. Nhận, ghi cho `/team:verify`.
- Khi U6a (T38) về, `resolve_safe_path` sẽ từ chối file trong kho HDSD; phép kiểm thư mục của task này phải còn qua (`design.md:308`). Chỉ kiểm được khi T38 có: chép thành điều phải kiểm ở lời giao T38 (chạy lại `test_erp_ai_setting`).
- Mô tả `allowed_reports` (điểm (b)) chỉ đúng sau T15: T15 là task kế trong chuỗi và cùng đợt 0, không bản phát hành nào đứng giữa. Nhận.

## deferred

- 3 điểm nhỏ ở trên: (b) và (c) là chữ mô tả, gom vào task chữ mô tả của kế hoạch đợt 1a nếu team-leader muốn; (a) không cần làm lại.
