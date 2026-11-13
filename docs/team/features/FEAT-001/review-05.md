# Review T5 (FEAT-001)

Verdict: approve (round 2; 1 vòng rework)
Diff: `git diff a85f798..team/FEAT-001-task-5` (head 922b20a); vòng 2: `git diff 4268655..team/FEAT-001-task-5`.
Vòng 1 request-changes: major STD-TEST-8 run_eval.py:26 (`None == None` gán nhãn cho dòng không có ticket_type); major STD-TEST-2 test_run_eval.py:93-97 (test báo cáo không giữ phần theo nhóm, ma trận nhầm, nhóm tác giả khác). Vòng 2: cả hai ADDRESSED.
minor | — | — | tên biến `m` đổi thành `metrics` làm diff lớn hơn; nhóm count 0 in "0.0% (0/0)" | dev's call (deferred)
Diễn giải dev cần người xác nhận: `top_owner` = chủ sở hữu nhiều nhất, hòa thì theo thứ tự chữ cái; dự đoán rỗng/ngoài A–F = chưa phân loại và sai; 0 dòng gán nhãn → accuracy 0.0, verdict "< 70%"; hai nhóm cùng ticket_type thì nhóm đầu A–F thắng (T9 nên cân nhắc validate_mapping chặn trùng).
Bằng chứng dev: vòng 1 RED (stub) GREEN 4 test, `--app erp_ai` 15 OK; vòng 2 RED `0 != 2` GREEN 5 test, pre-commit exit 0.
