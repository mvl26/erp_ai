Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 03 — CHG-002 T3

- Diff: `git diff fd69e5f..44727f4` (nhánh `team/CHG-002-task-3`, 1 commit; merge vào `team/CHG-002` ở `f46ebf2`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | 0 blocker, 0 major | — |

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. `TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES` (tên nhập lại, A-1.2); `TEXT_TOO_LARGE` dựng từ hằng (A-1.3); chữ `TEXT_SECRET_NAME`, `GIT_DIR`, `TEXT_HAS_NUL`, `TEXT_NOT_UTF8` đúng §3.1; thứ tự `TEN_CAM` → `.git*` → kích thước → NUL → UTF-8 chặt; đúng một phép so kích thước (A-1.4); `SETSID_EXECUTABLE` cạnh hai hằng thực thi (A-5); `SEARCH_FILE_MAX_BYTES`, `resolve_safe_path`, `read_source`, `search_source` chưa đụng (T4, T49).
2. Đạt. Đúng 2 file touchpoint.
3. Đạt. RED 10 lỗi vì thiếu thuộc tính; có cặp biên 2 MiB, `data=None`, byte rỗng; không skip.
4. Đạt. Chỉ thêm test; `unittest.TestCase` thuần.
5. Đạt. Chỉ bắt `UnicodeDecodeError` và đổi thành lý do.
6. Đạt. Luật siết thêm cái tool được phép.
7. Đạt. Chỉ thêm.
8. Đạt (minor d).
9. Đạt. Không thêm phụ thuộc.
10. Đạt. `feat(source): … (CHG-002)`, một commit, không dòng AI.

## Không kiểm được từ diff, tech-lead đã xử lý
- Sau merge, module `erp_ai.agent.tools.test_source` trên `team/CHG-002`: `Ran 116 tests` / `OK`; lần chạy cả app của đợt: xem dòng progress của T3 trong `tasks.md`.
- Luật `.git*` tách theo `os.sep`: T4 và T9 phải truyền đường dẫn tương đối dùng `/` (đúng trên Linux) → nhắc khi review T4, T9.
- Trước T9, `TEXT_SECRET_NAME` là bản chép thứ hai của `change_guard.NAME_FORBIDDEN` và hai chữ `GIT_DIR` còn khác nhau: đúng kế hoạch, T9 trỏ về hằng của `source.py`.
- Luật kiến trúc "`setsid` đúng 1 lần", "so `CHANGE_FILE_MAX_BYTES` chỉ ở `text_refusal`" thuộc T47, T49.

## deferred
1. STD-DESIGN-5 `source.py:40`: hằng phụ `GIT_NAME_PREFIX` không có trong Returns (không dùng lại được `change_guard.GIT_DIR_NAME` vì vòng import); vô hại.
2. STD-TEST-8 `test_source.py:2384-2397`: chưa có ca từ khóa bí mật chỉ nằm ở tên thư mục (ví dụ `myapp/secrets/x.py`) → T4 hoặc T9.
3. STD-TEST-2 `source.py:37`: `TEXT_TOO_LARGE` chỉ ghim bằng so cả chuỗi; viết tay chuỗi vẫn xanh → luật kiến trúc ở T49.
4. STD-NAME-6 `test_source.py:2373`: `test_order_and_reasons` ghim cả `SETSID_EXECUTABLE` mà tên test không nói.
