"""BUG-010 (ticket 43406): an @ai run whose message carries no authority tells the bot why it lacks tools.

The runner passes the tools an instructor's message would have opened in this run; the first message of an @ai run
then names them and the reason. A run with an instructor, or one where authority would open nothing, keeps its first
message as before. All of it is seen through the fake model gateway.
"""

from unittest.mock import patch

from erp_ai.agent import authority, prompts, runner
from erp_ai.agent.test_agent_runner import INSTRUCTOR, GuidanceTestBase, make_instructor
from erp_ai.test_utils import make_model_result, set_agent_settings

RECORD_TOOLS = ("api_list_records", "api_get_record", "api_create_record", "api_update_record")


class TestNoInstructorLine(GuidanceTestBase):
	"""Settings like site miyano on 2026-11-17: L3 with the record tools on."""

	def setUp(self):
		super().setUp()
		set_agent_settings(permission_level="L3", level_cap_a="L3", record_tools_enabled=1)
		self.latest_classification.return_value = ("A", 90)
		built = patch.object(runner, "build_initial_message", wraps=prompts.build_initial_message)
		self.build = built.start()
		self.addCleanup(built.stop)

	def _comment_run(self, instructor):
		self.gateway.results = [make_model_result()]
		with patch.object(authority, "run_instructor", return_value=instructor):
			self._run("comment_mention")
		(call,) = [call for call in self.gateway.calls if call["task"] == "reason"]
		return call

	def test_without_authority_the_message_names_the_locked_tools(self):
		call = self._comment_run(None)

		names = {tool["name"] for tool in call["tools"]}
		self.assertFalse(names & set(RECORD_TOOLS))
		locked = self.build.call_args.kwargs.get("instructor_tools")
		self.assertTrue(set(RECORD_TOOLS) <= set(locked or ()), locked)
		self.assertIn("create_task", locked)
		self.assertFalse(set(locked) & names)
		message = call["messages"][0]["content"]
		self.assertEqual(message.count(prompts.no_instructor_text(locked)), 1)

	def test_with_an_instructor_nothing_is_added(self):
		make_instructor(self)
		call = self._comment_run(INSTRUCTOR)

		self.assertTrue(set(RECORD_TOOLS) <= {tool["name"] for tool in call["tools"]})
		self.assertEqual(self.build.call_args.kwargs.get("instructor_tools"), ())
		self.assertNotIn(
			"ERP AI Instructor, hoặc người được người khác giao phiếu này", call["messages"][0]["content"]
		)

	def test_below_the_threshold_authority_opens_nothing(self):
		# an ask-only run: an instructor's message would get the same tools, so there is nothing to explain
		set_agent_settings(confidence_threshold=95)
		call = self._comment_run(None)

		self.assertEqual(self.build.call_args.kwargs.get("instructor_tools"), ())
		self.assertNotIn(
			"ERP AI Instructor, hoặc người được người khác giao phiếu này", call["messages"][0]["content"]
		)
