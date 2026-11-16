"""CHG-010 T3: a run with the console switch on gets propose_console_script and its prompt block, the tool makes one
pending console proposal and nothing runs. Seen through the fake model gateway."""

import json
from unittest.mock import patch

import frappe

from erp_ai.agent import authority, runner
from erp_ai.agent.changes import block
from erp_ai.agent.prompts import ACT_NOW_BLOCK, CONSOLE_TOOLS_BLOCK
from erp_ai.agent.test_agent_runner import (
	INSTRUCTOR,
	GuidanceTestBase,
	make_instructor,
	tool_turn,
	tool_use,
)
from erp_ai.constants import CHANGE_KIND_COMMAND, CHANGE_STATUS_PENDING, PROPOSAL_DOCTYPE
from erp_ai.test_utils import make_model_result, set_agent_settings

CLASSIFY_C_85 = make_model_result(
	text=json.dumps({"dau_muc": "C", "do_tin_cay": "Cao", "do_tin_cay_pct": 85, "ly_do": "x"})
)
CHANGE_TOOLS = ["propose_file_change", "propose_new_file", "propose_bench_command"]
SCRIPT = 'import frappe\nfor name in frappe.get_all("ToDo", pluck="name", limit=3):\n\tprint(name)\n'


class TestConsoleRun(GuidanceTestBase):
	def setUp(self):
		super().setUp()
		# L3, code change off, console and act-now on: console must not need the code-change switch
		set_agent_settings(
			permission_level="L3",
			level_cap_c="L3",
			act_now_enabled=1,
			code_change_enabled=0,
			console_enabled=1,
			confidence_threshold=10,
		)
		self.latest_classification.side_effect = self.real_latest_classification
		make_instructor(self)
		frappe.db.set_value("HD Ticket", self.ticket.name, "owner", INSTRUCTOR, update_modified=False)

	def _reason_calls(self):
		return [call for call in self.gateway.calls if call["task"] == "reason"]

	def _proposals(self):
		return frappe.get_all(
			PROPOSAL_DOCTYPE,
			filters={"ticket": self.ticket.name},
			fields=["name", "change_status", "change_kind", "content_after", "command_list"],
		)

	def test_the_run_proposes_a_console_script_and_enqueues_nothing(self):
		propose = tool_use("toolu_c", "propose_console_script", script=SCRIPT, reason="không có API")
		self.gateway.results = [CLASSIFY_C_85, tool_turn(propose), make_model_result()]
		with (
			patch.object(authority, "run_instructor", return_value=INSTRUCTOR),
			patch.object(frappe, "enqueue") as enqueue,
		):
			self._run("comment_mention")

		first, second = self._reason_calls()
		names = [tool["name"] for tool in first["tools"]]
		self.assertIn("propose_console_script", names)
		self.assertFalse(set(CHANGE_TOOLS) & set(names))
		system = first["system"][0]["text"]
		self.assertEqual(system.count(CONSOLE_TOOLS_BLOCK), 1)
		self.assertIn(ACT_NOW_BLOCK, system)
		(proposal,) = self._proposals()
		self.assertEqual(proposal.change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(proposal.change_kind, CHANGE_KIND_COMMAND)
		self.assertEqual(proposal.content_after, SCRIPT)
		self.assertTrue(block.is_console(frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)))
		self.assertEqual(enqueue.call_args_list, [])
		result = json.loads(second["messages"][-1]["content"][0]["content"])
		self.assertTrue(result["ok"], result)

	def test_switch_off_gives_no_tool_and_no_block(self):
		set_agent_settings(console_enabled=0)
		self.gateway.results = [CLASSIFY_C_85, make_model_result()]
		with patch.object(authority, "run_instructor", return_value=INSTRUCTOR):
			self._run("comment_mention")

		(call,) = self._reason_calls()
		self.assertNotIn("propose_console_script", [tool["name"] for tool in call["tools"]])
		self.assertNotIn(CONSOLE_TOOLS_BLOCK, call["system"][0]["text"])
