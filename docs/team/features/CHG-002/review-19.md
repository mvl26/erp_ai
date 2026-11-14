Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 19 — CHG-002 T19

- Diff: `git diff fd69e5f..f9ef86e` (nhánh `team/CHG-002-task-19`, 1 commit; merge vào `team/CHG-002` ở `e5442bf`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | 0 blocker, 0 major | — |

minor | — | — | 3 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. Chữ ký `apply_message(proposal, ticket, label, approver, operations=None)`, `undo_message(…, operations=None)`, `block_label(operations) -> str` đúng plan; dòng mục nằm ngay sau dòng "Phiếu" ở cả hai message; `operations=None` cho đúng từng byte chữ cũ.
2. Đạt. Đúng 2 file touchpoint.
3. Đạt. RED `errors=3` đúng lý do; giá trị kỳ vọng là chuỗi đầy đủ viết cứng; `block_label` kiểm ở 1, 2, 4 mục và một mục đổi tên.
4. Đạt. Test cũ không đổi; không DB, đồng hồ, mạng.
5. Đạt. Hàm thuần dựng chữ.
6. Đạt.
7. Đạt. Bốn nơi gọi ngoài task (`apply_job.py:262`, `:430`, `:624`, `erp_ai_change_proposal.py:91`) đều truyền theo vị trí, nên đổi tên tham số `file_path` → `label` không vỡ; luật kiến trúc "`change_text.py` chỉ nhập thư viện chuẩn và `erp_ai.constants`" còn giữ.
8. Đạt.
9. Đạt.
10. Đạt. `feat(changes): … (CHG-002)`, một commit, không dòng AI.

## Không kiểm được từ diff, tech-lead đã xử lý
- Sau merge: module `erp_ai.agent.test_change_text` và lần chạy cả app trên `team/CHG-002`, xem dòng progress của T19 trong `tasks.md`.
- Đường dẫn của mục nay vào thân commit: `check_write_path` có chặn xuống dòng và ký tự điều khiển trong `path`/`new_path` hay không nằm ở `change_guard.py` → nêu khi review T12 (hình dạng khối) và T22 (controller truyền `operations`).
- Khối rỗng tới `block_label` cho `"0 file"`: `check_block` chặn khối rỗng (`BLOCK_EMPTY`, T12).

## deferred
1. STD-STYLE-4 `change_text.py:66,83`: tham số `operations` chưa có gợi ý kiểu (`Sequence` được, không nhập `FileOp`).
2. `test_none_operations_is_byte_identical_to_old` có assertion đầu so hàm với chính nó (`test_change_text.py:331-334`); các chuỗi viết cứng phía sau mới là thứ ghim.
3. STD-TEST-8: chưa có ca danh sách rỗng và `kind` lạ (`_item_lines` ném `KeyError`).
