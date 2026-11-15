Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 173 — FEAT-007 T173

- Diff: `git diff ce696e161d9d9a208ae2e4d46d6c4598b819d61c..41426cd` (nhánh `team/FEAT-007-task-173`; 3 commit `f8d5705` test, `8c56e52` mã, `41426cd` xuống dòng docstring; 2 file +39/−5, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `10781fc` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED @ `f8d5705` (chỉ test), `MIGRATE_EXIT=0`: `FAIL: test_refused_reason_secret_masked (erp_ai.agent.test_run_log.TestActionEntry.test_refused_reason_secret_masked)`, `AssertionError: 'ERPAI-TEST lỗi: password=ERPAI-TEST-p9 và Bearer ERPAITESTbearer12345' != 'ERPAI-TEST lỗi: password=[đã che] và Bearer [đã che]'`, `Ran 22 tests in 2.620s FAILED (failures=1)`; `test_two_mask_words_have_distinct_meanings` xanh ngay trong cùng lần chạy (dòng task ghi đây là test ghim). GREEN @ `41426cd`, `MIGRATE_EXIT=0`: test_run_log `Ran 22 tests in 2.897s OK`, test_architecture `Ran 181 tests in 15.613s OK`.
- Nhận xét của tech-lead về RED: đỏ vì `reason` còn chuỗi gốc (thiếu hành vi), báo bằng assertion.
- Sáu điểm tech-lead yêu cầu phán, reviewer đều cho đạt:
  1. Diff mã chỉ có `run_log.py:90` (`redact.redact_secrets(reason) if _is_name(reason) else NO_REASON`) và docstring `:63-67`; `_mask`, `_password_fields`, `rule` (`:91-92`), hằng số, chữ ký không đổi.
  2. Test khớp Expect từng chữ: ca chính `test_run_log.py:475-490` (`:480` bằng `redact_secrets(reason)`, `:481` có `MASK`, `:482-483` không có `ERPAI-TEST-p9`, `ERPAITESTbearer12345`; `:484-488` subtest `sk-ant` với chữ mong đợi viết cứng; `:489-490` subtest `rule`); test ghim `:492-506` (`SECRET_MASK == "[đã ẩn]" == SCRUBBED_VALUE`, `MASK == "[đã che]"`, hai chữ khác nhau, ví dụ `value_after`).
  3. Biên (STD-TEST-8), mỗi cái đã có test ghim: `reason` rỗng, `None`, toàn khoảng trắng → `NO_REASON` (`test_refused_entry_keeps_reason:467-473`); `ok=True` không có khóa `reason` dù có truyền (`test_shape_has_all_keys_in_order:410,417`); `reason` không có bí mật giữ nguyên (`test_refused_entry_keeps_reason:448,463`).
  4. Không khẳng định cũ nào bị nới; bốn test `TestActionEntry` cũ giống từng byte. Import `SCRUBBED_VALUE` từ `site_api` không thêm cạnh lớp mới (file test đã import `SECRET_FIELDS` từ đó, `run_log.py:7` import cùng module).
  5. STD-SEC-6, STD-SEC-1: `reason` không phải `str` không qua `_is_name` (`run_log.py:21-22`) nên thành `NO_REASON`; mọi `str` khác rỗng đi qua `redact_secrets`; không nhánh nào ghi `reason` gốc. Bí mật mà không mẫu nào của `redact` khớp là giới hạn của T35/T120, không của task này. Chuỗi test rõ ràng là giả.
  6. Nhánh và ba dòng tiêu đề commit đúng dạng; không dòng ghi công AI; không skip. Commit thứ ba chỉ xuống dòng docstring của `8c56e52`, nhận được theo STD-GIT-2.
- Checklist (10): 10/10 đạt.

### Findings

Không có blocker, không có major.

- minor | — | — | 2 điểm nhỏ: (a) subtest `rule` (`test_run_log.py:489-490`) dùng giá trị không có bí mật nên vẫn xanh nếu `rule` cũng bị đưa qua `redact_secrets`; (b) không test nào truyền `reason` không phải `str` (ví dụ `123`) để ghim thứ tự "kiểm rỗng trước, che sau" | dev's call

### Không kiểm được từ diff — tech-lead giải

- T91, T92, T110 phải chỉ đưa chữ của tool hay ngoại lệ vào `reason`, không vào `rule` (`rule` không che, theo thiết kế): không thuộc diff này; tech-lead ghi vào progress của T173 để đưa vào lời giao reviewer của ba task đó.
- Reviewer không chạy test. Tech-lead chạy sau merge trên `team/FEAT-007` @ `10781fc`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_run_log `Ran 22 tests in 2.528s OK`, test_architecture `Ran 181 tests in 15.827s OK`; `pre-commit run --all-files`: mọi hook `Passed`.

## deferred

- Không có.
