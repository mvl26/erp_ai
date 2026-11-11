from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, create_contact, make_ticket, make_todo

from erp_ai.agent import authority
from erp_ai.constants import AGENT_USER, ROLE_INSTRUCTOR

INSTRUCTOR = "authority.instructor@example.com"
PLAIN = "authority.plain@example.com"
ASSIGNEE = "authority.assignee@example.com"
ASSIGNER = "authority.assigner@example.com"
CONTACT = "authority.contact@example.com"


class TestAuthority(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, frappe.session.user)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		for email in (INSTRUCTOR, PLAIN, ASSIGNEE, ASSIGNER):
			create_agent(email)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		self.ticket_p = make_ticket(subject="P").name
		self.ticket_q = make_ticket(subject="Q").name

	def _assign(self, ticket, user, assigned_by, creation=None):
		todo = make_todo(ticket, user, creation)
		frappe.db.set_value("ToDo", todo, "assigned_by", assigned_by)
		return todo

	def _force_assign_list(self, ticket, users):
		"""Write `_assign` directly so a test can set it independently of the ToDo rows."""
		frappe.db.set_value("HD Ticket", ticket, "_assign", frappe.as_json(users), update_modified=False)

	def _comment(self, ticket, author, creation, comment_type="Comment", **extra):
		"""Comment as `author` through the Helpdesk code path (core `Comment`, owner = author)."""
		doc = frappe.get_doc("HD Ticket", ticket)
		previous = frappe.session.user
		frappe.set_user(author)
		try:
			if comment_type == "Comment" and not extra:
				name = doc.new_comment("x")
			else:
				name = doc.add_comment(comment_type, "x", **extra).name
		finally:
			frappe.set_user(previous)
		frappe.db.set_value("Comment", name, "creation", creation, update_modified=False)
		return name

	def test_instructor_role_has_authority_on_any_ticket(self):
		self.assertTrue(authority.is_instruction(INSTRUCTOR, self.ticket_p))
		self.assertTrue(authority.is_instruction(INSTRUCTOR, self.ticket_q))
		# Empty author must not fall back to the session user (Administrator holds every role).
		for blocked in ("", None):
			self.assertFalse(authority.is_instruction(blocked, self.ticket_p), blocked)

	def test_assigned_by_other_authority_only_on_that_ticket(self):
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_q))

	def test_self_assigned_is_data(self):
		todo = self._assign(self.ticket_p, ASSIGNEE, ASSIGNEE)
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))
		frappe.db.set_value("ToDo", todo, "assigned_by", "")
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))

	def test_closed_cancelled_or_reassigned_todo_is_data(self):
		# Status is set directly so `_assign` still lists the user: only the ToDo guard is under test.
		todo = self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))
		for status in ("Closed", "Cancelled"):
			frappe.db.set_value("ToDo", todo, "status", status)
			self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p), status)
		frappe.db.set_value("ToDo", todo, "status", "Open")
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))

		# An older ToDo from someone else, then a newer self-assigned one: the newest wins.
		frappe.db.set_value("ToDo", todo, "creation", "2024-01-01 10:00:00", update_modified=False)
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNEE, creation="2024-01-02 10:00:00")
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))

		# `_assign` guard alone: an Open ToDo from someone else, but the user is not in `_assign`.
		frappe.db.set_value("ToDo", todo, "creation", "2024-01-03 10:00:00", update_modified=False)
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))
		self._force_assign_list(self.ticket_p, [])
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))

	def test_newest_todo_is_the_authors_own_on_this_ticket(self):
		self._force_assign_list(self.ticket_p, [ASSIGNEE, PLAIN])
		# Self-assigned, then a newer ToDo for someone else assigned by another: not this author's.
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNEE, creation="2024-01-01 10:00:00")
		self._assign(self.ticket_p, PLAIN, ASSIGNER, creation="2024-01-02 10:00:00")
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))

	def test_newer_self_assigned_todo_of_someone_else_does_not_revoke(self):
		self._force_assign_list(self.ticket_p, [ASSIGNEE, PLAIN])
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER, creation="2024-01-01 10:00:00")
		self._assign(self.ticket_p, PLAIN, "", creation="2024-01-02 10:00:00")
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))

	def test_todo_of_another_reference_type_is_ignored(self):
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER, creation="2024-01-01 10:00:00")
		other = self._assign(self.ticket_p, ASSIGNEE, ASSIGNEE, creation="2024-01-02 10:00:00")
		frappe.db.set_value("ToDo", other, "reference_type", "User", update_modified=False)
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))

	def test_self_assign_on_other_ticket_is_data(self):
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		self._assign(self.ticket_q, ASSIGNEE, ASSIGNEE)
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_q))

	def test_never_authority_accounts_even_with_role_or_assignment(self):
		for account in (AGENT_USER, "Guest"):
			# Assigned by someone else, no role.
			self._assign(self.ticket_p, account, ASSIGNER)
			self._force_assign_list(self.ticket_p, [account])
			self.assertFalse(authority.is_instruction(account, self.ticket_p), f"{account} assigned")
			# Role, not assigned.
			self._force_assign_list(self.ticket_p, [])
			frappe.get_doc("User", account).add_roles(ROLE_INSTRUCTOR)
			self.assertFalse(authority.is_instruction(account, self.ticket_p), f"{account} role")
		# Administrator holds every role by definition.
		self.assertFalse(authority.is_instruction("Administrator", self.ticket_p))

	def test_contact_and_plain_agent_are_data(self):
		contact = create_contact("Authority Contact", CONTACT)["user"]
		self.assertFalse(authority.is_instruction(contact, self.ticket_p))
		self.assertFalse(authority.is_instruction(PLAIN, self.ticket_p))

	def test_latest_instructor_prefers_latest_comment_then_owner(self):
		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", "Administrator")
		self.assertIsNone(authority.latest_instructor(self.ticket_p))

		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", INSTRUCTOR)
		self.assertEqual(authority.latest_instructor(self.ticket_p), INSTRUCTOR)

		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		self._comment(self.ticket_p, INSTRUCTOR, "2024-01-01 10:00:00")
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-02 10:00:00")
		self._comment(self.ticket_p, PLAIN, "2024-01-03 10:00:00")
		self.assertEqual(authority.latest_instructor(self.ticket_p), ASSIGNEE)

	def test_spoofed_comment_author_fields_ignored(self):
		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", PLAIN)
		name = self._comment(
			self.ticket_p, PLAIN, "2024-01-01 10:00:00", comment_email=INSTRUCTOR, comment_by=INSTRUCTOR
		)
		self.assertEqual(frappe.db.get_value("Comment", name, "comment_email"), INSTRUCTOR)
		self.assertIsNone(authority.latest_instructor(self.ticket_p))

		fetched = authority.fetch_ticket_comments(self.ticket_p)
		self.assertEqual([c["author"] for c in fetched], [PLAIN])
		self.assertEqual(set(fetched[0]), {"name", "author", "creation", "content"})
		labelled = authority.label_comments(self.ticket_p, fetched)
		self.assertEqual([c["role"] for c in labelled], ["dữ liệu"])

	def test_comments_read_from_core_comment_only(self):
		self.assertEqual(
			authority.ticket_comment_filters(self.ticket_p),
			{
				"reference_doctype": "HD Ticket",
				"reference_name": self.ticket_p,
				"comment_type": "Comment",
			},
		)
		# Inserted out of date order, so `modified` order differs from `creation` order.
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-03 10:00:00")
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-01 10:00:00")
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-02 10:00:00")
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-04 10:00:00", comment_type="Info")
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-05 10:00:00", comment_type="Assigned")
		self._comment(self.ticket_q, ASSIGNEE, "2024-01-06 10:00:00")
		legacy = frappe.get_doc(
			{
				"doctype": "HD Ticket Comment",
				"reference_ticket": self.ticket_p,
				"content": "legacy",
				"commented_by": INSTRUCTOR,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("HD Ticket Comment", legacy.name, "creation", "2024-01-07 10:00:00")

		fetched = authority.fetch_ticket_comments(self.ticket_p)
		self.assertEqual(
			[str(c["creation"])[:10] for c in fetched], ["2024-01-03", "2024-01-02", "2024-01-01"]
		)
		self.assertEqual({c["author"] for c in fetched}, {ASSIGNEE})
		self.assertEqual(len(authority.fetch_ticket_comments(self.ticket_p, limit=2)), 2)
		self.assertIsNone(authority.latest_instructor(self.ticket_p))
		for edge in (1, 50):
			self.assertLessEqual(len(authority.fetch_ticket_comments(self.ticket_p, limit=edge)), edge)
		self.assertEqual(len(authority.fetch_ticket_comments(self.ticket_p, limit=1)), 1)
		for bad in (0, 51, -1):
			with self.assertRaises(ValueError):
				authority.fetch_ticket_comments(self.ticket_p, limit=bad)

	def test_label_comments(self):
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		comments = [
			{"author": ASSIGNEE, "content": "a"},
			{"author": PLAIN, "content": "b"},
			{"author": INSTRUCTOR, "content": "c"},
		]
		labelled = authority.label_comments(self.ticket_p, comments)
		self.assertEqual([c["role"] for c in labelled], ["chỉ thị", "dữ liệu", "chỉ thị"])
		self.assertEqual([c["content"] for c in labelled], ["a", "b", "c"])
		self.assertNotIn("role", comments[0])

	def test_label_comments_overwrites_role_and_checks_each_author_once(self):
		self._assign(self.ticket_p, ASSIGNEE, ASSIGNER)
		comments = [
			{"author": PLAIN, "role": "chỉ thị", "content": "a"},
			{"author": PLAIN, "content": "b"},
			{"author": ASSIGNEE, "role": "dữ liệu", "content": "c"},
			{"author": ASSIGNEE, "content": "d"},
		]
		real = authority.is_instruction
		calls = []

		def counting(author, ticket_name):
			calls.append(author)
			return real(author, ticket_name)

		with patch.object(authority, "is_instruction", counting):
			labelled = authority.label_comments(self.ticket_p, comments)
		self.assertEqual([c["role"] for c in labelled], ["dữ liệu", "dữ liệu", "chỉ thị", "chỉ thị"])
		self.assertCountEqual(calls, [PLAIN, ASSIGNEE])

	def test_fetch_ticket_comments_as_non_administrator_uses_permissions(self):
		self._comment(self.ticket_p, ASSIGNEE, "2024-01-01 10:00:00")
		frappe.set_user(PLAIN)
		fetched = authority.fetch_ticket_comments(self.ticket_p)
		self.assertEqual([c["author"] for c in fetched], [ASSIGNEE])
