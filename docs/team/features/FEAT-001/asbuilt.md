Feature: FEAT-001
Stage: asbuilt
Author-agent: writer
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G4 đang tắt. -->

<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod. -->
Approved-by-prod:

# As-Built FEAT-001 — AI Agent `erp_ai` cho Helpdesk Miyano (`L0`/`L1`)

Căn cứ: nhánh `team/FEAT-001`, commit `533180a` (qa nghiệm thu lần 2, `Verdict: accepted`), base so diff là `develop` (`2932a2b`, merge-base). Nguồn: `acceptance.md`, `design.md` (kèm mục Amendments), `journal/FEAT-001.md` (D2–D10), `diff.patch`, các `review-NN.md`, ADR-001..006.

```
grep -nE '^Verdict: accepted$' acceptance.md  ->  142:Verdict: accepted
G4: tắt (config.json gates.G4_uat = false); Approved-by để trống đúng thiết kế.
```

## 1. Đã làm so với spec

App `erp_ai` cài lên site Helpdesk ở trạng thái **tắt**, mức `L0`; khi người bật thì chạy được `L0` (shadow: chỉ ghi dự đoán vào nhật ký) và `L1` (phân loại, hướng giải quyết, comment, Task). 48 task (T1..T43 cùng T1b, T7b, T9b, T11b, T20b, T20c), 170 commit trên nhánh so với `develop`, 507 test tự động.

| Nhóm | AC | Kết quả (acceptance.md, 533180a) |
|---|---|---|
| Bộ đánh giá offline: xuất phiếu, chạy prompt, báo cáo độ chính xác, ma trận nhầm lẫn, kết luận theo ngưỡng 85%/70% | AC-1, AC-2, AC-3 | đạt |
| Cài đặt: role, tài khoản agent không có System Manager, trường AI permlevel 8, mặc định tắt/`L0` | AC-4 | đạt (xem E-1 ở mục 6) |
| Kích hoạt, chống tự kích hoạt, chống trùng, nhóm loại trừ, chốt tài khoản job | AC-5, AC-6 | đạt |
| Thẩm quyền theo người, bộ tool = mức × thẩm quyền | AC-7, AC-8 | đạt |
| Hành vi `L0` và `L1`; ghi nhận người sửa tay; báo cáo `ERP AI Accuracy` | AC-9, AC-10, AC-11, AC-12 | đạt (AC-10 đạt ở lần 2, xem D9) |
| Tool đọc mã nguồn và bản ghi; cấm DocType nhạy cảm; khóa API không lộ | AC-13, AC-14 | đạt |
| Giới hạn lượt/ngày, chi phí, ngân sách tháng; chọn khóa, cầu dao, hạn mức; scheduler giờ/ngày | AC-15..AC-18 | đạt |
| Form cấu hình: phân quyền, nút "Kiểm tra khóa" | AC-19 | phần tự động đạt; **bấm nút thật: chờ người** |
| Trường AI hiện trên trang ticket Helpdesk cho HD Agent, ẩn với khách | AC-20 | phần tự động đạt (permlevel 8); **chụp màn hình: chờ người** |

Ngoài phạm vi (giữ đúng spec A-1, A-6, A-7): tool `L2`/`L3` (cấp đúng bộ tool `L1`), dự phòng nhà cung cấp thứ hai, agent tự giao phiếu cho người, đổi `status` phiếu, bất kỳ bước nào trên production.

Kiểm chung (acceptance.md, 533180a): `cmd.test` `Ran 507 tests OK`, bằng tổng theo 25 module; `cmd.lint` exit 0; `cmd.migrate` exit 0; grep dấu skip rỗng; không chạm `protected_paths`.

## 2. Quyết định lệch guide hoặc design gốc

Design đã được amend (mục `Amendments 2026-11-11`, 11 dòng) để khớp các quyết định dưới đây, nên so với design hiện hành các mục này là "đúng thiết kế"; chúng lệch **guide v2.2 hoặc design bản đầu**. Nguồn: `docs/team/journal/FEAT-001.md`.

| Mã | Quyết định | Vì | Hoàn tác |
|---|---|---|---|
| Phạm vi L0/L1 (A-1; journal dòng 15) | Chỉ làm `L0`/`L1`; `L2`/`L3` chọn được nhưng cấp bộ tool `L1` | guide `:1466` chưa có schema tool `L2`/`L3` | `/team:analyze FEAT-001 --amend`; mở feature "erp_ai L2/L3 tools" |
| D2 (dòng 32) | Mọi file test ở gốc gói chuyển vào `erp_ai/tests/` (+`__init__.py`); `test_utils.py` giữ ở gốc | Frappe 15 nhập file test ở gốc gói thành `erp_ai`, `cmd.test` chạy 0 test | chuyển file về gốc |
| D3 (dòng 32) | `cmd.*` trong profile thành lệnh một đoạn (bench tự tìm thư mục) | hook role-policy chặn `cd ../.. && …` | đổi lại `cmd.*` |
| D4 (dòng 39) | `git_source` chỉ còn `log` và `blame`; allowlist cờ theo đúng tên; pathspec và file blame qua `resolve_safe_path`; bỏ `show`/`diff` | `show`/`diff`/`log -p` in được nội dung file bí mật đã commit, lách deny-list (NFR-6); reviewer bắt `--cont=` lách cờ cấm ở T7 | mở lại enum subcommand |
| D5 (dòng 40) | Giữ thẻ khẩn `[GẬP]` đúng guide/spec; bộ phân giải nhận cả `[GẬP]` lẫn `[GẤP]` | đổi chính tả ảnh hưởng eval NFR-9, việc của người | sửa prompt + spec |
| D6 (dòng 46) | 5 trường tiền USD là Float precision 6, nhãn có "(USD)"; không dùng Currency | Currency hiển thị theo tiền tệ mặc định của site (`miyano` = VND) | đổi về Currency + patch |
| D7 (dòng 52) | Hook `ignore_links_on_delete = ["ERP AI Log"]` | nhật ký không được chặn việc xóa phiếu; dòng log vẫn không xóa được | bỏ dòng hook |
| D8 (dòng 59) | Comment phiếu lấy từ core `Comment` (`comment_type="Comment"`, `reference_doctype="HD Ticket"`), tác giả = `owner` server đặt; không đọc `HD Ticket Comment`/`commented_by` | Helpdesk 15.1.0 đã chuyển comment sang core `Comment`; `commented_by` do client đặt được, giả mạo được (STD-SEC-4) | thêm handler cho `HD Ticket Comment` |
| D9 (dòng 80) | `ERP AI Log` thêm trường `skipped_fields` (Small Text JSON `[{field, reason}]`, chỉ đọc); runner chép `skipped` của `set_classification` vào dòng `classify` và `reason` | spec AC-10 đòi "lý do vào nhật ký"; lần nghiệm thu 1 trả design-defect (DD-1) | bỏ trường (cột NULL để lại không hại) |
| D10 (dòng 80) | Đổi `erp_ai/agent/test_runner.py` thành `test_agent_runner.py`; thêm luật test kiến trúc cấm tên file test mà Frappe bỏ qua | `frappe/test_runner.py:160` bỏ qua mọi file tên `test_runner.py`: 52 test runner không chạy trong `cmd.test`/CI (DD-2) | đổi tên lại |

Mọi quyết định trên do team-leader ghi ở chế độ `decide` (G1–G4 tắt); chưa có người nào duyệt chúng bằng chữ ký. Người nên đọc lại D4, D7, D8 (đụng bảo mật/dữ liệu).

## Differences from design

Cách đối chiếu: với mỗi mục thiết kế, đã đối chiếu các hunk của `diff.patch` ở những chỗ amendment nêu (đọc mã tại dòng ghi ở cột 3); phần còn lại dựa vào danh sách file trong diff, kết quả test trong `acceptance.md` và phán quyết approve của `review-NN`. "Đúng thiết kế" nghĩa là đúng design **sau Amendments**. Lý do chỉ lấy từ journal/review; không có thì ghi "không ghi nhận". Số dòng `:1` nghĩa là chỉ xác nhận file có trong diff, chưa đọc từng dòng.

### 2.1 Tám mục của design

| Mục thiết kế | Thực tế | file:line | Lý do |
|---|---|---|---|
| 1. Bối cảnh | đúng thiết kế (đã sửa theo D2, D4, D7, D8, D10) | `design.md:16` | — |
| 2. Mô hình dữ liệu | khác design gốc: 5 trường USD là Float (D6); thêm `skipped_fields` (D9); comment là core `Comment` (D8). Khớp design hiện hành | `erp_ai_setting.json:66`, `erp_ai_credential.json:73`, `erp_ai_log.json:171` | journal D6, D8, D9 |
| 3. API / hợp đồng | khác design gốc: `git_source` chỉ `log`/`blame` (D4); hook comment đặt trên `Comment` (D8). Khớp design hiện hành. Chỉ có đúng 1 method whitelist: `check_keys` | `source.py:30-52`, `hooks.py:148-150`, `erp_ai_setting.py:107` | journal D4, D8 |
| 4. Luồng | khác design gốc: bước 6 và 8 của 4.3 ghi `skipped_fields` (D9) | `runner.py:227-228`, `:288-305`, `:337` | journal D9 (acceptance DD-1) |
| 5. Quyền | đúng thiết kế (trường AI permlevel 8; role agent không có System Manager) | `install.py:19`, `:48-64` | — |
| 6. Migration và rollback | đúng thiết kế: không có patch dữ liệu; `ensure_setup` idempotent, không ghi đè giá trị đã lưu; thêm cột NULL `skipped_fields` | `install.py:30-37`, `:66-76` | — |
| 7. Touchpoints | đúng: 71 touchpoint, xem 2.2; file ngoài danh sách xem 2.3 | — | — |
| 8. Test plan | đúng: 507 test (design amend lần 2 dự kiến thêm 4+1+2 test, thực tế có đủ); số test `cmd.test` = tổng theo module | `acceptance.md:22-23` | — |

### 2.2 Bảng touchpoint (71 file; 3 sửa, 68 mới)

| Touchpoint | Thực tế | file:line | Lý do |
|---|---|---|---|
| `pyproject.toml` (sửa) | đúng: `anthropic>=0.103.1,<1`, frappe `>=15.126.1,<16.0.0` | `pyproject.toml:12`, `:20` | — |
| `erp_ai/hooks.py` (sửa) | đúng design hiện hành; khác bản gốc: hook `Comment.after_insert` và `ignore_links_on_delete` | `hooks.py:148-154` | journal D7, D8 |
| `.github/workflows/ci.yml` (sửa) | đúng (init bench v15, helpdesk `v15.1.0`, `run-tests --app erp_ai`); chưa chạy thật vì cấm push | `ci.yml:93`, `:110` | acceptance DoD: "CI xanh" chưa kiểm được |
| `erp_ai/constants.py` | đúng | `constants.py:1` | — |
| `erp_ai/alerts.py` | đúng | `alerts.py:1` | — |
| `erp_ai/handlers.py` | đúng design hiện hành: `comment_after_insert` nhận core `Comment`, tác giả = `owner` | `handlers.py:100` | journal D8 |
| `erp_ai/tasks.py` | đúng (hourly dò lại khóa; daily cộng chi phí, kiểm nâng quyền) | `hooks.py:159-162` | — |
| `erp_ai/install.py` | đúng | `install.py:30` | — |
| `erp_ai/test_utils.py` | đúng | `test_utils.py:1` | — |
| `erp_ai/tests/__init__.py` | đúng (thêm theo D2) | `tests/__init__.py` | journal D2 |
| `erp_ai/tests/test_handlers.py` | đúng | `tests/test_handlers.py:1` | — |
| `erp_ai/tests/test_tasks.py` | đúng | `tests/test_tasks.py:1` | — |
| `erp_ai/tests/test_install.py` | đúng | `tests/test_install.py:1` | — |
| `erp_ai/tests/test_alerts.py` | đúng | `tests/test_alerts.py:1` | — |
| `erp_ai/tests/test_ticket_delete.py` | đúng (test xóa phiếu có log) | `tests/test_ticket_delete.py:28` | journal D7 |
| `erp_ai/tests/test_architecture.py` | đúng: thêm `FRAPPE_SKIPPED_TEST_FILENAMES` và luật cấm tên file | `tests/test_architecture.py:113`, `:579` | journal D10 |
| `erp_ai/agent/__init__.py` | đúng | `agent/__init__.py` | — |
| `erp_ai/agent/queue.py` | đúng | `queue.py:1` | — |
| `erp_ai/agent/policy.py` | đúng | `policy.py:1` | — |
| `erp_ai/agent/authority.py` | đúng design hiện hành: đọc comment từ core `Comment` | `authority.py:27` | journal D8 |
| `erp_ai/agent/prompts.py` | đúng | `prompts.py:1` | — |
| `erp_ai/agent/classification.py` | đúng design hiện hành: nhận `[GẬP]` và `[GẤP]` | `classification.py:11-12` | journal D5 |
| `erp_ai/agent/run_log.py` | đúng: không đổi mã (list `skipped_fields` đi qua quy tắc serialize JSON có sẵn) | `run_log.py:1` | — |
| `erp_ai/agent/runner.py` | đúng design hiện hành: `skipped_fields` ở bước phân loại và vòng lập luận | `runner.py:227-228`, `:288-305`, `:337` | journal D9 |
| `erp_ai/agent/test_queue.py` | đúng | `test_queue.py:1` | — |
| `erp_ai/agent/test_policy.py` | đúng | `test_policy.py:1` | — |
| `erp_ai/agent/test_authority.py` | đúng | `test_authority.py:1` | — |
| `erp_ai/agent/test_classification.py` | đúng | `test_classification.py:1` | — |
| `erp_ai/agent/test_run_log.py` | đúng | `test_run_log.py:1` | — |
| `erp_ai/agent/test_agent_runner.py` | khác design gốc: tên cũ `test_runner.py` bị Frappe bỏ qua; đã đổi tên, thêm 4 test D9 | `test_agent_runner.py:1` | journal D10 |
| `erp_ai/agent/tools/__init__.py` | đúng | `tools/__init__.py:1` | — |
| `erp_ai/agent/tools/registry.py` | đúng design hiện hành: `git_source` chỉ log/blame | `registry.py:1` | journal D4 |
| `erp_ai/agent/tools/read.py` | đúng design hiện hành: `get_record` mở `Comment`, bỏ `HD Ticket Comment` | `read.py:1` | journal D8 |
| `erp_ai/agent/tools/source.py` | khác design gốc: allowlist cờ, chỉ `log`/`blame` | `source.py:30-52`, `:203`, `:222` | journal D4 |
| `erp_ai/agent/tools/write_ticket.py` | đúng: không đổi ở lần sửa 2; `skipped` đã có sẵn trong hợp đồng | `write_ticket.py:25-57` | — |
| `erp_ai/agent/tools/test_registry.py` | đúng | `test_registry.py:1` | — |
| `erp_ai/agent/tools/test_read.py` | đúng | `test_read.py:1` | — |
| `erp_ai/agent/tools/test_source.py` | đúng | `test_source.py:1` | — |
| `erp_ai/agent/tools/test_write_ticket.py` | đúng | `test_write_ticket.py:1` | — |
| `erp_ai/gateway/__init__.py` | đúng | `gateway/__init__.py:1` | — |
| `erp_ai/gateway/client.py` | đúng (chỗ duy nhất `import anthropic`) | `client.py:1` | — |
| `erp_ai/gateway/breaker.py` | đúng | `breaker.py:1` | — |
| `erp_ai/gateway/credentials.py` | đúng | `credentials.py:1` | — |
| `erp_ai/gateway/cost.py` | đúng | `cost.py:1` | — |
| `erp_ai/gateway/test_breaker.py` | đúng | `test_breaker.py:1` | — |
| `erp_ai/gateway/test_gateway.py` | đúng | `test_gateway.py:1` | — |
| `erp_ai/eval/__init__.py` | đúng | `eval/__init__.py` | — |
| `erp_ai/eval/export_tickets.py` | đúng | `export_tickets.py:20` | — |
| `erp_ai/eval/run_eval.py` | đúng | `run_eval.py:145` | — |
| `erp_ai/eval/test_export_tickets.py` | đúng | `test_export_tickets.py:1` | — |
| `erp_ai/eval/test_run_eval.py` | đúng | `test_run_eval.py:1` | — |
| `erp_ai_agent/doctype/__init__.py` | đúng | `doctype/__init__.py` | — |
| `erp_ai_setting/__init__.py` | đúng | — | — |
| `erp_ai_setting/erp_ai_setting.json` | đúng design hiện hành: `monthly_budget_usd` Float | `erp_ai_setting.json:66` | journal D6 |
| `erp_ai_setting/erp_ai_setting.py` | đúng (`check_keys` chỉ System Manager) | `erp_ai_setting.py:107` | — |
| `erp_ai_setting/erp_ai_setting.js` | đúng (nút "Kiểm tra khóa") | `erp_ai_setting.js:1` | — |
| `erp_ai_setting/test_erp_ai_setting.py` | đúng | `test_erp_ai_setting.py:1` | — |
| `erp_ai_credential/__init__.py` | đúng | — | — |
| `erp_ai_credential/erp_ai_credential.json` | đúng design hiện hành: `budget_month_usd` Float | `erp_ai_credential.json:73` | journal D6 |
| `erp_ai_credential/erp_ai_credential.py` | đúng (lớp rỗng) | `erp_ai_credential.py:1` | — |
| `erp_ai_credential/test_erp_ai_credential.py` | đúng | `test_erp_ai_credential.py:1` | — |
| `erp_ai_log/__init__.py` | đúng | — | — |
| `erp_ai_log/erp_ai_log.json` | đúng design hiện hành: thêm `skipped_fields` (Small Text, chỉ đọc) | `erp_ai_log.json:28`, `:171` | journal D9 |
| `erp_ai_log/erp_ai_log.py` | đúng (lớp rỗng) | `erp_ai_log.py:1` | — |
| `erp_ai_log/test_erp_ai_log.py` | đúng: thêm `test_skipped_fields_is_read_only_small_text` | `test_erp_ai_log.py:1` | journal D9 |
| `report/__init__.py` | đúng | — | — |
| `erp_ai_accuracy/__init__.py` | đúng | — | — |
| `erp_ai_accuracy/erp_ai_accuracy.json` | đúng (Script Report, System Manager) | `erp_ai_accuracy.json:1` | — |
| `erp_ai_accuracy/erp_ai_accuracy.py` | đúng (mẫu = 0 thì `accuracy_pct = None`) | `erp_ai_accuracy.py:1` | spec không định số cho ca này |
| `erp_ai_accuracy/erp_ai_accuracy.js` | đúng | `erp_ai_accuracy.js:1` | — |
| `erp_ai_accuracy/test_erp_ai_accuracy.py` | đúng | `test_erp_ai_accuracy.py:1` | — |

Đủ 71 hàng (3 sửa + 68 mới). Số test thực tế: 507 (`grep -c 'def test_'` tĩnh = 507).

### 2.3 File trong diff nhưng ngoài touchpoint

| File | Thực tế | Lý do |
|---|---|---|
| `.gitignore` | thêm dòng bỏ qua file chạy cục bộ của plugin team (`.team/current.json`, `.claude/worktrees/`…) | không ghi nhận trong review/tasks.md; là thay đổi onboard của team (commit `34e4c8f`, journal dòng 25) |
| `CLAUDE.md`, `.claude/rules/{source,team-core,tests,tool-map}.md`, `.claude/settings.json`, `.team/config.json`, `.team/profile.json` | cấu hình team plugin, không phải mã sản phẩm | journal dòng 25 (onboard) |
| `docs/**` (guide, ADR-001..006, architecture, research, journal, metrics…) | tài liệu của team | artifact của các bước analyze/architect/research |

Không có endpoint, cờ cấu hình hay mặc định nào trong mã sản phẩm nằm ngoài spec và `acceptance.md`: `grep frappe.whitelist erp_ai` (trừ test) chỉ ra `check_keys` (AC-19); không có `allow_guest`. Hai điểm là quyết định có chủ ý chưa nằm chữ nghĩa trong spec, đã ghi trong journal và design Amendments: D7 (`ignore_links_on_delete` cũng gỡ chặn liên kết `ERP AI Log` → User, design D-29) và D5 (nhận thêm `[GẤP]`). Người nên xác nhận cả hai.

## Release notes (cho người dùng)

Đối tượng: người vận hành (Hiếu, IT) và người duyệt (COO). Mỗi dòng truy về AC hoặc file.

- **Đổi gì.** Có app mới `erp_ai` cho Helpdesk. Cài xong agent **tắt**, mức `L0` (AC-4). Khi bật: `L0` chỉ ghi dự đoán phân loại vào `ERP AI Log`, không đổi phiếu (AC-9); `L1` ghi loại phiếu/nhóm/ưu tiên theo bảng ánh xạ đầu mục, độ tin cậy, hướng giải quyết và comment, không đổi `status`, không ghi đè phân loại của người (AC-10). Lý do một trường bị bỏ qua (giá trị không tồn tại) nằm ở trường "Trường bỏ qua khi phân loại" của `ERP AI Log` (AC-10, `erp_ai_log.json:171`). Agent chịu thẩm quyền theo người (AC-7), không gọi API với phiếu thuộc nhóm loại trừ hoặc có cờ "không dùng AI" (AC-5), không vượt 8 lượt/lần, 5 lần/phiếu/ngày, ngân sách tháng (AC-15, AC-16). Nhiều khóa API được quản lý trên form `ERP AI Setting`, có nút "Kiểm tra khóa" (AC-17, AC-19). Báo cáo `ERP AI Accuracy` đo độ chính xác theo đầu mục (AC-12). Bộ đánh giá offline đo độ chính xác trên phiếu đã gán nhãn (AC-1, AC-2).
- **Ai bị ảnh hưởng.** HD Agent thấy thêm các trường AI trên phiếu; khách (HD Contact) không thấy (AC-20, kiểm bằng tay). Tài khoản `ai.agent@miyano.com.vn` được tạo khi cài/migrate, chỉ có role `ERP AI Agent` và `Agent`, không có System Manager (AC-4). Comment của agent có `@mention` sẽ gửi email cho người được nhắc (design, mục rủi ro).
- **Cần làm gì.** Xem mục 6 (checklist người) trước khi bật. Tóm tắt: đặt lại `ERP AI Setting` trên `miyano`, kiểm phiên bản Helpdesk production, nhập khóa API và ngân sách tháng, rồi mới bật.

## CHANGELOG

Đã thêm dưới `## [Unreleased]` trong `CHANGELOG.md` (tạo file mới, Keep a Changelog): Added 5 dòng, mỗi dòng kết thúc `(FEAT-001)`. Không đổi `[Unreleased]` thành số phiên bản.

## Nợ sau G4

Số việc qa để lại cho writer: 3 (As-Built, README/tài liệu, CHANGELOG). Đóng: 3/3. Hai mục khác trong DoD không thuộc writer: CI xanh (để `/team:pr`, `/team:release`) và AC-19/AC-20 (pending-human, mục 6).

| Mục DoD qa ghi chủ | Đã làm | Kiểm lại (lệnh → kết quả) |
|---|---|---|
| As-Built | `docs/team/features/FEAT-001/asbuilt.md` (file này) | file tồn tại; `/team:release` kiểm bằng `ls docs/team/features/FEAT-001/asbuilt.md` |
| README/tài liệu | `README.md`: cài đặt, cấu hình, các mức `L0`/`L1`, nhóm loại trừ, bộ đánh giá, chạy test | `grep -n "run-tests --app erp_ai" README.md` → `61:bench --site <site> run-tests --app erp_ai` (khớp `cmd.test` với `<site>` thay cho `miyano`) |
| CHANGELOG | `CHANGELOG.md` mục `[Unreleased]` | `grep -c '(FEAT-001)' CHANGELOG.md` → `5` |
| CI xanh trên nhánh (DoD phần build, chưa tick) | không phải việc của writer | để `/team:pr`, `/team:release` kiểm: feature cấm push (intake `:28`) nên workflow chưa chạy; bước test tương đương xanh tại chỗ (507 test) |
| AC-19 bấm nút, AC-20 chụp màn hình | không phải việc của writer | pending-human, xem mục 6 |

`pr-body.md`: `grep -cE '^## (Feature|Why|What changed|How verified)$'` → `4`.

## 6. Cài đặt, bật app và checklist cho người

### Cài đặt (site `miyano` hoặc site khác)

```
bench get-app <URL_REPO> --branch team/FEAT-001      # nhánh này chưa push; URL do người quyết
bench --site <site> install-app erp_ai               # cần Helpdesk 15.1.0 đã cài (required_apps)
bench --site <site> migrate
```
Lệnh `install` của profile: `cd ../.. && bench setup requirements --dev && bench --site miyano install-app erp_ai`. Cài xong: agent tắt, mức `L0`, tài khoản agent và role được tạo (`install.py:30`). Chạy lại migrate không ghi đè giá trị cấu hình đã lưu.

### Bật app (sau khi xong checklist)

Mở `/app/erp-ai-setting`: dán khóa API ở bảng khóa, đặt ngân sách và bốn đơn giá token (phải > 0 mới bật được), rồi tích `enabled`. Giữ `L0` ít nhất một tuần đo độ chính xác; chỉ chuyển `L1` khi đạt ngưỡng guide `:1285` (≥ 85% tổng, không đầu mục nào sai liên tiếp 3 lần).

### Checklist trước khi bật (người làm, chưa tick)

- [ ] **Đặt lại `ERP AI Setting` trên `miyano` (E-1).** Bản ghi hiện giữ `permission_level = L2`, `excluded_teams` rỗng (rò từ một lần chạy test cũ lúc 15:26, `acceptance.md:121`). Trên form đặt `permission_level = L0` và `excluded_teams` = "Nhân sự & Hành chính" + "Tài chính Kế toán" (mỗi tên một dòng). Nếu không, phiếu nhóm loại trừ sẽ được gửi lên API khi bật (NFR-4). Dọn thêm HD Team thừa "IT", "Nhân sự & Hành chính" do test cũ để lại (journal dòng 66).
- [ ] **Kiểm phiên bản Helpdesk trên production ≥ 15.1.0.** Từ 15.1.0 comment phiếu nằm ở core `Comment` (D8). Bản cũ hơn vẫn ghi `HD Ticket Comment` nên trigger comment và đọc comment sẽ không thấy gì. Lệnh đọc phiên bản do người chọn (không có trong `cmd.*`).
- [ ] **AC-19:** trên `/app/erp-ai-setting` của site dev, bấm "Kiểm tra khóa", chụp kết quả. Cần một khóa API thật đã nhập.
- [ ] **AC-20:** mở 1 phiếu bằng tài khoản HD Agent và 1 phiếu bằng HD Contact; chụp màn hình; xác nhận trường AI hiện với HD Agent và ẩn với khách (`ui: false`, không có QA trình duyệt tự động).
- [ ] **Khóa API và ngân sách tháng.** Nhập ít nhất một khóa Anthropic loại workspace chuẩn (`sk-ant-api03-`, không dùng key per-user, guide mục 9.1) và `monthly_budget_usd` (mặc định 10 USD, đề xuất của guide để đo). Đơn giá 4 loại token mặc định 0 nên phải nhập; model và đơn giá lấy từ cấu hình, không viết cứng. Khóa tuyệt đối không dán vào comment, log hay artifact.
- [ ] **Guide §18, việc COO chốt:** ai được cấp `ERP AI Instructor` (đề xuất COO + Hiếu); Server Script tạo-ở-trạng-thái-tắt (đồng ý hay không); phiếu nhóm Nhân sự & Kế toán không chạy agent; ngân sách API tháng đầu; người giữ khóa API và quyền admin Console; cơ cấu workspace Console; quy ước mọi thay đổi Role của `ai.agent` chỉ COO duyệt. Spec A-15 đã lấy đề xuất của guide làm mặc định; sai thì sửa trên form, không cần sửa mã.
- [ ] **Guide §19, 12 điểm kiểm chứng trên production:** tên field thật của HD Ticket/Comment; `server_script_enabled`; HD Ticket Template còn dùng được; HD Form Script; `frappe.enqueue(job_id, deduplicate)`; tài khoản thật job nền chạy dưới (probe mục 5.2); ID model và đơn giá hiện hành; trường người được giao trên ToDo (`allocated_to`); `ripgrep` đã cài (`which rg`; máy dev chưa có, tool tìm mã sẽ trả `ok=false` "chưa cài"); quyền đọc `apps/` của tài khoản chạy bench, không có `.env`/khóa lọt vào; tên header hạn mức qua SDK; loại khóa API (workspace chuẩn, không per-user).
- [ ] **Dọn dòng Error Log do test trên `miyano`.** Journal ghi các dòng test/mutation để lại (tiêu đề `m`, `erp_ai: CẢNH BÁO`, `ERPAI-TEST-probe`), cộng 1 dòng `helpdesk.search.build_index` mỗi lần `migrate` (của Helpdesk, không phải erp_ai). Số đếm ghi trong journal và acceptance: 145 → 195 (dòng 70), 195 → 200 (dòng 74), 203 → 206 (dòng 85), 207 → 208 (`acceptance.md:33`); đếm lại trước khi dọn. Người xóa; agent không được phép tự xóa.
- [ ] Việc ngoài DoD của đội (spec): backup và script kiểm chứng mục 6 của guide trên production; gán nhãn 71 phiếu; chạy bộ đánh giá với khóa thật và đạt NFR-9 (≥ 85%); quyết định bật agent.

### Chưa kiểm (qa ghi nhận)

Lần chạy CI workflow thật; chiều xuống của migration (`uninstall-app` xóa dữ liệu nên không chạy); scheduler thật nhận mục hourly/daily trên `miyano` (chỉ có test kiểm `hooks.py`).

## Rollback

<!-- /team:release viết trước lần deploy đầu: điều kiện kích hoạt, lệnh (từ docs/team/ci.md), phần dữ liệu, thời gian dự kiến -->

<!-- devops thêm dòng sau khi lên prod thành công: Released: <tag> <YYYY-MM-DD> -->
