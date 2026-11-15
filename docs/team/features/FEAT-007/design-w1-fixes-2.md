# FEAT-007 — design-w1-fixes-2: phán ba điểm hẹp về mặt nạ bí mật (chữ mặt nạ, `reason`, K-4/K-7)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu; không chặn build (READY build 56/124).
- Đầu vào: `review-84.md:33-35`; `design-addendum-1-U3.md:95`, `:98`, `:130`, `:145`; `review-120.md:45`; `design-w0-fixes-3.md:160-170` (K-1..K-8); `design-w0-fixes-4.md` điểm 3 (K-4, K-4a).
- Mã đọc (chỉ đọc, `git show team/FEAT-007:<path>` @ `ce696e1`): `erp_ai/agent/run_log.py:14-92` (`SECRET_MASK`, `_password_fields`, `_mask`, `action_entry`); `erp_ai/agent/redact.py:11-107` (`MASK`, `_KEY_VALUE`, `_mask_key_values`, `redact_secrets`); `erp_ai/agent/tools/site_api.py:33`, `:61` (`SECRET_FIELDS`, `SCRUBBED_VALUE`); `erp_ai/agent/changes/result_comment.py:25`, `:49` (`MASKED_WORD`); `erp_ai/agent/test_run_log.py:441-527`; `erp_ai/agent/test_redact.py:226-301`.
- Không đổi kiến trúc: theo ADR-033 Ràng buộc (`action_entry` là hàm dựng mục duy nhất), ADR-034 QĐ 2 (một hàm che dùng chung, sửa ở một chỗ).

---

## Điểm 1 — Hai chữ mặt nạ trong một mục hành động

### Hiện trạng (dữ kiện)
- `run_log.SECRET_MASK = "[đã ẩn]"` (`run_log.py:16`) thay **cả giá trị** của khóa bí mật: `redact.is_secret_key(khóa)`, `site_api.SECRET_FIELDS`, hoặc trường `Password` theo meta của `doctype` (`run_log.py:36-39`).
- Mọi chuỗi lá còn lại đi qua `redact.redact_secrets` (`run_log.py:44-45`), hàm này chỉ thay **đoạn bí mật** trong văn bản bằng `redact.MASK = "[đã che]"` (`redact.py:11`), giữ phần còn lại.
- Cùng chữ `"[đã ẩn]"` đã có ở hai chỗ khác với cùng nghĩa "ẩn nguyên một đơn vị, không đọc nội dung": `site_api.SCRUBBED_VALUE` (`site_api.py:61`, mặt nạ của T61, `U3.md:130` ghi "cùng chữ với mặt nạ của T61") và `result_comment.MASKED_WORD` (`result_comment.py:25`, ẩn nguyên một từ có `://` hoặc `@`). `"[đã che]"` là chữ duy nhất của `redact` cho mọi kênh (nhật ký, kết quả tool, Error Log, email; `redact.py:1`).
- Mã làm đúng `U3.md:98` và `U3.md:145`; `test_masks_secret_keys_password_fields_and_secret_text` (`test_run_log.py:475`) đã ghim `SECRET_MASK == "[đã ẩn]"` và chuỗi lá `== redact.redact_secrets(...)`.

### Phán quyết
**Giữ hai chữ, cố ý.** Nghĩa của từng chữ:

| Chữ | Nghĩa | Ai đặt |
|---|---|---|
| `"[đã ẩn]"` | **Nguyên giá trị** của một trường bị ẩn vì **bản thân trường** là bí mật (theo tên khóa, `SECRET_FIELDS` hoặc kiểu `Password`); giá trị không được đọc, không biết bên trong có gì. | `run_log.SECRET_MASK`, `site_api.SCRUBBED_VALUE`, `result_comment.MASKED_WORD` |
| `"[đã che]"` | Một **đoạn bí mật** được tìm thấy **bên trong văn bản tự do** (mẫu giá trị hoặc cặp khóa-giá trị, R-1..R-5); phần còn lại của văn bản giữ nguyên. | `redact.MASK`, qua `redact.redact_secrets` |

Ví dụ của `review-84.md:33` (`{"api_key": "[đã ẩn]", "note": "Bearer [đã che]"}`) là đúng ý: người đọc nhật ký biết `api_key` bị ẩn trọn, còn `note` là văn bản có một đoạn bị che.

**Không** đặt `SECRET_MASK = redact.MASK` và **không** thêm tham số mặt nạ cho `redact`: hợp nhất không tăng an toàn (cả hai đều không để lộ giá trị), nhưng phải sửa ba module đã merge cùng test đã ghim của chúng (`test_site_api.py:33`, `test_result_comment.py:34`, `test_run_log.py:476`) và mất phân biệt "trọn trường" với "một đoạn". Hai chữ là hằng riêng; không module nào so khớp chữ của module kia.

### Thay chữ thiết kế (tech-lead chép; designer không sửa `design-addendum-1-U3.md`)
Thay `design-addendum-1-U3.md:98` bằng:

> Giá trị của khóa bí mật trong `value_before`/`value_after` (tên khóa, `SECRET_FIELDS`, trường `Password`) thay trọn bằng `"[đã ẩn]"` (mục 3.1); đoạn bí mật bên trong các chuỗi lá còn lại do `redact.redact_secrets` thay bằng `"[đã che]"`. Hai chữ cố ý khác nhau: `"[đã ẩn]"` = ẩn trọn một trường, `"[đã che]"` = che một đoạn trong văn bản (`design-w1-fixes-2.md` điểm 1). `reason` cũng đi qua `redact.redact_secrets` (`design-w1-fixes-2.md` điểm 2).

As-Built (writer): một dòng trong phần nhật ký giải thích hai chữ theo bảng trên.

### Mã
Không cần sửa mã. Một test ghim nghĩa của hai chữ được gộp vào task của điểm 2 (cùng file `test_run_log.py`): `TestActionEntry::test_two_mask_words_have_distinct_meanings`.

---

## Điểm 2 — `reason` của mục hành động không đi qua `redact_secrets` (STD-SEC-6)

### Hiện trạng (dữ kiện)
- `run_log.py:88-89`: `entry["reason"] = reason if _is_name(reason) else NO_REASON` — chuỗi gốc vào mục, không che. `U3.md:95` định nghĩa `reason` là "lý do bị từ chối hoặc lớp lỗi khi sập"; `U3.md:145` chỉ yêu cầu che `value_*`.
- `review-84.md:34`: T91 (tool), T92 (định tuyến), T110 (thông báo) có thể truyền `str(exception)` hoặc văn bản tool trả về vào `reason`; văn bản đó có thể chứa bí mật (ví dụ lỗi HTTP có `Authorization: Bearer …`, lỗi validate có `password=…`).
- `action_entry` là hàm dựng mục duy nhất (ADR-033 Ràng buộc), nên che ở đây phủ mọi nơi gọi hiện có và sau này.

### Phán quyết
**Có. `reason` đi qua `redact.redact_secrets` bên trong `action_entry`**, một chỗ duy nhất (ADR-034 QĐ 2: không giao việc che cho từng nơi gọi T91, T92, T110). Thứ tự: kiểm rỗng trước, che sau: `redact.redact_secrets(reason) if _is_name(reason) else NO_REASON`. `redact_secrets` không bao giờ biến chuỗi khác rỗng thành rỗng, nên quy tắc `NO_REASON` không đổi. `rule` **không** che: là tên quy tắc định tuyến lấy từ cấu hình, không phải văn bản tool hay ngoại lệ. Lời giao reviewer của T91, T92, T110 không cần thêm điều kiện che riêng; chỉ ghi "`reason` được `action_entry` che, nơi gọi không tự che".

**Password của hàng bảng con — giới hạn đã chấp nhận, không thêm luật cho đợt 1:** `_password_fields` chỉ đọc meta của `doctype` cha, nên một trường `Password` của hàng bảng con chỉ bị ẩn trọn khi tên khóa qua `is_secret_key` hoặc thuộc `SECRET_FIELDS` (hai luật này áp ở mọi mức lồng nhau, `run_log.py:36-43`), còn không thì giá trị chỉ được `redact_secrets` che theo mẫu; ghi vào As-Built, xem lại khi có tool ghi hàng bảng con của DocType có trường `Password`.

### Touchpoints
| File | Đổi |
|---|---|
| `erp_ai/agent/run_log.py` | `action_entry`: một dòng `reason`; docstring thêm "`reason` passed through `redact.redact_secrets`". Không tên mới, không đổi chữ ký. |
| `erp_ai/agent/test_run_log.py` | Hai test mới trong `TestActionEntry`. |

Không đường mới; không chạm `protected_paths`. Cả hai file đã có trong `files:` của T84 (đã merge).

### Khối task mới (tech-lead đặt số và tiêu đề; chèn trong `tasks-w1.md` ngay sau T84)

```
- [ ] T?? — `action_entry` che `reason` bằng `redact_secrets` — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py — test: erp_ai/agent/test_run_log.py — depends: T84
  - Tiêu chí: NFR-6, AC-10; STD-SEC-6; `review-84.md:33-34`; `design-w1-fixes-2.md` điểm 1 (ghim hai chữ) và điểm 2. Chỉ sửa dòng `reason` của `action_entry` và docstring; không đổi `_mask`, `_password_fields`, `rule`, hằng số, chữ ký.
  - Receives: `action_entry`, `_is_name`, `NO_REASON`, `SECRET_MASK` (T84); `redact.redact_secrets`, `redact.MASK` (T35, T120); `site_api.SCRUBBED_VALUE` (T61).
  - Returns: không tên mới. Khi `ok` là `False`: `entry["reason"] = redact.redact_secrets(reason) if _is_name(reason) else NO_REASON`. Khi `ok` là `True`: không có khóa `reason` (như nay). `rule` giữ nguyên chuỗi gốc.
  - Expect: `TestActionEntry::test_refused_reason_secret_masked` (reason `"ERPAI-TEST lỗi: password=ERPAI-TEST-p9 và Bearer ERPAITESTbearer12345"` → `entry["reason"] == redact.redact_secrets(reason)`, chứa `redact.MASK`, không chứa `ERPAI-TEST-p9`, không chứa `ERPAITESTbearer12345`; subtest reason `"khóa sk-ant-FAKE0000 hết hạn"` → `"khóa [đã che] hết hạn"`; subtest `rule="ERPAI-TEST-rule-9"` giữ nguyên) đỏ trước (reason còn chuỗi gốc) rồi xanh; `::test_two_mask_words_have_distinct_meanings` (test ghim, xanh ngay là đúng, ghi lý do trong progress: `run_log.SECRET_MASK == site_api.SCRUBBED_VALUE == "[đã ẩn]"`, `redact.MASK == "[đã che]"`, hai chữ khác nhau; `action_entry(..., value_after={"api_key": "ERPAI-TEST-k", "note": BEARER_TEXT})` → `api_key == SECRET_MASK`, `note` chứa `redact.MASK` và không chứa `SECRET_MASK`); bốn test `TestActionEntry` cũ giữ xanh (`test_refused_entry_keeps_reason` với `"ERPAI-TEST-not-permitted"` không đổi: không có `:`/`=`, không khớp mẫu nào). `cmd.test_one` xanh cho `erp_ai/agent/test_run_log.py`.
```

### Task phải chờ task này
- **Thêm `depends:` task mới** vào **T85** (file chung `run_log.py`, `test_run_log.py`; giữ một chủ mỗi file) và **T91** (nơi đầu tiên truyền `reason` thật từ tool).
- Chờ bắc cầu, không cần sửa dòng `depends:`: T86 (sau T85), T92 (sau T91), T93 (sau T92), T110 (sau T93).
- Nếu T85 đã đang chạy khi chèn: task mới chạy ngay sau T85 merge, và thêm vào `depends:` của T86 thay cho T85; T91 vẫn phải chờ task mới.

---

## Điểm 3 — Chỗ hở giữa K-4 mới và K-7 cũ (NFR-6)

### Lần theo đường mã (đọc mã, **không chạy thử**)
Đầu vào `password=sk-ant-FAKE&tailFAKE`, qua `redact.redact_secrets` (`redact.py:97-107`) @ `ce696e1`:
1. NFC không đổi chuỗi.
2. `SECRET_PATTERNS[0]` `(?<![\w-])sk-ant-[\w-]+` (`redact.py:18`): trước `s` là `=` (không thuộc `[\w-]`) → khớp `sk-ant-FAKE`, dừng ở `&` (không thuộc `[\w-]`) → văn bản thành `password=[đã che]&tailFAKE`. Bốn mẫu còn lại không khớp.
3. `_mask_key_values` (`redact.py:68-90`): `_KEY_CANDIDATE.search` khớp `password=` (kết thúc ở vị trí 9). `text.startswith(MASK, 9)` đúng → thêm `MASK`, nhảy qua `MASK`, `continue` (`redact.py:75-78`); **không** gọi `_KEY_VALUE`, **không** xét K-4.
4. Tìm ứng viên tiếp từ `&tailFAKE`: `tailFAKE` theo sau là hết văn bản, không có `:`/`=` → không có ứng viên; phần còn lại thêm nguyên văn.

Kết quả: `password=[đã che]&tailFAKE` — `&tailFAKE` **lộ**. Khẳng định của `review-120.md:45` đúng. Theo K-4 (`design-w0-fixes-4.md` điểm 3), nếu không có R-3 thì `&` theo sau là `tailFAKE` rồi hết văn bản không thỏa (a), (b), (c), nên thuộc giá trị và cả `sk-ant-FAKE&tailFAKE` bị che; K-7 làm tắt bước này. Cùng chỗ hở với mọi ký tự K-4 coi là thuộc giá trị trần nhưng mẫu R-3 dừng ở đó: `.` `/` `+` `:` `&` `;` `,` (ví dụ `password=sk-ant-FAKE.tailFAKE`, `pwd=sk-FAKE0000000000000000+tailFAKE`, `token=eyJa.eyJb.c2ln&tailFAKE`).

### Phán quyết
**Sửa K-7, không thêm ca K-4a.** Lý do: phần đuôi là một phần của giá trị bí mật theo đúng K-4 đã phán, nên để lộ là lỗi thiết kế chứ không phải giới hạn cần chấp nhận (NFR-6); sửa ở một chỗ trong `redact.py` (ADR-034 QĐ 2); dùng lại đúng phần lặp của nhánh trần K-4 nên không có luật thứ hai để trôi lệch.

Thay `design-w0-fixes-3.md:167` (K-7) bằng:

> - **K-7.** Giá trị trần bắt đầu bằng `MASK` (đã che ở R-3) → giữ đúng một `MASK`, không che lần hai (không thành `[đã che] che]`). Nếu tên là bí mật (K-5): phần đuôi ngay sau `MASK` mà K-4 còn coi là thuộc giá trị trần (các cụm ký tự không phải khoảng trắng và không thuộc `, ; & " ' } ]`, cùng các dấu `, ; &` không thỏa (a), (b), (c) của K-4) bị bỏ, chỉ còn một `MASK`; quét tiếp ngay sau phần đuôi. Tên không bí mật → giữ nguyên `MASK` và phần sau nó, quét tiếp ngay sau `MASK` (như cũ). Phần đuôi đọc mỗi ký tự một lần rồi vị trí quét vượt qua nó, nên K-8 giữ.

K-4a **không đổi**. Văn bản tự do không có tên khóa (`sk-ant-FAKE&tail` → `[đã che]&tail`) vẫn do mẫu R-3 quyết định: không có tên khóa thì không có căn cứ coi phần sau `&` là một phần của bí mật; không đổi.

Lần theo luật mới (đọc, không chạy): `password=sk-ant-FAKE&tailFAKE` → R-3 rồi K-7, đuôi `&tailFAKE` (`&` không thỏa (a)(b)(c)) → `password=[đã che]`; `password=sk-ant-FAKE&amp;tailFAKE` → sau `&` là `amp;` (không phải `:`/`=`) → thuộc đuôi; sau `;` là `tailFAKE` rồi hết → thuộc đuôi → `password=[đã che]`; `password=sk-ant-FAKE&page=2` → sau `&` là `page=` → (c) → đuôi rỗng → `password=[đã che]&page=2`; `password=sk-ant-FAKE, tiếp` → (b) → `password=[đã che], tiếp`; `password=sk-ant-FAKE;` → (a) → `password=[đã che];`; `{password=sk-ant-FAKE}` → `}` không thuộc đuôi → `{password=[đã che]}`; `note=sk-ant-FAKE&tailFAKE` → tên không bí mật → `note=[đã che]&tailFAKE` (như cũ); `password=sk-ant-FAKE0000` → đuôi rỗng → như khẳng định cũ (`test_redact.py:230`).

Ngoài phạm vi, chỉ ghi nhận (không phán, không lộ): `password=x&sk-ant-FAKE` → R-3 cho `password=x&[đã che]`, nhánh trần K-4 đọc `x&[đã` (dừng ở khoảng trắng trong `MASK`) → `password=[đã che] che]`. Không lộ bí mật, chỉ xấu chữ; nếu cần sửa thì phải có phán riêng.

### Touchpoints
| File | Đổi |
|---|---|
| `erp_ai/agent/redact.py` | `_mask_key_values` nhánh `MASK` (`:75-78`); tách chuỗi phần lặp của nhánh trần `_KEY_VALUE` (`:41-43`) thành một mảnh dùng chung cho `_KEY_VALUE` và một mẫu riêng `_BARE_VALUE_TAIL`; docstring module thêm "K-7 as amended by `design-w1-fixes-2.md` point 3". |
| `erp_ai/agent/test_redact.py` | Hai test mới trong `TestRedact`. |

Không đường mới; không chạm `protected_paths`. Cả hai file đã có trong `files:` của T120 (đã merge).

### Khối task mới (tech-lead đặt số và tiêu đề; chèn trong `tasks-w1.md` ngay sau T120)

```
- [ ] T?? — Hàm che: phần đuôi sau giá trị đã che ở R-3 thuộc cùng giá trị trần (K-7) — files: erp_ai/agent/redact.py, erp_ai/agent/test_redact.py — test: erp_ai/agent/test_redact.py — depends: T120
  - Tiêu chí: NFR-6, AC-46, AC-50; ADR-034 QĐ 2; `review-120.md:45`; `design-w1-fixes-2.md` điểm 3 (K-7 mới). Chỉ sửa nhánh `MASK` của `_mask_key_values` và cách dựng `_KEY_VALUE`; không đổi `SECRET_PATTERNS`, `SECRET_WORDS`, `MASK`, `is_secret_key`, chữ ký `redact_secrets`, K-4a.
  - Receives: `redact.py` sau T120: `_KEY_CANDIDATE`, `_KEY_VALUE` (nhánh trần K-4 với nhìn trước (a)/(b)/(c)), `_mask_key_values`, `is_secret_key`, `MASK`.
  - Returns: không tên công khai mới. Mảnh chuỗi phần lặp của nhánh trần (cụm possessive `(?=(?P<chunk>…))(?P=chunk)` hoặc `[,;&]` với nhìn trước phủ định) dựng một lần, dùng cho cả `_KEY_VALUE` và `_BARE_VALUE_TAIL = re.compile(<mảnh>*)` (riêng tư). Trong `_mask_key_values`, khi `text.startswith(MASK, position)`: thêm `MASK`, `position += len(MASK)`; nếu `is_secret_key(candidate.group("name"))` thì `position = _BARE_VALUE_TAIL.match(text, position).end()` (bỏ phần đuôi); rồi `continue`. Tên không bí mật: như cũ.
  - Expect: `TestRedact::test_pattern_masked_value_tail_masked` (`password=sk-ant-FAKE&tailFAKE` → `password={MASK}`; `password=sk-ant-FAKE&amp;tailFAKE` → `password={MASK}`; `password=sk-ant-FAKE.tailFAKE` → `password={MASK}`; `pwd=sk-FAKE0000000000000000+tailFAKE` → `pwd={MASK}`; `token=eyJa.eyJb.c2ln&tailFAKE` → `token={MASK}`; mỗi ca kiểm thêm `"tailFAKE" not in` kết quả) đỏ trước (đuôi còn lộ) rồi xanh; `::test_pattern_masked_value_tail_stops_like_bare_value` (test ghim, xanh ngay là đúng, ghi lý do trong progress: `password=sk-ant-FAKE&page=2` → `password={MASK}&page=2`; `password=sk-ant-FAKE, tiếp` → `password={MASK}, tiếp`; `password=sk-ant-FAKE;` → `password={MASK};`; `{password=sk-ant-FAKE}` → `{{password={MASK}}}`; `note=sk-ant-FAKE&tailFAKE` → `note={MASK}&tailFAKE`; `api_key=sk-ant-FAKE&pwd=fake-z` → `api_key={MASK}&pwd={MASK}`); mọi test `TestRedact` cũ giữ xanh, gồm `test_value_patterns_run_before_key_scan`, `test_list_separator_*`, `test_long_run_without_secret_untouched`, `test_every_pattern_is_python_310_syntax`. `cmd.test_one` xanh cho `erp_ai/agent/test_redact.py` và `erp_ai/agent/test_knowledge.py`.
```

### Task phải chờ task này
Không có. `grep` trên `tasks.md`: không task chưa xong nào có `redact.py` hoặc `test_redact.py` trong `files:` (T120 đã xong). Task này độc lập với task của điểm 2 (khác file); hai task chạy song song được. Các nơi gọi `redact_secrets` (T91, T110, kênh email, Error Log) nhận luật mới mà không đổi mã.

---

## Tóm tắt

| Điểm | Phán | File mã | Task | Căn cứ |
|---|---|---|---|---|
| 1 | Giữ hai chữ cố ý: `"[đã ẩn]"` = ẩn trọn trường, `"[đã che]"` = che đoạn trong văn bản; thay chữ `U3.md:98` | không (test ghim gộp vào task điểm 2) | — | ADR-033 Ràng buộc, `review-84.md:33` |
| 2 | `reason` qua `redact_secrets` trong `action_entry`; Password bảng con = giới hạn đã chấp nhận | `run_log.py`, `test_run_log.py` | mới, `depends: T84`; T85, T91 chờ | STD-SEC-6, NFR-6, AC-10, ADR-034 QĐ 2 |
| 3 | Sửa K-7: bỏ phần đuôi giá trị trần sau `MASK` khi tên bí mật; K-4a không đổi | `redact.py`, `test_redact.py` | mới, `depends: T120`; không task nào chờ | NFR-6, AC-46, AC-50, ADR-034 QĐ 2 |

As-Built (writer): nghĩa hai chữ mặt nạ (điểm 1); giới hạn Password của hàng bảng con (điểm 2).

## Tóm tắt Explore
Không gọi Explore: các file cần đọc đã biết đường dẫn; đọc trực tiếp từng đoạn (danh sách ở đầu tài liệu) qua `git show team/FEAT-007:<path>` và `grep` trên `tasks.md`/`tasks-w1.md`. Không giả định nghiệp vụ nào; không câu hỏi cho analyst. Không chạy test hay `bench`: mọi lần theo ở điểm 3 là đọc mã.
