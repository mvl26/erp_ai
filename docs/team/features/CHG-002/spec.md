Feature: CHG-002
Stage: analyze
Author-agent: analyst
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Spec CHG-002 — Bot sửa được tất cả: mở đường sửa code, giữ vành đai an toàn (con trỏ)

Mode: decide, cỡ L, playbook change-request, G1 tắt. File này là con trỏ theo mẫu CHG-001: tiêu chí đầy đủ nằm ở `docs/team/features/FEAT-004/spec.md`, mục "Amendment 4 — 2026-11-15" (các mục Q-1..Q-9). Không có `questions.md`: mọi điểm lớn nằm ở mục Assumptions, đủ 4 trường. Cách làm (restart, khối nhiều mục, hoàn tác) do architect (`arch-impact.md` của CHG-002) và designer chọn; spec này chỉ nêu kết quả cần đạt.

## Mục tiêu
**Giả thuyết (độ tin cậy 80%):** người muốn bot sửa được code lõi mà không còn các rào cản kỹ thuật làm mỗi việc thật phải qua nhiều lần duyệt và một lần restart tay: một đề xuất gồm nhiều file (tạo cả thư mục mới, xóa, đổi tên) cùng các lệnh đi kèm (`migrate`, `build`, `restart`), người bấm Duyệt một lần, code có hiệu lực trên site mà không ai gõ lệnh. Vành đai an toàn do người chọn ("Giữ vành đai an toàn", N-1) giữ nguyên.

Chưa tới 85% vì bốn lẽ:
1. Restart tự động chưa thử được trên máy thật: tài khoản hệ điều hành của `miyano` chưa có quyền restart; lúc build chỉ kiểm bằng bản giả, phép đo thật nằm ở DoD sau G4 (AC-45, AC-57, NFR-15).
2. "Bỏ giới hạn kích thước" nhưng không có con số nào về chỗ lưu và form chịu được bao nhiêu (A-37).
3. Mục tiêu của người "sửa được tất cả, cả code lẫn data" được đọc theo N-1 là "mở có vành đai"; phần data thuộc FEAT-007 (QĐ-1 của team-leader).
4. Điều kiện cấp công cụ có thể đổi khi FEAT-007 merge (5 công tắc); designer đối chiếu (A-43).

| Mục | Nội dung |
|---|---|
| Outcome | Người có `ERP AI Instructor` giao bot một thay đổi code gồm nhiều file (kể cả thư mục mới, xóa, đổi tên) và các lệnh đi kèm, trong một app thuộc danh sách được sửa. Bot đưa một đề xuất; người bấm Duyệt một lần; hệ thống áp dụng cả khối; code mới có hiệu lực mà người không gõ lệnh nào; phần file hoàn tác được một thao tác. Mọi thứ ngoài vành đai (app `erp_ai`; file khóa, mật khẩu, cấu hình site; `.git` và push; lệnh bench ngoài danh sách; bot tự duyệt) vẫn bị từ chối ở mọi loại mục. |
| Users | Người có `ERP AI Instructor` (ra lệnh, duyệt, hoàn tác). System Manager (ô cho phép sửa code, danh sách app). Mới: người giữ máy `miyano`, làm một lần việc cấp quyền restart hẹp (A-42). Người giữ repo app (đọc commit, đẩy lên fork) không đổi. |
| Why now | Người cần gấp. Hôm nay một thay đổi N file là N lần duyệt, không tạo được module hay DocType mới, không xóa hay đổi tên được file, và sửa `.py` xong phải có người restart (`erp_ai/agent/change_text.py:113`). Phiên khác đang build FEAT-007 (phần dữ liệu) nên cần ranh giới rõ. |
| Success | Lúc build: AC-36..AC-56 đạt trên `miyano`, `cmd.test` xanh, và 40 phép thử của ma trận vành đai (AC-53) đều bị từ chối. Sau G4: số lần Duyệt cho một thay đổi N file kèm lệnh = 1 (hôm nay N); số lệnh người gõ trên máy để thay đổi `.py` đã duyệt có hiệu lực = 0 (hôm nay 1); một khối tạo DocType thử bằng code có DocType trên `miyano` sau 1 lần Duyệt; một khối có xóa và đổi tên hoàn tác một thao tác, trùng từng byte. |
| Constraints | Không push, không deploy prod (G5). Vành đai N-1 giữ nguyên chữ. Không đặt con số mới khi chưa có nguồn. Không sửa `site_api.py`, `registry.py`, `policy.py`, `runner.py`, `erp_ai_setting.json` (thuộc FEAT-007; cần thì nêu để báo phiên đó, A-43). Mọi `run-tests` và `migrate` qua khóa `.team/miyano-site.lock`. |
| Out of scope | Phần dữ liệu (công cụ bản ghi, 5 công tắc, danh mục trắng, đề xuất ghi bản ghi có duyệt): FEAT-007. Sửa app `erp_ai`. Lệnh bench ngoài danh sách (chỉ thêm `restart`). File khóa, mật khẩu, cấu hình site. `.git`, push. Bot tự duyệt. Duyệt hàng loạt nhiều đề xuất. Một khối gồm nhiều app. Đổi tên file giữa hai app. File nhị phân. Hoàn tác một lần bấm trong comment. Bot tự cấp quyền hệ điều hành cho mình. Production. PR và CI (push bị từ chối 403, chuỗi dừng ở merge cục bộ vào `develop`). |

## Người dùng
Như bảng trên. Chi tiết và các quy tắc an toàn đã đổi: FEAT-004 spec, Amendment 4, Q-1 và Q-2.

## Phạm vi
- **Trong (FEAT-004 Amendment 4, Q-3 mục 20–27):** một đề xuất nhiều mục thuộc một app, một lần duyệt; mục xóa file; mục đổi tên file; mục tạo file kèm thư mục cha mới (tạo được module và DocType mới bằng code cùng lệnh `migrate`); bỏ ba giới hạn kích thước; mọi file văn bản UTF-8; lệnh `restart` và restart tự động sau áp dụng; kiểm cú pháp `.py` và `.json` trước khi ghi.
- **Ngoài:** như dòng Out of scope ở trên. Mọi điều cấm của FEAT-004 N-2 ("Những điều vẫn bị cấm") và Amendment 3 P-2 giữ nguyên.

## Dữ liệu
Đề xuất phải giữ thêm: danh sách mục (loại; đường dẫn, hoặc đường dẫn nguồn và đích; nội dung trước và sau; kết quả từng mục); các lệnh đi kèm dưới dạng danh sách đối số đúng như đã duyệt; việc khối có cần restart; mã commit áp dụng và hoàn tác; kết quả restart (đã chạy và site trả lời, lỗi, chưa được cấp quyền, không cần). Không có thực thể mới do spec này đặt; designer đặt tên và chọn cách lưu. Nội dung file bị xóa và bị đổi tên được lưu như nội dung trước của đề xuất (đã đúng với file bị sửa). Không có cấu hình mới: điều kiện cấp công cụ không đổi (A-36).

## Giao diện / tích hợp
Comment của bot trên phiếu liệt kê mọi mục, mọi lệnh và việc restart trước khi người bấm Duyệt (AC-48); form Desk của đề xuất hiện diff từng mục và giữ ba nút, hộp xác nhận và nút Hoàn tác. Quyền restart ở hệ điều hành do người cấp một lần, chỉ cho các tiến trình của bench này (AC-57). Chạm: `tools/change_guard.py`, `tools/propose_change.py`, `tools/source.py`, `agent/changes/**`, `constants.py`, `change_text.py`, DocType `ERP AI Change Proposal` và test của chúng. Chạm ba ADR an toàn (ADR-011 QĐ 1 và 4, ADR-013 QĐ 6 và 7, ADR-022 QĐ 1 và 2): architect phán quyết ở tài liệu riêng.

## NFR
Chi tiết ở FEAT-004 Amendment 4, Q-4. Tóm tắt, không có con số thời gian mới (architect đo `migrate`, `build` và restart trên `miyano`, NFR-3 đã giao):

| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-12 | Trước khi duyệt: 0 byte, 0 thư mục, 0 commit, 0 lệnh, 0 restart, với mọi loại mục | Test AC-36: so cây thư mục, HEAD, bản giả tiến trình con và bản giả restart |
| NFR-13 | Phần file của khối là tất-cả-hoặc-không, cả lúc áp dụng lẫn hoàn tác | Test AC-37, AC-42: lỗi ở mục đầu, giữa, cuối |
| NFR-14 | Vành đai nguyên vẹn: HEAD và trạng thái làm việc của `frappe`, `erpnext`, `helpdesk`, `hrms` và repo `erp_ai` thật trùng trước và sau `cmd.test` | qa so trước và sau (NFR-9 mở rộng); luật kiến trúc |
| NFR-15 | Số lệnh người gõ để thay đổi `.py` đã duyệt có hiệu lực = 0 (hôm nay 1) | Sau G4 trên `miyano` (AC-45) |

## Tiêu chí nghiệm thu
Mã AC tiếp nối FEAT-004 (đã dùng tới AC-35). Cột "Cách kiểm" tóm tắt; bản đầy đủ ở FEAT-004 Amendment 4, Q-5.

| Mã | Tiêu chí (tóm tắt, đo được) | Cách kiểm |
|---|---|---|
| AC-36 | Một đề xuất ≥ 2 mục (sửa, tạo, xóa, đổi tên, lệnh bench trong danh sách), mọi mục file cùng một app: 1 đề xuất "Chờ duyệt", 1 comment 3 liên kết, 0 tác dụng cho tới khi duyệt; 1 lần duyệt áp dụng cả khối; khối có mục ở hai app bị từ chối cả khối | Test trên gốc app tạm, nhóm 5 mục, đếm đề xuất, comment, lời gọi quyết định = 1 |
| AC-37 | Phần file tất-cả-hoặc-không: một mục sai điều kiện lúc áp dụng, hoặc lỗi giữa chừng, thì 0 mục ghi (mục đã ghi trả về từng byte), 0 commit, HEAD và vùng staged như trước, lý do nêu đúng mục, 1 dòng nhật ký | Test từng điều kiện, lỗi ở mục đầu, giữa, cuối |
| AC-38 | Commit của khối chứa đúng các đường dẫn của khối và không đường dẫn nào khác; file khác giữ nguyên; nhánh, ref khác không đổi; blob từng mục trùng từng byte nội dung đã duyệt | Test như AC-17 mở rộng, repo tạm có file staged và unstaged khác |
| AC-39 | Mục tạo file kèm thư mục cha mới (nhiều cấp), chỉ trong thư mục của app được phép; không tạo trực tiếp dưới `apps/`, `sites/` hay app ngoài danh sách; hoàn tác gỡ thư mục do khối tạo nếu rỗng; sau G4: khối tạo DocType thử bằng code và `migrate` thì DocType có trong site | Test cây thư mục trên gốc tạm; sau G4 đo trên `miyano` |
| AC-40 | Mục xóa file: file tồn tại, sạch, qua bộ chặn như ghi; từ chối thư mục, file không có, file đã đổi, file không phải UTF-8; sau áp dụng file mất khỏi đĩa và có trong commit; hoàn tác trả đủ byte | Test từng nhánh trên repo tạm |
| AC-41 | Mục đổi tên: nguồn tồn tại và sạch, đích chưa có, cùng một app, hai đầu qua bộ chặn; nội dung giữ từng byte; hoàn tác trả lại | Test từng nhánh trên repo tạm |
| AC-42 | Hoàn tác khối bằng một thao tác: mọi mục file về từng byte (sửa, tạo gỡ, xóa có lại, đổi tên trả, thư mục do khối tạo gỡ nếu rỗng); từ chối cả khối nếu bất kỳ đường dẫn đã đổi sau áp dụng; lệnh trong khối không hoàn tác và được nói rõ trước khi duyệt | Test hoàn tác khối 5 mục và các nhánh từ chối |
| AC-43 | Ba giới hạn cũ (file mới 20 000 ký tự, 10 chỗ sửa, file nguồn 1 MiB) không còn là lý do từ chối: đề xuất ở mức ngay trên từng giới hạn tạo được, áp dụng và hoàn tác đúng từng byte; nếu còn trần kỹ thuật thì có số đo trong design, khác ba số cũ, và vượt thì từ chối nêu số đó | Test ba ca ngay trên giới hạn; đọc design |
| AC-44 | Mọi file văn bản UTF-8 trong app được sửa, tạo, xóa, đổi tên, không phụ thuộc đuôi, trừ vành đai; file không phải văn bản bị từ chối kèm lý do | Test `.yaml`, `.toml`, `.po`, `.sql`, `.scss`, `.ts`, `.xml`, file không đuôi; `.png` và `.pyc` bị từ chối |
| AC-45 | Khối có file `.py` áp dụng thành công thì hệ thống restart bench đúng 1 lần, là bước cuối, chỉ sau khi người đã duyệt, mọi mục file đã commit và mọi lệnh trong khối thành công; khối không có `.py` thì 0 restart; từ chối, hết hiệu lực, lỗi thì 0 restart; kết quả ghi trên đề xuất và comment | Test thứ tự và số lần với bản giả restart; sau G4 đo trên `miyano` (NFR-15 = 0) |
| AC-46 | An toàn của restart tự động: `.py` không biên dịch được và `.json` không hợp lệ bị từ chối cả khối (lúc đề xuất và lúc áp dụng); trước khi restart bắt đầu đã có comment nêu mã commit, nhánh và cách khôi phục bằng tay; sau restart có kết quả site trả lời hoặc không trả lời | Test từng nhánh; đọc comment trước thời điểm gọi restart |
| AC-47 | Danh sách lệnh bench chỉ thêm `restart` (dạng thường, không đối số nào dừng hay cấu hình lại dịch vụ); mọi lệnh khác, cờ `--force`, ký tự điều khiển shell và site khác vẫn bị từ chối lúc đề xuất và lúc áp dụng | Test như AC-9 cho từng nhóm, cộng `restart` hợp lệ và `restart` kèm đối số bị từ chối |
| AC-48 | Trước khi duyệt, comment liệt kê số mục mỗi loại, đường dẫn từng mục, dòng riêng cho mục xóa và đổi tên, từng lệnh đúng đối số, dòng "sẽ restart" khi và chỉ khi khối có `.py`, nhắc lệnh không hoàn tác; form hiện diff đủ mọi mục | Test đọc HTML comment và dữ liệu form; qa xem trang phiếu thật |
| AC-49 | Sau mỗi kết cục của khối có đúng 1 comment kết quả: kết quả từng mục, mã commit, mã thoát từng lệnh, kết quả restart, "việc người còn phải làm"; lệnh quá giờ thì dừng, nêu tên lệnh, giữ phần file đã áp dụng, không restart; 0 URL, khóa, token | Test job trên repo tạm, gieo token giả đếm = 0 |
| AC-50 | Vành đai `erp_ai`: mọi loại mục chạm repo `erp_ai` (kể cả worktree và symlink) thì cả khối bị từ chối, 0 đề xuất, 0 byte; 9 mục hợp lệ cộng 1 mục `erp_ai` bị từ chối đủ 10; kiểm lại lúc áp dụng | Test từng loại mục ở hai thời điểm |
| AC-51 | Vành đai bí mật và cấu hình site: đường dẫn khớp mẫu bí mật, `protected_paths`, dưới `sites/` thì từ chối mọi loại mục; không bị đọc, không vào đề xuất, comment, nhật ký; lệnh đọc hay đổi cấu hình site vẫn bị từ chối | Test từng loại mục; gieo khóa giả đếm = 0 |
| AC-52 | Vành đai `.git` và push: đường dẫn có thành phần `.git` hay tên bắt đầu bằng `.git` bị từ chối mọi loại mục; sau áp dụng và hoàn tác khối có xóa và đổi tên: ref remote và nhánh không đổi, 0 hook, 0 thao tác git bị cấm (luật AC-23 giữ) | Test trên repo tạm; test kiến trúc |
| AC-53 | Ma trận vành đai: 5 loại mục (sửa, tạo kể cả thư mục cha mới, xóa, đổi tên nguồn, đổi tên đích) × 4 vành (`erp_ai`; bí mật và cấu hình site; `.git`; ngoài app được phép) = 20 ô, mỗi ô thử lúc đề xuất và lúc áp dụng = 40 phép thử, cả 40 bị từ chối | Test ma trận 20 ô × 2 thời điểm |
| AC-54 | Một đề xuất một lần duyệt: chữ ký và dấu nội dung phủ cả khối; đề xuất thứ hai cùng file là đề xuất mới "Chờ duyệt"; duyệt đề xuất 1 chỉ áp dụng đúng nội dung đề xuất 1; N đề xuất cần N lần duyệt; không "duyệt tất cả"; lệnh và restart chỉ chạy nếu đã hiện trước khi duyệt | Test hai đề xuất liên tiếp, đổi một mục sau khi đề xuất, đếm lần duyệt |
| AC-55 | Bot không tự duyệt: tài khoản agent, `Administrator`, `Guest`, người không có vai trò bị từ chối ở cả hai đường duyệt; hàm quyết định và ghi vào đề xuất bị từ chối ở chế độ Toàn quyền; chữ "ok", "duyệt", "restart đi" không đổi gì; job kiểm lại người duyệt; restart chỉ chạy khi một người đã duyệt | Test từng người dùng, từng đường; model giả khẳng định "đã duyệt" thì 0 mục áp dụng |
| AC-56 | Điều kiện cấp công cụ không đổi: cả hai ô tắt thì danh sách tool và prompt trùng bản nền; mục mới chỉ có khi đủ điều kiện (a) của AC-2; Toàn quyền không mở thêm; prompt có khối nói rõ khối nhiều mục, xóa và đổi tên cần duyệt, restart do hệ thống làm, "ok" không phải duyệt | Test ma trận AC-1, AC-2 và so chuỗi prompt |
| AC-57 | Quyền restart ở hệ điều hành chỉ cho các tiến trình của bench này: một lệnh quản trị khác dưới cùng quyền bị từ chối; không có mật khẩu hay bí mật của quyền này trong repo, cấu hình, nhật ký, comment | Sau G4: người cấp, người thử một lệnh khác và dán kết quả; quét repo = 0 kết quả |

Thứ tự bỏ khi khối lượng vượt cỡ L (A-44): không bỏ AC-36, AC-37, AC-38, AC-42, AC-45, AC-47 và nhóm vành đai AC-50..AC-55, AC-57. Bỏ trước: kiểm site trả lời sau restart ở AC-46, rồi kiểm `.json` ở AC-46, rồi phần "trần kỹ thuật có số đo" ở AC-43, rồi phần đếm và nhấn mạnh theo loại ở AC-48.

## Assumptions decided by the team
Đủ 4 trường (chọn / vì / phương án khác / sai thì) ở FEAT-004 spec, Amendment 4, mục Q-6: A-32..A-45. Các điểm lớn nhất: một khối chỉ trong một app (A-32); phần file tất-cả-hoặc-không, lệnh chạy sau và không hoàn tác (A-33); không có con số kích thước thay thế (A-37); restart tự động đúng 1 lần cho khối có `.py`, cả khi hoàn tác (A-39); kiểm cú pháp là điều analyst thêm vì restart tự động (A-40); site không lên sau restart thì phục hồi bằng tay (A-41); quyền restart do người cấp một lần, hẹp (A-42).

## Definition of Done
**Phần build (trước G4):**
- [ ] AC-36..AC-56 đạt, đầu ra dán trong `acceptance.md` của CHG-002 (STD-TEST-2)
- [ ] Có ADR (mới hoặc sửa) do architect cho từng chỗ trái ở FEAT-004 Amendment 4, Q-2 (ADR-011 QĐ 1 và 4, ADR-013 QĐ 6 và 7, ADR-022 QĐ 1 và 2), kèm cách hoàn tác: tắt ô cho phép sửa code (AC-1) hoặc revert merge
- [ ] Mỗi AC có ít nhất 1 test tự động hoặc 1 bước kiểm có đầu ra; không skip, xfail hay only (STD-TEST-4)
- [ ] Test cũ chỉ được sửa ở các nhánh Q-2 liệt kê, mỗi chỗ có ADR tương ứng; không sửa assertion cho khớp mã (STD-TEST-5)
- [ ] `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`) xanh, chạy qua khóa `.team/miyano-site.lock`; các lỗi do cài đặt site đã biết (DoD FEAT-004) không được sửa bằng cách đổi test; `cmd.lint` sạch
- [ ] NFR-12, NFR-13, NFR-14 đạt; NFR-14 có đầu ra HEAD và `status --porcelain` của `frappe`, `erpnext`, `helpdesk`, `hrms` và `erp_ai` trước và sau `cmd.test`, dán trong `acceptance.md`
- [ ] Ma trận vành đai AC-53: 40 phép thử bị từ chối, đầu ra dán trong `acceptance.md`
- [ ] Mọi test có git, thư mục, xóa, đổi tên chạy trên gốc app tạm (ADR-022 QĐ 8); luật kiến trúc mới cho nơi ghi file, tạo thư mục, xóa, đổi tên, chạy tiến trình, restart và thao tác git
- [ ] Reviewer chấm các file mới và file sửa theo Review checklist (10)
- [ ] Diff không chạm `protected_paths`, không chứa bí mật; không sửa `site_api.py`, `registry.py`, `policy.py`, `runner.py`, `erp_ai_setting.json` (hoặc đã nêu để báo phiên FEAT-007, A-43)
- [ ] Merge cục bộ vào `develop` (push GitHub bị từ chối 403, nên chưa có PR và CI)

**Sau G4 (`/team:asbuilt`, người làm phần đo thực tế):**
- [ ] As-Built (`asbuilt.md`) viết xong, có mục "Rủi ro còn lại" theo FEAT-004 Amendment 4, Q-7
- [ ] README và tài liệu người dùng: khối nhiều mục, xóa, đổi tên, thư mục mới, restart tự động, cách khôi phục bằng tay khi site không lên, bảng "Quy tắc an toàn đã đổi" (S-11..S-16) và danh sách điều vẫn bị cấm
- [ ] Mục CHANGELOG
- [ ] Người làm một lần trên máy `miyano`: cấp quyền restart hẹp (AC-57); cách cấp ghi trong As-Built; mật khẩu không vào repo
- [ ] Người đo trên `miyano`: sửa một file `.py` thử qua 1 lần Duyệt, có hiệu lực mà không ai gõ lệnh (AC-45, NFR-15 = 0), dán vào `acceptance.md`
- [ ] Người đo trên `miyano`: một khối tạo DocType thử bằng code (thư mục, file, `migrate`, restart) có DocType trong site (AC-39); hoàn tác phần file; người dọn DocType thử ở Desk
- [ ] Người đo trên `miyano`: một khối có xóa và đổi tên file thử, hoàn tác một thao tác, file trùng từng byte (AC-42)
- [ ] Trước khi bật trên môi trường khác: người xác nhận quyền restart ở môi trường đó (chưa kiểm trên production, `UNVERIFIED`); lên prod cần G5

## Amendment
Không có; file này là con trỏ tới FEAT-004 Amendment 4. Artifact sau bị ảnh hưởng: xem FEAT-004 Amendment 4, Q-8 (`arch-impact.md`, ba ADR an toàn, `design.md`, plan và tasks của CHG-002, test đang ghim hành vi cũ, tài liệu người dùng).
