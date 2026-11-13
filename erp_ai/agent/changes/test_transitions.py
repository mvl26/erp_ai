from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import (
	BOT_GIT_EMAIL,
	BOT_GIT_NAME,
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	CHANGE_STEPS,
	COMMAND_TIMEOUT_S,
	CORE_APPS,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	PROPOSAL_DOCTYPE,
	PROPOSAL_TEXT_MAX_CHARS,
	REPLACE_MAX_ITEMS,
	RUN_BACKSTOP_S,
	TITLE_CHANGE_FAILED,
	TRIGGER_CHANGE_ACTION,
)


class TestChangeConstants(FrappeTestCase):
	def test_status_values(self):
		self.assertEqual(
			(
				CHANGE_STATUS_PENDING,
				CHANGE_STATUS_REJECTED,
				CHANGE_STATUS_APPROVED,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				CHANGE_STATUS_FAILED,
				CHANGE_STATUS_STALE,
				CHANGE_STATUS_UNDOING,
				CHANGE_STATUS_UNDONE,
			),
			(
				"Chờ duyệt",
				"Đã từ chối",
				"Đã duyệt",
				"Đang áp dụng",
				"Đã áp dụng",
				"Lỗi",
				"Hết hiệu lực",
				"Đang hoàn tác",
				"Đã hoàn tác",
			),
		)
		self.assertEqual(PROPOSAL_DOCTYPE, "ERP AI Change Proposal")
		self.assertEqual((CHANGE_KIND_CODE, CHANGE_KIND_COMMAND), ("Thay đổi code", "Lệnh bench"))
		self.assertEqual(CHANGE_STEPS, ("propose", "approve", "reject", "apply", "fail", "stale", "undo"))
		self.assertEqual(TRIGGER_CHANGE_ACTION, "change_action")
		self.assertEqual(TITLE_CHANGE_FAILED, "erp_ai: áp dụng thay đổi lỗi")
		self.assertEqual((PROPOSAL_TEXT_MAX_CHARS, REPLACE_MAX_ITEMS), (20000, 10))

	def test_command_timeout_is_job_timeout_minus_margin(self):
		self.assertEqual(COMMAND_TIMEOUT_S, JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S)
		self.assertEqual(COMMAND_TIMEOUT_S, 540)

	def test_run_backstop(self):
		self.assertEqual(RUN_BACKSTOP_S, COMMAND_TIMEOUT_S + JOB_SAFETY_MARGIN_S // 2)
		self.assertEqual(RUN_BACKSTOP_S, 570)

	def test_core_apps_and_bot_identity(self):
		self.assertEqual(CORE_APPS, ("frappe", "erpnext", "helpdesk", "hrms"))
		self.assertNotIn("erp_ai", CORE_APPS)
		self.assertEqual(BOT_GIT_NAME, "ERP AI Agent")
		self.assertEqual(BOT_GIT_EMAIL, "erp-ai-agent@bot.invalid")
		self.assertTrue(BOT_GIT_EMAIL.endswith(".invalid"))
