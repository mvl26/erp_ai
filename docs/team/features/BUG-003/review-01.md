Feature: BUG-003
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 01 — BUG-003 T1

- Diff: `git diff d425faa95f08194152d52bf8d982be908be7dac3..2354fe0^2` (nhánh `team/BUG-003-task-1`, đầu `fae6172`; commit `362b3bd`, `fae6172`; merge `2354fe0` trên `team/BUG-003`)
- Vòng: 2 (1 vòng làm lại; max_rework = 3)
- Verdict: approve (tầng 1 — đúng spec: đạt C1–C4; tầng 2 — checklist 10/10)

## Vòng 1 — request-changes

- Diff: `git diff d425faa..362b3bd` (2 file, +116/−5)
- Tầng 1: mã đạt C1–C4 (mọi đường ẩn/hiện đi qua `setIndicatorVisible`, ghi `hidden` và `display` cùng lúc; hai hằng style không có `display`, `dockIndicator` không đụng `display`); test chỉ phủ một phần C1.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/tests/test_architecture.py:1326-1328 | `check_status_indicator_hides` chỉ kiểm `render` có cả `setIndicatorVisible(el, false)` và `setIndicatorVisible(el, true)`, không kiểm mỗi lời gọi nằm ở nhánh nào. Hoán đổi hai lời gọi (hiện khi 0 lần chạy, ẩn khi đang chạy — ngược C1) vẫn xanh; reviewer đã thử bằng sed trên file của nhánh. Mẫu `good` của test tự kiểm dùng `if (x) { …false… }` nên điều kiện không được ghim | Ghim điều kiện cùng lời gọi, vd. `if \(state\.runs\.size === 0\) \{\s*setIndicatorVisible\(el, false\);\s*return;`, và `(el, true)` là câu lệnh cuối trước `};` của render; thêm ca tự kiểm cho phép hoán đổi |

minor | — | — | 2 điểm nhỏ: (1) ghi `display` lên khung ngoài helper không bị bắt (vd. `el.style.display = "flex"` trong `dockIndicator`/`render`), chỉ quét hai hằng style; (2) guard "does not call" chưa có ca tự kiểm riêng | tùy dev

## Vòng 2 — approve (scoped re-review)

- Diff: `git diff 362b3bd..fae6172` (FIX_BASE..HEAD; 1 file `erp_ai/tests/test_architecture.py`, +50/−1)
- major STD-TEST-2 (hoán đổi nhánh trong `render`): ADDRESSED — dòng 1331 ghim `if (state.runs.size === 0) { setIndicatorVisible(el, false); return; }`, dòng 1335 buộc `render` kết thúc bằng `setIndicatorVisible(el, true);`; ca tự kiểm 2448-2462 phủ hoán đổi (mỗi kiểm một mảnh) và câu lệnh chèn sau lời gọi cuối.
- minor (1) ghi `display` ngoài helper: ADDRESSED — regex `STATUS_INDICATOR_DISPLAY_WRITE` (114-117) áp cho cả bốn hàm, 2 ca tự kiểm; không dương tính giả với `dots`/`dot`.
- minor (2) ca tự kiểm cho guard: ADDRESSED — ca `reset` ở 2463-2467.
- Phát hiện mới trong diff sửa: không có blocker/major.

minor | — | — | 3 điểm nhỏ: (a) hai mục "does not call" của render (dòng 1342) nay trùng với ghim mới 1331/1335; (b) regex ghi display (dòng 115) chưa bắt `style.setProperty("display", …)`, `cssText`, `style["display"]`; (c) kiểm cuối hàm (dòng 1335) chấp nhận lời gọi cuối có điều kiện như `else setIndicatorVisible(el, true);` | tùy dev

## Bằng chứng của dev
- RED (trước khi sửa): `FAIL: test_status_script_indicator_hides_with_display_none (erp_ai.tests.test_architecture.TestArchitecture…)` — `AssertionError: Lists differ: ['setIndicatorVisible is missing', 'line 7[621 chars]se)'] != []` (9 vi phạm, đều là hành vi lỗi: `line 77: ensureElement sets hidden without display…`, 123, 134, 438).
- GREEN: `Ran 79 tests in 0.798s` `OK`.
- Vòng làm lại: RED `Ran 79 tests` `FAILED (failures=5)` — `AssertionError: 0 not greater than 0 : scanner missed the violation`; GREEN `Ran 79 tests in 0.803s` `OK`.

## "Không kiểm được từ diff" — tech-lead xử lý
- Full suite: sau merge `2354fe0`, `cmd.test` lần 1 `Ran 660 tests in 126.564s` `FAILED (errors=39)` — cả 39 là `QueryDeadlockError (1213)` trong `setUp` của `test_agent_runner`, `test_runner_status`, `tools.test_read` (không file nào thuộc diff), trùng lúc phiên khác chạy suite FEAT-004 trên cùng site `miyano`; lần 2 `Ran 660 tests in 117.672s` `OK`. Nguyên nhân: tranh chấp DB giữa hai lượt chạy suite, không do merge hay task. Xem mục chập chờn bên dưới.
- Test không do reviewer chạy / `mask_js` giữ offset: lượt xanh 660 test ở trên gồm `erp_ai.tests.test_architecture` trên script thật.
- Định dạng: `pre-commit run --all-files` trên `team/BUG-003` @ `2354fe0` — 12 hook `Passed`.
- Hiển thị thật trên trình duyệt (CSS Helpdesk ẩn khung với `display:none` inline, khi nổi và khi gắn): không kiểm được tự động (`ui: false`) → bước tay AC-10 của người, xem acceptance.md.

## Review checklist (10)
1. đạt — đúng và đủ tiêu chí, không thừa (sau vòng 2).
2. đạt — chỉ hai file touchpoint, không file mới.
3. đạt — RED trước GREEN; có ca biên (hoán đổi nhánh, ghi display ngoài helper); không thêm dấu skip.
4. đạt — không assert nào bị nới; test tĩnh, lặp lại được.
5. đạt — không catch mới; try/catch cũ giữ nguyên.
6. đạt — không secret, không `protected_paths`, không bề mặt injection.
7. đạt — không đổi chữ ký hay dữ liệu.
8. đạt — tên và kiểu theo file; không mã chết.
9. đạt — không thêm phụ thuộc.
10. đạt — `fix(panel): … (BUG-003)`, `test(panel): … (BUG-003)`, không trailer AI.

## deferred
- 3 điểm nhỏ của vòng 2 (a)(b)(c) — tùy dev, chưa làm; đề xuất ghi vào `docs/team/debt.md` (STD-TEST-8).
- Test chập chờn (STD-TEST-7): full suite trên site dùng chung `miyano` ra `QueryDeadlockError 1213` khi hai phiên chạy `cmd.test` cùng lúc (dev gặp 3/7/27 lỗi, tech-lead gặp 39 lỗi rồi xanh). Chưa ghi vào `docs/team/debt.md` mục "Test chập chờn" vì tech-lead không có công cụ sửa từng phần file dùng chung đó trong lượt này — team-leader ghi giúp.
