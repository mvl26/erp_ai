import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import classification, prompts
from erp_ai.agent.prompts import DESCRIPTION_MAX_CHARS
from erp_ai.constants import (
	CATEGORIES,
	CONFIDENCE_VALUES,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

VALID = {
	"dau_muc": "A",
	"do_tin_cay": "Cao",
	"ly_do": "Đơn bán đã hủy nhưng trạng thái sai",
	"nhom": "IT",
	"uu_tien": "High",
	"can_tach": False,
	"cac_yeu_cau": [],
}


def _text(**override):
	return json.dumps({**VALID, **override}, ensure_ascii=False)


class TestParseClassification(FrappeTestCase):
	def test_parse_valid_plain_json(self):
		result = classification.parse_classification(_text())
		self.assertEqual(
			result,
			classification.Classification(
				category="A",
				confidence="Cao",
				reason="Đơn bán đã hủy nhưng trạng thái sai",
				team="IT",
				priority="High",
				needs_split=False,
				requests=[],
			),
		)

	def test_parse_accepts_single_json_fence(self):
		for fence in ("```json\n{}\n```", "```\n{}\n```", "  ```json\n{}\n```  "):
			result = classification.parse_classification(fence.format(_text(dau_muc="C")))
			self.assertIsNotNone(result, fence)
			self.assertEqual(result.category, "C")

	def test_parse_rejects_non_json_and_bad_values(self):
		bad_inputs = [
			"",
			"   ",
			"Đây là phiếu loại A",
			"{not json",
			"[1, 2, 3]",
			"null",
			'"A"',
			"42",
			_text(dau_muc="G"),
			_text(dau_muc="a"),
			_text(dau_muc=None),
			_text(dau_muc=["A"]),
			_text(do_tin_cay="Rất cao"),
			_text(do_tin_cay=None),
			json.dumps({k: v for k, v in VALID.items() if k != "dau_muc"}),
			json.dumps({k: v for k, v in VALID.items() if k != "do_tin_cay"}),
			"```json\n" + _text() + "\n```\n```json\n" + _text() + "\n```",
			"Kết quả: " + _text(),
		]
		for text in bad_inputs:
			self.assertIsNone(classification.parse_classification(text), repr(text))

	def test_parse_never_raises_on_non_string(self):
		for value in (None, 5, b"{}", {"dau_muc": "A"}):
			self.assertIsNone(classification.parse_classification(value))

	def test_unknown_priority_becomes_none(self):
		for value in ("Critical", None, 3, ""):
			result = classification.parse_classification(_text(uu_tien=value))
			self.assertIsNotNone(result)
			self.assertIsNone(result.priority)

	def test_every_category_and_confidence_value_is_accepted(self):
		for category in CATEGORIES:
			for confidence in CONFIDENCE_VALUES:
				result = classification.parse_classification(_text(dau_muc=category, do_tin_cay=confidence))
				self.assertEqual((result.category, result.confidence), (category, confidence))

	def test_optional_fields_default_safely(self):
		minimal = json.dumps({"dau_muc": "F", "do_tin_cay": "Thấp"})
		result = classification.parse_classification(minimal)
		self.assertEqual(result.category, "F")
		self.assertEqual(result.reason, "")
		self.assertIsNone(result.team)
		self.assertIsNone(result.priority)
		self.assertFalse(result.needs_split)
		self.assertEqual(result.requests, [])

	def test_needs_split_and_requests(self):
		result = classification.parse_classification(_text(can_tach=True, cac_yeu_cau=["một", "hai"]))
		self.assertTrue(result.needs_split)
		self.assertEqual(result.requests, ["một", "hai"])
		garbage = classification.parse_classification(_text(can_tach="yes", cac_yeu_cau="x"))
		self.assertFalse(garbage.needs_split)
		self.assertEqual(garbage.requests, [])


class TestMapping(FrappeTestCase):
	def test_default_mapping_matches_d8(self):
		mapping = classification.DEFAULT_CATEGORY_MAPPING
		self.assertEqual(tuple(mapping), CATEGORIES)
		self.assertEqual(mapping["A"]["ticket_type"], "Sự cố & lỗi hệ thống")
		self.assertEqual(mapping["F"]["ticket_type"], "Câu hỏi, phiếu nhiễu")
		self.assertEqual(
			{c: mapping[c]["agent_group"] for c in CATEGORIES},
			{"A": "IT", "B": "IT", "C": "IT", "D": "", "E": "", "F": "IT"},
		)
		self.assertEqual(
			{c: mapping[c]["priority"] for c in CATEGORIES},
			{"A": "High", "B": "Medium", "C": "Medium", "D": "Medium", "E": "", "F": "Low"},
		)
		classification.validate_mapping(json.dumps(mapping))

	def test_validate_mapping_accepts_valid_and_partial(self):
		classification.validate_mapping(json.dumps(classification.DEFAULT_CATEGORY_MAPPING))
		classification.validate_mapping('{"A": {"ticket_type": "X"}}')
		classification.validate_mapping("{}")

	def test_mapping_with_bad_schema_raises_validation_error(self):
		bad = [
			"",
			None,
			"not json",
			"[]",
			'"A"',
			'{"G": {"ticket_type": "X"}}',
			'{"A": "IT"}',
			'{"A": []}',
			'{"A": {"ticket_type": "X", "owner": "Y"}}',
			'{"A": {"ticket_type": 5}}',
			'{"A": {"priority": null}}',
		]
		for raw in bad:
			with self.assertRaises(frappe.ValidationError, msg=repr(raw)):
				classification.validate_mapping(raw)

	def test_validate_mapping_message_is_specific(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			classification.validate_mapping('{"G": {"ticket_type": "X"}}')
		self.assertIn("G", str(ctx.exception))

	def test_load_mapping(self):
		raw = json.dumps({"A": {"ticket_type": "X", "agent_group": "IT", "priority": "High"}})
		self.assertEqual(classification.load_mapping(raw), json.loads(raw))
		for bad in (None, "", "garbage", '{"Z": {}}', "[]"):
			self.assertEqual(classification.load_mapping(bad), {}, repr(bad))


class TestResolveTicketValues(FrappeTestCase):
	def setUp(self):
		self.mapping = classification.DEFAULT_CATEGORY_MAPPING

	def _result(self, **override):
		return classification.parse_classification(_text(**override))

	def test_values_come_from_mapping_not_from_model(self):
		result = self._result(dau_muc="B", nhom="Kế toán", uu_tien="Low")
		self.assertEqual(
			classification.resolve_ticket_values(result, "Thêm trường", self.mapping),
			{"ticket_type": "Quản trị & cấu hình hệ thống", "agent_group": "IT", "priority": "Medium"},
		)

	def test_missing_category_in_mapping_gives_none(self):
		result = self._result(dau_muc="C")
		values = classification.resolve_ticket_values(result, "x", {"A": self.mapping["A"]})
		self.assertEqual(values, {"ticket_type": None, "agent_group": None, "priority": None})

	def test_missing_key_inside_entry_gives_none(self):
		result = self._result(dau_muc="A")
		values = classification.resolve_ticket_values(result, "x", {"A": {"ticket_type": "T"}})
		self.assertEqual(values, {"ticket_type": "T", "agent_group": None, "priority": None})

	def test_empty_mapping(self):
		values = classification.resolve_ticket_values(self._result(), "x", {})
		self.assertEqual(values, {"ticket_type": None, "agent_group": None, "priority": None})

	def test_urgent_prefix_forces_urgent(self):
		result = self._result(dau_muc="F", uu_tien="Low")
		for subject in (
			"[GẤP] Lỗi đơn bán",
			"[GẬP] Lỗi đơn bán",
			"[HR][GẤP] Cấp tài khoản",
			"Lỗi đơn bán [GẤP] ở kho",
			"lỗi [gấp] ở kho",
		):
			values = classification.resolve_ticket_values(result, subject, self.mapping)
			self.assertEqual(values["priority"], "Urgent", subject)
			self.assertEqual(values["ticket_type"], "Câu hỏi, phiếu nhiễu", subject)

	def test_urgent_prefix_overrides_empty_priority_and_missing_category(self):
		result = self._result(dau_muc="E")
		self.assertEqual(self.mapping["E"]["priority"], "")
		values = classification.resolve_ticket_values(result, "[GẤP] việc", self.mapping)
		self.assertEqual(values["priority"], "Urgent")
		values = classification.resolve_ticket_values(result, "[GẤP] việc", {})
		self.assertEqual(values["priority"], "Urgent")

	def test_no_urgent_without_bracketed_tag(self):
		result = self._result(dau_muc="A")
		for subject in ("GẤP lỗi", "gấp", "[GẤP lỗi", "", None):
			values = classification.resolve_ticket_values(result, subject, self.mapping)
			self.assertEqual(values["priority"], "High", repr(subject))


class TestPrompts(FrappeTestCase):
	def test_ticket_text_format_and_html_stripped(self):
		text = prompts.ticket_text("Lỗi", "<p>Xin <b>chào</b></p>")
		self.assertEqual(text, "Tiêu đề: Lỗi\n\nNội dung:\nXin chào")

	def test_ticket_text_truncates_description(self):
		text = prompts.ticket_text("t", "x" * (DESCRIPTION_MAX_CHARS + 500))
		self.assertEqual(text, "Tiêu đề: t\n\nNội dung:\n" + "x" * DESCRIPTION_MAX_CHARS)

	def test_ticket_text_handles_none(self):
		self.assertEqual(prompts.ticket_text(None, None), "Tiêu đề: \n\nNội dung:\n")

	def test_build_classify_request_shape(self):
		request = prompts.build_classify_request("Lỗi", "<p>nội dung</p>")
		self.assertEqual(set(request), {"system", "messages"})
		self.assertEqual(
			request["system"],
			[{"type": "text", "text": prompts.CLASSIFY_PROMPT, "cache_control": {"type": "ephemeral"}}],
		)
		self.assertEqual(
			request["messages"],
			[{"role": "user", "content": prompts.ticket_text("Lỗi", "<p>nội dung</p>")}],
		)
		self.assertIn("[GẤP]", prompts.CLASSIFY_PROMPT)
		self.assertIn("dau_muc", prompts.CLASSIFY_PROMPT)

	def test_build_reason_system(self):
		blocks = prompts.build_reason_system("DIGEST-XYZ")
		self.assertEqual(len(blocks), 1)
		self.assertEqual(blocks[0]["type"], "text")
		self.assertEqual(blocks[0]["cache_control"], {"type": "ephemeral"})
		text = blocks[0]["text"]
		for part in (prompts.CORE_PROMPT, prompts.CATEGORY_TABLE, prompts.ROUTING_TABLE, prompts.CONVENTIONS):
			self.assertIn(part, text)
		self.assertTrue(text.endswith("DIGEST-XYZ"))

	def test_build_reason_system_empty_digest(self):
		text = prompts.build_reason_system("")[0]["text"]
		self.assertIn(prompts.CORE_PROMPT, text)
		self.assertFalse(text.endswith("\n\n"))

	def _ticket(self, **override):
		return {
			"subject": "Lỗi",
			"description": "<p>nội dung</p>",
			"status": "Open",
			"priority": "High",
			"ticket_type": "Sự cố & lỗi hệ thống",
			"agent_group": "IT",
			"creation": "2026-11-11 08:00:00",
			"name": "SHOULD-NOT-LEAK",
			**override,
		}

	def _payload(self, message):
		json_part = message.split("\n\n", 1)[0]
		return json.loads(json_part)

	def test_initial_message_new_ticket(self):
		message = prompts.build_initial_message(
			self._ticket(), [], TRIGGER_TICKET_INSERT, {"category": "A", "confidence": "Cao"}
		)
		payload = self._payload(message)
		self.assertEqual(
			set(payload["ticket"]),
			{"subject", "description", "status", "priority", "ticket_type", "agent_group", "creation"},
		)
		self.assertEqual(payload["ticket"]["description"], "nội dung")
		self.assertEqual(payload["trigger"], TRIGGER_TICKET_INSERT)
		self.assertEqual(payload["classification"], {"category": "A", "confidence": "Cao"})
		self.assertEqual(payload["comments"], [])
		self.assertIn("set_resolution_hint", message)
		self.assertNotIn("SHOULD-NOT-LEAK", message)

	def test_initial_message_comment_trigger_and_no_classification(self):
		message = prompts.build_initial_message(self._ticket(), [], TRIGGER_COMMENT_MENTION, None)
		self.assertIsNone(self._payload(message)["classification"])
		self.assertIn("post_comment", message)
		self.assertNotIn("set_resolution_hint", message)

	def test_initial_message_limits_comments_and_lengths(self):
		comments = [
			{"author": f"Người {i}", "role": "dữ liệu", "content": "<b>c</b>" + "y" * 3000} for i in range(35)
		]
		ticket = self._ticket(description="d" * (DESCRIPTION_MAX_CHARS + 10))
		payload = self._payload(prompts.build_initial_message(ticket, comments, TRIGGER_TICKET_INSERT, None))
		self.assertEqual(len(payload["ticket"]["description"]), DESCRIPTION_MAX_CHARS)
		self.assertEqual(len(payload["comments"]), 30)
		self.assertEqual(payload["comments"][-1]["author"], "Người 34")
		self.assertEqual(payload["comments"][0]["author"], "Người 5")
		self.assertEqual(len(payload["comments"][0]["content"]), 2000)
		self.assertEqual(payload["comments"][0]["role"], "dữ liệu")
		self.assertTrue(payload["comments"][0]["content"].startswith("cyyy"))
