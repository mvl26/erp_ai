Feature: FEAT-002
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-002 — Bot "đang suy nghĩ" rồi trễ 3–5 giây mới trả lời, chỉnh được trong cấu hình

> **Amendment 1 (2026-11-12):** người dùng thay comment tạm bằng chỉ báo trạng thái trực tiếp. Mọi dòng có dấu `[changed — Amendment 1]` được thay bằng nội dung ở mục `## Amendment 1` cuối file; phần chữ cũ giữ lại để đối chiếu. Một điểm chờ người trả lời: `questions.md` Q1.
>
> **Cập nhật 2026-11-12:** người đã trả lời Q1 = **b** (chỉ báo riêng tiếng Việt, mã giao diện trong app `erp_ai`, không sửa mã nguồn Helpdesk). Mọi nhánh "nếu Q1 = a/c" trong Amendment 1 hết hiệu lực; AC-9..AC-11 có hiệu lực. Chi tiết và đề xuất cỡ L: mục `### Chốt sau câu trả lời Q1 (2026-11-12)` cuối file. Không còn câu hỏi mở.
>
> **Amendment 2 (2026-11-12):** research (`research.md`) cho thấy Frappe 15 không nạp handler realtime của Helpdesk, nên trên `miyano` chỉ báo "is typing" có sẵn và sự kiện `helpdesk:ticket-update` không bao giờ tới trình duyệt. Các dòng "đã có sẵn" về chúng trong Amendment 1 là sai. A-18 không áp dụng. Quyết định của người (Q1 = b) không đổi. Mọi dòng có dấu `[changed — Amendment 2]` được sửa ở mục `## Amendment 2` cuối file. Không có câu hỏi mới.

## Mục tiêu
**Giả thuyết (độ tin cậy 75%):** khi có người gọi agent bằng `@ai` trong comment, người đó muốn thấy ngay một dấu hiệu "Đang suy nghĩ…" trên phiếu, rồi câu trả lời hiện ra không sớm hơn 3–5 giây sau đó, thay vì câu trả lời bật ra như máy; câu chữ và khoảng trễ sửa được trên form cấu hình agent. Dưới 85% vì: (1) yêu cầu gốc không nói comment "đang suy nghĩ" ở lại hay biến mất (đội tự quyết, A-2); (2) chưa biết giao diện Helpdesk có hiện comment mới mà không cần tải lại trang không — nếu không, người dùng có thể không bao giờ thấy dấu hiệu (A-9); (3) "delay 3–5 s" có thể hiểu là chờ thêm sau khi model trả lời, hoặc khoảng cách tối thiểu kể từ dấu hiệu (đội chọn cách sau, A-3). **[changed — Amendment 1: giả thuyết mới ở mục Amendment 1]** **[changed — chốt Q1: giả thuyết cuối ở mục Chốt sau câu trả lời Q1]**

| Mục | Nội dung |
|---|---|
| Outcome | Mỗi lần chạy do `@ai` kích hoạt (mức `L1` trở lên) đăng ngay một comment tạm "Đang suy nghĩ…", câu trả lời xuất hiện không sớm hơn khoảng trễ đã cấu hình kể từ comment tạm, và comment tạm biến mất khi câu trả lời xuất hiện hoặc khi lần chạy kết thúc **[changed — Amendment 1]** |
| Users | Nhân viên/agent Helpdesk gõ `@ai` trong comment phiếu; quản trị viên chỉnh cấu hình agent |
| Why now | Người yêu cầu nêu trong hội thoại 2026-11-12, ngay sau khi FEAT-001 chạy được trên `miyano` (intake dòng 10) |
| Success | Lúc build: AC-1..AC-8 đạt trên site dev `miyano`, toàn bộ test của app xanh. Sau khi bàn giao (việc của người): trên `miyano`, gõ `@ai` thấy "Đang suy nghĩ…" rồi thấy câu trả lời thay chỗ (bước tay, DoD phần sau) **[changed — Amendment 1]** |
| Constraints | Commit local trên `team/FEAT-002` (nền `team/FEAT-001`), không push, không đụng `develop`/`main`; không ghi khóa API vào artifact/log/commit; không đổi giá trị `ERP AI Setting` trên `miyano` (intake dòng 28–29). Giữ nguyên mọi hành vi FEAT-001/BUG-001 ngoài phần được nêu ở đây |
| Out of scope | Hiệu ứng "đang gõ" kiểu chat theo thời gian thực; dấu hiệu cho lần chạy do tạo phiếu (`ticket_insert`); đổi giao diện Helpdesk; đổi quy tắc giới hạn lần chạy/ngày, dedup, ngân sách; chi tiết ở mục Phạm vi **[changed — Amendment 1]** |

### Đã có câu trả lời sẵn (không hỏi lại)
- "Gọi ai" = comment chứa từ khóa kích hoạt (mặc định `@ai`, trường `trigger_keyword`), trigger `comment_mention` (`erp_ai/handlers.py:100-120`, `erp_ai/constants.py:22`).
- Lần chạy do `@ai` ở `L0` bị bỏ qua, không gọi model (`erp_ai/agent/runner.py:99-101`); ở `L1+` agent đã được phép đăng comment (tool `post_comment`, nhóm `ticket_write`, `erp_ai/agent/tools/registry.py:37`; `erp_ai/agent/tools/write_ticket.py:73-83`).
- Comment do tài khoản agent viết không kích hoạt lần chạy mới (`erp_ai/handlers.py:109-110`, lý do `written_by_agent`).
- Agent đọc comment phiếu từ core `Comment`, tác giả = `owner`, mới nhất trước, ngay trước lượt lập luận đầu (`erp_ai/agent/authority.py:18-41`, `erp_ai/agent/runner.py:241`).
- Job chạy trên queue `long`, thời hạn 600 s, dừng gọi model ở 540 s (`erp_ai/agent/queue.py:29-32`, `erp_ai/constants.py:24-25`, `erp_ai/agent/runner.py:97`).
- Các số nguyên trên cấu hình có cận được kiểm khi lưu form (`INT_LIMITS`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:30-36`, `:88-93`).
- Comment tối đa 5000 ký tự (schema `post_comment`, `erp_ai/agent/tools/write_ticket.py:154`).
- Không có `docs/team/glossary.md`; thuật ngữ theo spec FEAT-001.

## Người dùng
- **Người gọi agent**: nhân viên/agent Helpdesk viết comment có `@ai` trên một phiếu gửi được cho agent. Họ cần biết agent đã nhận lời gọi và đang xử lý, rồi đọc câu trả lời.
- **Quản trị viên agent** (người sửa form `ERP AI Setting`): đặt câu chữ của dấu hiệu và khoảng trễ, hoặc tắt hẳn tính năng.
- **Người đọc phiếu về sau**: không được thấy comment "Đang suy nghĩ…" còn sót lại xen giữa lịch sử trao đổi.

## Phạm vi
- Trong:
  1. Ba mục cấu hình mới trên form agent: câu chữ dấu hiệu, khoảng trễ tối thiểu (giây), khoảng trễ tối đa (giây); giá trị mặc định và kiểm tra khi lưu (AC-1).
  2. Lần chạy `comment_mention` ở `L1+` đã qua mọi điều kiện chạy: đăng comment tạm trước lời gọi model đầu tiên (AC-2). **[changed — Amendment 1]**
  3. Khoảng trễ: câu trả lời đầu tiên không xuất hiện sớm hơn khoảng trễ của lần chạy, tính từ lúc đăng comment tạm; model chậm hơn khoảng trễ thì không chờ thêm (AC-3). **[changed — Amendment 1: mốc tính là lúc chỉ báo bắt đầu]**
  4. Gỡ comment tạm khi câu trả lời đầu tiên xuất hiện, hoặc khi lần chạy kết thúc mà không có câu trả lời, ở mọi nhánh kết thúc (AC-4). **[changed — Amendment 1]**
  5. Comment tạm không bao giờ là dữ liệu cho model, không kích hoạt lần chạy mới; comment tạm sót lại từ lần chạy bị ngắt được dọn ở lần chạy `@ai` kế tiếp của phiếu đó (AC-6). **[changed — Amendment 1]**
  6. Lỗi khi đăng/gỡ comment tạm không chặn câu trả lời (AC-7). **[changed — Amendment 1]**
- Ngoài:
  - Lần chạy `ticket_insert` (phân loại phiếu mới, kể cả khi ở `L1` nó có đăng comment) — giữ nguyên hành vi FEAT-001 (A-1). **[changed — Amendment 1: `ticket_insert` có chỉ báo, vẫn không trễ]**
  - Hiệu ứng "đang gõ" hay cập nhật trực tiếp trên giao diện; sửa SPA Helpdesk (`profile.json` `notes.ui`). **[changed — Amendment 1: chỉ báo trực tiếp nay thuộc phạm vi; sửa mã nguồn Helpdesk vẫn ngoài phạm vi]**
  - Đổi giới hạn lần chạy/phiếu/ngày, dedup job, ngân sách, số lượt mỗi lần chạy.
  - Khoảng trễ giữa các comment thứ hai trở đi trong cùng một lần chạy (A-5).
  - Đổi giá trị cấu hình trên `miyano` (việc của người).

## Dữ liệu
- **Cấu hình agent** (Single, đã có): thêm 3 mục người đặt — câu chữ dấu hiệu (văn bản, ≤ 5000 ký tự, rỗng = không đăng dấu hiệu), khoảng trễ tối thiểu và tối đa (giây, số nguyên). Tên trường, kiểu trường do designer chọn. Theo ADR-004, các mục này chỉ người ghi qua form; runner chỉ đọc.
- **Comment của phiếu** (core `Comment`, đã có): thêm một loại comment tạm do tài khoản agent viết, sống không quá một lần chạy (trừ khi job bị ngắt cứng, A-7). Cách nhận ra comment tạm do designer chọn; yêu cầu nghiệp vụ là phân biệt được nó với câu trả lời thật của agent và với comment của người. **[changed — Amendment 1: không còn comment tạm]**
- **Nhật ký từng lượt** (đã có): lỗi khi đăng/gỡ comment tạm được ghi vào nhật ký lần chạy, chỉ tên lỗi, không nội dung (AC-7, STD-SEC-6). Có cần ghi thêm khoảng trễ đã áp dụng hay không: designer quyết (A-8). **[changed — Amendment 1: lỗi khi phát chỉ báo]**
- Khối lượng: thêm tối đa 1 comment tạm mỗi lần chạy `@ai`, tức ≤ 5 comment tạm/phiếu/ngày theo giới hạn hiện có (FEAT-001 NFR-3), và mỗi cái bị gỡ trong cùng lần chạy. **[changed — Amendment 1]**
- Dữ liệu nhạy cảm: không có dữ liệu mới. Câu chữ dấu hiệu do quản trị viên nhập, coi là văn bản thường khi hiển thị (STD-SEC-3).

## Giao diện / tích hợp
- **Form `ERP AI Setting`**: thêm 3 mục ở AC-1; thông báo lỗi khi lưu bằng tiếng Việt, nêu tên mục, cùng kiểu với thông báo hiện có (`erp_ai_setting.py:93`).
- **Phiếu Helpdesk** (comment): comment tạm hiện như một comment của tài khoản agent; câu trả lời hiện như comment agent bình thường (đường `post_comment` có sẵn). **[changed — Amendment 1]**
- **Queue/job**: không thêm job, không thêm trigger. Khoảng trễ nằm trong thời hạn 540 s của lần chạy (A-6).
- Hệ thống ngoài: không đổi; số lời gọi model mỗi lần chạy không đổi.
- Quyền: tài khoản agent cần gỡ được comment do chính nó đăng trên phiếu. Helpdesk cấp CRUD `Comment` cho role `Agent` (FEAT-001 design.md dòng 45, 536); designer xác nhận quyền này đủ và không mở rộng sang comment của người. **[changed — Amendment 1: agent không gỡ bản ghi nào]**

## NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Khoảng trễ của mỗi lần chạy nằm trong [tối thiểu, tối đa] đã cấu hình; mặc định 3–5 s (intake dòng 10) | AC-3 |
| NFR-2 | Khoảng trễ không làm vượt thời hạn lần chạy hiện có (540 s gọi model, 600 s job — `constants.py:24-25`); cận trên của khoảng trễ là 30 s (A-6) | AC-1 (cận), AC-3 (thời gian chờ được trừ vào hạn chót của lần chạy) |
| NFR-3 | Không thêm lời gọi model, không thêm chi phí: số lời gọi gateway và `cost_usd` của một lần chạy `@ai` bằng đúng như trước FEAT-002 với cùng stub | AC-8 |
| NFR-4 | Không lộ nội dung: nhật ký/Error Log về comment tạm chỉ chứa mã phiếu, mã lần chạy, tên lỗi (STD-SEC-6, FEAT-001 NFR-5) **[changed — Amendment 1]** | AC-7 |

## Tiêu chí nghiệm thu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Form cấu hình có 3 mục mới với mặc định: câu chữ = `Đang suy nghĩ…`, tối thiểu = 3, tối đa = 5. Lưu bị từ chối, kèm thông báo tiếng Việt nêu tên mục, khi: tối thiểu hoặc tối đa < 0 hoặc > 30, tối thiểu > tối đa, câu chữ > 5000 ký tự. Lưu được khi 0 ≤ tối thiểu ≤ tối đa ≤ 30 (gồm 0/0 và tối thiểu = tối đa) và khi câu chữ rỗng **[changed — Amendment 1: chỉ đổi nghĩa của câu chữ, cận và mặc định giữ nguyên]** | Test tự động trên DocType: mỗi trường hợp từ chối một test (`frappe.ValidationError`), các trường hợp hợp lệ lưu được; test đọc mặc định của DocType mới tạo |
| AC-2 | Lần chạy `comment_mention` ở `L1+` đã qua mọi kiểm tra (bật, gửi được, chưa hết lượt/ngày, mức ≠ `L0`) và câu chữ ≠ rỗng → đúng 1 comment tạm của tài khoản agent, nội dung = câu chữ cấu hình, đã tồn tại trên phiếu tại thời điểm lời gọi model đầu tiên bắt đầu **[changed — Amendment 1]** | Test tự động với stub gateway: trong stub, đếm comment tạm của phiếu = 1 và đọc nội dung |
| AC-3 | Gọi `d` là khoảng trễ của lần chạy, `d` ∈ [tối thiểu, tối đa]. (a) Model trả lời ngay → comment trả lời đầu tiên được tạo không sớm hơn `d` giây sau comment tạm; (b) tối thiểu = tối đa = `k` → `d = k`; (c) model mất lâu hơn `d` → không có thời gian chờ thêm nào trước khi đăng câu trả lời; (d) tối thiểu = tối đa = 0 → không chờ. Thời gian chờ được tính vào hạn chót của lần chạy **[changed — Amendment 1: mốc "sau comment tạm" thành "sau lúc chỉ báo bắt đầu"]** | Test tự động với đồng hồ/thời gian chờ giả lập: ghi lại thời gian chờ thực áp dụng ở từng nhánh; chạy (a) nhiều lần với tối thiểu ≠ tối đa, mọi `d` nằm trong khoảng |
| AC-4 | Comment tạm không còn trên phiếu: (a) ngay khi comment trả lời đầu tiên của lần chạy được tạo — tại thời điểm đó phiếu có comment trả lời và 0 comment tạm; (b) khi lần chạy kết thúc không đăng comment nào, ở mọi nhánh: model không gọi `post_comment`, lỗi gateway, hết hạn thời gian, hết số lượt, tool lỗi, ngoại lệ bất kỳ trong runner **[changed — Amendment 1]** | Test tự động, mỗi nhánh một test: sau `run_for_ticket`, số comment tạm của phiếu = 0; nhánh (a) kiểm trong stub của lượt kế tiếp |
| AC-5 | Không đăng comment tạm và không chờ khi: trigger `ticket_insert` (mọi mức); lần chạy bị bỏ qua (`agent` tắt, `not_sendable`, `daily_limit`, `level_L0`); câu chữ rỗng. Câu chữ rỗng nhưng khoảng trễ > 0 → không comment tạm, câu trả lời vẫn tuân AC-3 tính từ lúc lần chạy bắt đầu lập luận (A-3) **[changed — Amendment 1]** | Test tự động mỗi nhánh: 0 comment tạm; thời gian chờ đo được = 0 ở các nhánh bị bỏ qua và `ticket_insert` |
| AC-6 | (a) Nội dung gửi cho model ở mọi lượt không chứa comment tạm (của lần chạy này hay sót lại từ lần trước); (b) tạo comment tạm không kích hoạt lần chạy mới (handler ghi `written_by_agent`); (c) một lần chạy `@ai` vẫn tính đúng 1 lần chạy cho giới hạn/ngày; (d) phiếu có comment tạm sót lại từ lần chạy bị ngắt → lần chạy `@ai` kế tiếp của phiếu đó gỡ nó, comment của người và câu trả lời cũ của agent không bị đụng **[changed — Amendment 1]** | Test tự động: kiểm `messages` gửi tới stub; kiểm hàng đợi rỗng sau khi đăng comment tạm; đếm `runs_today`; gieo một comment tạm cũ + 1 comment người + 1 comment agent rồi chạy, sau đó chỉ comment tạm cũ biến mất |
| AC-7 | Đăng hoặc gỡ comment tạm thất bại (thiếu quyền, ngoại lệ) → lần chạy vẫn gọi model và đăng câu trả lời như khi không có tính năng; lỗi được ghi vào nhật ký lần chạy chỉ gồm tên lỗi, không có câu chữ dấu hiệu hay nội dung phiếu **[changed — Amendment 1]** | Test tự động: làm hỏng bước đăng và bước gỡ (hai test), kiểm có comment trả lời và bản ghi nhật ký có lỗi; kiểm chuỗi câu chữ không có trong nhật ký/Error Log |
| AC-8 | Không đổi hành vi cũ: toàn bộ test hiện có của app xanh; với cùng stub, số lời gọi gateway và tổng `cost_usd` của một lần chạy `@ai` bằng trước FEAT-002 | `cmd.test` (`bench --site miyano run-tests --app erp_ai`) xanh, dán đầu ra; một test tự động so số lời gọi stub và `cost_usd` |

## Assumptions decided by the team
Mode `decide` (intake dòng 15): không có câu hỏi cho người; mỗi điểm lớn ghi đủ 4 mục.

- **A-1 Chỉ áp dụng cho `@ai`.** Chọn: chỉ trigger `comment_mention`. Vì: "khi gọi ai" là người chủ động gọi; `ticket_insert` không do ai gọi và chủ yếu là phân loại. Thay thế: áp dụng cả cho `ticket_insert` ở `L1` khi nó định đăng comment. Sai thì: thêm một AC như AC-2..AC-4 cho `ticket_insert`, bỏ dòng tương ứng ở AC-5. **[changed — Amendment 1: chỉ báo áp dụng cả `ticket_insert`; khoảng trễ vẫn chỉ cho `@ai`, xem A-11]**
- **A-2 Comment tạm biến mất, câu trả lời là comment mới.** Chọn: gỡ comment tạm khi câu trả lời đầu tiên xuất hiện hoặc khi lần chạy kết thúc. Vì: để lại thì mỗi phiếu tích lũy comment "Đang suy nghĩ…" vô nghĩa và sai lệch (dấu hiệu nói đang suy nghĩ khi đã xong); câu trả lời là comment mới thì giữ đúng thời điểm tạo dùng cho AC-3 và đường đăng comment hiện có. Thay thế: (i) sửa comment tạm thành câu trả lời; (ii) để lại comment tạm. Sai thì: (i) amend AC-3/AC-4 để đo trên lần sửa thay vì lần tạo; (ii) bỏ AC-4, AC-6(d). **[changed — Amendment 1: người bỏ comment tạm, thay bằng chỉ báo]**
- **A-3 Khoảng trễ là khoảng cách tối thiểu, có bù thời gian model.** Chọn: câu trả lời không sớm hơn `d` giây kể từ comment tạm (hoặc kể từ lúc bắt đầu lập luận nếu không đăng comment tạm); thời gian model đã chạy được trừ vào. Vì: yêu cầu là "không trả lời luôn"; bản thân lời gọi model đã mất vài giây, chờ cộng thêm sẽ làm chậm vô ích. Thay thế: luôn chờ thêm `d` sau khi model trả lời. Sai thì: đổi AC-3(c) thành "chờ đúng `d` sau khi model trả lời".
- **A-4 Khoảng ngẫu nhiên tối thiểu–tối đa.** Chọn: hai mục tối thiểu/tối đa, mỗi lần chạy lấy một giá trị trong khoảng; tối thiểu = tối đa cho giá trị cố định; 0/0 = tắt trễ. Vì: người yêu cầu nói "khoảng 3–5 s"; khoảng ngẫu nhiên tự nhiên hơn và vẫn cho phép một giá trị cố định. Thay thế: một mục giây duy nhất. Sai thì: gộp thành một mục, AC-1 và AC-3(b) đổi theo.
- **A-5 Chỉ trễ trước câu trả lời đầu tiên.** Chọn: các comment sau trong cùng lần chạy (nếu model đăng nhiều) không bị trễ thêm. Vì: dấu hiệu chỉ có một và chỉ có ý nghĩa trước câu trả lời đầu. Thay thế: trễ trước mỗi comment. Sai thì: mở rộng AC-3 cho mọi comment của lần chạy.
- **A-6 Cận trên 30 s, mặc định 3/5 s.** Chọn: 0 ≤ tối thiểu ≤ tối đa ≤ 30. Vì: mặc định lấy từ intake; 30 s là giới hạn đội chọn — 6 lần mặc định tối đa, vẫn rất nhỏ so với 540 s của lần chạy (`constants.py:24-25`), và một lời trễ dài hơn nửa phút chỉ làm người dùng tưởng agent hỏng. Không có số đo nào trong repo cho cận này. Thay thế: không có cận trên ngoài thời hạn lần chạy. Sai thì: đổi số trong AC-1 và NFR-2.
- **A-7 Comment tạm sót lại khi job bị ngắt cứng.** Chọn: nếu worker bị giết (vượt 600 s, khởi động lại) thì comment tạm có thể còn tới lần chạy `@ai` kế tiếp của phiếu đó, lần chạy ấy dọn nó (AC-6(d)); không thêm job dọn định kỳ. Vì: trường hợp hiếm, thêm job định kỳ là phạm vi lớn hơn yêu cầu. Thay thế: job định kỳ dọn comment tạm quá hạn. Sai thì: thêm một AC cho job dọn, đổi cỡ nếu cần. **[changed — Amendment 1: thay bằng A-16]**
- **A-8 Bật sẵn sau khi migrate.** Chọn: mặc định 3/5 s và câu chữ `Đang suy nghĩ…` áp dụng ngay khi cập nhật app, quản trị viên tắt bằng 0/0 và câu chữ rỗng. Vì: người yêu cầu muốn đây là hành vi chuẩn. Thay thế: mặc định tắt. Sai thì: đổi mặc định ở AC-1 thành 0/0 và rỗng. Việc ghi khoảng trễ đã áp dụng vào nhật ký: không bắt buộc, designer quyết.
- **A-9 Hiển thị trên giao diện Helpdesk.** Chọn: spec chỉ cam kết hành vi phía server (comment tạm tồn tại rồi biến mất đúng lúc); việc giao diện có hiện comment mới mà không tải lại trang hay không được kiểm bằng tay sau khi bàn giao. Vì: `profile.json` `ui: false`, SPA Helpdesk không thuộc app. Thay thế: thêm thay đổi giao diện. Sai thì: nếu bước tay cho thấy người dùng không thấy dấu hiệu nếu không tải lại, mở feature mới cho phần hiển thị trực tiếp. **[changed — Amendment 1: hiển thị trực tiếp nay thuộc phạm vi, cách hiện chờ Q1]** **[changed — chốt Q1 = b: chỉ báo riêng, mã giao diện trong app `erp_ai`]**
- **A-10 Dedup khi đang chờ.** Chọn: một `@ai` thứ hai trên cùng phiếu trong lúc lần chạy trước đang chờ/suy nghĩ xử lý như hiện nay (job trùng id bị bỏ, `queue.py:17`, `:35`). Vì: không đổi quy tắc dedup (Phạm vi → Ngoài); khoảng trễ chỉ làm cửa sổ này dài thêm tối đa 30 s. Thay thế: xếp hàng lần gọi thứ hai. Sai thì: feature riêng về dedup.

## Đề xuất về cỡ
- Không đổi: 8 AC, một nhóm hành vi liền nhau trên runner + cấu hình; vừa cỡ M của intake. **[changed — Amendment 1: xem mục Đề xuất về cỡ của Amendment 1]** **[changed — chốt Q1: đề xuất L, xem mục Chốt sau câu trả lời Q1]**

## Definition of Done
**Phần build (trước khi bàn giao):**
- [ ] AC-1..AC-8 đạt, đầu ra lệnh được dán trong `acceptance.md` **[changed — Amendment 1: AC-1..AC-11]**
- [ ] Mỗi AC có ít nhất một test tự động (STD-TEST-2); không có skip/xfail (STD-TEST-4)
- [ ] `cmd.test` xanh trên `team/FEAT-002`; `cmd.lint` sạch
- [ ] `cmd.migrate` chạy được trên `miyano`, 3 mục mới hiện trên form với mặc định ở AC-1 (không đổi giá trị cấu hình khác trên `miyano`)
- [ ] Commit local trên `team/FEAT-002`, không push

**Phần sau G4 / sau bàn giao (`/team:asbuilt`, người):**
- [ ] As-Built viết xong (`asbuilt.md`) — `/team:asbuilt`
- [ ] README/tài liệu người dùng: mô tả 3 mục cấu hình mới và cách tắt — `/team:asbuilt`
- [ ] Mục CHANGELOG — `/team:asbuilt`
- [ ] CI xanh
- [ ] Bước tay trên `miyano` (người, A-9): ở mức `L1+`, gõ comment `@ai …` trên một phiếu gửi được → thấy comment "Đang suy nghĩ…" của agent, rồi thấy câu trả lời và comment tạm biến mất; ghi kết quả (có cần tải lại trang không) vào `acceptance.md` **[changed — Amendment 1: thay bằng bước tay AC-10]**

## Amendment 1 (2026-11-12)

### Nguồn và lý do
- Người dùng chốt qua team-leader (AskUserQuestion 2026-11-12), nguyên văn: "Làm dạng như claude cạy đó, nếu nó đang làm hay đang suy nghĩ thì viết là ... đang suy nghĩ, đang làm để người dùng biết ai đang hoạt động, tăng UI/UX. tránh ai đang chạy mà ko hiển thị gì để user theo dõi".
- Lý do: comment tạm phải bị xóa, trái ADR-004 quyết định 1 và 6 (`design.md` mục 1.3, `DESIGN_CONFLICT`). Người không muốn sửa ADR-004.
- Ràng buộc của người (qua team-leader): không sửa ADR-004; giữ khoảng trễ 3–5 s chỉnh được trong cấu hình; ưu tiên cách hiện không phải sửa giao diện Helpdesk; chỉ báo không được kẹt khi lần chạy lỗi/hết thời gian.

### Giả thuyết mới (độ tin cậy 80%)
Trong suốt một lần chạy của agent, ai đang mở trang phiếu đó trên Helpdesk thấy một chỉ báo trực tiếp: tên tài khoản agent và việc nó đang làm ("Đang suy nghĩ…", "Đang làm: <việc>…"). Chỉ báo tự mất khi lần chạy kết thúc ở mọi nhánh, không để lại gì trên phiếu. Câu trả lời vẫn trễ 3–5 s, chỉnh được. Dưới 85% vì: (1) chưa biết người có nhận một đoạn mã giao diện chạy trên trang phiếu Helpdesk không (Q1); (2) chưa biết cách hiện riêng có làm được mà không sửa mã nguồn Helpdesk không (researcher kiểm, xem "Đã có câu trả lời sẵn"). **[changed — chốt Q1: (1) đã trả lời, xem mục Chốt sau câu trả lời Q1]**

### Đã có câu trả lời sẵn (đọc mã, không hỏi lại)
- **Helpdesk đã có sẵn chỉ báo "đang gõ".** Trang phiếu phía agent (desktop và mobile) hiện `<tên> is typing` kèm ba chấm động dưới khung soạn (`helpdesk/desk/src/components/TypingIndicator.vue:1-60`, gắn ở `CommunicationArea.vue:32`). Nó nghe sự kiện `helpdesk_ticket_typing` / `helpdesk_ticket_typing_stopped` mang `{ticket_id, user}` (`desk/src/composables/realtime.ts:64-90`), được chuyển tới phòng `open_doc:HD Ticket/<tên>` (`helpdesk/realtime/handlers.js`, `frappe/realtime/handlers/frappe_handlers.js:192`). Chữ "is typing" viết cứng bằng tiếng Anh. Phía nhận không có hạn tự tắt: mất tín hiệu dừng thì chỉ báo nằm tới khi tải lại trang. Có phát được sự kiện này từ worker phía server không: researcher kiểm. **[changed — Amendment 2: SAI trên `miyano` — Frappe 15 không nạp `helpdesk/realtime/handlers.js`, tín hiệu không bao giờ tới trình duyệt; xem Amendment 2]**
- **Trang phiếu tự tải lại khi phiếu được lưu** (sự kiện `helpdesk:ticket-update`, `hd_ticket.py:73-77`, nghe ở `TicketAgent.vue:226-230`). **[changed — Amendment 2: SAI trên `miyano` — sự kiện phát vào phòng `open_doc:` không ai vào; xem Amendment 2]**
- **Khách cũng vào cùng phòng realtime của phiếu** (`TicketCustomer.vue:401-404`), nhưng trang khách không gắn chỉ báo "đang gõ".
- **HD Form Script chạy trên trang phiếu agent** nhận một ngữ cảnh gồm `call, router, toast, $dialog, updateField, createToast`, không có kênh realtime (`TicketHeader.vue:320-327`, `formCustomisation.ts:93`). Có dùng được để hiện chỉ báo riêng không: researcher kiểm. **[changed — Amendment 2: research đã trả lời, xem Amendment 2]**
- **Lần chạy nào gọi model:** `ticket_insert` gọi model để phân loại ở mọi mức, kể cả `L0`; `comment_mention` chỉ gọi ở `L1+` (`runner.py:99-117`).
- **Ghi một trường trạng thái lên HD Ticket** sẽ thêm một người ghi mới vào bảng chủ ghi của ADR-004 (hàng "HD Ticket": chỉ tool ghi ở `L1`), và bị cấm ở `L0` (quyết định 4). Vì vậy cách đó trái ràng buộc "không sửa ADR-004", và bị loại ở mục Phạm vi.

### Thay đổi phạm vi
- Trong (thay mục 2, 4, 5, 6 cũ):
  - 2'. Chỉ báo trạng thái trực tiếp cho mọi lần chạy có gọi model: `comment_mention` ở `L1+` và `ticket_insert` ở mọi mức, sau khi đã qua mọi kiểm tra (AC-2, AC-5).
  - 4'. Chỉ báo kết thúc ở mọi nhánh: có trả lời, không trả lời, lỗi gateway, hết thời gian, hết số lượt, tool lỗi, ngoại lệ bất kỳ (AC-4).
  - 5'. Trạng thái việc: "Đang làm: <việc>…" khi agent chạy một tool hoặc bước phân loại (AC-9).
  - 6'. Lỗi khi phát chỉ báo không chặn lần chạy (AC-7).
  - 7. Người đang xem trang phiếu agent thấy chỉ báo mà không tải lại trang (AC-10). Cách hiện: chờ Q1. **[changed — chốt Q1 = b: chỉ báo riêng tiếng Việt, mã giao diện trong app `erp_ai`]**
- Ngoài (thêm):
  - Mọi cách hiện mà phải tạo, sửa hay xóa bản ghi chỉ để hiện chỉ báo (comment tạm, trường trạng thái trên HD Ticket, Task…). Lý do: giữ nguyên ADR-004.
  - Sửa mã nguồn app Helpdesk.
  - Chỉ báo khi job còn nằm chờ trong hàng đợi, trước khi lần chạy bắt đầu (A-17).
  - Lịch sử các trạng thái của một lần chạy. Nhật ký lần chạy hiện có không đổi.
- Không đổi: khoảng trễ (mục 3, mốc tính mới ở AC-3), 3 mục cấu hình (mục 1), giới hạn lần chạy, dedup, ngân sách.

### Dữ liệu (thay đoạn "Comment của phiếu" và "Khối lượng")
- Không thêm và không sửa bản ghi nghiệp vụ nào để hiện chỉ báo. Số bản ghi `Comment`, `HD Ticket`, `Task` do một lần chạy tạo ra hay sửa đi giống hệt như khi tắt tính năng.
- Chỉ báo chỉ mang: tên phiếu, tài khoản agent, trạng thái (suy nghĩ / làm việc / kết thúc), câu chữ cấu hình và nhãn việc. Nó không mang nội dung phiếu, tham số tool, câu trả lời hay tên khách (NFR-4').
- Câu chữ cấu hình (AC-1) là chữ của trạng thái "đang suy nghĩ"; rỗng = tắt chỉ báo. Nhãn việc là chữ tiếng Việt cố định, một nhãn cho mỗi tool hoặc bước (A-15).
- Lỗi khi phát chỉ báo được ghi vào trường lỗi có sẵn của nhật ký lần chạy, chỉ tên lỗi.

### Giao diện (thay dòng "Phiếu Helpdesk" và "Quyền")
- **Trang phiếu Helpdesk phía agent:** hiện chỉ báo theo phương án người chọn ở Q1. Trang phiếu phía khách không hiện chỉ báo (A-13). **[changed — chốt Q1 = b]**
- **Quyền:** agent không xóa và không sửa bản ghi nào để hiện chỉ báo. Không cần quyền mới.

### NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1..NFR-3 | Giữ nguyên | AC-3, AC-1, AC-8 |
| NFR-4' [changed] | Không lộ nội dung: chỉ báo và các dòng nhật ký/Error Log về chỉ báo chỉ chứa mã phiếu, mã lần chạy, tài khoản agent, trạng thái, câu chữ cấu hình, nhãn việc, tên lỗi (STD-SEC-6, FEAT-001 NFR-5) | AC-7, AC-9 |
| NFR-5 | Chỉ báo mất trên trang đang mở, không cần tải lại, chậm nhất 10 s sau khi lần chạy kết thúc ở nhánh thường. Số 10 s lấy theo mức Helpdesk tự dùng cho chỉ báo "đang gõ" (`realtime.ts:106-119`, 10000 ms) (A-12) | AC-10 |
| NFR-6 | Không thêm lời gọi model. Không thêm bản ghi `Comment`/`HD Ticket`/`Task` | AC-2, AC-8 |

### Tiêu chí nghiệm thu đổi và thêm
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 [changed] | Như cũ: 3 mục, mặc định `Đang suy nghĩ…` / 3 / 5, cùng các cận và thông báo. Chỉ đổi nghĩa: câu chữ là chữ của trạng thái "đang suy nghĩ" trong chỉ báo; rỗng = tắt chỉ báo, khoảng trễ vẫn áp dụng. Nếu Q1 = a thì câu chữ chỉ còn vai trò bật/tắt (khác rỗng = bật) **[changed — chốt Q1 = b: nhánh "Q1 = a" bỏ; câu chữ hiện đúng nguyên văn trên chỉ báo]** | Như cũ |
| AC-2 [changed] | Lần chạy đã qua mọi kiểm tra và có gọi model (`comment_mention` ở `L1+`; `ticket_insert` ở mọi mức), câu chữ ≠ rỗng → tín hiệu "bắt đầu / đang suy nghĩ" được phát trước lời gọi model đầu tiên, mang tên phiếu, tài khoản agent và câu chữ cấu hình. Lần chạy không tạo, sửa hay xóa thêm bản ghi `Comment`, `HD Ticket`, `Task` nào so với khi tắt tính năng | Test tự động với stub gateway: ghi lại các tín hiệu; tại lời gọi model đầu tiên đã có đúng 1 tín hiệu bắt đầu. So số `Comment`/`Task` và `modified` của phiếu giữa lần bật và lần tắt tính năng, với cùng stub |
| AC-3 [changed] | Như cũ (a)–(d), nhưng mốc "sau comment tạm" đổi thành "sau lúc phát tín hiệu bắt đầu". Câu chữ rỗng → mốc là lúc bắt đầu lập luận. Chỉ áp dụng cho `comment_mention` (A-11). Trong lúc chờ, chỉ báo ở trạng thái "đang suy nghĩ" | Như cũ |
| AC-4 [changed] | Mỗi lần chạy đã phát tín hiệu bắt đầu thì phát đúng 1 tín hiệu kết thúc, trước khi lần chạy trả về, ở mọi nhánh: có câu trả lời, model không gọi `post_comment`, lỗi gateway, hết thời gian, hết số lượt, tool lỗi, ngoại lệ bất kỳ trong runner. Tín hiệu kết thúc là tín hiệu cuối của lần chạy | Test tự động, mỗi nhánh một test: chuỗi tín hiệu ghi lại kết thúc bằng đúng 1 tín hiệu kết thúc |
| AC-5 [changed] | Không phát tín hiệu nào và không chờ khi lần chạy bị bỏ qua: agent tắt, `not_sendable`, `daily_limit`, `comment_mention` ở `L0`. Câu chữ rỗng → không phát tín hiệu, khoảng trễ vẫn áp dụng cho `comment_mention`. `ticket_insert` → có chỉ báo (theo AC-2, AC-4, AC-9), không chờ | Test tự động mỗi nhánh: số tín hiệu = 0 ở nhánh bị bỏ qua và khi câu chữ rỗng; thời gian chờ = 0 ở nhánh bị bỏ qua và ở `ticket_insert` |
| AC-6 [changed] | (a), (b), (d) cũ bỏ, vì không còn comment tạm. (c) giữ: một lần chạy `@ai` vẫn tính đúng 1 lần cho giới hạn/ngày. Thêm (e): `messages` gửi cho model ở mọi lượt giống hệt khi tắt tính năng, với cùng stub | Test tự động: đếm `runs_today`; so `messages` của stub giữa lần bật và lần tắt |
| AC-7 [changed] | Phát tín hiệu thất bại (ngoại lệ) ở bất kỳ bước nào → lần chạy vẫn gọi model, vẫn đăng câu trả lời như khi không có tính năng, và vẫn cố phát tín hiệu kết thúc. Lỗi ghi vào nhật ký lần chạy chỉ gồm tên lỗi, không có câu chữ cấu hình hay nội dung phiếu | Test tự động: làm hỏng bước phát (bắt đầu, việc, kết thúc; mỗi bước một test), kiểm có comment trả lời và nhật ký có tên lỗi; kiểm chuỗi câu chữ không có trong nhật ký/Error Log |
| AC-8 | Giữ nguyên | Giữ nguyên |
| AC-9 [mới] | Khi agent chạy một tool, hoặc bước phân loại của `ticket_insert`, thì phát tín hiệu "Đang làm: <nhãn>" trước khi việc đó chạy, rồi quay về "đang suy nghĩ" trước lời gọi model kế tiếp. Mỗi tool mà runner có thể cấp và bước phân loại đều có một nhãn tiếng Việt khác rỗng. Nhãn không chứa tham số tool hay nội dung phiếu. Nếu Q1 = a thì phần chữ không hiện trên giao diện, nhưng tín hiệu vẫn đúng như trên **[changed — chốt Q1 = b: có hiệu lực đầy đủ; nhánh "Q1 = a" bỏ; nhãn hiện trên chỉ báo, kiểm ở AC-10]** | Test tự động: stub cho model gọi 1 tool đọc rồi `post_comment` → chuỗi tín hiệu = [bắt đầu/suy nghĩ, làm: <nhãn tool đọc>, suy nghĩ, làm: <nhãn post_comment>, kết thúc]. Một test duyệt mọi tool trong registry, kiểm nhãn khác rỗng. Một chuỗi đánh dấu trong tham số tool không xuất hiện trong tín hiệu nào |
| AC-10 [mới] | Trên `miyano`, người đang mở trang phiếu agent (desktop) thấy chỉ báo kèm tên tài khoản agent khi gõ `@ai …` ở `L1+`, không cần tải lại trang. Chỉ báo mất chậm nhất 10 s sau khi câu trả lời hiện ra (NFR-5). Một lần chạy có lỗi (ví dụ không có khóa API hợp lệ) cũng không để chỉ báo kẹt quá 10 s. Trang phiếu phía khách không hiện chỉ báo. Q1 = b: chữ hiện là câu chữ cấu hình và "Đang làm: <nhãn>…" **[changed — chốt Q1 = b: có hiệu lực; thêm các ý ở mục Chốt sau câu trả lời Q1]** **[changed — Amendment 2: thêm ý (h), (i)]** | Bước tay (`ui: false`, không có Playwright), người làm sau bàn giao: làm theo kịch bản, ghi kết quả từng ý, kèm ảnh chụp nếu có, vào `acceptance.md` |
| AC-11 [mới, chỉ khi Q1 = b] | Nếu không nhận được tín hiệu kết thúc (worker bị giết), chỉ báo tự mất trên trang đang mở chậm nhất 600 s sau tín hiệu bắt đầu (bằng thời hạn job `JOB_TIMEOUT_S`, `constants.py:24`), và không hiện lại khi tải lại trang **[changed — chốt Q1 = b: có hiệu lực]** | Bước tay hoặc test của phần hiện chỉ báo, nếu researcher tìm ra cách test tự động: phát tín hiệu bắt đầu mà không phát kết thúc, chờ quá hạn **[changed — Amendment 2: cách kiểm theo J1, xem Amendment 2]** |

Thứ tự bỏ trước nếu phải cắt: AC-11, rồi phần "Đang làm" của AC-9. AC-2..AC-5 là cốt lõi.

### Assumptions decided by the team (thêm)
- **A-11 Chỉ báo cho mọi lần chạy gọi model, khoảng trễ chỉ cho `@ai`** (thay A-1).
  - Chọn: chỉ báo cho `comment_mention` ở `L1+` và `ticket_insert` ở mọi mức. Khoảng trễ chỉ áp dụng cho `comment_mention`.
  - Vì: người nói "tránh ai đang chạy mà ko hiển thị gì". Chỉ báo không ghi bản ghi nào, nên hiện ở `L0` không trái ADR-004 quyết định 4. Trễ phân loại phiếu mới thì không ai được lợi.
  - Thay thế: chỉ báo chỉ cho `@ai`, như A-1 cũ.
  - Sai thì: thêm nhánh `ticket_insert` vào AC-5 (không phát tín hiệu); bỏ phần `ticket_insert` ở AC-2 và AC-9.
- **A-12 Người mở trang giữa chừng.**
  - Chọn: người mở trang phiếu khi lần chạy đã bắt đầu thấy chỉ báo chậm nhất từ lần đổi trạng thái kế tiếp (bước làm việc hoặc lời gọi model kế tiếp).
  - Vì: không phải phát nhắc lại theo chu kỳ trong lúc chờ model. 10 s ở NFR-5 lấy theo mức Helpdesk tự dùng, không phải số đo của dự án.
  - Thay thế: thấy trong ≤ 10 s kể từ lúc mở trang.
  - Sai thì: thêm một ý vào AC-10 và cho designer cách nhắc lại hoặc tra trạng thái.
- **A-13 Khách không thấy chỉ báo.**
  - Chọn: chỉ trang phiếu phía agent hiện chỉ báo.
  - Vì: hoạt động của agent AI là việc nội bộ; ở `L0` agent chạy ngầm (chỉ ghi nhật ký) và khách không cần biết.
  - Thay thế: khách cũng thấy "đang suy nghĩ".
  - Sai thì: thêm một ý cho trang khách vào AC-10.
- **A-14 Chỉ báo không ghi bản ghi nào** (thay A-2, A-7).
  - Chọn: hiện chỉ báo không tạo, sửa hay xóa bản ghi nghiệp vụ nào. Cơ chế cụ thể do researcher/designer chọn.
  - Vì: người cấm sửa ADR-004. Comment tạm và trường trạng thái trên phiếu đều đụng bảng chủ ghi; một bản ghi còn lại khi worker chết thì kẹt "đang suy nghĩ".
  - Thay thế: một trường trạng thái trên HD Ticket, cần ADR mới.
  - Sai thì: architect viết ADR mới; amend AC-2 (bỏ ý "không thêm bản ghi") và AC-11.
- **A-15 Nhãn việc.**
  - Chọn: chữ tiếng Việt ngắn, cố định trong mã, một nhãn cho mỗi tool hoặc bước, ví dụ "đọc phiếu", "đọc comment", "tra nguồn", "phân loại phiếu", "viết trả lời". Câu chữ cuối do designer chốt; quản trị viên không sửa được.
  - Vì: người chỉ yêu cầu sửa được delay; thêm một mục cấu hình cho mỗi nhãn làm phình form.
  - Thay thế: nhãn sửa được trên cấu hình.
  - Sai thì: thêm bảng nhãn vào AC-1.
- **A-16 Chỉ báo kẹt khi worker bị giết** (thay A-7).
  - Chọn: Q1 = b → tự mất theo AC-11. Q1 = a → chỉ báo sẵn có của Helpdesk không có hạn tự tắt, nên nằm tới khi người tải lại trang. Đây là rủi ro đã nêu trong Q1. **[changed — chốt Q1 = b: áp dụng nhánh b, tự mất theo AC-11]** **[changed — Amendment 2: nhánh Q1 = a cũng không chạy trên `miyano`; chỉ còn nhánh b]**
  - Vì: trường hợp hiếm; ở mọi nhánh lỗi thường, tín hiệu kết thúc đã có AC-4.
  - Thay thế: không có, nếu không sửa Helpdesk.
  - Sai thì: chọn b ở Q1.
- **A-17 Không có chỉ báo lúc job chờ hàng đợi.**
  - Chọn: chỉ báo bắt đầu khi lần chạy bắt đầu (sau các kiểm tra), không bắt đầu từ lúc comment `@ai` được lưu.
  - Vì: người nói "đang chạy". Lúc job còn chờ thì chưa biết lần chạy có bị bỏ qua hay không.
  - Thay thế: hiện "Đang chờ…" ngay khi xếp job.
  - Sai thì: thêm một AC cho lúc xếp job, kèm tín hiệu kết thúc khi job bị bỏ qua.

### Ảnh hưởng tới các artifact sau
- `design.md`: viết lại mục 1.3 (hết `DESIGN_CONFLICT`, không cần ngoại lệ xóa / ADR-007), 2.2, 3.2, 3.3, 4.x, 5, 6.3, 7, 8 theo AC-2..AC-11 → `/team:design FEAT-002` (amend). Nếu Q1 = b → cần `/team:research` trước: làm sao hiện chỉ báo riêng trên trang phiếu Helpdesk 15.1.0 mà không sửa mã nguồn Helpdesk. **[changed — chốt Q1 = b: `/team:research` bắt buộc, rồi `/team:architect`, rồi `/team:design`; xem mục Chốt sau câu trả lời Q1]**
- ADR: không đổi ADR-004. Không cần ADR-007 dạng "ngoại lệ xóa". Nếu cách hiện ở Q1 = b thêm một lớp giao diện mới vào app thì architect xét có cần ADR không.
- `tasks.md`: chưa có, không ảnh hưởng.
- `.team/profile.json`: Q1 = b thì thêm `javascript` vào `language` (`notes.language` đã dự trù) — việc của team-leader. **[changed — chốt Q1 = b: áp dụng]** **[changed — Amendment 2: việc của người, team-leader không được sửa `.team/profile.json`]**

### Đề xuất về cỡ
- Q1 = a: giữ M (11 AC, AC-11 không áp dụng).
- Q1 = b: vẫn M nếu researcher xác nhận có cách hiện không sửa Helpdesk và phần giao diện chỉ là một đoạn nhỏ. Nếu cần nhiều hơn → team-leader xét đổi sang L, hoặc tách phần giao diện thành feature riêng (phương án c của Q1). **[changed — chốt Q1 = b: đề xuất L, lý do ở mục Chốt sau câu trả lời Q1]**

### Definition of Done (thay đổi)
**Phần build:**
- [ ] AC-1..AC-9 đạt bằng test tự động, đầu ra dán trong `acceptance.md`; AC-11 nếu Q1 = b và có test được **[changed — chốt Q1 = b: xem DoD ở mục Chốt sau câu trả lời Q1]**
- [ ] Không còn mã hay test nào về comment tạm (AC-4/AC-6 cũ)
- [ ] Các mục DoD build cũ khác giữ nguyên (`cmd.test` xanh, `cmd.lint` sạch, `cmd.migrate`, commit local không push)

**Phần sau G4 / sau bàn giao:**
- [ ] As-Built, README/tài liệu người dùng (thêm: chỉ báo trông thế nào, cách tắt), CHANGELOG, CI xanh — như cũ
- [ ] Bước tay AC-10 (và AC-11 nếu Q1 = b) trên `miyano`, kết quả ghi vào `acceptance.md` (thay bước tay cũ)

### Chốt sau câu trả lời Q1 (2026-11-12)

**Câu trả lời của người:** Q1 = **b** (team-leader hỏi qua AskUserQuestion 2026-11-12; ghi ở `questions.md` mục "Câu trả lời của người"). Ý người: chỉ báo riêng bằng tiếng Việt; mã giao diện nằm trong app `erp_ai`; không sửa mã nguồn Helpdesk. Vòng hỏi đóng ở 1/2; không còn câu hỏi mở.

**Giả thuyết cuối (độ tin cậy 85%):** trong suốt một lần chạy có gọi model, agent Helpdesk đang mở trang phiếu đó thấy, không cần tải lại trang, một chỉ báo tiếng Việt kèm tên tài khoản agent: câu chữ cấu hình ("Đang suy nghĩ…") hoặc "Đang làm: <việc>…". Chỉ báo do mã giao diện của app `erp_ai` hiện ra, không sửa Helpdesk, không ghi bản ghi nào. Nó mất khi lần chạy kết thúc ở mọi nhánh, và tự mất sau tối đa 600 s nếu worker chết. Câu trả lời của `@ai` vẫn trễ 3–5 s, chỉnh được. Còn 15% vì chưa biết làm được cách này trên Helpdesk 15.1.0 mà không sửa mã nguồn Helpdesk hay không (researcher kiểm; nếu không được thì theo A-18). **[changed — Amendment 2: research xác nhận làm được; lý do của 15% còn lại đổi, xem Amendment 2]**

**Nhánh đã chốt (thay mọi chỗ "nếu Q1 = …" ở trên):**
- AC-1: câu chữ cấu hình hiện đúng nguyên văn trên chỉ báo ở trạng thái "đang suy nghĩ"; rỗng = tắt chỉ báo. Nhánh "Q1 = a, câu chữ chỉ bật/tắt" bỏ.
- AC-9: có hiệu lực đầy đủ; nhãn việc hiện trên chỉ báo. Nhánh "Q1 = a, phần chữ không hiện" bỏ.
- AC-10: có hiệu lực, chữ hiện là câu chữ cấu hình và "Đang làm: <nhãn>…". Để ghi kết quả từng ý, đánh số các ý cũ của AC-10 theo thứ tự: (a) thấy chỉ báo kèm tên tài khoản agent, không tải lại trang; (b) chỉ báo mất ≤ 10 s sau khi câu trả lời hiện ra; (c) lần chạy có lỗi không để chỉ báo kẹt quá 10 s; (d) trang phía khách không hiện chỉ báo. Thêm 3 ý (bước tay, cùng kịch bản):
  - (e) Đổi câu chữ trên form thành một chuỗi thử (ví dụ `Đang xử lý thử…`), gõ `@ai` → chỉ báo hiện đúng chuỗi đó. Trả lại giá trị cũ sau khi kiểm (Constraints: không để lại thay đổi cấu hình trên `miyano`).
  - (f) Câu chữ chứa thẻ HTML (ví dụ `<b>x</b>`) → chỉ báo hiện nguyên văn ký tự, không hiểu thành HTML (STD-SEC-3, Dữ liệu: "coi là văn bản thường").
  - (g) Trang phiếu và các trang Helpdesk khác vẫn mở và dùng bình thường khi app `erp_ai` đã cài, không có lỗi mới trong console trình duyệt khi không có lần chạy nào.
- AC-11: có hiệu lực. Bước tay là bắt buộc. Nếu researcher/designer tìm được cách test tự động cho phần hiện chỉ báo thì thêm test, không thay bước tay. **[changed — Amendment 2: test tự động phía trang chỉ khi người thêm slot lệnh, xem A-21]**
- A-9, A-16: áp dụng nhánh b.
- Thứ tự bỏ trước nếu phải cắt: giữ như cũ (AC-11, rồi phần "Đang làm" của AC-9).

**Ràng buộc mới từ câu trả lời:**
- Mã giao diện của chỉ báo nằm trong repo app `erp_ai`, theo `structure.allowed_new_file_roots` (`erp_ai`), và về site khi cài hoặc cập nhật app. Không có bước nào yêu cầu người dán mã tay vào site.
- Không sửa tệp nào trong app Helpdesk (`apps/helpdesk`), kể cả để thử.
- Cách đưa phần giao diện lên trang phiếu do researcher/architect chọn. Nếu cách đó phải tạo một bản ghi lúc cài app, architect xác nhận việc này không thuộc bảng chủ ghi ADR-004, vì ADR-004 nói về bản ghi agent ghi lúc chạy. Chỉ báo lúc chạy vẫn không ghi bản ghi nào (A-14).

**Assumptions decided by the team (thêm sau Q1):**
- **A-18 Nếu không làm được b mà không sửa Helpdesk.** **[changed — Amendment 2: KHÔNG ÁP DỤNG — research xác nhận làm được; phương án lùi "quay về a" cũng không chạy trên `miyano`; thay bằng A-18' ở Amendment 2]**
  - Chọn: researcher báo không làm được (kèm bằng chứng) → team-leader báo người trước khi vào design. Mặc định đội quay về phương án a cho FEAT-002, đúng như đã nói trong Q1, và đề xuất phần b thành feature riêng.
  - Vì: người đã đọc điều kiện này trong Q1 lúc chọn b; sửa Helpdesk nằm ngoài phạm vi.
  - Thay thế: dừng FEAT-002 chờ người quyết lại.
  - Sai thì: team-leader hỏi người; amend AC-1, AC-9, AC-10, AC-11 theo nhánh a (nội dung nhánh a vẫn còn ở trên).
- **A-19 Chỉ trang phiếu agent bản desktop.**
  - Chọn: AC-10 và AC-11 cam kết trang phiếu agent bản desktop. Trang phiếu agent bản mobile của Helpdesk không bắt buộc.
  - Vì: người không nhắc tới mobile; Helpdesk có giao diện mobile riêng, làm thêm thì tăng phạm vi phần giao diện.
  - Thay thế: hiện chỉ báo trên cả trang mobile.
  - Sai thì: thêm một ý mobile vào AC-10 và AC-11, bước tay kiểm thêm trên mobile.
- **A-20 Chỉ báo hiện ở đâu trên trang.**
  - Chọn: spec chỉ cam kết chỉ báo nhìn thấy được khi đang xem trang phiếu, kèm tên tài khoản agent và chữ trạng thái. Vị trí, kiểu dáng, hiệu ứng do designer chọn.
  - Vì: người chỉ nói "như Claude" và "để người dùng biết ai đang hoạt động"; không có yêu cầu về vị trí.
  - Thay thế: spec cố định vị trí (ví dụ dưới khung soạn như chỉ báo "đang gõ").
  - Sai thì: thêm vị trí vào AC-10, designer sửa phần giao diện.

**Đề xuất cỡ: L** (analyst không tự đổi cỡ; team-leader ghi vào `intake.md` mục "Đổi cỡ").
- Lý do, theo thang cỡ của kit (`workflows/README.md`: L = nhiều module, NFR mới, > 5 ngày công):
  1. Nhiều module và thêm một lớp mới. Phải sửa cấu hình agent (`erp_ai_setting`), runner (phát tín hiệu ở mọi nhánh, mọi tool), và thêm một lớp giao diện mới chạy trên trang Helpdesk. Đây là mã giao diện đầu tiên của dự án: `profile.json` `language` hiện chỉ có `python`.
  2. NFR mới: NFR-5 (mất trong 10 s), NFR-6, cùng hạn tự mất 600 s phía trang (AC-11).
  3. Chưa biết làm được hay không, nên cần `/team:research`, có thể cần ADR cho lớp giao diện (`/team:architect`). Đó là đường của cỡ L.
  4. 11 AC so với 8 lúc chốt M; có thêm hai bước tay giao diện (AC-10, AC-11).
- Không có số ngày công đo được; tiêu chí "> 5 ngày công" không dùng làm lý do.
- Thay thế: giữ M bằng cách tách phần giao diện thành feature riêng (phương án c). Người đã không chọn c, nên đội không đề xuất tách.

**Ảnh hưởng tới các artifact sau (thay mục Ảnh hưởng ở trên khi khác):**
- `/team:research FEAT-002` (bắt buộc, trước design). Câu hỏi:
  - (1) Làm sao để mã giao diện do app `erp_ai` cung cấp chạy trên trang phiếu agent của Helpdesk 15.1.0 mà không sửa mã nguồn Helpdesk?
  - (2) Worker phía server phát tín hiệu tới trang đang mở bằng cách nào?
  - (3) Phía trang tự tắt sau 600 s, và không hiện lại khi tải lại trang, bằng cách nào?
  - (4) Có cách test tự động phần này không?
  - Kết quả không làm được → A-18. **[changed — Amendment 2: research đã xong, kết quả làm được; A-18 không áp dụng]**
- `/team:architect FEAT-002`: xét ADR cho lớp giao diện mới trong app (cỡ L; G2 đang tắt).
- `design.md` hiện có viết trước Amendment 1 (còn `DESIGN_CONFLICT`), nên đã cũ. `team.py` vẫn báo stage `designed` vì file còn đó. Phải viết lại bằng `/team:design FEAT-002` sau research/architect.
- `.team/profile.json`: thêm `javascript` vào `language` — việc của team-leader. `formatters_by_ext` đã có `.js`. **[changed — Amendment 2: việc của người, team-leader không được sửa `.team/profile.json`]**
- `tasks.md`: chưa có.

**Definition of Done (thay DoD của Amendment 1 khi khác):**

Phần build:
- [ ] AC-1..AC-9 đạt bằng test tự động, đầu ra dán trong `acceptance.md`. **[changed — Amendment 2: thêm AC-12]**
- [ ] Không còn mã hay test nào về comment tạm (AC-4/AC-6 cũ).
- [ ] Mã giao diện nằm trong `erp_ai/`, `cmd.format`/`cmd.lint` sạch cho cả tệp `.js`. Nếu phần giao diện cần build tài sản thì `cmd.build` chạy được, dán đầu ra.
- [ ] App Helpdesk không bị sửa: `git -C ../helpdesk status --porcelain` không có dòng nào do FEAT-002 tạo ra, dán đầu ra.
- [ ] `cmd.test` xanh, `cmd.migrate` chạy được trên `miyano`, commit local trên `team/FEAT-002`, không push.

Phần sau G4 / sau bàn giao:
- [ ] Bước tay AC-10 (a)–(g) và AC-11 trên `miyano`, desktop, kết quả từng ý ghi vào `acceptance.md` (người làm). **[changed — Amendment 2: AC-10 (a)–(i)]**
- [ ] As-Built (`/team:asbuilt`). Tài liệu người dùng mô tả chỉ báo trông thế nào, các nhãn việc, cách tắt (câu chữ rỗng), khoảng trễ. Mục CHANGELOG. CI xanh.

## Amendment 2 (2026-11-12)

### Nguồn và lý do
- `research.md` (researcher, 2026-11-12), đoạn "Phát hiện trái với spec": Frappe 15.126.1 trên bench này chỉ nạp handler realtime của chính Frappe (`apps/frappe/realtime/index.js:28-31`); bộ nạp handler realtime của app khác chỉ có ở Frappe v16/develop. Hệ quả trên `miyano`: phòng `open_doc:HD Ticket/<tên>` không có trang nào vào, nên chỉ báo "is typing" có sẵn của Helpdesk và sự kiện `helpdesk:ticket-update` không bao giờ tới trình duyệt.
- Team-leader yêu cầu sửa spec cho khớp research (`/team:analyze FEAT-002 --amend --decide`). Mode decide: không mở vòng hỏi mới.
- Không đổi quyết định của người: Q1 = b (chỉ báo riêng tiếng Việt, mã giao diện trong app `erp_ai`, không sửa Helpdesk); không sửa ADR-004; giữ khoảng trễ 3–5 s chỉnh được.

### Sửa các dòng "Đã có câu trả lời sẵn" của Amendment 1
| Dòng cũ (Amendment 1) | Đúng hay sai trên `miyano` | Thay bằng |
|---|---|---|
| "Helpdesk đã có sẵn chỉ báo đang gõ" | Sai. Thành phần giao diện có trong mã Helpdesk, nhưng tín hiệu không tới trình duyệt vì `helpdesk/realtime/handlers.js` không được nạp (`research.md` dòng 23) | Không có chỉ báo sẵn nào của Helpdesk dùng được. Chỉ báo của FEAT-002 không được dựa vào nó (R-1) |
| "Trang phiếu tự tải lại khi phiếu được lưu" (`helpdesk:ticket-update`) | Sai. Sự kiện phát vào phòng `open_doc:` (`helpdesk/utils.py:94-95`), không trang nào nhận | Comment mới, kể cả câu trả lời của agent, vẫn hiện ngay trên trang đang mở qua đường cập nhật comment của chính Frappe (`research.md` Q2; `TicketTimeline.vue:509-510`). AC-10 (b) đo từ lúc câu trả lời hiện ra, nên không đổi |
| "HD Form Script … không có kênh realtime … researcher kiểm" | Phần mô tả ngữ cảnh đúng; câu hỏi đã có trả lời | Research: làm được phương án b trên Helpdesk 15.1.0 mà không sửa Helpdesk (`research.md` "Câu trả lời ngắn") |
| NFR-5: 10 s "theo mức Helpdesk tự dùng" (`realtime.ts:106-119`) | Nguồn số vẫn dùng được: đây là hằng số trong mã Helpdesk 15.1.0, không phụ thuộc việc handler có được nạp hay không | NFR-5 giữ 10 s, nguồn không đổi |
| `questions.md` Q1 phương án a ("dùng chỉ báo is typing có sẵn") | Phương án a vốn không chạy được trên `miyano` | Không ảnh hưởng, vì người đã chọn b. Ghi lại để không ai dùng a làm phương án lùi (A-18') |

### Giả thuyết (độ tin cậy 85%)
Nội dung giả thuyết cuối ở mục "Chốt sau câu trả lời Q1" giữ nguyên. Lý do của 15% còn lại đổi: research đã xác nhận làm được b trên Helpdesk 15.1.0 mà không sửa Helpdesk. Còn chưa chắc vì (1) chưa chạy thử trên trình duyệt (`ui: false`, không có Playwright); (2) cách research đề xuất để trang nhận tín hiệu dựa vào một chi tiết nội bộ của SPA không có trong tài liệu (`research.md` dòng 21, `UNVERIFIED`). Cả hai chỉ kiểm được ở bước tay AC-10.

### Ràng buộc mới (yêu cầu nghiệp vụ, không phải lựa chọn công nghệ)
- **R-1** Chỉ báo không dựa vào chỉ báo, sự kiện hay phòng realtime nào chỉ có khi handler realtime của Helpdesk được nạp (`helpdesk/realtime/handlers.js`, phòng `open_doc:`), vì chúng không chạy trên Frappe 15 của `miyano`.
- **R-2** "Ở mọi nhánh" của AC-4 bao gồm cả nhánh mà dữ liệu của lần chạy bị hoàn tác (rollback): tín hiệu kết thúc vẫn phải tới trang. Research chỉ ra một cách phát làm mất tín hiệu khi rollback (`research.md` Q2). Đây là cách hiểu cụ thể của AC-4, không phải AC mới; designer thêm một test cho nhánh này.
- **R-3** Phần giao diện của chỉ báo không được làm mất cập nhật trực tiếp sẵn có của trang phiếu (comment mới hiện ngay). Research nêu rủi ro này (`research.md` Q2, "Không được `doc_unsubscribe`"). Kiểm ở AC-10 (h).

### Cách phát tín hiệu: đầu vào cho architect, không phải quyết định của spec
- Research khuyến nghị **D1 + C1** (`research.md` mục "Khuyến nghị"): app cài một bản ghi tùy biến chính thức của Helpdesk (HD Form Script) cho trang phiếu agent; worker phát một sự kiện riêng của app qua realtime vào phòng tài liệu của phiếu. Team-leader yêu cầu đội đi theo khuyến nghị này.
- Spec ghi nhận đó là hướng đội đi theo, nhưng không viết nó thành tiêu chí. Các AC giữ dạng hành vi (tín hiệu, chỉ báo nhìn thấy, cài đặt đúng một bản). Architect chốt cách làm trong ADR (`/team:architect FEAT-002`), designer chi tiết hóa. Nếu architect chọn cách khác (D2/D3, C2/C3 của research), không AC nào phải đổi, trừ khi cách đó ghi dữ liệu lúc chạy (C2 ghi cache): khi đó architect xét theo A-14.
- Hai điểm research nêu để architect xác nhận, spec đã có chỗ: bản ghi tạo lúc cài app không thuộc bảng chủ ghi lúc chạy của ADR-004 ("Ràng buộc mới từ câu trả lời"); bản ghi được đặt lại mỗi lần cập nhật app (A-22).

### Tiêu chí nghiệm thu đổi và thêm
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-10 [changed — Amendment 2] | Giữ (a)–(g) của "Chốt sau câu trả lời Q1". Thêm: (h) khi app `erp_ai` đã cài, dù đang có hay không có lần chạy, một comment mới do người khác thêm vào phiếu vẫn hiện trên trang đang mở mà không cần tải lại, như trước khi cài (R-3); (i) chuyển qua lại giữa hai phiếu trong cùng tab rồi quay lại: một lần chạy chỉ hiện một chỉ báo, và chỉ báo của lần chạy trên phiếu A không hiện khi đang xem phiếu B | Bước tay, cùng kịch bản AC-10. (h): hai phiên (hai tài khoản hoặc hai trình duyệt), phiên B thêm comment, phiên A thấy ngay. (i): gõ `@ai` trên phiếu A, chuyển sang phiếu B rồi về A trong lúc chạy. Ghi kết quả từng ý vào `acceptance.md` |
| AC-11 [changed — Amendment 2] | Tiêu chí giữ nguyên | Bước tay là bắt buộc (phương án kiểm thử J1 của research). Test tự động cho logic phía trang (J2: hẹn giờ tự mất, lọc đúng phiếu) chỉ làm khi người đã thêm slot lệnh test JavaScript vào `.team/profile.json` (A-21); khi đó test thêm vào, không thay bước tay. Hiện `.team/profile.json` `cmd` không có slot này, nên build theo J1 |
| AC-12 [mới] | Phần giao diện của chỉ báo về site chỉ bằng việc cài/cập nhật app, không cần bước dán mã tay: sau khi bước cài của app chạy hai lần liên tiếp, site có đúng một bản phần giao diện đó, nội dung khớp tệp trong repo `erp_ai`, và chỉ áp cho trang phiếu phía agent, không áp cho trang khách. Sau bước gỡ app, không còn bản nào (A-22) | Test tự động (`cmd.test_one`): gọi bước cài hai lần, kiểm đúng một bản, nội dung bằng tệp trong repo, chỉ áp trang agent; gọi bước gỡ, kiểm còn 0 bản. Kèm đầu ra `cmd.migrate` trên `miyano` dán trong `acceptance.md` |

Thứ tự bỏ trước nếu phải cắt: giữ như cũ (AC-11, rồi phần "Đang làm" của AC-9). AC-10 (h) và AC-12 không bỏ: (h) bảo vệ hành vi sẵn có của Helpdesk, AC-12 là ràng buộc của người ("về site khi cài hoặc cập nhật app").

### Assumptions decided by the team (thêm)
- **A-18' Không còn phương án lùi sẵn** (thay A-18).
  - Chọn: bỏ A-18. Research xác nhận làm được b, nên điều kiện của A-18 không xảy ra.
  - Vì: `research.md` "Câu trả lời ngắn". Hơn nữa, phương án lùi "quay về a" của A-18 không tồn tại: a dựa vào chỉ báo "is typing", mà chỉ báo này không chạy trên `miyano`.
  - Thay thế: giữ A-18 làm phương án lùi.
  - Sai thì (bước tay AC-10 cho thấy b không chạy trên trình duyệt): không có phương án lùi sẵn. Team-leader báo người; phần phía server (AC-1..AC-9, AC-12) vẫn giữ được; phần hiện trên trang chờ người quyết (sửa hay tách feature).
- **A-21 Kiểm thử phía trang theo J1.**
  - Chọn: phần hiện chỉ báo trên trang chỉ kiểm bằng bước tay AC-10/AC-11; phần phía server và AC-12 kiểm bằng test Python (`cmd.test_one`).
  - Vì: `.team/profile.json` `language` chỉ có `python` và `cmd` không có slot test JavaScript. Dev và QA chỉ chạy lệnh trong `cmd.*`. Team-leader không được sửa `.team/profile.json`.
  - Thay thế: J2 (test tự động cho logic phía trang).
  - Sai thì: **người** thêm `javascript` vào `language`, thêm slot `cmd.test_js` và quy ước tên tệp test JavaScript vào `.team/profile.json` → `/team:plan FEAT-002 --insert` thêm task test JS cho AC-11 và AC-10 (i); DoD thêm dòng "`cmd.test_js` xanh, dán đầu ra".
- **A-22 Phần giao diện do app sở hữu.**
  - Chọn: mỗi lần cài hoặc cập nhật app, phần giao diện trên site được đặt lại đúng như trong repo; quản trị viên sửa tay trên site sẽ bị ghi đè. Gỡ app thì gỡ theo.
  - Vì: ràng buộc của người là mã giao diện nằm trong repo và về site khi cài/cập nhật app; repo là nguồn duy nhất. Research nêu điểm này (`research.md` bảng phương án, D1).
  - Thay thế: chỉ tạo khi chưa có, không ghi đè bản trên site.
  - Sai thì: AC-12 đổi "nội dung khớp tệp trong repo" thành "chỉ tạo khi chưa có"; tài liệu người dùng bỏ dòng cảnh báo ghi đè.

### Việc của người (team-leader không làm được)
- `.team/profile.json`: thêm `javascript` vào `language` (`notes.language` đã dự trù "Thêm javascript khi có HD Form Script"). Không chặn build: `formatters_by_ext` đã có `.js`, nên `cmd.format`/`cmd.lint` vẫn chạy cho tệp `.js`.
- Nếu muốn J2: thêm slot `cmd.test_js` (research gợi ý test runner có sẵn của Node 20 trên bench) và quy ước tên tệp test JavaScript (`naming.test_file` hiện chỉ có `test_{name}.py`). Không thêm → build theo J1 (A-21).
- Hai dòng "việc của team-leader" ở Amendment 1 và "Chốt sau câu trả lời Q1" đã được đánh dấu `[changed — Amendment 2]`.

### Ảnh hưởng tới các artifact sau
- `research.md`: không đổi.
- `/team:architect FEAT-002`: ADR cho lớp giao diện mới. Đầu vào: khuyến nghị D1 + C1, R-1..R-3, A-22, "Ràng buộc mới từ câu trả lời".
- `design.md`: vẫn là bản trước Amendment 1 (`DESIGN_CONFLICT`). `team.py status` báo `designed / READY → /team:plan` chỉ vì tệp còn đó; trạng thái này sai. Không chạy `/team:plan` trước khi `/team:design FEAT-002` viết lại theo AC-1..AC-12.
- `questions.md`: không sửa (lịch sử); không có vòng hỏi mới.
- `tasks.md`: chưa có.
- `.team/profile.json`: xem "Việc của người".

### Đề xuất về cỡ
- Giữ L. 12 AC (thêm AC-12); không thêm module so với "Chốt sau câu trả lời Q1".

### Definition of Done (thay DoD của "Chốt sau câu trả lời Q1" khi khác)
Phần build:
- [ ] AC-1..AC-9 và AC-12 đạt bằng test tự động (`cmd.test_one`), đầu ra dán trong `acceptance.md`; có test cho nhánh rollback của AC-4 (R-2).
- [ ] Chỉ khi người đã thêm slot test JavaScript (A-21): test phía trang xanh, dán đầu ra.
- [ ] Các mục build khác giữ như "Chốt sau câu trả lời Q1" (không còn mã comment tạm; `.js` trong `erp_ai/`, `cmd.format`/`cmd.lint` sạch; Helpdesk không bị sửa; `cmd.test` xanh; `cmd.migrate` chạy được; commit local, không push).

Phần sau G4 / sau bàn giao:
- [ ] Bước tay AC-10 (a)–(i) và AC-11 trên `miyano`, desktop, kết quả từng ý ghi vào `acceptance.md` (người làm).
- [ ] As-Built (`/team:asbuilt`), có dòng "chạy lại bước tay AC-10 sau mỗi lần nâng cấp Helpdesk hoặc Frappe" (research, Hệ quả của nháp ADR).
- [ ] Tài liệu người dùng: như "Chốt sau câu trả lời Q1", thêm cảnh báo "sửa tay phần giao diện của chỉ báo trên site sẽ bị ghi đè khi cập nhật app" (A-22).
- [ ] Mục CHANGELOG. CI xanh.
