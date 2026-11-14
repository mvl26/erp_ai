from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.desk.query_report import run as run_report
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import LOG_DOCTYPE, ROLE_AGENT, ROLE_INSTRUCTOR, SETTING_DOCTYPE
from erp_ai.erp_ai_agent.report.erp_ai_cost.erp_ai_cost import execute
from erp_ai.tasks import recompute_monthly_spend
from erp_ai.test_utils import keep_agent_settings, make_log_entry, set_agent_settings

PREFIX = "ERPAI-TEST-COST-"
REPORT = "ERP AI Cost"
BY_TICKET = "Phiếu"
BY_RUN = "Lần chạy"
NO_TICKET = "(không gắn phiếu)"
# A month no other test writes log rows into, so the rows made here are the only ones in it.
NOW = datetime(2031, 3, 20, 10, 0, 0)
FROM_DATE = date(2031, 3, 5)
TO_DATE = date(2031, 3, 10)
RUN_DAYS = (5, 7, 8, 10)
SIX_PLACES = Decimal("0.000001")
INSTRUCTOR_USER = "erp-ai-cost-instructor@example.com"
AGENT_ONLY_USER = "erp-ai-cost-agent@example.com"
SYSTEM_MANAGER_USER = "erp-ai-cost-sysmanager@example.com"


def _ticket(number):
	return f"{PREFIX}T{number}"


def _run(number, run_index):
	return f"{PREFIX}T{number}-R{run_index}"


def _cost(ticket_number, run_index, row_index):
	return (
		ticket_number * Decimal("0.100001")
		+ run_index * Decimal("0.010203")
		+ row_index * Decimal("0.000007")
	)


def _six(value):
	"""A cost as an exact Decimal at 6 places, so equality means "error 0 at 6 decimals"."""
	return Decimal(str(value)).quantize(SIX_PLACES)


def _make_user(email, role):
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


class TestCost(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# ERP AI Log cannot be deleted: every row made here is undone by the rollback.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		keep_agent_settings(self)
		frappe.set_user("Administrator")
		self.rows = []

	def _log(self, run_id, ticket, creation, cost):
		name = make_log_entry(run_id=run_id, entry_type="reason", cost_usd=cost)
		frappe.db.set_value(
			LOG_DOCTYPE, name, {"ticket": ticket, "creation": creation}, update_modified=False
		)
		self.rows.append({"run_id": run_id, "ticket": ticket, "creation": creation, "cost": Decimal(cost)})

	def _make_sample(self):
		"""3 tickets x 4 runs x 2 rows inside the range, two runs without a ticket, and decoys around both
		ends of the range and of the month."""
		for number in (1, 2, 3):
			for run_index, day in enumerate(RUN_DAYS):
				for row_index in (0, 1):
					creation = datetime(2031, 3, day, number, row_index)
					if (number, run_index, row_index) == (1, 0, 0):
						creation = datetime(2031, 3, 5, 0, 0, 0)  # first second of from_date
					if (number, run_index, row_index) == (3, 3, 1):
						creation = datetime(2031, 3, 10, 23, 59, 59)  # last second of to_date
					self._log(
						_run(number, run_index),
						_ticket(number),
						creation,
						_cost(number, run_index, row_index),
					)
		self._log(f"{PREFIX}NULL", None, datetime(2031, 3, 9, 12, 0), Decimal("0.000001"))
		self._log(f"{PREFIX}EMPTY", "", datetime(2031, 3, 6, 12, 0), Decimal("0.000004"))
		# Decoys in the month but outside the range: one in a run that is inside the range (its total and
		# start must not move), one more in another run of a ticket.
		self._log(_run(1, 0), _ticket(1), datetime(2031, 3, 4, 23, 59, 59), Decimal("5"))
		self._log(_run(2, 3), _ticket(2), datetime(2031, 3, 11, 0, 0, 0), Decimal("7"))
		# First and last second of the month: in the month total, not in the range.
		self._log(_run(2, 8), _ticket(2), datetime(2031, 3, 1, 0, 0, 0), Decimal("0.000002"))
		self._log(_run(2, 9), _ticket(2), datetime(2031, 3, 31, 23, 59, 59), Decimal("0.000003"))
		# Outside the month on both sides.
		self._log(_run(3, 8), _ticket(3), datetime(2031, 2, 28, 23, 59, 59), Decimal("11"))
		self._log(_run(3, 9), _ticket(3), datetime(2031, 4, 1, 0, 0, 0), Decimal("13"))

	def _filters(self, group_by=BY_TICKET, **overrides):
		return {"from_date": FROM_DATE, "to_date": TO_DATE, "group_by": group_by, **overrides}

	def _in_range(self):
		start, end = datetime(2031, 3, 5), datetime(2031, 3, 11)
		return [row for row in self.rows if start <= row["creation"] < end]

	def _summary(self, filters=None):
		_, _, _, _, summary = execute(filters or self._filters(), now=NOW)
		return {item["label"]: item["value"] for item in summary}

	def test_per_ticket_and_run_totals(self):
		self._make_sample()

		columns, data, *_ = execute(self._filters(), now=NOW)
		self.assertEqual([column["fieldname"] for column in columns], ["ticket", "runs", "cost_usd"])
		cost_column = next(column for column in columns if column["fieldname"] == "cost_usd")
		self.assertEqual((cost_column["fieldtype"], cost_column["precision"]), ("Float", 6))
		# Hand-computed: ticket n has 8 rows: 8 * n * 0.100001 + 2 * (0+1+2+3) * 0.010203 + 4 * 0.000007.
		self.assertEqual(
			[(row["ticket"], row["runs"], _six(row["cost_usd"])) for row in data],
			[
				(_ticket(1), 4, Decimal("0.922472")),
				(_ticket(2), 4, Decimal("1.722480")),
				(_ticket(3), 4, Decimal("2.522488")),
				(NO_TICKET, 2, Decimal("0.000005")),
			],
		)
		# Each ticket total equals the sum of its log rows in the range.
		for row in data[:3]:
			expected = sum(r["cost"] for r in self._in_range() if r["ticket"] == row["ticket"])
			self.assertEqual(_six(row["cost_usd"]), _six(expected))

		columns, data, *_ = execute(self._filters(BY_RUN), now=NOW)
		self.assertEqual(
			[column["fieldname"] for column in columns], ["run_id", "ticket", "started_at", "cost_usd"]
		)
		expected_runs = {}
		for row in self._in_range():
			run = expected_runs.setdefault(
				row["run_id"],
				{"ticket": row["ticket"] or NO_TICKET, "started_at": row["creation"], "cost": Decimal(0)},
			)
			run["started_at"] = min(run["started_at"], row["creation"])
			run["cost"] += row["cost"]
		self.assertEqual(len(expected_runs), 14)
		ordered = sorted(expected_runs.items(), key=lambda item: (item[1]["started_at"], item[0]))
		self.assertEqual(
			[(row["run_id"], row["ticket"], row["started_at"], _six(row["cost_usd"])) for row in data],
			[(run_id, run["ticket"], run["started_at"], _six(run["cost"])) for run_id, run in ordered],
		)
		first = data[0]
		# The decoy one second before the range in the same run moves neither its start nor its total.
		self.assertEqual(
			(first["run_id"], first["started_at"], _six(first["cost_usd"])),
			(_run(1, 0), datetime(2031, 3, 5, 0, 0, 0), Decimal("0.200009")),
		)

		summary = self._summary()
		self.assertEqual(_six(summary["Tổng trong khoảng"]), Decimal("5.167445"))
		self.assertEqual(_six(sum(run["cost"] for run in expected_runs.values())), Decimal("5.167445"))

	def test_month_total_matches_spent(self):
		self._make_sample()
		# Before the daily job the summary shows the stored spend as it is, not the log total.
		set_agent_settings(spent_this_month_usd=1.234567)
		stale = self._summary()
		self.assertEqual(_six(stale["Đã chi tháng này (Setting)"]), Decimal("1.234567"))
		self.assertEqual(_six(stale["Tổng tháng này (ERP AI Log)"]), Decimal("17.167450"))

		recompute_monthly_spend(now=NOW)
		spent = frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")

		summary = self._summary()
		# Range 5.167445 + decoys in March 5 + 7 + 0.000002 + 0.000003; February and April rows excluded.
		self.assertEqual(_six(summary["Tổng tháng này (ERP AI Log)"]), Decimal("17.167450"))
		self.assertEqual(_six(summary["Đã chi tháng này (Setting)"]), _six(spent))
		self.assertEqual(_six(summary["Tổng tháng này (ERP AI Log)"]), _six(spent))
		# The month of `now`, not of the range: a range in another month keeps the same month total.
		other_month = self._summary(self._filters(from_date=date(2031, 4, 1), to_date=date(2031, 4, 1)))
		self.assertEqual(_six(other_month["Tổng tháng này (ERP AI Log)"]), Decimal("17.167450"))
		self.assertEqual(_six(other_month["Tổng trong khoảng"]), Decimal("13.000000"))

	def test_single_day_range_and_empty_range(self):
		self._make_sample()
		_, data, *_ = execute(self._filters(from_date=TO_DATE, to_date=TO_DATE), now=NOW)
		self.assertEqual(
			[(row["ticket"], row["runs"], _six(row["cost_usd"])) for row in data],
			[
				(_ticket(1), 1, _six(_cost(1, 3, 0) + _cost(1, 3, 1))),
				(_ticket(2), 1, _six(_cost(2, 3, 0) + _cost(2, 3, 1))),
				(_ticket(3), 1, _six(_cost(3, 3, 0) + _cost(3, 3, 1))),
			],
		)
		_, data, *_ = execute(self._filters(from_date=date(2031, 6, 1), to_date=date(2031, 6, 30)), now=NOW)
		self.assertEqual(data, [])

	def test_filters_are_validated(self):
		bad_filters = (
			{},
			{"to_date": TO_DATE, "group_by": BY_TICKET},
			{"from_date": FROM_DATE, "group_by": BY_TICKET},
			self._filters(from_date=TO_DATE, to_date=FROM_DATE),
			self._filters(group_by=None),
			self._filters(group_by="Tháng"),
		)
		for filters in bad_filters:
			with self.subTest(filters=filters), self.assertRaises(frappe.ValidationError):
				execute(filters, now=NOW)

	def test_access_three_accounts(self):
		self._make_sample()
		report = frappe.get_doc("Report", REPORT)
		self.assertEqual(
			(report.report_type, report.ref_doctype, report.is_standard, report.module),
			("Script Report", LOG_DOCTYPE, "Yes", "ERP AI agent"),
		)
		self.assertEqual(sorted(row.role for row in report.roles), ["ERP AI Instructor", "System Manager"])
		filters = self._filters()

		frappe.set_user(_make_user(INSTRUCTOR_USER, ROLE_INSTRUCTOR))
		self.assertNotIn("System Manager", frappe.get_roles())
		result = run_report(REPORT, filters=filters)
		self.assertEqual(len(result["result"]), 4)

		frappe.set_user(_make_user(AGENT_ONLY_USER, ROLE_AGENT))
		self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles())
		with self.assertRaises(frappe.PermissionError):
			run_report(REPORT, filters=filters)
		with self.assertRaises(frappe.PermissionError):
			execute(filters, now=NOW)

		frappe.set_user(_make_user(SYSTEM_MANAGER_USER, "System Manager"))
		self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles())
		result = run_report(REPORT, filters=filters)
		self.assertEqual(len(result["result"]), 4)
