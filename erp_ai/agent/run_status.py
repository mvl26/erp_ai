"""Status signals of one agent run to the ticket page (design 3.2, 3.3). Only the runner imports this module.

Nothing here raises: a failed signal must never change what the run does (AC-7).
"""

import frappe
from frappe.realtime import get_doc_room
from frappe.utils import get_fullname

from erp_ai.constants import AGENT_STATUS_EVENT, AGENT_USER, JOB_TIMEOUT_S

PAYLOAD_KEYS = ("ticket_id", "run_id", "agent_user", "agent_name", "state", "text", "expires_in_s")
STATE_THINKING = "thinking"
STATE_WORKING = "working"
STATE_DONE = "done"
CLASSIFY_STEP = "classify"
WORKING_TEXT = "Đang làm: {label}…"
FALLBACK_WORK_LABEL = "xử lý yêu cầu"
# The only table of work labels (A-15): the text of a "working" signal comes from here, never from the model.
WORK_LABELS = {
	"get_ticket": "đọc phiếu",
	"list_comments": "đọc comment",
	"search_resolved_tickets": "tìm phiếu đã giải quyết",
	"get_record": "tra bản ghi",
	"search_source": "tra mã nguồn",
	"read_source": "đọc mã nguồn",
	"git_source": "xem lịch sử mã nguồn",
	"set_classification": "ghi phân loại",
	"set_resolution_hint": "ghi hướng giải quyết",
	"post_comment": "viết trả lời",
	"create_task": "tạo task",
	"search_knowledge_base": "tìm bài CSKT",
	"search_manuals": "tìm trong HDSD",
	"read_error_logs": "đọc nhật ký lỗi",
	"run_report": "xem báo cáo",
	CLASSIFY_STEP: "phân loại phiếu",
}


class RunStatus:
	def __init__(self, ticket_name: str, run_id: str, thinking_text: str | None):
		self.ticket_name = ticket_name
		self.run_id = run_id
		self.text = (thinking_text or "").strip()
		self.active = bool(self.text)
		self.started = False
		self.finished = False
		self.last_state = None
		self.signal_count = 0
		self._errors = []

	def start(self) -> None:
		if not self.active or self.started:
			return
		# marked before emitting so that `done` is still attempted when this emit fails (AC-7)
		self.started = True
		self._emit(STATE_THINKING, self.text)

	def thinking(self) -> None:
		if self.started and not self.finished and self.last_state != STATE_THINKING:
			self._emit(STATE_THINKING, self.text)

	def working(self, step: str) -> None:
		if self.started and not self.finished:
			try:
				# an unknown name (invented by the model) never reaches the text (D-5)
				label = WORK_LABELS.get(step, FALLBACK_WORK_LABEL)
			except TypeError:
				label = FALLBACK_WORK_LABEL
			self._emit(STATE_WORKING, WORKING_TEXT.format(label=label))

	def take_errors(self) -> list[str]:
		errors, self._errors = self._errors, []
		return errors

	def done(self) -> None:
		if self.started and not self.finished:
			self.finished = True
			self._emit(STATE_DONE, "")

	def stop(self) -> None:
		"""The one `done` of a run that stopped early on its skip row (ADR-008 Amendment 1): only before `start()`."""
		if self.active and not self.started and not self.finished:
			self.finished = True
			self._emit(STATE_DONE, "")

	def _emit(self, state: str, text: str) -> None:
		self.last_state = state
		self.signal_count += 1
		try:
			payload = dict(
				zip(
					PAYLOAD_KEYS,
					(
						str(self.ticket_name),
						self.run_id,
						AGENT_USER,
						get_fullname(AGENT_USER),
						state,
						text,
						JOB_TIMEOUT_S,
					),
					strict=True,
				)
			)
			frappe.publish_realtime(
				AGENT_STATUS_EVENT,
				message=payload,
				room=get_doc_room("HD Ticket", self.ticket_name),
				after_commit=False,
			)
		except Exception as exc:
			self._errors.append(f"status_{state}: {type(exc).__name__}")
