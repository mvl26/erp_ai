from frappe.model.document import Document

from erp_ai.agent.agent_write_guard import refuse_agent_write


class ERPAICredential(Document):
	# No valid write path for the agent account (ADR-023 QĐ 5).
	def before_insert(self):
		refuse_agent_write(self)

	def validate(self):
		refuse_agent_write(self)

	def on_trash(self):
		refuse_agent_write(self)

	def before_rename(self, old, new, merge=False):
		refuse_agent_write(self)

	def before_submit(self):
		refuse_agent_write(self)

	def before_cancel(self):
		refuse_agent_write(self)
