Feature: FEAT-002
Stage: asbuilt
Author-agent: writer
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G4 đang tắt. -->

<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod. -->
Approved-by-prod:

# As-Built FEAT-002 — Chỉ báo "Đang suy nghĩ… / Đang làm: <việc>…" trên trang phiếu agent và độ trễ trả lời `@ai`

Căn cứ: nhánh `team/FEAT-002`, qa nghiệm thu ở commit mã `7ea066a` (commit cuối có đổi mã là `b8f6a3f`), `Verdict: accepted`. Base so diff là `23ded66` (merge-base với `team/FEAT-001`). Nguồn: `spec.md`, `design.md`, `acceptance.md`, `review-01..10.md`, `tasks.md`, `diff.patch`, ADR-007, ADR-008, `journal/FEAT-002.md`. Ký hiệu: "D-n (journal)" là quyết định build trong journal; "design D-n" là giả định của design.md.

```
grep -nE '^Verdict: accepted$' acceptance.md  ->  181:Verdict: accepted
G4: tắt (config.json gates.G4_uat = false); Approved-by để trống đúng thiết kế.
```

## 1. Đã làm so với spec

Khi người gõ `@ai ...` trên một phiếu, trang phiếu của HD Agent hiện một chỉ báo nổi ở góc dưới phải: tên tài khoản agent và chữ `Đang suy nghĩ…`, đổi thành `Đang làm: <nhãn>…` khi agent chạy tool; chỉ báo mất khi lần chạy kết thúc (kể cả lỗi). Câu trả lời đầu tiên của `@ai` được giữ lại một khoảng ngẫu nhiên trong [min, max] giây kể từ tín hiệu bắt đầu. Chỉ báo không tạo bản ghi nào (không `Comment`, `Task`, không sửa phiếu).

| Phần | AC / NFR | Kết quả (acceptance.md, `7ea066a`) |
|---|---|---|
| 3 trường `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` trên `ERP AI Setting`, có kiểm khi lưu | AC-1, NFR-2 | đạt (test tự động) |
| Tín hiệu bắt đầu trước lời gọi model đầu; `comment_mention` ở `L1+` và `ticket_insert` ở mọi mức | AC-2 | đạt |
| Câu trả lời trễ `d` ∈ [min, max], trần là hạn chót lần chạy | AC-3, NFR-1, NFR-2 | đạt |
| Đúng một `done` ở mọi nhánh kết thúc, kể cả rollback; `done` đứng sau commit cuối | AC-4, NFR-5 | đạt phía server; phía trang chờ người |
| Lần chạy bị bỏ qua và câu chữ rỗng: không tín hiệu; `ticket_insert` không bao giờ chờ | AC-5 | đạt |
| Không đổi số lần tính giới hạn ngày, nội dung gửi model, số lời gọi và chi phí | AC-6 (c)(e), AC-8, NFR-3 | đạt |
| Lỗi phát tín hiệu không chặn lần chạy, không lộ câu chữ vào nhật ký | AC-7, NFR-4' | đạt |
| Nhãn "Đang làm: <việc>…" cho 11 tool và bước phân loại | AC-9 | đạt |
| Script trang phiếu (hiển thị, hai phiên, đổi phiếu, tự mất sau `expires_in_s`) | AC-10, AC-11 | **chờ người** (`ui: false`, không có test JS) |
| Một bản ghi HD Form Script do app sở hữu, đặt lại khi cài/migrate, xóa khi gỡ | AC-12 | đạt (test + migrate lên → lên → xuống → lên) |

Kiểm chung (acceptance.md, mục "Kiểm chung"): 8 module của FEAT-002 chạy riêng đều `OK`, cộng 242 test (`test_agent_runner` 56, `test_answer_delay` 8, `test_runner_status` 39, `test_run_status` 9, `test_erp_ai_setting` 19, `test_architecture` 58, `test_handlers` 31, `test_install` 22). `cmd.lint`: 12 dòng `Passed`, 0 `Failed`. Không có dấu skip mới; không chạm `protected_paths`; Helpdesk không bị FEAT-002 sửa. `cmd.test`: `Ran 591 tests`, `FAILED (failures=16, errors=3)`; 19 test đỏ này giống hệt trên code FEAT-001 với cùng dữ liệu site, xem BUG-002 ở mục 6.

Ngoài phạm vi (giữ đúng spec): sửa `apps/helpdesk`; chỉ báo lúc job còn chờ hàng đợi; chỉ báo trên cổng khách; lịch sử trạng thái; trễ cho comment `@ai` thứ hai trở đi; đổi giới hạn lần chạy, dedup, ngân sách; mọi thay đổi dữ liệu site `miyano`.

### 1.1 Cấu hình mới (`ERP AI Setting`)

| Trường | Loại | Mặc định | Giới hạn |
|---|---|---|---|
| `thinking_text` | Small Text | `Đang suy nghĩ…` | ≤ 5000 ký tự; rỗng hoặc chỉ khoảng trắng = tắt chỉ báo (khoảng trễ vẫn áp dụng) |
| `answer_delay_min_s` | Int | `3` | 0 đến 30 |
| `answer_delay_max_s` | Int | `5` | 0 đến 30; min ≤ max |

Câu lỗi (test so đúng chuỗi): `Trễ trả lời tối thiểu phải từ 0 đến 30`; `Trễ trả lời tối đa phải từ 0 đến 30`; `Trễ trả lời tối thiểu không được lớn hơn trễ trả lời tối đa`; `Chữ chỉ báo khi đang suy nghĩ không được dài quá 5000 ký tự` (`erp_ai_setting.py:42-43`, `:108`). Câu chữ rỗng được lưu là `""` chứ không phải `NULL`, để lần migrate sau không điền lại mặc định (design D-8; test `test_emptied_thinking_text_survives_setup`).

### 1.2 Hợp đồng tín hiệu realtime (ADR-008)

- Sự kiện `erp_ai:agent_status` (`constants.py:37`), phát bằng `frappe.publish_realtime` với `room = doc:HD Ticket/<tên>` và `after_commit=False`; chỉ `erp_ai/agent/run_status.py` phát, chỉ `runner.py` gọi module này.
- Payload đúng 7 khóa: `ticket_id`, `run_id`, `agent_user`, `agent_name`, `state` (`thinking` | `working` | `done`), `text`, `expires_in_s` (= `JOB_TIMEOUT_S`, 600) (`run_status.py:12`). Không có tham số tool, nội dung phiếu hay câu trả lời trong payload.
- Với mỗi `run_id`: tín hiệu đầu là `thinking`; đúng 1 `done`, là tín hiệu cuối. Lần chạy bị bỏ qua hoặc câu chữ rỗng: 0 tín hiệu. Tên tool lạ do model bịa ra dùng nhãn dự phòng `xử lý yêu cầu`.
- Không ghi DB, cache hay tệp (ADR-004 giữ nguyên, nên phát ở `L0` không trái quyết định 4). Thiếu tiến trình `socketio` thì chỉ báo im lặng, lần chạy không đổi.
- Ghi chú: câu "Hệ quả" của ADR-008 về khách vào phòng `doc:` đã được đính chính ở ADR-009 (thuộc FEAT-003, ngoài As-Built này); hợp đồng payload không đổi.

### 1.3 Bản ghi HD Form Script do app sở hữu (ADR-007)

- Tên `ERP AI Agent Status`; `dt = HD Ticket`, `apply_to = Form`, `enabled = 1`, `apply_to_customer_portal = 0`, `apply_on_new_page = 0`, `is_standard = 0`; `script` = nội dung tệp `erp_ai/public/js/agent_status_indicator.js` (`install.py:20-23`).
- `after_install` và `after_migrate` (qua `ensure_setup`, bước 7, `install.py:41-49`, `:208`) tạo bản ghi nếu thiếu, hoặc đặt lại từ tệp repo nếu khác ở bất kỳ khóa nào; nếu giống hệt thì không lưu lại. `before_uninstall` (`install.py:52`, `hooks.py:92`) xóa đúng bản ghi này; đó là lệnh xóa duy nhất trong mã cài đặt.
- **Hệ quả cho người quản trị: mọi sửa tay bản ghi này trên site bị ghi đè ở lần `migrate` kế tiếp, theo thiết kế** (spec A-22; test `test_status_script_reset_when_changed_on_site`). Muốn đổi giao diện chỉ báo thì sửa tệp `.js` trong repo.

## 2. Quyết định lệch design hoặc phát sinh khi build

Nguồn: `docs/team/journal/FEAT-002.md` và các `review-NN`. Mọi quyết định do team-leader ghi ở chế độ `decide` (G1–G4 tắt); chưa có chữ ký người.

| Mã | Quyết định | Vì | Hoàn tác |
|---|---|---|---|
| D-1 (journal, dòng 15) | Tiêu chí "`cmd.test` xanh" hiểu là: danh sách test đỏ giống hệt nền, không thêm test đỏ. Nền `--app erp_ai` đã đỏ trước FEAT-002 (16 failures + 3 errors) | 19 test của `test_tasks.TestCheckPrivilegeEscalation` và `erp_ai_accuracy` phụ thuộc dữ liệu site | sửa BUG-002 rồi `cmd.test` xanh thật |
| D-2 (dòng 15) | Hook chặn tech-lead chạy `bench run-tests --app erp_ai`; dựa vào đầu ra toàn bộ do dev dán, cây `erp_ai/` sau merge giống nhánh task | role-policy | — |
| D-3 (dòng 16) | Hai dev chạy full suite đồng thời gây deadlock MariaDB trên site chung; từ nhóm sau chỉ một dev mỗi lượt | site chung | — |
| D-4 (dòng 17) | Số đếm DB đổi 4/4/0/22 thành 4/5/0/29 là do người dùng thật (HD Ticket 43067/43068), không phải rò rỉ test; từ đó so đếm trước/sau từng lần chạy | người dùng thật làm trên site dev | — |
| D-5 (dòng 17; review-08 deferred) | Design 3.7 bước 4 (`reset()` không xóa ticket) lệch ADR-008 Quyết định 6; code theo ADR | review-08 (STD-DESIGN-2) | designer cập nhật chữ ở 3.7 |
| D-6 (dòng 19; review-09 deferred) | Design D-13 ("cảnh báo cả lúc cài và lúc gỡ") mâu thuẫn mục 3.6 ("gỡ: không làm gì"); code theo 3.6: `before_uninstall` thiếu doctype thì im lặng, `_ensure_agent_status_script` thiếu doctype thì ghi cảnh báo logger | review-09 | `/team:design FEAT-002 --amend` chọn một |
| D-7 (dòng 20) | Full suite vòng 1 của T6: `Ran 563`, 16F/3E giống nền; `Comment` +20 cần so lại ở full suite cuối | người dùng thật cùng lúc | qa đã so ở lần verify cuối (acceptance.md, "Kiểm chung") |

Ghi chú: design D-5 (tên tool lạ nhận nhãn dự phòng) và design D-6 (chờ trước tool đầu của lượt có `post_comment`, để không giữ khóa dòng phiếu khi ngủ) được làm đúng như thiết kế; design D-6 có test riêng sau review-04 (STD-TEST-2). Ngoài hai điểm lệch (D-5, D-6 của journal), không tìm thấy điểm lệch nào khác khi đối chiếu diff.

## Differences from design

Cách đối chiếu: với từng mục design và từng touchpoint, đã đọc hunk tương ứng trong mã tại dòng ghi ở cột 3 (số dòng của cây `team/FEAT-002`). Lý do chỉ lấy từ `review-NN`, `tasks.md`, journal; nếu không có thì ghi "không ghi nhận". Không phát hiện hành vi nào trong diff nằm ngoài spec và `acceptance.md`: không có endpoint `whitelist` mới, không có cờ cấu hình hay mặc định ngoài 3 trường của AC-1.

### 3.1 Tám mục của design

| Mục thiết kế | Thực tế | file:line | Lý do |
|---|---|---|---|
| 1. Bối cảnh | đúng thiết kế | `run_status.py:1`, `answer_delay.py:1` | — |
| 2. Mô hình dữ liệu | đúng thiết kế: 3 trường sau `trigger_keyword`, bản ghi HD Form Script 6 cờ + `script` | `erp_ai_setting.json:21-23`, `:120-133`; `install.py:20-23` | — |
| 3. API / hợp đồng | đúng thiết kế (3.1 form, 3.2 sự kiện, 3.3 `RunStatus`, 3.4 `AnswerDelay`, 3.5 lỗi, 3.6 cài đặt, 3.7 script, 3.8 test util). **Khác ở hai chỗ:** 3.6 về cảnh báo khi gỡ (code theo 3.6, mâu thuẫn design D-13), 3.7 bước 4 về `reset()` (code theo ADR-008) | `erp_ai_setting.py:42-43`, `:108-111`; `run_status.py:36-77`; `answer_delay.py:35-52`; `install.py:52-57`, `:208-226`; `agent_status_indicator.js:1`, `:161-176` | journal D-6, D-5; review-09, review-08 |
| 4. Luồng | đúng thiết kế: `RunStatus` tạo sau chốt `level_L0`; `try/finally` + `_end_status`; chờ trước tool của lượt có `post_comment`; `working()` trước `classify`, `set_classification` và mỗi tool | `runner.py:108-136`, `:140-157`, `:203`, `:243`, `:317`, `:341-344` | — |
| 5. Quyền | đúng thiết kế: cấu hình vẫn chỉ System Manager; script chỉ trang agent; payload 7 khóa, `textContent` | `install.py:23`; `run_status.py:12`; `agent_status_indicator.js:86-87` | — |
| 6. Migration và rollback | đúng thiết kế: không DDL, không patch; `ensure_setup` chỉ điền thiếu cho 3 trường; migrate lên → lên → xuống → lên khớp đối soát 6.3 | `install.py:41-49`; `acceptance.md` mục "Migration" | — |
| 7. Touchpoints | đúng: 18 file, xem 3.2; không có file ngoài danh sách trong `erp_ai/` | — | — |
| 8. Test plan | đúng: mọi test có tên trong 8.1/8.2 đều có (qa đã đối chiếu 28 tên với junit); thêm `test_unhashable_step_never_throws` sau review-05 | `test_run_status.py:68`, `test_runner_status.py:1` | review-05 (STD-TEST-1) |

### 3.2 Bảng touchpoint (18 file: 6 mới, 12 sửa)

| Touchpoint | Thực tế | file:line | Lý do |
|---|---|---|---|
| `erp_ai_setting/erp_ai_setting.json` (sửa) | đúng: 3 trường, `field_order` | `erp_ai_setting.json:21-23`, `:120-133` | — |
| `erp_ai_setting/erp_ai_setting.py` (sửa) | đúng: 2 dòng `INT_LIMITS`, `check_status_settings`, gọi trong `validate` | `erp_ai_setting.py:42-43`, `:61`, `:108` | — |
| `erp_ai_setting/test_erp_ai_setting.py` (sửa) | đúng: `test_status_fields_defaults/rejections/valid_edges_save` | `test_erp_ai_setting.py:1` | review-02 approve vòng 1 |
| `erp_ai/constants.py` (sửa) | đúng: 3 hằng | `constants.py:25`, `:35`, `:37` | — |
| `erp_ai/agent/run_status.py` (mới) | đúng; thêm hằng `STATE_*` và nhánh bắt `TypeError` ở `working()` | `run_status.py:12-18`, `:59-66` | review-05 (`test_unhashable_step_never_throws`) |
| `erp_ai/agent/answer_delay.py` (mới) | đúng | `answer_delay.py:9-52` | review-03 vòng 2 (2 major, STD-TEST-5/8) |
| `erp_ai/agent/runner.py` (sửa) | đúng; nối `status.take_errors()` vào `error` ở 5 chỗ | `runner.py:40`, `:108-157`, `:214`, `:224`, `:234`, `:331`, `:356` | review-07 (STD-TEST-2) |
| `erp_ai/install.py` (sửa) | đúng; `before_uninstall` im lặng khi thiếu doctype (xem journal D-6) | `install.py:20-57`, `:208-226` | journal D-6, review-09 |
| `erp_ai/hooks.py` (sửa) | đúng: `before_uninstall = "erp_ai.install.before_uninstall"` | `hooks.py:92` | — |
| `erp_ai/public/js/agent_status_indicator.js` (mới) | đúng thiết kế; `reset()` theo ADR-008 (journal D-5), thêm `router.afterEach` | `agent_status_indicator.js:1`, `:130-135`, `:161-176` | review-08 |
| `erp_ai/test_utils.py` (sửa) | đúng: `FakeGateway(on_call)`, `record_status_signals` | `test_utils.py:38-50`, `:57` | — |
| `erp_ai/agent/test_agent_runner.py` (sửa) | đúng: gắn `record_status_signals` ở `setUp` | `test_agent_runner.py:79` | review-04 |
| `erp_ai/agent/test_run_status.py` (mới) | đúng: 9 test | `test_run_status.py:1` | review-05, review-07 |
| `erp_ai/agent/test_answer_delay.py` (mới) | đúng: 8 test | `test_answer_delay.py:1` | review-03 |
| `erp_ai/agent/test_runner_status.py` (mới) | đúng: 39 test | `test_runner_status.py:1` | review-01, review-04..07 |
| `erp_ai/tests/test_handlers.py` (sửa) | đúng: gắn `record_status_signals` | `test_handlers.py:65` | review-04 |
| `erp_ai/tests/test_install.py` (sửa) | đúng: test AC-12 và mặc định AC-1; thêm test thiếu doctype | `test_install.py:360`, `:383` | review-09 (2 major, STD-TEST-8) |
| `erp_ai/tests/test_architecture.py` (sửa) | đúng: bộ quét ADR-007/008 và tự kiểm; thêm ca `getattr`, `import_module`, bí danh, `from frappe import db` | `test_architecture.py:1084`, `:1097`, `:1117`, `:1606` | review-10 (3 vòng, STD-TEST-8) |

Đủ 18 hàng, khớp 18 file trong `git diff --name-status 23ded66 HEAD -- erp_ai` (6 `A`, 12 `M`).

### 3.3 File trong diff nhưng ngoài touchpoint

Ngoài `erp_ai/`: chỉ có tài liệu của đội (`docs/team/**`: spec, design, ADR-007/008, research, acceptance, journal, metrics, `review-NN`, `review-pkg-*`) và cấu hình `.team`/`.claude` do đội quản lý. Không có mã sản phẩm ngoài touchpoint.

## Release notes (cho người dùng)

Đối tượng: người vận hành (IT) và HD Agent. Mỗi dòng truy về AC hoặc file.

- **Đổi gì.** Trên trang phiếu của HD Agent, khi `@ai` đang chạy, góc dưới phải hiện tên tài khoản agent và `Đang suy nghĩ…`, đổi thành `Đang làm: <việc>…` (ví dụ "đọc phiếu", "viết trả lời", "phân loại phiếu") và mất khi lần chạy xong, kể cả khi lỗi (AC-2, AC-4, AC-9, `run_status.py:20`). Câu trả lời đầu tiên của `@ai` được giữ lại 3–5 giây (tính từ lúc chỉ báo bắt đầu), chỉnh được (AC-1, AC-3). Với phiếu mới (`ticket_insert`) chỉ báo hiện ở mọi mức nhưng không có độ trễ (AC-2, AC-5). Chỉ báo không tạo comment, task hay thay đổi phiếu (NFR-6).
- **Ai bị ảnh hưởng.** HD Agent thấy chỉ báo; khách trên cổng khách không thấy (AC-12, `apply_to_customer_portal = 0`). Quản trị viên (System Manager) có 3 trường mới trên `/app/erp-ai-setting` (AC-1). Chi phí và số lời gọi model không đổi (AC-8).
- **Cần làm gì.** Cài/nâng cấp: `bench --site <site> migrate` (restart không đủ: bản ghi HD Form Script chỉ được đặt lại khi `migrate`). Để đổi câu chữ hoặc độ trễ: sửa 3 trường trên `ERP AI Setting`; để tắt chỉ báo: để trống `thinking_text` (độ trễ vẫn áp dụng; đặt 0 và 0 để tắt trễ). Không sửa bản ghi HD Form Script `ERP AI Agent Status` trên site: sẽ bị ghi đè ở `migrate` tiếp theo. Xem mục 6 (checklist).

## CHANGELOG

Đã thêm dưới `## [Unreleased]` trong `CHANGELOG.md`: Added 3 dòng, Changed 1 dòng, mỗi dòng kết thúc `(FEAT-002)`. Không đổi `[Unreleased]` thành số phiên bản.

## Nợ sau G4

Số việc qa để lại cho writer: 3 (As-Built, README/tài liệu người dùng, CHANGELOG; acceptance.md mục "DoD"). Đóng: 3/3. Mục thứ tư của DoD (bước tay AC-10, AC-11) thuộc người, không phải writer.

| Mục DoD qa ghi chủ | Đã làm | Kiểm lại (lệnh → kết quả) |
|---|---|---|
| As-Built, kèm dòng "chạy lại bước tay AC-10 sau mỗi lần nâng cấp Helpdesk/Frappe" | `docs/team/features/FEAT-002/asbuilt.md` (file này), mục 6 | `grep -n "Chạy lại các bước tay" docs/team/features/FEAT-002/asbuilt.md` → có dòng ở mục 6 |
| README/tài liệu người dùng (chỉ báo, nhãn việc, cách tắt, khoảng trễ, cảnh báo ghi đè A-22) | `README.md`, mục "Chỉ báo trạng thái trên trang phiếu" | `grep -n "ERP AI Agent Status" README.md` → khớp |
| CHANGELOG | `CHANGELOG.md` mục `[Unreleased]` | `grep -c '(FEAT-002)' CHANGELOG.md` → 4 |
| Bước tay AC-10 (a)–(i), AC-11 | không phải việc của writer | người, mục 6 |

`pr-body.md`: `grep -cE '^## (Feature|Why|What changed|How verified)$' docs/team/features/FEAT-002/pr-body.md` → 4.

## 6. Cài đặt, nâng cấp và checklist cho người

### Cài đặt và nâng cấp

```
bench --site <site> migrate
```

Lệnh `migrate` của profile (`cmd.migrate`): `cd ../.. && bench --site miyano migrate`. Với app đã cài, chỉ cần cập nhật mã rồi chạy `migrate`: `after_migrate` điền mặc định cho 3 trường mới (chỉ khi chưa có giá trị) và tạo hoặc đặt lại bản ghi HD Form Script từ tệp `.js`. Cài mới: `bench --site <site> install-app erp_ai` (Helpdesk 15.1.0 đã cài), cùng bước tạo bản ghi. **Sau mỗi lần sửa `agent_status_indicator.js` phải chạy `migrate`; restart không đưa nội dung mới vào bản ghi.** Gỡ app (`uninstall-app`) xóa bản ghi `ERP AI Agent Status`. `cmd.build` không cần (tệp `.js` được Python đọc lúc cài, không phải bundle). Cần tiến trình `socketio` của bench chạy; thiếu nó thì chỉ báo im lặng nhưng lần chạy không đổi.

Lùi một nửa (giữ phần server, tắt phần trang): để trống `thinking_text` trên form. Lùi hẳn: gọi `erp_ai.install.before_uninstall` trên site trước khi revert mã, rồi revert và `migrate` (design mục 6.2).

### Checklist cho người (chưa tick)

- [ ] **Bước tay AC-10 (a)–(i) và AC-11.** Làm đúng như `acceptance.md`, mục "Bước tay cho người (AC-10, AC-11)" (12 bước), trên `miyano`, desktop, bằng tài khoản HD Agent (không phải `ai.agent@…`), cấu hình ở `L1+` và `enabled=1`. Ghi kết quả từng ý vào cuối `acceptance.md`; trả cấu hình về giá trị đã ghi ở bước 1.
- [ ] **Chạy lại các bước tay đó sau mỗi lần nâng cấp Helpdesk hoặc Frappe.** Script dựa vào `$socket` và `get_ticket_customizations` của Helpdesk, những chỗ không được đảm bảo giữa các phiên bản (design, "Việc của người" điểm 3: tối thiểu chạy lại (a), (g), (h)).
- [ ] **Sự cố quyền tài khoản agent (critical, STD-SEC-4; người quyết, đội không tự sửa dữ liệu site).** Theo truy vấn đọc của qa (`acceptance.md`, mục (a), (b)): `ai.agent@miyano.com.vn` có `System Manager` cùng 96 role ngoài danh sách cho phép, do một lần lưu User lúc 2026-11-12 11:21 trong phiên của tài khoản quản trị của người dùng (Version `spr34j6nam`). `ERP AI Setting` hiện là `permission_level = L3`, `excluded_teams` rỗng, `monthly_budget_usd = 100`, `enabled = 1` (lần lưu cuối 13:54:34, cùng phiên); giá trị người đặt sáng nay là L1 / "Nhân sự & Hành chính" + "Tài chính Kế toán" / 10. Người xác nhận việc thêm role có chủ ý không; nếu không, gỡ các role thừa và đặt lại ba giá trị trên. Cho tới lúc đó nhóm loại trừ không có hiệu lực và agent chạy ở `L3`.
- [ ] **BUG-002 (đã biết, có từ FEAT-001): 19 test phụ thuộc dữ liệu sống của site** (`test_tasks.TestCheckPrivilegeEscalation` 15 test, `erp_ai_accuracy.TestAccuracyTenLogSample` 4 test; `cmd.test` đỏ `failures=16, errors=3`). Đề xuất `/team:intake` thành bug riêng: cô lập dữ liệu trong `setUp` (STD-TEST-6). Nguồn `L0` lúc 13:49 chưa xác định (`acceptance.md`, mục (b); ý 3 của BUG-002).
- [ ] **`.team/profile.json`** chưa có `javascript` trong `language` và chưa có slot `cmd.test_js` (profile hiện `"language": ["python"]`). Người thêm nếu muốn chạy test JS; khi đó chạy `/team:plan FEAT-002 --insert` để thêm test JS cho AC-11 và AC-10 (i). Không chặn: `cmd.format`/`cmd.lint` đã chạy prettier và eslint cho `.js`.
- [ ] **Designer sửa chữ design** (`/team:design FEAT-002 --amend`): design D-13 so với mục 3.6 (journal D-6) và mục 3.7 bước 4 (journal D-5).
- [ ] **Production:** xác nhận có tiến trình `socketio` (câu hỏi mở A-2 của FEAT-001).

### Chưa kiểm (qa ghi nhận)

AC-10 và AC-11 (bước tay, cần trình duyệt và `socketio`); phần hiển thị của NFR-5 (AC-10 (b), (c)); CI workflow thật (cấm push).

## Rollback

<!-- /team:release viết trước lần deploy đầu: điều kiện kích hoạt, lệnh (từ docs/team/ci.md), phần dữ liệu, thời gian dự kiến -->

<!-- devops thêm dòng sau khi lên prod thành công: Released: <tag> <YYYY-MM-DD> -->
