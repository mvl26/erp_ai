Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 15 — FEAT-007 T15

- Diff: `git diff a805842d416dd572403e7837d76ead11b8df24e3..dd35a0b` (nhánh `team/FEAT-007-task-15`, 1 commit `dd35a0b`, 4 file +212/−3)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline a805842d..team/FEAT-007-task-15`, `git diff --stat …`, `git diff …`; `git grep -n -e 'HD Ticket Comment' -e 'reference_ticket' team/FEAT-007-task-15 -- 'erp_ai/**' | grep -v -e '/test_' -e '/tests/'` → 0 dòng; `git grep -n '"HD Ticket"' … -- erp_ai/constants.py 'erp_ai/agent/*.py'`; `git grep -n -A12 'def denied_doctypes' … -- erp_ai/agent/tools/read.py`; `git grep -n escape_html …`; `git show` phần import của `erp_ai_setting.py` và đầu `policy.py`; `git log -1 --format='%an%n%B'`; `git -C ../helpdesk grep -n -B3 '"options": "HD Ticket"' -- hd_ticket.json hd_ticket_comment.json`.
- Bằng chứng của dev: RED sau migrate, chưa có mã controller: `test_erp_ai_setting` `Ran 68 tests … FAILED (failures=16)` (`AssertionError: None != "Báo cáo 'ERP AI Test BC tắt Script Report' đang tắt"`, `AssertionError: "Kho HDSD 'khong_co_thu_muc_nay' phải là thư mục có sẵn dưới apps/" != "Báo cáo 'ERP AI Test BC không có' không có"`); `test_policy` với `policy.py` của nền: `AssertionError: False is not true : policy has no ticket_link_fieldnames()`, `Ran 38 tests … FAILED (failures=1)`. GREEN một lần giữ khóa, migrate exit 0: `test_erp_ai_setting` `Ran 68 tests in 7.702s OK`; `test_policy` `Ran 38 tests in 3.761s OK`; `test_architecture` `Ran 112 tests in 5.680s OK`.
- Lớp 1 (khớp spec): AC-49, E-6 và phán quyết 2 đã làm đủ. Diff nằm trong touchpoints; phép kiểm chạy đúng thứ tự (bước 6 → 7 → 8); chữ lỗi khớp `design-w0-fixes.md:55` với phần thay của `design-w0-fixes-3.md:74-75`.

### Điều kiện của architect

| Điều kiện | Kết quả | Bằng chứng |
|---|---|---|
| C-T15-1 | đạt | `policy.py`: chỉ một khối mới ở cuối (dòng 148-174) và `TICKET_CONTENT_DOCTYPES` thêm vào import dòng 9; không hàm, hằng, import nào khác đổi; không import mới từ `erp_ai.agent.*` hay `erp_ai.erp_ai_agent.*`. `test_policy.py`: chỉ thêm lớp `TestTicketContentDoctype` và tên `keep_agent_settings` trong dòng import `test_utils` sẵn có (tech-lead đã nhận ở dòng "Bổ sung" của T15) |
| C-T15-2 | đạt | `_stored_doctype_name` chạy `frappe.db.get_value("DocType", doctype, "name")`; phép thuộc `TICKET_CONTENT_DOCTYPES` và `get_meta` đều dùng `name` đã lưu; DocType không có → `()` / `False`, không ném. Test: `"comment"` → True, `"Task"` → True, `ticket_link_fieldnames("Task") == ("ai_ticket",)`, thêm `"task"`, `"hd ticket"` (ca `"hd ticket"` → `()` sẽ đỏ nếu bỏ tra tên, vì `hd_ticket.json` tự Link tới mình qua `ticket_split_from`, `merged_with`) |
| C-T15-3 | đạt | chữ lỗi dùng biến `ref_doctype` (`erp_ai_setting.py:278`); hai chuỗi cấm xuất hiện 0 lần ngoài file test; `test_architecture` 112 OK |
| C-T15-4 | đạt | `depends: T8, T14`, `test:` có `test_policy.py`; ba lần `cmd.test_one` xanh trước merge (dev) và sau merge (tech-lead), đầu ra ở journal 2026-11-15 |
| C-T15-5 | đạt phần test | ca `Task` có trong `test_report_on_ticket_linked_doctype_blocked` (`test_erp_ai_setting.py:1669`). Dòng journal và câu hỏi không chặn cho analyst là việc của team-leader: tech-lead nhắc trong báo cáo lượt 7 |

### Phát hiện (chỉ blocker/major)

Không có blocker, không có major.

minor | — | — | 4 điểm nhỏ: (1) STD-DESIGN-4 `policy.py:150` thêm `TICKET_DOCTYPE = "HD Ticket"` trong khi `agent/kpi.py:17` đã có `TICKET = "HD Ticket"` và `constants.py` chưa có tên dùng chung; chuyển vào `constants.py` là ngoài touchpoints của task → ghi nợ; (2) STD-TEST-8 `test_policy.py:373-390`: không ca nào đỏ nếu bỏ phép `field.fieldtype == "Link"`, không ca nào có hai trường Link nên luật "theo thứ tự meta" chưa được kiểm (thực tế bỏ phép kiểm không đổi gì vì chỉ trường Link ghi "HD Ticket" ở `options`); (3) STD-DESIGN-5 `policy.py:170-174`: `is_ticket_content_doctype` tra tên đã lưu rồi `ticket_link_fieldnames(name)` tra lại, mỗi lời gọi hai truy vấn DocType; (4) STD-TEST-8 `test_erp_ai_setting.py:1625`: docstring nói báo cáo "đầu tiên trong danh sách" bị từ chối nhưng không test nào có hai dòng sai | tùy dev

### Review checklist (10)

1. đạt (bốn lý do E-6, hợp của DocType mang nội dung phiếu và DocType bị cấm, dòng trống bỏ qua, đứng trước `check_manuals_dir`, test thứ tự ở `:1640-1644`; escape tên người gõ nhất quán với E-1) 2. đạt (đúng 4 file touchpoints) 3. đạt (RED/GREEN có; phủ tên không có, HTML trong tên, hai kiểu sai, báo cáo tắt, 4 DocType của hằng, danh sách cấm, DocType có Link tới phiếu, giá trị trống; không skip/xfail) 4. đạt (không phép khẳng định cũ nào đổi; rollback, `keep_agent_settings`, tự tạo Report; phụ thuộc `Task.ai_ticket` đã cài nhưng `setUp` khẳng định trường đó có) 5. đạt 6. đạt (tên người gõ được escape, `:250`; `get_value` có tham số) 7. đạt (hàm mới, phép kiểm mới; không migration) 8. đạt 9. đạt 10. đạt (`feat(setting): … (FEAT-007)`, một commit, không trailer AI)

## Không kiểm được từ diff — kết luận của tech-lead

- Reviewer không chạy test → tech-lead chạy sau merge trên `team/FEAT-007` @ `7572547` (một lần giữ khóa, `MIGRATE_EXIT=0`): `test_erp_ai_setting` `Ran 68 tests in 11.965s OK`, `test_policy` `Ran 38 tests in 6.262s OK`, `test_architecture` `Ran 112 tests in 6.208s OK`.
- Tra tên báo cáo không phân biệt hoa thường (collation của MariaDB): `"erp ai test bc query"` được nhận và lưu đúng như gõ. Phép kiểm lại lúc chạy thuộc U6b (`design-addendum-1-U6b.md:178`, đợt 1): phải so tên cùng cách; lệch thì đóng (không chạy), không phải lỗ bảo mật → chuyển team-leader cho kế hoạch đợt 1.
- `ALLOWED_REPORT_TYPES` nằm ở controller; nếu phép kiểm lúc chạy của U6b cần cùng bộ đó thì theo F-1 phải chuyển sang `constants.py` trước → cùng ghi chú cho đợt 1.
- E-6 xét báo cáo chỉ theo `ref_doctype`; một Query/Script Report có thể đọc bảng khác. Đây là thiết kế của ADR-034 QĐ 3 như đã viết; tech-lead không đổi thiết kế, chuyển team-leader để kiểm ở U6b (đợt 1).

## deferred

- 4 điểm nhỏ ở trên; điểm (1) đề nghị ghi vào `docs/team/debt.md` (hằng `"HD Ticket"` lặp ở `policy.py`, `kpi.py`).
