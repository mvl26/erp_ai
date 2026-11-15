"""Ticket lifecycle (FEAT-007 U6b, ADR-033): the N-2 status changes that need no model.

Agent core: never imports the model gateway, the tools or the runner (ADR-033 QĐ 3, Ràng buộc 4); it reads
the lifecycle switches and the origin field itself (`lifecycle_settings`) and never writes ERP AI Setting.
"""

from dataclasses import dataclass

import frappe

from erp_ai.agent import policy
from erp_ai.constants import SETTING_DOCTYPE

STATUS_RESOLVED = "Resolved"
STATUS_CLOSED = "Closed"
RESOLVED_CATEGORY = "Resolved"
TASK_COMPLETED = "Completed"
TASK_CANCELLED = "Cancelled"
CATEGORY_E = "E"
CATEGORY_F = "F"
TOOL_RESOLVE_ON_TASKS_DONE = "resolve_on_tasks_done"
TOOL_CLOSE_SILENT_F = "close_silent_f"
TOOL_LIFECYCLE_COMMENT = "lifecycle_comment"
TOOL_REQUESTER_NOTICE = "requester_notice"
TOOL_LIFECYCLE_CONFIG = "ticket_lifecycle"
REASON_ORIGIN_NOT_CONFIGURED = "chưa cấu hình trường Nguồn phát sinh (field_origin, origin_board_value)"
TITLE_LIFECYCLE_FAILED = "ERP AI lifecycle failed"
COMMENT_RESOLVED = "ERP AI: mọi Task liên kết đã xong ({completed} Completed), phiếu chuyển Resolved."
COMMENT_SILENT_CLOSED = "ERP AI: người tạo chưa phản hồi {days} ngày sau tin của bot, phiếu chuyển Closed."
NOTICE_SILENT_CLOSE = (
	"Phiếu #{ticket} được đóng vì chưa nhận được phản hồi sau {days} ngày. "
	"Nếu vấn đề còn, anh/chị trả lời tin này để mở lại."
)

TICKET_DOCTYPE = "HD Ticket"
# Refusal codes of status_change_refusal, in the order they are checked (AC-42 (b), (c); A-U6b-5).
REFUSAL_ORIGIN_NOT_CONFIGURED = "origin_not_configured"
REFUSAL_NOT_SENDABLE = "not_sendable"
REFUSAL_BOARD_DIRECTED = "board_directed"
REFUSAL_CATEGORY_E = "category_e"
# ERP AI Setting `close_silent_f_days` (Int 3, 1..30); anything else reads the default.
CLOSE_SILENT_F_DAYS_DEFAULT = 3
CLOSE_SILENT_F_DAYS_MIN = 1
CLOSE_SILENT_F_DAYS_MAX = 30


@dataclass(frozen=True)
class LifecycleSettings:
	reply: bool
	resolve_on_tasks_done: bool
	close_silent_f: bool
	close_silent_f_days: int
	kb_draft: bool
	field_origin: str
	origin_board_value: str


def _days(value) -> int:
	try:
		days = int(value)
	except (TypeError, ValueError):
		return CLOSE_SILENT_F_DAYS_DEFAULT
	return days if CLOSE_SILENT_F_DAYS_MIN <= days <= CLOSE_SILENT_F_DAYS_MAX else CLOSE_SILENT_F_DAYS_DEFAULT


def _text(value) -> str:
	return (value or "").strip()


def lifecycle_settings(settings) -> LifecycleSettings:
	"""The only reader of the seven lifecycle fields of ERP AI Setting; a missing field reads off / blank."""
	return LifecycleSettings(
		reply=bool(getattr(settings, "reply_enabled", 0)),
		resolve_on_tasks_done=bool(getattr(settings, "resolve_on_tasks_done_enabled", 0)),
		close_silent_f=bool(getattr(settings, "close_silent_f_enabled", 0)),
		close_silent_f_days=_days(getattr(settings, "close_silent_f_days", None)),
		kb_draft=bool(getattr(settings, "kb_draft_enabled", 0)),
		field_origin=_text(getattr(settings, "field_origin", None)),
		origin_board_value=_text(getattr(settings, "origin_board_value", None)),
	)


def kb_draft_enabled() -> bool:
	"""The knowledge-draft switch in one read, for the handler."""
	return bool(frappe.db.get_single_value(SETTING_DOCTYPE, "kb_draft_enabled"))


def origin_configured(ls: LifecycleSettings) -> bool:
	"""Both origin settings set and `field_origin` a field of HD Ticket; anything else is False (fail-closed, AC-42 (c))."""
	return bool(
		ls.field_origin
		and ls.origin_board_value
		and frappe.get_meta(TICKET_DOCTYPE).has_field(ls.field_origin)
	)


def _normalize(value) -> str:
	return str(value or "").strip().casefold()


def status_change_refusal(ticket_name: str, ls: LifecycleSettings) -> str | None:
	"""The one guard of both N-2 status changes (AC-42 (b)): why the bot must not change this ticket's status, or None.

	First match wins: origin not configured, not sendable (excluded ticket, A-U6b-5), board-directed origin
	(compared after strip and casefold), latest category E.
	"""
	if not origin_configured(ls):
		return REFUSAL_ORIGIN_NOT_CONFIGURED
	if not policy.can_send_ticket(ticket_name):
		return REFUSAL_NOT_SENDABLE
	origin = frappe.db.get_value(TICKET_DOCTYPE, ticket_name, ls.field_origin)
	if _normalize(origin) == _normalize(ls.origin_board_value):
		return REFUSAL_BOARD_DIRECTED
	if policy.latest_classification(ticket_name)[0] == CATEGORY_E:
		return REFUSAL_CATEGORY_E
	return None
