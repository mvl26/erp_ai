from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import hooks, tasks
from erp_ai.constants import (
	AGENT_USER,
	CREDENTIAL_DOCTYPE,
	HELPDESK_AGENT_ROLE,
	LOG_DOCTYPE,
	ROLE_AGENT,
	SETTING_DOCTYPE,
	TITLE_ALARM,
	TITLE_RUN_FAILED,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import add_credential, set_agent_settings

# Far-future months cannot hold real ERP AI Log rows, so sums only see rows the test inserts.
NOW = datetime(2031, 11, 15, 8, 0, 0)
THIS_MONTH = datetime(2031, 11, 3, 9, 0, 0)
LAST_MONTH = datetime(2031, 10, 31, 23, 59, 59)
FIRST_OF_MONTH = datetime(2031, 11, 1, 0, 0, 0)
NEXT_MONTH = datetime(2031, 12, 1, 0, 0, 0)


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

	def _run(self):
		tasks.check_privilege_escalation()
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
		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
			if not frappe.db.exists("Has Role", {"parent": AGENT_USER, "role": role}):
				self._add_role(role)

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
		for role in (ROLE_AGENT, HELPDESK_AGENT_ROLE):
			if not frappe.db.exists("Has Role", {"parent": AGENT_USER, "role": role}):
				self._add_role(role)
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "role": ROLE_AGENT})

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn(ROLE_AGENT, self._alarm_messages()[0])

	def test_alarm_on_permission_records_modified_by_agent(self):
		name = self._add_perm(AGENT_USER)

		self._run()

		self.assertEqual(self.send_alarm.call_count, 1)
		self.assertIn(name, self._alarm_messages()[0])

	def test_permission_record_modified_by_someone_else_does_not_alarm(self):
		self._add_perm("Administrator")

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
		self._add_role("System Manager")
		self._add_perm(AGENT_USER)
		self._add_server_script(AGENT_USER, disabled=0)
		self._add_empty_key()

		self._run()

		self.assertEqual(self.send_alarm.call_count, 4)

	def test_lists_at_most_five_names(self):
		names = [self._add_perm(AGENT_USER) for _ in range(7)]

		self._run()

		message = self._alarm_messages()[0]
		self.assertEqual(sum(name in message for name in names), 5)
		self.assertIn("…và 2 mục khác", message)

	def test_five_names_have_no_overflow_text(self):
		for _ in range(5):
			self._add_perm(AGENT_USER)

		self._run()

		self.assertNotIn("mục khác", self._alarm_messages()[0])

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
		self._add_role("System Manager")
		self._add_perm(AGENT_USER)
		self._add_empty_key()

		with (
			patch("frappe.sendmail", side_effect=frappe.OutgoingEmailError("no account")) as sendmail,
			patch.object(frappe.db, "rollback") as rollback,
		):
			tasks.check_privilege_escalation()

		rollback.assert_not_called()
		self.assertEqual(sendmail.call_count, 3)
		titles = [call.args[0] for call in self.log_error.call_args_list]
		self.assertEqual(titles.count(TITLE_ALARM), 3)
		self.assertEqual(titles.count(TITLE_RUN_FAILED), 3)
		self.log_error.assert_any_call(
			TITLE_RUN_FAILED, "check_privilege_escalation email error=OutgoingEmailError"
		)
