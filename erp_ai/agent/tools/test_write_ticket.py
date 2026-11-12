from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.tools import registry, write_ticket
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import AGENT_USER, CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN, ROLE_AGENT

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
		result = self._run(AGENT)
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
		result = self._run(AGENT, mapping)
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
		args = {"subject": "ERPAI-TEST-T26 việc", "description": "Kiểm tra máy in"}
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
		args = {"subject": "ERPAI-TEST-T26 việc", "description": "Dòng 1\nDòng 2 <b>x</b>"}
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
		result = self._call(write_ticket.create_task, T26_AGENT_ONLY, {"subject": "s", "description": "d"})
		self._assert_refused(result)
		self.assertIn("Task", result["reason"])
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_requires_instructor(self):
		before = frappe.db.count("Task")
		args = {"subject": "ERPAI-TEST-T26 việc", "description": "x"}
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
			result = self._call(write_ticket.create_task, T26_AGENT, {"subject": "s", "description": "d"})
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
			result = self._call(write_ticket.create_task, T26_AGENT, {"subject": "s", "description": "d"})
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	def test_create_task_without_ticket_access_returns_ok_false(self):
		_make_user(T26_OUTSIDER, "Projects User")
		before = frappe.db.count("Task")
		result = self._call(write_ticket.create_task, T26_OUTSIDER, {"subject": "s", "description": "d"})
		self._assert_refused(result)
		self.assertEqual(frappe.db.count("Task"), before)

	# shared

	def test_handlers_do_not_commit(self):
		with patch.object(frappe.db, "commit") as commit:
			self._call(write_ticket.set_resolution_hint, T26_AGENT, {"text": "x"})
			self._call(write_ticket.post_comment, T26_AGENT, {"content": "x"})
			self._call(write_ticket.create_task, T26_AGENT, {"subject": "s", "description": "d"})
		commit.assert_not_called()

	def test_new_tool_schemas_take_no_doctype_or_field_names(self):
		specs = {spec.name: spec for spec in write_ticket.TOOLS}
		expected = {
			"set_resolution_hint": ("ticket_write", {"text"}),
			"post_comment": ("ticket_write", {"content"}),
			"create_task": ("task_write", {"subject", "description"}),
		}
		for name, (group, properties) in expected.items():
			with self.subTest(tool=name):
				spec = specs[name]
				self.assertEqual(spec.group, group)
				self.assertIs(spec.handler, getattr(write_ticket, name))
				input_schema = spec.schema["input_schema"]
				self.assertEqual(set(input_schema["properties"]), properties)
				self.assertEqual(set(input_schema["required"]), properties)
				for rule in input_schema["properties"].values():
					self.assertEqual(rule["type"], "string")
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
				("post_comment", {"content": "x", "doctype": "User"}),
				("create_task", {"subject": "s", "description": "d", "doctype": "User"}),
			):
				with self.subTest(tool=name):
					self.assertFalse(execute_tool(name, args, self._ctx())["ok"])
			no_instructor = execute_tool("create_task", {"subject": "s", "description": "d"}, self._ctx(None))
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
		result = write_ticket.create_task({"subject": "ERPAI-TEST-T16 việc", "description": "mô tả"}, ctx)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Task", result["task"], "ai_ticket"), self.ticket)
