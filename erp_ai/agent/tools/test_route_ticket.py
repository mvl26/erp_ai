import ast
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.desk.form import assign_to
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent.classification import Classification
from erp_ai.agent.labels import IGNORED_LABELS
from erp_ai.agent.routing import RouteDecision
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.agent.tools.route_ticket import (
	ASSIGN_REQUEST,
	NO_SLA,
	REASON_ASSIGN_FAILED,
	REASON_NO_VALID_ASSIGNEE,
	REASON_TASK_NOT_ASSIGNED,
	TASK_REQUEST,
	TaskSharingDisabled,
	add_labels,
	apply_route,
	assign_owner,
	create_routed_task,
	post_routing_comment,
)
from erp_ai.constants import AGENT_USER, CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN, MESSAGE_DOCTYPE
from erp_ai.test_utils import PREFIX, make_active_agent, make_sla, make_team, pin_agent_roles

SCORE_FIELDS = ("ai_complexity", "ai_importance", "ai_score_reason")
CLASSIFICATION_REASON_FIELD = "ai_classification_reason"
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
	def test_classification_reason_stored_on_the_ticket(self):
		# Why the model classified the ticket so is ticket information: it is stored with the route.
		ticket = self._ticket(priority="Low")
		reason = "ERPAI-TEST người dùng hỏi cách dùng"
		result = self._apply_as_agent(ticket, classification=self._classification(reason=reason))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["after"][CLASSIFICATION_REASON_FIELD], reason)
		self.assertEqual(frappe.db.get_value("HD Ticket", ticket, CLASSIFICATION_REASON_FIELD), reason)

	def test_classification_without_reason_writes_no_reason(self):
		ticket = self._ticket(priority="Low")
		result = self._apply_as_agent(ticket)
		self.assertTrue(result["ok"], result)
		self.assertNotIn(CLASSIFICATION_REASON_FIELD, result["after"])
		self.assertFalse(frappe.db.get_value("HD Ticket", ticket, CLASSIFICATION_REASON_FIELD))

	def test_classification_without_reason_clears_an_earlier_reason(self):
		# A reason left by an earlier classification would describe the wrong one.
		ticket = self._ticket(priority="Low")
		frappe.db.set_value("HD Ticket", ticket, CLASSIFICATION_REASON_FIELD, "lý do của lần trước")
		result = self._apply_as_agent(ticket)
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["after"][CLASSIFICATION_REASON_FIELD], "")
		self.assertFalse(frappe.db.get_value("HD Ticket", ticket, CLASSIFICATION_REASON_FIELD))

	def test_scores_written_readable_by_agent_role_user(self):
		# Priority is set explicitly so the changed set does not depend on the site's default SLA priority.
		ticket = self._ticket(priority="Low")
		result = self._apply_as_agent(ticket, classification=self._classification(confidence_pct=70))
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
				"ai_confidence_pct": 70,
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
			category="E", complexity=1, importance=2, score_reason="E có điểm", confidence_pct=60
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
			set(result["after"]),
			{"ai_confidence", "ai_complexity", "ai_importance", "ai_score_reason", "ai_confidence_pct"},
		)


PCT_FIELD = "ai_confidence_pct"
PCT_WRITERS = {"agent/tools/route_ticket.py", "install.py"}
SETTER_NAMES = {"set", "db_set", "set_value"}


def _pct_writes(source: str) -> list[int]:
	"""Line numbers where `source` assigns `ai_confidence_pct` (design Fix 5 checkable constraint)."""
	lines = []
	for node in ast.walk(ast.parse(source)):
		if isinstance(node, ast.keyword) and node.arg == PCT_FIELD:
			lines.append(node.value.lineno)
		elif isinstance(node, ast.Attribute) and node.attr == PCT_FIELD and isinstance(node.ctx, ast.Store):
			lines.append(node.lineno)
		elif isinstance(node, ast.Dict):
			lines.extend(
				key.lineno for key in node.keys if isinstance(key, ast.Constant) and key.value == PCT_FIELD
			)
		elif (
			isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute | ast.Name)
			and getattr(node.func, "attr", getattr(node.func, "id", None)) in SETTER_NAMES
		):
			lines.extend(
				arg.lineno for arg in node.args if isinstance(arg, ast.Constant) and arg.value == PCT_FIELD
			)
	return sorted(lines)


class TestConfidencePct(RouteTicketTestCase):
	def test_apply_route_writes_confidence_pct(self):
		ticket = self._ticket()
		result = self._apply_as_agent(ticket, classification=self._classification(confidence_pct=85))
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["after"].get(PCT_FIELD), 85)
		self.assertIn(PCT_FIELD, result["before"])
		# An Int column of Frappe 15 is NOT NULL DEFAULT 0: a ticket never routed reads 0, not None.
		self.assertEqual(result["before"][PCT_FIELD], 0)
		self.assertEqual(frappe.db.get_value("HD Ticket", ticket, PCT_FIELD), 85)

	def test_human_classified_pct_not_written(self):
		ticket = self._ticket()
		frappe.db.set_value("HD Ticket", ticket, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		result = self._apply_as_agent(ticket, classification=self._classification(confidence_pct=85))
		self.assertFalse(result["ok"])
		self.assertFalse(frappe.db.get_value("HD Ticket", ticket, PCT_FIELD))

	def test_only_route_ticket_assigns_ai_confidence_pct(self):
		# The scanner sees each of the four write forms the design names.
		sample = (
			"f(ai_confidence_pct=1)\n"
			"doc.ai_confidence_pct = 1\n"
			"doc.update({'ai_confidence_pct': 1})\n"
			"frappe.db.set_value('HD Ticket', n, 'ai_confidence_pct', 1)\n"
			"doc.get('ai_confidence_pct')\n"
		)
		self.assertEqual(_pct_writes(sample), [1, 2, 3, 4])

		root = Path(frappe.get_app_path("erp_ai"))
		writers = {}
		for path in sorted(root.rglob("*.py")):
			if path.name.startswith("test_"):
				continue
			if lines := _pct_writes(path.read_text(encoding="utf-8")):
				writers[path.relative_to(root).as_posix()] = lines
		self.assertLessEqual(set(writers), PCT_WRITERS, writers)
		self.assertIn("agent/tools/route_ticket.py", writers)


class TestAddLabels(RouteTicketTestCase):
	"""ADR-049: the labels of the classification become Helpdesk Tags of the ticket, added, never removed."""

	def _tags(self, ticket):
		return frappe.db.get_value("HD Ticket", ticket, "_user_tags") or ""

	def _links(self, ticket):
		# Helpdesk tags a requester's first ticket itself
		rows = frappe.get_all(
			"Tag Link", filters={"document_type": "HD Ticket", "document_name": ticket}, pluck="tag"
		)
		return sorted(tag for tag in rows if tag not in IGNORED_LABELS)

	def _add_as_agent(self, ticket, names):
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		return add_labels(names, self._ctx(ticket))

	def test_labels_become_tags_of_the_ticket_as_the_agent(self):
		ticket = self._ticket()
		names = (f"{PREFIX}Kho", f"{PREFIX}In ấn")

		result = self._add_as_agent(ticket, names)

		self.assertEqual(result, {"ok": True, "added": list(names)})
		self.assertEqual(self._links(ticket), sorted(names))
		for name in names:
			self.assertIn(name, self._tags(ticket).split(","))
			# claimed for helpdesk, so the Tags box lists it
			self.assertEqual(frappe.db.get_value("Tag", name, "app"), "helpdesk")

	def test_a_tag_the_ticket_has_is_kept_and_not_added_twice(self):
		ticket = self._ticket()
		person = f"{PREFIX}người gắn"
		frappe.get_doc("HD Ticket", ticket).add_tag(person)
		frappe.get_doc("HD Ticket", ticket).add_tag(f"{PREFIX}Kho")

		result = self._add_as_agent(ticket, (f"{PREFIX}kho", f"{PREFIX}Mới"))

		self.assertEqual(result["added"], [f"{PREFIX}Mới"])
		self.assertEqual(self._links(ticket), sorted([person, f"{PREFIX}Kho", f"{PREFIX}Mới"]))

	def test_existing_tag_keeps_its_spelling(self):
		frappe.get_doc({"doctype": "Tag", "name": f"{PREFIX}Delivery Note"}).insert(ignore_permissions=True)
		ticket = self._ticket()

		result = self._add_as_agent(ticket, (f"{PREFIX}delivery note",))

		self.assertEqual(result["added"], [f"{PREFIX}Delivery Note"])
		self.assertEqual(self._links(ticket), [f"{PREFIX}Delivery Note"])

	def test_no_labels_writes_nothing(self):
		ticket = self._ticket()
		before = self._tags(ticket)
		self.assertEqual(self._add_as_agent(ticket, ()), {"ok": True, "added": []})
		self.assertEqual(self._tags(ticket), before)

	def test_user_without_write_permission_refused(self):
		ticket = self._ticket()
		real = Document.has_permission

		def deny_write(doc, permtype="read", *args, **kwargs):
			return False if permtype == "write" else real(doc, permtype, *args, **kwargs)

		with patch.object(Document, "has_permission", deny_write):
			result = self._add_as_agent(ticket, (f"{PREFIX}Kho",))
		self.assertFalse(result["ok"])
		self.assertEqual(self._links(ticket), [])


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


class TestAssignOwner(RouteTicketTestCase):
	def _count(self, doctype: str, **filters) -> int:
		return frappe.db.count(doctype, filters)

	def _assign_as_agent(self, ticket: str, user: str) -> dict:
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		return assign_owner(user, self._ctx(ticket))

	def test_ticket_never_shared_one_todo_one_notification(self):
		ticket = self._ticket()
		owner = make_active_agent(self)
		todo = {"reference_type": "HD Ticket", "reference_name": ticket, "allocated_to": owner}
		note = {"document_type": "HD Ticket", "document_name": ticket, "for_user": owner}
		real_add = assign_to.add
		with patch.object(assign_to, "add", wraps=real_add) as add:
			result = self._assign_as_agent(ticket, owner)
		self.assertEqual(result, {"ok": True, "assignee": owner})
		# Exactly Frappe's public `add` with exactly these args: no extra flag, no private variant.
		add.assert_called_once_with({"assign_to": [owner], "doctype": "HD Ticket", "name": ticket})
		self.assertEqual(self._count("ToDo", status="Open", **todo), 1)
		self.assertEqual(self._count("Notification Log", type="Assignment", **note), 1)
		self.assertEqual(self._count("DocShare", share_doctype="HD Ticket", share_name=ticket), 0)

	def test_no_read_permission_refused(self):
		ticket = self._ticket()
		owner = make_active_agent(self)
		real = Document.has_permission

		def deny_read(doc, permtype="read", *args, **kwargs):
			return False if permtype == "read" else real(doc, permtype, *args, **kwargs)

		with patch.object(Document, "has_permission", deny_read), patch.object(assign_to, "add") as add:
			result = self._assign_as_agent(ticket, owner)
		self.assertFalse(result["ok"])
		self.assertTrue(result["reason"])
		self.assertLessEqual(len(result["reason"]), 200)
		add.assert_not_called()
		self.assertEqual(self._count("ToDo", reference_type="HD Ticket", reference_name=ticket), 0)

	def test_denied_write_does_not_block_assignment(self):
		# Only `read` on the ticket gates the assignment: a write denial alone must not refuse it.
		ticket = self._ticket()
		owner = make_active_agent(self)
		real = Document.has_permission

		def deny_write(doc, permtype="read", *args, **kwargs):
			return False if permtype == "write" else real(doc, permtype, *args, **kwargs)

		with patch.object(Document, "has_permission", deny_write):
			result = self._assign_as_agent(ticket, owner)
		self.assertEqual(result, {"ok": True, "assignee": owner})


class TestRoutingComment(RouteTicketTestCase):
	def _comments(self, ticket: str) -> list[str]:
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "HD Ticket", "reference_name": ticket, "comment_type": "Comment"},
			pluck="content",
		)

	def test_lines_joined_in_one_message(self):
		# ADR-050: one message of the ticket's conversation, no comment
		ticket = self._ticket()
		lines = [ASSIGN_REQUEST.format(reason=REASON_ASSIGN_FAILED), NO_SLA]
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		result = post_routing_comment(lines, self._ctx(ticket))
		self.assertTrue(result["ok"], result)
		said = frappe.get_all(MESSAGE_DOCTYPE, filters={"ticket": ticket}, pluck="content")
		self.assertEqual(said, ["\n".join(lines)])
		self.assertEqual(self._comments(ticket), [])

	def test_fixed_sentences(self):
		self.assertEqual(NO_SLA, "Chưa có SLA áp vào phiếu, cần System Manager cấu hình.")
		reasons = {
			REASON_NO_VALID_ASSIGNEE: "cấu hình không có người hợp lệ",
			REASON_ASSIGN_FAILED: "gán người không thành công",
		}
		for reason, text in reasons.items():
			with self.subTest(reason=text):
				self.assertEqual(reason, text)
				self.assertEqual(
					ASSIGN_REQUEST.format(reason=reason),
					f"Bot chưa gán được người phụ trách cho phiếu này: {text}. Nhờ trưởng nhóm phân công.",
				)

	def test_task_refused_sentence_is_its_own(self):
		self.assertEqual(REASON_TASK_NOT_ASSIGNED, "chia sẻ tài liệu đang tắt")
		sentence = TASK_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED)
		self.assertEqual(
			sentence,
			"Bot đã gán người phụ trách cho phiếu nhưng không giao được Task: chia sẻ tài liệu đang tắt. "
			"Nhờ trưởng nhóm giao Task.",
		)
		self.assertNotIn("chưa gán được người", sentence)


class TestCreateRoutedTask(RouteTicketTestCase):
	def _create_as_agent(self, ticket: str, user: str, subject: str = "ERPAI-TEST việc", classification=None):
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		return create_routed_task(user, subject, classification or self._classification(), self._ctx(ticket))

	def _task_count(self) -> int:
		return frappe.db.count("Task", {"subject": ("like", f"{PREFIX}%")})

	def _assert_refused(self, result, add):
		self.assertFalse(result["ok"], result)
		self.assertTrue(result["reason"])
		self.assertLessEqual(len(result["reason"]), 200)
		add.assert_not_called()
		self.assertEqual(self._task_count(), 0)

	def test_assignee_without_projects_user_gets_share(self):
		ticket = self._ticket()
		owner = make_active_agent(self)
		self.assertNotIn("Projects User", frappe.get_roles(owner))
		result = self._create_as_agent(ticket, owner)
		self.assertTrue(result["ok"], result)
		share = {"share_doctype": "Task", "share_name": result["task"], "user": owner, "read": 1}
		self.assertEqual(frappe.db.count("DocShare", share), 1)
		self.assertTrue(frappe.has_permission("Task", "read", doc=result["task"], user=owner))

	def test_assign_to_add_called_on_task_with_one_todo(self):
		ticket = self._ticket()
		owner = make_active_agent(self)
		with patch.object(assign_to, "add", wraps=assign_to.add) as add:
			result = self._create_as_agent(ticket, owner)
		self.assertTrue(result["ok"], result)
		add.assert_called_once_with({"assign_to": [owner], "doctype": "Task", "name": result["task"]})
		todo = {"reference_type": "Task", "reference_name": result["task"], "allocated_to": owner}
		self.assertEqual(frappe.db.count("ToDo", {**todo, "status": "Open"}), 1)

	def test_task_references_ticket(self):
		ticket = self._ticket()
		result = self._create_as_agent(ticket, make_active_agent(self))
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Task", result["task"], "ai_ticket"), ticket)

	def test_subject_cut_to_140_chars(self):
		ticket = self._ticket()
		long_subject = f"{PREFIX}" + "".join(chr(97 + i % 26) for i in range(200))
		result = self._create_as_agent(ticket, make_active_agent(self), subject=long_subject)
		self.assertTrue(result["ok"], result)
		self.assertEqual(frappe.db.get_value("Task", result["task"], "subject"), long_subject[:140])

	def test_description_has_ticket_link_first(self):
		ticket = self._ticket()
		result = self._create_as_agent(ticket, make_active_agent(self))
		self.assertTrue(result["ok"], result)
		description = frappe.db.get_value("Task", result["task"], "description")
		self.assertIn(f'<a href="/helpdesk/tickets/{ticket}"', description)
		self.assertLess(description.index("/helpdesk/tickets/"), description.index("Độ phức tạp"))

	def test_description_escaped_and_has_scores(self):
		ticket = self._ticket()
		classification = self._classification(
			complexity=2, importance=3, score_reason="<img src=x onerror=alert(1)> & lý do"
		)
		result = self._create_as_agent(ticket, make_active_agent(self), classification=classification)
		self.assertTrue(result["ok"], result)
		description = frappe.db.get_value("Task", result["task"], "description")
		self.assertIn("Độ phức tạp 2/3, độ quan trọng 3/3: ", description)
		self.assertIn("&lt;img src=x onerror=alert(1)&gt; &amp; lý do", description)
		self.assertNotIn("<img", description)

	def test_sharing_disabled_raises(self):
		ticket = self._ticket()
		owner = make_active_agent(self)
		real = frappe.get_system_settings

		def settings(key):
			return 1 if key == "disable_document_sharing" else real(key)

		with patch.object(frappe, "get_system_settings", settings):
			with self.assertRaises(TaskSharingDisabled):
				self._create_as_agent(ticket, owner)

	def test_no_task_doctype_refused(self):
		ticket = self._ticket()
		real = frappe.db.exists

		def no_task(dt, *args, **kwargs):
			return None if dt == "DocType" and args == ("Task",) else real(dt, *args, **kwargs)

		with patch.object(frappe.db, "exists", no_task), patch.object(assign_to, "add") as add:
			result = self._create_as_agent(ticket, make_active_agent(self))
		self._assert_refused(result, add)

	def test_no_task_create_permission_refused(self):
		ticket = self._ticket()
		real = frappe.has_permission

		def deny_create(doctype=None, ptype="read", *args, user=None, **kwargs):
			if doctype == "Task" and ptype == "create" and user in (None, AGENT_USER):
				return False
			return real(doctype, ptype, *args, user=user, **kwargs)

		with patch.object(frappe, "has_permission", deny_create), patch.object(assign_to, "add") as add:
			result = self._create_as_agent(ticket, make_active_agent(self))
		self._assert_refused(result, add)

	def test_no_ticket_read_permission_refused(self):
		ticket = self._ticket()
		real = Document.has_permission

		def deny_read(doc, permtype="read", *args, **kwargs):
			if permtype == "read" and doc.doctype == "HD Ticket" and frappe.session.user == AGENT_USER:
				return False
			return real(doc, permtype, *args, **kwargs)

		with patch.object(Document, "has_permission", deny_read), patch.object(assign_to, "add") as add:
			result = self._create_as_agent(ticket, make_active_agent(self))
		self._assert_refused(result, add)
