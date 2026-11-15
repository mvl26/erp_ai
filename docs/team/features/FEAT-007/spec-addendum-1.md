Feature: FEAT-007
Stage: analyze
Author-agent: analyst
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G1 không áp dụng cho FEAT-007 (chỉ có G5). Addendum này chưa được duyệt, giống spec.md. -->

# Spec addendum 1 FEAT-007 — đối chiếu với FEAT-004 Amendment 2, CHG-001 và ADR-023

**Quy tắc đọc.** File này thắng `spec.md` ở mọi chỗ hai file khác nhau. Chỗ nào addendum không nhắc thì `spec.md` giữ nguyên. Không có dòng nào của `spec.md` bị xóa: mỗi AC bị đổi hoặc bỏ được giữ nguyên bản trong `spec.md` và được đánh dấu ở đây bằng `[changed]` hoặc `[dropped, owner FEAT-004 AC-n]`. "FEAT-004 AC-n" là tiêu chí của `docs/team/features/FEAT-004/spec.md` mục "Amendment 2 — 2026-11-14" (N-7); "AC-n" không kèm tên là của FEAT-007.

**Lý do viết.** Bản giao việc đầu tiên của spec.md có trước bốn file này, nên spec.md không nhắc tới chúng. Lúc 10:11 ngày 2026-11-14 một phiên khác đã commit: FEAT-004 Amendment 2 (N-1..N-10, FEAT-004 AC-1..AC-35), `docs/team/features/CHG-001/spec.md` (con trỏ tới Amendment 2), `docs/team/features/CHG-001/arch-impact.md` và `docs/team/adr/ADR-023.md` (biện pháp M1–M5, quyết định 6 còn mở). Chúng được build song song trên nhánh `team/FEAT-004` và bao phủ cùng năm quyền C1–C5.

**Giả thuyết (độ tin cậy 80%).** Hai bộ tài liệu mô tả cùng năm quyền; 3 AC của FEAT-007 là bản trùng và 15 AC hoặc giả định khác chồng một phần; và có 7 chỗ quyết định N-1 của người đòi điều khác Amendment 2 hoặc ADR-023. Chưa tới 90% vì: chỉ đọc spec và ADR, chưa đọc mã trên `team/FEAT-004` (đang build); ADR-023 ở trạng thái `proposed` và quyết định 6 còn mở; cả hai spec chưa được duyệt (G1 tắt). Không ghi `.team/current.json` (phiên khác đang giữ).

**Đã có sẵn, không cần hỏi (nguồn).** `docs/team/features/FEAT-004/spec.md:265-458` (N-1..N-10, DoD); `docs/team/features/CHG-001/spec.md`; `docs/team/features/CHG-001/arch-impact.md`; `docs/team/adr/ADR-023.md`; `docs/team/features/FEAT-007/spec.md`, `intake.md` (N-1..N-3, QĐ-1..QĐ-5); `docs/team/features/FEAT-007/source-strategy.md:100-123,180`. Không chạy Explore: mọi điểm đối chiếu nằm ở văn bản đã đọc.

**Quyết định của người dùng làm chuẩn (N-1, `intake.md`):** đường chính làm đúng tài liệu (bot chỉ ghi vào danh mục trắng; việc ngoài danh mục phải được bấm Duyệt trên comment rồi mới làm); 5 quyền ngày 13/11 vẫn giữ nhưng là công tắc riêng, mặc định tắt, bật thì có cảnh báo và ghi log đủ. Cách hiểu từng chữ nằm ở mục 3.

---

## 1. Bảng chồng lấn: mục FEAT-007 ↔ FEAT-004 AC / ADR-023 ↔ chủ ↔ phần FEAT-007 còn thêm

"Chủ" là bên viết tiêu chí, build và kiểm mục đó; bên kia chỉ dùng lại. Mỗi dòng đúng một chủ; mục bị chia đôi thì được tách thành hai dòng con.

| # | Mục FEAT-007 | Tương ứng FEAT-004 AC / ADR-023 | Chủ | FEAT-007 còn thêm |
|---|---|---|---|---|
| O-1 | AC-1 (5 công tắc, mặc định, migrate) | FEAT-004 AC-1, AC-2, A-24 (một ô hai nghĩa); ADR-023 QĐ 4 | FEAT-007, `[changed]` | 5 công tắc độc lập; migrate đặt ba công tắc mới = tắt kể cả khi ô sửa code đang bật (xung đột K-1) |
| O-2 | AC-2 (ma trận 16 ca, 5 công tắc tắt) | FEAT-004 AC-1 (hàng "cả hai ô tắt" = bản nền), AC-2 (ma trận có chiều vượt ngân sách) | FEAT-004, `[dropped, owner FEAT-004 AC-1]` | Không. Hàng "cả 5 tắt" được giữ làm một hàng của ma trận AC-3 |
| O-3 | AC-3 (mỗi công tắc độc lập, 5 hàng) | FEAT-004 AC-2 (ba đường cấp), AC-29; ADR-023 QĐ 4 (một hàm cấp, một bảng cấp) | FEAT-007, `[changed]` | Tách công cụ bản ghi (2), khối "làm luôn" (3) và liên kết một lần bấm (5) khỏi ô sửa code (4), vẫn trong một hàm cấp |
| O-4 | AC-4 (cảnh báo khi bật, cảnh báo hằng ngày) | FEAT-004 A-23 (không cảnh báo khi bật, không cảnh báo hằng ngày) | FEAT-007, giữ nguyên AC; A-23 bị N-1 thay (xung đột K-2) | Toàn bộ AC-4 |
| O-5a | AC-5 (a), (c), (d): xóa, migrate/deploy, Purchase Invoice và Payment Entry đã submit | FEAT-004 AC-31 (không có tool xóa), AC-2(a) (tool bench chỉ khi ô code bật), AC-30 (không sửa chứng từ đã submit) | FEAT-004, `[dropped from AC-5, owner FEAT-004 AC-31]` | Không |
| O-5b | AC-5 (b): sửa Role Permission, 8 vector | FEAT-004 AC-31 (6 vai trò cấm, Role Permission, Custom DocPerm); ADR-023 QĐ 3 (M3: thêm `DocType`, `Role`; bảng con bị chặn vì `istable`) | FEAT-007, `[changed]` | 3 vector mà FEAT-004 và M3 chưa phủ (User Permission, DocShare, Property Setter đổi `permlevel`); bỏ vector `Has Role` chung (mâu thuẫn S-4) |
| O-6 | AC-6 (khối prompt theo công tắc, không câu trái nhau) | FEAT-004 AC-14 (nội dung khối đề xuất), AC-29 (khối "làm luôn" khi nhóm nào được cấp) | FEAT-007 cho điều kiện hiện khối; FEAT-004 cho nội dung khối. `[changed]` | Khối "làm luôn" chỉ hiện khi (3) bật và có nhóm ghi được cấp (xung đột K-1) |
| O-7 | AC-7 (vượt ngân sách, mọi nhóm lui về L1) | FEAT-004 AC-2 câu cuối ((a)(b) mất, (c) Toàn quyền còn); ADR-023 QĐ 4 "Ghi nhận" (giữ nguyên) | FEAT-007, `[changed]` | Chỉ vế "Toàn quyền cũng mất khi vượt ngân sách" (xung đột K-4); vế còn lại do FEAT-004 AC-2 làm chủ |
| O-8 | AC-8 (đọc chéo phiếu nhóm loại trừ) | ADR-023 QĐ 3 (một nguồn danh sách cấm của `site_api`), QĐ 6 (`call_method`); FEAT-004 AC-33 | FEAT-007, `[changed]` | Chặn ở mức bản ghi (phiếu loại trừ, cờ không dùng AI), nằm ở cùng file tool bản ghi mà M3 sửa (rủi ro xung đột merge); đường `call_method` phụ thuộc QĐ 6 (L-5) |
| O-9a | AC-10, phần công cụ bản ghi và nhóm Toàn quyền | FEAT-004 AC-34 (mỗi lời gọi một mục), AC-35 (giá trị trước/sau, người ra lệnh, 0 byte bí mật), NFR-11 | FEAT-004, `[dropped from AC-10, owner FEAT-004 AC-34, AC-35]` | Không |
| O-9b | AC-10, mọi lần ghi còn lại của bot (trường phiếu, Task, comment, trả lời, trạng thái, hành động danh mục, đề xuất bản ghi đã áp dụng, thay đổi công tắc) | FEAT-004 AC-34, AC-35 cho cùng dạng mục; ADR-023 QĐ 5 (chỉ `run_log.write_entry` được ghi nhật ký) | FEAT-007, `[changed]` | Dùng đúng dạng mục và đúng đường ghi của FEAT-004 cho các lần ghi này; thêm lý do khi bị từ chối, mã lần chạy, giá trị môi trường (L-7 về đơn vị lưu) |
| O-10a | AC-11, cơ chế liên kết (chữ ký, một lần thắng, kiểm vai trò, không GET đổi trạng thái, không hộp xác nhận ở liên kết) | FEAT-004 AC-24, AC-25, AC-26, NFR-10; ADR-023 QĐ 1 (M1) | FEAT-004, `[dropped from AC-11, owner FEAT-004 AC-25]` | Không |
| O-10b | AC-11, cổng công tắc (5) và hạn 24 giờ | FEAT-004 A-25, ADR-023 QĐ 1 (không hạn) | FEAT-007, `[changed]` | Cổng công tắc (5) và hành vi khi tắt (xung đột K-1, K-7); bỏ hạn 24 giờ |
| O-11 | AC-12 (môi trường test/production) | FEAT-004 Amendment 1 (đề xuất sửa file và lệnh bench, quyền (4)); không có khái niệm môi trường ở Amendment 2 | FEAT-007, `[changed]` | Cổng môi trường chỉ ở đường chính (danh mục); đề xuất code/bench là quyền (4), không bị chặn theo môi trường (L-4) |
| O-12 | AC-13 (người ra lệnh theo tác giả `@ai`, người được bot gán không thành người ra lệnh) | ADR-023 QĐ 4 "Ghi nhận" (người ra lệnh gồm người được giao phiếu, "giữ nguyên"); FEAT-004 AC-11 | FEAT-007, giữ nguyên chữ; xung đột L-2 chờ architect | Toàn bộ AC-13 |
| O-13 | AC-14 (kiểm lại người duyệt lúc áp dụng) | ADR-023 QĐ 2 (M2); FEAT-004 AC-27 (kiểm lúc áp dụng) | FEAT-004, `[dropped, owner FEAT-004 AC-27]` | Tập điều kiện của người duyệt theo loại đề xuất, nằm ở AC-35 `[changed]` |
| O-14 | AC-15 (chốt chặn hàm `erp_ai.*` và 4 DocType chống chuỗi thoát) | ADR-023 QĐ 5 (M5: đóng bằng danh tính ở controller, so chuỗi chỉ còn là từ chối sớm); FEAT-004 AC-33 | FEAT-004, `[dropped, owner FEAT-004 AC-33]` | Không |
| O-15 | AC-22 (độ tin cậy dưới 70 thì chỉ hỏi) | FEAT-004 AC-29 (làm ngay, không hỏi lại) | FEAT-007, `[changed]` | Phạm vi: lệnh trực tiếp khi (3) bật không bị ngưỡng chặn (xung đột K-6) |
| O-16a | AC-23, comment kết quả áp dụng đề xuất (xong, lỗi, hết hiệu lực, hoàn tác) | FEAT-004 AC-28 (chưa có mã) | FEAT-004, `[dropped from AC-23, owner FEAT-004 AC-28]` | Không. Đề xuất bản ghi dùng chính cơ chế đó (AC-33 `[changed]`) |
| O-16b | AC-23, các comment còn lại (routing, lỗi cuối, bỏ qua vì ngân sách hoặc giới hạn ngày; 4 ca không comment) | FEAT-004 AC-24 chỉ là comment sau khi tạo đề xuất | FEAT-007, `[changed]` | Toàn bộ phần còn lại |
| O-17 | AC-29 (danh mục trắng, mặc định cấm) | FEAT-004 AC-30, AC-31 (công cụ bản ghi theo danh sách cấm, không theo danh mục); ADR-023 QĐ 3 | FEAT-007, `[changed]` | Làm rõ danh mục chỉ cổng đường chính, không cổng 5 quyền; danh sách cấm cứng dùng chung (xung đột K-1) |
| O-18 | AC-30 (5 hành động có tên) | FEAT-004 AC-31 (6 vai trò cấm), N-2 S-4 | FEAT-007, giữ nguyên chữ | Dùng đúng danh sách 6 vai trò cấm của FEAT-004 AC-31, không lập danh sách thứ hai (mục 4) |
| O-19 | AC-31, AC-32 (mức theo đầu mục; L1 không tool ghi ERP) | FEAT-004 AC-2 (điều kiện mức của ba đường cấp); ADR-023 QĐ 4 | FEAT-007, `[changed]` | Mức theo đầu mục chỉ áp cho đường chính, không kéo điều kiện mức của 5 quyền xuống (xung đột K-5) |
| O-20 | AC-33 (luồng đề xuất, Duyệt hai lần vẫn một lần, code dùng chung luồng) | ADR-012 QĐ 3; FEAT-004 AC-25, NFR-10; AC-28 | Máy trạng thái và hàng đợi áp dụng: FEAT-004. Loại đề xuất "thay đổi bản ghi": FEAT-007. `[changed]` | Loại đề xuất mới và hết hiệu lực khi giá trị đích đổi (xung đột K-3) |
| O-21 | AC-35 (người duyệt hợp lệ) | FEAT-004 AC-5 (chỉ `ERP AI Instructor`), AC-26 (kể cả người được giao phiếu bị từ chối); ADR-012 QĐ 4 | FEAT-007, `[changed]` | Người duyệt theo loại đề xuất (xung đột K-3) |
| O-22 | AC-39 (Duyệt/Sửa/Từ chối từ trang phiếu, không màn hình khác) | ADR-023 QĐ 1 (liên kết mở form Desk rồi POST), QĐ 6 (người duyệt có vào được Desk không) | FEAT-007, `[changed]` | Bắt đầu từ trang phiếu; thao tác hoàn tất ở form (xung đột K-7) |
| O-23 | AC-42 (chốt chung hai đường đổi trạng thái) | FEAT-004 AC-30, AC-32, N-2 S-3 (công cụ bản ghi ghi mọi trường, kể cả `status`) | FEAT-007, `[changed]` | Giới hạn "không đổi `status`" về hai đường N-2 và đường chính, không áp cho quyền (1), (2) (L-3) |
| O-24 | A-3 (5 công tắc, Toàn quyền gồm công cụ bản ghi) | FEAT-004 A-23, A-24 | FEAT-007, `[changed]` | Xem mục 2.3 |
| O-25 | A-4 (giữ khả năng nguy hiểm, giảm nhẹ bằng...) | N-2 S-6; ADR-023 QĐ 1, 5, 6 | FEAT-007, `[changed]` | Danh sách giảm nhẹ đổi nguồn; rủi ro còn lại đổi |
| O-26 | A-6 (người duyệt hợp lệ) | FEAT-004 AC-5, AC-26; ADR-012 QĐ 4 | FEAT-007, `[changed]` | Theo loại đề xuất |
| O-27 | A-13 (hạn liên kết 24 giờ) | ADR-023 QĐ 1 ("không đặt hạn"); FEAT-004 A-25 | FEAT-007, `[changed]` | Bỏ riêng số 24 giờ; các số khác của A-13 giữ |
| O-28 | A-18 (5 test đỏ vì cài đặt site) | FEAT-004 DoD Amendment 2 (5 lỗi: 3 ở `TestRunnerL1Classification`, 2 ở `test_runner_routing`) | FEAT-004, `[changed]` | FEAT-007 không sửa 5 test này |
| O-29 | A-19, A-20 (quan hệ feature, ADR mới) | FEAT-004 N-9, A-28; ADR-023 | FEAT-007, `[changed]` | Xem mục 2.3 |
| O-30 | AR-1, AR-4, AR-5; R-3 | ADR-023 QĐ 1, 2, 4, 5, 6 | Architect, `[changed]` | AR-5 đã có lời giải (QĐ 5); AR-4 và AR-1 còn phần dư (K-1..K-7, L-2) |

**Không chồng lấn** (không đổi, không cần chủ chung): AC-4 (chỉ vướng A-23), AC-9, AC-16..AC-21, AC-24..AC-28, AC-30 (trừ ràng buộc dùng chung), AC-34, AC-36..AC-38, AC-40, AC-41, AC-43..AC-64. AC-21 nhắc "ghi của bot qua công cụ bản ghi không tính là sửa của người": nhãn người ghi lấy từ nhật ký của FEAT-004 AC-34, không cần AC mới.

**Đếm.** AC của FEAT-007 `[changed]`: 18 (AC-1, 3, 5, 6, 7, 8, 10, 11, 12, 22, 23, 29, 31, 32, 33, 35, 39, 42). AC `[dropped]`: 3 (AC-2, AC-14, AC-15). Giả định đổi: 7 (A-3, A-4, A-6, A-13, A-18, A-19, A-20). Câu kỹ thuật đổi: 3 (AR-1, AR-4, AR-5; R-3 ghi chú). AC-13 giữ nguyên chữ nhưng đang chờ architect (L-2).

---

## 2. Văn bản mới đầy đủ

### 2.1 Tiêu chí `[changed]`

Quy ước kiểm như `spec.md` mục Tiêu chí nghiệm thu. "5 công tắc" như `spec.md` (1 Toàn quyền, 2 công cụ bản ghi chung, 3 làm luôn, 4 sửa code + bench, 5 liên kết duyệt một lần bấm).

| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 `[changed]` | [C1–C5, N-1] Có đúng 5 công tắc quyền độc lập. Sau cài mới cả 5 đều tắt. Sau migrate trên site đã có cấu hình: (1) và (4) giữ giá trị đã lưu; (2), (3), (5) bằng tắt, kể cả khi site đang bật (4). Hệ quả có chủ ý: từ lúc migrate, ô (4) chỉ còn mở 3 tool đề xuất sửa file, tạo file, lệnh bench; không còn mở công cụ bản ghi, khối "làm luôn" hay liên kết một lần bấm (thay FEAT-004 A-24). Chạy migrate lần hai không đổi giá trị nào người đã đặt. Hồi quy: đặt (2) bằng giá trị của (4), (3) bật, (5) bật thì bộ tool và prompt trùng ảnh chụp của ADR-023 QĐ 4 (M4) ở mọi tổ hợp (4) × (1) × 4 mức × có/không người ra lệnh | Test cài mới đọc 5 giá trị. Test migrate với cấu hình giả lập đã bật hai công tắc cũ → hai giá trị giữ, ba mới bằng 0; chạy lần hai → không đổi. Test hồi quy so ảnh chụp M4 với ánh xạ tương đương nói trên |
| AC-3 `[changed]` | [C1–C5] Mỗi công tắc độc lập: bật riêng một công tắc (5 ca) thì tập tool và khối prompt thêm đúng bằng tập đã khai báo cho quyền đó, không thêm gì khác. Khai báo: (1) nhóm xóa, submit/hủy, gọi hàm whitelist cùng bốn công cụ bản ghi, từ mức > L0 khi có người ra lệnh (đúng FEAT-004 AC-2(c)); (2) liệt kê, đọc, tạo, sửa bản ghi, cần mức L3 và người ra lệnh (đúng FEAT-004 AC-2(b)); (3) khối prompt "làm luôn", không thêm tool; (4) ba tool đề xuất sửa file, tạo file, lệnh bench, cần mức L3 và người ra lệnh (đúng FEAT-004 AC-2(a)); (5) không thêm tool, chỉ đổi hình thức liên kết trong comment (AC-11). Thêm một hàng "cả 5 tắt" bằng bản nền (FEAT-004 AC-1). Trong registry có đúng một hàm cấp và một bảng cấp; ba công tắc mới là đầu vào thêm của hàm đó (ADR-023 QĐ 4) | Test bảng 6 hàng (5 công tắc + cả 5 tắt); assert tập thêm = tập khai báo; luật kiến trúc của ADR-023 ("đúng một hàm cấp") vẫn xanh |
| AC-5 `[changed]` | [C1, C2] Khi Toàn quyền tắt (kể cả khi 2, 3, 4, 5 bật), phần FEAT-007 làm chủ của "sửa Role Permission": ghi vào User Permission, DocShare, và Property Setter đổi `permlevel` bị từ chối, dữ liệu không đổi. Ba vector đã có người làm chủ nhưng vẫn nằm trong cùng test để chống thụt lùi: Custom DocPerm, `Role`, `DocType` (ADR-023 M3). Các vector này nằm trong đúng một danh sách cấm dùng chung (mục 4), không lập danh sách thứ hai. KHÔNG cấm ghi `Has Role` hay Role Profile nói chung: tạo User và gán vai trò nghiệp vụ là quyền (2) giữ theo N-1 (FEAT-004 N-2 S-4, A-1'); chỉ 6 vai trò của FEAT-004 AC-31 bị từ chối. Các ý (a) xóa, (c) migrate/deploy, (d) Purchase Invoice và Payment Entry đã submit: `[dropped from AC-5, owner FEAT-004 AC-31]` (xóa), FEAT-004 AC-2(a) (bench), FEAT-004 AC-30 (chứng từ đã submit) | Test 6 vector × chế độ thường: mỗi ca assert dữ liệu trước = sau và 1 mục nhật ký `ok=false` kèm lý do; 1 ca khẳng định gán vai trò nghiệp vụ qua User vẫn thành công khi (2) bật |
| AC-6 `[changed]` | [C3] Khối prompt của mỗi quyền chỉ có khi đúng điều kiện: khối "bản ghi chung" khi (2) bật và công cụ bản ghi được cấp; khối "toàn quyền" khi (1) bật và nhóm đó được cấp; khối "làm luôn" khi (3) bật và có ít nhất một nhóm ghi được cấp (thay điều kiện "bất kỳ nhóm nào được cấp" của FEAT-004 AC-29, xung đột K-1); khối đề xuất code khi (4) bật và tool đề xuất được cấp. Nội dung các khối do FEAT-004 AC-14, AC-29 làm chủ. Khi một khối bật, các câu cấm gốc trong khối lõi bị thay hoặc bỏ đúng chỗ: prompt không chứa đồng thời một câu cấm và câu cho phép chính việc đó, theo danh sách cặp câu do designer lập từ `prompts.py` | Test từng công tắc: dựng prompt, assert không còn cặp câu trái nhau, assert khối vắng khi điều kiện không đủ; thêm 1 ca (2) bật, (3) tắt: công cụ bản ghi được cấp, khối "làm luôn" vắng, bot hỏi lại khi thiếu thông tin |
| AC-7 `[changed]` | [C1, H7] Khi chi tháng vượt ngân sách (mức hạ về L1), tập tool của mọi lần chạy kế tiếp bằng tập tool L1 của cấu hình hiện tại với 5 công tắc tắt, dù cả 5 bật: không còn nhóm bản ghi, đề xuất code (FEAT-004 AC-2 làm chủ vế này) và không còn nhóm Toàn quyền (xóa, submit/hủy, gọi hàm, bốn công cụ bản ghi). Phần FEAT-007 làm chủ chỉ là vế sau: Toàn quyền cũng mất khi vượt ngân sách, thay câu cuối của FEAT-004 AC-2 ("(c) còn") và đoạn "Ghi nhận" của ADR-023 QĐ 4 (xung đột K-4). Đường chính về L1 theo AC-31. Nếu architect hoặc người giữ ADR-023 QĐ 4 thì vế sau bỏ, AC-7 chỉ còn "mọi nhóm trừ Toàn quyền", và As-Built ghi rõ Toàn quyền sống qua vượt ngân sách | Test bật cả 5 công tắc, gieo chi vượt, assert tập tool = tập L1 với 5 công tắc tắt (không còn nhóm Toàn quyền). Test ma trận của FEAT-004 AC-2 có chiều vượt ngân sách được sửa theo (NFR-8, ghi lý do) |
| AC-8 `[changed]` | [C6, H6] Đọc chéo qua các tool bản ghi: khi công cụ bản ghi bật (kể cả cùng Toàn quyền), liệt kê và đọc HD Ticket, Comment, Communication, File (siêu dữ liệu) của phiếu thuộc nhóm loại trừ hoặc có cờ không dùng AI: 0 dòng trả về, có lý do bị từ chối; phiếu thường vẫn đọc được. Danh sách và đếm không lộ sự tồn tại của phiếu loại trừ. Đường gọi hàm whitelist (Toàn quyền) theo ADR-023 QĐ 6: nếu người chọn (a) danh sách hàm cho phép thì không hàm nào trong danh sách trả phiếu loại trừ; nếu chọn (b) gọi tự do thì AC này không bảo đảm cho đường đó, và rủi ro được ghi ở thông báo bật Toàn quyền (AC-4) và As-Built. Không lập danh sách cấm thứ hai: chốt ở mức bản ghi bổ sung cho danh sách cấm ở mức DocType của ADR-023 QĐ 3 | Test ma trận 4 DocType × {nhóm loại trừ, cờ không dùng AI, phiếu thường}; kiểm cả đường liệt kê lẫn đọc theo tên; nếu chọn (a): thêm 1 ca cho mỗi hàm trong danh sách |
| AC-10 `[changed]` | [H8, C1] Nhật ký hành động cho mọi lần ghi của bot. Phần FEAT-004 làm chủ (`[dropped from AC-10, owner FEAT-004 AC-34, AC-35]`): mỗi lời gọi công cụ bản ghi và nhóm Toàn quyền, kể cả bị từ chối hoặc sập, có một mục; mỗi lần ghi, xóa, submit, gọi hàm thành công có giá trị trước, giá trị sau, người ra lệnh, 0 byte bí mật. Phần FEAT-007 làm chủ: (a) cho mọi lần ghi còn lại của bot (trường phiếu, Task, comment, trả lời, trạng thái, hành động danh mục, đề xuất bản ghi đã áp dụng, thay đổi công tắc quyền) có đúng một mục cùng dạng và cùng đường ghi với FEAT-004 AC-34, AC-35: tên tool, đích (loại và tên bản ghi), từng trường với giá trị trước và sau, người ra lệnh (user ID), kết quả; (b) cho mọi mục, kể cả mục do FEAT-004 ghi, thêm mã lần chạy, giá trị môi trường site và, khi bị từ chối, lý do; (c) gọi cùng tool hai lần trong một lần chạy → hai mục; (d) giá trị trường mật khẩu và khóa được che | Test mỗi tool ghi của đường chính một ca, thêm 1 ca gọi cùng tool hai lần, 1 ca bị từ chối có lý do, 1 ca có mật khẩu giả; đếm mục và đối chiếu giá trị. Thêm 1 ca xuyên: một lần chạy có 1 lời gọi công cụ bản ghi và 1 ghi trường phiếu → 2 mục cùng mã lần chạy, cùng dạng |
| AC-11 `[changed]` | [C5] Liên kết duyệt một lần bấm do công tắc (5) quản. Cơ chế liên kết (chữ ký gắn đề xuất và hành động, một lần thắng, kiểm vai trò ở server, không đường GET nào đổi trạng thái, không hộp xác nhận ở đường một lần bấm) là của FEAT-004 (`[dropped from AC-11, owner FEAT-004 AC-25]`; AC-24, AC-26, NFR-10, ADR-023 QĐ 1). Phần FEAT-007 làm chủ là cổng công tắc: (i) (5) tắt (mặc định): comment đề xuất không chứa liên kết Duyệt/Từ chối một lần bấm, chỉ có liên kết mở đề xuất; mở một liên kết một lần bấm cũ (từ comment tạo trước đó) chỉ mở form, không gọi bước duyệt, trạng thái đứng yên, 0 job; Duyệt và Từ chối làm trên form qua hộp xác nhận (như FEAT-004 AC-22 cho form); (ii) (5) bật: hành vi đúng FEAT-004 AC-25; (iii) thông báo bật (AC-4) nêu "một lần bấm, không hộp xác nhận; người có vai trò bấm liên kết được chuyển tiếp cũng duyệt". `[dropped]` hạn 24 giờ (A-13 `[changed]`). Điều kiện "người bấm đủ điều kiện duyệt" nằm ở AC-35 `[changed]` | Test 4 ca: (5) tắt, comment mới; (5) tắt, mở liên kết cũ → trạng thái đứng yên, 0 job; (5) tắt, Duyệt trên form phải qua hộp xác nhận (test dữ liệu form như FEAT-004 AC-22); (5) bật, comment có liên kết, mở một lần → kết quả do test FEAT-004 AC-25 kiểm, không lặp ở đây |
| AC-12 `[changed]` | [H10] Cấu hình có môi trường site `test` hoặc `production`, mặc định `production` (cũng cho site đang có). Ở đường chính (danh mục và đề xuất bản ghi), các loại Custom Field, Server Script, Client Script, Property Setter, Workflow, Data Import chạy chỉ thực hiện được khi môi trường là `test`; ở `production` bị từ chối, không tạo đề xuất, bot đăng 1 comment "cần làm trên site test". Đã bỏ "sửa file code, lệnh bench" khỏi danh sách: đề xuất code và lệnh là quyền (4) do FEAT-004 làm chủ, không bị chặn theo môi trường, nhất quán với "5 công tắc không bị chặn bởi môi trường". Giá trị môi trường được ghi vào thông báo bật của mọi công tắc (AC-4) và vào mọi mục nhật ký của 5 quyền (AC-10(b)) | Test 6 loại × 2 môi trường = 12 ca ở đường chính; test (2) bật ở `production` vẫn ghi và mục nhật ký có "production"; test đề xuất code ở `production` vẫn tạo được (không bị chặn) |
| AC-22 `[changed]` | [H2] Độ tin cậy của phân loại và của mỗi đề xuất là số nguyên 0–100 (nhãn Cao/Trung bình/Thấp cũ giữ cho dữ liệu cũ). Dưới ngưỡng (mặc định 70, sửa trong cấu hình): lần chạy không có tool ghi nào (không ghi trường, không gán, không tạo Task, không hành động ERP, không trả lời ngoài câu hỏi) và đăng đúng 1 comment hỏi; từ ngưỡng trở lên chạy bình thường. Comment đề xuất phải có "Độ tin cậy: NN%" và phần "Căn cứ" không rỗng, thiếu thì tool trả lỗi cho model và comment không được đăng. Phạm vi: ngưỡng áp cho mọi lần chạy trừ lần chạy có người ra lệnh với công tắc (3) bật: đó là lệnh trực tiếp của người, bot làm luôn theo FEAT-004 AC-29 và không bị ngưỡng chặn (độ tin cậy vẫn ghi vào nhật ký nếu model nêu). Khi (3) tắt, dù có người ra lệnh và quyền (2) hoặc (4) bật, dưới ngưỡng bot chỉ hỏi | Test stub trả 69, 70, 100, thiếu căn cứ: đếm tool ghi và comment; ca đổi ngưỡng sang 80; thêm 2 ca: (3) bật + người ra lệnh + 69% → công cụ bản ghi chạy được; (3) tắt + người ra lệnh + 69% → 0 tool ghi, 1 comment hỏi |
| AC-23 `[changed]` | [H3] Mỗi hành động có đúng 1 comment trên phiếu: routing thành công (một comment gộp trường đã ghi, người gán, Task tạo); lần chạy lỗi sau lần cuối; lần chạy bị bỏ qua vì hết ngân sách (tối đa 1 comment mỗi phiếu mỗi ngày); lần chạy bị bỏ qua vì chạm giới hạn ngày (tối đa 1 comment mỗi phiếu mỗi ngày). Không comment (chỉ log) cho: agent tắt, mức L0, phiếu nhóm loại trừ, cờ không dùng AI. `[dropped from AC-23, owner FEAT-004 AC-28]`: comment kết quả áp dụng đề xuất (xong, lỗi, hết hiệu lực, hoàn tác). FEAT-007 không dựng cơ chế comment thứ hai | Test ma trận 8 tình huống (4 có comment, 4 không), đếm comment từng ca; chạy lặp trong ngày vẫn 1 comment cho ca bỏ qua |
| AC-29 `[changed]` | [H5, C2] Danh mục trắng nằm trong cấu hình; mặc định không có dòng nào, mọi hành động ghi ERP của đường chính (5 hành động có tên ở AC-30 và đề xuất thay đổi bản ghi) bị từ chối với thông báo "ngoài danh mục" và không đổi dữ liệu. Danh mục không cổng: công cụ của 5 quyền (do công tắc và FEAT-004 AC-30..AC-33 quản, N-1 giữ 5 quyền), và việc ghi trường phân loại, gán, Task, comment đã được phép từ FEAT-001 và FEAT-006. Thêm một dòng thì đúng hành động hoặc DocType đó, đúng trường, đúng đầu mục đó dùng được, ở chế độ của dòng; có hiệu lực từ lần chạy kế tiếp, không deploy. Lưu bị chặn khi dòng trỏ vào điều cấm cứng (xóa, Role Permission, chứng từ đã submit, DocType của app) hoặc hành động không có. Điều cấm cứng lấy từ danh sách dùng chung của ADR-023 QĐ 3 | Test: danh mục rỗng × mỗi hành động của AC-30 và đề xuất bản ghi = từ chối; thêm 1 dòng → chỉ dòng đó dùng được; lưu 4 dòng cấm → bị chặn; 1 ca (2) bật, danh mục rỗng → công cụ bản ghi vẫn ghi được (không cổng) |
| AC-31 `[changed]` | [H4] Mức hiệu lực của một phiếu cho đường chính = nhỏ hơn giữa mức toàn hệ thống và mức tối đa của đầu mục trong cấu hình. Mặc định theo bảng mục 3: A L2, B L3, C L1, D L2, E L1, F L3 (C chỉ L1 vì việc nhỏ cần site test, N-4). Vượt ngân sách thì mọi đầu mục về L1. Mức theo đầu mục chỉ quyết định đường chính (danh mục, đề xuất, Task nháp, BA note). Điều kiện mức của 5 quyền (L3 cho (2) và (4); > L0 cho (1)) tính trên mức toàn hệ thống sau khi hạ vì ngân sách, đúng FEAT-004 AC-2 và ADR-023 QĐ 4, không bị mức đầu mục kéo xuống (xung đột K-5) | Test 6 đầu mục × 4 mức toàn hệ thống × có/không vượt ngân sách cho đường chính; thêm 1 ca: phiếu đầu mục C (cap L1), mức toàn hệ thống L3, (4) bật, có người ra lệnh → vẫn có tool đề xuất code |
| AC-32 `[changed]` | [H4] Ở mức hiệu lực L1 của đường chính, khi Toàn quyền tắt: không có tool ghi ERP; bot chỉ đăng comment đề xuất (chẩn đoán, phương án, độ tin cậy, căn cứ) và dùng được tool Task nháp. Task (tool ghi phiếu) cấp ở L1+ như nay. Khi Toàn quyền bật, nhóm Toàn quyền vẫn được cấp ở L1 theo FEAT-004 AC-2(c) (đó là quyền (1), không phải đường chính), trừ khi vượt ngân sách (AC-7) | Test tập tool ở L1 cho 6 đầu mục với Toàn quyền tắt; 1 ca Toàn quyền bật ở L1 không vượt ngân sách |
| AC-33 `[changed]` | [H4, N-1] Ở mức hiệu lực ≥ L2 của đường chính, một hành động có chế độ `Cần duyệt`, hoặc chế độ `Tự làm` nhưng chưa đủ điều kiện AC-36, tạo đề xuất chờ duyệt thuộc loại "thay đổi bản ghi", chưa ghi gì. Comment đề xuất nêu hành động, đích, giá trị, độ tin cậy, căn cứ và có Duyệt, Sửa, Từ chối. Đề xuất hết hiệu lực khi giá trị hiện tại của đích khác giá trị trước lúc đề xuất. Sau Duyệt: áp dụng đúng một lần, có mục nhật ký (AC-10) và 1 comment kết quả đi qua cơ chế của FEAT-004 AC-28 với đủ 4 kết cục (xong, lỗi, hết hiệu lực, hoàn tác). Sau Từ chối: không ghi, có nhật ký và comment. `[dropped from AC-33, owner FEAT-004 AC-25]`: "Duyệt hai lần vẫn một lần" (NFR-10, ADR-012 QĐ 3) và "đề xuất sửa code và lệnh bench dùng cùng luồng và cùng trạng thái" (ADR-012). Đề xuất bản ghi dùng chính máy trạng thái và hàng đợi áp dụng của FEAT-004; FEAT-007 thêm loại đề xuất, không thêm máy trạng thái thứ hai | Test: dữ liệu đích không đổi cho tới khi duyệt; từ chối; đích đổi giữa chừng → hết hiệu lực; mỗi kết cục trong 4 có đúng 1 comment qua cơ chế AC-28 của FEAT-004 |
| AC-35 `[changed]` | [H4] Người duyệt hợp lệ theo loại đề xuất: (a) đề xuất thay đổi bản ghi (đường chính): người đang được giao phiếu (việc gán còn mở) hoặc người có `ERP AI Instructor`; (b) đề xuất sửa code và lệnh `bench` (quyền (4)): chỉ `ERP AI Instructor` (FEAT-004 AC-5, ADR-012 QĐ 4), người được giao phiếu và người tạo phiếu không duyệt được. Người tạo phiếu không có điều kiện (a), người có role Agent không được giao, tài khoản agent, Administrator, Guest: bị từ chối ở Duyệt, Sửa, Từ chối của cả hai loại. Kiểm lại lúc áp dụng (ADR-023 QĐ 2, M2) dùng đúng tập điều kiện của loại đó: mất điều kiện giữa lúc duyệt và lúc áp → không áp, đề xuất sang trạng thái "Lỗi" có lý do (không tạo trạng thái thứ ba), 1 mục nhật ký, 1 comment. Thay AC-14 `[dropped, owner FEAT-004 AC-27]` | Test 5 vai × 2 loại đề xuất; duyệt rồi gỡ điều kiện (gỡ role hoặc hủy gán) trước khi job chạy → 0 thay đổi dữ liệu, trạng thái Lỗi. Test M2 của FEAT-004 là test cho loại (b); FEAT-007 thêm test cho loại (a) |
| AC-39 `[changed]` | [C5, N-1] Duyệt, Sửa, Từ chối bắt đầu được từ trang phiếu Helpdesk, ngay trên comment của bot hoặc ngăn của bot trên trang đó, không phải tìm đề xuất ở danh sách hay màn hình khác. Thao tác hoàn tất ở đích mà ADR-023 QĐ 1 chọn cho liên kết (form đề xuất): hộp xác nhận khi (5) tắt, một lần bấm khi (5) bật (FEAT-004 AC-25); riêng "Sửa" đòi nhập giá trị. Trạng thái đổi sau thao tác; comment kết quả hiện trên trang phiếu. Điều kiện: người duyệt vào được form đề xuất (ADR-023 QĐ 6 chưa kiểm cho Hiếu, Việt, Tiến). Lệch có chủ ý so với tài liệu chiến lược (`source-strategy.md:107`, "không cần mở màn hình khác"): xem K-7. Nếu R-3 chứng minh nút bấm được ngay trên dòng thời gian của phiếu thì khôi phục AC-39 nguyên văn | Kiểm có đầu ra: trên site dev, bật một dòng danh mục `Cần duyệt`, cho bot đề xuất, người được giao phiếu thao tác Duyệt, Sửa và Từ chối bắt đầu từ trang phiếu; dán ảnh và dòng nhật ký; ghi thêm người đó có vào được form hay không |
| AC-42 `[changed]` | [G5, G6, N-2] Chốt chung của hai đường đổi trạng thái N-2: (a) cả hai công tắc tắt thì bot không đổi `status` phiếu bằng tool hay job nào của đường chính (kể cả các việc theo lịch); (b) phiếu có nguồn "Chỉ đạo BGĐ" hoặc đầu mục E không bao giờ bị bot đổi trạng thái theo hai đường N-2 (Resolved khi Task xong, đóng F im lặng). `[dropped]` vế "và không bị đổi bởi công cụ bản ghi chung hay Toàn quyền": quyền (1) và (2) là lệnh trực tiếp của người, giữ nguyên theo N-1; việc đổi `status` qua chúng có mục nhật ký theo FEAT-004 AC-34, AC-35; (c) khi trường "Nguồn phát sinh" chưa cấu hình (AC-24) thì không đường nào chạy, 1 dòng log mỗi ngày nêu lý do (A-11); (d) trạng thái nào cũng ghi log và 1 comment | Test bảng chân trị: 6 đầu mục × {BGĐ, không BGĐ, chưa cấu hình} × 2 công tắc. Bỏ 2 ca thử ghi `status` bằng quyền 2 và quyền 1 |

### 2.2 Tiêu chí `[dropped]`

Nguyên văn các AC này vẫn nằm trong `spec.md`; chúng không còn là tiêu chí của FEAT-007. Việc bỏ chỉ có hiệu lực nếu biện pháp tương ứng của ADR-023 được xây và có test (điều kiện khôi phục ở cuối mục).

| Mã | Trạng thái | Nơi chuyển tới | Còn lại cho FEAT-007 |
|---|---|---|---|
| AC-2 | `[dropped, owner FEAT-004 AC-1]` | FEAT-004 AC-1 (hàng "cả hai ô tắt" khớp bản nền, kể cả prompt) và AC-2 (ma trận có chiều vượt ngân sách) | Một hàng "cả 5 tắt = bản nền" trong ma trận AC-3 (chống thụt lùi khi thêm ba công tắc) |
| AC-14 | `[dropped, owner FEAT-004 AC-27]` | ADR-023 QĐ 2 và Test M2 (đầu job kiểm người thực hiện không thuộc `NEVER_AUTHORITY`, còn vai trò, user phiên trùng; khóa hết giờ → trạng thái Lỗi) | Tập điều kiện theo loại đề xuất ở AC-35 `[changed]` |
| AC-15 | `[dropped, owner FEAT-004 AC-33]` | ADR-023 QĐ 5 và Test M5 (danh tính ở controller, phủ cả `frappe.client.insert` với chuỗi JSON có `\u` và `savedocs`); AR-5 đã được trả lời | Không. Phần "bot tự đổi công tắc qua đường ghi DB không qua controller" là QĐ 6, chờ người (L-5) |

**Điều kiện khôi phục.** FEAT-004 AC-27 chưa có chữ về việc người duyệt mất vai trò giữa lúc duyệt và lúc áp, và FEAT-004 AC-33 chưa có chữ về chuỗi thoát; hai chỗ đó hiện chỉ nằm ở Test M2 và Test M5 của ADR-023. Nếu M2 hoặc M5 không được đưa vào plan của FEAT-004 (arch-impact đã giao tech-lead), khôi phục AC-14, AC-15 nguyên văn cho FEAT-007. Đề nghị team-leader đưa hai phép kiểm đó thành chữ của AC-27 và AC-33 trong FEAT-004 để khỏi mất.

### 2.3 Giả định và câu kỹ thuật đổi

Mỗi giả định đủ 4 trường.

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-3 `[changed]` | 5 công tắc độc lập (K-1). (1) và (4) đã có, giữ giá trị người đã đặt; (2), (3), (5) mới, mặc định tắt. Ô (4) chỉ mở 3 tool đề xuất code/bench; ô (2) mở công cụ bản ghi (thay FEAT-004 A-24). Toàn quyền gồm cả bốn công cụ bản ghi. Công tắc bật thì hành vi như mã ngày 13/11 nhưng có cảnh báo (AC-4, thay FEAT-004 A-23), nhật ký đủ (AC-10 và FEAT-004 AC-34, AC-35), và cắt khi vượt ngân sách (AC-7, K-4) | N-1: "vẫn giữ nhưng là công tắc riêng, mặc định tắt, bật thì có cảnh báo và ghi log đủ". FEAT-004 A-24 tự ghi cách sửa nếu cần: "thêm ô, một dòng ở bảng cấp, đổi AC-1, AC-2" | Giữ 2 ô như FEAT-004 A-24; ép tắt cả hai ô cũ sau migrate | Bỏ hàng (2), (3), (5) khỏi AC-3 và phần migrate của AC-1; FEAT-004 AC-1, AC-2 giữ nguyên |
| A-4 `[changed]` | Giữ nguyên các khả năng nguy hiểm khi công tắc bật, gồm Toàn quyền cho bot sửa User của chính nó và gán System Manager. Giảm nhẹ: cảnh báo bật và cảnh báo hằng ngày (AC-4, FEAT-007); nhật ký trước/sau (FEAT-004 AC-34, AC-35, AC-10 FEAT-007); cắt khi vượt ngân sách (AC-7, nếu K-4 giữ); kiểm lại lúc áp dụng và bot không tự duyệt, không đổi công tắc của mình qua controller (ADR-023 M2, M5, FEAT-004). Bỏ "đường dẫn có hạn". Rủi ro còn lại, thay đoạn "trình duyệt tải trước" (đã bị ADR-023 M1 loại): (i) người có vai trò bấm liên kết được chuyển tiếp; (ii) khi Toàn quyền bật và người chọn (b) ở ADR-023 QĐ 6, bot còn chạm được công tắc của mình qua đường ghi DB không qua controller; (iii) tài khoản agent mang System Manager (L-8) | N-1 giữ 5 quyền; thu hẹp là đảo quyết định của người | Sàn cứng "bot không tự nâng quyền" kể cả khi Toàn quyền bật | Thêm AC sàn cứng bằng change-request |
| A-6 `[changed]` | Người duyệt hợp lệ theo loại đề xuất: đề xuất bản ghi = người được giao phiếu (việc gán còn mở) hoặc `ERP AI Instructor`; đề xuất code và lệnh `bench` = chỉ `ERP AI Instructor` | Tài liệu chiến lược: "người phụ trách bấm duyệt" (`source-strategy.md:100,107`) cho việc ở đường chính; ADR-012 QĐ 4 và FEAT-004 AC-5 giữ cho code và lệnh vì việc đó chạy mã trên site | Chỉ Instructor cho cả hai (đúng FEAT-004, nhưng người phụ trách như IT, trưởng bộ phận thường không phải Instructor); người được giao cho cả hai (hạ FEAT-004 AC-5, rủi ro khi chạy code) | Đổi AC-35. Architect phán ở K-3 |
| A-13 `[changed]` | Bỏ số "hết hạn đường dẫn một lần bấm 24 giờ". Các số khác của A-13 (nhắc hạn trước 24 giờ; 5 kết quả mỗi lần tìm; 20 dòng mỗi báo cáo bot chạy; 10 Task mỗi lần chạy; báo cáo COO gửi cả cuối tuần) giữ | ADR-023 QĐ 1 chọn không hạn và chặn đề xuất cũ lúc áp dụng; FEAT-004 A-9, A-25. Số 24 giờ là số analyst tự đặt, không đến từ N-1 | Giữ hạn 24 giờ (đụng `change_link` của FEAT-004 đang build) | Thêm hạn bằng change-request trên FEAT-004 sau khi FEAT-004 merge |
| A-18 `[changed]` | Năm test đỏ vì đọc cài đặt đã lưu của site (3 ở `TestRunnerL1Classification`, 2 ở `test_runner_routing`) do FEAT-004 làm chủ (DoD Amendment 2 của nó đòi cả app xanh). FEAT-007 không sửa năm test này. Nếu FEAT-007 merge trước, áp đúng bản sửa tối thiểu (test tự đặt cài đặt và trả lại) và FEAT-004 bỏ phần việc đó; thứ tự do team-leader xếp. Phần còn lại của A-18 (test ghim hành vi mà spec đổi được sửa theo AC, NFR-8) giữ | FEAT-004 DoD ghi "không đổi test cho khớp site (STD-TEST-5)"; hai phiên cùng sửa một test là xung đột chắc chắn | FEAT-007 sửa trước và FEAT-004 theo | Team-leader chọn lại thứ tự merge |
| A-19 `[changed]` | FEAT-004 Amendment 2 đã nêu hệ quả cho FEAT-005 (N-9, A-28: đề nghị đóng hoặc thu hẹp) và cho FEAT-006 AC-9 (phép thử tĩnh cần ngoại lệ có ADR). Comment kết quả áp dụng là FEAT-004 AC-28 (bỏ khỏi AC-23). FEAT-004 giữ các luật kiến trúc T31, T32, T44, T48. Đề nghị "gộp phần trùng khi merge" của A-19 cũ được thay bằng bảng ở mục 1. Ngoại lệ cho FEAT-006 AC-9 dùng chung một ngoại lệ cho cả công cụ bản ghi (FEAT-004) và tool danh mục (FEAT-007: thêm người vào nhóm, tạo tài khoản theo mẫu) | Tránh hai ADR và hai ngoại lệ cho cùng phép thử | Làm song song không gộp | Team-leader quyết khi lập kế hoạch |
| A-20 `[changed]` | ADR-023 (`proposed`, 2026-11-14) đã phán phần thay ADR-005 QĐ 3, ADR-011 QĐ 2 và 6, ADR-012 QĐ 4 và 7. FEAT-004 AC-22 đã được FEAT-004 sửa (liên kết không hộp xác nhận, form giữ hộp). Còn thiếu ADR hoặc amendment cho K-1..K-7 và L-2, L-5, L-6, L-7 | Mục 3 | Không | Architect viết |
| AR-1 `[changed]` | Phần đã có lời giải: ADR-023 QĐ 2, QĐ 4 (người ra lệnh gồm người được giao phiếu, giữ nguyên). Phần còn: người duyệt theo loại (K-3) và người ra lệnh theo tác giả `@ai` (L-2) | | | |
| AR-4 `[changed]` | ADR mới cho 5 quyền đã có ở dạng ADR-023 (hai công tắc). Còn amendment cho 5 công tắc, loại đề xuất mới, người duyệt theo loại, cổng (5), mức theo đầu mục (K-1..K-7) | | | |
| AR-5 `[changed]` | Đã có lời giải ở ADR-023 QĐ 5 (M5); phần dư là QĐ 6 (L-5) | | | |
| R-3 `[changed]` | ADR-023 "Phương án đã xét" loại `<form>` đặt trong comment (chưa kiểm Helpdesk có giữ thẻ `form`) và chọn liên kết tới form Desk. R-3 vẫn cần trả lời nút bấm được trên dòng thời gian hay ngăn của bot hay không, để quyết khôi phục AC-39 nguyên văn (K-7) | | | |

---

## 3. Xung đột giữa quyết định N-1 của người và Amendment 2 / ADR-023: danh sách cho architect

Mỗi xung đột: N-1 (hoặc hệ quả trực tiếp của nó) đòi gì; Amendment 2 / ADR-023 nói gì; mặc định addendum này chọn (decide mode) để team không bị chặn; architect phải phán gì. Không có điểm nào ở đây là chọn công nghệ.

**K-1. Số công tắc và điều kiện cấp.**
- N-1: 5 quyền, mỗi quyền một công tắc riêng, mặc định tắt (kể cả site đang chạy mã ngày 13/11).
- Amendment 2 / ADR-023: 2 ô. Ô sửa code mở cả tool đề xuất và công cụ bản ghi (FEAT-004 A-24); khối "làm luôn" hiện khi nhóm nào được cấp (FEAT-004 AC-29); liên kết một lần bấm luôn có (FEAT-004 AC-25, ADR-023 QĐ 1); QĐ 4 chốt bảng cấp 4 đầu vào và "bộ tool cấp ra giống hệt hiện nay ở mọi tổ hợp".
- Mặc định đã chọn: AC-1, AC-3, AC-6, AC-11 `[changed]`; ba đầu vào mới vào cùng một hàm cấp và một bảng cấp; site `miyano` (đang bật ô code, công cụ bản ghi đang chạy) sau migrate mất công cụ bản ghi, khối "làm luôn" và liên kết một lần bấm cho tới khi người bật lại. FEAT-004 A-24 đã ghi sẵn đường sửa "thêm ô".
- Architect phán: sửa QĐ 4 sang bảng 5 đầu vào; khi (3) tắt và (2) bật thì khối "làm luôn" vắng (đổi điều kiện của FEAT-004 AC-29); ảnh chụp M4 trở thành test hồi quy với ánh xạ tương đương (AC-1); cách gating (5) ở form (K-7).

**K-2. Cảnh báo khi bật và cảnh báo hằng ngày.**
- N-1: "bật thì có cảnh báo".
- FEAT-004 A-23: "không cảnh báo khi bật", không tác vụ nền; chỉ ghi nhận rủi ro "quên tắt" ở S-6.
- Mặc định: AC-4 giữ nguyên (thông báo khi lưu, 1 dòng log người bật, cảnh báo hằng ngày nêu mọi quyền đang bật). A-23 bị thay.
- Architect phán: xác nhận AC-4 không đụng cơ chế FEAT-004; ghi lại trong ADR amendment rằng A-23 hết hiệu lực.

**K-3. Việc ngoài danh mục phải duyệt: loại đề xuất mới và người duyệt.**
- N-1: việc ngoài danh mục (chế độ `Cần duyệt`) phải được người phụ trách bấm Duyệt rồi mới làm; tài liệu nói "người phụ trách bấm duyệt" (`source-strategy.md:100,107`).
- FEAT-004 / ADR-012 / ADR-023: đề xuất chỉ cho sửa code và lệnh bench; người duyệt chỉ `ERP AI Instructor`, người được giao phiếu bị từ chối (FEAT-004 AC-26, AC-5); FEAT-004 A-21: với bản ghi không có nút duyệt nào; ADR-023 QĐ 5 chỉ mở một đường hợp lệ cho tài khoản agent tạo đề xuất, cờ chỉ được đặt ở `run_log.py` và module tool đề xuất (grep nơi khác là finding).
- Mặc định đã chọn: cùng DocType đề xuất và cùng máy trạng thái thêm một loại "thay đổi bản ghi" (AC-33); tool tạo đề xuất bản ghi đi qua đúng module tool đề xuất hiện có để giữ luật grep của ADR-023; người duyệt theo loại (AC-35, A-6): bản ghi = người được giao hoặc Instructor, code và lệnh = chỉ Instructor; kiểm lại lúc áp dụng theo tập điều kiện của loại.
- Architect phán: một DocType với loại hay hai DocType; sửa `_decider` (ADR-012 QĐ 4) theo loại; QĐ 2 của ADR-023 ("vẫn có `ERP AI Instructor`") thành "vẫn đủ điều kiện của loại"; xác nhận đường hợp lệ M5 gồm loại mới.

**K-4. Vượt ngân sách và Toàn quyền.**
- N-1: "mặc định theo chiến lược"; chiến lược: vượt ngân sách thì bot lui về L1 (`source-strategy.md:180`); H7 "mọi nhóm tool ghi lui".
- FEAT-004 AC-2 và ADR-023 QĐ 4 "Ghi nhận": Toàn quyền có hiệu lực cả ở L1, tức cả khi mức bị hạ vì vượt ngân sách; "giữ nguyên".
- Mặc định đã chọn (an toàn hơn): AC-7 `[changed]`, Toàn quyền cũng mất khi vượt ngân sách. Văn bản N-1 không nói rõ điều này, nên có lối lui: nếu architect hoặc người giữ QĐ 4, AC-7 chỉ còn "mọi nhóm trừ Toàn quyền" và As-Built ghi rõ.
- Architect phán: giữ hay sửa đoạn "Ghi nhận" của QĐ 4; nếu sửa, đổi câu cuối FEAT-004 AC-2 và test ma trận có chiều vượt ngân sách (NFR-8, ghi lý do). Người xác nhận nếu cần vì lệnh ngày 13/11 gọi nó là "khẩn cấp".

**K-5. Mức theo đầu mục và điều kiện mức của 5 quyền.**
- N-1: "mặc định theo chiến lược": mức tự chủ theo đầu mục (C chỉ L1 vì việc nhỏ cần site test).
- ADR-023 QĐ 4: hàm cấp nhận "mức hiệu lực" (mức toàn hệ thống sau khi hạ vì ngân sách); L3 cho công cụ bản ghi và đề xuất, > L0 cho Toàn quyền.
- Nếu mức đầu mục chặn cả 5 quyền thì quyền (4) mất ngay trên phiếu đầu mục C, là đầu mục cần đổi code nhất.
- Mặc định đã chọn: mức theo đầu mục chỉ áp cho đường chính (AC-31 `[changed]`); 5 quyền tính trên mức toàn hệ thống.
- Architect phán: định nghĩa "mức hiệu lực" ở QĐ 4 gồm hai khái niệm (mức cho quyền, mức cho đường chính) và ghi vào bảng cấp.

**K-6. "Làm luôn" và ngưỡng độ tin cậy 70.**
- N-1 / chiến lược: độ tin cậy dưới ngưỡng thì chỉ hỏi, không ghi.
- FEAT-004 AC-29, N-2 S-2: bot làm ngay trong lượt, không hỏi lại, thiếu đúng một thông tin mới hỏi một câu.
- Mặc định đã chọn: AC-22 `[changed]`: lệnh trực tiếp với (3) bật không bị ngưỡng chặn; (3) tắt thì dưới ngưỡng chỉ hỏi.
- Architect phán: xác nhận hai quy tắc cùng nằm trong prompt và test; không cần ADR riêng nếu K-1 được amendment.

**K-7. Duyệt trên trang phiếu so với form Desk, và cổng (5).**
- N-1 / chiến lược: Duyệt, Sửa, Từ chối bấm ngay trên comment của bot, "không cần mở màn hình khác" (`source-strategy.md:107`); một lần bấm chỉ khi (5) bật.
- ADR-023 QĐ 1: liên kết trong comment mở form Desk của đề xuất rồi tự gọi một lần POST, không hộp xác nhận; không còn đường GET (đã chặn tải trước, thẻ `<img>`, lỗi mất job do GET không commit); QĐ 6: người duyệt phải mở được Desk (chưa kiểm cho Hiếu, Việt, Tiến).
- Mặc định đã chọn: AC-11 và AC-39 `[changed]`: bấm bắt đầu từ trang phiếu, hoàn tất ở form; (5) tắt thì form không tự gọi bước duyệt và Duyệt đi qua hộp xác nhận; (5) bật thì như FEAT-004 AC-25. Lệch với `source-strategy.md:107` được ghi nhận.
- Architect phán: cổng (5) ở form (form đọc công tắc trước khi tự gọi); nếu người duyệt không vào được Desk (QĐ 6): cấp Desk hay giữ GET + cờ commit (ADR-023 đã nêu chờ researcher); R-3 có thể khôi phục AC-39 nguyên văn.

---

## 3b. Điểm khác còn lại, không do N-1

Các điểm này không do quyết định N-1; hoặc đã được giải ngay trong addendum, hoặc chờ architect hoặc người.

- **L-1. Hạn liên kết 24 giờ (A-13, AC-11).** Giải: bỏ hạn, theo ADR-023 QĐ 1. Không cần architect.
- **L-2. Người ra lệnh (AC-13).** ADR-023 QĐ 4 ghi "người ra lệnh là `authority.is_instruction`, gồm cả người được giao phiếu không có `ERP AI Instructor`, giữ nguyên"; AC-13 đòi người được bot gán không thành người ra lệnh và quyền ghi theo tác giả `@ai`, không theo 30 comment gần nhất. Giữ AC-13 nguyên chữ (an toàn hơn, chặn bot tự cấp quyền cho người nó gán). Architect phán: nếu giữ "giữ nguyên" thì AC-13 chỉ còn vế tác giả `@ai` và vế 30 comment, bỏ vế người được bot gán.
- **L-3. AC-42(b) và quyền (1), (2).** Đã giải: bỏ vế "không bị đổi bởi công cụ bản ghi chung hay Toàn quyền" vì N-1 giữ 5 quyền (xem 2.1). Rủi ro còn lại: bot có thể đổi `status` của phiếu BGĐ hoặc đầu mục E qua quyền (1), (2); có mục nhật ký (FEAT-004 AC-34, AC-35).
- **L-4. AC-12 và đề xuất code/bench.** Đã giải: cổng môi trường chỉ ở danh mục; quyền (4) không bị chặn. Hệ quả cho C4 ("không phân biệt production"): phần "chặn production" của code và lệnh không còn trong FEAT-007; C4 được phủ bằng mặc định tắt (AC-1), cảnh báo nêu môi trường (AC-4), nhật ký ghi môi trường (AC-10). Muốn chặn cứng thì mở change-request trên bước kiểm lúc áp dụng của FEAT-004 sau khi FEAT-004 merge.
- **L-5. `call_method` khi Toàn quyền bật (ADR-023 QĐ 6, chờ người).** AC-8 dưới Toàn quyền và "bot không tự đổi công tắc" chỉ bảo đảm trọn khi người chọn (a) danh sách hàm cho phép (architect khuyến nghị). Chọn (b) thì AC-8 không phủ đường gọi hàm và A-4 ghi rủi ro.
- **L-6. M5 và dữ liệu mới của FEAT-007.** ADR-023 QĐ 5 đóng mọi DocType của module app với tài khoản agent trừ hai đường hợp lệ. FEAT-007 thêm dữ liệu mới (đề xuất bản ghi, số liệu KPI theo tuần, danh sách rà soát hằng tháng, bài CSKT nháp liên kết phiếu, lịch sử sửa prompt, bộ đếm duyệt). Cần architect chốt: lần ghi nào do việc theo lịch hoặc người duyệt (không phải phiên tài khoản agent) và lần ghi nào do lần chạy của bot (cần đường hợp lệ mới trong QĐ 5). Nếu không chốt, M5 chặn chính FEAT-007.
- **L-7. Đơn vị lưu nhật ký.** `spec.md` mục Dữ liệu: "mỗi lần ghi một dòng". FEAT-004 AC-34: "một mục trong cột hành động của nhật ký lần chạy". AC-10 `[changed]` chỉ đòi đếm được theo lần ghi và truy ra mã lần chạy; designer chọn một đơn vị cho cả hai feature.
- **L-8. Tài khoản agent mang System Manager và ERP AI Instructor trên `miyano`.** ADR-023 QĐ 6 điểm 3 và FEAT-004 A-2' coi là ý định chờ người xác nhận; `spec.md` DoD "phần việc của người" và BUG-002 coi là việc gỡ role thừa. Gỡ `System Manager` thu hẹp thực chất công cụ bản ghi (FEAT-004 A-2'). Giữ nguyên dòng "gỡ role thừa" ở DoD nhưng đánh dấu chờ người trả lời câu 3 của ADR-023; không là điều kiện merge.

---

## 4. Ràng buộc chung với FEAT-004 và phụ thuộc mới

**Một cơ chế duy nhất** (mọi mục lấy từ ADR-023, FEAT-007 không dựng bản thứ hai; luật kiến trúc của ADR-023 giữ xanh):
1. Một hàm cấp và một bảng cấp tool trong registry; ba công tắc mới là đầu vào thêm (QĐ 4).
2. Một nguồn danh sách DocType cấm cho tool bản ghi và cho điều cấm cứng của danh mục (QĐ 3).
3. Một danh sách 6 vai trò cấm (FEAT-004 AC-31) cho công cụ bản ghi và cho hành động "tạo tài khoản theo mẫu" (AC-30).
4. Một đường ghi nhật ký (QĐ 5: chỉ `run_log.write_entry`) và một dạng mục (FEAT-004 AC-34, AC-35).
5. Một cơ chế comment kết quả (FEAT-004 AC-28), một máy trạng thái và một hàng đợi áp dụng đề xuất (ADR-012).
6. Một ngoại lệ cho phép thử tĩnh FEAT-006 AC-9 (A-19).

**Phụ thuộc mới của FEAT-007 vào FEAT-004** (tech-lead xếp thứ tự merge; N-3 vẫn là build song song):

| AC của FEAT-007 | Cần từ FEAT-004 / ADR-023 | Va chạm file nếu build song song |
|---|---|---|
| AC-1, AC-3, AC-6, AC-7 | M4 (một hàm cấp), FEAT-004 AC-2 | registry, runner, prompts |
| AC-5, AC-8 | M3 (một nguồn danh sách cấm) | tool bản ghi |
| AC-10 | FEAT-004 AC-34, AC-35 | runner, nhật ký |
| AC-11, AC-39 | M1 (form và liên kết) | liên kết ký, form đề xuất |
| AC-23, AC-33 | FEAT-004 AC-28 (chưa có mã) | job áp dụng, comment |
| AC-35 | M2 (kiểm lúc áp dụng), ADR-012 QĐ 4 | job áp dụng, controller đề xuất |
| mọi AC ghi dữ liệu app mới | M5 | controller của DocType mới |

Gói 1 của FEAT-007 sửa cùng các file mà M1..M5 sửa; nếu không xếp thì xung đột merge gần như chắc chắn (N-3 đã chấp nhận). Gói 2 đến Gói 6 độc lập với FEAT-004 trừ AC-23 và AC-33.

---

## 5. Đổi Definition of Done, NFR và bảng phủ

**DoD (phần build), thay các dòng tương ứng của `spec.md`:**
- `[changed]` "Mọi AC-1..AC-64 đạt" → 61 AC của FEAT-007 đạt (64 trừ AC-2, AC-14, AC-15). Ba AC `[dropped]` do FEAT-004 đạt; FEAT-007 chỉ chạy lại chúng như hồi quy qua `cmd.test` trên cây đã merge.
- `[changed]` "ADR mới hoặc amendment cho A-20 và AR-1..AR-5" → ADR-023 đã phán phần của nó; còn amendment hoặc ADR cho K-1..K-7 và L-2, L-5, L-6, L-7; câu R-1..R-5 vẫn có trả lời trong `research.md`.
- `[changed]` "Danh sách test bị sửa vì spec đổi" gồm thêm các test của FEAT-004 mà K-1, K-4, K-5, K-6 làm đổi: ma trận 32 tổ hợp của FEAT-004 AC-1 và AC-2, ảnh chụp M4, test cấp công cụ bản ghi trong `test_site_api`, test prompt "làm luôn" trong `test_classification`; mỗi chỗ ghi lý do (STD-TEST-5).
- `[changed]` `cmd.test` xanh: chạy trên cây đã gồm sửa 5 test đỏ của FEAT-004 (A-18 `[changed]`); lần chạy cả app khoảng 558 s theo DoD FEAT-004.
- `[changed]` tài liệu người dùng (phần sau G4): mô tả 5 công tắc viết một lần, ở FEAT-007 (FEAT-004 DoD sau G4 mô tả hai ô); phần liên kết Duyệt/Từ chối và ai mở được giữ ở FEAT-004.
- Phần việc của người: dòng "gỡ role thừa của tài khoản agent (BUG-002)" chờ câu 3 của ADR-023 (L-8).

**NFR-8 `[changed]`:** danh sách test được phép sửa theo spec gồm thêm test của FEAT-004 nêu trên và bỏ "2 bước xác nhận AC-22 của FEAT-004" (FEAT-004 đã tự sửa AC-22: liên kết không hộp xác nhận, form giữ hộp; FEAT-007 AC-11 chỉ thêm ca (5) tắt).

**Phụ thuộc gói (`spec.md` bảng Gói):** Gói 1 từ AC-1..AC-15 thành 12 AC (bỏ AC-2, AC-14, AC-15) và phụ thuộc thêm FEAT-004 (mục 4). Gói 2 phụ thuộc thêm FEAT-004 AC-28 ở AC-23. Gói 3 phụ thuộc thêm FEAT-004 AC-28 và ADR-012 ở AC-33, AC-35.

**Bảng phủ C1–C6, G1–G13, H1–H14 sau khi sửa** (chỉ ghi các dòng đổi; mọi dòng không ghi giữ như `spec.md`):

| Dòng | AC của FEAT-007 sau sửa | Phần chuyển sang FEAT-004 |
|---|---|---|
| C1 | AC-1, AC-3, AC-4, AC-5, AC-7, AC-10 | FEAT-004 AC-30, AC-31 (a)(c)(d), AC-34, AC-35 |
| C2 | AC-1, AC-3, AC-5, AC-8, AC-29, AC-33 | FEAT-004 AC-1 (thay AC-2) |
| C3 | AC-1, AC-3, AC-6 | FEAT-004 AC-1, AC-29 (thay AC-2) |
| C4 | AC-1, AC-3, AC-4, AC-10, AC-12 (L-4: chỉ còn mặc định tắt, cảnh báo và nhật ký môi trường) | FEAT-004 AC-2(a) (thay AC-2) |
| C5 | AC-11, AC-34, AC-35, AC-39 | FEAT-004 AC-25, AC-26, M1 (cơ chế); FEAT-004 AC-27, M2 (thay AC-14) |
| C6 | AC-8 | không |
| H1 | AC-21 | không |
| H2 | AC-22 | không |
| H3 | AC-23 | FEAT-004 AC-28 (kết quả áp dụng) |
| H4 | AC-31..AC-37 | FEAT-004 AC-25, NFR-10 (một lần thắng) |
| H6 | AC-8, AC-9 | không |
| H7 | AC-7 | FEAT-004 AC-2 (vế còn lại) |
| H8 | AC-10 | FEAT-004 AC-34, AC-35 |
| H10 | AC-12 | không |
| G5, G6 | AC-42, AC-43, AC-44 | không |

**Xác nhận phủ.** C1–C6, G1–G13 và H1–H14 vẫn được phủ hoặc đã chuyển: không dòng nào mất tiêu chí. Các dòng chuyển một phần sang chủ FEAT-004 là C1, C2, C3, C4, C5, H3, H4, H7, H8, kèm điều kiện khôi phục ở mục 2.2; G1–G4, G7–G13, H1, H5, H9, H11–H14 không chạm vào. Ngoại lệ phải ghi: C4 và H10 mất phần "chặn cứng code và lệnh ở `production`" (L-4), chuyển thành mặc định tắt cộng cảnh báo và nhật ký môi trường; H14 vẫn ở Ngoài phạm vi N-7 của `spec.md`.

**Out of scope (thêm):** hạn dùng cho liên kết duyệt (L-1); chặn cứng code và lệnh `bench` theo môi trường (L-4); phán quyết cho các câu K-1..K-7 và L-2, L-5, L-6, L-7, L-8 (việc của architect và người, không của analyst).
