Feature: CHG-002
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:
<!-- Cổng: không có (team.py: CHG-002 planned 11/52, READY build). -->

# Design addendum 5 — CHG-002 (hẹp: T21, T31, bốn câu hỏi của reviewer)

Phạm vi: đúng sáu phán quyết dưới đây. Không đổi AC, không đổi NFR, không đổi phạm vi "Giữ vành đai an toàn". Không phán T9, T2 (design-addendum-4.md) và T5, T23 (arch-ruling-2.md). Không sửa `design.md`; câu của addendum này có hiệu lực **thay** những chỗ được dẫn, như các addendum trước.

Nguồn đã đọc (không Explore, theo lệnh giao): `tasks.md` T20–T33; `review-16.md`, `review-17.md`, `review-18.md`, `review-20.md`, `review-31.md`; `design.md` §3.2 dòng 316, §3.3, §3.6, §3.7 dòng 366–424, §4.4 dòng 559–581; `design-addendum-3.md` RQ-4 dòng 71–86, RQ-5 dòng 90–97; `f2fa5a1:erp_ai/agent/changes/result_comment.py:103-147`; `a6a6560:erp_ai/agent/change_text.py:107-200`; `a6a6560:erp_ai/agent/changes/transitions.py:236-262`; `a6a6560:erp_ai/agent/changes/test_block.py:120-135`; `a6a6560:erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:52-54`; `a6a6560:erp_ai/constants.py:32-33, 61, 80-83`.

Tên đã hứa với phiên FEAT-007 trong `design-addendum-3.md` giữ nguyên, không đổi chữ ký: `result_comment.post_restart_notice(name, action)`, tiền tố `kết quả đề xuất` chỉ cho comment kết quả, `result_lines(fields, *, doc=None)`, `block.is_block(doc)`, `ValueError` cho `change_kind` lạ ở `operations_of`/`commands_of`, thứ tự rẽ "FEAT-007 chèn nhánh của họ **trước**", các tên test `RC::TestRestartNotice::test_info_comment_session_user_not_result_prefix`, `AB::TestRestart::test_no_restart_in_list_zero_notice_comment`, `ARCH::TestChangeBlockRules::test_restart_notice_single_call_site`.

## Assumptions decided by the team
- A5-1. `restart_sent_at` là trường Datetime của Frappe, lưu **không múi giờ** theo giờ hệ thống (`now_datetime()` ở §4.4 bước 2; A-6 của T23). Đọc từ DB ra `datetime.datetime`; trong dict của test có thể là chuỗi ISO.
- A5-2. `restart_status` là trường Select bốn giá trị (`constants.py:80-83`). Giá trị ngoài bốn giá trị đó chỉ có khi ai đó ghi thẳng vào DB, tức là dữ liệu hỏng, không phải một trạng thái.
- A5-3. Khối chỉ có lệnh có `change_kind = Lệnh bench` (T28), nên `request_undo` từ chối nó ngay dòng đầu (`transitions.py:248-249`): job hoàn tác không bao giờ tới §4.4 với khối đó.
- A5-4. `proposal_notes` được `propose_change._comment` gọi lúc đề xuất, khi `restart_status` còn rỗng, nên nhãn restart chỉ hiện trên form (T30 không đổi chữ).

---

## P-1. T21: nhãn restart trên form

**Câu thiết kế mới** (thay bảng "Nhãn trên form", `design.md` dòng 416–423; chữ bốn nhãn giữ nguyên, chỉ thêm luật):

1. **Chỗ đứng:** nhãn là **dòng cuối cùng** của danh sách `proposal_notes` trả về, sau mọi dòng khác (sau dòng 1–6 của §3.7, sau `Commit áp dụng: …` / `Commit hoàn tác: …`, sau câu `.py` của dạng cũ). Luật không phụ thuộc dạng khối hay dạng cũ: chỉ nhìn `restart_status`. `restart_status` rỗng (`None` hoặc `""`) → không thêm dòng nào; đầu ra trùng từng byte với `e6cda3e`.
2. **Chữ chính xác** (hằng mô-đun trong `change_text.py`, đọc bằng `RESTART_STATUS_*` của `constants.py`):

| `restart_status` | Dòng thêm |
|---|---|
| `Đã gửi`, `restart_sent_at` có giá trị | `Restart: đã gửi lúc {giờ}, chờ xác nhận.` |
| `Đã gửi`, `restart_sent_at` rỗng | `Restart: đã gửi, chờ xác nhận.` |
| `Đã xác nhận` | `Restart: đã xác nhận, web và worker đã khởi động lại.` |
| `Chưa xác nhận` | `Restart: chưa xác nhận (có thể chưa được cấp quyền restart). Việc người còn phải làm: restart bench.` |
| `Lỗi khởi chạy` | `Restart: lỗi khởi chạy. Việc người còn phải làm: restart bench.` |
| giá trị khác | `ValueError(f"restart_status không hỗ trợ: {value!r}")` |

3. **`{giờ}`:** `restart_sent_at.strftime("%H:%M %d/%m/%Y")`, ví dụ `Restart: đã gửi lúc 14:05 15/11/2026, chờ xác nhận.`
   - Kiểu đầu vào nhận: `datetime.datetime` không múi giờ, hoặc `str` đọc bằng `datetime.datetime.fromisoformat` (dạng Frappe `YYYY-MM-DD HH:MM:SS[.ffffff]`).
   - Múi giờ: **không đổi**. Giá trị đã là giờ hệ thống (A5-1), hiện nguyên giờ đồng hồ đó; không thêm hậu tố múi giờ. `change_text.py` vẫn là mô-đun thuần (thư viện chuẩn và `erp_ai.constants`), không gọi `frappe.utils`.
   - `datetime` **có** `tzinfo`, chuỗi không đọc được, hay kiểu khác → `ValueError` (A-6: không trộn mốc có và không có múi giờ).
4. **`Đã gửi` mà `restart_sent_at` rỗng:** dòng không có giờ (bảng trên), **không** ném lỗi. `record_restart` đã từ chối `sent_at` không phải datetime (`transitions.py` T17), nên ca này chỉ là dữ liệu cũ hoặc sửa tay; nhãn vẫn nói đúng sự thật đã biết.
5. **`restart_status` lạ:** ném `ValueError` như `_stored_commands` (cùng luật STD-ERR-1 mà `review-20.md` vòng 1 đã chấm major khi nuốt `command_list` hỏng). Form vẫn mở nhờ P-5.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Dòng cuối của `proposal_notes`, một luật cho mọi dạng | Nhãn nói việc **sau** áp dụng, đứng sau dòng commit là đúng trình tự đọc; không chen vào thứ tự 1–7 mà T20 và T30 đã ghim | (a) dòng đầu tiên cho nổi bật; (b) trường onload riêng `restart_label` | Đổi sang (b): bỏ dòng cuối, thêm `set_onload("restart_label", …)` ở T22; tên test T21 giữ, assertion đổi chỗ đọc |
| `%H:%M %d/%m/%Y`, giờ hệ thống không đổi | Thời hạn tính bằng phút (`RESTART_TIMEOUT_S//60`); thứ tự ngày/tháng của người đọc tiếng Việt; mô-đun thuần không có múi giờ hệ thống để đổi | `frappe.utils.format_datetime` theo định dạng người dùng | Chuyển việc định dạng sang controller (T22) rồi truyền chuỗi vào; test T21 đổi đầu vào |
| `Đã gửi` thiếu giờ → bỏ phần giờ; trạng thái lạ → `ValueError` | Thiếu giờ vẫn là trạng thái hợp lệ và có ích cho người; trạng thái lạ là dữ liệu hỏng, im lặng thì người tưởng không có restart | Bỏ qua trạng thái lạ (không thêm dòng) | Đổi `ValueError` thành "không thêm dòng" + logger ở T22; một test T21 đổi tên thành `test_unknown_status_no_label` |

**Test (T21, `erp_ai/agent/test_change_text.py`):** `TestRestartLabel::test_four_values_exact_text`, `test_unconfirmed_says_permission_may_be_missing_and_todo_restart`, `test_empty_status_no_label` (đã có trong tasks.md) và thêm `test_label_is_last_line` (khối có lệnh, dạng cũ `.py`, `Đã áp dụng` có commit: nhãn là phần tử cuối), `test_sent_time_from_datetime_and_iso_string` (cùng giờ ra cùng `14:05 15/11/2026`), `test_sent_without_time_drops_time_part`, `test_aware_or_bad_sent_at_raises_value_error`, `test_unknown_status_raises_value_error`.

---

## P-2. T31: comment trước restart khi không có commit

**Câu thiết kế mới** (thêm sau `design.md` dòng 400):

`restart_notice_text(fields, action)` chọn mẫu theo **sha của hành động** (`apply_commit_sha` khi `action = "apply"`, `undo_commit_sha` khi `"undo"`):
- sha có giá trị → mẫu hiện có, đúng từng chữ (dòng 400).
- sha rỗng (`None` hoặc `""`) → mẫu không commit, **không** nêu commit, nhánh, app hay lệnh `git`:

> Đề xuất {tên} đã áp dụng. Hệ thống sắp restart bench. Nếu site không lên sau vài phút: trên máy chủ chạy `bench restart`.

> Đề xuất {tên} đã hoàn tác. Hệ thống sắp restart bench. Nếu site không lên sau vài phút: trên máy chủ chạy `bench restart`.

- Mẫu hoàn tác không commit không xảy ra ở đường thật (A5-3); nó có để hàm thuần không bao giờ ra `None` hay `apps/None`. `action` lạ vẫn `KeyError` như hôm nay.
- `NOTICE_FIELDS` không đổi (không đọc thêm `command_list`, không đọc `upstream_ref`). Chữ vẫn qua `escape_html`; không mở đầu bằng `kết quả đề xuất`.

**Sửa câu A3 RQ-4** (`design-addendum-3.md` dòng 76 và 84, và dòng "Thêm theo A3 RQ-4" của T31): thay "Không gọi `frappe.set_user`, `frappe.publish_realtime`, không phát sự kiện `new_comment`" và "`frappe.set_user` và `frappe.publish_realtime` (patch) 0 lần gọi" bằng:

> 0 lời gọi `frappe.set_user`, `frappe.publish_realtime` và `new_comment` của riêng hàm; sự kiện realtime duy nhất là `doc_update` và `list_update` mà Frappe phát khi `insert` Comment mới (`Document.notify_update`), đúng như `post_result` (`test_post_result_publishes_no_realtime`).

Luật AST của T49 (`result_comment.py` có 0 lần `publish_realtime`) đã mang đúng nghĩa "của riêng nó", không đổi.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Chọn mẫu theo sha rỗng; mẫu không commit chỉ gợi ý `bench restart` | Không có commit thì không có gì để `revert`; luật dựa trên dữ liệu thật của hàm, không thêm trường; giữ chữ ký đã hứa với FEAT-007 | (a) nêu `{m} lệnh bench` như gợi ý của reviewer, phải đọc thêm `command_list`; (b) khối chỉ có lệnh không gửi notice | (a): thêm `command_list` vào `NOTICE_FIELDS`, chữ thêm `: {m} lệnh bench`; (b): T38 bỏ gọi khi không có mục file, nới `test_restart_notice_single_call_site` |
| Sửa chữ RQ-4 thành "của riêng hàm" | "0 lần" theo nghĩa đen không đạt được ở Frappe 15 (`review-31.md` dòng 25) | Tắt `notify_update` cho Comment | Không có hoàn tác cần thiết: chỉ là câu chữ |

---

## P-3. Câu hỏi review-16: cạnh hoàn tác từ `Đã áp dụng` có so `CHANGE_KIND_CODE` không

**Chọn: có.** Câu thiết kế mới (thay §3.6 dòng 351 và §3.3 hàng `undo`): `request_undo` nhận **chỉ** `change_kind = CHANGE_KIND_CODE` cho **cả hai** cạnh (`Đã áp dụng` và `Lỗi` có commit). Thứ tự kiểm sau `_lock`:
1. `change_kind == CHANGE_KIND_COMMAND` → `Lệnh bench không hoàn tác được` (như hôm nay).
2. `change_kind != CHANGE_KIND_CODE` → `_refuse(row.change_status, "hoàn tác")`, tức câu có sẵn `Đề xuất đang ở trạng thái {status}, không hoàn tác được`, `InvalidTransition`, không ghi gì.
3. Hai cạnh như hôm nay.

FEAT-007 cần hoàn tác cho loại bản ghi của họ (ADR-031 QĐ 6) thì chèn nhánh của họ **trước** bước 2, cùng cách G-10 của A3 RQ-5. CHG-002 không viết nhánh đó.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Danh sách cho phép `== CHANGE_KIND_CODE` ở cả hai cạnh | Cùng luật với A3 RQ-5 (đường code chỉ nhận hai loại đã biết); job hoàn tác (§4.3) chỉ biết hoàn tác file và commit, một loại khác tới đó là sai | Giữ `!= COMMAND` và để FEAT-007 tự chặn | Bỏ bước 2; xóa test mới; test cũ không đổi |

**Test:** `erp_ai/agent/changes/test_transitions.py` `TestRequestUndo::test_request_undo_refused_for_other_kind_when_applied` (loại thứ ba ở `Đã áp dụng` → `InvalidTransition`, trạng thái và `undo_by` không đổi). `test_request_undo_refused_for_code_outside_applied` giữ tên (deferred 1 của review-16 tùy tech-lead).

---

## P-4. Câu hỏi review-17: `confirm_restart` nhận `sent_at`

**Chọn: có.** Câu thiết kế mới (thay §3.6 dòng 361–363):

- `transitions.confirm_restart(name, value, *, sent_at) -> bool`, `sent_at` là tham số **chỉ từ khóa, bắt buộc**.
- Dưới cùng một `_lock`: ghi khi và chỉ khi `restart_status = Đã gửi` **và** `get_datetime(row.restart_sent_at) == get_datetime(sent_at)`. Khác → trả `False`, không ghi gì. `sent_at` rỗng → `ValueError` (như `record_restart`).
- `_lock` đọc thêm `restart_sent_at` nếu chưa đọc.
- T24: `confirm_restart` của controller đọc `restart_status` và `restart_sent_at` **một lần**, tính `outcome` bằng đúng `restart_sent_at` đó, rồi truyền nguyên giá trị đã đọc vào `sent_at=`. `False` → trả `restart_status` đọc lại, không lỗi, không ghi logger kết luận.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| So `sent_at` dưới khóa (ghi có điều kiện) | Khe giữa lúc đọc bằng chứng và lúc ghi là có thật khi job hoàn tác ghi `record_restart` mới; cùng kiểu "có điều kiện, một bên thắng" của §3.6 | (a) nhận khe; (b) khóa dòng từ lúc đọc tới lúc ghi trong controller | (a): bỏ tham số, xóa hai test mới; (b): chuyển việc đọc vào trong `transitions` |

**Test:** `test_transitions.py` `TestConfirmRestart::test_stale_sent_at_writes_nothing`, `test_missing_sent_at_raises_value_error`; các test `TestConfirmRestart` hiện có đổi lời gọi sang `sent_at=` (chỉ thêm đối số, không đổi assertion). T24: `TestConfirmRestart::test_passes_sent_at_it_read`, `test_resent_between_read_and_write_keeps_new_status`.

---

## P-5. Câu hỏi review-20: `onload` khi `command_list` hỏng

**Chọn: form vẫn mở.** Câu thiết kế mới (thêm vào §3.7 sau "Nhãn trên form"):

`ERPAIChangeProposal.onload` gọi `change_text.proposal_notes(self)` trong `try … except ValueError`. Khi bắt được:
- `change_notes` = đúng một dòng: `Không đọc được nội dung đã lưu của đề xuất này (dữ liệu hỏng); báo quản trị trước khi duyệt.`
- `frappe.logger("erp_ai").warning("erp_ai notes proposal=%s error=%s", self.name, type(exc).__name__)` (logger tệp, không ghi DB trong request đọc).
- Không bắt lớp lỗi nào khác. Nút và quyền trên form không đổi: duyệt rồi áp dụng vẫn bị bộ chặn lúc áp dụng (T33) từ chối; người vẫn bấm được `Từ chối`.
- `proposal_notes` vẫn chặt (giữ sửa vòng 2 của T20); comment lúc đề xuất không đổi.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| Bắt `ValueError` ở `onload`, một dòng cảnh báo + logger | Form không mở thì người không từ chối được bản ghi hỏng; lỗi vẫn được ghi (STD-ERR-1) và vẫn hiện cho người | (a) để form ném lỗi; (b) `proposal_notes` tự nuốt lỗi | Bỏ `try`; xóa test T22 mới |

**Test (T22):** `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py` `TestERPAIChangeProposal::test_onload_unreadable_notes_opens_with_one_warning_line` (hai ca: `command_list` không phải list argv; `restart_status` lạ; logger được gọi đúng 1 lần, không có Error Log mới).

---

## P-6. Câu hỏi review-18: mục `Sửa` đường dẫn rỗng của dạng cũ bị chặn ở đâu

**Chọn: ở bộ chặn, không ở bộ chuyển đổi.** `block.operations_of` giữ hành vi ghim ở `test_block.py:120` (không bịa đường dẫn, `path = ""`). Câu thiết kế mới (thêm vào `design.md` dòng 304, bước "hình dạng"): mục có `path` không phải chuỗi khác rỗng (sau `strip()`), hoặc mục `Đổi tên` có `new_path` như vậy → từ chối bằng lý do hình dạng mục của `check_block` (cùng hằng T14 dùng cho mục sai hình dạng), ở **cả hai** thời điểm (`at_apply=False` và `True`). Lúc áp dụng (T33) lý do này làm job kết thúc `Lỗi` trước mọi lần ghi file.

| Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|
| `check_block` bước 2 chặn đường dẫn rỗng | Một cổng chặn duy nhất cho mọi dạng (§3.2 "gọi ở cả hai thời điểm"); bộ chuyển đổi chỉ đọc | `operations_of` ném `ValueError` khi `file_path` rỗng | Thêm `ValueError` vào `operations_of`, đổi `test_legacy_edit_empty_contents_and_path` thành test ném lỗi |

**Test:** T14 `test_change_guard.py` thêm `test_empty_path_item_refused` (cả `at_apply` False/True); T33 thêm `test_legacy_edit_empty_path_refused_at_apply_zero_writes`. `test_block.py::test_legacy_edit_empty_contents_and_path` giữ nguyên.

---

## Việc dev phải sửa trên f2fa5a1 (nhánh `team/CHG-002-task-31`)
1. `result_comment.py:121-130` `restart_notice_text`: sha của hành động rỗng → trả mẫu không commit của P-2 (đúng hai câu ở trên, theo `verb`); sha có → chữ hiện có, không đổi một ký tự. Không đọc `app`, nhánh khi sha rỗng. Docstring nêu hai mẫu.
2. `test_result_comment.py` thêm: `TestRestartNotice::test_command_only_apply_notice_has_no_commit_branch_app` (`apply_commit_sha` rỗng, `applied_branch`, `target_branch`, `app` là `None`: chữ đúng từng ký tự, không chứa `None`, `commit`, `git -C`, `apps/`), `test_undo_without_commit_notice_text`.
3. `test_info_comment_session_user_not_result_prefix`: giữ assertion hiện có (danh sách lời gọi realtime đúng bằng `doc_update` và `list_update`), chỉ sửa docstring/chú thích theo câu RQ-4 mới.
4. Không đổi `NOTICE_FIELDS`, chữ ký `post_restart_notice(name, action)`, cách ghi `add_comment(COMMENT_TYPE_INFO, text)`. Ba điểm deferred của `review-31.md`: tùy dev, không bắt buộc.
5. RED trước: hai test mới đỏ trên `f2fa5a1` (chữ chứa `None`), rồi GREEN bằng `cmd.test_one` với `erp_ai/agent/changes/test_result_comment.py`.

## tasks.md đổi gì (tech-lead ghi; designer không sửa tasks.md)

| Phán quyết | Task nhận | Returns / Receives đổi | Expect thêm |
|---|---|---|---|
| P-1 | T21 | Returns: nhãn là dòng cuối của `proposal_notes`; năm dòng chữ của bảng P-1; `{giờ}` = `%H:%M %d/%m/%Y` từ `datetime` không múi giờ hoặc chuỗi ISO; `Đã gửi` không giờ → bỏ phần giờ; giá trị lạ, `tzinfo`, chuỗi hỏng → `ValueError` | `test_label_is_last_line`, `test_sent_time_from_datetime_and_iso_string`, `test_sent_without_time_drops_time_part`, `test_aware_or_bad_sent_at_raises_value_error`, `test_unknown_status_raises_value_error` |
| P-1, P-5 | T22 | Returns thêm: `onload` bắt `ValueError` của `proposal_notes` → một dòng cảnh báo P-5 + logger `erp_ai notes proposal=%s error=%s` | `TestERPAIChangeProposal::test_onload_unreadable_notes_opens_with_one_warning_line` |
| P-1 | T25 | Receives: nhãn ở phần tử cuối của `change_notes`; không đổi Returns | (không thêm) |
| P-2 | T31 | Returns thêm: sha rỗng → mẫu không commit P-2; dòng "Thêm theo A3 RQ-4" đổi thành câu RQ-4 mới | `TestRestartNotice::test_command_only_apply_notice_has_no_commit_branch_app`, `test_undo_without_commit_notice_text` |
| P-2 | T38 | Không đổi Returns; khối chỉ có lệnh `["restart"]` vẫn gọi notice đúng 1 lần | (không thêm; tùy tech-lead thêm `AB::TestRestart::test_command_only_block_notice_without_commit`) |
| P-2 | T49 | Câu luật AST đọc là "0 lời gọi của riêng `result_comment.py`"; không đổi test | (không thêm) |
| P-3, P-4 | `transitions.py` (T16, T17 đã tick): tech-lead chọn mở lại hoặc chèn task (`/team:plan --insert`); phải xong **trước** T24 | `request_undo`: bước 2 của P-3; `confirm_restart(name, value, *, sent_at)` của P-4 | `TestRequestUndo::test_request_undo_refused_for_other_kind_when_applied`, `TestConfirmRestart::test_stale_sent_at_writes_nothing`, `test_missing_sent_at_raises_value_error` |
| P-4 | T24 | Receives: `transitions.confirm_restart(name, value, *, sent_at)`; Returns: đọc `restart_sent_at` một lần, tính `outcome` bằng nó, truyền nó vào `sent_at=`; `False` → trả trạng thái đọc lại | `TestConfirmRestart::test_passes_sent_at_it_read`, `test_resent_between_read_and_write_keeps_new_status` |
| P-6 | T14 | Returns thêm: bước "hình dạng" chặn `path`/`new_path` rỗng ở cả hai thời điểm | `test_empty_path_item_refused` |
| P-6 | T33 | Expect thêm ca dạng cũ `Sửa` đường dẫn rỗng | `test_legacy_edit_empty_path_refused_at_apply_zero_writes` |

## Đối chiếu AC/NFR và test plan
- AC của spec (đối tượng CHG-002): AC-35, AC-36, AC-37, AC-38, AC-39, AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50, AC-51, AC-52, AC-53, AC-54, AC-55, AC-56 (22). NFR: NFR-12, NFR-13, NFR-14, NFR-15 (4).
- Addendum này **không xóa và không đổi tên** test nào của `design.md` §8 và addendum 1–3; chỉ thêm test. Nên 22/22 AC và 4/4 NFR vẫn có ≥ 1 dòng `file::name` như trước.
- AC chạm tới và test thêm: AC-45, AC-46 (c) ← P-1 (T21), P-4 (T24 + transitions); AC-46 (b) ← P-2 (T31); AC-42 ← P-3 (`test_transitions.py`); AC-48, AC-54 ← P-5 (T22); AC-36, AC-44 ← P-6 (T14, T33); AC-55 ← P-4 (T24 giữ `_decider` đầu tiên, không đổi).

## Touchpoints (đường dẫn có sẵn, không tạo file mới)
`erp_ai/agent/change_text.py`, `erp_ai/agent/test_change_text.py`, `erp_ai/agent/changes/result_comment.py`, `erp_ai/agent/changes/test_result_comment.py`, `erp_ai/agent/changes/transitions.py`, `erp_ai/agent/changes/test_transitions.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, và file của T14/T33 đã có trong tasks.md. 0 file mới, nên không có so sánh `allowed_new_file_roots`; không file nào thuộc `protected_paths` (không đụng secrets, cấu hình site).
