import re
import time
import unicodedata

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import redact
from erp_ai.agent.tools import site_api
from erp_ai.test_utils import keep_agent_settings

MASK = "[đã che]"
FAKE_FRAPPE_KEY = "fakekey0000000a"
FAKE_FRAPPE_SECRET = "fakesecret00000"
FAKE_JWT = "eyJmYWtlIjoxfQ.eyJmYWtlIjoyfQ.ZmFrZXNpZ25hdHVyZQ"
_COUNTED_REPEAT = re.compile(r"\{(?:\d+|\d*,\d*)\}")


def _python_311_constructs(source: str) -> list[str]:
	"""Possessive quantifiers and atomic groups in a regex source: Python 3.10 `re` rejects both."""
	found = []
	index = 0
	after_quantifier = False
	while index < len(source):
		char = source[index]
		group_start = index > 0 and source[index - 1] == "(" and (index < 2 or source[index - 2] != "\\")
		if char == "\\":
			index += 2
			after_quantifier = False
			continue
		if char == "[":
			index += 1
			if source.startswith("^", index):
				index += 1
			if source.startswith("]", index):
				index += 1
			while index < len(source) and source[index] != "]":
				index += 2 if source[index] == "\\" else 1
			index += 1
			after_quantifier = False
			continue
		if source.startswith("(?>", index):
			found.append(f"(?> at {index}")
		if after_quantifier and char == "+":
			found.append(f"possessive at {index}")
			after_quantifier = False
		elif after_quantifier and char == "?":
			after_quantifier = False
		elif char in "*+?" and not group_start:
			after_quantifier = True
		elif counted := _COUNTED_REPEAT.match(source, index):
			index = counted.end()
			after_quantifier = True
			continue
		else:
			after_quantifier = False
		index += 1
	return found


def _module_patterns() -> list[re.Pattern]:
	patterns = []
	for value in vars(redact).values():
		for item in value if isinstance(value, tuple | list) else (value,):
			if isinstance(item, re.Pattern):
				patterns.append(item)
	return patterns


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
		# K-8: generous bound; a linear scan takes milliseconds here, a quadratic one about a minute
		# for 50,000 characters, so 10 seconds only fails on quadratic scanning.
		for text in (
			"a" * 100_000,
			"Q2hhb_-9" * 12_500,
			f"dữ liệu {'f0' * 50_000} hết",
			"pwd" * 33_334,
			"Token" * 20_000,
			"a " * 50_000 + ": x",
			"Mật khẩu " * 20_000,
		):
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
		# One row per line of table 3c (design-w0-fixes-3.md), labelled with the deciding criterion.
		rows = (
			(
				"N-6",
				True,
				(
					"api_key",
					"x_api_key",
					"api_secret",
					"access_token",
					"new_password",
					"reset_password_key",
					"smtp_pwd",
					"API_SECRET",
					"auth_token",
					*site_api.SECRET_FIELDS,
				),
			),
			("N-2a", True, ("apiKey", "accessToken", "clientSecret")),
			("N-2a digit", True, ("oauth2Token",)),
			("N-2b", True, ("DBPassword", "APIKey", "JWTToken")),
			("N-4", True, ("api-key", "smtp.password", "Secret Key")),
			("N-1 N-3", True, ("Mật khẩu", unicodedata.normalize("NFD", "Mật khẩu"), "MẬT KHẨU")),
			(
				"N-6 N-7",
				False,
				("input_tokens", "output_tokens", "max_tokens", "MAX_TOKENS", "tokenizer", "passwords"),
			),
			("N-6 adjacent", False, ("api_primary_key",)),
			(
				"N-4 N-6 N-7",
				False,
				("apikey", "primary_key", "subject", "description", "customer", "mat khau"),
			),
		)
		for criterion, expected, names in rows:
			for name in names:
				with self.subTest(criterion=criterion, name=name):
					self.assertIs(redact.is_secret_key(name), expected)

	def test_usage_counters_not_masked(self):
		self.assertEqual(
			redact.redact_secrets("input_tokens: 1200, output_tokens: 512, api_key=abc"),
			f"input_tokens: 1200, output_tokens: 512, api_key={MASK}",
		)

	def test_nfd_vietnamese_key_masked(self):
		text = unicodedata.normalize("NFD", "Mật khẩu: fake-value-nfd")
		self.assertEqual(redact.redact_secrets(text), f"Mật khẩu: {MASK}")

	def test_key_after_plain_key_value_masked(self):
		# A plain key's value can itself be "secret_key=value"; the scan must not swallow it.
		self.assertEqual(redact.redact_secrets("ghi chú: token=fake-a"), f"ghi chú: token={MASK}")
		self.assertEqual(
			redact.redact_secrets("subject: hello, Đặt Mật khẩu: fake-b"),
			f"subject: hello, Đặt Mật khẩu: {MASK}",
		)

	def test_key_value_rules(self):
		# K-2 (up to three runs), K-5 (no pair dropping), K-6. The two unchanged texts are the accepted
		# K-2 limit: the secret word is not among the last three runs before the separator.
		cases = (
			("token abc: fake-c", f"token abc: {MASK}"),
			("Secret Key: fake-x", f"Secret Key: {MASK}"),
			("password mới: fake-y", f"password mới: {MASK}"),
			("Mật khẩu mới: fake-m", f"Mật khẩu mới: {MASK}"),
			("Mật khẩu đăng nhập mới: fake-n", "Mật khẩu đăng nhập mới: fake-n"),
			("password cũ của anh: fake-z", "password cũ của anh: fake-z"),
			("pwd password=fake-d", f"pwd password={MASK}"),
			("ghi chú: token=fake-a", f"ghi chú: token={MASK}"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_value_patterns_run_before_key_scan(self):
		# R-3 before R-4; K-7 keeps a value already masked by R-3.
		cases = (
			("Authorization: token FAKEKEY:FAKESECRET", f"Authorization: token {MASK}"),
			("password=sk-ant-FAKE0000", f"password={MASK}"),
			('api_key: "sk-FAKE0000000000000000"', f'api_key: "{MASK}"'),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_secret_patterns_are_the_five_value_patterns(self):
		samples = (
			"khóa sk-ant-abc hết hạn",
			"khóa sk-FAKE000000000000000000 hết hạn",
			"Authorization: Bearer FAKEtoken00000000",
			f"Authorization: token {FAKE_FRAPPE_KEY}:{FAKE_FRAPPE_SECRET}",
			f"jwt {FAKE_JWT} cuối",
		)
		self.assertEqual(len(redact.SECRET_PATTERNS), 5)
		for index, sample in enumerate(samples):
			with self.subTest(sample=sample):
				matching = [i for i, pattern in enumerate(redact.SECRET_PATTERNS) if pattern.search(sample)]
				self.assertEqual(matching, [index])
		for pattern in redact.SECRET_PATTERNS:
			with self.subTest(pattern=pattern.pattern):
				self.assertIsNone(pattern.search("api_key=abc"))

	def test_output_is_nfc(self):
		text = unicodedata.normalize("NFD", "Mật khẩu đã đổi xong")
		result = redact.redact_secrets(text)
		self.assertEqual(result, unicodedata.normalize("NFC", text))
		self.assertTrue(unicodedata.is_normalized("NFC", result))

	def test_secret_key_without_value_untouched(self):
		self.assertEqual(redact.redact_secrets("api_key= , pwd=fake-e"), f"api_key= , pwd={MASK}")

	def test_single_quoted_value_masked(self):
		self.assertEqual(redact.redact_secrets("password='fake value 11'"), f"password='{MASK}'")

	def test_one_word_list_for_both_functions(self):
		for word in redact.SECRET_WORDS:
			with self.subTest(word=word):
				self.assertTrue(redact.is_secret_key(word))
				self.assertEqual(redact.redact_secrets(f"{word}=fake-value"), f"{word}={MASK}")

	def test_python_311_construct_check_catches_each_construct(self):
		for source in (r"a++", r"[\w-]*+b", r"\s?+", r"a{2}+", r"a{0,2}+", r"(?:ab){1,}+", r"(?>a|b)c"):
			with self.subTest(source=source):
				self.assertTrue(_python_311_constructs(source))
		for source in (
			r"a+b*c?",
			r"a+?b*?c??d{1,2}?",
			r"[+*?{}]+\++\*+\?+",
			r"(?:a)+(?P<x>b)*(?=c)?(?<!d)",
			r"\(?a\{2}+",
			r"[\]+]+x",
		):
			with self.subTest(source=source):
				self.assertEqual(_python_311_constructs(source), [])

	def test_every_pattern_is_python_310_syntax(self):
		# CI and `requires-python` start at 3.10, whose `re` has no possessive quantifier or atomic group.
		patterns = _module_patterns()
		self.assertIn(redact._KEY_CANDIDATE, patterns)
		self.assertIn(redact._KEY_VALUE, patterns)
		self.assertIn(redact._SEGMENT_SEPARATOR, patterns)
		for pattern in redact.SECRET_PATTERNS:
			self.assertIn(pattern, patterns)
		for pattern in patterns:
			with self.subTest(pattern=pattern.pattern):
				self.assertEqual(_python_311_constructs(pattern.pattern), [])
