Feature: takeover
Stage: takeover
Author-agent: team-leader
Date: 2026-11-10
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Nợ kỹ thuật

## Chặn (phải xử lý trước khi đội làm việc an toàn)
| Mục | STD | Bằng chứng | Đề xuất |
|---|---|---|---|
| CI đỏ khi chưa có test: bước "Find tests" chạy `grep -rn "def test" > /dev/null`, grep không thấy gì thì thoát mã 1 → job fail ở mọi push lên `develop` và mọi PR | STD-TEST | `.github/workflows/ci.yml:42-45` | Thêm test đầu tiên ngay trong intake đầu tiên (đúng TDD), hoặc tạm đổi bước thành cảnh báo. Không xóa bước chạy test |
| Không có môi trường chạy được tính năng: bench local không có app `helpdesk`; `erp_ai` chưa cài lên site nào | STD-TEST | `ls ~/frappe-bench/apps`, `sites/apps.txt`, `bench --site miyano list-apps` | Chốt site dev, cài helpdesk đúng phiên bản production vào bench dev (việc của người, ngoài takeover) |
| `docs/team/` bị gitignore bởi mẫu `team/` → artifact của đội không được version | STD-DOC | `.gitignore:10` (`git check-ignore -v docs/team/assessment.md`). Dòng này và `.team/` (`:9`) là **thay đổi chưa commit**, xuất hiện lúc 2026-11-10 18:25:53 trong khi quét (lúc bắt đầu `git status` sạch với `.gitignore`); takeover không ghi file này | Đổi thành `/team/` hoặc bỏ dòng trước khi commit; giữ `.team/` |

## Nên làm
| Mục | STD | Bằng chứng | Đề xuất |
|---|---|---|---|
| Tài liệu đặt doctype ở `erp_ai/erp_ai/doctype/` nhưng module thật là `ERP AI agent` → `erp_ai/erp_ai_agent/` | STD-DOC | guide `:634`, `:905`; `erp_ai/modules.txt:1` | Chọn một: sửa guide theo module thật, hoặc đổi module trước khi tạo DocType đầu tiên (đổi sau khi có DocType thì đắt) |
| Phụ thuộc `anthropic` chưa được khai; guide dùng `requirements.txt` trong khi app khai bằng `pyproject.toml` | STD-DEP | guide `:640`; `pyproject.toml:10-12` | Khai `anthropic` (có ghim phiên bản) trong `[project].dependencies` khi intake đầu tiên cần SDK |
| Action CI phiên bản cũ (`checkout@v3`, `setup-python@v4`, `setup-node@v3`, `cache@v3`) | STD-CI | `ci.yml:40`, `:48`, `:53`; `linter.yml:49` | Nâng lên bản hiện hành trong một PR riêng |
| README nói pre-commit có pyupgrade, cấu hình không có | STD-DOC | `README.md:29`; `.pre-commit-config.yaml:20-64` | Sửa README (ruff `UP` đã thay pyupgrade, `pyproject.toml:36`) |
| Tên repo trong guide (`mvl26/erp-ai`, SSH) khác remote thật (`mvl26/erp_ai`, HTTPS) | STD-DOC | guide `:610`, `:1279`; `git remote -v` | Sửa guide |
| Guide và `.claude/settings.json` chưa commit | STD-DOC | `git status --porcelain` lúc bắt đầu: `?? .claude/`, `?? docs/` | Commit cùng PR đầu tiên |
| `cmd.lint` đỏ: ruff-format muốn xóa dòng trống cuối `erp_ai/hooks.py` | STD-STYLE | Onboard 2026-11-11: `pre-commit run --all-files` exit 1, "1 file reformatted" (diff: `erp_ai/hooks.py:249` dòng trống thừa); onboard đã hoàn tác | Chạy `pre-commit run --files erp_ai/hooks.py` và commit trong PR đầu tiên |
| `test_setup_neutralizes_live_rows_attributed_to_agent` tự gọi `_neutralize_agent_rows()` nên vẫn xanh nếu bỏ lệnh gọi trong `setUp` (BUG-002, minor hoãn) | STD-TEST-5 | `erp_ai/tests/test_tasks.py:339-347`; acceptance BUG-002 | Đổi tên test cho đúng việc kiểm, hoặc tạo dòng ở `setUpClass` rồi kiểm `setUp` đã vô hiệu hóa chúng |
| Guard `frappe.db.exists("DocType", doctype)` luôn đúng trên Frappe v15 (BUG-002, minor hoãn) | STD-STYLE-5 | `erp_ai/tests/test_tasks.py:197`; acceptance BUG-002 | Bỏ guard khi dọn |
| FEAT-001 `design.md` §3.4.3 hàng 6 chưa ghi tiền tố `Your credit balance is too low` (BUG-001) | STD-DOC | `docs/team/features/FEAT-001/design.md:330`, D-6 `:872` | Thêm tiền tố vào hàng 6 và D-6 (writer không có công cụ sửa trong lượt này) |
| FEAT-003: ERP AI Setting thiếu Section Break `section_reply` ("Chỉ báo và độ trễ trả lời") so với design 2.1; `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` nằm dưới `section_model` (lý do: ruling D-1 của tech-lead, `review-03.md`: `test_erp_ai_setting.py::test_status_fields_defaults` không sửa được, STD-TEST-5, yêu cầu `thinking_text` đứng ngay sau `trigger_keyword`) | STD-DOC | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:141-174`; `docs/team/features/FEAT-003/asbuilt.md` DEV-2; `docs/team/features/FEAT-003/review-03.md` D-1 | Việc còn lại: chỉ sửa chữ của design 2.1 (6 Section Break, không `section_reply`) cho khớp mã; `section_reply` không được thêm lại |
| FEAT-003: design 3.2 bảng lỗi (hàng `text` sai kiểu) ghi `ValidationError`, thực tế `FrappeTypeError` do Frappe ném trước thân hàm | STD-DOC | `docs/team/features/FEAT-003/design.md:172`; `erp_ai/tests/test_ticket_panel.py:394-397`; `review-T9-r1.md` | Sửa hàng 172 theo bảng ở asbuilt.md DEV-1 (design đã duyệt, writer không sửa) |
| FEAT-003, minor hoãn (review-08, T10): `sanitize_html` gọi không có `disallowed_tags` (không ảnh hưởng dạng lưu); `trigger_keyword` đọc hai lần mỗi lần gửi; không test kiểm log `denied method=send reason=no_read` | STD-TEST-2 | `erp_ai/ticket_panel.py:107`, `:130`; `docs/team/features/FEAT-003/review-08.md` | Gộp hai lần đọc thành một; thêm assert log `denied method=send reason=no_read` khi có task sửa `ticket_panel.py` |
| FEAT-003, minor hoãn (review-08, T13): chưa ghim `formEl.append(inputEl, sendEl)`, `"keydown"`, cuối thân `onSendFailed`; T13 minor 1, 3, 5 (chi tiết ở reviewer T13) | STD-TEST-2 | `erp_ai/tests/test_architecture.py`; `docs/team/features/FEAT-003/review-08.md`, `review-T13-r1.md` | Thêm ghim vào luật tĩnh của `.js` |
| FEAT-003, minor hoãn (review-08, T14): ghim chưa bắt giá trị hằng `NARROW_SCREEN_PX = 640` (lần thứ hai một ghim bỏ sót giá trị hằng) | STD-TEST-2 | `erp_ai/public/js/agent_status_indicator.js:23`; `docs/team/features/FEAT-003/review-08.md` | Ghim cả giá trị hằng; rà các hằng khác của `.js` có cùng lỗ hổng |
| FEAT-003, minor hoãn (review-09, T11): `TITLE_RUN_FAILED` / `self.log_error` không dùng (assert không ghi hoặc bỏ); assert `call_count` thừa; chưa kiểm `decisions` đúng 1 phần tử | STD-TEST-5 | `erp_ai/tests/test_ticket_panel.py` (`TestTicketPanelGateParity`); `docs/team/features/FEAT-003/review-09.md` | Dọn khi có task sửa file test này |
| FEAT-003, minor hoãn (review-09, T15): vòng tự kiểm của scanner cổng lặp trên chính tuple của nó; chưa có mẫu chuỗi thuần cho scanner lời gọi cấm; chưa bắt các cách lách `socket.once(`, `call (`, `doc.add_comment(` | STD-TEST-8 | `erp_ai/tests/test_architecture.py`; `docs/team/features/FEAT-003/review-09.md` | Thêm mẫu vi phạm cho ba cách lách và một mẫu chuỗi thuần |

## Để sau
| Mục | STD | Bằng chứng | Đề xuất |
|---|---|---|---|
| Tài liệu "Chiến lược AI Agent Helpdesk Miyano" (31/10) được tham chiếu nhưng không có trong repo | STD-DOC | guide `:5`, `:1474-1492` | Đưa vào `docs/` hoặc ghi đường dẫn nơi lưu |
| Guide 1519 dòng / 82 KB, trộn quyết định, mã mẫu và việc của người | STD-DOC | `wc -l docs/HuongDan_TrienKhai_erp-ai.md` | Khi bắt đầu code, tách dần thành spec theo từng tính năng trong `docs/team/` |
| `ruff` không có trong env của bench (chỉ chạy được qua pre-commit) | STD-STYLE | `env/bin/python -m ruff` → "No module named ruff" | Cài khi cần format từng file nhanh |

## Test chập chờn
| Test | Lần gặp | Ghi chú |
|---|---|---|
| `erp_ai/agent/tools/test_route_ticket.py::test_sla_chosen_by_complexity_condition` | 2026-11-14, 3/3 lần trên `team/FEAT-004` @ `ba89ab3`: cả app 19:18, chạy lại module 19:26, lượt chốt 19:40 (`Ran 29 tests in 51.694s` / `FAILED (errors=3)`) | FEAT-004 `acceptance.md` F-5 (STD-TEST-7). Luôn là `QueryDeadlockError 1213`, trong khi các ca 1213 khác đổi tên giữa các lần. `git diff --stat develop...team/FEAT-004` trên `route_ticket.py`, `test_route_ticket.py`, `hooks.py`: rỗng, nên không do diff FEAT-004. Site `miyano` dùng chung, lúc đó có `run-tests --app erp_ai` của phiên khác ngoài khóa (pid 851601). Chưa có lần xanh nào khi site độc quyền. Việc: chạy lại khi không phiên nào khác chạy test; vẫn đỏ thì tìm kết nối thứ hai trong test. Chủ: team-leader xếp, ngoài FEAT-004. Bằng chứng: scratchpad qa `v/app.xml`, `v/rr/`, `v/rr3/` |
| `erp_ai/tests/test_ticket_panel.py::test_thread_ignores_non_comment_types` | 2026-11-14, 3/3 lần trên `ba89ab3`: cả app 19:18, chạy lại module 19:32, lượt chốt 19:41 (`Ran 36 tests in 55.310s` / `FAILED (failures=1, errors=19)`) | FEAT-004 `acceptance.md` F-5 (STD-TEST-7). Luôn `QueryDeadlockError 1213`; `ticket_panel.py`, `test_ticket_panel.py` không đổi so với `develop`. Cùng hoàn cảnh và cùng việc phải làm như dòng trên |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py::test_no_role_can_write_or_delete` | 2026-11-14 19:14:44, 1 lần, trong lần cả app trên `ba89ab3` (`Items in the first set but not the second: 'ERP AI Instructor'`); chạy riêng 19:27 `Ran 1` `OK`, cả module 19:51 `Ran 7 tests in 5.092s` / `OK` | FEAT-004 `acceptance.md` F-4. Không phải thứ tự test: nhánh FEAT-004 không cấp `ERP AI Instructor` trên `ERP AI Log` ở đâu cả. `team/FEAT-007` @ `5b3fe27` (T5, commit 19:17:46) thêm DocPerm đó vào `erp_ai_log.json` và dev của nó chạy `cmd.migrate` trên site `miyano` trước commit (progress T5 trong `docs/team/features/FEAT-007/tasks.md`); phiên FEAT-007 không dùng khóa site. Test đọc DocPerm từ DB nên đỏ khi site mang lược đồ của nhánh khác. Việc: trước mỗi lần `cmd.test` cả app của một nhánh, migrate từ đúng worktree của nhánh đó và không cho phiên khác migrate trong lúc chạy; khi FEAT-007 vào `develop` thì phép so đã được chính nó đổi thành ba role. Chủ: team-leader |

## Đã quét / Chưa quét / Độ tin cậy
| Tầng | Đã quét | Chưa quét | Độ tin cậy |
|---|---|---|---|
| T0 | detect-stack (TODO/FIXME 0, skip 1 — dương tính giả), git log | — | cao |
| T1 | README, guide (mục lục + mục liên quan) | Bản chiến lược 31/10 (không có trong repo) | tb |
| T2 | Đọc trực tiếp toàn bộ file có nội dung (< 30 file) + môi trường bench chỉ đọc | — | cao |
| T3 | Không chạy: không có mâu thuẫn chưa giải thích | — | — |
