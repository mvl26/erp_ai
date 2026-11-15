Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ G5). Để trống. -->

# Phán quyết kiến trúc: comment kết quả theo nhánh A (CHG-001), câu L-1 của ADR-035, FEAT-007

**Phán quyết tổng: nhánh A được nhận. U7a dùng lại `result_comment.post_result(proposal_name)` của FEAT-004 nguyên chữ ký, chỉ thêm chữ cho loại bản ghi và cho `Đã từ chối`. Comment sau Từ chối không còn đi qua job: nó là dòng `Info` ghi ngay trong request Từ chối, dưới người từ chối.**
- ADR-035 đã sửa (vẫn `proposed`): QĐ 6 viết lại, có câu L-1 ở dạng cấu trúc; thêm QĐ 7 (dòng `Info` dưới người thực hiện là ngoại lệ có tên của ADR-033 QĐ 1). Không ADR mới. ADR-033 không sửa chữ: ngoại lệ nằm ở ADR-035, người duyệt hai ADR cùng lượt.
- Không mở vòng design thứ ba. Mục 4 là danh sách điều kiện B-0..B-16 cho plan đợt 2; mục 6 kê từng đoạn của hai file sửa U7a không còn hiệu lực. Ở chỗ khác nhau, file này thắng `design-addendum-2-U7a-fixes.md`, `design-addendum-2-U7a-fixes-2.md` và `arch-review-design-w2b-r2.md`.

## Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Nhánh A trông thế nào | `post_result(proposal_name) -> str \| None`, một lời gọi trong `apply_job.run_change` sau trạng thái cuối đã commit, `add_comment("Info", …)` dưới user phiên của job, không `set_user`; dòng 1 `kết quả đề xuất {name} ({đích}): {change_status}`; đích chỉ có dạng code và lệnh; chỉ lý do được che | `docs/team/features/CHG-001/design.md:16-18`, `:29-39` |
| Ai đọc dòng `Info` | Không `handlers.comment_after_insert` (bước 0), không `ticket_comment_filters`, không realtime, không chốt `is_agent` | CHG-001 `design.md:13`, `:18` |
| Từ chối hôm nay | `reject` controller: `_decider` → `transitions.reject`, không job | `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:114-117` |
| Từ chối chỉ thắng một lần | `transitions.reject` → `_decide(…, CHANGE_STATUS_REJECTED, …)`; cùng đường khóa dòng và phép chuyển có điều kiện của `approve` (ADR-012 QĐ 3) | `erp_ai/agent/changes/transitions.py:183-185` |
| Test FEAT-004 đếm job khi Từ chối | `develop`: `test_change_decision.py:79` `test_reject_link_rejects_without_a_job`; không test nào có tên chứa `reject` khẳng định số comment (`grep` trên `test_change_decision.py`, `test_erp_ai_change_proposal.py`) | `develop` |
| Phép kiểm lại M2 của ADR-023 | Đầu `_run`, cho áp dụng và hoàn tác: người thực hiện "vẫn có `ERP AI Instructor`" | `docs/team/adr/ADR-023.md:36` |
| AC của FEAT-007 | AC-23 "đúng 1 comment trên phiếu" mỗi kết cục; AC-33 "Sau Từ chối: không ghi, có log và comment"; AC-39 "comment kết quả hiện trên trang phiếu", kiểm có đầu ra trên site dev | `spec.md:185`, `:199`, `:205` |

## 1. Câu L-1 vào ADR-035 QĐ 6

Câu L-1 xin ở `arch-review-design-w2b-r2.md:183` giả định có một job Từ chối. Dưới nhánh A, job đó không còn lý do tồn tại (mục 2), nên câu được viết ở dạng cấu trúc. ADR-035 QĐ 6 nay chứa nguyên văn:

> "Từ chối không xếp job nào, nên phép kiểm lại người duyệt của ADR-023 (đầu `_run` của job) không bao giờ chạy cho Từ chối, và không job nào được rẽ nhánh theo trạng thái `Đã từ chối`."

Nội dung L-1 giữ: người từ chối là agent Helpdesk được giao, hoặc Instructor bị thu role, vẫn có comment, và `Đã từ chối` không bao giờ bị đẩy sang `Lỗi`. Bây giờ điều đó đúng vì không có job, không nhờ thứ tự các bước trong job.

## 2. Comment sau Từ chối: vì sao rời job

QĐ 6 bản trước đưa comment vào job vì đúng một lý do: ghi dưới tài khoản agent mà không `set_user` trong request. CHG-001 đã chốt dòng kết quả ghi dưới người thực hiện, không chuyển phiên. Nếu giữ job, job đó cũng chạy dưới người từ chối (user đã xếp nó), nên `owner` y hệt. Cái giữ lại chỉ là chi phí: một trường `rejection_comment_posted`, một migration, một job mỗi lần Từ chối, nhánh trước M2 (L-1), và hai test FEAT-004 phải sửa (L-2, phán quyết (1)). Ghi trong request cho cùng `owner`, chỉ một lần nhờ phép chuyển, dòng có ngay khi request trả về (tốt cho AC-39), và giữ test "Từ chối → 0 job" của FEAT-004. STD-DESIGN-5.

## 3. Nhánh A có đáp ứng AC và ADR không

| Mục | Đáp ứng? | Điều kiện / câu phải đổi |
|---|---|---|
| FEAT-007 AC-23 (đúng 1 comment mỗi kết cục) | **Có**, nếu dòng `Info` được đếm là "comment kết quả" và kết cục không có comment thứ hai | B-6, B-10 |
| FEAT-007 AC-33 (sau Duyệt 1 comment kết quả; sau Từ chối có log và comment) | **Có**: log = dòng `reject` của `transitions`; comment = dòng `Info` trong request | B-7, B-8 |
| FEAT-007 AC-39 (comment kết quả hiện trên trang phiếu) | **Có điều kiện**: theo mã nguồn, `TicketTimeline.vue:318` vẽ subtype `info`, nhưng chưa ai thấy trên trang thật (A-D1). `Info` không phát realtime, nên dòng của job chỉ hiện khi tải lại | B-0, B-13, mục 7 |
| ADR-033 QĐ 1 ("mọi ghi … comment phiếu … dưới tài khoản agent") | **Không**, theo chữ | Ngoại lệ có tên ở ADR-035 QĐ 7: chỉ dòng `Info` của `post_result`. Câu ADR-033 bị thu hẹp: QĐ 1 câu 1 và Ràng buộc cuối ("Comment, trạng thái, trả lời do app tạo có `owner` = tài khoản agent") |
| ADR-033 QĐ 7 (bảng chủ ghi) | Thiếu hàng | ADR-035 QĐ 7 thêm hàng "Dòng kết quả đề xuất (`Comment` `Info`) \| `post_result`, từ `run_change` và `reject` \| người thực hiện". Hàng này cũng trả lời A-D2 của CHG-001 |
| ADR-033 QĐ 5 (đơn vị nhật ký = mục hành động) | Có. Dòng `Info` không phải ghi của bot, không cần mục hành động | — |
| ADR-035 QĐ 6 | Bản trước **không** khớp (job, tài khoản agent) | Đã viết lại (mục 1, 2) |
| ADR-031 QĐ 3 (cùng comment kết quả của FEAT-004 AC-28) | Có, một bộ dựng | B-2 |
| ADR-013 QĐ 1, Ràng buộc (job không `set_user`, không realtime) | Có | B-2, B-7 |
| ADR-010 QĐ 3, ADR-017 (tác giả = `owner`) | Có: `owner` là người thật | — |
| NFR-8 | Có điều kiện: CHG-001 chỉ che lý do; đích loại bản ghi có thể là email (`User` tên = email) | B-3, B-12 |

## 4. Điều kiện nhánh A cho plan đợt 2 (tech-lead chép nguyên chữ vào task U7a, U7b)

- **B-0 Kiểm A-D1 sớm.** Trước khi task comment kết quả của U7a bắt đầu: trên site dev `miyano`, sau khi FEAT-004 (T56, T57) merge, duyệt một đề xuất code, tải lại trang phiếu Helpdesk và dán ảnh có dòng `kết quả đề xuất …`. Không thấy → `STOP` cho team-leader (mục 7), U7a không làm đường vòng.
- **B-1 Thứ tự.** Task U7a này bắt đầu khi `team/FEAT-004` có T56, T57 đã vào `develop` và `team/FEAT-007` đã rebase. Đầu task: `grep -c "def post_result" erp_ai/agent/changes/result_comment.py` = 1. Khác 1 → `DESIGN_CONFLICT`. U7a không tạo `result_comment.py`.
- **B-2 Một bộ dựng, một chữ ký.** U7a gọi `result_comment.post_result(proposal_name)` với `str`. Không đổi chữ ký, `COMMENT_TYPE_INFO`, `TITLE_RESULT_COMMENT_FAILED`, phép nối `"; "`, `escape_html`. Không thêm bộ dựng hay hằng `MASK`, `COMMIT_SHORT_LEN`, `RESULT_STATUSES` riêng của U7a.
- **B-3 Đích loại bản ghi.** Trong `result_lines`: `change_kind == CHANGE_KIND_RECORD` → đích = `{catalog_action} trên {target_doctype} {target_name}`. Đọc thêm đúng ba trường `catalog_action`, `target_doctype`, `target_name`. `target_name` đi qua **cùng** hàm che của lý do (từ chứa `@` hoặc `://` → `[đã ẩn]`). Không có dòng `Việc: …` riêng.
- **B-4 Dòng 2 của loại bản ghi.**
  - `Đã áp dụng` → không có dòng 2.
  - `Đã hoàn tác` → không có dòng 2 (không có `undo_commit_sha`).
  - `Lỗi`, `Hết hiệu lực` → đúng quy tắc CHG-001 (lý do đã che; tiền tố `khi hoàn tác, ` khi có `undo_by`).
  - Không dòng nào in `commit` với giá trị rỗng.
- **B-5 `Đã từ chối`.** Thêm vào tập trạng thái hợp lệ của `result_lines`. Chỉ dòng 1, mọi loại. Không đọc `failure_reason`. Trạng thái ngoài tập vẫn → `ValueError`.
- **B-6 `apply_job.py`.** U7a thêm **0** lời gọi `post_result`. Bốn kết cục của `_run_record` phải đi tới lời gọi duy nhất trong `run_change`. Nếu đường bản ghi không trả qua `run_change`, sửa đường đó cho trả qua, không thêm lời gọi. `_run_record` và `catalog_tools._post_comment` không đăng comment kết quả nào.
- **B-7 `reject` của controller.** Thứ tự đúng: `user = _decider(name)` → `status = transitions.reject(name, user)` → `result_comment.post_result(name)` → trả `{"name": name, "status": status}`. Không `enqueue`, không `try` quanh `post_result`, không `set_user`, `agent_session`, `enter_agent_session`. Ba đường Từ chối (form, liên kết có chữ ký qua `change_decision`, ngăn qua `decide_proposal`) đều tới hàm này; U7a không sửa `change_decision.py`.
- **B-8 Không trường, không job.** Không trường `rejection_comment_posted`, không `claim_rejection_comment`, không sửa `STATE_FIELDS`, không nhánh `Đã từ chối` trong `apply_job.py`, không `cmd.migrate` cho comment Từ chối. Chỉ một lần = phép chuyển `Chờ duyệt → Đã từ chối`.
- **B-9 `owner`.** Mọi khẳng định về dòng kết quả: `comment_type == "Info"`, `owner` = `decided_by` (áp dụng, lỗi, hết hiệu lực), `undo_by` (hoàn tác, lỗi khi hoàn tác), người từ chối (`Đã từ chối`). Không khẳng định `owner == AGENT_USER` cho dòng kết quả.
- **B-10 Cách đếm AC-23.** "1 comment kết quả" = +1 `Comment` có `reference_doctype = "HD Ticket"`, `reference_name` = phiếu, `comment_type = "Info"`, `content` chứa tên đề xuất; **và** +0 `Comment` loại `"Comment"` do app tạo cho cùng kết cục. Ma trận 9 tình huống của AC-23 dùng đúng định nghĩa này cho hàng "kết quả áp dụng đề xuất"; các hàng khác vẫn đếm `Comment` loại `"Comment"`, `owner = AGENT_USER`.
- **B-11 Không thành chỉ thị.** Ca Từ chối bởi người có `ERP AI Instructor`, đề xuất có từ khóa gọi bot trong đích: 0 job agent; dòng không có trong `fetch_ticket_comments`; `latest_instructor` không đổi.
- **B-12 NFR-8.** Đề xuất `catalog_create_user` có `target_name = real.person@example.com`, lý do có `https://x-token-FAKE@host/repo`: 0 lần `real.person@`, `FAKE`, `://` trong `content`, mỗi trạng thái của B-4, B-5.
- **B-13 AC-39 kiểm có đầu ra.** Trên site dev: một đề xuất bản ghi `Cần duyệt`; Duyệt → chờ job → tải lại trang phiếu → ảnh có dòng kết quả; một đề xuất khác Từ chối → ảnh có dòng ngay sau thao tác. Dán ảnh và dòng logger `comment=`.
- **B-14 U7b.** `decide_proposal` với Từ chối gọi `reject` của controller; 0 job; ngăn tải lại dữ liệu sau thao tác. Không `publish_realtime` cho dòng kết quả.
- **B-15 Touchpoint U7a cho phần này.** Sửa: `erp_ai/agent/changes/result_comment.py`, `erp_ai/agent/changes/test_result_comment.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` (`reject`), test của controller, `erp_ai/agent/changes/test_apply_job.py`, `erp_ai/tests/test_architecture.py`. Không chạm vì phần này: `transitions.py`, `test_transitions.py`, `queue.py`, `change_decision.py`, `test_change_decision.py`, JSON đề xuất.
- **B-16 Test FEAT-004.** `test_reject_link_rejects_without_a_job` (`develop` `:79`) và `test_post_reject_zero_jobs` (`team/FEAT-004` `:239`) giữ nguyên và phải xanh. Nếu sau rebase có test FEAT-004 khẳng định 0 comment sau Từ chối: chỉ assertion đó đổi thành +1 dòng `Info` (STD-TEST-5, AC-33), kèm danh sách `grep` trong báo cáo task và một dòng journal FEAT-007.

**Dòng test U7a cho phần này** (thay mọi dòng kê ở mục 6; không dòng nào có điều kiện):

| AC / ràng buộc | Test |
|---|---|
| AC-33, AC-28 chữ | `TRC::TestResultLines::test_lines_for_each_final_status` (test của CHG-001) thêm subTest: bản ghi × {`Đã áp dụng`, `Lỗi`, `Hết hiệu lực`, `Đã hoàn tác`}; `Đã từ chối` × {code, lệnh, bản ghi} |
| NFR-8 | `TRC::TestResultLines::test_record_target_and_reason_are_masked` (B-12) |
| AC-23, AC-33 kết cục bản ghi | `TA::TestApplyRecord::test_each_outcome_one_result_comment`: subTest `Đã áp dụng`, `Lỗi` do bộ thực thi, `Lỗi` do kiểm lại, `Hết hiệu lực`, `Đã hoàn tác` → mỗi ca theo B-9, B-10 |
| AC-33 Từ chối | `TP::TestRecordDecision::test_reject_writes_nothing` (giữ tên): đích không đổi, 1 dòng `reject`, 0 job, +1 dòng theo B-9, B-10, phiên/sid/`form_dict` không đổi |
| AC-33 Từ chối mọi loại, một lần | `TP::TestRecordDecision::test_reject_posts_one_info_line_per_kind`: subTest code, lệnh, bản ghi; Từ chối lần hai → `InvalidTransition`, 0 dòng thêm |
| AC-11 | `TP::TestRecordDecision::test_reject_line_is_not_an_instruction` (B-11) |
| Ranh giới | `TArch::TestCatalogArchitecture::test_result_comment_boundaries`: `post_result` gọi đúng 2 chỗ (`run_change`, `reject`), lời gọi trong `reject` không trong `try`, `result_comment.py` không có `new_comment`, `set_user`, `agent_session`, `enter_agent_session`, `publish_realtime`; ngoài test, `add_comment(` chỉ trong `result_comment.py` |
| Không áp dụng sau Từ chối | `TP::…::test_rejected_never_applies` (`:591`) giữ nguyên, không thêm bước "chạy job đã xếp" |

## 5. C-1..C-15 của `arch-review-design-w2b-r2.md` mục 6 dưới nhánh A

| C | Trạng thái | Chữ mới |
|---|---|---|
| C-1 | **Đổi** | Điều kiện trước thêm "FEAT-004 vào `develop` **có** T56, T57" (B-1). Danh sách `cmd.migrate` bỏ `rejection_comment_posted` (còn option Select, DocPerm) |
| C-2 | **Đổi** | Bỏ dòng `erp_ai/test_change_decision.py` và `erp_ai/agent/changes/test_transitions.py` (trừ ca B-16). Thêm `erp_ai/agent/changes/result_comment.py`, `test_result_comment.py`: FEAT-004 tạo, U7a sửa sau merge |
| C-3 | **Đổi (iv)**; (i), (ii), (iii), (v) giữ | (iv) U7a cùng commit: `reject` gọi `post_result` (B-7), nhánh chữ bản ghi và `Đã từ chối` (B-3..B-5), các test ở mục 4 |
| C-4 | **Thay** | Không job Từ chối; L-1 nằm trong ADR-035 QĐ 6 (mục 1). Test `test_reject_job_skips_decider_recheck` bỏ; thay bằng `test_reject_posts_one_info_line_per_kind` |
| C-5 | **Bỏ** | Không trường trạng thái mới (B-8) |
| C-6, C-7, C-8, C-9 | Giữ | — |
| C-10 | **Bỏ** | Trừ ca B-16 |
| C-11 | **Đổi một chữ** | "có comment kết quả" = một dòng `Info` theo B-9 |
| C-12 | **Đổi** | Dòng test của phần comment kết quả chép từ mục 4 của file này, không từ `design-addendum-2-U7a-fixes.md` Sửa 3.6 hay `design-addendum-2-U7a-fixes-2.md` Sửa 2.7 |
| C-13, C-14 | Giữ | — |
| C-15 | **Đổi** | Bỏ "nhánh A/B của w2a (6)" (đã chốt). "Duyệt ADR-035" nay gồm QĐ 6 mới và QĐ 7. Thêm B-0 (A-D1) và câu R-5 (mục 7) |

Ngoài U7a: `design-addendum-2-U7b-U8-fixes.md` Sửa 8 (`:303-311`, "reject → 1 job", "chạy lại → 0") không còn hiệu lực; U7b theo B-14. Phán quyết (1) của `arch-review-design-w2b-r2.md` (U7a sửa test "Từ chối → 0 job") bỏ, trừ ca B-16. L-1, L-2 đóng vì không còn đối tượng.

## 6. Đoạn của hai file sửa U7a không còn hiệu lực

`design-addendum-2-U7a-fixes.md` (vòng 1), Sửa 3:
- 3.1 (`:93-94`): câu "U7a nhận AC-28 theo nhánh B".
- 3.2 (`:96-106`): hai bảng (chủ = U7a, "chờ người xác nhận nhánh"). Chủ là FEAT-004 T56, T57.
- Điều kiện bắt đầu (`:108`): vế nhánh B. Thay bằng B-1.
- 3.3 (`:110-124`) toàn bộ: module mới, `import authority`, `MASK`, `COMMIT_SHORT_LEN`, `post_result(proposal)`, chữ `Đề xuất {name}: …`, dòng `Việc: …`, `with authority.agent_session(): … new_comment(…)`, `owner = AGENT_USER`.
- 3.4 (`:126-131`) toàn bộ: `_post_result`, `TITLE_RESULT_COMMENT_FAILED` của U7a, logger `posted|none|failed`. CHG-001 đã có bản của nó.
- 3.5 (`:133`) toàn bộ.
- 3.6 (`:135-151`): mọi hàng thay bởi mục 4; các hàng code/lệnh/`LOCK_BUSY`/job lặp/lỗi comment là test của CHG-001 (tên theo CHG-001 `design.md` mục 8); mọi khẳng định `owner == AGENT_USER`.
- 3.7 (`:153-159`): gạch 1, phần "dòng `Việc: …`" (thay bằng B-3); gạch 2 toàn bộ (không chuyển phiên); gạch 3, nhánh "T57 gọi ở từng nhánh của `_run_in_lock`" (CHG-001 gọi một chỗ). Các gạch còn lại của 3.7 vẫn đúng.

`design-addendum-2-U7a-fixes-2.md` (vòng 2):
- Sửa 2.1 (`:73-79`) toàn bộ: trường `rejection_comment_posted`, migration, câu đối soát.
- Sửa 2.2 (`:81-87`) toàn bộ: `claim_rejection_comment`.
- Sửa 2.3 (`:89-93`): gạch 1 (`enqueue_change_job(name, "apply")`, thay bằng B-7); gạch 3, vế "Request **không** đăng comment". Gạch 2 và vế "không `agent_session`, không `set_user`" vẫn đúng.
- Sửa 2.4 (`:95-114`) toàn bộ: nhánh `_locked_run`, `_post_result(name, outcome)`, logger `outcome=Đã từ chối`.
- Sửa 2.5 (`:116-119`): hằng `RESULT_STATUSES` riêng, dòng `Việc: …`, gạch `post_result` (tài khoản agent). Ý "thêm `Đã từ chối`" giữ dưới dạng B-5.
- Sửa 2.6 (`:121`) toàn bộ.
- Sửa 2.7 (`:123-138`): mọi hàng, trừ hai ý giữ lại ở mục 4 (`test_reject_writes_nothing` với kỳ vọng mới; subTest `Đã từ chối` của `TRC`). Ghi chú U7b `:138` cũng bỏ.
- Mục 2 Touchpoints: dòng JSON "+1 trường" (`:178`), vế "`reject` xếp job" (`:179`), dòng `transitions.py` (`:180`), dòng `apply_job.py` (`:181`, thay bằng B-6), cột "mới nhánh B" và `RESULT_STATUSES` của dòng `result_comment.py` (`:182`), dòng `test_change_decision.py` (`:183`), câu `test_change_decision.py` ở `:186`.
- Mục 3: A-U7a-13, A-U7a-14 (`:201-202`).
- Mục 4 (`:213-215`): "(+ FEAT-004 AC-28 theo nhánh B)" và test J-2.
- Sửa 4 (`:168`): phần đếm AC-33, AC-28 (số dòng đổi theo mục 4).
- Sửa 2.8 (`:140`, bỏ A-U7a-10) vẫn đúng.

## 7. Rủi ro còn lại

- **R-1 (A-D1 của CHG-001, chưa ai thấy).** Chưa ai thấy dòng `Info` hiện thế nào trên trang phiếu Helpdesk thật. Căn cứ chỉ là đọc `TicketTimeline.vue:318`. Không hiện thì cùng hỏng: AC-39 (cho mọi kết cục), AC-23 hàng kết quả, AC-33 comment sau Duyệt và Từ chối. Lối ra của CHG-001 ("người bỏ AC-28 theo N-7") không đủ cho FEAT-007, vì AC-33 và AC-39 là AC riêng của FEAT-007: cần một ADR mới cho cách đánh dấu comment hệ thống, hoặc analyst `--amend`. B-0 kéo phép kiểm này lên trước đợt 2, thay vì sau G4 như CHG-001 `design.md:78`.
- **R-2 Không realtime.** Dòng của job chỉ hiện khi tải lại. Người duyệt trên trang phiếu không thấy kết quả tự hiện. Đã nhận (ADR-013, ADR-035 Hệ quả).
- **R-3 Dòng mang tên người.** Người đọc phiếu thấy "<họ tên> kết quả đề xuất …". Chữ mở đầu cố định phân biệt nó với lời người viết. Đã nhận.
- **R-4 Từ chối nguyên tử.** Ghi dòng lỗi → Từ chối không thành, người bấm lại. Ca phiếu đã xóa trả `None`, không ném.
- **R-5 (ngoài nhánh A, phát hiện khi tự phản biện, chưa kiểm hết).** M2 của ADR-023 (`:36`) đòi người duyệt "vẫn có `ERP AI Instructor`" ở đầu mọi job áp dụng. ADR-031 QĐ 5 cho agent Helpdesk được giao duyệt đề xuất bản ghi. Nếu M2 của T55 so đúng chữ đó, thì mọi đề xuất bản ghi do agent được giao duyệt sẽ kết thúc ở `Lỗi`. Tôi chưa thấy đoạn nào trong phần đã đọc của hai file sửa U7a xử lý điểm này. Team-leader: hỏi tech-lead đối chiếu trước khi lập plan đợt 2; nếu đúng là hở thì gọi architect (đổi chữ M2 cần ADR mới, vì ADR-023 không phải của FEAT-007). Không chặn phán quyết này: Từ chối không đi qua M2 (ADR-035 QĐ 6).

## 8. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR và file này mà vẫn xung đột, rồi siết:
1. U7a thêm dòng `Việc: …` theo vòng 1, trong khi CHG-001 đặt đích ở dòng 1. Kết quả là hai dạng chữ. Siết: B-3.
2. Đề xuất bản ghi `Đã hoàn tác` in `commit hoàn tác ` rỗng. Siết: B-4.
3. `catalog_create_user` làm lộ email ở đích. Siết: B-3, B-12.
4. Ma trận AC-23 chỉ đếm loại `"Comment"`, nên dòng kết quả không được đếm. Dev thêm comment agent cho đủ, thành hai comment. Siết: B-10, B-6.
5. Dev bọc `post_result` trong `try` ở `reject` "cho an toàn": có Từ chối mà không có comment, im lặng. Siết: B-7, ràng buộc AST.
6. U7a thêm lời gọi trong `_run_record`, CHG-001 gọi trong `run_change`: hai dòng. Siết: B-6.
7. U7b vẫn khẳng định "reject → 1 job" theo Sửa 8 cũ, còn U7a không xếp job. Siết: B-14, mục 5.

Sau khi siết, không còn cặp nào trong phạm vi comment kết quả của U7a, U7b.

## Việc tiếp
- **Team-leader:**
  - ghi journal "phán quyết nhánh A: comment Từ chối trong request, ADR-035 QĐ 6 viết lại, QĐ 7 mới";
  - chuyển ADR-035 (QĐ 1–7) cho người duyệt cùng ADR-033;
  - đặt B-0 lên lịch ngay sau khi FEAT-004 merge;
  - đưa R-5 cho tech-lead.
- **Tech-lead:** plan đợt 2 mang C-1..C-15 đã đổi ở mục 5 và B-0..B-16; dòng test lấy từ mục 4.
- **Designer:** không có vòng sửa.
