# Ghi chú bàn giao từ phiên làm trực tiếp (d6349641) cho phiên đang hoàn thiện FEAT-004/005

Ngày: 2026-11-14. Người viết: team-leader của phiên `d6349641`, phiên đã viết thẳng phần code chưa commit trên `develop` theo lệnh của người ("không dùng skill hay agent nào của team, làm trực tiếp").

Phiên này không commit, không tạo nhánh, không gọi agent nào cho phần code đó, để khỏi giẫm lên việc phiên kia đang làm (journal FEAT-004 dòng 2026-11-14, `.team/current.json` = FEAT-004/build lúc 00:30).

## 1. Code chưa commit gồm những gì

| Phần | File chính | Người yêu cầu gì |
|---|---|---|
| Công cụ bản ghi chung (liệt kê, đọc, tạo, sửa) | `erp_ai/agent/tools/site_api.py` | Bot tạo User, gán role, sửa cấu hình trực tiếp, không qua duyệt |
| Ô "Toàn quyền (khẩn cấp)" | `unrestricted_enabled` trong ERP AI Setting, `policy.unrestricted_enabled`, nhóm `site_unrestricted` trong `registry.py` | Thêm xóa, submit/hủy, gọi hàm whitelist; bỏ giới hạn role và tài khoản |
| Ba công cụ đề xuất | `erp_ai/agent/tools/propose_change.py` | Bot đề xuất sửa file, tạo file, lệnh bench |
| Job áp dụng và hoàn tác | `erp_ai/agent/changes/apply_job.py` | Ghi file + 1 commit git local; hoàn tác bằng commit mới |
| Duyệt một lần bấm ngay trên phiếu | `erp_ai/agent/change_link.py`, `erp_ai/change_decision.py`, comment trong `propose_change._comment` | "Nút duyệt phải trên phản hồi ticket", bấm là chạy, không hộp hỏi lại |
| Bot làm luôn, không hỏi | `ACT_NOW_BLOCK`, `SITE_ADMIN_TOOLS_BLOCK`, `UNRESTRICTED_TOOLS_BLOCK` trong `prompts.py` | "Bot làm luôn, không cần hỏi" |
| Nối vào runner | `runner.py`: cấp tool theo công tắc, `WRITE_TOOL_TARGETS`, dòng log `propose` | — |
| Lấy từ nhánh task chưa merge | diff của `team/FEAT-004-task-42` (`change_guard.py`) và `team/FEAT-004-task-6` (`erp_ai_setting.py`) đã `git apply` vào cây chính | Cần cho job áp dụng đọc trạng thái git |

## 2. Đã kiểm gì, chưa kiểm gì

- Lần chạy cả app gần nhất: `Ran 1237 tests in 558.583s`, `FAILED (failures=5)`. Lần đó chạy TRƯỚC khi thêm `ACT_NOW_BLOCK`, `change_link.py`, `change_decision.py`.
- 5 lỗi đó đều do test đọc cài đặt đang lưu của site (`auto_assign_enabled=1`): 3 ở `test_agent_runner.TestRunnerL1Classification`, 2 ở `test_runner_routing`. 3 lỗi đầu đã chạy lại trên mã chưa sửa và vẫn đỏ; 2 lỗi sau mới kết luận từ thông báo lỗi.
- Sau lần đó chỉ chạy theo module, đều `OK`: `test_change_link` (3), `test_change_decision` (8), `test_propose_change` (9), `test_classification` (39), `test_architecture` (112), `test_erp_ai_change_proposal` (24). Chưa chạy lại cả app.
- `pre-commit run --all-files` xanh; `bench migrate` exit 0.
- Cả app giờ chạy khoảng 560 giây: giới hạn 580 giây là không đủ (một lần chạy đã bị cắt).
- CHƯA thử với model thật. CHƯA xem comment có Duyệt / Từ chối hiển thị thế nào trên trang phiếu Helpdesk. CHƯA bấm thử đường dẫn duyệt qua HTTP thật.

## 3. Chỗ cần reviewer xem kỹ (chưa ai review)

1. `change_decision.decide` là GET đổi trạng thái. Chặn giả mạo bằng chữ ký HMAC của Frappe (`get_signed_params`) trên tên đề xuất + hành động; vai trò và trạng thái vẫn kiểm bằng `approve`/`reject` của controller. Cần đánh giá: trình duyệt hoặc proxy tải trước đường dẫn; một agent không có role gửi đường dẫn cho Instructor.
2. `site_api.call_method` (chỉ ở chế độ toàn quyền): chặn hàm `erp_ai.*` và mọi tham số có nhắc tên 4 DocType của app bằng so chuỗi trên JSON. Đây là danh sách cấm, không kín tuyệt đối.
3. `site_api` ở chế độ thường: danh sách role cấm, tài khoản cấm, DocType cấm, trường mật khẩu, Server Script/Webhook luôn tắt. Cần soát đường vòng (ví dụ Role Profile, bảng con).
4. `apply_job`: thứ tự trả lại file khi commit lỗi; `_commit` so `parents` và `paths` sau commit; khóa `filelock` toàn bench.
5. Trái với thiết kế đã ghim: ADR-005 (tool ghi không nhận `doctype`), AC-9 của FEAT-006 (model không chọn người qua tool), xác nhận 2 bước của FEAT-004 (AC-22). Người đã chủ ý đổi; cần ADR mới hoặc amendment ghi lại.
6. Test cũ đã bị sửa theo hành vi mới: `test_registry.py` (số tool 11 → 21, `SCHEMA_TYPES` thêm `object`, số trường `ToolContext` 9 → 10, test chạy mọi handler), `test_doctype_descriptions.py` (mô tả `code_change_enabled`, thêm `unrestricted_enabled`, `field_count` 26 → 27), `test_architecture.py` (`POLICY_FIELDS`), `test_classification.py` (khối prompt).

## 4. Việc còn thiếu so với kế hoạch FEAT-004

- Chưa có luật kiến trúc mới của T31, T32, T44 cho `apply_job.py`, `propose_change.py`, `site_api.py`, `change_decision.py`.
- Chưa có test chéo T48 (hook git không chạy, ref remote không đổi, metadata commit sạch).
- `propose_change.py` không theo từng chữ của design 3.x: tham số là `path`, `edits[{old,new}]`, `reason`; chưa dùng `REPLACE_MAX_ITEMS` ngoài `maxItems`.
- Kết quả áp dụng (xong, lỗi, hết hiệu lực) chưa được comment về phiếu; người phải mở form đề xuất mới biết.
- Form Desk vẫn có hộp xác nhận cho Duyệt / Từ chối / Hoàn tác; chỉ đường dẫn trong comment là một lần bấm.

## 5. Quan hệ với các feature khác

- `CHG-001` (intake 2026-11-13, đang ở `intaken`) mô tả đúng việc mục 1 đã làm. 5 điểm mở trong `intake.md` đã được người trả lời bằng hành vi nêu ở mục 1: làm luôn áp cho cả bản ghi và code; nút nằm trên phản hồi ticket; chỉ bỏ hộp xác nhận ở đường dẫn trong comment; luồng chữ "ok" thay bằng nút; danh sách cấm giữ như mục 3.
- `FEAT-005` (0/52): phần "tạo User và sửa cấu hình qua DocType" phần lớn đã được `site_api.py` thay thế. Cần quyết định thu hẹp hay đóng.
- Site `miyano` đang chạy mã này từ lúc máy khởi động lại 00:26 ngày 2026-11-14 (`enabled=1`, `L3`, `code_change_enabled=1`, `unrestricted_enabled=0`).
