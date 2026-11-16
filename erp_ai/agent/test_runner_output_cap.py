"""BUG-005: the reasoning call's output cap, and a turn the cap cut runs none of its tool calls.

A turn the model result calls `max_tokens` may hold `tool_use` blocks whose input stops half way; the runner
answers each with an error `tool_result` instead of running it, and the run goes on so the model can call again.
All of it is seen through the fake model gateway.
"""

import json
from unittest.mock import patch

import frappe

from erp_ai.agent import answer_delay, authority
from erp_ai.agent.runner import CUT_REASON, CUT_TOOL_RESULT, REASON_MAX_TOKENS, STOP_MAX_TOKENS
from erp_ai.agent.test_agent_runner import SANDBOX_APP, SANDBOX_REL, tool_use
from erp_ai.agent.test_runner_propose_now import CLASSIFY_C_85, ProposeNowBase
from erp_ai.constants import CHANGE_STATUS_PENDING, PROPOSAL_DOCTYPE
from erp_ai.test_utils import make_model_result, set_agent_settings

CUT_COMMENT = "NHAN-DINH-BI-CAT"


def cut_turn(*blocks):
	return make_model_result(content=list(blocks), stop_reason=STOP_MAX_TOKENS)


def propose_block(block_id):
	return tool_use(
		block_id,
		"propose_file_change",
		path=f"{SANDBOX_APP}/{SANDBOX_REL}",
		find=["x = 1"],
		replace=["x = 2"],
		reason="r",
	)


def tool_turn_of(*blocks):
	return make_model_result(content=list(blocks), stop_reason="tool_use")


class TestOutputCap(ProposeNowBase):
	def setUp(self):
		super().setUp()
		self._owner_is_instructor()

	def _proposals(self):
		return frappe.get_all(
			PROPOSAL_DOCTYPE, filters={"ticket": self.ticket.name}, fields=["change_status"]
		)

	def _comment_contents(self):
		return frappe.get_all(
			"Comment", filters=authority.ticket_comment_filters(self.ticket.name), pluck="content"
		)

	def _cut_post_comment(self, block_id="toolu_c"):
		return tool_use(block_id, "post_comment", content=CUT_COMMENT)

	def test_the_reasoning_call_asks_for_16000_tokens(self):
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		self._run("ticket_insert")

		self.assertEqual(REASON_MAX_TOKENS, 16000)
		(call,) = self._reason_calls()
		self.assertEqual(call["max_tokens"], 16000)

	def test_a_cut_turn_runs_no_tool_and_the_model_is_told(self):
		self.gateway.results = [
			CLASSIFY_C_85,
			cut_turn(propose_block("toolu_p"), self._cut_post_comment()),
			make_model_result(),
		]
		self._run("ticket_insert")

		self.assertEqual(self._proposals(), [])
		self.assertFalse([c for c in self._comment_contents() if CUT_COMMENT in (c or "")])
		calls = self._reason_calls()
		self.assertEqual(len(calls), 2)
		results = calls[1]["messages"][-1]["content"]
		self.assertEqual(
			[(r["type"], r["tool_use_id"], r["is_error"], r["content"]) for r in results],
			[
				("tool_result", "toolu_p", True, CUT_TOOL_RESULT),
				("tool_result", "toolu_c", True, CUT_TOOL_RESULT),
			],
		)
		# the assistant content of the cut turn goes back as for a normal tool turn
		self.assertEqual(calls[1]["messages"][-2]["role"], "assistant")

	def test_the_model_calls_again_after_a_cut_and_the_proposal_is_made_once(self):
		self.gateway.results = [
			CLASSIFY_C_85,
			cut_turn(propose_block("toolu_cut")),
			tool_turn_of(propose_block("toolu_ok")),
			make_model_result(),
		]
		self._run("ticket_insert")

		self.assertEqual(len(self._reason_calls()), 3)
		self.assertEqual([p.change_status for p in self._proposals()], [CHANGE_STATUS_PENDING])

	def test_the_cut_turn_row_keeps_max_tokens_and_a_failed_action(self):
		self.gateway.results = [
			CLASSIFY_C_85,
			cut_turn(propose_block("toolu_p"), self._cut_post_comment()),
			make_model_result(),
		]
		self._run("ticket_insert")

		first = self._entries(entry_type="reason")[0]
		self.assertEqual(first.stop_reason, STOP_MAX_TOKENS)
		self.assertIn(STOP_MAX_TOKENS, first.error)
		actions = json.loads(first.actions)
		(proposed,) = [a for a in actions if a["tool"] == "propose_file_change"]
		self.assertFalse(proposed["ok"])
		self.assertEqual(proposed["reason"], CUT_REASON)
		self.assertEqual(json.loads(first.tools_called), ["propose_file_change", "post_comment"])

	def test_a_cut_turn_with_only_text_ends_the_run(self):
		self.gateway.results = [
			CLASSIFY_C_85,
			make_model_result(text="nhận định dở", stop_reason=STOP_MAX_TOKENS),
			make_model_result(),
		]
		self._run("ticket_insert")

		self.assertEqual(len(self._reason_calls()), 1)
		self.assertEqual([e.stop_reason for e in self._entries(entry_type="reason")], [STOP_MAX_TOKENS])

	def test_a_cut_last_turn_runs_no_tool_and_ends_the_run(self):
		set_agent_settings(max_turns_per_run=1)
		self.gateway.results = [
			CLASSIFY_C_85,
			cut_turn(propose_block("toolu_p"), self._cut_post_comment()),
			make_model_result(),
		]
		self._run("ticket_insert")

		self.assertEqual(len(self._reason_calls()), 1)
		self.assertEqual(self._proposals(), [])
		self.assertFalse([c for c in self._comment_contents() if CUT_COMMENT in (c or "")])
		self.assertEqual([e.stop_reason for e in self._entries(entry_type="reason")], [STOP_MAX_TOKENS])

	def test_a_cut_answer_does_not_use_up_the_answer_delay(self):
		# the delay of an @ai run waits before the answer that runs, not before a cut one that is discarded
		set_agent_settings(max_turns_per_run=5)
		self.gateway.results = [
			CLASSIFY_C_85,
			cut_turn(self._cut_post_comment()),
			tool_turn_of(tool_use("toolu_a", "post_comment", content="nhận định đủ")),
			make_model_result(),
		]
		with patch.object(answer_delay.AnswerDelay, "wait_before_answer", return_value=0) as wait:
			self._run("comment_mention")
			self.assertEqual(len(self._reason_calls()), 3)
			self.assertEqual(wait.call_count, 1)
