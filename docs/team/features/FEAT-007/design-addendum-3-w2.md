Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Không có cổng cho lần sửa này (team.py: chỉ G5). Để trống. -->

# Sửa thiết kế đợt 2 theo phụ lục spec 3 — U7a, U7b + U8 (FEAT-007)

**Phạm vi.** Mỗi dòng của bảng `arch-review-addendum-3.md` mục 6 thuộc `design-addendum-2-U7a.md`, `design-addendum-2-U7a-fixes-2.md`, `design-addendum-2-U7b-U8.md`, `design-addendum-2-U7b-U8-fixes.md` thành một mục sửa (S-n), có chữ thay thế. Căn cứ: ADR-031 Amendment 1 (A1-1..A1-6), ADR-036 QĐ 2, 5, AR3-1..AR3-9.

**Thứ bậc.** File này **thắng** bốn file trên, và cả `design-addendum-2-U7a-fixes.md`, ở đúng các dòng nêu dưới. Dòng khác của chúng giữ nguyên. Tech-lead chép chữ từ file này, không chép từ dòng cũ. Phán quyết `arch-ruling-result-comment.md` B-0..B-16 giữ nguyên, không mục nào dưới đây đụng tới.

**Phụ thuộc spec.** Chữ AC-29, AC-30, AC-33 của `spec-addendum-3.md` mục 3.2 hôm nay vẫn ghi "danh mục rỗng × 6 hành động (5 có tên và đổi trường) → đề xuất". Thiết kế này theo ADR-031 A1-2 và AR3-2, AR3-4: "Đổi trường" và thêm người vào nhóm loại trừ khi không có dòng thì bị từ chối. Analyst phải `--amend` trước khi lập plan đợt 2 (AR3-2). Đây là chỗ lệch với chữ spec chưa sửa, không lệch ADR.

## 0. Căn cứ (đọc trực tiếp ngày 2026-11-14; đã biết đích nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Thứ tự `check` đang thiết kế | input → danh mục → điều cấm cứng → vai trò → môi trường → không đổi | `design-addendum-2-U7a.md:183-191` |
| `rule_mode`, `CheckResult` | `rule_mode(...) -> tuple[str \| None, str \| None]`; `CheckResult` chưa có căn cứ | U7a `:143-144`, `:164` |
| Vị từ nhóm loại trừ | `policy.is_excluded_team(team) -> bool` (đọc `excluded_teams`) | `erp_ai/agent/policy.py:42` |
| Trạng thái đề xuất | `CHANGE_STATUS_PENDING/APPROVED/APPLYING/APPLIED/FAILED/STALE/REJECTED/UNDOING/UNDONE` | `erp_ai/constants.py:22-30` |
| Hàng đợi lần chạy bot | `queue.enqueue_agent_run(ticket_name, trigger)`; job áp dụng `enqueue_change_job` | `erp_ai/agent/queue.py:14`, `:43` |
| Cổng model | runner gọi `gateway.call_model` | `erp_ai/agent/runner.py:128` |
| Trường nhật ký có sẵn để ghi thời gian | ERP AI Log có `latency_ms`; dòng `change` hôm nay không dùng nó | `erp_ai_log.json`; `run_log.write_entry` |
| `decided_at`, `finished_at` | do `transitions` ghi (`:165`, `:266`) | `erp_ai/agent/changes/transitions.py` |
| Logger của `run_change` | `erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s comment=%s` | `erp_ai/agent/changes/apply_job.py:100` |
| Comment "Tự làm", comment site test | đều đi qua `catalog_tools._post_comment` → `write_ticket.post_comment` | U7a-fixes-2 `:144`, `:148`; U7b-U8-fixes `:183` |
| Thiết kế U4b theo ADR-036 | chưa viết (không có `design-addendum-3-w1*`) | `ls docs/team/features/FEAT-007` |

## 1. Hợp đồng cần từ U4b (ADR-036; U4b đặt tên)

U4b đặt tên cho các hợp đồng dưới đây (ADR-036 "Phải làm thêm"). File này tạm gọi chúng bằng tên đề xuất. Nếu U4b đặt tên khác, tech-lead thay chữ theo U4b; hình dạng không đổi.

| # | Cần | Tên đề xuất | Dùng ở |
|---|---|---|---|
| R-1 | Hàm trợ giúp "khóa dòng HD Ticket (`for_update`) + đọc có khóa", trả **tên và trạng thái** các bản ghi khớp, không chỉ số đếm | `ticket_lock.locked_find(ticket_name, doctype, filters, fields) -> list[dict]` | S-6 (chống trùng đề xuất) |
| R-2 | Cờ "lần chạy này đưa hướng" trên `ToolContext` | `ctx.direction_run: bool` (mặc định `False`) | S-5, S-6, S-8 |
| R-3 | Bộ gom theo `run_id` với ba mục | `collector.add(ctx, section, line_html) -> None`; `SECTION_DONE` ("Đã làm"), `SECTION_PENDING` ("Chờ duyệt"), `SECTION_DECIDE` ("Cần ai quyết") | S-5, S-6, S-8 |
| R-4 | Dòng đề xuất chỉ vào bộ gom tại `insert_proposal` (S-6). U4b không thêm dòng "Chờ duyệt" ở chỗ khác | — | ADR-036 QĐ 2, 5 |

## 2. Mục sửa U7a

### S-1 Thứ tự `check` theo ADR-031 A1-1
- **Cũ:** `design-addendum-2-U7a.md:183-191`. Kéo theo: `:191` ("Đạt cả 6"), `:195` (`undo` "bước 1, 3, 5"), `:197` (`check_edit` "đủ 6 bước").
- **Mới:**

  **`check` — thứ tự cố định (ADR-031 A1-1), trả kết cục đầu tiên khớp, không ghi gì:**
  1. **Đầu vào.** Giữ nguyên chữ bước 1 cũ (`:184`). Thêm cho tạo tài khoản: `policy.user_template_roles(template)` trả `None` → `TEMPLATE_MISSING`. Dòng này dời từ bước 4 cũ: tham số trỏ vào mẫu không có.
  2. **Điều cấm cứng.** Giữ nguyên chữ bước 3 cũ (`:186`), cộng phần vai trò cấm của bước 4 cũ: giao với `site_api.FORBIDDEN_ROLES` (so `casefold`) → `FORBIDDEN_ROLE`. Bảng con (`istable = 1`) bị chặn **trong** `hard_bans.hard_ban_reason`, dẫn xuất từ meta. Đó là task chèn AR3-3 ở đợt 1 (`hard_bans.py`). U7a không tự kiểm `istable` và không lập danh sách tên. Lý do ra ở bước này không chứa chữ "danh mục".
  3. **Cổng môi trường.** Giữ nguyên chữ bước 5 cũ (`:188`) → `TEST_SITE_ONLY`, `test_site_only=True`.
  4. **Dòng `Cấm`.** `rule_mode` chọn ứng viên: dòng cùng `action`, cùng `target_doctype` (Đổi trường theo `doctype`, Tạo Custom Field theo `dt`), `category ∈ categories`. Có ứng viên `Cấm` → `RULE_DENIED`. Với Đổi trường, ứng viên `Cấm` phải giao trường khác rỗng. `category` None → không dòng nào khớp.
  5. **Dòng phủ.** Có ứng viên không-`Cấm` phủ yêu cầu (Đổi trường: tập khóa ⊆ `fields`) → `mode` = `Cần duyệt` nếu một dòng phủ là `Cần duyệt`, ngược lại `Tự làm`. `basis = {"source": "rule", "rule": {"action", "target_doctype", "fields": sắp xếp, "categories": sắp xếp, "mode"}}`, là ảnh chụp dòng quyết định (dòng có `idx` nhỏ nhất trong các dòng mang chế độ đã chọn).
  6. **Không dòng phủ.** `default_needs_approval(request.action, request.args)` đúng → `mode = MODE_NEEDS_APPROVAL`, `basis = {"source": "default"}`. Sai → `OUT_OF_CATALOG`.
  7. **Không đổi.** Giữ nguyên chữ bước 6 cũ (`:189`) → `NO_CHANGE`.

  Đạt cả 7 bước → `CheckResult(ok=True, mode=…, watched=…, basis=…)`. Bước 2–4 không phụ thuộc chế độ.
  - `rule_mode(rules, request, doctype, fields) -> RuleOutcome`, với `RuleOutcome(denied: bool, mode: str | None, basis: dict | None)` frozen. Hàm chỉ xét dòng, không biết mặc định (bước 6 nằm trong `check`).
  - `CheckResult` thêm trường `basis: dict | None = None`.
  - **`undo`** (thay `:195`): chạy bước 1, 2, 3 của `check` (đầu vào, điều cấm cứng, môi trường; không xét danh mục). Phần còn lại giữ nguyên.
  - **`check_edit`** (thay "đủ 6 bước" ở `:197`): "đủ 7 bước". `basis` của kết quả bị bỏ qua: căn cứ của đề xuất là nội dung bất biến (S-4), lần sửa không đổi nó.
- **Vì:** AC-29, AC-30, AC-33 `[changed]`; AR3-1; ADR-031 A1-1, A1-3, A1-4.

### S-2 Tập "mặc định Cần duyệt"; "Đổi trường" và nhóm loại trừ không dòng thì từ chối
- **Cũ:** `design-addendum-2-U7a.md:177` (hàng `ACTION_ADD_TEAM_MEMBER`), `:181` (hàng `ACTION_UPDATE_FIELDS`). Khối hằng `:156-162`.
- **Mới:** thêm vào khối hằng của `catalog.py`, ngay sau `RESTORABLE_ACTIONS`:
  ```python
  FIXED_SURFACE_ACTIONS = (ACTION_CREATE_USER, ACTION_ADD_TEAM_MEMBER, ACTION_ADD_HOLIDAY,
                           ACTION_SET_ITEM_GROUP, ACTION_CREATE_CUSTOM_FIELD)   # ADR-031 A1-2; U8 nối ACTION_CREATE_PROJECT
  def default_needs_approval(action: str, args: dict) -> bool
      # action ∈ FIXED_SURFACE_ACTIONS và không (action == ACTION_ADD_TEAM_MEMBER và policy.is_excluded_team(args.get("team")))
  ```
  - Hàng `:177` thêm cuối cột "Ghi": "Nhóm thuộc `excluded_teams` (`policy.is_excluded_team`) nằm ngoài tập A1-2: không dòng phủ → `OUT_OF_CATALOG`."
  - Hàng `:181` thêm cuối cột "Ghi": "∉ `FIXED_SURFACE_ACTIONS`: không dòng phủ → `OUT_OF_CATALOG`, 0 đề xuất."
  - Tập này được định nghĩa đúng một lần, trong `catalog.py`. `catalog_tools.py`, `registry.py`, `prompts.py` chỉ import (ADR-031 Ràng buộc A1). Không lập danh sách nhóm thứ hai: vị từ nhóm lấy từ `policy.py`.
- **Vì:** AR3-2, AR3-4; AC-29 (sau amend); ADR-031 A1-2.

### S-3 Nghĩa mới của `OUT_OF_CATALOG`, `RULE_DENIED`; chữ căn cứ
- **Cũ:** `design-addendum-2-U7a.md:199` (hai hằng đầu), `:274` (hàng hợp đồng chữ).
- **Mới `:199`:**
  - `OUT_OF_CATALOG = "cần dòng danh mục: việc này chỉ làm được khi danh mục trắng có dòng Cần duyệt hoặc Tự làm cho nó ở đầu mục của phiếu"`. Chỉ trả cho hành động ngoài tập A1-2 không có dòng phủ (bước 6).
  - `RULE_DENIED = "danh mục cấm việc này"`.
  - Thêm `MODE_BASIS_DEFAULT = "Căn cứ chế độ: không có dòng danh mục cho việc này, mặc định Cần duyệt"`.
  - Thêm `MODE_BASIS_RULE = "Căn cứ chế độ: dòng danh mục «{action}»{doctype} · đầu mục {categories} · chế độ {mode}"`. `{doctype}` là `" trên {target_doctype}"` khi có, rỗng khi không. `{categories}` nối bằng `", "`.
  - Thêm `MODE_BASIS_SOURCES = ("rule", "default")` và `def mode_basis_text(basis: dict) -> str` (chữ thô, người gọi tự thoát HTML). Đây là bộ dựng duy nhất cho comment và ngăn (STD-DESIGN-4).
  - Các hằng khác giữ nguyên. `HARD_BAN`, `FORBIDDEN_ROLE`, `TEMPLATE_MISSING`, `TEST_SITE_ONLY` không chứa "danh mục". Mọi chữ ≤ `site_api.REASON_MAX`.
- **Mới `:274`:** "Chữ `OUT_OF_CATALOG` (nghĩa: 'cần dòng danh mục'), `RULE_DENIED` ('danh mục cấm việc này'), `TEST_SITE_ONLY`, `NO_CHANGE`, `STALE_TARGET`, `MODE_BASIS_DEFAULT`, `MODE_BASIS_RULE` | 3.3 | `catalog.py` | U7b test, U8 test". Thêm hai hàng vào bảng 3.11:
  - `FIXED_SURFACE_ACTIONS`, `default_needs_approval`, `mode_basis_text`, `CheckResult.basis` | S-1..S-3 | `catalog.py` | U7b (ngăn, qua `record_summary`), U8 (nối `ACTION_CREATE_PROJECT`)
  - `DUPLICATE_BLOCKING_STATUSES`, `pending_line` | S-6 | `propose_change.py` | bộ gom U4b (qua `insert_proposal`)
- **Vì:** AC-29; AR3-1.

### S-4 Căn cứ chế độ là nội dung bất biến của đề xuất
- **Cũ:** `design-addendum-2-U7a.md:76-93` (bảng trường 2.1, `RECORD_CONTENT_FIELDS`, `RECORD_DIGEST_FIELDS`), `:210` (`_propose` bước 5), `:217` (`_comment`), `:248` (`validate`).
- **Mới:**
  - Bảng 2.1 thêm hàng: `mode_basis` | Code (JSON) | nội dung | `propose_change.insert_proposal` | căn cứ chế độ: `{"source": "rule", "rule": {...}}` hoặc `{"source": "default"}` (ADR-031 A1-5).
  - `RECORD_CONTENT_FIELDS` nối `"mode_basis"` vào cuối. `RECORD_DIGEST_FIELDS` nối `"mode_basis"` vào cuối. Dấu của loại code giữ đúng `DIGEST_FIELDS`.
  - `_propose` bước 5 (`:210`): dict giá trị thêm `"mode_basis": json.dumps(result.basis, ensure_ascii=False, sort_keys=True)`.
  - `validate` lúc tạo, loại bản ghi (`:248`): `mode_basis` là JSON object, `source ∈ catalog.MODE_BASIS_SOURCES`, có khóa `rule` khi và chỉ khi `source == "rule"` → sai thì `ValidationError`.
  - `_comment` nhánh `CHANGE_KIND_RECORD` (`:217`): sau dòng `Căn cứ: {reason}` thêm một dòng `escape_html(catalog.mode_basis_text(json.loads(mode_basis)))`. Câu đầu tách thành `pending_line(values) -> str` (xem S-6). `_comment` gọi lại nó.
  - `record_summary` (U7a-fixes-2 3.3 và U7b-U8 3.3) thêm khóa `mode_basis` = `catalog.mode_basis_text(...)`, chữ thô.
- **Vì:** AR3-5; ADR-031 A1-5; AC-33.

### S-5 Comment "cần làm trên site test" và việc bị từ chối, trong lần đưa hướng
- **Cũ:** `design-addendum-2-U7a.md:208` (`_propose` bước 3), `:212`; `design-addendum-2-U7a-fixes-2.md:144` (chữ thay bước 3), `:161` (test).
- **Mới, bước 3 của `_propose`** (thay `fixes-2:144`):

  "Không đạt: trả `{"ok": False, "reason": result.reason}`, không tạo đề xuất. Trước đó:
  - **`ctx.direction_run` đúng (R-2), lần đưa hướng:** 0 comment.
    - `result.test_site_only` và `ctx.run_id ∉ frappe.local.flags.erp_ai_test_site_runs` → `collector.add(ctx, SECTION_DECIDE, TEST_SITE_COMMENT.format(action=escape_html(action), doctype=escape_html(result.doctype)))`, rồi nhớ `ctx.run_id`.
    - Lý do ở bước 2, 4, 6 của `check` → `collector.add(ctx, SECTION_DECIDE, REFUSED_LINE.format(action=escape_html(action), reason=escape_html(result.reason)))`.
  - **`ctx.direction_run` sai, lần chạy khác:** giữ đúng chữ `fixes-2:144`: 1 comment `_post_comment` mỗi `run_id` khi `test_site_only`; lý do khác không comment.
  - Bước 1 (tham số sai) và bước 7 (không đổi): không dòng bộ gom, không comment."

  Hằng mới `REFUSED_LINE = "Việc «{action}» không làm được: {reason}. Người phụ trách làm tay nếu cần."`. `TEST_SITE_COMMENT` (`:212`) giữ chữ, dùng cho cả comment lẫn dòng bộ gom.
- **Vì:** AC-23 `[changed]`, AC-12, AC-67 (việc bị cấm nêu ở "Hướng xử lý"); ADR-036 QĐ 2, Ràng buộc 3.

### S-6 Chống trùng đề xuất trên đường chèn duy nhất
- **Cũ:** `design-addendum-2-U7a.md:209-210` (`_propose` bước 4–5), `:216` (`insert_proposal`), `:255` (`runner.py`, điều kiện ghi bước `propose`).
- **Mới `:216`**, thêm sau gạch đầu:
  - `insert_proposal(ctx, values)`. Chỉ khi `values["change_kind"] == CHANGE_KIND_RECORD`, trước `insert`: `existing = ticket_lock.locked_find(ctx.ticket_name, PROPOSAL_DOCTYPE, filters={"ticket": ctx.ticket_name, "change_kind": CHANGE_KIND_RECORD, "catalog_action", "target_doctype", "target_name", "action_args": values["action_args"], "change_status": ("in", DUPLICATE_BLOCKING_STATUSES)}, fields=["name", "change_status"])` (R-1). Hàm khóa dòng HD Ticket và đọc có khóa (ADR-036 QĐ 4).
  - So `action_args` bằng chuỗi JSON chuẩn: `sort_keys=True`, `ensure_ascii=False`, đúng phép dựng của `_propose` bước 5. Cùng tham số cho ra cùng chuỗi. `confidence_pct`, `reason`, `mode_basis` không nằm trong khóa so.
  - Có `existing` → không chèn, không comment AC-33. Trả `{"ok": True, "proposal": existing[0].name, "status": existing[0].change_status, "comment": "", "duplicate": True}`.
  - `DUPLICATE_BLOCKING_STATUSES = (CHANGE_STATUS_PENDING, CHANGE_STATUS_APPROVED, CHANGE_STATUS_APPLYING)`, hằng của `propose_change.py`. Đề xuất đã kết thúc không chặn. Ví dụ: sau Từ chối, người `@ai` nhờ lại → có đề xuất mới (AC-67). Đề xuất đã áp dụng thì bước 7 (`NO_CHANGE`) đã chặn trước.
  - Bộ gom (R-3, R-4): khi `ctx.direction_run`, sau một lần chèn mới (mọi loại) hoặc một lần trùng có trạng thái `Chờ duyệt` → `collector.add(ctx, SECTION_PENDING, pending_line(doc))`. `pending_line` là câu đầu của `_comment` cộng dòng căn cứ chế độ (loại bản ghi). Bộ dựng tóm tắt dùng lại, không viết bộ mới (STD-DESIGN-4).
  - Loại code và lệnh bench không chống trùng (ADR-036 QĐ 5 chỉ áp cho loại bản ghi).
- **Mới `:255`:** điều kiện ghi bước `propose` thành `name in PROPOSE_TOOLS and outcome.get("ok") and outcome.get("proposal") and not outcome.get("duplicate")`.
- `catalog_tools.py` không chứa phép so trùng nào (ADR-036 Ràng buộc).
- **Vì:** AC-67, NFR-3; ADR-036 QĐ 4, 5; AR3-6 (phần U7a).

### S-7 AC-68: không gọi model sau Duyệt; thời gian Duyệt → kết quả
- **Cũ:** `design-addendum-2-U7a.md:226-227` (`finish`, `log_step`), `:239` (`_run_record` bước 4), `:241` (logger), `:377`, `:381` (test).
- **Mới:**
  - `transitions.log_step(..., actions=None, latency_ms: int | None = None)`, `finish(..., actions=None, latency_ms=None)`: truyền nguyên xuống `write_entry(latency_ms=…)`. `latency_ms` là trường có sẵn của ERP AI Log. Không thêm trường mới.
  - `_run_record` bước 4, chỉ với action apply: `latency_ms = int((now_datetime() - get_datetime(proposal.decided_at)).total_seconds() * 1000)`, truyền vào `finish` của cả ba kết cục `applied`, `refused`, `stale`. Undo không ghi.
  - Logger của `run_change` (`:241`) thêm `approve_to_result_ms=%s`, tính từ `decided_at` → `finished_at` đã lưu. Undo hoặc `OUTCOME_SKIPPED` ghi `-`.
  - Đường áp dụng không đổi: `apply_job` → `catalog.execute` với `action_args`/`edited_args` đã lưu. Không import Cổng model. Comment kết quả là dòng `Info` của `post_result` (ADR-035 QĐ 7, B-6, B-11).
- **Vì:** AC-68; AR3-9; NFR-2 bổ sung.

### S-8 (U7a, bước 4 của `_propose`) Giữ
- `design-addendum-2-U7a.md:209`: chữ giữ nguyên ("U7a luôn tạo đề xuất"; điểm chen của U7b). Đề xuất theo mặc định (bước 6) đi cùng đường với dòng `Cần duyệt`.

## 3. Mục sửa U7b + U8

### S-9 "Tự làm": báo qua bộ gom hoặc 1 comment của agent, không qua `post_result`
- **Cũ:** `design-addendum-2-U7b-U8.md:200` (nhánh `applied`); `design-addendum-2-U7b-U8-fixes.md:183` (chữ thay nhánh `applied`), `:184` (nhánh khác); `design-addendum-2-U7b-U8.md:268` và `-fixes.md:188` (luồng 4.2).
- **Mới, thay `fixes:183`:**

  "`ex.outcome == "applied"` → dựng `html = AUTO_DONE_COMMENT.format(...)` (mọi giá trị qua `escape_html`; `changes` = `key: trước → sau`).
  - `ctx.direction_run` đúng: `collector.add(ctx, SECTION_DONE, html)`, 0 comment, khóa `comment` = `""`.
  - `ctx.direction_run` sai: đúng 1 comment qua `catalog_tools._post_comment(ctx, html)`, tức `Comment` dưới tài khoản agent (ADR-033 QĐ 1).
  - Không bao giờ gọi `result_comment.post_result` hay tạo dòng `Info` (ADR-035 QĐ 7 chỉ dành cho kết cục của đề xuất).
  - Trả `{"ok": True, "auto": True, "doctype", "name", "value_before", "value_after", "comment"}`. Runner ghi 1 mục hành động như cũ. Lượt lỗi sau đó: rollback như cũ."
- **Mới, thay `fixes:184`:** "khác → `{"ok": False, "reason": ex.reason}`; không tạo đề xuất. Khi `ctx.direction_run` → `collector.add(ctx, SECTION_DECIDE, REFUSED_LINE.format(...))` (AC-66: việc bộ thực thi từ chối ghi ở 'Cần ai quyết'). Ngược lại không comment. Đích không đổi."
- **Mới luồng 4.2:** thay "→ 1 comment báo lại + 1 mục hành động" bằng "→ dòng 'Đã làm' qua bộ gom (lần đưa hướng) hoặc 1 comment của agent (lần chạy khác) + 1 mục hành động trong dòng `reason`".
- **Vì:** AC-36 `[changed]`, AC-66; AR3-8; ADR-036 QĐ 2, Ràng buộc 3.

### S-10 Tạo Project luôn là đề xuất, không cần dòng
- **Cũ:** `design-addendum-2-U7b-U8.md:270` (luồng 4.3); `design-addendum-2-U7b-U8-fixes.md:214` (hàng `catalog.py` của commit U8).
- **Mới 4.3:** "Phiếu C, `level_cap_c ≥ L2` (A-U7b-7) → `catalog_create_project` → `catalog.check`:
  - không dòng → bước 6: `ACTION_CREATE_PROJECT ∈ FIXED_SURFACE_ACTIONS` → đề xuất, `basis` mặc định;
  - dòng `Cấm` → `RULE_DENIED`, 0 đề xuất;
  - dòng `Cần duyệt` → đề xuất, `basis` theo dòng;
  - dòng `Tự làm` → `auto_mode_allowed` sai ở vế `approval_only` (`APPROVAL_ONLY_ACTIONS` giữ) → đề xuất.

  Rồi người duyệt hợp lệ duyệt (ngăn hoặc form) → job → `catalog.execute` → Project + gắn Task của phiếu → `Đã áp dụng`. 0 Project trước Duyệt."
- **Mới `fixes:214`:** "`ACTION_HANDLERS[ACTION_CREATE_PROJECT]` theo bảng `:207-218`; nối `ACTION_CREATE_PROJECT` vào cuối `FIXED_SURFACE_ACTIONS` trong cùng commit".
- **Vì:** AC-64 `[changed]`; ADR-031 A1-2.

### S-11 Ngăn: hiện căn cứ chế độ; mọi đề xuất `Chờ duyệt` hiện cùng lúc
- **Cũ:** `design-addendum-2-U7b-U8.md:114` (`_proposals`), `:116-123` (bảng khóa), `:142` (`renderProposals`), `:266` (luồng 4.1).
- **Mới:**
  - `_proposals(ticket)` dùng hai `frappe.get_list` dưới phiên người dùng, cùng hook và cùng bước `has_permission("read")` như cũ:
    - (a) `change_status = CHANGE_STATUS_PENDING`, `limit_page_length=0`, `order_by="creation asc"`;
    - (b) `change_status != CHANGE_STATUS_PENDING`, `limit_page_length=PANEL_PROPOSAL_LIMIT`, `order_by="creation desc"`.

    Kết quả = (a) + (b). Số đề xuất chờ có giới hạn tự nhiên nhờ chống trùng (S-6).
  - Bảng khóa thêm hàng: `mode_basis` | `proposal_controller.record_summary(doc)["mode_basis"]` (chữ thô).
  - `renderProposals`: sau dòng `Căn cứ: ...` thêm một dòng `mode_basis` (gán `textContent`). Không hằng chữ mới ở JS: chữ đã có tiền tố "Căn cứ chế độ:".
  - Luồng 4.1 thêm sau "mục 'Đề xuất chờ duyệt'": "hiện mọi đề xuất `Chờ duyệt` của phiếu cùng lúc, mỗi đề xuất có dòng căn cứ chế độ".
- **Vì:** AC-67, AC-39; AR3-5; ADR-031 A1-5.

### S-12 Test U7b + U8 viết lại
- `design-addendum-2-U7b-U8.md:352` và `:372`: thay theo mục 6 dưới đây (T-20, T-21, T-24..T-26).

## 4. Sửa thêm ngoài bảng mục 6 (cần để AC-67 đạt)

### E-1 `catalog_list_allowed` và `CATALOG_BLOCK` không được nói "chỉ dòng mới được phép"
- **Cũ:** `design-addendum-2-U7a.md:203` (tool đọc chỉ trả dòng không-`Cấm`); `design-addendum-2-U7b-U8.md:237` (`CATALOG_BLOCK`: "Gọi catalog_list_allowed trước để biết việc được phép cho đầu mục của phiếu").
- **Lý do.** Với danh mục rỗng, tool trả `[]`. Prompt bảo model chỉ làm việc có trong danh sách, nên model không gọi tool ghi → 0 đề xuất. AC-67 ("danh mục rỗng, 2 hành động → 2 đề xuất") vì vậy hỏng.
- **Mới `:203`:** `catalog_list_allowed` trả `{"rows": [như cũ], "default_needs_approval": list(FIXED_SURFACE_ACTIONS), "note": LIST_ALLOWED_NOTE}`, với `LIST_ALLOWED_NOTE = "Hành động trong default_needs_approval gọi được khi không có dòng: kết quả là đề xuất chờ duyệt, trừ khi bị cấm. Đổi trường và thêm người vào nhóm loại trừ cần dòng."`.
- **Mới `:237`:** câu thứ ba của `CATALOG_BLOCK` thành: "Gọi catalog_list_allowed để biết dòng danh mục của đầu mục phiếu và các hành động mặc định chờ duyệt; việc không có dòng vẫn gọi tool được, kết quả là đề xuất hoặc lời từ chối có lý do." `PROMPT_CONFLICT_PAIRS` không đổi.
- **Vì:** AC-67, AC-29 `[changed]`. Không đổi hình dạng ADR nào. Architect xem lại nếu muốn.

## 5. Dữ liệu, migration, quan sát

- Một cột mới `mode_basis` trên ERP AI Change Proposal, nằm trong cùng thay đổi JSON của U7a (U7a chưa dựng). Không thêm bước migration: `cmd.migrate` của U7a tạo luôn cột này.
- Bước xuống ở mục 6 của U7a thêm `mode_basis` vào danh sách cột bỏ.
- Đối chiếu: trước U7a chưa có đề xuất loại bản ghi nào, nên 0 dòng cần điền lại. Kiểm bằng `select count(*) … where change_kind = 'Thay đổi bản ghi'` = 0 trước migrate, dán vào As-Built.
- Quan sát:
  - logger `erp_ai catalog action=… outcome=… env=…` (U7a `:193`) thêm `basis=rule|default`;
  - logger `run_change` thêm `approve_to_result_ms` (S-7);
  - dòng `apply` có `latency_ms`;
  - trùng đề xuất: 1 dòng `frappe.logger(LOGGER_NAME).info("erp_ai proposal duplicate ticket=%s proposal=%s", …)`.
- `catalog_approvals.record_proposals` (U7b 3.4) thêm `mode_basis` vào tập trường trả về, để AC-37 tách được theo căn cứ (A1-5). Report không đổi cột.

## 6. Touchpoints (thêm vào ô U7a, U7b, U8; không đơn vị mới)

| File | Sửa | Đơn vị |
|---|---|---|
| `erp_ai/agent/tools/catalog.py` | S-1, S-2, S-3, logger `basis` | U7a; U8 nối 1 phần tử vào `FIXED_SURFACE_ACTIONS` |
| `erp_ai/agent/tools/catalog_tools.py` | S-5, S-9, E-1 | U7a (S-5, E-1), U7b (S-9) |
| `erp_ai/agent/tools/propose_change.py` | S-4 (`_comment`), S-6 (`insert_proposal`, `pending_line`, `DUPLICATE_BLOCKING_STATUSES`) | U7a |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json`, `.py` | S-4 (`mode_basis`, `validate`, `record_summary`) | U7a |
| `erp_ai/agent/changes/transitions.py`, `apply_job.py` | S-7 | U7a |
| `erp_ai/agent/runner.py` | S-6 (`:255`, điều kiện `duplicate`) | U7a |
| `erp_ai/ticket_panel.py`, `erp_ai/public/js/agent_status_indicator.js` | S-11 | U7b |
| `erp_ai/agent/prompts.py` | E-1 (`CATALOG_BLOCK`) | U7b |
| `erp_ai/agent/tools/catalog_approvals.py` | mục 5 (`mode_basis`) | U7b |
| Test: `erp_ai/agent/tools/test_catalog.py`, `test_catalog_tools.py`, `test_propose_change.py`, `erp_ai/agent/changes/test_apply_job.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/tests/test_ticket_panel.py`, `erp_ai/tests/test_architecture.py`, `erp_ai/agent/test_agent_runner.py` | mục 7 | như trên |

Phụ thuộc thêm: U4b (R-1..R-4) và task chèn AR3-3 (`hard_bans.py`) phải merge trước U7a. Đúng ô "U7 Phụ thuộc" của `arch-review-addendum-3.md` mục 7.

**Đường dẫn mới so với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
docs/team/features/FEAT-007/design-addendum-3-w2.md -> docs OK
(không file mã mới; mọi file ở bảng trên đã có trong ô U7a/U7b/U8 và nằm dưới erp_ai -> OK)
```
**So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào khớp → 0.

## 7. Test plan (viết lại hoặc thêm)

Chạy qua `cmd.test_one` với `{file}` là đường dẫn. Ký hiệu như U7a `:357` và U7b `:341`: `TC`, `TT`, `TA`, `TP`, `TArch`, `TPN`, `TRN`. Thêm `TPC` = `erp_ai/agent/tools/test_propose_change.py`. Mọi test tool dựng `ctx.direction_run` tường minh. Test viết lại vì spec đổi ghi lý do ở commit (NFR-8, STD-TEST-5). Chưa có mã nên không assertion nào đã merge bị đổi.

| # | Thay / thêm | Test (`file::Class::name`) | Kiểm | AC / AR3 |
|---|---|---|---|---|
| T-1 | thay U7a `:361` (test 1) | `TC::TestRuleMode::test_empty_catalog_fixed_surface_actions_need_approval` | danh mục rỗng × 5 hành động của `FIXED_SURFACE_ACTIONS` (thêm người vào nhóm thường) → `ok`, `mode = Cần duyệt`, `basis = {"source": "default"}`, DB trước = sau | AC-29, AC-30 |
| T-2 | thêm | `TC::TestRuleMode::test_empty_catalog_update_fields_refused` | rỗng × Đổi trường → `OUT_OF_CATALOG`, chữ chứa "cần dòng danh mục" | AC-29; AR3-2 |
| T-3 | thêm | `TC::TestRuleMode::test_empty_catalog_excluded_team_refused` | rỗng × thêm người vào nhóm ∈ `excluded_teams` → `OUT_OF_CATALOG`; cùng ca với nhóm thường → đạt (biên) | AR3-4; NFR-1 |
| T-4 | thay U7a `:361` (test 2) | `TT::TestProposeFlow::test_empty_catalog_creates_proposals` | mỗi tool của 5 hành động → `ok=true`, 1 đề xuất `Chờ duyệt`, `mode_basis` mặc định, 1 comment AC-33 có dòng `MODE_BASIS_DEFAULT`, đích không đổi | AC-29, AC-30, AC-33 |
| T-5 | thêm | `TT::TestProposeFlow::test_empty_catalog_update_fields_no_proposal`; `::test_excluded_team_without_row_no_proposal` | `ok=false`, 0 đề xuất, 0 comment | AR3-2, AR3-4 |
| T-6 | thay U7a `:362` | `TC::TestRuleMode::test_one_row_opens_only_its_scope` (chỉ Đổi trường: khác hành động, khác DocType, trường ngoài `fields`, đầu mục khác, `category` None → `OUT_OF_CATALOG`); `::test_row_scope_for_fixed_surface_falls_to_default` (dòng `Tự làm` "Đổi nhóm hàng" đầu mục B, phiếu D → `Cần duyệt`, căn cứ mặc định) | biên: trường thứ hai ngoài dòng; đầu mục None | AC-29 |
| T-7 | sửa U7a `:363` | `TC::TestRuleMode::test_deny_row_wins` (chữ đúng `"danh mục cấm việc này"`); thêm `::test_deny_row_on_fixed_surface_refuses` (rỗng trừ 1 dòng `Cấm` "Đổi nhóm hàng" B → `RULE_DENIED`); `::test_needs_approval_row_same_as_default_except_basis` (`mode` bằng nhau, `basis` khác) | — | AC-29 |
| T-8 | thêm | `TC::TestCheckOrder::test_hard_ban_beats_deny_row` (đích cấm cứng + dòng `Cấm` → `HARD_BAN`); `::test_environment_beats_deny_row` (`production` + `Cấm` → `TEST_SITE_ONLY`); `::test_hard_ban_beats_environment`; `::test_environment_before_out_of_catalog` (Đổi trường trên Server Script, rỗng, `production` → `TEST_SITE_ONLY`); `::test_no_change_is_last` (hành động trong tập, đích đã ở giá trị → `NO_CHANGE`); `::test_steps_2_3_never_mention_catalog` (mọi lý do ở bước 2–3 của các ca trên, kể cả chữ `hard_ban_reason` của `DocPerm`, `Role`, một DocType app → không chứa "danh mục") | 4 cặp thứ tự | AC-29; AR3-1; ADR-031 A1 Ràng buộc |
| T-9 | thay U7a `:364` | `TT::TestProposeFlow::test_rule_added_between_calls_takes_effect` (chỉ Đổi trường: gọi → `OUT_OF_CATALOG`; lưu Setting thêm dòng `Cần duyệt`; gọi lại → đề xuất); thêm `::test_deny_row_added_between_calls_takes_effect` ("Đổi nhóm hàng": đề xuất → thêm `Cấm` → `RULE_DENIED`) | — | AC-29 |
| T-10 | thêm sau U7a `:365` | `TC::TestHardBans::test_child_tables_refused` (`DocPerm`, `Has Role`, một DocType `istable = 1` tìm động; có dòng `Tự làm` Đổi trường cho chính DocType đó → vẫn `HARD_BAN`, 0 ghi); `TT::TestProposeFlow::test_hard_bans_with_empty_catalog_no_proposal` (rỗng × xóa/Role Permission/chứng từ submit/DocType app/vai trò cấm → `ok=false`, 0 đề xuất) | cần task AR3-3 đã merge | AC-29; AR3-3 |
| T-11 | thêm sau U7a `:374` | `TT::TestProposeFlow::test_empty_catalog_target_unchanged_until_approval` (rỗng, "Đổi nhóm hàng" → đề xuất, Item không đổi; duyệt + chạy job → Item đổi) | — | AC-33 `[changed]` |
| T-12 | thay U7a `:380` (test 1) | `TA::TestApplyRecord::test_update_fields_rule_removed_before_job_fails` (`Lỗi` `OUT_OF_CATALOG`, 0 thay đổi); `::test_fixed_surface_rule_removed_before_job_applies` (dòng `Cần duyệt` "Đổi nhóm hàng" bị xóa giữa tạo và job → `Đã áp dụng`); `::test_deny_row_added_before_job_fails` (`Lỗi` `RULE_DENIED`, 0 thay đổi) | 3 ca A1-3 | AC-33; ADR-031 A1-3 |
| T-13 | thêm | `TA::TestApplyRecord::test_mode_basis_changed_after_approval_fails` (`db.set_value` đổi `mode_basis` sau duyệt → `Lỗi` `DIGEST_CHANGED`); `TP::TestERPAIChangeProposal::test_record_content_immutable` thêm `mode_basis`; `TP::TestERPAIChangeProposal::test_mode_basis_validated` (`source` lạ; `rule` thiếu khi `source=rule` → `ValidationError`) | — | AR3-5 |
| T-14 | thêm | `TPC::TestRecordComment::test_mode_basis_line` (mặc định → `MODE_BASIS_DEFAULT`; theo dòng → `MODE_BASIS_RULE` có hành động, đầu mục, chế độ; giá trị `<script>` đã thoát) | HTML trong giá trị | AR3-5; AC-33 |
| T-15 | thêm (thay ý U7a `:377`, `:381` cho AC-68) | `TA::TestApplyRecord::test_approve_runs_without_model_or_agent_run`: patch `erp_ai.agent.runner.gateway.call_model` (spy ném nếu bị gọi) và `erp_ai.agent.queue.enqueue_agent_run` (spy); duyệt qua controller `approve`, chạy job đồng bộ. Kết quả: 0 lời gọi model; 0 lời gọi `enqueue_agent_run`; Item đổi; đúng 1 dòng `Info` kết quả mới (đường `post_result`); đúng 1 dòng `change` bước `apply` có 1 mục hành động và `latency_ms` = `finished_at − decided_at` (ms, ≥ 0, sai số ≤ 1000) | — | AC-68; AR3-9 |
| T-16 | thêm | `TA::TestApplyRecord::test_latency_on_failed_and_stale` (`Lỗi`, `Hết hiệu lực` cũng có `latency_ms`; hoàn tác không có) | 3 kết cục | AC-68 |
| T-17 | thêm | `TT::TestProposeFlow::test_same_proposal_twice_two_runs_one_proposal` (hai `run_id`, cùng hành động, đích, tham số → 1 đề xuất, lần hai `duplicate: true`, tổng 1 comment AC-33); `::test_different_value_new_proposal`; `::test_rejected_then_again_new_proposal`; `::test_approved_or_applying_blocks` (`Đã duyệt`, `Đang áp dụng` → trùng); `::test_insert_proposal_uses_locked_helper` (patch R-1, gọi đúng 1 lần với `PROPOSAL_DOCTYPE`); `TRN::TestProposalDedupe::test_duplicate_writes_no_propose_step` | biên: `Lỗi`/`Hết hiệu lực` không chặn | AC-67, NFR-3; ADR-036 QĐ 5 |
| T-18 | thêm | `TArch::TestCatalogArchitecture::test_dedupe_only_in_insert_proposal` (AST `catalog_tools.py`: không tham chiếu `DUPLICATE_BLOCKING_STATUSES`, không `get_list`/`get_all`/`exists` trên `PROPOSAL_DOCTYPE`); `::test_fixed_surface_set_defined_once` (`FIXED_SURFACE_ACTIONS` gán đúng 1 lần, trong `catalog.py`; ở `catalog_tools.py`, `registry.py`, `prompts.py` chỉ import); `TC::TestRuleMode::test_fixed_surface_is_catalog_actions_minus_update_fields` (tập = `CATALOG_ACTIONS − {ACTION_UPDATE_FIELDS}`; U8 giữ xanh khi thêm Project) | — | ADR-031 A1 Ràng buộc; ADR-036 Ràng buộc |
| T-19 | thay `fixes-2:161`, thêm | `TT::TestSiteEnvironment::test_two_refusals_one_comment_per_run` (giữ, `direction_run=False`); thêm `::test_direction_run_no_site_comment` (`direction_run=True`, `production`, hai lời gọi cùng `run_id` → 0 Comment, bộ gom có đúng 1 dòng `SECTION_DECIDE` chứa chữ `TEST_SITE_COMMENT`); `::test_direction_run_refusal_line` (`RULE_DENIED` → 1 dòng `SECTION_DECIDE`, 0 Comment) | — | AC-23 `[changed]`, AC-12, AC-67 |
| T-20 | thay U7b `:352` (test 2) | `TT::TestAutoMode::test_category_outside_row_named_action_proposes` (dòng `Tự làm` "Đổi nhóm hàng" cho B, phiếu D → đề xuất `Chờ duyệt`, căn cứ mặc định, Item không đổi); `::test_category_outside_row_update_fields_refused` (dòng `Tự làm` Đổi trường cho B, phiếu D → `OUT_OF_CATALOG`, 0 đề xuất) | — | AC-29, AC-36 |
| T-21 | thêm | `TT::TestAutoMode::test_auto_in_direction_run_goes_to_done` (`direction_run=True`, đủ 6 vế: Item đổi; 0 Comment mới; bộ gom 1 dòng `SECTION_DONE`; kết quả `comment == ""`); `::test_auto_in_other_run_one_agent_comment` (`direction_run=False`: đúng 1 `Comment` mới, `comment_type = "Comment"`, `owner = AGENT_USER`; 0 dòng `Info`; spy `result_comment.post_result` 0 lần); `::test_auto_refused_in_direction_run_goes_to_decide` (stub `PermissionError` → 1 dòng `SECTION_DECIDE`, 0 Comment); `TArch::TestCatalogArchitecture::test_catalog_tools_never_calls_post_result` (AST: không import `result_comment`, không tên `post_result`) | 2 ca AC-36 `[changed]` + lỗi | AC-36, AC-66; AR3-8 |
| T-22 | thêm | `TRN::TestCatalogAuto::test_auto_in_direction_run_no_extra_comment` (stub model gọi 1 tool `Tự làm` trong lần chạy đầu → số Comment mới = 1 comment hướng (hàm ghi U4b), dòng "Đã làm" có việc đó, 0 đề xuất) | cần U4b | AC-36, AC-66, AC-23 |
| T-23 | thêm | `TRN::TestCatalogDirection::test_empty_catalog_two_actions_two_pending` (L2, rỗng, stub model gọi 2 tool → 2 đề xuất trong lần chạy đầu; comment hướng có cả hai ở "Chờ duyệt"; `ticket_panel._proposals` có cả hai; `@ai` hai lần, stub gọi lại cùng tool → vẫn 2); `::test_hard_ban_and_deny_row_zero_proposals_manual_lines` (1 đích cấm cứng + 1 dòng `Cấm` → 0 đề xuất, "Cần ai quyết" có 2 dòng `REFUSED_LINE`) | cần U4b | AC-67, AC-23 |
| T-24 | thay U7b `:372` (test 1) | `TT::TestCreateProject::test_no_rule_creates_proposal` (không dòng → đề xuất `Chờ duyệt`, căn cứ mặc định, 0 Project trước Duyệt) | — | AC-64 `[changed]` |
| T-25 | thêm | `TT::TestCreateProject::test_deny_row_refused` (`RULE_DENIED`, 0 đề xuất, 0 Project); `::test_auto_row_still_needs_approval` (giữ, `why=approval_only`); `::test_rule_creates_proposal_not_project` (giữ, căn cứ theo dòng) | `Cấm`, `Tự làm` | AC-64 |
| T-26 | thêm vào AC-39 | `TPN::TestPanelProposals::test_mode_basis_shown` (một đề xuất mặc định, một theo dòng → khóa `mode_basis` đúng chữ, chữ thường); `::test_all_pending_shown_beyond_limit` (12 `Chờ duyệt` + 12 `Đã áp dụng` → đủ 12 chờ + 10 khác) | biên: > `PANEL_PROPOSAL_LIMIT` | AC-67, AC-39; AR3-5 |
| T-27 | thêm (E-1) | `TT::TestListAllowed::test_empty_catalog_lists_default_actions` (rỗng → `rows == []`, `default_needs_approval` = `FIXED_SURFACE_ACTIONS`, `note` có); `erp_ai/agent/test_prompts.py::TestCatalogBlock::test_no_list_only_sentence` (`CATALOG_BLOCK` không còn "để biết việc được phép"; có "việc không có dòng vẫn gọi tool được") | — | AC-67 |

Test cũ bị bỏ (thay ở trên, không xóa lặng): U7a `:361` `test_empty_catalog_refuses_every_action`, `test_empty_catalog_no_proposal` (→ T-1..T-5); U7a `:380` `test_rule_removed_before_job_fails` (→ T-12); U7b `:352` `test_category_outside_row_refused` (→ T-20); U7b `:372` `test_no_rule_refused` (→ T-24). Mỗi lần thay ghi lý do "spec-addendum-3 AC-29/AC-64 `[changed]`, ADR-031 A1" ở commit.

## 8. Đối chiếu AC (Done criteria)

- **AC trong phạm vi lời gọi** (spec-addendum-3 mục 3, phần U7a, U7b, U8): AC-29, AC-30, AC-33, AC-36, AC-64, AC-67, AC-68.
- **AC có dòng test ở mục 7:**
  - AC-29: T-1, T-2, T-4, T-6, T-7, T-8, T-9, T-10, T-20
  - AC-30: T-1, T-4
  - AC-33: T-4, T-11, T-12, T-14
  - AC-36: T-20, T-21, T-22
  - AC-64: T-24, T-25
  - AC-67: T-17, T-19, T-23, T-26, T-27
  - AC-68: T-15, T-16

  Khớp 7/7. Mỗi AC có ca lỗi hoặc biên.
- AC phụ có chạm: AC-12 (T-19), AC-23 `[changed]` (T-19, T-22, T-23), AC-39 (T-26), AC-66 (T-21, T-22).
- Test của U7a, U7b, U8 không có trong mục 7 giữ nguyên dòng của các file trước.

## 9. Bảng AR3 → mục sửa

| Mã | Mục sửa đáp ứng | Test |
|---|---|---|
| AR3-1 | S-1, S-3 | T-6, T-7, T-8 |
| AR3-2 | S-2 (Đổi trường ∉ tập) | T-2, T-5, T-9, T-12, T-20 |
| AR3-3 | S-1 bước 2 (nhắc lại; mã ở task chèn đợt 1 `hard_bans.py`) | T-10 |
| AR3-4 | S-2 (`default_needs_approval`, `policy.is_excluded_team`) | T-3, T-5 |
| AR3-5 | S-4 (`mode_basis` nội dung + dấu + comment), S-11 (ngăn) | T-13, T-14, T-26 |
| AR3-6 | phần U7a, U7b, U8: S-5, S-6, S-9 (trả dòng cho bộ gom; chống trùng ở `insert_proposal`); phần U4b, U1 ngoài file này | T-17, T-18, T-19, T-21, T-23 |
| AR3-7 | không có trong U7a/U7b: S-6 dùng hàm trợ giúp chung R-1, không tự viết khóa | T-17 (`test_insert_proposal_uses_locked_helper`) |
| AR3-8 | S-9 | T-21, T-22 |
| AR3-9 | S-7 | T-15, T-16 |

## 10. Chỗ thiết kế lệch ADR-031 A1 hoặc ADR-036

Rỗng. Ba điểm architect có thể muốn xem, không phải lệch:
1. `latency_ms` (trường có sẵn của ERP AI Log, đang dùng cho lời gọi model) được ghi thêm trên dòng `change` của bước áp dụng (S-7). AR3-9 cho phép "dòng bước áp dụng hoặc logger". Nếu architect không muốn dùng chung trường thì chỉ giữ logger; T-15 khi đó đọc dòng logger.
2. E-1 nằm ngoài bảng mục 6 nhưng cần cho AC-67. Nó đổi dạng trả của tool đọc `catalog_list_allowed` và một câu `CATALOG_BLOCK`.
3. R-4: dòng "Chờ duyệt" vào bộ gom tại `insert_proposal`, cho **mọi** loại đề xuất. U4b phải không thêm lần nữa. Đúng ADR-036 QĐ 2, 5; cần U4b ghi nhận khi viết thiết kế đợt 1.

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-W2-1 | `TEMPLATE_MISSING` ở bước 1 (đầu vào), `FORBIDDEN_ROLE` ở bước 2 | A1-1 xếp "vai trò cấm" vào điều cấm cứng; mẫu không có là tham số trỏ vào thứ không có. Cả hai đứng trước mặc định, nên không tạo đề xuất | để cả hai ở bước 2 | dời một dòng trong `check` |
| A-W2-2 | Căn cứ "theo dòng" là ảnh chụp nội dung dòng, không lưu `name`/`idx` của dòng | `name` của hàng bảng con đổi khi Setting lưu lại; người duyệt cần thấy nội dung dòng | lưu `name` dòng | đổi `basis["rule"]` |
| A-W2-3 | Tập trạng thái chặn trùng = `Chờ duyệt`, `Đã duyệt`, `Đang áp dụng` | ADR-036 QĐ 5 "còn chờ hoặc đã được duyệt, chưa kết thúc"; `Đã áp dụng` đã bị `NO_CHANGE` chặn | thêm `Đã áp dụng` | sửa `DUPLICATE_BLOCKING_STATUSES` |
| A-W2-4 | Đề xuất trùng mà đã `Đã duyệt`/`Đang áp dụng` không vào "Chờ duyệt" của bộ gom | mục đó là việc chờ người quyết | ghi vào "Đã làm" | đổi điều kiện ở S-6 |
| A-W2-5 | Việc bị từ chối ở bước 1, 7 không vào bộ gom | lỗi tham số của model, hoặc không có việc; không phải việc người phải làm tay | ghi tất cả | thêm nhánh trong S-5 |
| A-W2-6 | Ngăn hiện mọi đề xuất `Chờ duyệt`, không giới hạn số | AC-67 "hiện cùng lúc"; chống trùng giới hạn số thực tế | giới hạn cao (50) | thêm `limit_page_length` cho (a) |

Câu hỏi nghiệp vụ mới: 0. Phần đang chờ người: AR3-10 (team-leader chuyển). Phần đang chờ analyst: `--amend` AC-29, AC-30, AC-33 (AR3-2, AR3-4) trước plan đợt 2.
