Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 84 — FEAT-007 T84

- Diff: `git diff 43ae572..589cf2f` (nhánh `team/FEAT-007-task-84`; 1 commit, 2 file +239/−1)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `2aed7d6` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `test_run_log` `AttributeError: module 'erp_ai.agent.run_log' has no attribute 'ACTION_KEYS'` (tương tự `NO_REASON`, `SECRET_MASK`, `action_entry`) ở cả 4 test của `TestActionEntry`, `Ran 20 tests in 2.595s` / `FAILED (errors=14)`; GREEN `Ran 20 tests in 2.705s` / `OK`; `test_architecture` `Ran 181 tests in 15.793s` / `OK`.
- Nhận xét của tech-lead về RED: đỏ vì hằng và hàm chưa có (thiếu hành vi); file test nạp được, các test cũ trong file vẫn chạy.
- Tier 1 (đối chiếu spec): đạt. Đủ `ACTION_KEYS` đúng thứ tự; `reason` chỉ có khi `ok` là False, rỗng thành `NO_REASON`; `rule` chỉ có khi khác rỗng; `doctype` cắt ở 80; `_mask` đệ quy, không sửa dict đầu vào; đầu vào sai báo `ValueError`; hợp nhất `SECRET_FIELDS` có trong Receives. Bốn hằng và chữ ký khớp Returns và `plan-w1.md:53`. `run_log` import `tools.site_api` không tạo vòng.
- Checklist (10): 1 đạt · 2 đạt · 3 đạt (ca biên: `reason` None/`""`/`"   "`, `rule=""`, doctype 81 ký tự, DocType không tồn tại, list lồng trong dict, lá số; mỗi test đỏ nếu bỏ hành vi tương ứng) · 4 đạt · 5 đạt · 6 đạt so với thiết kế (khóa bí mật ở mọi cấp lồng, `SECRET_FIELDS`, trường Password của `doctype` → `SECRET_MASK = "[đã ẩn]"`, cùng chữ với `site_api.SCRUBBED_VALUE` của T61, đúng `U3.md:130`; chuỗi lá qua `redact.redact_secrets` → `"[đã che]"`; `tool`, `doctype`, `name`, `instructor`, `rule` là định danh; `reason` không che vì thiết kế chỉ đòi cho `value_*`) · 7 đạt · 8 đạt · 9 đạt · 10 đạt (1 commit `feat(run_log): … (FEAT-007)`).

### Findings

Không có blocker, không có major.

- minor | STD-TEST-6 | `erp_ai/agent/test_run_log.py` (`TestActionEntry`) | không gọi `keep_agent_settings(self)` như "Quy ước cho mọi task" (`tasks.md:17`); hàm không đọc Setting nên không có rủi ro thật | thêm lời gọi
- minor | STD-ERR-2 | `erp_ai/agent/run_log.py:89` | `doctype=""` cho ra `None`; `doctype` không phải chuỗi thì báo `TypeError` không ghi trong docstring | ghi vào docstring hoặc đổi thành `ValueError`
- minor | STD-STYLE-4 | `erp_ai/agent/run_log.py:93` | `if rule:` giữ `rule="   "` trong khi `reason` dùng `_is_name` | dùng cùng một phép kiểm
- minor | STD-TEST-8 | `erp_ai/agent/test_run_log.py:513` | giá trị mong đợi của `note` tính bằng chính `redact.redact_secrets` (đã có `assertNotIn` đỡ) | viết cứng chuỗi mong đợi

### Không kiểm được từ diff — tech-lead giải

- Hai chữ mặt nạ trong một mục (`U3.md:98` viết `"[đã ẩn]"` cho giá trị bí mật của `value_*`; `U3.md:145` bắt chuỗi lá qua `redact.redact_secrets`, hàm này che bằng `"[đã che]"`, ví dụ `{"api_key": "[đã ẩn]", "note": "Bearer [đã che]"}`): mã làm đúng cả hai dòng thiết kế và đúng Returns của task, nên không phải khoảng trống của T84. Chuyển team-leader → designer: chọn một chữ cho `U3.md:98` hoặc ghi rõ cố ý dùng hai chữ (cách sửa có thể: `redact` nhận tham số mặt nạ, hoặc `SECRET_MASK = redact.MASK`). Nên phán trước T91 (nơi đầu tiên gọi `action_entry`).
- `reason` không che: nếu T91 hoặc T110 truyền `str(exception)` hay văn bản tool trả về vào `reason`, bí mật trong đó vào log (STD-SEC-6). Ghi vào lời giao reviewer của T91, T92, T110; hoặc designer thêm `redact_secrets` cho `reason`.
- Password của bảng con: `_password_fields` chỉ đọc meta của `doctype` cha; hàng bảng con có trường Password mà tên không có từ bí mật sẽ không bị che. Giới hạn của thiết kế (`U3.md:145`); xem lại khi T91 định dạng `value_*` cho tool bản ghi chung. Chuyển team-leader.
- Test sau merge (`2aed7d6`, một lần giữ khóa site, `MIGRATE_EXIT=0`): `test_run_log` `Ran 20 tests in 2.645s OK`; `test_architecture` `Ran 181 tests in 15.478s OK`. `cmd.lint`: `pre-commit run --all-files`, mọi hook `Passed`.

## deferred

- Bốn minor trên (dev's call); T85, T86, T93 cùng file có thể gom.
- Ba điểm thiết kế ở mục trên: chờ designer.
