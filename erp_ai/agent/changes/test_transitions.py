import hashlib
import inspect
import json
from datetime import datetime
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import transitions
from erp_ai.agent.changes.process_runner import CommandResult
from erp_ai.constants import (
	BOT_GIT_EMAIL,
	BOT_GIT_NAME,
	CHANGE_KIND_CODE,
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
	CHANGE_STEPS,
	COMMAND_TIMEOUT_S,
	CORE_APPS,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	LOG_DOCTYPE,
	PROPOSAL_DOCTYPE,
	PROPOSAL_TEXT_MAX_CHARS,
	REPLACE_MAX_ITEMS,
	RUN_BACKSTOP_S,
	TITLE_CHANGE_FAILED,
	TRIGGER_CHANGE_ACTION,
)
from erp_ai.test_utils import make_change_proposal

# Design 2.1 state group, written out by hand (11 fields + 4 CHG-002 fields + 4 git fields of round 1).
STATE_FIELDS_EXPECTED = (
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
	"command_results",
	"failure_reason",
	"created_dirs",
	"restart_status",
	"restart_sent_at",
	"applied_branch",
	"applied_ahead_count",
	"apply_commit_sha",
	"undo_commit_sha",
)
# A non-empty value for every state field, so clearing is observable.
STATE_VALUES = {
	"change_status": "Đã duyệt",
	"decided_by": "Administrator",
	"decided_at": "2026-11-13 10:00:00",
	"approved_digest": "2" * 64,
	"undo_by": "Administrator",
	"undo_at": "2026-11-13 11:00:00",
	"finished_at": "2026-11-13 12:00:00",
	"exit_code": 1,
	"duration_ms": 250,
	"command_output": "lỗi\n",
	"failure_reason": "nội dung đề xuất đã bị sửa sau khi duyệt",
	"applied_branch": "main",
	"applied_ahead_count": 1,
	"apply_commit_sha": "a" * 40,
	"undo_commit_sha": "b" * 40,
}
# Design 2.3, in order: 9 fields + 5 git fields of round 1; each paired with a different valid value.
DIGEST_FIELD_NEW_VALUES = (
	("change_kind", "Lệnh bench"),
	("app", "otherapp"),
	("file_path", "otherapp/otherapp/ok.py"),
	("is_new_file", 1),
	("command_args", '["migrate"]'),
	("base_hash", "0" * 64),
	("content_before", "y = 1\n"),
	("content_after", "y = 2\n"),
	("after_hash", "1" * 64),
	("target_branch", "develop"),
	("upstream_ref", "upstream/develop"),
	("ahead_count", 7),
	("is_core_app", 1),
	("commit_message", "erp_ai: thông điệp khác"),
)
# Fields outside the digest (design 2.3: `reason` is display only; identity and diff are derived/context).
NON_DIGEST_FIELD_NEW_VALUES = (
	("reason", "Lý do khác"),
	("diff", "--- a/x\n+++ b/x\n"),
	("run_id", "ERPAI-TEST-other-run"),
	("instructor", "Guest"),
	("reversible", 0),
	*STATE_VALUES.items(),
)


class TestChangeConstants(FrappeTestCase):
	def test_status_values(self):
		self.assertEqual(
			(
				CHANGE_STATUS_PENDING,
				CHANGE_STATUS_REJECTED,
				CHANGE_STATUS_APPROVED,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				CHANGE_STATUS_FAILED,
				CHANGE_STATUS_STALE,
				CHANGE_STATUS_UNDOING,
				CHANGE_STATUS_UNDONE,
			),
			(
				"Chờ duyệt",
				"Đã từ chối",
				"Đã duyệt",
				"Đang áp dụng",
				"Đã áp dụng",
				"Lỗi",
				"Hết hiệu lực",
				"Đang hoàn tác",
				"Đã hoàn tác",
			),
		)
		self.assertEqual(PROPOSAL_DOCTYPE, "ERP AI Change Proposal")
		self.assertEqual((CHANGE_KIND_CODE, CHANGE_KIND_COMMAND), ("Thay đổi code", "Lệnh bench"))
		self.assertEqual(CHANGE_STEPS, ("propose", "approve", "reject", "apply", "fail", "stale", "undo"))
		self.assertEqual(TRIGGER_CHANGE_ACTION, "change_action")
		self.assertEqual(TITLE_CHANGE_FAILED, "erp_ai: áp dụng thay đổi lỗi")
		self.assertEqual((PROPOSAL_TEXT_MAX_CHARS, REPLACE_MAX_ITEMS), (20000, 10))

	def test_command_timeout_is_job_timeout_minus_margin(self):
		self.assertEqual(COMMAND_TIMEOUT_S, JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S)
		self.assertEqual(COMMAND_TIMEOUT_S, 540)

	def test_run_backstop(self):
		self.assertEqual(RUN_BACKSTOP_S, COMMAND_TIMEOUT_S + JOB_SAFETY_MARGIN_S // 2)
		self.assertEqual(RUN_BACKSTOP_S, 570)

	def test_core_apps_and_bot_identity(self):
		self.assertEqual(CORE_APPS, ("frappe", "erpnext", "helpdesk", "hrms"))
		self.assertNotIn("erp_ai", CORE_APPS)
		self.assertEqual(BOT_GIT_NAME, "ERP AI Agent")
		self.assertEqual(BOT_GIT_EMAIL, "erp-ai-agent@bot.invalid")
		self.assertTrue(BOT_GIT_EMAIL.endswith(".invalid"))


def _hand_digest(doc) -> str:
	values = [
		doc.change_kind,
		doc.app,
		doc.file_path,
		doc.is_new_file,
		doc.command_args,
		doc.base_hash,
		doc.content_before,
		doc.content_after,
		doc.after_hash,
		doc.target_branch,
		doc.upstream_ref,
		doc.ahead_count,
		doc.is_core_app,
		doc.commit_message,
	]
	return hashlib.sha256(json.dumps(values, ensure_ascii=False).encode("utf-8")).hexdigest()


class TestTransitionsBasics(FrappeTestCase):
	def test_state_fields_are_the_design_state_group(self):
		self.assertEqual(transitions.STATE_FIELDS, STATE_FIELDS_EXPECTED)
		self.assertNotIn("reason", transitions.STATE_FIELDS)
		self.assertNotIn("commit_message", transitions.STATE_FIELDS)

	def test_invalid_transition_is_a_validation_error(self):
		self.assertTrue(issubclass(transitions.InvalidTransition, frappe.ValidationError))

	def test_prepare_new_forces_pending_and_clears_state_fields(self):
		for status in (
			CHANGE_STATUS_APPROVED,
			CHANGE_STATUS_REJECTED,
			CHANGE_STATUS_APPLYING,
			CHANGE_STATUS_APPLIED,
			CHANGE_STATUS_FAILED,
			CHANGE_STATUS_STALE,
			CHANGE_STATUS_UNDOING,
			CHANGE_STATUS_UNDONE,
			None,
		):
			with self.subTest(status=status):
				doc = frappe.get_doc({"doctype": PROPOSAL_DOCTYPE, **STATE_VALUES, "change_status": status})
				transitions.prepare_new(doc)
				self.assertEqual(doc.change_status, "Chờ duyệt")
				for fieldname in STATE_FIELDS_EXPECTED[1:]:
					self.assertIsNone(doc.get(fieldname), fieldname)

	def test_prepare_new_keeps_content_fields(self):
		doc = frappe.get_doc(
			{"doctype": PROPOSAL_DOCTYPE, **dict(DIGEST_FIELD_NEW_VALUES), "reason": "Lý do", **STATE_VALUES}
		)
		transitions.prepare_new(doc)
		for fieldname, value in (*DIGEST_FIELD_NEW_VALUES, ("reason", "Lý do")):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(doc.get(fieldname), value)

	def test_prepare_new_rejects_other_doctype(self):
		doc = frappe.get_doc({"doctype": LOG_DOCTYPE, "change_status": CHANGE_STATUS_APPROVED})
		with self.assertRaises(ValueError):
			transitions.prepare_new(doc)
		self.assertEqual(doc.get("change_status"), CHANGE_STATUS_APPROVED)

	def test_content_digest_is_sha256_of_the_fourteen_fields(self):
		for kind in (CHANGE_KIND_CODE, CHANGE_KIND_COMMAND):
			with self.subTest(kind=kind):
				doc = frappe.get_doc(PROPOSAL_DOCTYPE, make_change_proposal(kind=kind).name)
				digest = transitions.content_digest(doc)
				self.assertRegex(digest, r"^[0-9a-f]{64}$")
				self.assertEqual(digest, _hand_digest(doc))

	def test_content_digest_pins_the_order_of_the_three_int_fields(self):
		# Distinct values in is_new_file, ahead_count and is_core_app: swapping any two names in
		# DIGEST_FIELDS changes the digest, so a stored approved_digest cannot silently drift.
		doc = frappe.get_doc(
			PROPOSAL_DOCTYPE, make_change_proposal(is_new_file=1, ahead_count=2, is_core_app=0).name
		)
		self.assertEqual(len({doc.is_new_file, doc.ahead_count, doc.is_core_app}), 3)
		self.assertEqual(transitions.content_digest(doc), _hand_digest(doc))

	def test_content_digest_keeps_non_ascii_unescaped(self):
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, make_change_proposal(content_after="x = 'Đã duyệt'\n").name)
		values = [doc.get(name) for name, _value in DIGEST_FIELD_NEW_VALUES]
		escaped = hashlib.sha256(json.dumps(values).encode("utf-8")).hexdigest()
		self.assertNotEqual(transitions.content_digest(doc), escaped)
		self.assertEqual(transitions.content_digest(doc), _hand_digest(doc))

	def test_content_digest_changes_with_any_field(self):
		self.assertEqual(len(DIGEST_FIELD_NEW_VALUES), 14)
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, make_change_proposal().name)
		before = transitions.content_digest(doc)
		for fieldname, new_value in DIGEST_FIELD_NEW_VALUES:
			with self.subTest(fieldname=fieldname):
				changed = frappe.get_doc(PROPOSAL_DOCTYPE, doc.name)
				self.assertNotEqual(changed.get(fieldname), new_value)
				changed.set(fieldname, new_value)
				self.assertNotEqual(transitions.content_digest(changed), before)

	def test_content_digest_ignores_fields_outside_the_list(self):
		doc = frappe.get_doc(PROPOSAL_DOCTYPE, make_change_proposal().name)
		before = transitions.content_digest(doc)
		for fieldname, new_value in NON_DIGEST_FIELD_NEW_VALUES:
			with self.subTest(fieldname=fieldname):
				changed = frappe.get_doc(PROPOSAL_DOCTYPE, doc.name)
				changed.set(fieldname, new_value)
				self.assertEqual(transitions.content_digest(changed), before)

	def test_content_digest_rejects_other_doctype(self):
		with self.assertRaises(ValueError):
			transitions.content_digest(frappe.get_doc({"doctype": LOG_DOCTYPE}))

	def test_log_step_writes_one_change_row(self):
		proposal = make_change_proposal()
		before = {"sha256": "a" * 64, "head": "1" * 40}
		after = {"sha256": "b" * 64, "commit": "2" * 40, "branch": "main"}
		log_count = frappe.db.count(LOG_DOCTYPE)
		name = transitions.log_step(
			proposal.name, "apply", "Administrator", error="lý do", before=before, after=after
		)
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), log_count + 1)
		row = frappe.db.get_value(
			LOG_DOCTYPE,
			name,
			[
				"entry_type",
				"trigger",
				"change_step",
				"actor",
				"change_proposal",
				"ticket",
				"run_id",
				"error",
				"value_before",
				"value_after",
			],
			as_dict=True,
		)
		self.assertEqual(
			dict(row, value_before=json.loads(row.value_before), value_after=json.loads(row.value_after)),
			{
				"entry_type": "change",
				"trigger": "change_action",
				"change_step": "apply",
				"actor": "Administrator",
				"change_proposal": proposal.name,
				"ticket": proposal.ticket,
				"run_id": proposal.run_id,
				"error": "lý do",
				"value_before": before,
				"value_after": after,
			},
		)

	def test_log_step_without_optional_values_leaves_them_empty(self):
		proposal = make_change_proposal()
		name = transitions.log_step(proposal.name, "approve", "Administrator")
		row = frappe.db.get_value(
			LOG_DOCTYPE, name, ["change_step", "error", "value_before", "value_after"], as_dict=True
		)
		self.assertEqual(
			row, {"change_step": "approve", "error": None, "value_before": None, "value_after": None}
		)

	def test_log_step_refuses_bad_input_and_writes_nothing(self):
		proposal = make_change_proposal()
		log_count = frappe.db.count(LOG_DOCTYPE)
		cases = {
			"unknown step": (proposal.name, "commit", "Administrator"),
			"empty actor": (proposal.name, "approve", ""),
			"empty proposal": ("", "approve", "Administrator"),
			"proposal not a string": (proposal, "approve", "Administrator"),
			"unknown proposal": ("AICHG-99999999", "approve", "Administrator"),
		}
		for case, args in cases.items():
			with self.subTest(case=case), self.assertRaises(ValueError):
				transitions.log_step(*args)
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), log_count)


# Design 2.2 / 3.5: the edges `finish` may take, each with the one log step it writes (hand-written).
FINISH_EDGES_EXPECTED = {
	(CHANGE_STATUS_APPROVED, CHANGE_STATUS_FAILED): "fail",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_APPLIED): "apply",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_FAILED): "fail",
	(CHANGE_STATUS_APPLYING, CHANGE_STATUS_STALE): "stale",
	(CHANGE_STATUS_UNDOING, CHANGE_STATUS_UNDONE): "undo",
	(CHANGE_STATUS_UNDOING, CHANGE_STATUS_FAILED): "fail",
}
ALL_STATUSES = (
	"Chờ duyệt",
	"Đã từ chối",
	"Đã duyệt",
	"Đang áp dụng",
	"Đã áp dụng",
	"Lỗi",
	"Hết hiệu lực",
	"Đang hoàn tác",
	"Đã hoàn tác",
)
GIT_FIELDS_EXPECTED = ("applied_branch", "applied_ahead_count", "apply_commit_sha", "undo_commit_sha")
NOW = datetime(2026, 11, 13, 9, 30, 15)
ACTOR = "Administrator"
LOG_FIELDS = ("change_step", "actor", "ticket", "run_id", "error", "value_before", "value_after", "creation")


def _state(name) -> dict:
	return frappe.db.get_value(PROPOSAL_DOCTYPE, name, list(STATE_FIELDS_EXPECTED), as_dict=True)


def _modified(name):
	return frappe.db.get_value(PROPOSAL_DOCTYPE, name, "modified")


def _rows(name) -> list:
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"change_proposal": name},
		fields=list(LOG_FIELDS),
		order_by="creation asc",
	)
	for row in rows:
		for key in ("value_before", "value_after"):
			row[key] = None if row[key] is None else json.loads(row[key])
	return rows


def _proposal_in(status, kind=CHANGE_KIND_CODE):
	proposal = make_change_proposal(kind=kind)
	frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, "change_status", status, update_modified=False)
	return proposal


class TransitionTestCase(FrappeTestCase):
	def setUp(self):
		patcher = patch("erp_ai.agent.changes.transitions.now_datetime", return_value=NOW)
		patcher.start()
		self.addCleanup(patcher.stop)

	def assertNothingChanged(self, name, state, modified):
		self.assertEqual(_state(name), state)
		self.assertEqual(_modified(name), modified)
		self.assertEqual(_rows(name), [])

	def assertRefused(self, call, message, name):
		state, modified = _state(name), _modified(name)
		with self.assertRaises(transitions.InvalidTransition) as caught:
			call()
		self.assertEqual(str(caught.exception), message)
		self.assertNothingChanged(name, state, modified)


class TestApproveReject(TransitionTestCase):
	def test_approve_writes_decision_digest_and_one_row(self):
		proposal = make_change_proposal()
		before, modified = _state(proposal.name), _modified(proposal.name)
		digest = _hand_digest(frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name))
		self.assertEqual(transitions.approve(proposal.name, ACTOR), "Đã duyệt")
		self.assertEqual(
			_state(proposal.name),
			{
				**before,
				"change_status": "Đã duyệt",
				"decided_by": ACTOR,
				"decided_at": NOW,
				"approved_digest": digest,
			},
		)
		self.assertNotEqual(_modified(proposal.name), modified)
		rows = _rows(proposal.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(
			{key: rows[0][key] for key in LOG_FIELDS[:-1]},
			{
				"change_step": "approve",
				"actor": ACTOR,
				"ticket": proposal.ticket,
				"run_id": proposal.run_id,
				"error": None,
				"value_before": None,
				"value_after": None,
			},
		)

	def test_reject_writes_decision_and_one_row_without_digest(self):
		proposal = make_change_proposal()
		before = _state(proposal.name)
		self.assertEqual(transitions.reject(proposal.name, ACTOR), "Đã từ chối")
		self.assertEqual(
			_state(proposal.name),
			{**before, "change_status": "Đã từ chối", "decided_by": ACTOR, "decided_at": NOW},
		)
		self.assertIsNone(_state(proposal.name).approved_digest)
		self.assertEqual([(row.change_step, row.actor) for row in _rows(proposal.name)], [("reject", ACTOR)])

	def test_approve_twice_second_raises_and_logs_nothing(self):
		proposal = make_change_proposal()
		transitions.approve(proposal.name, ACTOR)
		state, modified, rows = _state(proposal.name), _modified(proposal.name), _rows(proposal.name)
		with self.assertRaises(transitions.InvalidTransition) as caught:
			transitions.approve(proposal.name, "Guest")
		self.assertEqual(str(caught.exception), "Đề xuất đang ở trạng thái Đã duyệt, không duyệt được")
		self.assertEqual(_state(proposal.name), state)
		self.assertEqual(_modified(proposal.name), modified)
		self.assertEqual(_rows(proposal.name), rows)

	def test_reject_then_approve_raises(self):
		proposal = make_change_proposal()
		transitions.reject(proposal.name, ACTOR)
		state, modified, rows = _state(proposal.name), _modified(proposal.name), _rows(proposal.name)
		for call, verb in ((transitions.approve, "duyệt"), (transitions.reject, "từ chối")):
			with self.subTest(verb=verb), self.assertRaises(transitions.InvalidTransition) as caught:
				call(proposal.name, ACTOR)
			self.assertEqual(
				str(caught.exception), f"Đề xuất đang ở trạng thái Đã từ chối, không {verb} được"
			)
		self.assertEqual(_state(proposal.name), state)
		self.assertEqual(_modified(proposal.name), modified)
		self.assertEqual(_rows(proposal.name), rows)

	def test_approve_and_reject_refused_from_every_other_state(self):
		for status in ALL_STATUSES[1:]:
			for call, verb in ((transitions.approve, "duyệt"), (transitions.reject, "từ chối")):
				with self.subTest(status=status, verb=verb):
					proposal = _proposal_in(status)
					self.assertRefused(
						lambda: call(proposal.name, ACTOR),
						f"Đề xuất đang ở trạng thái {status}, không {verb} được",
						proposal.name,
					)


class TestRequestUndo(TransitionTestCase):
	def test_request_undo_writes_undo_by_and_at_without_row(self):
		proposal = _proposal_in(CHANGE_STATUS_APPLIED)
		before = _state(proposal.name)
		self.assertEqual(transitions.request_undo(proposal.name, ACTOR), "Đang hoàn tác")
		self.assertEqual(
			_state(proposal.name),
			{**before, "change_status": "Đang hoàn tác", "undo_by": ACTOR, "undo_at": NOW},
		)
		self.assertEqual(_rows(proposal.name), [])

	def test_request_undo_refused_for_command(self):
		for status in ALL_STATUSES:
			with self.subTest(status=status):
				proposal = _proposal_in(status, kind=CHANGE_KIND_COMMAND)
				self.assertRefused(
					lambda: transitions.request_undo(proposal.name, ACTOR),
					"Lệnh bench không hoàn tác được",
					proposal.name,
				)

	def test_request_undo_refused_for_code_outside_applied(self):
		for status in (s for s in ALL_STATUSES if s != "Đã áp dụng"):
			with self.subTest(status=status):
				proposal = _proposal_in(status)
				self.assertRefused(
					lambda: transitions.request_undo(proposal.name, ACTOR),
					f"Đề xuất đang ở trạng thái {status}, không hoàn tác được",
					proposal.name,
				)

	# CHG-002 design 3.3 `undo`, 4.3 "Cạnh mới": `Lỗi → Đang hoàn tác` for a code change whose apply
	# commit exists and was not undone yet; each condition failing on its own keeps the old refusal.
	def _failed_with(self, kind=CHANGE_KIND_CODE, **fields):
		proposal = _proposal_in(CHANGE_STATUS_FAILED, kind=kind)
		if fields:
			frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, fields, update_modified=False)
		return proposal

	def test_from_failed_needs_apply_sha_and_no_undo_sha(self):
		proposal = self._failed_with(apply_commit_sha="a" * 40)
		before = _state(proposal.name)
		self.assertEqual(transitions.request_undo(proposal.name, ACTOR), "Đang hoàn tác")
		self.assertEqual(
			_state(proposal.name),
			{**before, "change_status": "Đang hoàn tác", "undo_by": ACTOR, "undo_at": NOW},
		)
		self.assertEqual(_state(proposal.name).apply_commit_sha, "a" * 40)
		self.assertEqual(_rows(proposal.name), [])

	def test_from_failed_without_sha_refused(self):
		for apply_sha in (None, ""):
			with self.subTest(apply_commit_sha=apply_sha):
				proposal = self._failed_with(apply_commit_sha=apply_sha)
				self.assertRefused(
					lambda: transitions.request_undo(proposal.name, ACTOR),
					"Đề xuất đang ở trạng thái Lỗi, không hoàn tác được",
					proposal.name,
				)
				self.assertEqual(_state(proposal.name).change_status, "Lỗi")

	def test_from_failed_with_undo_sha_refused(self):
		proposal = self._failed_with(apply_commit_sha="a" * 40, undo_commit_sha="b" * 40)
		self.assertRefused(
			lambda: transitions.request_undo(proposal.name, ACTOR),
			"Đề xuất đang ở trạng thái Lỗi, không hoàn tác được",
			proposal.name,
		)
		self.assertEqual(_state(proposal.name).change_status, "Lỗi")

	def test_from_failed_other_kind_refused(self):
		proposal = self._failed_with(apply_commit_sha="a" * 40)
		frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, "change_kind", "Loại lạ", update_modified=False)
		self.assertRefused(
			lambda: transitions.request_undo(proposal.name, ACTOR),
			"Đề xuất đang ở trạng thái Lỗi, không hoàn tác được",
			proposal.name,
		)
		self.assertEqual(_state(proposal.name).change_status, "Lỗi")

	def test_command_only_block_not_undoable(self):
		proposal = self._failed_with(
			kind=CHANGE_KIND_COMMAND, command_list=json.dumps([["migrate"]]), apply_commit_sha="a" * 40
		)
		self.assertRefused(
			lambda: transitions.request_undo(proposal.name, ACTOR),
			"Lệnh bench không hoàn tác được",
			proposal.name,
		)
		self.assertEqual(_state(proposal.name).change_status, "Lỗi")

	def test_other_statuses_refused_even_with_apply_sha(self):
		for status in (s for s in ALL_STATUSES if s not in ("Đã áp dụng", "Lỗi")):
			with self.subTest(status=status):
				proposal = _proposal_in(status)
				frappe.db.set_value(
					PROPOSAL_DOCTYPE, proposal.name, "apply_commit_sha", "a" * 40, update_modified=False
				)
				self.assertRefused(
					lambda: transitions.request_undo(proposal.name, ACTOR),
					f"Đề xuất đang ở trạng thái {status}, không hoàn tác được",
					proposal.name,
				)

	def test_two_callers_one_wins(self):
		proposal = self._failed_with(apply_commit_sha="a" * 40)
		self.assertEqual(transitions.request_undo(proposal.name, ACTOR), "Đang hoàn tác")
		self.assertRefused(
			lambda: transitions.request_undo(proposal.name, "Guest"),
			"Đề xuất đang ở trạng thái Đang hoàn tác, không hoàn tác được",
			proposal.name,
		)
		self.assertEqual(_state(proposal.name).undo_by, ACTOR)

	def test_lock_reads_status_kind_and_both_commit_shas(self):
		proposal = self._failed_with(apply_commit_sha="a" * 40)
		with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value:
			transitions.request_undo(proposal.name, ACTOR)
		locks = [entry for entry in get_value.call_args_list if entry.kwargs.get("for_update") is True]
		self.assertEqual(len(locks), 1)
		self.assertEqual(
			locks[0].args,
			(
				PROPOSAL_DOCTYPE,
				proposal.name,
				["change_status", "change_kind", "apply_commit_sha", "undo_commit_sha"],
			),
		)


class TestBeginApply(TransitionTestCase):
	def test_begin_apply_only_from_approved_and_second_call_false(self):
		proposal = _proposal_in(CHANGE_STATUS_APPROVED)
		before = _state(proposal.name)
		self.assertIs(transitions.begin_apply(proposal.name), True)
		self.assertEqual(_state(proposal.name), {**before, "change_status": "Đang áp dụng"})
		self.assertEqual(_rows(proposal.name), [])
		state, modified = _state(proposal.name), _modified(proposal.name)
		self.assertIs(transitions.begin_apply(proposal.name), False)
		self.assertNothingChanged(proposal.name, state, modified)

	def test_begin_apply_false_from_every_other_state(self):
		for status in (s for s in ALL_STATUSES if s != "Đã duyệt"):
			with self.subTest(status=status):
				proposal = _proposal_in(status)
				state, modified = _state(proposal.name), _modified(proposal.name)
				self.assertIs(transitions.begin_apply(proposal.name), False)
				self.assertNothingChanged(proposal.name, state, modified)


class TestFinish(TransitionTestCase):
	def test_finish_edges_are_the_design_state_machine(self):
		self.assertEqual(len(FINISH_EDGES_EXPECTED), 6)
		for expected in ALL_STATUSES:
			for new_status in ALL_STATUSES:
				step = FINISH_EDGES_EXPECTED.get((expected, new_status))
				with self.subTest(expected=expected, new_status=new_status):
					proposal = _proposal_in(expected)
					if step is None:
						state, modified = _state(proposal.name), _modified(proposal.name)
						for any_step in ("apply", "fail", "stale", "undo"):
							with self.assertRaises(ValueError):
								transitions.finish(
									proposal.name, expected, new_status, step=any_step, actor=ACTOR
								)
						self.assertNothingChanged(proposal.name, state, modified)
					else:
						self.assertIs(
							transitions.finish(proposal.name, expected, new_status, step=step, actor=ACTOR),
							True,
						)
						self.assertEqual(_state(proposal.name).change_status, new_status)

	def test_finish_refuses_a_step_that_does_not_match_the_edge(self):
		for (expected, new_status), step in FINISH_EDGES_EXPECTED.items():
			for wrong_step in (s for s in CHANGE_STEPS if s != step):
				with self.subTest(expected=expected, new_status=new_status, step=wrong_step):
					proposal = _proposal_in(expected)
					state, modified = _state(proposal.name), _modified(proposal.name)
					with self.assertRaises(ValueError):
						transitions.finish(proposal.name, expected, new_status, step=wrong_step, actor=ACTOR)
					self.assertNothingChanged(proposal.name, state, modified)

	def test_finish_writes_status_time_reason_fields_and_one_row(self):
		proposal = _proposal_in(CHANGE_STATUS_APPLYING)
		before = _state(proposal.name)
		fields = {
			"apply_commit_sha": "c" * 40,
			"applied_branch": "main",
			"applied_ahead_count": 1,
		}
		value_before = {"sha256": "a" * 64, "head": "d" * 40}
		value_after = {"sha256": "b" * 64, "commit": "c" * 40, "branch": "main"}
		self.assertIs(
			transitions.finish(
				proposal.name,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				step="apply",
				actor=ACTOR,
				fields=fields,
				before=value_before,
				after=value_after,
			),
			True,
		)
		self.assertEqual(
			_state(proposal.name),
			{
				**before,
				"change_status": "Đã áp dụng",
				"finished_at": NOW,
				"failure_reason": None,
				"apply_commit_sha": "c" * 40,
				"applied_branch": "main",
				"applied_ahead_count": 1,
			},
		)
		rows = _rows(proposal.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(
			{key: rows[0][key] for key in LOG_FIELDS[:-1]},
			{
				"change_step": "apply",
				"actor": ACTOR,
				"ticket": proposal.ticket,
				"run_id": proposal.run_id,
				"error": None,
				"value_before": value_before,
				"value_after": value_after,
			},
		)

	def test_finish_failure_stores_reason_and_logs_it_as_error(self):
		proposal = _proposal_in(CHANGE_STATUS_UNDOING)
		before = _state(proposal.name)
		reason = "file đã đổi sau khi áp dụng, không hoàn tác"
		self.assertIs(
			transitions.finish(
				proposal.name,
				CHANGE_STATUS_UNDOING,
				CHANGE_STATUS_FAILED,
				step="fail",
				actor=ACTOR,
				reason=reason,
				fields={"undo_commit_sha": "e" * 40},
			),
			True,
		)
		self.assertEqual(
			_state(proposal.name),
			{
				**before,
				"change_status": "Lỗi",
				"finished_at": NOW,
				"failure_reason": reason,
				"undo_commit_sha": "e" * 40,
			},
		)
		self.assertEqual(
			[(row.change_step, row.error, row.value_before, row.value_after) for row in _rows(proposal.name)],
			[("fail", reason, None, None)],
		)

	def test_finish_result_stores_command_output_on_proposal_and_row(self):
		# (result, exit_code stored on the proposal): the Int column is NOT NULL, so no exit code is 0 there.
		cases = {
			"exit code": (
				CommandResult(exit_code=1, output="lỗi\n", duration_ms=250, timed_out=False, not_found=False),
				1,
			),
			"no budget": (
				CommandResult(exit_code=None, output="", duration_ms=0, timed_out=True, not_found=False),
				0,
			),
		}
		for case, (result, stored_exit_code) in cases.items():
			with self.subTest(case=case):
				proposal = _proposal_in(CHANGE_STATUS_APPLYING, kind=CHANGE_KIND_COMMAND)
				before = _state(proposal.name)
				self.assertIs(
					transitions.finish(
						proposal.name,
						CHANGE_STATUS_APPLYING,
						CHANGE_STATUS_FAILED,
						step="fail",
						actor=ACTOR,
						reason="quá thời gian",
						result=result,
					),
					True,
				)
				self.assertEqual(
					_state(proposal.name),
					{
						**before,
						"change_status": "Lỗi",
						"finished_at": NOW,
						"failure_reason": "quá thời gian",
						"exit_code": stored_exit_code,
						"duration_ms": result.duration_ms,
						"command_output": result.output,
					},
				)
				self.assertEqual(
					[(row.change_step, row.error, row.value_after) for row in _rows(proposal.name)],
					[
						(
							"fail",
							"quá thời gian",
							{
								"exit_code": result.exit_code,
								"duration_ms": result.duration_ms,
								"output": result.output,
							},
						)
					],
				)

	def test_finish_refuses_bad_result(self):
		ok = CommandResult(exit_code=0, output="", duration_ms=1, timed_out=False, not_found=False)
		cases = {
			"not a CommandResult": {"result": {"exit_code": 0, "duration_ms": 1, "output": ""}},
			"result and after": {"result": ok, "after": {"sha256": "a" * 64}},
		}
		for case, kwargs in cases.items():
			with self.subTest(case=case):
				proposal = _proposal_in(CHANGE_STATUS_APPLYING, kind=CHANGE_KIND_COMMAND)
				state, modified = _state(proposal.name), _modified(proposal.name)
				with self.assertRaises(ValueError):
					transitions.finish(
						proposal.name,
						CHANGE_STATUS_APPLYING,
						CHANGE_STATUS_APPLIED,
						step="apply",
						actor=ACTOR,
						**kwargs,
					)
				self.assertNothingChanged(proposal.name, state, modified)

	def test_finish_with_wrong_expected_does_nothing(self):
		for (expected, new_status), step in FINISH_EDGES_EXPECTED.items():
			for current in (s for s in ALL_STATUSES if s != expected):
				with self.subTest(expected=expected, new_status=new_status, current=current):
					proposal = _proposal_in(current)
					state, modified = _state(proposal.name), _modified(proposal.name)
					self.assertIs(
						transitions.finish(
							proposal.name, expected, new_status, step=step, actor=ACTOR, reason="x"
						),
						False,
					)
					self.assertNothingChanged(proposal.name, state, modified)

	def test_finish_fields_only_git_keys_else_valueerror(self):
		self.assertEqual(transitions.STATE_FIELDS[-4:], GIT_FIELDS_EXPECTED)
		values = {
			"applied_branch": "develop",
			"applied_ahead_count": 3,
			"apply_commit_sha": "f" * 40,
			"undo_commit_sha": "9" * 40,
		}
		for key in GIT_FIELDS_EXPECTED:
			with self.subTest(key=key):
				proposal = _proposal_in(CHANGE_STATUS_APPLYING)
				transitions.finish(
					proposal.name,
					CHANGE_STATUS_APPLYING,
					CHANGE_STATUS_FAILED,
					step="fail",
					actor=ACTOR,
					fields={key: values[key]},
				)
				self.assertEqual(_state(proposal.name)[key], values[key])
		bad_fields = (
			{"change_status": CHANGE_STATUS_APPLIED},
			{"failure_reason": "x"},
			{"decided_by": "Guest"},
			{"finished_at": NOW},
			{"exit_code": 0},
			{"content_after": "x"},
			{"target_branch": "develop"},
			{"apply_commit_sha": "f" * 40, "approved_digest": "0" * 64},
			[("apply_commit_sha", "f" * 40)],
		)
		for fields in bad_fields:
			with self.subTest(fields=fields):
				proposal = _proposal_in(CHANGE_STATUS_APPLYING)
				state, modified = _state(proposal.name), _modified(proposal.name)
				with self.assertRaises(ValueError):
					transitions.finish(
						proposal.name,
						CHANGE_STATUS_APPLYING,
						CHANGE_STATUS_FAILED,
						step="fail",
						actor=ACTOR,
						fields=fields,
					)
				self.assertNothingChanged(proposal.name, state, modified)

	def test_command_results_stored(self):
		results = [
			{
				"args": ["migrate"],
				"exit_code": 0,
				"duration_ms": 1200,
				"timed_out": False,
				"output": "xong\n",
			},
			{"args": ["clear-cache"], "exit_code": None, "duration_ms": 0, "timed_out": True, "output": ""},
		]
		proposal = _proposal_in(CHANGE_STATUS_APPLYING)
		before = _state(proposal.name)
		self.assertIs(
			transitions.finish(
				proposal.name,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				step="apply",
				actor=ACTOR,
				command_results=results,
			),
			True,
		)
		state = _state(proposal.name)
		self.assertEqual(json.loads(state.command_results), results)
		self.assertEqual(
			state,
			{
				**before,
				"change_status": "Đã áp dụng",
				"finished_at": NOW,
				"command_results": state.command_results,
			},
		)
		self.assertEqual([row.change_step for row in _rows(proposal.name)], ["apply"])
		# Without `command_results` the field stays empty.
		other = _proposal_in(CHANGE_STATUS_APPLYING)
		transitions.finish(
			other.name, CHANGE_STATUS_APPLYING, CHANGE_STATUS_APPLIED, step="apply", actor=ACTOR
		)
		self.assertIsNone(_state(other.name).command_results)

	def test_command_results_refused_when_not_a_list(self):
		proposal = _proposal_in(CHANGE_STATUS_APPLYING)
		state, modified = _state(proposal.name), _modified(proposal.name)
		with self.assertRaises(ValueError):
			transitions.finish(
				proposal.name,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				step="apply",
				actor=ACTOR,
				command_results='[{"args": ["migrate"]}]',
			)
		self.assertNothingChanged(proposal.name, state, modified)

	def test_command_results_is_keyword_only(self):
		parameters = inspect.signature(transitions.finish).parameters
		self.assertEqual(
			[name for name, p in parameters.items() if p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD],
			["name", "expected", "new_status"],
		)
		self.assertIs(parameters["command_results"].kind, inspect.Parameter.KEYWORD_ONLY)
		self.assertIsNone(parameters["command_results"].default)
		results = [{"args": ["migrate"], "exit_code": 0, "duration_ms": 5, "timed_out": False, "output": ""}]
		proposal = _proposal_in(CHANGE_STATUS_APPLYING)
		state, modified = _state(proposal.name), _modified(proposal.name)
		with self.assertRaises(TypeError):
			transitions.finish(
				proposal.name,
				CHANGE_STATUS_APPLYING,
				CHANGE_STATUS_APPLIED,
				results,
				step="apply",
				actor=ACTOR,
			)
		self.assertNothingChanged(proposal.name, state, modified)
		transitions.finish(
			proposal.name,
			CHANGE_STATUS_APPLYING,
			CHANGE_STATUS_APPLIED,
			step="apply",
			actor=ACTOR,
			command_results=results,
		)
		self.assertEqual(json.loads(_state(proposal.name).command_results), results)


class TestPrepareNew(FrappeTestCase):
	def test_new_state_fields_cleared(self):
		new_values = {
			"command_results": '[{"args": ["migrate"], "exit_code": 0}]',
			"created_dirs": '["erp_ai/erp_ai/moi"]',
			"restart_status": "Đã gửi",
			"restart_sent_at": "2026-11-13 12:00:00",
		}
		for fieldname in new_values:
			self.assertIn(fieldname, transitions.STATE_FIELDS)
		doc = frappe.get_doc({"doctype": PROPOSAL_DOCTYPE, **STATE_VALUES, **new_values})
		transitions.prepare_new(doc)
		self.assertEqual(doc.change_status, "Chờ duyệt")
		for fieldname in new_values:
			with self.subTest(fieldname=fieldname):
				self.assertIsNone(doc.get(fieldname))


class TestRecordCommit(TransitionTestCase):
	def test_git_result_fields_add_created_dirs(self):
		self.assertEqual(transitions.GIT_RESULT_FIELDS, (*GIT_FIELDS_EXPECTED, "created_dirs"))

	def test_writes_git_fields_keeps_status_no_log_row(self):
		cases = {
			CHANGE_STATUS_APPLYING: {
				"apply_commit_sha": "c" * 40,
				"applied_branch": "main",
				"applied_ahead_count": 1,
				"created_dirs": ["erp_ai/erp_ai/moi", "erp_ai/erp_ai/moi/con"],
			},
			CHANGE_STATUS_UNDOING: {"undo_commit_sha": "e" * 40},
		}
		for status, fields in cases.items():
			with self.subTest(status=status):
				proposal = _proposal_in(status)
				before = _state(proposal.name)
				self.assertIs(transitions.record_commit(proposal.name, status, fields=fields), True)
				state = _state(proposal.name)
				stored = {**fields}
				if "created_dirs" in fields:
					self.assertEqual(json.loads(state.created_dirs), fields["created_dirs"])
					stored["created_dirs"] = state.created_dirs
				self.assertEqual(state, {**before, **stored})
				self.assertEqual(state.change_status, status)
				self.assertEqual(_rows(proposal.name), [])

	def test_wrong_status_returns_false(self):
		for expected in (CHANGE_STATUS_APPLYING, CHANGE_STATUS_UNDOING):
			for current in (s for s in ALL_STATUSES if s != expected):
				with self.subTest(expected=expected, current=current):
					proposal = _proposal_in(current)
					state, modified = _state(proposal.name), _modified(proposal.name)
					self.assertIs(
						transitions.record_commit(
							proposal.name, expected, fields={"apply_commit_sha": "c" * 40}
						),
						False,
					)
					self.assertNothingChanged(proposal.name, state, modified)

	def test_refuses_expected_outside_running_states_and_bad_fields(self):
		cases = [
			(status, {"apply_commit_sha": "c" * 40})
			for status in ALL_STATUSES
			if status not in (CHANGE_STATUS_APPLYING, CHANGE_STATUS_UNDOING)
		]
		cases += [
			(CHANGE_STATUS_APPLYING, {"change_status": CHANGE_STATUS_APPLIED}),
			(CHANGE_STATUS_APPLYING, {"command_results": "[]"}),
			(CHANGE_STATUS_APPLYING, {"created_dirs": "erp_ai/erp_ai/moi"}),
			(CHANGE_STATUS_APPLYING, [("apply_commit_sha", "c" * 40)]),
		]
		for expected, fields in cases:
			with self.subTest(expected=expected, fields=fields):
				proposal = _proposal_in(expected)
				state, modified = _state(proposal.name), _modified(proposal.name)
				with self.assertRaises(ValueError):
					transitions.record_commit(proposal.name, expected, fields=fields)
				self.assertNothingChanged(proposal.name, state, modified)

	def test_fields_is_keyword_only(self):
		with self.assertRaises(TypeError):
			transitions.record_commit("x", CHANGE_STATUS_APPLYING, {"apply_commit_sha": "c" * 40})


class TestTransitionInput(TransitionTestCase):
	def _calls(self, name, person=ACTOR):
		return {
			"approve": lambda: transitions.approve(name, person),
			"reject": lambda: transitions.reject(name, person),
			"request_undo": lambda: transitions.request_undo(name, person),
			"begin_apply": lambda: transitions.begin_apply(name),
			"finish": lambda: transitions.finish(
				name, CHANGE_STATUS_APPLYING, CHANGE_STATUS_FAILED, step="fail", actor=person
			),
		}

	def test_name_must_be_a_non_empty_string(self):
		proposal = make_change_proposal()
		for bad in ("", "  ", None, 7, proposal):
			for function, call in self._calls(bad).items():
				with self.subTest(name=bad, function=function), self.assertRaises(ValueError):
					call()

	def test_unknown_proposal_raises_does_not_exist(self):
		for name, shown in (("AICHG-99999999", "AICHG-99999999"), ("<b>x</b>", "&lt;b&gt;x&lt;/b&gt;")):
			for function, call in self._calls(name).items():
				with self.subTest(name=name, function=function):
					with self.assertRaises(frappe.DoesNotExistError) as caught:
						call()
					self.assertEqual(str(caught.exception), f"Không có đề xuất {shown}")

	def test_unknown_proposal_goes_through_frappe_throw(self):
		# Design 3.3: `frappe.throw(msg, DoesNotExistError)` so the sentence reaches the HTTP client.
		for function, call in self._calls("AICHG-99999999").items():
			with self.subTest(function=function), patch.object(frappe, "throw", wraps=frappe.throw) as throw:
				with self.assertRaises(frappe.DoesNotExistError):
					call()
				throw.assert_called_once_with("Không có đề xuất AICHG-99999999", frappe.DoesNotExistError)

	def test_user_and_actor_must_be_non_empty_strings(self):
		for bad in ("", "  ", None, 7):
			proposal = _proposal_in(CHANGE_STATUS_APPLYING)
			state, modified = _state(proposal.name), _modified(proposal.name)
			calls = self._calls(proposal.name, person=bad)
			del calls["begin_apply"]
			for function, call in calls.items():
				with self.subTest(person=bad, function=function), self.assertRaises(ValueError):
					call()
			self.assertNothingChanged(proposal.name, state, modified)


class TestLockBeforeWrite(TransitionTestCase):
	"""D-2: each transition reads the row with `for_update=True` before its `set_value(update_modified=True)`."""

	def test_each_transition_locks_the_row_before_writing(self):
		cases = (
			("approve", CHANGE_STATUS_PENDING, lambda name: transitions.approve(name, ACTOR)),
			("reject", CHANGE_STATUS_PENDING, lambda name: transitions.reject(name, ACTOR)),
			("request_undo", CHANGE_STATUS_APPLIED, lambda name: transitions.request_undo(name, ACTOR)),
			("begin_apply", CHANGE_STATUS_APPROVED, transitions.begin_apply),
			(
				"finish",
				CHANGE_STATUS_APPLYING,
				lambda name: transitions.finish(
					name, CHANGE_STATUS_APPLYING, CHANGE_STATUS_APPLIED, step="apply", actor=ACTOR
				),
			),
			(
				"record_commit",
				CHANGE_STATUS_UNDOING,
				lambda name: transitions.record_commit(
					name, CHANGE_STATUS_UNDOING, fields={"undo_commit_sha": "e" * 40}
				),
			),
		)
		for function, status, call in cases:
			with self.subTest(function=function):
				proposal = _proposal_in(status)
				db = Mock()
				with (
					patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value,
					patch.object(frappe.db, "set_value", wraps=frappe.db.set_value) as set_value,
				):
					db.attach_mock(get_value, "get_value")
					db.attach_mock(set_value, "set_value")
					call(proposal.name)
				names = [entry[0] for entry in db.mock_calls]
				self.assertIn("set_value", names)
				first_write = names.index("set_value")
				locks = [
					entry
					for entry in db.mock_calls[:first_write]
					if entry[0] == "get_value"
					and entry.args[:2] == (PROPOSAL_DOCTYPE, proposal.name)
					and entry.kwargs.get("for_update") is True
				]
				self.assertEqual(len(locks), 1, db.mock_calls[:first_write])
				writes = [entry for entry in db.mock_calls if entry[0] == "set_value"]
				self.assertEqual(len(writes), 1)
				self.assertEqual(writes[0].args[:2], (PROPOSAL_DOCTYPE, proposal.name))
				self.assertIs(writes[0].kwargs.get("update_modified"), True)


class TestEveryStepLogs(TransitionTestCase):
	def test_each_step_writes_exactly_one_change_row(self):
		errors = {
			"fail": "đang có thay đổi khác chạy, không lấy được khóa",
			"stale": "file đích đã đổi kể từ lúc đề xuất",
		}
		cases = (
			("propose", CHANGE_STATUS_PENDING, lambda name: transitions.log_step(name, "propose", ACTOR)),
			("approve", CHANGE_STATUS_PENDING, lambda name: transitions.approve(name, ACTOR)),
			("reject", CHANGE_STATUS_PENDING, lambda name: transitions.reject(name, ACTOR)),
			(
				"apply",
				CHANGE_STATUS_APPLYING,
				lambda name: transitions.finish(
					name, CHANGE_STATUS_APPLYING, CHANGE_STATUS_APPLIED, step="apply", actor=ACTOR
				),
			),
			(
				"fail",
				CHANGE_STATUS_APPROVED,
				lambda name: transitions.finish(
					name,
					CHANGE_STATUS_APPROVED,
					CHANGE_STATUS_FAILED,
					step="fail",
					actor=ACTOR,
					reason=errors["fail"],
				),
			),
			(
				"stale",
				CHANGE_STATUS_APPLYING,
				lambda name: transitions.finish(
					name,
					CHANGE_STATUS_APPLYING,
					CHANGE_STATUS_STALE,
					step="stale",
					actor=ACTOR,
					reason=errors["stale"],
				),
			),
			(
				"undo",
				CHANGE_STATUS_UNDOING,
				lambda name: transitions.finish(
					name, CHANGE_STATUS_UNDOING, CHANGE_STATUS_UNDONE, step="undo", actor=ACTOR
				),
			),
		)
		self.assertEqual(tuple(step for step, _status, _call in cases), CHANGE_STEPS)
		for step, status, call in cases:
			with self.subTest(step=step):
				proposal = _proposal_in(status)
				call(proposal.name)
				rows = _rows(proposal.name)
				self.assertEqual(len(rows), 1)
				self.assertIsNotNone(rows[0].creation)
				self.assertEqual(
					{key: rows[0][key] for key in ("change_step", "actor", "ticket", "run_id", "error")},
					{
						"change_step": step,
						"actor": ACTOR,
						"ticket": proposal.ticket,
						"run_id": proposal.run_id,
						"error": errors.get(step),
					},
				)
