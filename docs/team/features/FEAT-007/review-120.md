Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 120 — FEAT-007 T120

- Diff: `git diff 43ae572..05a4b50` (nhánh `team/FEAT-007-task-120`; 3 commit `d9d8cd0`, `9e9c1bd`, `05a4b50`; 3 file +72/−6)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve ở vòng 2; merge `ce696e1` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — request-changes

- Diff vòng: `git diff 43ae572..d9d8cd0` (3 file, +52/−5).
- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `test_redact` `Ran 22 tests in 0.308s FAILED (failures=5)`, cả 5 là subtest của `test_list_separator_inside_bare_value_masked`, ví dụ `AssertionError: 'password=[đã che]&cd' != 'password=[đã che]'`; `test_list_separator_before_next_key_ends_value` xanh từ trước. RED `test_knowledge` `Ran 37 tests in 1.095s FAILED (failures=1)`: `AssertionError: 'tailFAKE' unexpectedly found in '... mật khẩu: [đã che]&amp;tailFAKE '`. GREEN: `test_redact` `Ran 22 tests in 0.284s OK`; `test_knowledge` `Ran 37 tests in 1.058s OK`; `test_architecture` `Ran 181 tests in 15.338s OK`.
- Nhận xét của tech-lead về RED: đỏ vì phần sau dấu phân cách còn lộ (thiếu hành vi).
- Tier 1: mã đáp ứng đủ Returns. Nhánh trần đi qua `, ; &` trừ khi ngay sau là hết văn bản, khoảng trắng, hoặc đầu một ứng viên khóa; phép nhìn trước dạng `(?=(?P<x>…))(?P=x)`; chữ ký giữ nguyên; `_KEY_CANDIDATE` sau khi tách thành `_KEY_NAME_RUNS`, `_KEY_NAME_END` giống hệt bản cũ (reviewer so từng ký tự); `knowledge.py` không sửa.
- Checklist (10): 1 đạt · 2 đạt · 3 không đạt ở ca biên (major dưới) · 4 đạt · 5 đạt (reviewer tính thời gian quét tuyến tính: hai nhánh của vòng lặp loại trừ nhau theo ký tự đầu, không quay lui) · 6 đạt · 7 đạt · 8 đạt · 9 không áp dụng · 10 đạt.

### Findings

- major | STD-TEST-8 | `erp_ai/agent/test_redact.py:276-287` | Vế (c) của K-4 nói ứng viên khóa có 1–3 cụm, nháy tùy chọn, `\s*`, rồi `:` hoặc `=`; mọi ca kết thúc giá trị chỉ dùng khóa 1 cụm với `=`. Hai bản đột biến lọt qua cả 10 ca: nhìn trước chỉ 1 cụm (lộ bí mật: `pwd=ab;api key: FAKE`); chỉ nhận `=` (che lố: `pwd=ab;user:bob`) | thêm các ca `pwd=ab;api key: fake-z`, `pwd=ab;user:bob`, `pwd=ab;user :x`, `token=abc&page"=2`, cộng một khóa 3 cụm
- minor | STD-DOC-2 | `erp_ai/agent/redact.py:3` | (a) docstring còn dẫn K-1..K-8 về `design-w0-fixes-3.md` | trỏ K-4, K-4a, K-8 về `design-w0-fixes-4.md`
- minor | STD-TEST-8 | `erp_ai/agent/test_redact.py` | (b) dấu phân cách đứng trước `"` `}` `]` bị tính vào giá trị (đúng thiết kế), chưa có test riêng | thêm test

## Vòng 2 — approve (scoped re-review)

- Diff vòng: `git diff d9d8cd0..05a4b50` (2 commit, 2 file, +20/−1; `redact.py` chỉ đổi docstring +2/−1).
- Bằng chứng của dev: 6 ca mới xanh ngay trên mã `d9d8cd0`. Bản đột biến 1 (nhìn trước một cụm, sửa tạm trong worktree, không commit): `FAILED (failures=3)`: `AssertionError: 'pwd=[đã che] key: fake-z' != 'pwd=[đã che];api key: [đã che]'`, cộng hai ca khóa ba cụm. Bản đột biến 2 (chỉ `=`): `FAILED (failures=4)`: `AssertionError: 'pwd=[đã che]' != 'pwd=[đã che];user:bob'`, `'pwd=[đã che] :x' != 'pwd=[đã che];user :x'`, cộng ca `api key:` và ca khóa ba cụm. GREEN sau khi khôi phục regex: `test_redact` `Ran 23 tests in 0.305s OK`; `test_knowledge` `Ran 37 tests in 1.065s OK`; `test_architecture` `Ran 181 tests in 15.828s OK`.
- Nhận xét của tech-lead: các ca biên của vế (c) theo thiết kế phải xanh trước và sau (`design-w0-fixes-4.md:45`), nên bằng chứng đỏ là hai lần chạy đột biến.
- Finding vòng 1: major → ADDRESSED (`test_redact.py:284-290`, 6 ca, giá trị mong đợi viết cứng; reviewer dò từng ca theo `_KEY_VALUE`/`_KEY_NAME_RUNS` và K-4 (c)) · minor (a) → ADDRESSED (`redact.py:3-4`) · minor (b) → ADDRESSED (`test_redact.py:295-305`, `test_list_separator_before_closing_mark_stays_in_value`).

### Findings mới

Không có blocker, không có major.

- minor | STD-TEST-8 | `erp_ai/agent/test_redact.py` | chưa có ca khóa trần 3 cụm của phép nhìn trước (ví dụ `pwd=ab&a b c d=x` → `pwd=[đã che] b c d=x`); phép nhìn trước dùng chung hằng `_KEY_NAME_RUNS` với `_KEY_CANDIDATE` nên rủi ro thấp | thêm một ca

### Không kiểm được từ diff — tech-lead giải

- Đầu ra GREEN chỉ có trong lời dev: tech-lead chạy lại sau merge `ce696e1`, giữ khóa site, `MIGRATE_EXIT=0`, 0 `QueryDeadlockError`: `test_redact` `Ran 23 tests in 0.296s OK`; `test_knowledge` `Ran 37 tests in 1.108s OK`; `test_run_log` `Ran 20 tests in 2.593s OK`; `test_system_read` `Ran 8 tests in 0.248s OK` (ba file test có dùng `redact`); `test_architecture` `Ran 181 tests in 15.844s OK`. `cmd.lint`: `pre-commit run --all-files`, mọi hook `Passed`.
- Chỗ hở giữa K-4 mới và K-7 cũ (vòng 1): giá trị trần bắt đầu bằng một đoạn khớp `SECRET_PATTERNS` thì K-7 giữ MASK rồi quét tiếp sau MASK; ví dụ `password=sk-ant-FAKE&tailFAKE` cho `password=[đã che]&tailFAKE`, `&tailFAKE` lộ (NFR-6). Reviewer suy ra từ `redact.py:83-86` và `design-w0-fixes-3.md:167`, chưa chạy thử; lỗi ở thiết kế, khả năng gặp thấp, không chặn T120. Chuyển team-leader → designer: thêm ca này vào K-4a, hoặc sửa K-7 để quét tiếp như phần đuôi của giá trị trần.
- Quét khóa có thể bậc hai trên văn bản dài (`_KEY_VALUE.match` chạy trước `is_secret_key`; nhánh nháy thiếu nháy đóng đọc tới hết văn bản): có từ T35, ngoài diff.

## deferred

- Minor vòng 2 (dev's call).
- K-4/K-7: chờ designer. Quét bậc hai: ghi nợ cho `/team:clean` hoặc task riêng.
