Feature: FEAT-007
Stage: analyze
Author-agent: analyst
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G1 không áp dụng cho FEAT-007 (team.py: chỉ có G5), để trống. -->

# Spec FEAT-007 — Đưa app `erp_ai` về đúng và đủ theo "Chiến lược AI Agent Helpdesk Miyano"

## Mục tiêu
Giả thuyết: người yêu cầu muốn app `erp_ai` làm đúng điều tài liệu chiến lược 31/10/2026 đã viết, ở hai phía. Phía "điều chỉnh": đường chính của bot chỉ ghi vào danh mục trắng, việc ngoài danh mục phải được người phụ trách bấm Duyệt rồi mới làm; 5 quyền do lệnh trực tiếp ngày 13/11 vẫn giữ nhưng thành công tắc riêng, mặc định tắt. Phía "hoàn thiện": phần vận hành chưa có (báo cáo 8h cho COO, KPI hằng tuần, việc chạy theo lịch, bài CSKT nháp, trả lời người tạo phiếu, đóng phiếu). Độ tin cậy 85%. Lý do chưa cao hơn: site production `erp.miyano.com.vn` chưa kiểm được (có hay không các trường "Nguồn phát sinh", "Hạn hoàn thành", có worker hàng đợi `long`, có tài khoản gửi mail), nên mọi phần phụ thuộc site là cấu hình rỗng (QĐ-5).

- **Outcome:** sau FEAT-007, mỗi dòng đối chiếu C1–C6, G1–G13, H1–H14 của `gap-audit.md` hoặc đạt một tiêu chí đo được dưới đây, hoặc nằm trong mục "Ngoài phạm vi" kèm lý do. Bot không còn làm điều tài liệu cấm trên đường chính. Việc vận hành của COO (báo cáo, KPI, nhắc hạn, rà soát) chạy theo lịch.
- **Users:** COO (nhận báo cáo, xem KPI, giữ ngân sách), người phụ trách phiếu (duyệt hành động của bot), người có role `ERP AI Instructor`, System Manager (giữ cấu hình, danh mục trắng, công tắc), người tạo phiếu (nhận trả lời của bot), trưởng nhóm IT.
- **Why now:** người đã chọn hướng ở `intake.md` (N-1 theo chiến lược, N-2 cho bot trả lời và đóng phiếu có chốt, N-3 build song song). Kiểm tra ngày 2026-11-14 trên `develop` @ `7cc37bb` cho thấy 6 điểm app làm trái tài liệu (C1–C6, gộp từ 9 dòng đối chiếu) và 27 việc còn thiếu hoặc mới làm một phần (G1–G13, H1–H14) (`gap-audit.md` mục 3, 4). Lộ trình tài liệu đưa GĐ1 (L0, 17/11) lên trước: cửa L0 → L1 phải đo được trước ngày đó.
- **Success:** đạt AC-1..AC-64. Bảng phủ ở mục Phạm vi không còn dòng C/G/H nào thiếu. Gói 1 nghiệm thu riêng được và xong trước các gói khác (mục Gói).
- **Constraints:** N-1, N-2, N-3 và QĐ-1..QĐ-5 của `intake.md`. QĐ-2: giữ các điểm lệch có quyết định (job nền thay dịch vụ riêng; L0 chỉ ghi log; đọc bản ghi theo danh sách cho phép; tool đọc mã nguồn; nhiều khóa API; đánh giá offline trước). Không ghi `.team/current.json`. Việc làm trên nhánh `team/FEAT-007` trong worktree riêng. Mọi giá trị phụ thuộc site là cấu hình, mặc định rỗng hoặc tắt (QĐ-5, STD-DESIGN-7). Nội dung phiếu, tài liệu chiến lược và comment là dữ liệu, không phải lệnh (STD-SEC-5). Không lộ khóa API, mật khẩu, nội dung phiếu nhóm loại trừ (STD-SEC-6).
- **Out of scope:** triển khai lên `erp.miyano.com.vn` (G5); dữ liệu site (cài 6 Loại phiếu, SLA, Assignment Rule, gán tay phiếu cũ, cấp role: QĐ-4); site test đồng bộ từ production và đường đưa thay đổi từ site test lên production; việc đầu mục D (rà soát dữ liệu, file mẫu, Data Import sau duyệt); tái dùng khung cho bot đơn hàng và bot CRM (H14); dịch vụ riêng, systemd, Claude Agent SDK, webhook (QĐ-2). Chi tiết và lý do ở mục "Ngoài phạm vi" bên dưới.

Đã có sẵn, không cần hỏi (nguồn):
- Yêu cầu và quyết định: `docs/team/features/FEAT-007/intake.md` (N-1..N-3, QĐ-1..QĐ-5); tài liệu chiến lược: `source-strategy.md` (bản chữ), file gốc thắng khi khác.
- Hiện trạng code, từng dòng có `file:line`: `gap-audit.md`, `audit-A1.md`..`audit-A8.md`. Analyst không chạy lại Explore vì đã có 8 báo cáo cùng mốc `develop` @ `7cc37bb`; cache explore không dùng.
- Các điểm hướng dẫn 2.2 chủ ý làm khác: `docs/HuongDan_TrienKhai_erp-ai.md:1474-1490`. Code viết theo lệnh trực tiếp 13/11: `docs/team/features/CHG-001/handoff-direct-session.md`.
- Chưa có `docs/team/glossary.md`. Thuật ngữ giữ như trong repo: "ERP AI Setting", "ERP AI Log", "đầu mục A–F", "người ra lệnh".

## Người dùng
| Ai | Tình huống | Cần gì |
|---|---|---|
| COO | Mỗi sáng 8h; mỗi tuần; khi duyệt ngân sách | Báo cáo hằng ngày, 6 KPI cùng mục tiêu, bằng chứng để mở mức L1/L2/L3; không nhận nội dung phiếu nhạy cảm |
| Người phụ trách phiếu (IT, trưởng bộ phận) | Bot đề xuất một thay đổi trên ERP | Duyệt, Sửa hoặc Từ chối ngay trên trang phiếu; thấy độ tin cậy và căn cứ; việc ngoài danh mục không tự chạy |
| Người có `ERP AI Instructor` | Rà báo cáo độ đúng, rà ngẫu nhiên 10 phiếu mỗi tháng, duyệt bài CSKT nháp | Xem được báo cáo và hàng chờ mà không cần System Manager |
| System Manager | Cấu hình | Sửa danh mục trắng, prompt, mức theo đầu mục, người nhận báo cáo, 5 công tắc quyền và công tắc N-2, không cần deploy |
| Người tạo phiếu (nhân viên các phòng) | Gửi câu hỏi hoặc yêu cầu | Nhận trả lời của bot khi công tắc bật, kể cả khi không có role Agent; trả lời lại thì bot đọc được |
| Nhân sự & HC, Kế toán | Phiếu chứa CCCD, lương | Nội dung không đi vào bài CSKT, báo cáo, tool đọc chung hay lượt lập luận |

## Phạm vi
- Trong: 6 gói, nghiệm thu riêng được (bảng Gói bên dưới).
  1. **Gói 1, Guardrail** (C1–C6, H6, H7, H8, H10): 5 công tắc quyền, đường chính theo danh mục, vá lỗ rò, nhật ký hành động, môi trường site.
  2. **Gói 2, Phân loại và routing** (G1, G12, H1, H2, H3, H11, H12): quét bù, cửa L0 → L1, không đè lựa chọn của người, độ tin cậy, một comment cho mỗi hành động, ngoại lệ ưu tiên.
  3. **Gói 3, Danh mục trắng, duyệt, mức tự chủ** (H4, H5, H9): L2 thật, L3 thật, Duyệt/Sửa/Từ chối trên trang phiếu, prompt sửa được.
  4. **Gói 4, Tri thức, trả lời, đóng phiếu** (G5–G10): N-2, bài CSKT nháp, công cụ tìm, công cụ đọc riêng.
  5. **Gói 5, Vận hành** (G2, G3, G4, G11, G13): báo cáo 8h, KPI, nhắc hạn, rà ngẫu nhiên, chi phí.
  6. **Gói 6, Đầu mục C** (H13): BA note, nhiều Task có ước lượng, Project.
- Ngoài: xem mục "Ngoài phạm vi và lý do" cuối phần này.

**Bảng phủ.** Mọi dòng C/G/H của `gap-audit.md` mục 3 và 4 nằm đúng một dòng dưới đây.

| Dòng | Việc | AC hoặc Ngoài phạm vi |
|---|---|---|
| C1 | Công tắc "Toàn quyền" | AC-1, AC-3, AC-4, AC-5, AC-7, AC-10 |
| C2 | Công cụ bản ghi chung ghi thẳng, không qua duyệt | AC-1, AC-2, AC-3, AC-5, AC-8, AC-29, AC-33 |
| C3 | Khối "làm luôn, không hỏi lại" | AC-1, AC-2, AC-3, AC-6 |
| C4 | Sửa code và `bench migrate` sau một lần bấm; không phân biệt production | AC-1, AC-2, AC-3, AC-12 |
| C5 | Đường dẫn Duyệt một lần GET | AC-11, AC-14, AC-34 |
| C6 | Công cụ bản ghi chung đọc phiếu nhóm loại trừ | AC-8 |
| G1 | Quét bù 15 phút, đo mốc 5 phút | AC-16, AC-17 |
| G2 | Báo cáo 8h cho COO | AC-51, AC-52 |
| G3 | 6 KPI hằng tuần lên trang tổng quan | AC-53..AC-56 |
| G4 | Nhắc hạn; mốc Task 3 ngày; BA note 24h; tiến độ cho COO | AC-51, AC-57, AC-58 |
| G5 | Task xong thì phiếu Resolved | AC-42, AC-43 |
| G6 | Phiếu F tự đóng sau 3 ngày im lặng | AC-42, AC-44 |
| G7 | Bài CSKT nháp khi phiếu đóng | AC-45 |
| G8 | Tìm CSKT, kho HDSD, phiếu cũ trả về cách giải quyết thật | AC-46, AC-47, AC-48 |
| G9 | Công cụ chạy báo cáo, đọc Error Log | AC-49, AC-50 |
| G10 | Trả lời người tạo phiếu và nhận trả lời của họ | AC-40, AC-41 |
| G11 | Rà ngẫu nhiên 10 phiếu mỗi tháng | AC-59 |
| G12 | Cửa L0 → L1 đo được; Instructor xem báo cáo | AC-18, AC-19, AC-20 |
| G13 | Chi phí theo phiếu, theo lần chạy; báo khi vượt | AC-60, AC-61 |
| H1 | Không đè lựa chọn người đã điền | AC-21 |
| H2 | Dưới ngưỡng tin cậy thì chỉ hỏi | AC-22 |
| H3 | Mỗi hành động một comment | AC-23 |
| H4 | L2 làm sau duyệt, L3 chỉ danh mục trắng, mức theo đầu mục, đếm lần duyệt | AC-31, AC-32, AC-33, AC-34, AC-35, AC-36, AC-37 |
| H5 | Danh mục trắng trong cấu hình, mặc định cấm; công cụ riêng cho việc B | AC-29, AC-30 |
| H6 | Vá rò dữ liệu nhạy cảm | AC-8, AC-9 |
| H7 | Vượt ngân sách thì mọi nhóm tool ghi lui | AC-7 |
| H8 | Nhật ký hành động đủ cho mọi lần ghi | AC-10 |
| H9 | Prompt sửa được trong cấu hình | AC-38 |
| H10 | Khái niệm site test/production và chốt theo nó | AC-12 (phần app); đường đưa lên production: Ngoài phạm vi N-1 |
| H11 | Dùng trường sẵn có của phiếu khi site có | AC-24 |
| H12 | Ngoại lệ ưu tiên, mốc SLA, D/E theo hạn, IT theo dõi D, đề xuất tách | AC-25, AC-26, AC-27, AC-28 |
| H13 | Đầu mục C: BA note, nhiều Task có ước lượng, Project | AC-62, AC-63, AC-64 |
| H14 | Tái dùng khung cho bot đơn hàng, bot CRM | Ngoài phạm vi N-7 |

**Gói.** Mỗi gói có AC riêng, build và nghiệm thu riêng được, merge theo thứ tự ở cột cuối. "Vùng đụng chạm" là các module đã có (từ `intake.md`), để tech-lead xếp lịch tránh xung đột với phiên FEAT-004/005 (N-3).

| Gói | AC | Phụ thuộc | Vùng đụng chạm | Merge |
|---|---|---|---|---|
| 1 Guardrail | AC-1..AC-15 | không | registry, policy, prompts, runner, site_api, change_link/change_decision, ERP AI Setting, tasks (cảnh báo hằng ngày) | 1 |
| 2 Phân loại và routing | AC-16..AC-28 | Gói 1 chỉ ở AC-23 (chung cơ chế comment) và AC-22 (bỏ qua tool ghi) | handlers, classification, routing, runner, báo cáo ERP AI Accuracy, hooks (lịch) | 2 |
| 3 Danh mục, duyệt, mức | AC-29..AC-39 | Gói 1 (công tắc, nhật ký, người ra lệnh), Gói 2 AC-22 (độ tin cậy) | registry, policy, prompts, ERP AI Setting, đề xuất thay đổi, ngăn bot trên trang phiếu | 3 |
| 4 Tri thức, trả lời, đóng phiếu | AC-40..AC-50 | Gói 1 (nhật ký, chốt nhóm nhạy cảm); AC-42..AC-44 cần tên trường "Nguồn phát sinh" qua AC-24 | handlers (sự kiện Task, Communication, đóng phiếu), tool đọc, tool ghi phiếu, hooks | 4 |
| 5 Vận hành | AC-51..AC-61 | AC-57, AC-58 cần AC-62; AC-53..AC-56 cần số liệu của Gói 2, 4 (tính ra 0 khi chưa có, không lỗi) | tasks, hooks (lịch), báo cáo, alerts | 5 |
| 6 Đầu mục C | AC-62..AC-64 | AC-64 cần Gói 3 | prompts, tool Task, đề xuất thay đổi | 5 hoặc 6 |

Thứ tự bỏ trước nếu phải cắt (bước 8, mọi dòng đều "phải có" theo người): AC-64 (Project) → AC-59 (rà ngẫu nhiên) → AC-47 (kho HDSD) → AC-49 (chạy báo cáo) → AC-27 (IT theo dõi D) → AC-28 (đề xuất tách) → AC-26 (kiểm mốc phản hồi) → AC-61 phần cảnh báo chạm giới hạn ngày. Lõi, không cắt: Gói 1 đủ, AC-16, AC-18..AC-22, AC-29..AC-36, AC-40..AC-44, AC-51, AC-53..AC-56. Khối lượng vượt cỡ L: xem đề xuất ở Assumptions A-22.

### Ngoài phạm vi và lý do
| # | Việc | Lý do |
|---|---|---|
| N-1 | Site test đồng bộ hằng tuần từ production; đường đưa thay đổi từ site test lên production sau khi dev duyệt (phần còn lại của H10) | Hạ tầng và quy trình deploy; tài liệu đặt là việc chờ COO chốt ("cho phép tạo site test") và đầu ra của #1759. App chỉ cần biết mình đang chạy ở môi trường nào và từ chối đúng (AC-12). |
| N-2 | Việc đầu mục D: rà soát dữ liệu hiện có, lập danh sách thiếu/sai, soạn file mẫu Data Import, import sau duyệt (A3-9, A4-19). Tool `create_server_script` riêng chỉ cho site test (A4-18) | Cần site test và cơ chế xử lý file và dữ liệu nghiệp vụ nhạy cảm; không dòng C/G/H nào đòi. Đề xuất mở feature riêng sau khi có site test. Server Script vẫn ghi được qua công cụ bản ghi chung (quyền 2) và luôn bị ép tắt (QĐ-2, hướng dẫn `:1483`). |
| N-3 | Bot tự tách phiếu gộp sau khi người tạo xác nhận | FEAT-006 QĐ-2 đã loại. AC-28 chỉ làm phần "đề xuất tách". |
| N-4 | Code trên site test cho việc nhỏ của đầu mục C (< 2 giờ) | Không có site test (N-1). Mức mặc định của đầu mục C là L1 (AC-31). |
| N-5 | Hạ tầng của tài liệu: dịch vụ Python riêng, systemd, Claude Agent SDK, webhook; L0 không comment; thẩm quyền theo người thay duyệt cho việc đã trong danh mục; `get_doc` bất kỳ DocType; nhiều khóa API | QĐ-2. Giữ nguyên. |
| N-6 | Dữ liệu và việc tổ chức trên site (QĐ-4): 6 Loại phiếu thay bộ cũ, bắt buộc Nhóm + Ưu tiên, SLA và Assignment Rule theo mục 3, gán tay lại phiếu cũ, tạo HD Agent cho người nhận, gỡ role thừa của tài khoản agent (BUG-002), chốt ngân sách và người giữ khóa, quyết định 6 ô tick của COO | Không phải mã; production cần người duyệt (G5). Liệt kê ở DoD "phần việc của người". |
| N-7 | Tái dùng ≥ 60% mã cho bot đơn hàng (#1764) và bot CRM (#1768) (H14) | Chưa có bot thứ hai nên không đo được 60%; ô tick số 6 của COO ("chung khung hay riêng") chưa chốt. Architect ghi nhận trong `arch-impact.md` điểm dính Helpdesk của khung (A6-6) để feature sau dùng; FEAT-007 không thêm tiêu chí. |
| N-8 | Các dòng audit không thuộc C/G/H: che số CCCD/lương trong nội dung gửi model (A5-7); nhóm dự phòng khi không tìm được nhóm D/E (A2-1); tiền tố [HR]/[Kế toán] thành mã (A1-6) ngoài AC-9; `@ai` thứ hai bị nuốt khi job đang chờ (A6-11); role "người giữ khóa" (A6-10); dòng cấu hình đang lệch trên site dev (A1-10, A2-5) | Tài liệu không đòi hoặc là việc cấu hình. Ghi để tech-lead không bỏ sót; thêm bằng change-request nếu người muốn. |
| N-9 | Soạn dự thảo công văn, checklist cho đầu mục E; nhắc hạn nội dung phiếu E nằm trong nhóm loại trừ | Chất lượng bản dự thảo không đo được. Phiếu E thường thuộc Nhân sự & HC hoặc Kế toán, là hai nhóm bị loại trừ (hướng dẫn 13.2, QĐ-2): bot không đọc nội dung, chỉ nhắc hạn bằng mã (A-12). |

## Dữ liệu
Mô tả theo nghĩa nghiệp vụ. Hình dạng cụ thể (tên trường, DocType) do designer chọn.

**Cấu hình thêm vào ERP AI Setting** (sửa không cần deploy; mặc định rỗng hoặc tắt, cài lại không ghi đè giá trị người đã sửa):
- 3 công tắc quyền mới (bản ghi chung, làm luôn, duyệt một lần bấm), cạnh 2 công tắc đã có (Toàn quyền, sửa code + bench). Môi trường của site: `test` hoặc `production`, mặc định `production`.
- Danh mục trắng: danh sách dòng, mỗi dòng gồm hành động hoặc DocType, trường được ghi, đầu mục được phép, chế độ `Cấm` / `Cần duyệt` / `Tự làm`. Mặc định: không có dòng nào, tức là cấm hết.
- Mức tự chủ tối đa theo đầu mục A–F. Ngưỡng độ tin cậy (70). Số lần duyệt liên tiếp không sửa để mở `Tự làm` (20).
- Tên 7 trường sẵn có của phiếu và giá trị nghĩa là "Chỉ đạo BGĐ" (QĐ-5). Mốc phản hồi và xử lý mong đợi theo đầu mục (mốc phản hồi mới, mặc định theo bảng mục 3).
- Công tắc N-2: bot trả lời người tạo; bot chuyển phiếu sang Resolved khi Task xong; bot đóng phiếu F im lặng 3 ngày. Công tắc soạn bài CSKT nháp. Mỗi việc một công tắc, mặc định tắt.
- Người nhận báo cáo COO, người rà soát hằng tháng, người theo dõi phiếu D (cả ba mặc định rỗng), kho HDSD (mặc định rỗng), danh sách báo cáo bot được chạy (mặc định rỗng), mục tiêu KPI theo bảng mục 5, ghi đè từng phần prompt (mặc định rỗng).

**Nhật ký ERP AI Log** được mở rộng: mỗi lần ghi một dòng với đích, giá trị trước/sau, người ra lệnh, tool, kết quả; độ tin cậy số; độ trễ phân loại; nhãn người gõ lúc tạo phiếu; cờ kết quả duyệt (không sửa, có sửa, từ chối, hoàn tác).

**Dữ liệu mới:** đề xuất chờ duyệt cho thay đổi bản ghi (kèm trạng thái, người duyệt, có sửa hay không); số liệu KPI theo tuần (để so tuần trước); danh sách rà soát hằng tháng; bài CSKT nháp liên kết về phiếu nguồn.

**Dữ liệu nhạy cảm:** phiếu thuộc nhóm loại trừ (mặc định Nhân sự & Hành chính, Tài chính Kế toán) và phiếu có cờ không dùng AI: không vào bài CSKT, không vào kết quả tool đọc chung, không có tiêu đề hay nội dung trong báo cáo và email (chỉ đếm), không gửi cho model sau lúc biết nhóm. Khóa API, mật khẩu, giá trị trường mật khẩu: không vào comment, nhật ký, báo cáo, email (NFR-6).

**Khối lượng:** vài chục đến một trăm phiếu mỗi tháng (tài liệu, mục 5). Số dòng nhật ký, KPI và rà soát nhỏ; không cần chỉ mục đặc biệt.

## Giao diện / tích hợp
- Trang phiếu Helpdesk: comment của bot (một comment cho mỗi hành động, AC-23), Duyệt/Sửa/Từ chối (AC-39), ngăn bot đã có.
- Kênh tới người tạo phiếu: trả lời mà người tạo không có role Agent đọc được (AC-40); câu trả lời của họ quay lại bot (AC-41). Kênh cụ thể (comment, email, cổng khách) là câu hỏi cho researcher (R-1).
- Email: báo cáo 8h cho COO, cảnh báo quyền đang bật, cảnh báo vượt ngân sách, nhắc hạn nhóm loại trừ. Dùng kênh email đang có (`alerts`).
- Trang tổng quan Helpdesk: 6 KPI (AC-56). Nếu không thêm được mà không sửa lõi Helpdesk thì dùng một trang của app (A-15, R-2).
- Báo cáo trong Desk: ERP AI Accuracy (mở rộng), báo cáo chi phí theo phiếu và lần chạy, thống kê duyệt theo loại việc.
- Cổng model (Claude qua gateway): số lời gọi thêm chỉ ở việc có công tắc riêng (NFR-2).
- Helpdesk: Task liên kết phiếu, HD Article, Communication, trạng thái phiếu, theo dõi phiếu.
- Lịch chạy: quét 15 phút, báo cáo 08:00 hằng ngày, KPI hằng tuần, rà soát hằng tháng, nhắc hạn.

## NFR
Chỉ dùng số từ tài liệu chiến lược, `intake.md` hoặc cấu hình đang có. Không đặt ngưỡng độ trễ mới (A-9).

| Mã | Yêu cầu | Đo bằng |
|---|---|---|
| NFR-1 | Bảo vệ nhóm nhạy cảm: với phiếu thuộc nhóm loại trừ hoặc cờ không dùng AI, số lời gọi model sau khi biết nhóm là 0; số dòng của phiếu đó xuất hiện trong kết quả tool đọc, bài CSKT, báo cáo, email là 0 (chỉ đếm, không tiêu đề). Nguồn: tài liệu mục 6, hướng dẫn 13.2, NFR-4 FEAT-001, `README.md:39` | Test với stub cổng model đếm lời gọi, và quét đầu ra tool, bài nháp, nội dung email bằng một chuỗi dấu hiệu gieo vào phiếu |
| NFR-2 | Giới hạn chống lặp: số lần chạy của bot cho một phiếu trong một ngày ≤ giá trị `max_runs_per_ticket_per_day` (mặc định 5, tài liệu mục 6), gồm cả lần do quét bù, do người tạo trả lời, do `@ai`. Việc có công tắc riêng (soạn CSKT, báo cáo) tính riêng nhưng mỗi việc chỉ chạy một lần cho một sự kiện. Số lời gọi model của một phiếu mới không tăng so với nay (1 phân loại + ≤ `max_turns_per_run` lượt) | Test đếm lần chạy và lời gọi model của stub qua một ngày giả lập với đủ các nguồn kích hoạt |
| NFR-3 | Chạy lại không sinh trùng: mỗi việc theo lịch (quét, báo cáo, nhắc hạn, KPI, rà soát), mỗi sự kiện (Task xong, phiếu đóng) chạy hai lần liên tiếp cho cùng kỳ hoặc cùng phiếu thì kết quả như một lần: 0 email, comment, Task, bài nháp, dòng KPI thêm | Test gọi hàm hai lần với cùng thời điểm giả lập; đếm bản ghi trước/sau |
| NFR-4 | Mặc định an toàn: sau cài mới, mọi hành vi mới có tác động ra ngoài phiếu đều tắt hoặc không chạy vì cấu hình rỗng (5 công tắc quyền, 3 công tắc N-2, soạn CSKT, danh mục trắng, người nhận báo cáo, kho HDSD, tên trường sẵn có). Nguồn: N-1, N-2, QĐ-5 | Test cài mới liệt kê từng giá trị mặc định; test "chạy với cấu hình rỗng" cho từng việc: 0 tác động, 1 dòng log nêu lý do |
| NFR-5 | Mốc thời gian lấy nguyên từ tài liệu: quét bù mỗi 15 phút; báo cáo COO lúc 08:00 giờ của site; phiếu F im lặng 3 ngày; Task trong 3 ngày; BA note trong 24 giờ; rà ngẫu nhiên 10 phiếu mỗi tháng; ngưỡng tin cậy 70%; cửa L0 → L1 là 85% trên ≥ 30 phiếu trong 2 tuần; cửa L3 là 20 lần duyệt liên tiếp không sửa | Mỗi mốc có AC riêng với ca biên (29/30, 84/85, 69/70, 19/20) |
| NFR-6 | Không lộ bí mật: một khóa API giả và một mật khẩu giả gieo vào cấu hình, vào giá trị trường, vào nội dung Error Log xuất hiện 0 lần trong comment, nhật ký, báo cáo, email, bài nháp, kết quả tool. Nguồn: STD-SEC-6, NFR-5 FEAT-001 | Test tự động gieo và quét |
| NFR-7 | Không phụ thuộc cấu hình đã lưu trên site dùng chung: mọi test mới tự đặt cấu hình, dữ liệu (team, user, trường, SLA, Task) và trả lại khi xong; một lần đỏ trên site `miyano` phải chạy lại trước khi kết luận (`intake.md`, N-3) | Chạy bộ test hai lần liên tiếp cho cùng kết quả; số bản ghi cấu hình trước = sau |
| NFR-8 | Test đang ghim hành vi mà spec này đổi (`TestSiteApiUnrestricted`, bảng cấp tool theo mức, khối prompt, 2 bước xác nhận AC-22 của FEAT-004, AC-9 của FEAT-006) chỉ được sửa theo đúng AC tương ứng, mỗi chỗ sửa ghi lý do (STD-TEST-5). Không skip, xfail (STD-TEST-4) | Diff test được reviewer đối chiếu với danh sách trong DoD |

## Tiêu chí nghiệm thu
Quy ước kiểm: "Test tự động" chạy bằng `cmd.test_one` cho từng file test của gói và `cmd.test` cho cả app; test tự tạo dữ liệu, dùng stub cổng model, không gọi mạng (STD-TEST-6). "Kiểm có đầu ra" là một bước có lệnh hoặc thao tác với đầu ra dán vào `acceptance.md` (`ui: false`, nên thao tác trên trang phiếu do người thử và chụp màn hình, hoặc Playwright nếu có). "5 công tắc" là: (1) Toàn quyền, (2) công cụ bản ghi chung, (3) làm luôn, (4) sửa code + bench, (5) đường dẫn duyệt một lần bấm.

### Gói 1, Guardrail
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-1 | [C1–C5, N-1] Sau cài mới, 5 công tắc đều tắt. Sau migrate trên site đã có cấu hình: hai công tắc đã tồn tại (Toàn quyền, sửa code + bench) giữ giá trị đã lưu; ba công tắc mới (2, 3, 5) bằng tắt, kể cả khi site đang bật sửa code + bench (A-3) | Test cài mới đọc 5 giá trị. Test migrate với cấu hình giả lập `code_change_enabled=1`, `unrestricted_enabled=1` → hai giá trị giữ, ba công tắc mới = 0 |
| AC-2 | [C2, C3, C4] Với 5 công tắc tắt, ở mọi mức L0–L3, có hay không có người ra lệnh, trong hoặc vượt ngân sách (16 ca): danh sách tool gửi cho model không có tool nào tạo/sửa bản ghi tùy DocType, xóa, submit/hủy, gọi hàm whitelist, đề xuất sửa code, đề xuất lệnh bench; prompt không chứa 3 khối "bản ghi chung", "toàn quyền", "làm ngay" | Test ma trận 16 ca; so tập tool với tập mong đợi của từng ca |
| AC-3 | [C1–C5] Mỗi công tắc độc lập: bật riêng một công tắc (5 ca) thì tập tool và khối prompt thêm đúng bằng tập đã khai báo cho quyền đó, không thêm gì khác. Khai báo: (1) nhóm xóa, submit/hủy, gọi hàm whitelist và kế thừa (2); (2) nhóm liệt kê, đọc, tạo, sửa bản ghi, cần mức L3 và người ra lệnh như nay; (3) khối prompt "làm ngay"; (4) 3 tool đề xuất sửa file, tạo file, lệnh bench; (5) đường dẫn đổi trạng thái trong comment (AC-11) | Test bảng 5 hàng; assert tập thêm = tập khai báo |
| AC-4 | [C1–C5] Lưu cấu hình khi một công tắc quyền đổi 0 → 1 thì người lưu nhận thông báo nêu tên quyền, hậu quả (bản ghi chung: ghi thẳng không duyệt; Toàn quyền: xóa, sửa phân quyền, gọi hàm; sửa code + bench: đổi code; làm luôn; một lần bấm) và giá trị môi trường site; có đúng 1 dòng log ghi người bật và thời điểm; lưu mà không đổi công tắc thì không có thông báo. Cảnh báo hằng ngày (`check_privilege_escalation`) nêu mọi quyền đang bật; tắt hết thì không thêm dòng | Test gọi hàm lưu: bật từng công tắc, đọc nội dung thông báo và dòng log; test cảnh báo với 2 quyền bật rồi 0 quyền bật |
| AC-5 | [C1, C2] Bốn điều cấm của tài liệu, khi Toàn quyền tắt (kể cả khi 2, 3, 4, 5 bật): (a) xóa bản ghi: không có tool; (b) sửa Role Permission: ghi vào Custom DocPerm, DocPerm, Has Role, Role Profile, User Permission, DocShare, Role, và Property Setter đổi `permlevel` đều bị từ chối, dữ liệu không đổi; (c) chạy `migrate` hoặc deploy: không có tool bench khi công tắc 4 tắt; (d) tạo, sửa, hủy Purchase Invoice hoặc Payment Entry đã submit: bị từ chối | Test 8 vector của (b), 1 của (a), 1 của (c), 2 của (d); mỗi ca assert dữ liệu trước = sau và có 1 dòng log `ok=false` kèm lý do |
| AC-6 | [C3] Mỗi khối quyền chỉ có trong prompt khi công tắc tương ứng bật. Khi bật, các câu cấm gốc trong khối lõi bị thay hoặc bỏ đúng chỗ: prompt không chứa đồng thời một câu cấm và câu cho phép chính việc đó, theo danh sách cặp câu do designer lập từ `prompts.py` | Test từng công tắc: dựng prompt, assert không còn cặp câu trái nhau trong danh sách; assert khối vắng khi công tắc tắt |
| AC-7 | [C1, H7] Khi chi tháng vượt ngân sách, tập tool của mọi lần chạy kế tiếp bằng tập tool L1 của cấu hình hiện tại, dù cả 5 công tắc bật: không còn nhóm xóa, submit/hủy, gọi hàm, bản ghi chung, đề xuất code | Test bật cả 5 công tắc, gieo chi vượt, assert tập tool = tập L1 với 5 công tắc tắt |
| AC-8 | [C6, H6] Đọc chéo: khi công cụ bản ghi chung bật (kể cả cùng Toàn quyền), liệt kê và đọc HD Ticket, Comment, Communication, File (siêu dữ liệu) của phiếu thuộc nhóm loại trừ hoặc có cờ không dùng AI: 0 dòng trả về, có lý do bị từ chối; phiếu thường vẫn đọc được. Danh sách và đếm không lộ sự tồn tại của phiếu loại trừ | Test ma trận 4 DocType × {nhóm loại trừ, cờ không dùng AI, phiếu thường}; kiểm cả đường liệt kê lẫn đọc theo tên |
| AC-9 | [H6] Phiếu chưa có nhóm nhưng thuộc bộ phận loại trừ: (a) tiêu đề có tiền tố của bộ phận loại trừ ([HR], [Kế toán], danh sách tiền tố trong cấu hình) thì số lời gọi model là 0 và có 1 dòng bỏ qua; (b) kết quả phân loại chỉ ra bộ phận hoặc nhóm loại trừ thì không có lượt lập luận, không có ghi vào phiếu, không có tool nào chạy, và `@ai` hay quét bù sau đó đều bỏ qua phiếu đó. Lời gọi phân loại đầu tiên của ca (b) là rủi ro còn lại, đã chấp nhận (A-21) | Test stub cổng model đếm lời gọi: ca (a) = 0, ca (b) = 1 và 0 ghi, rồi chạy `@ai` và quét → vẫn 1 |
| AC-10 | [H8, C1] Mọi lần ghi của bot (trường phiếu, Task, comment, trả lời, trạng thái, hành động trong danh mục, bản ghi chung, đề xuất đã áp dụng, 5 quyền) có đúng 1 dòng nhật ký: tên tool, đích (loại và tên bản ghi), từng trường với giá trị trước và sau, người ra lệnh (user ID), mã lần chạy, kết quả. Gọi cùng tool hai lần trong một lần chạy → hai dòng. Lần bị từ chối cũng có dòng với `ok=false` và lý do. Giá trị của trường mật khẩu và khóa được che | Test gọi mỗi tool ghi (mỗi tool ghi một ca, thêm một ca gọi cùng tool hai lần, một ca bị từ chối, một ca có mật khẩu giả); đếm dòng và đối chiếu giá trị |
| AC-11 | [C5] Công tắc 5 tắt (mặc định): comment đề xuất không chứa đường dẫn đổi trạng thái, chỉ có đường dẫn mở đề xuất; mở đường dẫn cũ `change_decision` một lần không đổi trạng thái đề xuất và không tạo job áp dụng; Duyệt và Từ chối đòi thao tác xác nhận có chủ ý. Công tắc 5 bật: đường dẫn một lần bấm chỉ dùng được một lần (lần hai bị từ chối), hết hạn sau số giờ cấu hình (mặc định 24, A-13), chỉ hợp lệ khi người bấm đang đăng nhập và đủ điều kiện duyệt (AC-35); người khác, kể cả Instructor không đủ điều kiện, bị từ chối. Rủi ro còn lại: trình duyệt của người duyệt tải trước đường dẫn (A-4) | Test 6 ca: GET khi tắt (trạng thái đứng yên), bật + đúng người, bật + lần hai, bật + quá hạn (đồng hồ giả lập), bật + người khác, bật + chưa đăng nhập |
| AC-12 | [H10, C4] Cấu hình có môi trường site `test` hoặc `production`, mặc định `production` (cũng cho site đang có). Ở đường chính (danh mục, đề xuất), các loại Custom Field, Server Script, Client Script, Property Setter, Workflow, Data Import chạy, sửa file code, lệnh bench chỉ thực hiện được khi môi trường là `test`; ở `production` bị từ chối, không tạo đề xuất, bot đăng 1 comment "cần làm trên site test". 5 công tắc không bị chặn bởi môi trường nhưng thông báo bật (AC-4) và nhật ký (AC-10) ghi giá trị môi trường | Test 8 loại × 2 môi trường ở đường chính = 16 ca; test công tắc 2 bật ở `production` vẫn ghi và log có "production" |
| AC-13 | [Điểm architect 1, 2] Quyền ghi của một lần chạy do tác giả của comment gọi bot (`@ai`) quyết, không do comment cũ nào trong 30 comment gần nhất. Bot gán phiếu cho một người không làm người đó thành người ra lệnh trên phiếu. Người gõ `@ai` không đủ quyền thì không có tool ghi ERP, dù một Instructor đã comment trước đó | Test 4 ca: Instructor comment cũ + người thường gõ `@ai` → không tool ghi; Instructor gõ → có; người được bot gán gõ → theo vai của họ chứ không theo việc được gán; 30 comment trở lên không đổi kết quả |
| AC-14 | [C5, Điểm architect 4] Lúc áp dụng đề xuất đã duyệt, hệ thống kiểm lại người duyệt vẫn đủ điều kiện (AC-35). Mất quyền giữa lúc duyệt và lúc áp thì không áp, đề xuất sang trạng thái hết hiệu lực, 1 comment (AC-23) | Test: duyệt, gỡ role trước khi job chạy, chạy job → 0 thay đổi dữ liệu, trạng thái hết hiệu lực |
| AC-15 | [Điểm architect 3, C1] Khi Toàn quyền bật, chốt chặn hàm `erp_ai.*` và 4 DocType của app không bị lách bằng chuỗi thoát (`\u`), JSON lồng, chữ hoa thường, khoảng trắng | Test ≥ 6 biến thể mã hóa tên hàm và tên DocType: mọi ca bị từ chối, dữ liệu không đổi |

### Gói 2, Phân loại và routing
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-16 | [G1] Lịch quét chạy mỗi 15 phút. Mỗi lần quét xếp hàng đúng các phiếu: tạo sau khi agent bật, chưa có dòng phân loại thành công (gồm lần chạy lỗi: gateway lỗi, trả sai định dạng, job mất), tạo quá 5 phút. Không xếp hàng: phiếu do agent tạo, nhóm loại trừ, cờ không dùng AI, đã điền đủ 3 trường, đã dùng hết số lần chạy trong ngày (NFR-2). Quét hai lần liên tiếp → vẫn một job cho mỗi phiếu | Test 7 loại phiếu → đúng phiếu được xếp hàng; test lần chạy lỗi rồi quét → được xếp lại; test quét hai lần (NFR-3); đối chiếu khai báo lịch có chu kỳ 15 phút |
| AC-17 | [G1] Mỗi lần phân loại thành công ghi độ trễ (thời điểm có kết quả trừ thời điểm tạo phiếu). Báo cáo ERP AI Accuracy hiện thêm 3 số trong khoảng ngày chọn: phiếu phân loại trong ≤ 5 phút, trong > 5 phút, chưa phân loại. Số này chỉ báo, không là cổng (A-9) | Test với 6 phiếu giả lập có độ trễ 1, 5, 6 phút, lỗi, chưa chạy, bị bỏ qua → 3 số đúng; mốc biên đúng 5 phút tính "≤ 5" |
| AC-18 | [G12] Báo cáo ERP AI Accuracy trả kết luận cửa L0 → L1 trên 14 ngày liền gần nhất: "Đạt" khi có ≥ 30 phiếu có nhãn và đúng ≥ 85%; "Chưa đủ mẫu" khi < 30 phiếu có nhãn; "Chưa đạt" khi ≥ 30 phiếu và < 85%. Đổi mức lên L1 trở lên khi kết luận không phải "Đạt" thì form cấu hình hiện cảnh báo, không chặn (A-8) | Test 7 ca: 29 phiếu có nhãn → "Chưa đủ mẫu"; 40 phiếu, 34 đúng (đúng 85%) → "Đạt"; 40 phiếu, 33 đúng (82,5%) → "Chưa đạt"; 30 phiếu, 26 đúng → "Đạt"; phiếu ngoài cửa sổ 14 ngày không tính; lưu cấp L1 khi "Chưa đạt" → có cảnh báo; khi "Đạt" → không cảnh báo |
| AC-19 | [G12] Nhãn người gõ lúc tạo phiếu (đầu mục, nhóm, ưu tiên) được ghi vào nhật ký trước khi bot ghi. Độ đúng so dự đoán với: nhãn lúc tạo nếu có; không có thì nhãn người đặt hoặc sửa sau đó; không có cả hai thì là "chưa có nhãn", không tính đúng, không tính vào mẫu 30. Lần chạy lỗi tính ở cột riêng, không bị bỏ khỏi báo cáo. Phiếu D/E không bị tính "bị sửa" chỉ vì bot để trống nhóm | Test 6 loại phiếu (nhãn lúc tạo, sửa sau, im lặng, lỗi, D/E bỏ trống nhóm, hai nhãn khác nhau) → từng số trong báo cáo |
| AC-20 | [G12] Người chỉ có role `ERP AI Instructor` (không System Manager) mở và chạy được báo cáo ERP AI Accuracy, báo cáo chi phí (AC-60) và thống kê duyệt (AC-37); người không có role đó bị từ chối | Test quyền 3 tài khoản: Instructor, người chỉ có Agent, System Manager |
| AC-21 | [H1] Với mỗi tập con khác rỗng của 3 trường (loại, nhóm, ưu tiên) người điền lúc tạo (6 tập, tập đủ 3 trường vẫn bị bỏ qua như nay), ở mọi mức L1+: giá trị người điền không đổi sau lần chạy; trường còn trống được bot điền. Người sửa trường khi chưa có dòng log đầu tiên cũng được ghi là sửa của người và lần `@ai` sau không đè. Ghi của bot qua công cụ bản ghi chung (quyền 2) vào HD Ticket không được tính là sửa của người | Test 6 tập con + 1 ca sửa trước log + 1 ca ghi qua quyền 2; assert `ai_classified_by` và từng trường |
| AC-22 | [H2] Độ tin cậy của phân loại và của mỗi đề xuất là số nguyên 0–100 (nhãn Cao/Trung bình/Thấp cũ giữ cho dữ liệu cũ). Dưới ngưỡng (mặc định 70, sửa trong cấu hình): lần chạy không có tool ghi nào (không ghi trường, không gán, không tạo Task, không hành động ERP, không trả lời ngoài câu hỏi) và đăng đúng 1 comment hỏi; từ ngưỡng trở lên chạy bình thường. Comment đề xuất phải có "Độ tin cậy: NN%" và phần "Căn cứ" không rỗng, thiếu thì tool trả lỗi cho model và comment không được đăng | Test stub trả 69, 70, 100, thiếu căn cứ: đếm tool ghi và comment; ca đổi ngưỡng sang 80 |
| AC-23 | [H3] Mỗi hành động có đúng 1 comment trên phiếu: routing thành công (một comment gộp trường đã ghi, người gán, Task tạo); kết quả áp dụng đề xuất (xong, lỗi, hết hiệu lực, hoàn tác); lần chạy lỗi sau lần cuối; lần chạy bị bỏ qua vì hết ngân sách hoặc chạm giới hạn ngày (tối đa 1 comment mỗi phiếu mỗi ngày). Không comment cho: agent tắt, mức L0, phiếu nhóm loại trừ hoặc cờ không dùng AI (chỉ log) | Test ma trận 9 tình huống, đếm comment từng ca; chạy lặp trong ngày vẫn 1 comment cho ca bỏ qua |
| AC-24 | [H11, QĐ-5] Cấu hình cho tên của 7 trường sẵn có (Tính chất phiếu, Phân hệ ERP, Nguồn phát sinh, Hạn hoàn thành, Dự án, Mã hàng, Số sê-ri) và giá trị nghĩa "Chỉ đạo BGĐ", mặc định rỗng. Khi đặt và trường có trên phiếu: giá trị của phiếu có trong dữ liệu gửi cho bước phân loại và lập luận. Đặt tên trường không tồn tại thì lưu bị chặn với thông báo. Chưa đặt: phần hành vi phụ thuộc không chạy, 1 dòng log nêu "chưa cấu hình trường X" | Test với trường tùy biến do test tạo: có/không có trường × có/không cấu hình = 4 ca; assert yêu cầu của stub; assert lưu tên sai bị chặn |
| AC-25 | [H12] Ba ngoại lệ ưu tiên được bảo đảm bằng mã, không chỉ bằng điểm model chấm: A và model báo chặn nghiệp vụ kế toán hoặc kho → ít nhất Urgent; B và hạn ≤ 24 giờ → ít nhất High; D và có Hạn hoàn thành → ít nhất High. Ba quy tắc còn lại của FEAT-006 (tiền tố [GẤP]/[GẬP], F → Low, E không ghi) giữ nguyên (A-10). Không có trường hạn trên site thì ngoại lệ B/D theo hạn bỏ qua và có 1 dòng log | Test bảng chân trị ≥ 14 ca (6 đầu mục × có/không điều kiện, 2 ca thiếu trường hạn) |
| AC-26 | [H12] Cấu hình có mốc phản hồi mong đợi theo đầu mục (mặc định 15', 15', 1h, 1h, 1h, 5' cho A–F, theo bảng mục 3). Phiếu quá mốc mà chưa có phản hồi nào ra ngoài (bot hoặc người) được đánh dấu "quá mốc phản hồi" trong log và đếm trong báo cáo hằng ngày. Đầu mục D, E dùng Hạn hoàn thành làm mốc xử lý khi trường đã cấu hình (AC-24) | Test đồng hồ giả lập: phiếu quá mốc, đúng mốc, đã phản hồi; D có/không Hạn hoàn thành |
| AC-27 | [H12] Khi người theo dõi phiếu D (IT) đã cấu hình, phiếu đầu mục D được thêm người đó làm người theo dõi đúng một lần; đầu mục khác không; chưa cấu hình thì không thêm và có 1 dòng log | Test: D có cấu hình, D chạy lại, C, D không cấu hình |
| AC-28 | [H12] Khi bước phân loại báo phiếu gộp ≥ 2 yêu cầu, bot đăng đúng 1 comment liệt kê các yêu cầu và xin người tạo xác nhận; lưu cờ tách vào nhật ký; không tạo, sửa, đóng phiếu nào; chạy lại không đăng lần hai. Việc tách thật nằm ngoài phạm vi (N-3) | Test phiếu 4 yêu cầu → 1 comment, 0 phiếu mới; chạy lại → vẫn 1 |

### Gói 3, Danh mục trắng, duyệt, mức tự chủ
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-29 | [H5, C2] Danh mục trắng nằm trong cấu hình; mặc định không có dòng nào, mọi hành động ghi ERP bị từ chối với thông báo "ngoài danh mục" và không đổi dữ liệu. Thêm một dòng thì đúng hành động hoặc DocType đó, đúng trường, đúng đầu mục đó dùng được, ở chế độ của dòng; có hiệu lực từ lần chạy kế tiếp, không deploy. Lưu bị chặn khi dòng trỏ vào điều cấm cứng (xóa, Role Permission, chứng từ đã submit, DocType của app) hoặc hành động không có | Test: danh mục rỗng × mỗi hành động của AC-30 và đề xuất bản ghi = từ chối; thêm 1 dòng → chỉ dòng đó dùng được; lưu 4 dòng cấm → bị chặn |
| AC-30 | [H5] Năm hành động có tên: (1) tạo tài khoản theo mẫu: vai trò ⊆ tập vai trò của mẫu trong cấu hình; System Manager, Administrator, ERP AI Instructor, ERP AI Agent, Guest, All và trường mật khẩu bị từ chối; (2) thêm người vào nhóm Helpdesk: thêm 1 người, các thành viên cũ còn nguyên; (3) thêm ngày nghỉ vào Holiday List: các dòng cũ còn nguyên; (4) đổi Item Group của một Item: chỉ trường đó đổi; (5) tạo Custom Field: từ chối `permlevel`, `fetch_from`, `ignore_user_permissions` và mọi thuộc tính ngoài danh sách cho phép. Mỗi hành động tuân chế độ của dòng danh mục (AC-33, AC-36) | Test 5 hành động × (1 ca đúng + 1 ca bị từ chối); ca (2), (3) assert tập cũ ⊆ tập mới và số thêm = 1 |
| AC-31 | [H4] Mức hiệu lực của một phiếu = nhỏ hơn giữa mức toàn hệ thống và mức tối đa của đầu mục trong cấu hình. Mặc định theo bảng mục 3: A L2, B L3, C L1, D L2, E L1, F L3 (C chỉ L1 vì việc nhỏ cần site test, N-4). Vượt ngân sách thì mọi đầu mục về L1 | Test 6 đầu mục × 4 mức toàn hệ thống × có/không vượt ngân sách |
| AC-32 | [H4] Ở mức hiệu lực L1: không có tool ghi ERP; bot chỉ đăng comment đề xuất (chẩn đoán, phương án, độ tin cậy, căn cứ) và dùng được tool Task nháp. Task (tool ghi phiếu) cấp ở L1+ như nay | Test tập tool ở L1 cho 6 đầu mục |
| AC-33 | [H4, N-1] Ở mức hiệu lực ≥ L2, một hành động có chế độ `Cần duyệt`, hoặc chế độ `Tự làm` nhưng chưa đủ điều kiện AC-36, tạo đề xuất chờ duyệt, chưa ghi gì. Comment đề xuất nêu hành động, đích, giá trị, độ tin cậy, căn cứ và có Duyệt, Sửa, Từ chối. Sau Duyệt: áp dụng đúng một lần (Duyệt hai lần vẫn một lần), có dòng log (AC-10) và 1 comment kết quả (AC-23). Sau Từ chối: không ghi, có log và comment. Đề xuất hết hiệu lực khi giá trị hiện tại của đích khác giá trị trước lúc đề xuất. Đề xuất sửa code và lệnh bench (quyền 4) dùng cùng luồng và cùng trạng thái | Test: dữ liệu đích không đổi cho tới khi duyệt; duyệt 2 lần; từ chối; đích đổi giữa chừng → hết hiệu lực; 1 đề xuất code đi qua cùng trạng thái |
| AC-34 | [C5, A3-6] "Sửa": người duyệt đổi giá trị trong đề xuất rồi duyệt; giá trị mới được kiểm lại theo danh mục và điều cấm cứng; giá trị áp dụng là giá trị đã sửa; kết quả ghi "duyệt có sửa" kèm giá trị trước và sau của lần sửa. Sửa ra ngoài trường hoặc đích cho phép bị từ chối | Test 3 ca: sửa hợp lệ, sửa sang trường ngoài danh mục, sửa sang DocType cấm |
| AC-35 | [H4] Người duyệt hợp lệ là người đang được giao phiếu (việc gán còn mở) hoặc người có `ERP AI Instructor` (A-6). Người tạo phiếu không có hai điều kiện đó, người có role Agent không được giao, tài khoản agent: bị từ chối khi Duyệt, Sửa, Từ chối | Test 5 vai |
| AC-36 | [H4] Hành động `Tự làm` chạy không cần duyệt chỉ khi đồng thời: mức hiệu lực L3; đầu mục được phép; độ tin cậy ≥ ngưỡng; số lần duyệt liên tiếp không sửa của loại hành động đó ≥ giá trị cấu hình (mặc định 20). Không đủ thì rơi về `Cần duyệt`. Sau khi tự làm, bot đăng 1 comment báo lại. Từ chối, duyệt có sửa, hoàn tác đặt bộ đếm của loại đó về 0 | Test biên 19 / 20; ca bị từ chối giữa chừng reset; ca đầu mục C (cap L1) không tự làm |
| AC-37 | [H4, A3-12] Có thống kê duyệt theo loại hành động và theo tháng: số đề xuất, duyệt không sửa, duyệt có sửa, từ chối, hoàn tác, bộ đếm liên tiếp hiện tại, hai tỷ lệ "duyệt không sửa" và "duyệt (kể cả có sửa)" trên số đã quyết. Hiển thị mục tiêu ≥ 70% của GĐ2. Việc phân biệt "sửa nhỏ" không tự động (A-14) | Test 10 đề xuất giả lập → từng số và hai tỷ lệ |
| AC-38 | [H9] Ghi đè prompt theo ba phần trong cấu hình: bước phân loại, phần chỉ dẫn lập luận, bảng hướng dẫn theo đầu mục; rỗng = bản dựng sẵn. Phần có nội dung được dùng ở lần chạy kế tiếp, không deploy. Lưu bị chặn khi thiếu mục bắt buộc của phần đó (danh sách do designer lập) hoặc quá dài. Các câu cấm tuyệt đối và khối của 5 quyền không bị ghi đè dù cấu hình có gì. Mỗi lần sửa có lịch sử (người, thời điểm, giá trị cũ) | Test: đặt phần phân loại → yêu cầu của stub chứa nội dung mới; đặt chuỗi xóa câu cấm → câu cấm vẫn có; lưu thiếu mục → chặn; kiểm tồn tại bản ghi lịch sử |
| AC-39 | [C5, N-1] Duyệt, Sửa, Từ chối làm được từ trang phiếu Helpdesk (comment của bot hoặc ngăn của bot trên trang đó), không cần mở màn hình khác ngoài hộp xác nhận. Trạng thái đổi sau thao tác, comment kết quả hiện trên trang phiếu | Kiểm có đầu ra: trên site dev, bật một dòng danh mục `Cần duyệt`, cho bot đề xuất, người duyệt thao tác; dán ảnh và dòng log. Phần kỹ thuật hiển thị: R-3 |

### Gói 4, Tri thức, trả lời, đóng phiếu
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-40 | [G10, N-2] Công tắc "trả lời người tạo" tắt: không có tool trả lời. Bật: tool gửi trả lời tới người tạo phiếu; người tạo không có role Agent đọc được nội dung đó; chỉ gửi cho người tạo của phiếu; không gửi cho phiếu nhóm loại trừ hoặc cờ không dùng AI. Mỗi trả lời có 1 dòng log (AC-10). Với đầu mục F, trả lời đòi ít nhất 1 nguồn (tên bài CSKT, mục HDSD hoặc số phiếu cũ), thiếu thì phải là câu hỏi lại; dưới ngưỡng tin cậy chỉ được hỏi lại. Sau trả lời đầu tiên, phiếu có mốc phản hồi đầu tiên theo định nghĩa của Helpdesk (R-1) | Test: tắt → tool vắng; bật → người dùng không có role Agent đọc được; ca nhóm loại trừ → từ chối; F không nguồn → từ chối; 69% trả lời → từ chối, hỏi lại → qua; kiểm mốc phản hồi |
| AC-41 | [G10] Khi người tạo phiếu trả lời sau tin nhắn của bot (qua email hoặc cổng), bot chạy một lần cho tin đó, chịu giới hạn NFR-2. Tin của chính bot, tin của người khác không có từ khóa gọi bot không kích hoạt. Tin này cũng đặt lại đồng hồ im lặng của AC-44 | Test 4 ca: người tạo trả lời → 1 job; bot tự gửi → 0; người khác → 0; hết giới hạn ngày → 0 và 1 comment (AC-23) |
| AC-42 | [G5, G6, N-2] Chốt chung của hai đường đổi trạng thái: (a) cả hai công tắc tắt thì bot không đổi `status` phiếu bằng bất kỳ tool hay job nào; (b) phiếu có nguồn "Chỉ đạo BGĐ" hoặc đầu mục E không bao giờ bị bot đổi trạng thái theo hai đường này, và không bị đổi bởi công cụ bản ghi chung hay Toàn quyền; (c) khi trường "Nguồn phát sinh" chưa cấu hình (AC-24) thì không đường nào chạy, 1 dòng log mỗi ngày nêu lý do (A-11); (d) trạng thái nào cũng ghi log và 1 comment | Test bảng chân trị: 6 đầu mục × {BGĐ, không BGĐ, chưa cấu hình} × 2 công tắc; thêm 2 ca thử ghi `status` bằng quyền 2 và quyền 1 trên phiếu BGĐ và E |
| AC-43 | [G5] Công tắc "Resolved khi Task xong" bật: phiếu có ≥ 1 Task liên kết, mọi Task liên kết đã Completed (Task Cancelled không tính, và phải còn ≥ 1 Task Completed) thì phiếu chuyển Resolved, 1 dòng log, 1 comment. Chưa xong hết, không có Task, phiếu đã Resolved hoặc Closed: không đổi. Chạy lại: không đổi hai lần. Task do người tạo mà không có liên kết phiếu không được tính (A-11) | Test 7 ca: 2/2 xong, 1/2 xong, 0 Task, 1 Cancelled + 1 Completed, tất cả Cancelled, phiếu đã Closed, sự kiện lặp |
| AC-44 | [G6] Công tắc "đóng phiếu F" bật: phiếu đầu mục F không phải BGĐ, đã có trả lời hoặc câu hỏi của bot gửi cho người tạo, người tạo không phản hồi sau số ngày cấu hình (mặc định 3), đang không ở trạng thái đóng, thì chuyển trạng thái đóng, có 1 comment và 1 thông báo tới người tạo. Người tạo trả lời trước hạn: đồng hồ bắt đầu lại. Phiếu đầu mục khác và phiếu F chưa từng được bot trả lời không bị đóng | Test đồng hồ giả lập: 2 ngày 23 giờ (không đóng), 3 ngày (đóng), có trả lời ở ngày 2 (không đóng), F do BGĐ, E, C, F chưa trả lời |
| AC-45 | [G7] Công tắc soạn CSKT bật, mức hiệu lực ≥ L1: khi phiếu chuyển Resolved hoặc Closed, bot soạn đúng 1 bài HD Article ở trạng thái nháp, liên kết về phiếu nguồn, gồm vấn đề và các bước đã giải quyết. Không soạn khi: phiếu nhóm loại trừ hoặc cờ không dùng AI (NFR-1); phiếu đóng bằng quy tắc im lặng AC-44; phiếu không có nội dung giải quyết (không có chi tiết giải quyết và không có comment của người phụ trách) (A-16). Bot không xuất bản được bài. Đóng lại lần hai không sinh bài thứ hai. Người có Instructor mở được danh sách bài nháp do bot soạn | Test 6 ca: phiếu thường; nhóm loại trừ; cờ không dùng AI; đóng do im lặng; không nội dung; đóng hai lần. Assert trạng thái bài = nháp, bot không đổi được sang xuất bản. NFR-1: quét bài tìm chuỗi gieo |
| AC-46 | [G8] Công cụ tìm CSKT: tìm bài đã xuất bản theo nội dung (không theo tên băm), trả về tên, tiêu đề và đoạn trích, tối đa số kết quả cấu hình (mặc định 5, A-13); không trả bài nháp hoặc lưu trữ; câu truy vấn hai từ đảo thứ tự vẫn tìm thấy, bài khớp nhiều từ xếp trước | Test 6 bài (2 nháp, 1 lưu trữ): kết quả, thứ tự, giới hạn |
| AC-47 | [G8] Công cụ tìm HDSD: khi kho HDSD đã cấu hình, tìm theo nội dung và trả đoạn khớp kèm tên tài liệu và vị trí; chưa cấu hình thì trả "chưa có kho HDSD" và model không bịa nguồn. Nội dung kho không vào được qua tool đọc mã nguồn thay cho tool này | Test với kho giả gồm 3 tài liệu: khớp, không khớp, chưa cấu hình |
| AC-48 | [G8] Tìm phiếu cũ trả về cách giải quyết thật: ngoài tiêu đề và chi tiết giải quyết, kèm tối đa số comment cuối của người phụ trách (không phải comment của bot) khi chi tiết giải quyết trống; xếp theo số từ khớp, không chỉ khớp chuỗi con. Không trả phiếu nhóm loại trừ hoặc cờ không dùng AI. Prompt chính nhắc ba nguồn (CSKT, HDSD, phiếu cũ) và yêu cầu nêu nguồn trong "Căn cứ" | Test 5 phiếu Resolved (1 nhóm loại trừ, 1 chi tiết trống có comment, 1 chi tiết trống không comment): nội dung và thứ tự; assert prompt có 3 nguồn |
| AC-49 | [G9] Tool chạy báo cáo: chỉ chạy báo cáo có trong danh sách cho phép của cấu hình (mặc định rỗng → từ chối), theo quyền của tài khoản agent, chỉ đọc, giới hạn số dòng (mặc định 20, A-13), mức L1+. Kết quả không chứa nội dung phiếu nhóm loại trừ | Test: danh sách rỗng, báo cáo ngoài danh sách, báo cáo trong danh sách vượt 20 dòng, báo cáo chạm phiếu loại trừ |
| AC-50 | [G9] Tool đọc Error Log: chỉ đọc, lọc theo khoảng thời gian và từ khóa, giới hạn số dòng, che khóa, mật khẩu, token trong nội dung (NFR-6). Không cần cấp System Manager cho tài khoản agent (điểm architect A-3) | Test: lọc, giới hạn, một Error Log chứa khóa giả bị che; assert tập role của tài khoản agent không đổi |

### Gói 5, Vận hành
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-51 | [G2, G4] Báo cáo hằng ngày lúc 08:00 giờ site gửi tới người nhận COO trong cấu hình. Nội dung: số phiếu mới 24 giờ qua (theo đầu mục và ưu tiên) kèm danh sách; phiếu sắp quá hạn (còn ≤ 24 giờ tới mốc xử lý hoặc Hạn hoàn thành) và đã quá hạn; phiếu quá mốc phản hồi (AC-26); phiếu C thiếu BA note quá 24 giờ và C/D thiếu Task quá 3 ngày; tiến độ đầu mục D, E (xong, đang làm, quá hạn); việc bot đã làm theo loại (phân loại, gán, Task, comment, trả lời, đóng, đề xuất chờ duyệt, đã duyệt, bị từ chối, lỗi) và chi phí hôm qua | Test dữ liệu giả lập 12 phiếu đủ loại → từng mục của nội dung; đối chiếu khai báo lịch 08:00 |
| AC-52 | [G2] Người nhận rỗng → không gửi, 1 dòng log mỗi ngày. Gửi hai lần cùng ngày → 1 email (NFR-3). Gửi lỗi → ghi log, không ném ngoại lệ ra khỏi job. Phiếu nhóm loại trừ chỉ có trong số đếm và số phiếu, không có tiêu đề hay nội dung (NFR-1). Ngày không có phiếu vẫn gửi với số 0 | Test 5 ca: người nhận rỗng, hai lần, lỗi gửi, phiếu nhóm loại trừ với chuỗi gieo, ngày trống |
| AC-53 | [G3] KPI 1 "thời gian phản hồi đầu tiên": trung vị số phút từ lúc tạo tới phản hồi đầu tiên ra ngoài (bot hoặc người) của các phiếu tạo trong tuần, kèm tỷ lệ trong ≤ 15 phút và ≤ 5 phút. KPI 2 "phiếu đủ đầu mục, nhóm, ưu tiên": tỷ lệ trên phiếu đang mở. KPI 3 "phiếu đóng không cần người làm": tỷ lệ trên phiếu đóng trong tuần mà mọi hành động phía agent trên phiếu (comment, trả lời, đổi trạng thái, gán) là của tài khoản bot (A-14) | Test bộ dữ liệu cố định 10 phiếu, mỗi KPI có ca đúng tay tính; ca mẫu bằng 0 hiện "chưa có dữ liệu", không chia cho 0 |
| AC-54 | [G3] KPI 4 "thời gian xử lý trung bình đầu mục B": trung bình số giờ từ tạo tới Resolved của phiếu B được Resolved trong tuần. KPI 5 "phiếu C có Task liên kết trong 3 ngày": trên phiếu C tạo ≥ 3 ngày trước thời điểm tính, tỷ lệ có ≥ 1 Task liên kết tạo trong 72 giờ kể từ lúc tạo phiếu. KPI 6 "phiếu tồn > 5 ngày": số phiếu đang mở quá 5 ngày, và riêng số quá 7 ngày | Test bộ dữ liệu cố định; ca biên đúng 72 giờ, đúng 5 ngày; mẫu bằng 0 |
| AC-55 | [G3] Số KPI tính hằng tuần vào 08:00 thứ Hai cho tuần trước (A-14); lưu theo tuần để so tuần trước; tính lại cùng tuần cho cùng giá trị và không thêm dòng (NFR-3). Mục tiêu GĐ2 và GĐ4 theo bảng mục 5 nằm trong cấu hình | Test tính tuần W hai lần → 1 bộ; tuần W+1 so với W |
| AC-56 | [G3] COO và người có `ERP AI Instructor` xem 6 KPI cùng nhau ở một màn hình, mỗi KPI kèm giá trị tuần này, tuần trước, mục tiêu GĐ2 và GĐ4. Màn hình là Trang tổng quan Helpdesk nếu thêm được mà không sửa lõi Helpdesk, nếu không là một trang của app (A-15) | Kiểm có đầu ra: mở màn hình bằng tài khoản Instructor và dán ảnh; test quyền: người không có role bị từ chối |
| AC-57 | [G4] Nhắc hạn: với phiếu D, E đang mở có Hạn hoàn thành (hoặc mốc xử lý): đúng 1 lời nhắc khi còn 24 giờ (A-13) và đúng 1 lời nhắc khi quá hạn; lời nhắc gửi tới người phụ trách. Phiếu thường: comment trên phiếu. Phiếu nhóm loại trừ: thông báo chỉ có số phiếu và hạn, không tiêu đề, không nội dung, không lời gọi model, không comment (A-12). Phiếu đã đóng không được nhắc | Test đồng hồ giả lập, 3 loại phiếu × {còn 24h, quá hạn, đã đóng}, đếm lời nhắc; nhóm loại trừ với chuỗi gieo |
| AC-58 | [G4] Kiểm mốc: phiếu C tạo ≥ 24 giờ mà chưa có BA note (AC-62) và phiếu C/D tạo ≥ 3 ngày mà chưa có Task liên kết được nhắc đúng 1 lần mỗi mốc bằng comment tới người phụ trách và có trong báo cáo (AC-51). Có BA note hoặc Task rồi thì không nhắc | Test đồng hồ giả lập, 6 ca: có/không BA note, có/không Task, ở 23 giờ và 24 giờ, 71 giờ và 72 giờ |
| AC-59 | [G11] Mỗi tháng tạo một danh sách rà soát gồm 10 phiếu chọn ngẫu nhiên trong các phiếu bot có ít nhất 1 lần ghi trong tháng trước (ít hơn 10 thì lấy hết); loại phiếu nhóm loại trừ. Mỗi dòng có chỗ ghi kết luận (đúng, sai, ghi chú) và người rà. Chạy lại cùng tháng không chọn bộ khác. Người rà soát trong cấu hình nhận thông báo, rỗng thì không có thông báo nhưng danh sách vẫn tạo | Test 25 phiếu giả lập → 10 phiếu không trùng; 6 phiếu → 6; chạy lại → cùng bộ; nhóm loại trừ vắng mặt |
| AC-60 | [G13] Báo cáo chi phí cho tổng chi (USD) theo từng lần chạy và theo từng phiếu trong khoảng ngày chọn. Tổng theo phiếu cộng lại bằng tổng các dòng nhật ký của phiếu; tổng cả tháng bằng tổng chi tháng đang hiển thị | Test 3 phiếu × 4 lần chạy giả lập → từng tổng khớp tay tính, sai số 0 ở 6 chữ số thập phân |
| AC-61 | [G13] Kiểm ngân sách trước mỗi lần chạy dùng tổng các dòng nhật ký hiện có, không dùng số chốt của hôm trước. Lần đầu chi tháng vượt ngân sách: đúng 1 email tới `alert_recipients` và 1 dòng log. Phiếu chạm giới hạn lần chạy trong ngày: đúng 1 thông báo trong ngày đó (AC-23) | Test: gieo dòng log tổng > ngân sách giữa ngày → lần chạy kế lùi về L1, 1 email; lần thứ hai không có email; phiếu chạm 5 lần → 1 thông báo |

### Gói 6, Đầu mục C
| Mã | Tiêu chí (đo được) | Cách kiểm |
|---|---|---|
| AC-62 | [H13] Phiếu đầu mục C ở mức hiệu lực ≥ L1 nhận đúng 1 comment "BA note" gồm: mục tiêu, phạm vi, tính năng sẵn có của ERPNext, Frappe hoặc fork Miyano đã tìm (có hoặc không, kèm nguồn), rủi ro, câu hỏi mở; mỗi mục không rỗng. Chạy lại không đăng lần hai. Độ tin cậy dưới ngưỡng thì chỉ có phần câu hỏi mở (AC-22) | Test stub: đủ 5 mục; thiếu mục → tool trả lỗi cho model; chạy lại → 1 comment; 69% → chỉ câu hỏi |
| AC-63 | [H13] Bot tạo nhiều Task cho một phiếu C, mỗi Task có tiêu đề, mô tả, ước lượng bằng giờ (số dương), liên kết về phiếu. Tối đa số Task mỗi lần chạy (mặc định 10, A-13). Chạy lại không tạo trùng (khớp theo phiếu và tiêu đề). Task không có ước lượng bị từ chối | Test: 3 Task đủ trường; 1 không ước lượng → từ chối; 11 Task → dừng ở 10; chạy lại → không trùng |
| AC-64 | [H13] Tạo Project cho phiếu C đi qua đường duyệt của Gói 3: chỉ khi có dòng danh mục `Cần duyệt` cho hành động đó và người duyệt hợp lệ; sau duyệt, Project có, các Task của phiếu được gắn vào Project; trước duyệt không có Project nào. Môi trường `production` không cản hành động này | Test: danh mục có và không có dòng; trước và sau duyệt; Task được gắn |

## Assumptions decided by the team
Decide mode: mọi điểm lớn có đủ 4 trường. Sai thì sửa nghĩa là cách đảo lại.

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-1 | Hình 2, nhánh duyệt: duyệt rồi mới Thực hiện, sau đó Kiểm tra và ghi nhật ký. "Sửa" là chỉnh giá trị rồi thực hiện; "Từ chối" là không thực hiện, ghi log và comment, vòng quay về bước 1 cho phiếu kế tiếp (ghi chú người chép 1, 2) | Tiêu đề hình ("chờ người duyệt trước khi làm") và bảng L2 ("khi người phụ trách bấm Duyệt") | Mũi tên vẽ từ Duyệt thẳng tới Kiểm tra (không thực hiện) | Đổi AC-33, AC-34 |
| A-2 | Cách hiểu N-1: danh mục có 3 chế độ `Cấm` / `Cần duyệt` / `Tự làm`; vắng mặt = cấm. "Việc ngoài danh mục trắng phải được bấm Duyệt" = dòng chế độ `Cần duyệt`. `Tự làm` là danh mục trắng theo nghĩa tài liệu | "Danh sách DocType được ghi là danh mục trắng, mặc định cấm" (mục 6) vẫn đúng; việc cần duyệt vẫn có chỗ trong cấu hình | Việc vắng mặt trong danh mục cũng được đề xuất để duyệt (thực chất là danh sách cấm) | Đổi AC-29, AC-33 |
| A-3 | 5 công tắc: hai đã có giữ giá trị người đã đặt, ba mới mặc định tắt; Toàn quyền bao gồm công cụ bản ghi chung (như code hiện nay); công tắc bật thì hành vi như code ngày 13/11 nhưng thêm cảnh báo, nhật ký đủ, cắt khi vượt ngân sách | N-1: "vẫn giữ nhưng công tắc riêng, mặc định tắt, bật thì có cảnh báo và ghi log đủ". Không đổi ý định của người | Ép tắt cả hai công tắc cũ sau migrate | Sửa AC-1 |
| A-4 | Giữ nguyên các khả năng nguy hiểm khi công tắc tương ứng bật, gồm cả việc Toàn quyền cho bot sửa User của chính nó và gán System Manager. Giảm nhẹ bằng cảnh báo (AC-4), cảnh báo hằng ngày, nhật ký (AC-10), cắt khi vượt ngân sách (AC-7), đường dẫn một lần bấm có hạn và dùng một lần (AC-11). Rủi ro còn lại ghi nhận: trình duyệt của người duyệt tải trước đường dẫn một lần bấm | N-1 giữ 5 quyền; thu hẹp là đảo quyết định của người | Sàn cứng "bot không tự nâng quyền" kể cả khi Toàn quyền bật | Thêm AC sàn cứng bằng change-request |
| A-5 | Môi trường mặc định `production`; chỉ chặn ở đường chính; 5 công tắc không bị chặn nhưng ghi giá trị môi trường vào cảnh báo và log. Site dev `miyano` phải được đặt `test` thì mới thử được Custom Field, Server Script trên đường chính | Mặc định cấm (mục 6); sai về phía `test` nguy hơn sai về phía `production` | Mặc định `test`; hoặc chặn cả 5 công tắc ở production | Đổi AC-12 |
| A-6 | Người duyệt hợp lệ: người được giao phiếu (việc gán còn mở) hoặc có `ERP AI Instructor`. Người tạo phiếu không có hai điều kiện đó không duyệt được | Tài liệu: "người phụ trách bấm duyệt"; ADR-012 đòi role Instructor | Chỉ Instructor; Instructor và phải khác người ra lệnh | Đổi AC-35 |
| A-7 | Độ tin cậy là số nguyên 0–100; ngưỡng 70 trong cấu hình; dưới ngưỡng chỉ hỏi | Tài liệu mục 6 nói bằng phần trăm | Giữ nhãn Cao/Trung bình/Thấp, "Thấp" = dưới 70 | Đổi AC-22 |
| A-8 | Cửa L0 → L1: báo cáo hiện kết luận, form cấu hình cảnh báo khi nâng mức mà chưa "Đạt", không chặn | Tài liệu: "mở dần theo số liệu đo được, không theo lịch cứng"; mở là quyết định của người | Chặn cứng | Đổi AC-18 |
| A-9 | Mốc 5 phút (phân loại) chỉ đo và báo, không là cổng build hay nghiệm thu | Tài liệu không nêu tỷ lệ đạt; không bịa NFR; cách làm giống A-8 của FEAT-006 | Đặt ngưỡng ≥ 95% trong 5 phút | Thêm ngưỡng khi người đặt số |
| A-10 | Giữ bảng "độ quan trọng → mức ưu tiên" của FEAT-006 (điểm 2 có thể lên High), thêm 3 ngoại lệ của tài liệu bảo đảm bằng mã | FEAT-006 A-2 đã chốt; N-1..N-3 không đụng | Hạ về đúng 3 ngoại lệ của tài liệu | Đổi AC-25 |
| A-11 | Chưa cấu hình trường "Nguồn phát sinh" thì hai đường đổi trạng thái (AC-43, AC-44) không chạy ("fail closed"). "Task liên kết" là Task có liên kết tới phiếu; Task người tạo không điền liên kết không được tính | N-2: không bao giờ áp cho phiếu BGĐ; không xác định được thì không áp. QĐ-5 | Chỉ loại đầu mục E khi thiếu trường | Đổi AC-42 |
| A-12 | Phiếu nhóm loại trừ vẫn được nhắc hạn bằng mã, không lời gọi model, không comment, chỉ gồm số phiếu và hạn | Nhắc hạn là việc của tài liệu cho E, mà E thường nằm ở hai nhóm loại trừ; đọc nội dung vẫn bị cấm (13.2) | Không nhắc cho nhóm loại trừ | Bỏ ca nhóm loại trừ khỏi AC-57 |
| A-13 | Giá trị kỹ thuật mặc định chưa có trong tài liệu, đều sửa được trong cấu hình: hết hạn đường dẫn một lần bấm 24 giờ; nhắc hạn trước 24 giờ; 5 kết quả mỗi lần tìm; 20 dòng mỗi báo cáo bot chạy; 10 Task mỗi lần chạy; báo cáo COO gửi cả cuối tuần | Không dòng nào là NFR; chỉ để AC có số kiểm được | Hỏi người từng số | Đổi số trong cấu hình |
| A-14 | Định nghĩa KPI: phản hồi đầu tiên dùng trung vị; "đủ đầu mục, nhóm, ưu tiên" tính trên phiếu đang mở (khớp cửa GĐ0 "100% phiếu mở"); "đóng không cần người làm" = mọi hành động phía agent là của bot; xử lý B tính theo giờ lịch; KPI tuần tính 08:00 thứ Hai cho tuần trước; "sửa nhỏ" không phân biệt, hai tỷ lệ cùng được hiện (AC-37) | Tài liệu cho tên KPI và mục tiêu, không cho công thức | Trung bình thay trung vị; tính trên mọi phiếu | Đổi AC-53..AC-55, AC-37 |
| A-15 | KPI hiện ở Trang tổng quan Helpdesk nếu thêm được mà không sửa lõi Helpdesk (R-2); nếu không thì một trang của app | Tài liệu ghi Trang tổng quan Helpdesk; không sửa lõi Helpdesk | Luôn dùng trang của app | Đổi AC-56 |
| A-16 | Soạn bài CSKT có công tắc riêng, mặc định tắt (việc ghi vào HD Article, tốn một lời gọi model). Bỏ qua phiếu không có nội dung giải quyết và phiếu đóng do im lặng | Mỗi phiếu đóng một lần gọi model là chi phí mới; bài từ phiếu không có lời giải là rác | Soạn cho mọi phiếu đóng | Đổi AC-45 |
| A-17 | Dữ liệu site `miyano` (còn 4 loại cũ, thiếu 4 nhóm, SLA và Assignment Rule lệch, tài khoản agent mang nhiều role) không là căn cứ cho tiêu chí hay test; test tự dựng dữ liệu | Cách làm A-13 của FEAT-006; QĐ-4 | Dọn site trước | Không áp dụng |
| A-18 | Test đang ghim hành vi mà spec đổi được sửa theo AC (NFR-8). Năm test đỏ vì đọc cài đặt đã lưu của site (`handoff-direct-session.md` mục 2) được sửa để tự đặt cài đặt, vì phải xanh `cmd.test` | STD-TEST-5: đổi test chỉ khi spec đổi | Để nguyên đỏ | Tách thành bug riêng |
| A-19 | Quan hệ với feature khác: AC-29, AC-30 thu hẹp hoặc thay phần "tạo User và sửa cấu hình qua DocType" của FEAT-005 (0/52 task); FEAT-004 còn các luật kiến trúc T31, T32, T44, T48 và việc comment kết quả áp dụng (trùng AC-23). Đề nghị team-leader thu hẹp hoặc đóng FEAT-005 và gộp phần trùng của FEAT-004 khi merge | `handoff-direct-session.md` mục 4, 5; `gap-audit.md` mục 6.5 | Làm song song không gộp | Team-leader quyết khi lập kế hoạch |
| A-20 | Mọi ADR ở trạng thái "proposed", `Approved-by` trống; ADR-014..018 bị `site_api` thay trên thực tế. Spec này cần ADR mới hoặc amendment cho: 5 quyền (trái ADR-005, AC-9 FEAT-006, AC-22 FEAT-004), danh mục ba chế độ, người duyệt, môi trường site. Ghi cho architect | `gap-audit.md` mục 6.5; `handoff-direct-session.md` mục 3.5 | Không | Architect viết |
| A-21 | Lời gọi phân loại đầu tiên của phiếu chưa có nhóm và không có tiền tố bộ phận loại trừ vẫn gửi tiêu đề và nội dung cắt 6000 ký tự cho model. Sau khi biết nhóm là loại trừ thì dừng (AC-9) | Không biết nhóm trước khi phân loại; muốn đọc trước thì phải đọc | Chặn mọi phiếu chưa có nhóm | Đổi AC-9 |
| A-22 | Khối lượng vượt cỡ L: 64 AC, 6 gói. Giữ một ID (QĐ-1), nhưng đề nghị team-leader coi mỗi gói là một đơn vị merge và nghiệm thu riêng, xếp lịch theo thứ tự cột "Merge". Nếu muốn tách thành feature riêng, ranh giới gói đã sạch (Gói 1 và Gói 3 là nền) | Mục 9 của quy trình: khối lượng quá cỡ thì đề xuất đổi | Giữ nguyên không chia | Team-leader mở intake mới |
| A-23 | Câu hỏi kỹ thuật chuyển cho researcher và architect (không phải ẩn số của yêu cầu): R-1..R-5, AR-1..AR-5 trong `## Câu hỏi kỹ thuật` bên dưới | Analyst không chọn công nghệ | Không | Không áp dụng |

## Câu hỏi kỹ thuật
Cho researcher (cần tài liệu đúng phiên bản Helpdesk và Frappe trên bench này):
- R-1: Trả lời tới người tạo phiếu không có role Agent đi kênh nào (comment, Communication, email, cổng khách) và đặt được mốc phản hồi đầu tiên của Helpdesk hay không; tin nhắn của người tạo quay lại bằng sự kiện nào (AC-40, AC-41, KPI 1).
- R-2: Trang tổng quan Helpdesk phiên bản này có cho thêm thẻ số hoặc biểu đồ mà không sửa lõi hay không (AC-56, A-15).
- R-3: Comment của bot hiện thế nào trên dòng thời gian Helpdesk, có nút bấm được không, ngăn "Trao đổi với bot" (HD Form Script) làm được gì (AC-39, AC-11). `handoff-direct-session.md:27` ghi chưa ai thử.
- R-4: Tìm nội dung HD Article của Helpdesk, trạng thái nháp/xuất bản/lưu trữ, quyền tạo bài nháp; kho HDSD của Miyano nằm ở đâu và ở dạng nào (AC-45, AC-46, AC-47).
- R-5: Lịch 08:00 theo giờ site, lịch hằng tuần và hằng tháng, và worker hàng đợi `long` trên production (AC-16, AC-51, AC-55, AC-59).

Cho architect (`arch-impact.md`, ADR):
- AR-1: Mô hình quyền "người ra lệnh" và "người duyệt" (AC-13, AC-14, AC-35; `gap-audit.md` mục 6.1, 6.2, 6.4).
- AR-2: Đọc Error Log và chạy báo cáo mà không cấp System Manager cho tài khoản agent, theo kiểu đọc hệ thống chỉ-đọc như ADR-021 QĐ 4 (AC-49, AC-50).
- AR-3: Cách cấu hình danh mục ba chế độ, ghi đè prompt, môi trường site cùng với ERP AI Setting đang có 27 trường (AC-12, AC-29, AC-38).
- AR-4: ADR mới hay amendment cho 5 quyền và cho các điều trái ADR-005, FEAT-006 AC-9, FEAT-004 AC-22 (A-20).
- AR-5: Chốt chặn hàm và DocType chống chuỗi thoát (AC-15), đọc `gap-audit.md` mục 6.3.

## Definition of Done
Phần build (trong các task, mỗi gói đạt riêng):
- [ ] Mọi AC-1..AC-64 đạt, đầu ra lệnh được dán trong `acceptance.md`; gói nào đủ AC của gói đó thì nghiệm thu gói đó được
- [ ] Mỗi AC có ít nhất 1 test tự động hoặc 1 bước kiểm có đầu ra (STD-TEST-2); không skip, xfail (STD-TEST-4); test mới tự đặt và trả lại cấu hình (NFR-7)
- [ ] Mỗi gói có cấu hình mặc định an toàn (NFR-4); cài lại không ghi đè giá trị người đã sửa
- [ ] ADR mới hoặc amendment cho A-20 và các câu AR-1..AR-5; câu R-1..R-5 có trả lời trong `research.md`
- [ ] Danh sách test bị sửa vì spec đổi (NFR-8, A-18) kèm lý do trong `acceptance.md`
- [ ] `cmd.test` (`cd ../.. && bench --site miyano run-tests --app erp_ai`) xanh, chạy trên cây đã merge các gói; một lần đỏ trên site dùng chung được chạy lại trước khi kết luận
- [ ] `cmd.lint` (`pre-commit run --all-files`) sạch
- [ ] `cmd.migrate` chạy được trên site dev; có bước migrate lên xuống cho thay đổi trường (STD-OPS-2)
- [ ] Làm trên nhánh `team/FEAT-007` trong worktree riêng, không checkout ở cây chính (`intake.md`, N-3); không ghi `.team/current.json`
- [ ] Có nhật ký (STD-OPS-5): mỗi việc theo lịch ghi 1 dòng mỗi lần chạy (đã chạy, bỏ qua vì cấu hình rỗng, lỗi)

Phần sau G4 (`/team:asbuilt`; G4 tắt nên làm ngay sau verify):
- [ ] As-Built viết xong (`docs/team/features/FEAT-007/asbuilt.md`), có bảng "Chiến lược → app" cập nhật từ `gap-audit.md`
- [ ] Tài liệu người dùng cập nhật: 5 công tắc quyền và cảnh báo; cách điền danh mục trắng; môi trường site; người nhận báo cáo; tên trường sẵn có; ba công tắc N-2; cách đọc 6 KPI và cửa L0 → L1; cách duyệt và sửa trên trang phiếu
- [ ] `docs/HuongDan_TrienKhai_erp-ai.md` mục 17 và dòng 34, 13.3 cập nhật theo N-1, N-2 (dòng "chỉ comment nội bộ", "không đổi status", "duyệt từng hành động") và `README.md:39` (cam kết nhóm loại trừ)
- [ ] Mục CHANGELOG
- [ ] CI xanh trên PR

Phần việc của người (QĐ-4; trên site, không phải điều kiện merge; không agent nào làm, STD-OPS-7):
- [ ] Cài 6 Loại phiếu thay bộ cũ; bắt buộc Nhóm + Ưu tiên khi tạo; SLA và Assignment Rule theo bảng mục 3; gán tay lại phiếu cũ (N-6). Kiểm: báo cáo KPI 2 (AC-53) đạt 100% phiếu mở
- [ ] Tạo HD Agent cho người nhận; điền người mặc định, bộ phận → nhóm; xem lại `excluded_teams`
- [ ] Đặt môi trường site (`test` trên site dev, `production` trên production); điền người nhận báo cáo COO, người rà soát, người theo dõi phiếu D, tên trường "Nguồn phát sinh" và giá trị "Chỉ đạo BGĐ", "Hạn hoàn thành"
- [ ] Gỡ role thừa của tài khoản agent (BUG-002); cấp `ERP AI Instructor` cho COO và người rà soát; chốt ngân sách tháng và người giữ khóa
- [ ] COO chốt danh mục trắng khởi điểm (ngày nghỉ lễ, tài khoản theo mẫu, thêm người vào nhóm Helpdesk, đổi Item Group, trả lời từ CSKT) và quyết định ô tick số 6 (chung khung hay riêng)
- [ ] Bật từng công tắc N-2 và công tắc soạn CSKT chỉ sau khi tên trường "Nguồn phát sinh" đã cấu hình (A-11); triển khai lên `erp.miyano.com.vn` qua G5 với người duyệt
