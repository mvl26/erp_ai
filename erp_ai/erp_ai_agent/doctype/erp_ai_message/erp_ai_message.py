import frappe
from frappe import _
from frappe.model.document import Document


class ERPAIMessage(Document):
	# A message is a record of what was said; it is written once and never changed.
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Tin trao đổi với bot không sửa được."))
