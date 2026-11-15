Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 29 — FEAT-007 T29

- Diff: `git diff cbca448f126fcefadf0dc6609ccae2469e497346..9737874038d9f545e6d5845ea2df55bb19b5bbe2` (đầu nhánh task khi merge)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 1 request-changes, vòng 2 approve)

## Vòng 1 — request-changes

- Range: `cbca448..414a9e8` (1 commit, 2 file, +184/−4), đúng 2 file của touchpoints; không gì dưới `erp_ai/agent/**` đổi.
- Bằng chứng của dev: RED (hàm giả `l0_l1_gate` trả `GateResult("", 0, 0)`): `FAIL: test_not_enough_sample_29 ... AssertionError: Tuples differ: ('', 0, 0) != ('Chưa đủ mẫu', 29, 29)`; `FAIL: test_pass_exactly_85 ... ('', 0, 0) != ('Đạt', 40, 34)`; `FAIL: test_fail_82_5 ... ('', 0, 0) != ('Chưa đạt', 40, 33)`; `FAIL: test_pass_30_26 ... ('', 0, 0) != ('Đạt', 30, 26)`; `FAIL: test_outside_window_ignored ... ('', 0, 0) != ('Đạt', 32, 30)`; `Ran 29 tests in 3.222s`, `FAILED (failures=10)`. GREEN `test_erp_ai_accuracy` `Ran 29 tests in 2.598s OK`; `test_architecture` `Ran 112 tests in 5.300s OK`.
- Kết luận của reviewer: phần báo cáo của AC-18 đạt; hằng, `GateResult`, chữ ký `l0_l1_gate` và ba chuỗi kết luận khớp `design.md:404` và `tasks.md`; cả 5 test được nêu tên có trong diff và đã đỏ với hàm giả.
- Kiểm đột biến (đọc mã): sàn 29/30 (`<` thành `<=` → `test_pass_30_26`; hạ sàn → `test_not_enough_sample_29`); đúng 85 % (`>=` thành `>` → `test_pass_exactly_85`); hai biên cửa sổ 14 ngày (`test_outside_window_ignored`); lần thành công đầu của mỗi phiếu (`test_window_uses_the_first_successful_row_of_each_ticket`); chuỗi kết luận so bằng tuple; `now` mặc định (`test_default_now_is_the_current_time`).

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py:473-486 | `test_rows_of_other_entry_types_are_ignored` không bao giờ đỏ trên dữ liệu của chính nó. Dòng mồi `reason` chỉ có `predicted_category="A"`, không có `predicted_ticket_type/agent_group/priority`. Bỏ `.where(log.entry_type == "classify")` (`erp_ai_accuracy.py:153`) thì dòng lọt qua nhưng `label_outcome` trả (False, False), kết quả vẫn ("Chưa đủ mẫu", 29, 29). Test xanh vì lý do sai. | Cho dòng mồi đủ các giá trị `predicted_*` của `PREDICTED` để khi lọt qua thì ra ("Đạt", 30, 30). Dán dòng đỏ khi bỏ bộ lọc. |

minor | — | — | 2 điểm nhỏ: (a) `test_default_now_is_the_current_time` vá tên `now_datetime` ở mức module, gọi thẳng `frappe.utils.now_datetime()` sẽ làm test đỏ dù hành vi như nhau (STD-TEST-6); (b) mỗi lần gọi cửa đọc mọi dòng `classify` từng ghi, T32 sẽ làm vậy ở mỗi lần lưu Setting (không trái STD; ghi cho T32/T31) | tùy dev

### Bảy điều tech-lead hỏi
1. Cửa sổ `(now − 14 ngày, now]` theo `creation` của dòng `classify` thành công đầu tiên, bỏ qua bộ lọc báo cáo: khớp `design.md:404`.
2. `_first_successes` dùng chung: hành vi báo cáo của T28 không đổi (cùng vòng lặp, A–F, `setdefault`, thứ tự chèn); thỏa STD-DESIGN-4.
3. So ngưỡng bằng `Fraction`: đúng; thiết kế chỉ nói "≥ 0.85"; không thêm hành vi.
4. Test thêm: phần lớn là biên hợp lệ; `test_constants_are_the_documented_numbers` trùng một phần nhưng không vô nghĩa; `test_rows_of_other_entry_types_are_ignored` bị che (major trên).
5. `l0_l1_gate` không tự kiểm quyền: không phải finding. Hàm không whitelisted, chỉ trả số đếm; `execute` kiểm `has_permission` trước; ở T32 nó chạy trong `on_update` của ERP AI Setting sau khi quyền ghi đã được kiểm. Thiết kế im lặng; review T32 nên xác nhận chỉ người ghi Setting thấy thông báo.
6. `_failed_runs` coi mọi đầu mục khác rỗng là thành công còn `_first_successes` đòi A–F: có sẵn từ T28 (`review-28.md` minor c); chỗ hở của thiết kế, cần một định nghĩa; không phải finding của T29.
7. `AccuracyTestCase.setUp` viết lại mọi dòng `classify` bằng một câu lệnh: có sẵn, ngoài diff này; hoãn, không chặn. Thuộc STD-TEST-6 / STD-TEST-7: ghi `docs/team/debt.md`, designer chọn cách cô lập.

### Review checklist (10)
1. đạt 2. đạt 3. đạt 4. trượt (test bị che ở trên) 5. đạt (nhánh `labeled < 30` đứng trước phép chia) 6. đạt 7. đạt 8. đạt 9. đạt (chỉ thư viện chuẩn) 10. đạt

## Vòng 2 — approve (scoped re-review)

- Range sửa: `git diff 414a9e873e306154e20a3abac0c4bd03b84042de..9737874038d9f545e6d5845ea2df55bb19b5bbe2` (1 commit `test(report): … (FEAT-007)`, 1 file `test_erp_ai_accuracy.py`, +7/−1); `erp_ai_accuracy.py` không đổi so với vòng 1.
- Bằng chứng của dev: RED đột biến 1 (bộ lọc dòng 153 cho mọi dòng qua): `AssertionError: Tuples differ: ('Đạt', 30, 30) != ('Chưa đủ mẫu', 29, 29)` (`FAIL: TestGate.test_rows_of_other_entry_types_are_ignored`); RED đột biến 2 (`_failed_runs` dòng 184 `>= start` thành `> start`): `ERROR: test_failed_run_at_the_first_second_of_the_range_counts (…TestLabels…)` với `KeyError: 'Tổng'`. GREEN (mã sản phẩm không đổi) `test_erp_ai_accuracy` `Ran 29 tests in 2.885s OK`; `test_architecture` `Ran 112 tests in 5.446s OK`.

| # | Finding vòng 1 | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | major STD-TEST-5: dòng mồi `reason` không bao giờ có nhãn | ADDRESSED | `test_erp_ai_accuracy.py:476-481`: dòng mồi nay có `predicted_category="A"` cùng mọi trường `predicted_*` của `PREDICTED` và `created_labels=PREDICTED` trên phiếu riêng; bỏ bộ lọc thì cửa thấy 30/30 và trả "Đạt" |
| 2a | minor: vá `now_datetime` theo đường dẫn module | NOT ADDRESSED (minor, tùy dev) | `:495-500` không đổi |
| 2b | minor: mỗi lần gọi cửa đọc mọi dòng `classify` | NOT ADDRESSED (minor, ghi cho T31/T32) | `erp_ai_accuracy.py:37` không đổi |
| — | đột biến `_failed_runs` `>= start` chưa có dòng đỏ ở vòng 1 | nay có bằng chứng | `ERROR ... KeyError: 'Tổng'` |

`KeyError: 'Tổng'` có là cái ghim chấp nhận được cho biên `>= start` không: có. Với `> start` dòng "at-start" không được đếm, báo cáo đi nhánh trả sớm `return _columns(), []` (`erp_ai_accuracy.py:77-78`), `_rows()` dựng dict rỗng và đọc `["Tổng"]` ném KeyError. Chỉ đột biến này dẫn tới đó và test không thể xanh khi nó còn; lỗi ngược lại (đếm cả dòng sớm hơn) ra 2 thay vì 1. Cái giá duy nhất là thông báo đỏ kém rõ.

Finding mới trong diff sửa: không có. Ngoài phạm vi (không phải finding): dòng mồi lặp lại việc `_row` đã làm (thêm tham số `entry_type` cho `_row` thì bỏ được bản chép); `test_failed_run_at_the_first_second_of_the_range_counts` nên `assertIn("Tổng", rows)` trước.

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `QueryDeadlockError` từ `setUp` đã ghi vào `docs/team/debt.md` chưa | Chưa ghi trong lượt này (tech-lead không sửa `docs/team/debt.md` khi chưa có quyết định của team-leader về cách cô lập); báo team-leader trong lời trả về: test STD-TEST-7, `AccuracyTestCase.setUp` khóa mọi dòng `classify` trên site dùng chung. Không chặn tick: mã có sẵn từ T28 đã merge, ngoài diff T29. |
| `test_architecture` còn xanh sau merge | Xem dòng progress của T29 trong `tasks.md`. |

## deferred

- (minor, tùy dev) 2a, 2b và hai ghi chú ngoài phạm vi của vòng 2; 2b cần xét ở T32 (mỗi lần lưu Setting đọc toàn bộ dòng `classify`).
- (designer, không chặn) một định nghĩa "dòng thành công" cho `_failed_runs` và `_first_successes` (đầu mục ngoài A–F).
- (nợ test, STD-TEST-7) `AccuracyTestCase.setUp` viết lại mọi dòng `classify` trong mỗi test: nguồn `QueryDeadlockError` trên site dùng chung.
- (review T32) xác nhận chỉ người ghi ERP AI Setting thấy số "correct/labeled" của cửa.
