import os
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime
from helpdesk.test_utils import make_ticket

from erp_ai.agent import policy
from erp_ai.constants import CORE_APPS, LOG_DOCTYPE, SETTING_DOCTYPE
from erp_ai.test_utils import TempAppsRoot, keep_agent_settings, set_agent_settings

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

	def _log(self, ticket, run_id, entry_type="classify", created=None):
		log = frappe.get_doc(
			{"doctype": LOG_DOCTYPE, "ticket": ticket, "run_id": run_id, "entry_type": entry_type, "turn": 0}
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
	# U1 3.1: the five permission switches, read in one place, in the spec's order (1)..(5).
	FIELD_FLAGS = (
		("unrestricted_enabled", "unrestricted"),
		("record_tools_enabled", "record_tools"),
		("act_now_enabled", "act_now"),
		("code_change_enabled", "code_change"),
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
		self.assertEqual(policy.PermissionSwitches(), policy.PermissionSwitches(*off.values()))
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
		# Read from the stored setting: (2) and (5) on, the rest off.
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


class TestBudget(FrappeTestCase):
	# AC-61: the month's spend is summed from live ERP AI Log rows, never from spent_this_month_usd.
	# A far month keeps the site's own log rows out of the sums; every row carries a different cost.
	JUNE = datetime(2031, 6, 15, 10, 0)

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def _log(self, created, cost_usd=None, entry_type="classify"):
		values = {"doctype": LOG_DOCTYPE, "run_id": f"budget-{created}", "entry_type": entry_type, "turn": 0}
		if cost_usd is not None:
			values["cost_usd"] = cost_usd
		log = frappe.get_doc(values).insert(ignore_permissions=True)
		frappe.db.set_value(LOG_DOCTYPE, log.name, "creation", created, update_modified=False)

	def _june_rows(self):
		self._log(datetime(2031, 5, 31, 23, 59, 59), 100.0)  # last second of the month before
		self._log(datetime(2031, 6, 1, 0, 0, 0), 0.125)  # first instant of the month counts
		self._log(datetime(2031, 6, 15, 9, 0), 1.25, "classify")
		self._log(datetime(2031, 6, 30, 23, 59, 59), 2.5, "reason")
		self._log(datetime(2031, 6, 20, 8, 0), None, "skip")  # no cost_usd: adds nothing
		self._log(datetime(2031, 7, 1, 0, 0, 0), 1000.0)  # first instant of the next month

	def test_month_spend_sums_live_log_rows(self):
		self._june_rows()
		for now in (datetime(2031, 6, 1, 0, 0), self.JUNE, datetime(2031, 6, 30, 23, 59, 59)):
			with self.subTest(now=now):
				spend = policy.month_spend_usd(now=now)
				self.assertIsInstance(spend, float)
				self.assertEqual(spend, 3.875)
		self.assertEqual(policy.month_spend_usd(now=datetime(2031, 5, 2)), 100.0)
		self.assertEqual(policy.month_spend_usd(now=datetime(2031, 7, 31, 12)), 1000.0)
		# December rolls over to January of the next year.
		self._log(datetime(2031, 12, 31, 23, 59, 59), 7.0)
		self._log(datetime(2032, 1, 1, 0, 0, 0), 50.0)
		self.assertEqual(policy.month_spend_usd(now=datetime(2031, 12, 10)), 7.0)
		self.assertEqual(policy.month_spend_usd(now=datetime(2032, 1, 10)), 50.0)
		# A month without rows spends 0.0.
		self.assertEqual(policy.month_spend_usd(now=datetime(2031, 9, 10)), 0.0)

	def test_over_budget_reads_log_not_spent_field(self):
		self._june_rows()  # June spends 3.875
		cases = [
			({"monthly_budget_usd": 3.5, "spent_this_month_usd": 0}, True),
			({"monthly_budget_usd": 4, "spent_this_month_usd": 999}, False),
			({"monthly_budget_usd": 3.875, "spent_this_month_usd": 999}, False),  # equal is not over
			({"monthly_budget_usd": None, "spent_this_month_usd": 0}, True),
		]
		for fields, expected in cases:
			with self.subTest(**fields):
				self.assertIs(policy.is_over_budget(frappe._dict(fields), now=self.JUNE), expected)
		# No spend and no budget: 0 > 0 is not over.
		empty = frappe._dict(monthly_budget_usd=0, spent_this_month_usd=5)
		self.assertIs(policy.is_over_budget(empty, now=datetime(2031, 9, 10)), False)
		# The stored setting is read the same way.
		set_agent_settings(monthly_budget_usd=3.75, spent_this_month_usd=0)
		self.assertIs(policy.is_over_budget(frappe.get_doc(SETTING_DOCTYPE), now=self.JUNE), True)

	def test_over_budget_caps_permission_level_at_l1(self):
		over = {"L3": "L1", "L2": "L1", "L1": "L1", "L0": "L0"}
		for level, expected in over.items():
			with self.subTest(level=level):
				# the spent field says "far over" but only the flag counts
				settings = frappe._dict(
					permission_level=level, monthly_budget_usd=1, spent_this_month_usd=999
				)
				self.assertEqual(policy.effective_level(settings, over_budget=True), expected)
				self.assertEqual(policy.effective_level(settings, over_budget=False), level)
		with self.assertRaises(TypeError):
			policy.effective_level(frappe._dict(permission_level="L3"), True)
