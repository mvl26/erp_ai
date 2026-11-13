"""Proposal state machine: the only module that writes the state group of ERP AI Change Proposal (ADR-012 QĐ 2)."""

import hashlib
import json

import frappe
from frappe.utils import now_datetime

from erp_ai.agent.changes.process_runner import CommandResult
from erp_ai.agent.run_log import ENTRY_TYPE_CHANGE, write_entry
from erp_ai.constants import (
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	PROPOSAL_DOCTYPE,
	TRIGGER_CHANGE_ACTION,
)

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
# The state fields a job may pass to `finish(fields=)` (design 3.5, round 1).
GIT_RESULT_FIELDS = ("applied_branch", "applied_ahead_count", "apply_commit_sha", "undo_commit_sha")
# Design 2.2: the edges a job ends with, each with the one log step it writes.
FINISH_EDGES = {
	(CHANGE_STATUS_APPROVED, CHANGE_STATUS_FAILED): "fail",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_APPLIED): "apply",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_FAILED): "fail",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_STALE): "stale",
	(CHANGE_STATUS_UNDOING, CHANGE_STATUS_UNDONE): "undo",
	(CHANGE_STATUS_UNDOING, CHANGE_STATUS_FAILED): "fail",
}


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


def _require_text(value, label) -> None:
	if not isinstance(value, str) or not value.strip():
		raise ValueError(f"{label} must be a non-empty string, got {value!r}")


def _lock(name) -> frappe._dict:
	"""Lock the proposal row (D-2) and return its `change_status` and `change_kind`.

	Raises:
		ValueError: `name` is not a non-empty string.
		frappe.DoesNotExistError: no proposal has that name (design 3.3 sentence, escaped).
	"""
	_require_text(name, "name")
	row = frappe.db.get_value(
		PROPOSAL_DOCTYPE, name, ["change_status", "change_kind"], as_dict=True, for_update=True
	)
	if row is None:
		raise frappe.DoesNotExistError(f"Không có đề xuất {frappe.utils.escape_html(name)}")
	return row


def _refuse(status, verb):
	frappe.throw(f"Đề xuất đang ở trạng thái {status}, không {verb} được", InvalidTransition)


def _decide(name, user, new_status, verb, step) -> str:
	_require_text(user, "user")
	row = _lock(name)
	if row.change_status != CHANGE_STATUS_PENDING:
		_refuse(row.change_status, verb)
	values = {"change_status": new_status, "decided_by": user, "decided_at": now_datetime()}
	if new_status == CHANGE_STATUS_APPROVED:
		values["approved_digest"] = content_digest(frappe.get_doc(PROPOSAL_DOCTYPE, name))
	frappe.db.set_value(PROPOSAL_DOCTYPE, name, values, update_modified=True)
	log_step(name, step, user)
	return new_status


def approve(name, user) -> str:
	"""`Chờ duyệt → Đã duyệt`: write `decided_by`, `decided_at`, `approved_digest` and one `approve` row.

	Raises:
		InvalidTransition: the proposal is not `Chờ duyệt`; nothing is written.
		ValueError, frappe.DoesNotExistError: see `_lock`; `user` is not a non-empty string.
	"""
	return _decide(name, user, CHANGE_STATUS_APPROVED, "duyệt", "approve")


def reject(name, user) -> str:
	"""`Chờ duyệt → Đã từ chối`: write `decided_by`, `decided_at` and one `reject` row. Raises as `approve`."""
	return _decide(name, user, CHANGE_STATUS_REJECTED, "từ chối", "reject")


def request_undo(name, user) -> str:
	"""`Đã áp dụng → Đang hoàn tác` for a code change: write `undo_by`, `undo_at`; the job logs `undo`.

	Raises:
		InvalidTransition: a bench command (any state), or a code change not `Đã áp dụng`; nothing is written.
		ValueError, frappe.DoesNotExistError: see `_lock`; `user` is not a non-empty string.
	"""
	_require_text(user, "user")
	row = _lock(name)
	if row.change_kind == CHANGE_KIND_COMMAND:
		frappe.throw("Lệnh bench không hoàn tác được", InvalidTransition)
	if row.change_status != CHANGE_STATUS_APPLIED:
		_refuse(row.change_status, "hoàn tác")
	frappe.db.set_value(
		PROPOSAL_DOCTYPE,
		name,
		{"change_status": CHANGE_STATUS_UNDOING, "undo_by": user, "undo_at": now_datetime()},
		update_modified=True,
	)
	return CHANGE_STATUS_UNDOING


def begin_apply(name) -> bool:
	"""`Đã duyệt → Đang áp dụng`; `False` and nothing written from any other state (a repeated job).

	Raises:
		ValueError, frappe.DoesNotExistError: see `_lock`.
	"""
	if _lock(name).change_status != CHANGE_STATUS_APPROVED:
		return False
	frappe.db.set_value(
		PROPOSAL_DOCTYPE, name, {"change_status": CHANGE_STATUS_APPLYING}, update_modified=True
	)
	return True


def finish(
	name,
	expected,
	new_status,
	*,
	step,
	actor,
	reason=None,
	result=None,
	fields=None,
	before=None,
	after=None,
) -> bool:
	"""End a job: `expected → new_status` (an edge of `FINISH_EDGES` with its `step`) and one log row.

	Writes `finished_at`, `failure_reason = reason`, the git `fields` and, with a `CommandResult`
	`result`, `exit_code`/`duration_ms`/`command_output` (also the row's `value_after`). `before` and
	`after` go to the row's `value_before`/`value_after` (design 4.3 step 3.7, 4.4 step 7).
	Returns `False` and writes nothing when the proposal is no longer `expected`.

	Raises:
		ValueError: not an edge of `FINISH_EDGES` or `step` not its step; `fields` not a dict of
			`GIT_RESULT_FIELDS` keys; `result` not a `CommandResult`, or given with `after`; `actor`
			not a non-empty string; see `_lock`.
		frappe.DoesNotExistError: see `_lock`.
	"""
	edge_step = FINISH_EDGES.get((expected, new_status))
	if edge_step is None:
		raise ValueError(f"{expected!r} → {new_status!r} is not a job edge")
	if step != edge_step:
		raise ValueError(f"{expected!r} → {new_status!r} logs step {edge_step!r}, got {step!r}")
	fields = {} if fields is None else fields
	if not isinstance(fields, dict) or not set(fields) <= set(GIT_RESULT_FIELDS):
		raise ValueError(f"fields must be a dict of {GIT_RESULT_FIELDS}, got {fields!r}")
	if result is not None:
		if not isinstance(result, CommandResult):
			raise ValueError(f"result must be a CommandResult, got {result!r}")
		if after is not None:
			raise ValueError("pass either result or after, not both")
	_require_text(actor, "actor")
	if _lock(name).change_status != expected:
		return False
	values = {"change_status": new_status, "finished_at": now_datetime(), "failure_reason": reason, **fields}
	if result is not None:
		# `exit_code` is a NOT NULL Int column: no exit code (never ran) is stored as Frappe's empty Int, 0;
		# the log row keeps `None`.
		exit_code = 0 if result.exit_code is None else result.exit_code
		values.update(
			{"exit_code": exit_code, "duration_ms": result.duration_ms, "command_output": result.output}
		)
		after = {"exit_code": result.exit_code, "duration_ms": result.duration_ms, "output": result.output}
	frappe.db.set_value(PROPOSAL_DOCTYPE, name, values, update_modified=True)
	log_step(name, step, actor, error=reason, before=before, after=after)
	return True
