"""Proposal state machine: the only module that writes the state group of ERP AI Change Proposal (ADR-012 QĐ 2)."""

import hashlib
import json

import frappe

from erp_ai.agent.run_log import ENTRY_TYPE_CHANGE, write_entry
from erp_ai.constants import CHANGE_STATUS_PENDING, PROPOSAL_DOCTYPE, TRIGGER_CHANGE_ACTION

# Design 2.1 state group; `change_status` first, then every field a transition may set.
STATE_FIELDS = (
	"change_status",
	"decided_by",
	"decided_at",
	"approved_digest",
	"undo_by",
	"undo_at",
	"finished_at",
	"exit_code",
	"duration_ms",
	"command_output",
	"failure_reason",
	"applied_branch",
	"applied_ahead_count",
	"apply_commit_sha",
	"undo_commit_sha",
)
# Design 2.3, in this exact order (ADR-012 QĐ 7); `reason`, `diff` and identity fields are not part of it.
DIGEST_FIELDS = (
	"change_kind",
	"app",
	"file_path",
	"is_new_file",
	"command_args",
	"base_hash",
	"content_before",
	"content_after",
	"after_hash",
	"target_branch",
	"upstream_ref",
	"ahead_count",
	"is_core_app",
	"commit_message",
)


class InvalidTransition(frappe.ValidationError):
	"""The proposal is not in the state the requested transition starts from."""


def _require_proposal(doc) -> None:
	if doc.get("doctype") != PROPOSAL_DOCTYPE:
		raise ValueError(f"expected a {PROPOSAL_DOCTYPE} document, got {doc.get('doctype')!r}")


def prepare_new(doc) -> None:
	"""`before_insert`: whatever the caller passed, a new proposal starts `Chờ duyệt` with an empty state group.

	Raises:
		ValueError: `doc` is not an ERP AI Change Proposal.
	"""
	_require_proposal(doc)
	for fieldname in STATE_FIELDS:
		doc.set(fieldname, None)
	doc.set("change_status", CHANGE_STATUS_PENDING)


def content_digest(doc) -> str:
	"""sha256 hex of the JSON list of the 14 design 2.3 fields (`ensure_ascii=False`), as stored on `doc`.

	Raises:
		ValueError: `doc` is not an ERP AI Change Proposal.
	"""
	_require_proposal(doc)
	values = [doc.get(fieldname) for fieldname in DIGEST_FIELDS]
	return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode("utf-8")).hexdigest()


def log_step(proposal, step, actor, *, error=None, before=None, after=None) -> str:
	"""Write the one `change` ERP AI Log row of a proposal step; return the log name.

	`proposal` is the proposal name; the row takes its `ticket` and `run_id`. `before`/`after` go to
	`value_before`/`value_after` (stored as JSON).

	Raises:
		ValueError: `proposal` is not the name of an existing proposal, or `write_entry` refuses the
			step/actor (unknown `step`, blank `actor`).
	"""
	if not isinstance(proposal, str) or not proposal.strip():
		raise ValueError(f"proposal must be a non-empty name, got {proposal!r}")
	row = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal, ["ticket", "run_id"], as_dict=True)
	if row is None:
		raise ValueError(f"no {PROPOSAL_DOCTYPE} named {proposal!r}")
	return write_entry(
		entry_type=ENTRY_TYPE_CHANGE,
		trigger=TRIGGER_CHANGE_ACTION,
		change_step=step,
		actor=actor,
		change_proposal=proposal,
		ticket=row.ticket,
		run_id=row.run_id,
		error=error,
		value_before=before,
		value_after=after,
	)
