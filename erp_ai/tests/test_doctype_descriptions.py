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
		"field_count": 22,
		"phrases": {
			"enabled": ("Tắt", "4 đơn giá", "từ khóa kích hoạt"),
			"permission_level": ("L0", "L1", "L2", "L3", "ngân sách"),
			"max_turns_per_run": ("1", "20", "dừng"),
			"max_runs_per_ticket_per_day": ("1", "50", "00:00"),
			"max_keys_per_call": ("1", "10", "báo lỗi"),
			"request_timeout_s": ("5", "300", "giây", "khóa kế tiếp"),
			"monthly_budget_usd": ("USD", "L1", "0", "không phải"),
			"spent_this_month_usd": ("mỗi ngày", "tổng chi phí"),
			"price_input_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_write_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_cache_read_per_mtok": ("USD", "triệu token", "không được âm"),
			"price_output_per_mtok": ("USD", "triệu token", "không được âm"),
			"model_classify_default": ("phân loại", "model"),
			"trigger_keyword": ("@ai", "không phân biệt hoa thường"),
			"thinking_text": ("Để trống", "giây"),
			"answer_delay_min_s": ("giây", "0", "30", "bình luận"),
			"answer_delay_max_s": ("giây", "0", "30", "bình luận"),
			"excluded_teams": ("mỗi dòng", "không phân biệt hoa thường"),
			"category_mapping": ("JSON", "A", "F", "[GẤP]", "Urgent"),
			"prompt_digest": ("lập luận", "phân loại"),
			"alert_recipients": ("mỗi dòng", "canhbao@congty.vn", "dấu phẩy"),
			"credentials": ("không trùng", "Kiểm tra khóa"),
		},
		"section_count": 6,
		"read_only_fields": ("spent_this_month_usd",),
		"sections": (
			("section_activation", "Bật và mức quyền", "enabled"),
			("section_limits", "Giới hạn mỗi lần chạy", "max_turns_per_run"),
			("section_budget", "Ngân sách và đơn giá", "monthly_budget_usd"),
			("section_model", "Model, từ khóa và chỉ báo trả lời", "model_classify_default"),
			("section_routing", "Phân loại và nhóm loại trừ", "excluded_teams"),
			("section_alerts", "Cảnh báo và khóa API", "alert_recipients"),
		),
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
				for fieldname, phrases in config["phrases"].items():
					description = by_name[fieldname].get("description") or ""
					missing = [p for p in phrases if p.lower() not in description.lower()]
					self.assertEqual(missing, [], f"{doctype}.{fieldname}: thiếu cụm {missing}")

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
				if source == field["fieldname"] and value == description:
					continue
				self.assertNotIn(
					value, description, f"{field['fieldname']} chứa giá trị đang lưu của {source}"
				)

	def test_section_breaks_carry_only_label(self):
		for doctype, _config, doctype_json in self.each_doctype():
			with self.subTest(doctype=doctype):
				for section in section_breaks(doctype_json):
					self.assertEqual(
						set(section), {"fieldname", "fieldtype", "label"}, f"{doctype}.{section['fieldname']}"
					)
