import frappe
from frappe.model.document import Document

from erp_ai import gateway
from erp_ai.agent.classification import validate_mapping
from erp_ai.constants import CREDENTIAL_DOCTYPE, KEY_STATUS_ACTIVE, KEY_STATUS_BAD_KEY, SETTING_DOCTYPE

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
}
PRICE_FIELDS = (
	"price_input_per_mtok",
	"price_cache_write_per_mtok",
	"price_cache_read_per_mtok",
	"price_output_per_mtok",
)
PROBE_RESULT_FIELDS = ("label", "ok", "error_kind", "status")


class ERPAISetting(Document):
	def validate(self):
		self.restore_self_managed_fields()
		self.check_labels()
		validate_mapping(self.category_mapping)
		self.check_limits()
		self.check_enabled_requirements()

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

	def check_limits(self):
		for fieldname, (label, low, high) in INT_LIMITS.items():
			value = self.get(fieldname) or 0
			if value < low or (high is not None and value > high):
				bound = f"từ {low} đến {high}" if high is not None else f"không nhỏ hơn {low}"
				frappe.throw(f"{label} phải {bound}")
		for fieldname in PRICE_FIELDS:
			if (self.get(fieldname) or 0) < 0:
				frappe.throw("Đơn giá không được âm")

	def check_enabled_requirements(self):
		if not self.enabled:
			return
		if any((self.get(fieldname) or 0) <= 0 for fieldname in PRICE_FIELDS):
			frappe.throw("Không thể bật agent khi chưa nhập đủ 4 đơn giá lớn hơn 0")
		if not (self.trigger_keyword or "").strip():
			frappe.throw("Không thể bật agent khi từ khóa kích hoạt rỗng")


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
