Feature: CHG-001
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan CHG-001

Bản ghi lại (`/team:plan CHG-001 --insert`, chỉ ghi, không sinh task mới). CHG-001 không có kế hoạch riêng: task của nó đã được chèn vào FEAT-004 và build ở đó. Nguồn duy nhất về chữ task, tiến độ và review là `docs/team/features/FEAT-004/tasks.md` (Phần 6) và `docs/team/features/FEAT-004/plan.md` mục "Chèn CHG-001 (Amendment 2)". File này và `tasks.md` cạnh nó chỉ trỏ về đó.

- Nhánh feature: không có `team/CHG-001`; công việc chạy trên `team/FEAT-004`, đã merge vào `develop` (`4469287`)
- Số task: 16 (FEAT-004 T53–T68), đều đã tick ở nguồn; song song tối đa: theo build của FEAT-004

## Task đã đi đâu và vì sao
- Đi đâu: commit `7c2a3af` chèn T53–T68 thành "Phần 6, CHG-001 / Amendment 2" của `FEAT-004/tasks.md`; T48 và T34 của FEAT-004 được gắn `[affected]`. Bản đồ file → task, ràng buộc dùng chung, bảng một file một chủ nằm ở `FEAT-004/plan.md` mục "Chèn CHG-001 (Amendment 2)".
- Vì sao chèn vào FEAT-004 thay vì lập `tasks.md` riêng:
  1. CHG-001 là change-request trên FEAT-004 lúc FEAT-004 còn đang build (45/52 đã tick); `CHG-001/spec.md` chỉ là con trỏ tới Amendment 2 của spec FEAT-004 (AC-24..AC-35).
  2. Mọi file bị chạm (`apply_job.py`, `site_api.py`, `registry.py`, `runner.py`, `propose_change.py`, `change_decision.py`, `test_architecture.py`) đang có task FEAT-004 khác sở hữu. Hai `tasks.md` cùng sở hữu một file là trái luật một file một chủ; chèn vào cùng một file cho phép xếp chuỗi `depends:` (ví dụ T47 → T21 → T22 → T55 → T57 → T48).
  3. Mã CHG-001 nhận về (`25be823`, `6d90e79`) đã nằm trên nhánh của FEAT-004; review và `cmd.test` chạy trên cùng nhánh đó.

## Thứ tự
Như đã build ở FEAT-004: M1 (T53, T54) → M2 (T55) → AC-28 (T56 → T57, sau khi `CHG-001/design.md` có) → AC-27 (T58) → M3 và `site_api` (T59 → T60 → T61 → T62) → M4 (T63 → T64) → M5 (T65 → T66 → T67) → luật kiến trúc ADR-023 (T68).

## Truy vết CHG-001 → task FEAT-004
Chép từ `design.md` mục "Truy vết CHG-001 → task FEAT-004"; chỗ nào lệch thì design thắng.

| Mục | Task | Mục | Task |
|---|---|---|---|
| M1 | T53, T54, T68 | AC-24 | T53 |
| M2 | T55 | AC-25, AC-26 | T54 |
| M3 | T59, T60, T68 | AC-27 | T58 |
| M4 | T63, T68 | AC-28 | T56, T57 (+T48 kiểm chéo NFR-8) |
| M5 | T65, T66, T67, T68 | AC-29, AC-34 | mã nhận về; AC-34 thêm T64 |
| AC-30 | T60 | AC-31 | T59, T60 |
| AC-32 | T63 | AC-33 | T59, T61, T65, T66, T67 |
| AC-35 | T62, T64 | | |

## Không thuộc bản soi
- FEAT-004 T69 (F-3, logger của `source.py`): phát hiện nghiệm thu của FEAT-004, không thuộc Amendment 2.
- FEAT-004 T70 (F-R4-2): chỉ sửa test, ghim câu báo lỗi của AC-26 trong `erp_ai/test_change_decision.py` (file của T54). Có liên quan tới CHG-001 nhưng được chèn như sửa sau nghiệm thu của FEAT-004 (Phần 8), nên chỉ ghi ở đây, không đếm vào `tasks.md` của CHG-001.
- FEAT-004 T48, T34 (`[affected]`): task của FEAT-004 chịu ảnh hưởng, không phải task của CHG-001.

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| Bản soi lệch nguồn | ô tick ở `CHG-001/tasks.md` khác `FEAT-004/tasks.md` | nguồn thắng; sửa bản soi, không sửa nguồn |
| T61 vượt `max_rework` một lần theo quyết định của người | `FEAT-004/asbuilt.md` mục 5 "Rủi ro còn lại", dòng 1 | đọc trước khi bật "Toàn quyền" trên môi trường thật |
| A-D1 của `design.md` còn mở | chưa ai xem dòng `Info` trên trang phiếu Helpdesk thật | qa kiểm khi verify |

## Walking skeleton (cỡ L)
Không áp dụng: không có task mới; walking skeleton là T1 của FEAT-004.
