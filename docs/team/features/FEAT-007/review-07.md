Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 07 — FEAT-007 T7

- Diff: `git diff 5e265563c4f76864dd650e626870a771ef32e9d6..5af1f80` (đầu nhánh task khi merge; merge `dbf0dea` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `5e26556..5af1f80` (1 commit, 4 file, +159/−3), đúng 4 file của touchpoints.
- Bằng chứng của dev: RED 1 `FAIL: test_level_caps_default ... AssertionError: 'section_autonomy' not found in [...]`, lỗi `Field level_cap_a does not exist`, `FAILED (failures=1, errors=9)`; RED 2 (trước hai dòng `INT_LIMITS`) `FAIL: test_int_limits_edges (fieldname='confidence_threshold', value=-1) AssertionError: ValidationError not raised`, `FAILED (failures=4)`; GREEN `test_erp_ai_setting` `Ran 36 tests ... OK`, `test_doctype_descriptions` `Ran 12 tests ... OK`, `test_install` `Ran 36 tests ... OK`, `test_architecture` `Ran 112 tests ... OK`.
- Kết luận của reviewer: AC-31 (`level_cap_a`..`level_cap_f` là Select `L0\nL1\nL2\nL3`, mặc định L2, L3, L1, L2, L1, L3, khớp `design.md:121`); AC-22 (`confidence_threshold` Int, mặc định 70, 0..100); AC-36 (`auto_approve_streak` Int, mặc định 20, 1..100); chữ lỗi theo dạng sẵn có; `section_autonomy` đứng sau `site_environment`, trước `section_limits`, đúng chỗ theo bảng `design.md:95-110`; 8 mô tả khớp `design.md:165-167` từng chữ; `field_count` 31 → 39, `section_count` 8 → 9; 8 dòng mới trong `FEAT007_NEW_FIELD_DEFAULTS`; `TestFeat007Limits` gọi `keep_agent_settings`; controller không thêm tên công tắc quyền. Nhãn 8 trường do dev đặt (thiết kế không cho), theo mẫu sẵn có.
- `test_int_limits_edges` dùng bảng chữ lỗi viết thẳng (`FEAT007_INT_LIMITS`), tách khỏi `INT_LIMITS` mà nó kiểm; đỏ khi bỏ một dòng, khi dời biên, khi đổi nhãn.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 3 điểm nhỏ: (1) `test_erp_ai_setting.py:604-611` `LEVEL_CAP_DEFAULTS` lặp 6 dòng của `FEAT007_NEW_FIELD_DEFAULTS`, và `test_level_caps_default:666` kiểm lại mặc định cài đặt mà `test_every_new_field_default` đã kiểm (STD-DESIGN-4); (2) `:700-702` ở biên thấp `confidence_threshold=0`, đọc lại giá trị không phân biệt được 0 đã lưu với dòng Int thiếu, phép kiểm thật là không có ValidationError (STD-TEST-8); (3) không test nào cho giá trị cap ngoài option (ví dụ "L4"), Frappe tự chặn và chuỗi option đã được ghim | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (RED 1, RED 2 được dán; biên hai phía; không skip) 4. đạt (rollback + `keep_agent_settings`, không dùng đồng hồ) 5. đạt (kiểm ở lúc lưu qua `INT_LIMITS`) 6. đạt 7. đạt (chỉ thêm trường; `after_migrate` → `ensure_setup` → `_ensure_default_settings` điền mặc định trên site đã có) 8. đạt 9. không áp dụng 10. đạt (`feat(setting): … (FEAT-007)`, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `test_doctype_descriptions` không có lần chạy đỏ riêng (dev tự báo) | Phần sửa của file đó chỉ là cấu hình (`field_count`, `section_count`, cụm bắt buộc); RED 1 của `test_erp_ai_setting` đã cho thấy trường chưa có. Số đếm 39 / 9 được chính test đó kiểm với JSON sau merge (xanh). Không chặn tick. |
| Test sau merge | Tech-lead chạy từ worktree `feat-007` sau merge `dbf0dea`: `cmd.migrate` exit 0; `test_erp_ai_setting` `Ran 36 tests in 1.343s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.342s OK`; `test_install` `Ran 36 tests in 15.243s OK`; `test_architecture` `Ran 112 tests in 3.092s OK`. `cmd.lint` (chạy sau merge T61): chỉ nợ nền `erp_ai/test_change_decision.py`. |
| Chiều xuống: bỏ 8 trường Single để lại dòng `tabSingles` | Thuộc T23 (dòng thừa vô hại) và đối soát ở verify. |

## deferred

- (minor, tùy dev) 3 điểm nhỏ ở trên.
