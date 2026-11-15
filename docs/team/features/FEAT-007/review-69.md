Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 69 — FEAT-007 T69

- Diff: `git diff 566ff695fb7c937670c6637dbe26502e03f1d259..ce7a027` (nhánh `team/FEAT-007-task-69`; 2 commit `8a99e34` test, `ce7a027` mã; 2 file +194/−0, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `67f0fcb` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED sau commit test, `MIGRATE_EXIT=0`: cả 8 test `TestConfidence` lỗi `AttributeError: module 'erp_ai.agent.policy' has no attribute 'is_below_confidence'` (53), `'latest_classification'` (9), `'confidence_threshold'` (2), `'CONFIDENCE_THRESHOLD_FIELD'` (1); `Ran 55 tests in 2.617s FAILED (errors=65)`. GREEN, `MIGRATE_EXIT=0`: test_policy `Ran 55 tests in 2.714s OK`, test_architecture `Ran 181 tests in 15.481s OK`.
- Lớp 1: mọi tiêu chí đã làm, diff nằm trong touchpoint, không có thừa và không hiểu sai.

Theo từng mục checklist (10):

1. Spec/tiêu chí (STD-DESIGN-5, STD-TEST-2): đạt. Có đủ 5 tên trong Returns, đúng chữ ký, hai cờ là keyword-only. Biên 69 dưới, 70 không dưới. None hoặc -1 là dưới, kể cả ngưỡng 0, đúng chữ A-U1-1 đã sửa ở fixes-2 (1). Người ra lệnh ∧ act_now thì không bao giờ dưới. `latest_classification` trả pct None khi cột là -1 hoặc ngoài 0..100, đúng fixes-2 `:130`. Ba test ngoài Expect chỉ kiểm thêm hành vi đã có trong thiết kế, không thêm tính năng.
2. Touchpoint và cấu trúc (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Chỉ sửa `policy.py` và `test_policy.py`, không có file mới.
3. Test trước, biên, skip (STD-TEST-1/8/4): đạt. RED ở `8a99e34` là AttributeError trên 4 tên mới (`errors=65`); GREEN `Ran 55 … OK`. Không có skip/xfail. Thử đột biến trên giấy, mỗi đột biến đều làm ít nhất một test đỏ: `and`→`or` ở phép miễn người ra lệnh; `<`→`<=`; bỏ phép loại bool hoặc bỏ cận 0..100 của `_known_pct` (riêng cận dưới không lộ qua `is_below_confidence`, nhưng các ca -1/-7 của `latest_classification` và ngưỡng -1 vẫn bắt được); bỏ lọc `entry_type` (dòng `reason` mới hơn sẽ thắng); bỏ lọc `predicted_category` (dòng "" mới hơn sẽ thắng); `creation desc`→`asc`, hoặc bỏ `order_by` để rơi về mặc định `modified desc` (thứ tự chèn B, A, E cố ý khác thứ tự thời gian nên vẫn bắt được).
4. Test độc lập, lặp lại được (STD-TEST-5/6): đạt. Có chốt chặn commit và rollback. Setting được giữ bằng `keep_agent_settings`, mốc giờ tương đối theo `now_datetime()`. Phiếu được tạo mới cho từng ca. Không sửa test cũ.
5. Lỗi và đầu vào (STD-ERR-1/2/5): `except (TypeError, ValueError)` có ghi chú lý do và rơi về mặc định đúng thiết kế ("thiếu/None → 70"). Không gọi dịch vụ ngoài.
6. Bảo mật (STD-SEC-1/3/4/6): đạt. `frappe.get_all` với filters dict nên truy vấn có tham số. `("is","set")` sinh `!= ''`, `can_be_null=False` (đã đọc `frappe/model/db_query.py:1255-1263`), nên loại cả NULL lẫn "". Không có secret, không đụng protected_paths.
7. Hợp đồng và migration (STD-DESIGN-3, STD-OPS-2): chỉ thêm hàm mới, không đổi hàm cũ, không có schema.
8. Tên, style, dead code (STD-NAME-1/2, STD-STYLE-4/5): đạt. Docstring khớp mã. "The only reader" đúng ở `ce7a027`: git grep không thấy chỗ đọc nào khác. `_known_pct` không trùng helper nào có sẵn.
9. Dependency (STD-DEP-1/3/5): không có dependency mới.
10. Commit, nhánh, tài liệu (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2): đạt. `test(policy)…`/`feat(policy)… (FEAT-007)`, không có trailer AI. Nhánh `team/FEAT-007-task-69`. Không đổi hành vi người dùng thấy được.

Truy vấn ERP AI Log trong `latest_classification`: lọc `ticket` + `entry_type="classify"` + `predicted_category` khác rỗng; `order_by="creation desc"`, `limit=1`; pct đi qua `_known_pct`, khớp `U1.md:130` / fixes-2 (1); không đòi `applied=1`, vì thiết kế không đòi.

### Findings

- Không có blocker hay major.
- minor | — | — | 2 điểm nhỏ: (a) `confidence_threshold` chấp nhận chuỗi "80" và số thực (`int(85.7)`→85), còn rỗng/rác/bool/ngoài 0..100 đọc thành 70, rộng hơn câu thiết kế (chỉ nói thiếu/None); vô hại vì validator của Setting (`erp_ai_setting.py:63`) đã giới hạn 0..100; (b) `order_by` không có khóa phụ (`name desc`) khi hai dòng classify trùng `creation`; thiết kế không nói, `creation` có micro-giây nên khó xảy ra | dev's call

### Không kiểm được từ diff

- Reviewer không chạy test.
- Ca "dòng không ghi pct đọc -1" phụ thuộc site đã migrate cột T3 với `default "-1"` (dev báo `MIGRATE_EXIT=0`).
- Luật kiến trúc `POLICY_FIELDS` chưa có `confidence_threshold`; T83 sẽ thêm.

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline 566ff69..ce7a027`; `git log --format='%h %an%n%B---' 566ff69..ce7a027`; `git diff --stat 566ff69..ce7a027`; `git diff 566ff69..ce7a027`; `git show ce7a027:erp_ai/agent/test_policy.py`; `git show ce7a027:erp_ai/agent/policy.py`; `git show ce7a027:erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json`; `git show ce7a027:erp_ai/agent/runner.py`; `git grep -n "confidence_threshold\|predicted_confidence_pct\|confidence_pct" ce7a027`; `git grep -n -i confidence ce7a027 -- erp_ai/agent/`; `git grep -n "<= 100" ce7a027`.

## Kết luận của tech-lead

- Test sau merge (tech-lead, worktree `feat-007` @ `67f0fcb`, một lần giữ khóa site, `MIGRATE_EXIT=0` nên cột `predicted_confidence_pct` mặc định `-1` có trên site): `erp_ai.agent.test_policy` `Ran 55 tests in 2.614s` / `OK`; `erp_ai.tests.test_architecture` `Ran 181 tests in 15.939s` / `OK`.
- `POLICY_FIELDS` chưa có `confidence_threshold`: đúng phân công, thuộc T83 (dòng Returns của T83); từ nay tới T83 không luật nào cấm đọc trường này ngoài `policy.py` → ghi vào lời giao reviewer của T80, T81.
- Lo ngại 1, 2 của dev (ngưỡng rác đọc 70; pct lạ coi là không biết): reviewer xếp minor (a) và xác nhận vế "không biết = dưới ngưỡng" đúng chữ A-U1-1 đã sửa. Không mở vòng sửa.
- Tick T69: 63/174.

## deferred

- minor (a), (b) ở trên.
- Lời giao reviewer của T80, T81: kiểm không nơi nào ngoài `policy.py` đọc `confidence_threshold` (luật máy tới T83 mới có).
