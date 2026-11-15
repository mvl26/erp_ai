Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Sửa design addendum 2 — U7a (vòng sửa 1/3), theo `arch-review-design-w2a.md`

File này **thắng** `design-addendum-2-U7a.md` ở mọi chỗ hai file khác nhau. Chỗ nào file này không nhắc thì addendum giữ nguyên. Thứ tự đọc của tech-lead: addendum → `arch-review-design-w2a.md` (mục 3 "U7a", mục 4, mục 5) → file này. Theo ADR-031 QĐ 1–9 (giữ cả chín), ADR-033 QĐ 1, QĐ 7, ADR-013 Ràng buộc "không `set_user` trong `changes/`", ADR-012 QĐ 3; không đổi kiến trúc, không cần ADR mới (review mục "Việc tiếp").

**Nhánh cho comment kết quả (phán quyết (6)):** thiết kế theo **nhánh B** — U7a sở hữu `erp_ai/agent/changes/result_comment.py` cho **mọi** loại đề xuất, ghi comment qua `authority.agent_session`. Team-leader chọn (journal FEAT-007, dòng 2026-11-14 "điểm chờ người từ review w2a"); **chờ người xác nhận** vì nó đổi phạm vi FEAT-004 (bỏ AC-28, gỡ T56, T57). Nếu người chọn nhánh A thì đọc Sửa 3.7: chỉ những dòng ghi ở đó đổi.

Không tên nào ở mục 5 của review bị đổi. Tên mới trong file này đều là **thêm**: `IMPLICIT_COMMIT_ACTIONS` (catalog), `result_comment.result_lines`/`post_result`, `TITLE_RESULT_COMMENT_FAILED`, `ROUTE_WORD_EXCEPTIONS` (test).

---

## 0. Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Điểm kết thúc của `run_change` | `run_change` gọi `_locked_run` một lần, nhận `outcome` (trạng thái cuối hoặc `OUTCOME_SKIPPED`), rồi ghi dòng logger. Mọi nhánh đã commit trước khi trả: `LOCK_BUSY` (`:121-126`), `_run_in_lock` (`:172`) | `.claude/worktrees/feat-004/erp_ai/agent/changes/apply_job.py:84-105`, `:108-173` (`fad39a3`) |
| `_run_in_lock` commit trạng thái chạy trước khi làm | Có: `begin_apply` → `frappe.db.commit()` (`:140`) → `_run`; ngoại lệ lạ → `rollback` → `log_error` → `finish(expected, Lỗi)` → commit | `apply_job.py:129-173` |
| `_decider` hiện tại | So `ROLE_INSTRUCTOR` + `NEVER_AUTHORITY` **trước** khi kiểm tồn tại; chữ từ chối "Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được" | `erp_ai_change_proposal.py:93-112` |
| Chữ từ chối đó có bị test ghim không | **Có**, ở hai file: `erp_ai/test_change_decision.py:42`, `:276-281` (FEAT-004, ngoài touchpoint U7a) và `test_erp_ai_change_proposal.py:449`, `:557`, `:564`, `:577` | grep trên worktree `feat-004` |
| Comment phiếu của bot được ghi thế nào | `frappe.get_doc(TICKET_DOCTYPE, name).new_comment(html)`; `HD Ticket.new_comment` ném `PermissionError` khi người gọi không phải HD Agent | `propose_change.py:122`; `helpdesk/.../hd_ticket.py:617-629` |
| Comment của tài khoản agent có xếp lần chạy mới không | Không: `comment_after_insert` bỏ qua `doc.owner == AGENT_USER` (`written_by_agent`) | `.claude/worktrees/feat-004/erp_ai/handlers.py:100-112` |
| `enter_agent_session` của U1 | `() -> bool`; chỗ duy nhất `frappe.set_user(AGENT_USER)`; không khôi phục user cũ | `design-addendum-1-U1.md:196`, `:203`, `:293` |
| Tiêu chí T56, T57 | T56: `result_lines(proposal) -> list[str]`, `post_result(proposal) -> str \| None`, che từ có `://`/`@` trong lý do, không `command_output`, không import `apply_job`. T57: đúng 1 lời gọi sau khi trạng thái cuối đã commit, không gọi khi `OUTCOME_SKIPPED`, lỗi comment → `log_error`, trạng thái giữ | `.claude/worktrees/feat-004/docs/team/features/FEAT-004/tasks.md:636-645` |
| FEAT-004 AC-28 | "Sau mỗi lần áp dụng, lỗi, hết hiệu lực hoặc hoàn tác … 1 comment mới trên phiếu … nói trạng thái cuối … lỗi có lý do … không chứa URL remote, khóa hay token." **Từ chối không thuộc AC-28** | FEAT-004 `spec.md:369` |
| Phép thử tĩnh AC-9 | So từ con trên mọi khóa schema; chưa có ngoại lệ | `erp_ai/agent/tools/test_registry.py:18-32`, `:247-259` |

---

## 1. Các sửa

### Sửa 1 — H-1, D-1: commit `Đang áp dụng` trước khi áp dụng; bỏ A-U7a-7; Custom Field không dựa vào savepoint sau `insert`

**1.1 Thay `design-addendum-2-U7a.md:235-240` (gạch `_run_record` của 3.7) bằng:**

- `_run_record(name, action, actor) -> str` theo dạng của `_run_in_lock`, chỉ khác là **không** lấy `filelock` (ADR-031 QĐ 9 giữ: đồng thời do phép chuyển có điều kiện của `transitions` cộng kiểm "trước" của `catalog` trong **cùng giao dịch ghi đích**):
  1. Apply: `transitions.begin_apply(name)` sai → trả `OUTCOME_SKIPPED`; `expected = CHANGE_STATUS_APPLYING`. Undo: trạng thái ≠ `Đang hoàn tác` → `OUTCOME_SKIPPED`; `expected = CHANGE_STATUS_UNDOING` (trạng thái này đã được `request_undo` commit).
  2. `reasons = _recheck_record(proposal, action)` — phiên = `decided_by`/`undo_by` (`WRONG_RUNNER`), `authority.can_decide(runner, proposal.change_kind, proposal.ticket)` (`APPROVER_LOST_ROLE`), `content_digest == approved_digest` (`DIGEST_CHANGED`); chạy **trước** khi bộ thực thi đổi phiên (ADR-031 Ràng buộc 3). Có lý do → `transitions.finish(name, expected, Lỗi, step="fail", actor=actor, reason=…)`, `frappe.db.commit()`, trả `Lỗi`.
  3. `frappe.db.commit()` — `Đang áp dụng` bền **trước** mọi ghi đích (cùng lý do ADR-013 QĐ 5 của loại code: một ghi đích có thể tự commit, xem 1.2).
  4. `request = CatalogRequest(catalog_action, catalog.effective_args(action_args, edited_args), category)`. Apply → `catalog.execute(request, watched_before=record_before)`; undo → `catalog.undo(request, applied_values=…, record_before=…)`. Kiểm "trước" và ghi đích chạy trong cùng một giao dịch (bên trong `catalog`).
  5. Kết quả → `finish` như addendum `:239` (không đổi): `refused` → `finish(expected, Lỗi, step="fail", reason, actions=[entry])`; `stale` → `finish(APPLYING, Hết hiệu lực, step="stale", …)`; `applied` → `finish(APPLYING, Đã áp dụng, step="apply", fields={"applied_values": …}, …)`; undo xong → `finish(UNDOING, Đã hoàn tác, step="undo", …)`. `entry = run_log.action_entry(handler.tool, doctype, name, ok, reason=…, value_before=result.value_before, value_after=result.value_after, instructor=proposal.instructor)`. Rồi `frappe.db.commit()`, trả trạng thái cuối.
  6. Ngoại lệ không lường ở bước 4–5 → `frappe.db.rollback()` (chỉ lùi phần sau commit ở bước 3; trạng thái vẫn là `expected`), `frappe.log_error(TITLE_CHANGE_FAILED, f"proposal={name} action={action} error={type(exc).__name__}")`, `finish(expected, Lỗi, step="fail", actor=actor, reason=type(exc).__name__)`, commit, trả `Lỗi`. Vì `expected` đã commit ở bước 3, phép chuyển `expected → Lỗi` luôn hợp lệ, kể cả khi ghi đích đã tự commit giữa chừng — đề xuất không kẹt ở `Đang áp dụng`.

**1.2 Thay câu "Ghi: …" và "Lỗi: …" của `execute` ở `design-addendum-2-U7a.md:193` bằng:**

`IMPLICIT_COMMIT_ACTIONS = (ACTION_CREATE_CUSTOM_FIELD,)` (hằng mới của `catalog.py`): hành động có ghi đích làm Frappe tự commit (`CustomField` → `frappe.db.updatedb` → `sql_ddl` → `commit()` trước DDL; `database.py:422-425`). Ghi: `frappe.db.savepoint(SAVEPOINT)` → `with authority.agent_session(): before, after = handler.write(args)` → `release_savepoint(SAVEPOINT)` chỉ khi hành động ∉ `IMPLICIT_COMMIT_ACTIONS` (với hành động tự commit, savepoint đã mất cùng lần commit đó). Lỗi khi ghi (`PermissionError` → `AGENT_NO_PERMISSION`; `ValidationError` → `SYSTEM_REFUSED`; khác → `log_error(TITLE_CATALOG_FAILED, …)` + `UNEXPECTED_ERROR`), dọn theo một hàm `_undo_partial_write(action, doctype, name) -> dict | None`:
- hành động ∉ `IMPLICIT_COMMIT_ACTIONS` → `frappe.db.rollback(save_point=SAVEPOINT)`, trả `None` (như addendum);
- hành động ∈ `IMPLICIT_COMMIT_ACTIONS` → `present = bool(frappe.db.exists(doctype, name))` (`doctype` lấy từ `ACTION_TARGET_DOCTYPES`, không viết tay, ADR-031 Ràng buộc 7). `present` sai → chưa có lần commit nào (commit ngầm chỉ xảy ra sau khi dòng Custom Field đã chèn) nên savepoint còn: `rollback(save_point=SAVEPOINT)`. `present` đúng → **không** gọi rollback savepoint (nó sẽ ném vì savepoint đã mất). Trả `{"present": present}`.

`ExecResult("refused", reason, doctype, name, value_before=None, value_after=<giá trị trả của _undo_partial_write>)`: với tạo Custom Field, mục hành động ghi `value_after = {"present": true|false}` để người đối soát thấy trường đã có hay chưa. Phiên luôn được trả lại trước khi `execute` trả (giữ). `undo` không đổi: `RESTORABLE_ACTIONS` không chứa hành động tự commit.

**Ghi chú cho U7b (điểm chen "Tự làm", 3.11):** khi U7b gọi `execute(..., watched_before=None)` trong runner cho `ACTION_CREATE_CUSTOM_FIELD`, lần commit ngầm cũng chốt giao dịch đang mở của runner. Designer U7b ghi điều này trong addendum của mình; U7a không đổi gì thêm.

**1.3 Thay luồng 4.3 (`design-addendum-2-U7a.md:292`) bằng:** Job (phiên = `decided_by`) → `begin_apply` (khóa dòng đề xuất) → `_recheck_record` (phiên, `can_decide`, dấu) → **commit `Đang áp dụng`** → `catalog.execute(effective_args, watched_before=record_before)`: `check` lại → so canh → `agent_session` + savepoint → ghi theo phân quyền → trả phiên → `finish` (`Đã áp dụng` | `Hết hiệu lực` | `Lỗi`, 1 dòng có 1 mục hành động) → commit → comment kết quả (Sửa 3). Lệnh `bench` đang giữ `erp_ai_change` không chặn bước này. Tiêu đề 4.3 đổi "(một giao dịch, không khóa chung)" thành "(trạng thái chạy commit trước, ghi đích một giao dịch, không khóa chung)".

**1.4 `design-addendum-2-U7a.md:426` (A-U7a-7): bỏ.** Thay bằng A-U7a-9 ở mục 3.

**1.5 Test (thay `:380`, thêm dòng):**

| AC / ràng buộc | Test | Ca biên / lỗi |
|---|---|---|
| AC-33 kiểm lại lúc áp dụng | `TA::TestApplyRecord::test_rule_removed_before_job_fails` (giữ); `TA::TestApplyRecord::test_unexpected_error_rolls_back_to_failed` (**đổi kỳ vọng**: stub `catalog.execute` ném `RuntimeError` → trạng thái cuối `Lỗi` đi từ `Đang áp dụng`, dòng `fail` có `reason = "RuntimeError"`, đích không đổi, 1 Error Log `TITLE_CHANGE_FAILED`) | ngoại lệ lạ |
| H-1 trạng thái chạy bền trước khi ghi | `TA::TestApplyRecord::test_applying_committed_before_execute` (stub `catalog.execute` gọi `frappe.db.rollback()` rồi đọc `change_status` → `Đang áp dụng`; rồi ném → cuối `Lỗi`) | rollback toàn giao dịch |
| H-1 Custom Field lỗi sau `insert` | `TA::TestApplyRecord::test_custom_field_error_after_insert_not_stuck` (môi trường `test`, dòng danh mục, đề xuất tạo Custom Field đã duyệt; stub `write` của handler gọi `insert` thật rồi ném `RuntimeError` → `Lỗi` `UNEXPECTED_ERROR`, **không** `Đang áp dụng`, không `InvalidTransition`, dòng `fail` có 1 mục với `value_after == {"present": true}`; `tearDown` xóa Custom Field và commit vì dữ liệu đã bị commit ngầm, STD-TEST-6) | lỗi sau commit ngầm |
| H-1 ở mức bộ thực thi | `TC::TestCreateCustomField::test_error_after_insert_reports_presence` (`ExecResult.outcome == "refused"`, `reason == UNEXPECTED_ERROR`, `value_after == {"present": True}`, không ngoại lệ savepoint, phiên = người gọi); `TC::TestCreateCustomField::test_error_before_insert_rolls_back_savepoint` (stub `validate` của Custom Field ném `ValidationError` → `SYSTEM_REFUSED`, `{"present": False}`, 0 Custom Field) | trước / sau commit ngầm |

### Sửa 2 — H-2, D-2: `_decider` dùng `can_decide`, không so role

**Thay `design-addendum-2-U7a.md:245` (gạch `_decider` của 3.8) bằng:**

- `_decider(name) -> tuple[str, str]` (người, loại). `user = frappe.session.user`. Đọc `change_kind`, `ticket` của đề xuất khi `name` là chuỗi khác rỗng và đề xuất có.
  - Không có đề xuất (hoặc `name` không phải chuỗi khác rỗng): `authority.can_decide(user, CHANGE_KIND_CODE, None)` đúng (tức có Instructor và ∉ `NEVER_AUTHORITY`) → `DoesNotExistError` "Không có đề xuất {0}" (chữ cũ); sai → `PermissionError` `DECIDE_REFUSAL`. Người không đủ điều kiện không biết tên có tồn tại hay không (AC-35, hành vi FEAT-004 giữ).
  - Có đề xuất: `not authority.can_decide(user, kind, ticket)` → `PermissionError` `DECIDE_REFUSAL`.
  - `DECIDE_REFUSAL` = **đúng chữ cũ** "Chỉ người có vai trò ERP AI Instructor mới duyệt, từ chối hoặc hoàn tác được", cho mọi lần từ chối của `_decider` (A-U7a-11). Bỏ hằng `NOT_ELIGIBLE` của addendum (không thuộc mục 5 của review).
  - Không còn nhánh riêng cho `NEVER_AUTHORITY` trong controller: `can_decide` đã trả `False` cho các tài khoản đó.
- Controller bỏ import `ROLE_INSTRUCTOR` và không gọi `frappe.get_roles`. `_recheck` của `apply_job` cũng gọi `can_decide` (addendum `:234`, giữ) và `_has_authority` bị xóa. Không chỗ nào khác so role để quyết duyệt (ADR-031 Ràng buộc 4).

**Test (thay `:400`, giữ `:392`):**

| Ràng buộc | Test |
|---|---|
| ADR-031 Ràng buộc 4 | `TArch::TestCatalogArchitecture::test_no_role_compare_for_decisions` — AST của controller đề xuất và `apply_job.py`: 0 tên `ROLE_INSTRUCTOR`, 0 lời gọi `get_roles`; cả hai file có ≥ 1 lời gọi `can_decide` |
| AC-35 không lộ tên | `TP::TestRecordDecision::test_unknown_name_non_instructor_permission_error` (người được giao không vai trò, người không vai trò, tài khoản agent × `approve`/`reject`/`undo`/`approve_with_edit` với `"AICHG-99999"` → `PermissionError` `DECIDE_REFUSAL`; Instructor → `DoesNotExistError`) |
| Hồi quy chữ FEAT-004 | `erp_ai/test_change_decision.py` và các ca `ROLE_REFUSAL` có sẵn của `TP` chạy **không sửa** và xanh (bằng chứng: đầu ra `cmd.test_one` cho hai file) |

### Sửa 3 — H-3, D-3, phán quyết (6): comment kết quả theo nhánh B

**3.1 Thay `design-addendum-2-U7a.md:26` (gạch cuối 1.1) bằng:**
- FEAT-004 AC-28 (comment kết quả): `grep new_comment` trong `erp_ai/agent/changes/` = 0, nên **chưa có mã**. Nhưng plan FEAT-004 **có task**: T56 (`changes/result_comment.py`, `post_result`) và T57 (job gọi `post_result` sau mọi kết cục), chưa tick, **ĐỖ từ round 66** vì chưa có câu trả lời "ghi dưới tài khoản nào" (`.claude/worktrees/feat-004/docs/team/features/FEAT-004/tasks.md:636-645`). ADR-033 QĐ 1 đã trả lời câu đó (tài khoản agent, một hàm chuyển phiên); U7a nhận AC-28 theo nhánh B (Sửa 3.3).

**3.2 Thay dòng "Comment kết quả …" ở `:40` (bảng 1.2) bằng:**

| Tên | Nguồn | Có trên `team/FEAT-004` hôm nay? |
|---|---|---|
| Comment kết quả áp dụng (`result_comment.post_result`) | FEAT-004 T56, T57 (ĐỖ) → **nhánh B: U7a tạo** (Sửa 3.3) | Không có mã. Có task T56, T57, đang ĐỖ |

**Thay dòng "Comment kết quả …" ở `:65` (bảng 1.3) bằng:**

| Cần | Chủ | Trạng thái |
|---|---|---|
| Comment kết quả cho mọi loại đề xuất (FEAT-004 AC-28) | **U7a** (nhánh B, phán quyết (6)); FEAT-004 bỏ AC-28, gỡ T56, T57 theo thứ tự bỏ của FEAT-004 spec N-7 | **Chờ người xác nhận nhánh.** Analyst `--amend` FEAT-007 để phủ AC-28 cho mọi loại (team-leader chuyển). Nhánh A: Sửa 3.7 |

**Thay điều kiện bắt đầu ở `:54` bằng:** FEAT-004 đã merge `develop` (hết chuỗi `apply_job.py`, T67) **và** T56, T57 đã gỡ khỏi FEAT-004 (nhánh B); U0, U1, U2, U3 đã ở `team/FEAT-007`. FEAT-004 merge mà còn `result_comment.py` → áp nhánh A (Sửa 3.7), không tạo file thứ hai. Cắt sớm hơn → `DESIGN_CONFLICT`, dừng.

**3.3 Mục mới 3.12 — `erp_ai/agent/changes/result_comment.py` (mới, nhánh B)**

Chỉ import `frappe`, `frappe.utils.escape_html`, `erp_ai.constants`, `erp_ai.agent.authority`. Không import `apply_job`, `transitions`; không `frappe.set_user`, không `publish_realtime` (ADR-013 Ràng buộc giữ).

```python
MASK = "[đã ẩn]"
COMMIT_SHORT_LEN = 12
def result_lines(proposal) -> list[str]
def post_result(proposal) -> str | None
```

| Hàm | Hành vi | Lỗi |
|---|---|---|
| `result_lines` | Chỉ đọc các trường `name`, `ticket`, `change_status`, `change_kind`, `failure_reason`, `apply_commit_sha`, `undo_commit_sha`, `exit_code`, `catalog_action`, `target_doctype`, `target_name`; **không** đọc `command_output`. Dòng 1: `Đề xuất {name}: {change_status}.` Rồi theo loại: code `Đã áp dụng` → `Commit: {apply_commit_sha[:12]}`; code `Đã hoàn tác` → `Commit hoàn tác: {undo_commit_sha[:12]}`; lệnh → `Mã thoát: {exit_code}`; **bản ghi** → `Việc: {catalog_action} trên {target_doctype} {target_name}`. `Lỗi` hoặc `Hết hiệu lực` → `Lý do: {failure_reason}` sau khi thay mỗi từ (tách theo khoảng trắng) chứa `://` hoặc `@` bằng `MASK`. Mọi giá trị qua `escape_html` | trạng thái không phải cuối → `ValueError` |
| `post_result` | `ticket` rỗng hoặc phiếu không còn → `None`. Ngược lại `with authority.agent_session(): return frappe.get_doc(TICKET_DOCTYPE, ticket).new_comment("<br>".join(result_lines(proposal)))` — cùng đường ghi comment của `propose_change._comment`; comment có `owner` = tài khoản agent (ADR-033 QĐ 1, QĐ 7 hàng "Comment … lỗi") nên `comment_after_insert` bỏ qua, không xếp lần chạy agent. Không commit (người gọi commit) | `PermissionError` từ `agent_session` (không vào được phiên agent) hoặc từ `new_comment` (tài khoản agent không phải HD Agent) → ném lên |

**3.4 Thêm vào 3.7 (`apply_job.py`) — một lời gọi duy nhất cho mọi loại:**

- `run_change`: sau `outcome = _locked_run(...)`, nếu `outcome != OUTCOME_SKIPPED` → `_post_result(proposal_name)`. Đây là **điểm kết thúc chung** của mọi đường: code/bench (`_run_in_lock`: áp dụng, lỗi, hết hiệu lực, hoàn tác), khóa bận `LOCK_BUSY` (`_locked_run`), và cả 4 kết cục cùng `Lỗi` do kiểm lại của `_run_record`. Mỗi đường đã commit trạng thái cuối trước khi trả (mục 0), nên comment luôn ghi sau commit (tiêu chí T57). `_run_record`, `_run_in_lock` **không** có lời gọi comment nào (bất biến của phán quyết (6): một bộ dựng, một lời gọi mỗi kết cục).
- `_post_result(name) -> None`: `try: result_comment.post_result(frappe.get_doc(PROPOSAL_DOCTYPE, name)); frappe.db.commit()`; `except Exception as exc: frappe.db.rollback(); frappe.log_error(TITLE_RESULT_COMMENT_FAILED, f"proposal={name} error={type(exc).__name__}"); frappe.db.commit()`. Rollback chỉ lùi comment dở; trạng thái cuối đã commit nên kết cục không đổi (STD-ERR-1).
- `TITLE_RESULT_COMMENT_FAILED = "erp_ai: comment kết quả đề xuất lỗi"` cạnh `TITLE_CHANGE_FAILED`.
- Dòng logger của `run_change` thêm `comment=%s` (`posted` | `none` | `failed`) — một tín hiệu cho đường mới (STD-OPS-5).

**3.5 Thay `:290` phần trong ngoặc của "Từ chối"** bằng: "Từ chối: `transitions.reject`, không job, 1 dòng `reject`, **không** comment kết quả (AC-28 chỉ liệt kê áp dụng, lỗi, hết hiệu lực, hoàn tác; A-U7a-10)."

**3.6 Thay `:381` và `:412`; thêm dòng test (mọi dòng dưới là test bắt buộc, không có điều kiện):**

Ký hiệu mới: `TRC` = `erp_ai/agent/changes/test_result_comment.py`.

| AC / ràng buộc | Test | Ca biên / lỗi |
|---|---|---|
| AC-33 / FEAT-004 AC-28, loại bản ghi (thay `:381`) | `TA::TestApplyRecord::test_each_outcome_one_result_comment` (subTest: `Đã áp dụng`, `Lỗi` do bộ thực thi từ chối, `Lỗi` do kiểm lại `APPROVER_LOST_ROLE`, `Hết hiệu lực`, `Đã hoàn tác` → mỗi ca đúng +1 comment trên phiếu, `owner == AGENT_USER`, chứa trạng thái cuối; ca lỗi và hết hiệu lực chứa lý do) | 5 ca |
| AC-28, loại code và lệnh | `TA::test_one_result_comment_per_outcome` (subTest trên `GitSandbox`: áp dụng code có 12 ký tự đầu của commit, lệnh mã ≠ 0 có mã thoát, hết hiệu lực do đổi nhánh, hoàn tác, khóa hết giờ `LOCK_BUSY` → mỗi ca +1 comment) | `LOCK_BUSY` |
| AC-28 job lặp | `TA::test_skipped_job_posts_nothing` (job lần hai `OUTCOME_SKIPPED` → 0 comment) | — |
| AC-28 lỗi comment không đổi kết cục | `TA::test_comment_failure_keeps_final_status_and_logs` (stub `post_result` ném `PermissionError` → trạng thái cuối giữ, 1 Error Log `TITLE_RESULT_COMMENT_FAILED`, 0 comment) | agent không phải HD Agent |
| AC-28 không lộ bí mật | `TA::test_result_comment_has_no_remote_url_or_fake_token`; `TRC::TestResultLines::test_reason_with_url_or_token_is_masked` (gieo `https://x-token-FAKE@host/repo` trong `failure_reason`, đếm `FAKE` và `://` = 0) | URL, `@` |
| AC-28 nội dung | `TRC::TestResultLines::test_lines_for_each_final_status` (subTest: code `Đã áp dụng`, lệnh `Đã áp dụng` `mã thoát 0`, `Lỗi`, `Hết hiệu lực`, `Đã hoàn tác`, **bản ghi** `Đã áp dụng` có "Việc: … trên …"); `::test_non_final_status_raises` | trạng thái `Chờ duyệt` → `ValueError` |
| AC-28 ghi dưới agent, không xếp lần chạy | `TRC::TestPostResult::test_post_result_writes_one_escaped_comment_and_enqueues_no_agent_run` (giá trị `<script>` thoát; `owner == AGENT_USER`; phiên sau lời gọi = người gọi, cả khi `new_comment` ném; 0 job agent được xếp); `::test_post_result_without_ticket_returns_none` | phiếu bị xóa |
| Từ chối không comment kết quả | `TP::TestRecordDecision::test_reject_writes_nothing` (bổ sung khẳng định: 0 comment mới sau dòng `reject`) | — |
| Ranh giới module | `TArch::TestCatalogArchitecture::test_result_comment_boundaries` (`result_comment.py` không import `apply_job`/`transitions`; không `set_user`, `publish_realtime`; `apply_job.py` có đúng 1 lời gọi `post_result`, nằm trong `_post_result`) | — |

Thay `:412` bằng: "Phần comment 4 kết cục của AC-33 (FEAT-004 AC-28) có test bắt buộc ở bảng trên; không còn dòng nào có điều kiện."

**3.7 Nếu người chọn nhánh A (FEAT-004 giữ AC-28, T56, T57 build trong FEAT-004)** — chỉ những điểm sau đổi, phần còn lại của Sửa 3 giữ:
- `result_comment.py` và `test_result_comment.py` thành **sửa** (không mới): U7a chỉ thêm nhánh chữ loại bản ghi (dòng `Việc: …`, đọc thêm `catalog_action`, `target_doctype`, `target_name`) trong `result_lines` của T56, nguyên tên `post_result`; thêm subTest bản ghi vào `test_lines_for_each_final_status`. Bỏ 3.3 (không viết lại hàm).
- Chuyển phiên: dùng cách T56 đã build (FEAT-004 tự chuyển phiên qua `authority.py`); sau khi U1 merge, đường đó gộp vào `enter_agent_session` (việc của U1/FEAT-004, không của U7a). U7a không thêm `agent_session` vào `result_comment.py`.
- `apply_job.py`: nếu T57 đã gọi `post_result` ở một điểm chung (`run_change`) thì U7a không thêm lời gọi nào (4 kết cục của `_run_record` đi qua `_locked_run` → `run_change`); nếu T57 gọi ở từng nhánh của `_run_in_lock` thì U7a thêm đúng 1 lời gọi sau commit cuối của `_run_record` theo cùng mẫu bắt lỗi của T57. Bỏ 3.4 (`_post_result`, `TITLE_RESULT_COMMENT_FAILED` là của T57).
- Test: các dòng code/lệnh của 3.6 là của T56/T57 (FEAT-004), U7a không viết lại; U7a giữ bắt buộc `TA::TestApplyRecord::test_each_outcome_one_result_comment`, subTest bản ghi của `TRC`, `test_reject_writes_nothing` bổ sung, `test_result_comment_boundaries`.
- Điều kiện bắt đầu `:54`: đòi FEAT-004 merge **có** T56, T57.
- Touchpoint (mục 2): hai dòng `result_comment.py`, `test_result_comment.py` đổi cột "Mới/sửa" thành "sửa"; bảng so `allowed_new_file_roots` bỏ hai dòng đó.

### Sửa 4 — Phán quyết (4), D-4: ba hằng ở `erp_ai/constants.py`, touchpoint U7a

**Thay dòng đầu bảng 1.3 (`:60`) và dòng touchpoint `:337` bằng:** U7a sửa `erp_ai/constants.py`, **đúng 3 hằng**, nối vào cuối khối FEAT-007 (sau khối T8 của U0 và trigger của U6b); `constants.py` giữ 0 dòng import:
```python
CHANGE_KIND_RECORD = "Thay đổi bản ghi"
ACTION_TARGET_DOCTYPES = {ACTION_CREATE_USER: "User", ACTION_ADD_TEAM_MEMBER: "HD Team",
                          ACTION_ADD_HOLIDAY: "Holiday List", ACTION_SET_ITEM_GROUP: "Item",
                          ACTION_CREATE_CUSTOM_FIELD: "Custom Field", ACTION_UPDATE_FIELDS: None}
TEST_SITE_ONLY_DOCTYPES = ("Custom Field", "Server Script", "Client Script", "Property Setter", "Workflow", "Data Import")
```
- `CHANGE_KIND_RECORD` vào **cùng commit** với option mới `Thay đổi bản ghi` của `change_kind` trong `erp_ai_change_proposal.json`.
- Giá trị `ACTION_TARGET_DOCTYPES` đúng cột "DocType đích" của `design.md:214-221`. `TEST_SITE_ONLY_DOCTYPES` (AC-12) khác nghĩa với `site_api.PERMLEVEL_DOCTYPES`; cùng chứa `"Custom Field"` không phải định nghĩa trùng.
- Thứ tự sửa `constants.py`: U0 (T8) → U6b → U7a.
- Test: `TArch::TestCatalogArchitecture::test_one_proposal_doctype_three_kinds` (có sẵn ở `:397`) khẳng định option = `(CHANGE_KIND_CODE, CHANGE_KIND_COMMAND, CHANGE_KIND_RECORD)`; thêm `::test_action_target_doctypes_cover_catalog_actions` (khóa của `ACTION_TARGET_DOCTYPES` == `set(CATALOG_ACTIONS)`; mỗi giá trị khác `None` là DocType có trên site).

### Sửa 5 — Phán quyết (5), D-5: `site_api.permlevel_refusal` của U2

**Thay dòng `site_api.permlevel_refusal` ở `:62` (bảng 1.3) bằng:**

| Cần | Chủ | Trạng thái |
|---|---|---|
| `site_api.permlevel_refusal(doctype: str, values: dict, *, name: str \| None = None) -> str \| None` — thuần theo luật C-6, không `ctx`; `name` khác `None` thì `site_api` tự đọc giá trị đã lưu; trả `PERMLEVEL_REASON` hoặc `None` | U2 (phán quyết (5)) | Nếu U2 đã merge mà chưa có tên công khai: plan đợt 2 thêm một task **chỉ tách hàm** trên `site_api.py` + `test_site_api.py`, đặt **trước** task bộ thực thi của U7a. `site_api.py` không vào touchpoint U7a. U7a không chép luật |

**Thay mệnh đề `permlevel` ở bước 3 của `check` (`:186`) bằng:** "`site_api.permlevel_refusal(doctype, values, name=name)` khi `doctype ∈ site_api.PERMLEVEL_DOCTYPES` — với tạo Custom Field: `doctype = ACTION_TARGET_DOCTYPES[ACTION_CREATE_CUSTOM_FIELD]`, `values` = các khóa sẽ ghi, `name=None` (bản ghi mới); với Đổi trường: `values = args["values"]`, `name = args["name"]` (giá trị đã lưu do `site_api` đọc). Có lý do → trả nguyên lý do đó." Luôn chế độ thường (không `ctx.unrestricted`).

**Test (giữ `:372`, ghi rõ):** `TC::TestUpdateFields::test_permlevel_on_custom_field_refused` (Đổi trường trên một Custom Field đã có `permlevel > 0` và trên Property Setter `property = "permlevel"` → `PERMLEVEL_REASON`; DB không đổi); `TArch::TestCatalogArchitecture::test_catalog_does_not_copy_permlevel_rule` (`catalog.py` không chứa chuỗi `"permlevel"` ngoài khóa của `CUSTOM_FIELD_KEY_REFUSED` ca thử; có lời gọi `permlevel_refusal`).

### Sửa 6 — D-6 (minor H-4): quyền đọc form đề xuất là của U7b

Thêm vào mục 5 (Quyền) sau bảng, thay không dòng nào khác: "U7a **không** thêm DocPerm nào cho ERP AI Change Proposal. Quyền đọc đề xuất loại bản ghi cho người được giao (ADR-032 QĐ 3) là hook quyền của U7b. U7a và U7b vào `develop` cùng lượt merge cuối đợt 2. Đường giao diện của AC-34, AC-35 (người được giao mở form từ liên kết `Sửa`/`OPEN_PROPOSAL_LABEL`, bấm "Sửa và duyệt") được QA nghiệm thu sau khi U7b merge; ma trận AC-35 của U7a chạy qua POST (`TP::TestRecordDecision::test_eligibility_matrix`, giữ)." Tech-lead ghi điều kiện merge cùng lượt vào plan đợt 2.

### Sửa 7 — D-7 (minor H-5): luật ADR-005 trong `catalog.py`, danh sách C-2

**Thêm vào cuối đoạn import của 3.3 (`:135`):** "Đọc dữ liệu chỉ bằng `frappe.db.exists`, `frappe.db.get_value`, `frappe.get_doc` (luật AST ADR-005 của `agent/tools/**`, `test_architecture.py:624-637`: cấm `get_all`, `db.set_value`, `db.sql` ghi, `set_user`, `ignore_permissions`). Kiểm "đội đã có người" đọc `get_doc(...).users`, không `get_all`. Gọi `policy.site_environment()` để đọc môi trường."

**`erp_ai/tests/test_architecture.py`, vùng C-2:** danh sách cho phép của `check_site_environment_readers` thêm **lời gọi** `policy.site_environment(` (mọi file được gọi hàm đọc; tên trường/thuộc tính `site_environment` vẫn chỉ ở các file C-2 đã liệt kê). Thêm một ca xanh dựng bằng chuỗi mẫu (`policy.site_environment()` trong một file `agent/tools/x.py`) và giữ ca đỏ `settings.site_environment` của C-2.

**Test:** `cmd.test_one` cho `erp_ai/tests/test_architecture.py` xanh với `catalog.py` thật (đầu ra dán journal của task).

### Sửa 8 — Phán quyết (7), D-8: danh sách ngoại lệ của phép thử tĩnh FEAT-006 AC-9

**Thay dòng ngoại lệ AC-9 ở `:66` (bảng 1.3) bằng:**

| Cần | Chủ | Trạng thái |
|---|---|---|
| `ROUTE_WORD_EXCEPTIONS: tuple[tuple[str, str], ...] = (("catalog_add_team_member", "user"),)` ngay sau `FORBIDDEN_ROUTE_PARAMETER_WORDS` trong `erp_ai/agent/tools/test_registry.py`; `test_no_tool_schema_takes_person_sla_priority_or_score` bỏ qua đúng các cặp `(spec.name, key)` đó | **U7a** (file đã trong touchpoint `:339`), cùng commit với `catalog_tools.py` | Danh sách duy nhất của ADR-031 Ràng buộc 8. **Không** đưa `email`, `first_name`, `last_name` của `catalog_create_user` (không chạm từ cấm nào); công cụ bản ghi FEAT-004 nhận `doctype`/`values` nên không cần ngoại lệ |

**Test (thêm):** `erp_ai/agent/tools/test_registry.py::TestRegistry::test_route_word_exceptions_are_live` — mỗi cặp phải có: tool có thật trong `REAL_ALL_SPECS()`, khóa có thật trong schema của tool, và khóa chạm ít nhất một từ của `FORBIDDEN_ROUTE_PARAMETER_WORDS`. `test_no_tool_schema_takes_person_sla_priority_or_score` xanh với 7 tool `catalog_*` thật (lớp test giữ tên của file hiện tại).

### Sửa 9 — Phán quyết (8): `policy.py`, `runner.py`, `registry.py` vào touchpoint U7a, có vùng

**Thay hai dòng touchpoint `:335`, `:336` và ghi vùng cho `:334`:**

| File | Thứ tự sửa | Vùng duy nhất của U7a |
|---|---|---|
| `erp_ai/agent/policy.py` | U1 → U2 → U6b → **U7a** → U8 (nếu cần) | 3.1: `CATALOG_RULES_FIELD`, `USER_TEMPLATES_FIELD`, `CatalogRule`, `catalog_rules`, `user_template_roles`. `policy` không import `hard_bans`, `tools` |
| `erp_ai/agent/runner.py` | U1 → U2 → U3 → U4b → U6b → **U7a** | `PROPOSE_TOOLS`; điều kiện ghi bước `propose`; 6 dòng `WRITE_TOOL_TARGETS`; phép chọn hàng trong `_entry_values` (3.9) |
| `erp_ai/agent/tools/registry.py` | U1 → U6b → **U7a** → U8 | `TOOL_MODULES`, `ToolSpec.group`, một dòng `GRANT_TABLE` |

`prompts.py` (khối danh mục) thuộc U7b. Cột "Trong ô U7 của arch-impact?" của hai dòng `policy.py`, `runner.py` đọc là "có, theo phán quyết (8) của `arch-review-design-w2a.md`".

**Test (thêm, minor (b)):** `erp_ai/agent/test_agent_runner.py::TestEntryValues::test_u3_rows_unchanged_for_existing_tools` (subTest cho mỗi tool ghi của U3 trên bảng `_entry_values`: cùng kết quả mẫu → cùng `value_before`/`value_after` như trước U7a, ghim bằng giá trị cụ thể); `::test_catalog_tool_rows` (kết quả có `proposal` → hàng `propose_*`; có `value_before`/`value_after` → hàng 1).

### Sửa 10 — Minor (a): `agent_session` khôi phục bằng `frappe.set_user(previous)`

Giữ 3.2 (`:131`). Luật U1 `test_set_user_agent_only_in_enter_agent_session` chỉ bắt `set_user` có đối số là `AGENT_USER`. Dev U7a ghim bằng một ca: `TArch::TestCatalogArchitecture::test_agent_session_restore_is_not_agent_set_user` (AST `authority.agent_session`: có đúng 1 `set_user(previous)` trong `finally`, 0 `set_user(AGENT_USER)`; luật U1 vẫn xanh). Nếu luật U1 đã build bắt mọi `set_user` trong `authority.py` → `DESIGN_CONFLICT`, báo tech-lead (không sửa luật U1 trong task U7a).

### Sửa 11 — Phán quyết (9): A-U7a-3 không đổi

Không đổi mã hay test. Câu nghiệp vụ "tự gán rồi tự duyệt có được không" vẫn là `NEEDS_ANSWER` không chặn, team-leader chuyển analyst/người. Nếu câu trả lời là "không": thêm vế `assigned_by ≠ user` vào thân `authority.is_assigned` cộng một ca `TAU::TestCanDecide::test_self_assigned_cannot_decide_record`; chữ ký `is_assigned`, `can_decide` không đổi (mục 5 của review).

---

## 2. Touchpoints (thay toàn bộ bảng mục 7, `:323-341`)

| Đường dẫn | Mới/sửa | Căn cứ | Mục |
|---|---|---|---|
| `erp_ai/agent/tools/catalog.py` | mới | ô U7 arch-impact | 3.3 + Sửa 1.2, 5, 7 |
| `erp_ai/agent/tools/catalog_tools.py` | mới | ô U7 | 3.4 |
| `erp_ai/agent/changes/result_comment.py` | **mới (nhánh B)**; nhánh A: sửa | phán quyết (6) | Sửa 3.3 |
| `erp_ai/agent/tools/propose_change.py` | sửa | ô U7 | 3.5 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json` | sửa | ô U7 | 2.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | sửa | ô U7 | 3.8 + Sửa 2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js` | sửa | ô U7 | 3.8 |
| `erp_ai/agent/changes/transitions.py` | sửa | ô U7 | 3.6 |
| `erp_ai/agent/changes/apply_job.py` | sửa | ô U7 | 3.7 + Sửa 1.1, 3.4 |
| `erp_ai/agent/authority.py` | sửa | ô U7 | 3.2 |
| `erp_ai/agent/tools/registry.py` | sửa (vùng Sửa 9) | ô U7 | 3.9 |
| `erp_ai/agent/policy.py` | sửa (vùng Sửa 9) | phán quyết (8) | 3.1 |
| `erp_ai/agent/runner.py` | sửa (vùng Sửa 9) | phán quyết (8) | 3.9 |
| `erp_ai/constants.py` | sửa, đúng 3 hằng | phán quyết (4) | Sửa 4 |
| Test mới: `erp_ai/agent/tools/test_catalog.py`, `erp_ai/agent/tools/test_catalog_tools.py`, `erp_ai/agent/changes/test_result_comment.py` (nhánh B; nhánh A: sửa) | mới | test | mục 8 + Sửa 1.5, 3.6 |
| Test sửa: `erp_ai/agent/test_authority.py`, `erp_ai/agent/test_policy.py`, `erp_ai/agent/changes/test_transitions.py`, `erp_ai/agent/changes/test_apply_job.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/agent/tools/test_registry.py` (thêm `ROUTE_WORD_EXCEPTIONS`, Sửa 8), `erp_ai/agent/test_agent_runner.py` (Sửa 9), `erp_ai/tests/test_architecture.py` (`TestCatalogArchitecture` + danh sách C-2, Sửa 7) | sửa | test | — |

Không chạm: `site_api.py` (U2, hoặc task tách hàm do plan chèn, Sửa 5), `change_decision.py`, `erp_ai/test_change_decision.py` (chữ từ chối giữ, Sửa 2), `run_log.py`, `hard_bans.py`, `erp_ai_setting.*`, `prompts.py`, `ticket_panel.py`, `agent_status_indicator.js`, report thống kê, `daily_report.py`, `ops_data.py`, `missed_scan.py`, `queue.py` (U7a không thêm đích enqueue, phán quyết (2)). Thứ tự merge `test_architecture.py` với U5b: K-5 của review.

**So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
erp_ai/agent/tools/catalog.py                          -> erp_ai  OK
erp_ai/agent/tools/catalog_tools.py                    -> erp_ai  OK
erp_ai/agent/changes/result_comment.py                 -> erp_ai  OK   (nhánh B)
erp_ai/agent/tools/test_catalog.py                     -> erp_ai  OK
erp_ai/agent/tools/test_catalog_tools.py               -> erp_ai  OK
erp_ai/agent/changes/test_result_comment.py            -> erp_ai  OK   (nhánh B)
docs/team/features/FEAT-007/design-addendum-2-U7a-fixes.md -> docs OK
```
**So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào ở bảng touchpoint khớp (không `.env*`, `.pem`, `.key`, `license.txt`) → 0.

---

## 3. Giả định do đội quyết (thay/thêm vào bảng cuối addendum)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U7a-7 | **Bỏ** (H-1) | commit ngầm của DDL làm "một giao dịch" sai | — | — |
| A-U7a-9 | Đề xuất bản ghi commit `Đang áp dụng` trước khi ghi đích, như loại code. Worker chết giữa bước 3 và `finish` để đề xuất ở `Đang áp dụng`, giống loại code hôm nay (ADR-013 QĐ 5); U7a không thêm đường phục hồi | D-1; một dạng xử lý cho mọi loại; mục hành động có `present` cho người đối soát | không commit trước (A-U7a-7 cũ, kẹt khi DDL) | thêm việc dọn `Đang áp dụng` quá hạn ở một đơn vị sau, cần architect |
| A-U7a-10 | Từ chối không đăng comment kết quả | AC-28 chỉ liệt kê áp dụng, lỗi, hết hiệu lực, hoàn tác; từ chối đã có dòng `reject` | comment cả khi từ chối | gọi `_post_result` trong `reject` của controller |
| A-U7a-11 | Mọi lần từ chối của `_decider` dùng đúng chữ cũ của FEAT-004 | chữ đó bị ghim ở `erp_ai/test_change_decision.py` (FEAT-004, ngoài touchpoint) và `TP`; một chữ cho mọi ca nên không lộ đề xuất bản ghi có tồn tại (AC-35); với người bị từ chối, chữ vẫn đúng (họ không có vai trò) | chữ riêng `NOT_ELIGIBLE` cho loại bản ghi (phải sửa test FEAT-004, và chữ khác nhau lộ loại của tên có thật) | đổi `DECIDE_REFUSAL` và hai test ghim, kèm lý do spec AC-35 |
| A-U7a-12 | Lời gọi comment kết quả đặt một chỗ trong `run_change` sau `_locked_run` | mọi đường đã commit trạng thái cuối trước khi trả; một lời gọi nên không thể có kết cục hai comment | gọi ở từng điểm kết thúc | dời lời gọi, test 3.6 giữ nguyên |

---

## 4. Đối chiếu AC (Done criteria, sau sửa)

- AC của spec trong phạm vi U7a (arch-impact hàng U7 ∩ lời gọi): **AC-12, AC-29, AC-30, AC-33, AC-34, AC-35**. Cộng **FEAT-004 AC-28** theo nhánh B (chờ người; analyst `--amend` thành AC của FEAT-007).
- AC có dòng test (addendum mục 8 + file này): **AC-12** (5 dòng), **AC-29** (6), **AC-30** (8 + 2 dòng Custom Field ở Sửa 1.5), **AC-33** (11, dòng `:381` nay bắt buộc, `:380` đổi kỳ vọng, + 2 dòng H-1), **AC-34** (5), **AC-35** (4 + hồi quy chữ ở Sửa 2), **AC-28** (7 dòng ở Sửa 3.6). Khớp 6/6 + AC-28; không dòng test nào có điều kiện (`grep -n "chỉ viết khi"` trên file này chỉ trúng câu này và câu trích ở bảng cuối, không trúng dòng test).
- Test cho mỗi major: H-1 → `TA::TestApplyRecord::test_custom_field_error_after_insert_not_stuck`, `::test_applying_committed_before_execute`; H-2 → `TArch::TestCatalogArchitecture::test_no_role_compare_for_decisions` + `TP::TestRecordDecision::test_unknown_name_non_instructor_permission_error`; H-3 → `TA::TestApplyRecord::test_each_outcome_one_result_comment`.

---

## 5. Bảng đóng: finding, điều kiện, phán quyết → sửa

| Mục của review | Nội dung ngắn | Giải bởi |
|---|---|---|
| H-1 (major) | DDL commit ngầm, đề xuất kẹt `Đang áp dụng` | Sửa 1 |
| H-2 (major) | `_decider` so `ROLE_INSTRUCTOR` | Sửa 2 |
| H-3 (major) | "không có task" sai; test 4 kết cục có điều kiện | Sửa 3 |
| H-4 (minor) | đường giao diện chết giữa U7a và U7b | Sửa 6 |
| H-5 (minor) | luật ADR-005 và C-2 cho `catalog.py` | Sửa 7 |
| minor (a) | `set_user(previous)` trong `agent_session` | Sửa 10 |
| minor (b) | hồi quy hàng U3 của `_entry_values` | Sửa 9 (test) |
| minor (c) | thứ tự `budget_alert` | không phải U7a (U5b) |
| D-1 | bỏ A-U7a-7, commit trước, Custom Field `present` | Sửa 1 |
| D-2 | `can_decide` trong `_decider` | Sửa 2 |
| D-3 | sửa 1.1, 1.2, 1.3, AC-28, test `:381` bắt buộc | Sửa 3 |
| D-4 | `constants.py` vào touchpoint | Sửa 4 |
| D-5 | `permlevel_refusal(..., name=)` | Sửa 5 |
| D-6 | hook quyền là của U7b, merge cùng lượt | Sửa 6 |
| D-7 | đọc bằng `exists`/`get_value`/`get_doc`; C-2 cho phép lời gọi | Sửa 7 |
| D-8 | danh sách ngoại lệ AC-9 | Sửa 8 |
| Phán quyết (4) | 3 hằng, chủ U7a | Sửa 4 |
| Phán quyết (5) | `site_api.permlevel_refusal` công khai của U2 | Sửa 5 |
| Phán quyết (6) | comment kết quả, nhánh B (nhánh A ở 3.7) | Sửa 3 |
| Phán quyết (7) | `ROUTE_WORD_EXCEPTIONS` + test sống | Sửa 8 |
| Phán quyết (8) | `policy.py`, `runner.py`, `registry.py` có vùng | Sửa 9 |
| Phán quyết (9) | A-U7a-3 nghiệp vụ, không chặn | Sửa 11 (không đổi) |
| Phán quyết (1)–(3), G-1, G-2, K-1..K-5 | U5b | không phải U7a; K-5 nhắc ở mục 2 |
| Mục 5 của review (hợp đồng không đổi) | mọi tên giữ nguyên | mở đầu file; tên mới chỉ là thêm |
