Feature: FEAT-007
Stage: analyze
Author-agent: analyst
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G1 không áp dụng cho FEAT-007 (chỉ có G5). Addendum này chưa được duyệt, giống spec.md, spec-addendum-1.md, spec-addendum-2.md. -->

# Spec addendum 3 FEAT-007 — ba hành vi đích của người (một hướng xử lý, việc tự làm được thì làm luôn, bấm Duyệt thì bot tự làm)

**Quy tắc đọc.** File này thắng `spec.md`, `spec-addendum-1.md` và `spec-addendum-2.md` ở mọi chỗ các file khác nhau; chỗ nào không nhắc thì ba file kia giữ nguyên. Không dòng nào của ba file kia bị xóa: AC bị đổi giữ nguyên bản ở chỗ cũ và được đánh dấu ở đây bằng `[changed]`; AC thêm mới đánh số tiếp từ AC-65 và đánh dấu `[new]`. "FEAT-004 AC-n" là tiêu chí của `docs/team/features/FEAT-004/spec.md` mục "Amendment 2"; "AC-n" không kèm tên là của FEAT-007. Đường dẫn nguồn tính từ `docs/team/features/FEAT-007/` trừ khi ghi khác.

## 1. Mục tiêu

Giả thuyết (độ tin cậy 80%): người muốn app làm đúng một chuỗi ba việc cho mỗi phiếu: bot đưa hướng xử lý một lần duy nhất; việc bot tự làm được thì làm luôn; việc cần người đồng ý thì hiện thành một đề xuất có nút Duyệt, bấm Duyệt là bot tự làm, không còn bước nào khác của người. Chưa tới 90% vì: (a) câu của người ("bỏ phần yêu cầu gì đi", journal 22:03) mơ hồ, team-leader đã chọn cách đọc "thôi đưa câu hỏi cho người, làm theo khuyến nghị" (journal 22:10 (a)); (b) tôi chưa đọc mã của ngăn Duyệt (U7b chưa dựng); (c) phải đảo một giả định của spec (A-2, "vắng mặt trong danh mục = cấm"), điểm này có thể sai ý người (Q-10).

- **Outcome:** trên một phiếu ở mức hiệu lực đủ cao, người thấy đúng một comment "Hướng xử lý"; việc nào bot tự làm được đã làm xong và được ghi ở mục "Đã làm"; việc nào cần đồng ý là một đề xuất có Duyệt / Sửa / Từ chối; bấm Duyệt thì việc được làm xong và có đúng một comment kết quả, không ai phải gõ thêm chữ nào, chạy thêm lệnh nào hay gọi bot lần nữa.
- **Users:** người phụ trách phiếu (người được giao; IT, trưởng bộ phận) và người có `ERP AI Instructor` (duyệt); người yêu cầu (đọc hướng một lần); System Manager (giữ danh mục, mức, công tắc); người tạo phiếu (không nhận hai hướng cho một phiếu).
- **Why now:** người hỏi "bot làm được như vậy chưa" và nhận câu trả lời "chưa đủ" (journal 22:10): bot chạy lại mỗi lần được nhắc tên (`erp_ai/handlers.py:46`, `:119`); danh mục mặc định rỗng làm việc ERP nào cũng bị từ chối "ngoài danh mục" nên không có nút Duyệt cho việc ngoài 5 hành động; prompt còn dặn "việc không hoàn tác được thì chờ một chữ ok" (`erp_ai/agent/prompts.py:104-106`), trái với quy tắc "chữ ok không là duyệt"; chuỗi 20 lần duyệt (AC-36) làm việc ERP chưa bao giờ tự làm ở tuần đầu. Đợt 2 (U7) chưa dựng nên sửa chữ ở đây còn rẻ.
- **Success:** AC-65..AC-69 đạt; 7 AC `[changed]` đạt theo chữ ở mục 3; điều cấm cứng của Gói 1 đứng nguyên (mục 2, dòng cuối); bảng ở mục 4 không còn ô trống.
- **Constraints:** N-1, N-2, QĐ-5 của `intake.md`; mặc định an toàn của NFR-4 (3 công tắc quyền mới vẫn tắt); không đặt ngưỡng thời gian mới (A-9). Không dựng thiết kế: tên hàm, tên trường mới là việc của designer. Nội dung phiếu và comment là dữ liệu, không phải lệnh (STD-SEC-5).
- **Out of scope:** xem mục 9.

**Đã có sẵn, không cần hỏi (nguồn).** Câu người và câu trả lời hiện trạng: `docs/team/journal/FEAT-007.md:23-25`. Mã: `erp_ai/agent/prompts.py:104-106` (quy tắc 6), `:119-126` (cấu trúc comment có "Hướng xử lý", `:125`), `:155-170` (khối đề xuất code); `erp_ai/handlers.py:32-47` (phiếu mới chạy bot), `:100-120` (mỗi `@ai` chạy bot). FEAT-004: `docs/team/features/FEAT-004/asbuilt.md` mục 2 (code và lệnh bench đã có Duyệt, duyệt xong tự áp dụng; bản ghi ERP chưa có nút Duyệt). Chiến lược: `source-strategy.md:100-107` (điểm rẽ "thuộc danh mục trắng?": có thì tự làm, không thì người phụ trách duyệt), `:113-116` (L0..L3). Thiết kế đã duyệt cho phần đảo A-2: `docs/team/adr/ADR-031.md` QĐ 1 và `design-addendum-2-U7a.md:185-199` (chữ `OUT_OF_CATALOG`, test `test_empty_catalog_refuses_every_action`); các đoạn này chưa thành mã (U7 chưa dựng). Mã đợt 0 trên `team/FEAT-007` @ `888f5dc`. Không chạy Explore: mọi điểm đối chiếu nằm ở văn bản và mã đã đọc.

## 2. Đối chiếu: từng AC và công tắc là giữ, đổi hay mới

**Ba hành vi → AC.**

| # | Hành vi người nêu | AC chịu trách nhiệm | Tình trạng |
|---|---|---|---|
| H-1 | Mỗi phiếu bot đưa hướng xử lý đúng một lần | AC-65 `[new]`; AC-23 `[changed]`, AC-41 `[changed]`; AC-22 giữ | trước đây không có luật "một lần" |
| H-2 | Việc bot tự làm được thì làm luôn | AC-66 `[new]`; AC-36 `[changed]`; AC-32, AC-21, AC-63 giữ | ghi phiếu đã làm luôn; việc ERP tự làm chỉ qua AC-36 |
| H-3 | Việc cần đồng ý: một đề xuất có nút Duyệt, bấm là bot tự làm | AC-67 `[new]`, AC-68 `[new]`; AC-29, AC-30, AC-33, AC-64 `[changed]`; AC-35, AC-39 giữ | trước đây việc ngoài danh mục bị từ chối, không có nút |
| E2E | Cả ba trên một phiếu thật | AC-69 `[new]` | kiểm có đầu ra trên site dev |

**Năm AC người nêu tên, và các AC liên quan.**

| AC | Tình trạng | Một dòng |
|---|---|---|
| AC-29 | `[changed]` | Danh mục mặc định rỗng vẫn rỗng, nhưng "vắng mặt" không còn là cấm: việc không vướng điều cấm cứng và không có dòng `Cấm` thành đề xuất chờ Duyệt. Đảo A-2 (Q-10) |
| AC-32 | giữ | Ở L1 không tool ghi ERP; hướng xử lý là chữ, không có nút. Hệ quả có chủ ý: đầu mục C, E (cap mặc định L1) chỉ nhận hướng bằng chữ |
| AC-33 | `[changed]` | Thêm trường hợp thứ ba tạo đề xuất (hành động không có dòng nào phủ); đề xuất của một lần chạy được tạo cùng lần đưa hướng |
| AC-36 | `[changed]` | Bốn điều kiện giữ, số 20 giữ (Q-11); chỉ đổi chỗ báo lại: việc tự làm trong lần đưa hướng nằm ở mục "Đã làm", không thêm comment |
| AC-39 | giữ | Duyệt / Sửa / Từ chối trong ngăn của bot; thêm điểm đo ở AC-68 |
| AC-30 | `[changed]` | Câu cuối: hành động tuân chế độ của dòng; không có dòng thì như `Cần duyệt` |
| AC-23 | `[changed]` | Comment định tuyến và các thông báo từ chối của lần đưa hướng gộp vào comment hướng xử lý |
| AC-41 | `[changed]` | Người tạo trả lời vẫn chạy bot một lần; không đăng "Hướng xử lý" lần hai |
| AC-64 | `[changed]` | Tạo Project luôn là đề xuất; dòng danh mục không còn là điều kiện |
| AC-22 | giữ | Câu hỏi dưới ngưỡng không tính là hướng xử lý |
| AC-12, AC-31, AC-34, AC-35, AC-37, AC-38 | giữ | AC-12: chữ giữ, comment "cần làm trên site test" đi theo AC-23. AC-38: AC-65 vẫn đúng khi prompt bị ghi đè |
| AC-1, AC-3, AC-6, AC-8, AC-11 | giữ | Ba công tắc: mục 5. AC-6: danh sách cặp câu của designer thêm hai cặp (mục 3, AC-66) |

**Điều cấm cứng của Gói 1 không đổi.** Chữ của AC-1..AC-13 không đổi: xóa bản ghi, sửa Role Permission (kể cả Custom Field `permlevel`), migrate và deploy, chứng từ đã submit (AC-5 và các phần `[dropped]` về FEAT-004); phiếu nhóm loại trừ và cờ không dùng AI không đọc, không ghi (AC-8, AC-9); cổng môi trường `test` / `production` (AC-12). Phụ lục này không mở thêm đường nào qua các điều đó: đề xuất mới nằm sau chúng (mục 3, AC-29).

## 3. Văn bản đầy đủ của AC mới và AC đổi

Quy ước kiểm như `spec.md` mục Tiêu chí nghiệm thu. "Mức hiệu lực" như `spec-addendum-1.md` (AC-31).

### 3.1 AC mới

| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-65 `[new]` | [H-1, H3] Mỗi phiếu nhận đúng một lần "Hướng xử lý" của bot: số comment của tài khoản bot có mục "Hướng xử lý" trên một phiếu ≤ 1 vào mọi lúc, bất kể số lần chạy và nguồn kích hoạt (tạo phiếu, quét bù AC-16, `@ai` bao nhiêu lần, người tạo trả lời AC-41, sự kiện Task). (a) Lần chạy đầu tiên ở mức hiệu lực ≥ L1, không bị bỏ qua (AC-23) và đạt ngưỡng tin cậy (AC-22), đăng comment hướng xử lý có: nhận định, căn cứ, hướng xử lý, "Đã làm" (AC-66), "Chờ duyệt" (AC-67), "Cần ai quyết" khi có. (b) Lần chạy dưới ngưỡng đăng câu hỏi theo AC-22; câu hỏi không tính là hướng; hướng được đăng ở lần chạy kế tiếp đạt ngưỡng. Lần chạy lỗi không tính là đã đưa hướng (lần chạy lại vẫn được đưa). (c) Sau khi có hướng, lần chạy sau không đăng mục "Hướng xử lý" lần hai: nếu người ra lệnh việc mới qua `@ai` thì làm theo quyền hiện có và đăng comment kết quả (AC-23, AC-33) không có mục đó; không có việc nào thì không đăng comment và có 1 dòng log nêu "đã có hướng xử lý". (d) Hệ thống từ chối lần đăng thứ hai kể cả khi phần prompt bị ghi đè hoặc xóa (AC-38): tool trả lỗi cho model, 0 comment thêm. BA note (AC-62), trả lời người tạo (AC-40), nhắc hạn (AC-57, AC-58), comment kết quả, comment trạng thái, câu hỏi tách phiếu (AC-28) không phải "Hướng xử lý" và không tính vào số này | Test stub cổng model, 9 chuỗi sự kiện, đếm comment có mục đó: tạo phiếu → 1; tạo + `@ai` ×3 → 1; dưới ngưỡng (69) rồi người tạo trả lời, lần sau đạt ngưỡng → 1 câu hỏi + 1 hướng; quét bù sau lần chạy thành công → 1; lần chạy lỗi rồi chạy lại → 1; hướng + Duyệt → 1 hướng + 1 comment kết quả; `@ai` sau hướng với lệnh tạo Task → Task có, 0 hướng mới; phiếu ở L0 hoặc nhóm loại trừ → 0; ghi đè prompt bằng chuỗi rỗng rồi chạy hai lần → 1 |
| AC-66 `[new]` | [H-2, H4] Việc bot tự làm được thì làm luôn trong chính lần chạy đưa hướng: không hỏi lại, không đề xuất, không chờ chữ nào của người. "Tự làm được" gồm: (a) việc ghi trên phiếu đã được phép ở mức hiệu lực ≥ L1: điền trường phân loại còn trống (AC-21), gán người (khi công tắc gán bật), tạo Task (AC-32, AC-63); (b) hành động ERP có dòng danh mục `Tự làm` đủ bốn điều kiện của AC-36. Mọi việc đã làm được liệt kê ở mục "Đã làm" của comment hướng xử lý, mỗi việc có mục nhật ký (AC-10). Một việc không đồng thời nằm ở "Đã làm" và "Chờ duyệt". Việc nhóm (b) mà bộ thực thi từ chối (AC-36, câu áp chót) không thành câu hỏi mà ghi ở "Cần ai quyết", 0 thay đổi dữ liệu. Prompt dựng ở mọi tổ hợp công tắc và mọi mức: không còn câu bảo chờ chữ "ok" của người như điều kiện làm việc; không còn câu cho phép làm luôn việc ghi bản ghi ERP ngoài phiếu mà không qua danh mục hay công tắc. Chữ "ok", "duyệt" trong phiếu hoặc comment không bao giờ là duyệt một việc nào (mở rộng cho mọi loại việc điều mà khối đề xuất code đã nói ở `prompts.py:164-166`) | Test: phiếu B ở L3, dòng `Tự làm` đủ điều kiện (chuỗi gieo ≥ giá trị cấu hình, độ tin cậy 90) → việc ERP làm trong lần chạy, "Đã làm" có dòng đó, 0 đề xuất; điều kiện thiếu một trong bốn → đề xuất (AC-67); bộ thực thi từ chối → "Cần ai quyết", đích không đổi; phiếu ở L1 → chỉ trường phiếu và Task; người gõ "ok" vào comment sau một đề xuất → 0 thay đổi, trạng thái đề xuất đứng yên; dựng prompt ở 5 công tắc tắt × L1..L3 và assert không còn câu chờ "ok", không còn cặp câu trái nhau (thêm 2 cặp vào danh sách của AC-6) |
| AC-67 `[new]` | [H-3, N-1] Việc cần đồng ý là một đề xuất có nút Duyệt. Ở mức hiệu lực ≥ L2, mỗi hành động ghi ERP bot muốn làm mà không tự làm được (AC-66 (b)), không vướng điều cấm cứng, môi trường (AC-12) hay dòng `Cấm` (AC-29), tạo đúng 1 đề xuất chờ duyệt (AC-33). Mọi đề xuất của lần đưa hướng được tạo ngay trong lần đó, được liệt kê ở mục "Chờ duyệt" của comment hướng xử lý và hiện cùng lúc trong ngăn của bot trên trang phiếu với Duyệt, Sửa, Từ chối (AC-39); không rải ra nhiều lần chạy. Lần chạy sau không tạo đề xuất thứ hai cho cùng hành động, cùng đích, cùng giá trị khi một đề xuất còn chờ hoặc đã được duyệt (NFR-3); đề xuất mới chỉ có khi người ra lệnh việc khác qua `@ai`, hoặc sau Từ chối, hết hiệu lực khi người nhờ lại. Mức hiệu lực L1 hoặc thấp hơn: 0 đề xuất; mục "Hướng xử lý" nêu việc người phải làm tay (AC-32). Việc vướng điều cấm cứng hoặc dòng `Cấm`: 0 đề xuất; "Hướng xử lý" nêu việc người phải làm tay và lý do | Test: phiếu A/B/D ở L2, danh mục rỗng, bot muốn 2 hành động → 2 đề xuất trong lần chạy đầu, cả hai có trong "Chờ duyệt" và trong ngăn; chạy `@ai` hai lần → vẫn 2; đề xuất bị từ chối rồi người `@ai` nhờ lại → đề xuất mới; phiếu C hoặc E (cap L1) → 0 đề xuất; hành động chạm điều cấm cứng và hành động có dòng `Cấm` → 0 đề xuất, "Hướng xử lý" nêu việc tay |
| AC-68 `[new]` | [H-3] Bấm Duyệt là bot tự làm. Sau Duyệt (và bước xác nhận khi công tắc (5) tắt, AC-39) không còn bước nào của người: không gõ chữ, không `@ai`, không mở màn hình khác, không chạy lệnh. Việc áp dụng do job nền chạy theo AC-33 (một lần, kiểm lại người duyệt AC-35, hết hiệu lực khi đích đổi), 0 lời gọi model (giá trị đã nằm trong đề xuất hoặc do người sửa), kết thúc bằng đúng 1 comment kết quả và 1 mục nhật ký. Thời gian từ Duyệt tới comment kết quả được ghi vào nhật ký để đo; không là ngưỡng (A3-8). Duyệt rồi gỡ điều kiện người duyệt trước khi job chạy: trạng thái "Lỗi" như AC-35 | Test: Duyệt → số lời gọi model của stub = 0, đích đổi, 1 comment kết quả, 1 mục nhật ký có thời gian; Duyệt khi (5) tắt phải qua hộp xác nhận, khi (5) bật không; Duyệt hai lần → áp một lần; không có lần chạy bot nào được xếp hàng sau Duyệt |
| AC-69 `[new]` | [H-1, H-2, H-3] Kiểm đầu-cuối ba hành vi trên một phiếu thật ở site dev `miyano`. Chuẩn bị: bot bật, mức toàn hệ thống L3, giới hạn đầu mục B = L3, 5 công tắc quyền tắt, danh mục rỗng, môi trường `test`. (1) Tạo phiếu đầu mục B nhờ đổi nhóm hàng của một Item: có đúng 1 comment "Hướng xử lý" với "Đã làm" (phân loại, gán) và "Chờ duyệt" (1 đề xuất đổi nhóm hàng); nhắc `@ai` hai lần → vẫn 1 comment như vậy. (2) Trong ngăn của bot, bấm Duyệt rồi xác nhận: Item đổi nhóm, có 1 comment kết quả, nhật ký không có lời gọi model sau Duyệt. (3) Thêm dòng `Tự làm` cho hành động đó đầu mục B, đặt chuỗi duyệt = 1 (hoặc gieo đủ chuỗi), tạo phiếu tương tự: Item đổi ngay trong lần chạy đầu, "Đã làm" có việc đó, 0 đề xuất. (4) Đặt giới hạn đầu mục B = L1, tạo phiếu tương tự: 1 comment hướng bằng chữ, 0 đề xuất, Item không đổi. (5) Gõ "ok" vào comment sau một đề xuất đang chờ: không đổi gì | Kiểm có đầu ra, `ui: false`: người thử thao tác, dán ảnh trang phiếu (comment hướng, ngăn có đề xuất, sau Duyệt), dòng nhật ký của từng bước và số lời gọi model; đặt lại cấu hình sau khi thử. Chỉ nghiệm thu sau khi U7a, U7b vào `develop` cùng lượt (như AC-39) |

### 3.2 AC đổi

| Mã | Tiêu chí mới (đo được) | Cách kiểm | Vì sao đổi |
|---|---|---|---|
| AC-23 `[changed]` | Mọi chữ của addendum 2 giữ, thêm: khi một lần chạy đưa hướng (AC-65), mọi nội dung của lần chạy gộp vào đúng 1 comment hướng xử lý: trường đã ghi, người gán, Task tạo, việc từ chối vì môi trường hoặc danh mục ("cần làm trên site test", AC-12), danh sách "Chờ duyệt"; không đăng comment định tuyến riêng. Comment đề xuất của từng đề xuất (AC-33) và các comment kết quả sau đó giữ như addendum 2 | Test ma trận 9 tình huống như addendum 1 + 1 ca: lần chạy đầu thành công có ghi trường, gán, Task và 1 đề xuất → số comment mang nội dung định tuyến = 1 và nằm chung với comment hướng; ca việc bị từ chối vì `production` trong lần đưa hướng → không có comment riêng | Người chỉ muốn đọc hướng một lần; "mỗi hành động một comment" (H3) giữ cho kết quả sau Duyệt |
| AC-29 `[changed]` | [H5, C2] Danh mục trắng nằm trong cấu hình; mặc định không có dòng nào. Một hành động ghi ERP của đường chính (5 hành động có tên và đề xuất thay đổi bản ghi) có đúng một kết cục, xét theo thứ tự: (1) điều cấm cứng (xóa, Role Permission, chứng từ đã submit, DocType của app, 6 vai trò cấm, trường mật khẩu và khóa), và cổng môi trường của AC-12: từ chối, dữ liệu không đổi, không bao giờ thành đề xuất, không dòng nào mở được; (2) dòng `Cấm` phủ đúng hành động, DocType, trường, đầu mục: từ chối với thông báo "danh mục cấm việc này"; (3) còn lại theo dòng phủ nó (`Cần duyệt` hoặc `Tự làm`); không dòng nào phủ thì coi như `Cần duyệt`: tạo đề xuất chờ duyệt, không từ chối. Dòng `Tự làm` là cách duy nhất để một hành động ERP chạy không cần duyệt (AC-36). Dòng danh mục có hiệu lực từ lần chạy kế tiếp, không deploy. Lưu bị chặn khi dòng trỏ vào điều cấm cứng hoặc hành động không có. Danh mục không cổng việc ghi trên phiếu và công cụ của 5 quyền (addendum 1). Hành động "tạo tài khoản theo mẫu" vẫn bị từ chối khi chưa có mẫu | Test: danh mục rỗng × 6 hành động (5 có tên và đổi trường) ở mức ≥ L2 → đề xuất, đích không đổi; × điều cấm cứng (xóa, Role Permission, chứng từ submit, DocType của app, vai trò cấm) → từ chối, 0 đề xuất; × `production` cho 6 loại của AC-12 → từ chối; thêm dòng `Cấm` → từ chối; thêm dòng `Cần duyệt` → như không dòng; thêm dòng `Tự làm` → chỉ dòng đó, đúng trường và đầu mục, đi AC-36; lưu 4 dòng cấm → bị chặn | Người nêu "việc cần đồng ý thì một đề xuất có nút Duyệt"; N-1 chữ gốc và chiến lược (`source-strategy.md:100,107`) cũng nói việc ngoài danh mục đi vào Duyệt, không bị cấm. Đảo A-2 (A3-4, Q-10) |
| AC-30 `[changed]` | Năm hành động có tên: nguyên văn addendum 2, riêng câu cuối thành: mỗi hành động tuân chế độ của dòng danh mục phủ nó (AC-33, AC-36); không có dòng thì đi như `Cần duyệt` (AC-29); riêng tạo Custom Field luôn đi đường `Cần duyệt` (addendum 2) | Test 5 hành động × (1 ca đúng + 1 ca bị từ chối) như `spec.md`; thêm ca mỗi hành động với danh mục rỗng → đề xuất | Theo AC-29 |
| AC-33 `[changed]` | Chữ của addendum 2 giữ, thêm: một hành động tạo đề xuất chờ duyệt thuộc loại "thay đổi bản ghi" ở ba trường hợp: dòng `Cần duyệt`; dòng `Tự làm` chưa đủ điều kiện AC-36; không có dòng nào phủ (AC-29). Các đề xuất của một lần đưa hướng được tạo trong lần đó (AC-67) | Test của addendum 2 giữ; thêm 1 ca danh mục rỗng → đề xuất đã tạo, đích không đổi tới khi Duyệt | Theo AC-29, AC-67 |
| AC-36 `[changed]` | Bốn điều kiện giữ nguyên chữ của addendum 2 (dòng `Tự làm`; không thuộc nhóm luôn cần duyệt; mức hiệu lực L3; độ tin cậy ≥ ngưỡng; chuỗi duyệt không sửa ≥ giá trị cấu hình, mặc định 20, ngoài 1..100 coi là 100). Đổi chỗ báo lại: việc tự làm trong lần đưa hướng nằm ở mục "Đã làm" của comment hướng xử lý (AC-66), không thêm comment; việc tự làm trong lần chạy khác (do `@ai` hoặc người tạo trả lời) báo bằng đúng 1 comment kết quả. Mỗi lần tự làm có 1 mục nhật ký. Số 20 là mặc định đang dựng (Q-11) | Test biên 19 / 20, ngưỡng 69 / 70 / 80, chuỗi 0 / 101 / -1 của addendum 2; thêm 2 ca: tự làm trong lần đưa hướng → 0 comment mới ngoài comment hướng; tự làm do `@ai` → 1 comment kết quả | Hợp nhất với "một lần" (AC-65) |
| AC-41 `[changed]` | Chữ của `spec.md` giữ, thêm: bot chạy một lần cho tin của người tạo không đăng mục "Hướng xử lý" lần hai nếu phiếu đã có hướng (AC-65 (c)); nếu phiếu mới có câu hỏi dưới ngưỡng, lần chạy này là lần được đăng hướng (AC-65 (b)) | Thêm 2 ca vào test 4 ca của `spec.md`: trả lời sau hướng → 0 hướng mới; trả lời sau câu hỏi dưới ngưỡng → 1 hướng | Theo AC-65 |
| AC-64 `[changed]` | Chữ của addendum 2 giữ, trừ chữ "chỉ khi có dòng danh mục `Cần duyệt` cho hành động đó" nay là: tạo Project luôn là đề xuất chờ duyệt (không bao giờ tự làm), không cần dòng danh mục; dòng `Cấm` chặn; điều kiện mức (≥ L2 cho đầu mục C, Q-3) giữ | Test: không dòng → đề xuất, 0 Project trước Duyệt; dòng `Tự làm` → vẫn đề xuất; dòng `Cấm` → từ chối; giới hạn C = L1 → không tool, 0 Project | Theo AC-29 |

## 4. Bảng: hành vi → AC → đơn vị build → task đợt 0 đã merge bị ảnh hưởng

Đơn vị theo `arch-impact.md` mục "Đơn vị build và thứ tự merge". U1, U2, U3, U4b, U5b, U6b, U7, U8 chưa dựng; chỉ U0, U4a, U5a, U6a có task đã merge. "Đã merge" theo `tasks.md` và `team/FEAT-007` @ `888f5dc`.

| Hành vi | AC | Đơn vị build | Task đợt 0 đã merge bị ảnh hưởng |
|---|---|---|---|
| H-1 Hướng xử lý một lần | AC-65 `[new]`, AC-23 `[changed]`, AC-41 `[changed]`, AC-22 giữ | U4b (lượt chạy, đăng comment, cờ "đã có hướng", `@ai`); U6b (trigger người tạo trả lời, AC-41); U1 (prompt nền, danh sách cặp câu AC-6) | Không. T27, T62 (chữ comment hỏi tách phiếu), T24..T26 (định tuyến) không đụng; AC-65 không phụ thuộc mã đợt 0 |
| H-2 Việc tự làm được thì làm luôn | AC-66 `[new]`, AC-36 `[changed]`; AC-32, AC-21, AC-63 giữ | U1 (prompt nền, bỏ câu chờ "ok"); U4b (ghi trường, gán, Task cùng lượt); U7a, U7b (dòng `Tự làm`, bộ thực thi, điều kiện AC-36); U8 (nhiều Task) | T2 (đã merge): mô tả ô `permission_level` nói "L2 có công cụ như L1", lệch với AC-33 từ trước, sửa chữ khi chỉnh T10; T7 (cap mặc định A L2, B L3, C L1, D L2, E L1, F L3) giữ, không đổi mã. T35..T37 (che bí mật, đọc Error Log) không đụng |
| H-3 Duyệt thì bot tự làm | AC-67 `[new]`, AC-68 `[new]`, AC-29, AC-30, AC-33, AC-64 `[changed]`; AC-35, AC-39 giữ | U7a (quy tắc kết cục của hành động, đề xuất, job áp dụng); U7b (ngăn, nút Duyệt, `Tự làm`); U3 (cổng (5), nhật ký, thời gian Duyệt → kết quả); U8 (AC-64) | T10 (đã merge `a9e0704`): chữ mô tả của ô `catalog_rules` ("Không có dòng nào = bot không ghi ERP ngoài phiếu") sai theo AC-29; sửa chữ, kiểm `test_doctype_descriptions`. T8 (`c0ae410`: bảng con, chế độ mặc định `Cần duyệt`), T11 (hình dạng dòng), T9 (điều cấm cứng): giữ, không đổi mã hay mặc định |
| Cả ba | AC-69 `[new]` | Mọi đơn vị trên, chạy sau U7a, U7b | Không |

Tóm lại: không task đợt 0 nào đổi mã, mặc định hay dữ liệu; hai chỗ chỉ đổi chữ mô tả trên form (T10, T2); phần phải sửa nằm ở tài liệu thiết kế của U7a, U7b, U8, U1 chưa dựng và ở ADR-031 QĐ 1 (mục 8).

## 5. Ba công tắc `act_now_enabled`, `one_click_approval_enabled`, `record_tools_enabled`

Cả ba giữ tên, giữ mặc định tắt, giữ cảnh báo khi bật (AC-4), giữ giá trị sau migrate (AC-1). Ba hành vi của phụ lục này không cần công tắc nào trong ba:

| Công tắc | Tình trạng | Quan hệ với ba hành vi |
|---|---|---|
| `record_tools_enabled` (2) | giữ nguyên AC-1, AC-3, AC-8, AC-29 (không cổng danh mục) | H-2 và H-3 chạy trên đường chính, không qua công tắc này. Bật công tắc này chỉ thêm đường lệnh trực tiếp của người (ghi thẳng, L3, người ra lệnh), như cũ. Bật hay tắt, AC-65 vẫn đúng: một hướng mỗi phiếu |
| `act_now_enabled` (3) | giữ nguyên AC-3, AC-6, AC-22 (phạm vi) | Khác H-2. "Làm ngay" của công tắc này là làm theo lệnh của người ra lệnh, không bị ngưỡng tin cậy chặn. H-2 là việc bot tự làm theo chính nó, không cần người ra lệnh, luôn tuân ngưỡng (AC-22) và AC-36. Hai thứ cùng tồn tại, không thay nhau |
| `one_click_approval_enabled` (5) | giữ nguyên AC-3, AC-11, AC-39 | Mặc định tắt: Duyệt trong ngăn có một bước xác nhận (AC-39); H-3 vẫn đạt vì bước cuối của người là Duyệt, xác nhận (AC-68). Bật: một lần bấm. Đổi mặc định là Q-12 |

## 6. Giả định đổi hoặc mới (decide mode, đủ 4 trường)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A3-1 | "Một lần" tính theo mục "Hướng xử lý" trong comment của bot: tối đa 1 mỗi phiếu; câu hỏi dưới ngưỡng không tính; lần `@ai` sau chỉ làm việc và báo kết quả | Câu người: "chỉ đưa ra hướng xử lý 1 lần"; đếm được bằng một dấu hiệu trong comment | Cho đăng hướng mới khi người `@ai` nhờ lại | Đổi AC-65 (c) |
| A3-2 | Comment định tuyến và thông báo từ chối của lần đưa hướng gộp vào comment hướng xử lý | Người đọc một lần, không hai comment cùng lúc | Giữ hai comment như AC-23 cũ | Đổi AC-23 |
| A3-3 | Mỗi việc cần duyệt một đề xuất; các đề xuất của một lần chạy hiện cùng lúc; không gộp một nút Duyệt cho cả gói | Máy trạng thái, chuỗi duyệt (AC-36) và hết hiệu lực (AC-33) đều tính theo từng hành động; gộp gây hỏng một phần khó hiểu | Một nút Duyệt cho cả gói | Đổi AC-67, ADR-035 |
| A3-4 | Hành động ghi ERP không bị cấm cứng và không có dòng `Cấm` thì thành đề xuất chờ Duyệt (đảo A-2, "vắng mặt = cấm") | Câu người; N-1 chữ gốc; chiến lược `source-strategy.md:100,107` nói việc ngoài danh mục đi vào Duyệt; mỗi việc vẫn có người bấm Duyệt, điều cấm cứng và cổng môi trường đứng trước | Giữ A-2: ngoài danh mục thì từ chối (đã dựng thiết kế) | Đổi AC-29, AC-30, AC-33, AC-64 về addendum 2 (Q-10) |
| A3-5 | Hành động ERP chỉ tự làm khi có dòng `Tự làm` và đủ AC-36 (L3, ngưỡng, chuỗi 20) | Chiến lược `:116`: L3 sau ≥ 20 lần duyệt không sửa; người có thể hạ số 20 trong cấu hình không cần deploy | Hạ mặc định, hoặc bỏ chuỗi cho dòng `Tự làm` | Đổi giá trị cấu hình hoặc AC-36 (Q-11) |
| A3-6 | Mức hiệu lực cần: hướng xử lý ≥ L1; ghi phiếu ≥ L1; đề xuất có nút Duyệt ≥ L2; tự làm L3. Đầu mục C, E (cap L1) chỉ nhận hướng bằng chữ | AC-31, AC-32 giữ theo chiến lược (`:114-116`) | Nâng cap C, E | Đổi giá trị cap trong cấu hình |
| A3-7 | Chữ "ok" hay "duyệt" trong phiếu không bao giờ là duyệt; prompt nền bỏ câu chờ "ok" | Đã đúng cho code (`prompts.py:164-166`); câu 104-106 trái với nó và với AC-33 | Giữ "chờ ok" cho việc không hoàn tác | Đổi AC-66 |
| A3-8 | Thời gian từ Duyệt tới có kết quả chỉ ghi, không là ngưỡng | Không có số trong tài liệu hay intake; A-9 làm tương tự | Đặt ngưỡng (ví dụ 1 phút) | Thêm khi người đặt số |
| A3-9 | BA note, trả lời người tạo, nhắc hạn, comment trạng thái và câu hỏi tách phiếu không phải "Hướng xử lý" | Mỗi thứ có AC riêng và mục đích khác | Gộp BA note vào hướng ở đầu mục C | Đổi AC-65 (danh sách loại trừ) |

## 7. Câu hỏi nghiệp vụ không chặn cho người

Không câu nào chặn build: mỗi câu có mặc định mà team dựng theo phụ lục này. Decide mode: không có `questions.md`; team-leader chuyển danh sách này cho người, trả lời lúc nào cũng được.

**Q-9. Báo cáo trên Task và trên mọi DocType có trường Link tới phiếu Helpdesk không chạy được qua bot. Có chấp nhận không?** (journal 20:57 `docs/team/journal/FEAT-007.md:14`; C-T15-5 của `arch-review-w0-fixes-3.md:58`; AC-49, ADR-034 QĐ 3)
- Mặc định đang dựng: **chặn** (T15). Công cụ chạy báo cáo của bot từ chối báo cáo có `ref_doctype` là Task hoặc DocType có Link tới phiếu, vì kết quả có thể chứa nội dung phiếu nhóm loại trừ (NFR-1).
- Hệ quả: bot không dùng được báo cáo về Task (tiến độ Task, Task quá hạn); người xem các báo cáo đó bằng tay. Writer ghi vào As-Built.
- Cách đảo: người trả lời "Q-9: cho chạy báo cáo trên Task" thì tech-lead chèn một task nới danh sách ở T15, kèm lọc nhóm loại trừ theo từng dòng (thiết kế do designer lập).

**Q-10. Việc ghi ERP không bị cấm cứng nhưng chưa có dòng nào trong danh mục: bot đề xuất chờ Duyệt hay từ chối?** (AC-29, A3-4)
- Mặc định đang dựng: **đề xuất chờ Duyệt** (khuyến nghị). Danh mục rỗng vẫn đúng nghĩa "không việc nào tự làm"; việc cần ghi thành một đề xuất, người bấm Duyệt mới ghi. Điều cấm cứng, `Cấm` và cổng môi trường đứng trước.
- Các lựa chọn: (a) đề xuất chờ Duyệt cho mọi việc không bị cấm (mặc định); (b) giữ A-2: từ chối "ngoài danh mục", người phải thêm từng dòng `Cần duyệt` thì mới có nút Duyệt; (c) chỉ 5 hành động có tên được đề xuất khi chưa có dòng, "đổi trường" tùy ý phải có dòng.
- Hệ quả của (a): người được giao phiếu (hoặc `ERP AI Instructor`) có thể duyệt thay đổi trên bất kỳ bản ghi không bị cấm, nên phải đọc kỹ giá trị trước khi bấm; người tự giao phiếu cho mình vẫn duyệt được (Q-2). (b) không đạt hành vi người nêu cho việc ngoài 5 hành động và phải điền danh mục trước. (c) nằm giữa.
- Cách đảo: một thay đổi quy tắc kết cục ở U7a và đổi chữ AC-29, AC-30, AC-33, AC-64; chưa có mã nên chi phí nhỏ nếu đổi trước khi U7a dựng.

**Q-11. Hành động ERP có dòng `Tự làm`: chờ 20 lần duyệt liên tiếp không sửa (mặc định) hay làm ngay từ lần đầu?** (AC-36, A3-5)
- Mặc định đang dựng: **giữ 20** theo chiến lược (`source-strategy.md:116`). Tuần đầu mọi việc ERP đều qua Duyệt.
- Các lựa chọn: (a) giữ 20 (mặc định; khuyến nghị cho tới khi có số liệu duyệt AC-37); (b) đổi mặc định xuống số nhỏ (người nêu số), dòng `Tự làm` làm sau chừng đó lần duyệt không sửa; (c) bỏ điều kiện chuỗi cho dòng `Tự làm` do người đặt (người đặt dòng coi như đã đồng ý trước).
- Hệ quả: (a) và (b) cùng cơ chế, chỉ khác một giá trị cấu hình (1..100, không cần deploy); (c) đổi AC-36 và lệch chiến lược ("20 lần L2 liên tiếp được duyệt không sửa cho loại việc đó"). Hạ số là hạ lớp an toàn cuối khi bot tin sai.
- Cách đảo: sửa giá trị trong cấu hình bất cứ lúc nào; (c) cần đổi AC-36 một dòng ở U7b.

**Q-12. Hộp xác nhận khi bấm Duyệt: giữ mặc định (có hộp) hay bật "một lần bấm"?** (công tắc `one_click_approval_enabled`, AC-11, AC-39)
- Mặc định đang dựng: **tắt**, tức Duyệt trong ngăn có một bước xác nhận (N-1: 5 quyền mặc định tắt). H-3 vẫn đạt vì sau Duyệt không còn bước nào khác (AC-68).
- Các lựa chọn: (a) giữ tắt (mặc định); (b) người tự bật công tắc (5) ở site cần, cảnh báo AC-4 hiện; (c) đổi mặc định cài mới thành bật.
- Hệ quả: (b) không cần đổi gì ngoài một lần lưu cấu hình; (c) đổi AC-1 và test cài mới của T2 (đã merge, đang ghim "5 công tắc đều tắt") và đảo một quyết định của người (N-1); khi bật, người bấm liên kết được chuyển tiếp cũng duyệt (AC-4).
- Cách đảo: tắt lại công tắc trong cấu hình.

## 8. Đổi DoD, NFR, bảng phủ và việc cho designer, architect

**DoD (phần build), thêm vào ba file trước:**
- `[changed]` Số AC của FEAT-007 từ 61 thành 66: thêm AC-65..AC-69; mỗi AC có ít nhất 1 test tự động hoặc bước kiểm có đầu ra (STD-TEST-2). AC-69 là bước kiểm có đầu ra, làm sau khi U7a, U7b vào `develop`.
- `[changed]` AC-23, AC-29, AC-30, AC-33, AC-36, AC-41, AC-64 đạt theo chữ ở mục 3.2.
- Chữ mô tả trên form của `catalog_rules` (T10) và `permission_level` (T2) sửa cho khớp AC-29 và AC-33; chạy lại `test_doctype_descriptions` và `test_erp_ai_setting`. Không đổi mã, mặc định, dữ liệu.
- Danh sách test bị sửa vì spec đổi (NFR-8): các test của thiết kế U7a, U7b, U8 ghim "danh mục rỗng = từ chối" (`test_empty_catalog_refuses_every_action`, `test_empty_catalog_no_proposal`, `test_no_rule_refused` của AC-64) được viết lại theo AC-29 khi viết mã, mỗi chỗ ghi lý do (STD-TEST-5); chưa có mã nên không có assertion nào đã merge bị đổi.
- Phần sau G4: As-Built ghi Q-9, Q-10 (người được giao duyệt mọi bản ghi không bị cấm), Q-11, Q-12 và nơi đặt từng số cấu hình; tài liệu người dùng mô tả "một hướng xử lý, Đã làm, Chờ duyệt, Duyệt" và cách đặt dòng `Tự làm`, số chuỗi duyệt.

**NFR-4 `[changed]`:** câu "chạy với cấu hình rỗng: 0 tác động" thành: danh mục rỗng không làm bot ghi bản ghi ERP nào; bot chỉ tạo đề xuất chờ duyệt, không đổi dữ liệu nào cho tới khi có người Duyệt. Mặc định cài mới của 5 công tắc quyền không đổi (tắt).
**NFR-2 bổ sung:** lượt áp dụng sau Duyệt (AC-68) không tính vào số lần chạy bot của phiếu và không gọi model.

**Bảng phủ.** Chỉ ghi các dòng chạm vào; dòng khác giữ như ba file trước:

| Dòng | AC sau addendum 3 | Ghi chú |
|---|---|---|
| H3 | AC-23, AC-65 | một hướng mỗi phiếu |
| H4 | AC-29, AC-30, AC-33, AC-36, AC-66..AC-68 | |
| H5 | AC-29, AC-30 | danh mục không còn là cổng cấm, là cổng chọn chế độ |
| C2, C5 | AC-29, AC-33, AC-39, AC-68 | |
| H13 | AC-64 | |

C1–C6, G1–G13, H1–H14 vẫn được phủ: phụ lục này không bỏ và không chuyển tiêu chí nào.

**Việc cho designer và architect (không phải của analyst).** Architect: amendment cho ADR-031 QĐ 1 (danh mục: vắng mặt = cấm thành vắng mặt = `Cần duyệt`) và xác nhận điều cấm cứng cùng cổng môi trường đứng trước kết cục; xác nhận AC-65 (d) (từ chối lần đăng thứ hai) không đòi ngoại lệ cho luật ghi comment. Designer: sửa `design-addendum-2-U7a.md` (quy tắc kết cục, chữ `OUT_OF_CATALOG` chỉ còn cho trường hợp từ chối vì cấm, bảng test dòng 361-362), `design-addendum-2-U7b-U8.md` (AC-64, test 352, 372), thiết kế U1 (prompt nền câu 104-106, hai cặp câu mới cho AC-6) và U4b (đăng comment hướng, dấu hiệu "đã có hướng", gộp comment định tuyến). Tech-lead: một task chèn nhỏ cho chữ mô tả T10, T2 khi lập kế hoạch đợt 1; thứ tự ưu tiên của đường tới U7 đã có ở journal 22:10 (b), (e).

## 9. Out of scope (thêm)

Đổi ngữ nghĩa ba công tắc `record_tools_enabled`, `act_now_enabled`, `one_click_approval_enabled`; gộp nhiều việc thành một nút Duyệt (A3-3); ngưỡng thời gian từ Duyệt tới kết quả (A3-8); bỏ hộp xác nhận mặc định (Q-12); hạ số 20 (Q-11); nới điều cấm cứng nào của Gói 1; bot làm việc ERP trên `erp.miyano.com.vn` (G5); phán quyết kỹ thuật cho các điểm ở mục 8 (việc của architect, designer).
