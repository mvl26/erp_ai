# FEAT-006 Checkpoint C5 (dev)

Nhánh: `team/FEAT-006-c5` từ `team/FEAT-006` (đầu c470381). Không sửa mã, không commit mã. Site miyano, chạy tuần tự.
Tài khoản agent: `constants.AGENT_USER = "ai.agent@miyano.com.vn"`.

## Đếm Has Role TRƯỚC (đọc-only)
```
$ echo 'SELECT COUNT(*) AS has_role_before FROM `tabHas Role` WHERE parent="ai.agent@miyano.com.vn" AND parenttype="User";' | bench --site miyano mariadb
has_role_before
99
```

## 1. cmd.test toàn app
```
$ cd /home/miyano/frappe-bench && PYTHONPATH=<worktree> bench --site miyano run-tests --app erp_ai
exit=0
----------------------------------------------------------------------
Ran 880 tests in 159.797s

OK
```
(Dòng "ERROR CSSStyleDeclaration: Syntax Error in Property: box-shadow" là log của thư viện CSS khi render in, không phải lỗi test.)

## Has Role SAU bộ test
```
has_role_after_tests
99
```

## 2. pre-commit run --all-files
```
trim trailing whitespace.................................................Passed
check for merge conflicts................................................Passed
check python ast.........................................................Passed
check json...............................................................Passed
check toml...............................................................Passed
check yaml...............................................................Passed
debug statements (python)................................................Passed
Run ruff import sorter...................................................Passed
Run ruff linter..........................................................Passed
Run ruff formatter.......................................................Passed
prettier.................................................................Passed
eslint...................................................................Passed
exit=0
```
Không hook nào tự sửa file; `git status --short` rỗng.

## 3. migrate
```
$ PYTHONPATH=<worktree> bench --site miyano migrate
exit=0
[AssetCore] Core DocPerm: 0 insert, 0 update, 926 skip (0 DocType bỏ qua, 0 role bỏ qua).
[AssetCore] Notifications: 7 rule(s) đã sync.
[AssetCore] ac_caps::* busted (cap-set v105.b50a24e5f62f)
[AssetCore] prune_orphan_link_customfields: đã gỡ 0 orphan Custom Field.
[AssetCore FE] dist đã có, bỏ qua build (after_migrate).
  Dọn role: skip: User 'cr73_alloc_tech@example.invalid' — còn liên kết với IMM Audit Trail IMM-AUD-2026-0025509
  Dọn role: skip: Role 'Internal Auditor' — còn liên kết với Workflow Action i5ql894mec
  Dọn role: skip: 1 Contact của user test còn liên kết (vd. John Doe)
RBAC sync tắt (mvl_rbac_enabled chưa bật)

Queued rebuilding of search index for miyano
```
Has Role SAU migrate:
```
has_role_after_migrate
99
```

## So sánh Has Role
TRƯỚC = 99; SAU migrate = 99; SAU bộ test = 99. Bằng nhau (không rò role). Thứ tự thực hiện: đếm trước, test, đếm, pre-commit, migrate, đếm.

## 4. grep response_by|resolution_by trong erp_ai/agent/
```
$ grep -rnE "response_by|resolution_by" erp_ai/agent/
erp_ai/agent/tools/test_route_ticket.py:304:		return frappe.db.get_value("HD Ticket", ticket, ["sla", "response_by", "resolution_by"], as_dict=True)
erp_ai/agent/tools/test_registry.py:28:	"resolution_by",
erp_ai/agent/test_runner_routing.py:1336:		return tuple(frappe.db.get_value("HD Ticket", ticket, ["response_by", "resolution_by"]))
erp_ai/agent/tools/test_route_ticket.py:321:			self.assertIsNotNone(row.response_by)
erp_ai/agent/tools/test_route_ticket.py:322:			self.assertIsNotNone(row.resolution_by)
```
Phép gán: KHÔNG có. Cả 5 hit đều nằm trong test_*.py: 304 và 1336 là đọc (get_value), 321/322 là assertIsNotNone, test_registry.py:28 là phần tử trong danh sách tên trường (chuỗi). Không có hit ở mã nguồn không-test. (Tech-lead kiểm lại bằng `git grep` trên team/FEAT-006: đúng 5 hit này.)

## 5. grep resolve_ticket_values|ROUTING_TABLE trong erp_ai/
```
$ grep -rn "resolve_ticket_values\|ROUTING_TABLE" erp_ai/
(rỗng)
exit=1
```
(Tech-lead kiểm lại bằng `git grep` trên team/FEAT-006: rỗng.)
