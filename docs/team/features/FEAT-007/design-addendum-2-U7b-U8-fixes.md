Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Sửa design addendum 2 — U7b và U8 AC-64, vòng sửa 1/3 (FEAT-007)

Trả lời `arch-review-design-w2b.md` (request-changes). **File này thắng `design-addendum-2-U7b-U8.md` ở mọi chỗ khác nhau**; addendum không bị viết lại. Chỗ nào file này không nhắc, addendum giữ nguyên.

Căn cứ kiến trúc: ADR-035 QĐ 1–6 (proposed; thay ADR-032 QĐ 3, sửa ADR-010 QĐ 5, ADR-031 QĐ 4, bổ sung ADR-033 QĐ 1), ADR-030 QĐ 4 và Ràng buộc "một vị từ dưới ngưỡng", ADR-031 QĐ 4, 5, 7, ADR-032 QĐ 1, 2, 4, 5, ADR-009, ADR-033 QĐ 1, 5. Không đổi kiến trúc.

**Đánh số finding.** Dòng đầu của review (`arch-review-design-w2b.md:12`) gọi ba major là J-4, J-5, J-6, còn bảng finding (`:72-75`) đánh J-3 (danh sách), J-4 (tool đọc Setting), J-5 (Custom Field), J-6 (minor, import `authority`). File này theo **bảng finding**.

**Tên mới chỉ là thêm** (review "Việc tiếp"): `authority.open_assignment_condition`, `policy.meets_confidence`, `policy.one_click_approval_enabled`, `ToolContext.threshold_pct`, `ToolContext.streak_required`, controller `panel_summary`, lý do logger `"implicit_commit"`, `"context"`. Không đổi tên nào của hợp đồng U7a (mục 5 của w2a, mục 6 của w2b).

---

## 0. Explore summary (đọc trực tiếp ngày 2026-11-14, `develop` @ `431bf55`; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Vị từ "dưới ngưỡng" hiện thiết kế | `policy.is_below_confidence(confidence_pct, threshold, *, has_instructor, act_now)`: `False` nếu `has_instructor and act_now`, ngược lại `confidence_pct is None or confidence_pct < threshold` | `design-addendum-1-U1.md:116`, `:129`, `:283` |
| Runner đọc ngưỡng ở đâu | Bước (e): `threshold = policy.confidence_threshold(settings)`; `ToolContext` dựng ở đó, `dataclasses.replace` sau phân loại | `design-addendum-1-U1.md:259-261` |
| `ToolContext` hôm nay | Dataclass ở `erp_ai/agent/tools/registry.py:13`; U1 thêm trường **có mặc định** để không đổi chỗ khởi tạo cũ | `registry.py:13-16`; `design-addendum-1-U1.md:166` |
| Tên trường Setting ngoài `policy.py` | Cấm (luật `POLICY_FIELDS`): `confidence_threshold` là tên trường, nên không được làm tên trường của `ToolContext` | ADR-030 Ràng buộc 2 (`ADR-030.md:56`) |
| `is_assigned` của U7a | `user` có trong `_assign` của phiếu **và** ToDo mới nhất (`reference_type="HD Ticket"`, `reference_name`, `allocated_to=user`) có `status == "Open"`; thân qua `_open_assignment` | `design-addendum-2-U7a.md:121`, `:128` |
| `IMPLICIT_COMMIT_ACTIONS` | `(ACTION_CREATE_CUSTOM_FIELD,)`, hằng của `catalog.py` (U7a) | `design-addendum-2-U7a-fixes.md:14`, `:51` |
| Module ngăn import gì | `frappe`, `helpdesk.utils.is_agent`, `erp_ai.agent.policy`, `erp_ai.constants`; không import `authority` hay `tools` | `erp_ai/ticket_panel.py:3-14` |
| `policy.py` tự đọc Setting | Có tiền lệ hàm không tham số tự đọc Setting (`get_trigger_keyword`) | `erp_ai/agent/policy.py:62-69` |
| Luật lưu danh mục của U0 | `check_catalog_rules()` ở `erp_ai_setting.py`, lý do "hành động này không nhận DocType" / "không nhận danh sách trường" | `design.md:298-305`; `design-w0-fixes.md:64` |
| `hooks.py` | Chưa có `has_permission`, `permission_query_conditions` (chỉ có comment mẫu) | `erp_ai/hooks.py:121-127` |
| DocType danh mục | `erp_ai_catalog_rule` chưa có trên `develop` (U0 T8 chưa tick) | `ls erp_ai/erp_ai_agent/doctype/` |

---

## Sửa 1 — J-3, phán quyết (1), (2): danh sách và từng bản ghi là cùng một tập "được giao"

**Thay:** addendum `:161`, `:162` (mục 3.3), dòng `:321` ("Không chạm: … `authority.py` …"), dòng test `:370`. `:160`, `:163`, `:165` giữ.

### 1.1 `erp_ai/agent/authority.py` (sửa, đúng 1 hàm thêm, sau U7a)

```python
def open_assignment_condition(user: str, ticket_column: str) -> str
    # dạng SQL của is_assigned(user, <ticket_column>); đặt ngay dưới is_assigned
```

| Mục | Giá trị |
|---|---|
| Ý nghĩa | Biểu thức SQL boolean, đúng trên một dòng **khi và chỉ khi** `is_assigned(user, <giá trị cột>)` đúng. Một định nghĩa "giao mở" cho duyệt (`can_decide`) và đọc (hook), ADR-035 QĐ 3 |
| Dạng | `exists (select 1 from `tab{TICKET_DOCTYPE}` t where t.name = {ticket_column} and t._assign like {esc(pattern)}) and (select td.status from `tabToDo` td where td.reference_type = {esc(TICKET_DOCTYPE)} and td.reference_name = {ticket_column} and td.allocated_to = {esc(user)} order by <đúng biểu thức sắp mà `_open_assignment` của U7a dùng> limit 1) = {esc("Open")}` |
| `pattern` | `'%"' + u + '"%'` với `u` = `user` đã thoát `\`, `%`, `_` cho LIKE; mọi giá trị qua `frappe.db.escape` (STD-SEC-3). `_assign` là danh sách JSON nên tên nằm giữa hai dấu `"` |
| `ticket_column` | Hằng do người gọi đặt, không bao giờ từ dữ liệu ngoài. Không khớp `` ^`tab[A-Za-z ]+`\.`[a-z_]+`$ `` → `ValueError` |
| `user` rỗng hoặc ∈ `NEVER_AUTHORITY` | Trả `"1=0"` (cùng kết quả `can_decide` cho các người này) |
| Đổi sau này | Nếu câu A-U7a-3 được trả lời "không tự gán rồi tự duyệt", vế `assigned_by ≠ user` thêm vào **cả** `is_assigned` và hàm này trong cùng commit. Test 1.4 (ca `assigned_by = user`) bắt việc quên một bên |

Không sửa thân `is_assigned`, `_open_assignment`, `can_decide` của U7a. Nếu U7a viết biểu thức sắp ToDo thành chữ, dev chép đúng chữ đó. Ca "hai ToDo, cũ `Open`, mới `Cancelled`" và ca ngược lại ở test 1.4 ghim thứ tự.

### 1.2 Controller `erp_ai_change_proposal.py`: hai hook (thay `:161-162`)

- `has_permission(doc, ptype=None, user=None, debug=False) -> bool | None`
  - người không phải "chỉ-agent-Helpdesk" (`_helpdesk_agent_reader_only`, `:160`) → `None`;
  - `ptype != "read"` → `False`;
  - đúng khi đồng thời: `doc.change_kind == CHANGE_KIND_RECORD`; `doc.ticket` khác rỗng; `is_agent(user)`; `frappe.has_permission(TICKET_DOCTYPE, "read", doc=doc.ticket, user=user)`; `authority.is_assigned(user, doc.ticket)`;
  - còn lại `False`.
- `get_permission_query_conditions(user=None) -> str`
  - người không phải "chỉ-agent-Helpdesk" → `""`;
  - không `is_agent(user)` → `"1=0"`;
  - còn lại: `` `tabERP AI Change Proposal`.`change_kind` = {esc(CHANGE_KIND_RECORD)} and `` + `authority.open_assignment_condition(user, PROPOSAL_TICKET_COLUMN)`, với `PROPOSAL_TICKET_COLUMN` là hằng module của controller dựng từ `PROPOSAL_DOCTYPE` (`` f"`tab{PROPOSAL_DOCTYPE}`.`ticket`" ``).
- Vế "đọc được phiếu" chỉ ở hook từng bản ghi (phán quyết (2)): với Helpdesk 15.1, phiếu được giao thì đọc được. Test 1.4 có ca "được giao + `restrict_tickets_by_agent_group` bật, khác nhóm". Ca đó đỏ → điều kiện danh sách thêm vế đọc phiếu theo điều kiện danh sách của chính HD Ticket (`frappe.get_list(TICKET_DOCTYPE, user=user)` dạng truy vấn con), không sửa hook.
- Bất biến (ADR-035 QĐ 3): tập danh sách ⊆ tập hook; test đòi **bằng nhau**.
- Hook không chứa `ignore_permissions`, `ROLE_INSTRUCTOR`, `tabToDo`, `"ToDo"` (ADR-035 Ràng buộc 3).
- Bỏ câu "Lọc danh sách thô; chốt chính xác là `has_permission` theo từng bản ghi". Mọi đường danh sách của Frappe (list view, report view, `/api/resource`, `frappe.client.get_list`, `get_count`, tìm Link) chỉ áp `permission_query_conditions`.

### 1.3 Dòng DocPerm và hai khóa `hooks.py` trong cùng một commit (phán quyết (1))

- `erp_ai_change_proposal.json`: đúng một dòng DocPerm role `Agent` (`HELPDESK_AGENT_ROLE`), `read: 1`; `write`, `create`, `delete`, `submit`, `cancel`, `amend`, `report`, `export`, `print`, `email`, `share`, `select`, `import` = 0 (ADR-035 Ràng buộc 1). Hàng `:71` của addendum giữ, cộng danh sách cờ này.
- `erp_ai/hooks.py`: hai khóa ở Sửa 5.
- Dòng DocPerm, hai khóa `hooks.py`, hai hàm hook, `open_assignment_condition` và các test 1.4 vào **cùng một commit**. Không commit nào có dòng `Agent` mà thiếu hook.
- Rút lui: mục 6 của addendum `:294` đã đúng thứ tự "gỡ DocPerm → trả mã hook". As-Built chép lại thứ tự này và câu đối chiếu `COUNT(*) = 0`.

### 1.4 Test (thay `TP::TestProposalPermissionHook::test_agent_reader_matrix` ở `:370`)

| Test | Kiểm |
|---|---|
| `TP::TestProposalPermissionHook::test_list_equals_record_matrix` | Ma trận ADR-035 Ràng buộc 4: người {chỉ-`Agent` được giao, chỉ-`Agent` không giao, chỉ-`Agent` được giao phiếu khác, Instructor, System Manager, `AGENT_USER`} × đề xuất {bản ghi của phiếu được giao, bản ghi của phiếu khác, code của phiếu được giao}. Với mỗi người: `set(frappe.get_list(PROPOSAL_DOCTYPE, pluck="name"))` (dưới phiên người đó) = tập tên có `frappe.has_permission(PROPOSAL_DOCTYPE, "read", doc=…)` đúng. Chỉ-`Agent` được giao thấy đúng `{bản ghi của phiếu được giao}`. Với chỉ-`Agent`: `write`, `create`, `delete` luôn `False` |
| `TP::TestProposalPermissionHook::test_list_paths_leak_nothing` | **Lời gọi danh sách không trả đề xuất người đó không mở được.** Dưới phiên chỉ-`Agent` không giao, rồi chỉ-`Agent` được giao phiếu khác, gọi: `frappe.get_list(…, fields=["name","action_args","record_before","reason"])`, `frappe.client.get_list`, `frappe.desk.reportview.get` (report view), `frappe.client.get_count`, `frappe.desk.search.search_link`. Mỗi tên trả về phải có `has_permission(…, "read")` đúng; với hai người này mọi kết quả rỗng và `get_count` = 0. Người được giao: kết quả chỉ chứa tên của đề xuất bản ghi phiếu được giao |
| `TP::TestProposalPermissionHook::test_assignment_edges_same_in_both_paths` | ToDo `Closed` → ẩn ở cả hai đường; hai ToDo (cũ `Open`, mới `Cancelled`) → ẩn; (cũ `Cancelled`, mới `Open`) → hiện; `_assign` có tên mà không ToDo mở → ẩn. Mỗi ca: danh sách = hook |
| `TP::TestProposalPermissionHook::test_restricted_agent_group_assigned` | HD Settings `restrict_tickets_by_agent_group = 1`, agent khác nhóm, được giao → danh sách = hook (phán quyết (2)) |
| `TP::TestProposalPermissionHook::test_instructor_and_agent_account_unchanged` | giữ (`:370`) |
| `TAU::TestOpenAssignmentCondition::test_sql_form_matches_is_assigned` (`erp_ai/agent/test_authority.py`) | Ma trận phiếu × người (gồm ToDo `assigned_by = user`, ToDo do bot gán, `_assign` lệch ToDo): `{t : frappe.db.sql("select name from `tabHD Ticket` where name in %(names)s and " + open_assignment_condition(u, "`tabHD Ticket`.`name`"))}` = `{t : is_assigned(u, t)}` |
| `TAU::TestOpenAssignmentCondition::test_escaping` | `user` có `'`, `%`, `_` → không lỗi SQL, không khớp thừa (người `a_b@x` không thấy phiếu giao cho `axb@x`); `ticket_column` lạ (`"name; drop"`) → `ValueError`; `user` ∈ `NEVER_AUTHORITY` → `"1=0"` |
| `TArch::TestProposalPermissionArchitecture::test_agent_docperm_pairs_with_hooks` | Đọc JSON và `hooks.py`: có dòng `Agent` ⇔ có **cả hai** khóa cho `PROPOSAL_DOCTYPE`, trỏ vào module controller; dòng `Agent` chỉ `read` (thay `TArch::TestCatalogArchitecture::test_agent_docperm_read_only` của `:379`) |
| `TArch::TestProposalPermissionArchitecture::test_hooks_have_no_todo_or_bypass` | Mã nguồn hai hàm hook không chứa `ignore_permissions`, `ROLE_INSTRUCTOR`, `tabToDo`, `"ToDo"` |

---

## Sửa 2 — J-4: vị từ "Tự làm" không đọc ERP AI Setting và không tự so ngưỡng

**Thay:** addendum `:188-197` (chữ ký và 5 vế), `:199` (lời gọi), `:239` (runner), phần `policy.py` của `:228-231` (thêm hàm, xem Sửa 7 cho `auto_approve_streak`).

### 2.1 `policy.py` (sửa): một phép so ngưỡng

```python
def meets_confidence(confidence_pct: int | None, threshold: int) -> bool
    # phép so ngưỡng duy nhất: confidence_pct is not None and confidence_pct >= threshold
```

`is_below_confidence` (U1) đổi thân thành `False if has_instructor and act_now else not meets_confidence(confidence_pct, threshold)`. Hành vi giữ nguyên chữ U1 (`None` → dưới; 69 < 70 → dưới; 70 → không dưới). Chữ ký không đổi. Như vậy "dưới ngưỡng" (ADR-030 QĐ 4) và "đạt ngưỡng" của "Tự làm" (ADR-031 QĐ 4) dùng chung một phép so, ở `policy.py` (ADR-030 Ràng buộc 4).

### 2.2 `registry.py` (sửa vùng `ToolContext`)

```python
threshold_pct: int | None = None     # = policy.confidence_threshold(settings), runner bước (e)
streak_required: int | None = None   # = policy.auto_approve_streak(settings), runner bước (e)
```

- Có mặc định nên mọi chỗ khởi tạo cũ không đổi (như U1 `:166`).
- Không đặt tên `confidence_threshold` / `auto_approve_streak`: đó là tên trường Setting, chỉ được ở `policy.py` (luật `POLICY_FIELDS`).
- `grant_inputs()` không đọc hai trường này (hàm cấp không đổi).

### 2.3 `runner.py` bước (e) (sửa; thay `:239`)

- Cạnh `threshold = policy.confidence_threshold(settings)` (U1 `:259`): `streak_required = policy.auto_approve_streak(settings)`; `overrides = policy.prompt_overrides(settings)`.
- `ToolContext(..., threshold_pct=threshold, streak_required=streak_required)`.
- `dataclasses.replace` sau phân loại (U1 `:261`) giữ hai trường.
- `_classify` / `_reason` truyền ghi đè như `:239`.
- Runner không đổi gì khác.

### 2.4 `catalog_tools.py`: vị từ duy nhất (thay `:188-197`)

```python
def auto_mode_allowed(ctx: ToolContext, result: CheckResult, action: str,
                      confidence_pct: int) -> tuple[bool, str]   # (đúng/sai, lý do cho logger)
```

Bỏ tham số `args`, `settings`. Xét theo thứ tự; trả lý do của vế sai đầu tiên:

| # | Vế (U7b) | Sai → lý do |
|---|---|---|
| 1 | `result.mode == MODE_AUTO` | `"mode"` |
| 2 | `action ∉ catalog.IMPLICIT_COMMIT_ACTIONS` (Sửa 3) | `"implicit_commit"` |
| 3 | `ctx.main_path_level == "L3"` | `"level"` |
| 4 | `ctx.threshold_pct is not None and ctx.streak_required is not None` (fail-closed khi context dựng thiếu) | `"context"` |
| 5 | `policy.meets_confidence(confidence_pct, ctx.threshold_pct)` | `"confidence"` |
| 6 | `catalog_approvals.current_streak(kind_of(action, result.doctype if action == ACTION_UPDATE_FIELDS else None)) >= ctx.streak_required` | `"streak"` |

- Vế `"approval_only"` (`action ∉ APPROVAL_ONLY_ACTIONS`) là của U8, chèn ngay sau vế 1 (Sửa 4).
- Vế 6 chạy cuối vì là vế duy nhất truy vấn DB.
- Phần grant đã mang sẵn "nhóm `catalog` chỉ có khi mức đường chính ≥ L2 ∧ ¬dưới ngưỡng" (ADR-030 QĐ 3), nên tool không xét lại độ tin cậy phân loại. `confidence_pct` ở vế 5 là độ tin cậy của chính lời gọi tool (U7a 3.4 bước 1), so bằng hàm của `policy`.
- `catalog_tools.py` không gọi `confidence_threshold`, `auto_approve_streak`, `permission_switches`, `get_single`, `get_cached_doc`, `get_single_value`, không import `SETTING_DOCTYPE`, không có phép so (`Compare`) nào nhận `threshold_pct` làm toán hạng.

`_propose` bước 4 (thay `:199`, phần trước "Sai →"): `allowed, why = auto_mode_allowed(ctx, result, action, confidence_pct)`; logger `erp_ai catalog auto action=%s allowed=%s why=%s streak=%s` (`streak=-` khi vế 6 chưa chạy).

### 2.5 Test

| Test | Kiểm |
|---|---|
| `TPol::TestMeetsConfidence::test_boundary` | 69/70 → `False`/`True`; `None` → `False`; ngưỡng 0, pct 0 → `True`; ngưỡng 100, pct 100 → `True` |
| `TPol::TestIsBelowConfidence::test_delegates_to_meets_confidence` | patch `meets_confidence` trả `True` → `is_below_confidence(…, has_instructor=False, act_now=False)` là `False`; các test U1 của `is_below_confidence` giữ xanh, không sửa |
| `TRN::TestCatalogAuto::test_context_carries_threshold_and_streak` | Setting ngưỡng 80, chuỗi 5 → `ToolContext.threshold_pct == 80`, `streak_required == 5`, cả trước và sau `dataclasses.replace` của lần chạy tạo phiếu |
| `TT::TestAutoMode::test_tool_does_not_read_setting` | Context đủ điều kiện (L3, `threshold_pct` 70, `streak_required` 20, chuỗi 20). Patch `frappe.get_single`, `frappe.get_cached_doc`, `frappe.db.get_single_value` ném khi doctype = ERP AI Setting trong lúc gọi tool → vẫn tự làm, Item đổi. Rồi đổi Setting ngưỡng thành 90 mà giữ context → kết quả vẫn theo `ctx` |
| `TT::TestAutoMode::test_missing_context_values_never_auto` | `threshold_pct=None` hoặc `streak_required=None` → đề xuất `Chờ duyệt`, logger `why=context` |
| `TT::TestAutoMode::test_confidence_69_vs_70` (`:351`, đổi cách dựng) | ngưỡng đặt qua `ctx.threshold_pct` (70: 69 → đề xuất, 70 → tự làm; 80: 70 → đề xuất), không qua Setting |
| `TT::TestAutoMode::test_streak_setting_5` (`:353`, đổi cách dựng) | `ctx.streak_required = 5`, chuỗi 5 → tự làm; 4 → đề xuất |
| `TArch::TestCatalogArchitecture::test_catalog_tools_reads_no_setting` | AST `catalog_tools.py`: không `Call` tới `confidence_threshold`, `auto_approve_streak`, `permission_switches`, `get_single`, `get_cached_doc`, `get_single_value`; không import `SETTING_DOCTYPE` |
| `TArch::TestCatalogArchitecture::test_single_threshold_compare` | AST mọi module `erp_ai/agent/**/*.py` (trừ test): `Compare` có toán hạng tên hoặc thuộc tính chứa `threshold` chỉ nằm trong `policy.meets_confidence` |

---

## Sửa 3 — J-5, phán quyết (8): hành động tự commit không bao giờ "Tự làm"

**Thay:** addendum `:199-201` (nhánh đúng/sai sau `auto_mode_allowed`), `:268` (luồng 4.2), câu "dữ liệu không đổi — bộ thực thi đã rollback savepoint". Vế mới đã ở bảng 2.4 (vế 2).

- **Vế 2:** `action ∉ catalog.IMPLICIT_COMMIT_ACTIONS` (import tên của U7a, không chép tập; hôm nay `(ACTION_CREATE_CUSTOM_FIELD,)`). Sai → lý do logger `"implicit_commit"` (ADR-035 "Phải làm thêm": tên lý do do designer đặt).
- Vế 2 đứng trước vế 3–6, nên dòng `Tự làm` cho "Tạo Custom Field" luôn đi bước 5 của U7a: tạo đề xuất `Chờ duyệt`, comment đề xuất như dòng `Cần duyệt`. Áp dụng sau duyệt đi đúng `apply_job._run_record` của U7a, theo D-1 (trạng thái chạy commit trước khi ghi đích) và sửa J-1 của U7a. U7b không đổi đường đó.
- Ở `production`, "Tạo Custom Field" đã bị `catalog.check` từ chối (`TEST_SITE_ONLY`) trước bước 4, nên vế này chỉ có tác dụng trên site `test`.

**Chữ đúng thay `:199-201`:**

> Đúng → `ex = catalog.execute(request, watched_before=None)`. Mọi hành động tới được nhánh này ∉ `IMPLICIT_COMMIT_ACTIONS` (vế 2), nên lần ghi đích nằm trong savepoint của bộ thực thi và **không có commit nào giữa lượt chạy**:
> - `ex.outcome == "applied"` → đăng **1** comment `AUTO_DONE_COMMENT` (mọi giá trị qua `escape_html`; `changes` = `key: trước → sau`) qua `catalog_tools._post_comment(ctx, html)` của U7a (phán quyết (6)); trả `{"ok": True, "auto": True, "doctype", "name", "value_before", "value_after", "comment"}`. Runner ghi 1 mục hành động vào dòng `reason` của lượt qua `_entry_values` hàng 1 (ADR-031 QĐ 8, ADR-033 QĐ 5). Lượt lỗi sau đó thì cả lần ghi đích, comment và mục nhật ký cùng rollback theo giao dịch của runner.
> - khác → `{"ok": False, "reason": ex.reason}`; không tạo đề xuất, không comment. Đích không đổi vì bộ thực thi đã `rollback(save_point)` (U7a 3.3, nhánh ∉ `IMPLICIT_COMMIT_ACTIONS`).
>
> Sai → bước 5 của U7a (tạo đề xuất, "rơi về Cần duyệt").

**Luồng 4.2, thay `:268`:** Lượt chạy (mức đường chính ≥ L2, trên ngưỡng) → `catalog_*` → `_propose` → `catalog.check` đạt với `mode = Tự làm` → `auto_mode_allowed(ctx, …)` (6 vế; U8 thêm vế 7, đọc `ctx`, không đọc Setting) → đúng: `catalog.execute(watched_before=None)` dưới tài khoản agent, trong savepoint → 1 comment báo lại + 1 mục hành động trong dòng `reason`; sai (kể cả "Tạo Custom Field") → đề xuất `Chờ duyệt` (U7a). Từ chối, duyệt có sửa, hoàn tác của loại đó đẩy mốc đặt lại → chuỗi về 0 ở lần tính kế (không lưu bộ đếm).

**Test:**

| Test | Kiểm |
|---|---|
| `TT::TestAutoMode::test_custom_field_auto_row_needs_approval` | **ADR-035 Ràng buộc 7 + "giao dịch runner chưa commit".** Site `test`; dòng `Tự làm` cho "Tạo Custom Field"; `ctx.main_path_level = L3`, `threshold_pct` 70, `streak_required` 20; 50 đề xuất "Tạo Custom Field" duyệt không sửa; gọi tool với `confidence_pct` 100. Trước lời gọi: `frappe.db.savepoint("t_auto_cf")`; bọc `frappe.db.commit` và `frappe.db.sql_ddl` bằng `patch.object(..., wraps=...)`. Kết quả: `ok=true`, có `proposal`, trạng thái `Chờ duyệt`; 0 Custom Field có `fieldname` đó; logger 1 dòng `why=implicit_commit`; spy `commit` và `sql_ddl` không được gọi. Sau đó `frappe.db.rollback(save_point="t_auto_cf")` chạy không lỗi và đề xuất vừa tạo biến mất (savepoint còn ⇒ không có commit trong lượt) |
| `TT::TestAutoMode::test_implicit_commit_actions_always_refused` | Với mỗi `a ∈ IMPLICIT_COMMIT_ACTIONS`, context và chuỗi đủ mọi vế khác → `auto_mode_allowed` = `(False, "implicit_commit")` |
| `TT::TestAutoMode::test_execute_refused_no_fallback_proposal` (`:354`, giữ) | thêm kiểm: spy `frappe.db.commit` không được gọi |
| Áp dụng Custom Field sau duyệt | test của U7a giữ (`TA` D-1, J-1 của U7a); U7b không thêm |

**Hệ quả nghiệp vụ (không chặn):** AC-30 "mỗi hành động tuân chế độ của dòng" có ngoại lệ "Tạo Custom Field luôn cần duyệt" trên site `test`. Câu hỏi cho analyst/người do team-leader chuyển (phán quyết (8)); nếu người không chấp nhận thì cần ADR mới cho giao thức commit của runner, ngoài phạm vi U7b.

---

## Sửa 4 — phán quyết (4): U8 sở hữu AC-64 trong một commit, sau U7a và U7b

**Thay:** hàng N-2 (`:54`); câu "`ACTION_CREATE_PROJECT` là của U0" ở `:316`; dòng `:185` (`APPROVAL_ONLY_ACTIONS` không còn là của U7b); vế 2 cũ "`approval_only`" của `:194`; câu "options từ `CATALOG_ACTIONS` qua JSON tĩnh" ở `:260` (thêm test ghim).

**Một commit của U8 (AC-64), merge sau U7b**, gồm đúng các sửa sau:

| File | Sửa |
|---|---|
| `erp_ai/constants.py` | `ACTION_CREATE_PROJECT = "Tạo Project cho phiếu"`; nối vào **cuối** `CATALOG_ACTIONS` (giữ thứ tự option cũ); `ACTION_TARGET_DOCTYPES[ACTION_CREATE_PROJECT] = "Project"` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.json` | option Select `action` thêm dòng cuối, đúng `"\n".join(CATALOG_ACTIONS)` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | `check_catalog_rules`: thêm `ACTION_CREATE_PROJECT` vào đúng **một** chỗ U0 đặt nhóm "đích cố định" (`target_doctype`, `fields` phải trống). Nếu U0 suy nhóm đó từ tập ngược (hành động nhận DocType) thì không sửa file này; dev dán `grep -n "CATALOG_ACTIONS\|ACTION_" erp_ai_setting.py` vào báo cáo task |
| `erp_ai/agent/tools/catalog.py` | `ACTION_HANDLERS[ACTION_CREATE_PROJECT]` theo bảng `:207-218` |
| `erp_ai/agent/tools/catalog_tools.py` | tool `catalog_create_project` (`:203`); `APPROVAL_ONLY_ACTIONS = (ACTION_CREATE_PROJECT,)`; vế `action ∉ APPROVAL_ONLY_ACTIONS` → `"approval_only"`, chèn ngay sau vế 1 của `auto_mode_allowed` (vẫn một hàm vị từ) |
| `erp_ai/agent/tools/write_ticket.py` | hằng `TASK_TICKET_FIELD = "ai_ticket"`; dòng `:143` dùng lại |
| `erp_ai/erp_ai_agent/report/erp_ai_approval_stats/erp_ai_approval_stats.js` | option Select `catalog_action` thêm "Tạo Project cho phiếu" |
| `erp_ai/agent/tools/test_registry.py` | chỉ khi test AC-9 FEAT-006 trúng từ cấm (`expected_end_date`, `project_name`): nối `ROUTE_WORD_EXCEPTIONS` (minor (e)) |
| Test của U8 | `TC::TestCreateProject`, `TT::TestCreateProject`, `TA::TestApplyRecord` (Project), `TP::TestRecordDecision::test_project_proposal_eligibility`, cộng 3 test dưới |

- **U0 không thêm hằng sớm.** U7a, U7b không nhắc `ACTION_CREATE_PROJECT`.
- Lượt merge cuối đợt 2 vào `develop` chạy `cmd.migrate` (option Select đổi).
- Lý do một commit: test ghim option của U0, `test_action_target_doctypes_cover_catalog_actions` của U7a và test ghim `.js` dưới đây đỏ nếu tách.

| Test thêm | Kiểm |
|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestCatalogRules::test_create_project_is_fixed_target` | dòng "Tạo Project cho phiếu" có `target_doctype` → "hành động này không nhận DocType"; có `fields` → "hành động này không nhận danh sách trường"; trống cả hai → lưu được |
| `TAS::TestApprovalStats::test_js_filter_options_match_catalog_actions` | đọc `erp_ai_approval_stats.js`, lấy chuỗi `options` của bộ lọc `catalog_action` → bằng `"\n" + "\n".join(CATALOG_ACTIONS)` (dòng trống đầu = "mọi hành động"). U7b viết test này; U8 giữ nó xanh |
| `TT::TestCreateProject::test_auto_row_still_needs_approval` (`:372`, giữ) | `why=approval_only` |

---

## Sửa 5 — phán quyết (5): dòng `PANEL_METHODS` và hai khóa `hooks.py` thuộc U7b

**Thay:** hàng N-3 (`:55`), N-4 (`:56`), dòng `:163`, hai hàng `:316-317` của bảng touchpoint.

- `erp_ai/constants.py` (U7b): đúng 1 dòng thêm `"erp_ai.ticket_panel.decide_proposal"` vào `PANEL_METHODS`. Cùng commit với `decide_proposal` và lời gọi `state.call("erp_ai.ticket_panel.decide_proposal", …)` trong `agent_status_indicator.js` (test ADR-009 so hai tập).
- `erp_ai/hooks.py` (U7b): đúng 2 khóa, nối ở **cuối** file, không đụng khóa của U4a, U5a, U6a, U6b:
  ```python
  has_permission = {PROPOSAL_DOCTYPE: "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.has_permission"}
  permission_query_conditions = {PROPOSAL_DOCTYPE: "erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal.get_permission_query_conditions"}
  ```
  Khóa là chuỗi `"ERP AI Change Proposal"` nếu `hooks.py` không import `erp_ai.constants` (theo kiểu của file hiện có). Test `test_agent_docperm_pairs_with_hooks` so với `PROPOSAL_DOCTYPE`.
- Cùng commit với dòng DocPerm `Agent` (Sửa 1.3).
- Hai file này nằm ngoài ô U7 của `arch-impact.md:181`; architect đã chấp nhận (phán quyết (5)).

---

## Sửa 6 — phán quyết (3), J-6: bit `proposal_one_step` qua `policy`, dữ liệu đề xuất qua controller

**Thay:** `:120`, `:122`, `:123`, `:125`, `:134` (mục 3.1); hàng A-U7b-5 (`:419`) đổi trạng thái thành "architect chấp nhận, ADR-035 QĐ 4".

### 6.1 Controller (sửa, thêm 1 hàm cạnh `record_summary` của U7a)

```python
def panel_summary(doc, user: str) -> dict
    # {**record_summary(doc), "can_decide": bool}; "edit_fields" chỉ có khi can_decide
```

- `can_decide = doc.change_status == CHANGE_STATUS_PENDING and authority.can_decide(user, doc.change_kind, doc.ticket)`, đúng vị từ `_decider` dùng.
- `record_summary(doc)` của U7a không đổi chữ ký (phán quyết (6)).

### 6.2 `ticket_panel.py`

- Mỗi phần tử `proposals`: `s = proposal_controller.panel_summary(doc, frappe.session.user)`; `changes = s["changes"]`, `can_decide = s["can_decide"]`, `edit_fields = s.get("edit_fields", [])`. Các khóa còn lại như bảng `:116-123`.
- `proposal_one_step = policy.one_click_approval_enabled()`: hàm không tham số mới của `policy.py`, tự đọc Setting như `get_trigger_keyword` (`policy.py:62-69`), trả `permission_switches(settings).one_click_approval`. `ticket_panel.py` không đọc ERP AI Setting và không chứa tên trường nào của nó.
- Tập khóa của `get_panel_data` cố định: `{"ticket", "ai_fields", "messages", "proposals", "proposal_one_step"}`. Đúng một khóa suy từ cấu hình (ADR-035 QĐ 4).
- `decide_proposal` không gọi `permission_switches` hay `one_click_approval_enabled` ((5) không phải ranh giới).
- Import mới của `ticket_panel.py` (thay `:134`): chỉ module controller đề xuất (`erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.erp_ai_change_proposal`). **Không** import `erp_ai.agent.authority`, `erp_ai.agent.tools.*`.
- `LAYER_RULES` của `erp_ai.ticket_panel` (`test_architecture.py:105-109`): giữ 3 cấm cũ, thêm cấm `erp_ai.agent.authority`, `erp_ai.agent.tools`. Danh sách được import thêm đúng module controller.

### 6.3 Test

| Test | Kiểm |
|---|---|
| `TArch::TestPanelArchitecture::test_panel_imports_controller_not_authority` | AST `ticket_panel.py`: không import `erp_ai.agent.authority` hay `erp_ai.agent.tools`; có import module controller |
| `TArch::TestPanelArchitecture::test_panel_read_keys_fixed` | `get_panel_data` (người được giao, có 1 đề xuất) trả đúng 5 khóa trên |
| `TArch::TestPanelArchitecture::test_decide_does_not_read_switches` | AST thân `decide_proposal`: không `Call` tới `permission_switches`, `one_click_approval_enabled` |
| `TArch::TestPanelArchitecture::test_no_agent_session_in_whitelisted_modules` | ADR-035 Ràng buộc 8: AST `ticket_panel.py`, controller đề xuất, `change_decision.py`, controller ERP AI Setting không gọi `agent_session` hay hàm chuyển phiên của U1 |
| `TP::TestPanelSummary::test_can_decide_matches_decider` | người được giao / không giao / Instructor × `Chờ duyệt` / `Đã duyệt`: `panel_summary(...)["can_decide"]` = (trạng thái chờ ∧ `can_decide`); `edit_fields` vắng khi `False` |
| `TPN::TestDecideProposal::test_switch5_off_panel_still_decides`, `::test_switch5_on_flag` (`:369`) | giữ |

---

## Sửa 7 — phán quyết (9): chữ của `auto_approve_streak` (mục 3.7)

**Thay:** `:229` và `:231`.

Chữ ký thay `:229`:

```python
def auto_approve_streak(settings) -> int   # 1..100; giá trị lưu ngoài 1..100 hoặc không phải số nguyên → 100 + 1 dòng logger cảnh báo
```

Chữ thay `:231`:

> `auto_approve_streak(settings)`: đọc `int` của trường `auto_approve_streak`. Thiếu hoặc `None` (site chưa migrate) → mặc định của U0 (20), như `confidence_threshold` của U1 `:128`. Giá trị lưu ngoài `1..100` (chỉ có thể qua ghi DB thô; U0 đã chặn lúc lưu) → trả `100`, fail-closed: khó tự làm nhất, cùng tiền lệ "đầu mục chưa biết → L1" của ADR-030 QĐ 2. Kèm đúng 1 dòng `frappe.logger(LOGGER_NAME).warning("erp_ai policy auto_approve_streak out of range value=%s", value)`. Không ném, không nuốt ngoại lệ nào. Hàm được **runner** gọi ở bước (e) khi dựng `ToolContext` (Sửa 2.3), không được tool gọi. Ba tên trường `prompt_override_*` và `auto_approve_streak` chỉ xuất hiện ở `policy.py` (mở rộng luật `POLICY_FIELDS`).

Test giữ: `TPol::TestAutoApproveStreak::test_reads_setting` (5 → 5); `::test_out_of_range_is_fail_closed` (0, 101, -1 ghi DB thô → 100 và đúng 1 dòng logger `warning` mỗi lần đọc); thêm `::test_missing_is_default` (`None` → 20, 0 dòng logger).

---

## Sửa 8 — J-2 phần U7b, phán quyết (7): Từ chối xếp 1 job

**Thay:** `:366` và câu "Từ chối: → `reject`, không job" ở `:266`.

- Luồng 4.1, chữ thay: "Từ chối: → controller `reject` → `Đã từ chối`, xếp **1** job (U7a, phán quyết (7)); job đăng 1 comment kết quả dưới `AGENT_USER` qua `result_comment.post_result`; đích không đổi."
- `decide_proposal` vẫn không gọi `enqueue_change_job` (ADR-032 Ràng buộc 2): job do `reject` của controller xếp.
- Dòng test `:366` thay bằng `TPN::TestDecideProposal::test_approve_reject_edit_by_assignee`: approve → `Đã duyệt`, 1 job; reject → `Đã từ chối`, **1 job, đích không đổi**; approve_with_edit hợp lệ → `approved_with_edit=1`, 1 job.
- Thêm `TPN::TestDecideProposal::test_reject_via_panel_posts_one_result_comment`: chạy job của ca reject → đúng 1 comment `owner = AGENT_USER`; chạy lại → 0 comment thêm (ADR-035 Ràng buộc 9, đường ngăn; hai đường form và liên kết có chữ ký là test của U7a).
- Kiểm tay 8.1 bước 9 thêm: "chờ vài giây: comment kết quả 'Đã từ chối' xuất hiện trên dòng thời gian".

---

## Sửa 9 — minor (a)–(e) của review

| Minor | Thay | Chữ đúng |
|---|---|---|
| (a) | `:40`, `:45`, `:59` (N-7), `:393` (bước 7 "cần N-7"), `:407` | `NOT_ELIGIBLE` → `DECIDE_REFUSAL` (chữ cũ FEAT-004, U7a-fixes Sửa 2). Comment kết quả là của U7a (nhánh B: `result_comment.post_result`; nhánh A: tên của T56). Bỏ N-7; bước 7 của 8.1 không còn phụ thuộc FEAT-004. Bảng 1.2 thêm `catalog.IMPLICIT_COMMIT_ACTIONS`, `catalog_tools._post_comment(ctx, html) -> str`, `erp_ai_change_proposal.record_summary(doc) -> dict`, `result_comment.post_result`. N-6 (`:58`) bỏ: U7a viết sẵn `_post_comment` (phán quyết (6)), U7b chỉ gọi |
| (b) | N-1 (`:53`), `:362` (`test_classify_override_without_pct_key_blocked`), `:407` | Chủ N-1 là **U1 đợt 1**, cùng commit với khóa `do_tin_cay_pct` của `CLASSIFY_PROMPT`, không phải U0. Nếu U1 đã merge mà thiếu, plan đợt 2 chèn một task 1 dòng trước U7b (việc của tech-lead). Test `::test_classify_override_without_pct_key_blocked` giữ ở U7b |
| (c) | `:167-169` | `catalog_approvals.py` đặt ở `erp_ai/agent/tools/` nhưng **không** là module tool: không vào `TOOL_MODULES`. Test `TRG::TestToolModules::test_catalog_approvals_not_registered` (tên module ∉ `TOOL_MODULES`; không spec nào có tên bắt đầu `catalog_approvals`) |
| (d) | `:260` | Xem Sửa 4: option tĩnh của `.js` có test ghim `test_js_filter_options_match_catalog_actions`; U8 nối "Tạo Project cho phiếu" trong commit AC-64 |
| (e) | `:203` | Xem Sửa 4 hàng `test_registry.py` |

---

## 7'. Touchpoints (thay toàn bộ mục 7 `:299-335`)

| Đường dẫn | Mới/sửa | Đơn vị | Trong ô của `arch-impact.md:181-182`? | Sửa / mục |
|---|---|---|---|---|
| `erp_ai/ticket_panel.py` | sửa | U7b | có | 3.1, Sửa 6 |
| `erp_ai/public/js/agent_status_indicator.js` | sửa | U7b | có | 3.2, Sửa 5 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | sửa | U7b | có | Sửa 1.2, 6.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json` | sửa | U7b | có | 2.1, Sửa 1.3 |
| `erp_ai/agent/authority.py` | sửa (1 hàm `open_assignment_condition`) | U7b | **không**; architect giao (J-3, review mục 5) | Sửa 1.1 |
| `erp_ai/hooks.py` | sửa (2 khóa, nối cuối) | U7b | **không**; phán quyết (5) | Sửa 5 |
| `erp_ai/constants.py` | sửa | U7b: 1 dòng `PANEL_METHODS`. U8: `ACTION_CREATE_PROJECT`, phần tử cuối `CATALOG_ACTIONS`, khóa `ACTION_TARGET_DOCTYPES` | **không**; phán quyết (4), (5) | Sửa 4, 5 |
| `erp_ai/agent/tools/catalog_approvals.py` | mới | U7b | có | 3.4 |
| `erp_ai/agent/tools/catalog_tools.py` | sửa | U7b: `auto_mode_allowed`, nhánh bước 4, `AUTO_DONE_COMMENT`. U8: tool Project, `APPROVAL_ONLY_ACTIONS`, vế `approval_only` | có | Sửa 2.4, 3, 4 |
| `erp_ai/agent/tools/registry.py` | sửa | U7b: `Grant.catalog_block`, `ToolContext.threshold_pct`, `streak_required` | có | 3.7, Sửa 2.2 |
| `erp_ai/agent/policy.py` | sửa | U7b: `PromptOverrides`, `prompt_overrides`, `auto_approve_streak`, `meets_confidence` (+ thân `is_below_confidence`), `one_click_approval_enabled` | **không** (N-5) | 3.7, Sửa 2.1, 6.2, 7 |
| `erp_ai/agent/runner.py` | sửa | U7b: bước (e) | **không** (N-5) | Sửa 2.3 |
| `erp_ai/agent/prompts.py` | sửa | U7b | có | 3.7 |
| `erp_ai/erp_ai_agent/report/erp_ai_approval_stats/{__init__.py, erp_ai_approval_stats.json, .py, .js}` | mới (U7b); `.js` sửa (U8) | U7b, U8 | có | 2.2, 3.8, Sửa 4 |
| `erp_ai/agent/tools/catalog.py` | sửa (1 mục `ACTION_HANDLERS`) | U8 | có | 3.6 |
| `erp_ai/agent/tools/write_ticket.py` | sửa (1 hằng) | U8 | có | 3.6 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.json` | sửa (1 option) | U8 | **không**; phán quyết (4) | Sửa 4 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | sửa (≤ 1 mục luật đích cố định) | U8 | **không**; phán quyết (4) | Sửa 4 |
| Test mới: `erp_ai/agent/tools/test_catalog_approvals.py`, `erp_ai/erp_ai_agent/report/erp_ai_approval_stats/test_erp_ai_approval_stats.py`, `erp_ai/agent/test_prompts.py` | mới | U7b | test | 8 |
| Test sửa: `erp_ai/tests/test_ticket_panel.py`, `erp_ai/tests/test_architecture.py`, `erp_ai/agent/tools/test_catalog_tools.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/test_policy.py`, `erp_ai/agent/test_agent_runner.py`, `erp_ai/agent/test_authority.py` | sửa | U7b | test | 8, 8' |
| Test sửa: `erp_ai/agent/tools/test_catalog.py`, `erp_ai/agent/tools/test_catalog_tools.py`, `erp_ai/agent/changes/test_apply_job.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`, `erp_ai/agent/tools/test_registry.py` (chỉ khi trúng từ cấm) | sửa | U8 | test | 8, Sửa 4 |

**Không chạm:** `transitions.py`, `apply_job.py`, `result_comment.py` (U7a sở hữu nhánh `Đã từ chối`, phán quyết (7)), `propose_change.py`, `change_decision.py`, `install.py`, `erp_ai_setting.json`. U7b không chạm `catalog.py`. U8 không chạm `registry.py`, `runner.py`, `policy.py`, `authority.py`, `hooks.py`.

**Thứ tự merge vào `team/FEAT-007`** theo review mục 5: U5b ∥ U7a → U7b → U8 (AC-64). Mỗi đơn vị rebase rồi chạy `cmd.test_one` cho mọi file chung trước khi merge. Ba ràng buộc "cùng commit": (i) dòng DocPerm `Agent` + 2 khóa `hooks.py` + 2 hook + `open_assignment_condition` + test Sửa 1.4; (ii) `decide_proposal` + dòng `PANEL_METHODS` + lời gọi `.js`; (iii) toàn bộ bảng Sửa 4.

**So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`** (không có đường dẫn mới nào ngoài addendum, trừ file này):
```
erp_ai/agent/tools/catalog_approvals.py                                         -> erp_ai OK
erp_ai/agent/tools/test_catalog_approvals.py                                    -> erp_ai OK
erp_ai/agent/test_prompts.py                                                    -> erp_ai OK
erp_ai/erp_ai_agent/report/erp_ai_approval_stats/__init__.py                    -> erp_ai OK
erp_ai/erp_ai_agent/report/erp_ai_approval_stats/erp_ai_approval_stats.json     -> erp_ai OK
erp_ai/erp_ai_agent/report/erp_ai_approval_stats/erp_ai_approval_stats.py       -> erp_ai OK
erp_ai/erp_ai_agent/report/erp_ai_approval_stats/erp_ai_approval_stats.js       -> erp_ai OK
erp_ai/erp_ai_agent/report/erp_ai_approval_stats/test_erp_ai_approval_stats.py  -> erp_ai OK
docs/team/features/FEAT-007/design-addendum-2-U7b-U8-fixes.md                   -> docs OK
```
**So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào ở bảng trên khớp → 0.

---

## 8'. Test plan (các dòng thay / thêm vào mục 8 `:343-381`)

Ký hiệu như `:341`, thêm `TAU` = `erp_ai/agent/test_authority.py`, `TSet` = `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`. Mọi dòng không nhắc ở đây giữ nguyên.

| AC / ràng buộc | Test (`file::Class::name`) | Ca biên / lỗi | Thay dòng |
|---|---|---|---|
| AC-36 ngưỡng tin cậy | `TT::TestAutoMode::test_confidence_69_vs_70` (ngưỡng qua `ctx.threshold_pct`); `TPol::TestMeetsConfidence::test_boundary`; `TPol::TestIsBelowConfidence::test_delegates_to_meets_confidence` | 69 / 70 / 80, `None` | `:351` |
| AC-36 cấu hình chuỗi | `TPol::TestAutoApproveStreak::test_reads_setting`, `::test_out_of_range_is_fail_closed`, `::test_missing_is_default`; `TT::TestAutoMode::test_streak_setting_5` (qua `ctx.streak_required`); `TRN::TestCatalogAuto::test_context_carries_threshold_and_streak` | 0, 101, -1, `None` | `:353` |
| AC-36 tool không đọc Setting (J-4) | `TT::TestAutoMode::test_tool_does_not_read_setting`; `::test_missing_context_values_never_auto`; `TArch::TestCatalogArchitecture::test_catalog_tools_reads_no_setting`; `::test_single_threshold_compare` | context thiếu | thêm |
| AC-36 / ADR-035 Ràng buộc 7 (J-5) | `TT::TestAutoMode::test_custom_field_auto_row_needs_approval` (đề xuất `Chờ duyệt`, 0 Custom Field, `why=implicit_commit`, không `commit`/`sql_ddl`, savepoint của test còn); `::test_implicit_commit_actions_always_refused` | chuỗi 50, pct 100 | thêm |
| AC-36 lỗi khi ghi | `TT::TestAutoMode::test_execute_refused_no_fallback_proposal` (+ không `commit`) | — | `:354` |
| AC-39 quyết định qua ngăn | `TPN::TestDecideProposal::test_approve_reject_edit_by_assignee` (reject → 1 job, đích không đổi); `::test_reject_via_panel_posts_one_result_comment` | chạy lại job | `:366` |
| AC-39 hook quyền (J-3) | `TP::TestProposalPermissionHook::test_list_equals_record_matrix`; `::test_list_paths_leak_nothing`; `::test_assignment_edges_same_in_both_paths`; `::test_restricted_agent_group_assigned`; `::test_instructor_and_agent_account_unchanged`; `TAU::TestOpenAssignmentCondition::test_sql_form_matches_is_assigned`; `::test_escaping` | 6 người × 3 đề xuất; ToDo `Closed`, hai ToDo; `'`, `%`, `_` | `:370` |
| AC-39 dữ liệu ngăn qua controller (J-6, (3)) | `TP::TestPanelSummary::test_can_decide_matches_decider`; `TArch::TestPanelArchitecture::test_panel_imports_controller_not_authority`; `::test_panel_read_keys_fixed`; `::test_decide_does_not_read_switches`; `::test_no_agent_session_in_whitelisted_modules` | — | thêm |
| ADR-035 Ràng buộc 1, 2, 3 | `TArch::TestProposalPermissionArchitecture::test_agent_docperm_pairs_with_hooks`; `::test_hooks_have_no_todo_or_bypass` | — | `:379` (bỏ `test_agent_docperm_read_only`) |
| AC-64 luật lưu, option | `TSet::TestCatalogRules::test_create_project_is_fixed_target`; `TAS::TestApprovalStats::test_js_filter_options_match_catalog_actions`; test ghim option của U0 và `test_action_target_doctypes_cover_catalog_actions` của U7a giữ xanh | DocType có / `fields` có | thêm |
| minor (c) | `TRG::TestToolModules::test_catalog_approvals_not_registered` | — | thêm |

### Đối chiếu AC (Done criteria)

- AC trong phạm vi: **AC-36, AC-37, AC-38, AC-39, AC-64** (như addendum `:405`).
- Sau sửa: **AC-36** có 11 dòng của addendum, trong đó `:351`, `:353`, `:354` thay theo bảng trên, cộng 2 dòng mới (J-4, J-5). **AC-37** 3 dòng (không đổi). **AC-38** 5 dòng (không đổi). **AC-39** 9 dòng, `:366`, `:370` thay, cộng 1 dòng (J-6), cộng kiểm tay 8.1 (bước 9 thêm comment). **AC-64** 5 dòng, cộng 1 dòng (luật lưu, option). Khớp 5/5.
- Ba test leader đòi: J-3 → `TP::TestProposalPermissionHook::test_list_paths_leak_nothing`; J-4 → `TT::TestAutoMode::test_tool_does_not_read_setting` + `TArch::TestCatalogArchitecture::test_catalog_tools_reads_no_setting`; J-5 → `TT::TestAutoMode::test_custom_field_auto_row_needs_approval`.

---

## Assumptions decided by the team (thêm / đổi)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U7b-4 | **Giữ**, architect xác nhận (phán quyết (2), ADR-035 QĐ 2) | — | — | — |
| A-U7b-5 | **Giữ**, architect chấp nhận (phán quyết (3), ADR-035 QĐ 4); bit lấy qua `policy.one_click_approval_enabled()` | ngăn không đọc Setting | — | — |
| A-U7b-11 | `ToolContext.threshold_pct`, `streak_required` mặc định `None`; `None` → vị từ sai (`"context"`) | giữ mọi chỗ khởi tạo cũ (như U1 `:166`) mà vẫn fail-closed | trường bắt buộc (vỡ mọi test dựng `ToolContext`) | đổi mặc định |
| A-U7b-12 | `open_assignment_condition` khớp `_assign` bằng LIKE đã thoát `\ % _`, cộng ToDo mới nhất `Open` của đúng `allocated_to` | cùng hai vế của `is_assigned`; không ký tự đại diện lọt | `JSON_CONTAINS` (phụ thuộc phiên bản MariaDB) | đổi thân hàm; test `test_sql_form_matches_is_assigned` giữ |
| A-U7b-13 | Lý do logger của vế tự commit = `"implicit_commit"`; vế đứng thứ 2, trước mức, ngưỡng, chuỗi | không truy vấn chuỗi cho hành động không bao giờ tự làm | đứng cuối | đổi thứ tự trong một hàm |

**Câu không chặn cho team-leader** (không ghi `questions.md` vì giới hạn của lời gọi này):
- (8) "Tạo Custom Field luôn cần duyệt, dù dòng là `Tự làm`" có chấp nhận không (analyst/người).
- A-U7b-7 vẫn mở.
- A-U7a-3 vẫn mở. Nếu trả lời "không", vế `assigned_by ≠ user` vào **cả** `is_assigned` và `open_assignment_condition` (Sửa 1.1).

---

## Bảng đóng: finding / phán quyết → sửa

| Finding / phán quyết | Giải bởi |
|---|---|
| J-3 (danh sách rộng hơn hook; DocPerm + hooks cùng commit) | Sửa 1 (1.1–1.4), Sửa 5 |
| J-4 (tool đọc Setting, so ngưỡng lần hai) | Sửa 2 (2.1–2.5), Sửa 7 (runner gọi `auto_approve_streak`) |
| J-5 (Custom Field "Tự làm" commit giữa lượt) | Sửa 3 |
| J-6 minor (ngăn import `authority`) | Sửa 6 |
| J-2 phần U7b (`:366` reject → 0 job) | Sửa 8 |
| Phán quyết (1) DocPerm `Agent` + hai hook, cùng commit, rút lui | Sửa 1.3, Sửa 5 |
| Phán quyết (2) tập đọc = "được giao" | Sửa 1.1, 1.2; A-U7b-4 |
| Phán quyết (3) bit `proposal_one_step` | Sửa 6 |
| Phán quyết (4) U8 sở hữu hằng, option, đích, luật lưu, một commit | Sửa 4 |
| Phán quyết (5) `PANEL_METHODS` và hai khóa `hooks.py` | Sửa 5 |
| Phán quyết (6) `_post_comment`, `record_summary` của U7a | Sửa 3 (dùng `_post_comment`), Sửa 6.1 (dùng `record_summary`), Sửa 9 (a) (bỏ N-6) |
| Phán quyết (7) phần U7b | Sửa 8 |
| Phán quyết (8) hành động tự commit không "Tự làm" | Sửa 3 |
| Phán quyết (9) chữ `:229-231` | Sửa 7 |
| Minor (a)–(e) | Sửa 9; (d), (e) cùng Sửa 4 |
