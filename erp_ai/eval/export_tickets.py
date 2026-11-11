import json
import os

import frappe

from erp_ai.agent import policy
from erp_ai.constants import CLASSIFICATION_FIELDS

EXPORT_FIELDS = ("subject", "description", *CLASSIFICATION_FIELDS, "owner")
REPO_ERROR = "Không ghi dữ liệu phiếu vào repo"


def _inside_repo(path: str) -> bool:
	# realpath resolves `..` and symlinks (also through a not-yet-existing file name).
	repo = os.path.dirname(os.path.realpath(frappe.get_app_path("erp_ai")))
	target = os.path.realpath(path)
	return os.path.commonpath([repo, target]) == repo


def export(path: str) -> int:
	"""Write labeled, send-allowed tickets as JSONL (6 keys per line); return the line count."""
	if _inside_repo(path):
		raise ValueError(REPO_ERROR)

	# "Labeled" = ticket_type set, the same definition compute_metrics uses.
	fields = list(dict.fromkeys(["name", *policy.SEND_POLICY_FIELDS, *EXPORT_FIELDS]))
	tickets = frappe.get_all("HD Ticket", filters={"ticket_type": ("is", "set")}, fields=fields)
	written = 0
	with open(path, "w", encoding="utf-8") as handle:
		for ticket in tickets:
			if not policy.can_send_ticket(ticket):
				continue
			handle.write(json.dumps({key: ticket.get(key) for key in EXPORT_FIELDS}, ensure_ascii=False))
			handle.write("\n")
			written += 1
	return written
