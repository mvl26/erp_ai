Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 46 — FEAT-007 T46

- Diff: vòng 3 `git diff 8f801ef..0ea0a22` (sửa), cả task `git diff 5dcbd0b..0ea0a22` (nhánh `team/FEAT-007-task-46`, 3 commit; lệnh vòng 3: `git log --oneline 8f801ef..0ea0a22`, `git diff --stat 8f801ef..0ea0a22`, `git diff 8f801ef..0ea0a22`, `git log -1 --format='%an%n%B' 0ea0a22`, `git show 0ea0a22:erp_ai/agent/test_kpi.py` (`:1-60`, `:315-380`, grep `window_end`), `git show 0ea0a22:erp_ai/agent/kpi.py` (`:15-30`, `:100-130`), `git diff 8f801ef..0ea0a22 | grep -ciE 'skip|xfail|expectedFailure'` (0), `git diff --stat 5dcbd0b..0ea0a22`, `git log --oneline 5dcbd0b..0ea0a22`; lệnh vòng 2: `git log --oneline 5dcbd0b..8f801ef`, `git diff --stat 6d6fac6..8f801ef`, `git diff 6d6fac6..8f801ef`, `git diff --stat 5dcbd0b..8f801ef`, `git log -1 --format='%an%n%B' 8f801ef`, `git show 8f801ef:erp_ai/agent/test_kpi.py` (`:320-368`), `git show 8f801ef:erp_ai/agent/kpi.py` (`:100-128`, grep `TASK_DUE`), `git show 8f801ef:erp_ai/tests/test_architecture.py` (grep `TASK_DUE`); vòng 1: `5dcbd0b..6d6fac6`)
- Vòng: 3 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Range: `5dcbd0b..6d6fac6` (1 commit `feat(agent): weekly KPI 4 to 6 in compute_week (FEAT-007)`, 2 file, +189/−11), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `KeyError: 'b_resolution_sample'` / `'c_task_sample'` / `'stale_over_5_days'` và `test_zero_sample_none` `AssertionError: Items in the second set but not the first:`, `FAILED (failures=1, errors=4)` (lỗi thứ 5 là `QueryDeadlockError (1213)` ở `test_kpi1`, do site dùng chung). GREEN `test_kpi` `Ran 7 tests in 4.956s OK`; `test_architecture` `Ran 112 tests in 3.237s OK`. Một lần chạy sau format không in dòng kết quả: không phải bằng chứng; lần kế tiếp có dòng OK.
- Đối chiếu định nghĩa (spec AC-54, `design.md:466-468`, A-D2 `:82`, A-D4 `:84`, `design-w0-fixes-2.md` điểm 3):
  - KPI 4 (`kpi.py:86-101`): đầu mục B qua `category_by_ticket_type`/`ticket_category`, `resolution_date ∈ [ws, we)`, trung bình giờ lịch `resolution_date − creation`, mẫu 0 → `None`. Khớp.
  - KPI 5 (`kpi.py:103-125`): đầu mục C, `creation ∈ [ws − 72 h, we − 72 h)`, ≥ 1 Task `ai_ticket` = phiếu với `Task.creation ≤ phiếu.creation + 72 h`, mẫu 0 → `None`. Khớp.
  - KPI 6 (`kpi.py:130-136`): tập "đang mở tại `we`" dùng chung `_open_at` với KPI 2 (lọc không đổi so với T45), đếm `we − creation > 5 ngày` và `> 7 ngày`, mọi đầu mục, mẫu 0 → 0. Khớp.
- Kiểm đột biến trên dữ liệu của chính test (tính tay từng hàng):
  - KPI 4: `>= ws` → `> ws` (mẫu 2), `< we` → `<= we` (mẫu 4), bỏ lọc đầu mục (mẫu 7), trung bình → trung vị (10 ≠ 14), JSON-order thay `CATEGORIES`-order (D thắng, mẫu 0): đều đỏ.
  - KPI 5: biên đầu cửa sổ `>=` → `>` (25 %/3), biên cuối `<` → `<=` (40 %/5), `≤ 72 h` → `< 72 h` (25 %), "mọi Task" thay "≥ 1 Task" (25 %), bỏ lọc đầu mục (mẫu 7), chỉ dời một đầu cửa sổ (60 %/5 hoặc 33,3 %/3): đều đỏ. **Bỏ hẳn việc dời 3 ngày** (cửa sổ `[ws, we)`): XANH — xem finding.
  - KPI 6: `> 5` → `>= 5` (5), `> 7` → `>= 7` (3), `resolution_date >= we` → `> we` (3/1), bỏ `is not set` (1/1), tính tuổi từ `ws` thay `we`: đều đỏ.
- Sửa test T45: `test_kpi1` và `test_zero_sample_none` chỉ đổi tập khóa sang `KPI_KEYS` và thêm khóa mới, phép khẳng định cũ giữ nguyên (STD-TEST-5 giữ). `setUp` ghi `category_mapping` cố định bằng `set_agent_settings` rồi đọc `get_single`: bỏ được phụ thuộc vào ánh xạ của site (A-13); mapping qua `_mapping_error` (`classification.py:128-148`), nên KPI 4/5 không đi vào nhánh `{}`; D trùng `ticket_type` với B được ghim gián tiếp bởi `b_resolution_sample == 3`.

## Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/test_kpi.py:352 | A-D4 (cửa sổ lùi 3 ngày, chính là tiêu chí của task) không được ghim: hai hàng đổi phía khi bỏ việc dời đối xứng nhau — hàng `window_start` (`:339`, có Task đúng 72 h, đạt) rời mẫu và mồi `window_end` (`:352`, Task sau 1 h, đạt) vào mẫu; mẫu vẫn 4 (`#2`, `#3`, `#4`, mồi cuối), đạt vẫn 2 → `50.0`. Đổi `kpi.py:110` thành `[["creation", ">=", ws], ["creation", "<", we]]` thì `test_kpi5_task_within_72h_edge` vẫn xanh (confirmed, tính tay) | làm cho hai phía không cân: hoặc mồi `window_end` không có Task (cửa sổ không dời → 1/4 = 25 %), hoặc thêm một phiếu C ở `ws − 1 ngày` có Task nhanh và khẳng định `c_task_sample == 5`, `c_task_in_3_days_pct == 60.0`; kiểm lại rằng 4 đột biến biên ở trên vẫn đỏ

minor | — | — | 3 điểm nhỏ: (a) STD-DOC-7: docstring module `kpi.py:4` "A KPI whose sample is 0 is `None`; its sample field is 0" nay sai với KPI 6 (không có trường mẫu, giá trị 0 theo `design.md:468`); (b) STD-TEST-8: mồi `_ticket(we)` (`test_kpi.py:379`) vô hiệu với KPI 6 — tuổi 0 không bao giờ > 5 ngày, nên bỏ hay giữ lọc `creation < we` đều xanh (lọc này đã có T45 ghim cho KPI 2); (c) STD-TEST-8: ca "một Task trễ, một Task sớm" (`:342-345`) chỉ đỏ với đột biến "giữ một Task mỗi phiếu" tùy thứ tự trả về của `get_all` | tùy dev

## Review checklist (10)
1. chưa đạt (A-D4 chưa ghim; mã khớp spec, không thừa) 2. đạt (đúng 2 file) 3. chưa đạt (RED có trước; thiếu ca cho cửa sổ dời, finding) 4. đạt (năm 2001, `now` không dùng, mapping seed trong `setUp`, rollback) 5. đạt (hàm thuần, không gọi ngoài; `load_mapping` không ném) 6. đạt (chỉ đọc, `get_all` có tham số) 7. đạt (thêm khóa trùng tên trường `ERP AI KPI Week`, `design.md:266-268`; `_open_at` giữ lọc của KPI 2) 8. đạt (minor a) 9. đạt (không thêm) 10. đạt (`feat(agent): … (FEAT-007)`, không trailer, nhánh `team/FEAT-007-task-46`)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Reviewer không chạy test (luật site dùng chung); GREEN chỉ có từ dev, lần chạy sau format không in dòng kết quả. Cần `test_kpi` và `test_architecture` sau merge | |
| Site không có phiếu thật tạo trước 2001-08-13 (KPI 6 và KPI 2 đọc mọi phiếu đang mở tại `we`; cùng giả định với T45) | |
| Thiết kế im lặng: Task bị hủy (`status = Cancelled`) có tính là "Task liên kết" của KPI 5 không; KPI 4 có làm tròn không. Mã tính mọi Task và không làm tròn — chỉ ghi cho designer, không chặn | |

## deferred

- (minor, tùy dev) 3 điểm nhỏ ở trên.
- (designer, không chặn) `design.md:467`: nói rõ Task `Cancelled` có tính vào KPI 5 không.

## Vòng 2 — request-changes

- Range sửa: `6d6fac6..8f801ef` (1 commit `test(agent): pin the 3-day shift of the KPI 5 window with a C ticket the day before the week (FEAT-007)`, chỉ `erp_ai/agent/test_kpi.py`, +5/−2); `kpi.py` không đổi. Không thêm marker skip/xfail; commit đúng mẫu, không trailer.
- Bằng chứng của dev: MUTATION RED (cửa sổ `kpi.py:110` thành `[ws, we)`) `FAIL: test_kpi5_task_within_72h_edge` / `AssertionError: 4 != 5` / `FAILED (failures=1, errors=1)` (lỗi kia là `QueryDeadlockError` 1213 ở test khác). GREEN `test_kpi` `Ran 7 tests in 4.777s OK`, `test_architecture` `Ran 112 tests in 3.187s OK`.
- Sửa: thêm phiếu C tạo lúc `ws − 1 ngày` có Task sau 1 h (`test_kpi.py:340-342`), khẳng định đổi thành mẫu 5 / `60.0` (`:364-365`).
- Tính tay ở head, cửa sổ đúng `[ws − 3 ngày, ws + 4 ngày)`: hàng `window_start` (đạt, đúng 72 h), hàng mới `ws − 1 ngày` (đạt), `both` (đạt), `ws` Task 72 h + 1 s (không đạt), `ws + 2 ngày` không Task (không đạt) → 5 mẫu, 3 đạt, `60.0`. Khớp. Mồi `window_start − 1 s`, `window_end`, B/unmapped/None, A đều ngoài mẫu.
- Đột biến lại trên head: bỏ dời (`[ws, we)`) → mẫu 4 (đỏ, khớp RED của dev); đầu `>=` → `>` → 4; cuối `<` → `<=` → 6; `≤ 72 h` → `< 72 h` → 40 %; "mọi Task" → 40 %; bỏ lọc đầu mục → 9; chỉ dời đầu → 6; chỉ dời cuối → 3: đều đỏ.
- **Còn xanh:** dời một khoảng trong `[1 ngày, 3 ngày)`, kể cả đột biến hằng `TASK_DUE = timedelta(hours=48)` (`kpi.py:22`, một hằng dùng cho cả dời cửa sổ `:110` lẫn ngưỡng `:122`). Với 48 h: cửa sổ `[ws − 2 ngày, ws + 5 ngày)`; `window_start` (đạt) rời mẫu, mồi `window_end` (`:356`, Task sau 1 h, đạt) vào mẫu; hàng mới `ws − 1 ngày` vẫn trong → 5 mẫu, 3 đạt (`ws − 1 ngày`, `both`, `window_end`), `60.0`: xanh (confirmed, tính tay). Tương tự với `TASK_DUE` từ 24 h đến 71 h. Tức là con số "3 ngày / 72 h" của AC-54/A-D4 vẫn không được ghim theo chiều nhỏ hơn — cùng nguyên nhân của vòng 1 (hai hàng biên đối xứng đều "đạt"). Đây là lỗ trong gợi ý sửa thứ hai của chính reviewer ở vòng 1 (thêm một hàng, không phá đối xứng); gợi ý thứ nhất (mồi `window_end` không có Task nhanh) đã đủ. Lỗ này đã có từ vòng 1 (khi đó 4/50 % cũng xanh với 48 h), reviewer bỏ sót.

### Đối chiếu finding vòng 1

- major STD-TEST-8 `test_kpi.py:352` (A-D4 không được ghim): **NOT ADDRESSED (một phần)** — đột biến được nêu (bỏ hẳn dời) nay đỏ (`test_kpi.py:340-342`, `:364`), nhưng khoảng dời "3 ngày" chưa được ghim: dời 1–2 ngày hoặc `TASK_DUE` 24–71 h vẫn xanh (`test_kpi.py:355-356`).

### Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/test_kpi.py:356 | Mồi `window_end` và hàng `window_start` vẫn cùng "đạt", nên mọi cửa sổ dời ít hơn 3 ngày (kể cả `TASK_DUE = timedelta(hours=48)` ở `kpi.py:22`) đổi chỗ hai hàng mà mẫu/tỉ lệ giữ 5 / `60.0`; con số 3 ngày / 72 h của AC-54, A-D4 chưa được ghim theo chiều nhỏ (confirmed, tính tay) | phá đối xứng ở chính mồi `window_end`: cho nó không có Task hoặc chỉ một Task trễ (ví dụ `created + 80 h`), giữ mồi `window_start − 1 s` có Task nhanh; giữ hàng `ws − 1 ngày`. Khi đó khẳng định vẫn 5 / `60.0`, còn `TASK_DUE` 48 h → 2/5 = 40 %, bỏ dời → mẫu 4, cuối `<=` → mẫu 6, `TASK_DUE` 73 h → mẫu 6: đều đỏ; dán RED của đột biến `TASK_DUE = timedelta(hours=48)`

Không có blocker/major mới do commit sửa gây ra.

### Review checklist (10) — phạm vi sửa

1. chưa đạt (A-D4 chỉ ghim một phần, finding) 2. đạt (chỉ `test_kpi.py`) 3. chưa đạt (RED đột biến có; thiếu ca cho khoảng dời, finding) 4. đạt (khẳng định đổi do thêm hàng, không phải theo hành vi sai: tính tay khớp; dữ liệu năm 2001, rollback) 5. đạt (không đổi mã) 6. đạt (không đổi mã) 7. đạt (không đổi hợp đồng) 8. đạt (chú thích hàng mới đúng; dùng lại biến `created` như các khối khác) 9. đạt (không thêm) 10. đạt (`test(agent): … (FEAT-007)`, không trailer, cùng nhánh)

### Không kiểm được từ diff — tech-lead xử lý trước khi tick (vòng 2)

| Mục | Kết luận của tech-lead |
|---|---|
| Reviewer không chạy test (luật site dùng chung); GREEN vòng 2 chỉ có từ dev. Cần `test_kpi` và `test_architecture` sau merge | |
| Hai mục còn lại của vòng 1 (phiếu thật trước 2001-08-13; Task `Cancelled`/làm tròn KPI 4) giữ nguyên, sửa không đụng tới | |

### deferred (vòng 2)

- Ba minor vòng 1 (docstring `kpi.py:4`, mồi `_ticket(we)` KPI 6, ca hai Task phụ thuộc thứ tự `get_all`) chưa sửa; vẫn tùy dev, không chặn.

## Vòng 3 — approve

- Range sửa: `8f801ef..0ea0a22` (1 commit `test(agent): give the KPI 5 window-end decoy only a late Task so a shorter shift turns red (FEAT-007)`, chỉ `erp_ai/agent/test_kpi.py`, +5/−3); `kpi.py` không đổi. Không thêm marker skip/xfail (grep 0); commit đúng mẫu, tác giả `hivx`, không trailer. Cả task `5dcbd0b..0ea0a22`: 3 commit, vẫn đúng 2 file của touchpoints.
- Bằng chứng của dev: MUTATION RED (`TASK_DUE = timedelta(hours=48)`) `FAIL: test_kpi5_task_within_72h_edge` / `AssertionError: 40.0 != 60.0` / `Ran 7 tests in 5.113s FAILED (failures=1)`. GREEN `erp_ai.agent.test_kpi` `Ran 7 tests in 5.231s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.229s OK`.
- Sửa: tách vòng lặp hai mồi thành hai khối; mồi `window_start − 1 s` giữ Task sau 1 h (`test_kpi.py:355-356`), mồi `window_end` nay chỉ có Task sau 80 h (`:358`). Khẳng định giữ 5 / `60.0` (`:366-367`).
- Tính tay ở head, cửa sổ đúng `[ws − 3 ngày, ws + 4 ngày)`: `window_start` (đạt, đúng 72 h), `ws − 1 ngày` (đạt), `both` (đạt), `ws` Task 72 h + 1 s (không đạt), `ws + 2 ngày` không Task riêng (không đạt) → 5 mẫu, 3 đạt, `60.0`. Mồi `window_start − 1 s` và `window_end` ngoài mẫu; B/unmapped/None, A ngoài mẫu. Khớp.
- Đột biến lại trên head (tính tay):
  - `TASK_DUE = 48 h` (dời và ngưỡng cùng đổi): cửa sổ `[ws − 2 ngày, ws + 5 ngày)`; `window_start` rời, `window_end` (Task 80 h, trễ) vào → 5 mẫu, 2 đạt (`ws − 1 ngày`, `both`), `40.0`: đỏ, khớp RED của dev.
  - Chỉ dời cửa sổ một khoảng `d ∈ (0, 3 ngày)`, ngưỡng giữ 72 h: `window_start` (đạt) luôn rời, `window_end` (không đạt) luôn vào → nhiều nhất 2/5 = 40 % (với `d < 1 ngày` thì thêm hàng `ws − 1 ngày` rời, mẫu 4): đỏ trên cả khoảng.
  - `TASK_DUE = 73 h`: mồi `window_start − 1 s` (Task nhanh) vào, `window_end` vẫn ngoài → mẫu 6: đỏ. Bỏ dời (`[ws, we)`) → mẫu 4; đầu `>=` → `>` → mẫu 4; cuối `<` → `<=` → mẫu 6; `≤ 72 h` → `< 72 h` → 40 %; ngưỡng nới (72 h + 1 s đạt) → 80 %; "mọi Task" → 40 %; bỏ lọc đầu mục → mẫu 9: đều đỏ.
- Con số 3 ngày / 72 h của AC-54, A-D4 nay được ghim cả hai chiều (nhỏ hơn: `window_end` trễ vào mẫu; lớn hơn: `window_start − 1 s` nhanh vào mẫu); biên "đúng 72 h tính đạt" (`design.md:467`) vẫn ghim ở hàng `window_start`.

### Đối chiếu finding vòng 2

- major STD-TEST-8 `test_kpi.py:356` (mồi `window_end` và hàng `window_start` cùng "đạt"): **ADDRESSED** — `erp_ai/agent/test_kpi.py:358`, mồi `window_end` chỉ có Task sau 80 h; `TASK_DUE = 48 h` và mọi dời `< 3 ngày` cho 40 % thay vì 60 % (RED của dev khớp tính tay).

### Phát hiện (chỉ blocker/major)

Không có blocker/major. Chú thích mới (`:354`, `:357`) đúng với dữ liệu; không có minor mới trong phạm vi sửa.

### Review checklist (10) — phạm vi sửa

1. đạt (A-D4 ghim cả hai chiều; mã không đổi, không thừa) 2. đạt (chỉ `test_kpi.py`) 3. đạt (RED đột biến `TASK_DUE` 48 h có; ca biên cửa sổ dời và ngưỡng 72 h đều có) 4. đạt (khẳng định không đổi; chỉ đổi dữ liệu mồi ngoài mẫu; năm 2001, rollback) 5. đạt (không đổi mã) 6. đạt (không đổi mã) 7. đạt (không đổi hợp đồng) 8. đạt (chú thích đúng; tách vòng lặp hai phần tử thành hai khối rõ hơn) 9. đạt (không thêm) 10. đạt (`test(agent): … (FEAT-007)`, không trailer, cùng nhánh)

### Không kiểm được từ diff — tech-lead xử lý trước khi tick (vòng 3)

| Mục | Kết luận của tech-lead |
|---|---|
| Reviewer không chạy test (luật site dùng chung); GREEN vòng 3 chỉ có từ dev. Cần `test_kpi` và `test_architecture` sau merge | |
| Hai mục còn lại của vòng 1 (phiếu thật trước 2001-08-13; Task `Cancelled`/làm tròn KPI 4) giữ nguyên, sửa không đụng tới | |

### deferred (vòng 3)

- Ba minor vòng 1 (docstring `kpi.py:4`, mồi `_ticket(we)` KPI 6, ca hai Task phụ thuộc thứ tự `get_all`) vẫn chưa sửa; tùy dev, không chặn.
- (designer, không chặn) `design.md:467`: nói rõ Task `Cancelled` có tính vào KPI 5 không.

### Kết luận của tech-lead trước khi tick (2026-11-14, sau merge `f7da325`)

- Test sau merge trên `team/FEAT-007` @ `f7da325`, dưới khóa site: `test_kpi` `Ran 7 tests in 5.411s OK`; `test_architecture` `Ran 112 tests in 3.359s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- Phiếu thật trước 2001-08-13 trên site: `test_kpi` xanh trên `miyano` nên giả định đang đúng; không ghim được từ mã.
- Task `Cancelled` trong KPI 5 và làm tròn KPI 4: câu hỏi cho designer, không chặn; đã báo team-leader.
- Số vòng: 3 (vòng 1, 2 `request-changes`; vòng 3 `approve`). Diff cả task: `git diff 5dcbd0b..0ea0a22`.
