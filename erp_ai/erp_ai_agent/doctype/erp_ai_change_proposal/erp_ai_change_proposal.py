import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, get_datetime, get_system_timezone, now_datetime

from erp_ai.agent import change_text, policy, queue
from erp_ai.agent.agent_write_guard import refuse_agent_write
from erp_ai.agent.authority import NEVER_AUTHORITY
from erp_ai.agent.changes import block, restart_check, result_comment, transitions
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_STATUS_PENDING,
	OPERATION_DOCTYPE,
	PANEL_MAX_PROPOSALS,
	PROPOSAL_DOCTYPE,
	RESTART_STATUS_SENT,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
)

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


# CHG-008 design 3.2 lines 4-6: why the ticket panel shows no Duyệt / Từ chối buttons (or why the POST is refused).
PANEL_REFUSALS = {
	"role": "Chỉ người có vai trò ERP AI Instructor mới duyệt hoặc từ chối được.",
	"not_pending": "Đề xuất không còn chờ duyệt.",
	"switch_off": "Duyệt một lần bấm đang tắt; hãy duyệt ở form đề xuất.",
}


def has_decider_role(user: str) -> bool:
	"""The one place `ROLE_INSTRUCTOR` is compared: `user` holds it and is not an account of `NEVER_AUTHORITY`.

	The role is read with `frappe.get_roles`, never `is_instruction`: the agent account is refused even with it.
	Not whitelisted.
	"""
	return user not in NEVER_AUTHORITY and ROLE_INSTRUCTOR in frappe.get_roles(user)


def panel_decision_refusal(status: str) -> str | None:
	"""Why the session user cannot decide a proposal in `status` from the ticket panel, or None when they can.

	Checked in this order: role, then pending, then switch (5). The switch is read through
	`policy.permission_switches` on every call and only when the first two checks pass. Not whitelisted.

	Returns:
		A key of `PANEL_REFUSALS`, or None.
	"""
	if not has_decider_role(frappe.session.user):
		return "role"
	if status != CHANGE_STATUS_PENDING:
		return "not_pending"
	if not policy.permission_switches(frappe.get_single(SETTING_DOCTYPE)).one_click_approval:
		return "switch_off"
	return None


def proposal_head(name) -> frappe._dict:
	"""`{"ticket", "change_status"}` of proposal `name`, read from the stored record. Not whitelisted.

	Raises:
		frappe.DoesNotExistError: `name` is not a string, is empty, or names no proposal (the text of `_decider`).
	"""
	head = None
	if isinstance(name, str) and name.strip():
		head = frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["ticket", "change_status"], as_dict=True)
	if not head:
		frappe.throw(
			_("Không có đề xuất {0}").format(frappe.utils.escape_html(cstr(name))),
			frappe.DoesNotExistError,
		)
	return frappe._dict(ticket=head.ticket, change_status=head.change_status)


# CHG-008 design 2, 3.1: what a panel card reads and shows. No content field is ever read (diff, file text,
# command args and output, commit message, reason, digest, created dirs), so a card cannot show one.
CARD_FIELDS = (
	"name",
	"change_kind",
	"is_new_file",
	"file_path",
	"app",
	"command_list",
	"change_status",
	"restart_status",
	"restart_sent_at",
	"decided_by",
	"failure_reason",
	"target_branch",
	"upstream_ref",
	"ahead_count",
	"is_core_app",
	"apply_commit_sha",
	"undo_commit_sha",
)
CARD_OPERATION_FIELDS = ("parent", "idx", "operation", "file_path", "new_path")
CARD_KEYS = (
	"name",
	"target",
	"notes",
	"status",
	"restart_status",
	"decided_by",
	"failure_reason",
	"can_decide",
	"can_open",
)


def _card_notes(proposal_name: str, fields) -> list[str]:
	"""`change_text.proposal_notes`, or the one warning line when the stored content is unreadable (D-6)."""
	try:
		return change_text.proposal_notes(fields)
	except ValueError as exc:
		frappe.logger("erp_ai").warning(
			"erp_ai notes proposal=%s error=%s", proposal_name, type(exc).__name__
		)
		return [UNREADABLE_NOTES]


def panel_cards(ticket: str) -> list[dict]:
	"""One card per change proposal attached to `ticket`, newest first, at most `PANEL_MAX_PROPOSALS`.

	Reads only `CARD_FIELDS` and `CARD_OPERATION_FIELDS` and writes nothing. It checks no gate: the only
	caller is `ticket_panel.get_panel_data`, after its gate. A proposal without a ticket has no card.
	`can_decide` reads the one-click switch again on every call (no cache); `can_open` is the viewer's read
	permission on the proposal doctype and on that proposal. Not whitelisted.

	Returns:
		list of dicts with exactly the keys of `CARD_KEYS`; every value is plain text, a bool or None.
	"""
	if not ticket:
		return []
	rows = frappe.get_all(
		PROPOSAL_DOCTYPE,
		filters={"ticket": ticket},
		fields=list(CARD_FIELDS),
		order_by="creation desc, name desc",
		limit_page_length=PANEL_MAX_PROPOSALS,
	)
	if not rows:
		return []
	by_parent: dict[str, list] = {}
	operations = frappe.get_all(
		OPERATION_DOCTYPE,
		filters={"parenttype": PROPOSAL_DOCTYPE, "parent": ("in", [row.name for row in rows])},
		fields=list(CARD_OPERATION_FIELDS),
		order_by="idx asc",
	)
	for operation in operations:
		by_parent.setdefault(operation.parent, []).append(operation)
	# CHG-008 ruling: per-document read through one get_list that reads only `name`, so no card loads the forbidden
	# fields (`has_permission(..., doc=name)` would load the whole document); role, user permissions and shares apply.
	readable = set()
	if frappe.has_permission(PROPOSAL_DOCTYPE, "read") and rows:
		readable = set(
			frappe.get_list(
				PROPOSAL_DOCTYPE,
				filters={"name": ("in", [row.name for row in rows])},
				pluck="name",
				limit_page_length=0,
			)
		)
	cards = []
	for row in rows:
		fields = frappe._dict(row, operations=by_parent.get(row.name, []))
		decided_by = cstr(row.decided_by)
		failure_reason = result_comment.masked_reason(row.failure_reason)
		# values in the order of CARD_KEYS; not a dict literal, which the state-field rule of ADR-012 reads as a write
		values = (
			row.name,
			change_text.proposal_target_text(fields),
			_card_notes(row.name, fields),
			row.change_status,
			row.restart_status or None,
			change_text.safe_person_name(frappe.utils.get_fullname(decided_by)) if decided_by else None,
			failure_reason or None,
			panel_decision_refusal(row.change_status) is None,
			row.name in readable,
		)
		cards.append(dict(zip(CARD_KEYS, values, strict=True)))
	return cards


def _decider(name) -> str:
	"""Design 3.3/4.2 boundary: the session user holds `ERP AI Instructor`, then `name` is an existing proposal.

	`name` has no type annotation on the three methods on purpose: Frappe would refuse a non-string with its
	own type error before this check, and design 3.3 answers it with `DoesNotExistError` instead.
	Returns the session user. The role is read with `frappe.get_roles`, never `is_instruction`: an assigned
	user without the role is refused, and the accounts of `NEVER_AUTHORITY` are refused even with it.
	"""
	user = frappe.session.user
	if not has_decider_role(user):
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
