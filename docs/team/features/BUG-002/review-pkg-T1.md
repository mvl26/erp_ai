# Review package BUG-002 T1

Commands: `git log --oneline b8f9485..team/BUG-002-task-1`; `git diff b8f9485228d2a8d2873e58bdac329b429e5a43b1..team/BUG-002-task-1`

Task criteria (tasks.md T1): test_tasks.TestCheckPrivilegeEscalation tự dựng trạng thái (Has Role của agent đặt về tập cho phép trong transaction test; rollback), giữ nguyên ý nghĩa từng test; không weakening/skip/xfail/xóa assertion; không đổi mã sản phẩm; chỉ sửa erp_ai/tests/test_tasks.py; không commit/DDL trong test.

```
c004ee8 fix(tests): isolate privilege-escalation tests from live agent roles (BUG-002)

 erp_ai/tests/test_tasks.py | 5 +++++
 1 file changed, 5 insertions(+)
```

```diff
diff --git a/erp_ai/tests/test_tasks.py b/erp_ai/tests/test_tasks.py
index 9f1419f..b14f6d5 100644
--- a/erp_ai/tests/test_tasks.py
+++ b/erp_ai/tests/test_tasks.py
@@ -183,6 +183,11 @@ class TestCheckPrivilegeEscalation(FrappeTestCase):
 		self.addCleanup(self.send_alarm_patch.stop)
 		# Keys already on the site must not influence the key condition.
 		frappe.db.set_value(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE}, "enabled", 0)
+		# The agent's real roles on the site must not influence the role condition: start from
+		# exactly the allowed set (rolled back with the test transaction).
+		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User"})
+		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
+			self._add_role(role)
 
 	def _run(self):
 		tasks.check_privilege_escalation()
```
