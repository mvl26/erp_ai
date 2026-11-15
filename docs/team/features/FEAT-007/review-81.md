Feature: FEAT-007
Stage: build
Author-agent: tech-lead
Date: 2026-11-15

# Review T81 — Lần tạo phiếu: context sau phân loại, dưới ngưỡng không định tuyến

## Vòng 1 (2026-11-15, lượt build 19) — `request-changes`

- Lệnh diff (reviewer tự chạy): `git log --format='%h %s%n%b' c7002de..6497ac6`, `git diff --stat c7002de..6497ac6`, `git diff c7002de..6497ac6`, `git show 6497ac6:erp_ai/agent/{runner,test_agent_runner}.py`, `git grep 6497ac6 -- erp_ai/agent/policy.py`. BASE = `git merge-base team/FEAT-007 team/FEAT-007-task-81` = `c7002de`.
- Hai commit: `0e10bc7` test, `6497ac6` feat. 2 file, đều là touchpoint (+104/−20). Reviewer dùng 16 lần gọi tool, không chạy test.
- Tầng 1 đạt: `_classify` trả `(proceed, classification, context)`, `_run` đưa context trả về cho `_reason`; context dựng lại bằng `dataclasses.replace` sau phân loại, qua một lời gọi `_below_threshold` → `policy.is_below_confidence`; `_route` và `status.working` chỉ chạy khi `not context.below_threshold`; dòng `classify` ghi `predicted_confidence_pct`; `git grep 'below_threshold=False'` trên `runner.py` không ra dòng nào; `_reason`, danh sách tool, `test_runner_routing.py`, `test_runner_status.py` không đổi.

Finding (nguyên văn):

- major | STD-TEST-2 | erp_ai/agent/test_agent_runner.py:3160 | The criterion "insert run builds its context with `category=None, pct=None` through the same `is_below_confidence`" has no test that fails if it is removed. This is runner.py:183-185, where unknown counts as below threshold. If an insert run kept `below_threshold=False` before classification, all three new tests would stay green. In the 69 case, the context before and after the rebuild are both below threshold, so `t_cls ok=False` passes either way. The comment at :3165 ("gets the context recomputed") claims more than that assert shows. The only place the pre-classification context reaches `_reason` is an unparseable classification: `_classify` returns at runner.py:332 with the context unchanged. The existing `test_unparseable_classification_still_reasons_at_l1` (:1131) does not check what that run is allowed to do. | Add a `TestRunnerGrant` test. Insert run, stub text "không phải JSON", then a `set_classification` tool turn. Assert `ok` is False and the reason contains "không được cấp". It must be red with an insert-side `below_threshold=False`. | confirmed
- minor | — | — | 2 small points: (a) The `_classify` docstring at runner.py:299 says "routes only above the threshold", but the code routes at the threshold or above. (b) Insert runs with instructor AND act_now are not covered here; that case belongs to the T69 predicate. | dev's call

Review checklist (10): 1 ok · 2 ok · 3 ok với test 1–2, test 3 chưa có lần đỏ trong gói (xem dưới) · 4 ok (cấu hình test dựa vào đều được gieo: L1, act_now 0, ngưỡng 70, `level_cap_a`) · 5 ok · 6 ok · 7 ok (`_classify` là hàm riêng, nơi gọi duy nhất đã sửa) · 8 ok trừ minor (a) · 9 ok (chỉ `dataclasses` của thư viện chuẩn) · 10 ok.

Bằng chứng của dev ở vòng này (nguyên văn dòng kết quả): RED (file test của `0e10bc7` trên mã `c7002de`, lần chạy có lọc, không có dòng HEAD và `MIGRATE_EXIT`): `test_insert_at_threshold_routes_and_writes` `AssertionError: -1 != 70`; `test_low_confidence_insert_skips_routing_writes` `AssertionError: Expected 'apply_route' to not have been called. Called 1 times.`; `Ran 116 tests … FAILED (failures=2)`. GREEN trên `6497ac6`, `MIGRATE_EXIT=0`, một lần giữ khóa: test_agent_runner `Ran 117 tests … OK`; test_runner_routing `Ran 62 tests … OK`; test_runner_status `Ran 39 tests … OK`; test_architecture `Ran 187 tests … OK`; `pre-commit run --all-files` mọi hook Passed, `LINT_EXIT=0`.

Không kiểm được từ diff, và cách tech-lead xử lý (một dev chạy bằng chứng song song với lần review, không sửa, không commit; một lần giữ khóa, mã từ worktree của dev):

- Lần RED không gắn được với `0e10bc7` → chạy lại không lọc: HEAD `0e10bc7`, `MIGRATE_EXIT=0`, `Ran 116 tests in 29.739s` / `FAILED (failures=2)`; `test_insert_at_threshold_routes_and_writes` ở `:3176` `AssertionError: -1 != 70`; `test_low_confidence_insert_skips_routing_writes` ở `:3163` `AssertionError: Expected 'apply_route' to not have been called. Called 1 times.` Đỏ đúng lý do.
- Test thứ ba `test_insert_reason_context_takes_category_cap_of_classification` nằm trong commit mã, chưa có lần đỏ → phép đột biến (bỏ đúng ba dòng tính lại `main_path_level` trong `_classify`, hunk `@@ -373,9 +373,6 @@`, chưa commit): HEAD `6497ac6`, `Ran 117 tests in 30.580s` / `FAILED (failures=1)`, chỉ test đó đỏ ở `:3187` `AssertionError: 'L1' != 'L0'`, hai test của Expect vẫn xanh; trả lại file, cây sạch: `Ran 117 tests in 30.703s` / `OK`. Không phải chỗ hở.
- Các lần GREEN: lần (C) ở trên trên `6497ac6`; lần chạy sau merge sẽ chạy lại.

Xử lý: vòng sửa 1/3, finding major chuyển nguyên văn cho dev (FIX_BASE=`6497ac6`). Test thêm nằm trong touchpoints và kiểm đúng tiêu chí của dòng task, nên là `request-changes`, không phải `design-defect`.

## Vòng 2 (2026-11-15, lượt build 19) — soát hẹp trên diff sửa — `approve`

- Lệnh diff (reviewer tự chạy): `git log --format='%h %s%n%b' 6497ac6..1087184`, `git diff --stat 6497ac6..1087184`, `git diff 6497ac6..1087184`; đọc thêm ở `1087184`: `test_agent_runner.py:3120-3190`, `runner.py:180-215,227-229,285-345`, `policy.py:111-139`. Một commit `1087184` (test), 2 file touchpoint +17/−2. Reviewer dùng 5 lần gọi tool, không chạy test.
- major STD-TEST-2 `test_agent_runner.py:3160`: ADDRESSED. Test mới `test_unparseable_insert_reasons_below_threshold` (`:3171-3184`, khẳng định ở `:3183-3184`): stub không phân tích được nên `_classify` trả ở `runner.py:332` với context chưa đổi, context dựng trước phân loại đi tới `_reason`; test khẳng định `set_classification` `ok` False và lý do chứa "không được cấp". Không dựa vào dữ liệu site thật: `category=None` cho `UNKNOWN_CATEGORY_LEVEL` (`policy.py:113-114`), `permission_level`, `act_now`, ngưỡng đều gieo ở `setUp` (`:3054`, `:111`).
- minor (a) (docstring `_classify`): ADDRESSED, `runner.py:301` nay ghi "routes only at the threshold or above"; chú thích nói quá ở test cũng đã sửa (`test_agent_runner.py:3167`). minor (b) (lần tạo phiếu có instructor VÀ act_now): NOT ADDRESSED, quyền của dev, thuộc vị từ của T69, không chặn.
- Finding mới trong diff sửa: không có blocker hay major. Một minor: test mới dựng dict kết quả tool tại chỗ (`:3181-3182`) thay vì dùng helper, như `_run_insert_classified`; quyền của dev. Review checklist (10) trên diff sửa: 1 ok · 2 ok · 3 ok · 4 ok · 5 n/a · 6 ok · 7 ok · 8 ok · 9 ok · 10 ok.

Bằng chứng của dev ở vòng này (nguyên văn dòng kết quả): đột biến chưa commit (`below_threshold=` quanh `runner.py:202` thành `False if trigger == TRIGGER_TICKET_INSERT else _below_threshold(...)`), HEAD `6497ac6`, `MIGRATE_EXIT=0`: `FAIL: test_unparseable_insert_reasons_below_threshold`, dòng 3183 `AssertionError: True is not false`, `Ran 118 tests in 28.880s` / `FAILED (failures=1)`. GREEN trên `1087184`, cây sạch, `MIGRATE_EXIT=0`, một lần giữ khóa: test_agent_runner `Ran 118 tests in 30.211s OK`; test_runner_routing `Ran 62 tests in 32.759s OK`; test_runner_status `Ran 39 tests in 8.191s OK`; test_architecture `Ran 187 tests in 16.840s OK`; `pre-commit run --all-files` mọi hook Passed, `LINT_EXIT=0`.

Không kiểm được từ diff: các lần GREEN và lint có đúng trên `1087184` không → lần chạy sau merge của tech-lead chạy lại bốn module (kết quả ở dòng `progress:` của T81 trong `tasks.md`).

deferred (không chặn): minor (b) vòng 1; minor về helper ở vòng 2.

Số vòng: 2 (vòng sửa 1/3). Verdict cuối: `approve`.
