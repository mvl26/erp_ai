# Review package FEAT-006 T3 (bộ đọc điểm), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=4cfd68f; head=team/FEAT-006-task-3 (df1a99c).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 4cfd68f..team/FEAT-006-task-3`
Commit: `git log --oneline 4cfd68f..team/FEAT-006-task-3` → df1a99c feat(classification): validated score reader, bad score means no score (FEAT-006)
Stat: `git diff --stat 4cfd68f..team/FEAT-006-task-3` → erp_ai/agent/classification.py, erp_ai/agent/test_classification.py (đúng touchpoint).
Tiêu chí: dòng T3 của `tasks.md` (AC-1 đoạn đọc, D-3, D-4), design.md mục 3.1; `plan.md` "Shared constraints". Hành vi: điểm sai (0, 4, "2", true, 2.0, thiếu khóa, một đúng một sai) → cả hai = 0 và score_reason = ""; không ném lỗi; lý do cắt 25 từ; `bo_phan` không phải chuỗi → None; hằng `SCORE_VALUES=(1,2,3)`, `SCORE_REASON_MAX_WORDS=25`.
Các test cũ của `test_classification.py` phải còn nguyên (không sửa/nới/xóa).
