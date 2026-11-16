"""CHG-009 T4: the panel's bot status reader (design 3.2, 3.3, D-1, D-2, D-4; ADR-048 QĐ 6).

Each test writes the rows the reader sees as their writers write them: run_event rows through
`run_log.record_event` (the queue's call rows, the handlers' refusals, the runner's end rows), skip, classify and
reason rows through `run_log.write_entry`. Their `creation` is then moved to a fixed time and `now` is passed, so no
assertion reads the wall clock (STD-TEST-6).
"""

from datetime import datetime, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import bot_status, run_log, runner
from erp_ai.agent.messages import add_message
from erp_ai.constants import (
	BOT_CALL_EXPIRY_S,
	EVENT_CALL_BUSY,
	EVENT_CALL_MERGED,
	EVENT_CALL_RECEIVED,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
	LOG_DOCTYPE,
	MESSAGE_DOCTYPE,
	SKIP_AGENT_DISABLED,
	SKIP_DAILY_LIMIT,
	SKIP_LEVEL_L0,
	SKIP_NOT_SENDABLE,
	SKIP_PREFILLED,
)
from erp_ai.test_utils import keep_agent_settings, make_log_entry, set_agent_settings

NOW = datetime(2026, 11, 3, 15, 47, 10)
YESTERDAY = NOW - timedelta(days=1)
EXPIRY = timedelta(seconds=BOT_CALL_EXPIRY_S)
# AC-1: the two fixed forms of the status line, as the spec quotes them.
RUNNING = "Đang xử lý…"
NEVER = "Bot chưa chạy trên phiếu này"
CALL_AND_RUN_CODES = (
	EVENT_CALL_RECEIVED,
	EVENT_CALL_MERGED,
	EVENT_CALL_BUSY,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
)
# Codes a bookkeeping stop or an old run left on a skip row: not in the table, so no line (design 3.2 step 6).
OFF_TABLE_SKIPS = ("event_missing", "superseded", "kb_exists", SKIP_NOT_SENDABLE)


def at(hour: int, minute: int, second: int = 0, day: datetime = NOW) -> datetime:
	return day.replace(hour=hour, minute=minute, second=second, microsecond=0)


def status(state, text, lines=(), expires_in_s=None, expired_text=None) -> dict:
	"""The value of `panel_status`, with exactly the keys of design 3.1."""
	return {
		"state": state,
		"text": text,
		"expires_in_s": expires_in_s,
		"expired_text": expired_text,
		"lines": list(lines),
	}


def line(kind, text, after_message=None) -> dict:
	"""One system line: exactly `kind`, `text`, `after_message` (no author, no bot flag: design 3.1)."""
	return {"kind": kind, "text": text, "after_message": after_message}


def not_run(code, clock=None) -> str:
	"""AC-1 "Không chạy: <lý do>", or with `clock` the AC-4 line "Không chạy lúc HH:MM: <lý do>"."""
	reason = bot_status.REASONS[code]
	return f"Không chạy lúc {clock}: {reason}" if clock else f"Không chạy: {reason}"


class _StatusCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		# A new ticket or message queues no job; the refusal row its handler writes is removed by `_ticket`.
		keep_agent_settings(self)
		set_agent_settings(enabled=0)

	def _ticket(self, *message_times) -> tuple[str, list[str]]:
		"""A new ticket with one message at each of `message_times`, and no ERP AI Log row: the rows its creation
		and its messages left are removed, so each test writes every row the reader sees."""
		ticket = str(make_ticket(subject="ERPAI-TEST-bot-status").name)
		messages = [
			self._created(MESSAGE_DOCTYPE, add_message(ticket, f"ERPAI-TEST tin {index}", trusted=True), when)
			for index, when in enumerate(message_times)
		]
		frappe.db.delete(LOG_DOCTYPE, {"ticket": ticket})
		return ticket, messages

	def _created(self, doctype, name, when) -> str:
		frappe.db.set_value(doctype, name, "creation", when, update_modified=False)
		return name

	def _event(self, ticket, code, when, run_id=None) -> str:
		"""A run_event row as the queue, a handler or the runner's end writes it, created at `when`."""
		name = run_log.record_event(ticket=ticket, trigger="comment_mention", code=code, run_id=run_id)
		self.assertIsNotNone(name, code)
		return self._created(LOG_DOCTYPE, name, when)

	def _run_row(self, ticket, entry_type, when, run_id, stop_reason=None) -> str:
		"""A skip, classify or reason row of run `run_id`, as the runner writes it, created at `when`."""
		name = make_log_entry(
			ticket=ticket,
			entry_type=entry_type,
			trigger="comment_mention",
			run_id=run_id,
			stop_reason=stop_reason,
		)
		return self._created(LOG_DOCTYPE, name, when)

	def _status(self, ticket, messages=(), now=NOW) -> dict:
		return bot_status.panel_status(ticket, list(messages), now=now)


class TestPanelStatus(_StatusCase):
	def test_five_forms(self):
		running, done, failed, refused, stopped, never = (self._ticket()[0] for _ in range(6))
		call = at(15, 42, 10)
		self._event(running, EVENT_CALL_RECEIVED, call, "ERPAI-TEST-run-open")
		self._event(done, EVENT_CALL_RECEIVED, at(10, 5), "ERPAI-TEST-run-done")
		self._event(done, EVENT_RUN_DONE, at(10, 12, 40), "ERPAI-TEST-run-done")
		self._event(failed, EVENT_CALL_RECEIVED, at(11, 0), "ERPAI-TEST-run-failed")
		self._event(failed, EVENT_RUN_FAILED, at(11, 3, 30), "ERPAI-TEST-run-failed")
		# not run: a handler's refusal (no call), and the runner's early stop that closes its call
		excluded_title = f"{SKIP_NOT_SENDABLE}:excluded_title"
		self._event(refused, excluded_title, at(8, 12))
		self._event(stopped, EVENT_CALL_RECEIVED, at(13, 20), "ERPAI-TEST-run-stopped")
		self._run_row(stopped, "skip", at(13, 20, 5), "ERPAI-TEST-run-stopped", SKIP_DAILY_LIMIT)

		deadline = call + EXPIRY
		expected = {
			running: status(
				"running",
				RUNNING,
				expires_in_s=BOT_CALL_EXPIRY_S - 300,
				expired_text=f"Lỗi lúc {deadline:%H:%M}",
			),
			done: status("done", "Đã xong lúc 10:12", [line("done", "Đã xong lúc 10:12")]),
			failed: status("failed", "Lỗi lúc 11:03", [line("failed", "Lỗi lúc 11:03")]),
			refused: status(
				"not_run", not_run(excluded_title), [line("not_run", not_run(excluded_title, "08:12"))]
			),
			stopped: status(
				"not_run", not_run(SKIP_DAILY_LIMIT), [line("not_run", not_run(SKIP_DAILY_LIMIT, "13:20"))]
			),
			never: status("never", NEVER),
		}
		for ticket, want in expected.items():
			with self.subTest(state=want["state"], text=want["text"]):
				self.assertEqual(self._status(ticket), want)

	def test_open_call_wins_over_later_refusal(self):
		ticket, _ = self._ticket()
		call = at(15, 30)
		opted_out = f"{SKIP_NOT_SENDABLE}:opted_out"
		self._event(ticket, EVENT_CALL_RECEIVED, call, "ERPAI-TEST-run-open")
		self._event(ticket, EVENT_CALL_MERGED, at(15, 31))
		self._event(ticket, opted_out, at(15, 40))
		merged = line("merged", bot_status.LINE_TEXTS["merged"])
		refusal = line("not_run", not_run(opted_out, "15:40"))
		deadline = call + EXPIRY
		self.assertEqual(
			self._status(ticket),
			status(
				"running",
				RUNNING,
				[merged, refusal],
				expires_in_s=int((deadline - NOW).total_seconds()),
				expired_text=f"Lỗi lúc {deadline:%H:%M}",
			),
		)
		# The run ends before the refusal: the newest event decides; a later busy row decides nothing.
		self._event(ticket, EVENT_RUN_DONE, at(15, 38), "ERPAI-TEST-run-open")
		self._event(ticket, EVENT_CALL_BUSY, at(15, 45))
		self.assertEqual(
			self._status(ticket),
			status(
				"not_run",
				not_run(opted_out),
				[
					merged,
					line("done", "Đã xong lúc 15:38"),
					refusal,
					line("busy", bot_status.LINE_TEXTS["busy"]),
				],
			),
		)

	def test_clock_today_and_other_day(self):
		ticket, _ = self._ticket()
		self._event(ticket, EVENT_CALL_RECEIVED, at(23, 50, day=YESTERDAY), "ERPAI-TEST-run-late")
		self._event(ticket, EVENT_RUN_DONE, at(23, 59, 30, day=YESTERDAY), "ERPAI-TEST-run-late")
		# read the next day: day/month first, then the time
		late = "Đã xong lúc 02/11 23:59"
		self.assertEqual(self._status(ticket), status("done", late, [line("done", late)]))
		# read the same day: the time only
		same_day = "Đã xong lúc 23:59"
		self.assertEqual(
			self._status(ticket, now=at(23, 59, 50, day=YESTERDAY)),
			status("done", same_day, [line("done", same_day)]),
		)
		# a refusal after midnight: the old line keeps its date, the new one has none
		self._event(ticket, SKIP_AGENT_DISABLED, at(0, 1))
		self.assertEqual(
			self._status(ticket),
			status(
				"not_run",
				not_run(SKIP_AGENT_DISABLED),
				[line("done", late), line("not_run", not_run(SKIP_AGENT_DISABLED, "00:01"))],
			),
		)

	def test_legacy_runs_read_as_done_or_failed(self):
		# D-4: a run before CHG-009 left only classify/reason rows; the newest decides the status line, no line
		ticket, _ = self._ticket()
		self._run_row(ticket, "classify", at(9, 0, 5), "ERPAI-TEST-legacy-1")
		self._run_row(ticket, "reason", at(9, 2, 40), "ERPAI-TEST-legacy-1")
		self.assertEqual(self._status(ticket), status("done", "Đã xong lúc 09:02"))
		for stop in (runner.STOP_GATEWAY_ERROR, runner.STOP_TIME_BUDGET):
			with self.subTest(stop=stop):
				ticket, _ = self._ticket()
				self._run_row(ticket, "classify", at(8, 0), "ERPAI-TEST-legacy-old")
				self._run_row(ticket, "classify", at(10, 10), "ERPAI-TEST-legacy-2")
				self._run_row(ticket, "reason", at(10, 15, 20), "ERPAI-TEST-legacy-2", stop)
				self.assertEqual(self._status(ticket), status("failed", "Lỗi lúc 10:15"))

	def test_open_call_fails_at_deadline(self):
		# AC-8, D-1: a call with no end row is "Đang xử lý…" until its deadline, then "Lỗi lúc <deadline>"
		ticket, _ = self._ticket()
		first, second = at(14, 5, 20), at(14, 7)
		self._event(ticket, EVENT_CALL_RECEIVED, first, "ERPAI-TEST-run-lost-1")
		self._event(ticket, EVENT_CALL_RECEIVED, second, "ERPAI-TEST-run-lost-2")
		first_deadline, second_deadline = first + EXPIRY, second + EXPIRY
		first_line = line("failed", f"Lỗi lúc {first_deadline:%H:%M}")
		second_text = f"Lỗi lúc {second_deadline:%H:%M}"
		one_second = timedelta(seconds=1)
		to_second = int((second_deadline - first_deadline).total_seconds())
		cases = {
			"both open: the latest deadline counts": (
				first_deadline - one_second,
				status("running", RUNNING, expires_in_s=to_second + 1, expired_text=second_text),
			),
			"the first at its deadline: one line, the second still runs": (
				first_deadline,
				status("running", RUNNING, [first_line], expires_in_s=to_second, expired_text=second_text),
			),
			"one second before the last deadline": (
				second_deadline - one_second,
				status("running", RUNNING, [first_line], expires_in_s=1, expired_text=second_text),
			),
			"half a second before it: still at least 1": (
				second_deadline - one_second / 2,
				status("running", RUNNING, [first_line], expires_in_s=1, expired_text=second_text),
			),
			"at the last deadline": (
				second_deadline,
				status("failed", second_text, [first_line, line("failed", second_text)]),
			),
			"one second after it": (
				second_deadline + one_second,
				status("failed", second_text, [first_line, line("failed", second_text)]),
			),
		}
		for case, (now, want) in cases.items():
			with self.subTest(case=case):
				self.assertEqual(self._status(ticket, now=now), want)


class TestPanelLines(_StatusCase):
	def test_lines_ordered_and_anchored(self):
		ticket, (first, second, third) = self._ticket(at(9, 0), at(9, 10), at(9, 20))
		# written out of time order, so the order of the lines is the reader's
		self._event(ticket, EVENT_RUN_FAILED, at(9, 30), "ERPAI-TEST-run-3")
		self._event(ticket, EVENT_CALL_RECEIVED, at(9, 28), "ERPAI-TEST-run-3")
		self._event(ticket, EVENT_CALL_RECEIVED, at(9, 0, 1), "ERPAI-TEST-run-1")
		self._event(ticket, EVENT_RUN_DONE, at(9, 5), "ERPAI-TEST-run-1")
		self._event(ticket, SKIP_PREFILLED, at(8, 55))
		self._event(ticket, EVENT_CALL_RECEIVED, at(7, 0), "ERPAI-TEST-run-lost")
		self._event(ticket, EVENT_CALL_MERGED, at(9, 10))  # at the second message's own time: under it
		self._event(ticket, EVENT_CALL_BUSY, at(9, 10, 1))
		self._event(ticket, EVENT_CALL_RECEIVED, at(9, 24), "ERPAI-TEST-run-2")
		self._run_row(ticket, "skip", at(9, 25), "ERPAI-TEST-run-2", SKIP_LEVEL_L0)
		# no line: a bookkeeping stop or an old code, a legacy run's rows
		for index, code in enumerate(OFF_TABLE_SKIPS):
			run_id = f"ERPAI-TEST-run-off-{index}"
			self._event(ticket, EVENT_CALL_RECEIVED, at(9, 40 + index), run_id)
			self._run_row(ticket, "skip", at(9, 40 + index, 30), run_id, code)
		self._run_row(ticket, "classify", at(6, 0), "ERPAI-TEST-legacy")
		self._run_row(ticket, "reason", at(6, 1), "ERPAI-TEST-legacy")

		lost_deadline = at(7, 0) + EXPIRY
		self.assertEqual(
			self._status(ticket, [first, second, third]),
			status(
				"failed",
				"Lỗi lúc 09:30",
				[
					line("failed", f"Lỗi lúc {lost_deadline:%H:%M}"),
					line("not_run", not_run(SKIP_PREFILLED, "08:55")),
					line("done", "Đã xong lúc 09:05", first),
					line("merged", bot_status.LINE_TEXTS["merged"], second),
					line("busy", bot_status.LINE_TEXTS["busy"], second),
					line("not_run", not_run(SKIP_LEVEL_L0, "09:25"), third),
					line("failed", "Lỗi lúc 09:30", third),
				],
			),
		)


class TestReasonTable(_StatusCase):
	def test_reasons_distinct_and_cover_every_code(self):
		refusals = set(run_log.EVENT_CODES) - set(CALL_AND_RUN_CODES)  # the handlers' seven reasons
		run_stops = refusals | {
			SKIP_LEVEL_L0,
			SKIP_DAILY_LIMIT,
		}  # what the runner's skip rows carry (design 3.7)
		self.assertEqual(set(bot_status.REASONS), run_stops)
		self.assertEqual(len(set(bot_status.REASONS.values())), len(run_stops))
		self.assertEqual(set(bot_status.FAILED_STOPS), {runner.STOP_GATEWAY_ERROR, runner.STOP_TIME_BUDGET})

		# each code reaches the panel with its own sentence, from a handler's row and from a runner's skip row
		ticket, _ = self._ticket()
		when = at(8, 0)
		for index, code in enumerate(sorted(run_stops)):
			writers = ("run_event", "skip") if code in refusals else ("skip",)
			for writer in writers:
				with self.subTest(code=code, writer=writer):
					when += timedelta(minutes=1)
					if writer == "skip":
						self._run_row(ticket, "skip", when, f"ERPAI-TEST-stop-{index}", code)
					else:
						self._event(ticket, code, when)
					got = self._status(ticket)
					self.assertEqual((got["state"], got["text"]), ("not_run", not_run(code)))
					self.assertEqual(got["lines"][-1], line("not_run", not_run(code, f"{when:%H:%M}")))
