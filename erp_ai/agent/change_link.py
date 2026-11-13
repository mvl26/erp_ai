"""Signed approve/reject links for a change proposal, put in the bot's ticket comment.

The signature is Frappe's signed-URL HMAC over the proposal name and the action, so a link cannot be
made for another proposal or turned from reject into approve. Who may use a link is decided where it
is opened (`erp_ai.change_decision.decide`), not here.
"""

import hmac

from frappe.utils.verified_command import get_signed_params

DECIDE_METHOD = "erp_ai.change_decision.decide"
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTIONS = (ACTION_APPROVE, ACTION_REJECT)
SIGNATURE_MARK = "&_signature="


def _signed_query(name, action) -> str:
	if not isinstance(name, str) or not name.strip():
		raise ValueError(f"name must be a non-empty proposal name, got {name!r}")
	if action not in ACTIONS:
		raise ValueError(f"action must be one of {ACTIONS}, got {action!r}")
	return get_signed_params({"name": name, "action": action})


def decision_path(name: str, action: str) -> str:
	"""Site-relative URL that approves or rejects `name` when an ERP AI Instructor opens it."""
	return f"/api/method/{DECIDE_METHOD}?{_signed_query(name, action)}"


def signature_ok(name, action, signature) -> bool:
	"""True only for the signature `decision_path(name, action)` carries."""
	if not isinstance(signature, str) or not signature:
		return False
	try:
		expected = _signed_query(name, action).rsplit(SIGNATURE_MARK, 1)[1]
	except ValueError:
		return False
	return hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8"))
