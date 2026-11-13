import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr

# Design 2.1 content group (ADR-012 QĐ 1): written once at insert, never changed afterwards.
CONTENT_FIELDS = (
	"ticket",
	"run_id",
	"instructor",
	"change_kind",
	"app",
	"file_path",
	"is_new_file",
	"command_args",
	"base_hash",
	"content_before",
	"content_after",
	"after_hash",
	"diff",
	"reason",
	"reversible",
	"target_branch",
	"upstream_ref",
	"ahead_count",
	"is_core_app",
	"commit_message",
)
NUMERIC_CONTENT_FIELDS = ("is_new_file", "reversible", "ahead_count", "is_core_app")


def _stored_form(fieldname: str, value):
	"""Compare as the database stores the value: integers for Check/Int, text otherwise (None is "")."""
	if fieldname in NUMERIC_CONTENT_FIELDS:
		return cint(value)
	return cstr(value)


class ERPAIChangeProposal(Document):
	def validate(self):
		if self.is_new():
			return
		before = frappe.db.get_value(self.doctype, self.name, CONTENT_FIELDS, as_dict=True)
		changed = [
			fieldname
			for fieldname in CONTENT_FIELDS
			if _stored_form(fieldname, self.get(fieldname)) != _stored_form(fieldname, before.get(fieldname))
		]
		if changed:
			frappe.throw(
				_("Nội dung đề xuất không sửa được sau khi tạo: {0}").format(", ".join(changed)),
				frappe.ValidationError,
			)
