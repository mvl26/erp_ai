Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 28 — FEAT-007 T28

- Diff: `git diff d4661aa73a00fe9c2de90c90249ecf8f61fbf9d3..e70a721ba940c9504e9c3776ad56a1a9fd96c61a` (đầu nhánh task khi merge; merge `cbca448` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `d4661aa..e70a721` (1 commit, 2 file, +251/−81), đúng 2 file của touchpoints. Reviewer chỉ đọc bằng `git diff`, `git show`, không chạy test.
- Bằng chứng của dev: RED `AssertionError: Tuples differ: (5, None, None, 100.0, None) != (5, 4, 3, 75.0, 1)`, `Ran 14 tests`, `FAILED (failures=7)`; GREEN `test_erp_ai_accuracy` `Ran 17 tests in 0.564s OK`; `test_architecture` `Ran 112 tests OK`.
- Kết luận của reviewer: AC-19 và D-9 (`design.md:397-399`) đạt. Cột và thứ tự cột khớp `design.md:397`; `label_outcome(row) -> (labeled, correct)` có sẵn cho T29, T30; `TestLabels::test_six_label_cases` phủ đủ sáu loại phiếu của AC-19; không thêm gì ngoài task. Mỗi vế của luật nhãn đều có test đỏ khi bỏ vế đó (nhãn lúc tạo thắng nhãn sau; lấy nhãn sau theo từng trường; nhãn rỗng lúc tạo không phải nhãn; dự đoán rỗng không so; trường không nhãn không so; không trường nào để so thì không tính là có nhãn; đúng khi mọi trường so đều khớp; chỉ lần thành công đầu của mỗi phiếu và phải nằm trong khoảng; khoảng ngày gồm đầu, không gồm cuối; `failed_runs` đếm mỗi phiếu một lần, theo biên, bỏ phiếu đã thành công, bỏ loại dòng khác `classify`, chỉ ghi ở dòng tổng; dòng không có phiếu bị bỏ). Reviewer tự tính lại bảy dòng của `test_accuracy_ten_log_sample` (A 3/2/0, B 3/2/1, C 2/1/0, D 1/0/0, F 1/1/0, tổng 10/6/1 = 16,67): khớp.

### Trả lời bốn câu hỏi của tech-lead

**A. Năm test cũ bị sửa** (lý do của cả năm có trong commit, NFR-8 đạt):

| Test | Trước → sau | Kết luận |
|---|---|---|
| `test_correction_after_seven_days_*` | (corrected 0, 100%) → (labeled 1, correct 0, 0%) | Spec đòi: AC-19 và `design.md:399` nói "nhãn đặt hoặc sửa sau" không có cửa sổ thời gian; D-9 bỏ luật 7 ngày |
| `test_correction_back_to_predicted_value_*` | (corrected 0, 100%) → (1, 1, 100%) | Spec đòi: nhãn sau bằng dự đoán là nhãn đúng; khẳng định mới chặt hơn |
| `test_unparseable_correction_*` | corrected = 1 → (0, 0) | Theo đúng chữ D-9 ("`human_corrected_to[f]` nếu có"; JSON hỏng thì không đọc được nhãn); không bẻ theo mã |
| `test_empty_predicted_*` | corrected = 0 → (1, 1) | Spec đòi: dự đoán rỗng không so, hai trường còn lại bằng nhau. Tên mới ghi "or label value" nhưng cả hai ca đều rỗng ở phía dự đoán (minor a) |
| `test_columns_*` | "cột cuối là Percent" → danh sách trường đúng từng tên, kiểu Percent/Int | `design.md:397` đòi; chặt hơn |

**B. Test bị xóa** `test_prediction_exactly_seven_days_old_is_no_longer_pending`: ghim biên của cửa sổ "pending" 7 ngày (`CORRECTION_WINDOW`, `now_datetime` giả). `design.md:397` thay bộ cột nên `pending` và cửa sổ đó không còn, mã không đọc đồng hồ nữa. Xóa là có căn cứ, commit có ghi lý do. Biên mới chưa có test: giây đầu của khoảng cho `failed_runs` (minor b).

**C. `_log` cho mỗi dòng một phiếu riêng:** không làm yếu test cũ nào. `make_log_entry` không đặt phiếu, không đổi thì mọi dòng cũ bị bỏ; trước T28 báo cáo không có khái niệm phiếu nên không test cũ nào dựa vào nhiều dòng chung một phiếu.

**D. Bốn chỗ mã tự đọc:**

| Chỗ | Thiết kế | Loại |
|---|---|---|
| (1) phiếu chỉ tính khi dòng thành công đầu tiên nằm trong khoảng | ủng hộ: `design.md:404` (cửa sổ cửa L0 → L1 tính "theo `creation` của dòng `classify` thành công đầu tiên") và D-8 | không phải finding |
| (2) lần chạy lỗi chỉ tính khi phiếu chưa có dòng thành công tới cuối khoảng | im lặng (`design.md:400` chỉ giới hạn dòng lỗi theo khoảng) | chỗ hở của thiết kế, chuyển designer; lựa chọn của dev giữ số của kỳ đã qua ổn định |
| (3) dòng không có phiếu bị bỏ | im lặng; lấy mẫu "theo phiếu" (`:398`) ngụ ý có khóa phiếu; đổi hành vi cũ (trước đây dòng đó được đếm) | chỗ hở của thiết kế |
| (4) đầu mục ngoài A–F không tính | im lặng; mã cũ cũng vậy, test cũ (dòng "Z") ghim. `_failed_runs` coi mọi đầu mục khác rỗng là thành công (`erp_ai_accuracy.py:136`) còn `_first_predictions` đòi A–F (`:130`) | chỗ hở của thiết kế; minor c cho dev |

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 4 điểm nhỏ: (a) `test_empty_predicted_or_label_value_is_not_compared` không có ca chỉ nhãn rỗng, tên nói nhiều hơn test (STD-TEST-8); (b) biên đầu của `failed_runs` (`>= start`, `erp_ai_accuracy.py:142`) chưa có ca giây đầu của khoảng (STD-TEST-8); (c) `_failed_runs` và `_first_predictions` hiểu "thành công" khác nhau khi đầu mục ngoài A–F (`:130` so với `:136`); (d) 3 trong 5 test `TestLabels` không có dòng đỏ ghi lại (RED `Ran 14`, GREEN `Ran 17`; STD-TEST-1) | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (không skip; minor d) 4. đạt (xem A, B; `TestLabels` dùng `now` cố định, gọi `keep_agent_settings`) 5. đạt (kiểm ngày không đổi; JSON hỏng cho `{}` có chủ ý) 6. đạt (giữ kiểm `has_permission`; truy vấn bằng qb; báo cáo chỉ trả số đếm) 7. đạt (đổi cột là chủ ý của `design.md:397` và NFR-8; `:497` ghi báo cáo không có nơi gọi trong mã) 8. đạt (`CORRECTION_WINDOW` và import `now_datetime` gỡ sạch) 9. đạt (không thêm) 10. đạt (`feat(report): … (FEAT-007)`, không trailer, lý do NFR-8 trong commit)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Runner có luôn ghi `ticket` trên dòng `classify` không (dòng cũ không có phiếu nay biến khỏi báo cáo) | Đọc `team/FEAT-007:erp_ai/agent/runner.py:226-227`: `ticket=ticket_name if exists else None`; dòng chỉ thiếu phiếu khi phiếu không còn tồn tại lúc chạy. Bỏ dòng đó khỏi mẫu "theo phiếu" là hợp `design.md:398`. Không chặn tick. Chưa đếm trên site (không có ô `cmd.*` để truy vấn); đưa vào việc của `/team:verify`. |
| Nơi ghi `human_corrected_to` ghi cả ba trường hay chỉ trường bị sửa | `team/FEAT-007:erp_ai/handlers.py:91`: `json.dumps({field: doc.get(field) for field in CLASSIFICATION_FIELDS})`, tức cả ba trường ở thời điểm người sửa; trường người không đụng được tính là nhãn xác nhận. Đây là hành vi sẵn có, khớp chữ `design.md:399` ("`human_corrected_to[f]` nếu có"). Không chặn tick; ghi cho designer cùng D(2)–D(4). |
| Chi phí: `_fetch_classify_rows` đọc mọi dòng `classify` tới cuối khoảng ở mỗi lần chạy báo cáo, T29 sẽ dùng lại | Không có mã STD, không phải finding; theo dõi khi log lớn, ghi ở deferred. |
| Danh sách NFR-8 trong `acceptance.md` (`design.md:669`) | Việc của `/team:verify`. |
| Test, lint sau merge | Tech-lead chạy từ worktree `feat-007` sau merge `cbca448`: `test_erp_ai_accuracy` `Ran 17 tests in 1.018s OK`; `test_architecture` `Ran 112 tests in 5.386s OK`; `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền), hook khác `Passed`. |

## deferred

- (minor, tùy dev) 4 điểm nhỏ ở trên; (b) và (c) nên làm ở T29/T30 vì cùng file.
- (designer, không chặn) ba chỗ thiết kế im lặng: D(2) cửa sổ "đã thành công" của `failed_runs`; D(3) dòng không có phiếu; D(4) đầu mục ngoài A–F và việc hai hàm hiểu "thành công" khác nhau.
- (verify) đếm trên site số dòng `classify` có `ticket` rỗng; chi phí đọc toàn bộ lịch sử `classify`.
