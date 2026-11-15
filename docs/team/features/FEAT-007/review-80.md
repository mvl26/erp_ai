Feature: FEAT-007
Stage: build
Author-agent: tech-lead
Date: 2026-11-15

# Review T80 — Runner dựng context từ `policy` và `run_instructor`

## Vòng 1 (2026-11-15, lượt build 18) — `request-changes`

- Lệnh diff (reviewer tự chạy): `git diff --stat ed341b9..cdf5b85`, `git diff ed341b9..cdf5b85 -- <từng file>`, `git log --format='%h %an%n%B---' ed341b9..cdf5b85`, `git show c00340e`, `git grep -n latest_instructor cdf5b85 -- '*.py'`.
- Bốn commit: `a487dbb` test, `c00340e` test, `22bf3ad` test, `cdf5b85` feat. 6 file, đều trong touchpoints. Reviewer dùng 13/22 lượt, không chạy test.
- Tầng 1 đạt: bước (e) và context đúng `U1.md:259-260`; lần chạy tạo phiếu `category=None, below_threshold=False`; `_reason` không đổi; không kéo việc của T81, T82.

Finding (nguyên văn):

- major | STD-TEST-6 | erp_ai/agent/test_agent_runner.py:3116 | `_run_classified` writes a classify row with `predicted_category="A"`. "A" is in `CATEGORIES`, so `main_path_level` (runner.py:204) reads the live site's `level_cap_a`, which no test sets. The class comment at :3053 says no setting the grant uses comes from the shared site, and :82 avoids exactly this for the base. If the live cap is L0, the 69 test passes for the wrong reason (refused by the cap, not the threshold) and the 70 test turns red. | Write `predicted_category=SEEDED_CLASSIFICATION[0]` in the row, or set `level_cap_a="L3"` in `_run_classified` | confirmed (code path read; not run)
- minor | — | — | 3 small points: (a) no runner test checks that the classify row's category feeds `main_path_level`; replacing it with `None` stays green. (b) The new architecture rule only catches a fetch plus instruction check inside one function, so two helpers that split the scan would slip through; its docstring says so. (c) `c00340e` has a subject but no body. | dev's call

Review checklist (10): 1 ok · 2 ok · 3 ok · 4 major (STD-TEST-6) · 5 ok · 6 ok (quyền vẫn kiểm phía server ở `execute_tool`) · 7 ok · 8 ok · 9 n/a · 10 ok.

Đã kiểm theo danh sách: chỉ sáu file touchpoint; `run_instructor` được dùng, `latest_classification` chỉ gọi ở lần chạy không tạo phiếu; `authority.py` chỉ bỏ `latest_instructor`; bốn test `TestRunnerGrant` có đủ, test dưới ngưỡng chỉ khẳng định kết quả (phán quyết `design-w1-fixes-17.md` Điểm 1); 24 dòng `patch.object` đổi tên, giữ `return_value`; `c00340e` chỉ đổi helper mới `_comment`; `test_authority.py`, `test_result_comment.py` đúng các dòng của Returns; luật kiến trúc mới chỉ thêm; RED đúng lý do, commit test đứng trước commit mã; không commit nào có dòng ghi công AI.

Không kiểm được từ diff:

- Giá trị thật của `level_cap_a` trên site `miyano` (quyết định finding major có lộ ra hôm nay hay không).
- `only_python(sources)` có loại file test hay không (lần chạy xanh gợi ý là có, reviewer chưa đọc).

Bằng chứng của dev ở vòng này (nguyên văn dòng kết quả): RED trên `c00340e`: test_agent_runner `Ran 114 tests in 55.226s` / `FAILED (failures=48, errors=1)`; test_architecture `Ran 187 tests in 28.235s` / `FAILED (failures=1)`; F-3 `AttributeError: module 'erp_ai.agent.authority' has no attribute 'latest_instructor'`, `Ran 6 tests in 5.579s` / `FAILED (errors=1)`. GREEN trên `cdf5b85`, `MIGRATE_EXIT=0`: test_agent_runner `Ran 114 tests in 55.104s` OK; test_authority `Ran 27 tests in 44.277s` OK; changes.test_result_comment `Ran 6 tests in 5.435s` OK; test_runner_status `Ran 39 tests in 15.420s` OK; test_runner_routing `Ran 62 tests in 69.319s` OK; test_architecture `Ran 187 tests in 28.396s` OK; `pre-commit run --all-files` 12 hook Passed, `LINT_EXIT=0`.

Xử lý: vòng sửa 1/3, finding major chuyển nguyên văn cho dev (FIX_BASE=`cdf5b85`).

## Vòng 2 (2026-11-15, lượt build 19) — soát hẹp trên diff sửa — `approve`

- Lệnh diff (reviewer tự chạy): `git log --format='%h %s%n%b' cdf5b85..978463b`, `git diff --stat cdf5b85..978463b`, `git diff cdf5b85..978463b`; đọc thêm `git show 978463b:erp_ai/agent/test_agent_runner.py` (:81-82, :3048-3060, :3108-3130), `git show 978463b:erp_ai/agent/policy.py` (:104-121, :157-168), `git grep -n "category_level_cap\|main_path_level(" 978463b`. Một commit `978463b` (test), 1 file +2/−1. Reviewer dùng 6 lần gọi tool, không chạy test. Lần gọi soát hẹp đầu tiên (round 114, lượt 18) bị cắt bởi lần khởi động lại máy, không có kết quả; đây là lần gọi lại ở round 115.
- major STD-TEST-6 `test_agent_runner.py:3116`: ADDRESSED. `:3117` ghi `predicted_category=SEEDED_CLASSIFICATION[0]` (`f"{PREFIX}category"`, ngoài `CATEGORIES`), nên `category_level_cap` (`policy.py:113-114`) trả `UNKNOWN_CATEGORY_LEVEL` trước khi đọc `level_cap_<x>` của site; `main_path_level` chỉ có một nơi gọi (`runner.py:204`). Dòng `classify` vẫn khớp bộ lọc của `latest_classification`, ngưỡng 69 và 70 vẫn lấy từ dòng đó.
- Reviewer tự sửa finding vòng 1: câu "test 70 sẽ đỏ nếu cap thật là L0" sai với phần cấp của T80 (lần chạy của dev với dòng tạm `level_cap_a="L0"`, chưa sửa: `Ran 114 tests in 59.548s OK`); finding chỉ còn đúng ở nghĩa "đọc cấu hình của site thật", và chỗ sửa đã bỏ lần đọc đó.
- minor (a) (không test nào ghim rằng đầu mục của dòng `classify` đi vào `main_path_level`): NOT ADDRESSED, quyền của dev; minor (b) (luật kiến trúc lọt khi tách hai helper): NOT ADDRESSED, ngoài diff sửa; minor (c) (`c00340e` không có thân): NOT ADDRESSED, không viết lại lịch sử.
- Finding mới trong diff sửa: không có. Review checklist (10) trên diff sửa: 1 ok · 2 ok · 3 ok · 4 ok · 5 n/a · 6 ok · 7 n/a · 8 ok · 9 n/a · 10 ok.

Bằng chứng trên `978463b` (dev chạy lại ở round 115 theo quyết định 17:50 (b), không sửa gì, cây sạch trước và sau; một lần giữ khóa site, mã lấy từ worktree của dev, `MIGRATE_EXIT=0`): test_agent_runner `Ran 114 tests in 28.106s` / `OK`; test_authority `Ran 27 tests in 20.882s` / `OK`; changes.test_result_comment `Ran 6 tests in 2.685s` / `OK`; test_runner_status `Ran 39 tests in 7.532s` / `OK`; test_runner_routing `Ran 62 tests in 30.393s` / `OK`; test_architecture `Ran 187 tests in 16.561s` / `OK`; `pre-commit run --all-files` 12 hook Passed, `LINT_EXIT=0`; `git grep -n latest_instructor -- '*.py'` chỉ ra `erp_ai/tests/test_architecture.py`.

deferred (không chặn): minor (a) — một test đặt `level_cap_<x>` và gieo dòng `classify` có đầu mục thuộc `CATEGORIES` để ghim đường vào `runner.py:204`; reviewer đề nghị đưa vào T81 hoặc T82.

Số vòng: 2 (vòng sửa 1/3). Verdict cuối: `approve`.
