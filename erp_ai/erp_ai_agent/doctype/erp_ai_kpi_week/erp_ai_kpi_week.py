from frappe.model.document import Document
from frappe.utils import getdate

from erp_ai.agent.agent_write_guard import refuse_agent_write


class ERPAIKPIWeek(Document):
	# The name is the cycle key of ADR-033 QĐ 6: a second row for the same week is a DuplicateEntryError.
	def autoname(self):
		self.name = f"KPI-{getdate(self.week_start).isoformat()}"

	# Only the scheduled job (Administrator) writes this row; the agent account never does (ADR-023 QĐ 5).
	def before_insert(self):
		refuse_agent_write(self)

	def validate(self):
		refuse_agent_write(self)

	def on_trash(self):
		refuse_agent_write(self)

	def before_rename(self, old, new, merge=False):
		refuse_agent_write(self)
