# FEAT-007 — design-w1-fixes-10: phán F-14 (T93), xác nhận F-9 (T82), trần mô tả `trigger` (T85, T140)

- Người viết: designer, 2026-11-15. Cỡ L. Chỉ tài liệu. Không chặn build (team-leader, `team.py` 09:10: READY build 66/174).
- Đầu vào: `preflight-w1.md:30` (F-9), `:35` (F-14), `:47` (T85, đếm ký tự); `tasks.md:755-760` (T82), `:824-828` (T93), `:786-790` (T85), `:1044-1048` (T140); `design-w1-fixes-3.md:46-53`; `design-addendum-1-U3.md:225-230`, `:146`, `:368`; `design-addendum-1-U1.md:136-187`; `design-addendum-1-U6b.md:314`; `design-w1-fixes-4.md` Điểm 1 (tên trường `GrantInputs.effective_level`).
- Mã đọc (chỉ đọc, `git show`): `team/FEAT-007` @ `caa555a` — `erp_ai/tests/test_tasks.py:11`, `:47`, `:54-68` (`_add_log`), `:71-73` (`_hand_action`), `:219` (`class TestCheckPrivilegeEscalation`), `:265-280` (`_log_row`), `:300`, `:936-946`, `:1019`, `:1050-1061`, `:1122-1133`; `erp_ai/agent/test_kpi.py:129-140` (`_log`); `erp_ai/agent/run_log.py:15-18`, `:49-93` (`action_entry`), `:104-139` (`write_entry`); `erp_ai/tasks.py:198-214`; `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py:6-18`, `erp_ai_log.json` (`actions` Long Text, `value_before`/`value_after` Code, `autoname` hash); `erp_ai/agent/tools/registry.py:55-107`; `erp_ai/agent/tools/site_api.py:571-678`; `erp_ai/agent/policy.py:235-240` (`PermissionSwitches`); `erp_ai/agent/tools/test_propose_change.py:18`, `:73-81`, `:435-441`; `erp_ai/agent/test_run_status.py:14-15`, `:44-48`; `erp_ai/constants.py:11` (`LEVELS`); `erp_ai/tests/test_architecture.py:168-176` (`POLICY_FIELDS`); `erp_ai/tests/test_doctype_descriptions.py:10`, `:15`, `:321-337`, `:532`, `:546-589`.
- Không đổi kiến trúc: theo ADR-033 Ràng buộc (`action_entry` là hàm dựng mục duy nhất), ADR-004/ADR-023 QĐ 5 (mã sản phẩm ghi ERP AI Log chỉ qua `write_entry`; luật `test_action_entries_built_only_in_run_log` miễn file test, `U3.md:368`), ADR-024 Ràng buộc (R5-14 của T93 không đổi), ADR-030 QĐ 2, QĐ 3 (bảng cấp). Không đổi quy tắc nghiệp vụ. Không có `DESIGN_CONFLICT`.

---

## Điểm 1 — F-14: `erp_ai/tests/test_tasks.py` dưới phép kiểm `ACTION_KEYS` của T93

### Hiện trạng (dữ kiện)
- `_hand_action` (`test_tasks.py:71-73`) trả dict năm khóa `tool, doctype, name, ok, instructor`; thiếu `value_before`, `value_after` của `ACTION_KEYS` (`run_log.py:15`). Mọi chỗ gọi (khoảng 40, `:482` tới `:1178`) đi qua `_log_row` (`:265-280`) → `run_log.write_entry(actions=…)`. Sau T93 (`U3.md:146` vế (b)) mọi test đó đỏ vì `ValueError`.
- Hai chỗ cố ý ghi `actions` không phải danh sách mục, để thử job cảnh báo chịu được dữ liệu xấu: `:1050-1057` (ba subtest `broken JSON`, `not a list`, `entry not a dict`, đều là chuỗi) và `:1130-1133` (`broken_actions`, chuỗi JSON cụt). Sau T93 không ghi được qua `write_entry`; dữ liệu loại này vẫn có thể có trong bảng (dòng ghi trước T93, sửa tay), nên ca thử phải giữ.
- `_agent_calls` (`:285-302`) dựng mục bằng `runner._action` (`:300`); từ T91 hàm đó đi qua `action_entry` (dòng Receives của T93) → không sửa ở đây.
- `action_entry(tool, doctype, name, ok, *, instructor=…)` (`run_log.py:49-93`) trả đủ `ACTION_KEYS` theo thứ tự; `value_before`/`value_after` mặc định `None`; `ok=False` thêm `reason = NO_REASON`. Job cảnh báo đọc ảnh chụp ở **cột** `value_before`/`value_after` của dòng (`tasks.py:198`, `:210`), không ở khóa trong mục, và bỏ qua mục `ok` sai (`tasks.py:214`). Vậy mục bảy khóa (thêm `reason` cho ca `ok=False` ở `:938`) cho đúng cùng kết quả cảnh báo như mục năm khóa.
- Tiền lệ dựng dòng ERP AI Log trong test không qua `write_entry`: `erp_ai/agent/test_kpi.py:129-140` (`frappe.get_doc({...}).db_insert()`), và chính `test_tasks.py:54-68` (`_add_log`, `.insert(ignore_permissions=True)`). Controller `ERPAILog` chỉ chặn tài khoản agent (`erp_ai_log.py:6-18`); test chạy bằng Administrator, hai chỗ gọi không nằm trong `_as_agent()`.

### Phán quyết
1. **`_hand_action` đổi một chỗ, không đổi 40 chỗ gọi.** Giữ chữ ký `_hand_action(tool, doctype, name, ok=True)`; thân thành:
   ```python
   return run_log.action_entry(tool, doctype, name, ok, instructor=INSTRUCTOR)
   ```
   Docstring: "An action entry of a `reason` row built by the one entry builder (`run_log.action_entry`), for cases the tools cannot seed." `run_log` đã import (`:11`). Không chỗ gọi nào đổi.
2. **Dòng có `actions` xấu dựng bằng `db_insert` thẳng**, như `test_kpi.py:129-140` (chọn `db_insert` thay `.insert()`: dữ liệu cố ý sai, `db_insert` bỏ qua mọi kiểm ở tầng tài liệu, nên ca thử không phụ thuộc vào kiểm sau này thêm vào controller). Thêm phương thức của `TestCheckPrivilegeEscalation`, đặt ngay sau `_log_row`:
   ```python
   def _bad_actions_row(self, actions_text, at=SEEDED_AT):
       """Insert a `reason` row whose `actions` column is not a list of entries (rows from before T93, hand
       edits). `write_entry` refuses it, so insert it directly as `test_kpi._log` does; back-date `creation`."""
       doc = frappe.get_doc(
           {
               "doctype": LOG_DOCTYPE,
               "run_id": "ERPAI-TEST-run",
               "entry_type": "reason",
               "trigger": TRIGGER_TICKET_INSERT,
               "turn": 1,
               "instructor": INSTRUCTOR,
               "actions": actions_text,
           }
       )
       doc.db_insert()
       frappe.db.set_value(LOG_DOCTYPE, doc.name, "creation", at, update_modified=False)
       return doc.name
   ```
   (thụt lề bằng tab như file). Trường giống đúng `_log_row` trừ `value_before`/`value_after` (hai chỗ gọi đều không truyền). Không gọi trong `_as_agent()`.
3. **Hai chỗ gọi đổi tên hàm, tham số giữ nguyên:** `:1057` `name = self._log_row(actions, at=at)` → `name = self._bad_actions_row(actions, at=at)`; `:1130-1133` `broken_actions = self._log_row(` → `broken_actions = self._bad_actions_row(`. Không khẳng định nào đổi.
4. **Chuỗi chủ `test_tasks.py`: T94 (đã tick) → T82 → T93.** T93 thêm file vào `files:` và `depends: T82`. Sửa (1)–(3) xanh cả trên BASE (trước khi đổi `write_entry`): dev commit test riêng, đứng trước commit mã của `run_log.py`.
5. Ngoài phạm vi điểm này: F-15 (`test_erp_ai_log.py`) do team-leader phán `files:`; nếu thêm, nối file đó sau `erp_ai/tests/test_tasks.py` ở dòng tiêu đề dưới đây.

### Dòng task T93 (dán thay dòng tiêu đề, Tiêu chí, Returns, Expect; Receives giữ)

```
- [ ] T93 — `write_entry` từ chối mục hành động viết tay — files: erp_ai/agent/run_log.py, erp_ai/agent/test_run_log.py, erp_ai/tests/test_architecture.py, erp_ai/tests/test_tasks.py — test: erp_ai/agent/test_run_log.py — depends: T92, T89, T82
  - Tiêu chí: AC-10; `U3.md:146` vế (b), `:368`; ADR-033 Ràng buộc; F-14 (`design-w1-fixes-10.md` Điểm 1: `test_tasks.py` dựng mục năm khóa và ghi `actions` hỏng qua `write_entry`, nên đổi cùng task; chuỗi chủ `test_tasks.py`: T94 → T82 → T93).
  - Returns: `write_entry` ném `ValueError`, 0 dòng, khi một phần tử `actions` thiếu khóa của `ACTION_KEYS`; luật `test_action_entries_built_only_in_run_log`. Luật bắt được vi phạm ở mã đã merge → trả `DESIGN_CONFLICT` kèm danh sách. R5-14: phép kiểm `ACTION_KEYS` chạy trước `insert`; `insert` và `commit` vẫn trong cùng lời gọi `write_entry`; reviewer dán thân `write_entry` sau merge, `erp_ai/agent/test_agent_runner.py` (gồm test ADR-024 QĐ 2 của FEAT-005) chạy lại xanh. T93 đứng trước T110 (R5-15). Test chỉ đổi đúng các chỗ sau trong `erp_ai/tests/test_tasks.py`, không đổi khẳng định nào: (1) thân `_hand_action` (`:71-73`) thành `return run_log.action_entry(tool, doctype, name, ok, instructor=INSTRUCTOR)`, chữ ký giữ, khoảng 40 chỗ gọi không sửa; (2) thêm `TestCheckPrivilegeEscalation._bad_actions_row(self, actions_text, at=SEEDED_AT)` ngay sau `_log_row`: `frappe.get_doc({doctype: LOG_DOCTYPE, run_id: "ERPAI-TEST-run", entry_type: "reason", trigger: TRIGGER_TICKET_INSERT, turn: 1, instructor: INSTRUCTOR, actions: actions_text}).db_insert()` (như `erp_ai/agent/test_kpi.py:129-140`), rồi lùi `creation` như `_log_row` `:279`, trả tên dòng; (3) `:1057` và `:1130-1133` đổi `self._log_row(` thành `self._bad_actions_row(`, tham số giữ (dòng số đo ở `team/FEAT-007` @ `caa555a`, dịch theo T82).
  - Expect: `TestWriteEntry::test_hand_built_entry_rejected`; `test_architecture.py::test_action_entries_built_only_in_run_log` xanh. Sửa test (1)–(3) là commit riêng trước commit mã, xanh trên BASE; sau commit mã `cmd.test_one` xanh cả file `erp_ai/tests/test_tasks.py`, trong đó `TestCheckPrivilegeEscalation::test_unusable_snapshot_shapes_listed_without_before_after` (3 subtest `actions`) và `::test_broken_snapshot_json_listed_without_before_after` xanh, khẳng định không đổi; reviewer kiểm diff của `test_tasks.py` chỉ có ba chỗ trên.
```

---

## Điểm 2 — F-9: xác nhận `GrantInputs` tương đương cho ba lời gọi chữ ký cũ (T82)

Xác nhận phán quyết của team-leader: T82 thêm `erp_ai/agent/tools/test_propose_change.py` và `erp_ai/agent/test_run_status.py` vào `files:`, chỉ đổi ba lời gọi `get_tool_schemas` chữ ký cũ và dòng import cần cho chúng; không khẳng định nào đổi.

### Cơ sở tương đương (dữ kiện)
- Bảng cũ (`registry.py:55-79`): `read`, `ticket_write` luôn; `task_write` khi `has_instructor`; `change_propose` khi `change_enabled ∧ level == "L3" ∧ has_instructor`; `site_admin` khi cùng điều kiện đó (cầu) hoặc toàn quyền; `site_unrestricted` chỉ khi toàn quyền (mọi lời gọi dưới đây `unrestricted=False`).
- Bảng mới (`U1.md:166-187`): `change_propose` theo `switches.code_change`, `site_admin` theo `switches.record_tools` (sau khi T82 gỡ cầu, công tắc (4) không còn mở (2)). Vậy `change_enabled` cũ = **cả hai** công tắc `code_change` và `record_tools` cùng giá trị. `over_budget`, `below_threshold` để mặc định `False`; `main_path_level` là trường bắt buộc (không mặc định, `U1.md:141`) → đặt bằng mức quyền, như `ToolContext.grant_inputs()` làm khi `main_path_level` là `None`. Tên trường mức là `effective_level` (`design-w1-fixes-4.md` Điểm 1). `record_tools`, `code_change` không thuộc `POLICY_FIELDS` (`test_architecture.py:168-176`).
- Import: `PermissionSwitches` từ `erp_ai.agent.policy`; `GrantInputs` từ `erp_ai.agent.tools.registry` (cùng dòng với `get_tool_schemas`). Thứ tự import theo `cmd.format`/`cmd.lint`.

### Ba lời gọi

| Chỗ | Lời gọi cũ | Thay bằng | Tập nhóm cũ = mới |
|---|---|---|---|
| `test_propose_change.py:76` (`TestProposeGrant.test_offered_only_with_switch_l3_and_instructor`, hàm con `names`) | `get_tool_schemas(level, has_instructor, change_enabled)` | `get_tool_schemas(GrantInputs(effective_level=level, main_path_level=level, has_instructor=has_instructor, switches=PermissionSwitches(record_tools=change_enabled, code_change=change_enabled)))` | `("L3", True, True)`: read, ticket_write, task_write, change_propose, site_admin; `("L3", True, False)`: read, ticket_write, task_write; `("L3", False, True)`: read, ticket_write; `("L2", True, True)`: read, ticket_write, task_write. `("L0", True, True)`: cũ cho read, ticket_write, task_write, mới cho `()` (bước (1) của `grant`, ADR-030 QĐ 3, hành vi mới có chủ đích); khẳng định `:81` chỉ đòi không có tên nào của `TOOL_NAMES` (lọc ở `:77`) → đúng ở cả hai |
| `test_propose_change.py:437` (`test_no_delete_or_rename_operation_exists`) | `get_tool_schemas("L3", True, True)` | `get_tool_schemas(GrantInputs(effective_level="L3", main_path_level="L3", has_instructor=True, switches=PermissionSwitches(record_tools=True, code_change=True)))` | read, ticket_write, task_write, change_propose, site_admin (`api_list_records`, `api_get_record`, `api_create_record`, `api_update_record`; `api_delete_record`, `api_submit_record`, `api_call_method` thuộc `site_unrestricted`, `site_api.py:644-678`, không được cấp) — đúng tập hôm nay |
| `test_run_status.py:45` (`test_every_granted_tool_and_classify_step_has_label`) | `get_tool_schemas(LEVELS[-1], True, False)` | `get_tool_schemas(GrantInputs(effective_level=LEVELS[-1], main_path_level=LEVELS[-1], has_instructor=True, switches=PermissionSwitches()))` | read, ticket_write, task_write (`LEVELS[-1] == "L3"`, `constants.py:11`) |

Dòng import: `test_propose_change.py:18` → `from erp_ai.agent.tools.registry import GrantInputs, ToolContext, execute_tool, get_tool_schemas`, thêm `from erp_ai.agent.policy import PermissionSwitches`; `test_run_status.py:14` → `from erp_ai.agent.tools.registry import GrantInputs, get_tool_schemas`, thêm `from erp_ai.agent.policy import PermissionSwitches`.

### Dòng task T82 (dán thay dòng tiêu đề; thêm dòng "Chèn 10" ngay sau dòng "Chèn 8"; các dòng khác giữ)

```
- [ ] T82 — `_reason` lấy tool và cờ khối từ `grant`; bỏ đường cấp cũ và cầu của T76 — files: erp_ai/agent/runner.py, erp_ai/agent/tools/registry.py, erp_ai/agent/prompts.py, erp_ai/agent/test_agent_runner.py, erp_ai/agent/tools/test_registry.py, erp_ai/agent/tools/test_site_api.py, erp_ai/tests/test_tasks.py, erp_ai/tests/test_architecture.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/agent/test_run_status.py — test: erp_ai/agent/test_agent_runner.py — depends: T81, T79, T65
  - Chèn 10 (F-9 của `preflight-w1.md:30`; phán `files:` của team-leader, đầu vào tương đương do designer xác nhận ở `design-w1-fixes-10.md` Điểm 2; file thứ chín, thứ mười của `files:`): chỉ đổi ba lời gọi `get_tool_schemas` chữ ký cũ và dòng import của chúng, không đổi khẳng định nào: `erp_ai/agent/tools/test_propose_change.py:76` → `get_tool_schemas(GrantInputs(effective_level=level, main_path_level=level, has_instructor=has_instructor, switches=PermissionSwitches(record_tools=change_enabled, code_change=change_enabled)))`; `:437` → `get_tool_schemas(GrantInputs(effective_level="L3", main_path_level="L3", has_instructor=True, switches=PermissionSwitches(record_tools=True, code_change=True)))`; `erp_ai/agent/test_run_status.py:45` → `get_tool_schemas(GrantInputs(effective_level=LEVELS[-1], main_path_level=LEVELS[-1], has_instructor=True, switches=PermissionSwitches()))`; `GrantInputs` import từ `erp_ai.agent.tools.registry`, `PermissionSwitches` từ `erp_ai.agent.policy`. Expect thêm: `cmd.test_one` xanh cả file `erp_ai/agent/test_run_status.py` (`erp_ai/agent/tools/test_propose_change.py` đã có ở dòng Expect); reviewer kiểm diff của hai file chỉ có ba lời gọi và dòng import (dòng số đo ở `team/FEAT-007` @ `caa555a`).
```

---

## Điểm 3 — Trần 400 ký tự của mô tả `trigger` (ERP AI Log): T85 và T140

### Hiện trạng (dữ kiện)
- Mô tả `trigger` hiện 274 ký tự; T85 nối câu của `U3.md:228` → 392, còn 8 (`preflight-w1.md:47`). Task U6b nối `requester_reply`, `kb_draft` vào cùng mô tả là **T140** ("Hai trigger mới `requester_reply`, `kb_draft` trong một commit [migrate]", `tasks.md:1044`; câu thêm theo `U6b.md:314`) → vượt trần, `TestDoctypeDescriptions::test_descriptions_at_most_400_chars` (`test_doctype_descriptions.py:546`) đỏ.
- Luật phải giữ: trần `MAX_DESCRIPTION_CHARS = 400` (`:10`, đếm `len` của chuỗi Python); cụm bắt buộc `trigger` hiện có `("ticket_insert", "comment_mention", "change_action", "bình luận", "bước của đề xuất")` (`:337`), T85 thêm `"setting_save"`, `"scheduled_job"`, T140 thêm `"requester_reply"`, `"kb_draft"`; trường chỉ đọc phải có `"Hệ thống tự ghi"` và `"không sửa được"` (`:15`, `:580-589`).

### Phán quyết
Viết lại **cả** mô tả `trigger` ngay ở T85 theo dạng gọn "giá trị: nghĩa;" theo thứ tự option, để T140 chỉ chèn một đoạn, không sửa chữ nào khác. Câu thêm của `U3.md:228` và `U6b.md:314` cho trường `trigger` được thay bằng hai chuỗi dưới đây (nghĩa giữ nguyên; mô tả `entry_type` không đổi, 346 ký tự sau T85). `phrases` không đổi so với hai thiết kế đó.

**T85** — giá trị `description` của trường `trigger` trong `erp_ai_log.json` (289 ký tự):
```
Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được.
```

**T140** — giá trị `description` của trường `trigger` (388 ký tự; = chuỗi T85 với đoạn `requester_reply: người tạo phiếu trả lời tin của bot; kb_draft: soạn bài CSKT nháp khi đóng phiếu; ` chèn ngay trước `change_action:`, đúng thứ tự option `TRIGGERS + CHANGE_TRIGGERS + BOT_ACTION_TRIGGERS`):
```
Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; requester_reply: người tạo phiếu trả lời tin của bot; kb_draft: soạn bài CSKT nháp khi đóng phiếu; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được.
```

Đo bằng lệnh (đọc thôi, `python3 -I -c`, `len` như `test_doctype_descriptions.py:552`; kiểm luôn mọi cụm bắt buộc và hai cụm của trường chỉ đọc, và chuỗi T140 đúng bằng chuỗi T85 cộng đoạn chèn):
```
T85 289 111
T140 388 12
missing [] []
T140 = T85 with insert: True
```
(cột 3 = số ký tự còn dưới trần; `missing` = cụm bắt buộc thiếu ở T85, ở T140.)

### Dòng task (thêm ngay sau dòng Returns của mỗi task; các dòng khác giữ)

T85:
```
  - Chèn 10 (`design-w1-fixes-10.md` Điểm 3, trần 400 của `preflight-w1.md:47`): mô tả `trigger` của `erp_ai_log.json` là ĐÚNG chuỗi sau (289 ký tự), thay câu thêm của `U3.md:228` cho trường này; mô tả `entry_type` theo `U3.md:228` (346 ký tự): "Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được." Expect thêm: `erp_ai/tests/test_doctype_descriptions.py::TestDoctypeDescriptions::test_descriptions_at_most_400_chars`, `::test_required_phrases_present`, `::test_read_only_fields_say_system_writes` xanh sau `cmd.migrate`.
```

T140:
```
  - Chèn 10 (`design-w1-fixes-10.md` Điểm 3): mô tả `trigger` của `erp_ai_log.json` là ĐÚNG chuỗi sau (388 ký tự; chuỗi của T85 chèn thêm đoạn `requester_reply: …; kb_draft: …; ` ngay trước `change_action:`, không đổi chữ nào khác), thay câu thêm của `U6b.md:314`: "Nguồn kích hoạt — ticket_insert: phiếu mới tạo; comment_mention: bình luận có từ khóa kích hoạt; requester_reply: người tạo phiếu trả lời tin của bot; kb_draft: soạn bài CSKT nháp khi đóng phiếu; change_action: bước của đề xuất thay đổi; setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hay theo sự kiện, không qua model. Hệ thống tự ghi, không sửa được." Expect thêm: `erp_ai/tests/test_doctype_descriptions.py::TestDoctypeDescriptions::test_descriptions_at_most_400_chars`, `::test_required_phrases_present` xanh sau `cmd.migrate`.
```

---

## Giả định do nhóm tự quyết
- A-10-1: dòng `actions` xấu dựng bằng `db_insert` (không `.insert()`), vì ca thử là dữ liệu đã nằm trong bảng; tiền lệ `test_kpi.py:129-140`. Không phải quy tắc nghiệp vụ.
- A-10-2: ở ba lời gọi F-9, `change_enabled` cũ ánh xạ sang cả `record_tools` và `code_change` để giữ đúng tập tool hôm nay (cầu cũ mở cả hai nhóm).
- A-10-3: mô tả `trigger` dạng "giá trị: nghĩa;" và bỏ vế "(thường do người duyệt thực hiện)" để có chỗ cho T140; nghĩa từng trigger giữ như `U3.md:228`, `U6b.md:314`.

Câu hỏi nghiệp vụ: 0.
