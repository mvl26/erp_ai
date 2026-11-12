from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import routing
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING, Classification

CONFIG = {"importance_priority": {"1": "", "2": "High", "3": "High"}}

# Expected priority without the urgent tag, per category -> importance 1..3 (guide 16.2 + R1-R5).
EXPECTED = {
	"A": ("High", "High", "Urgent"),
	"B": ("Medium", "High", "High"),
	"C": ("Medium", "High", "High"),
	"D": ("Medium", "High", "High"),
	"E": (None, None, None),
	"F": ("Low", "Low", "Low"),
}


def _decide(category, importance, subject="Thông thường", mapping=None, config=None):
	return routing.decide_route(
		Classification(category=category, confidence="Cao", importance=importance),
		subject,
		DEFAULT_CATEGORY_MAPPING if mapping is None else mapping,
		CONFIG if config is None else config,
		team_exists=lambda team: True,
		is_excluded_team=lambda team: False,
		is_active_agent=lambda user: True,
	)


class TestDecidePriority(FrappeTestCase):
	def test_priorities_constant(self):
		self.assertEqual(routing.PRIORITIES, ("Low", "Medium", "High", "Urgent"))

	def test_priority_matrix_36_cases(self):
		count = 0
		for category, expected in EXPECTED.items():
			for importance in (1, 2, 3):
				for tagged in (False, True):
					subject = "[GẤP] việc" if tagged else "việc"
					want = "Urgent" if tagged else expected[importance - 1]
					with self.subTest(category=category, importance=importance, tagged=tagged):
						self.assertEqual(_decide(category, importance, subject).priority, want)
					count += 1
		self.assertEqual(count, 36)

	def test_spec_samples(self):
		self.assertEqual(_decide("B", 2).priority, "High")
		self.assertEqual(_decide("C", 1).priority, "Medium")
		self.assertEqual(_decide("A", 3).priority, "Urgent")
		self.assertEqual(_decide("F", 3).priority, "Low")
		self.assertIsNone(_decide("E", 2).priority)
		for category in "ABCDEF":
			self.assertEqual(_decide(category, 1, "[GẤP] x").priority, "Urgent")

	def test_urgent_tag_variants_casefold(self):
		for subject in ("[GẬP] x", "lỗi [gấp] ở kho", "[HR][GẤP] y"):
			self.assertEqual(_decide("F", 1, subject).priority, "Urgent", subject)
		for subject in ("GẤP lỗi", "[GẤP lỗi", "", None):
			self.assertEqual(_decide("B", 1, subject).priority, "Medium", repr(subject))

	def test_importance_zero_has_no_minimum(self):
		self.assertEqual(_decide("B", 0).priority, "Medium")
		self.assertIsNone(_decide("B", 0, mapping={"B": {"priority": ""}}).priority)

	def test_config_table_read_each_run(self):
		self.assertEqual(_decide("B", 2, config={"importance_priority": {"2": "Medium"}}).priority, "Medium")
		self.assertEqual(_decide("C", 1, config={"importance_priority": {"1": "Urgent"}}).priority, "Urgent")

	def test_missing_or_empty_config_and_mapping(self):
		self.assertEqual(_decide("B", 3, config={}).priority, "Medium")
		self.assertIsNone(_decide("B", 3, mapping={}, config={}).priority)
		self.assertEqual(_decide("B", 3, mapping={}).priority, "High")
		self.assertIsNone(_decide("B", 3, mapping={"B": {"priority": ""}}, config={}).priority)

	def test_other_values_still_from_mapping(self):
		decision = _decide("B", 2)
		self.assertEqual(decision.ticket_type, DEFAULT_CATEGORY_MAPPING["B"]["ticket_type"])
		self.assertEqual(decision.agent_group, "IT")
