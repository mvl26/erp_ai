Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 01 — FEAT-005 T1

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff b653ee1..043307e` (nhánh `team/FEAT-005-task-1`, 2 commit: `b7402ad`, `043307e`; merge `4e6ddf1`)
- Vòng: 2
- Verdict: approve (vòng 2)

## Vòng 1 — request-changes (`b653ee1..b7402ad`)

Lớp 1 (khớp spec): đạt. Mọi ý của Returns có trong mã: `SNAPSHOT_TABLES`; `_snapshot` có `name`; User chỉ `name` + `roles`; dòng con bỏ 10 trường và giữ thứ tự `idx`; bỏ trường mật ở cha và con; giá trị qua `json.loads(frappe.as_json(v))`; không cắt. Chỉ hai file touchpoint.

- major | STD-TEST-2 | erp_ai/agent/tools/test_site_api.py:1197 (cùng site_api.py:217-218) | Tiêu chí "giá trị qua `json.loads(frappe.as_json(v))`" không có test nào phủ: mọi giá trị gieo đã là kiểu JSON sẵn, thay `_snapshot_value` bằng `lambda v: v` thì hai test vẫn xanh | Gieo `datetime.datetime(2026, 11, 14, 8, 30)` thật, khẳng định ra `"2026-11-14 08:30:00"` và `json.dumps(snapshot)` (không `default=`) chạy được
- minor | — | — | 3 điểm nhỏ: `SNAPSHOT_ROW_DROPPED` lặp 9 trường của `SYSTEM_FIELDS`; nhánh bỏ `field == "name"` không có tác dụng; `no_private_properties=True` chưa được khẳng định | tùy dev

Đã kiểm và đủ (bỏ hành vi thì đỏ): thứ tự dòng (gieo idx 2 rồi 1), 10 trường hệ thống của dòng con, trường mật ở dòng con (`api_key`) và ở cha (Email Account `password`), User chỉ `name` + `roles` khi `fields=()`, không cắt (30.000 ký tự so nguyên).

Bằng chứng của dev: RED `AttributeError: module 'erp_ai.agent.tools.site_api' has no attribute '_snapshot'`, `Ran 62 tests in 84.636s` / `FAILED (errors=2)`; GREEN `Ran 62 tests in 20.640s` / `OK`.

## Vòng 2 — approve (`b7402ad..043307e`, re-review theo phạm vi)

- major STD-TEST-2: ADDRESSED (`test_site_api.py:1199,1229-1231`: datetime thật, `Decimal("12.50")` ở cha, `json.dumps(snapshot)` không `default=`)
- minor 1: ADDRESSED (`site_api.py:81`: `(SYSTEM_FIELDS - {"docstatus"}) | {"name", "parentfield"}`, đúng 10 trường)
- minor 2: ADDRESSED (bỏ nhánh thừa)
- minor 3: ADDRESSED (`test_site_api.py:1205,1225`: gieo `__unsaved`, khẳng định không khóa nào bắt đầu bằng `_`)
- Phát hiện mới: không có. minor | — | — | 1 điểm nhỏ: commit `043307e` kiểu `test(...)` nhưng có sửa `site_api.py` | tùy dev

Bằng chứng của dev: đổi phép chuyển giá trị thành hàm đồng nhất → `AssertionError: datetime.datetime(2026, 11, 14, 8, 30) != '2026-11-14 08:30:00'`, `FAILED (failures=1)`; trả lại → `Ran 62 tests in 19.002s` / `OK`.

## Không kiểm được từ diff (tech-lead xử lý)

- `_snapshot` chưa có nơi gọi: kiểu giá trị của bản ghi nạp từ DB ở đường xóa ("mọi trường có giá trị") để T2, T3 kiểm bằng test của chúng.
- `SNAPSHOT_ROW_DROPPED` nay suy từ `SYSTEM_FIELDS`: thêm trường vào `SYSTEM_FIELDS` thì dòng con của ảnh chụp cũng bỏ trường đó; chấp nhận, ghi nhớ khi `SYSTEM_FIELDS` đổi.
- Sau merge `4e6ddf1`, tech-lead chạy `cmd.test_one` test_site_api trên `team/FEAT-005`: `Ran 62 tests in 19.050s` / `OK`. `cmd.test` cả app chạy ở T16.

## deferred

Không có.
