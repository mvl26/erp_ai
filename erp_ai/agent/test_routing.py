import json

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import routing
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING, Classification
from erp_ai.constants import AGENT_USER

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
			self.assertEqual(_team_notes(decision), [])
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


ASSIGN_CONFIG = {
	"assignees": {
		"A": {"default": "a.default@x.com", "prefixes": {"[tracecore]": "trace@x.com", "[kho]": "kho@x.com"}},
		"B": {"default": "b.default@x.com", "prefixes": {}},
		"C": {"default": "c.default@x.com", "prefixes": {"[hr]": ""}},
		"F": {"default": "", "prefixes": {}},
	},
	"departments": {
		"Kế toán": {"team": "Accounting", "head": "head@x.com"},
		"HR": {"team": "HR", "head": ""},
	},
}


def _decide_assignee(category, subject="Thông thường", department=None, config=None, is_active_agent=None):
	return routing.decide_route(
		Classification(category=category, confidence="Cao", importance=1, department=department),
		subject,
		DEFAULT_CATEGORY_MAPPING,
		ASSIGN_CONFIG if config is None else config,
		team_exists=lambda team: True,
		is_excluded_team=lambda team: False,
		is_active_agent=is_active_agent or (lambda user: True),
	)


def _assignee_notes(decision):
	return [note["reason"] for note in decision.notes if note["field"] == "assignee"]


class TestDecideAssignee(FrappeTestCase):
	def test_default_when_no_prefix_matches(self):
		for category, want in (("A", "a.default@x.com"), ("B", "b.default@x.com"), ("C", "c.default@x.com")):
			decision = _decide_assignee(category, "Không có tiền tố")
			self.assertEqual(decision.assignee, want)
			self.assertEqual(_assignee_notes(decision), [])

	def test_prefix_overrides_default(self):
		for subject in (
			"[tracecore] lỗi",
			"[GẤP] [tracecore] lỗi",
			"[TraceCore] lỗi",
			"lỗi [TRACECORE] giữa",
		):
			with self.subTest(subject=subject):
				self.assertEqual(_decide_assignee("A", subject).assignee, "trace@x.com")
		# Reverse: another category's prefix is not used; no prefix -> default.
		self.assertEqual(_decide_assignee("B", "[tracecore] lỗi").assignee, "b.default@x.com")
		self.assertEqual(_decide_assignee("A", "[trace] lỗi").assignee, "a.default@x.com")
		self.assertEqual(_decide_assignee("A", None).assignee, "a.default@x.com")

	def test_first_declared_prefix_with_person_wins(self):
		self.assertEqual(_decide_assignee("A", "[kho] [tracecore] x").assignee, "trace@x.com")
		self.assertEqual(_decide_assignee("A", "[tracecore] [kho] x").assignee, "trace@x.com")
		self.assertEqual(_decide_assignee("A", "[kho] x").assignee, "kho@x.com")
		# Prefix matched but empty person is passed over: falls to default.
		self.assertEqual(_decide_assignee("C", "[hr] việc").assignee, "c.default@x.com")
		# D-13: the first matching prefix WITH a person wins; an empty one is skipped.
		config = {"assignees": {"A": {"default": "d@x.com", "prefixes": {"[x]": "", "[y]": "y@x.com"}}}}
		self.assertEqual(_decide_assignee("A", "[x] [y]", config=config).assignee, "y@x.com")

	def test_config_prefix_casefolded(self):
		config = {"assignees": {"A": {"default": "d@x.com", "prefixes": {"[TraceCore]": "trace@x.com"}}}}
		self.assertEqual(_decide_assignee("A", "[tracecore] x", config=config).assignee, "trace@x.com")

	def test_empty_prefix_key_ignored(self):
		config = {"assignees": {"A": {"default": "d@x.com", "prefixes": {"": "any@x.com"}}}}
		self.assertEqual(_decide_assignee("A", "bất kỳ", config=config).assignee, "d@x.com")

	def test_invalid_chosen_candidate_does_not_fall_back_to_default(self):
		def not_trace(user):
			return user != "trace@x.com"

		decision = _decide_assignee("A", "[tracecore] x", is_active_agent=not_trace)
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["trace@x.com không phải HD Agent đang hoạt động"])

	def test_de_assignee_is_department_head(self):
		for category in "DE":
			with self.subTest(category=category):
				decision = _decide_assignee(category, department="  KẾ toán ")
				self.assertEqual(decision.assignee, "head@x.com")
				self.assertEqual(_assignee_notes(decision), [])
		decision = _decide_assignee("D", department="HR")
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["cấu hình không có người cho đầu mục D"])

	def test_empty_candidate_note(self):
		decision = _decide_assignee("F")
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["cấu hình không có người cho đầu mục F"])
		decision = _decide_assignee("E", department="Kho")
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["cấu hình không có người cho đầu mục E"])
		self.assertIsNone(_decide_assignee("A", config={}).assignee)

	def test_inactive_or_missing_agent_not_chosen(self):
		decision = _decide_assignee("A", "[tracecore] lỗi", is_active_agent=lambda user: False)
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["trace@x.com không phải HD Agent đang hoạt động"])
		decision = _decide_assignee("D", department="Kế toán", is_active_agent=lambda user: False)
		self.assertIsNone(decision.assignee)
		self.assertEqual(_assignee_notes(decision), ["head@x.com không phải HD Agent đang hoạt động"])

		# Only the failing user is rejected; others stay valid.
		def only_trace(user):
			return user == "trace@x.com"

		self.assertEqual(
			_decide_assignee("A", "[tracecore] x", is_active_agent=only_trace).assignee, "trace@x.com"
		)
		self.assertIsNone(_decide_assignee("B", is_active_agent=only_trace).assignee)

	def test_agent_user_never_chosen(self):
		config = {
			"assignees": {"A": {"default": AGENT_USER, "prefixes": {"[tracecore]": AGENT_USER}}},
			"departments": {"Kế toán": {"team": "Accounting", "head": AGENT_USER}},
		}
		for category, subject in (("A", "[tracecore] x"), ("A", "x"), ("D", "x")):
			with self.subTest(category=category, subject=subject):
				decision = _decide_assignee(category, subject, department="Kế toán", config=config)
				self.assertIsNone(decision.assignee)
				self.assertFalse(decision.needs_task)
				self.assertEqual(_assignee_notes(decision), ["không gán tài khoản agent"])

	def test_agent_user_variants_never_chosen(self):
		for variant in (AGENT_USER.upper(), f"  {AGENT_USER} ", AGENT_USER.title()):
			with self.subTest(variant=repr(variant)):
				config = {"assignees": {"A": {"default": variant, "prefixes": {}}}}
				decision = _decide_assignee("A", config=config)
				self.assertIsNone(decision.assignee)
				self.assertEqual(_assignee_notes(decision), ["không gán tài khoản agent"])

	def test_needs_task_only_c_d_with_assignee(self):
		for category in "ABCDEF":
			with self.subTest(category=category):
				decision = _decide_assignee(category, department="Kế toán")
				self.assertEqual(decision.needs_task, category in ("C", "D"))
		self.assertFalse(_decide_assignee("C", config={}).needs_task)
		self.assertFalse(_decide_assignee("D", department="HR").needs_task)
		self.assertFalse(_decide_assignee("C", is_active_agent=lambda user: False).needs_task)


def _bad(mutate):
	config = json.loads(routing.DEFAULT_ROUTING_RULES)
	mutate(config)
	return json.dumps(config)


class TestRoutingConfig(FrappeTestCase):
	def test_default_valid_and_loads(self):
		routing.validate_routing_config(routing.DEFAULT_ROUTING_RULES)
		config = routing.load_routing_config(routing.DEFAULT_ROUTING_RULES)
		self.assertEqual(config, json.loads(routing.DEFAULT_ROUTING_RULES))
		self.assertEqual(config["importance_priority"], {"1": "", "2": "High", "3": "High"})
		self.assertEqual(
			config["expected_sla"],
			{
				"A": {"response_min": 15, "resolution_min": 480},
				"B": {"response_min": 15, "resolution_min": 240},
				"C": {"response_min": 60, "resolution_min": 1440},
				"D": {"response_min": 60, "resolution_min": None},
				"E": {"response_min": 60, "resolution_min": None},
				"F": {"response_min": 5, "resolution_min": 60},
			},
		)
		for category in "ABCF":
			self.assertEqual(config["assignees"][category]["default"], "")
		self.assertEqual(config["departments"], {})

	def test_bad_configs_raise_with_path(self):
		def set_level(c):
			c["importance_priority"]["2"] = "Hgh"

		def drop_three(c):
			del c["importance_priority"]["3"]

		def add_d(c):
			c["assignees"]["D"] = {"default": "", "prefixes": {}}

		def unknown_default(c):
			c["assignees"]["A"]["default"] = "khong.ton.tai@example.com"

		def unknown_prefix(c):
			c["assignees"]["A"]["prefixes"]["[x]"] = "khong.ton.tai@example.com"

		def unknown_head(c):
			c["departments"]["Kế toán"] = {"team": "", "head": "khong.ton.tai@example.com"}

		def negative(c):
			c["expected_sla"]["A"]["response_min"] = -5

		def boolean(c):
			c["expected_sla"]["B"]["resolution_min"] = True

		def bad_department(c):
			c["departments"]["Kế toán"] = "x"

		cases = (
			("not json", "{khong phai json", "không phải JSON object"),
			("list root", "[]", "không phải JSON object"),
			("root key", json.dumps({"lạ": {}}), "'lạ'"),
			("level", _bad(set_level), "importance_priority.2"),
			("missing 3", _bad(drop_three), "importance_priority"),
			("assignees.D", _bad(add_d), "assignees: đầu mục 'D'"),
			("user default", _bad(unknown_default), "assignees.A.default"),
			("user prefix", _bad(unknown_prefix), "assignees.A.prefixes.[x]"),
			("user head", _bad(unknown_head), "departments.Kế toán.head"),
			("negative", _bad(negative), "expected_sla.A.response_min"),
			("bool", _bad(boolean), "expected_sla.B.resolution_min"),
			("department shape", _bad(bad_department), "departments.Kế toán"),
		)
		for name, raw, path in cases:
			with self.subTest(case=name):
				with self.assertRaises(frappe.ValidationError) as caught:
					routing.validate_routing_config(raw)
				self.assertIn(path, str(caught.exception))

	def test_user_checked_only_when_non_empty_and_agent_not_blocked(self):
		def fill(c):
			c["assignees"]["A"]["default"] = "Administrator"
			c["assignees"]["B"]["default"] = AGENT_USER
			c["departments"]["Kế toán"] = {"team": "Nhóm chưa tạo", "head": ""}

		routing.validate_routing_config(_bad(fill))

	def test_load_bad_returns_empty(self):
		def add_d(c):
			c["assignees"]["D"] = {"default": "", "prefixes": {}}

		for raw in (None, "", "khong phai json", "[]", "3", json.dumps({"lạ": 1}), _bad(add_d)):
			with self.subTest(raw=raw):
				self.assertEqual(routing.load_routing_config(raw), {})
