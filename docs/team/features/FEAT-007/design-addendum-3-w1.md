Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Không có cổng cho tài liệu này (team.py: chỉ G5). Để trống. -->

# Thiết kế phụ lục 3, đợt 1 (U1, U4b, U6b, U8 AC-62/63): một hướng xử lý mỗi phiếu, bỏ câu chờ "ok"

**Quy tắc đọc.** Ở mọi dòng được nêu dưới đây, file này **thắng** `design-addendum-1-U1.md`, `design-addendum-1-U4b-U8.md` và `design-addendum-1-U6b.md`. Chỗ không nêu thì ba file kia giữ nguyên. Đường dẫn tính từ `docs/team/features/FEAT-007/`, trừ khi ghi khác. Tuân ADR-036 (QĐ 1–9 và Ràng buộc), ADR-030, ADR-033 QĐ 1, 2, 5, 7, ADR-035 QĐ 7, ADR-019 QĐ 2 (bản sửa của ADR-036). Phần U7a, U7b, U8 AC-64 (đợt 2) không nằm ở đây.

## 0. Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Model đăng comment thế nào | `post_comment` gọi `doc.new_comment(args["content"])`, **không** thoát HTML | `erp_ai/agent/tools/write_ticket.py:102-112` |
| `new_comment` tạo gì | `Comment`, `comment_type = "Comment"` qua `add_comment` | `helpdesk/.../hd_ticket.py:617-629` |
| `Comment.content` có bị lọc không | `HTML Editor`, `ignore_xss_filter: 1`: lưu nguyên, chú thích HTML `<!-- … -->` còn nguyên | `frappe/core/doctype/comment/comment.json:88-90` |
| `ToolContext` | dataclass của U1 trong `registry.py`; `registry.py` ngoài file của U4b | `erp_ai/agent/tools/registry.py:13-23`; `design-addendum-1-U4b-U8.md:333` |
| Bước định tuyến đăng comment ở đâu | `_route` → `_comment_unit` → `post_routing_comment` | `erp_ai/agent/runner.py:337-366`, `:468-482` |
| Vòng suy luận, chỗ ghi dòng `reason` | lỗi cổng `:629-638` (`return`); mỗi lượt `write_entry` `:652-663`; dừng `:664-665` | `runner.py:584-667` |
| Tool đề xuất code ghi dòng `propose` | `_run_tool`, `PROPOSE_TOOLS` | `runner.py:689-700` |
| Prompt quy tắc 6, VIẾT COMMENT | `:104-106`, `:119-132` | `erp_ai/agent/prompts.py:84-132` |
| Khóa chống trùng hiện thiết kế | khóa phiếu `get_value(..., for_update=True)` rồi `SELECT` thường | `design-addendum-1-U4b-U8.md:87`, `:172`, `:174`, `:175` |

## 1. Quyết định chung (tên và hình dạng ADR-036 để designer chốt)

Mọi tên mới nằm trong `erp_ai/agent/tools/write_ticket.py` (file của U4b; ADR-036 QĐ 1 "trong `erp_ai/agent/tools/`"). Không file nguồn mới, không trường mới, không migration (QĐ 6).

```python
# write_ticket.py (U4b)
_GUIDANCE_KEY = "erp_ai:huong-xu-ly"
GUIDANCE_MARKER = f"<!-- {_GUIDANCE_KEY} -->"        # dấu hiệu: dòng 1 của comment hướng; định nghĩa đúng một chỗ
SECTION_DONE, SECTION_PENDING, SECTION_DECIDE = "Đã làm", "Chờ duyệt", "Cần ai quyết"
GUIDANCE_SECTIONS = (SECTION_DONE, SECTION_PENDING, SECTION_DECIDE)
GUIDANCE_HEADER = "Hướng xử lý"
GUIDANCE_FALLBACK = ("**Nhận định:** bot chưa viết được nhận định cho phiếu này; việc bot đã làm và việc đang chờ ở dưới.\n"
                     "**Hướng xử lý:** người phụ trách xem các mục dưới; cần bot làm tiếp thì nhắc @ai.")
REASON_MARKER = "nội dung chứa dấu hiệu dành riêng cho comment hướng xử lý của hệ thống; bỏ dấu hiệu đó"
REASON_GUIDANCE_EXISTS = "phiếu đã có hướng xử lý"
REASON_GUIDANCE_HEADER = "phiếu đã có hướng xử lý: chỉ báo kết quả việc vừa làm, không viết mục 'Hướng xử lý'"
HELD_NOTE = "đã giữ làm nhận định của comment hướng xử lý; bot đăng một lần ở cuối lần chạy"

def locked_count(ticket_name: str, doctype: str, filters: dict) -> int
def guidance_filters(ticket_name: str) -> dict
def count_guidance(ticket_name: str, *, lock: bool = False) -> int
def open_collector(run_id: str) -> None
def collecting(run_id: str) -> bool
def collect(run_id: str, section: str, line: str) -> None
def hold_analysis(run_id: str, content: str) -> None
def collected(run_id: str) -> tuple[str | None, dict[str, list[str]]]
def close_collector(run_id: str) -> None
def mark_work_only(run_id: str) -> None
def post_guidance(ticket_name: str, run_id: str) -> dict
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `locked_count` | (1) `frappe.db.get_value("HD Ticket", ticket_name, "name", for_update=True)`; None → `ValueError("phiếu không có")`. (2) `len(frappe.db.get_values(doctype, filters, "name", for_update=True))`: đọc có khóa, thấy bản đã commit mới nhất dưới `REPEATABLE READ` (ADR-036 QĐ 4). Khóa giữ tới commit kế của giao dịch | `ValueError` |
| `guidance_filters` | `{"reference_doctype": "HD Ticket", "reference_name": t, "comment_type": "Comment", "owner": AGENT_USER, "content": ["like", GUIDANCE_MARKER + "%"]}`: dấu hiệu phải ở **vị trí 0**, nên chữ model nằm giữa một comment khác (đề xuất FEAT-004, BA note) không bao giờ được đếm. Dòng `Info` (ADR-035 QĐ 7) bị loại bởi `comment_type` | — |
| `count_guidance` | Hàm đếm duy nhất (QĐ 3). `lock=False` → `frappe.db.count("Comment", guidance_filters(t))` (chỉ runner dùng ở đầu lần chạy để chọn chế độ, QĐ 7). `lock=True` → `locked_count(t, "Comment", guidance_filters(t))` | — |
| bộ gom | Sống trong `frappe.flags.erp_ai_guidance[run_id] = {"analysis": None, SECTION_DONE: [], SECTION_PENDING: [], SECTION_DECIDE: []}` (cùng mẫu `asked_in_run`, A-U4b-8; `ToolContext` là của U1 nên không thêm trường). `collect` khi `not collecting(run_id)` → không làm gì. `hold_analysis` thay nhận định cũ (lần giữ sau thắng). `collected` trả `(analysis, {mục: dòng})`. `close_collector` xóa khóa; runner gọi trong `finally` | `collect` với `section ∉ GUIDANCE_SECTIONS` → `ValueError` |
| `mark_work_only` | thêm `run_id` vào `frappe.flags.erp_ai_work_only_runs` (lần chạy trên phiếu đã có hướng) | — |
| `post_guidance` | Hàm ghi duy nhất (QĐ 1), không phải `ToolSpec`. (1) `n = count_guidance(t, lock=True)`; `n > 0` → `{"ok": False, "reason": REASON_GUIDANCE_EXISTS}`, không ghi. (2) `analysis, sections = collected(run_id)`; `analysis` None và mọi mục rỗng → `{"ok": False, "reason": "không có nội dung"}`, không ghi (lần chạy sau còn được đưa hướng). (3) Thân = `GUIDANCE_MARKER + "\n" + (analysis or GUIDANCE_FALLBACK)`, rồi mỗi mục khác rỗng: `"\n<p><strong>{mục}:</strong></p><ul>" + "".join(f"<li>{escape_html(d)}</li>") + "</ul>"`. (4) đăng qua `_post(t, content)` (hàm tách ở U4b `:172`). Trả `{"ok": True, "comment": name, "counts": {mục: len}}` | quyền như `post_comment` → `{"ok": False, …}` |

**Phần nhận định do model viết (ADR-036 "Phải làm thêm").** Đi qua `post_comment` `kind="de_xuat"`. Trong lần chạy đưa hướng (`collecting(ctx.run_id)`), tool kiểm như nay (độ tin cậy, Căn cứ), rồi **giữ** nội dung cho hàm ghi thay vì đăng. Không thêm `kind`, không đổi schema. Không chọn "văn bản cuối lượt": model hôm nay viết qua tool, và văn bản cuối lượt thường là câu ngắn ngoài phiếu.

**Chế độ của lần chạy (QĐ 7).** Runner đọc `count_guidance(t)` một lần sau khi dựng context. Lần chạy là **lần đưa hướng** ⇔ số đếm = 0 ∧ `context.main_path_level != "L0"` ∧ `not context.below_threshold` (sau khi biết phân loại). Đưa hướng → `open_collector(run_id)`. Phiếu đã có hướng → `mark_work_only(run_id)`, đưa `guidance_posted=True` vào thông điệp đầu, và ghi 1 dòng logger `"erp_ai guidance ticket=%s run_id=%s: đã có hướng xử lý"` (AC-65 (c)). Dưới ngưỡng → không mở bộ gom, chỉ hỏi như U4b (AC-65 (b)).

**Lần chạy lỗi sau bước định tuyến (chốt một).** Các dòng đã gom vào **thông báo lỗi** `run_failed` của chính lần chạy: thêm câu `"\nTrước khi lỗi, bot đã làm: {dòng nối bằng '; '}"`. Không dồn vào "Đã làm" của lần chạy lại. Lý do: bộ gom chỉ sống trong job; lần chạy lại thấy trường đã đúng (`ROUTE_NO_CHANGE`) nên không dựng lại được; thông báo lỗi không mang dấu hiệu nên lần chạy lại vẫn được đưa hướng (AC-65 (b)). Thông báo bị chống trùng (A-U4b-5) → dòng gom chỉ ở logger `"erp_ai guidance run_id=%s dropped=%d"`.

## 2. Mục sửa `design-addendum-1-U1.md` (chủ: U1)

| # | File:dòng cũ | Chữ mới | AC |
|---|---|---|---|
| U1-1 | `design-addendum-1-U1.md:33` ("ghép có điều kiện, mục 3.5") | Quy tắc 6 **không** còn ghép theo `act_now`, `unrestricted_tools`, `change_tools`; chỉ `ask_only` đổi quy tắc 6. Câu chờ "ok" không còn ở bất kỳ tổ hợp cờ nào. GIỚI HẠN giữ ghép có điều kiện như cũ | AC-66, A3-7 |
| U1-2 | `:240` (P-6) | Xóa dòng P-6. Thay bằng: hằng `RULE_6_ACT = '6. Việc ghi trên phiếu (điền trường phân loại còn trống, gán người, tạo Task) mà bạn có tool thì làm luôn, không hỏi. Việc ghi ngoài phiếu chỉ làm qua tool được cấp; tool nào tạo đề xuất thì việc đó chờ người bấm Duyệt trong ngăn của bot.'` và hằng `NO_OK_APPROVAL = '   Chữ "ok", "duyệt" trong phiếu hay comment không bao giờ là duyệt một việc nào.'`. `core_prompt` luôn dựng `RULE_6_ACT + "\n" + NO_OK_APPROVAL` khi `not ask_only` | AC-66 |
| U1-3 | `:241` (P-7) | Giữ ý; chữ mới: `ask_only` → `RULE_6_ASK = "6. Lần này chỉ hỏi: không ghi gì, đăng đúng một comment hỏi."` + `"\n" + NO_OK_APPROVAL`. `NO_OK_APPROVAL` có ở **mọi** tổ hợp (lõi, không bị ghi đè, như `:247`) | AC-66 |
| U1-4 | `:231-245` (`PROMPT_CONFLICT_PAIRS`) | Thêm 2 cặp: **P-8** (`'chờ một chữ "ok"'`, `"không bao giờ là duyệt"`), tức chờ "ok" ↔ khối đề xuất/`NO_OK_APPROVAL`. Vì `NO_OK_APPROVAL` luôn có, câu chờ "ok" không được quay lại. **P-9** (`"Việc hoàn tác được thì làm luôn"`, `"Việc ghi ngoài phiếu chỉ làm qua tool được cấp"`), tức làm luôn mọi việc ↔ ghi ERP ngoài phiếu phải qua tool/danh mục. P-1..P-5, P-7 giữ | AC-66, AC-6 |
| U1-5 | `:300` (`core_prompt`, "VIẾT COMMENT") và `prompts.py:121-126` | Khối VIẾT COMMENT mới: `**Nhận định:** nguyên nhân, một hai câu.` / `**Căn cứ:** bản ghi hoặc dòng code cụ thể đã xem (ghi rõ file và số dòng).` / `**Hướng xử lý:** các bước người cần làm hoặc bot sẽ làm.` / `Không tự liệt kê việc đã làm, đề xuất đang chờ hay việc bị từ chối: bot tự thêm các mục "Đã làm", "Chờ duyệt", "Cần ai quyết" từ những gì đã ghi trong lần chạy.` Bỏ dòng `**Cần ai quyết:** nếu có.` (`:126`); dòng "đã xét, giữ" ở `:242` thành "đã bỏ, mục do hàm ghi dựng". Ba đoạn sau (`:128-132`) giữ nguyên chữ. Ghi đè `reasoning` của U7 vẫn chỉ thay quy tắc 1–5 và VIẾT COMMENT (`:300` giữ câu đó) | AC-65 (a), AC-23 `[changed]` |
| U1-6 | `:223` (`CORE_PROMPT = core_prompt()` "bằng từng byte chuỗi hiện nay") | `CORE_PROMPT = core_prompt()`, bằng chuỗi cũ **trừ** quy tắc 6 (U1-2) và VIẾT COMMENT (U1-5). Quy tắc 1–5 và GIỚI HẠN giữ từng byte | AC-66, AC-6 |
| U1-7 | `:402` (ma trận AC-6) | Thêm hàng: `test_no_wait_for_ok_five_switches_off_l1_to_l3`, dựng qua `grant` (5 công tắc tắt × L1, L2, L3) → `build_reason_system`. Assert: không có `'chờ một chữ "ok"'`, không có `"Việc hoàn tác được thì làm luôn"`, có `NO_OK_APPROVAL` | AC-66, AC-6 |
| U1-8 | `:403` (`test_default_core_prompt_unchanged`, ghim chuỗi cũ) | Đổi thành `test_default_core_prompt_keeps_rules_1_5_and_limits`: phần trước dòng `6.` và khối GIỚI HẠN bằng từng byte bản cũ; quy tắc 6 = `RULE_6_ACT` + `NO_OK_APPROVAL`; VIẾT COMMENT = khối U1-5. Lý do trong commit: "spec đổi (AC-66, AC-65 (a)); NFR-8, STD-TEST-5". Test không chép chuỗi mới, chỉ dùng hằng | AC-66 |

Ghi chú thứ tự: U1 merge trước U4b, nên giữa hai lần merge VIẾT COMMENT đã nói "bot tự thêm các mục" mà hàm ghi chưa có. `develop` không deploy prod giữa hai lần merge (FEAT-007 chỉ cổng G5), nên chấp nhận (A-W1-4).

## 3. Mục sửa `design-addendum-1-U4b-U8.md`, phần U4b (chủ: U4b)

| # | File:dòng cũ | Chữ mới | AC |
|---|---|---|---|
| U4b-1 | `design-addendum-1-U4b-U8.md:27` | "tách: hàm nội bộ `_post` giữ thân; tool `post_comment` có `kind`, kiểm 'Độ tin cậy'/'Căn cứ'/BA note, **từ chối dấu hiệu ở mọi `kind`**, giữ `de_xuat` cho hàm ghi trong lần đưa hướng; thêm mục 1 của file này (dấu hiệu, hàm đếm, hàm ghi, bộ gom, `locked_count`)" | AC-65 (a), (d) |
| U4b-2 | `:34` ("đúng 1 comment gộp cho định tuyến thành công") | "lần đưa hướng: câu định tuyến vào bộ gom, 0 comment định tuyến riêng; lần chạy không đưa hướng: 1 comment gộp như cũ" | AC-23 `[changed]`, AC-65 |
| U4b-3 | `:83` (bảng dữ liệu, dòng Comment) | Thay dòng bằng hai dòng. (a) "Comment hướng xử lý (`Comment`, `owner = AGENT_USER`, `content` bắt đầu bằng `GUIDANCE_MARKER`) \| ghi: `post_guidance`; đếm: `count_guidance` \| runner \| lọc `reference_name`, `comment_type`, `owner`, `content LIKE '<dấu hiệu>%'`; ≤ 1 mỗi phiếu". (b) "Comment khác của agent \| ghi; đọc chống trùng **có khóa** qua `locked_count` \| `post_comment_tool`, `post_notice`, BA note \| như cũ". Bảng khóa `:87-97`: câu đầu đổi thành "giữ khóa bằng `locked_count` (khóa dòng phiếu + đọc có khóa)"; thêm hàng "Hướng xử lý (AC-65) \| (phiếu, comment agent bắt đầu bằng dấu hiệu) \| không ghi, `REASON_GUIDANCE_EXISTS`, 1 dòng logger" | AC-65, AC-23, AC-62; NFR-3 |
| U4b-4 | `:146-147` (chữ ký) | Thêm khối chữ ký mục 1 của file này sau `:148`. `post_comment` giữ: hàm nội bộ, `route_ticket` vẫn gọi | AC-65 |
| U4b-5 | `:170` (`post_comment`) | Giữ. Thêm câu: "không kiểm dấu hiệu: chỉ mã gọi (`route_ticket`, `_post`); chữ model không qua đây" | AC-65 (d) |
| U4b-6 | `:171` (`post_comment_tool`) | Thứ tự mới: **(0)** `_GUIDANCE_KEY in re.sub(r"\s+", "", content).lower()` → `_fail(REASON_MARKER)`, mọi `kind`, trước mọi kiểm khác; **(1)** `kind`; **(2)** dưới ngưỡng như cũ; **(3)** `de_xuat` kiểm như cũ; **(3b)** `ctx.run_id ∈ frappe.flags.erp_ai_work_only_runs` ∧ `section_text(content, GUIDANCE_HEADER)` khác rỗng → `_fail(REASON_GUIDANCE_HEADER)`; **(3c)** `kind == "de_xuat"` ∧ `collecting(ctx.run_id)` → `hold_analysis(ctx.run_id, content)`, trả `{"ok": True, "held": True, "note": HELD_NOTE}`, 0 Comment; **(4)** `hoi` trên ngưỡng: đăng riêng như cũ (câu hỏi không phải hướng, AC-65); **(5)** đăng bằng `_post` | `{"ok": False, …}`; 0 Comment |
| U4b-7 | `:172` (`post_notice`) | "Kiểm `notice`; `n = locked_count(ticket_name, "Comment", {reference_doctype, reference_name, comment_type: "Comment", owner: AGENT_USER, creation: [">=", since], content: ["like", prefix + "%"]})`; `n > 0` → `REASON_NOTICE_SENT`; ngược lại `_post`". Bỏ khóa và `SELECT` riêng | AC-23, NFR-3 (AR3-7) |
| U4b-8 | `:173` (`set_classification`) | Thêm: thành công ∧ `collecting(ctx.run_id)` → `collect(run_id, SECTION_DONE, ROUTE_DONE.format(...))` (dùng `FIELD_LABELS`; hằng chuyển từ runner sang `write_ticket.py`, runner import lại) | AC-23, AC-66 (a) |
| U4b-9 | `:182` (schema `post_comment`) | Mô tả thêm: "Không tự viết mục Đã làm/Chờ duyệt/Cần ai quyết. Khi phiếu đã có hướng xử lý: chỉ báo kết quả việc vừa làm." Schema (tham số) không đổi | AC-65 (a), (c) |
| U4b-10 | `:203` sau (prompts, `build_initial_message`) | Thêm tham số `guidance_posted: bool = False`; True → `payload["ticket"]["guidance_posted"] = True` và ghép `"\n" + TASK_AFTER_GUIDANCE` sau dòng việc, với `TASK_AFTER_GUIDANCE = "Phiếu đã có comment Hướng xử lý của bot. Chỉ làm việc người vừa nhờ và báo kết quả; không viết lại hướng xử lý."`. False → payload trùng bản U4b. Là dữ liệu phiếu, không phải cấu hình (ADR-030, ADR-036 QĐ 7) | AC-65 (c) |
| U4b-11 | `:236-238` (`_run`) | Sau khi dựng context (mức > L0): `posted = write_ticket.count_guidance(t) > 0`. Lần tạo phiếu: quyết sau `_classify` parse, **trước** `_route`. Lần khác: quyết sau context. `guidance_run = not posted and context.main_path_level != "L0" and not context.below_threshold` → `open_collector(run_id)`. `posted` → `mark_work_only(run_id)` + 1 dòng logger mục 1. `finally` của `_run`: `close_collector(run_id)` | AC-65 (a), (c) |
| U4b-12 | `:242` (`_classify` lỗi cổng) | Giữ; thêm câu: "chưa có `_route` nên bộ gom rỗng, thân thông báo không có câu 'Trước khi lỗi'" | AC-65 (b), AC-23 |
| U4b-13 | `:246` (`_route`) | Thêm tham số `collect_run_id: str \| None = None`. None → **như cũ** (1 comment; test FEAT-006 gọi `_route` trực tiếp giữ xanh). Có và `collecting(...)` → không gọi `_comment_unit`: `_route_lines(...)` → `collect(SECTION_DONE, …)`; các câu khác trong `lines` (cảnh báo SLA, gán lỗi, nhờ trưởng nhóm, `split_text`) → `collect(SECTION_DECIDE, …)`; không mục `post_routing_comment` | AC-23 `[changed]`, AC-65 |
| U4b-14 | `:251` (`_reason` lỗi cổng) | Mục `_notice(…, "run_failed", RUN_FAILED_BODY.format(…) + _done_suffix(run_id), …)` với `_done_suffix` = `"\nTrước khi lỗi, bot đã làm: " + "; ".join(dòng của ba mục)` khi bộ gom có dòng, ngược lại `""`. `_reason` trả `False`. Thông báo bị chống trùng → logger `dropped` (mục 1) | AC-65 (b), AC-23 |
| U4b-15 | `:252` (`_reason` lượt cuối) | Giữ nhánh `ask_fallback`. Thêm: `final ∧ write_ticket.collecting(run_id)` → `_finish_guidance(context, actions)` **trước** `write_entry` của lượt cuối. Đây là **chỗ duy nhất** runner gọi `write_ticket.post_guidance`. `_finish_guidance`: `r = post_guidance(t, run_id)`. `ok` → `actions.append(run_log.action_entry(GUIDANCE_TOOL, "Comment", r["comment"], True, value_after={"counts": r["counts"]}, instructor=…))`, với `GUIDANCE_TOOL = "post_guidance"`. `REASON_GUIDANCE_EXISTS` (lần chạy song song đã đăng trước) → logger mục 1; bộ gom có dòng → đăng 1 comment kết quả **không dấu hiệu** qua `post_routing_comment(dòng, context)` + mục `post_routing_comment` (AC-23 "lần chạy không đưa hướng báo như trước"). "không có nội dung" → logger `"erp_ai guidance run_id=%s skipped=no_content"`, 0 mục. `_reason` trả `True` | AC-65 (a), (c), AC-23 |
| U4b-16 | `runner.py` `_run_tool` (`design-addendum-1-U4b-U8.md:375`: U4b "—") | U4b sửa hai chỗ. (a) `outcome.get("held")` → không thêm mục hành động: không ghi gì, ADR-036 QĐ 8. (b) `name ∈ PROPOSE_TOOLS ∧ ok ∧ collecting(run_id)` → `collect(SECTION_PENDING, PENDING_LINE.format(proposal=outcome["proposal"], label=PROPOSE_LABELS[name]))`, với `PENDING_LINE = "Đề xuất {proposal} ({label}) đang chờ duyệt trong ngăn của bot."`, nhãn cố định theo tên tool, không chép tham số (B-3). Đề xuất bản ghi của U7 nối dòng cùng cách ở đợt 2 | AC-23, AC-65 (a), AC-67 (phần đợt 1) |
| U4b-17 | `:277` (luồng happy path) | Đoạn "… 1 comment 'Bot đã phân loại phiếu …' → `_reason` …" thành: "… `_route` gom câu định tuyến (0 comment) → `_reason`: model `post_comment(kind=de_xuat)` → giữ → tool ghi phiếu, Task, đề xuất code → dòng vào bộ gom → lượt cuối `post_guidance`: khóa phiếu, đếm có khóa = 0, đăng **1** comment (dấu hiệu, nhận định, Đã làm, Chờ duyệt, Cần ai quyết) → mục `post_guidance` trong dòng `reason` cuối" | AC-65, AC-23 |
| U4b-18 | `:279` (dưới ngưỡng) | Giữ; thêm "không mở bộ gom, 0 hướng; câu hỏi không mang dấu hiệu" | AC-65 (b) |
| U4b-19 | `:289-297` (bảng lỗi) | Thêm hàng. "Lỗi cổng ở suy luận sau `_route` thành công: 1 comment lỗi có 'Trước khi lỗi, bot đã làm: …', 0 hướng; lần chạy lại đưa hướng". "Phiếu đã có hướng, `@ai` không việc nào: 0 comment, 1 dòng logger 'đã có hướng xử lý'". "Tạo phiếu ∥ `@ai`, cả hai đếm 0 ở đầu: `post_guidance` tuần tự hóa bằng khóa; lần sau → comment kết quả không dấu hiệu". `:297`: "khóa dòng phiếu + đọc có khóa qua `locked_count` trong `post_notice`, BA note, `create_task`, `post_guidance`" | AC-65, AC-23, NFR-3 |
| U4b-20 | `:291` (lỗi cổng) | "dòng có `error` + 1 comment (có câu 'Trước khi lỗi' khi bộ gom có dòng); lỗi tiếp theo trước lần thành công kế → 0 comment" | AC-23, AC-65 (b) |
| U4b-21 | `:466` (A-U4b-5) | Thêm vào cột "Chọn": "thân có câu 'Trước khi lỗi, bot đã làm' từ bộ gom (mục 1 file này)" | AC-65 (b), AC-23 |
| U4b-22 | `:318` (quan sát) | Thêm: mục `post_guidance` (`value_after.counts`); mục `post_comment` `ok=false` `REASON_MARKER`/`REASON_GUIDANCE_HEADER`; logger `erp_ai guidance … đã có hướng xử lý`, `skipped=no_content`, `dropped=n`. Đối chiếu sau deploy: `SELECT reference_name, COUNT(*) FROM tabComment WHERE content LIKE '<!-- erp_ai:huong-xu-ly -->%' GROUP BY 1 HAVING COUNT(*) > 1` → 0 dòng | STD-OPS-5; AC-65 |

**Quét bù (NFR-2, ADR-036 "Phải làm thêm").** Không đổi tiêu chí chọn phiếu, không đọc dấu hiệu ở `tasks.py`. Phiếu có hướng thì đã có dòng thành công, nên bình thường không bị xếp lại. Nếu bị xếp lại (biên), lần chạy ở chế độ chỉ làm việc: 0 comment, 1 dòng logger.

## 4. Mục sửa `design-addendum-1-U4b-U8.md`, phần U8 AC-62/63 (chủ: U8, sau U4b)

| # | File:dòng cũ | Chữ mới | AC |
|---|---|---|---|
| U8-1 | `:174` (`create_task`) | "khóa dòng phiếu (như `post_notice`); trùng …" thành "`locked_count(t, "Task", {"ai_ticket": t, "subject": subject.strip()})` > 0 → `REASON_TASK_DUPLICATE` (tên Task đọc sau, cùng khóa)". Thêm: tạo thành công ∧ `collecting(ctx.run_id)` → `collect(SECTION_DONE, "Đã tạo Task {task} ({hours} giờ).")`; không gọi hàm đăng comment nào | AC-63, AC-23, AR3-7 |
| U8-2 | `:175` (`ba_note`) | "khóa dòng phiếu; đã có comment agent bắt đầu bằng `BA_NOTE_MARKER`" thành "`locked_count(t, "Comment", {…, "content": ["like", BA_NOTE_MARKER + "%"]})` > 0 → `REASON_BA_NOTE_EXISTS`". Bước (0) dấu hiệu (U4b-6) chạy trước, nên BA note không bao giờ mang dấu hiệu. BA note **đăng riêng** cả trong lần đưa hướng (A3-9: không phải hướng; U5a cần dòng 1 = marker); không giữ vào bộ gom | AC-62, AC-65, A3-9 |
| U8-3 | `:283` (luồng phiếu C) | Thêm: "trong lần đưa hướng: BA note là 1 comment riêng, không dấu hiệu; Task → dòng 'Đã làm' của comment hướng" | AC-62, AC-63, AC-65 |

## 5. Mục sửa `design-addendum-1-U6b.md` (chủ: U6b, merge sau U4b)

| # | File:dòng cũ | Chữ mới | AC |
|---|---|---|---|
| U6b-1 | `design-addendum-1-U6b.md:425-432` (bảng test AC-41) | Thêm hai hàng sau `:431`: `erp_ai/agent/test_agent_runner.py::TestRequesterReplyRun::test_reply_after_guidance_no_new_guidance` (phiếu có comment hướng; người tạo trả lời → 1 job, chạy, `count_guidance` = 1, 0 Comment có dấu hiệu mới, nếu không có việc thì 1 dòng logger "đã có hướng xử lý") và `…::test_reply_after_low_confidence_question_posts_guidance` (lần 1 dưới ngưỡng: 1 câu hỏi, 0 hướng; người tạo trả lời, lần 2 đạt ngưỡng → `count_guidance` = 1). U6b **không** tự kiểm "đã có hướng" ở handler hay trigger: handler chỉ xếp hàng (ADR-033 QĐ 2, ADR-036 QĐ 7); chế độ do runner của U4b chọn | AC-41 `[changed]`, AC-65 |

Ca thứ hai cần lần chạy trả lời vượt được ngưỡng. Xem điểm mở OI-1.

## 6. Touchpoint theo đơn vị và thứ tự merge

| File | Chủ (đơn vị) | Phần sửa trong file này |
|---|---|---|
| `erp_ai/agent/prompts.py` | U1: `core_prompt`, hằng quy tắc 6, `NO_OK_APPROVAL`, VIẾT COMMENT, `PROMPT_CONFLICT_PAIRS` | U1-1..U1-6 |
| `erp_ai/agent/prompts.py` | U4b: `build_initial_message` (`guidance_posted`), `TASK_AFTER_GUIDANCE` | U4b-10 |
| `erp_ai/agent/tools/write_ticket.py` | U4b: mục 1 (dấu hiệu, `locked_count`, `count_guidance`, bộ gom, `post_guidance`), `post_comment_tool` (0), (3b), (3c), `post_notice`, `set_classification`, `FIELD_LABELS`/`ROUTE_DONE` chuyển vào | U4b-1, -3..-8 |
| `erp_ai/agent/tools/write_ticket.py` | U8: `create_task`, nhánh `ba_note` qua `locked_count` | U8-1, U8-2 |
| `erp_ai/agent/runner.py` | U4b: `_run` (chế độ, `finally`), `_route` (`collect_run_id`), `_reason` (trả bool, lượt cuối, lỗi cổng), `_finish_guidance`, `_done_suffix`, `_run_tool` (held, Chờ duyệt), `GUIDANCE_TOOL`, `PENDING_LINE`, `PROPOSE_LABELS` | U4b-11..-16 |
| `erp_ai/agent/test_prompts.py` | U1 | mục 7 (AC-6, AC-66) |
| `erp_ai/agent/tools/test_write_ticket.py` | U4b, rồi U8 | mục 7 |
| `erp_ai/agent/test_agent_runner.py` | U4b, rồi U6b, U8 | mục 7 |
| `erp_ai/agent/test_runner_routing.py` | U4b | mục 7 |
| `erp_ai/tests/test_architecture.py` | U4b | mục 7 (Ràng buộc ADR-036) |

Không sửa: `registry.py`, `handlers.py` (cho ADR-036), `route_ticket.py`, `queue.py`, `tasks.py`, `policy.py`. File chạm của mỗi đơn vị khớp `arch-impact.md` (`arch-review-addendum-3.md` mục 7, "File chạm của mỗi đơn vị không đổi").

**Thứ tự merge đợt 1:** U1 (một mình) → U2 ∥ U3 → **U4b** → U6b, U8 (song song với nhau, cả hai **merge sau U4b**). U6b build được song song, nhưng hai test AC-41 mới chỉ chạy sau khi U4b vào `develop`. Task chèn AR3-3 / T10 / T2 (tech-lead) không đụng file nào ở trên.

**So khớp đường dẫn:**
```
new: docs/team/features/FEAT-007/design-addendum-3-w1.md -> prefix "docs/" khớp allowed_new_file_roots ["erp_ai", "docs", ".github"]
new code/test: không có
modified (3 nguồn + 5 test, đều dưới erp_ai/): so protected_paths [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"] -> không file nào khớp
```

## 7. Test theo AC

Chạy từng file bằng `cmd.test_one`, cả app bằng `cmd.test`. Stub cổng model, không mạng (STD-TEST-6). Mọi số đếm "hướng" dùng `write_ticket.count_guidance` (ADR-036 QĐ 3).

| AC | Test (`file::Class::name`) | Ca / biên |
|---|---|---|
| AC-65 chuỗi 1 | `erp_ai/agent/test_agent_runner.py::TestOneGuidance::test_chain_1_ticket_insert_one_guidance` | tạo phiếu → 1 |
| AC-65 chuỗi 2 | `…::TestOneGuidance::test_chain_2_insert_then_ai_three_times_one_guidance` | tạo + `@ai` ×3 (stub cố đăng `de_xuat` mỗi lần) → 1; 3 dòng logger "đã có hướng xử lý" hoặc comment kết quả không dấu hiệu |
| AC-65 chuỗi 3 | `…::TestOneGuidance::test_chain_3_low_confidence_reply_then_guidance` | pct 69 → 1 câu hỏi, 0 hướng; người tạo trả lời; lần sau đạt ngưỡng → 1 câu hỏi + 1 hướng (phụ thuộc OI-1) |
| AC-65 chuỗi 4 | `…::TestOneGuidance::test_chain_4_sweep_after_success_one_guidance` | gọi quét bù sau lần chạy thành công → 1 |
| AC-65 chuỗi 5 | `…::TestOneGuidance::test_chain_5_failed_run_then_rerun_one_guidance` | lần 1 lỗi cổng ở suy luận sau `_route` → 0 hướng, 1 comment lỗi có "Trước khi lỗi, bot đã làm"; chạy lại → 1 |
| AC-65 chuỗi 6 | `…::TestOneGuidance::test_chain_6_guidance_then_approve_one_guidance_one_result` | đề xuất code FEAT-004 trong "Chờ duyệt"; Duyệt → 1 dòng `Info`; `count_guidance` = 1 |
| AC-65 chuỗi 7 | `…::TestOneGuidance::test_chain_7_ai_after_guidance_creates_task_no_new_guidance` | Task có; 1 comment kết quả không dấu hiệu; đếm 1 |
| AC-65 chuỗi 8 | `…::TestOneGuidance::test_chain_8_level_l0_or_excluded_team_zero` | subTest L0; nhóm loại trừ → 0 |
| AC-65 chuỗi 9 | `…::TestOneGuidance::test_chain_9_empty_prompt_two_runs_one_guidance` | patch `build_reason_system` trả `""` (ghi đè rỗng; bản U7 thêm ca ghi đè thật ở đợt 2); lần 2 stub gọi `post_comment` có `GUIDANCE_MARKER` → `ok=false`; đếm 1 |
| AC-65 (a) | `…::TestOneGuidance::test_guidance_has_analysis_done_pending_decide` | dòng 1 = dấu hiệu; nhận định của model; mục rỗng không hiện |
| AC-65 (a) | `…::TestOneGuidance::test_no_analysis_with_done_items_uses_fallback`, `::test_no_analysis_no_items_posts_nothing` | `GUIDANCE_FALLBACK`; 0 comment, logger `no_content`, lần sau vẫn đưa hướng |
| AC-65 (c) | `…::TestOneGuidance::test_ai_after_guidance_no_work_no_comment_one_log_line` | 0 Comment; đúng 1 dòng logger chứa "đã có hướng xử lý" |
| AC-65 (c) | `erp_ai/agent/tools/test_write_ticket.py::TestGuidanceWriter::test_work_only_run_guidance_header_refused` | nội dung có `**Hướng xử lý:**` → `REASON_GUIDANCE_HEADER`, 0 Comment |
| AC-65 (d) | `…test_write_ticket.py::TestGuidanceWriter::test_post_comment_marker_refused_every_kind` | `de_xuat`, `hoi`, `ba_note` → `ok=false` `REASON_MARKER`, 0 Comment |
| AC-65 (d) | `…::TestGuidanceWriter::test_marker_case_and_spacing_variants_refused` | hoa thường, khoảng trắng trong `<!-- … -->` |
| AC-65 (d), QĐ 8 | `erp_ai/agent/test_agent_runner.py::TestOneGuidance::test_marker_refusal_one_failed_action_entry` | 1 mục `post_comment` `ok=false` có `reason` |
| AC-65, QĐ 4 | `…test_write_ticket.py::TestGuidanceWriter::test_concurrent_snapshot_does_not_double_post` | hai kết nối DB: giao dịch 1 đọc trước (ảnh chụp); giao dịch 2 đăng hướng, commit; giao dịch 1 gọi `post_guidance` → `REASON_GUIDANCE_EXISTS`, 0 comment thêm; `tearDown` xóa bản ghi đã commit |
| AC-65, QĐ 4 | `…::TestGuidanceWriter::test_writer_posts_once_second_call_refused` | |
| AC-65, QĐ 3 | `…::TestGuidanceWriter::test_count_ignores_info_other_owner_and_non_prefix` | dòng `Info`; owner người; dấu hiệu giữa nội dung → không đếm |
| AC-65, QĐ 3 | `…::TestGuidanceWriter::test_marker_survives_save` | đọc lại `content` từ DB bắt đầu bằng dấu hiệu |
| AC-65, QĐ 6 | `…::TestGuidanceWriter::test_deleted_guidance_allows_new_one` | |
| AC-65 (a) | `…::TestGuidanceWriter::test_de_xuat_held_in_guidance_run` | `held`, 0 Comment; lần giữ sau thắng |
| AC-23 `[changed]` +1 | `erp_ai/agent/test_agent_runner.py::TestRunNotices::test_guidance_run_fields_assign_task_proposal_one_routing_comment` | ghi trường, gán, Task, 1 đề xuất code → câu định tuyến nằm trong đúng 1 comment (comment hướng); 0 mục `post_routing_comment`; comment của đề xuất FEAT-004 không đổi số |
| AC-23 `[changed]` | `…::TestRunNotices::test_matrix_eight_situations` (sửa) | "định tuyến thành công → 1" nay là comment hướng có câu định tuyến; 7 ca còn lại giữ |
| AC-23 | `…::TestRunNotices::test_reason_error_after_route_lines_in_failure_notice` | |
| AC-23 | `erp_ai/agent/test_runner_routing.py::TestOneCommentPerAction::test_route_collect_mode_posts_nothing` | `_route(..., collect_run_id=r)` → 0 Comment; Đã làm / Cần ai quyết có đúng câu |
| AC-23 | `…test_runner_routing.py::TestOneCommentPerAction::test_route_success_one_comment_lists_fields_assignee_task` (giữ, chế độ None) | |
| AC-23, AR3-7 | `erp_ai/agent/tools/test_write_ticket.py::TestLockedCount::test_post_notice_sees_comment_committed_after_snapshot` | hai kết nối, như ca QĐ 4 |
| AC-66 | `erp_ai/agent/test_prompts.py::TestCorePrompt::test_no_wait_for_ok_five_switches_off_l1_to_l3` | U1-7 |
| AC-66 | `…test_prompts.py::TestCorePrompt::test_no_ok_approval_in_every_combination` | 2⁴ + `ask_only` → có `NO_OK_APPROVAL` |
| AC-66, AC-6 | `…test_prompts.py::TestCorePrompt::test_no_conflict_pair_in_any_flag_combination` (giữ; nay có P-8, P-9) | |
| AC-66 | `…test_prompts.py::TestCorePrompt::test_default_core_prompt_keeps_rules_1_5_and_limits` (thay `test_default_core_prompt_unchanged`) | U1-8 |
| AC-66 | `erp_ai/agent/test_agent_runner.py::TestDoneInGuidance::test_l1_ticket_only_ticket_fields_and_task` | L1: trường phiếu, Task trong "Đã làm"; 0 đề xuất |
| AC-66 | `…::TestDoneInGuidance::test_item_not_in_both_done_and_pending` | |
| AC-66 | `…::TestDoneInGuidance::test_ok_comment_does_not_approve_pending_proposal` | đề xuất code chờ; comment "@ai ok" → trạng thái đứng yên, 0 job áp dụng |
| AC-41 `[changed]` | U6b-1 (2 test) | |
| AC-62 | `erp_ai/agent/tools/test_write_ticket.py::TestBaNote::test_ba_note_not_counted_as_guidance` | BA note đăng trong lần đưa hướng → comment riêng; `count_guidance` không đổi |
| AC-62 | `…::TestBaNote::test_second_note_refused` (giữ, nay qua `locked_count`) | |
| AC-63 | `erp_ai/agent/test_agent_runner.py::TestCategoryC::test_tasks_in_guidance_run_listed_in_done` | 3 Task → 3 dòng "Đã làm", 0 comment thêm, 3 mục hành động |
| Ràng buộc ADR-036 | `erp_ai/tests/test_architecture.py::test_guidance_marker_defined_once_used_only_by_writer_module`, `::test_runner_calls_post_guidance_in_one_place`, `::test_locked_count_queries_use_for_update`, `::test_dedup_reads_go_through_locked_count`, `::test_handlers_do_not_import_write_ticket`, `::test_no_guidance_flag_field` | AST/grep: hằng 1 chỗ; 1 lời gọi; `get_value(…, for_update=True)` và `get_values(…, for_update=True)` trong `locked_count`; `post_notice`, `ba_note`, `create_task`, `post_guidance` không tự khóa/đọc; không trường chứa `guidance`/`huong` trên HD Ticket, ERP AI Log, ERP AI Setting |

Ca `production` (0 comment "site test" riêng), "Tự làm" trong lần đưa hướng và chống trùng đề xuất bản ghi thuộc U7a/U7b, đợt 2. Hàm `collect`, `locked_count` là hợp đồng cho các đơn vị đó.

Test cũ phải sửa theo AC, ghi lý do trong commit (NFR-8, STD-TEST-5): `test_default_core_prompt_unchanged` (U1-8); `TestRunNotices::test_matrix_eight_situations`, `TestAskOnly::test_stub_69_70_100` (ca 70, 100: "comment định tuyến" → "comment hướng có câu định tuyến"). Test FEAT-006 của `test_runner_routing.py` gọi `_route` trực tiếp **không** đổi (chế độ None). Test FEAT-006 chạy `run_for_ticket` và đếm comment định tuyến: dev liệt kê bằng grep `run_for_ticket` trong file đó, sửa "đếm comment định tuyến = 1" thành "comment hướng có câu định tuyến = 1".

**Đối chiếu AC.** AC giao cho đợt này: AC-65, AC-66, AC-23 `[changed]`, AC-41 `[changed]`, AC-6 (2 cặp), AC-62, AC-63 (phần ADR-036). Có trong bảng trên: AC-65, AC-66, AC-23, AC-41, AC-6, AC-62, AC-63. Khớp 7/7. Phần của AC-66 (b) (`Tự làm` L3, bộ thực thi từ chối → "Cần ai quyết") và AC-67 là của U7a, U7b.

## 8. Chỗ thiết kế lệch ADR-036 QĐ 1–5

Rỗng. Năm điểm dưới đây là lựa chọn ADR để lại cho designer, hoặc là phần bổ sung, không phải lệch:
- QĐ 1: lời gọi duy nhất nằm trong `_reason` ở lượt cuối, trước `write_entry`/commit của lượt đó. Đó là "sau lượt suy luận cuối và trước commit cuối".
- QĐ 2: bộ gom theo `run_id` trong `frappe.flags` (một trong hai chỗ ADR cho phép). Khi thua lần chạy song song, các dòng đã gom đi vào 1 comment kết quả không dấu hiệu (ADR-036 QĐ 2 gạch 2).
- QĐ 3: `post_comment` không thoát HTML, nên chống giả dấu hiệu dựa vào lời từ chối ở bước (0) cộng phép đếm theo tiền tố vị trí 0. Bổ sung: lời từ chối mục "Hướng xử lý" trong lần chạy chỉ làm việc (U4b-6 (3b)). Phép này không thay hàm đếm.
- QĐ 4: đọc có khóa bằng `frappe.db.get_values(..., for_update=True)`.
- QĐ 5: chưa dựng (U7a, đợt 2). `locked_count(t, "ERP AI Change Proposal", …)` là hàm trợ giúp để dùng lại; tập trạng thái chặn do thiết kế U7a chốt.

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-W1-1 | Dấu hiệu = chú thích HTML `<!-- erp_ai:huong-xu-ly -->` ở dòng 1 | `Comment.content` có `ignore_xss_filter` nên lưu nguyên; người đọc không thấy; tiền tố vị trí 0 loại chữ model nằm giữa comment khác | thuộc tính `data-*` (bộ dựng UI có thể bỏ) | đổi một hằng; `test_marker_survives_save` báo |
| A-W1-2 | Nhận định đi qua `post_comment kind=de_xuat`, được giữ trong lần đưa hướng | model đã viết qua tool; giữ luật độ tin cậy và Căn cứ | `kind` mới; văn bản cuối lượt | thêm `kind` vào `COMMENT_KINDS` |
| A-W1-3 | Dòng định tuyến của lần chạy lỗi vào thông báo lỗi | bộ gom không sống qua job; lần chạy lại không dựng lại được | "Đã làm" của lần chạy lại (cần lưu dòng vào log) | đọc `actions` của dòng `classify` ở lần chạy lại |
| A-W1-4 | VIẾT COMMENT mới đi với U1, chấp nhận khoảng U1 → U4b trên `develop` | khối `core_prompt` là của U1 (`:354`); không deploy prod giữa hai lần merge | U4b sửa VIẾT COMMENT (đụng khối của U1) | chuyển U1-5 sang task U4b |
| A-W1-5 | Câu hỏi trên ngưỡng (`hoi`) trong lần đưa hướng vẫn đăng riêng | AC-65 loại câu hỏi khỏi số đếm; AC-23 không liệt kê câu hỏi | gom vào "Cần ai quyết" | giữ `hoi` vào bộ gom ở (3c) |
| A-W1-6 | Không có nhận định và bộ gom rỗng → không đăng, lần sau còn được đưa hướng | một hướng rỗng sẽ tiêu mất "một lần" | đăng câu dự phòng | bỏ nhánh `no_content` |

## Điểm mở cho architect / team-leader

- **OI-1 (cần architect phán).** AC-65 chuỗi 3 và AC-41 ca 2 đòi lần chạy sau câu hỏi dưới ngưỡng được vượt ngưỡng. Thiết kế U1 (`:260`) cho lần chạy không phải tạo phiếu đọc pct của dòng `classify` gần nhất. Như vậy pct 69 giữ mãi, và lần chạy trả lời lại chỉ hỏi. Đề xuất: lần chạy `requester_reply`/`comment_mention` mà pct gần nhất dưới ngưỡng thì phân loại lại, đầu vào thêm tin người tạo sau câu hỏi. Việc này đụng `latest_classification` (U1), vị từ ADR-030 QĐ 4, bước định tuyến ở lần chạy không phải tạo phiếu (ADR-019) và chi phí NFR-2 (thêm 1 lời gọi model). Chưa phán thì hai test này đỏ theo đúng nghĩa: không skip, báo `DESIGN_CONFLICT` khi build.
