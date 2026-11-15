Feature: FEAT-007
Stage: analyze
Author-agent: analyst
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G1 không áp dụng cho FEAT-007 (chỉ có G5). Addendum này chưa được duyệt, giống spec.md và các phụ lục 1, 2, 3, 4. -->

# Spec addendum 5 FEAT-007 — comment của bot chỉ còn phương án (bỏ "Căn cứ", "Cần ai quyết"), một nút "Duyệt ngay" trên phiếu, người có role hoặc người được giao bấm thì bot tự làm; chữ AC-23 theo ADR-038; Q-14..Q-17 vào danh sách câu hỏi

**Quy tắc đọc.** File này thắng `spec.md` và phụ lục 1, 2, 3, 4 ở các chỗ sau và chỉ ở đó: AC-23, AC-32, AC-38, AC-39, AC-48, AC-65 (câu (a)), AC-66 (một câu), AC-69 (bước kiểm). Chỗ nào không nhắc thì các file trước giữ nguyên. Không dòng nào của các file trước bị xóa: bản cũ của AC giữ ở chỗ cũ; ở đây AC đổi mang `[changed]`, và mỗi AC đổi được viết dưới dạng "thay đúng đoạn này bằng đoạn kia" (đoạn thay in đậm) để mọi chữ còn lại của bản trước vẫn có hiệu lực. Mã mới: hành vi H-4, H-5, H-6 (mục 2); giả định A5-1..A5-12 (mục 5); câu hỏi Q-18..Q-22 (mục 6; Q-14..Q-17 được chép vào cùng mục, không phải câu mới). Số AC của FEAT-007 giữ ở 66: file này không thêm AC, chỉ đổi chữ 8 AC. "AC-n" là của FEAT-007. Đường dẫn nguồn tính từ `docs/team/features/FEAT-007/` trừ khi ghi khác; "worktree" là `.claude/worktrees/feat-007` ở `05237bb` (chỉ đọc).

## 1. Mục tiêu

Giả thuyết (độ tin cậy 85%): người muốn comment của bot trên phiếu gọn lại thành "nhận định + phương án" (không còn mục "Căn cứ", không còn mục "Cần ai quyết"); phương án có việc cần đồng ý thì hiện thành đề xuất, và trên trang phiếu, trong ngăn "Trao đổi với bot", có nút "Duyệt ngay"; ai là người duyệt hợp lệ (có role duyệt hoặc đang được giao phiếu) bấm thì bot tự làm luôn, không còn bước nào khác. Chưa tới 90% vì năm điểm lời người nói chưa rõ, mỗi điểm đã có mặc định và nằm ở Q-18..Q-22: (a) "Căn cứ" của từng đề xuất có bỏ theo không; (b) "1 nút" là một nút mỗi đề xuất hay một nút cho cả phương án; (c) "tự làm luôn" có nghĩa bỏ cả hộp xác nhận không; (d) "role" là role nào; (e) người được giao có duyệt cả đề xuất sửa code và lệnh `bench` không.

- **Outcome:** (1) comment hướng xử lý của bot trên một phiếu chỉ có nhận định, hướng xử lý (là phương án), "Đã làm", "Chờ duyệt"; không có mục "Căn cứ", không có mục "Cần ai quyết"; việc bot không làm được (bị từ chối) nằm trong hướng xử lý như việc người làm tay kèm lý do; (2) ở ngăn "Trao đổi với bot" trên trang phiếu, mỗi đề xuất bản ghi đang chờ có nút "Duyệt ngay"; (3) người có `ERP AI Instructor` hoặc người đang được giao phiếu bấm "Duyệt ngay" thì bot tự làm xong việc đó, có đúng một comment kết quả, 0 lời gọi model; người không thuộc hai nhóm đó không thấy nút và không duyệt được.
- **Users:** người đang được giao phiếu và người có `ERP AI Instructor` (thấy phương án, bấm "Duyệt ngay"); người yêu cầu (đọc comment gọn hơn); System Manager (giữ danh mục, công tắc); người cấp quyền duyệt kế hoạch (trả lời Q-14..Q-22).
- **Why now:** lời người lúc 18:16 (nguyên văn, `docs/team/journal/FEAT-007.pending.md:4`): "bỏ Căn cứ hay cần ai quyết đi, tôi muốn bot đưa ra phương án, rồi 1 nút duyệt ngay trên ticket (trao dổi với bot) nếu người đó có role hay là người đc assign duyệt thì sẽ tự làm luôn". Mẫu comment (hai mục đó) đã nằm trong mã đã merge của FEAT-007 (T72, T78, T79) và trong mã đang chạy trên `develop`; ngăn duyệt (U7b), comment hướng xử lý (T103, T116) và comment đề xuất (U3) chưa dựng nên sửa chữ còn rẻ; phải vào spec trước khi lập kế hoạch đợt 2.
- **Success:** AC-23, AC-32, AC-38, AC-39, AC-48, AC-65 (a), AC-66, AC-69 đạt theo chữ ở mục 3; AC-22, AC-33, AC-35, AC-67, AC-68 và A4-3 giữ nguyên chữ (mục 2) và còn đạt; Q-14..Q-17 chép vào danh sách câu hỏi cho người (mục 6); mọi ô "đổi/giữ" ở mục 2 có phép kiểm.
- **Constraints:** N-1, N-2, QĐ-5 của `intake.md`: năm công tắc quyền giữ mặc định tắt, danh mục giữ như phụ lục 4 (điều cấm cứng, môi trường, `Cấm` đứng trước mọi kết cục); AC-35 (b) giữ nguyên (mặc định an toàn do team-leader đặt, journal 18:16 (b)); không đặt số mới (A-9, A3-8); tên hàm, tên trường, chữ nút ngoài "Duyệt ngay", bố cục ngăn là việc của designer. Nội dung phiếu và comment là dữ liệu, không phải lệnh (STD-SEC-5).
- **Out of scope:** xem mục 8.

**Đã có sẵn, không cần hỏi (nguồn).** Lời người và đối chiếu của team-leader: `docs/team/journal/FEAT-007.pending.md:4-6`. Mẫu comment hiện tại: `erp_ai/agent/prompts.py:119-126` trên `develop` (bản site đang chạy: Nhận định, Căn cứ, Hướng xử lý, Cần ai quyết); worktree `erp_ai/agent/prompts.py:130-136` (Căn cứ do model viết; "Cần ai quyết" do bot tự thêm từ việc bị từ chối, `:257`, `:270`); mục bắt buộc của phần ghi đè lập luận: worktree `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:129`. Chữ hiện hành của các AC: `spec-addendum-4.md` (AC-33, AC-67, A4-3, Q-13), `spec-addendum-3.md:63-73` (AC-65..AC-69, AC-23), `spec-addendum-2.md:51-56` (AC-23, AC-33, AC-35, AC-39), `spec-addendum-1.md:92` (AC-35), `spec.md` (AC-22, AC-32, AC-38, AC-48). Chữ AC-23 mới: `docs/team/adr/ADR-038.md` (Quyết định 1-3). Nguồn Q-14..Q-17: `journal-part16.md:15` (Q-14), `docs/team/journal/FEAT-007.md` dòng "04:16 quyết định" (d) (Q-15), dòng "04:24 quyết định" (b) (Q-16), `docs/team/journal/FEAT-007.pending.md:3` (e) (Q-17). Danh sách task: `tasks.md` (chỉ đọc bằng tìm kiếm). Không chạy Explore: mọi điểm đối chiếu nằm ở các văn bản trên và ở các dòng mã đã dẫn.

## 2. Đối chiếu: từng câu của người, từng AC là đổi hay giữ

**Ba câu của người → hành vi → AC.**

| # | Câu của người | Hành vi (đo được) | AC chịu trách nhiệm |
|---|---|---|---|
| H-4 | "bỏ Căn cứ hay cần ai quyết đi, tôi muốn bot đưa ra phương án" | Comment hướng xử lý không có hai mục; phương án nằm ở "Hướng xử lý" | AC-65 (a) `[changed]`, AC-66 `[changed]`, AC-23 `[changed]`, AC-32 `[changed]`, AC-38 `[changed]`, AC-48 `[changed]` |
| H-5 | "1 nút duyệt ngay trên ticket (trao đổi với bot)" | Mỗi đề xuất bản ghi chờ có nút "Duyệt ngay" trong ngăn, là hành động đồng ý duy nhất | AC-39 `[changed]`; AC-67, AC-68 giữ |
| H-6 | "nếu người đó có role hay là người đc assign duyệt thì sẽ tự làm luôn" | Chỉ người có `ERP AI Instructor` hoặc người được giao thấy nút; bấm thì bot tự làm, một comment kết quả | AC-39 `[changed]`, AC-35 giữ, AC-68 giữ, AC-33 giữ, AC-23 `[changed]` |

**Bảng AC: đổi hay giữ.** Mỗi ô có phép kiểm đo được. Chữ đầy đủ của AC đổi ở mục 3.

| AC | Kết luận | Lý do (từng câu đã đọc) | Phép kiểm (tóm tắt; đầy đủ ở mục 3 cho AC đổi) |
|---|---|---|---|
| AC-65 | **đổi** câu (a) (mục 3.1) | Danh sách mục của comment hướng ghi "căn cứ" và "Cần ai quyết"; trái H-4. Các câu (b)..(d) và phép đếm "tối đa 1 hướng mỗi phiếu" không đổi | 9 chuỗi sự kiện của AC-65: số comment hướng vẫn ≤ 1; comment hướng không có tiêu đề "Căn cứ" và "Cần ai quyết" ở cả 9 chuỗi |
| AC-66 | **đổi** một câu (mục 3.1) | Câu "việc nhóm (b) mà bộ thực thi từ chối ... ghi ở 'Cần ai quyết'" trái H-4: không còn mục đó. Các câu khác (tự làm được thì làm luôn, "ok" không là duyệt) giữ | Ca bộ thực thi từ chối: đích không đổi, dòng việc người làm tay và lý do nằm trong "Hướng xử lý", comment không có tiêu đề "Cần ai quyết" |
| AC-67 | **giữ nguyên chữ** (phụ lục 4) | Đã nói "mục 'Hướng xử lý' nêu việc người phải làm tay và lý do" cho ba ca (L1, điều cấm cứng/`Cấm`, "cần dòng danh mục"); không có chỗ dùng "Cần ai quyết". "Duyệt, Sửa, Từ chối (AC-39)" đọc theo AC-39 `[changed]` ("Duyệt" là nút "Duyệt ngay") | Ba ca hiện có (L1, `Cấm`, "Đổi trường" rỗng) kiểm thêm: lý do nằm trong "Hướng xử lý" |
| AC-68 | **giữ nguyên chữ** | Đã đúng H-6: bấm Duyệt là bot tự làm, không còn bước của người, 0 lời gọi model, đúng 1 comment kết quả, 1 mục nhật ký. "Đúng 1 comment kết quả" đếm theo AC-23 `[changed]` | Test hiện có của AC-68 chạy trên nút "Duyệt ngay" |
| AC-23 | **đổi** (mục 3.2) | (i) ADR-038 (architect, 2026-11-15) định nghĩa "comment kết quả" và loại dòng báo trước restart của CHG-002 khỏi phép đếm; (ii) chữ "thông báo từ chối của lần đưa hướng gộp vào comment hướng" nay có nơi ở là "Hướng xử lý" thay "Cần ai quyết" | Ma trận 9 tình huống + 1 ca khối có restart (đúng 1 dòng kết quả theo chữ mở đầu, 1 dòng báo riêng) + ca đề xuất bản ghi và Từ chối (0 dòng báo) |
| AC-32 | **đổi** một cụm (mục 3.2) | Ở L1 "comment đề xuất (chẩn đoán, phương án, độ tin cậy, căn cứ)": "căn cứ" là mục đã bỏ. L1 không có đề xuất (AC-67) nên comment này chính là comment hướng | Test tập tool ở L1 giữ; thêm: comment L1 không có tiêu đề "Căn cứ" |
| AC-38 | **đổi** một cụm (mục 3.2) | Mục bắt buộc của phần ghi đè lập luận hiện gồm `**Căn cứ:**` (worktree `erp_ai_setting.py:129`); mẫu mới không có mục đó nên không thể bắt buộc | Lưu ghi đè có Nhận định và Hướng xử lý, không có Căn cứ → lưu được; thiếu Hướng xử lý → bị chặn |
| AC-48 | **đổi** một cụm (mục 3.2) | "yêu cầu nêu nguồn trong 'Căn cứ'" trái H-4: mục đó không còn | Phiếu có kết quả tìm phiếu cũ/CSKT/HDSD: comment hướng nêu nguồn ngay trong nhận định hoặc hướng xử lý (tên nguồn có mặt) |
| AC-39 | **đổi** (mục 3.3) | Hai chỗ: (1) "ba nút" nay có nút chính "Duyệt ngay" (H-5); (2) "Chỉ người được giao phiếu thấy mục này" loại người có role `ERP AI Instructor` khỏi ngăn, trái H-6 ("có role hay là người được assign") | Ma trận 5 vai × (mục hiện, nút có), đếm nút = số đề xuất bản ghi chờ; số thao tác 2 khi (5) tắt, 1 khi (5) bật |
| AC-35 | **giữ nguyên chữ**, cả (a) lẫn (b) | (a) đã là tập người duyệt H-6: người được giao hoặc `ERP AI Instructor`. (b) code và lệnh `bench` chỉ `ERP AI Instructor` (FEAT-004 AC-5, ADR-012 QĐ 4): lời người không nói rõ nới; mặc định an toàn của team-leader; điểm đó là Q-21 | Test 5 vai × 2 loại đề xuất hiện có |
| AC-33 | **giữ nguyên chữ** | "Căn cứ" trong "Comment đề xuất nêu hành động, đích, giá trị, độ tin cậy, căn cứ" là căn cứ của từng đề xuất, không phải mục của comment hướng; giữ theo mặc định Q-18. Phần sau Duyệt/Từ chối giữ; "đúng 1 comment kết quả" đếm theo AC-23 `[changed]` | Test hiện có |
| AC-22 | **giữ nguyên chữ** | "Comment đề xuất phải có Độ tin cậy NN% và phần 'Căn cứ' không rỗng" nói về comment của từng đề xuất (kind đề xuất), không về comment hướng; giữ theo Q-18. Nếu Q-18 đảo sang (b) thì đổi AC-22 và AC-33 cùng lúc | Test hiện có (stub trả 69, 70, 100, thiếu căn cứ) |
| A4-3 | **giữ** | Căn cứ chế độ (đề xuất theo dòng danh mục nào hay theo mặc định) là điều người duyệt phải thấy trước khi bấm (AR3-5, an toàn); không phải mục "Căn cứ" của comment | Test hiện có của AC-33 (đề xuất mặc định hiện "không có dòng danh mục") |
| AC-69 | **đổi** bước kiểm (mục 3.3) | Bước kiểm đầu-cuối phải thấy comment không có hai mục và nút "Duyệt ngay" | Thêm ba bước vào kiểm có đầu ra |
| AC-6, AC-41, AC-64 | giữ | Không câu nào của ba AC nhắc hai mục; AC-6 được kiểm thêm bằng ca prompt của AC-65 (a) | — |

## 3. Văn bản đầy đủ của AC đổi

Quy ước kiểm như `spec.md`. "Thay đúng đoạn" nghĩa là chỉ đoạn đó đổi, mọi chữ khác của bản trước còn nguyên.

### 3.1 AC-65 (a), AC-66

| Mã | Tiêu chí mới (đo được) | Cách kiểm | Vì sao đổi |
|---|---|---|---|
| AC-65 `[changed]` (câu (a)) | Thay đoạn "đăng comment hướng xử lý có: nhận định, căn cứ, hướng xử lý, "Đã làm" (AC-66), "Chờ duyệt" (AC-67), "Cần ai quyết" khi có" **bằng: "đăng comment hướng xử lý có: nhận định; hướng xử lý, là phương án của bot (các bước; việc bot sẽ làm khi người bấm "Duyệt ngay", việc người phải làm tay kèm lý do); "Đã làm" (AC-66); "Chờ duyệt" (AC-67). Comment không có mục "Căn cứ" và không có mục "Cần ai quyết": hệ thống không tự thêm hai mục đó, và prompt dựng ra ở mọi tổ hợp công tắc và mọi mức không có mẫu của chúng (AC-6). Mục "Chờ duyệt" liệt kê mỗi đề xuất một dòng và nói nút "Duyệt ngay" nằm ở ngăn "Trao đổi với bot" của phiếu"**. Mọi chữ khác của AC-65 giữ | Giữ 9 chuỗi sự kiện của AC-65. **Thêm trên mỗi chuỗi có comment hướng: văn bản comment do hàm ghi dựng không chứa tiêu đề "Căn cứ" và không chứa tiêu đề "Cần ai quyết" (stub model trả đúng mẫu của prompt dựng ra); prompt dựng ở 5 công tắc tắt × L1..L3 không chứa mẫu "Căn cứ" và "Cần ai quyết" (thêm vào danh sách cặp câu của AC-6); ca có việc bị từ chối (môi trường, danh mục, điều cấm cứng) → 1 dòng việc người làm tay trong "Hướng xử lý", 0 tiêu đề "Cần ai quyết"; "Chờ duyệt" có đúng 1 dòng cho mỗi đề xuất vừa tạo** | Lời người (H-4); A5-1, A5-4 |
| AC-66 `[changed]` (một câu) | Thay đoạn "Việc nhóm (b) mà bộ thực thi từ chối (AC-36, câu áp chót) không thành câu hỏi mà ghi ở "Cần ai quyết", 0 thay đổi dữ liệu" **bằng: "Việc nhóm (b) mà bộ thực thi từ chối (AC-36, câu áp chót) không thành câu hỏi và không có mục riêng: ghi trong "Hướng xử lý" như một việc người phải làm tay kèm lý do, 0 thay đổi dữ liệu".** Mọi chữ khác của AC-66 giữ | Giữ test của AC-66. **Sửa ca "bộ thực thi từ chối": đích không đổi, "Hướng xử lý" có dòng việc người làm tay và lý do, comment không có tiêu đề "Cần ai quyết"; câu của prompt cho model ghi "Cần ai quyết" khi tool trả `ok=false` (worktree `prompts.py:257-270`) không còn trong prompt dựng ra** | Lời người (H-4); A5-4 |

### 3.2 AC-23, AC-32, AC-38, AC-48

| Mã | Tiêu chí mới (đo được) | Cách kiểm | Vì sao đổi |
|---|---|---|---|
| AC-23 `[changed]` | Mọi chữ của phụ lục 2 và 3 giữ, **thêm hai điều.** **(1) Cách đếm "comment kết quả" (theo `ADR-038.md` Quyết định 1-3):** "comment kết quả" là dòng `Info` do dòng kết quả của đề xuất ghi, nhận ra bằng chữ mở đầu của nó (không bằng việc dòng có chứa tên đề xuất); đúng 1 dòng như vậy mỗi kết cục cuối (xong, lỗi, hết hiệu lực, hoàn tác, từ chối). Khối có khởi động lại hệ thống (CHG-002, FEAT-004 AC-46 (b)) có thêm đúng 1 dòng `Info` báo trước khi khởi động lại, đến trước dòng kết quả; dòng báo không phải comment kết quả và không vào số đếm. Đề xuất loại bản ghi và mọi kết cục Từ chối không có dòng báo. Cách đếm này áp cho mọi chỗ spec viết "đúng 1 comment kết quả" (AC-33, AC-35, AC-68). **(2) Thông báo từ chối của lần đưa hướng** (việc từ chối vì môi trường hoặc danh mục, "cần làm trên site test", AC-12) gộp vào comment hướng xử lý như việc người phải làm tay kèm lý do trong "Hướng xử lý" (AC-65 (a)), không có mục "Cần ai quyết" | Giữ ma trận 9 tình huống của phụ lục 3. **Thêm: (a) khối có `.py`, `migrate`, `restart`, áp dụng thành công (khởi động giả) → trên phiếu đúng 1 dòng kết quả (đếm theo chữ mở đầu, không theo tên đề xuất) và đúng 1 dòng báo; số đếm "comment kết quả" = 1; (b) đề xuất bản ghi × {xong, lỗi, hết hiệu lực, hoàn tác} và Từ chối × {bản ghi, code, lệnh} → 0 dòng báo, đúng 1 dòng kết quả; (c) dòng báo không kích hoạt lần chạy bot nào (như comment kết quả); (d) ca việc bị từ chối vì `production` → 1 dòng việc người làm tay trong comment hướng, không có comment riêng**. Test đếm dòng báo là ràng buộc của ADR-038 cho CHG-002 và `test_architecture.py`; FEAT-007 chỉ thêm cách đếm | `ADR-038.md` (proposed): dòng báo của CHG-002 chứa tên đề xuất nên phép đếm "chứa tên" báo 2 cho mọi khối có restart. H-4 cho điều (2) |
| AC-32 `[changed]` (một cụm) | Thay "bot chỉ đăng comment đề xuất (chẩn đoán, phương án, độ tin cậy, căn cứ)" **bằng "bot chỉ đăng comment hướng xử lý bằng chữ (chẩn đoán, phương án, độ tin cậy)"**; mọi chữ khác của AC-32 (phụ lục 1) giữ | Giữ test tập tool ở L1 cho 6 đầu mục. **Thêm: phiếu ở L1 → comment hướng không có tiêu đề "Căn cứ"** | H-4 |
| AC-38 `[changed]` (một cụm) | Thay "Lưu bị chặn khi thiếu mục bắt buộc của phần đó" áp cho phần lập luận: **mục bắt buộc của phần lập luận là "Nhận định" và "Hướng xử lý"; mục "Căn cứ" không còn bắt buộc (và không có trong bản dựng sẵn)**. Giá trị ghi đè đã lưu trước đây có "Căn cứ" vẫn lưu lại được, không bị coi là sai; hệ thống không lọc chữ model tự viết (A5-9). Mọi chữ khác của AC-38 giữ | Giữ test của AC-38. **Thêm: ghi đè lập luận có "Nhận định" và "Hướng xử lý", không có "Căn cứ" → lưu được; thiếu "Hướng xử lý" → bị chặn; ghi đè cũ có đủ ba mục → lưu lại được; bản dựng sẵn (rỗng) không có mẫu "Căn cứ"** | H-4; A5-9 |
| AC-48 `[changed]` (một cụm) | Thay "yêu cầu nêu nguồn trong "Căn cứ"" **bằng "yêu cầu nêu nguồn (CSKT, HDSD, phiếu cũ) ngay trong nhận định hoặc hướng xử lý, không có mục riêng"**; mọi chữ khác của AC-48 giữ | Giữ test 5 phiếu Resolved. **Thêm: phiếu có kết quả tra cứu → văn bản comment hướng có tên nguồn đã dùng, không có tiêu đề "Căn cứ"** | H-4 |

### 3.3 AC-39, AC-69

| Mã | Tiêu chí mới (đo được) | Cách kiểm | Vì sao đổi |
|---|---|---|---|
| AC-39 `[changed]` | [C5, N-1] **Chữ của phụ lục 2 giữ, thay ba đoạn.** **(1)** Thay "Mỗi đề xuất hiện hành động, đích, giá trị trước và đề xuất, độ tin cậy, căn cứ, ba nút" **bằng: "Mỗi đề xuất hiện hành động, đích, giá trị trước và đề xuất, độ tin cậy, căn cứ của đề xuất (Q-18), căn cứ chế độ (AC-33) và một nút "Duyệt ngay", là nút chính và là hành động đồng ý duy nhất trên đề xuất; Sửa và Từ chối giữ như cũ, là nút phụ, nghĩa không đổi. Bấm "Duyệt ngay" là bot tự làm (AC-68), không còn bước nào khác của người"**. **(2)** Thay "Khi (5) tắt, Duyệt và Từ chối qua bước xác nhận ngay trong ngăn; khi (5) bật, một lần bấm, không bước xác nhận" **bằng: "Khi (5) tắt, "Duyệt ngay" và Từ chối qua bước xác nhận ngay trong ngăn (từ ngăn đã mở tới lúc việc được áp dụng: 2 thao tác, bấm và xác nhận); khi (5) bật, một lần bấm, không xác nhận (1 thao tác)"**; ngăn chỉ nhận một giá trị đúng/sai suy từ (5), như cũ. **(3)** Thay "Chỉ người được giao phiếu (AC-35) thấy mục này; người chỉ-`Agent` không được giao thì mục không hiện; Instructor và System Manager thấy mọi đề xuất qua form" **bằng: "Mục "Đề xuất chờ duyệt" và nút "Duyệt ngay" hiện cho đúng tập người duyệt hợp lệ loại bản ghi của AC-35 (a): người đang được giao phiếu (việc gán còn mở) và người có `ERP AI Instructor`; với Instructor mục liệt kê mọi đề xuất bản ghi của phiếu đang mở. Người chỉ-`Agent` không được giao, người tạo phiếu, tài khoản agent, Administrator, Guest: mục không hiện, nút không có, và Duyệt bị từ chối ở máy chủ (AC-35). System Manager không có `ERP AI Instructor` xem đề xuất qua form như AC-35 nhưng không có nút. Đề xuất sửa code và lệnh `bench` không có nút trong ngăn: duyệt ở form Desk theo AC-35 (b) (A5-8, Q-21)"**. Người được giao mở được form đề xuất ở Desk (chỉ đọc), như cũ | Giữ kiểm 15 bước của `design-addendum-2-U7b-U8.md:383-401` (site dev, ảnh, dòng nhật ký). **Thêm: ma trận {được giao không có role, Instructor không được giao, Instructor và được giao, chỉ-`Agent` không giao, người tạo phiếu, System Manager không Instructor} × {đề xuất bản ghi của phiếu, đề xuất code của phiếu}: mục hiện đúng cho hai nhóm đầu, số nút "Duyệt ngay" = số đề xuất bản ghi chờ, đề xuất code → 0 nút trong ngăn; Instructor không được giao bấm "Duyệt ngay" → áp dụng (1 comment kết quả, 1 mục nhật ký, 0 lời gọi model); (5) tắt → 2 thao tác, (5) bật → 1; người bị gỡ role giữa lúc bấm và lúc job chạy → "Lỗi", 0 thay đổi (AC-35); gọi Duyệt trực tiếp bằng tài khoản không thuộc tập → bị từ chối, trạng thái đứng yên** | Lời người: "1 nút duyệt ngay trên ticket (trao đổi với bot) nếu người đó có role hay là người đc assign" (H-5, H-6). A5-2, A5-5, A5-6, A5-7, A5-8 |
| AC-69 `[changed]` (bước kiểm) | Chữ của phụ lục 3 giữ. **Thêm vào kiểm có đầu ra: ba bước.** **(6)** ở bước (1), dán ảnh comment hướng: có nhận định, hướng xử lý, "Đã làm", "Chờ duyệt"; không có tiêu đề "Căn cứ" và "Cần ai quyết". **(7)** ở bước (2), dán ảnh ngăn: đề xuất có nút "Duyệt ngay"; đăng nhập một người có `ERP AI Instructor` không được giao phiếu: thấy mục và bấm được; đăng nhập một người chỉ-`Agent` không được giao: không thấy mục. **(8)** ghi số thao tác từ ngăn đã mở tới comment kết quả: 2 khi (5) tắt, 1 khi (5) bật (đặt lại cấu hình sau khi thử) | Kiểm có đầu ra như phụ lục 3 (`ui: false`: người thử thao tác, dán ảnh, nhật ký). Chỉ nghiệm thu sau khi U7a, U7b vào `develop` cùng lượt | Gắn H-4..H-6 vào bước kiểm đầu-cuối |

## 4. NFR

NFR-1, NFR-2, NFR-3, NFR-4 (cả hai lần đổi) giữ nguyên chữ. Lượt áp dụng sau "Duyệt ngay" không gọi model và không tính vào số lần chạy bot (NFR-2, AC-68) như cũ. File này không đặt NFR mới và không đặt ngưỡng thời gian nào (A3-8): số thao tác "2 khi (5) tắt, 1 khi (5) bật" lấy từ AC-39 hiện hành, không phải số mới.

## 5. Giả định mới (decide mode, đủ 4 trường)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A5-1 | "Căn cứ" và "Cần ai quyết" là hai mục của mẫu comment hướng xử lý; bỏ cả hai; giữ "Nhận định", "Hướng xử lý", "Đã làm", "Chờ duyệt" | Lời người nêu đúng hai tên đó; hai mục có mặt ở mẫu (`prompts.py:124`, `:126` trên `develop`) | Bỏ thêm "Nhận định" | Đổi AC-65 (a) |
| A5-2 | "Role" là `ERP AI Instructor` (tập người duyệt của AC-35 (a)); không thêm role nào | AC-35 (a) đã có đúng hai nhóm người duyệt bản ghi: người được giao và `ERP AI Instructor`; lời người ("có role hay là người được assign") khớp | Mọi người có role `Agent` (agent Helpdesk) duyệt đề xuất của mọi phiếu họ thấy; hoặc `System Manager` | Q-22; đổi AC-35 (a), AC-39 (3) |
| A5-3 | "Căn cứ" của từng đề xuất (AC-22, AC-33) và căn cứ chế độ (A4-3) giữ | Chúng nằm ở comment đề xuất và ngăn, là thứ người duyệt đọc trước khi bấm (C5); lời người nói về comment của bot (phương án), không nói bỏ thông tin duyệt; căn cứ chế độ là điều kiện an toàn AR3-5 | Bỏ luôn căn cứ của đề xuất | Q-18; đổi AC-22, AC-33, AC-39 (1) |
| A5-4 | Việc bot không làm được (từ chối vì môi trường, danh mục, điều cấm cứng, bộ thực thi) nằm trong "Hướng xử lý" như việc người làm tay kèm lý do | AC-67 đã viết đúng cho ba ca; cùng một chỗ, không thêm mục | Một mục riêng khác tên | Đổi AC-66, AC-23 (2) |
| A5-5 | "1 nút" là một nút "Duyệt ngay" cho mỗi đề xuất; không có nút duyệt cả gói; Sửa và Từ chối giữ | A3-3 (phụ lục 3): trạng thái, chuỗi duyệt (AC-36) và hết hiệu lực (AC-33) tính theo từng hành động | Một nút "Duyệt tất cả" cho mọi đề xuất chờ của phiếu | Q-19; đổi AC-39, A3-3 |
| A5-6 | Hộp xác nhận giữ theo công tắc (5), mặc định tắt: "Duyệt ngay" khi (5) tắt có một bước xác nhận | N-1 (người đã quyết: 5 công tắc quyền mặc định tắt); Q-12 chưa được trả lời; AC-68 vẫn đạt vì sau xác nhận không còn bước nào của người | Bật (5) mặc định cài mới | Q-20; đổi AC-1, test cài mới của T2 |
| A5-7 | Người có `ERP AI Instructor` thấy mục và nút trong ngăn cả khi không được giao phiếu (mở rộng AC-39 "chỉ người được giao") | Lời người: "nếu người đó có role ... duyệt"; AC-35 (a) đã cho Instructor quyền duyệt bản ghi; chữ cũ của AC-39 hạn chế hiển thị, không hạn chế quyền | Giữ ngăn chỉ cho người được giao; Instructor duyệt ở form | Đổi AC-39 (3); architect xác nhận ADR-035 QĐ 2-4 (mục 7) |
| A5-8 | Đề xuất sửa code và lệnh `bench` không có nút trong ngăn; duyệt ở form Desk; AC-35 (b) giữ | Mặc định an toàn của team-leader (journal 18:16 (b)); FEAT-004 AC-22 đòi xem diff trước khi duyệt code | Nút "Duyệt ngay" cho cả code và lệnh trong ngăn | Q-21; `--amend` AC-35 và AC-39, kéo theo FEAT-004 AC-5 |
| A5-9 | Hệ thống không lọc chữ model tự viết: bỏ mục khỏi mẫu của prompt và khỏi những gì hệ thống tự thêm, nhưng nếu một bản ghi đè prompt cũ còn mẫu "Căn cứ" thì bot vẫn viết theo ghi đè | AC-38: ghi đè do người đặt, không bị chặn quá mức; lọc chữ model là thêm cơ chế | Hệ thống cắt tiêu đề "Căn cứ" khỏi chữ model viết | Thêm bộ lọc (AC mới); người xóa chữ cũ trong ghi đè |
| A5-10 | Khi bot cần người chọn giữa hai phương án, bot chọn một phương án (khuyến nghị) và nêu phương án kia trong "Hướng xử lý"; người đổi hướng bằng "Sửa", Từ chối hoặc `@ai`; không có mục hỏi riêng | Lời người: "bot đưa ra phương án"; AC-22 và AC-28 giữ cho câu hỏi khi độ tin cậy thấp hoặc tách phiếu | Thêm lại một mục hỏi | Đổi AC-65 (a) |
| A5-11 | Thay đổi này tới site cùng FEAT-007 (sau G5); `develop` hiện tại và site đang chạy không đổi trong lúc đó | Journal 18:16 (f): mẫu comment trên `develop` thuộc chuỗi `prompts.py` của FEAT-007 và CHG-002 | Việc riêng trên `develop` để bỏ hai mục sớm | Mở việc riêng (CHG) |
| A5-12 | Chữ AC-23 theo ADR-038 là chữ của quyết định đã có (trạng thái `proposed` cùng ADR); analyst không thêm quyết định | Lệnh giao việc: "chữ AC-23 theo ADR-038" | — | Nếu ADR-038 bị bác: chữ cũ "chứa tên đề xuất" của AC-23 hiệu lực lại; đổi mục 3.2 (1) |

## 6. Câu hỏi nghiệp vụ không chặn cho người

Không câu nào chặn build: mỗi câu có mặc định mà team dựng theo file này. Decide mode: không có `questions.md` (không có điểm lớn hoặc không lùi được); team-leader chuyển danh sách này (cùng Q-1..Q-13 của các phụ lục trước) cho người, trả lời lúc nào cũng được. Q-14..Q-17 chép từ journal vào đây (chưa có phụ lục nào chứa); Q-18..Q-22 mới.

**Q-14. Phiếu tạo trước FEAT-007 không có độ tin cậy số. `@ai` trên phiếu cũ thì xử lý thế nào?** (`journal-part16.md:15`; N-1 của `arch-review-design-w1a.md:46`; ADR-037 QĐ 1)
- Mặc định đang dựng: **(a) giữ**: phiếu cũ đã có kết quả phân loại → `@ai` phân loại lại một lần rồi chạy bình thường; phiếu cũ chưa có kết quả phân loại → bot chỉ hỏi.
- Các lựa chọn: (a) giữ (mặc định, khuyến nghị); (b) phiếu cũ không bao giờ được phân loại lại bằng `@ai`: bot chỉ trả lời rằng cần phân loại tay trước; (c) phiếu cũ chạy bình thường không qua ngưỡng tin cậy (AC-22).
- Hệ quả: (a) mỗi phiếu cũ tốn thêm một lượt phân loại trong lần `@ai` đầu; (b) an toàn nhất nhưng người phải phân loại tay hàng loạt phiếu cũ; (c) bot hành động trên phiếu cũ mà không có số đo tin cậy, trái ý AC-22.
- Cách đảo: (b), (c) đổi quy tắc ở U4b/U6b (ADR-037 QĐ 1) và chữ AC-22 (phạm vi); chưa dựng nên chi phí nhỏ.

**Q-15. Một tin của người tạo bị bỏ qua vì chạm giới hạn ngày hoặc không gửi được: hôm sau có chạy lại không?** (`journal/FEAT-007.md` dòng "04:16 quyết định" (d); `arch-review-design-w1b-r2.md:81` (m-5); ADR-033 QĐ 4)
- Mặc định đang dựng: **(a) không chạy lại**: tin đó coi là đã xử lý (có một dòng log nêu lý do bỏ qua); người muốn bot đọc lại thì `@ai` hoặc trả lời lại.
- Các lựa chọn: (a) không chạy lại (mặc định, khớp ADR-033 QĐ 4); (b) hôm sau chạy lại một lần cho tin bị bỏ qua vì giới hạn ngày; (c) như (b) cho cả tin không gửi được.
- Hệ quả: (a) một tin người tạo có thể không bao giờ được bot đọc nếu người không nhắc lại; As-Built ghi cạnh AC-41; (b), (c) thêm một đường chạy theo lịch và phải tính vào giới hạn ngày.
- Cách đảo: (b), (c) cần designer đổi khóa sự kiện của U6b và đổi chữ AC-41; sau khi dựng thì tốn hơn.

**Q-16. Phân loại lại gửi tối đa 5 tin đến sau (mỗi tin ≤ 200 ký tự) cho model trước khi biết nhóm của phiếu. Phiếu sau đó rơi vào nhóm bị loại thì các đoạn đó đã gửi. Nhận không?** (`journal/FEAT-007.md` dòng "04:24 quyết định" (b); A-21)
- Mặc định đang dựng: **(a) nhận**, cùng căn cứ với A-21: lần phân loại đầu cũng gửi tiêu đề và mô tả trước khi biết nhóm.
- Các lựa chọn: (a) nhận (mặc định); (b) phân loại lại chỉ theo tiêu đề và mô tả, không gửi tin đến sau; (c) gửi tin đến sau chỉ khi phiếu đã có phân loại không thuộc nhóm loại trừ.
- Hệ quả: (a) rủi ro NFR-1 còn lại: nội dung một tin ngắn của phiếu nhóm nhạy cảm đã tới model trước khi bị loại (đã có che dữ liệu nhạy cảm, NFR-8); (b) bỏ rủi ro nhưng phân loại lại kém chính xác khi chỉ có tin mới cho biết đầu mục; (c) bỏ rủi ro cho phiếu đã biết nhóm, phiếu chưa phân loại vẫn như (b).
- Cách đảo: một thay đổi ở bước phân loại lại của U4b (T113) và chữ A-21; chưa dựng.

**Q-17. Báo cáo 08:00 đếm "việc bot đã làm" theo cách nào?** (`docs/team/journal/FEAT-007.pending.md:3` (e); `design-w1-fixes-18.md` điểm 1-2; ADR-024)
- Mặc định đang dựng: **(a) như designer ghi**: "đóng" đếm theo lần bot đổi trạng thái (một phiếu Resolved rồi Closed trong ngày tính 2); `set_classification` ở lượt lý luận tính vào "phân loại"; comment vòng đời tính "comment", thông báo cho người tạo tính "khác"; "trả lời" bằng 0 cho tới khi U6b có công cụ trả lời riêng (T166).
- Các lựa chọn: (a) như trên (mặc định); (b) "đóng" đếm theo phiếu (một phiếu Resolved rồi Closed tính 1); (c) bỏ cột "khác" khỏi báo cáo.
- Hệ quả: (a) người đọc báo cáo thấy số "đóng" có thể lớn hơn số phiếu đóng; cột "trả lời" bằng 0 tới T166; As-Built ghi; (b) sát cách người đếm hơn nhưng đổi luật KPI 3 (ADR-024); (c) báo cáo gọn hơn nhưng mất chỗ cho việc không xếp loại.
- Cách đảo: (b), (c) sửa T52 và T166; T52 đang làm vòng 2/3 nên đổi sớm rẻ nhất.

**Q-18. Bỏ "Căn cứ" khỏi comment hướng xử lý (đã làm, H-4). "Căn cứ" của từng đề xuất và dòng căn cứ chế độ cũng bỏ theo không?** (AC-22, AC-33, A4-3, A5-3; lời người "bỏ Căn cứ")
- Mặc định đang dựng: **(a) giữ**: comment từng đề xuất và ngăn vẫn có căn cứ (không rỗng) và căn cứ chế độ; chỉ mục "Căn cứ" của comment hướng xử lý bị bỏ.
- Các lựa chọn: (a) giữ (mặc định, khuyến nghị: người duyệt cần thấy vì sao trước khi bấm "Duyệt ngay"); (b) bỏ "Căn cứ" của đề xuất; vẫn giữ căn cứ chế độ (an toàn); (c) bỏ cả hai, ngăn chỉ còn hành động, đích, giá trị, độ tin cậy.
- Hệ quả: (a) comment đề xuất vẫn có một dòng căn cứ; (b) bớt một dòng nhưng người duyệt mất lý do của model; AC-22 phải bỏ điều kiện "căn cứ không rỗng"; (c) mất điều kiện an toàn AR3-5 (người duyệt thấy "không có dòng danh mục"): không khuyến nghị, cần architect.
- Cách đảo: (b) đổi AC-22, AC-33, AC-39 (1) và T100 (chưa dựng); (c) thêm ADR amendment.

**Q-19. "1 nút duyệt": một nút "Duyệt ngay" cho mỗi đề xuất, hay một nút duyệt cả phương án (mọi đề xuất chờ của phiếu)?** (A3-3, A5-5; lời người "1 nút duyệt ngay trên ticket")
- Mặc định đang dựng: **(a) mỗi đề xuất một nút "Duyệt ngay"**; Sửa và Từ chối giữ.
- Các lựa chọn: (a) mỗi đề xuất một nút (mặc định, giữ A3-3); (b) thêm một nút "Duyệt tất cả" ngoài nút của từng đề xuất; (c) chỉ một nút duyệt tất cả, bỏ nút từng đề xuất.
- Hệ quả: (a) phiếu có 3 đề xuất thì bấm 3 lần (khi (5) bật) hoặc 6 thao tác (khi (5) tắt); (b) bấm một lần cho cả gói nhưng mỗi đề xuất vẫn áp dụng và có kết quả riêng: 1 phần lỗi thì phần kia vẫn chạy; chuỗi duyệt (AC-36) tính theo từng đề xuất; (c) người không loại được từng việc trước khi duyệt: không khuyến nghị.
- Cách đảo: (b) thêm một nút ở U7b và ca test "duyệt cả gói": designer thiết kế; (c) kèm đổi A3-3.

**Q-20. Hộp xác nhận khi bấm "Duyệt ngay": lời người "tự làm luôn" có nghĩa bỏ hộp xác nhận (một lần bấm) không?** (Q-12; công tắc (5); AC-11; A5-6)
- Mặc định đang dựng: **(a) giữ Q-12 (a)**: công tắc (5) tắt mặc định, có hộp xác nhận; người cần bật (5) ở site mình, cảnh báo AC-4 hiện.
- Các lựa chọn: (a) giữ tắt (mặc định, theo N-1); (b) site `miyano` tự bật (5) sau khi cài (không đổi mặc định cài mới); (c) đổi mặc định cài mới thành bật.
- Hệ quả: lời mới của người nghiêng về (b) hoặc (c) ("1 nút ... tự làm luôn"); (b) không đổi mã, chỉ một lần lưu cấu hình; (c) đảo một quyết định của người (N-1), đổi AC-1 và test cài mới của T2 (đã merge).
- Cách đảo: tắt lại công tắc; (c) cần `--amend` AC-1, AC-3, AC-11.

**Q-21. Người được giao phiếu có được duyệt đề xuất sửa code và lệnh `bench` ngay trên phiếu không?** (AC-35 (b); FEAT-004 AC-5; ADR-012 QĐ 4; A5-8)
- Mặc định đang dựng: **(a) không**: code và lệnh `bench` chỉ người có `ERP AI Instructor` duyệt (AC-35 (b) giữ nguyên), duyệt ở form Desk sau khi xem diff; ngăn không có nút cho hai loại này.
- Các lựa chọn: (a) giữ (mặc định, khuyến nghị: lệnh `bench` và sửa code chạy trên server ngoài phạm vi phiếu); (b) người được giao duyệt code, không duyệt lệnh `bench`; (c) người được giao duyệt cả hai, "Duyệt ngay" có trong ngăn.
- Hệ quả: (a) người được giao không có nút cho việc sửa code; họ nhờ Instructor; (b)/(c) tăng bề mặt rủi ro (người tự giao phiếu cho mình, Q-2, duyệt được việc sửa code), đảo FEAT-004 AC-5 (đang chạy ở `develop`) và ADR-012 QĐ 4.
- Cách đảo: (b)/(c) `--amend` AC-35, AC-39 (3), thêm amendment cho ADR-012 (architect), kéo theo test FEAT-004; chưa dựng U7b nên chi phí phía FEAT-007 nhỏ, phía FEAT-004 lớn.

**Q-22. "Người đó có role": role nào được duyệt?** (AC-35 (a); A5-2)
- Mặc định đang dựng: **(a) `ERP AI Instructor`** (cùng người duyệt hiện có của AC-35 (a)), cộng người đang được giao phiếu.
- Các lựa chọn: (a) `ERP AI Instructor` (mặc định); (b) mọi người có role `Agent` (agent Helpdesk) thấy phiếu đều duyệt được đề xuất bản ghi của phiếu đó; (c) thêm `System Manager`.
- Hệ quả: (a) giữ nguyên tập người duyệt; (b) nới lớn: bất kỳ agent nào duyệt việc ERP trên mọi phiếu họ đọc được, kể cả phiếu của người khác; rủi ro R-S5 (Q-13) tăng; (c) System Manager đã thấy đề xuất qua form, thêm quyền duyệt là nới nhỏ.
- Cách đảo: (b)/(c) `--amend` AC-35 (a), AC-39 (3) và architect soát ADR-023, ADR-035 QĐ 1-4.

Q-13 (phụ lục 4) tăng thêm trọng lượng sau H-6: người được giao hoặc Instructor duyệt trong một thao tác; chưa đổi chữ Q-13; As-Built ghi cả hai.

## 7. DoD, bảng phủ, đơn vị và task bị chạm, việc cho designer, architect, tech-lead

**DoD (phần build), thêm vào các file trước:**
- `[changed]` AC-23, AC-32, AC-38, AC-39, AC-48, AC-65 (a), AC-66, AC-69 đạt theo chữ ở mục 3; chữ đó thay chữ của các file trước cho các đoạn nêu. Số AC giữ ở 66. Mỗi AC đổi có ít nhất 1 test tự động hoặc bước kiểm có đầu ra (STD-TEST-2); AC-39 và AC-69 chỉ nghiệm thu giao diện sau khi U7a, U7b vào `develop` cùng lượt.
- AC-22, AC-33, AC-35 (cả (a) và (b)), AC-67, AC-68, A4-3 vẫn đạt theo chữ của các file trước; test hiện có của chúng không đổi (Q-18, Q-21 giữ mặc định).
- Danh sách test bị sửa vì spec đổi (NFR-8), mỗi chỗ ghi lý do theo STD-TEST-5. **Đã merge, ghim chữ cũ:** `erp_ai/agent/test_prompts.py` (mẫu cũ ở `:55-57`, `:74-79`, `:146`), `erp_ai/agent/test_classification.py:505`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:2345`, `:2636` (trên `team/FEAT-007` @ `05237bb`); sửa theo mục 3, qua task chèn của tech-lead (task cũ T72, T78, T79 đã tick, không mở lại). **Chưa dựng:** test của T103, T104, T116, T118 (hai tiêu đề và dòng "Chờ duyệt"), T157 (nguồn nêu trong nhận định), U7b (nút, ma trận hiển thị), U7a nếu Q-18 đảo.
- Phần sau G4: As-Built ghi Q-14..Q-22 và câu trả lời hoặc "chưa trả lời, chạy mặc định"; tài liệu người dùng mô tả "comment của bot: nhận định, hướng xử lý, đã làm, chờ duyệt", nút "Duyệt ngay" trong ngăn "Trao đổi với bot", ai thấy nút (người được giao, người có `ERP AI Instructor`), đề xuất sửa code và lệnh duyệt ở form; ghi cả việc mẫu cũ còn trên `develop` tới khi FEAT-007 lên site (A5-11).

**Bảng phủ.** Chỉ ghi dòng chạm vào; dòng khác giữ như các file trước:

| Dòng | AC sau addendum 5 | Ghi chú |
|---|---|---|
| H3 | AC-23 `[changed]`, AC-65 | một hướng mỗi phiếu; đếm comment kết quả theo ADR-038 |
| H-1 | AC-65 `[changed]` (a) | mục của comment hướng |
| H-3 | AC-39 `[changed]`, AC-67, AC-68 | nút "Duyệt ngay", người duyệt |
| H-4, H-5, H-6 | xem mục 2 | ba câu của lời người 18:16 |
| H2, H9, G8 | AC-22 giữ, AC-38 `[changed]`, AC-48 `[changed]` | mục "Căn cứ" không còn là mục bắt buộc hay nơi nêu nguồn |
| C5 | AC-39 `[changed]` | ngăn cho Instructor; căn cứ của đề xuất còn hiện |

C1–C6, G1–G13, H1–H14 vẫn được phủ: file này không bỏ và không chuyển tiêu chí nào.

**Đơn vị và task bị chạm** (từ `tasks.md` @ vòng 19, chỉ đọc bằng tìm kiếm; chưa thay file nào).
- *Đã merge (đã tick), cần sửa chữ qua task chèn:* U1 (prompt nền): T72 (độ tin cậy số, mục bắt buộc của phần lập luận trong `erp_ai_setting.py`), T78 (quy tắc 6), T79 (khối VIẾT COMMENT, khối chỉ-làm-việc có câu "Cần ai quyết", `prompts.py:130-136`, `:257`, `:270`) cùng các test ở danh sách trên. Không đổi mặc định hay dữ liệu.
- *Chưa dựng, chạm trực tiếp (giữ tới khi designer phán):* U4b: T103 (hàm ghi comment hướng: chữ dự phòng, thứ tự mục), T104 (từ chối dấu hiệu, giữ nhận định), T105 (dòng "Chờ duyệt"; lời trỏ tới ngăn), T116 (lượt cuối gộp comment hướng), T117 (lỗi sau định tuyến: chữ việc đã làm), T118 (kiểm đầu-cuối hai tiêu đề); prompt suy luận: T157 (khối ba nguồn: "nêu nguồn trong Căn cứ", AC-48); U7b: ngăn, nút "Duyệt ngay", hiển thị cho Instructor (đợt 2, chưa có số task); U7a: chữ comment đề xuất chỉ nếu Q-18 đảo; AC-69: bước kiểm đầu-cuối.
- *Chung file `prompts.py`, chưa thấy chữ hai mục trong dòng task:* T106, T107, T156, T170: kiểm khi designer phán (chỉ chạm nếu đoạn VIẾT COMMENT nằm trong phạm vi sửa).
- *Chạm nhẹ, chỉ khi Q-18 hoặc nhãn liên kết đổi:* U3: T89 và `propose_change._comment` (comment đề xuất); T100 (comment đề xuất cần căn cứ).
- *Không chạm:* T80..T83 (vòng 19), T84..T88, T91..T93 (nhật ký, cổng (5)), T101, T110 (thông báo trạng thái), T169, T171 (BA note).

**Việc cho designer, architect, tech-lead (không phải của analyst).**
- *Designer* (cùng lượt S-4, S-6, S-7, AD3-8..AD3-10 đang chờ): chữ mẫu VIẾT COMMENT mới; chữ mục bắt buộc của phần lập luận (AC-38) và cách một ghi đè cũ còn "Căn cứ" được xử lý; thứ tự và chữ comment hướng của hàm ghi (T103, T116); thiết kế nút "Duyệt ngay", bố cục ngăn, hiển thị cho Instructor (U7b); chữ dòng "Chờ duyệt" trỏ tới ngăn; chữ nguồn tra cứu (T157). Task nào ở nhóm "chưa dựng, chạm trực tiếp" giữ tới khi có thiết kế.
- *Architect:* chỉ cần một xác nhận ngắn cho AC-39 (3): quy tắc "ai thấy mục trong ngăn" của ADR-035 QĐ 2-4 và `design-addendum-2-U7b-U8.md` (A-U7b-4) cho phép Instructor thấy mục và nút, hay cần amendment; không có ADR mới dự kiến. ADR-023 (người duyệt), ADR-036 (dấu hiệu comment hướng, "Hướng xử lý" giữ) và ADR-037 không bị chạm; ADR-038 là chữ quyết định của AC-23. Nếu Q-18 (c), Q-21 (b)/(c) hoặc Q-22 (b) được người chọn thì cần architect.
- *Tech-lead:* `/team:plan --insert` sau designer: task chèn sửa chữ T72, T78, T79 (mẫu comment, mục bắt buộc, câu "Cần ai quyết") và các test ở danh sách NFR-8; ghi vào preflight vòng 20 các task chung file `prompts.py`; chép ràng buộc ADR-038 vào task U7a có `result_comment.py` (đã có ở ADR).

## 8. Out of scope (thêm)

Bỏ hai mục khỏi mẫu comment đang chạy trên `develop` ngay (A5-11; mở việc riêng nếu người muốn); nới AC-35 (b) hoặc đưa nút "Duyệt ngay" cho đề xuất sửa code và lệnh (Q-21); nút duyệt cả gói (Q-19); đổi mặc định công tắc (5) (Q-20); thêm role duyệt (Q-22); bỏ "Căn cứ" của từng đề xuất (Q-18); bộ lọc chữ model tự viết (A5-9); ngưỡng thời gian từ bấm tới kết quả (A3-8); chọn một trong hai cách siết của Q-13; bố cục ngăn, chữ nút ngoài "Duyệt ngay", tên hàm, tên trường, thứ tự mục của comment (việc của designer); mọi AC ngoài AC-23, AC-32, AC-38, AC-39, AC-48, AC-65 (a), AC-66, AC-69.
