Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 30 — FEAT-007 T30

- Diff: `git diff b403799457c8780834f44bfa6f45e33cb1018332..1059db031b25a8f85ba5e66a06f3820acd0e8491` (đầu nhánh task khi merge; merge `6c231aa` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `b403799..1059db0` (1 commit, 2 file, +257/−13: 81 dòng mã, 189 dòng test, 9 test mới), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED (đổi hình dạng trả về trước, tóm tắt `[]`): 7 test `AssertionError: Lists differ: [] != ['Phân loại ≤ 5 phút', 'Phân loại > 5 phút', 'Chưa phân loại', 'Cửa L0 → L1']`, gồm `test_six_tickets_three_numbers`; sau đó, với phiếu được phân loại sau cuối khoảng: `AssertionError: Tuples differ: (0, 0, 1) != (1, 0, 0)`. GREEN `test_erp_ai_accuracy` `Ran 38 tests in 14.783s OK`; `test_architecture` `Ran 112 tests in 5.514s OK`.
- Kiểm đột biến trên dữ liệu của chính test: đúng 5:00 đổi thành `<` → `test_six_tickets` ra `(1,2,2)`; 5:01 có test riêng; mỗi loại "bỏ qua có chủ ý" nếu bị đếm thì đổi một số (phiếu của agent → "chưa phân loại", opt-out → "≤ 5", nhóm loại trừ → "> 5", phiếu đủ nhãn theo `created_labels` → "> 5", phiếu đủ nhãn hiện tại → "chưa phân loại"); `all` thành `any` → đỏ; lần thành công đầu thay bằng dòng đầu hoặc lần thành công cuối → đỏ; hai biên khoảng ±1 s → đỏ; dữ liệu cửa giới hạn theo khoảng → đỏ.

### Tám điều tech-lead hỏi
1. Bốn test có sẵn bị chạm (`_rows`, `test_no_prediction_in_range_gives_empty_data`, `test_columns_have_the_documented_fieldnames`, `test_failed_runs_count_tickets_without_success_in_the_range`): chỉ đổi phép tách tuple; không phép khẳng định nào đổi (STD-TEST-5 giữ).
2. `l0_l1_gate` tách ra `_gate_result(rows, now)`: chữ ký và thân không đổi. Trong `execute` một lần đọc tới `max(end, now + 1µs)`; dòng của khoảng lọc bằng `< end` (cùng tập, cùng thứ tự với `_fetch_classify_rows(end)` cũ nên dữ liệu T28 không đổi); dòng của cửa lọc bằng `<= now` (bằng `l0_l1_gate(now)`); `test_gate_item_stops_at_now_inside_the_range` đỏ ở cả hai đột biến.
3. "Đủ nhãn lúc tạo": khớp `design.md:402` khi phiếu có dòng thành công (`created_labels` của lần thành công đầu). Khi không có dòng thành công, mã đọc trường của phiếu lúc này; thiết kế không nói dùng gì ở đây (nguồn đúng là `ai_created_labels`, T60 chưa cài). Chỗ hở của thiết kế, không phải finding của dev. Hệ quả: phiếu bot lỗi hoặc chưa chạy mà người điền đủ 3 trường sau đó bị bỏ ra thay vì tính "Chưa phân loại" (khớp luật quét của AC-16).
4. Dòng thành công sau cuối khoảng vẫn cho độ trễ của phiếu tạo trong khoảng: đúng; có test đỏ `(0,0,1)` nếu chỉ dùng dòng của khoảng.
5. "Bỏ qua có chủ ý" đúng ba loại của `design.md:402` (`erp_ai_accuracy.py:148-154`); phiếu bị `daily_limit` hoặc mức L0 chặn tính "Chưa phân loại" như thiết kế. Thiết kế im lặng về phiếu tạo trước khi bật agent (AC-16 bỏ chúng khỏi việc quét, ở đây chúng được đếm): chỗ hở của thiết kế.
6. Nhãn tóm tắt là chuỗi thường, nhất quán với `TOTAL_LABEL` và chuỗi kết luận của T28/T29; mục cửa là `f"{verdict} ({correct}/{labeled})"`, khớp `design.md:404`.
7. Ngày năm 2001 trong test mới: phiếu thật của site nằm ngoài khoảng; `setUp` nền đã che dòng `classify` thật (STD-TEST-6 giữ).
8. Cỡ diff: không gì ngoài task trừ phần gộp một lần đọc và test của nó (minor a).

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 2 điểm nhỏ: (a) STD-DESIGN-5: `l0_l1_gate` được tách thành `_gate_result`/`_through` để báo cáo chỉ đọc dòng một lần; gọi thẳng `l0_l1_gate()` thì đơn giản hơn, kết quả như nhau, nhưng `test_classify_rows_are_read_once` (`:670-676`) nay ghim một tính chất không ai yêu cầu; (b) STD-STYLE-4: `_summary` (`erp_ai_accuracy.py:157`) không có docstring trong khi các hàm phụ mới bên cạnh có | tùy dev

## Review checklist (10)
1. đạt (minor a) 2. đạt 3. đạt 4. đạt 5. đạt (`_validate_dates` không đổi) 6. đạt (`has_permission(LOG_DOCTYPE, "report", throw=True)` ở `:83` chạy trước mọi lần đọc; tóm tắt chỉ có số đếm và kết luận) 7. đạt (trả 5 phần tử là hợp đồng 3.5.3 của thiết kế; ngoài thư mục báo cáo không ai gọi `execute`) 8. đạt 9. đạt (không thêm) 10. đạt (`feat(report): … (FEAT-007)`, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Runner ghi `created_labels` trên dòng `classify` thành công nằm ngoài diff; đường production của "đủ nhãn lúc tạo" phụ thuộc vào đó | Cột `created_labels` do T3 thêm; phần ghi giá trị thuộc đợt 1 (U1/U4b) theo bảng đơn vị, chưa có ở đợt 0. Ở đợt 0 nhánh "không có `created_labels`" chạy như test đã ghim. Không chặn tick; ghi cho `/team:plan` đợt 1 và `/team:verify`. |
| Frappe Desk hiển thị `report_summary` thế nào (`.js` không đổi) | Việc của `/team:verify` (kiểm màn hình, cùng AC-56). |
| Test sau merge | Tech-lead chạy từ worktree `feat-007` sau merge `6c231aa`: `test_erp_ai_accuracy` `Ran 38 tests in 6.376s OK`; `test_architecture` `Ran 112 tests in 5.449s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền). |

## deferred

- (minor, tùy dev) 2 điểm nhỏ ở trên.
- (designer, không chặn) `design.md:402`: nêu nguồn của "lúc tạo" trước T60 và sau T60 (`ai_created_labels`); nói rõ phiếu tạo trước khi bật agent có tính vào "Chưa phân loại" không.
- (đợt 1 / verify) runner ghi `created_labels`; cách Desk hiện `report_summary`.
