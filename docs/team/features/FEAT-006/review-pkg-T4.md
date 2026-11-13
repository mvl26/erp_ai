# Review package FEAT-006 T4 (prompt phân loại), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=b1af21f; head=team/FEAT-006-task-4 (a7db04d).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff b1af21f..team/FEAT-006-task-4`
Commit: a7db04d feat(prompts): classify prompt score scale, 4 JSON keys, optional department list (FEAT-006)
Stat: erp_ai/agent/prompts.py, erp_ai/agent/test_classification.py (đúng touchpoint).
Tiêu chí: dòng T4 của `tasks.md` (AC-1 prompt, AC-5/D-10, AC-15), design.md mục 3.1, spec mục Dữ liệu (bảng thang điểm: đối chiếu chép nguyên văn). Test prompt suy luận hiện có không đổi (T23). Test cũ của `test_classification.py` phải còn nguyên.
