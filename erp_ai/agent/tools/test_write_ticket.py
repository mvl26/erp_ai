import itertools
import json
import re
from unittest.mock import MagicMock, call, patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import escape_html, get_datetime, now_datetime
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent import policy, site_facts
from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import decide_route
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools import registry, write_ticket
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_AI,
	CLASSIFIED_BY_HUMAN,
	ROLE_AGENT,
)
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

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
	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		# Nothing may have been committed: the team and the ticket types must be gone after the rollback.
		leftovers = [
			(doctype, name)
			for doctype, name in (("HD Team", TEAM), ("HD Ticket Type", TICKET_TYPE), ("User", AGENT))
			if frappe.db.exists(doctype, name)
		]
		assert not leftovers, f"test data was committed: {leftovers}"

	def setUp(self):
		# Registered first so it is undone last: the rollback cleanup below runs while commits are still guarded.
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# FrappeTestCase rolls back only after the whole class: undo each test. Cleanups run LIFO:
		# set_user, then rollback, then the stale Redis rule map (HD Team.after_insert caches an Assignment Rule).
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
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
		self.ticket = make_ticket(subject="T25 phiếu", raised_by=CUSTOMER).name
		self.mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High"}}

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
		started = now_datetime().replace(microsecond=0)
		result = self._run(AGENT_USER)
		self.assertTrue(result["ok"], result)
		row = self._row()
		self.assertEqual((row.ticket_type, row.agent_group, row.priority), (TICKET_TYPE, TEAM, "High"))
		self.assertEqual((row.ai_confidence, row.ai_classified_by), ("Cao", CLASSIFIED_BY_AI))
		self.assertIsNotNone(row.ai_updated_at)
		self.assertGreaterEqual(row.ai_updated_at, started)
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
		# The ticket's customer may write permlevel 0 but not the higher-permlevel fields; the refusal comes at ticket_type.
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

	def test_permlevel_denied_on_one_written_field_writes_nothing(self):
		real = Document.has_permlevel_access_to
		for denied in ("priority", "ai_classified_by", "ai_updated_at"):
			with self.subTest(denied=denied):

				def deny_one(doc, fieldname=None, df=None, permission_type="read", denied=denied):
					if fieldname == denied:
						return False
					return real(doc, fieldname, df, permission_type)

				before = self._row()
				with patch.object(Document, "has_permlevel_access_to", deny_one):
					result = self._run(AGENT)
				self.assertFalse(result["ok"])
				self.assertIn(denied, result["reason"])
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
		result = self._run(AGENT_USER, mapping)
		self.assertTrue(result["ok"], result)
		self.assertEqual([s["field"] for s in result["skipped"]], ["ticket_type"])
		self.assertTrue(result["skipped"][0]["reason"])
		row = self._row()
		self.assertEqual(row.ticket_type, before.ticket_type)
		self.assertEqual((row.agent_group, row.priority), (TEAM, "High"))
		self.assertEqual(row.ai_classified_by, CLASSIFIED_BY_AI)

	def test_mapping_with_none_value_skips_field_with_reason(self):
		mapping = {"A": {"ticket_type": None, "agent_group": TEAM, "priority": "High"}}
		result = self._run(AGENT, mapping)
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["skipped"], [{"field": "ticket_type", "reason": "ánh xạ không có giá trị"}])

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
		self.assertEqual(
			[spec.name for spec in write_ticket.TOOLS],
			["set_classification", "set_resolution_hint", "post_comment", "create_task"],
		)
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


T26_AGENT = "erpai-test-t26.agent@example.com"
T26_CUSTOMER = "erpai-test-t26.customer@example.com"
T26_OUTSIDER = "erpai-test-t26.outsider@example.com"
T26_AGENT_ONLY = "erpai-test-t26.agent-only@example.com"
T26_INSTRUCTOR = "erpai-test-t26.instructor@example.com"
HINT_FIELD = "ai_resolution_hint"
# AC-63 (T167): every create_task call carries a positive hour estimate.
TASK_ARGS = {"subject": "s", "description": "d", "expected_hours": 1}


def _comment_count():
	return frappe.db.count("Comment", {"reference_doctype": "HD Ticket"})


class TestWriteTicketTools(FrappeTestCase):
	"""set_resolution_hint, post_comment and create_task (T26). Nothing here may commit."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(T26_AGENT)
		# The production agent has only ROLE_AGENT + Agent: Task create comes from the if_owner Custom DocPerm.
		_make_user(T26_AGENT, ROLE_AGENT)
		_make_user(T26_AGENT_ONLY, "Agent")
		_make_user(T26_CUSTOMER, "HD Customer")
		_make_user(T26_OUTSIDER)
		self.ticket = make_ticket(subject="ERPAI-TEST-T26 phiếu", raised_by=T26_CUSTOMER).name

	def _ctx(self, instructor=T26_INSTRUCTOR):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=instructor,
			run_id="run-t26",
			category_mapping={},
			agent_user=AGENT_USER,
		)

	def _hint(self):
		return frappe.db.get_value("HD Ticket", self.ticket, HINT_FIELD)

	def _call(self, handler, user, args, ctx=None):
		frappe.set_user(user)
		return handler(args, ctx or self._ctx())

	def _assert_refused(self, result):
		self.assertFalse(result["ok"], result)
		self.assertTrue(result["reason"])
		self.assertLessEqual(len(result["reason"]), 200)

	# set_resolution_hint

	def test_set_resolution_hint_writes_hint_and_returns_before_after(self):
		before = self._hint()
		result = self._call(write_ticket.set_resolution_hint, T26_AGENT, {"text": "Khởi động lại máy in"})
		self.assertTrue(result["ok"], result)
		self.assertEqual(self._hint(), "Khởi động lại máy in")
		self.assertEqual(result["before"], before)
		self.assertEqual(result["after"], "Khởi động lại máy in")

	def test_set_resolution_hint_returns_the_stored_value_as_after(self):
		# Text Editor values are sanitized on save: `after` must be what was stored, not the raw input.
		result = self._call(
			write_ticket.set_resolution_hint, T26_AGENT, {"text": "Khởi động <script>alert(1)</script>lại"}
		)
		self.assertTrue(result["ok"], result)
		self.assertNotIn("<script", self._hint())
		self.assertEqual(result["after"], self._hint())

	def test_set_resolution_hint_without_write_permission_returns_ok_false_unchanged(self):
		before = self._hint()
		result = self._call(write_ticket.set_resolution_hint, T26_OUTSIDER, {"text": "x"})
		self._assert_refused(result)
		self.assertEqual(self._hint(), before)

	def test_set_resolution_hint_denied_by_document_permission_alone(self):
		real = Document.has_permission

		def deny_write(doc, permtype="read", *args, **kwargs):
			return False if permtype == "write" else real(doc, permtype, *args, **kwargs)

		before = self._hint()
		with patch.object(Document, "has_permission", deny_write):
			result = self._call(write_ticket.set_resolution_hint, T26_AGENT, {"text": "x"})
		self._assert_refused(result)
		self.assertEqual(self._hint(), before)

	def test_set_resolution_hint_without_permlevel_access_returns_ok_false_unchanged(self):
		# The customer may write the ticket (permlevel 0) but not the permlevel field of the hint.
		frappe.set_user(T26_CUSTOMER)
		doc = frappe.get_doc("HD Ticket", self.ticket)
		self.assertTrue(doc.has_permission("write"))
		self.assertFalse(doc.has_permlevel_access_to(HINT_FIELD, permission_type="write"))
		before = self._hint()
		result = self._call(write_ticket.set_resolution_hint, T26_CUSTOMER, {"text": "x"})
		self._assert_refused(result)
		self.assertIn(HINT_FIELD, result["reason"])
		self.assertEqual(self._hint(), before)

	# post_comment

	def test_post_comment_creates_core_comment_owned_by_agent(self):
		before = _comment_count()
		legacy_before = frappe.db.count("HD Ticket Comment")
		result = self._call(write_ticket.post_comment, T26_AGENT, {"content": "Đã nhận phiếu"})
		self.assertTrue(result["ok"], result)
		self.assertEqual(_comment_count(), before + 1)
		self.assertEqual(frappe.db.count("HD Ticket Comment"), legacy_before)
		comment = frappe.db.get_value(
			"Comment",
			result["comment"],
			["comment_type", "reference_doctype", "reference_name", "owner", "content"],
			as_dict=True,
		)
		self.assertEqual(comment.comment_type, "Comment")
		self.assertEqual(comment.reference_doctype, "HD Ticket")
		self.assertEqual(comment.reference_name, self.ticket)
		self.assertEqual(comment.owner, T26_AGENT)
		self.assertIn("Đã nhận phiếu", comment.content)

	def test_post_comment_without_ticket_access_returns_ok_false_no_comment(self):
		before = _comment_count()
		result = self._call(write_ticket.post_comment, T26_OUTSIDER, {"content": "x"})
		self._assert_refused(result)
		self.assertEqual(_comment_count(), before)

	def test_post_comment_denied_by_ticket_read_permission_alone(self):
		real = Document.has_permission

		def deny_read(doc, permtype="read", *args, **kwargs):
			return False if permtype == "read" else real(doc, permtype, *args, **kwargs)

		before = _comment_count()
		with patch.object(Document, "has_permission", deny_read):
			result = self._call(write_ticket.post_comment, T26_AGENT, {"content": "x"})
		self._assert_refused(result)
		self.assertEqual(_comment_count(), before)

	def test_post_comment_denied_by_comment_create_permission_alone(self):
		real = frappe.has_permission

		def deny_comment_create(doctype=None, ptype="read", *args, **kwargs):
			if doctype == "Comment" and ptype == "create":
				return False
			return real(doctype, ptype, *args, **kwargs)

		before = _comment_count()
		with patch.object(frappe, "has_permission", deny_comment_create):
			result = self._call(write_ticket.post_comment, T26_AGENT, {"content": "x"})
		self._assert_refused(result)
		self.assertEqual(_comment_count(), before)

	def test_post_comment_refused_by_new_comment_returns_ok_false(self):
		# new_comment itself refuses non-agents; the refusal must come back as ok=false, not an exception.
		before = _comment_count()
		with patch.object(Document, "has_permission", lambda doc, *args, **kwargs: True):
			with patch.object(frappe, "has_permission", lambda *args, **kwargs: True):
				result = self._call(write_ticket.post_comment, T26_OUTSIDER, {"content": "x"})
		self._assert_refused(result)
		self.assertEqual(_comment_count(), before)

	# create_task

	def test_create_task_creates_task_with_ticket_link_in_first_line(self):
		before = frappe.db.count("Task")
		args = {"subject": "ERPAI-TEST-T26 việc", "description": "Kiểm tra máy in", "expected_hours": 2}
		result = self._call(write_ticket.create_task, T26_AGENT, args)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.count("Task"), before + 1)
		task = frappe.db.get_value("Task", result["task"], ["subject", "description", "owner"], as_dict=True)
		self.assertEqual(task.subject, args["subject"])
		self.assertEqual(task.owner, T26_AGENT)
		first_line = task.description.splitlines()[0]
		self.assertIn(self.ticket, first_line)
		self.assertIn(f"/helpdesk/tickets/{self.ticket}", first_line)
		self.assertIn("Kiểm tra máy in", task.description)

	def test_create_task_description_is_html_with_clickable_link_and_separated_text(self):
		args = {
			"subject": "ERPAI-TEST-T26 việc",
			"description": "Dòng 1\nDòng 2 <b>x</b>",
			"expected_hours": 2,
		}
		result = self._call(write_ticket.create_task, T26_AGENT, args)
		self.assertTrue(result["ok"], result)
		description = frappe.db.get_value("Task", result["task"], "description")
		self.assertIn(f'<a href="/helpdesk/tickets/{self.ticket}"', description)
		self.assertTrue(description.startswith("<p>"), description)
		self.assertIn("Dòng 1<br>Dòng 2", description)
		self.assertNotIn("<b>x</b>", description)
		self.assertLess(description.index("/helpdesk/tickets/"), description.index("Dòng 1"))

	def test_create_task_without_task_role_perm_for_agent_only_user_is_refused(self):
		before = frappe.db.count("Task")
		result = self._call(write_ticket.create_task, T26_AGENT_ONLY, TASK_ARGS)
		self._assert_refused(result)
		self.assertIn("Task", result["reason"])
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_requires_instructor(self):
		before = frappe.db.count("Task")
		args = {"subject": "ERPAI-TEST-T26 việc", "description": "x", "expected_hours": 2}
		result = self._call(write_ticket.create_task, T26_AGENT, args, self._ctx(instructor=None))
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_without_task_doctype_returns_ok_false(self):
		real = frappe.db.exists

		def no_task_doctype(dt, *args, **kwargs):
			if dt == "DocType" and args and args[0] == "Task":
				return None
			return real(dt, *args, **kwargs)

		before = frappe.db.count("Task")
		with patch.object(frappe.db, "exists", no_task_doctype):
			result = self._call(write_ticket.create_task, T26_AGENT, TASK_ARGS)
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_without_task_create_permission_returns_ok_false(self):
		real = frappe.has_permission

		def deny_task_create(doctype=None, ptype="read", *args, **kwargs):
			if doctype == "Task" and ptype == "create":
				return False
			return real(doctype, ptype, *args, **kwargs)

		before = frappe.db.count("Task")
		with patch.object(frappe, "has_permission", deny_task_create):
			result = self._call(write_ticket.create_task, T26_AGENT, TASK_ARGS)
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_without_ticket_access_returns_ok_false(self):
		_make_user(T26_OUTSIDER, "Projects User")
		before = frappe.db.count("Task")
		result = self._call(write_ticket.create_task, T26_OUTSIDER, TASK_ARGS)
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	# shared

	def test_handlers_do_not_commit(self):
		with patch.object(frappe.db, "commit") as commit:
			self._call(write_ticket.set_resolution_hint, T26_AGENT, {"text": "x"})
			self._call(write_ticket.post_comment, T26_AGENT, {"content": "x"})
			self._call(write_ticket.create_task, T26_AGENT, TASK_ARGS)
		commit.assert_not_called()

	def test_new_tool_schemas_take_no_doctype_or_field_names(self):
		specs = {spec.name: spec for spec in write_ticket.TOOLS}
		# spec changed (AC-22, T100): the post_comment tool takes a required `kind` and runs post_comment_tool.
		expected = {
			"set_resolution_hint": ("ticket_write", {"text"}, write_ticket.set_resolution_hint),
			"post_comment": ("ticket_write", {"content", "kind"}, write_ticket.post_comment_tool),
			# spec changed (AC-63, T167): a Task needs a positive hour estimate, a JSON number.
			"create_task": (
				"task_write",
				{"subject", "description", "expected_hours"},
				write_ticket.create_task,
			),
		}
		for name, (group, properties, handler) in expected.items():
			with self.subTest(tool=name):
				spec = specs[name]
				self.assertEqual(spec.group, group)
				self.assertIs(spec.handler, handler)
				input_schema = spec.schema["input_schema"]
				self.assertEqual(set(input_schema["properties"]), properties)
				self.assertEqual(set(input_schema["required"]), properties)
				for key, rule in input_schema["properties"].items():
					if key == "expected_hours":
						self.assertEqual(rule, {"type": "number", "exclusiveMinimum": 0})
						continue
					self.assertEqual(rule["type"], "string")
					if key == "kind":
						self.assertEqual(rule["enum"], list(write_ticket.COMMENT_KINDS))
					else:
						self.assertGreaterEqual(rule["minLength"], 1)
		subject_rule = specs["create_task"].schema["input_schema"]["properties"]["subject"]
		self.assertEqual(subject_rule["maxLength"], 140)
		content_rule = specs["post_comment"].schema["input_schema"]["properties"]["content"]
		self.assertEqual(content_rule["maxLength"], 5000)

	def test_execute_tool_rejects_doctype_and_field_names_for_new_tools(self):
		frappe.set_user(T26_AGENT)
		before = frappe.db.count("Task")
		with patch.object(registry, "_all_specs", lambda: write_ticket.TOOLS):
			for name, args in (
				("set_resolution_hint", {"text": "x", "fieldname": "status"}),
				("post_comment", {"content": "x", "kind": "hoi", "doctype": "User"}),
				("create_task", {**TASK_ARGS, "doctype": "User"}),
			):
				with self.subTest(tool=name):
					self.assertFalse(execute_tool(name, args, self._ctx())["ok"])
			no_instructor = execute_tool("create_task", TASK_ARGS, self._ctx(None))
			self.assertFalse(no_instructor["ok"])
		self.assertEqual(frappe.db.count("Task"), before)


class TestCreateTask(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(T26_AGENT)
		_make_user(T26_AGENT, ROLE_AGENT)
		_make_user(T26_CUSTOMER, "HD Customer")
		self.ticket = make_ticket(subject="ERPAI-TEST-T16 phiếu", raised_by=T26_CUSTOMER).name

	def test_sets_ai_ticket(self):
		ctx = ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=T26_INSTRUCTOR,
			run_id="run-t16",
			category_mapping={},
			agent_user=AGENT_USER,
		)
		frappe.set_user(T26_AGENT)
		args = {"subject": "ERPAI-TEST-T16 việc", "description": "mô tả", "expected_hours": 1}
		result = write_ticket.create_task(args, ctx)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Task", result["task"], "ai_ticket"), self.ticket)


T167_PREFIX = "ERPAI-TEST-T167"
NOT_VALID_HOURS = {"ok": False, "reason": "tham số không hợp lệ: expected_hours"}


class TestCreateTaskEstimate(FrappeTestCase):
	"""AC-63 (U4b.md:174, :183): create_task needs a positive hour estimate and stops at the run's Task cap."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		create_agent(T26_AGENT)
		_make_user(T26_AGENT, ROLE_AGENT)
		_make_user(T26_CUSTOMER, "HD Customer")
		self.ticket = make_ticket(subject=f"{T167_PREFIX} phiếu", raised_by=T26_CUSTOMER).name

	def _ctx(self):
		run_id = f"{T167_PREFIX}-{frappe.generate_hash(length=10)}"
		self.addCleanup(lambda: frappe.flags.get("erp_ai_run_tasks", {}).pop(run_id, None))
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=T26_INSTRUCTOR,
			run_id=run_id,
			category_mapping={},
			agent_user=AGENT_USER,
		)

	def _args(self, subject, **extra):
		return {"subject": subject, "description": f"{T167_PREFIX} mô tả", **extra}

	def _create(self, ctx, subject, **extra):
		frappe.set_user(T26_AGENT)
		try:
			return write_ticket.create_task(self._args(subject, **extra), ctx)
		finally:
			frappe.set_user("Administrator")

	def _execute(self, ctx, arguments):
		frappe.set_user(T26_AGENT)
		try:
			with patch.object(registry, "_all_specs", lambda: write_ticket.TOOLS):
				return execute_tool("create_task", arguments, ctx)
		finally:
			frappe.set_user("Administrator")

	def _task_count(self):
		return frappe.db.count("Task", {"ai_ticket": self.ticket})

	def test_three_tasks_with_estimates(self):
		ctx = self._ctx()
		hours = {f"{T167_PREFIX} việc 1": 2, f"{T167_PREFIX} việc 2": 1.5, f"{T167_PREFIX} việc 3": 0.25}
		results = {
			subject: self._create(ctx, subject, expected_hours=estimate)
			for subject, estimate in list(hours.items())[:2]
		}
		# The third goes through the registry: the schema takes the estimate as a JSON number.
		subject = f"{T167_PREFIX} việc 3"
		results[subject] = self._execute(ctx, self._args(subject, expected_hours=hours[subject]))
		for subject, result in results.items():
			with self.subTest(subject):
				self.assertTrue(result["ok"], result)
				task = frappe.db.get_value(
					"Task",
					result["task"],
					["subject", "description", "ai_ticket", "expected_time"],
					as_dict=True,
				)
				self.assertEqual(
					(task.subject, task.ai_ticket, task.expected_time), (subject, self.ticket, hours[subject])
				)
				self.assertIn(f"/helpdesk/tickets/{self.ticket}", task.description)
				self.assertIn(f"{T167_PREFIX} mô tả", task.description)
		self.assertEqual(self._task_count(), 3)
		schema = next(spec for spec in write_ticket.TOOLS if spec.name == "create_task").schema
		self.assertEqual(
			schema["input_schema"]["properties"]["expected_hours"], {"type": "number", "exclusiveMinimum": 0}
		)
		self.assertIn("expected_hours", schema["input_schema"]["required"])

	def test_missing_or_non_positive_estimate_refused(self):
		ctx = self._ctx()
		refused = {
			"missing": {},
			"zero": {"expected_hours": 0},
			"negative": {"expected_hours": -1},
			"text": {"expected_hours": "2"},
			"bool": {"expected_hours": True},
			"not a number": {"expected_hours": float("nan")},
			"infinite": {"expected_hours": float("inf")},
		}
		for case, extra in refused.items():
			with self.subTest(case):
				result = self._create(ctx, f"{T167_PREFIX} việc", **extra)
				self.assertEqual(result, {"ok": False, "reason": write_ticket.REASON_NO_ESTIMATE})
		# Through the registry a missing, text or bool estimate is refused by the schema, a non-positive one by the tool.
		subject = f"{T167_PREFIX} việc"
		self.assertEqual(self._execute(ctx, self._args(subject)), NOT_VALID_HOURS)
		for given in ("2", True):
			with self.subTest(registry=given):
				self.assertEqual(
					self._execute(ctx, self._args(subject, expected_hours=given)), NOT_VALID_HOURS
				)
		for given in (0, -1):
			with self.subTest(registry=given):
				self.assertEqual(
					self._execute(ctx, self._args(subject, expected_hours=given)),
					{"ok": False, "reason": write_ticket.REASON_NO_ESTIMATE},
				)
		self.assertEqual(self._task_count(), 0)
		# A refused call does not count towards the cap: the run still creates its first Task.
		set_agent_settings(max_tasks_per_run=1)
		self.assertTrue(self._create(ctx, subject, expected_hours=1)["ok"])

	def test_eleventh_task_in_run_refused(self):
		self.assertEqual(write_ticket.DEFAULT_MAX_TASKS_PER_RUN, 10)
		with self.subTest("empty setting: the default 10"):
			set_agent_settings(max_tasks_per_run=None)
			ctx = self._ctx()
			for index in range(1, 11):
				self.assertTrue(
					self._create(ctx, f"{T167_PREFIX} việc {index}", expected_hours=1)["ok"], index
				)
			self.assertEqual(
				self._create(ctx, f"{T167_PREFIX} việc 11", expected_hours=1),
				{"ok": False, "reason": write_ticket.REASON_TASK_LIMIT.format(limit=10)},
			)
			self.assertEqual(self._task_count(), 10)
		with self.subTest("configured 3"):
			set_agent_settings(max_tasks_per_run=3)
			ctx = self._ctx()
			for index in range(1, 4):
				self.assertTrue(
					self._create(ctx, f"{T167_PREFIX} cấu hình {index}", expected_hours=1)["ok"], index
				)
			self.assertEqual(
				self._create(ctx, f"{T167_PREFIX} cấu hình 4", expected_hours=1),
				{"ok": False, "reason": write_ticket.REASON_TASK_LIMIT.format(limit=3)},
			)
			self.assertEqual(self._task_count(), 13)
		with self.subTest("a new run_id counts again"):
			other = self._ctx()
			for index in range(1, 4):
				self.assertTrue(
					self._create(other, f"{T167_PREFIX} lần mới {index}", expected_hours=1)["ok"], index
				)
			self.assertFalse(self._create(other, f"{T167_PREFIX} lần mới 4", expected_hours=1)["ok"])
			self.assertEqual(self._task_count(), 16)


class TestSetClassification(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT)
		_make_user(CUSTOMER, "HD Customer")
		if not frappe.db.exists("HD Ticket Type", TICKET_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": TICKET_TYPE}).insert()
		if not frappe.db.exists("HD Team", TEAM):
			frappe.get_doc({"doctype": "HD Team", "team_name": TEAM, "users": [{"user": AGENT}]}).insert()
		self.ticket = make_ticket(subject="T17 phiếu", raised_by=CUSTOMER).name

	def _ctx(self, mapping, routing_config=None):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=None,
			run_id="run-t17",
			category_mapping=mapping,
			agent_user=AGENT_USER,
			routing_config=routing_config,
		)

	def _row(self):
		return frappe.db.get_value(
			"HD Ticket", self.ticket, ["ticket_type", "agent_group", "priority"], as_dict=True
		)

	def test_same_priority_as_route(self):
		mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "Medium"}}
		config = {"importance_priority": {"2": "Urgent"}}
		frappe.db.set_value("HD Ticket", self.ticket, {"ai_complexity": 1, "ai_importance": 2})
		expected = decide_route(
			Classification("A", "Cao", complexity=1, importance=2),
			"T17 phiếu",
			mapping,
			config,
			team_exists=site_facts.team_exists,
			is_excluded_team=policy.is_excluded_team,
			is_active_agent=site_facts.is_active_agent,
		)
		self.assertEqual(expected.priority, "Urgent")
		frappe.set_user(AGENT)
		result = write_ticket.set_classification(
			{"category": "A", "confidence": "Cao"}, self._ctx(mapping, config)
		)
		self.assertTrue(result["ok"], result)
		self.assertEqual(self._row().priority, expected.priority)
		self.assertEqual(result["after"]["priority"], expected.priority)

	def test_de_skips_team_without_department(self):
		mapping = {"D": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High"}}
		before = self._row()
		frappe.set_user(AGENT)
		result = write_ticket.set_classification({"category": "D", "confidence": "Cao"}, self._ctx(mapping))
		self.assertTrue(result["ok"], result)
		row = self._row()
		self.assertEqual(row.agent_group, before.agent_group)
		self.assertEqual((row.ticket_type, row.priority), (TICKET_TYPE, "High"))
		self.assertEqual([item["field"] for item in result["skipped"]], ["agent_group"])
		self.assertEqual(result["skipped"][0]["reason"], "không có bộ phận")

	def test_category_a_without_team_in_mapping_keeps_mapping_reason(self):
		mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": None, "priority": "High"}}
		frappe.set_user(AGENT)
		result = write_ticket.set_classification({"category": "A", "confidence": "Cao"}, self._ctx(mapping))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["skipped"], [{"field": "agent_group", "reason": "ánh xạ không có giá trị"}])


T98_OTHER_TYPE = "T98 Loại khác"
T98_OTHER_TEAM = "T98 Nhóm khác"
T98_FIELDS = (*CLASSIFICATION_FIELDS, "ai_confidence", "ai_confidence_pct", "ai_classified_by")


class ClassificationWriteCase(FrappeTestCase):
	"""set_classification under AGENT_USER, the session runs use (design-w1-fixes-13 Điểm 1). Nothing commits."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		create_agent(AGENT)
		_make_user(CUSTOMER, "HD Customer")
		for ticket_type in (TICKET_TYPE, T98_OTHER_TYPE):
			if not frappe.db.exists("HD Ticket Type", ticket_type):
				frappe.get_doc({"doctype": "HD Ticket Type", "name": ticket_type}).insert()
		for team in (TEAM, T98_OTHER_TEAM):
			if not frappe.db.exists("HD Team", team):
				frappe.get_doc({"doctype": "HD Team", "team_name": team, "users": [{"user": AGENT}]}).insert()
		self.mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High"}}

	def _ticket(self, **typed):
		return make_ticket(subject="T98 phiếu", raised_by=CUSTOMER, **typed).name

	def _row(self, ticket):
		return frappe.db.get_value("HD Ticket", ticket, T98_FIELDS, as_dict=True)

	def _run(self, ticket, **extra):
		ctx = ToolContext(
			ticket_name=ticket,
			effective_level="L1",
			instructor=None,
			run_id="run-t98",
			category_mapping=self.mapping,
			agent_user=AGENT_USER,
		)
		frappe.set_user(AGENT_USER)
		try:
			return write_ticket.set_classification({"category": "A", "confidence": "Cao", **extra}, ctx)
		finally:
			frappe.set_user("Administrator")


class TestHumanFields(ClassificationWriteCase):
	"""AC-21: a field the person typed at creation is never overwritten by set_classification."""

	def test_set_classification_skips_created_fields(self):
		cases = (
			({"priority": "Low"}, {"ticket_type": TICKET_TYPE, "agent_group": TEAM}),
			({"ticket_type": T98_OTHER_TYPE, "agent_group": T98_OTHER_TEAM, "priority": "Low"}, {}),
		)
		for typed, written in cases:
			with self.subTest(typed=typed):
				ticket = self._ticket(**typed)
				stored = frappe.db.get_value("HD Ticket", ticket, write_ticket.CREATED_LABELS_FIELD)
				self.assertEqual(json.loads(stored), typed)
				before = self._row(ticket)

				result = self._run(ticket)

				self.assertTrue(result["ok"], result)
				row = self._row(ticket)
				self.assertEqual({field: row[field] for field in CLASSIFICATION_FIELDS}, {**written, **typed})
				self.assertEqual(
					result["skipped"],
					[
						{"field": field, "reason": write_ticket.REASON_HUMAN_FILLED}
						for field in CLASSIFICATION_FIELDS
						if field in typed
					],
				)
				self.assertFalse(set(result["after"]) & set(typed), result["after"])
				self.assertFalse(set(result["before"]) & set(typed), result["before"])
				self.assertEqual(
					row.ai_classified_by, CLASSIFIED_BY_AI if written else before.ai_classified_by
				)

	def test_invalid_created_labels_write_none_of_three(self):
		every = dict.fromkeys(CLASSIFICATION_FIELDS, True)
		self.assertEqual(write_ticket.created_labels(None), {})
		self.assertEqual(write_ticket.created_labels(""), {})
		self.assertEqual(write_ticket.created_labels('{"priority": "Low"}'), {"priority": "Low"})
		ticket = self._ticket()
		before = self._row(ticket)
		every_field_human = [
			{"field": field, "reason": write_ticket.REASON_HUMAN_FILLED} for field in CLASSIFICATION_FIELDS
		]
		for raw in ("{không phải JSON", "[]", '"priority"', "null", '{"priority": "Low", "status": "Open"}'):
			with self.subTest(raw=raw):
				self.assertEqual(write_ticket.created_labels(raw), every)
				frappe.db.set_value(
					"HD Ticket", ticket, write_ticket.CREATED_LABELS_FIELD, raw, update_modified=False
				)
				logger = MagicMock()

				with patch.object(frappe, "logger", return_value=logger):
					result = self._run(ticket)

				self.assertTrue(result["ok"], result)
				self.assertEqual((result["before"], result["after"]), ({}, {}))
				self.assertEqual(result["skipped"], every_field_human)
				self.assertEqual(self._row(ticket), before)
				self.assertEqual(
					[call.args[0] for call in logger.warning.call_args_list],
					[f"erp_ai created_labels invalid ticket={ticket}"],
				)


class TestConfidenceSource(ClassificationWriteCase):
	"""AC-22 (W-2): apply_route is the only writer of ai_confidence_pct; set_classification neither takes nor writes it."""

	def test_set_classification_never_writes_confidence_pct(self):
		ticket = self._ticket()
		frappe.db.set_value("HD Ticket", ticket, "ai_confidence_pct", 85, update_modified=False)

		result = self._run(ticket, confidence_pct=40)

		self.assertTrue(result["ok"], result)
		self.assertEqual(result["after"]["priority"], "High")
		self.assertNotIn("ai_confidence_pct", result["before"])
		self.assertNotIn("ai_confidence_pct", result["after"])
		self.assertEqual(self._row(ticket).ai_confidence_pct, 85)

	def test_set_classification_schema_has_no_confidence_pct(self):
		(spec,) = [spec for spec in write_ticket.TOOLS if spec.name == "set_classification"]
		input_schema = spec.schema["input_schema"]
		self.assertEqual(set(input_schema["properties"]), {"category", "confidence"})
		self.assertNotIn("confidence_pct", input_schema["required"])
		self.assertNotIn("confidence_pct", json.dumps(spec.schema))


T99_PREFIX = "ERPAI-TEST-T99"


class TestLockedCount(FrappeTestCase):
	"""ADR-036 QĐ 4: locked_rows locks the ticket row, then reads with a lock, so it sees rows another transaction
	committed after this one's REPEATABLE READ snapshot. Two connections commit for real; tearDown deletes it all."""

	def setUp(self):
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		self.committed_tickets = []

	def tearDown(self):
		# After its first use, secondary_connection() leaves frappe.local.db on the second connection.
		frappe.local.db = self._primary_connection
		frappe.db.rollback()
		for ticket in self.committed_tickets:
			frappe.db.delete("Comment", {"reference_doctype": "HD Ticket", "reference_name": ticket})
			frappe.db.delete("HD Ticket", ticket)
		frappe.db.commit()

	def _committed_ticket(self) -> str:
		"""A bare HD Ticket row (no hooks: no job, no mail, no assignment), committed so both connections see it."""
		doc = frappe.new_doc("HD Ticket")
		doc.subject = f"{T99_PREFIX} phiếu"
		doc.set_new_name()
		self.committed_tickets.append(doc.name)
		doc.db_insert()
		frappe.db.commit()
		return doc.name

	def test_missing_ticket_raises(self):
		for name in (f"{T99_PREFIX} không có", "", None):
			for helper in (write_ticket.locked_rows, write_ticket.locked_count):
				with self.subTest(name=name, helper=helper.__name__), self.assertRaises(ValueError):
					helper(name, "Comment", {"reference_doctype": "HD Ticket"})

	def test_rows_committed_after_snapshot_are_seen(self):
		with self.primary_connection():
			ticket = self._committed_ticket()
			filters = {"reference_doctype": "HD Ticket", "reference_name": ticket}
			# The first plain read takes this transaction's snapshot.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
		with self.secondary_connection():
			other = frappe.get_doc(
				{"doctype": "Comment", "comment_type": "Info", "content": f"{T99_PREFIX} khác", **filters}
			).insert(ignore_permissions=True)
			frappe.db.commit()
		with self.primary_connection():
			# Precondition: a plain read still sees the snapshot, so only a locking read can see the new row.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
			with patch.object(frappe.db, "commit", side_effect=AssertionError("locked_rows must not commit")):
				rows = write_ticket.locked_rows(ticket, "Comment", filters, fields=("name", "content"))
				count = write_ticket.locked_count(ticket, "Comment", filters)

		self.assertEqual(rows, [{"name": other.name, "content": f"{T99_PREFIX} khác"}])
		self.assertEqual(count, 1)

	def test_post_notice_sees_comment_committed_after_snapshot(self):
		# AC-23, AR3-7: a notice another job committed after this transaction's snapshot still blocks a second one.
		self.addCleanup(frappe.set_user, "Administrator")
		since = get_datetime("2024-01-01 10:00:00")
		with self.primary_connection():
			ticket = self._committed_ticket()
			filters = {"reference_doctype": "HD Ticket", "reference_name": ticket}
			# The first plain read takes this transaction's snapshot.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
		with self.secondary_connection():
			# Set inside: opening the second connection (frappe.connect) makes Administrator the session user.
			frappe.set_user(AGENT_USER)
			posted = write_ticket.post_notice(ticket, "run_failed", f"{T99_PREFIX} lần một", since)
			frappe.db.commit()
		with self.primary_connection():
			# Precondition: a plain read still sees the snapshot, so only a locking read can see the notice.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
			with patch.object(frappe.db, "commit", side_effect=AssertionError("post_notice must not commit")):
				result = write_ticket.post_notice(ticket, "run_failed", f"{T99_PREFIX} lần hai", since)
			comments = write_ticket.locked_rows(ticket, "Comment", filters, fields=("name", "content"))

		self.assertTrue(posted["ok"], posted)
		self.assertEqual(result, {"ok": False, "reason": write_ticket.REASON_NOTICE_SENT})
		prefix = write_ticket.NOTICE_PREFIXES["run_failed"]
		self.assertEqual(comments, [{"name": posted["comment"], "content": f"{prefix} {T99_PREFIX} lần một"}])


T100_PREFIX = "ERPAI-TEST-T100"
EVIDENCE = "**Căn cứ:** đã đọc mô tả phiếu và comment cuối"
QUESTION = f"Máy in báo lỗi gì trên màn hình?\n{EVIDENCE}"


class TicketCommentCase(FrappeTestCase):
	"""A fresh ticket and the agent account's session (AGENT_USER, as runs use). Nothing commits."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		_make_user(CUSTOMER, "HD Customer")
		self.ticket = make_ticket(subject=f"{T100_PREFIX} phiếu", raised_by=CUSTOMER).name
		frappe.set_user(AGENT_USER)

	def _comments(self, ticket=None):
		return frappe.get_all(
			"Comment",
			filters={
				"reference_doctype": "HD Ticket",
				"reference_name": ticket or self.ticket,
				"comment_type": "Comment",
			},
			pluck="content",
			order_by="creation asc",
		)


class TestPostCommentKinds(TicketCommentCase):
	"""AC-22: the post_comment tool takes a kind; a proposal needs a confidence line and grounds; below the
	threshold only one question per run, with the footer (U4b.md:171, U4b-fixes Fix 9)."""

	def _ctx(self, below_threshold=False, run_id=None):
		run_id = run_id or f"{T100_PREFIX}-{frappe.generate_hash(length=10)}"
		self.addCleanup(lambda: frappe.flags.get("erp_ai_asked_runs", set()).discard(run_id))
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=None,
			run_id=run_id,
			category_mapping={},
			agent_user=AGENT_USER,
			below_threshold=below_threshold,
		)

	def _post(self, kind, content, ctx=None):
		return write_ticket.post_comment_tool({"kind": kind, "content": content}, ctx or self._ctx())

	def _classify_row(self, pct):
		frappe.set_user("Administrator")
		write_entry(
			ticket=self.ticket,
			run_id=f"{T100_PREFIX}-classify",
			entry_type="classify",
			trigger="ticket_insert",
			turn=0,
			predicted_category="A",
			predicted_confidence_pct=pct,
		)
		frappe.set_user(AGENT_USER)

	def _refused(self, reason):
		return {"ok": False, "reason": reason}

	def test_proposal_needs_confidence_and_evidence(self):
		refused = (
			(
				"no confidence line",
				f"**Nhận định:** máy in hỏng\n{EVIDENCE}",
				write_ticket.REASON_NO_CONFIDENCE,
			),
			(
				"101%",
				f"**Nhận định:** máy in hỏng\n{EVIDENCE}\nĐộ tin cậy: 101%",
				write_ticket.REASON_NO_CONFIDENCE,
			),
			("no evidence", "**Nhận định:** máy in hỏng\nĐộ tin cậy: 90%", write_ticket.REASON_NO_EVIDENCE),
			(
				"empty evidence before the next heading",
				"**Căn cứ:**\n**Hướng xử lý:** khởi động lại máy in\nĐộ tin cậy: 90%",
				write_ticket.REASON_NO_EVIDENCE,
			),
			(
				"blank evidence at the end",
				"Độ tin cậy: 90%\n**Căn cứ:**   \n",
				write_ticket.REASON_NO_EVIDENCE,
			),
		)
		for case, content, reason in refused:
			with self.subTest(case):
				self.assertEqual(self._post("de_xuat", content), self._refused(reason))
				self.assertEqual(self._comments(), [])

		proposal = f"**Nhận định:** máy in hỏng\n{EVIDENCE}\nĐộ tin cậy: 100%"
		result = self._post("de_xuat", proposal)

		self.assertTrue(result["ok"], result)
		self.assertEqual(self._comments(), [proposal])
		self.assertEqual(frappe.db.get_value("Comment", result["comment"], "content"), proposal)
		# Above the threshold a question is posted as written: no grounds, no confidence, no footer (step 4).
		self.assertTrue(self._post("hoi", "Máy in nào?")["ok"])
		self.assertEqual(self._comments(), [proposal, "Máy in nào?"])

	def test_section_text_reads_one_section(self):
		content = "**Nhận định:** A\n**Căn cứ:** dòng 1\ndòng 2\n**Hướng xử lý:** B\nĐộ tin cậy: 90%"
		self.assertEqual(write_ticket.section_text(content, "Căn cứ"), "dòng 1\ndòng 2")
		self.assertEqual(write_ticket.section_text(content, "Hướng xử lý"), "B\nĐộ tin cậy: 90%")
		self.assertEqual(write_ticket.section_text("Căn cứ: không có dấu sao", "Căn cứ"), "không có dấu sao")
		self.assertEqual(write_ticket.section_text("**Căn cứ:**\n**Nhận định:** A", "Căn cứ"), "")
		self.assertIsNone(write_ticket.section_text("Nhận định: A, Căn cứ: B", "Căn cứ"))
		self.assertIsNone(write_ticket.section_text(content, "Rủi ro"))

	def test_bad_kind_refused(self):
		for below_threshold in (False, True):
			for args in (
				{"content": QUESTION},
				{"content": QUESTION, "kind": "x"},
				{"content": QUESTION, "kind": ""},
			):
				with self.subTest(below_threshold=below_threshold, args=args):
					result = write_ticket.post_comment_tool(args, self._ctx(below_threshold))
					self.assertFalse(result["ok"], result)
					self.assertIn("kind", result["reason"])
					self.assertEqual(self._comments(), [])
		with patch.object(registry, "_all_specs", lambda: write_ticket.TOOLS):
			self.assertFalse(execute_tool("post_comment", {"content": QUESTION}, self._ctx())["ok"])
		self.assertEqual(self._comments(), [])

	def test_below_threshold_one_question_with_footer(self):
		self._classify_row(69)
		set_agent_settings(confidence_threshold=70)
		ctx = self._ctx(below_threshold=True)
		proposal = f"**Nhận định:** máy in hỏng\n{EVIDENCE}\nĐộ tin cậy: 90%"

		self.assertEqual(self._post("de_xuat", proposal, ctx), self._refused(write_ticket.REASON_ASK_ONLY))
		self.assertEqual(
			self._post("hoi", "Máy in báo lỗi gì?", ctx), self._refused(write_ticket.REASON_NO_EVIDENCE)
		)
		self.assertEqual(self._comments(), [])
		self.assertFalse(write_ticket.asked_in_run(ctx.run_id))

		first = self._post("hoi", QUESTION, ctx)

		self.assertTrue(first["ok"], first)
		footer = write_ticket.ASK_FOOTER.format(pct="69%", threshold=70)
		self.assertIn("69% (ngưỡng 70%)", footer)
		self.assertEqual(self._comments(), [f"{QUESTION}\n\n{footer}"])
		self.assertTrue(write_ticket.asked_in_run(ctx.run_id))
		self.assertEqual(self._post("hoi", QUESTION, ctx), self._refused(write_ticket.REASON_ONE_ASK))
		self.assertEqual(len(self._comments()), 1)

	def test_footer_threshold_80_and_unknown_pct(self):
		set_agent_settings(confidence_threshold=80)

		unknown = self._post("hoi", QUESTION, self._ctx(below_threshold=True))

		self.assertTrue(unknown["ok"], unknown)
		footer = write_ticket.ASK_FOOTER.format(pct="chưa có", threshold=80)
		self.assertIn("chưa có (ngưỡng 80%)", footer)
		self.assertEqual(self._comments(), [f"{QUESTION}\n\n{footer}"])

		self._classify_row(75)
		known = self._post("hoi", QUESTION, self._ctx(below_threshold=True))

		self.assertTrue(known["ok"], known)
		self.assertEqual(
			self._comments()[-1], f"{QUESTION}\n\n{write_ticket.ASK_FOOTER.format(pct='75%', threshold=80)}"
		)

	def test_marked_run_refuses_comment_question(self):
		ctx = self._ctx(below_threshold=True)
		self.assertFalse(write_ticket.asked_in_run(ctx.run_id))

		write_ticket.mark_asked(ctx.run_id)

		self.assertTrue(write_ticket.asked_in_run(ctx.run_id))
		self.assertFalse(write_ticket.asked_in_run(f"{ctx.run_id}-khác"))
		self.assertEqual(self._post("hoi", QUESTION, ctx), self._refused(write_ticket.REASON_ONE_ASK))
		self.assertEqual(self._comments(), [])
		with self.assertRaises(ValueError):
			write_ticket.mark_asked("")


class TestPostNotice(TicketCommentCase):
	"""AC-23, NFR-3: one status notice of a kind per ticket since the mark; the dedup read is locked_count's."""

	def test_same_notice_since_mark_posted_once(self):
		since = get_datetime("2024-01-01 10:00:00")
		prefix = write_ticket.NOTICE_PREFIXES["daily_limit"]
		self.assertEqual(
			set(write_ticket.NOTICE_PREFIXES), {"daily_limit", "over_budget", "run_failed", "ask_fallback"}
		)
		# A person's comment with the same text is no notice of the bot.
		frappe.set_user("Administrator")
		self.assertTrue(write_ticket._post(self.ticket, f"{prefix} người viết")["ok"])
		frappe.set_user(AGENT_USER)

		with patch.object(write_ticket, "locked_count", wraps=write_ticket.locked_count) as counted:
			first = write_ticket.post_notice(self.ticket, "daily_limit", "đủ 5 lần hôm nay.", since)
			again = write_ticket.post_notice(self.ticket, "daily_limit", "lần hai.", since)

		self.assertTrue(first["ok"], first)
		self.assertEqual(frappe.db.get_value("Comment", first["comment"], "owner"), AGENT_USER)
		self.assertEqual(again, {"ok": False, "reason": write_ticket.REASON_NOTICE_SENT})
		self.assertEqual(self._comments(), [f"{prefix} người viết", f"{prefix} đủ 5 lần hôm nay."])
		self.assertEqual([call.args[:2] for call in counted.call_args_list], [(self.ticket, "Comment")] * 2)

		# Another notice is its own key.
		other = write_ticket.post_notice(self.ticket, "run_failed", "lỗi cổng.", since)
		self.assertTrue(other["ok"], other)
		self.assertEqual(len(self._comments()), 3)

		# A notice from before the mark does not count; from after it, it does.
		frappe.db.set_value(
			"Comment", first["comment"], "creation", "2024-01-01 09:00:00", update_modified=False
		)
		earlier = get_datetime("2024-01-01 08:00:00")
		self.assertEqual(
			write_ticket.post_notice(self.ticket, "daily_limit", "x", earlier),
			{"ok": False, "reason": write_ticket.REASON_NOTICE_SENT},
		)
		self.assertTrue(write_ticket.post_notice(self.ticket, "daily_limit", "ngày mới.", since)["ok"])
		self.assertEqual(self._comments()[-1], f"{prefix} ngày mới.")

		before = len(self._comments())
		with self.assertRaises(ValueError):
			write_ticket.post_notice(self.ticket, "x_unknown", "x", since)
		self.assertEqual(len(self._comments()), before)


# The analysis a model writes to the reasoning template (design-w1-fixes-20 Điểm 1.2): no "Căn cứ" section.
ANALYSIS = "**Nhận định:** A\n**Hướng xử lý:** B\nĐộ tin cậy: 90%"
_HEADING = re.compile(r"(?m)^[ \t]*\*\*([^*\n]+):\*\*|<strong>([^<]+):</strong>")
_PLAN_HEADING = re.compile(r"(?m)^[ \t]*(?:\*\*)?Hướng xử lý:|<strong>Hướng xử lý:</strong>")


def _headings(content: str) -> list[str]:
	"""The section names of a comment, in order (design-w1-fixes-20 Điểm 3.3)."""
	return [model or system for model, system in _HEADING.findall(content)]


class TestGuidanceWriter(TicketCommentCase):
	"""AC-65, ADR-036 QĐ 3: the guidance comment is the agent's core Comment whose content opens with the marker."""

	def _run(self, analysis=None, done=(), pending=(), manual=()):
		"""A fresh guidance collector holding `analysis` and the raw lines of each section; closed at cleanup."""
		run_id = f"{T100_PREFIX}-{frappe.generate_hash(length=10)}"
		self.addCleanup(write_ticket.close_collector, run_id)
		write_ticket.open_collector(run_id)
		if analysis is not None:
			write_ticket.hold_analysis(run_id, analysis)
		for section, lines in (
			(write_ticket.SECTION_DONE, done),
			(write_ticket.SECTION_PENDING, pending),
			(write_ticket.SECTION_DECIDE, manual),
		):
			for line in lines:
				write_ticket.collect(run_id, section, line)
		return run_id

	def _body(self, run_id):
		"""The stored content of the guidance comment post_guidance posts for `run_id`; the comment is then deleted,
		so the next case of a test may post again."""
		result = write_ticket.post_guidance(self.ticket, run_id)
		self.assertTrue(result["ok"], result)
		content = frappe.db.get_value("Comment", result["comment"], "content")
		frappe.db.delete("Comment", result["comment"])
		return content

	def test_count_ignores_info_other_owner_and_non_prefix(self):
		marker = write_ticket.GUIDANCE_MARKER
		self.assertEqual(
			write_ticket.guidance_filters(self.ticket),
			{
				"reference_doctype": "HD Ticket",
				"reference_name": self.ticket,
				"comment_type": "Comment",
				"owner": AGENT_USER,
				"content": ["like", f"{marker}%"],
			},
		)
		frappe.set_user("Administrator")
		other = make_ticket(subject=f"{T100_PREFIX} phiếu khác", raised_by=CUSTOMER).name
		# a person's comment opening with the marker
		self.assertTrue(write_ticket._post(self.ticket, f"{marker}\nngười viết")["ok"])
		frappe.set_user(AGENT_USER)
		# the agent's Info row opening with the marker (ADR-035 QĐ 7)
		frappe.get_doc("HD Ticket", self.ticket).add_comment("Info", f"{marker}\nthông tin")
		# the agent's comment with the marker inside, not at position 0 (a proposal or BA note quoting it)
		self.assertTrue(write_ticket._post(self.ticket, f"Đề xuất của bot\n{marker}")["ok"])
		# another ticket's guidance
		self.assertTrue(write_ticket._post(other, f"{marker}\n**Nhận định:** B")["ok"])

		self.assertEqual(write_ticket.count_guidance(self.ticket), 0)
		self.assertEqual(write_ticket.count_guidance(self.ticket, lock=True), 0)

		self.assertTrue(write_ticket._post(self.ticket, f"{marker}\n**Nhận định:** A")["ok"])

		self.assertEqual(write_ticket.count_guidance(self.ticket), 1)
		self.assertEqual(write_ticket.count_guidance(self.ticket, lock=True), 1)
		self.assertEqual(write_ticket.count_guidance(other), 1)

	def test_count_with_lock_goes_through_locked_count(self):
		with patch.object(write_ticket, "locked_count", return_value=7) as counted:
			self.assertEqual(write_ticket.count_guidance(self.ticket, lock=True), 7)
		counted.assert_called_once_with(self.ticket, "Comment", write_ticket.guidance_filters(self.ticket))

	def test_marker_survives_save(self):
		marker = write_ticket.GUIDANCE_MARKER
		posted = write_ticket._post(self.ticket, f"{marker}\n**Nhận định:** A\n**Hướng xử lý:** B")
		self.assertTrue(posted["ok"], posted)

		stored = frappe.db.get_value("Comment", posted["comment"], "content")
		self.assertTrue(stored.startswith(f"{marker}\n"), stored)
		frappe.set_user("Administrator")
		frappe.get_doc("Comment", posted["comment"]).save()

		self.assertTrue(
			frappe.db.get_value("Comment", posted["comment"], "content").startswith(f"{marker}\n")
		)
		self.assertEqual(write_ticket.count_guidance(self.ticket), 1)

	def test_writer_posts_once_second_call_refused(self):
		# AC-65, ADR-036 QĐ 1, 4: one guidance comment per ticket; the count runs under the ticket lock.
		run_id = self._run(ANALYSIS, done=["Bot đã phân loại phiếu: Loại A."])
		refused = {"ok": False, "reason": write_ticket.REASON_GUIDANCE_EXISTS}
		with patch.object(write_ticket, "locked_count", wraps=write_ticket.locked_count) as counted:
			first = write_ticket.post_guidance(self.ticket, run_id)
			again = write_ticket.post_guidance(self.ticket, self._run(ANALYSIS))
			same_run = write_ticket.post_guidance(self.ticket, run_id)

		self.assertTrue(first["ok"], first)
		self.assertEqual(
			first["counts"],
			{write_ticket.SECTION_DONE: 1, write_ticket.SECTION_PENDING: 0, write_ticket.SECTION_DECIDE: 0},
		)
		self.assertEqual(frappe.db.get_value("Comment", first["comment"], "owner"), AGENT_USER)
		self.assertEqual(again, refused)
		self.assertEqual(same_run, refused)
		self.assertEqual(len(self._comments()), 1)
		self.assertEqual(write_ticket.count_guidance(self.ticket), 1)
		self.assertEqual(
			counted.call_args_list,
			[call(self.ticket, "Comment", write_ticket.guidance_filters(self.ticket))] * 3,
		)

	def test_concurrent_snapshot_does_not_double_post(self):
		# ADR-036 QĐ 4: two runs of one ticket both counted 0 at their start. The later writer still sees the
		# guidance the other committed after this transaction's REPEATABLE READ snapshot. Only the second
		# connection commits (the primary keeps its commit guard); the cleanup deletes what it committed.
		committed = []
		self.addCleanup(self._delete_committed, committed)
		# setUp's ticket holds the naming-series row lock: drop it so the second connection can name its ticket.
		frappe.db.rollback()
		later_run = self._run(ANALYSIS)
		with self.secondary_connection():
			doc = frappe.new_doc("HD Ticket")
			doc.subject = f"{T100_PREFIX} phiếu hai kết nối"
			doc.set_new_name()
			committed.append(doc.name)
			# a bare row: no hooks, no job, no mail
			doc.db_insert()
			frappe.db.commit()
		ticket = committed[0]
		filters = {"reference_doctype": "HD Ticket", "reference_name": ticket}
		with self.primary_connection():
			# The first plain read takes this transaction's snapshot.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
		with self.secondary_connection():
			# Set inside: opening the second connection (frappe.connect) makes Administrator the session user.
			frappe.set_user(AGENT_USER)
			posted = write_ticket.post_guidance(ticket, self._run(ANALYSIS, done=["D"]))
			frappe.db.commit()
		with self.primary_connection():
			# Precondition: a plain read still sees the snapshot, so only a locking read can see the guidance.
			self.assertEqual(frappe.db.count("Comment", filters), 0)
			result = write_ticket.post_guidance(ticket, later_run)
			comments = write_ticket.locked_rows(ticket, "Comment", filters)

		self.assertTrue(posted["ok"], posted)
		self.assertEqual(result, {"ok": False, "reason": write_ticket.REASON_GUIDANCE_EXISTS})
		self.assertEqual(comments, [{"name": posted["comment"]}])

	def _delete_committed(self, tickets):
		# The primary's locks go first; then the deletes run on the second connection, which committed the rows:
		# Database.delete builds its query through frappe.db, so frappe.local.db must point at that connection.
		self._primary_connection.rollback()
		try:
			if tickets:
				frappe.local.db = self._secondary_connection
				for ticket in tickets:
					frappe.db.delete("Comment", {"reference_doctype": "HD Ticket", "reference_name": ticket})
					frappe.db.delete("HD Ticket", {"name": ticket})
				frappe.db.commit()
		finally:
			# After its first use, secondary_connection() leaves frappe.local.db on the second connection.
			frappe.local.db = self._primary_connection

	def test_deleted_guidance_allows_new_one(self):
		# ADR-036 QĐ 6: the comment is the source of truth; once deleted, a later run posts again.
		first = write_ticket.post_guidance(self.ticket, self._run(ANALYSIS))
		self.assertTrue(first["ok"], first)
		frappe.set_user("Administrator")
		frappe.delete_doc("Comment", first["comment"])
		frappe.set_user(AGENT_USER)
		self.assertEqual(write_ticket.count_guidance(self.ticket), 0)

		second = write_ticket.post_guidance(self.ticket, self._run(ANALYSIS))

		self.assertTrue(second["ok"], second)
		self.assertNotEqual(second["comment"], first["comment"])
		self.assertEqual(write_ticket.count_guidance(self.ticket), 1)

	def test_no_analysis_no_items_posts_nothing(self):
		# w1.md:64 step (2): nothing to say → no comment, so a later run is still offered guidance.
		for case, run_id in (("open, empty", self._run()), ("no collector", f"{T100_PREFIX}-không gom")):
			with self.subTest(case):
				self.assertEqual(
					write_ticket.post_guidance(self.ticket, run_id),
					{"ok": False, "reason": write_ticket.REASON_NO_CONTENT},
				)
				self.assertEqual(self._comments(), [])
		self.assertTrue(write_ticket.post_guidance(self.ticket, self._run(ANALYSIS))["ok"])

	def test_no_analysis_with_done_items_uses_fallback(self):
		content = self._body(self._run(done=["D"]))

		self.assertEqual(
			content,
			f"{write_ticket.GUIDANCE_MARKER}\n{write_ticket.GUIDANCE_FALLBACK}"
			f"\n<p><strong>{write_ticket.SECTION_DONE}:</strong></p><ul><li>D</li></ul>",
		)
		self.assertEqual(_headings(content), ["Nhận định", "Hướng xử lý", "Đã làm"])

	def test_collected_line_html_escaped_once(self):
		# AD3-4: a collected line is raw text; the writer escapes it exactly once, the model's analysis not at all.
		value = "<b>&x"
		self.assertEqual(escape_html(value), "&lt;b&gt;&amp;x")

		content = self._body(self._run(ANALYSIS, done=[value], manual=[value]))

		self.assertEqual(content.count("&lt;b&gt;&amp;x"), 2)
		self.assertNotIn(value, content)
		self.assertNotIn("&amp;lt;", content)
		self.assertNotIn("&amp;amp;", content)
		self.assertIn(ANALYSIS.split("\n", 1)[0], content)

	def test_body_order_analysis_plan_done_pending(self):
		# design-w1-fixes-20 Điểm 1.2: the example body, byte for byte.
		result = write_ticket.post_guidance(
			self.ticket, self._run(ANALYSIS, done=["D"], pending=["P"], manual=["L"])
		)
		self.assertTrue(result["ok"], result)
		content = frappe.db.get_value("Comment", result["comment"], "content")

		self.assertEqual(
			content,
			"<!-- erp_ai:huong-xu-ly -->\n"
			"**Nhận định:** A\n"
			"**Hướng xử lý:** B\n"
			"<ul><li>L</li></ul>\n"
			"Độ tin cậy: 90%\n"
			"<p><strong>Đã làm:</strong></p><ul><li>D</li></ul>\n"
			f"<p><strong>Chờ duyệt:</strong> {write_ticket.PENDING_NOTE}</p><ul><li>P</li></ul>",
		)
		self.assertEqual(_headings(content), ["Nhận định", "Hướng xử lý", "Đã làm", "Chờ duyệt"])
		self.assertEqual(result["counts"], {"Đã làm": 1, "Chờ duyệt": 1, "Hướng xử lý": 1})

	def test_manual_lines_inside_plan_section(self):
		# AC-66 [changed], AC-23 [changed] (2): work left to a person goes inside "Hướng xử lý", no heading of its own.
		ul = "<ul><li>L</li></ul>"
		plan = "<strong>Hướng xử lý:</strong>"
		cases = (
			(
				"plan is the last section",
				"**Nhận định:** A\n**Hướng xử lý:** B\nbước 2",
				f"**Nhận định:** A\n**Hướng xử lý:** B\nbước 2\n{ul}",
			),
			(
				"before the confidence heading",
				"**Nhận định:** A\n**Hướng xử lý:** B\n**Độ tin cậy:** 90%",
				f"**Nhận định:** A\n**Hướng xử lý:** B\n{ul}\n**Độ tin cậy:** 90%",
			),
			(
				"before the analysis heading",
				"**Hướng xử lý:** B\nbước 2\n**Nhận định:** A\nĐộ tin cậy: 90%",
				f"**Hướng xử lý:** B\nbước 2\n{ul}\n**Nhận định:** A\nĐộ tin cậy: 90%",
			),
			(
				"headings without stars",
				"Nhận định: A\nHướng xử lý: B\nĐộ tin cậy: 90%",
				f"Nhận định: A\nHướng xử lý: B\n{ul}\nĐộ tin cậy: 90%",
			),
			(
				"no plan heading",
				"**Nhận định:** A\nĐộ tin cậy: 90%",
				f"**Nhận định:** A\nĐộ tin cậy: 90%\n<p>{plan}</p>{ul}",
			),
			("fallback", None, f"{write_ticket.GUIDANCE_FALLBACK}\n{ul}"),
		)
		for case, analysis, text in cases:
			with self.subTest(case):
				content = self._body(self._run(analysis, manual=["L"]))

				self.assertEqual(content, f"{write_ticket.GUIDANCE_MARKER}\n{text}")
				# exactly one plan heading, a heading written without stars included
				(plan_at,) = [m.start() for m in _PLAN_HEADING.finditer(content)]
				if analysis is not None and "Hướng xử lý:" not in analysis:
					self.assertEqual(content.count(plan), 1)
				# the list sits after the plan heading and before the next heading
				later = [m.start() for m in _HEADING.finditer(content) if m.start() > plan_at]
				self.assertGreater(content.index(ul), plan_at)
				if later:
					self.assertLess(content.index(ul), later[0])

	def test_no_evidence_or_decide_heading(self):
		# AC-65 (a) [changed]: no "Căn cứ" and no "Cần ai quyết" section, whatever the run collected.
		for constant in (write_ticket.GUIDANCE_FALLBACK, write_ticket.PENDING_NOTE):
			for forbidden in ("Căn cứ", "Cần ai quyết"):
				self.assertNotIn(forbidden, constant)
		for analysis in (ANALYSIS, None):
			for done, pending, manual in itertools.product(((), ("x",)), repeat=3):
				if analysis is None and not (done or pending or manual):
					continue
				with self.subTest(analysis=analysis, done=done, pending=pending, manual=manual):
					content = self._body(self._run(analysis, done, pending, manual))
					headings = _headings(content)

					self.assertNotIn("Căn cứ", headings)
					self.assertNotIn("Cần ai quyết", headings)
					self.assertNotIn("Cần ai quyết", content)
					self.assertLessEqual(set(headings), {"Nhận định", "Hướng xử lý", "Đã làm", "Chờ duyệt"})
					# an empty section does not show
					self.assertEqual("Đã làm" in headings, bool(done))
					self.assertEqual("Chờ duyệt" in headings, bool(pending))

	def test_pending_note_and_one_item_per_proposal(self):
		# AC-65 (a) [changed], AC-67: one line per proposal; the pointer to "Duyệt ngay" once, in the heading paragraph.
		head = "<strong>Chờ duyệt:</strong>"
		self.assertIn('"Duyệt ngay"', write_ticket.PENDING_NOTE)
		self.assertIn('"Trao đổi với bot"', write_ticket.PENDING_NOTE)

		content = self._body(self._run(ANALYSIS, pending=["Đề xuất CR-1 (sửa code)", "Đề xuất CR-2 (lệnh)"]))

		pending = content[content.index(head) :]
		paragraph = pending[: pending.index("</p>")]
		self.assertIn(write_ticket.PENDING_NOTE, paragraph)
		self.assertEqual(content.count(write_ticket.PENDING_NOTE), 1)
		self.assertEqual(pending.count("<li>"), 2)
		self.assertEqual(
			pending[pending.index("<ul>") :],
			"<ul><li>Đề xuất CR-1 (sửa code)</li><li>Đề xuất CR-2 (lệnh)</li></ul>",
		)

		empty = self._body(self._run(ANALYSIS, done=["D"]))

		self.assertNotIn(head, empty)
		self.assertNotIn(write_ticket.PENDING_NOTE, empty)

	def test_failure_summary_three_parts_escaped_once(self):
		# design-w1-fixes-20 Điểm 3.1: done, pending and manual lines apart, each escaped once; no marker, no heading.
		self.assertEqual(write_ticket.FAILURE_DONE, "Trước khi lỗi, bot đã làm: ")
		self.assertEqual(write_ticket.FAILURE_PENDING, "Đề xuất đã tạo, đang chờ duyệt: ")
		self.assertEqual(write_ticket.FAILURE_MANUAL, "Việc người phải làm tay: ")
		self.assertEqual(write_ticket.failure_summary(f"{T100_PREFIX}-không gom"), "")
		self.assertEqual(write_ticket.failure_summary(self._run()), "")
		self.assertEqual(write_ticket.failure_summary(self._run(ANALYSIS)), "")

		summary = write_ticket.failure_summary(
			self._run(
				ANALYSIS,
				done=["Bot đã phân loại phiếu: Loại A.", "<b>&x"],
				pending=["Đề xuất CR-1"],
				manual=["Nhờ trưởng nhóm phân công."],
			)
		)

		self.assertEqual(
			summary,
			f"{write_ticket.FAILURE_DONE}Bot đã phân loại phiếu: Loại A.; &lt;b&gt;&amp;x\n"
			f"{write_ticket.FAILURE_PENDING}Đề xuất CR-1\n"
			f"{write_ticket.FAILURE_MANUAL}Nhờ trưởng nhóm phân công.",
		)
		self.assertEqual(
			write_ticket.failure_summary(self._run(manual=["<b>&x"])),
			f"{write_ticket.FAILURE_MANUAL}&lt;b&gt;&amp;x",
		)
		self.assertNotIn(write_ticket.GUIDANCE_MARKER, summary)
		self.assertEqual(_headings(summary), [])
		self.assertEqual(self._comments(), [])

	def _ctx(self, run_id=None, below_threshold=False, category_mapping=None):
		return ToolContext(
			ticket_name=self.ticket,
			effective_level="L1",
			instructor=None,
			run_id=run_id or f"{T100_PREFIX}-{frappe.generate_hash(length=10)}",
			category_mapping=category_mapping or {},
			agent_user=AGENT_USER,
			below_threshold=below_threshold,
		)

	def _tool(self, kind, content, ctx=None):
		return write_ticket.post_comment_tool({"kind": kind, "content": content}, ctx or self._ctx())

	def test_post_comment_marker_refused_every_kind(self):
		# AC-65 (d), ADR-036 QĐ 3: the model's text never carries the marker, whatever the kind; step (0) runs first.
		refused = {"ok": False, "reason": write_ticket.REASON_MARKER}
		guidance_run = self._run()
		# passes every other check of a proposal
		content = f"{write_ticket.GUIDANCE_MARKER}\n{ANALYSIS}\n{EVIDENCE}"
		for kind in ("de_xuat", "hoi", "ba_note", "x"):
			for case, ctx in (
				("above the threshold", self._ctx()),
				("below the threshold", self._ctx(below_threshold=True)),
				("guidance run", self._ctx(guidance_run)),
			):
				with self.subTest(kind=kind, case=case):
					self.assertEqual(self._tool(kind, content, ctx), refused)
		with patch.object(registry, "_all_specs", lambda: write_ticket.TOOLS):
			self.assertEqual(
				execute_tool("post_comment", {"kind": "de_xuat", "content": content}, self._ctx()), refused
			)

		self.assertEqual(self._comments(), [])
		self.assertEqual(write_ticket.collected(guidance_run)[0], None)
		self.assertEqual(write_ticket.count_guidance(self.ticket), 0)

	def test_marker_case_and_spacing_variants_refused(self):
		refused = {"ok": False, "reason": write_ticket.REASON_MARKER}
		variants = (
			"<!-- ERP_AI:HUONG-XU-LY -->",
			"<!--erp_ai:huong-xu-ly-->",
			"<!-- Erp_Ai : Huong - Xu - Ly -->",
			"<!--\terp_ai:\nhuong-xu-ly\t-->",
			"erp_ai:huong-xu-ly",
			"ERP_AI: huong-xu-ly",
		)
		for variant in variants:
			for case, content in (
				("first line", f"{variant}\n{ANALYSIS}\n{EVIDENCE}"),
				("inside", f"{ANALYSIS}\n{variant}\n{EVIDENCE}"),
			):
				with self.subTest(variant=variant, case=case):
					self.assertEqual(self._tool("de_xuat", content), refused)
		self.assertEqual(self._comments(), [])
		# the plan heading alone is no marker
		proposal = f"{ANALYSIS}\n{EVIDENCE}"
		self.assertTrue(self._tool("de_xuat", proposal)["ok"])
		self.assertEqual(self._comments(), [proposal])

	def test_system_heading_judged_after_normalising_each_line(self):
		# C8-fix1 round 2 (R13c): a line is judged after tags, entities, emphasis marks, case and spaces are
		# normalised; mid-sentence mentions pass.
		import unicodedata

		refused = {"ok": False, "reason": write_ticket.REASON_SYSTEM_SECTION}
		forged = (
			"<b>Đã làm:</b> xong",
			"<h3>Chờ duyệt</h3>",
			"&nbsp;Đã làm: xong",
			"Đã làm:\u00a0xong",
			"Đã làm:",
			"Đã làm",
			"## Chờ duyệt",
			unicodedata.normalize("NFD", "Đã làm:") + " xong",
			"ĐÃ LÀM: xong",
			"<p>ok</p><p>Chờ duyệt: không còn</p>",
			"__Chờ duyệt__: đã duyệt",
			"<em>đã&nbsp;làm</em>: xong",
		)
		for line in forged:
			for content in (f"{line}\n{ANALYSIS}\n{EVIDENCE}", f"{ANALYSIS}\n{line}\n{EVIDENCE}"):
				for kind, ctx in (("de_xuat", self._ctx()), ("hoi", self._ctx())):
					with self.subTest(line=line, kind=kind):
						self.assertEqual(self._tool(kind, content, ctx), refused)
		for line in (
			"Tôi đã làm theo hướng dẫn của khách",
			"Việc đã làm: khách xác nhận",
			"Cần chờ duyệt của quản lý",
			"Đã làm sạch dữ liệu",
		):
			with self.subTest(line=line):
				reply = self._tool("hoi", f"{line}\n{ANALYSIS}\n{EVIDENCE}", self._ctx())
				self.assertNotEqual(reply, refused)

	def test_system_section_heading_refused_every_kind(self):
		# AC-66, AC-67 (C7-fix1 R13a): "Đã làm" and "Chờ duyệt" are written by the system only, so a line of the
		# model's text opening with either heading is refused in every kind and is never held as the analysis.
		refused = {"ok": False, "reason": write_ticket.REASON_SYSTEM_SECTION}
		self.assertIn(write_ticket.SECTION_DONE, write_ticket.REASON_SYSTEM_SECTION)
		self.assertIn(write_ticket.SECTION_PENDING, write_ticket.REASON_SYSTEM_SECTION)
		self.assertIn("hệ thống", write_ticket.REASON_SYSTEM_SECTION)
		guidance_run = self._run()
		forged = (
			"**Đã làm:** đã duyệt mọi đề xuất",
			"**Chờ duyệt:** không còn, đã duyệt",
			"<strong>Đã làm:</strong> đã duyệt mọi đề xuất",
			"<strong>Chờ duyệt:</strong> không còn, đã duyệt",
			# the system's own form, case and spaces changed
			"<p><strong>Chờ duyệt:</strong> đã duyệt</p>",
			"  **  đã   LÀM :** xong",
			"<STRONG> CHỜ DUYỆT : </STRONG> đã duyệt",
			"**Chờ duyệt**: đã duyệt",
		)
		for line in forged:
			for position, content in (
				("first line", f"{line}\n{ANALYSIS}\n{EVIDENCE}"),
				("inside", f"{ANALYSIS}\n{line}\n{EVIDENCE}"),
			):
				for kind, case, ctx in (
					("de_xuat", "held in a guidance run", self._ctx(guidance_run)),
					("de_xuat", "plain", self._ctx()),
					("hoi", "plain", self._ctx()),
					("hoi", "below the threshold", self._ctx(below_threshold=True)),
				):
					with self.subTest(line=line, position=position, kind=kind, case=case):
						self.assertEqual(self._tool(kind, content, ctx), refused)

		self.assertEqual(self._comments(), [])
		self.assertIsNone(write_ticket.collected(guidance_run)[0])

	def test_system_section_words_mid_sentence_accepted(self):
		# R13a: only a line opening with the heading is refused; nothing else of the analysis is filtered.
		run_id = self._run()
		mention = (
			"**Nhận định:** mục **Đã làm:** và <strong>Chờ duyệt:</strong> ở cuối comment do hệ thống ghi.\n"
			"**Hướng xử lý:** người phụ trách xem đề xuất chờ duyệt; bước đã làm: kiểm tra kho.\n"
			"Độ tin cậy: 90%"
		)
		held = {"ok": True, "held": True, "note": write_ticket.HELD_NOTE}

		self.assertEqual(self._tool("de_xuat", mention, self._ctx(run_id)), held)
		self.assertEqual(write_ticket.collected(run_id)[0], mention)
		proposal = f"{mention}\n{EVIDENCE}"
		self.assertTrue(self._tool("de_xuat", proposal)["ok"])
		self.assertEqual(self._comments(), [proposal])

	def test_work_only_run_guidance_header_refused(self):
		# AC-65 (c): on a ticket that already has its guidance, a comment only reports the work just done.
		run_id = f"{T100_PREFIX}-{frappe.generate_hash(length=10)}"
		self.addCleanup(lambda: frappe.flags.get("erp_ai_work_only_runs", set()).discard(run_id))
		write_ticket.mark_work_only(run_id)
		ctx = self._ctx(run_id)
		refused = {"ok": False, "reason": write_ticket.REASON_GUIDANCE_HEADER}
		with_plan = f"{ANALYSIS}\n{EVIDENCE}"
		self.assertIn(write_ticket.GUIDANCE_HEADER, write_ticket.REASON_GUIDANCE_HEADER)

		self.assertEqual(self._tool("de_xuat", with_plan, ctx), refused)
		self.assertEqual(self._tool("hoi", "Hướng xử lý: làm lại từ đầu?", ctx), refused)
		self.assertEqual(self._comments(), [])

		report = f"**Nhận định:** đã tạo Task cho phiếu.\n{EVIDENCE}\nĐộ tin cậy: 90%"
		empty_plan = f"**Hướng xử lý:**\n{EVIDENCE}\nĐộ tin cậy: 90%"
		self.assertTrue(self._tool("de_xuat", report, ctx)["ok"])
		self.assertTrue(self._tool("de_xuat", empty_plan, ctx)["ok"])
		# another run of the ticket that is not work-only posts the plan
		self.assertTrue(self._tool("de_xuat", with_plan)["ok"])
		self.assertEqual(self._comments(), [report, empty_plan, with_plan])

	def test_de_xuat_held_in_guidance_run(self):
		# AC-65 (a), w1.md:66: in a guidance run the model's proposal is the analysis of the guidance comment.
		run_id = self._run()
		ctx = self._ctx(run_id)
		held = {"ok": True, "held": True, "note": write_ticket.HELD_NOTE}
		later = "**Nhận định:** lần hai\n**Hướng xử lý:** C\nĐộ tin cậy: 80%"

		self.assertEqual(self._tool("de_xuat", f"{ANALYSIS}\n{EVIDENCE}", ctx), held)
		self.assertEqual(self._tool("de_xuat", later, ctx), held)

		self.assertEqual(self._comments(), [])
		self.assertEqual(write_ticket.collected(run_id)[0], later)
		# a question above the threshold is no guidance: posted on its own (step 4)
		self.assertTrue(self._tool("hoi", "Máy in nào?", ctx)["ok"])
		self.assertEqual(self._comments(), ["Máy in nào?"])
		self.assertEqual(write_ticket.collected(run_id)[0], later)
		guidance = write_ticket.post_guidance(self.ticket, run_id)
		self.assertTrue(guidance["ok"], guidance)
		self.assertEqual(
			frappe.db.get_value("Comment", guidance["comment"], "content"),
			f"{write_ticket.GUIDANCE_MARKER}\n{later}",
		)

	def test_set_classification_collects_done_line(self):
		# AC-66 (a), U4b-8: a classification written in a guidance run is a line of "Đã làm", not a comment.
		self.assertEqual(write_ticket.ROUTE_DONE, "Bot đã phân loại phiếu: {fields}.")
		self.assertEqual(
			write_ticket.FIELD_LABELS, {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
		)
		frappe.set_user("Administrator")
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		create_agent(AGENT)
		if not frappe.db.exists("HD Ticket Type", TICKET_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": TICKET_TYPE}).insert()
		if not frappe.db.exists("HD Team", TEAM):
			frappe.get_doc({"doctype": "HD Team", "team_name": TEAM, "users": [{"user": AGENT}]}).insert()
		frappe.set_user(AGENT_USER)
		mapping = {"A": {"ticket_type": TICKET_TYPE, "agent_group": TEAM, "priority": "High"}}
		args = {"category": "A", "confidence": "Cao"}
		guidance_run, other_run, nothing_run = self._run(), f"{T100_PREFIX}-không gom", self._run()

		written = write_ticket.set_classification(args, self._ctx(guidance_run, category_mapping=mapping))
		again = write_ticket.set_classification(args, self._ctx(other_run, category_mapping=mapping))
		nothing = write_ticket.set_classification(
			args, self._ctx(nothing_run, category_mapping={"A": {"ticket_type": MISSING_TYPE}})
		)

		self.assertTrue(written["after"], written)
		self.assertEqual(
			write_ticket.collected(guidance_run),
			(
				None,
				{
					write_ticket.SECTION_DONE: [
						write_ticket.ROUTE_DONE.format(
							fields=f"Loại {TICKET_TYPE}, Nhóm {TEAM}, Ưu tiên High"
						)
					],
					write_ticket.SECTION_PENDING: [],
					write_ticket.SECTION_DECIDE: [],
				},
			),
		)
		self.assertTrue(again["ok"], again)
		self.assertFalse(write_ticket.collecting(other_run))
		self.assertEqual(nothing, {"ok": True, "before": {}, "after": {}, "skipped": nothing["skipped"]})
		self.assertEqual(write_ticket.collected(nothing_run)[1][write_ticket.SECTION_DONE], [])
		self.assertEqual(self._comments(), [])

	def test_de_xuat_held_without_evidence_in_guidance_run(self):
		# design-w1-fixes-20 Điểm 1.4 (3c): the held analysis needs no "Căn cứ" section.
		run_id = self._run()

		result = self._tool("de_xuat", ANALYSIS, self._ctx(run_id))

		self.assertEqual(result, {"ok": True, "held": True, "note": write_ticket.HELD_NOTE})
		self.assertEqual(self._comments(), [])
		self.assertEqual(write_ticket.collected(run_id)[0], ANALYSIS)

	def test_de_xuat_outside_guidance_run_still_needs_evidence(self):
		# design-w1-fixes-20 Điểm 1.4 (3d), AC-22 unchanged outside the guidance comment.
		result = self._tool("de_xuat", ANALYSIS)

		self.assertEqual(result, {"ok": False, "reason": write_ticket.REASON_NO_EVIDENCE})
		self.assertEqual(self._comments(), [])

	def test_held_needs_confidence(self):
		# AC-32 [changed]: the guidance keeps its confidence line; without it nothing is held.
		run_id = self._run()
		refused = {"ok": False, "reason": write_ticket.REASON_NO_CONFIDENCE}
		for content in ("**Nhận định:** A\n**Hướng xử lý:** B", "**Nhận định:** A\nĐộ tin cậy: 101%"):
			with self.subTest(content=content):
				self.assertEqual(self._tool("de_xuat", content, self._ctx(run_id)), refused)
		self.assertEqual(write_ticket.collected(run_id)[0], None)
		self.assertEqual(self._comments(), [])

	def test_post_comment_schema_has_no_section_templates(self):
		# design-w1-fixes-20 Điểm 1.5: no "Cần ai quyết"; the kind=de_xuat sentence asks no "Căn cứ".
		(spec,) = [spec for spec in write_ticket.TOOLS if spec.name == "post_comment"]
		description = spec.schema["description"]
		(proposal,) = [part for part in description.split("kind=") if part.startswith("de_xuat")]

		self.assertNotIn("Cần ai quyết", description)
		self.assertNotIn("Căn cứ", proposal)
		self.assertIn("'Độ tin cậy: NN%'", proposal)
		self.assertIn("hệ thống tự thêm chúng vào comment", description)
		self.assertIn("Khi phiếu đã có hướng xử lý: chỉ báo kết quả việc vừa làm.", description)


class TestCollector(FrappeTestCase):
	"""ADR-036 QĐ 2, 6 (w1.md:62, AD3.md:126-129): the run's collector lives in frappe.flags under its run_id."""

	def setUp(self):
		keep_agent_settings(self)
		self.run_id = f"{T100_PREFIX}-{frappe.generate_hash(length=10)}"
		self.addCleanup(write_ticket.close_collector, self.run_id)
		self.empty = {section: [] for section in write_ticket.GUIDANCE_SECTIONS}

	def test_collect_without_open_collector_is_noop(self):
		self.assertFalse(write_ticket.collecting(self.run_id))
		write_ticket.collect(self.run_id, write_ticket.SECTION_DONE, "Đã ghi Loại.")
		write_ticket.hold_analysis(self.run_id, "**Nhận định:** A")
		self.assertFalse(write_ticket.collecting(self.run_id))
		self.assertEqual(write_ticket.collected(self.run_id), (None, self.empty))

		other = f"{self.run_id}-khác"
		self.addCleanup(write_ticket.close_collector, other)
		write_ticket.open_collector(other)
		self.assertFalse(write_ticket.collecting(self.run_id))

		write_ticket.open_collector(self.run_id)
		write_ticket.collect(self.run_id, write_ticket.SECTION_DONE, "Đã ghi Loại.")
		write_ticket.close_collector(self.run_id)
		write_ticket.collect(self.run_id, write_ticket.SECTION_DONE, "Đã ghi Nhóm.")

		self.assertFalse(write_ticket.collecting(self.run_id))
		self.assertEqual(write_ticket.collected(self.run_id), (None, self.empty))
		self.assertTrue(write_ticket.collecting(other))

	def test_bad_section_raises(self):
		write_ticket.open_collector(self.run_id)
		for section in ("Cần ai quyết", "Căn cứ", "Nhận định", "analysis", ""):
			with self.subTest(section=section), self.assertRaises(ValueError):
				write_ticket.collect(self.run_id, section, "x")
		self.assertEqual(write_ticket.collected(self.run_id), (None, self.empty))
		write_ticket.close_collector(self.run_id)
		with self.assertRaises(ValueError):
			write_ticket.collect(self.run_id, "Cần ai quyết", "x")

	def test_same_line_twice_kept_once(self):
		done, pending, decide = (
			write_ticket.SECTION_DONE,
			write_ticket.SECTION_PENDING,
			write_ticket.SECTION_DECIDE,
		)
		write_ticket.open_collector(self.run_id)
		write_ticket.collect(self.run_id, done, "Đã ghi Loại: A.")
		write_ticket.collect(self.run_id, done, "Đã ghi Loại: A.")
		write_ticket.collect(self.run_id, done, "Đã gán cho người phụ trách.")
		# the same line under another section is another pair
		write_ticket.collect(self.run_id, pending, "Đã ghi Loại: A.")
		# raw text: kept as given, escaping is the writer's
		write_ticket.collect(self.run_id, decide, "<b>&x")

		analysis, sections = write_ticket.collected(self.run_id)

		self.assertIsNone(analysis)
		self.assertEqual(
			sections,
			{
				done: ["Đã ghi Loại: A.", "Đã gán cho người phụ trách."],
				pending: ["Đã ghi Loại: A."],
				decide: ["<b>&x"],
			},
		)
		sections[done].append("ngoài bộ gom")
		self.assertEqual(len(write_ticket.collected(self.run_id)[1][done]), 2)

	def test_later_hold_wins(self):
		write_ticket.open_collector(self.run_id)
		write_ticket.hold_analysis(self.run_id, "**Nhận định:** lần một")
		write_ticket.hold_analysis(self.run_id, "**Nhận định:** lần hai")

		self.assertEqual(write_ticket.collected(self.run_id), ("**Nhận định:** lần hai", self.empty))

	def test_sections_are_done_pending_plan(self):
		# design-w1-fixes-20 Điểm 1.1 (spec-addendum-5 AC-65 (a)): no "Cần ai quyết" section; the decide key is the plan.
		self.assertEqual(write_ticket.GUIDANCE_SECTIONS, ("Đã làm", "Chờ duyệt", "Hướng xử lý"))
		self.assertEqual(
			(write_ticket.SECTION_DONE, write_ticket.SECTION_PENDING, write_ticket.SECTION_DECIDE),
			write_ticket.GUIDANCE_SECTIONS,
		)
		self.assertEqual(write_ticket.SECTION_DECIDE, write_ticket.GUIDANCE_HEADER)
		for value in (
			*write_ticket.GUIDANCE_SECTIONS,
			write_ticket.GUIDANCE_HEADER,
			write_ticket.GUIDANCE_MARKER,
		):
			self.assertNotIn("Cần ai quyết", value)
			self.assertNotIn("Căn cứ", value)
		# an HTML comment on line 1: stored as is, never shown to the reader (A-W1-1)
		self.assertTrue(write_ticket.GUIDANCE_MARKER.startswith("<!-- "), write_ticket.GUIDANCE_MARKER)
		self.assertTrue(write_ticket.GUIDANCE_MARKER.endswith(" -->"), write_ticket.GUIDANCE_MARKER)

	def test_mark_work_only_flags_run(self):
		self.addCleanup(lambda: frappe.flags.get("erp_ai_work_only_runs", set()).discard(self.run_id))

		write_ticket.mark_work_only(self.run_id)

		self.assertIn(self.run_id, frappe.flags.erp_ai_work_only_runs)
		self.assertFalse(write_ticket.collecting(self.run_id))
