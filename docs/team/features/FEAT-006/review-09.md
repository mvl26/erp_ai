Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 09 — FEAT-006 T9

- Diff: `git diff 8c5af9c..989c37d` (nhánh `team/FEAT-006-task-9`; merge `896b7ac`)
- Vòng: 3 (vòng 1 và 2 request-changes, vòng 3 scoped re-review approve; số vòng sửa 2 <= max_rework 3; hai finding khác nhau, vòng 2 chỉ còn phần chưa phủ của finding vòng 1)
- Verdict: approve

## Phát hiện (blocker/major)
| severity | STD | file:line | description | fix | kết quả |
|---|---|---|---|---|---|
| major | STD-TEST-8 | test_routing.py:379 | thiếu ca cho 5 hàng/bảo vệ của bộ kiểm (assignees sai dạng, tên bộ phận rỗng, `expected_sla` lạ, người không phải chuỗi, khóa gốc không phải object) | thêm ca vào `cases` và vòng nạp "không ném" | vòng 2: NOT ADDRESSED một phần |
| major | STD-TEST-8 | test_routing.py:393,451 (routing.py:183-184) | chỉ kiểm bảo vệ đầu của `assignees.<cat>`; thiếu `default` và `prefixes` | hai ca vào `cases` và `nested_junk` | vòng 3: ADDRESSED |

## Deferred
- routing.py:198-203: `departments.<d>` thiếu ca riêng cho kiểm chuỗi của `team` và `head` (bỏ kiểm `team` thì `team` không phải chuỗi lọt qua cả bộ kiểm lẫn bộ nạp). Việc này đã được ghi từ vòng 2; làm ở T11 hoặc ở bước dọn trước C2 nếu chạm cùng file.
- Từ reviewer, cần tech-lead soát ở T11/T12: `routing_rules` rỗng (""/None) làm `validate_routing_config` báo "không phải JSON object hợp lệ", giống `validate_mapping`; T11 phải đảm bảo các lần lưu và test ERP AI Setting hiện có gán `routing_rules` hoặc dựa vào mặc định của T12. Test `test_user_checked_only_when_non_empty_and_agent_not_blocked` cần User `AGENT_USER` và `Administrator` tồn tại trên site test.

## Bằng chứng chạy (dev)
- `cmd.test` trên nền chưa sửa (61e51f2 cùng cây mã với 8c5af9c): Ran 703 tests, OK (đây là lần chạy nối tiếp đang chờ của T7/T2/T8).
- RED T9: Ran 28 tests, FAILED (errors=4), AttributeError thiếu `validate_routing_config`/`DEFAULT_ROUTING_RULES`.
- GREEN `erp_ai.agent.test_routing`: Ran 31 tests, OK. `cmd.test` trên đầu nhánh task 989c37d: Ran 710 tests, OK. Lint: all hooks passed.
- Sau merge: `git diff --stat 989c37d HEAD -- . ':!docs'` rỗng (cây mã = đầu nhánh task đã chạy xanh).
- Dev chứng minh đỏ bằng cách phá từng bảo vệ rồi hoàn tác (AttributeError, KeyError, ValidationError not raised).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 3).
