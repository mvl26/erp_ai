from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.policy import PermissionSwitches
from erp_ai.agent.run_status import (
	CLASSIFY_STEP,
	FALLBACK_WORK_LABEL,
	PAYLOAD_KEYS,
	WORK_LABELS,
	WORKING_TEXT,
	RunStatus,
)
from erp_ai.agent.tools.registry import GrantInputs, get_tool_schemas
from erp_ai.constants import LEVELS
from erp_ai.test_utils import record_status_signals

LABEL_TABLE = {
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
	# FEAT-007 T155 (R22a): the knowledge read tools every grant above L0 now holds.
	"search_knowledge_base": "tìm bài CSKT",
	"search_manuals": "tìm trong HDSD",
	"read_error_logs": "đọc nhật ký lỗi",
	"run_report": "xem báo cáo",
	"classify": "phân loại phiếu",
}


class TestRunStatus(FrappeTestCase):
	def setUp(self):
		self.signals = record_status_signals(self)

	def _status(self):
		status = RunStatus("HD-TICKET-1", "run1", "Đang suy nghĩ…")
		status.start()
		self.signals.clear()
		return status

	def test_every_granted_tool_and_classify_step_has_label(self):
		granted = {
			schema["name"]
			for schema in get_tool_schemas(
				GrantInputs(
					effective_level=LEVELS[-1],
					main_path_level=LEVELS[-1],
					has_instructor=True,
					switches=PermissionSwitches(),
				)
			)
		}

		self.assertEqual(CLASSIFY_STEP, "classify")
		self.assertEqual(set(WORK_LABELS), granted | {CLASSIFY_STEP})
		self.assertEqual(WORK_LABELS, LABEL_TABLE)
		for step in WORK_LABELS:
			with self.subTest(step):
				status = self._status()
				status.working(step)
				self.assertEqual(self.signals[-1]["message"]["state"], "working")
				self.assertEqual(
					self.signals[-1]["message"]["text"], WORKING_TEXT.format(label=LABEL_TABLE[step])
				)

	def test_unknown_tool_gets_fallback_label(self):
		status = self._status()

		status.working("drop_all_tables")

		text = self.signals[-1]["message"]["text"]
		self.assertEqual(text, f"Đang làm: {FALLBACK_WORK_LABEL}…")
		self.assertNotIn("drop_all_tables", text)

	def test_unhashable_step_never_throws(self):
		for step in (["x"], {}):
			with self.subTest(repr(step)):
				status = self._status()

				status.working(step)

				self.assertEqual(len(self.signals), 1)
				self.assertEqual(self.signals[0]["message"]["text"], f"Đang làm: {FALLBACK_WORK_LABEL}…")

	def test_payload_has_exactly_seven_keys(self):
		status = self._status()

		status.working("get_ticket")
		status.thinking()
		status.done()

		self.assertEqual([s["message"]["state"] for s in self.signals], ["working", "thinking", "done"])
		for signal in self.signals:
			self.assertEqual(list(signal["message"]), list(PAYLOAD_KEYS))
			self.assertEqual(len(signal["message"]), 7)

	def test_thinking_not_repeated_after_thinking(self):
		status = self._status()

		status.thinking()
		status.working("get_ticket")
		status.thinking()
		status.thinking()

		self.assertEqual([s["message"]["state"] for s in self.signals], ["working", "thinking"])

	def test_working_silent_when_inactive_or_finished(self):
		silent = RunStatus("HD-TICKET-1", "run1", "  ")
		silent.start()
		silent.working("get_ticket")
		finished = self._status()
		finished.done()
		self.signals.clear()
		finished.working("get_ticket")

		self.assertEqual(self.signals, [])

	def test_take_errors_returns_and_clears(self):
		status = self._status()

		with patch.object(frappe, "publish_realtime", side_effect=RuntimeError("secret")):
			status.working("get_ticket")

		self.assertEqual(status.take_errors(), ["status_working: RuntimeError"])
		self.assertEqual(status.take_errors(), [])

	def test_emit_never_raises_and_records_class(self):
		marker = "MARKERXYZ"
		failures = {
			"publish_realtime": (
				RuntimeError,
				patch.object(frappe, "publish_realtime", side_effect=RuntimeError(marker)),
			),
			"get_fullname": (
				KeyError,
				patch("erp_ai.agent.run_status.get_fullname", side_effect=KeyError(marker)),
			),
			"get_doc_room": (
				ValueError,
				patch("erp_ai.agent.run_status.get_doc_room", side_effect=ValueError(marker)),
			),
		}
		for name, (error_class, failure) in failures.items():
			with self.subTest(name):
				status = RunStatus("HD-TICKET-1", "run1", "Đang suy nghĩ…")

				with failure:
					status.start()
					status.working("get_ticket")
					status.thinking()
					status.done()

				errors = status.take_errors()
				self.assertEqual(
					errors,
					[
						f"status_{state}: {error_class.__name__}"
						for state in ("thinking", "working", "thinking", "done")
					],
				)
				self.assertNotIn(marker, " ".join(errors))
				self.assertEqual(status.signal_count, 4)
				self.assertEqual(self.signals, [])

	def test_done_sent_after_failed_start(self):
		status = RunStatus("HD-TICKET-1", "run1", "Đang suy nghĩ…")

		with patch.object(frappe, "publish_realtime", side_effect=RuntimeError("down")):
			status.start()
		status.done()

		self.assertEqual(status.take_errors(), ["status_thinking: RuntimeError"])
		self.assertEqual([s["message"]["state"] for s in self.signals], ["done"])
		self.assertTrue(status.finished)

	def test_stop_emits_one_done_only_before_start(self):
		# ADR-008 Amendment 1 (CHG-009): an early stop sends exactly one empty `done` for its run_id; a run that started
		# ends with done(), so stop() after start() sends nothing; no text, no signal
		stopped = RunStatus("HD-TICKET-1", "run-stopped", "Đang suy nghĩ…")

		stopped.stop()
		stopped.stop()
		stopped.done()

		self.assertEqual(
			[(s["message"]["state"], s["message"]["text"], s["message"]["run_id"]) for s in self.signals],
			[("done", "", "run-stopped")],
		)
		self.assertTrue(stopped.finished)
		started = self._status()
		started.stop()
		self.assertEqual(self.signals, [])
		started.done()
		self.assertEqual([s["message"]["state"] for s in self.signals], ["done"])
		self.signals.clear()
		RunStatus("HD-TICKET-1", "run-silent", "   ").stop()
		self.assertEqual(self.signals, [])
