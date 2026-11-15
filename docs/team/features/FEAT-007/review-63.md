Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 63 — FEAT-007 T63

- Diff: `git diff 7821d401614544b778d8a13505e82fa35477a337..3d5f7ce` (nhánh `team/FEAT-007-task-63`; 1 commit, 3 file +57/−2)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `7af5fa7` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `test_hard_bans` `AssertionError: None != 'bảng con của DocType khác'` cho subTest `DocPerm`, `Has Role`, `About Us Team Member`, `Ran 9 tests ... FAILED (failures=3)`; RED `test_erp_ai_setting` `AssertionError: 'Danh mục dòng 1: trường title không có trên DocPerm' != 'Danh mục dòng 1: DocType DocPerm bị cấm cứng: bảng con của DocType khác'`, `Ran 103 tests ... FAILED (failures=3)`; GREEN `Ran 9 tests in 0.179s OK`, `Ran 103 tests in 7.573s OK`; `test_architecture` `Ran 181 tests in 15.563s OK`.
- Nhận xét của tech-lead về RED: đỏ vì thiếu hành vi (hàm trả `None` cho bảng con), không phải lỗi import hay cú pháp.
- Tier 1 (đối chiếu spec): đạt. `hard_bans.py:29-30` đọc `meta.istable` từ `frappe.get_meta`, không viết tay tên DocType; chữ ký giữ nguyên; DocType không tồn tại vẫn ném `DoesNotExistError` (có test); lúc lưu `erp_ai_setting.py:555` dùng cùng hàm; lý do mới không chứa "danh mục" (AR3-1), `test_hard_bans.py:96` khóa điều này. Không file nào ngoài `files:`.
- Checklist (10): 1 đạt · 2 đạt · 3 đạt (RED rồi GREEN ở cả hai file; ca biên: `ToDo`, `Note` không bị cấm; bảng con của app vẫn nhận `REASON_DENIED`; DocType không tồn tại; lưu bị từ chối thì dòng đã lưu không đổi) · 4 đạt (không assertion cũ nào đổi; `keep_agent_settings`, rollback) · 5 đạt · 6 đạt (siết thêm quyền) · 7 đạt về mã · 8 đạt · 9 không áp dụng · 10 đạt (1 commit `feat(hard-bans): … (FEAT-007)`).

### Findings

Không có blocker, không có major.

- minor | STD-DESIGN-4 | `erp_ai/agent/test_hard_bans.py:82-87`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:1181-1187` | hàm tìm bảng con ngoài các tập cấm bị chép hai lần | gom về một helper test
- minor | STD-TEST-6 | `erp_ai/agent/test_hard_bans.py:101` | `limit=1` không có `order_by`, mỗi lần chạy có thể lấy một bảng con khác của app (kết quả vẫn đúng) | thêm `order_by`
- minor | STD-TEST-8 | `erp_ai/agent/test_hard_bans.py` | thứ tự giữa lý do submit và lý do bảng con chưa có test khóa; thiết kế không quy định và không có DocType nào vừa submit vừa là bảng con | thêm một ca khi thiết kế định thứ tự

### Không kiểm được từ diff — tech-lead giải

- Dữ liệu đã lưu (dòng `ERP AI Catalog Rule` trỏ vào bảng con sẽ chặn mọi lần lưu Setting): DocType `ERP AI Catalog Rule` chỉ có trên `team/FEAT-007` (`git ls-tree -r develop | grep -c erp_ai_catalog_rule` = 0, trên nhánh feature = 3), chưa từng lên `develop` hay production; test tạo dòng đều rollback. Không phải khoảng trống; ghi cho As-Built: kiểm bảng này trên site trước khi deploy.
- AR3-3 phải nhắc lại ở bước 2 của bộ thực thi U7a (chưa có mã): thuộc designer/kế hoạch đợt 2; chuyển team-leader.
- `cmd.lint`: `pre-commit run --all-files` trên `team/FEAT-007` @ `aef271c` (sau merge T63 và T66), mọi hook `Passed`.
- Test sau merge (`7af5fa7`, một lần giữ khóa site, `MIGRATE_EXIT=0`): `test_hard_bans` `Ran 9 tests in 0.187s OK`; `test_erp_ai_setting` `Ran 103 tests in 7.073s OK`; `test_architecture` `Ran 181 tests in 16.201s OK`.

## deferred

- Ba minor trên (dev's call); gom cho `/team:clean`.
