"""C0F R6c: raise the HD Ticket counter past every ticket name the ERP AI Log refers to.

Before `handlers.ticket_after_delete`, deleting the newest ticket moved the counter back, and the next
ticket took the deleted ticket's name together with its kept log rows (D7). Only ever raises the counter;
a site whose counter is already past every logged ticket is left alone.
"""

import frappe

from erp_ai.constants import LOG_DOCTYPE
from erp_ai.handlers import raise_ticket_series, ticket_number


def execute():
	tickets = frappe.db.sql_list(
		f"select distinct ticket from `tab{LOG_DOCTYPE}` where ifnull(ticket, '') != ''"
	)
	numbers = [number for number in map(ticket_number, tickets) if number is not None]
	if numbers:
		raise_ticket_series(max(numbers))
