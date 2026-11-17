import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import SETTING_DOCTYPE
from erp_ai.patches import chg013_seed_once_for_existing_sites as seed_patch
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

PATCHES_TXT = Path(__file__).resolve().parent.parent / "patches.txt"
PATCH_LINE = "erp_ai.patches.chg013_seed_once_for_existing_sites"
ENABLED_AT = "2026-11-17 09:30:00"
EARLIER = "2026-01-02 03:04:05"


def post_model_sync_lines() -> list[str]:
	lines = [line.strip() for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()]
	section = lines[lines.index("[post_model_sync]") + 1 :]
	return [line for line in section if line and not line.startswith("#")]


def stored_settings() -> dict:
	return dict(frappe.db.sql("select field, value from `tabSingles` where doctype=%s", SETTING_DOCTYPE))


def stored(fieldname):
	return frappe.db.get_single_value(SETTING_DOCTYPE, fieldname, cache=False)


class TestSeedOnceForExistingSites(FrappeTestCase):
	"""CHG-013: the one patch gives a site that already had the app the seed that install gives a new site."""

	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def mapped_type(self) -> str:
		name = f"CHG013 {frappe.generate_hash(length=6)} patch type"
		set_agent_settings(
			category_mapping=json.dumps({"A": {"ticket_type": name, "agent_group": "", "priority": "High"}})
		)
		return name

	def test_execute_fills_a_missing_default_and_creates_a_mapped_type(self):
		name = self.mapped_type()
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "thinking_text"})
		seed_patch.execute()
		self.assertEqual(stored("thinking_text"), "Đang suy nghĩ…")
		self.assertTrue(frappe.db.exists("HD Ticket Type", name))

	def test_second_execute_changes_nothing(self):
		self.mapped_type()
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "thinking_text"})
		seed_patch.execute()
		settings = stored_settings()
		types = frappe.db.count("HD Ticket Type")
		seed_patch.execute()
		self.assertEqual(stored_settings(), settings)
		self.assertEqual(frappe.db.count("HD Ticket Type"), types)

	def test_enable_mark_set_once_for_an_enabled_site(self):
		set_agent_settings(enabled=1)
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "agent_enabled_at"})
		with patch("frappe.utils.now_datetime", return_value=frappe.utils.get_datetime(ENABLED_AT)):
			seed_patch.execute()
		self.assertEqual(stored_settings().get("agent_enabled_at"), ENABLED_AT)
		with patch(
			"frappe.utils.now_datetime", return_value=frappe.utils.get_datetime("2026-12-01 00:00:00")
		):
			seed_patch.execute()
		self.assertEqual(stored_settings().get("agent_enabled_at"), ENABLED_AT)

	def test_enable_mark_kept_when_present(self):
		set_agent_settings(enabled=1, agent_enabled_at=EARLIER)
		seed_patch.execute()
		self.assertEqual(stored_settings().get("agent_enabled_at"), EARLIER)

	def test_enable_mark_untouched_when_not_enabled(self):
		set_agent_settings(enabled=0)
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "agent_enabled_at"})
		seed_patch.execute()
		self.assertNotIn("agent_enabled_at", stored_settings())

	def test_patch_listed_once_after_model_sync(self):
		self.assertEqual(post_model_sync_lines().count(PATCH_LINE), 1)
