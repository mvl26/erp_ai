import json
import re
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

APP_DIR = Path(__file__).resolve().parent.parent
DOCTYPE_DIR = APP_DIR / "erp_ai_agent" / "doctype"
MAX_DESCRIPTION_CHARS = 400
MIN_STORED_VALUE_CHARS = 4
BREAK_TYPES = ("Section Break", "Column Break", "Tab Break")
SAFE_EMAIL_DOMAINS = ("congty.vn", "example.com")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SYSTEM_WRITES = "Hệ thống tự ghi"
NOT_EDITABLE = "không sửa được"
VIETNAMESE_ACCENTS = re.compile(
	"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", re.IGNORECASE
)

# Keyed by DocType name: expected visible-field count, required phrases per field,
# and the Section Breaks as (fieldname, label, first field of the group).
DOCTYPE_CONFIG = {
	"ERP AI Setting": {
		"folder": "erp_ai_setting",
		"field_count": 26,
		"phrases": {
			"enabled": ("Tắt", "4 đơn giá", "từ khóa kích hoạt"),
			"permission_level": ("L0", "L1", "L2", "L3", "ngân sách"),
			"max_turns_per_run": ("từ 1 đến 20", "dừng"),
			"max_runs_per_ticket_per_day": ("từ 1 đến 50", "00:00"),
			"max_keys_per_call": ("từ 1 đến 10", "báo lỗi"),
			"request_timeout_s": ("từ 5 đến 300", "giây", "khóa kế tiếp"),
			"monthly_budget_usd": ("USD", "L1", "Nhập 0", "không phải"),
			"spent_this_month_usd": ("mỗi ngày", "tổng chi phí"),
			"price_input_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_write_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_read_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_output_per_mtok": ("USD", "triệu token", "không được âm"),
			"model_classify_default": ("phân loại", "model", "claude-haiku", "trần token"),
			"trigger_keyword": ("@ai", "không phân biệt hoa thường"),
			"thinking_text": ("Để trống", "giây"),
			"answer_delay_min_s": ("giây", "từ 0 đến 30", "bình luận"),
			"answer_delay_max_s": ("giây", "từ 0 đến 30", "bình luận"),
			"excluded_teams": ("mỗi dòng", "không phân biệt hoa thường"),
			"category_mapping": ("JSON", "A đến F", "[GẤP]", "Urgent"),
			"auto_assign_enabled": (
				"Bật",
				"L1",
				"Quy tắc định tuyến",
				"Assignment Rule",
				"chưa có ai được gán",
				"Task",
				"Tắt",
				"HD Agent",
			),
			"routing_rules": ("đầu mục", "SLA", "phút", "bị chặn khi lưu"),
			"prompt_digest": ("lập luận", "phân loại"),
			"alert_recipients": ("mỗi dòng", "canhbao@congty.vn", "dấu phẩy"),
			"credentials": ("không trùng", "Kiểm tra khóa"),
			"code_change_enabled": (
				"L3",
				"người ra lệnh",
				"được duyệt",
				"commit git local",
				"không push",
				"Tắt",
			),
			"code_change_apps": (
				"Mỗi dòng",
				"apps/",
				"frappe, erpnext, helpdesk, hrms",
				"mọi site trên bench",
				"erp_ai",
				"Bỏ trống",
			),
		},
		"section_count": 7,
		"read_only_fields": ("spent_this_month_usd",),
		"sections": (
			("section_activation", "Bật và mức quyền", "enabled"),
			("section_limits", "Giới hạn mỗi lần chạy", "max_turns_per_run"),
			("section_budget", "Ngân sách và đơn giá", "monthly_budget_usd"),
			("section_model", "Model, từ khóa và chỉ báo trả lời", "model_classify_default"),
			("section_routing", "Phân loại và nhóm loại trừ", "excluded_teams"),
			("section_code_change", "Sửa code và lệnh bench", "code_change_enabled"),
			("section_alerts", "Cảnh báo và khóa API", "alert_recipients"),
		),
	},
	"ERP AI Credential": {
		"folder": "erp_ai_credential",
		"field_count": 18,
		"phrases": {
			"label": ("không trùng", "không phân biệt hoa thường"),
			"provider": ("nhà cung cấp", "Anthropic", "OpenAI", "bỏ qua"),
			"api_key": ("khóa bí mật", "mã hóa", "không hiện lại", "Log"),
			"model_classify": ("Setting", "phân loại", "claude-haiku", "trần token"),
			"model_reason": ("lập luận", "không dùng"),
			"try_order": ("99", "nhỏ", "Để trống", "hoặc 0", "lớn hơn 99"),
			"purpose": ("ghi chú", "không ảnh hưởng"),
			"budget_month_usd": ("USD", "Nhập 0", "không giới hạn", "ngược"),
			"spent_month_usd": ("mỗi ngày", "Log"),
			"enabled": ("Tắt", "không được thử", "không xóa"),
			"status": ("Tạm nghỉ", "Hết hạn mức", "Lỗi khóa", "Hoạt động"),
			"paused_until": ("tạm nghỉ",),
			"tokens_remaining": ("số token còn lại", "lần gọi gần nhất"),
			"limit_reset_at": ("hạn mức", "nhà cung cấp", "đặt lại"),
			"error_count": ("lỗi liên tiếp", "về 0"),
			"last_error": ("không bao giờ chứa khóa",),
			"last_success_at": ("thành công",),
			"note": ("ghi chú",),
		},
		"section_count": 4,
		"read_only_fields": (
			"spent_month_usd",
			"paused_until",
			"tokens_remaining",
			"limit_reset_at",
			"error_count",
			"last_error",
			"last_success_at",
		),
		"sections": (
			("section_key", "Khóa và model", "label"),
			("section_usage", "Thứ tự thử và ngân sách", "try_order"),
			("section_state", "Trạng thái khóa", "status"),
			("section_note", "Ghi chú", "note"),
		),
	},
	"ERP AI Log": {
		"folder": "erp_ai_log",
		"field_count": 38,
		"phrases": {
			"ticket": ("HD Ticket", "mã phiếu", "lọc"),
			"run_id": ("cùng một lần chạy", "gom"),
			"entry_type": ("classify", "reason", "skip", "phân loại", "lập luận"),
			"turn": ("Lượt 0", "lượt 1", "lập luận"),
			"trigger": ("ticket_insert", "comment_mention", "bình luận"),
			"instructor": ("ERP AI Instructor", "giao việc", "chủ phiếu", "ticket_insert", "dòng reason"),
			"model": ("model", "lần gọi"),
			"change_proposal": ("ERP AI Change Proposal", "dòng change", "để trống"),
			"change_step": (
				"propose",
				"approve",
				"reject",
				"apply",
				"fail",
				"stale",
				"undo",
				"mỗi bước một dòng",
			),
			"actor": ("người thực hiện", "người duyệt", "agent", "không suy từ"),
			"input_tokens": ("token", "gửi lên"),
			"output_tokens": ("token", "model trả về"),
			"cache_creation_input_tokens": ("ghi vào cache", "token"),
			"cache_read_input_tokens": ("đọc từ cache", "token"),
			"cost_usd": ("USD", "đơn giá", "Setting", "đã chi trong tháng"),
			"credential_label": ("nhãn", "khóa", "thử cuối cùng", "gateway_error"),
			"keys_tried": ("danh sách", "nhãn khóa", "kết quả"),
			"latency_ms": ("mili giây", "lần gọi", "ghi 0"),
			"stop_reason": (
				"ví dụ",
				"tool_use",
				"end_turn",
				"max_turns",
				"time_budget",
				"gateway_error",
				"unparseable",
				"not_sendable",
				"daily_limit",
				"level_L0",
			),
			"tools_called": ("tool", "trong lượt này"),
			"actions": ("hành động", "phiếu"),
			"value_before": ("JSON", "trước khi"),
			"value_after": ("JSON", "sau khi"),
			"skipped_fields": ("bỏ qua", "phân loại"),
			"predicted_category": ("đầu mục", "A đến F"),
			"predicted_confidence": ("Cao", "Trung bình", "Thấp", "ai_confidence"),
			"predicted_ticket_type": ("loại phiếu", "dự đoán"),
			"predicted_agent_group": ("nhóm xử lý", "dự đoán"),
			"predicted_priority": ("ưu tiên", "dự đoán"),
			"predicted_complexity": ("độ phức tạp", "1 đến 3", "ghi 0"),
			"predicted_importance": ("độ quan trọng", "1 đến 3", "ghi 0"),
			"predicted_score_reason": ("lý do", "không có điểm"),
			"predicted_assignee": ("người phụ trách", "dự đoán"),
			"applied": ("đã ghi", "phiếu"),
			"human_corrected_to": ("loại phiếu", "nhóm xử lý", "ưu tiên", "AI đã dự đoán"),
			"human_corrected_by": ("người đổi", "AI đã dự đoán"),
			"human_corrected_at": ("lần sửa đầu", "AI đã dự đoán"),
			"error": ("lỗi", "không có khóa"),
		},
		"section_count": 6,
		"read_only_fields": (
			"ticket",
			"run_id",
			"entry_type",
			"turn",
			"trigger",
			"instructor",
			"model",
			"change_proposal",
			"change_step",
			"actor",
			"input_tokens",
			"output_tokens",
			"cache_creation_input_tokens",
			"cache_read_input_tokens",
			"cost_usd",
			"credential_label",
			"keys_tried",
			"latency_ms",
			"stop_reason",
			"tools_called",
			"actions",
			"value_before",
			"value_after",
			"skipped_fields",
			"predicted_category",
			"predicted_confidence",
			"predicted_ticket_type",
			"predicted_agent_group",
			"predicted_priority",
			"predicted_complexity",
			"predicted_importance",
			"predicted_score_reason",
			"predicted_assignee",
			"applied",
			"human_corrected_to",
			"human_corrected_by",
			"human_corrected_at",
			"error",
		),
		"sections": (
			("section_run", "Lần chạy", "ticket"),
			("section_usage", "Token, chi phí và khóa", "input_tokens"),
			("section_changes", "Tool và thay đổi trên phiếu", "tools_called"),
			("section_prediction", "Dự đoán phân loại", "predicted_category"),
			("section_correction", "Người sửa sau dự đoán", "human_corrected_to"),
			("section_error", "Lỗi", "error"),
		),
	},
}

# FEAT-004 design 2.4: exact contract of the code-change block of ERP AI Setting.
CODE_CHANGE_FIELDS = {
	"code_change_enabled": {
		"fieldtype": "Check",
		"label": "Cho phép sửa code và lệnh bench",
		"default": "0",
		"description": "Bật thì bot được đề xuất sửa code và lệnh bench, chỉ ở mức L3 và khi có người ra lệnh; "
		"mọi thay đổi phải được duyệt trên form đề xuất. Mỗi thay đổi đã áp dụng thành một commit git local; "
		"bot không push. Tắt thì bot trở lại như cũ.",
	},
	"code_change_apps": {
		"fieldtype": "Small Text",
		"label": "App được phép sửa",
		"default": None,
		"description": "Mỗi dòng một tên thư mục app trong apps/. Có thể thêm app lõi frappe, erpnext, helpdesk, hrms; "
		"sửa app lõi ảnh hưởng mọi site trên bench. Không bao giờ được thêm erp_ai. "
		"Bỏ trống thì không file nào được sửa.",
	},
}


# Wordings that contradicted the code that writes the field (T5 review round 1).
FORBIDDEN_PHRASES = {
	"ERP AI Log": {
		"instructor": ("người ra lệnh", "khi phiếu mới tạo"),
		"tools_called": ("lần chạy này",),
		"predicted_confidence": ("thường khiến", "không được áp dụng"),
		"stop_reason": ("là lỗi khi gọi nhà cung cấp",),
		"latency_ms": ("có thể để trống",),
	},
}


def load_doctype(config):
	path = DOCTYPE_DIR / config["folder"] / f"{config['folder']}.json"
	return json.loads(path.read_text(encoding="utf-8"))


def visible_fields(doctype_json):
	return [
		field
		for field in doctype_json["fields"]
		if field["fieldtype"] not in BREAK_TYPES and not field.get("hidden")
	]


def section_breaks(doctype_json):
	return [field for field in doctype_json["fields"] if field["fieldtype"] == "Section Break"]


class TestDoctypeDescriptions(FrappeTestCase):
	def each_doctype(self):
		return [(doctype, config, load_doctype(config)) for doctype, config in DOCTYPE_CONFIG.items()]

	def test_every_visible_field_has_description(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				fields = visible_fields(doctype_json)
				self.assertEqual(len(fields), config["field_count"])
				missing = [f["fieldname"] for f in fields if not (f.get("description") or "").strip()]
				self.assertEqual(
					missing, [], f"{doctype}: thiếu mô tả {len(missing)}/{len(fields)}: {missing}"
				)

	def test_descriptions_at_most_400_chars(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				too_long = {
					f["fieldname"]: len(f["description"])
					for f in visible_fields(doctype_json)
					if len(f.get("description") or "") > MAX_DESCRIPTION_CHARS
				}
				self.assertEqual(too_long, {}, f"{doctype}: mô tả dài quá {MAX_DESCRIPTION_CHARS} ký tự")

	def test_required_phrases_present(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				by_name = {f["fieldname"]: f for f in visible_fields(doctype_json)}
				self.assertEqual(set(config["phrases"]), set(by_name), f"{doctype}: cấu hình test lệch field")
				missing = {}
				for fieldname, phrases in config["phrases"].items():
					description = by_name[fieldname].get("description") or ""
					absent = [p for p in phrases if p.lower() not in description.lower()]
					if absent:
						missing[fieldname] = absent
				self.assertEqual(missing, {}, f"{doctype}: thiếu cụm")

	def test_forbidden_phrases_absent(self):
		for doctype, forbidden in FORBIDDEN_PHRASES.items():
			by_name = {f["fieldname"]: f for f in visible_fields(load_doctype(DOCTYPE_CONFIG[doctype]))}
			present = {}
			for fieldname, phrases in forbidden.items():
				description = (by_name[fieldname].get("description") or "").lower()
				found = [p for p in phrases if p.lower() in description]
				if found:
					present[fieldname] = found
			self.assertEqual(present, {}, f"{doctype}: còn cụm sai")

	def test_read_only_fields_say_system_writes(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				by_name = {f["fieldname"]: f for f in visible_fields(doctype_json)}
				read_only = {f for f, field in by_name.items() if field.get("read_only")}
				self.assertEqual(read_only, set(config["read_only_fields"]))
				for fieldname in read_only:
					description = by_name[fieldname].get("description") or ""
					self.assertIn(SYSTEM_WRITES, description, f"{doctype}.{fieldname}")
					self.assertIn(NOT_EDITABLE, description, f"{doctype}.{fieldname}")

	def test_section_breaks_labelled_in_vietnamese(self):
		for doctype, config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				breaks = section_breaks(doctype_json)
				self.assertGreaterEqual(len(breaks), 2)
				self.assertEqual(len(breaks), config["section_count"])
				expected = [(name, label) for name, label, _first in config["sections"]]
				self.assertEqual([(b["fieldname"], b.get("label")) for b in breaks], expected)
				for section in breaks:
					self.assertTrue(VIETNAMESE_ACCENTS.search(section["label"]), section["fieldname"])
					self.assertNotIn("(USD)", section["label"])
				order = doctype_json["field_order"]
				for name, _label, first in config["sections"]:
					self.assertEqual(order.index(first), order.index(name) + 1, f"{doctype}: {name}")

	def test_descriptions_have_no_sensitive_data(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for field in visible_fields(doctype_json):
					description = field.get("description") or ""
					where = f"{doctype}.{field['fieldname']}"
					self.assertNotIn("sk-", description, where)
					self.assertNotIn("miyano", description.lower(), where)
					for email in EMAIL_PATTERN.findall(description):
						self.assertTrue(email.lower().endswith(SAFE_EMAIL_DOMAINS), f"{where}: {email}")

	def test_descriptions_contain_no_stored_setting_values(self):
		setting = frappe.get_single("ERP AI Setting")
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		stored = {}
		for field in visible_fields(doctype_json):
			if field["fieldtype"] in ("Table", "Password"):
				continue
			value = setting.get(field["fieldname"])
			if isinstance(value, str) and len(value.strip()) >= MIN_STORED_VALUE_CHARS:
				stored[field["fieldname"]] = value.strip().lower()
		for field in visible_fields(doctype_json):
			description = (field.get("description") or "").lower()
			for source, value in stored.items():
				self.assertNotIn(
					value, description, f"{field['fieldname']} chứa giá trị đang lưu của {source}"
				)

	def test_skipped_fields_still_follows_value_after(self):
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Log"])
		order = doctype_json["field_order"]
		self.assertEqual(order.index("skipped_fields"), order.index("value_after") + 1)
		names = [f["fieldname"] for f in doctype_json["fields"]]
		self.assertEqual(names, order)

	def test_section_breaks_carry_only_label(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for section in section_breaks(doctype_json):
					self.assertEqual(
						set(section), {"fieldname", "fieldtype", "label"}, f"{doctype}.{section['fieldname']}"
					)

	def test_code_change_block_follows_feat006_fields(self):
		doctype_json = load_doctype(DOCTYPE_CONFIG["ERP AI Setting"])
		order = doctype_json["field_order"]
		start = order.index("prompt_digest")
		self.assertEqual(
			order[start : start + 5],
			[
				"prompt_digest",
				"section_code_change",
				"code_change_enabled",
				"code_change_apps",
				"section_alerts",
			],
		)
		self.assertLess(order.index("routing_rules"), order.index("section_code_change"))
		by_name = {f["fieldname"]: f for f in doctype_json["fields"]}
		actual = {
			fieldname: {key: by_name[fieldname].get(key) for key in expected}
			for fieldname, expected in CODE_CHANGE_FIELDS.items()
		}
		self.assertEqual(actual, CODE_CHANGE_FIELDS)
		self.assertFalse(any(by_name[name].get("read_only") for name in CODE_CHANGE_FIELDS))
