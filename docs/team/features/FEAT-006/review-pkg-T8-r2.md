# Review package FEAT-006 T8, vòng 2 (scoped re-review)

BASE=2851bca; head=team/FEAT-006-task-8 (57fd5ca, một commit squash thay 69aa409).
Chỉ xét fix: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 69aa409..57fd5ca` (toàn bộ là `git diff 2851bca..57fd5ca`, 2 file; `git status` đã sạch).

Findings vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-8 | test_routing.py:178-181,215-227 | mọi tiền tố config đều viết thường; cần `[TraceCore]` với tiêu đề `[tracecore] x` (dev: `test_config_prefix_casefolded`).
2. major | STD-TEST-8 | test_routing.py:229-267 | (a) D-13 "tiền tố khớp đầu tiên CÓ NGƯỜI" (`{"[x]": "", "[y]": "y@x.com"}`, tiêu đề `[x] [y]` → `y@x.com`); (b) ứng viên đã chọn không hợp lệ thì không lùi sang `default` (is_active_agent=False cho trace → `None` + đúng 1 note).
3. major (suspected) | STD-ERR-2 | routing.py:91 | `candidate == AGENT_USER` so sánh chính xác; sửa: `strip().casefold()`, test biến thể HOA/khoảng trắng/Title.
Minor dev đã làm: bỏ qua khóa tiền tố rỗng `""` (design 3.2/3.3 không nói; kiểm có đúng ý spec không); `# noqa: E731` thay bằng `def`.
Dev báo đã phá mã tạm cho từng test mới để chứng minh đỏ (rồi hoàn tác).
Ngoài phạm vi → `deferred`.
