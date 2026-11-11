from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import runner
from erp_ai.constants import SETTING_DOCTYPE
from erp_ai.test_utils import FakeGateway, make_model_result

RUN_FOR_TICKET_PATH = "erp_ai.agent.runner.run_for_ticket"


def _setting_value(enabled):
	real_get_single_value = frappe.db.get_single_value

	def fake(doctype, fieldname=None, *args, **kwargs):
		if doctype == SETTING_DOCTYPE:
			return enabled
		return real_get_single_value(doctype, fieldname, *args, **kwargs)

	return fake


def _setting_doctype_exists():
	"""The DocType is created in T9; until then pretend it exists so the handler reads the setting."""
	real_exists = frappe.db.exists

	def fake(dt, dn=None, *args, **kwargs):
		if dt == "DocType" and dn == SETTING_DOCTYPE:
			return SETTING_DOCTYPE
		return real_exists(dt, dn, *args, **kwargs)

	return fake


def _agent_calls(enqueue_mock):
	return [call for call in enqueue_mock.call_args_list if call.args and call.args[0] == RUN_FOR_TICKET_PATH]


class TestTicketHandlers(FrappeTestCase):
	def test_new_ticket_enqueues_one_agent_job(self):
		fake_gateway = FakeGateway()
		with (
			patch.object(frappe.db, "exists", side_effect=_setting_doctype_exists()),
			patch.object(frappe.db, "get_single_value", side_effect=_setting_value(1)),
			patch("erp_ai.gateway.call_model", fake_gateway),
			patch.object(frappe, "enqueue") as enqueue,
		):
			ticket = make_ticket(subject="erp_ai T1 enqueue")

		agent_calls = _agent_calls(enqueue)
		self.assertEqual(len(agent_calls), 1)
		kwargs = agent_calls[0].kwargs
		self.assertEqual(kwargs["queue"], "long")
		self.assertEqual(kwargs["timeout"], 600)
		self.assertIs(kwargs["enqueue_after_commit"], True)
		self.assertIs(kwargs["deduplicate"], True)
		self.assertEqual(kwargs["ticket_name"], ticket.name)
		self.assertEqual(kwargs["trigger"], "ticket_insert")
		self.assertEqual(kwargs["job_id"], f"erp_ai::{ticket.name}::ticket_insert")
		self.assertEqual(fake_gateway.call_count, 0)

	def test_new_ticket_with_agent_disabled_enqueues_nothing(self):
		with (
			patch.object(frappe.db, "exists", side_effect=_setting_doctype_exists()),
			patch.object(frappe.db, "get_single_value", side_effect=_setting_value(0)),
			patch.object(frappe, "enqueue") as enqueue,
		):
			make_ticket(subject="erp_ai T1 disabled")

		self.assertEqual(_agent_calls(enqueue), [])

	def test_ticket_insert_without_setting_doctype_enqueues_nothing(self):
		real_exists = frappe.db.exists
		real_get_single_value = frappe.db.get_single_value

		def missing_doctype(dt, dn=None, *args, **kwargs):
			if dt == "DocType" and dn == SETTING_DOCTYPE:
				return None
			return real_exists(dt, dn, *args, **kwargs)

		def must_not_read(doctype, fieldname=None, *args, **kwargs):
			if doctype == SETTING_DOCTYPE:
				raise AssertionError("setting must not be read when its DocType is absent")
			return real_get_single_value(doctype, fieldname, *args, **kwargs)

		with (
			patch.object(frappe.db, "exists", side_effect=missing_doctype),
			patch.object(frappe.db, "get_single_value", side_effect=must_not_read),
			patch.object(frappe, "enqueue") as enqueue,
		):
			ticket = make_ticket(subject="erp_ai T1 setting doctype missing")

		self.assertTrue(real_exists("HD Ticket", ticket.name))
		self.assertEqual(_agent_calls(enqueue), [])

	def test_saving_ticket_never_calls_the_model(self):
		fake_gateway = FakeGateway()
		with (
			patch.object(frappe.db, "exists", side_effect=_setting_doctype_exists()),
			patch.object(frappe.db, "get_single_value", side_effect=_setting_value(1)),
			patch("erp_ai.gateway.call_model", fake_gateway),
			patch.object(frappe, "enqueue"),
		):
			ticket = make_ticket(subject="erp_ai T1 no model call")
			ticket.reload()
			ticket.subject = "erp_ai T1 no model call (edited)"
			ticket.save(ignore_permissions=True)

		self.assertEqual(fake_gateway.call_count, 0)

	def test_run_for_ticket_calls_classify_once(self):
		fake_gateway = FakeGateway(make_model_result(text="{}"))
		with (
			patch.object(frappe.db, "get_single_value", side_effect=_setting_value(0)),
			patch("erp_ai.gateway.call_model", fake_gateway),
		):
			ticket = make_ticket(subject="erp_ai T1 runner")
			runner.run_for_ticket(ticket.name, "ticket_insert")

		self.assertEqual(fake_gateway.call_count, 1)
		call = fake_gateway.calls[0]
		self.assertEqual(call["task"], "classify")
		self.assertEqual(call["max_tokens"], 400)
		self.assertTrue(call["system"])
		self.assertTrue(call["messages"])
