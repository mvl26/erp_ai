from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.tools import registry, write_ticket
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import AGENT_USER, CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN

AGENT = "t25.agent@example.com"
CUSTOMER = "t25.customer@example.com"
OUTSIDER = "t25.outsider@example.com"
TEAM = "T25 Nhóm"
TICKET_TYPE = "T25 Loại"
MISSING_TYPE = "T25 Loại không tồn tại"
SCHEMA_TYPES = {"string", "integer", "boolean", "array"}
FIELDS = ("ticket_type", "agent_group", "priority", "ai_confidence", "ai_classified_by", "ai_updated_at")


def _make_user(email, *roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "T25", "send_welcome_email": 0}
		).insert()
	if roles:
		frappe.get_doc("User", email).add_roles(*roles)


class TestWriteTicket(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT)
		_make_user(CUSTOMER, "HD Customer")
		_make_user(OUTSIDER)
		if not frappe.db.exists("HD Ticket Type", TICKET_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": TICKET_TYPE}).insert()
		if not frappe.db.exists("HD Team", TEAM):
			frappe.get_doc({"doctype": "HD Team", "team_name": TEAM, "users": [{"user": AGENT}]}).insert()
			self.addCleanup(self._drop_team)
		self.ticket = make_ticket(subject="T25 phiếu", raised_by=CUSTOMER).name
		self.mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High"}}

	def _drop_team(self):
		# HD Team.after_insert makes an Assignment Rule cached in Redis; rollback leaves the cache stale.
		frappe.delete_doc("HD Team", TEAM, force=True)
		frappe.cache.hdel("assignment_rule_map", "HD Ticket")

	def _ctx(self, mapping=None):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=None,
			run_id="run-t25",
			category_mapping=self.mapping if mapping is None else mapping,
			agent_user=AGENT_USER,
		)

	def _row(self):
		return frappe.db.get_value("HD Ticket", self.ticket, [*FIELDS, "status"], as_dict=True)

	def _run(self, user, mapping=None, category="A", confidence="Cao"):
		frappe.set_user(user)
		args = {"category": category, "confidence": confidence}
		return write_ticket.set_classification(args, self._ctx(mapping))

	def test_agent_writes_mapped_fields_and_ai_marks(self):
		before = self._row()
		result = self._run(AGENT)
		self.assertTrue(result["ok"], result)
		row = self._row()
		self.assertEqual((row.ticket_type, row.agent_group, row.priority), (TICKET_TYPE, TEAM, "High"))
		self.assertEqual((row.ai_confidence, row.ai_classified_by), ("Cao", CLASSIFIED_BY_AI))
		self.assertTrue(get_datetime(row.ai_updated_at))
		self.assertEqual(row.status, before.status)
		self.assertEqual(result["skipped"], [])
		self.assertEqual(result["before"]["ticket_type"], before.ticket_type)
		self.assertEqual(
			result["after"],
			{"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High", "ai_confidence": "Cao"},
		)

	def test_write_without_permission_returns_ok_false_unchanged(self):
		before = self._row()
		result = self._run(OUTSIDER)
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(), before)

	def test_field_without_permlevel_access_returns_ok_false_unchanged(self):
		# The ticket's customer may write permlevel 0 but has no access to the permlevel 8 AI fields.
		frappe.set_user(CUSTOMER)
		doc = frappe.get_doc("HD Ticket", self.ticket)
		self.assertTrue(doc.has_permission("write"))
		self.assertFalse(doc.has_permlevel_access_to("ai_confidence", permission_type="write"))
		before = self._row()
		result = self._run(CUSTOMER)
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(), before)

	def test_write_denied_by_document_permission_alone_returns_ok_false_unchanged(self):
		# The agent holds every permlevel it needs; only the document-level write check says no.
		real = Document.has_permission

		def deny_write(doc, permtype="read", *args, **kwargs):
			return False if permtype == "write" else real(doc, permtype, *args, **kwargs)

		before = self._row()
		with patch.object(Document, "has_permission", deny_write):
			result = self._run(AGENT)
		self.assertFalse(result["ok"])
		self.assertLessEqual(len(result["reason"]), 200)
		self.assertEqual(self._row(), before)

	def test_permlevel_denied_on_one_mapped_field_writes_nothing(self):
		real = Document.has_permlevel_access_to

		def deny_priority(doc, fieldname=None, df=None, permission_type="read"):
			if fieldname == "priority":
				return False
			return real(doc, fieldname, df, permission_type)

		before = self._row()
		with patch.object(Document, "has_permlevel_access_to", deny_priority):
			result = self._run(AGENT)
		self.assertFalse(result["ok"])
		self.assertEqual(self._row(), before)

	def test_human_classified_ticket_is_not_overwritten(self):
		frappe.db.set_value("HD Ticket", self.ticket, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		frappe.db.set_value("HD Ticket", self.ticket, "priority", "Low")
		before = self._row()
		result = self._run(AGENT)
		self.assertFalse(result["ok"])
		self.assertIn("người đã phân loại", result["reason"])
		self.assertEqual(self._row(), before)

	def test_mapping_to_missing_value_skips_field(self):
		mapping = {"A": {"ticket_type": MISSING_TYPE, "agent_group": TEAM, "priority": "High"}}
		before = self._row()
		result = self._run(AGENT, mapping)
		self.assertTrue(result["ok"], result)
		self.assertEqual([s["field"] for s in result["skipped"]], ["ticket_type"])
		self.assertTrue(result["skipped"][0]["reason"])
		row = self._row()
		self.assertEqual(row.ticket_type, before.ticket_type)
		self.assertEqual((row.agent_group, row.priority), (TEAM, "High"))
		self.assertEqual(row.ai_classified_by, CLASSIFIED_BY_AI)

	def test_category_without_mapped_values_writes_nothing(self):
		before = self._row()
		result = self._run(AGENT, {"A": {"ticket_type": "", "agent_group": "", "priority": ""}})
		self.assertTrue(result["ok"], result)
		self.assertEqual({s["field"] for s in result["skipped"]}, {"ticket_type", "agent_group", "priority"})
		self.assertEqual(self._row(), before)

	def test_urgent_subject_tag_forces_urgent_priority(self):
		frappe.db.set_value("HD Ticket", self.ticket, "subject", "[GẤP] máy in hỏng")
		self.assertTrue(self._run(AGENT)["ok"])
		self.assertEqual(self._row().priority, "Urgent")

	def test_handler_does_not_commit(self):
		with patch.object(frappe.db, "commit") as commit:
			self._run(AGENT)
		commit.assert_not_called()

	def test_tool_spec_schema_takes_no_doctype_or_field_names(self):
		self.assertEqual([spec.name for spec in write_ticket.TOOLS], ["set_classification"])
		spec = write_ticket.TOOLS[0]
		self.assertEqual(spec.group, "ticket_write")
		self.assertIs(spec.handler, write_ticket.set_classification)
		input_schema = spec.schema["input_schema"]
		self.assertEqual(set(input_schema["properties"]), {"category", "confidence"})
		self.assertEqual(set(input_schema["required"]), {"category", "confidence"})
		self.assertEqual(input_schema["properties"]["category"]["enum"], list("ABCDEF"))
		self.assertEqual(input_schema["properties"]["confidence"]["enum"], ["Cao", "Trung bình", "Thấp"])
		self.assertTrue({p["type"] for p in input_schema["properties"].values()} <= SCHEMA_TYPES)

	def test_execute_tool_rejects_field_names_and_runs_handler(self):
		frappe.set_user(AGENT)
		with patch.object(registry, "_all_specs", lambda: write_ticket.TOOLS):
			bad = execute_tool(
				"set_classification",
				{"category": "A", "confidence": "Cao", "fieldname": "status", "doctype": "User"},
				self._ctx(),
			)
			self.assertFalse(bad["ok"])
			self.assertFalse(self._row().ai_classified_by)
			ok = execute_tool("set_classification", {"category": "A", "confidence": "Cao"}, self._ctx())
		self.assertTrue(ok["ok"], ok)
