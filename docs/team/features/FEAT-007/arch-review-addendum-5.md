Verdict: approve-with-conditions

Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- Không có cổng cho lần soát này (chỉ G5). Để trống. -->

# Soát kiến trúc hẹp: AC-39 `[changed]` (3) của `spec-addendum-5.md`, Instructor thấy mục "Đề xuất chờ duyệt" và nút "Duyệt ngay" trong ngăn

REVIEW: ok
Quy tắc đọc hiện có đã cho người có `ERP AI Instructor` không được giao phiếu thấy mục và nút: ADR-035 QĐ 1 để DocPerm quyết với mọi người không phải chỉ-`Agent`, QĐ 2 và QĐ 3 chỉ thu hẹp người chỉ-`Agent`, còn nút đi theo vị từ duyệt duy nhất của ADR-031 QĐ 5, nên không cần amendment và không có ADR-039. Bộ nút "Duyệt ngay" + Sửa + Từ chối không trái ADR-023 QĐ 1, 2, 5 hay ADR-035 QĐ 4, 6, 7, vì "Duyệt ngay" vẫn là `approve` qua đúng method POST của ngăn (ADR-032 QĐ 2), bước xác nhận vẫn theo bit (5), và lúc áp dụng job vẫn kiểm lại người duyệt. Phần còn lệch nằm ở thiết kế, không ở ADR: theo thiết kế hiện tại, mục cũng hiện (không có nút) cho System Manager không có Instructor và cho Administrator, trái chữ mới của AC-39 (3), nên designer của U7b phải theo AR5-1..AR5-7.

Không sửa spec, thiết kế, `tasks.md`, journal, mã. Không ghi `.team/**` (không `team.py claim`) vì lệnh giao việc chỉ cho ghi file này, và một vòng build đang chạy song song. Không chạy test hay migrate. Q-21 (code và lệnh `bench` chỉ Instructor, duyệt ở form) và Q-22 (role duyệt = `ERP AI Instructor`) giữ mặc định. Tập người duyệt không nới.

## 1. Căn cứ (đọc trực tiếp ngày 2026-11-15; đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Chữ cũ và chữ mới của AC-39 về ai thấy mục | Cũ: "Chỉ người được giao phiếu (AC-35) thấy mục này; ... Instructor và System Manager thấy mọi đề xuất qua form". Mới (3): mục và nút hiện cho người được giao và Instructor; chỉ-`Agent` không giao, người tạo phiếu, tài khoản agent, Administrator, Guest thì không; System Manager không Instructor không có nút; code và `bench` không có nút | `spec-addendum-2.md:56`; `spec-addendum-5.md:47`, `:79` |
| Tập người duyệt bản ghi | Người đang được giao (giao mở) hoặc `ERP AI Instructor`; code và `bench` chỉ Instructor | `spec-addendum-2.md:54` (AC-35); ADR-031 QĐ 5 (`ADR-031.md:32`) |
| Ai đọc được đề xuất | DocPerm của DocType đề xuất: `ERP AI Agent` (create, read), `ERP AI Instructor` (read), `System Manager` (read); dòng `Agent` chỉ-đọc là của U7b, chưa dựng | `team/FEAT-007` @ `c7002de`: `erp_ai_change_proposal.json`, khối `permissions`; ADR-035 QĐ 1 (`ADR-035.md:25`) |
| Hook có xét Instructor không | Không. Người không phải "chỉ-agent-Helpdesk" → `None`, DocPerm quyết như hôm nay. Hook không được so `ROLE_INSTRUCTOR` | `design-addendum-2-U7b-U8.md:161`; ADR-035 QĐ 1, Ràng buộc 3 (`ADR-035.md:25`, `:45`) |
| Tập đọc của chỉ-`Agent` | = tập người duyệt theo phiếu (giao mở); danh sách = từng bản ghi | ADR-035 QĐ 2, QĐ 3 (`ADR-035.md:26-27`); A-U7b-4 (`design-addendum-2-U7b-U8.md:418`; fixes `:403`) |
| Ngăn lấy đề xuất thế nào | `get_list` dưới phiên người, lọc `change_kind = bản ghi`, rồi `has_permission("read")` từng cái; mục ẩn khi `proposals` rỗng; nút chỉ vẽ khi `can_decide` | `design-addendum-2-U7b-U8.md:114`, `:138`, `:142-145` |
| `can_decide` của mỗi đề xuất | `panel_summary(doc, user)`: trạng thái chờ ∧ `authority.can_decide(user, kind, ticket)`, cùng vị từ với `_decider` | fixes `:257-265`; `design-addendum-2-U7a.md:130`, `:245` |
| Tập khóa kết quả đọc của ngăn | Cố định `{ticket, ai_fields, messages, proposals, proposal_one_step}`; đúng một khóa suy từ cấu hình | fixes `:267`; ADR-035 QĐ 4 và Ràng buộc "Ngăn" (`ADR-035.md:28`, `:48`) |
| Cổng của ngăn | `is_agent()` ∧ đọc được phiếu (đọc và gửi); gửi và quyết định chặn thêm tài khoản agent | ADR-010 QĐ 3 (`ADR-010.md:51-55`); `team/FEAT-007:erp_ai/ticket_panel.py:25-40`; fixes/design `:129` |
| `is_agent` của Helpdesk | Administrator → đúng; có dòng HD Agent → theo `is_active`; không có → có role `Agent` hoặc `Agent Manager` | `apps/helpdesk/helpdesk/utils.py:31-55` |
| Method quyết định | `decide_proposal` POST, `action ∈ {approve, approve_with_edit, reject}`, chỉ đề xuất bản ghi của đúng phiếu, gọi đúng hàm controller | `design-addendum-2-U7b-U8.md:103-104`, `:127-134` |
| Đường duyệt của ADR-023 | QĐ 1: liên kết trong comment mở form Desk rồi POST; QĐ 2: job kiểm lại người duyệt; QĐ 5: controller chặn tài khoản agent; QĐ 6 điểm 2: người duyệt mở được Desk | `ADR-023.md:28-38`, `:48-54` |
| Từ chối | Trong request, dòng `Info` dưới người từ chối, 0 job | ADR-035 QĐ 6, QĐ 7 (`ADR-035.md:30-39`) |

## 2. Phán: quy tắc hiện có có cho Instructor không được giao thấy mục và nút không

**Có.** Lần theo đường gọi với một người có `ERP AI Instructor`, là agent Helpdesk, không được giao phiếu:
1. Cổng ngăn (ADR-010 QĐ 3): đạt nếu người đó là agent Helpdesk và đọc được phiếu. Instructor không là agent Helpdesk thì không có ngăn (AR5-3).
2. Đọc đề xuất: dòng DocPerm `ERP AI Instructor` cho `read`. Hai hook trả `None` vì người đó có role khác có `read` (ADR-035 QĐ 1; thiết kế `:161`). Vì vậy `get_list` và `has_permission` trả mọi đề xuất bản ghi của phiếu. Mục hiện.
3. Nút: `panel_summary.can_decide` = trạng thái chờ ∧ `can_decide(user, bản ghi, ticket)`. Vị từ ADR-031 QĐ 5 cho Instructor đúng. Nút có.
4. Bấm: `decide_proposal` → `approve` của controller → `_decider` (cùng vị từ) → job, kiểm lại bằng cùng vị từ (ADR-023 QĐ 2, ADR-031 QĐ 5).

ADR-035 QĐ 2–4 không bị chạm. QĐ 2 và QĐ 3 chỉ định nghĩa tập đọc của người chỉ-`Agent`. QĐ 4 chỉ ràng buộc bit (5) và đường import. Chữ cũ của AC-39 ("chỉ người được giao thấy mục") hẹp hơn thiết kế đã duyệt. Thiết kế chưa bao giờ lọc Instructor khỏi mục. Chữ mới khớp thiết kế ở phía Instructor, nên **không cần amendment cho ADR-035 hay ADR-023, và không có ADR-039**.

**Lệch còn lại (thiết kế, không phải ADR).** Thiết kế ẩn mục chỉ khi `proposals` rỗng (`:138`). Theo đường gọi trên, mục vẫn hiện, chỉ không có nút, cho mọi người qua được cổng ngăn và đọc được đề xuất qua DocPerm mà không thuộc tập người duyệt:
- System Manager không có Instructor: đọc qua dòng DocPerm `System Manager`.
- Administrator: `is_agent` đúng (`utils.py:38-40`), có mọi role, nhưng nằm trong `NEVER_AUTHORITY`.
- Tài khoản agent, nếu qua được cổng đọc.

Chữ mới của AC-39 (3) và ma trận của nó ("mục hiện đúng cho hai nhóm đầu") đòi không hiện cho những người này. ADR cho phép họ đọc nhưng không đòi ngăn phải hiện cho họ, nên thu hẹp ở ngăn hợp lệ. AR5-1, AR5-2 chốt cách thu hẹp để hai task không chọn lệch nhau.

## 3. Phán: bộ nút "Duyệt ngay" + Sửa + Từ chối có trái ADR-023, ADR-035 không

**Không trái.**
- ADR-023 QĐ 1 nói về liên kết trong comment (form Desk rồi POST, không GET). Ngăn là đường thứ hai, do ADR-032 QĐ 2 định: một method POST, gọi đúng `approve` / `approve_with_edit` / `reject` của controller. Không có GET đổi trạng thái, nên ADR-010 và Ràng buộc 1 của ADR-023 vẫn giữ. "Duyệt ngay" là chữ của nút `approve`, không phải đường duyệt mới.
- ADR-023 QĐ 2: Instructor không được giao bị gỡ role giữa lúc bấm và lúc job chạy → `Lỗi`, 0 thay đổi. Đây đúng là ca mà AC-39 (3) đã liệt kê.
- ADR-023 QĐ 5: `decide_proposal` chặn tài khoản agent ở cổng, còn controller chặn theo danh tính.
- ADR-035 QĐ 4: chữ AC-39 (2) giữ nghĩa của (5): tắt thì 2 thao tác, bật thì 1. Ngăn vẫn nhận đúng một bit, và method quyết định không đọc bit đó. "Tự làm luôn" sau khi bấm là AC-68, không phải bỏ bước xác nhận.
- ADR-035 QĐ 6, QĐ 7: Từ chối của Instructor trong ngăn ghi dòng `Info` dưới Instructor, ngay trong request, 0 job.
- Đề xuất code và `bench`: `_proposals` lọc `change_kind = bản ghi` (`:114`), `decide_proposal` bước 3 từ chối loại khác (`:130`). Nên 0 nút, duyệt ở form theo ADR-023 QĐ 1 và ADR-032 QĐ 5, đúng Q-21 mặc định.

Một điểm chữ, không phải xung đột ADR. Spec viết "Duyệt ngay ... là hành động đồng ý duy nhất" nhưng giữ "Sửa" (`approve_with_edit`, cũng là đồng ý, kèm giá trị sửa). AR5-5 đọc câu đó là "nút đồng ý không sửa duy nhất". Nếu analyst muốn nghĩa khác thì phải `--amend`.

## 4. Điều kiện cho designer của U7b

| # | Điều kiện | Căn cứ | Kiểm |
|---|---|---|---|
| AR5-1 | Mục "Đề xuất chờ duyệt" hiện khi và chỉ khi người phiên thuộc tập người duyệt loại bản ghi của phiếu đó, tức `authority.can_decide(user, CHANGE_KIND_RECORD, ticket)` (không xét trạng thái đề xuất). Ngăn lấy vị từ này qua module controller đề xuất, không qua vị từ thứ hai. Quyết ở server: không thuộc tập thì `proposals` là danh sách rỗng. Quy tắc phía trình duyệt giữ "ẩn khi `proposals` rỗng" (`:138`). `ticket_panel.py` và JS không so role, không gọi `authority` trực tiếp. Nút của từng đề xuất vẫn theo `panel_summary.can_decide` (trạng thái chờ ∧ cùng vị từ) | ADR-031 QĐ 5, Ràng buộc 4 (một vị từ, không so role nơi khác); ADR-035 QĐ 4 (dữ liệu đề xuất cho ngăn, kể cả "quyết được không", lấy qua controller; không import `authority`) | Test: mỗi người của ma trận AC-39 (3) → (`proposals` khác rỗng ⇔ vị từ đúng) trên phiếu có ít nhất 1 đề xuất bản ghi; System Manager không Instructor và Administrator → `proposals == []`; test kiến trúc `test_panel_imports_controller_not_authority` giữ |
| AR5-2 | Không thêm khóa nào vào kết quả đọc của ngăn. Khóa cố định giữ `{ticket, ai_fields, messages, proposals, proposal_one_step}`, đúng một khóa suy từ cấu hình | ADR-035 QĐ 4 và Ràng buộc "Ngăn"; ADR-010 QĐ 5 | `test_panel_read_keys_fixed` không đổi; 0 câu ghi SQL như cũ |
| AR5-3 | Cổng ngăn (ADR-010 QĐ 3) không nới cho Instructor. Các dòng "Instructor" của ma trận AC-39 dùng Instructor là agent Helpdesk (dòng HD Agent `is_active = 1`, hoặc role `Agent`). Instructor không là agent Helpdesk thì không có ngăn và duyệt ở form; As-Built ghi điều này | ADR-010 QĐ 3; `helpdesk/utils.py:42-55` | Fixture ma trận ghi rõ; thêm 1 ca: Instructor không là agent Helpdesk → `PermissionError` ở cổng, 0 dữ liệu |
| AR5-4 | Hai hook quyền của DocType đề xuất không thêm nhánh Instructor. Instructor đọc nhờ dòng DocPerm `ERP AI Instructor`, hook trả `None`. Ma trận của ADR-035 Ràng buộc 4 giữ nguyên, thêm dòng "Instructor không được giao, là agent Helpdesk" | ADR-035 QĐ 1, Ràng buộc 3 (hook không so `ROLE_INSTRUCTOR`) | Danh sách = từng bản ghi cho dòng mới; hook trả `None` cho dòng đó |
| AR5-5 | "Duyệt ngay" là `action = "approve"` của `decide_proposal`. `PANEL_DECISION_ACTIONS` giữ ba giá trị, không thêm method, không thêm đường duyệt. Sửa giữ `approve_with_edit` và `check_edit` ở controller. Bước xác nhận theo bit (5) như ADR-032 QĐ 4. `decide_proposal` không đọc bit đó | ADR-032 QĐ 2, QĐ 4; ADR-035 QĐ 4; ADR-023 QĐ 1 (không GET) | `test_decide_does_not_read_switches` giữ; số whitelist của `ticket_panel.py` không đổi |
| AR5-6 | Đề xuất code và `bench` không vào ngăn: giữ bộ lọc `change_kind` ở `_proposals` và bước 3 của `decide_proposal`. Instructor duyệt code và `bench` ở form (ADR-023 QĐ 1). ADR-023 QĐ 6 điểm 2 (Instructor mở được Desk) vẫn mở cho loại này; As-Built ghi | ADR-023 QĐ 1, QĐ 6; ADR-032 QĐ 5; Q-21 mặc định | Instructor không được giao × đề xuất code của phiếu → 0 nút; gọi `decide_proposal` trên đề xuất code → `PermissionError` `NOT_PANEL_PROPOSAL` |
| AR5-7 | Với Instructor không được giao: kiểm lại lúc áp dụng và Từ chối dùng đúng đường đã có. Job kiểm bằng cùng vị từ, gỡ role → `Lỗi`, 0 thay đổi. Từ chối → dòng `Info` `owner` = Instructor, trong request, 0 job | ADR-023 QĐ 2; ADR-031 QĐ 5; ADR-035 QĐ 6, QĐ 7 | Các ca AC-39 (3) "gỡ role" và Từ chối chạy với fixture Instructor không được giao |

## 5. Tự thử thách

- **Thử 1.** Task server lọc `proposals` theo vị từ. Task trình duyệt ẩn mục khi không đề xuất nào có `can_decide`. Kết quả: Instructor mở phiếu chỉ có đề xuất đã áp dụng thì một bên thấy danh sách, bên kia không. AR5-1 chặn: chỉ server quyết, vị từ không xét trạng thái, trình duyệt chỉ xét rỗng.
- **Thử 2.** U7b tự viết "Instructor hoặc được giao" trong ngăn, còn U7a dùng `can_decide`. Kết quả: lệch khi A-U7a-3 hoặc Q-22 đổi. AR5-1 chặn bằng một vị từ qua controller (ADR-031 Ràng buộc 4).
- **Thử 3.** Thêm khóa "có thể duyệt phiếu này" vào kết quả đọc. Kết quả: đổi tập khóa cố định và tạo nguồn thứ hai. AR5-2 chặn.

## 6. Không bị chạm

ADR-023, ADR-031, ADR-032, ADR-035 giữ nguyên chữ. Không amendment, không ADR-039. Câu cần architect quay lại nếu người chọn khác mặc định: Q-21 (b)/(c) (amendment ADR-012 QĐ 4 và ADR-023 QĐ 1 cho loại code), Q-22 (b)/(c) (ADR-035 QĐ 1–3 và ADR-031 QĐ 5), Q-18 (c) (ADR-031 A1-5).
