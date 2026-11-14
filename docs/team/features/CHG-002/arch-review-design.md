Feature: CHG-002
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- Cổng: G2 tắt cho CHG-002 (team.py: designed, READY plan). Để trống. -->

# Rà soát kiến trúc design CHG-002

REVIEW: fix

Design khớp ADR-040 QĐ 1–8 ở những chỗ vành đai khó giữ nhất: mọi đường dẫn của mọi loại mục, cả hai đầu đổi tên và từng thư mục mới, đi qua cùng `check_write_path` ở cả hai thời điểm (chặn `erp_ai` theo danh tính repo theo ADR-011 QĐ 4; `TEN_CAM`, `.git*`, symlink, repo lồng; `sites/`, `config/supervisor.conf` và cấu hình chung của bench nằm ngoài gốc `apps/`), tập git ghi giữ `{add, commit, rm --cached}` (ADR-022 QĐ 2), danh sách `bench` chỉ thêm đúng `["restart"]`, và `queue.py` vẫn đúng 2 lời gọi enqueue (ADR-013 QĐ 2). Restart tách rời đúng ADR-040 QĐ 7 và ADR-013 QĐ 3, 5: argv hằng `setsid -f timeout -s KILL 700 bench restart` với 3 luồng `DEVNULL`, chỉ khởi chạy sau khi `Đã áp dụng`/`Đã hoàn tác` và comment khôi phục đã commit DB, xác nhận lười không thêm lối chạy nền; tệp sudoers §5.1 cho đúng ba dòng lệnh mà bench 5.31.0 gọi, thoát `\:` đúng, và vì `restart` không đọc lại cấu hình supervisor nên tệp không mở đường leo thang qua `config/supervisor.conf` (chỉ còn rủi ro từ chối dịch vụ đã ghi ở ADR-040 Hệ quả). Không có blocker, nhưng phải sửa ba major trước khi tech-lead chốt task: §2.5 chưa tính `diff` vào tổng nên còn trần ẩn ở gói SQL (Phán quyết C-1 của ADR-040, AC-43); `confirm_restart` nhận cả System Manager không có `ERP AI Instructor`, trái ADR-012 QĐ 4 và Ràng buộc; `remove_file` chưa kiểm lại `.git*` và symlink trên đường xóa như ADR-040 Ràng buộc đòi.

## Phán quyết C-1
Đã ghi trong `docs/team/adr/ADR-040.md`, mục "Phán quyết C-1 (2026-11-15, architect)". Tóm tắt:
- Mỗi file tối đa `CHANGE_FILE_MAX_BYTES` = 2 MiB, là hằng mới trong `erp_ai/constants.py`. Tool đọc (`read_source`, `search_source`) và bộ chặn ghi dùng chung hằng này qua một hàm "văn bản cho phép".
- Tổng mỗi đề xuất vẫn là 8 MiB, nhưng tính cả byte của `diff` trên bản ghi cha.
- 50 thao tác file và 6 lệnh giữ nguyên.
- Căn cứ: gói SQL 16 MiB ở cả máy chủ và pymysql; Frappe chèn từng dòng bằng câu riêng; thoát chuỗi xấu nhất ×2. Dòng con ≤ 8 MiB và bản ghi cha ≤ khoảng 10,7 MiB sau khi thoát chuỗi.

## Findings
Định dạng: `severity | STD | file:line | mô tả | sửa`. Cột "Blocker" trả lời câu hỏi của team-leader.

| # | Blocker | severity | STD | file:line (mục) | mô tả | sửa |
|---|---|---|---|---|---|---|
| F-1 | không | major | STD-DESIGN-2 | `design.md:61`, `:70`, `:188`, `:190`, `:196-199`, `:258`, `:770` (§1.4, §1.5 R-1, §2.5, §3.1, §8.1) | Design phải theo Phán quyết C-1 của ADR-040. Hiện `TEXT_MAX_BYTES` là 1 MiB "chờ C-1", và tổng 8 MiB chỉ đếm trước + sau. Ước "3% tiền tố dòng" sai với dòng ngắn: khi file toàn dòng rỗng, `diff` dài gấp đôi nội dung. Một khối 8 MiB khi đó cho bản ghi cha tới 16 MiB thô, vượt gói SQL lúc `insert` mà không có lý do nêu con số. AC-43 cấm đúng loại trần ẩn này. | `CHANGE_FILE_MAX_BYTES = 2 MiB` trong `constants.py`, và `source.TEXT_MAX_BYTES` chỉ nhập lại hằng đó. `CHANGE_MAX_TOTAL_BYTES` đếm trước + sau + `diff`. Chữ của `BLOCK_TOO_LARGE` thêm "(kể cả diff)", chữ của `TEXT_TOO_LARGE` lấy "2 MiB" từ hằng. Bỏ chữ "chờ C-1" ở test `test_source_file_one_mib_plus_one`. Thêm các test ở "Ràng buộc của phán quyết" (gồm test ngân sách gói với nội dung xấu nhất). Việc chia task không phải đợi: chỉ đổi giá trị hằng và cách đếm. |
| F-2 | không | major | STD-SEC-4 | `design.md:326` (§3.3), `:615` (§5) | `confirm_restart` cho "`ERP AI Instructor` hoặc `System Manager`". ADR-012 QĐ 4 đòi mọi method whitelisted trên form đề xuất kiểm role `ERP AI Instructor`. Ràng buộc của ADR-012 đòi người không có role đó bị `PermissionError`. ADR-040 QĐ 8 giữ nguyên ADR-012 QĐ 4–7 như vành đai N-1. Hàm chỉ ghi kết luận rút từ bằng chứng nên hại nhỏ, nhưng đây là một method thứ hai trên form có luật quyền khác `_decider`. | `confirm_restart` gọi đúng `_decider` (chỉ `ERP AI Instructor`, ngoài `NEVER_AUTHORITY`). Thêm vào `DOC::TestConfirmRestart` ca System Manager không có Instructor → `PermissionError`, `restart_status` không đổi. |
| F-3 | không | major | STD-DESIGN-2 | `design.md:345` (§3.5), cùng `:346` | ADR-040 Ràng buộc: "`file_writer` từ chối mọi thành phần `.git*` và mọi symlink trên đường dẫn ghi, xóa và tạo thư mục". `write_atomic` và `make_parents` có kiểm. `remove_file` chỉ nói "file thường, không xóa symlink" và không kiểm lại thư mục cha. Nếu một thư mục cha bị thay bằng symlink giữa lúc `check_block` lúc áp dụng và lúc xóa, lệnh xóa sẽ đi ra ngoài app. `remove_empty_dirs` cũng chưa nêu luật này. | `remove_file` áp cùng hai điều kiện như `write_atomic`: không thành phần `.git*`, và `realpath(dirname) == dirname`. `remove_empty_dirs` bỏ qua (không `rmdir`) mọi thư mục là symlink hoặc có thành phần `.git*`. Thêm vào `test_file_writer.py` ca thư mục cha là symlink → `ValueError`, 0 file bị xóa. |
| — | không | minor | — | — | 3 điểm nhỏ. (1) `:642` (§5.1 bước 3): `sudo -n -l` không in "đúng ba dòng". Nó in một mục `(root) NOPASSWD:` liệt kê ba lệnh, và nếu `miyano` thuộc nhóm `sudo` thì có thêm mục `(ALL : ALL) ALL`. Sửa chữ để người giữ máy không tưởng AC-57 trượt. (2) `:336` (§3.4): `"setsid"` là tên trần, tra theo PATH của `_minimal_env()`, trong khi `timeout` và `bench` là hằng do server xác định (ADR-013 QĐ 7). Nên đặt `SETSID_EXECUTABLE` cạnh hai hằng kia, và test hình dạng argv đi theo. (3) `:573` (§4.4): `birth_date` của rq là giờ UTC không có múi giờ, còn `create_time()` của psutil là epoch. Đổi về cùng một gốc thời gian trước khi so, và thêm một test có múi giờ máy khác UTC. | dev tự quyết |

## Căn cứ đã đọc (2026-11-15, `develop` @ `2fd42ad`, chỉ đọc)
- `docs/team/features/CHG-002/design.md` (887 dòng, đọc hết); `docs/team/features/CHG-002/intake.md` (N-1); `docs/team/features/FEAT-004/spec.md:512-692` (Amendment 4, AC-43, A-37); ADR-011, ADR-012, ADR-013, ADR-022, ADR-040.
- `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:93-112`: `_decider` chỉ nhận `ERP AI Instructor`, ngoài `NEVER_AUTHORITY`. Đây là căn cứ của F-2.
- `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json:369`: `track_changes: 0`, nên `insert` không sinh bản ghi Version chứa nội dung.
- `erp_ai/agent/tools/propose_change.py:91-99`: `_diff` là `difflib.unified_diff`, mỗi dòng có 1 byte tiền tố. Đây là căn cứ của F-1.
- `erp_ai/agent/changes/apply_job.py:232-234`: hoàn tác hôm nay đã dùng `allowed_apps=(proposal.app,)`. §4.3 của design giữ đúng hành vi này, không phải finding.
- `erp_ai/agent/tools/source.py:33`, `:37`, `:153`, `:220`: `READ_MAX_LINES = 400` và `SEARCH_FILE_MAX_BYTES = 1 MiB`. Đây là căn cứ của Phán quyết C-1, điểm 2.
- Mã đã cài: `pymysql/connections.py:190` (gói mặc định 16 MiB); `pymysql/converters.py:63-69` (bảng thoát chuỗi); `frappe/model/document.py:445-446` (mỗi dòng con một câu INSERT).
