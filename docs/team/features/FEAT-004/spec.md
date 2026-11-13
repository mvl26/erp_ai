Feature: FEAT-004
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec FEAT-004 — Cho bot quyền sửa code và chạy lệnh bench, có người duyệt từng thay đổi

Mode: decide (intake `:15`), nên không có `questions.md`. Mọi điểm lớn nằm ở mục Assumptions, đủ 4 trường. Cỡ L, playbook new-feature, cổng G5 (`team.py status FEAT-004`).

> **Amendment 1 (2026-11-12, `--amend --decide`, G1 tắt):** sửa được code app lõi và mỗi thay đổi đã áp dụng thành đúng một commit git local. Văn bản gốc được giữ nguyên. Dòng nào bị đổi có dấu **[changed: Amd-1 …]**, dòng mới có dấu **[added: Amd-1]**. Nội dung mới nằm ở mục "Amendment 1" phía dưới.

## Mục tiêu
**Giả thuyết (độ tin cậy 70%):** người yêu cầu muốn bot đề xuất được thay đổi code trong các app của bench và đề xuất được lệnh `bench`. Mỗi thay đổi chỉ được áp dụng sau khi một người có thẩm quyền xem đúng nội dung đó và bấm duyệt. Thay đổi đã áp dụng hoàn tác được, và mọi bước đều có trong nhật ký. Nội dung phiếu không bao giờ tự kích hoạt hay tự duyệt được thay đổi. **[changed: Amd-1 M-1]**

Chưa tới 85% vì ba lẽ:
1. Câu gốc nêu cả "tạo 1 user" và "sửa cài đặt hệ thống" (intake `:10`), nhưng người đã chốt "Thêm quyền sửa code và chạy lệnh". Đội hiểu là tạo User và sửa cấu hình qua DocType nằm ngoài phạm vi (A-1).
2. Chưa biết người muốn bot sửa những app nào (A-3). **[changed: Amd-1 M-1, đã có câu trả lời: app lõi]**
3. Chưa có số đo thời gian chạy `bench migrate`/`bench build` trên site `miyano`, nên giới hạn thời gian lệnh dựa vào con số 600 s có sẵn (A-8).

| Mục | Nội dung |
|---|---|
| Outcome | Một người có vai trò `ERP AI Instructor` nhờ bot sửa lỗi code trên phiếu. Bot đưa ra đề xuất có diff đầy đủ (hoặc một lệnh `bench` cụ thể), người đó duyệt, và hệ thống áp dụng đúng nội dung đã duyệt. Trước khi được duyệt thì không có byte nào trên đĩa đổi và không có lệnh nào chạy. |
| Users | Người ra lệnh/duyệt: người có vai trò `ERP AI Instructor` (Hiếu, Việt, Tiến theo bảng routing `erp_ai/agent/prompts.py:139-141`). System Manager bật/tắt khả năng này và chọn app được sửa. Người tạo phiếu là nguồn dữ liệu không tin cậy. |
| Why now | Người đã cấp full quyền cho tài khoản bot mà bot "chả làm được gì" (intake `:10`). Rào cản thật nằm ở bộ tool, prompt và policy, không nằm ở quyền của tài khoản: bot chỉ có 4 tool ghi phiếu (`erp_ai/agent/tools/write_ticket.py:116-164`), prompt cấm sửa `apps/` (`erp_ai/agent/prompts.py:98`), và lệnh ngoài duy nhất được phép là `git` chỉ đọc (ADR-005 Quyết định 5). |
| Success | Lúc build: AC-1..AC-15 đạt trên site dev `miyano`, `cmd.test` xanh. Sau G4 (việc của người): bật trên môi trường thật cho ≥ 1 app, cho bot xử lý 1 phiếu lỗi code từ đề xuất tới khi duyệt và áp dụng, rồi hoàn tác thử 1 lần. **[changed: Amd-1 M-3 — AC-1..AC-23; có thêm vòng thử trên 1 app lõi]** |
| Constraints | Không push, không deploy prod (G5 cần người duyệt). Không đổi role của tài khoản `ai.agent@miyano.com.vn` (A-2). Không đọc, không ghi `protected_paths` hay file bí mật. Tắt công tắc thì bot quay về đúng hành vi hiện tại. Chỉ commit local trên `team/FEAT-004*`. **[changed: Amd-1 M-3 — câu "chỉ commit local trên `team/FEAT-004*`" là quy tắc cho commit của đội; bot được tạo commit local trong repo app (A-4 mới), vẫn không push]** |
| Out of scope | Tạo User và gán Role. Tool cấu hình `L2`/`L3` của guide (Client Script, Property Setter, Workflow, Report…, guide `:240-251`). Bot tự duyệt hoặc tự áp dụng. Push, commit, đổi nhánh git. `bench restart`. Xóa file. Sửa chính app `erp_ai`. Chạy trên production trong feature này. **[changed: Amd-1 M-3 — bỏ chữ "commit"; thêm tạo nhánh, sửa lịch sử git]** |

## Người dùng
- **Người ra lệnh và người duyệt (vai trò `ERP AI Instructor`):** viết comment trên phiếu để nhờ bot. Họ đọc đề xuất (diff hoặc lệnh, lý do, cảnh báo hoàn tác được hay không) rồi duyệt hoặc từ chối. Với thay đổi code đã áp dụng, họ có thể bấm hoàn tác. Thẩm quyền xác định như hiện nay (`erp_ai/agent/authority.py:44-50`). `Administrator`, `Guest` và tài khoản agent không bao giờ có thẩm quyền (`authority.py:12`). **[changed: Amd-1 M-3 — họ thấy thêm nhánh nhận commit, cảnh báo app lõi và mã commit]**
- **System Manager:** bật hoặc tắt khả năng sửa code và chạy lệnh, chọn danh sách app bot được sửa. Mặc định là tắt và danh sách rỗng. **[changed: Amd-1 A-3 — được thêm cả app lõi `frappe`, `erpnext`, `helpdesk`, `hrms`]**
- **Người tạo phiếu, người comment không có thẩm quyền:** nội dung họ viết là dữ liệu (STD-SEC-5). Họ không làm bot có tool mới và không duyệt được gì.
- **Người tra cứu nhật ký (System Manager):** tra lại ai đề xuất gì, ai duyệt, đã áp dụng hay hoàn tác lúc nào, và lệnh trả về gì.
- **Người giữ repo app (lập trình viên của công ty) [added: Amd-1]:** đọc commit bot tạo, tự đẩy lên fork, mở PR, deploy, và tự xử lý khi `bench update`.

## Phạm vi
- **Trong:**
  1. **Đề xuất thay đổi code:** sửa nội dung một file đã có, hoặc tạo file mới, trong một app thuộc danh sách được phép. Mỗi đề xuất là một file (A-5). Đề xuất lưu đủ nội dung trước/sau và diff, chưa ghi gì xuống đĩa. **[changed: Amd-1 M-3 — app lõi được phép; đề xuất lưu thêm nhánh nhận commit và cảnh báo]**
  2. **Đề xuất lệnh `bench`:** chỉ lệnh trong danh sách cho phép (A-6), chỉ cho site đang chạy agent. Lưu lệnh dưới dạng chính xác từng đối số. Chưa chạy.
  3. **Duyệt hoặc từ chối:** người có thẩm quyền làm việc này qua một thao tác chủ ý, kiểm ở server. Mỗi lần duyệt gắn với đúng một đề xuất.
  4. **Áp dụng sau khi duyệt:** áp dụng đúng nội dung đã duyệt, không gọi lại model. Một đề xuất áp dụng nhiều nhất một lần. Đề xuất hết hiệu lực nếu file đích đã đổi kể từ lúc đề xuất. **[changed: Amd-1 M-3 mục 11 — áp dụng gồm ghi file và tạo đúng 1 commit local]**
  5. **Hoàn tác** một thay đổi code đã áp dụng bằng một thao tác. Lệnh `bench` không hoàn tác được, và điều này được ghi rõ trên đề xuất. **[changed: Amd-1 M-3 mục 12 — hoàn tác tạo một commit mới]**
  6. **Chặn đường dẫn và chặn lệnh:** từ chối từ lúc đề xuất và kiểm lại lúc áp dụng.
  7. **Nhật ký:** mỗi bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) có một dòng nhật ký.
  8. **Công tắc và danh sách app** trên cấu hình agent. Bộ tool mới chỉ được cấp khi công tắc bật, mức hiệu lực là `L3` và có người ra lệnh.
  9. **Prompt:** khi bộ tool mới không được cấp, lệnh cấm "Không sửa file trong apps/" giữ nguyên. Khi được cấp, prompt nói rõ mọi thay đổi phải chờ duyệt.
  10. **ADR mới:** ghi lại các phần của ADR-005 bị thay và cách hoàn tác (xem Giao diện / tích hợp).
  11.–14. **[added: Amd-1]** xem Amendment 1, M-3.
- **Ngoài (non-goals):**
  - Tạo User, gán Role, sửa phân quyền (Role Permission, Custom DocPerm, Has Role…), sửa cấu hình qua DocType. Phần này thuộc nhóm tool `L2`/`L3` của guide `:240-251` và cần một intake riêng (A-1).
  - Bot tự duyệt; duyệt bằng comment văn bản tự do; duyệt hàng loạt nhiều đề xuất một lần.
  - Commit, push, tạo hay đổi nhánh git trong repo của app (A-4). **[changed: Amd-1 M-3 — commit local nay nằm trong phạm vi; push, tạo/đổi nhánh, sửa lịch sử vẫn ngoài phạm vi]**
  - `bench restart`, `bench update`, cài/gỡ app, backup/restore, `execute`/`console`, đổi config site. Đầy đủ ở A-6.
  - Xóa hoặc đổi tên file; sửa file ngoài `apps/`; sửa app `erp_ai` hay bất kỳ bản sao, worktree nào của nó (A-3).
  - Hoàn tác lệnh `bench` đã chạy.
  - Giao diện duyệt riêng trên SPA Helpdesk (profile `ui: false`; vị trí nút duyệt do designer chọn).
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
- **Cấu hình mới:** công tắc bật/tắt (mặc định tắt) và danh sách app được sửa (mặc định rỗng). Chỉ System Manager sửa. Bot không đọc được cấu hình, vì `ERP AI Setting` nằm trong `DENIED_DOCTYPES` (`erp_ai/agent/tools/read.py:9-12`).
- **Dữ liệu nhạy cảm:**
  - Nội dung file nguồn được lưu trong DB.
  - File có tên khớp mẫu bí mật, file thuộc `protected_paths`, `site_config.json`, `common_site_config.json` và mọi thứ dưới `sites/` đều bị từ chối, nên không vào đề xuất (guide `:330-336`).
  - Đầu ra lệnh có thể chứa đường dẫn. Đầu ra không được chứa giá trị khóa API (NFR-5 của FEAT-001).
  - **[added: Amd-1 M-4]** URL remote của repo app có thể chứa token, nên không lưu và không hiển thị. Metadata commit không chứa email người dùng thật.
- **Nhật ký:** dùng ERP AI Log hiện có, theo nguyên tắc "chỉ runner tạo nhật ký" (ADR-004). Bước duyệt, áp dụng, hoàn tác do người thao tác và chạy ngoài runner, nên designer phải nêu ai ghi nhật ký cho các bước này mà không trái ADR-004, hoặc architect sửa ADR-004.

## Giao diện / tích hợp
- **Model ↔ registry tool:** thêm nhóm tool mới, cấp theo mức × thẩm quyền × công tắc (ADR-005 Quyết định 1). Tên tool và schema do designer chọn.
- **Hệ thống tệp:** chỉ trong `apps/<app được phép>/`. Bộ chặn phải khử symlink và kiểm lại lúc áp dụng.
- **Tiến trình con `bench`:** chạy trong thư mục bench, không qua shell, có timeout, đối số đúng như đã duyệt.
- **Repo git của app [added: Amd-1 M-3]:** bước áp dụng và hoàn tác tạo commit local trong repo của app đích. Không có thao tác nào với remote. Chi tiết ở M-8 (điểm mở cho architect).
- **Người ↔ hệ thống:**
  - Màn hình duyệt là Desk form hoặc khu vực trên trang phiếu. Nếu chọn khu vực trên trang phiếu thì phải phối hợp với FEAT-003 Amendment 1, đang build trên cùng khu vực.
  - Bot comment trên phiếu kèm liên kết tới đề xuất.
- **Các quyết định kiến trúc bị chạm (architect xử lý, cần ADR mới):** **[changed: Amd-1 M-8 — thêm ADR-013 QĐ 6 và lệnh git ghi]**
  - ADR-005 Quyết định 5 ("lệnh ngoài duy nhất là `git` log/show/diff/blame") và ràng buộc "`subprocess` chỉ xuất hiện trong module tool mã nguồn": phải nới ra cho lệnh `bench` đã duyệt.
  - ADR-005 ràng buộc "trong `erp_ai/agent/tools/**` không có … ghi": tool đề xuất không ghi file. Bước áp dụng nằm ở đâu do architect quyết.
  - ADR-003: job agent bị giới hạn 600 s và an toàn 60 s (`erp_ai/constants.py:25-27`), trong khi lệnh như `bench build` có thể chạy lâu hơn. Architect quyết định lệnh chạy trong job agent hay ở đường chạy riêng sau khi duyệt.
  - ADR-004 (ai ghi nhật ký): xem mục Dữ liệu.
  - **Hoàn tác toàn bộ feature:** tắt công tắc thì bộ tool và prompt trở lại đúng như FEAT-001 (AC-1).
- **Không đổi:** ADR-006 (tài khoản agent không có System Manager) giữ nguyên (A-2).

## NFR
| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Không có thay đổi nào khi chưa duyệt: 0 byte trên đĩa đổi và 0 lệnh chạy cho tới khi đề xuất ở trạng thái đã duyệt **[changed: Amd-1 M-5 — thêm 0 commit]** | Test AC-3, AC-8: so dấu nội dung file trước/sau; stub tiến trình con đếm 0 lời gọi |
| NFR-2 | Áp dụng đúng nội dung đã duyệt: file sau áp dụng trùng từng byte với nội dung đã duyệt; lệnh chạy đúng danh sách đối số đã duyệt; mỗi đề xuất áp dụng ≤ 1 lần **[changed: Amd-1 M-5 — nội dung file trong commit cũng trùng từng byte]** | Test AC-6, AC-8 |
| NFR-3 | Thời gian một lệnh không vượt giới hạn của đường chạy mà architect chọn. Nếu lệnh chạy trong job agent: lệnh phải kết thúc trước mốc 600 s − 60 s (`erp_ai/constants.py:25-27`), quá thì bị dừng và ghi lỗi **[changed: Amd-1 M-5 — bước git nằm trong cùng ngân sách]** | Test AC-10 bằng stub; architect đo `bench migrate` và `bench build --app <app>` trên `miyano` rồi ghi số vào design |
| NFR-4 | Đầu ra lệnh đưa cho model và lưu nhật ký ≤ 400 dòng, theo trần đọc sẵn có (NFR-6 FEAT-001, ADR-005) | Test AC-8: lệnh stub in 1.000 dòng thì kết quả còn ≤ 400 dòng |
| NFR-5 | 0 byte giá trị khóa API hoặc bí mật trong đề xuất, đầu ra lệnh, nhật ký | Test AC-13 gieo khóa giả (cùng cách NFR-5 FEAT-001) |
| NFR-6 | 100% các bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) có một dòng nhật ký với phiếu, đề xuất, người thực hiện, thời điểm, kết quả **[changed: Amd-1 M-5 — dòng áp dụng/hoàn tác có mã commit]** | Test AC-12 đếm dòng nhật ký theo từng bước |
| NFR-7..NFR-9 | **[added: Amd-1]** xem M-5 | — |

## Tiêu chí nghiệm thu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | Công tắc tắt (mặc định): với 4 mức × có/không người ra lệnh, danh sách tên tool trùng hoàn toàn với danh sách hiện nay. Prompt vẫn chứa câu "Không sửa file trong apps/" | Test tự động theo ma trận 8 tổ hợp, so với danh sách tên tool chụp từ nhánh nền; test grep chuỗi trong prompt |
| AC-2 | Bộ tool mới chỉ có khi đủ cả ba điều kiện: công tắc bật, mức hiệu lực `L3`, có người ra lệnh. Thiếu một điều kiện thì không có, kể cả khi vượt ngân sách và mức bị hạ về `L1` (ADR-003 bước e) | Test ma trận: công tắc × 4 mức × thẩm quyền × vượt/không vượt ngân sách |
| AC-3 | Gọi tool đề xuất thay đổi code hợp lệ thì: tạo 1 đề xuất "chờ duyệt", dấu nội dung file trên đĩa không đổi, và bot comment trên phiếu có liên kết tới đề xuất | Test tự động trên một app tạm trong danh sách được phép: so hash file trước/sau, đếm đề xuất và comment |
| AC-4 | Từ chối (`ok=false` kèm lý do, 0 đề xuất được tạo) với từng trường hợp: app `erp_ai`; đường dẫn khử symlink rơi vào repo `erp_ai` (kể cả worktree như `apps/erp_ai-wt`); app không có trong danh sách; đường dẫn thoát khỏi `apps/` bằng `..` hoặc symlink; tên khớp mẫu bí mật hoặc `protected_paths`; đuôi file ngoài danh sách đọc sẵn có; thao tác xóa hoặc đổi tên | Test tự động, mỗi nhánh từ chối một test |
| AC-5 | Chỉ người có vai trò `ERP AI Instructor` mới duyệt hoặc từ chối được. Tài khoản agent, `Administrator`, `Guest` và người không có vai trò đều bị từ chối ở server. Một comment chứa "ok"/"duyệt" của bất kỳ ai không làm đổi trạng thái đề xuất. Đề xuất bị từ chối thì không bao giờ được áp dụng | Test tự động: gọi thao tác duyệt dưới từng user; tạo comment "ok" rồi kiểm trạng thái vẫn là "chờ duyệt" |
| AC-6 | Sau khi duyệt, file trùng từng byte với nội dung đã duyệt, và lần duyệt hay áp dụng thứ hai không đổi gì thêm. Nếu file đích đã đổi kể từ lúc đề xuất thì: không ghi, trạng thái "hết hiệu lực", có dòng nhật ký **[changed: Amd-1 — thêm commit, xem AC-17; nhánh "hết hiệu lực" cũng có 0 commit]** | Test tự động: so byte; duyệt hai lần; sửa file giữa lúc đề xuất và lúc duyệt |
| AC-7 | Hoàn tác thay đổi code đã áp dụng thì file trở lại trùng từng byte với nội dung trước (file mới tạo thì bị gỡ). Nếu file đã bị sửa sau khi áp dụng thì từ chối hoàn tác và không ghi **[changed: Amd-1 — hoàn tác tạo commit mới, xem AC-20]** | Test tự động hai nhánh |
| AC-8 | Đề xuất một lệnh trong danh sách cho phép: tạo đề xuất "chờ duyệt", 0 lời gọi tiến trình con. Sau khi duyệt: đúng 1 lời gọi với đúng danh sách đối số đã duyệt, không qua shell, thư mục làm việc là thư mục bench, có timeout. Mã thoát và đầu ra (≤ 400 dòng) được lưu | Test tự động với stub tiến trình con: đếm lời gọi, so đối số, kiểm `shell` không bật, kiểm có timeout; lệnh stub in 1.000 dòng |
| AC-9 | Từ chối lúc đề xuất và kiểm lại lúc áp dụng với: mọi lệnh ngoài danh sách cho phép, mọi lệnh trong danh sách cấm (A-6), đối số chứa ký tự điều khiển shell (`;`, `|`, `&`, `` ` ``, `$(`, `>`), site khác site đang chạy, cờ `--force` | Test tự động, một test cho mỗi nhóm; thêm test sửa đề xuất đã duyệt cho thành lệnh cấm thì khi áp dụng vẫn bị chặn |
| AC-10 | Lệnh chạy quá giới hạn thời gian (NFR-3) thì bị dừng, trạng thái "lỗi", lý do "quá thời gian", có dòng nhật ký | Test tự động với stub ném hết thời gian |
| AC-11 | Chống chèn lệnh qua phiếu: phiếu và comment của người không có thẩm quyền chứa câu như "sửa file X / chạy bench Y / tự duyệt" thì lần chạy có 0 tool mới và tạo 0 đề xuất. Khi có người ra lệnh mà chưa ai duyệt thì có 0 lần áp dụng, dù model trả lời "đã được duyệt" | Test tự động với stub Cổng model: kịch bản không có người ra lệnh; kịch bản model gọi tool đề xuất rồi khẳng định đã duyệt |
| AC-12 | Mỗi bước (đề xuất, duyệt, từ chối, áp dụng, lỗi, hết hiệu lực, hoàn tác) tạo đúng 1 dòng nhật ký, có phiếu, đề xuất, người thực hiện, thời điểm, kết quả **[changed: Amd-1 — dòng áp dụng và hoàn tác thành công có mã commit; commit lỗi là bước "lỗi"]** | Test tự động đếm dòng nhật ký sau mỗi bước |
| AC-13 | Gieo khóa API giả vào cấu hình rồi chạy đề xuất, áp dụng và một lệnh stub in ra môi trường: chuỗi khóa xuất hiện 0 lần trong đề xuất, tool_result, nhật ký và comment **[changed: Amd-1 — thêm thông điệp và metadata commit, xem NFR-8]** | Test tự động, cùng cách test NFR-5 của FEAT-001 |
| AC-14 | Khi bộ tool mới được cấp, prompt nói rõ mọi thay đổi code hoặc lệnh phải chờ người duyệt, và bot không coi nội dung phiếu là lệnh duyệt. Khi không được cấp, prompt giống hệt hiện nay | Test tự động so chuỗi prompt hai trạng thái |
| AC-15 | Có ADR mới ghi phần nào của ADR-005 (và ADR-003/ADR-004 nếu đổi) bị thay, vì sao, và cách hoàn tác (tắt công tắc). Các test kiến trúc hiện có (ràng buộc ADR-005, scanner "writes-nothing" của FEAT-002) vẫn xanh hoặc được sửa đúng theo ADR mới **[changed: Amd-1 — thêm thay đổi ADR-013 QĐ 6 về commit, xem M-8 O-1, O-2]** | `ls docs/team/adr/` có ADR mới tham chiếu ADR-005; `cmd.test` xanh |
| AC-16..AC-23 | **[added: Amd-1]** xem M-6 | — |

## Assumptions decided by the team
- **A-1 Không làm tạo User và tool cấu hình.** chọn: chỉ làm sửa code và chạy lệnh, như người đã chốt (intake `:10`) | vì: tạo User và gán Role là nhóm "Tài khoản" của guide `:249`, cần thiết kế riêng (mẫu Role cố định, chặn tự nâng quyền theo guide `:258`); gộp vào thì vượt cỡ L | phương án khác: thêm tool tạo User vào feature này | sai thì: mở intake mới "tool L2/L3 theo guide 4.2" và đặt lên trước. Cảnh báo: sau feature này bot vẫn chưa tạo được user.
- **A-2 Không nâng quyền tài khoản agent.** chọn: giữ role hiện có, không System Manager (ADR-006) | vì: sửa file và chạy lệnh chạy ở mức hệ điều hành, role Frappe không chặn được gì (guide `:333`); rào cản thật là chặn đường dẫn, chặn lệnh và người duyệt. Cấp System Manager chỉ mở thêm đường ghi DocType bỏ qua thiết kế | phương án khác: cấp System Manager | sai thì: người tự cấp role ở Desk; spec không phụ thuộc vào việc này.
- **A-3 App được sửa là danh sách System Manager chọn, mặc định rỗng; `erp_ai` luôn bị cấm.** chọn: danh sách cho phép trên cấu hình; `erp_ai` và mọi đường dẫn khử symlink rơi vào repo `erp_ai` bị cấm cứng | vì: bot sửa được chính code chặn của mình là tự nâng quyền; bench có 13 thư mục app, trong đó có fork ERPNext/HRMS (`prompts.py:90`) và `erp_ai-wt` | phương án khác: cho sửa mọi app trừ `frappe` | sai thì: System Manager thêm app vào danh sách; muốn cho sửa `erp_ai` thì phải có ADR mới. **[changed: Amd-1 M-7 A-3']**
- **A-4 Bot không commit, push hay đổi nhánh.** chọn: thay đổi nằm ở working tree; người tự `git diff`/commit | vì: repo các app là của người (có thể đang có thay đổi chưa commit); tránh ghi đè lịch sử; quy tắc chỉ push `team/*` | phương án khác: mỗi thay đổi thành một commit trên nhánh riêng | sai thì: thêm bước commit local vào bước áp dụng ở feature sau; đề xuất đã lưu đủ diff nên không mất gì. **[changed: Amd-1 M-7 A-4' — thay thế]**
- **A-5 Một đề xuất là một file; mọi lệnh đều phải duyệt.** chọn: duyệt từng file, từng lệnh, kể cả lệnh chỉ đọc | vì: đúng chữ "duyệt từng thay đổi" (tiêu đề intake); áp dụng một file thì không cần cơ chế tất-cả-hoặc-không; lệnh `bench` nào cũng có thể có tác dụng phụ | phương án khác: đề xuất nhiều file, áp dụng trọn gói; miễn duyệt cho lệnh chỉ đọc | sai thì: thêm "nhóm đề xuất" ở amendment; tool đọc mã nguồn hiện có vẫn không cần duyệt.
- **A-6 Danh sách lệnh.** chọn: cho phép nhóm lệnh làm mới trạng thái của site đang chạy: `migrate`, `build --app <app được phép>`, `clear-cache`, `clear-website-cache`, và các lệnh chỉ in thông tin (`version`, `list-apps`). Cấm mọi lệnh khác, nêu rõ: `execute`, `console`, `mariadb`/`db-console`, `backup`, `restore`, `drop-site`, `reinstall`, `set-config`, `set-admin-password`, `add-system-manager`, `add-user`, `install-app`, `uninstall-app`, `remove-app`, `get-app`, `update`, `setup`, `restart`, `run-tests`, `--force` | vì: `execute`/`console` là chạy code tùy ý; các lệnh còn lại xóa dữ liệu, đổi bí mật, tự nâng quyền hoặc giết chính worker | phương án khác: cho cả `execute` khi có duyệt | sai thì: designer, cùng researcher, đối chiếu tên lệnh với bench và Frappe 15 trên `miyano`; thêm hay bớt lệnh là sửa danh sách, có test AC-9.
- **A-7 Người duyệt.** chọn: bất kỳ ai có `ERP AI Instructor`, kể cả chính người ra lệnh | vì: công ty khoảng 10 người (`prompts.py:73-74`); thẩm quyền đã định nghĩa sẵn (`authority.py`) | phương án khác: bắt buộc người duyệt khác người ra lệnh | sai thì: thêm một điều kiện ở thao tác duyệt và một test ở AC-5.
- **A-8 Giới hạn thời gian lệnh.** chọn: dùng mốc 600 s − 60 s có sẵn nếu lệnh chạy trong job agent; architect đo trên `miyano` rồi chốt | vì: không có số đo nào trong intake; không tự đặt số mới | phương án khác: một hàng đợi riêng với giới hạn dài hơn | sai thì: architect ghi số đo và giới hạn mới trong ADR; NFR-3 đổi theo.
- **A-9 Không có hạn duyệt theo thời gian.** chọn: đề xuất chỉ hết hiệu lực khi file đích đã đổi hoặc người từ chối | vì: không có nguồn nào cho con số hạn; kiểm dấu nội dung đã chặn việc áp dụng nội dung cũ | phương án khác: hết hạn sau N giờ | sai thì: thêm hạn ở amendment, có test.
- **A-10 Sau khi sửa code Python cần `bench restart`, việc này do người làm.** chọn: bot nêu trong comment là "cần restart" | vì: restart giết chính worker đang chạy job (ADR-003 Hệ quả) | phương án khác: cho bot restart | sai thì: architect thiết kế đường restart ngoài job ở feature sau.
- **A-11..A-18 [added: Amd-1]:** xem M-7.

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
| AC-22 | Trước khi duyệt, form duyệt hiện đủ: app, đường dẫn, diff, nhánh nhận commit, thông điệp commit sẽ dùng, các cảnh báo của AC-21 và cờ hoàn tác được. Sau khi áp dụng, form hiện mã commit áp dụng. Sau khi hoàn tác, form hiện mã commit hoàn tác | Test tự động đọc dữ liệu form theo từng trạng thái; qa mở form trên `miyano` và dán ảnh chụp hoặc mô tả vào `acceptance.md` |
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

## Definition of Done
**Phần build (trước G4):**
- [ ] Mọi AC-1..AC-15 đạt, đầu ra được dán trong `acceptance.md` **[changed: Amd-1 — AC-1..AC-23]**
- [ ] Có ADR mới cho các phần ADR-005 (ADR-003/004 nếu cần) bị thay, có cách hoàn tác **[changed: Amd-1 — thêm sửa ADR-013 QĐ 6 (commit local) và các điểm O-1..O-7]**
- [ ] Mỗi AC có ít nhất 1 test tự động (STD-TEST-2); không skip/xfail (STD-TEST-4)
- [ ] `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`) xanh; `cmd.lint` sạch
- [ ] Diff không chạm `protected_paths`, không chứa bí mật
- [ ] CI xanh
- [ ] **[added: Amd-1]** NFR-7..NFR-9 đạt; NFR-9 có đầu ra so HEAD và trạng thái working tree của `frappe`, `erpnext`, `helpdesk`, `hrms` trước/sau `cmd.test`, dán trong `acceptance.md`
- [ ] **[added: Amd-1]** Mọi test git chạy trên repo tạm; luật kiến trúc AC-23 xanh

**Sau G4 (`/team:asbuilt`, người làm phần đo thực tế):**
- [ ] As-Built viết xong (`asbuilt.md`)
- [ ] README/tài liệu người dùng: cách bật công tắc, chọn app, duyệt, hoàn tác, danh sách lệnh **[changed: Amd-1 — thêm: thêm app lõi vào danh sách và rủi ro; commit bot tạo trông thế nào; hoàn tác bằng commit; cách tự đẩy lên fork; làm gì trước và khi `bench update`]**
- [ ] Mục CHANGELOG
- [ ] Người chạy thử một vòng đề xuất → duyệt → áp dụng → hoàn tác trên môi trường thật trước khi bật lâu dài (Success); lên prod cần G5 **[changed: Amd-1 — vòng thử trên 1 app lõi ở site dev, có commit áp dụng và commit hoàn tác; người tự đẩy lên fork cho CI]**
