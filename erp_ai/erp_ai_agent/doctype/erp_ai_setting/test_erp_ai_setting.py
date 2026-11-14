import ast
import datetime
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
from erp_ai.agent.tools import read, site_api
from erp_ai.constants import (
	AGENT_USER,
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


USER_TEMPLATE_DOCTYPE = "ERP AI User Template"
# FEAT-007 design 2.1: default of every new ERP AI Setting field (NFR-4); one row per field as tasks add them.
# Table fields have no Singles value: see test_catalog_starts_empty_after_install and its siblings.
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
	"excluded_title_prefixes": "[HR]\n[Kế toán]",
	"field_ticket_nature": "",
	"field_erp_module": "",
	"field_origin": "",
	"origin_board_value": "",
	"field_due_date": "",
	"field_project": "",
	"field_item_code": "",
	"field_serial_no": "",
	"reply_enabled": 0,
	"resolve_on_tasks_done_enabled": 0,
	"close_silent_f_enabled": 0,
	"close_silent_f_days": 3,
	"kb_draft_enabled": 0,
	"knowledge_search_limit": 5,
	"manuals_dir": "",
	"allowed_reports": "",
	"report_row_limit": 20,
	"coo_report_recipients": "",
	"daily_report_weekends": 1,
	"monthly_reviewers": "",
	"review_sample_size": 10,
	"d_ticket_watcher": "",
	"due_reminder_hours": 24,
	"ba_note_due_hours": 24,
	"task_due_days": 3,
	"max_tasks_per_run": 10,
	"kpi_targets": (
		"{\n"
		'  "first_response_minutes": {"gd2": 15, "gd4": 5},\n'
		'  "complete_fields_pct": {"gd2": 100, "gd4": 100},\n'
		'  "closed_without_human_pct": {"gd2": 10, "gd4": 30},\n'
		'  "b_resolution_hours": {"gd2": 4, "gd4": 1},\n'
		'  "c_task_in_3_days_pct": {"gd2": 80, "gd4": 100},\n'
		'  "stale_over_5_days": {"gd2": 10, "gd4": 4}\n'
		"}"
	),
	# No Singles row: get_single_value casts the absent Date to date(1, 1, 1) (see test_watermarks_start_unset).
	"daily_report_sent_on": datetime.date(1, 1, 1),
	"budget_alert_sent_month": "",
}
# FEAT-007 AC-26, D-2: the expected first-response minutes of categories A-F (routing_rules.expected_sla).
RESPONSE_TARGET_MINUTES = {"A": 15, "B": 15, "C": 60, "D": 60, "E": 60, "F": 5}
# FEAT-007 design.md:108: section_operations and its twelve fields, in form order, with their field types.
OPERATIONS_SECTION = {
	"coo_report_recipients": "Small Text",
	"daily_report_weekends": "Check",
	"monthly_reviewers": "Small Text",
	"review_sample_size": "Int",
	"d_ticket_watcher": "Link",
	"due_reminder_hours": "Int",
	"ba_note_due_hours": "Int",
	"task_due_days": "Int",
	"max_tasks_per_run": "Int",
	"kpi_targets": "Code",
	"daily_report_sent_on": "Date",
	"budget_alert_sent_month": "Data",
}
# FEAT-007 design.md:189-197 (section 2.1.1): the default KPI targets per stage.
DEFAULT_KPI_TARGETS = {
	"first_response_minutes": {"gd2": 15, "gd4": 5},
	"complete_fields_pct": {"gd2": 100, "gd4": 100},
	"closed_without_human_pct": {"gd2": 10, "gd4": 30},
	"b_resolution_hours": {"gd2": 4, "gd4": 1},
	"c_task_in_3_days_pct": {"gd2": 80, "gd4": 100},
	"stale_over_5_days": {"gd2": 10, "gd4": 4},
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

	def test_catalog_starts_empty_after_install(self):
		# AC-29: a Table keeps its rows in the child table, not in Singles; install seeds no catalog row.
		row_filters = {"parent": SETTING_DOCTYPE, "parentfield": "catalog_rules"}
		frappe.db.delete(CATALOG_RULE_DOCTYPE, row_filters)
		install._ensure_default_settings()
		self.assertEqual(frappe.get_all(CATALOG_RULE_DOCTYPE, filters=row_filters), [])

	def test_user_templates_start_empty_after_install(self):
		# AC-30 (1): like catalog_rules, the templates live in the child table; install seeds no template row.
		row_filters = {"parent": SETTING_DOCTYPE, "parentfield": "user_templates"}
		frappe.db.delete(USER_TEMPLATE_DOCTYPE, row_filters)
		install._ensure_default_settings()
		self.assertEqual(frappe.get_all(USER_TEMPLATE_DOCTYPE, filters=row_filters), [])

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

	def test_response_targets_reuse_routing_rules(self):
		# AC-26, D-2: the response targets are routing_rules.expected_sla.<X>.response_min, no field of their own;
		# a fresh install stores 15, 15, 60, 60, 60, 5 for A-F.
		stored = json.loads(self._value_after_install("routing_rules"))
		self.assertEqual(
			{category: sla["response_min"] for category, sla in stored["expected_sla"].items()},
			RESPONSE_TARGET_MINUTES,
		)
		fieldnames = [field.fieldname for field in frappe.get_meta(SETTING_DOCTYPE).fields]
		self.assertEqual([name for name in fieldnames if "response" in name], [])

	def test_operations_section_shape(self):
		# design.md:108: section 12 follows the knowledge section; design.md:138-149: the field types; the two
		# watermarks are read-only; design.md:189-197: the KPI targets default.
		meta = frappe.get_meta(SETTING_DOCTYPE)
		order = [field.fieldname for field in meta.fields]
		self.assertIn("section_operations", order, "ERP AI Setting has no section_operations")
		start = order.index("section_operations")
		self.assertEqual(order[start - 1], "report_row_limit")
		self.assertEqual(order[start + 1 : start + 13], list(OPERATIONS_SECTION))
		self.assertEqual(
			{fieldname: meta.get_field(fieldname).fieldtype for fieldname in OPERATIONS_SECTION},
			OPERATIONS_SECTION,
		)
		self.assertEqual(meta.get_field("d_ticket_watcher").options, "User")
		self.assertEqual(meta.get_field("kpi_targets").options, "JSON")
		read_only = {name for name in OPERATIONS_SECTION if meta.get_field(name).read_only}
		self.assertEqual(read_only, {"daily_report_sent_on", "budget_alert_sent_month"})
		self.assertEqual(json.loads(meta.get_field("kpi_targets").default), DEFAULT_KPI_TARGETS)

	def test_watermarks_start_unset(self):
		# design.md:148-149: the two watermarks have no default; install stores no value for them.
		for fieldname in ("daily_report_sent_on", "budget_alert_sent_month"):
			with self.subTest(fieldname=fieldname):
				self.assertIsNone(frappe.get_meta(SETTING_DOCTYPE).get_field(fieldname).default)
				self._value_after_install(fieldname)
				stored = frappe.db.sql(
					"select value from `tabSingles` where doctype=%s and field=%s",
					(SETTING_DOCTYPE, fieldname),
				)
				self.assertEqual(stored, ())


# FEAT-007 AC-22, AC-36, AC-44, AC-46, AC-49, AC-51, AC-59, AC-63: fieldname -> (exact error text, low, high).
FEAT007_INT_LIMITS = {
	"confidence_threshold": ("Ngưỡng độ tin cậy phải từ 0 đến 100", 0, 100),
	"auto_approve_streak": ("Số lần duyệt liên tiếp để Tự làm phải từ 1 đến 100", 1, 100),
	"close_silent_f_days": ("Số ngày chờ trước khi đóng phiếu F phải từ 1 đến 30", 1, 30),
	"knowledge_search_limit": ("Số kết quả tìm tri thức tối đa phải từ 1 đến 20", 1, 20),
	"report_row_limit": ("Số dòng báo cáo tối đa phải từ 1 đến 100", 1, 100),
	"review_sample_size": ("Số phiếu rà soát mỗi tháng phải từ 1 đến 50", 1, 50),
	"due_reminder_hours": ("Số giờ báo trước hạn phải từ 1 đến 168", 1, 168),
	"ba_note_due_hours": ("Số giờ chờ BA note phải từ 1 đến 168", 1, 168),
	"task_due_days": ("Số ngày chờ Task phải từ 1 đến 30", 1, 30),
	"max_tasks_per_run": ("Số Task tối đa mỗi lần chạy phải từ 1 đến 20", 1, 20),
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

	def _save_rows(self, *rows, ignore_links=False):
		"""Save the setting with exactly these catalog rows; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("catalog_rules", [])
		for row in rows:
			doc.append("catalog_rules", {"categories": "A", "mode": constants.MODE_NEEDS_APPROVAL, **row})
		doc.flags.ignore_links = ignore_links
		try:
			doc.save()
		except frappe.ValidationError as error:
			return frappe.utils.strip_html(str(error))
		return None

	def _stored_rows(self):
		return [
			(row.action, row.target_doctype, row.fields, row.categories)
			for row in frappe.get_doc(SETTING_DOCTYPE).catalog_rules
		]

	def test_row_shape_rules(self):
		# AC-29, E-4 (design.md:214-221, 300-305): each case differs from a valid row in one rule only;
		# a valid row stands first so the bad row is row 2 and {idx} is pinned.
		first = {"action": constants.ACTION_ADD_HOLIDAY}
		update_note = {"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "Note", "fields": "title"}
		custom_field_note = {"action": constants.ACTION_CREATE_CUSTOM_FIELD, "target_doctype": "Note"}
		fixed_actions = (
			constants.ACTION_CREATE_USER,
			constants.ACTION_ADD_TEAM_MEMBER,
			constants.ACTION_ADD_HOLIDAY,
			constants.ACTION_SET_ITEM_GROUP,
		)
		cases = []
		for action in fixed_actions:
			cases += [
				(action, {"action": action, "target_doctype": "Note"}, "hành động này không nhận DocType"),
				(action, {"action": action, "fields": "title"}, "hành động này không nhận danh sách trường"),
			]
		cases += [
			(
				"custom field, no DocType",
				{**custom_field_note, "target_doctype": None},
				"hành động này cần DocType",
			),
			(
				"custom field, fields",
				{**custom_field_note, "fields": "title"},
				"hành động này không nhận danh sách trường",
			),
			("update, no DocType", {**update_note, "target_doctype": None}, "hành động này cần DocType"),
			("update, no fields", {**update_note, "fields": None}, "cần ít nhất một trường"),
			("update, blank lines", {**update_note, "fields": "\n  \n"}, "cần ít nhất một trường"),
			(
				"update, unknown field",
				{**update_note, "fields": "title\nkhong_co_truong"},
				"trường khong_co_truong không có trên Note",
			),
		]
		category_error = "đầu mục phải là các chữ A\u2013F cách nhau bằng dấu phẩy"  # en dash, as in E-4
		for categories in ("G", "A,G", "a", "AB", "A,,B", "A,", "A;B"):
			cases.append(
				(f"categories {categories!r}", {**update_note, "categories": categories}, category_error)
			)
		stored_before = self._stored_rows()
		for label, row, reason in cases:
			with self.subTest(label):
				self.assertEqual(self._save_rows(first, row), f"Danh mục dòng 2: {reason}")
		# Duplicate: same action + target_doctype; the later row names the earlier one.
		self.assertEqual(
			self._save_rows(first, update_note, {**update_note, "fields": "content", "categories": "B"}),
			"Danh mục dòng 3: trùng với dòng 2",
		)
		self.assertEqual(
			self._save_rows(first, {"action": constants.ACTION_ADD_HOLIDAY, "categories": "C"}),
			"Danh mục dòng 2: trùng với dòng 1",
		)
		self.assertEqual(self._stored_rows(), stored_before)

	def test_unknown_action_and_case_variant_doctype(self):
		# T10 review: a row without a DocType still has its action checked; a DocType typed in another
		# letter case is the same DocType for the ban sets and is stored under its real name.
		self.assertEqual(
			self._save_rows({"action": constants.ACTION_ADD_HOLIDAY}, {"action": "Xóa bản ghi"}),
			"Danh mục dòng 2: hành động không hợp lệ",
		)
		self.assertEqual(
			self._save_rows(
				{"action": constants.ACTION_ADD_HOLIDAY},
				{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "erp ai log", "fields": "title"},
				ignore_links=True,
			),
			"Danh mục dòng 2: DocType ERP AI Log bị cấm cứng: "
			"DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)",
		)
		self.assertIsNone(
			self._save_rows(
				{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "note", "fields": "title"},
				ignore_links=True,
			)
		)
		self.assertEqual(self._stored_rows(), [(constants.ACTION_UPDATE_FIELDS, "Note", "title", "A")])
		self.assertEqual(
			self._save_rows(
				{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "Note", "fields": "title"},
				{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "NOTE", "fields": "content"},
				ignore_links=True,
			),
			"Danh mục dòng 2: trùng với dòng 1",
		)

	def test_valid_rule_saves_and_categories_normalized(self):
		# AC-29: one valid row per action saves; categories become "A,B" (no duplicates, sorted, no spaces).
		rows = (
			{"action": constants.ACTION_CREATE_USER, "categories": "C,A"},
			{"action": constants.ACTION_ADD_TEAM_MEMBER, "categories": "B,B"},
			{"action": constants.ACTION_ADD_HOLIDAY, "categories": "A, B"},
			{"action": constants.ACTION_SET_ITEM_GROUP, "categories": " F ,E,F,D "},
			{
				"action": constants.ACTION_CREATE_CUSTOM_FIELD,
				"target_doctype": "Note",
				"categories": "A,B,C,D,E,F",
			},
			{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "Note", "fields": "title\ncontent"},
			# Same DocType, other action; same action, other DocType: not duplicates.
			{"action": constants.ACTION_CREATE_CUSTOM_FIELD, "target_doctype": "ToDo"},
			{"action": constants.ACTION_UPDATE_FIELDS, "target_doctype": "ToDo", "fields": "description"},
		)
		self.assertIsNone(self._save_rows(*rows))
		self.assertEqual(
			self._stored_rows(),
			[
				(constants.ACTION_CREATE_USER, None, None, "A,C"),
				(constants.ACTION_ADD_TEAM_MEMBER, None, None, "B"),
				(constants.ACTION_ADD_HOLIDAY, None, None, "A,B"),
				(constants.ACTION_SET_ITEM_GROUP, None, None, "D,E,F"),
				(constants.ACTION_CREATE_CUSTOM_FIELD, "Note", None, "A,B,C,D,E,F"),
				(constants.ACTION_UPDATE_FIELDS, "Note", "title\ncontent", "A"),
				(constants.ACTION_CREATE_CUSTOM_FIELD, "ToDo", None, "A"),
				(constants.ACTION_UPDATE_FIELDS, "ToDo", "description", "A"),
			],
		)


USER_TEMPLATE_JSON = (
	Path(erp_ai_setting.__file__).resolve().parent.parent
	/ "erp_ai_user_template"
	/ "erp_ai_user_template.json"
)
# AC-30 (1), spec.md:196: the six roles a template may never hold, written out once.
SPEC_FORBIDDEN_ROLES = (
	"System Manager",
	"Administrator",
	"ERP AI Instructor",
	"ERP AI Agent",
	"Guest",
	"All",
)
# Each forbidden role with one vowel accented: tabRole's utf8mb4_unicode_ci collation still finds the real role.
ACCENTED_FORBIDDEN_ROLES = {
	"System Manager": "Sýstem Manager",
	"Administrator": "Ádministrator",
	"ERP AI Instructor": "ERP AI Ínstructor",
	"ERP AI Agent": "ERP AI Ágent",
	"Guest": "Gúest",
	"All": "Áll",
}
# Own test data: two business roles created in setUp, rolled back afterwards.
STOCK_ROLE = "ERP AI Test Thủ kho"
OFFICE_ROLE = "ERP AI Test Văn phòng"


class TestUserTemplates(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.assertTrue(
			frappe.db.exists("DocType", USER_TEMPLATE_DOCTYPE), "DocType ERP AI User Template is missing"
		)
		for role in (STOCK_ROLE, OFFICE_ROLE):
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

	def _save_templates(self, *rows):
		"""Save the setting with exactly these template rows; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.set("user_templates", [])
		for row in rows:
			doc.append("user_templates", row)
		try:
			doc.save()
		except frappe.ValidationError as error:
			return frappe.utils.strip_html(str(error))
		return None

	def _stored_templates(self):
		return [
			(row.template_name, row.roles, row.note) for row in frappe.get_doc(SETTING_DOCTYPE).user_templates
		]

	def test_child_doctype_and_field_shape(self):
		# design.md:225 and :100: three fields; the Table sits right after catalog_rules in section_catalog.
		doctype_json = json.loads(USER_TEMPLATE_JSON.read_text(encoding="utf-8"))
		self.assertEqual(doctype_json["istable"], 1)
		fields = {f["fieldname"]: f for f in doctype_json["fields"] if f["fieldtype"] != "Section Break"}
		self.assertEqual(
			{name: (f["fieldtype"], f.get("reqd", 0)) for name, f in fields.items()},
			{"template_name": ("Data", 1), "roles": ("Small Text", 0), "note": ("Small Text", 0)},
		)
		meta = frappe.get_meta(SETTING_DOCTYPE)
		field = meta.get_field("user_templates")
		self.assertEqual((field.fieldtype, field.options), ("Table", USER_TEMPLATE_DOCTYPE))
		order = [f.fieldname for f in meta.fields]
		self.assertEqual(order[order.index("section_catalog") + 1 :][:2], ["catalog_rules", "user_templates"])
		doc = frappe.new_doc(USER_TEMPLATE_DOCTYPE)
		self.assertEqual(type(doc).__name__, "ERPAIUserTemplate")
		self.assertEqual(type(doc).__bases__, (Document,))
		self.assertEqual([name for name in vars(type(doc)) if not name.startswith("__")], [])

	def test_forbidden_role_blocked(self):
		# AC-30 (1): each of the six roles alone makes the template unsavable, also typed in another case
		# or with an accent the database ignores (the check runs on the real role name, STD-ERR-2);
		# a valid template stands first (decoy) so the bad row is row 2 and {idx} is pinned.
		self.assertEqual(site_api.FORBIDDEN_ROLES, frozenset(SPEC_FORBIDDEN_ROLES))
		self.assertEqual(set(ACCENTED_FORBIDDEN_ROLES), set(SPEC_FORBIDDEN_ROLES))
		decoy = {"template_name": "Thủ kho", "roles": STOCK_ROLE}
		stored_before = self._stored_templates()
		for role in SPEC_FORBIDDEN_ROLES:
			for typed in (role, role.upper(), ACCENTED_FORBIDDEN_ROLES[role]):
				with self.subTest(role=typed):
					self.assertEqual(
						self._save_templates(
							decoy, {"template_name": "Quản trị", "roles": f"{OFFICE_ROLE}\n{typed}"}
						),
						f"Mẫu tài khoản dòng 2: vai trò {role} bị cấm cho bot",
					)
		self.assertEqual(self._stored_templates(), stored_before)

	def test_unknown_role_and_duplicate_name_blocked(self):
		# AC-30 (1), E-5: unknown role; name duplicated regardless of case and spaces; blank name; no role.
		decoy = {"template_name": "Thủ kho", "roles": STOCK_ROLE}
		cases = (
			(
				"unknown role",
				{"template_name": "Văn phòng", "roles": f"{OFFICE_ROLE}\nKhông Có Vai Trò Này"},
				"không có vai trò Không Có Vai Trò Này",
			),
			("same name", {"template_name": "Thủ kho", "roles": OFFICE_ROLE}, "trùng tên với dòng 1"),
			("other case", {"template_name": "THỦ KHO", "roles": OFFICE_ROLE}, "trùng tên với dòng 1"),
			("spaces", {"template_name": "  thủ kho ", "roles": OFFICE_ROLE}, "trùng tên với dòng 1"),
			("blank name", {"template_name": "   ", "roles": OFFICE_ROLE}, "tên mẫu không được để trống"),
			("no role", {"template_name": "Văn phòng", "roles": None}, "cần ít nhất một vai trò"),
			("blank lines", {"template_name": "Văn phòng", "roles": "\n  \n"}, "cần ít nhất một vai trò"),
		)
		stored_before = self._stored_templates()
		for label, row, reason in cases:
			with self.subTest(label):
				self.assertEqual(self._save_templates(decoy, row), f"Mẫu tài khoản dòng 2: {reason}")
		# Bad row at position 3 of 4, duplicating row 2: pins {idx} and {j} beyond the first two rows.
		self.assertEqual(
			self._save_templates(
				decoy,
				{"template_name": "Văn phòng", "roles": OFFICE_ROLE},
				{"template_name": "VĂN PHÒNG", "roles": STOCK_ROLE},
				{"template_name": "Kế toán", "roles": OFFICE_ROLE},
			),
			"Mẫu tài khoản dòng 3: trùng tên với dòng 2",
		)
		self.assertEqual(self._stored_templates(), stored_before)

	def test_valid_template_saves(self):
		# AC-30 (1): templates with known, allowed roles save; names differing by one letter are not duplicates;
		# roles are stored one per line under their real name, blank lines dropped.
		rows = (
			{
				"template_name": "Thủ kho",
				"roles": f" {STOCK_ROLE} \n\n{OFFICE_ROLE.upper()}",
				"note": "Kho chính",
			},
			{"template_name": "Thủ kho 2", "roles": STOCK_ROLE},
		)
		self.assertIsNone(self._save_templates(*rows))
		self.assertEqual(
			self._stored_templates(),
			[
				("Thủ kho", f"{STOCK_ROLE}\n{OFFICE_ROLE}", "Kho chính"),
				("Thủ kho 2", STOCK_ROLE, None),
			],
		)


# FEAT-007 design.md:104-106, 127-128 (AC-24): the ticket field names, in form order, with their form label (E-1).
TICKET_FIELD_LABELS = {
	"field_ticket_nature": "Tính chất phiếu",
	"field_erp_module": "Phân hệ ERP",
	"field_origin": "Nguồn phát sinh",
	"field_due_date": "Hạn hoàn thành",
	"field_project": "Dự án",
	"field_item_code": "Mã hàng",
	"field_serial_no": "Số sê-ri",
}
TICKET_FIELD_SECTION = (
	"section_ticket_fields",
	"field_ticket_nature",
	"field_erp_module",
	"field_origin",
	"origin_board_value",
	"field_due_date",
	"field_project",
	"field_item_code",
	"field_serial_no",
)
DUE_FIELD_ERROR = "Trường Hạn hoàn thành phải có kiểu Date hoặc Datetime"
BOARD_VALUE_ERROR = "Đặt giá trị Chỉ đạo BGĐ thì phải đặt tên trường Nguồn phát sinh"
BOARD_VALUE = "Chỉ đạo BGĐ"
# Real HD Ticket fields, one per setting: Helpdesk's own fields and the Custom Fields erp_ai installs
# (test_install pins them), so no test creates a Custom Field (its ALTER TABLE would commit).
VALID_TICKET_FIELDS = {
	"field_ticket_nature": "ticket_type",
	"field_erp_module": "ai_score_reason",
	"field_origin": "ai_confidence",
	"field_due_date": "ai_updated_at",
	"field_project": "subject",
	"field_item_code": "ai_classified_by",
	"field_serial_no": "raised_by",
}
CUSTOM_TICKET_FIELDS = ("ai_score_reason", "ai_confidence", "ai_updated_at", "ai_classified_by")


def _accented(name):
	"""`name` with its first plain vowel accented: the database collation would still match it."""
	vowel = next(letter for letter in name if letter in "aeiou")
	return name.replace(vowel, "áéíóú"["aeiou".index(vowel)], 1)


def _unknown_ticket_field_error(fieldname, typed):
	return f"Trường '{typed}' không có trên HD Ticket ({TICKET_FIELD_LABELS[fieldname]})"


class TestTicketFieldNames(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		meta = frappe.get_meta(SETTING_DOCTYPE)
		for fieldname in TICKET_FIELD_SECTION:
			self.assertTrue(meta.has_field(fieldname), f"ERP AI Setting has no {fieldname} field")
		for fieldname in CUSTOM_TICKET_FIELDS:
			self.assertTrue(
				frappe.db.exists("Custom Field", {"dt": "HD Ticket", "fieldname": fieldname}),
				f"Custom Field HD Ticket.{fieldname} of erp_ai is missing",
			)
		self.assertIsNone(self._save(dict.fromkeys(TICKET_FIELD_SECTION[1:], "")))

	def _save(self, values):
		"""Save the setting with these values; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update(values)
		try:
			doc.save()
		except frappe.ValidationError as error:
			return frappe.utils.strip_html(str(error))
		return None

	def _stored(self):
		return {
			fieldname: frappe.db.get_single_value(SETTING_DOCTYPE, fieldname, cache=False) or ""
			for fieldname in TICKET_FIELD_SECTION[1:]
		}

	def test_section_and_field_shape(self):
		# design.md:104-106, 127-128: one Data field per name and the board value, in this order, after routing;
		# D-19: the excluded title prefixes sit right after excluded_teams.
		meta = frappe.get_meta(SETTING_DOCTYPE)
		order = [field.fieldname for field in meta.fields]
		self.assertIn("section_ticket_fields", order, "ERP AI Setting has no section_ticket_fields")
		start = order.index("section_ticket_fields")
		self.assertEqual(order[start : start + 10], [*TICKET_FIELD_SECTION, "section_code_change"])
		self.assertLess(order.index("prompt_digest"), start)
		for fieldname in TICKET_FIELD_SECTION[1:]:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(meta.get_field(fieldname).fieldtype, "Data")
		for fieldname, label in TICKET_FIELD_LABELS.items():
			self.assertEqual(meta.get_field(fieldname).label, label)
		self.assertEqual(order[order.index("excluded_teams") + 1], "excluded_title_prefixes")
		field = meta.get_field("excluded_title_prefixes")
		self.assertEqual((field.fieldtype, field.default), ("Small Text", "[HR]\n[Kế toán]"))

	def test_unknown_field_blocked(self):
		# AC-24, E-1: each of the seven names alone, as an unknown name, in another letter case and with an
		# accent (meta names are exact, STD-ERR-2); the other six hold real fields (decoy).
		self.assertIsNone(self._save(VALID_TICKET_FIELDS))
		stored_before = self._stored()
		for fieldname in TICKET_FIELD_LABELS:
			real = VALID_TICKET_FIELDS[fieldname]
			for typed in ("khong_co_truong_nay", real.upper(), _accented(real), real.title()):
				with self.subTest(fieldname=fieldname, typed=typed):
					self.assertNotEqual(typed, real)
					self.assertEqual(
						self._save(VALID_TICKET_FIELDS | {fieldname: f" {typed} "}),
						_unknown_ticket_field_error(fieldname, typed),
					)
		# Two wrong names: the first in form order is reported.
		self.assertEqual(
			self._save(VALID_TICKET_FIELDS | {"field_erp_module": "sai_mot", "field_serial_no": "sai_hai"}),
			_unknown_ticket_field_error("field_erp_module", "sai_mot"),
		)
		self.assertEqual(self._stored(), stored_before)

	def test_unknown_field_name_escaped(self):
		# AC-24, E-1, STD-SEC-3: the typed name is HTML-escaped in the message, as the key label is (:308).
		# Turns red when check_ticket_field_names puts the name into frappe.throw unescaped.
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update(VALID_TICKET_FIELDS | {"field_ticket_nature": "<b>sai</b>"})
		with self.assertRaises(frappe.ValidationError) as raised:
			doc.save()
		self.assertEqual(
			str(raised.exception),
			"Trường '&lt;b&gt;sai&lt;/b&gt;' không có trên HD Ticket (Tính chất phiếu)",
		)

	def test_ticket_fields_checked_before_catalog(self):
		# design.md:294, steps 4 then 5: a save with both a wrong ticket field name and a bad catalog row
		# reports E-1. Turns red when check_catalog_rules runs before check_ticket_field_names in validate.
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update(VALID_TICKET_FIELDS | {"field_erp_module": "sai_mot"})
		doc.set("catalog_rules", [])
		doc.append(
			"catalog_rules",
			{
				"action": constants.ACTION_ADD_HOLIDAY,
				"target_doctype": "Note",
				"categories": "A",
				"mode": constants.MODE_NEEDS_APPROVAL,
			},
		)
		with self.assertRaises(frappe.ValidationError) as raised:
			doc.save()
		self.assertEqual(str(raised.exception), _unknown_ticket_field_error("field_erp_module", "sai_mot"))

	def test_due_field_must_be_date(self):
		# AC-24, E-2: Data, Link, Time, Small Text and Select fields are refused; an unknown name stays E-1.
		self.assertIsNone(self._save(VALID_TICKET_FIELDS))
		stored_before = self._stored()
		for typed in ("subject", "priority", "opening_time", "ai_score_reason", "ai_confidence"):
			with self.subTest(typed=typed):
				self.assertEqual(self._save(VALID_TICKET_FIELDS | {"field_due_date": typed}), DUE_FIELD_ERROR)
		self.assertEqual(
			self._save(VALID_TICKET_FIELDS | {"field_due_date": "han_khong_co"}),
			_unknown_ticket_field_error("field_due_date", "han_khong_co"),
		)
		self.assertEqual(self._stored(), stored_before)
		# A Date and a Datetime field (Helpdesk's own) save.
		for typed in ("opening_date", "resolution_by"):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save({"field_due_date": typed}))
				self.assertEqual(self._stored()["field_due_date"], typed)

	def test_board_value_needs_origin_field(self):
		# AC-24, E-3: the board value without the origin field is refused (empty or blank origin);
		# the origin field without a board value saves, and so does a blank board value.
		stored_before = self._stored()
		for origin in ("", "   ", None):
			with self.subTest(origin=origin):
				self.assertEqual(
					self._save({"origin_board_value": BOARD_VALUE, "field_origin": origin}), BOARD_VALUE_ERROR
				)
		self.assertEqual(self._stored(), stored_before)
		self.assertIsNone(self._save({"origin_board_value": "  ", "field_origin": ""}))
		self.assertEqual(self._stored()["origin_board_value"], "")
		self.assertIsNone(self._save({"origin_board_value": "", "field_origin": "ai_confidence"}))
		self.assertEqual(
			(self._stored()["field_origin"], self._stored()["origin_board_value"]), ("ai_confidence", "")
		)

	def test_existing_custom_field_saves(self):
		# AC-24: names of real fields (erp_ai's Custom Fields and Helpdesk's own) save, trimmed; blank names
		# stay unset.
		values = {fieldname: f"  {name}\t" for fieldname, name in VALID_TICKET_FIELDS.items()}
		self.assertIsNone(self._save(values | {"origin_board_value": f" {BOARD_VALUE} "}))
		self.assertEqual(self._stored(), VALID_TICKET_FIELDS | {"origin_board_value": BOARD_VALUE})
		self.assertIsNone(self._save(dict.fromkeys(TICKET_FIELD_LABELS, "  ") | {"origin_board_value": ""}))
		self.assertEqual(self._stored(), dict.fromkeys(TICKET_FIELD_SECTION[1:], ""))


# FEAT-007 design.md:107: section_knowledge and its nine fields, in form order, with their field types.
KNOWLEDGE_SECTION = {
	"reply_enabled": "Check",
	"resolve_on_tasks_done_enabled": "Check",
	"close_silent_f_enabled": "Check",
	"close_silent_f_days": "Int",
	"kb_draft_enabled": "Check",
	"knowledge_search_limit": "Int",
	"manuals_dir": "Data",
	"allowed_reports": "Small Text",
	"report_row_limit": "Int",
}


def _manuals_dir_error(typed):
	return f"Kho HDSD '{typed}' phải là thư mục có sẵn dưới apps/"


class TestManualsDir(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.sandbox = TempAppsRoot(self, apps=("myapp",))
		self.sandbox.write("myapp/docs/hdsd.md", "# HDSD\n")
		self.assertIsNone(self._save(""))

	def _save(self, value):
		"""Save the setting with this manuals_dir (no app list, so the temp root holds); return the error or None."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update({"manuals_dir": value, "code_change_apps": ""})
		try:
			doc.save()
		except frappe.ValidationError as error:
			return str(error)
		return None

	def _stored(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "manuals_dir", cache=False) or ""

	def test_section_and_field_shape(self):
		# design.md:107: section 11 follows the code-change block; design.md:131-137: the field types.
		meta = frappe.get_meta(SETTING_DOCTYPE)
		order = [field.fieldname for field in meta.fields]
		self.assertIn("section_knowledge", order, "ERP AI Setting has no section_knowledge")
		start = order.index("section_knowledge")
		self.assertEqual(order[start - 1], "code_change_apps")
		self.assertEqual(order[start + 1 : start + 10], list(KNOWLEDGE_SECTION))
		self.assertEqual(
			{fieldname: meta.get_field(fieldname).fieldtype for fieldname in KNOWLEDGE_SECTION},
			KNOWLEDGE_SECTION,
		)

	def test_missing_or_outside_dir_blocked(self):
		# AC-47, E-7: a missing directory, a file, a path leaving apps/ (traversal, absolute, symlink) and
		# apps/ itself are refused; the stored value does not change.
		self.assertIsNone(self._save("myapp/docs"))
		refused = (
			"myapp/khong_co",
			"myapp/docs/hdsd.md",
			"myapp/ok.py",
			"../outside",
			"myapp/../../outside",
			self.sandbox.outside,
			"myapp/dir_out",
			".",
			"myapp/..",
			self.sandbox.root,
		)
		for typed in refused:
			with self.subTest(typed=typed):
				self.assertEqual(self._save(f" {typed} "), _manuals_dir_error(typed))
				self.assertEqual(self._stored(), "myapp/docs")

	def test_manuals_dir_escaped_in_error(self):
		# STD-SEC-3: the typed path is HTML-escaped in the message, as the ticket field name is.
		self.assertEqual(self._save("<b>x</b>"), _manuals_dir_error("&lt;b&gt;x&lt;/b&gt;"))

	def test_existing_dir_saves(self):
		# AC-47: an existing directory under apps/ saves trimmed; a blank value saves as empty.
		for typed, stored in (
			("myapp/docs", "myapp/docs"),
			("\tmyapp ", "myapp"),
			("myapp/docs/", "myapp/docs/"),
		):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(typed))
				self.assertEqual(self._stored(), stored)
		for typed in ("", "   ", None):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(typed))
				self.assertEqual(self._stored(), "")


def _report_error(typed, reason):
	return f"Báo cáo '{typed}' {reason}"


def _ticket_based_reason(doctype):
	return f"dựa trên {doctype}, mang nội dung phiếu hoặc dữ liệu của app: bot không được chạy"


class TestAllowedReports(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.assertTrue(
			frappe.get_meta(SETTING_DOCTYPE).has_field("allowed_reports"),
			"ERP AI Setting has no allowed_reports",
		)
		self.assertIsNone(self._save(""))

	def _report(self, name, ref_doctype="Note", report_type="Query Report", disabled=0):
		"""A Report row of this test (raw insert: Report.validate needs Script Manager and may export files)."""
		frappe.get_doc(
			{
				"doctype": "Report",
				"name": name,
				"report_name": name,
				"ref_doctype": ref_doctype,
				"report_type": report_type,
				"is_standard": "No",
				"disabled": disabled,
			}
		).db_insert()
		return name

	def _save(self, value, **fields):
		"""Save the setting with this allowed_reports (and fields); return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update({"allowed_reports": value, **fields})
		try:
			doc.save()
		except frappe.ValidationError as error:
			return str(error)
		return None

	def _stored(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "allowed_reports", cache=False) or ""

	def test_unknown_type_disabled_ticket_based_blocked(self):
		# AC-49, E-6: an unknown name (escaped), a type other than Script/Query Report, a disabled report and a
		# report on a DocType of TICKET_CONTENT_DOCTYPES are refused on any line; the stored value holds.
		safe = self._report("ERP AI Test BC an toàn")
		self.assertIsNone(self._save(safe))
		cases = [
			("ERP AI Test BC không có", _report_error("ERP AI Test BC không có", "không có")),
			("<b>x</b>", _report_error("&lt;b&gt;x&lt;/b&gt;", "không có")),
		]
		for report_type in ("Report Builder", "Custom Report"):
			name = self._report(f"ERP AI Test BC {report_type}", report_type=report_type)
			cases.append((name, _report_error(name, "phải là Script Report hoặc Query Report")))
		for report_type in ("Query Report", "Script Report"):
			name = self._report(f"ERP AI Test BC tắt {report_type}", report_type=report_type, disabled=1)
			cases.append((name, _report_error(name, "đang tắt")))
		for doctype in ("HD Ticket", "Comment", "Communication", "File"):
			name = self._report(f"ERP AI Test BC trên {doctype}", ref_doctype=doctype)
			cases.append((name, _report_error(name, _ticket_based_reason(doctype))))
		for typed, error in cases:
			with self.subTest(typed=typed):
				self.assertEqual(self._save(f"{safe}\n\n  {typed} \n{safe}"), error)
				self.assertEqual(self._stored(), safe)
		# design.md step 7 before step 8: a bad report is reported before a bad manuals directory.
		self.assertEqual(
			self._save("ERP AI Test BC không có", manuals_dir="khong_co_thu_muc_nay"),
			_report_error("ERP AI Test BC không có", "không có"),
		)

	def test_log_based_report_blocked(self):
		# AC-49, ADR-034 QĐ 3: a report on a DocType the read tools deny (app data) is refused, read live from
		# read.denied_doctypes().
		for doctype in ("ERP AI Log", "ERP AI Setting", "User"):
			name = self._report(f"ERP AI Test BC trên {doctype}", ref_doctype=doctype)
			with self.subTest(doctype=doctype):
				self.assertEqual(self._save(name), _report_error(name, _ticket_based_reason(doctype)))
				self.assertEqual(self._stored(), "")
		name = self._report("ERP AI Test BC trên Note")
		self.assertIsNone(self._save(name))
		original = read.denied_doctypes
		with patch.object(read, "denied_doctypes", lambda: original() | {"Note"}):
			self.assertEqual(self._save(name), _report_error(name, _ticket_based_reason("Note")))
		self.assertEqual(self._stored(), name)

	def test_report_on_ticket_linked_doctype_blocked(self):
		# design-w0-fixes-3.md ruling 2, C-T15-5: a DocType with a Link to HD Ticket (the legacy ticket comment
		# by its standard field, Task by erp_ai's Custom Field) carries ticket content.
		for doctype in ("HD Ticket Comment", "Task"):
			name = self._report(f"ERP AI Test BC trên {doctype}", ref_doctype=doctype)
			with self.subTest(doctype=doctype):
				self.assertEqual(self._save(name), _report_error(name, _ticket_based_reason(doctype)))
				self.assertEqual(self._stored(), "")

	def test_safe_report_saves(self):
		# AC-49: enabled Script and Query Reports on a DocType without ticket content save as typed; blank lines
		# are ignored; a blank value saves.
		query = self._report("ERP AI Test BC Query")
		script = self._report("ERP AI Test BC Script", ref_doctype="ToDo", report_type="Script Report")
		value = f"  {query}\n\n{script}\t\n"
		self.assertIsNone(self._save(value))
		self.assertEqual(self._stored(), value)
		for typed in ("", "\n  \n", None):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(typed))
				self.assertEqual(self._stored(), typed or "")


OPS_REVIEWER = "erpai-test-ops-reviewer@example.com"
OPS_REVIEWER_OFF = "erpai-test-ops-reviewer-off@example.com"
OPS_WATCHER = "erpai-test-ops-watcher@example.com"
WATCHER_ERROR = "Người theo dõi phiếu D phải là tài khoản người đang bật"


def _email_error(typed):
	return f"Người nhận báo cáo COO: '{typed}' không phải email hợp lệ"


def _reviewer_error(typed):
	return f"Người rà soát: không có tài khoản '{typed}' đang bật"


class TestOperationPeople(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.assertTrue(
			frappe.get_meta(SETTING_DOCTYPE).has_field("coo_report_recipients"),
			"ERP AI Setting has no coo_report_recipients",
		)
		for email, enabled in ((OPS_REVIEWER, 1), (OPS_REVIEWER_OFF, 0), (OPS_WATCHER, 1)):
			user = frappe.new_doc("User")
			user.update(
				{"email": email, "first_name": "ERP AI Test", "enabled": enabled, "send_welcome_email": 0}
			)
			user.insert(ignore_permissions=True)
		self.assertIsNone(self._save(coo_report_recipients="", monthly_reviewers="", d_ticket_watcher=""))

	def _save(self, **fields):
		"""Save the setting with these fields; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update(fields)
		try:
			doc.save()
		except frappe.ValidationError as error:
			return str(error)
		return None

	def _stored(self, fieldname):
		return frappe.db.get_single_value(SETTING_DOCTYPE, fieldname, cache=False) or ""

	def test_bad_email_blocked(self):
		# AC-51, E-8: a line that is not exactly one email is refused on any line (blank lines skipped); the typed
		# text is escaped; the stored value holds. design.md step 8 before step 9: a bad manuals dir comes first.
		good = "coo@example.com\n\n  ke.toan@congty.vn  \n"
		self.assertIsNone(self._save(coo_report_recipients=good))
		self.assertEqual(self._stored("coo_report_recipients"), good)
		for typed, shown in (
			("khong-phai-email", "khong-phai-email"),
			("coo@", "coo@"),
			("a@example.com, b@example.com", "a@example.com, b@example.com"),
			("a@example.com, sai", "a@example.com, sai"),
			("Giám đốc <coo@example.com>", "Giám đốc &lt;coo@example.com&gt;"),
			("<b>x</b>", "&lt;b&gt;x&lt;/b&gt;"),
		):
			with self.subTest(typed=typed):
				value = f"coo@example.com\n\n  {typed} \nke.toan@congty.vn"
				self.assertEqual(self._save(coo_report_recipients=value), _email_error(shown))
				self.assertEqual(self._stored("coo_report_recipients"), good)
		self.assertEqual(
			self._save(coo_report_recipients="sai", manuals_dir="khong_co_thu_muc_nay"),
			"Kho HDSD 'khong_co_thu_muc_nay' phải là thư mục có sẵn dưới apps/",
		)
		for typed in ("", "\n  \n", None):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(coo_report_recipients=typed, manuals_dir=""))
				self.assertEqual(self._stored("coo_report_recipients"), typed or "")

	def test_disabled_reviewer_blocked(self):
		# AC-59, E-8: each reviewer line must be an enabled User; a disabled or unknown account is refused on any
		# line (escaped); blank lines are skipped; the stored value holds; the COO list is checked first.
		good = f"{OPS_REVIEWER}\n\n  {OPS_WATCHER} \n"
		self.assertIsNone(self._save(monthly_reviewers=good))
		self.assertEqual(self._stored("monthly_reviewers"), good)
		for typed, shown in (
			(OPS_REVIEWER_OFF, OPS_REVIEWER_OFF),
			("erpai-test-khong-co@example.com", "erpai-test-khong-co@example.com"),
			("<b>x</b>", "&lt;b&gt;x&lt;/b&gt;"),
		):
			with self.subTest(typed=typed):
				value = f"{OPS_REVIEWER}\n\n {typed}\t\n{OPS_WATCHER}"
				self.assertEqual(self._save(monthly_reviewers=value), _reviewer_error(shown))
				self.assertEqual(self._stored("monthly_reviewers"), good)
		self.assertEqual(
			self._save(monthly_reviewers=OPS_REVIEWER_OFF, coo_report_recipients="sai"), _email_error("sai")
		)
		for typed in ("", "\n  \n", None):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(monthly_reviewers=typed, coo_report_recipients=""))
				self.assertEqual(self._stored("monthly_reviewers"), typed or "")

	def test_watcher_must_be_enabled_human(self):
		# AC-27, E-8: the D watcher, when set, must be enabled and not the agent account (each half alone); an
		# unknown account is refused too; empty is allowed; the reviewers are checked first.
		self.assertEqual(frappe.db.get_value("User", AGENT_USER, "enabled"), 1)
		self.assertIsNone(self._save(d_ticket_watcher=OPS_WATCHER))
		self.assertEqual(self._stored("d_ticket_watcher"), OPS_WATCHER)
		for typed in (OPS_REVIEWER_OFF, AGENT_USER, AGENT_USER.upper()):
			with self.subTest(typed=typed):
				self.assertEqual(self._save(d_ticket_watcher=typed), WATCHER_ERROR)
				self.assertEqual(self._stored("d_ticket_watcher"), OPS_WATCHER)
		self.assertIsNotNone(self._save(d_ticket_watcher="erpai-test-khong-co@example.com"))
		self.assertEqual(self._stored("d_ticket_watcher"), OPS_WATCHER)
		self.assertEqual(
			self._save(d_ticket_watcher=AGENT_USER, monthly_reviewers=OPS_REVIEWER_OFF),
			_reviewer_error(OPS_REVIEWER_OFF),
		)
		for typed in ("", None):
			with self.subTest(typed=typed):
				self.assertIsNone(self._save(d_ticket_watcher=typed, monthly_reviewers=""))
				self.assertEqual(self._stored("d_ticket_watcher"), "")


KPI_ERROR_PREFIX = "Mục tiêu KPI: "
KPI_ALLOWED = (
	"first_response_minutes, complete_fields_pct, closed_without_human_pct, b_resolution_hours, "
	"c_task_in_3_days_pct, stale_over_5_days"
)


def _kpi_targets(**changes):
	"""The default targets with these KPI entries replaced (a value of ... drops the KPI)."""
	targets = {kpi: dict(stages) for kpi, stages in DEFAULT_KPI_TARGETS.items()}
	for kpi, value in changes.items():
		if value is ...:
			targets.pop(kpi)
		else:
			targets[kpi] = value
	return targets


class TestKpiTargets(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		self.default_raw = frappe.get_meta(SETTING_DOCTYPE).get_field("kpi_targets").default
		self.assertEqual(json.loads(self.default_raw), DEFAULT_KPI_TARGETS)
		self.assertIsNone(self._save(kpi_targets=self.default_raw, coo_report_recipients=""))

	def _save(self, **fields):
		"""Save the setting with these fields; return the error text, or None when it saved."""
		doc = frappe.get_doc(SETTING_DOCTYPE)
		doc.update(fields)
		try:
			doc.save()
		except frappe.ValidationError as error:
			return str(error)
		return None

	def _stored(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "kpi_targets", cache=False)

	def test_default_targets_valid(self):
		# AC-55, E-9: the shipped default saves as is; zero, decimals, another key order and outer blanks pass.
		self.assertEqual(json.loads(self._stored()), DEFAULT_KPI_TARGETS)
		reordered = dict(reversed(list(_kpi_targets(b_resolution_hours={"gd4": 0.5, "gd2": 0}).items())))
		for value in (
			json.dumps(reordered),
			"\n  " + json.dumps(_kpi_targets(stale_over_5_days={"gd2": 21, "gd4": 1e3})) + "\n",
		):
			with self.subTest(value=value):
				self.assertIsNone(self._save(kpi_targets=value))
				self.assertEqual(self._stored(), value)

	def test_bad_targets_blocked(self):
		# AC-55, E-9: each refusal names the key path; the stored value holds; the first fault in KPI_IDS order
		# (unknown top keys before) wins; the operations people (step 9) are checked before the targets (step 10).
		good = json.dumps(_kpi_targets(first_response_minutes={"gd2": 20, "gd4": 7}))
		self.assertIsNone(self._save(kpi_targets=good))
		number = "phải là số không âm"
		stages = "phải là object có đúng gd2 và gd4"
		cases = (
			(json.dumps(_kpi_targets(b_resolution_hours=...)), "b_resolution_hours bị thiếu"),
			(json.dumps(_kpi_targets(stale_over_5_days=...)), "stale_over_5_days bị thiếu"),
			(
				json.dumps(_kpi_targets(complete_fields_pct=..., stale_over_5_days=...)),
				"complete_fields_pct bị thiếu",
			),
			(
				json.dumps({**DEFAULT_KPI_TARGETS, "other_kpi": {"gd2": 1, "gd4": 1}}),
				f"other_kpi không phải KPI hợp lệ, chỉ nhận {KPI_ALLOWED}",
			),
			(
				json.dumps({"<b>x</b>": {}, **_kpi_targets(first_response_minutes=...)}),
				f"&lt;b&gt;x&lt;/b&gt; không phải KPI hợp lệ, chỉ nhận {KPI_ALLOWED}",
			),
			(json.dumps(_kpi_targets(complete_fields_pct=[100, 100])), f"complete_fields_pct {stages}"),
			(json.dumps(_kpi_targets(b_resolution_hours=4)), f"b_resolution_hours {stages}"),
			(
				json.dumps(_kpi_targets(c_task_in_3_days_pct={"gd4": 100})),
				"c_task_in_3_days_pct.gd2 bị thiếu",
			),
			(
				json.dumps(_kpi_targets(closed_without_human_pct={"gd2": 10})),
				"closed_without_human_pct.gd4 bị thiếu",
			),
			(
				json.dumps(_kpi_targets(stale_over_5_days={"gd2": 10, "gd4": 4, "gd3": 6})),
				"stale_over_5_days.gd3 không hợp lệ, chỉ nhận gd2, gd4",
			),
			(
				json.dumps(_kpi_targets(stale_over_5_days={"gd2": 10, "gd4": 4, "<i>": 6})),
				"stale_over_5_days.&lt;i&gt; không hợp lệ, chỉ nhận gd2, gd4",
			),
			(
				json.dumps(_kpi_targets(b_resolution_hours={"gd2": -1, "gd4": 1})),
				f"b_resolution_hours.gd2 {number}",
			),
			(
				json.dumps(_kpi_targets(stale_over_5_days={"gd2": 10, "gd4": -0.5})),
				f"stale_over_5_days.gd4 {number}",
			),
			(
				json.dumps(_kpi_targets(complete_fields_pct={"gd2": "100", "gd4": 100})),
				f"complete_fields_pct.gd2 {number}",
			),
			(
				json.dumps(_kpi_targets(complete_fields_pct={"gd2": 100, "gd4": None})),
				f"complete_fields_pct.gd4 {number}",
			),
			(
				json.dumps(_kpi_targets(closed_without_human_pct={"gd2": True, "gd4": 30})),
				f"closed_without_human_pct.gd2 {number}",
			),
			(
				json.dumps(_kpi_targets(first_response_minutes={"gd2": 15, "gd4": False})),
				f"first_response_minutes.gd4 {number}",
			),
			(
				json.dumps(_kpi_targets(c_task_in_3_days_pct={"gd2": 80, "gd4": float("inf")})),
				f"c_task_in_3_days_pct.gd4 {number}",
			),
			(
				json.dumps(_kpi_targets(b_resolution_hours={"gd2": float("nan"), "gd4": 1})),
				f"b_resolution_hours.gd2 {number}",
			),
			(
				json.dumps(
					_kpi_targets(
						complete_fields_pct={"gd2": -1, "gd4": 100},
						b_resolution_hours=...,
						stale_over_5_days={"gd2": 10},
					)
				),
				f"complete_fields_pct.gd2 {number}",
			),
			('{"first_response_minutes": {"gd2": 15, "gd4": 5},', "không phải JSON object hợp lệ"),
			("{'first_response_minutes': {}}", "không phải JSON object hợp lệ"),
			(json.dumps([DEFAULT_KPI_TARGETS]), "không phải JSON object hợp lệ"),
			('"xxx"', "không phải JSON object hợp lệ"),
			("12", "không phải JSON object hợp lệ"),
		)
		for value, reason in cases:
			with self.subTest(value=value):
				self.assertEqual(self._save(kpi_targets=value), KPI_ERROR_PREFIX + reason)
				self.assertEqual(self._stored(), good)
		empty = f"{KPI_ERROR_PREFIX}không được để trống. Muốn khôi phục, hãy dán JSON mặc định sau:\n{self.default_raw}"
		for value in ("", "  \n\t ", None):
			with self.subTest(value=value):
				self.assertEqual(self._save(kpi_targets=value), empty)
				self.assertEqual(self._stored(), good)
		self.assertEqual(self._save(kpi_targets="", coo_report_recipients="sai"), _email_error("sai"))
		self.assertEqual(self._stored(), good)
