# Review package BUG-002 T2

Commands: `git log --oneline f433fe9..team/BUG-002-task-2`; `git diff f433fe9..team/BUG-002-task-2`

Criteria (tasks.md T2, intake.md): test_erp_ai_accuracy.py (13 tests) passes regardless of live ERP AI Log rows, each test's meaning kept, no weakening/skip/xfail/deleted assertion, no product code change, no commit/DDL, rolled back with the test transaction; only the touchpoint file edited.

```
2ed354c fix(tests): isolate accuracy report tests from live ERP AI Log rows (BUG-002)
 erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py | 3 +++
```

```diff
@@ AccuracyTestCase.setUp
 		frappe.set_user("Administrator")
+		# Rows from real use of the site must not reach the report: hide every existing prediction
+		# inside this transaction (rolled back in cleanup), so the rows made by the test are the only ones.
+		frappe.db.sql(f"update `tab{LOG_DOCTYPE}` set entry_type = 'reason' where entry_type = 'classify'")
 		self.now = now_datetime().replace(microsecond=0)
```

Dev evidence: RED `Ran 13 tests ... FAILED (failures=4)` (e.g. `Lists differ: [{'category': 'A', 'predictions': 0, ...}] != []`, `2 != 1`); GREEN `Ran 13 tests in 0.410s ... OK`.
