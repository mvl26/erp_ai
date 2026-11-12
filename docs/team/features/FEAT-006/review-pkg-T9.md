# Review package FEAT-006 T9 (cấu hình routing_rules: mặc định, bộ nạp, bộ kiểm), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=8c5af9c; head=team/FEAT-006-task-9 (a692a70).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 8c5af9c..team/FEAT-006-task-9`
Commit: a692a70 feat(routing): routing_rules default, loader and validator (FEAT-006)
Stat: erp_ai/agent/routing.py (+145), erp_ai/agent/test_routing.py (+95) (đúng touchpoint).
Tiêu chí: dòng T9 của `tasks.md` (AC-4 bộ kiểm, AC-14 không hằng người trong .py, D-1, D-11), design.md mục 3.3 (dạng cấu hình, bảng đường dẫn khóa sai), plan.md "Shared constraints".
Kiểm: (1) `DEFAULT_ROUTING_RULES` đúng 3.3, danh sách người rỗng, `expected_sla` theo D-11; (2) `load_routing_config` không ném, sai dạng -> `{}`; (3) `validate_routing_config` nêu đường dẫn khóa sai, kiểm User khi khác rỗng, không chặn tài khoản agent, không kiểm nhóm tồn tại; (4) mỗi ca trong test có thật sự đỏ nếu bộ kiểm bỏ nhánh tương ứng (STD-TEST-8).
Bằng chứng dev: RED 4 lỗi AttributeError; GREEN test_routing 28 OK; `cmd.test` nền 703 OK, sau thay đổi 707 OK; lint pass.
