Feature: FEAT-004
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-004 — Cho bot quyền sửa code và chạy lệnh bench, có người duyệt từng thay đổi

Mode: decide (intake `:15`), nên không có `questions.md`. Mọi điểm lớn nằm ở mục Assumptions, đủ 4 trường. Cỡ L, playbook new-feature, cổng G5 (`team.py status FEAT-004`).

> **Amendment 1 (2026-11-12, `--amend --decide`, G1 tắt):** sửa được code app lõi và mỗi thay đổi đã áp dụng thành đúng một commit git local. Văn bản gốc được giữ nguyên. Dòng nào bị đổi có dấu **[changed: Amd-1 …]**, dòng mới có dấu **[added: Amd-1]**. Nội dung mới nằm ở mục "Amendment 1" phía dưới.

> **Amendment 2 (2026-11-14, `--amend --decide`, G1 tắt, change-request CHG-001):** ghi lại điều người đã ra lệnh và phiên khác đã viết code: bot làm luôn không hỏi lại; một lần bấm Duyệt / Từ chối ngay trên phản hồi của bot ở phiếu; công cụ bản ghi trực tiếp; ô "Toàn quyền (khẩn cấp)". Văn bản gốc và Amendment 1 giữ nguyên. Dòng bị đổi có dấu **[changed: Amd-2 …]**, dòng mới có dấu **[added: Amd-2]**. Nội dung mới nằm ở mục "Amendment 2" phía dưới, trước Definition of Done.

## Mục tiêu
**Giả thuyết (độ tin cậy 70%):** người yêu cầu muốn bot đề xuất được thay đổi code trong các app của bench và đề xuất được lệnh `bench`. Mỗi thay đổi chỉ được áp dụng sau khi một người có thẩm quyền xem đúng nội dung đó và bấm duyệt. Thay đổi đã áp dụng hoàn tác được, và mọi bước đều có trong nhật ký. Nội dung phiếu không bao giờ tự kích hoạt hay tự duyệt được thay đổi. **[changed: Amd-1 M-1]** **[changed: Amd-2 N-1 — "bấm duyệt" nay có thể là một lần mở liên kết Duyệt trong comment của bot; "xem đúng nội dung đó" là đọc tóm tắt ở comment, bản đầy đủ có diff nằm sau liên kết "Xem nội dung thay đổi" (AC-22); bot còn có công cụ bản ghi trực tiếp không qua duyệt (N-2)]**

Chưa tới 85% vì ba lẽ:
1. Câu gốc nêu cả "tạo 1 user" và "sửa cài đặt hệ thống" (intake `:10`), nhưng người đã chốt "Thêm quyền sửa code và chạy lệnh". Đội hiểu là tạo User và sửa cấu hình qua DocType nằm ngoài phạm vi (A-1). **[changed: Amd-2 A-1' — người sau đó ra lệnh cho bot tạo User và sửa cấu hình trực tiếp; phần này nay nằm trong phạm vi dưới dạng công cụ bản ghi, N-3]**
2. Chưa biết người muốn bot sửa những app nào (A-3). **[changed: Amd-1 M-1, đã có câu trả lời: app lõi]**
3. Chưa có số đo thời gian chạy `bench migrate`/`bench build` trên site `miyano`, nên giới hạn thời gian lệnh dựa vào con số 600 s có sẵn (A-8).

| Mục | Nội dung |
|---|---|
| Outcome | Một người có vai trò `ERP AI Instructor` nhờ bot sửa lỗi code trên phiếu. Bot đưa ra đề xuất có diff đầy đủ (hoặc một lệnh `bench` cụ thể), người đó duyệt, và hệ thống áp dụng đúng nội dung đã duyệt. Trước khi được duyệt thì không có byte nào trên đĩa đổi và không có lệnh nào chạy. |
| Users | Người ra lệnh/duyệt: người có vai trò `ERP AI Instructor` (Hiếu, Việt, Tiến theo bảng routing `erp_ai/agent/prompts.py:139-141`). System Manager bật/tắt khả năng này và chọn app được sửa. Người tạo phiếu là nguồn dữ liệu không tin cậy. |
| Why now | Người đã cấp full quyền cho tài khoản bot mà bot "chả làm được gì" (intake `:10`). Rào cản thật nằm ở bộ tool, prompt và policy, không nằm ở quyền của tài khoản: bot chỉ có 4 tool ghi phiếu (`erp_ai/agent/tools/write_ticket.py:116-164`), prompt cấm sửa `apps/` (`erp_ai/agent/prompts.py:98`), và lệnh ngoài duy nhất được phép là `git` chỉ đọc (ADR-005 Quyết định 5). |
| Success | Lúc build: AC-1..AC-15 đạt trên site dev `miyano`, `cmd.test` xanh. Sau G4 (việc của người): bật trên môi trường thật cho ≥ 1 app, cho bot xử lý 1 phiếu lỗi code từ đề xuất tới khi duyệt và áp dụng, rồi hoàn tác thử 1 lần. **[changed: Amd-1 M-3 — AC-1..AC-23; có thêm vòng thử trên 1 app lõi]** **[changed: Amd-2 N-1 — AC-1..AC-35; vòng thử sau G4 duyệt bằng một lần bấm trên trang phiếu, có thêm phép đo "bot hỏi lại 0 lần"]** |
| Constraints | Không push, không deploy prod (G5 cần người duyệt). Không đổi role của tài khoản `ai.agent@miyano.com.vn` (A-2). Không đọc, không ghi `protected_paths` hay file bí mật. Tắt công tắc thì bot quay về đúng hành vi hiện tại. Chỉ commit local trên `team/FEAT-004*`. **[changed: Amd-1 M-3 — câu "chỉ commit local trên `team/FEAT-004*`" là quy tắc cho commit của đội; bot được tạo commit local trong repo app (A-4 mới), vẫn không push]** **[changed: Amd-2 — "tắt công tắc" nay là tắt cả hai ô: "Cho phép sửa code và lệnh bench" và "Toàn quyền (khẩn cấp)" (AC-1); A-2 xem A-2']** |
| Out of scope | Tạo User và gán Role. Tool cấu hình `L2`/`L3` của guide (Client Script, Property Setter, Workflow, Report…, guide `:240-251`). Bot tự duyệt hoặc tự áp dụng. Push, commit, đổi nhánh git. `bench restart`. Xóa file. Sửa chính app `erp_ai`. Chạy trên production trong feature này. **[changed: Amd-1 M-3 — bỏ chữ "commit"; thêm tạo nhánh, sửa lịch sử git]** **[changed: Amd-2 N-3 — "Tạo User và gán Role" và "tool cấu hình" nay nằm TRONG phạm vi dưới dạng công cụ bản ghi trực tiếp; "Bot tự duyệt hoặc tự áp dụng" và "Xóa file" giữ nguyên]** |

## Người dùng
- **Người ra lệnh và người duyệt (vai trò `ERP AI Instructor`):** viết comment trên phiếu để nhờ bot. Họ đọc đề xuất (diff hoặc lệnh, lý do, cảnh báo hoàn tác được hay không) rồi duyệt hoặc từ chối. Với thay đổi code đã áp dụng, họ có thể bấm hoàn tác. Thẩm quyền xác định như hiện nay (`erp_ai/agent/authority.py:44-50`). `Administrator`, `Guest` và tài khoản agent không bao giờ có thẩm quyền (`authority.py:12`). **[changed: Amd-1 M-3 — họ thấy thêm nhánh nhận commit, cảnh báo app lõi và mã commit]** **[changed: Amd-2 N-5 — họ duyệt hoặc từ chối bằng một lần mở liên kết ngay trong comment của bot trên phiếu; hoàn tác vẫn làm trên form đề xuất]**
- **System Manager:** bật hoặc tắt khả năng sửa code và chạy lệnh, chọn danh sách app bot được sửa. Mặc định là tắt và danh sách rỗng. **[changed: Amd-1 A-3 — được thêm cả app lõi `frappe`, `erpnext`, `helpdesk`, `hrms`]** **[changed: Amd-2 A-24 — ô "Cho phép sửa code và lệnh bench" nay cũng mở công cụ bản ghi trực tiếp; thêm ô "Toàn quyền (khẩn cấp)", mặc định tắt, tắt bằng tay]**
- **Người tạo phiếu, người comment không có thẩm quyền:** nội dung họ viết là dữ liệu (STD-SEC-5). Họ không làm bot có tool mới và không duyệt được gì.
- **Người tra cứu nhật ký (System Manager):** tra lại ai đề xuất gì, ai duyệt, đã áp dụng hay hoàn tác lúc nào, và lệnh trả về gì.
- **Người giữ repo app (lập trình viên của công ty) [added: Amd-1]:** đọc commit bot tạo, tự đẩy lên fork, mở PR, deploy, và tự xử lý khi `bench update`.

## Phạm vi
- **Trong:**
  1. **Đề xuất thay đổi code:** sửa nội dung một file đã có, hoặc tạo file mới, trong một app thuộc danh sách được phép. Mỗi đề xuất là một file (A-5). Đề xuất lưu đủ nội dung trước/sau và diff, chưa ghi gì xuống đĩa. **[changed: Amd-1 M-3 — app lõi được phép; đề xuất lưu thêm nhánh nhận commit và cảnh báo]**
  2. **Đề xuất lệnh `bench`:** chỉ lệnh trong danh sách cho phép (A-6), chỉ cho site đang chạy agent. Lưu lệnh dưới dạng chính xác từng đối số. Chưa chạy.
  3. **Duyệt hoặc từ chối:** người có thẩm quyền làm việc này qua một thao tác chủ ý, kiểm ở server. Mỗi lần duyệt gắn với đúng một đề xuất. **[changed: Amd-2 N-3 — thao tác chủ ý gồm hai đường: nút trên form (có hộp xác nhận) và liên kết ký trong comment của bot (một lần mở, không hộp xác nhận)]**
  4. **Áp dụng sau khi duyệt:** áp dụng đúng nội dung đã duyệt, không gọi lại model. Một đề xuất áp dụng nhiều nhất một lần. Đề xuất hết hiệu lực nếu file đích đã đổi kể từ lúc đề xuất. **[changed: Amd-1 M-3 mục 11 — áp dụng gồm ghi file và tạo đúng 1 commit local]**
  5. **Hoàn tác** một thay đổi code đã áp dụng bằng một thao tác. Lệnh `bench` không hoàn tác được, và điều này được ghi rõ trên đề xuất. **[changed: Amd-1 M-3 mục 12 — hoàn tác tạo một commit mới]**
  6. **Chặn đường dẫn và chặn lệnh:** từ chối từ lúc đề xuất và kiểm lại lúc áp dụng.
  7. **Nhật ký:** mỗi bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) có một dòng nhật ký.
  8. **Công tắc và danh sách app** trên cấu hình agent. Bộ tool mới chỉ được cấp khi công tắc bật, mức hiệu lực là `L3` và có người ra lệnh. **[changed: Amd-2 AC-2 — thêm đường cấp thứ hai: ô "Toàn quyền (khẩn cấp)" bật, mức từ `L1` trở lên, có người ra lệnh]**
  9. **Prompt:** khi bộ tool mới không được cấp, lệnh cấm "Không sửa file trong apps/" giữ nguyên. Khi được cấp, prompt nói rõ mọi thay đổi phải chờ duyệt. **[changed: Amd-2 AC-14, AC-29 — đối với thay đổi code và lệnh, "chờ duyệt" là chờ người bấm Duyệt trên comment; bot không hỏi lại và không chờ chữ "ok"]**
  10. **ADR mới:** ghi lại các phần của ADR-005 bị thay và cách hoàn tác (xem Giao diện / tích hợp).
  11.–14. **[added: Amd-1]** xem Amendment 1, M-3.
  15.–19. **[added: Amd-2]** xem Amendment 2, N-3.
- **Ngoài (non-goals):**
  - Tạo User, gán Role, sửa phân quyền (Role Permission, Custom DocPerm, Has Role…), sửa cấu hình qua DocType. Phần này thuộc nhóm tool `L2`/`L3` của guide `:240-251` và cần một intake riêng (A-1). **[changed: Amd-2 A-1' — tạo User, gán vai trò nghiệp vụ và sửa cấu hình nay làm được trực tiếp qua công cụ bản ghi; sửa Role Permission và Custom DocPerm vẫn đóng ở chế độ thường]**
  - Bot tự duyệt; duyệt bằng comment văn bản tự do; duyệt hàng loạt nhiều đề xuất một lần. **[changed: Amd-2 N-3 — liên kết có chữ ký do công cụ tự đăng trong comment không phải "văn bản tự do"; chữ "ok" hay "duyệt" do người viết vẫn không bao giờ là duyệt]**
  - Commit, push, tạo hay đổi nhánh git trong repo của app (A-4). **[changed: Amd-1 M-3 — commit local nay nằm trong phạm vi; push, tạo/đổi nhánh, sửa lịch sử vẫn ngoài phạm vi]**
  - `bench restart`, `bench update`, cài/gỡ app, backup/restore, `execute`/`console`, đổi config site. Đầy đủ ở A-6.
  - Xóa hoặc đổi tên file; sửa file ngoài `apps/`; sửa app `erp_ai` hay bất kỳ bản sao, worktree nào của nó (A-3).
  - Hoàn tác lệnh `bench` đã chạy.
  - Giao diện duyệt riêng trên SPA Helpdesk (profile `ui: false`; vị trí nút duyệt do designer chọn). **[changed: Amd-2 N-5 — người đã chọn vị trí: nút Duyệt / Từ chối là liên kết trong comment của bot trên trang phiếu; không có giao diện SPA riêng]**
  - Bật trên production. Việc này của người, sau G4/G5.

## Dữ liệu
- **Đề xuất (thực thể mới; designer đặt tên và chọn cách lưu):** **[changed: Amd-1 M-4 — thêm thông tin nhánh, cảnh báo, mã commit]**
  - phiếu, lần chạy và người ra lệnh;
  - loại (thay đổi code / lệnh);
  - app và đường dẫn tương đối, hoặc lệnh dạng danh sách đối số;
  - dấu nội dung file lúc đề xuất (để phát hiện file đã đổi);
  - nội dung trước, nội dung sau, diff;
  - lý do bot đưa ra, cờ "hoàn tác được";
  - trạng thái: chờ duyệt / đã từ chối / đã áp dụng / lỗi / hết hiệu lực / đã hoàn tác;
  - người duyệt hoặc từ chối và thời điểm;
  - kết quả lệnh: mã thoát, đầu ra đã cắt, thời gian chạy.
- **Khối lượng:** mỗi file một đề xuất. Không có số đo về số đề xuất mỗi ngày. Giới hạn lần chạy hiện có (NFR-3 của FEAT-001: 5 lần chạy/phiếu/ngày, 8 lượt) gián tiếp chặn số đề xuất.
- **Cấu hình mới:** công tắc bật/tắt (mặc định tắt) và danh sách app được sửa (mặc định rỗng). Chỉ System Manager sửa. Bot không đọc được cấu hình, vì `ERP AI Setting` nằm trong `DENIED_DOCTYPES` (`erp_ai/agent/tools/read.py:9-12`). **[changed: Amd-2 N-4 — thêm một ô "Toàn quyền (khẩn cấp)", mặc định tắt; bot vẫn không đọc, không sửa được cấu hình này ở mọi chế độ (AC-33)]**
- **Dữ liệu nhạy cảm:**
  - Nội dung file nguồn được lưu trong DB.
  - File có tên khớp mẫu bí mật, file thuộc `protected_paths`, `site_config.json`, `common_site_config.json` và mọi thứ dưới `sites/` đều bị từ chối, nên không vào đề xuất (guide `:330-336`).
  - Đầu ra lệnh có thể chứa đường dẫn. Đầu ra không được chứa giá trị khóa API (NFR-5 của FEAT-001).
  - **[added: Amd-1 M-4]** URL remote của repo app có thể chứa token, nên không lưu và không hiển thị. Metadata commit không chứa email người dùng thật.
  - **[added: Amd-2 N-4]** Liên kết Duyệt / Từ chối nằm trong comment trên phiếu mang chữ ký gắn với đúng một đề xuất và một hành động; ai đọc được comment đều thấy liên kết, nhưng chỉ phiên của người có vai trò mới làm đổi trạng thái (AC-26). Công cụ bản ghi có thể đọc và ghi dữ liệu nghiệp vụ và dữ liệu người dùng; mật khẩu và khóa API của người dùng đóng ở mọi chế độ (AC-31, AC-33).
- **Nhật ký:** dùng ERP AI Log hiện có, theo nguyên tắc "chỉ runner tạo nhật ký" (ADR-004). Bước duyệt, áp dụng, hoàn tác do người thao tác và chạy ngoài runner, nên designer phải nêu ai ghi nhật ký cho các bước này mà không trái ADR-004, hoặc architect sửa ADR-004. **[changed: Amd-2 AC-34, AC-35 — mỗi lời gọi công cụ bản ghi có một mục trong cột hành động của nhật ký lần chạy; giá trị trước/sau chưa có (AC-35)]**

## Giao diện / tích hợp
- **Model ↔ registry tool:** thêm nhóm tool mới, cấp theo mức × thẩm quyền × công tắc (ADR-005 Quyết định 1). Tên tool và schema do designer chọn. **[changed: Amd-2 N-5 — thêm nhóm công cụ bản ghi và nhóm Toàn quyền, cấp theo AC-2]**
- **Hệ thống tệp:** chỉ trong `apps/<app được phép>/`. Bộ chặn phải khử symlink và kiểm lại lúc áp dụng.
- **Tiến trình con `bench`:** chạy trong thư mục bench, không qua shell, có timeout, đối số đúng như đã duyệt.
- **Repo git của app [added: Amd-1 M-3]:** bước áp dụng và hoàn tác tạo commit local trong repo của app đích. Không có thao tác nào với remote. Chi tiết ở M-8 (điểm mở cho architect).
- **Người ↔ hệ thống:**
  - Màn hình duyệt là Desk form hoặc khu vực trên trang phiếu. Nếu chọn khu vực trên trang phiếu thì phải phối hợp với FEAT-003 Amendment 1, đang build trên cùng khu vực. **[changed: Amd-2 N-5 — đã chọn: comment của bot trên trang phiếu có liên kết Duyệt, Từ chối và "Xem nội dung thay đổi"; form Desk giữ nguyên]**
  - Bot comment trên phiếu kèm liên kết tới đề xuất.
- **Các quyết định kiến trúc bị chạm (architect xử lý, cần ADR mới):** **[changed: Amd-1 M-8 — thêm ADR-013 QĐ 6 và lệnh git ghi]**
  - ADR-005 Quyết định 5 ("lệnh ngoài duy nhất là `git` log/show/diff/blame") và ràng buộc "`subprocess` chỉ xuất hiện trong module tool mã nguồn": phải nới ra cho lệnh `bench` đã duyệt.
  - ADR-005 ràng buộc "trong `erp_ai/agent/tools/**` không có … ghi": tool đề xuất không ghi file. Bước áp dụng nằm ở đâu do architect quyết.
  - ADR-003: job agent bị giới hạn 600 s và an toàn 60 s (`erp_ai/constants.py:25-27`), trong khi lệnh như `bench build` có thể chạy lâu hơn. Architect quyết định lệnh chạy trong job agent hay ở đường chạy riêng sau khi duyệt.
  - ADR-004 (ai ghi nhật ký): xem mục Dữ liệu.
  - **Hoàn tác toàn bộ feature:** tắt công tắc thì bộ tool và prompt trở lại đúng như FEAT-001 (AC-1). **[changed: Amd-2 AC-1 — tắt cả hai ô]**
  - **[added: Amd-2 N-2]** Năm chỗ trái thiết kế đã ghim do lệnh của người (ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7, FEAT-006 AC-9) cần phán quyết của architect: giữ, sửa hay hỏi người. Phán quyết nằm ở tài liệu của architect, không ở spec này.
- **Không đổi:** ADR-006 (tài khoản agent không có System Manager) giữ nguyên (A-2). **[changed: Amd-2 A-2' — ADR-006 vẫn đúng với vai trò của chính tài khoản agent; ở chế độ Toàn quyền bot gán được System Manager cho người khác]**

## NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Không có thay đổi nào khi chưa duyệt: 0 byte trên đĩa đổi và 0 lệnh chạy cho tới khi đề xuất ở trạng thái đã duyệt **[changed: Amd-1 M-5 — thêm 0 commit]** **[changed: Amd-2 N-6 — chỉ áp cho đề xuất code và lệnh; công cụ bản ghi đổi dữ liệu ngay, không qua duyệt, do lệnh của người]** | Test AC-3, AC-8: so dấu nội dung file trước/sau; stub tiến trình con đếm 0 lời gọi |
| NFR-2 | Áp dụng đúng nội dung đã duyệt: file sau áp dụng trùng từng byte với nội dung đã duyệt; lệnh chạy đúng danh sách đối số đã duyệt; mỗi đề xuất áp dụng ≤ 1 lần **[changed: Amd-1 M-5 — nội dung file trong commit cũng trùng từng byte]** | Test AC-6, AC-8 |
| NFR-3 | Thời gian một lệnh không vượt giới hạn của đường chạy mà architect chọn. Nếu lệnh chạy trong job agent: lệnh phải kết thúc trước mốc 600 s − 60 s (`erp_ai/constants.py:25-27`), quá thì bị dừng và ghi lỗi **[changed: Amd-1 M-5 — bước git nằm trong cùng ngân sách]** | Test AC-10 bằng stub; architect đo `bench migrate` và `bench build --app <app>` trên `miyano` rồi ghi số vào design |
| NFR-4 | Đầu ra lệnh đưa cho model và lưu nhật ký ≤ 400 dòng, theo trần đọc sẵn có (NFR-6 FEAT-001, ADR-005) | Test AC-8: lệnh stub in 1.000 dòng thì kết quả còn ≤ 400 dòng |
| NFR-5 | 0 byte giá trị khóa API hoặc bí mật trong đề xuất, đầu ra lệnh, nhật ký | Test AC-13 gieo khóa giả (cùng cách NFR-5 của FEAT-001) |
| NFR-6 | 100% các bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) có một dòng nhật ký với phiếu, đề xuất, người thực hiện, thời điểm, kết quả **[changed: Amd-1 M-5 — dòng áp dụng/hoàn tác có mã commit]** | Test AC-12 đếm dòng nhật ký theo từng bước |
| NFR-7..NFR-9 | **[added: Amd-1]** xem M-5 | — |
| NFR-10..NFR-11 | **[added: Amd-2]** xem N-6 | — |

## Tiêu chí nghiệm thu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Công tắc tắt (mặc định): với 4 mức × có/không người ra lệnh, danh sách tên tool trùng hoàn toàn với danh sách hiện nay. Prompt vẫn chứa câu "Không sửa file trong apps/" **[changed: Amd-2 N-7 — "công tắc tắt" là cả hai ô tắt]** | Test tự động theo ma trận 8 tổ hợp, so với danh sách tên tool chụp từ nhánh nền; test grep chuỗi trong prompt |
| AC-2 | Bộ tool mới chỉ có khi đủ cả ba điều kiện: công tắc bật, mức hiệu lực `L3`, có người ra lệnh. Thiếu một điều kiện thì không có, kể cả khi vượt ngân sách và mức bị hạ về `L1` (ADR-003 bước e) **[changed: Amd-2 N-7 — có hai đường cấp, xem N-7]** | Test ma trận: công tắc × 4 mức × thẩm quyền × vượt/không vượt ngân sách |
| AC-3 | Gọi tool đề xuất thay đổi code hợp lệ thì: tạo 1 đề xuất "chờ duyệt", dấu nội dung file trên đĩa không đổi, và bot comment trên phiếu có liên kết tới đề xuất | Test tự động trên một app tạm trong danh sách được phép: so hash file trước/sau, đếm đề xuất và comment |
| AC-4 | Từ chối (`ok=false` kèm lý do, 0 đề xuất được tạo) với từng trường hợp: app `erp_ai`; đường dẫn khử symlink rơi vào repo `erp_ai` (kể cả worktree như `apps/erp_ai-wt`); app không có trong danh sách; đường dẫn thoát khỏi `apps/` bằng `..` hoặc symlink; tên khớp mẫu bí mật hoặc `protected_paths`; đuôi file ngoài danh sách đọc sẵn có; thao tác xóa hoặc đổi tên | Test tự động, mỗi nhánh từ chối một test |
| AC-5 | Chỉ người có vai trò `ERP AI Instructor` mới duyệt hoặc từ chối được. Tài khoản agent, `Administrator`, `Guest` và người không có vai trò đều bị từ chối ở server. Một comment chứa "ok"/"duyệt" của bất kỳ ai không làm đổi trạng thái đề xuất. Đề xuất bị từ chối thì không bao giờ được áp dụng **[changed: Amd-2 N-7 — điều này đúng cho cả hai đường duyệt: nút trên form và liên kết trong comment (AC-26)]** | Test tự động: gọi thao tác duyệt dưới từng user; tạo comment "ok" rồi kiểm trạng thái vẫn là "chờ duyệt" |
| AC-6 | Sau khi duyệt, file trùng từng byte với nội dung đã duyệt, và lần duyệt hay áp dụng thứ hai không đổi gì thêm. Nếu file đích đã đổi kể từ lúc đề xuất thì: không ghi, trạng thái "hết hiệu lực", có dòng nhật ký **[changed: Amd-1 — thêm commit, xem AC-17; nhánh "hết hiệu lực" cũng có 0 commit]** | Test tự động: so byte; duyệt hai lần; sửa file giữa lúc đề xuất và lúc duyệt |
| AC-7 | Hoàn tác thay đổi code đã áp dụng thì file trở lại trùng từng byte với nội dung trước (file mới tạo thì bị gỡ). Nếu file đã bị sửa sau khi áp dụng thì từ chối hoàn tác và không ghi **[changed: Amd-1 — hoàn tác tạo commit mới, xem AC-20]** | Test tự động hai nhánh |
| AC-8 | Đề xuất một lệnh trong danh sách cho phép: tạo đề xuất "chờ duyệt", 0 lời gọi tiến trình con. Sau khi duyệt: đúng 1 lời gọi với đúng danh sách đối số đã duyệt, không qua shell, thư mục làm việc là thư mục bench, có timeout. Mã thoát và đầu ra (≤ 400 dòng) được lưu | Test tự động với stub tiến trình con: đếm lời gọi, so đối số, kiểm `shell` không bật, kiểm có timeout; lệnh stub in 1.000 dòng |
| AC-9 | Từ chối lúc đề xuất và kiểm lại lúc áp dụng với: mọi lệnh ngoài danh sách cho phép, mọi lệnh trong danh sách cấm (A-6), đối số chứa ký tự điều khiển shell (`;`, `|`, `&`, `` ` ``, `$(`, `>`), site khác site đang chạy, cờ `--force` | Test tự động, một test cho mỗi nhóm; thêm test sửa đề xuất đã duyệt cho thành lệnh cấm thì khi áp dụng vẫn bị chặn |
| AC-10 | Lệnh chạy quá giới hạn thời gian (NFR-3) thì bị dừng, trạng thái "lỗi", lý do "quá thời gian", có dòng nhật ký | Test tự động với stub ném hết thời gian |
| AC-11 | Chống chèn lệnh qua phiếu: phiếu và comment của người không có thẩm quyền chứa câu như "sửa file X / chạy bench Y / tự duyệt" thì lần chạy có 0 tool mới và tạo 0 đề xuất. Khi có người ra lệnh mà chưa ai duyệt thì có 0 lần áp dụng, dù model trả lời "đã được duyệt" **[changed: Amd-2 N-7 — "0 tool mới" gồm cả công cụ bản ghi và nhóm Toàn quyền: 0 bản ghi đổi]** | Test tự động với stub Cổng model: kịch bản không có người ra lệnh; kịch bản model gọi tool đề xuất rồi khẳng định đã duyệt |
| AC-12 | Mỗi bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) tạo đúng 1 dòng nhật ký, có phiếu, đề xuất, người thực hiện, thời điểm, kết quả **[changed: Amd-1 — dòng áp dụng và hoàn tác thành công có mã commit; commit lỗi là bước "lỗi"]** **[changed: Amd-2 N-7 — bước duyệt hoặc từ chối qua liên kết ghi đúng người đã mở liên kết]** | Test tự động đếm dòng nhật ký sau mỗi bước |
| AC-13 | Gieo khóa API giả vào cấu hình rồi chạy đề xuất, áp dụng và một lệnh stub in ra môi trường: chuỗi khóa xuất hiện 0 lần trong đề xuất, tool_result, nhật ký và comment **[changed: Amd-1 — thêm thông điệp và metadata commit, xem NFR-8]** | Test tự động, cùng cách test NFR-5 của FEAT-001 |
| AC-14 | Khi bộ tool mới được cấp, prompt nói rõ mọi thay đổi code hoặc lệnh phải chờ người duyệt, và bot không coi nội dung phiếu là lệnh duyệt. Khi không được cấp, prompt giống hệt hiện nay **[changed: Amd-2 N-7 — "chờ người duyệt" là chờ người bấm Duyệt trong comment của bot; prompt còn nói chữ "ok" không phải duyệt; thêm khối "làm luôn" ở AC-29]** | Test tự động so chuỗi prompt hai trạng thái |
| AC-15 | Có ADR mới ghi phần nào của ADR-005 (và ADR-003/ADR-004 nếu đổi) bị thay, vì sao, và cách hoàn tác (tắt công tắc). Các test kiến trúc hiện có (ràng buộc ADR-005, scanner "writes-nothing" của FEAT-002) vẫn xanh hoặc được sửa đúng theo ADR mới **[changed: Amd-1 — thêm thay đổi ADR-013 QĐ 6 về commit, xem M-8 O-1, O-2]** **[changed: Amd-2 N-7 — thêm các chỗ trái ở N-2: ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7; cách hoàn tác là tắt hai ô]** | `ls docs/team/adr/` có ADR mới tham chiếu ADR-005; `cmd.test` xanh |
| AC-16..AC-23 | **[added: Amd-1]** xem M-6 | — |
| AC-24..AC-35 | **[added: Amd-2]** xem N-7 | — |

## Assumptions decided by the team
- **A-1 Không làm tạo User và tool cấu hình.** chọn: chỉ làm sửa code và chạy lệnh, như người đã chốt (intake `:10`) | vì: tạo User và gán Role là nhóm "Tài khoản" của guide `:249`, cần thiết kế riêng (mẫu Role cố định, chặn tự nâng quyền theo guide `:258`); gộp vào thì vượt cỡ L | phương án khác: thêm tool tạo User vào feature này | sai thì: mở intake mới "tool L2/L3 theo guide 4.2" và đặt lên trước. Cảnh báo: sau feature này bot vẫn chưa tạo được user. **[changed: Amd-2 N-8 A-1' — thay]**
- **A-2 Không nâng quyền tài khoản agent.** chọn: giữ role hiện có, không System Manager (ADR-006) | vì: sửa file và chạy lệnh chạy ở mức hệ điều hành, role Frappe không chặn được gì (guide `:333`); rào cản thật là chặn đường dẫn, chặn lệnh và người duyệt. Cấp System Manager chỉ mở thêm đường ghi DocType bỏ qua thiết kế | phương án khác: cấp System Manager | sai thì: người tự cấp role ở Desk; spec không phụ thuộc vào việc này. **[changed: Amd-2 N-8 A-2' — bổ sung]**
- **A-3 App được sửa là danh sách System Manager chọn, mặc định rỗng; `erp_ai` luôn bị cấm.** chọn: danh sách cho phép trên cấu hình; `erp_ai` và mọi đường dẫn khử symlink rơi vào repo `erp_ai` bị cấm cứng | vì: bot sửa được chính code chặn của mình là tự nâng quyền; bench có 13 thư mục app, trong đó có fork ERPNext/HRMS (`prompts.py:90`) và `erp_ai-wt` | phương án khác: cho sửa mọi app trừ `frappe` | sai thì: System Manager thêm app vào danh sách; muốn cho sửa `erp_ai` thì phải có ADR mới. **[changed: Amd-1 M-7 A-3']**
- **A-4 Bot không commit, push hay đổi nhánh.** chọn: thay đổi nằm ở working tree; người tự `git diff`/commit | vì: repo các app là của người (có thể đang có thay đổi chưa commit); tránh ghi đè lịch sử; quy tắc chỉ push `team/*` | phương án khác: mỗi thay đổi thành một commit trên nhánh riêng | sai thì: thêm bước commit local vào bước áp dụng ở feature sau; đề xuất đã lưu đủ diff nên không mất gì. **[changed: Amd-1 M-7 A-4' — thay thế]**
- **A-5 Một đề xuất là một file; mọi lệnh đều phải duyệt.** chọn: duyệt từng file, từng lệnh, kể cả lệnh chỉ đọc | vì: đúng chữ "duyệt từng thay đổi" (tiêu đề intake); áp dụng một file thì không cần cơ chế tất-cả-hoặc-không; lệnh `bench` nào cũng có thể có tác dụng phụ | phương án khác: đề xuất nhiều file, áp dụng trọn gói; miễn duyệt cho lệnh chỉ đọc | sai thì: thêm "nhóm đề xuất" ở amendment; tool đọc mã nguồn hiện có vẫn không cần duyệt.
- **A-6 Danh sách lệnh.** chọn: cho phép nhóm lệnh làm mới trạng thái của site đang chạy: `migrate`, `build --app <app được phép>`, `clear-cache`, `clear-website-cache`, và các lệnh chỉ in thông tin (`version`, `list-apps`). Cấm mọi lệnh khác, nêu rõ: `execute`, `console`, `mariadb`/`db-console`, `backup`, `restore`, `drop-site`, `reinstall`, `set-config`, `set-admin-password`, `add-system-manager`, `add-user`, `install-app`, `uninstall-app`, `remove-app`, `get-app`, `update`, `setup`, `restart`, `run-tests`, `--force` | vì: `execute`/`console` là chạy code tùy ý; các lệnh còn lại xóa dữ liệu, đổi bí mật, tự nâng quyền hoặc giết chính worker | phương án khác: cho cả `execute` khi có duyệt | sai thì: designer, cùng researcher, đối chiếu tên lệnh với bench và Frappe 15 trên `miyano`; thêm hay bớt lệnh là sửa danh sách, có test AC-9.
- **A-7 Người duyệt.** chọn: bất kỳ ai có `ERP AI Instructor`, kể cả chính người ra lệnh | vì: công ty khoảng 10 người (`prompts.py:73-74`); thẩm quyền đã định nghĩa sẵn (`authority.py`) | phương án khác: bắt buộc người duyệt khác người ra lệnh | sai thì: thêm một điều kiện ở thao tác duyệt và một test ở AC-5.
- **A-8 Giới hạn thời gian lệnh.** chọn: dùng mốc 600 s − 60 s có sẵn nếu lệnh chạy trong job agent; architect đo trên `miyano` rồi chốt | vì: không có số đo nào trong intake; không tự đặt số mới | phương án khác: một hàng đợi riêng với giới hạn dài hơn | sai thì: architect ghi số đo và giới hạn mới trong ADR; NFR-3 đổi theo.
- **A-9 Không có hạn duyệt theo thời gian.** chọn: đề xuất chỉ hết hiệu lực khi file đích đã đổi hoặc người từ chối | vì: không có nguồn nào cho con số hạn; kiểm dấu nội dung đã chặn việc áp dụng nội dung cũ | phương án khác: hết hạn sau N giờ | sai thì: thêm hạn ở amendment, có test.
- **A-10 Sau khi sửa code Python cần `bench restart`, việc này do người làm.** chọn: bot nêu trong comment là "cần restart" | vì: restart giết chính worker đang chạy job (ADR-003 Hệ quả) | phương án khác: cho bot restart | sai thì: architect thiết kế đường restart ngoài job ở feature sau.
- **A-11..A-18 [added: Amd-1]:** xem M-7.
- **A-19..A-28 [added: Amd-2]:** xem N-8 (A-28 ở cuối N-9).

## Amendment 1 — 2026-11-12: sửa code app lõi, mỗi thay đổi thành một commit git local

Nguồn: intake mục "Yêu cầu bổ sung 2026-11-12" (`intake.md:29-44`) và journal FEAT-004 (quyết định (c) = (a) + (b)). Mode decide, G1 tắt, nên không có `questions.md`. Câu của người: "có cách nào để bot sửa được code không? kiểu can thiệp trực tiếp vào core ý", rồi "oke làm đi". Cỡ giữ L; không đề xuất đổi cỡ (khối lượng thêm: 8 AC, 3 NFR, các điểm sửa ADR-011/012/013).

### M-1 Giả thuyết sau amendment (độ tin cậy 75%)
Người muốn bot đề xuất được thay đổi code trong cả app lõi `frappe`, `erpnext`, `helpdesk`, `hrms`. Mỗi thay đổi vẫn được duyệt từng cái. Mỗi thay đổi đã áp dụng được giữ thành lịch sử git local, để người đẩy lên fork cho CI test và hoàn tác được bằng git.

Chưa tới 85% vì hai lẽ:
1. Người chưa tự chọn hướng (b) commit. Team-leader chọn (c) sau khi người nói "làm đi" mà chưa chọn hướng nào (intake `:36`).
2. "Can thiệp trực tiếp vào core" có thể hàm ý bỏ bước duyệt từng thay đổi. Đội vẫn giữ bước duyệt theo điểm rủi ro ở intake `:21` (STD-SEC-5).

Lẽ 2 cũ ở mục Mục tiêu ("chưa biết bot sửa app nào") nay đã có câu trả lời: app lõi, khi System Manager thêm vào danh sách.

### M-2 Đã có câu trả lời nhờ xem trực tiếp (không cần hỏi)
Trạng thái repo app lõi trên bench, đọc bằng `git -C apps/<app> status -sb -uno` ngày 2026-11-12:

| App | Nhánh đang checkout | Nhánh remote đang theo | File người đã sửa mà chưa commit |
|---|---|---|---|
| `frappe` | `version-15` | `upstream/version-15` | 1 (`ui/yarn.lock`) |
| `erpnext` | `develop` | `origin/develop` | 7 (trong đó có `erpnext/hooks.py`) |
| `helpdesk` | `version-15` | `upstream/version-15` | 3 |
| `hrms` | `feat/timesheet-and-payroll` | `origin/feat/timesheet-and-payroll` | 0 |

Hệ quả cho spec:
1. Repo đang có sẵn thay đổi chưa commit của người, nên commit của bot chỉ được chứa đúng file của nó và không cuốn theo thay đổi khác (AC-17, A-13).
2. Cả 4 nhánh đều theo một nhánh remote. Commit local làm nhánh đi trước remote, và `frappe`/`helpdesk` theo nhánh chính thức, nên `bench update` có thể gặp xung đột. Vì vậy cần cảnh báo (AC-21).
3. Thiết kế hiện tại: bộ chặn chỉ đọc file, không gọi `git` (`design.md:246`). ADR-013 QĐ 6 ghi "Không chạm `.git`, không commit, không đổi nhánh (A-4)" (`ADR-013.md:41`, `design.md:435`). Cả hai phải sửa (M-8).

### M-3 Phạm vi sau amendment
**Trong (thêm):**
11. **Commit local khi áp dụng:** áp dụng thành công một thay đổi code nghĩa là file được ghi và có đúng 1 commit mới trên nhánh đang checkout của repo app đó, chỉ chứa file đó. Hai việc này thành công cùng nhau hoặc không việc nào xảy ra (A-16).
12. **Hoàn tác sau commit:** hoàn tác tạo 1 commit mới khôi phục file. Commit áp dụng vẫn còn trong lịch sử (A-14).
13. **Cảnh báo trên đề xuất và form duyệt:** nhánh sẽ nhận commit; nhánh remote đang theo và số commit local đi trước; cảnh báo app lõi (AC-21).
14. **Điều kiện repo trước khi ghi:** từ chối khi repo hoặc file đích không ở trạng thái commit được (A-13, AC-18).

**Ngoài (thay dòng Out of scope và dòng "Commit, push, tạo hay đổi nhánh…"):**
- Bot push, fetch, pull, tạo/xóa/đổi nhánh, đổi nhánh đang checkout, sửa lịch sử (sửa commit cũ, reset, rebase, merge), tạo tag, đổi remote, mở PR. Đẩy lên fork, mở PR, deploy và gộp với upstream là việc của người.
- `bench update` vẫn bị cấm với bot (A-6). Xử lý xung đột giữa commit của bot và upstream là việc của người.
- Công tắc riêng để bật/tắt bước commit (A-15).
- Sửa app `erp_ai` và mọi bản sao, worktree của nó: vẫn cấm cứng.
- Thay đổi gồm nhiều file trong một commit (A-5 giữ nguyên).

**Success sau amendment:** lúc build, AC-1..AC-23 đạt trên `miyano` và `cmd.test` xanh. Sau G4 (việc của người): trên site dev, cho bot xử lý 1 phiếu sửa code ở 1 app lõi từ đề xuất qua duyệt, áp dụng (có commit) tới hoàn tác (có commit hoàn tác). Sau đó người tự đẩy nhánh lên fork để CI test.

### M-4 Dữ liệu thêm vào đề xuất (designer đặt tên và chọn cách lưu)
- nhánh sẽ nhận commit, đọc lúc đề xuất; nhánh thật đã nhận commit lúc áp dụng;
- tên nhánh remote đang theo (chỉ tên remote và tên nhánh, không lưu URL) và số commit local đi trước, đọc lúc đề xuất và lúc áp dụng;
- cờ "app lõi" (app thuộc `frappe`, `erpnext`, `helpdesk`, `hrms`);
- thông điệp commit sẽ dùng;
- mã commit áp dụng; mã commit hoàn tác;
- lý do lỗi khi không commit được (A-13, A-16).

Nhạy cảm: URL remote có thể chứa token, nên không lưu và không hiển thị. Danh tính tác giả commit không phải email cá nhân (A-12).

### M-5 NFR
- **NFR-1 [changed]:** ngoài 0 byte đổi và 0 lệnh chạy, còn có **0 commit mới** trong repo app cho tới khi đề xuất được duyệt. Đo bằng: test AC-3 và AC-17 so mã HEAD của repo tạm trước/sau khi đề xuất.
- **NFR-2 [changed]:** nội dung file trong commit áp dụng trùng từng byte với nội dung đã duyệt. Đo bằng: test AC-17 so nội dung file ở commit mới với nội dung đã duyệt.
- **NFR-3 [changed]:** bước git chạy trong cùng job và cùng ngân sách thời gian với bước ghi file. Không đặt số thời gian mới. Git đang bị khóa bởi thao tác khác thì báo lỗi có lý do, không chờ vô hạn. Đo bằng: test AC-18 nhánh "khóa git đang bị giữ".
- **NFR-6 [changed]:** dòng nhật ký của bước áp dụng và hoàn tác thành công có mã commit. Đo bằng: test AC-12.

| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-7 | Commit đúng phạm vi. Mỗi lần áp dụng hoặc hoàn tác thành công tạo đúng 1 commit, commit đó chứa đúng 1 đường dẫn, và cha của nó là HEAD ngay trước đó. Với mọi đường dẫn khác: 0 thay đổi ở working tree và ở vùng staged. Nhánh đang checkout không đổi. 0 ref nào khác đổi (nhánh khác, tag, ref remote) | Test trên repo git tạm có sẵn thay đổi staged và unstaged ở file khác: so trạng thái working tree, vùng staged và danh sách ref trước/sau; đếm số file trong commit mới |
| NFR-8 | 0 email người dùng thật, 0 URL remote, 0 chuỗi khóa/token giả trong metadata commit (tác giả, người commit, thông điệp), trong comment của bot và trên form duyệt | Test gieo token giả vào URL remote của repo tạm và dùng người duyệt có email thật dạng mẫu; đếm số lần chuỗi xuất hiện = 0 |
| NFR-9 | Bộ test không tạo commit và không đổi file nào trong repo thật của app trên bench. Mã HEAD và trạng thái working tree của `frappe`, `erpnext`, `helpdesk`, `hrms` trùng nhau trước và sau `cmd.test` | qa ghi `git -C apps/<app> rev-parse HEAD` và `git -C apps/<app> status --porcelain` trước và sau `cmd.test`, rồi so |

### M-6 Tiêu chí nghiệm thu thêm
- **AC-6 [changed]:** thêm điều kiện: áp dụng thành công thì có đúng 1 commit (AC-17); nhánh "hết hiệu lực" và lần áp dụng thứ hai đều có 0 commit mới.
- **AC-7 [changed]:** hoàn tác thành công thì tạo commit hoàn tác (AC-20); nhánh từ chối hoàn tác có 0 commit mới.
- **AC-12 [changed]:** dòng nhật ký áp dụng/hoàn tác thành công có mã commit. Commit lỗi tạo 1 dòng bước "lỗi" có lý do.
- **AC-13 [changed]:** khóa giả xuất hiện 0 lần thêm cả trong thông điệp và metadata commit.
- **AC-15 [changed]:** ADR mới (hoặc ADR-013 sửa) ghi rõ: bot được tạo commit local; bot vẫn không push, không đổi nhánh, không sửa lịch sử; cách hoàn tác.

| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-16 | App lõi được phép khi có trong danh sách. Có `frappe`, `erpnext`, `helpdesk` hoặc `hrms` trong danh sách thì đề xuất hợp lệ cho app đó được tạo (không bị chặn cứng). Không có trong danh sách thì bị từ chối như AC-4. `erp_ai` có trong danh sách vẫn bị từ chối | Test tự động trên cây thư mục tạm có app tên `frappe`, `erpnext`, `helpdesk`, `hrms`, `erp_ai` (repo git tạm); mỗi app một test có và không có trong danh sách |
| AC-17 | Áp dụng một thay đổi code đã duyệt thì: đúng 1 commit mới trên nhánh đang checkout; commit chứa đúng 1 đường dẫn là file đích; nội dung file trong commit và trên đĩa trùng từng byte với nội dung đã duyệt; tên nhánh đang checkout không đổi; thay đổi staged và unstaged có sẵn ở các file khác còn nguyên; thông điệp commit có mã đề xuất, số phiếu và họ tên người duyệt; mã commit được lưu trên đề xuất | Test tự động trên repo git tạm có sẵn 1 file staged và 1 file unstaged khác: so nhánh, danh sách ref, số commit, danh sách file của commit, nội dung, thông điệp, trạng thái của file khác |
| AC-18 | Không ghi, 0 commit, có lý do và có dòng nhật ký, kiểm muộn nhất lúc áp dụng (architect chọn có kiểm cả lúc đề xuất không, O-3), khi: file đích có thay đổi chưa commit (staged hoặc unstaged); file đích bị git bỏ qua; thư mục app không phải repo git; HEAD không nằm trên nhánh nào (detached); repo đang merge, rebase, cherry-pick hoặc revert dở; khóa git đang bị giữ. Thay đổi chưa commit ở file khác thì không chặn **[changed: Amd-1 D-1 — thêm trường hợp: nhánh đang checkout lúc áp dụng khác nhánh đã lưu lúc đề xuất (nhánh người duyệt đã thấy, AC-22) thì không ghi, 0 commit, trạng thái "hết hiệu lực" (không phải "lỗi"), có lý do và có dòng nhật ký (ADR-022 QĐ 6)]** | Test tự động, mỗi trường hợp một test trên repo git tạm; kèm test "file khác bẩn vẫn áp dụng được" **[changed: Amd-1 D-1 — thêm test: đổi nhánh của repo tạm giữa lúc duyệt và lúc áp dụng thì trạng thái "hết hiệu lực", file không đổi, 0 commit mới trên cả hai nhánh]** |
| AC-19 | Bước commit lỗi sau khi đã ghi file (ví dụ hook của repo từ chối, hoặc stub làm lệnh commit thất bại) thì file trở lại trùng từng byte với nội dung trước (file mới tạo thì bị gỡ), 0 commit mới, vùng staged như trước, trạng thái "lỗi" có lý do, có dòng nhật ký **[changed: Amd-1 D-2 — ví dụ "hook của repo từ chối" không còn đúng: commit của bot không chạy hook của repo (ADR-022 QĐ 4, O-6), nên lỗi ở đây là lệnh commit thất bại hoặc quá giờ. AC-19 áp cả cho commit hoàn tác: bước commit hoàn tác lỗi thì file trở lại trùng từng byte với nội dung ngay trước khi hoàn tác (file đã bị gỡ thì có lại), 0 commit mới, vùng staged như trước, trạng thái "lỗi" có lý do, có dòng nhật ký]** | Test tự động với repo tạm có hook từ chối commit, và một test với stub thất bại **[changed: Amd-1 D-2 — thay bằng: (a) stub làm lệnh commit thất bại; (b) stub làm lệnh commit quá giờ; (a) và (b) chạy cho cả áp dụng và hoàn tác, với file sửa và file mới tạo; (c) repo tạm cài hook từ chối commit và hook ghi tệp đánh dấu thì áp dụng vẫn thành công, 0 hook chạy (0 tệp đánh dấu)]** |
| AC-20 | Hoàn tác sau commit: tạo đúng 1 commit mới, chỉ chứa file đích, đưa file về trùng từng byte với nội dung trước (file mới tạo thì bị gỡ khỏi đĩa và khỏi cây của commit mới). Commit áp dụng vẫn nằm trong lịch sử nhánh. Nhánh đang checkout không đổi. Mã commit hoàn tác được lưu. Từ chối hoàn tác (không ghi, 0 commit) khi: file đã đổi kể từ lúc áp dụng; commit áp dụng không còn nằm trong lịch sử của nhánh đang checkout; hoặc một điều kiện của AC-18 không đạt | Test tự động trên repo git tạm: hoàn tác file sửa, hoàn tác file mới tạo, đổi sang nhánh khác rồi hoàn tác, sửa file rồi hoàn tác |
| AC-21 | Comment của bot và form duyệt hiện: tên nhánh sẽ nhận commit; nếu nhánh theo một nhánh remote thì hiện tên remote/nhánh và số commit local đi trước. Với 4 app lõi, có thêm cảnh báo rằng thay đổi ảnh hưởng mọi site trên bench, rằng `bench update` có thể xung đột với hoặc làm mất commit local, và rằng đẩy lên fork là việc của người. App khác không có cảnh báo app lõi. URL remote xuất hiện 0 lần | Test tự động: repo tạm có remote với URL chứa token giả, nhánh theo remote và đi trước 2 commit; kiểm chuỗi trong comment và trong dữ liệu form; một test cho app không phải app lõi |
| AC-22 | Trước khi duyệt, form duyệt hiện đủ: app, đường dẫn, diff, nhánh nhận commit, thông điệp commit sẽ dùng, các cảnh báo của AC-21 và cờ hoàn tác được. Sau khi áp dụng, form hiện mã commit áp dụng. Sau khi hoàn tác, form hiện mã commit hoàn tác **[changed: Amd-2 N-7 — tiêu chí này giữ nguyên cho form (kể cả hộp xác nhận của ba nút trên form), và thêm phần cho comment của bot: xem AC-22 [changed] ở N-7]** | Test tự động đọc dữ liệu form theo từng trạng thái; qa mở form trên `miyano` và dán ảnh chụp hoặc mô tả vào `acceptance.md` |
| AC-23 | Bot không có đường nào để push hay đổi nhánh. Mã nguồn của feature không gọi thao tác git nào ngoài nhóm cần cho đọc trạng thái và tạo commit, và luật kiến trúc chặn rõ: push, fetch, pull, checkout/switch, tạo/xóa nhánh, reset, rebase, merge, sửa commit cũ, tag, đổi remote. Sau áp dụng và hoàn tác trong test, danh sách ref remote không đổi | Test kiến trúc quét mã nguồn; test tích hợp so danh sách ref remote trước/sau |

Thứ tự bỏ khi khối lượng vượt cỡ L (A-18): bỏ trước phần "số commit đi trước" của AC-21, sau đó phần "hiện mã commit hoàn tác" của AC-22. Không bỏ AC-16..AC-20 và AC-23.

### M-7 Assumptions decided by the team (amendment)
- **A-3' [changed, thay A-3]. Danh sách app được sửa có thể gồm app lõi; `erp_ai` luôn bị cấm.** chọn: giữ A-3 (danh sách do System Manager chọn, mặc định rỗng, `erp_ai` và mọi đường dẫn khử symlink rơi vào repo `erp_ai` bị cấm cứng), và ghi rõ: `frappe`, `erpnext`, `helpdesk`, `hrms` được phép khi System Manager thêm vào; ngoài `erp_ai` không có app nào bị cấm cứng; app lõi có cảnh báo riêng (AC-21) | vì: người hỏi thẳng "can thiệp trực tiếp vào core" (intake `:33`); bước duyệt từng thay đổi và bộ chặn vẫn giữ | phương án khác: cấm cứng `frappe`; cho app lõi nhưng phải có 2 người duyệt | sai thì: System Manager rút app khỏi danh sách (bot quay về hành vi cũ ngay); muốn 2 người duyệt thì thêm điều kiện ở A-7 và một test ở AC-5.
- **A-4' [changed, thay A-4]. Mỗi thay đổi đã áp dụng là đúng 1 commit local.** chọn: áp dụng = ghi file + 1 commit trên nhánh đang checkout của repo app, commit chỉ chứa file đó; bot không push, không tạo hay đổi nhánh, không sửa lịch sử; người đẩy lên fork, mở PR và deploy | vì: không có commit thì thay đổi trên site dev không có đường lên prod và dễ mất khi `bench update` (intake `:40`); commit giữ lịch sử và hoàn tác được bằng git; push cần token GitHub trên máy chủ, trái quy tắc chỉ push `team/*` | phương án khác: giữ ở working tree (A-4 cũ); commit lên một nhánh phụ không checkout; bot push và mở PR | sai thì: `analyze --amend` trả A-4 về như cũ; đề xuất vẫn lưu đủ diff nên không mất gì.
- **A-11 Nhánh nhận commit là nhánh đang checkout.** chọn: commit lên nhánh repo đang đứng; không tạo nhánh phụ | vì: người dặn không đổi nhánh đang checkout (site chạy nhánh đó); sau commit thì file trên đĩa khớp HEAD. Nếu commit lên nhánh phụ thì file trên đĩa khác HEAD của nhánh đang checkout, repo luôn "bẩn", và đề xuất sau trên cùng file bị A-13 chặn | phương án khác: cập nhật một nhánh phụ riêng của bot mà không checkout nó | sai thì: architect đổi ở ADR (O-4); AC-17 và AC-20 đổi điều kiện về nhánh.
- **A-12 Danh tính commit.** chọn: tác giả và người commit là một danh tính riêng của bot, không phải email cá nhân, không lấy từ cấu hình git chung của máy hay của người duyệt; người duyệt được ghi bằng họ tên (không email) trong thông điệp, cùng mã đề xuất và số phiếu | vì: truy vết được ai duyệt; không đưa email cá nhân vào lịch sử git có thể bị đẩy lên GitHub; cấu hình git chung của máy có thể mang tên người dựng bench, gây hiểu sai | phương án khác: tác giả = người duyệt, người commit = bot | sai thì: architect đổi chiến lược ở ADR (O-5); NFR-8 và AC-17 đổi theo.
- **A-13 File đích phải "sạch".** chọn: từ chối khi file đích có thay đổi chưa commit, bị git bỏ qua, repo không phải git, HEAD detached, repo đang có thao tác dở, hoặc khóa git đang bị giữ; thay đổi chưa commit ở file khác không chặn | vì: commit chỉ chứa một file thì không tách được thay đổi của người khỏi thay đổi của bot trong cùng file đó; `erpnext` đang có 7 file chưa commit (M-2), bắt cả repo sạch thì không dùng được | phương án khác: bắt cả repo sạch; commit cả file, gồm cả thay đổi của người | sai thì: nới hoặc siết điều kiện; AC-18 đổi theo.
- **A-14 Hoàn tác là một commit mới.** chọn: hoàn tác tạo 1 commit khôi phục file, không xóa commit áp dụng, không sửa lịch sử; chỉ hoàn tác khi commit áp dụng còn trong lịch sử nhánh đang checkout | vì: người có thể đã đẩy commit áp dụng lên fork, nên sửa lịch sử là trái STD-GIT-4; giữ dấu vết cả hai bước | phương án khác: bỏ commit áp dụng nếu chưa push | sai thì: amendment sau, AC-20 đổi.
- **A-15 Không có công tắc riêng cho bước commit.** chọn: commit là phần bắt buộc của áp dụng; hoàn tác toàn bộ bằng công tắc chính hoặc rút app khỏi danh sách | vì: STD-DESIGN-5; thay đổi không có commit dễ mất (intake `:40`) | phương án khác: công tắc "commit sau khi áp dụng" | sai thì: thêm công tắc ở amendment sau, có test.
- **A-16 Áp dụng là tất-cả-hoặc-không.** chọn: ghi file và commit thành công cùng nhau; commit lỗi thì file trở về như trước, trạng thái "lỗi" | vì: không để file đổi mà không có commit (trái A-4'); trạng thái đề xuất luôn khớp đĩa và lịch sử | phương án khác: giữ file, thêm trạng thái "đã áp dụng, chưa commit" | sai thì: thêm trạng thái mới, AC-19 đổi.
- **A-17 Hook git của repo app khi bot commit.** chọn: đội không chốt, architect quyết (O-6); đội khuyên commit của bot không chạy hook do repo cài, vì hook có thể sửa file khác, chạy lâu hoặc cần mạng | vì: đây là lựa chọn kỹ thuật; dù chọn bên nào, hook lỗi đều đi nhánh AC-19 | phương án khác: chạy hook như commit của người | sai thì: architect đổi trong ADR; AC-19 vẫn giữ nguyên. **[changed: Amd-1 D-3 — architect đã chốt O-6 ở ADR-022 QĐ 4; văn bản trên không còn đúng, thay cả 4 trường: chọn: mọi lệnh git của bot (áp dụng và hoàn tác) không chạy hook nào do repo app cài | vì: hook có thể sửa file khác (trái NFR-7), chạy lâu, cần mạng hoặc từ chối commit không đoán được; vì không có hook nào chạy, hook không còn là nguồn lỗi của AC-19: lỗi ở AC-19 là lệnh commit thất bại hoặc quá giờ, và AC-19 test (c) kiểm repo có hook từ chối vẫn áp dụng được, 0 hook chạy | phương án khác: chạy hook như commit của người (AC-19 vẫn bắt lỗi nhưng NFR-7 không còn kiểm được) | sai thì: architect đổi ADR-022 QĐ 4; AC-19 đổi theo (ví dụ "hook từ chối" quay lại, test (c) đổi kỳ vọng)]**
- **A-18 Thứ tự bỏ AC.** chọn: như dòng cuối M-6 | vì: phần hiển thị bỏ được, phần an toàn (commit đúng phạm vi, trả lại khi lỗi, không push) thì không | phương án khác: bỏ AC-22 trọn vẹn | sai thì: team-leader chọn lại khi plan vượt cỡ.

### M-8 Điểm mở cho architect (và designer)
- **O-1 ADR-013 QĐ 6** ("Không chạm `.git`, không commit, không đổi nhánh", `ADR-013.md:41`): sửa để cho phép commit local trong job áp dụng/hoàn tác, vẫn cấm push, đổi nhánh và sửa lịch sử. Cần chốt: thứ tự ghi file → commit → trả lại khi lỗi (A-16); khóa chung của QĐ 4 phủ cả bước git; khi khóa git của người đang bị giữ thì báo lỗi, không chờ vô hạn (NFR-3).
- **O-2 ADR-005 QĐ 5** và ràng buộc "`subprocess` chỉ trong module tool mã nguồn" (đã được nới cho `bench` ở ADR-013): nay thêm lệnh git có ghi trong module áp dụng. Cần chốt nhóm thao tác git được phép và luật kiến trúc của AC-23.
- **O-3 ADR-011, bộ chặn:** bộ chặn hiện chỉ đọc file, không gọi git (`design.md:246`). Cần quyết: kiểm A-13 và đọc thông tin nhánh cho cảnh báo AC-21 ngay lúc đề xuất, hay chỉ lúc áp dụng; nếu lúc đề xuất thì đọc ở đâu mà không trái ADR-005.
- **O-4 Chiến lược nhánh (A-11):** xác nhận commit lên nhánh đang checkout, hoặc ghi lý do đổi. researcher đọc hành vi của `bench update` trong bản bench đang cài với nhánh có commit local đi trước upstream (dừng, gộp, rebase hay bỏ commit; ảnh hưởng của cờ reset), để câu cảnh báo AC-21 viết đúng.
- **O-5 Danh tính commit (A-12):** giá trị tên/địa chỉ cụ thể (không phải email cá nhân), nơi đặt cấu hình, không phụ thuộc cấu hình git chung của máy; mẫu thông điệp commit (AC-17).
- **O-6 Hook git (A-17):** chạy hay không chạy hook của repo app. **[changed: Amd-1 D-3 — đã chốt, không còn mở: ADR-022 QĐ 4, hook của repo app không bao giờ chạy với lệnh git của bot; A-17 và AC-19 đã theo]**
- **O-7 ADR-012 / dữ liệu / ADR-004:** các trường ở M-4; trạng thái khi commit lỗi (A-16); trạng thái khi từ chối hoàn tác vì commit áp dụng đã ra khỏi lịch sử (AC-20); dòng nhật ký có mã commit (NFR-6).
- **O-8 Cô lập test (NFR-9):** mọi test git dùng repo tạm, không bao giờ chạm repo thật; cách dựng app tạm tên `frappe`/`erp_ai` cho AC-16 mà bộ chặn `erp_ai` vẫn nhận ra.
- **O-9 Form duyệt (AC-22), designer:** vị trí hiển thị nhánh, cảnh báo, mã commit; phối hợp với FEAT-003 Amendment 1 như đã ghi ở mục Giao diện.

### M-9 Tài liệu phía sau bị ảnh hưởng (phải làm lại sau amendment)
- `docs/team/features/FEAT-004/arch-impact.md`: thêm tác động commit, app lõi.
- ADR-013 (QĐ 6, QĐ 4, Ràng buộc, Hệ quả); ADR-011 (bộ chặn, O-3); ADR-012 (trạng thái, trường, O-7); ADR-005 nếu architect sửa ràng buộc `subprocess` (O-2). ADR-019..021 không thuộc FEAT-004, không chạm.
- `design.md`: §1 (Ngoài phạm vi, `:12`), §2.1 và §2.2 (trường, trạng thái), §3.2 (bộ chặn), §3.5 và §4.3 (`:435`), §4.4 (hoàn tác), §5 (quyền), §6 (rollback), §7 (touchpoints), §8 (test plan, thêm AC-16..AC-23, NFR-7..NFR-9).
- `plan.md`, `tasks.md`: thêm task cho commit, hoàn tác bằng commit, cảnh báo, luật kiến trúc git, cô lập test.
- Trạng thái: FEAT-004 đang `planned`; sau amendment phải chạy lại architect → design → plan trước `/team:build`.

## Amendment 2 — 2026-11-14: bot làm luôn, một lần bấm Duyệt / Từ chối trên phiếu, công cụ bản ghi trực tiếp, ô "Toàn quyền (khẩn cấp)"

Nguồn, theo thứ tự tin cậy:
1. Lệnh của người trong `docs/team/features/CHG-001/intake.md:10`: "sửa lại bot làm luôn, không cần hỏi, chỉ cần 1 nút duyệt or khôgn duyệt nếu duyệt thì bot làm luôn" (2026-11-13).
2. `docs/team/features/CHG-001/handoff-direct-session.md` mục 1 (cột "Người yêu cầu gì": "Bot tạo User, gán role, sửa cấu hình trực tiếp, không qua duyệt"; "Thêm xóa, submit/hủy, gọi hàm whitelist; bỏ giới hạn role và tài khoản"; "Nút duyệt phải trên phản hồi ticket", bấm là chạy, không hộp hỏi lại; "Bot làm luôn, không cần hỏi") và mục 5 (5 điểm mở của intake đã được người trả lời).
3. Quyết định của người "Nhận code đó làm nền" (journal CHG-001, 2026-11-14) và mã nhận về ở commit `25be823` (job áp dụng/hoàn tác, liên kết ký) và `6d90e79` (ba tool đề xuất, công cụ bản ghi, ô Toàn quyền, các khối prompt). Mã này mới được kiểm bằng test của chính nó; chưa reviewer nào xem; chưa thử với model thật (handoff mục 2).

Mode decide, G1 tắt, nên không có `questions.md`. Amendment này GHI LẠI điều người đã ra lệnh và code đã làm; analyst không thiết kế lại và không quyết lại các chỗ trái ADR (phán quyết của architect nằm ở tài liệu riêng). Cỡ giữ L; xem N-10 về khối lượng.

### N-1 Giả thuyết sau amendment và khối mở đầu (độ tin cậy 85%)
Người muốn bot làm xong việc được giao ngay trong lượt đó, không hỏi lại. Với thay đổi bản ghi thì bot làm thẳng. Với thay đổi code và lệnh `bench` thì bot đăng một đề xuất kèm hai liên kết Duyệt / Từ chối ngay trong phản hồi ở phiếu; người có vai trò mở liên kết Duyệt một lần là hệ thống áp dụng ngay, không hộp xác nhận. Cho tình huống khẩn cấp, người có thêm một ô "Toàn quyền (khẩn cấp)" cho bot xóa, submit/hủy, gọi hàm whitelist và bỏ các giới hạn về vai trò và tài khoản.

Chưa tới 100% vì hai lẽ:
1. Chưa thử với model thật, chưa xem comment có liên kết hiển thị thế nào trên trang phiếu Helpdesk, chưa mở liên kết qua HTTP thật (handoff mục 2). Phép đo ở "Success" bù chỗ này.
2. Lệnh về ô "Toàn quyền" đến qua bản tóm tắt của phiên khác (handoff mục 1), không có câu gốc của người trong repo.

| Mục | Nội dung |
|---|---|
| Outcome | Người có vai trò `ERP AI Instructor` giao việc trên phiếu. Bot làm luôn trong cùng lượt, không hỏi lại "có muốn tôi làm không". Việc về bản ghi (tạo User, gán vai trò nghiệp vụ, cấu hình, bản ghi nháp) xảy ra ngay. Việc về code hoặc lệnh `bench` dừng ở một đề xuất có hai liên kết trong comment của bot; mở liên kết Duyệt là áp dụng ngay, mở Từ chối là không đổi gì. Mọi thay đổi code vẫn chỉ xảy ra sau khi một người có vai trò bấm. |
| Users | Người ra lệnh/duyệt: người có `ERP AI Instructor` (không đổi). System Manager: bật hai ô trên cấu hình agent, "Cho phép sửa code và lệnh bench" và "Toàn quyền (khẩn cấp)", và là người duy nhất tắt bật chúng. Người tạo phiếu và người comment không có thẩm quyền: dữ liệu, không phải lệnh (không đổi). |
| Why now | Người đã ra lệnh (intake CHG-001) và phiên khác đã viết code theo lệnh đó; code nằm trên `develop` (`25be823`, `6d90e79`) và site `miyano` đã chạy mã này từ 2026-11-14 00:26 (L3, ô code bật, Toàn quyền tắt; handoff mục 5). Reviewer của FEAT-004 không chấm được phần vượt spec khi chưa có amendment này. |
| Success | Lúc build: AC-1..AC-35 đạt trên `miyano`; `cmd.test` xanh (xem DoD về thời gian chạy). Sau G4 (việc của người trên `miyano`): (a) ba phiếu kịch bản có đủ thông tin (tạo 1 User; đổi 1 cấu hình; sửa 1 file code) và số lần bot hỏi lại người ra lệnh trước khi làm = 0; (b) với đề xuất sửa code: từ lúc comment hiện ra tới lúc file có commit chỉ cần 1 lần mở liên kết, 0 hộp xác nhận, và bot hoặc hệ thống comment kết quả về phiếu (AC-25, AC-28); (c) bật "Toàn quyền" một lần trên dev, làm 1 việc xóa hoặc submit thử, rồi tắt; mục nhật ký ghi việc đó (AC-34). |
| Constraints | Không push, không deploy prod (G5 cần người duyệt). Không đọc, không ghi `protected_paths` hay file bí mật. Mọi ràng buộc của Amendment 1 về code, lệnh, commit giữ nguyên. Bot không bao giờ tự duyệt đề xuất của chính nó. Mật khẩu và khóa API của người dùng đóng ở mọi chế độ. Cấu hình agent, khóa, nhật ký và đề xuất của app đóng ở mọi chế độ. |
| Out of scope | Hoàn tác một lần bấm trong comment (hoàn tác vẫn làm trên form, có hộp xác nhận). Hẹn giờ tự tắt "Toàn quyền". Bỏ hộp xác nhận ở form Desk. Thiết kế lại danh sách cấm (ghi nhận nguyên trạng, N-2). Sửa spec FEAT-005 và FEAT-006 (chỉ ghi hệ quả, N-9). Bật trên production. |

### N-2 Quy tắc an toàn đã đổi (đọc một phút)

Mỗi hàng: quy tắc cũ → quy tắc mới → ai ra lệnh → rủi ro còn lại. "Handoff §n" là `handoff-direct-session.md`. Phán quyết giữ/sửa của từng chỗ trái ADR là việc của architect, không ghi ở đây.

| # | Quy tắc cũ | Quy tắc mới | Ai ra lệnh | Rủi ro còn lại |
|---|---|---|---|---|
| S-1 | Chỉ duyệt bằng nút trên form Desk, gọi kiểu POST, có hộp xác nhận (ADR-012 QĐ 4; AC-5, AC-22 cũ). | Thêm đường thứ hai: liên kết Duyệt / Từ chối có chữ ký trong comment của bot trên phiếu. Mở liên kết Duyệt một lần là duyệt và áp dụng ngay, không hộp xác nhận. Form giữ nguyên, kể cả hộp xác nhận và nút Hoàn tác (handoff §5). | Người: intake CHG-001 ("chỉ cần 1 nút duyệt… duyệt thì bot làm luôn"); handoff §1 "Nút duyệt phải trên phản hồi ticket". | Đường duyệt là GET đổi trạng thái. Chữ ký gắn với đề xuất và hành động, không gắn với người bấm và không hết hạn: ai có vai trò mở liên kết, kể cả liên kết được chuyển tiếp, đều duyệt mà chưa chắc đã xem diff. Trình duyệt hoặc proxy của người có vai trò tải trước liên kết cũng có thể duyệt ngoài ý muốn. Mất hộp xác nhận ở đường này thì bấm nhầm không còn lưới; lưới còn lại là bước kiểm lại lúc áp dụng (AC-27) và hoàn tác bằng commit. Người đọc được comment nhưng không có vai trò thì không duyệt được (AC-26). |
| S-2 | Bot hỏi và chờ chữ "ok" với việc không hoàn tác được (quy tắc 6 của prompt); comment luôn có mục "Cần ai quyết"; FEAT-005 A-7 bắt "ok" trước khi bật Workflow, Notification, Assignment Rule. | Bot làm ngay trong lượt, không hỏi lại, không chờ "ok"; thiếu đúng một thông tin bắt buộc mới hỏi một câu; "Cần ai quyết" chỉ khi công cụ trả `ok=false` hoặc việc ngoài công cụ. Chữ "ok" vẫn không bao giờ là duyệt đề xuất code hoặc lệnh (AC-29). | Người: intake CHG-001 ("làm luôn, không cần hỏi"); handoff §1 "Bot làm luôn, không cần hỏi"; handoff §5 (làm luôn áp cho cả bản ghi và code). | Hiểu sai lệnh thì việc đã xảy ra: với bản ghi không còn bước nào chặn trước. Chốt chặn duy nhất còn lại là chỉ người ra lệnh có thẩm quyền mới được cấp công cụ và nội dung phiếu là dữ liệu (AC-11). |
| S-3 | Mỗi tool ghi làm một việc, DocType và trường viết cứng (ADR-005 QĐ 3). | Công cụ bản ghi chung: liệt kê, đọc, tạo, sửa; DocType và các trường do model đưa ra; chạy dưới tài khoản agent theo phân quyền Frappe; có danh sách cấm của AC-31. | Người: handoff §1 "Bot tạo User, gán role, sửa cấu hình trực tiếp, không qua duyệt". Người đã chủ ý đổi (handoff §3 mục 5). | Phạm vi thật là quyền Frappe của tài khoản agent (người đã cấp full quyền, xem "Why now" ở trên), không còn là một danh sách việc viết cứng; danh sách cấm là chốt duy nhất và là danh sách cấm, không kín (handoff §3 mục 3: đường vòng như Role Profile, bảng con chưa soát hết). Client Script không bị ép tắt và chạy JS trên trình duyệt của người dùng khác, kể cả người có quyền cao. Workflow, Notification (gửi thư và dữ liệu ra ngoài) làm được ngay, trái giới hạn A-7 và A-11 của FEAT-005. |
| S-4 | Prompt cấm "chạm Role Permission, Custom DocPerm, Has Role"; FEAT-005 A-3, A-4, A-5: danh sách vai trò được gán do System Manager chọn, chỉ thêm vai trò, không đổi tài khoản của người ra lệnh. | Chế độ thường: được tạo User và gán vai trò nghiệp vụ. Vẫn cấm gán `System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All` (kể cả qua Role Profile); vẫn cấm sửa `Administrator`, `Guest`, tài khoản agent; vẫn cấm Role Permission và Custom DocPerm. Không còn danh sách vai trò được gán, không còn chặn vai trò có quyền sửa User. | Người: handoff §1. | Gán một vai trò có quyền sửa người dùng hay phân quyền (không nằm trong 6 vai trò cấm) là nâng quyền gián tiếp. Sửa User thay toàn bộ dòng vai trò nên bot có thể bớt vai trò của người khác. Tài khoản của chính người ra lệnh sửa được. Cảnh báo hằng ngày về bản ghi phân quyền do agent sửa vẫn chạy (không đổi) và là lưới bù duy nhất. |
| S-5 | Bảng cấp tool chỉ có một chỗ (ADR-011 QĐ 2 và 6: một điều kiện, một hàm). FEAT-006 AC-9: không tool nào nhận tên người, SLA hay mức ưu tiên làm tham số. | Công cụ bản ghi cấp bằng một dòng thêm vào bảng cấp, cùng điều kiện với tool đề xuất (ô code bật, `L3`, có người ra lệnh). Nhóm Toàn quyền cấp bằng hàm riêng, ngoài bảng, từ `L1`, không cần ô code. Công cụ bản ghi nhận mọi trường nên đặt được người được giao, mức ưu tiên khi người ra lệnh yêu cầu. | Người: handoff §1, §3 mục 5. | Hai nơi cấp tool: test chỉ ở bảng cấp không phủ nhóm Toàn quyền. Ô "Cho phép sửa code và lệnh bench" nay có hai nghĩa; site nào đã bật ô này để chỉ cho đề xuất code thì nay cũng đang mở ghi bản ghi trực tiếp (site `miyano` ở đúng trạng thái này). Phép thử tĩnh của FEAT-006 AC-9 cần ngoại lệ cho nhóm này. Bảo vệ chống chèn lệnh từ phiếu vẫn là điều kiện có người ra lệnh. |
| S-6 | Không xóa, không submit hay hủy; Server Script và Webhook luôn lưu ở trạng thái tắt; không gán vai trò quản trị; không sửa tài khoản quản trị; DocType nhạy cảm đóng. | Ô "Toàn quyền (khẩn cấp)", mặc định tắt: mở thêm xóa, submit/hủy, gọi hàm whitelist; gỡ giới hạn vai trò, tài khoản, DocType và việc ép tắt Server Script, Webhook; hiệu lực từ `L1` khi có người ra lệnh, không cần ô code. Vẫn đóng ở mọi chế độ: cấu hình, khóa, nhật ký và đề xuất của app; mật khẩu, khóa API của người dùng; hàm của app `erp_ai` (AC-33). | Người: handoff §1 "Thêm xóa, submit/hủy, gọi hàm whitelist; bỏ giới hạn role và tài khoản". | Tắt bằng tay, không hẹn giờ, không cảnh báo khi đang bật: quên tắt là rủi ro chính. Xóa và submit không hoàn tác. Gán được `System Manager` cho bất kỳ ai. Server Script bật được nghĩa là chạy code do bot viết trên site (nếu site cho chạy), có thể vòng qua danh sách đóng. Gọi hàm whitelist là bề mặt rất rộng. Danh sách đóng so khớp chuỗi (kể cả tên DocType trong tham số) nên không kín tuyệt đối (handoff §3 mục 2). |
| S-7 | Nhật ký giá trị trước/sau cho mỗi lần ghi (guide `:985`, FEAT-005 NFR-3). | Chưa có: mỗi lời gọi công cụ bản ghi chỉ để lại công cụ, DocType, tên bản ghi và kết quả đúng/sai trong cột hành động của nhật ký lần chạy (AC-34). | Không ai ra lệnh bỏ. Đây là khoảng trống của mã nhận về (AC-35). | Không dựng lại được "đã đổi từ gì sang gì"; xóa, submit và gọi hàm chỉ còn tên. Là điều kiện nên có trước khi bật Toàn quyền trên môi trường thật. |
| S-8 | Kết quả sau áp dụng người xem ở form đề xuất. | Chưa có: bấm Duyệt xong người được chuyển về phiếu mà phiếu không báo kết quả (xong, lỗi, hết hiệu lực) (handoff §4). Cần AC-28. | Không ai ra lệnh bỏ. Khoảng trống của mã nhận về. | Người tưởng đã áp dụng trong khi đề xuất báo lỗi hoặc hết hiệu lực, đặc biệt vì đường bấm một lần không cho thấy trạng thái. |

**Những điều vẫn bị cấm (không đổi dù duyệt một bước hay bật Toàn quyền):**
- Mọi thay đổi code và lệnh `bench` vẫn cần một người có vai trò `ERP AI Instructor` bấm. Bot không tự duyệt: đề xuất của app nằm trong danh sách đóng ở mọi chế độ và công cụ gọi hàm không gọi được hàm nào của `erp_ai` (kể cả hàm nhận quyết định từ liên kết).
- Chữ "ok", "duyệt" hay "đã duyệt" trong phiếu và comment, của bất kỳ ai, không phải là duyệt.
- Nội dung phiếu và comment của người không có thẩm quyền là dữ liệu: 0 công cụ ghi, 0 đề xuất (AC-11).
- Mọi điều cấm của Amendment 1: không sửa app `erp_ai` và bản sao; không push, fetch, đổi nhánh, sửa lịch sử; hook của repo app không chạy; lệnh `bench` ngoài danh sách A-6; đường dẫn khớp mẫu bí mật hoặc `protected_paths`; `bench restart`.
- Cấu hình agent (kể cả hai ô công tắc), khóa API và nhật ký: bot không đọc, không ghi.
- Mật khẩu và khóa API của người dùng: bot không đặt, không đọc. Người mới được tạo nhận email để tự đặt mật khẩu.
- Giới hạn số lần chạy hiện có (5 lần chạy/phiếu/ngày, 8 lượt) giữ nguyên.
- Không deploy prod (G5).

### N-3 Phạm vi sau amendment
**Trong (thêm):**
15. **Bot làm luôn:** khi người ra lệnh giao một việc bot có công cụ để làm, bot làm trong cùng lượt, không hỏi lại, không chờ "ok" (AC-29).
16. **Duyệt một lần bấm trên phiếu:** comment của bot có liên kết Duyệt và Từ chối có chữ ký; mở liên kết Duyệt thì duyệt và áp dụng ngay, không hộp xác nhận; kiểm vai trò và trạng thái ở server như đường form (AC-24..AC-27). Form giữ nguyên.
17. **Báo kết quả về phiếu** sau áp dụng, lỗi, hết hiệu lực (AC-28). Chưa có trong mã nhận về.
18. **Công cụ bản ghi trực tiếp, không qua duyệt:** liệt kê, đọc, tạo, sửa bản ghi theo quyền của tài khoản agent (AC-30, AC-31). Tên công cụ hiện có trong code, ghi để đối chiếu, không phải quyết định: `api_list_records`, `api_get_record`, `api_create_record`, `api_update_record`.
19. **Ô "Toàn quyền (khẩn cấp)":** mặc định tắt; khi bật mở thêm xóa, submit/hủy, gọi hàm whitelist (`api_delete_record`, `api_submit_record`, `api_call_method`) và gỡ giới hạn (AC-32, AC-33). Nhật ký theo AC-34, AC-35.

**Ngoài (thêm):** hoàn tác một lần bấm trong comment; hẹn giờ tự tắt Toàn quyền; bỏ hộp xác nhận ở form Desk; duyệt hàng loạt; cho bot bấm liên kết của chính nó.

### N-4 Dữ liệu
- Một ô "Toàn quyền (khẩn cấp)" trên cấu hình agent: mặc định tắt, mô tả nêu rõ nó bỏ gì. Chỉ người sửa được cấu hình agent đặt được; bot không đọc, không sửa (AC-33).
- Ô "Cho phép sửa code và lệnh bench" đổi nghĩa: nay cũng mở công cụ bản ghi (A-24). Mô tả của ô đã đổi theo (`6d90e79`).
- Không thực thể mới. Liên kết Duyệt / Từ chối là chuỗi có chữ ký sinh từ mã đề xuất và hành động, không lưu thêm gì.
- Nhật ký: cột hành động của nhật ký lần chạy nhận thêm mục cho từng lời gọi công cụ bản ghi; bước "đề xuất" của đề xuất được ghi bằng tài khoản agent (`6d90e79`). Giá trị trước/sau chưa có (AC-35).

### N-5 Giao diện / tích hợp
- **Comment của bot trên phiếu** (do công cụ tự đăng, không phải model viết): mã đề xuất, loại, đích (file hoặc lệnh), nhánh nhận commit, nhánh remote đang theo và số commit đi trước (nếu theo), cảnh báo app lõi, ghi chú "cần bench restart" (file `.py`) hoặc "lệnh bench không hoàn tác được", rồi ba liên kết: **Duyệt**, **Từ chối**, **Xem nội dung thay đổi** (tới form có diff). Prompt dặn model không tự viết lại liên kết duyệt.
- **Liên kết Duyệt / Từ chối:** mở bằng trình duyệt đang đăng nhập; chữ ký gắn với đúng một đề xuất và một hành động; kiểm vai trò và trạng thái ở server như nút trên form; xong thì chuyển về trang phiếu; từ chối hoặc lỗi thì hiện trang báo lý do, không đổi gì.
- **Form Desk:** giữ ba nút, giữ hộp xác nhận, giữ nút Hoàn tác (handoff §5).
- **Cấp công cụ:** một bảng cấp có thêm một dòng cho công cụ bản ghi; nhóm Toàn quyền cấp riêng (S-5, AC-2).
- **Các quyết định kiến trúc bị chạm:** ADR-005 QĐ 3; ADR-011 QĐ 2 và 6; ADR-012 QĐ 4 và 7 (handoff §3 mục 5; journal CHG-001 2026-11-14 nêu thêm ADR-012). Phán quyết do architect, song song với amendment này.

### N-6 NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 [changed] | Xem dòng NFR-1 ở trên: chỉ áp cho đề xuất code và lệnh. | Test AC-3, AC-8 như cũ |
| NFR-10 | Từ comment tới áp dụng chỉ cần 1 lần mở liên kết và 0 hộp xác nhận; mỗi liên kết chỉ làm đổi trạng thái đề xuất đúng một lần | Test AC-25: một lời gọi đường liên kết dưới người có vai trò → trạng thái "Đã duyệt", đúng 1 job áp dụng được xếp hàng; lời gọi thứ hai → 0 job mới |
| NFR-11 | 100% lời gọi công cụ bản ghi (thành công, từ chối hoặc lỗi) có một mục trong cột hành động của nhật ký lần chạy | Test AC-34 đếm mục theo từng công cụ |

Không có NFR về thời gian phản hồi: không có số trong intake và chưa có số đo. Giới hạn job 600 s giữ nguyên.

### N-7 Tiêu chí nghiệm thu
**Bản có hiệu lực của tiêu chí đã sửa** (dòng gốc ở bảng chính được giữ và có dấu `[changed: Amd-2]`):

| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 [changed] | Cả hai ô tắt (mặc định: "Cho phép sửa code và lệnh bench" và "Toàn quyền (khẩn cấp)"): với 4 mức × có/không người ra lệnh, danh sách tên tool và prompt trùng hoàn toàn với bản nền (không tool đề xuất, không công cụ bản ghi, không khối "làm luôn"). Prompt vẫn chứa câu "Không sửa file trong apps/". | Test ma trận 4 mức × 2 ô × có/không người ra lệnh = 32 tổ hợp: 8 tổ hợp "cả hai tắt" khớp bản nền; 24 tổ hợp còn lại khớp bảng cấp của AC-2. Test grep chuỗi trong prompt |
| AC-2 [changed] | Ba đường cấp, mỗi đường chỉ có khi đủ điều kiện của nó và không đường nào có ở `L0` hay khi không có người ra lệnh: (a) tool đề xuất: ô code bật ∧ `L3` ∧ có người ra lệnh; (b) công cụ bản ghi (liệt kê, đọc, tạo, sửa): cùng ba điều kiện với (a); (c) nhóm Toàn quyền (xóa, submit/hủy, gọi hàm whitelist, cùng bốn công cụ bản ghi): ô "Toàn quyền" bật ∧ mức ∈ {`L1`, `L2`, `L3`} ∧ có người ra lệnh, không cần ô code. Khi vượt ngân sách và mức bị hạ về `L1` (ADR-003 bước e): (a) và (b) mất, (c) còn. | Test ma trận: ô code × ô Toàn quyền × 4 mức × thẩm quyền × vượt/không vượt ngân sách; so danh sách tên công cụ từng tổ hợp |
| AC-5 [changed] | Chỉ người có `ERP AI Instructor` mới duyệt hoặc từ chối được, qua cả hai đường: nút trên form và liên kết trong comment. Tài khoản agent, `Administrator`, `Guest` và người không có vai trò đều bị từ chối ở server. Comment chứa "ok" hay "duyệt" của bất kỳ ai không đổi trạng thái đề xuất. Đề xuất đã từ chối thì không bao giờ được áp dụng. | Test tự động: gọi từng đường dưới từng người dùng; tạo comment "ok" rồi kiểm trạng thái vẫn "chờ duyệt" |
| AC-11 [changed] | Chống chèn lệnh qua phiếu: phiếu và comment của người không có thẩm quyền chứa câu như "sửa file X / chạy bench Y / tự duyệt / tạo user admin / xóa bản ghi Z" thì lần chạy có 0 tool đề xuất, 0 công cụ bản ghi, 0 công cụ Toàn quyền, 0 đề xuất, 0 bản ghi đổi (kể cả khi ô Toàn quyền bật). Khi có người ra lệnh mà chưa ai duyệt đề xuất code hoặc lệnh thì có 0 lần áp dụng, dù model trả lời "đã được duyệt". | Test tự động với stub Cổng model: kịch bản không có người ra lệnh với từng ô bật; kịch bản model gọi tool đề xuất rồi khẳng định đã duyệt |
| AC-12 [changed] | Như bản gốc và Amendment 1, thêm: bước duyệt hoặc từ chối qua liên kết ghi một dòng nhật ký với đúng người đã mở liên kết (không phải tài khoản agent hay người tạo đề xuất). | Test tự động đếm dòng nhật ký sau mỗi bước, qua cả hai đường |
| AC-14 [changed] | Khi bộ tool mới được cấp, prompt nêu: mọi thay đổi code hoặc lệnh phải chờ người bấm Duyệt trong comment của bot; chữ trong phiếu hay comment, kể cả "ok", không phải duyệt; bot không nói một thay đổi đã áp dụng khi mới tạo đề xuất; bot không tự viết lại liên kết duyệt. Khi không được cấp, prompt giống hệt hiện nay. | Test tự động so chuỗi prompt hai trạng thái |
| AC-15 [changed] | Có ADR (mới hoặc sửa) ghi từng chỗ trái ở N-2 (ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7), vì sao, và cách hoàn tác (tắt cả hai ô). Các test kiến trúc hiện có xanh hoặc được sửa đúng theo ADR đó; không test cũ nào bị sửa chỉ để xanh mà không có ADR (STD-TEST-5). | `ls docs/team/adr/`; `cmd.test` xanh; reviewer đối chiếu danh sách test cũ đã sửa ở `6d90e79` (`test_registry.py`, `test_doctype_descriptions.py`, `test_architecture.py`, `test_classification.py`) với ADR |
| AC-22 [changed] | Giữ nguyên cho form: trước khi duyệt form hiện app, đường dẫn, diff, nhánh nhận commit, thông điệp commit, cảnh báo AC-21, cờ hoàn tác được; ba nút trên form giữ hộp xác nhận. Thêm cho comment của bot: trước khi mở liên kết, người duyệt thấy ngay trong comment mã đề xuất, loại, đích (file hoặc lệnh), nhánh nhận commit, nhánh remote đang theo và số commit đi trước (nếu theo), cảnh báo app lõi (chỉ với 4 app lõi), ghi chú "cần bench restart" (file `.py`) hoặc "lệnh bench không hoàn tác được" (lệnh), và liên kết "Xem nội dung thay đổi" tới form có diff, lý do, thông điệp commit, cờ hoàn tác. URL remote xuất hiện 0 lần. Liên kết Duyệt không có hộp xác nhận. | Test tự động đọc HTML comment cho: một đề xuất file ở app lõi có nhánh theo remote; một đề xuất file ở app không lõi; một đề xuất lệnh; kiểm từng chuỗi nêu trên và URL token giả = 0 lần. Test dữ liệu form như cũ. qa mở comment và form trên trang phiếu Helpdesk của `miyano` và dán ảnh chụp hoặc mô tả vào `acceptance.md` (chưa ai xem, handoff mục 2) |

**Tiêu chí mới (AC-24..AC-35).** Cột "Mã nhận về" ghi tình trạng của code đã commit để reviewer và tech-lead biết chỗ nào đã có, chỗ nào còn thiếu; nó không thay cho kiểm tra.

| Mã | Tiêu chí (đo được) | Cách kiểm | Mã nhận về |
|---|---|---|---|
| AC-24 | Sau khi công cụ đề xuất tạo thành công một đề xuất, trên phiếu có đúng 1 comment mới của bot với ba liên kết: Duyệt, Từ chối, Xem nội dung thay đổi. Hai liên kết quyết định mang chữ ký gắn với đúng đề xuất và đúng hành động: đổi mã đề xuất hoặc đổi "từ chối" thành "duyệt" thì chữ ký không còn khớp. Phần chữ do model viết không nằm trong liên kết và không chứa liên kết quyết định nào. | Test tự động đọc HTML comment sau mỗi công cụ đề xuất (3 công cụ); sinh liên kết rồi đổi từng phần → chữ ký sai | Có (`change_link.py`, `propose_change._comment`; test `test_change_link`, `test_propose_change`) |
| AC-25 | Người có `ERP AI Instructor` đang đăng nhập mở liên kết Duyệt của một đề xuất "Chờ duyệt": trạng thái thành "Đã duyệt", đúng 1 job áp dụng được xếp hàng, trình duyệt được chuyển về trang phiếu của đề xuất, và không có hộp xác nhận nào ở đường này. Mở liên kết Từ chối: "Đã từ chối", 0 job, 0 byte ghi, 0 commit, 0 lệnh chạy. Mở lại một trong hai liên kết sau đó: trạng thái không đổi, 0 job mới, trang báo trạng thái hiện tại. | Test tự động gọi đường liên kết dưới người có vai trò (tiếp tục NFR-10); qa mở liên kết bằng trình duyệt thật trên `miyano` và dán mô tả hoặc ảnh chụp vào `acceptance.md` | Có (`change_decision.py`; test `test_change_decision`); chưa mở qua HTTP thật |
| AC-26 | Liên kết bị từ chối, trạng thái đề xuất không đổi, 0 job, trang báo "không hợp lệ" hoặc lý do từ chối, khi: chữ ký thiếu hoặc sai; chữ ký của đề xuất khác; hành động khác duyệt/từ chối; người dùng là `Guest`, `Administrator`, tài khoản agent, hoặc người không có `ERP AI Instructor` (kể cả người được giao phiếu và người tạo phiếu); đề xuất không còn "Chờ duyệt". Đường liên kết chỉ nhận GET và không bao giờ cho `Guest`. | Test tự động, mỗi nhánh một test | Có (`test_change_decision`) |
| AC-27 | Duyệt qua liên kết không bỏ qua kiểm tra nào lúc áp dụng: sau khi mở liên kết Duyệt, nếu ô code đã tắt, hoặc file đích đã đổi, hoặc nội dung đề xuất không còn khớp dấu lúc duyệt, hoặc nhánh đang checkout đã đổi, hoặc app đã bị rút khỏi danh sách, thì 0 byte ghi, 0 commit, 0 lệnh chạy, trạng thái "Lỗi" hoặc "Hết hiệu lực" kèm lý do, có dòng nhật ký (như AC-6, AC-9, AC-18). | Test tự động: từng điều kiện trên, kích hoạt bằng đường liên kết | Một phần: `apply_job` kiểm công tắc, dấu nội dung và bộ chặn (`test_apply_job`); chưa có test kích hoạt từ đường liên kết |
| AC-28 | Sau mỗi lần áp dụng, lỗi, hết hiệu lực hoặc hoàn tác của một đề xuất, có 1 comment mới trên phiếu của đề xuất nói trạng thái cuối; với thay đổi code thành công có mã commit; với lệnh có mã thoát; với lỗi có lý do. Comment không chứa URL remote, khóa hay token. | Test tự động chạy job áp dụng trên repo tạm và đếm comment sau từng kết cục; gieo token giả, đếm chuỗi = 0 | Chưa có (handoff §4) |
| AC-29 | Khi bất kỳ nhóm công cụ nào (đề xuất, bản ghi, Toàn quyền) được cấp, prompt có khối "làm luôn": làm ngay trong lượt; không hỏi lại, không chờ "ok"; thiếu đúng một thông tin bắt buộc không tra được thì hỏi một câu; "Cần ai quyết" chỉ khi công cụ trả `ok=false` hoặc việc ngoài công cụ. Khối đó đứng sau các khối nhóm công cụ. Khi không nhóm nào được cấp, prompt trùng bản nền (AC-1). Phép đo hành vi (sau G4): trong 3 phiếu kịch bản có đủ thông tin, số lần bot hỏi lại người ra lệnh trước khi làm = 0. | Test tự động so chuỗi prompt cho từng tổ hợp nhóm; sau G4 người chạy 3 phiếu thật trên `miyano` với model thật, đếm comment của bot chứa câu hỏi cho người ra lệnh trước khi có hành động, dán vào `acceptance.md` | Có phần prompt (`ACT_NOW_BLOCK`; `test_classification`); chưa thử với model thật |
| AC-30 | Công cụ bản ghi (chế độ thường): tạo, sửa, đọc, liệt kê bản ghi chạy dưới tài khoản agent theo phân quyền Frappe. Thành công → `ok=true` nêu DocType và tên bản ghi. Thiếu quyền, hoặc hệ thống từ chối → `ok=false` có lý do ngắn, 0 bản ghi đổi (không để lại nửa chừng). Không đổi tên bản ghi; không sửa chứng từ đã submit hoặc hủy; trường mật khẩu và khóa không bao giờ được ghi hay đọc. | Test tự động với một người dùng agent thử: tạo và sửa một bản ghi nháp; một người dùng thiếu quyền → `ok=false`, so bản ghi trước/sau; một chứng từ đã submit → `ok=false` | Có (`site_api.py`; `test_site_api`) |
| AC-31 | Chế độ thường vẫn bị từ chối (`ok=false`, 0 bản ghi đổi): gán `System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest` hay `All`, kể cả qua Role Profile; sửa `Administrator`, `Guest`, tài khoản agent; ghi Role Permission, Custom DocPerm; ghi các DocType nằm trong danh sách đóng đọc của app (cấu hình, khóa, nhật ký, giao dịch nhạy cảm như Salary Slip); xóa, submit hay hủy (không có công cụ); Server Script và Webhook luôn được lưu ở trạng thái tắt dù model yêu cầu bật. | Test tự động, mỗi nhánh một test | Có (`test_site_api`). Không còn trong chế độ thường, theo N-2 S-4: danh sách vai trò được gán, chặn vai trò có quyền sửa User, chỉ-thêm-vai-trò |
| AC-32 | Ô "Toàn quyền (khẩn cấp)": mặc định 0; chỉ người sửa được cấu hình agent đặt được. Khi 0, hành vi theo AC-1 và AC-2. Khi 1, ở `L1`, `L2`, `L3` có người ra lệnh, bot có thêm xóa bản ghi, submit/hủy chứng từ và gọi hàm whitelist, và các giới hạn vai trò, tài khoản, DocType của AC-31 không còn, trừ danh sách ở AC-33. Mỗi lời gọi vẫn chạy dưới tài khoản agent theo phân quyền Frappe. | Test tự động: giá trị mặc định; quyền sửa ô (người không có quyền → lỗi quyền); từng công cụ Toàn quyền trên một bản ghi thử; gán một vai trò bị cấm ở chế độ thường thành công khi bật; ma trận cấp ở AC-2 | Có (`registry.py`, `policy.py`, `site_api.py`, `erp_ai_setting.json`; `test_site_api`, `test_registry`, `test_policy`) |
| AC-33 | Ở mọi chế độ kể cả Toàn quyền, bị từ chối (`ok=false`, 0 thay đổi): ghi hay đọc ERP AI Setting, ERP AI Credential, ERP AI Log, ERP AI Change Proposal; trường mật khẩu và khóa API của người dùng; gọi hàm có tên thuộc app `erp_ai` (gồm hàm nhận quyết định từ liên kết duyệt); gọi hàm mà tham số nhắc tới tên của bốn DocType trên. Vì vậy bot không tự bật ô của mình và không tự duyệt đề xuất của mình. | Test tự động, mỗi nhánh một test, trong chế độ Toàn quyền bật; thử cụ thể gọi hàm quyết định với liên kết hợp lệ do chính bot đọc được → bị từ chối | Có (`test_site_api`). Cách chặn là so khớp chuỗi, chưa có test cho cách viết khác của tên DocType (reviewer soát, handoff §3 mục 2) |
| AC-34 | Mỗi lời gọi công cụ bản ghi hoặc Toàn quyền, kể cả bị từ chối hoặc sập, có đúng 1 mục trong cột hành động của nhật ký lần chạy, gồm công cụ, DocType, tên bản ghi (nếu có) và kết quả đúng/sai; bước "đề xuất" của mỗi đề xuất tạo thành công được ghi bằng tài khoản agent. | Test tự động qua runner với Cổng model giả: đếm mục theo công cụ và theo kết quả | Có (`runner.py`; `test_agent_runner`) |
| AC-35 | Mỗi lần công cụ bản ghi hoặc Toàn quyền ghi, xóa, submit/hủy hoặc gọi hàm thành công, nhật ký có giá trị trước và giá trị sau của bản ghi bị chạm (trước rỗng khi tạo, sau rỗng khi xóa), người ra lệnh, và 0 byte mật khẩu hay khóa giả đã gieo. | Test tự động: một test cho mỗi công cụ ghi, so giá trị trước/sau trong nhật ký với bản ghi; gieo khóa giả, đếm = 0 (cùng cách NFR-5 của FEAT-001) | Chưa có: nhật ký chỉ có công cụ, DocType, tên, đúng/sai |

**Thứ tự bỏ khi khối lượng vượt cỡ L (A-26):** không AC nào do lệnh của người đặt ra (AC-24..AC-27, AC-29..AC-33) được bỏ. Hai AC do analyst thêm vì mã nhận về còn thiếu là AC-28 và AC-35; nếu phải bỏ thì bỏ AC-28 trước (phần hoàn tác trước, rồi phần áp dụng), sau đó AC-35. Bỏ AC-35 cần người đồng ý và kèm điều kiện: không bật "Toàn quyền" trên môi trường thật. Không bỏ AC-26, AC-27, AC-33.

### N-8 Assumptions decided by the team (amendment)
- **A-1' [changed, thay A-1]. Tạo User và sửa cấu hình nằm trong phạm vi, làm trực tiếp qua công cụ bản ghi.** chọn: bot tạo User, gán vai trò nghiệp vụ, sửa cấu hình và bản ghi nháp ngay khi người ra lệnh yêu cầu, không qua duyệt, theo N-2 S-3, S-4 | vì: người ra lệnh (handoff §1); mã đã có (`6d90e79`) | phương án khác: giữ ngoài phạm vi như A-1 và dùng FEAT-005 | sai thì: tắt ô "Cho phép sửa code và lệnh bench" (bot mất cả công cụ bản ghi và tool đề xuất cùng lúc, xem A-24).
- **A-2' [changed, bổ sung A-2]. Vai trò của chính tài khoản agent không đổi; quyền của nó là chốt cuối.** chọn: không cấp thêm vai trò cho tài khoản agent trong feature này; công cụ bản ghi chạy theo phân quyền của tài khoản đó; ở chế độ Toàn quyền bot được gán cho người khác, kể cả `System Manager`, khi người ra lệnh yêu cầu rõ | vì: ADR-006 vẫn đúng cho tài khoản agent; "full quyền" cho tài khoản bot là việc người đã làm ở Desk (intake FEAT-004 `:10`) | phương án khác: cấp quyền hẹp cho tài khoản agent qua thủ tục cài (hướng của FEAT-005) | sai thì: System Manager gỡ role thừa của tài khoản agent; công cụ bản ghi tự thu hẹp theo.
- **A-19 "Làm luôn" áp cho cả bản ghi và code.** chọn: việc bản ghi làm thẳng; việc code và lệnh `bench` tạo đề xuất ngay, không hỏi trước, và người bấm Duyệt trên phiếu | vì: handoff §5 ghi người đã trả lời "làm luôn áp cho cả bản ghi và code" | phương án khác: chỉ cho việc bot đã có quyền làm (phân loại, gán người, comment) | sai thì: sửa khối "làm luôn" và AC-29.
- **A-20 Một lần bấm chỉ ở liên kết trong comment.** chọn: bỏ hộp xác nhận chỉ ở liên kết; form Desk giữ hộp xác nhận cho Duyệt, Từ chối, Hoàn tác; Hoàn tác không có liên kết một lần bấm | vì: handoff §5 ("chỉ bỏ hộp xác nhận ở đường dẫn trong comment") | phương án khác: bỏ hộp xác nhận cả ở form; thêm liên kết hoàn tác | sai thì: sửa AC-22 và thêm một AC cho liên kết hoàn tác.
- **A-21 Luồng chữ "ok" của FEAT-005 bị thay.** chọn: không còn bước "ok" nào, kể cả khi bật Workflow, Notification, Assignment Rule; với bản ghi không có nút duyệt nào, nút chỉ có cho code và lệnh | vì: handoff §5 ("luồng chữ ok thay bằng nút") cộng handoff §1 ("không qua duyệt") và đúng như mã nhận về | phương án khác: nút duyệt cho cả bản ghi nhạy cảm (Workflow, Notification, Server Script) | sai thì: thêm danh sách việc phải duyệt, một AC và task; đây là việc cần người quyết nếu rủi ro ở N-2 S-3 không chấp nhận được.
- **A-22 Danh sách cấm giữ như mã nhận về.** chọn: danh sách ở AC-31 và AC-33, không thêm, không bớt | vì: handoff §5 ("danh sách cấm giữ như mục 3"); analyst không thiết kế lại | phương án khác: danh sách vai trò được gán và chặn vai trò có quyền sửa User (FEAT-005) | sai thì: thêm phần tử vào danh sách và một test ở AC-31.
- **A-23 Toàn quyền là công tắc tay, không hẹn giờ, không cảnh báo khi bật.** chọn: như mã nhận về; "xong thì tắt" là việc người (mô tả của ô) | vì: không có số nào về thời hạn trong lệnh của người; không tự đặt số | phương án khác: tự tắt sau N giờ; cảnh báo hằng ngày khi ô đang bật | sai thì: thêm một AC và một tác vụ nền; đây là hướng giảm rủi ro "quên tắt" ở N-2 S-6.
- **A-24 Một ô, hai nghĩa.** chọn: ô "Cho phép sửa code và lệnh bench" cùng mở công cụ bản ghi và tool đề xuất | vì: mã nhận về và mô tả ô đã đổi theo (`6d90e79`) | phương án khác: một ô riêng cho công cụ bản ghi | sai thì: thêm ô, một dòng ở bảng cấp và đổi AC-1, AC-2. Cảnh báo: site `miyano` đang bật ô này ở `L3` nên công cụ bản ghi đang chạy ở dev.
- **A-25 Liên kết ký không hết hạn và không gắn với người.** chọn: như mã nhận về; chữ ký gắn với đề xuất và hành động, hiệu lực chấm dứt khi đề xuất rời "Chờ duyệt" | vì: không có yêu cầu hạn dùng trong lệnh của người; không tự đặt số | phương án khác: hạn dùng N giờ; gắn chữ ký với người nhận | sai thì: thêm điều kiện vào chữ ký và một test ở AC-26.
- **A-26 Mã nhận về là hiện trạng, chỗ thiếu thành việc của plan.** chọn: AC-27 (phần đường liên kết), AC-28, AC-35 là chỗ mã chưa đạt; tech-lead chèn task ở `plan --insert` | vì: handoff §4 liệt kê chỗ thiếu; analyst không viết code hay kế hoạch | phương án khác: bỏ ba AC này | sai thì: team-leader chọn lại theo thứ tự bỏ ở N-7.
- **A-27 Hai việc phải qua người trước khi bật trên môi trường thật.** chọn: AC-35 đạt (hoặc người đồng ý bỏ và không bật Toàn quyền) và ô "Toàn quyền" tắt khi deploy | vì: S-6, S-7 ở N-2; G5 vẫn cần người duyệt | phương án khác: không điều kiện | sai thì: bỏ dòng này ở DoD sau G4.

### N-9 Hệ quả cho FEAT-005 (0/52 task, chưa build)

Đọc spec FEAT-005 (kèm Amendment 1) đối chiếu với mã nhận về. "Đạt" nghĩa là hành vi có trong mã đã đọc, chưa chắc có test đúng chữ của AC. FEAT-005 hiện có `Approved-by` trống và plan 52 task chưa task nào được tích.

| AC của FEAT-005 | Kết luận | Căn cứ |
|---|---|---|
| AC-1 (bản nền không đổi) | Mâu thuẫn một phần | Bản nền đã đổi (tool đề xuất, công cụ bản ghi, Toàn quyền); ảnh chụp bản nền ở T1 phải chụp lại theo AC-1 mới của FEAT-004 |
| AC-2 (`L2` nhóm cấu hình, `L3` thêm nhóm tài khoản) | Mâu thuẫn | `L2` không có nhóm nào; công cụ bản ghi cấp ở `L3` cùng ô code; không có nhóm tách theo `L2`/`L3` |
| AC-3 (tạo User, 2 vai trò, không mật khẩu, nhật ký trước/sau, nêu cách hoàn tác) | Đạt một phần | Tạo User không đặt mật khẩu: đạt. Thiếu: danh sách vai trò được gán, giá trị trước/sau (AC-35), cách hoàn tác trong kết quả công cụ |
| AC-4 (từ chối gán vai trò) | Đạt một phần | 6 vai trò cấm cứng và Role Profile: đạt; email sai hoặc đã có: hệ thống Frappe từ chối (chưa có test riêng đúng ca). Thiếu: vai trò ngoài danh sách, vai trò có quyền sửa User hoặc DocType phân quyền, Custom Field, Property Setter, System Settings |
| AC-5 (thêm vai trò, vai trò cũ còn nguyên, từ chối các đích) | Mâu thuẫn một phần | Chặn `Administrator`, `Guest`, tài khoản agent; không chặn người ra lệnh và người có vai trò cấm; sửa User thay toàn bộ dòng vai trò nên không còn "chỉ thêm" |
| AC-6 (danh sách vai trò được gán) | Mâu thuẫn | Không có danh sách này trong mã nhận về |
| AC-7 (Custom Field, chặn khóa phân quyền) | Mâu thuẫn | Custom Field tạo qua công cụ chung, không chặn `permlevel`, `ignore_user_permissions`, `reqd`, `fetch_from`… |
| AC-8 (Property Setter chỉ property vô hại) | Mâu thuẫn | Không giới hạn property |
| AC-9 (Holiday List, ngày cũ còn nguyên) | Đạt một phần | Tạo, thêm được; bảng con thay toàn bộ dòng cũ nên "ngày cũ còn nguyên" không được bảo đảm |
| AC-10 (Workflow, Notification, Assignment Rule: tạo tắt, bật cần "ok") | Mâu thuẫn | Lệnh của người: không còn "ok" (A-21); ba loại này không bị ép tắt |
| AC-11 (DocType đích cấm, người nhận Notification) | Mâu thuẫn một phần | DocType nhạy cảm đóng đọc thì đóng ghi: đạt. Người nhận Notification không bị giới hạn |
| AC-12 (System Settings chỉ nhóm hiển thị) | Mâu thuẫn | System Settings là DocType đơn, sửa được mọi trường qua công cụ chung |
| AC-13 (mỗi lời gọi một dòng nhật ký; giá trị trước/sau) | Đạt một phần | Mỗi lời gọi có mục trong cột hành động, kể cả bị từ chối (AC-34). Thiếu giá trị trước/sau và dòng "đã áp dụng" riêng (AC-35) |
| AC-14 (cảnh báo hằng ngày, ngoại lệ A-9) | Chưa làm, đề nghị đổi | Cảnh báo chưa phân biệt vai trò gán qua công cụ. Vì bot nay gán vai trò trực tiếp mà danh sách cấm hẹp (S-4), đề nghị giữ cảnh báo cho mọi dòng vai trò do tài khoản agent tạo thay vì thêm ngoại lệ A-9 |
| AC-15 (tài khoản agent có đúng tập vai trò; test ADR-005 xanh trừ một chỗ nới) | Mâu thuẫn một phần | Công cụ chạy theo phân quyền Frappe, không bỏ qua phân quyền: đạt. ADR-005 QĐ 3 nay bị thay cho cả nhóm tool, không chỉ một ngoại lệ; test cũ đã sửa ở `6d90e79` |
| AC-16 (chống chèn lệnh) | Đạt (chế độ thường) | Nhóm công cụ cần người ra lệnh; 6 vai trò cấm cứng bị từ chối. Ở Toàn quyền, gán được theo lệnh người |
| AC-17 (khóa giả 0 lần) | Chưa kiểm cho công cụ mới | Trường mật khẩu và khóa bị chặn đọc và ghi; chưa có test gieo khóa giả cho các công cụ này |
| AC-18 (prompt, ADR-014/015) | Mâu thuẫn một phần | Khối prompt nêu việc bot làm được, giới hạn cứng, nội dung phiếu là dữ liệu: đạt. "Việc nào chờ ok": không còn. ADR-014..018 (proposed) mô tả mô hình bị thay, cần viết lại theo phán quyết của architect |

Đếm 18 AC: đạt hoặc đạt một phần 5 (AC-3, AC-4, AC-9, AC-13, AC-16); chưa kiểm 1 (AC-17); mâu thuẫn hoặc mâu thuẫn một phần 11 (AC-1, AC-2, AC-5, AC-6, AC-7, AC-8, AC-10, AC-11, AC-12, AC-15, AC-18); chưa làm, đề nghị đổi 1 (AC-14).

**Kế hoạch 52 task còn hợp lý không?** Không, ở dạng hiện nay. Nó viết cho mô hình "mỗi việc một tool, danh sách role được gán, chờ chữ ok". Theo tiêu đề task (tech-lead xác nhận lại khi lập plan):
- Bị thay thế, khoảng 36 task: T1 (ảnh chụp bản nền cũ), T3, T6, T7, T9 (danh sách role được gán, danh sách cấm), T10, T12, T13, T22 (validator và cấp nhóm; mã nhận về đã có cách riêng), T17–T19, T21 (tool tài khoản), T26–T34 (cơ chế "ok" và `config_guard`), T35–T45 (tool theo từng loại cấu hình), T46, T49, T50 (luật kiến trúc cho ADR-014..018).
- Tùy quyết định, 2 task: T14, T15 (cài quyền hẹp cho tài khoản agent): chỉ cần nếu người muốn thu hẹp quyền tài khoản agent thay vì để "full quyền".
- Còn dùng được, khoảng 14 task, xoay quanh nhật ký trước/sau và cảnh báo (AC-35, AC-14 đổi): T2, T4, T5, T8, T11, T16, T20, T23, T24, T25, T47, T48, T51, T52.

**Đề nghị cho team-leader hỏi người (A-28, decide mode nên chỉ ghi, không chặn):** đóng FEAT-005 phần "tool theo từng việc" là đã được thay bởi CHG-001 (Amendment 2 này) và FEAT-004; nếu người muốn giữ nhật ký trước/sau và cảnh báo hằng ngày thì mở một feature nhỏ từ khoảng 14 task còn lại, hoặc đưa AC-35 vào plan của FEAT-004. Không ai mất code vì FEAT-005 chưa build. Analyst không sửa spec FEAT-005 (ngoài quyền của việc này). **[added: Amd-2 A-28: chọn: đề nghị trên | vì: 12 trên 18 AC mâu thuẫn hoặc chưa làm, 36 trên 52 task bị thay | phương án khác: giữ FEAT-005 và chỉnh spec cho khớp mã nhận về | sai thì: team-leader chạy `analyze --amend` cho FEAT-005 với danh sách mâu thuẫn ở bảng trên]**

Ghi thêm cho chủ FEAT-006: AC-9 (không tool nào nhận tên người, SLA, ưu tiên làm tham số) không còn đúng với nhóm công cụ bản ghi (N-2 S-5); phép thử tĩnh cần ngoại lệ có ADR. Analyst không sửa spec FEAT-006.

### N-10 Tài liệu phía sau bị ảnh hưởng, khối lượng
- `arch-impact.md` và ADR: phán quyết của architect cho ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7 (journal CHG-001 2026-11-14), ADR-014..018 của FEAT-005.
- `design.md` của FEAT-004: thêm phần liên kết ký, công cụ bản ghi, Toàn quyền (chưa có trong design; `propose_change.py` cũng không theo từng chữ của design 3.x, handoff §4); §3.9 (mẫu comment) có thêm ba liên kết.
- `plan.md`, `tasks.md` của FEAT-004: `plan --insert` cho AC-27 (phần liên kết), AC-28, AC-35; luật kiến trúc mới cho `apply_job.py`, `propose_change.py`, `site_api.py`, `change_decision.py` (T31, T32, T44 chưa làm, handoff §4); test chéo T48 (hook git không chạy, ref remote không đổi, metadata sạch). Task có thể đã bị thay: T18, T19, T25 (journal CHG-001 2026-11-13) cần đối chiếu.
- Review: reviewer chấm các file nhận về chưa từng được review (handoff §3: `change_decision.decide` GET đổi trạng thái; `site_api.call_method`; danh sách cấm của `site_api`; thứ tự trả file trong `apply_job`).
- `FEAT-005`, `FEAT-006`: xem N-9.
- **Khối lượng (bước 9):** FEAT-004 từ 23 lên 35 AC (+12), phần lớn đã có code. Giữ cỡ L. Nếu plan vượt `max_agents_per_feature` của cỡ L (10), đề xuất cho team-leader tách AC-30..AC-35 (công cụ bản ghi và Toàn quyền) thành một feature mới nhận code `6d90e79`, và FEAT-004 giữ AC-1..AC-29. Analyst không tự đổi cỡ.

## Definition of Done
**Phần build (trước G4):**
- [ ] Mọi AC-1..AC-15 đạt, đầu ra được dán trong `acceptance.md` **[changed: Amd-1 — AC-1..AC-23]** **[changed: Amd-2 — AC-1..AC-35]**
- [ ] Có ADR mới cho các phần ADR-005 (ADR-003/004 nếu cần) bị thay, có cách hoàn tác **[changed: Amd-1 — thêm sửa ADR-013 QĐ 6 (commit local) và các điểm O-1..O-7]** **[changed: Amd-2 — thêm các chỗ trái ở N-2 (ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7); cách hoàn tác là tắt hai ô]**
- [ ] Mỗi AC có ít nhất 1 test tự động (STD-TEST-2); không skip/xfail (STD-TEST-4)
- [ ] `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`) xanh; `cmd.lint` sạch **[changed: Amd-2 — lần chạy cả app gần nhất mất khoảng 558 s và còn 5 lỗi do test đọc cài đặt đang lưu của site (`auto_assign_enabled=1`): 3 ở `test_agent_runner.TestRunnerL1Classification`, 2 ở `test_runner_routing` (handoff mục 2). Giới hạn 580 s không đủ cho một lần chạy; người dùng lệnh chọn giới hạn lớn hơn. Cần cả app xanh, không đổi test cho khớp site (STD-TEST-5)]**
- [ ] Diff không chạm `protected_paths`, không chứa bí mật
- [ ] CI xanh
- [ ] **[added: Amd-1]** NFR-7..NFR-9 đạt; NFR-9 có đầu ra so HEAD và trạng thái working tree của `frappe`, `erpnext`, `helpdesk`, `hrms` trước/sau `cmd.test`, dán trong `acceptance.md`
- [ ] **[added: Amd-1]** Mọi test git chạy trên repo tạm; luật kiến trúc AC-23 xanh
- [ ] **[added: Amd-2]** NFR-10, NFR-11 đạt; AC-24..AC-35 đạt (AC-28, AC-35 là chỗ mã nhận về còn thiếu, hoặc người đồng ý bỏ theo thứ tự ở N-7)
- [ ] **[added: Amd-2]** reviewer đã chấm các file nhận về chưa từng được review (`change_link.py`, `change_decision.py`, `propose_change.py`, `site_api.py`, `apply_job.py`, phần mới của `runner.py`, `registry.py`, `prompts.py`) theo Review checklist, và các điểm handoff §3 mục 1–4 đều có kết luận
- [ ] **[added: Amd-2]** luật kiến trúc mới cho `apply_job.py`, `propose_change.py`, `site_api.py`, `change_decision.py` và test chéo T48 xanh (handoff §4)

**Sau G4 (`/team:asbuilt`, người làm phần đo thực tế):**
- [ ] As-Built viết xong (`asbuilt.md`)
- [ ] README/tài liệu người dùng: cách bật công tắc, chọn app, duyệt, hoàn tác, danh sách lệnh **[changed: Amd-1 — thêm: thêm app lõi vào danh sách và rủi ro; commit bot tạo trông thế nào; hoàn tác bằng commit; cách tự đẩy lên fork; làm gì trước và khi `bench update`]** **[changed: Amd-2 — thêm: hai ô công tắc và ô nào mở gì; liên kết Duyệt / Từ chối trên phiếu và ai mở được; bot làm luôn không hỏi lại; danh sách "Quy tắc an toàn đã đổi" (N-2); khi nào bật Toàn quyền và phải tắt ngay sau đó]**
- [ ] Mục CHANGELOG
- [ ] Người chạy thử một vòng đề xuất → duyệt → áp dụng → hoàn tác trên môi trường thật trước khi bật lâu dài (Success); lên prod cần G5 **[changed: Amd-1 — vòng thử trên 1 app lõi ở site dev, có commit áp dụng và commit hoàn tác; người tự đẩy lên fork cho CI]** **[changed: Amd-2 — vòng thử duyệt bằng một lần mở liên kết trên trang phiếu Helpdesk thật, có comment kết quả (AC-25, AC-28)]**
- [ ] **[added: Amd-2]** Người chạy 3 phiếu kịch bản với model thật trên `miyano`, số lần bot hỏi lại trước khi làm = 0 (AC-29), dán vào `acceptance.md`
- [ ] **[added: Amd-2]** Người bật "Toàn quyền" một lần trên dev, làm một việc xóa hoặc submit thử rồi tắt; mục nhật ký ghi việc đó (AC-34)
- [ ] **[added: Amd-2]** Trước khi deploy: ô "Toàn quyền" tắt trên môi trường đích, và AC-35 đã đạt hoặc người đồng ý bằng văn bản (A-27); lên prod cần G5
