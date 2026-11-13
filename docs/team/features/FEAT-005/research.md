Feature: FEAT-005
Stage: research
Author-agent: researcher
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Research FEAT-005 — Tài khoản agent không có System Manager ghi được User và các DocType cấu hình ra sao trên Frappe 15.126.1, và chỗ nào Frappe không tự chặn

Team-leader giao ID mà không kèm câu hỏi. Researcher lấy câu hỏi từ phần spec để lại cho architect: spec `:77` ("Cách cấp do architect quyết"), `:84` (ngoại lệ tham số DocType đích) và A-8 (`:136`). Có ba câu hỏi con:

1. **Q1 — User và role.** Một role không phải System Manager cần quyền gì để tạo User và gán role bằng `insert()`/`save()` có kiểm quyền? Frappe có tự chặn việc gán role quản trị không? Câu trả lời là bảng sự thật, mỗi dòng có nguồn.
2. **Q2 — DocType cấu hình.** Mặc định role nào có quyền trên từng DocType đích? Khi ghi, Frappe chạy những tác dụng phụ nào làm sai giả định của spec? Câu trả lời là bảng sự thật, mỗi dòng có nguồn.
3. **Q3 — Cách cấp quyền.** Có những cách nào để cài quyền hẹp mà cài lại được và nhìn thấy trong Desk? Câu trả lời là bảng phương án kèm khuyến nghị; architect quyết.

## Câu trả lời ngắn
- Tài khoản agent cần `create`/`write` ở permlevel 0 **và** `write` ở permlevel 1 trên `User`, vì bảng `roles` nằm ở permlevel 1. Frappe **không** chặn việc gán `System Manager` hay `Administrator` cho người có các quyền đó. Thiếu quyền permlevel 1 thì Frappe **lặng lẽ bỏ** các role mới, không báo lỗi. Vì vậy tool vừa là chốt duy nhất cho danh sách role, vừa phải đọc lại role sau khi lưu.
- Sau khi agent có quyền ghi `Custom Field`/`Property Setter`/`System Settings`, Frappe không còn giới hạn gì thêm: agent đổi được `permlevel` của bất kỳ trường nào, và sửa được mọi trường bảo mật của System Settings vì DocType này không có trường nào ở permlevel > 0. Ở các DocType này, lớp phân quyền thứ hai của ADR-005 không còn tác dụng.
- Có 4 tác dụng phụ trái với spec:
  - Lưu một Workflow, **kể cả khi chưa kích hoạt**, vẫn tạo Custom Field (DDL, tự commit) và UPDATE hàng loạt chứng từ có sẵn.
  - Notification có `set_property_after_alert`, và khi gửi sẽ ghi chứng từ bằng `ignore_permissions=True`. Kênh Slack/SMS cùng `cc`/`bcc` tự do có thể gửi dữ liệu ra ngoài.
  - Assignment Rule tự chia sẻ chứng từ cho người được giao chưa có quyền đọc.
  - `make_property_setter` bỏ qua phân quyền.

Độ tin cậy: **cao** cho các sự thật (đọc mã nguồn ở tag `v15.126.1`, có test của chính Frappe). **Trung bình** cho khuyến nghị, vì còn tùy cách architect cân với ADR-005 và ADR-006.

## Phiên bản đang dùng
- `frappe @ 15.126.1`: `apps/frappe/frappe/__init__.py:__version__`. Checkout cục bộ ở commit `2e9ecdc03f` (`git describe`: `v15.118.0-1106-g2e9ecdc03f`). Hành vi chính đã được đối chiếu với tag `v15.126.1` trên GitHub. Số dòng ghi trong bài là số dòng của bản cục bộ.
- `erpnext @ 15.83.0` (`apps/erpnext/erpnext/__init__.py`), `hrms @ 15.51.0` (`apps/hrms/hrms/__init__.py`), `helpdesk @ 15.1.0` (`apps/helpdesk/helpdesk/__init__.py`).
- Cache: `docs/team/research/` chưa có mục nào cho chủ đề này, nên đây là research mới.

## Q1 — User và role (sự thật)
| # | Sự thật | Nguồn |
|---|---|---|
| U1 | Quyền chuẩn của `User`: System Manager có full quyền ở level 0, có read/write ở **level 1**; Desk User chỉ có `select`. | `frappe/core/doctype/user/user.json:890-913`; GitHub tag [S1] |
| U2 | Các trường ở permlevel 1 gồm `roles` (Has Role), `role_profile_name`, `user_type`, `block_modules`, `user_emails`, `restrict_ip`, `login_after`, `login_before`, `api_key`, `api_secret`, `reset_password_key`. `module_profile` ở level 0. | `user.json:227-649`; [S1] |
| U3 | Khi lưu, các trường ở permlevel mà người lưu không có quyền `write` sẽ bị **đặt lại về giá trị cũ hoặc giá trị mặc định, không báo lỗi**. Riêng `Administrator` và `flags.ignore_permissions` được bỏ qua bước này. Có cờ hẹp `doc.flags.ignore_permlevel_for_fields = [...]` để bỏ qua bước đặt lại cho từng trường. | `frappe/model/document.py:928-951`, `:3018-3046`; [S2] |
| U4 | Test của Frappe chứng minh U3 với trường `roles`: user không có quyền level 1 gọi `add_roles("System Manager")` thì role "is not added (it is reset)"; khi đặt `ignore_permlevel_for_fields = ["roles"]` thì role được thêm. | `frappe/core/doctype/user/test_user.py:237-269`; [S3] |
| U5 | `User.validate` **không** kiểm người lưu được gán role nào. Nó chỉ bỏ role trùng, role bị tắt, và mọi role của Guest. Ai có quyền ghi `roles` thì gán được cả `System Manager`. Trong file, `only_for` chỉ xuất hiện ở `generate_keys` (System Manager) và `impersonate` (Administrator). | `user.py:172-206`, `:605-642`; [S4] |
| U6 | `role_profile_name` có giá trị thì `validate` **thay toàn bộ** `roles` bằng role của Role Profile. | `user.py:208-212` |
| U7 | `has_permission` của User không cho ai ngoài Administrator đọc hay sửa `Administrator`/`Guest`. Frappe đã chặn sẵn một phần của A-5. | `user.py:1243-1246`; [S4] |
| U8 | Email chào mừng chỉ gửi khi `send_welcome_email = 1`. Trường này không có giá trị mặc định trong JSON, nên tool phải tự đặt (A-6). Không có Email Account gửi đi thì Frappe hiện `msgprint` và `log_error`, **không** ném lỗi, và user vẫn được tạo. | `user.py:347-377`, `user.json:175-178` |
| U9 | `before_insert` có throttle: quá `throttle_user_limit` (mặc định 60) user mỗi 60 giây thì ném lỗi "Throttled". Bước này bỏ qua khi `in_test`. Các hook sau khi tạo (`create_contact`, `share_with_self`, Notification Settings) tự dùng `ignore_permissions`/`ignore_share_permission`, nên user không phải System Manager vẫn tạo được User. | `user.py:163-170`, `:229-243`, `:339-345`, `:1303-1309`, `:1323-1352`; [S4] |
| U10 | Meta dùng **Custom DocPerm thay cho toàn bộ DocPerm** khi DocType đó có ít nhất 1 dòng Custom DocPerm. `add_permission`/`setup_custom_perms` chép DocPerm chuẩn sang Custom DocPerm trước khi thêm dòng mới. Từ lúc đó, mọi thay đổi DocPerm chuẩn ở bản Frappe sau không còn áp dụng cho DocType ấy. | `frappe/model/meta.py:553-566`; `frappe/permissions.py:660-712`; [S5] |

## Q2 — DocType cấu hình (sự thật)
| # | DocType | Quyền mặc định | Tác dụng phụ / chỗ Frappe không chặn | Nguồn |
|---|---|---|---|---|
| C1 | Custom Field | System Manager, Administrator | `on_update` → `frappe.db.updatedb` → `sql_ddl`, mà `sql_ddl` **commit giao dịch trước** khi chạy DDL. Không rollback được, kể cả trong test. Frappe tự chặn trùng tên trường. Người có quyền ghi Custom Field đặt được `permlevel`, `reqd`, `fetch_from` cho trường mới trên mọi DocType. | `custom/doctype/custom_field/custom_field.py:162-216`; `database/database.py:422-426`; [S6][S7] |
| C2 | Property Setter | System Manager, Administrator | Helper `make_property_setter` ghi rõ "WARNING: Ignores Permissions" và đặt `flags.ignore_permissions = True`, **nên tool không được dùng**. `validate` của bản ghi mới xóa Property Setter cũ cùng khóa bằng `frappe.db.delete`, nên tool phải đọc giá trị trước khi insert. Người có quyền ghi Property Setter đổi được `permlevel` của bất kỳ trường nào, tức là đổi phân quyền. | `custom/doctype/property_setter/property_setter.py:39-90`; [S8] |
| C3 | Holiday List (ERPNext) | Chỉ HR Manager (C/R/W/D) | `validate` tự chặn ngày nằm ngoài `from_date`..`to_date` và ngày trùng (AC-9 có sẵn một phần). `on_update` của hrms chỉ xóa cache. | `erpnext/setup/doctype/holiday_list/holiday_list.json:150-160`, `holiday_list.py:38-152`; `hrms/hooks.py:133-136`; [S9] |
| C4 | Workflow | System Manager | `on_update` chạy **dù `is_active = 0`**: (a) nếu DocType đích chưa có trường trạng thái thì tạo Custom Field, với `owner = "Administrator"` và không bỏ qua phân quyền. Agent vì thế cần quyền tạo Custom Field. DDL commit như C1. Chỉ Administrator xóa được trường này (`custom_field.py:218-225`). (b) `update_default_workflow_status` chạy **UPDATE SQL thẳng** lên mọi chứng từ có sẵn của DocType đích còn để trống trường trạng thái. Kích hoạt thì một câu SQL thẳng tắt mọi Workflow khác của cùng DocType. Transition `allowed` (role nào được duyệt) là quyền nghiệp vụ trên thực tế. | `workflow/doctype/workflow/workflow.py:34-121`; [S10][S11] |
| C5 | Notification | System Manager | (a) `set_property_after_alert` + `property_value`: lúc gửi, ghi chứng từ bằng `doc.save(ignore_permissions=True)`, nên đây là một đường ghi vòng qua phân quyền. (b) `channel` có Slack (webhook ra ngoài) và SMS. (c) `cc`/`bcc` của Notification Recipient là trường `Code` tự do. (d) `is_standard = 1` → `export_module_json` ghi file vào thư mục app. (e) Frappe chỉ cấm DocType `Email Queue`. `condition` chạy qua `safe_eval`; `message` render trong Jinja sandbox với `restrict_globals=True`. | `email/doctype/notification/notification.py:21`, `:87-131`, `:189-226`; `notification_recipient.json:18-37`; [S12][S13] |
| C6 | Email Template | System Manager; Desk User chỉ đọc | Không thấy tác dụng phụ đáng kể. | `email/doctype/email_template/email_template.json` |
| C7 | Assignment Rule | System Manager | Khi chạy, `do_assignment` xóa giao việc cũ rồi gọi `assign_to._add(ignore_permissions=True)`. Nếu người được giao **chưa có quyền đọc** chứng từ thì Frappe **tự chia sẻ** chứng từ cho họ qua `add_docshare`, trừ khi bật `disable_document_sharing`. Vậy Assignment Rule nới quyền đọc. Frappe chỉ cấm DocType `ToDo`. | `automation/doctype/assignment_rule/assignment_rule.py:44-101`; `desk/form/assign_to.py:122-134`; [S14][S15] |
| C8 | System Settings | System Manager, chỉ level 0; **không trường nào ở permlevel > 0** | Có quyền `write` là sửa được mọi trường: mật khẩu, 2FA, phiên, scheduler, backup. Frappe không có cách nào giới hạn quyền ghi vào nhóm hiển thị/khu vực. | `core/doctype/system_settings/system_settings.json`; [S16] |
| C9 | Custom DocPerm, User Permission, Module Profile, Role, Role Profile | System Manager | Không đụng tới (ngoài phạm vi). Chỉ cần cho danh sách cấm cứng: "role có create/write trên User hoặc DocType phân quyền" tính được từ `frappe.get_meta(dt).permissions`, vì giá trị này đã tính Custom DocPerm (U10). | `meta.py:553-566` |

Tài liệu người dùng chính thức nói cùng ý: field ở permlevel X chỉ nối với quy tắc quyền ở level X [S17][S18]; tick "Is Active" thì các Workflow khác bị tắt [S11]. Tài liệu không nói gì về các tác dụng phụ ở C4(b), C5(a) và C7. Các điểm đó chỉ có trong mã nguồn ở tag.

## Mâu thuẫn tài liệu/mã ↔ spec (không chọn hộ architect)
- **M1: Workflow "chưa kích hoạt" không vô hại.** Spec mục 6 và A-7 coi việc tạo hay sửa Workflow chưa kích hoạt là làm ngay, không cần "ok". Mã ở C4 thì vẫn tạo Custom Field (không xóa được nếu không phải Administrator) và UPDATE dữ liệu nghiệp vụ. Có hai cách: A: giữ spec, chấp nhận hai tác dụng này và ghi vào cách hoàn tác; B: bắt "ok" từ lúc tạo, hoặc chỉ cho tạo Workflow khi DocType đích đã có trường trạng thái.
- **M2: Lớp thứ hai của ADR-005 không giữ được.** ADR-005 giả định phân quyền Frappe là lớp thứ hai. Ở User (role), Custom Field, Property Setter, System Settings, quyền Frappe cần cấp đã rộng bằng System Manager trong phạm vi DocType đó (U5, C1, C2, C8), nên tool là chốt duy nhất. A-8 đã ghi điều này cho User. Mã cho thấy nó đúng cả với ba DocType kia.
- **M3: Tác dụng phụ ngay trong lúc chạy tool.** Ràng buộc ADR-005 cấm `ignore_permissions` và `frappe.db.sql` có ghi *trong tool*. Nhưng `Workflow.on_update` và `Custom Field.on_update` của Frappe tự chạy SQL ghi và DDL commit trong lúc tool gọi `insert()`. Tool không vi phạm câu chữ, nhưng tác dụng thì có.

## Phương án — cấp quyền cho tài khoản agent (Q3)
Tiêu chí từ NFR: NFR-1 (0 lần gán role cấm), NFR-2 (0 lần ghi ngoài tập cho phép), NFR-6 (giữ nguyên ở `L0`/`L1`), AC-15 (chạy không cần System Manager), ADR-005 Ràng buộc, ADR-006 (cài lặp lại được).

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| **A. Custom DocPerm cho role `ERP AI Agent`** trên từng DocType đích, cài trong thủ tục cài/migrate, giống tiền lệ `_ensure_task_permission` (`erp_ai/install.py:184-205`). `User`: level 0 C/R/W + level 1 R/W. | Đúng ADR-005: tool không có cờ bỏ quyền nào. Nhìn thấy trong Role Permission Manager. Cài lặp lại được. Có sẵn mẫu trong repo. | Level 1 trên User mở luôn `user_type`, `restrict_ip`, `login_after`, `role_profile_name`, `block_modules` ở tầng Frappe (U2). DocType nào có Custom DocPerm cũng không còn nhận thay đổi DocPerm chuẩn từ bản Frappe sau (U10). Quyền vẫn còn khi hạ về `L1`, dù khi đó không tool nào dùng tới. | Lỗi trong tool thành lỗi bảo mật thật (M2). Cảnh báo hằng ngày không theo dõi Custom DocPerm do *installer* tạo, vì `modified_by` khi cài là Administrator. | Thấp: khoảng 10 dòng cài và test cài hai lần. |
| **B. Như A, nhưng User chỉ cấp level 0**; tool đặt `doc.flags.ignore_permlevel_for_fields = ["roles"]` sau khi đã kiểm danh sách role. | Quyền Frappe hẹp hơn A: agent không đổi được `user_type`, `restrict_ip`, `role_profile_name` ở bất kỳ đường nào. Bỏ quyền đúng một trường, nằm trong mã có test. | Trái tinh thần Ràng buộc ADR-005 (bỏ quyền trong tool), nên cần một ngoại lệ ghi trong ADR và sửa test tĩnh của ADR-005. Cờ này không có trong tài liệu, chỉ có ở mã và test của Frappe [S2][S3]; độ bền giữa các bản là `UNVERIFIED`. | Bản Frappe sau đổi tên hoặc bỏ cờ thì role lặng lẽ không được gán (U3). Phải có test đọc lại role. | Thấp: 1 dòng trong tool, 1 ngoại lệ ADR, 1 test. |
| **C. Role riêng cho quyền cấu hình** (ví dụ "ERP AI Configurator") giữ các Custom DocPerm của A. Installer gán role này cho tài khoản agent. | System Manager rút toàn bộ quyền cấu hình bằng cách bỏ một role, không cần gỡ app. Tách rõ quyền đọc phiếu (ADR-006) với quyền cấu hình. | Đổi tập role mong đợi của ADR-006 và `_agent_role_drift` (`erp_ai/tasks.py:74-81`). Thêm một role cần vào danh sách cấm cứng. | Như A. Nếu người bỏ role mà không hạ mức thì tool trả `ok=false` hàng loạt; đúng thiết kế nhưng dễ bị tưởng là lỗi (ADR-005 Hệ quả). | Trung bình: role mới, đổi cảnh báo, đổi test ADR-006. |
| **D. Không cấp quyền Frappe; tool ghi bằng `ignore_permissions`.** | Không đổi quyền nào trên site. | Vi phạm thẳng Ràng buộc ADR-005. Mất hẳn lớp thứ hai cả ở Holiday List, Notification, Assignment Rule, nơi quyền Frappe còn có ý nghĩa. | Cao. | Thấp về mã, cao về rủi ro. |

**Phụ: System Settings (C8)**

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| S1. Cấp `write` System Settings cho role agent; tool giữ allowlist trường | Làm được AC-12 | Tầng Frappe mở cả mật khẩu, 2FA, phiên, scheduler | Lỗi allowlist thành hạ bảo mật toàn site | Thấp |
| S2. Bỏ AC-12 khỏi đợt 1 (đứng đầu "thứ tự bỏ trước" của spec `:124`) | Không mở quyền nguy hiểm | Thiếu một phần mục tiêu "cài đặt hệ thống" | Thấp | Không |

## Khuyến nghị
Chờ architect quyết.
- **Đề xuất A** (Custom DocPerm cho `ERP AI Agent`, cài qua installer) kèm năm điều kiện bắt buộc sau. Lý do: A đúng Ràng buộc ADR-005 mà không cần ngoại lệ, và có sẵn tiền lệ trong repo. Quyền thừa ở level 1 của User không mở thêm đường nào, vì không tool nào ghi các trường đó. B chỉ đáng chọn nếu architect muốn quyền ở tầng Frappe hẹp hơn và chấp nhận một ngoại lệ ADR-005.
  1. Sau mỗi lần lưu User, tool đọc lại `roles` từ DB và trả `ok=false` nếu thiếu role (U3: Frappe bỏ role không báo lỗi).
  2. Tool từ chối khi đầu vào có `role_profile_name`, `module_profile`, `user_type` hay bất kỳ trường permlevel 1 nào ngoài `roles` (U2, U6).
  3. Tool không dùng `make_property_setter` (C2). Tool tạo `Property Setter`/`Custom Field` bằng `frappe.get_doc(...).insert()`.
  4. Tool Notification ép `channel ∈ {Email, System Notification}`, `set_property_after_alert` rỗng, `is_standard = 0`, và mọi `cc`/`bcc` phải là email của User có trên hệ thống (C5).
  5. Tool Assignment Rule chỉ nhận người được giao đã có quyền `read` trên DocType đích (C7).
- **System Settings: đề xuất S2.** Quyền Frappe không chia nhỏ được (C8), và spec đã xếp AC-12 bỏ trước.
- **M1 (Workflow): architect chọn A hay B.** Researcher nghiêng về B, tức chỉ cho tạo Workflow khi DocType đích đã có trường trạng thái, hoặc bắt "ok" từ lúc tạo. Lý do: tác dụng phụ ở C4 không hoàn tác được bằng tay nếu không có Administrator.
- **Cho designer và qa:**
  - Custom Field và Workflow gây DDL commit (C1), nên test không dựa vào rollback của test runner và phải tự dọn trong `tearDown`.
  - Nhật ký ERP AI Log phải ghi sau DDL, kèm bước bù trừ (STD-ERR-7).

## POC (nếu có)
Không làm POC. Câu hỏi then chốt (permlevel 1 bỏ role mà không báo lỗi; cờ `ignore_permlevel_for_fields`) đã có test của chính Frappe chứng minh (`test_user.py:237-269`, [S3]). POC trên site dev `miyano` sẽ phải ghi Custom DocPerm thật vào DB dùng chung. Không tạo worktree.

## Nháp ADR (không đánh số — architect đánh số)
- **Bối cảnh:** FEAT-005 cho bot tạo User, gán role nghiệp vụ và ghi 8 DocType cấu hình, dưới tài khoản không có System Manager (ADR-006). Trên Frappe 15.126.1:
  - Ghi `roles` cần quyền level 1 trên User, và Frappe không chặn việc gán role quản trị (U1–U5).
  - Quyền ghi Custom Field, Property Setter, System Settings tương đương quyền sửa phân quyền hoặc cấu hình bảo mật (C1, C2, C8).
  - Workflow, Notification, Assignment Rule có tác dụng phụ vòng qua phân quyền (C4, C5, C7).
- **Phương án:** A, B, C, D ở bảng trên. S1/S2 cho System Settings. M1-A/M1-B cho Workflow.
- **Khuyến nghị:** A + năm điều kiện của tool + S2 + M1-B (chờ architect quyết).
- **Hệ quả:**
  - Tốt: không có cờ bỏ quyền trong tool; quyền nhìn thấy và cài lại được.
  - Xấu: tool là chốt duy nhất cho role và cho các DocType ở C1, C2. Các DocType có Custom DocPerm không còn nhận DocPerm chuẩn của bản Frappe sau (U10).
  - Hoàn tác: hạ về `L1` thì không tool nào dùng quyền này. Gỡ hẳn là xóa các dòng Custom DocPerm của role agent; với DocType mà app tạo bản sao Custom DocPerm thì "Reset to defaults" trong Role Permission Manager.
  - Phải sửa ADR-005 (Quyết định 6 và câu "lớp thứ hai"), ADR-006 (quyền cài sẵn) và test tĩnh liên quan.

## Sources
- [S1] https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/user/user.json — permissions và trường `roles` permlevel 1 (truy cập 2026-11-12)
- [S2] https://raw.githubusercontent.com/frappe/frappe/v15.126.1/frappe/model/document.py — `validate_higher_perm_levels`, `reset_values_if_no_permlevel_access`, `ignore_permlevel_for_fields` (truy cập 2026-11-12)
- [S3] https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/user/test_user.py — `test_high_permlevel_validations` (truy cập 2026-11-12)
- [S4] https://raw.githubusercontent.com/frappe/frappe/v15.126.1/frappe/core/doctype/user/user.py — `validate`, `has_permission`, `throttle_user_creation`; không có kiểm role khi gán (truy cập 2026-11-12)
- [S5] Mã cục bộ `apps/frappe/frappe/model/meta.py:553-566`, `apps/frappe/frappe/permissions.py:660-712` (frappe 15.126.1); bản tương ứng ở https://github.com/frappe/frappe/blob/v15.126.1/frappe/permissions.py (truy cập 2026-11-12)
- [S6] https://github.com/frappe/frappe/blob/v15.126.1/frappe/custom/doctype/custom_field/custom_field.py — `on_update` → `updatedb`, kiểm trùng tên trường (truy cập 2026-11-12)
- [S7] https://github.com/frappe/frappe/blob/v15.126.1/frappe/database/database.py — `sql_ddl` commit trước DDL (truy cập 2026-11-12)
- [S8] https://github.com/frappe/frappe/blob/v15.126.1/frappe/custom/doctype/property_setter/property_setter.py — `make_property_setter` "WARNING: Ignores Permissions" (truy cập 2026-11-12)
- [S9] https://github.com/frappe/erpnext/blob/v15.83.0/erpnext/setup/doctype/holiday_list/holiday_list.json — chỉ HR Manager (truy cập 2026-11-12)
- [S10] https://github.com/frappe/frappe/blob/v15.126.1/frappe/workflow/doctype/workflow/workflow.py — `on_update` chạy không phụ thuộc `is_active` (truy cập 2026-11-12)
- [S11] https://docs.frappe.io/erpnext/user/manual/en/workflows — "Is Active", trường trạng thái tự tạo (truy cập 2026-11-12)
- [S12] https://github.com/frappe/frappe/blob/v15.126.1/frappe/email/doctype/notification/notification.py — `FORBIDDEN_DOCUMENT_TYPES`, `on_update` ghi file, `set_property_after_alert` + `ignore_permissions` (truy cập 2026-11-12)
- [S13] https://docs.frappe.io/erpnext/user/manual/en/notifications — Set Property After Alert, kênh Email/Slack/System Notification/SMS (truy cập 2026-11-12)
- [S14] https://github.com/frappe/frappe/blob/v15.126.1/frappe/desk/form/assign_to.py — chia sẻ chứng từ khi người được giao thiếu quyền (truy cập 2026-11-12)
- [S15] https://docs.frappe.io/erpnext/user/manual/en/assignment-rule — điều kiện Python, Round Robin/Load Balancing/Based on Field (truy cập 2026-11-12)
- [S16] https://github.com/frappe/frappe/blob/v15.126.1/frappe/core/doctype/system_settings/system_settings.json — không trường nào permlevel > 0 (truy cập 2026-11-12)
- [S17] https://docs.frappe.io/erpnext/user/manual/en/role-based-permissions — "Permission 'Level' connects fields with level X to a permission rule with level X" (truy cập 2026-11-12)
- [S18] https://docs.frappe.io/framework/user/en/basics/users-and-permissions — Permission Level, "The default set of permissions show up here and can be overridden" (truy cập 2026-11-12)
