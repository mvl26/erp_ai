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


DEPT_CONFIG = {
	"departments": {"Kế toán": {"team": "Accounting", "head": "head@x.com"}, "HR": {"team": "", "head": ""}}
}


# D/E carry a decoy mapping group: routing must ignore it and use the department table (AC-5).
DECOY_MAPPING = {
	**DEFAULT_CATEGORY_MAPPING,
	"D": {**DEFAULT_CATEGORY_MAPPING["D"], "agent_group": "IT"},
	"E": {**DEFAULT_CATEGORY_MAPPING["E"], "agent_group": "IT"},
}


def _decide_team(category, department=None, config=None, team_exists=None, is_excluded_team=None):
	return routing.decide_route(
		Classification(category=category, confidence="Cao", importance=1, department=department),
		"Thông thường",
		DECOY_MAPPING,
		DEPT_CONFIG if config is None else config,
		team_exists=team_exists or (lambda team: True),
		is_excluded_team=is_excluded_team or (lambda team: False),
		is_active_agent=lambda user: True,
	)


def _team_notes(decision):
	return [note for note in decision.notes if note["field"] == "agent_group"]


class TestDecideTeam(FrappeTestCase):
	def test_abcf_team_from_mapping(self):
		# A/B/C/F are not filtered by team_exists / is_excluded_team: behaviour as today.
		for category in "ABCF":
			decision = _decide_team(
				category,
				department="Kế toán",
				team_exists=lambda team: False,
				is_excluded_team=lambda team: True,
			)
			self.assertEqual(decision.agent_group, "IT")
			self.assertEqual(decision.notes, ())
		empty = routing.decide_route(
			Classification(category="B", confidence="Cao"),
			"x",
			{"B": {"agent_group": ""}},
			{},
			team_exists=lambda team: True,
			is_excluded_team=lambda team: False,
			is_active_agent=lambda user: True,
		)
		self.assertIsNone(empty.agent_group)

	def test_de_team_from_department(self):
		for category in "DE":
			for department in ("Kế toán", "KẾ TOÁN", "  kế   toán ", "Kế\ttoán"):
				with self.subTest(category=category, department=department):
					decision = _decide_team(category, department=department)
					self.assertEqual(decision.agent_group, "Accounting")
					self.assertEqual(_team_notes(decision), [])

	def test_de_config_key_case_and_spaces(self):
		config = {"departments": {"  KẾ TOÁN ": {"team": "Accounting", "head": ""}}}
		for category in "DE":
			for department in ("Kế toán", "kế  toán"):
				with self.subTest(category=category, department=department):
					decision = _decide_team(category, department=department, config=config)
					self.assertEqual(decision.agent_group, "Accounting")
					self.assertEqual(_team_notes(decision), [])

	def test_de_team_skip_reasons(self):
		def reason(decision):
			self.assertIsNone(decision.agent_group)
			self.assertEqual(len(_team_notes(decision)), 1)
			return _team_notes(decision)[0]["reason"]

		self.assertEqual(reason(_decide_team("D", department=None)), "không có bộ phận")
		self.assertEqual(reason(_decide_team("D", department="   ")), "không có bộ phận")
		self.assertEqual(
			reason(_decide_team("E", department="Kho")), "bộ phận 'Kho' không có trong bảng bộ phận"
		)
		self.assertEqual(reason(_decide_team("D", department="HR")), "nhóm '' không tồn tại")
		self.assertEqual(
			reason(_decide_team("D", department="Kế toán", team_exists=lambda team: False)),
			"nhóm 'Accounting' không tồn tại",
		)
		self.assertEqual(
			reason(_decide_team("E", department="Kế toán", is_excluded_team=lambda team: True)),
			"nhóm 'Accounting' bị loại trừ",
		)
		both = _decide_team(
			"D", department="Kế toán", team_exists=lambda team: False, is_excluded_team=lambda team: True
		)
		self.assertEqual(reason(both), "nhóm 'Accounting' không tồn tại")
