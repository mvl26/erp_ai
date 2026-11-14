import os

import frappe
from frappe.model.document import Document

from erp_ai import gateway
from erp_ai.agent import policy
from erp_ai.agent.classification import validate_mapping
from erp_ai.agent.hard_bans import hard_ban_reason
from erp_ai.agent.routing import validate_routing_config
from erp_ai.agent.tools import site_api, source
from erp_ai.constants import (
	ACTION_CREATE_CUSTOM_FIELD,
	ACTION_UPDATE_FIELDS,
	ANSWER_DELAY_MAX_S,
	CATALOG_ACTIONS,
	CATEGORIES,
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	SETTING_DOCTYPE,
)

SELF_MANAGED_KEY_FIELDS = (
	"status",
	"paused_until",
	"tokens_remaining",
	"limit_reset_at",
	"error_count",
	"last_error",
	"last_success_at",
	"spent_month_usd",
)
NEW_KEY_DEFAULTS = {
	"status": KEY_STATUS_ACTIVE,
	"paused_until": None,
	"tokens_remaining": None,
	"limit_reset_at": None,
	"error_count": 0,
	"last_error": "",
	"last_success_at": None,
	"spent_month_usd": 0,
}

# fieldname: (label, min, max); max None = unbounded (NFR-3).
INT_LIMITS = {
	"max_turns_per_run": ("Số lượt tối đa mỗi lần chạy", 1, 20),
	"max_runs_per_ticket_per_day": ("Số lần chạy tối đa mỗi phiếu mỗi ngày", 1, 50),
	"max_keys_per_call": ("Số khóa tối đa mỗi lời gọi", 1, 10),
	"request_timeout_s": ("Timeout mỗi lời gọi API", 5, 300),
	"monthly_budget_usd": ("Ngân sách tháng", 0, None),
	"answer_delay_min_s": ("Trễ trả lời tối thiểu", 0, ANSWER_DELAY_MAX_S),
	"answer_delay_max_s": ("Trễ trả lời tối đa", 0, ANSWER_DELAY_MAX_S),
	"confidence_threshold": ("Ngưỡng độ tin cậy", 0, 100),
	"auto_approve_streak": ("Số lần duyệt liên tiếp để Tự làm", 1, 100),
	"close_silent_f_days": ("Số ngày chờ trước khi đóng phiếu F", 1, 30),
	"knowledge_search_limit": ("Số kết quả tìm tri thức tối đa", 1, 20),
	"report_row_limit": ("Số dòng báo cáo tối đa", 1, 100),
}
THINKING_TEXT_MAX_CHARS = 5000
PRICE_FIELDS = (
	"price_input_per_mtok",
	"price_cache_write_per_mtok",
	"price_cache_read_per_mtok",
	"price_output_per_mtok",
)
PROBE_RESULT_FIELDS = ("label", "ok", "error_kind", "status")
# D-7: the switches are the Check fields of this section, read from the meta; no switch name is written here.
PERMISSION_SECTION = "section_permissions"
PERMISSION_NOTICE_TITLE = "Đã bật quyền mở rộng"
# design.md:214-221: the only catalog actions whose row names a DocType; the others act on a fixed one.
DOCTYPE_ACTIONS = (ACTION_CREATE_CUSTOM_FIELD, ACTION_UPDATE_FIELDS)
# AC-24: the settings naming an HD Ticket field, in form order; the due field must hold a date (E-2).
TICKET_DOCTYPE = "HD Ticket"
TICKET_FIELD_SETTINGS = (
	"field_ticket_nature",
	"field_erp_module",
	"field_origin",
	"field_due_date",
	"field_project",
	"field_item_code",
	"field_serial_no",
)
DUE_FIELD_SETTING = "field_due_date"
DUE_FIELD_TYPES = ("Date", "Datetime")


def permission_switch_fields(meta) -> list:
	"""The Check fields between `PERMISSION_SECTION` and the next Section Break, in form order."""
	switches, inside = [], False
	for field in meta.fields:
		if field.fieldtype == "Section Break":
			inside = field.fieldname == PERMISSION_SECTION
		elif inside and field.fieldtype == "Check":
			switches.append(field)
	return switches


class ERPAISetting(Document):
	def validate(self):
		self.restore_self_managed_fields()
		self.check_labels()
		validate_mapping(self.category_mapping)
		self.check_routing_rules()
		policy.validate_change_apps(self, source.get_source_root())
		self.check_limits()
		self.check_status_settings()
		self.check_enabled_requirements()
		self.check_ticket_field_names()
		self.check_catalog_rules()
		self.check_user_templates()
		self.check_manuals_dir()

	def on_update(self):
		self.notify_permission_switches()

	def notify_permission_switches(self):
		"""AC-4: one notice listing every switch turned 0 -> 1 by this save, then the site environment."""
		before = self.get_doc_before_save()
		escape = frappe.utils.escape_html
		lines = [
			f"<b>{escape(field.label)}</b>: {escape(field.description or '')}"
			for field in permission_switch_fields(self.meta)
			if self.get(field.fieldname) and not (before and before.get(field.fieldname))
		]
		if not lines:
			return
		lines.append(f"Môi trường site: {escape(self.site_environment or '')}")
		frappe.msgprint("<br>".join(lines), title=PERMISSION_NOTICE_TITLE, indicator="orange")

	def restore_self_managed_fields(self):
		# (b) the monthly spend is written only by the scheduler
		self.spent_this_month_usd = frappe.db.get_single_value(
			SETTING_DOCTYPE, "spent_this_month_usd", cache=False
		)
		stored = {
			row.name: row
			for row in frappe.get_all(
				CREDENTIAL_DOCTYPE,
				filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE},
				fields=["name", *SELF_MANAGED_KEY_FIELDS],
			)
		}
		for row in self.credentials:
			saved = stored.get(row.name)
			if not saved:
				row.update(NEW_KEY_DEFAULTS)
				continue
			human_reactivated = saved.status == KEY_STATUS_BAD_KEY and row.status == KEY_STATUS_ACTIVE
			for fieldname in SELF_MANAGED_KEY_FIELDS:
				row.set(fieldname, saved[fieldname])
			if human_reactivated:
				row.update({"status": KEY_STATUS_ACTIVE, "error_count": 0, "last_error": ""})

	def check_labels(self):
		seen = set()
		for row in self.credentials:
			label = (row.label or "").strip()
			if not label:
				frappe.throw(f"Dòng {row.idx}: nhãn khóa không được để trống")
			if label.lower() in seen:
				frappe.throw(f"Nhãn khóa '{label}' bị trùng")
			seen.add(label.lower())

	def check_routing_rules(self):
		validate_routing_config(self.routing_rules)

	def check_limits(self):
		for fieldname, (label, low, high) in INT_LIMITS.items():
			value = self.get(fieldname) or 0
			if value < low or (high is not None and value > high):
				bound = f"từ {low} đến {high}" if high is not None else f"không nhỏ hơn {low}"
				frappe.throw(f"{label} phải {bound}")
		for fieldname in PRICE_FIELDS:
			if (self.get(fieldname) or 0) < 0:
				frappe.throw("Đơn giá không được âm")

	def check_status_settings(self):
		# Saved as "" (not NULL) so that _ensure_default_settings never re-enables a switched-off indicator.
		self.thinking_text = self.thinking_text or ""
		if (self.answer_delay_min_s or 0) > (self.answer_delay_max_s or 0):
			frappe.throw("Trễ trả lời tối thiểu không được lớn hơn trễ trả lời tối đa")
		if len(self.thinking_text) > THINKING_TEXT_MAX_CHARS:
			frappe.throw(f"Chữ chỉ báo khi đang suy nghĩ không được dài quá {THINKING_TEXT_MAX_CHARS} ký tự")

	def check_enabled_requirements(self):
		if not self.enabled:
			return
		if any((self.get(fieldname) or 0) <= 0 for fieldname in PRICE_FIELDS):
			frappe.throw("Không thể bật agent khi chưa nhập đủ 4 đơn giá lớn hơn 0")
		if not (self.trigger_keyword or "").strip():
			frappe.throw("Không thể bật agent khi từ khóa kích hoạt rỗng")

	def check_ticket_field_names(self):
		"""AC-24: each set field name, trimmed, must be a field of HD Ticket by its exact name (E-1, E-2, E-3)."""
		ticket_meta = frappe.get_meta(TICKET_DOCTYPE)
		for fieldname in TICKET_FIELD_SETTINGS:
			name = (self.get(fieldname) or "").strip()
			self.set(fieldname, name)
			if not name:
				continue
			field = ticket_meta.get_field(name)
			if not field:
				label = self.meta.get_label(fieldname)
				frappe.throw(f"Trường '{frappe.utils.escape_html(name)}' không có trên HD Ticket ({label})")
			if fieldname == DUE_FIELD_SETTING and field.fieldtype not in DUE_FIELD_TYPES:
				frappe.throw("Trường Hạn hoàn thành phải có kiểu Date hoặc Datetime")
		self.origin_board_value = (self.origin_board_value or "").strip()
		if self.origin_board_value and not self.field_origin:
			frappe.throw("Đặt giá trị Chỉ đạo BGĐ thì phải đặt tên trường Nguồn phát sinh")

	def check_catalog_rules(self):
		"""AC-29, ADR-031 decision 1: refuse the first catalog row breaking an E-4 rule; normalise categories."""
		seen = {}
		for row in self.catalog_rules:
			reason = catalog_rule_error(row)
			if not reason:
				key = (row.action, row.target_doctype or "")
				if key in seen:
					reason = f"trùng với dòng {seen[key]}"
				seen[key] = row.idx
			if reason:
				frappe.throw(f"Danh mục dòng {row.idx}: {reason}")

	def check_user_templates(self):
		"""AC-30 (1): refuse the first account template breaking an E-5 rule."""
		seen = {}
		for row in self.user_templates:
			name = (row.template_name or "").strip()
			reason = user_template_error(row) if name else "tên mẫu không được để trống"
			if not reason:
				key = name.casefold()
				if key in seen:
					reason = f"trùng tên với dòng {seen[key]}"
				seen[key] = row.idx
			if reason:
				frappe.throw(f"Mẫu tài khoản dòng {row.idx}: {reason}")

	def check_manuals_dir(self):
		"""AC-47, E-7: a set manuals path, trimmed, must be an existing directory under apps/, not apps/ itself.

		`resolve_safe_path` refuses a path leaving the source root and the root itself, so only the directory
		test is added here.
		"""
		self.manuals_dir = (self.manuals_dir or "").strip()
		if not self.manuals_dir:
			return
		path = source.resolve_safe_path(self.manuals_dir)
		if not (path and os.path.isdir(path)):
			typed = frappe.utils.escape_html(self.manuals_dir)
			frappe.throw(f"Kho HDSD '{typed}' phải là thư mục có sẵn dưới apps/")


def user_template_error(row) -> str | None:
	"""The first E-5 role reason of this row, or None; on success the roles are stored one per line by real name.

	The ban is checked on the real name too: tabRole's collation ignores case and accents, so "Gúest" finds Guest.
	"""
	forbidden = {role.casefold(): role for role in site_api.FORBIDDEN_ROLES}
	roles = [line.strip() for line in (row.roles or "").splitlines() if line.strip()]
	if not roles:
		return "cần ít nhất một vai trò"
	stored = []
	for role in roles:
		if role.casefold() in forbidden:
			return f"vai trò {forbidden[role.casefold()]} bị cấm cho bot"
		real = frappe.db.get_value("Role", role)
		if not real:
			return f"không có vai trò {role}"
		if real in site_api.FORBIDDEN_ROLES:
			return f"vai trò {real} bị cấm cho bot"
		stored.append(real)
	row.roles = "\n".join(stored)
	return None


def catalog_rule_error(row) -> str | None:
	"""The first E-4 reason of this row alone (not the duplicate check), or None.

	On success the row's DocType is set to its stored name and its categories to the form "A,B".
	"""
	if row.action not in CATALOG_ACTIONS:
		return "hành động không hợp lệ"
	takes_doctype = row.action in DOCTYPE_ACTIONS
	if row.target_doctype and not takes_doctype:
		return "hành động này không nhận DocType"
	if takes_doctype and not row.target_doctype:
		return "hành động này cần DocType"
	if row.target_doctype:
		doctype = frappe.db.get_value("DocType", row.target_doctype)
		if not doctype:
			return f"không có DocType {row.target_doctype}"
		ban = hard_ban_reason(doctype)
		if ban:
			return f"DocType {doctype} bị cấm cứng: {ban}"
		row.target_doctype = doctype
	fields = [line.strip() for line in (row.fields or "").splitlines() if line.strip()]
	if fields and row.action != ACTION_UPDATE_FIELDS:
		return "hành động này không nhận danh sách trường"
	if row.action == ACTION_UPDATE_FIELDS:
		if not fields:
			return "cần ít nhất một trường"
		meta = frappe.get_meta(row.target_doctype)
		for fieldname in fields:
			if not meta.has_field(fieldname):
				return f"trường {fieldname} không có trên {row.target_doctype}"
	letters = [part.strip() for part in (row.categories or "").split(",")]
	if not all(letter in CATEGORIES for letter in letters):
		# The escape is the en dash of the design text (E-4); ruff RUF001 refuses the literal character.
		return "đầu mục phải là các chữ A\u2013F cách nhau bằng dấu phẩy"
	row.categories = ",".join(sorted(set(letters)))
	return None


@frappe.whitelist(methods=["POST"])
def check_keys(label: str | None = None) -> list[dict]:
	"""Probe every key row (or the one with this label); return only the safe result fields (AC-19)."""
	frappe.only_for("System Manager")
	rows = frappe.get_all(
		CREDENTIAL_DOCTYPE,
		filters={"parent": SETTING_DOCTYPE, "parenttype": SETTING_DOCTYPE, "parentfield": "credentials"},
		fields=["name", "label"],
		order_by="idx",
	)
	if label is not None:
		rows = [row for row in rows if row.label == label]
		if not rows:
			frappe.throw(f"Không có khóa '{frappe.utils.escape_html(label)}'")
	results = []
	for row in rows:
		probed = gateway.probe_credential(row.name)
		results.append({fieldname: probed.get(fieldname) for fieldname in PROBE_RESULT_FIELDS})
	return results
