# Review package FEAT-006 T10 (`sla_lag` và `departments`), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=7fa9ad9; head=team/FEAT-006-task-10 (2f0b871).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 7fa9ad9..team/FEAT-006-task-10`
Commit: 2f0b871 feat(routing): sla_lag and departments (FEAT-006)
Stat: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py (đúng touchpoint).
Tiêu chí: dòng T10 của `tasks.md` (AC-12 lệch mức: 2 con số, D/E không kiểm; D-10 tên bộ phận cho prompt), design.md mục 3.3 và nơi nói về `sla_lag`/SLA lệch, spec AC-12.
Điểm cần soi: (1) quy tắc làm tròn dev chọn (`actual_min = ceil(resolution_s/60)`, chỉ coi là chậm khi `resolution_s > expected_min*60`) vì tasks.md không nêu: có khớp design/spec AC-12 không, và có test pin; (2) mỗi bảo vệ có ca riêng (STD-TEST-8): hỏi đột biến trong đầu cho từng điều kiện của `sla_lag` và `departments`; (3) `departments` giữ thứ tự khai và kiểu tuple.
Bằng chứng dev: RED 13 lỗi AttributeError (`sla_lag` chưa có); GREEN `test_routing` 44 OK; `cmd.test` 723 OK; lint pass; 11 đột biến đều đỏ rồi hoàn tác (bảng trong báo cáo dev, chưa dán đủ vào gói).
