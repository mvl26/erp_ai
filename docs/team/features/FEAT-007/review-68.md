Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 68 — FEAT-007 T68

- Diff: `git diff 10781fc879e3dfb7df763711a292eb4bf7b62e4c..bb1eedd` (nhánh `team/FEAT-007-task-68`; 3 commit `ade0e88` test, `eee748e` test (RUF012), `bb1eedd` mã; 2 file +118/−1, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `566ff69` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED, `MIGRATE_EXIT=0`: `FAIL: test_cap_above_or_below_permission_level`, `FAIL: test_main_path_level_matrix`, `FAIL: test_unknown_category_or_bad_cap_reads_l1`, mỗi cái `AssertionError: False is not true : policy has no LEVEL_CAP_FIELD_PREFIX`; `Ran 47 tests in 1.751s FAILED (failures=3)`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_policy `Ran 47 tests in 1.899s OK`, test_architecture `Ran 181 tests in 16.129s OK`.
- Lớp 1: AC-31 và U1 3.1 (chữ ký và hai dòng bảng `category_level_cap`/`main_path_level`) đã làm đủ, không thêm gì ngoài phạm vi, chỉ sửa trong touchpoint.

Theo từng mục checklist (10):

1. Phạm vi/tiêu chí (STD-DESIGN-5, STD-TEST-2): có đủ `LEVEL_CAP_FIELD_PREFIX`, `UNKNOWN_CATEGORY_LEVEL="L1"` và hai hàm. Thân `main_path_level` đúng nguyên văn biểu thức trong design. Ma trận 6×4×2=48 có đếm `cases==48`, giá trị mong đợi viết cứng và khớp bảng mặc định A L2, B L3, C L1, D L2, E L1, F L3. Test thêm `test_cap_above_or_below_permission_level` nằm trong AC-31, không tính là scope creep.
2. Touchpoint/cấu trúc (STD-DESIGN-1, STD-STRUCT-1/2): chỉ sửa `erp_ai/agent/policy.py` và `erp_ai/agent/test_policy.py`, không có file mới.
3. Test trước, cạnh và lỗi, skip (STD-TEST-1/8/4): RED có trong gói review (3 FAIL từ `hasattr` ở `setUp`), commit test đứng trước commit mã, không có skip marker nào trong `test.skip_markers`. Đã thử đột biến trong đầu: bỏ guard `CATEGORIES` thì ca `None` ném lỗi, còn `"a"` đọc ra L3, nên test đỏ. Bỏ kiểm `cap in LEVELS` thì ca `"L4"`/`3` đỏ. Đổi `min` thành `max` thì ma trận đỏ. Cho hàm bỏ qua settings mà trả cứng giá trị mặc định thì ca `level_cap_d=L0/L3` đỏ. Bỏ `.lower()` thì B/F trong ma trận đỏ. Có ca trường thiếu (`_dict()`, `object()`) và ca giá trị rỗng đã lưu.
4. Tính độc lập (STD-TEST-5/6): `keep_agent_settings` cộng rollback. Ma trận tự gán cap mặc định và `permission_level` vào setting rồi mới đọc từ setting đã lưu. Riêng giá trị mặc định thì lấy từ meta, không lấy dữ liệu đang có trên site. Không phụ thuộc giờ hay mạng.
5. Lỗi/biên (STD-ERR-1/2): fail-closed về L1 đúng NFR-4, không có `except`, không gọi dịch vụ ngoài.
6. Bảo mật (STD-SEC-1/3/4/6): không có secret, không có truy vấn, không đụng `protected_paths`.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): chỉ thêm API mới, không đổi hàm cũ, không có migration.
8. Tên/style (STD-NAME-1/2, STD-STYLE-4/5): hằng UPPER_SNAKE, hàm snake_case, thụt tab đúng file. Docstring "the only reader of level_cap_<x>" đúng ở `bb1eedd`: `git grep level_cap` chỉ thấy `policy.py` cùng các file test và mô tả.
9. Phụ thuộc (STD-DEP-1/3/5): không thêm.
10. Commit/nhánh/tài liệu (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2): nhánh `team/FEAT-007-task-68`, cả 3 message đúng mẫu `type(scope): ... (FEAT-007)`, không có trailer AI. Commit `eee748e` chỉ là sửa lint RUF012 cho test. Không có thay đổi người dùng thấy được, nên không cần sửa README.

### Findings

- Không có blocker hay major.
- minor | — | — | 2 điểm nhỏ: (a) các `assertTrue(hasattr(...))` trong `setUp` chỉ để tạo RED, giờ đã thừa; (b) `_caps` viết cứng `"level_cap_"` thay vì dùng `policy.LEVEL_CAP_FIELD_PREFIX` (hằng này đã được pin riêng). Kèm một ghi chú, không tính là finding: bỏ `key=LEVELS.index` vẫn cho cùng kết quả với giá trị hợp lệ, vì L0 < L1 < L2 < L3 cũng đúng theo thứ tự chữ | dev's call

### Không kiểm được từ diff

- Nếu `permission_level` nằm ngoài `LEVELS` thì `LEVELS.index` ném `ValueError`. Design ghi cột lỗi là "—" và chỉ định đúng biểu thức này. Nơi gọi sau này (runner/registry) phải bảo đảm truyền vào giá trị từ `effective_level`, mà giá trị đó là Select đã qua validate.
- Test chưa chạy ở bước review (hai dòng GREEN do dev báo).

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline <range>`, `git diff --stat <range>`, `git diff <range>`, `git log --format='%h %an%n%B---' <range>`, `git diff 10781fc..ade0e88 --stat`, `git diff ade0e88..eee748e`, `git grep -n -E "^(CATEGORIES|LEVELS)\b" bb1eedd -- erp_ai/constants.py`, `git grep -n "level_cap" bb1eedd -- 'erp_ai/*.py' 'erp_ai/*.js'`, `git grep -n -A12 "def set_agent_settings\|def keep_agent_settings" bb1eedd -- erp_ai`.

## Kết luận của tech-lead

- Mục "không kiểm được" 1 (`ValueError` khi mức ngoài `LEVELS`): ở T68 chưa có nơi gọi nào ngoài test; nơi gọi đầu tiên là T80 (runner dựng context). Không phải chỗ hở của T68 (design chỉ định đúng biểu thức). Chuyển thành việc phải kiểm ở lời giao reviewer của T80: `main_path_level` chỉ nhận giá trị trả về của `policy.effective_level`.
- Mục "không kiểm được" 2: tech-lead đã chạy sau merge, worktree `feat-007` @ `566ff69`, một lần giữ khóa site, `MIGRATE_EXIT=0`: `erp_ai.agent.test_policy` `Ran 47 tests in 1.703s` / `OK`; `erp_ai.tests.test_architecture` `Ran 181 tests in 15.654s` / `OK`. Lưu ý: `bench run-tests` trả mã thoát 0 cả khi test đỏ, nên chỉ đọc dòng `Ran … OK/FAILED`.
- Tick T68: 61/174.

## deferred

- minor (a), (b) ở trên: dọn khi T69 hoặc task kế của `test_policy.py` chạm vùng đó; không mở vòng sửa.
- Lời giao reviewer của T80 thêm phép kiểm nguồn giá trị `permission_level` truyền vào `main_path_level`.
