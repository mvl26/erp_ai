Feature: CHG-001
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks CHG-001

**Nguồn: `docs/team/features/FEAT-004/tasks.md` (Phần 6, T53–T68).** File này là bản soi, không phải nơi giao việc: mỗi dòng trỏ tới một task FEAT-004 thuộc CHG-001 và file review của nó; ô tick chép từ nguồn ngày 2026-11-14 (`develop` @ `4469287`). Tiêu chí, touchpoint, Receives/Returns, tiến độ và số vòng review chỉ có ở nguồn; lệch thì nguồn thắng. Không build từ file này, không có nhánh `team/CHG-001`. Lý do: `plan.md`.

- [x] T53 — M1: liên kết quyết định mở form Desk — nguồn: FEAT-004 T53 — review: docs/team/features/FEAT-004/review-53.md
- [x] T54 — M1: `decide` chỉ nhận POST, form Desk tự gọi một lần — nguồn: FEAT-004 T54 — review: docs/team/features/FEAT-004/review-54.md
- [x] T55 — M2: ghim kiểm lại người thực hiện và khóa hết giờ ở job — nguồn: FEAT-004 T55 — review: docs/team/features/FEAT-004/review-55.md
- [x] T56 — AC-28: dựng và ghi comment kết quả của đề xuất — nguồn: FEAT-004 T56 — review: docs/team/features/FEAT-004/review-56.md
- [x] T57 — AC-28: job gọi comment kết quả sau mỗi kết cục — nguồn: FEAT-004 T57 — review: docs/team/features/FEAT-004/review-57.md
- [x] T58 — AC-27, AC-12: duyệt qua `decide` không bỏ kiểm lúc áp dụng — nguồn: FEAT-004 T58 — review: docs/team/features/FEAT-004/review-58.md
- [x] T59 — M3: tập cấm của `site_api` dẫn xuất, so tên không phân biệt hoa thường — nguồn: FEAT-004 T59 — review: docs/team/features/FEAT-004/review-59.md
- [x] T60 — `site_api._write` không để lại nửa chừng, đủ nhánh từ chối — nguồn: FEAT-004 T60 — review: docs/team/features/FEAT-004/review-60.md
- [x] T61 — `api_call_method` không bao giờ trả khóa API hay mật khẩu — nguồn: FEAT-004 T61 — review: docs/team/features/FEAT-004/review-61.md
- [x] T62 — AC-35: công cụ ghi trả giá trị trước/sau — nguồn: FEAT-004 T62 — review: docs/team/features/FEAT-004/review-62.md
- [x] T63 — M4: một hàm cấp, một `GRANT_TABLE`, `unrestricted` là đầu vào thứ tư — nguồn: FEAT-004 T63 — review: docs/team/features/FEAT-004/review-63.md
- [x] T64 — AC-35: runner ghi trước/sau và người ra lệnh vào mục hành động — nguồn: FEAT-004 T64 — review: docs/team/features/FEAT-004/review-64.md
- [x] T65 — M5: bộ chặn ghi của tài khoản agent, ERP AI Setting và ERP AI Credential đóng — nguồn: FEAT-004 T65 — review: docs/team/features/FEAT-004/review-65.md
- [x] T66 — M5: ERP AI Log chỉ nhận ghi của agent qua `run_log.write_entry` — nguồn: FEAT-004 T66 — review: docs/team/features/FEAT-004/review-66.md
- [x] T67 — M5: ERP AI Change Proposal chỉ nhận tạo của agent qua tool đề xuất — nguồn: FEAT-004 T67 — review: docs/team/features/FEAT-004/review-67.md
- [x] T68 — Luật kiến trúc của ADR-023 — nguồn: FEAT-004 T68 — review: docs/team/features/FEAT-004/review-68.md
