import frappe

from erp_ai.agent import policy
from erp_ai.constants import LESSON_DOCTYPE, LOG_DOCTYPE, SETTING_DOCTYPE


def schema_present() -> bool:
	"""The lesson DocType, the lesson switch of the Setting and the lessons column of the Log all exist."""
	return bool(
		frappe.db.exists("DocType", LESSON_DOCTYPE)
		and frappe.get_meta(SETTING_DOCTYPE).has_field(policy.LESSONS_ENABLED_FIELD)
		and frappe.get_meta(LOG_DOCTYPE).has_field("lessons_used")
	)
