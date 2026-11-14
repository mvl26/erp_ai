import time

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import redact
from erp_ai.agent.tools import site_api
from erp_ai.test_utils import keep_agent_settings

MASK = "[đã che]"
FAKE_FRAPPE_KEY = "fakekey0000000a"
FAKE_FRAPPE_SECRET = "fakesecret00000"
FAKE_JWT = "eyJmYWtlIjoxfQ.eyJmYWtlIjoyfQ.ZmFrZXNpZ25hdHVyZQ"


class TestRedact(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_each_pattern(self):
		cases = (
			("khóa sk-ant-FAKE0000000000000000 hết hạn", "khóa [đã che] hết hạn"),
			("khóa sk-ant-abc hết hạn", "khóa [đã che] hết hạn"),
			("khóa sk-FAKE000000000000000000 hết hạn", "khóa [đã che] hết hạn"),
			("khóa sk-FAKE000000000000 hết hạn", "khóa [đã che] hết hạn"),
			("Authorization: Bearer FAKEtoken00000000", "Authorization: Bearer [đã che]"),
			(
				f"Authorization: token {FAKE_FRAPPE_KEY}:{FAKE_FRAPPE_SECRET}",
				"Authorization: token [đã che]",
			),
			(f"jwt {FAKE_JWT} cuối", "jwt [đã che] cuối"),
			("api_key=fake-value-1", "api_key=[đã che]"),
			("api_secret: fake-value-2", "api_secret: [đã che]"),
			("token=fake-value-3", "token=[đã che]"),
			("client_secret = fake-value-4", "client_secret = [đã che]"),
			("PASSWORD=fake-value-5", "PASSWORD=[đã che]"),
			("passwd: fake-value-6", "passwd: [đã che]"),
			("pwd=fake-value-7", "pwd=[đã che]"),
			("Mật khẩu: fake-value-8", "Mật khẩu: [đã che]"),
			("new_password=fake-value-9", "new_password=[đã che]"),
			('{"api_key": "fake value 10"}', '{"api_key": "[đã che]"}'),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_short_sk_prefix_untouched(self):
		self.assertEqual(redact.redact_secrets("mã sk-12345 của kho"), "mã sk-12345 của kho")
		self.assertEqual(
			redact.redact_secrets("mã sk-FAKE00000000000 của kho"), "mã sk-FAKE00000000000 của kho"
		)

	def test_long_run_without_secret_untouched(self):
		# Generous bound: the anchored scan takes milliseconds here; the unanchored regex took
		# about a minute for 50,000 characters, so 10 seconds only fails on quadratic scanning.
		for text in ("a" * 100_000, "Q2hhb_-9" * 12_500, f"dữ liệu {'f0' * 50_000} hết"):
			with self.subTest(length=len(text)):
				started = time.monotonic()
				self.assertEqual(redact.redact_secrets(text), text)
				self.assertLess(time.monotonic() - started, 10)

	def test_plain_text_untouched(self):
		for text in (
			"Khách báo lỗi không đăng nhập được, cần đặt lại mật khẩu cho tài khoản.",
			"Token hết hạn, vui lòng đăng nhập lại.",
			"The secret to success is a clear password policy.",
			"Phiếu HD-0001: đổi nhóm hàng cho mã 1200-A.",
			"",
		):
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), text)

	def test_none_and_empty(self):
		self.assertEqual(redact.redact_secrets(None), "")
		self.assertEqual(redact.redact_secrets(""), "")

	def test_several_secrets_in_one_text(self):
		text = f"api_key=fake-a, Bearer FAKEtoken00000000 và {FAKE_JWT}; pwd=fake-b"
		self.assertEqual(
			redact.redact_secrets(text),
			"api_key=[đã che], Bearer [đã che] và [đã che]; pwd=[đã che]",
		)

	def test_secret_at_start_and_end(self):
		self.assertEqual(redact.redact_secrets("sk-FAKE000000000000000000"), MASK)
		self.assertEqual(redact.redact_secrets("sk-FAKE000000000000000000 ở đầu"), f"{MASK} ở đầu")
		self.assertEqual(redact.redact_secrets("ở cuối password=fake-end"), f"ở cuối password={MASK}")

	def test_is_secret_key_names(self):
		for name in (
			"api_key",
			"new_password",
			"Mật khẩu",
			"API_SECRET",
			"auth_token",
			*site_api.SECRET_FIELDS,
		):
			with self.subTest(name=name):
				self.assertTrue(redact.is_secret_key(name))
		for name in ("subject", "description", "customer"):
			with self.subTest(name=name):
				self.assertFalse(redact.is_secret_key(name))

	def test_one_word_list_for_both_functions(self):
		for word in redact.SECRET_WORDS:
			with self.subTest(word=word):
				self.assertTrue(redact.is_secret_key(word))
				self.assertEqual(redact.redact_secrets(f"{word}=fake-value"), f"{word}={MASK}")
