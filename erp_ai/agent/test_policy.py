import dataclasses
import os
import shutil
import tempfile
import unicodedata
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.model.meta import load_meta
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from helpdesk.test_utils import make_ticket

from erp_ai.agent import policy
from erp_ai.agent.policy import LessonSettings
from erp_ai.constants import (
	AGENT_USER,
	CORE_APPS,
	LOG_DOCTYPE,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
	TRIGGER_CHANGE_ACTION,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_KB_DRAFT,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import TempAppsRoot, keep_agent_settings, make_log_entry, set_agent_settings

TEAM = "Nhân sự & Hành chính"


def _ensure_team(name):
	"""Create the HD Team inside the current transaction if missing."""
	if frappe.db.exists("HD Team", name):
		return
	frappe.get_doc({"doctype": "HD Team", "team_name": name, "users": [{"user": "Administrator"}]}).insert(
		ignore_permissions=True
	)


TEAMS = (TEAM, "IT")


class TestPolicy(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert makes an Assignment Rule that Frappe caches in Redis; the DB
		# rollback leaves that entry stale. Registered first so it runs AFTER the rollback.
		# (Never delete_doc HD Team: HDTeam.on_trash commits the transaction.)
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		# Teams are created inside each test transaction and rolled back; any commit during a
		# test would leak them (FrappeTestCase's own class-level commits happen outside setUp).
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(
			enabled=0,
			trigger_keyword="@ai",
			excluded_teams=f"{TEAM}\nTài chính Kế toán",
			permission_level="L2",
			monthly_budget_usd=10,
			spent_this_month_usd=0,
		)
		for name in TEAMS:
			_ensure_team(name)

	def _ticket(self, **values):
		ticket = make_ticket(subject="T20 policy ticket")
		for key, value in values.items():
			frappe.db.set_value("HD Ticket", ticket.name, key, value)
		return ticket.name

	def test_is_enabled_follows_setting(self):
		self.assertFalse(policy.is_enabled())
		set_agent_settings(enabled=1)
		self.assertTrue(policy.is_enabled())

	def test_field_names_are_exported(self):
		self.assertEqual(policy.OPT_OUT_FIELD, "ai_opt_out")
		self.assertEqual(policy.EXCLUDED_TEAMS_FIELD, "excluded_teams")
		self.assertIn(policy.OPT_OUT_FIELD, policy.SEND_POLICY_FIELDS)
		self.assertIn("agent_group", policy.SEND_POLICY_FIELDS)

	def test_ticket_without_team_can_send(self):
		self.assertTrue(policy.can_send_ticket(self._ticket()))

	def test_opt_out_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(self._ticket(**{policy.OPT_OUT_FIELD: 1})))

	def test_excluded_team_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_other_team_can_send(self):
		self.assertTrue(policy.can_send_ticket(self._ticket(agent_group="IT")))

	def test_excluded_team_matches_ignoring_case_and_spaces(self):
		set_agent_settings(excluded_teams="  nhân  sự &   HÀNH chính \n")
		self.assertFalse(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_blank_excluded_teams_excludes_nobody(self):
		set_agent_settings(excluded_teams="\n  \n")
		self.assertTrue(policy.can_send_ticket(self._ticket(agent_group=TEAM)))

	def test_is_excluded_team_same_normalization(self):
		set_agent_settings(excluded_teams="  nhân  sự &   HÀNH chính \n\nIT  Support")
		self.assertTrue(policy.is_excluded_team(TEAM))
		self.assertTrue(policy.is_excluded_team("  NHÂN sự & hành   CHÍNH "))
		self.assertTrue(policy.is_excluded_team("it support"))
		self.assertFalse(policy.is_excluded_team("IT"))
		self.assertFalse(policy.is_excluded_team(""))
		self.assertFalse(policy.is_excluded_team(None))
		set_agent_settings(excluded_teams="\n  \n")
		self.assertFalse(policy.is_excluded_team(TEAM))

	def test_unrestricted_enabled_reads_switch(self):
		self.assertTrue(policy.unrestricted_enabled(frappe._dict(unrestricted_enabled=1)))
		self.assertFalse(policy.unrestricted_enabled(frappe._dict(unrestricted_enabled=0)))
		self.assertFalse(policy.unrestricted_enabled(frappe._dict(unrestricted_enabled=None)))
		self.assertFalse(policy.unrestricted_enabled(frappe._dict()))

	def test_auto_assign_enabled_reads_switch(self):
		self.assertTrue(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=1)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=0)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict(auto_assign_enabled=None)))
		self.assertFalse(policy.auto_assign_enabled(frappe._dict()))
		self.assertFalse(policy.auto_assign_enabled(object()))

	def test_missing_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket("T20-NOT-A-TICKET"))

	def test_empty_ticket_cannot_send(self):
		self.assertFalse(policy.can_send_ticket(None))

	def test_accepts_dict_and_document(self):
		name = self._ticket(agent_group=TEAM)
		self.assertFalse(policy.can_send_ticket({"agent_group": TEAM}))
		self.assertFalse(policy.can_send_ticket(frappe.get_doc("HD Ticket", name)))
		self.assertTrue(policy.can_send_ticket({"agent_group": "IT", policy.OPT_OUT_FIELD: 0}))
		self.assertFalse(policy.can_send_ticket({"agent_group": "IT", policy.OPT_OUT_FIELD: 1}))

	def test_contains_keyword_ignores_case(self):
		self.assertTrue(policy.contains_keyword("xin chào @AI giúp tôi"))
		self.assertFalse(policy.contains_keyword("không nhắc ai"))
		self.assertFalse(policy.contains_keyword(None))

	def test_contains_keyword_ignores_case_of_configured_keyword(self):
		set_agent_settings(trigger_keyword="@AI")
		self.assertTrue(policy.contains_keyword("xin chào @ai giúp tôi"))

	def test_empty_keyword_never_matches(self):
		set_agent_settings(trigger_keyword="")
		self.assertFalse(policy.contains_keyword("anything @ai"))

	def test_get_trigger_keyword_matches_contains_keyword(self):
		for configured in ("@AI", " @ai ", "", None):
			with self.subTest(configured=configured):
				set_agent_settings(trigger_keyword=configured)
				keyword = policy.get_trigger_keyword()
				self.assertEqual(keyword, configured or "")
				if keyword:
					self.assertTrue(policy.contains_keyword(f"hi {keyword.upper()} there"))
				else:
					self.assertFalse(policy.contains_keyword("anything @ai"))

	def test_effective_level_over_budget_never_raises(self):
		cases = [("L3", "L1"), ("L2", "L1"), ("L1", "L1"), ("L0", "L0")]
		for level, expected in cases:
			with self.subTest(level=level):
				settings = frappe._dict(permission_level=level)
				self.assertEqual(policy.effective_level(settings, over_budget=True), expected)

	def test_effective_level_at_budget_does_not_lower(self):
		settings = frappe._dict(permission_level="L3", monthly_budget_usd=10)
		with patch.object(policy, "month_spend_usd", return_value=10.0):
			over_budget = policy.is_over_budget(settings, now=datetime(2001, 2, 15, 12, 0))
		self.assertEqual(policy.effective_level(settings, over_budget=over_budget), "L3")

	def test_effective_level_under_budget_unchanged(self):
		settings = frappe._dict(permission_level="L2")
		self.assertEqual(policy.effective_level(settings, over_budget=False), "L2")

	def _log(self, ticket, run_id, entry_type="classify", created=None):
		log = frappe.get_doc(
			{
				"doctype": LOG_DOCTYPE,
				"ticket": ticket,
				"run_id": run_id,
				"entry_type": entry_type,
				"trigger": TRIGGER_TICKET_INSERT,
				"turn": 0,
			}
		).insert(ignore_permissions=True)
		if created:
			frappe.db.set_value(LOG_DOCTYPE, log.name, "creation", created, update_modified=False)

	def test_runs_today_counts_distinct_runs_of_classify_and_reason(self):
		ticket = self._ticket()
		self._log(ticket, "r1", "classify")
		self._log(ticket, "r1", "reason")
		self._log(ticket, "r2", "reason")
		self._log(ticket, "r3", "skip")
		self._log(self._ticket(), "other", "classify")
		self.assertEqual(policy.runs_today(ticket), 2)

	def test_runs_today_ignores_yesterday(self):
		ticket = self._ticket()
		self._log(ticket, "old", "classify", created=now_datetime() - timedelta(days=1, minutes=1))
		self._log(ticket, "new", "classify")
		self.assertEqual(policy.runs_today(ticket), 1)

	def test_runs_today_uses_given_now(self):
		ticket = self._ticket()
		self._log(ticket, "r1", "classify")
		tomorrow = datetime.combine(now_datetime().date() + timedelta(days=1), datetime.min.time())
		self.assertEqual(policy.runs_today(ticket, now=tomorrow + timedelta(hours=1)), 0)
		self.assertEqual(policy.runs_today(ticket, now=now_datetime()), 1)

	def test_runs_today_counts_creation_exactly_at_midnight(self):
		ticket = self._ticket()
		midnight = datetime.combine(now_datetime().date(), datetime.min.time())
		self._log(ticket, "edge", "classify", created=midnight)
		self._log(ticket, "before", "classify", created=midnight - timedelta(seconds=1))
		self.assertEqual(policy.runs_today(ticket, now=midnight + timedelta(hours=12)), 1)

	def test_runs_today_ignores_change_rows(self):
		ticket = self._ticket()
		self._log(ticket, "r1", "reason")
		self._log(ticket, "c1", "change")
		self._log(ticket, "c2", "change")
		self.assertEqual(policy.runs_today(ticket), 1)
		only_change = self._ticket()
		self._log(only_change, "c3", "change")
		self.assertEqual(policy.runs_today(only_change), 0)

	# code change settings (FEAT-004) -----------------------------------------------------------

	def test_change_settings_defaults_off_and_empty(self):
		off = policy.ChangeSettings(enabled=False, allowed_apps=())
		self.assertEqual(policy.change_settings(frappe._dict()), off)
		self.assertEqual(policy.change_settings(object()), off)
		for enabled, apps in ((0, None), (None, ""), (0, "\n  \n\t\n")):
			with self.subTest(enabled=enabled, apps=apps):
				settings = frappe._dict(code_change_enabled=enabled, code_change_apps=apps)
				self.assertEqual(policy.change_settings(settings), off)
		self.assertEqual(
			policy.change_settings(frappe._dict(code_change_enabled=1, code_change_apps=None)),
			policy.ChangeSettings(enabled=True, allowed_apps=()),
		)
		set_agent_settings(code_change_enabled=0, code_change_apps="")
		self.assertEqual(policy.current_change_settings(), off)
		self.assertEqual(policy.change_settings(frappe.get_doc(SETTING_DOCTYPE)), off)

	def test_current_change_settings_reads_db_every_call(self):
		set_agent_settings(code_change_enabled=0, code_change_apps="")
		self.assertEqual(
			policy.current_change_settings(), policy.ChangeSettings(enabled=False, allowed_apps=())
		)
		with patch.object(frappe.db, "get_single_value", wraps=frappe.db.get_single_value) as reads:
			set_agent_settings(code_change_enabled=1, code_change_apps="myapp\nhrms")
			self.assertEqual(
				policy.current_change_settings(),
				policy.ChangeSettings(enabled=True, allowed_apps=("myapp", "hrms")),
			)
		self.assertTrue(reads.call_args_list)
		self.assertTrue(all(call.kwargs.get("cache") is False for call in reads.call_args_list))

	def test_change_apps_parsing_and_dedup(self):
		settings = frappe._dict(
			code_change_enabled=1, code_change_apps="  myapp \n\nfrappe\r\nmyapp\n  \n\thrms\t\nfrappe"
		)
		self.assertEqual(
			policy.change_settings(settings),
			policy.ChangeSettings(enabled=True, allowed_apps=("myapp", "frappe", "hrms")),
		)

	def test_change_settings_keeps_names_validate_would_refuse(self):
		# Refusing erp_ai or a bad name is the tools' guard (APP_FORBIDDEN), not this reader's job.
		settings = frappe._dict(code_change_enabled=1, code_change_apps="erp_ai\n../x\n\nmyapp\nerp_ai\n../x")
		self.assertEqual(policy.change_settings(settings).allowed_apps, ("erp_ai", "../x", "myapp"))

	def _assert_refused(self, apps, message, root):
		with self.assertRaises(frappe.ValidationError) as caught:
			policy.validate_change_apps(frappe._dict(code_change_apps=apps), root)
		self.assertEqual(str(caught.exception), message)

	def test_validate_change_apps_rejects_erp_ai_dotdot_missing_dir(self):
		apps_root = TempAppsRoot(self, apps=("myapp", "erp_ai"))
		apps_root.write("afile", "x = 1\n")
		cases = (
			("../x", "Tên app '../x' không hợp lệ"),
			("a/b", "Tên app 'a/b' không hợp lệ"),
			("x.y", "Tên app 'x.y' không hợp lệ"),
			("my app", "Tên app 'my app' không hợp lệ"),
			("..", "Tên app '..' không hợp lệ"),
			("erp_ai", "Không được thêm erp_ai vào danh sách app được sửa"),
			("  erp_ai  ", "Không được thêm erp_ai vào danh sách app được sửa"),
			("nope", "Không có thư mục apps/nope"),
			("afile", "Không có thư mục apps/afile"),
			("frappe", "Không có thư mục apps/frappe"),
		)
		for apps, message in cases:
			with self.subTest(apps=apps):
				self._assert_refused(apps, message, apps_root.root)

	def test_validate_change_apps_order_of_reasons(self):
		apps_root = TempAppsRoot(self, apps=("myapp", "erp_ai"))
		cases = (
			# lines are checked in order for the name rules ...
			("erp_ai\n../x", "Không được thêm erp_ai vào danh sách app được sửa"),
			("../x\nerp_ai", "Tên app '../x' không hợp lệ"),
			# ... and every name is checked before any directory is looked up
			("nope\n../x", "Tên app '../x' không hợp lệ"),
			("nope\nerp_ai", "Không được thêm erp_ai vào danh sách app được sửa"),
			("myapp\nnope\nother", "Không có thư mục apps/nope"),
		)
		for apps, message in cases:
			with self.subTest(apps=apps):
				self._assert_refused(apps, message, apps_root.root)

	def test_validate_change_apps_never_looks_up_a_bad_name(self):
		apps_root = TempAppsRoot(self, apps=("myapp",))
		with patch("os.path.isdir", wraps=os.path.isdir) as isdir:
			self._assert_refused("myapp\n../x", "Tên app '../x' không hợp lệ", apps_root.root)
		isdir.assert_not_called()

	def test_validate_change_apps_accepts_blank_and_listed_dirs(self):
		apps_root = TempAppsRoot(self, apps=("myapp",))
		for apps in (None, "", "\n  \n", "myapp", "  myapp \n\nmyapp\n"):
			with self.subTest(apps=apps):
				self.assertIsNone(
					policy.validate_change_apps(frappe._dict(code_change_apps=apps), apps_root.root)
				)
		self.assertIsNone(policy.validate_change_apps(frappe._dict(), apps_root.root))

	def test_validate_change_apps_accepts_core_apps(self):
		self.assertEqual(CORE_APPS, ("frappe", "erpnext", "helpdesk", "hrms"))
		apps_root = TempAppsRoot(self, apps=CORE_APPS)
		settings = frappe._dict(code_change_apps="frappe\nerpnext\nhelpdesk\nhrms\nfrappe")
		self.assertIsNone(policy.validate_change_apps(settings, apps_root.root))
		self.assertEqual(
			policy.change_settings(settings).allowed_apps, ("frappe", "erpnext", "helpdesk", "hrms")
		)

	def test_validate_change_apps_core_app_still_needs_its_dir(self):
		apps_root = TempAppsRoot(self, apps=("frappe", "erpnext", "helpdesk"))
		self._assert_refused("frappe\nhrms", "Không có thư mục apps/hrms", apps_root.root)

	def test_validate_change_apps_uses_given_root(self):
		given = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, given, True)
		other = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, other, True)
		os.makedirs(os.path.join(given, "onlygiven"))
		os.makedirs(os.path.join(other, "onlyother"))
		settings = frappe._dict(code_change_apps="onlygiven")
		self.assertIsNone(policy.validate_change_apps(settings, given))
		self._assert_refused("onlygiven", "Không có thư mục apps/onlygiven", other)
		self._assert_refused("onlyother", "Không có thư mục apps/onlyother", given)
		self.assertIsNone(policy.validate_change_apps(frappe._dict(code_change_apps="onlyother"), other))


class TestTicketContentDoctype(FrappeTestCase):
	# ADR-034 QĐ 1: the four names of TICKET_CONTENT_DOCTYPES (T8 pins the constant itself).
	CONSTANT_NAMES = ("HD Ticket", "Comment", "Communication", "File")

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		for function in ("ticket_link_fieldnames", "is_ticket_content_doctype"):
			self.assertTrue(callable(getattr(policy, function, None)), f"policy has no {function}()")
		# The Custom Field erp_ai installs (test_install pins it); no test creates one (ALTER TABLE commits).
		self.assertTrue(
			frappe.db.exists(
				"Custom Field", {"dt": "Task", "fieldname": "ai_ticket", "options": "HD Ticket"}
			),
			"Custom Field Task.ai_ticket of erp_ai is missing",
		)

	def test_constant_and_ticket_links(self):
		# design-w0-fixes-3.md ruling 2, C-T15-2: the constant by name, any other DocType by its Link fields to
		# HD Ticket (standard or Custom Field), always on the stored DocType name.
		for doctype in (*self.CONSTANT_NAMES, "comment", "HD Ticket Comment", "Task", "task"):
			with self.subTest(doctype=doctype):
				self.assertTrue(policy.is_ticket_content_doctype(doctype))
		for doctype in ("User", "Note", "Không có DocType này"):
			with self.subTest(doctype=doctype):
				self.assertFalse(policy.is_ticket_content_doctype(doctype))
		cases = (
			("HD Ticket Comment", ("reference_ticket",)),
			("Task", ("ai_ticket",)),
			("task", ("ai_ticket",)),
			# HD Ticket links to itself (split from, merged with) but is the ticket, not a linked record.
			("HD Ticket", ()),
			("hd ticket", ()),
			("Comment", ()),
			("User", ()),
			("Không có DocType này", ()),
		)
		for doctype, fieldnames in cases:
			with self.subTest(doctype=doctype):
				self.assertEqual(policy.ticket_link_fieldnames(doctype), fieldnames)


class TestPermissionSwitches(FrappeTestCase):
	# U1 3.1: the permission switches, read in one place, in the order of the settings section.
	# BUG-008: console joins them (sixth in the dataclass, fifth in the section, before one_click_approval).
	FIELD_FLAGS = (
		("unrestricted_enabled", "unrestricted"),
		("record_tools_enabled", "record_tools"),
		("act_now_enabled", "act_now"),
		("code_change_enabled", "code_change"),
		("console_enabled", "console"),
		("one_click_approval_enabled", "one_click_approval"),
	)

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		for name in ("permission_switches", "PermissionSwitches", "PERMISSION_SWITCH_FIELDS"):
			self.assertTrue(hasattr(policy, name), f"policy has no {name}")

	def _flags(self, switches):
		return {flag: getattr(switches, flag) for _field, flag in self.FIELD_FLAGS}

	def test_missing_fields_read_off(self):
		off = {flag: False for _field, flag in self.FIELD_FLAGS}
		self.assertEqual(policy.PermissionSwitches(), policy.PermissionSwitches(**off))
		# A settings object without the fields (before migrate) reads every switch off and never raises.
		for settings in (frappe._dict(), object()):
			with self.subTest(settings=settings):
				self.assertEqual(self._flags(policy.permission_switches(settings)), off)
		for value in (0, None, ""):
			with self.subTest(value=value):
				settings = frappe._dict({field: value for field, _flag in self.FIELD_FLAGS})
				self.assertEqual(self._flags(policy.permission_switches(settings)), off)
		set_agent_settings(**{field: 0 for field, _flag in self.FIELD_FLAGS})
		self.assertEqual(self._flags(policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE))), off)
		with self.assertRaises(AttributeError):
			policy.permission_switches(frappe._dict()).act_now = True

	def test_switch_flags_pair_fields_by_name(self):
		# BUG-008: tasks pairs a field with its flag through this map, never by position.
		self.assertEqual(tuple(policy.SWITCH_FLAGS), policy.PERMISSION_SWITCH_FIELDS)
		own = {f.name for f in dataclasses.fields(policy.PermissionSwitches)}
		self.assertEqual(set(policy.SWITCH_FLAGS.values()), own)
		self.assertEqual(policy.SWITCH_FLAGS[policy.CONSOLE_FIELD], "console")
		self.assertEqual(policy.SWITCH_FLAGS[policy.ONE_CLICK_APPROVAL_FIELD], "one_click_approval")

	def test_each_field_maps_to_its_flag(self):
		self.assertEqual(
			(
				policy.UNRESTRICTED_FIELD,
				policy.RECORD_TOOLS_FIELD,
				policy.ACT_NOW_FIELD,
				policy.ONE_CLICK_APPROVAL_FIELD,
			),
			("unrestricted_enabled", "record_tools_enabled", "act_now_enabled", "one_click_approval_enabled"),
		)
		self.assertEqual(policy.PERMISSION_SWITCH_FIELDS, tuple(field for field, _flag in self.FIELD_FLAGS))
		for field, flag in self.FIELD_FLAGS:
			with self.subTest(field=field):
				switches = policy.permission_switches(frappe._dict({field: 1}))
				self.assertEqual(
					self._flags(switches), {other: other == flag for _f, other in self.FIELD_FLAGS}
				)
		self.assertTrue(
			all(
				self._flags(
					policy.permission_switches(frappe._dict.fromkeys(policy.PERMISSION_SWITCH_FIELDS, 1))
				).values()
			)
		)
		# Read from the stored setting: record_tools and one_click_approval on, the rest off.
		set_agent_settings(
			unrestricted_enabled=0,
			record_tools_enabled=1,
			act_now_enabled=0,
			code_change_enabled=0,
			one_click_approval_enabled=1,
		)
		self.assertEqual(
			policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE)),
			policy.PermissionSwitches(record_tools=True, one_click_approval=True),
		)


class TestConsoleSwitch(FrappeTestCase):
	# CHG-010 Task 1: the console switch, read only by policy. The site meta may not know the field (no migrate),
	# so values are written with set_agent_settings and read from a document, never get_single_value.
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def test_console_field_name(self):
		self.assertEqual(policy.CONSOLE_FIELD, "console_enabled")

	def test_console_switch_off_when_missing(self):
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": policy.CONSOLE_FIELD})
		self.assertIs(policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE)).console, False)
		self.assertIs(policy.permission_switches(frappe._dict()).console, False)
		self.assertIs(policy.console_enabled_now(), False)

	def test_console_switch_on(self):
		set_agent_settings(console_enabled=1)
		self.assertIs(policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE)).console, True)

	def test_console_independent_of_code_change(self):
		set_agent_settings(code_change_enabled=0, console_enabled=1)
		switches = policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE))
		self.assertIs(switches.console, True)
		self.assertIs(switches.code_change, False)
		set_agent_settings(code_change_enabled=1, console_enabled=0)
		switches = policy.permission_switches(frappe.get_doc(SETTING_DOCTYPE))
		self.assertIs(switches.console, False)
		self.assertIs(switches.code_change, True)

	def test_console_is_the_sixth_field(self):
		self.assertEqual(
			policy.PermissionSwitches(True, True, True, True, True, True).console,
			True,
		)
		self.assertIs(policy.PermissionSwitches().console, False)

	def test_console_enabled_now_reads_fresh(self):
		set_agent_settings(console_enabled=0)
		self.assertIs(policy.console_enabled_now(), False)
		set_agent_settings(console_enabled=1)
		self.assertIs(policy.console_enabled_now(), True)
		set_agent_settings(console_enabled=0)
		self.assertIs(policy.console_enabled_now(), False)


class TestBudget(FrappeTestCase):
	# AC-61: the month's spend is summed from live ERP AI Log rows, never from spent_this_month_usd.
	# February 2001 has no real rows on the site; every row here is written inside the test transaction.
	FEB = datetime(2001, 2, 15, 12, 0)

	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def _log(self, created, cost_usd=None, entry_type="classify"):
		values = {"doctype": LOG_DOCTYPE, "run_id": f"budget-{created}", "entry_type": entry_type, "turn": 0}
		if cost_usd is not None:
			values["cost_usd"] = cost_usd
		log = frappe.get_doc(values).insert(ignore_permissions=True)
		frappe.db.set_value(LOG_DOCTYPE, log.name, "creation", created, update_modified=False)

	def _february_rows(self):
		"""February 2001 spends 4.0 + 6.0 = 10.0; the two boundary rows are outside [start, end)."""
		self._log(datetime(2001, 1, 31, 23, 59, 59), 100.0)  # last second of the month before
		self._log(datetime(2001, 2, 1, 0, 0, 0), 4.0)  # first instant of the month counts
		self._log(datetime(2001, 2, 15, 9, 0), None, "skip")  # no cost_usd: adds nothing
		self._log(datetime(2001, 2, 28, 23, 59, 59), 6.0, "reason")
		self._log(datetime(2001, 3, 1, 0, 0, 0), 1000.0)  # first instant of the next month

	def test_month_spend_sums_live_log_rows(self):
		self.assertEqual(policy.month_spend_usd(now=self.FEB), 0.0)  # a month without rows
		self._february_rows()
		spend = policy.month_spend_usd(now=self.FEB)
		self.assertIsInstance(spend, float)
		self.assertEqual(spend, 10.0)

	def test_over_budget_reads_log_not_spent_field(self):
		self._february_rows()
		cases = [
			({"monthly_budget_usd": 9.5, "spent_this_month_usd": 0}, True),
			({"monthly_budget_usd": 10.5, "spent_this_month_usd": 999}, False),
			({"monthly_budget_usd": None, "spent_this_month_usd": 0}, True),
		]
		for fields, expected in cases:
			with self.subTest(**fields):
				self.assertIs(policy.is_over_budget(frappe._dict(fields), now=self.FEB), expected)
		# The spend goes through the module-level seam, called with the given `now`.
		with patch.object(policy, "month_spend_usd", return_value=10.01) as month_spend:
			self.assertIs(policy.is_over_budget(frappe._dict(monthly_budget_usd=10), now=self.FEB), True)
		month_spend.assert_called_once_with(self.FEB)

	def test_over_budget_caps_permission_level_at_l1(self):
		self._february_rows()
		over = {"L3": "L1", "L2": "L1", "L1": "L1", "L0": "L0"}
		for level, expected in over.items():
			with self.subTest(level=level):
				# the spent field says "under" but the log rows (10.0) are over the budget of 9.5
				settings = frappe._dict(
					permission_level=level, monthly_budget_usd=9.5, spent_this_month_usd=0
				)
				over_budget = policy.is_over_budget(settings, now=self.FEB)
				self.assertIs(over_budget, True)
				self.assertEqual(policy.effective_level(settings, over_budget=over_budget), expected)
				self.assertEqual(policy.effective_level(settings, over_budget=False), level)
		with self.assertRaises(TypeError):
			policy.effective_level(frappe._dict(permission_level="L3"), True)

	def test_spend_equal_to_budget_is_not_over(self):
		# No spend and no budget: 0 > 0 is not over.
		self.assertIs(policy.is_over_budget(frappe._dict(monthly_budget_usd=0), now=self.FEB), False)
		self._february_rows()
		settings = frappe._dict(permission_level="L3", monthly_budget_usd=10, spent_this_month_usd=999)
		self.assertIs(policy.is_over_budget(settings, now=self.FEB), False)
		self.assertEqual(policy.effective_level(settings, over_budget=False), "L3")


class TestLevels(FrappeTestCase):
	# AC-31, U1 3.1: the main-path level of a ticket = the smaller of the permission level and the category cap.
	# (category, default cap, expected main-path level for permission_level L0, L1, L2, L3 under budget)
	CATEGORY_ROWS = (
		("A", "L2", ("L0", "L1", "L2", "L2")),
		("B", "L3", ("L0", "L1", "L2", "L3")),
		("C", "L1", ("L0", "L1", "L1", "L1")),
		("D", "L2", ("L0", "L1", "L2", "L2")),
		("E", "L1", ("L0", "L1", "L1", "L1")),
		("F", "L3", ("L0", "L1", "L2", "L3")),
	)
	# Over budget the permission level is already capped at L1 (never raises L0): every category reads <= L1.
	OVER_BUDGET = ("L0", "L1", "L1", "L1")

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		for name in (
			"LEVEL_CAP_FIELD_PREFIX",
			"UNKNOWN_CATEGORY_LEVEL",
			"category_level_cap",
			"main_path_level",
		):
			self.assertTrue(hasattr(policy, name), f"policy has no {name}")

	def _caps(self, cap=None):
		"""level_cap_<x> of every category: the default caps, or `cap` for all."""
		return {
			f"level_cap_{category.lower()}": cap or default for category, default, _ in self.CATEGORY_ROWS
		}

	def test_main_path_level_matrix(self):
		self.assertEqual(policy.LEVEL_CAP_FIELD_PREFIX, "level_cap_")
		meta = frappe.get_meta(SETTING_DOCTYPE)
		for field, level in self._caps().items():
			with self.subTest(default=field):
				self.assertEqual(meta.get_field(field).default, level)
		# Read from the stored setting carrying the default caps (the matrix of AC-31: 6 x 4 x 2 = 48 cases).
		set_agent_settings(monthly_budget_usd=0, **self._caps())
		cases = 0
		for level_index, level in enumerate(("L0", "L1", "L2", "L3")):
			set_agent_settings(permission_level=level)
			settings = frappe.get_doc(SETTING_DOCTYPE)
			for over_budget in (False, True):
				permission_level = policy.effective_level(settings, over_budget=over_budget)
				for category, default_cap, expected_by_level in self.CATEGORY_ROWS:
					expected = (self.OVER_BUDGET if over_budget else expected_by_level)[level_index]
					with self.subTest(category=category, level=level, over_budget=over_budget):
						self.assertEqual(policy.category_level_cap(settings, category), default_cap)
						self.assertEqual(
							policy.main_path_level(settings, permission_level, category), expected
						)
					cases += 1
		self.assertEqual(cases, 48)

	def test_cap_above_or_below_permission_level(self):
		# The cap only lowers: a cap above the permission level keeps the permission level, L0 always wins.
		cases = (
			("L3", "L0", "L0"),
			("L1", "L0", "L0"),
			("L0", "L3", "L0"),
			("L1", "L3", "L1"),
			("L3", "L1", "L1"),
			("L2", "L2", "L2"),
		)
		for permission_level, cap, expected in cases:
			with self.subTest(permission_level=permission_level, cap=cap):
				settings = frappe._dict(level_cap_d=cap)
				self.assertEqual(policy.category_level_cap(settings, "D"), cap)
				self.assertEqual(policy.main_path_level(settings, permission_level, "D"), expected)

	def test_unknown_category_or_bad_cap_reads_l1(self):
		self.assertEqual(policy.UNKNOWN_CATEGORY_LEVEL, "L1")
		all_l3 = frappe._dict(self._caps("L3"))
		# An unknown category (None, empty, lower case, not one of A..F) reads L1 even when every cap is L3.
		for category in (None, "", "a", "G", "AB", " A", "level_cap_a"):
			with self.subTest(category=category):
				self.assertEqual(policy.category_level_cap(all_l3, category), "L1")
				self.assertEqual(policy.main_path_level(all_l3, "L3", category), "L1")
				self.assertEqual(policy.main_path_level(all_l3, "L1", category), "L1")
				self.assertEqual(policy.main_path_level(all_l3, "L0", category), "L0")
		# A missing field (before migrate) or a value outside LEVELS reads L1 (fail-closed, NFR-4).
		for settings in (frappe._dict(), object()):
			with self.subTest(settings=settings):
				self.assertEqual(policy.category_level_cap(settings, "B"), "L1")
				self.assertEqual(policy.main_path_level(settings, "L3", "B"), "L1")
		for value in (None, "", "L4", "l3", "L-1", " L3", 3, "Toàn quyền"):
			with self.subTest(value=value):
				settings = frappe._dict(level_cap_b=value)
				self.assertEqual(policy.category_level_cap(settings, "B"), "L1")
				self.assertEqual(policy.main_path_level(settings, "L3", "B"), "L1")
				self.assertEqual(policy.main_path_level(settings, "L0", "B"), "L0")
		# A bad cap on one category does not leak into another.
		settings = frappe._dict(level_cap_b="L9", level_cap_f="L3")
		self.assertEqual(policy.main_path_level(settings, "L3", "F"), "L3")
		# Read from the stored setting: an empty cap reads L1.
		set_agent_settings(level_cap_a="")
		self.assertEqual(policy.category_level_cap(frappe.get_doc(SETTING_DOCTYPE), "A"), "L1")


class TestConfidence(FrappeTestCase):
	# AC-22, A-U1-1, U1 3.1: the single below-threshold predicate; unknown confidence (None, -1, outside 0..100)
	# is below every threshold unless an instructor gave the order and switch (3) act_now is on.
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def _below(self, pct, threshold, has_instructor=False, act_now=False):
		return policy.is_below_confidence(pct, threshold, has_instructor=has_instructor, act_now=act_now)

	def test_threshold_boundaries(self):
		self.assertEqual(policy.CONFIDENCE_THRESHOLD_FIELD, "confidence_threshold")
		self.assertEqual(policy.DEFAULT_CONFIDENCE_THRESHOLD, 70)
		cases = (
			(69, 70, True),
			(70, 70, False),
			(71, 70, False),
			(0, 70, True),
			(100, 70, False),
			(None, 70, True),
			(-1, 70, True),
			# threshold 0: unknown is still below, a known 0 is not (design-w0-fixes-2.md ruling (1))
			(None, 0, True),
			(-1, 0, True),
			(0, 0, False),
			(99, 100, True),
			(100, 100, False),
			# outside 0..100, a bool or a non-int reads unknown: below even at threshold 0
			(101, 0, True),
			(-5, 0, True),
			(True, 0, True),
			(False, 0, True),
			("80", 70, True),
			(80.0, 70, True),
		)
		for pct, threshold, expected in cases:
			with self.subTest(pct=pct, threshold=threshold):
				self.assertIs(self._below(pct, threshold), expected)
		# The stored default threshold (a fresh install) gives the same 69/70 boundary.
		set_agent_settings(confidence_threshold=70)
		threshold = policy.confidence_threshold(frappe.get_doc(SETTING_DOCTYPE))
		self.assertEqual(threshold, 70)
		self.assertIs(self._below(69, threshold), True)
		self.assertIs(self._below(70, threshold), False)

	def test_threshold_changed_to_80(self):
		set_agent_settings(confidence_threshold=80)
		threshold = policy.confidence_threshold(frappe.get_doc(SETTING_DOCTYPE))
		self.assertIsInstance(threshold, int)
		self.assertEqual(threshold, 80)
		self.assertIs(self._below(70, threshold), True)
		self.assertIs(self._below(79, threshold), True)
		self.assertIs(self._below(80, threshold), False)
		for value in (0, 100):
			with self.subTest(stored=value):
				set_agent_settings(confidence_threshold=value)
				self.assertEqual(policy.confidence_threshold(frappe.get_doc(SETTING_DOCTYPE)), value)

	def test_threshold_missing_or_invalid_reads_default(self):
		# A missing field (before migrate), empty, garbage, a bool or a value outside 0..100 reads the default 70.
		self.assertEqual(policy.confidence_threshold(frappe._dict()), 70)
		self.assertEqual(policy.confidence_threshold(object()), 70)
		for value in (None, "", "abc", "7O", True, False, -1, 101, [80]):
			with self.subTest(value=value):
				self.assertEqual(policy.confidence_threshold(frappe._dict(confidence_threshold=value)), 70)
		for value, expected in ((0, 0), (100, 100), ("80", 80), (85.0, 85)):
			with self.subTest(value=value):
				threshold = policy.confidence_threshold(frappe._dict(confidence_threshold=value))
				self.assertIsInstance(threshold, int)
				self.assertEqual(threshold, expected)

	def test_instructor_with_act_now_is_never_below(self):
		for pct in (None, -1, 0, 1, 69, 70, 100, 101, True, "80"):
			for threshold in (0, 70, 80, 100):
				with self.subTest(pct=pct, threshold=threshold):
					self.assertIs(self._below(pct, threshold, has_instructor=True, act_now=True), False)

	def test_act_now_off_instructor_still_below(self):
		# Only the pair instructor AND act_now lifts the threshold; either one alone does not.
		for has_instructor, act_now in ((True, False), (False, True), (False, False)):
			for pct, expected in ((69, True), (None, True), (-1, True), (70, False)):
				with self.subTest(has_instructor=has_instructor, act_now=act_now, pct=pct):
					self.assertIs(self._below(pct, 70, has_instructor, act_now), expected)
		# The two flags are keyword-only.
		with self.assertRaises(TypeError):
			policy.is_below_confidence(69, 70, True, True)

	def _classify_row(self, ticket, category, pct=None, created=None, entry_type="classify"):
		values = {
			"doctype": LOG_DOCTYPE,
			"ticket": ticket,
			"run_id": f"conf-{frappe.generate_hash(length=8)}",
			"entry_type": entry_type,
			"turn": 0,
			"predicted_category": category,
		}
		log = frappe.get_doc(values).insert(ignore_permissions=True)
		if pct is not None:
			frappe.db.set_value(LOG_DOCTYPE, log.name, "predicted_confidence_pct", pct, update_modified=False)
		if created:
			frappe.db.set_value(LOG_DOCTYPE, log.name, "creation", created, update_modified=False)
		return log.name

	def test_latest_classification_minus_one_reads_none(self):
		for pct, expected in ((-1, None), (0, 0), (70, 70), (100, 100), (101, None), (-7, None)):
			with self.subTest(pct=pct):
				ticket = make_ticket(subject="T69 confidence").name
				self._classify_row(ticket, "C", pct)
				self.assertEqual(policy.latest_classification(ticket), ("C", expected))
		# A row written without the pct takes the column default -1: unknown.
		ticket = make_ticket(subject="T69 confidence").name
		self._classify_row(ticket, "D")
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, {"ticket": ticket}, "predicted_confidence_pct"), -1)
		self.assertEqual(policy.latest_classification(ticket), ("D", None))

	def test_latest_classification_without_row_reads_none(self):
		ticket = make_ticket(subject="T69 confidence").name
		self.assertEqual(policy.latest_classification(ticket), (None, None))
		self.assertEqual(policy.latest_classification("no-such-ticket"), (None, None))
		# Rows that do not count: an empty category, another entry type, another ticket.
		self._classify_row(ticket, "", 90)
		self._classify_row(ticket, None, 90)
		self._classify_row(ticket, "B", 90, entry_type="reason")
		self._classify_row(make_ticket(subject="T69 other").name, "A", 90)
		self.assertEqual(policy.latest_classification(ticket), (None, None))

	def test_latest_classification_newest_row_wins(self):
		ticket = make_ticket(subject="T69 confidence").name
		now = now_datetime()
		self._classify_row(ticket, "B", 95, created=now - timedelta(hours=1))
		self._classify_row(ticket, "A", 40, created=now - timedelta(hours=2))
		self._classify_row(ticket, "E", 80, created=now - timedelta(days=1))
		self.assertEqual(policy.latest_classification(ticket), ("B", 95))
		# A newer row with an empty category, or of another entry type, does not replace the classification.
		self._classify_row(ticket, "", 10, created=now)
		self._classify_row(ticket, "F", 10, created=now, entry_type="reason")
		self.assertEqual(policy.latest_classification(ticket), ("B", 95))
		# A newer classify row with an unknown pct wins and reads None (no fallback to an older number).
		self._classify_row(ticket, "C", -1, created=now + timedelta(minutes=1))
		self.assertEqual(policy.latest_classification(ticket), ("C", None))


class TestRunsToday(FrappeTestCase):
	# arch-review w1a C-3 and ruling (2), ADR-033 QĐ 4: the daily limit counts only the runs started by a
	# trigger of RUN_LIMIT_TRIGGERS; classify/reason rows of any other trigger (or none) are not a run.
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)

	def _log(self, ticket, run_id, entry_type, trigger, turn=0, stop_reason=None):
		frappe.get_doc(
			{
				"doctype": LOG_DOCTYPE,
				"ticket": ticket,
				"run_id": run_id,
				"entry_type": entry_type,
				"trigger": trigger,
				"turn": turn,
				"stop_reason": stop_reason,
			}
		).insert(ignore_permissions=True)

	def test_counts_only_run_limit_triggers(self):
		ticket = make_ticket(subject="T71 runs_today ticket").name
		self._log(ticket, "insert", "classify", TRIGGER_TICKET_INSERT)
		self._log(ticket, "mention", "reason", TRIGGER_COMMENT_MENTION)
		self._log(ticket, "change-reason", "reason", TRIGGER_CHANGE_ACTION)
		self._log(ticket, "change-classify", "classify", TRIGGER_CHANGE_ACTION)
		self.assertEqual(policy.runs_today(ticket), 2)
		# U6b-fixes Sửa 3 (AC-41): the requester-reply run is counted, the KB-draft run never is.
		self.assertEqual(
			policy.RUN_LIMIT_TRIGGERS,
			(TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY),
		)

	def test_kb_draft_reason_row_not_counted(self):
		# U6b-fixes Sửa 3 (X-2): a KB-draft run is not a run of the daily limit.
		ticket = make_ticket(subject="T140 kb_draft runs_today ticket").name
		self._log(ticket, "insert", "classify", TRIGGER_TICKET_INSERT)
		self.assertEqual(policy.runs_today(ticket), 1)
		self._log(ticket, "kb-draft", "reason", TRIGGER_KB_DRAFT)
		self.assertEqual(policy.runs_today(ticket), 1)
		self.assertNotIn(TRIGGER_KB_DRAFT, policy.RUN_LIMIT_TRIGGERS)

	def test_requester_reply_reason_row_counted(self):
		# U6b-fixes Sửa 3 (X-2): a requester-reply run counts once per run_id, its turns and skips add nothing.
		ticket = make_ticket(subject="T140 requester_reply runs_today ticket").name
		self.assertEqual(policy.runs_today(ticket), 0)
		run_id = f"{TRIGGER_REQUESTER_REPLY}:{ticket}:COMM-1"
		self._log(ticket, run_id, "reason", TRIGGER_REQUESTER_REPLY)
		self.assertEqual(policy.runs_today(ticket), 1)
		self._log(ticket, run_id, "reason", TRIGGER_REQUESTER_REPLY, turn=1)
		self.assertEqual(policy.runs_today(ticket), 1)
		self._log(
			ticket,
			f"{TRIGGER_REQUESTER_REPLY}:{ticket}:COMM-2",
			"skip",
			TRIGGER_REQUESTER_REPLY,
			stop_reason="superseded",
		)
		self.assertEqual(policy.runs_today(ticket), 1)


class TestSiteEnvironment(FrappeTestCase):
	# ADR-031 QĐ 7, arch-review w1a C-1: the one reader of the site environment; anything but an exact
	# "production" or "test" (missing field, empty, unknown, other case) fails closed to "production".
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def test_values_and_fail_closed(self):
		self.assertEqual(policy.SITE_ENVIRONMENT_FIELD, "site_environment")
		self.assertEqual(policy.SITE_ENVIRONMENTS, ("production", "test"))
		self.assertEqual(policy.DEFAULT_SITE_ENVIRONMENT, "production")
		for value in ("production", "test"):
			with self.subTest(value=value):
				self.assertEqual(policy.site_environment(frappe._dict(site_environment=value)), value)
		# A settings object without the field (before migrate) reads production and never raises.
		for settings in (frappe._dict(), object()):
			with self.subTest(settings=settings):
				self.assertEqual(policy.site_environment(settings), "production")
		for value in (
			"",
			None,
			"staging",
			"Test",
			"TEST",
			"Production",
			" test",
			"test ",
			0,
			1,
			True,
			["test"],
		):
			with self.subTest(value=value):
				self.assertEqual(policy.site_environment(frappe._dict(site_environment=value)), "production")
		# settings=None reads the stored ERP AI Setting (a value written without validate, as an old row could be).
		for stored, expected in (
			("test", "test"),
			("production", "production"),
			("staging", "production"),
			("", "production"),
		):
			with self.subTest(stored=stored):
				set_agent_settings(site_environment=stored)
				self.assertEqual(policy.site_environment(), expected)
				self.assertEqual(policy.site_environment(None), expected)
		# A given settings object wins over the stored value.
		set_agent_settings(site_environment="production")
		self.assertEqual(policy.site_environment(frappe._dict(site_environment="test")), "test")
		set_agent_settings(site_environment="test")
		self.assertEqual(policy.site_environment(frappe._dict()), "production")
		self.assertEqual(policy.site_environment(frappe.get_doc(SETTING_DOCTYPE)), "test")


class TestTitlePrefix(FrappeTestCase):
	# AC-9 (a), U2.md:93-94, :112-113, :126-128: a title starting with a configured prefix (same NFC + spaces +
	# casefold key on both sides) is excluded; only the start of the title counts.
	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def test_prefix_boundaries(self):
		self.assertEqual(policy.EXCLUDED_TITLE_PREFIXES_FIELD, "excluded_title_prefixes")
		self.assertEqual(policy.SUBJECT_FIELD, "subject")
		ke_toan_nfc = unicodedata.normalize("NFC", "[Kế toán]")
		ke_toan_nfd = unicodedata.normalize("NFD", "[Kế toán]")
		self.assertNotEqual(ke_toan_nfc, ke_toan_nfd)
		# Empty and blank lines are dropped: an empty prefix would exclude every title.
		set_agent_settings(excluded_title_prefixes=f"[HR]\n\n   \n{ke_toan_nfc}\n")
		self.assertEqual(policy.excluded_title_prefixes(), ("[hr]", "[kế toán]"))
		for subject in ("[HR] X", "  [hr]   X", f"{ke_toan_nfc}X", f"{ke_toan_nfd}X"):
			with self.subTest(subject=subject):
				self.assertTrue(policy.has_excluded_title(subject))
		for subject in ("Hỏi về [HR]", "[HRM] X", "", None):
			with self.subTest(subject=subject):
				self.assertFalse(policy.has_excluded_title(subject))
		# Each config line goes through _title_key too: an NFD line with extra spaces gives the NFC key,
		# so an admin typing the prefix in NFD (some IMEs, macOS) still gets the rule.
		set_agent_settings(excluded_title_prefixes="  " + unicodedata.normalize("NFD", "[Kế   toán]") + " ")
		self.assertEqual(policy.excluded_title_prefixes(), ("[kế toán]",))
		self.assertTrue(policy.has_excluded_title(f"{ke_toan_nfc}X"))
		# An empty configuration has no rule.
		set_agent_settings(excluded_title_prefixes="\n  \n")
		self.assertEqual(policy.excluded_title_prefixes(), ())
		self.assertFalse(policy.has_excluded_title("[HR] X"))

	def test_missing_field_adds_no_message(self):
		# Before migrate the DocType has no excluded_title_prefixes field: no rule, never raises, and nothing
		# lands in message_log (a web request would show it as a red dialog, STD-ERR-3).
		set_agent_settings(excluded_title_prefixes="[HR]")
		frappe.db.value_cache.pop(policy.SETTING_DOCTYPE, None)
		self.addCleanup(frappe.db.value_cache.pop, policy.SETTING_DOCTYPE, None)
		fields = frappe.get_meta(policy.SETTING_DOCTYPE)._fields
		frappe.clear_messages()
		with patch.dict(fields):
			del fields[policy.EXCLUDED_TITLE_PREFIXES_FIELD]
			self.assertEqual(policy.excluded_title_prefixes(), ())
			self.assertFalse(policy.has_excluded_title("[HR] X"))
		self.assertEqual(frappe.get_message_log(), [])


class TestSendRefusal(FrappeTestCase):
	# AC-9, ADR-034 QĐ 1, U2.md:95-102, :115-117, :130-132: one send predicate that answers with a reason code;
	# can_send_ticket is `send_refusal(ticket) is None`.
	def setUp(self):
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		set_agent_settings(excluded_teams=TEAM, excluded_title_prefixes="[HR]")
		for name in TEAMS:
			_ensure_team(name)

	def _ticket(self, **values):
		ticket = make_ticket(subject=values.pop("subject", "Hỏi về máy in"))
		for key, value in values.items():
			frappe.db.set_value("HD Ticket", ticket.name, key, value)
		return ticket.name

	def _classified_excluded(self, ticket):
		make_log_entry(
			ticket=ticket, entry_type="classify", stop_reason=policy.EXCLUDED_BY_CLASSIFICATION, applied=0
		)

	def test_order_and_codes(self):
		self.assertEqual(policy.EXCLUDED_BY_CLASSIFICATION, "excluded_by_classification")
		self.assertEqual(
			(
				policy.REFUSAL_OPTED_OUT,
				policy.REFUSAL_EXCLUDED_TEAM,
				policy.REFUSAL_EXCLUDED_TITLE,
				policy.REFUSAL_EXCLUDED_BY_CLASSIFICATION,
				policy.REFUSAL_MISSING,
			),
			("opted_out", "excluded_team", "excluded_title", "excluded_by_classification", "missing"),
		)
		self.assertEqual(
			policy.SEND_POLICY_FIELDS, (policy.OPT_OUT_FIELD, policy.TEAM_FIELD, policy.SUBJECT_FIELD)
		)
		self.assertEqual(policy.send_refusal("không có phiếu này"), policy.REFUSAL_MISSING)
		self.assertEqual(policy.send_refusal(None), policy.REFUSAL_MISSING)
		self.assertIsNone(policy.send_refusal(self._ticket()))
		self.assertIsNone(policy.send_refusal(self._ticket(agent_group="IT")))

		opted_out = self._ticket(ai_opt_out=1, agent_group=TEAM, subject="[HR] X")
		self.assertEqual(policy.send_refusal(opted_out), policy.REFUSAL_OPTED_OUT)
		team_and_title = self._ticket(agent_group=TEAM, subject="[HR] X")
		self.assertEqual(policy.send_refusal(team_and_title), policy.REFUSAL_EXCLUDED_TEAM)
		self.assertEqual(
			policy.send_refusal(self._ticket(subject="[hr] Nghỉ phép")), policy.REFUSAL_EXCLUDED_TITLE
		)
		# The prefix is the creator's intent: it counts with or without a team.
		self.assertEqual(
			policy.send_refusal(self._ticket(agent_group="IT", subject="[HR] Nghỉ phép")),
			policy.REFUSAL_EXCLUDED_TITLE,
		)
		self.assertIsNone(policy.send_refusal(self._ticket(subject="Hỏi về [HR]")))

		# A name or the saved doc gives the same answer.
		self.assertEqual(
			policy.send_refusal(frappe.get_doc("HD Ticket", team_and_title)), policy.REFUSAL_EXCLUDED_TEAM
		)

		# Excluded by classification: only while no team is set; a person's team choice ends it (A-U2-2).
		classified = self._ticket()
		self._classified_excluded(classified)
		self.assertTrue(policy.is_excluded_by_classification(classified))
		self.assertFalse(policy.is_excluded_by_classification(self._ticket()))
		self.assertEqual(policy.send_refusal(classified), policy.REFUSAL_EXCLUDED_BY_CLASSIFICATION)
		self.assertEqual(
			policy.send_refusal(frappe.get_doc("HD Ticket", classified)),
			policy.REFUSAL_EXCLUDED_BY_CLASSIFICATION,
		)
		frappe.db.set_value("HD Ticket", classified, "agent_group", "IT")
		self.assertIsNone(policy.send_refusal(classified))
		frappe.db.set_value("HD Ticket", classified, "agent_group", TEAM)
		self.assertEqual(policy.send_refusal(classified), policy.REFUSAL_EXCLUDED_TEAM)
		# A classify row with another stop_reason does not exclude.
		other = self._ticket()
		make_log_entry(ticket=other, entry_type="classify", stop_reason="end_turn", applied=0)
		self.assertIsNone(policy.send_refusal(other))

	def test_can_send_ticket_is_send_refusal_is_none(self):
		for values in ({}, {"ai_opt_out": 1}, {"agent_group": TEAM}, {"subject": "[HR] X"}):
			with self.subTest(values=values):
				name = self._ticket(**values)
				self.assertEqual(policy.can_send_ticket(name), policy.send_refusal(name) is None)
		self.assertFalse(policy.can_send_ticket(None))
		self.assertFalse(policy.can_send_ticket("không có phiếu này"))


class TestExcludedQuery(FrappeTestCase):
	# AC-8, ADR-034 QĐ 1, Ràng buộc 2, U2.md:114, :118, :129, :133: the query form of the send predicate
	# selects exactly the tickets the predicate refuses.
	def setUp(self):
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		for name in TEAMS:
			_ensure_team(name)

	def _ticket(self, subject="Hỏi về máy in", **values):
		ticket = make_ticket(subject=subject)
		for key, value in values.items():
			frappe.db.set_value("HD Ticket", ticket.name, key, value)
		return ticket.name

	def test_excluded_team_names_use_the_predicate_comparison(self):
		set_agent_settings(excluded_teams=f"  {TEAM.upper()}  \nKhông có nhóm này")
		self.assertEqual(policy.excluded_team_names(), [TEAM])
		set_agent_settings(excluded_teams="")
		self.assertEqual(policy.excluded_team_names(), [])

	def test_query_form_matches_predicate(self):
		set_agent_settings(
			excluded_teams=TEAM, excluded_title_prefixes="[HR]\n50%_off\n[Kế   toán]\nback\\slash"
		)
		opted_out = self._ticket(ai_opt_out=1)
		in_team = self._ticket(agent_group=TEAM)
		prefixed = self._ticket(subject="[HR] Nghỉ phép")
		classified = self._ticket()
		make_log_entry(
			ticket=classified, entry_type="classify", stop_reason=policy.EXCLUDED_BY_CLASSIFICATION, applied=0
		)
		combined = self._ticket(subject="[HR] X", agent_group=TEAM, ai_opt_out=1)
		normal = self._ticket()
		spaced = self._ticket(subject="   [hr]    Lương")
		upper = self._ticket(subject="[Kế TOÁN] Sổ sách")
		escapes = self._ticket(subject="50%_off sale")
		lookalike = self._ticket(subject="50Xaoff sale")
		backslash = self._ticket(subject="back\\slash x")
		not_prefix = self._ticket(subject="Hỏi về [HR]")
		classified_then_team = self._ticket(agent_group="IT")
		make_log_entry(
			ticket=classified_then_team,
			entry_type="classify",
			stop_reason=policy.EXCLUDED_BY_CLASSIFICATION,
			applied=0,
		)
		names = policy.excluded_ticket_names()
		self.assertEqual(len(names), len(set(names)))
		everything = frappe.get_all("HD Ticket", pluck="name")
		self.assertEqual(set(names), {name for name in everything if not policy.can_send_ticket(name)})
		for excluded in (
			opted_out,
			in_team,
			prefixed,
			classified,
			combined,
			spaced,
			upper,
			escapes,
			backslash,
		):
			self.assertIn(excluded, names)
		for sendable in (normal, lookalike, not_prefix, classified_then_team):
			self.assertNotIn(sendable, names)

	def test_no_rule_set_and_no_opt_out_gives_empty_candidates(self):
		set_agent_settings(excluded_teams="", excluded_title_prefixes="")
		opted_out = frappe.get_all("HD Ticket", filters={"ai_opt_out": 1}, pluck="name")
		classified = frappe.get_all(
			LOG_DOCTYPE,
			filters={"entry_type": "classify", "stop_reason": policy.EXCLUDED_BY_CLASSIFICATION},
			pluck="ticket",
		)
		self.assertEqual(
			set(policy.excluded_ticket_names()),
			{name for name in (*opted_out, *classified) if not policy.can_send_ticket(name)},
		)

	def _comment(self, ticket, doctype="HD Ticket"):
		doc = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Comment",
				"reference_doctype": doctype,
				"reference_name": ticket,
				"content": "ERPAI-TEST",
			}
		)
		doc.db_insert()
		return doc.name

	def _communication(self, ticket):
		doc = frappe.get_doc(
			{
				"doctype": "Communication",
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": "Sent",
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"subject": "ERPAI-TEST",
				"content": "ERPAI-TEST",
			}
		)
		doc.db_insert()
		return doc.name

	def _file(self, doctype, name):
		doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "ERPAI-TEST-links.txt",
				"attached_to_doctype": doctype,
				"attached_to_name": name,
				"is_private": 1,
				"content": "ERPAI-TEST",
			}
		).insert(ignore_permissions=True)
		physical = doc.get_full_path()
		self.addCleanup(lambda: os.path.exists(physical) and os.remove(physical))
		return doc.name

	def _task(self, ticket):
		doc = frappe.get_doc({"doctype": "Task", "subject": "ERPAI-TEST links", "ai_ticket": ticket})
		doc.db_insert()
		return doc.name

	def _legacy_comment(self, ticket):
		return (
			frappe.get_doc(
				{"doctype": "HD Ticket Comment", "reference_ticket": ticket, "content": "ERPAI-TEST"}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _row(self, doctype, **values):
		doc = frappe.get_doc({"doctype": doctype, **values})
		doc.db_insert()
		return doc.name

	def test_constants(self):
		self.assertEqual(
			policy.TICKET_LINK_FIELDS,
			{
				"Comment": (("reference_doctype", "reference_name"),),
				"Communication": (("reference_doctype", "reference_name"),),
				"File": (("attached_to_doctype", "attached_to_name"),),
				# R10b, R10g: the column names of the installed DocType JSON, every pair of the DocType. Version is
				# refused by the record tool instead (R10e).
				"ToDo": (("reference_type", "reference_name"),),
				"Notification Log": (("document_type", "document_name"), ("source_doctype", "source_name")),
				"Activity Log": (
					("reference_doctype", "reference_name"),
					("timeline_doctype", "timeline_name"),
					("link_doctype", "link_name"),
				),
				"Email Queue": (("reference_doctype", "reference_name"),),
				# R11a: Frappe's add_tag stores the ticket subject in the Tag Link title.
				"Tag Link": (("document_type", "document_name"),),
				"Document Follow": (("ref_doctype", "ref_docname"),),
				"Workflow Action": (("reference_doctype", "reference_name"),),
				"Reminder": (("reminder_doctype", "reminder_docname"),),
			},
		)
		# R10a; HD Ticket Comment is a known gap (R10f): D8 bars product code from naming it.
		self.assertEqual(policy.TICKET_PARENT_DOCTYPES, ("Comment", "Communication"))
		self.assertEqual(policy.EXCLUDED_TICKET_REASON, "bản ghi thuộc phiếu không được phép đưa cho AI")

	def test_owning_ticket_per_doctype(self):
		ticket = self._ticket()
		records = (
			("HD Ticket", ticket),
			("Comment", self._comment(ticket)),
			("Communication", self._communication(ticket)),
			("File", self._file("HD Ticket", ticket)),
			("HD Ticket Comment", self._legacy_comment(ticket)),
			("Task", self._task(ticket)),
		)
		for doctype, name in records:
			with self.subTest(doctype=doctype):
				self.assertEqual(policy.owning_ticket(doctype, name), ticket)
		# Attached to or commenting on another DocType: no ticket.
		todo = frappe.get_doc({"doctype": "ToDo", "description": "ERPAI-TEST"}).insert(
			ignore_permissions=True
		)
		self.assertIsNone(policy.owning_ticket("File", self._file("ToDo", todo.name)))
		self.assertIsNone(policy.owning_ticket("Comment", self._comment(todo.name, "ToDo")))
		# Missing record, empty name, DocType outside the set.
		for doctype, name in (
			("Comment", "không có bản ghi này"),
			("HD Ticket", "không có phiếu này"),
			("Task", ""),
			("User", "Administrator"),
			("Không có DocType này", "x"),
		):
			with self.subTest(doctype=doctype, name=name):
				self.assertIsNone(policy.owning_ticket(doctype, name))

	def test_link_columns_dynamic_plus_static(self):
		self.assertEqual(policy.ticket_link_columns("Comment"), (("reference_doctype", "reference_name"),))
		self.assertEqual(policy.ticket_link_columns("File"), (("attached_to_doctype", "attached_to_name"),))
		self.assertEqual(policy.ticket_link_columns("HD Ticket Comment"), ((None, "reference_ticket"),))
		self.assertEqual(policy.ticket_link_columns("task"), ((None, "ai_ticket"),))
		# R10g: every pair of the DocType, in declaration order.
		self.assertEqual(
			policy.ticket_link_columns("Activity Log"),
			(
				("reference_doctype", "reference_name"),
				("timeline_doctype", "timeline_name"),
				("link_doctype", "link_name"),
			),
		)
		self.assertEqual(
			policy.ticket_link_columns("Notification Log"),
			(("document_type", "document_name"), ("source_doctype", "source_name")),
		)
		for doctype in ("HD Ticket", "User", "Không có DocType này"):
			self.assertEqual(policy.ticket_link_columns(doctype), ())
		# A DocType with both: the dynamic pair plus every static Link, neither excludes the other.
		with patch.object(policy, "ticket_link_fieldnames", return_value=("custom_ticket",)):
			self.assertEqual(
				policy.ticket_link_columns("Comment"),
				(("reference_doctype", "reference_name"), (None, "custom_ticket")),
			)

	def test_link_columns_derived_from_the_live_schema(self):
		# R11d: every (Link to DocType, Dynamic Link on it) pair of the live meta, none listed in TICKET_LINK_FIELDS;
		# the column names of the installed DocType JSON.
		for doctype, pair in (
			("Integration Request", ("reference_doctype", "reference_docname")),
			("Discussion Topic", ("reference_doctype", "reference_docname")),
			("Auto Repeat", ("reference_doctype", "reference_document")),
			("View Log", ("reference_doctype", "reference_name")),
			("Event", ("reference_doctype", "reference_docname")),
		):
			with self.subTest(doctype=doctype):
				self.assertNotIn(doctype, policy.TICKET_LINK_FIELDS)
				self.assertEqual(policy.ticket_link_columns(doctype), (pair,))

	def test_custom_dynamic_pair_is_picked_up(self):
		# R11d: a (Link to DocType, Dynamic Link on it) pair a Custom Field adds is read from the live meta. Note's
		# `title` and `content` columns stand in for the columns of that pair, in a private meta (load_meta never
		# caches): a real Custom Field runs ALTER TABLE, which commits, and puts its meta into the shared cache.
		set_agent_settings(excluded_teams=TEAM, excluded_title_prefixes="")
		excluded = self._ticket(agent_group=TEAM)
		normal = self._ticket()
		on_excluded = self._row("Note", title="HD Ticket", content=excluded)
		on_normal = self._row("Note", title="HD Ticket", content=normal)
		meta = load_meta("Note")
		meta.get_field("title").update({"fieldtype": "Link", "options": "DocType"})
		meta.get_field("content").update({"fieldtype": "Dynamic Link", "options": "title"})
		# Not pairs: a Dynamic Link on a Link to another DocType, and one on no field.
		meta.fields.extend(
			[
				frappe._dict(fieldname="custom_party_type", fieldtype="Link", options="User"),
				frappe._dict(fieldname="custom_party", fieldtype="Dynamic Link", options="custom_party_type"),
				frappe._dict(fieldname="custom_orphan", fieldtype="Dynamic Link", options="no_such_field"),
			]
		)
		real_get_meta = frappe.get_meta

		def get_meta(doctype, *args, **kwargs):
			return meta if doctype == "Note" else real_get_meta(doctype, *args, **kwargs)

		with patch.object(frappe, "get_meta", side_effect=get_meta):
			self.assertEqual(policy.ticket_link_columns("Note"), (("title", "content"),))
			self.assertEqual(policy.link_column_names("Note"), ["title", "content"])
			self.assertEqual(
				policy.linked_tickets("Note", {"title": "HD Ticket", "content": excluded}), [excluded]
			)
			self.assertTrue(policy.is_ticket_record_excluded("Note", on_excluded))
			self.assertFalse(policy.is_ticket_record_excluded("Note", on_normal))
			filters, or_filters = policy.ticket_content_filters("Note")
			self.assertEqual(filters, [])
			self.assertEqual(or_filters[0], ["title", "not in", ["HD Ticket", "Comment", "Communication"]])
			self.assertIn(excluded, or_filters[1][2])
			# The exclusion is part of the query.
			listed = frappe.get_list(
				"Note",
				filters=[["name", "in", [on_excluded, on_normal]], *filters],
				or_filters=or_filters,
				pluck="name",
			)
			self.assertEqual(listed, [on_normal])

	def test_parent_link_fields(self):
		# R10g: a Link to Comment or Communication, read from the live schema like a Link to HD Ticket.
		for doctype in ("Email Queue", "email queue"):
			self.assertEqual(policy.parent_link_fields(doctype), (("communication", "Communication"),))
		self.assertEqual(policy.parent_link_fields("Communication"), (("in_reply_to", "Communication"),))
		for doctype in ("Comment", "File", "Task", "Không có DocType này"):
			self.assertEqual(policy.parent_link_fields(doctype), ())
		self.assertEqual(
			policy.link_column_names("Email Queue"), ["reference_doctype", "reference_name", "communication"]
		)
		self.assertEqual(policy.link_column_names("task"), ["ai_ticket"])
		self.assertEqual(policy.link_column_names("User"), [])

	def test_ticket_content_filters_other_pairs_and_parent_links(self):
		# R10g: get_list takes one OR group, so the rows that another pair points at an excluded ticket (or a record
		# of one) are left out by name; a Link to Comment or Communication is compared with the records of the
		# excluded tickets.
		names = ["T-1", "T-2"]
		owners = ["HD Ticket", "Comment", "Communication"]
		communication = self._communication("T-1")
		timeline = self._row("Activity Log", timeline_doctype="HD Ticket", timeline_name="T-2")
		linked = self._row("Activity Log", link_doctype="Communication", link_name=communication)
		other = self._row("Activity Log", timeline_doctype="ToDo", timeline_name="T-1")
		pair = [
			["reference_doctype", "not in", owners],
			["reference_name", "not in", [*names, communication]],
		]
		with patch.object(policy, "excluded_ticket_names", return_value=names):
			filters, or_filters = policy.ticket_content_filters("Activity Log")
			self.assertEqual(or_filters, pair)
			self.assertEqual([row[:2] for row in filters], [["name", "not in"]])
			self.assertEqual(set(filters[0][2]), {timeline, linked})
			self.assertNotIn(other, filters[0][2])
			self.assertEqual(
				policy.ticket_content_filters("Email Queue"),
				([["communication", "not in", [communication]]], pair),
			)

	def test_ticket_content_filters_empty_when_nothing_excluded(self):
		with patch.object(policy, "excluded_ticket_names", return_value=[]):
			for doctype in (
				"HD Ticket",
				"Comment",
				"Communication",
				"File",
				"HD Ticket Comment",
				"Task",
				"User",
			):
				with self.subTest(doctype=doctype):
					self.assertEqual(policy.ticket_content_filters(doctype), ([], []))
		with patch.object(policy, "excluded_ticket_names", return_value=["T-1"]):
			for doctype in ("User", "Không có DocType này"):
				with self.subTest(doctype=doctype):
					self.assertEqual(policy.ticket_content_filters(doctype), ([], []))

	def test_ticket_content_filters_shapes(self):
		# No Comment or Communication points at these names: the name list is the tickets only.
		names = ["T-1", "T-2"]
		owners = ["HD Ticket", "Comment", "Communication"]
		real_fieldnames = policy.ticket_link_fieldnames
		with patch.object(policy, "excluded_ticket_names", return_value=names):
			self.assertEqual(policy.ticket_content_filters("HD Ticket"), ([["name", "not in", names]], []))
			for doctype, (type_column, name_column) in (
				("Comment", ("reference_doctype", "reference_name")),
				("File", ("attached_to_doctype", "attached_to_name")),
				("ToDo", ("reference_type", "reference_name")),
				("Email Queue", ("reference_doctype", "reference_name")),
			):
				with self.subTest(doctype=doctype):
					self.assertEqual(
						policy.ticket_content_filters(doctype),
						([], [[type_column, "not in", owners], [name_column, "not in", names]]),
					)
			self.assertEqual(policy.ticket_content_filters("Task"), ([["ai_ticket", "not in", names]], []))
			self.assertEqual(
				policy.ticket_content_filters("HD Ticket Comment"),
				([["reference_ticket", "not in", names]], []),
			)
			# A stub column on File only: the parent DocTypes are queried on their real columns.
			with patch.object(
				policy,
				"ticket_link_fieldnames",
				side_effect=lambda doctype: ("custom_ticket",)
				if doctype == "File"
				else real_fieldnames(doctype),
			):
				self.assertEqual(
					policy.ticket_content_filters("File"),
					(
						[["custom_ticket", "not in", names]],
						[["attached_to_doctype", "not in", owners], ["attached_to_name", "not in", names]],
					),
				)

	def test_record_on_a_ticket_comment_or_communication_belongs_to_the_ticket(self):
		# R10a: one hop more through Comment and Communication, no deeper (HD Ticket Comment is a known gap, R10f);
		# R10b: ToDo names its ticket by its own pair; R10g: the other pairs of the log DocTypes and Email Queue's
		# Link to Communication go the same hop.
		set_agent_settings(excluded_teams=TEAM, excluded_title_prefixes="")
		excluded = self._ticket(agent_group=TEAM)
		comment = self._comment(excluded)
		communication = self._communication(excluded)
		on_comment = self._comment(comment, "Comment")
		todo = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "ERPAI-TEST",
				"reference_type": "HD Ticket",
				"reference_name": excluded,
			}
		)
		todo.db_insert()
		for doctype, name in (
			("File", self._file("Comment", comment)),
			("File", self._file("Communication", communication)),
			("Comment", on_comment),
			("ToDo", todo.name),
			("Activity Log", self._row("Activity Log", timeline_doctype="HD Ticket", timeline_name=excluded)),
			("Activity Log", self._row("Activity Log", link_doctype="Comment", link_name=comment)),
			(
				"Notification Log",
				self._row("Notification Log", source_doctype="Communication", source_name=communication),
			),
			("Email Queue", self._row("Email Queue", communication=communication)),
		):
			with self.subTest(doctype=doctype, name=name):
				self.assertEqual(policy.owning_ticket(doctype, name), excluded)
				self.assertTrue(policy.is_ticket_record_excluded(doctype, name))
		self.assertIsNone(policy.owning_ticket("File", self._file("Comment", on_comment)))
		# R10h: the values of a record about to be written; the type in any case, the name as a number.
		for doctype, values in (
			("File", {"attached_to_doctype": "comment", "attached_to_name": comment}),
			("Comment", {"reference_doctype": "Communication", "reference_name": communication}),
			("Email Queue", {"communication": communication}),
			("ToDo", {"reference_type": "HD Ticket", "reference_name": int(excluded)}),
		):
			with self.subTest(values=values):
				self.assertEqual(policy.linked_tickets(doctype, values), [str(excluded)])
		for values in (
			{"attached_to_doctype": "Comment", "attached_to_name": on_comment},
			{"attached_to_doctype": "Comment", "attached_to_name": ""},
			{"attached_to_doctype": "", "attached_to_name": comment},
		):
			with self.subTest(values=values):
				self.assertEqual(policy.linked_tickets("File", values), [])
		filters, or_filters = policy.ticket_content_filters("File")
		self.assertEqual(filters, [])
		self.assertEqual(
			or_filters[0],
			["attached_to_doctype", "not in", ["HD Ticket", "Comment", "Communication"]],
		)
		self.assertEqual(or_filters[1][:2], ["attached_to_name", "not in"])
		self.assertLessEqual({excluded, comment, communication}, set(or_filters[1][2]))
		self.assertNotIn(on_comment, or_filters[1][2])

	def test_is_ticket_record_excluded_follows_the_owning_ticket(self):
		set_agent_settings(excluded_teams=TEAM, excluded_title_prefixes="")
		normal = self._ticket()
		excluded = self._ticket(agent_group=TEAM)
		for doctype, make in (
			("HD Ticket", lambda ticket: ticket),
			("Comment", self._comment),
			("Communication", self._communication),
			("File", lambda ticket: self._file("HD Ticket", ticket)),
			("HD Ticket Comment", self._legacy_comment),
			("Task", self._task),
		):
			with self.subTest(doctype=doctype):
				self.assertFalse(policy.is_ticket_record_excluded(doctype, make(normal)))
				self.assertTrue(policy.is_ticket_record_excluded(doctype, make(excluded)))
		self.assertFalse(policy.is_ticket_record_excluded("User", "Administrator"))
		self.assertFalse(policy.is_ticket_record_excluded("Comment", "không có bản ghi này"))
		# Any one excluded ticket among the columns excludes the record.
		comment = self._comment(normal)
		real_get_value = frappe.db.get_value

		def get_value(doctype, name=None, *args, **kwargs):
			if doctype == "Comment" and name == comment:
				return frappe._dict(
					reference_doctype="HD Ticket", reference_name=normal, custom_ticket=excluded
				)
			return real_get_value(doctype, name, *args, **kwargs)

		with (
			patch.object(policy, "ticket_link_fieldnames", return_value=("custom_ticket",)),
			patch.object(frappe.db, "get_value", side_effect=get_value),
		):
			self.assertTrue(policy.is_ticket_record_excluded("Comment", comment))


def _lesson_user(email, *roles):
	"""A user holding exactly `roles`, created inside the test transaction."""
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


class TestLessonPolicy(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		keep_agent_settings(self)

	def test_lesson_settings_defaults(self):
		set_agent_settings(lessons_enabled=1, lessons_max_per_request=5, lessons_max_chars=2000)
		self.assertEqual(
			policy.lesson_settings(frappe.get_single("ERP AI Setting")), LessonSettings(True, 5, 2000, 500)
		)

	def test_lesson_settings_out_of_range_reads_default(self):
		set_agent_settings(lessons_enabled=0, lessons_max_per_request=99, lessons_max_chars=5)
		self.assertEqual(
			policy.lesson_settings(frappe.get_single("ERP AI Setting")), LessonSettings(False, 5, 2000, 500)
		)

	def test_teach_marker_is_stripped_and_blank_is_empty(self):
		set_agent_settings(lesson_teach_marker="  ghi nhớ: ")
		self.assertEqual(policy.lesson_teach_marker(), "ghi nhớ:")
		set_agent_settings(lesson_teach_marker="   ")
		self.assertEqual(policy.lesson_teach_marker(), "")

	def test_approver_is_reviewer_or_system_manager(self):
		reviewer = _lesson_user("lesson.reviewer@example.com", "Desk User")
		manager = _lesson_user("lesson.manager@example.com", "System Manager")
		instructor = _lesson_user("lesson.instructor@example.com", ROLE_INSTRUCTOR)
		set_agent_settings(
			monthly_reviewers="\n".join([reviewer, "", "Administrator", "Guest", AGENT_USER]),
		)
		self.assertTrue(policy.is_lesson_approver(reviewer))
		self.assertTrue(policy.is_lesson_approver(manager))
		self.assertFalse(policy.is_lesson_approver(instructor))
		for user in ("Administrator", "Guest", AGENT_USER, "", None):
			self.assertFalse(policy.is_lesson_approver(user), user)

	def test_manager_is_instructor_only(self):
		instructor = _lesson_user("lesson.instructor@example.com", ROLE_INSTRUCTOR)
		manager = _lesson_user("lesson.manager@example.com", "System Manager")
		self.assertTrue(policy.can_manage_lessons(instructor))
		self.assertFalse(policy.can_manage_lessons(manager))
		for user in ("Administrator", "Guest", AGENT_USER, "", None):
			self.assertFalse(policy.can_manage_lessons(user), user)

	def test_limit_errors(self):
		def errors(**caps):
			return policy.lesson_limit_errors(frappe._dict(caps))

		for value in (0, 21):
			self.assertEqual(len(errors(lessons_max_per_request=value)), 1, value)
		# R13: one lesson of the largest size (300 + 1000 characters) always fits under the smallest cap
		self.assertEqual(policy.LESSONS_CHARS_RANGE, (1300, 20000))
		for value in (1299, 20001):
			self.assertEqual(len(errors(lessons_max_chars=value)), 1, value)
		for per_request, chars in ((1, 1300), (20, 20000)):
			self.assertEqual(errors(lessons_max_per_request=per_request, lessons_max_chars=chars), [])
		self.assertEqual(errors(), [])
		for value in ("abc", 0, True):
			self.assertEqual(len(errors(lessons_max_chars=value)), 1, value)
