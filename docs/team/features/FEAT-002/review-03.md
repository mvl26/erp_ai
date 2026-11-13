Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 03 — FEAT-002 T3

- Diff: `git diff a4cb74f..team/FEAT-002-task-3` (vòng 2: `git diff d27f81f..6dd4c6f`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-5 | erp_ai/agent/test_answer_delay.py:23,41,50 | `_pick` thật không chạy trong test nào (setUp giả hóa; test khoảng kiểm stdlib) nên NFR-1 không có test có thể đỏ | giữ `REAL_PICK`, `record` gọi nó, test độ trễ cố định vá ngược về `REAL_PICK` (6dd4c6f) |
| major (vòng 1, ADDRESSED) | STD-TEST-8 | erp_ai/agent/test_answer_delay.py:82-83 | cận dưới (-5) không được kiểm | ghi đối số `_pick` cho `start(-5, 99)` và so `(0, 30)`; thêm `start(-5, -1).delay_s == 0` |

minor (ADDRESSED): kiểu tham số `AnswerDelay.start` và docstring lớp.

## Review checklist (10)
1–10: đạt ở vòng 2 (giới hạn ở diff sửa); vòng 1 phủ 10/10.

## Bằng chứng dev
- ĐỎ (stub): 8 test, failures=6 (`Lists differ: [] != [4]`, `0.0 != 30`).
- Vòng 2, đột biến: `_pick` → `uniform(low, high + 5)` làm 3 test đỏ (`7.90 not <= 4`, `7.09 != 3`, `4.99 != 0`); bỏ cận dưới làm test kẹp đỏ (`[(-5, 30)] != [(0, 30)]`); đột biến đã hoàn lại trước commit.
- XANH: `test_answer_delay` Ran 8 OK; `test_architecture` Ran 42 OK; lint đạt.
- Toàn bộ (vòng 1): Ran 518, failures=16, errors=4; 1 error thêm `test_read.test_get_record_hides_fields_above_users_permlevel` là DB error do chạy đồng thời với T2 trên site chung, chạy riêng 27 test OK. DB 4/4/0/22. Merge sau T2: cây `erp_ai/` giống nhánh task.
- Full suite sau merge T2+T3 sẽ do dev T4 chạy làm nền đầu tiên (hook chặn tech-lead).

## deferred
Không có.
