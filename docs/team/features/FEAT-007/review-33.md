Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 33 — FEAT-007 T33

- Diff: `git diff a3dd63fdf9d06fc6f86df9f5e4d8737f8353b6b0..86683d7` (nhánh `team/FEAT-007-task-33`; 2 commit `fb2a925` test, `86683d7` mã; 2 file mới +222, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `caa555a` trên `team/FEAT-007` (đầu lượt 15, 2026-11-15 09:19; lượt 14 đã chạm trần 6 merge trước khi tới lượt task này). Sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_missed_scan `Ran 8 tests in 6.112s OK`, test_architecture `Ran 182 tests in 16.414s OK`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này không ghi file dưới `docs/`); chữ của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên module giả (hằng + `find_missed_tickets` trả `[]`), `MIGRATE_EXIT=0`: `FAIL: test_seven_ticket_kinds … AssertionError: Lists differ: [] != ['43070', '43071', '43072']`; `FAIL: test_failed_run_requeued … [] != ['43070']`; `FAIL: test_grace_edge_exactly_five_minutes … [] != ['43070']`; `FAIL: test_no_enabled_at_noop … [] != ['43070']`; `FAIL: test_batch_limit_oldest_first`; thêm `test_runs_below_daily_limit_still_found`, `test_predicted_category_on_other_entry_type_does_not_count`; `Ran 8 tests in 6.095s FAILED (failures=7)`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_missed_scan `Ran 8 tests in 5.765s OK`, test_architecture `Ran 181 tests in 15.559s OK`.
- Lớp 1: đủ 8 điều kiện AC-16, đúng touchpoints, không thừa.

Đối chiếu 8 điều kiện (`design.md:368-376`) với `erp_ai/agent/missed_scan.py`:

1. `creation > enabled_at` nằm ở `:15`, guard rỗng → `[]` ở `:39-41`. Mốc được đọc thô vì `get_single_value` trả về năm 1, còn `get_datetime(None)` trả về now; cả hai bẫy này đều bị test bắt.
2. `creation <= cutoff` ở `:16`. Test biên có ca đúng 5' và ca 5' trừ 1 s, nên đổi `<=` thành `<` hay bỏ khoảng chờ đều làm test đỏ.
3. `status_category` khác Resolved ở `:17`. 4. `owner` khác AGENT_USER ở `:18`.
5. `NOT EXISTS` dòng `classify` có `predicted_category` ở `:20-23`. Ba test chặn ba hướng: lọc `entry_type`, lọc `predicted_category`, và lần chạy lỗi được xếp lại.
6. `OR` trên từng trường của `CLASSIFICATION_FIELDS` ở `:12`. Ba phiếu `wanted` mỗi phiếu thiếu đúng một trường, nên mỗi vế đều được kiểm.
7. Gọi `policy.can_send_ticket` ở `:55`. 8. Điều kiện `runs_today(name, now) < max_runs` ở `:55`. Đổi `<` thành `<=`, bỏ tham số `now` hay viết cứng giới hạn đều làm test đỏ.

- Thứ tự `creation asc, name asc` đúng. Test lô tạo tên tăng còn `creation` giảm, nên phân biệt được sắp theo tên hay theo ngày. Phiếu bị từ chối cũ nhất không chiếm chỗ, nên nếu đặt `LIMIT 50` trong SQL thì test đỏ.

Checklist (10):

1. Phạm vi: đúng Returns. `SCAN_BATCH=50`, `SCAN_GRACE_MIN=5`, `find_missed_tickets(now) -> list[str]`, không import gateway hay runner. Ba test thêm đều kiểm điều kiện của design, không phải mở rộng phạm vi (STD-DESIGN-5, STD-TEST-2).
2. Chỉ hai file mới, nằm trong `erp_ai/`, test đặt cạnh mã (STD-DESIGN-1, STD-STRUCT-1, STD-STRUCT-2).
3. Có RED trên module giả (7/8 FAIL) rồi GREEN 8/8. Có ca biên và nhánh lỗi. Không có skip marker (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Test độc lập với dữ liệu thật và với đồng hồ: `NOW` cố định, cửa sổ năm 2099, `_found` lọc theo phiếu của chính test, có rollback và chặn commit. Test lô so toàn bộ kết quả, dựa vào việc không có phiếu nào tạo năm 2099; chấp nhận được (STD-TEST-5, STD-TEST-6).
5. Không có try/except, không gọi dịch vụ ngoài. Đầu vào `now` qua `get_datetime` (STD-ERR-1, STD-ERR-2, STD-ERR-5).
6. Truy vấn có tham số. f-string chỉ ghép hằng của mã (`CLASSIFICATION_FIELDS`, `LOG_DOCTYPE`). Không có dữ liệu nhạy cảm (STD-SEC-3, STD-SEC-6).
7. Hợp đồng mới thuần thêm. Không có migration (STD-DESIGN-3, STD-OPS-2).
8. Tên theo profile, không có mã chết. Docstring `_agent_enabled_at` khớp mã (STD-NAME-2, STD-STYLE-5).
9. Không thêm dependency (STD-DEP-1).
10. Commit `test(...)`/`feat(...)` có `(FEAT-007)`. Nhánh `team/FEAT-007-task-33`. Không có trailer AI (STD-NAME-4, STD-NAME-5, STD-GIT-8).

STD-DESIGN-2 (hai lần đọc cấu hình trực tiếp): đạt, không phải design-defect. `agent_enabled_at` và `max_runs_per_ticket_per_day` không phải trường mức quyền hay trường điều kiện gửi. ADR-003 chỉ khóa nhóm loại trừ và cờ opt-out; ADR-005 chỉ khóa mức quyền. Cả hai trường cũng không có trong `POLICY_FIELDS`. Đã có tiền lệ: `runner.py:160` đọc `settings.max_runs_per_ticket_per_day`, `install.py:110-112` đọc thô `agent_enabled_at`. Nhóm loại trừ và opt-out vẫn chỉ đi qua `policy.can_send_ticket`.

### Findings

- Không có blocker hay major.
- minor | — | — | 3 điểm nhỏ: (a) STD-DESIGN-4: câu SQL thô đọc `agent_enabled_at` trùng `install.py:110-112`; có thể tách một hàm đọc dùng chung trong `erp_ai/agent/`. (b) STD-TEST-8: chỉ thử giá trị NULL, chưa thử `""` cho `predicted_category` và cho các trường phân loại. `ifnull` đã xử lý cả hai, và runner chỉ ghi `predicted_category` khi thành công, nên rủi ro thấp. (c) STD-GIT-2: commit test đứng riêng thì đỏ (chưa có module); chấp nhận được vì đây là luồng test-trước của nhóm. | dev's call

### Không kiểm được từ diff

- Câu `CANDIDATES_SQL` không có `LIMIT`. Lô 50 chỉ giới hạn đầu ra, không giới hạn lượng việc. Phiếu thuộc nhóm loại trừ hoặc có cờ opt-out sẽ không bao giờ có dòng `classify`, nên chúng nằm lại trong tập ứng viên đến khi Resolved. Mỗi lượt quét đọc lại toàn bộ tên rồi chạy 2 truy vấn cho mỗi phiếu trước khi tới phiếu mới. Cách lọc sau bằng Python là do design bắt buộc (ADR-003 cấm đọc opt-out trong SQL). Đề nghị designer hoặc tech-lead xem lại mục tiêu 300 s của D-16 khi làm T34.
- Chưa kiểm có index cho `creation`/`status_category` của `tabHD Ticket` trên site; cần đo EXPLAIN khi dữ liệu lớn.
- Reviewer không chạy test (site dùng chung).

### Lệnh git reviewer đã chạy (chỉ đọc)

- `git log --oneline a3dd63f..86683d7`; `git diff --stat` và `git diff` cùng khoảng; `git log --format='%H%n%B---'` cùng khoảng; `git show 86683d7:{erp_ai/agent/policy.py, erp_ai/constants.py, erp_ai/tests/test_architecture.py, erp_ai/install.py, .team/profile.json}`; `git grep -n "max_runs_per_ticket_per_day\|agent_enabled_at\|predicted_category" 86683d7`.

## Kết luận của tech-lead (vòng 1)

- Chưa merge: lượt 14 dừng ở trần 6 merge (T68, T175, T69, T125, T123, T70). Việc đầu lượt 15: merge `team/FEAT-007-task-33` (hai file mới, không thể xung đột), một lần giữ khóa `migrate` + `erp_ai.agent.test_missed_scan` + `erp_ai.tests.test_architecture`, rồi tick và ghi số vào mục này.
- "Không kiểm được" 1 (tập ứng viên không có `LIMIT`, phiếu loại trừ nằm lại mãi): không phải chỗ hở của T33 so với dòng task (Returns chỉ đòi lô 50 ở đầu ra), nhưng là rủi ro thật cho mốc 300 s của D-16 → chuyển team-leader, phải có câu trả lời của designer trước khi T34 (job quét 15 phút) được gọi.
- "Không kiểm được" 2 (index): chưa đo; ghi cho `/team:verify` (NFR hiệu năng của AC-16).

## deferred

- minor (a), (b), (c) ở trên.
- Câu hỏi D-16 cho designer trước T34; phép đo EXPLAIN cho `/team:verify`.
