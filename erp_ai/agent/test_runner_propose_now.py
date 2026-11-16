"""CHG-007 T2 (AC-1, AC-2, AC-4, AC-5): the runner tells the bot to propose a code change in the same run.

The first message of a ticket-creation or @ai run carries TASK_PROPOSE_NOW when the run's grant has the
proposal tools and the act-now block; every other run keeps its first message byte for byte. All of it is
seen through the fake model gateway.
"""

import json
from unittest.mock import patch

import frappe

from erp_ai.agent import authority, prompts, runner
from erp_ai.agent.prompts import ACT_NOW_BLOCK, CHANGE_TOOLS_BLOCK, TASK_PROPOSE_NOW
from erp_ai.agent.test_agent_runner import (
	BA_NOTE_TEXT,
	INSTRUCTOR,
	PREFIX,
	SANDBOX_APP,
	SANDBOX_BEFORE,
	SANDBOX_REL,
	GuidanceTestBase,
	ba_note_call,
	make_instructor,
	requester_message,
	tool_turn,
	tool_use,
)
from erp_ai.agent.tools import write_ticket
from erp_ai.constants import CHANGE_STATUS_PENDING, LOG_DOCTYPE, PROPOSAL_DOCTYPE
from erp_ai.test_utils import GitSandbox, make_model_result, pin_agent_roles, set_agent_settings

PROPOSE_TOOLS = ["propose_file_change", "propose_new_file", "propose_bench_command"]
CLASSIFY_C_85 = make_model_result(
	text=json.dumps({"dau_muc": "C", "do_tin_cay": "Cao", "do_tin_cay_pct": 85, "ly_do": "x"})
)


def hint_count(message):
	return message.count(TASK_PROPOSE_NOW)


class ProposeNowBase(GuidanceTestBase):
	"""Settings like site miyano: L3, code change and act-now on, threshold 10, one allowed app."""

	def setUp(self):
		super().setUp()
		self.sandbox = GitSandbox(self, apps=(SANDBOX_APP,), erp_ai_worktree=None)
		self.sandbox.commit_file(SANDBOX_APP, SANDBOX_REL, SANDBOX_BEFORE)
		set_agent_settings(
			permission_level="L3",
			level_cap_c="L3",
			act_now_enabled=1,
			code_change_enabled=1,
			code_change_apps=SANDBOX_APP,
			confidence_threshold=10,
		)
		# the ticket's own classification, from this run's classify row (the gate of the BA note reads it too)
		self.latest_classification.side_effect = self.real_latest_classification
		# every call of the first message is kept: its arguments and the text it built
		built = patch.object(runner, "build_initial_message", wraps=prompts.build_initial_message)
		self.build = built.start()
		self.addCleanup(built.stop)

	def _owner_is_instructor(self):
		"""The ticket's owner holds the instructor role: a run that reads its owner finds an instructor."""
		make_instructor(self)
		frappe.db.set_value("HD Ticket", self.ticket.name, "owner", INSTRUCTOR, update_modified=False)

	def _reason_calls(self):
		return [call for call in self.gateway.calls if call["task"] == "reason"]

	def _first_message(self, call=None):
		return (call or self._reason_calls()[0])["messages"][0]["content"]

	def _without_the_hint(self):
		"""The first message the run built is what `propose_now=False` builds: no hint, nothing else changed."""
		(call,) = self.build.call_args_list
		self.assertNotIn(TASK_PROPOSE_NOW, self._first_message())
		baseline = prompts.build_initial_message(*call.args, **{**call.kwargs, "propose_now": False})
		self.assertEqual(self._first_message(), baseline)
		return call


class TestProposeNowGrant(ProposeNowBase):
	def test_ticket_insert_c_85_owner_instructor_gets_tools_blocks_and_the_hint(self):
		self._owner_is_instructor()
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		self._run("ticket_insert")

		(call,) = self._reason_calls()
		names = [tool["name"] for tool in call["tools"]]
		for name in PROPOSE_TOOLS:
			self.assertIn(name, names)
		system = call["system"][0]["text"]
		self.assertIn(CHANGE_TOOLS_BLOCK, system)
		self.assertIn(ACT_NOW_BLOCK, system)
		message = self._first_message(call)
		self.assertEqual(hint_count(message), 1)
		# the C ticket keeps its BA note line, the new line stands after it
		self.assertIn(prompts.TASK_CATEGORY_C, message)
		self.assertLess(message.index(prompts.TASK_CATEGORY_C), message.index(TASK_PROPOSE_NOW))
		self.assertTrue(self.build.call_args.kwargs["propose_now"])

	def test_owner_without_the_role_gets_no_propose_tool_and_no_hint(self):
		# the owner of the test ticket is Administrator, which never carries authority
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		self._run("ticket_insert")

		(call,) = self._reason_calls()
		names = [tool["name"] for tool in call["tools"]]
		self.assertFalse(set(PROPOSE_TOOLS) & set(names))
		self.assertEqual(hint_count(self._first_message(call)), 0)
		self.assertFalse(self.build.call_args.kwargs["propose_now"])

	def test_at_mention_with_an_instructor_gets_the_hint(self):
		# the @ai run reads the same grant: tools, act-now block, then the hint
		self._owner_is_instructor()
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		with patch.object(authority, "run_instructor", return_value=INSTRUCTOR):
			self._run("comment_mention")

		(call,) = self._reason_calls()
		self.assertTrue(set(PROPOSE_TOOLS) <= {tool["name"] for tool in call["tools"]})
		self.assertEqual(hint_count(self._first_message(call)), 1)


class TestProposeNowAbsent(ProposeNowBase):
	"""AC-2, AC-4: outside the condition the first message is the one of before."""

	def setUp(self):
		super().setUp()
		self._owner_is_instructor()

	def test_act_now_off(self):
		set_agent_settings(act_now_enabled=0)
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		self._run("ticket_insert")

		(call,) = self._reason_calls()
		self.assertNotIn(ACT_NOW_BLOCK, call["system"][0]["text"])
		self._without_the_hint()

	def test_below_threshold(self):
		# act-now is off, so the threshold holds: 85 is under 90
		set_agent_settings(act_now_enabled=0, confidence_threshold=90)
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		self._run("ticket_insert")

		self._without_the_hint()

	def test_change_action_run(self):
		# the tools and the block are granted to this run, the trigger is not one the hint is for
		self.latest_classification.side_effect = None
		self.latest_classification.return_value = ("C", 85)
		self.gateway.results = [make_model_result()]
		self._run("change_action")

		(call,) = self._reason_calls()
		self.assertTrue(set(PROPOSE_TOOLS) <= {tool["name"] for tool in call["tools"]})
		self.assertIn(ACT_NOW_BLOCK, call["system"][0]["text"])
		self._without_the_hint()

	def test_requester_reply_run(self):
		self.latest_classification.side_effect = None
		self.latest_classification.return_value = ("C", 85)
		requester = f"{PREFIX.lower()}requester@example.com"
		frappe.db.set_value("HD Ticket", self.ticket.name, "raised_by", requester, update_modified=False)
		communication = requester_message(
			self.ticket.name, frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-30)
		)
		self.gateway.results = [make_model_result()]
		runner.run_for_ticket(self.ticket.name, "requester_reply", communication_name=communication)

		(call,) = self._reason_calls()
		self.assertTrue(set(PROPOSE_TOOLS) <= {tool["name"] for tool in call["tools"]})
		self._without_the_hint()

	def test_kb_draft_run(self):
		pin_agent_roles(self)
		set_agent_settings(kb_draft_enabled=1)
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{
				"status": "Resolved",
				"status_category": "Resolved",
				"resolution_details": f"<p>{PREFIX}đã cấu hình lại máy in</p>",
			},
			update_modified=False,
		)
		self.gateway.results = [make_model_result()]
		runner.run_for_ticket(self.ticket.name, "kb_draft")

		(call,) = self._reason_calls()
		self.assertFalse(set(PROPOSE_TOOLS) & {tool["name"] for tool in call["tools"]})
		self._without_the_hint()


class TestProposeNowEndToEnd(ProposeNowBase):
	"""AC-5: the run proposes once, nothing is written, and words in the ticket approve nothing."""

	def _proposals(self):
		return frappe.get_all(
			PROPOSAL_DOCTYPE, filters={"ticket": self.ticket.name}, fields=["name", "change_status"]
		)

	def _ba_notes(self):
		return frappe.get_all(
			"Comment",
			filters={
				**authority.ticket_comment_filters(self.ticket.name),
				"content": ["like", f"{write_ticket.BA_NOTE_MARKER}%"],
			},
			pluck="content",
		)

	def test_the_bot_proposes_once_and_a_comment_does_not_approve_it(self):
		self._owner_is_instructor()
		propose = tool_use(
			"toolu_p",
			"propose_file_change",
			path=f"{SANDBOX_APP}/{SANDBOX_REL}",
			find=["x = 1"],
			replace=["x = 2"],
			reason="r",
		)
		self.gateway.results = [
			CLASSIFY_C_85,
			tool_turn(propose, ba_note_call("toolu_b")),
			make_model_result(),
		]
		with patch.object(frappe, "enqueue") as enqueue:
			self._run("ticket_insert")

		self.assertEqual(hint_count(self._first_message()), 1)
		(proposal,) = self._proposals()
		self.assertEqual(proposal.change_status, CHANGE_STATUS_PENDING)
		(change,) = frappe.get_all(
			LOG_DOCTYPE,
			filters={"ticket": self.ticket.name, "entry_type": "change", "change_step": "propose"},
			fields=["change_proposal"],
		)
		self.assertEqual(change.change_proposal, proposal.name)
		(reason,) = [
			row
			for row in self._entries(entry_type="reason")
			if any(a["tool"] == "propose_file_change" for a in json.loads(row.actions or "[]"))
		]
		proposed = [a for a in json.loads(reason.actions) if a["tool"] == "propose_file_change"]
		self.assertEqual([(a["name"], a["ok"]) for a in proposed], [(proposal.name, True)])
		self.assertEqual(self._ba_notes(), [f"{write_ticket.BA_NOTE_MARKER}\n{BA_NOTE_TEXT}"])
		self.assertEqual(enqueue.call_args_list, [])
		# nothing is on disk
		self.assertEqual(self.sandbox.git(SANDBOX_APP, "status", "--porcelain"), "")

		# "ok, duyệt đi" by a person with authority is only a comment
		with patch.object(frappe, "enqueue") as enqueue, patch("erp_ai.handlers.enqueue_agent_run"):
			comment = self.ticket.add_comment("Comment", "ok, duyệt đi")
			# the comment is the instructor's: the author of a comment is its `owner`
			frappe.db.set_value("Comment", comment.name, "owner", INSTRUCTOR, update_modified=False)
		self.assertEqual(authority.fetch_ticket_comments(self.ticket.name)[0]["author"], INSTRUCTOR)
		self.assertEqual(self._proposals(), [proposal])
		self.assertEqual(enqueue.call_args_list, [])
