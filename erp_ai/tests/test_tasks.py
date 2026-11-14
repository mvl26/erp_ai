from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import hooks, tasks
from erp_ai.agent import run_log, runner
from erp_ai.agent.tools import site_api
from erp_ai.agent.tools.registry import ToolContext, execute_tool
from erp_ai.constants import (
	AGENT_USER,
	CREDENTIAL_DOCTYPE,
	HELPDESK_AGENT_ROLE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_QUOTA_EXHAUSTED,
	LOG_DOCTYPE,
	ROLE_AGENT,
	SETTING_DOCTYPE,
	TITLE_ALARM,
	TITLE_RUN_FAILED,
	TRIGGER_CHANGE_ACTION,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_setting import erp_ai_setting
from erp_ai.gateway import client
from erp_ai.test_utils import add_credential, make_change_proposal, set_agent_settings

# Far-future months cannot hold real ERP AI Log rows, so sums only see rows the test inserts.
NOW = datetime(2031, 11, 15, 8, 0, 0)
THIS_MONTH = datetime(2031, 11, 3, 9, 0, 0)
LAST_MONTH = datetime(2031, 10, 31, 23, 59, 59)
FIRST_OF_MONTH = datetime(2031, 11, 1, 0, 0, 0)
NEXT_MONTH = datetime(2031, 12, 1, 0, 0, 0)
# The privilege alarm reads ERP AI Log in (watermark, upper]: real rows are older than the far-future watermark.
WATERMARK = datetime(2031, 11, 15, 8, 0, 0)
SEEDED_AT = datetime(2031, 11, 15, 8, 10, 0)
RUN_AT = datetime(2031, 11, 15, 9, 0, 0)
UPPER = RUN_AT - timedelta(seconds=300)
PERMISSION_SUBJECT = "Agent đã sửa bản ghi phân quyền"
INSTRUCTOR = "erpai-tasks-boss@example.invalid"
PROFILE_PREFIX = "ERPAI-TEST hồ sơ"
BY = "(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)"
NO_BEFORE_AFTER = ", không có trước/sau"
FAKE_KEY = "sk-ERPAI-TEST-fake-0123456789abcdef"


def _add_log(cost_usd, label, creation):
	"""Insert an ERP AI Log row inside the test transaction and back-date `creation`."""
	doc = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"run_id": "ERPAI-TEST-run",
			"entry_type": "skip",
			"trigger": TRIGGER_TICKET_INSERT,
			"turn": 0,
			"cost_usd": cost_usd,
			"credential_label": label,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(LOG_DOCTYPE, doc.name, "creation", creation, update_modified=False)
	return doc.name


def _hand_action(tool, doctype, name, ok=True):
	"""An action entry of a `reason` row as the runner writes it, for cases the tools cannot seed."""
	return {"tool": tool, "doctype": doctype, "name": name, "ok": ok, "instructor": INSTRUCTOR}


class TestRecomputeMonthlySpend(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_error = patch("frappe.log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		self.label_a = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		self.label_b = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		set_agent_settings(spent_this_month_usd=99)
		self.row_a = add_credential(self.label_a, spent_month_usd=77)
		self.row_b = add_credential(self.label_b, spent_month_usd=55)

	def _spent_total(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")

	def _spent_key(self, row):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, row, "spent_month_usd")

	def test_recompute_spend_from_log(self):
		_add_log(0.25, self.label_a, THIS_MONTH)
		_add_log(0.5, self.label_a, FIRST_OF_MONTH)
		_add_log(1.125, self.label_b, THIS_MONTH)
		_add_log(0.0625, "", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 1.9375, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.75, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_b), 1.125, places=6)

	def test_month_start_resets_to_zero(self):
		_add_log(3.0, self.label_a, LAST_MONTH)

		tasks.recompute_monthly_spend(now=datetime(2031, 11, 1, 0, 5, 0))

		self.assertEqual(self._spent_total(), 0)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_only_logs_of_the_month_of_now_count(self):
		_add_log(3.0, self.label_a, LAST_MONTH)
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)

	def test_logs_after_the_month_of_now_are_not_counted(self):
		_add_log(2.0, self.label_a, NEXT_MONTH)
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)

	def test_label_without_credential_row_does_not_break_and_key_without_log_gets_zero(self):
		_add_log(0.5, f"{self.label_a}-gone", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_recompute_spend_unchanged_by_change_rows(self):
		_add_log(0.5, self.label_a, THIS_MONTH)
		proposal = make_change_proposal()
		for step in ("propose", "approve", "apply"):
			name = run_log.write_entry(
				ticket=proposal.ticket,
				run_id=proposal.run_id,
				entry_type="change",
				trigger=TRIGGER_CHANGE_ACTION,
				change_step=step,
				actor="Administrator",
				change_proposal=proposal.name,
			)
			frappe.db.set_value(LOG_DOCTYPE, name, "creation", THIS_MONTH, update_modified=False)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_default_now_is_current_time(self):
		tasks.recompute_monthly_spend()
		baseline = self._spent_total()
		_add_log(0.5, self.label_a, frappe.utils.now_datetime())

		tasks.recompute_monthly_spend()

		self.assertAlmostEqual(self._spent_total() - baseline, 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)

	def test_null_credential_label_counts_in_total_only(self):
		_add_log(0.5, None, THIS_MONTH)
		_add_log(0.25, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.75, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.25, places=6)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_key_rows_are_written_without_touching_modified(self):
		modified_before = frappe.db.get_value(CREDENTIAL_DOCTYPE, self.row_a, "modified")
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, self.row_a, "modified"), modified_before)

	def test_db_error_is_logged_and_rolled_back_not_raised(self):
		_add_log(0.5, self.label_a, THIS_MONTH)
		frappe.db.savepoint("t33_before_job")
		real_rollback = frappe.db.rollback

		def rollback_to_savepoint(*args, **kwargs):
			real_rollback(save_point="t33_before_job")

		with (
			patch.object(frappe.db, "set_value", side_effect=frappe.QueryTimeoutError("boom")),
			patch.object(frappe.db, "rollback", side_effect=rollback_to_savepoint) as rollback,
		):
			tasks.recompute_monthly_spend(now=NOW)

		rollback.assert_called_once()
		self.log_error.assert_called_once_with(
			TITLE_RUN_FAILED, "recompute_monthly_spend month=2031-11 error=QueryTimeoutError"
		)
		self.assertEqual(self._spent_total(), 99)
		self.assertEqual(self._spent_key(self.row_a), 77)
		self.assertEqual(self._spent_key(self.row_b), 55)

	def test_hook_registered_in_daily_scheduler(self):
		self.assertIn("erp_ai.tasks.recompute_monthly_spend", hooks.scheduler_events["daily"])


class TestCheckPrivilegeEscalation(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_error = patch("frappe.log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		self.send_alarm_patch = patch("erp_ai.alerts.send_alarm")
		self.send_alarm = self.send_alarm_patch.start()
		self.addCleanup(self.send_alarm_patch.stop)
		# Keys already on the site must not influence the key condition.
		frappe.db.set_value(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE}, "enabled", 0)
		# The agent's real roles on the site must not influence the role condition: start from
		# exactly the allowed set (rolled back with the test transaction).
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User"})
		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
			self._add_role(role)
		self._neutralize_agent_rows()
		# Real ERP AI Log rows of the site are older than this watermark, so only seeded rows are read.
		frappe.db.set_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", WATERMARK)
		if not frappe.db.exists("User", INSTRUCTOR):
			frappe.get_doc(
				{"doctype": "User", "email": INSTRUCTOR, "first_name": "ERPAI-TEST", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.addCleanup(frappe.clear_cache, user=AGENT_USER)

	@contextmanager
	def _as_agent(self):
		# Only System Manager may write Role Profile / User Permission: granted to the agent for the seeding only.
		self._add_role("System Manager")
		frappe.clear_cache(user=AGENT_USER)
		frappe.set_user(AGENT_USER)
		try:
			yield
		finally:
			frappe.set_user("Administrator")
			frappe.db.delete(
				"Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": "System Manager"}
			)
			frappe.clear_cache(user=AGENT_USER)

	def _log_row(
		self, actions, before=None, after=None, instructor=INSTRUCTOR, at=SEEDED_AT, entry_type="reason"
	):
		"""Write one ERP AI Log row in the runner's shape (design-amd2 §2) and back-date its `creation`."""
		name = run_log.write_entry(
			run_id="ERPAI-TEST-run",
			entry_type=entry_type,
			trigger=TRIGGER_TICKET_INSERT,
			turn=1,
			instructor=instructor,
			actions=actions,
			value_before=before or None,
			value_after=after or None,
		)
		frappe.db.set_value(LOG_DOCTYPE, name, "creation", at, update_modified=False)
		return name

	def _agent_calls(self, *calls, at=SEEDED_AT, instructor=INSTRUCTOR, unrestricted=False):
		"""Run generic write tools as the agent account and log them as one `reason` row, as the runner does.
		Returns the name of each written record."""
		context = ToolContext(
			ticket_name="",
			effective_level="L3",
			instructor=instructor,
			run_id="ERPAI-TEST-run",
			category_mapping={},
			agent_user=AGENT_USER,
			change_enabled=True,
			unrestricted=unrestricted,
		)
		actions, before, after = [], {}, {}
		with self._as_agent():
			for tool, arguments in calls:
				outcome = execute_tool(tool, arguments, context)
				self.assertTrue(outcome.get("ok"), outcome)
				actions.append(runner._action(tool, context, outcome, True, arguments))
				runner._record_snapshot(tool, outcome, len(actions), before, after)
			self._log_row(actions, before, after, instructor, at)
		return [action["name"] for action in actions]

	def _create_profile(self, label, at=SEEDED_AT):
		values = {"role_profile": f"{PROFILE_PREFIX} {label}", "roles": [{"role": "Desk User"}]}
		return self._agent_calls(("api_create_record", {"doctype": "Role Profile", "values": values}), at=at)[
			0
		]

	def _changes(self, lower=WATERMARK, upper=UPPER):
		return tasks._privilege_changes_by_agent(lower, upper)

	def _permission_alarm(self):
		messages = [m for m in self._alarm_messages() if m.startswith(f"{PERMISSION_SUBJECT}:")]
		self.assertEqual(len(messages), 1, self._alarm_messages())
		return messages[0]

	def _neutralize_agent_rows(self):
		# Live rows attributed to the agent must not influence the permission-record and
		# script/webhook conditions: reattribute or disable them (rolled back with the test).
		for doctype in tasks.PERMISSION_DOCTYPES:
			if frappe.db.exists("DocType", doctype):
				frappe.db.set_value(
					doctype,
					{"modified_by": AGENT_USER},
					"modified_by",
					"Administrator",
					update_modified=False,
				)
		frappe.db.set_value("Server Script", {"owner": AGENT_USER}, "disabled", 1)
		frappe.db.set_value("Webhook", {"owner": AGENT_USER}, "enabled", 0)

	def _run(self):
		tasks.check_privilege_escalation(now=RUN_AT)
		self.log_error.assert_not_called()

	def _add_role(self, role):
		frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": AGENT_USER,
				"parenttype": "User",
				"parentfield": "roles",
				"role": role,
			}
		).insert(ignore_permissions=True)

	def _add_perm(self, modified_by):
		doc = frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parent": "ToDo",
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": "System Manager",
				"permlevel": 7,
				"read": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Custom DocPerm", doc.name, "modified_by", modified_by, update_modified=False)
		return doc.name

	def _add_server_script(self, owner, disabled):
		suffix = frappe.generate_hash(length=6)
		doc = frappe.get_doc(
			{
				"doctype": "Server Script",
				"name": f"ERPAI-TEST-{suffix}",
				"script_type": "API",
				"api_method": f"erpai_test_{suffix}",
				"allow_guest": 0,
				"disabled": disabled,
				"script": "frappe.response['message'] = 1",
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Server Script", doc.name, "owner", owner, update_modified=False)
		return doc.name

	def _add_webhook(self, owner, enabled):
		doc = frappe.get_doc(
			{
				"doctype": "Webhook",
				"name": f"ERPAI-TEST-{frappe.generate_hash(length=6)}",
				"webhook_doctype": "ToDo",
				"webhook_docevent": "on_update",
				"request_url": "https://example.invalid/erpai-test",
				"request_method": "POST",
				"request_structure": "Form URL-Encoded",
				"enabled": enabled,
			}
		)
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Webhook", doc.name, "owner", owner, update_modified=False)
		return doc.name

	def _add_empty_key(self, enabled=1):
		label = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		row = add_credential(label, enabled=enabled)
		frappe.db.set_value(CREDENTIAL_DOCTYPE, row, "api_key", "")
		return label

	def _alarm_messages(self):
		return [call.args[1] for call in self.send_alarm.call_args_list]

	def test_no_condition_sends_no_alarm(self):
		self._run()

		self.send_alarm.assert_not_called()

	def test_alarm_on_role_drift(self):
		self._add_role("System Manager")

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn("System Manager", self._alarm_messages()[0])

	def test_allowed_roles_do_not_alarm(self):
		self._add_role("Desk User")

		self._run()

		self.send_alarm.assert_not_called()

	def test_alarm_when_agent_account_is_missing(self):
		real_exists = frappe.db.exists

		def exists(doctype, name=None, *args, **kwargs):
			if doctype == "User" and name == AGENT_USER:
				return None
			return real_exists(doctype, name, *args, **kwargs)

		with patch.object(frappe.db, "exists", side_effect=exists):
			self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn(AGENT_USER, self._alarm_messages()[0])

	def test_alarm_when_agent_lost_a_required_role(self):
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "role": ROLE_AGENT})

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn(ROLE_AGENT, self._alarm_messages()[0])

	def test_alarm_on_permission_records_modified_by_agent(self):
		profile, permission = self._agent_calls(
			(
				"api_create_record",
				{
					"doctype": "Role Profile",
					"values": {"role_profile": f"{PROFILE_PREFIX} 1", "roles": [{"role": "Desk User"}]},
				},
			),
			(
				"api_create_record",
				{
					"doctype": "User Permission",
					"values": {"user": INSTRUCTOR, "allow": "Role", "for_value": "Desk User"},
				},
			),
		)
		self._agent_calls(
			(
				"api_update_record",
				{"doctype": "Role Profile", "name": profile, "values": {"roles": [{"role": "Desk User"}]}},
			),
			at=datetime(2031, 11, 15, 8, 20, 0),
		)
		# DocType rows are built by hand: saving a real DocType runs DDL, which commits implicitly.
		old_perms = [{"role": "Desk User", "read": 1}]
		new_perms = [{"role": "Desk User", "read": 1, "write": 1}]
		for name, after_perms, at in (
			("Note", new_perms, datetime(2031, 11, 15, 8, 30, 0)),
			("ToDo", old_perms, datetime(2031, 11, 15, 8, 40, 0)),
		):
			self._log_row(
				[_hand_action("api_update_record", "DocType", name)],
				{"api_update_record#1": {"name": name, "permissions": old_perms}},
				{"api_update_record#1": {"name": name, "permissions": after_perms}},
				at=at,
			)

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertEqual(
			self._alarm_messages()[0],
			"Agent đã sửa bản ghi phân quyền: "
			"tạo Role Profile ERPAI-TEST hồ sơ 1 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10), "
			f"tạo User Permission {permission} (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10), "
			"sửa Role Profile ERPAI-TEST hồ sơ 1 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:20), "
			"sửa DocType Note (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:30)",
		)

	def test_permission_record_modified_by_someone_else_does_not_alarm(self):
		frappe.get_doc("User", INSTRUCTOR).add_roles("Desk User")
		self._add_perm("Administrator")
		# Stamped as the agent but with no log row: `modified_by` is not read any more (ADR-024 QĐ 1).
		self._add_perm(AGENT_USER)

		self._run()

		self.send_alarm.assert_not_called()

	def test_window_excludes_watermark_includes_upper_in_creation_order(self):
		for name, at in (
			("at-watermark", WATERMARK),
			("at-upper", UPPER),
			("after-upper", UPPER + timedelta(seconds=1)),
			("inside", WATERMARK + timedelta(seconds=1)),
		):
			self._log_row([_hand_action("api_update_record", "Custom DocPerm", name)], at=at)

		self.assertEqual(
			self._changes(),
			[
				"sửa Custom DocPerm inside (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:00)"
				f"{NO_BEFORE_AFTER}",
				"sửa Custom DocPerm at-upper (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:55)"
				f"{NO_BEFORE_AFTER}",
			],
		)

	def test_job_reads_watermark_and_settled_upper_bound(self):
		with (
			patch.object(tasks, "_privilege_changes_by_agent", return_value=[]) as changes,
			patch.object(tasks, "now_datetime", return_value=RUN_AT),
		):
			tasks.check_privilege_escalation()
			tasks.check_privilege_escalation(now="2031-11-16 09:00:00")

		self.assertEqual(
			[call.args for call in changes.call_args_list],
			[
				(WATERMARK, datetime(2031, 11, 15, 8, 55, 0)),
				(datetime(2031, 11, 15, 8, 55, 0), datetime(2031, 11, 16, 8, 55, 0)),
			],
		)

	def _set_raw_watermark(self, raw):
		"""Leave this raw text in tabSingles (None = no row at all), as a fresh site or an old save may."""
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "privilege_alert_checked_until"})
		if raw is not None:
			frappe.db.sql(
				"insert into `tabSingles` (doctype, field, value) values (%s, %s, %s)",
				(SETTING_DOCTYPE, "privilege_alert_checked_until", raw),
			)

	def test_empty_watermark_reads_from_the_start(self):
		self._log_row(
			[_hand_action("api_update_record", "Custom DocPerm", "a-year-ago")],
			at=datetime(2030, 11, 15, 9, 0, 0),
		)

		# Frappe 15 casts these raw forms to datetime(1, 1, 1) or None: all mean "never alarmed" (design-amd2 §2).
		for raw in (None, "", "0001-01-01 00:00:00"):
			with self.subTest(raw=raw):
				self._set_raw_watermark(raw)

				self.assertIsNone(erp_ai_setting.read_privilege_watermark())
				with patch.object(tasks, "_privilege_changes_by_agent", return_value=[]) as changes:
					self._run()
				changes.assert_called_once_with(None, UPPER)
				self.assertIn(
					"sửa Custom DocPerm a-year-ago (người ra lệnh erpai-tasks-boss@example.invalid, 2030-11-15 09:00)"
					f"{NO_BEFORE_AFTER}",
					self._changes(lower=None),
				)

	def _watermark(self):
		return erp_ai_setting.read_privilege_watermark()

	def _spy_changes(self):
		"""Record the entries the permission condition finds on each job run (the real function still runs)."""
		found = []
		real = tasks._privilege_changes_by_agent

		def spy(lower, upper):
			found.append(real(lower, upper))
			return found[-1]

		self.enterContext(patch.object(tasks, "_privilege_changes_by_agent", side_effect=spy))
		return found

	def _watermark_writes(self):
		"""Every `set_single_value` call on the watermark field, whoever makes it."""
		real = frappe.db.set_single_value
		writes = self.enterContext(patch.object(frappe.db, "set_single_value", wraps=real))
		return lambda: [c for c in writes.call_args_list if c.args[1:2] == ("privilege_alert_checked_until",)]

	def _listed(self, entries, profile):
		return [entry for entry in entries if entry.startswith(f"tạo Role Profile {profile} ")]

	def test_change_alarmed_on_next_run_only(self):
		found = self._spy_changes()
		profile = self._create_profile("T11 sau 1 giờ")
		first, second = SEEDED_AT + timedelta(hours=1), SEEDED_AT + timedelta(hours=25)

		tasks.check_privilege_escalation(now=first)
		self.assertEqual(self._watermark(), first - timedelta(seconds=300))
		self.assertIn(profile, self._permission_alarm())
		self.send_alarm.reset_mock()
		tasks.check_privilege_escalation(now=second)

		self.log_error.assert_not_called()
		self.assertEqual([len(self._listed(entries, profile)) for entries in found], [1, 0])
		self.assertEqual(self._watermark(), second - timedelta(seconds=300))
		self.send_alarm.assert_not_called()

	def test_change_after_two_missed_runs_alarmed_once(self):
		found = self._spy_changes()
		profile = self._create_profile("T11 lỡ hai lần")
		late, next_run = SEEDED_AT + timedelta(hours=49), SEEDED_AT + timedelta(hours=73)

		tasks.check_privilege_escalation(now=late)
		tasks.check_privilege_escalation(now=next_run)

		self.log_error.assert_not_called()
		self.assertEqual([len(self._listed(entries, profile)) for entries in found], [1, 0])
		self.assertEqual(self._watermark(), next_run - timedelta(seconds=300))

	def test_change_before_rollout_alarmed_on_first_run_only(self):
		profile = self._create_profile("T11 trước triển khai", at=datetime(2030, 11, 15, 9, 0, 0))
		self._set_raw_watermark(None)
		found = self._spy_changes()

		self._run()
		self.assertEqual(self._watermark(), UPPER)
		tasks.check_privilege_escalation(now=RUN_AT + timedelta(days=1))

		self.log_error.assert_not_called()
		self.assertEqual([len(self._listed(entries, profile)) for entries in found], [1, 0])
		self.assertEqual(self._watermark(), UPPER + timedelta(days=1))

	def test_change_inside_settle_margin_waits_for_next_run(self):
		found = self._spy_changes()
		at_lower = self._create_profile("T11 bằng mốc", at=WATERMARK)
		at_upper = self._create_profile("T11 bằng cận trên", at=UPPER)
		settling = self._create_profile("T11 đang lắng", at=UPPER + timedelta(seconds=1))
		next_run = RUN_AT + timedelta(days=1)

		self._run()
		tasks.check_privilege_escalation(now=next_run)

		self.log_error.assert_not_called()
		self.assertEqual(
			[[len(self._listed(entries, p)) for p in (at_lower, at_upper, settling)] for entries in found],
			[[0, 1, 0], [0, 0, 1]],
		)
		self.assertEqual(self._watermark(), next_run - timedelta(seconds=300))

	def test_upper_not_after_watermark_keeps_it(self):
		self._create_profile("T11 trước mốc", at=WATERMARK - timedelta(minutes=1))
		watermark_writes = self._watermark_writes()

		for now in (WATERMARK + timedelta(seconds=300), WATERMARK):
			with self.subTest(now=now):
				tasks.check_privilege_escalation(now=now)

				self.log_error.assert_not_called()
				self.send_alarm.assert_not_called()
				self.assertEqual(watermark_writes(), [])
				self.assertEqual(self._watermark(), WATERMARK)

	def test_watermark_written_once_after_all_conditions(self):
		watermark_writes = self._watermark_writes()
		seen_by_last_condition = []

		def last_condition():
			seen_by_last_condition.append(self._watermark())
			return []

		# Take the job's commit branch without committing: the patched commit only records how many
		# watermark writes the transaction holds at that point; the test transaction is rolled back.
		writes_at_commit = []
		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		self.enterContext(
			patch.object(
				frappe.db, "commit", side_effect=lambda: writes_at_commit.append(len(watermark_writes()))
			)
		)

		with patch.object(tasks, "_enabled_keys_without_value", side_effect=last_condition):
			self._run()

		self.assertEqual(seen_by_last_condition, [WATERMARK])
		self.assertEqual(writes_at_commit, [1])
		self.assertEqual(len(watermark_writes()), 1)
		self.assertEqual(self._watermark(), UPPER)

	def test_doctype_write_without_permissions_change_not_listed(self):
		perms = [{"role": "Desk User", "read": 1}]
		self._log_row(
			[
				_hand_action("api_update_record", "DocType", "Note"),
				_hand_action("api_update_record", "DocType", "ToDo"),
			],
			{
				"api_update_record#1": {"name": "Note", "description": "old", "permissions": perms},
				"api_update_record#2": {"name": "ToDo", "description": "old"},
			},
			{
				"api_update_record#1": {"name": "Note", "description": "new", "permissions": perms},
				"api_update_record#2": {"name": "ToDo", "description": "new"},
			},
		)

		self.assertEqual(self._changes(), [])

	def _test_role(self, label):
		name = f"ERPAI-TEST vai {label}"
		if not frappe.db.exists("Role", name):
			frappe.get_doc({"doctype": "Role", "role_name": name, "desk_access": 1}).insert(
				ignore_permissions=True
			)
		return name

	def _user_values(self, *roles):
		return {
			"email": f"erpai-tasks-{frappe.generate_hash(length=8)}@example.invalid",
			"first_name": "ERPAI-TEST",
			"send_welcome_email": 0,
			"roles": [{"role": role} for role in roles],
		}

	def _human_user(self, *roles):
		"""A User given its roles by a person: no ERP AI Log row."""
		return (
			frappe.get_doc({"doctype": "User", **self._user_values(*roles)})
			.insert(ignore_permissions=True)
			.name
		)

	def test_bot_created_user_role_alarm_names_user_role_instructor(self):
		role_a, role_b = self._test_role("A"), self._test_role("B")
		user = self._agent_calls(
			("api_create_record", {"doctype": "User", "values": self._user_values(role_a, role_b)})
		)[0]

		self._run()

		self.assertEqual(
			self._permission_alarm(),
			"Agent đã sửa bản ghi phân quyền: "
			f"thêm role ERPAI-TEST vai A cho {user} "
			"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10), "
			f"thêm role ERPAI-TEST vai B cho {user} "
			"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
		)

	def test_bot_removed_role_listed_as_removed(self):
		kept, removed, added = self._test_role("giữ"), self._test_role("gỡ"), self._test_role("thêm")
		user = self._human_user(kept, removed)
		self._agent_calls(
			(
				"api_update_record",
				{"doctype": "User", "name": user, "values": {"roles": [{"role": kept}, {"role": added}]}},
			)
		)

		self.assertEqual(
			self._changes(),
			[
				f"thêm role ERPAI-TEST vai thêm cho {user} "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
				f"gỡ role ERPAI-TEST vai gỡ của {user} "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
			],
		)

	def test_user_roles_compared_by_name_count_deleted_user_loses_all(self):
		# Rows built by hand: Frappe drops duplicate role rows on save, and deleting a User is out of the seeding.
		self._log_row(
			[
				_hand_action("api_update_record", "User", "dup@example.invalid"),
				_hand_action("api_delete_record", "User", "gone@example.invalid"),
			],
			{
				"api_update_record#1": {
					"name": "dup@example.invalid",
					"roles": [{"role": "A"}, {"role": "A"}, {"role": "A"}, {"role": "B"}],
				},
				"api_delete_record#2": {"name": "gone@example.invalid", "roles": [{"role": "C"}]},
			},
			{
				"api_update_record#1": {
					"name": "dup@example.invalid",
					"roles": [{"role": "B"}, {"role": "A"}, {"role": "B"}, {"role": "B"}],
				},
				# The runner writes the key with None for a delete (runner._record_snapshot).
				"api_delete_record#2": None,
			},
		)

		self.assertEqual(
			self._changes(),
			[
				"thêm role B cho dup@example.invalid "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
				"thêm role B cho dup@example.invalid "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
				"gỡ role A của dup@example.invalid "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
				"gỡ role A của dup@example.invalid "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
				"gỡ role C của gone@example.invalid "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
			],
		)

	def test_bot_resave_user_without_role_change_no_line(self):
		role_a, role_b = self._test_role("A"), self._test_role("B")
		user = self._human_user(role_a, role_b)
		self._agent_calls(
			(
				"api_update_record",
				{
					"doctype": "User",
					"name": user,
					"values": {
						"first_name": "ERPAI-TEST lưu lại",
						"roles": [{"role": role_a}, {"role": role_b}],
					},
				},
			),
			("api_update_record", {"doctype": "User", "name": user, "values": {"last_name": "lần hai"}}),
		)

		self.assertEqual(self._changes(), [])
		self._run()
		self.send_alarm.assert_not_called()

	def test_admin_role_marked_and_listed_first(self):
		# Five ordinary items older than the admin one: by time alone the admin item would be cut by the 5-item limit.
		for minute in range(11, 16):
			self._create_profile(minute, at=datetime(2031, 11, 15, 8, minute, 0))
		user = self._human_user()
		set_agent_settings(unrestricted_enabled=1)
		self._agent_calls(
			(
				"api_update_record",
				{"doctype": "User", "name": user, "values": {"roles": [{"role": "System Manager"}]}},
			),
			at=datetime(2031, 11, 15, 8, 20, 0),
			unrestricted=True,
		)

		self._run()

		self.assertEqual(
			self._permission_alarm(),
			"Agent đã sửa bản ghi phân quyền: "
			f"[QUẢN TRỊ] thêm role System Manager cho {user} "
			"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:20), "
			"tạo Role Profile ERPAI-TEST hồ sơ 11 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:11), "
			"tạo Role Profile ERPAI-TEST hồ sơ 12 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:12), "
			"tạo Role Profile ERPAI-TEST hồ sơ 13 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:13), "
			"tạo Role Profile ERPAI-TEST hồ sơ 14 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:14)"
			" …và 1 mục khác",
		)

	def test_every_forbidden_role_is_marked_when_added_or_removed(self):
		# Rows built by hand: the tools refuse most of these roles, and deleting a User is out of the seeding.
		roles = sorted(site_api.FORBIDDEN_ROLES)
		actions, before, after = [], {}, {}
		for role in roles:
			actions.append(_hand_action("api_update_record", "User", f"add {role}"))
			before[f"api_update_record#{len(actions)}"] = {"name": f"add {role}", "roles": []}
			after[f"api_update_record#{len(actions)}"] = {"name": f"add {role}", "roles": [{"role": role}]}
			actions.append(_hand_action("api_delete_record", "User", f"remove {role}"))
			before[f"api_delete_record#{len(actions)}"] = {
				"name": f"remove {role}",
				"roles": [{"role": role}],
			}
			# The runner writes the key with None for a delete (runner._record_snapshot).
			after[f"api_delete_record#{len(actions)}"] = None
		ordinary = self._test_role("thường")
		actions.append(_hand_action("api_update_record", "User", "ordinary"))
		before[f"api_update_record#{len(actions)}"] = {"name": "ordinary", "roles": []}
		after[f"api_update_record#{len(actions)}"] = {"name": "ordinary", "roles": [{"role": ordinary}]}
		self._log_row(actions, before, after)

		changes = self._changes()

		by = "(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)"
		for role in roles:
			with self.subTest(role=role):
				self.assertIn(f"[QUẢN TRỊ] thêm role {role} cho add {role} {by}", changes)
				self.assertIn(f"[QUẢN TRỊ] gỡ role {role} của remove {role} {by}", changes)
		self.assertEqual(changes[-1], f"thêm role {ordinary} cho ordinary {by}")
		self.assertEqual(len(changes), 2 * len(roles) + 1)

	def test_admin_items_first_each_group_by_time(self):
		# Rows built by hand so one action can add an admin role and an ordinary one. The earlier admin entry
		# ("thêm …") sorts after the later one ("gỡ …") by text, so only the time order passes.
		ordinary_a, ordinary_b = self._test_role("A"), self._test_role("B")
		for at, user, old, new in (
			(datetime(2031, 11, 15, 8, 11, 0), "u1", [], [ordinary_a]),
			(datetime(2031, 11, 15, 8, 12, 0), "u2", [], ["System Manager", ordinary_b]),
			(datetime(2031, 11, 15, 8, 14, 0), "u3", [ROLE_AGENT], []),
		):
			self._log_row(
				[_hand_action("api_update_record", "User", user)],
				{"api_update_record#1": {"name": user, "roles": [{"role": role} for role in old]}},
				{"api_update_record#1": {"name": user, "roles": [{"role": role} for role in new]}},
				at=at,
			)
		self._log_row(
			[_hand_action("api_create_record", "Role Profile", "p")],
			{"api_create_record#1": None},
			{"api_create_record#1": {"name": "p", "roles": []}},
			at=datetime(2031, 11, 15, 8, 13, 0),
		)

		self.assertEqual(
			self._changes(),
			[
				"[QUẢN TRỊ] thêm role System Manager cho u2 "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:12)",
				f"[QUẢN TRỊ] gỡ role {ROLE_AGENT} của u3 "
				"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:14)",
				"thêm role ERPAI-TEST vai A cho u1 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:11)",
				"thêm role ERPAI-TEST vai B cho u2 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:12)",
				"tạo Role Profile p (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:13)",
			],
		)

	def test_only_ok_generic_writes_on_permission_doctypes_are_listed(self):
		perms = [{"role": "Desk User", "read": 1}]
		self._log_row(
			[
				_hand_action("api_update_record", "Custom DocPerm", "refused", ok=False),
				_hand_action("api_update_record", "Has Role", "has-role-row"),
				_hand_action("api_call_method", "Custom DocPerm", "called"),
				_hand_action("api_update_record", "Note", "a-note"),
				_hand_action("api_update_record", "DocType", "ToDo"),
				_hand_action("api_delete_record", "User Permission", "up-1"),
				_hand_action("api_submit_record", "Custom DocPerm", "perm-1"),
				_hand_action("api_create_record", "Role", "ERPAI-TEST role"),
				_hand_action("api_update_record", "DocType", "Note"),
			],
			{
				"api_update_record#5": {"name": "ToDo", "permissions": perms},
				"api_update_record#9": {"name": "Note", "permissions": perms},
			},
			{
				"api_update_record#5": {"name": "ToDo", "permissions": perms},
				"api_update_record#9": {"name": "Note", "permissions": []},
			},
		)

		self.assertEqual(
			self._changes(),
			[
				f"xóa User Permission up-1 {BY}{NO_BEFORE_AFTER}",
				f"submit/hủy Custom DocPerm perm-1 {BY}{NO_BEFORE_AFTER}",
				f"tạo Role ERPAI-TEST role {BY}{NO_BEFORE_AFTER}",
				"sửa DocType Note (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:10)",
			],
		)

	def test_record_action_without_snapshot_listed(self):
		# An old row: no snapshot column at all (written before design-amd2 §2).
		self._log_row(
			[
				_hand_action("api_update_record", "User", "old-user"),
				_hand_action("api_delete_record", "User Permission", "up-old"),
				_hand_action("api_update_record", "DocType", "Note"),
				_hand_action("api_update_record", "Has Role", "has-role-row"),
				_hand_action("api_update_record", "Note", "a-note"),
			],
			at=datetime(2031, 11, 15, 8, 10, 0),
		)
		# A newer row whose snapshots lack some keys, next to keys that are usable.
		self._log_row(
			[
				_hand_action("api_update_record", "User", "after-missing"),
				_hand_action("api_delete_record", "User", "deleted"),
				_hand_action("api_update_record", "User", "unchanged"),
				_hand_action("api_update_record", "Custom DocPerm", "before-missing"),
				_hand_action("api_update_record", "User", "added"),
			],
			{
				"api_update_record#1": {"name": "after-missing", "roles": [{"role": "A"}]},
				"api_delete_record#2": {"name": "deleted", "roles": [{"role": "C"}]},
				"api_update_record#3": {"name": "unchanged", "roles": [{"role": "A"}]},
				"api_update_record#5": {"name": "added", "roles": []},
			},
			{
				# The runner writes the key with None for a delete: that is a usable "after", not a missing one.
				"api_delete_record#2": None,
				"api_update_record#3": {"name": "unchanged", "roles": [{"role": "A"}]},
				"api_update_record#4": {"name": "before-missing", "role": "Desk User"},
				"api_update_record#5": {"name": "added", "roles": [{"role": "A"}]},
			},
			at=datetime(2031, 11, 15, 8, 20, 0),
		)

		by_later = "(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:20)"
		self.assertEqual(
			self._changes(),
			[
				f"sửa User old-user {BY}{NO_BEFORE_AFTER}",
				f"xóa User Permission up-old {BY}{NO_BEFORE_AFTER}",
				f"sửa DocType Note {BY}{NO_BEFORE_AFTER}",
				f"sửa User after-missing {by_later}{NO_BEFORE_AFTER}",
				f"gỡ role C của deleted {by_later}",
				f"sửa Custom DocPerm before-missing {by_later}{NO_BEFORE_AFTER}",
				f"thêm role A cho added {by_later}",
			],
		)

	def test_unusable_snapshot_shapes_listed_without_before_after(self):
		shapes = {
			"broken JSON": ('{"api_update_record#1": {"name": "u", "roles": [', None),
			"column not a dict": ('["api_update_record#1"]', None),
			"snapshot not a dict": ({"api_update_record#1": "u"}, None),
			"roles not a list": ({"api_update_record#1": {"name": "u", "roles": "System Manager"}}, None),
			"roles an empty object": ({"api_update_record#1": {"name": "u", "roles": {}}}, None),
			"role row not a dict": (
				{"api_update_record#1": {"name": "u", "roles": ["System Manager"]}},
				None,
			),
			"roles missing": ({"api_update_record#1": {"name": "u"}}, None),
			"both sides None": ({"api_update_record#1": None}, {"api_update_record#1": None}),
		}
		usable_after = {"api_update_record#1": {"name": "u", "roles": [{"role": "A"}]}}
		# One row per shape, each alone in its own one-minute window.
		at = SEEDED_AT
		for shape, (before, after) in shapes.items():
			at += timedelta(minutes=1)
			with self.subTest(shape=shape):
				self._log_row(
					[_hand_action("api_update_record", "User", "u")], before, after or usable_after, at=at
				)

				self.assertEqual(
					self._changes(at - timedelta(seconds=1), at),
					[
						f"sửa User u (người ra lệnh erpai-tasks-boss@example.invalid, {at:%Y-%m-%d %H:%M}){NO_BEFORE_AFTER}"
					],
				)

		for shape, actions in (
			("broken JSON", '[{"tool": "api_update_record", "doctype": "User", "name": "cut'),
			("not a list", '{"tool": "api_update_record", "doctype": "User", "name": "u", "ok": true}'),
			("entry not a dict", '["api_update_record"]'),
		):
			at += timedelta(minutes=1)
			with self.subTest(actions=shape):
				name = self._log_row(actions, at=at)

				self.assertEqual(
					self._changes(at - timedelta(seconds=1), at), [f"ERP AI Log {name}{NO_BEFORE_AFTER}"]
				)

	def test_unusable_after_snapshot_shapes_listed_without_before_after(self):
		# The `after` side is unusable while `before` is fine (mirror of the test above).
		usable = {"api_update_record#1": {"name": "u", "roles": [{"role": "A"}]}}
		shapes = {
			"broken JSON": '{"api_update_record#1": {"name": "u", "roles": [',
			"column not a dict": '["api_update_record#1"]',
			"snapshot not a dict": {"api_update_record#1": "u"},
			"roles not a list": {"api_update_record#1": {"name": "u", "roles": "System Manager"}},
			"roles an empty object": {"api_update_record#1": {"name": "u", "roles": {}}},
			"role row not a dict": {"api_update_record#1": {"name": "u", "roles": ["System Manager"]}},
			"roles missing": {"api_update_record#1": {"name": "u"}},
		}
		cases = [(shape, usable, bad) for shape, bad in shapes.items()]
		# A role row that is a dict without a `role` name, on each side.
		no_role_name = {"api_update_record#1": {"name": "u", "roles": [{"idx": 1}]}}
		cases += [("role row without role, before", no_role_name, usable)]
		cases += [("role row without role, after", usable, no_role_name)]
		at = SEEDED_AT
		for shape, before, after in cases:
			at += timedelta(minutes=1)
			with self.subTest(shape=shape):
				self._log_row([_hand_action("api_update_record", "User", "u")], before, after, at=at)

				self.assertEqual(
					self._changes(at - timedelta(seconds=1), at),
					[
						f"sửa User u (người ra lệnh erpai-tasks-boss@example.invalid, {at:%Y-%m-%d %H:%M}){NO_BEFORE_AFTER}"
					],
				)

	def test_unusable_permission_snapshot_listed_without_before_after(self):
		usable = {
			"Custom DocPerm": {"name": "perm-1", "role": "Desk User", "read": 1},
			"DocType": {"name": "Note", "permissions": [{"role": "Desk User", "read": 1}]},
		}
		at = SEEDED_AT
		for doctype, name in (("Custom DocPerm", "perm-1"), ("DocType", "Note")):
			for shape, before, after in (
				("before a str", name, usable[doctype]),
				("after a str", usable[doctype], name),
				("both sides None", None, None),
			):
				at += timedelta(minutes=1)
				with self.subTest(doctype=doctype, shape=shape):
					self._log_row(
						[_hand_action("api_update_record", doctype, name)],
						{"api_update_record#1": before},
						{"api_update_record#1": after},
						at=at,
					)

					self.assertEqual(
						self._changes(at - timedelta(seconds=1), at),
						[
							f"sửa {doctype} {name} (người ra lệnh erpai-tasks-boss@example.invalid, "
							f"{at:%Y-%m-%d %H:%M}){NO_BEFORE_AFTER}"
						],
					)

	def test_broken_snapshot_json_listed_without_before_after(self):
		role = self._test_role("thường")
		self._log_row(
			[_hand_action("api_update_record", "User", "broken@example.invalid")],
			'{"api_update_record#1": {"name": "broken@example.invalid", "roles": [{"role": "Sys',
			{"api_update_record#1": {"name": "broken@example.invalid", "roles": []}},
			at=datetime(2031, 11, 15, 8, 10, 0),
		)
		broken_actions = self._log_row(
			'[{"tool": "api_update_record", "doctype": "User", "name": "cut@example.invalid", "ok": tr',
			at=datetime(2031, 11, 15, 8, 20, 0),
		)
		# A broken `value_after` column next to a usable `value_before` one.
		self._log_row(
			[_hand_action("api_update_record", "User", "broken-after@example.invalid")],
			{"api_update_record#1": {"name": "broken-after@example.invalid", "roles": []}},
			'{"api_update_record#1": {"name": "broken-after@example.invalid", "roles": [{"role": "Sys',
			at=datetime(2031, 11, 15, 8, 25, 0),
		)
		# A neighbouring row with usable snapshots still gives its normal entry.
		self._log_row(
			[_hand_action("api_update_record", "User", "fine@example.invalid")],
			{"api_update_record#1": {"name": "fine@example.invalid", "roles": []}},
			{"api_update_record#1": {"name": "fine@example.invalid", "roles": [{"role": role}]}},
			at=datetime(2031, 11, 15, 8, 30, 0),
		)
		self._add_role("System Manager")
		script = self._add_server_script(AGENT_USER, disabled=0)
		label = self._add_empty_key()

		self._run()

		self.assertEqual(
			self._permission_alarm(),
			"Agent đã sửa bản ghi phân quyền: "
			f"sửa User broken@example.invalid {BY}{NO_BEFORE_AFTER}, "
			f"ERP AI Log {broken_actions}{NO_BEFORE_AFTER}, "
			"sửa User broken-after@example.invalid "
			f"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:25){NO_BEFORE_AFTER}, "
			f"thêm role {role} cho fine@example.invalid "
			"(người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:30)",
		)
		messages = self._alarm_messages()
		self.assertEqual(len(messages), 4, messages)
		self.assertTrue(
			any(m.startswith("Tài khoản agent có role") and "System Manager" in m for m in messages)
		)
		self.assertTrue(any(m.startswith("Server Script/Webhook") and script in m for m in messages))
		self.assertTrue(any(m.startswith("Khóa đang bật") and label in m for m in messages))
		self.assertEqual(self._watermark(), UPPER)

	def test_fake_key_never_in_privilege_alarm(self):
		secret_user = {"name": "secret@example.invalid", "api_key": FAKE_KEY, "roles": []}
		self._log_row(
			[
				_hand_action("api_update_record", "User", "secret@example.invalid"),
				_hand_action("api_update_record", "User Permission", "up-secret"),
				_hand_action("api_update_record", "DocType", "Note"),
				_hand_action("api_update_record", "User", "broken@example.invalid"),
			],
			{
				"api_update_record#1": secret_user,
				"api_update_record#2": {"name": "up-secret", "for_value": FAKE_KEY},
				"api_update_record#3": {"name": "Note", "permissions": [{"role": FAKE_KEY}]},
				"api_update_record#4": {"name": "broken@example.invalid", "roles": FAKE_KEY},
			},
			{
				"api_update_record#1": {**secret_user, "roles": [{"role": self._test_role("A")}]},
				"api_update_record#2": {"name": "up-secret", "for_value": FAKE_KEY},
				"api_update_record#3": {"name": "Note", "permissions": []},
				"api_update_record#4": {"name": "broken@example.invalid", "roles": FAKE_KEY},
			},
		)

		self._run()

		message = self._permission_alarm()
		self.assertIn("sửa User broken@example.invalid", message)
		self.assertEqual(sum(m.count(FAKE_KEY) for m in self._alarm_messages()), 0)
		self.assertEqual(sum(m.count("sk-") for m in self._alarm_messages()), 0)

	def test_empty_instructor_is_named_unknown(self):
		self._log_row([_hand_action("api_update_record", "Custom DocPerm", "x")], instructor=None)

		self.assertEqual(
			self._changes(),
			["sửa Custom DocPerm x (người ra lệnh không rõ, 2031-11-15 08:10)" + NO_BEFORE_AFTER],
		)

	def test_only_reason_rows_are_read(self):
		for entry_type in ("classify", "skip"):
			self._log_row([_hand_action("api_update_record", "Custom DocPerm", "x")], entry_type=entry_type)

		self.assertEqual(self._changes(), [])

	def test_setup_neutralizes_live_rows_attributed_to_agent(self):
		self._add_perm(AGENT_USER)
		self._add_server_script(AGENT_USER, disabled=0)
		self._add_webhook(AGENT_USER, enabled=1)

		self._neutralize_agent_rows()
		self._run()

		self.send_alarm.assert_not_called()

	def test_alarm_on_enabled_server_script_or_webhook_by_agent(self):
		script = self._add_server_script(AGENT_USER, disabled=0)
		hook = self._add_webhook(AGENT_USER, enabled=1)

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		message = self._alarm_messages()[0]
		self.assertIn(script, message)
		self.assertIn(hook, message)

	def test_disabled_or_foreign_server_script_and_webhook_do_not_alarm(self):
		self._add_server_script(AGENT_USER, disabled=1)
		self._add_server_script("Administrator", disabled=0)
		self._add_webhook(AGENT_USER, enabled=0)
		self._add_webhook("Administrator", enabled=1)

		self._run()

		self.send_alarm.assert_not_called()

	def test_alarm_on_enabled_key_without_secret(self):
		label = self._add_empty_key()

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn(label, self._alarm_messages()[0])

	def test_key_with_value_or_disabled_key_does_not_alarm(self):
		add_credential(f"ERPAI-TEST-{frappe.generate_hash(length=8)}", enabled=1)
		self._add_empty_key(enabled=0)

		self._run()

		self.send_alarm.assert_not_called()

	def test_message_never_contains_key_text(self):
		self._add_empty_key()
		add_credential(f"ERPAI-TEST-{frappe.generate_hash(length=8)}", enabled=1)

		self._run()

		self.assertNotIn("sk-", self._alarm_messages()[0])

	def test_listed_keys_are_never_decrypted(self):
		self._add_empty_key()
		add_credential(f"ERPAI-TEST-{frappe.generate_hash(length=8)}", enabled=1)

		with (
			patch("frappe.utils.password.get_decrypted_password", side_effect=AssertionError("decrypt")),
			patch("frappe.model.document.Document.get_password", side_effect=AssertionError("decrypt")),
		):
			self._run()

		self.assertEqual(self.send_alarm.call_count, 1)

	def test_one_alarm_per_condition(self):
		self._create_profile(1)
		self._add_role("System Manager")
		self._add_server_script(AGENT_USER, disabled=0)
		self._add_empty_key()

		self._run()

		self.assertEqual(self.send_alarm.call_count, 4)

	def test_lists_at_most_five_names(self):
		# Seeded newest first: the alarm still lists by `creation` ascending.
		for minute in range(17, 10, -1):
			self._create_profile(minute, at=datetime(2031, 11, 15, 8, minute, 0))

		self._run()

		self.assertEqual(
			self._permission_alarm(),
			"Agent đã sửa bản ghi phân quyền: "
			"tạo Role Profile ERPAI-TEST hồ sơ 11 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:11), "
			"tạo Role Profile ERPAI-TEST hồ sơ 12 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:12), "
			"tạo Role Profile ERPAI-TEST hồ sơ 13 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:13), "
			"tạo Role Profile ERPAI-TEST hồ sơ 14 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:14), "
			"tạo Role Profile ERPAI-TEST hồ sơ 15 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:15)"
			" …và 2 mục khác",
		)

	def test_five_names_have_no_overflow_text(self):
		for minute in range(11, 16):
			self._create_profile(minute, at=datetime(2031, 11, 15, 8, minute, 0))

		self._run()

		self.assertEqual(
			self._permission_alarm(),
			"Agent đã sửa bản ghi phân quyền: "
			"tạo Role Profile ERPAI-TEST hồ sơ 11 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:11), "
			"tạo Role Profile ERPAI-TEST hồ sơ 12 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:12), "
			"tạo Role Profile ERPAI-TEST hồ sơ 13 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:13), "
			"tạo Role Profile ERPAI-TEST hồ sơ 14 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:14), "
			"tạo Role Profile ERPAI-TEST hồ sơ 15 (người ra lệnh erpai-tasks-boss@example.invalid, 2031-11-15 08:15)",
		)

	def test_error_is_logged_and_rolled_back_not_raised(self):
		frappe.db.savepoint("t34_before_job")
		real_rollback = frappe.db.rollback

		def rollback_to_savepoint(*args, **kwargs):
			real_rollback(save_point="t34_before_job")

		with (
			patch("frappe.get_all", side_effect=frappe.QueryTimeoutError("boom")),
			patch.object(frappe.db, "rollback", side_effect=rollback_to_savepoint) as rollback,
		):
			tasks.check_privilege_escalation()

		rollback.assert_called_once()
		self.log_error.assert_called_once_with(
			TITLE_RUN_FAILED, "check_privilege_escalation error=QueryTimeoutError"
		)
		self.send_alarm.assert_not_called()

	def test_email_failure_keeps_alarm_logs_failure_and_continues(self):
		self.send_alarm_patch.stop()
		set_agent_settings(alert_recipients="erpai-test@example.invalid")
		self._create_profile(1)
		self._add_role("System Manager")
		self._add_empty_key()

		with (
			patch("frappe.sendmail", side_effect=frappe.OutgoingEmailError("no account")) as sendmail,
			patch.object(frappe.db, "rollback") as rollback,
		):
			tasks.check_privilege_escalation(now=RUN_AT)

		rollback.assert_not_called()
		self.assertEqual(sendmail.call_count, 3)
		titles = [call.args[0] for call in self.log_error.call_args_list]
		self.assertEqual(titles.count(TITLE_ALARM), 3)
		self.assertEqual(titles.count(TITLE_RUN_FAILED), 3)
		self.log_error.assert_any_call(
			TITLE_RUN_FAILED, "check_privilege_escalation email error=OutgoingEmailError"
		)


class TestReprobeExhaustedKeys(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.log_error = self.enterContext(patch("frappe.log_error"))
		self.notice = self.enterContext(patch("erp_ai.alerts.send_notice"))
		self.alarm = self.enterContext(patch("erp_ai.alerts.send_alarm"))
		# Keys already on the site must not be probed.
		frappe.db.set_value(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE}, "enabled", 0)
		set_agent_settings(model_classify_default="ERPAI-TEST-model")
		self.exhausted_label = self._label()
		self.exhausted = add_credential(self.exhausted_label, status=KEY_STATUS_QUOTA_EXHAUSTED)
		self.bad = add_credential(self._label(), status=KEY_STATUS_BAD_KEY)
		self.active = add_credential(self._label(), status=KEY_STATUS_ACTIVE)

	def _label(self):
		return f"ERPAI-TEST-{frappe.generate_hash(length=8)}"

	def _status(self, row):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, row, "status")

	def _run_recovering(self):
		keys_sent = []

		def send(api_key, *, timeout, request):
			keys_sent.append(api_key)
			return client.RawReply(message={"type": "message", "content": []}, headers={}, request_id="r")

		with patch.object(client, "send", send):
			tasks.reprobe_exhausted_keys()
		return keys_sent

	def test_reprobe_only_exhausted_keys(self):
		keys_sent = self._run_recovering()

		self.assertEqual(keys_sent, [f"sk-{self.exhausted_label}"])
		self.assertEqual(self._status(self.exhausted), KEY_STATUS_ACTIVE)
		self.assertEqual(self._status(self.bad), KEY_STATUS_BAD_KEY)
		self.assertEqual(self._status(self.active), KEY_STATUS_ACTIVE)
		self.log_error.assert_not_called()

	def test_recovered_key_sends_exactly_one_notice(self):
		self._run_recovering()

		self.assertEqual(self.notice.call_count, 1)

	def test_still_exhausted_key_sends_no_notice(self):
		failed = [{"label": "x", "ok": False, "error_kind": "quota", "status": 402}]
		with patch("erp_ai.gateway.reprobe_exhausted_keys", return_value=failed):
			tasks.reprobe_exhausted_keys()

		self.notice.assert_not_called()
		self.log_error.assert_not_called()

	def test_gateway_error_is_logged_and_rolled_back_not_raised(self):
		frappe.db.savepoint("t35_before_job")
		real_rollback = frappe.db.rollback

		def rollback_to_savepoint(*args, **kwargs):
			real_rollback(save_point="t35_before_job")

		with (
			patch("erp_ai.gateway.reprobe_exhausted_keys", side_effect=frappe.QueryTimeoutError("boom")),
			patch.object(frappe.db, "rollback", side_effect=rollback_to_savepoint) as rollback,
		):
			tasks.reprobe_exhausted_keys()

		rollback.assert_called_once()
		self.log_error.assert_called_once_with(
			TITLE_RUN_FAILED, "reprobe_exhausted_keys error=QueryTimeoutError"
		)

	def test_hooks_register_hourly_and_daily_order(self):
		self.assertEqual(hooks.scheduler_events["hourly"], ["erp_ai.tasks.reprobe_exhausted_keys"])
		self.assertEqual(
			hooks.scheduler_events["daily"],
			["erp_ai.tasks.recompute_monthly_spend", "erp_ai.tasks.check_privilege_escalation"],
		)
