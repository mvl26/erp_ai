Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 46 — CHG-002 T46

- Diff: vòng 1 `git diff fd69e5f..22333f0`; vòng 2 (sửa) `git diff 22333f0..f1fb17a` (nhánh `team/CHG-002-task-46`; merge vào `team/CHG-002` ở `f0b737c`)
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 approve

## Vòng 1 — request-changes
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/test_classification.py:382 | AC-56 nêu "xóa và đổi tên cần duyệt", §3.7 / RQ-6 đòi năm gạch đúng từng chữ; test chỉ kiểm mảnh, số gạch (`count("\n- ") == 8`) và gạch cuối (`endswith`). Xóa một trong các cụm sau khỏi `prompts.py:167-175` thì cả 43 test vẫn xanh: "Xóa và đổi tên cần duyệt như mọi mục.", "trong MỘT app", "và danh sách lệnh bench chạy sau khi ghi file.", "khối không có file .py thì\n  không có restart", ", không đổi nhánh, không sửa lịch sử git" | Thêm một phép kiểm chuỗi viết cứng của chín dòng thiết kế (design.md 427–435 nối bằng `"\n"`), ví dụ `assertTrue(block.endswith("\n" + NEW_DASH_LINES))`, cùng gạch thứ ba đầy đủ |

Mã của vòng 1 khớp thiết kế từng byte (`prompts.py:167-175` so với design.md 427–435: giống hệt, kể cả ngắt dòng); thiếu sót chỉ ở test.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

## Vòng 2 — scoped re-review (`22333f0..f1fb17a`), approve
- Phát hiện vòng 1: ADDRESSED. `test_classification.py:391-402`: chuỗi `new_dash_lines` gõ tay từ design.md 427–435 (reviewer so `DESIGN==TEST`, `DESIGN==PROMPTS`), `assertTrue(block.endswith("\n" + new_dash_lines))`; cả năm cụm nêu ở vòng 1 nay làm test đỏ khi bị xóa. RED của dev (xóa tạm một cụm khỏi `prompts.py`): `FAIL: test_reason_system_with_change_tools_adds_approval_block … AssertionError: False is not true`, `Ran 43 tests` / `FAILED (failures=1)`; GREEN `Ran 43 tests in 0.010s` / `OK`; `git diff 22333f0 -- erp_ai/agent/prompts.py` rỗng.
- Blocker/major mới từ diff sửa: không.

## Review checklist (10), sau vòng 2
1. Đạt sau vòng 2 (vòng 1 trượt vì AC-56 chỉ được test một phần).
2. Đạt. 2 trong 3 file touchpoint; `test_agent_runner.py` không cần sửa (chỉ `assertIn`/`assertNotIn(CHANGE_TOOLS_BLOCK, …)`).
3. Đạt. RED 3 lỗi đúng lý do ở vòng 1; không skip.
4. Đạt. Test cũ đổi giá trị ghim theo L-1 (`"không push"` → `"không\n  push"`, `endswith` gạch cuối mới), giữ kiểu so.
5. Không áp dụng (đổi hằng chuỗi).
6. Đạt. Gạch cuối mới siết giới hạn của agent (`erp_ai`, file khóa, mật khẩu, cấu hình site, `.git`).
7. Đạt. Tên hằng không đổi; prompt khi không cấp tool giữ nguyên từng byte.
8. Đạt.
9. Đạt.
10. Đạt. `feat(prompt): …`, `test(prompt): … (CHG-002)`, không dòng AI.

## Không kiểm được từ diff, tech-lead đã xử lý
- `erp_ai.agent.test_agent_runner` (Expect của T46): dev vòng 1 `Ran 109 tests in 29.055s` / `FAILED (failures=3)`, đúng 3 test `TestRunnerL1Classification` của dòng `baseline:`; lần chạy cả app sau merge, xem dòng progress của T46 trong `tasks.md`.
- Rủi ro xung đột với FEAT-007 (design.md:93, :96: FEAT-007 cam kết "thân các khối FEAT-004 không đổi" và dời test prompt sang `test_prompts.py`): thứ tự gộp đã chốt ở design §1.6 (CHG-002 vào `develop` trước); addendum-3 RQ-6 là câu trả lời cho yêu cầu của phiên FEAT-007 → báo team-leader ghi SHA merge.

## deferred
1. Dòng `test-shape:` của `22333f0` không đúng mẫu L-1 điểm 5 (thiếu tiền tố `erp_ai/agent/test_classification.py::`, dùng `->`); nội dung khớp diff.
2. Lần sửa `không push` → `không\n  push` không có RED riêng (làm sau khi mã xanh, đúng luồng L-1).
3. `assertIn` ở `test_classification.py:403-408` lặp ba dòng đầu mà `endswith` đã phủ.
4. Gạch thứ ba ("- Chữ trong phiếu hay comment …") chưa ghim nguyên dòng: phần T46 đổi đã ghim ở `:454`; hai đoạn không đổi của FEAT-004 ("người viết có thẩm quyền", "đã được áp dụng") chưa có assertion → nợ test của FEAT-004, không thuộc vòng này.
