Verdict: approve-with-conditions

Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- Không có cổng cho lần soát này (team.py: chỉ G5). Để trống. -->

# Soát kiến trúc phụ lục spec 3 (FEAT-007): một hướng xử lý, việc tự làm được thì làm luôn, bấm Duyệt thì bot tự làm

**Kết luận.** Ba hành vi H-1..H-3 đứng được trên kiến trúc hiện có, sau hai thay đổi đã ghi ở trạng thái `proposed`:
- **ADR-031 Amendment 1**: vắng mặt trong danh mục = `Cần duyệt`, với thứ tự kết cục cố định. Riêng "Đổi trường" và thêm người vào nhóm loại trừ vẫn cần dòng danh mục. Bảng con không bao giờ là đích.
- **ADR-036 (mới)**: một hàm ghi comment hướng xử lý, gom nội dung lần chạy, dấu hiệu do mã đặt, khóa phiếu cộng đọc có khóa.

AC-65 (d) không đòi ngoại lệ nào cho ADR-033 QĐ 1, QĐ 5 hay ADR-035 QĐ 7; nó chỉ sửa ADR-019 QĐ 2 (u4) và một câu của ADR-031 QĐ 7. AC-68 khớp ADR-035 và nhánh A. Điều kiện: AR3-1..AR3-11 (mục 5). AR3-2 lệch chữ AC-29 "6 hành động", nên analyst phải `--amend`. AR3-10 là câu cho người, không chặn build.

Không sửa spec, thiết kế, mã. Không ghi `.team/current.json`: một phiên build đang giữ file đó, và lệnh giao việc giới hạn chỉ ghi `docs/team/**`. Không chạy migrate hay test.

## Căn cứ (đọc trực tiếp ngày 2026-11-14; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Thứ tự kiểm của bộ thực thi trong thiết kế | danh mục (bước 2) đứng **trước** điều cấm cứng (3), vai trò (4), môi trường (5); không dòng → `OUT_OF_CATALOG` | `design-addendum-2-U7a.md:183-191`, `:199` |
| Test ghim "rỗng = cấm" | `test_empty_catalog_refuses_every_action`, `test_empty_catalog_no_proposal`, `test_rule_added_between_calls_takes_effect`, `test_rule_removed_before_job_fails`; U7b `test_category_outside_row_refused`, `test_no_rule_refused` | U7a `:361-364`, `:380`; U7b-U8 `:352`, `:372` |
| "Đổi trường" lấy DocType và trường từ đâu | tham số `doctype`, `name`, `values` của model | U7a `:181`, `:184` |
| Điều cấm cứng hôm nay | `read.denied_doctypes()` ∪ `site_api.DENIED_DOCTYPES` (FEAT-007 @ `888f5dc`), sau INT-1 là `site_api.PERMISSION_DOCTYPES` = {Custom Role, Custom DocPerm, DocType, Role} (`develop`) + submittable; không xét `istable` | `erp_ai/agent/hard_bans.py`; `develop:erp_ai/agent/tools/site_api.py:29`; `design-w0-fixes.md:209` |
| Chốt riêng của 5 quyền FEAT-004 mà bộ thực thi không dùng | `FORCED_VALUES` (Server Script tắt, Webhook tắt); `FORBIDDEN_ROLES` chỉ kiểm khi gán vai trò cho User | `develop:site_api.py:31`, `:66`; U7a `:187` (chỉ tạo tài khoản) |
| Tài khoản agent trên `miyano` | giữ `System Manager` | ADR-031 Hệ quả; arch-impact L-8 |
| Ai duyệt đề xuất bản ghi | Instructor hoặc người có ToDo mở của phiếu, kể cả tự giao (Q-2 mặc định) | `spec-addendum-2.md:54`, `:84-87` |
| Comment của bot hôm nay (thiết kế) | định tuyến 1 comment ở `_route` trước suy luận; model đăng qua `post_comment`; `catalog_tools` đăng comment site test và "Tự làm" riêng | U4b `:246`, `:171`; U7a `:208`; U7a-fixes-2 `:144`; U7b-U8 `:200`, U7b-U8-fixes `:183` |
| Chống trùng comment trong thiết kế | khóa dòng phiếu `for_update` rồi đọc Comment theo tiền tố | U4b `:172` (`post_notice`), `:175` (BA note) |
| Mức cô lập DB | Frappe không đặt (grep `isolation` trong `frappe/database/` chỉ thấy chú thích `mariadb/database.py:30`) → MariaDB `REPEATABLE READ` | `apps/frappe/frappe/database/` |
| Hai lần chạy song song của một phiếu | `job_id = erp_ai::{ticket}::{trigger}`: khác trigger → khác job | `erp_ai/agent/queue.py:18` |
| Prompt quy tắc 6 | "chờ một chữ 'ok'" | `erp_ai/agent/prompts.py:104-106`; U1 P-6, P-7 (`design-addendum-1-U1.md:240-241`), `:403` (test ghim chuỗi cũ) |
| Nhánh A comment kết quả | `post_result` một lời gọi trong `run_change`, dòng `Info` dưới người thực hiện; Từ chối ghi trong request | ADR-035 QĐ 6, 7; `arch-ruling-result-comment.md` B-0..B-16 |
| M2 so `ERP AI Instructor` (R-5 của phán quyết trước) | U7a thay `_has_authority` bằng `authority.can_decide` trong `_recheck` | U7a `:234`, `:237` |

## 1. Mục tiêu (1): amendment ADR-031 QĐ 1

Đã ghi ở `docs/team/adr/ADR-031.md`, mục "Amendment 1" (thân giữ nguyên chữ, chỗ bị thay có dấu `[A1]`). Không viết ADR mới vì ADR-031 còn `proposed`; tiền lệ là ADR-035 cũng sửa cùng ngày.

- **A1-1 Thứ tự kết cục** (lúc tạo và lúc áp dụng):
  1. tham số sai;
  2. **điều cấm cứng**: `hard_ban_reason`, vai trò cấm, phiếu loại trừ, `permlevel`, bảng con;
  3. **cổng môi trường**;
  4. dòng `Cấm`;
  5. chế độ của dòng phủ;
  6. không dòng → `Cần duyệt` (trong tập A1-2), ngoài tập thì từ chối "cần dòng danh mục";
  7. không đổi.

  Đúng thứ tự người yêu cầu, thêm bước 1 (đầu vào) và 7 (không đổi). Lý do ở bước 2–3 không bao giờ nói "danh mục".
- **A1-2 Tập "mặc định Cần duyệt"** = hành động có bề mặt ghi cố định: 5 hành động có tên và tạo Project. Ngoài tập: "Đổi trường", và thêm người vào nhóm loại trừ (mục 4).
- **A1-3** Kiểm lại lúc áp dụng: dòng `Cấm` thêm sau → `Lỗi`; dòng bị xóa → hành động trong tập vẫn áp dụng.
- **A1-4** Bảng con (`istable`) là điều cấm cứng, dẫn xuất từ meta trong cùng `hard_ban_reason`.
- **A1-5** Căn cứ chế độ (dòng nào, hay mặc định) là nội dung bất biến của đề xuất, hiện cho người duyệt.

Xác nhận theo spec mục 8: điều cấm cứng và cổng môi trường đứng **trước** mọi kết cục của danh mục. Thiết kế U7a hiện đặt sai thứ tự (AR3-1).

## 2. Mục tiêu (2): AC-65 (d) đặt ở đâu, có cần ngoại lệ không

**Đặt ở đâu.** Ở tầng ghi, không ở prompt, handler hay hàm cấp (ADR-036):
- Một hàm ghi comment hướng xử lý trong `erp_ai/agent/tools/`, runner gọi đúng một lần ở cuối lần chạy đưa hướng. Hàm khóa dòng HD Ticket rồi đếm bằng đọc có khóa; đã có thì không ghi (QĐ 1, 4).
- Tool `post_comment` (U4b, `tools/write_ticket.py`) từ chối mọi nội dung của model mang dấu hiệu, ở mọi `kind`, `ok=false` (QĐ 3). Đây chính là "tool trả lỗi cho model, 0 comment thêm".
- Dấu hiệu do mã đặt, nên ghi đè hay xóa prompt (AC-38) không lách được. Đếm bằng một hàm, chỉ `Comment` loại `"Comment"` của tài khoản agent.

**Vì sao phải ở cuối lần chạy.** AC-67 và AC-23 `[changed]` đòi "Chờ duyệt" và mọi việc đã làm nằm trong cùng comment. Đề xuất được tạo trong lượt suy luận, sau bước định tuyến. Chỉ một hàm chạy sau mọi lượt mới thấy đủ.

**Vì sao đọc có khóa.** Hai trigger khác nhau chạy song song được (`queue.py:18`). Dưới `REPEATABLE READ`, `SELECT` thường sau khóa dòng đọc ảnh chụp cũ, nên vẫn đăng trùng. Mẫu `post_notice` và BA note của U4b (`:172`, `:175`) có cùng lỗi (AR3-7).

**Ngoại lệ cho luật ghi comment hay luật kiến trúc.**

| Luật | Cần ngoại lệ? | Ghi chú |
|---|---|---|
| ADR-033 QĐ 1 (comment phiếu dưới tài khoản agent) | Không | Comment hướng vẫn do tài khoản agent ghi |
| ADR-033 QĐ 5 (mỗi lần ghi một mục hành động) | Không | Lần từ chối vì dấu hiệu = 1 mục `ok=false`; "đã có hướng, không ghi" không phải ghi → chỉ logger |
| ADR-033 QĐ 2, ADR-003 (handler chỉ xếp hàng) | Không | Handler không đọc dấu hiệu |
| ADR-030 (hàm cấp; runner không lọc tool; `prompts.py` không đọc cấu hình) | Không | Không thêm đầu vào hàm cấp; "đã có hướng" vào thông điệp đầu như dữ liệu phiếu |
| ADR-035 QĐ 7 (dòng `Info` kết quả, `add_comment` chỉ ở `result_comment.py`) | Không | Hàm đếm bỏ qua `Info`; comment hướng không dùng `add_comment` |
| ADR-019 QĐ 2 (u4) (bước định tuyến đăng tối đa 1 comment) | **Sửa** (không phải ngoại lệ) | Trong lần đưa hướng (u4) vào bộ gom, không đăng riêng. Do AC-23 `[changed]`, không do (d) |
| ADR-031 QĐ 7 (comment "cần làm trên site test") | **Sửa** một câu | Như trên; ghi ở ADR-031 `[A1]` và ADR-036 |

## 3. Mục tiêu (3): AC-68 (0 lời gọi model sau Duyệt)

**Khớp** ADR-035 và nhánh A, với AR3-8, AR3-9:
- Áp dụng là `apply_job` → `catalog.execute` với `action_args` hoặc `edited_args` đã lưu. Không đường nào tới Cổng model: ADR-033 Ràng buộc "chỉ `runner.py` import Cổng model"; ADR-001.
- Comment kết quả = dòng `Info` của `post_result`, gọi một chỗ trong `run_change` (ADR-035 QĐ 7, B-6). `Info` không qua `handlers.comment_after_insert`, nên không xếp lần chạy bot nào (B-11). Đúng "không có lần chạy bot nào được xếp hàng sau Duyệt".
- "1 mục nhật ký" = mục hành động trong dòng bước áp dụng (ADR-031 QĐ 8, ADR-033 QĐ 5).
- "Thời gian từ Duyệt tới kết quả" suy từ `decided_at` → `finished_at` của đề xuất, cả hai do `transitions` ghi. Không thêm đường đo, chỉ đưa số vào dòng bước áp dụng hoặc logger của `run_change` (AR3-9).
- Duyệt rồi gỡ điều kiện → `Lỗi`: `_recheck_record` gọi `authority.can_decide` (U7a `:237`). R-5 của `arch-ruling-result-comment.md` mục 7 vì vậy đóng trên giấy, với điều kiện câu "vẫn đủ điều kiện duyệt của loại" của ADR-031 (thay ADR-023 QĐ 2) được dựng đúng.
- Hộp xác nhận theo (5): ADR-035 QĐ 4 (bit một bước). Duyệt hai lần → áp một lần: phép chuyển có điều kiện (ADR-012 QĐ 3).

Một chỗ dễ lệch: AC-36 `[changed]` "việc tự làm trong lần chạy khác báo bằng 1 comment kết quả". Comment đó là `Comment` của tài khoản agent (ADR-033 QĐ 1), **không** là dòng `Info` của `post_result`, vì ADR-035 QĐ 7 chỉ dành cho kết cục của đề xuất (AR3-8).

## 4. Mục tiêu (4): rủi ro bảo mật của "người được giao duyệt mọi bản ghi không bị cấm" (Q-10 × Q-2)

**Bối cảnh rủi ro.** Ba điều cùng đúng:
- người tự giao phiếu cho mình là người duyệt (Q-2);
- tài khoản agent trên `miyano` là `System Manager`, nên quyền Frappe không chặn gì;
- phụ lục bỏ dòng danh mục làm ranh giới.

Gộp lại, lớp chặn duy nhất còn lại là danh sách cấm cứng. `spec-addendum-2.md:86` đã ghi "chỉ còn danh mục trắng và điều cấm cứng là lớp chặn". Phụ lục 3 gỡ nốt danh mục.

| # | Rủi ro | Ví dụ cụ thể | Mức | Xử lý |
|---|---|---|---|---|
| R-S1 | Leo quyền qua "Đổi trường" không dòng | Agent Helpdesk tự giao phiếu, viết "đổi trường X của bản ghi Y", bot đề xuất, chính họ Duyệt, tài khoản `System Manager` ghi. Đích không bị cấm cứng: `Webhook.request_url` (gửi dữ liệu ra ngoài; `FORCED_VALUES` của FEAT-004 không áp ở bộ thực thi), `Email Account.smtp_server` (mật khẩu đã lưu gửi tới máy chủ lạ), `OAuth Client.redirect_uris`, `Social Login Key.base_url`, `Notification`, `System Settings`, `Server Script.script` khi môi trường `test`, dữ liệu tài chính chưa submit (Bank Account, Supplier, Item Price) | **Cao** | AR3-2: "Đổi trường" vẫn cần dòng (ADR-031 A1-2). Danh sách cấm cho cả framework không đóng được (mỗi app thêm DocType), nên không vá bằng danh sách |
| R-S2 | Leo quyền qua bảng con, **có cả trên đường có dòng** | `DocPerm` (bảng quyền chuẩn; chỉ `Custom DocPerm` bị cấm), `Has Role` (gán `System Manager` trực tiếp, đi vòng qua `FORBIDDEN_ROLES` vốn chỉ kiểm khi tạo tài khoản) | **Cao** (lỗ có trước phụ lục; phụ lục làm nó tới được bằng một lần bấm) | AR3-3: `istable` là điều cấm cứng, dẫn xuất từ meta (ADR-031 A1-4) |
| R-S3 | Tự cấp quyền đọc phiếu nhạy cảm | Agent tự giao phiếu, bot đề xuất "thêm tôi vào nhóm HR" (nhóm thuộc `excluded_teams`), họ Duyệt và đọc được phiếu HR (NFR-1) | Cao | AR3-4: thêm người vào nhóm loại trừ nằm ngoài tập mặc định, phải có dòng tường minh (ADR-031 A1-2) |
| R-S4 | Người duyệt không biết việc này chưa từng được System Manager cho phép | Đề xuất mặc định và đề xuất theo dòng trông giống nhau | Vừa | AR3-5: căn cứ chế độ hiện ở comment đề xuất và ngăn (ADR-031 A1-5) |
| R-S5 | Rủi ro còn lại sau AR3-2..AR3-5 | Người được giao (kể cả tự giao) duyệt 6 hành động có tên trên mọi đích không bị cấm: tạo tài khoản theo mẫu do System Manager đặt, thêm người vào nhóm thường, thêm ngày nghỉ, đổi nhóm hàng, Custom Field (chỉ `test`), Project. Không tách được người yêu cầu và người duyệt | Vừa | Nhật ký mỗi lần áp dụng (ADR-031 QĐ 8); cảnh báo vai trò ADR-024 đọc cả dòng bước áp dụng; As-Built và gói G5 nêu rõ (AR3-10). Muốn siết: Q-2 "cách đảo" (một commit), hoặc đề xuất mặc định chỉ Instructor duyệt (đổi AC-35, việc của người) |
| R-S6 | Chữ của model trong phiếu là dữ liệu (STD-SEC-5) | Người yêu cầu viết lệnh trong phiếu để bot đề xuất | Đã có lớp chặn | Mỗi đề xuất vẫn cần một người bấm Duyệt; "ok" trong comment không bao giờ là duyệt (AC-66); prompt không còn câu chờ "ok" (U1) |

**Điều kiện thêm.** AR3-2, AR3-3, AR3-4, AR3-5 là ràng buộc kiến trúc: chúng giữ câu của chính phụ lục "không mở thêm đường nào qua điều cấm cứng" (mục 2) và NFR-1, NFR-4. AR3-10 là câu cho người: chấp nhận R-S5, hoặc chọn một trong hai cách siết.

## 5. Điều kiện (mã AR3-n)

| Mã | Điều kiện | Chủ | Kiểm bằng | Chặn gì |
|---|---|---|---|---|
| AR3-1 | `catalog.check` theo đúng thứ tự ADR-031 A1-1. `OUT_OF_CATALOG` chỉ còn cho hành động ngoài tập A1-2 không có dòng; `RULE_DENIED` có chữ "danh mục cấm việc này"; điều cấm cứng và môi trường không nói "danh mục" | designer U7a | Ràng buộc A1 (ca thứ tự) | design U7a sửa |
| AR3-2 | "Đổi trường" không dòng phủ → từ chối, 0 đề xuất. Analyst `--amend`: AC-29 (chữ "6 hành động" và test "danh mục rỗng × 6 hành động"), AC-30, AC-33 nêu ngoại lệ "Đổi trường" và nhóm loại trừ. Người đảo được chỉ bằng ADR mới (ADR-031 "Phương án đã xét A1") | analyst; designer U7a | test A1 "Đổi trường rỗng → từ chối" | design U7a sửa; spec amend trước plan đợt 2 |
| AR3-3 | `hard_ban_reason` trả lý do cho mọi DocType `istable = 1`, dẫn xuất từ meta, không viết tay tên. Áp cả lúc lưu dòng danh mục (U0) lẫn bộ thực thi | tech-lead: một task chèn ở đợt 1 (sửa `erp_ai/agent/hard_bans.py`, `test_hard_bans.py`; sau INT-1); designer U7a nhắc lại trong bước 2 | `test_hard_bans`: `DocPerm`, `Has Role`, một bảng con tìm động; lưu dòng trỏ bảng con → chặn | merge U7a |
| AR3-4 | Thêm người vào nhóm thuộc `excluded_teams` ngoài tập A1-2: không dòng → từ chối. Vị từ nhóm loại trừ lấy từ `policy.py`, không lập danh sách | designer U7a | test A1 "nhóm loại trừ rỗng → từ chối" | design U7a sửa |
| AR3-5 | Căn cứ chế độ (dòng / mặc định) nằm trong nội dung bất biến và dấu của đề xuất bản ghi; hiện trong comment đề xuất (U7a `_comment`) và ngăn (U7b) | designer U7a, U7b | sửa căn cứ sau duyệt → `DIGEST_CHANGED`; test ngăn có khóa căn cứ | design U7a, U7b sửa |
| AR3-6 | ADR-036 toàn bộ: một hàm ghi cuối lần chạy, bộ gom, dấu hiệu, `post_comment` từ chối dấu hiệu, chống trùng đề xuất ở đường chèn duy nhất | designer U4b (chủ), U1 (prompt), U7a, U7b, U8 (trả dòng cho bộ gom thay vì đăng comment) | Ràng buộc ADR-036 | design U4b sửa trước plan đợt 1 |
| AR3-7 | Mọi phép chống trùng comment "khóa phiếu rồi đọc" (`post_notice`, BA note, hướng xử lý, đề xuất) dùng chung một hàm trợ giúp đọc có khóa (ADR-036 QĐ 4) | designer U4b | AST `for_update=True`; test hai kết nối | design U4b sửa |
| AR3-8 | "Tự làm" trong lần đưa hướng → mục "Đã làm" qua bộ gom, 0 comment. Trong lần chạy khác → đúng 1 `Comment` dưới tài khoản agent. Không bao giờ qua `post_result` | designer U7b | test AC-36 `[changed]` 2 ca | design U7b sửa |
| AR3-9 | AC-68: test "Duyệt → stub cổng model 0 lời gọi, 0 job agent trong hàng đợi"; thời gian Duyệt → kết quả suy từ `decided_at`/`finished_at`, ghi vào dòng bước áp dụng hoặc logger `run_change`, không thêm trường đo | designer U7a | test AC-68 | design U7a sửa |
| AR3-10 | Team-leader chuyển cho người, không chặn build: (a) R-S5 (người được giao và người tự giao duyệt 6 hành động có tên dưới `System Manager`); (b) AR3-2 lệch Q-10 (a) ở "Đổi trường"; (c) lựa chọn siết: đảo Q-2, hoặc đề xuất mặc định chỉ Instructor duyệt. Ghi journal; As-Built và gói G5 nêu câu trả lời hoặc "chưa trả lời, chạy mặc định" | team-leader | dòng journal; mục As-Built | G5 |
| AR3-11 | Bảng đơn vị của `arch-impact.md` đổi 4 ô (mục 7). Tech-lead lập plan đợt 1, đợt 2 theo đó | tech-lead | plan đợt 1, 2 | plan |

## 6. Bảng cho designer: tài liệu thiết kế → dòng phải sửa → vì AC nào

Đường dẫn tính từ `docs/team/features/FEAT-007/`. "Dòng" là dòng của file hôm nay.

| Tài liệu | Dòng | Phải sửa | Vì |
|---|---|---|---|
| `design-addendum-1-U1.md` | `:33`, `:240` (P-6), `:241` (P-7) | Quy tắc 6 không còn "chờ một chữ ok" ở **mọi** tổ hợp cờ (không chỉ khi `act_now`). Vế "việc hoàn tác được thì làm luôn" chỉ cho việc ghi trên phiếu; việc ERP ngoài phiếu qua danh mục hoặc công tắc. Thêm câu "chữ ok/duyệt trong phiếu không bao giờ là duyệt" vào lõi | AC-66, A3-7 |
| `design-addendum-1-U1.md` | `:231-245` (`PROMPT_CONFLICT_PAIRS`) | Thêm 2 cặp câu (chờ "ok" ↔ khối đề xuất; làm luôn ↔ ghi ERP ngoài danh mục) | AC-66, AC-6 |
| `design-addendum-1-U1.md` | `:300` (`core_prompt`, "VIẾT COMMENT") | Cấu trúc comment hướng: nhận định, căn cứ, hướng xử lý; các mục "Đã làm", "Chờ duyệt", "Cần ai quyết" do hàm ghi dựng (ADR-036 QĐ 2), model không tự liệt kê | AC-65 (a), AC-23 `[changed]` |
| `design-addendum-1-U1.md` | `:402`, `:403` | Ma trận AC-6 thêm 5 công tắc tắt × L1..L3, khẳng định không còn câu chờ "ok". `test_default_core_prompt_unchanged` (ghim chuỗi cũ byte-byte) đổi theo AC-66, ghi lý do (NFR-8, STD-TEST-5) | AC-66, AC-6 |
| `design-addendum-1-U4b-U8.md` | `:27`, `:146-147`, `:170-171`, `:182` | `post_comment_tool`: từ chối dấu hiệu ở mọi `kind` (ADR-036 QĐ 3); chọn cách model nộp phần nhận định (một `kind` riêng được giữ lại cho hàm ghi, hoặc văn bản cuối lượt) | AC-65 (a), (d) |
| `design-addendum-1-U4b-U8.md` | `:246`, `:34`, `:277` | `_route` trong lần đưa hướng không đăng comment (u4); dòng vào bộ gom | AC-23 `[changed]`, AC-65 |
| `design-addendum-1-U4b-U8.md` | `:252` | Lượt cuối: gọi hàm ghi hướng một lần (khóa phiếu, đếm có khóa); câu dự phòng khi model không viết nhận định; dòng logger "đã có hướng xử lý" | AC-65 (a), (c) |
| `design-addendum-1-U4b-U8.md` | `:172`, `:175`, `:83` | `post_notice`, BA note: đọc có khóa qua hàm trợ giúp chung (AR3-7); bảng dữ liệu `:83` thêm phép đếm hướng | AC-65, AC-23, AC-62; NFR-3 |
| `design-addendum-1-U4b-U8.md` | `:242`, `:291`, `:466` | Lần chạy lỗi sau bước định tuyến: dòng định tuyến vào thông báo lỗi hay "Đã làm" của lần chạy lại (chốt một) | AC-65 (b), AC-23 |
| `design-addendum-1-U4b-U8.md` | `:289-296`, `:416-434`, `:448` | Ma trận AC-23 + 1 ca; test AC-65 (9 chuỗi + ca ghi đè prompt rỗng); test AC-66 phiếu L1 chỉ trường phiếu và Task; danh sách test FEAT-006 đếm comment định tuyến sửa theo AC | AC-23, AC-65, AC-66 |
| `design-addendum-1-U6b.md` | `:425-432` | Thêm 2 ca AC-41: trả lời sau hướng → 0 hướng mới; trả lời sau câu hỏi dưới ngưỡng → 1 hướng. Dựa vào hàm ghi của U4b, U6b không tự kiểm | AC-41 `[changed]`, AC-65 |
| `design-addendum-2-U7a.md` | `:183-191` | Thứ tự `check` theo ADR-031 A1-1: điều cấm cứng (+ bảng con) → môi trường → `Cấm` → chế độ dòng → mặc định `Cần duyệt` cho tập A1-2 → không đổi; `category` None với hành động trong tập → mặc định | AC-29, AC-30, AC-33 `[changed]` |
| `design-addendum-2-U7a.md` | `:181`, `:177` | "Đổi trường" không dòng → từ chối; thêm thành viên vào nhóm loại trừ không dòng → từ chối | AR3-2, AR3-4; AC-29 (sau amend) |
| `design-addendum-2-U7a.md` | `:199`, `:274` | `OUT_OF_CATALOG` đổi nghĩa ("cần dòng danh mục"); `RULE_DENIED` = "danh mục cấm việc này" | AC-29 |
| `design-addendum-2-U7a.md` | `:76-93`, `:217` | Nội dung đề xuất bản ghi thêm căn cứ chế độ, vào `RECORD_DIGEST_FIELDS`; `_comment` hiện căn cứ | AR3-5 |
| `design-addendum-2-U7a.md` | `:208`, `:212`; `design-addendum-2-U7a-fixes-2.md:144`, `:161` | Comment site test: trong lần đưa hướng vào bộ gom (không `_post_comment`); lần chạy khác giữ 1 comment mỗi `run_id` | AC-23 `[changed]`, AC-12 |
| `design-addendum-2-U7a.md` | `:209-210` | Chống trùng đề xuất (cùng hành động, đích, tham số; còn chờ hoặc đã duyệt) trên đường chèn duy nhất, dưới khóa phiếu; trùng → trả đề xuất cũ cho bộ gom | AC-67, NFR-3 |
| `design-addendum-2-U7a.md` | `:361`, `:362`, `:364` | Viết lại theo NFR-8 (spec mục 8): rỗng × tập A1-2 → đề xuất; rỗng × "Đổi trường" → từ chối; ca thứ tự; `test_rule_added_between_calls` chỉ cho "Đổi trường" | AC-29, AC-30 |
| `design-addendum-2-U7a.md` | `:374`, `:380` | Thêm ca danh mục rỗng → đề xuất, đích không đổi tới Duyệt. `test_rule_removed_before_job_fails` chỉ đúng cho "Đổi trường"; thêm ca hành động có tên → vẫn áp dụng; ca dòng `Cấm` thêm trước job → `Lỗi` | AC-33, ADR-031 A1-3 |
| `design-addendum-2-U7a.md` | `:365` | Thêm ca bảng con (`DocPerm`, `Has Role`) → điều cấm cứng | AR3-3 |
| `design-addendum-2-U7a.md` | `:377`, `:381` | Thêm test AC-68: stub cổng model 0 lời gọi sau Duyệt, 0 job agent, thời gian trong dòng bước áp dụng | AC-68, AR3-9 |
| `design-addendum-2-U7b-U8.md` | `:200`, `:270` (4.2); `design-addendum-2-U7b-U8-fixes.md:183` | "Tự làm" trong lần đưa hướng → "Đã làm" qua bộ gom, không `AUTO_DONE_COMMENT`; lần chạy khác → 1 comment (agent, không `post_result`) | AC-36 `[changed]`, AC-66, AR3-8 |
| `design-addendum-2-U7b-U8.md` | `:352` | `test_category_outside_row_refused` → hành động có tên: đề xuất (mặc định); "Đổi trường": từ chối | AC-29, AC-36 |
| `design-addendum-2-U7b-U8.md` | `:270` (4.3), `:372` | Tạo Project: không dòng → đề xuất (`test_no_rule_refused` → `test_no_rule_creates_proposal`, 0 Project trước Duyệt); dòng `Cấm` → từ chối; dòng `Tự làm` → vẫn đề xuất (`APPROVAL_ONLY_ACTIONS` giữ) | AC-64 `[changed]` |
| `design-addendum-2-U7b-U8.md` | mục ngăn (4.1) và test AC-39 | Ngăn hiện căn cứ chế độ của mỗi đề xuất; mọi đề xuất `Chờ duyệt` của phiếu hiện cùng lúc | AC-67, AR3-5 |
| `design-addendum-1-U4b-U8.md` (U8) | `:175`, `:283` | BA note và Task của phiếu C: Task tạo trong lần đưa hướng vào "Đã làm"; BA note không mang dấu hiệu (AC-65 loại trừ) | AC-63, AC-65, A3-9 |

Không sửa: `design-addendum-2-U5b.md`, `design-addendum-1-U2.md`, `design-addendum-1-U3.md`. Phán quyết `arch-ruling-result-comment.md` B-0..B-16 giữ nguyên.

## 7. Bảng đơn vị và thứ tự merge của `arch-impact.md`

**Còn đúng ở khung:** không đơn vị mới; đợt 0 → cổng FEAT-004 → đợt 1 (U1 một mình → U2 ∥ U3 → U4b ∥ U6b ∥ U8) → đợt 2 (U7 → U8 AC-64 ∥ U5b). File chạm của mỗi đơn vị không đổi: ADR-036 nằm trong `runner.py`, `prompts.py`, `tools/write_ticket.py` của U4b. **Phải đổi 4 ô:**

| Ô | Hôm nay | Đổi thành | Vì |
|---|---|---|---|
| U6b, "Phụ thuộc" / "Song song được với" | U1, U3, U6a / U4b nếu khác file | Thêm phụ thuộc U4b cho 2 ca AC-41 `[changed]`. Build song song được, nhưng **merge sau U4b** | Hàm ghi hướng của U4b (ADR-036) |
| U7 (U7a, U7b), "Phụ thuộc" | U1, U3; FEAT-004 … | Thêm U4b (bộ gom, hàm ghi) và task chèn AR3-3 | AC-23 `[changed]`, AC-36 `[changed]`, ADR-031 A1-4 |
| U8 (AC-62, 63), "Song song được với" | U6b | Merge sau U4b, như `design-addendum-1-U4b-U8.md:377` đã ghi; Task trong lần đưa hướng vào bộ gom | ADR-036 QĐ 2 |
| Đợt 1, thêm một task nhỏ | — | Chữ mô tả `catalog_rules` (T10) và `permission_level` (T2) theo spec mục 4, cùng AR3-3 (`hard_bans.py` + test), sau khi `team/FEAT-007` merge `develop` (INT-1). File U0, không đụng file lõi của U1 | spec-addendum-3 mục 8; AR3-3 |

AC-69 nghiệm thu sau khi U7a, U7b vào `develop` cùng lượt, giữ như spec.

## 8. Quét NFR và chiều

| Mục | Kết luận |
|---|---|
| NFR-1 nhóm nhạy cảm | Đã quyết: AR3-4 (thêm vào nhóm loại trừ cần dòng); comment hướng chỉ trên phiếu bot được đọc (ADR-034 giữ) |
| NFR-2 giới hạn lần chạy | Đã quyết: lượt áp dụng sau Duyệt không phải lần chạy (ADR-033 QĐ 4), không gọi model (mục 3). Để designer: quét bù có xếp lại phiếu đã có hướng không |
| NFR-3 chạy lại không trùng | Đã quyết: ADR-036 QĐ 4, 5 (hướng, đề xuất) |
| NFR-4 `[changed]` | Đã quyết: danh mục rỗng → chỉ đề xuất, 0 dữ liệu đổi trước Duyệt; 5 công tắc giữ tắt; "Đổi trường" vẫn cần dòng (an toàn hơn chữ NFR-4 mới, không trái) |
| NFR-6, NFR-8 bí mật | Đã quyết: dòng "Chờ duyệt" dùng lại bộ dựng tóm tắt đề xuất (không bộ dựng mới, STD-DESIGN-4); đích qua cùng phép che (B-3) |
| Triển khai | Không đổi; không migration (không trường mới cho "đã có hướng") |
| Chủ dữ liệu | Đã quyết: comment hướng = tài khoản agent qua một hàm (ADR-036 QĐ 9); căn cứ chế độ là nội dung đề xuất (A1-5) |
| Đường ghi | Đã quyết: một hàm ghi hướng; một đường chèn đề xuất; bộ thực thi duy nhất (ADR-031 QĐ 2) |
| Lỗi, log, cấu hình | Đã quyết: từ chối = `ok=false` + mục hành động; "đã có hướng" = 1 dòng logger. Để designer: chữ lý do |
| Phân quyền | Đã quyết: A1-2, A1-4, AR3-2..AR3-5. Câu mở cho người: AR3-10 |

## 9. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR (kể cả ADR-031 A1, ADR-036) mà vẫn xung đột, rồi siết:
1. U4b đếm hướng bằng chữ tiêu đề, U7a "Căn cứ" có chữ đó → 2. Siết: dấu hiệu do mã đặt, chữ model đã thoát không tạo được (ADR-036 QĐ 3).
2. U7b gọi `_post_comment` cho "Tự làm", U4b gom → hai comment. Siết: ADR-036 QĐ 2 + Ràng buộc 3.
3. Lần chạy tạo phiếu và `@ai` song song, cả hai đếm 0. Siết: khóa phiếu + đọc có khóa (QĐ 4).
4. U7a chống trùng đề xuất trong `catalog_tools`, U8 tạo Project qua đường khác → trùng. Siết: chống trùng chỉ trên đường chèn duy nhất (QĐ 5).
5. U7a để danh mục trước điều cấm cứng; dòng `Cấm` trên `DocPerm` cho lý do "danh mục", rồi khi người xóa dòng thì thành đề xuất. Siết: A1-1 + A1-4.
6. U6b kiểm "đã có hướng" trong handler để khỏi xếp hàng (tiết kiệm NFR-2), U4b kiểm trong runner → handler đọc comment, trái ADR-033 QĐ 2. Siết: ADR-036 QĐ 7 + Ràng buộc 6.
7. U1 bỏ tool ghi khỏi hàm cấp khi đã có hướng → `@ai` sau hướng không làm được việc. Siết: QĐ 7 (hàm cấp không đầu vào mới).
8. Dòng `Cần duyệt` của "Đổi nhóm hàng" bị xóa sau khi duyệt, U7a giữ test cũ (`Lỗi`), U7b coi mặc định là `Cần duyệt` → hai kết quả. Siết: A1-3.
9. "Tự làm" trong lần chạy `@ai` báo bằng `post_result` (dòng `Info` dưới… không ai), U7a giữ hai người gọi. Siết: AR3-8.

Sau khi siết, không còn cặp nào tìm được trong phạm vi phụ lục 3.

## 10. Việc tiếp

- **Team-leader:** ghi journal "phụ lục 3: ADR-031 A1, ADR-036, AR3-1..AR3-11"; chuyển AR3-10 cho người (không chặn); gọi analyst `--amend` cho AR3-2, AR3-4 (chữ AC-29, AC-30, AC-33); gọi designer sửa theo mục 6 (U1, U4b, U6b trước plan đợt 1; U7a, U7b, U8 trước plan đợt 2); đưa ADR-031 A1 và ADR-036 cho người duyệt cùng ADR-033, ADR-035.
- **Tech-lead:** áp mục 7 vào plan; task chèn ở đợt 1 (T10/T2 chữ + AR3-3).
- **Designer:** mục 6; không cần vòng architect mới, trừ khi đổi hình dạng đã chốt ở ADR-036 QĐ 1–5.
