Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 174 — FEAT-007 T174

- Diff: `git diff ce696e161d9d9a208ae2e4d46d6c4598b819d61c..d1e89f38a82f24a40556679943489d99ba0950e7` (nhánh `team/FEAT-007-task-174`; 2 commit `7c11873` test, `d1e89f3` mã; 2 file +44/−7, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: design-defect; CHƯA merge, chưa tick
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer ở lượt này chỉ ghi được file nhớ của mình); chữ của finding giữ nguyên văn.
- Lệnh git reviewer đã dùng (chỉ đọc): `git log --oneline <range>`, `git diff --stat <range>`, `git diff <range>`, `git log --format='%H%n%B---' <range>`, `git show --stat 7c11873 d1e89f3`, `git show d1e89f3:erp_ai/agent/redact.py`, `git show d1e89f3:erp_ai/agent/test_redact.py`.

## Vòng 1 — design-defect

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên mã chưa sửa, `MIGRATE_EXIT=0`: `'password=[đã che]&tailFAKE' != 'password=[đã che]'`, `'password=[đã che]&amp;tailFAKE' != 'password=[đã che]'`, `'password=[đã che].tailFAKE' != 'password=[đã che]'`, `'pwd=[đã che]+tailFAKE' != 'pwd=[đã che]'`, `'token=[đã che]&tailFAKE' != 'token=[đã che]'` cùng hai ca thêm, `Ran 25 tests in 0.330s FAILED (failures=7)`. GREEN, `MIGRATE_EXIT=0`: test_redact `Ran 25 tests in 0.322s OK`, test_knowledge `Ran 37 tests in 1.103s OK`, test_architecture `Ran 181 tests in 15.696s OK`.
- Lớp 1 (khớp đặc tả): mã làm đúng từng chữ phần Returns của T174. `_BARE_VALUE_STEP` (`redact.py:41-43`) được dựng một lần và dùng cho cả `_KEY_VALUE` (`:44-46`) lẫn `_BARE_VALUE_TAIL` (`:48`). Nhánh `MASK` (`:79-84`) chỉ bỏ đuôi khi `is_secret_key`. Docstring module thêm K-7. Không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, K-4a. Hai ca dev thêm (`,` và quét tiếp sau đuôi) cùng tiêu chí, không phải lan phạm vi. Hai lỗi dưới đây nằm ở định nghĩa đuôi của K-7 mới (`design-w1-fixes-2.md:95`), nên verdict là design-defect.
- `_KEY_VALUE` tương đương bản cũ: `}}` trong chuỗi `rf` cho ra `}`, các nhánh và tên nhóm giữ nguyên. Các test K-4 cũ không đổi và vẫn xanh theo GREEN của dev.
- Chi phí backtracking: mỗi bước là cụm possessive `(?=(?P<chunk>…))(?P=chunk)` hoặc một dấu `[,;&]`. Hai nhánh tách nhau theo ký tự đầu, phép nhìn trước là nguyên khối, và sau `*` không còn gì có thể thất bại, nên không có quay lui. Phép nhìn trước phủ định đọc tối đa một ứng viên khóa cho mỗi dấu phân cách, nên K-8 giữ (tuyến tính). Không có `*+`, `++`, `(?>`. `_BARE_VALUE_TAIL` là `re.Pattern` cấp module nên đã nằm trong `test_every_pattern_is_python_310_syntax` (qua `_module_patterns`).
- Khóa không bí mật giữ hành vi cũ: vị trí chỉ dừng sau `MASK` như trước. Ca `note=sk-ant-FAKE&tailFAKE` → `note={MASK}&tailFAKE` (`test_redact.py:254-266`) sẽ đỏ nếu bỏ điều kiện `is_secret_key` ở `:82`.
- `_BARE_VALUE_TAIL.match` có thể khớp chuỗi rỗng nên không bao giờ trả `None`; không có đường lỗi mới.
- Checklist (10): 1 đạt; 2 đạt (2 file touchpoint); 3 đạt với ghi chú: commit test đứng trước commit mã, 7 lỗi khớp 7 subtest, không skip; biên còn thiếu nằm ở minor và ở hai finding; 4 đạt (diff chỉ thêm test, không nới khẳng định cũ, hàm thuần); 5 đạt; 6 không đạt (finding 1); 7 đạt (tên công khai và chữ ký không đổi); 8 đạt; 9 đạt (không thêm phụ thuộc); 10 đạt (`test(redact): … (FEAT-007)`, `fix(redact): … (FEAT-007)`, không dòng ghi công AI, nhánh `team/FEAT-007-task-174`).

### Findings

- major | STD-SEC-6 | erp_ai/agent/redact.py:82-83 | Đuôi K-7 (cụm `[^\s,;&"'}\]]+` gồm cả `:`, `=`, `.`, `/`, `|`, `)`, `+`) nuốt luôn tên khóa bí mật kế tiếp khi khóa đó nối bằng ký tự không phải `, ; &` và sau `:`/`=` có khoảng trắng. Ví dụ `password=sk-ant-FAKE|api_key: hunter2`: mã cũ quét tiếp từ `|api_key: …` và cho `password=[đã che]|api_key: [đã che]`; mã mới lấy cụm `|api_key:`, dừng ở khoảng trắng, rồi quét tiếp từ ` hunter2` (không còn ứng viên) → `password=[đã che] hunter2`, lộ `hunter2`. Tương tự với `password=sk-ant-FAKE.pwd = hunter2`. Nhánh K-4 không qua R-3 vốn đã có giới hạn này (`password=abc|api_key: hunter2`), nhưng K-4a không liệt kê nó, và phần lần theo ở `design-w1-fixes-2.md:99` không xét nó. Mã làm đúng Returns nên đây là lỗi thiết kế | designer chọn một trong hai: (a) ghi ca "khóa bí mật kế tiếp nối bằng ký tự không phải dấu phân cách, có khoảng trắng trước giá trị" vào K-4a (giới hạn chấp nhận, chung với K-4, thêm vào As-Built) và thêm test ghim; hoặc (b) sửa K-4, và đuôi theo nó vì dùng chung mảnh, để dừng trước đầu một ứng viên khóa đứng sau ký tự không phải từ | confirmed (lần theo regex, không chạy)
- major | STD-DESIGN-2 | erp_ai/agent/redact.py:82-83 | Câu đầu của K-7 mới hứa "không thành `[đã che] che]`", nhưng đuôi có thể chạy vào một `MASK` thứ hai do R-3 đặt. Với `password=sk-ant-A&sk-ant-B`, R-3 cho `password=[đã che]&[đã che]`. Đuôi lấy `&` (sau nó là `[`, không thỏa (a)(b)(c)), rồi lấy cụm `[đã` (`[` không bị loại khỏi lớp ký tự), rồi dừng ở khoảng trắng giữa `MASK` → `password=[đã che] che]` (cũ: `password=[đã che]&[đã che]`). Không lộ bí mật, nhưng ra đúng chuỗi mà K-7 cấm. Mã làm đúng định nghĩa đuôi, tức thiết kế tự mâu thuẫn | designer phán cùng lượt với finding trên: đuôi dừng ở đầu `MASK` (cụm không được bắt đầu tại `[đã che]`), hoặc chấp nhận và sửa câu K-7; kèm test ghim | confirmed (lần theo regex, không chạy)
- minor | — | — | 2 điểm nhỏ: (a) chưa có ca đuôi dừng ở khoảng trắng giữa chừng, ở `"`, `'` hay `]` (chỉ có `}`). Lớp ký tự dùng chung với `_KEY_VALUE` và `]` đã được ghim ở `test_list_separator_before_closing_mark_stays_in_value`, nhưng nếu ai đó viết lại riêng `_BARE_VALUE_TAIL` và bỏ `]` thì không test nào bắt được; (b) đuôi bỏ cả dấu câu hay `)` dính sau bí mật (`(password=sk-ant-FAKE).` → `(password=[đã che]`), khớp K-4 nhưng làm mất chữ trong email hay nhật ký | dev's call

### Không kiểm được từ diff — tech-lead giải

- Dev chạy RED trước commit test và lọc đầu ra qua `grep`/`tail`, nên không chứng minh được RED chạy đúng trên nội dung file của `7c11873`. Số lỗi 7 khớp 7 subtest của `test_pattern_masked_value_tail_masked`. Việc test ghim xanh trên mã cũ khớp lần theo của reviewer (`&page=2`: sau `MASK` mã cũ quét tiếp, `page` không bí mật).
- Reviewer không chạy test và không chạy thử hai chuỗi của finding (hook chặn python ở vai reviewer): cả hai finding là lần theo regex bằng tay. Tech-lead chưa chạy lại vì task dừng trước merge; lần gọi dev kế tiếp của T174 phải dựng hai chuỗi đó thành test trước.
- Nếu designer chọn phương án (a): đoạn K-4a trong As-Built phải ghi thêm ca của finding 1.

## Kết luận của tech-lead (vòng 1)

- `design-defect` → theo quy trình, DỪNG riêng chuỗi T174 (`redact.py`, `test_redact.py`: T120 → T174), báo team-leader; không gọi dev sửa, không merge, không tick. Các làn khác của lượt 14 chạy tiếp.
- Nhánh `team/FEAT-007-task-174` @ `d1e89f3` giữ lại. Cần designer phán hai điểm: (1) ca `password=sk-ant-FAKE|api_key: hunter2` (K-4a hay sửa luật đuôi/K-4); (2) đuôi chạy vào `MASK` thứ hai (`password=sk-ant-A&sk-ant-B`).
- Hai finding chưa được chạy thật: lượt designer nên yêu cầu test ghim cho cả hai chuỗi để phép lần theo regex được đo.

## deferred

- Không có.

## Vòng 3 (2026-11-15, range ce696e1..ee9c618)

- Diff: `git diff ce696e161d9d9a208ae2e4d46d6c4598b819d61c..ee9c618` (nhánh `team/FEAT-007-task-174`; vòng này 2 commit `b575415` test, `ee9c618` mã; cả range 2 file +269/−12: `redact.py` +44/−12, `test_redact.py` +225/−0, đều là touchpoint). Duyệt toàn bộ, không giới hạn ở diff sửa.
- Vòng: 3 (trần `max_rework` = 3). Verdict: **approve** (0 blocker, 0 major).
- Lệnh git đã dùng (chỉ đọc): `git log --oneline ce696e1..ee9c618`, `git diff --stat ce696e1..ee9c618`, `git diff --stat 4e24c65..ee9c618`, `git diff 4e24c65..ee9c618 -- erp_ai/agent/redact.py`, `git diff 4e24c65..ee9c618 -- erp_ai/agent/test_redact.py`, `git diff --numstat ce696e1..ee9c618`, `git diff ce696e1..ee9c618 -- erp_ai/agent/test_redact.py` (tìm dòng `-` và skip/xfail), `git log --format='%h %an %s%n%b' ce696e1..ee9c618`, `git show ee9c618:erp_ai/agent/redact.py`.

### Lớp 1 (khớp đặc tả)

- Mã đúng từng chữ mục 3 `design-w1-fixes-16.md`: `diff` dòng 46–94 của thiết kế với khối `_secret_value_end` + `_mask_key_values` của `git show ee9c618:erp_ai/agent/redact.py` → `DIFF_EXIT=0`. `_NOT_WORD_CHAR` đã bỏ; `is_secret_key` hỏi trước `_KEY_VALUE.match`; nhánh `text.startswith(MASK, position)` không còn; docstring module đúng câu "K-4b and K-7 as amended by `design-w1-fixes-16.md`", không có `\w` trong chuỗi thường. `git diff 4e24c65..ee9c618 -- redact.py` không chạm `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, `_WORD_START`, `_KEY_CANDIDATE`, `_KEY_VALUE`, `_BARE_VALUE_STEP`, `_BARE_VALUE_TAIL`.
- Lần theo: khoảng không co (`max` ở nhánh `MASK`; ở nhánh ứng viên `value.end() >= candidate.end() >= end`); mỗi `MASK` và mỗi đầu cụm trong khoảng đọc một lần; `candidate.end() >= end` bắt cả giá trị nháy của khóa bên trong (cụm trần dừng ở `"`/`'`, nên ứng viên kết thúc đúng ở cuối khoảng). Chạy `python3 -I` trên chữ module: `password=abc|api_key:"hunter2 x" y` → `password=[đã che] y`, `password=a|api_key:'hunter2 x' y` → `password=[đã che] y`, `password=a|token=sk-ant-B x y` → `password=[đã che] x y`; ca ghim cũ giữ: `password=ab cd` → `password=[đã che] cd`, `api_key= , pwd=x` → `api_key= , pwd=[đã che]`, `note=sk-ant-FAKE&tailFAKE` → `note=[đã che]&tailFAKE`, `{pwd=ab;}` → `{pwd=[đã che]}`, `user=x|api_key: hunter2` → `user=x|api_key: [đã che]`.
- Test (Expect (1)–(6)): hai test đổi tên đổi khẳng định vì đặc tả đổi (K-4b thay bằng `design-w1-fixes-16.md`, STD-TEST-5 đạt); 9 + 4 ca đúng danh sách, kèm `"hunter2" not in` / `count(MASK) == 1` / `"che] che]" not in`; (3) đúng chuỗi; `_K8_GENERATORS` 16 bộ đúng thứ tự và giá trị; `_k8_text`, `_CountingPattern` đúng chữ; (4) vá `_KEY_VALUE` và `_BARE_VALUE_TAIL` qua `mock.patch.object` (hai hàm đọc biến cấp module lúc gọi, nên vá có tác dụng), `subTest(unit, head)`, ở 60 KB; (5) 240 KB, biên 2 s mỗi subtest, hai khẳng định chữ; (6) `_PLANT_KEYS`, `_PLANT_SEPARATORS`, `_planted_items`, `_must_mask` đúng mô tả; số văn bản 40 + 40²·6 + 20³·36 = 297 640, khớp hằng. `test_redact.py` −0 dòng so với `ce696e1`: mọi test giữ xanh không đổi khẳng định. Không skip/xfail/only.
- RED (dev, `b575415` trên mã `4e24c65`, đọc file đầu ra không lọc): 20 `FAIL:` = (1) 9, (2) 4, (3) 1, (4) 2, (5) 3, (6) 1, mỗi cái đỏ đúng lý do (chuỗi `[đã che]&[đã che]`, `|api_key: [đã che]`, số đọc 314 562 560 / 269 611 886, giờ 27,7 s / 23,7 s, lộ `api_key=zq0b api_key=`). Lệch so với 19 của Expect: subtest thứ ba của (5) là `password=abc|api_key:,` với `'hunter2' unexpectedly found` — đó chính là chỗ lộ vòng 2 trên `4e24c65` mà khẳng định `"hunter2" not in` của (5) bắt được; con số 19 là ước của designer (`design-w1-fixes-16.md` mục 4d ghi (5) không chạy trên `4e24c65`). Đỏ đúng lý do; lệch được chấp nhận.

### Finding các vòng trước

- Vòng 1 (1) STD-SEC-6 `password=sk-ant-FAKE|api_key: hunter2`: ADDRESSED — `redact.py:74-97`; chạy: → `password=[đã che]`; ghim ở `test_secret_key_inside_secret_value_masked_with_it`.
- Vòng 1 (2) STD-DESIGN-2 `[đã che] che]`: ADDRESSED — `redact.py:84-87`; chạy: `password=sk-ant-A&sk-ant-B` → `password=[đã che]`; ghim ở `test_mask_inside_secret_value_masked_once` (`count(MASK) == 1`).
- Vòng 2 (1) O(n²) K-8: ADDRESSED — `redact.py:79-97`, `:107-110`; đo `python3 -I` ở 240 KB, tốt nhất 3 lần: `pwd=a|` 0,080 s (vòng 2: 16,0 s), `user=a|` 0,206 s; test đếm tất định `test_value_reads_stay_linear` xanh.
- Vòng 2 (2) lộ sau khóa bí mật bên trong không giá trị: ADDRESSED — `redact.py:90-94`; chạy: `password=abc|api_key:,hunter2` → `password=[đã che]`; thêm `api_key=zq0b api_key=` → `api_key=[đã che]` (chỗ lộ thứ ba của mục 1 thiết kế).

### Đã chạy

- Site, một lần giữ khóa, PYTHONPATH = worktree `agent-ae40749d8cce32ff8` @ `ee9c618`: `MIGRATE_EXIT=0`; `Ran 33 tests in 18.927s` OK `TEST_EXIT=0`; `Ran 33 tests in 18.653s` OK `TEST_EXIT=0`; `Ran 33 tests in 18.991s` OK `TEST_EXIT=0`. Thời gian riêng: `test_no_planted_secret_survives` 15,2 / 14,9 / 15,3 s; `test_value_scan_time_at_240_kb` 2,07 / 2,06 / 2,06 s (cả 16 subtest). Ghi chú quy trình: lệnh của reviewer có ống `grep -v` (bỏ dòng `Updating/Executing/Enqueu…`) và `tail -40`; các dòng `Ran …`, `OK`, `MIGRATE_EXIT`, `TEST_EXIT` còn nguyên trong file đầu ra.
- Không site (`python3 -I`, chữ module từ `git show ee9c618:…`): mỗi bộ `_K8_GENERATORS` ở 240 KB, tốt nhất 3 lần, load average 1,6 trên 20 lõi: lớn nhất `pwd= ` 0,321 s, `pwd=a|x ` 0,286 s, `user=a|` 0,206 s, tổng 2,05 s; không bộ nào ra `hunter2` hay `che] che]`.
- Phán về đồng hồ: biên 2 s áp cho **từng subtest**; subtest chậm nhất 0,32 s → dư ~6 lần, trung bình 0,13 s → dư ~15 lần. Đủ ổn trên máy chung nếu không bị nghẽn CPU cực nặng; người gác K-8 thật là test đếm tất định (4), nên (5) đỏ một lần thì ghi vào `docs/team/debt.md` (STD-TEST-7), không nới biên. `test_no_planted_secret_survives` ~15 s (≈ 80 % thời gian module) là chi phí chấp nhận được cho một test liệt kê, không phụ thuộc giờ; không phải finding.

### Findings

- Không blocker, không major.
- minor (gộp): (a) STD-TEST-6 | `erp_ai/agent/test_redact.py` `test_value_scan_time_at_240_kb` | test phụ thuộc đồng hồ theo đúng Expect; dư ~6 lần ở subtest chậm nhất; chú thích "linear takes under 0.2 s here" thấp hơn số đo 0,32 s của `pwd= ` | giữ; flake thì ghi `debt.md` (STD-TEST-7) | confirmed (đo). (b) STD-TEST-8 | `erp_ai/agent/test_redact.py` `_must_mask` | trọng tài dùng lại `redact._KEY_CANDIDATE`, `_KEY_VALUE`, `_mask_keep_prefix`, `SECRET_PATTERNS` của chính module: đổi regex K-4 thì trọng tài đổi theo; được bù bởi các ca ghim chữ (`test_key_value_rules`, 4c) và trọng tài quét mọi đầu cụm, khác vòng quét của mã (đã bắt chỗ lộ của `4e24c65`) | dev's call | confirmed.

### Checklist (10)

1 đạt (mã đúng mục 3, test đúng Expect, không thêm gì); 2 đạt (2 file touchpoint); 3 đạt (commit test trước commit mã, 20 đỏ đúng lý do, không skip/xfail); 4 đạt (hai test đổi vì đặc tả đổi; −0 dòng test cũ; test thuần, độc lập; (5) xem minor a); 5 đạt (không đường lỗi mới; `_BARE_VALUE_TAIL.match` không bao giờ `None`; vòng lặp có chặn: `scan` tăng mỗi bước hoặc trả về); 6 đạt (đóng hai chỗ lộ vòng 2 và chỗ lộ `api_key=zq0b api_key=`; che thừa được thiết kế chấp nhận; token trong test là giả `zq…`, `hunter2`, `sk-ant-FAKE`); 7 đạt (không tên công khai mới, chữ ký `redact_secrets` không đổi; đầu ra chỉ che thêm); 8 đạt (tên theo profile, `_NOT_WORD_CHAR` gỡ, không mã chết); 9 đạt (chỉ `itertools`, `unittest.mock` của thư viện chuẩn, trong test); 10 đạt (`test(redact): … (FEAT-007)`, `fix(redact): … (FEAT-007)`, STD-NAME-5; không `Co-Authored-By`/dòng ghi công AI, STD-GIT-8; nhánh `team/FEAT-007-task-174`; As-Built K-4a/K-8 là việc của writer theo mục 2 thiết kế).

### Không kiểm được từ diff — tech-lead giải

- Reviewer không chạy `erp_ai/agent/test_knowledge.py`, `erp_ai/tests/test_architecture.py`, `pre-commit run --all-files` trên `ee9c618`; chỉ có GREEN của dev (`Ran 37 tests in 2.800s` OK, `Ran 181 tests in 29.326s` OK, `LINT_EXIT=0`). test_architecture của dev chạy trên nhánh gốc `ce696e1`: sau merge vào `team/FEAT-007` phải chạy lại với các luật đã merge sau đó.
- Phép liệt kê 2 313 640 văn bản (mục 4b thiết kế) không chạy lại; chỉ có 297 640 văn bản của test (6).
- Nơi gọi `redact_secrets` (log, kết quả tool, Error Log, email) nay nhận che thừa nhiều hơn (cả tên khóa bí mật bên trong); không đổi hợp đồng, nhưng As-Built phải ghi câu K-4a mới.

## Kết luận của reviewer (vòng 3)

- `approve`: merge được vào `team/FEAT-007`; sau merge chạy lại test_redact, test_knowledge, test_architecture trên nhánh feature.
