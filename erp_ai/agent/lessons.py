"""The lesson store (ADR-045): the only writer of ERP AI Lesson and its audit rows.

Every write runs in the session of the person who acted, never commits, and goes through the store flag with
permissions bypassed after the store's own checks. Sources in a person's request call it through `safely`.
"""

import re
import unicodedata
import uuid

import frappe
from frappe.utils import escape_html, now_datetime

from erp_ai.agent import authority, policy
from erp_ai.agent.knowledge import plain_text
from erp_ai.agent.redact import redact_secrets
from erp_ai.constants import (
	AGENT_USER,
	LESSON_DOCTYPE,
	LESSON_SOURCE_CORRECTION,
	LESSON_SOURCE_OUTCOME,
	LESSON_SOURCE_RESOLVED,
	LESSON_SOURCE_TEACHING,
	LESSON_STATUS_ACTIVE,
	LESSON_STATUS_DISABLED,
	LESSON_STATUS_PENDING,
	LESSON_STATUS_REJECTED,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
	TRIGGER_COMMENT_MENTION,
)

SITUATION_MAX = 300
TEXT_MAX = 1000
STEP_CREATE = "Tạo"
STEP_UPDATE = "Cập nhật"
CLASSIFICATION_FIELDS = ("ticket_type", "agent_group", "priority")
STEP_DISABLE = "Tắt"
STEP_REJECT = "Từ chối"
SAVEPOINT = "erp_ai_lesson"
TITLE_STORE_FAILED = "erp_ai: ghi bài học lỗi"

ACTIONS = {  # action -> (from status, to status, step)
	"approve": (LESSON_STATUS_PENDING, LESSON_STATUS_ACTIVE, "Duyệt"),
	"reject": (LESSON_STATUS_PENDING, LESSON_STATUS_REJECTED, "Từ chối"),
	"disable": (LESSON_STATUS_ACTIVE, LESSON_STATUS_DISABLED, "Tắt"),
	"enable": (LESSON_STATUS_DISABLED, LESSON_STATUS_ACTIVE, "Bật"),
}
APPROVER_ACTIONS = ("approve", "reject")


class InvalidLessonTransition(frappe.ValidationError):
	"""The lesson is not in the status the action starts from, or the action is unknown; nothing is written."""


def schema_present() -> bool:
	"""The lesson DocType, the lesson switch of the Setting and the lessons column of the Log all exist."""
	return bool(
		frappe.db.exists("DocType", LESSON_DOCTYPE)
		and frappe.get_meta(SETTING_DOCTYPE).has_field(policy.LESSONS_ENABLED_FIELD)
		and frappe.get_meta(LOG_DOCTYPE).has_field("lessons_used")
	)


def _actor() -> str:
	"""The session user, who is the actor of every store write; the agent account is refused (QĐ 8)."""
	user = frappe.session.user
	if user == AGENT_USER:
		frappe.throw("Tài khoản agent không được ghi bài học", frappe.PermissionError)
	return user


def _status_for(source: str, authorized: bool) -> str | None:
	"""The initial status of a lesson from its source and the actor's authority (QĐ 3); None means no lesson."""
	if source == LESSON_SOURCE_CORRECTION:
		return LESSON_STATUS_ACTIVE if authorized else LESSON_STATUS_PENDING
	if source == LESSON_SOURCE_TEACHING:
		return LESSON_STATUS_ACTIVE if authorized else None
	if source == LESSON_SOURCE_OUTCOME:
		return LESSON_STATUS_ACTIVE
	if source == LESSON_SOURCE_RESOLVED:
		return LESSON_STATUS_PENDING
	raise ValueError(f"unknown lesson source {source!r}")


def _clean(text, limit: int) -> str:
	"""Secrets masked, whitespace collapsed to single spaces, cut to `limit` characters (NFR-3)."""
	return " ".join(redact_secrets(text).split())[:limit]


def _add_event(doc, step: str, user: str, when) -> None:
	doc.append("history", {"step": step, "actor": user, "happened_at": when})


def _write(doc, *, insert: bool = False) -> None:
	doc.flags.erp_ai_lesson_store = True
	if insert:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _ticket_situation(ticket: str, *, with_description: bool) -> str:
	"""`"{subject}"` or `"{subject}: {plain description}"`; "" for a missing ticket or one the bot must not take."""
	if policy.send_refusal(ticket) is not None:
		return ""
	row = frappe.db.get_value(policy.TICKET_DOCTYPE, ticket, ["subject", "description"], as_dict=True)
	subject = " ".join((row.subject or "").split())
	description = " ".join(plain_text(row.description).split()) if with_description else ""
	return f"{subject}: {description}" if description else subject


def _store(
	source: str,
	event_key: str,
	*,
	situation: str,
	text: str,
	authorized: bool,
	ticket: str | None = None,
	change_proposal: str | None = None,
	updatable: bool = False,
) -> str | None:
	"""Create the lesson of one event, or return the one already made for `event_key` (NFR-4).

	With `updatable`, an existing lesson takes the new situation, text, author and recomputed status and one
	`Cập nhật` event; a new status clears the last decision, and the same situation, text and status write
	nothing. Returns None (writes nothing) when learning is off, the ticket is one the bot must not
	take (NFR-1), the source gives no lesson for this actor, or the text is empty.

	Raises:
		frappe.PermissionError: the session user is the agent account.
		ValueError: `event_key` is empty or `source` is unknown.
	"""
	user = _actor()
	if not event_key:
		raise ValueError("a lesson needs a non-empty event key")
	if not policy.lessons_enabled():
		return None
	if ticket and policy.send_refusal(ticket) is not None:
		return None
	status = _status_for(source, authorized)
	if status is None:
		return None
	lesson_text = _clean(text, TEXT_MAX)
	if not lesson_text:
		return None
	situation = _clean(situation, SITUATION_MAX)
	now = now_datetime()
	existing = frappe.db.get_value(LESSON_DOCTYPE, {"event_key": event_key}, "name")
	if existing:
		if not updatable:
			return existing
		doc = frappe.get_doc(LESSON_DOCTYPE, existing, for_update=True)
		stored = (doc.situation or "", doc.lesson_text or "", doc.lesson_status)
		if stored == (situation, lesson_text, status):
			return doc.name
		if doc.lesson_status != status:
			doc.update({"reviewed_by": None, "reviewed_at": None})
		doc.update(
			{"situation": situation, "lesson_text": lesson_text, "author": user, "lesson_status": status}
		)
		_add_event(doc, STEP_UPDATE, user, now)
		_write(doc)
		return doc.name
	doc = frappe.get_doc(
		{
			"doctype": LESSON_DOCTYPE,
			"lesson_status": status,
			"lesson_source": source,
			"situation": situation,
			"lesson_text": lesson_text,
			"ticket": ticket,
			"change_proposal": change_proposal,
			"event_key": event_key,
			"author": user,
		}
	)
	_add_event(doc, STEP_CREATE, user, now)
	_write(doc, insert=True)
	return doc.name


def _retire_correction(event_key: str) -> None:
	"""The person put the classification back to the bot's own: their correction lesson stops being used.

	It is the person's own correction, so there is no permission check; any status but active or pending is left.
	"""
	name = frappe.db.get_value(LESSON_DOCTYPE, {"event_key": event_key}, "name")
	if not name:
		return
	user = _actor()
	doc = frappe.get_doc(LESSON_DOCTYPE, name, for_update=True)
	if doc.lesson_status == LESSON_STATUS_ACTIVE:
		doc.lesson_status, step = LESSON_STATUS_DISABLED, STEP_DISABLE
	elif doc.lesson_status == LESSON_STATUS_PENDING:
		doc.lesson_status, step = LESSON_STATUS_REJECTED, STEP_REJECT
	else:
		return
	now = now_datetime()
	doc.update({"reviewed_by": user, "reviewed_at": now})
	_add_event(doc, step, user, now)
	# Only the status and the reviewer change: a link the lesson already holds (a deleted ticket) is not re-checked.
	doc.flags.ignore_links = True
	_write(doc)


def record_correction(ticket: str, log_name: str) -> str | None:
	"""A person's classification of `ticket` differs from the bot's (the classify row `log_name`): one lesson.

	The same ticket keeps one lesson, updated by each later correction. When the person's values are again
	exactly the bot's, no lesson is made and the existing one is retired. Returns the lesson name or None.
	"""
	user = _actor()
	predicted = frappe.db.get_value(
		LOG_DOCTYPE,
		log_name,
		[f"predicted_{field}" for field in CLASSIFICATION_FIELDS],
	)
	current = frappe.db.get_value(policy.TICKET_DOCTYPE, ticket, list(CLASSIFICATION_FIELDS))
	if not predicted or not current:
		return None
	event_key = f"correction:{ticket}"
	if all((before or "") == (after or "") for before, after in zip(predicted, current, strict=True)):
		_retire_correction(event_key)
		return None
	t0, g0, p0 = (value or "—" for value in predicted)
	t1, g1, p1 = (value or "—" for value in current)
	return _store(
		LESSON_SOURCE_CORRECTION,
		event_key,
		ticket=ticket,
		updatable=True,
		authorized=authority.is_instruction(user, ticket),
		situation=_ticket_situation(ticket, with_description=True),
		text=(
			f"Bot xếp: Loại {t0}, Nhóm {g0}, Ưu tiên {p0}. Người sửa thành: Loại {t1}, Nhóm {g1}, Ưu tiên {p1}."
		),
	)


def _fold(text: str) -> str:
	return unicodedata.normalize("NFC", text or "")


def teaching_rule(text: str) -> str | None:
	"""The rule of a "ghi nhớ:" message, or None when the message is not one or has no rule after the marker.

	The trigger keyword is dropped first (once); then the message must start with the teach marker (case and
	Unicode form ignored, spaces before the colon ignored). A blank marker setting turns this off.
	"""
	marker = _fold(policy.lesson_teach_marker())
	if not marker or not isinstance(text, str):
		return None
	body = _fold(text)
	if keyword := _fold(policy.get_trigger_keyword()).strip():
		body = re.sub(re.escape(keyword), "", body, count=1, flags=re.IGNORECASE)
	body = body.strip()
	words = marker.rstrip(":").split()
	if not words:
		return None
	pattern = r"\s+".join(re.escape(word) for word in words) + (r"\s*:" if marker.endswith(":") else "")
	found = re.match(pattern, body, flags=re.IGNORECASE)
	if not found:
		return None
	return body[found.end() :].strip() or None


def record_teaching_message(ticket: str, message_name: str, rule: str) -> str | None:
	"""A "ghi nhớ:" message: a taught rule, kept only when its author has the authority to instruct the bot."""
	authorized = authority.run_instructor(ticket, TRIGGER_COMMENT_MENTION, message_name) is not None
	return _store(
		LESSON_SOURCE_TEACHING,
		f"teach:{message_name}",
		ticket=ticket,
		situation=_ticket_situation(ticket, with_description=False),
		text=rule,
		authorized=authorized,
	)


def transition(name: str, action: str) -> str:
	"""Move a lesson along one edge of `ACTIONS` as the session user; return the new status (QĐ 2).

	Approve and reject need a lesson approver (A-2), disable and enable an ERP AI Instructor (D-3). The row is
	locked and must be in the action's "from" status; the change and one event row are written together.

	Raises:
		frappe.PermissionError: the agent account, or a user without the right for this action.
		InvalidLessonTransition: an unknown action, or the lesson is not in the "from" status.
		frappe.DoesNotExistError: no lesson has that name.
	Nothing is written when it raises.
	"""
	user = _actor()
	if not isinstance(action, str) or action not in ACTIONS:
		frappe.throw("Thao tác với bài học không hợp lệ", InvalidLessonTransition)
	from_status, to_status, step = ACTIONS[action]
	allowed = policy.is_lesson_approver if action in APPROVER_ACTIONS else policy.can_manage_lessons
	if not allowed(user):
		frappe.throw(f"Bạn không có quyền {step.lower()} bài học", frappe.PermissionError)
	current = None
	if isinstance(name, str) and name:
		current = frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status", for_update=True)
	if current is None:
		frappe.throw(f"Không có bài học {escape_html(str(name))}", frappe.DoesNotExistError)
	if current != from_status:
		frappe.throw(
			f"Bài học đang ở trạng thái {current}, không {step.lower()} được", InvalidLessonTransition
		)
	now = now_datetime()
	doc = frappe.get_doc(LESSON_DOCTYPE, name)
	doc.update({"lesson_status": to_status, "reviewed_by": user, "reviewed_at": now})
	_add_event(doc, step, user, now)
	# Only the status and the reviewer change: a link the lesson already holds (a deleted ticket) is not re-checked.
	doc.flags.ignore_links = True
	_write(doc)
	return to_status


def teach(rule: str, situation: str = "") -> str:
	"""An ERP AI Instructor teaches the bot a rule by hand (AC-8); the lesson is active at once and has no ticket.

	Raises:
		frappe.PermissionError: the agent account, or a user who is not an ERP AI Instructor.
		frappe.ValidationError: learning is off, or the rule is empty.
	"""
	user = _actor()
	if not policy.can_manage_lessons(user):
		frappe.throw("Chỉ người có vai trò ERP AI Instructor được dạy bot", frappe.PermissionError)
	if not policy.lessons_enabled():
		frappe.throw("Bot đang tắt việc học", frappe.ValidationError)
	if not isinstance(rule, str) or not _clean(rule, TEXT_MAX):
		frappe.throw("Cần nhập quy tắc", frappe.ValidationError)
	return _store(
		LESSON_SOURCE_TEACHING,
		f"teach:{uuid.uuid4().hex}",
		situation=situation if isinstance(situation, str) else "",
		text=rule,
		authorized=True,
	)


def safely(func, *args, **kwargs) -> str | None:
	"""Run a store call for a source inside a person's request so that its failure does not fail the request (QĐ 5).

	On any exception the store's writes are undone to the savepoint, the messages it queued for the response
	are dropped, one Error Log with secrets masked is written, and None is returned; the person's own writes
	and messages from before the call stay. It re-raises only when the savepoint itself is gone (e.g. a
	deadlock already rolled back the whole transaction).
	"""
	queued = len(frappe.local.message_log)
	frappe.db.savepoint(SAVEPOINT)
	try:
		return func(*args, **kwargs)
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		# frappe.throw/msgprint queued these before raising; left in place they reach the person as an error dialog.
		del frappe.local.message_log[queued:]
		frappe.log_error(
			title=TITLE_STORE_FAILED,
			message=redact_secrets(frappe.get_traceback()) or TITLE_STORE_FAILED,
		)
		return None
