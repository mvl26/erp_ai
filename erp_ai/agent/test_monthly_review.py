import json
from datetime import date, datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import monthly_review
from erp_ai.constants import LOG_DOCTYPE
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

REVIEW_MONTH = "ERP AI Review Month"
# Months long before any real log row on the shared site.
MONTH = "2001-02"
IN_MONTH = datetime(2001, 2, 14, 10, 0)
NOW = datetime(2001, 3, 1, 8, 0)
REVIEWERS = "erpai-review-a@example.com\n  erpai-review-b@example.com  \n\n"


def _tickets(count: int) -> list[str]:
	return [make_ticket(subject=f"ERPAI-TEST review {n}").name for n in range(count)]


def _log(ticket: str, creation: datetime = IN_MONTH, entry_type="reason", actions=None, applied=0) -> None:
	row = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"ticket": ticket,
			"run_id": "ERPAI-TEST-run",
			"entry_type": entry_type,
			"trigger": "ticket_insert",
			"turn": 1,
			"applied": applied,
			"actions": json.dumps(actions or []),
		}
	)
	row.db_insert()
	frappe.db.set_value(LOG_DOCTYPE, row.name, "creation", creation, update_modified=False)


def _ok_action(ticket: str, ok: bool = True) -> dict:
	return {"tool": "post_comment", "doctype": "Comment", "name": "x", "ok": ok, "ticket": ticket}


def _bot_touched(tickets: list[str]) -> None:
	for ticket in tickets:
		_log(ticket, actions=[_ok_action(ticket)])


class MonthlyReviewTestCase(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)
		set_agent_settings(review_sample_size=10, monthly_reviewers="")
		# The shared site may hold real rows: this class sees only its own.
		frappe.db.delete(REVIEW_MONTH)
		frappe.db.delete(LOG_DOCTYPE, {"creation": ["between", ["2001-01-01", "2001-12-31"]]})


class TestPick(FrappeTestCase):
	def test_pure_sample_is_fixed_by_the_month(self):
		names = [f"T{n:03d}" for n in range(25)]
		first = monthly_review.pick_sample(names, MONTH, 10)
		self.assertEqual(len(first), 10)
		self.assertEqual(len(set(first)), 10)
		self.assertTrue(set(first) <= set(names))
		self.assertEqual(monthly_review.pick_sample(names, MONTH, 10), first)
		self.assertNotEqual(monthly_review.pick_sample(names, "2001-03", 10), first)
		self.assertEqual(sorted(monthly_review.pick_sample(names[:6], MONTH, 10)), names[:6])
		self.assertEqual(monthly_review.pick_sample([], MONTH, 10), [])


class TestReview(MonthlyReviewTestCase):
	def _items(self) -> list[str]:
		return frappe.get_all(
			"ERP AI Review Item", filters={"parent": f"REV-{MONTH}"}, order_by="idx", pluck="ticket"
		)

	def test_25_gives_10_unique(self):
		tickets = _tickets(25)
		_bot_touched(tickets)
		monthly_review.run_monthly_review(now=NOW)

		doc = frappe.get_doc(REVIEW_MONTH, f"REV-{MONTH}")
		self.assertEqual((doc.period_start, doc.period_end), (date(2001, 2, 1), date(2001, 2, 28)))
		self.assertEqual(doc.candidate_count, 25)
		items = self._items()
		self.assertEqual(len(items), 10)
		self.assertEqual(len(set(items)), 10)
		self.assertTrue(set(items) <= set(tickets))

	def test_6_gives_6(self):
		tickets = _tickets(6)
		_bot_touched(tickets)
		monthly_review.run_monthly_review(now=NOW)
		self.assertEqual(sorted(self._items()), sorted(tickets))

	def test_rerun_same_set(self):
		tickets = _tickets(12)
		_bot_touched(tickets)
		monthly_review.run_monthly_review(now=NOW)
		first = self._items()
		# A later run in the same cycle, even with more candidates, leaves the row alone.
		_bot_touched(_tickets(3))
		monthly_review.run_monthly_review(now=datetime(2001, 3, 9, 8, 0))
		self.assertEqual(frappe.db.count(REVIEW_MONTH, {"month": MONTH}), 1)
		self.assertEqual(self._items(), first)
		self.assertEqual(
			monthly_review.pick_sample(monthly_review.review_candidates(MONTH), MONTH, 10),
			monthly_review.pick_sample(monthly_review.review_candidates(MONTH), MONTH, 10),
		)

	def test_only_the_previous_month(self):
		_bot_touched(_tickets(2))
		# Run at 07:59 on the 1st still belongs to the cycle before: the month to review is the one before that.
		monthly_review.run_monthly_review(now=datetime(2001, 3, 1, 7, 59))
		self.assertFalse(frappe.db.exists(REVIEW_MONTH, f"REV-{MONTH}"))
		self.assertTrue(frappe.db.exists(REVIEW_MONTH, "REV-2001-01"))
		# An older month with no row is not filled in later (D-10).
		monthly_review.run_monthly_review(now=datetime(2001, 5, 1, 8, 0))
		self.assertEqual(frappe.db.count(REVIEW_MONTH), 2)
		self.assertFalse(frappe.db.exists(REVIEW_MONTH, "REV-2001-03"))
		self.assertTrue(frappe.db.exists(REVIEW_MONTH, "REV-2001-04"))

	def test_candidates_are_tickets_the_bot_wrote_on(self):
		applied, ok_action, failed, other_month, no_write = _tickets(5)
		_log(applied, entry_type="classify", applied=1)
		_log(ok_action, actions=[_ok_action(ok_action, ok=False), _ok_action(ok_action)])
		_log(failed, actions=[_ok_action(failed, ok=False)])
		_log(failed, entry_type="classify", applied=0)
		_log(other_month, creation=datetime(2001, 3, 1, 0, 0), actions=[_ok_action(other_month)])
		_log(no_write)
		self.assertEqual(
			monthly_review.review_candidates(MONTH), sorted([applied, ok_action]), "sorted by name"
		)

	def test_excluded_absent(self):
		kept, opted_out = _tickets(2)
		_bot_touched([kept, opted_out])
		frappe.db.set_value("HD Ticket", opted_out, "ai_opt_out", 1)
		self.assertEqual(monthly_review.review_candidates(MONTH), [kept])
		monthly_review.run_monthly_review(now=NOW)
		self.assertEqual(self._items(), [kept])

	def test_no_reviewers_list_still_created(self):
		_bot_touched(_tickets(3))
		with patch("frappe.sendmail") as sendmail:
			monthly_review.run_monthly_review(now=NOW)
		sendmail.assert_not_called()
		self.assertEqual(len(self._items()), 3)

	def test_reviewers_get_the_count_and_the_link_without_titles(self):
		_bot_touched(_tickets(4))
		set_agent_settings(monthly_reviewers=REVIEWERS)
		with patch("frappe.sendmail") as sendmail:
			monthly_review.run_monthly_review(now=NOW)
		sendmail.assert_called_once()
		sent = sendmail.call_args.kwargs
		self.assertEqual(sent["recipients"], ["erpai-review-a@example.com", "erpai-review-b@example.com"])
		self.assertEqual(sent["subject"], f"[erp_ai] Danh sách rà soát {MONTH}")
		self.assertIs(sent["delayed"], True)
		self.assertIn(f"/app/erp-ai-review-month/REV-{MONTH}", sent["message"])
		self.assertIn("4", sent["message"])
		self.assertNotIn("ERPAI-TEST review", sent["message"])

	def test_error_midway_no_row_then_once(self):
		_bot_touched(_tickets(3))
		set_agent_settings(monthly_reviewers=REVIEWERS)
		with (
			patch("frappe.sendmail", side_effect=frappe.OutgoingEmailError("boom")),
			patch("frappe.log_error") as log_error,
		):
			monthly_review.run_monthly_review(now=NOW)
		log_error.assert_called_once()
		self.assertEqual(log_error.call_args.args[0], monthly_review.TITLE_REVIEW_FAILED)
		self.assertFalse(frappe.db.exists(REVIEW_MONTH, f"REV-{MONTH}"))

		with patch("frappe.sendmail") as sendmail:
			monthly_review.run_monthly_review(now=NOW)
			monthly_review.run_monthly_review(now=NOW)
		sendmail.assert_called_once()
		self.assertEqual(frappe.db.count(REVIEW_MONTH, {"month": MONTH}), 1)
