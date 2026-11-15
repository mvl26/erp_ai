import copy
import json
from unittest.mock import patch

import frappe
import frappe.client
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import redact, run_log
from erp_ai.agent.agent_write_guard import AGENT_WRITE_FLAG
from erp_ai.agent.tools.site_api import SCRUBBED_VALUE, SECRET_FIELDS
from erp_ai.constants import AGENT_USER, HELPDESK_AGENT_ROLE, LOG_DOCTYPE, ROLE_AGENT
from erp_ai.erp_ai_agent.doctype.erp_ai_log.erp_ai_log import ERPAILog
from erp_ai.test_utils import make_change_proposal, make_log_entry

AI_USER = "erpai-test-run-log-agent@example.com"
HD_AGENT_USER = "erpai-test-run-log-hd-agent@example.com"
KEYS_TRIED = [
	{"label": "ERPAI-TEST-k1", "outcome": "rate_limit"},
	{"label": "ERPAI-TEST-k2", "outcome": "ok"},
]
TOOLS_CALLED = ["get_ticket", "set_classification"]
ACTIONS = [{"tool": "set_classification", "doctype": "HD Ticket", "name": "1", "ok": True}]
# FEAT-004 design 2.5 / ADR-012 QĐ 6: the closed set of proposal steps and the single change trigger.
CHANGE_STEP_VALUES = ("propose", "approve", "reject", "apply", "fail", "stale", "undo")
CHANGE_TRIGGER = "change_action"
OLD_ENTRY_TYPES = ("classify", "reason", "skip")
MISSING = object()
# ADR-023 QĐ 5 (M5): the ERP AI Log hooks that refuse the agent account outside `run_log.write_entry`.
GUARDED_HOOKS = ("before_insert", "validate", "on_trash", "before_rename")
# As frappe.model.rename_doc passes them: old name, new name, merge.
HOOK_ARGUMENTS = {"before_rename": ("old-name", "new-name", False)}
REFUSAL = "Tài khoản agent không được ghi"
SAVEPOINT = "erp_ai_run_log_guard_path"
# The DocType name spelled with a JSON escape, as a model could send it through call_method.
LOG_ESCAPED = "ERP AI \\u004cog"


def _make_user(email, role):
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)


class TestRunLog(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		_make_user(AI_USER, ROLE_AGENT)
		_make_user(HD_AGENT_USER, HELPDESK_AGENT_ROLE)

	def test_write_entry_serializes_json_and_requires_agent_role(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			run_id="ERPAI-TEST-run",
			entry_type="reason",
			trigger="comment_mention",
			turn=1,
			model="fake-model",
			input_tokens=7,
			cost_usd=0.000123,
			keys_tried=KEYS_TRIED,
			tools_called=TOOLS_CALLED,
			actions=ACTIONS,
			value_before={"priority": "Low"},
			value_after={"priority": "High"},
			error="Không phân loại được",
		)

		doc = frappe.get_doc(LOG_DOCTYPE, name)
		self.assertRegex(name, r"^[0-9a-z]{10}$")
		self.assertEqual(doc.owner, AI_USER)
		self.assertEqual(json.loads(doc.keys_tried), KEYS_TRIED)
		self.assertEqual(json.loads(doc.tools_called), TOOLS_CALLED)
		self.assertEqual(json.loads(doc.actions), ACTIONS)
		self.assertEqual(json.loads(doc.value_before), {"priority": "Low"})
		self.assertEqual(json.loads(doc.value_after), {"priority": "High"})
		self.assertEqual((doc.turn, doc.input_tokens, doc.cost_usd), (1, 7, 0.000123))
		self.assertEqual(doc.error, "Không phân loại được")

		frappe.set_user(HD_AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			run_log.write_entry(
				run_id="ERPAI-TEST-run", entry_type="classify", trigger="ticket_insert", turn=0
			)

	def test_write_entry_keeps_string_values_and_non_ascii_json(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			run_id="ERPAI-TEST-run",
			entry_type="skip",
			trigger="ticket_insert",
			turn=0,
			keys_tried='[{"a": 1}]',
			actions=[{"note": "Không phân loại"}],
		)

		doc = frappe.get_doc(LOG_DOCTYPE, name)
		self.assertEqual(doc.keys_tried, '[{"a": 1}]')
		self.assertIn("Không phân loại", doc.actions)

	def test_write_entry_rejects_missing_or_unknown_entry_type(self):
		frappe.set_user(AI_USER)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", trigger="ticket_insert", turn=0)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="bogus", trigger="ticket_insert", turn=0)

	def test_write_entry_rejects_missing_or_unknown_trigger(self):
		frappe.set_user(AI_USER)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", turn=0)
		with self.assertRaises(ValueError):
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="bogus", turn=0)

	def test_write_entry_ignores_doctype_override(self):
		frappe.set_user(AI_USER)
		name = run_log.write_entry(
			doctype="User", run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0
		)

		self.assertTrue(frappe.db.exists(LOG_DOCTYPE, name))

	def test_write_entry_commits_outside_tests(self):
		frappe.set_user(AI_USER)
		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		with patch.object(frappe.db, "commit") as commit:
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0)
		commit.assert_called_once_with()

	def test_write_entry_does_not_commit_in_tests(self):
		frappe.set_user(AI_USER)
		with patch.object(frappe.db, "commit") as commit:
			run_log.write_entry(run_id="ERPAI-TEST-run", entry_type="skip", trigger="ticket_insert", turn=0)
		commit.assert_not_called()

	def _change_fields(self, proposal, **overrides):
		fields = {
			"ticket": proposal.ticket,
			"run_id": proposal.run_id,
			"entry_type": "change",
			"trigger": CHANGE_TRIGGER,
			"change_step": "approve",
			"actor": HD_AGENT_USER,
			"change_proposal": proposal.name,
		}
		fields.update(overrides)
		return {key: value for key, value in fields.items() if value is not MISSING}

	def test_change_entry_requires_step_actor_proposal_and_trigger(self):
		proposal = make_change_proposal()
		frappe.set_user(HD_AGENT_USER)
		log_count = frappe.db.count(LOG_DOCTYPE)
		bad_cases = {
			"trigger missing": {"trigger": MISSING},
			"trigger ticket_insert": {"trigger": "ticket_insert"},
			"trigger comment_mention": {"trigger": "comment_mention"},
			"trigger unknown": {"trigger": "bogus"},
			"change_step missing": {"change_step": MISSING},
			"change_step empty": {"change_step": ""},
			"change_step unknown": {"change_step": "commit"},
			"change_step wrong case": {"change_step": "Apply"},
			"actor missing": {"actor": MISSING},
			"actor empty": {"actor": ""},
			"actor blank": {"actor": "   "},
			"actor not a string": {"actor": ["Administrator"]},
			"change_proposal missing": {"change_proposal": MISSING},
			"change_proposal empty": {"change_proposal": ""},
			"change_proposal not a string": {"change_proposal": 7},
		}
		for case, overrides in bad_cases.items():
			with self.subTest(case=case), self.assertRaises(ValueError):
				run_log.write_entry(**self._change_fields(proposal, **overrides))
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), log_count)

		for entry_type in OLD_ENTRY_TYPES:
			with self.subTest(entry_type=entry_type), self.assertRaises(ValueError):
				run_log.write_entry(
					run_id="ERPAI-TEST-run", entry_type=entry_type, trigger=CHANGE_TRIGGER, turn=0
				)

		for step in CHANGE_STEP_VALUES:
			with self.subTest(step=step):
				name = run_log.write_entry(**self._change_fields(proposal, change_step=step))
				row = frappe.db.get_value(
					LOG_DOCTYPE,
					name,
					["entry_type", "trigger", "change_step", "actor", "change_proposal", "ticket"],
					as_dict=True,
				)
				self.assertEqual(
					row,
					{
						"entry_type": "change",
						"trigger": "change_action",
						"change_step": step,
						"actor": HD_AGENT_USER,
						"change_proposal": proposal.name,
						"ticket": proposal.ticket,
					},
				)

	def test_change_entry_keeps_git_keys_of_apply_and_undo_rows(self):
		proposal = make_change_proposal()
		before = {"sha256": "a" * 64, "head": "1" * 40}
		after = {"sha256": None, "commit": "2" * 40, "branch": "develop"}
		for step in ("apply", "undo"):
			with self.subTest(step=step):
				name = run_log.write_entry(
					**self._change_fields(proposal, change_step=step, value_before=before, value_after=after)
				)
				doc = frappe.get_doc(LOG_DOCTYPE, name)
				self.assertEqual(json.loads(doc.value_before), before)
				self.assertEqual(json.loads(doc.value_after), after)

	def test_change_entry_bypasses_permission_but_other_types_do_not(self):
		proposal = make_change_proposal()
		frappe.set_user(HD_AGENT_USER)
		self.assertFalse(frappe.has_permission(LOG_DOCTYPE, "create"))

		name = run_log.write_entry(**self._change_fields(proposal, change_step="reject"))

		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "owner"), HD_AGENT_USER)
		for entry_type in OLD_ENTRY_TYPES:
			with self.subTest(entry_type=entry_type), self.assertRaises(frappe.PermissionError):
				run_log.write_entry(
					run_id="ERPAI-TEST-run", entry_type=entry_type, trigger="ticket_insert", turn=0
				)

	def test_log_change_fields_match_design(self):
		meta = frappe.get_meta(LOG_DOCTYPE)
		self.assertEqual(
			meta.get_field("entry_type").options.split("\n"),
			["classify", "reason", "skip", "change", "bot_action"],
		)
		self.assertEqual(
			meta.get_field("trigger").options.split("\n"),
			["ticket_insert", "comment_mention", "change_action", "setting_save", "scheduled_job"],
		)
		expected = {
			"change_proposal": ("Link", "ERP AI Change Proposal"),
			"change_step": ("Select", "propose\napprove\nreject\napply\nfail\nstale\nundo"),
			"actor": ("Link", "User"),
		}
		for fieldname, (fieldtype, options) in expected.items():
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field)
				self.assertEqual((field.fieldtype, field.options, field.read_only), (fieldtype, options, 1))

	def test_make_log_entry_returns_name_of_saved_log(self):
		name = make_log_entry(model="fake-model")

		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "trigger"), "ticket_insert")
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "model"), "fake-model")
		self.assertTrue(frappe.db.get_value(LOG_DOCTYPE, name, "run_id"))


class TestRunLogAgentWriteGuard(FrappeTestCase):
	"""M5 of ADR-023 QĐ 5: the agent account writes ERP AI Log only through `run_log.write_entry`."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.flags.pop, AGENT_WRITE_FLAG, None)
		frappe.set_user("Administrator")
		frappe.flags.pop(AGENT_WRITE_FLAG, None)
		if not frappe.db.exists("User", AGENT_USER):
			raise AssertionError(f"{AGENT_USER} does not exist on this site")
		self.log_name = make_log_entry(model="ERPAI-TEST-guard")

	def _snapshot(self) -> tuple:
		row = frappe.db.sql(f"select * from `tab{LOG_DOCTYPE}` where name=%s", self.log_name, as_dict=True)
		return frappe.db.count(LOG_DOCTYPE), tuple(sorted(row[0].items()))

	def _assert_refused(self, write):
		"""Run `write` as the agent: refused by the guard, the log table unchanged; undone for the next path."""
		before = self._snapshot()
		frappe.db.savepoint(SAVEPOINT)
		frappe.set_user(AGENT_USER)
		try:
			with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
				write()
			frappe.set_user("Administrator")
			self.assertEqual(self._snapshot(), before)
		finally:
			frappe.set_user("Administrator")
			frappe.db.rollback(save_point=SAVEPOINT)

	def test_every_guarded_hook_refuses_the_agent(self):
		doc = frappe.get_doc(LOG_DOCTYPE, self.log_name)
		frappe.set_user(AGENT_USER)
		for hook in GUARDED_HOOKS:
			with self.subTest(hook=hook), self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
				doc.run_method(hook, *HOOK_ARGUMENTS.get(hook, ()))

	def test_agent_cannot_write_log_outside_write_entry(self):
		def save_log():
			doc = frappe.get_doc(LOG_DOCTYPE, self.log_name)
			doc.error = "forged"
			doc.save(ignore_permissions=True)

		new_log = {"run_id": "ERPAI-TEST-forged", "entry_type": "skip", "trigger": "ticket_insert", "turn": 0}
		paths = {
			"insert": lambda: frappe.get_doc({"doctype": LOG_DOCTYPE, **new_log}).insert(
				ignore_permissions=True
			),
			"save": save_log,
			"delete": lambda: frappe.delete_doc(LOG_DOCTYPE, self.log_name, ignore_permissions=True),
			"client.insert JSON string": lambda: frappe.client.insert(
				json.dumps(new_log)[:-1] + f', "doctype": "{LOG_ESCAPED}"}}'
			),
			"forged flag in doc": lambda: frappe.client.insert(
				{"doctype": LOG_DOCTYPE, "flags": {AGENT_WRITE_FLAG: True}, AGENT_WRITE_FLAG: 1, **new_log}
			),
		}
		for path, write in paths.items():
			with self.subTest(path=path):
				self._assert_refused(write)

	def test_write_entry_still_works_under_agent_account(self):
		proposal = make_change_proposal()
		before = frappe.db.count(LOG_DOCTYPE)
		frappe.set_user(AGENT_USER)
		names = [
			run_log.write_entry(
				run_id="ERPAI-TEST-guard", entry_type="reason", trigger="comment_mention", turn=1
			),
			run_log.write_entry(
				ticket=proposal.ticket,
				run_id=proposal.run_id,
				entry_type="change",
				trigger=CHANGE_TRIGGER,
				change_step="propose",
				actor=AGENT_USER,
				change_proposal=proposal.name,
			),
		]

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), before + 2)
		for name in names:
			self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "owner"), AGENT_USER)

	def test_flag_is_off_after_write_entry(self):
		seen = []

		def spy(doc):
			seen.append(frappe.flags.get(AGENT_WRITE_FLAG))

		frappe.set_user(AGENT_USER)
		with patch.object(ERPAILog, "before_insert", spy, create=True):
			run_log.write_entry(run_id="ERPAI-TEST-guard", entry_type="skip", trigger="ticket_insert", turn=0)
		self.assertEqual(seen, [True])
		self.assertIsNone(frappe.flags.get(AGENT_WRITE_FLAG))

		before = frappe.db.count(LOG_DOCTYPE)
		with self.assertRaises(frappe.LinkValidationError):
			run_log.write_entry(
				ticket="ERPAI-TEST-missing-ticket",
				run_id="ERPAI-TEST-guard",
				entry_type="skip",
				trigger="ticket_insert",
				turn=0,
			)
		self.assertIsNone(frappe.flags.get(AGENT_WRITE_FLAG))
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), before)
		frappe.set_user("Administrator")
		self._assert_refused(
			lambda: frappe.get_doc(
				{
					"doctype": LOG_DOCTYPE,
					"run_id": "ERPAI-TEST-guard",
					"entry_type": "skip",
					"trigger": "ticket_insert",
				}
			).insert(ignore_permissions=True)
		)


# U3 3.1 (ADR-033 QĐ 5): the one action-entry shape, in this order.
ACTION_KEYS_EXPECTED = ("tool", "doctype", "name", "ok", "value_before", "value_after", "instructor")
# A core DocType with a `Password` field whose name holds no secret word: only the meta can mask it.
PASSWORD_DOCTYPE = "Google Calendar"
PASSWORD_FIELD = "authorization_code"
BEARER_TEXT = "Gọi lại với Authorization: Bearer ERPAITESTbearer12345 nhé"


class TestActionEntry(FrappeTestCase):
	def test_shape_has_all_keys_in_order(self):
		self.assertEqual(run_log.ACTION_KEYS, ACTION_KEYS_EXPECTED)
		self.assertEqual(run_log.ACTION_DOCTYPE_MAX, 80)
		before, after = {"priority": "Low"}, {"priority": "High"}
		entry = run_log.action_entry(
			"api_update_record",
			"HD Ticket",
			"ERPAI-TEST-ticket-7",
			True,
			reason="ERPAI-TEST-ignored-when-ok",
			value_before=before,
			value_after=after,
			instructor="erpai-test-instructor@example.com",
			rule="ERPAI-TEST-rule-3",
		)

		self.assertEqual(tuple(entry), (*ACTION_KEYS_EXPECTED, "rule"))
		self.assertEqual(
			list(entry.values()),
			[
				"api_update_record",
				"HD Ticket",
				"ERPAI-TEST-ticket-7",
				True,
				{"priority": "Low"},
				{"priority": "High"},
				"erpai-test-instructor@example.com",
				"ERPAI-TEST-rule-3",
			],
		)
		self.assertIsNot(entry["value_before"], before)

		bare = run_log.action_entry("route_ticket", None, None, True, rule="")
		self.assertEqual(tuple(bare), ACTION_KEYS_EXPECTED)
		self.assertEqual(list(bare.values()), ["route_ticket", None, None, True, None, None, None])

		long_doctype = "D" * 79 + "EF"
		cut = run_log.action_entry("api_create_record", long_doctype, "ERPAI-TEST-new", True)
		self.assertEqual(cut["doctype"], "D" * 79 + "E")

	def test_refused_entry_keeps_reason(self):
		self.assertEqual(run_log.NO_REASON, "tool không nêu lý do")
		refused = run_log.action_entry(
			"api_delete_record",
			"ToDo",
			"ERPAI-TEST-todo-1",
			False,
			reason="ERPAI-TEST-not-permitted",
			instructor="erpai-test-boss@example.com",
			rule="ERPAI-TEST-rule-9",
		)
		self.assertEqual(tuple(refused), (*ACTION_KEYS_EXPECTED, "reason", "rule"))
		self.assertEqual(
			list(refused.values()),
			[
				"api_delete_record",
				"ToDo",
				"ERPAI-TEST-todo-1",
				False,
				None,
				None,
				"erpai-test-boss@example.com",
				"ERPAI-TEST-not-permitted",
				"ERPAI-TEST-rule-9",
			],
		)
		for blank in (None, "", "   "):
			with self.subTest(reason=blank):
				entry = run_log.action_entry(
					"api_delete_record", "ToDo", "ERPAI-TEST-todo-2", False, reason=blank
				)
				self.assertEqual(tuple(entry), (*ACTION_KEYS_EXPECTED, "reason"))
				self.assertEqual(entry["reason"], run_log.NO_REASON)

	def test_refused_reason_secret_masked(self):
		reason = "ERPAI-TEST lỗi: password=ERPAI-TEST-p9 và Bearer ERPAITESTbearer12345"
		entry = run_log.action_entry(
			"api_update_record", "ToDo", "ERPAI-TEST-todo-3", False, reason=reason, rule="ERPAI-TEST-rule-9"
		)
		self.assertEqual(entry["reason"], redact.redact_secrets(reason))
		self.assertIn(redact.MASK, entry["reason"])
		self.assertNotIn("ERPAI-TEST-p9", entry["reason"])
		self.assertNotIn("ERPAITESTbearer12345", entry["reason"])
		with self.subTest(reason="khóa sk-ant-FAKE0000 hết hạn"):
			key_entry = run_log.action_entry(
				"api_update_record", "ToDo", "ERPAI-TEST-todo-3", False, reason="khóa sk-ant-FAKE0000 hết hạn"
			)
			self.assertEqual(key_entry["reason"], "khóa [đã che] hết hạn")
		with self.subTest(rule="ERPAI-TEST-rule-9"):
			self.assertEqual(entry["rule"], "ERPAI-TEST-rule-9")

	def test_two_mask_words_have_distinct_meanings(self):
		self.assertEqual(run_log.SECRET_MASK, "[đã ẩn]")
		self.assertEqual(SCRUBBED_VALUE, run_log.SECRET_MASK)
		self.assertEqual(redact.MASK, "[đã che]")
		self.assertNotEqual(run_log.SECRET_MASK, redact.MASK)
		entry = run_log.action_entry(
			"api_update_record",
			"ToDo",
			"ERPAI-TEST-todo-4",
			True,
			value_after={"api_key": "ERPAI-TEST-k", "note": BEARER_TEXT},
		)
		self.assertEqual(entry["value_after"]["api_key"], run_log.SECRET_MASK)
		self.assertIn(redact.MASK, entry["value_after"]["note"])
		self.assertNotIn(run_log.SECRET_MASK, entry["value_after"]["note"])

	def test_masks_secret_keys_password_fields_and_secret_text(self):
		self.assertEqual(run_log.SECRET_MASK, "[đã ẩn]")
		mask = run_log.SECRET_MASK
		value_before = {
			"api_key": "ERPAI-TEST-k1",
			"subject": "ERPAI-TEST-plain-subject",
			"nested": {
				"new_password": "ERPAI-TEST-p2",
				"rows": [{"Mật khẩu": "ERPAI-TEST-m3", "note": BEARER_TEXT}, "ERPAI-TEST-leaf", 42],
			},
		}
		value_after = {field: f"ERPAI-TEST-{field}" for field in sorted(SECRET_FIELDS)}
		value_after["count"] = 5
		originals = copy.deepcopy((value_before, value_after))

		entry = run_log.action_entry(
			"api_update_record",
			"User",
			"ERPAI-TEST-user",
			True,
			value_before=value_before,
			value_after=value_after,
		)

		self.assertEqual(
			entry["value_before"],
			{
				"api_key": mask,
				"subject": "ERPAI-TEST-plain-subject",
				"nested": {
					"new_password": mask,
					"rows": [
						{"Mật khẩu": mask, "note": redact.redact_secrets(BEARER_TEXT)},
						"ERPAI-TEST-leaf",
						42,
					],
				},
			},
		)
		self.assertNotIn("ERPAITESTbearer12345", entry["value_before"]["nested"]["rows"][0]["note"])
		self.assertEqual(entry["value_after"], {**{field: mask for field in SECRET_FIELDS}, "count": 5})
		self.assertEqual((value_before, value_after), originals)

		values = {PASSWORD_FIELD: "ERPAI-TEST-code-4", "calendar_name": "ERPAI-TEST-cal"}
		on_meta = run_log.action_entry(
			"api_update_record", PASSWORD_DOCTYPE, "ERPAI-TEST-cal", True, value_after=values
		)
		self.assertEqual(on_meta["value_after"], {PASSWORD_FIELD: mask, "calendar_name": "ERPAI-TEST-cal"})
		not_a_doctype = run_log.action_entry(
			"api_update_record", "ERPAI-TEST-no-such-doctype", "x", True, value_before=values
		)
		self.assertEqual(not_a_doctype["value_before"], values)

	def test_rejects_blank_tool_non_bool_ok_non_dict_values(self):
		cases = [
			{"tool": ""},
			{"tool": "   "},
			{"tool": None},
			{"tool": 7},
			{"ok": 1},
			{"ok": "true"},
			{"ok": None},
			{"value_before": ["ERPAI-TEST-a"]},
			{"value_before": "ERPAI-TEST-b"},
			{"value_after": ("ERPAI-TEST-c",)},
			{"value_after": 0},
		]
		for case in cases:
			arguments = {"tool": "api_update_record", "ok": True, **case}
			with self.subTest(**{key: repr(value) for key, value in case.items()}):
				with self.assertRaises(ValueError):
					run_log.action_entry(
						arguments.pop("tool"), "ToDo", "ERPAI-TEST-todo", arguments.pop("ok"), **arguments
					)


BOT_ACTION_ENTRY = {
	"tool": "permission_switch",
	"doctype": "ERP AI Setting",
	"name": "ERP AI Setting",
	"ok": True,
	"value_before": {"a": 0},
	"value_after": {"a": 1},
	"instructor": "Administrator",
}


class _RollbackCase(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")


class TestWriteEntry(_RollbackCase):
	def test_every_row_gets_site_environment(self):
		for entry_type, trigger in (("reason", "comment_mention"), ("skip", "ticket_insert")):
			with (
				self.subTest(entry_type=entry_type),
				patch("erp_ai.agent.policy.site_environment", return_value="test"),
			):
				name = run_log.write_entry(run_id="ERPAI-TEST-env", entry_type=entry_type, trigger=trigger)
				self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "site_environment"), "test")
		with patch("erp_ai.agent.policy.site_environment", return_value="test"):
			name = run_log.write_entry(
				run_id="ERPAI-TEST-env",
				entry_type="reason",
				trigger="comment_mention",
				site_environment="production",
			)
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "site_environment"), "production")


class TestBotAction(_RollbackCase):
	def _write(self, **fields):
		values = {
			"run_id": "ERPAI-TEST-bot",
			"entry_type": "bot_action",
			"trigger": "setting_save",
			"actions": [BOT_ACTION_ENTRY],
			**fields,
		}
		return run_log.write_entry(**values)

	def test_bot_action_needs_known_trigger_actions_and_zero_cost(self):
		self.assertEqual(run_log.ENTRY_TYPE_BOT_ACTION, "bot_action")
		self.assertEqual(run_log.ENTRY_TYPES, ("classify", "reason", "skip", "change", "bot_action"))
		self.assertEqual(run_log.TRIGGER_SETTING_SAVE, "setting_save")
		self.assertEqual(run_log.TRIGGER_SCHEDULED_JOB, "scheduled_job")
		self.assertEqual(run_log.BOT_ACTION_TRIGGERS, ("setting_save", "scheduled_job"))
		self.assertEqual(run_log.TOOL_PERMISSION_SWITCH, "permission_switch")
		bad = {
			"trigger ticket_insert": {"trigger": "ticket_insert"},
			"trigger change_action": {"trigger": "change_action"},
			"trigger missing": {"trigger": None},
			"actions missing": {"actions": None},
			"actions empty": {"actions": []},
			"actions not a list": {"actions": "x"},
			"cost not zero": {"cost_usd": 0.5},
		}
		before = frappe.db.count(LOG_DOCTYPE)
		for case, change in bad.items():
			with self.subTest(case=case), self.assertRaises(ValueError):
				self._write(**change)
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), before)
		for trigger in run_log.BOT_ACTION_TRIGGERS:
			with self.subTest(trigger=trigger):
				name = self._write(trigger=trigger)
				self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, name, "cost_usd"), 0)
		self.assertEqual(frappe.db.count(LOG_DOCTYPE), before + 2)
		with self.assertRaises(ValueError):
			self._write(entry_type="classify", trigger="setting_save")
