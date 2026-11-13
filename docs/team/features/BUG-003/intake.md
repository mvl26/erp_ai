Feature: BUG-003
Stage: intake
Author-agent: team-leader
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake BUG-003 — Chỉ báo 3 chấm của bot luôn hiện trên trang phiếu dù không có lần chạy nào

- Yêu cầu gốc: "Chỉ báo 3 chấm của bot luôn hiện trên trang phiếu vì display:flex inline đè thuộc tính hidden"
- Nguồn: hội thoại (người báo: "lúc nào tôi cũng thấy 3 chấm chạy thể hiện bot đang chạy, thực tế thì bot không hề làm gì cả")
- Loại việc: bug
- Playbook: bug-fix
- Size: S
- Mode: decide
- Lý do chọn playbook/cỡ: Hành vi lệch spec và suy ra được từ mã — FEAT-002 AC-10 (`docs/team/features/FEAT-002/spec.md:186`) yêu cầu chỉ báo mất chậm nhất 10 s sau câu trả lời, nhưng `erp_ai/public/js/agent_status_indicator.js:77-88` ẩn khung bằng `el.hidden = true` rồi gán style inline `display: "flex"`, mà CSS Helpdesk (Tailwind 3.4.19) chỉ có `[hidden]{display:none}` không `!important` nên style inline thắng và khung không bao giờ ẩn; sửa một file mã + test → S. Không chọn `quick` vì sửa lỗi bắt buộc có test đỏ trước và review (STD-TEST-1), và chỗ ẩn/hiện nằm ở nhiều điểm (`ensureElement`, `render`, `reset`).
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 3; feature_budget_usd = không giới hạn

## Bằng chứng (2026-11-13, site `miyano`)
- Mã: `ensureElement` đặt `el.hidden = true` (`:77`) rồi `Object.assign(el.style, …, { display: "flex", … })` (`:78-88`); `render` (`:122-137`) và `reset` (`:397-399`) chỉ bật/tắt `hidden`.
- CSS đã build của Helpdesk: `[hidden]:where(:not([hidden=until-found])){display:none}` — không `!important`.
- Server không chạy gì: không có RQ Job `started`/`queued`; lần chạy gần nhất (phiếu 43072, 10:14) kết thúc `end_turn` sau khoảng 10 s; `done` được phát trong `finally` (`erp_ai/agent/runner.py:134-137`).
- Lỗi có từ FEAT-002 (commit `c7930e2`), FEAT-003 giữ nguyên (`31c4b75`).
- Chưa quan sát trực tiếp trên trình duyệt: kết luận dựa trên mã và CSS. Dev xác nhận bằng test đỏ; bước tay AC-10 xác nhận sau khi sửa.

## Phạm vi
- Trong: khung chỉ báo ẩn thật khi không có lần chạy (lúc mới tạo, sau `done`, sau hẹn giờ tự mất, khi `reset`, cả khi nổi lẫn khi gắn trong khu vực "Trao đổi với bot"); test tái hiện trước.
- Ngoài: tín hiệu `done` bị rớt làm chỉ báo giữ tới 600 s (đúng AC-11, không phải lỗi); 4 dòng Error Log "lần chạy lỗi … TypeError" của phiếu 43072 lúc 22:22–22:24 ngày 2026-11-12 (chưa điều tra, việc riêng nếu người muốn); mọi thay đổi khác của khu vực trao đổi.

## Lưu ý cho build
- `.team/profile.json` chưa có slot lệnh test JavaScript (FEAT-002 A-21): test tự động theo kiểu quy tắc tĩnh trên file script như các test hiện có của chỉ báo; bước tay AC-10 trên `miyano` vẫn cần người làm.
- Nhánh gốc: script này thuộc FEAT-002/FEAT-003, chưa vào `main`; tách `team/BUG-003` từ `team/FEAT-003`.

## Ràng buộc của người yêu cầu
- Như các việc trước: commit local trên `team/BUG-003`, không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật.

## Đổi cỡ (nếu có)
- —
