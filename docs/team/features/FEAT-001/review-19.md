# Review 19 — FEAT-001 T15 (cổng: chi phí, client SDK, phụ thuộc)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 1d6976e..team/FEAT-001-task-15` (head 82c2f1b); merge b4122ab
- Bằng chứng dev: RED Ran 10 FAILED (failures=5, errors=3, stub không có hành vi); GREEN Ran 10 OK; pre-commit exit 0
- Sau merge (qua dev, cùng cây với T20b): `--app erp_ai` Ran 186 tests OK hai lần liên tiếp

## Findings
Không có blocker/major.

## Deferred
- minor STD-TEST-8: `usage.get(k, 0)` ném TypeError khi khóa có giá trị `None` (SDK trả `cache_*_tokens=None`); T17 `call_model` phải chuẩn hóa usage (None → 0) trước `compute_cost`, hoặc sửa `or 0` + test.
- minor STD-ERR-2: `retry-after` "nan"/"inf"/âm lọt qua `float()`; chưa test cắt `message_prefix`, nhánh ngày HTTP.
- STD-TEST-7: test_install chớp nhoáng deadlock 1213 khi chạy song song nhiều agent trên site miyano (ghi nhận, không tái hiện khi chạy tuần tự).
- Kiểm kiến trúc T40: `test_secret_handling_rules` cho phép `erp_ai/gateway/**`, còn test T15 chỉ cho `client.py`; thống nhất.
