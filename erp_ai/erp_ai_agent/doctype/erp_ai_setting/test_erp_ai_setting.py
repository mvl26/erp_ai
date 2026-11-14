import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
from frappe.model.document import Document
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from erp_ai import constants, install
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.agent.routing import DEFAULT_ROUTING_RULES
from erp_ai.agent.tools import read
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	SETTING_DOCTYPE,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_setting import erp_ai_setting
from erp_ai.test_utils import TempAppsRoot, keep_agent_settings, set_agent_settings

PRICES = {
	"price_input_per_mtok": 1,
	"price_cache_write_per_mtok": 1.25,
	"price_cache_read_per_mtok": 0.1,
	"price_output_per_mtok": 5,
}


SELF_MANAGED_FIELDS = (
	"status",
	"paused_until",
	"tokens_remaining",
	"limit_reset_at",
	"error_count",
	"last_error",
	"last_success_at",
	"spent_month_usd",
)
DATETIME_FIELDS = ("paused_until", "limit_reset_at", "last_success_at")


def _settings_with_keys(*labels):
	"""Save the setting with the given key labels and return the reloaded document."""
	doc = frappe.get_doc(SETTING_DOCTYPE)
	doc.set("credentials", [])
	for label in labels:
		doc.append("credentials", {"label": label, "api_key": f"sk-{label}"})
	doc.save()
	return frappe.get_doc(SETTING_DOCTYPE)


class TestERPAISetting(FrappeTestCase):
	def setUp(self):
		self.assertTrue(
			frappe.db.exists("DocType", SETTING_DOCTYPE),
			"DocType ERP AI Setting is missing",
		)
		# FrappeTestCase rolls back only after the whole class: undo each test, then start from a known valid baseline.
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			enabled=0,
			max_turns_per_run=8,
			max_runs_per_ticket_per_day=5,
			max_keys_per_call=3,
			request_timeout_s=60,
			monthly_budget_usd=10,
			trigger_keyword="@ai",
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING),
			spent_this_month_usd=0,
			**PRICES,
		)

	def test_default_mapping_and_default_disabled_l0(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		self.assertTrue(meta.issingle)
		self.assertEqual(meta.module, "ERP AI agent")
		self.assertEqual(json.loads(meta.get_field("category_mapping").default), DEFAULT_CATEGORY_MAPPING)
		self.assertEqual(int(meta.get_field("enabled").default), 0)
		self.assertEqual(meta.get_field("permission_level").default, "L0")
		self.assertEqual(meta.get_field("credentials").options, CREDENTIAL_DOCTYPE)
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE})
		doc = frappe.get_doc(SETTING_DOCTYPE)
		self.assertFalse(doc.enabled)
		self.assertEqual(doc.permission_level, "L0")
		self.assertEqual(json.loads(doc.category_mapping), DEFAULT_CATEGORY_MAPPING)

	def test_monthly_budget_is_float_precision_6_usd(self):
		field = frappe.get_meta(SETTING_DOCTYPE).get_field("monthly_budget_usd")
		self.assertEqual(field.fieldtype, "Float")
		self.assertEqual(str(field.precision), "6")
		self.assertIn("(USD)", field.label)

	def test_hd_agent_cannot_read_or_write_settings(self):
		email = "erp-ai-hd-agent@example.com"
		if not frappe.db.exists("User", email):
			user = frappe.new_doc("User")
			user.update({"email": email, "first_name": "HD Agent", "send_welcome_email": 0})
			user.append("roles", {"role": "Agent"})
			user.insert(ignore_permissions=True)
		for ptype in ("read", "write"):
			self.assertFalse(frappe.has_permission(SETTING_DOCTYPE, ptype, user=email), ptype)
		self.assertTrue(frappe.has_permission(SETTING_DOCTYPE, "read", user="Administrator"))
		roles = {p.role for p in frappe.get_meta(SETTING_DOCTYPE).permissions}
		self.assertEqual(roles, {"System Manager"})

	def test_self_managed_fields_restored_on_human_save(self):
		set_agent_settings(spent_this_month_usd=3.5)
		doc = _settings_with_keys("k1")
		row = doc.credentials[0]
		in_db = {
			"status": KEY_STATUS_PAUSED,
			"paused_until": "2030-05-01 10:00:00",
			"tokens_remaining": 77,
			"limit_reset_at": "2030-05-02 11:00:00",
			"error_count": 4,
			"last_error": "rate_limit 429 req_1",
			"last_success_at": "2030-04-30 09:00:00",
			"spent_month_usd": 2.5,
		}
		from_form = {
			"status": KEY_STATUS_ACTIVE,
			"paused_until": "2031-01-01 00:00:00",
			"tokens_remaining": 1,
			"limit_reset_at": "2031-01-02 00:00:00",
			"error_count": 0,
			"last_error": "",
			"last_success_at": "2031-01-03 00:00:00",
			"spent_month_usd": 9,
		}
		self.assertEqual(set(in_db), set(SELF_MANAGED_FIELDS))
		frappe.db.set_value(CREDENTIAL_DOCTYPE, row.name, in_db)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].update(from_form)
		doc.spent_this_month_usd = 0
		doc.save()
		stored = frappe.db.get_value(CREDENTIAL_DOCTYPE, row.name, list(SELF_MANAGED_FIELDS), as_dict=True)
		for fieldname in SELF_MANAGED_FIELDS:
			expected = in_db[fieldname]
			actual = stored[fieldname]
			if fieldname in DATETIME_FIELDS:
				expected, actual = get_datetime(expected), get_datetime(actual)
			with self.subTest(fieldname=fieldname):
				self.assertEqual(actual, expected)
		self.assertEqual(float(frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")), 3.5)

	def test_new_key_row_gets_default_self_managed_fields(self):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("credentials", [])
		doc.append(
			"credentials",
			{
				"label": "fresh",
				"api_key": "sk-x",
				"status": KEY_STATUS_BAD_KEY,
				"paused_until": "2031-01-01 00:00:00",
				"tokens_remaining": 50,
				"limit_reset_at": "2031-01-02 00:00:00",
				"error_count": 9,
				"last_error": "auth 401 req_9",
				"last_success_at": "2031-01-03 00:00:00",
				"spent_month_usd": 7,
			},
		)
		doc.save()
		row = frappe.get_doc(SETTING_DOCTYPE).credentials[0]
		self.assertEqual(row.status, KEY_STATUS_ACTIVE)
		self.assertIsNone(row.paused_until)
		self.assertFalse(row.tokens_remaining)
		self.assertIsNone(row.limit_reset_at)
		self.assertEqual(row.error_count, 0)
		self.assertFalse(row.last_error)
		self.assertIsNone(row.last_success_at)
		self.assertEqual(row.spent_month_usd, 0)

	def test_human_can_move_key_error_to_active_only(self):
		doc = _settings_with_keys("k1", "k2")
		bad, paused = doc.credentials[0], doc.credentials[1]
		frappe.db.set_value(
			CREDENTIAL_DOCTYPE,
			bad.name,
			{"status": KEY_STATUS_BAD_KEY, "error_count": 5, "last_error": "auth 401 req_2"},
		)
		frappe.db.set_value(CREDENTIAL_DOCTYPE, paused.name, "status", KEY_STATUS_PAUSED)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].status = KEY_STATUS_ACTIVE
		doc.credentials[1].status = KEY_STATUS_ACTIVE
		doc.save()
		moved = frappe.db.get_value(
			CREDENTIAL_DOCTYPE, bad.name, ["status", "error_count", "last_error"], as_dict=True
		)
		self.assertEqual(moved.status, KEY_STATUS_ACTIVE)
		self.assertEqual(moved.error_count, 0)
		self.assertFalse(moved.last_error)
		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, paused.name, "status"), KEY_STATUS_PAUSED)
		# A human cannot move an active key back to the error state.
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.credentials[0].status = KEY_STATUS_BAD_KEY
		doc.save()
		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, bad.name, "status"), KEY_STATUS_ACTIVE)

	def test_validation_rejects_bad_mapping_limits_and_missing_prices(self):
		def saved_with(**fields):
			doc = frappe.get_doc(SETTING_DOCTYPE)
			doc.update(fields)
			doc.save()

		turns = "Số lượt tối đa mỗi lần chạy phải từ 1 đến 20"
		runs = "Số lần chạy tối đa mỗi phiếu mỗi ngày phải từ 1 đến 50"
		keys = "Số khóa tối đa mỗi lời gọi phải từ 1 đến 10"
		timeout = "Timeout mỗi lời gọi API phải từ 5 đến 300"
		cases = [
			({"category_mapping": "not json"}, "không phải JSON hợp lệ"),
			({"category_mapping": json.dumps({"Z": {}})}, "Đầu mục 'Z' không hợp lệ"),
			({"max_turns_per_run": 0}, turns),
			({"max_turns_per_run": 21}, turns),
			({"max_runs_per_ticket_per_day": 0}, runs),
			({"max_runs_per_ticket_per_day": 51}, runs),
			({"max_keys_per_call": 0}, keys),
			({"max_keys_per_call": 11}, keys),
			({"request_timeout_s": 4}, timeout),
			({"request_timeout_s": 301}, timeout),
			({"monthly_budget_usd": -1}, "Ngân sách tháng phải không nhỏ hơn 0"),
			({"enabled": 1, "trigger_keyword": " "}, "từ khóa kích hoạt rỗng"),
		]
		for fieldname in PRICES:
			cases.append(({fieldname: -1}, "Đơn giá không được âm"))
			cases.append(({"enabled": 1, fieldname: 0}, "chưa nhập đủ 4 đơn giá"))
		for fields, message in cases:
			with self.subTest(fields=fields), self.assertRaisesRegex(frappe.ValidationError, message):
				saved_with(**fields)

	def test_status_fields_defaults(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		self.assertEqual(meta.get_field("thinking_text").fieldtype, "Small Text")
		self.assertEqual(meta.get_field("thinking_text").default, "Đang suy nghĩ…")
		for fieldname, default in (("answer_delay_min_s", "3"), ("answer_delay_max_s", "5")):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(meta.get_field(fieldname).fieldtype, "Int")
				self.assertEqual(meta.get_field(fieldname).default, default)
		order = [field.fieldname for field in meta.fields]
		after = order.index("trigger_keyword")
		self.assertEqual(
			order[after + 1 : after + 4], ["thinking_text", "answer_delay_min_s", "answer_delay_max_s"]
		)

	def test_status_fields_rejections(self):
		min_msg = "Trễ trả lời tối thiểu phải từ 0 đến 30"
		max_msg = "Trễ trả lời tối đa phải từ 0 đến 30"
		order_msg = "Trễ trả lời tối thiểu không được lớn hơn trễ trả lời tối đa"
		text_msg = "Chữ chỉ báo khi đang suy nghĩ không được dài quá 5000 ký tự"
		cases = [
			({"answer_delay_min_s": -1, "answer_delay_max_s": 5}, min_msg),
			({"answer_delay_min_s": 31, "answer_delay_max_s": 31}, min_msg),
			({"answer_delay_min_s": 3, "answer_delay_max_s": -1}, max_msg),
			({"answer_delay_min_s": 3, "answer_delay_max_s": 31}, max_msg),
			({"answer_delay_min_s": 6, "answer_delay_max_s": 5}, order_msg),
			({"thinking_text": "x" * 5001}, text_msg),
		]
		for fields, message in cases:
			with self.subTest(fields=fields):
				doc = frappe.get_doc(SETTING_DOCTYPE)
				doc.update(fields)
				with self.assertRaises(frappe.ValidationError) as caught:
					doc.save()
				self.assertEqual(frappe.utils.strip_html(str(caught.exception)), message)

	def test_status_fields_valid_edges_save(self):
		cases = [
			{"answer_delay_min_s": 0, "answer_delay_max_s": 0},
			{"answer_delay_min_s": 30, "answer_delay_max_s": 30},
			{"answer_delay_min_s": 3, "answer_delay_max_s": 3},
			{"answer_delay_min_s": 0, "answer_delay_max_s": 30},
			{"thinking_text": ""},
			{"thinking_text": "x" * 5000},
		]
		for fields in cases:
			with self.subTest(fields=fields):
				doc = frappe.get_doc(SETTING_DOCTYPE)
				doc.update(fields)
				doc.save()
				saved = frappe.get_doc(SETTING_DOCTYPE)
				for fieldname, value in fields.items():
					self.assertEqual(
						saved.get(fieldname) or ("" if fieldname == "thinking_text" else 0), value
					)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.thinking_text = None
		doc.save()
		stored = frappe.db.sql(
			"select value from `tabSingles` where doctype=%s and field='thinking_text'", SETTING_DOCTYPE
		)
		self.assertEqual(stored, (("",),))

	def test_validation_rejects_empty_and_duplicate_key_labels(self):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("credentials", [])
		doc.append("credentials", {"label": "  ", "api_key": "a"})
		with self.assertRaisesRegex(frappe.ValidationError, "nhãn khóa không được để trống"):
			doc.save()
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.append("credentials", {"label": "Dup", "api_key": "a"})
		doc.append("credentials", {"label": "dup", "api_key": "b"})
		with self.assertRaisesRegex(frappe.ValidationError, "bị trùng"):
			doc.save()

	def test_valid_settings_can_be_enabled(self):
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"), 0)
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.enabled = 1
		doc.save()
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"), 1)

	def test_set_agent_settings_writes_values(self):
		set_agent_settings(enabled=1, permission_level="L1")
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L1")


DESCRIPTION_MAX_CHARS = 400


class TestRoutingRules(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			enabled=0,
			max_turns_per_run=8,
			max_runs_per_ticket_per_day=5,
			max_keys_per_call=3,
			request_timeout_s=60,
			monthly_budget_usd=10,
			trigger_keyword="@ai",
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING),
			spent_this_month_usd=0,
			**PRICES,
		)

	def _save_rules(self, raw):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.routing_rules = raw
		doc.save()
		return frappe.get_doc(SETTING_DOCTYPE)

	def test_fields_in_section_routing_with_type_options_default(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		order = [f.fieldname for f in meta.fields]
		self.assertGreater(order.index("auto_assign_enabled"), order.index("section_routing"))
		self.assertGreater(order.index("routing_rules"), order.index("section_routing"))
		switch = meta.get_field("auto_assign_enabled")
		self.assertEqual(switch.fieldtype, "Check")
		self.assertEqual(str(switch.default), "0")
		rules = meta.get_field("routing_rules")
		self.assertEqual(rules.fieldtype, "Code")
		self.assertEqual(rules.options, "JSON")
		self.assertFalse(rules.default)

	def test_new_field_descriptions_at_most_400_chars(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		for fieldname in ("auto_assign_enabled", "routing_rules"):
			with self.subTest(fieldname=fieldname):
				description = (meta.get_field(fieldname).description or "").strip()
				self.assertTrue(description, "description is empty")
				self.assertLessEqual(len(description), DESCRIPTION_MAX_CHARS)

	def test_default_rules_valid(self):
		doc = self._save_rules(DEFAULT_ROUTING_RULES)
		self.assertEqual(json.loads(doc.routing_rules), json.loads(DEFAULT_ROUTING_RULES))

	def test_blank_rules_message_has_default_json_not_constant_name(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			self._save_rules("")
		message = str(ctx.exception)
		self.assertIn(DEFAULT_ROUTING_RULES, message)
		self.assertNotIn("DEFAULT_ROUTING_RULES", message)

	def test_blank_rules_blocked_with_restore_hint(self):
		for blank in (None, "", "  \n"):
			with self.subTest(blank=blank), self.assertRaisesRegex(frappe.ValidationError, "JSON mặc định"):
				self._save_rules(blank)

	def test_bad_rules_blocked_with_location(self):
		rules = json.loads(DEFAULT_ROUTING_RULES)
		rules["importance_priority"]["2"] = "Critical"
		cases = (
			("not json", "không phải JSON object hợp lệ"),
			(json.dumps(["x"]), "không phải JSON object hợp lệ"),
			(json.dumps({"assign": {}}), "khóa lạ 'assign'"),
			(json.dumps(rules), "importance_priority.2"),
			(
				json.dumps({"assignees": {"A": {"default": "no-such-user@example.com", "prefixes": {}}}}),
				"assignees.A.default",
			),
			(json.dumps({"expected_sla": {"A": {"response_min": 0}}}), "expected_sla.A.response_min"),
		)
		for raw, message in cases:
			with self.subTest(raw=raw), self.assertRaisesRegex(frappe.ValidationError, message):
				self._save_rules(raw)


MISSING_DIR_MSG = "Không có thư mục apps/{0}"
OWN_APP_MSG = "Không được thêm erp_ai vào danh sách app được sửa"
BAD_NAME_MSG = "Tên app '{0}' không hợp lệ"


class TestChangeApps(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			enabled=0,
			max_turns_per_run=8,
			max_runs_per_ticket_per_day=5,
			max_keys_per_call=3,
			request_timeout_s=60,
			monthly_budget_usd=10,
			trigger_keyword="@ai",
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING),
			spent_this_month_usd=0,
			**PRICES,
		)

	def _save_apps(self, raw):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.code_change_apps = raw
		doc.save()
		return frappe.db.get_single_value(SETTING_DOCTYPE, "code_change_apps", cache=False)

	def _refusal(self, raw):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._save_apps(raw)
		return frappe.utils.strip_html(str(caught.exception))

	def test_validate_checks_dirs_under_source_root(self):
		TempAppsRoot(self, apps=("myapp",))
		self.assertEqual(self._save_apps("myapp"), "myapp")
		# `erpnext` exists under the real apps/ but not under the patched root: only the given root counts.
		for name in ("otherapp", "erpnext"):
			with self.subTest(name=name):
				self.assertEqual(self._refusal(name), MISSING_DIR_MSG.format(name))

	def test_change_apps_validation(self):
		sandbox = TempAppsRoot(self, apps=("frappe", "hrms", "erp_ai"))
		# `../x` resolves to an existing directory, so only the name rule can refuse it.
		sandbox.write("x/ok.py", "x = 1\n", root=sandbox.base)
		refusals = [
			("erp_ai", OWN_APP_MSG),
			("../x", BAD_NAME_MSG.format("../x")),
			("nosuch", MISSING_DIR_MSG.format("nosuch")),
			# Every name/erp_ai line is checked before any directory.
			("nosuch\nerp_ai", OWN_APP_MSG),
		]
		for raw, message in refusals:
			with self.subTest(raw=raw):
				self.assertEqual(self._refusal(raw), message)
		for raw in (None, "", "  \n"):
			with self.subTest(raw=raw):
				self.assertEqual(self._save_apps(raw) or "", raw or "")
		for raw in ("frappe", "hrms", "frappe\nhrms"):
			with self.subTest(raw=raw):
				self.assertEqual(self._save_apps(raw), raw)


CHECK_KEYS_HD_AGENT = "erpai-test-check-keys-agent@example.com"
FAKE_SECRET = "sk-ant-ERPAI-TEST-SECRET-0001"


class TestCheckKeys(FrappeTestCase):
	def setUp(self):
		# Undo each test (user, keys); log_error is patched so no Error Log row is left on the site.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, frappe.session.user)
		log_error = patch("frappe.log_error")
		log_error.start()
		self.addCleanup(log_error.stop)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			enabled=0,
			max_turns_per_run=8,
			max_runs_per_ticket_per_day=5,
			max_keys_per_call=3,
			request_timeout_s=60,
			monthly_budget_usd=10,
			trigger_keyword="@ai",
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING),
			spent_this_month_usd=0,
			**PRICES,
		)
		self.setting = _settings_with_keys("ERPAI-TEST-A", "ERPAI-TEST-B")
		self.rows = {row.label: row.name for row in self.setting.credentials}

	def _become_hd_agent(self):
		user = frappe.new_doc("User")
		user.update({"email": CHECK_KEYS_HD_AGENT, "first_name": "HD Agent", "send_welcome_email": 0})
		user.append("roles", {"role": "Agent"})
		user.insert(ignore_permissions=True)
		frappe.set_user(CHECK_KEYS_HD_AGENT)
		# only_for returns early while flags.in_test is set; switch it off to exercise the real guard.
		self.addCleanup(setattr, frappe.local.flags, "in_test", frappe.local.flags.in_test)
		frappe.local.flags.in_test = False

	def _fake_probe(self, row_name):
		label = frappe.db.get_value(CREDENTIAL_DOCTYPE, row_name, "label")
		if label == "ERPAI-TEST-B":
			return {"label": label, "ok": False, "error_kind": "auth", "status": 401}
		return {"label": label, "ok": True, "error_kind": None, "status": None}

	def test_check_keys_system_manager_only_and_per_key_result(self):
		with patch("erp_ai.gateway.probe_credential", side_effect=self._fake_probe) as probe:
			result = erp_ai_setting.check_keys()
			self.assertEqual(
				result,
				[
					{"label": "ERPAI-TEST-A", "ok": True, "error_kind": None, "status": None},
					{"label": "ERPAI-TEST-B", "ok": False, "error_kind": "auth", "status": 401},
				],
			)
			self.assertEqual(
				[call.args[0] for call in probe.call_args_list],
				[self.rows["ERPAI-TEST-A"], self.rows["ERPAI-TEST-B"]],
			)
			probe.reset_mock()
			single_result = erp_ai_setting.check_keys("ERPAI-TEST-B")
			self.assertEqual([item["label"] for item in single_result], ["ERPAI-TEST-B"])
			probe.assert_called_once_with(self.rows["ERPAI-TEST-B"])
			probe.reset_mock()
			with self.assertRaises(frappe.ValidationError):
				erp_ai_setting.check_keys("ERPAI-TEST-NOPE")
			probe.assert_not_called()

	def test_check_keys_whitelisted_for_post(self):
		self.assertIn(erp_ai_setting.check_keys, frappe.whitelisted)
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[erp_ai_setting.check_keys], ["POST"]
		)

	def test_check_keys_escapes_the_label_in_the_unknown_label_error(self):
		with patch.object(erp_ai_setting.gateway, "probe_credential") as probe:
			with self.assertRaises(frappe.ValidationError) as caught:
				erp_ai_setting.check_keys("<img src=x onerror=alert(1)>")
		message = str(caught.exception)
		self.assertNotIn("<img", message)
		self.assertIn("&lt;img", message)
		probe.assert_not_called()

	def test_check_keys_refuses_hd_agent_before_reading_or_probing(self):
		self._become_hd_agent()
		with (
			patch("erp_ai.gateway.probe_credential") as probe,
			patch.object(erp_ai_setting.frappe, "get_all") as get_all,
		):
			with self.assertRaises(frappe.PermissionError):
				erp_ai_setting.check_keys()
			with self.assertRaises(frappe.PermissionError):
				erp_ai_setting.check_keys("ERPAI-TEST-NOPE")
		get_all.assert_not_called()
		probe.assert_not_called()

	def test_check_keys_never_saves_the_setting(self):
		with (
			patch("erp_ai.gateway.probe_credential", side_effect=self._fake_probe),
			patch("frappe.model.document.Document.save", MagicMock()) as save,
		):
			erp_ai_setting.check_keys()
			erp_ai_setting.check_keys("ERPAI-TEST-A")
		save.assert_not_called()

	def test_check_keys_result_has_only_the_four_fields_no_secret_or_exception_text(self):
		def leaky_probe(row_name):
			return {
				"label": frappe.db.get_value(CREDENTIAL_DOCTYPE, row_name, "label"),
				"ok": False,
				"error_kind": "auth",
				"status": 401,
				"error": f"AuthenticationError: invalid x-api-key {FAKE_SECRET}",
				"api_key": FAKE_SECRET,
			}

		with patch("erp_ai.gateway.probe_credential", side_effect=leaky_probe):
			result = erp_ai_setting.check_keys()
		self.assertEqual(len(result), 2)
		for item in result:
			self.assertEqual(set(item), {"label", "ok", "error_kind", "status"})
		self.assertNotIn(FAKE_SECRET, json.dumps(result))
		self.assertNotIn("AuthenticationError", json.dumps(result))


# FEAT-007 design 2.1: default of every new ERP AI Setting field (NFR-4); one row per field as tasks add them.
FEAT007_NEW_FIELD_DEFAULTS = {
	"site_environment": "production",
	"record_tools_enabled": 0,
	"act_now_enabled": 0,
	"one_click_approval_enabled": 0,
	"level_cap_a": "L2",
	"level_cap_b": "L3",
	"level_cap_c": "L1",
	"level_cap_d": "L2",
	"level_cap_e": "L1",
	"level_cap_f": "L3",
	"confidence_threshold": 70,
	"auto_approve_streak": 20,
	# A Table keeps no Singles row: no stored value means the catalog starts empty.
	"catalog_rules": None,
}
# FEAT-007 AC-31: the highest level per category A-F, in form order.
LEVEL_CAP_DEFAULTS = (
	("level_cap_a", "L2"),
	("level_cap_b", "L3"),
	("level_cap_c", "L1"),
	("level_cap_d", "L2"),
	("level_cap_e", "L1"),
	("level_cap_f", "L3"),
)


class TestFeat007Defaults(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def _value_after_install(self, fieldname):
		"""Drop the stored value of `fieldname`, run the install default step and return the value it wrote."""
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": fieldname})
		install._ensure_default_settings()
		return frappe.db.get_single_value(SETTING_DOCTYPE, fieldname, cache=False)

	def test_site_environment_default_production_and_options(self):
		field = frappe.get_meta(SETTING_DOCTYPE).get_field("site_environment")
		self.assertIsNotNone(field, "ERP AI Setting has no site_environment field")
		self.assertEqual(
			(field.fieldtype, field.options, field.default), ("Select", "production\ntest", "production")
		)
		self.assertEqual(self._value_after_install("site_environment"), "production")

		doc = frappe.get_single(SETTING_DOCTYPE)
		doc.site_environment = "test"
		doc.flags.ignore_validate = True
		doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "site_environment", cache=False), "test")

		doc = frappe.get_single(SETTING_DOCTYPE)
		doc.site_environment = "staging"
		doc.flags.ignore_validate = True
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_every_new_field_default(self):
		for fieldname, expected in FEAT007_NEW_FIELD_DEFAULTS.items():
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self._value_after_install(fieldname), expected)

	def test_level_caps_default(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		order = [field.fieldname for field in meta.fields]
		self.assertIn("section_autonomy", order, "ERP AI Setting has no section_autonomy")
		start = order.index("section_autonomy") + 1
		self.assertEqual(
			order[start : start + 8],
			[fieldname for fieldname, _default in LEVEL_CAP_DEFAULTS]
			+ ["confidence_threshold", "auto_approve_streak"],
		)
		for fieldname, default in LEVEL_CAP_DEFAULTS:
			with self.subTest(fieldname=fieldname):
				field = meta.get_field(fieldname)
				self.assertEqual(
					(field.fieldtype, field.options, field.default), ("Select", "L0\nL1\nL2\nL3", default)
				)
				self.assertEqual(self._value_after_install(fieldname), default)


# FEAT-007 AC-22, AC-36: fieldname -> (exact error text, low, high).
FEAT007_INT_LIMITS = {
	"confidence_threshold": ("Ngưỡng độ tin cậy phải từ 0 đến 100", 0, 100),
	"auto_approve_streak": ("Số lần duyệt liên tiếp để Tự làm phải từ 1 đến 100", 1, 100),
}


class TestFeat007Limits(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)

	def _save(self, fieldname, value):
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set(fieldname, value)
		doc.save()

	def test_int_limits_edges(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		for fieldname, (message, low, high) in FEAT007_INT_LIMITS.items():
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field, f"ERP AI Setting has no {fieldname} field")
			self.assertEqual(field.fieldtype, "Int", fieldname)
			for value in (low - 1, high + 1):
				with self.subTest(fieldname=fieldname, value=value):
					with self.assertRaises(frappe.ValidationError) as caught:
						self._save(fieldname, value)
					self.assertEqual(frappe.utils.strip_html(str(caught.exception)), message)
			for value in (low, high):
				with self.subTest(fieldname=fieldname, value=value):
					self._save(fieldname, value)
					self.assertEqual(
						frappe.db.get_single_value(SETTING_DOCTYPE, fieldname, cache=False), value
					)


# FEAT-007 design 2.1: the five Check fields of section_permissions (AC-4 notice, D-7).
PERMISSION_SWITCHES = (
	"unrestricted_enabled",
	"record_tools_enabled",
	"act_now_enabled",
	"code_change_enabled",
	"one_click_approval_enabled",
)
NOTICE_TITLE = "Đã bật quyền mở rộng"


class TestPermissionSwitchNotice(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self._save({fieldname: 0 for fieldname in PERMISSION_SWITCHES} | {"site_environment": "production"})

	def _save(self, values):
		"""Save the setting with `values`; return the mock that stood in for frappe.msgprint."""
		doc = frappe.get_single(SETTING_DOCTYPE)
		doc.update(values)
		doc.flags.ignore_validate = True
		with patch.object(frappe, "msgprint") as msgprint:
			doc.save(ignore_permissions=True)
		return msgprint

	def _notice_calls(self, msgprint):
		return [c for c in msgprint.call_args_list if c.kwargs.get("title") == NOTICE_TITLE]

	def test_each_switch_on_shows_name_consequence_environment(self):
		meta = frappe.get_meta(SETTING_DOCTYPE)
		for environment, fieldname in zip(("test", "production") * 3, PERMISSION_SWITCHES, strict=False):
			with self.subTest(fieldname=fieldname):
				self._save({name: 0 for name in PERMISSION_SWITCHES})
				msgprint = self._save({fieldname: 1, "site_environment": environment})
				calls = self._notice_calls(msgprint)
				self.assertEqual(len(calls), 1, f"no single notice when {fieldname} goes 0 -> 1")
				call = calls[0]
				self.assertEqual(call.kwargs.get("indicator"), "orange")
				message = call.args[0] if call.args else call.kwargs.get("msg")
				field = meta.get_field(fieldname)
				self.assertIn(
					f"<b>{frappe.utils.escape_html(field.label)}</b>: {frappe.utils.escape_html(field.description)}",
					message,
				)
				lines = message.split("<br>")
				self.assertEqual(len(lines), 2)
				self.assertEqual(lines[-1], f"Môi trường site: {environment}")

	def test_several_switches_on_one_notice_in_form_order_without_outside_check(self):
		# Review round 1: two switches in one save -> one notice, one line each in form order,
		# environment last; auto_assign_enabled (section_routing) is a Check outside the section.
		self._save({"auto_assign_enabled": 0})
		meta = frappe.get_meta(SETTING_DOCTYPE)
		msgprint = self._save(
			{
				"one_click_approval_enabled": 1,
				"act_now_enabled": 1,
				"auto_assign_enabled": 1,
				"site_environment": "test",
			}
		)
		calls = self._notice_calls(msgprint)
		self.assertEqual(len(calls), 1, "several switches on in one save must give exactly one notice")
		message = calls[0].args[0] if calls[0].args else calls[0].kwargs.get("msg")
		lines = message.split("<br>")
		expected_switch_lines = [
			f"<b>{frappe.utils.escape_html(field.label)}</b>: {frappe.utils.escape_html(field.description)}"
			for field in (meta.get_field("act_now_enabled"), meta.get_field("one_click_approval_enabled"))
		]
		self.assertEqual(lines, [*expected_switch_lines, "Môi trường site: test"])
		self.assertNotIn(meta.get_field("auto_assign_enabled").label, message)

	def test_save_without_switch_change_no_notice(self):
		self._save({"record_tools_enabled": 1})
		msgprint = self._save({"site_environment": "test"})
		self.assertEqual(self._notice_calls(msgprint), [])
		msgprint = self._save({})
		self.assertEqual(self._notice_calls(msgprint), [])

	def test_switch_off_no_notice(self):
		self._save({"act_now_enabled": 1, "one_click_approval_enabled": 1})
		msgprint = self._save({"act_now_enabled": 0, "one_click_approval_enabled": 0})
		self.assertEqual(self._notice_calls(msgprint), [])

	def test_unrestricted_notice_has_call_method_caveat(self):
		msgprint = self._save({"unrestricted_enabled": 1})
		calls = self._notice_calls(msgprint)
		self.assertEqual(len(calls), 1)
		message = calls[0].args[0]
		self.assertIn("gọi hàm whitelist", message)
		self.assertIn("Gọi hàm là tự do", message)
		self.assertIn("chỉ là cố gắng", message)


CATALOG_RULE_DOCTYPE = "ERP AI Catalog Rule"
CATALOG_RULE_JSON = (
	Path(erp_ai_setting.__file__).resolve().parent.parent / "erp_ai_catalog_rule" / "erp_ai_catalog_rule.json"
)
# FEAT-007 design.md:214-221 and design-w0-fixes.md F-1: the stored Select values, written out once.
CATALOG_ACTION_CONSTANTS = {
	"ACTION_CREATE_USER": "Tạo tài khoản theo mẫu",
	"ACTION_ADD_TEAM_MEMBER": "Thêm người vào nhóm Helpdesk",
	"ACTION_ADD_HOLIDAY": "Thêm ngày nghỉ",
	"ACTION_SET_ITEM_GROUP": "Đổi nhóm hàng",
	"ACTION_CREATE_CUSTOM_FIELD": "Tạo Custom Field",
	"ACTION_UPDATE_FIELDS": "Đổi trường",
}
CATALOG_MODE_CONSTANTS = {
	"MODE_DENY": "Cấm",
	"MODE_NEEDS_APPROVAL": "Cần duyệt",
	"MODE_AUTO": "Tự làm",
}
# F-1: the FEAT-007 block closes constants.py, names in this order.
FEAT007_CONSTANT_BLOCK = (
	*CATALOG_ACTION_CONSTANTS,
	"CATALOG_ACTIONS",
	*CATALOG_MODE_CONSTANTS,
	"CATALOG_MODES",
	"KPI_IDS",
	"TICKET_CONTENT_DOCTYPES",
)


class TestCatalogRules(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.assertTrue(
			frappe.db.exists("DocType", CATALOG_RULE_DOCTYPE), "DocType ERP AI Catalog Rule is missing"
		)

	def test_select_options_match_constants(self):
		# AC-29: the JSON options come from the constants, one source.
		fields = {
			f["fieldname"]: f for f in json.loads(CATALOG_RULE_JSON.read_text(encoding="utf-8"))["fields"]
		}
		self.assertEqual(fields["action"]["options"], "\n".join(constants.CATALOG_ACTIONS))
		self.assertEqual(fields["mode"]["options"], "\n".join(constants.CATALOG_MODES))
		self.assertEqual(fields["mode"]["default"], constants.MODE_NEEDS_APPROVAL)
		self.assertEqual(
			{name: getattr(constants, name) for name in CATALOG_ACTION_CONSTANTS}, CATALOG_ACTION_CONSTANTS
		)
		self.assertEqual(constants.CATALOG_ACTIONS, tuple(CATALOG_ACTION_CONSTANTS.values()))
		self.assertEqual(
			{name: getattr(constants, name) for name in CATALOG_MODE_CONSTANTS}, CATALOG_MODE_CONSTANTS
		)
		self.assertEqual(constants.CATALOG_MODES, ("Cấm", "Cần duyệt", "Tự làm"))
		self.assertEqual(frappe.new_doc(CATALOG_RULE_DOCTYPE).mode, "Cần duyệt")

	def test_kpi_ids_in_order(self):
		self.assertEqual(
			constants.KPI_IDS,
			(
				"first_response_minutes",
				"complete_fields_pct",
				"closed_without_human_pct",
				"b_resolution_hours",
				"c_task_in_3_days_pct",
				"stale_over_5_days",
			),
		)

	def test_ticket_content_doctypes_is_adr_034_list(self):
		# design-w0-fixes-3.md ruling 2: exactly the four DocTypes of ADR-034 decision 1, in this order.
		self.assertEqual(constants.TICKET_CONTENT_DOCTYPES, ("HD Ticket", "Comment", "Communication", "File"))

	def test_constants_stay_leaf_with_block_at_end(self):
		# A-D6: constants.py imports nothing; F-1: the FEAT-007 names are the last assignments, in order.
		source = Path(constants.__file__).read_text(encoding="utf-8")
		self.assertEqual([line for line in source.splitlines() if line.startswith(("import", "from"))], [])
		tree = ast.parse(source)
		self.assertFalse([node for node in ast.walk(tree) if isinstance(node, ast.Import | ast.ImportFrom)])
		names = [node.targets[0].id for node in tree.body if isinstance(node, ast.Assign)]
		self.assertEqual(tuple(names[-len(FEAT007_CONSTANT_BLOCK) :]), FEAT007_CONSTANT_BLOCK)

	def test_controller_is_empty_document(self):
		doc = frappe.new_doc(CATALOG_RULE_DOCTYPE)
		self.assertEqual(type(doc).__name__, "ERPAICatalogRule")
		self.assertEqual(type(doc).__bases__, (Document,))
		own_members = [name for name in vars(type(doc)) if not name.startswith("__")]
		self.assertEqual(own_members, [])

	def _save_rule(self, action, target_doctype, ignore_links=False):
		"""Save the setting with exactly one catalog row; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("catalog_rules", [])
		doc.append(
			"catalog_rules",
			{
				"action": action,
				"target_doctype": target_doctype,
				"fields": "title",
				"categories": "A",
				"mode": "Cần duyệt",
			},
		)
		doc.flags.ignore_links = ignore_links
		try:
			doc.save()
		except frappe.ValidationError as error:
			return frappe.utils.strip_html(str(error))
		return None

	def test_four_hard_bans_blocked(self):
		# AC-29: a row on app data, a permission DocType, a submittable document or an unknown action is refused.
		cases = (
			(
				"Đổi trường",
				"ERP AI Log",
				"Danh mục dòng 1: DocType ERP AI Log bị cấm cứng: "
				"DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)",
			),
			(
				"Đổi trường",
				"Custom Role",
				"Danh mục dòng 1: DocType Custom Role bị cấm cứng: DocType phân quyền",
			),
			(
				"Đổi trường",
				"Sales Invoice",
				"Danh mục dòng 1: DocType Sales Invoice bị cấm cứng: chứng từ submit",
			),
			("Xóa bản ghi", "Note", "Danh mục dòng 1: hành động không hợp lệ"),
		)
		stored_before = [row.as_dict() for row in frappe.get_doc(SETTING_DOCTYPE).catalog_rules]
		for action, target_doctype, message in cases:
			with self.subTest(target_doctype=target_doctype):
				self.assertEqual(self._save_rule(action, target_doctype), message)
		self.assertEqual(
			[row.as_dict() for row in frappe.get_doc(SETTING_DOCTYPE).catalog_rules], stored_before
		)

	def test_unknown_doctype_blocked(self):
		# E-4: a DocType name that does not exist (data sent through the API without link checks).
		self.assertEqual(
			self._save_rule("Đổi trường", "Không Có DocType Này", ignore_links=True),
			"Danh mục dòng 1: không có DocType Không Có DocType Này",
		)

	def test_hard_ban_follows_denied_doctypes_source(self):
		# AC-29, ADR-031: the save-time check reads the live ban sets, no copy of its own.
		self.assertIsNone(self._save_rule("Đổi trường", "Note"))
		original = read.denied_doctypes
		with patch.object(read, "denied_doctypes", lambda: original() | {"Note"}):
			self.assertEqual(
				self._save_rule("Đổi trường", "Note"),
				"Danh mục dòng 1: DocType Note bị cấm cứng: "
				"DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)",
			)
		# (b) Custom Role is only in the site_api permission set.
		self.assertEqual(
			self._save_rule("Đổi trường", "Custom Role"),
			"Danh mục dòng 1: DocType Custom Role bị cấm cứng: DocType phân quyền",
		)
