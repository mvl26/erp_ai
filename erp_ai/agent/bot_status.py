"""The bot's status in the "Trao đổi với bot" panel, read from the ticket's ERP AI Log rows (ADR-048 QĐ 6).

The one reader of the panel's status line and system lines (CHG-009 design 3.2, 3.3). It reads the ticket's
`run_event`, `skip`, `classify` and `reason` rows, and the creation time of the panel's messages, and builds every
sentence from the one table below, by code only: no setting, ticket content or error detail reaches the panel. It
checks no gate (its one caller, the panel's read, has), and writes nothing, reads no cache and no job state.
"""

from datetime import datetime

import frappe
from frappe.utils import add_to_date, ceil, now_datetime

from erp_ai.constants import (
	BOT_CALL_EXPIRY_S,
	EVENT_CALL_BUSY,
	EVENT_CALL_MERGED,
	EVENT_CALL_RECEIVED,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
	LOG_DOCTYPE,
	LOG_ENTRY_RUN_EVENT,
	MESSAGE_DOCTYPE,
	SKIP_AGENT_DISABLED,
	SKIP_CREATED_BY_AGENT,
	SKIP_DAILY_LIMIT,
	SKIP_LEVEL_L0,
	SKIP_NOT_SENDABLE,
	SKIP_PREFILLED,
)

MAX_ROWS = 500
# The stop reasons a failed run leaves on its classify/reason row; they tell a failed run before CHG-009 (D-4).
# Equal to runner.STOP_GATEWAY_ERROR, STOP_TIME_BUDGET: this module may not import the runner, the test compares.
FAILED_STOPS = ("gateway_error", "time_budget")
ENTRY_SKIP = "skip"
RUN_ENTRY_TYPES = ("classify", "reason")
READ_ENTRY_TYPES = (LOG_ENTRY_RUN_EVENT, ENTRY_SKIP, *RUN_ENTRY_TYPES)

# design 3.1: the states of the status line; the kinds of a system line are the three end states and two more.
STATE_RUNNING = "running"
STATE_DONE = "done"
STATE_FAILED = "failed"
STATE_NOT_RUN = "not_run"
STATE_NEVER = "never"
KIND_MERGED = "merged"
KIND_BUSY = "busy"
END_STATES = (STATE_DONE, STATE_FAILED, STATE_NOT_RUN)
EVENT_KINDS = {
	EVENT_RUN_DONE: STATE_DONE,
	EVENT_RUN_FAILED: STATE_FAILED,
	EVENT_CALL_MERGED: KIND_MERGED,
	EVENT_CALL_BUSY: KIND_BUSY,
}

# design 3.3, ADR-048 QĐ 6: the one table from a code to its sentence. `{clock}` is the only value put into a
# sentence; a reason names its kind only, never a keyword, a limit, a prefix or a team (A-8).
STATUS_TEXTS = {
	STATE_RUNNING: "Đang xử lý…",
	STATE_DONE: "Đã xong lúc {clock}",
	STATE_FAILED: "Lỗi lúc {clock}",
	STATE_NOT_RUN: "Không chạy: {reason}",
	STATE_NEVER: "Bot chưa chạy trên phiếu này",
}
LINE_TEXTS = {
	STATE_DONE: "Đã xong lúc {clock}",
	STATE_FAILED: "Lỗi lúc {clock}",
	STATE_NOT_RUN: "Không chạy lúc {clock}: {reason}",
	KIND_MERGED: "Bot sẽ đọc tin này trong lần xử lý đang chờ.",
	KIND_BUSY: (
		"Bot đang xử lý tin trước nên có thể chưa đọc tin này; nếu bot không trả lời, hãy gửi lại sau khi bot xong."
	),
}
REASONS = {
	SKIP_AGENT_DISABLED: "bot đang tắt",
	SKIP_CREATED_BY_AGENT: "phiếu do tài khoản bot tạo",
	SKIP_PREFILLED: "phiếu đã có đủ phân loại khi tạo",
	f"{SKIP_NOT_SENDABLE}:opted_out": "phiếu được đánh dấu không dùng AI",
	f"{SKIP_NOT_SENDABLE}:excluded_team": "phiếu thuộc nhóm bị loại trừ",
	f"{SKIP_NOT_SENDABLE}:excluded_title": "tiêu đề phiếu có tiền tố bị loại trừ",
	f"{SKIP_NOT_SENDABLE}:excluded_by_classification": "phiếu bị loại trừ theo kết quả phân loại",
	SKIP_LEVEL_L0: "bot đang ở chế độ chỉ ghi nhận nên chỉ phân loại lúc phiếu mới tạo",
	SKIP_DAILY_LIMIT: "phiếu đã hết lượt của bot hôm nay",
}


def panel_status(ticket: str, message_names: list[str], now: datetime | None = None) -> dict:
	"""The bot's status line and system lines for the panel of `ticket` (design 3.1, 3.2).

	`message_names` are the panel's messages, the lines are anchored under them; `now` defaults to the system time.
	A call received and not closed by its run's end row or a `skip` row is open until its deadline (received +
	`BOT_CALL_EXPIRY_S`); while one is, the state is `running`. Otherwise the newest end event decides: a run's end
	row, a refusal or early stop with a reason of `REASONS`, a run before CHG-009 known only by its classify/reason
	rows (D-4), a call past its deadline. Merged and busy rows only add a line. Reads only; never raises on rows
	with codes outside the table, they give nothing.

	Returns:
		`{"state", "text", "expires_in_s", "expired_text", "lines"}`: `state` in `running|done|failed|not_run|never`;
		`text` its sentence; `expires_in_s` (int >= 1) and `expired_text` ("Lỗi lúc <deadline>") for the latest
		deadline of an open call, else None; `lines` oldest first, each `{"kind", "text", "after_message"}` with
		`after_message` the newest message created at or before the line (None: before every message).
	"""
	now = now or now_datetime()
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket, "entry_type": ("in", READ_ENTRY_TYPES)},
		fields=["name", "entry_type", "stop_reason", "run_id", "creation"],
		order_by="creation desc, name desc",
		limit=MAX_ROWS,
	)
	rows.reverse()
	calls, closed, runs, lines = {}, set(), {}, []
	for row in rows:
		code = row.stop_reason
		if row.entry_type == LOG_ENTRY_RUN_EVENT and code == EVENT_CALL_RECEIVED:
			calls[row.run_id] = row.creation
		elif row.entry_type in RUN_ENTRY_TYPES:
			runs.setdefault(row.run_id, []).append(row)
		elif row.entry_type == ENTRY_SKIP or code in (EVENT_RUN_DONE, EVENT_RUN_FAILED):
			closed.add(row.run_id)
		if row.entry_type == LOG_ENTRY_RUN_EVENT and code in EVENT_KINDS:
			lines.append((row.creation, EVENT_KINDS[code], None))
		elif row.entry_type in (LOG_ENTRY_RUN_EVENT, ENTRY_SKIP) and code in REASONS:
			lines.append((row.creation, STATE_NOT_RUN, REASONS[code]))

	deadlines = [
		add_to_date(received, seconds=BOT_CALL_EXPIRY_S)
		for run_id, received in calls.items()
		if run_id not in closed
	]
	lines.extend((deadline, STATE_FAILED, None) for deadline in deadlines if deadline <= now)
	lines.sort(key=lambda line: line[0])
	ends = [line for line in lines if line[1] in END_STATES] + _legacy_ends(runs, closed, calls)
	ends.sort(key=lambda end: end[0])

	expires_in_s = expired_text = None
	live = [deadline for deadline in deadlines if deadline > now]
	if live:
		latest = max(live)
		state, text = STATE_RUNNING, STATUS_TEXTS[STATE_RUNNING]
		expires_in_s = max(1, ceil((latest - now).total_seconds()))
		expired_text = STATUS_TEXTS[STATE_FAILED].format(clock=_clock(latest, now))
	elif ends:
		at, state, reason = ends[-1]
		text = STATUS_TEXTS[state].format(clock=_clock(at, now), reason=reason)
	else:
		state, text = STATE_NEVER, STATUS_TEXTS[STATE_NEVER]
	return {
		"state": state,
		"text": text,
		"expires_in_s": expires_in_s,
		"expired_text": expired_text,
		"lines": _anchored(lines, message_names, now),
	}


def _legacy_ends(runs: dict, closed: set, calls: dict) -> list:
	"""D-4: a run known only by its classify/reason rows ended at its newest row, failed when one of them carries
	a stop reason of `FAILED_STOPS`; it gives the status line only, never a line."""
	return [
		(
			max(row.creation for row in run_rows),
			STATE_FAILED if any(row.stop_reason in FAILED_STOPS for row in run_rows) else STATE_DONE,
			None,
		)
		for run_id, run_rows in runs.items()
		if run_id not in closed and run_id not in calls
	]


def _anchored(lines: list, message_names: list[str], now: datetime) -> list:
	"""Each line, oldest first, as `{kind, text, after_message}` under the newest message created at or before it
	(D-5); messages created at the same time keep the panel's order."""
	order = {name: index for index, name in enumerate(message_names)}
	messages = (
		sorted(
			(row.creation, order[row.name], row.name)
			for row in frappe.get_all(
				MESSAGE_DOCTYPE, filters={"name": ("in", message_names)}, fields=["name", "creation"]
			)
		)
		if message_names
		else []
	)
	anchored, index, after = [], 0, None
	for at, kind, reason in lines:
		while index < len(messages) and messages[index][0] <= at:
			after = messages[index][2]
			index += 1
		text = LINE_TEXTS[kind].format(clock=_clock(at, now), reason=reason)
		anchored.append({"kind": kind, "text": text, "after_message": after})
	return anchored


def _clock(at: datetime, now: datetime) -> str:
	"""A-6: "HH:MM" on the day of `now`, else "dd/mm HH:MM"; system time, as the log stores it."""
	return at.strftime("%H:%M" if at.date() == now.date() else "%d/%m %H:%M")
