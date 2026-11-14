from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import LOG_DOCTYPE
from erp_ai.patches import feat007_unknown_confidence_pct
from erp_ai.test_utils import keep_agent_settings, make_log_entry

FIELD = "predicted_confidence_pct"
UNKNOWN_PCT = -1
PATCHES_TXT = Path(__file__).resolve().parent.parent / "patches.txt"
PATCH_LINE = "erp_ai.patches.feat007_unknown_confidence_pct"


def post_model_sync_lines() -> list[str]:
	lines = [line.strip() for line in PATCHES_TXT.read_text(encoding="utf-8").splitlines()]
	section = lines[lines.index("[post_model_sync]") + 1 :]
	return [line for line in section if line and not line.startswith("#")]


def column_default() -> str | None:
	rows = frappe.db.sql(
		"""select COLUMN_DEFAULT from information_schema.columns
		where table_schema = database() and table_name = %s and column_name = %s""",
		(f"tab{LOG_DOCTYPE}", FIELD),
	)
	return rows[0][0] if rows else None


def stored_pct(names: list[str]) -> list[int]:
	return [frappe.db.get_value(LOG_DOCTYPE, name, FIELD) for name in names]


def write_pct(name: str, value: int) -> None:
	frappe.db.sql(f"update `tab{LOG_DOCTYPE}` set `{FIELD}` = %s where name = %s", (value, name))


class TestUnknownConfidencePct(FrappeTestCase):
	"""design-w0-fixes-2.md section 1: -1 means "unknown"; the patch turns the old default 0 into -1 once (NFR-4)."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def make_rows(self, values: list[int]) -> list[str]:
		names = [make_log_entry(entry_type="classify") for _ in values]
		for name, value in zip(names, values, strict=True):
			write_pct(name, value)
		return names

	def test_column_default_is_minus_one(self):
		self.assertEqual(frappe.get_meta(LOG_DOCTYPE).get_field(FIELD).default, "-1")
		self.assertEqual(int(column_default()), UNKNOWN_PCT)

	def test_row_without_pct_reads_minus_one(self):
		without_pct = make_log_entry(entry_type="classify")
		written_zero = make_log_entry(entry_type="classify", predicted_confidence_pct=0)
		self.assertEqual(stored_pct([without_pct, written_zero]), [UNKNOWN_PCT, 0])

	def test_patch_turns_zero_into_minus_one_only(self):
		names = self.make_rows([0, 55, UNKNOWN_PCT])
		feat007_unknown_confidence_pct.execute()
		self.assertEqual(stored_pct(names), [UNKNOWN_PCT, 55, UNKNOWN_PCT])
		feat007_unknown_confidence_pct.execute()
		self.assertEqual(stored_pct(names), [UNKNOWN_PCT, 55, UNKNOWN_PCT])

	def test_patch_loops_until_no_row_changes(self):
		# Batch of 1 with three zero rows: a single UPDATE … LIMIT would leave two rows at 0.
		names = self.make_rows([0, 0, 0])
		with patch.object(feat007_unknown_confidence_pct, "BATCH_SIZE", 1):
			feat007_unknown_confidence_pct.execute()
		self.assertEqual(stored_pct(names), [UNKNOWN_PCT] * 3)
		self.assertFalse(frappe.db.exists(LOG_DOCTYPE, {FIELD: 0}))

	def test_patch_listed_once_after_model_sync(self):
		# The column default must change before the patch runs, so it belongs to [post_model_sync].
		self.assertEqual(post_model_sync_lines().count(PATCH_LINE), 1)
