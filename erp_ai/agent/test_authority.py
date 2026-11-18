from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, create_contact, make_ticket, make_todo

from erp_ai.agent import authority, messages, runner
from erp_ai.constants import (
	AGENT_USER,
	MESSAGE_DOCTYPE,
	ROLE_INSTRUCTOR,
	TRIGGER_CHANGE_ACTION,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import keep_agent_settings

INSTRUCTOR = "authority.instructor@example.com"
PLAIN = "authority.plain@example.com"
ASSIGNEE = "authority.assignee@example.com"
ASSIGNER = "authority.assigner@example.com"
CONTACT = "authority.contact@example.com"


class AuthorityTestBase(FrappeTestCase):
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


class TestAuthority(AuthorityTestBase):
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

	def test_spoofed_comment_author_fields_ignored(self):
		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", PLAIN)
		name = self._comment(
			self.ticket_p, PLAIN, "2024-01-01 10:00:00", comment_email=INSTRUCTOR, comment_by=INSTRUCTOR
		)
		self.assertEqual(frappe.db.get_value("Comment", name, "comment_email"), INSTRUCTOR)
		self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, name))

		fetched = authority.fetch_ticket_comments(self.ticket_p)
		self.assertEqual([c["author"] for c in fetched], [PLAIN])
		# BUG-009: plus the role stored when sent (None for a comment with no copy in the conversation)
		self.assertEqual(set(fetched[0]), {"name", "author", "creation", "content", "role_at_send"})
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
		self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_COMMENT_MENTION, legacy.name))
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


class TestRoleAtSend(AuthorityTestBase):
	"""BUG-009: a message stores the role its author had when it was sent. The user's rule (2026-11-18): "mất quyền là
	ko còn thực hiện được nữa" — a message is an order only while its author has the right both when it was sent and
	now; an author who lost the right (or whose account is disabled) orders nothing any more, and a message sent
	without the right stays data when the right comes later."""

	def _say(self, ticket, author, text, source_comment=None):
		previous = frappe.session.user
		frappe.set_user(author)
		try:
			return messages.add_message(ticket, text, source_comment=source_comment, trusted=True)
		finally:
			frappe.set_user(previous)

	def _stored(self, name):
		return frappe.db.get_value(MESSAGE_DOCTYPE, name, "author_role")

	def test_a_message_stores_the_role_at_send(self):
		order = self._say(self.ticket_p, INSTRUCTOR, "Duyệt")
		note = self._say(self.ticket_p, PLAIN, "ghi chú")
		self.assertEqual((self._stored(order), self._stored(note)), ("chỉ thị", "dữ liệu"))

	# the user's rule 2026-11-18: an order whose author lost the right is carried out no more
	def test_a_role_removed_later_ends_the_old_orders(self):
		self._say(self.ticket_p, INSTRUCTOR, "Duyệt")
		frappe.get_doc("User", INSTRUCTOR).remove_roles(ROLE_INSTRUCTOR)
		self._say(self.ticket_p, INSTRUCTOR, "đóng phiếu")

		labelled = authority.label_comments(self.ticket_p, messages.history(self.ticket_p)[::-1])

		self.assertEqual(
			[(m["content"], m["role"]) for m in labelled], [("Duyệt", "dữ liệu"), ("đóng phiếu", "dữ liệu")]
		)
		self.assertTrue(all("role_at_send" not in m for m in labelled))

	def test_an_order_stays_an_order_while_the_right_holds(self):
		self._say(self.ticket_p, INSTRUCTOR, "Duyệt")
		(labelled,) = authority.label_comments(self.ticket_p, messages.history(self.ticket_p))
		self.assertEqual(labelled["role"], "chỉ thị")

	def test_a_message_without_a_stored_role_is_judged_now(self):
		name = self._say(self.ticket_p, INSTRUCTOR, "cũ")
		frappe.db.set_value(MESSAGE_DOCTYPE, name, "author_role", None, update_modified=False)
		frappe.get_doc("User", INSTRUCTOR).remove_roles(ROLE_INSTRUCTOR)

		(labelled,) = authority.label_comments(self.ticket_p, messages.history(self.ticket_p))

		self.assertEqual(labelled["role"], "dữ liệu")

	def test_an_ai_comment_keeps_the_send_time_data_of_its_copy(self):
		# the copy stored "dữ liệu": the comment stays data when its author gains the right later
		comment = self._comment(self.ticket_p, PLAIN, "2026-11-17 10:00:00")
		self._say(self.ticket_p, PLAIN, "x", source_comment=comment)
		frappe.get_doc("User", PLAIN).add_roles(ROLE_INSTRUCTOR)

		labelled = authority.label_comments(self.ticket_p, authority.fetch_ticket_comments(self.ticket_p))

		self.assertEqual([(c["name"], c["role"]) for c in labelled], [(comment, "dữ liệu")])

	def test_an_ai_comment_of_an_author_who_lost_the_right_is_data(self):
		comment = self._comment(self.ticket_p, INSTRUCTOR, "2026-11-17 10:00:00")
		self._say(self.ticket_p, INSTRUCTOR, "x", source_comment=comment)
		frappe.get_doc("User", INSTRUCTOR).remove_roles(ROLE_INSTRUCTOR)

		labelled = authority.label_comments(self.ticket_p, authority.fetch_ticket_comments(self.ticket_p))

		self.assertEqual([(c["name"], c["role"]) for c in labelled], [(comment, "dữ liệu")])

	# BUG-009 review
	def test_a_merge_copy_lends_no_role_to_the_comment(self):
		# Helpdesk's ticket merge inserts the copy in the merger's session: an instructor's copy of a plain user's
		# comment must not label that comment "chỉ thị"
		comment = self._comment(self.ticket_p, PLAIN, "2026-11-17 10:00:00")
		self._say(self.ticket_p, INSTRUCTOR, "x", source_comment=comment)

		labelled = authority.label_comments(self.ticket_p, authority.fetch_ticket_comments(self.ticket_p))

		self.assertEqual([(c["name"], c["role"]) for c in labelled], [(comment, "dữ liệu")])

	def test_a_role_gained_later_leaves_old_messages_data(self):
		self._say(self.ticket_p, PLAIN, "trước")
		frappe.get_doc("User", PLAIN).add_roles(ROLE_INSTRUCTOR)
		self._say(self.ticket_p, PLAIN, "sau")

		labelled = authority.label_comments(self.ticket_p, messages.history(self.ticket_p)[::-1])

		self.assertEqual(
			[(m["content"], m["role"]) for m in labelled], [("trước", "dữ liệu"), ("sau", "chỉ thị")]
		)

	def test_a_disabled_author_gives_no_order_any_more(self):
		self._say(self.ticket_p, INSTRUCTOR, "Duyệt")
		frappe.db.set_value("User", INSTRUCTOR, "enabled", 0, update_modified=False)

		(labelled,) = authority.label_comments(self.ticket_p, messages.history(self.ticket_p))

		self.assertEqual(labelled["role"], "dữ liệu")

	# a disabled account keeps its Has Role rows: the right ends with the account, on every path that reads it
	def test_a_disabled_account_has_no_right_anywhere(self):
		frappe.db.set_value("User", INSTRUCTOR, "enabled", 0, update_modified=False)
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles(INSTRUCTOR))
		self.assertFalse(authority.is_instruction(INSTRUCTOR, self.ticket_p))
		comments = [{"author": INSTRUCTOR, "content": "đóng phiếu"}]
		self.assertEqual(authority.label_comments(self.ticket_p, comments)[0]["role"], "dữ liệu")
		# a run with no comment trigger falls back to the ticket owner
		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", INSTRUCTOR, update_modified=False)
		self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_TICKET_INSERT))

	def test_a_forged_role_at_insert_is_overwritten(self):
		previous = frappe.session.user
		frappe.set_user(PLAIN)
		try:
			doc = frappe.get_doc(
				{
					"doctype": MESSAGE_DOCTYPE,
					"ticket": self.ticket_p,
					"content": "x",
					"author_role": "chỉ thị",
				}
			).insert(ignore_permissions=True)
		finally:
			frappe.set_user(previous)
		self.assertEqual(self._stored(doc.name), "dữ liệu")

	def test_the_bot_and_administrator_store_data(self):
		for author in (AGENT_USER, "Administrator"):
			with self.subTest(author=author):
				self.assertEqual(self._stored(self._say(self.ticket_p, author, "x")), "dữ liệu")

	def test_an_unknown_stored_value_is_judged_now(self):
		comments = [{"author": PLAIN, "content": "a", "role_at_send": "chỉ thị nhé"}]
		(labelled,) = authority.label_comments(self.ticket_p, comments)
		self.assertEqual(labelled["role"], "dữ liệu")


class TestRunInstructor(AuthorityTestBase):
	"""ADR-030 QĐ 6 / AC-13: the instructor of a run comes only from the event that queued it."""

	def setUp(self):
		keep_agent_settings(self)
		super().setUp()

	def _mention(self, message_name, ticket=None):
		return authority.run_instructor(ticket or self.ticket_p, TRIGGER_COMMENT_MENTION, message_name)

	def _message(self, ticket, author, creation):
		"""A message as `author` (owner is set by the server), then its creation time."""
		previous = frappe.session.user
		frappe.set_user(author)
		try:
			with patch.object(frappe, "enqueue"):
				name = messages.add_message(ticket, "x", trusted=True)
		finally:
			frappe.set_user(previous)
		frappe.db.set_value("ERP AI Message", name, "creation", creation, update_modified=False)
		return name

	def _set_owner(self, owner):
		frappe.db.set_value("HD Ticket", self.ticket_p, "owner", owner, update_modified=False)

	def test_old_instructor_message_does_not_lend_authority(self):
		# The owner is an instructor too: a comment run must not fall back to the owner.
		self._set_owner(INSTRUCTOR)
		self._message(self.ticket_p, INSTRUCTOR, "2024-01-01 10:00:00")
		mention = self._message(self.ticket_p, PLAIN, "2024-01-02 10:00:00")
		self.assertIsNone(self._mention(mention))

	def test_instructor_mention_is_instructor(self):
		self._set_owner(PLAIN)
		mention = self._message(self.ticket_p, INSTRUCTOR, "2024-01-01 10:00:00")
		# A newer comment by a plain agent is not the trigger and changes nothing.
		self._message(self.ticket_p, PLAIN, "2024-01-02 10:00:00")
		self.assertEqual(self._mention(mention), INSTRUCTOR)

	def test_assigned_by_agent_is_not_instruction(self):
		self._assign(self.ticket_p, ASSIGNEE, AGENT_USER)
		# The user is listed in `_assign` with an Open ToDo: only `assigned_by` decides.
		self.assertIn(ASSIGNEE, frappe.parse_json(frappe.db.get_value("HD Ticket", self.ticket_p, "_assign")))
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))
		mention = self._message(self.ticket_p, ASSIGNEE, "2024-01-01 10:00:00")
		self.assertIsNone(self._mention(mention))

		# Assigned by the bot, but holding the role: the role decides, not the assignment.
		self._assign(self.ticket_p, INSTRUCTOR, AGENT_USER)
		mention = self._message(self.ticket_p, INSTRUCTOR, "2024-01-02 10:00:00")
		self.assertEqual(self._mention(mention), INSTRUCTOR)

	def test_assigned_by_another_person_is_instruction(self):
		todo = self._assign(self.ticket_p, ASSIGNEE, ASSIGNER, creation="2024-01-01 10:00:00")
		self.assertTrue(authority.is_instruction(ASSIGNEE, self.ticket_p))
		mention = self._message(self.ticket_p, ASSIGNEE, "2024-01-01 11:00:00")
		self.assertEqual(self._mention(mention), ASSIGNEE)

		# A newer ToDo from the bot replaces the person's assignment.
		self._assign(self.ticket_p, ASSIGNEE, AGENT_USER, creation="2024-01-02 10:00:00")
		self.assertFalse(authority.is_instruction(ASSIGNEE, self.ticket_p))
		self.assertIsNone(self._mention(mention))
		frappe.db.set_value("ToDo", todo, "creation", "2024-01-03 10:00:00", update_modified=False)
		self.assertEqual(self._mention(mention), ASSIGNEE)

	def test_thirty_one_messages_do_not_change_result(self):
		instructor_mention = self._message(self.ticket_p, INSTRUCTOR, "2024-01-01 09:00:00")
		for minute in range(31):
			self._message(self.ticket_p, PLAIN, f"2024-01-02 10:{minute:02d}:00")
		self.assertEqual(self._mention(instructor_mention), INSTRUCTOR)

		plain_mention = self._message(self.ticket_p, PLAIN, "2024-01-03 09:00:00")
		for minute in range(31):
			self._message(self.ticket_p, INSTRUCTOR, f"2024-01-04 10:{minute:02d}:00")
		self.assertIsNone(self._mention(plain_mention))
		self.assertEqual(self._mention(instructor_mention), INSTRUCTOR)

	def test_bad_message_reference_gives_none(self):
		# The owner is an instructor: every bad reference must give None, never fall back to the owner.
		self._set_owner(INSTRUCTOR)
		for missing in (None, "", "no-such-message"):
			self.assertIsNone(self._mention(missing), repr(missing))

		other_ticket = self._message(self.ticket_q, INSTRUCTOR, "2024-01-01 10:00:00")
		self.assertIsNone(self._mention(other_ticket))
		self.assertEqual(self._mention(other_ticket, ticket=self.ticket_q), INSTRUCTOR)

	def _copy(self, ticket, author, comment):
		"""The copy of comment `comment` in the ticket's conversation, made in `author`'s session."""
		previous = frappe.session.user
		frappe.set_user(author)
		try:
			with patch.object(frappe, "enqueue"):
				return messages.add_message(ticket, "x", source_comment=comment, trusted=True)
		finally:
			frappe.set_user(previous)

	def test_copy_of_a_comment_lends_only_the_authority_of_who_wrote_the_comment(self):
		written = self._comment(self.ticket_p, INSTRUCTOR, "2024-01-01 10:00:00")
		self.assertEqual(self._mention(self._copy(self.ticket_p, INSTRUCTOR, written)), INSTRUCTOR)

		# Helpdesk's ticket merge re-inserts old comments in the merger's session and restores their owner
		# afterwards: the copy is then owned by the merger, who did not write the comment
		others = self._comment(self.ticket_p, PLAIN, "2024-01-02 10:00:00")
		self.assertIsNone(self._mention(self._copy(self.ticket_p, INSTRUCTOR, others)))
		self.assertIsNone(self._mention(self._copy(self.ticket_p, INSTRUCTOR, "no-such-comment")))

	def test_other_trigger_uses_valid_owner_only(self):
		plain_message = self._message(self.ticket_p, PLAIN, "2024-01-01 10:00:00")
		instructor_message = self._message(self.ticket_p, INSTRUCTOR, "2024-01-02 10:00:00")

		self._set_owner(INSTRUCTOR)
		for trigger in (TRIGGER_TICKET_INSERT, TRIGGER_CHANGE_ACTION):
			self.assertEqual(authority.run_instructor(self.ticket_p, trigger), INSTRUCTOR, trigger)
			# A comment name is ignored outside the comment trigger.
			self.assertEqual(
				authority.run_instructor(self.ticket_p, trigger, plain_message), INSTRUCTOR, trigger
			)

		for owner in (PLAIN, "Administrator", AGENT_USER):
			self._set_owner(owner)
			self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_TICKET_INSERT), owner)
			self.assertIsNone(
				authority.run_instructor(self.ticket_p, TRIGGER_TICKET_INSERT, instructor_message), owner
			)

		self._set_owner(ASSIGNEE)
		todo = self._assign(self.ticket_p, ASSIGNEE, AGENT_USER)
		self.assertIsNone(authority.run_instructor(self.ticket_p, TRIGGER_TICKET_INSERT))
		frappe.db.set_value("ToDo", todo, "assigned_by", ASSIGNER)
		self.assertEqual(authority.run_instructor(self.ticket_p, TRIGGER_TICKET_INSERT), ASSIGNEE)


class TestEnterAgentSession(FrappeTestCase):
	"""ADR-033 QĐ 1 / U1.md: the one place a job switches its session to the agent account."""

	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user("Administrator")
		frappe.db.set_value("User", AGENT_USER, "enabled", 1)

	def _enter(self):
		with patch.object(frappe, "log_error") as log_error:
			entered = authority.enter_agent_session()
		return entered, log_error

	def test_switches_to_agent(self):
		entered, log_error = self._enter()

		self.assertIs(entered, True)
		self.assertEqual(frappe.session.user, AGENT_USER)
		log_error.assert_not_called()

	def test_disabled_agent_refused_and_logged(self):
		frappe.db.set_value("User", AGENT_USER, "enabled", 0)

		entered, log_error = self._enter()

		self.assertIs(entered, False)
		log_error.assert_called_once_with(authority.TITLE_WRONG_USER, "Không có tài khoản agent")
		self.assertEqual(frappe.session.user, "Administrator")

	def test_missing_agent_refused_and_logged(self):
		with patch.object(authority, "AGENT_USER", "authority.missing.agent@example.com"):
			entered, log_error = self._enter()

		self.assertIs(entered, False)
		log_error.assert_called_once_with(authority.TITLE_WRONG_USER, "Không có tài khoản agent")
		self.assertEqual(frappe.session.user, "Administrator")

	def test_session_not_switched_refused_and_logged(self):
		with patch.object(frappe, "set_user") as set_user:
			entered, log_error = self._enter()

		set_user.assert_called_once_with(AGENT_USER)
		self.assertIs(entered, False)
		log_error.assert_called_once_with(authority.TITLE_WRONG_USER, "Sai tài khoản: Administrator")
		self.assertEqual(frappe.session.user, "Administrator")

	def test_title_is_the_runner_title(self):
		# The title moved here; the old name `runner.TITLE_WRONG_USER` stays the same object (U1.md:264).
		self.assertIs(runner.TITLE_WRONG_USER, authority.TITLE_WRONG_USER)
		self.assertEqual(authority.TITLE_WRONG_USER, "erp_ai: sai tài khoản job")
