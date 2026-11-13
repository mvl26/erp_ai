# FEAT-006 — Research R2: dữ liệu site `miyano`

- Người làm: researcher (R2), ngày 2026-11-12.
- Câu hỏi: spec A-9, A-10, AC-6, AC-10, AC-11. Site đang có gì về SLA, Team, Agent, Custom Field, role và `category_mapping`?
- Cách đọc dự kiến: file test POC chỉ-đọc trong worktree `.claude/worktrees/poc-feat006-site`, chạy bằng `cmd.test_one`, không ghi DB.
- Trạng thái: **BLOCKED một phần.** Không đọc được DB vì hook chặn `cmd.test_one` (xem mục dưới). Phần suy được từ mã nguồn và tài liệu đã có ghi ở mục 1–6. Phần cần DB ghi `UNVERIFIED`. File POC sẵn chạy nằm ở Phụ lục A.

## Chặn chính (BLOCKER): researcher không chạy được `cmd.test_one`

- Lệnh thật đã chạy (cwd `apps/erp_ai`):
  `cd ../.. && PYTHONPATH=<worktree>/docs/team/poc bench --site miyano run-tests --module "$(echo poc_feat006_site/test_poc_site.py | sed 's#/#.#g; s#\.py$##')" --skip-before-tests --skip-test-records`
- Kết quả thật: `BLOCKED (role-policy): team:researcher may only run read-only commands or git worktree *, cmd.*; got 'bench --site miyano run-tests --module $(echo poc_feat006_site/test_poc_site.py | sed ...'`. Lệnh không chạy, DB không bị chạm.
- Nguyên nhân (đọc mã hook, kit team 0.4.0):
  - `scripts/teamlib.py:584-590` lấy tiền tố của mỗi slot `cmd.*` là phần trước `{file}`. Với `cmd.test_one`, tiền tố là `cd ../.. && bench --site miyano run-tests --module "$(echo`.
  - `teamlib.py:645` tách lệnh tại `&&`, rồi `:662` so TỪNG đoạn với tiền tố đó.
  - Đoạn `bench --site …` không bao giờ bắt đầu bằng `cd ../.. && …`. Vì vậy mọi slot `cmd.*` có `cd ../.. &&` (install, build, test, test_one, run, migrate) đều bị chặn với researcher.
  - Lỗi nằm ở kit, không ở lệnh. Researcher không vượt hook.
- Cách gỡ (team-leader chọn):
  - (a) Team-leader hoặc qa chạy file POC ở Phụ lục A (chỉ đọc, `rollback` ở cuối), rồi dán đầu ra vào mục 1–6. Agent-memory của qa cho thấy qa đã từng chạy truy vấn chỉ-đọc trên `miyano`.
  - (b) Sửa kit: so tiền tố với cả chuỗi lệnh, hoặc bỏ `cd ../.. &&` khỏi phần đem so.
  - (c) Ghi `/team:feedback` cho role-policy.
- Bắt buộc có `--skip-before-tests`. Không có cờ này, `run-tests --module` chạy hook `before_tests` của mọi app (`frappe/test_runner.py:83`). Hook của erpnext ghi DB, trái yêu cầu "không ghi gì vào DB". `--skip-test-records` chặn `make_test_records(..., commit=True)` (`test_runner.py:232`).
- Không dùng được bản sao lưu: bản duy nhất `sites/miyano/private/backups/20261015_164912-miyano-database.sql.gz` (2026-10-15) đã cũ, có trước FEAT-001. Bản này lại nén gzip, mà các lệnh chỉ-đọc được phép không giải nén được.

## Version in use

- frappe `15.126.1` (`apps/frappe/frappe/__init__.py:54`); helpdesk `15.1.0` (`apps/helpdesk/helpdesk/__init__.py:1`); erpnext có cài.
- App trên site (`sites/apps.txt`): frappe, telephony, antmed_crm, mvl_accounting, normcore_dmktkt, workflowcore, erpnext, erp_ai, assetcore, norm_himedic, helpdesk, hrms.

## 1. SLA / Priority (A-10, AC-10, AC-11)

| Sự thật | Nguồn | Mức |
|---|---|---|
| Lúc cài, helpdesk tạo SLA `Standard` (`DEFAULT_SLA`) với `default_sla=1`, `enabled=1`, `document_type=HD Ticket`, không có `condition` | `helpdesk/setup/install.py:66-` (`add_default_sla`), `helpdesk/consts.py:4` | mã, chắc |
| SLA `Standard` có 4 Priority (response / resolution): Low 24h / 72h; **Medium (default_priority=1)** 8h / 24h; High 1h / 4h; Urgent 30 phút / 2h. Giờ làm việc 10:00–18:00 | `install.py:76-131` | mã, chắc |
| `HD Ticket Priority` mặc định: Urgent, High, Medium, Low (`level` = tên) | `install.py:154-164` | mã, chắc |
| DocType SLA có các trường `default_sla`, `rank`, `default_priority`, `enabled`, `condition`, `condition_json` | `hd_service_level_agreement.json` | mã, chắc |
| Trên site có 2 SLA, cả hai đang bật: `Standard` và `SLA Priority` (xem đầu ra dưới) | DB `miyano`, đọc 2026-11-12 | DB, chắc |

Đọc DB (qa thay researcher, 2026-11-12, chỉ `SELECT`). Mọi lệnh chạy từ `/home/miyano/frappe-bench`, viết tắt `M` = `bench --site miyano mariadb -e`.

- Lệnh: `M "SELECT name, enabled, default_sla, rank, default_priority, condition, condition_json, apply_sla_for_resolution, holiday_list, modified FROM tabHD Service Level Agreement; SELECT parent, priority, default_priority, response_time, resolution_time FROM tabHD Service Level Priority ORDER BY parent, idx; SELECT name, level, disabled FROM tabHD Ticket Priority; SELECT parent, workday, start_time, end_time FROM tabHD Service Day …"` → exit 0. Đầu ra rút gọn:

  ```text
  name          enabled default_sla rank default_priority condition                                  holiday_list
  SLA Priority  1       0           0    Medium           doc.priority in ['High', 'Urgent', 'Low']  Test Holiday List
  Standard      1       1           0    Medium           NULL                                       Default
  Priority (cả 2 SLA giống nhau, giây): Low 86400/259200; Medium(default) 28800/86400; High 3600/14400; Urgent 1800/7200
  HD Ticket Priority: High, Low, Medium, Urgent (disabled=0 cả 4)
  Service Day (cả 2 SLA): Monday..Friday 10:00–18:00
  ```

- Lệnh: `M "SELECT name, owner, creation FROM tabHD Service Level Agreement; SELECT sla, COUNT(*) FROM tabHD Ticket GROUP BY sla; SELECT priority, COUNT(*) FROM tabHD Ticket GROUP BY priority"` và `M "SELECT name, creation FROM tabHD Service Holiday List"` → exit 0:

  ```text
  SLA Priority  Administrator  2026-11-11 11:42:43   |  Standard  Administrator  2026-11-11 10:27:48
  HD Ticket: 6 phiếu, sla=Standard 6, priority=Medium 6
  HD Service Holiday List: _Test Holiday List (2026-11-11 13:17), Default (10:27), Test Holiday List (11:42)
  ```

- `SLA Priority` và `Test Holiday List` là tên cố định trong `helpdesk/helpdesk/test_utils.py:36-37` (`SLA_PRIORITY_NAME`, `TEST_HOLIDAY_LIST_NAME`). Đây là rác test của helpdesk còn lại trên site, không phải SLA người cấu hình.
- **Kết luận A-10:** đúng về thực chất. SLA người dùng thật chỉ có `Standard` (mặc định, không `condition`). Nhưng còn SLA rác `SLA Priority` đang bật, có `condition` bắt priority High/Urgent/Low. Phiếu mà bot đặt High (mục A) hoặc Low (mục F) có thể nhận SLA rác này cùng lịch nghỉ `Test Holiday List`, chứ không nhận `Standard`. Test AC-11 phải tắt cả 2 SLA. Team-leader nên báo người dọn (tắt/xóa) `SLA Priority` trên site; qa không ghi DB.

## 2. HD Team / Assignment Rule (AC-6)

- Theo schema, `HD Team` có `assignment_rule` (Link → Assignment Rule) và `users` (Table → `HD Team Member`, chỉ một trường `user`) (`helpdesk/helpdesk/doctype/hd_team/hd_team.json:11-35`, `hd_team_member.json`).
- `ERP AI Setting.excluded_teams` mặc định là "Nhân sự & Hành chính\nTài chính Kế toán", nên site rất có thể có hai team tên này (`erp_ai_setting.json`). DB: có `Nhân sự & Hành chính`, **không có** `Tài chính Kế toán`. Giá trị đang lưu của `excluded_teams` là rỗng (mục 6).
- Lệnh: `M "SELECT name, assignment_rule, disabled, creation FROM tabHD Team; SELECT parent, user FROM tabHD Team Member WHERE parenttype='HD Team'"` → exit 0:

  ```text
  team                  assignment_rule                          disabled  creation
  Billing               Billing - Support Rotation               0         2026-11-11 10:27
  IT                    IT - Support Rotation                    0         2026-11-11 15:26
  Nhân sự & Hành chính  Nhân sự & Hành chính - Support Rotation  0         2026-11-11 15:26
  Product Experts       Product Experts - Support Rotation       0         2026-11-11 10:27
  HD Team Member: IT → Administrator; Nhân sự & Hành chính → Administrator (chỉ 2 dòng)
  ```

- Lệnh: `M "SELECT name, disabled, rule, document_type, priority, assign_condition, unassign_condition FROM tabAssignment Rule; SELECT parent, user FROM tabAssignment Rule User"` và `M "SELECT t.name, t.assignment_rule, (r.name IS NOT NULL) rule_exists FROM tabHD Team t LEFT JOIN tabAssignment Rule r ON r.name=t.assignment_rule; SELECT COUNT(*) FROM tabAssignment Rule User"` → exit 0:

  ```text
  Assignment Rule (tổng 3):
  Billing - Support Rotation          disabled=0 Round Robin HD Ticket prio=1 "status == 'Open' and agent_group == 'Billing'"
  Product Experts - Support Rotation  disabled=0 Round Robin HD Ticket prio=1 "status == 'Open' and agent_group == 'Product Experts'"
  Support Rotation                    disabled=1 Round Robin HD Ticket prio=0 "status == 'Open'"
  rule_exists: Billing 1, IT 0, Nhân sự & Hành chính 0, Product Experts 1
  Assignment Rule User: 0 dòng
  ```

- Không có team `Tài chính Kế toán`.
- Team `IT` và `Nhân sự & Hành chính` trỏ tới Assignment Rule **không tồn tại** (link treo). `HDTeam.on_update` gọi `frappe.get_doc("Assignment Rule", self.assignment_rule)` (`helpdesk/.../hd_team/hd_team.py:27-33`), nên lưu hai team này sẽ lỗi `DoesNotExistError`. Không rule nào có người (`Assignment Rule User` = 0). Vì vậy Helpdesk không tự chia phiếu `agent_group=IT` cho ai.
- **Kết luận AC-6:** trên site, round-robin của Helpdesk không giành việc của bot (rule IT không có, các rule khác không có người). Nhưng team IT đang hỏng link rule. Test AC-6 phải tự tạo team/agent riêng, không dùng team `IT` của site. Muốn bot chạy trên site thì người phải sửa rule của `IT` (tạo lại hoặc xóa link).

## 3. HD Agent đang hoạt động (AC-6)

- HD Agent có các trường `user`, `agent_name`, `is_active`, `availability` (`hd_agent.json`).
- Bot cài vai Helpdesk `Agent` cho tài khoản agent (`erp_ai/install.py:69`: `wanted = (ROLE_AGENT, HELPDESK_AGENT_ROLE)`).
- Lệnh: `M "SELECT a.name, a.user, a.agent_name, a.is_active, u.enabled FROM tabHD Agent a LEFT JOIN tabUser u ON u.name=a.user"` → exit 0, **không có dòng nào**. Lệnh `M "SELECT COUNT(*) hd_agents FROM tabHD Agent"` → `hd_agents 0`.
- Lệnh: `M "SELECT hr.parent, u.enabled FROM tabHas Role hr JOIN tabUser u ON u.name=hr.parent WHERE hr.parenttype='User' AND hr.role='Agent'"` → exit 0: 2 user có role `Agent`, cả hai `enabled=1`: `ai.agent@miyano.com.vn` và 1 tài khoản cá nhân (gmail, không ghi địa chỉ ở đây theo STD-SEC-6). Cả hai đều không có bản ghi HD Agent.
- `M "SELECT field, value FROM tabSingles WHERE doctype='HD Settings' AND field IN (…)"` → `restrict_tickets_by_agent_group=0`, `do_not_restrict_tickets_without_an_agent_group=0`, `default_priority`/`default_ticket_type` NULL.
- **Kết luận AC-6:** site có **0 HD Agent**. Trên site hiện tại, mọi người cấu hình trong bảng người mặc định đều rơi vào nhánh "không phải HD Agent đang hoạt động → không gán, ghi nhật ký". Test AC-6 phải tự tạo HD Agent `is_active=1`. Muốn gán thật trên site thì người phải tạo HD Agent trước.

## 4. Custom Field trên HD Ticket (A-9)

- Custom Field do `erp_ai` tạo (`erp_ai/install.py:114-153`):

  | fieldname | label | fieldtype |
  |---|---|---|
  | `AI_SECTION_FIELD` | ERP AI | Section Break |
  | `ai_resolution_hint` | Hướng giải quyết (AI) | Text Editor |
  | `ai_confidence` | Độ tin cậy (AI) | Select |
  | `ai_classified_by` | Phân loại bởi | Select |
  | `ai_updated_at` | AI cập nhật lúc | Datetime |
  | `OPT_OUT_FIELD` | Không dùng AI cho phiếu này | Check |

- Trong mã của mọi app trên bench (`grep` `Hạn hoàn thành|Nguồn phát sinh|han_hoan_thanh|nguon_phat_sinh`) không có Custom Field nào gắn vào HD Ticket. Không app nào có file JSON với `"dt": "HD Ticket"`.
  - "Hạn hoàn thành" chỉ là label của DocType **`WFC Task`** trong workflowcore (`workflowcore/.../wfc_task/wfc_task.json:157`). Đây không phải HD Ticket.
  - "Nguồn phát sinh" chỉ xuất hiện trong prompt (`erp_ai/agent/prompts.py:142-150`) và tài liệu triển khai.
- Kết luận: không app nào tạo hai trường này bằng mã. Người vẫn có thể đã thêm chúng bằng Customize Form trên site. DB bên dưới cho thấy không có.
- Lệnh: `M "SELECT fieldname, label, fieldtype, options, module, insert_after FROM tabCustom Field WHERE dt='HD Ticket' ORDER BY idx"` → exit 0, 6 dòng, đều `module=ERP AI agent`:

  ```text
  ai_section          ERP AI                        Section Break  (insert_after resolution_failed_by)
  ai_resolution_hint  Hướng giải quyết (AI)          Text Editor
  ai_confidence       Độ tin cậy (AI)                Select  \nCao\nTrung bình\nThấp
  ai_classified_by    Phân loại bởi                  Select  \nAI\nNgười
  ai_updated_at       AI cập nhật lúc                Datetime
  ai_opt_out          Không dùng AI cho phiếu này    Check
  ```

- Lệnh: `M "SELECT fieldname, label FROM tabCustom Field WHERE dt='HD Ticket' AND (label LIKE BINARY '%Hạn%' OR … '%Nguồn%' …)"` → exit 0, 0 dòng. Bản không-BINARY (`LIKE '%hạn%' OR LIKE '%nguồn%'`) trả 1 dòng `ai_classified_by | Phân loại bởi`. Đây là khớp sai, do collation bỏ dấu.
- Lệnh: `M "SHOW COLUMNS FROM tabHD Ticket"` → không có cột nào về hạn/nguồn ngoài cột SLA (`response_by`, `resolution_by`, …) và 5 cột `ai_*`. `M "SELECT COUNT(*) FROM tabProperty Setter WHERE doc_type='HD Ticket'"` → `0`. `HD Ticket Template Field` (template `Default`): chỉ 5 trường `ai_*`.
- **Kết luận A-9:** đã xác minh. Trên site không có trường "Hạn hoàn thành" hay "Nguồn phát sinh" ở HD Ticket. Theo nhánh "model đọc hạn từ nội dung phiếu".

## 5. Role của tài khoản agent; DocType Task (Q-A2)

- Tài khoản agent là hằng `AGENT_USER = "ai.agent@miyano.com.vn"` (`erp_ai/constants.py:1`). `ERP AI Setting` **không có** trường user; bảng `credentials` (ERP AI Credential) chỉ chứa khóa API, model, hạn mức (`erp_ai_credential.json`).
- Lúc cài, bot cần 2 role: `ERP AI Agent` và `Agent` (`install.py:69-83`).
- Dữ liệu sống gần nhất đã ghi: tài khoản agent có **99 role, trong đó có `System Manager`**. 97 role được thêm bằng một lần lưu User lúc 11:21 ngày 2026-11-12 trong phiên quản trị của người (`docs/team/features/BUG-002/intake.md:26`, `asbuilt.md:28`). Hiện trạng ngày 2026-11-12: vẫn 99 role (đầu ra dưới).
- DocType `Task` có trong mã: erpnext, module `Projects` (`erpnext/projects/doctype/task/task.json`). erpnext có trong `apps.txt`, nên DocType này gần như chắc chắn tồn tại trên site. Quyền chuẩn chỉ có role **`Projects User`** với read/write/create. Custom DocPerm trên site có thêm `ERP AI Agent` (đầu ra dưới).
  - Hệ quả (suy từ mã, **bị DB bác bỏ một phần**, xem dưới): tài khoản agent chỉ có 2 role cài sẵn thì KHÔNG tạo được Task. Nó chỉ tạo được nhờ 97 role thừa (đang bị coi là lỗi, BUG-002). Thiết kế đừng dựa vào số role thừa đó.
- Lệnh: `M "SELECT COUNT(*) n_roles, SUM(role='System Manager'), SUM(role='ERP AI Agent'), SUM(role='Agent'), SUM(role='Projects User'), SUM(role='Agent Manager') FROM tabHas Role WHERE parenttype='User' AND parent='ai.agent@miyano.com.vn'; SELECT MAX(modified) …; SELECT name, module FROM tabDocType WHERE name IN ('Task','ToDo','HD Ticket')"` → exit 0:

  ```text
  n_roles 99 | System Manager 1 | ERP AI Agent 1 | Agent 1 | Projects User 1 | Agent Manager 1
  last_role_change 2026-11-12 11:21:12   (vẫn là lần lưu của BUG-002; user enabled=1, System User)
  DocType: HD Ticket/Helpdesk, Task/Projects, ToDo/Desk
  ```

- Lệnh: `M "SELECT 'standard', parent, role, permlevel, read, write, create, delete, if_owner FROM tabDocPerm WHERE parent IN ('Task','ToDo','HD Ticket') UNION ALL SELECT 'custom', … FROM tabCustom DocPerm …"` và `M "SELECT parent, role, owner, creation FROM tabCustom DocPerm WHERE parent='Task'"` → exit 0. Rút gọn (r/w/c/d, if_owner):

  ```text
  Task  standard: Projects User 1/1/1/1
  Task  custom  : Projects User 1/1/1/1; Employee Self Service 0/0/0/0;
                  ERP AI Agent 1/1/1/0 if_owner=1 (Administrator, 2026-11-11 13:55:48)
  ToDo  standard: All 1/1/1/1; System Manager 1/1/1/0
  ToDo  custom  : All 1/1/1/1; System Manager 1/1/1/0; + 27 role AssetCore/khác 1/1/1/1
  HD Ticket standard = custom (bản sao): Agent lv0 1/1/1/0, lv7 1/1/0/0, lv8 1/1/0/0;
                  Agent Manager lv0 1/1/1/1; System Manager lv0 1/1/1/1; HD Customer(+Manager) lv0 1/1/1/0
  ```

- Dòng Custom DocPerm `Task / ERP AI Agent` do `erp_ai/install.py:184-205` (`_ensure_task_permission`) tạo: gọi `setup_custom_perms("Task")` rồi thêm read/write/create, `if_owner=1`. Vì Task đã có Custom DocPerm, Frappe dùng bộ custom thay bộ chuẩn.
- **Kết luận (Q-A2, AC-6):** role cài sẵn `ERP AI Agent` đã đủ để tài khoản agent tạo Task, không cần `Projects User` hay 97 role thừa. Nhận định "chỉ `Projects User` mới tạo được" ở trên là sai trên site này. Giới hạn: `if_owner=1` nên agent chỉ đọc/sửa Task do chính nó tạo. Người được giao muốn thấy Task thì cần role `Projects User` hoặc được share/assign. ToDo thì role `All` tạo được. HD Ticket thì role `Agent` đọc/ghi được ở level 0/7/8.

## 6. ERP AI Setting.category_mapping

- Giá trị **mặc định** trong DocType (`erp_ai_setting.json`, trường `category_mapping`, kiểu Code/JSON):

  | Mục | ticket_type | agent_group | priority |
  |---|---|---|---|
  | A | Sự cố & lỗi hệ thống | IT | High |
  | B | Quản trị & cấu hình hệ thống | IT | Medium |
  | C | Phát triển tính năng & tự động hóa | IT | Medium |
  | D | Chuẩn hóa dữ liệu & quy trình trên ERP | "" | Medium |
  | E | Công việc nghiệp vụ ngoài IT | "" | "" |
  | F | Câu hỏi, phiếu nhiễu | IT | Low |

- Lệnh: `M "SELECT field, LEFT(value,120), CHAR_LENGTH(value) FROM tabSingles WHERE doctype='ERP AI Setting' AND field IN ('enabled','permission_level','excluded_teams','category_mapping','modified')"` và `M "SELECT value FROM tabSingles WHERE doctype='ERP AI Setting' AND field='category_mapping'\G; SELECT name FROM tabHD Ticket Type"` → exit 0. Không đọc bảng `ERP AI Credential`.

  ```text
  enabled 1 | permission_level L3 | excluded_teams "" (độ dài 0) | modified 2026-11-12 13:54:34
  category_mapping (567 ký tự):
   A Sự cố & lỗi hệ thống / IT / High        B Quản trị & cấu hình hệ thống / IT / Medium
   C Phát triển tính năng & tự động hóa / IT / Medium
   D Chuẩn hóa dữ liệu & quy trình trên ERP / "" / Medium
   E Công việc nghiệp vụ ngoài IT / "" / ""   F Câu hỏi, phiếu nhiễu / IT / Low
  HD Ticket Type: Unspecified, Question, Bug, Incident + đủ 6 ticket_type A–F ở trên
  ```

- **Kết luận:** `category_mapping` trên site trùng hoàn toàn giá trị mặc định. Đủ 6 ticket_type đều có trong `HD Ticket Type`, và team `IT` có thật (nhưng hỏng link rule, xem mục 2). Hai điểm khác mặc định: `excluded_teams` đang **rỗng** (mặc định là 2 team), và `permission_level = L3`, nên trên site mọi điều kiện "`L1`+" của AC-6 đều thỏa.

## Hệ quả cho spec (khuyến nghị, architect/designer quyết)

- A-10: nếu chưa ai cấu hình SLA, site chỉ có `Standard` (mặc định, không `condition`). Các priority Low/Medium/High/Urgent khớp với giá trị priority trong `category_mapping`, nên AC-11 ("thiếu SLA") chỉ xảy ra khi `Standard` bị tắt. Test AC-10 phải tự tạo SLA thứ hai, đúng như spec đã ghi.
- A-9: mã không có trường "Hạn hoàn thành"/"Nguồn phát sinh" trên HD Ticket. Chọn nhánh "model đọc hạn từ nội dung phiếu" cho tới khi POC test_4 nói khác.
- Task (Q-A2): cần role `Projects User`, mà role này không có trong 2 role cài sẵn. Phương án: (A) thêm `Projects User` vào role cài sẵn; (B) dùng ToDo/assign của Helpdesk thay cho Task. R1 (research.md) quyết về quyền theo mã nguồn.

## Phụ lục A — file POC chỉ-đọc (để team-leader/qa chạy)

Đặt file tại `<thư mục X>/poc_feat006_site/test_poc_site.py`, ngoài cây chính. Từ `apps/erp_ai` chạy:
`cd ../.. && PYTHONPATH=<thư mục X> bench --site miyano run-tests --module poc_feat006_site.test_poc_site --skip-before-tests --skip-test-records`

```python
import json, re, unittest
import frappe
from erp_ai.constants import AGENT_USER

PERM_FIELDS = ["role", "permlevel", "read", "write", "create"]

def out(tag, data):
	print(f"\n=== {tag} ===\n" + json.dumps(data, ensure_ascii=False, default=str, indent=1))

class TestPocSiteRead(unittest.TestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()

	def test_1_sla(self):
		keys = ("name", "enabled", "default_sla", "condition", "condition_json", "rank", "default_priority")
		for s in frappe.get_all("HD Service Level Agreement", fields=["*"]):
			out(f"SLA {s.name}", {k: s.get(k) for k in keys if k in s})
		out("SLA priorities", frappe.get_all("HD Service Level Priority",
			fields=["parent", "priority", "default_priority", "response_time", "resolution_time"]))
		out("HD Ticket Priority", frappe.get_all("HD Ticket Priority", fields=["*"]))

	def test_2_team(self):
		for t in frappe.get_all("HD Team", fields=["*"]):
			rule = None
			if t.get("assignment_rule"):
				rule = frappe.db.get_value("Assignment Rule", t.assignment_rule,
					["name", "disabled", "rule", "document_type", "priority", "assign_condition"], as_dict=True)
				if rule:
					rule["users"] = frappe.get_all("Assignment Rule User", filters={"parent": t.assignment_rule}, pluck="user")
			out(f"HD Team {t.name}", {"team": dict(t), "rule": rule})
		out("HD Team Member", frappe.get_all("HD Team Member", filters={"parenttype": "HD Team"}, fields=["parent", "user"]))

	def test_3_agents(self):
		out("HD Agent", frappe.get_all("HD Agent", fields=["name", "user", "agent_name", "is_active"]))

	def test_4_ticket_custom_fields(self):
		out("Custom Field HD Ticket", frappe.get_all("Custom Field", filters={"dt": "HD Ticket"},
			fields=["fieldname", "label", "fieldtype", "options", "module"]))

	def test_5_roles_task(self):
		out(f"roles of {AGENT_USER}", {"roles": sorted(frappe.get_roles(AGENT_USER)),
			"hd_agent": frappe.db.get_value("HD Agent", {"user": AGENT_USER}, ["name", "is_active"], as_dict=True)})
		out("DocType Task", frappe.db.get_value("DocType", "Task", ["name", "module"], as_dict=True))
		for dt in ("Task", "ToDo", "HD Ticket"):
			out(f"{dt} perms", {"custom": frappe.get_all("Custom DocPerm", filters={"parent": dt}, fields=PERM_FIELDS),
				"standard": frappe.get_all("DocPerm", filters={"parent": dt}, fields=PERM_FIELDS)})

	def test_6_category_mapping(self):
		s = frappe.get_single("ERP AI Setting")
		out("ERP AI Setting", {"enabled": s.enabled, "permission_level": s.permission_level,
			"excluded_teams": s.excluded_teams, "category_mapping": s.category_mapping})
```

## Sources

Mã nguồn đã cài trên bench, đọc ngày 2026-11-12 (official source của đúng phiên bản đang dùng):

- helpdesk 15.1.0: `apps/helpdesk/helpdesk/setup/install.py:66-164`; `apps/helpdesk/helpdesk/consts.py:4`; `apps/helpdesk/helpdesk/helpdesk/doctype/{hd_team,hd_team_member,hd_agent,hd_service_level_agreement}/*.json`. Bản GitHub cùng tag: https://github.com/frappe/helpdesk/blob/v15.1.0/helpdesk/setup/install.py (truy cập 2026-11-12, chưa đối chiếu nội dung trên web nên dùng bản đã cài làm chuẩn).
- frappe 15.126.1: `apps/frappe/frappe/test_runner.py:83,226-249`; `apps/frappe/frappe/commands/utils.py:773`. Bản GitHub: https://github.com/frappe/frappe/blob/v15.126.1/frappe/test_runner.py (truy cập 2026-11-12).
- erpnext: `apps/erpnext/erpnext/projects/doctype/task/task.json` (module Projects, quyền `Projects User`).
- erp_ai: `erp_ai/constants.py:1-4`, `erp_ai/install.py:61-153`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json`, `erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json`, `erp_ai/agent/prompts.py:142-150`.
- workflowcore: `workflowcore/workflowcore/workflowcore/doctype/wfc_task/wfc_task.json:157`.
- Dữ liệu site đã ghi trước đó: `docs/team/features/BUG-002/intake.md:26`, `docs/team/features/BUG-002/asbuilt.md:28`.
- Hook: `~/.claude/plugins/cache/automation-ai/team/0.4.0/scripts/teamlib.py:584-666`, `hooks/role-policy.json:132-148`.
