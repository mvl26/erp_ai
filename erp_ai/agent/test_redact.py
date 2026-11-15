import itertools
import re
import time
import unicodedata
from unittest import mock

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


# K-8 text generators `(unit, head, tail)`: secret keys without a value, long separator runs, many
# `MASK`s, non-secret keys (design-w1-fixes-16.md section 4a).
_K8_GENERATORS = (
	("pwd=a|", "", ""),
	("password=abc|api_key:,", "", "hunter2"),
	("api_key: |", "", ""),
	("pwd= ", "", ""),
	("pwd=a|x ", "", ""),
	("&", "password=a", ""),
	(",;&|", "password=a", "x"),
	(" ", "pwd=a", "x"),
	("|", "password=a", "api_key: hunter2"),
	("a.", "password=", "api_key: z"),
	("password=sk-ant-A&", "", ""),
	("sk-ant-A.", "password=", ""),
	("pwd=a&sk-ant-X|", "", ""),
	("user=sk-ant-A&", "", ""),
	("user=a|", "", ""),
	("|user:", "password=", ""),
)


def _k8_text(unit: str, head: str, tail: str, size: int) -> str:
	return head + unit * ((size - len(head) - len(tail)) // len(unit)) + tail


class _CountingPattern:
	"""Wraps a compiled pattern and adds the characters each `match` reads to `counter[0]`."""

	def __init__(self, pattern: re.Pattern, counter: list[int]):
		self.pattern = pattern
		self.counter = counter

	def match(self, text: str, pos: int = 0):
		found = self.pattern.match(text, pos)
		if found:
			self.counter[0] += found.end() - pos
		return found


_PLANT_KEYS = (("api_key", True), ("my api key", True), ("user", False))
_PLANT_SEPARATORS = (",", ";", "&", "|", " ", "\n")


def _planted_items(index: int, keys=_PLANT_KEYS, key_separators=("=", ":", ": ")) -> list[tuple]:
	"""Items `(text, token, secret)` for one position; `token` is unique to the position and kind."""
	items = []
	for kind in ("empty", "bare", "quoted", "pattern"):
		token = None if kind == "empty" else f"zq{index}{kind[0]}"
		value = {"empty": "", "bare": token, "quoted": f'"{token}"', "pattern": f"sk-ant-{token}"}[kind]
		for key, secret in keys:
			for key_separator in key_separators:
				items.append((f"{key}{key_separator}{value}", token, secret and token is not None))
		items.append((value, token, False))
	return items


def _must_mask(text: str, planted: tuple) -> set[str]:
	"""Tokens that must not survive: secret by construction, inside a value pattern, or inside the K-4
	value of any key candidate with a secret name, looked for at every run start (not the code's scan)."""
	tokens = [token for _, token, _ in planted if token is not None]
	must = {token for _, token, secret in planted if secret}
	masked = text
	for pattern in redact.SECRET_PATTERNS:
		for found in pattern.finditer(masked):
			must.update(token for token in tokens if token in found.group())
		masked = pattern.sub(redact._mask_keep_prefix, masked)
	for word in re.finditer(r"(?<![\w-])[\w-]", masked):
		candidate = redact._KEY_CANDIDATE.match(masked, word.start())
		if candidate and redact.is_secret_key(candidate.group("name")):
			value = redact._KEY_VALUE.match(masked, candidate.end())
			if value:
				must.update(token for token in tokens if token in value.group())
	return must


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

	def test_pattern_masked_value_tail_masked(self):
		# K-7 as amended: after a secret key, the tail K-4 still counts as bare value goes with the MASK.
		cases = (
			("password=sk-ant-FAKE&tailFAKE", f"password={MASK}"),
			("password=sk-ant-FAKE&amp;tailFAKE", f"password={MASK}"),
			("password=sk-ant-FAKE.tailFAKE", f"password={MASK}"),
			("pwd=sk-FAKE0000000000000000+tailFAKE", f"pwd={MASK}"),
			("token=eyJa.eyJb.c2ln&tailFAKE", f"token={MASK}"),
			("password=sk-ant-FAKE,tailFAKE", f"password={MASK}"),
			("password=sk-ant-FAKE&tailFAKE;pwd=fake-z", f"password={MASK};pwd={MASK}"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				result = redact.redact_secrets(text)
				self.assertEqual(result, expected)
				self.assertNotIn("tailFAKE", result)

	def test_pattern_masked_value_tail_stops_like_bare_value(self):
		# The tail stops where a bare value stops (K-4 (a)-(c), `}`); a non-secret key keeps it (K-7).
		cases = (
			("password=sk-ant-FAKE&page=2", f"password={MASK}&page=2"),
			("password=sk-ant-FAKE, tiếp", f"password={MASK}, tiếp"),
			("password=sk-ant-FAKE;", f"password={MASK};"),
			("{password=sk-ant-FAKE}", f"{{password={MASK}}}"),
			("note=sk-ant-FAKE&tailFAKE", f"note={MASK}&tailFAKE"),
			("api_key=sk-ant-FAKE&pwd=fake-z", f"api_key={MASK}&pwd={MASK}"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_secret_key_inside_secret_value_masked_with_it(self):
		# K-4b: the masked span of a secret bare value only grows; a key candidate with a secret name
		# that runs past its end, and that key's value, are masked with it in one MASK.
		cases = (
			("password=sk-ant-FAKE|api_key: hunter2", f"password={MASK}"),
			("password=sk-ant-FAKE.pwd = hunter2", f"password={MASK}"),
			("password=sk-ant-FAKE&tailFAKE|api_key: hunter2", f"password={MASK}"),
			("password=sk-ant-FAKE|my api key: hunter2", f"password={MASK}"),
			("password=abc|api_key: hunter2", f"password={MASK}"),
			("password=api_key: hunter2", f"password={MASK}"),
			("password=abc|api_key:,hunter2", f"password={MASK}"),
			('password=abc|api_key:"hunter2" x', f"password={MASK} x"),
			("pwd=a|x pwd=b|y", f"pwd={MASK}"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				result = redact.redact_secrets(text)
				self.assertEqual(result, expected)
				self.assertNotIn("hunter2", result)

	def test_mask_inside_secret_value_masked_once(self):
		# K-4b, K-7: the span takes in every MASK that starts before its end, never `[đã che] che]`.
		cases = (
			("password=sk-ant-A&sk-ant-B", f"password={MASK}"),
			("password=sk-ant-FAKE&tailFAKE.sk-ant-B", f"password={MASK}"),
			("password=x&sk-ant-FAKE", f"password={MASK}"),
			("password=a|api_key: sk-ant-B&tailFAKE x", f"password={MASK} x"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				result = redact.redact_secrets(text)
				self.assertEqual(result, expected)
				self.assertEqual(result.count(MASK), 1)
				self.assertNotIn("che] che]", result)

	def test_secret_key_without_value_inside_value_keeps_rest(self):
		# Like `api_key= , pwd=x`: K-4 gives the inner secret key no value, so the span ends at the key.
		self.assertEqual(redact.redact_secrets("password=abc|api_key: ,hunter2"), f"password={MASK},hunter2")

	def test_value_reads_stay_linear(self):
		# K-8, deterministic: the characters `_KEY_VALUE` and `_BARE_VALUE_TAIL` read stay within the text.
		for unit, head, tail in _K8_GENERATORS:
			with self.subTest(unit=unit, head=head):
				text = _k8_text(unit, head, tail, 60 * 1024)
				counter = [0]
				with (
					mock.patch.object(redact, "_KEY_VALUE", _CountingPattern(redact._KEY_VALUE, counter)),
					mock.patch.object(
						redact, "_BARE_VALUE_TAIL", _CountingPattern(redact._BARE_VALUE_TAIL, counter)
					),
				):
					redact.redact_secrets(text)
				self.assertLessEqual(counter[0], len(text))

	def test_value_scan_time_at_240_kb(self):
		# K-8: generous bound like test_long_run_without_secret_untouched; linear takes under 0.2 s here.
		for unit, head, tail in _K8_GENERATORS:
			with self.subTest(unit=unit, head=head):
				text = _k8_text(unit, head, tail, 240 * 1024)
				started = time.monotonic()
				result = redact.redact_secrets(text)
				self.assertLess(time.monotonic() - started, 2)
				self.assertNotIn("hunter2", result)
				self.assertNotIn("che] che]", result)

	def test_no_planted_secret_survives(self):
		# NFR-6, systematic enumeration (design-w1-fixes-16.md section 4b, smaller sets).
		full = [_planted_items(i) for i in range(3)]
		small = [
			_planted_items(i, keys=(("api_key", True), ("user", False)), key_separators=("=", ": "))
			for i in range(3)
		]
		count = 0
		leaks = []
		for item_lists in (full[:1], full[:2], small):
			for combo in itertools.product(*item_lists):
				for separators in itertools.product(_PLANT_SEPARATORS, repeat=len(combo) - 1):
					text = combo[0][0] + "".join(
						separator + item[0] for separator, item in zip(separators, combo[1:], strict=True)
					)
					count += 1
					result = redact.redact_secrets(text)
					if any(token in result for token in _must_mask(text, combo)):
						leaks.append((text, result))
		self.assertEqual(count, 297_640)
		self.assertEqual(leaks[:3], [])

	def test_non_secret_key_inside_value_stays_value(self):
		# K-4b: a key candidate with a non-secret name inside a secret value stays part of the value.
		cases = (
			("password=sk-ant-FAKE|user:bob", f"password={MASK}"),
			("password=ab|user:bob", f"password={MASK}"),
			('password=sk-ant-FAKE|"api_key": "hunter2"', f'password={MASK}"api_key": "{MASK}"'),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				result = redact.redact_secrets(text)
				self.assertEqual(result, expected)
				self.assertNotIn("hunter2", result)

	def test_secret_value_cut_stays_linear(self):
		# K-8 with K-4b: same generous 10-second bound as test_long_run_without_secret_untouched.
		cases = (
			("password=" + "|user:" * 30_000, f"password={MASK}"),
			("pwd=a|x " * 25_000, f"pwd={MASK}"),
			("password=" + "a." * 50_000 + "api_key: z", f"password={MASK}"),
		)
		for text, prefix in cases:
			with self.subTest(length=len(text), prefix=prefix):
				started = time.monotonic()
				result = redact.redact_secrets(text)
				self.assertLess(time.monotonic() - started, 10)
				self.assertTrue(result.startswith(prefix))
				self.assertNotIn("a|x", result)
				self.assertNotIn("api_key: z", result)

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

	def test_list_separator_inside_bare_value_masked(self):
		# K-4: `,` `;` `&` not followed by end of text, whitespace or a key candidate belong to the value.
		cases = (
			("password=ab&cd", f"password={MASK}"),
			("password=ab&amp;cd", f"password={MASK}"),
			("pwd=ab;cd", f"pwd={MASK}"),
			("pwd=ab,cd", f"pwd={MASK}"),
			("password=ab&cd tiếp", f"password={MASK} tiếp"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_list_separator_before_next_key_ends_value(self):
		# K-4 (a)-(c): the separator ends the value before end of text, whitespace or the next key.
		cases = (
			("token=abc&page=2", f"token={MASK}&page=2"),
			("api_key=x;pwd=y", f"api_key={MASK};pwd={MASK}"),
			("password=abc;", f"password={MASK};"),
			("password=abc, tiếp", f"password={MASK}, tiếp"),
			("api_key= , pwd=x", f"api_key= , pwd={MASK}"),
			# (c) covers keys of two and three runs, `:` as well as `=`, and the quote and space before it.
			("pwd=ab;api key: fake-z", f"pwd={MASK};api key: {MASK}"),
			("pwd=ab;user:bob", f"pwd={MASK};user:bob"),
			("pwd=ab;user :x", f"pwd={MASK};user :x"),
			('token=abc&page"=2', f'token={MASK}&page"=2'),
			("pwd=ab;my api key: fake-q", f"pwd={MASK};my api key: {MASK}"),
			("pwd=ab&page no 2=x", f"pwd={MASK}&page no 2=x"),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

	def test_list_separator_before_closing_mark_stays_in_value(self):
		# K-4: a separator followed by `"` `}` `]` is none of (a)-(c), so it belongs to the value.
		cases = (
			("{pwd=ab;}", f"{{pwd={MASK}}}"),
			("[pwd=ab,]", f"[pwd={MASK}]"),
			('x="pwd=ab&"', f'x="pwd={MASK}"'),
		)
		for text, expected in cases:
			with self.subTest(text=text):
				self.assertEqual(redact.redact_secrets(text), expected)

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
