Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 06 — FEAT-007 T6

- Diff: `git diff 80469e76ffd8008fd2d74bf72b625692b157e7c9..9010dd3` (đầu nhánh `team/FEAT-007-task-6`; merge vào `team/FEAT-007` là `270cb38`)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 2); vòng 1 là request-changes

## Vòng 1 — request-changes

- Range: `80469e7..d065852` (1 commit, 2 file, +102/−0), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED `AssertionError: 0 != 1 : no single notice when act_now_enabled goes 0 -> 1`, `Ran 33 tests in 4.254s FAILED (failures=6)`; GREEN `erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting` `Ran 33 tests in 1.277s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.270s OK`.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:662-700 | AC-4 đòi **một** `msgprint` chứa mỗi ô 0 → 1 một dòng. Mọi test chỉ bật một ô mỗi lần lưu, nên phần "một thông báo cho nhiều ô" không được kiểm. Nếu mã gọi `msgprint` mỗi ô một lần, hoặc chỉ giữ dòng cuối, cả 4 test vẫn xanh. | Thêm một ca bật từ 2 ô trở lên trong một lần lưu (ví dụ `act_now_enabled` + `one_click_approval_enabled`). Khẳng định đúng 1 lời gọi thông báo, 3 dòng, hai dòng ô theo thứ tự form, dòng môi trường ở cuối. |
| major | STD-TEST-8 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:66-69 (chỗ hở của test ở cùng file test trên) | Bộ lọc theo section (tắt ở Section Break kế tiếp) không có mồi nhử. Không test nào bật một trường Check ngoài `section_permissions`; `auto_assign_enabled` ở `section_routing` là trường thật trên form. Nếu phép đặt lại hỏng (ví dụ `inside = inside or …`), bật `auto_assign_enabled` sẽ hiện trong thông báo "quyền mở rộng" mà test vẫn xanh. | Trong cùng ca mới, đặt thêm `auto_assign_enabled` 0 → 1, khẳng định nhãn của nó không có trong thông báo và số dòng không đổi. Một test phủ được cả hai finding. |

minor | — | — | 1 điểm nhỏ: phép escape không được test. Không nhãn, mô tả nào của 5 ô, và không giá trị môi trường nào, chứa `& < > " '`, và chuỗi mong đợi cũng dựng bằng `escape_html`, nên bỏ `escape` ở `erp_ai_setting.py:89,93` test vẫn xanh. Cách sửa: dùng một giá trị có ký tự cần escape (Property Setter trên một nhãn có `<`, hoặc patch meta) | tùy dev

### Ghi nhận của reviewer

- Mã đạt AC-4 (phần form) và `design.md:322`: `on_update` gọi một `frappe.msgprint` tiêu đề "Đã bật quyền mở rộng", `indicator="orange"`; liệt kê các ô 0 → 1 từ `get_doc_before_save()` theo thứ tự form, dạng `<b>nhãn</b>: mô tả` có escape HTML; dòng cuối "Môi trường site: …".
- D-7: danh sách ô lấy từ meta qua `permission_switch_fields`, không tên ô nào trong `.py` ngoài test. NFR-7: `keep_agent_settings` và rollback trong `setUp`.
- Test đi cùng đường lưu của Frappe như production: `check_if_latest` nạp bản trước khi lưu cả khi đặt `ignore_validate` (`frappe/model/document.py:1004`).

### Review checklist (10)
1. trượt một phần — hai chỗ hở của test (2 major trên)
2. đạt 3. đạt (RED trước: 6 failure = 5 subTest + test `unrestricted`; hai test "không thông báo" xanh trước khi có mã là đúng với test phủ định; không skip) 4. đạt 5. đạt 6. đạt (đầu ra có escape) 7. đạt 8. đạt 9. đạt 10. đạt (`feat(setting): notice when an extended permission switch is turned on (FEAT-007)`, không dòng ghi công AI)

## Vòng 2 — approve (scoped re-review)

- Range sửa: `git diff d065852..9010dd3` (1 commit, 1 file `test_erp_ai_setting.py`, +24; không đổi mã sản phẩm). Merge vào `team/FEAT-007` là `270cb38`.
- Bằng chứng của dev: test mới `test_several_switches_on_one_notice_in_form_order_without_outside_check`; RED với đột biến "mỗi ô một `msgprint`": `AssertionError: 2 != 1 : several switches on in one save must give exactly one notice`; RED với đột biến "chỉ giữ dòng cuối": `AssertionError: Lists differ: ['<b>Duyệt một lần bấm</b>: ...] != ['<b>Làm luôn, không hỏi lại</b>: ...]`; RED với đột biến `inside = inside or field.fieldname == PERMISSION_SECTION`: `AssertionError: Lists differ: [..., '<b>Tự gán người và tạo Task</b>: Bật thì ...] != [..., 'Môi trường site: test']`; GREEN `test_erp_ai_setting` `Ran 34 tests ... OK`; `test_architecture` `Ran 112 tests ... OK`.

| # | Finding vòng 1 | Kết quả |
|---|---|---|
| 1 | major STD-TEST-2 — "một thông báo, mỗi ô một dòng" chưa được test | ADDRESSED (`test_erp_ai_setting.py:688-695` một lần lưu bật `one_click_approval_enabled` và `act_now_enabled`; `:697` đúng một thông báo; `:705` so cả danh sách dòng; dict lưu để `one_click` trước còn form để `act_now` trước, test mong thứ tự form nên mã theo thứ tự lưu cũng đỏ) |
| 2 | major STD-TEST-8 — bộ lọc section không có mồi nhử | ADDRESSED (`:686` đặt `auto_assign_enabled` về 0, `:692` bật nó trong cùng lần lưu; trường này là Check ở `section_routing` sau `section_permissions`; cờ "trong section" không đặt lại thì `:705`, `:706` đỏ) |

Lỗi mới do diff sửa gây ra: không có ở mức blocker/major.

### Review checklist (10), chỉ diff sửa
1–10: đạt (chỉ test; trong touchpoints; RED cho ba đột biến; không khẳng định sẵn có nào đổi; `test(setting): ... (FEAT-007)`, không dòng ghi công AI).

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `test_architecture` (luật `POLICY_FIELDS`, D-7) và GREEN chỉ có lời của dev | Sau merge, trên `team/FEAT-007` @ `270cb38`: `test_erp_ai_setting` `Ran 34 tests in 1.351s OK`; `test_architecture` `Ran 112 tests in 3.114s OK`. |
| `msgprint` cũng nổ khi mã (trình cài đặt, helper test) lưu ERP AI Setting và một ô đổi 0 → 1 | `git grep` trên đầu nhánh task: không file `.py` ngoài test nào gọi `.save()` trên ERP AI Setting (các `doc.save()` tìm thấy đều là phiếu hoặc bản ghi của công cụ; cài đặt điền `tabSingles` trực tiếp). Trong job nền `msgprint` chỉ vào message log. Không phải thiếu sót. |
| Dòng log "ai bật" thuộc U3 | Không thuộc T6. |
| `cmd.test` cả bộ | Mốc M1. `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`. |

## deferred

- (minor, tùy dev) phép escape chưa có test.
- (ngoài vòng) mồi nhử mới chỉ phủ trường Check đứng SAU section; `enabled` (Check ở `section_activation`, đứng TRƯỚC) chưa có test bật. Rủi ro thấp.
