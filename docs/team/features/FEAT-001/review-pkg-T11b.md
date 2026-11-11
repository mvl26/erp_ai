# Review package FEAT-001 T11b (BASE 7415abd..4f302e2, branch team/FEAT-001-task-11b)

Diff command: `git diff 7415abd..team/FEAT-001-task-11b`

Commits:
- 4f302e2 feat(hooks): allow deleting HD Ticket that has ERP AI Log rows (FEAT-001)

Stat: erp_ai/hooks.py (+3), erp_ai/tests/test_ticket_delete.py (+40, new)

## Diff

```diff
diff --git a/erp_ai/hooks.py b/erp_ai/hooks.py
@@ -144,6 +144,9 @@ doc_events = {
 	},
 }
 
+# Deleting a ticket must not be blocked by its audit-log rows (the log is kept)
+ignore_links_on_delete = ["ERP AI Log"]
+
 # Scheduled Tasks
 # ---------------
 
diff --git a/erp_ai/tests/test_ticket_delete.py b/erp_ai/tests/test_ticket_delete.py
new file mode 100644
+import frappe
+from frappe.tests.utils import FrappeTestCase
+from helpdesk.test_utils import make_ticket
+
+from erp_ai.constants import LOG_DOCTYPE
+
+
+class TestTicketDeleteKeepsLog(FrappeTestCase):
+	def setUp(self):
+		# FrappeTestCase rolls back only after the whole class: undo each test.
+		self.addCleanup(frappe.db.rollback)
+		self.addCleanup(frappe.set_user, "Administrator")
+		frappe.set_user("Administrator")
+
+	def _ticket_with_log(self):
+		ticket = make_ticket(subject="T11b delete ticket")
+		log = frappe.get_doc(
+			{
+				"doctype": LOG_DOCTYPE,
+				"ticket": ticket.name,
+				"run_id": "t11b",
+				"entry_type": "classify",
+				"turn": 0,
+			}
+		).insert(ignore_permissions=True)
+		return ticket, log
+
+	def test_ticket_with_log_can_be_deleted_and_log_survives(self):
+		ticket, log = self._ticket_with_log()
+
+		frappe.delete_doc("HD Ticket", ticket.name, force=False)
+
+		self.assertFalse(frappe.db.exists("HD Ticket", ticket.name))
+		self.assertTrue(frappe.db.exists(LOG_DOCTYPE, log.name))
+		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, log.name, "ticket"), ticket.name)
+
+	def test_log_doctype_still_has_no_delete_permission(self):
+		for perm in frappe.get_meta(LOG_DOCTYPE).permissions:
+			with self.subTest(role=perm.role):
+				self.assertFalse(perm.get("delete"))
```
