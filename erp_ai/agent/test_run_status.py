from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.run_status import (
	CLASSIFY_STEP,
	FALLBACK_WORK_LABEL,
	PAYLOAD_KEYS,
	WORK_LABELS,
	WORKING_TEXT,
	RunStatus,
)
from erp_ai.agent.tools.registry import get_tool_schemas
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
		granted = {schema["name"] for schema in get_tool_schemas(LEVELS[-1], True)}

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
