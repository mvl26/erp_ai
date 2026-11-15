import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, get_datetime, get_system_timezone, now_datetime

from erp_ai.agent import change_text, queue
from erp_ai.agent.agent_write_guard import refuse_agent_write
from erp_ai.agent.authority import NEVER_AUTHORITY
from erp_ai.agent.changes import block, restart_check, transitions
from erp_ai.constants import CHANGE_KIND_CODE, PROPOSAL_DOCTYPE, RESTART_STATUS_SENT, ROLE_INSTRUCTOR

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
	"command_list",
)
# CHG-002 design 2.1: the 7 fields of an `ERP AI Change Operation` row, content like the fields above.
OPERATION_ROW_FIELDS = (
	"operation",
	"file_path",
	"new_path",
	"content_before",
	"content_after",
	"base_hash",
	"after_hash",
)
UNREADABLE_NOTES = (
	"Không đọc được nội dung đã lưu của đề xuất này (dữ liệu hỏng); báo quản trị trước khi duyệt."
)
NUMERIC_CONTENT_FIELDS = ("is_new_file", "reversible", "ahead_count", "is_core_app")


def _stored_form(fieldname: str, value):
	"""Compare as the database stores the value: integers for Check/Int, text otherwise (None is "")."""
	if fieldname in NUMERIC_CONTENT_FIELDS:
		return cint(value)
	return cstr(value)


def _operation_rows(doc) -> list[tuple[str, ...]]:
	"""The child rows in stored order (`idx`), each as the text of its 7 content fields."""
	rows = sorted(doc.get("operations") or (), key=lambda row: cint(row.idx))
	return [tuple(cstr(row.get(fieldname)) for fieldname in OPERATION_ROW_FIELDS) for row in rows]


class ERPAIChangeProposal(Document):
	"""M5 (ADR-023 QĐ 5): the agent account writes a proposal only inside `propose_change._insert`."""

	def before_insert(self):
		refuse_agent_write(self)
		transitions.prepare_new(self)

	def onload(self):
		"""Design 3.3 form data: the 3.9 sentences, built only from the stored fields (no git).

		Unreadable stored content still opens the form, with one warning line (CHG-002 addendum-5 P-5).
		"""
		try:
			notes = change_text.proposal_notes(self)
		except ValueError as exc:
			frappe.logger("erp_ai").warning(
				"erp_ai notes proposal=%s error=%s", self.name, type(exc).__name__
			)
			notes = [UNREADABLE_NOTES]
		self.set_onload("change_notes", notes)

	def on_trash(self):
		refuse_agent_write(self)

	def before_rename(self, old, new, merge=False):
		refuse_agent_write(self)

	def validate(self):
		refuse_agent_write(self)
		if self.is_new():
			self._set_commit_message()
			return
		before = frappe.db.get_value(self.doctype, self.name, CONTENT_FIELDS, as_dict=True)
		changed = [
			fieldname
			for fieldname in CONTENT_FIELDS
			if _stored_form(fieldname, self.get(fieldname)) != _stored_form(fieldname, before.get(fieldname))
		]
		if _operation_rows(self) != _operation_rows(self.get_doc_before_save()):
			changed.append("operations")
		if changed:
			frappe.throw(
				_("Nội dung đề xuất không sửa được sau khi tạo: {0}").format(", ".join(changed)),
				frappe.ValidationError,
			)

	def _set_commit_message(self):
		"""D-14: the apply-commit preview (design 3.9), replacing whatever the caller passed.

		Runs in `validate` at insert, once Frappe has named the proposal; a bench command has no commit.
		"""
		if self.change_kind != CHANGE_KIND_CODE:
			self.commit_message = None
			return
		label, operations = cstr(self.file_path), None
		if block.is_block(self):
			# CHG-002 design 3.7: a block is labelled by its items and lists one line per item.
			operations = block.operations_of(self)
			label = change_text.block_label(operations)
		subject, body = change_text.apply_message(
			self.name, cstr(self.ticket), label, change_text.APPROVER_PLACEHOLDER, operations=operations
		)
		self.commit_message = change_text.message_text(subject, body)


def _decider(name) -> str:
	"""Design 3.3/4.2 boundary: the session user holds `ERP AI Instructor`, then `name` is an existing proposal.

	`name` has no type annotation on the three methods on purpose: Frappe would refuse a non-string with its
	own type error before this check, and design 3.3 answers it with `DoesNotExistError` instead.
	Returns the session user. The role is read with `frappe.get_roles`, never `is_instruction`: an assigned
	user without the role is refused, and the accounts of `NEVER_AUTHORITY` are refused even with it.
	"""
	user = frappe.session.user
	if user in NEVER_AUTHORITY or ROLE_INSTRUCTOR not in frappe.get_roles(user):
		frappe.throw(
			_("Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được"),
			frappe.PermissionError,
		)
	if not isinstance(name, str) or not name.strip() or not frappe.db.exists(PROPOSAL_DOCTYPE, name):
		frappe.throw(
			_("Không có đề xuất {0}").format(frappe.utils.escape_html(cstr(name))),
			frappe.DoesNotExistError,
		)
	return user


@frappe.whitelist(methods=["POST"])
def approve(name=None) -> dict:
	"""`Chờ duyệt → Đã duyệt`, then queue the `apply` job (design 3.3, ADR-012 QĐ 4)."""
	user = _decider(name)
	status = transitions.approve(name, user)
	queue.enqueue_change_job(name, "apply")
	return {"name": name, "status": status}


@frappe.whitelist(methods=["POST"])
def reject(name=None) -> dict:
	"""`Chờ duyệt → Đã từ chối`; no job (design 3.3)."""
	user = _decider(name)
	return {"name": name, "status": transitions.reject(name, user)}


@frappe.whitelist(methods=["POST"])
def undo(name=None) -> dict:
	"""`Đã áp dụng → Đang hoàn tác` for a code change, then queue the `undo` job (design 3.3)."""
	user = _decider(name)
	status = transitions.request_undo(name, user)
	queue.enqueue_change_job(name, "undo")
	return {"name": name, "status": status}


@frappe.whitelist(methods=["POST"])
def confirm_restart(name=None) -> dict:
	"""`restart_status`: `Đã gửi → Đã xác nhận / Chưa xác nhận` from lazy evidence (design 3.3, 4.4 step 5).

	Writes only when the stored status is `Đã gửi` and `restart_check.outcome` concludes; the conclusion is
	written against the very `restart_sent_at` the evidence was measured from (addendum-5 P-4), so a send
	recorded in between wins and its status is returned.
	"""
	_decider(name)
	stored = frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["restart_status", "restart_sent_at"], as_dict=True)
	# `get_datetime(None)` is "now": a send without its moment has nothing to measure against.
	if stored.restart_status != RESTART_STATUS_SENT or not stored.restart_sent_at:
		return {"name": name, "status": stored.restart_status}
	timezone = get_system_timezone()
	value = restart_check.outcome(
		restart_check.epoch_of_system_time(get_datetime(stored.restart_sent_at), timezone),
		restart_check.epoch_of_system_time(now_datetime(), timezone),
		restart_check.web_started(),
		restart_check.workers_started(),
	)
	if value is None:
		return {"name": name, "status": stored.restart_status}
	if not transitions.confirm_restart(name, value, sent_at=stored.restart_sent_at):
		return {"name": name, "status": frappe.db.get_value(PROPOSAL_DOCTYPE, name, "restart_status")}
	frappe.logger("erp_ai").info("erp_ai restart proposal=%s status=%s", name, value)
	return {"name": name, "status": value}
