import frappe
from frappe.model.document import Document

from erp_ai.agent import lessons
from erp_ai.agent.agent_write_guard import refuse_agent_write

STORE_ONLY_MESSAGE = "Bài học chỉ đổi được qua nút trên form"
NO_DELETE_MESSAGE = "Không xóa bài học; hãy tắt bài"


class ERPAILesson(Document):
	# Only the lesson store writes this row (ADR-045): it sets the flag on the parent, so its history rows pass too.
	def before_insert(self):
		refuse_agent_write(self)

	def validate(self):
		refuse_agent_write(self)
		if not self.flags.erp_ai_lesson_store:
			frappe.throw(STORE_ONLY_MESSAGE)

	def on_trash(self):
		refuse_agent_write(self)
		frappe.throw(NO_DELETE_MESSAGE)

	def before_rename(self, old, new, merge=False):
		refuse_agent_write(self)


@frappe.whitelist(methods=["POST"])
def teach(rule=None, situation=None) -> dict:
	"""Teach the bot a rule from the list (AC-8); the lesson is active at once."""
	return {"name": lessons.teach(rule, situation or "")}


@frappe.whitelist(methods=["POST"])
def decide(name=None, action=None) -> dict:
	"""Approve, reject, disable or enable a lesson from its form; returns the new status."""
	return {"status": lessons.transition(name, action)}
