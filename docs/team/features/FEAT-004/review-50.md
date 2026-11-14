Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 50 — FEAT-004 T50

- Diff: `git diff 4087f83..09c1481` (1 commit, 1 file `erp_ai/agent/tools/test_propose_change.py`, +177; chỉ thêm test). Mã sản phẩm của T50 (`_code_values`, `_comment` dùng `change_text.proposal_notes`) do phiên khác viết ngoài quy trình; reviewer chấm mã ở đầu nhánh task
- Vòng: 1 (max_rework=3)
- Verdict: approve (đường dẫn ký sẵn trong `_comment` thuộc Amendment 2 / CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — approve
Lớp 1: AC-16, AC-21, NFR-8, D-14 đạt ở đầu nhánh. `_code_values` (`propose_change.py:139-157`) lấy 4 trường git chỉ từ `guard.git` / `guard.is_core_app`; handler lệnh bench (`:212-217`) lưu `""`/0 theo design 2.1; tool không truyền `commit_message`; `_comment` escape mọi giá trị, mỗi dòng `proposal_notes` một `<p>` (design 3.8).
- Phép kiểm rò rỉ chứng minh kho không rỗng trước (`test_propose_change.py:625` kho remote của git có URL chứa token; `:644` đề xuất đã lưu có tên upstream) rồi mới đếm 0 lần (`:645-652`)
- Câu trong comment (`CORE_WARNING`, `NO_UPSTREAM_NOTE`, `RESTART_NOTE`, câu nhánh, câu upstream) trùng từng chữ design 3.9; `assert_in_order` dùng `str.index` nên thiếu câu là đỏ
- Trường git không đến được từ model: schema từ chối mọi khóa giả cho cả 3 tool (`:699-704`); gọi thẳng handler thì giá trị của bộ chặn thắng (`:716`); `commit_message` so với mẫu 3.9 viết tay (`:717-722`); lệnh `build frappe`: 4 trường git và `commit_message` là `""`/0 (`:729-731`)

Không có blocker, major.

minor | — | — | 4 điểm nhỏ: `test_bench_app_checked_by_check_bench_args_at_proposal_time` (`:736`) thuộc phần còn lại của T27, ghi công cho T27; bằng chứng đỏ chỉ phủ bộ trường và test bench, các câu comment chưa có dòng đỏ (đọc mã thì đỏ được); phép kiểm rò ở `:733-734` và kho "kết quả" ở `:648` chưa chứng minh không rỗng trước; design 3.9 mục 2 không giới hạn cho thay đổi code trong khi mã chỉ hiện cho code (`change_text.py:86`) | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Mã đã đúng sẵn; dòng đỏ lấy từ thay đổi tạm rồi bỏ: `('feature/core', '', 0, 0) != ('feature/core', '', 0, 1)`; `('feature/core', '', 0, 0) != ('feature/core', 'origin/feature/core', 3, 1)`; `('main', '', 0, 0) != ('main', 'origin/main', 1, 0)`; `('forged-branch', 'https://x-token-FAKE@host/r.git', 99, 1) != ('feature/real', '', 0, 0)`; `{'ok': True, …} != {'ok': False, 'reason': 'đối số chứa ký tự điều khiển shell'}`; `{'ok': True, …} != {'ok': False, 'reason': 'lệnh build cần app'}`
- GREEN: `Ran 24 tests in 23.904s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `source.read_git_state` có bao giờ trả URL trong `upstream_ref` không: T39 đã ghim (`test_branch_remote_set_to_url_never_leaks_it`, review-39 approve).
- Controller không đặt `commit_message` cho lệnh bench: test `:731` kiểm qua đề xuất thật, xanh.

## deferred
- Cho designer: design 3.9 mục 2 ghi rõ chỉ áp cho thay đổi code.
