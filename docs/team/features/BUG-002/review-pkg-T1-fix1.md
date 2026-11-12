# Review package BUG-002 T1 — rework round 1 (scoped re-review)

Commands: `git log --oneline c004ee8..team/BUG-002-task-1b`; `git diff c004ee8..team/BUG-002-task-1b` (FIX_BASE=c004ee8). Full task diff: `git diff b8f9485..team/BUG-002-task-1b`.

Findings to mark ADDRESSED / NOT ADDRESSED:
1. major STD-TEST-6: setUp did not neutralize permission-record rows (`modified_by=AGENT_USER`, tasks.PERMISSION_DOCTYPES) nor enabled Server Script/Webhook rows (`owner=AGENT_USER`).
2. minor STD-STYLE-5/STD-TEST-8: dead `if not exists` guards; no test kept an automatic-role row.

Output pasted by dev: new test red when the helper is a no-op (`Called 2 times`, 34 tests, failures=1), green with it: `Ran 34 tests ... OK`.

```
fd9fbf4 fix(tests): neutralize live agent-attributed rows in privilege-escalation tests (BUG-002)
```

```diff
@@ setUp
 		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
 			self._add_role(role)
+		self._neutralize_agent_rows()
+
+	def _neutralize_agent_rows(self):
+		for doctype in tasks.PERMISSION_DOCTYPES:
+			if frappe.db.exists("DocType", doctype):
+				frappe.db.set_value(doctype, {"modified_by": AGENT_USER}, "modified_by", "Administrator", update_modified=False)
+		frappe.db.set_value("Server Script", {"owner": AGENT_USER}, "disabled", 1)
+		frappe.db.set_value("Webhook", {"owner": AGENT_USER}, "enabled", 0)
@@ test_allowed_roles_do_not_alarm
-		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
-			if not frappe.db.exists("Has Role", {"parent": AGENT_USER, "role": role}):
-				self._add_role(role)
+		self._add_role("Desk User")
@@ test_alarm_when_agent_lost_a_required_role
-		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
-			if not frappe.db.exists("Has Role", {"parent": AGENT_USER, "role": role}):
-				self._add_role(role)
 		frappe.db.delete("Has Role", {"parent": AGENT_USER, "role": ROLE_AGENT})
+	def test_setup_neutralizes_live_rows_attributed_to_agent(self):
+		self._add_perm(AGENT_USER)
+		self._add_server_script(AGENT_USER, disabled=0)
+		self._add_webhook(AGENT_USER, enabled=1)
+		self._neutralize_agent_rows()
+		self._run()
+		self.send_alarm.assert_not_called()
```
(Abridged; the authoritative diff is the git command above.)
