from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent

from erp_ai import change_decision
from erp_ai.agent import change_link
from erp_ai.constants import (
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
)
from erp_ai.test_utils import make_change_proposal

INSTRUCTOR = "decision.instructor@example.com"
PLAIN = "decision.plain@example.com"
RUN_CHANGE = "erp_ai.agent.changes.apply_job.run_change"


class TestChangeDecision(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		for email in (INSTRUCTOR, PLAIN):
			create_agent(email)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		enqueue = patch("frappe.enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)
		page = patch.object(frappe, "respond_as_web_page")
		self.page = page.start()
		self.addCleanup(page.stop)
		self.addCleanup(frappe.local.response.pop, "location", None)
		self.addCleanup(frappe.local.response.pop, "type", None)
		self.proposal = make_change_proposal()

	def signature(self, action, name=None):
		return change_link.decision_path(name or self.proposal.name, action).rsplit("&_signature=", 1)[1]

	def decide(self, user, action, signature=None, name=None):
		frappe.set_user(user)
		try:
			change_decision.decide(
				name=name or self.proposal.name,
				action=action,
				_signature=self.signature(action) if signature is None else signature,
			)
		finally:
			frappe.set_user("Administrator")

	def status(self):
		return frappe.db.get_value(PROPOSAL_DOCTYPE, self.proposal.name, "change_status")

	def jobs(self):
		return [call for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_CHANGE]

	def assertRefused(self, phrase):
		self.assertEqual(self.status(), CHANGE_STATUS_PENDING)
		self.assertEqual(self.jobs(), [])
		self.page.assert_called_once()
		self.assertIn(phrase, self.page.call_args.args[1])
		self.assertNotEqual(frappe.local.response.get("type"), "redirect")

	def test_approve_link_approves_queues_the_job_and_returns_to_the_ticket(self):
		self.decide(INSTRUCTOR, "approve")

		self.assertEqual(self.status(), CHANGE_STATUS_APPROVED)
		(job,) = self.jobs()
		self.assertEqual(
			(job.kwargs["proposal_name"], job.kwargs["action"]), (self.proposal.name, "apply")
		)
		self.assertEqual(
			frappe.db.get_value(PROPOSAL_DOCTYPE, self.proposal.name, "decided_by"), INSTRUCTOR
		)
		self.assertEqual(frappe.local.response["type"], "redirect")
		self.assertEqual(frappe.local.response["location"], f"/helpdesk/tickets/{self.proposal.ticket}")
		self.page.assert_not_called()

	def test_reject_link_rejects_without_a_job(self):
		self.decide(INSTRUCTOR, "reject")

		self.assertEqual(self.status(), CHANGE_STATUS_REJECTED)
		self.assertEqual(self.jobs(), [])
		self.assertEqual(frappe.local.response["location"], f"/helpdesk/tickets/{self.proposal.ticket}")

	def test_wrong_or_missing_signature_changes_nothing(self):
		for signature in ("0" * 64, "", self.signature("reject")):
			self.page.reset_mock()
			self.decide(INSTRUCTOR, "approve", signature=signature)
			self.assertRefused("không hợp lệ")

	def test_signature_of_another_proposal_is_refused(self):
		other = make_change_proposal()
		self.decide(INSTRUCTOR, "approve", signature=self.signature("approve", other.name))
		self.assertRefused("không hợp lệ")

	def test_unknown_action_is_refused(self):
		self.decide(INSTRUCTOR, "undo", signature="0" * 64)
		self.assertRefused("không hợp lệ")

	def test_user_without_role_and_administrator_are_refused_with_a_valid_link(self):
		for user in (PLAIN, "Administrator"):
			self.page.reset_mock()
			self.decide(user, "approve")
			self.assertRefused("ERP AI Instructor")

	def test_second_click_reports_the_state_and_queues_nothing_more(self):
		self.decide(INSTRUCTOR, "approve")
		self.decide(INSTRUCTOR, "approve")

		self.assertEqual(len(self.jobs()), 1)
		self.page.assert_called_once()
		self.assertIn(CHANGE_STATUS_APPROVED, self.page.call_args.args[1])

	def test_method_is_get_only_and_never_guest(self):
		fn = change_decision.decide
		self.assertIn(fn, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["GET"])
		self.assertNotIn(fn, frappe.guest_methods)
