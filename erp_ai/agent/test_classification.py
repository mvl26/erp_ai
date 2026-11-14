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
from erp_ai.test_utils import make_routing_rules

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

	def test_scores_valid_each_level(self):
		for level in classification.SCORE_VALUES:
			result = classification.parse_classification(
				_text(do_phuc_tap=level, do_quan_trong=level, ly_do_diem="Vì sao", bo_phan="Kế toán")
			)
			self.assertEqual(result.complexity, level)
			self.assertEqual(result.importance, level)
			self.assertEqual(result.score_reason, "Vì sao")
			self.assertEqual(result.department, "Kế toán")
		mixed = classification.parse_classification(_text(do_phuc_tap=1, do_quan_trong=3))
		self.assertEqual((mixed.complexity, mixed.importance), (1, 3))

	def test_bad_scores_mean_no_score(self):
		missing_both = json.dumps(VALID)
		bad_values = [0, 4, "2", True, 2.0, None, [2]]
		cases = [missing_both]
		for bad in bad_values:
			cases.append(_text(do_phuc_tap=bad, do_quan_trong=2, ly_do_diem="Lý do"))
			cases.append(_text(do_phuc_tap=2, do_quan_trong=bad, ly_do_diem="Lý do"))
		for text in cases:
			result = classification.parse_classification(text)
			self.assertIsNotNone(result, text)
			self.assertEqual(result.category, "A", text)
			self.assertEqual((result.complexity, result.importance, result.score_reason), (0, 0, ""), text)

	def test_score_reason_cut_to_25_words(self):
		words = [f"từ{i}" for i in range(40)]
		result = classification.parse_classification(
			_text(do_phuc_tap=2, do_quan_trong=2, ly_do_diem=" ".join(words))
		)
		self.assertEqual(result.score_reason, " ".join(words[: classification.SCORE_REASON_MAX_WORDS]))
		self.assertEqual(classification.SCORE_REASON_MAX_WORDS, 25)
		short = classification.parse_classification(_text(do_phuc_tap=2, do_quan_trong=2, ly_do_diem="a b c"))
		self.assertEqual(short.score_reason, "a b c")

	def test_department_not_string_is_none(self):
		for bad in (1, ["IT"], True, {}):
			self.assertIsNone(classification.parse_classification(_text(bo_phan=bad)).department)

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

	def test_parse_deeply_nested_json_returns_none(self):
		self.assertIsNone(classification.parse_classification("[" * 100000))

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
		self.assertIn("[GẬP]", prompts.CLASSIFY_PROMPT)
		self.assertNotIn("[GẤP]", prompts.CLASSIFY_PROMPT)
		self.assertIn("[GẬP]", prompts.CONVENTIONS)
		self.assertNotIn("[GẤP]", prompts.CONVENTIONS)
		self.assertIn("dau_muc", prompts.CLASSIFY_PROMPT)

	def test_classify_prompt_has_score_keys_and_scale(self):
		prompt = prompts.CLASSIFY_PROMPT
		for key in ("do_phuc_tap", "do_quan_trong", "ly_do_diem", "bo_phan"):
			self.assertIn(f'"{key}"', prompt)
		for row in (
			"| 1 | Làm xong dưới 1 giờ làm việc, không cần đổi hệ thống: hỏi đáp, thao tác có sẵn | Ảnh hưởng một người, không chặn việc, không có hạn gần |",
			"| 2 | Trong 1 ngày làm việc: cấu hình có sẵn, sửa một lỗi xác định, một đợt dữ liệu nhỏ | Chặn việc của một người hoặc một bộ phận; hoặc có hạn trong 24 giờ; hoặc (đầu mục D) có Hạn hoàn thành |",
			"| 3 | Nhiều ngày, cần phân tích trước (BA), xây mới hoặc tích hợp | Chặn nghiệp vụ kế toán, kho hoặc bán hàng; hoặc nhiều bộ phận ngừng việc |",
		):
			self.assertIn(row, prompt)
		self.assertIn("| Điểm | Độ phức tạp | Độ quan trọng |", prompt)

	def test_classify_request_appends_departments_only_when_given(self):
		base = prompts.build_classify_request("Lỗi", "nội dung")
		self.assertEqual(base["system"][0]["text"], prompts.CLASSIFY_PROMPT)
		self.assertNotIn("\n\nDANH SÁCH BỘ PHẬN:", base["system"][0]["text"])
		empty = prompts.build_classify_request("Lỗi", "nội dung", ())
		self.assertEqual(empty, base)

		request = prompts.build_classify_request("Lỗi", "nội dung", ("Kế toán", "Mua hàng"))
		self.assertEqual(len(request["system"]), 1)
		block = request["system"][0]
		self.assertEqual(block["cache_control"], {"type": "ephemeral"})
		self.assertTrue(block["text"].startswith(prompts.CLASSIFY_PROMPT))
		self.assertTrue(block["text"].endswith("DANH SÁCH BỘ PHẬN: Kế toán, Mua hàng"))
		self.assertEqual(request["messages"], base["messages"])

	def _routing_inputs(self, **override):
		mapping = json.loads(json.dumps(classification.DEFAULT_CATEGORY_MAPPING))
		config = json.loads(make_routing_rules())
		config["assignees"]["A"] = {"default": "a1@x.com", "prefixes": {"[tracecore]": "a2@x.com"}}
		config["assignees"]["B"]["default"] = "b1@x.com"
		config["departments"] = {
			"Kế toán": {"team": "Nhóm KT", "head": "k1@x.com"},
			"Kho": {"team": "Nhóm Kho", "head": "k2@x.com"},
			"Mua hàng": {"team": "Nhóm KT", "head": "k3@x.com"},
		}
		config.update(override)
		names = {
			"a1@x.com": "Người A1",
			"a2@x.com": "Người A2",
			"b1@x.com": "Người B1",
			"k1@x.com": "Người K1",
			"k2@x.com": "Người K2",
			"k3@x.com": "Người K3",
		}
		return mapping, config, names

	def test_routing_table_shows_configured_people(self):
		mapping, config, names = self._routing_inputs()
		table = prompts.build_routing_table(mapping, config, names)
		self.assertTrue(table.startswith("BẢNG ROUTING"))
		self.assertIn("| Đầu mục | Nhóm nhận | Người mặc định | Ưu tiên | SLA phản hồi / xử lý |", table)
		self.assertIn("| A | IT | Người A1; [tracecore]: Người A2 | High | 15 phút / 480 phút |", table)
		self.assertIn("| B | IT | Người B1 | Medium | 15 phút / 240 phút |", table)
		self.assertIn("| C | IT | - | Medium | 60 phút / 1440 phút |", table)
		heads = (
			"Trưởng bộ phận: Người K1 (Kế toán); Trưởng bộ phận: Người K2 (Kho); "
			"Trưởng bộ phận: Người K3 (Mua hàng)"
		)
		# D and E list every department: teams deduplicated (two departments share "Nhóm KT"), heads joined
		self.assertIn(f"| D | Nhóm KT, Nhóm Kho | {heads} | Medium | 60 phút / theo Hạn hoàn thành |", table)
		self.assertIn(f"| E | Nhóm KT, Nhóm Kho | {heads} | - | 60 phút / theo Hạn hoàn thành |", table)
		self.assertIn("| F | IT | - | Low | 5 phút / 60 phút |", table)

		# the default person changes: only that cell changes, the rest of the table is the same
		table1 = table
		config["assignees"]["A"]["default"] = "new@x.com"
		table2 = prompts.build_routing_table(mapping, config, {**names, "new@x.com": "Người Mới"})
		self.assertEqual(table2, table1.replace("Người A1", "Người Mới"))
		self.assertNotEqual(table2, table1)

	def test_routing_table_cell_escapes_pipe_and_newline(self):
		mapping, config, names = self._routing_inputs()
		names["a1@x.com"] = "Người|A1\nHai"
		table = prompts.build_routing_table(mapping, config, names)
		self.assertIn("| A | IT | Người/A1 Hai; [tracecore]: Người A2 | High |", table)
		for line in table.splitlines()[4:]:
			self.assertEqual(line.count("|"), 6, line)

	def test_routing_table_falls_back_to_user_id_without_name(self):
		mapping, config, names = self._routing_inputs()
		table = prompts.build_routing_table(mapping, config, {})
		self.assertIn("a1@x.com", table)

	def test_routing_table_empty_without_config(self):
		self.assertEqual(prompts.build_routing_table({}, {}, {}), "")

	def test_build_reason_system(self):
		blocks = prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC")
		self.assertEqual(len(blocks), 1)
		self.assertEqual(blocks[0]["type"], "text")
		self.assertEqual(blocks[0]["cache_control"], {"type": "ephemeral"})
		text = blocks[0]["text"]
		for part in (prompts.CORE_PROMPT, prompts.CATEGORY_TABLE, "ROUTING-ABC", prompts.CONVENTIONS):
			self.assertIn(part, text)
		self.assertLess(text.index(prompts.CATEGORY_TABLE), text.index("ROUTING-ABC"))
		self.assertLess(text.index("ROUTING-ABC"), text.index(prompts.CONVENTIONS))
		self.assertTrue(text.endswith("DIGEST-XYZ"))

	def test_reason_system_without_routing_table(self):
		text = prompts.build_reason_system("DIGEST-XYZ")[0]["text"]
		self.assertNotIn("BẢNG ROUTING", text)
		self.assertEqual(
			text,
			"\n\n".join([prompts.CORE_PROMPT, prompts.CATEGORY_TABLE, prompts.CONVENTIONS, "DIGEST-XYZ"]),
		)

	def test_build_reason_system_empty_digest(self):
		text = prompts.build_reason_system("")[0]["text"]
		self.assertIn(prompts.CORE_PROMPT, text)
		self.assertFalse(text.endswith("\n\n"))

	def test_reason_system_without_change_tools_is_byte_identical(self):
		for digest, routing in (
			("DIGEST-XYZ", "ROUTING-ABC"),
			("DIGEST-XYZ", ""),
			("", "ROUTING-ABC"),
			("", ""),
		):
			parts = [prompts.CORE_PROMPT, prompts.CATEGORY_TABLE, routing, prompts.CONVENTIONS, digest]
			expected = [
				{
					"type": "text",
					"text": "\n\n".join(part for part in parts if part),
					"cache_control": {"type": "ephemeral"},
				}
			]
			self.assertEqual(prompts.build_reason_system(digest, routing), expected)
			self.assertEqual(prompts.build_reason_system(digest, routing, change_tools=False), expected)
			text = expected[0]["text"]
			self.assertIn("Không sửa file trong apps/", text)
			self.assertNotIn(prompts.CHANGE_TOOLS_BLOCK, text)

	def test_reason_system_with_change_tools_adds_approval_block(self):
		block = prompts.CHANGE_TOOLS_BLOCK
		self.assertTrue(block.startswith("SỬA CODE VÀ LỆNH BENCH — CHỈ ĐỀ XUẤT, NGƯỜI DUYỆT\n\n"))
		self.assertIn("KHÔNG BAO GIỜ là duyệt", block)
		self.assertIn("commit git local", block)
		self.assertIn("không\n  push", block)
		self.assertNotIn('chờ một chữ "ok"', block)
		for tool in ("propose_file_change", "propose_new_file", "propose_bench_command"):
			self.assertIn(tool, block)
		self.assertTrue(
			block.endswith(
				"- Không đề xuất gì chạm app erp_ai, file khóa hay mật khẩu, cấu hình site, hay tên bắt đầu bằng .git."
			)
		)
		for phrase in (
			"propose_file_change nhận nhiều mục (edit, create,\n  delete, rename; create tự tạo thư mục cha)",
			"Việc trải trên hai app là hai đề xuất.",
			"kết thúc bằng lệnh migrate rồi restart",
			"Restart do hệ thống chạy sau khi người duyệt; không nhờ người restart.",
			"- Lệnh bench không hoàn tác được; hoàn tác chỉ trả lại phần file.",
			"cả khối thành một commit git local trên nhánh đang checkout.",
		):
			self.assertIn(phrase, block)
		# design.md §3.7 "Prompt" lines 427-435, word for word (AC-56).
		new_dash_lines = (
			"- Một đề xuất là một khối trong MỘT app: propose_file_change nhận nhiều mục (edit, create,\n"
			"  delete, rename; create tự tạo thư mục cha) và danh sách lệnh bench chạy sau khi ghi file.\n"
			"  Xóa và đổi tên cần duyệt như mọi mục. Việc trải trên hai app là hai đề xuất.\n"
			"- Khối có file .py phải kết thúc bằng lệnh migrate rồi restart; khối không có file .py thì\n"
			"  không có restart. Restart do hệ thống chạy sau khi người duyệt; không nhờ người restart.\n"
			"- Lệnh bench không hoàn tác được; hoàn tác chỉ trả lại phần file.\n"
			"- Khi được duyệt, cả khối thành một commit git local trên nhánh đang checkout. Bạn không\n"
			"  push, không đổi nhánh, không sửa lịch sử git.\n"
			"- Không đề xuất gì chạm app erp_ai, file khóa hay mật khẩu, cấu hình site, hay tên bắt đầu bằng .git."
		)
		self.assertTrue(block.endswith("\n" + new_dash_lines))
		self.assertIn(
			"\n- Một đề xuất là một khối trong MỘT app: propose_file_change nhận nhiều mục (edit, create,\n"
			"  delete, rename; create tự tạo thư mục cha) và danh sách lệnh bench chạy sau khi ghi file.\n"
			"  Xóa và đổi tên cần duyệt như mọi mục. Việc trải trên hai app là hai đề xuất.\n",
			block,
		)

		old = prompts.build_reason_system("", "ROUTING-ABC")[0]["text"]
		blocks = prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC", change_tools=True)
		self.assertEqual(len(blocks), 1)
		self.assertEqual(blocks[0]["cache_control"], {"type": "ephemeral"})
		text = blocks[0]["text"]
		self.assertEqual(text, "\n\n".join([old, block, prompts.ACT_NOW_BLOCK, "DIGEST-XYZ"]))
		self.assertTrue(text.startswith(prompts.CORE_PROMPT))
		self.assertEqual(text[: text.index(block)], old + "\n\n")

		no_digest = prompts.build_reason_system("", "", change_tools=True)[0]["text"]
		self.assertEqual(
			no_digest,
			"\n\n".join(
				[
					prompts.CORE_PROMPT,
					prompts.CATEGORY_TABLE,
					prompts.CONVENTIONS,
					block,
					prompts.ACT_NOW_BLOCK,
				]
			),
		)
		with self.assertRaises(TypeError):
			prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC", True)

	def test_block_first_line_unchanged(self):
		self.assertEqual(
			prompts.CHANGE_TOOLS_BLOCK.split("\n")[0],
			"SỬA CODE VÀ LỆNH BENCH — CHỈ ĐỀ XUẤT, NGƯỜI DUYỆT",
		)
		self.assertIn("thay cho quy tắc 6:\n- Các tool này chỉ tạo một đề xuất", prompts.CHANGE_TOOLS_BLOCK)
		self.assertIn("- Chỉ người có vai trò ERP AI Instructor duyệt", prompts.CHANGE_TOOLS_BLOCK)

	def test_block_drops_one_file_one_command_and_manual_restart_lines(self):
		block = prompts.CHANGE_TOOLS_BLOCK
		self.assertNotIn("Mỗi đề xuất là một file hoặc một lệnh", block)
		self.assertNotIn("Sửa file .py chỉ có hiệu lực sau khi người chạy bench restart", block)
		self.assertEqual(block.count("\n- "), 8)

	def test_block_keeps_never_approval_phrase_and_restart_example(self):
		block = prompts.CHANGE_TOOLS_BLOCK
		self.assertIn("KHÔNG BAO GIỜ là duyệt", block)
		self.assertIn('"restart đi"', block)
		self.assertIn('("ok", "duyệt", "đã duyệt", "restart đi"…) KHÔNG BAO GIỜ là duyệt', block)

	def test_block_has_no_wait_for_ok_or_auto_undo(self):
		block = prompts.CHANGE_TOOLS_BLOCK
		self.assertNotIn('chờ một chữ "ok"', block)
		self.assertNotIn("Việc hoàn tác được thì làm luôn", block)

	def test_reason_system_with_site_admin_tools_adds_record_block(self):
		block = prompts.SITE_ADMIN_TOOLS_BLOCK
		for tool in ("api_list_records", "api_get_record", "api_create_record", "api_update_record"):
			self.assertIn(tool, block)
		for phrase in ("người ra lệnh", "System Manager", "không đặt mật khẩu", "Không xóa", "dữ liệu"):
			self.assertIn(phrase, block)

		old = prompts.build_reason_system("", "ROUTING-ABC")[0]["text"]
		text = prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC", site_admin_tools=True)[0]["text"]
		self.assertEqual(text, "\n\n".join([old, block, prompts.ACT_NOW_BLOCK, "DIGEST-XYZ"]))
		both = prompts.build_reason_system("", "", change_tools=True, site_admin_tools=True)[0]["text"]
		self.assertTrue(
			both.endswith("\n\n".join([prompts.CHANGE_TOOLS_BLOCK, block, prompts.ACT_NOW_BLOCK]))
		)
		self.assertNotIn(block, prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC")[0]["text"])

	def test_reason_system_with_unrestricted_tools_adds_full_access_block(self):
		block = prompts.UNRESTRICTED_TOOLS_BLOCK
		for tool in (
			"api_list_records",
			"api_get_record",
			"api_create_record",
			"api_update_record",
			"api_delete_record",
			"api_submit_record",
			"api_call_method",
		):
			self.assertIn(tool, block)
		for phrase in ("TOÀN QUYỀN", "người ra lệnh", "dữ liệu", "ERP AI Setting", "mật khẩu"):
			self.assertIn(phrase, block)

		old = prompts.build_reason_system("", "ROUTING-ABC")[0]["text"]
		text = prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC", unrestricted_tools=True)[0]["text"]
		self.assertEqual(text, "\n\n".join([old, block, prompts.ACT_NOW_BLOCK, "DIGEST-XYZ"]))
		# the full-access block replaces the record block, never joins it
		both = prompts.build_reason_system("", "", site_admin_tools=True, unrestricted_tools=True)[0]["text"]
		self.assertIn(block, both)
		self.assertNotIn(prompts.SITE_ADMIN_TOOLS_BLOCK, both)

	def test_act_now_block_only_with_action_tools(self):
		block = prompts.ACT_NOW_BLOCK
		for phrase in (
			"LÀM LUÔN, KHÔNG HỎI LẠI",
			"quy tắc 6",
			"Cần ai quyết",
			"Không hỏi lại",
			"tạo đề xuất luôn",
			"Nút Duyệt / Từ chối",
			"xác nhận duy nhất",
			"người ra lệnh",
		):
			self.assertIn(phrase, block)
		self.assertNotIn(block, prompts.build_reason_system("DIGEST-XYZ", "ROUTING-ABC")[0]["text"])
		for flags in ({"change_tools": True}, {"site_admin_tools": True}, {"unrestricted_tools": True}):
			text = prompts.build_reason_system("", "", **flags)[0]["text"]
			self.assertEqual(text.count(block), 1, flags)
			self.assertTrue(text.endswith(block), flags)

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
