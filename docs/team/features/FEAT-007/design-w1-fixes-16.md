# FEAT-007 — design-w1-fixes-16: phán lần ba luật che giá trị bí mật của T174 (K-4b chậm O(n²) và lộ chữ sau khóa bí mật không giá trị)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu; không chặn build (READY build 79/174). **Thay** luật K-4b, câu K-7, câu thêm của K-4a, mục "Mã đề xuất" và ba dòng Tiêu chí / Returns / Expect của T174 trong `design-w1-fixes-5.md`. Phần "Hai lỗi đã đo" của `design-w1-fixes-5.md` vẫn đúng.
- Đầu vào: `tasks.md` dòng T174 (662-667, gồm `progress:` round 100); `design-w1-fixes-5.md`; `review-174.md`; `docs/team/adr/ADR-034.md` QĐ 2; K-8 (`design-w0-fixes-3.md:168`, `design-w0-fixes-4.md:26`).
- Mã: `git show team/FEAT-007-task-174:erp_ai/agent/redact.py` (@ `4e24c65`, đúng từng chữ "Mã đề xuất" của `design-w1-fixes-5.md`) và `git show team/FEAT-007:erp_ai/agent/redact.py` (blob `a612f97`, giống hệt `ce696e1`). Module chỉ dùng `re`, `unicodedata`.
- Không đổi kiến trúc: ADR-034 QĐ 2 (một hàm che dùng chung, sửa ở một chỗ là `redact.py`). Không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, regex `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`, `_WORD_START`. Không `DESIGN_CONFLICT`: luật mới nằm trong thiết kế K, không cần phương án dự phòng "che tới cuối dòng".
- Mọi số dưới đây **đã chạy**: `python3 -I` qua stdin heredoc, chỉ thư viện chuẩn, chữ module nạp bằng `git show` rồi `exec`; bản "đề xuất" = chữ của `4e24c65` với đoạn từ `_WORD_START = …` đến trước `def _mask_keep_prefix` thay bằng mục "Mã đề xuất" (thân hàm đúng từng chữ; lúc đo docstring của `_secret_value_end` rút gọn). Không `bench`, không site, không ghi file nào khác.

---

## 1. Hai lỗi đo lại trên `4e24c65` (xác nhận `progress:` round 100), và hai lỗi nữa tìm thấy khi đo

- Lộ: `password=abc|api_key:,hunter2` → `'password=[đã che]|api_key:,hunter2'` trên `4e24c65`; `team/FEAT-007` và `d1e89f3` cho `'password=[đã che]'`.
- O(n²): `"pwd=a|" * N`, `4e24c65`: 30 KB 0,283 s, 60 KB 1,046 s, 120 KB 4,052 s (×3,7, ×3,9 mỗi lần gấp đôi); `team/FEAT-007`: 0,004 / 0,006 / 0,012 s. Số ký tự `_KEY_VALUE` + `_BARE_VALUE_TAIL` khớp ở 60 KB: 5119,8 × độ dài văn bản.
- Nguyên nhân chung: luật cắt của `design-w1-fixes-5.md` (K-4b cũ). Mỗi lần cắt ở khóa bí mật bên trong, vòng quét quay lại khóa đó và `_KEY_VALUE` đọc lại phần giá trị còn lại tới cuối (O(n) mỗi khóa → O(n²)). Phần bị cắt bỏ được giao cho khóa bên trong; khóa đó không có giá trị theo K-4 (`api_key:` rồi `,`) thì không ai che phần đó.
- Thêm (phép liệt kê mục 4 tìm ra): `4e24c65` còn lộ khi ứng viên bí mật nhiều cụm bắt đầu ngay ở đầu giá trị: `api_key=zq0b api_key=` → nguyên văn (cắt còn rỗng, `zq0b api_key` là tên bí mật theo K-2); 35 496 văn bản lộ.
- Thêm, **có sẵn trên `team/FEAT-007` hôm nay**: `_mask_key_values` gọi `_KEY_VALUE.match` trước khi hỏi `is_secret_key`, nên khóa **không** bí mật cũng đọc giá trị: `"user=a|" * N` 60 KB đọc 4388 × độ dài, 0,927 s (480 KB ước ~60 s). Vỡ K-8 sẵn từ T120; T174 sửa luôn bằng đổi thứ tự (mã ở mục 3), không thêm phạm vi file.

## 2. Phán quyết

**K-4b mới: "một khoảng che chỉ lớn lên".** Bỏ việc cắt. Giá trị trần của khóa bí mật được che **trọn** như K-4 đọc, và khoảng che **chỉ kéo dài thêm** khi có thứ chạy qua mép phải của nó. Che thừa được chấp nhận, lộ thì không; đây là luật đơn giản nhất qua được cả ba phép đo (STD-DESIGN-5). Không dùng phương án "che tới cuối dòng": không cần, và nó đổi ca ghim K-4a `password=ab cd` → `password=[đã che] cd`.

Thay K-4b của `design-w1-fixes-5.md` (thêm vào `design-w0-fixes-3.md` mục 3, sau K-4a):

> - **K-4b (khoảng che của giá trị bí mật).** Khi tên là bí mật (K-5) và giá trị là trần theo K-4 (kể cả giá trị bắt đầu bằng `MASK`, K-7), phần bị che là **một khoảng** từ đầu giá trị tới cuối giá trị trần K-4 đọc được. Khoảng không bao giờ bị cắt; nó kéo dài, lặp tới khi không điều nào còn áp: (1) một `MASK` bắt đầu trước cuối khoảng → khoảng kéo qua hết `MASK` đó và đuôi K-7 sau nó; (2) một ứng viên khóa K-1..K-3 bắt đầu trong khoảng (ở chỗ ký tự trước không thuộc `[\w-]`), tên bí mật theo `is_secret_key`, và kết thúc (gồm khoảng trắng sau `:`/`=`) ở hoặc sau cuối khoảng → khoảng kéo tới hết giá trị K-4 của ứng viên đó (nháy kép, nháy đơn, trần hay bắt đầu bằng `MASK`); ứng viên đó không có giá trị → tới cuối ứng viên. Cả khoảng thay bằng **đúng một** `MASK`; quét tiếp ngay sau khoảng. Ứng viên tên bí mật kết thúc trước cuối khoảng không đổi gì: giá trị của nó, nếu có, nằm trọn trong khoảng (giá trị trần đọc từ một chỗ bên trong dừng đúng ở chỗ giá trị ngoài dừng; bắt đầu ở `, ; &` thì không có giá trị). Ứng viên tên không bí mật trong khoảng bị che cùng khoảng (như K-4 nay). Giá trị trong nháy của khóa bí mật: như K-4 (`"[đã che]"`), không áp K-4b.

Thay K-7 (bản của `design-w1-fixes-5.md`):

> - **K-7.** Giá trị trần bắt đầu bằng `MASK` (đã che ở R-3). Tên bí mật → K-4b: giá trị K-4 đọc từ `MASK` dừng ở khoảng trắng trong `MASK`, điều (1) kéo khoảng qua `MASK` và đuôi K-7 (các cụm và dấu `, ; &` mà K-4 còn coi là giá trị trần), rồi qua mọi `MASK` khác khoảng chạm tới → ra đúng một `MASK`, không bao giờ `[đã che] che]`. Tên không bí mật → giữ nguyên `MASK` và phần sau nó, quét tiếp (như cũ).

Thay câu "Thêm (K-4b)" của K-4a (bản của `design-w1-fixes-5.md`) bằng:

> Thêm (K-4b, che thừa được chấp nhận): trong giá trị trần của khóa bí mật, một `MASK` khác hay một dạng khóa tên bí mật không cắt giá trị; khoảng che đi qua chúng và qua giá trị của khóa đó, nên tên khóa bên trong và chữ giữa chúng bị che chung một `[đã che]` (`password=abc|api_key: hunter2` → `password=[đã che]`; `password=sk-ant-A&sk-ant-B` → `password=[đã che]`; `pwd=a|x pwd=b|y` → `pwd=[đã che]` vì `x pwd` là tên bí mật theo K-2). Khóa bí mật bên trong không có giá trị K-4 để chữ sau nó như K-4 (`password=abc|api_key: ,hunter2` → `password=[đã che],hunter2`, cùng lý do với `api_key= , pwd=x`).

Thêm vào K-8:

> - **K-8 (bổ sung, K-4b).** `_KEY_VALUE` chỉ chạy cho tên bí mật (`is_secret_key` hỏi trước). K-4b chỉ đọc phần khoảng mới thêm, khoảng chỉ lớn lên, quét tiếp sau khoảng; nên tổng ký tự mà `_KEY_VALUE` và `_BARE_VALUE_TAIL` khớp không vượt độ dài văn bản (đo: tối đa 1,000 ×, mục 4).

As-Built (writer): đoạn K-4a ghi câu thay ở trên; ghi K-8 bổ sung và việc T174 sửa luôn chỗ O(n²) của khóa không bí mật có từ T120.

## 3. Mã đề xuất (đã chạy đúng thân hàm này)

Trong `erp_ai/agent/redact.py` @ `4e24c65`: giữ `_WORD_START`; **bỏ** `_NOT_WORD_CHAR`; thay `_secret_value_end` và `_mask_key_values` bằng:

```python
def _secret_value_end(text: str, start: int, end: int) -> int:
	"""K-4b: end of the one span masked for a secret key whose bare value K-4 reads over `text[start:end]`.

	The span only grows: while a `MASK` starts before its end, or a key candidate with a secret name starts
	in it and ends at or past its end, it takes in that `MASK` and its K-7 tail, or that candidate and its
	K-4 value. Each part is read once (K-8).
	"""
	scan = start
	while scan < end:
		mask = text.find(MASK, scan, end + len(MASK) - 1)
		if mask != -1:
			scan = mask + len(MASK)
			end = max(end, _BARE_VALUE_TAIL.match(text, scan).end())
			continue
		for word in _WORD_START.finditer(text, scan, end):
			candidate = _KEY_CANDIDATE.match(text, word.start())
			if candidate and candidate.end() >= end and is_secret_key(candidate.group("name")):
				scan = candidate.end()
				value = _KEY_VALUE.match(text, scan)
				end = scan if value is None else value.end()
				break
		else:
			return end
	return end


def _mask_key_values(text: str) -> str:
	"""K-1..K-8: mask the value after each key-name candidate that `is_secret_key` accepts; one pass."""
	parts = []
	position = 0
	while candidate := _KEY_CANDIDATE.search(text, position):
		parts.append(text[position : candidate.end()])
		position = candidate.end()
		if not is_secret_key(candidate.group("name")):
			continue
		value = _KEY_VALUE.match(text, position)
		if value is None:
			continue
		if value.group("double") is not None:
			parts.append(f'"{MASK}"')
			position = value.end()
		elif value.group("single") is not None:
			parts.append(f"'{MASK}'")
			position = value.end()
		else:
			parts.append(MASK)
			position = _secret_value_end(text, position, value.end())
	parts.append(text[position:])
	return "".join(parts)
```

Docstring module: "K-4b added and K-7 as amended by `design-w1-fixes-5.md`" → "K-4b and K-7 as amended by `design-w1-fixes-16.md`".

Ghi chú đã kiểm khi chạy: (1) nhánh `text.startswith(MASK, position)` riêng không còn: với tên bí mật, `_KEY_VALUE` đọc `[đã` (dừng ở khoảng trắng trong `MASK`) rồi điều (1) đi qua `MASK` và đuôi; với tên không bí mật, `continue` để vòng quét đi tiếp từ `MASK`, và không ứng viên nào bắt đầu được trong `[đã che]` (sau `che` là `]`), nên đầu ra như cũ (mọi ca P, K, A ở mục 4c giữ nguyên). (2) `text.find(MASK, scan, end + len(MASK) - 1)` chỉ trả `MASK` bắt đầu trước `end`, có chặn. (3) `max(...)`: khoảng không bao giờ co (một `MASK` nằm trong giá trị nháy của khóa bên trong không làm khoảng ngắn lại). (4) Bỏ qua các ứng viên giữa `scan` cũ và `MASK` tìm thấy là đúng: tên khóa không chạy qua được `[`, nên chúng kết thúc trước cuối khoảng.

## 4. Phép đo nghiệm thu

### 4a. Thời gian (giây, tốt nhất của 3 lần, bản đề xuất; KB = 1024 ký tự)

| Bộ sinh | 60 KB | 120 KB | 240 KB | 480 KB | gấp đôi lớn nhất |
|---|---|---|---|---|---|
| A1 nhiều khóa bí mật không giá trị `"pwd=a\|"*N` | 0.0123 | 0.0245 | 0.0491 | 0.0977 | 2.01 |
| A2 `"password=abc\|api_key:,"*N + "hunter2"` | 0.0227 | 0.0455 | 0.0911 | 0.1818 | 2.01 |
| A3 `"api_key: \|"*N` | 0.0228 | 0.0455 | 0.0911 | 0.1826 | 2.00 |
| A4 `"pwd= "*N` | 0.0458 | 0.0917 | 0.1836 | 0.3677 | 2.00 |
| A5 `"pwd=a\|x "*N` | 0.0405 | 0.0817 | 0.1620 | 0.3228 | 2.02 |
| B1 chuỗi dấu phân cách dài `"password=a" + "&"*N` | 0.0125 | 0.0240 | 0.0630 | 0.1253 | 2.62 |
| B2 `"password=a" + ",;&\|"*N + "x"` | 0.0112 | 0.0232 | 0.0676 | 0.1326 | 2.91 |
| B3 `"pwd=a" + " "*N + "x"` | 0.0071 | 0.0146 | 0.0286 | 0.0564 | 2.06 |
| B4 `"password=a" + "\|"*N + "api_key: hunter2"` | 0.0063 | 0.0125 | 0.0252 | 0.0514 | 2.04 |
| B5 `"password=" + "a."*N + "api_key: z"` | 0.0147 | 0.0294 | 0.0589 | 0.1198 | 2.04 |
| C1 nhiều `MASK` `"password=sk-ant-A&"*N` | 0.0177 | 0.0353 | 0.0711 | 0.1432 | 2.01 |
| C2 `"password=" + "sk-ant-A."*N` | 0.0087 | 0.0171 | 0.0344 | 0.0686 | 2.01 |
| C3 `"pwd=a&sk-ant-X\|"*N` | 0.0076 | 0.0154 | 0.0308 | 0.0620 | 2.02 |
| C4 `"user=sk-ant-A&"*N` | 0.0196 | 0.0388 | 0.0784 | 0.1582 | 2.02 |
| D1 khóa không bí mật `"user=a\|"*N` | 0.0290 | 0.0581 | 0.1191 | 0.2344 | 2.05 |
| D2 `"password=" + "\|user:"*N` | 0.0094 | 0.0186 | 0.0365 | 0.0756 | 2.07 |

```
WORST doubling ratio 2.91; WORST 480 KB 0.3677s
4e24c65 A1 60 KB: 1.056s   4e24c65 A1 120 KB: 4.074s
```

- 480 KB: mọi bộ sinh dưới 0,37 s (< 1 s). Gấp đôi ≤ 2,07 ở 14/16 bộ sinh, mọi bước.
- B1, B2 vượt 2,2 ở **một** bước 120 → 240 KB, rồi về 2,0: bước đó là của regex `_KEY_VALUE` không đổi, đo riêng trên `team/FEAT-007` (tốt nhất của 7 lần, 60/120/240/480/960 KB): B1 `redact` 0.0102 0.0200 0.0588 0.1161 0.2297, `_KEY_VALUE.match` một mình 0.0052 0.0107 0.0386 0.0785 0.1536; B2 `redact` 0.0098 0.0199 0.0631 0.1239 0.2527, `_KEY_VALUE.match` một mình 0.0049 0.0103 0.0444 0.0863 0.1681. Đây là bậc hằng số (240 → 960 KB: ×3,9 qua hai lần gấp đôi), không phải tăng bậc hai; số đọc bên dưới đúng 1,000 × độ dài.
- Số ký tự `_KEY_VALUE` + `_BARE_VALUE_TAIL` khớp / độ dài văn bản, 480 KB, bản đề xuất: A1 1.000, A2 0.545, A3 0.900, A4 0.800, A5 0.375, B1 1.000, B2 1.000, B3 0.000, B4 1.000, B5 1.000, C1 0.167, C2 0.444, C3 0.667, C4 0.000, D1 0.000, D2 1.000 → `WORST proposed reads/len 1.000`. Cùng số ở 60 KB: `4e24c65` A1 5119.8, D1 4388.3; `team/FEAT-007` D1 4388.286 (mọi bộ khác ≤ 1).

### 4b. Liệt kê có hệ thống (không ngẫu nhiên)

Mỗi mục = khóa × dấu khóa × giá trị. Khóa: `api_key`, `my api key` (bí mật), `user` (không bí mật), không khóa. Dấu khóa: `=`, `:`, `: `. Giá trị: rỗng, trần `zq{i}b`, nháy `"zq{i}q"`, mẫu bí mật `sk-ant-zq{i}p` (`i` = vị trí mục, token không trùng nhau). 40 mục mỗi vị trí; mọi dãy 1, 2, 3 mục nối bằng mọi dấu `,` `;` `&` `|` khoảng trắng, xuống dòng: 40 + 40²·6 + 40³·36 = 2 313 640 văn bản. Token phải che = token của giá trị khóa bí mật (theo cấu trúc dựng), hoặc nằm trong một khớp `SECRET_PATTERNS`, hoặc nằm trong giá trị K-4 của **bất kỳ** ứng viên khóa tên bí mật nào (dò ở mọi đầu cụm của văn bản sau R-3, không theo vòng quét của mã). Lộ = một token phải che còn trong đầu ra.

```
items per position: 40
texts enumerated: 2313640
proposed {'cases': 2313640, 'leak_cases': 0, 'leaked_tokens': 0, 'must_tokens': 3862096, 'che_che': 0, 'over': 18180}
4e24c65 {'cases': 2313640, 'leak_cases': 35496, 'leaked_tokens': 35712, 'must_tokens': 3862096, 'che_che': 0, 'over': 17172}
   e.g. 'api_key=zq0b api_key=' -> 'api_key=zq0b api_key='
   e.g. 'api_key=zq0b api_key=zq1b' -> 'api_key=zq0b api_key=[đã che]'
ce696e1 {'cases': 2313640, 'leak_cases': 46872, 'leaked_tokens': 47016, 'must_tokens': 3862096, 'che_che': 61362, 'over': 0}
   e.g. 'api_key=|api_key: zq1b' -> 'api_key=[đã che] zq1b'
   e.g. 'api_key=|api_key="zq1q"' -> 'api_key=[đã che]"zq1q"'
real	2m42.792s
```

Bản đề xuất: 0 lộ trên 3 862 096 token phải che, 0 `che] che]`; `over` = 18 180 token không phải che bị che thừa (chấp nhận theo ưu tiên).

### 4c. Ca K-4/K-4a ghim trong `test_redact.py` và các ca của T174 (`ce696e1` | `4e24c65` | đề xuất; `M` = `[đã che]`)

29 ca K1..K25, A1..A4 của `design-w1-fixes-5.md` mục "Ca K-4/K-4a" ra **giống hệt nhau ở cả ba bản** (chạy lại lần này, ví dụ `password=ab cd` → `password=M cd`, `api_key= , pwd=x` → `api_key= , pwd=M`, `pwd=ab;api key: fake-z` → `pwd=M;api key: M`, `{pwd=ab;}` → `{pwd=M}`, `pwd password=fake-d` → `pwd password=M`). Bảy ca E và sáu ca P (`test_pattern_masked_value_tail_*`) và ba ca N (`test_non_secret_key_inside_value_stays_value`) của đề xuất giống `4e24c65`. Các ca đổi:

| Đầu vào | `ce696e1` | `4e24c65` | đề xuất |
|---|---|---|---|
| `password=sk-ant-FAKE\|api_key: hunter2` | `password=M\|api_key: M` | `password=M\|api_key: M` | `password=M` |
| `password=sk-ant-FAKE.pwd = hunter2` | `password=M.pwd = M` | `password=M.pwd = M` | `password=M` |
| `password=sk-ant-FAKE&tailFAKE\|api_key: hunter2` | `password=M&tailFAKE\|api_key: M` | `password=M\|api_key: M` | `password=M` |
| `password=sk-ant-FAKE\|my api key: hunter2` | `password=M\|my api key: M` | `password=M\|my api key: M` | `password=M` |
| `password=abc\|api_key: hunter2` | `password=M hunter2` | `password=M\|api_key: M` | `password=M` |
| `password=api_key: hunter2` | `password=M hunter2` | `password=api_key: M` | `password=M` |
| `password=abc\|api_key:,hunter2` | `password=M` | `password=M\|api_key:,hunter2` | `password=M` |
| `password=abc\|api_key:"hunter2" x` | `password=M"hunter2" x` | `password=M\|api_key:"M" x` | `password=M x` |
| `pwd=a\|x pwd=b\|y` | `pwd=M pwd=M` | `pwd=M\|x pwd=M` | `pwd=M` |
| `password=sk-ant-A&sk-ant-B` | `password=M&M` | `password=M&M` | `password=M` |
| `password=sk-ant-FAKE&tailFAKE.sk-ant-B` | `password=M&tailFAKE.M` | `password=M.M` | `password=M` |
| `password=x&sk-ant-FAKE` | `password=M che]` | `password=M&M` | `password=M` |
| `password=a\|api_key: sk-ant-B&tailFAKE x` | `password=M M&tailFAKE x` | `password=M\|api_key: M x` | `password=M x` |
| `password=abc\|api_key: ,hunter2` | `password=M ,hunter2` | `password=M\|api_key: ,hunter2` | `password=M,hunter2` |

Cả lớp `TestRedact` của `test_redact.py` @ `4e24c65` (frappe thay bằng `unittest.TestCase`, `site_api.SECRET_FIELDS` chép từ `site_api.py:33`, `keep_agent_settings` không làm gì):

```
[4e24c65] TestRedact @ 4e24c65 test file: ran=29 failures=0 errors=0 failing=[]
[proposed] TestRedact @ 4e24c65 test file: ran=29 failures=9 errors=0 failing=[... 'test_value_stops_before_mask', 'test_value_stops_before_next_secret_key']
```

9 lỗi = đúng 6 + 3 subtest của hai test `f12e429` mà khẳng định đổi theo phán quyết này (STD-TEST-5: đặc tả đổi); 27 test khác xanh, gồm `test_key_value_rules`, `test_list_separator_*`, `test_value_patterns_run_before_key_scan`, `test_pattern_masked_value_tail_*`, `test_non_secret_key_inside_value_stays_value`, `test_secret_value_cut_stays_linear`, `test_long_run_without_secret_untouched`, `test_every_pattern_is_python_310_syntax`.

### 4d. Ba test mới của Expect, chạy đúng chữ ở dòng Expect

```
[proposed] test_no_planted_secret_survives: 9.56s failures=0 errors=0 []     (enumeration texts 297640 leaks 0; đo khi máy đang chạy song song phép 4b)
[proposed] test_value_reads_stay_linear: 0.32s failures=0 errors=0 []
[proposed] test_value_scan_time_at_240_kb: 1.26s failures=0 errors=0 []
[4e24c65] test_value_reads_stay_linear: 2.42s failures=2 errors=0 ['AssertionError: 314562560 not less than or equal to 61440', 'AssertionError: 269611886 not less than or equal to 61439']
[4e24c65] test_no_planted_secret_survives: 8.98s failures=1 errors=0 ["-  ('api_key=zq0b api_key: ', 'api_key=zq0b api_key: ')]"]
```

`test_value_scan_time_at_240_kb` không chạy trên `4e24c65` (ước từ số đo 120 KB: A1 và D1 mỗi cái ~16 s → đỏ 2 subtest; dev đo thật).

**Chưa chạy:** `erp_ai/agent/test_knowledge.py` (cần site); `cmd.lint`/định dạng của mã đề xuất; docstring đầy đủ của `_secret_value_end` (lúc đo dùng bản rút gọn; chữ trên không có `\w`).

---

## 5. Touchpoints

| File | Đổi |
|---|---|
| `erp_ai/agent/redact.py` | Bỏ `_NOT_WORD_CHAR`; thay `_secret_value_end`, `_mask_key_values` đúng mục 3; docstring module. |
| `erp_ai/agent/test_redact.py` | Đổi tên và khẳng định hai test của `f12e429`; thêm một test ghim, ba test mới và các hàm trợ giúp cấp module (dòng Expect). |

Không đường mới (hai file đã có trong `files:` của T174); so với `protected_paths`: không file nào thuộc. Không đổi chữ ký công khai, không mã lỗi mới, không migration.

## 6. Nhánh: dev làm tiếp trên `team/FEAT-007-task-174` @ `4e24c65` (vòng sửa 3/3, vòng cuối)

Hai commit mới: `test(redact): …` (đổi hai test, thêm bốn test; chạy đỏ trên `4e24c65`, dán đầu ra không lọc) rồi `fix(redact): …` (mã mục 3). BASE của review kế: `ce696e161d9d9a208ae2e4d46d6c4598b819d61c`.

## 7. Dòng task T174 (tech-lead chép, thay ba dòng Tiêu chí / Returns / Expect của T174 trong `tasks.md`; tiêu đề, Receives không đổi, `progress:` giữ và nối tiếp)

```
  - Tiêu chí: NFR-6, AC-46, AC-50; ADR-034 QĐ 2; K-8; `review-174.md` (vòng 1, vòng 2 ở `progress:` round 100); `design-w1-fixes-16.md` (K-4b "một khoảng che chỉ lớn lên" thay bản của `design-w1-fixes-5.md`; K-7, câu thêm của K-4a, K-8 bổ sung). Làm tiếp trên `team/FEAT-007-task-174` @ `4e24c65`, vòng sửa 3/3. Chỉ sửa `redact.py` ở: bỏ `_NOT_WORD_CHAR`, thay `_secret_value_end` và `_mask_key_values`, docstring module; không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, `_WORD_START`, regex `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`.
  - Returns: không tên công khai mới. `_secret_value_end(text: str, start: int, end: int) -> int` và `_mask_key_values(text: str) -> str` đúng từng chữ `design-w1-fixes-16.md` mục 3 (khoảng che bắt đầu ở giá trị trần của khóa bí mật, chỉ lớn lên: qua mọi `MASK` bắt đầu trước cuối khoảng cùng đuôi `_BARE_VALUE_TAIL` của nó, và qua giá trị K-4 của ứng viên tên bí mật bắt đầu trong khoảng mà `candidate.end() >= end`; `end = max(...)` ở nhánh `MASK`; ra đúng một `MASK`, `position` = cuối khoảng). `_mask_key_values` hỏi `is_secret_key` TRƯỚC khi gọi `_KEY_VALUE.match` (tên không bí mật → `continue`, không đọc giá trị); không còn nhánh `text.startswith(MASK, position)` riêng. Docstring module: "K-4b and K-7 as amended by `design-w1-fixes-16.md`"; docstring không viết `\w` trong chuỗi thường.
  - Expect: trong `test_redact.py` (thêm `import itertools`, `from unittest import mock`). (1) Đổi `::test_value_stops_before_next_secret_key` thành `::test_secret_key_inside_secret_value_masked_with_it`: `password=sk-ant-FAKE|api_key: hunter2`, `password=sk-ant-FAKE.pwd = hunter2`, `password=sk-ant-FAKE&tailFAKE|api_key: hunter2`, `password=sk-ant-FAKE|my api key: hunter2`, `password=abc|api_key: hunter2`, `password=api_key: hunter2`, `password=abc|api_key:,hunter2` → mỗi ca `password={MASK}`; `password=abc|api_key:"hunter2" x` → `password={MASK} x`; `pwd=a|x pwd=b|y` → `pwd={MASK}`; mỗi ca kiểm thêm `"hunter2" not in` kết quả. (2) Đổi `::test_value_stops_before_mask` thành `::test_mask_inside_secret_value_masked_once`: `password=sk-ant-A&sk-ant-B`, `password=sk-ant-FAKE&tailFAKE.sk-ant-B`, `password=x&sk-ant-FAKE` → mỗi ca `password={MASK}`; `password=a|api_key: sk-ant-B&tailFAKE x` → `password={MASK} x`; mỗi ca kiểm thêm `result.count(MASK) == 1` và `"che] che]" not in`. (3) Mới `::test_secret_key_without_value_inside_value_keeps_rest`: `password=abc|api_key: ,hunter2` → `password={MASK},hunter2` (chú thích: như `api_key= , pwd=x`, K-4 "không có giá trị"). (4) Mới `::test_value_reads_stay_linear` (K-8, tất định, không đo giờ): hằng cấp module `_K8_GENERATORS` = 16 bộ `(unit, head, tail)` đúng thứ tự `("pwd=a|", "", "")`, `("password=abc|api_key:,", "", "hunter2")`, `("api_key: |", "", "")`, `("pwd= ", "", "")`, `("pwd=a|x ", "", "")`, `("&", "password=a", "")`, `(",;&|", "password=a", "x")`, `(" ", "pwd=a", "x")`, `("|", "password=a", "api_key: hunter2")`, `("a.", "password=", "api_key: z")`, `("password=sk-ant-A&", "", "")`, `("sk-ant-A.", "password=", "")`, `("pwd=a&sk-ant-X|", "", "")`, `("user=sk-ant-A&", "", "")`, `("user=a|", "", "")`, `("|user:", "password=", "")`; `_k8_text(unit, head, tail, size) = head + unit * ((size - len(head) - len(tail)) // len(unit)) + tail`; lớp `_CountingPattern(pattern, counter)` có `match(text, pos=0)` gọi `pattern.match(text, pos)` và cộng `found.end() - pos` vào `counter[0]`; mỗi bộ ở `60 * 1024`: `mock.patch.object(redact, "_KEY_VALUE", …)` và `mock.patch.object(redact, "_BARE_VALUE_TAIL", …)` bọc bằng `_CountingPattern`, gọi `redact_secrets`, `assertLessEqual(counter[0], len(text))` trong `subTest(unit=unit, head=head)`. (5) Mới `::test_value_scan_time_at_240_kb` (K-8, biên rộng như `test_long_run_without_secret_untouched`): mỗi bộ của `_K8_GENERATORS` ở `240 * 1024`: `time.monotonic()` dưới 2 s, `"hunter2" not in`, `"che] che]" not in` kết quả. (6) Mới `::test_no_planted_secret_survives` (NFR-6, liệt kê có hệ thống): `_PLANT_KEYS = (("api_key", True), ("my api key", True), ("user", False))`, `_PLANT_SEPARATORS = (",", ";", "&", "|", " ", "\n")`; `_planted_items(index, keys=_PLANT_KEYS, key_separators=("=", ":", ": "))`: với mỗi `kind` theo thứ tự `("empty", "bare", "quoted", "pattern")`, `token = None if kind == "empty" else f"zq{index}{kind[0]}"`, giá trị `""`, `token`, `f'"{token}"'`, `f"sk-ant-{token}"`; mỗi `(key, secret)` × `key_separator` thêm `(f"{key}{key_separator}{value}", token, secret and token is not None)`, rồi thêm `(value, token, False)` (không khóa); `_must_mask(text, planted)`: token có cờ bí mật, cộng token nằm trong một khớp của từng `SECRET_PATTERNS` (dò trên văn bản đã thay dần bằng `redact._mask_keep_prefix`), cộng token nằm trong `redact._KEY_VALUE.match(masked, candidate.end())` của mọi `redact._KEY_CANDIDATE.match(masked, w)` có `is_secret_key(name)` tại mọi đầu cụm `re.finditer(r"(?<![\w-])[\w-]", masked)`; văn bản = mục đầu + `separator + mục` cho mỗi mục sau, mọi `itertools.product` của các bộ mục `full[:1]`, `full[:2]` (`full = [_planted_items(i) for i in range(3)]`) và `small` (`_planted_items(i, keys=(("api_key", True), ("user", False)), key_separators=("=", ": "))` cho `i` = 0, 1, 2) × `itertools.product(_PLANT_SEPARATORS, repeat=len(combo) - 1)`; khẳng định số văn bản `== 297_640` và danh sách `(text, result)` có token phải che còn trong kết quả rỗng (`assertEqual(leaks[:3], [])`). Đỏ trước trên `4e24c65`, đầu ra không lọc qua `grep`/`tail`: (1) 9 subtest, (2) 4, (3) 1, (4) 2 (`pwd=a|`, `user=a|`), (5) 2 (`pwd=a|`, `user=a|`, mỗi cái ~16 s), (6) 1 → `FAILED (failures=19)`; rồi xanh. Giữ xanh không đổi khẳng định: `test_non_secret_key_inside_value_stays_value`, `test_secret_value_cut_stays_linear`, `test_pattern_masked_value_tail_masked` (7 ca), `test_pattern_masked_value_tail_stops_like_bare_value` (6 ca) và mọi test `TestRedact` cũ, gồm `test_value_patterns_run_before_key_scan`, `test_list_separator_*`, `test_key_value_rules`, `test_secret_key_without_value_untouched`, `test_long_run_without_secret_untouched`, `test_every_pattern_is_python_310_syntax`. `cmd.test_one` xanh cho `erp_ai/agent/test_redact.py` và `erp_ai/agent/test_knowledge.py`.
```

Ghi cho reviewer vòng 3: so mã của dev với mục 3 từng chữ; so RED của dev với "failures=19" (số của (5) là ước, các số khác designer đã chạy ở mục 4c, 4d); các phép đo mục 4 chạy lại được bằng `python3 -I` với chữ module từ `git show`.

## 8. Tóm tắt

| Điểm | Phán | File mã | Task | Căn cứ |
|---|---|---|---|---|
| K-4b (lần ba) | Bỏ cắt; khoảng che giá trị bí mật chỉ lớn lên qua `MASK` + đuôi và qua giá trị của khóa bí mật chạy qua mép phải; một `MASK`; `is_secret_key` trước `_KEY_VALUE` | `redact.py`, `test_redact.py` | T174 (vòng 3/3 trên nhánh @ `4e24c65`) | NFR-6, ADR-034 QĐ 2, K-8; mục 4: 0 lộ / 2 313 640 văn bản, 480 KB ≤ 0,37 s, số đọc ≤ 1,000 × độ dài |
