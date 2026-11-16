import json
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.desk.form import assign_to
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import due_checks, run_log
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, LOGGER_NAME, SETTING_DOCTYPE
from erp_ai.test_utils import (
	keep_agent_settings,
	make_active_agent,
	make_team,
	pin_agent_roles,
	set_agent_settings,
)

NOW = datetime(2026, 11, 18, 10, 0)
TICKET = "HD Ticket"
TYPE_PREFIX = "ERPAI-TEST due "
CATEGORY_MAPPING = {category: {"ticket_type": f"{TYPE_PREFIX}{category}"} for category in "ABCDEF"}
# A real Datetime Custom Field erp_ai installs on HD Ticket (test_install pins it), as in test_daily_report.
DUE_FIELD = "ai_updated_at"
SUMMARY = "due_checks: due_soon=%d overdue=%d ba_note=%d task=%d errors=%d no_assignee=%d capped=%s"


def _fake_ticket() -> str:
	"""A ticket name no real ticket has: `sent_keys` only matches it against the `ticket` column of ERP AI Log."""
	return f"ERPAI-TEST-due-{frappe.generate_hash(length=10)}"


def _log_row(ticket: str, actions, *, entry_type: str = "bot_action", trigger: str = "scheduled_job") -> None:
	"""An ERP AI Log row inserted straight into the database; `actions` is stored as given (a list as JSON)."""
	frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"run_id": "ERPAI-TEST-due",
			"entry_type": entry_type,
			"trigger": trigger,
			"ticket": ticket,
			"cost_usd": 0,
			"actions": actions if isinstance(actions, str) else json.dumps(actions),
		}
	).db_insert()


def _due_entry(kind: str, deadline: str, ok: bool = True, tool: str = "due_reminder") -> dict:
	return run_log.action_entry(
		tool,
		"Comment",
		"ERPAI-TEST-comment",
		ok,
		reason=None if ok else "lỗi",
		value_after={"kind": kind, "deadline": deadline, "assignees": []},
	)


def _milestone_entry(kind: str, ok: bool = True) -> dict:
	return run_log.action_entry(
		"milestone_reminder",
		"Comment",
		"ERPAI-TEST-comment",
		ok,
		reason=None if ok else "lỗi",
		value_after={"kind": kind, "assignees": []},
	)


def _ticket(category: str | None, creation: datetime, **values) -> str:
	"""An open ticket of `category` created at `creation`, its fields set straight in the database; the side
	records of the insert (comments, assignments, log rows, Tasks, notifications) removed."""
	name = make_ticket(subject="ERPAI-TEST due", description="ERPAI-TEST due").name
	for doctype in ("Comment", "Communication"):
		frappe.db.delete(doctype, {"reference_doctype": TICKET, "reference_name": name})
	frappe.db.delete("ToDo", {"reference_type": TICKET, "reference_name": name})
	frappe.db.delete("Notification Log", {"document_type": TICKET, "document_name": name})
	frappe.db.delete(LOG_DOCTYPE, {"ticket": name})
	frappe.db.delete("Task", {"ai_ticket": name})
	row = {
		"ticket_type": f"{TYPE_PREFIX}{category}" if category else f"{TYPE_PREFIX}unmapped",
		"status": "Open",
		"status_category": "Open",
		"agent_group": None,
		"_assign": None,  # no ToDo left, so no assignee either
		"resolution_by": None,
		DUE_FIELD: None,
		**values,
	}
	row["creation"] = creation
	frappe.db.set_value(TICKET, name, row, update_modified=False)
	return name


def _closed() -> dict:
	return {"status": "Closed", "status_category": "Resolved"}


def _assign(ticket: str, *users: str) -> None:
	"""People in charge, set the way a user does it (the ToDo rows and the ticket's assignee list agree)."""
	for user in users:
		assign_to.add({"assign_to": [user], "doctype": TICKET, "name": ticket})


def _agent_comments(ticket: str) -> list:
	return frappe.get_all(
		"Comment",
		filters={"reference_doctype": TICKET, "reference_name": ticket, "comment_type": "Comment"},
		fields=["name", "owner", "content"],
		order_by="creation asc",
	)


def _bot_rows(ticket: str) -> list:
	return frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket, "entry_type": "bot_action"},
		fields=["name", "trigger", "actions", "cost_usd", "creation"],
		order_by="creation asc",
	)


def _iso(moment: datetime) -> str:
	return f"{moment:%Y-%m-%d %H:%M:%S}"


def _shown(moment: datetime) -> str:
	return f"{moment:%d/%m/%Y %H:%M}"


def _mention(user: str) -> str:
	label = frappe.db.get_value("User", user, "full_name")
	return f'<span class="mention" data-type="mention" data-id="{user}" data-label="{label}">@{label}</span>'


def _notices(ticket: str) -> list:
	"""The Notification Log rows the agent account wrote about `ticket` (an assignment's own notice is not one)."""
	return frappe.get_all(
		"Notification Log",
		filters={"document_type": TICKET, "document_name": ticket, "from_user": AGENT_USER},
		fields=["name", "for_user", "subject", "type"],
		order_by="creation asc",
	)


SEED_DOCTYPES = ("Notification Log", LOG_DOCTYPE, "Error Log", "Email Queue")
TEXT_FIELD_TYPES = ("Data", "Small Text", "Text", "Long Text", "Text Editor", "Code", "JSON", "HTML Editor")


def _seed_rows(seed: str) -> dict[str, int]:
	"""How many rows of each of SEED_DOCTYPES hold `seed` in a text column."""
	counts = {}
	for doctype in SEED_DOCTYPES:
		fields = [
			field.fieldname
			for field in frappe.get_meta(doctype).fields
			if field.fieldtype in TEXT_FIELD_TYPES
		]
		or_filters = [[field, "like", f"%{seed}%"] for field in fields]
		counts[doctype] = len(frappe.get_all(doctype, or_filters=or_filters, pluck="name"))
	return counts


class DueChecksTestCase(FrappeTestCase):
	"""Own tickets and settings, rolled back after each test; the agent account pinned to its production roles;
	the job never commits in a test."""

	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		pin_agent_roles(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self._settings(
			enabled=1,
			permission_level="L2",
			category_mapping=json.dumps(CATEGORY_MAPPING),
			field_due_date=DUE_FIELD,
			due_reminder_hours=24,
			ba_note_due_hours=24,
			task_due_days=3,
			excluded_teams="",
			excluded_title_prefixes="",
		)

	def _settings(self, **fields) -> None:
		set_agent_settings(**fields)
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)

	def _excluded_team(self) -> str:
		"""A team listed in excluded_teams: the agent may not take its tickets (ADR-034)."""
		team = make_team(self)
		self._settings(excluded_teams=team)
		return team

	def _run(self, now: datetime) -> None:
		"""One run of the job at `now`; the job leaves the agent session on, the test goes on as Administrator."""
		due_checks.run_due_checks(now)
		frappe.set_user("Administrator")


class TestNames(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_constants_match_design(self):
		# U5b.md:122-137, verbatim
		self.assertEqual(due_checks.DUE_REMINDER_TOOL, "due_reminder")
		self.assertEqual(due_checks.MILESTONE_REMINDER_TOOL, "milestone_reminder")
		self.assertEqual((due_checks.KIND_DUE_SOON, due_checks.KIND_OVERDUE), ("due_soon", "overdue"))
		self.assertEqual(
			(due_checks.KIND_BA_NOTE_MISSING, due_checks.KIND_TASK_MISSING),
			("ba_note_missing", "task_missing"),
		)
		self.assertEqual(due_checks.CANDIDATE_LIMIT, 200)
		self.assertEqual(due_checks.LOCK_NAME, "erp_ai_due_checks")
		self.assertEqual(
			due_checks.DUE_SOON_TEXT,
			"Nhắc hạn: phiếu còn dưới {hours} giờ tới hạn {deadline}. Người phụ trách: {people}.",
		)
		self.assertEqual(
			due_checks.OVERDUE_TEXT, "Nhắc hạn: phiếu đã quá hạn {deadline}. Người phụ trách: {people}."
		)
		self.assertEqual(
			due_checks.BA_NOTE_TEXT,
			"Nhắc mốc: phiếu đầu mục C đã quá {hours} giờ mà chưa có BA note. Người phụ trách: {people}.",
		)
		self.assertEqual(
			due_checks.TASK_TEXT,
			"Nhắc mốc: phiếu đã quá {days} ngày mà chưa có Task liên kết. Người phụ trách: {people}.",
		)
		self.assertEqual(due_checks.NO_ASSIGNEE_TEXT, "chưa có người phụ trách")
		self.assertEqual(
			due_checks.CODE_SUBJECT,
			{
				"due_soon": "Phiếu #{name}: còn dưới {hours} giờ tới hạn {deadline}",
				"overdue": "Phiếu #{name}: đã quá hạn {deadline}",
				"task_missing": "Phiếu #{name}: quá {days} ngày chưa có Task liên kết",
			},
		)


class TestDueReminder(DueChecksTestCase):
	def test_three_kinds_by_due_overdue_closed(self):
		# D takes its deadline from the due field, E from resolution_by (no due value): both are D-18 deadlines
		soon, past = NOW + timedelta(hours=24), NOW - timedelta(hours=1)
		cases = {
			("D", "due_soon"): ({DUE_FIELD: soon}, soon, "due_soon"),
			("D", "overdue"): ({DUE_FIELD: past}, past, "overdue"),
			("D", "closed"): ({DUE_FIELD: past, **_closed()}, past, None),
			("E", "due_soon"): ({"resolution_by": soon}, soon, "due_soon"),
			("E", "overdue"): ({"resolution_by": past}, past, "overdue"),
			("E", "closed"): ({"resolution_by": soon, **_closed()}, soon, None),
		}
		# D of an excluded team, two people in charge: a coded notice to each of them, never a comment (A-12)
		team = self._excluded_team()
		people = [make_active_agent(self), make_active_agent(self)]
		cases.update(
			{
				("D excluded", "due_soon"): ({DUE_FIELD: soon, "agent_group": team}, soon, "due_soon"),
				("D excluded", "overdue"): ({DUE_FIELD: past, "agent_group": team}, past, "overdue"),
				("D excluded", "closed"): ({DUE_FIELD: past, "agent_group": team, **_closed()}, past, None),
			}
		)
		tickets = {
			case: _ticket(case[0][0], NOW - timedelta(hours=1), **values)
			for case, (values, _, _) in cases.items()
		}
		for case, ticket in tickets.items():
			if case[0] == "D excluded":
				_assign(ticket, *people)

		self._run(NOW)

		for case, (_, deadline, kind) in cases.items():
			ticket = tickets[case]
			with self.subTest(case=case):
				comments = _agent_comments(ticket)
				if kind is None:
					self.assertEqual(comments, [])
					self.assertEqual(_notices(ticket), [])
					self.assertEqual(due_checks.sent_keys([ticket]), set())
					continue
				self.assertEqual(due_checks.sent_keys([ticket]), {(ticket, kind, _iso(deadline))})
				if case[0] == "D excluded":
					self.assertEqual(comments, [])
					subject = due_checks.CODE_SUBJECT[kind].format(
						name=ticket, hours=24, deadline=_shown(deadline)
					)
					self.assertEqual(
						[(row.for_user, row.type, row.subject) for row in _notices(ticket)],
						[(person, "Alert", subject) for person in people],
					)
					continue
				text = due_checks.DUE_SOON_TEXT if kind == "due_soon" else due_checks.OVERDUE_TEXT
				expected = text.format(
					hours=24, deadline=_shown(deadline), people=due_checks.NO_ASSIGNEE_TEXT
				)
				self.assertEqual([row.content for row in comments], [expected])
				self.assertEqual(_notices(ticket), [])

	def test_first_seen_overdue_only_overdue(self):
		deadline = NOW - timedelta(hours=3)
		ticket = _ticket("D", NOW - timedelta(hours=10), **{DUE_FIELD: deadline})

		self._run(NOW)

		self.assertEqual(due_checks.sent_keys([ticket]), {(ticket, "overdue", _iso(deadline))})
		self.assertEqual(len(_agent_comments(ticket)), 1)
		self.assertTrue(_agent_comments(ticket)[0].content.startswith("Nhắc hạn: phiếu đã quá hạn"))

	def test_due_soon_then_overdue_two_total(self):
		deadline = NOW + timedelta(hours=20)
		ticket = _ticket("D", NOW - timedelta(hours=1), **{DUE_FIELD: deadline})

		with patch("frappe.logger") as get_logger:
			self._run(NOW)
			self._run(deadline + timedelta(hours=1))

		self.assertEqual(
			due_checks.sent_keys([ticket]),
			{(ticket, "due_soon", _iso(deadline)), (ticket, "overdue", _iso(deadline))},
		)
		self.assertEqual(len(_agent_comments(ticket)), 2)
		summaries = [args for args in get_logger.return_value.info.call_args_list if args[0][0] == SUMMARY]
		self.assertEqual(
			[args[0][1:] for args in summaries], [(1, 0, 0, 0, 0, 0, False), (0, 1, 0, 0, 0, 0, False)]
		)

	def test_deadline_moved_is_new_cycle(self):
		first = NOW + timedelta(hours=20)
		moved = first + timedelta(days=3)
		ticket = _ticket("E", NOW - timedelta(hours=1), resolution_by=first)

		self._run(NOW)
		frappe.db.set_value(TICKET, ticket, "resolution_by", moved, update_modified=False)
		self._run(NOW + timedelta(hours=1))  # the moved deadline is not near yet
		self._run(moved - timedelta(hours=20))

		self.assertEqual(
			due_checks.sent_keys([ticket]),
			{(ticket, "due_soon", _iso(first)), (ticket, "due_soon", _iso(moved))},
		)
		self.assertEqual(len(_agent_comments(ticket)), 2)

	def test_not_d_or_e_not_reminded(self):
		soon = NOW + timedelta(hours=2)
		tickets = [
			_ticket(category, NOW - timedelta(hours=1), resolution_by=soon, **{DUE_FIELD: soon})
			for category in ("A", "B", "C", "F", None)
		]

		self._run(NOW)

		for ticket in tickets:
			with self.subTest(ticket=ticket):
				self.assertEqual(_agent_comments(ticket), [])
				self.assertEqual(_bot_rows(ticket), [])

	def test_due_field_not_configured_uses_resolution_by(self):
		self._settings(field_due_date="")
		near, far = NOW + timedelta(hours=2), NOW + timedelta(hours=30)
		by_resolution = _ticket("D", NOW - timedelta(hours=1), resolution_by=near, **{DUE_FIELD: far})
		by_due_value = _ticket("D", NOW - timedelta(hours=1), resolution_by=far, **{DUE_FIELD: near})

		with patch("frappe.logger") as get_logger:
			self._run(NOW)

		self.assertEqual(due_checks.sent_keys([by_resolution]), {(by_resolution, "due_soon", _iso(near))})
		self.assertEqual(due_checks.sent_keys([by_due_value]), set())
		lines = [
			args
			for method in ("info", "warning", "error")
			for args in getattr(get_logger.return_value, method).call_args_list
			if "resolution_by" in str(args)
		]
		self.assertEqual(len(lines), 1)

	def test_comment_mentions_assignees_owner_is_agent(self):
		first, second, removed = (make_active_agent(self) for _ in range(3))
		deadline = NOW + timedelta(hours=5)
		assigned = _ticket("E", NOW - timedelta(hours=2), resolution_by=deadline)
		_assign(assigned, first, removed, second)
		assign_to.remove(TICKET, assigned, removed)  # a closed assignment is nobody in charge
		nobody = _ticket("E", NOW - timedelta(hours=1), resolution_by=deadline)

		self._run(NOW)

		people = f"{_mention(first)}, {_mention(second)}"
		for ticket, text, assignees in (
			(assigned, people, [first, second]),
			(nobody, due_checks.NO_ASSIGNEE_TEXT, []),
		):
			with self.subTest(ticket=ticket):
				comments = _agent_comments(ticket)
				self.assertEqual(len(comments), 1)
				self.assertEqual(comments[0].owner, AGENT_USER)
				self.assertEqual(
					comments[0].content,
					due_checks.DUE_SOON_TEXT.format(hours=24, deadline=_shown(deadline), people=text),
				)
				rows = _bot_rows(ticket)
				self.assertEqual(len(rows), 1)
				self.assertEqual(rows[0].trigger, "scheduled_job")
				# U5b.md:356: the record HD Ticket.new_comment makes is a core Comment
				self.assertEqual(
					json.loads(rows[0].actions),
					[
						run_log.action_entry(
							"due_reminder",
							"Comment",
							comments[0].name,
							True,
							value_after={
								"kind": "due_soon",
								"deadline": _iso(deadline),
								"assignees": assignees,
							},
						)
					],
				)
		for user in (first, second):
			self.assertIn(f'data-id="{user}"', _agent_comments(assigned)[0].content)
		self.assertNotIn(removed, _agent_comments(assigned)[0].content)

	def test_boundary_exactly_24h(self):
		cases = (
			# deadline - now = 24:00 counts as due soon; 24:01 is not yet
			(NOW + timedelta(hours=24), 24, "due_soon"),
			(NOW + timedelta(hours=24, minutes=1), 24, None),
			(NOW + timedelta(seconds=1), 24, "due_soon"),
			# deadline - now = 0 is overdue, and so is any deadline before now
			(NOW, 24, "overdue"),
			(NOW - timedelta(days=3), 24, "overdue"),
			# the window is the hours given
			(NOW + timedelta(hours=2), 2, "due_soon"),
			(NOW + timedelta(hours=2, seconds=1), 2, None),
			# no deadline
			(None, 24, None),
		)
		for deadline, hours, expected in cases:
			with self.subTest(deadline=deadline, hours=hours):
				self.assertEqual(due_checks.due_kind(deadline, NOW, hours), expected)


class TestExcluded(DueChecksTestCase):
	def test_seeded_string_never_leaves_ticket(self):
		seed = f"ERPAI-SEED-{frappe.generate_hash(length=10)}"
		deadline = NOW + timedelta(hours=3)
		team = self._excluded_team()
		ticket = _ticket("D", NOW - timedelta(hours=1), agent_group=team, **{DUE_FIELD: deadline})
		frappe.db.set_value(
			TICKET,
			ticket,
			{"subject": f"{seed} tiêu đề", "description": f"<p>{seed} mô tả</p>"},
			update_modified=False,
		)
		person = make_active_agent(self)
		_assign(ticket, person)
		before = _seed_rows(seed)

		with (
			patch("erp_ai.gateway.call_model", side_effect=AssertionError("the model gateway was called")),
			patch("erp_ai.gateway.client.send", side_effect=AssertionError("the model client was called")),
		):
			self._run(NOW)

		self.assertEqual(_agent_comments(ticket), [])
		notices = _notices(ticket)
		self.assertEqual(
			[(row.for_user, row.type, row.subject) for row in notices],
			[(person, "Alert", f"Phiếu #{ticket}: còn dưới 24 giờ tới hạn {_shown(deadline)}")],
		)
		self.assertEqual(_seed_rows(seed), before)
		after = {"kind": "due_soon", "deadline": _iso(deadline), "assignees": [person], "by_code": True}
		self.assertEqual(
			[json.loads(row.actions) for row in _bot_rows(ticket)],
			[
				[
					run_log.action_entry(
						"due_reminder", "Notification Log", notices[0].name, True, value_after=after
					)
				]
			],
		)

	def test_no_assignee_no_key_then_reminded_after_assign(self):
		deadline = NOW - timedelta(hours=2)
		team = self._excluded_team()
		ticket = _ticket("E", NOW - timedelta(hours=5), agent_group=team, resolution_by=deadline)

		with patch("frappe.logger") as get_logger:
			self._run(NOW)

		self.assertEqual((_notices(ticket), _agent_comments(ticket), _bot_rows(ticket)), ([], [], []))
		summaries = [
			args[0][1:] for args in get_logger.return_value.info.call_args_list if args[0][0] == SUMMARY
		]
		self.assertEqual(summaries, [(0, 0, 0, 0, 0, 1, False)])

		person = make_active_agent(self)
		_assign(ticket, person)
		self._run(NOW + timedelta(minutes=15))

		self.assertEqual([row.for_user for row in _notices(ticket)], [person])
		self.assertEqual(_agent_comments(ticket), [])
		self.assertEqual(due_checks.sent_keys([ticket]), {(ticket, "overdue", _iso(deadline))})


class TestGates(DueChecksTestCase):
	def test_agent_off_or_l0_no_reminder(self):
		ticket = _ticket("D", NOW - timedelta(hours=1), **{DUE_FIELD: NOW + timedelta(hours=2)})
		for case, fields in (("agent off", {"enabled": 0}), ("level L0", {"permission_level": "L0"})):
			with self.subTest(case=case):
				self._settings(**{"enabled": 1, "permission_level": "L2", **fields})

				with patch("frappe.logger") as get_logger:
					due_checks.run_due_checks(NOW)

				self.assertEqual(frappe.session.user, "Administrator")
				self.assertEqual(_agent_comments(ticket), [])
				self.assertEqual(_bot_rows(ticket), [])
				self.assertEqual(len(get_logger.return_value.method_calls), 1)
				self.assertEqual(get_logger.return_value.method_calls[0][0], "info")


class TestMilestones(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_milestone_due_boundary(self):
		cases = (
			(NOW - timedelta(hours=23, minutes=59), 24, False),
			(NOW - timedelta(hours=24), 24, True),
			(NOW - timedelta(days=5), 24, True),
			(NOW - timedelta(hours=71, minutes=59, seconds=59), 72, False),
			(NOW - timedelta(hours=72), 72.0, True),
			(NOW - timedelta(minutes=30), 0.5, True),
			(NOW, 24, False),
		)
		for created, hours, expected in cases:
			with self.subTest(created=created, hours=hours):
				self.assertIs(due_checks.milestone_due(created, NOW, hours), expected)


class TestSentKeys(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)

	def test_reads_ok_entries_and_skips_bad_json(self):
		first, second, third, outside = (_fake_ticket() for _ in range(4))
		_log_row(
			first,
			[
				_due_entry("due_soon", "2026-11-20 23:59:59"),
				_milestone_entry("ba_note_missing"),
				# a failed entry is no key; another tool is no key
				_due_entry("overdue", "2026-11-20 23:59:59", ok=False),
				_milestone_entry("task_missing", ok=False),
				_due_entry("due_soon", "2026-11-25 08:00:00", tool="lifecycle_comment"),
			],
		)
		# unreadable actions: that row is skipped with one warning, the ticket's other rows still count
		_log_row(second, "not json")
		_log_row(second, [_due_entry("overdue", "2026-11-19 08:00:00")])
		# a row of another trigger or entry type is no key
		_log_row(third, [_milestone_entry("task_missing")], trigger="setting_save")
		_log_row(
			third,
			[_due_entry("due_soon", "2026-11-21 09:00:00")],
			entry_type="reason",
			trigger="ticket_insert",
		)
		# a ticket outside the asked names is never read
		_log_row(outside, [_due_entry("due_soon", "2026-11-21 09:00:00")])

		with patch("frappe.logger") as get_logger:
			keys = due_checks.sent_keys([first, second, third])

		self.assertEqual(
			keys,
			{
				(first, "due_soon", "2026-11-20 23:59:59"),
				(first, "ba_note_missing", ""),
				(second, "overdue", "2026-11-19 08:00:00"),
			},
		)
		get_logger.assert_called_with(LOGGER_NAME)
		self.assertEqual(len(get_logger.return_value.warning.call_args_list), 1)
		self.assertEqual(due_checks.sent_keys([]), set())
