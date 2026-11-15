Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 175 — FEAT-007 T175

- Diff: `git diff 10781fc879e3dfb7df763711a292eb4bf7b62e4c..879bf5b` (nhánh `team/FEAT-007-task-175`; 1 commit `879bf5b`; 1 file +24/−5, là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `a3dd63f` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED bước A (chỉ mục 1, 5, 6; `MIGRATE_EXIT=0`): `FAIL: test_send_matches_comments_box_in_every_gate_branch (...) (branch='over_budget')` (`'L2'` thay cho `'L1'`), `(branch='instructor_role')` và `(branch='assignee')` (`'L1'` thay cho `'L2'`); `Ran 36 tests in 16.447s FAILED (failures=3)`. GREEN bước B (`MIGRATE_EXIT=0`): `Ran 36 tests in 17.278s OK`.
- Lớp 1: đủ Returns (1)–(6), touchpoint đúng, không có gì thừa.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đủ (1)–(6). (1) import `policy` ở `test_ticket_panel.py:11`. (2) patcher ở `:593-595`. (3) `l1` budget 1, giữ `spent_this_month_usd: 0` (`:613-614`), nhánh `over_budget` = `{**l1, "permission_level": "L2"}` (`:675`), bộ chín phần tử giữ nguyên. (4) hằng ở `:567-568`, `return_value` đặt trước hai lời gọi `_decision` (`:788`). (5) bọc `effective_level` có giữ hàm thật (`:722-732`), `outcome["levels"]` ở `:753`. (6) khẳng định mới ở `:803-804`. Các khẳng định cũ không đổi. `ClassVar` là phần thêm để lint sạch (RUF012, STD-STYLE-2), chấp nhận được.
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1/2): chỉ sửa `erp_ai/tests/test_ticket_panel.py`, không có file mới, không sửa mã nguồn.
3. Test trước (STD-TEST-1/8/4): RED bước A ra 3 FAIL kèm subTest, đúng ca "0 < S ≤ 1" của Expect. GREEN `Ran 36 tests ... OK`. Không có skip/xfail. Test bắt được lỗi thật: nếu bỏ patcher, hoặc cho `over_budget` dùng 0.0, hoặc runner đọc `spent_this_month_usd` (=0, không vượt) thì `over_budget` ra `{'L2'}` và đỏ. Nếu `levels` rỗng thì `set() != {'L1'}`, cũng đỏ.
4. STD-TEST-5/6: không khẳng định nào bị nới. Cả hai điều Expect bảo reviewer kiểm đều đạt: không còn đường nào tới `month_spend_usd` thật (`git grep`: người gọi duy nhất là `policy.py:88`, gọi qua tên toàn cục của module, nên `patch.object(policy, "month_spend_usd")` ở `setUp` chặn được); `spent_this_month_usd` không còn quyết định nhánh nào (`is_over_budget` không đọc trường này, `policy.py:86-88`; `set_agent_settings` ghi thẳng DB, không qua validate, `test_utils.py:96-99`); `runner.py:164` gọi `policy.effective_level` qua tên module, nên lớp bọc ghi được mức; `ticket_panel` không gọi hàm này.
5. Lỗi/biên/timeout (STD-ERR-1/2/5): không áp dụng (chỉ sửa test).
6. Bảo mật (STD-SEC-1/3/4/6): không có secret, không chạm `protected_paths`, không có dữ liệu nhạy cảm.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): không đổi API hay dữ liệu.
8. Tên/cấu trúc/style (STD-NAME-1/2, STD-STYLE-4/5): tên theo nghĩa nghiệp vụ, patcher theo đúng mẫu `start` + `addCleanup` sẵn có, không có code chết.
9. Phụ thuộc (STD-DEP-*): chỉ thêm `typing` của thư viện chuẩn.
10. Commit/nhánh (STD-NAME-4/5, STD-GIT-1/8): nhánh `team/FEAT-007-task-175`, một commit `test(ticket_panel): ... (FEAT-007)`, thân commit nêu T175 và design, không có trailer AI.

### Findings

- Không có blocker hay major.
- minor | — | — | 1 điểm nhỏ: `ClassVar[dict]` không ghi kiểu khóa/giá trị (có thể viết `ClassVar[dict[str, str]]` / `dict[str, float]`) | dev quyết định

### Không kiểm được từ diff

- RED bước A không được commit (đúng STD-GIT-2), nên dòng FAIL chỉ có trong báo cáo của dev. Diff không cho thấy các ca S = 0 và S > 1; suy luận từ mã thì cũng đỏ.
- Chưa chạy test ở bước review; `cmd.lint` (RUF012).
- Không nhánh nào đặt `spent_this_month_usd` > ngân sách khi S = 0, nên test này không loại được một runner đọc cả Log lẫn trường đó (OR). Design Điểm 3 mục 3 đã chọn chỉ chứng minh theo một chiều; chiều còn lại thuộc test của T67 trong `test_policy.py`.

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline 10781fc..879bf5b`; `git diff --stat 10781fc..879bf5b`; `git diff 10781fc..879bf5b`; `git show 879bf5b:erp_ai/tests/test_ticket_panel.py`; `git show 879bf5b:erp_ai/agent/policy.py`; `git show 879bf5b:erp_ai/agent/runner.py`; `git show 879bf5b:erp_ai/test_utils.py`; `git show 879bf5b:erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`; `git grep -n "month_spend_usd\|effective_level\|spent_this_month_usd" 879bf5b -- erp_ai`; `git log --format='%an%n%B' -1 879bf5b`; `git branch --contains 879bf5b --list 'team/*'`.

## Kết luận của tech-lead

- RED không commit: nhận. Ba dòng `FAIL:` của dev khớp đúng ca "0 < S ≤ 1" mà Expect tính trước cho mọi S, và dev giữ file log đủ của lần chạy; commit đỏ sẽ trái STD-GIT-2.
- Test sau merge (tech-lead, worktree `feat-007` @ `a3dd63f`, một lần giữ khóa site, `MIGRATE_EXIT=0`): `erp_ai.tests.test_ticket_panel` `Ran 36 tests in 16.873s` / `OK`; `erp_ai.agent.test_policy` `Ran 47 tests in 1.974s` / `OK`. Lint: dev đã chạy `pre-commit run --files erp_ai/tests/test_ticket_panel.py`, exit 0 (hook git không chạy trong worktree dev; `cmd.lint` cả cây chưa chạy lại ở lượt này, xem dòng DỪNG lượt 14 của `tasks.md`).
- Chiều "runner đọc cả Log lẫn trường cũ": không phải chỗ hở của T175 (thiết kế chọn một chiều); `test_policy.py` của T67 đã ghim `is_over_budget` không đọc `spent_this_month_usd`.
- Tick T175: 62/174.

## deferred

- minor: kiểu của `ClassVar[dict]`; không mở vòng sửa.
