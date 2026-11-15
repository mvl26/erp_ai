Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 35 — FEAT-007 T35

- Diff: `git diff 66fc4afb47f2bc1727f845919304b94f733776d2..0d7b49b` (nhánh `team/FEAT-007-task-35`, 5 commit `9af4fa7`, `9a39527`, `b286281`, `7fb3b68`, `0d7b49b`); diff sửa vòng 4: `git diff b286281..7fb3b68`; diff sửa vòng 5: `git diff 7fb3b68..0d7b49b`
- Vòng: 5 (hai vòng thêm trên trần `max_rework` = 3, team-leader cho từng vòng: quyết định (a) lúc 22:10 và quyết định (a) lúc 23:31 ở journal; vòng 5 là lượt sửa hẹp, chỉ finding STD-CI-2)
- Verdict: approve (vòng 5); request-changes ở vòng 1, 2, 3, 4

## Vòng 1 — request-changes

- Range: `66fc4af..9af4fa7` (1 commit, 2 file mới, +145).
- Bằng chứng của dev: RED `erp_ai.agent.test_redact` `AttributeError: module 'erp_ai.agent.redact' has no attribute 'redact_secrets'`, `FAILED (errors=37)`; GREEN `Ran 8 tests in 0.071s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.101s OK`; `grep -c "def is_secret_key" erp_ai/agent/redact.py` = 1.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/test_redact.py:19 | Tiêu chí là "từng mẫu", nhưng mẫu `sk-ant-` (`redact.py:20`) không bao giờ là mẫu che ca của nó. Đầu vào `sk-ant-FAKE0000000000000000` còn 24 ký tự sau `sk-`, nên mẫu chung `(?<![\w-])sk-[\w-]{16,}` (`redact.py:21`) cũng che. Xóa `redact.py:20` thì cả bộ test vẫn xanh. | Thêm một ca chỉ mẫu đó bắt được: khóa ngắn như `"khóa sk-ant-abc hết hạn"` → `"khóa [đã che] hết hạn"`. Thêm cặp biên 15/16 ký tự cho mẫu `sk-` chung (hiện chỉ có `sk-12345`). |
| major | STD-TEST-8 | erp_ai/agent/redact.py:11-12 | Regex khóa-giá trị bắt đầu bằng `[\w-]*` và không neo. Trên một dãy dài liền chữ, số, `_`, `-` không chứa từ bí mật (dữ liệu base64url, hex dump, định danh dài trong kết quả công cụ hoặc Error Log), `re` của Python thử lại từ mọi vị trí và lùi hết dãy mỗi lần, nên công tăng theo bình phương độ dài dãy. Không test nào dùng đầu vào dài, dù hàm này sẽ chạy trên mọi dòng log, kết quả công cụ và lần đọc Error Log. (suspected: reviewer không đo được; xác nhận bằng một dòng đo thời gian `redact_secrets("a"*50000)`) | Neo đầu khóa bằng `(?<![\w-])` trước `[\w-]*` để mỗi dãy chỉ quét một lần; kết quả khớp không đổi. Thêm test với dãy 100.000 ký tự, kiểm văn bản trả về không đổi. |

minor | — | — | 4 điểm nhỏ: (1) `test_one_word_list_for_both_functions` kết bằng `assertTrue(redact.SECRET_PATTERNS)`, không bao giờ đỏ; (2) `redact_secrets` dựa vào việc `_KEY_VALUE` là phần tử 0 của `SECRET_PATTERNS` (`SECRET_PATTERNS[1:]`); (3) giá trị không ngoặc có dấu cách chỉ được che tới dấu cách đầu (`password: my phrase` → `password: [đã che] phrase`); (4) `Bearer\s+\S{8,}` không phân biệt hoa thường cũng che chữ tiếng Anh thường như "bearer instrument" | tùy dev

### Ghi nhận của reviewer

- Đủ ba thứ phải giao; một danh sách `SECRET_WORDS` dựng regex khóa-giá trị và điều khiển `is_secret_key`; 6 mẫu khớp `design.md:486`, tên khóa và tiền tố được giữ; 4 tên của `site_api.SECRET_FIELDS` được phủ, test đọc danh sách thật; `redact.py` chỉ import `re` (F-1).

### Review checklist (10)
1. đạt 2. đạt 3. trượt một phần (2 major trên); không skip 4. đạt 5. đạt 6. đạt (khóa trong test đều là giá trị giả) 7. đạt 8. đạt 9. đạt 10. đạt (`feat(agent): ... (FEAT-007)`)

## Vòng 2 — request-changes (scoped re-review)

- Range sửa: `git diff 9af4fa7..9a39527` (1 commit, 2 file, +19/−5).
- Bằng chứng của dev: finding 1: ca mới `"khóa sk-ant-abc hết hạn"` → `"khóa [đã che] hết hạn"`; xóa dòng `sk-ant-` thì `FAILED (failures=1)`, `AssertionError: 'khóa sk-ant-abc hết hạn' != 'khóa [đã che] hết hạn'`; cặp biên `sk-FAKE000000000000` (16, bị che) / `sk-FAKE00000000000` (15, giữ nguyên). Finding 2: trước khi sửa `redact_secrets("a"*50000)` mất 59,35 s (5k: 0,606 s; 10k: 2,4 s; 20k: 9,86 s); thêm `(?<![\w-])` trước `[\w-]*` của `_KEY_VALUE`; sau khi sửa 50k mất 0,005 s, 100k mất 0,0098 s; regex cũ và mới cho cùng kết quả trên 200.000 chuỗi ngắn ngẫu nhiên (`diffs 0`); test mới `test_long_run_without_secret_untouched` trên mã cũ đỏ vì thời gian: `230.86 / 221.81 / 290.98 not less than 10`, `FAILED (failures=3)`. GREEN `test_redact` `Ran 9 tests ... OK`; `test_architecture` `Ran 112 tests ... OK`.

| # | Finding vòng 1 | Kết quả |
|---|---|---|
| 1 | major STD-TEST-2 — mẫu `sk-ant-` không có ca riêng; thiếu cặp biên 15/16 | ADDRESSED (`test_redact.py:22` chỉ `redact.py:20` che được; cặp biên ở `test_redact.py:24` và `:48-50`) |
| 2 | major STD-TEST-8 — regex khóa-giá trị không neo, công bậc hai, không test đầu vào dài | ADDRESSED cho dạng đầu vào nêu ở vòng 1 (`redact.py:12` thêm `(?<![\w-])`; `test_redact.py:52-59` đo ba dãy khoảng 100.000 ký tự). Còn hở với một dạng đầu vào liên quan: finding mới bên dưới |

### Phát hiện mới ở vòng 2
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/redact.py:12 (chỗ hở của test ở test_redact.py:55) | Phép neo chỉ chặn `[\w-]*` đứng đầu. `[\w-]*` đứng sau nhóm từ bí mật không đổi. Trong một dãy chữ, mỗi lần gặp một từ bí mật thì lượng từ đó chạy tới hết dãy rồi lùi từng ký tự để tìm `["']?\s*[:=]`. Nên một dãy dài gồm các từ bí mật lặp lại không có `:`/`=` (ví dụ `"pwd" * 33_334` hoặc `"token" * 20_000`, khoảng 100k ký tự) vẫn tốn khoảng n²/(2·len(từ)) bước, cùng cỡ với ca 59 s của vòng 1. Cả ba đầu vào của test mới không chứa từ bí mật, nên đường này không được chạy. Hàm dùng chung cho kết quả công cụ, lần đọc Error Log và email (`design.md:486`), là chữ do khách hàng điều khiển. (suspected: suy từ cách engine regex của CPython lùi; reviewer không chạy được) | Làm cho phép quét khóa tuyến tính: khớp dãy khóa một lần rồi kiểm bằng `is_secret_key` trong callback thay thế (giữ dạng hai từ `mật khẩu`), hoặc làm phần đuôi không lùi: `[\w-]*+` trên Python ≥ 3.11, hoặc `(?=(?P<tail>[\w-]*))(?P=tail)` trên bản cũ hơn. Dạng possessive vẫn quét tới hết dãy mỗi lần trúng, nên cách callback mới thật sự tuyến tính. Thêm ca đo thời gian với `"pwd" * 33_334` và `"Token" * 20_000` (không có `:`/`=`) vào `test_long_run_without_secret_untouched` hoặc một test cạnh nó, và dán đầu ra đỏ trên mã hiện tại. |

minor | — | — | 1 điểm nhỏ: `test_redact.py:59` khẳng định trên thời gian thật (STD-TEST-6); biên 10 s khiến khó chập chờn, nhưng test đếm bước, hoặc đầu vào nhỏ hơn với biên chặt hơn mà vẫn rộng, sẽ không phụ thuộc máy | tùy dev

### Review checklist (10), chỉ diff sửa
1. đạt 2. đạt 3. đạt cho hai finding cũ; finding mới ở trên 4. xem minor; không khẳng định sẵn có nào bị nới 5. không liên quan 6. đạt 7. đạt (chữ ký `redact_secrets` không đổi) 8. đạt 9. đạt 10. đạt (`fix(agent): ... (FEAT-007)`)

### Trạng thái vòng (tech-lead)

- Đã dùng 2/3 vòng. Finding 2 của vòng 1 được đánh dấu ADDRESSED; finding mới là một dạng đầu vào khác của cùng họ lỗi (regex lùi bậc hai), mức "suspected". Chưa quá `max_rework`, chưa phải "cùng một finding hai vòng liền": còn đúng một vòng rework (3/3) với một dev mới nhận báo cáo này làm đầu vào. Vòng 3 vẫn còn finding của họ này → dừng, phán từng finding và báo team-leader.
- Thông tin dev vòng 3 cần: bench chạy Python 3.12.3 (`/home/miyano/frappe-bench/env/bin/python --version`), nên `[\w-]*+` dùng được; reviewer khuyên cách callback.
- Vòng 3 CHƯA gọi: tech-lead dừng lượt này để báo ba design-defect (T3, T24, T41). FIX_BASE vòng 3 = `9a39527`.

## Vòng 3 — request-changes (scoped re-review + thay đổi thiết kế 5a)

- Range sửa: `git diff 9a39527..b286281` (1 commit, 2 file, +117/−20). Vòng này mang cả luật đoạn tên của `design-w0-fixes-2.md` 5a.
- Bằng chứng của dev: RED trên mã cũ `AssertionError: 51.454898399999365 not less than 10`; `'input_tokens: [đã che], output_tokens: [đã che], api_key=[đã che]' != 'input_tokens: 1200, output_tokens: 512, api_key=[đã che]'`; `Ran 13 tests in 82.432s FAILED (failures=10)`. GREEN `test_redact` `Ran 15 tests in 0.125s OK`; `test_architecture` `Ran 112 tests in 3.360s OK`.

| # | Finding vòng 2 | Kết quả |
|---|---|---|
| R2-1 | major STD-TEST-8 — `[\w-]*` đứng sau nhóm từ bí mật lùi bậc hai trên dãy từ bí mật lặp lại | ADDRESSED (`redact.py:16`: đầu neo, hai cụm possessive `[\w-]++`, kiểm bí mật bằng `is_secret_key` trong vòng lặp, công tuyến tính; `test_redact.py:60-61` thêm `"pwd" * 33_334`, `"Token" * 20_000`) |

Đối chiếu 5a: `is_secret_key` (`redact.py:20-32, 88-95`) đúng từng bước; mẫu ứng viên (`redact.py:16`) đúng; năm mẫu còn lại không đổi; mọi ví dụ True/False của 5a và 4 tên `SECRET_FIELDS` có trong `test_is_secret_key_names`.

### Phát hiện mới ở vòng 3
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-5 | erp_ai/agent/redact.py:51-56 (ghim bởi test_redact.py:146-149) | Luật "cụm đầu là bí mật → bỏ cặp, xét cụm sau" không có trong 5a và làm lộ giá trị mà 5a che. Với "Secret Key: S3cr3t", "password mới: x", "token cũ: x": cặp bị bỏ, cụm sau một mình ("Key", "mới", "cũ") không phải bí mật, giá trị còn nguyên. Theo 5a `is_secret_key("Secret Key")` là True và giá trị phải bị che. `test_secret_word_before_another_run_is_not_the_key` khẳng định "token abc: fake-c" không bị che, ngược với 5a. Luật này có để giữ khẳng định cũ `token <key>:<secret>`, nhưng một bản sửa đúng 5a cũng giữ được khẳng định đó. (confirmed: lần theo tay, không chạy) | Bỏ nhánh bỏ cặp, áp 5a như chữ. Chạy mẫu `token <key>:<secret>` (redact.py:40, không đổi) trước bước quét khóa-giá trị. Theo vết trên giấy: mọi khẳng định cũ giữ kết quả, "Authorization: token K:S" vẫn ra "Authorization: token [đã che]", "token abc: fake-c" thành "token abc: [đã che]". Viết lại test đó, thêm "Secret Key: fake-x" → bị che. Nếu designer muốn giữ luật bỏ cặp thì 5a phải được sửa trước. |
| major | STD-TEST-8 | erp_ai/agent/redact.py:12, :25, :91-95 (không ca nào ở test_redact.py:95-126) | Ba vế của luật 5a không có test nào đỏ khi bị bỏ: (a) ranh giới "số đứng trước chữ hoa" (`or name[index - 1].isdigit()`, ví dụ oauth2Token); (b) `-` và `.` làm dấu tách (api-key, smtp.password); (c) "liền nhau": đổi phép kiểm lát cắt thành phép kiểm tập con vẫn xanh vì không tên False nào có cả `api` và `key` rời nhau. Mỗi vế sai sẽ lặng lẽ biến một khóa bí mật thành không bí mật trong run_log của U3. (confirmed: đột biến lần theo tay) | Thêm ca True "oauth2Token", "api-key", "smtp.password" và ca False "api_primary_key". |

minor | — | — | 4 điểm nhỏ: (1) docstring `redact_secrets` (redact.py:79) nói "giá trị bí mật khớp SECRET_PATTERNS" trong khi `SECRET_PATTERNS[0]` nay chỉ tìm ứng viên, và không nói đầu ra là NFC (STD-DOC-7); (2) còn phụ thuộc vị trí `SECRET_PATTERNS[1:]` (redact.py:83); (3) chú thích ở test_redact.py:54-55 còn nói "anchored scan" đã bị thay; (4) biên thời gian thật ở test_redact.py:66, đã nêu ở vòng 2 | tùy dev

### Review checklist (10), chỉ diff sửa
1. trượt (luật thừa ngoài 5a, finding 1) 2. đạt 3. một phần (có RED, không skip; ba vế 5a chưa có test, finding 2) 4. đạt (không khẳng định cũ nào bị nới; test mới ở :146-149 thuộc finding 1) 5. đạt 6. một phần (finding 1 để lọt giá trị vào log, NFR-6) 7. đạt về mã (chữ ký không đổi; nghĩa của `SECRET_PATTERNS[0]` đổi) 8. đạt 9. đạt (`unicodedata` là thư viện chuẩn) 10. đạt (`fix(agent): … (FEAT-007)`)

### Phán của tech-lead ở trần vòng (3/3 đã dùng) — DỪNG T35, báo team-leader

Đã gọi dev 3 lần (vòng 1, rework 2, rework 3) và review 3 lần; review vòng 3 vẫn `request-changes`. Gọi thêm một vòng là vượt `max_rework` = 3, nên tech-lead không gọi và phán từng finding còn mở:

| Finding còn mở | Phán | Lý do |
|---|---|---|
| Vòng 3 #1 — major STD-DESIGN-5, luật bỏ cặp ngoài 5a | **Thật, chặn merge.** | Để lọt giá trị bí mật ("Secret Key: …", "password mới: …") vào log, trái NFR-6 và trái chữ 5a. Dev đã báo đây là lệch có chủ ý vì khẳng định cũ `token key:secret`; reviewer chỉ ra cách sửa nằm trong 5a (đổi thứ tự: mẫu `token <key>:<secret>` chạy trước), mới lần theo tay, chưa chạy. Không phải cùng một finding lặp lại: vòng 1, 2 là công bậc hai, vòng 3 phát sinh từ thay đổi thiết kế 5a đưa vào đúng vòng cuối. |
| Vòng 3 #2 — major STD-TEST-8, ba vế 5a chưa có test | **Thật, chặn merge.** | Bốn ca test, không đổi mã. Cùng mã STD-TEST-8 với vòng 1 và 2 nhưng là chỗ hở khác (vế mới của 5a). |
| deferred — mẫu JWT (`redact.py:41`, dòng không đổi) nghi lùi bậc hai trên `"eyJ-" * 25_000` | **Thật có thể có, hoãn, cần đo.** | Ngoài diff sửa; 5a chỉ đòi tuyến tính cho mẫu khóa-giá trị. Đề nghị đưa một ca đo thời gian vào vòng sửa kế nếu team-leader cho thêm vòng; không thì ghi `debt.md`. |
| Câu hỏi thiết kế — văn bản trả về luôn ở dạng NFC, kể cả khi không che gì | **Không phải finding; cần designer.** | 5a chỉ nói "chuẩn hóa NFC trước khi so". T36, T37, T53, U3 chưa viết; cần biết nơi gọi có được so `redact_secrets(x)` với `x` không. |
| Câu hỏi thiết kế — `SECRET_PATTERNS[0]` nay chỉ tìm ứng viên | **Không phải finding; cần designer ghi chữ.** | `design.md:486` và dòng Returns của T35 còn tả "giá trị khớp SECRET_PATTERNS"; chưa nơi nào gọi. |

Đề nghị: team-leader (decide) cho một vòng sửa thứ 4 với dev mới, đầu vào là hai finding vòng 3 nguyên văn, kèm câu trả lời của designer cho hai câu hỏi thiết kế (hoặc xác nhận "giữ 5a, đổi thứ tự mẫu"). FIX_BASE vòng kế = `b286281`; nhánh `team/FEAT-007-task-35` giữ, chưa merge; worktree dev đã xóa (sạch). T36, T37, T53 chờ T35.

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Câu hỏi thiết kế (không chặn T35): luật "tên chứa một từ" cộng từ `token` khiến `redact_secrets` che số đếm sử dụng (`output_tokens: 512` → `output_tokens: [đã che]`, `is_secret_key("input_tokens")` là True); `runner.py:97` `USAGE_COLUMNS` và `gateway/__init__.py:25` `USAGE_FIELDS` dùng đúng các khóa đó, và NFR-6 đưa log qua hàm này | Chữ của thiết kế gây ra, không phải dev. Tech-lead chuyển team-leader để designer quyết có loại `*_tokens` hay không, trước các task dùng hàm này trên log (T36, T53, U3). |
| RED của dev: stub `redact.py` có ở lúc RED | Đúng cách tech-lead yêu cầu (module import sạch, đỏ vì thiếu hàm). |
| Chuẩn hóa Unicode: `mật khẩu` chỉ khớp ở dạng NFC | Thiết kế không nói; đưa vào `deferred`, kèm câu hỏi thiết kế trên. |

## deferred

- (minor, tùy dev) 4 điểm nhỏ ở trên.
- (thiết kế) `*_tokens` bị che; dạng Unicode NFD.

## Vòng 4 — request-changes (scoped re-review, luật N/K/R của `design-w0-fixes-3.md` mục 3)

- Range sửa: `git diff b286281..7fb3b68` (1 commit, 2 file, +132/−70). Lệnh reviewer đã chạy: `git log --oneline b286281..7fb3b68`, `git diff --stat b286281..7fb3b68`, `git diff b286281..7fb3b68`, `git show 7fb3b68:erp_ai/agent/redact.py`, `git show 7fb3b68:erp_ai/agent/test_redact.py`, `git log -1 --format=%B 7fb3b68`, `git diff --check b286281..7fb3b68`; đọc thêm một lần cho rủi ro có tên: `git show 7fb3b68:.github/workflows/ci.yml`, `pyproject.toml`.
- Bằng chứng của dev: RED trên `redact.py` cũ: `test_is_secret_key_names (criterion='N-2b', name='DBPassword') AssertionError: False is not True` (cùng dạng cho `APIKey`, `JWTToken`); `test_key_value_rules (text='token abc: fake-c') AssertionError: 'token abc: fake-c' != 'token abc: [đã che]'` (cùng dạng cho `'Secret Key: fake-x'`, `'password mới: fake-y'`, `'Mật khẩu mới: fake-m'`); `test_secret_patterns_are_the_five_value_patterns AssertionError: 6 != 5`; `Ran 18 tests in 0.173s FAILED (failures=8)`. `test_output_is_nfc` và `test_value_patterns_run_before_key_scan` xanh ngay lần đầu trên mã cũ (không có RED). GREEN `test_redact` `Ran 18 tests in 0.184s OK`; `test_architecture` `Ran 112 tests in 3.098s OK`.

| # | Finding vòng 3 | Kết quả |
|---|---|---|
| R3-1 | major STD-DESIGN-5 — luật bỏ cặp ngoài 5a làm lộ giá trị (`redact.py:51-56` @ `b286281`) | ADDRESSED (`redact.py:52-74`: nhánh bỏ cặp đã bỏ; tên ứng viên xét nguyên bằng `is_secret_key(candidate.group("name"))` ở `:64`; `test_redact.py:156-171` khẳng định "token abc", "Secret Key", "password mới", "Mật khẩu mới" bị che) |
| R3-2 | major STD-TEST-8 — ba vế 5a không có test | ADDRESSED (`test_redact.py:117` `oauth2Token` đỏ khi bỏ vế chữ số; `:119` `api-key`, `smtp.password` đỏ khi bỏ `-`/`.` khỏi dấu tách; `:126` `api_primary_key` đỏ khi đổi "liền nhau" thành "tập con"; đột biến lần theo tay) |

Đối chiếu từng luật (mã @ `7fb3b68` → test đỏ khi bỏ luật):

| Luật | Mã | Test ghim |
|---|---|---|
| N-1 | `redact.py:33` | `test_redact.py:120` (NFD "Mật khẩu") |
| N-2a | `redact.py:39-40` | `:116`, `:117` (`oauth2Token`) |
| N-2b | `redact.py:41` | `:118` (RED có); vế `name[index - 1].isupper()` không ghim (minor 1) |
| N-3 | `redact.py:46` `casefold()` | `:111`, `:120` (`MẬT KHẨU`) |
| N-4 | `redact.py:13`, `:46` | `:119` |
| N-5 | `redact.py:11`, `:49` | `:213-217` |
| N-6 | `redact.py:96-101` | `:126` (`api_primary_key`), `:130` (`apikey`) |
| N-7 | không có mã thêm | `:124` (`passwords`, `*_tokens`), `:130` (`mat khau`) |
| K-1 | `redact.py:26` `(?<![\w-])` | `:56-68` (đo thời gian) |
| K-2 | `redact.py:26` `{0,2}` | `:163` (≥ 3 cụm), `:165` "password cũ của anh" (≤ 3 cụm), `:164` |
| K-3 | `redact.py:26` | `:41`, `:35` |
| K-4 | `redact.py:28` | `:208`, `:211`, `:41` |
| K-5 | `redact.py:64` | `:160-163` |
| K-6 | `redact.py:57-58`, `:66-72` | `:150`, `:167` ("ghi chú: token=…") |
| K-7 | `redact.py:59-62` | `:177` (bỏ K-7 → `"password=[đã che] che]"`) |
| K-8 | `redact.py:26` (possessive) | `:62-63` thêm `"a " * 50_000 + ": x"`, `"Mật khẩu " * 20_000`; xem finding mới |
| R-1 | `redact.py:86-87` | `:82-83` |
| R-2, 3a | `redact.py:88` | `:201-205`, `:144-146` |
| R-3, R-4 | `redact.py:89-91`, `:77-78` | `:176` (đổi thứ tự → `"Authorization: token FAKEKEY:[đã che]"`) |
| 3b | `redact.py:16-22`; `_KEY_CANDIDATE` riêng, không truy cập theo chỉ số | `:184-199` |

Hai test không có RED (`test_output_is_nfc`, `test_value_patterns_run_before_key_scan`) ghim hành vi đã có trước vòng này (mã cũ ra cùng kết quả nhờ nhánh bỏ cặp). Trên mã mới chúng bắt được đột biến: đổi thứ tự R-3/R-4 đỏ ở `:176`, bỏ K-7 đỏ ở `:177`. Không phải finding.

### Phát hiện mới ở vòng 4

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-CI-2 | erp_ai/agent/redact.py:26 | `_KEY_CANDIDATE` dùng lượng từ possessive (`[\w-]++`, `\s*+`). `re` của Python chỉ nhận chúng từ bản 3.11; trên 3.10, `re.compile` ném `re.error: multiple repeat`, nên import `erp_ai.agent.redact` hỏng. Dự án khai `requires-python = ">=3.10"` (`pyproject.toml:7`), và `.github/workflows/ci.yml:50` dựng Python 3.10 rồi chạy `bench run-tests --app erp_ai` (`:110`) mỗi lần push `develop` và mỗi PR. Sau khi T35 merge, `test_redact` và mọi module import nó sau này (T36, T37, T53, U3) lỗi trên CI đó. Bench chạy 3.12 nên GREEN của dev không thấy. Dòng này nằm trong diff sửa; cấu trúc possessive có từ `b286281` (vòng 3, reviewer vòng 3 bỏ sót) và ghi chú vòng 2 chấp nhận `*+` chỉ dựa trên bản Python của bench. (confirmed: đọc ci.yml, pyproject; không chạy) | Giữ tính "không lùi" của K-8 bằng cú pháp 3.10 nhận: mỗi cụm `(?=(?P<runN>[\w-]+))(?P=runN)` (ba tên nhóm riêng cho ba cụm), hai `\s*+` làm tương tự; giữ test đo thời gian làm bằng chứng tuyến tính. Hoặc người quyết nâng sàn Python lên 3.11 ở `pyproject.toml:7`, `ci.yml:50`, `linter.yml:25,:44` (ngoài touchpoints của T35, tech-lead và người quyết). |

minor | — | — | 3 điểm nhỏ: (1) vế `name[index - 1].isupper()` của N-2b (`redact.py:41`) không có test đỏ khi bị bỏ (ví dụ `"x/Token"` thành True; chỉ che thừa, không lộ) (STD-TEST-8); (2) K-2 "đúng một dấu cách U+0020" (dấu cách trơn ở `redact.py:26`) không ghim: đổi thành `\s` vẫn xanh, chỉ che thừa; (3) biên thời gian thật ở `test_redact.py:68`, đã nêu ở vòng 2 và 3 (STD-TEST-6) | tùy dev

### Review checklist (10), chỉ diff sửa

1. đạt (mọi dòng mã truy về N/K/R/3a/3b; không luật thừa) 2. đạt (2 file trong touchpoints) 3. đạt (RED cho 8 subtest; hai test không RED ghim hành vi có sẵn, đột biến lần theo tay; không skip) 4. đạt (chỉ thay `test_secret_word_before_another_run_is_not_the_key` theo thiết kế, lý do STD-TEST-5 ghi trong commit; mọi tên cũ của `test_is_secret_key_names` còn, `assertIs` chặt hơn `assertTrue`) 5. đạt (R-1 xử lý `None`; không gọi dịch vụ ngoài) 6. đạt (giá trị trong test đều giả; chỗ lộ của R3-1 đã đóng) 7. một phần (chữ ký không đổi; mã cần Python ≥ 3.11 trái `requires-python >=3.10`, finding mới) 8. đạt (tên rõ, docstring khớp N/K/R, không mã chết) 9. đạt (chỉ thư viện chuẩn) 10. đạt (`fix(agent): … (FEAT-007)`, không trailer AI)

### Không kiểm được từ diff (vòng 4)

- Không chạy test, lint (site dùng chung); `failures=8` của RED khớp vết tay (3 N-2b + 4 luật K + 1 độ dài).
- `ci.yml` có thật sự chạy trên GitHub cho repo này không; prod chạy Python nào (nếu 3.10 thì lỗi cả lúc chạy, không chỉ CI).
- Kết quả ruff-format (`pre-commit` không chạy); E501 đã tắt trong `pyproject.toml`, `git diff --check` sạch.
- Test "che trước, cắt sau" của 3a thuộc T36, T37.

### deferred (vòng 4)

- (thiết kế, K-4) Giá trị mở nháy mà không đóng (`password="abc`) không có giá trị theo K-4 nên không bị che, lộ ra; câu hỏi cho designer, không phải lỗi dev.
- (giữ từ vòng 3) mẫu JWT trên `"eyJ-" * 25_000`; 4 điểm nhỏ của vòng 3.

### Phán của tech-lead sau vòng 4 (không có vòng 5) — DỪNG T35 lần hai, báo team-leader

| Finding | Phán | Lý do |
|---|---|---|
| major STD-CI-2 `redact.py:26` (lượng từ possessive) | có thật, CHẶN merge | tech-lead đọc lại trên `7fb3b68`: `pyproject.toml:7` `requires-python = ">=3.10"`; `.github/workflows/ci.yml:50` `python-version: '3.10'`, `:110` `run-tests --app erp_ai`; `redact.py:26` có `[\w-]++` và `\s*+`; bench chạy Python 3.12.3. Lượng từ possessive chỉ có trong `re` từ Python 3.11, nên merge là làm CI đỏ ngay ở bước import (STD-CI-2), không hoãn được |
| 3 minor của vòng 4 | có thật, hoãn (deferred) | chỉ che thừa, không lộ; không chặn |
| câu hỏi K-4 (nháy mở không đóng) | chuyển designer | thiết kế, không phải lỗi dev |

Hai lối ra, cần team-leader/người chọn: (a) cho một lượt sửa nữa trong touchpoints của T35: viết lại `_KEY_CANDIDATE` bằng cú pháp Python 3.10 nhận (lookahead + tham chiếu ngược như cột `fix`), giữ test đo thời gian; phần còn lại của vòng 4 đã đạt (R3-1, R3-2 ADDRESSED, 20 luật đều có mã và test); (b) nâng sàn Python lên 3.11 ở `pyproject.toml`, `ci.yml`, `linter.yml`: ngoài touchpoints của T35, là quyết định của người. Nhánh `team/FEAT-007-task-35` @ `7fb3b68` giữ nguyên, chưa merge. T36, T37, T53 vẫn chờ.

## Vòng 5 — approve (scoped re-review, lượt sửa hẹp cuối, chỉ finding STD-CI-2 của vòng 4)

- Căn cứ: quyết định (a) của team-leader lúc 23:31 (journal `docs/team/journal/FEAT-007.md`): lối ra (a) ở trên, một lượt sửa trong touchpoints; reviewer soát finding đó và hồi quy.
- Diff sửa: `git diff 7fb3b68243f8f1916988eef53cdb66c4504b8b7e..team/FEAT-007-task-35` = 1 commit `0d7b49b` (`fix(agent): write the key-name candidate in Python 3.10 regex syntax (FEAT-007)`), 2 file: `erp_ai/agent/redact.py` +9/−3, `erp_ai/agent/test_redact.py` +80.
- Lệnh reviewer đã dùng (chỉ đọc): `git log --oneline 7fb3b68..team/FEAT-007-task-35`, `git diff --stat …`, `git diff …`; `git show team/FEAT-007-task-35:erp_ai/agent/redact.py`, `:erp_ai/agent/test_redact.py`, `:pyproject.toml`, `:.github/workflows/ci.yml`; `git log -1 --format='%an%n%B'`; `git grep` ở đầu nhánh tìm regex possessive/atomic khác và API chỉ có từ Python 3.11.
- Bằng chứng của dev: RED trên mã cũ `AssertionError: Lists differ: ['possessive at 25', 'possessive at 36', 'possessive at 53', 'possessive at 61'] != []`, `Ran 20 tests in 0.200s FAILED (failures=1)`; GREEN `erp_ai.agent.test_redact` `Ran 20 tests in 0.266s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.098s OK`.

### Finding cũ

| Finding | Trạng thái | Bằng chứng |
|---|---|---|
| vòng 4, major STD-CI-2 `redact.py:26` (lượng từ possessive) | ADDRESSED | `redact.py:28-32` ở `0d7b49b` không còn `++`, `*+`, `?+`, `(?>`; mỗi cụm và mỗi `\s*` viết thành `(?=(?P<x>…))(?P=x)` (lookahead + tham chiếu ngược, cú pháp `re` có từ trước 3.10). `test_every_pattern_is_python_310_syntax` (`test_redact.py:286-297`) ghim điều này cho mọi mẫu đã biên dịch của module và kiểm cả danh sách mẫu được quét (không qua được trên danh sách rỗng). Bốn vị trí 25, 36, 53, 61 trong RED của dev khớp số đếm tay của reviewer. `pyproject.toml:7` (`>=3.10`) và `ci.yml` (`python-version: '3.10'`) không đổi |

### Hồi quy (K-8, cùng tập khớp, cú pháp 3.10)

- Cùng tập khớp: lookahead của Python không lùi vào trong chính nó, nên nhóm bắt giữ giữ dãy dài nhất và tham chiếu ngược ăn đúng dãy đó, giống `[\w-]++` và `\s*+`. Nhóm `{0,2}` cũ vốn không possessive; dạng lồng `(?: … (?: …)?)?` giữ nguyên điều đó. Ký tự đứng sau một cụm (dấu cách, nháy, `\s`, `[:=]`) không khớp `[\w-]`, ký tự sau `\s*` (`[:=]` hoặc hết chuỗi) không khớp khoảng trắng, nên việc trả ký tự lại không bao giờ biến một lần trượt thành một lần khớp.
- Số nhóm: `name` vẫn là nhóm 1; nơi gọi duy nhất dùng `candidate.group("name")` (`redact.py:64`); `_mask_keep_prefix` chỉ dùng `groupdict()` trên `SECRET_PATTERNS` (không đổi).
- Tuyến tính (K-8): `(?<![\w-])` chỉ cho bắt đầu khớp ở đầu một dãy; từ mỗi điểm bắt đầu máy đọc tối đa 3 cụm và một khối khoảng trắng. `test_long_run_without_secret_untouched` (đầu vào ~100 nghìn ký tự, trần 10 giây) phủ cả đường nhiều cụm lẫn dãy đơn dài và xanh trong GREEN của dev.
- Cú pháp 3.10: mọi mẫu của module (`_SEGMENT_SEPARATOR`, 5 mẫu `SECRET_PATTERNS`, `_KEY_CANDIDATE`, `_KEY_VALUE`) được test mới quét; possessive và nhóm atomic là cú pháp regex duy nhất 3.11 thêm. File test tự nó chạy được trên 3.10. Phép tự kiểm `test_python_311_construct_check_catches_each_construct` dùng chuỗi cố định: mọi dạng possessive, `(?>`, và các bẫy báo nhầm (lượng từ lười, `\{2}+`, `[\]+]+`, `(?P<…>`, lookaround).

### Phát hiện mới ở vòng 5

Không có blocker, không có major.

minor | — | — | 2 điểm nhỏ: (a) `test_redact.py:21` phép kiểm đọc nhầm dấu `?` sau một dấu gạch chéo ngược đã escape rồi tới nhóm (`\\(?:…)`) là lượng từ; không báo sai được vì ký tự kế đặt lại trạng thái, nhưng chưa có test; (b) bộ tách regex 40 dòng trong test có thể ngắn hơn nếu đi trên đầu ra của `re._parser` (đổi lại phụ thuộc API riêng) | tùy dev

### Review checklist (10), chỉ diff sửa

1. đạt (chỉ mẫu tên khóa và một test ghim cú pháp) 2. đạt (2 file trong touchpoints, không file mới) 3. đạt (RED dán; tự kiểm phủ ca biên; không skip/xfail) 4. đạt (không phép khẳng định cũ nào đổi; test mới là hàm thuần, không dữ liệu site) 5. đạt / không áp dụng 6. đạt (hành vi che không đổi; không bí mật) 7. đạt (chữ ký và kết quả của `redact_secrets`, `is_secret_key` không đổi; nhóm 1 vẫn là `name`) 8. đạt (tab như phần còn lại; comment `redact.py:24-27` đúng; không mã chết) 9. đạt (chỉ `re` của thư viện chuẩn) 10. đạt (`fix(agent): … (FEAT-007)`, một commit, không trailer AI)

### Không kiểm được từ diff (vòng 5) — kết luận của tech-lead

- Reviewer không chạy test → tech-lead chạy `cmd.test_one` cho `erp_ai/agent/test_redact.py` và `erp_ai/tests/test_architecture.py` trên `team/FEAT-007` sau merge, dưới khóa site; đầu ra ở dòng `progress:` của T35 trong `tasks.md`.
- CI có thật sự xanh trên Python 3.10 hay không: CHƯA kiểm bằng một trình thông dịch 3.10 (bench chạy 3.12.3; tech-lead chỉ được chạy git và các ô `cmd.*`). Căn cứ hiện có: phép kiểm tĩnh trong test và lập luận ở mục Hồi quy. Còn mở, không chặn merge: xác nhận ở lần CI đầu tiên của nhánh (`/team:pr`) hoặc ở `/team:verify`; nếu đỏ ở bước import `erp_ai.agent.redact` thì mở lại T35.

### deferred (vòng 5)

- 2 điểm nhỏ của vòng 5; 3 điểm nhỏ của vòng 4; câu hỏi K-4 (nháy mở không đóng) cho designer; mẫu JWT trên `"eyJ-" * 25_000` và 4 điểm nhỏ của vòng 3 vẫn giữ.
- Reviewer đã dò phần còn lại của app (`erp_ai/*.py` ở đầu nhánh) tìm cú pháp/API chỉ có từ 3.11 (`tomllib`, `datetime.UTC`, `StrEnum`, `except*`, `typing.Self`, `TaskGroup`, `ExceptionGroup`, regex possessive/atomic): không có gì ngoài 2 lần báo nhầm ở dữ liệu test dạng diff (`+++ b/x`).
