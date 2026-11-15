from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import LOG_DOCTYPE
from erp_ai.handlers import ticket_series_name
from erp_ai.patches import feat007_ticket_series_past_logged_tickets as series_patch
from erp_ai.test_utils import keep_agent_settings, make_log_entry

PATCHES_TXT = Path(__file__).resolve().parent.parent / "patches.txt"
PATCH_LINE = "erp_ai.patches.feat007_ticket_series_past_logged_tickets"


def post_model_sync_lines() -> list[str]:
	lines = [line.strip() for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()]
	section = lines[lines.index("[post_model_sync]") + 1 :]
	return [line for line in section if line and not line.startswith("#")]


def series_current() -> int:
	rows = frappe.db.sql("select current from `tabSeries` where name = %s", (ticket_series_name(),))
	return int(rows[0][0]) if rows else 0


def set_series(current: int) -> None:
	frappe.db.sql("update `tabSeries` set current = %s where name = %s", (current, ticket_series_name()))


def log_row_of_deleted_ticket(number: int) -> str:
	"""A kept ERP AI Log row (D7) of a ticket that no longer exists: the ticket column holds its old name."""
	name = make_log_entry(entry_type="classify")
	frappe.db.set_value(LOG_DOCTYPE, name, "ticket", str(number), update_modified=False)
	return name


class TestTicketSeriesPastLoggedTickets(FrappeTestCase):
	"""C0F R6c: raise the HD Ticket counter past every ticket name the log refers to; never lower it."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		# The rows already on the site set the starting point; the test adds rows above it.
		series_patch.execute()
		self.start = series_current()

	def test_counter_rises_to_the_highest_logged_ticket(self):
		log_row_of_deleted_ticket(self.start + 2)
		log_row_of_deleted_ticket(self.start + 5)
		series_patch.execute()
		self.assertEqual(series_current(), self.start + 5)
		series_patch.execute()
		self.assertEqual(series_current(), self.start + 5)

	def test_counter_already_higher_is_left_alone(self):
		log_row_of_deleted_ticket(self.start + 3)
		set_series(self.start + 10)
		series_patch.execute()
		self.assertEqual(series_current(), self.start + 10)

	def test_patch_listed_once_after_model_sync(self):
		self.assertEqual(post_model_sync_lines().count(PATCH_LINE), 1)
