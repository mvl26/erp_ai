from frappe.model.document import Document


class ERPAIChangeOperation(Document):
	"""One file item of a block proposal (CHG-002 design 2.1); written once with its parent, never alone."""
