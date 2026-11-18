import frappe
from frappe import _
from frappe.model.document import Document

from erp_ai.agent import authority


class ERPAIMessage(Document):
	def before_insert(self):
		# BUG-009: the role the owner (the session user, set before this hook) holds as the message is sent; written
		# here so every insert path stores it and no client value is kept
		self.author_role = authority.role_label(self.owner, self.ticket)

	# A message is a record of what was said; it is written once and never changed.
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Tin trao đổi với bot không sửa được."))
