import hashlib
import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import transitions
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

# Design 2.1 state group, written out by hand (11 fields + 4 git fields of round 1).
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
	"failure_reason",
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
