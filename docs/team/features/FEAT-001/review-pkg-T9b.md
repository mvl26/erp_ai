# Review package FEAT-001 T9b

BASE=06f83c8 .. team/FEAT-001-task-9b head ef4f106

Commits:
- ef4f106 fix(agent): use Float precision 6 for USD budget fields (FEAT-001)

Stat: 4 files changed, 18 insertions(+), 4 deletions(-)
Command: `git diff 06f83c8..team/FEAT-001-task-9b`

Decision D6 (supersedes design.md money fieldtypes): USD money fields are Float precision 6 with "(USD)" in the label, never Currency (site miyano shows Currency in VND).
Decision D4 (supersedes design.md 3.5 and 5.4): git_source is log/blame only.

```diff
--- erp_ai_credential.json
 "fieldname": "budget_month_usd",
-"fieldtype": "Currency",
-"label": "Ngân sách tháng (USD)"
+"fieldtype": "Float",
+"label": "Ngân sách tháng (USD)",
+"precision": "6"
--- test_erp_ai_credential.py
+	def test_budget_month_is_float_precision_6_usd(self):
+		field = self.meta.get_field("budget_month_usd")
+		self.assertEqual(field.fieldtype, "Float")
+		self.assertEqual(str(field.precision), "6")
+		self.assertIn("(USD)", field.label)
--- erp_ai_setting.json
 "fieldname": "monthly_budget_usd",
-"fieldtype": "Currency",
+"fieldtype": "Float",
 "label": "Ngân sách tháng (USD)",
-"default": "10"
+"default": "10",
+"precision": "6"
--- test_erp_ai_setting.py
+	def test_monthly_budget_is_float_precision_6_usd(self):
+		field = frappe.get_meta(SETTING_DOCTYPE).get_field("monthly_budget_usd")
+		(same three assertions)
```
Full diff: run the command above (the 4 files are exactly the touchpoints).
