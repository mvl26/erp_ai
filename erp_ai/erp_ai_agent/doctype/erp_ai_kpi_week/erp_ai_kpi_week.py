from frappe.model.document import Document
from frappe.utils import getdate


class ERPAIKPIWeek(Document):
	# The name is the cycle key of ADR-033 QĐ 6: a second row for the same week is a DuplicateEntryError.
	def autoname(self):
		self.name = f"KPI-{getdate(self.week_start).isoformat()}"
