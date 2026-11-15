Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-15
Approved-by:

# FEAT-007 — Sửa thiết kế đợt 0, lần 6: nơi đặt hàm tách dòng người nhận (R-9)

Lý do gọi: `plan-w1.md` R-9 (dòng 240, 269) — `design-w0-fixes-5.md` điểm 2 mục 3 bắt `erp_ai/agent/daily_report.py` import `filled_lines` từ controller `erp_ai_setting.py`, trái `LAYER_RULES` (ADR-001). Cần trước khi gọi dev T53.

## Thay thế phần nào của `design-w0-fixes-5.md`
Phán quyết này thay câu ở điểm 2 mục 3 của `design-w0-fixes-5.md` (dòng 48, từ "Dùng lại hàm tách dòng của `erp_ai_setting.py`" tới "import ở `daily_report`") và dòng Touchpoints thứ hai của điểm 2 (dòng 59, "`_filled_lines` → `filled_lines`, sửa 3 chỗ gọi trong file"); hành vi đọc người nhận (mục 1–3 phần còn lại), mục 4, phần Test và Loại của điểm 2 giữ nguyên.

## Phán quyết
1. **Hàm tách dòng sống ở tầng Lõi agent, trong một module mới không phụ thuộc gì của app:** `erp_ai/agent/text_lines.py`, hàm công khai
   `filled_lines(value: str | None) -> list[str]` — các dòng khác rỗng sau `strip()`, giữ thứ tự, **giữ dòng trùng**; `None`/`""` → `[]`. Thân hàm đúng như `_filled_lines` hiện có (`erp_ai_setting.py:313-315`), không đổi hành vi. Module chỉ import thư viện chuẩn (không `frappe`, không module nào của `erp_ai`).
2. **Ai import:**
   - `erp_ai/agent/daily_report.py` (Lõi → Lõi, hợp lệ): `from erp_ai.agent.text_lines import filled_lines`; người nhận = `list(dict.fromkeys(filled_lines(setting.coo_report_recipients)))` (bỏ trùng là việc của nơi gọi, không nằm trong `filled_lines`). Rỗng → bước 4 của `design.md:433`.
   - `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (Cửa vào → Lõi, hợp lệ; file này đã import `erp_ai.agent.policy`, `classification`, `hard_bans`, `routing`, `tools`): `from erp_ai.agent.text_lines import filled_lines`; xóa `_filled_lines` (`:313-315`); mọi chỗ gọi `_filled_lines` trong file (hiện `:285`, `:289`) gọi `filled_lines`. Sau sửa `grep -c _filled_lines` trên file = 0.
3. **Không** để `daily_report` giữ phép tách dòng riêng, và **không** để controller import `daily_report` (xem Phương án đã loại).
4. Ngoài phạm vi (STD-DESIGN-5): các bản tách dòng khác đã có (`erp_ai/alerts.py:8`, `erp_ai/agent/policy.py:107-109` `_change_app_lines`, `erp_ai_setting.py:374`, `:411`) giữ nguyên; muốn gom thì là việc `/team:clean` sau, không thuộc FEAT-007.

## Căn cứ
- ADR-001 Quyết định 2 (bảng tầng: "method whitelist trong controller DocType" thuộc Cửa vào; `erp_ai/agent/` là Lõi agent) và Quyết định 3 (chiều Cửa vào → Lõi agent → Cổng model). Ràng buộc "`erp_ai/agent/**` không import ... mã cài đặt".
- `LAYER_RULES` (`erp_ai/tests/test_architecture.py`, worktree `feat-007`, đọc 2026-11-15): luật scope `"erp_ai.agent"` ở `:69-80` cấm `"erp_ai.erp_ai_agent"` → `daily_report` không được import controller. Chiều ngược (controller → `erp_ai.agent.*`) không bị luật nào cấm; scope `erp_ai.agent.tools` và `erp_ai.agent.changes` không chứa `text_lines`.
- STD-DESIGN-2 (theo ADR, không đổi kiến trúc → không cần ADR mới, không cần architect), STD-DESIGN-6 (phụ thuộc một chiều: `text_lines` không import gì của app nên không tạo vòng; controller nằm trong `FRESH_IMPORT_MODULES` `test_architecture.py:35-41`, thêm một import chỉ dùng thư viện chuẩn không đổi kết quả của phép import riêng), STD-DESIGN-4 (một bản hàm dùng chung thay vì thêm bản thứ bảy), STD-STRUCT-5 (module một việc; không nhét hàm chữ vào `policy.py` hay `constants.py`), STD-STRUCT-1 (file mới dưới root `erp_ai`).

## Phương án đã loại
| Phương án | Vì sao loại |
|---|---|
| `daily_report` import `filled_lines` từ controller (`design-w0-fixes-5.md` điểm 2) | Trái `LAYER_RULES` `:69-80`, ADR-001 Ràng buộc; `TestArchitecture::test_layer_imports` đỏ |
| `daily_report` tự viết `[l.strip() for l in ... if l.strip()]` | Chép lại logic đã có (STD-DESIGN-4); hai chỗ có thể lệch luật "dòng trống" giữa phía lưu và phía gửi |
| Đặt `filled_lines` trong `daily_report.py`, controller import từ đó | Hợp lệ theo tầng nhưng controller phải nạp cả đồ thị import của báo cáo 08:00 (`redact`, `kpi`, `filelock`...) chỉ để tách dòng; sai trách nhiệm (STD-STRUCT-5) |
| Đặt trong `erp_ai/agent/policy.py` (cạnh `_change_app_lines`) hoặc `erp_ai/constants.py` | `policy.py` là chính sách kích hoạt/mức quyền, nhiều task đang chạm (xung đột nhánh); `constants.py` chỉ chứa hằng (STD-STRUCT-5) |

## Touchpoints
| File | Thay đổi | Ghi chú |
|---|---|---|
| `erp_ai/agent/text_lines.py` | **mới**: `filled_lines(value) -> list[str]` + docstring nêu "giữ thứ tự, giữ trùng, `None` → `[]`" | root `erp_ai` |
| `erp_ai/agent/test_text_lines.py` | **mới**: test của `filled_lines` | root `erp_ai`; `naming.test_file` `test_*.py`, colocated như các test khác trong `erp_ai/agent/` |
| `erp_ai/agent/daily_report.py` | import `filled_lines` từ `erp_ai.agent.text_lines`; bỏ trùng bằng `dict.fromkeys` | file đã thuộc T51–T54 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | thêm import; xóa `_filled_lines`; đổi chỗ gọi `:285`, `:289` | đổi tên thuần, không đổi hành vi |

Đối chiếu file mới ↔ `allowed_new_file_roots` (`['erp_ai', 'docs', '.github']`):
- `erp_ai/agent/text_lines.py` → khớp `erp_ai`.
- `erp_ai/agent/test_text_lines.py` → khớp `erp_ai`.
- `docs/team/features/FEAT-007/design-w0-fixes-6.md` (file này) → khớp `docs`.

Đối chiếu với `protected_paths` (`['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`): 0 file khớp.

## Test (đỏ trước)
| Test | Kiểm gì | Đỏ trước vì |
|---|---|---|
| `erp_ai/agent/test_text_lines.py::TestFilledLines::test_trims_and_drops_blank_lines` | `"coo@example.com\n\n  ke.toan@congty.vn  \n \t\n"` → `["coo@example.com", "ke.toan@congty.vn"]`; dòng `\r\n` cũng tách đúng | module chưa có (ImportError) |
| `erp_ai/agent/test_text_lines.py::TestFilledLines::test_none_empty_and_whitespace_only_give_empty_list` | `None`, `""`, `"  \n\t\n"` → `[]` (biên của AC-52: chỉ khoảng trắng = rỗng) | như trên |
| `erp_ai/agent/test_text_lines.py::TestFilledLines::test_keeps_order_and_duplicates` | `"b\na\nb"` → `["b", "a", "b"]` (bỏ trùng là việc nơi gọi) | như trên |
| `erp_ai/agent/test_daily_report.py::TestRun::test_recipients_trimmed_blank_and_duplicate_dropped` | giữ nguyên như `design-w0-fixes-5.md` điểm 2 (sendmail nhận `["coo@example.com", "ke.toan@congty.vn"]`) | `run_daily_report` chưa có |
| `erp_ai/agent/test_daily_report.py::TestRun::test_no_recipients_logs_only` | thêm ca trường chỉ có dòng trắng → chỉ log (như dòng T54 đã có) | nhánh rỗng chưa có |

Phải còn xanh (không đổi hành vi, không thêm test):
- `erp_ai/tests/test_architecture.py::TestArchitecture::test_layer_imports` — chứng minh `daily_report` không import `erp_ai.erp_ai_agent` (sẽ đỏ nếu dev làm theo chữ cũ của fixes-5).
- `erp_ai/tests/test_architecture.py::TestArchitecture::test_agent_modules_import_alone_in_fresh_process` — controller vẫn import riêng được sau khi thêm import `text_lines`.
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestOperationPeople::test_bad_email_blocked`, `::test_disabled_reviewer_blocked` — hai chỗ gọi đổi sang `filled_lines` giữ nguyên hành vi.

Lệnh chạy: slot `cmd.test_one` với từng file trên.

## Dòng task phải đổi (tech-lead build áp khi gộp; designer không chia task)
| Dòng | Đổi |
|---|---|
| T53 | `files:` thêm `erp_ai/agent/text_lines.py`, `erp_ai/agent/test_text_lines.py`; `test:` thêm `erp_ai/agent/test_text_lines.py`. Receives: thay "(`design-w0-fixes-5.md` điểm 2, mục 3)" bằng "(`design-w0-fixes-5.md` điểm 2 mục 1–3, nơi đặt hàm theo `design-w0-fixes-6.md`)". Returns thêm `erp_ai.agent.text_lines.filled_lines(value) -> list[str]`. Expect thêm ba test `test_text_lines.py::TestFilledLines::*` và `test_architecture.py::TestArchitecture::test_layer_imports` xanh. Bỏ ghi chú "không gọi dev T53 khi chưa có phán quyết về nơi đặt hàm" ở bảng "Sửa dòng task cũ khi gộp" của `tasks-w1.md` và ở dòng progress của T53 (R-9 đã đóng). T53 **không** chạm `erp_ai_setting.py`. |
| T54 | Receives thêm `filled_lines` (T53). Expect giữ ca "chỉ dòng trắng → rỗng" đã ghi; không thêm file. |
| Bước đổi controller | Chưa có task (`plan-w1.md:97`). Điều kiện cho tech-lead đặt: chạy **sau khi T53 merge** (cần `text_lines.py`); `files:` có `erp_ai_setting.py` nên không cùng lượt với bất kỳ task nào đang mở trên file đó (chuỗi U0 → T56 → T32 → T72 → T87, `plan-w1.md` R-9); test: `test_erp_ai_setting.py` (hai test `TestOperationPeople` ở trên) và `test_architecture.py::TestArchitecture::test_agent_modules_import_alone_in_fresh_process`. Có thể gắn thêm vào một task sẵn có đã có `erp_ai_setting.py` trong `files:` và chạy sau T53, hoặc một task nhỏ mới — tech-lead chọn. Cho tới khi bước này merge, `_filled_lines` và `filled_lines` cùng tồn tại (tạm, cùng hành vi). |

## Giả định do nhóm quyết
- Tên module `text_lines` và tên hàm `filled_lines` theo `naming.file`/`naming.function` (snake_case) của profile; không cần mục glossary.
- `filled_lines` không bỏ trùng: controller cần kiểm từng dòng gõ (kể cả dòng trùng) như hiện tại; daily_report tự bỏ trùng.

Câu hỏi nghiệp vụ: 0.

## Explore / đối chiếu
Không gọi Explore: mọi đọc là file đã biết. Đã đọc: `design-w0-fixes-5.md:43-66`, `plan-w1.md:97,177,240,255-285`, `tasks-w1.md:24-38`, `tasks.md:331-334,449-468`, ADR-001, `design.md:427-435` (grep `daily_report`); mã worktree `feat-007`: `test_architecture.py:1-120,1888-1896,2161-2175`, `erp_ai_setting.py:1-14,265-316` (grep import/def), `erp_ai/agent/` (ls; `__init__.py` rỗng), grep `splitlines()` trên `erp_ai/` (6 bản tách dòng: `alerts.py:8`, `policy.py:109`, `erp_ai_setting.py:257,315,374,411`); `.team/profile.json` (`structure`, `protected_paths`, `cmd.test_one`).
