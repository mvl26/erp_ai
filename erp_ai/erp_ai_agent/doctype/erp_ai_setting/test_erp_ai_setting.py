import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	SETTING_DOCTYPE,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_setting import erp_ai_setting
from erp_ai.test_utils import set_agent_settings

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
