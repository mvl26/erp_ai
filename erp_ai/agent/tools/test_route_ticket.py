from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import RouteDecision
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.agent.tools.route_ticket import apply_route
from erp_ai.constants import AGENT_USER, CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN
from erp_ai.test_utils import PREFIX, make_active_agent, make_sla, make_team, pin_agent_roles

SCORE_FIELDS = ("ai_complexity", "ai_importance", "ai_score_reason")
ROW_FIELDS = (
	"ticket_type",
	"agent_group",
	"priority",
	"ai_confidence",
	*SCORE_FIELDS,
	"ai_classified_by",
	"ai_updated_at",
)
REASON_TEXT = "ERPAI-TEST lý do chấm điểm"
CUSTOMER = f"{PREFIX}customer@example.com"


def _make_customer() -> str:
	if not frappe.db.exists("User", CUSTOMER):
		frappe.get_doc(
			{"doctype": "User", "email": CUSTOMER, "first_name": "ERPAI", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", CUSTOMER).add_roles("HD Customer")
	return CUSTOMER


class RouteTicketTestCase(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# Cleanups run LIFO: set_user, then rollback, then the stale Redis rule map of the self-made team.
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.team = make_team(self)
		self.ticket_type = f"{PREFIX}Loại-{frappe.generate_hash(length=6)}"
		frappe.get_doc({"doctype": "HD Ticket Type", "name": self.ticket_type}).insert(
			ignore_permissions=True
		)

	def _ticket(self, **fields) -> str:
		return make_ticket(subject=f"{PREFIX}phiếu", raised_by=CUSTOMER, **fields).name

	def _ctx(self, ticket: str) -> ToolContext:
		return ToolContext(
			ticket_name=ticket,
			effective_level="L1",
			instructor=None,
			run_id="run-t14",
			category_mapping={},
			agent_user=AGENT_USER,
		)

	def _decision(self, **fields) -> RouteDecision:
		values = {
			"ticket_type": self.ticket_type,
			"agent_group": self.team,
			"priority": "Medium",
			"assignee": None,
			"needs_task": False,
			"notes": (),
		}
		values.update(fields)
		return RouteDecision(**values)

	def _classification(self, **fields) -> Classification:
		values = {
			"category": "A",
			"confidence": "Cao",
			"complexity": 2,
			"importance": 3,
			"score_reason": REASON_TEXT,
		}
		values.update(fields)
		return Classification(**values)

	def _row(self, ticket: str) -> dict:
		return frappe.db.get_value("HD Ticket", ticket, ROW_FIELDS, as_dict=True)

	def _apply_as_agent(self, ticket: str, decision=None, classification=None) -> dict:
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		return apply_route(
			decision or self._decision(), classification or self._classification(), self._ctx(ticket)
		)


class TestApplyRoute(RouteTicketTestCase):
	def test_scores_written_readable_by_agent_role_user(self):
		# Priority is set explicitly so the changed set does not depend on the site's default SLA priority.
		ticket = self._ticket(priority="Low")
		result = self._apply_as_agent(ticket)
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["skipped"], [])
		self.assertEqual(
			result["after"],
			{
				"ticket_type": self.ticket_type,
				"agent_group": self.team,
				"priority": "Medium",
				"ai_confidence": "Cao",
				"ai_complexity": 2,
				"ai_importance": 3,
				"ai_score_reason": REASON_TEXT,
			},
		)
		self.assertEqual(set(result["before"]), set(result["after"]))
		self.assertEqual(result["before"]["priority"], "Low")
		row = self._row(ticket)
		self.assertEqual((row.ai_complexity, row.ai_importance, row.ai_score_reason), (2, 3, REASON_TEXT))
		self.assertEqual(row.ai_classified_by, CLASSIFIED_BY_AI)
		self.assertIsNotNone(row.ai_updated_at)

		# A user holding only the Agent role reads the three score fields.
		reader = make_active_agent(self)
		frappe.set_user(reader)
		self.assertEqual(set(frappe.get_roles(reader)) & {"Agent", "System Manager"}, {"Agent"})
		rows = frappe.get_list("HD Ticket", filters={"name": ticket}, fields=list(SCORE_FIELDS))
		self.assertEqual(
			[(r.ai_complexity, r.ai_importance, r.ai_score_reason) for r in rows], [(2, 3, REASON_TEXT)]
		)

	def test_human_classified_refused(self):
		ticket = self._ticket()
		frappe.db.set_value("HD Ticket", ticket, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		before = self._row(ticket)
		result = self._apply_as_agent(ticket)
		self.assertFalse(result["ok"])
		self.assertTrue(result["reason"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(ticket), before)

	def test_user_without_write_permission_refused(self):
		# The agent holds every permlevel it needs; only the document-level write check says no.
		ticket = self._ticket()
		real = Document.has_permission

		def deny_write(doc, permtype="read", *args, **kwargs):
			return False if permtype == "write" else real(doc, permtype, *args, **kwargs)

		before = self._row(ticket)
		with patch.object(Document, "has_permission", deny_write):
			result = self._apply_as_agent(ticket)
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(ticket), before)

	def test_missing_marker_permission_refused(self):
		# The ticket's customer writes permlevel 0 but holds no permlevel 8: no marker, so no write at all.
		ticket = self._ticket()
		customer = _make_customer()
		before = self._row(ticket)
		frappe.set_user(customer)
		doc = frappe.get_doc("HD Ticket", ticket)
		self.assertTrue(doc.has_permission("write"))
		result = apply_route(self._decision(), self._classification(), self._ctx(ticket))
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(ticket), before)

	def test_marker_write_permission_missing_refused_though_readable(self):
		# Read without write on the marker (design: Agent reads permlevel 8) must still refuse the whole write.
		ticket = self._ticket()
		original = Document.has_permlevel_access_to

		def deny_marker_write(doc, fieldname, df=None, permission_type="read"):
			if permission_type == "write" and fieldname == "ai_classified_by":
				return False
			return original(doc, fieldname, df=df, permission_type=permission_type)

		before = self._row(ticket)
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		doc = frappe.get_doc("HD Ticket", ticket)
		self.assertTrue(doc.has_permlevel_access_to("ai_classified_by", permission_type="read"))
		with patch.object(Document, "has_permlevel_access_to", deny_marker_write):
			result = apply_route(self._decision(), self._classification(), self._ctx(ticket))
		self.assertFalse(result["ok"])
		self.assertIn("ai_classified_by", result["reason"])
		self.assertEqual(self._row(ticket), before)

	def test_missing_field_permission_skipped(self):
		ticket = self._ticket(priority="Low")
		original = Document.has_permlevel_access_to

		def deny_priority_and_reason(doc, fieldname, df=None, permission_type="read"):
			if permission_type == "write" and fieldname in ("priority", "ai_score_reason"):
				return False
			return original(doc, fieldname, df=df, permission_type=permission_type)

		with patch.object(Document, "has_permlevel_access_to", deny_priority_and_reason):
			result = self._apply_as_agent(ticket)
		self.assertTrue(result["ok"], result)
		skipped = {item["field"] for item in result["skipped"]}
		self.assertEqual(skipped, {"priority", "ai_score_reason"})
		self.assertNotIn("priority", result["after"])
		self.assertNotIn("ai_score_reason", result["after"])
		self.assertNotIn("priority", result["before"])
		self.assertEqual(result["after"]["agent_group"], self.team)
		row = self._row(ticket)
		self.assertEqual(row.priority, "Low")
		self.assertFalse(row.ai_score_reason)
		self.assertEqual((row.agent_group, row.ai_complexity, row.ai_importance), (self.team, 2, 3))
		self.assertEqual(row.ai_classified_by, CLASSIFIED_BY_AI)

	def test_value_missing_on_site_not_written(self):
		ticket = self._ticket(priority="Low")
		before = self._row(ticket)
		decision = self._decision(agent_group=f"{PREFIX}Nhóm không có", ticket_type="Loại không có")
		result = self._apply_as_agent(ticket, decision=decision)
		self.assertTrue(result["ok"], result)
		self.assertEqual({item["field"] for item in result["skipped"]}, {"agent_group", "ticket_type"})
		self.assertNotIn("agent_group", result["after"])
		self.assertNotIn("ticket_type", result["after"])
		row = self._row(ticket)
		self.assertEqual((row.agent_group, row.ticket_type), (before.agent_group, before.ticket_type))
		self.assertEqual(row.priority, "Medium")

	def test_unchanged_field_left_out_of_before_after(self):
		ticket = self._ticket(priority="Medium")
		result = self._apply_as_agent(ticket)
		self.assertTrue(result["ok"], result)
		self.assertNotIn("priority", result["before"])
		self.assertNotIn("priority", result["after"])
		self.assertEqual(set(result["before"]), set(result["after"]))
		self.assertEqual(result["after"]["agent_group"], self.team)
		self.assertEqual(self._row(ticket).priority, "Medium")

	def test_before_after_only_changed_fields_and_one_save(self):
		ticket = self._ticket(priority="Low")
		saves = []

		def counting_save(doc, *args, **kwargs):
			saves.append(doc.doctype)
			return original_save(doc, *args, **kwargs)

		original_save = Document.save
		with patch.object(Document, "save", counting_save):
			result = self._apply_as_agent(ticket)
		self.assertEqual(saves.count("HD Ticket"), 1)
		self.assertEqual(result["before"]["priority"], "Low")
		self.assertEqual(result["after"]["priority"], "Medium")
		self.assertEqual(result["before"]["ai_complexity"], 0)

	def test_save_exception_propagates(self):
		ticket = self._ticket()
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		with patch.object(Document, "save", side_effect=frappe.ValidationError("boom")):
			with self.assertRaises(frappe.ValidationError):
				apply_route(self._decision(), self._classification(), self._ctx(ticket))

	def test_e_ticket_still_saved_with_scores(self):
		ticket = self._ticket()
		before = self._row(ticket)
		decision = self._decision(ticket_type=None, agent_group=None, priority=None)
		classification = self._classification(
			category="E", complexity=1, importance=2, score_reason="E có điểm"
		)
		result = self._apply_as_agent(ticket, decision=decision, classification=classification)
		self.assertTrue(result["ok"], result)
		self.assertEqual(
			{item["field"] for item in result["skipped"]}, {"ticket_type", "agent_group", "priority"}
		)
		row = self._row(ticket)
		self.assertEqual((row.ai_complexity, row.ai_importance, row.ai_score_reason), (1, 2, "E có điểm"))
		self.assertEqual(row.ai_classified_by, CLASSIFIED_BY_AI)
		self.assertEqual(
			(row.ticket_type, row.agent_group, row.priority),
			(before.ticket_type, before.agent_group, before.priority),
		)
		self.assertEqual(
			set(result["after"]), {"ai_confidence", "ai_complexity", "ai_importance", "ai_score_reason"}
		)


class TestSlaFromHelpdesk(RouteTicketTestCase):
	def _sla_of(self, ticket: str) -> dict:
		return frappe.db.get_value("HD Ticket", ticket, ["sla", "response_by", "resolution_by"], as_dict=True)

	def test_sla_chosen_by_complexity_condition(self):
		default_sla = make_sla(self, default=True)
		complex_sla = make_sla(self, condition="doc.ai_complexity == 3")
		complex_ticket = self._ticket()
		simple_ticket = self._ticket()
		self.assertTrue(
			self._apply_as_agent(complex_ticket, classification=self._classification(complexity=3))["ok"]
		)
		self.assertTrue(
			self._apply_as_agent(simple_ticket, classification=self._classification(complexity=1))["ok"]
		)
		complex_row, simple_row = self._sla_of(complex_ticket), self._sla_of(simple_ticket)
		self.assertEqual(complex_row.sla, complex_sla)
		self.assertEqual(simple_row.sla, default_sla)
		for row in (complex_row, simple_row):
			self.assertIsNotNone(row.response_by)
			self.assertIsNotNone(row.resolution_by)

	def test_ge_condition_saves_l0_and_new_ticket(self):
		make_sla(self, default=True)
		ge_sla = make_sla(self, condition="doc.ai_complexity >= 3")
		# A new ticket (no score yet) is created with the `>=` condition active, and does not pick that SLA.
		ticket = self._ticket()
		self.assertNotEqual(self._sla_of(ticket).sla, ge_sla)
		# Complexity 0 (apply_route still writes the marker; the real L0 path is T20) saves cleanly and still does not pick it.
		result = self._apply_as_agent(
			ticket, classification=self._classification(complexity=0, importance=0, score_reason="")
		)
		self.assertTrue(result["ok"], result)
		self.assertNotEqual(self._sla_of(ticket).sla, ge_sla)
		# A score of 3 does.
		result = self._apply_as_agent(ticket, classification=self._classification(complexity=3))
		self.assertTrue(result["ok"], result)
		self.assertEqual(self._sla_of(ticket).sla, ge_sla)
