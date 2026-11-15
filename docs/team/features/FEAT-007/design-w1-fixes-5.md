# FEAT-007 — design-w1-fixes-5: làm lại điểm 3 của `design-w1-fixes-2.md` (đuôi K-7 nuốt khóa kế tiếp, `[đã che] che]`)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu; không chặn build (READY build 66/174). Thay phần "Phán quyết", "Touchpoints" và "Khối task mới" của `design-w1-fixes-2.md` điểm 3 (dòng 90-119). Phần "Lần theo đường mã" ở đó (dòng 81-88) vẫn đúng; câu "Ngoài phạm vi" ở dòng 101 được giải luôn ở đây (ca R3b).
- Đầu vào: `review-174.md:16-41`; `design-w1-fixes-2.md:79-125`; `design-w0-fixes-4.md` điểm 3 (K-4, K-4a); `tasks.md` dòng T174 (613-618).
- Mã: `git show team/FEAT-007:erp_ai/agent/redact.py` (@ `ce696e1`, trước T174) và `git show team/FEAT-007-task-174:erp_ai/agent/redact.py` (@ `d1e89f3`, chưa review xong). Module chỉ dùng `re`, `unicodedata`.
- Không đổi kiến trúc: ADR-034 QĐ 2 (một hàm che dùng chung, sửa ở một chỗ là `redact.py`). Không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, không đổi regex `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`.
- **Lần này đã chạy thật**, không chỉ đọc: `python3 -I` qua stdin, chỉ thư viện chuẩn, nạp chữ module bằng `git show` rồi `exec`; bản "đề xuất" là chữ của `d1e89f3` cộng đúng đoạn mã ở mục "Mã đề xuất". Không `bench`, không site, không ghi file nào khác.

---

## Hai lỗi đã đo (xác nhận `review-174.md:28-29`)

Chạy thật trên `d1e89f3` (cột thứ ba của bảng):
- `password=sk-ant-FAKE|api_key: hunter2` → `'password=[đã che] hunter2'` (lộ `hunter2`; `ce696e1` cho `'password=[đã che]|api_key: [đã che]'`).
- `password=sk-ant-A&sk-ant-B` → `'password=[đã che] che]'` (`ce696e1` cho `'password=[đã che]&[đã che]'`).

Nguyên nhân: cụm `[^\s,;&"'}\]]+` của đuôi (cũng là của nhánh trần K-4) đi qua cả tên khóa kế tiếp và cả `[đã` của một `MASK` khác. Nhánh trần K-4 (không qua R-3) có cùng hai lỗi, đo được trên cả `ce696e1` lẫn `d1e89f3`: `password=abc|api_key: hunter2` → `'password=[đã che] hunter2'`, `password=api_key: hunter2` → `'password=[đã che] hunter2'`, `password=x&sk-ant-FAKE` → `'password=[đã che] che]'`.

## Phán quyết

**Chọn phương án (b) của `review-174.md:28`: một luật cắt dùng chung (K-4b) cho giá trị trần của khóa bí mật (K-4) và cho đuôi K-7.** Làm bằng Python sau phép khớp regex (`_KEY_VALUE`, `_BARE_VALUE_TAIL` giữ nguyên), vì điều kiện cắt cần `is_secret_key`, regex không làm được. Không chọn (a) vì (a) để `hunter2` lộ, trái NFR-6, trong khi sửa chỉ tốn một hàm riêng tư ở đúng một chỗ.

Thêm vào `design-w0-fixes-3.md` mục 3 (sau K-4a của `design-w0-fixes-4.md` điểm 3):

> - **K-4b (cắt giá trị bí mật).** Khi tên là bí mật (K-5), phần K-4 đọc được làm giá trị trần, hoặc phần đuôi của K-7, **dừng sớm** ở điểm đầu tiên bên trong nó là (1) đầu một `MASK`, hoặc (2) đầu một ứng viên khóa K-1..K-3 (bắt đầu ở chỗ ký tự trước nó không thuộc `[\w-]`) mà tên là bí mật theo `is_secret_key`. Điểm dừng lùi lại qua các ký tự không thuộc `[\w-]` đứng ngay trước nó; các ký tự đó giữ nguyên trong văn bản. Không có điểm dừng → giữ nguyên độ dài K-4 đọc được. Giá trị trần bị cắt còn rỗng → không che ở ứng viên này, quét tiếp ngay sau ứng viên (như "không có giá trị" của K-4). Ứng viên khóa tên **không** bí mật bên trong giá trị vẫn là một phần của giá trị (như K-4 nay). Giá trị trong nháy không áp K-4b.

Thay K-7 (`design-w0-fixes-3.md:167`, bản của `design-w1-fixes-2.md:95`) bằng:

> - **K-7.** Giá trị trần bắt đầu bằng `MASK` (đã che ở R-3) → giữ đúng một `MASK`, không che lần hai. Nếu tên là bí mật (K-5): phần đuôi ngay sau `MASK` mà K-4 còn coi là thuộc giá trị trần (các cụm ký tự không phải khoảng trắng và không thuộc `, ; & " ' } ]`, cùng các dấu `, ; &` không thỏa (a), (b), (c) của K-4), **cắt theo K-4b**, bị bỏ; quét tiếp ngay sau phần đuôi đã cắt. Nhờ K-4b, đuôi không bao giờ chứa tên một khóa bí mật hay một `MASK` khác, nên không thành `[đã che] che]` và không nuốt khóa kế tiếp. Tên không bí mật → giữ nguyên `MASK` và phần sau nó, quét tiếp ngay sau `MASK` (như cũ). K-8 giữ: mỗi ký tự trong khoảng được đọc một số lần có chặn (đo ở bảng K-8).

Sửa K-4a (`design-w0-fixes-4.md:25`), thêm một câu cuối trước "Thêm vào As-Built":

> Thêm (K-4b): mật khẩu trần chứa, sau một ký tự không thuộc `[\w-]`, dạng khóa có tên bí mật hoặc chuỗi `[đã che]`, bị cắt ở đó: các ký tự không thuộc `[\w-]` ngay trước chỗ cắt lộ ra; phần sau do khóa bí mật đó che nếu nó có giá trị. Đuôi K-7 có thể bỏ một dấu câu đứng ngay trước một nháy (`password=sk-ant-FAKE|"api_key": …` → `password=[đã che]"api_key": …`, ca R1e), không lộ bí mật.

As-Built (writer): đoạn K-4a ghi thêm câu trên. Phương án (a) không dùng, nên không cần ghi ca `password=abc|api_key: hunter2` là giới hạn; ca đó nay được che (R3).

## Mã đề xuất (đã chạy đúng đoạn này)

Thêm vào `erp_ai/agent/redact.py`, ngay trước `def _mask_key_values` (tên riêng tư, không tên công khai mới):

```python
_WORD_START = re.compile(r"(?<![\w-])[\w-]")
_NOT_WORD_CHAR = re.compile(r"[^\w-]")


def _secret_value_end(text: str, start: int, end: int) -> int:
	"""K-4b: end of the secret bare value or K-7 tail read over `text[start:end]`.

	Stops at the first `MASK` or key candidate with a secret name inside it, less the non-word
	characters just before that point; otherwise `end`.
	"""
	stop = text.find(MASK, start, end + len(MASK) - 1)
	stop = end if stop == -1 else stop
	for word in _WORD_START.finditer(text, start, stop):
		candidate = _KEY_CANDIDATE.match(text, word.start())
		if candidate and is_secret_key(candidate.group("name")):
			stop = word.start()
			break
	if stop == end:
		return end
	while stop > start and _NOT_WORD_CHAR.match(text, stop - 1):
		stop -= 1
	return stop
```

Trong `_mask_key_values`, thay phần từ nhánh `MASK` đến cuối thân vòng lặp bằng:

```python
		if text.startswith(MASK, position):
			parts.append(MASK)
			position += len(MASK)
			if is_secret_key(candidate.group("name")):
				position = _secret_value_end(text, position, _BARE_VALUE_TAIL.match(text, position).end())
			continue
		value = _KEY_VALUE.match(text, position)
		if value is None or not is_secret_key(candidate.group("name")):
			continue
		if value.group("double") is not None:
			parts.append(f'"{MASK}"')
			position = value.end()
		elif value.group("single") is not None:
			parts.append(f"'{MASK}'")
			position = value.end()
		elif (end := _secret_value_end(text, position, value.end())) > position:
			parts.append(MASK)
			position = end
```

Ghi chú đã kiểm khi chạy: (1) `re` của Python cho phép nhìn sau đọc ký tự trước `pos` (`re.compile(r"(?<![\w-])[\w-]").match("ab", 1)` → `None`), nên `_WORD_START.finditer(text, start, stop)` và `_KEY_CANDIDATE.match(text, p)` thấy đúng ký tự đứng trước. (2) `text.find(MASK, start, end + len(MASK) - 1)` chỉ trả chỉ số `< end` và có chặn, không quét hết văn bản. (3) Docstring không được viết `\w` trong chuỗi thường (lần chạy đầu của bản nháp ra `SyntaxWarning: invalid escape sequence '\w'`); bản trên đã bỏ. (4) Hai mẫu mới là `re.Pattern` cấp module, nên tự nằm trong `test_every_pattern_is_python_310_syntax`; lần chạy cả lớp `TestRedact` trên bản đề xuất xanh, gồm test đó.

## Bảng ca, đã chạy thật

Mọi dòng dưới đây **đã chạy**; ô là `repr` của `redact_secrets(đầu vào)` chép nguyên văn từ đầu ra. Cột: `ce696e1` = `team/FEAT-007` (trước T174); `d1e89f3` = `team/FEAT-007-task-174`; "đề xuất" = `d1e89f3` + mã ở trên. `M` = `[đã che]` (chỉ viết tắt trong bảng này; đầu ra thật in đủ chữ). Dấu `\|` là ký tự `|` trong đầu vào.

### Hai ca của review và ca cùng họ

| Ca | Đầu vào | `ce696e1` | `d1e89f3` | đề xuất |
|---|---|---|---|---|
| R1 | `password=sk-ant-FAKE\|api_key: hunter2` | `password=M\|api_key: M` | `password=M hunter2` | `password=M\|api_key: M` |
| R1b | `password=sk-ant-FAKE.pwd = hunter2` | `password=M.pwd = M` | `password=M = hunter2` | `password=M.pwd = M` |
| R1c | `password=sk-ant-FAKE&tailFAKE\|api_key: hunter2` | `password=M&tailFAKE\|api_key: M` | `password=M hunter2` | `password=M\|api_key: M` |
| R1d | `password=sk-ant-FAKE\|my api key: hunter2` | `password=M\|my api key: M` | `password=M api key: M` | `password=M\|my api key: M` |
| R1e | `password=sk-ant-FAKE\|"api_key": "hunter2"` | `password=M\|"api_key": "M"` | `password=M"api_key": "M"` | `password=M"api_key": "M"` |
| R2 | `password=sk-ant-A&sk-ant-B` | `password=M&M` | `password=M che]` | `password=M&M` |
| R2b | `password=sk-ant-FAKE&tailFAKE.sk-ant-B` | `password=M&tailFAKE.M` | `password=M che]` | `password=M.M` |
| R3 | `password=abc\|api_key: hunter2` | `password=M hunter2` | `password=M hunter2` | `password=M\|api_key: M` |
| R3b | `password=x&sk-ant-FAKE` | `password=M che]` | `password=M che]` | `password=M&M` |
| R3c | `password=api_key: hunter2` | `password=M hunter2` | `password=M hunter2` | `password=api_key: M` |
| N1 | `password=sk-ant-FAKE\|user:bob` | `password=M\|user:bob` | `password=M` | `password=M` |
| N2 | `password=ab\|user:bob` | `password=M` | `password=M` | `password=M` |
| N3 | `password=sk-ant-FAKE.tailFAKE!` | `password=M.tailFAKE!` | `password=M` | `password=M` |

### Năm ca đỏ của Expect T174 và hai ca dev thêm (`test_pattern_masked_value_tail_masked`)

| Ca | Đầu vào | `ce696e1` | `d1e89f3` | đề xuất |
|---|---|---|---|---|
| E1 | `password=sk-ant-FAKE&tailFAKE` | `password=M&tailFAKE` | `password=M` | `password=M` |
| E2 | `password=sk-ant-FAKE&amp;tailFAKE` | `password=M&amp;tailFAKE` | `password=M` | `password=M` |
| E3 | `password=sk-ant-FAKE.tailFAKE` | `password=M.tailFAKE` | `password=M` | `password=M` |
| E4 | `pwd=sk-FAKE0000000000000000+tailFAKE` | `pwd=M+tailFAKE` | `pwd=M` | `pwd=M` |
| E5 | `token=eyJa.eyJb.c2ln&tailFAKE` | `token=M&tailFAKE` | `token=M` | `token=M` |
| E6 | `password=sk-ant-FAKE,tailFAKE` | `password=M,tailFAKE` | `password=M` | `password=M` |
| E7 | `password=sk-ant-FAKE&tailFAKE;pwd=fake-z` | `password=M&tailFAKE;pwd=M` | `password=M;pwd=M` | `password=M;pwd=M` |

### Sáu ca ghim của T174 (`test_pattern_masked_value_tail_stops_like_bare_value`)

| Ca | Đầu vào | `ce696e1` | `d1e89f3` | đề xuất |
|---|---|---|---|---|
| P1 | `password=sk-ant-FAKE&page=2` | `password=M&page=2` | `password=M&page=2` | `password=M&page=2` |
| P2 | `password=sk-ant-FAKE, tiếp` | `password=M, tiếp` | `password=M, tiếp` | `password=M, tiếp` |
| P3 | `password=sk-ant-FAKE;` | `password=M;` | `password=M;` | `password=M;` |
| P4 | `{password=sk-ant-FAKE}` | `{password=M}` | `{password=M}` | `{password=M}` |
| P5 | `note=sk-ant-FAKE&tailFAKE` | `note=M&tailFAKE` | `note=M&tailFAKE` | `note=M&tailFAKE` |
| P6 | `api_key=sk-ant-FAKE&pwd=fake-z` | `api_key=M&pwd=M` | `api_key=M&pwd=M` | `api_key=M&pwd=M` |

### Ca K-4/K-4a của `test_redact.py` không được đổi (cùng một số ca K-4a theo chữ của luật)

| Ca | Đầu vào | `ce696e1` | `d1e89f3` | đề xuất |
|---|---|---|---|---|
| K1 | `password=sk-ant-FAKE0000` | `password=M` | `password=M` | `password=M` |
| K2 | `api_key: "sk-FAKE0000000000000000"` | `api_key: "M"` | `api_key: "M"` | `api_key: "M"` |
| K3 | `Authorization: token FAKEKEY:FAKESECRET` | `Authorization: token M` | `Authorization: token M` | `Authorization: token M` |
| K4 | `password=ab&cd` | `password=M` | `password=M` | `password=M` |
| K5 | `password=ab&amp;cd` | `password=M` | `password=M` | `password=M` |
| K6 | `pwd=ab;cd` | `pwd=M` | `pwd=M` | `pwd=M` |
| K7 | `pwd=ab,cd` | `pwd=M` | `pwd=M` | `pwd=M` |
| K8 | `password=ab&cd tiếp` | `password=M tiếp` | `password=M tiếp` | `password=M tiếp` |
| K9 | `token=abc&page=2` | `token=M&page=2` | `token=M&page=2` | `token=M&page=2` |
| K10 | `api_key=x;pwd=y` | `api_key=M;pwd=M` | `api_key=M;pwd=M` | `api_key=M;pwd=M` |
| K11 | `password=abc;` | `password=M;` | `password=M;` | `password=M;` |
| K12 | `password=abc, tiếp` | `password=M, tiếp` | `password=M, tiếp` | `password=M, tiếp` |
| K13 | `api_key= , pwd=x` | `api_key= , pwd=M` | `api_key= , pwd=M` | `api_key= , pwd=M` |
| K14 | `pwd=ab;api key: fake-z` | `pwd=M;api key: M` | `pwd=M;api key: M` | `pwd=M;api key: M` |
| K15 | `pwd=ab;user:bob` | `pwd=M;user:bob` | `pwd=M;user:bob` | `pwd=M;user:bob` |
| K16 | `pwd=ab;user :x` | `pwd=M;user :x` | `pwd=M;user :x` | `pwd=M;user :x` |
| K17 | `token=abc&page"=2` | `token=M&page"=2` | `token=M&page"=2` | `token=M&page"=2` |
| K18 | `pwd=ab;my api key: fake-q` | `pwd=M;my api key: M` | `pwd=M;my api key: M` | `pwd=M;my api key: M` |
| K19 | `pwd=ab&page no 2=x` | `pwd=M&page no 2=x` | `pwd=M&page no 2=x` | `pwd=M&page no 2=x` |
| K20 | `{pwd=ab;}` | `{pwd=M}` | `{pwd=M}` | `{pwd=M}` |
| K21 | `[pwd=ab,]` | `[pwd=M]` | `[pwd=M]` | `[pwd=M]` |
| K22 | `x="pwd=ab&"` | `x="pwd=M"` | `x="pwd=M"` | `x="pwd=M"` |
| K23 | `password='fake value 11'` | `password='M'` | `password='M'` | `password='M'` |
| K24 | `pwd password=fake-d` | `pwd password=M` | `pwd password=M` | `pwd password=M` |
| K25 | `ghi chú: token=fake-a` | `ghi chú: token=M` | `ghi chú: token=M` | `ghi chú: token=M` |
| A1 (K-4a) | `password=ab&page=cd` | `password=M&page=cd` | `password=M&page=cd` | `password=M&page=cd` |
| A2 (K-4a) | `password=ab cd` | `password=M cd` | `password=M cd` | `password=M cd` |
| A3 (K-4a) | `password=ab"cd` | `password=M"cd` | `password=M"cd` | `password=M"cd` |
| A4 (K-4a) | `password=ab}cd` | `password=M}cd` | `password=M}cd` | `password=M}cd` |

Đổi so với `d1e89f3`: chỉ R1, R1b, R1c, R1d, R2, R2b, R3, R3b, R3c (cả chín đều theo hướng che đủ hơn hoặc bỏ `che] che]`). Mọi ca E, P, K, A, N giữ nguyên.

### Cả lớp `TestRedact` của `test_redact.py` @ `d1e89f3` (frappe thay bằng `unittest.TestCase`, `site_api.SECRET_FIELDS` chép từ `site_api.py:33`, `keep_agent_settings` không làm gì)

```
[ce696e1] test_redact.TestRedact @ d1e89f3 test file: ran=25 failures=7 errors=0 failing=[... 'test_pattern_masked_value_tail_masked']
[d1e89f3] test_redact.TestRedact @ d1e89f3 test file: ran=25 failures=0 errors=0 failing=[]
[proposed] test_redact.TestRedact @ d1e89f3 test file: ran=25 failures=0 errors=0 failing=[]
```

### Bốn test mới của Expect dưới đây, chạy đúng chữ của các ca

```
[d1e89f3] ran=4 failures=9 errors=0      (6 subtest của ::test_value_stops_before_next_secret_key, 3 của ::test_value_stops_before_mask)
[proposed] ran=4 failures=0 errors=0
```

### K-8 (thời gian, giây, một lần chạy)

```
password= + 'a.b'*50000                    | len=150009 | d1e89f3=0.010s | proposed=0.028s
password=sk-ant-X + '.x'*50000             | len=100017 | d1e89f3=0.008s | proposed=0.025s
password= + '.user'*30000 + ':x'           | len=150011 | d1e89f3=0.009s | proposed=0.021s
password= + '|user:'*30000                 | len=180009 | d1e89f3=0.012s | proposed=0.104s
'password=sk-ant-A&b.c ' * 20000           | len=440000 | d1e89f3=0.102s | proposed=0.216s
'pwd=a|x ' * 25000                         | len=200000 | d1e89f3=0.096s | proposed=0.252s
password= + 'a.'*50000 + 'api_key: z'      | len=100019 | d1e89f3=0.007s | proposed=0.024s
```

Tuyến tính (khoảng 2-9 lần hằng số so với `d1e89f3`, xa ngưỡng 10 s của test K-8).

**Chưa chạy:** `erp_ai/agent/test_knowledge.py` (cần frappe/site; dev chạy bằng `cmd.test_one`); `cmd.lint`/định dạng của đoạn mã đề xuất.

---

## Touchpoints

| File | Đổi |
|---|---|
| `erp_ai/agent/redact.py` | Thêm `_WORD_START`, `_NOT_WORD_CHAR`, `_secret_value_end` (riêng tư) ngay trước `_mask_key_values`; trong `_mask_key_values` đổi nhánh `MASK` và nhánh trần đúng như "Mã đề xuất"; docstring module: "K-4b added and K-7 as amended by `design-w1-fixes-5.md`" thay cho "K-7 as amended by `design-w1-fixes-2.md` point 3". |
| `erp_ai/agent/test_redact.py` | Bốn test mới trong `TestRedact`; không sửa test nào đã có. |

Không đường mới (hai file đã có trong `files:` của T120 và T174); so với `protected_paths`: không file nào thuộc. Không đổi chữ ký công khai, không mã lỗi mới, không migration.

## Nhánh: dev làm tiếp trên `team/FEAT-007-task-174` @ `d1e89f3`, không làm lại

Lý do (đã đo): bản đề xuất = chữ của `d1e89f3` + một hàm và một đoạn thay trong `_mask_key_values`; `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`, docstring và hai test của `7c11873` giữ nguyên và vẫn xanh (25/25). Dev thêm hai commit mới lên nhánh: `test(redact): …` (bốn test mới, chạy đỏ: đúng 9 subtest của hai test đầu, dán đầu ra không lọc) rồi `fix(redact): …` (mã). BASE của vòng review kế: `ce696e161d9d9a208ae2e4d46d6c4598b819d61c` (review cả bốn commit). Vòng này là vòng 2 trong trần `max_rework` = 3.

## Dòng task T174 (tech-lead chép, thay ba dòng Tiêu chí / Returns / Expect của T174 trong `tasks.md`; Receives không đổi, `progress:` giữ và nối tiếp)

```
  - Tiêu chí: NFR-6, AC-46, AC-50; ADR-034 QĐ 2; `review-120.md:45`; `review-174.md:28-29`; `design-w1-fixes-5.md` (K-4b mới, K-7 thay bản của `design-w1-fixes-2.md:95`, K-4a thêm một câu). Làm tiếp trên `team/FEAT-007-task-174` @ `d1e89f3`, không làm lại. Chỉ sửa `_mask_key_values` và thêm `_WORD_START`, `_NOT_WORD_CHAR`, `_secret_value_end`; không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, regex `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`.
  - Returns: không tên công khai mới. Giữ phần `d1e89f3` (`_BARE_VALUE_STEP` dùng chung cho `_KEY_VALUE` và `_BARE_VALUE_TAIL`). Thêm riêng tư `_WORD_START = re.compile(r"(?<![\w-])[\w-]")`, `_NOT_WORD_CHAR = re.compile(r"[^\w-]")` và `_secret_value_end(text: str, start: int, end: int) -> int` đúng chữ ở `design-w1-fixes-5.md` mục "Mã đề xuất" (điểm dừng = `MASK` đầu tiên bắt đầu trước `end`, hoặc đầu ứng viên `_KEY_CANDIDATE.match` đầu tiên ở một `_WORD_START` trong khoảng có `is_secret_key(name)`; lùi qua ký tự `_NOT_WORD_CHAR` nhưng không qua `start`; không có điểm dừng → `end`; docstring không viết `\w` trong chuỗi thường). Trong `_mask_key_values`: nhánh `MASK` với tên bí mật đặt `position = _secret_value_end(text, position, _BARE_VALUE_TAIL.match(text, position).end())`; nhánh trần với tên bí mật: `end = _secret_value_end(text, position, value.end())`, `end > position` → thêm `MASK`, `position = end`; `end == position` → không thêm gì, quét tiếp từ cuối ứng viên. Nhánh nháy kép, nháy đơn, tên không bí mật: như cũ.
  - Expect: bốn test mới trong `TestRedact`: `::test_value_stops_before_next_secret_key` (`password=sk-ant-FAKE|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=sk-ant-FAKE.pwd = hunter2` → `password={MASK}.pwd = {MASK}`; `password=sk-ant-FAKE&tailFAKE|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=sk-ant-FAKE|my api key: hunter2` → `password={MASK}|my api key: {MASK}`; `password=abc|api_key: hunter2` → `password={MASK}|api_key: {MASK}`; `password=api_key: hunter2` → `password=api_key: {MASK}`; mỗi ca kiểm thêm `"hunter2" not in` kết quả) và `::test_value_stops_before_mask` (`password=sk-ant-A&sk-ant-B` → `password={MASK}&{MASK}`; `password=sk-ant-FAKE&tailFAKE.sk-ant-B` → `password={MASK}.{MASK}`; `password=x&sk-ant-FAKE` → `password={MASK}&{MASK}`; mỗi ca kiểm thêm `"che] che]" not in`) đỏ trước trên `d1e89f3` (đúng 9 subtest, đầu ra không lọc qua `grep`/`tail`) rồi xanh; `::test_non_secret_key_inside_value_stays_value` (test ghim, xanh ngay là đúng, ghi lý do trong progress: `password=sk-ant-FAKE|user:bob` → `password={MASK}`; `password=ab|user:bob` → `password={MASK}`; `password=sk-ant-FAKE|"api_key": "hunter2"` → `password={MASK}"api_key": "{MASK}"`) và `::test_secret_value_cut_stays_linear` (test ghim K-8: `"password=" + "|user:" * 30_000`, `"pwd=a|x " * 25_000`, `"password=" + "a." * 50_000 + "api_key: z"`; mỗi ca dưới 10 s, kết quả bắt đầu bằng `password={MASK}` hoặc `pwd={MASK}`, không chứa `a|x`, không chứa `api_key: z`); `test_pattern_masked_value_tail_masked` (7 ca) và `test_pattern_masked_value_tail_stops_like_bare_value` (6 ca) của `7c11873` giữ xanh, không đổi khẳng định; mọi test `TestRedact` cũ giữ xanh, gồm `test_value_patterns_run_before_key_scan`, `test_list_separator_*`, `test_key_value_rules`, `test_long_run_without_secret_untouched`, `test_every_pattern_is_python_310_syntax`. `cmd.test_one` xanh cho `erp_ai/agent/test_redact.py` và `erp_ai/agent/test_knowledge.py`.
```

Ghi cho reviewer vòng 2: các ca của bốn test mới đã được designer chạy thật trên `d1e89f3` và trên bản đề xuất (mục "Bảng ca"); reviewer so mã của dev với "Mã đề xuất" và so đầu ra RED của dev với "9 subtest".

## Tóm tắt

| Điểm | Phán | File mã | Task | Căn cứ |
|---|---|---|---|---|
| 3 (làm lại) | K-4b mới: giá trị trần bí mật và đuôi K-7 dừng trước `MASK` kế hoặc trước khóa bí mật kế (lùi qua dấu câu); K-7 cắt theo K-4b; K-4a thêm một câu | `redact.py`, `test_redact.py` | T174 (làm tiếp trên nhánh @ `d1e89f3`) | NFR-6, ADR-034 QĐ 2, `review-174.md:28-29`; bảng ca đã chạy |
