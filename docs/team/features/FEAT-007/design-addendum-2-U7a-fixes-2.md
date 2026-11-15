Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Sửa design addendum 2 — U7a (vòng sửa 2/3), theo `arch-review-design-w2b.md`

File này **thắng** `design-addendum-2-U7a-fixes.md` (vòng 1) và `design-addendum-2-U7a.md` (addendum) ở mọi chỗ khác nhau. Chỗ nào file này không nhắc thì vòng 1 giữ nguyên, rồi tới addendum. Thứ tự đọc của tech-lead: addendum → `arch-review-design-w2a.md` → vòng 1 → `arch-review-design-w2b.md` (mục 3 J-1, J-2; mục 4 phán quyết (6), (7), (9); mục 6) → file này.

Theo ADR-031 QĐ 1–9, ADR-033 QĐ 1, QĐ 6, ADR-035 QĐ 5, QĐ 6 (proposed), ADR-012, ADR-013 Ràng buộc "không `set_user` trong `changes/`". Không đổi kiến trúc, không cần ADR mới. Nhánh B của comment kết quả (vòng 1, mở đầu) giữ, vẫn chờ người; mọi sửa dưới đây đúng cho cả nhánh A và B (w2b phán quyết (7) câu cuối), riêng chỗ khác nhánh được ghi rõ.

**Tên:** không tên nào ở mục 5 của `arch-review-design-w2a.md` bị đổi. Tên mới đều là **thêm**: `transitions.claim_rejection_comment`, trường `rejection_comment_posted`, `result_comment.RESULT_STATUSES`. Các tên mục 6 của w2b (`IMPLICIT_COMMIT_ACTIONS`, `_post_comment`, `record_summary`, `post_result`, `DECIDE_REFUSAL`) giữ đúng chữ. Hai hàm riêng (`_undo_partial_write`, `_post_result`) do vòng 1 đặt, không thuộc hợp đồng, đổi chữ ký ở đây.

---

## 0. Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Thứ tự trong `CustomField.on_update` | `validate_fields_for_doctype(self.dt)` (import trong thân hàm) chạy **trước** `frappe.clear_cache` + `frappe.db.updatedb(self.dt)` | `apps/frappe/frappe/custom/doctype/custom_field/custom_field.py:206-216` |
| Commit ngầm ở đâu | `sql_ddl`: `self.commit()` rồi mới `self.sql(query)` — DDL lỗi sau commit thì dòng đã bền mà cột không có | `apps/frappe/frappe/database/database.py:422-425` |
| `commit()` chạy callback nào | `before_commit.run()` → `sql("commit")` → `begin()` → `after_commit.run()`; `rollback()` toàn phần `reset()` cả hai hàng; `rollback(save_point=…)` không đụng callback | `database.py:1187-1215` |
| `CallbackManager.run` | `popleft` từng hàm rồi gọi: mỗi callback chạy **đúng một lần** | `apps/frappe/frappe/utils/__init__.py:1222-1229` |
| `enqueue_change_job` | `(proposal_name, action)`, `action ∈ VALID_CHANGE_ACTIONS = ("apply", "undo")`, đích `apply_job.run_change`, `enqueue_after_commit=True`, `job_id = erp_ai_change::{name}::{action}`, `deduplicate=True` | `.claude/worktrees/feat-004/erp_ai/agent/queue.py:7`, `:43-58` |
| `run_change` / `_locked_run` | `_locked_run` đọc `change_status`; khác trạng thái chờ → `OUTCOME_SKIPPED` | `.claude/worktrees/feat-004/erp_ai/agent/changes/apply_job.py:84-126` |
| Controller `reject` | `_decider` → `transitions.reject`; "no job" | `erp_ai_change_proposal.py:124-128` (worktree feat-004) |
| Liên kết có chữ ký đi đâu | `change_decision` ánh `ACTION_REJECT → proposal_form.reject` (hàm controller) | `.claude/worktrees/feat-004/erp_ai/change_decision.py:16` |
| Test ghim "từ chối → 0 job" | `erp_ai/test_change_decision.py::…::test_post_reject_zero_jobs` (`:239`, FEAT-004); `TP` có `test_rejected_never_applies` (`:599`) | grep trên worktree `feat-004` |
| `transitions.STATE_FIELDS` | bắt đầu ở `:27` (`change_status`, `decided_by`, `decided_at`, `approved_digest`, `undo_by`, `undo_at`, …) | `.claude/worktrees/feat-004/erp_ai/agent/changes/transitions.py:27` |
| Đường ghi comment phiếu có sẵn | `write_ticket.post_comment(args, ctx) -> dict`: kiểm `read` phiếu, `Comment.create`, `doc.new_comment(args["content"])`, `PermissionError` → `{"ok": False, …}`, đúng → `{"ok": True, "comment": name}`; `propose_change._comment` dựng HTML đề xuất rồi `new_comment` (`:122`) | `.claude/worktrees/feat-004/erp_ai/agent/tools/write_ticket.py:102-112`; `propose_change.py:102-122` |

---

## 1. Các sửa

### Sửa 1 — J-1: phân biệt "đã có commit trong lúc ghi" thay cho "dòng có tồn tại"

**1.1 Thay toàn bộ đoạn "Lỗi khi ghi …" cùng hai gạch đầu dòng của `_undo_partial_write` ở vòng 1 `:51-53`, và câu đầu của `:55`, bằng:**

`IMPLICIT_COMMIT_ACTIONS = (ACTION_CREATE_CUSTOM_FIELD,)` (giữ nguyên tên, giá trị, lý do của vòng 1). Ghi trong `execute` (và `undo`, cùng mẫu):

1. `committed = {"seen": False}` (biến cục bộ của lần gọi); `frappe.db.after_commit.add(lambda: committed.__setitem__("seen", True))` — đăng ký **ngay trước** `savepoint`.
2. `frappe.db.savepoint(SAVEPOINT)` → `with authority.agent_session(): before, after = handler.write(args)`.
3. Thành công: `committed["seen"]` sai → `frappe.db.release_savepoint(SAVEPOINT)`; đúng → không gọi (savepoint đã mất cùng lần commit). Quy tắc này thay "release chỉ khi ∉ `IMPLICIT_COMMIT_ACTIONS`" của vòng 1: quyết bằng việc có commit thật, không bằng tên hành động.
4. Lỗi khi ghi (`PermissionError` → `AGENT_NO_PERMISSION`; `ValidationError` → `SYSTEM_REFUSED`; khác → `log_error(TITLE_CATALOG_FAILED, …)` + `UNEXPECTED_ERROR`, như vòng 1) → `value_after = _undo_partial_write(request, doctype, name, committed=committed["seen"])`.

`_undo_partial_write(request, doctype, name, *, committed: bool) -> dict | None` (hàm riêng, chữ ký đổi so với vòng 1):
- `committed` sai (chưa có commit nào từ lúc đặt savepoint, **kể cả khi dòng Custom Field đã chèn trong giao dịch**, ví dụ `validate_fields_for_doctype` ném trước `updatedb`) → **luôn** `frappe.db.rollback(save_point=SAVEPOINT)`. Trả `{"present": False}` khi `request.action ∈ IMPLICIT_COMMIT_ACTIONS`, ngược lại `None`. Sau lần lùi này, dòng chèn dở không còn trong giao dịch, nên `finish` + commit ở bước 5 của `_run_record` không làm bền được nó.
- `committed` đúng → **không** lùi (savepoint đã mất). `present = bool(frappe.db.exists(doctype, name))` (`doctype` từ `ACTION_TARGET_DOCTYPES`, ADR-031 Ràng buộc 7). Với `ACTION_CREATE_CUSTOM_FIELD`: thêm `column = present and frappe.db.has_column(request.args["dt"], request.args["fieldname"])`, trả `{"present": present, "column": column}`; `present` đúng mà `column` sai (DDL lỗi **sau** commit ngầm của `sql_ddl`) → thêm 1 Error Log `TITLE_CATALOG_FAILED`, chữ `f"action={action} doctype={doctype} name={name} orphan_custom_field=1"` (không giá trị trường). Hành động ∉ `IMPLICIT_COMMIT_ACTIONS` mà `committed` đúng (tập thiếu một hành động) → Error Log `TITLE_CATALOG_FAILED` với `unexpected_commit=1`, trả `{"present": present}`.
- Callback đã đăng ký mà không có commit nào sẽ chạy ở lần commit kế (bước 5 của `_run_record`) và chỉ đặt cờ của một dict cục bộ đã bỏ: vô hại; `rollback()` toàn phần xóa nó.

`ExecResult("refused", reason, doctype, name, value_before=None, value_after=<giá trị trả của _undo_partial_write>)` (giữ vòng 1). Phiên luôn được trả lại trước khi `execute` trả (giữ). `undo` không gặp hành động tự commit (`RESTORABLE_ACTIONS` không chứa nó), nhưng dùng cùng mẫu cờ ở bước 1–3.

**1.2 Danh sách đọc của Sửa 7 vòng 1 (`:194`):** thêm `frappe.db.has_column` (đọc schema, không ghi) vào câu "Đọc dữ liệu chỉ bằng …". Luật AST ADR-005 không cấm tên này; `test_executor_imports_and_no_ignore_permissions` giữ.

**1.3 Thay ghi chú cho U7b ở vòng 1 `:57` bằng:** "Theo ADR-035 QĐ 5, vị từ 'Tự làm' của U7b có vế 'hành động ∉ `catalog.IMPLICIT_COMMIT_ACTIONS`'; tạo Custom Field vì vậy chỉ chạy trong job sau duyệt (trạng thái chạy đã commit ở bước 3 của `_run_record`), không bao giờ giữa một lượt runner. U7a không thêm chặn trong `execute`."

**1.4 Test (thay hai dòng "H-1 Custom Field lỗi sau `insert`" và "H-1 ở mức bộ thực thi" của vòng 1 `:69-70`; dòng khác của 1.5 vòng 1 giữ):**

| AC / ràng buộc | Test | Ca biên / lỗi |
|---|---|---|
| J-1 lỗi trong `on_update` trước DDL, mức bộ thực thi | `TC::TestCreateCustomField::test_error_in_on_update_before_ddl_rolls_back` (môi trường `test`; patch `frappe.core.doctype.doctype.doctype.validate_fields_for_doctype` ném `frappe.ValidationError` → `outcome == "refused"`, `reason` bắt đầu bằng phần cố định của `SYSTEM_REFUSED`, `value_after == {"present": False}`, `frappe.db.exists("Custom Field", "<dt>-<fieldname>")` sai **ngay sau** `execute`, không ngoại lệ savepoint, phiên = người gọi) | dòng đã chèn, chưa commit |
| J-1 không có hàng mồ côi sau job | `TA::TestApplyRecord::test_custom_field_error_before_ddl_leaves_no_row` (đề xuất tạo Custom Field đã duyệt; cùng patch; chạy `run_change(name, "apply")` → trạng thái cuối `Lỗi` `SYSTEM_REFUSED`; sau job gọi `frappe.db.rollback()` rồi đếm: 0 Custom Field, 0 cột trên `dt`; mục hành động của dòng `fail` có `value_after == {"present": false}`) | job commit ở bước 5 |
| J-1 DDL lỗi sau commit ngầm | `TC::TestCreateCustomField::test_ddl_failure_after_implicit_commit_reports_orphan` (patch `frappe.db.updatedb` bằng hàm gọi `frappe.db.commit()` rồi ném `RuntimeError` → `UNEXPECTED_ERROR`, `value_after == {"present": True, "column": False}`, 1 Error Log `TITLE_CATALOG_FAILED` chứa `orphan_custom_field=1`, không lời gọi `rollback(save_point=…)`; `tearDown` xóa Custom Field + commit, STD-TEST-6) | commit rồi DDL lỗi |
| H-1 lỗi sau DDL thật (đổi kỳ vọng vòng 1) | `TC::TestCreateCustomField::test_error_after_insert_reports_presence` và `TA::TestApplyRecord::test_custom_field_error_after_insert_not_stuck` giữ tên, kỳ vọng `value_after == {"present": True, "column": True}` (thay `{"present": True}`) | sau commit ngầm |
| Savepoint theo commit thật | `TC::TestExecute::test_savepoint_released_only_without_commit` (patch `frappe.db.release_savepoint`: hành động không tự commit, thành công → gọi 1 lần; stub `write` gọi `frappe.db.commit()` rồi trả → 0 lần, không ngoại lệ) | commit lạ trong ghi |
| Giữ | `TC::TestCreateCustomField::test_error_before_insert_rolls_back_savepoint` (vòng 1, không đổi) | — |

### Sửa 2 — J-2, phán quyết (7): comment sau Từ chối, đăng bởi job; bỏ A-U7a-10

**2.1 Dữ liệu — thay không dòng nào, thêm vào mục 2.1 của addendum (bảng trường thêm của `erp_ai_change_proposal.json`):**

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `rejection_comment_posted` | Check, `default 0`, `read_only 1`, `no_copy 1` | Phần **trạng thái**: nối vào `transitions.STATE_FIELDS`; chỉ `transitions.py` ghi (ADR-031 Ràng buộc 6, ADR-035 "Phải làm thêm"). Không thuộc `CONTENT_FIELDS`, `DIGEST_FIELDS`, `RECORD_DIGEST_FIELDS`. Áp mọi loại đề xuất |

Migration: lên = `cmd.migrate` thêm cột, giá trị 0 cho mọi dòng cũ (đề xuất đã từ chối trước khi deploy không có job nào, nên không được đăng bù). Xuống = gỡ trường khỏi JSON + `cmd.migrate`; Frappe không xóa cột, mã cũ không đọc nó; không mất dữ liệu nào khác. Đối soát sau deploy: `SELECT COUNT(*) FROM tabERP AI Change Proposal WHERE change_status='Đã từ chối' AND rejection_comment_posted=0 AND decided_at >= <giờ deploy>` = số Error Log `TITLE_RESULT_COMMENT_FAILED` của các đề xuất đó (job đang chờ trong hàng đợi được trừ ra).

**2.2 Thêm vào bảng 3.6 của addendum (`transitions.py`):**

| Hàm | Đổi |
|---|---|
| `claim_rejection_comment(name) -> bool` (mới) | `_lock(name)` (khóa dòng đề xuất, như mọi phép chuyển). `change_status ≠ Đã từ chối` → `InvalidTransition`. `rejection_comment_posted == 1` → `False`, không ghi gì. Ngược lại `frappe.db.set_value(PROPOSAL_DOCTYPE, name, "rejection_comment_posted", 1, update_modified=False)` → `True`. Không commit (người gọi commit cùng comment). Không ghi dòng nhật ký |

Khóa `_lock` làm phép nhận **nguyên tử**: hai job song song cho cùng đề xuất thì job sau chờ khóa dòng, đọc `1` sau khi job trước commit, trả `False`.

**2.3 Thay gạch `reject` ở addendum `:246` ("`approve`, `reject`, `undo`: gọi `_decider` mới; thân khác giữ") cho riêng `reject` bằng:**

- `reject(name=None) -> dict` (chữ ký, POST, dạng trả giữ): `user = _decider(name)`; `status = transitions.reject(name, user)`; `queue.enqueue_change_job(name, "apply")`; trả `{"name": name, "status": status}`. Đúng như `approve`; không thêm đích enqueue, không sửa `queue.py` (A-U7a-13). `enqueue_after_commit=True` của `enqueue_change_job` nên job chỉ vào hàng sau khi request commit `Đã từ chối`.
- Đây là điểm cuối chung của cả ba đường Từ chối: form (POST thẳng), liên kết có chữ ký (`change_decision` → `proposal_form.reject`), ngăn U7b (`decide_proposal` gọi hàm controller, ADR-032 QĐ 2). U7a không sửa `change_decision.py`.
- Request **không** đăng comment, **không** gọi `agent_session`/`enter_agent_session`, không `set_user` (ADR-035 QĐ 6; luật AST chuyển phiên trong module whitelisted là của U7b, w2b mục 5).

**2.4 Thay gạch `run_change` của vòng 1 Sửa 3.4 (`:128`) và gạch `_post_result` (`:129`) bằng:**

- `_locked_run`: ngay sau khi đọc `row`, nếu `action == ACTION_APPLY` và `row.change_status == CHANGE_STATUS_REJECTED` → trả `CHANGE_STATUS_REJECTED`: không lấy `filelock`, không gọi `begin_apply`/`finish`, không đổi trạng thái. Mọi loại (code, lệnh, bản ghi) đi chung nhánh này. Nhánh có trước phép so `waiting`; các nhánh khác giữ.
- `run_change`: sau `outcome = _locked_run(...)`, nếu `outcome != OUTCOME_SKIPPED` → `comment = _post_result(proposal_name, outcome)`; ngược lại `comment = "none"`. Vẫn **đúng một** lời gọi `_post_result` trong file (A-U7a-12 giữ).
- `_post_result(name, outcome) -> str` (hàm riêng; trả `posted` | `none` | `failed` cho dòng logger):
  ```
  try:
      if outcome == CHANGE_STATUS_REJECTED and not transitions.claim_rejection_comment(name):
          return "none"                       # đã đăng ở lần chạy trước: 0 comment thêm
      posted = result_comment.post_result(frappe.get_doc(PROPOSAL_DOCTYPE, name))
      frappe.db.commit()                      # comment và cờ bền cùng một lần
      return "posted" if posted else "none"
  except Exception as exc:
      frappe.db.rollback()                    # lùi comment dở và cờ; trạng thái cuối đã commit trước đó
      frappe.log_error(TITLE_RESULT_COMMENT_FAILED, f"proposal={name} error={type(exc).__name__}")
      frappe.db.commit()
      return "failed"
  ```
  Comment lỗi thì cờ vẫn 0, nên chạy lại job (tay hoặc do hàng đợi) đăng được đúng 1 lần; comment thành công thì cờ 1, chạy lại → `none`.
- Dòng logger của `run_change`: `outcome=Đã từ chối` cho nhánh mới, `comment=%s` theo giá trị trả (STD-OPS-5); `kind=%s` giữ.

**2.5 Thay hàng `result_lines` của bảng 3.3 vòng 1 (`:123`) ở hai điểm, phần còn lại giữ:**
- `RESULT_STATUSES = (Đã áp dụng, Lỗi, Hết hiệu lực, Đã hoàn tác, Đã từ chối)` (hằng mới của module, lấy từ `erp_ai.constants`). Trạng thái ∉ `RESULT_STATUSES` → `ValueError` (thay "trạng thái không phải cuối").
- `Đã từ chối`: dòng 1 `Đề xuất {name}: Đã từ chối.`; loại bản ghi thêm dòng `Việc: {catalog_action} trên {target_doctype} {target_name}`; loại code và lệnh không thêm dòng (không commit, không mã thoát). Không đọc `failure_reason`.
- `post_result` không đổi: cùng bộ dựng, ghi dưới tài khoản agent qua `authority.agent_session` (nhánh B) hoặc đường chuyển phiên T56 (nhánh A), `owner = AGENT_USER`, không xếp lần chạy agent.

**2.6 Thay vòng 1 Sửa 3.5 (câu thay addendum `:290`) bằng:** "Từ chối: `transitions.reject` + xếp `enqueue_change_job(name, "apply")` (cùng đường `approve`), 1 dòng `reject`. Job đọc `Đã từ chối`, không đổi trạng thái, đăng đúng 1 comment kết quả qua `_post_result` (AC-33 'Sau Từ chối: không ghi, có log và comment'; ADR-035 QĐ 6)." Câu này thay luôn phần trong ngoặc của luồng 4.2 addendum `:290`.

**2.7 Test (thay hàng "Từ chối không comment kết quả" của vòng 1 `:148` và hàng "AC-33 từ chối" addendum `:378`; thêm subTest vào hai hàng của vòng 1 `:141`, `:146`):**

| AC / ràng buộc | Test | Ca biên / lỗi |
|---|---|---|
| AC-33 từ chối, trong request | `TP::TestRecordDecision::test_reject_writes_nothing` (đổi kỳ vọng, giữ tên): patch `frappe.enqueue`; POST `reject` → đích không đổi, 1 dòng `reject`, **1** job `RUN_CHANGE` với `action="apply"`, trạng thái lúc enqueue = `Đã từ chối`; **0** Comment mới trên phiếu trong request; sau lời gọi `frappe.session.user`, `frappe.local.session.sid`, `frappe.local.form_dict` bằng giá trị trước lời gọi | comment không bao giờ trong request |
| AC-33 từ chối, trong job, mọi loại | `TA::TestRejectComment::test_reject_job_posts_once` (subTest code, lệnh, bản ghi: `reject` qua controller; chạy `run_change(name, "apply")` → +1 comment trên phiếu, `owner == AGENT_USER`, chứa `Đã từ chối`; trạng thái vẫn `Đã từ chối`, `rejection_comment_posted == 1`; đích không đổi; chạy lại job → **0** comment thêm, logger `comment=none`) | chạy lại job |
| AC-33 lỗi comment sau Từ chối | `TA::TestRejectComment::test_comment_failure_keeps_flag_unset_and_logs` (stub `result_comment.post_result` ném `PermissionError` → 1 Error Log `TITLE_RESULT_COMMENT_FAILED`, 0 comment, cờ 0, trạng thái `Đã từ chối`; bỏ stub, chạy lại → đúng 1 comment) | agent không phải HD Agent |
| Phép nhận nguyên tử | `erp_ai/agent/changes/test_transitions.py::TestClaimRejectionComment::test_claim_once` (lần 1 `True`, lần 2 `False`, cờ 1); `::test_claim_on_non_rejected_raises` (`Chờ duyệt`, `Đã áp dụng` → `InvalidTransition`, không ghi) | trạng thái sai |
| Đường liên kết có chữ ký | `erp_ai/test_change_decision.py::…::test_post_reject_zero_jobs` (`:239`, FEAT-004) **đổi kỳ vọng** thành 1 job `RUN_CHANGE` `action="apply"`, 0 comment trong request; giữ tên (A-U7a-13, mục 2 dưới) | — |
| Không áp dụng sau Từ chối | `TP::…::test_rejected_never_applies` (`:599`) giữ, thêm: chạy job đã xếp → đích không đổi, không `begin_apply` | — |
| Nội dung | `TRC::TestResultLines::test_lines_for_each_final_status` thêm subTest `Đã từ chối` (code: đúng 1 dòng; bản ghi: có `Việc: … trên …`); `::test_non_final_status_raises` giữ (`Chờ duyệt`, `Đã duyệt` → `ValueError`) | — |
| Mọi kết cục một comment | `TA::TestApplyRecord::test_each_outcome_one_result_comment` thêm subTest `Đã từ chối` (đúng +1, `owner == AGENT_USER`) | 6 ca |
| Ràng buộc module | `TArch::TestCatalogArchitecture::test_result_comment_boundaries` giữ: `apply_job.py` vẫn đúng 1 lời gọi `post_result`, nằm trong `_post_result`; thêm: `transitions.py` là file duy nhất có chuỗi `"rejection_comment_posted"` trong lời gọi `set_value` | — |
| Ảnh chụp trường | `TArch::TestCatalogArchitecture::test_proposal_fields_snapshot` cập nhật ảnh chụp thêm `rejection_comment_posted` (không phải trường bộ đếm, ADR-031 Ràng buộc 5) | — |

Ghi cho U7b (không phải việc của file này): dòng `design-addendum-2-U7b-U8.md:366` "reject → 0 job" đổi thành "reject → 1 job, đích không đổi" trong vòng sửa của U7b (w2b phán quyết (7)).

**2.8 Bỏ A-U7a-10** (vòng 1 `:277`). Thay bằng A-U7a-13, A-U7a-14 ở mục 3.

### Sửa 3 — Phán quyết (6): `_post_comment` và `record_summary` là hàm ngay từ đầu

**3.1 Thay bước 3 của `_propose` ở addendum `:208` bằng:** "Không đạt: nếu `result.test_site_only` và `ctx.run_id ∉ frappe.local.flags.erp_ai_test_site_runs` → `_post_comment(ctx, TEST_SITE_COMMENT.format(action=escape_html(action), doctype=escape_html(result.doctype)))`, rồi nhớ `ctx.run_id`; trả `{"ok": False, "reason": result.reason}`. Không tạo đề xuất."

**3.2 Thêm vào 3.4 addendum (`catalog_tools.py`), hàm cấp module:**

`_post_comment(ctx, html) -> str`: `result = write_ticket.post_comment({"content": html}, ctx)` — dùng lại tool comment có sẵn (kiểm `read` phiếu, `Comment.create`, bắt `PermissionError`). `result["ok"]` đúng → trả `result["comment"]` (tên Comment). Sai → `frappe.logger(LOGGER_NAME).warning("erp_ai catalog comment_refused ticket=%s reason=%s", ctx.ticket_name, result["reason"])`, trả `""` (lỗi được ghi, không ném: comment báo không phải điều kiện của kết quả tool). `catalog_tools.py` **không** gọi `new_comment` trực tiếp (STD-DESIGN-4: không thêm bản thứ ba). `html` do người gọi đã thoát. U7b gọi hàm này cho comment báo lại "Tự làm", không tách lại.

**3.3 Thay gạch `onload` ở addendum `:249` bằng:**

- Hàm cấp module `record_summary(doc) -> dict` trong `erp_ai_change_proposal.py`: `doc.change_kind ≠ CHANGE_KIND_RECORD` → `ValueError`. Trả đúng các khóa `name`, `ticket`, `change_status`, `catalog_action`, `target_doctype`, `target_name`, `confidence_pct`, `reason`, `reversible`, `editable_args` (`{k: effective_args[k] for k in editable_keys}`, `effective_args = catalog.effective_args(action_args, edited_args)`). Chỉ đọc, không kiểm quyền: người gọi đã có `doc` qua đường có kiểm quyền (form của Frappe; U7b gọi sau hook của ADR-035).
- `onload`: loại bản ghi → `self.set_onload("editable_args", record_summary(self)["editable_args"])` (khóa onload giữ tên, JS không đổi); không gọi `change_text.proposal_notes`.
- U7b dùng `record_summary` cho ngăn và đặt hàm tóm tắt có `can_decide` của mình cạnh nó (w2b J-6); U7a không viết `can_decide` vào `record_summary`.

**3.4 Test (thêm):**

| Ràng buộc | Test |
|---|---|
| (6) một đường comment | `TT::TestPostComment::test_returns_comment_name` (comment có trên phiếu, trả đúng tên); `::test_refused_returns_empty_and_logs` (stub `write_ticket.post_comment` trả `{"ok": False, "reason": "x"}` → `""`, 1 dòng logger cảnh báo); `TArch::TestCatalogArchitecture::test_catalog_tools_has_no_direct_new_comment` (AST `catalog_tools.py`: 0 lời gọi `new_comment`; lời gọi `write_ticket.post_comment` chỉ nằm trong `_post_comment`) |
| (6) AC-12 một comment mỗi lần chạy | `TT::TestSiteEnvironment::test_two_refusals_one_comment_per_run` (addendum `:394`) giữ, thêm khẳng định comment đi qua `_post_comment` (patch đếm 1) |
| (6) `record_summary` | `TP::TestRecordSummary::test_keys_and_editable_args` (tập khóa cố định; sau `approve_with_edit` thì `editable_args` mang giá trị sửa); `::test_code_kind_raises`; `::test_onload_uses_record_summary` (patch `record_summary`, gọi `onload` → 1 lời gọi; `__onload.editable_args` bằng giá trị trả) |

### Sửa 4 — Phán quyết (9): câu sai ở vòng 1 `:286`

**Thay toàn bộ dòng vòng 1 `:286` bằng dòng sau (dòng duy nhất của file này chứa cụm grep):**

- AC có dòng test (addendum mục 8 + vòng 1 + file này): **AC-12** (5 dòng, + khẳng định `_post_comment` ở Sửa 3.4), **AC-29** (6), **AC-30** (8 + 2 dòng Custom Field ở vòng 1 Sửa 1.5, trong đó 2 dòng đổi kỳ vọng ở Sửa 1.4 + 3 dòng J-1 mới ở Sửa 1.4), **AC-33** (11 dòng của vòng 1, hàng từ chối addendum `:378` và vòng 1 `:148` thay bởi 4 dòng ở Sửa 2.7, + 2 dòng H-1), **AC-34** (5), **AC-35** (4 + hồi quy chữ ở vòng 1 Sửa 2), **AC-28** (7 dòng ở vòng 1 Sửa 3.6, 2 dòng thêm subTest `Đã từ chối`). Khớp 6/6 + AC-28; không dòng test nào có điều kiện: `grep -n "chỉ viết khi"` trên file này chỉ trúng chính dòng này; trên `design-addendum-2-U7a.md` vẫn trả `:381`, vì các file sửa không sửa addendum mà **thắng** nó, và tech-lead chép dòng test AC-33/AC-28 từ vòng 1 Sửa 3.6 cộng Sửa 2.7 của file này, không từ addendum `:381`; plan không có dòng test nào kèm điều kiện.

---

## 2. Touchpoints (thay đổi so với bảng mục 2 của vòng 1; dòng khác giữ)

| Đường dẫn | Mới/sửa | Căn cứ | Sửa |
|---|---|---|---|
| `erp_ai/agent/tools/catalog.py` | mới (đã có) | ô U7 | + Sửa 1.1 |
| `erp_ai/agent/tools/catalog_tools.py` | mới (đã có) | ô U7, phán quyết (6) w2b | + Sửa 3.1, 3.2 (import `write_ticket`, không sửa `write_ticket.py`) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json` | sửa (đã có) | ô U7 | + 1 trường Sửa 2.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | sửa (đã có) | ô U7 | + `reject` xếp job (2.3), `record_summary`, `onload` (3.3) |
| `erp_ai/agent/changes/transitions.py` | sửa (đã có) | ô U7 | + `STATE_FIELDS`, `claim_rejection_comment` (2.2) |
| `erp_ai/agent/changes/apply_job.py` | sửa (đã có) | ô U7 | + nhánh `_locked_run`, `_post_result` (2.4) |
| `erp_ai/agent/changes/result_comment.py` | mới nhánh B / sửa nhánh A (đã có) | phán quyết (6) w2a | + `RESULT_STATUSES`, dòng `Đã từ chối` (2.5) |
| `erp_ai/test_change_decision.py` | **sửa, đúng 1 test** (thay câu "Không chạm" của vòng 1 `:255` cho file này) | ADR-035 Ràng buộc test "Từ chối qua liên kết có chữ ký → 1 job"; AC-33 | Sửa 2.7 |
| Test sửa (đã có trong vòng 1): `test_catalog.py`, `test_catalog_tools.py`, `test_apply_job.py`, `test_erp_ai_change_proposal.py`, `test_transitions.py`, `test_result_comment.py`, `erp_ai/tests/test_architecture.py` | sửa | test | Sửa 1.4, 2.7, 3.4 |

Không chạm (thêm vào danh sách vòng 1): `erp_ai/agent/queue.py`, `erp_ai/change_decision.py`, `erp_ai/agent/tools/write_ticket.py`. `erp_ai/test_change_decision.py` đang có sửa chưa commit trên `develop` (CHG-001): task U7a sửa file này rebase sau khi CHG-001 merge, chạy `cmd.test_one` cho file đó trước merge (K-5 của w2a).

**So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:** file này không thêm đường dẫn mã mới nào; đường dẫn mới duy nhất:
```
docs/team/features/FEAT-007/design-addendum-2-U7a-fixes-2.md -> docs  OK
```
**So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào ở bảng trên khớp → 0.

---

## 3. Giả định do đội quyết (thay/thêm vào bảng mục 3 của vòng 1)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U7a-10 | **Bỏ** (J-2) | AC-33 của FEAT-007 đòi comment sau Từ chối | — | — |
| A-U7a-13 | Job Từ chối xếp bằng `enqueue_change_job(name, "apply")`; `run_change` rẽ theo trạng thái `Đã từ chối` | không thêm đích enqueue (w2a (2)), không sửa `queue.py`; `Đã từ chối` là trạng thái cuối nên `job_id …::apply` không trùng job áp dụng thật nào | thêm `"reject"` vào `VALID_CHANGE_ACTIONS` (sửa `queue.py`, ngoài touchpoint) | thêm action mới, đổi lời gọi ở `reject`, test 2.7 giữ |
| A-U7a-14 | Dấu chống lặp = trường trạng thái `rejection_comment_posted`, nhận nguyên tử dưới khóa dòng, commit cùng comment | ADR-035 "Phải làm thêm"; trạng thái không đổi nên phép chuyển không chặn lặp được; đếm Comment có sẵn thì không nguyên tử | tìm comment có `Đã từ chối` của agent trên phiếu | đổi nguồn dấu, test `test_reject_job_posts_once` giữ |
| A-U7a-15 | "Đã có commit trong lúc ghi" = cờ do callback `frappe.db.after_commit` đặt, đăng ký ngay trước savepoint | đúng nghĩa J-1 (commit thật, không suy từ `exists`/`transaction_writes`, w2b tự phản biện 8); `CallbackManager.run` chạy mỗi hàm một lần | so `transaction_writes`; đọc `exists` (J-1 bác) | đổi cơ chế cờ trong `catalog.py`, test Sửa 1.4 giữ |
| A-U7a-16 | DDL lỗi sau commit ngầm → U7a không xóa Custom Field mồ côi; báo `{"present": true, "column": false}` + Error Log `orphan_custom_field=1`; người đối soát xóa | xóa dữ liệu đã bền cần người (designer không quyết); ca hiếm, chỉ site `test` | xóa bù trong `execute` | thêm bước bù có test, cần architect duyệt |
| A-U7a-17 | `_post_comment` dùng `write_ticket.post_comment`; bị từ chối → `""` + logger cảnh báo | đường comment đã kiểm quyền của tool; comment báo không quyết kết quả tool | ném lên | đổi thành ném, sửa `test_refused_returns_empty_and_logs` |

Câu nghiệp vụ mới: không. A-U7a-3 và "Custom Field luôn cần duyệt" (w2b (8)) vẫn mở ở team-leader.

---

## 4. Đối chiếu AC trong phạm vi U7a (paste)

- Spec (arch-impact hàng U7 ∩ lời gọi): AC-12, AC-29, AC-30, AC-33, AC-34, AC-35 (+ FEAT-004 AC-28 theo nhánh B).
- Test plan sau file này: AC-12, AC-29, AC-30, AC-33, AC-34, AC-35, AC-28 — mỗi AC ≥ 1 dòng `file::name` (dòng duy nhất có đếm: Sửa 4). Khớp.
- Test cho từng finding: J-1 → `TC::TestCreateCustomField::test_error_in_on_update_before_ddl_rolls_back`, `TA::TestApplyRecord::test_custom_field_error_before_ddl_leaves_no_row`; J-2 → `TA::TestRejectComment::test_reject_job_posts_once` (đúng 1 lần, chạy lại 0), `TP::TestRecordDecision::test_reject_writes_nothing` (0 comment trong request, phiên không đổi).

---

## 5. Bảng đóng: finding hoặc phán quyết → sửa

| Mục của `arch-review-design-w2b.md` | Nội dung ngắn | Giải bởi |
|---|---|---|
| J-1 (major) | lỗi trong `on_update` trước DDL để lại Custom Field mồ côi bị commit | Sửa 1 (1.1 cờ commit, 1.4 test) |
| J-2 (major) | A-U7a-10 trái AC-33: Từ chối phải có comment | Sửa 2 |
| Phán quyết (7) | comment Từ chối: cùng bộ dựng, đăng bởi job qua `enqueue_change_job`, chạy lại 0 comment | Sửa 2 (2.2–2.7), A-U7a-13, A-U7a-14 |
| Phán quyết (6) | `_post_comment`, `record_summary` là hàm từ đầu | Sửa 3 |
| Phán quyết (9), phần U7a-fixes `:286`; minor (f) | câu grep sai | Sửa 4 |
| J-5 phần ghi chú vòng 1 `:57` | ghi chú U7b về commit ngầm | Sửa 1.3 (theo ADR-035 QĐ 5) |
| Mục 6 w2b (hợp đồng U7a bổ sung) | sáu tên/hành vi | giữ chữ; Sửa 1–3 hiện thực |
