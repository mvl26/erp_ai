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
	CATEGORIES,
	CLASSIFICATION_FIELDS,
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
	PROPOSAL_DOCTYPE,
	SETTING_DOCTYPE,
	TRIGGER_COMMENT_MENTION,
)

SITUATION_MAX = 300
TEXT_MAX = 1000
STEP_CREATE = "Tạo"
STEP_UPDATE = "Cập nhật"
# R9: the label of each classification field in a correction lesson.
CORRECTION_LABELS = {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
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
	nothing. A `Bị từ chối` lesson is final: an update finds it and writes nothing (R12). Returns None (writes
	nothing) when learning is off, the ticket is one the bot must not take (NFR-1), the source gives no lesson
	for this actor, or the text is empty.

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
		if doc.lesson_status == LESSON_STATUS_REJECTED or stored == (situation, lesson_text, status):
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


def _retire(event_key: str) -> str | None:
	"""The person undid the decision the lesson of `event_key` came from: it stops being used (I5).

	`Đang dùng` becomes `Đã tắt` (step `Tắt`), `Chờ duyệt` becomes `Bị từ chối` (step `Từ chối`), with the session
	user as reviewer and actor. It undoes the person's own decision, so there is no permission check; any other
	status, or no lesson for the key, is left as it is. Returns the name of the lesson it retired, else None.
	"""
	name = frappe.db.get_value(LESSON_DOCTYPE, {"event_key": event_key}, "name")
	if not name:
		return None
	user = _actor()
	doc = frappe.get_doc(LESSON_DOCTYPE, name, for_update=True)
	if doc.lesson_status == LESSON_STATUS_ACTIVE:
		doc.lesson_status, step = LESSON_STATUS_DISABLED, STEP_DISABLE
	elif doc.lesson_status == LESSON_STATUS_PENDING:
		doc.lesson_status, step = LESSON_STATUS_REJECTED, STEP_REJECT
	else:
		return None
	now = now_datetime()
	doc.update({"reviewed_by": user, "reviewed_at": now})
	_add_event(doc, step, user, now)
	# Only the status and the reviewer change: a link the lesson already holds (a deleted ticket) is not re-checked.
	doc.flags.ignore_links = True
	_write(doc)
	return doc.name


def record_correction(ticket: str, log_name: str, changed_fields) -> list[str]:
	"""A person changed `changed_fields` of the classification of `ticket` after the bot's classify row `log_name`.

	Each changed field is its own lesson `correction:{ticket}:{field}` (R9), updated by each later change of that
	field, and names only that field: "Bot dự đoán {label} {predicted}; người chọn {label} {value}.". A field the
	bot made no prediction for gives none; a field set back to the bot's prediction (None and "" equal) retires its
	lesson instead. Returns the names of the lessons made or updated.
	"""
	user = _actor()
	fields = [field for field in CLASSIFICATION_FIELDS if field in (changed_fields or ())]
	if not fields:
		return []
	predicted = frappe.db.get_value(
		LOG_DOCTYPE, log_name, [f"predicted_{field}" for field in fields], as_dict=True
	)
	current = frappe.db.get_value(policy.TICKET_DOCTYPE, ticket, fields, as_dict=True)
	if not predicted or not current:
		return []
	names, context = [], None
	for field in fields:
		bot_value, value = predicted[f"predicted_{field}"] or "", current[field] or ""
		if not bot_value:
			continue
		event_key = f"correction:{ticket}:{field}"
		if value == bot_value:
			_retire(event_key)
			continue
		if context is None:
			context = {
				"authorized": authority.is_instruction(user, ticket),
				"situation": _ticket_situation(ticket, with_description=True),
			}
		label = CORRECTION_LABELS[field]
		name = _store(
			LESSON_SOURCE_CORRECTION,
			event_key,
			ticket=ticket,
			updatable=True,
			text=f"Bot dự đoán {label} {bot_value}; người chọn {label} {value or '—'}.",
			**context,
		)
		if name:
			names.append(name)
	return names


def record_assignee_change(ticket: str, bot_user: str, new_user: str) -> str | None:
	"""A person assigned `ticket` to `new_user` after the bot had chosen `bot_user`: one lesson per ticket (AC-6).

	Giving the ticket back to `bot_user` retires that lesson instead (I5).
	"""
	user = _actor()
	event_key = f"assignee:{ticket}"
	if new_user == bot_user:
		_retire(event_key)
		return None
	return _store(
		LESSON_SOURCE_CORRECTION,
		event_key,
		ticket=ticket,
		updatable=True,
		authorized=authority.is_instruction(user, ticket),
		situation=_ticket_situation(ticket, with_description=True),
		text=f"Bot gán người nhận {bot_user}, người đổi sang {new_user}.",
	)


OUTCOME_VERBS = {"reject": "từ chối", "undo": "hoàn tác"}


def record_proposal_outcome(proposal: str, outcome: str) -> str | None:
	"""A change proposal a person rejected (`reject`) or undid (`undo`): one "don't do this" lesson (AC-10).

	The lesson names the kind and the target of the change and nothing of the ticket but its subject.
	"""
	if outcome not in OUTCOME_VERBS:
		raise ValueError(f"unknown proposal outcome: {outcome!r}")
	row = frappe.db.get_value(
		PROPOSAL_DOCTYPE,
		proposal,
		["ticket", "change_kind", "file_path", "command_args", "app"],
		as_dict=True,
	)
	if not row:
		return None
	target = " ".join((row.file_path or row.command_args or f"trong app {row.app or '—'}").split())
	return _store(
		LESSON_SOURCE_OUTCOME,
		f"{outcome}:{proposal}",
		ticket=row.ticket,
		change_proposal=proposal,
		authorized=True,
		situation=_ticket_situation(row.ticket, with_description=False) if row.ticket else "",
		text=f"Đừng làm như vậy: đề xuất {row.change_kind} {target} đã bị {OUTCOME_VERBS[outcome]}.",
	)


def record_review_verdict(review_month: str, ticket: str, note: str) -> str | None:
	"""A monthly-review verdict "Sai" on `ticket`: one "don't do this" lesson with the reviewer's note (AC-11)."""
	chosen = frappe.db.get_value(
		LOG_DOCTYPE,
		{"ticket": ticket, "entry_type": "classify", "predicted_category": ("in", CATEGORIES)},
		["predicted_ticket_type", "predicted_agent_group", "predicted_priority"],
		order_by="creation asc, name asc",
	)
	t, g, p = (value or "—" for value in (chosen or (None, None, None)))
	return _store(
		LESSON_SOURCE_OUTCOME,
		f"review:{review_month}:{ticket}",
		ticket=ticket,
		authorized=True,
		situation=_ticket_situation(ticket, with_description=True),
		text=(
			f"Đừng làm như vậy: rà soát tháng chấm Sai lần phân loại của bot (Loại {t}, Nhóm {g}, Ưu tiên {p}). "
			f"Ghi chú người rà: {note or '—'}"
		),
	)


def retire_review_verdict(review_month: str, ticket: str) -> str | None:
	"""The reviewer took back the "Sai" verdict on `ticket`: the lesson that verdict made stops being used (I5)."""
	return _retire(f"review:{review_month}:{ticket}")


def _fold(text: str) -> str:
	return unicodedata.normalize("NFC", text or "")


def teaching_rule(text: str) -> str | None:
	"""The rule of a "ghi nhớ:" message, or None when the message is not one or has no rule after the marker.

	A trigger keyword that starts the message is dropped (never one inside the rule); then the message must start
	with the teach marker (case and Unicode form ignored, spaces before the colon ignored). A blank marker setting
	turns this off.
	"""
	marker = _fold(policy.lesson_teach_marker())
	if not marker or not isinstance(text, str):
		return None
	body = _fold(text).strip()
	keyword = _fold(policy.get_trigger_keyword()).strip()
	if keyword and (lead := re.match(re.escape(keyword), body, flags=re.IGNORECASE)):
		body = body[lead.end() :].strip()
	words = marker.rstrip(":").split()
	if not words:
		return None
	pattern = r"\s+".join(re.escape(word) for word in words) + (r"\s*:" if marker.endswith(":") else "")
	found = re.match(pattern, body, flags=re.IGNORECASE)
	if not found:
		return None
	return body[found.end() :].strip() or None


def record_teaching_message(ticket: str, message_name: str, rule: str) -> str | None:
	"""A "ghi nhớ:" message: a taught rule, kept only when its author has the authority to instruct the bot.

	The lesson keeps the ticket link but no situation: the subject is the requester's text and a rule lesson is
	read as the teacher's rule, so none of it may ride along (R11).
	"""
	authorized = authority.run_instructor(ticket, TRIGGER_COMMENT_MENTION, message_name) is not None
	return _store(
		LESSON_SOURCE_TEACHING,
		f"teach:{message_name}",
		ticket=ticket,
		situation="",
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
