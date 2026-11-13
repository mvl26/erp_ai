Feature: FEAT-001
Stage: architect
Author-agent: architect
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Đánh giá tác động kiến trúc FEAT-001

## Module bị chạm
| Module | Thay đổi | Mức |
|---|---|---|
| `erp_ai` / module `ERP AI agent` (`erp_ai/erp_ai_agent/`) | DocType mới: cấu hình agent + bảng con khóa API, nhật ký, báo cáo độ chính xác | Mới (ADR-001) |
| `erp_ai/agent/`, `erp_ai/gateway/`, `erp_ai/eval/`, handlers, tasks, cài đặt | Toàn bộ mã mới, theo bốn tầng | Mới (ADR-001) |
| `erp_ai/hooks.py`, `pyproject.toml` | `doc_events`, `scheduler_events`, `after_install`/`after_migrate`, `required_apps = ["helpdesk"]`, phụ thuộc `anthropic>=0.103.1,<1` | Sửa khung |
| Helpdesk (dữ liệu, không sửa mã) | Custom field AI trên HD Ticket (permlevel 8); thêm dòng vào HD Ticket Template `Default` | Thêm, không ghi đè (ADR-006) |
| Bench env dùng chung | Không đổi phiên bản `anthropic` (đang 0.103.1) | Không đổi (ADR-002) |

## Hợp đồng thay đổi
- Mọi hợp đồng đều mới, không có bên tiêu thụ cũ, nên không có vấn đề tương thích ngược.
- Hợp đồng nội bộ do kiến trúc chốt:
  - một hàm xếp hàng job agent (ADR-003);
  - một hàm điều kiện gửi (ADR-003);
  - một hàm bộ tool theo (mức hiệu lực, có người ra lệnh) (ADR-005);
  - Cổng model là đường duy nhất tới Claude API (ADR-002).
- Schema dữ liệu mới trên site: các DocType của app và custom field trên HD Ticket. Không đổi schema của Helpdesk ngoài custom field.

## NFR bị ảnh hưởng
Đủ 9/9 NFR có giải pháp, xem bảng "NFR → giải pháp" trong `docs/team/architecture.md`.
- NFR-9 không phải điều kiện build. Kiến trúc chỉ bảo đảm phép đo đúng (prompt chung, nhật ký có giá trị người sửa).
- NFR-8 dựa vào tên header còn `UNVERIFIED` (research `:67`).

## Quyết định
ADR mới, đều ở trạng thái `proposed`:
- ADR-001 — Một module `ERP AI agent` và bốn tầng mã phụ thuộc một chiều (đóng H-1).
- ADR-002 — Một cổng gọi Claude API; ghim `anthropic>=0.103.1,<1`; `max_retries=0`; bản rõ khóa chỉ trong cổng (đóng H-4, H-6; theo research Q1 phương án A).
- ADR-003 — Handler chỉ xếp hàng sau commit; job `long` 600 s dưới tài khoản agent; runner kiểm lại mọi chốt (đóng H-3 ở mức kiến trúc).
- ADR-004 — Mỗi thực thể một chủ ghi; nhật ký là nguồn sự thật cho chi phí và số lần chạy.
- ADR-005 — Registry tool là biên giới; mức hiệu lực và thẩm quyền tính một lần ở runner.
- ADR-006 — Cài đặt lặp lại được, tắt sẵn, không ghi đè bản ghi Helpdesk; trường AI permlevel 8 (đóng H-2 ở mức kiến trúc; theo research Q2 phương án A).

Không thay thế ADR nào, vì trước đây chưa có ADR.

## Rủi ro
- Lớn nhất: nhiều bên cùng ghi cấu hình agent (người, runner, job giờ/ngày, nút "Kiểm tra khóa") rồi ghi đè lẫn nhau → ADR-004 Ràng buộc: cấm `.save()` cấu hình; trạng thái khóa chỉ ghi trong `erp_ai/gateway/**`.
- Job chạy dưới user đã lưu phiếu, không phải tài khoản agent (research `:105`) → ADR-003: chuyển tài khoản và kiểm là bước đầu tiên của job.
- Các rủi ro còn lại và kết quả tự phản biện: xem `docs/team/architecture.md` mục Rủi ro.

## Để designer quyết
- Tên file trong từng tầng, tên DocType, tên và kiểu trường (theo `naming.*`): không qua phép thử điều kiện 2, đã có quy ước.
- Xếp 402 và 400 "specified ... usage limits" vào bảng cầu dao (research `:65`): chỉ Cổng model cài đặt (ADR-002), nên không có hai bên lệch nhau.
- Con số timeout mỗi lời gọi và ngưỡng thời gian an toàn trước mốc 600 s: tham số, không phải cấu trúc.
- Cơ chế chặn trùng trong cùng request (research Q2 phương án B gợi ý): chỉ hàm xếp hàng duy nhất dùng.
- Cách tìm mã nguồn (research Q3 gợi ý Python thuần) và danh sách đuôi/mẫu tên bí mật: chỉ module tool mã nguồn dùng.
- Custom field AI tạo bằng fixture có lọc hay bằng mã cài đặt: hai cách đều giữ được ADR-006.
- Có giữ trường hiển thị "số lượt hôm nay" trên phiếu hay không: nếu giữ thì chỉ để hiển thị (ADR-004).
- Schema JSON từng tool, nội dung prompt, định dạng bộ đọc JSON phân loại, cách tìm phiếu tương tự, dạng báo cáo AC-12, tiêu đề Error Log, cách gửi email cảnh báo qua Email Queue.
- "Kiểm tra khóa" chạy đồng bộ trong request hay qua job: NFR-1 chỉ áp cho luồng lưu phiếu/comment; timeout của cổng chặn thời gian chờ.

## Chế độ system
- Kiến trúc toàn hệ thống: `docs/team/architecture.md`. Tài liệu đó có cơ sở khảo sát, sơ đồ một chiều, đơn vị triển khai, quét các chiều và tự phản biện.
- ADR mới: `docs/team/adr/ADR-001.md` … `docs/team/adr/ADR-006.md`. Cả sáu chuyển `accepted` khi G2 được duyệt. Lưu ý: G2 đang tắt trong `.team/config.json`.
