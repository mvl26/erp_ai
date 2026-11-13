# Review 08 — T7b (git_source chỉ còn log và blame, D4)

- Verdict: approve (vòng 2)
- Số vòng: 2 (vòng 1 request-changes, vòng 2 approve)
- Diff: `git diff 9010e38..team/FEAT-001-task-7b` (vòng 2: `git diff 2b523ac..team/FEAT-001-task-7b`); merge a97adc1
- Checklist (10): 10/10 sau vòng 2

## Findings
- Vòng 1: major | STD-TEST-2 | test_source.py:300-307 | test từ chối `show`/`diff` vẫn xanh khi bỏ bảo vệ vì mọi đối số đều bị checker blame từ chối; dispatch `else` rơi về checker blame. Sửa: thêm ca `["src/a.py"]`, `["--", "src/a.py"]`; thay `else` bằng map tường minh. Vòng 2: ADDRESSED (dev đã chứng minh đỏ khi thêm lại `show`).

## Đã giải quyết "không kiểm được từ diff"
- Red/green: dev dán đỏ (6 test thất bại, đúng hành vi) rồi xanh; sau merge `--app erp_ai` Ran 80 tests OK, pre-commit exit 0.
- Không nơi nào khác gọi `git_source` hay đưa `show`/`diff` cho agent (git grep).

## Deferred
- minor: `full is not None` trong `_git_blame_args_ok` không bao giờ sai; log `--porcelain` bị từ chối chưa có test riêng; map `GIT_ARGS_CHECKERS` chưa có test riêng.
- Cho người/designer: design.md 3.5 (dòng ~331) và 5.4 (dòng ~510) còn ghi enum log/show/diff/blame; cần cập nhật theo D4 trước T27 (schema tool dựng từ design).
