"""BUG-007: a ticket_insert run on a category C ticket whose bot wrote a BA note and a resolution hint but no de_xuat
comment: the guidance message carries the hint's plan, not the fallback sentence. Seen through the fake gateway."""

from unittest.mock import patch

from erp_ai.agent import authority
from erp_ai.agent.test_agent_runner import ba_note_call, tool_turn, tool_use
from erp_ai.agent.test_runner_propose_now import CLASSIFY_C_85, ProposeNowBase
from erp_ai.agent.tools import write_ticket
from erp_ai.test_utils import make_model_result

HINT = (
	"Nhận định: Purchase Invoice chưa có chốt kiểm tra trước khi nộp.\n\n"
	"Hướng xử lý: Dùng Server Script loại Document Event, before_submit trên Purchase Invoice."
)


class TestGuidanceTakesTheHint(ProposeNowBase):
	def test_the_guidance_carries_the_hint_when_no_analysis_comment_was_written(self):
		self.gateway.results = [
			CLASSIFY_C_85,
			tool_turn(tool_use("toolu_h", "set_resolution_hint", text=HINT), ba_note_call("toolu_b")),
			make_model_result(),
		]
		with patch.object(authority, "run_instructor", return_value="Administrator"):
			self._run("ticket_insert")

		content = self._guidance_content()
		self.assertIn("Dùng Server Script loại Document Event, before_submit", content)
		self.assertIn("Nhận định: Purchase Invoice chưa có chốt kiểm tra", content)
		self.assertNotIn("bot chưa viết được nhận định", content)
		self.assertNotIn(write_ticket.GUIDANCE_FALLBACK, content)
