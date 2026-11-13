# Review 20 — FEAT-001 T20 (chính sách: điều kiện gửi, mức hiệu lực, giới hạn ngày)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff 1d6976e..team/FEAT-001-task-20` (head bea59c9); merge c7df05b
- Vòng 1 request-changes: major STD-TEST-8 (test từ khóa chỉ lowercase, `.casefold()` phía từ khóa không quyết định); major STD-DESIGN-4 (`OPT_OUT_FIELD` định nghĩa hai lần ở install.py). Vòng 2 (FIX_BASE 300988e): cả hai ADDRESSED; touchpoint mở rộng sang `erp_ai/install.py` (chỉ import)
- Bằng chứng dev: RED errors=20 (stub NotImplementedError); GREEN test_policy Ran 21 OK; kiểm đột biến bỏ casefold → đỏ
- Rò Redis do test_policy tìm ra sau merge: xem T20b / review-23

## Findings
Không còn blocker/major sau vòng 2.

## Deferred
- minor STD-TEST-6: hai test `runs_today` dùng đồng hồ thật (qua nửa đêm có thể chớp).
- minor STD-DESIGN-3: `if not ticket` trả False cho `{}` (design: agent_group rỗng → True); nên `is None`.
- `erp_ai/tests/test_install.py` còn viết cứng "ai_opt_out" thay vì `policy.OPT_OUT_FIELD`.
