Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- G2 tắt cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Đánh giá tác động của CHG-002 (ADR-040) lên phần chưa build của FEAT-007

**Mục tiêu 1. Phần lớn giữ; 3 chỗ sửa thiết kế (U7a); 1 ADR mới (ADR-038, proposed).** CHG-002 không chạm `runner.py`, `write_ticket.py`, `registry.py`, `policy.py`, `site_api.py`. Vì vậy chuỗi U4b ở runner, bộ gom và hàm đếm hướng (ADR-036) giữ nguyên. Ba điều cần giữ để T89, T105 và U7 vẫn đúng:
- `propose_change.py` vẫn có **một** hàm chèn (ADR-031 QĐ 3);
- dòng "Chờ duyệt" mỗi khối vẫn là một dòng;
- `CHANGE_TOOLS_BLOCK` đổi thân nhưng giữ dòng đầu.

Ba chỗ thiết kế U7a phải sửa: thứ tự rẽ nhánh của dấu nội dung, thứ tự rẽ nhánh của job áp dụng, và `pending_line`. Điểm cần ADR: dòng `Info` báo trước restart của CHG-002 là dòng `Info` thứ hai trên phiếu. Nó trái câu "ngoại lệ duy nhất" của ADR-035 QĐ 7 và làm sai cách đếm B-10 của AC-23. ADR-038 xử lý điểm này.

**Mục tiêu 2. Lần gộp `develop` thứ hai là một task riêng, chạy ở vòng đầu tiên sau khi mã CHG-002 vào `develop`.** Ba mốc:
- **Mốc cứng 1:** trước T105 (U4b).
- **Mốc cứng 2:** trước mọi task U7a và trước khi lập plan đợt 2.
- **Mốc mềm:** trước T89 nếu kịp.

Không chọn "cuối đợt 1": khi đó T89, T105 đã viết trên hình dạng cũ, và toàn bộ việc gộp dồn vào một lần ngay trước đợt 2. Không chọn "trước U4b" làm mốc cứng: U4b ở runner không chung file nào với CHG-002. Phần phải kiểm là CI-17..CI-24.

**Mục tiêu 3. Tám yêu cầu cho phiên CHG-002 (RQ-1..RQ-8).** Chủ yếu: giữ một hàm chèn và các tên đang dùng; rẽ nhánh dòng kết quả và bộ chuyển đổi theo `change_kind`; chữ dòng báo trước restart; xóa đủ hai câu cũ của `CHANGE_TOOLS_BLOCK`. Không yêu cầu nào đổi phạm vi hay AC của CHG-002.

Số ADR: dùng ADR-038. Không dùng 040. Số kế cho FEAT-007 là 039, rồi 041 trở đi. Không sửa thân ADR nào.

## Căn cứ (đọc trực tiếp 2026-11-15, read-only; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Đầu hai nhánh | `develop` @ `a689b8d` (chưa có mã CHG-002); `team/FEAT-007` @ `8d694c7` | `git log -1` |
| FEAT-007 đã sửa file mà CHG-002 viết lại chưa | Chưa: `propose_change.py`, `agent/changes/**`, `change_text.py`, DocType đề xuất, `prompts.py` có 0 dòng đổi từ merge-base `1918db2` | `git diff --stat 1918db2 HEAD -- …` (worktree `feat-007`) |
| Hàm chèn hôm nay | `_insert(ctx, values)` là chỗ `insert()` duy nhất (dưới `allow_agent_write`), rồi gọi `_comment`; ba tool gọi nó | `develop:erp_ai/agent/tools/propose_change.py:125-139`, `:184`, `:198`, `:222` |
| CHG-002 nói gì về hàm chèn | "Cả ba handler đi về một hàm nội bộ `_propose_block(changes, commands, reason, ctx)`"; "hàm chèn duy nhất nay là `_propose_block`"; bước 4: "một `insert`, rồi 1 comment" | CHG-002 `design.md:209`, `:123`, `:474` |
| Luật một hàm chèn | "Tạo đề xuất mọi loại đi qua **đúng một hàm chèn** trong `tools/propose_change.py`" | ADR-031 QĐ 3 (`ADR-031.md:30`) |
| Chỗ thêm dòng "Chờ duyệt" | Một chỗ: hàm chèn duy nhất (`_insert`, sau U7a là `insert_proposal`); runner không thêm | `arch-review-design-addendum-3.md:131`; `tasks.md:796-800` (T105); `tasks.md:855` (T116) |
| Runner đọc gì của tool đề xuất | Chỉ khóa `proposal` của kết quả (`WRITE_TOOL_TARGETS`, `_action`); không ghi đối số tool đề xuất vào mục hành động; `PROPOSE_TOOLS` theo tên | `develop:erp_ai/agent/runner.py:72-80`, `:99`, `:714-790` |
| Thân `CHANGE_TOOLS_BLOCK` | Dòng đầu (`:157`) là neo P-1 của U1. CHG-002 thay câu `:167` ("Mỗi đề xuất là một file hoặc một lệnh") và `:170` ("…sau khi người chạy bench restart") | `develop:prompts.py:155-170`; CHG-002 `arch-impact.md:24`, `design.md:425-437`; `design-addendum-1-U1.md:235` |
| Dòng báo trước restart | `result_comment.post_restart_notice(name, action)`, comment `Info`, trước lời khởi chạy; dòng kết quả đến sau | CHG-002 `design.md:398-414`, `:560` |
| Đếm "1 comment kết quả" (AC-23) | B-10: `Info` có `content` chứa tên đề xuất | `arch-ruling-result-comment.md:70` |
| Dấu nội dung của CHG-002 | Hai dạng, phân biệt bằng `is_block(doc) = bool(doc.operations) or bool(doc.command_list)`; dạng cũ = 14 trường | CHG-002 `design.md:167-180` |
| Đường áp dụng của CHG-002 | "Mã áp dụng và hoàn tác chỉ có một đường, chạy trên kết quả của bộ chuyển đổi"; dạng cũ → 1 mục từ trường vô hướng | CHG-002 `design.md:171-174` |
| Đọc bảng con khi cha có hook quyền | Frappe gộp điều kiện dòng của cha (gồm `permission_query_conditions`) vào truy vấn bảng con; `frappe.client.get` của dòng con đọc qua cha | `apps/frappe/frappe/model/db_query.py:1401-1436`; `apps/frappe/frappe/client.py:213-218` |
| Kho HDSD sau `text_refusal` | `knowledge._manual_files` tự lọc `.md` và có trần `MANUALS_FILE_MAX_BYTES` riêng; không phụ thuộc `DUOI_CHO_PHEP` | `feat-007:erp_ai/agent/knowledge.py:115-131` |
| FEAT-007 có dùng tên mà CHG-002 xóa không | Dòng FEAT-007 thêm từ merge-base: 0 lần `DUOI_CHO_PHEP`, `SEARCH_FILE_MAX_BYTES`, `PROPOSAL_TEXT_MAX_CHARS`, `REPLACE_MAX_ITEMS`, `EXT_FORBIDDEN`; chỉ `_base_resolve` (dòng 118 dùng `DUOI_CHO_PHEP` là dòng đã có) | `git diff 1918db2 HEAD -- erp_ai \| grep '^+'` |

## 1. Mục tiêu 1: giả định của FEAT-007 trước CHG-002

Ký hiệu: **Giữ** = không đổi gì; **Giữ, có điều kiện** = đúng nếu giữ CI-n; **Sửa thiết kế** = nêu file và mục; **ADR** = cần quyết định kiến trúc.

### 1.1 U4b: `propose_change.py` (T89, T105)

| # | Giả định FEAT-007 (nguồn) | CHG-002 đổi gì | Phán | Điều kiện |
|---|---|---|---|---|
| G-1 | Một hàm chèn, nơi T105 thêm dòng "Chờ duyệt" (`_insert`; T105; AD3 `:131`; ADR-031 QĐ 3) | Ba tool đi về `_propose_block`. Design 1.6 gọi `_propose_block` là "hàm chèn duy nhất". Hàm này chỉ dựng đề xuất code/lệnh; đề xuất bản ghi của U7a không đi qua nó được | **Giữ, có điều kiện.** Hàm chèn vẫn phải là một hàm chung cho mọi loại: dựng bản ghi (kể cả dòng con và `command_list`), `insert` trong `allow_agent_write()`, rồi `_comment`. `_propose_block` kiểm và dựng giá trị, rồi gọi hàm đó | CI-1; RQ-1 |
| G-2 | Mỗi lần chèn mới, đúng 1 dòng "Chờ duyệt", nhãn cố định theo `change_kind`, không chép tham số (T105 `pending_line`) | Một khối = một đề xuất. `change_kind` = `Thay đổi code` khi có ≥ 1 mục file, ngược lại `Lệnh bench`. Từ chối cả khối → 0 đề xuất | **Giữ.** Khối 5 mục + 3 lệnh → 1 dòng, không đường dẫn nào | CI-2 |
| G-3 | `_comment` chỉ gọi `change_link.decision_path` khi `one_click_approval` (T89) | CHG-002 viết lại câu đầu ("khối {n} mục trong app {app}") và các dòng ghi chú; giữ "ba liên kết như hôm nay" (`design.md:386`) | **Giữ, có điều kiện.** T89 áp lên `_comment` mới. Test của T89 khẳng định liên kết, không khẳng định câu đầu | CI-3 |
| G-4 | Chống trùng chỉ cho loại bản ghi, trên hàm chèn duy nhất, dưới khóa phiếu (ADR-036 QĐ 5; w2 S-6) | Không thêm chống trùng cho code/lệnh | **Giữ.** Nhánh trùng của U7a đặt trong hàm chèn của G-1, trước `insert` | CI-1 |
| G-5 | Runner nhận đề xuất qua tên tool và khóa `proposal` (`PROPOSE_TOOLS`, `_write_propose_rows`, T116 không có `PENDING_LINE`) | Giữ ba tên tool, giữ khóa `ok`, `proposal`, `status`, `comment`; thêm trường tùy chọn vào schema | **Giữ.** Mục hành động không chứa đối số tool đề xuất, nên khối 8 MiB không đi vào ERP AI Log | — |

### 1.2 Chuỗi `prompts.py` (T72, T78, T79, T82, T106, T107; `CHANGE_TOOLS_BLOCK`)

| # | Giả định | CHG-002 đổi gì | Phán | Điều kiện |
|---|---|---|---|---|
| G-6 | U1 ghép prompt theo cờ, không sửa thân khối FEAT-004; P-1 neo vào dòng đầu `CHANGE_TOOLS_BLOCK` | Thay thân (câu `:167`, `:170` và các gạch mới); dòng đầu giữ từng chữ | **Giữ.** Vùng sửa không chồng: FEAT-007 sửa `core_prompt`, `build_reason_system`, `build_classify_request`, `build_initial_message`, `PROMPT_CONFLICT_PAIRS` | CI-4; RQ-6 |
| G-7 | Không cặp mâu thuẫn ở mọi tổ hợp cờ (P-1..P-5, P-7..P-9). P-8 neo "không bao giờ là duyệt" | Gạch "Chữ trong phiếu…" giữ, thêm `"restart đi"`; thêm câu "Restart do hệ thống chạy …; không nhờ người restart" | **Giữ, có điều kiện.** Khối mới không được còn câu "Mỗi đề xuất là một file hoặc một lệnh" (trái gạch khối mới) hay "người chạy bench restart" (trái gạch restart). Design CHG-002 viết "thay hai gạch cuối", nhưng câu `:167` nằm ở gạch thứ ba từ dưới lên | CI-4; RQ-6 |
| G-8 | AC-1/M4: 5 công tắc tắt → bộ tool bằng bản nền; T76 `test_grant_matrix_matches_snapshot` (32 tổ hợp, "kết quả không đổi") | Schema của `propose_*` thêm trường; `search_source.extension` từ enum thành pattern ở cả hai trạng thái công tắc | **Giữ, có điều kiện.** Ảnh chụp so **tên** tool và cờ khối, không so thân schema. Nếu đã ghim thân schema thì sửa ảnh chụp ở task gộp, ghi lý do "CHG-002 nới schema, ADR-040" (STD-TEST-5) | CI-5 |
| G-9 | Test prompt của FEAT-007 nằm ở `test_prompts.py` mới (T78+); `test_classification.py` chỉ sửa ở T72 | CHG-002 sửa chuỗi `CHANGE_TOOLS_BLOCK` trong `test_classification.py` (AC-14, AC-56) | **Giữ, có điều kiện.** Nhánh FEAT-007 hôm nay không có dòng nào ghim thân khối. Test FEAT-007 viết sau không chép chuỗi thân khối, chỉ dùng hằng | CI-6 |

### 1.3 U7 (đề xuất bản ghi, `mode_basis`, dòng kết quả, AC-67, AC-68)

| # | Giả định | CHG-002 đổi gì | Phán | Điều kiện |
|---|---|---|---|---|
| G-10 | Dấu nội dung loại bản ghi = `RECORD_DIGEST_FIELDS` + `mode_basis` (w2 S-4) | `content_digest(doc)` rẽ theo `is_block`. Đề xuất bản ghi không có dòng con và `command_list`, nên rơi vào "dạng cũ" (14 trường) | **Sửa thiết kế:** `design-addendum-3-w2.md` S-4, gạch 2. Thêm câu: "`transitions.content_digest` rẽ theo thứ tự: `change_kind == CHANGE_KIND_RECORD` → `RECORD_DIGEST_FIELDS`; rồi `block.is_block` → dấu khối; còn lại → dạng cũ. `test_block.py::TestLegacyDigest` của CHG-002 giữ xanh" | CI-7; RQ-5 |
| G-11 | Job: `apply_job.run_change` rẽ sang `_run_record` theo loại (ADR-031 QĐ 3; U7a) | Một đường áp dụng/hoàn tác chạy trên `block.operations_of`/`commands_of`. Dạng cũ thành 1 mục từ trường vô hướng, nên đề xuất bản ghi (`file_path` rỗng) sẽ thành một mục rỗng | **Sửa thiết kế:** `design-addendum-3-w2.md` S-7. Thêm gạch: "`run_change` rẽ `CHANGE_KIND_RECORD` → `_run_record` **trước** mọi lời gọi `block.*`, `change_guard.check_block`, `_recheck` phần code. Một dòng logger của `run_change` mang cả `ops= commands= restart=` (CHG-002) và `approve_to_result_ms=` (S-7); loại bản ghi ghi `ops=0 commands=0 restart=-`. `finish` nhận cả `command_results=` (CHG-002) và `latency_ms=` (S-7), đều là đối số từ khóa" | CI-8, CI-9; RQ-5 |
| G-12 | `pending_line` (w2 S-4 gạch cuối, S-6 gạch 5): "câu đầu của `_comment` cộng dòng căn cứ chế độ" | Câu đầu của `_comment` nay là tóm tắt khối ("khối {n} mục trong app {app}"), khác `PENDING_LINE` của T105 | **Sửa thiết kế:** `design-addendum-3-w2.md` S-4 gạch cuối và S-6 gạch 5. Thay bằng: "`pending_line` là hàm của T105 (`PENDING_LINE`, nhãn cố định theo `change_kind`). U7a chỉ thêm, cho loại bản ghi, một dòng `mode_basis_text` sau nhãn, và nhánh trùng `Chờ duyệt`. `_comment` không gọi `pending_line`" | CI-2 |
| G-13 | Dòng kết quả: một bộ dựng `post_result`, đúng 1 `Info` mỗi kết cục (ADR-035 QĐ 7, B-2..B-6, B-10) | `result_lines` thêm dạng khối; thêm `post_restart_notice` (một `Info` thứ hai, trước restart) | **ADR:** ADR-038 (proposed). Hai hàm có tên cùng module; "comment kết quả" nhận ra bằng tiền tố `kết quả đề xuất {name}`; B-10 đổi theo. Rẽ nhánh `result_lines`: `Đã từ chối` (B-5, mọi loại, chỉ dòng 1) → loại bản ghi (B-3, B-4) → khối (CHG-002) → dạng cũ (CHG-001) | CI-10, CI-11, CI-12; RQ-3, RQ-4 |
| G-14 | Cạnh hoàn tác: loại bản ghi chỉ từ `Đã áp dụng` (ADR-031 QĐ 6) | Cạnh mới `Lỗi → Đang hoàn tác` khi `change_kind = Thay đổi code`, có `apply_commit_sha`, chưa có `undo_commit_sha` (ADR-040 QĐ 3) | **Giữ, có điều kiện.** Hai ADR sửa ADR-012 QĐ 3 ở hai loại khác nhau. `request_undo` so `change_kind` tường minh | CI-13; RQ-7 |
| G-15 | Agent Helpdesk đọc đề xuất bản ghi qua một dòng DocPerm `Agent` cộng hai hook (ADR-035 QĐ 1–3) | DocType con `ERP AI Change Operation` không có quyền riêng, chứa nội dung file của đề xuất code | **Giữ.** Frappe 15 gộp điều kiện dòng của cha vào truy vấn bảng con và đọc dòng con qua cha | CI-14 |
| G-16 | AC-67: chống trùng đề xuất bản ghi, mọi đề xuất chờ ở "Chờ duyệt" | Không đổi đường bản ghi | **Giữ** (G-1, G-4) | CI-1, CI-2 |
| G-17 | AC-68: không gọi model sau Duyệt; `latency_ms` Duyệt → kết quả (w2 S-7) | Không thêm lời gọi model hay enqueue. `confirm_restart` chỉ đọc, chỉ cho Instructor/System Manager | **Giữ.** Rủi ro (không chặn): `bench restart` do một khối code gửi sẽ dừng worker. Một lần chạy agent đang dở có thể bị giết sau `stopwaitsecs`; AC-65 (b) "lỗi không tính là đã đưa hướng" đã phủ | CI-9 |
| G-18 | `mode_basis`: một cột nội dung trên JSON đề xuất; U7a thêm giá trị Select `Thay đổi bản ghi` và dòng DocPerm `Agent` | CHG-002 thêm 6 trường và bảng con vào cùng JSON và controller (`CONTENT_FIELDS` thêm `command_list`, dòng con bất biến) | **Giữ, có điều kiện.** U7a viết trên JSON đã có CHG-002 | CI-16 |
| G-19 | Kho HDSD: bot không ghi vào kho (T121, `resolve_safe_path`) | `text_refusal` thay kiểm đuôi trong `_base_resolve`; xóa, đổi tên, thư mục mới đều qua `check_write_path` | **Giữ, có điều kiện.** Lời khẳng định của CHG-002 (`design.md:114`) phải thành test | CI-15 |

### 1.4 Điều kiện của Mục tiêu 1

| # | Điều kiện | Đơn vị / task | Kiểm xong (có đầu ra) |
|---|---|---|---|
| CI-1 | **Một hàm chèn.** Trong `erp_ai/agent/tools/propose_change.py`, đúng 1 lời gọi `.insert(` và đúng 1 `with allow_agent_write()`, cùng trong một hàm. Ba tool (qua `_propose_block`) và đường bản ghi của U7a cùng gọi hàm đó. Nhánh trùng (ADR-036 QĐ 5) và lời `collect` của T105 nằm trong hàm đó. Hàm chèn bị inline vào `_propose_block` → task gộp lần hai tách lại, không đổi hành vi | task gộp lần hai; T105; U7a | `git grep -c "\.insert(" HEAD -- erp_ai/agent/tools/propose_change.py` = 1; `git grep -c "allow_agent_write()" …` = 1; reviewer dán thân hàm |
| CI-2 | **Một dòng "Chờ duyệt" mỗi đề xuất.** Thêm ca vào T105: khối 3 mục (sửa, tạo trong thư mục mới, đổi tên) + `migrate`, `restart` trong lần đưa hướng → đúng 1 dòng `SECTION_PENDING`, không chứa đường dẫn hay argv; khối bị từ chối → 0 dòng. U7a chỉ thêm `mode_basis_text` cho loại bản ghi (G-12) | T105; U7a | tên test trong `review-105.md`, `cmd.test_one` xanh |
| CI-3 | **T89 trên `_comment` mới.** Test T89 chỉ khẳng định có/không có liên kết ký (`decision_path`) và nhãn `OPEN_PROPOSAL_LABEL`, không khẳng định câu đầu. Có ca khối nhiều mục: công tắc (5) tắt → 0 liên kết ký | T89 (hoặc task gộp nếu T89 đi trước) | `cmd.test_one erp_ai/agent/tools/test_propose_change.py` xanh sau gộp |
| CI-4 | **Prompt sau gộp.** `CHANGE_TOOLS_BLOCK` bắt đầu bằng đúng dòng neo P-1; không chứa "Mỗi đề xuất là một file hoặc một lệnh", "người chạy bench restart", `chờ một chữ "ok"`, "Việc hoàn tác được thì làm luôn"; vẫn chứa "KHÔNG BAO GIỜ là duyệt". `TestCorePrompt::test_no_conflict_pair_in_any_flag_combination` và `::test_no_ok_approval_in_every_combination` xanh | task gộp lần hai; T78, T79, T82 nếu đến sau | `git grep -c` cho từng chuỗi (0 / 1); `cmd.test_one erp_ai/agent/test_prompts.py` |
| CI-5 | **Ảnh chụp cấp tool.** `test_grant_matrix_matches_snapshot` so tên tool và cờ, không thân schema. Nếu đã ghim thân schema: task gộp sửa ảnh chụp cho riêng các trường CHG-002 nới, lý do trong commit | T76 (nếu chưa merge), task gộp | `cmd.test_one erp_ai/agent/tools/test_registry.py` xanh |
| CI-6 | **Không chép thân khối vào test FEAT-007.** `test_prompts.py`, `test_agent_runner.py` của FEAT-007 không chứa chữ của `CHANGE_TOOLS_BLOCK` ngoài dòng neo P-1 | T72–T107 | `git grep -c "propose_file_change nhận nhiều mục\|Mỗi đề xuất là một file" -- erp_ai/agent/test_prompts.py` = 0 |
| CI-7 | **Dấu rẽ theo loại trước.** Như G-10. Test U7a: đề xuất bản ghi có `operations` rỗng, `command_list` rỗng → `content_digest` dùng `RECORD_DIGEST_FIELDS` (đổi `mode_basis` sau duyệt → `DIGEST_CHANGED`, T-13 của w2) | U7a | `cmd.test_one erp_ai/agent/changes/test_transitions.py`, `test_block.py` xanh |
| CI-8 | **Job rẽ theo loại trước bộ chuyển đổi.** Như G-11. Test U7a: spy `block.operations_of`, `block.commands_of`, `change_guard.check_block`, `process_runner.launch_restart` → 0 lời gọi qua 4 kết cục của `_run_record` | U7a | `cmd.test_one erp_ai/agent/changes/test_apply_job.py` xanh |
| CI-9 | **Một dòng logger, hai đối số từ khóa.** Như G-11. AC-68 T-15 của w2 chạy trên mã đã gộp: 0 lời gọi model, 0 `enqueue_agent_run`, 0 `launch_restart` | U7a | đầu ra test T-15; dòng logger dán vào review |
| CI-10 | **Rẽ nhánh `result_lines`.** `Đã từ chối` → chỉ dòng 1 cho mọi loại, kể cả khối (B-5); loại bản ghi → B-3, B-4 (không dòng `commit`, `restart:`, `việc người còn phải làm`); khối → chữ CHG-002; dạng cũ → chữ CHG-001. `test_lines_for_each_final_status` của CHG-001 thêm subTest khối × `Đã từ chối` | U7a | `cmd.test_one erp_ai/agent/changes/test_result_comment.py` xanh |
| CI-11 | **B-10 theo ADR-038.** Ma trận AC-23 và `TestApplyRecord::test_each_outcome_one_result_comment` đếm `Info` mở đầu bằng `kết quả đề xuất {name}`. Thêm một ca code có `restart`: 1 dòng kết quả + 1 dòng báo, AC-23 vẫn đếm 1 | U7a | tên test, đầu ra `cmd.test_one` |
| CI-12 | **Ràng buộc ADR-038.** Luật AST ở `test_architecture.py`: `post_restart_notice` gọi đúng 1 chỗ trong `apply_job.py`; `add_comment(` chỉ trong `result_comment.py`, trong đúng hai hàm. Chữ dòng báo không mở đầu bằng `kết quả đề xuất`. B-11 mở rộng cho dòng báo | U7a (luật `test_result_comment_boundaries`); task gộp kiểm tiền tố | `cmd.test_one erp_ai/tests/test_architecture.py` xanh |
| CI-13 | **Hai cạnh hoàn tác cùng sống.** `request_undo`: loại bản ghi ở `Lỗi` → `InvalidTransition`; loại code ở `Lỗi` có sha → `Đang hoàn tác` | U7a | `cmd.test_one erp_ai/agent/changes/test_transitions.py` xanh |
| CI-14 | **Bảng con không mở lối đọc.** Ma trận ADR-035 thêm: người chỉ-`Agent` được giao → `frappe.get_list("ERP AI Change Operation", parent_doctype="ERP AI Change Proposal")` = 0 dòng; `frappe.client.get` dòng con của đề xuất code → `PermissionError` | task U7b thêm dòng DocPerm `Agent` | tên test, đầu ra `cmd.test_one` |
| CI-15 | **Kho HDSD sau `text_refusal`.** Thêm vào `test_change_guard.py` hoặc test khối của CHG-002, với `manuals_dir` đặt: tạo file trong thư mục mới dưới kho, xóa file trong kho, nguồn đổi tên trong kho, đích đổi tên vào kho → mỗi ca `ok=false`, 0 đề xuất. `test_new_file_in_manuals_refused`, `TestManualsExcluded` và `test_knowledge.py` giữ xanh | task gộp lần hai | đầu ra `cmd.test_one` của ba file |
| CI-16 | **JSON đề xuất mang cả hai.** Sau `cmd.migrate` từ worktree: `tabERP AI Change Operation` tồn tại; 6 cột của CHG-002 có. Sau U7a: thêm `mode_basis`, giá trị Select bản ghi, dòng DocPerm `Agent`; `frappe.db.exists("DocType", "ERP AI Change Operation")` vẫn đúng | task gộp lần hai; U7a | đầu ra truy vấn dán vào progress |

## 2. Mục tiêu 2: chỗ của lần gộp `develop` thứ hai

### Phán quyết
Lần gộp thứ hai là **một task riêng** (tech-lead đặt số; dưới đây gọi là "task gộp lần hai"), gắn `[migrate]`. Nó chạy ở vòng build đầu tiên sau khi commit merge của CHG-002 có trên `develop` và không còn nhánh task nào đang mở trên file của nó. Nó chen vào chuỗi "Một file, một chủ" của mọi file trong `files:` ở đúng chỗ đó.

| Mốc | Loại | Vì |
|---|---|---|
| Trước T105 | **Cứng** | T105 sửa đúng hàm chèn mà CHG-002 viết lại; test của nó dựng đề xuất một-file. T105 là lá: không task nào `depends:` nó. Chờ thì chỉ phải đổi thứ tự ở chuỗi `test_architecture.py` (T99 → T119 → T105 được) và dời M10 phần `test_propose_change` |
| Trước mọi task U7a và trước khi lập plan đợt 2 | **Cứng** | U7a sửa `apply_job.py`, `transitions.py`, `result_comment.py`, controller và JSON đề xuất, tức gần trọn vùng CHG-002 viết lại (G-10..G-18). Lập plan đợt 2 trên hình dạng cũ thì phải viết lại |
| Trước T89 | Mềm | T89 nhỏ, chỉ chạm `_comment`. Nếu CHG-002 đã ở `develop` khi T89 sẵn sàng thì gộp trước. Nếu chưa thì T89 đi trên hình dạng cũ, và task gộp chạy lại CI-3 |
| Trước U4b ở runner | Không cần | CHG-002 không chạm `runner.py`, `write_ticket.py`, `handlers.py`, `route_ticket.py`; `PROPOSE_TOOLS` và khóa `proposal` giữ (G-5) |
| Cuối đợt 1 | Không chọn | Đợt 1 gồm cả 1b (U2, U6b, U8). Chờ tới đó thì T89, T105 viết trên hình dạng cũ, và mọi xung đột dồn vào một lần gộp ngay trước đợt 2: đúng cái giá mà `arch-ruling-r5.md` mục 2 đã tránh cho `runner.py`. R5-5 vẫn cấm `team/FEAT-007` → `develop` trước U2, nên chiều gộp này không vướng R5-5 |

Không ràng buộc nào ở đây đổi thứ tự `runner.py` của R5-1..R5-6.

### Task gộp lần hai phải kiểm gì

| # | Điều kiện | Kiểm xong (có đầu ra) |
|---|---|---|
| CI-17 | **Điều kiện bắt đầu.** Trên đúng SHA `develop` sẽ gộp: `git grep -c "_propose_block" <SHA> -- erp_ai/agent/tools/propose_change.py` > 0 và `git ls-tree <SHA> erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/` khác rỗng (mã CHG-002 đã vào đủ, không phải một phần). Ghi SHA vào `Receives` | hai đầu ra dán vào progress |
| CI-18 | **Xung đột chỉ ở chỗ đã biết.** Chạy `git merge-tree --write-tree --name-only team/FEAT-007 <SHA>` (read-only). Mọi file xung đột phải nằm trong bảng `CHG-002/design.md` mục 1.6, cộng các file FEAT-007 đã sửa sau ngày hôm nay (`propose_change.py`, `test_propose_change.py` nếu T89 đã merge; `test_prompts.py`, `test_registry.py`, `test_agent_runner.py`, `test_architecture.py`). Có xung đột ở `runner.py`, `write_ticket.py`, `site_api.py`, `registry.py`, `policy.py`, `tasks.py` hoặc ở file ngoài `files:` → dừng, báo architect | danh sách file xung đột trong progress |
| CI-19 | **Vùng của CHG-002 vào nguyên vẹn.** Sau gộp, `git diff <SHA> HEAD -- erp_ai/agent/changes/ erp_ai/agent/change_text.py erp_ai/agent/tools/change_guard.py erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/ erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/` không in dòng nào. FEAT-007 chưa sửa các file này; nếu U7a đã chạy trước thì mốc cứng của mục trên đã bị vi phạm | lệnh diff không in gì |
| CI-20 | **`source.py` theo công thức của CHG-002 mục 1.6.** Giữ `_base_resolve`, `manuals_root`, `resolve_manual_path`, `resolve_safe_path` của FEAT-007. Trong `_base_resolve`, hai dòng kiểm `TEN_CAM` và `DUOI_CHO_PHEP` thành `if text_refusal(os.path.relpath(full, root)) is not None: return None`. Ngoài test, `DUOI_CHO_PHEP` xuất hiện 0 lần trong `erp_ai/`; `SEARCH_FILE_MAX_BYTES` không có trong `change_guard.py`, `propose_change.py` (ADR-040 Phán quyết C-1) | hai phép `git grep -c` (0, 0); CI-15 xanh |
| CI-21 | **Không mất test.** Với `test_architecture.py`, `test_change_guard.py`, `test_source.py`, `test_classification.py`, `test_propose_change.py`, `test_registry.py`, `test_agent_runner.py`, `test_utils.py`: tập `def test_`/`def ` của bản `<SHA>` trừ bản gộp, và của đầu nhánh trước gộp trừ bản gộp (`comm -23`, hai chiều), đều rỗng. Test đổi tên có chủ đích thì ghi tên vào progress (bài học M-2 của T56) | hai lần `comm -23` mỗi file, rỗng hoặc có danh sách đã giải thích |
| CI-22 | **CI-1, CI-4, CI-5, CI-6, CI-12 (phần tiền tố), CI-15, CI-16** chạy trên cây đã gộp | đầu ra từng phép |
| CI-23 | **Một lần giữ khóa site.** `cmd.migrate` từ worktree `feat-007`, rồi `cmd.test_one` cho `erp_ai/agent/tools/test_propose_change.py`, `test_change_guard.py`, `test_source.py`, `test_registry.py`, `erp_ai/agent/test_classification.py`, `test_prompts.py` (nếu đã có), `test_agent_runner.py`, `erp_ai/agent/test_knowledge.py`, `erp_ai/agent/changes/test_apply_job.py`, `test_apply_block.py`, `test_block.py`, `test_result_comment.py`, `test_transitions.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/tests/test_architecture.py`. `cmd.test` cả bộ ở mốc kế tiếp của plan, trước task kế tiếp trên `propose_change.py` | `Ran … OK` của từng module |
| CI-24 | **Hết migrate chéo cho DocType của CHG-002.** Sau migrate này, migrate từ worktree FEAT-007 không còn xóa `ERP AI Change Operation`. Ghi một dòng vào `note-to-chg-002-session.md` (team-leader) | `frappe.db.exists("DocType", "ERP AI Change Operation")` sau một lần `cmd.migrate` nữa |

## 3. Mục tiêu 3: yêu cầu cho phiên CHG-002

Đây là yêu cầu. File này không sửa hồ sơ CHG-002. Team-leader chuyển qua `note-to-chg-002-session.md`.

| # | Yêu cầu | Vì (FEAT-007) |
|---|---|---|
| RQ-1 | **Giữ một hàm chèn chung**, giữ tên `_insert(ctx, values)` (hoặc báo tên mới). Hàm nhận `values` có cả `operations` (list dòng con) và `command_list`; làm `get_doc` → `insert()` trong `allow_agent_write()` → `_comment`; trả `{"ok", "proposal", "status", "comment"}`. `_propose_block` kiểm và dựng `values`, rồi gọi hàm này; không tự `insert`. Trong file: đúng 1 `.insert(`, đúng 1 `allow_agent_write()` | ADR-031 QĐ 3; T105; U7a (đường bản ghi, chống trùng); CI-1 |
| RQ-2 | **Giữ ổn định các tên** FEAT-007 dùng: `_comment(ctx, proposal)` và ba liên kết dựng bằng `change_link.decision_path` trong đó; ba tên tool và `PROPOSE_TOOL_NAMES`; khóa kết quả `ok`, `proposal`, `status`, `comment`; `result_comment.post_result(proposal_name)` với đúng một lời gọi trong `run_change`; `transitions.finish` và `log_step` chỉ thêm đối số từ khóa; `transitions.content_digest(doc)`; `block.is_block(doc)` | T89, T105, U7a (B-2, B-6, S-7); CI-3, CI-9 |
| RQ-3 | **`result_lines` rẽ theo dạng.** Dòng riêng của khối (`restart:`, `việc người còn phải làm`, dòng từng mục, dòng lệnh) chỉ khi `block.is_block(doc)`. Dạng cũ giữ đúng chữ CHG-001. Tập trạng thái hợp lệ để mở (U7a thêm `Đã từ chối`, chỉ dòng 1) | B-3, B-4, B-5; CI-10 |
| RQ-4 | **Dòng báo trước restart:** nằm trong `result_comment.py`; gọi đúng 1 chỗ trong `apply_job.py`; chỉ khi `command_list` có `restart`; chữ **không** mở đầu bằng `kết quả đề xuất`; dưới user phiên, `Info`, không `set_user`, `new_comment`, `publish_realtime` | ADR-038; CI-11, CI-12 |
| RQ-5 | **Bộ chuyển đổi và dấu không nuốt loại lạ.** `block.operations_of`/`commands_of` và nhánh "dạng cũ" của `content_digest` chỉ nhận `change_kind ∈ {Thay đổi code, Lệnh bench}`; loại khác → `ValueError`. Như vậy đề xuất bản ghi chạm nhầm đường code sẽ lỗi rõ, không thành một mục rỗng | G-10, G-11; CI-7, CI-8 |
| RQ-6 | **`CHANGE_TOOLS_BLOCK`:** bỏ cả câu `prompts.py:167` ("Mỗi đề xuất là một file hoặc một lệnh") lẫn `:170` (design 3.7 viết "hai gạch cuối", nhưng `:167` nằm ở gạch thứ ba từ dưới lên). Giữ dòng đầu từng chữ và cụm "KHÔNG BAO GIỜ là duyệt". Không thêm `chờ một chữ "ok"` hay "Việc hoàn tác được thì làm luôn" | P-1, P-8, P-9 của U1; CI-4 |
| RQ-7 | **Cạnh `Lỗi → Đang hoàn tác`** so `change_kind == CHANGE_KIND_CODE` tường minh, không viết "khác lệnh bench" | ADR-031 QĐ 6 (loại bản ghi); CI-13 |
| RQ-8 | **Báo SHA merge của CHG-002** vào `note-from-feat-004-session.md` khi vào `develop`. Luật mới ở `test_architecture.py` đặt thành khối riêng, không sửa thân `check_tools_never_bypass_permissions`; không dùng `frappe.qb` trong `tools/` (T122) | CI-17, CI-18; `note-to-chg-002-session.md` |

## 4. Đối chiếu NFR và chiều

- NFR của FEAT-007 bị chạm:
  - NFR-1 (nhóm loại trừ): CHG-002 không chạm đường định tuyến. Giữ.
  - NFR-3 (không làm trùng): G-4, CI-1. Giữ.
  - NFR-8 (không lộ bí mật trong chữ):
    - dòng báo không có URL, theo `_shown` của CHG-002 và ADR-038 QĐ 1;
    - mục hành động không mang đối số của tool đề xuất (G-5).
  - NFR-2 (chi phí model): 0 lời gọi thêm. Giữ.
- Chiều:
  - Triển khai: không đơn vị chạy mới.
  - Chủ dữ liệu: đề xuất vẫn do `transitions` giữ trạng thái; CHG-002 thêm trường trạng thái, FEAT-007 thêm trường nội dung.
  - Đường ghi:
    - một hàm chèn (CI-1);
    - comment `Info` chỉ ở `result_comment.py` (ADR-038).
  - Lỗi, log, cấu hình: một dòng logger `run_change` (CI-9).
  - Quyền: bảng con theo cha (CI-14).
  - Để designer U7a: chữ dòng `mode_basis` trong `pending_line`, tên test.

## 5. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR mà vẫn xung đột, rồi siết:
1. CHG-002 inline `insert` vào `_propose_block`; U7a thêm `insert_proposal` cho loại bản ghi. Kết quả là hai hàm chèn, chống trùng chỉ ở một hàm, T105 chỉ thấy một hàm. Siết bằng CI-1, RQ-1.
2. U7a viết `RECORD_DIGEST_FIELDS` sau nhánh `is_block` của CHG-002. Đề xuất bản ghi ký bằng 14 trường code, nên đổi `mode_basis` sau duyệt vẫn qua. Siết bằng CI-7, RQ-5.
3. U7a test AC-23 đếm `Info` "chứa tên đề xuất"; CHG-002 đăng dòng báo trước restart. Ca code có `.py` đếm ra 2, dev "sửa" bằng cách bỏ dòng báo. Siết bằng ADR-038, CI-11.
4. CHG-002 in `restart: không cần` cho mọi kết cục; U7a B-4 cấm dòng thừa cho loại bản ghi. Siết bằng CI-10, RQ-3.
5. Task gộp lần hai chạy sau U7a. U7a đã viết `_run_record` trên `apply_job.py` cũ, và lần gộp phải gỡ gần trọn file. Siết bằng mốc cứng của mục 2 và CI-19.
6. T105 merge trên `_insert` cũ; CHG-002 xóa `_insert`; lần gộp giữ một trong hai, và dòng "Chờ duyệt" mất lặng lẽ. Siết bằng mốc cứng trước T105 và CI-2 (test đếm 1 dòng).
7. CHG-002 chỉ thay "hai gạch cuối"; câu "một file hoặc một lệnh" còn cạnh câu khối. Không cặp nào của U1 bắt được. Siết bằng CI-4, RQ-6.

Sau khi siết, không còn cặp nào trong phạm vi T89, T105, chuỗi `prompts.py`, U7a/U7b và task gộp lần hai.

## Việc tiếp

- **Team-leader:**
  - ghi journal;
  - chuyển RQ-1..RQ-8 vào `note-to-chg-002-session.md`;
  - đưa ADR-038 cho người duyệt cùng ADR-035.
- **Tech-lead:** thêm task gộp lần hai theo mục 2. Thêm:
  - CI-2 vào T105;
  - CI-3 vào T89;
  - CI-5 vào T76 nếu chưa merge;
  - CI-6 vào chuỗi prompt.
- **Designer, trước plan đợt 2:** sửa `design-addendum-3-w2.md` S-4, S-6, S-7 theo G-10, G-11, G-12.
- **Plan đợt 2:** mang CI-7..CI-14, CI-16 và Ràng buộc của ADR-038.
